// Port graficznej czesci map_items.py: elementy sceny dla POI, polilinii i polygonow oraz ich dodatki
// (etykiety, strzalki kierunku, numery adresowe, HLevel) i linijka skali.
//
// Dane obiektu (MapObject z rdzenia) nie sa kopiowane: element trzyma wskaznik do MapData i indeks obiektu.
#pragma once

#include <QGraphicsPathItem>
#include <QGraphicsPixmapItem>
#include <QGraphicsSimpleTextItem>
#include <QHash>
#include <QLineF>
#include <QPainterPath>
#include <QPen>
#include <QStaticText>
#include <optional>
#include <vector>

#include "map_data.hpp"

namespace pwm::gui {

class MapScene;
class MapView;

// Typy elementow (QGraphicsItem::type()) - zamiast isinstance z Pythona.
enum ItemType {
    PoiItemType = QGraphicsItem::UserType + 1,
    PolylineItemType,
    PolygonItemType,
    RulerItemType,
    GripItemType,
    GpsTrackItemType,
    GpsWaypointItemType,
    RoadCasingItemType,
    AnnotationLayerItemType,
    PoiIconLayerItemType,
    TrailIconLayerItemType,
};

// Element, do ktorego punktow przyciagaja sie wezly (Ctrl), np. slady GPS.
class SnapSource {
public:
    virtual ~SnapSource() = default;
    virtual void snap_points(std::vector<QPointF>& out) const = 0;
};

class GripItem;

QString mp_to_qstring(const std::string& cp1250);

// Opis obiektu: etykieta, numer adresowy, numer HLevel albo strzalka kierunku. Nie jest elementem sceny - rysuje
// go AnnotationLayer (setki tysiecy elementow z ItemIgnoresTransformations spowalnialy rysowanie, hover
// i przelaczanie flagi przy progu skali). Powyzej IGNORE_TRANSFORMATION_TRESHOLD opis ma stala wielkosc
// na ekranie, ponizej maleje razem z mapa, ponizej SCALE_WITHOUT_LABELS napisy nie sa rysowane (strzalki tak).
struct Annotation {
    enum class Kind : unsigned char {
        Label,          // etykieta: lewy gorny rog w anchor + offset, obrot angle
        AddressNumber,  // numer adresowy: srodek napisu w anchor + offset (offset w pikselach, nie maleje)
        LevelNumber,    // HLevel: napis na zoltym tle, lewy gorny rog w anchor
        Arrow,          // strzalka kierunku w anchor, obrot angle
    };
    Kind kind = Kind::Label;
    bool decoration = false;  // tylko w trybie edycji wezlow (interpolowane numery adresowe)
    bool prepared = false;    // QStaticText przygotowany dla czcionki rodzaju opisu
    float angle = 0;          // stopnie
    QColor colour = Qt::black;
    QPointF anchor;  // w ukladzie elementu obiektu (dla polilinii i polygonu to wspolrzedne sceny)
    QPointF offset;  // w pikselach ekranu
    QStaticText text;
};

// Czy obiekt ma wezly na poziomie Data level (POI: co najmniej jeden wezel).
bool object_has_data_level(const MapObject& obj, int level);
// Poziomy Data obiektu, z ktorych powstaja elementy sceny (rosnaco). Obiekt bez wezlow dostaje jeden, zawsze
// ukryty element poziomu 0 - zeby mial element (zaznaczanie po undo, odswiezanie po zmianie danych).
std::vector<int> object_item_levels(const MapObject& obj);
// Poziom Data pokazywany na poziomie mapy level: wlasny, a gdy go nie ma (w zakresie EndLevel) - najwyzszy nizszy;
// -1 gdy obiekt jest ukryty (usuniety, poza EndLevel, brak nizszych poziomow).
int object_shown_data_level(const MapObject& obj, int level);

// Wspolna czesc POI/polilinii/polygonu: powiazanie z obiektem w MapData i jednym jego poziomem Data.
// Obiekt ma osobny element dla kazdego poziomu Data (object_item_levels). Element ma stala geometrie, a zmiana
// poziomu mapy tylko go pokazuje albo ukrywa - nie zmienia geometrii, wiec nie przebudowuje indeksu sceny.
class MapObjectItem {
public:
    MapObjectItem(MapData* map, size_t index, int data_level)
        : map_(map), index_(index), data_level_(data_level) {}
    virtual ~MapObjectItem() = default;

    MapObject& object() { return map_->objects()[index_]; }
    const MapObject& object() const { return map_->objects()[index_]; }
    size_t object_index() const { return index_; }
    long long object_type() const { return object().type.value_or(0); }
    // Poziom Data, z ktorego zbudowany jest element (staly).
    int data_level() const { return data_level_; }

    // Widocznosc dla poziomu mapy (odpowiednik set_map_level): element jest widoczny, gdy na tym poziomie obiekt
    // pokazuje jego poziom Data. Obiekt oznaczony jako usuniety jest zawsze ukryty.
    virtual void set_map_level(int level) = 0;
    // Przebudowuje element z danych obiektu po ich zmianie (komendy undo/redo): polozenie, sciezka, dodatki.
    virtual void refresh() = 0;
    // Poziom Data, ktorego wezly sa teraz pokazywane (moze byc nizszy niz poziom mapy), -1 gdy zaden.
    virtual int shown_data_level() const = 0;
    virtual QGraphicsItem* graphics_item() = 0;
    // Wyglad wedlug typu obiektu (ikona, pioro, wypelnienie) - po zmianie typu w panelu wlasciwosci.
    virtual void apply_style() {}
    // Odpowiednik set_z_value: z wedlug typu obiektu (bez podniesienia za zaznaczenie).
    virtual void set_z_value() = 0;
    void set_selection_z_value();

    // Opisy obiektu (rysuje je AnnotationLayer).
    std::vector<Annotation>& annotations() { return annotations_; }
    const std::vector<Annotation>& annotations() const { return annotations_; }

protected:
    MapScene* map_scene() const;
    int scene_map_level() const;
    // Przerysowanie obszaru opisow - wolac przed i po ich zmianie, przesunieciu, ukryciu elementu.
    void annotations_changed();
    // Wspolna obsluga itemChange: przesuniecie, widocznosc i zaznaczenie zmieniaja wyglad opisow.
    void annotations_item_change(QGraphicsItem::GraphicsItemChange change);
    // Przesuwanie myszka (ItemIsMovable) dopiero po przekroczeniu MIN_MOVE_DISTANCE pikseli i tylko
    // w trybie zaznaczania - jak _movable w Pythonie. Zwraca true, gdy ruch ma byc przekazany do Qt.
    bool accept_mouse_move(QGraphicsSceneMouseEvent* event);

    MapData* map_;
    size_t index_;
    int data_level_;
    bool move_started_ = false;
    std::vector<Annotation> annotations_;
};

// ---------------------------------------------------------------- POI
// POI w ukladzie sceny (bez ItemIgnoresTransformations - takie elementy indeks BSP przeglada liniowo przy kazdym
// zapytaniu). Ikone rysuje PoiIconLayer; element ma ItemHasNoContents i sluzy do zaznaczania, najechania
// i przeciagania. Zaznaczony albo podswietlony POI rysuje sie sam (nad innymi, z ramka). Ikona ma powyzej
// IGNORE_TRANSFORMATION_TRESHOLD stala wielkosc na ekranie, ponizej maleje razem z mapa: shape() i paint() skaluja
// ja o icon_scale(). boundingRect jest staly - rozmiar ikony przy skali progu, najwiekszy w jednostkach sceny
// (nadzbior) - wiec przyblizanie nie zmienia geometrii w indeksie.
class PoiItem : public QGraphicsPixmapItem, public MapObjectItem {
public:
    PoiItem(MapData* map, size_t index, int data_level, const QPixmap& icon);
    int type() const override { return PoiItemType; }
    QGraphicsItem* graphics_item() override { return this; }
    QPainterPath shape() const override;
    // Skala ikony w ukladzie elementu: 1 do progu, powyzej prog/skala widoku (stala wielkosc na ekranie).
    double icon_scale() const;
    // Prostokat faktycznie rysowanej ikony (w ukladzie elementu).
    QRectF icon_rect() const;
    // Czy ikone rysuje sam element (zaznaczony albo podswietlony), a nie PoiIconLayer.
    bool paints_itself() const { return !(flags() & QGraphicsItem::ItemHasNoContents); }

    void set_map_level(int level) override;
    void refresh() override;
    void apply_style() override;
    int shown_data_level() const override { return shown_level_; }
    void set_z_value() override { setZValue(20); }
    void add_label();
    void paint(QPainter* painter, const QStyleOptionGraphicsItem* option, QWidget* widget) override;

protected:
    void hoverEnterEvent(QGraphicsSceneHoverEvent* event) override;
    void hoverLeaveEvent(QGraphicsSceneHoverEvent* event) override;
    void mousePressEvent(QGraphicsSceneMouseEvent* event) override;
    void mouseMoveEvent(QGraphicsSceneMouseEvent* event) override;
    QVariant itemChange(GraphicsItemChange change, const QVariant& value) override;

private:
    void read_positions();
    // Zaznaczony albo podswietlony POI rysuje sie sam, pozostale rysuje PoiIconLayer.
    void update_self_painting();

    std::optional<QPointF> mp_data_[5];
    int shown_level_ = -1;
    bool hovered_ = false;
};

// ---------------------------------------------------------------- polilinie i polygony
class PolyItem : public QGraphicsPathItem, public MapObjectItem {
public:
    PolyItem(MapData* map, size_t index, int data_level, bool polygon);

    QGraphicsItem* graphics_item() override { return this; }
    void set_map_level(int level) override;
    void refresh() override;
    int shown_data_level() const override { return has_data_level(data_level_) ? data_level_ : -1; }
    bool has_data_level(int level) const;
    bool is_polygon() const { return polygon_; }

    QPainterPath path_for_level(int level) const;
    // Wezly pokazywanego poziomu (we wspolrzednych sceny), po jednej liscie na czesc obiektu.
    std::vector<std::vector<QPointF>> shown_nodes() const;

    // ---- tryb edycji wezlow ----
    // Uchwyty na wezlach pokazywanego poziomu (decorate/undecorate z Pythona). W trakcie edycji obiekt
    // nie daje sie przesuwac, bo Qt przesuwalby go razem z przeciaganym uchwytem.
    void decorate();
    void undecorate();
    bool decorated() const { return !grips_.empty(); }
    const std::vector<GripItem*>& grips() const { return grips_; }
    // Podglad przeciagania uchwytu: sciezka z jednym wezlem w nowym miejscu (bez zmiany danych).
    void preview_node_position(size_t poly_num, size_t node_num, const QPointF& pos);
    // Podglad wstawiania wezla (przeciaganie z krawedzi): sciezka z nowym wezlem przed indeksem index.
    void preview_inserted_node(size_t poly_num, size_t index, const QPointF& pos);

    // Miejsce wstawienia nowego wezla najblizej punktu: czesc, indeks (przed ktorym wstawic) i polozenie.
    struct NodeInsertion {
        size_t poly_num = 0;
        size_t index = 0;
        QPointF position;
        double distance = 0;
    };
    // on_segment: polozenie na odcinku (Shift+klik), inaczej sam punkt (klawisz Insert); extend_ends: dla
    // otwartej polilinii punkt za koncem linii przedluza ja zamiast wstawiac wezel na pierwszym/ostatnim odcinku.
    std::optional<NodeInsertion> node_insertion(const QPointF& scene_pos, bool on_segment, bool extend_ends) const;
    // Najmniejsza liczba wezlow czesci obiektu (polilinia 2, polygon 3).
    size_t min_nodes() const { return polygon_ ? 3 : 2; }
    // Lista wielokatow (bez powtorzonego pierwszego punktu w polygonie) - jak get_polygons_from_path.
    std::vector<std::vector<QPointF>> polygons_from_path() const;

    void paint(QPainter* painter, const QStyleOptionGraphicsItem* option, QWidget* widget) override;
    // Ustawia sciezke z danych poziomu elementu i odtwarza dodatki (etykiety, strzalki, numery).
    void rebuild();

    // Trafienie (hover, klikniecie, zaznaczanie prostokatem) liczone geometrycznie z wezlow sciezki zamiast przez
    // shape(): shape() obrysowuje cala sciezke przy kazdym wywolaniu (QPainterPathStroker), a Qt wola je dla kazdego
    // obiektu, ktorego prostokat obejmuje kursor. Ten sam obszar co shape(): polilinia (i polygon w edycji wezlow)
    // - odleglosc od odcinkow do szerokosci piora, polygon - wnetrze (regula parzystosci) i pol szerokosci piora
    // wokol krawedzi. Rozni sie tylko na koncach i zalamaniach linii (zaokraglone zamiast scietych).
    bool collidesWithPath(const QPainterPath& path, Qt::ItemSelectionMode mode = Qt::IntersectsItemShape) const override;
    bool contains(const QPointF& point) const override;
    // Czy prostokat (w ukladzie elementu, moze miec zerowy rozmiar) trafia w obiekt.
    bool hits(const QRectF& rect) const;

protected:
    void hoverEnterEvent(QGraphicsSceneHoverEvent* event) override;
    void hoverLeaveEvent(QGraphicsSceneHoverEvent* event) override;
    void mousePressEvent(QGraphicsSceneMouseEvent* event) override;
    void mouseMoveEvent(QGraphicsSceneMouseEvent* event) override;
    QVariant itemChange(GraphicsItemChange change, const QVariant& value) override;
    QPainterPath stroke_shape() const;

    virtual void remove_level_items() {}
    virtual void add_level_items() {}
    // Dodatki widoczne tylko w trybie edycji wezlow (np. interpolowane numery adresowe polilinii).
    virtual void add_decoration_items() {}
    virtual void remove_decoration_items() {}

    QPen orig_pen_;
    bool polygon_;
    bool hovered_ = false;
    std::vector<GripItem*> grips_;
};

class PolylineItem : public PolyItem {
public:
    PolylineItem(MapData* map, size_t index, int data_level, const QPen& pen);
    int type() const override { return PolylineItemType; }
    void set_z_value() override { setZValue(10); }
    void apply_style() override;
    QPainterPath shape() const override { return stroke_shape(); }

protected:
    void remove_level_items() override;
    void add_level_items() override;

private:
    void add_arrow_heads();
    void add_label();
    void add_hlevel_labels();
    void add_housenumber_labels();
    void add_decoration_items() override;
    void remove_decoration_items() override;
};

class PolygonItem : public PolyItem {
public:
    PolygonItem(MapData* map, size_t index, int data_level, const QPen& pen, const QBrush& brush, int z_value);
    int type() const override { return PolygonItemType; }
    void set_z_value() override { setZValue(z_value_); }
    void apply_style() override;
    void paint(QPainter* painter, const QStyleOptionGraphicsItem* option, QWidget* widget) override;
    // Jak shape() w Pythonie: w trybie edycji wezlow tylko krawedz (krzyzyk i najechanie tylko na obwodzie).
    QPainterPath shape() const override { return decorated() ? stroke_shape() : QGraphicsPathItem::shape(); }
    bool small_poly() const;

protected:
    void remove_level_items() override;
    void add_level_items() override;

private:
    int z_value_;
};

// ---------------------------------------------------------------- uchwyt wezla
// Port GripItem: kwadrat na wezle obiektu w trybie edycji wezlow (pierwszy wezel czerwony).
//  - przeciagniecie przesuwa wezel (jedna komenda undo po puszczeniu przycisku),
//  - Ctrl+klik usuwa wezel,
//  - klawisz 's' nad uchwytem dzieli polilinie w tym wezle.
// Operacje sa wykonywane po zakonczeniu obslugi zdarzenia, bo przebudowuja uchwyty (usuwaja ten obiekt).
class GripItem : public QGraphicsPathItem {
public:
    GripItem(PolyItem* parent, int data_level, size_t poly_num, size_t node_num, const QPointF& pos);
    ~GripItem() override;
    int type() const override { return GripItemType; }
    PolyItem* poly_item() const { return parent_; }
    int data_level() const { return data_level_; }
    size_t poly_num() const { return poly_num_; }
    size_t node_num() const { return node_num_; }
    // Uchwyt tylko do pokazania (nowy wezel przeciagany z krawedzi): wyglada jak przeciagany uchwyt,
    // nie reaguje na mysz i jego przesuniecie nie zmienia sciezki obiektu.
    void set_preview_only();
    // Uchwyt aktywnego wezla (pokazywanego w panelu wlasciwosci) rysowany jest na niebiesko.
    bool is_active() const;
    void paint(QPainter* painter, const QStyleOptionGraphicsItem* option, QWidget* widget) override;

protected:
    QVariant itemChange(GraphicsItemChange change, const QVariant& value) override;
    void hoverEnterEvent(QGraphicsSceneHoverEvent* event) override;
    void hoverLeaveEvent(QGraphicsSceneHoverEvent* event) override;
    void mousePressEvent(QGraphicsSceneMouseEvent* event) override;
    void mouseMoveEvent(QGraphicsSceneMouseEvent* event) override;
    void mouseReleaseEvent(QGraphicsSceneMouseEvent* event) override;
    void keyPressEvent(QKeyEvent* event) override;

private:
    void set_hover(bool hover);
    bool first_grip() const { return node_num_ == 0; }

    PolyItem* parent_;
    int data_level_;
    size_t poly_num_;
    size_t node_num_;
    QPointF press_pos_;
    bool ready_ = false;  // itemChange dopiero po zbudowaniu uchwytu
    MapScene* hover_scene_ = nullptr;  // scena powiadomiona o najechaniu (do zwolnienia w destruktorze)
};

// ---------------------------------------------------------------- opisy
// Polozenie numeru adresowego przy odcinku: wektor od wezla na zewnatrz linii (port get_numbers_position).
enum NumberSide { LeftBefore, LeftAfter, RightBefore, RightAfter };
QLineF numbers_position(const QLineF& segment, int side);

// Jeden element rysujacy opisy (Annotation) wszystkich obiektow mapy w odswiezanym fragmencie widoku, w pikselach
// ekranu. Nad obiektami (z 30), pod zaznaczonymi. Nie reaguje na mysz (pusty ksztalt).
class AnnotationLayer : public QGraphicsItem {
public:
    explicit AnnotationLayer(MapScene* scene);
    int type() const override { return AnnotationLayerItemType; }
    QRectF boundingRect() const override { return rect_; }
    QPainterPath shape() const override { return {}; }
    void set_rect(const QRectF& rect);
    void paint(QPainter* painter, const QStyleOptionGraphicsItem* option, QWidget* widget) override;

    // Opisy wychodza poza element obiektu najwyzej o tyle pikseli (wybor obiektow do rysowania, przerysowanie).
    static constexpr double MARGIN_PX = 300;

private:
    MapScene* map_scene_;
    QRectF rect_;
};

// Ikony POI: jeden element rysujacy ikony wszystkich widocznych POI w odswiezanym fragmencie widoku (z 20, jak POI).
// POI do rysowania bierze z indeksu sceny. Pomija POI, ktore rysuja sie same (zaznaczone, podswietlone).
// Nie reaguje na mysz (pusty ksztalt).
class PoiIconLayer : public QGraphicsItem {
public:
    explicit PoiIconLayer(MapScene* scene);
    int type() const override { return PoiIconLayerItemType; }
    QRectF boundingRect() const override { return rect_; }
    QPainterPath shape() const override { return {}; }
    void set_rect(const QRectF& rect);
    void paint(QPainter* painter, const QStyleOptionGraphicsItem* option, QWidget* widget) override;

private:
    MapScene* map_scene_;
    QRectF rect_;
};

// Obwodki drog i kolei: jeden element dla calej mapy, miedzy polygonami (z 1-8) a poliliniami (z 10). Rysuje
// szersza, ciemniejsza linie pod kazda widoczna droga w odswiezanym fragmencie widoku (pod kolejka dodatkowo
// biale tlo, wiec przerwy miedzy czarnymi odcinkami sa biale). Wszystkie obwodki leza pod
// wszystkimi drogami, wiec skrzyzowania sa czyste (obwodka jednej drogi nie przecina drugiej). Nie reaguje
// na mysz (pusty ksztalt) i nie ma wlasnych danych - sciezki bierze z elementow drog przy kazdym rysowaniu.
class RoadCasingLayer : public QGraphicsItem {
public:
    explicit RoadCasingLayer(const MapScene* scene);
    int type() const override { return RoadCasingItemType; }
    QRectF boundingRect() const override { return rect_; }
    QPainterPath shape() const override { return {}; }
    // Obszar mapy (prostokat sceny); obwodki poza nim nie sa rysowane.
    void set_rect(const QRectF& rect);
    void paint(QPainter* painter, const QStyleOptionGraphicsItem* option, QWidget* widget) override;

private:
    const MapScene* map_scene_;
    QRectF rect_;
};

// Ikony szlakow: jeden element dla calej mapy rysujacy wzdluz szlakow pieszych i chodnikow ikone pieszego,
// a wzdluz szlakow rowerowych i drog dla rowerow ikone roweru (MapStyles::trail_icon) - krazek w kolorze szlaku
// (droga dla rowerow i chodnik: bialy, szlak wielokolorowy: cwiartki). Ikony sa pionowe, o stalej wielkosci na
// ekranie, rozmieszczone co okolo TRAIL_ICON_SPACING_PX pikseli drogi na ekranie, liczac od poczatku czesci linii
// (przesuwanie mapy ich nie przestawia). Kazdy typ szlaku ma swoje przesuniecie (trail_icon_slot), wiec szlaki
// roznych kolorow na jednej drodze pokazuja ikony obok siebie. Ponizej SCALE_WITHOUT_TRAIL_ICONS ikony nie sa
// rysowane. Linie bierze z indeksu sceny (jak PoiIconLayer; przejscie po wszystkich elementach mapy kosztowalo
// 3-6 ms na przerysowanie), polozenia liczy przy kazdym rysowaniu - bez wlasnych danych.
// Uwaga: w QGraphicsScene::render (program go nie uzywa) indeks nie zwraca elementow juz narysowanych (Qt oznacza
// je itemDiscovered), wiec ikony linii lezacych pod warstwa nie powstana - tak samo w PoiIconLayer.
class TrailIconLayer : public QGraphicsItem {
public:
    explicit TrailIconLayer(const MapScene* scene);
    int type() const override { return TrailIconLayerItemType; }
    QRectF boundingRect() const override { return rect_; }
    QPainterPath shape() const override { return {}; }
    void set_rect(const QRectF& rect);
    void paint(QPainter* painter, const QStyleOptionGraphicsItem* option, QWidget* widget) override;

    // Srodki ikon (we wspolrzednych ekranu) linii path (moze miec kilka czesci) dla typu o numerze slot;
    // to_screen: z ukladu sciezki na ekran. Czesc krotsza niz 1,5 ikony nie dostaje ikony.
    static void icon_positions(const QPainterPath& path, const QTransform& to_screen, int slot,
                               std::vector<QPointF>& out);
    // Ikona typu (krazek z rysunkiem) o rozmiarze TRAIL_ICON_SIZE_PX dla gestosci pikseli dpr.
    static QPixmap make_icon(long long poly_type, QColor colour, double dpr);

private:
    const QPixmap& icon(long long poly_type, double dpr);

    const MapScene* map_scene_;
    QRectF rect_;
    QHash<long long, QPixmap> icons_;
    double icons_dpr_ = 0;
};

// Linijka skali w lewym gornym rogu widoku: odcinek dlugosci 1 cm na ekranie i jego dlugosc w terenie.
class MapRuler : public QGraphicsPathItem {
public:
    MapRuler(MapView* view, const Projection* projection);
    int type() const override { return RulerItemType; }
    void set_projection(const Projection* projection) { projection_ = projection; }
    void move_to();   // po przesunieciu widoku
    void scale_to();  // po zmianie skali
    double map_scale();  // mianownik skali mapy (1:N)

private:
    void draw_ruler();
    void calculate_geo_distance();
    QPointF calculate_point_2() const;

    MapView* view_;
    const Projection* projection_;
    std::optional<double> one_cm_geo_distance_;
    QGraphicsSimpleTextItem* distance_label_ = nullptr;
    int screen_dpi_;
};

}  // namespace pwm::gui
