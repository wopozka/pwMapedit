#!/usr/bin/env python3
# -*- coding: utf-8 -*-

class MapObjDefinitions(object):
    """"basic map object class"""
    def __init__(self, skins_file):
        self.poi_type_icon = dict()

    def read_icons_from_skin_file(self, skin_filename):
        with open(skin_filename, 'r') as skinfile:
            skin_file_content = skinfile.readlines()
        in_poi = False
        type = ''
        subtype = ''
        icon = ''
        in_xpm_def = False
        for linia in skin_file_content:
            if in_poi:
                if linia.startswith('Type='):
                    type = linia.strip('=', 1)[-1].strip()
                    continue
                elif linia.startswith('SubType='):
                    subtype = linia.strip('=', 1)[-1].strip()
                    continue
                elif 'xpm=' in linia:
                    icon += linia.split('=', 1)[-1]
                    in_xpm_def = True
                    continue
                elif '[end]' in linia:
                    in_poi = False
                    in_xpm_def = False
                    self.poi_type_icon[type + subtype.split('x')[-1]] = icon
                    icon = ''
                    type = ''
                    subtype = ''
                    continue
                elif in_xpm_def:
                    icon += linia.split('=', 1)[-1]
                    continue
            elif '[_point]' in linia:
                in_poi = True
                continue


