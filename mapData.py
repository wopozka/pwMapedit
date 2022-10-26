#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import string
import sys
from collections import OrderedDict
import projection
from singleton_store import Store

class mapData(object):
    """class stores all data from map ie polylines, polygones, pois, map header, map weird sections"""

    def __init__(self, filename):
        # inicjujemy zmienne początkowe
        # z założenia każdy obiekt na mapie będzie miał swoje osobne ID. Dlatego będzie
        # przechowywany zmiennej typu listowego, gdzie ID to będzie kolejny numer
        # ten sam tag będzie miał obiekt tworzony na canvas
        # usunięcie obiektu będzie zwalniało dany ID stworzenie obiektu będzie wykorzystywało zwolnione
        # ID albo dodawało nowe na kołcu listy
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
        self.MAP_OBJECT_TYPES = ('[POI]', '[POLYGON]', '[POLYLINE]')
        self.MAP_OBJECT_END = '[END]'
        self.filename = filename

        # map bounding box, the maximal and minimal values of longitude and lattitude
        # presented as a python dictionary, with keys N, S, W, E
        # at the begining the dictionary is empty, that makes thinks a bit easier to start
        self.mapBoundingBox = {}

        # map projections
        # self.projection = None
        Store.projection=projection.Mercator(self.mapBoundingBox)

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
            if zawartosc_pliku_mp[b].strip() not in self.MAP_OBJECT_TYPES:
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

        print('zakonczylen obrabianie naglowka. Wartosc b: %s'%b)
        print(self.mapBoundingBox)
        while b < zawartosc_pliku_mp_len:
            # print(b)
            mp_record = []
            mpfileline = zawartosc_pliku_mp[b].strip()
            while not mpfileline.startswith(self.MAP_OBJECT_END) and b < zawartosc_pliku_mp_len-1:

                mp_record.append(mpfileline)
                b += 1
                mpfileline = zawartosc_pliku_mp[b]

            map_object = mapObject(mp_record, self.lastObjectId)
            self.lastObjectId += 1
            self.mapObjectsList.append(map_object)
            self.set_map_bounding_box(map_object.objBoundingBox)
            del mp_record[:]
            b += 1
        Store.projection.mapBoundingBox = self.mapBoundingBox
        Store.projection.calculate_data_ofset()

        print(Store.projection.mapDataOfset)

    def set_map_bounding_box(self, bBox):
        if not self.mapBoundingBox:
            self.mapBoundingBox = {k: v for k, v in bBox.items()}
        else:
            if bBox['E'] > self.mapBoundingBox['E']:
                self.mapBoundingBox['E'] = bBox['E']
            if bBox['W'] < self.mapBoundingBox['W']:
                self.mapBoundingBox['W'] = bBox['W']
            if bBox['N'] > self.mapBoundingBox['N']:
                self.mapBoundingBox['N'] = bBox['N']
            if bBox['S'] < self.mapBoundingBox['S']:
                self.mapBoundingBox['S'] = bBox['S']


class Point(object):
    """Class used for stroing coordinates of given map object point"""
    def __init__(self, latitude, longitude):
        # self.acuracy = 10000
        self.longitude = longitude
        self.latitude = latitude

    def return_canvas_coords(self):
        # print(Store.projection.projectionName)
        coords = Store.projection.geo_to_canvas(self.latitude, self.longitude)
        return coords

    def return_real_coords(self):
        coords = Store.projection.canvas_to_geo()
        return coords

class mapObject(object):
    """The class stores information about the map object ie. POI, POLYLINE, POLYGON.
    All properties of this objects residue here"""

    def __init__(self, data, objectId):
        self.MAP_OBJECT_TYPES = ('[POI]', '[POLYGON]', '[POLYLINE]')
        self.MAP_OBJECT_END = '[END]'
        self.comment = []
        self.object_type = ''  # possible 3 values, [POI], [POLYLINE], [POLYGONE]
        self.Type = None  # Type value
        self.EndLevel = None  # Endlevel
        self.Label = None
        self.Points = OrderedDict()  # objects coordinates as a list of instances point class
        # maximal and minimal values for coordinates for the given object

        # bounding box for the object. The dictionary with NSEW keys, and values of minimal and
        # maximal longitudes and latitudes. At the begining it is empty dictionary, because it makes
        # thinks to start easier
        self.objBoundingBox = {}
        self.objectId=objectId
        self.projection = Store.projection

        self.extract_data(data)


    def extract_data(self, data):
        Data0_val = Data1_val = Data2_val = Data2_val = Data3_val = Data4_val = 0
        for aaa in data[:]:
            aaa=aaa.strip()
            if aaa.startswith(';'):
                self.comment.append(aaa)

            elif aaa in self.MAP_OBJECT_TYPES:  # we have found begining object type data, process it further
                self.object_type = aaa

            elif aaa.startswith('Data0'):
                Data='Data0'+'_'+str(Data0_val)
                Data0_val += 1
                self.Points [Data] = self.extract_coords_from_data(aaa)
            elif aaa.startswith('Data1'):
                Data='Data1'+'_'+str(Data1_val)
                Data1_val += 1
                self.Points [Data] = self.extract_coords_from_data(aaa)
            elif aaa.startswith('Data2'):
                Data='Data2'+'_'+str(Data2_val)
                Data2_val += 1
                self.Points [Data] = self.extract_coords_from_data(aaa)
            elif aaa.startswith('Data3'):
                Data='Data3'+'_'+str(Data3_val)
                Data3_val += 1
                self.Points [Data] = self.extract_coords_from_data(aaa)
            elif aaa.startswith('Data4'):
                Data='Data4'+'_'+str(Data4_val)
                Data4_val += 1
                self.Points [Data] = self.extract_coords_from_data(aaa)
            elif aaa.startswith('Label'):
                self.Label = aaa.split('=')[-1]
            elif aaa.startswith('Type'):
                self.Type = aaa.split('=')[-1]
            elif aaa == self.MAP_OBJECT_END:  # if [END] was found it means there was no beginning, something wrong
                # with datafile
                pass
            elif not aaa:  # empy lines separate records, after strip() we receive empty string
                pass
            else:
                pass

    def extract_coords_from_data(self, Dataline):
        coord = []
        coordlist = Dataline.split('=')[-1]
        coordlist = coordlist.strip().lstrip('(').rstrip(')')
        for a in coordlist.split('),('):
            latitude, longitude = a.split(',')
            self.set_obj_bounding_box(float(latitude), float(longitude))
            coord.append(Point(latitude, longitude))
        return coord

    def set_obj_bounding_box(self, latitude, longitude):
        if not self.objBoundingBox:
            self.objBoundingBox['S'] = latitude
            self.objBoundingBox['N'] = latitude
            self.objBoundingBox['E'] = longitude
            self.objBoundingBox['W'] = longitude
        else:
            if latitude <= self.objBoundingBox['S']:
                self.objBoundingBox['S'] = latitude
            elif latitude >= self.objBoundingBox['N']:
                self.objBoundingBox['N'] = latitude
            if longitude <= self.objBoundingBox['W']:
                self.objBoundingBox['W'] = longitude
            elif longitude >= self.objBoundingBox['E']:
                self.objBoundingBox['E'] = longitude
        return