import time
from collections import OrderedDict, namedtuple
import misc_functions
import copy
# from singleton_store import Store
# from PyQt5.QtSvg import QGraphicsSvgItem
from PyQt5.QtWidgets import QGraphicsItemGroup
from PyQt5.QtWidgets import QGraphicsPixmapItem, QGraphicsRectItem, QGraphicsPathItem, QGraphicsItem, \
    QGraphicsPolygonItem, QStyle, QGraphicsSimpleTextItem, QGraphicsEllipseItem
from PyQt5.QtCore import QPointF, Qt, QLineF, QPoint
from PyQt5.QtGui import QPainterPath, QPolygonF, QBrush, QPen, QColor, QPainterPathStroker, QCursor, QVector2D, QFont
from datetime import datetime
from pwmapedit_constants import IGNORE_TRANSFORMATION_TRESHOLD
import commands
import itertools

Numbers_Definition = namedtuple('Numbers_Definition',
                                ['left_side_numbering_style',
                                 'left_side_number_before', 'left_side_number_after', 'right_side_numbering_style',
                                 'right_side_number_before', 'right_side_number_after', 'left_side_zip_code',
                                 'right_side_zip_code', 'left_side_city', 'left_side_region', 'left_side_country',
                                 'right_side_city', 'right_side_region', 'right_side_country']
                                )

Number_Index = namedtuple('Number_Index', ['data_level', 'data_num', 'index_of_point_in_the_polyline'])
Interpolated_Number = namedtuple('Interpolated_Number', ['vector', 'position', 'number'])


class Node(QPointF):
    """Class used for storing coordinates of given map object point"""
    def __init__(self, latitude=None, longitude=None, x=None, y=None, projection=None):
        # self.acuracy = 10000
        self.projection = None
        if projection is not None:
            self.projection = projection
        if latitude is not None and longitude is not None:
            _x, _y = self.projection.geo_to_canvas(latitude, longitude)
        elif x is not None and y is not None:
            _x = x
            _y = y
        self._numbers_definitions = None
        self._hlevel_definition = None
        super(Node, self).__init__(_x, _y)

    # def set_coordinates(self, latitude, longitude):
    #     self.longitude = longitude
    #     self.latitude = latitude

    def clear_numbers_definiton(self):
        self._numbers_definitions = None

    def copy(self):
        aaa = Node(x=self.x(), y=self.y(), projection=self.projection)
        if self._numbers_definitions is not None:
            aaa.set_numbers_definition(copy.copy(self._numbers_definitions))
        if self._hlevel_definition is not None:
            aaa.set_hlevel_definition(copy.copy(self._hlevel_definition))
        return aaa

    def get_numbers_definition(self):
        return self._numbers_definitions

    def get_specific_number_definition(self, fieldname):
        return self._numbers_definitions._asdict()[fieldname]


    def get_hlevel_definition(self):
        return self._hlevel_definition

    def get_geo_coordinates(self):
        return self.projection.geo_to_canvas(self.x(), self.y())

    def get_canvas_coords(self):
        return self.x(), self.y()
        return self.projection.geo_to_canvas(self.latitude, self.longitude)

    def get_canvas_coords_as_qpointf(self):
        return self
        return QPointF(self.x(), self.y())

    def node_starts_numeration(self):
        if self._numbers_definitions is None:
            return False
        if self._numbers_definitions.left_side_number_after is not None or \
                self._numbers_definitions.right_side_number_after is not None:
            return True
        return False

    def node_ends_numeration(self):
        if self._numbers_definitions is None:
            return False
        if self._numbers_definitions.left_side_number_before is not None or \
                self._numbers_definitions.right_side_number_before is not None:
            return True
        return False

    def node_has_numeration(self):
        if self._numbers_definitions is None:
            return False
        if self.node_starts_numeration() or self.node_ends_numeration():
            return True
        return False

    def __str__(self):
        return str(self._numbers_definitions)

    def set_coordinates_from_qpointf(self, position):
        self.setX(position.x())
        self.setY(position.y())

    def set_hlevel_definition(self, definition):
        self._hlevel_definition = definition

    def set_node_has_no_hlevel(self):
        self._hlevel_definition = None

    def set_node_has_no_numeration(self):
        self._numbers_definitions = None

    def set_numbers_definition(self, definition):
        self._numbers_definitions = definition

    def set_numbers_definition_field_name(self, field_name, definition):
        if self._numbers_definitions is None:
            self._numbers_definitions = Numbers_Definition(*[None for a in range(14)])
        definitions = self._numbers_definitions._asdict()
        definitions[field_name] = definition
        self._numbers_definitions = Numbers_Definition(**definitions)

    def update_numbers_after_poly_reversing(self):
        if self._numbers_definitions is None:
            return
        new_defs = {}
        for key, value in self._numbers_definitions._asdict().items():
            if key.startswith('right'):
                key = key.replace('right', 'left')
            elif key.startswith('left'):
                key = key.replace('left', 'right')
            if key.endswith('before'):
                key = key.replace('before', 'after')
            elif key.endswith('after'):
                key = key.replace('after', 'before')
            new_defs[key] = value
        self._numbers_definitions = Numbers_Definition(**new_defs)


class Data_X(object):
    def __init__(self, projection=None):
        self.projection = projection
        # dane mozna by przechowywac w slownikach, ale poniewaz jest ich duzo, dlatego pod wzgledem przechowywania
        # uzycie list bedzie sporo bardziej efektywne pod wzgledem wielkosci pamieci. Jako ze mapy moga byc duze, moze
        # miec to znaczenia.

        # Data0, Data1, Data2, Data3, Data4...
        # przechowuje informacje pod ktorym indeksem jest przechowywana jaki level
        self._data_levels = []
        # przechowuje wspolrzedne punktow dla Data0, Data1, Data2 ..., w postaci listy list. Pierwsza lista to
        # dany Data, druga lista w tej liscie, to dany polyline, albo polygon jako klasa Node
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

        # definicje numeracji, odkąd numeracja jest w nodach, zbędne
        # self._numbers_definitions = None

    def add_hlevels_from_string(self, hlevels_definition):
        for hlevel_def in hlevels_definition.lstrip('(').rstrip(')').split('),('):
            node_num, level_val = hlevel_def.split(',')
            self.add_hlevel_to_node_from_string(int(node_num), int(level_val))

    def add_hlevel_to_node_from_string(self, node_num, level_val):
        # dodawanie podczas wczytywania pliku
        data_level = self._last_data_level
        poly_num = self._last_poly_data_index
        self.set_hlevel_to_node(data_level, poly_num, node_num, level_val)

    def add_housenumbers_from_string(self, num_string):
        data_level, poly_num = self.get_last_data_level_and_last_index()
        if '=' in num_string:
            _, definition = num_string.split('=', 1)
        else:
            definition = num_string
        self.add_housenumbers_to_node(data_level, poly_num, definition)

    def add_housenumbers_to_node(self, data_level, poly_num, definition):
        """
        Parameters
        ----------
        data_level: int, 0, 1, 2, 3, 4, odpowiada Data0, Data1, Data2, Data3, Data4
        poly_num: int, 0, 1, 2, 3, 4..., kolejny numer polyline/polygon
        definition: string: definicja Numbers w pliku mp
        Returns: None
        -------
        """
        num_data = definition.split(',')
        node_num = int(num_data[0])
        left_style = num_data[1]
        left_start = int(num_data[2]) if left_style != 'N' else None
        left_end = int(num_data[3]) if left_style != 'N' else None
        right_style = num_data[4]
        right_start = int(num_data[5]) if right_style != 'N' else None
        right_end = int(num_data[6]) if right_style != 'N' else None

        self._poly_data_points[data_level][poly_num][node_num].set_numbers_definition_field_name('left_side_numbering_style', left_style)
        self._poly_data_points[data_level][poly_num][node_num].set_numbers_definition_field_name('left_side_number_after', left_start)
        self._poly_data_points[data_level][poly_num][node_num].set_numbers_definition_field_name('right_side_numbering_style', right_style)
        self._poly_data_points[data_level][poly_num][node_num].set_numbers_definition_field_name('right_side_number_after', right_start)
        last_node_def = self._poly_data_points[data_level][poly_num][-1].get_numbers_definition()

        if last_node_def is not None:
            self._poly_data_points[data_level][poly_num][node_num].set_numbers_definition_field_name('left_side_number_before', last_node_def.left_side_number_before)
            self._poly_data_points[data_level][poly_num][node_num].set_numbers_definition_field_name('right_side_number_before', last_node_def.right_side_number_before)
            self._poly_data_points[data_level][poly_num][-1].set_node_has_no_numeration()

        if left_start is not None or right_start is not None:
            self._poly_data_points[data_level][poly_num][-1].set_numbers_definition_field_name('left_side_number_before', left_end)
            self._poly_data_points[data_level][poly_num][-1].set_numbers_definition_field_name('right_side_number_before', right_end)

    def add_nodes_from_string(self, data_level, data_string):
        _data_level = int(data_level[4:])
        if _data_level not in self._data_levels:
            self._data_levels.append(_data_level)
            self._poly_data_points.append([])
        data_index = self._data_levels.index(_data_level)
        self._poly_data_points[data_index].append(self.coords_from_data_to_nodes(data_string))
        self._last_data_level = _data_level
        self._last_poly_data_index = len(self._poly_data_points[data_index]) - 1

    def coords_from_data_to_nodes(self, data_line):
        coords = []
        coordlist = data_line.strip().lstrip('(').rstrip(')')
        for a in coordlist.split('),('):
            latitude, longitude = a.split(',')
            self.set_obj_bounding_box(float(latitude), float(longitude))
            coords.append(Node(latitude=latitude, longitude=longitude, projection=self.projection))
        return coords

    def copy(self):
        d_copy = Data_X(self.projection)
        d_copy._bounding_box_N = self._bounding_box_N
        d_copy._bounding_box_S = self._bounding_box_S
        d_copy.bounding_box_W = self._bounding_box_W
        d_copy._bounding_box_E = self._bounding_box_E
        d_copy._data_levels = copy.copy(self._data_levels)
        d_copy._last_data_level = self._last_data_level
        d_copy._last_poly_data_index = self._last_poly_data_index
        d_copy._poly_data_points = list()
        # iterujemy po wszystkich data_level
        for dl_num in range(len(self._poly_data_points)):
            polys_points = []
            # iterujemy po polygonach dla danego data_level
            for poly in self._poly_data_points[dl_num]:
                polys_points.append([node.copy() for node in poly])
            d_copy._poly_data_points.append(polys_points)
        return d_copy


    def delete_node_at_position(self, data_level, polynum, index):
        # remove point
        del self._poly_data_points[data_level][polynum][index]
        self.clean_numbers_definitions(data_level, polynum)

    def clean_empty_numbers_definitions(self):
        for dl in self.get_data_levels():
            for poly in self.get_polys_for_data_level(dl):
                pass
            # do dokonczenia


    def clean_numbers_definitions(self, data_level, polynum):
         # update numbers definitions for nodes
        # na poczatek zerujemy ostatnie wezly, bo przed i po nie ma dla nich sensu
        # pierwszy nod
        if self._poly_data_points[data_level][polynum][0].node_has_numeration():
            for key in ('left_side_number_before', 'right_side_number_before'):
                self._poly_data_points[data_level][polynum][0].set_numbers_definition_field_name(key, None)
        # ostatni nod
        last_node = self._poly_data_points[data_level][polynum][-1]
        if last_node.node_has_numeration():
            for key in ('left_side_numbering_style', 'left_side_number_after', 'right_side_numbering_style',
                        'right_side_number_after', 'left_side_zip_code',
                        'right_side_zip_code', 'left_side_city', 'left_side_region', 'left_side_country',
                        'right_side_city', 'right_side_region', 'right_side_country'):
                last_node.set_numbers_definition_field_name(key, None)

        nodes_with_numbers = [a for a in self._poly_data_points[data_level][polynum] if a.node_has_numeration()]
        # nie ma zadnych w wezlow z numeracja, nie rob nic
        if len(nodes_with_numbers) == 0:
            return
        # mamy jeden wezel z numeracja, trzeba na ostatnim ustawic 0, o ile nie sa ustawione
        if len(nodes_with_numbers) == 1:
            last_node = self._poly_data_points[data_level][polynum][-1]
            if nodes_with_numbers[0].get_specific_number_definition('left_side_number_after') is None:
                last_node.set_numbers_definition_field_name('left_side_number_before', None)
            else:
                if last_node.get_specific_number_definition('left_side_number_before') is None:
                    last_node.set_numbers_definition_field_name('left_side_number_before', 0)
            if nodes_with_numbers[0].get_specific_number_definition('right_side_number_after') is None:
                last_node.set_numbers_definition_field_name('right_side_number_before', None)
            else:
                if last_node.get_specific_number_definition('right_side_number_before') is None:
                    last_node.set_numbers_definition_field_name('right_side_number_before', 0)
            return


        # jesli ostatni wezel nie ma ustawionej zadnej numeracji to ja ustaw, pomoze to porzadkowac wezly
        if not last_node.node_has_numeration():
            last_node.set_numbers_definition_field_name('left_side_number_before', 0)
            last_node.set_numbers_definition_field_name('right_side_number_before', 0)

        nodes_with_numbers = [a for a in self._poly_data_points[data_level][polynum] if a.node_has_numeration()]

        # mamy wiele wezlow z numeracja przeorganizuj je
        for node_num in range(len(nodes_with_numbers) - 1):
            node_start = nodes_with_numbers[node_num]
            node_end = nodes_with_numbers[node_num + 1]
            if node_start.node_starts_numeration():
                if node_start.get_specific_number_definition('left_side_number_after') is None:
                    node_end.set_numbers_definition_field_name('left_side_number_before', None)
                else:
                    if node_end.get_specific_number_definition('left_side_number_before') is None:
                        node_end.set_numbers_definition_field_name('left_side_number_before', 0)
                if node_start.get_specific_number_definition('right_side_number_after') is None:
                    node_end.set_numbers_definition_field_name('right_side_number_before', None)
                else:
                    if node_end.get_specific_number_definition('right_side_number_before') is None:
                        node_end.set_numbers_definition_field_name('right_side_number_before', 0)
            else:
                # przypadek gdy dany nod zaczyna dalej numeracje. wtedy numer przed nie będzie już potrzebny
                # jesli nod nie ma numeracji
                if node_end.node_has_numeration() and node_end.node_starts_numeration():
                    node_end.set_numbers_definition_field_name('left_side_number_before', None)
                    node_end.set_numbers_definition_field_name('right_side_number_before', None)
                else:
                    # jesli nod nie zaczyna numeracji wyzeruj jego numeracje
                    node_end.set_node_has_no_numeration()

        return

    def get_data_levels(self):
        return self._data_levels

    def get_data_level_index(self, data_level):
        if data_level in self._data_levels:
            return self._data_levels.index(data_level)

    def get_polys_for_data_level(self, data_level):
        if data_level not in self._data_levels:
            return tuple()
        data_level_index = self.get_data_level_index(data_level)
        return self._poly_data_points[data_level_index]

    def get_housenumbers_for_poly(self, data_level, poly_num):
        # zwraca definicje wszystkich numerow domow przypisanych do danego noda
        polys = self.get_polys_for_data_level(data_level)
        return [node.get_numbers_definition() for node in polys[poly_num]]

    def get_interpolated_housenumbers_for_poly(self, data_level, poly_num):
        interpolated_numbers = {'left': [], 'right': []}
        # house_numbers_defs = self.get_housenumbers_for_poly(data_level, poly_num)
        # # pozniej trzeba poruszac sie po nodzie z numerem i nodzie nastepnym, dlatego trzeba zbudowac liste
        # # indeksow numerow ktore zawieraja numeracje. Potem bedzie mozna sie posuwac o jeden w przod
        # nodes_with_nums_idx = [a for a in range(len(house_numbers_defs)) if house_numbers_defs[a] is not None]
        # if not [a for a in range(len(house_numbers_defs)) if house_numbers_defs[a] is not None]:
        #     return interpolated_numbers

        for pair in itertools.pairwise(self.get_nodes_with_housenumbers_indexes(data_level, poly_num)):
            start_node_idx, end_node_idx = pair
            node_with_num = self.get_poly_node(data_level, poly_num, start_node_idx, False)
            node_with_num_plus = self.get_poly_node(data_level, poly_num, end_node_idx, False)
            # create polyline elements as vectors
            poly_vectors = self.get_poly_vectors(data_level, poly_num, start_node_idx, end_node_idx)

            left_num_style = node_with_num.get_specific_number_definition('left_side_numbering_style')
            if left_num_style != 'N':
                left_num_start = node_with_num.get_specific_number_definition('left_side_number_after')
                left_num_end = node_with_num_plus.get_specific_number_definition('left_side_number_before')
                on_left = self.get_numbers_between(left_num_start, left_num_end, left_num_style)
                # poly vectors will be changed during get_interpolated_numbers_coordinates,
                # therefore we work on a copy: list(poly_vectors)
                interpolated_numbers['left'] += self.get_interpolated_numbers_coordinates(list(poly_vectors), on_left)

            right_num_style = node_with_num.get_specific_number_definition('right_side_numbering_style')
            if right_num_style != 'N':
                right_num_start = node_with_num.get_specific_number_definition('right_side_number_after')
                right_num_end = node_with_num_plus.get_specific_number_definition('right_side_number_before')
                on_right = self.get_numbers_between(right_num_start, right_num_end, right_num_style)
                # poly vectors will be changed during get_interpolated_numbers_coordinates,
                # therefore we work on a copy: list(poly_vectors)
                interpolated_numbers['right'] += self.get_interpolated_numbers_coordinates(list(poly_vectors), on_right)
        return interpolated_numbers

    @staticmethod
    def get_interpolated_numbers_coordinates(poly_vectors, numbers, current_num_distance=None,
                                             default_num_distance=None):
        if not numbers:
            return []
        if default_num_distance is None:
            all_polys_length = sum([p.length() for p in poly_vectors])
            default_num_distance = all_polys_length/(len(numbers) + 1)
        if current_num_distance is None:
            current_num_distance = default_num_distance
        poly_length = poly_vectors[0].length()
        if poly_length > current_num_distance:
            position = poly_vectors[0].pointAt(current_num_distance/poly_length)
            num = numbers.pop(0)
            if current_num_distance + default_num_distance <= poly_length:
                current_num_distance += default_num_distance
                vector = poly_vectors[0]
            else:
                current_num_distance = default_num_distance - (poly_length - current_num_distance)
                vector = poly_vectors.pop(0)
            return ([Interpolated_Number(vector, position, num)] +
                    Data_X.get_interpolated_numbers_coordinates(poly_vectors, numbers,
                                                                current_num_distance=current_num_distance,
                                                                default_num_distance=default_num_distance))
        elif poly_length == current_num_distance:
            position = poly_vectors[0].p2()
            vector = poly_vectors.pop(0)
            num = numbers.pop(0)
            current_num_distance = default_num_distance
            return ([Interpolated_Number(vector, position, num)] +
                    Data_X.get_interpolated_numbers_coordinates(poly_vectors, numbers,
                                                                current_num_distance=current_num_distance,
                                                                default_num_distance=default_num_distance))
        else:
            current_num_distance = current_num_distance - poly_length
            poly_vectors = poly_vectors[1:]
            return ([] + Data_X.get_interpolated_numbers_coordinates(poly_vectors, numbers,
                                                                     current_num_distance=current_num_distance,
                                                                     default_num_distance=default_num_distance))


    def get_nodes_with_housenumbers(self, data_level, poly_num):
        # zwraca nody dla ktory przypisana jest numeracja
        nodes_with_nums = []
        for node in  self.get_polys_for_data_level(data_level)[poly_num]:
            if node.node_has_numeration():
                nodes_with_nums.append(node)
        return nodes_with_nums

    def get_nodes_with_housenumbers_indexes(self, data_level, poly_num):
        # zwraca indeksy nodow z numerami,
        nodes_with_nums_indexes = []
        for node_idx, node in  enumerate(self.get_polys_for_data_level(data_level)[poly_num]):
            if node.node_has_numeration():
                nodes_with_nums_indexes.append(node_idx)
        return nodes_with_nums_indexes

    @staticmethod
    def get_numbers_between(start_point, end_point, num_style):
        if (start_point - end_point) in (-1, 0, 1):
            return []
        if start_point > end_point:
            step = -1
            start_point -= 1
        else:
            step = 1
            start_point += 1
        numbers = []
        for a in range(start_point, end_point, step):
            if num_style == 'E':
                if a % 2 == 0:
                    numbers.append(a)
            elif num_style == 'O':
                if a % 2 == 1:
                    numbers.append(a)
            else:
                numbers.append(a)
        return numbers

    def get_hlevels_for_poly(self, data_level, poly_num):
        polys = self.get_polys_for_data_level(data_level)
        return [node.get_hlevel_definition() for node in polys[poly_num]]

    def get_last_data_level_and_last_index(self):
        return self._last_data_level, self._last_poly_data_index

    def get_obj_bounding_box(self):
        return {'S': self._bounding_box_S, 'N': self._bounding_box_N, 'E': self._bounding_box_E,
                'W': self._bounding_box_E}

    def get_poly_node(self, data_level, poly_num, node_num, qpointsf):
        # zwraca nody dla konkretnego polygonu
        if data_level not in self._data_levels:
            return None
        data_list = self._poly_data_points[self._data_levels.index(data_level)]
        nodes_list = data_list[poly_num]
        if qpointsf:
            return nodes_list[node_num].get_canvas_coords_as_qpointf()
        return nodes_list[node_num]

    def get_poly_nodes(self, data_level, qpointsf):
        # zwraca nody dla wszystkich polygonow danego data_level
        if data_level not in self._data_levels:
            return None
        returned_data = list()
        for data_list in self._poly_data_points[self._data_levels.index(data_level)]:
            if qpointsf:
                returned_data.append([a.get_canvas_coords_as_qpointf() for a in data_list])
            else:
                returned_data.append(data_list)
        return returned_data

    def get_poly_vectors(self, data_level, poly_num, start_node_num, end_node_num):
        """
        generating polygon vectors for each path. Each path is split to separate polygons and then each polygon
        is converted to single vectors. In Poly class there is similar function, but those one creates
        vectors from path, it creates vectors for all path, not separate points.
        Parameters
        ----------
        data_level: int, data level
        poly_num: int, number of polygon
        start_node_num: int, start node number
        end_node_num: int, end node number

        Returns
        -------

        list: list of QLineF vectors

        """
        poly = self.get_polys_for_data_level(data_level)[poly_num]
        poly_vectors = list()
        for vector_num in range(start_node_num, end_node_num):
            x1 = poly[vector_num].x()
            y1 = poly[vector_num].y()
            x2 = poly[vector_num + 1].x()
            y2 = poly[vector_num + 1].y()
            poly_vectors.append(QLineF(x1, y1, x2, y2))
        return poly_vectors

    def insert_node_at_position(self, data_level, polynum, index, x, y):
        polygon = self._poly_data_points[data_level][polynum]
        polygon_mod = polygon[:index] + [Node(x=x, y=y, projection=self.projection)] + polygon[index:]
        self._poly_data_points[data_level][polynum] = polygon_mod

    def reverse_poly(self, data_level):
        # inverting order of nodes, which gives eg road oposite direction
        polys = self.get_polys_for_data_level(data_level)
        for poly_num in range(len(polys)):
            poly_copy = [a.copy() for a in (polys[poly_num])]
            polys[poly_num].reverse()
            for num in range(len(poly_copy)):
                polys[poly_num][-num - 1].set_node_has_no_hlevel()
                polys[poly_num][-num - 1].set_node_has_no_numeration()
                polys[poly_num][-num - 1].set_hlevel_definition(poly_copy[num].get_hlevel_definition())
                polys[poly_num][-num - 1].set_numbers_definition(poly_copy[num].get_numbers_definition())

            for node in self.get_nodes_with_housenumbers(data_level, poly_num):
                node.update_numbers_after_poly_reversing()

            for nodes_pair in itertools.pairwise(self.get_nodes_with_housenumbers(data_level, poly_num)):
                node_start, node_end = nodes_pair
                left_side_numbering_style = node_end.get_specific_number_definition('left_side_numbering_style')
                right_side_numbering_style = node_end.get_specific_number_definition('right_side_numbering_style')
                node_start.set_numbers_definition_field_name('left_side_numbering_style', left_side_numbering_style)
                node_start.set_numbers_definition_field_name('right_side_numbering_style', right_side_numbering_style)
            self.clean_numbers_definitions(data_level, poly_num)

    def set_hlevel_to_node(self, data_level, poly_num, node_num, level_val):
        dl_index = self.get_data_level_index(data_level)
        self._poly_data_points[dl_index][poly_num][node_num].set_hlevel_definition(level_val)

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

    def update_node_coordinates(self, data_level, polynum, index, position):
        """
        Ustaw wsplorzedne noda w poly
        Parameters
        ----------
        data_level: (int) 0, 1, 2, 3, 4, w zależności od Data
        polynum: (int) numer polygonu
        index: (int) indeks noda
        position: (QPointF), wspolrzedne jako QPointF

        Returns
        -------

        """
        polygon = self.get_polys_for_data_level(data_level)[polynum]
        polygon_nod = polygon[index]
        polygon_nod.set_coordinates_from_qpointf(position)

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
        self.last_data_level = None
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

    def coords_from_data_to_nodes(self, data_line):
        coords = []
        coordlist = data_line.strip().lstrip('(').rstrip(')')
        for a in coordlist.split('),('):
            latitude, longitude = a.split(',')
            self.set_obj_bounding_box(float(latitude), float(longitude))
            coords.append(Node(latitude=latitude, longitude=longitude, projection=self.projection))
        return coords

    def get_comment(self):
        return self.obj_comment

    def get_datax(self, dataX):
        # tymczasowo na potrzeby testow tylko jedno data
        # zwracamy liste Nodow, jesli
        data_level = int(dataX[4:])
        return self.data0.get_poly_nodes(data_level, False)

    # getters
    def get_dirindicator(self):
        if self.dirindicator is None:
            return False
        return self.dirindicator

    def get_endlevel(self):
        return self.endlevel

    def get_house_number(self):
        if self.housenumber is None:
            return ''
        return self.housenumber

    def get_housenumbers_along_road(self):
        return self.data0.get_housenumbers_nodes_defs()

    def get_label1(self):
        if self.label1 is not None:
            return self.label1
        return ''

    def get_label2(self):
        if self.label2 is not None:
            return self.label2
        return ''

    def get_label3(self):
        if self.label3 is not None:
            return self.label3
        return ''

    def get_others(self):
        return_val = list()
        for key_tuple, val in self.others.items():
            key = key_tuple[1]
            return_val.append((key, val,))
        return return_val

    def get_param(self, parameter):
        return getattr(self, parameter.lower())

    def get_phone_number(self):
        if self.phone is None:
            return ''
        return self.phone

    def get_street_desc(self):
        if self.streetdesc is None:
            return ''
        return self.streetdesc

    # setters

    def set_comment(self, _comments):
        for _comment in _comments:
            self.obj_comment.append(_comment)

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
                self.set_housenumbers_along_road(obj_data[number_keyname])
            elif number_keyname[1].startswith('HLevel'):
                self.set_hlevels(obj_data[number_keyname])
            # elif number_keyname[1] in ('Miasto', 'Typ', 'Plik'):
            #     # temporary remove these from reporting
            #     pass
            else:
                self.set_others(number_keyname, obj_data[number_keyname])
                # print('Unknown key value: %s.' % number_keyname[1])

    def set_datax(self, data012345, data012345_val):
        if self.data0 is None:
            self.data0 = Data_X(projection=self.projection)
        self.data0.add_nodes_from_string(data012345, data012345_val)
        self.set_obj_bounding_box(self.data0.get_obj_bounding_box())
        return

    def set_dirindicator(self, value):
        self.dirindicator = value

    def set_endlevel(self, value):
        if isinstance(value, str):
            value = int(value)
        self.endlevel = value

    def set_house_number(self, value):
        self.housenumber = value

    def set_housenumbers_along_road(self, numbers_definition):
        self.data0.add_housenumbers_from_string(numbers_definition)

    def set_label1(self, value):
        self.label1 = value

    def set_label2(self, value):
        self.label2 = value

    def set_label3(self, value):
        self.label3 = value

    def set_others(self, key, value):
        self.others[key] = value

    def set_param(self, parameter, value):
        setattr(self, parameter.lower(), value)
        # self.obj_data[parameter] = value

    def set_phone_number(self, value):
        self.phone = value

    def set_street_desc(self, value):
        self.streetdesc = value

    def set_obj_bounding_box(self, obj_bb):
        if not self.obj_bounding_box:
            self.obj_bounding_box['S'] = obj_bb['S']
            self.obj_bounding_box['N'] = obj_bb['N']
            self.obj_bounding_box['E'] = obj_bb['E']
            self.obj_bounding_box['W'] = obj_bb['W']
        else:
            self.obj_bounding_box['S'] = min(self.obj_bounding_box['S'], obj_bb['S'])
            self.obj_bounding_box['N'] = max(self.obj_bounding_box['N'], obj_bb['N'])
            self.obj_bounding_box['W'] = min(self.obj_bounding_box['W'], obj_bb['W'])
            self.obj_bounding_box['E'] = max(self.obj_bounding_box['E'], obj_bb['E'])

        return

    # niepotrzebne?
    def get_hlevels(self, level_for_data):
        # do redefinicji
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
        for hlevel_item in hlevel_items.lstrip('(').rstrip(')').split('),('):
            self.data0.add_hlevels_from_string(hlevel_item)
        return


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
        self.recorded_pos = None
        self.label = None
        self._mp_data = [None, None, None, None, None]
        # self._mp_end_level = 0
        self._mp_label = None
        # setting level 4, makes it easier to handle levels when file is loaded
        self._current_map_level = 4
        # self.icon = self.map_objects_properties.get_poi_icon(self.get_param('Type'))
        self.setZValue(20)
        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable)
        self.setAcceptHoverEvents(True)
        self.current_data_x = 4
        self.set_transformation_flag()
        self.hovered_shape = None

    @staticmethod
    def accept_map_level_change():
        return True

    def add_hovered_shape(self):
        self.hovered_shape = QGraphicsRectItem(*self.boundingRect().getRect(), self)
        hovered_color = QColor('red')
        # hovered_color.setAlpha(50)
        hovered_over_pen = QPen(hovered_color)
        hovered_over_pen.setCosmetic(True)
        hovered_over_pen.setWidth(1)
        self.hovered_shape.setPen(hovered_over_pen)

    def command_move_poi(self):
        command = commands.SelectModeMovePoi(self, 'Przesun POI', self.recorded_pos)
        self.scene().undo_redo_stack.push(command)

    def highlight_when_hoverover(self):
        if self.scene().get_viewer_scale() * 10 < IGNORE_TRANSFORMATION_TRESHOLD:
            return False
        return True

    def paint(self, painter, option, widget):
        self.set_transformation_flag()
        self.update()
        for child in self.childItems():
            child.update()
            # return
        super().paint(painter, option, widget)

    def set_transformation_flag(self):
        if self.scene() is None:
            return False
        if self.scene().get_viewer_scale() > IGNORE_TRANSFORMATION_TRESHOLD:
            if not bool(self.flags() & QGraphicsItem.ItemIgnoresTransformations):
                self.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)
                return True
        else:
            if bool(self.flags() & QGraphicsItem.ItemIgnoresTransformations):
                self.setFlag(QGraphicsItem.ItemIgnoresTransformations, False)
                return True
        return False

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

    def hoverEnterEvent(self, event):
        mode = self.scene().get_pw_mapedit_mode()
        if mode == 'select_objects' and not self.isSelected() and self.highlight_when_hoverover():
            self.add_hovered_shape()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.remove_hovered_shape()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        self.remove_hovered_shape()
        self.recorded_pos = self.pos()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self.pos() != self.recorded_pos:
            self.command_move_poi()
            self.recorded_pos = None
        super().mouseReleaseEvent(event)

    def remove_hovered_shape(self):
        if self.hovered_shape is not None:
            self.scene().removeItem(self.hovered_shape)
            self.hovered_shape = None

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
        if self.set_transformation_flag():
            self.update()
        super().paint(painter, option, widget)

    def set_transformation_flag(self):
        if self.scene() is None:
            return False
        if self.scene().get_viewer_scale() > IGNORE_TRANSFORMATION_TRESHOLD:
            if not bool(self.flags() & QGraphicsItem.ItemIgnoresTransformations):
                self.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)
                return True
        else:
            if bool(self.flags() & QGraphicsItem.ItemIgnoresTransformations):
                self.setFlag(QGraphicsItem.ItemIgnoresTransformations, False)
                return True
        return False

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


class HoveredShapePainterPath(QGraphicsPathItem):
    _accept_map_level_change = False

    def __init__(self, path):
        super(HoveredShapePainterPath, self).__init__(path)


class PolyQGraphicsPathItem(BasicMapItem, QGraphicsPathItem):
    # basic class for Polyline and Polygon, for presentation on maps
    decorated_z_value = 100
    closest_node_circle = QGraphicsEllipseItem(- 10, - 10, 20, 20)
    closest_node_circle.setZValue(150)
    closest_node_circle.setPen(QPen(QColor("blue")))
    closest_node_circle.setBrush(QBrush(QColor("blue")))
    closest_node_circle.setFlag(QGraphicsPathItem.ItemIgnoresTransformations, True)
    closest_node_circle.setOpacity(0.5)
    closest_node_min_distance = 15
    closest_node_circle_pen = QPen(QColor("blue"))
    closest_node_circle_brush = QBrush(QColor("blue"))
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
        self.decorated_poly_nums = None
        self.recorded_pos = None
        self._mouse_press_timestamp = None
        self._closest_node_circle = None
        self._drag_to_closest_node = False

    @staticmethod
    def accept_map_level_change():
        return True

    # when shape is hovered over, then around the shape is formed. Let's create it.
    def add_hovered_shape(self):
        # elem_shape = self.shape()
        self.hovered_shape_id = HoveredShapePainterPath(self.path())
        self.scene().addItem(self.hovered_shape_id)
        # self.hovered_shape_id.setPos(self.pos())
        self.hovered_shape_id.setZValue(self.zValue() - 1)
        hovered_color = QColor('red')
        # hovered_color.setAlpha(50)
        hovered_over_pen = QPen(hovered_color)
        hovered_over_pen.setCosmetic(True)
        hovered_over_pen.setWidth(self.pen().width() + 2)
        self.hovered_shape_id.setPen(hovered_over_pen)
        # self.hovered_shape_id.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)
        self.setPen(self.hovered_over_pen)
        self.hovered_shape_id.setParentItem(self)
        self.hovered_shape_id.setOpacity(0.3)

    def add_interpolated_housenumber_labels(self):
        return

    def add_items_after_new_map_level_set(self):
        return

    def add_label(self):
        pass

    def closest_point_to_point(self, event_pos):
        circle = QPainterPath()
        circle.addEllipse(event_pos, 30, 30)
        items_under_circle = self.scene().items(circle)
        if self in items_under_circle:
            items_under_circle.remove(self)
        items_under_circle = [a for a in items_under_circle if (isinstance(a, PolylineQGraphicsPathItem)
                                                                or isinstance(a, PolygonQGraphicsPathItem))]
        if items_under_circle:
            point_node_dist = []
            for item_under_c in items_under_circle:
                for polygon in self.get_polygons_from_path(item_under_c.path()):
                    for point in polygon:
                        point_event_l = QLineF(event_pos, point)
                        if point_event_l.length() <= self.closest_node_min_distance:
                            point_node_dist.append(point_event_l)
            if point_node_dist:
                closes_point = sorted(point_node_dist, key=lambda a: a.length())[0]
                self._closest_node_circle = self.closest_node_circle
                self._closest_node_circle.setPos(closes_point.p2())
                self.scene().addItem(self._closest_node_circle)

    def _closest_point_to_poly(self, event_pos):
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

        polygons = self.get_polygons_from_path(self.path())
        intersections_for_separate_paths = list()
        for path_num, points in enumerate(polygons):
            # iterate through pair of points, if the polygon is not "closed",
            # add the start to the end
            p1 = points.pop(0)
            if self.is_polygon() and points[-1] != p1:  # identical to QPolygonF.isClosed()
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

    def command_insert_point(self, index, pos):
        # index is always > 0, so the first element will always be moveTo
        path_num, coord_num = index
        polygons = self.get_polygons_from_path(self.path())
        try:
            polygon = polygons[path_num]
            polygon_modified = polygon[:coord_num] + [pos] + polygon[coord_num:]
            polygons[path_num] = polygon_modified
        except IndexError:
            return
        command = commands.InsertNodeCmd(self, index, pos, polygons, 'Dodaj nod')
        self.scene().undo_redo_stack.push(command)

    def command_move_grip(self, grip):
        print('ruszam')
        if grip not in self.node_grip_items:
            return
        polygons = self.get_polygons_from_path(self.path())
        grip_poly_num, grip_coord_num = grip.grip_indexes
        try:
            polygons[grip_poly_num][grip_coord_num] = grip.pos()
        except IndexError:
            return
        # usuń kółko dociągające, bo jeśli jest może być już niepotrzebne przy self._drag_to_closes_node
        if self._closest_node_circle is not None:
            self.scene().removeItem(self._closest_node_circle)
            self._closest_node_circle = None
        if self._drag_to_closest_node:
            self.closest_point_to_point(grip.pos())
        # jeśli znalazłeś najbliższy nod, wtedy przesuń grip na tę pozycję, przez co obiekt zostanie do tego
        # dociągnięty
        if self._drag_to_closest_node and self._closest_node_circle is not None:
            grip.setPos(self._closest_node_circle.pos())
        command = commands.MoveGripCmd(self, grip, 'przesun wezel')
        self.scene().undo_redo_stack.push(command)

    def command_move_item(self):
        command = commands.SelectModeMoveItem(self, 'Przesun poly', self.pos())
        self.scene().undo_redo_stack.push(command)
        return

    def command_remove_point(self, grip):
        # if there are 2 grip items in a path, then removal is not possible do not even try
        # in another case decide later whether it is possible
        if len(self.node_grip_items) <= 2:
            return
        polygons = self.get_polygons_from_path(self.path())
        grip_poly_num, grip_coord_num = grip.grip_indexes
        print('remove_point')
        print(grip_poly_num, grip_coord_num)
        try:
            polygons[grip_poly_num][grip_coord_num]
        except IndexError:
            print('index error')
            return
        if not self.is_point_removal_possible(len(polygons[grip_poly_num])):
            return

        command = commands.RemoveNodeCmd(self, grip.grip_indexes, polygons, 'Usuń węzeł')
        self.scene().undo_redo_stack.push(command)

        # self.data0.delete_node_at_position(self.current_data_x, grip_poly_num, grip_coord_num)
        # self.setPath(self.create_painter_path(polygons))
        # self.undecorate()
        # self.update_arrow_heads()
        # self.update_label_pos()
        # self.update_hlevel_labels()
        # self.update_housenumber_labels()
        # self.decorate()

    def command_reverse_poly(self):
        return

    def create_painter_path(self, poly_lists):
        path = QPainterPath()
        for poly in poly_lists:
            if self.is_polygon() and poly[0] != poly[-1]:
                poly.append(poly[0])
            qpp = QPainterPath()
            qpp.addPolygon(QPolygonF(poly))
            path.addPath(qpp)
        return path

    def _decorate(self):
        print('dekoruje polygon', 'type_polygon', self.is_polygon())
        if self.decorated():
            self.undecorate()
        self.setZValue(self.zValue() + self.decorated_z_value)
        # elapsed = datetime.now()
        # polygons = self.path().toSubpathPolygons()
        polygons = self.get_polygons_from_path(self.path())
        for polygon_num, polygon in enumerate(polygons):
            if self.decorated_poly_nums is None:
                self.decorated_poly_nums = []
            self.decorated_poly_nums.append(polygon_num)
            # elapsed = datetime.now()
            hlevels = self.get_hlevels_for_poly(self.current_data_x, polygon_num)
            for polygon_node_num, polygon_node in enumerate(polygon):
                square = GripItem(polygon_node, (polygon_num, polygon_node_num,),
                                  hlevels[polygon_node_num], self)
                self.node_grip_items.append(square)
            # else:
            #     self.node_grip_items.append(None)
        self.set_hover_over_for_address_labels(True)
        self.add_interpolated_housenumber_labels()
        self.setFlags(QGraphicsItem.ItemIsSelectable)
        self.setCursor(QCursor(Qt.CrossCursor))

    def decorate(self):
        # to be redefined in polyline and polygon classes
        return

    def decorated(self):
        return True if self.node_grip_items else False

    def get_hlevels_for_poly(self, data_level, poly_num):
        return self.data0.get_hlevels_for_poly(data_level, poly_num)

    def get_housenumbers_for_poly(self, data_level, poly_num):
        return self.data0.get_housenumbers_for_poly(data_level, poly_num)

    def get_interpolated_housenumbers(self, data_level, poly_num):
        return None

    def get_polygons_from_path(self, path):
        polygons = []
        for poly in path.toSubpathPolygons():
            # kopiuje wspolrzedne punktow esplicite, bo przez jakas referencje qpointf z path sie zmienialy
            poly_coords = [QPointF(p.x(), p.y()) for p in poly]
            if self.is_polygon() and poly.isClosed():
                poly_coords.pop()
            polygons.append(poly_coords)
        return polygons

    def get_polygons_vectors(self, path):
        # generating polygon vectors from path. Each path is split to separate polygons and then each polygon
        # is converted to single vectors. In data_x class there is similar function, but those one creates
        # vectors from Data data, and additionally one can get vectors between given path points.
        polygon_vectors = []
        for poly in path.toSubpathPolygons():
            vectors = []
            poly_coords = [QPointF(p.x(), p.y()) for p in poly]
            if self.is_polygon() and poly.isClosed():
                poly_coords.pop()
            for coord_num in range(len(poly_coords)-1):
                vectors.append(QLineF(poly_coords[coord_num], poly_coords[coord_num + 1]))
            polygon_vectors.append(vectors)
        return polygon_vectors

    def highlight_when_hoverover(self):
        if self.scene().get_viewer_scale() * 10 < IGNORE_TRANSFORMATION_TRESHOLD:
            return False
        return True

    def hoverEnterEvent(self, event):
        # print('hoverEnter')
        if not self.highlight_when_hoverover():
            return
        if self.decorated():
            self.setCursor(QCursor(Qt.CrossCursor))
            return
        self.hovered = True
        if not self.isSelected():
            self.add_hovered_shape()

    def hoverLeaveEvent(self, event):
        # print('hoverLeave')
        if self.decorated():
            self.setCursor(QCursor(Qt.ArrowCursor))
            return
        self.hovered = False
        if not self.isSelected():
            self.setPen(self.orig_pen)
            self.remove_hovered_shape()

    # to be override in other classes
    def insert_point(self, index, pos):
        return

    @staticmethod
    def is_point_removal_possible(num_elems_in_path):
        return False

    def is_polygon(self):
        if isinstance(self, PolygonQGraphicsPathItem):
            return True
        return False

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Control:
            self._drag_to_closest_node = True
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Control:
            self._drag_to_closest_node = False
        super().keyReleaseEvent(event)

    def mouseMoveEvent(self, event):
        mode = self.scene().get_pw_mapedit_mode()
        # trybie edytuj nody zachowuj sie standardowo
        if mode == 'edit_nodes':
            super().mouseMoveEvent(event)
            return
        if mode == 'select_objects':
            super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        self._mouse_press_timestamp = time.time()
        super().mousePressEvent(event)
        self.remove_hovered_shape()
        mode = self.scene().get_pw_mapedit_mode()
        if mode =='edit_nodes':
            if event.button() == Qt.LeftButton and event.modifiers() == Qt.ShiftModifier:
                dist, pos, index = self.closest_point_to_poly(event.pos())
                print(dist, pos, index)
                if index[1] >= 0 and dist <= self.threshold():
                    self.insert_point(index, pos)
                    return
        elif mode == 'select_objects':
            self.recorded_pos = self.pos()

    def mouseReleaseEvent(self, event):
        if self._closest_node_circle is not None:
            self.scene().removeItem(self._closest_node_circle)
            self._closest_node_circle = None
        self._mouse_press_timestamp = None
        mode = self.scene().get_pw_mapedit_mode()
        if mode == 'select_objects':
            if self.pos() != self.recorded_pos:
                self.command_move_item()
        self.recorded_pos = None
        super().mouseReleaseEvent(event)


    def move_grip(self, grip):
        # do be defined in child classes
        return

    def paint(self, painter, option, widget=None):
        if option.state & QStyle.State_Selected or self.decorated():
            self.setOpacity(0.5)
        else:
            self.setOpacity(1)
        if option.state & QStyle.State_Selected or self.decorated():
            self.setPen(self.selected_pen)
        elif self.hovered and not self.node_grip_items:
            self.setPen(self.hovered_over_pen)
        else:
            self.setPen(self.orig_pen)
        super().paint(painter, option, widget=widget)

    def update_arrow_heads(self):
        return

    def remove_all_hlevel_labels(self):
        return

    def remove_items_before_new_map_level_set(self):
        return

    def remove_hlevel_labels(self, node_num):
        return

    def remove_interpolated_house_numbers(self):
        return

    def remove_label(self):
        if self.label is not None:
            self.scene().removeItem(self.label)
        self.label = None

    def remove_grip(self, grip):
        # to be redefined in subclasses
        return

    def remove_hovered_shape(self):
        if self.hovered_shape_id is not None:
            self.scene().removeItem(self.hovered_shape_id)
            self.hovered_shape_id = None

    def remove_all_hlevel_labels(self):
        pass

    def remove_hlevel_labels(self, node_num):
        return

    def set_hover_over_for_address_labels(self, value):
        return

    def set_mp_data(self, level, data):
        # to be defined separately for polygon and polyline
        pass

    def set_map_level(self):
        level = self.scene().get_map_level()
        # lets save the current path in case it's changed
        self._mp_data[self.current_data_x] = self.path()
        if self._mp_data[level] is not None:
            self.remove_items_before_new_map_level_set()
            self.setPath(self._mp_data[level])
            self.current_data_x = level
            self.add_items_after_new_map_level_set()
            self.setVisible(True)
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

    def setPen(self, pen):
        if self.orig_pen is None:
            self.orig_pen = pen
        super().setPen(pen)

    def _shape(self):
        stroker = QPainterPathStroker()
        if self.hovered_shape_id is not None:
            stroker.setWidth(self.hovered_shape_id.pen().width() * self.non_cosmetic_multiplicity)
        else:
            stroker.setWidth(self.pen().width() * self.non_cosmetic_multiplicity)
        return stroker.createStroke(self.path())

    def set_threshold(self, threshold):
        self._threshold = threshold

    def threshold(self):
        if self._threshold is not None:
            return self._threshold
        return self.pen().width() or 1.

    def undecorate(self):
        print('usuwam dekoracje, %s punktow' % len(self.node_grip_items))
        self.setZValue(self.zValue() - 100)
        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable)
        self.remove_interpolated_house_numbers()
        for grip_item in self.node_grip_items:
            if grip_item is not None:
                self.scene().removeItem(grip_item)
        self.node_grip_items = []
        self.set_hover_over_for_address_labels(False)
        self.hoverLeaveEvent(None)
        self.decorated_poly_nums = None
        self.setCursor(QCursor(Qt.ArrowCursor))

    def update_label_pos(self):
        return

    def update_hlevel_labels(self):
        return

    def update_hlevel_in_node(self, grip, hlevel_value):
        return

    def update_housenumber_labels(self):
        return

    def update_interpolated_housenumber_labels(self):
        return

    def update_items_after_obj_move(self):
        self.remove_items_before_new_map_level_set()
        self.add_items_after_new_map_level_set()

class PolylineQGraphicsPathItem(PolyQGraphicsPathItem):
    def __init__(self, map_objects_properties=None, projection=None):
        super(PolylineQGraphicsPathItem, self).__init__(map_objects_properties=map_objects_properties,
                                                        projection=projection)
        self.arrow_head_items = []
        self.hlevel_labels = None
        self.housenumber_labels = None
        self.interpolated_house_numbers_labels = None
        self._mp_hlevels = [None, None, None, None, None]
        self._mp_address_numbers = [None, None, None, None, None]
        self._mp_dir_indicator = False
        self.setZValue(10)
        self.setAcceptHoverEvents(True)
        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable)

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

    def add_hlevel_labels(self):
        # add hlevel numbers dependly on map level
        if self.hlevel_labels is None:
            self.hlevel_labels = []
        for poly_num, polygon in enumerate(self.get_polygons_from_path(self.path())):
            hlevels = self.get_hlevels_for_poly(self.current_data_x, poly_num)
            for polygon_node_num, polygon_node in enumerate(polygon):
                if hlevels[polygon_node_num] is None:
                    continue
                self.hlevel_labels.append(PolylineLevelNumber(hlevels[polygon_node_num], polygon_node, self))
                # self.hlevel_labels[-1].setPos(polygon_node)

    def add_housenumber_labels(self):
        polygons = self.get_polygons_from_path(self.path())
        polygons_vectors = self.get_polygons_vectors(self.path())
        adr = list()
        for polygon_num, polygon in enumerate(polygons):
            numbers = self.get_housenumbers_for_poly(self.current_data_x, polygon_num)
            for polygon_node_num, polygon_node in enumerate(polygon):
                house_numbers = numbers[polygon_node_num]
                if house_numbers is None:
                    continue
                if house_numbers.left_side_number_before is not None:
                    line_segment_vector = polygons_vectors[polygon_num][polygon_node_num - 1]
                    position = self.get_numbers_position(line_segment_vector, 'left_side_number_before')
                    adr.append(PolylineAddressNumber(position, house_numbers.left_side_number_before, self))
                if house_numbers.left_side_number_after is not None:
                    line_segment_vector = polygons_vectors[polygon_num][polygon_node_num]
                    position = self.get_numbers_position(line_segment_vector, 'left_side_number_after')
                    adr.append(PolylineAddressNumber(position, house_numbers.left_side_number_after, self))
                if house_numbers.right_side_number_before is not None:
                    line_segment_vector = polygons_vectors[polygon_num][polygon_node_num - 1]
                    position = self.get_numbers_position(line_segment_vector, 'right_side_number_before')
                    adr.append(PolylineAddressNumber(position, house_numbers.right_side_number_before, self))
                if house_numbers.right_side_number_after is not None:
                    line_segment_vector = polygons_vectors[polygon_num][polygon_node_num]
                    position = self.get_numbers_position(line_segment_vector, 'right_side_number_after')
                    adr.append(PolylineAddressNumber(position, house_numbers.right_side_number_after, self))
        if adr:
            self.housenumber_labels = adr
        else:
            self.housenumber_labels = None

    def add_interpolated_housenumber_labels(self):
        if self.decorated_poly_nums is None:
            return
        ihn = []
        for polygon_num in self.decorated_poly_nums:
            interpolated_numbers = self.get_interpolated_housenumbers(self.current_data_x, polygon_num)
            if interpolated_numbers is not None:
                for num_def in interpolated_numbers:
                    ihn.append(PolylineAddressNumber(num_def[0], num_def[1], self))
        if ihn:
            self.interpolated_house_numbers_labels = ihn
        else:
            self.interpolated_house_numbers_labels = None

    def add_label(self):
        label = self.get_label1()
        if label is not None and label:
            self.label = PolylineLabel(label, self)

    def command_reverse_poly(self):
        print('reversing polyline')
        command = commands.ReversePolylineCmd(self, 'Odwróć polyline')
        self.scene().undo_redo_stack.push(command)

    @staticmethod
    def get_numbers_position(line_segment_vector, subj_position, testing=False):
        # testing=True is used or testing purposes, then values of for number position calculations are fixed
        # wartosci przy pointAt sa dobrane tak, aby zwracac poprawny wektor prostopadly, uwzgledniajac
        # ze operujemy w ekranowych wspolrzednych.

        if testing:
            position_at_line_segment = 0.2
            left_side_number_before = 'left_side_number_before'
            left_side_number_after = 'left_side_number_after'
            right_side_number_after = 'right_side_number_after'
            right_side_number_before = 'right_side_number_before'
        else:
            position_at_line_segment = 5 / line_segment_vector.length()
            left_side_number_before = 'right_side_number_before'
            left_side_number_after = 'right_side_number_after'
            right_side_number_after = 'left_side_number_after'
            right_side_number_before = 'left_side_number_before'
        if subj_position == left_side_number_before:
            v_start_point = line_segment_vector.pointAt(1)
            v_start = line_segment_vector.pointAt(1 - position_at_line_segment)
            v_end = line_segment_vector.pointAt(1 - 2 * position_at_line_segment)
        elif subj_position == left_side_number_after:
            v_start_point = line_segment_vector.pointAt(0)
            v_start = line_segment_vector.pointAt(position_at_line_segment)
            v_end = line_segment_vector.pointAt(0.0)
        elif subj_position == right_side_number_after:
            v_start_point = line_segment_vector.pointAt(0)
            v_start = line_segment_vector.pointAt(position_at_line_segment)
            v_end = line_segment_vector.pointAt(2 * position_at_line_segment)
        elif subj_position == right_side_number_before:
            v_start_point = line_segment_vector.pointAt(1)
            v_start = line_segment_vector.pointAt(1 - position_at_line_segment)
            v_end = line_segment_vector.pointAt(1)
        else:
            v_start_point = None
            v_start = None
            v_end = None
        return QLineF(v_start_point, QLineF(v_start, v_end).normalVector().p2())

    def get_interpolated_housenumbers(self, data_level, poly_num):
        inter_num = self.data0.get_interpolated_housenumbers_for_poly(data_level, poly_num)
        numbers = []
        for num_def in inter_num['left']:
            vector = QLineF(num_def.position, num_def.vector.p2()).normalVector()
            numbers.append((vector.unitVector(), num_def.number,))
        for num_def in inter_num['right']:
            vector = QLineF(num_def.position, num_def.vector.p2()).normalVector().normalVector().normalVector()
            numbers.append((vector.unitVector(), num_def.number,))
        return numbers

    def set_mp_data(self):
        for given_level in ('Data0', 'Data1', 'Data2', 'Data3', 'Data4'):
            data = self.get_datax(given_level)
            if not data:
                continue
            level = int(given_level[-1])
            polylines_list = list()
            for nodes in data:
                polylines_list.append(nodes)
            self._mp_data[level] = self.create_painter_path(polylines_list)
            if self.path().isEmpty():
                self.setPath(self._mp_data[level])
                self.current_data_x = level

    # niepotrzebne
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
        if self.housenumber_labels is not None and self.housenumber_labels:
            self.remove_housenumber_labels()

    def add_items_after_new_map_level_set(self):
        # print('add_items_after_new_map_level_set')
        if self._mp_dir_indicator:
            self.add_arrow_heads()
        self.add_label()
        self.add_hlevel_labels()
        self.add_housenumber_labels()

    def set_hover_over_for_address_labels(self, value):
        if self.housenumber_labels is not None and self.housenumber_labels:
            for house_num in self.housenumber_labels:
                house_num.setAcceptHoverEvents(value)

    def set_mp_dir_indicator(self, dir_indicator):
        self._mp_dir_indicator = dir_indicator
        if dir_indicator:
            self.add_arrow_heads()
        else:
            self.remove_arrow_heads()

    # redefine shape function from QGraphicsPathItem, to be used in hoverover etc.
    def shape(self):
        return self._shape()
    
    def remove_arrow_heads(self):
        for arrow_head in self.arrow_head_items:
            self.scene().removeItem(arrow_head)
        self.arrow_head_items = []

    def update_arrow_heads(self):
        # convinience function, instead call remove and add, just call one function
        if self.arrow_head_items:
            self.remove_arrow_heads()
            self.add_arrow_heads()

    def remove_housenumber_labels(self):
        if self.housenumber_labels is None:
            return
        for house_number in self.housenumber_labels:
            self.scene().removeItem(house_number)
        self.housenumber_labels = None

    def remove_interpolated_house_numbers(self):
        if self.interpolated_house_numbers_labels is not None:
            for interpolated_num in self.interpolated_house_numbers_labels:
                self.scene().removeItem(interpolated_num)
            self.interpolated_house_numbers_labels = None

    def update_label_pos(self):
        if self.label is not None:
            self.label.set_label_position()

    def update_hlevel_labels(self):
        # update numbers positions when nodes are moved around
        self.remove_all_hlevel_labels()
        self.add_hlevel_labels()

    def update_housenumber_labels(self):
        self.remove_housenumber_labels()
        self.add_housenumber_labels()

    def update_interpolated_housenumber_labels(self):
        self.remove_interpolated_house_numbers()
        self.add_interpolated_housenumber_labels()

    def update_hlevel_in_node(self, grip, hlevel_value):
        grip_poly_num, grip_coord_num = grip.grip_indexes
        self.data0.set_hlevel_to_node(self.current_data_x, grip_poly_num, grip_coord_num, hlevel_value)
        self.update_hlevel_labels()

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
        for hl in tuple(self.hlevel_labels):
            self.scene().removeItem(hl)
        self.hlevel_labels = None

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

        return self._closest_point_to_poly(event_pos)

    def decorate(self):
        self._decorate()

    def move_grip(self, grip):
        self.command_move_grip(grip)

    def remove_grip(self, grip):
        if grip in self.node_grip_items:
            self.command_remove_point(grip)

    def insert_point(self, index, pos):
        self.command_insert_point(index, pos)

    @staticmethod
    def is_point_removal_possible(num_elems_in_path):
        return num_elems_in_path >= 2

    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget=widget)


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
                nodes_qpointfs.append(nodes)
            self._mp_data[level] = self.create_painter_path(nodes_qpointfs)
            if self.path().isEmpty():
                self.setPath(self._mp_data[level])
                self.current_data_x = level

    def shape(self):
        if not self.decorated():
            return super().shape()
        return self._shape()

    def remove_items_before_new_map_level_set(self):
        if self.label is not None:
            self.remove_label()

    def add_items_after_new_map_level_set(self):
        self.add_label()

    def decorate(self):
        self._decorate()

    def move_grip(self, grip):
        self.command_move_grip(grip)

    def remove_grip(self, grip):
        if grip in self.node_grip_items:
            self.command_remove_point(grip)

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
        return self._closest_point_to_poly(event_pos)

    def insert_point(self, index, pos):
        self.command_insert_point(index, pos)


class MapLabels(QGraphicsSimpleTextItem):
    _accept_map_level_change = False

    def __init__(self, string_text, parent):
        super(MapLabels, self).__init__(string_text, parent)

    @staticmethod
    def accept_map_level_change():
        return False

    def paint(self, painter, option, widget):
        if self.set_transformation_flag():
            self.update()
            # return
        super().paint(painter, option, widget)

    def set_transformation_flag(self):
        if self.scene() is None:
            return False
        if self.scene().get_viewer_scale() > IGNORE_TRANSFORMATION_TRESHOLD:
            if not bool(self.flags() & QGraphicsItem.ItemIgnoresTransformations):
                self.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)
                return True
        else:
            if bool(self.flags() & QGraphicsItem.ItemIgnoresTransformations):
                self.setFlag(QGraphicsItem.ItemIgnoresTransformations, False)
                return True
        return False


class PoiLabel(MapLabels):
    # poi label nie musi byc typem maplabels bo jako dziecko poi, bedzie mialo jego flagi
    _accept_map_level_change = False
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
        self.set_label_position()
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

    def set_label_position(self):
        self.setPos(self.get_label_pos())
        self.setRotation(self.get_label_angle())


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
    _accept_map_level_change = False

    def __init__(self, position, text, parent):
        self.parent = parent
        self.grip_mode = False
        self.position = position
        super(PolylineAddressNumber, self).__init__(str(text), parent)
        self.setText(str(text))
        qm_font = QFont()
        qm_font.setPointSize(6)
        self.setFont(qm_font)
        self.setBrush(QBrush(QColor('blue')))
        # _, _, pheight, pwidth = self.boundingRect().getRect()
        # self.setTransformOriginPoint(pheight / 2, pwidth / 2)
        self.set_transformation_flag()
        self.set_pos(self.position)
        self.hovered_shape = None
        self.last_keyboard_press_time = None
        self.cursor_before_hoverover = None
        self.setFlag(QGraphicsItem.ItemIgnoresParentOpacity, True)

    def add_hovered_shape(self):
        self.hovered_shape = QGraphicsRectItem(*self.boundingRect().getRect(), self)
        hovered_color = QColor('red')
        # hovered_color.setAlpha(50)
        hovered_over_pen = QPen(hovered_color)
        hovered_over_pen.setCosmetic(True)
        hovered_over_pen.setWidth(self.pen().width() + 1)
        self.hovered_shape.setPen(hovered_over_pen)

    def hoverEnterEvent(self, event):
        self.setFocus(True)
        self.grabKeyboard()
        self.parent.hoverLeaveEvent(event)
        self.cursor_before_hoverover = self.cursor()
        self.setCursor(QCursor(Qt.IBeamCursor))
        super().hoverEnterEvent(event)
        self.add_hovered_shape()
        self.last_keyboard_press_time = 0
        self.scene().disable_maplevel_shortcuts()

    def hoverLeaveEvent(self, event):
        self.clearFocus()
        self.ungrabKeyboard()
        self.scene().removeItem(self.hovered_shape)
        self.hovered_shape = None
        self.scene().enable_maplevel_shortcuts()
        super().hoverLeaveEvent(event)
        self.last_keyboard_press_time = None
        self.setCursor(self.cursor_before_hoverover)
        self.cursor_before_hoverover = None

    def keyPressEvent(self, event):
        _time = time.time()
        if time.time() - self.last_keyboard_press_time > 1:
            self.setText(event.text())
        else:
            self.setText(self.text() + event.text())
        self.last_keyboard_press_time = time.time()
        self.scene().removeItem(self.hovered_shape)
        self.add_hovered_shape()

    def keyReleaseEvent(self, event):
        pass

    def paint(self, painter, option, widget):
        self.set_pos(self.position)
        super().paint(painter, option, widget)

    def set_pos(self, position):
        # workoround dla setPos, tak aby mozna wykorzystac wektor jako wspolrzedna, a nie tylko sam punkt
        # przypadku gdy skalowanie sie wylacza - powyżej ustalonej skali, wtedy nalezy caly czas przeliczac
        # punkt umieszczenia numeru i pomniejszac go proporcjonalnie do skale
        if not bool(self.flags() & QGraphicsItem.ItemIgnoresTransformations):
            self.setPos(position.pointAt(1 / self.scene().get_viewer_scale()))
        else:
            self.setPos(position.p2())


class PolylineLevelNumber(MapLabels):
    arrow_up = '\u2191'

    def __init__(self, text, position, parent):
        self.parent = parent
        self.position = position
        if not isinstance(text, str):
            text = self.arrow_up + str(text)
        else:
            text = self.arrow_up + text
        super(PolylineLevelNumber, self).__init__(text, parent)
        self.set_transformation_flag()
        _, _, pheight, pwidth = self.boundingRect().getRect()
        self.setTransformOriginPoint(pheight/2, pwidth/2)
        self.set_pos(self.position)

    def set_pos(self, position):
        # alternatywa dla setPos, tak aby moc wykorzystac wektor jak pozycje i nie mylic z oryginalnym setPos
        _, _, pheight, pwidth = self.boundingRect().getRect()
        scale = 1
        # przypadku gdy skalowanie sie wylacza - powyżej ustalonej skali, wtedy nalezy caly czas przeliczac
        # punkt umieszczenia numeru i pomniejszac go proporcjonalnie do skali
        if bool(self.flags() & QGraphicsItem.ItemIgnoresTransformations):
            scale = self.scene().get_viewer_scale()
        self.setPos(position + QPointF(-pwidth/scale/2, -pheight/scale/2))

    def paint(self, painter, option, widget):
        self.setPos(self.position)
        brush = QBrush(Qt.yellow)
        painter.setBrush(brush)
        a, b, c, d = self.boundingRect().getRect()
        painter.drawRect(int(a), int(b), int(c) + 1, int(d) + 1)
        super().paint(painter, option, widget)


class GripItem(QGraphicsPathItem):
    # https://stackoverflow.com/questions/77350670/how-to-insert-a-vertex-into-a-qgraphicspolygonitem
    _pen = QPen(QColor('green'), 1)
    #_pen.setCosmetic(True)
    _first_grip_pen = QPen(QColor('red'), 1)
    #_first_grip_pen.setCosmetic(True)
    inactive_brush = QBrush(QColor('green'))
    _first_grip_inactive_brush = QBrush(QColor('red'))
    square = QPainterPath()
    square.addRect(-5, -5, 10, 10)
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
        self.adr_labels = []
        self.setPos(pos)
        self.setParentItem(parent)
        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable
                      | QGraphicsItem.ItemSendsGeometryChanges | QGraphicsItem.ItemIgnoresParentOpacity)
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
        self.setFocus(True)
        self.grabKeyboard()
        self.scene().disable_maplevel_shortcuts()
        super().hoverEnterEvent(event)
        self._setHover(True)

    def hoverLeaveEvent(self, event):
        self.clearFocus()
        self.ungrabKeyboard()
        self.scene().enable_maplevel_shortcuts()
        super().hoverLeaveEvent(event)
        self._setHover(False)
        # w przypadku gdy grip został przesunięty bo został dociągnięty do węzła, wtedy ucieka spod myszy
        # w takim przypadku jeśli pojawiło się kółko dociągające wtedy usuń je bo inaczej zostawało
        if self.parent._closest_node_circle is not None:
            self.scene().removeItem(self.parent._closest_node_circle)
            self.parent._closest_node_circle = None
        # to samo dla modyfikatora ctrl,
        self.parent._drag_to_closest_node = False

    def keyPressEvent(self, event):
        if event.text() == 'n':
            print('wlaczam, wylaczam numeracje')
        elif event.text() == 'h':
            if self.hlevel is None:
                self.parent.update_hlevel_in_node(self, 0)
                self.hlevel = 0
            else:
                self.parent.update_hlevel_in_node(self, None)
                self.hlevel = None
        elif event.text().isdigit():
            hl = int(event.text())
            if self.hlevel is None:
                self.hlevel = hl
            self.parent.update_hlevel_in_node(self, hl)
        super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if (event.button() == Qt.LeftButton and event.modifiers() == Qt.ControlModifier):
            self.parent.setSelected(True)
            self.parent.remove_grip(self)
        elif (event.button() == Qt.LeftButton and event.modifiers() == Qt.ShiftModifier):
            print('z shiftem')
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
        if self.scene() is None:
            return False
        if self.scene().get_viewer_scale() > IGNORE_TRANSFORMATION_TRESHOLD:
            if not bool(self.flags() & QGraphicsItem.ItemIgnoresTransformations):
                self.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)
                return True
        else:
            if bool(self.flags() & QGraphicsItem.ItemIgnoresTransformations):
                self.setFlag(QGraphicsItem.ItemIgnoresTransformations, False)
                return True
        return False

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
        if self.scene() is None:
            return False
        if self.scene().get_viewer_scale() > IGNORE_TRANSFORMATION_TRESHOLD:
            if not bool(self.flags() & QGraphicsItem.ItemIgnoresTransformations):
                self.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)
                return True
        else:
            if bool(self.flags() & QGraphicsItem.ItemIgnoresTransformations):
                self.setFlag(QGraphicsItem.ItemIgnoresTransformations, False)
                return True
        return False

    def paint(self, painter, option, widget=None):
        if self.set_transformation_flag():
            self.update()
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
        if points[-1] != p1:  # identical to QPolygonF.isClosed()
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
