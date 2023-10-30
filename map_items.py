from collections import OrderedDict
# import projection
# from singleton_store import Store
# from PyQt5.QtSvg import QGraphicsSvgItem
from PyQt5.QtWidgets import QGraphicsItemGroup
from PyQt5.QtWidgets import QGraphicsPixmapItem, QGraphicsEllipseItem, QGraphicsPathItem, QGraphicsItem, \
    QGraphicsPolygonItem
from PyQt5.QtCore import QPointF, Qt
from PyQt5.QtGui import QPainterPath, QPolygonF, QBrush, QPen, QColor, QPixmap


class Data_X(object):
    """storing multiple data it is probably better to do it in the separate class, as some operations might be easier"""
    def __init__(self):
        self.nodes_list = []
        self.outer_inner = []
        self.last_outer_index = 0
        self.polygon = False

    def add_points(self, points_list):
        self.nodes_list.append(points_list)
        self.outer_inner.append('inner' if self.is_data_inner(points_list) else 'outer')

    def get_nodes_and_inn_outer(self):
        returned_data = list()
        for num, data_list in enumerate(self.nodes_list):
            returned_data.append((data_list, self.outer_inner[num]))
        return returned_data

    def is_data_inner(self, points_list):
        if self.polygon:
            # for the present moment I treat all polygons as outer, here checking whether all points lay inside
            # one polygon, then we can say it is inner or outer
            return False
        return False

    def set_polygon(self):
        self.polygon = True


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

    def return_canvas_coords(self):
        # print(Store.projection.projectionName)
        return self.projection.geo_to_canvas(self.latitude, self.longitude)

    def return_real_coords(self):
        return self.projection.canvas_to_geo()


# tutaj chyba lepiej byloby uzyc QPainterPath
# class BasicMapItem(QGraphicsItemGroup):
class BasicMapItem(object):
    def __init__(self, *args, map_comment_data=None, map_elem_data=None, map_objects_properties=None, projection=None,
                 **kwargs):
        """
        basic map items properties, derived map items inherit from it
        Parameters
        ----------
        args
        map_elem_data: dict, key=tuple(elem_name, elem_position), value=value
        map_objects_properties = class for map elements appearance: icons, line types, area patterns and filling
        kwargs
        """
        self.projection = None
        if projection is not None:
            self.projection = projection
        self.obj_comment = list()
        self.map_levels = set()
        self.obj_data = OrderedDict({'Type': '', 'Label': '', 'Label2': '', 'Label3': '',
                                     'DirIndicator': bool, 'EndLevel': '', 'StreetDesc': '', 'HouseNumber': '',
                                     'Phone': '', 'CityIdx': '',
                                     'DisctrictName': '', 'Highway': '',  'Data0': Data_X(),
                                     'Data1': Data_X(), 'Data2': Data_X(), 'Data3': Data_X(),
                                     'Data4': Data_X(), 'RouteParam': [], 'CityName': '', 'CountryName': '',
                                     'RegionName': '', 'RoadID': 0,
                                     'CountryCode': '', 'ZipCode': '', 'Others': OrderedDict()})
        self.map_objects_properties = None
        if map_objects_properties is not None:
            self.map_objects_properties = map_objects_properties
        self.obj_bounding_box = {}
        if map_elem_data is not None:
            self.set_data(map_comment_data, map_elem_data)

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
            self.obj_comment_set(comment_data)
        for number_keyname in obj_data:
            _, key = number_keyname
            if number_keyname[1] in ('Type', 'Label', 'Label2', 'Label3', 'DirIndicator', 'EndLevel', 'StreetDesc',
                                     'HouseNumber', 'Phone', 'Highway', 'CityName', 'CountryName', 'RegionName',
                                     'CountryCode', 'ZipCode'):
                self.obj_param_set(key, obj_data[number_keyname])
            elif number_keyname[1] in ('Data0', 'Data1', 'Data2', 'Data3', 'Data4'):
                self.obj_datax_set(number_keyname[1], obj_data[number_keyname])
            elif number_keyname[1] == 'RouteParam':
                for single_param in obj_data[number_keyname].split(','):
                    self.obj_data['RouteParam'].append(int(single_param))
            elif number_keyname[1] == 'RoadID':
                self.obj_data['RoadID'] = int(obj_data[number_keyname])
            elif number_keyname[1].startswith('Nod'):
                pass
            elif number_keyname[1].startswith('Numbers'):
                pass
            elif number_keyname[1].startswith('HLevel'):
                pass
            elif number_keyname[1] in ('Miasto', 'Typ', 'Plik'):
                # temporary remove these from reporting
                pass
            else:
                self.obj_others_set(number_keyname, obj_data[number_keyname])
                # print('Unknown key value: %s.' % number_keyname[1])

    def obj_comment_get(self):
        return self.obj_comment

    def obj_comment_set(self, _comments):
        for _comment in _comments:
            self.obj_comment.append(_comment)

    def obj_param_get(self, parameter):
        return self.obj_data[parameter]

    def obj_param_set(self, parameter, value):
        self.obj_data[parameter] = value

    def obj_datax_get(self, dataX):
        # tymczasowo na potrzeby testow tylko jedno data
        # zwracamy liste Nodow, jesli
        return self.obj_data[dataX].get_nodes_and_inn_outer()

    def obj_datax_set(self, data012345, data012345_val):
        self.obj_data[data012345].add_points(self.coords_from_data_to_nodes(data012345_val))
        self.map_levels.add(data012345)

    def obj_others_set(self, key, value):
        self.obj_data['Others'][key] = value

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

    def data_values(self):
        tmp_data = OrderedDict({})
        for key in self.obj_data['DataX']:
            tmp_data[key].items()

    def get_obj_levels(self):
        return self.map_levels


class Poi(QGraphicsItemGroup, BasicMapItem):
    def __init__(self, *args, **kwargs):
        super(Poi, self).__init__(*args, **kwargs)
        # self.object_type = '[POI]'
        self.create_object()

    def create_object(self):
        nodes, inner_outer = self.obj_datax_get('Data0')[0]
        x, y = nodes[0].return_canvas_coords()
        if self.map_objects_properties is not None \
                and self.map_objects_properties.poi_type_has_icon(self.obj_param_get('Type')):
            poi = QGraphicsPixmapItem(self.map_objects_properties.get_poi_pixmap(self.obj_param_get('Type')))
            poi.setPos(x, y)
            poi.setZValue(20)
        else:
            print('Unknown icon for %s, using ellipse instead.' % self.obj_param_get('Type'))
            poi = QGraphicsEllipseItem(x, y, 10, 10)
            brush = QBrush(Qt.black)
            poi.setBrush(brush)
            poi.setZValue(20)
        poi.setParentItem(self)


# tutaj chyba lepiej byloby uzyc QPainterPath
class Polyline(QGraphicsItemGroup, BasicMapItem):
    # qpp = QPainterPath()
    # qpp.addPolygon(your_polyline)
    # item = QGraphicsPathItem(qpp)
    # item.setPen(your_pen)
    # self.your_scene.addItem(item)
    def __init__(self, *args, **kwargs):
        super(Polyline, self).__init__(*args, **kwargs)
        # self.object_type = '[POLYLINE]'
        self.create_object()

    def create_object(self):
        colour = Qt.black
        width = 1
        dash = Qt.SolidLine
        if self.map_objects_properties is not None:
            colour = self.map_objects_properties.get_polyline_colour(self.obj_param_get('Type'))
            width = self.map_objects_properties.get_polyline_width(self.obj_param_get('Type'))
            dash = self.map_objects_properties.get_polyline_dash(self.obj_param_get('Type'))
        for nodes, inner_outer in self.obj_datax_get('Data0'):
            polyline = QPainterPath()
            graphics_path_item = QGraphicsPathItem()
            the_first_node = True
            for node in nodes:
                # coordslist += points.return_canvas_coords()
                coord_x, coord_y = node.return_canvas_coords()
                if the_first_node:
                    polyline.moveTo(coord_x, coord_y)
                    the_first_node = False
                else:
                    polyline.lineTo(coord_x, coord_y)
            pen = QPen(colour)
            pen.setWidth(width)
            pen.setStyle(dash)
            graphics_path_item.setPath(polyline)
            graphics_path_item.setPen(pen)
            graphics_path_item.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable)
            graphics_path_item.setZValue(10)
            # self.addItem(graphics_path_item)
            self.addToGroup(graphics_path_item)


class Polygon(QGraphicsItemGroup, BasicMapItem):
    def __init__(self, *args, **kwargs):
        super(Polygon, self).__init__(*args, **kwargs)
        # self.object_type = '[POLYLGON]'
        self.polygon_transparent = False
        for _data in ('Data0', 'Data1', 'Data2', 'Data3', 'Data4',):
            self.obj_data[_data].set_polygon()
        self.create_objects()

    def create_objects(self):
        polygon_nodes = []
        if self.map_objects_properties is not None:
            fill_colour = self.map_objects_properties.get_polygon_fill_colour(self.obj_param_get('Type'))
        if self.polygon_transparent == 'transparent':
            fill_colour = ''
        for nodes, inner_outer in self.obj_datax_get('Data0'):
            for node in nodes:
                x, y = node.return_canvas_coords()
                # print('x: %s, y: %s' %(x, y))
                polygon_nodes.append(QPointF(x, y))
        q_polygon = QGraphicsPolygonItem(QPolygonF(polygon_nodes))
        brush = QBrush(fill_colour)
        q_polygon.setBrush(brush)
        q_polygon.setZValue(0)
        # self.addItem(q_polygon)
        self.addToGroup(q_polygon)
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
            if key in self.restr_data:
                self.self.restr_sign_data[key].append(map_elem_data[number_keyname])
            else:
                self.restr_sign_data_others[number_keyname] = map_elem_data[number_keyname]


class RoadSign(object):
    def __init__(self, map_comment_data=None, map_elem_data=None):
        self.restr_sign_data = OrderedDict({'SignPoints': [], 'SignRoads': [], 'SignParams': []})
        super(RoadSign, self).__init__(map_comment_data=map_comment_data, map_elem_data=map_elem_data)

class Restriction(object):
    def __init__(self, map_comment_data=None, map_elem_data=None):
        self.restr_sign_data = OrderedDict({'Nod': [], 'TraffPoints': [], 'TraffRoads': []})
        super(Restriction, self).__init__(map_comment_data=map_comment_data, map_elem_data=map_elem_data)
