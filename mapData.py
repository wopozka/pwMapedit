#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import string
import sys
import pwmapedit_constants
from collections import OrderedDict
import projection
from singleton_store import Store
from PyQt5.QtSvg import QGraphicsSvgItem
from PyQt5.QtWidgets import QGraphicsItemGroup


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
        self.filename = filename

        # map bounding box, the maximal and minimal values of longitude and lattitude
        # presented as a python dictionary, with keys N, S, W, E
        # at the begining the dictionary is empty, that makes thinks a bit easier to start
        self.map_bounding_box = {}

        # map projections
        # self.projection = None
        Store.projection = projection.Mercator(self.map_bounding_box)

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

            map_object = mapObject(mp_record, self.lastObjectId)
            self.lastObjectId += 1
            self.mapObjectsList.append(map_object)
            self.set_map_bounding_box(map_object.obj_bounding_box)
            del mp_record[:]
            b += 1
        Store.projection.map_bounding_box = self.map_bounding_box
        Store.projection.calculate_data_ofset()

        print('map data ofset', Store.projection.mapDataOfset)
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


class Point(object):
    """Class used for storing coordinates of given map object point"""
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
        self.obj_bounding_box = {}
        self.objectId = objectId
        self.projection = Store.projection

        self.extract_data(tuple(data))


    def extract_data(self, data):
        map_object_types = ('[POI]', '[POLYGON]', '[POLYLINE]')
        map_object_end = '[END]'
        for no, aaa in enumerate(data):
            aaa = aaa.strip()
            if not aaa:
                continue
            elif aaa.startswith(';'):
                self.comment.append(aaa)
            elif aaa in map_object_types:  # we have found begining object type data, process it further
                self.object_type = aaa
            elif aaa.startswith('Data0'):
                Data = 'Data0' + '_' + str(no)
                self.Points[Data] = self.extract_coords_from_data(aaa)
            elif aaa.startswith('Data1'):
                Data = 'Data1' + '_' + str(no)
                self.Points[Data] = self.extract_coords_from_data(aaa)
            elif aaa.startswith('Data2'):
                Data = 'Data2' + '_' + str(no)
                self.Points[Data] = self.extract_coords_from_data(aaa)
            elif aaa.startswith('Data3'):
                Data = 'Data3' + '_' + str(no)
                self.Points[Data] = self.extract_coords_from_data(aaa)
            elif aaa.startswith('Data4'):
                Data = 'Data4' + '_' + str(no)
                self.Points[Data] = self.extract_coords_from_data(aaa)
            elif aaa.startswith('Label'):
                self.Label = aaa.split('=')[-1]
            elif aaa.startswith('Type'):
                self.Type = aaa.split('=')[-1]
            elif aaa == map_object_end:  # if [END] was found it means there was no beginning, something wrong
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
        if not self.obj_bounding_box:
            self.obj_bounding_box['S'] = latitude
            self.obj_bounding_box['N'] = latitude
            self.obj_bounding_box['E'] = longitude
            self.obj_bounding_box['W'] = longitude
        else:
            if latitude <= self.obj_bounding_box['S']:
                self.obj_bounding_box['S'] = latitude
            elif latitude >= self.obj_bounding_box['N']:
                self.obj_bounding_box['N'] = latitude
            if longitude <= self.obj_bounding_box['W']:
                self.obj_bounding_box['W'] = longitude
            elif longitude >= self.obj_bounding_box['E']:
                self.obj_bounding_box['E'] = longitude
        return


class BasicMapItem(QGraphicsItemGroup):
    def __init__(self, *args, **kwargs):
        self.obj_data = OrderedDict({'Comment': list(), 'Type': '', 'Label': '', 'Label2': '', 'Label3': '',
                                     'DirIndicator': bool, 'EndLevel': '', 'StreetDesc': '', 'CityIdx': '',
                                     'DisctrictName': '', 'Phone': '', 'Highway': '',  'DataX': OrderedDict(),
                                     'Others': OrderedDict()})
        self.obj_bounding_box = {}
        super(BasicMapItem, self).__init__(*args, **kwargs)

    def set_data(self, obj_data):
        for key in obj_data:
            if key == 'Comment':
                self.obj_comment_set(obj_data[key])
            elif key == 'Type':
                self.obj_type_set(obj_data[key])
            elif key == 'Label':
                self.obj_label_set(obj_data[key])
            elif key == 'Label2':
                self.obj_label2_set(obj_data[key])
            elif key == 'Label3':
                self.obj_label3_set(obj_data[key])
            elif key == 'DirIndicator':
                self.obj_dirindicator_set(obj_data[key])
            elif key == 'EndLevel':
                self.obj_endlevel_set(obj_data[key])
            elif key == 'StreetDesc':
                self.obj_streetdesc_set(obj_data[key])
            elif key == 'Phone':
                self.obj_phone_set(obj_data[key])
            elif key == 'Highway':
                self.obj_highway_set(obj_data[key])
            elif key.startswith('Data0') or key.startswith('Data1') or key.startswith('Data2') \
                    or key.startswith('Data3') or key.startswith('Data4'):
                self.obj_datax_set(key, obj_data[key])
            else:
                self.obj_data['Other'][key] = obj_data[key]

    def obj_comment_get(self):
        return self.obj_data['Comment']

    def obj_comment_set(self, _comments):
        for _comment in _comments:
            self.obj_data['Comment'].append(_comment)

    def obj_type_get(self):
        return self.obj_data['Type']

    def obj_type_set(self, _type):
        self.obj_data['Type'] = _type

    def obj_label_get(self):
        return self.obj_data['Label']

    def obj_label_set(self, _label):
        self.obj_data['Label'] = _label

    def obj_label2_get(self):
        return self.obj_data['Label2']

    def obj_label2_set(self, _label):
        self.obj_data['Label2'] = _label

    def obj_label3_get(self):
        return self.obj_data['Label3']

    def obj_label3_set(self, _label):
        self.obj_data['Label3'] = _label

    def obj_dirindicator_get(self):
        return self.obj_data['DirIndicator']

    def obj_dirindicator_set(self, _dir):
        self.obj_data['DirIndicator'] = _dir

    def obj_endlevel_get(self):
        return self.obj_data['EndLevel']

    def obj_endlevel_set(self, _endlevel):
        self.obj_data['EndLevel'] = _endlevel

    def obj_streetdesc_get(self):
        return self.obj_data['StreetDesc']

    def obj_treetdesc_set(self, _streetdesc):
        self.obj_data['StreetDesc'] = _streetdesc

    def obj_phone_get(self):
        return self.obj_data['Phone']

    def obj_phone_set(self, _phone):
        self.obj_data['Phone'] = _phone

    def obj_highway_get(self):
        return self.obj_data['Highway']

    def obj_highway_set(self, _highway):
        self.obj_data['Highway'] = _highway

    def obj_datax_get(self):
        pass

    def obj_datax_set(self, key, _dataX):
        self.obj_data['DataX'][key] = self.coord_from_data_to_point(_dataX)

    def coords_from_data_to_points(self, data_line):
        coords = []
        coordlist = data_line.split('=')[-1]
        coordlist = coordlist.strip().lstrip('(').rstrip(')')
        for a in coordlist.split('),('):
            latitude, longitude = a.split(',')
            self.set_obj_bounding_box(float(latitude), float(longitude))
            coords.append(Point(latitude, longitude))
        return coords

    def set_obj_bounding_box(self, latitude, longitude):
        if not self.obj_bounding_box:
            self.obj_bounding_box['S'] = latitude
            self.obj_bounding_box['N'] = latitude
            self.obj_bounding_box['E'] = longitude
            self.obj_bounding_box['W'] = longitude
        else:
            if latitude <= self.obj_bounding_box['S']:
                self.obj_bounding_box['S'] = latitude
            elif latitude >= self.obj_bounding_box['N']:
                self.obj_bounding_box['N'] = latitude
            if longitude <= self.obj_bounding_box['W']:
                self.obj_bounding_box['W'] = longitude
            elif longitude >= self.obj_bounding_box['E']:
                self.obj_bounding_box['E'] = longitude
        return

    def data_values(self):
        tmp_data = OrderedDict({})
        for key in self.obj_data['DataX']:
            tmp_data[key].items()

class POI(BasicMapItem):
    def __init__(self, obj_data):
        super(POI, self).__init__()
        self.set_data(obj_data)

    def create_object(self):
        for key, val in self.data_values():
            for coord_pair in val:
                x, y = coord_pair.return_canvas_coords()
        if mapobject.Type in self.mOP.poi_icons:
            # poi = QGraphicsPixmapItem(self.mOP.poi_icons[mapobject.obj_type_get()])
            poi = QGraphicsSvgItem('icons/2a00.svg')
            poi.setPos(x, y)
            poi.setZValue(20)
            self.addItem(poi)
        else:
            print(mapobject.Type)
            poi = QGraphicsEllipseItem(x, y, 10, 10)
            brush = QBrush(Qt.black)
            poi.setBrush(brush)
            poi.setZValue(20)
            self.addItem(poi)


class Polyline(BasicMapItem):
    def __init__(self, obj_data):
        _obj_data = {'Comment': list(), 'Type': '', 'Label': '', 'EndLevel': '', 'DataX': OrderedDict({}),
                     'Other': OrderedDict({})}
        self.obj_data = OrderedDict(_obj_data)
        super(Polyline, self).__init__()
        self.set_data(obj_data)


class Polygon(BasicMapItem):
    def __init__(self, obj_data):
        _obj_data = {'Comment': list(), 'Type': '', 'Label': '', 'EndLevel': '', 'DataX': OrderedDict({}),
                     'Other': OrderedDict({})}
        self.obj_data = OrderedDict(_obj_data)
        super(Polygon, self).__init__()
        self.set_data(obj_data)


