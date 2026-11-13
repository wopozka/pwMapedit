// Port mapCanvas.py (QGraphicsScene z obiektami mapy): wyswietlanie, zaznaczanie i operacje edycyjne.
#pragma once

#include <QGraphicsScene>
#include <QPointF>
#include <vector>

#include "constants.hpp"
#include "map_data.hpp"

class QUndoCommand;
class QUndoStack;

namespace pwm::gui {

class MapStyles;
class MapObjectItem;

class MapScene : public QGraphicsScene {
    Q_OBJECT
public:
    explicit MapScene(QObject* parent = nullptr);

    // Tworzy elementy dla wszystkich obiektow mapy (odpowiednik draw_poi_polyline_polygon).
    void set_map(MapData* map, const MapStyles* styles);
    // Usuwa elementy mapy (pozostale elementy, np. linijka, zostaja).
    void clear_map();
    MapData* map() const { return map_; }
    const MapStyles* styles() const { return styles_; }

    int map_level() const { return map_level_; }
    void set_map_level(int level);

    // Skala widoku (iloczyn wszystkich powiekszen). Przy przekroczeniu IGNORE_TRANSFORMATION_TRESHOLD
    // elementy o stalej wielkosci ekranowej (ikony, napisy, strzalki) przelaczaja flage.
    double viewer_scale() const { return viewer_scale_; }
    void set_viewer_scale(double scale);

    Tool tool() const { return tool_; }
    void set_tool(Tool tool) { tool_ = tool; }

    // Prostokat sceny z prostokata ograniczajacego mapy (+0.001 stopnia z kazdej strony).
    void set_canvas_rectangle(const GeoBBox& bbox, const Projection& projection);

    const std::vector<MapObjectItem*>& object_items() const { return object_items_; }
    // Element sceny dla obiektu o danym indeksie w MapData (nullptr, gdy obiekt nie ma elementu).
    MapObjectItem* item_for_object(size_t index) const;
    // Przebudowuje element obiektu po zmianie jego danych (wywolywane przez komendy undo/redo).
    void refresh_object(size_t index);
    // Zaznaczone obiekty mapy, w kolejnosci indeksow w MapData.
    std::vector<MapObjectItem*> selected_object_items() const;

    // Stos undo/redo okna; komendy edycji sa na nim umieszczane przez widok i okno.
    QUndoStack* undo_stack() const { return undo_stack_; }
    void set_undo_stack(QUndoStack* stack) { undo_stack_ = stack; }

    // ---- edycja (kazda operacja to jedna komenda na stosie undo) ----
    // Przesuniecie obiektow o wektory (we wspolrzednych sceny), np. po przeciagnieciu mysza.
    void move_objects(const std::vector<std::pair<MapObjectItem*, QPointF>>& moves);
    void delete_selected();
    // Odwrocenie kierunku zaznaczonych polilinii (wszystkie poziomy Data).
    void reverse_selected_polylines();
    // Elementy, ktore maja przetrwac clear_map() (np. linijka skali).
    void add_persistent_item(QGraphicsItem* item) {
        persistent_items_.append(item);
        addItem(item);
    }

signals:
    void progress(int value, int maximum);

private:
    void apply_transformation_flags(bool ignore);
    void push_command(QUndoCommand* command);

    MapData* map_ = nullptr;
    const MapStyles* styles_ = nullptr;
    std::vector<MapObjectItem*> object_items_;
    std::vector<MapObjectItem*> items_by_object_;  // indeks obiektu w MapData -> element
    QUndoStack* undo_stack_ = nullptr;
    QList<QGraphicsItem*> persistent_items_;
    int map_level_ = 0;
    double viewer_scale_ = 1.0;
    Tool tool_ = Tool::SelectObjects;
};

}  // namespace pwm::gui
