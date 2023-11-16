#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from collections import OrderedDict
import pwmapedit_constants
import math

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
    inside_record = False
    for line_num, line_content in enumerate(map_strings_record):
        line_content = line_content.strip()
        if not line_content:
            continue
        if line_content.startswith(';') and not inside_record:
            comment_list.append(line_content[1:])
        elif line_content in pwmapedit_constants.MAP_ALL_OBJECTS:
            poi_poly = line_content
            inside_record = True
        elif '=' in line_content:
            key, val = line_content.split('=', 1)
            record_dict[(line_num, key)] = val
        else:
            print('Unknown line, without =: %s' % line_content)
    return poi_poly, comment_list, record_dict


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
        return 360 - angle


