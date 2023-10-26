from collections import OrderedDict
# import projection
# from singleton_store import Store
# from PyQt5.QtSvg import QGraphicsSvgItem
from PyQt5.QtWidgets import QGraphicsItemGroup
from PyQt5.QtWidgets import QGraphicsPixmapItem, QGraphicsEllipseItem, QBrush
QtCore import QPointF, Qt


class Data_X(object):
    """storing multiple data it is probably better to do it in the separate class, as some operations might be easier"""
    def __init__(self):
        pass


class Node(object):
    """Class used for storing coordinates of given map object point"""
    def __init__(self, latitude=None, longitude=None):
        # self.acuracy = 10000
        if latitude is not None and longitude is not None:
            self.set_coordinates(self, latitude, longitude)

    def set_coordinates(self, latitude, longitude):
        self.longitude = longitude
        self.latitude = latitude

    def get_coordinates(self):
        return self.latitude, self.longitude


# tutaj chyba lepiej byloby uzyc QPainterPath
# class BasicMapItem(QGraphicsItemGroup):
class BasicMapItem(object):
    def __init__(self, *args, map_elem_data=None, map_objects_properties=None, **kwargs):
        """
        basic map items properties, derived map items inherit from it
        Parameters
        ----------
        args
        map_elem_data: dict, key=tuple(elem_name, elem_position), value=value
        map_objects_properties = class for map elems apperiance: icons, line types, area paterns and filling
        kwargs
        """
        self.obj_data = OrderedDict({'Comment': list(), 'Type': '', 'Label': '', 'Label2': '', 'Label3': '',
                                     'DirIndicator': bool, 'EndLevel': '', 'StreetDesc': '', 'CityIdx': '',
                                     'DisctrictName': '', 'Phone': '', 'Highway': '',  'DataX': OrderedDict(),
                                     'Others': OrderedDict()})
        self.map_objects_properties = None
        if map_objects_properties is not None:
            self.map_objects_properties = map_objects_properties
        self.obj_bounding_box = {}
        if map_elem_data is not None:
            self.set_data(map_elem_data)

    def set_data(self, obj_data):
        """
        Setting element properties when red from disk
        Parameters
        ----------
        obj_data: dict() key: tuple(elem_name, elem_position), value: value
        Returns
        -------

        """
        for key_num in obj_data:
            key, num = key_num
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
                self.obj_data['Others'][key] = obj_data[key]

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
        # tymczasowo na potrzeby testow tylko jedno data
        # zwracamy liste Nodow, jesli
        for a in self.obj_data['DataX']:
            return self.obj_data['DataX'][a]

    def obj_datax_set(self, key, _dataX):
        self.obj_data['DataX'][key] = self.coord_from_data_to_point(_dataX)

    def coords_from_data_to_points(self, data_line):
        coords = []
        coordlist = data_line.strip().lstrip('(').rstrip(')')
        for a in coordlist.split('),('):
            latitude, longitude = a.split(',')
            self.set_obj_bounding_box(float(latitude), float(longitude))
            coords.append(Node(latitude=latitude, longitude=longitude))
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


class POI(BasicMapItem, QGraphicsItemGroup):
    def __init__(self, *args, **kwargs):
        super(POI, self).__init__(*args, **kwargs)
        self.create_object()

    def create_object(self):
        for val in self.obj_datax_get():
            for coord_pair in val:
                x, y = coord_pair.return_canvas_coords()
        if self.map_objects_properties is not None \
                and self.map_objects_properties.poi_type_has_icon(self.obj_type_get()):
            poi = QGraphicsPixmapItem(self.map_objects_properties.get_poi_pixmap(self.obj_type_get()))
            poi.setPos(x, y)
            poi.setZValue(20)
        else:
            print(self.obj_type_get())
            poi = QGraphicsEllipseItem(x, y, 10, 10)
            brush = QBrush(Qt.black)
            poi.setBrush(brush)
            poi.setZValue(20)
        poi.setParentItem(self)


# tutaj chyba lepiej byloby uzyc QPainterPath
class Polyline(BasicMapItem, QGraphicsItemGroup):
    # qpp = QPainterPath()
    # qpp.addPolygon(your_polyline)
    # item = QGraphicsPathItem(qpp)
    # item.setPen(your_pen)
    # self.your_scene.addItem(item)
    def __init__(self, *args, **kwargs):
        _obj_data = {'Comment': list(), 'Type': '', 'Label': '', 'EndLevel': '', 'DataX': OrderedDict({}),
                     'Other': OrderedDict({})}
        self.obj_data = OrderedDict(_obj_data)
        super(Polyline, self).__init__(*args, **kwargs)
        self.create_object()

    def create_object(self):
        f_coordslist = []
        colour = Qt.black
        width = 1
        dash = Qt.SolidLine
        if self.map_objects_properties is not None:
            colour = self.map_objects_properties.get_polyline_colour(self.obj_type_get())
            width = self.map_objects_properties.get_polyline_width(self.obj_type_get())
            dash = self.map_objects_properties.get_polyline_dash(self.obj_type_get())
        for key in mapobject.Points.keys():  # because might be multiple Data (Data0_0, Data0_1, Data1_0 etc)
            polyline = QPainterPath()
            graphics_path_item = QGraphicsPathItem()
            for num, points in enumerate(mapobject.Points[key]):
                coordslist += points.return_canvas_coords()
                coord_x, coord_y = points.return_canvas_coords()
                if num == 0:
                    polyline.moveTo(coord_x, coord_y)
                else:
                    polyline.lineTo(coord_x, coord_y)
            pen = QPen(colour)
            pen.setWidth(width)
            pen.setStyle(dash)
            graphics_path_item.setPath(polyline)
            graphics_path_item.setPen(pen)
            graphics_path_item.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable)
            graphics_path_item.setZValue(10)
            self.addItem(graphics_path_item)
            # in case polyline has a label, place it on the map
            if mapobject.Label:
                if len(coordslist) == 4:
                    label_pos = [coordslist[0], coordslist[1]]
                    if (coordslist[3] - coordslist[1]) == 0:
                        label_angle = 90
                    else:
                        label_angle = math.atan((coordslist[2] - coordslist[1]) / (coordslist[3] - coordslist[1]))

                    # print(label_angle)
                    # self.create_text(label_pos, text = mapobject.Label, angle = label_angle)
                else:
                    pass
                    # calculate label position, lets say it will be in the meadle of the polyline
                    # label_pos = coordslist[len(coordslist) // 2]
                    # label_angle =
            del (coordslist[:])


class Polygon(BasicMapItem):
    def __init__(self, map_elem_data):
        _obj_data = {'Comment': list(), 'Type': '', 'Label': '', 'EndLevel': '', 'DataX': OrderedDict({}),
                     'Other': OrderedDict({})}
        self.obj_data = OrderedDict(_obj_data)
        super(Polygon, self).__init__()
        self.set_data(map_elem_data)


