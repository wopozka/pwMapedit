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
#include <cmath>

#include "commands.hpp"
#include "line_crossings.hpp"
#include "map_items.hpp"
#include "misc.hpp"
#include "polygon_ops.hpp"
#include "map_styles.hpp"

namespace pwm::gui {

MapScene::MapScene(QObject* parent) : QGraphicsScene(parent) {
    // Indeks BSP o stalej glebokosci (automatyczna glebokosc Qt dla duzych map wychodzi 5 albo 17 - za malo
    // albo za duzo). Zmiana poziomu mapy nie zmienia geometrii elementow (element na poziom Data obiektu,
    // przelaczana jest tylko widocznosc), wiec indeks nie jest przy niej przebudowywany.
    // Glebokosc jest zapisana w obiekcie indeksu - ustawiac po kazdym setItemIndexMethod.
    setItemIndexMethod(QGraphicsScene::BspTreeIndex);
    setBspTreeDepth(SCENE_BSP_TREE_DEPTH);
    connect(this, &QGraphicsScene::selectionChanged, this, &MapScene::selection_changed);
    // jeden element na cala mape, przetrwa clear_map(); niewidoczny (wylaczony) nic nie kosztuje
    road_casing_ = new RoadCasingLayer(this);
    road_casing_->setVisible(false);
    add_persistent_item(road_casing_);
    annotation_layer_ = new AnnotationLayer(this);
    add_persistent_item(annotation_layer_);
    poi_icon_layer_ = new PoiIconLayer(this);
    add_persistent_item(poi_icon_layer_);
}

void MapScene::update_annotations(MapObjectItem* item) {
    if (rebuilding_all_) return;
    QGraphicsItem* g = item->graphics_item();
    const QRectF reference = g->sceneBoundingRect();
    const double margin = AnnotationLayer::MARGIN_PX / std::max(viewer_scale_, 1e-9);
    update(reference.adjusted(-margin, -margin, margin, margin));
}

bool MapScene::road_casing() const { return road_casing_->isVisible(); }

void MapScene::set_road_casing(bool on) { road_casing_->setVisible(on); }

void MapScene::clear_map() {
    clearSelection();  // zdejmuje tez uchwyty (selection_changed)
    selection_order_.clear();
    decorated_.clear();
    active_grip_.reset();
    highlight_path(QPainterPath(), false);
    delete snap_indicator_;
    snap_indicator_ = nullptr;
    end_rotation();
    delete rotation_marker_;
    rotation_marker_ = nullptr;
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
    items_by_object_.assign(objects.size(), {});
    emit progress(0, total);
    QElapsedTimer progress_timer;
    progress_timer.start();
    rebuilding_all_ = true;
    for (size_t i = 0; i < objects.size(); ++i) {
        if (!objects[i].deleted) create_items(i);
        if (progress_timer.elapsed() > 100) {
            emit progress(static_cast<int>(i), total);
            QCoreApplication::processEvents(QEventLoop::ExcludeUserInputEvents);
            progress_timer.restart();
        }
    }
    rebuilding_all_ = false;
    update();
    emit progress(total, total);
}

MapObjectItem* MapScene::create_items(size_t i) {
    const MapObject& obj = map_->objects()[i];
    if (!obj.data) return nullptr;
    MapObjectItem* first = nullptr;
    for (int level : object_item_levels(obj)) {
        MapObjectItem* item = create_item(i, level);
        if (!first) first = item;
    }
    return first;
}

MapObjectItem* MapScene::create_item(size_t i, int data_level) {
    const MapObject& obj = map_->objects()[i];
    const long long type = obj.type.value_or(0);
    MapObjectItem* result = nullptr;
    switch (obj.kind()) {
        case ObjectKind::Poi: {
            auto* item = new PoiItem(map_, i, data_level, styles_->poi_icon(type));
            addItem(item);
            item->add_label();
            result = item;
            break;
        }
        case ObjectKind::Polyline: {
            auto* item = new PolylineItem(map_, i, data_level, styles_->polyline_pen(type));
            addItem(item);
            item->rebuild();
            result = item;
            break;
        }
        case ObjectKind::Polygon: {
            auto* item = new PolygonItem(map_, i, data_level, styles_->polygon_pen(type),
                                         QBrush(styles_->polygon_fill_colour(type)), styles_->polygon_z_value(type));
            addItem(item);
            item->rebuild();
            result = item;
            break;
        }
        case ObjectKind::Basic:
            return nullptr;
    }
    result->set_map_level(map_level_);
    object_items_.push_back(result);
    auto& items = items_by_object_[i];
    auto pos = std::find_if(items.begin(), items.end(),
                            [&](const MapObjectItem* it) { return it->data_level() > data_level; });
    items.insert(pos, result);
    return result;
}

void MapScene::remove_item(MapObjectItem* item) {
    auto erase = [item](auto& v) {
        auto it = std::find(v.begin(), v.end(), item);
        if (it != v.end()) v.erase(it);
    };
    erase(object_items_);
    erase(selection_order_);
    erase(items_by_object_[item->object_index()]);
    if (auto* poly = dynamic_cast<PolyItem*>(item)) {
        erase(decorated_);
        poly->undecorate();
    }
    QGraphicsItem* g = item->graphics_item();
    g->setSelected(false);
    update_annotations(item);
    delete g;  // usuwa tez ze sceny
}

void MapScene::set_transparent_polygons(bool transparent) {
    if (transparent_polygons_ == transparent) return;
    transparent_polygons_ = transparent;
    update();
}

void MapScene::set_map_level(int level) {
    if (level == map_level_ || level < 0 || level >= MAP_LEVELS) return;
    map_level_ = level;
    clearSelection();
    const int total = static_cast<int>(object_items_.size());
    emit progress(0, total);
    QElapsedTimer progress_timer;
    progress_timer.start();
    rebuilding_all_ = true;
    for (int i = 0; i < total; ++i) {
        object_items_[static_cast<size_t>(i)]->set_map_level(level);
        if (progress_timer.elapsed() > 100) {
            emit progress(i, total);
            QCoreApplication::processEvents(QEventLoop::ExcludeUserInputEvents);
            progress_timer.restart();
        }
    }
    rebuilding_all_ = false;
    update();
    emit progress(total, total);
}

void MapScene::set_viewer_scale(double scale) { viewer_scale_ = scale; }

void MapScene::set_canvas_rectangle(const GeoBBox& bbox, const Projection& projection) {
    if (!bbox.valid) return;
    const double cor = 0.001;
    PointF start = projection.geo_to_canvas(bbox.N + cor, bbox.W - cor);
    PointF end = projection.geo_to_canvas(bbox.S - cor, bbox.E + cor);
    setSceneRect(start.x, start.y, end.x - start.x, end.y - start.y);
    road_casing_->set_rect(sceneRect());
    annotation_layer_->set_rect(sceneRect());
    poi_icon_layer_->set_rect(sceneRect());
}

// ---------------------------------------------------------------- edycja
MapObjectItem* MapScene::item_for_object(size_t index) const {
    if (index >= items_by_object_.size()) return nullptr;
    const auto& items = items_by_object_[index];
    for (MapObjectItem* item : items)
        if (item->graphics_item()->isVisible()) return item;
    return items.empty() ? nullptr : items.front();
}

const std::vector<MapObjectItem*>& MapScene::items_for_object(size_t index) const {
    static const std::vector<MapObjectItem*> none;
    return index < items_by_object_.size() ? items_by_object_[index] : none;
}

void MapScene::refresh_object(size_t index) {
    if (map_ && index < items_by_object_.size() && !items_by_object_[index].empty()) {
        // elementy dopasowane do poziomow Data obiektu: zbedne usuwane, istniejace przebudowane, brakujace dodane
        const std::vector<int> levels = object_item_levels(map_->objects()[index]);
        const std::vector<MapObjectItem*> current = items_by_object_[index];
        for (MapObjectItem* item : current) {
            if (std::find(levels.begin(), levels.end(), item->data_level()) == levels.end())
                remove_item(item);
            else
                item->refresh();
        }
        for (int level : levels) {
            const auto& items = items_by_object_[index];
            const bool exists = std::any_of(items.begin(), items.end(),
                                            [level](const MapObjectItem* it) { return it->data_level() == level; });
            if (!exists) create_item(index, level);
        }
    }
    // Aktywny wezel jest pamietany numerem. Po zmianie liczby wezlow (usuniecie wezla, undo dodania) numer moze
    // wskazywac poza linie - panel wlasciwosci czytalby nieistniejacy wezel (MpError i zamkniecie programu).
    if (active_grip_ && active_grip_->obj == index && !active_grip_valid()) {
        active_grip_.reset();
        emit active_grip_changed();
    }
}

bool MapScene::active_grip_valid() const {
    if (!active_grip_ || !map_ || active_grip_->obj >= map_->objects().size()) return false;
    const MapObject& obj = map_->objects()[active_grip_->obj];
    if (obj.deleted || !obj.data) return false;
    const auto* polys = obj.data->polys_for_data_level(active_grip_->level);
    return polys && active_grip_->poly < polys->size() && active_grip_->node < (*polys)[active_grip_->poly].size();
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
    end_rotation();
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
    // inny obiekt w edycji - nastepny obrot to nowy gest; ten sam obiekt (przebudowa po zabku obrotu) - bez zmian
    if (rotation_) {
        MapObjectItem* rotated = item_for_object(rotation_->obj);
        if (!rotated || !rotated->graphics_item()->isSelected()) end_rotation();
    }
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
    const std::optional<size_t> previous = active_grip_ ? std::optional(active_grip_->obj) : std::nullopt;
    active_grip_ = GripRef{obj, level, poly, node};
    if (previous && *previous != obj) update_grips(*previous);
    update_grips(obj);
    emit active_grip_changed();
}

void MapScene::update_grips(size_t obj) const {
    if (PolyItem* item = poly_item(obj))
        for (GripItem* grip : item->grips()) grip->update();
}

std::optional<GripRef> MapScene::neighbour_grip(int delta) const {
    if (!active_grip_valid()) return std::nullopt;
    const GripRef g = *active_grip_;
    const auto& polys = *map_->objects()[g.obj].data->polys_for_data_level(g.level);
    if (delta < 0) {
        if (g.node > 0) return GripRef{g.obj, g.level, g.poly, g.node - 1};
        for (size_t p = g.poly; p-- > 0;)
            if (!polys[p].empty()) return GripRef{g.obj, g.level, p, polys[p].size() - 1};
    } else if (delta > 0) {
        if (g.node + 1 < polys[g.poly].size()) return GripRef{g.obj, g.level, g.poly, g.node + 1};
        for (size_t p = g.poly + 1; p < polys.size(); ++p)
            if (!polys[p].empty()) return GripRef{g.obj, g.level, p, 0};
    }
    return std::nullopt;
}

void MapScene::activate_grip(const GripRef& grip) {
    set_active_grip(grip.obj, grip.level, grip.poly, grip.node);
    PolyItem* item = poly_item(grip.obj);
    if (!item) return;
    const auto nodes = item->shown_nodes();
    if (grip.poly >= nodes.size() || grip.node >= nodes[grip.poly].size()) return;
    // ensureVisible przewija tylko wtedy, gdy wezla (z marginesem w pikselach) nie widac
    const QRectF point(nodes[grip.poly][grip.node], QSizeF(0, 0));
    for (QGraphicsView* view : views()) view->ensureVisible(point, 60, 60);
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

QString MapScene::subtract_selected_polygons(bool delete_second, bool* changed) {
    if (changed) *changed = false;
    const std::vector<MapObjectItem*> selected = selected_object_items_in_order();
    if (!map_ || selected.size() != 2 || selected[0]->object().kind() != ObjectKind::Polygon ||
        selected[1]->object().kind() != ObjectKind::Polygon)
        return tr("Zaznacz dwa polygony (Ctrl+klik): od pierwszego zaznaczonego zostanie odjęty drugi.");
    auto* a = static_cast<PolyItem*>(selected[0]);
    auto* b = static_cast<PolyItem*>(selected[1]);
    const int level = a->shown_data_level();
    if (level < 0 || b->shown_data_level() < 0) return tr("Polygony nie mają danych na oglądanym poziomie.");
    // pokazywany poziom obu polygonow (to, co widac na mapie); pierscienie bez powtorzonego punktu zamykajacego
    auto rings = [](const PolyItem* item) {
        std::vector<geom::Ring> out;
        for (const auto& poly : item->shown_nodes()) {
            geom::Ring ring;
            for (const QPointF& p : poly) ring.push_back(PointF{p.x(), p.y()});
            if (ring.size() > 1 && ring.front() == ring.back()) ring.pop_back();
            out.push_back(std::move(ring));
        }
        return out;
    };
    const geom::SubtractResult result = geom::subtract(rings(a), rings(b));
    if (result.status == geom::SubtractResult::Status::NoOverlap)
        return tr("Polygony się nie nakładają (poziom Data%1) - nic nie zmieniono.").arg(level);
    if (result.status == geom::SubtractResult::Status::Empty)
        return tr("Drugi polygon pokrywa cały pierwszy - nic nie zmieniono.");

    const size_t a_index = a->object_index(), b_index = b->object_index();
    MapObject after = a->object();
    std::vector<Poly> polys;
    for (const geom::Ring& ring : result.rings) {
        Poly poly;
        for (const PointF& p : ring) poly.emplace_back(p.x, p.y);
        polys.push_back(std::move(poly));
    }
    after.data->set_level_polys(level, std::move(polys));
    after.bbox = after.data->obj_bounding_box();
    const QString text = delete_second ? tr("Odejmij polygony i usuń drugi") : tr("Odejmij polygony");
    auto* command = new QUndoCommand(text);
    new ReplaceObjectCmd(this, a_index, map_->objects()[a_index], std::move(after), text, command);
    if (delete_second) new DeleteObjectsCmd(this, {b_index}, text, command);
    push_command(command);
    clearSelection();
    if (MapObjectItem* item = item_for_object(a_index)) item->graphics_item()->setSelected(true);
    if (changed) *changed = true;
    return tr("Odjęto polygony na poziomie Data%1: pierwszy ma teraz %2 część(i).").arg(level).arg(result.rings.size());
}

bool MapScene::has_selected(ObjectKind kind) const {
    for (MapObjectItem* item : selected_object_items())
        if (item->object().kind() == kind) return true;
    return false;
}

QString MapScene::add_viaduct_pois(bool* changed) {
    if (changed) *changed = false;
    if (!map_) return {};
    std::vector<PolyItem*> lines;
    for (MapObjectItem* item : selected_object_items())
        if (item->object().kind() == ObjectKind::Polyline)
            if (auto* poly = dynamic_cast<PolyItem*>(item)) lines.push_back(poly);
    if (lines.size() < 2)
        return tr("Zaznacz co najmniej dwie drogi (Ctrl + klik) – bojki wiadukt stawiane są w miejscach ich przecięć.");

    // przeciecia kazdej pary (wspolrzedne sceny, ok. 0,6 m na jednostke - punkty blizsze niz 1 sa laczone)
    const double merge = 1.0;
    std::vector<std::vector<LinePart>> parts;
    for (PolyItem* item : lines) {
        std::vector<LinePart> item_parts;
        for (const auto& nodes : item->shown_nodes()) {
            LinePart part;
            for (const QPointF& p : nodes) part.push_back(PointF{p.x(), p.y()});
            item_parts.push_back(std::move(part));
        }
        parts.push_back(std::move(item_parts));
    }
    std::vector<PointF> crossings;
    for (size_t i = 0; i < parts.size(); ++i)
        for (size_t j = i + 1; j < parts.size(); ++j)
            for (const PointF& p : line_crossings(parts[i], parts[j], merge)) {
                bool known = false;
                for (const PointF& c : crossings) known = known || std::hypot(c.x - p.x, c.y - p.y) < merge;
                if (!known) crossings.push_back(p);
            }
    if (crossings.empty()) return tr("Nie znaleziono przecięć zaznaczonych dróg.");

    size_t skipped = 0;
    const int added = add_marker_pois(VIADUCT_POI_TYPE, crossings, merge, tr("Dodaj bojki wiadukt (%1)"), &skipped);
    if (added == 0) return tr("Wszystkie przecięcia (%1) mają już POI wiadukt.").arg(crossings.size());
    if (changed) *changed = true;
    QString result = tr("Dodano bojki wiadukt: %1").arg(added);
    if (skipped) result += tr(" (pominięto %1 – POI wiadukt już tam jest)").arg(skipped);
    return result;
}

int MapScene::add_marker_pois(long long type, const std::vector<PointF>& points, double distance,
                              const QString& text, size_t* skipped) {
    // punkty, przy ktorych stoi juz POI tego typu, sa pomijane (ponowne uzycie nie dubluje POI)
    std::vector<PointF> existing;
    for (const MapObject& obj : map_->objects()) {
        if (obj.deleted || obj.kind() != ObjectKind::Poi || obj.type.value_or(-1) != type || !obj.data) continue;
        for (const auto& level : obj.data->raw_polys())
            for (const Poly& poly : level)
                for (const Node& n : poly) existing.push_back(n.pos());
    }
    const Projection& projection = map_->projection();
    auto* command = new QUndoCommand;
    for (const PointF& p : points) {
        bool exists = false;
        for (const PointF& e : existing) exists = exists || std::hypot(e.x - p.x, e.y - p.y) < distance;
        if (exists) {
            if (skipped) ++*skipped;
            continue;
        }
        GeoPoint g;
        try {
            g = projection.canvas_to_geo(p.x, p.y);
        } catch (const std::exception&) {
            continue;
        }
        // 10 miejsc po przecinku jak create_object - zapis i tak uzywa precyzji mapy
        std::optional<MapObject> poi = map_->object_from_record(
            {object_kind_section(ObjectKind::Poi), QString::asprintf("Type=0x%llx", type).toStdString(),
             QString::asprintf("Data0=(%.10f,%.10f)", g.latitude, g.longitude).toStdString()});
        if (poi) new AddObjectCmd(this, std::move(*poi), QString(), command);
    }
    const int added = command->childCount();
    if (added == 0) {
        delete command;
        return 0;
    }
    command->setText(text.arg(added));
    push_command(command);
    return added;
}

QString MapScene::add_dead_end_pois(bool* changed) {
    if (changed) *changed = false;
    if (!map_) return {};
    std::vector<PolyItem*> lines;
    for (MapObjectItem* item : selected_object_items())
        if (item->object().kind() == ObjectKind::Polyline)
            if (auto* poly = dynamic_cast<PolyItem*>(item)) lines.push_back(poly);
    if (lines.empty()) return tr("Zaznacz co najmniej jedną drogę.");

    // Konce czesci zaznaczonych linii (pokazywany poziom); linia zamknieta (np. rondo) nie ma koncow.
    struct End {
        PointF pos;
        size_t obj;
        size_t part;
    };
    std::vector<End> ends;
    for (PolyItem* item : lines) {
        const int level = item->shown_data_level();
        const auto* polys = item->object().data ? item->object().data->polys_for_data_level(level) : nullptr;
        if (!polys) continue;
        for (size_t part = 0; part < polys->size(); ++part) {
            const Poly& poly = (*polys)[part];
            if (poly.size() < 2 || poly.front().pos() == poly.back().pos()) continue;
            ends.push_back({poly.front().pos(), item->object_index(), part});
            ends.push_back({poly.back().pos(), item->object_index(), part});
        }
    }
    // Koniec jest polaczony, gdy w tym samym miejscu jest wezel innej drogi (dowolny wezel, pokazywany poziom)
    // albo innej czesci tej samej linii. Wezly porownywane z tolerancja 0,01 jednostki (ok. 6 mm).
    const double same = 0.01;
    std::vector<bool> connected(ends.size(), false);
    QRectF area;
    for (const End& e : ends) area = area.united(QRectF(e.pos.x - same, e.pos.y - same, 2 * same, 2 * same));
    for (MapObjectItem* item : object_items_) {
        QGraphicsItem* g = item->graphics_item();
        if (g->type() != PolylineItemType || !g->isVisible()) continue;
        const MapObject& obj = item->object();
        if (!obj.data || !MapStyles::is_road(obj.type.value_or(-1))) continue;
        if (!g->sceneBoundingRect().intersects(area)) continue;  // szybkie odrzucenie dalekich drog
        const auto* polys = obj.data->polys_for_data_level(item->shown_data_level());
        if (!polys) continue;
        for (size_t part = 0; part < polys->size(); ++part)
            for (const Node& n : (*polys)[part])
                for (size_t k = 0; k < ends.size(); ++k) {
                    if (connected[k] || (ends[k].obj == item->object_index() && ends[k].part == part)) continue;
                    if (std::hypot(n.x() - ends[k].pos.x, n.y() - ends[k].pos.y) < same) connected[k] = true;
                }
    }
    std::vector<PointF> dead_ends;
    for (size_t k = 0; k < ends.size(); ++k)
        if (!connected[k]) dead_ends.push_back(ends[k].pos);
    if (dead_ends.empty()) return tr("Nie znaleziono ślepych końców – każdy koniec zaznaczonych dróg łączy się z inną drogą.");

    size_t skipped = 0;
    const int added = add_marker_pois(DEAD_END_POI_TYPE, dead_ends, 1.0, tr("Dodaj bojki ślepy (%1)"), &skipped);
    if (added == 0) return tr("Wszystkie ślepe końce (%1) mają już POI ślepy.").arg(dead_ends.size());
    if (changed) *changed = true;
    QString result = tr("Dodano bojki ślepy: %1").arg(added);
    if (skipped) result += tr(" (pominięto %1 – POI ślepy już tam jest)").arg(skipped);
    return result;
}

QString MapScene::convert_selected(ObjectKind from, bool* changed) {
    if (changed) *changed = false;
    if (!map_ || (from != ObjectKind::Polygon && from != ObjectKind::Polyline)) return {};
    const bool to_polyline = from == ObjectKind::Polygon;
    const ObjectKind to = to_polyline ? ObjectKind::Polyline : ObjectKind::Polygon;
    std::vector<size_t> old_indexes;
    std::vector<MapObject> converted;
    QStringList dropped;   // pola usuniete przy zamianie na polygon
    QStringList skipped;   // polilinie, ktorych nie da sie zamienic
    for (MapObjectItem* item : selected_object_items_in_order()) {
        const MapObject& src = item->object();
        if (src.kind() != from || !src.data) continue;
        MapObject obj = src;
        obj.set_kind(to);
        obj.id.reset();
        obj.type = last_used_type(to);
        bool ok = true;
        for (int level : std::vector<int>(obj.data->data_levels())) {
            std::vector<Poly> polys = *obj.data->polys_for_data_level(level);
            for (Poly& poly : polys) {
                const bool closed = poly.size() > 1 && poly.front().pos() == poly.back().pos();
                if (to_polyline) {
                    // obrys polygonu jako zamknieta linia
                    if (!closed && !poly.empty()) poly.push_back(Node(poly.front().x(), poly.front().y()));
                } else {
                    if (closed) poly.pop_back();  // polygon zamyka sie sam
                    if (poly.size() < 3) ok = false;
                    for (Node& n : poly) {
                        if (n.has_numeration()) {
                            n.clear_numbers();
                            if (!dropped.contains("Numbers")) dropped << "Numbers";
                        }
                        if (n.has_hlevel()) {
                            n.set_hlevel(std::nullopt);
                            if (!dropped.contains("HLevel")) dropped << "HLevel";
                        }
                    }
                }
            }
            obj.data->set_level_polys(level, std::move(polys));
        }
        if (!ok) {
            skipped << (src.label1 ? QString::fromStdString(encoding::cp1250_to_utf8(*src.label1)) : tr("(bez nazwy)"));
            continue;
        }
        if (!to_polyline) {
            if (obj.dirindicator && !dropped.contains("DirIndicator")) dropped << "DirIndicator";
            if (obj.routeparam && !dropped.contains("RouteParam")) dropped << "RouteParam";
            obj.dirindicator = false;
            obj.routeparam.reset();
        }
        old_indexes.push_back(item->object_index());
        converted.push_back(std::move(obj));
    }
    QString skipped_note;
    if (!skipped.isEmpty())
        skipped_note = tr(" Pominięto (mniej niż 3 węzły w części): %1.").arg(skipped.join(", "));
    if (converted.empty())
        return skipped_note.isEmpty() ? tr("Nie zaznaczono obiektów do zamiany.") : skipped_note.trimmed();

    const QString text = to_polyline ? tr("Zamień polygon na polilinię") : tr("Zamień polilinię na polygon");
    auto* command = new QUndoCommand(text);
    new DeleteObjectsCmd(this, old_indexes, text, command);
    std::vector<AddObjectCmd*> adds;
    for (MapObject& obj : converted) adds.push_back(new AddObjectCmd(this, std::move(obj), text, command));
    push_command(command);
    clearSelection();
    for (AddObjectCmd* add : adds)
        if (add->index())
            if (MapObjectItem* item = item_for_object(*add->index())) item->graphics_item()->setSelected(true);
    if (changed) *changed = true;
    QString result = (to_polyline ? tr("Zamieniono polygony na polilinie: %1.") : tr("Zamieniono polilinie na polygony: %1."))
                         .arg(adds.size());
    if (!dropped.isEmpty()) result += tr(" Usunięto pola, których polygon nie obsługuje: %1.").arg(dropped.join(", "));
    return result + skipped_note;
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
    if (items_by_object_.size() < map_->objects().size()) items_by_object_.resize(map_->objects().size());
    create_items(index);
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

// ---------------------------------------------------------------- obrot
void MapScene::set_undo_stack(QUndoStack* stack) {
    if (undo_stack_) disconnect(undo_stack_, nullptr, this, nullptr);
    undo_stack_ = stack;
    // cofniecie albo inna zmiana konczy gest obrotu (nastepny obrot to nowy krok undo z nowym srodkiem)
    if (undo_stack_)
        connect(undo_stack_, &QUndoStack::indexChanged, this, [this] {
            if (!pushing_rotation_) end_rotation();
        });
}

PolyItem* MapScene::decorated_item_at(const QPointF& scene_pos, double max_distance) const {
    PolyItem* best = nullptr;
    double best_distance = max_distance;
    for (PolyItem* item : decorated_) {
        if (!item->isVisible() || !item->decorated()) continue;
        // wnetrze: polygon i linia zamknieta (np. rondo - pierwszy wezel rowny ostatniemu)
        bool inside = false;
        if (item->is_polygon()) {
            inside = item->path().contains(scene_pos - item->pos());
        } else {
            for (const auto& nodes : item->shown_nodes())
                if (nodes.size() > 3 && nodes.front() == nodes.back() &&
                    QPolygonF(QList<QPointF>(nodes.begin(), nodes.end())).containsPoint(scene_pos, Qt::OddEvenFill))
                    inside = true;
        }
        double distance = 0;
        if (!inside) {
            // odleglosc od najblizszego odcinka albo wezla (on_segment=false: bez martwych pol przy wezlach
            // po zewnetrznej stronie zakretu, ktore pomija Shift+klik)
            const auto ins = item->node_insertion(scene_pos, false, false);
            if (!ins) continue;
            distance = ins->distance;
        }
        if (distance <= best_distance) {
            best = item;
            best_distance = distance;
        }
    }
    return best;
}

bool MapScene::rotate_object(size_t obj, double degrees) {
    PolyItem* item = poly_item(obj);
    if (!map_ || !item || !map_->objects()[obj].data) return false;
    const MapObject& current = map_->objects()[obj];
    if (!rotation_ || rotation_->obj != obj) {
        end_rotation();
        const auto center = current.data->centroid(item->shown_data_level(), item->is_polygon());
        if (!center) return false;
        rotation_ = RotationGesture{obj, *center, 0, ++rotation_gestures_};
        if (!rotation_marker_) {
            QPainterPath cross;
            cross.moveTo(-8, 0);
            cross.lineTo(8, 0);
            cross.moveTo(0, -8);
            cross.lineTo(0, 8);
            rotation_marker_ = new QGraphicsPathItem(cross);
            QPen pen(QColor("red"), 2);
            pen.setCosmetic(true);
            rotation_marker_->setPen(pen);
            rotation_marker_->setZValue(150);
            rotation_marker_->setFlag(QGraphicsItem::ItemIgnoresTransformations, true);
            rotation_marker_->setAcceptedMouseButtons(Qt::NoButton);
            addItem(rotation_marker_);
        }
        rotation_marker_->setPos(center->x, center->y);
        rotation_marker_->setVisible(true);
    }
    if (!rotation_timer_) {
        rotation_timer_ = new QTimer(this);
        rotation_timer_->setSingleShot(true);
        connect(rotation_timer_, &QTimer::timeout, this, &MapScene::end_rotation);
    }
    rotation_->total_degrees += degrees;
    MapObject after = current;
    // os y sceny w dol: kat ujemny w ukladzie sceny to obrot przeciwny do ruchu wskazowek zegara na ekranie
    const double pi = std::acos(-1.0);
    after.data->rotate(rotation_->center, -degrees * pi / 180);
    pushing_rotation_ = true;
    push_command(new RotateObjectCmd(this, obj, current, std::move(after), tr("Obróć obiekt"), rotation_->id));
    pushing_rotation_ = false;
    rotation_timer_->start(ROTATION_GESTURE_MS);
    emit message(tr("Obrót: %1°").arg(QString::asprintf("%+.1f", rotation_->total_degrees)));
    return true;
}

void MapScene::end_rotation() {
    rotation_.reset();
    if (rotation_timer_) rotation_timer_->stop();
    if (rotation_marker_) rotation_marker_->setVisible(false);
}

}  // namespace pwm::gui
