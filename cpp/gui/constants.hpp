// Port pwmapedit_constants.py (czesc potrzebna w GUI).
#pragma once

#include <Qt>
#include <array>

namespace pwm::gui {

// Powyzej tej skali widoku ikony, napisy i strzalki nie skaluja sie razem z mapa (stala wielkosc na ekranie).
constexpr double IGNORE_TRANSFORMATION_TRESHOLD = 1.0;
constexpr double SCALE_WITHOUT_LABELS = 0.5;
constexpr double SCALE_WITHOUT_POIS = 0.25;
constexpr double SCALE_WITHOUT_SMALL_POLYS = 0.25;
constexpr double NEW_OBJECT_CREATION_Z_VAL = 200;
// Obwodki drog: nad polygonami (z 1-8), pod poliliniami (z 10).
constexpr double ROAD_CASING_Z_VAL = 9;
// Opisy (etykiety, numery, strzalki): nad wszystkimi obiektami (z do 20), pod zaznaczonymi.
constexpr double ANNOTATION_Z_VAL = 30;
constexpr double SELECTED_OBJECT_Z_VAL = 1000;
constexpr double HIGHLIGHTED_POLY_Z_VAL = 2000;
constexpr Qt::GlobalColor LEFT_SIDE_NUM_MAIN = Qt::blue;
constexpr Qt::GlobalColor LEFT_SIDE_NUM_INTER = Qt::red;
constexpr Qt::GlobalColor RIGHT_SIDE_NUM_MAIN = Qt::blue;
constexpr Qt::GlobalColor RIGHT_SIDE_NUM_INTER = Qt::red;
constexpr double MINIMAL_GEO_DISTANCE = 7;  // metry
constexpr double MIN_MOVE_DISTANCE = 3;
// Shift+klik dodaje wezel, gdy klikniecie jest najwyzej tyle pikseli od krawedzi obiektu.
constexpr double NODE_INSERT_DISTANCE = 8;
// Przyciaganie (Ctrl): wezel innego obiektu najwyzej tyle pikseli od kursora (closest_node_min_distance).
constexpr double SNAP_DISTANCE = 15;
constexpr double SMALL_POLY_PERIMETER = 500;
constexpr int WEBLAYER_DOWNLOAD_TIMEOUT = 15;
constexpr int MAP_LEVELS = 5;
constexpr int MAX_RECENT_FILES = 10;
// POI "Flyover" / WIADUKT - stawiany przez Tools -> Dodaj bojki wiadukt.
constexpr long long VIADUCT_POI_TYPE = 0x1709;
// POI "Dead end" / SLEPY - stawiany przez Tools -> Dodaj bojki ślepy.
constexpr long long DEAD_END_POI_TYPE = 0x1708;

// View -> Levels -> Automatycznie: poziom mapy dla skali 1:denominator.
// Wiecej niz 1:10 000 (np. 1:5 000) - 0; 1:10 000-1:50 000 - 1; 1:50 000-1:200 000 - 2;
// 1:200 000-1:1 000 000 - 3; mniej niz 1:1 000 000 - 4.
constexpr int map_level_for_scale(double denominator) {
    if (denominator < 10000) return 0;
    if (denominator < 50000) return 1;
    if (denominator < 200000) return 2;
    if (denominator < 1000000) return 3;
    return 4;
}

enum class Tool {
    None,
    ZoomMap,
    SelectObjects,
    RotateObjects,
    EditNodes,
    CreatePoint,
    CreatePolyline,
    CreatePolylineCircle,
    CreatePolygon,
    CreatePolygonStripe,
    CreatePolygonRectangle,
    CreatePolygonDisc,
};

}  // namespace pwm::gui
