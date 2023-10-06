from collections import OrderedDict
import projection
from singleton_store import Store
from PyQt5.QtSvg import QGraphicsSvgItem
from PyQt5.QtWidgets import QGraphicsItemGroup

# tutaj chyba lepiej byloby uzyc QPainterPath
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


