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
    l_type = ''
    l_subtype = ''
    l_icon = ''
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


