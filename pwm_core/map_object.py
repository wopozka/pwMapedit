# -*- coding: utf-8 -*-
"""Wlasciwosci obiektu mapy zapisywane w pliku MP (Type, Label, EndLevel...) - czesc wspolna POI, polylinii
i polygonow, bez czesci graficznej."""
from collections import OrderedDict

from pwm_core.data_x import Node, Data_X
from pwm_core import mp_format


class BasicMapItem(object):
    def __init__(self, map_obj_id, map_objects_properties=None, _projection=None):
        """
        basic map items properties, derived map items inherit from it
        Parameters
        ----------
        map_objects_properties = class for map elements appearance: icons, line types, area patterns and filling
        projection = projection class
        """
        # super(BasicMapItem, self).__init__()
        self._id = map_obj_id
        # used for marking objects that were removed from map. For undo/redo actions it is easier to mark object as
        # removed than to copy it and then remove.
        self._deleted = False
        self._projection = None
        self._map_objects_properties = None
        if _projection is not None:
            self._projection = _projection
        if map_objects_properties is not None:
            self._map_objects_properties = map_objects_properties
        self.obj_comment = None
        self._map_type = None
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
        self.districtname = None
        self.roadid = None
        self.zipcode = None
        self.others = None
        self.obj_bounding_box = {}

    # def __repr__(self):
    #     return str(self._map_type)

    def __str__(self):
        # redefine in other classes
        return

    def clear_others(self):
        self.others = None

    def coords_from_data_to_nodes(self, data_line):
        coords = []
        coordlist = data_line.strip().lstrip('(').rstrip(')')
        for a in coordlist.split('),('):
            latitude, longitude = a.split(',')
            self.set_obj_bounding_box(float(latitude), float(longitude))
            coords.append(Node(latitude=latitude, longitude=longitude, projection=self._projection))
        return coords

    def get_comment(self):
        return self.obj_comment

    def get_datax(self, dataX):
        # tymczasowo na potrzeby testow tylko jedno data
        # zwracamy liste Nodow, jesli
        data_level = int(dataX[4:])
        return self.data0.get_polys_for_data_level(data_level)

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

    def get_id(self):
        return self._id

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
        if self.others is None:
            return []
        return tuple(self.others)
        # return_val = list()
        # for key_tuple, val in self.others.items():
        #     key = key_tuple[1]
        #     return_val.append((key, val,))
        # return return_val

    def get_param(self, parameter):
        return getattr(self, parameter.lower())

    def get_phone_number(self):
        if self.phone is None:
            return ''
        return self.phone

    def get_route_params(self):
        if self.routeparam is None:
            return None
        return self.routeparam

    def get_street_desc(self):
        if self.streetdesc is None:
            return ''
        return self.streetdesc

    def get_type(self):
        return self._map_type

    def is_deleted(self):
        return self._deleted

    # setters
    def set_comment(self, _comments):
        if self.obj_comment is None:
            self.obj_comment = list()
        else:
            self.obj_comment.clear()
        if _comments is None:
            self.obj_comment = None
        else:
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
                # self.set_param('Type', int(obj_data[number_keyname], 16))
                self.set_type(obj_data[number_keyname])
            elif number_keyname[1] in ('CityName', 'CountryName', 'RegionName',
                                       'CountryCode', 'ZipCode', 'DistrictName'):
                self.set_param(key, obj_data[number_keyname])
            elif number_keyname[1] in ('Data0', 'Data1', 'Data2', 'Data3', 'Data4'):
                self.set_datax(number_keyname[1], obj_data[number_keyname])
            elif number_keyname[1] == 'RouteParam':
                self.set_route_params(obj_data[number_keyname].split(','))
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
                self.set_others(number_keyname[1], obj_data[number_keyname])
                # print('Unknown key value: %s.' % number_keyname[1])

    def set_datax(self, data012345, data012345_val):
        if self.data0 is None:
            self.data0 = Data_X(projection=self._projection)
        self.data0.add_nodes_from_string(data012345, data012345_val)
        self.set_obj_bounding_box(self.data0.get_obj_bounding_box())
        return

    def set_deleted(self):
        self._deleted = True

    def set_dirindicator(self, value):
        if value == False or value == '0':
            self.dirindicator = None
        else:
            self.dirindicator = True

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

    def set_id(self, obj_id):
        self._id = obj_id

    def set_others(self, key, value):
        if self.others is None:
            self.others = list()
        self.others.append((key, value,))

    def set_param(self, parameter, value):
        setattr(self, parameter.lower(), value)
        # self.obj_data[parameter] = value

    def set_phone_number(self, value):
        self.phone = value

    def set_route_params(self, value):
        # przypadku gdy na poczatku nie bylo zadnego route param self.routeparam wynosi none. Wtedy
        # gdy robimy redo, nie da sie enumerowac, ustawmy wiec None i z glowy. Zastanowic sie czy wszedzie zera
        # w route param nie powinny ustawiac routeparam na none
        if value is None:
            self.routeparam = None
        else:
            if self.routeparam is None:
                self.routeparam = [0 for a in range(12)]
            for param_num, single_param in enumerate(value):
                try:
                    self.routeparam[param_num] = int(single_param)
                except IndexError:
                    return

    def set_street_desc(self, value):
        self.streetdesc = value

    def set_type(self, type_val):
        if isinstance(type_val, str):
            self._map_type = int(type_val, 16)
        else:
            self._map_type = type_val

    def set_obj_bounding_box(self, obj_bb):
        # obwiednia moze byc nieustawiona (None), np. dla danych utworzonych przy podziale linii
        if any(obj_bb[key] is None for key in ('S', 'N', 'E', 'W')):
            return
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

    def set_undeleted(self):
        self._deleted = False

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

    def to_mp_record(self, default_precision=None):
        """default_precision: precyzja wspolrzednych dla obiektu, ktorego precyzja nie jest znana (precyzja mapy)"""
        if self.obj_comment is not None and self.obj_comment:
            mp_record = [';' + comment for comment in self.obj_comment]
        else:
            mp_record = []
        mp_record += self.to_mp_record_header()
        mp_record.append('Type=' + str(hex(self._map_type)))
        if self.label1 is not None and self.label1:
            mp_record.append('Label=' + self.label1)
        if self.endlevel is not None and self.endlevel:
            mp_record.append('EndLevel=' + str(self.endlevel))
        if self.dirindicator is not None and self.dirindicator:
            mp_record.append('DirIndicator=1')
        if self.routeparam:
            mp_record.append('RouteParam=' + ','.join(str(a) for a in self.routeparam))
        if self.housenumber is not None and self.housenumber:
            mp_record.append('HouseNumber=' + self.housenumber)
        if self.streetdesc is not None and self.streetdesc:
            mp_record.append('StreetDesc=' + self.streetdesc)
        if self.phone is not None and self.phone:
            mp_record.append('Phone=' + self.phone)
        mp_record += self.data0.to_mp_record(default_precision)
        if self.label2 is not None and self.label2:
            mp_record.append('Label2=' + self.label2)
        if self.label3 is not None and self.label3:
            mp_record.append('Label3=' + self.label3)
        return mp_record + self.to_mp_record_others()

    @staticmethod
    def to_mp_record_header():
        return []

    def to_mp_record_others(self):
        return [f'{key}={val}' for key, val in self.get_others()]


class Poi(BasicMapItem):
    """POI bez czesci graficznej"""
    @staticmethod
    def to_mp_record_header():
        return [mp_format.MAP_OBJECT_POI]


class Polyline(BasicMapItem):
    """Polylinia bez czesci graficznej"""
    @staticmethod
    def to_mp_record_header():
        return [mp_format.MAP_OBJECT_POLYLINE]


class Polygon(BasicMapItem):
    """Polygon bez czesci graficznej"""
    @staticmethod
    def to_mp_record_header():
        return [mp_format.MAP_OBJECT_POLYGON]


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
