import math
import os.path
class WebLayers(object):
    def __init__(self):
        self.zoom_level = 0
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

    @staticmethod
    def deg2num(lat_deg, lon_deg, zoom):
        lat_rad = math.radians(lat_deg)
        n = 1 << zoom
        xtile = int((lon_deg + 180.0) / 360.0 * n)
        ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
        return xtile, ytile

    @staticmethod
    def num2deg(xtile, ytile, zoom):
        n = 1 << zoom
        lon_deg = xtile / n * 360.0 - 180.0
        lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
        lat_deg = math.degrees(lat_rad)
        return lat_deg, lon_deg

    def get_tile_path(self, xtile, ytile):
        tp = os.path.join(str(self.zoom_level), str(xtile))
        tp = os.path.join(tp, str(ytile) + '.png')
        return os.path.join(self.cache_folder, tp)