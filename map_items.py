from collections import OrderedDict
# import projection
# from singleton_store import Store
# from PyQt5.QtSvg import QGraphicsSvgItem
from PyQt5.QtWidgets import QGraphicsItemGroup
from PyQt5.QtWidgets import QGraphicsPixmapItem, QGraphicsEllipseItem, QGraphicsPathItem, QGraphicsItem, \
    QGraphicsPolygonItem, QStyle, QGraphicsSimpleTextItem
from PyQt5.QtCore import QPointF, Qt
from PyQt5.QtGui import QPainterPath, QPolygonF, QBrush, QPen, QColor, QPixmap, QPainterPathStroker


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
            if number_keyname[1] in ('Type', 'Label', 'Label2', 'Label3', 'DirIndicator', 'EndLevel', 'StreetDesc',
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
        # https://stackoverflow.com/questions/77350670/how-to-insert-a-vertex-into-a-qgraphicspolygonitem

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

class PolylineQGraphicsPathItem(QGraphicsPathItem):
    def __init__(self, *args, **kwargs):
        # self.pen_before_hovering = None
        self.hovered = False
        # self.hovered = False
        self.selected_pen = None
        # self.hovered_pen = QPen(QColor("red"))
        super(PolylineQGraphicsPathItem, self).__init__(*args, **kwargs)
        self.orig_pen = None
        self.selected_pen = QPen(QColor("red"))
        self.selected_pen.setStyle(Qt.DotLine)
        self.hovered_over_pen = QPen(QColor('red'))
        self.hovered_over_pen.setWidth(4)

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
        self.hovered = True
        if not self.isSelected():
            self.setPen(self.hovered_over_pen)

    def hoverLeaveEvent(self, event):
        self.hovered = False
        if not self.isSelected():
            self.setPen(self.orig_pen)

    def shape(self):
        stroker = QPainterPathStroker()
        stroker.setWidth(self.pen().width())
        return stroker.createStroke(self.path())

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
        painter_path = self.parent.path()
        angle = painter_path.angleAtPercent(0.5)
        point = painter_path.pointAtPercent(0.5)
        self.setPos(point)
        self.setRotation(angle)
        self.setZValue(20)
