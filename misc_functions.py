#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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
    except (FileNotFoundError, PermissionError) as l_expection:
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


