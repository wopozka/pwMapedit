import math
from collections import OrderedDict
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


# tutaj chyba lepiej byloby uzyc QPainterPath
# class BasicMapItem(QGraphicsItemGroup):
class BasicMapItem(object):
    def __init__(self, map_comment_data=None, map_elem_data=None, map_objects_properties=None, projection=None):
        """
        basic map items properties, derived map items inherit from it
        Parameters
        ----------
        map_comment_data: comment to map item
        map_elem_data: dict, key=tuple(elem_name, elem_position), value=value
        map_objects_properties = class for map elements appearance: icons, line types, area patterns and filling
        """
        # super(BasicMapItem, self).__init__()
        self.projection = None
        if projection is not None:
            self.projection = projection
        self.obj_comment = list()
        self.map_levels = set()
        self.type = None
        self.label = None
        self.label2 = None
        self.label3 = None
        self.dirindicator = None
        self.endlevel = None
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
        self.map_objects_properties = None
        if map_objects_properties is not None:
            self.map_objects_properties = map_objects_properties
        self.obj_bounding_box = {}
        if map_elem_data is not None:
            self.set_data(map_comment_data, map_elem_data)

    def __repr__(self):
        return self.type

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
            self.obj_comment_set(comment_data)
        for number_keyname in obj_data:
            _, key = number_keyname
            if number_keyname[1] == 'Type':
                self.obj_param_set('Type', int(obj_data[number_keyname], 16))
            elif number_keyname[1] in ('Label', 'Label2', 'Label3', 'DirIndicator', 'EndLevel', 'StreetDesc',
                                       'HouseNumber', 'Phone', 'Highway', 'CityName', 'CountryName', 'RegionName',
                                       'CountryCode', 'ZipCode'):
                self.obj_param_set(key, obj_data[number_keyname])
            elif number_keyname[1] in ('Data0', 'Data1', 'Data2', 'Data3', 'Data4'):
                self.obj_datax_set(number_keyname[1], obj_data[number_keyname])
            elif number_keyname[1] == 'RouteParam':
                if self.routeparam is None:
                    self.routeparam = []
                for single_param in obj_data[number_keyname].split(','):
                    self.routeparam.append(int(single_param))
            elif number_keyname[1] == 'RoadID':
                self.roadid = int(obj_data[number_keyname])
            elif number_keyname[1].startswith('Nod'):
                pass
            elif number_keyname[1].startswith('Numbers'):
                pass
            elif number_keyname[1].startswith('HLevel'):
                self.set_hlevels(obj_data[number_keyname])
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
        return getattr(self, parameter.lower())

    def obj_param_set(self, parameter, value):
        setattr(self, parameter.lower(), value)
        # self.obj_data[parameter] = value

    def obj_datax_get(self, dataX):
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

    def obj_datax_set(self, data012345, data012345_val):
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
        self.map_levels.add(data012345)
        return

    def obj_others_set(self, key, value):
        self.others[key] = value

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

    def get_obj_levels(self):
        return self.map_levels

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


class Poi(BasicMapItem):
    def __init__(self, parent, map_comment_data=None, map_elem_data=None, map_objects_properties=None, projection=None):
        super(Poi, self).__init__(map_comment_data=map_comment_data, map_elem_data=map_elem_data,
                                  map_objects_properties=map_objects_properties, projection=projection)
        # self.object_type = '[POI]'
        # self.create_object()
        # modyfikacja sposobu wizaualizacji prostokata do podswietlania
        # https://stackoverflow.com/questions/1604995/qt-4-5-changing-the-selection-marquee-for-qgraphicsitem
        # https://www.qtcentre.org/threads/15089-QGraphicsView-change-selected-rectangle-style

    def create_object(self):
        nodes, inner_outer = self.obj_datax_get('Data0')[0]
        x, y = nodes[0].get_canvas_coords()
        if self.map_objects_properties is not None \
                and self.map_objects_properties.poi_type_has_pixmap_icon(self.obj_param_get('Type')):
            poi = QGraphicsPixmapItem(self.map_objects_properties.get_poi_pixmap(self.obj_param_get('Type')))
            poi.setPos(0, 0)
        else:
            # print('Unknown icon for %s, using ellipse instead.' % self.obj_param_get('Type'))
            poi = QGraphicsEllipseItem(0, 0, 20, 20)
            brush = QBrush(Qt.black)
            poi.setBrush(brush)
            poi.show()
        # poi.setParentItem(self)
        # self.setPos(x, y)
        # self.setZValue(20)
        # self.addToGroup(poi)


class Polyline(BasicMapItem):
    # tutaj chyba lepiej byloby uzyc QPainterPath
    # qpp = QPainterPath()
    # qpp.addPolygon(your_polyline)
    # item = QGraphicsPathItem(qpp)
    # item.setPen(your_pen)
    # self.your_scene.addItem(item)
    def __init__(self, parent, map_comment_data=None, map_elem_data=None, map_objects_properties=None, projection=None):
        super(Polyline, self).__init__(map_comment_data=map_comment_data, map_elem_data=map_elem_data,
                                       map_objects_properties=map_objects_properties, projection=projection)
        # self.object_type = '[POLYLINE]'
        # self.create_object()

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
                coord_x, coord_y = node.get_canvas_coords()
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
            # self.addToGroup(graphics_path_item)


class Polygon(BasicMapItem):
    def __init__(self, parent, map_comment_data=None, map_elem_data=None, map_objects_properties=None, projection=None):
        super(Polygon, self).__init__(map_comment_data=map_comment_data, map_elem_data=map_elem_data,
                                      map_objects_properties=map_objects_properties, projection=projection)
        # self.object_type = '[POLYLGON]'
        # self.polygon_transparent = False
        # for _data in ('Data0', 'Data1', 'Data2', 'Data3', 'Data4',):
        #     self.obj_data[_data].set_polygon()
        # self.create_objects()
        # polygon z przesuwanymi rogami za ktore mozna lapac
        # rysowanie przy pomocy myszy
        # https://stackoverflow.com/questions/60413976/how-to-draw-polyline-with-pyqt5-in-python

    def create_objects(self):
        polygon_nodes = []
        if self.map_objects_properties is not None:
            fill_colour = self.map_objects_properties.get_polygon_fill_colour(self.obj_param_get('Type'))
        if self.polygon_transparent == 'transparent':
            fill_colour = ''
        for nodes, inner_outer in self.obj_datax_get('Data0'):
            for node in nodes:
                x, y = node.get_canvas_coords()
                # print('x: %s, y: %s' %(x, y))
                polygon_nodes.append(QPointF(x, y))
        q_polygon = QGraphicsPolygonItem(QPolygonF(polygon_nodes))
        brush = QBrush(fill_colour)
        q_polygon.setBrush(brush)
        q_polygon.setZValue(0)
        # self.addItem(q_polygon)
        # self.addToGroup(q_polygon)
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


class PoiAsPath(QGraphicsPathItem):
    # basic class for poi without pixmap icon
    def __init__(self, projection, icon):
        self.projection = projection
        super(PoiAsPath, self).__init__()
        self._mp_data = [None, None, None, None, None]
        self._mp_end_level = 0
        self._curent_map_level = 0
        self.icon = icon
        self.setZValue(20)
        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable)

    def set_map_level(self, level):
        if self._curent_map_level == level:
            return
        if self._mp_data[level] is not None:
            self.setPos(self._mp_data[level])
        elif self._mp_data[level] is None and self._mp_end_level < level:
            self.setVisible(False)
        elif self._mp_data[level] is None and self._mp_end_level >= level:
            self.setVisible(True)
        return

    def set_mp_data(self, given_level, data):
        if self.path().isEmpty():
            self.setPath(self.icon)
        if isinstance(given_level, str):
            level = int(given_level[-1])
        else:
            level = given_level
        # creates qpainterpaths for polylines at given Data level
        node = data[0]
        x, y = node[0].get_canvas_coords()
        self._mp_data[level] = QPointF(x, y)
        if self.pos().isNull():
            self.setPos(self._mp_data[level])


    def decorate(self):
        pass

    def undecorate(self):
        pass

class PoiAsPixmap(QGraphicsPixmapItem):
    # basic class for poi with pixmap icon
    def __init__(self, projection, icon):
        self.projection = projection
        super(PoiAsPixmap, self).__init__()
        self._mp_data = [None, None, None, None, None]
        self._mp_end_level = 0
        self._curent_map_level = 0
        self.icon = icon
        self.setZValue(20)
        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable)
    def set_map_level(self, level):
        if self._curent_map_level == level:
            return
        if self._mp_data[level] is not None:
            self.setPath(self._mp_data[level])
        elif self._mp_data[level] is None and self._mp_end_level < level:
            self.setVisible(False)
        elif self._mp_data[level] is None and self._mp_end_level >= level:
            self.setVisible(True)
        return

    def set_mp_data(self, given_level, data):
        if self.pixmap().isNull():
            self.setPixmap(self.icon)
        if isinstance(given_level, str):
            level = int(given_level[-1])
        else:
            level = given_level
        node = data[0]
        x, y = node[0].get_canvas_coords()
        self._mp_data[level] = QPointF(x, y)
        if self.pos().isNull():
            self.setPos(self._mp_data[level])

    def decorate(self):
        pass

    def undecorate(self):
        pass

class PolyQGraphicsPathItem(QGraphicsPathItem):
    # basic class for Polyline and Polygon, for presentation on maps
    selected_pen = QPen(QColor("red"))
    selected_pen.setCosmetic(True)
    selected_pen.setStyle(Qt.DotLine)
    hovered_over_pen = QPen(QColor('red'))
    hovered_over_pen.setWidth(4)
    hovered_over_pen.setCosmetic(True)
    non_cosmetic_multiplicity = 4

    def __init__(self, projection, *args, **kwargs):
        self.hovered = False
        self.projection = projection
        super(PolyQGraphicsPathItem, self).__init__(*args, **kwargs)
        self.orig_pen = None
        self.node_grip_items = list()
        self.node_grip_hovered = False
        self.label = None
        self._mp_data = [None, None, None, None, None]
        self._mp_end_level = 0
        self._curent_map_level = 0

    def set_map_level(self, level):
        if self._curent_map_level == level:
            return
        if self._mp_data[level] is not None:
            self.setPath(self._mp_data[level])
        elif self._mp_data[level] is None and self._mp_end_level < level:
            self.setVisible(False)
        elif self._mp_data[level] is None and self._mp_end_level >= level:
            self.setVisible(True)
        return

    def set_mp_data(self, level, data):
        # to be defined separately for polygon and polyline
        pass

    def set_mp_end_level(self, end_level):
        self._mp_end_level = end_level

    def move_grip(self, grip):
        print('ruszam')
        if grip not in self.node_grip_items:
            return
        grip_index = self.node_grip_items.index(grip)
        path = self.path()
        path.setElementPositionAt(grip_index, grip.pos().x(), grip.pos().y())
        self.setPath(path)
        self.refresh_arrow_heads()
        self.update_label_pos()
        self.update_hlevel_labels()

    def remove_grip(self, grip):
        if grip in self.node_grip_items:
            self.remove_point(self.node_grip_items.index(grip))

    def paint(self, painter, option, widget=None):
        if option.state & QStyle.State_Selected:
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

    def hoverEnterEvent(self, event):
        if self.node_grip_items:
            return
        self.hovered = True
        if not self.isSelected():
            self.setPen(self.hovered_over_pen)

    def hoverLeaveEvent(self, event):
        if self.node_grip_items:
            return
        self.hovered = False
        if not self.isSelected():
            self.setPen(self.orig_pen)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)

    def decorate(self):
        self.setZValue(self.zValue() + 100)
        # elapsed = datetime.now()
        path = self.path()
        for path_elem in (path.elementAt(elem_num) for elem_num in range(path.elementCount())):
            point = QPointF(path_elem)
            elapsed = datetime.now()
            square = GripItem(QPointF(point), self)
            print(datetime.now() - elapsed)
            self.node_grip_items.append(square)
        self.setFlags(QGraphicsItem.ItemIsSelectable)
        # self.node_grip_items = [GripItem(QPointF(path.elementAt(elem_num)), self)
        #                         for elem_num in range(path.elementCount())]
        # print(datetime.now() - elapsed)

    def undecorate(self):
        print('usuwam dekoracje')
        self.setZValue(self.zValue() - 100)
        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable)
        scene = self.scene()
        for grip_item in self.node_grip_items:
            scene.removeItem(grip_item)
        self.node_grip_items = []
        self.hoverLeaveEvent(None)

    def remove_point(self, index):
        # if there are 2 grip items in a path, then removal is not possible do not even try
        # in another case decide later whether it is possible
        if len(self.node_grip_items) <= 2:
            return
        path = self.path()
        new_path = QPainterPath()
        next_elem_type = ''
        num_elems_in_path = []
        for elem_num in range(path.elementCount()):
            if elem_num == index:
                if path.elementAt(elem_num).isMoveTo():
                    next_elem_type = 'move_to'
                else:
                    next_elem_type = 'draw_to'
            else:
                if next_elem_type:
                    if next_elem_type == 'move_to':
                        num_elems_in_path.append(1)
                        new_path.moveTo(QPointF(path.elementAt(elem_num)))
                    else:
                        new_path.lineTo(QPointF(path.elementAt(elem_num)))
                        num_elems_in_path[-1] += 1
                    next_elem_type = ''
                else:
                    if path.elementAt(elem_num).isMoveTo():
                        new_path.moveTo(QPointF(path.elementAt(elem_num)))
                        num_elems_in_path.append(1)
                    else:
                        new_path.lineTo(QPointF(path.elementAt(elem_num)))
                        num_elems_in_path[-1] += 1
        if not self.is_point_removal_possible(num_elems_in_path):
            return

        self.setPath(new_path)
        grip = self.node_grip_items.pop(index)
        if self.scene():
            self.scene().removeItem(grip)
        self.refresh_arrow_heads()
        self.update_label_pos()
        self.delete_hlevel_label(index)

    @staticmethod
    def is_point_removal_possible(num_elems_in_path):
        return False

    def refresh_arrow_heads(self):
        return

    def update_label_pos(self):
        return

    def update_hlevel_labels(self):
        return

    def delete_hlevel_label(self, node_num):
        return

    def remove_label(self):
        self.scene().removeItem(self.label)
        self.label = None

class PolylineQGraphicsPathItem(PolyQGraphicsPathItem):
    def __init__(self, projection, *args, **kwargs):
        super(PolylineQGraphicsPathItem, self).__init__(projection, *args, **kwargs)
        self.arrow_head_items = []
        self.hlevel_labels = None
        self._mp_hlevels = [None, None, None, None, None]
        self._mp_address_numbers = [None, None, None, None, None]
        self.setZValue(10)
        self.setAcceptHoverEvents(True)
        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable)

    def set_mp_data(self, given_level, data):
        if isinstance(given_level, str):
            level = int(given_level[-1])
        else:
            level = given_level
        # creates qpainterpaths for polylines at given Data level
        polyline = QPainterPath()
        for nodes in data:
            for node_num, node in enumerate(nodes):
                x, y = node.get_canvas_coords()
                if node_num == 0:
                    polyline.moveTo(x, y)
                else:
                    polyline.lineTo(x, y)
        self._mp_data[level] = polyline
        if self.path().isEmpty():
            self.setPath(polyline)

    def set_mp_hlevels(self, given_level, data):
        if isinstance(given_level, str):
            level = int(given_level[-1])
        else:
            level = given_level
        self._mp_hlevels[level] = data

    def shape(self):
        stroker = QPainterPathStroker()
        stroker.setWidth(self.pen().width() * self.non_cosmetic_multiplicity)
        return stroker.createStroke(self.path())

    def add_arrow_heads(self):
        # lets add arrowhead every second segment
        path = self.path()
        for elem_num in range(0, path.elementCount() - 1, 2):
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

    def add_label(self, label):
        self.label = PolylineLabel(label, self)

    def update_label_pos(self):
        if self.label is not None:
            self.label.setPos(self.label.get_label_pos())
            self.label.setRotation(self.label.get_label_angle())

    def add_hlevel_labels(self):
        # add hlevel numbers dependly on map level
        if not self._mp_hlevels[self._curent_map_level]:
            return
        if self.hlevel_labels is None:
            self.hlevel_labels = dict()
        path = self.path()
        for node_num_value in self._mp_hlevels[self._curent_map_level]:
            node_num, value = node_num_value
            position = QPointF(path.elementAt(node_num))
            # print(position)
            self.hlevel_labels[node_num] = PolylineLevelNumber(value, self)
            self.hlevel_labels[node_num].setPos(position)

    def update_hlevel_labels(self):
        # update numbers positions when nodes are moved around
        if self.hlevel_labels is None:
            return
        path = self.path()
        for node_num in self.hlevel_labels:
            self.hlevel_labels[node_num].setPos(QPointF(path.elementAt(node_num)))

    def delete_hlevel_label(self, node_num):
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
        for hl in self.hlevel_labels:
            self.scene().removeItem(self.hlevel_labels[hl])
            del self.hlevel_labels[hl]
        self.hlevel_labels = None

    @staticmethod
    def is_point_removal_possible(num_elems_in_path):
        return all(a >= 2 for a in num_elems_in_path)


class PolygonQGraphicsPathItem(PolyQGraphicsPathItem):

    def __init__(self, projection, *args, **kwargs):
        super(PolygonQGraphicsPathItem, self).__init__(projection, *args, **kwargs)
        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable)
        self.setAcceptHoverEvents(True)

    def set_mp_data(self, given_level, data):
        if isinstance(given_level, str):
            level = int(given_level[-1])
        else:
            level = given_level
        qpainterpaths_to_add = []
        for nodes in data:
            nodes_qpointfs = [a.get_canvas_coords_as_qpointf() for a in nodes]
            # gdyby sie okazalo ze polygone musi byc zamkniety, ale chyba nie musi
            # nodes_qpointfs.append(nodes_qpointfs[0])
            qpp = QPainterPath()
            qpp.addPolygon(QPolygonF(nodes_qpointfs))
            if qpainterpaths_to_add and all(qpainterpaths_to_add[-1].contains(a) for a in nodes_qpointfs):
                # and all(outer_polygone.containsPoint(a, Qt.OddEvenFill) for a in nodes_qpointfs):
                qpainterpaths_to_add[-1] = qpainterpaths_to_add[-1].subtracted(qpp)
            else:
                qpainterpaths_to_add.append(qpp)
        polygon = QPainterPath()
        for poly in qpainterpaths_to_add:
            polygon.addPath(poly)
        self._mp_data[level] = polygon
        if self.path().isEmpty():
            self.setPath(polygon)

    @staticmethod
    def is_point_removal_possible(num_elems_in_path):
        return all(a >= 3 for a in num_elems_in_path)

    def add_label(self, label):
        self.label = PolygonLabel(label, self)

    def update_label_pos(self):
        if self.label is not None:
            self.label.setPos(self.label.get_label_pos())


class PoiLabel(QGraphicsSimpleTextItem):
    def __init__(self, string_text, parent):
        self.parent = parent
        super().__init__(string_text, parent)
        px0, py0, pheight, pwidth = parent.boundingRect().getRect()
        self.setPos(pheight, pwidth/2)
        self.setZValue(20)

    def paint(self, painter, option, widget):
        if self.parent.scene().get_viewer_scale() > IGNORE_TRANSFORMATION_TRESHOLD:
            self.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)
        else:
            self.setFlag(QGraphicsItem.ItemIgnoresTransformations, False)
        super().paint(painter, option, widget)


class PolylineLabel(QGraphicsSimpleTextItem):
    def __init__(self, string_text, parent):
        self.parent = parent
        super().__init__(string_text, parent)
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

    def paint(self, painter, option, widget):
        self.set_transformation_flag()
        super().paint(painter, option, widget)

    def set_transformation_flag(self):
        if self.parent.scene().get_viewer_scale() > IGNORE_TRANSFORMATION_TRESHOLD:
            self.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)
        else:
            self.setFlag(QGraphicsItem.ItemIgnoresTransformations, False)


class PolygonLabel(QGraphicsSimpleTextItem):
    def __init__(self, string_text, parent):
        self.parent = parent
        super().__init__(string_text, parent)
        self.setPos(self.get_label_pos())
        self.setZValue(20)
        self.set_transformation_flag()

    def get_label_pos(self):
        return self.parent.boundingRect().center()

    def paint(self, painter, option, widget):
        self.set_transformation_flag()
        super().paint(painter, option, widget)

    def set_transformation_flag(self):
        if self.parent.scene().get_viewer_scale() > IGNORE_TRANSFORMATION_TRESHOLD:
            self.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)
        else:
            self.setFlag(QGraphicsItem.ItemIgnoresTransformations, False)


class PolylineAddressNumber(QGraphicsSimpleTextItem):
    def __init__(self, text, parent):
        self.parent = parent
        super().__init__(text, parent)

    def paint(self, painter, option, widget):
        if self.parent.scene().get_viewer_scale() > IGNORE_TRANSFORMATION_TRESHOLD:
            self.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)
        else:
            self.setFlag(QGraphicsItem.ItemIgnoresTransformations, False)
        super().paint(painter, option, widget)


class PolylineLevelNumber(QGraphicsSimpleTextItem):
    def __init__(self, text, parent):
        self.parent = parent
        if not isinstance(text, str):
            text = str(text)
        super().__init__(text, parent)

    def paint(self, painter, option, widget):
        if self.parent.scene().get_viewer_scale() > IGNORE_TRANSFORMATION_TRESHOLD:
            self.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)
        else:
            self.setFlag(QGraphicsItem.ItemIgnoresTransformations, False)
        super().paint(painter, option, widget)


class GripItem(QGraphicsPathItem):
    # https://stackoverflow.com/questions/77350670/how-to-insert-a-vertex-into-a-qgraphicspolygonitem
    _pen = QPen(QColor('green'), 2)
    _pen.setCosmetic(True)
    inactive_brush = QBrush(QColor('green'))
    square = QPainterPath()
    square.addRect(-5, -5, 10, 10)
    active_brush = QBrush(QColor('red'))
    # keep the bounding rect consistent
    _boundingRect = square.boundingRect()

    def __init__(self, pos, parent):
        super().__init__()
        self.parent = parent
        self.setPos(pos)
        self.setParentItem(parent)
        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable
                      | QGraphicsItem.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setPath(self.square)
        self.setPen(self._pen)
        self.setZValue(100)
        self._setHover(False)
        self.hover_drag_mode = False
        self.set_transformation_flag()
        # self.setAttribute(Qt.WA_NoMousePropagation, False)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            self.parent.move_grip(self)
        return super().itemChange(change, value)

    def _setHover(self, hover):
        if hover:
            self.setBrush(self.active_brush)
            self.hover_drag_mode = True
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
        else:
            super().mousePressEvent(event)

    def wheelEvent(self, event):
        print('kolko myszy')
        if event.modifiers() == Qt.ControlModifier:
            pass
        else:
            super().wheelEvent(event)

    def paint(self, painter, option, widget=None):
        self.set_transformation_flag()
        super().paint(painter, option, widget=widget)

    def set_transformation_flag(self):
        if self.parent.scene().get_viewer_scale() > IGNORE_TRANSFORMATION_TRESHOLD:
            self.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)
        else:
            self.setFlag(QGraphicsItem.ItemIgnoresTransformations, False)


class DirectionArrowHead(QGraphicsPathItem):
    pen = QPen(Qt.black, 3)
    brush = QBrush(Qt.black)
    # pen.setCosmetic(True)

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

    def set_transformation_flag(self):
        if self.parent.scene().get_viewer_scale() > IGNORE_TRANSFORMATION_TRESHOLD:
            self.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)
        else:
            self.setFlag(QGraphicsItem.ItemIgnoresTransformations, False)

    def paint(self, painter, option, widget=None):
        self.set_transformation_flag()
        super().paint(painter, option, widget=widget)


class MapRuler(QGraphicsPathItem):
    pen = QPen(Qt.black, 2)
    pen.setCosmetic(True)
    brush = QBrush(Qt.black)
    ruler = QPainterPath()
    screen_coord_1 = QPoint(10, 10)
    screen_coord_2 = QPoint(50, 10)

    def __init__(self,  map_render, projection):
        self.map_render = map_render
        self.projection = projection
        super().__init__()
        self.geo_distance = None
        self.distance_label = None
        self.draw_ruler()
        self.screen_dpi = self.map_render.physicalDpiX()

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
        self.distance_label = QGraphicsSimpleTextItem(label, self)
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
            self.gripItems.append(GripItem(p, self))

    def addPoint(self, pos):
        self.insertPoint(len(self.gripItems), pos)

    def insertPoint(self, index, pos):
        poly = list(self.polygon())
        poly.insert(index, pos)
        self.gripItems.insert(index, GripItem(pos, self))
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
