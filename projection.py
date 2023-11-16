#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import math
import utm

class Projection(object):
    """general base class for all projections"""
    def __init__(self, mapBoundingBox):
        self.mapBoundingBox = mapBoundingBox
        self.earth_radius = 6378137.0
        self.projectionName = ''

    def calculate_data_offset(self):
        self.earth_radius = 6378137.0
        return 0

    def geo_to_canvas(self, latitude, longitude):
        return 0, 0

    def canvas_to_geo(self, latitude, longitude):
        return 0, 0

    def set_map_bounding_box(self, bbox):
        for key in bbox:
            self.mapBoundingBox[key] = bbox[key]

class Direct(Projection):
    """Simple, stupid projection, that uses geo coords for the plane. Used mainly for testing"""
    def __init__(self, mapBoundingBox):
        super(Direct, self).__init__(mapBoundingBox)
        self.mapBoundingBox = mapBoundingBox
        self.projectionName = 'Direct'

    def geo_to_canvas(self, latitude, longitude):
        return [self.earth_radius * float(longitude), -self.earth_radius * float(latitude)]

    def canvas_to_geo(self, latitude, longitude):
        pass

class Mercator(Projection):

    def __init__(self, mapBoundingBox):
        super(Mercator, self).__init__(mapBoundingBox)
        self.projectionName = 'Mercator'

    def geo_to_canvas(self, latitude, longitude):
        x = float(longitude)
        y = 180.0 / math.pi * math.log(math.tan(math.pi / 4.0 + float(latitude) * (math.pi / 180.0) / 2.0))
        # as screen 0,0 point is topleft corner of a screen and y increases down direction, we use -y
        return self.earth_radius * x, -y * self.earth_radius

    def canvas_to_geo(self, x, y):
        longitude = x / self.earth_radius
        # we need to take -y as in screen coordinates y increases in down direction
        latitude = 180.0 / math.pi * (2.0 * math.atan(math.exp((-y / self.earth_radius) * (math.pi / 180.0))) - math.pi / 2.0)
        return latitude, longitude

class UTM(Projection):

    def __init__(self, mBBox):
        super(UTM, self).__init__(mBBox)
        self.UTMEasting = float
        self.UTMNorthing = float
        self.UTMZone = int
        self.UTMNorthern = 1
        self.projectionName = 'UTM'

        # if map covers 2 zones but it less than 6 degrees wide, offset will help to calculate
        # proper projections. Value 0 means offset is not necessary, value -1 means map is wider
        # than 6 degrees
        self.map_data_offset = self.calculate_data_offset()


    def calculate_data_offset(self):

        if not self.mapBoundingBox:
            print('brak bounding box', self.mapBoundingBox)
            return -1

        """UTM projection can cover maximally 6 degrees longitude. If the area is higher then that
            it is not possible to show proper projection. If the map is less than 6 degrees wide,
            but crosses 2 zones, we will calculate offset to move data into one zone"""

        if self.mapBoundingBox['E'] - self.mapBoundingBox['W'] > 6:
            print('bounding box więcej niz 6')
            return -1
        else:
            if self.mapBoundingBox['E']//6 == self.mapBoundingBox['W']//6:
                print('szerokosc mapy w jednej strefie')
                return 0
            else:
                print('liczymy przesuniecie')
                return int(self.mapBoundingBox['W'] % 6)

    def geo_to_canvas(self, latitude, longitude):
        self.UTMEasting, self.UTMNorthing, self.UTMZone, a = \
                utm.from_latlon(float(latitude), float(longitude) - self.map_data_offset)
        if a in ('B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M'):
            self.UTMNorthern = -1
        else:
            self.UTMNorthern = 1

        # we have to recalculate UTM coordinates to canvas coords.
        # to convert coordinates to canvas coords you have to multiply
        # the UTMZone by UTM_MULTIPLICITY and add UTMEasting
        x = self.UTMEasting
        #print(x)
        # to calculate y you have to multiply the Northing by UTMNorther
        # all latitudes north will be positive, all latitudes south will be negative
        y = self.UTMNorthern * self.UTMNorthing

        return [x, -y]
        # return[self.longitude, -self.latitude]

    def canvas_to_geo(self, latitude, longitude):
        pass