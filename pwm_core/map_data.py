#!/usr/bin/env python3
# -*- coding: utf-8 -*-

class MapData(object):
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
        # najwieksza precyzja wspolrzednych wczytanych obiektow; przy zapisie dostaja ja obiekty, ktorych precyzja
        # nie jest znana (np. narysowane w programie)
        self.precision = None

    def contains_data(self):
        return len(self.mapObjectsList) > 0

    def records_number(self):
        return len(self.mapObjectsList)

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

    def update_precision(self, map_object):
        data = getattr(map_object, 'data0', None)
        if data is not None and data.precision is not None:
            self.precision = data.precision if self.precision is None else max(self.precision, data.precision)

    def get_precision(self):
        return self.precision

    def add_map_object(self, map_object):
        self.update_precision(map_object)
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
