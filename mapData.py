#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import string
import sys

import misc_functions
import pwmapedit_constants
import map_items
from PyQt5.QtGui import QPainterPath, QPixmap
from collections import OrderedDict
import projection as coordinates_projection
from singleton_store import Store
# from PyQt5.QtSvg import QGraphicsSvgItem
from PyQt5.QtWidgets import QGraphicsItemGroup


class mapData(object):
    """class stores all data from map ie polylines, polygones, pois, map header, map weird sections"""

    def __init__(self, filename, map_objects_properties=None, projection=None):
        # inicjujemy zmienne początkowe
        # z założenia każdy obiekt na mapie będzie miał swoje osobne ID. Dlatego będzie
        # przechowywany zmiennej typu listowego, gdzie ID to będzie kolejny numer
        # ten sam tag będzie miał obiekt tworzony na canvas
        # usunięcie obiektu będzie zwalniało dany ID stworzenie obiektu będzie wykorzystywało zwolnione
        # ID albo dodawało nowe na kołcu listy
        self.map_objects_properties = None
        if map_objects_properties is not None:
            self.map_objects_properties = map_objects_properties
        self.mapObjectsList_Polylines = []
        self.mapObjectsList_Polygones = []
        self.mapObjectsList_POI = []
        self.mapObjectsList = []
        # zwolnione id obiektów. W przypadku gdyby obiekt był usunięty z mapy, wtedy jego Id trafia na te
        # listę. To zwolnione id można później
        # wykorzystał w przypadku gdybyśmy tworzyli nowy obietk
        self.freeObiectIdList = []
        self.listOfAttachments = []
        self.lastObjectId_POI = 0
        self.lastObjectId_Polygon = 0
        self.lastObjectId_Polyline = 0
        self.lastObjectId = 0
        self.filename = filename

        # map bounding box, the maximal and minimal values of longitude and lattitude
        # presented as a python dictionary, with keys N, S, W, E
        # at the begining the dictionary is empty, that makes thinks a bit easier to start
        self.map_bounding_box = {}

        self.projection = projection


    def wczytaj_rekordy(self):
        print('wczytuje rekordy')

        with open(self.filename, 'r', encoding='cp1250') as a:
            zawartosc_pliku_mp = a.readlines()

        # Firstly. At the end of file there might be attachments (files or weblayers). The format is as below:
        # ;@File *, for file attached
        # ;@WEBMAP *, for web layers attached
        # we have to skipp these data as well.
        while zawartosc_pliku_mp[-1].startswith(';@'):
            print(zawartosc_pliku_mp[-1])
            self.listOfAttachments.append(zawartosc_pliku_mp[-1].strip())
            del (zawartosc_pliku_mp[-1])

        #remove all empty lines until there is the last [END] in the file
        while not zawartosc_pliku_mp[-1].strip():
            del (zawartosc_pliku_mp[-1])

        # after removal of attachments we can measure the lenght of the whole file
        zawartosc_pliku_mp_len = len(zawartosc_pliku_mp)
        b = 0

        # first lets skip the file header
        while b < zawartosc_pliku_mp_len:
            # print(b)
            if zawartosc_pliku_mp[b].strip() not in pwmapedit_constants.MAP_OBJECT_TYPES:
                b += 1
            else:
                break

        # we skipped the header, but at the same time we might have skipped
        # the first comment, try to recover it
        while b >= 0:
            if zawartosc_pliku_mp[b].strip().startswith(';'):
                b -= 1
            else:
                break

        print('zakonczylen obrabianie naglowka. Wartosc b: %s' % b)
        while b < zawartosc_pliku_mp_len:
            # print(b)
            mp_record = []
            mpfileline = zawartosc_pliku_mp[b].strip()
            while not mpfileline.startswith(pwmapedit_constants.MAP_OBJECT_END) and b < zawartosc_pliku_mp_len-1:

                mp_record.append(mpfileline)
                b += 1
                mpfileline = zawartosc_pliku_mp[b]

            poi_poly_type, obj_comment, obj_data = misc_functions.map_strings_record_to_dict_record(mp_record)
            self.lastObjectId += 1
            if poi_poly_type[0] == pwmapedit_constants.MAP_OBJECT_POI:
                poi_icon = self.map_objects_properties.get_poi_icon(poi_poly_type[1])
                if isinstance(poi_icon, QPainterPath):
                    print(mp_record)
                    map_object = map_items.PoiAsPath(map_objects_properties=self.map_objects_properties,
                                                     projection=self.projection)
                elif isinstance(poi_icon, QPixmap):
                    map_object = map_items.PoiAsPixmap(map_objects_properties=self.map_objects_properties,
                                                       projection=self.projection)
                elif isinstance(poi_icon, str):
                    map_object = map_items.AddrLabel(map_objects_properties=self.map_objects_properties,
                                                     projection=self.projection)
            elif poi_poly_type[0] == pwmapedit_constants.MAP_OBJECT_POLYLINE:
                map_object = map_items.PolylineQGraphicsPathItem(map_objects_properties=self.map_objects_properties,
                                                                 projection=self.projection)
            elif poi_poly_type[0] == pwmapedit_constants.MAP_OBJECT_POLYGON:
                map_object = map_items.PolygonQGraphicsPathItem(map_objects_properties=self.map_objects_properties,
                                                                projection=self.projection)
            elif poi_poly_type[0] == pwmapedit_constants.MAP_OBJECT_RESTRICT:
                pass
            elif poi_poly_type[0] == pwmapedit_constants.MAP_OBJECT_ROADSIGN:
                pass
            else:
                pass
            map_object.set_data(obj_comment, obj_data)
            self.mapObjectsList.append(map_object)
            self.set_map_bounding_box(map_object.obj_bounding_box)
            del mp_record[:]
            b += 1
        self.projection.set_map_bounding_box(self.get_map_bounding_box())
        self.projection.calculate_data_offset()

        print('map data ofset', self.projection.earth_radius)
        print('bonding box', self.map_bounding_box)


    def set_map_bounding_box(self, bBox):
        if not self.map_bounding_box:
            self.map_bounding_box = {k: v for k, v in bBox.items()}
        else:
            if bBox['E'] > self.map_bounding_box['E']:
                self.map_bounding_box['E'] = bBox['E']
            if bBox['W'] < self.map_bounding_box['W']:
                self.map_bounding_box['W'] = bBox['W']
            if bBox['N'] > self.map_bounding_box['N']:
                self.map_bounding_box['N'] = bBox['N']
            if bBox['S'] < self.map_bounding_box['S']:
                self.map_bounding_box['S'] = bBox['S']

    def get_map_bounding_box(self):
        return self.map_bounding_box

    def get_all_map_objects(self):
        return self.mapObjectsList

    def clean_all_map_objects(self):
        self.mapObjectsList.clear()
