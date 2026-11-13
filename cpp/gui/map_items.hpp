// Port graficznej czesci map_items.py: elementy sceny dla POI, polilinii i polygonow oraz ich dodatki
// (etykiety, strzalki kierunku, numery adresowe, HLevel) i linijka skali.
//
// Dane obiektu (MapObject z rdzenia) nie sa kopiowane: element trzyma wskaznik do MapData i indeks obiektu.
#pragma once

#include <QGraphicsPathItem>
#include <QGraphicsPixmapItem>
#include <QGraphicsSimpleTextItem>
#include <QLineF>
#include <QPainterPath>
#include <QPen>
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
    MapLabelItemType,
    ArrowHeadItemType,
    RulerItemType,
};

QString mp_to_qstring(const std::string& cp1250);

// Elementy, ktore powyzej IGNORE_TRANSFORMATION_TRESHOLD maja stala wielkosc na ekranie.
// Python przelaczal flage w paint() kazdego elementu; tu robi to scena przy przekroczeniu progu.
class ScreenSized {
public:
    virtual ~ScreenSized() = default;
    virtual QGraphicsItem* screen_sized_item() = 0;
    void apply_transformation_flag(bool ignore);
};

// Wspolna czesc POI/polilinii/polygonu: powiazanie z obiektem w MapData.
class MapObjectItem {
public:
    MapObjectItem(MapData* map, size_t index) : map_(map), index_(index) {}
    virtual ~MapObjectItem() = default;

    MapObject& object() { return map_->objects()[index_]; }
    const MapObject& object() const { return map_->objects()[index_]; }
    size_t object_index() const { return index_; }
    long long object_type() const { return object().type.value_or(0); }

    // Ustawia geometrie i widocznosc dla poziomu mapy (odpowiednik set_map_level).
    // Obiekt oznaczony jako usuniety jest zawsze ukryty.
    virtual void set_map_level(int level) = 0;
    // Przebudowuje element z danych obiektu po ich zmianie (komendy undo/redo): polozenie, sciezka, dodatki.
    virtual void refresh() = 0;
    // Poziom Data, ktorego wezly sa teraz pokazywane (moze byc nizszy niz poziom mapy), -1 gdy zaden.
    virtual int shown_data_level() const = 0;
    virtual QGraphicsItem* graphics_item() = 0;
    // Odpowiednik set_z_value: z wedlug typu obiektu (bez podniesienia za zaznaczenie).
    virtual void set_z_value() = 0;
    void set_selection_z_value();

protected:
    MapScene* map_scene() const;
    int scene_map_level() const;
    // Przesuwanie myszka (ItemIsMovable) dopiero po przekroczeniu MIN_MOVE_DISTANCE pikseli i tylko
    // w trybie zaznaczania - jak _movable w Pythonie. Zwraca true, gdy ruch ma byc przekazany do Qt.
    bool accept_mouse_move(QGraphicsSceneMouseEvent* event);

    MapData* map_;
    size_t index_;
    bool move_started_ = false;
};

// ---------------------------------------------------------------- POI
class PoiItem : public QGraphicsPixmapItem, public MapObjectItem, public ScreenSized {
public:
    PoiItem(MapData* map, size_t index, const QPixmap& icon);
    int type() const override { return PoiItemType; }
    QGraphicsItem* graphics_item() override { return this; }
    QGraphicsItem* screen_sized_item() override { return this; }

    void set_map_level(int level) override;
    void refresh() override;
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

    std::optional<QPointF> mp_data_[5];
    int shown_level_ = -1;
    QGraphicsItem* label_ = nullptr;
    bool hovered_ = false;
};

// ---------------------------------------------------------------- polilinie i polygony
class PolyItem : public QGraphicsPathItem, public MapObjectItem {
public:
    PolyItem(MapData* map, size_t index, bool polygon);

    QGraphicsItem* graphics_item() override { return this; }
    void set_map_level(int level) override;
    void refresh() override;
    int shown_data_level() const override { return has_data_level(current_data_x_) ? current_data_x_ : -1; }
    int current_data_level() const { return current_data_x_; }
    bool has_data_level(int level) const;
    bool is_polygon() const { return polygon_; }

    QPainterPath path_for_level(int level) const;
    // Lista wielokatow (bez powtorzonego pierwszego punktu w polygonie) - jak get_polygons_from_path.
    std::vector<std::vector<QPointF>> polygons_from_path() const;

    void paint(QPainter* painter, const QStyleOptionGraphicsItem* option, QWidget* widget) override;
    // Ustawia sciezke z danych biezacego poziomu i odtwarza dodatki (etykiety, strzalki, numery).
    void rebuild();

protected:
    void hoverEnterEvent(QGraphicsSceneHoverEvent* event) override;
    void hoverLeaveEvent(QGraphicsSceneHoverEvent* event) override;
    void mousePressEvent(QGraphicsSceneMouseEvent* event) override;
    void mouseMoveEvent(QGraphicsSceneMouseEvent* event) override;
    QVariant itemChange(GraphicsItemChange change, const QVariant& value) override;
    QPainterPath stroke_shape() const;

    virtual void remove_level_items() {}
    virtual void add_level_items() {}

    QPen orig_pen_;
    bool polygon_;
    int current_data_x_ = 0;
    int built_data_x_ = -1;  // poziom, dla ktorego sa zbudowane dodatki (etykiety, strzalki, numery)
    bool hovered_ = false;
};

class PolylineItem : public PolyItem {
public:
    PolylineItem(MapData* map, size_t index, const QPen& pen);
    int type() const override { return PolylineItemType; }
    void set_z_value() override { setZValue(10); }
    QPainterPath shape() const override { return stroke_shape(); }

protected:
    void remove_level_items() override;
    void add_level_items() override;

private:
    void add_arrow_heads();
    void add_label();
    void add_hlevel_labels();
    void add_housenumber_labels();

    std::vector<QGraphicsItem*> level_items_;
};

class PolygonItem : public PolyItem {
public:
    PolygonItem(MapData* map, size_t index, const QPen& pen, const QBrush& brush, int z_value);
    int type() const override { return PolygonItemType; }
    void set_z_value() override { setZValue(z_value_); }
    void paint(QPainter* painter, const QStyleOptionGraphicsItem* option, QWidget* widget) override;
    bool small_poly() const;

protected:
    void remove_level_items() override;
    void add_level_items() override;

private:
    int z_value_;
    QGraphicsItem* label_ = nullptr;
};

// ---------------------------------------------------------------- etykiety i dodatki
class MapLabel : public QGraphicsSimpleTextItem, public ScreenSized {
public:
    MapLabel(const QString& text, QGraphicsItem* parent);
    int type() const override { return MapLabelItemType; }
    QGraphicsItem* screen_sized_item() override { return this; }
    void paint(QPainter* painter, const QStyleOptionGraphicsItem* option, QWidget* widget) override;

protected:
    double viewer_scale() const;
};

class PoiLabel : public MapLabel {
public:
    PoiLabel(const QString& text, QGraphicsItem* parent);
};

class PolylineLabel : public MapLabel {
public:
    PolylineLabel(const QString& text, QGraphicsPathItem* parent);
};

class PolygonLabel : public MapLabel {
public:
    PolygonLabel(const QString& text, QGraphicsPathItem* parent);
};

// Numer adresowy przy wezle polilinii. position: wektor od wezla na zewnatrz linii.
class PolylineAddressNumber : public MapLabel {
public:
    PolylineAddressNumber(const QLineF& position, const QString& text, QGraphicsItem* parent, bool left_side,
                          bool interpolated);
    void paint(QPainter* painter, const QStyleOptionGraphicsItem* option, QWidget* widget) override;
    static QLineF numbers_position(const QLineF& segment, int subj_position);

    // subj_position dla numbers_position
    enum { LeftBefore, LeftAfter, RightBefore, RightAfter };

private:
    void set_pos();
    QLineF position_;
    double current_scale_ = -1;
};

class PolylineLevelNumber : public MapLabel {
public:
    PolylineLevelNumber(long long hlevel, const QPointF& position, QGraphicsItem* parent);
    void paint(QPainter* painter, const QStyleOptionGraphicsItem* option, QWidget* widget) override;
};

class DirectionArrowHead : public QGraphicsPathItem, public ScreenSized {
public:
    DirectionArrowHead(const QPointF& pos, QGraphicsItem* parent);
    int type() const override { return ArrowHeadItemType; }
    QGraphicsItem* screen_sized_item() override { return this; }
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
