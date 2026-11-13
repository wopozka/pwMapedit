#include "map_items.hpp"

#include <QFont>
#include <QGraphicsSceneMouseEvent>
#include <QPainter>
#include <QPainterPathStroker>
#include <QStyleOptionGraphicsItem>
#include <cmath>

#include "constants.hpp"
#include "map_scene.hpp"
#include "map_view.hpp"
#include "misc.hpp"

namespace pwm::gui {

QString mp_to_qstring(const std::string& cp1250) {
    return QString::fromStdString(encoding::cp1250_to_utf8(cp1250));
}

namespace {

QPen make_selected_pen() {
    QPen pen(QColor("red"));
    pen.setCosmetic(true);
    pen.setStyle(Qt::DotLine);
    pen.setWidth(4);
    return pen;
}

QPen make_hovered_pen() {
    QPen pen(QColor("red"));
    pen.setWidth(1);
    pen.setCosmetic(true);
    return pen;
}

double scene_viewer_scale(const QGraphicsItem* item) {
    auto* s = item->scene() ? qobject_cast<MapScene*>(item->scene()) : nullptr;
    return s ? s->viewer_scale() : 1.0;
}

bool scene_ignores_transformations(const QGraphicsItem* item) {
    return scene_viewer_scale(item) > IGNORE_TRANSFORMATION_TRESHOLD;
}

// Indeksowanie jak w Pythonie (-1 = ostatni element).
template <typename V>
const typename V::value_type* py_at(const V& v, long idx) {
    long n = static_cast<long>(v.size());
    if (idx < 0) idx += n;
    if (idx < 0 || idx >= n) return nullptr;
    return &v[static_cast<size_t>(idx)];
}

}  // namespace

// ================================================================ ScreenSized
void ScreenSized::apply_transformation_flag(bool ignore) {
    QGraphicsItem* item = screen_sized_item();
    if (item->flags().testFlag(QGraphicsItem::ItemIgnoresTransformations) != ignore)
        item->setFlag(QGraphicsItem::ItemIgnoresTransformations, ignore);
}

// ================================================================ MapObjectItem
MapScene* MapObjectItem::map_scene() const {
    auto* self = const_cast<MapObjectItem*>(this);
    QGraphicsScene* s = self->graphics_item()->scene();
    return s ? qobject_cast<MapScene*>(s) : nullptr;
}

int MapObjectItem::scene_map_level() const {
    MapScene* s = map_scene();
    return s ? s->map_level() : 0;
}

bool MapObjectItem::accept_mouse_move(QGraphicsSceneMouseEvent* event) {
    MapScene* s = map_scene();
    if (!s || s->tool() != Tool::SelectObjects || !(event->buttons() & Qt::LeftButton)) return false;
    if (!move_started_) {
        // Python mierzyl MIN_MOVE_DISTANCE w jednostkach sceny; tu w pikselach ekranu, niezaleznie od skali
        QPointF d = event->screenPos() - event->buttonDownScreenPos(Qt::LeftButton);
        if (std::hypot(d.x(), d.y()) <= MIN_MOVE_DISTANCE) return false;
        move_started_ = true;
    }
    return true;
}

void MapObjectItem::set_selection_z_value() {
    QGraphicsItem* item = graphics_item();
    if (item->zValue() < SELECTED_OBJECT_Z_VAL) item->setZValue(item->zValue() + SELECTED_OBJECT_Z_VAL);
}

// ================================================================ PoiItem
PoiItem::PoiItem(MapData* map, size_t index, const QPixmap& icon) : MapObjectItem(map, index) {
    read_positions();
    for (int level = 0; level < MAP_LEVELS; ++level) {
        if (mp_data_[level]) {
            setPos(*mp_data_[level]);
            break;
        }
    }
    setPixmap(icon);
    set_z_value();
    setFlags(QGraphicsItem::ItemIsSelectable | QGraphicsItem::ItemIsMovable);
    setAcceptHoverEvents(true);
}

void PoiItem::read_positions() {
    const MapObject& obj = object();
    for (int level = 0; level < MAP_LEVELS; ++level) {
        mp_data_[level].reset();
        if (!obj.data) continue;
        const auto* polys = obj.data->polys_for_data_level(level);
        if (!polys || polys->empty() || polys->front().empty()) continue;
        const Node& n = polys->front().front();
        mp_data_[level] = QPointF(n.x(), n.y());
    }
}

void PoiItem::set_map_level(int level) {
    apply_transformation_flag(scene_ignores_transformations(this));
    if (object().deleted) {
        shown_level_ = -1;
        setVisible(false);
    } else if (mp_data_[level]) {
        setPos(*mp_data_[level]);
        shown_level_ = level;
        setVisible(true);
    } else if (object().endlevel < level) {
        shown_level_ = -1;
        setVisible(false);
    } else {
        // jak w Pythonie: POI pozostaje widoczne w ostatnim polozeniu; bierzemy najwyzszy nizszy poziom
        shown_level_ = -1;
        for (int l = level - 1; l >= 0; --l) {
            if (mp_data_[l]) {
                setPos(*mp_data_[l]);
                shown_level_ = l;
                break;
            }
        }
        setVisible(true);
    }
}

void PoiItem::refresh() {
    read_positions();
    delete label_;
    label_ = nullptr;
    add_label();
    set_map_level(scene_map_level());
}

void PoiItem::add_label() {
    const MapObject& obj = object();
    if (obj.label1 && !obj.label1->empty()) label_ = new PoiLabel(mp_to_qstring(*obj.label1), this);
}

void PoiItem::paint(QPainter* painter, const QStyleOptionGraphicsItem* option, QWidget* widget) {
    if (scene_viewer_scale(this) < SCALE_WITHOUT_POIS) return;
    QGraphicsPixmapItem::paint(painter, option, widget);
    if (hovered_ && !isSelected()) {
        QPen pen(QColor("red"));
        pen.setCosmetic(true);
        pen.setWidth(1);
        painter->setPen(pen);
        painter->setBrush(Qt::NoBrush);
        painter->drawRect(boundingRect());
    }
}

void PoiItem::hoverEnterEvent(QGraphicsSceneHoverEvent* event) {
    MapScene* s = map_scene();
    if (s && s->tool() == Tool::SelectObjects && !isSelected() &&
        s->viewer_scale() * 10 >= IGNORE_TRANSFORMATION_TRESHOLD) {
        hovered_ = true;
        update();
    }
    QGraphicsPixmapItem::hoverEnterEvent(event);
}

void PoiItem::hoverLeaveEvent(QGraphicsSceneHoverEvent* event) {
    if (hovered_) {
        hovered_ = false;
        update();
    }
    QGraphicsPixmapItem::hoverLeaveEvent(event);
}

void PoiItem::mousePressEvent(QGraphicsSceneMouseEvent* event) {
    move_started_ = false;
    QGraphicsPixmapItem::mousePressEvent(event);
}

void PoiItem::mouseMoveEvent(QGraphicsSceneMouseEvent* event) {
    if (accept_mouse_move(event)) QGraphicsPixmapItem::mouseMoveEvent(event);
}

QVariant PoiItem::itemChange(GraphicsItemChange change, const QVariant& value) {
    if (change == ItemSelectedHasChanged) {
        if (value.toBool()) {
            hovered_ = false;
            set_selection_z_value();
        } else {
            set_z_value();
        }
    }
    return QGraphicsPixmapItem::itemChange(change, value);
}

// ================================================================ PolyItem
PolyItem::PolyItem(MapData* map, size_t index, bool polygon) : MapObjectItem(map, index), polygon_(polygon) {
    for (int level = 0; level < MAP_LEVELS; ++level) {
        if (has_data_level(level)) {
            current_data_x_ = level;
            setPath(path_for_level(level));
            break;
        }
    }
    setFlags(QGraphicsItem::ItemIsSelectable | QGraphicsItem::ItemIsMovable);
    setAcceptHoverEvents(true);
}

bool PolyItem::has_data_level(int level) const {
    const MapObject& obj = object();
    if (!obj.data) return false;
    const auto* polys = obj.data->polys_for_data_level(level);
    return polys && !polys->empty();
}

QPainterPath PolyItem::path_for_level(int level) const {
    QPainterPath path;
    const MapObject& obj = object();
    if (!obj.data) return path;
    const auto* polys = obj.data->polys_for_data_level(level);
    if (!polys) return path;
    for (const Poly& poly : *polys) {
        if (poly.empty()) continue;
        QPolygonF pp;
        pp.reserve(static_cast<int>(poly.size()) + 1);
        for (const Node& n : poly) pp.append(QPointF(n.x(), n.y()));
        if (is_polygon() && pp.first() != pp.last()) pp.append(pp.first());
        path.addPolygon(pp);
    }
    return path;
}

std::vector<std::vector<QPointF>> PolyItem::polygons_from_path() const {
    std::vector<std::vector<QPointF>> result;
    const QList<QPolygonF> subpaths = path().toSubpathPolygons();
    for (const QPolygonF& poly : subpaths) {
        std::vector<QPointF> coords(poly.begin(), poly.end());
        if (is_polygon() && poly.isClosed() && !coords.empty()) coords.pop_back();
        result.push_back(std::move(coords));
    }
    return result;
}

void PolyItem::rebuild() {
    remove_level_items();
    setPath(path_for_level(current_data_x_));
    add_level_items();
    built_data_x_ = current_data_x_;
}

void PolyItem::refresh() {
    // po przesunieciu sciezka jest juz w nowym miejscu, a polozenie elementu wraca do (0, 0)
    setPos(0, 0);
    built_data_x_ = -1;
    set_map_level(scene_map_level());
}

void PolyItem::set_map_level(int level) {
    const MapObject& obj = object();
    int target = -1;
    if (obj.deleted) {
        // ukryty
    } else if (has_data_level(level)) {
        target = level;
    } else if (obj.endlevel >= level) {
        // Python zostawial sciezke z poprzednio ogladanego poziomu; tu bierzemy najwyzszy nizszy poziom z danymi
        for (int l = level - 1; l >= 0; --l) {
            if (has_data_level(l)) {
                target = l;
                break;
            }
        }
    }
    if (target < 0) {
        if (isVisible()) setVisible(false);
        return;
    }
    if (target != built_data_x_) {
        current_data_x_ = target;
        rebuild();
    }
    if (!isVisible()) setVisible(true);
}

QPainterPath PolyItem::stroke_shape() const {
    QPainterPathStroker stroker;
    stroker.setWidth(orig_pen_.width() * 2);
    return stroker.createStroke(path());
}

void PolyItem::paint(QPainter* painter, const QStyleOptionGraphicsItem* option, QWidget* widget) {
    QPen pen = orig_pen_;
    if (isSelected()) {
        static const QPen selected_pen = make_selected_pen();
        pen = selected_pen;
    } else if (hovered_) {
        static const QPen hovered_pen = make_hovered_pen();
        pen = hovered_pen;
    }
    if (hovered_ && !isSelected()) {
        // obwodka jak hovered_shape w Pythonie: szersza, polprzezroczysta czerwona linia pod obiektem
        QPen shape_pen(QColor("red"));
        shape_pen.setCosmetic(true);
        shape_pen.setWidth(orig_pen_.width() + 2);
        painter->save();
        painter->setOpacity(painter->opacity() * 0.3);
        painter->setPen(shape_pen);
        painter->setBrush(Qt::NoBrush);
        painter->drawPath(path());
        painter->restore();
    }
    Q_UNUSED(option);
    Q_UNUSED(widget);
    painter->setPen(pen);
    painter->setBrush(brush());
    painter->drawPath(path());
}

void PolyItem::hoverEnterEvent(QGraphicsSceneHoverEvent* event) {
    MapScene* s = map_scene();
    if (s && s->viewer_scale() * 10 >= IGNORE_TRANSFORMATION_TRESHOLD && !isSelected() &&
        (s->tool() == Tool::SelectObjects || s->tool() == Tool::EditNodes)) {
        hovered_ = true;
        update();
    }
    QGraphicsPathItem::hoverEnterEvent(event);
}

void PolyItem::hoverLeaveEvent(QGraphicsSceneHoverEvent* event) {
    if (hovered_) {
        hovered_ = false;
        update();
    }
    QGraphicsPathItem::hoverLeaveEvent(event);
}

void PolyItem::mousePressEvent(QGraphicsSceneMouseEvent* event) {
    move_started_ = false;
    QGraphicsPathItem::mousePressEvent(event);
}

void PolyItem::mouseMoveEvent(QGraphicsSceneMouseEvent* event) {
    if (accept_mouse_move(event)) QGraphicsPathItem::mouseMoveEvent(event);
}

QVariant PolyItem::itemChange(GraphicsItemChange change, const QVariant& value) {
    if (change == ItemSelectedHasChanged) {
        // jak paint() w Pythonie: zaznaczony obiekt jest polprzezroczysty i rysowany czerwona kropkowana linia
        if (value.toBool()) {
            hovered_ = false;
            set_selection_z_value();
            setPen(make_selected_pen());
            setOpacity(0.5);
        } else {
            set_z_value();
            setPen(orig_pen_);
            setOpacity(1.0);
        }
    }
    return QGraphicsPathItem::itemChange(change, value);
}

// ================================================================ PolylineItem
PolylineItem::PolylineItem(MapData* map, size_t index, const QPen& pen) : PolyItem(map, index, false) {
    orig_pen_ = pen;
    setPen(pen);
    set_z_value();
}

void PolylineItem::remove_level_items() {
    for (QGraphicsItem* item : level_items_) delete item;
    level_items_.clear();
}

void PolylineItem::add_level_items() {
    if (object().dirindicator) add_arrow_heads();
    add_label();
    add_hlevel_labels();
    add_housenumber_labels();
}

void PolylineItem::add_arrow_heads() {
    // strzalka co drugi odcinek, w polowie odcinka
    const QPainterPath& p = path();
    for (int i = 0; i + 1 < p.elementCount(); i += 2) {
        QPointF p1 = p.elementAt(i);
        QPointF p2 = p.elementAt(i + 1);
        auto* arrow = new DirectionArrowHead(p1 + (p2 - p1) / 2, this);
        arrow->setRotation(misc::vector_angle(p2.x() - p1.x(), p2.y() - p1.y(), true, true));
        level_items_.push_back(arrow);
    }
}

void PolylineItem::add_label() {
    const MapObject& obj = object();
    if (obj.label1 && !obj.label1->empty()) level_items_.push_back(new PolylineLabel(mp_to_qstring(*obj.label1), this));
}

void PolylineItem::add_hlevel_labels() {
    const MapObject& obj = object();
    if (!obj.data) return;
    auto polygons = polygons_from_path();
    for (size_t poly_num = 0; poly_num < polygons.size(); ++poly_num) {
        std::vector<OptInt> hlevels;
        try {
            hlevels = obj.data->hlevels_for_poly(current_data_x_, poly_num);
        } catch (const MpError&) {
            continue;
        }
        for (size_t node_num = 0; node_num < polygons[poly_num].size() && node_num < hlevels.size(); ++node_num) {
            if (!hlevels[node_num]) continue;
            level_items_.push_back(new PolylineLevelNumber(*hlevels[node_num], polygons[poly_num][node_num], this));
        }
    }
}

void PolylineItem::add_housenumber_labels() {
    const MapObject& obj = object();
    if (!obj.data) return;
    auto polygons = polygons_from_path();
    for (size_t poly_num = 0; poly_num < polygons.size(); ++poly_num) {
        const auto& coords = polygons[poly_num];
        std::vector<QLineF> vectors;
        for (size_t i = 0; i + 1 < coords.size(); ++i) vectors.emplace_back(coords[i], coords[i + 1]);
        std::vector<const NumbersDefinition*> numbers;
        try {
            numbers = obj.data->housenumbers_for_poly(current_data_x_, poly_num);
        } catch (const MpError&) {
            continue;
        }
        auto add = [&](const OptInt& value, long segment_idx, int subj, bool left) {
            if (!value) return;
            const QLineF* segment = py_at(vectors, segment_idx);
            if (!segment || segment->length() == 0) return;
            QLineF position = PolylineAddressNumber::numbers_position(*segment, subj);
            level_items_.push_back(new PolylineAddressNumber(position, QString::number(*value), this, left, false));
        };
        for (size_t node = 0; node < coords.size() && node < numbers.size(); ++node) {
            const NumbersDefinition* def = numbers[node];
            if (!def) continue;
            long n = static_cast<long>(node);
            add(def->left_side_number_before, n - 1, PolylineAddressNumber::LeftBefore, true);
            add(def->left_side_number_after, n, PolylineAddressNumber::LeftAfter, true);
            add(def->right_side_number_before, n - 1, PolylineAddressNumber::RightBefore, false);
            add(def->right_side_number_after, n, PolylineAddressNumber::RightAfter, false);
        }
    }
}

// ================================================================ PolygonItem
PolygonItem::PolygonItem(MapData* map, size_t index, const QPen& pen, const QBrush& brush, int z_value)
    : PolyItem(map, index, true), z_value_(z_value) {
    orig_pen_ = pen;
    setPen(pen);
    setBrush(brush);
    set_z_value();
}

void PolygonItem::paint(QPainter* painter, const QStyleOptionGraphicsItem* option, QWidget* widget) {
    if (scene_viewer_scale(this) <= SCALE_WITHOUT_SMALL_POLYS && small_poly()) return;
    PolyItem::paint(painter, option, widget);
}

bool PolygonItem::small_poly() const {
    const MapObject& obj = object();
    return obj.data && obj.data->perimeter() < SMALL_POLY_PERIMETER;
}

void PolygonItem::remove_level_items() {
    delete label_;
    label_ = nullptr;
}

void PolygonItem::add_level_items() {
    // W Pythonie etykieta polygonu dostawala pusty tekst (_mp_label nie byl ustawiany); tu pokazujemy Label.
    const MapObject& obj = object();
    if (obj.label1 && !obj.label1->empty()) label_ = new PolygonLabel(mp_to_qstring(*obj.label1), this);
}

// ================================================================ etykiety
MapLabel::MapLabel(const QString& text, QGraphicsItem* parent) : QGraphicsSimpleTextItem(text, parent) {
    apply_transformation_flag(scene_ignores_transformations(this));
}

double MapLabel::viewer_scale() const { return scene_viewer_scale(this); }

void MapLabel::paint(QPainter* painter, const QStyleOptionGraphicsItem* option, QWidget* widget) {
    if (viewer_scale() >= SCALE_WITHOUT_LABELS) QGraphicsSimpleTextItem::paint(painter, option, widget);
}

PoiLabel::PoiLabel(const QString& text, QGraphicsItem* parent) : MapLabel(text, parent) {
    QRectF r = parent->boundingRect();
    setPos(r.width(), r.height() / 2);
    setZValue(20);
}

PolylineLabel::PolylineLabel(const QString& text, QGraphicsPathItem* parent) : MapLabel(text, parent) {
    const QPainterPath& path = parent->path();
    int n = path.elementCount();
    if (n < 2) {
        if (n == 1) setPos(QPointF(path.elementAt(0)));
    } else {
        int i1, i2;
        if (n == 2) {
            i1 = 0;
            i2 = 1;
        } else if (n % 2 == 0) {
            i1 = n / 2 - 1;
            i2 = n / 2;
        } else {
            i1 = n / 2;
            i2 = n / 2 + 1;
        }
        QPointF p1 = path.elementAt(i1);
        QPointF p2 = path.elementAt(i2);
        setPos(p1 + (p2 - p1) / 2);
        double angle = misc::vector_angle(p2.x() - p1.x(), p2.y() - p1.y(), true, true);
        setRotation(misc::calculate_label_angle(angle));
    }
    setZValue(20);
}

PolygonLabel::PolygonLabel(const QString& text, QGraphicsPathItem* parent) : MapLabel(text, parent) {
    setPos(parent->boundingRect().center());
    setZValue(20);
}

PolylineAddressNumber::PolylineAddressNumber(const QLineF& position, const QString& text, QGraphicsItem* parent,
                                             bool left_side, bool interpolated)
    : MapLabel(text, parent), position_(position) {
    QFont font;
    font.setPointSize(6);
    setFont(font);
    if (left_side)
        setBrush(QBrush(interpolated ? LEFT_SIDE_NUM_INTER : LEFT_SIDE_NUM_MAIN));
    else
        setBrush(QBrush(interpolated ? RIGHT_SIDE_NUM_INTER : RIGHT_SIDE_NUM_MAIN));
    setFlag(QGraphicsItem::ItemIgnoresParentOpacity, true);
    set_pos();
}

QLineF PolylineAddressNumber::numbers_position(const QLineF& segment, int subj_position) {
    // Port get_numbers_position (wariant nietestowy). Wartosci pointAt dobrane tak, aby wektor prostopadly
    // wskazywal wlasciwa strone w ekranowym ukladzie wspolrzednych (stad zamiana stron).
    double a = 15 / segment.length();
    QPointF start_point, start, end;
    switch (subj_position) {
        case RightBefore:
            start_point = segment.pointAt(1);
            start = segment.pointAt(1 - a);
            end = segment.pointAt(1 - 2 * a);
            break;
        case RightAfter:
            start_point = segment.pointAt(0);
            start = segment.pointAt(a);
            end = segment.pointAt(0.0);
            break;
        case LeftAfter:
            start_point = segment.pointAt(0);
            start = segment.pointAt(a);
            end = segment.pointAt(2 * a);
            break;
        case LeftBefore:
        default:
            start_point = segment.pointAt(1);
            start = segment.pointAt(1 - a);
            end = segment.pointAt(1);
            break;
    }
    return QLineF(start_point, QLineF(start, end).normalVector().p2());
}

void PolylineAddressNumber::set_pos() {
    double scale = viewer_scale();
    if (scale == current_scale_) return;
    current_scale_ = scale;
    QRectF r = boundingRect();
    QPointF text_center(-r.width() / 2, -r.height() / 2);
    setPos(position_.pointAt(1 / scale) + text_center / scale);
}

void PolylineAddressNumber::paint(QPainter* painter, const QStyleOptionGraphicsItem* option, QWidget* widget) {
    set_pos();
    MapLabel::paint(painter, option, widget);
}

PolylineLevelNumber::PolylineLevelNumber(long long hlevel, const QPointF& position, QGraphicsItem* parent)
    : MapLabel(QString(QChar(0x2191)) + QString::number(hlevel), parent) {
    QRectF r = boundingRect();
    setTransformOriginPoint(r.width() / 2, r.height() / 2);
    setPos(position);
}

void PolylineLevelNumber::paint(QPainter* painter, const QStyleOptionGraphicsItem* option, QWidget* widget) {
    if (viewer_scale() < SCALE_WITHOUT_LABELS) return;
    QRectF r = boundingRect();
    painter->setPen(QPen(Qt::black, 0));
    painter->setBrush(QBrush(Qt::yellow));
    painter->drawRect(QRect(int(r.x()), int(r.y()), int(r.width()) + 1, int(r.height()) + 1));
    QGraphicsSimpleTextItem::paint(painter, option, widget);
}

DirectionArrowHead::DirectionArrowHead(const QPointF& pos, QGraphicsItem* parent) : QGraphicsPathItem(parent) {
    setPos(pos);
    QPainterPath arrow;
    arrow.moveTo(-6, 4);
    arrow.lineTo(6, 0);
    arrow.lineTo(-6, -4);
    setPath(arrow);
    setPen(QPen(Qt::black, 1));
    setBrush(QBrush(Qt::black));
    setZValue(30);
    apply_transformation_flag(scene_ignores_transformations(this));
}

// ================================================================ MapRuler
MapRuler::MapRuler(MapView* view, const Projection* projection)
    : view_(view), projection_(projection), screen_dpi_(view->physicalDpiX()) {
    QPen pen(Qt::black, 2);
    pen.setCosmetic(true);
    setPen(pen);
    setBrush(QBrush(Qt::black));
    setZValue(50);
}

QPointF MapRuler::calculate_point_2() const {
    const double cm_per_inch = 2.54;
    QPoint p2 = QPoint(10, 10) + QPoint(int(screen_dpi_ / cm_per_inch), 0);
    return view_->mapToScene(p2);
}

void MapRuler::calculate_geo_distance() {
    if (one_cm_geo_distance_) return;
    QPointF p1 = view_->mapToScene(QPoint(10, 10));
    QPointF p2 = calculate_point_2();
    try {
        GeoPoint start = projection_->canvas_to_geo(p1.x(), p1.y());
        GeoPoint end = projection_->canvas_to_geo(p2.x(), p2.y());
        one_cm_geo_distance_ = misc::vincenty_distance(start, end);
    } catch (const std::exception&) {
        one_cm_geo_distance_ = 0.0;
    }
}

void MapRuler::draw_ruler() {
    delete distance_label_;
    distance_label_ = nullptr;
    QPointF p1 = view_->mapToScene(QPoint(10, 10));
    QPointF p2 = calculate_point_2();
    calculate_geo_distance();
    QPainterPath ruler;
    ruler.moveTo(p1);
    ruler.lineTo(p2);
    setPath(ruler);
    double d = one_cm_geo_distance_.value_or(0.0);
    QString label = d < 1000 ? QString::asprintf("%.1f m", d) : QString::asprintf("%.1f km", d / 1000);
    distance_label_ = new QGraphicsSimpleTextItem(label, this);
    distance_label_->setPos(p1);
    distance_label_->setFlag(QGraphicsItem::ItemIgnoresTransformations, true);
}

void MapRuler::move_to() { draw_ruler(); }

void MapRuler::scale_to() {
    one_cm_geo_distance_.reset();
    draw_ruler();
}

double MapRuler::map_scale() {
    calculate_geo_distance();
    return one_cm_geo_distance_.value_or(0.0) * 100;
}

}  // namespace pwm::gui
