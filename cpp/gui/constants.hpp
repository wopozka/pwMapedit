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
