from collections import OrderedDict
# import projection
# from singleton_store import Store
# from PyQt5.QtSvg import QGraphicsSvgItem
from PyQt5.QtWidgets import QGraphicsItemGroup
from PyQt5.QtWidgets import QGraphicsPixmapItem, QGraphicsEllipseItem, QBrush, QGraphicsPathItem, QGraphicsItem, \
    QGraphicsPolygonItem
from QtCore import QPointF, Qt
from PyQt5.QtGui import QPainterPath, QPolygonF, QBrush, QPen, QColor, QPixmap


class Data_X(object):
    """storing multiple data it is probably better to do it in the separate class, as some operations might be easier"""
    def __init__(self, polygon):
        self.nodes_list = []
        self.outer_inner = []
        self.last_outer_index = 0
        self.polygon = polygon

    def add_points(self, points_list):
        self.nodes_list.append(points_list)
        self.outer_inner.append('inner' if self.is_data_inner(points_list) else 'outer')

    def get_nodes_and_inn_outer(self):
        returned_data = list()
        for num, data_list in enumerate(self.nodes_list):
            returned_data.append(data_list, self.outer_inner[num])
        return returned_data

    def is_data_inner(self, points_list):
        if self.polygon:
            # for the present moment I treat all polygons as outer, here checking whether all points lay inside
            # one polygon, then we can say it is inner or outer
            return False
        return False



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
            self.set_coordinates(self, latitude, longitude)

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
        self.obj_data = OrderedDict({'Type': '', 'Label': '', 'Label2': '', 'Label3': '',
                                     'DirIndicator': bool, 'EndLevel': '', 'StreetDesc': '', 'CityIdx': '',
                                     'DisctrictName': '', 'Phone': '', 'Highway': '',  'Data0': Data_X(),
                                     'Data1': Data_X(), 'Data2': Data_X(), 'Data3': Data_X(),
                                     'Data4': Data_X(), 'Others': OrderedDict()})
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
        obj_data: dict() key: tuple(elem_name, elem_position), value: value
        Returns
        -------

        """
        if comment_data is not None and comment_data:
            self.obj_comment_set(comment_data)
        for key_num in obj_data:
            key, num = key_num
            if key == 'Comment':
                self.obj_comment_set(obj_data[key])
            elif key in ('Type', 'Label', 'Label2', 'Label3', 'DirIndicator', 'EndLevel', 'StreetDesc', 'Phone',
                         'Highway'):
                self.obj_param_set(key, obj_data[key])
            elif key in ('Data0', 'Data1', 'Data2', 'Data3', 'Data4'):
                self.obj_datax_set(key, obj_data[key])
            else:
                print('Unknown key value: %s.' % key)

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

    def obj_datax_set(self, dataX, key, dataX_val):
        self.obj_data[dataX].add_points(self.coord_from_data_to_points(dataX_val))

    def coords_from_data_to_points(self, data_line):
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


class Poi(BasicMapItem, QGraphicsItemGroup):
    def __init__(self, *args, **kwargs):
        super(Poi, self).__init__(*args, **kwargs)
        self.create_object()

    def create_object(self):
        coord_pair, inner_outer = self.obj_datax_get('Data0')
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
        super(Polyline, self).__init__(*args, **kwargs)
        self.create_object()

    def create_object(self):
        colour = Qt.black
        width = 1
        dash = Qt.SolidLine
        if self.map_objects_properties is not None:
            colour = self.map_objects_properties.get_polyline_colour(self.obj_type_get())
            width = self.map_objects_properties.get_polyline_width(self.obj_type_get())
            dash = self.map_objects_properties.get_polyline_dash(self.obj_type_get())
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
            self.addItem(graphics_path_item)
            # in case polyline has a label, place it on the map
            # if mapobject.Label:
            #     if len(coordslist) == 4:
            #         label_pos = [coordslist[0], coordslist[1]]
            #         if (coordslist[3] - coordslist[1]) == 0:
            #             label_angle = 90
            #         else:
            #             label_angle = math.atan((coordslist[2] - coordslist[1]) / (coordslist[3] - coordslist[1]))
            #
            #         # print(label_angle)
            #         # self.create_text(label_pos, text = mapobject.Label, angle = label_angle)
            #     else:
            #         pass
            #         # calculate label position, lets say it will be in the meadle of the polyline
            #         # label_pos = coordslist[len(coordslist) // 2]
            #         # label_angle =
            # del (coordslist[:])


class Polygon(BasicMapItem, QGraphicsItemGroup):
    def __init__(self, *args, **kwargs):
        super(Polygon, self).__init__(*args, **kwargs)
        self.create_objects()

    def create_objects(self):
        polygon_nodes = []
        if self.map_objects_properties is not None:
            fill_colour = self.map_objects_properties.get_polygon_fill_colour()
        if self.polygonFill == 'transparent':
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
        self.addItem(q_polygon)
        return


