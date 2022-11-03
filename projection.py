#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import math
import utm

class Projection(object):
    """general base class for all projections"""
    def __init__(self, mapBoundingBox):
        self.mapBoundingBox = mapBoundingBox
        self.mapDataOfset = 10000
        self.projectionName = ''

    def calculate_data_ofset(self):
        self.mapDataOfset = 100000
        return 0

    def geo_to_canvas(self, latitude, longitude):
        return 0, 0

    def canvas_to_geo(self, latitude, longitude):
        return 0, 0

class Direct(Projection):
    """Simple, stupid projection, that uses geo coords for the plane. Used mainly for testing"""
    def __init__(self, mapBoundingBox):
        super(Direct, self).__init__(mapBoundingBox)
        self.mapBoundingBox = mapBoundingBox
        self.projectionName = 'Direct'

    def geo_to_canvas(self, latitude, longitude):
        return [self.mapDataOfset * float(longitude), -self.mapDataOfset * float(latitude)]

    def canvas_to_geo(self, latitude, longitude):
        pass

class Mercator(Projection):

    def __init__(self, mapBoundingBox):
        super(Mercator, self).__init__(mapBoundingBox)
        self.projectionName = 'Mercator'

    def geo_to_canvas(self, latitude, longitude):
        x = float(longitude)
        y = 180.0 / math.pi * math.log(math.tan(math.pi / 4.0 + float(latitude) * (math.pi / 180.0) / 2.0))
        return [self.mapDataOfset * x, -y * self.mapDataOfset]

    def canvas_to_geo(self, x, y):
        longitude = x / self.mapDataOfset
        latitude = 180.0 / math.pi * (2.0 * math.atan(math.exp((-y / self.mapDataOfset) * (math.pi / 180.0))) - math.pi/2.0)
        return [latitude, longitude]

class UTM(Projection):

    def __init__(self, mBBox):
        super(UTM, self).__init__(mBBox)
        self.UTMEasting = float
        self.UTMNorthing = float
        self.UTMZone = int
        self.UTMNorthern = 1
        self.projectionName = 'UTM'

        # if map covers 2 zones but it less then 6 degrees wide, ofset will help to calculate
        # proper projections. Value 0 means ofset is not necesary, value -1 means map is wider
        # then 6 degrees
        self.calculate_data_ofset()


    def calculate_data_ofset(self):

        if not self.mapBoundingBox:
            print('brak bounding box', self.mapBoundingBox)
            self.mapDataOfset = -1
            return -1

        """UTM projection can cover maximally 6 degrees longitude. If the area is higher then that
            it is not possible to show proper projection. If the map is less than 6 degrees wide,
            but croses 2 zones, we will calculate ofset to move data into one zone"""

        if self.mapBoundingBox['E'] - self.mapBoundingBox['W'] > 6:
            print('bounding box więcej niz 6')
            self.mapDataOfset = -1
            return -1
        else:
            if self.mapBoundingBox['E']//6 == self.mapBoundingBox['W']//6:
                print('szerokosc mapy w jednej strefie')
                self.mapDataOfset = 0
            else:
                print('liczymy przesuniecie')
                a = self.mapBoundingBox['W'] % 6
                self.mapDataOfset = int(a)
        return 0

    def geo_to_canvas(self, latitude, longitude):
        self.UTMEasting, self.UTMNorthing, self.UTMZone, a = \
                utm.from_latlon(float(latitude), float(longitude)-self.mapDataOfset)
        if a in('B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M'):
            self.UTMNorthern = -1
        else:
            self.UTMNorthern = 1

        # we have to recalculate UTM coordinates to canvas coords.
        # to convert coordinates to canvas coords you have to multiply
        # the UTMZone by UTM_MULTIPLICITY and add UTMEasting
        x = self.UTMEasting
        #print(x)
        # to calculate y you have to multiply the Northing by UTMNorther
        # all latitudes north will be positive, all latituded south will be negative
        y = self.UTMNorthern * self.UTMNorthing

        return [x, -y]
        # return[self.longitude, -self.latitude]

    def canvas_to_geo(self, latitude, longitude):
        pass