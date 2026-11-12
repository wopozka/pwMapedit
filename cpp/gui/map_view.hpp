// Port mapRender.py (QGraphicsView): powiekszanie, przesuwanie prawym przyciskiem, zaznaczanie obiektow,
// linijka skali i informacje w pasku stanu. Warstwy WWW i tworzenie obiektow - kolejne etapy.
#pragma once

#include <QGraphicsView>
#include <QPointF>
#include <vector>

#include "projection.hpp"

class QMimeData;

namespace pwm::gui {

class MapScene;
class MapRuler;

class MapView : public QGraphicsView {
    Q_OBJECT
public:
    explicit MapView(MapScene* scene, QWidget* parent = nullptr);

    MapScene* map_scene() const;
    void set_projection(const Projection* projection);
    void set_ruler(MapRuler* ruler) { ruler_ = ruler; }
    MapRuler* ruler() const { return ruler_; }

    double map_scale() const { return map_scale_; }
    void zoom_in();
    void zoom_out();

    QPointF current_scene_mouse_coords() const { return scene_mouse_; }
    // (lat, lon) pod kursorem
    GeoPoint current_mouse_geo_coordinates() const;

    QMimeData* copy() const;
    void update_status(bool with_mouse_coords = true);

signals:
    void status_message(const QString& text);

protected:
    void mouseMoveEvent(QMouseEvent* event) override;
    void mousePressEvent(QMouseEvent* event) override;
    void mouseReleaseEvent(QMouseEvent* event) override;
    void wheelEvent(QWheelEvent* event) override;
    void resizeEvent(QResizeEvent* event) override;
    void scrollContentsBy(int dx, int dy) override;

private:
    void set_map_scale(double factor);
    void update_ruler(bool rescale);

    const Projection* projection_ = nullptr;
    MapRuler* ruler_ = nullptr;
    double map_scale_ = 1.0;
    QPointF scene_mouse_;
    QPoint view_mouse_{-1, -1};  // -1: kursor jeszcze nie byl nad mapa
    bool right_button_drag_ = false;
    // cykliczne wybieranie jednego z kilku obiektow pod kursorem kolejnymi kliknieciami
    std::vector<QGraphicsItem*> items_under_cursor_;
    int item_under_cursor_index_ = -1;
    QString last_coords_text_;
};

}  // namespace pwm::gui
