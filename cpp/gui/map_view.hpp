// Port mapRender.py (QGraphicsView): powiekszanie, przesuwanie prawym przyciskiem, zaznaczanie obiektow,
// linijka skali i informacje w pasku stanu. Warstwy WWW i tworzenie obiektow - kolejne etapy.
#pragma once

#include <QGraphicsView>
#include <QPointF>
#include <optional>
#include <vector>

#include "projection.hpp"

class QMimeData;
class QGraphicsPathItem;

namespace pwm::gui {

class MapScene;
class MapRuler;
class MapObjectItem;


class MapView : public QGraphicsView {
    Q_OBJECT
public:
    explicit MapView(MapScene* scene, QWidget* parent = nullptr);

    MapScene* map_scene() const;
    void set_projection(const Projection* projection);
    const Projection* projection() const { return projection_; }
    void set_ruler(MapRuler* ruler) { ruler_ = ruler; }
    MapRuler* ruler() const { return ruler_; }

    double map_scale() const { return map_scale_; }
    void zoom_in();
    void zoom_out();

    QPointF current_scene_mouse_coords() const { return scene_mouse_; }
    // Pozycja kursora na mapie (brak, gdy kursor jeszcze nie byl nad mapa).
    std::optional<QPointF> mouse_scene_pos() const {
        return view_mouse_.x() < 0 ? std::nullopt : std::optional<QPointF>(scene_mouse_);
    }
    // Miejsce ostatniego klikniecia lewym przyciskiem (punkt odniesienia przy kopiowaniu obiektow).
    std::optional<QPointF> last_click_scene_pos() const { return last_click_; }
    // (lat, lon) pod kursorem
    GeoPoint current_mouse_geo_coordinates() const;

    QMimeData* copy() const;

    // ---- tworzenie obiektow (narzedzia Create*) ----
    // Wezly rysowanego obiektu (polilinia, polygon) albo punkt na okregu i wezly okregu.
    const std::vector<QPointF>& creation_nodes() const { return creation_nodes_; }
    // Insert: wezel w miejscu kursora (albo przyciagniety); Backspace: usuniecie ostatniego; Enter: koniec.
    void creation_add_node();
    void creation_remove_last_node();
    bool creation_finish();
    // Esc albo zmiana narzedzia: porzucenie rysowanego obiektu.
    void creation_cancel();
    void update_status(bool with_mouse_coords = true);

signals:
    void status_message(const QString& text);
    // Widoczny fragment mapy sie zmienil (przesuniecie, powiekszenie, rozmiar) - np. dla warstw WWW.
    void view_changed();

protected:
    void keyPressEvent(QKeyEvent* event) override;
    void keyReleaseEvent(QKeyEvent* event) override;
    void mouseMoveEvent(QMouseEvent* event) override;
    void mousePressEvent(QMouseEvent* event) override;
    void mouseReleaseEvent(QMouseEvent* event) override;
    void wheelEvent(QWheelEvent* event) override;
    void resizeEvent(QResizeEvent* event) override;
    void scrollContentsBy(int dx, int dy) override;

private:
    void select_on_press(QMouseEvent* event);
    bool creation_tool() const;
    // Polozenie nowego wezla: przyciagniety wezel (Ctrl) albo punkt pod kursorem.
    QPointF creation_position() const;
    void update_snap(Qt::KeyboardModifiers modifiers);
    void creation_click();
    void update_creation_preview();
    void compute_circle();
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
    // polozenia zaznaczonych obiektow w chwili nacisniecia lewego przycisku - po puszczeniu przycisku
    // przesuniete obiekty trafiaja do jednej komendy undo
    std::vector<std::pair<MapObjectItem*, QPointF>> move_start_;
    std::optional<QPointF> last_click_;
    std::optional<QPointF> snapped_;
    std::vector<QPointF> creation_nodes_;
    std::vector<QPointF> circle_nodes_;  // okrag: wezly wyliczone dla biezacego polozenia kursora
    QGraphicsPathItem* creation_preview_ = nullptr;
    QString last_coords_text_;
};

}  // namespace pwm::gui
