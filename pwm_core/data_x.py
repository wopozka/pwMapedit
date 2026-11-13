# -*- coding: utf-8 -*-
"""Wspolrzedne obiektow mapy: wezly (Node) i dane Data0..Data4 z numeracja i HLevel (Data_X)."""
from collections import namedtuple
import copy
import itertools

from pwm_core.geometry import Point, Line

Numbers_Definition = namedtuple('Numbers_Definition',
                                ['left_side_numbering_style',
                                 'left_side_number_before', 'left_side_number_after', 'right_side_numbering_style',
                                 'right_side_number_before', 'right_side_number_after', 'left_side_zip_code',
                                 'right_side_zip_code', 'left_side_city', 'left_side_region', 'left_side_country',
                                 'right_side_city', 'right_side_region', 'right_side_country']
                                )

Interpolated_Number = namedtuple('Interpolated_Number', ['vector', 'position', 'number'])
# liczba miejsc po przecinku we wspolrzednych zapisywanych do pliku MP, gdy nie znamy precyzji ani obiektu, ani mapy
DEFAULT_MP_PRECISION = 5
# tolerancja (we wspolrzednych canvas) przy porownywaniu, czy wezly roznych obiektow sa tym samym punktem
SAME_NODE_TOLERANCE = 1e-3


class MergeError(Exception):
    """Obiektow nie da sie polaczyc, tresc wyjatku to komunikat dla uzytkownika"""
    pass


class Node(Point):
    """Class used for storing coordinates of given map object point"""
    def __init__(self, latitude=None, longitude=None, x=None, y=None, projection=None):
        # self.acuracy = 10000
        self._projection = None
        if projection is not None:
            self._projection = projection
        if latitude is not None and longitude is not None:
            _x, _y = self._projection.geo_to_canvas(latitude, longitude)
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
        aaa = Node(x=self.x(), y=self.y(), projection=self._projection)
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
        return self._projection.canvas_to_geo(self.x(), self.y())

    def get_canvas_coords(self):
        return self.x(), self.y()
        # return self._projection.geo_to_canvas(self.latitude, self.longitude)

    def get_mp_coords(self, accuracy):
        # get coords in mp file specification
        lan, lon = self.get_geo_coordinates()
        return f'({lan:.{accuracy}f},{lon:.{accuracy}f})'

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

    def node_has_hlevel(self):
        return False if self._hlevel_definition is None else True

    def node_has_numeration(self):
        if self._numbers_definitions is None:
            return False
        if self.node_starts_numeration() or self.node_ends_numeration():
            return True
        return False

    def __str__(self):
        return str(self._numbers_definitions)

    def set_coordinates_from_point(self, position):
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
        self._projection = projection
        # liczba miejsc po przecinku wspolrzednych wczytanych z pliku, None gdy nieznana (np. obiekt narysowany
        # w programie). Precyzja jest osobna dla kazdego obiektu - wczesniej byla zmienna klasowa i przechodzila
        # z jednej mapy (obiektu) na kolejne.
        self.precision = None
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

        # obwód polygonów albo długość linii
        self.poly_perimeter = 0

    def add_hlevels_from_string(self, hlevels_definition):
        if hlevels_definition.startswith('HLevel'):
            hlevels_definition = hlevels_definition.split('=', 1)[1]
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
        self.add_housenumbers_to_nodes(data_level, poly_num, definition)

    def add_housenumbers_to_nodes(self, data_level, poly_num, definition):
        """
        Parameters
        ----------
        data_level: int, 0, 1, 2, 3, 4, odpowiada Data0, Data1, Data2, Data3, Data4
        poly_num: int, 0, 1, 2, 3, 4..., kolejny numer polyline/polygon
        definition: string: definicja Numbers w pliku mp
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
        left_zip = None
        right_zip = None
        if len(num_data) > 7:
            try:
                if int(num_data[7]) == -1: 
                    lef_zip = None
            except ValueError:
                left_zip = num_data[7]
        if len(num_data) > 8:
            try:
                if int(num_data[8]) == -1:
                    right_zip
            except ValueError:
                right_zip = num_data[8]

        self._level_polys(data_level)[poly_num][node_num].set_numbers_definition_field_name('left_side_numbering_style', left_style)
        self._level_polys(data_level)[poly_num][node_num].set_numbers_definition_field_name('left_side_number_after', left_start)
        self._level_polys(data_level)[poly_num][node_num].set_numbers_definition_field_name('right_side_numbering_style', right_style)
        self._level_polys(data_level)[poly_num][node_num].set_numbers_definition_field_name('right_side_number_after', right_start)
        if left_zip is not None or right_zip is not None:
            self._level_polys(data_level)[poly_num][node_num].set_numbers_definition_field_name('left_side_zip_code', left_zip)
            self._level_polys(data_level)[poly_num][node_num].set_numbers_definition_field_name('right_side_zip_code', right_zip)
        last_node_def = self._level_polys(data_level)[poly_num][-1].get_numbers_definition()

        if last_node_def is not None:
            self._level_polys(data_level)[poly_num][node_num].set_numbers_definition_field_name('left_side_number_before', last_node_def.left_side_number_before)
            self._level_polys(data_level)[poly_num][node_num].set_numbers_definition_field_name('right_side_number_before', last_node_def.right_side_number_before)
            self._level_polys(data_level)[poly_num][-1].set_node_has_no_numeration()

        if left_start is not None or right_start is not None:
            self._level_polys(data_level)[poly_num][-1].set_numbers_definition_field_name('left_side_number_before', left_end)
            self._level_polys(data_level)[poly_num][-1].set_numbers_definition_field_name('right_side_number_before', right_end)

    def add_nodes_from_string(self, data_level, data_string):
        _data_level = int(data_level[4:])
        if _data_level not in self._data_levels:
            self._data_levels.append(_data_level)
            self._poly_data_points.append([])
        data_index = self._data_levels.index(_data_level)
        self._poly_data_points[data_index].append(self.coords_from_data_to_nodes(data_string))
        self._last_data_level = _data_level
        self._last_poly_data_index = len(self._poly_data_points[data_index]) - 1
        self.poly_perimeter = max(self.poly_perimeter,
                                  self.calculate_poly_perimeter(self._poly_data_points[data_index][-1]))

    @staticmethod
    def calculate_poly_perimeter(coords):
        perimeter = 0.0
        for coord_pair in itertools.pairwise(coords):
            line = Line.from_points(coord_pair[0], coord_pair[1])
            perimeter += line.length()
        return perimeter

    def clean_numbers_definitions(self, data_level, polynum):
        nodes_with_numbers = [a for a in self._level_polys(data_level)[polynum] if a.node_has_numeration()]
        # jesli nie ma wezlow z numeracja, to nie ma co robic
        if not nodes_with_numbers:
            return
        self.clean_numbers_definition_first_and_last_nodes(data_level, polynum)
        # jeśli mamy jeden wezel z numeracja, trzeba na ostatnim ustawic 0, o ile nie sa ustawione
        if len(nodes_with_numbers) == 1:
            self.clean_numbers_definitions_only_one_node_case(data_level, polynum, nodes_with_numbers)
            return
        self.clean_numbers_definitions_multiple_nodes_case(data_level, polynum)
        return

    def clean_numbers_definition_first_and_last_nodes(self, data_level, polynum):
        # update numbers definitions for nodes
        # na poczatek zerujemy ostatnie wezly, bo przed i po nie ma dla nich sensu
        # pierwszy nod
        if self._level_polys(data_level)[polynum][0].node_has_numeration():
            for key in ('left_side_number_before', 'right_side_number_before'):
                self._level_polys(data_level)[polynum][0].set_numbers_definition_field_name(key, None)
        # ostatni nod
        last_node = self._level_polys(data_level)[polynum][-1]
        if last_node.node_has_numeration():
            for key in ('left_side_numbering_style', 'left_side_number_after', 'right_side_numbering_style',
                        'right_side_number_after', 'left_side_zip_code',
                        'right_side_zip_code', 'left_side_city', 'left_side_region', 'left_side_country',
                        'right_side_city', 'right_side_region', 'right_side_country'):
                last_node.set_numbers_definition_field_name(key, None)

    def clean_numbers_definitions_only_one_node_case(self, data_level, polynum, nodes_with_numbers):
        last_node = self._level_polys(data_level)[polynum][-1]
        if nodes_with_numbers[0].get_specific_number_definition('left_side_number_after') is None:
            last_node.set_numbers_definition_field_name('left_side_number_before', None)
        else:
            if not last_node.node_has_numeration():
                last_node.set_numbers_definition_field_name('left_side_number_before', 0)
            elif last_node.get_specific_number_definition('left_side_number_before') is None:
                last_node.set_numbers_definition_field_name('left_side_number_before', 0)
        if nodes_with_numbers[0].get_specific_number_definition('right_side_number_after') is None:
            last_node.set_numbers_definition_field_name('right_side_number_before', None)
        else:
            if not last_node.node_has_numeration():
                last_node.set_numbers_definition_field_name('right_side_number_before', 0)
            elif last_node.get_specific_number_definition('right_side_number_before') is None:
                last_node.set_numbers_definition_field_name('right_side_number_before', 0)
        return

    def clean_numbers_definitions_multiple_nodes_case(self, data_level, polynum):
        # jesli ostatni wezel nie ma ustawionej zadnej numeracji to ja ustaw, pomoze to porzadkowac wezly
        last_node = self._level_polys(data_level)[polynum][-1]
        if not last_node.node_has_numeration():
            last_node.set_numbers_definition_field_name('left_side_number_before', 0)
            last_node.set_numbers_definition_field_name('right_side_number_before', 0)

        nodes_with_numbers = [a for a in self._level_polys(data_level)[polynum] if a.node_has_numeration()]
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

    def coords_from_data_to_nodes(self, data_line):
        coords = []
        coordlist = data_line.strip().lstrip('(').rstrip(')')
        precision = 0
        for a in coordlist.split('),('):
            latitude, longitude = a.split(',')
            if not precision:
                precision = max(len(latitude.split('.', 1)[1]), len(longitude.split('.', 1)[1]))
            self.set_obj_bounding_box(float(latitude), float(longitude))
            coords.append(Node(latitude=latitude, longitude=longitude, projection=self._projection))
        if precision <= 6:
            self.precision = max(self.precision or 0, precision)
        return coords

    def copy(self):
        d_copy = Data_X(self._projection)
        d_copy._bounding_box_N = self._bounding_box_N
        d_copy._bounding_box_S = self._bounding_box_S
        d_copy._bounding_box_W = self._bounding_box_W
        d_copy._bounding_box_E = self._bounding_box_E
        d_copy._data_levels = copy.copy(self._data_levels)
        d_copy._last_data_level = self._last_data_level
        d_copy._last_poly_data_index = self._last_poly_data_index
        d_copy.poly_perimeter = self.poly_perimeter
        d_copy.precision = self.precision
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
        del self._level_polys(data_level)[polynum][index]
        self.clean_numbers_definitions(data_level, polynum)

    def delete_poly_at_data_level(self, data_level, poly_num):
        """
        Usuwa cały polyline/polygon z danego data_level,
        Parameters
        ----------
        data_level: int, 0 - Data0, 1 - Data1, 2 - Data2, 3 - Data3, 4 - Data4
        poly_num: int, numer polyline/polygon w danym data_level

        Returns
        -------

        """
        if data_level in self._data_levels and poly_num < len(self._level_polys(data_level)):
            del self._level_polys(data_level)[poly_num]
            # jesli nie ma juz zadnych polygonow w danym data_level to usun go z listy
            if len(self._level_polys(data_level)) == 0:
                del self._poly_data_points[self._data_levels.index(data_level)]
                self._data_levels.remove(data_level)
        return

    def delete_whole_data_level(self, data_level):
        """
        Usuwa cały data_level dla danego obiektu,
        Parameters
        ----------
        data_level

        Returns
        -------

        """
        return

    def get_calculated_housenumber_defs_for_node(self, data_level, poly_num, node_num):
        """
        Calculate numbers definition for node, in case the node is located at interpolated numbers road section.
        Used when set numbering for node without numeration, or when polyline is split into parts.
        Parameters
        ----------
        data_level: int, 0 - Data0, 1 - Data1, 2 - Data2, 3 - Data3, 4 - Data4
        poly_num: int, number of poly in polys, in case there are more than 1
        node_num: int, number of node in poly

        Returns
        -------
        None: if there is no definition
        Numbers_Definition: if there is definition
        """

        for pair in itertools.pairwise(self.get_nodes_indexes_with_housenumbers(data_level, poly_num)):
            # if node is between two nodes with number
            start_node_idx, end_node_idx = pair
            if start_node_idx < node_num < end_node_idx:
                start_node = self.get_poly_node(data_level, poly_num, start_node_idx)
                end_node = self.get_poly_node(data_level, poly_num, end_node_idx)
                definitions = Numbers_Definition(*[None for a in range(14)])._asdict()
                left, right = self.get_interpolated_housenumbers_for_poly_section(data_level, poly_num,
                                                                                  start_node_idx, end_node_idx)
                if left:
                    # there are interpolated numbers on left, do something
                    for num_key in ('left_side_numbering_style', 'left_side_zip_code', 'left_side_city',
                                    'left_side_region', 'left_side_country'):
                        definitions[num_key] = start_node.get_specific_number_definition(num_key)
                    definitions['left_side_number_before'], definitions['left_side_number_after'] = (
                        self.get_housenumber_for_node_from_interpolated_numbers(data_level, poly_num, start_node_idx,
                                                                                end_node_idx, node_num, True))

                else:
                    # there are no interpolated numbers on left, check whether there are any
                    if start_node.node_has_numeration() and start_node.node_starts_numeration():
                        for num_key in ('left_side_numbering_style', 'left_side_zip_code', 'left_side_city',
                                        'left_side_region', 'left_side_country'):
                            definitions[num_key] = start_node.get_specific_number_definition(num_key)
                        definitions['left_side_number_after'] = (
                            end_node.get_specific_number_definition('left_side_number_before'))
                        definitions['left_side_number_before'] = (
                            start_node.get_specific_number_definition('left_side_number_after'))

                        # 'left_side_numbering_style',
                        # 'left_side_number_before', 'left_side_number_after', 'right_side_numbering_style',
                        # 'right_side_number_before', 'right_side_number_after', 'left_side_zip_code',
                        # 'right_side_zip_code', 'left_side_city', 'left_side_region', 'left_side_country',
                        # 'right_side_city', 'right_side_region', 'right_side_country'
                if right:
                    for num_key in ('right_side_numbering_style', 'right_side_zip_code', 'right_side_city',
                                    'right_side_region', 'right_side_country'):
                        definitions[num_key] = start_node.get_specific_number_definition(num_key)
                    definitions['right_side_number_before'], definitions['right_side_number_after'] = (
                        self.get_housenumber_for_node_from_interpolated_numbers(data_level, poly_num, start_node_idx,
                                                                                end_node_idx, node_num, False))
                else:
                    # there are no interpolated numbers on right, check whether there are any
                    if start_node.node_has_numeration() and start_node.node_starts_numeration():
                        for num_key in ('right_side_numbering_style', 'right_side_zip_code', 'right_side_city',
                                        'right_side_region', 'right_side_country'):
                            definitions[num_key] = start_node.get_specific_number_definition(num_key)
                        definitions['right_side_number_after'] = (
                            end_node.get_specific_number_definition('right_side_number_before'))
                        definitions['right_side_number_before'] = (
                            start_node.get_specific_number_definition('right_side_number_after'))
                return Numbers_Definition(**definitions)
        return None

    def get_data_levels(self):
        return self._data_levels

    def _level_polys(self, data_level):
        # _poly_data_points jest indeksowane pozycja poziomu na liscie _data_levels, a nie numerem poziomu
        # (obiekt moze miec np. tylko Data0 i Data2)
        return self._poly_data_points[self._data_levels.index(data_level)]

    def get_data_level_index(self, data_level):
        if data_level in self._data_levels:
            return self._data_levels.index(data_level)
        return None

    def get_housenumbers_for_poly(self, data_level, poly_num):
        # zwraca definicje wszystkich numerow domow przypisanych do danego noda
        polys = self.get_polys_for_data_level(data_level)
        return [node.get_numbers_definition() for node in polys[poly_num]]

    def get_housenumber_for_node_from_interpolated_numbers(self, data_level, poly_num, start_node_idx, end_node_idx,
                                                           node_idx, left_side):
        """
        returns interpolated numbers for each node
        Parameters
        ----------
        data_level: int, data0, data1, data2, data3, data4
        poly_num: int, num of poly in polygons
        start_node_idx: int, index of start node
        end_node_idx: int, index of end node
        node_idx: int, index of given node
        left_side: bool, either left or right side of the road

        Returns
        -------
        dict, {node_idx: Numbers_Definition}

        """
        segment_length = sum(a.length() for a in self.get_poly_vectors(data_level, poly_num, start_node_idx,
                                                                       end_node_idx))
        segment_to_node_length = sum(a.length() for a in self.get_poly_vectors(data_level, poly_num, start_node_idx,
                                                                       node_idx))
        start_node_num_def = self.get_poly_node(data_level, poly_num, start_node_idx).get_numbers_definition()
        end_node_num_def = self.get_poly_node(data_level, poly_num, end_node_idx).get_numbers_definition()
        if left_side:
            numbers = self.get_numbers_between(start_node_num_def.left_side_number_after,
                                                    end_node_num_def.left_side_number_before,
                                                    start_node_num_def.left_side_numbering_style)
            numbers = ([start_node_num_def.left_side_number_after] + numbers +
                            [end_node_num_def.left_side_number_before])
        else:
            numbers = self.get_numbers_between(start_node_num_def.right_side_number_after,
                                                     end_node_num_def.right_side_number_before,
                                                     start_node_num_def.right_side_numbering_style)
            numbers = ([start_node_num_def.right_side_number_after] + numbers +
                             [end_node_num_def.right_side_number_before])
        distance = segment_length / (len(numbers) - 1)
        before = numbers[int(segment_to_node_length // distance)]
        after = numbers[int(segment_to_node_length // distance + 1)]

        return before, after

    def get_interpolated_housenumbers_for_poly(self, data_level, poly_num):
        interpolated_numbers = {'left': [], 'right': []}
        for pair in itertools.pairwise(self.get_nodes_indexes_with_housenumbers(data_level, poly_num)):
            start_node_idx, end_node_idx = pair
            left, right = self.get_interpolated_housenumbers_for_poly_section(data_level,
                                                                              poly_num, start_node_idx, end_node_idx)
            interpolated_numbers['left'] += left
            interpolated_numbers['right'] += right
        return interpolated_numbers

    def get_interpolated_housenumbers_for_poly_section(self, data_level, poly_num, start_node_idx, end_node_idx):
        """
        Zwraca interpolowane numery dla odcinka drogi
        Parameters
        ----------
        data_level: int, końcówka data: data0 ->0, data1 - 1, data2 - 2, data3 - 3, data4 - 4
        poly_num: int, numer polygonu
        start_node_idx: int, indeks nodu startowego
        end_node_idx: index nodu koncowego

        Returns
        -------
        tuple(lhs, rhs) - (Interpolated_Number(vector, position, num), Interpolated_Number(vector, position, num))
        """
        left = []
        right = []
        node_with_num = self.get_poly_node(data_level, poly_num, start_node_idx)
        node_with_num_plus = self.get_poly_node(data_level, poly_num, end_node_idx)
        # create polyline elements as vectors
        poly_vectors = self.get_poly_vectors(data_level, poly_num, start_node_idx, end_node_idx)

        left_num_style = node_with_num.get_specific_number_definition('left_side_numbering_style')
        if left_num_style is not None and left_num_style != 'N':
            left_num_start = node_with_num.get_specific_number_definition('left_side_number_after')
            left_num_end = node_with_num_plus.get_specific_number_definition('left_side_number_before')
            on_left = self.get_numbers_between(left_num_start, left_num_end, left_num_style)
            # poly vectors will be changed during get_interpolated_numbers_coordinates,
            # therefore we work on a copy: list(poly_vectors)
            left += self.get_interpolated_numbers_coordinates(list(poly_vectors), on_left)

        right_num_style = node_with_num.get_specific_number_definition('right_side_numbering_style')
        if right_num_style is not None and right_num_style != 'N':
            right_num_start = node_with_num.get_specific_number_definition('right_side_number_after')
            right_num_end = node_with_num_plus.get_specific_number_definition('right_side_number_before')
            on_right = self.get_numbers_between(right_num_start, right_num_end, right_num_style)
            # poly vectors will be changed during get_interpolated_numbers_coordinates,
            # therefore we work on a copy: list(poly_vectors)
            right += self.get_interpolated_numbers_coordinates(list(poly_vectors), on_right)
        return left, right

    @staticmethod
    def get_interpolated_numbers_coordinates(poly_vectors, numbers, current_num_distance=None,
                                             default_num_distance=None):
        """
            Oblicza pozycje interpolowanych numerów na zadanym odcinku polilinii. Funkcja rekurencyjna. Oblicza długość
            polylinii, wylicza równą odległość pomiędzy numerami, potem kolejno oblicza pozycję numerów odcinając,
            z długości polylinii odcinek za odcinkiem.

            Parameters:
            -----------
            poly_vectors : list
                Lista obiektów Line reprezentujących kolejne odcinki polilinii.
            numbers : list
                Lista numerów do rozmieszczenia na odcinku.
            current_num_distance : float, opcjonalnie
                Odległość od początku pierwszego odcinka do pierwszego numeru (jeśli None, zostanie wyliczona automatycznie).
            default_num_distance : float, opcjonalnie
                Domyślna odległość pomiędzy kolejnymi numerami (jeśli None, zostanie wyliczona na podstawie długości polilinii i liczby numerów).

            Zwraca:
            --------
            list
                Lista obiektów Interpolated_Number, zawierających wektor (Line), pozycję (Point) oraz numer.
            """

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

    def get_nodes_indexes_with_housenumbers(self, data_level, poly_num):
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
                'W': self._bounding_box_W}

    def get_perimeter(self):
        return self.poly_perimeter

    def get_poly_node(self, data_level, poly_num, node_num):
        """
        zwraca konkretny nod dla konkretnego polygonu
        Parameters
        ----------
        data_level: int: 0, 1, 2, 3, 4, odpowiada Data0, Data1, Data2, Data3, Data4
        poly_num: int, number of polygon in polys, odpowiada kolejnemu polyline, polygonowi
        node_num: int, number of node in polygon, odpowiada kolejnemu nodowi w polygonie

        Returns
        -------
        Node
        """
        if data_level not in self._data_levels:
            return None
        data_list = self._poly_data_points[self._data_levels.index(data_level)]
        return data_list[poly_num][node_num]

    def get_polys_for_data_level(self, data_level):
        # zwraca nowa liste z (tymi samymi, niekopiowanymi) listami nodow wszystkich polygonow/polylinii danego
        # data_level
        if data_level not in self._data_levels:
            return None
        return list(self._poly_data_points[self._data_levels.index(data_level)])

    def get_poly_vectors(self, data_level, poly_num, start_node_idx, end_node_idx):
        """
        generating polygon vectors for each path. Each path is split to separate polygons and then each polygon
        is converted to single vectors. In Poly class there is similar function, but those one creates
        vectors from path, it creates vectors for all path, not separate points.
        Parameters
        ----------
        data_level: int, data level
        poly_num: int, number of polygon
        start_node_idx: int, start node number
        end_node_idx: int, end node number

        Returns
        -------

        list: list of Line vectors

        """
        poly = self.get_polys_for_data_level(data_level)[poly_num]
        poly_vectors = list()
        for vector_num in range(start_node_idx, end_node_idx):
            x1 = poly[vector_num].x()
            y1 = poly[vector_num].y()
            x2 = poly[vector_num + 1].x()
            y2 = poly[vector_num + 1].y()
            poly_vectors.append(Line(x1, y1, x2, y2))
        return poly_vectors

    def insert_node_at_position(self, data_level, polynum, index, x, y):
        polygon = self._level_polys(data_level)[polynum]
        if index == 0:
            polygon_mod = [Node(x=x, y=y, projection=self._projection)] + polygon
        elif index == -1:
            polygon_mod = polygon + [Node(x=x, y=y, projection=self._projection)]
        else:
            polygon_mod = polygon[:index] + [Node(x=x, y=y, projection=self._projection)] + polygon[index:]
        self._level_polys(data_level)[polynum] = polygon_mod

    def is_splitting_possible(self, data_level, poly_num, node_num):
        """
        Checks whether splitting is possible at given node.
        Parameters
        ----------
        data_level: int, data level
        poly_num: int, number of polygon
        node_num: int, number of node

        Returns
        -------
        bool: True if splitting is possible, False otherwise
        """
        if data_level not in self._data_levels:
            return False
        if poly_num >= len(self._level_polys(data_level)):
            return False
        if 1 <= node_num < len(self._level_polys(data_level)[poly_num]) - 1:
            return True
        return False

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
        if dl_index is not None:
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

    def split_data_x(self, data_level, poly_num, node_num):
        """
        Split dataX for given poli at node num. As a result we get two dataX objects, the first contains everything
        and the first part of split poly, the second contains only split part for a new poly - only one polyline
        Parameters
        ----------
        data_level: 0, 1, 2, 3, 4
        poly_num: int, number of poly
        node_num: int, node index

        Returns
        -------
        [dataX_1,dataX_2]] or [] in case of failure
        """

        if not self.is_splitting_possible(data_level, poly_num, node_num):
            return []
        if self.get_poly_node(data_level, poly_num, node_num).node_has_numeration():
            node_num_def = self.get_poly_node(data_level, poly_num, node_num).get_numbers_definition()
        else:
            node_num_def = self.get_calculated_housenumber_defs_for_node(data_level,poly_num, node_num)
        polys = [[]]
        for n_num, node in enumerate(self.get_polys_for_data_level(data_level)[poly_num]):
            if n_num == node_num:
                polys[-1].append(node.copy())
                polys.append([])
            polys[-1].append(node.copy())
        polys[0][-1].set_numbers_definition(node_num_def)
        polys[1][0].set_numbers_definition(node_num_def)
        poly1 = self.copy()
        poly1.set_poly_from_node_list(data_level, poly_num, polys[0])
        poly1.clean_numbers_definitions(data_level, poly_num)
        poly2 = Data_X(projection=self._projection)
        poly2.precision = self.precision
        poly2._data_levels.append(data_level)
        poly2._poly_data_points.append([polys[1]])
        # poly2 zawiera tylko jedna linie, wiec ma numer 0
        poly2.clean_numbers_definitions(data_level, 0)
        return [poly1, poly2]

    @staticmethod
    def same_node_position(node1, node2):
        return abs(node1.x() - node2.x()) <= SAME_NODE_TOLERANCE and abs(node1.y() - node2.y()) <= SAME_NODE_TOLERANCE

    def _single_line_copy(self, data_level, reverse=False):
        # kopia (ewentualnie odwrocona) jedynej linii z danego poziomu, z numeracja i hlevel
        tmp = Data_X(projection=self._projection)
        tmp._data_levels.append(data_level)
        tmp._poly_data_points.append([[node.copy() for node in self._level_polys(data_level)[0]]])
        if reverse:
            tmp.reverse_poly(data_level)
        return tmp._level_polys(data_level)[0]

    @staticmethod
    def _join_nodes(node_end, node_start, hlevel_from_start):
        """
        Wezel styku dwoch sklejanych linii: konczy przedzial numeracji linii poprzedniej (wartosci *_number_before)
        i zaczyna przedzial linii nastepnej (pozostale pola).
        Parameters
        ----------
        node_end: Node, ostatni wezel linii poprzedniej
        node_start: Node, pierwszy wezel linii nastepnej
        hlevel_from_start: bool, przy konflikcie hlevel bierzemy z node_start (True) albo z node_end (False)
        """
        joint = node_start.copy()
        end_def = node_end.get_numbers_definition()
        if end_def is not None:
            for key in ('left_side_number_before', 'right_side_number_before'):
                if getattr(end_def, key) is not None:
                    joint.set_numbers_definition_field_name(key, getattr(end_def, key))
        if hlevel_from_start:
            hlevel = node_start.get_hlevel_definition() if node_start.node_has_hlevel() else \
                node_end.get_hlevel_definition()
        else:
            hlevel = node_end.get_hlevel_definition() if node_end.node_has_hlevel() else \
                node_start.get_hlevel_definition()
        joint.set_hlevel_definition(hlevel)
        return joint

    @staticmethod
    def _chain_lines(data_objs, data_level):
        """
        Skleja jedyne linie z danego poziomu w jedna ciagla linie. Kierunek pierwszej linii jest zachowany, pozostale
        sa w razie potrzeby odwracane. Linie musza sie stykac koncami.
        Returns
        -------
        (list of Node, bool): sklejona linia, czy ktoras linie trzeba bylo odwrocic
        """
        same = Data_X.same_node_position
        chain = data_objs[0]._single_line_copy(data_level)
        remaining = list(data_objs[1:])
        reversed_any = False
        while remaining:
            for idx, data_obj in enumerate(remaining):
                line = data_obj._level_polys(data_level)[0]
                if same(chain[-1], line[0]) or same(chain[-1], line[-1]):
                    reverse = not same(chain[-1], line[0])
                    new = data_obj._single_line_copy(data_level, reverse=reverse)
                    chain = chain[:-1] + [Data_X._join_nodes(chain[-1], new[0], False)] + new[1:]
                elif same(chain[0], line[-1]) or same(chain[0], line[0]):
                    reverse = not same(chain[0], line[-1])
                    new = data_obj._single_line_copy(data_level, reverse=reverse)
                    chain = new[:-1] + [Data_X._join_nodes(new[-1], chain[0], True)] + chain[1:]
                else:
                    continue
                reversed_any = reversed_any or reverse
                del remaining[idx]
                break
            else:
                raise MergeError(f'Linie na poziomie Data{data_level} nie tworzą ciągłego łańcucha - '
                                 f'każda kolejna linia musi zaczynać się albo kończyć na końcu poprzednich.')
        return chain, reversed_any

    @staticmethod
    def merge_polylines(data_objs):
        """
        Skleja dane kilku polylinii w jedna linie. Kierunek i kolejnosc wyznacza pierwszy obiekt.
        Parameters
        ----------
        data_objs: list of Data_X, pierwszy to obiekt, po ktorym nowa linia dziedziczy wlasciwosci

        Returns
        -------
        (Data_X, list of int, bool): polaczone dane, pominiete poziomy (nie ma ich kazda linia albo nie tworza na
        nich ciaglego lancucha), czy ktoras linie trzeba bylo odwrocic.
        Raises MergeError, gdy linii nie da sie polaczyc.
        """
        if len(data_objs) < 2:
            raise MergeError('Do połączenia potrzebne są co najmniej dwie linie.')
        first = data_objs[0]
        all_levels = set()
        for data_obj in data_objs:
            all_levels.update(data_obj.get_data_levels())
        common_levels = [level for level in sorted(first.get_data_levels())
                         if all(level in data_obj.get_data_levels() for data_obj in data_objs)]
        if not common_levels:
            raise MergeError('Linie nie mają wspólnego poziomu Data, nie da się ich połączyć.')
        for data_obj in data_objs:
            for level in common_levels:
                if len(data_obj._level_polys(level)) != 1:
                    raise MergeError(f'Jedna z linii ma kilka części na poziomie Data{level}. '
                                     f'Łączenie linii wieloczęściowych nie jest obsługiwane.')
        merged = Data_X(projection=first._projection)
        known_precisions = [data_obj.precision for data_obj in data_objs if data_obj.precision is not None]
        merged.precision = max(known_precisions) if known_precisions else None
        skipped_levels = sorted(all_levels - set(common_levels))
        reversed_any = False
        for level in common_levels:
            try:
                chain, reversed_on_level = Data_X._chain_lines(data_objs, level)
            except MergeError:
                # najnizszy wspolny poziom musi sie dac skleic, wyzsze (uproszczone) w razie problemow pomijamy
                if level == common_levels[0]:
                    raise
                skipped_levels.append(level)
                continue
            if level == common_levels[0]:
                reversed_any = reversed_on_level
            merged._data_levels.append(level)
            merged._poly_data_points.append([chain])
            merged.clean_numbers_definitions(level, 0)
            merged.poly_perimeter = max(merged.poly_perimeter, merged.calculate_poly_perimeter(chain))
        # obwiednie obiektow zrodlowych moga byc nieustawione (np. czesc z podzialu linii) albo nieaktualne (po
        # przesunieciu wezlow), dlatego liczymy ja od nowa z wezlow
        merged.recalculate_bounding_box()
        return merged, sorted(skipped_levels), reversed_any

    def recalculate_bounding_box(self):
        self._bounding_box_N = self._bounding_box_S = self._bounding_box_W = self._bounding_box_E = None
        for polys in self._poly_data_points:
            for poly in polys:
                for node in poly:
                    self.set_obj_bounding_box(*node.get_geo_coordinates())

    def set_poly_from_node_list(self, data_level, poly_num, poly):
        polys = self.get_polys_for_data_level(data_level)
        if polys and len(polys) > poly_num:
            self._level_polys(data_level)[poly_num] = poly
            return True
        return False

    def __str__(self):
        return f'<Data Levels: {str(self._data_levels)}, Data Points: {str(self._poly_data_points)}>'

    def get_mp_precision(self, default_precision=None):
        """Precyzja zapisu: wlasna obiektu, a gdy nieznana - podana domyslna (np. precyzja mapy)."""
        if self.precision is not None:
            return self.precision
        if default_precision is not None:
            return default_precision
        return DEFAULT_MP_PRECISION

    def to_mp_record(self, default_precision=None):
        precision = self.get_mp_precision(default_precision)
        poly_points = []
        for data_level in self.get_data_levels():
            for poly_num, poly in enumerate(self.get_polys_for_data_level(data_level)):
                data_x = 'Data' + (str(data_level)) + '='
                poly_points.append(data_x + ','.join([point.get_mp_coords(precision) for point in poly]))
                nodes_with_nums = [(node_num, node) for node_num, node in enumerate(poly) if node.node_has_numeration()]
                nodes_with_hlevel = [(node_num, node) for node_num, node in enumerate(poly) if node.node_has_hlevel()]
                if len(nodes_with_nums) >= 2:
                    number_num = 1
                    for node_pair in itertools.pairwise(nodes_with_nums):
                        numbers_def = self.numbers_to_mp(node_pair[0][0], node_pair[0][1], node_pair[1][1])
                        poly_points.append('Numbers' + str(number_num) + '=' + numbers_def)
                        number_num += 1
                    # jeśli ostatni numerowany nod nie jest fizycznie ostatnim nodem, dodaj jeszcze informację
                    # gdzie numeracje sie konczy
                    last_node = nodes_with_nums[-1]
                    if last_node[0] < (len(poly) -1) and not last_node[1].node_starts_numeration():
                        poly_points.append('Numbers' + str(number_num) + '=' + str(last_node[0]) + ',N,-1,-1,N,-1,-1')
                if nodes_with_hlevel:
                    hlevel_def = []
                    for node_num_node in nodes_with_hlevel:
                        node_num = node_num_node[0]
                        node = node_num_node[1]
                        hlevel_def.append(f'({node_num},{node.get_hlevel_definition()})')
                    poly_points.append('HLevel' + str(poly_num) + '=' + ','.join(hlevel_def))
        return poly_points

    def numbers_to_mp(self, start_node_num, start_node, end_node):
        # tworzenie definicji numeracji zgodnej z plikiem mp na podstawie pary nodow
        s_numeration = start_node.get_numbers_definition()
        e_numeration = end_node.get_numbers_definition()
        numeration = [start_node_num]
        if s_numeration.left_side_numbering_style is not None and s_numeration.left_side_numbering_style != 'N':
            numeration.append(s_numeration.left_side_numbering_style)
            numeration.append(s_numeration.left_side_number_after)
            numeration.append(e_numeration.left_side_number_before)
        else:
            numeration += ['N,-1,-1']
        if s_numeration.right_side_numbering_style is not None and s_numeration.right_side_numbering_style != 'N':
            numeration.append(s_numeration.right_side_numbering_style)
            numeration.append(s_numeration.right_side_number_after)
            numeration.append(e_numeration.right_side_number_before)
        else:
            numeration += ['N,-1,-1']
        if s_numeration.left_side_zip_code is not None or s_numeration.right_side_zip_code is not None:
            if s_numeration.left_side_zip_code is not None:
                numeration.append(s_numeration.left_side_zip_code)
            else:
                numeration.append('-1')
            if s_numeration.right_side_zip_code is not None:
                numeration.append(s_numeration.right_side_zip_code)
            else:
                numeration.append('-1')
            numeration += ['-1', '-1']
        return ','.join(str(num) for num in numeration)

    def update_node_coordinates(self, data_level, polynum, index, position):
        """
        Ustaw wsplorzedne noda w poly
        Parameters
        ----------
        data_level: (int) 0, 1, 2, 3, 4, w zależności od Data
        polynum: (int) numer polygonu
        index: (int) indeks noda
        position: obiekt z metodami x() i y() (Point, Node, QPointF)

        Returns
        -------

        """
        polygon = self.get_polys_for_data_level(data_level)[polynum]
        polygon_nod = polygon[index]
        polygon_nod.set_coordinates_from_point(position)
