// Kafelki warstw WWW: wartosci oczekiwane policzone oryginalnym web_layers.py.
#include <cmath>
#include <string>

#include "../core/web_tiles.hpp"
#include "test_framework.hpp"

using namespace pwm::web;

TEST(web_zoom_from_scale) {
    for (Layer layer : {Layer::Osm, Layer::GeoportalOrto, Layer::GoogleOrto}) {
        CHECK_EQ(zoom_from_scale(layer, 600000000), 0);
        CHECK_EQ(zoom_from_scale(layer, 300000000), 1);
        CHECK_EQ(zoom_from_scale(layer, 1000), 19);
        CHECK_EQ(zoom_from_scale(layer, 12345), 16);
    }
    CHECK_EQ(zoom_from_scale(Layer::Osm, 600), 19);  // OSM ma najwyzej zoom 19
    CHECK_EQ(zoom_from_scale(Layer::Osm, 400), 19);
    CHECK_EQ(zoom_from_scale(Layer::GeoportalOrto, 600), 20);
    CHECK_EQ(zoom_from_scale(Layer::GoogleOrto, 400), 20);
}

TEST(web_deg2num_num2deg) {
    auto [x, y] = deg2num(52.1, 21.0, 16);
    CHECK_EQ(x, 36590);
    CHECK_EQ(y, 21617);
    auto [lat, lon] = num2deg(36590, 21600, 16);
    CHECK_NEAR(lat, 52.160454557747, 1e-11);
    CHECK_NEAR(lon, 20.994873046875, 1e-12);
}

TEST(web_tiles_for_area) {
    auto tiles = tiles_for_area(52.11, 20.99, 52.10, 21.01, 16);
    CHECK_EQ(tiles.size(), size_t{16});
    CHECK_EQ(tiles.front().x, 36589);
    CHECK_EQ(tiles.front().y, 21614);
    CHECK_NEAR(tiles.front().left_top_lat, 52.11325243469631, 1e-12);
    CHECK_NEAR(tiles.front().left_top_lon, 20.9893798828125, 1e-12);
    CHECK_NEAR(tiles.front().right_bott_lat, 52.10987894035489, 1e-12);
    CHECK_NEAR(tiles.front().right_bott_lon, 20.994873046875, 1e-12);
    CHECK_EQ(tiles.back().x, 36592);
    CHECK_EQ(tiles.back().y, 21617);
}

TEST(web_tile_urls) {
    CHECK_EQ(tile_url(Layer::Osm, 16, 36590, 21600), std::string("https://tile.openstreetmap.org/16/36590/21600.png"));
    CHECK_EQ(tile_url(Layer::GeoportalOrto, 16, 36590, 21600),
             std::string("http://mapy.geoportal.gov.pl/wss/service/PZGIK/ORTO/WMS/StandardResolution?REQUEST=GetMap"
                         "&TRANSPARENT=TRUE&FORMAT=image/jpeg&VERSION=1.3.0&LAYERS=Raster&STYLES=&EXCEPTIONS=xml"
                         "&WIDTH=256&HEIGHT=256&BBOX=52.15708,20.99487,52.16045,21.00037&CRS=EPSG:4326&SERVICE=WMS"));
    CHECK_EQ(tile_url(Layer::GoogleOrto, 16, 36590, 21600),
             std::string("http://khm0.google.pl/kh/v=1015&x=36590&s=&y=21600&z=16&s=Ga"));
    CHECK_EQ(tile_url(Layer::GoogleOrto, 18, 146363, 86403),
             std::string("http://khm1.google.pl/kh/v=1015&x=146363&s=&y=86403&z=18&s=Gali"));
    CHECK_EQ(tile_url(Layer::GoogleOrto, 18, 5, 7), std::string("http://khm1.google.pl/kh/v=1015&x=5&y=7&z=18&s=Galile"));
    CHECK_EQ(tile_path(Layer::Osm, 16, 36590, 21600), std::string("OSM/16/36590/21600.png"));
}
