// Port mapCanvas.py (QGraphicsScene z obiektami mapy): wyswietlanie, zaznaczanie i operacje edycyjne.
#pragma once

#include <QGraphicsScene>
#include <QPointF>
#include <optional>
#include <vector>

#include "constants.hpp"
#include "map_data.hpp"

class QUndoCommand;
class QUndoStack;

namespace pwm::gui {

class MapStyles;
class MapObjectItem;
class PolyItem;
class GripItem;

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
    // Zmiana narzedzia; w trybie edycji wezlow zaznaczone polilinie i polygony dostaja uchwyty.
    void set_tool(Tool tool);

    // Prostokat sceny z prostokata ograniczajacego mapy (+0.001 stopnia z kazdej strony).
    void set_canvas_rectangle(const GeoBBox& bbox, const Projection& projection);

    const std::vector<MapObjectItem*>& object_items() const { return object_items_; }
    // Element sceny dla obiektu o danym indeksie w MapData (nullptr, gdy obiekt nie ma elementu).
    MapObjectItem* item_for_object(size_t index) const;
    // Przebudowuje element obiektu po zmianie jego danych (wywolywane przez komendy undo/redo).
    void refresh_object(size_t index);
    // Zaznaczone obiekty mapy, w kolejnosci indeksow w MapData.
    std::vector<MapObjectItem*> selected_object_items() const;
    // Zaznaczone obiekty mapy w kolejnosci zaznaczania (laczenie bierze wlasciwosci z pierwszego).
    std::vector<MapObjectItem*> selected_object_items_in_order() const;

    // Stos undo/redo okna; komendy edycji sa na nim umieszczane przez widok i okno.
    QUndoStack* undo_stack() const { return undo_stack_; }
    void set_undo_stack(QUndoStack* stack) { undo_stack_ = stack; }

    // ---- edycja (kazda operacja to jedna komenda na stosie undo) ----
    // Przesuniecie obiektow o wektory (we wspolrzednych sceny), np. po przeciagnieciu mysza.
    void move_objects(const std::vector<std::pair<MapObjectItem*, QPointF>>& moves);
    void delete_selected();
    // Odwrocenie kierunku zaznaczonych polilinii (wszystkie poziomy Data).
    void reverse_selected_polylines();
    // Dodaje obiekt do MapData i tworzy jego element; zwraca indeks obiektu (bez komendy undo).
    size_t add_object(MapObject obj);
    // Zastapienie pierwszego obiektu polaczona linia (merged) i usuniecie pozostalych - jedna komenda.
    void merge_objects(const std::vector<size_t>& indexes, DataX merged, const QString& text);

    // ---- edycja wezlow (wspolrzedne sceny; level - poziom Data, na ktorym sa uchwyty) ----
    bool move_node(size_t obj, int level, size_t poly, size_t node, const QPointF& pos);
    bool remove_node(size_t obj, int level, size_t poly, size_t node);
    bool insert_node(size_t obj, int level, size_t poly, size_t index, const QPointF& pos);
    // Podzial polilinii w wezle: obiekt dostaje pierwsza czesc, druga staje sie nowym obiektem.
    bool split_polyline(size_t obj, int level, size_t poly, size_t node);
    // Klawisz Insert: nowy wezel w miejscu kursora, na najblizszym odcinku albo na przedluzeniu linii.
    bool insert_node_at(const QPointF& scene_pos);
    // Shift+klik na krawedzi obiektu z uchwytami: nowy wezel na odcinku, jesli klik jest dosc blisko.
    bool insert_node_on_segment(PolyItem* item, const QPointF& scene_pos, double max_distance);
    // Podzial w wezle ostatnio kliknietego uchwytu (menu Edit).
    bool split_at_active_grip();

    // Wywolywane przez uchwyty. Operacje wykonywane sa po zakonczeniu obslugi zdarzenia myszy/klawiatury,
    // bo przebudowuja uchwyty, czyli usuwaja ten, ktory je zglosil.
    void grip_hovered(GripItem* grip, bool hovered);
    void set_active_grip(size_t obj, int level, size_t poly, size_t node);
    void request_node_move(size_t obj, int level, size_t poly, size_t node, const QPointF& pos);
    void request_node_removal(size_t obj, int level, size_t poly, size_t node);
    void request_split(size_t obj, int level, size_t poly, size_t node);
    // Elementy, ktore maja przetrwac clear_map() (np. linijka skali).
    void add_persistent_item(QGraphicsItem* item) {
        persistent_items_.append(item);
        addItem(item);
    }

signals:
    void progress(int value, int maximum);
    // Kursor nad uchwytem wezla: okno wylacza wtedy skroty jednoliterowe (klawisz 's' dzieli linie).
    void grip_hover_changed(bool hovered);

private:
    void apply_transformation_flags(bool ignore);
    void push_command(QUndoCommand* command);
    MapObjectItem* create_item(size_t index);
    PolyItem* poly_item(size_t index) const;
    void selection_changed();
    void update_decorations();

    MapData* map_ = nullptr;
    const MapStyles* styles_ = nullptr;
    std::vector<MapObjectItem*> object_items_;
    std::vector<MapObjectItem*> items_by_object_;  // indeks obiektu w MapData -> element
    QUndoStack* undo_stack_ = nullptr;
    QList<QGraphicsItem*> persistent_items_;
    int map_level_ = 0;
    double viewer_scale_ = 1.0;
    Tool tool_ = Tool::SelectObjects;
    std::vector<MapObjectItem*> selection_order_;
    std::vector<PolyItem*> decorated_;
    GripItem* hovered_grip_ = nullptr;
    struct GripRef {
        size_t obj;
        int level;
        size_t poly;
        size_t node;
    };
    std::optional<GripRef> active_grip_;
};

}  // namespace pwm::gui
