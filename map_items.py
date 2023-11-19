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
        args
        map_elem_data: dict, key=tuple(elem_name, elem_position), value=value
        map_objects_properties = class for map elements appearance: icons, line types, area patterns and filling
        kwargs
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
        self.routeparam = None
        self.cityname = None
        self.countryname = None
        self.countrycode = None
        self.regionname = None
        self.roadid = None
        self.zipcode = None
        self.others = OrderedDict()

        # self.obj_data = OrderedDict({'Type': '', 'Label': '', 'Label2': '', 'Label3': '',
        #                              'DirIndicator': bool, 'EndLevel': '', 'StreetDesc': '', 'HouseNumber': '',
        #                              'Phone': '', 'CityIdx': '',
        #                              'DisctrictName': '', 'Highway': '',  'Data0': Data_X(),
        #                              'Data1': Data_X(), 'Data2': Data_X(), 'Data3': Data_X(),
        #                              'Data4': Data_X(), 'RouteParam': [], 'CityName': '', 'CountryName': '',
        #                              'RegionName': '', 'RoadID': 0,
        #                              'CountryCode': '', 'ZipCode': '', 'Others': OrderedDict()})
        self.map_objects_properties = None
        if map_objects_properties is not None:
            self.map_objects_properties = map_objects_properties
        self.obj_bounding_box = {}
        if map_elem_data is not None:
            self.set_data(map_comment_data, map_elem_data)

    def __repr__(self):
        return self.obj_data

    def __str__(self):
        return str(self.obj_data)

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
        return getattr(self, parameter.lower())

    def obj_param_set(self, parameter, value):
        setattr(self, parameter.lower(), value)
        # self.obj_data[parameter] = value

    def obj_datax_get(self, dataX):
        # tymczasowo na potrzeby testow tylko jedno data
        # zwracamy liste Nodow, jesli
        datax = dataX.lower()
        if datax == 'data0':
            return self.data0.get_nodes_and_inn_outer()
        elif datax == 'data1':
            return self.data1.get_nodes_and_inn_outer()
        elif datax == 'data2':
            return self.data2.get_nodes_and_inn_outer()
        elif datax == 'data3':
            return self.data3.get_nodes_and_inn_outer()
        elif datax == 'data4':
            return self.data4.get_nodes_and_inn_outer()

    def obj_datax_set(self, data012345, data012345_val):
        datax = data012345.lower()
        if datax == 'data0':
            if self.data0 is None:
                self.data0 = Data_X()
            self.data0.add_points(self.coords_from_data_to_nodes(data012345_val))
        elif datax == 'data1':
            if self.data1 is None:
                self.data1 = Data_X()
            self.data1.add_points(self.coords_from_data_to_nodes(data012345_val))
        elif datax == 'data2':
            if self.data2 is None:
                self.data2 = Data_X()
            self.data2.add_points(self.coords_from_data_to_nodes(data012345_val))
        elif datax == 'data3':
            if self.data3 is None:
                self.data3 = Data_X()
            self.data3.add_points(self.coords_from_data_to_nodes(data012345_val))
        elif datax == 'data4':
            if self.data4 is None:
                self.data4 = Data_X()
            self.data4.add_points(self.coords_from_data_to_nodes(data012345_val))
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

    def data_values(self):
        tmp_data = OrderedDict({})
        for key in self.obj_data['DataX']:
            tmp_data[key].items()

    def get_obj_levels(self):
        return self.map_levels



class Poi_Mod(QGraphicsPixmapItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


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
        self.setPos(x, y)
        self.setZValue(20)
        self.addToGroup(poi)

# tutaj chyba lepiej byloby uzyc QPainterPath
class Polyline(BasicMapItem):
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
            self.addToGroup(graphics_path_item)


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

    def gripMoved(self, grip):
        print('ruszanm')
        if grip not in self.node_grip_items:
            return
        grip_index = self.node_grip_items.index(grip)
        self.setElementPositionAt(grip_index, grip.pos().x(), grip.pos().y())

    def removeGrip(self, grip):
        if grip in self.gripItems:
            self.removePoint(self.gripItems.index(grip))

    def paint(self, painter, option, widget=None):
        if option.state & QStyle.State_Selected:
            self.setPen(self.selected_pen)
        elif self.hovered:
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
        # path = self.path()
        # for elem_num in range(path.elementCount()):
        #     path_elem = path.elementAt(elem_num)
        #     # print(QPointF(path_elem))
        #     if path_elem.isMoveTo():
        #         print(self.projection.canvas_to_geo(path_elem.x, path_elem.y))
        #     elif path_elem.isLineTo():
        #         print(self.projection.canvas_to_geo(path_elem.x, path_elem.y))

    def add_decorators(self):
        path = self.path()
        for path_elem in (path.elementAt(elem_num) for elem_num in range(path.elementCount())):
            self.node_grip_items.append(GripItem(QPointF(path_elem), self))
            # self.node_grip_items[-1].setVisible(False)
            # self.scene().addItem(self.node_grip_items[-1])

    def decorate(self):
        elapsed = datetime.now()
        path = self.path()
        for path_elem in (path.elementAt(elem_num) for elem_num in range(path.elementCount())):
            self.node_grip_items.append(GripItem(QPointF(path_elem), self))
        # self.node_grip_items = [GripItem(QPointF(path.elementAt(elem_num)), self)
        #                         for elem_num in range(path.elementCount())]
        print(datetime.now() - elapsed)

    def undecorate(self):
        scene = self.scene()
        for grip_item in self.node_grip_items:
            scene.removeItem(grip_item)
        self.node_grip_items = []


class PolylineQGraphicsPathItem(PolyQGraphicsPathItem):
    def __init__(self, projection, *args, **kwargs):
        super(PolylineQGraphicsPathItem, self).__init__(projection, *args, **kwargs)
        self.arrow_head_items = []

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



class PolygonQGraphicsPathItem(PolyQGraphicsPathItem):
    def __init__(self, projection, *args, **kwargs):
        super(PolygonQGraphicsPathItem, self).__init__(projection, *args, **kwargs)


class PoiLabel(QGraphicsSimpleTextItem):
    def __init__(self, string_text, parent):
        self.parent = parent
        super().__init__(string_text, parent)
        px0, py0, pheight, pwidth = parent.boundingRect().getRect()
        self.setPos(pheight, pwidth/2)
        self.setZValue(20)

class PolylineLabel(QGraphicsSimpleTextItem):
    def __init__(self, string_text, parent):
        self.parent = parent
        super().__init__(string_text, parent)
        path = self.parent.path()
        num_elem = path.elementCount()
        if num_elem == 2:
            p1 = QPointF(path.elementAt(0))
            p2 = QPointF(path.elementAt(1))
        elif num_elem % 2 == 0:
            p1 = QPointF(path.elementAt(num_elem // 2 - 1))
            p2 = QPointF(path.elementAt(num_elem // 2))
        else:
            p1 = QPointF(path.elementAt(num_elem // 2))
            p2 = QPointF(path.elementAt(num_elem // 2 + 1))
        self.setPos(p1 + (p2-p1)/2)
        angle = misc_functions.vector_angle(p2.x() - p1.x(), p2.y() - p1.y(),
                                            clockwise=True, screen_coord_system=True)
        self.setRotation(self.calculate_label_angle(angle))
        self.setZValue(20)
        self.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)

    @staticmethod
    def calculate_label_angle(angle):
        return misc_functions.calculate_label_angle(angle)

    # def paint(self, painter, style, widget):
    #     print(self.parent.scale())
    #     if self.parent.scale() < 1:
    #         self.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)
    #     else:
    #         self.setFlag(QGraphicsItem.ItemIgnoresTransformations, False)
    #     super().paint(painter, style, widget)


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
        self.poly = parent
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

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            self.poly.gripMoved(self)
        return super().itemChange(change, value)

    def _setHover(self, hover):
        if hover:
            self.setBrush(self.active_brush)
        else:
            self.setBrush(self.inactive_brush)

    def boundingRect(self):
        return self._boundingRect

    def hoverEnterEvent(self, event):
        super().hoverEnterEvent(event)
        self._setHover(True)

    def hoverLeaveEvent(self, event):
        super().hoverLeaveEvent(event)
        self._setHover(False)

    def mousePressEvent(self, event):
        # if (event.button() == Qt.LeftButton and event.modifiers() == Qt.ControlModifier):
        #     self.poly.removeGrip(self)
        # else:
        print('mousePpress')
        super().mousePressEvent(event)


class DirectionArrowHead(QGraphicsPathItem):
    pen = QPen(Qt.black, 3)
    pen.setCosmetic(True)

    def __init__(self, pos, parent):
        super().__init__()
        self.poly = parent
        self.setPos(pos)
        self.setParentItem(parent)
        arrow_head = QPainterPath()
        arrow_head.moveTo(QPointF(-6, 4))
        arrow_head.lineTo(QPointF(6, 0))
        arrow_head.lineTo(QPointF(-6, -4))
        self.setPath(arrow_head)
        self.setPen(self.pen)
        self.setZValue(30)


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
        self.draw_ruler()

    def draw_ruler(self):
        point1 = self.map_render.mapToScene(self.screen_coord_1)
        point2 = self.map_render.mapToScene(self.screen_coord_2)
        if self.geo_distance is None:
            self.calculate_geo_distance(point1, point2)
            print(self.geo_distance)
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

    def move_to(self):
        self.draw_ruler()

    def scale_to(self):
        self.geo_distance = None
        self.draw_ruler()

    def calculate_geo_distance(self, point1, point2):
        start_point = self.projection.canvas_to_geo(point1.x(), point1.y())
        end_point = self.projection.canvas_to_geo(point2.x(), point2.y())
        end_point1 = self.projection.canvas_to_geo(point1.x() + 1, point1.y())
        self.geo_distance = misc_functions.vincenty_distance(start_point, end_point)
        print(misc_functions.vincenty_distance(start_point, end_point1))



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
        '''
            Get the position along the polygon sides that is the closest
            to the given point.
            Returns:
            - distance from the edge
            - QPointF within the polygon edge
            - insertion index
            If no closest point is found, distance and index are -1
        '''
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
