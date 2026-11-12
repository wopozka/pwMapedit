// Port mapCanvas.py (QGraphicsScene z obiektami mapy) - czesc do wyswietlania i zaznaczania.
#pragma once

#include <QGraphicsScene>
#include <vector>

#include "constants.hpp"
#include "map_data.hpp"

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
    // Elementy, ktore maja przetrwac clear_map() (np. linijka skali).
    void add_persistent_item(QGraphicsItem* item) {
        persistent_items_.append(item);
        addItem(item);
    }

signals:
    void progress(int value, int maximum);

private:
    void apply_transformation_flags(bool ignore);

    MapData* map_ = nullptr;
    const MapStyles* styles_ = nullptr;
    std::vector<MapObjectItem*> object_items_;
    QList<QGraphicsItem*> persistent_items_;
    int map_level_ = 0;
    double viewer_scale_ = 1.0;
    Tool tool_ = Tool::SelectObjects;
};

}  // namespace pwm::gui
