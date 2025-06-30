#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import misc_functions
import pwmapedit_constants
import map_items


class mapData(object):
    """class stores all data from map ie polylines, polygones, pois, map header, map weird sections"""

    def __init__(self, map_filename, map_objects_properties=None, projection=None):
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
        # wykorzystał w przypadku gdybyśmy tworzyli nowy obiekt
        self.freeObiectIdList = []
        self.listOfAttachments = []
        self.lastObjectId_POI = 0
        self.lastObjectId_Polygon = 0
        self.lastObjectId_Polyline = 0
        self.lastObjectId = 0
        self.map_filename = map_filename
        self.map_header = []

        # map bounding box, the maximal and minimal values of longitude and lattitude
        # presented as a python dictionary, with keys N, S, W, E
        # at the begining the dictionary is empty, that makes thinks a bit easier to start
        self.map_bounding_box = {}

        self.projection = projection

    def contains_data(self):
        return len(self.mapObjectsList) > 0

    def records_number(self):
        return len(self.mapObjectsList)

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
                map_object = map_items.PoiAsPixmap(self.get_object_id(),
                                                   map_objects_properties=self.map_objects_properties,
                                                   _projection=self.projection)
            elif poi_poly_type[0] == pwmapedit_constants.MAP_OBJECT_POLYLINE:
                map_object = map_items.PolylineQGraphicsPathItem(self.get_object_id(),
                                                                 map_objects_properties=self.map_objects_properties,
                                                                 _projection=self.projection)
            elif poi_poly_type[0] == pwmapedit_constants.MAP_OBJECT_POLYGON:
                map_object = map_items.PolygonQGraphicsPathItem(self.get_object_id(),
                                                                map_objects_properties=self.map_objects_properties,
                                                                _projection=self.projection)
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

    def set_map_file_name(self, file_name):
        self.map_filename = file_name

    def get_map_bounding_box(self):
        return self.map_bounding_box

    def get_all_map_objects(self):
        return self.mapObjectsList

    def clean_all_map_objects(self):
        self.mapObjectsList.clear()

    def get_object_id(self):
        return len(self.mapObjectsList)

    def get_map_file_name(self):
        return self.map_filename

    def add_map_object(self, map_object):
        # dla nowych obiektow id moze byc ustawione na None, wtedy przypisz pierwszy wolny
        if map_object.get_id() is None:
           map_object.set_id(self.get_object_id())
        if map_object.get_id() < len(self.mapObjectsList) and self.mapObjectsList[map_object.get_id()] is None:
            self.mapObjectsList[map_object.get_id()] = map_object
        else:
            self.mapObjectsList.append(map_object)

    def set_map_object_deleted(self, map_object):
        self.mapObjectsList[map_object.get_id()].set_deleted()

    def unset_map_object_deleted(self, map_object):
        self.mapObjectsList[map_object.get_id()].unset_deleted()

    def set_projection(self, _projection):
        self.projection = _projection

    def set_map_objects_properties(self, _map_objects_properties):
        self.map_objects_properties = _map_objects_properties

    def update_map_object(self, map_object):
        map_object_id = map_object.get_id()
        if map_object_id is None:
            return
        if map_object_id < len(self.mapObjectsList):
            self.mapObjectsList[map_object_id] = map_object
        return
