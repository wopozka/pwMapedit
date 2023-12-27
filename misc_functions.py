#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from collections import OrderedDict
import pwmapedit_constants
import math
from PyQt5.QtGui import QPainterPath, QPolygonF
from PyQt5.QtCore import QPointF, QLineF

def read_icons_from_skin_file(skin_filename):
    """
    Reading skin file and create icons definitions
    Parameters
    ----------
    skin_filename: name of a file

    Returns: dict of poi type: icons def as xpm string. If file can't be read, empty dict is returned.
    -------
    """
    poi_type_icon = dict()
    icon_def = list()
    in_poi = False
    try:
        with open(skin_filename, 'r', encoding='cp1250') as skinfile:
            for linia in skinfile.readlines():
                if in_poi:
                    if '[end]' in linia:
                        in_poi = False
                        _type, _icon = return_icon_definition(icon_def)
                        poi_type_icon[_type] = _icon
                        icon_def.clear()
                    else:
                        icon_def.append(linia.strip())
                    continue
                elif '[_point]' in linia:
                    in_poi = True
                    continue
        return poi_type_icon
    except (FileNotFoundError, PermissionError) as l_expection:
        print(l_expection)
        return dict()


def return_icon_definition(icon_def):
    """
    converting skin record to icon type and icon string
    Parameters
    ----------
    icon_def: a list of skin records

    Returns: tuple of icon type: icon def as xpm
    -------
    """
    l_type = ''
    l_subtype = ''
    l_icon = '/* XPM */\n static const unsigned char * day_xpm[] = {\n'
    in_xpm_def = False
    for l_line in icon_def:
        if in_xpm_def:
            l_icon += l_line
            l_icon += '\n'
            continue
        elif l_line.startswith('Type='):
            l_type = l_line.split('=', 1)[-1].strip()
            continue
        elif l_line.startswith('SubType='):
            l_subtype = l_line.split('=', 1)[-1].strip()
            continue
        elif 'xpm=' in l_line:
            l_icon += l_line.split('xpm=', 1)[-1]
            l_icon += '\n'
            in_xpm_def = True
            continue
    return l_type + l_subtype.split('x')[-1].strip(), l_icon


def map_strings_record_to_dict_record(map_strings_record):
    """
    converst map object record to dictionary record form. As some of keys can appear more than once, the dictionary
    key is tuple: (line_num, key)
    Parameters
    ----------
    map_strings_record: list of strings in a form ['POI_POLY=POI', 'Type=0x000'...]

    Returns OrderedDict {line_num: commment1, line_num: comment2...,}, OrderedDict {(0, POI_POLY): POI: (1, Type): 0x000...}
    -------
    """
    record_dict = OrderedDict()
    comment_list = list()
    poi_poly_type = list()
    inside_record = False
    for line_num, line_content in enumerate(map_strings_record):
        line_content = line_content.strip()
        if not line_content:
            continue
        if line_content.startswith(';') and not inside_record:
            comment_list.append(line_content[1:])
        elif line_content in pwmapedit_constants.MAP_ALL_OBJECTS:
            poi_poly_type.append(line_content)
            inside_record = True
        elif '=' in line_content:
            key, val = line_content.split('=', 1)
            record_dict[(line_num, key)] = val
            if key == 'Type':
                poi_poly_type.append(int(val, 16))
        else:
            print('Unknown line, without =: %s' % line_content)
    return tuple(poi_poly_type), comment_list, record_dict


def vector_angle(x, y, clockwise=False, screen_coord_system=False):
    if screen_coord_system:
        y = -y
    if x == 0:
        if clockwise:
            return 90 if y < 0 else 270
        return 90 if y > 0 else 270
    y_by_x = round(y / x, 5)
    if y_by_x == 0:
        return 0 if x > 0 else 180
    calc_degrees = math.degrees(math.atan(y_by_x))
    if x > 0:
        if clockwise:
            return -calc_degrees if y < 0 else 360 - calc_degrees
        else:
            return calc_degrees if y > 0 else 360 + calc_degrees
    return 180 - calc_degrees if clockwise else 180 + calc_degrees


def calculate_label_angle(angle):
    if 0 <= angle <= 90:
        return angle
    elif 90 < angle < 180:
        return 180 + angle
    elif angle == 180:
        return 0
    elif 180 < angle <= 270:
        return angle - 180
    else:
        return angle


def great_circle_distance(coord1, coord2):
    lat1 = math.radians(coord1[0])
    lon1 = math.radians(coord1[1])
    lat2 = math.radians(coord2[0])
    lon2 = math.radians(coord1[1])
    return 6371 * math.acos(math.sin(lat1) * math.sin(lat2) + math.cos(lat1) *
                            math.cos(lat2) * math.cos(lon1 - lon2))


def vincenty_distance(coord1, coord2):
    """
    calculates distance betwen two earth points
    Parameters
    ----------
    coord1: tuple(latitude, longitude)
    coord2 tuple(latitude, longitude)

    Returns: distance in meters
    -------

    """
    # https://nathanrooy.github.io/posts/2016-12-18/vincenty-formula-with-python/
    a = 6378137.0  # radius at equator in meters (WGS-84)
    f = 1 / 298.257223563  # flattening of the ellipsoid (WGS-84)
    b = (1 - f) * a
    maxIter = 200
    tol = 10**-12

    # lat=phi_?   latitude (N, S) of the points
    # lon=L_?  longitude (E, W) of points
    phi_1, L_1 = coord1
    phi_2, L_2 = coord2

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


# def closest_point_to_poly(event_pos, polygons, threshold, type_polygon=True):
#     """
#     Get the position along the polyline/polygon sides that is the closest
#         to the given point.
#     Parameters
#     ----------
#     event_pos: event class position (event.pos)
#     polygons: [[poly_coords1], [poly_coords2], [poly_coords3]]
#     threshold: distance of mouse from line
#     type_polygon: whether we have polygon (True) or polyline (False)
#
#     Returns
#     -------
#     tuple(distance from edge, qpointf within polygon edge, insertion index) in case of succes and
#     tuple(-1, qpoinf, -1) in case of failure
#     """
#
#     intersections_for_separate_paths = list()
#     for path_num, points in enumerate(polygons):
#         # iterate through pair of points, if the polygon is not "closed",
#         # add the start to the end
#         p1 = points.pop(0)
#         if type_polygon and points[-1] != p1:  # identical to QPolygonF.isClosed()
#             points.append(p1)
#         intersections = []
#         for coord_index, p2 in enumerate(points, 1):
#             line = QLineF(p1, p2)
#             inters = QPointF()
#             # create a perpendicular line that starts at the given pos
#             perp = QLineF.fromPolar(threshold, line.angle() + 90).translated(event_pos)
#             if line.intersect(perp, inters) != QLineF.BoundedIntersection:
#                 # no intersection, reverse the perpendicular line by 180°
#                 perp.setAngle(perp.angle() + 180)
#                 if line.intersect(perp, inters) != QLineF.BoundedIntersection:
#                     # the pos is not within the line extent, ignore it
#                     p1 = p2
#                     continue
#             # get the distance between the given pos and the found intersection
#             # point, then add it, the intersection and the insertion index to
#             # the intersection list
#             intersections.append((QLineF(event_pos, inters).length(), inters, (path_num, coord_index,)))
#             p1 = p2
#         if intersections:
#             intersections_for_separate_paths.append(min(intersections, key=lambda item: item[0]))
#
#     if intersections_for_separate_paths:
#         # return the result with the shortest distance
#         return min(intersections_for_separate_paths, key=lambda item: item[0])
#     return -1, QPointF(), (0, -1)
