#include "map_scene.hpp"

#include <QCoreApplication>
#include <QElapsedTimer>
#include <QGraphicsEllipseItem>
#include <QGraphicsPathItem>
#include <QGraphicsView>
#include <QJsonArray>
#include <QJsonDocument>
#include <QMimeData>
#include <QTimer>
#include <QUndoStack>
#include <algorithm>

#include "commands.hpp"
#include "map_items.hpp"
#include "misc.hpp"
#include "map_styles.hpp"

namespace pwm::gui {

MapScene::MapScene(QObject* parent) : QGraphicsScene(parent) {
    // Bez indeksu BSP. Przy setkach tysiecy elementow indeks BSP bardzo spowalnia kazda zmiane geometrii
    // (setPath przy zmianie poziomu mapy: kilka ms na element, czyli minuty dla calej mapy), a przeglad liniowy
    // przy rysowaniu kosztuje kilkadziesiat ms. Python uzywal BSP, ale tam koszt ginal w narzucie interpretera.
    setItemIndexMethod(QGraphicsScene::NoIndex);
    connect(this, &QGraphicsScene::selectionChanged, this, &MapScene::selection_changed);
}

void MapScene::clear_map() {
    clearSelection();  // zdejmuje tez uchwyty (selection_changed)
    selection_order_.clear();
    decorated_.clear();
    active_grip_.reset();
    highlight_path(QPainterPath(), false);
    delete snap_indicator_;
    snap_indicator_ = nullptr;
    if (!object_items_.empty()) {
        // Usuwanie elementow pojedynczo kosztuje O(liczba elementow) na kazdy element (lista elementow
        // najwyzszego poziomu, indeks), czyli przy duzej mapie dziesiatki sekund. clear() usuwa wszystko naraz,
        // wiec elementy niezwiazane z mapa (np. linijke) trzeba wczesniej wyjac ze sceny.
        QList<QGraphicsItem*> keep;
        for (QGraphicsItem* item : std::as_const(persistent_items_)) {
            if (item->scene() == this) {
                removeItem(item);
                keep.append(item);
            }
        }
        clear();
        object_items_.clear();
        items_by_object_.clear();
        for (QGraphicsItem* item : keep) addItem(item);
    }
    map_ = nullptr;
}

void MapScene::set_map(MapData* map, const MapStyles* styles) {
    clear_map();
    map_ = map;
    styles_ = styles;
    if (!map_) return;

    auto& objects = map_->objects();
    const int total = static_cast<int>(objects.size());
    object_items_.reserve(objects.size());
    items_by_object_.assign(objects.size(), nullptr);
    emit progress(0, total);
    QElapsedTimer progress_timer;
    progress_timer.start();
    for (size_t i = 0; i < objects.size(); ++i) {
        if (!objects[i].deleted) create_item(i);
        if (progress_timer.elapsed() > 100) {
            emit progress(static_cast<int>(i), total);
            QCoreApplication::processEvents(QEventLoop::ExcludeUserInputEvents);
            progress_timer.restart();
        }
    }
    emit progress(total, total);
}

MapObjectItem* MapScene::create_item(size_t i) {
    const MapObject& obj = map_->objects()[i];
    if (!obj.data) return nullptr;
    const long long type = obj.type.value_or(0);
    MapObjectItem* result = nullptr;
    switch (obj.kind()) {
        case ObjectKind::Poi: {
            auto* item = new PoiItem(map_, i, styles_->poi_icon(type));
            addItem(item);
            item->add_label();
            result = item;
            break;
        }
        case ObjectKind::Polyline: {
            auto* item = new PolylineItem(map_, i, styles_->polyline_pen(type));
            addItem(item);
            result = item;
            break;
        }
        case ObjectKind::Polygon: {
            auto* item = new PolygonItem(map_, i, styles_->polygon_pen(type), QBrush(styles_->polygon_fill_colour(type)),
                                         styles_->polygon_z_value(type));
            addItem(item);
            result = item;
            break;
        }
        case ObjectKind::Basic:
            return nullptr;
    }
    result->set_map_level(map_level_);
    object_items_.push_back(result);
    items_by_object_[i] = result;
    return result;
}

void MapScene::set_map_level(int level) {
    if (level == map_level_ || level < 0 || level >= MAP_LEVELS) return;
    map_level_ = level;
    clearSelection();
    const int total = static_cast<int>(object_items_.size());
    emit progress(0, total);
    QElapsedTimer progress_timer;
    progress_timer.start();
    for (int i = 0; i < total; ++i) {
        object_items_[static_cast<size_t>(i)]->set_map_level(level);
        if (progress_timer.elapsed() > 100) {
            emit progress(i, total);
            QCoreApplication::processEvents(QEventLoop::ExcludeUserInputEvents);
            progress_timer.restart();
        }
    }
    emit progress(total, total);
}

void MapScene::set_viewer_scale(double scale) {
    bool was_ignoring = viewer_scale_ > IGNORE_TRANSFORMATION_TRESHOLD;
    viewer_scale_ = scale;
    bool ignoring = viewer_scale_ > IGNORE_TRANSFORMATION_TRESHOLD;
    if (was_ignoring != ignoring) apply_transformation_flags(ignoring);
}

namespace {
void apply_flag_recursive(QGraphicsItem* item, bool ignore) {
    if (auto* s = dynamic_cast<ScreenSized*>(item)) s->apply_transformation_flag(ignore);
    const QList<QGraphicsItem*> children = item->childItems();
    for (QGraphicsItem* child : children) apply_flag_recursive(child, ignore);
}
}  // namespace

void MapScene::apply_transformation_flags(bool ignore) {
    // scene->items() sortuje wszystkie elementy - przy setkach tysiecy to zbedny koszt
    for (MapObjectItem* item : object_items_) apply_flag_recursive(item->graphics_item(), ignore);
}

void MapScene::set_canvas_rectangle(const GeoBBox& bbox, const Projection& projection) {
    if (!bbox.valid) return;
    const double cor = 0.001;
    PointF start = projection.geo_to_canvas(bbox.N + cor, bbox.W - cor);
    PointF end = projection.geo_to_canvas(bbox.S - cor, bbox.E + cor);
    setSceneRect(start.x, start.y, end.x - start.x, end.y - start.y);
}

// ---------------------------------------------------------------- edycja
MapObjectItem* MapScene::item_for_object(size_t index) const {
    return index < items_by_object_.size() ? items_by_object_[index] : nullptr;
}

void MapScene::refresh_object(size_t index) {
    if (MapObjectItem* item = item_for_object(index)) item->refresh();
}

std::vector<MapObjectItem*> MapScene::selected_object_items() const {
    std::vector<MapObjectItem*> result;
    const QList<QGraphicsItem*> selected = selectedItems();
    for (QGraphicsItem* item : selected)
        if (auto* obj_item = dynamic_cast<MapObjectItem*>(item)) result.push_back(obj_item);
    std::sort(result.begin(), result.end(),
              [](const MapObjectItem* a, const MapObjectItem* b) { return a->object_index() < b->object_index(); });
    return result;
}

void MapScene::push_command(QUndoCommand* command) {
    if (undo_stack_) {
        undo_stack_->push(command);  // push wywoluje redo()
    } else {
        command->redo();
        delete command;
    }
}

void MapScene::move_objects(const std::vector<std::pair<MapObjectItem*, QPointF>>& moves) {
    if (!map_ || moves.empty()) return;
    QString text;
    if (moves.size() > 1)
        text = tr("Przesuń obiekty (%1)").arg(moves.size());
    else
        text = moves.front().first->graphics_item()->type() == PoiItemType ? tr("Przesuń POI") : tr("Przesuń obiekt");
    auto* command = new QUndoCommand(text);
    for (const auto& [item, delta] : moves) {
        const MapObject& obj = item->object();
        const int level = item->shown_data_level();
        if (level < 0 || !obj.data || delta.isNull()) {
            item->refresh();  // przesuniety element wraca na miejsce wynikajace z danych
            continue;
        }
        MapObject after = obj;
        after.data->translate_data_level(level, PointF{delta.x(), delta.y()});
        new ReplaceObjectCmd(this, item->object_index(), obj, std::move(after), text, command);
    }
    if (command->childCount() == 0) {
        delete command;
        return;
    }
    push_command(command);
}

void MapScene::delete_selected() {
    // jak w Pythonie: usuwanie obiektow tylko w trybie zaznaczania
    if (!map_ || tool_ != Tool::SelectObjects) return;
    std::vector<size_t> indexes;
    for (MapObjectItem* item : selected_object_items()) indexes.push_back(item->object_index());
    if (indexes.empty()) return;
    const QString text = indexes.size() == 1 ? tr("Usuń obiekt") : tr("Usuń obiekty (%1)").arg(indexes.size());
    push_command(new DeleteObjectsCmd(this, std::move(indexes), text));
}

void MapScene::reverse_selected_polylines() {
    if (!map_) return;
    // Python odwracal tylko biezacy poziom Data; tu wszystkie, zeby kierunek (DirIndicator, numeracja)
    // byl zgodny na kazdym poziomie.
    auto* command = new QUndoCommand(tr("Odwróć polilinię"));
    for (MapObjectItem* item : selected_object_items()) {
        if (item->graphics_item()->type() != PolylineItemType) continue;
        const MapObject& obj = item->object();
        if (!obj.data) continue;
        MapObject after = obj;
        const std::vector<int> levels = after.data->data_levels();
        for (int level : levels) after.data->reverse_poly(level);
        new ReplaceObjectCmd(this, item->object_index(), obj, std::move(after), command->text(), command);
    }
    if (command->childCount() == 0) {
        delete command;
        return;
    }
    push_command(command);
}


// ---------------------------------------------------------------- tryb edycji wezlow
void MapScene::set_tool(Tool tool) {
    tool_ = tool;
    update_decorations();
    emit tool_changed();
}

PolyItem* MapScene::poly_item(size_t index) const {
    MapObjectItem* item = item_for_object(index);
    return item ? dynamic_cast<PolyItem*>(item) : nullptr;
}

void MapScene::selection_changed() {
    std::vector<MapObjectItem*> order;
    for (MapObjectItem* item : selection_order_)
        if (item->graphics_item()->isSelected()) order.push_back(item);
    for (MapObjectItem* item : selected_object_items())
        if (std::find(order.begin(), order.end(), item) == order.end()) order.push_back(item);
    selection_order_ = std::move(order);
    update_decorations();
}

std::vector<MapObjectItem*> MapScene::selected_object_items_in_order() const {
    std::vector<MapObjectItem*> result;
    for (MapObjectItem* item : selection_order_)
        if (item->graphics_item()->isSelected()) result.push_back(item);
    return result;
}

void MapScene::update_decorations() {
    std::vector<PolyItem*> keep;
    for (PolyItem* item : decorated_) {
        if (tool_ == Tool::EditNodes && item->isSelected() && item->isVisible())
            keep.push_back(item);
        else
            item->undecorate();
    }
    decorated_ = std::move(keep);
    if (tool_ == Tool::EditNodes) {
        for (MapObjectItem* obj_item : selected_object_items()) {
            auto* item = dynamic_cast<PolyItem*>(obj_item);
            if (!item || !item->isVisible()) continue;
            if (!item->decorated()) item->decorate();
            if (std::find(decorated_.begin(), decorated_.end(), item) == decorated_.end()) decorated_.push_back(item);
        }
    }
    if (active_grip_) {
        PolyItem* item = poly_item(active_grip_->obj);
        if (!item || !item->decorated()) {
            active_grip_.reset();
            emit active_grip_changed();
        }
    }
}

void MapScene::grip_hovered(GripItem* grip, bool hovered) {
    if (hovered) {
        const bool changed = hovered_grip_ == nullptr;
        hovered_grip_ = grip;
        if (changed) emit grip_hover_changed(true);
    } else if (hovered_grip_ == grip) {
        hovered_grip_ = nullptr;
        emit grip_hover_changed(false);
    }
}

void MapScene::set_active_grip(size_t obj, int level, size_t poly, size_t node) {
    active_grip_ = GripRef{obj, level, poly, node};
    emit active_grip_changed();
}

void MapScene::replace_object(size_t obj, MapObject after, const QString& text) {
    if (!map_ || obj >= map_->objects().size()) return;
    push_command(new ReplaceObjectCmd(this, obj, map_->objects()[obj], std::move(after), text));
}

void MapScene::delete_object(size_t obj, const QString& text) {
    if (!map_ || obj >= map_->objects().size()) return;
    push_command(new DeleteObjectsCmd(this, {obj}, text));
}

std::optional<size_t> MapScene::replace_and_add(size_t obj, MapObject after, MapObject added, const QString& text) {
    if (!map_ || obj >= map_->objects().size()) return std::nullopt;
    added.id.reset();
    added.deleted = false;
    auto* command = new QUndoCommand(text);
    new ReplaceObjectCmd(this, obj, map_->objects()[obj], std::move(after), text, command);
    auto* add = new AddObjectCmd(this, std::move(added), text, command);
    push_command(command);
    return undo_stack_ ? add->index() : std::nullopt;
}

void MapScene::highlight_path(const QPainterPath& path, bool polygon) {
    // jak highlight_element w Pythonie: ciemnoczerwona polprzezroczysta sciezka nad obiektami
    delete highlight_;
    highlight_ = nullptr;
    if (path.isEmpty()) return;
    highlight_ = new QGraphicsPathItem(path);
    QPen pen(Qt::darkRed);
    pen.setWidth(5);
    pen.setCosmetic(true);
    highlight_->setPen(pen);
    if (polygon) highlight_->setBrush(QBrush(Qt::darkRed));
    highlight_->setZValue(HIGHLIGHTED_POLY_Z_VAL);
    highlight_->setOpacity(0.5);
    addItem(highlight_);
    for (QGraphicsView* view : views()) view->ensureVisible(highlight_);
}

void MapScene::request_node_move(size_t obj, int level, size_t poly, size_t node, const QPointF& pos) {
    QTimer::singleShot(0, this, [=] { move_node(obj, level, poly, node, pos); });
}

void MapScene::request_node_removal(size_t obj, int level, size_t poly, size_t node) {
    QTimer::singleShot(0, this, [=] { remove_node(obj, level, poly, node); });
}

void MapScene::request_split(size_t obj, int level, size_t poly, size_t node) {
    QTimer::singleShot(0, this, [=] { split_polyline(obj, level, poly, node); });
}

bool MapScene::move_node(size_t obj, int level, size_t poly, size_t node, const QPointF& pos) {
    if (!map_ || obj >= map_->objects().size() || !map_->objects()[obj].data) return false;
    MapObject after = map_->objects()[obj];
    try {
        after.data->update_node_coordinates(level, poly, static_cast<long>(node), PointF{pos.x(), pos.y()});
    } catch (const MpError&) {
        refresh_object(obj);  // uchwyt wraca na miejsce wezla
        return false;
    }
    push_command(new ReplaceObjectCmd(this, obj, map_->objects()[obj], std::move(after), tr("Przesuń węzeł")));
    return true;
}

bool MapScene::remove_node(size_t obj, int level, size_t poly, size_t node) {
    PolyItem* item = poly_item(obj);
    if (!map_ || !item || !map_->objects()[obj].data) return false;
    const auto* polys = map_->objects()[obj].data->polys_for_data_level(level);
    if (!polys || poly >= polys->size() || node >= (*polys)[poly].size()) return false;
    // polilinia musi miec co najmniej 2 wezly, polygon 3
    if ((*polys)[poly].size() <= item->min_nodes()) return false;
    MapObject after = map_->objects()[obj];
    after.data->delete_node_at_position(level, poly, static_cast<long>(node));
    push_command(new ReplaceObjectCmd(this, obj, map_->objects()[obj], std::move(after), tr("Usuń węzeł")));
    return true;
}

bool MapScene::insert_node(size_t obj, int level, size_t poly, size_t index, const QPointF& pos) {
    if (!map_ || obj >= map_->objects().size() || !map_->objects()[obj].data) return false;
    const auto* polys = map_->objects()[obj].data->polys_for_data_level(level);
    if (!polys || poly >= polys->size() || index > (*polys)[poly].size()) return false;
    MapObject after = map_->objects()[obj];
    after.data->insert_node_at_position(level, poly, static_cast<long>(index), pos.x(), pos.y());
    push_command(new ReplaceObjectCmd(this, obj, map_->objects()[obj], std::move(after), tr("Dodaj węzeł")));
    return true;
}

bool MapScene::insert_node_at(const QPointF& scene_pos) {
    if (tool_ != Tool::EditNodes) return false;
    for (PolyItem* item : decorated_) {
        auto ins = item->node_insertion(scene_pos, false, true);
        if (ins) return insert_node(item->object_index(), item->shown_data_level(), ins->poly_num, ins->index,
                                    ins->position);
    }
    return false;
}

bool MapScene::insert_node_on_segment(PolyItem* item, const QPointF& scene_pos, double max_distance) {
    if (!item || !item->decorated()) return false;
    auto ins = item->node_insertion(scene_pos, true, false);
    if (!ins || ins->distance > max_distance) return false;
    return insert_node(item->object_index(), item->shown_data_level(), ins->poly_num, ins->index, ins->position);
}

bool MapScene::split_at_active_grip() {
    if (!active_grip_) return false;
    const GripRef g = *active_grip_;
    return split_polyline(g.obj, g.level, g.poly, g.node);
}

bool MapScene::split_polyline(size_t obj, int level, size_t poly, size_t node) {
    if (!map_ || obj >= map_->objects().size()) return false;
    const MapObject& orig = map_->objects()[obj];
    if (orig.kind() != ObjectKind::Polyline || !orig.data) return false;
    std::vector<DataX> parts = orig.data->split_data_x(level, poly, static_cast<long>(node));
    if (parts.size() != 2) return false;
    MapObject first = orig;
    first.data = std::move(parts[0]);
    // druga czesc: nowy obiekt z tymi samymi wlasciwosciami (jak w Pythonie)
    MapObject second = orig;
    second.id.reset();
    second.deleted = false;
    parts[1].recalculate_bounding_box();
    second.bbox = parts[1].obj_bounding_box();
    second.data = std::move(parts[1]);
    const QString text = tr("Podziel polilinię");
    auto* command = new QUndoCommand(text);
    new ReplaceObjectCmd(this, obj, orig, std::move(first), text, command);
    new AddObjectCmd(this, std::move(second), text, command);
    push_command(command);
    return true;
}

size_t MapScene::add_object(MapObject obj) {
    obj.id.reset();
    MapObject& added = map_->add_map_object(std::move(obj));
    const size_t index = *added.id;
    if (items_by_object_.size() < map_->objects().size()) items_by_object_.resize(map_->objects().size(), nullptr);
    create_item(index);
    return index;
}

void MapScene::merge_objects(const std::vector<size_t>& indexes, DataX merged, const QString& text) {
    if (!map_ || indexes.size() < 2) return;
    const size_t first = indexes.front();
    MapObject after = map_->objects()[first];
    after.bbox = merged.obj_bounding_box();
    after.data = std::move(merged);
    auto* command = new QUndoCommand(text);
    new ReplaceObjectCmd(this, first, map_->objects()[first], std::move(after), text, command);
    new DeleteObjectsCmd(this, std::vector<size_t>(indexes.begin() + 1, indexes.end()), text, command);
    push_command(command);
    clearSelection();
    if (MapObjectItem* item = item_for_object(first)) item->graphics_item()->setSelected(true);
}


// ---------------------------------------------------------------- schowek
QMimeData* MapScene::copy_selected(const QPointF& reference) const {
    if (!map_) return nullptr;
    QJsonArray records;
    QString text;
    const QString position = QString("MouseScenePos=%1,%2").arg(reference.x(), 0, 'g', 17).arg(reference.y(), 0, 'g', 17);
    for (MapObjectItem* item : selected_object_items()) {
        const MapObject& obj = item->object();
        if (obj.deleted) continue;
        QJsonArray record;
        record.append(position);
        for (const std::string& line : obj.to_mp_record(map_->precision())) {
            const QString l = QString::fromStdString(encoding::cp1250_to_utf8(line));
            record.append(l);
            text += l + '\n';
        }
        record.append(QStringLiteral("[END]"));
        text += QStringLiteral("[END]\n\n");
        records.append(record);
    }
    if (records.isEmpty()) return nullptr;
    auto* mime = new QMimeData;
    mime->setData(QStringLiteral("application/json"), QJsonDocument(records).toJson(QJsonDocument::Compact));
    mime->setText(text);
    return mime;
}

int MapScene::paste(const QMimeData* mime, std::optional<QPointF> mouse) {
    if (!map_ || !mime) return 0;
    // rekordy: (MouseScenePos, linie w UTF-8)
    std::vector<std::pair<std::optional<QPointF>, QStringList>> records;
    if (mime->hasFormat(QStringLiteral("application/json"))) {
        const QJsonDocument doc = QJsonDocument::fromJson(mime->data(QStringLiteral("application/json")));
        for (const QJsonValue& rec_value : doc.array()) {
            QStringList lines;
            for (const QJsonValue& line : rec_value.toArray()) lines << line.toString();
            std::optional<QPointF> ref;
            if (!lines.isEmpty() && lines.front().startsWith(QLatin1String("MouseScenePos="))) {
                const QStringList xy = lines.takeFirst().mid(14).split(',');
                bool ok_x = false, ok_y = false;
                if (xy.size() == 2) {
                    const QPointF p(xy[0].toDouble(&ok_x), xy[1].toDouble(&ok_y));
                    if (ok_x && ok_y) ref = p;
                }
            }
            records.emplace_back(ref, lines);
        }
    } else if (mime->hasText()) {
        // tekst rekordow mp (np. z edytora): obiekty w oryginalnym miejscu
        for (const QString& chunk : mime->text().split(QStringLiteral("[END]"))) {
            if (!chunk.trimmed().isEmpty()) records.emplace_back(std::nullopt, chunk.split('\n'));
        }
    }

    QString text;
    std::vector<MapObject> objects;
    for (const auto& [ref, lines] : records) {
        std::vector<std::string> cp1250;
        for (const QString& line : lines) cp1250.push_back(encoding::utf8_to_cp1250(line.toStdString()));
        std::optional<MapObject> obj = map_->object_from_record(cp1250);
        if (!obj) continue;
        if (ref && mouse) {
            // Python przesuwal tylko pokazywany poziom; tu wszystkie, zeby obiekt nie rozjechal sie miedzy poziomami
            const QPointF delta = *mouse - *ref;
            const std::vector<int> levels = obj->data->data_levels();
            for (int level : levels) obj->data->translate_data_level(level, PointF{delta.x(), delta.y()});
            obj->data->recalculate_bounding_box();
            obj->bbox = obj->data->obj_bounding_box();
        }
        switch (obj->kind()) {
            case ObjectKind::Poi: text = tr("Wklej POI"); break;
            case ObjectKind::Polyline: text = tr("Wklej Polyline"); break;
            default: text = tr("Wklej Polygon"); break;
        }
        objects.push_back(std::move(*obj));
    }
    if (objects.empty()) return 0;
    if (objects.size() > 1) text = tr("Wklej obiekty (%1)").arg(objects.size());
    auto* command = new QUndoCommand(text);
    std::vector<AddObjectCmd*> adds;
    for (MapObject& obj : objects) adds.push_back(new AddObjectCmd(this, std::move(obj), text, command));
    push_command(command);
    // wklejone obiekty zostaja zaznaczone (wskazniki do komend sa wazne, dopoki komenda jest na stosie)
    clearSelection();
    for (AddObjectCmd* add : adds)
        if (add->index())
            if (MapObjectItem* item = item_for_object(*add->index())) item->graphics_item()->setSelected(true);
    return static_cast<int>(adds.size());
}


// ---------------------------------------------------------------- tworzenie obiektow
long long MapScene::last_used_type(ObjectKind kind) const { return last_used_type_[static_cast<int>(kind)]; }

void MapScene::set_last_used_type(ObjectKind kind, long long type) { last_used_type_[static_cast<int>(kind)] = type; }

std::optional<size_t> MapScene::create_object(ObjectKind kind, const std::vector<QPointF>& nodes,
                                              const std::vector<std::string>& fields,
                                              const std::vector<std::string>& comments) {
    if (!map_ || nodes.empty() || kind == ObjectKind::Basic) return std::nullopt;
    // Jak w Pythonie: rekord z Type i Data0 we wspolrzednych geograficznych. 10 miejsc po przecinku, zeby nie
    // podniesc precyzji zapisu calej mapy (cyfry powyzej 6 nie wplywaja na precyzje); zapis uzywa precyzji mapy.
    std::string data = "Data0=";
    const Projection& projection = map_->projection();
    for (size_t i = 0; i < nodes.size(); ++i) {
        GeoPoint g;
        try {
            g = projection.canvas_to_geo(nodes[i].x(), nodes[i].y());
        } catch (const std::exception&) {
            return std::nullopt;
        }
        if (i) data += ',';
        data += QString::asprintf("(%.10f,%.10f)", g.latitude, g.longitude).toStdString();
    }
    std::vector<std::string> lines;
    for (const std::string& c : comments) lines.push_back(";" + c);
    lines.push_back(object_kind_section(kind));
    lines.push_back(QString::asprintf("Type=0x%llx", last_used_type(kind)).toStdString());
    lines.insert(lines.end(), fields.begin(), fields.end());
    lines.push_back(data);
    std::optional<MapObject> obj = map_->object_from_record(lines);
    if (!obj) return std::nullopt;
    QString text;
    switch (kind) {
        case ObjectKind::Poi: text = tr("Utwórz POI"); break;
        case ObjectKind::Polyline: text = tr("Utwórz Polyline"); break;
        default: text = tr("Utwórz Polygon"); break;
    }
    auto* command = new AddObjectCmd(this, std::move(*obj), text);
    push_command(command);
    const std::optional<size_t> index = undo_stack_ ? command->index() : std::nullopt;
    // po utworzeniu obiektu narzedzie zaznaczania i zaznaczony nowy obiekt
    set_tool(Tool::SelectObjects);
    clearSelection();
    if (index)
        if (MapObjectItem* item = item_for_object(*index)) item->graphics_item()->setSelected(true);
    return index;
}

// ---------------------------------------------------------------- przyciaganie
std::optional<QPointF> MapScene::closest_node(const QPointF& pos, double max_distance,
                                              const MapObjectItem* excluded) const {
    std::optional<QPointF> best;
    double best_distance = max_distance;
    const QRectF area(pos.x() - max_distance, pos.y() - max_distance, 2 * max_distance, 2 * max_distance);
    const QList<QGraphicsItem*> under = items(area);
    auto consider = [&](const QPointF& node) {
        const QPointF d = node - pos;
        const double distance = std::hypot(d.x(), d.y());
        if (distance <= best_distance) {
            best_distance = distance;
            best = node;
        }
    };
    std::vector<QPointF> points;
    for (QGraphicsItem* graphics : under) {
        if (!graphics->isVisible()) continue;
        if (graphics->type() == GpsTrackItemType || graphics->type() == GpsWaypointItemType) {
            // punkty sladow GPS i waypointy
            if (auto* source = dynamic_cast<SnapSource*>(graphics)) {
                points.clear();
                source->snap_points(points);
                for (const QPointF& p : points) consider(p);
            }
            continue;
        }
        if (graphics->type() != PolylineItemType && graphics->type() != PolygonItemType) continue;
        auto* item = static_cast<PolyItem*>(graphics);
        if (item == excluded || item->object().deleted) continue;
        for (const auto& poly : item->shown_nodes())
            for (const QPointF& node : poly) consider(node);
    }
    return best;
}

void MapScene::show_snap_indicator(std::optional<QPointF> pos) {
    if (!pos) {
        if (snap_indicator_) snap_indicator_->setVisible(false);
        return;
    }
    if (!snap_indicator_) {
        // jak closest_node_circle_definition w Pythonie
        snap_indicator_ = new QGraphicsEllipseItem(-10, -10, 20, 20);
        snap_indicator_->setZValue(150);
        snap_indicator_->setPen(QPen(QColor("blue")));
        snap_indicator_->setBrush(QBrush(QColor("blue")));
        snap_indicator_->setFlag(QGraphicsItem::ItemIgnoresTransformations, true);
        snap_indicator_->setOpacity(0.5);
        snap_indicator_->setAcceptedMouseButtons(Qt::NoButton);
        addItem(snap_indicator_);
    }
    snap_indicator_->setPos(*pos);
    snap_indicator_->setVisible(true);
}

bool MapScene::snap_indicator_visible() const { return snap_indicator_ && snap_indicator_->isVisible(); }

}  // namespace pwm::gui
