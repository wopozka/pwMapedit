// Port mapCanvas.py (QGraphicsScene z obiektami mapy): wyswietlanie, zaznaczanie i operacje edycyjne.
#pragma once

#include <QGraphicsScene>
#include <QPainterPath>
#include <QPointF>
#include <optional>
#include <vector>

#include "constants.hpp"
#include "map_data.hpp"

class QGraphicsEllipseItem;
class QGraphicsPathItem;
class QMimeData;
class QUndoCommand;
class QUndoStack;

namespace pwm::gui {

class MapStyles;
class MapObjectItem;
class PolyItem;
class GripItem;

// Wezel wskazany uchwytem: obiekt (indeks w MapData), poziom Data, czesc i numer wezla.
struct GripRef {
    size_t obj;
    int level;
    size_t poly;
    size_t node;
};

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
    // ---- schowek (format zgodny z wersja Python: application/json + tekst rekordow mp) ----
    // Rekordy zaznaczonych obiektow; reference - punkt odniesienia zapisywany jako MouseScenePos
    // (wklejone obiekty sa przesuwane o odleglosc od niego do kursora). nullptr, gdy nic nie zaznaczono.
    QMimeData* copy_selected(const QPointF& reference) const;
    // Wkleja obiekty ze schowka jako nowe (jedna komenda) i zaznacza je; zwraca liczbe wklejonych.
    // mouse: biezaca pozycja kursora; bez niej (albo bez MouseScenePos) obiekty trafiaja w oryginalne miejsce.
    int paste(const QMimeData* mime, std::optional<QPointF> mouse);

    // ---- tworzenie obiektow (narzedzia Create*) ----
    // Nowy obiekt z wezlow (wspolrzedne sceny) i ostatnio uzytego typu: komenda undo, potem narzedzie
    // zaznaczania i zaznaczenie nowego obiektu (jak command_create_* w Pythonie). Zwraca indeks obiektu.
    // fields: dodatkowe pola rekordu (np. "Label=..."), comments: linie komentarza - tekst w cp1250.
    std::optional<size_t> create_object(ObjectKind kind, const std::vector<QPointF>& nodes,
                                        const std::vector<std::string>& fields = {},
                                        const std::vector<std::string>& comments = {});
    // Typ nadawany nowym obiektom - ostatnio wybrany w panelu wlasciwosci dla danego rodzaju (last_used_type).
    long long last_used_type(ObjectKind kind) const;
    void set_last_used_type(ObjectKind kind, long long type);

    // ---- przyciaganie do wezlow (Ctrl) ----
    // Najblizszy wezel polilinii lub polygonu (pokazywany poziom) albo punkt sladu GPS / waypoint w odleglosci
    // max_distance; excluded - obiekt pomijany (np. ten, ktorego wezel jest przeciagany).
    std::optional<QPointF> closest_node(const QPointF& pos, double max_distance,
                                        const MapObjectItem* excluded = nullptr) const;
    // Niebieskie kolko w miejscu, do ktorego wezel zostanie przyciagniety; brak punktu je ukrywa.
    void show_snap_indicator(std::optional<QPointF> pos);
    bool snap_indicator_visible() const;

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
    // Ostatnio klikniety uchwyt (wezel edytowany w panelu wlasciwosci); brak, gdy uchwyty zdjeto.
    const std::optional<GripRef>& active_grip() const { return active_grip_; }

    // Zamiana danych obiektu jedna komenda undo (panel wlasciwosci: typ, etykiety, numeracja wezla...).
    void replace_object(size_t obj, MapObject after, const QString& text);
    // Usuniecie jednego obiektu (np. gdy w karcie Elements usunieto jego ostatnia czesc).
    void delete_object(size_t obj, const QString& text);
    // Zmiana obiektu i nowy obiekt jedna komenda (ekstrakcja czesci); zwraca indeks nowego obiektu.
    std::optional<size_t> replace_and_add(size_t obj, MapObject after, MapObject added, const QString& text);
    // Odejmowanie polygonow: od pierwszego zaznaczonego odejmowany jest drugi (na pokazywanym poziomie Data
    // pierwszego; pozostale poziomy bez zmian). delete_second - drugi polygon jest usuwany w tej samej komendzie.
    // Zwraca opis wyniku; changed - czy mapa sie zmienila.
    QString subtract_selected_polygons(bool delete_second, bool* changed = nullptr);
    // Zamiana zaznaczonych obiektow rodzaju from (polygon albo polilinia) na drugi rodzaj: nowy obiekt z tymi
    // samymi wlasciwosciami i geometria (ostatnio uzyty typ docelowego rodzaju), stary usuwany - jedna komenda.
    // Zwraca opis wyniku; changed - czy mapa sie zmienila.
    QString convert_selected(ObjectKind from, bool* changed = nullptr);
    bool has_selected(ObjectKind kind) const;
    // Podswietlenie czesci obiektu wybranej w panelu (karta Elements); pusta sciezka zdejmuje podswietlenie.
    void highlight_path(const QPainterPath& path, bool polygon);
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
    void active_grip_changed();
    void tool_changed();

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
    std::optional<GripRef> active_grip_;
    QGraphicsPathItem* highlight_ = nullptr;
    QGraphicsEllipseItem* snap_indicator_ = nullptr;
    long long last_used_type_[4] = {0, 0, 0, 0};  // wedlug ObjectKind
};

}  // namespace pwm::gui
