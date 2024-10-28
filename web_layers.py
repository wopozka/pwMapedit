import math
import os.path


class MapLayersEnum(object):
    osm = 0
    geoportal_orto = 1
    google_orto = 2


class WebLayers(object):
    # https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames
    def __init__(self, web_layer):
        self.zoom = 0
        self.zoom_level_vs_scale = (
            500000000,  # 0
            250000000,  # 1
            150000000,  # 2
            70000000,   # 3
            35000000,   # 4
            15000000,   # 5
            10000000,   # 6
            4000000,    # 7
            2000000,    # 8
            1000000,    # 9
            500000,     # 10
            250000,     # 11
            150000,     # 12
            70000,      # 13
            35000,      # 14
            15000,      # 15
            8000,       # 16
            4000,       # 17
            2000,       # 18
            1000,       # 19
            500,        # 20
        )
        self.cache_folder = 'wl_cache'
        self.current_web_layer = web_layer
        self.web_layer_cache_path = os.path.join(self.cache_folder, str(web_layer))

    def deg2num(self, lat_deg, lon_deg):
        lat_rad = math.radians(lat_deg)
        n = 1 << self.zoom
        xtile = int((lon_deg + 180.0) / 360.0 * n)
        ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
        return xtile, ytile

    def deg2num_from_scale(self, lat_deg, lon_deg, scale):
        self.zoom = self.get_zoom_from_scale(scale)
        return self.deg2num(lat_deg, lon_deg)

    def get_tile_path(self, xtile, ytile):
        tp = os.path.join(str(self.zoom), str(xtile))
        tp = os.path.join(tp, str(ytile) + '.png')
        return os.path.join(self.web_layer_cache_path, tp)

    def get_tiles_paths(self, left_top_lat, left_top_lon, bottom_righ_lat, bottom_right_lon):
        tiles_path = list()
        left_top_xtile, left_top_ytile = self.deg2num(left_top_lat, left_top_lon)
        left_bottom_xtile, left_bottom_ytile = self.deg2num(bottom_righ_lat, bottom_right_lon)
        for xtile in range(left_top_xtile, left_bottom_xtile + 1):
            for ytile in range(left_top_ytile, left_bottom_ytile + 1):
                tiles_path.append((self.get_tile_path(xtile, ytile), self.num2deg(xtile, ytile),))
        return tiles_path

    def get_zoom_from_scale(self, scale):
        if scale >= self.zoom_level_vs_scale[0]:
            return 0
        for zoom_val in range(len(self.zoom_level_vs_scale) - 1):
            cur_zoom = zoom_val
            next_zoom = zoom_val + 1
            if self.zoom_level_vs_scale[next_zoom] <= scale < self.zoom_level_vs_scale[cur_zoom]:
                return next_zoom
        return len(self.zoom_level_vs_scale) - 1

    def num2deg(self, xtile, ytile):
        n = 1 << self.zoom
        lon_deg = xtile / n * 360.0 - 180.0
        lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
        lat_deg = math.degrees(lat_rad)
        return lat_deg, lon_deg

    def num2deg_from_scale(self, xtile, ytile, scale):
        self.zoom = self.get_zoom_from_scale(scale)
        return self.num2deg(xtile, ytile)

    def set_current_web_layer(self, weblayer_name):
        self.current_web_layer = weblayer_name
        self.web_layer_cache_path = os.path.join(self.cache_folder, weblayer_name)

    def set_zoom_from_scale(self, scale):
        self.zoom = self.get_zoom_from_scale(scale)
