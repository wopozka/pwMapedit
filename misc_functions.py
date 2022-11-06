#!/usr/bin/env python3
# -*- coding: utf-8 -*-

def read_icons_from_skin_file(skin_filename):
    poi_type_icon = dict()
    icon_def = list()
    in_poi = False
    with open(skin_filename, 'r') as skinfile:
        for linia in skinfile.readlines():
            if in_poi:
                if '[end]' in linia:
                    in_poi = False
                    _type, _icon = return_icon_definition(icon_def)
                    poi_type_icon[_type] = _icon
                    icon_def = ''
                else:
                    icon_def.append(linia.strip())
                continue
            elif '[_point]' in linia:
                in_poi = True
                continue
    return poi_type_icon


def return_icon_definition(icon_def):
    type = ''
    subtype = ''
    icon = ''
    in_xpm_def = False
    for linia in icon_def:
        if in_xpm_def:
            icon += linia.split('=', 1)[-1]
            continue
        elif linia.startswith('Type='):
            type = linia.strip('=', 1)[-1].strip()
            continue
        elif linia.startswith('SubType='):
            subtype = linia.strip('=', 1)[-1].strip()
            continue
        elif 'xpm=' in linia:
            icon += linia.split('=', 1)[-1]
            in_xpm_def = True
            continue
    return type + subtype.split('x')[-1].strip(), icon


