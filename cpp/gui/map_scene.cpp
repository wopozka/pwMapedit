#include "map_scene.hpp"

#include <QCoreApplication>
#include <QElapsedTimer>

#include "map_items.hpp"
#include "map_styles.hpp"

namespace pwm::gui {

MapScene::MapScene(QObject* parent) : QGraphicsScene(parent) {
    // Bez indeksu BSP. Przy setkach tysiecy elementow indeks BSP bardzo spowalnia kazda zmiane geometrii
    // (setPath przy zmianie poziomu mapy: kilka ms na element, czyli minuty dla calej mapy), a przeglad liniowy
    // przy rysowaniu kosztuje kilkadziesiat ms. Python uzywal BSP, ale tam koszt ginal w narzucie interpretera.
    setItemIndexMethod(QGraphicsScene::NoIndex);
}

void MapScene::clear_map() {
    clearSelection();
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
    emit progress(0, total);
    QElapsedTimer progress_timer;
    progress_timer.start();
    for (size_t i = 0; i < objects.size(); ++i) {
        const MapObject& obj = objects[i];
        if (obj.deleted || !obj.data) continue;
        long long type = obj.type.value_or(0);
        switch (obj.kind()) {
            case ObjectKind::Poi: {
                auto* item = new PoiItem(map_, i, styles_->poi_icon(type));
                addItem(item);
                item->add_label();
                item->set_map_level(map_level_);
                object_items_.push_back(item);
                break;
            }
            case ObjectKind::Polyline: {
                auto* item = new PolylineItem(map_, i, styles_->polyline_pen(type));
                addItem(item);
                item->set_map_level(map_level_);
                object_items_.push_back(item);
                break;
            }
            case ObjectKind::Polygon: {
                auto* item = new PolygonItem(map_, i, styles_->polygon_pen(type),
                                             QBrush(styles_->polygon_fill_colour(type)),
                                             styles_->polygon_z_value(type));
                addItem(item);
                item->set_map_level(map_level_);
                object_items_.push_back(item);
                break;
            }
            case ObjectKind::Basic:
                break;
        }
        if (progress_timer.elapsed() > 100) {
            emit progress(static_cast<int>(i), total);
            QCoreApplication::processEvents(QEventLoop::ExcludeUserInputEvents);
            progress_timer.restart();
        }
    }
    emit progress(total, total);
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

}  // namespace pwm::gui
