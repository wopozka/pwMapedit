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
class QTimer;
class QUndoCommand;
class QUndoStack;

namespace pwm::gui {

class MapStyles;
class MapObjectItem;
class PolyItem;
class GripItem;
class RoadCasingLayer;
class AnnotationLayer;
class PoiIconLayer;
class TrailIconLayer;

// Wezel wskazany uchwytem: obiekt (indeks w MapData), poziom Data, czesc i numer wezla.
struct GripRef {
    size_t obj;
    int level;
    size_t poly;
    size_t node;
};

// Wypelnienie polygonow (View -> Wypelnienie polygonow).
enum class PolygonFill {
    Solid,        // stale
    Transparent,  // polprzezroczyste - jak polygon zaznaczony
    Outline,      // tylko kontury: bez wypelnienia, obrys w kolorze polygonu
};

// Warstwy obiektow mapy (menu View -> Warstwy). Szlaki (MapStyles::is_trail) to polilinie, ale maja wlasna
// warstwe - wylaczenie polilinii nie ukrywa szlakow i odwrotnie.
enum class MapLayer { Poi, Polyline, Polygon, Trail };
constexpr int MAP_LAYER_COUNT = 4;

// Warstwa obiektu: z rodzaju, a dla polilinii takze z typu. Obiekt Basic nie nalezy do zadnej warstwy.
std::optional<MapLayer> layer_of(const MapObject& obj);
// Warstwa rodzaju (bez typu - polilinia to warstwa polilinii).
std::optional<MapLayer> layer_of(ObjectKind kind);

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

    // Skala widoku (iloczyn wszystkich powiekszen). Ikony POI i opisy maja ponizej
    // IGNORE_TRANSFORMATION_TRESHOLD rozmiar zmniejszony o te skale, powyzej staly rozmiar na ekranie.
    double viewer_scale() const { return viewer_scale_; }
    void set_viewer_scale(double scale);

    // Wypelnienie polygonow: stale (domyslnie), polprzezroczyste albo tylko kontury. Zaznaczony polygon wyglada
    // tak samo w kazdym trybie.
    PolygonFill polygon_fill() const { return polygon_fill_; }
    void set_polygon_fill(PolygonFill fill);

    // Obwodki drog (ciemniejsza, szersza linia pod droga - widac jasne drogi na jasnym tle). Domyslnie wylaczone.
    bool road_casing() const;
    void set_road_casing(bool on);

    // Ikony pieszego i roweru wzdluz szlakow (TrailIconLayer). Domyslnie wlaczone.
    bool trail_icons() const;
    void set_trail_icons(bool on);
    // Ikony routingu: zakaz ruchu i oplata na drogach (TrailIconLayer). Domyslnie wlaczone.
    bool routing_icons() const;
    void set_routing_icons(bool on);
    // Ikony nalozonych drog (wspolne odcinki widocznych drog, od skali SCALE_WITHOUT_OVERLAP_ICONS;
    // TrailIconLayer). Domyslnie wlaczone.
    bool overlap_icons() const;
    void set_overlap_icons(bool on);

    // Warstwy POI, polilinii, polygonow i szlakow (menu View -> Warstwy). Wylaczona warstwa ukrywa elementy jej
    // obiektow, a z nimi wszystko, co rysowane jest tylko dla widocznych elementow: etykiety, ikony POI, obwodki,
    // ikony szlakow i routingu; ukrytych obiektow nie mozna tez kliknac, zaznaczyc ramka ani przyciagnac do nich.
    // Zaznaczenie obiektow ukrywanej warstwy jest zdejmowane. Domyslnie wszystkie warstwy sa wlaczone.
    bool layer_visible(MapLayer layer) const;
    // Czy warstwa obiektu jest wlaczona (obiekt Basic - zawsze).
    bool layer_visible(const MapObject& obj) const;
    void set_layer_visible(MapLayer layer, bool on);
    // Wlacza warstwe obiektu, jesli jest wylaczona - przed utworzeniem, wklejeniem, dodaniem albo zmiana obiektu
    // (zmiana typu moze przeniesc linie do warstwy szlakow), zeby obiekt byl widoczny i mogl zostac zaznaczony.
    void ensure_layer_visible(MapLayer layer);
    void ensure_layer_visible(const MapObject& obj);

    Tool tool() const { return tool_; }
    // Zmiana narzedzia; w trybie edycji wezlow zaznaczone polilinie i polygony dostaja uchwyty.
    void set_tool(Tool tool);

    // Prostokat sceny z prostokata ograniczajacego mapy (+0.001 stopnia z kazdej strony).
    void set_canvas_rectangle(const GeoBBox& bbox, const Projection& projection);

    // Wszystkie elementy obiektow mapy (po jednym na poziom Data obiektu; ukryte tez).
    const std::vector<MapObjectItem*>& object_items() const { return object_items_; }
    // Element sceny obiektu o danym indeksie w MapData: widoczny na biezacym poziomie mapy, a gdy obiekt jest
    // ukryty - element najnizszego poziomu Data. nullptr, gdy obiekt nie ma elementow.
    MapObjectItem* item_for_object(size_t index) const;
    // Wszystkie elementy obiektu (rosnaco wedlug poziomu Data).
    const std::vector<MapObjectItem*>& items_for_object(size_t index) const;
    // Przebudowuje elementy obiektu po zmianie jego danych (wywolywane przez komendy undo/redo): elementy
    // poziomow Data, ktorych juz nie ma, sa usuwane, a dla nowych poziomow tworzone.
    void refresh_object(size_t index);
    // Zaznaczone obiekty mapy, w kolejnosci indeksow w MapData.
    std::vector<MapObjectItem*> selected_object_items() const;
    // Zaznaczone obiekty mapy w kolejnosci zaznaczania (laczenie bierze wlasciwosci z pierwszego).
    std::vector<MapObjectItem*> selected_object_items_in_order() const;

    // Stos undo/redo okna; komendy edycji sa na nim umieszczane przez widok i okno.
    QUndoStack* undo_stack() const { return undo_stack_; }
    void set_undo_stack(QUndoStack* stack);

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
    // level: poziom Data nowego obiektu (DataN); domyslnie biezacy poziom mapy, zeby obiekt narysowany na
    // poziomie > 0 zostal na nim (a nie trafil do Data0).
    std::optional<size_t> create_object(ObjectKind kind, const std::vector<QPointF>& nodes,
                                        const std::vector<std::string>& fields = {},
                                        const std::vector<std::string>& comments = {},
                                        std::optional<int> level = std::nullopt);
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

    // ---- obrot (Shift+kolko w edycji wezlow) ----
    // Obiekt z uchwytami pod kursorem: polygon - wnetrze albo krawedz, polilinia - linia w odleglosci max_distance.
    // Przy kilku - najblizszy. nullptr, gdy zaden.
    PolyItem* decorated_item_at(const QPointF& scene_pos, double max_distance) const;
    // Obrot obiektu o degrees (dodatnie - przeciwnie do ruchu wskazowek zegara na ekranie) wokol jego srodka
    // ciezkosci, wszystkie poziomy Data. Kolejne wywolania dla tego samego obiektu tworza jeden gest: srodek
    // liczony raz (z pokazywanego poziomu), jedna komenda undo, krzyzyk w srodku i laczny kat w komunikacie.
    // Gest konczy sie po ROTATION_GESTURE_MS bez obrotu albo przy innej zmianie (undo, narzedzie, zaznaczenie).
    bool rotate_object(size_t obj, double degrees);
    void end_rotation();
    bool rotation_active() const { return rotation_.has_value(); }
    static constexpr int ROTATION_GESTURE_MS = 1000;

    // Wywolywane przez uchwyty. Operacje wykonywane sa po zakonczeniu obslugi zdarzenia myszy/klawiatury,
    // bo przebudowuja uchwyty, czyli usuwaja ten, ktory je zglosil.
    void grip_hovered(GripItem* grip, bool hovered);
    void set_active_grip(size_t obj, int level, size_t poly, size_t node);
    // Ostatnio klikniety uchwyt (wezel edytowany w panelu wlasciwosci); brak, gdy uchwyty zdjeto.
    const std::optional<GripRef>& active_grip() const { return active_grip_; }
    // Wezel sasiadujacy z aktywnym (delta -1: poprzedni, +1: nastepny) w kolejnosci czesci poziomu Data
    // i wezlow w czesci; brak, gdy aktywny jest pierwszy/ostatni wezel albo nie ma aktywnego uchwytu.
    std::optional<GripRef> neighbour_grip(int delta) const;
    // Uaktywnia wezel jak klikniecie uchwytu i przewija widoki tak, zeby byl widoczny.
    void activate_grip(const GripRef& grip);

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
    // Tools -> Dodaj bojki wiadukt: POI WIADUKT (VIADUCT_POI_TYPE) w punktach, w ktorych zaznaczone polilinie
    // przecinaja sie (kazda para, pokazywany poziom; bez wspolnych wezlow i stykow - patrz line_crossings).
    // Przeciecia, przy ktorych POI wiadukt juz stoi, sa pomijane. Jedna komenda undo.
    // Zwraca opis wyniku; changed - czy dodano POI.
    QString add_viaduct_pois(bool* changed = nullptr);
    // Tools -> Dodaj bojki ślepy: POI SLEPY (DEAD_END_POI_TYPE) na kazdym koncu zaznaczonej polilinii, ktory nie
    // ma wspolnego wezla z inna droga (dowolny wezel drogi, pokazywany poziom; tez z inna czescia tej linii).
    // Linia zamknieta nie ma koncow. Konce z POI slepy sa pomijane. Jedna komenda undo.
    QString add_dead_end_pois(bool* changed = nullptr);
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
    // Przerysowanie obszaru opisow obiektu (AnnotationLayer); pomijane w trakcie przebudowy wszystkich elementow.
    void update_annotations(MapObjectItem* item);
    AnnotationLayer* annotation_layer() const { return annotation_layer_; }

signals:
    void progress(int value, int maximum);
    // Kursor nad uchwytem wezla: okno wylacza wtedy skroty jednoliterowe (klawisz 's' dzieli linie).
    void grip_hover_changed(bool hovered);
    void active_grip_changed();
    void tool_changed();
    // Warstwa zostala wlaczona albo wylaczona (tez przez ensure_layer_visible) - okno uaktualnia menu.
    void layer_visibility_changed(MapLayer layer, bool on);
    // Komunikat dla paska stanu (np. laczny kat obrotu).
    void message(const QString& text);

private:
    // POI typu type (Data0) w punktach (wspolrzedne sceny) jedna komenda undo o tekscie text (%1 - liczba POI).
    // Punkty blizsze niz distance istniejacemu POI tego typu sa pomijane (licznik w skipped). Zwraca liczbe dodanych.
    int add_marker_pois(long long type, const std::vector<PointF>& points, double distance, const QString& text,
                        size_t* skipped);
    bool active_grip_valid() const;
    void push_command(QUndoCommand* command);
    // Tworzy elementy obiektu dla wszystkich jego poziomow Data; zwraca element najnizszego poziomu.
    MapObjectItem* create_items(size_t index);
    MapObjectItem* create_item(size_t index, int data_level);
    // Usuwa element obiektu (poziom Data zniknal z danych) ze sceny i list.
    void remove_item(MapObjectItem* item);
    PolyItem* poly_item(size_t index) const;
    // Przerysowanie uchwytow obiektu (wyrozniony uchwyt aktywnego wezla).
    void update_grips(size_t obj) const;
    void selection_changed();
    void update_decorations();

    MapData* map_ = nullptr;
    const MapStyles* styles_ = nullptr;
    std::vector<MapObjectItem*> object_items_;
    std::vector<std::vector<MapObjectItem*>> items_by_object_;  // indeks obiektu w MapData -> elementy
    QUndoStack* undo_stack_ = nullptr;
    QList<QGraphicsItem*> persistent_items_;
    int map_level_ = 0;
    PolygonFill polygon_fill_ = PolygonFill::Solid;
    double viewer_scale_ = 1.0;
    Tool tool_ = Tool::SelectObjects;
    std::vector<MapObjectItem*> selection_order_;
    std::vector<PolyItem*> decorated_;
    GripItem* hovered_grip_ = nullptr;
    std::optional<GripRef> active_grip_;
    QGraphicsPathItem* highlight_ = nullptr;
    QGraphicsEllipseItem* snap_indicator_ = nullptr;
    RoadCasingLayer* road_casing_ = nullptr;
    AnnotationLayer* annotation_layer_ = nullptr;
    PoiIconLayer* poi_icon_layer_ = nullptr;
    TrailIconLayer* trail_icon_layer_ = nullptr;
    bool rebuilding_all_ = false;  // set_map/set_map_level: jedno przerysowanie na koncu zamiast na element
    struct RotationGesture {
        size_t obj;
        PointF center;
        double total_degrees;
        int id;
    };
    std::optional<RotationGesture> rotation_;
    int rotation_gestures_ = 0;
    bool pushing_rotation_ = false;
    QTimer* rotation_timer_ = nullptr;
    QGraphicsPathItem* rotation_marker_ = nullptr;
    long long last_used_type_[4] = {0, 0, 0, 0};  // wedlug ObjectKind
    bool layer_visible_[MAP_LAYER_COUNT] = {true, true, true, true};  // wedlug MapLayer
};

}  // namespace pwm::gui
