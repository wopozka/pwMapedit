#include "map_view.hpp"

#include <QMimeData>
#include <QMouseEvent>
#include <QWheelEvent>
#include <algorithm>
#include <cmath>

#include "map_items.hpp"
#include "map_scene.hpp"

namespace pwm::gui {

MapView::MapView(MapScene* scene, QWidget* parent) : QGraphicsView(scene, parent) {
    setMouseTracking(true);
}

MapScene* MapView::map_scene() const { return qobject_cast<MapScene*>(scene()); }

void MapView::set_projection(const Projection* projection) {
    projection_ = projection;
    if (ruler_) ruler_->set_projection(projection);
}

GeoPoint MapView::current_mouse_geo_coordinates() const {
    if (!projection_) return {};
    try {
        return projection_->canvas_to_geo(scene_mouse_.x(), scene_mouse_.y());
    } catch (const std::exception&) {
        return {};
    }
}

QMimeData* MapView::copy() const {
    // Zaznaczone obiekty beda kopiowane w kolejnym etapie (edycja); na razie wspolrzedne kursora.
    GeoPoint g = current_mouse_geo_coordinates();
    auto* mime = new QMimeData;
    mime->setText(QString::asprintf("%.6f,%.6f", g.latitude, g.longitude));
    return mime;
}

void MapView::update_status(bool with_mouse_coords) {
    if (with_mouse_coords) {
        GeoPoint g = current_mouse_geo_coordinates();
        last_coords_text_ = QString::asprintf("(%.7f, %.7f), (%.1f, %.1f), ", g.latitude, g.longitude,
                                              scene_mouse_.x(), -scene_mouse_.y());
    }
    double ruler_scale = ruler_ ? ruler_->map_scale() : 0.0;
    emit status_message(last_coords_text_ + QString::asprintf("view_render scale: %.3f, ", map_scale_) +
                        QString::asprintf("map scale: 1:%.0f", ruler_scale));
}

void MapView::set_map_scale(double factor) {
    map_scale_ *= factor;
    if (MapScene* s = map_scene()) s->set_viewer_scale(map_scale_);
}

void MapView::update_ruler(bool rescale) {
    if (!ruler_) return;
    if (rescale)
        ruler_->scale_to();
    else
        ruler_->move_to();
}

void MapView::zoom_in() {
    if (!scene()) return;
    QPointF center = mapToScene(viewport()->width() / 2, viewport()->height() / 2);
    if (view_mouse_.x() < 0) {
        view_mouse_ = viewport()->rect().center();
        scene_mouse_ = center;
    }
    QPointF mouse = scene_mouse_;
    QPointF mouse_center = center - mouse;
    double length = std::hypot(mouse_center.x(), mouse_center.y());
    setInteractive(false);
    set_map_scale(1.1);
    scale(1.1, 1.1);
    if (length > 0) {
        // punkt pod kursorem zostaje w miejscu
        QPointF center1 = mapToScene(viewport()->width() / 2, viewport()->height() / 2);
        QPointF mouse1 = mapToScene(view_mouse_);
        QPointF v1 = center1 - mouse1;
        double factor = std::hypot(v1.x(), v1.y()) / length;
        centerOn(mouse + mouse_center * factor);
    }
    setInteractive(true);
    update_ruler(true);
    update_status(false);
}

void MapView::zoom_out() {
    if (!scene()) return;
    setInteractive(false);
    set_map_scale(0.9);
    scale(0.9, 0.9);
    setInteractive(true);
    update_ruler(true);
    update_status(false);
}

void MapView::mouseMoveEvent(QMouseEvent* event) {
    if (!scene()) return;
    view_mouse_ = event->position().toPoint();
    scene_mouse_ = mapToScene(view_mouse_);
    QGraphicsView::mouseMoveEvent(event);
    if (!right_button_drag_) update_status(true);
}

void MapView::mousePressEvent(QMouseEvent* event) {
    move_start_.clear();
    if (event->button() == Qt::LeftButton) last_click_ = mapToScene(event->position().toPoint());
    select_on_press(event);
    MapScene* s = map_scene();
    if (s && event->button() == Qt::LeftButton && !right_button_drag_ && s->tool() == Tool::SelectObjects) {
        for (MapObjectItem* item : s->selected_object_items())
            move_start_.emplace_back(item, item->graphics_item()->pos());
    }
}

void MapView::select_on_press(QMouseEvent* event) {
    MapScene* s = map_scene();
    if (!s) return;

    // Przesuwanie mapy prawym przyciskiem: udajemy lewy przycisk w trybie ScrollHandDrag.
    if (event->button() == Qt::RightButton) {
        right_button_drag_ = true;
        setDragMode(QGraphicsView::ScrollHandDrag);
        setInteractive(false);
        QMouseEvent fake(QEvent::MouseButtonPress, event->position(), event->globalPosition(), Qt::LeftButton,
                         Qt::LeftButton, event->modifiers());
        QGraphicsView::mousePressEvent(&fake);
        return;
    }

    const Tool tool = s->tool();
    if (event->button() == Qt::LeftButton && (tool == Tool::SelectObjects || tool == Tool::EditNodes)) {
        const QList<QGraphicsItem*> under = items(event->position().toPoint());
        // uchwyt wezla obsluguje klikniecie sam (przeciaganie, Ctrl+klik), zaznaczenie sie nie zmienia
        if (!under.isEmpty() && under.front()->type() == GripItemType) {
            QGraphicsView::mousePressEvent(event);
            return;
        }
        // Shift+klik na krawedzi obiektu z uchwytami dodaje wezel
        if (tool == Tool::EditNodes && event->modifiers() == Qt::ShiftModifier) {
            const QPointF scene_pos = mapToScene(event->position().toPoint());
            const double max_distance = NODE_INSERT_DISTANCE / std::max(s->viewer_scale(), 1e-9);
            for (MapObjectItem* item : s->selected_object_items()) {
                if (s->insert_node_on_segment(dynamic_cast<PolyItem*>(item), scene_pos, max_distance)) {
                    event->accept();
                    return;
                }
            }
        }
        if (under.isEmpty()) {
            s->clearSelection();
            QGraphicsView::mousePressEvent(event);
            return;
        }
        std::vector<QGraphicsItem*> objects;
        for (QGraphicsItem* item : under) {
            int t = item->type();
            if ((t == PoiItemType || t == PolylineItemType || t == PolygonItemType) && item->isVisible())
                objects.push_back(item);
        }
        if (objects.empty()) {
            QGraphicsView::mousePressEvent(event);
            return;
        }
        auto* first = dynamic_cast<MapObjectItem*>(objects.front());
        if (objects.size() == 1) {
            if (!objects.front()->isSelected()) {
                if (event->modifiers() != Qt::ControlModifier || tool == Tool::EditNodes) s->clearSelection();
                if (first) first->set_selection_z_value();
            }
            QGraphicsView::mousePressEvent(event);
            return;
        }
        // kilka obiektow pod kursorem: kolejne klikniecia wybieraja kolejne z nich
        if (objects != items_under_cursor_) {
            items_under_cursor_ = objects;
            item_under_cursor_index_ = -1;
        }
        item_under_cursor_index_ = (item_under_cursor_index_ + 1) % static_cast<int>(items_under_cursor_.size());
        if (event->modifiers() != Qt::ShiftModifier || tool == Tool::EditNodes) s->clearSelection();
        if (auto* chosen = dynamic_cast<MapObjectItem*>(items_under_cursor_[size_t(item_under_cursor_index_)]))
            chosen->set_selection_z_value();
        QGraphicsView::mousePressEvent(event);
        return;
    }
    QGraphicsView::mousePressEvent(event);
}

void MapView::mouseReleaseEvent(QMouseEvent* event) {
    if (!scene()) return;
    if (event->button() == Qt::RightButton && right_button_drag_) {
        QMouseEvent fake(QEvent::MouseButtonRelease, event->position(), event->globalPosition(), Qt::LeftButton,
                         Qt::NoButton, event->modifiers());
        QGraphicsView::mouseReleaseEvent(&fake);
        setDragMode(QGraphicsView::NoDrag);
        setInteractive(true);
        right_button_drag_ = false;
        return;
    }
    QGraphicsView::mouseReleaseEvent(event);
    if (event->button() == Qt::LeftButton && !move_start_.empty()) {
        std::vector<std::pair<MapObjectItem*, QPointF>> moves;
        for (const auto& [item, start] : move_start_) {
            QPointF delta = item->graphics_item()->pos() - start;
            if (!delta.isNull()) moves.emplace_back(item, delta);
        }
        move_start_.clear();
        if (MapScene* s = map_scene(); s && !moves.empty()) s->move_objects(moves);
    }
}

void MapView::wheelEvent(QWheelEvent* event) {
    if (event->modifiers() == Qt::ControlModifier) {
        view_mouse_ = event->position().toPoint();
        scene_mouse_ = mapToScene(view_mouse_);
        if (event->angleDelta().y() < 0)
            zoom_out();
        else if (event->angleDelta().y() > 0)
            zoom_in();
        event->accept();
        return;
    }
    QGraphicsView::wheelEvent(event);
}

void MapView::resizeEvent(QResizeEvent* event) {
    QGraphicsView::resizeEvent(event);
    update_ruler(false);
}

void MapView::scrollContentsBy(int dx, int dy) {
    QGraphicsView::scrollContentsBy(dx, dy);
    update_ruler(false);
}

}  // namespace pwm::gui
