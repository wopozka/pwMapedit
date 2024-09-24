import math
from collections import OrderedDict, namedtuple
import misc_functions
# from singleton_store import Store
# from PyQt5.QtSvg import QGraphicsSvgItem
from PyQt5.QtWidgets import QGraphicsItemGroup
from PyQt5.QtWidgets import QGraphicsPixmapItem, QGraphicsEllipseItem, QGraphicsPathItem, QGraphicsItem, \
    QGraphicsPolygonItem, QStyle, QGraphicsSimpleTextItem
from PyQt5.QtCore import QPointF, Qt, QLineF, QPoint
from PyQt5.QtGui import QPainterPath, QPolygonF, QBrush, QPen, QColor, QPainterPathStroker, QCursor, QVector2D
from datetime import datetime
from pwmapedit_constants import IGNORE_TRANSFORMATION_TRESHOLD

Numbers_Definition = namedtuple('Numbers_Definition',
                                ['left_side_numbering_style',
                                 'first_number_on_left_ide', 'last_number_on_left_side', 'right_side_numbering_style',
                                 'first_number_on_right_side', 'last_number_on_right_side', 'left_side_zip_code',
                                 'right_side_zip_code', 'left_side_city', 'left_side_region', 'left_side_country',
                                 'right_side_city', 'right_side_region', 'right_side_country']
                                )

Number_Index = namedtuple('Number_Index', ['data_level', 'data_num', 'index_of_point_in_the_polyline'])

class Data_X(object):
    """storing multiple data it is probably better to do it in the separate class, as some operations might be easier"""
    def __init__(self, data_level=0):
        self.nodes_list = []
        self.outer_inner = []
        self.last_outer_index = 0
        self.polygon = False
        self.hlevel_offset = None
        self.data_level = data_level

    def add_points(self, points_list):
        self.nodes_list.append(points_list)
        self.outer_inner.append('outer')
        if self.hlevel_offset is None:
            self.hlevel_offset = 0
        else:
            self.hlevel_offset += len(points_list)

    def get_nodes(self):
        returned_data = list()
        for data_list in self.nodes_list:
            returned_data.append(data_list)
        return returned_data

    def set_polygon(self):
        self.polygon = True

    def is_polygon(self):
        return self.polygon

    def get_translated_hlevels(self, orig_hlevels):
        node_num, hlevel = orig_hlevels
        if isinstance(node_num, str):
            node_num = int(node_num)
        if isinstance(hlevel, str):
            hlevel = int(hlevel)
        return node_num + self.hlevel_offset, hlevel

    def get_data_level(self):
        return self.data_level


class Data_X1(object):
    def __init__(self, projection=None):
        self.projection = projection
        # dane mozna by przechowywac w slownikach, ale poniewaz jest ich duzo, dlatego pod wzgledem przechowywania
        # uzycie list bedzie sporo bardziej efektywne pod wzgledem wielkosci pamieci. Jako ze mapy moga byc duze, moze
        # miec to znaczenia.

        # Data0, Data1, Data2, Data3, Data4...
        # przechowuje informacje pod ktorym indeksem jest przechowywana jaki level
        self._data_levels = []
        # przechowuje wspolrzedne punktow dla Data0, Data1, Data2 ..., w postaci listy list. Pierwsza lista to
        # dany Data, druga lista w tej liscie, to dany polyline, albo polygon
        self._poly_data_points = []

        # boundingbox dla danych data, tu latwiej i szybciej to obliczyc
        self._bounding_box_N = None
        self._bounding_box_S = None
        self._bounding_box_W = None
        self._bounding_box_E = None

        # dobrze wiedzieć ktory data byl ostatnio dodawany, na potrzeby numeracji, przechowujmy
        # wiec te dane. To sa istotne kwestie przy wczytywaniu
        self._last_data_level = 0
        self._last_poly_data_index = 0

        # definicje numeracji
        self._numbers_definitions = None

    def add_nodes_from_string(self, data_string):
        datax, values = data_string.strip().split('=', 1)
        data_level = int(datax[4:])
        if data_level not in self._data_levels:
            self._data_levels.append(data_level)
            self._poly_data_points.append([])
        data_index = self._data_levels.index(data_level)
        self._poly_data_points[data_index].append(self.coords_from_data_to_nodes(values))
        self._last_data_level = data_level
        self._last_poly_data_index = len(self._poly_data_points[data_index]) - 1

    def add_housenumbers_from_string(self, num_string, data_level, cur_poly_num):
        _, definition = num_string.split('=', 1)
        numbers_indexes = (0, 2, 3, 5, 6)
        num_def = [None for _ in range(10)]
        index_of_point_in_the_polyline, definition = definition.split(',', 1)
        index_of_point_in_the_polyline = int(index_of_point_in_the_polyline)
        for no, elem in enumerate(definition.split(',')):
            if elem == '-1' or not elem.isdigit():
                continue
            elif no in numbers_indexes:
                num_def[no] = int(elem)
            else:
                num_def[no] = elem
        if self._numbers_definitions is None:
            self._numbers_definitions = OrderedDict()
        n_index = Number_Index(data_level, cur_poly_num, index_of_point_in_the_polyline)
        self._numbers_definitions[n_index] = Numbers_Definition(num_def[0], num_def[1], num_def[2], num_def[3],
                                                                num_def[4], num_def[5], num_def[6], num_def[7],
                                                                num_def[8], num_def[9], num_def[10], num_def[11],
                                                                num_def[12], num_def[13])

    def get_housenumbers_nodes_defs(self, data_level, cur_poly_num):
        housenumbers = []
        for node in self._numbers_definitions:
            if node.data_level != data_level:
                continue
            if node.cur_poly_num == cur_poly_num:
                housenumbers.append(self._numbers_definitions[node])
        return housenumbers

    def update_housenumbers_after_point_insert(self):
        pass


    def coords_from_data_to_nodes(self, data_line):
        coords = []
        coordlist = data_line.strip().lstrip('(').rstrip(')')
        for a in coordlist.split('),('):
            latitude, longitude = a.split(',')
            self.set_obj_bounding_box(float(latitude), float(longitude))
            coords.append(Node(latitude=latitude, longitude=longitude, projection=self.projection))
        return coords

    def set_obj_bounding_box(self, latitude, longitude):
        if self._bounding_box_N is None:
            self._bounding_box_S = latitude
            self._bounding_box_N = latitude
            self._bounding_box_E = longitude
            self._bounding_box_W = longitude
        else:
            if latitude <= self._bounding_box_S:
                self._bounding_box_S = latitude
            elif latitude >= self._bounding_box_N:
                self._bounding_box_N = latitude
            if longitude <= self._bounding_box_W:
                self._bounding_box_W = longitude
            elif longitude >= self._bounding_box_E:
                self._bounding_box_E = longitude
        return

    def get_obj_bounding_box(self):
        return {'S': self._bounding_box_S, 'N': self._bounding_box_N, 'E': self._bounding_box_E,
                'W': self._bounding_box_E}

    def get_poly_nodes(self, data_level, qpointsf):
        if data_level not in self._data_levels:
            return None
        returned_data = list()
        for data_list in self._poly_data_points[self._data_levels.index(data_level)]:
            if qpointsf:
                returned_data.append([a.get_canvas_coords_as_qpointf() for a in data_list])
            else:
                returned_data.append(data_list)
        return returned_data

    def get_data_levels(self):
        return self._data_levels

    def get_last_data_level_and_last_index(self):
        return self._last_data_level, self._last_poly_data_index

class Node(object):
    """Class used for storing coordinates of given map object point"""
    def __init__(self, latitude=None, longitude=None, projection=None):
        # self.acuracy = 10000
        self.projection = None
        self.latitude = None
        self.longitude = None
        if projection is not None:
            self.projection = projection
        if latitude is not None and longitude is not None:
            self.set_coordinates(latitude, longitude)

    def set_coordinates(self, latitude, longitude):
        self.longitude = longitude
        self.latitude = latitude

    def get_coordinates(self):
        return self.latitude, self.longitude

    def get_canvas_coords(self):
        # print(Store.projection.projectionName)
        return self.projection.geo_to_canvas(self.latitude, self.longitude)

    def get_canvas_coords_as_qpointf(self):
        x, y = self.get_canvas_coords()
        return QPointF(x, y)

    def return_real_coords(self):
        return self.projection.canvas_to_geo()


Numbers_Definition = namedtuple('Numbers_Definition',
                                ['left_side_numbering_style',
                                 'first_number_on_left_ide', 'last_number_on_left_side', 'right_side_numbering_style',
                                 'first_number_on_right_side', 'last_number_on_right_side', 'left_side_zip_code',
                                 'right_side_zip_code', 'left_side_city', 'left_side_region', 'left_side_country',
                                 'right_side_city', 'right_side_region', 'right_side_country']
                                )


class Numbers(object):
    # class for storing definitions of numbers along the roads
    even = 2
    odd = 1
    both = 0

    def __init__(self, numbers_defition):
        # przechowuje informacje pod ktorym indeksem jest przechowywana jaki level
        self._data_levels = []
        # przechowuje informacje dla ktorego kolejnej polyline sa dane dla danego _data_levels
        self._poly_num = []
        # konkretne definicje - lista, list, list
        self._numbers_definitions = []

    def add_definitions_from_string(self, num_string, data_level, cur_poly_num):
        _, definition = num_string.split('=', 1)
        numbers_indexes = (0, 2, 3, 5, 6)
        num_def = [None for _ in range(10)]
        for no, elem in enumerate(definition.split(',')):
            if elem == '-1' or not elem.isdigit():
                continue
            elif no in numbers_indexes:
                num_def[no] = int(elem)
            else:
                num_def[no] = elem
        if data_level in self._data_levels:
            dl_index = self._data_levels.index(data_level)
        else:
            dl_index = len(self._data_levels)
            self._data_levels.append(data_level)
            self._poly_num.append([])
            # self._numbers_definitions.append([[]])
        if cur_poly_num in self._poly_num[dl_index]:
            poly_index = self._poly_num[dl_index].index(cur_poly_num)
        else:
            poly_index = len(self._poly_num[dl_index])
            self._poly_num[dl_index].append(cur_poly_num)
            self._numbers_definitions[poly_index].append([])
        self._numbers_definitions[dl_index][poly_index].append(Numbers_Definition(num_def[0], num_def[1], num_def[2],
                                                                                  num_def[3], num_def[4], num_def[5],
                                                                                  num_def[6], num_def[7], num_def[8],
                                                                                  num_def[9], num_def[10], num_def[11],
                                                                                  num_def[12], num_def[13], num_def[14]
                                                                                  )
                                                               )

    def get_data_levels(self):
        return self._data_levels

    def get_poly_numbers(self, data_level):
        return self._poly_num[data_level]

    def get_number_definition(self, data_level, poly_num):
        return self._numbers_definitions[data_level][poly_num]


# tutaj chyba lepiej byloby uzyc QPainterPath
# class BasicMapItem(QGraphicsItemGroup):
class BasicMapItem(object):
    def __init__(self, map_objects_properties=None, projection=None):
        """
        basic map items properties, derived map items inherit from it
        Parameters
        ----------
        map_objects_properties = class for map elements appearance: icons, line types, area patterns and filling
        projection = projection class
        """
        # super(BasicMapItem, self).__init__()
        self.projection = None
        self.map_objects_properties = None
        if projection is not None:
            self.projection = projection
        if map_objects_properties is not None:
            self.map_objects_properties = map_objects_properties
        self.obj_comment = list()
        self.type = None
        self.label1 = None
        self.label2 = None
        self.label3 = None
        self.dirindicator = None
        self.endlevel = 0
        self.streetdesc = None
        self.housenumber = None
        self.phone = None
        self.cityidx = None
        self.data0 = None
        self.data1 = None
        self.data2 = None
        self.data3 = None
        self.data4 = None
        self.last_data_level = None
        self.hlevels0 = None
        self.hlevels1 = None
        self.hlevels2 = None
        self.hlevels3 = None
        self.hlevels4 = None
        self.hlevels_other = None
        self.routeparam = None
        self.cityname = None
        self.countryname = None
        self.countrycode = None
        self.regionname = None
        self.roadid = None
        self.zipcode = None
        self.others = OrderedDict()
        self.obj_bounding_box = {}

    def __repr__(self):
        return str(self.type)

    def __str__(self):
        return str(self.type)

    def set_data(self, comment_data, obj_data):
        """
        Setting element properties when red from disk
        Parameters
        ----------
        obj_data: dict() key: tuple(elem_position, elem_name), value: value
        Returns
        -------

        """
        if comment_data is not None and comment_data:
            self.set_comment(comment_data)
        for number_keyname in obj_data:
            _, key = number_keyname
            if number_keyname[1] == 'Type':
                self.set_param('Type', int(obj_data[number_keyname], 16))
            elif number_keyname[1] in ('Highway', 'CityName', 'CountryName', 'RegionName',
                                       'CountryCode', 'ZipCode'):
                self.set_param(key, obj_data[number_keyname])
            elif number_keyname[1] in ('Data0', 'Data1', 'Data2', 'Data3', 'Data4'):
                self.set_datax(number_keyname[1], obj_data[number_keyname])
            elif number_keyname[1] == 'RouteParam':
                if self.routeparam is None:
                    self.routeparam = []
                for single_param in obj_data[number_keyname].split(','):
                    self.routeparam.append(int(single_param))
            elif number_keyname[1] == 'StreetDesc':
                self.set_street_desc(obj_data[number_keyname])
            elif number_keyname[1] == 'HouseNumber':
                self.set_house_number(obj_data[number_keyname])
            elif number_keyname[1] == 'Phone':
                self.set_phone_number(obj_data[number_keyname])
            elif number_keyname[1] == 'Label':
                self.set_label1(obj_data[number_keyname])
            elif number_keyname[1] == 'Label2':
                self.set_label2(obj_data[number_keyname])
            elif number_keyname[1] == 'Label3':
                self.set_label3(obj_data[number_keyname])
            elif number_keyname[1] == 'DirIndicator':
                self.set_dirindicator(obj_data[number_keyname])
            elif number_keyname[1] == 'EndLevel':
                self.set_endlevel(obj_data[number_keyname])
            elif number_keyname[1] == 'RoadID':
                self.roadid = int(obj_data[number_keyname])
            elif number_keyname[1].startswith('Nod'):
                pass
            elif number_keyname[1].startswith('Numbers'):
                pass
            elif number_keyname[1].startswith('HLevel'):
                self.set_hlevels(obj_data[number_keyname])
            # elif number_keyname[1] in ('Miasto', 'Typ', 'Plik'):
            #     # temporary remove these from reporting
            #     pass
            else:
                self.set_others(number_keyname, obj_data[number_keyname])
                # print('Unknown key value: %s.' % number_keyname[1])

    def get_comment(self):
        return self.obj_comment

    def set_comment(self, _comments):
        for _comment in _comments:
            self.obj_comment.append(_comment)

    def get_dirindicator(self):
        if self.dirindicator is None:
            return False
        return self.dirindicator

    def set_dirindicator(self, value):
        self.dirindicator = value

    def get_param(self, parameter):
        return getattr(self, parameter.lower())

    def set_param(self, parameter, value):
        setattr(self, parameter.lower(), value)
        # self.obj_data[parameter] = value

    def set_endlevel(self, value):
        if isinstance(value, str):
            value = int(value)
        self.endlevel = value

    def get_endlevel(self):
        return self.endlevel

    def set_street_desc(self, value):
        self.streetdesc = value

    def get_street_desc(self):
        if self.streetdesc is None:
            return ''
        return self.streetdesc

    def set_house_number(self, value):
        self.housenumber = value

    def get_house_number(self):
        if self.housenumber is None:
            return ''
        return self.housenumber

    def set_phone_number(self, value):
        self.phone = value

    def get_phone_number(self):
        if self.phone is None:
            return ''
        return self.phone

    def set_label1(self, value):
        self.label1 = value

    def get_label1(self):
        if self.label1 is not None:
            return self.label1
        return ''

    def set_label2(self, value):
        self.label2 = value

    def get_label2(self):
        if self.label2 is not None:
            return self.label2
        return ''

    def set_label3(self, value):
        self.label3 = value

    def get_label3(self):
        if self.label3 is not None:
            return self.label3
        return ''

    def get_datax(self, dataX):
        # tymczasowo na potrzeby testow tylko jedno data
        # zwracamy liste Nodow, jesli
        datax = dataX.lower()
        if datax == 'data0':
            return self.data0.get_nodes() if self.data0 is not None else tuple()
        elif datax == 'data1':
            return self.data1.get_nodes() if self.data1 is not None else tuple()
        elif datax == 'data2':
            return self.data2.get_nodes() if self.data2 is not None else tuple()
        elif datax == 'data3':
            return self.data3.get_nodes() if self.data3 is not None else tuple()
        elif datax == 'data4':
            return self.data4.get_nodes() if self.data4 is not None else tuple()

    def set_datax(self, data012345, data012345_val):
        datax = data012345.lower()
        if datax == 'data0':
            if self.data0 is None:
                self.data0 = Data_X(data_level=0)
            self.data0.add_points(self.coords_from_data_to_nodes(data012345_val))
            self.last_data_level = self.data0
        elif datax == 'data1':
            if self.data1 is None:
                self.data1 = Data_X(data_level=1)
            self.data1.add_points(self.coords_from_data_to_nodes(data012345_val))
            self.last_data_level = self.data1
        elif datax == 'data2':
            if self.data2 is None:
                self.data2 = Data_X(data_level=2)
            self.data2.add_points(self.coords_from_data_to_nodes(data012345_val))
            self.last_data_level = self.data2
        elif datax == 'data3':
            if self.data3 is None:
                self.data3 = Data_X(data_level=3)
            self.data3.add_points(self.coords_from_data_to_nodes(data012345_val))
            self.last_data_level = self.data3
        elif datax == 'data4':
            if self.data4 is None:
                self.data4 = Data_X(data_level=4)
            self.data4.add_points(self.coords_from_data_to_nodes(data012345_val))
            self.last_data_level = self.data4
        return

    def set_others(self, key, value):
        self.others[key] = value

    def get_others(self):
        return_val = list()
        for key_tuple, val in self.others.items():
            key = key_tuple[1]
            return_val.append((key, val,))
        return return_val

    def coords_from_data_to_nodes(self, data_line):
        coords = []
        coordlist = data_line.strip().lstrip('(').rstrip(')')
        for a in coordlist.split('),('):
            latitude, longitude = a.split(',')
            self.set_obj_bounding_box(float(latitude), float(longitude))
            coords.append(Node(latitude=latitude, longitude=longitude, projection=self.projection))
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

    def get_hlevels(self, level_for_data):
        if isinstance(level_for_data, int):
            level = level_for_data
        else:
            level = int(level_for_data[-1])
        if level == 0:
            return self.hlevels0 if self.hlevels0 is not None else tuple()
        elif level == 1:
            return self.hlevels1 if self.hlevels1 is not None else tuple()
        elif level == 2:
            return self.hlevels2 if self.hlevels2 is not None else tuple()
        elif level == 3:
            return self.hlevels3 if self.hlevels3 is not None else tuple()
        elif level == 4:
            return self.hlevels4 if self.hlevels4 is not None else tuple()
        return self.hlevels_other if self.hlevels_other is not None else tuple()

    def set_hlevels(self, hlevel_items):
        _hlevel = []
        for hlevel_item in hlevel_items.lstrip('(').rstrip(')').split('),('):
            _hlevel.append(self.last_data_level.get_translated_hlevels(hlevel_item.split(',')))
        if self.last_data_level.get_data_level() == 0:
            if self.hlevels0 is None:
                self.hlevels0 = []
            self.hlevels0 += _hlevel
        elif self.last_data_level.get_data_level() == 1:
            if self.hlevels1 is None:
                self.hlevels1 = []
            self.hlevels1 += _hlevel
        elif self.last_data_level.get_data_level() == 2:
            if self.hlevels2 is None:
                self.hlevels2 = []
            self.hlevels2 += _hlevel
        elif self.last_data_level.get_data_level() == 3:
            if self.hlevels3 is None:
                self.hlevels3 = []
            self.hlevels3 += _hlevel
        elif self.last_data_level.get_data_level() == 4:
            if self.hlevels4 is None:
                self.hlevels4 = []
            self.hlevels4 += _hlevel
        else:
            if self.hlevels_other is None:
                self.hlevels_other = []
            self.hlevels_other += _hlevel


class BasicSignRestrict(object):
    def __init__(self, map_comment_data=None, map_elem_data=None):
        self.obj_comment = []
        self.restr_sign_data = None
        self.restr_sign_data_others = OrderedDict({})
        if map_comment_data is not None:
            for _comment in map_comment_data:
                self.obj_comment.append(_comment)
        self.set_data(map_elem_data)

    def set_data(self, map_elem_data):
        for number_keyname in map_elem_data:
            _, key = number_keyname
            if key in self.restr_sign_data:
                self.restr_sign_data[key].append(map_elem_data[number_keyname])
            else:
                self.restr_sign_data_others[number_keyname] = map_elem_data[number_keyname]


class RoadSign(object):
    def __init__(self, map_comment_data=None, map_elem_data=None):
        super(RoadSign, self).__init__(map_comment_data=map_comment_data, map_elem_data=map_elem_data)
        self.restr_sign_data = OrderedDict({'SignPoints': [], 'SignRoads': [], 'SignParams': []})


class Restriction(object):
    def __init__(self, map_comment_data=None, map_elem_data=None):
        super(Restriction, self).__init__(map_comment_data=map_comment_data, map_elem_data=map_elem_data)
        self.restr_sign_data = OrderedDict({'Nod': [], 'TraffPoints': [], 'TraffRoads': []})


class PoiAsPath(BasicMapItem, QGraphicsPathItem):
    # basic class for poi without pixmap icon
    _accept_map_level_change = True

    def __init__(self, map_objects_properties=None, projection=None):
        # super(PoiAsPath, self).__init__(map_objects_properties=map_objects_properties, projection=projection)
        BasicMapItem.__init__(self, map_objects_properties=map_objects_properties, projection=projection)
        QGraphicsPathItem.__init__(self)
        self.label = None
        self._mp_data = [None, None, None, None, None]
        # self._mp_end_level = 0
        # setting level 4, makes it easier to handle levels when file is loaded
        self._current_map_level = 4
        # self.icon = icon
        self.setZValue(20)
        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable)
        self.current_data_x = 4
        self.set_brush()

    @staticmethod
    def accept_map_level_change():
        return True

    def set_map_level(self):
        level = self.scene().get_map_level()
        if self._mp_data[level] is not None:
            self.setPos(self._mp_data[level])
            self.setVisible(True)
        elif self._mp_data[level] is None and self.get_endlevel() < level:
            self.setVisible(False)
        elif self._mp_data[level] is None and self.get_endlevel() >= level:
            self.setVisible(True)
        return

    def set_mp_data(self):
        for given_level in ('Data0', 'Data1', 'Data2', 'Data3', 'Data4'):
            data = self.get_datax(given_level)
            if not data:
                continue
            if self.path().isEmpty():
                self.setPath(self.map_objects_properties.get_poi_icon(self.get_param('Type')))
            level = int(given_level[-1])
            # creates qpainterpaths for polylines at given Data level
            node = data[0]
            x, y = node[0].get_canvas_coords()
            self._mp_data[level] = QPointF(x, y)
            if self.pos().isNull():
                self.setPos(self._mp_data[level])
                self.current_data_x = level

    def add_label(self):
        label = self.get_label1()
        if label is not None and label:
            self.label = PoiLabel(label, self)

    def set_brush(self):
        brush = self.map_objects_properties.get_nonpixmap_poi_brush(self.get_param('Type'))
        if brush:
            self.setBrush(brush)

    def decorate(self):
        pass

    def undecorate(self):
        pass


class PoiAsPixmap(BasicMapItem, QGraphicsPixmapItem):
    _accept_map_level_change = True

    # basic class for poi with pixmap icon
    def __init__(self, map_objects_properties=None, projection=None):
        # super(PoiAsPixmap, self).__init__(map_objects_properties=map_objects_properties, projection=projection)
        BasicMapItem.__init__(self, map_objects_properties=map_objects_properties, projection=projection)
        QGraphicsPixmapItem.__init__(self)
        self.label = None
        self._mp_data = [None, None, None, None, None]
        # self._mp_end_level = 0
        self._mp_label = None
        # setting level 4, makes it easier to handle levels when file is loaded
        self._current_map_level = 4
        # self.icon = self.map_objects_properties.get_poi_icon(self.get_param('Type'))
        self.setZValue(20)
        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable)
        self.current_data_x = 4
        self.set_transformation_flag()

    @staticmethod
    def accept_map_level_change():
        return True

    def paint(self, painter, option, widget):
        self.set_transformation_flag()
        super().paint(painter, option, widget)

    def set_transformation_flag(self):
        if self.scene() is None:
            return
        if self.scene().get_viewer_scale() > IGNORE_TRANSFORMATION_TRESHOLD:
            if not bool(self.flags() & QGraphicsItem.ItemIgnoresTransformations):
                self.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)
        else:
            if bool(self.flags() & QGraphicsItem.ItemIgnoresTransformations):
                self.setFlag(QGraphicsItem.ItemIgnoresTransformations, False)

    def set_map_level(self):
        level = self.scene().get_map_level()
        if self._mp_data[level] is not None:
            self.setPos(self._mp_data[level])
            self.setVisible(True)
        elif self._mp_data[level] is None and self.get_endlevel() < level:
            self.setVisible(False)
        elif self._mp_data[level] is None and self.get_endlevel() >= level:
            self.setVisible(True)
        self._current_map_level = level
        return

    def set_mp_data(self):
        for given_level in ('Data0', 'Data1', 'Data2', 'Data3', 'Data4'):
            data = self.get_datax(given_level)
            if not data:
                continue
            if self.pixmap().isNull():
                self.setPixmap(self.map_objects_properties.get_poi_icon(self.get_param('Type')))
            level = int(given_level[-1])
            node = data[0]
            x, y = node[0].get_canvas_coords()
            self._mp_data[level] = QPointF(x, y)
            if self.pos().isNull():
                self.setPos(self._mp_data[level])
                self.current_data_x = level

    def add_label(self):
        label = self.get_label1()
        if label is not None and label:
            self.label = PoiLabel(label, self)
            if self._mp_label is None:
                self._mp_label = label

    def set_brush(self):
        pass

    def decorate(self):
        pass

    def undecorate(self):
        pass


class AddrLabel(BasicMapItem, QGraphicsSimpleTextItem):
    _accept_map_level_change = True

    def __init__(self, map_objects_properties=None, projection=None):
        # super(AddrLabel, self).__init__(map_objects_properties=map_objects_properties, projection=projection)
        BasicMapItem.__init__(self, map_objects_properties=map_objects_properties, projection=projection)
        QGraphicsSimpleTextItem.__init__(self)
        self.setZValue(20)
        self.setText('__tmp__')
        self._mp_data = [None, None, None, None, None]
        # self._mp_end_level = 0
        self._mp_label = ''
        # setting level 4, makes it easier to handle levels when file is loaded
        self._current_map_level = 4
        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable)
        self.current_data_x = 4
        self.set_transformation_flag()

    @staticmethod
    def accept_map_level_change():
        return True

    def paint(self, painter, option, widget):
        self.set_transformation_flag()
        super().paint(painter, option, widget)

    def set_transformation_flag(self):
        if self.scene() is None:
            return
        if self.scene().get_viewer_scale() > IGNORE_TRANSFORMATION_TRESHOLD:
            if not bool(self.flags() & QGraphicsItem.ItemIgnoresTransformations):
                self.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)
        else:
            if bool(self.flags() & QGraphicsItem.ItemIgnoresTransformations):
                self.setFlag(QGraphicsItem.ItemIgnoresTransformations, False)

    def set_map_level(self):
        level = self.scene().get_map_level()
        if self._mp_data[level] is not None:
            self.setPos(self._mp_data[level])
            self.setVisible(True)
        elif self._mp_data[level] is None and self.get_endlevel() < level:
            self.setVisible(False)
        elif self._mp_data[level] is None and self.get_endlevel() >= level:
            self.setVisible(True)
        self._current_map_level = level
        return

    def set_mp_data(self):
        for given_level in ('Data0', 'Data1', 'Data2', 'Data3', 'Data4'):
            data = self.get_datax(given_level)
            if not data:
                continue
            level = int(given_level[-1])
            node = data[0]
            x, y = node[0].get_canvas_coords()
            self._mp_data[level] = QPointF(x, y)
            if self.pos().isNull():
                self.setPos(self._mp_data[level])
                self.current_data_x = level

    def add_label(self):
        label = self.get_label1()
        if label is not None and label:
            self._mp_label = label
            self.setText(label)

    def set_brush(self):
        pass

    def decorate(self):
        pass

    def undecorate(self):
        pass



class PolyQGraphicsPathItem(BasicMapItem, QGraphicsPathItem):
    # basic class for Polyline and Polygon, for presentation on maps
    selected_pen = QPen(QColor("red"))
    selected_pen.setCosmetic(True)
    selected_pen.setStyle(Qt.DotLine)
    selected_pen.setWidth(4)
    hovered_over_pen = QPen(QColor('red'))
    hovered_over_pen.setWidth(1)
    hovered_over_pen.setCosmetic(True)
    non_cosmetic_multiplicity = 2
    _threshold = None
    _accept_map_level_change = True

    def __init__(self, map_objects_properties=None, projection=None):
        self.hovered = False
        # super(PolyQGraphicsPathItem, self).__init__(map_objects_properties=map_objects_properties,
        #                                             projection=projection)
        BasicMapItem.__init__(self, map_objects_properties=map_objects_properties, projection=projection)
        QGraphicsPathItem.__init__(self)
        self.orig_pen = None
        self.node_grip_items = list()
        self.node_grip_hovered = False
        self.hovered_shape_id = None
        self.label = None
        self._mp_data = [None, None, None, None, None]
        # self._mp_end_level = 0
        self._mp_label = None
        self.current_data_x = 0

    def _shape(self):
        stroker = QPainterPathStroker()
        if self.hovered_shape_id is not None:
            stroker.setWidth(self.hovered_shape_id.pen().width() * self.non_cosmetic_multiplicity)
        else:
            stroker.setWidth(self.pen().width() * self.non_cosmetic_multiplicity)
        return stroker.createStroke(self.path())

    @staticmethod
    def accept_map_level_change():
        return True

    def highlight_when_hoverover(self):
        if self.scene().get_viewer_scale() * 10 < IGNORE_TRANSFORMATION_TRESHOLD:
            return False
        return True

    @staticmethod
    def create_painter_path(poly_lists, type_polygon=False):
        path = QPainterPath()
        for poly in poly_lists:
            if type_polygon and poly[0] != poly[-1]:
                poly.append(poly[0])
            qpp = QPainterPath()
            qpp.addPolygon(QPolygonF(poly))
            path.addPath(qpp)
        return path

    @staticmethod
    def get_polygons_from_path(path, type_polygon=False):
        polygons = []
        for poly in path.toSubpathPolygons():
            # kopiuje wspolrzedne punktow esplicite, bo przez jakas referencje qpointf z path sie zmienialy
            poly_coords = [QPointF(p.x(), p.y()) for p in tuple(poly)]
            if type_polygon and poly.isClosed():
                poly_coords.pop()
            polygons.append(poly_coords)
        return polygons

    def set_map_level(self):
        level = self.scene().get_map_level()
        # lets save the current path in case it's changed
        self._mp_data[self.current_data_x] = self.path()
        if self._mp_data[level] is not None:
            self.remove_items_before_new_map_level_set()
            self.setPath(self._mp_data[level])
            self.add_items_after_new_map_level_set()
            self.setVisible(True)
            self.current_data_x = level
        elif self.get_endlevel() < level:
            if self.isVisible():
                self.setVisible(False)
        else:
            if any(self._mp_data[a] is not None for a in range(level)):
                if not self.isVisible():
                    self.setVisible(True)
            else:
                if self.isVisible():
                    self.setVisible(False)
        return

    def remove_items_before_new_map_level_set(self):
        return

    def add_items_after_new_map_level_set(self):
        return

    def set_mp_data(self, level, data):
        # to be defined separately for polygon and polyline
        pass

    def add_label(self):
        pass

    def remove_label(self):
        if self.label is not None:
            self.scene().removeItem(self.label)
        self.label = None

    def _move_grip(self, grip, type_polygon=False):
        print('ruszam')
        if grip not in self.node_grip_items:
            return
        polygons = self.get_polygons_from_path(self.path(), type_polygon=type_polygon)
        grip_poly_num, grip_coord_num = grip.grip_indexes
        try:
            polygons[grip_poly_num][grip_coord_num] = grip.pos()
        except IndexError:
            return
        self.setPath(self.create_painter_path(polygons, type_polygon=type_polygon))
        self.refresh_arrow_heads()
        self.update_label_pos()
        self.update_hlevel_labels()

    def move_grip(self, grip):
        # do be defined in child classes
        return

    def remove_grip(self, grip):
        # to be redefined in subclasses
        return

    def paint(self, painter, option, widget=None):
        if option.state & QStyle.State_Selected or self.node_grip_items:
            self.setPen(self.selected_pen)
        elif self.hovered and not self.node_grip_items:
            self.setPen(self.hovered_over_pen)
        else:
            self.setPen(self.orig_pen)
        super().paint(painter, option, widget=widget)

    def setPen(self, pen):
        if self.orig_pen is None:
            self.orig_pen = pen
        super().setPen(pen)

    def _decorate(self, type_polygon=False):
        print('dekoruje polygon', 'type_polygon', type_polygon)
        if self.node_grip_items:
            self.undecorate()
        self.setZValue(self.zValue() + 100)
        # elapsed = datetime.now()
        # polygons = self.path().toSubpathPolygons()
        polygons = self.get_polygons_from_path(self.path(), type_polygon=type_polygon)
        for polygon_num, polygon in enumerate(polygons):
            # elapsed = datetime.now()
            for polygon_node_num, polygon_node in enumerate(polygon):
                square = GripItem(polygon_node, (polygon_num, polygon_node_num,),
                                  self.get_hlevel_for_node(polygon_node_num), self)
                self.node_grip_items.append(square)
            # else:
            #     self.node_grip_items.append(None)
        self.setFlags(QGraphicsItem.ItemIsSelectable)

    def decorate(self):
        # to be redefined in polyline and polygon classes
        return

    def undecorate(self):
        print('usuwam dekoracje, %s punktow' % len(self.node_grip_items))
        self.setZValue(self.zValue() - 100)
        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable)
        scene = self.scene()
        for grip_item in self.node_grip_items:
            if grip_item is not None:
                scene.removeItem(grip_item)
        self.node_grip_items = []
        self.hoverLeaveEvent(None)

    def _insert_point(self, index, pos, type_polygon=False):
        # index is always > 0, so the first element will always be moveTo
        path_num, coord_num = index
        polygons = self.get_polygons_from_path(self.path(), type_polygon=type_polygon)
        try:
            polygon = polygons[path_num]
            polygon_modified = polygon[:coord_num] + [pos] + polygon[coord_num:]
            polygons[path_num] = polygon_modified
        except IndexError:
            return
        self.undecorate()
        self.setPath(self.create_painter_path(polygons, type_polygon=type_polygon))
        self.decorate()

    # to be override in other classes
    def insert_point(self, index, pos, type_polygon=False):
        return

    def remove_point(self, grip, type_polygon=False):
        # if there are 2 grip items in a path, then removal is not possible do not even try
        # in another case decide later whether it is possible
        if len(self.node_grip_items) <= 2:
            return
        polygons = self.get_polygons_from_path(self.path(), type_polygon=type_polygon)
        grip_poly_num, grip_coord_num = grip.grip_indexes
        print('remove_point')
        print(grip_poly_num, grip_coord_num)
        try:
            polygons[grip_poly_num].pop(grip_coord_num)
        except IndexError:
            print('index error')
            return
        if not self.is_point_removal_possible(len(polygons[grip_poly_num])):
            return

        self.setPath(self.create_painter_path(polygons, type_polygon=type_polygon))
        # for grip_item in self.node_grip_items:
        #     if grip_item is not None:
        #         self.scene().removeItem(grip_item)
        # self.node_grip_items = []
        self.undecorate()
        self.decorate()
        self.refresh_arrow_heads()
        self.update_label_pos()
        self.remove_hlevel_labels(grip_coord_num)

    def _closest_point_to_poly(self, event_pos, type_polygon=False):
        """
            Get the position along the polyline/polygon sides that is the closest
                to the given point.
            Parameters
            ----------
            event_pos: event class position (event.pos)
            type_polygon: whether we have polygon (True) or polyline (False)

            Returns
            -------
            tuple(distance from edge, qpointf within polygon edge, insertion index) in case of succes and
            tuple(-1, qpoinf, -1) in case of failure
            """

        polygons = self.get_polygons_from_path(self.path(), type_polygon=False)
        intersections_for_separate_paths = list()
        for path_num, points in enumerate(polygons):
            # iterate through pair of points, if the polygon is not "closed",
            # add the start to the end
            p1 = points.pop(0)
            if type_polygon and points[-1] != p1:  # identical to QPolygonF.isClosed()
                points.append(p1)
            intersections = []
            for coord_index, p2 in enumerate(points, 1):
                line = QLineF(p1, p2)
                inters = QPointF()
                # create a perpendicular line that starts at the given pos
                perp = QLineF.fromPolar(self.threshold(), line.angle() + 90).translated(event_pos)
                if line.intersect(perp, inters) != QLineF.BoundedIntersection:
                    # no intersection, reverse the perpendicular line by 180°
                    perp.setAngle(perp.angle() + 180)
                    if line.intersect(perp, inters) != QLineF.BoundedIntersection:
                        # the pos is not within the line extent, ignore it
                        p1 = p2
                        continue
                # get the distance between the given pos and the found intersection
                # point, then add it, the intersection and the insertion index to
                # the intersection list
                intersections.append((QLineF(event_pos, inters).length(), inters, (path_num, coord_index,)))
                p1 = p2
            if intersections:
                intersections_for_separate_paths.append(min(intersections, key=lambda item: item[0]))

        if intersections_for_separate_paths:
            # return the result with the shortest distance
            return min(intersections_for_separate_paths, key=lambda item: item[0])
        return -1, QPointF(), (0, -1)

    def closest_point_to_poly(self, event_pos):
        # redefined in derived classes
        return -1, QPointF(), (0, -1)

    def threshold(self):
        if self._threshold is not None:
            return self._threshold
        return self.pen().width() or 1.

    def set_threshold(self, threshold):
        self._threshold = threshold

    @staticmethod
    def is_point_removal_possible(num_elems_in_path):
        return False

    def refresh_arrow_heads(self):
        return

    def update_label_pos(self):
        return

    def update_hlevel_labels(self):
        return

    def remove_hlevel_labels(self, node_num):
        return

    # mouse events
    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.remove_hovered_shape()
        if event.button() == Qt.LeftButton and event.modifiers() == Qt.ShiftModifier:
            dist, pos, index = self.closest_point_to_poly(event.pos())
            print(dist, pos, index)
            if index[1] >= 0 and dist <= self.threshold():
                self.insert_point(index, pos)
                return

    def hoverEnterEvent(self, event):
        # print('hoverEnter')
        if not self.highlight_when_hoverover():
            return
        if self.node_grip_items:
            self.setCursor(QCursor(Qt.CrossCursor))
            return
        self.hovered = True
        if not self.isSelected():
            self.add_hovered_shape()

    def hoverLeaveEvent(self, event):
        # print('hoverLeave')
        if self.node_grip_items:
            self.setCursor(QCursor(Qt.ArrowCursor))
            return
        self.hovered = False
        if not self.isSelected():
            self.setPen(self.orig_pen)
            self.remove_hovered_shape()

    # when shape is hovered over, then around the shape is formed. Let's create it.
    def add_hovered_shape(self):
        # elem_shape = self.shape()
        elem_shape = QPainterPath(self.path())
        self.hovered_shape_id = self.scene().addPath(elem_shape)
        self.hovered_shape_id.setPos(self.pos())
        self.hovered_shape_id.setZValue(self.zValue() - 1)
        hovered_color = QColor('red')
        hovered_color.setAlpha(50)
        hovered_over_pen = QPen(hovered_color)
        hovered_over_pen.setCosmetic(True)
        hovered_over_pen.setWidth(self.pen().width() + 2)
        self.hovered_shape_id.setPen(hovered_over_pen)
        self.setPen(self.hovered_over_pen)

    def remove_hovered_shape(self):
        if self.hovered_shape_id is not None:
            self.scene().removeItem(self.hovered_shape_id)
            self.hovered_shape_id = None

    def is_in_node_edit_mode(self):
        return True if self.node_grip_items else False

    def get_hlevel_for_node(self, node_num):
        return None

class PolylineQGraphicsPathItem(PolyQGraphicsPathItem):
    def __init__(self, map_objects_properties=None, projection=None):
        super(PolylineQGraphicsPathItem, self).__init__(map_objects_properties=map_objects_properties,
                                                        projection=projection)
        self.arrow_head_items = []
        self.hlevel_labels = None
        self._mp_hlevels = [None, None, None, None, None]
        self._mp_address_numbers = [None, None, None, None, None]
        self._mp_dir_indicator = False
        self.setZValue(10)
        self.setAcceptHoverEvents(True)
        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable)

    def set_mp_data(self):
        for given_level in ('Data0', 'Data1', 'Data2', 'Data3', 'Data4'):
            data = self.get_datax(given_level)
            if not data:
                continue
            level = int(given_level[-1])
            polylines_list = list()
            for nodes in data:
                polylines_list.append([node.get_canvas_coords_as_qpointf() for node in nodes])
            self._mp_data[level] = self.create_painter_path(polylines_list, type_polygon=False)
            if self.path().isEmpty():
                self.setPath(self._mp_data[level])
                self.current_data_x = level

    def set_mp_hlevels(self):
        for given_level in ('Data0', 'Data1', 'Data2', 'Data3', 'Data4'):
            data = self.get_hlevels(given_level)
            if not data:
                continue
            level = int(given_level[-1])
            self._mp_hlevels[level] = data

    def remove_items_before_new_map_level_set(self):
        if self.arrow_head_items is not None and self.arrow_head_items:
            self.remove_arrow_heads()
        if self.label is not None:
            self.remove_label()
        if self.hlevel_labels is not None and self.hlevel_labels:
            self.remove_all_hlevel_labels()

    def add_items_after_new_map_level_set(self):
        # print('add_items_after_new_map_level_set')
        if self._mp_dir_indicator:
            self.add_arrow_heads()
        self.add_label()
        self.add_hlevel_labels()

    def set_mp_dir_indicator(self, dir_indicator):
        self._mp_dir_indicator = dir_indicator
        if dir_indicator:
            self.add_arrow_heads()
        else:
            self.remove_arrow_heads()

    # redefine shape function from QGraphicsPathItem, to be used in hoverover etc.
    def shape(self):
        return self._shape()

    def add_arrow_heads(self):
        if not self._mp_dir_indicator:
            return
        # lets add arrowhead every second segment
        path = self.path()
        for elem_num in range(0, path.elementCount() - 1, 2):
            # QLineF could be used here, but due to the screen coordinates system, where y = -y, it is easier to
            # create custom function to angle calculation
            p1 = QPointF(path.elementAt(elem_num))
            p2 = QPointF(path.elementAt(elem_num + 1))
            position = p1 + (p2-p1) / 2
            self.arrow_head_items.append(DirectionArrowHead(position, self))
            angle = misc_functions.vector_angle(p2.x() - p1.x(), p2.y() - p1.y(),
                                                clockwise=True, screen_coord_system=True)
            self.arrow_head_items[-1].setRotation(angle)

    def remove_arrow_heads(self):
        for arrow_head in self.arrow_head_items:
            self.scene().removeItem(arrow_head)
        self.arrow_head_items = []

    def refresh_arrow_heads(self):
        if self.arrow_head_items:
            self.remove_arrow_heads()
            self.add_arrow_heads()

    def add_label(self):
        label = self.get_label1()
        if label is not None and label:
            self.label = PolylineLabel(label, self)

    def update_label_pos(self):
        if self.label is not None:
            self.label.setPos(self.label.get_label_pos())
            self.label.setRotation(self.label.get_label_angle())

    def add_hlevel_labels(self):
        # add hlevel numbers dependly on map level
        level = self.scene().get_map_level()
        if not self._mp_hlevels[level]:
            return
        if self.hlevel_labels is None:
            self.hlevel_labels = dict()
        path = self.path()
        for node_num_value in self._mp_hlevels[level]:
            node_num, value = node_num_value
            position = QPointF(path.elementAt(node_num))
            # print(position)
            self.hlevel_labels[node_num] = PolylineLevelNumber(str(value) + ' ' + str(node_num), self)
            self.hlevel_labels[node_num].setPos(position)

    def update_hlevel_labels(self):
        # update numbers positions when nodes are moved around
        self.remove_all_hlevel_labels()
        self.add_hlevel_labels()
        return
        print('moving numbers')
        if self.hlevel_labels is None:
            return
        path = self.path()
        for node_num in self.hlevel_labels:
            self.hlevel_labels[node_num].setPos(QPointF(path.elementAt(node_num)))

    def remove_hlevel_labels(self, node_num):
        # remove hlevels labels when node is removed
        if self.hlevel_labels is None:
            return
        if node_num not in self.hlevel_labels:
            return
        self.scene().removeItem(self.hlevel_labels[node_num])
        del self.hlevel_labels[node_num]
        if not self.hlevel_labels:
            self.hlevel_labels = None
        self.update_hlevel_labels()

    def remove_all_hlevel_labels(self):
        # called when map level is changed, for a new maplevel we need to remove old hlevels
        for hl in tuple(self.hlevel_labels.keys()):
            self.scene().removeItem(self.hlevel_labels[hl])
            del self.hlevel_labels[hl]
        self.hlevel_labels = None

    def get_hlevel_for_node(self, node_num):
        if self.hlevel_labels is None:
            return None
        if node_num in self.hlevel_labels:
            return self.hlevel_labels[node_num].text()
        return None


    def closest_point_to_poly(self, event_pos):
        """
        Get the position along the polyline/polygon sides that is the closest
            to the given point.
        Parameters
        ----------
        event_pos: event class position (event.pos)

        Returns
        -------
        tuple(distance from edge, qpointf within polygon edge, insertion index) in case of succes and
        tuple(-1, qpoinf, -1) in case of failure
        """
        # polylines = self.get_polygons_from_path(self.path(), type_polygon=False)
        # return misc_functions.closest_point_to_poly(event_pos, polylines, self.threshold(), type_polygon=False)
        return self._closest_point_to_poly(event_pos, type_polygon=False)

    def decorate(self):
        self._decorate(type_polygon=False)

    def move_grip(self, grip):
        self._move_grip(grip, type_polygon=False)

    def remove_grip(self, grip):
        if grip in self.node_grip_items:
            self.remove_point(grip, type_polygon=False)

    def insert_point(self, index, pos):
        self._insert_point(index, pos, type_polygon=False)

    @staticmethod
    def is_point_removal_possible(num_elems_in_path):
        return num_elems_in_path >= 2


class PolygonQGraphicsPathItem(PolyQGraphicsPathItem):

    def __init__(self, map_objects_properties=None, projection=None):
        super(PolygonQGraphicsPathItem, self).__init__(map_objects_properties=map_objects_properties,
                                                       projection=projection)
        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable)
        self.setAcceptHoverEvents(True)

    def set_mp_data(self):
        for given_level in ('Data0', 'Data1', 'Data2', 'Data3', 'Data4'):
            data = self.get_datax(given_level)
            if not data:
                continue
            level = int(given_level[-1])
            nodes_qpointfs = list()
            for nodes in data:
                nodes_qpointfs.append([a.get_canvas_coords_as_qpointf() for a in nodes])
            self._mp_data[level] = self.create_painter_path(nodes_qpointfs, type_polygon=True)
            if self.path().isEmpty():
                self.setPath(self._mp_data[level])
                self.current_data_x = level

    def shape(self):
        if not self.node_grip_items:
            return super().shape()
        return self._shape()

    def remove_items_before_new_map_level_set(self):
        if self.label is not None:
            self.remove_label()

    def add_items_after_new_map_level_set(self):
        self.add_label()

    def decorate(self):
        self._decorate(type_polygon=True)

    def move_grip(self, grip):
        self._move_grip(grip, type_polygon=True)

    def remove_grip(self, grip):
        if grip in self.node_grip_items:
            self.remove_point(grip, type_polygon=True)

    @staticmethod
    def is_point_removal_possible(num_elems_in_path):
        return num_elems_in_path >= 3

    def add_label(self):
        label = self.get_label1()
        if label is not None and label:
            self.label = PolygonLabel(self._mp_label, self)

    def update_label_pos(self):
        if self.label is not None:
            self.label.setPos(self.label.get_label_pos())

    def closest_point_to_poly(self, event_pos):
        """
        Get the position along the polyline/polygon sides that is the closest
            to the given point.
        Parameters
        ----------
        event_pos: event class position (event.pos)

        Returns
        -------
        tuple(distance from edge, qpointf within polygon edge, insertion index) in case of succes and
        tuple(-1, qpoinf, -1) in case of failure
        """
        # polygons = self.get_polygons_from_path(self.path(), type_polygon=True)
        # return misc_functions.closest_point_to_poly(event_pos, polygons, self.threshold(), type_polygon=True)
        return self._closest_point_to_poly(event_pos, type_polygon=True)

    def insert_point(self, index, pos):
        self._insert_point(index, pos, type_polygon=True)


class MapLabels(QGraphicsSimpleTextItem):
    _accept_map_level_change = False
    def __init__(self, string_text, parent):
        super(MapLabels, self).__init__(string_text, parent)

    @staticmethod
    def accept_map_level_change():
        return False

    def paint(self, painter, option, widget):
        self.set_transformation_flag()
        super().paint(painter, option, widget)

    def set_transformation_flag(self):
        if self.scene().get_viewer_scale() > IGNORE_TRANSFORMATION_TRESHOLD:
            if not bool(self.flags() & QGraphicsItem.ItemIgnoresTransformations):
                self.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)
        else:
            if bool(self.flags() & QGraphicsItem.ItemIgnoresTransformations):
                self.setFlag(QGraphicsItem.ItemIgnoresTransformations, False)


class PoiLabel(MapLabels):

    def __init__(self, string_text, parent):
        self.parent = parent
        super(PoiLabel, self).__init__(string_text, parent)
        px0, py0, pheight, pwidth = parent.boundingRect().getRect()
        self.setPos(pheight, pwidth/2)
        self.setZValue(20)
        self.set_transformation_flag()


class PolylineLabel(MapLabels):

    def __init__(self, string_text, parent):
        self.parent = parent
        super(PolylineLabel, self).__init__(string_text, parent)
        self.setPos(self.get_label_pos())
        self.setRotation(self.get_label_angle())
        self.setZValue(20)
        self.set_transformation_flag()

    def get_label_angle(self):
        p1, p2 = self.get_label_nodes()
        angle = misc_functions.vector_angle(p2.x() - p1.x(), p2.y() - p1.y(), clockwise=True, screen_coord_system=True)
        return misc_functions.calculate_label_angle(angle)

    def get_label_pos(self):
        p1, p2 = self.get_label_nodes()
        return p1 + (p2-p1)/2

    def get_label_nodes(self):
        path = self.parent.path()
        num_elem = path.elementCount()
        if num_elem == 2:
            return QPointF(path.elementAt(0)), QPointF(path.elementAt(1))
        elif num_elem % 2 == 0:
            return QPointF(path.elementAt(num_elem // 2 - 1)), QPointF(path.elementAt(num_elem // 2))
        return QPointF(path.elementAt(num_elem // 2)), QPointF(path.elementAt(num_elem // 2 + 1))


class PolygonLabel(MapLabels):

    def __init__(self, string_text, parent):
        self.parent = parent
        super(PolygonLabel, self).__init__(string_text, parent)
        self.setPos(self.get_label_pos())
        self.setZValue(20)
        self.set_transformation_flag()

    def get_label_pos(self):
        return self.parent.boundingRect().center()

class PolylineAddressNumber(MapLabels):

    def __init__(self, text, parent):
        self.parent = parent
        super(PolylineAddressNumber, self).__init__(text, parent)
        self.set_transformation_flag()


class PolylineLevelNumber(MapLabels):

    def __init__(self, text, parent):
        self.parent = parent
        if not isinstance(text, str):
            text = str(text) + ' hlevel'
        super(PolylineLevelNumber, self).__init__(text, parent)
        self.set_transformation_flag()


class GripItem(QGraphicsPathItem):
    # https://stackoverflow.com/questions/77350670/how-to-insert-a-vertex-into-a-qgraphicspolygonitem
    _pen = QPen(QColor('green'), 2)
    #_pen.setCosmetic(True)
    _first_grip_pen = QPen(QColor('red'), 2)
    #_first_grip_pen.setCosmetic(True)
    inactive_brush = QBrush(QColor('green'))
    _first_grip_inactive_brush = QBrush(QColor('red'))
    square = QPainterPath()
    square.addRect(-2, -2, 4, 4)
    active_brush = QBrush(QColor('red'))
    _first_grip_active_brush = QBrush(QColor('green'))
    # keep the bounding rect consistent
    _boundingRect = square.boundingRect()
    _accept_map_level_change = False

    def __init__(self, pos, grip_indexes, hlevel, parent):
        super().__init__()
        self.grip_indexes = grip_indexes
        self.parent = parent
        self.hlevel = hlevel
        self.setPos(pos)
        self.setParentItem(parent)
        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable
                      | QGraphicsItem.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setPath(self.square)
        if self.is_first_grip():
            self.setPen(self._first_grip_pen)
        else:
            self.setPen(self._pen)
        self.setZValue(100)
        self._setHover(False)
        self.hover_drag_mode = False
        self.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)
        # self.set_transformation_flag()
        _text = str(self.grip_indexes)
        if self.hlevel is not None:
            _text = _text + ' ' + str(self.hlevel)
        text = QGraphicsSimpleTextItem(_text, self)
        text.setPos(1, 1)

        # self.setAttribute(Qt.WA_NoMousePropagation, False)

    def is_first_grip(self):
        return self.grip_indexes[1] == 0

    def accept_map_level_change(self):
        return False

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            self.parent.move_grip(self)
        return super().itemChange(change, value)

    def _setHover(self, hover):
        if hover:
            if self.is_first_grip():
                self.setBrush(self._first_grip_active_brush)
            else:
                self.setBrush(self.active_brush)
            self.hover_drag_mode = True
        else:
            if self.is_first_grip():
                self.setBrush(self._first_grip_inactive_brush)
            else:
                self.setBrush(self.inactive_brush)
            self.hover_drag_mode = False

    def boundingRect(self):
        return self._boundingRect

    def hoverEnterEvent(self, event):
        super().hoverEnterEvent(event)
        self._setHover(True)

    def hoverLeaveEvent(self, event):
        super().hoverLeaveEvent(event)
        self._setHover(False)

    def mousePressEvent(self, event):
        if (event.button() == Qt.LeftButton and event.modifiers() == Qt.ControlModifier):
            self.parent.remove_grip(self)
        elif (event.button() == Qt.LeftButton and event.modifiers() == Qt.ShiftModifier):
            print('z shifterm')
        else:
            super().mousePressEvent(event)

    def wheelEvent(self, event):
        print('kolko myszy')
        if event.modifiers() == Qt.ControlModifier:
            pass
        else:
            super().wheelEvent(event)

    def paint(self, painter, option, widget=None):
        # self.set_transformation_flag()
        super().paint(painter, option, widget=widget)

    def set_transformation_flag(self):
        if self.scene().get_viewer_scale() > IGNORE_TRANSFORMATION_TRESHOLD:
            if not bool(self.flags() & QGraphicsItem.ItemIgnoresTransformations):
                self.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)
        else:
            if bool(self.flags() & QGraphicsItem.ItemIgnoresTransformations):
                self.setFlag(QGraphicsItem.ItemIgnoresTransformations, False)

    def decorate(self):
        # simulate decorate, we can do it here, or design in future what to do
        pass

    def undecorate(self):
        # simulate undecorate, we can do it here, or design in future what to do
        pass

class DirectionArrowHead(QGraphicsPathItem):
    pen = QPen(Qt.black, 1)
    brush = QBrush(Qt.black)
    # pen.setCosmetic(True)
    _accept_map_level_change = False

    def __init__(self, pos, parent):
        super().__init__()
        self.parent = parent
        self.setPos(pos)
        self.setParentItem(parent)
        arrow_head = QPainterPath()
        arrow_head.moveTo(QPointF(-6, 4))
        arrow_head.lineTo(QPointF(6, 0))
        arrow_head.lineTo(QPointF(-6, -4))
        self.setPath(arrow_head)
        self.setPen(self.pen)
        self.setBrush(self.brush)
        self.setZValue(30)
        # by default lets ignore transformations, as this helps when moving nodes. The arrow heads keep their size
        self.set_transformation_flag()

    @staticmethod
    def accept_map_level_change():
        return False

    def set_transformation_flag(self):
        if self.scene().get_viewer_scale() > IGNORE_TRANSFORMATION_TRESHOLD:
            if not bool(self.flags() & QGraphicsItem.ItemIgnoresTransformations):
                self.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)
        else:
            if bool(self.flags() & QGraphicsItem.ItemIgnoresTransformations):
                self.setFlag(QGraphicsItem.ItemIgnoresTransformations, False)

    def paint(self, painter, option, widget=None):
        self.set_transformation_flag()
        super().paint(painter, option, widget=widget)


class MapRulerLabel(QGraphicsSimpleTextItem):
    _accept_map_level_change = False
    def __init__(self, label, parent):
        self.parent = parent
        super(MapRulerLabel, self).__init__(label, parent)

    @staticmethod
    def accept_map_level_change():
        return False


class MapRuler(QGraphicsPathItem):
    pen = QPen(Qt.black, 2)
    pen.setCosmetic(True)
    brush = QBrush(Qt.black)
    ruler = QPainterPath()
    screen_coord_1 = QPoint(10, 10)
    screen_coord_2 = QPoint(50, 10)
    _accept_map_level_change = False

    def __init__(self,  map_render, projection):
        self.map_render = map_render
        self.projection = projection
        super().__init__()
        self.geo_distance = None
        self.distance_label = None
        self.draw_ruler()
        self.screen_dpi = self.map_render.physicalDpiX()
        print('Screen dpi: ', self.screen_dpi)

    @staticmethod
    def accept_map_level_change():
        return False

    def draw_ruler(self):
        if self.distance_label is not None:
            self.remove_distance_label()
        point1 = self.map_render.mapToScene(self.screen_coord_1)
        point2 = self.map_render.mapToScene(self.screen_coord_2)
        self.calculate_geo_distance()
        # x = point1.x()
        # y_mod = point1.y() * 0.9
        # y = point1.y()
        ruler = QPainterPath()
        ruler.moveTo(point1)
        ruler.lineTo(point2)
        # for ruler_segment in range(4):
        #     ruler.lineTo(x + ruler_length * ruler_segment, y)
        #     ruler.lineTo(x + ruler_length * ruler_segment, y_mod)
        #     ruler.moveTo(x + ruler_length * ruler_segment, y)
        # print(self.map_render.mapFromScene(self.pos()))
        # self.setPos(point1)
        self.setPath(ruler)
        self.setPen(self.pen)
        self.setBrush(self.brush)
        self.setZValue(50)
        self.add_distance_label(point1)

    def add_distance_label(self, point1):
        if self.geo_distance < 1000:
            label = '%.1f m' % self.geo_distance
        else:
            label = '%.1f km' % (self.geo_distance / 1000)
        # print(self.geo_distance / (40 / self.map_render.physicalDpiX() * 2.54 / 100))
        self.distance_label = MapRulerLabel(label, self)
        self.distance_label.setPos(point1)
        self.distance_label.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)

    def remove_distance_label(self):
        self.scene().removeItem(self.distance_label)
        self.distance_label = None

    def move_to(self):
        self.draw_ruler()

    def scale_to(self):
        self.geo_distance = None
        self.draw_ruler()

    def calculate_geo_distance(self):
        if self.geo_distance is not None:
            return
        point1 = self.map_render.mapToScene(self.screen_coord_1)
        point2 = self.map_render.mapToScene(self.screen_coord_2)
        start_point = self.projection.canvas_to_geo(point1.x(), point1.y())
        end_point = self.projection.canvas_to_geo(point2.x(), point2.y())
        # end_point1 = self.projection.canvas_to_geo(point1.x() + 1, point1.y())
        self.geo_distance = misc_functions.vincenty_distance(start_point, end_point)
        # print(misc_functions.vincenty_distance(start_point, end_point1))

    def get_map_scale(self):
        self.calculate_geo_distance()
        return self.geo_distance / (40 / self.map_render.physicalDpiX() * 2.54 / 100)


class PolygonAnnotation(QGraphicsPolygonItem):
    # https://stackoverflow.com/questions/77350670/how-to-insert-a-vertex-into-a-qgraphicspolygonitem
    _threshold = None
    _pen = QPen(QColor("green"), 2)
    normalBrush = QBrush(Qt.NoBrush)
    hoverBrush = QBrush(QColor(255, 0, 0, 100))

    def __init__(self, *args):
        super().__init__()
        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable
                      | QGraphicsItem.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setPen(self._pen)
        self.gripItems = []
        if len(args) == 1:
            arg = args[0]
            if isinstance(arg, QPolygonF):
                self.setPolygon(arg)
            if isinstance(arg, (tuple, list)):
                args = arg
        if all(isinstance(p, QPointF) for p in args):
            self.setPolygon(QPolygonF(args))

    def threshold(self):
        if self._threshold is not None:
            return self._threshold
        return self.pen().width() or 1.

    def setThreshold(self, threshold):
        self._threshold = threshold

    def setPolygon(self, poly):
        if self.polygon() == poly:
            return
        if self.gripItems:
            scene = self.scene()
            while self.gripItems:
                grip = self.gripItems.pop()
                if scene:
                    scene.removeItem(grip)

        super().setPolygon(poly)
        for i, p in enumerate(poly):
            self.gripItems.append(GripItem(p, None, self))

    def addPoint(self, pos):
        self.insertPoint(len(self.gripItems), pos)

    def insertPoint(self, index, pos):
        poly = list(self.polygon())
        poly.insert(index, pos)
        self.gripItems.insert(index, GripItem(pos, None, self))
        # just call the base implementation, not the override, as all required
        # items are already in place
        super().setPolygon(QPolygonF(poly))

    def removePoint(self, index):
        if len(self.gripItems) <= 3:
            # a real polygon always has at least three vertexes,
            # otherwise it would be a line or a point
            return
        poly = list(self.polygon())
        poly.pop(index)
        grip = self.gripItems.pop(index)
        if self.scene():
            self.scene().removeItem(grip)
        # call the base implementation, as in insertPoint()
        super().setPolygon(QPolygonF(poly))

    def closestPointToPoly(self, pos):
        """
            Get the position along the polygon sides that is the closest
            to the given point.
            Returns:
            - distance from the edge
            - QPointF within the polygon edge
            - insertion index
            If no closest point is found, distance and index are -1
        """
        poly = self.polygon()
        points = list(poly)

        # iterate through pair of points, if the polygon is not "closed",
        # add the start to the end
        p1 = points.pop(0)
        if points[-1] != p1: # identical to QPolygonF.isClosed()
            points.append(p1)
        intersections = []
        for i, p2 in enumerate(points, 1):
            line = QLineF(p1, p2)
            inters = QPointF()
            # create a perpendicular line that starts at the given pos
            perp = QLineF.fromPolar(
                self.threshold(), line.angle() + 90).translated(pos)
            if line.intersects(perp, inters) != QLineF.BoundedIntersection:
                # no intersection, reverse the perpendicular line by 180°
                perp.setAngle(perp.angle() + 180)
                if line.intersects(perp, inters) != QLineF.BoundedIntersection:
                    # the pos is not within the line extent, ignore it
                    p1 = p2
                    continue
            # get the distance between the given pos and the found intersection
            # point, then add it, the intersection and the insertion index to
            # the intersection list
            intersections.append((QLineF(pos, inters).length(), inters, i))
            p1 = p2

        if intersections:
            # return the result with the shortest distance
            return sorted(intersections)[0]
        return -1, QPointF(), -1

    def gripMoved(self, grip):
        if grip in self.gripItems:
            poly = list(self.polygon())
            poly[self.gripItems.index(grip)] = grip.pos()
            super().setPolygon(QPolygonF(poly))

    def removeGrip(self, grip):
        if grip in self.gripItems:
            self.removePoint(self.gripItems.index(grip))

    def hoverEnterEvent(self, event):
        super().hoverEnterEvent(event)
        self.setBrush(self.hoverBrush)

    def hoverLeaveEvent(self, event):
        super().hoverLeaveEvent(event)
        self.setBrush(self.normalBrush)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and event.modifiers() == Qt.ShiftModifier:
            dist, pos, index = self.closestPointToPoly(event.pos())
            if index >= 0 and dist <= self.threshold():
                self.insertPoint(index, pos)
                return
        super().mousePressEvent(event)
