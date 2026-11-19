#include "map_view.hpp"

#include <QGraphicsPathItem>
#include <QKeyEvent>
#include <QMimeData>
#include <QMouseEvent>
#include <QWheelEvent>
#include <algorithm>
#include <cmath>

#include "map_items.hpp"
#include "map_scene.hpp"
#include "misc.hpp"

namespace pwm::gui {

MapView::MapView(MapScene* scene, QWidget* parent) : QGraphicsView(scene, parent) {
    setMouseTracking(true);
    // zmiana narzedzia porzuca rysowany obiekt
    if (scene) connect(scene, &MapScene::tool_changed, this, &MapView::creation_cancel);
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
    const int level = map_scene() ? map_scene()->map_level() : 0;
    emit status_message(last_coords_text_ + QString::asprintf("view_render scale: %.3f, ", map_scale_) +
                        QString::asprintf("map scale: 1:%.0f, map level: %d", ruler_scale, level));
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
    emit view_changed();
}

void MapView::zoom_out() {
    if (!scene()) return;
    setInteractive(false);
    set_map_scale(0.9);
    scale(0.9, 0.9);
    setInteractive(true);
    update_ruler(true);
    update_status(false);
    emit view_changed();
}

void MapView::mouseMoveEvent(QMouseEvent* event) {
    if (!scene()) return;
    view_mouse_ = event->position().toPoint();
    scene_mouse_ = mapToScene(view_mouse_);
    if (edge_drag_) {
        move_edge_drag(event->modifiers());
        update_status(true);
        return;
    }
    QGraphicsView::mouseMoveEvent(event);
    if (!right_button_drag_) {
        update_snap(event->modifiers());
        if (creation_tool()) update_creation_preview();
        update_status(true);
    }
}

void MapView::mousePressEvent(QMouseEvent* event) {
    move_start_.clear();
    if (event->button() == Qt::LeftButton) last_click_ = mapToScene(event->position().toPoint());
    // narzedzia tworzenia: lewy przycisk nie zaznacza ani nie przesuwa obiektow (klikniecie obslugiwane po puszczeniu)
    if (event->button() == Qt::LeftButton && creation_tool()) {
        event->accept();
        return;
    }
    select_on_press(event);
    MapScene* s = map_scene();
    if (s && event->button() == Qt::LeftButton && !right_button_drag_ && s->tool() == Tool::SelectObjects) {
        for (MapObjectItem* item : s->selected_object_items())
            move_start_.emplace_back(item, item->graphics_item()->pos());
    }
}

bool MapView::start_edge_drag(QMouseEvent* event, const QList<QGraphicsItem*>& under) {
    MapScene* s = map_scene();
    if (!s || event->modifiers() != Qt::NoModifier) return false;
    const QPointF scene_pos = mapToScene(event->position().toPoint());
    const double max_distance = NODE_INSERT_DISTANCE / std::max(s->viewer_scale(), 1e-9);
    for (MapObjectItem* obj : s->selected_object_items()) {
        auto* item = dynamic_cast<PolyItem*>(obj);
        // obiekt w edycji ma ksztalt tylko wzdluz linii/krawedzi - trafienie oznacza kursor-krzyzyk nad krawedzia
        if (!item || !item->decorated() || !under.contains(item)) continue;
        const auto ins = item->node_insertion(item->mapFromScene(scene_pos), true, false);
        if (!ins || ins->distance > max_distance) continue;
        edge_drag_ = EdgeDrag{item, ins->poly_num, ins->index, event->position(), event->globalPosition(),
                              item->mapToScene(ins->position), false, nullptr};
        // wezel powstaje od razu w miejscu nacisniecia (na krawedzi) razem z kwadratem uchwytu
        edge_drag_->grip = new GripItem(item, item->shown_data_level(), ins->poly_num, ins->index, ins->position);
        edge_drag_->grip->set_preview_only();
        item->preview_inserted_node(ins->poly_num, ins->index, ins->position);
        return true;
    }
    return false;
}

void MapView::move_edge_drag(Qt::KeyboardModifiers modifiers) {
    MapScene* s = map_scene();
    EdgeDrag& d = *edge_drag_;
    if (!d.started) {
        const QPointF delta = QPointF(view_mouse_) - d.press_pos;
        if (std::max(std::abs(delta.x()), std::abs(delta.y())) < MIN_MOVE_DISTANCE) return;
        d.started = true;
    }
    d.position = scene_mouse_;
    // Ctrl: przyciaganie do wezla innego obiektu, jak przy przeciaganiu uchwytu
    std::optional<QPointF> snap;
    if (modifiers & Qt::ControlModifier)
        snap = s->closest_node(d.position, SNAP_DISTANCE / std::max(s->viewer_scale(), 1e-9), d.item);
    s->show_snap_indicator(snap);
    if (snap) d.position = *snap;
    const QPointF pos = d.item->mapFromScene(d.position);
    d.grip->setPos(pos);
    d.item->preview_inserted_node(d.poly_num, d.index, pos);
}

void MapView::finish_edge_drag(QMouseEvent* event) {
    const EdgeDrag d = *edge_drag_;
    edge_drag_.reset();
    delete d.grip;
    MapScene* s = map_scene();
    if (!d.started) {
        s->refresh_object(d.item->object_index());  // usuwa podglad wezla
        // zwykle klikniecie na krawedzi: obsluga jak bez przeciagania (np. wybor kolejnego obiektu pod kursorem)
        QMouseEvent press(QEvent::MouseButtonPress, d.press_pos, d.global_pos, Qt::LeftButton, Qt::LeftButton,
                          Qt::NoModifier);
        select_on_press(&press, false);
        QGraphicsView::mouseReleaseEvent(event);
        return;
    }
    s->show_snap_indicator(std::nullopt);
    const size_t obj = d.item->object_index();
    const int level = d.item->shown_data_level();
    const QPointF pos = d.item->mapFromScene(d.position);
    if (s->insert_node(obj, level, d.poly_num, d.index, pos))
        s->set_active_grip(obj, level, d.poly_num, d.index);
    else
        s->refresh_object(obj);  // przywraca sciezke sprzed podgladu
}

void MapView::select_on_press(QMouseEvent* event, bool allow_edge_drag) {
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
        // przeciagniecie z krawedzi obiektu z uchwytami dodaje wezel pod kursorem i od razu go przesuwa
        if (tool == Tool::EditNodes && allow_edge_drag && start_edge_drag(event, under)) {
            event->accept();
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
        // Ctrl+klik w trybie zaznaczania: dodaje najwyzszy NIEzaznaczony obiekt pod kursorem (np. maly polygon lezacy
        // na juz zaznaczonym duzym); gdy wszystkie pod kursorem sa zaznaczone - odznacza najwyzszy. Zaznaczenie
        // ustawiamy sami - Qt przelaczylby obiekt na wierzchu, a zaznaczony obiekt jest podniesiony nad inne.
        if (tool == Tool::SelectObjects && event->modifiers() == Qt::ControlModifier) {
            QGraphicsItem* target = nullptr;
            for (QGraphicsItem* item : objects) {
                if (!item->isSelected()) {
                    target = item;
                    break;
                }
            }
            if (target) {
                target->setSelected(true);
                if (auto* obj = dynamic_cast<MapObjectItem*>(target)) obj->set_selection_z_value();
            } else {
                objects.front()->setSelected(false);
            }
            event->accept();
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
    if (event->button() == Qt::LeftButton && edge_drag_) {
        finish_edge_drag(event);
        event->accept();
        return;
    }
    if (event->button() == Qt::LeftButton && creation_tool()) {
        scene_mouse_ = mapToScene(event->position().toPoint());
        update_snap(event->modifiers());
        creation_click();
        event->accept();
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
    // Shift+kolko w edycji wezlow nad obiektem z uchwytami: obrot o 1 stopien na zabek (z Ctrl o 0,1),
    // kolko od siebie - przeciwnie do ruchu wskazowek zegara. Poza obiektem Shift+kolko dziala jak zwykle.
    MapScene* s = map_scene();
    if (s && (event->modifiers() & Qt::ShiftModifier) && s->tool() == Tool::EditNodes) {
        const QPointF pos = mapToScene(event->position().toPoint());
        if (PolyItem* item = s->decorated_item_at(pos, NODE_INSERT_DISTANCE / std::max(s->viewer_scale(), 1e-9))) {
            // Shift moze zamienic os kolka (ruch poziomy) - liczy sie ta, ktora sie ruszyla
            int delta = event->angleDelta().y();
            if (delta == 0) delta = event->angleDelta().x();
            const double step = (event->modifiers() & Qt::ControlModifier) ? 0.1 : 1.0;
            if (delta != 0) s->rotate_object(item->object_index(), step * delta / 120.0);
            event->accept();
            return;
        }
    }
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
    emit view_changed();
}

void MapView::scrollContentsBy(int dx, int dy) {
    QGraphicsView::scrollContentsBy(dx, dy);
    update_ruler(false);
    emit view_changed();
}


// ---------------------------------------------------------------- tworzenie obiektow
bool MapView::creation_tool() const {
    MapScene* s = map_scene();
    if (!s) return false;
    const Tool t = s->tool();
    return t == Tool::CreatePoint || t == Tool::CreatePolyline || t == Tool::CreatePolylineCircle ||
           t == Tool::CreatePolygon;
}

QPointF MapView::creation_position() const { return snapped_.value_or(scene_mouse_); }

void MapView::update_snap(Qt::KeyboardModifiers modifiers) {
    MapScene* s = map_scene();
    snapped_.reset();
    // poza rysowaniem kolkiem zarzadza przeciagany uchwyt
    if (!s || !creation_tool()) return;
    if (modifiers & Qt::ControlModifier)
        snapped_ = s->closest_node(scene_mouse_, SNAP_DISTANCE / std::max(s->viewer_scale(), 1e-9));
    s->show_snap_indicator(snapped_);
}

void MapView::creation_click() {
    MapScene* s = map_scene();
    if (!s || !s->map()) return;
    const QPointF pos = creation_position();
    switch (s->tool()) {
        case Tool::CreatePoint:
            s->create_object(ObjectKind::Poi, {pos});
            break;
        case Tool::CreatePolyline:
        case Tool::CreatePolygon:
            creation_nodes_.push_back(pos);
            update_creation_preview();
            break;
        case Tool::CreatePolylineCircle:
            // pierwsze klikniecie: punkt na okregu; drugie (srodek pod kursorem) tworzy polilinie
            if (creation_nodes_.empty()) {
                creation_nodes_.push_back(pos);
                update_creation_preview();
            } else {
                compute_circle();
                const std::vector<QPointF> nodes = circle_nodes_;
                creation_cancel();
                if (nodes.size() > 2) s->create_object(ObjectKind::Polyline, nodes);
            }
            break;
        default:
            break;
    }
}

void MapView::creation_add_node() {
    MapScene* s = map_scene();
    if (!s || (s->tool() != Tool::CreatePolyline && s->tool() != Tool::CreatePolygon)) return;
    creation_nodes_.push_back(creation_position());
    update_creation_preview();
}

void MapView::creation_remove_last_node() {
    if (creation_nodes_.empty()) return;
    creation_nodes_.pop_back();
    update_creation_preview();
}

bool MapView::creation_finish() {
    MapScene* s = map_scene();
    if (!s) return false;
    const bool polygon = s->tool() == Tool::CreatePolygon;
    if (s->tool() != Tool::CreatePolyline && !polygon) return false;
    // polilinia co najmniej 2 wezly, polygon 3
    if (creation_nodes_.size() < (polygon ? 3u : 2u)) return false;
    const std::vector<QPointF> nodes = creation_nodes_;
    creation_cancel();
    return s->create_object(polygon ? ObjectKind::Polygon : ObjectKind::Polyline, nodes).has_value();
}

void MapView::creation_cancel() {
    creation_nodes_.clear();
    circle_nodes_.clear();
    delete creation_preview_;
    creation_preview_ = nullptr;
}

void MapView::compute_circle() {
    // Port rysowania okregu z mapRender.mouseMoveEvent: srodek pod kursorem, okrag przez pierwszy punkt;
    // liczba bokow taka, zeby bok wielokata wpisanego mial co najmniej MINIMAL_GEO_DISTANCE metrow.
    circle_nodes_.clear();
    if (creation_nodes_.empty() || !projection_) return;
    const QPointF first = creation_nodes_.front();
    const QPointF center = creation_position();
    const double r = std::hypot(first.x() - center.x(), first.y() - center.y());
    double geo_r = 0;
    try {
        geo_r = misc::vincenty_distance(projection_->canvas_to_geo(first.x(), first.y()),
                                        projection_->canvas_to_geo(center.x(), center.y()));
    } catch (const std::exception&) {
        geo_r = 0;
    }
    if (!(geo_r > 0) || r <= 0) return;
    const double r_min_geo = r / (geo_r / MINIMAL_GEO_DISTANCE);
    const double sin_half_alpha = 0.5 * r_min_geo / r;
    if (!(sin_half_alpha > 0 && sin_half_alpha <= std::sqrt(3.0) / 2)) return;
    const double alpha = 2 * std::asin(sin_half_alpha);
    const int n = static_cast<int>(std::floor(2 * M_PI / alpha));
    QLineF rot(center, first);
    circle_nodes_.push_back(first);
    for (int k = 1; k < n; ++k) {
        rot.setAngle(rot.angle() + 360.0 / n);
        circle_nodes_.push_back(rot.p2());
    }
    circle_nodes_.push_back(first);  // okrag zamkniety
}

void MapView::update_creation_preview() {
    MapScene* s = map_scene();
    if (!s || creation_nodes_.empty()) {
        delete creation_preview_;
        creation_preview_ = nullptr;
        return;
    }
    if (!creation_preview_) {
        creation_preview_ = new QGraphicsPathItem;
        creation_preview_->setZValue(NEW_OBJECT_CREATION_Z_VAL);
        creation_preview_->setAcceptedMouseButtons(Qt::NoButton);
        QPen pen(Qt::black, 1);
        pen.setCosmetic(true);  // 1 piksel niezaleznie od skali
        creation_preview_->setPen(pen);
        s->addItem(creation_preview_);
    }
    QPainterPath path;
    if (s->tool() == Tool::CreatePolylineCircle) {
        compute_circle();
        const QPointF first = creation_nodes_.front();
        const QPointF center = creation_position();
        const double r = std::hypot(first.x() - center.x(), first.y() - center.y());
        path.addEllipse(center, r, r);
        if (!circle_nodes_.empty()) path.addPolygon(QPolygonF(QList<QPointF>(circle_nodes_.begin(), circle_nodes_.end())));
    } else {
        QPolygonF poly(QList<QPointF>(creation_nodes_.begin(), creation_nodes_.end()));
        poly.append(creation_position());
        path.addPolygon(poly);
        if (s->tool() == Tool::CreatePolygon) {
            path.closeSubpath();
            creation_preview_->setBrush(Qt::yellow);
            creation_preview_->setOpacity(0.5);
        }
    }
    creation_preview_->setPath(path);
}

void MapView::keyPressEvent(QKeyEvent* event) {
    // '+' z Shift (np. Shift + '=' na klawiaturze polskiej i US) nie zawsze pasuje do skrotu "+" okna -
    // widok przybliza sam, gdy skrot nie zadzialal
    if (event->key() == Qt::Key_Plus && !(event->modifiers() & (Qt::ControlModifier | Qt::AltModifier))) {
        zoom_in();
        event->accept();
        return;
    }
    if (creation_tool()) {
        if (event->key() == Qt::Key_Control) {
            update_snap(event->modifiers() | Qt::ControlModifier);
            update_creation_preview();
        } else if (event->key() == Qt::Key_Backspace) {
            creation_remove_last_node();
            event->accept();
            return;
        } else if (event->key() == Qt::Key_Return || event->key() == Qt::Key_Enter) {
            creation_finish();
            event->accept();
            return;
        }
    }
    QGraphicsView::keyPressEvent(event);
}

void MapView::keyReleaseEvent(QKeyEvent* event) {
    if (event->key() == Qt::Key_Control) {
        if (MapScene* s = map_scene()) s->show_snap_indicator(std::nullopt);
        snapped_.reset();
        if (creation_tool()) update_creation_preview();
    }
    QGraphicsView::keyReleaseEvent(event);
}

}  // namespace pwm::gui
