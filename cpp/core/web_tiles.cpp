#include "web_tiles.hpp"

#include <cmath>
#include <cstdio>

namespace pwm::web {

namespace {

// zoom_level_vs_scale z web_layers.py: mianownik skali dla kolejnych poziomow zoomu
constexpr double ZOOM_LEVEL_VS_SCALE[] = {500000000, 250000000, 150000000, 70000000, 35000000, 15000000, 10000000,
                                          4000000,   2000000,   1000000,   500000,   250000,   150000,   70000,
                                          35000,     15000,     8000,      4000,     2000,     1000,     500};

constexpr double PI = 3.14159265358979323846;

}  // namespace

const char* layer_name(Layer layer) {
    switch (layer) {
        case Layer::Osm: return "OSM";
        case Layer::GeoportalOrto: return "Geoportal";
        case Layer::GoogleOrto: return "Google";
    }
    return "";
}

const char* extension(Layer layer) { return layer == Layer::Osm ? ".png" : ".jpg"; }

int max_zoom(Layer layer) { return layer == Layer::Osm ? 19 : 20; }

int zoom_from_scale(Layer layer, double scale) {
    if (scale >= ZOOM_LEVEL_VS_SCALE[0]) return 0;
    for (int zoom = 0; zoom < max_zoom(layer) - 1; ++zoom) {
        if (ZOOM_LEVEL_VS_SCALE[zoom + 1] <= scale && scale < ZOOM_LEVEL_VS_SCALE[zoom]) return zoom + 1;
    }
    return max_zoom(layer);
}

std::pair<int, int> deg2num(double lat_deg, double lon_deg, int zoom) {
    const double lat_rad = lat_deg * PI / 180.0;
    const double n = static_cast<double>(1LL << zoom);
    const int xtile = static_cast<int>((lon_deg + 180.0) / 360.0 * n);
    const int ytile = static_cast<int>((1.0 - std::asinh(std::tan(lat_rad)) / PI) / 2.0 * n);
    return {xtile, ytile};
}

std::pair<double, double> num2deg(int xtile, int ytile, int zoom) {
    const double n = static_cast<double>(1LL << zoom);
    const double lon_deg = xtile / n * 360.0 - 180.0;
    const double lat_rad = std::atan(std::sinh(PI * (1 - 2 * ytile / n)));
    return {lat_rad * 180.0 / PI, lon_deg};
}

std::vector<Tile> tiles_for_area(double left_top_lat, double left_top_lon, double right_bottom_lat,
                                 double right_bottom_lon, int zoom) {
    std::vector<Tile> tiles;
    const auto [x1, y1] = deg2num(left_top_lat, left_top_lon, zoom);
    const auto [x2, y2] = deg2num(right_bottom_lat, right_bottom_lon, zoom);
    for (int x = x1; x <= x2; ++x) {
        for (int y = y1; y <= y2; ++y) {
            Tile t;
            t.x = x;
            t.y = y;
            std::tie(t.left_top_lat, t.left_top_lon) = num2deg(x, y, zoom);
            std::tie(t.right_bott_lat, t.right_bott_lon) = num2deg(x + 1, y + 1, zoom);
            tiles.push_back(t);
        }
    }
    return tiles;
}

std::string tile_url(Layer layer, int zoom, int xtile, int ytile) {
    char buf[512];
    switch (layer) {
        case Layer::Osm:
            std::snprintf(buf, sizeof buf, "https://tile.openstreetmap.org/%d/%d/%d.png", zoom, xtile, ytile);
            return buf;
        case Layer::GoogleOrto: {
            // jak w Pythonie: string.sub('Galileo', 1, (3 * x + y) % 8)
            // long long: (x + 2) * y przekracza zakres int dla duzych zoomow (Python liczy na dowolnie duzych liczbach)
            const long long x = xtile, y = ytile;
            const std::string salt1 = std::string("Galileo").substr(0, static_cast<size_t>((3 * x + y) % 8));
            const char* salt2 = (10000 <= ytile && ytile < 100000) ? "&s=" : "";
            const int server = static_cast<int>(((x + 2) * y) % 2);
            std::snprintf(buf, sizeof buf, "http://khm%d.google.pl/kh/v=%d&x=%d%s&y=%d&z=%d&s=%s", server, 1015, xtile,
                          salt2, ytile, zoom, salt1.c_str());
            return buf;
        }
        case Layer::GeoportalOrto: {
            const auto [lt_lat, lt_lon] = num2deg(xtile, ytile, zoom);
            const auto [rb_lat, rb_lon] = num2deg(xtile + 1, ytile + 1, zoom);
            std::snprintf(buf, sizeof buf,
                          "http://mapy.geoportal.gov.pl/wss/service/PZGIK/ORTO/WMS/StandardResolution"
                          "?REQUEST=GetMap&TRANSPARENT=TRUE&FORMAT=image/jpeg&VERSION=1.3.0&LAYERS="
                          "Raster&STYLES=&EXCEPTIONS=xml&WIDTH=256&HEIGHT=256&"
                          "BBOX=%.5f,%.5f,%.5f,%.5f&CRS=EPSG:4326&SERVICE=WMS",
                          rb_lat, lt_lon, lt_lat, rb_lon);
            return buf;
        }
    }
    return {};
}

std::string tile_path(Layer layer, int zoom, int xtile, int ytile) {
    return std::string(layer_name(layer)) + "/" + std::to_string(zoom) + "/" + std::to_string(xtile) + "/" +
           std::to_string(ytile) + extension(layer);
}

}  // namespace pwm::web
