# -*- coding: utf-8 -*-
"""Elementy formatu pliku MP (polish format)."""
from collections import OrderedDict

MAP_OBJECT_POI = '[POI]'
MAP_OBJECT_POLYLINE = '[POLYLINE]'
MAP_OBJECT_POLYGON = '[POLYGON]'
MAP_OBJECT_RESTRICT = '[RESTRICT]'
MAP_OBJECT_ROADSIGN = '[SIGN]'
MAP_OBJECT_TYPES = ('[POI]', '[POLYGON]', '[POLYLINE]')
MAP_ALL_OBJECTS = ('[POI]', '[POLYGON]', '[POLYLINE]', '[RESTRICT]', '[SIGN]')
MAP_OBJECT_END = '[END]'


def map_strings_record_to_dict_record(map_strings_record):
    """
    converst map object record to dictionary record form. As some keys can appear more than once, the dictionary
    key is tuple: (line_num, key)
    Parameters
    ----------
    map_strings_record: list of strings in a form ['[POI]', 'Type=0x000'...]

    Returns tuple('[POI]/[POLYLINE]/[POLYGON]'), list({commment1, comment2...,],
            OrderedDict {(0, Type): 0x000. (1, Label): xxx, ...}
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
        elif line_content in MAP_ALL_OBJECTS:
            poi_poly_type.append(line_content)
            inside_record = True
        elif '=' in line_content:
            key, val = line_content.split('=', 1)
            record_dict[(line_num, key)] = val
            if key == 'Type':
                poi_poly_type.append(int(val, 16))
        elif line_content == '[END]':
            break
        else:
            print('Unknown line, without =: %s' % line_content)
    return tuple(poi_poly_type), comment_list, record_dict
