// Port web_layers.py (bez Qt): kafelki warstw WWW w ukladzie "slippy map"
// (https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames), zoom ze skali mapy i adresy kafelkow.
#pragma once

#include <string>
#include <utility>
#include <vector>

namespace pwm::web {

enum class Layer { Osm = 0, GeoportalOrto = 1, GoogleOrto = 2 };

struct Tile {
    int x = 0;
    int y = 0;
    double left_top_lat = 0, left_top_lon = 0;
    double right_bott_lat = 0, right_bott_lon = 0;
};

const char* layer_name(Layer layer);  // "OSM", "Geoportal", "Google"
const char* extension(Layer layer);   // ".png" / ".jpg"
int max_zoom(Layer layer);

// create_zoom_from_scale: zoom kafelkow dla mianownika skali mapy (1:scale).
int zoom_from_scale(Layer layer, double scale);
// deg2num / num2deg
std::pair<int, int> deg2num(double lat_deg, double lon_deg, int zoom);
std::pair<double, double> num2deg(int xtile, int ytile, int zoom);
// get_tiles_paths: kafelki pokrywajace prostokat (lewy gorny i prawy dolny rog), kolumnami.
std::vector<Tile> tiles_for_area(double left_top_lat, double left_top_lon, double right_bottom_lat,
                                 double right_bottom_lon, int zoom);
// get_tile_url
std::string tile_url(Layer layer, int zoom, int xtile, int ytile);
// Sciezka pliku w katalogu pamieci podrecznej: <warstwa>/<zoom>/<x>/<y><rozszerzenie>.
std::string tile_path(Layer layer, int zoom, int xtile, int ytile);

}  // namespace pwm::web
