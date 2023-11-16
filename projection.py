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
        return self.earth_radius * float(longitude), -self.earth_radius * float(latitude)

    def canvas_to_geo(self, latitude, longitude):
        pass

class Mercator(Projection):
    great_circle_length = 6371
    def __init__(self, mapBoundingBox):
        super(Mercator, self).__init__(mapBoundingBox)
        self.projectionName = 'Mercator'

    def geo_to_canvas(self, latitude, longitude):
        x = math.radians(float(longitude)) * self.earth_radius
        y = math.log(math.tan(math.pi / 4.0 + math.radians(float(latitude)) / 2.0)) * self.earth_radius
        # as screen 0,0 point is topleft corner of a screen and y increases down direction, we use -y
        return x, -y

    def canvas_to_geo(self, x, y):
        longitude = math.degrees(x / self.earth_radius)
        # we need to take -y as in screen coordinates y increases in down direction
        y = -y
        latitude = math.degrees(2.0 * math.atan(math.exp(y / self.earth_radius)) - math.pi / 2.0)
        return latitude, longitude

    def distance(self, coord1, coord2):
        lat1 = math.radians(coord1[0])
        lon1 = math.radians(coord1[1])
        lat2 = math.radians(coord2[0])
        lon2 = math.radians(coord1[1])
        return 6371 * math.acos(math.sin(lat1) * math.sin(lat2) + math.cos(lat1) *
                                math.cos(lat2) * math.cos(lon1 - lon2))

    def distance_vincenty(self, coord1, coord2):
        a = 6378137.0  # radius at equator in meters (WGS-84)
        f = 1 / 298.257223563  # flattening of the ellipsoid (WGS-84)
        b = (1 - f) * a
        maxIter = 200
        tol = 10**-12

        # (lat=L_?,lon=phi_?)
        L_1, phi_1 = coord1
        L_2, phi_2 = coord2

        u_1 = math.atan((1 - f) * math.tan(math.radians(phi_1)))
        u_2 = math.atan((1 - f) * math.tan(math.radians(phi_2)))

        L = math.radians(L_2 - L_1)

        Lambda = L  # set initial value of lambda to L

        sin_u1 = math.sin(u_1)
        cos_u1 = math.cos(u_1)
        sin_u2 = math.sin(u_2)
        cos_u2 = math.cos(u_2)

        # --- BEGIN ITERATIONS -----------------------------+
        iters = 0
        for i in range(0, maxIter):
            iters += 1

            cos_lambda = math.cos(Lambda)
            sin_lambda = math.sin(Lambda)
            sin_sigma = math.sqrt((cos_u2 * math.sin(Lambda)) ** 2 +
                                  (cos_u1 * sin_u2 - sin_u1 * cos_u2 * cos_lambda) ** 2)
            cos_sigma = sin_u1 * sin_u2 + cos_u1 * cos_u2 * cos_lambda
            sigma = math.atan2(sin_sigma, cos_sigma)
            sin_alpha = (cos_u1 * cos_u2 * sin_lambda) / sin_sigma
            cos_sq_alpha = 1 - sin_alpha ** 2
            cos2_sigma_m = cos_sigma - ((2 * sin_u1 * sin_u2) / cos_sq_alpha)
            C = (f / 16) * cos_sq_alpha * (4 + f * (4 - 3 * cos_sq_alpha))
            Lambda_prev = Lambda
            Lambda = L + (1 - C) * f * sin_alpha * (sigma + C * sin_sigma *
                                                    (cos2_sigma_m + C * cos_sigma * (-1 + 2 * cos2_sigma_m ** 2)))

            # successful convergence
            diff = abs(Lambda_prev - Lambda)
            if diff <= tol:
                break

        u_sq = cos_sq_alpha * ((a ** 2 - b ** 2) / b ** 2)
        A = 1 + (u_sq / 16384) * (4096 + u_sq * (-768 + u_sq * (320 - 175 * u_sq)))
        B = (u_sq / 1024) * (256 + u_sq * (-128 + u_sq * (74 - 47 * u_sq)))
        delta_sig = B * sin_sigma * (cos2_sigma_m + 0.25 * B * (
                    cos_sigma * (-1 + 2 * cos2_sigma_m ** 2) - (1 / 6) * B * cos2_sigma_m * (
                        -3 + 4 * sin_sigma ** 2) * (-3 + 4 * cos2_sigma_m ** 2)))

        m = b * A * (sigma - delta_sig)  # output distance in meters
        # self.km=self.meters/1000                    # output distance in kilometers
        # self.mm=self.meters*1000                    # output distance in millimeters
        # self.miles=self.meters*0.000621371          # output distance in miles
        # self.n_miles=self.miles*(6080.20/5280)      # output distance in nautical miles
        # self.ft=self.miles*5280                     # output distance in feet
        # self.inches=self.feet*12                    # output distance in inches
        # self.yards=self.feet/3                      # output distance in yards
        return m


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

        return x, -y
        # return[self.longitude, -self.latitude]

    def canvas_to_geo(self, latitude, longitude):
        pass