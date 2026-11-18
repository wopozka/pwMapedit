#include "map_items.hpp"

#include <QFont>
#include <QGraphicsSceneMouseEvent>
#include <QKeyEvent>
#include <algorithm>
#include <tuple>
#include <QPainter>
#include <QPainterPathStroker>
#include <QStyleOptionGraphicsItem>
#include <cmath>

#include "constants.hpp"
#include "map_scene.hpp"
#include "map_styles.hpp"
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

// Wielkosc elementu o stalym rozmiarze ekranowym: 1 powyzej progu, ponizej maleje razem z mapa.
double screen_size_factor(const QGraphicsItem* item) {
    return std::min(scene_viewer_scale(item), IGNORE_TRANSFORMATION_TRESHOLD);
}

QStaticText make_text(const QString& text) {
    QStaticText result(text);
    result.setTextFormat(Qt::PlainText);
    return result;
}

Annotation make_label(const QString& text, const QPointF& anchor) {
    Annotation a;
    a.kind = Annotation::Kind::Label;
    a.anchor = anchor;
    a.text = make_text(text);
    return a;
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

// ================================================================ MapObjectItem
bool object_has_data_level(const MapObject& obj, int level) {
    if (!obj.data) return false;
    const auto* polys = obj.data->polys_for_data_level(level);
    if (!polys || polys->empty()) return false;
    return obj.kind() != ObjectKind::Poi || !polys->front().empty();
}

std::vector<int> object_item_levels(const MapObject& obj) {
    std::vector<int> levels;
    for (int level = 0; level < MAP_LEVELS; ++level)
        if (object_has_data_level(obj, level)) levels.push_back(level);
    if (levels.empty()) levels.push_back(0);
    return levels;
}

int object_shown_data_level(const MapObject& obj, int level) {
    if (obj.deleted) return -1;
    if (object_has_data_level(obj, level)) return level;
    if (obj.endlevel < level) return -1;
    // Python zostawial dane z poprzednio ogladanego poziomu; tu bierzemy najwyzszy nizszy poziom z danymi
    for (int l = level - 1; l >= 0; --l)
        if (object_has_data_level(obj, l)) return l;
    return -1;
}

MapScene* MapObjectItem::map_scene() const {
    auto* self = const_cast<MapObjectItem*>(this);
    QGraphicsScene* s = self->graphics_item()->scene();
    return s ? qobject_cast<MapScene*>(s) : nullptr;
}

int MapObjectItem::scene_map_level() const {
    MapScene* s = map_scene();
    return s ? s->map_level() : 0;
}

void MapObjectItem::annotations_changed() {
    if (annotations_.empty()) return;
    if (MapScene* s = map_scene()) s->update_annotations(this);
}

void MapObjectItem::annotations_item_change(QGraphicsItem::GraphicsItemChange change) {
    switch (change) {
        case QGraphicsItem::ItemPositionChange:         // stare miejsce
        case QGraphicsItem::ItemPositionHasChanged:     // nowe miejsce
        case QGraphicsItem::ItemVisibleHasChanged:
        case QGraphicsItem::ItemSelectedHasChanged:     // przezroczystosc zaznaczonego obiektu
            annotations_changed();
            break;
        default:
            break;
    }
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
PoiItem::PoiItem(MapData* map, size_t index, int data_level, const QPixmap& icon)
    : MapObjectItem(map, index, data_level) {
    read_positions();
    if (mp_data_[data_level_]) setPos(*mp_data_[data_level_]);
    setPixmap(icon);
    set_z_value();
    // ItemSendsGeometryChanges: itemChange przy przesunieciu (przerysowanie opisow)
    setFlags(QGraphicsItem::ItemIsSelectable | QGraphicsItem::ItemIsMovable |
             QGraphicsItem::ItemSendsGeometryChanges | QGraphicsItem::ItemIgnoresTransformations);
    setAcceptHoverEvents(true);
}

QPainterPath PoiItem::shape() const {
    const double size = screen_size_factor(this);
    const QPainterPath full = QGraphicsPixmapItem::shape();
    return size < 1 ? QTransform::fromScale(size, size).map(full) : full;
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
    const MapObject& obj = object();
    const int shown = object_shown_data_level(obj, level);
    bool visible = shown >= 0 && shown == data_level_;
    shown_level_ = visible ? shown : -1;
    if (!visible && shown < 0 && !obj.deleted && obj.endlevel >= level) {
        // jak w Pythonie: POI bez danych na tym i nizszych poziomach (w zakresie EndLevel) pozostaje widoczne -
        // tu w polozeniu z najnizszego poziomu, bez pokazywanego poziomu Data
        const std::vector<int> levels = object_item_levels(obj);
        visible = mp_data_[data_level_] && levels.front() == data_level_;
    }
    if (isVisible() != visible) setVisible(visible);
}

void PoiItem::apply_style() {
    MapScene* s = map_scene();
    if (s && s->styles()) setPixmap(s->styles()->poi_icon(object_type()));
}

void PoiItem::refresh() {
    apply_style();
    read_positions();
    if (mp_data_[data_level_]) setPos(*mp_data_[data_level_]);
    annotations_changed();
    annotations_.clear();
    add_label();
    set_map_level(scene_map_level());
    annotations_changed();
}

void PoiItem::add_label() {
    const MapObject& obj = object();
    if (!obj.label1 || obj.label1->empty()) return;
    // na prawo od ikony, w polowie jej wysokosci
    Annotation a = make_label(mp_to_qstring(*obj.label1), QPointF());
    const QRectF r = boundingRect();
    a.offset = QPointF(r.width(), r.height() / 2);
    annotations_.push_back(std::move(a));
}

void PoiItem::paint(QPainter* painter, const QStyleOptionGraphicsItem* option, QWidget* widget) {
    if (scene_viewer_scale(this) < SCALE_WITHOUT_POIS) return;
    const double size = screen_size_factor(this);
    if (size < 1) painter->scale(size, size);
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
    annotations_item_change(change);
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
namespace {
QPainterPath make_path(const std::vector<std::vector<QPointF>>& polys, bool polygon) {
    QPainterPath path;
    for (const auto& poly : polys) {
        if (poly.empty()) continue;
        QPolygonF pp;
        pp.reserve(static_cast<int>(poly.size()) + 1);
        for (const QPointF& p : poly) pp.append(p);
        if (polygon && pp.first() != pp.last()) pp.append(pp.first());
        path.addPolygon(pp);
    }
    return path;
}
}  // namespace

PolyItem::PolyItem(MapData* map, size_t index, int data_level, bool polygon)
    : MapObjectItem(map, index, data_level), polygon_(polygon) {
    setPath(path_for_level(data_level_));
    setFlags(QGraphicsItem::ItemIsSelectable | QGraphicsItem::ItemIsMovable |
             QGraphicsItem::ItemSendsGeometryChanges);
    setAcceptHoverEvents(true);
}

bool PolyItem::has_data_level(int level) const { return object_has_data_level(object(), level); }

QPainterPath PolyItem::path_for_level(int level) const {
    std::vector<std::vector<QPointF>> polys;
    const MapObject& obj = object();
    if (obj.data) {
        if (const auto* data_polys = obj.data->polys_for_data_level(level)) {
            for (const Poly& poly : *data_polys) {
                polys.emplace_back();
                polys.back().reserve(poly.size());
                for (const Node& n : poly) polys.back().emplace_back(n.x(), n.y());
            }
        }
    }
    return make_path(polys, is_polygon());
}

std::vector<std::vector<QPointF>> PolyItem::shown_nodes() const {
    std::vector<std::vector<QPointF>> result;
    const int level = shown_data_level();
    const MapObject& obj = object();
    if (level < 0 || !obj.data) return result;
    if (const auto* polys = obj.data->polys_for_data_level(level)) {
        for (const Poly& poly : *polys) {
            result.emplace_back();
            result.back().reserve(poly.size());
            for (const Node& n : poly) result.back().emplace_back(n.x(), n.y());
        }
    }
    return result;
}

void PolyItem::decorate() {
    undecorate();
    const int level = shown_data_level();
    if (level < 0 || object().deleted) return;
    const auto polys = shown_nodes();
    for (size_t poly_num = 0; poly_num < polys.size(); ++poly_num)
        for (size_t node_num = 0; node_num < polys[poly_num].size(); ++node_num)
            grips_.push_back(new GripItem(this, level, poly_num, node_num, polys[poly_num][node_num]));
    add_decoration_items();
    setFlag(QGraphicsItem::ItemIsMovable, false);
    // jak _decorate w Pythonie: nad obiektem w edycji kursor jest krzyzykiem (polygon w edycji reaguje
    // tylko na krawedz, patrz PolygonItem::shape)
    prepareGeometryChange();
    setCursor(Qt::CrossCursor);
}

void PolyItem::undecorate() {
    remove_decoration_items();
    for (GripItem* grip : grips_) delete grip;
    const bool was_decorated = !grips_.empty();
    grips_.clear();
    setFlag(QGraphicsItem::ItemIsMovable, true);
    if (was_decorated) {
        prepareGeometryChange();
        // nie unsetCursor(): w Qt 6.12 czyta ostatnie zdarzenie myszy widoku, ktorego moze nie byc
        // (wywalenie w QEventPoint::position, np. przy Shift+kliku bez wczesniejszego ruchu myszy)
        setCursor(Qt::ArrowCursor);
    }
}

void PolyItem::preview_node_position(size_t poly_num, size_t node_num, const QPointF& pos) {
    auto polys = shown_nodes();
    if (poly_num >= polys.size() || node_num >= polys[poly_num].size()) return;
    polys[poly_num][node_num] = pos;
    setPath(make_path(polys, is_polygon()));
}

void PolyItem::preview_inserted_node(size_t poly_num, size_t index, const QPointF& pos) {
    auto polys = shown_nodes();
    if (poly_num >= polys.size() || index > polys[poly_num].size()) return;
    polys[poly_num].insert(polys[poly_num].begin() + static_cast<long>(index), pos);
    setPath(make_path(polys, is_polygon()));
}

std::optional<PolyItem::NodeInsertion> PolyItem::node_insertion(const QPointF& p, bool on_segment,
                                                                 bool extend_ends) const {
    std::optional<NodeInsertion> best;
    const auto polys = shown_nodes();
    for (size_t poly_num = 0; poly_num < polys.size(); ++poly_num) {
        const auto& nodes = polys[poly_num];
        const size_t n = nodes.size();
        if (n < 2) continue;
        // odcinki (a, b, indeks wstawienia); polygon ma tez odcinek zamykajacy
        std::vector<std::tuple<size_t, size_t, size_t>> segments;
        for (size_t i = 0; i + 1 < n; ++i) segments.emplace_back(i, i + 1, i + 1);
        if (is_polygon() && nodes.front() != nodes.back()) segments.emplace_back(n - 1, 0, n);
        for (const auto& [ia, ib, insert_at] : segments) {
            const QPointF a = nodes[ia], b = nodes[ib];
            const QPointF ab = b - a;
            const double len2 = QPointF::dotProduct(ab, ab);
            if (len2 == 0) continue;
            const double t_raw = QPointF::dotProduct(p - a, ab) / len2;
            if (on_segment && (t_raw <= 0 || t_raw >= 1)) continue;  // punkt poza odcinkiem
            const double t = std::clamp(t_raw, 0.0, 1.0);
            const QPointF proj = a + ab * t;
            const QPointF d = p - proj;
            NodeInsertion cand{poly_num, insert_at, on_segment ? proj : p, std::hypot(d.x(), d.y())};
            if (extend_ends && !is_polygon()) {
                if (ia == 0 && t_raw < 0)
                    cand.index = 0;  // przed pierwszym wezlem
                else if (ib == n - 1 && t_raw > 1)
                    cand.index = n;  // za ostatnim wezlem
            }
            if (!best || cand.distance < best->distance) best = cand;
        }
    }
    return best;
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
    annotations_changed();  // obszar starych opisow
    remove_level_items();
    setPath(path_for_level(data_level_));
    add_level_items();
    annotations_changed();
}

void PolyItem::refresh() {
    apply_style();
    const bool was_decorated = decorated();
    undecorate();
    // po przesunieciu sciezka jest juz w nowym miejscu, a polozenie elementu wraca do (0, 0)
    setPos(0, 0);
    rebuild();
    set_map_level(scene_map_level());
    // uchwyty odpowiadaja nowym wezlom (wstawienie lub usuniecie wezla zmienia ich liczbe)
    if (was_decorated && isVisible() && isSelected()) decorate();
}

void PolyItem::set_map_level(int level) {
    const int shown = object_shown_data_level(object(), level);
    const bool visible = shown >= 0 && shown == data_level_;
    if (isVisible() != visible) setVisible(visible);
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
    annotations_item_change(change);
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
PolylineItem::PolylineItem(MapData* map, size_t index, int data_level, const QPen& pen)
    : PolyItem(map, index, data_level, false) {
    orig_pen_ = pen;
    setPen(pen);
    set_z_value();
}

void PolylineItem::apply_style() {
    MapScene* s = map_scene();
    if (!s || !s->styles()) return;
    orig_pen_ = s->styles()->polyline_pen(object_type());
    if (!isSelected()) setPen(orig_pen_);  // zaznaczony obiekt ma pioro zaznaczenia
}

void PolylineItem::remove_level_items() {
    annotations_.erase(std::remove_if(annotations_.begin(), annotations_.end(),
                                      [](const Annotation& a) { return !a.decoration; }),
                       annotations_.end());
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
        Annotation a;
        a.kind = Annotation::Kind::Arrow;
        a.anchor = p1 + (p2 - p1) / 2;
        a.angle = static_cast<float>(misc::vector_angle(p2.x() - p1.x(), p2.y() - p1.y(), true, true));
        annotations_.push_back(std::move(a));
    }
}

void PolylineItem::add_label() {
    const MapObject& obj = object();
    if (!obj.label1 || obj.label1->empty()) return;
    // w polowie srodkowego odcinka, wzdluz niego
    const QPainterPath& path = this->path();
    const int n = path.elementCount();
    if (n == 0) return;
    Annotation a = make_label(mp_to_qstring(*obj.label1), path.elementAt(0));
    if (n >= 2) {
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
        a.anchor = p1 + (p2 - p1) / 2;
        double angle = misc::vector_angle(p2.x() - p1.x(), p2.y() - p1.y(), true, true);
        a.angle = static_cast<float>(misc::calculate_label_angle(angle));
    }
    annotations_.push_back(std::move(a));
}

void PolylineItem::add_hlevel_labels() {
    const MapObject& obj = object();
    if (!obj.data) return;
    auto polygons = polygons_from_path();
    for (size_t poly_num = 0; poly_num < polygons.size(); ++poly_num) {
        std::vector<OptInt> hlevels;
        try {
            hlevels = obj.data->hlevels_for_poly(data_level_, poly_num);
        } catch (const MpError&) {
            continue;
        }
        for (size_t node_num = 0; node_num < polygons[poly_num].size() && node_num < hlevels.size(); ++node_num) {
            if (!hlevels[node_num]) continue;
            Annotation a;
            a.kind = Annotation::Kind::LevelNumber;
            a.anchor = polygons[poly_num][node_num];
            a.text = make_text(QString(QChar(0x2191)) + QString::number(*hlevels[node_num]));
            annotations_.push_back(std::move(a));
        }
    }
}

namespace {
// Numer adresowy: srodek napisu odsuniety od wezla o wektor position (dlugosc w pikselach ekranu).
Annotation make_address_number(const QLineF& position, long long number, bool left_side, bool interpolated) {
    Annotation a;
    a.kind = Annotation::Kind::AddressNumber;
    a.anchor = position.p1();
    a.offset = position.p2() - position.p1();
    a.text = make_text(QString::number(number));
    if (left_side)
        a.colour = interpolated ? LEFT_SIDE_NUM_INTER : LEFT_SIDE_NUM_MAIN;
    else
        a.colour = interpolated ? RIGHT_SIDE_NUM_INTER : RIGHT_SIDE_NUM_MAIN;
    a.decoration = interpolated;
    return a;
}
}  // namespace

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
            numbers = obj.data->housenumbers_for_poly(data_level_, poly_num);
        } catch (const MpError&) {
            continue;
        }
        auto add = [&](const OptInt& value, long segment_idx, int side, bool left) {
            if (!value) return;
            const QLineF* segment = py_at(vectors, segment_idx);
            if (!segment || segment->length() == 0) return;
            annotations_.push_back(make_address_number(numbers_position(*segment, side), *value, left, false));
        };
        for (size_t node = 0; node < coords.size() && node < numbers.size(); ++node) {
            const NumbersDefinition* def = numbers[node];
            if (!def) continue;
            long n = static_cast<long>(node);
            add(def->left_side_number_before, n - 1, LeftBefore, true);
            add(def->left_side_number_after, n, LeftAfter, true);
            add(def->right_side_number_before, n - 1, RightBefore, false);
            add(def->right_side_number_after, n, RightAfter, false);
        }
    }
}

void PolylineItem::remove_decoration_items() {
    const bool any = std::any_of(annotations_.begin(), annotations_.end(),
                                 [](const Annotation& a) { return a.decoration; });
    if (!any) return;
    annotations_changed();
    annotations_.erase(std::remove_if(annotations_.begin(), annotations_.end(),
                                      [](const Annotation& a) { return a.decoration; }),
                       annotations_.end());
}

void PolylineItem::add_decoration_items() {
    // Port add_interpolated_housenumber_labels/get_interpolated_housenumbers: numery miedzy wezlami z numeracja,
    // rozlozone rowno wzdluz linii, odsuniete od niej prostopadle o 10 pikseli (wektor po stronie numeru).
    remove_decoration_items();
    const MapObject& obj = object();
    if (!obj.data) return;
    const int level = shown_data_level();
    if (level < 0) return;
    const size_t polys_count = shown_nodes().size();
    for (size_t poly_num = 0; poly_num < polys_count; ++poly_num) {
        InterpolatedNumbers numbers;
        try {
            numbers = obj.data->interpolated_housenumbers_for_poly(level, poly_num);
        } catch (const std::exception&) {
            continue;
        }
        auto add = [&](const InterpolatedNumber& num, bool left) {
            const QPointF position(num.position.x, num.position.y);
            QLineF along(position, QPointF(num.vector.p2.x, num.vector.p2.y));
            // numer dokladnie na koncu odcinka: kierunek bierzemy z calego odcinka
            if (along.length() == 0) along = QLineF(num.vector.p1.x, num.vector.p1.y, num.vector.p2.x, num.vector.p2.y);
            if (along.length() == 0) return;
            along.translate(position - along.p1());
            QLineF vector = along.normalVector();
            if (!left) vector = vector.normalVector().normalVector();
            QLineF number_vector = vector.unitVector();
            number_vector.setLength(10);
            annotations_.push_back(make_address_number(number_vector, num.number, left, true));
        };
        for (const InterpolatedNumber& num : numbers.left) add(num, true);
        for (const InterpolatedNumber& num : numbers.right) add(num, false);
    }
    annotations_changed();
}

// ================================================================ PolygonItem
PolygonItem::PolygonItem(MapData* map, size_t index, int data_level, const QPen& pen, const QBrush& brush,
                         int z_value)
    : PolyItem(map, index, data_level, true), z_value_(z_value) {
    orig_pen_ = pen;
    setPen(pen);
    setBrush(brush);
    set_z_value();
}

void PolygonItem::paint(QPainter* painter, const QStyleOptionGraphicsItem* option, QWidget* widget) {
    if (scene_viewer_scale(this) <= SCALE_WITHOUT_SMALL_POLYS && small_poly()) return;
    // tryb przezroczysty: niezaznaczony polygon jak zaznaczony (opacity 0.5); zaznaczony ma ja juz ustawiona
    MapScene* s = map_scene();
    if (s && s->transparent_polygons() && !isSelected()) {
        painter->save();
        painter->setOpacity(painter->opacity() * 0.5);
        PolyItem::paint(painter, option, widget);
        painter->restore();
        return;
    }
    PolyItem::paint(painter, option, widget);
}

void PolygonItem::apply_style() {
    MapScene* s = map_scene();
    if (!s || !s->styles()) return;
    const long long type = object_type();
    orig_pen_ = s->styles()->polygon_pen(type);
    setBrush(QBrush(s->styles()->polygon_fill_colour(type)));
    z_value_ = s->styles()->polygon_z_value(type);
    if (isSelected()) {
        setZValue(z_value_);
        set_selection_z_value();
    } else {
        setPen(orig_pen_);
        set_z_value();
    }
}

bool PolygonItem::small_poly() const {
    const MapObject& obj = object();
    return obj.data && obj.data->perimeter() < SMALL_POLY_PERIMETER;
}

void PolygonItem::remove_level_items() { annotations_.clear(); }

void PolygonItem::add_level_items() {
    // W Pythonie etykieta polygonu dostawala pusty tekst (_mp_label nie byl ustawiany); tu pokazujemy Label.
    const MapObject& obj = object();
    if (obj.label1 && !obj.label1->empty())
        annotations_.push_back(make_label(mp_to_qstring(*obj.label1), boundingRect().center()));
}

// ================================================================ opisy
QLineF numbers_position(const QLineF& segment, int side) {
    // Port get_numbers_position (wariant nietestowy). Wartosci pointAt dobrane tak, aby wektor prostopadly
    // wskazywal wlasciwa strone w ekranowym ukladzie wspolrzednych (stad zamiana stron).
    double a = 15 / segment.length();
    QPointF start_point, start, end;
    switch (side) {
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

AnnotationLayer::AnnotationLayer(MapScene* scene) : map_scene_(scene) {
    setZValue(ANNOTATION_Z_VAL);
    setAcceptedMouseButtons(Qt::NoButton);
    setAcceptHoverEvents(false);
    setFlag(QGraphicsItem::ItemUsesExtendedStyleOption, true);  // exposedRect w paint()
}

void AnnotationLayer::set_rect(const QRectF& rect) {
    if (rect == rect_) return;
    prepareGeometryChange();
    rect_ = rect;
}

void AnnotationLayer::paint(QPainter* painter, const QStyleOptionGraphicsItem* option, QWidget* widget) {
    Q_UNUSED(widget);
    if (!map_scene_->map()) return;
    static const QFont label_font;
    static const QFont number_font = [] {
        QFont font;
        font.setPointSize(6);
        return font;
    }();
    static const QPainterPath arrow = [] {
        QPainterPath path;
        path.moveTo(-6, 4);
        path.lineTo(6, 0);
        path.lineTo(-6, -4);
        return path;
    }();
    static const QPen arrow_pen(Qt::black, 1);
    static const QPen level_pen(Qt::black, 0);

    const QTransform world = painter->worldTransform();
    const double scale = std::max(world.m11(), 1e-9);
    // powyzej progu stala wielkosc na ekranie, ponizej opisy maleja razem z mapa
    const double size = std::min(scale, IGNORE_TRANSFORMATION_TRESHOLD);
    const bool texts = scale >= SCALE_WITHOUT_LABELS;
    const double margin = MARGIN_PX / scale;
    const QRectF exposed = option->exposedRect.adjusted(-margin, -margin, margin, margin);
    const double base_opacity = painter->opacity();

    painter->save();
    const QFont* current_font = nullptr;
    auto use_font = [&](const QFont& font) {
        if (current_font != &font) {
            painter->setFont(font);
            current_font = &font;
        }
    };
    auto prepare = [](Annotation& a, const QFont& font) {
        if (a.prepared) return;
        a.text.prepare(QTransform(), font);
        a.prepared = true;
    };

    for (MapObjectItem* obj : map_scene_->object_items()) {
        std::vector<Annotation>& annotations = obj->annotations();
        if (annotations.empty()) continue;
        QGraphicsItem* item = obj->graphics_item();
        if (!item->isVisible()) continue;
        const QPointF item_pos = item->pos();  // przy przeciaganiu obiekt ma przesuniete polozenie
        if (item->type() == PoiItemType ? !exposed.contains(item_pos) : !item->sceneBoundingRect().intersects(exposed))
            continue;
        const double opacity = base_opacity * item->opacity();  // zaznaczona polilinia/polygon: 0.5
        for (Annotation& a : annotations) {
            if (a.kind != Annotation::Kind::Arrow && !texts) continue;
            const QPointF p = world.map(item_pos + a.anchor);
            QTransform t;
            switch (a.kind) {
                case Annotation::Kind::Label: {
                    use_font(label_font);
                    prepare(a, label_font);
                    t.translate(p.x(), p.y());
                    if (a.angle != 0) t.rotate(a.angle);
                    t.scale(size, size);
                    t.translate(a.offset.x(), a.offset.y());
                    painter->setTransform(t);
                    painter->setOpacity(opacity);
                    painter->setPen(a.colour);
                    painter->drawStaticText(QPointF(), a.text);
                    break;
                }
                case Annotation::Kind::AddressNumber: {
                    use_font(number_font);
                    prepare(a, number_font);
                    const QSizeF s = a.text.size();
                    t.translate(p.x() + a.offset.x(), p.y() + a.offset.y());
                    t.scale(size, size);
                    painter->setTransform(t);
                    painter->setOpacity(base_opacity);  // jak ItemIgnoresParentOpacity
                    painter->setPen(a.colour);
                    painter->drawStaticText(QPointF(-s.width() / 2, -s.height() / 2), a.text);
                    break;
                }
                case Annotation::Kind::LevelNumber: {
                    use_font(label_font);
                    prepare(a, label_font);
                    const QSizeF s = a.text.size();
                    t.translate(p.x(), p.y());
                    t.scale(size, size);
                    painter->setTransform(t);
                    painter->setOpacity(opacity);
                    painter->setPen(level_pen);
                    painter->setBrush(Qt::yellow);
                    painter->drawRect(QRectF(0, 0, std::ceil(s.width()) + 1, std::ceil(s.height()) + 1));
                    painter->setPen(a.colour);
                    painter->drawStaticText(QPointF(), a.text);
                    break;
                }
                case Annotation::Kind::Arrow: {
                    t.translate(p.x(), p.y());
                    t.rotate(a.angle);
                    t.scale(size, size);
                    painter->setTransform(t);
                    painter->setOpacity(opacity);
                    painter->setPen(arrow_pen);
                    painter->setBrush(Qt::black);
                    painter->drawPath(arrow);
                    break;
                }
            }
        }
    }
    painter->restore();
}

// ================================================================ RoadCasingLayer
RoadCasingLayer::RoadCasingLayer(const MapScene* scene) : map_scene_(scene) {
    setZValue(ROAD_CASING_Z_VAL);
    setAcceptedMouseButtons(Qt::NoButton);
    setAcceptHoverEvents(false);
    // exposedRect w paint(): rysowane sa tylko drogi w odswiezanym fragmencie, nie cala mapa
    setFlag(QGraphicsItem::ItemUsesExtendedStyleOption, true);
}

void RoadCasingLayer::set_rect(const QRectF& rect) {
    if (rect == rect_) return;
    prepareGeometryChange();
    rect_ = rect;
}

void RoadCasingLayer::paint(QPainter* painter, const QStyleOptionGraphicsItem* option, QWidget* widget) {
    Q_UNUSED(widget);
    const MapStyles* styles = map_scene_->styles();
    if (!styles || !map_scene_->map()) return;
    // obwodka wychodzi poza prostokat drogi o kilka pikseli - z zapasem, zeby nie ucinac drog przy brzegu
    const double scale = std::max(painter->worldTransform().m11(), 1e-9);
    const double margin = 8 / scale;
    const QRectF exposed = option->exposedRect.adjusted(-margin, -margin, margin, margin);
    auto draw = [painter](QGraphicsItem* item) {
        const QPointF pos = item->pos();  // przy przeciaganiu droga ma przesuniete polozenie
        if (pos.isNull()) {
            painter->drawPath(static_cast<QGraphicsPathItem*>(item)->path());
        } else {
            painter->translate(pos);
            painter->drawPath(static_cast<QGraphicsPathItem*>(item)->path());
            painter->translate(-pos);
        }
    };
    // 1. obwodki wszystkich drog i kolei
    std::vector<std::pair<QGraphicsItem*, long long>> with_base;
    long long last_type = -1;
    for (MapObjectItem* obj : map_scene_->object_items()) {
        QGraphicsItem* item = obj->graphics_item();
        if (item->type() != PolylineItemType || !item->isVisible()) continue;
        if (!item->sceneBoundingRect().intersects(exposed)) continue;
        const long long type = obj->object_type();
        if (!MapStyles::has_casing(type)) continue;
        if (type != last_type) {
            painter->setPen(styles->road_casing_pen(type));
            last_type = type;
        }
        draw(item);
        if (MapStyles::is_railway(type)) with_base.emplace_back(item, type);
    }
    // 2. tlo pod linia przerywana (kolej) - nad wszystkimi obwodkami, zeby na rozjazdach czarna obwodka jednego
    // toru nie przecinala bialego tla drugiego
    last_type = -1;
    for (const auto& [item, type] : with_base) {
        if (type != last_type) {
            if (auto pen = styles->casing_base_pen(type)) painter->setPen(*pen);
            last_type = type;
        }
        draw(item);
    }
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

// ================================================================ GripItem
namespace {
QPainterPath grip_square() {
    QPainterPath square;
    square.addRect(-5, -5, 10, 10);
    return square;
}
}  // namespace

GripItem::GripItem(PolyItem* parent, int data_level, size_t poly_num, size_t node_num, const QPointF& pos)
    : QGraphicsPathItem(parent), parent_(parent), data_level_(data_level), poly_num_(poly_num), node_num_(node_num) {
    static const QPainterPath square = grip_square();
    setPath(square);
    setPen(QPen(first_grip() ? QColor("red") : QColor("green"), 1));
    set_hover(false);
    setZValue(100);
    setPos(pos);
    setFlags(QGraphicsItem::ItemIsMovable | QGraphicsItem::ItemSendsGeometryChanges |
             QGraphicsItem::ItemIgnoresParentOpacity | QGraphicsItem::ItemIgnoresTransformations |
             QGraphicsItem::ItemIsFocusable);
    setAcceptHoverEvents(true);
    setCursor(Qt::PointingHandCursor);
    ready_ = true;
}

void GripItem::set_preview_only() {
    ready_ = false;
    setAcceptedMouseButtons(Qt::NoButton);
    setAcceptHoverEvents(false);
    setFlag(QGraphicsItem::ItemIsMovable, false);
    set_hover(true);
}

GripItem::~GripItem() {
    if (hover_scene_) hover_scene_->grip_hovered(this, false);
}

void GripItem::set_hover(bool hover) {
    // pierwszy wezel: czerwony, po najechaniu zielony; pozostale odwrotnie
    const bool red = first_grip() != hover;
    setBrush(QBrush(red ? QColor("red") : QColor("green")));
}

bool GripItem::is_active() const {
    auto* s = qobject_cast<MapScene*>(scene());
    if (!s || !ready_) return false;
    const auto& g = s->active_grip();
    return g && g->obj == parent_->object_index() && g->level == data_level_ && g->poly == poly_num_ &&
           g->node == node_num_;
}

void GripItem::paint(QPainter* painter, const QStyleOptionGraphicsItem* option, QWidget* widget) {
    if (!is_active()) {
        QGraphicsPathItem::paint(painter, option, widget);
        return;
    }
    painter->setPen(QPen(Qt::black, 1));
    painter->setBrush(QColor(0, 120, 255));
    painter->drawPath(path());
}

QVariant GripItem::itemChange(GraphicsItemChange change, const QVariant& value) {
    if (change == ItemPositionHasChanged && ready_) parent_->preview_node_position(poly_num_, node_num_, pos());
    return QGraphicsPathItem::itemChange(change, value);
}

void GripItem::hoverEnterEvent(QGraphicsSceneHoverEvent* event) {
    set_hover(true);
    if (auto* s = qobject_cast<MapScene*>(scene())) {
        // skroty jednoliterowe (narzedzia, poziomy) sa wylaczane, zeby klawisz 's' trafil do uchwytu
        hover_scene_ = s;
        s->grip_hovered(this, true);
        setFocus(Qt::MouseFocusReason);
    }
    QGraphicsPathItem::hoverEnterEvent(event);
}

void GripItem::hoverLeaveEvent(QGraphicsSceneHoverEvent* event) {
    set_hover(false);
    clearFocus();
    if (hover_scene_) {
        hover_scene_->grip_hovered(this, false);
        hover_scene_ = nullptr;
    }
    QGraphicsPathItem::hoverLeaveEvent(event);
}

void GripItem::mousePressEvent(QGraphicsSceneMouseEvent* event) {
    auto* s = qobject_cast<MapScene*>(scene());
    if (!s || event->button() != Qt::LeftButton) {
        QGraphicsPathItem::mousePressEvent(event);
        return;
    }
    s->set_active_grip(parent_->object_index(), data_level_, poly_num_, node_num_);
    press_pos_ = pos();
    if (event->modifiers() == Qt::ControlModifier) {
        s->request_node_removal(parent_->object_index(), data_level_, poly_num_, node_num_);
        event->accept();
        return;
    }
    QGraphicsPathItem::mousePressEvent(event);
}

void GripItem::mouseMoveEvent(QGraphicsSceneMouseEvent* event) {
    QGraphicsPathItem::mouseMoveEvent(event);
    auto* s = qobject_cast<MapScene*>(scene());
    if (!s) return;
    // Ctrl w trakcie przeciagania: wezel przyciagany do najblizszego wezla innego obiektu (stick_to_neighbours)
    std::optional<QPointF> snap;
    if (event->modifiers() & Qt::ControlModifier)
        snap = s->closest_node(pos(), SNAP_DISTANCE / std::max(s->viewer_scale(), 1e-9), parent_);
    s->show_snap_indicator(snap);
    if (snap) setPos(*snap);
}

void GripItem::mouseReleaseEvent(QGraphicsSceneMouseEvent* event) {
    QGraphicsPathItem::mouseReleaseEvent(event);
    if (auto* s = qobject_cast<MapScene*>(scene())) s->show_snap_indicator(std::nullopt);
    if (event->button() != Qt::LeftButton || pos() == press_pos_) return;
    if (auto* s = qobject_cast<MapScene*>(scene()))
        s->request_node_move(parent_->object_index(), data_level_, poly_num_, node_num_, pos());
}

void GripItem::keyPressEvent(QKeyEvent* event) {
    auto* s = qobject_cast<MapScene*>(scene());
    if (s && event->text() == QLatin1String("s")) {
        s->request_split(parent_->object_index(), data_level_, poly_num_, node_num_);
        event->accept();
        return;
    }
    QGraphicsPathItem::keyPressEvent(event);
}

}  // namespace pwm::gui
