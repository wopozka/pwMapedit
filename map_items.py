import time
from collections import namedtuple
# from singleton_store import Store
# from PyQt5.QtSvg import QGraphicsSvgItem
# from PyQt5.QtWidgets import QGraphicsItemGroup
from PyQt6.QtWidgets import QGraphicsPixmapItem, QGraphicsRectItem, QGraphicsPathItem, QGraphicsItem,     QGraphicsPolygonItem, QStyle, QGraphicsSimpleTextItem, QGraphicsEllipseItem, QGraphicsLineItem
from PyQt6.QtCore import QPointF, Qt, QLineF, QPoint
from PyQt6.QtGui import QPainterPath, QPolygonF, QBrush, QPen, QColor, QPainterPathStroker, QCursor, QVector2D, QFont
from datetime import datetime
from pwmapedit_constants import (IGNORE_TRANSFORMATION_TRESHOLD, SCALE_WITHOUT_LABELS, SCALE_WITHOUT_POIS,
                                 SCALE_WITHOUT_SMALL_POLYS, SMALL_POLY_PERIMETER)
import commands
import itertools
import pwmapedit_constants
from pwm_core import geometry, mp_format, mp_file
from pwm_core.data_x import Data_X, MergeError
from pwm_core.map_object import BasicMapItem

Closest_Point = namedtuple('Closest_Point', ['distance', 'segment_pos', 'path_num', 'coord_index'])
Grip_Index = namedtuple('Grip_Index', ['poly_num', 'node_index'])

# kolory numerow adresowych: glowne (z pliku) i interpolowane
LEFT_SIDE_NUM_MAIN = Qt.GlobalColor.blue
LEFT_SIDE_NUM_INTER = Qt.GlobalColor.red
RIGHT_SIDE_NUM_MAIN = Qt.GlobalColor.blue
RIGHT_SIDE_NUM_INTER = Qt.GlobalColor.red


def to_qpointf(point):
    """Zamiana punktu z danych (Node, Point) na QPointF."""
    return QPointF(point.x(), point.y())


class PoiAsPixmap(BasicMapItem, QGraphicsPixmapItem):
    _accept_map_level_change = True
    # typ ostatnio wybrany przez uzytkownika dla tego rodzaju obiektu, nadawany nowo tworzonym obiektom
    last_used_type = 0x0

    # basic class for poi with pixmap icon
    def __init__(self, map_obj_id, map_objects_properties=None, _projection=None):
        # super(PoiAsPixmap, self).__init__(map_objects_properties=map_objects_properties, projection=projection)
        BasicMapItem.__init__(self, map_obj_id, map_objects_properties=map_objects_properties, _projection=_projection)
        QGraphicsPixmapItem.__init__(self)
        # używane do zapisania pozycji wyjsciowej obiektu podczas przesuwania myszka
        self.recorded_pos = None
        # potrzebujemy tego aby sprawdzić czy podczas przesuwania myszką obiektu można już go ruszać
        self._mouse_press_scene_pos = None
        self._movable = False
        # potrzebujemy tego w przypadku wklejania obiektu do nowego miejsca. Tak aby wkleić go w położeniu myszki
        self._mouse_release_scene_pos = None
        self.label = None
        # etykieta tworzona leniwie - dopiero gdy POI jest rysowany w skali, w ktorej etykiety sa widoczne
        self._label_pending = False
        self._mp_data = [None, None, None, None, None]
        # self._mp_end_level = 0
        self._mp_label = None
        # setting level 4, makes it easier to handle levels when file is loaded
        self._current_map_level = 4
        self.set_z_value()
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable | QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
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
        command = commands.SelectModeMovePoi(self, self.recorded_pos, 'Przesun POI')
        self.scene().undo_redo_stack.push(command)

    def command_update_comment(self, new_comment):
        command = commands.UpdateComment(self, new_comment, 'Zmiana komentarza')
        self.scene().undo_redo_stack.push(command)

    def command_update_extras(self, new_extras):
        command = commands.UpdateExtras(self, new_extras, 'Zmiana extras')
        self.scene().undo_redo_stack.push(command)

    def command_update_endlevel(self, new_endlevel):
        command = commands.SelectModeSetEndlevel(self, new_endlevel, 'Zmiana endlevel')
        self.scene().undo_redo_stack.push(command)

    def command_update_labels(self, label_num, new_label):
        command = commands.UpdateLabel123(self, label_num, new_label, 'Zmień label')
        self.scene().undo_redo_stack.push(command)

    def command_update_address(self, new_value, description):
        command = commands.UpdateAddressComponents(self, new_value, description)
        self.scene().undo_redo_stack.push(command)

    def command_update_type(self, new_type):
        PoiAsPixmap.last_used_type = new_type
        command = commands.UpdatePoiType(self, new_type, f'Edycja type POI na: {new_type}')
        self.scene().undo_redo_stack.push(command)

    def highlight_when_hoverover(self):
        if self.scene().get_viewer_scale() * 10 < IGNORE_TRANSFORMATION_TRESHOLD:
            return False
        return True

    def paint(self, painter, option, widget):
        if self.set_transformation_flag():
            self.update()
        if self._label_pending and self.scene().get_viewer_scale() >= SCALE_WITHOUT_LABELS:
            self.scene().request_pending_labels(self)
        if self.scene().get_viewer_scale() >= SCALE_WITHOUT_POIS:
            super().paint(painter, option, widget)

    def set_transformation_flag(self):
        if self.scene() is None:
            return False
        if self.scene().get_viewer_scale() > IGNORE_TRANSFORMATION_TRESHOLD:
            if not bool(self.flags() & QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations):
                self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
                return True
        else:
            if bool(self.flags() & QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations):
                self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, False)
                return True
        return False

    def set_map_level(self):
        # nie ustawiamy tu flagi ItemIgnoresTransformations (set_transformation_flag) - robi to leniwie paint, tylko
        # dla rysowanych POI. Przestawianie jej naraz na wszystkich POI jest w indeksie BSP Qt kwadratowe (zdejmowanie
        # flagi z setek tysiecy POI przy skali < 1 trwalo ok. minuty)
        level = self.scene().get_map_level()
        if self._mp_data[level] is not None:
            self.setPos(self._mp_data[level])
            self.setVisible(True)
        elif self._mp_data[level] is None and self.get_endlevel() < level:
            self.setVisible(False)
        elif self._mp_data[level] is None and self.get_endlevel() >= level:
            self.setVisible(True)
        self._current_map_level = level
        self.update()
        return

    def set_mp_data(self):
        for given_level in ('Data0', 'Data1', 'Data2', 'Data3', 'Data4'):
            data = self.get_datax(given_level)
            if not data:
                continue
            if self.pixmap().isNull():
                self.set_pixmap()
            level = int(given_level[-1])
            node = data[0]
            x, y = node[0].get_canvas_coords()
            self._mp_data[level] = QPointF(x, y)
            if self.pos().isNull():
                self.setPos(self._mp_data[level])
                self.current_data_x = level

    def set_projection(self, _projection):
        self._projection = _projection

    def set_map_objects_properties(self, _map_objects_properties):
        self._map_objects_properties = _map_objects_properties

    def set_selected(self, selected):
        if selected:
            self.set_selection_z_value()
        else:
            self.set_z_value()
        self.setSelected(selected)

    def set_z_value(self):
        self.setZValue(20)

    def set_selection_z_value(self):
        if self.zValue() < pwmapedit_constants.SELECTED_OBJECT_Z_VAL:
            self.setZValue(self.zValue() + pwmapedit_constants.SELECTED_OBJECT_Z_VAL)

    def __str__(self):
        return f'<POI, Object ID: {self._id}, Type: {self._map_type}>'

    def add_label(self):
        # etykiet POI sa setki tysiecy, a widac je dopiero przy przyblizeniu. Tutaj tylko zaznaczamy, ze etykiete
        # trzeba utworzyc, tworzy ja create_pending_labels wywolywane przez scene (patrz paint)
        label = self.get_label1()
        if label is not None and label:
            self._label_pending = True
            self.update()

    def create_pending_labels(self):
        if not self._label_pending:
            return
        self._label_pending = False
        label = self.get_label1()
        if label is not None and label:
            self.label = PoiLabel(label, self)
            if self._mp_label is None:
                self._mp_label = label

    def set_brush(self):
        pass

    def set_pixmap(self):
        self.setPixmap(self._map_objects_properties.get_poi_icon(self.get_type()))

    @staticmethod
    def to_mp_record_header():
        return ['[POI]']

    def decorate(self):
        pass

    def undecorate(self):
        pass

    def hoverEnterEvent(self, event):
        mode = self.scene().get_pw_mapedit_mode()
        if (mode == pwmapedit_constants.Tools.SELECT_OBJECTS and not self.isSelected()
                and self.highlight_when_hoverover()):
            self.add_hovered_shape()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.remove_hovered_shape()
        super().hoverLeaveEvent(event)

    def mouseMoveEvent(self, event):
        if not self._movable:
            dist = QLineF(self.mapToScene(event.pos()), self._mouse_press_scene_pos).length()
            if dist > pwmapedit_constants.MIN_MOVE_DISTANCE:
                self._movable = True
        else:
            super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        self.remove_hovered_shape()
        self.recorded_pos = self.pos()
        self._mouse_press_scene_pos = self.mapToScene(event.pos())
        self._movable = False
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        # potrzebujemy tego w przypadku wklejania obiektu do nowego miejsca. Tak aby wkleić go w położeniu myszki
        self._mouse_release_scene_pos = self.mapToScene(event.pos())
        self._mouse_press_scene_pos = None
        self._movable = False
        if self.recorded_pos is not None and self.pos() != self.recorded_pos:
            self.command_move_poi()
            self.recorded_pos = None
        super().mouseReleaseEvent(event)

    def remove_hovered_shape(self):
        if self.hovered_shape is not None:
            self.scene().removeItem(self.hovered_shape)
            self.hovered_shape = None

    def remove_label(self):
        self._label_pending = False
        if self.label is not None:
            self.scene().removeItem(self.label)
        self.label = None


class AddrLabel(BasicMapItem, QGraphicsSimpleTextItem):
    _accept_map_level_change = True

    def __init__(self, map_objects_properties=None, _projection=None):
        # super(AddrLabel, self).__init__(map_objects_properties=map_objects_properties, projection=projection)
        BasicMapItem.__init__(self, map_objects_properties=map_objects_properties, _projection=_projection)
        QGraphicsSimpleTextItem.__init__(self)
        self.setZValue(20)
        self.setText('__tmp__')
        self._mp_data = [None, None, None, None, None]
        # self._mp_end_level = 0
        self._mp_label = ''
        # setting level 4, makes it easier to handle levels when file is loaded
        self._current_map_level = 4
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable | QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
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
            if not bool(self.flags() & QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations):
                self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
                return True
        else:
            if bool(self.flags() & QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations):
                self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, False)
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
        self.update()
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
    closest_node_circle_definition = QGraphicsEllipseItem(- 10, - 10, 20, 20)
    closest_node_circle_definition.setZValue(150)
    closest_node_circle_definition.setPen(QPen(QColor("blue")))
    closest_node_circle_definition.setBrush(QBrush(QColor("blue")))
    closest_node_circle_definition.setFlag(QGraphicsPathItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
    closest_node_circle_definition.setOpacity(0.5)
    closest_node_min_distance = 15
    closest_node_circle_pen = QPen(QColor("blue"))
    closest_node_circle_brush = QBrush(QColor("blue"))
    selected_pen = QPen(QColor("red"))
    selected_pen.setCosmetic(True)
    selected_pen.setStyle(Qt.PenStyle.DotLine)
    selected_pen.setWidth(4)
    hovered_over_pen = QPen(QColor('red'))
    hovered_over_pen.setWidth(1)
    hovered_over_pen.setCosmetic(True)
    non_cosmetic_multiplicity = 2
    _threshold = None
    _accept_map_level_change = True

    def __init__(self, map_obj_id, map_objects_properties=None, _projection=None):
        BasicMapItem.__init__(self, map_obj_id, map_objects_properties=map_objects_properties, _projection=_projection)
        QGraphicsPathItem.__init__(self)
        self.hovered = False
        self.hover_enter_for_create_mode = False
        self.orig_pen = None
        self.node_grip_items = list()
        self.node_grip_hovered = False
        self.hovered_shape_id = None
        self.label = None
        self._perp_lines = []
        self._mp_data = [None, None, None, None, None]
        # self._mp_end_level = 0
        self._mp_label = None
        self.current_data_x = 0
        # przy dekorowaniu zapisujemy sobie numery poly (poly_num) tak aby później łatwiej uzyskać numery dla każdego
        # węzła. Z reguły to 0, 1, 2, itd w zależności od ilości polylinii
        self.decorated_poly_nums = None
        # potrzebujemy tego aby sprawdzić czy podczas przesuwania myszką obiektu można już go ruszać
        self._mouse_press_scene_pos = None
        self._movable = False
        # używane do zapisania pozycji wyjsciowej obiektu podczas przesuwania myszka
        self.recorded_pos = None
        # potrzebujemy tego w przypadku wklejania obiektu do nowego miejsca. Tak aby wkleić go w położeniu myszki
        self._mouse_release_scene_pos = None
        self._mouse_press_timestamp = None
        self._closest_node_circle = None

    @staticmethod
    def accept_map_level_change():
        return True

    # when shape is hovered over, then around the shape is formed. Let's create it.
    def add_hovered_shape(self):
        # czasami w wyniku bledu hovered_shape moze nie byc usuniety. Dlatego wiec w przypadku gdy go tworzysz, to usun
        # ten poprzedni.
        self.remove_hovered_shape()
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
        return

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
                self._closest_node_circle = self.closest_node_circle_definition
                self._closest_node_circle.setPos(closes_point.p2())
                self.scene().addItem(self._closest_node_circle)

    def _closest_point_to_poly_insert_node(self, event_pos):
        """
        Get the position along polyline/polygon where to insert a new node when insert key is pressed
        Parameters
        ----------
        event_pos: event position in scene coordinates

        Returns
        -------
        return: Closest_Point(distance, is_segment, path_num, insertion_index)

        """
        for line in self._perp_lines:
            self.scene().removeItem(line)
        self._perp_lines.clear()
        polygons = self.get_polygons_from_path(self.path())
        intersections_for_separate_paths = list()
        for path_num, points in enumerate(polygons):
            # jesli punkt wskaznik myszy jest w poblizu ostatniego albo pierwszego wezla, wtedy sprawdz, bo byc moze
            # trzeba przedluzyc polilinię. Zrób to tylko w przypadku gdy polilinia jest otwarta
            intersections = []
            if (not self.is_polygon()) and (points[0] != points[-1]):
                for pair in ((1, 0), (-2, -1,)):
                    vect = QLineF(points[pair[0]], points[pair[1]])
                    vect1 = QLineF(points[pair[0]], points[pair[1]])
                    vect1.translate(event_pos - vect.p1())
                    n_vect= vect.normalVector()
                    n_vect.translate(vect.dx(), vect.dy())
                    inter_type, inter_point = vect1.intersects(n_vect)
                    event_vect = QLineF(inter_point, event_pos)
                    vect = vect.unitVector()
                    vect.translate(-vect.p1())
                    event_vect.translate(-event_vect.p1())
                    event_vect = event_vect.unitVector()
                    if (vect.p2().x() * event_vect.p2().x() >= 0)  and (vect.p2().y() * event_vect.p2().y() >=0):
                        intersections.append(Closest_Point(QLineF(points[pair[1]], event_pos).length(),
                                                           None, path_num, pair[1]))
            p1 = points.pop(0)
            if self.is_polygon() and points[-1] != p1:  # identical to QPolygonF.isClosed()
                points.append(p1)
            for coord_index, p2 in enumerate(points, 1):
                line = QLineF(p1, p2)
                # create a perpendicular line that starts at the given pos
                perp = QLineF.fromPolar(line.length(), line.angle() + 90.0).translated(event_pos)
                intersection_type, inters = line.intersects(perp)
                if intersection_type == QLineF.IntersectionType.NoIntersection:
                    # print('no intersection continue')
                    p1 = p2
                    continue
                elif intersection_type == QLineF.IntersectionType.UnboundedIntersection:
                    perp = QLineF(event_pos, inters)
                    perp.setLength(perp.length() * 2)
                    intersection_type, inters1 = line.intersects(perp)
                    # print(f'Intersection type: {intersection_type}, inters: {inters}, inters1: {inters1}, {perp}')
                    if intersection_type == QLineF.IntersectionType.UnboundedIntersection:
                        # print('unbonded intersection points co calculate')
                        # text = QGraphicsSimpleTextItem(str(coord_index), self)
                        point_to_point_dist = QLineF(event_pos, p1).length()
                        intersections.append(Closest_Point(point_to_point_dist, 0, path_num, coord_index))
                        point_to_point_dist = QLineF(event_pos, p2).length()
                        intersections.append(Closest_Point(point_to_point_dist, 0, path_num, coord_index))
                        p1 = p2
                        continue
                intersections.append(Closest_Point(QLineF(event_pos, inters).length(), 1,
                                                   path_num, coord_index))
                # self._perp_lines.append(QGraphicsLineItem(perp, self))
                # self._perp_lines.append(QGraphicsSimpleTextItem('event_pos'))
                # print(event_pos)
                # self._perp_lines[-1].setPos(event_pos)
                p1 = p2
                # print('normal intersection')
            if intersections:
                print(sorted(intersections, key=lambda item: item[0]))
                intersections_for_separate_paths.append(min(intersections, key=lambda item: item[0]))
        if intersections_for_separate_paths:
            # return the result with the shortest distance
            return min(intersections_for_separate_paths, key=lambda item: item[0])
        return Closest_Point(-1, None, 0, -1)

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
                intersection_type, inters = line.intersects(perp)
                if intersection_type != QLineF.IntersectionType.BoundedIntersection:
                    # no intersection, reverse the perpendicular line by 180°
                    perp.setAngle(perp.angle() + 180)
                    intersection_type1, inters = line.intersects(perp)
                    if intersection_type1 != QLineF.IntersectionType.BoundedIntersection:
                        # the pos is not within the line extent, ignore it
                        p1 = p2
                        continue
                # get the distance between the given pos and the found intersection
                # point, then add it, the intersection and the insertion index to
                # the intersection list
                intersections.append(Closest_Point(QLineF(event_pos, inters).length(), inters,
                                                   path_num, coord_index))
                p1 = p2
            if intersections:
                intersections_for_separate_paths.append(min(intersections, key=lambda item: item[0]))

        if intersections_for_separate_paths:
            # return the result with the shortest distance
            return min(intersections_for_separate_paths, key=lambda item: item[0])
        return Closest_Point(-1, QPointF(), 0, -1)

    def closest_point_to_poly(self, event_pos):
        # redefined in derived classes
        return -1, QPointF(), (0, -1)

    def command_update_extras(self, new_extras):
        command = commands.UpdateExtras(self, new_extras, 'Zmiana extras')
        self.scene().undo_redo_stack.push(command)

    def command_insert_point(self, path_num, coord_num, pos):
        # index is always > 0, so the first element will always be moveTo
        polygons = self.get_polygons_from_path(self.path())
        try:
            polygon = polygons[path_num]
            if coord_num == 0:
                polygon_modified = [pos] + polygon
            elif coord_num == -1:
                polygon_modified = polygon + [pos]
            else:
                polygon_modified = polygon[:coord_num] + [pos] + polygon[coord_num:]
            polygons[path_num] = polygon_modified
        except IndexError:
            return
        command = commands.InsertNodeCmd(self, path_num, coord_num, pos, polygons, 'Dodaj nod')
        self.scene().undo_redo_stack.push(command)

    def command_move_grip2(self, grip):
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
        if self.scene().stick_to_neighbours():
            self.closest_point_to_point(grip.pos())
        # jeśli znalazłeś najbliższy nod, wtedy przesuń grip na tę pozycję, przez co obiekt zostanie do tego
        # dociągnięty
        if self.scene().stick_to_neighbours() and self._closest_node_circle is not None:
            grip.setPos(self._closest_node_circle.pos())
        command = commands.MoveGripCmd(self, grip, 'przesun wezel')
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
        # usuń kółko dociągające, bo jeśli jest może być już niepotrzebne przy self._drag_to_closes_node == False
        self.scene().closest_node_circle_remove()
        if self.scene().stick_to_neighbours():
            self.scene().closest_node_circle_draw(grip.pos(), excluded_item=self)
        # jeśli znalazłeś najbliższy nod, wtedy przesuń grip na tę pozycję, przez co obiekt zostanie do tego
        # dociągnięty
        if self.scene().stick_to_neighbours() and self.scene().closest_node_circle_position() is not None:
            grip.setPos(self.scene().closest_node_circle_position())
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

    def command_set_dirindicator(self, dirindicator):
        return

    def command_set_numeration_to_node(self, grip, num_definition):
        return

    def command_set_hlevel_to_node(self, grip, hlevel):
        return

    def command_set_route_params(self, route_params_values):
        return

    def command_split_poly(self, grip):
        return

    def command_update_comment(self, new_comment):
        command = commands.UpdateComment(self, new_comment, 'Zmiana komentarza')
        self.scene().undo_redo_stack.push(command)

    def command_update_endlevel(self, new_endlevel):
        command = commands.SelectModeSetEndlevel(self, new_endlevel, 'Zmiana endlevel')
        self.scene().undo_redo_stack.push(command)

    def command_update_labels(self, label_num, new_label):
        command = commands.UpdateLabel123(self, label_num, new_label, 'Zmień label')
        self.scene().undo_redo_stack.push(command)

    def command_update_type(self, new_type):
        return

    def create_painter_path(self, poly_lists):
        path = QPainterPath()
        for poly in poly_lists:
            pp_poly = [to_qpointf(point) for point in poly]
            if self.is_polygon() and pp_poly[0] != pp_poly[-1]:
                pp_poly.append(pp_poly[0])
            qpp = QPainterPath()
            qpp.addPolygon(QPolygonF(pp_poly))
            path.addPath(qpp)
        return path

    def _decorate(self):
        print('dekoruje polygon', 'type_polygon', self.is_polygon())
        if self.decorated():
            self.undecorate()
        # self.setZValue(self.zValue() + self.decorated_z_value)
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
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))

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
        # if not self.mode_allows_selection():
        #     return False
        return True

    def hoverEnterEvent(self, event):
        if not self.highlight_when_hoverover():
            return
        if self.decorated():
            self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
            return
        self.hovered = True
        if self.is_mode_create_mode():
            self.hover_enter_for_create_mode = True
            self.update()
            return
        if not self.isSelected() and self.mode_allows_selection():
            self.add_hovered_shape()

    def hoverLeaveEvent(self, event):
        if self.decorated():
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
            return
        self.hovered = False
        update_me = False
        if self.hover_enter_for_create_mode:
            self.hover_enter_for_create_mode = False
            update_me = True
        # if self.is_mode_create_mode():
        #     self.hover_enter_for_create_mode = False
        #     self.update()
        #     return
        if not self.isSelected():
            self.setPen(self.orig_pen)
            self.remove_hovered_shape()
            update_me = True
        if update_me:
            self.update()

    def is_mode_create_mode(self):
        mode = self.scene().get_pw_mapedit_mode()
        return mode in (pwmapedit_constants.Tools.CREATE_POLYLINE, pwmapedit_constants.Tools.CREATE_POLYGON,
                        pwmapedit_constants.Tools.CREATE_POLYLINE_CIRCLE, pwmapedit_constants.Tools.CREATE_POINT)

    def insert_key_pressed(self, event_pos):
        point_def = self._closest_point_to_poly_insert_node(event_pos)
        self.command_insert_point(point_def.path_num, point_def.coord_index, event_pos)

    def insert_point(self, path_num, coord_num, pos):
        self.command_insert_point(path_num, coord_num, pos)

    @staticmethod
    def is_point_removal_possible(num_elems_in_path):
        return False

    def is_polygon(self):
        if isinstance(self, PolygonQGraphicsPathItem):
            return True
        return False

    # def keyPressEvent(self, event):
    #     if self.scene().get_pw_mapedit_mode() == pwmapedit_constants.Tools.EDIT_NODES:
    #         dist = self._closest_point_to_poly_insert_node(self.mapToScene(event.pos()))
    #         print(dist)
    #     super().keyPressEvent(event)

    # def keyReleaseEvent(self, event):
    #     if event.key() == Qt.Key_Control:
    #         self._drag_to_closest_node = False
    #     super().keyReleaseEvent(event)

    def mode_allows_selection(self):
        if self.scene().get_pw_mapedit_mode() in (pwmapedit_constants.Tools.SELECT_OBJECTS,
                                                  pwmapedit_constants.Tools.EDIT_NODES):
            return True
        return False

    def mouseMoveEvent(self, event):
        mode = self.scene().get_pw_mapedit_mode()
        # trybie edytuj nody zachowuj sie standardowo
        if mode == pwmapedit_constants.Tools.EDIT_NODES:
            super().mouseMoveEvent(event)
            return
        elif mode == pwmapedit_constants.Tools.SELECT_OBJECTS:
            if not self._movable:
                dist = QLineF(self.mapToScene(event.pos()), self._mouse_press_scene_pos).length()
                if dist > pwmapedit_constants.MIN_MOVE_DISTANCE:
                    self._movable = True
            else:
                super().mouseMoveEvent(event)
        else:
            return

    def mousePressEvent(self, event):
        # jesli jestes w trybie tworzenia obiektow, nie rob nic tutaj
        if not self.mode_allows_selection():
            return
        self._mouse_press_timestamp = time.time()
        super().mousePressEvent(event)
        self.remove_hovered_shape()
        mode = self.scene().get_pw_mapedit_mode()
        if mode == pwmapedit_constants.Tools.EDIT_NODES:
            if event.button() == Qt.MouseButton.LeftButton and event.modifiers() == Qt.KeyboardModifier.ShiftModifier:
                closest_point = self.closest_point_to_poly(event.pos())
                print(closest_point)
                if closest_point.coord_index >= 0 and closest_point.distance <= self.threshold():
                    self.insert_point(closest_point.path_num, closest_point.coord_index, closest_point.segment_pos)
                    return
        elif mode == pwmapedit_constants.Tools.SELECT_OBJECTS:
            self._mouse_press_scene_pos = self.mapToScene(event.pos())
            self._movable = False
            self.recorded_pos = self.pos()

    def mouseReleaseEvent(self, event):
        # jesli jestes w trybie tworzenia obiektow, nie rob nic tutaj
        if not self.mode_allows_selection():
            return
        # potrzebujemy tego w przypadku wklejania obiektu do nowego miejsca. Tak aby wkleić go w położeniu myszki
        self._mouse_release_scene_pos = self.mapToScene(event.pos())
        self._mouse_press_scene_pos = None
        self._movable = False
        print('closest node circle remove')
        self.scene().closest_node_circle_remove()
        # if self._closest_node_circle is not None:
        #     self.scene().removeItem(self._closest_node_circle)
        #     self._closest_node_circle = None
        self._mouse_press_timestamp = None
        mode = self.scene().get_pw_mapedit_mode()
        if mode == pwmapedit_constants.Tools.SELECT_OBJECTS and self.recorded_pos is not None:
            if self.pos() != self.recorded_pos:
                dist = QLineF(self.pos(), self.recorded_pos).length()
                if dist > pwmapedit_constants.MIN_MOVE_DISTANCE:
                    self.command_move_item()
        self.recorded_pos = None
        super().mouseReleaseEvent(event)


    def move_grip(self, grip):
        # do be defined in child classes
        return

    def paint(self, painter, option, widget=None):
        if option.state & QStyle.StateFlag.State_Selected or self.decorated() or self.hover_enter_for_create_mode:
            self.setOpacity(0.5)
        else:
            if self.opacity() < 1:
                self.setOpacity(1)
        if option.state & QStyle.StateFlag.State_Selected or self.decorated():
            self.setPen(self.selected_pen)
        elif self.hovered and not self.hover_enter_for_create_mode and not self.decorated():
            self.setPen(self.hovered_over_pen)
        else:
            self.setPen(self.orig_pen)
        saved_option = option
        saved_option.state = QStyle.StateFlag.State_None
        super().paint(painter, saved_option, widget=widget)

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

    def remove_hlevel_labels(self, node_num):
        return

    def set_hover_over_for_address_labels(self, value):
        return

    def set_mp_data(self):
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
        self.update()
        return

    def set_brush(self):
        return

    def set_pen(self):
        return

    def set_selected(self, selected):
        if selected:
            self.set_selection_z_value()
        else:
            self.set_z_value()
        self.setSelected(selected)

    def set_z_value(self):
        return

    def set_selection_z_value(self):
        if self.zValue() < pwmapedit_constants.SELECTED_OBJECT_Z_VAL:
            self.setZValue(self.zValue() + pwmapedit_constants.SELECTED_OBJECT_Z_VAL)

    def setPen(self, pen):
        if self.orig_pen is None:
            self.orig_pen = pen
        super().setPen(pen)

    def set_projection(self, _projection):
        self._projection = _projection

    def set_map_objects_properties(self, _map_objects_properties):
        self._map_objects_properties = _map_objects_properties

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
        # self.setZValue(self.zValue() - 100)
        if self.zValue() > pwmapedit_constants.SELECTED_OBJECT_Z_VAL:
            self.set_z_value()
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable | QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.remove_interpolated_house_numbers()
        for grip_item in self.node_grip_items:
            if grip_item is not None:
                self.scene().removeItem(grip_item)
        self.node_grip_items = []
        self.set_hover_over_for_address_labels(False)
        self.hoverLeaveEvent(None)
        self.decorated_poly_nums = None
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

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
    # typ ostatnio wybrany przez uzytkownika dla tego rodzaju obiektu, nadawany nowo tworzonym obiektom
    last_used_type = 0x0

    def __init__(self, map_obj_id, map_objects_properties=None, _projection=None):
        super(PolylineQGraphicsPathItem, self).__init__(map_obj_id, map_objects_properties=map_objects_properties,
                                                        _projection=_projection)
        self.arrow_head_items = []
        self.hlevel_labels = None
        self.housenumber_labels = None
        # etykieta i numery adresowe tworzone sa leniwie - dopiero gdy linia jest rysowana w skali, w ktorej etykiety
        # sa widoczne. Flagi oznaczaja, ze maja zostac utworzone przy najblizszym takim rysowaniu
        self._label_pending = False
        self._housenumber_labels_pending = False
        self.interpolated_house_numbers_labels = None
        self._mp_hlevels = [None, None, None, None, None]
        self._mp_address_numbers = [None, None, None, None, None]
        self._mp_dir_indicator = False
        self.set_z_value()
        self.setAcceptHoverEvents(True)
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable | QGraphicsItem.GraphicsItemFlag.ItemIsMovable)

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
            angle = geometry.vector_angle(p2.x() - p1.x(), p2.y() - p1.y(),
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
        # przy duzych mapach numerow adresowych sa setki tysiecy, a widac je dopiero przy duzym przyblizeniu.
        # Tutaj tylko zaznaczamy, ze trzeba je utworzyc, tworzy je create_pending_labels wywolywane przez scene,
        # gdy linia zostanie narysowana w skali, w ktorej etykiety sa widoczne (patrz paint)
        self._housenumber_labels_pending = True
        self.update()

    def create_pending_labels(self):
        if self._label_pending:
            self._label_pending = False
            label = self.get_label1()
            if label is not None and label:
                self.label = PolylineLabel(label, self)
        if self._housenumber_labels_pending:
            self._housenumber_labels_pending = False
            self._create_housenumber_labels()
            if self.decorated():
                # dla linii w trybie edycji numery musza reagowac na najechanie myszka, patrz _decorate
                self.set_hover_over_for_address_labels(True)

    def _create_housenumber_labels(self):
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
                    adr.append(PolylineAddressNumber(position, house_numbers.left_side_number_before, self,
                                                     side='left', interpolated=False))
                if house_numbers.left_side_number_after is not None:
                    line_segment_vector = polygons_vectors[polygon_num][polygon_node_num]
                    position = self.get_numbers_position(line_segment_vector, 'left_side_number_after')
                    adr.append(PolylineAddressNumber(position, house_numbers.left_side_number_after, self,
                                                     side='left', interpolated=False))
                if house_numbers.right_side_number_before is not None:
                    line_segment_vector = polygons_vectors[polygon_num][polygon_node_num - 1]
                    position = self.get_numbers_position(line_segment_vector, 'right_side_number_before')
                    adr.append(PolylineAddressNumber(position, house_numbers.right_side_number_before, self,
                                                     side='right', interpolated=False))
                if house_numbers.right_side_number_after is not None:
                    line_segment_vector = polygons_vectors[polygon_num][polygon_node_num]
                    position = self.get_numbers_position(line_segment_vector, 'right_side_number_after')
                    adr.append(PolylineAddressNumber(position, house_numbers.right_side_number_after, self,
                                                     side='right', interpolated=False))
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
                    ihn.append(PolylineAddressNumber(num_def[0], num_def[1], self,
                                                     side=num_def[2], interpolated=True))
        if ihn:
            self.interpolated_house_numbers_labels = ihn
        else:
            self.interpolated_house_numbers_labels = None

    def add_label(self):
        # tylko zaznaczamy etykiete do utworzenia, patrz add_housenumber_labels i create_pending_labels
        label = self.get_label1()
        if label is not None and label:
            self._label_pending = True
            self.update()

    def remove_label(self):
        self._label_pending = False
        super().remove_label()

    def command_reverse_poly(self):
        print('reversing polyline')
        command = commands.ReversePolylineCmd(self, 'Odwróć polyline')
        self.scene().undo_redo_stack.push(command)

    def command_set_dirindicator(self, dirindicator):
        if dirindicator:
            command = commands.SelectModeSetDirindicator(self, dirindicator, 'Dodaj jednokierukowosc')
        else:
            command = commands.SelectModeSetDirindicator(self, dirindicator, 'Usuń jednokierukowosc')
        self.scene().undo_redo_stack.push(command)

    def command_set_numeration_to_node(self, grip, num_definition):
        command = commands.SetNumbersToNode(self, grip, num_definition, 'Ustaw numeracje dla wezla')
        self.scene().undo_redo_stack.push(command)

    def command_set_hlevel_to_node(self, grip, hlevel):
        command = commands.SetHlevelToNode(self, grip, hlevel, 'Ustaw hlevel dla wezla')
        self.scene().undo_redo_stack.push(command)

    def command_set_route_params(self, route_params_values):
        command = commands.SelectModeRouteParams(self, route_params_values)
        self.scene().undo_redo_stack.push(command)

    def command_split_poly(self, grip):
        grip_indexes = grip.get_grip_indexes()
        data12 = self.data0.split_data_x(self.current_data_x, grip_indexes.poly_num, grip_indexes.node_index)
        if data12:
            data1 = data12[0]
            data2 = data12[1]
            s_data = self.to_mp_record()
            poi_poly_type, obj_comment, obj_data = mp_format.map_strings_record_to_dict_record(s_data)
            map_object1 = PolylineQGraphicsPathItem(self.get_id(),
                                                    map_objects_properties=self._map_objects_properties,
                                                    _projection=self._projection)
            map_object1.set_data(obj_comment, obj_data)
            map_object1.data0 = data1
            map_object1.set_mp_data()
            map_object2 = PolylineQGraphicsPathItem(None, map_objects_properties=self._map_objects_properties,
                                                    _projection=self._projection)
            map_object2.set_data(obj_comment, obj_data)
            map_object2.data0 = data2
            map_object2.set_mp_data()
            command = commands.SplitPolylineCmd(self, map_object1, map_object2,
                                                self.scene().parent.map_objects, 'Podziel polyline')
            self.scene().undo_redo_stack.push(command)

    def create_merged_polyline(self, other_objects):
        """
        Tworzy nowa polylinie z polaczenia tej (pierwszej) i other_objects. Nowa linia dziedziczy id i wszystkie
        wlasciwosci tej linii, dostaje sklejone Data.
        Returns
        -------
        (PolylineQGraphicsPathItem, list of int, bool): nowa linia, pominiete poziomy Data, czy ktoras z linii
        trzeba bylo odwrocic. Raises MergeError, gdy linii nie da sie polaczyc.
        """
        merged_data, skipped_levels, reversed_any = Data_X.merge_polylines(
            [self.data0] + [obj.data0 for obj in other_objects])
        s_data = self.to_mp_record()
        poi_poly_type, obj_comment, obj_data = mp_format.map_strings_record_to_dict_record(s_data)
        merged_object = PolylineQGraphicsPathItem(self.get_id(), map_objects_properties=self._map_objects_properties,
                                                  _projection=self._projection)
        merged_object.set_data(obj_comment, obj_data)
        merged_object.data0 = merged_data
        # set_data ustawilo obwiednie pierwszej linii, zastepujemy ja obwiednia polaczonej
        merged_object.obj_bounding_box = dict(merged_data.get_obj_bounding_box())
        merged_object.set_mp_data()
        return merged_object, skipped_levels, reversed_any

    def is_oneway(self):
        route_params = self.get_route_params()
        return bool(route_params) and len(route_params) > 2 and route_params[2] == 1

    def command_update_type(self, new_type):
        PolylineQGraphicsPathItem.last_used_type = new_type
        command = commands.UpdatePolyType(self, new_type, f'Edycja type linii na: {new_type}')
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
            position_at_line_segment = 15 / line_segment_vector.length()
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
        for side in ('left', 'right',):
            for num_def in inter_num[side]:
                vector = QLineF(to_qpointf(num_def.position), to_qpointf(num_def.vector.p2())).normalVector()
                if side == 'right':
                    vector = vector.normalVector().normalVector()
                number_vector = vector.unitVector()
                number_vector.setLength(number_vector.length() * 10)
                numbers.append((number_vector, num_def.number, side))
        # for num_def in inter_num['right']:
        #     vector = QLineF(num_def.position, num_def.vector.p2()).normalVector().normalVector().normalVector()
        #     numbers.append((vector.unitVector(), num_def.number,))
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

    def set_pen(self):
        self.orig_pen = None
        pen = self._map_objects_properties.get_polyline_qpen(self.get_type())
        self.setPen(pen)

    def set_z_value(self):
        self.setZValue(10)

    def __str__(self):
        return f'<POLYLINE, Object ID: {self._id}, Type: {self._map_type}>'

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

    @staticmethod
    def to_mp_record_header():
        return ['[POLYLINE]']
    
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
        self._housenumber_labels_pending = False
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
        if self.hlevel_labels is not None:
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

    # def insert_point(self, index, pos):
    #     self.command_insert_point(index, pos)

    @staticmethod
    def is_point_removal_possible(num_elems_in_path):
        return num_elems_in_path >= 2

    def paint(self, painter, option, widget=None):
        if ((self._label_pending or self._housenumber_labels_pending)
                and self.scene().get_viewer_scale() >= SCALE_WITHOUT_LABELS):
            # nie dodajemy elementow do sceny w trakcie rysowania, scena utworzy etykiety po zakonczeniu rysowania
            self.scene().request_pending_labels(self)
        super().paint(painter, option, widget=widget)


class PolygonQGraphicsPathItem(PolyQGraphicsPathItem):
    # typ ostatnio wybrany przez uzytkownika dla tego rodzaju obiektu, nadawany nowo tworzonym obiektom
    last_used_type = 0x0

    def __init__(self, map_obj_id, map_objects_properties=None, _projection=None):
        super(PolygonQGraphicsPathItem, self).__init__(map_obj_id, map_objects_properties=map_objects_properties,
                                                       _projection=_projection)
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable | QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setAcceptHoverEvents(True)

    def command_update_type(self, new_type):
        PolygonQGraphicsPathItem.last_used_type = new_type
        command = commands.UpdatePolygonType(self, new_type, f'Edycja type polygonu na: {new_type}')
        self.scene().undo_redo_stack.push(command)

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

    @staticmethod
    def to_mp_record_header():
        return ['[POLYGON]']

    def remove_items_before_new_map_level_set(self):
        if self.label is not None:
            self.remove_label()

    def set_brush(self):
        color = self._map_objects_properties.get_polygon_fill_colour(self.get_type())
        self.setBrush(QBrush(color))

    def set_pen(self):
        self.orig_pen = None
        pen = self._map_objects_properties.get_polygon_qpen(self.get_type())
        self.setPen(pen)

    def set_z_value(self):
        self.setZValue(self._map_objects_properties.get_polygon_z_value(self.get_type()))

    def __str__(self):
        return f'<POLYGON, Object ID: {self._id}, Type: {self._map_type}>'

    def add_items_after_new_map_level_set(self):
        self.add_label()

    def decorate(self):
        self._decorate()

    def move_grip(self, grip):
        self.command_move_grip(grip)

    def paint(self, painter, option, widget=None):
        if self.scene().get_viewer_scale() <= SCALE_WITHOUT_SMALL_POLYS and self.small_poly():
            return
        super().paint(painter, option, widget=widget)

    def small_poly(self):
        return self.data0.get_perimeter() < SMALL_POLY_PERIMETER

    def remove_grip(self, grip):
        if grip in self.node_grip_items:
            self.command_remove_point(grip)

    @staticmethod
    def is_point_removal_possible(num_elems_in_path):
        # as for polygons the first and the last node is the same, then triangle formally contains 4 nodes
        # therefore something below 4 is not possible
        return num_elems_in_path >= 4

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

    # def insert_point(self, index, pos):
    #     self.command_insert_point(index, pos)


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
        if self.scene().get_viewer_scale() >= SCALE_WITHOUT_LABELS:
            super().paint(painter, option, widget)

    def set_transformation_flag(self):
        if self.scene() is None:
            return False
        if self.scene().get_viewer_scale() > IGNORE_TRANSFORMATION_TRESHOLD:
            if not bool(self.flags() & QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations):
                self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
                return True
        else:
            if bool(self.flags() & QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations):
                self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, False)
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
        angle = geometry.vector_angle(p2.x() - p1.x(), p2.y() - p1.y(), clockwise=True, screen_coord_system=True)
        return geometry.calculate_label_angle(angle)

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

    def __init__(self, position, text, parent, side='left', interpolated=False):
        self.parent = parent
        self.grip_mode = False
        self.position = position
        self.current_scale = None
        super(PolylineAddressNumber, self).__init__(str(text), parent)
        self.setText(str(text))
        qm_font = QFont()
        qm_font.setPointSize(6)
        self.setFont(qm_font)
        if side == 'left':
            if interpolated:
                self.setBrush(QBrush(LEFT_SIDE_NUM_INTER))
            else:
                self.setBrush(QBrush(LEFT_SIDE_NUM_MAIN))
        else:
            if interpolated:
                self.setBrush(QBrush(RIGHT_SIDE_NUM_INTER))
            else:
                self.setBrush(QBrush(RIGHT_SIDE_NUM_MAIN))
        # _, _, pheight, pwidth = self.boundingRect().getRect()
        # self.setTransformOriginPoint(pheight / 2, pwidth / 2)
        self.set_transformation_flag()
        self.set_pos()
        self.hovered_shape = None
        self.last_keyboard_press_time = None
        self.cursor_before_hoverover = None
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresParentOpacity, True)

    def add_hovered_shape(self):
        self.hovered_shape = QGraphicsRectItem(*self.boundingRect().getRect(), self)
        hovered_color = QColor('red')
        # hovered_color.setAlpha(50)
        hovered_over_pen = QPen(hovered_color)
        hovered_over_pen.setCosmetic(True)
        hovered_over_pen.setWidth(self.pen().width() + 1)
        self.hovered_shape.setPen(hovered_over_pen)

    def hoverEnterEvent(self, event):
        print('hover enter polyline address number')
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        self.grabKeyboard()
        self.parent.hoverLeaveEvent(event)
        self.cursor_before_hoverover = self.cursor()
        self.setCursor(QCursor(Qt.CursorShape.IBeamCursor))
        super().hoverEnterEvent(event)
        self.add_hovered_shape()
        self.last_keyboard_press_time = 0
        self.scene().disable_maplevel_shortcuts()

    def hoverLeaveEvent(self, event):
        print('hover leave polyline address number')
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

    def mousePressEvent(self, event):
        # do nothing
        return

    def mouseReleaseEvent(self, event):
        return

    def needs_reposition(self):
        if self.current_scale is None or self.current_scale != self.scene().get_viewer_scale():
            self.current_scale = self.scene().get_viewer_scale()
            return True
        return False

    def paint(self, painter, option, widget):
        self.set_pos()
        super().paint(painter, option, widget)

    def set_pos(self):
        # workoround dla setPos, tak aby mozna wykorzystac wektor jako wspolrzedna, a nie tylko sam punkt
        # przypadku gdy skalowanie sie wylacza - powyżej ustalonej skali, wtedy nalezy caly czas przeliczac
        # punkt umieszczenia numeru i pomniejszac go proporcjonalnie do skale
        if self.needs_reposition():
            _, _, pwidth, pheight = self.boundingRect().getRect()
            text_center = QPointF(-pwidth/2, -pheight/2)
            self.setPos(self.position.pointAt(1 / self.current_scale) + text_center / self.current_scale)
        # if not bool(self.flags() & QGraphicsItem.ItemIgnoresTransformations):
        #     self.setPos(position.pointAt(1 / self.scene().get_viewer_scale()) + angle_corr)
        # else:
        #     self.setPos(position.p2() + angle_corr)
        return


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
        if bool(self.flags() & QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations):
            scale = self.scene().get_viewer_scale()
        self.setPos(position + QPointF(-pwidth/scale/2, -pheight/scale/2))

    def paint(self, painter, option, widget):
        if self.scene().get_viewer_scale() >= SCALE_WITHOUT_LABELS:
            self.setPos(self.position)
            brush = QBrush(Qt.GlobalColor.yellow)
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
        self.grip_indexes = Grip_Index(*grip_indexes)
        self.parent = parent
        self.hlevel = hlevel
        self.adr_labels = []
        self.setPos(pos)
        self.setParentItem(parent)
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable | QGraphicsItem.GraphicsItemFlag.ItemIsMovable
                      | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
                      | QGraphicsItem.GraphicsItemFlag.ItemIgnoresParentOpacity)
        self.setAcceptHoverEvents(True)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setPath(self.square)
        if self.is_first_grip():
            self.setPen(self._first_grip_pen)
        else:
            self.setPen(self._pen)
        self.setZValue(100)
        self._setHover(False)
        self.hover_drag_mode = False
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
        # self.set_transformation_flag()
        _text = f'({self.grip_indexes[0]},{self.grip_indexes[1]})'
        text = QGraphicsSimpleTextItem(_text, self)
        text.setPos(1, 1)
        # self.setAttribute(Qt.WA_NoMousePropagation, False)
        # gdy klikniemy na grip wtedy polygon pod spodem staje sie transparentny. Trzeba go zapamietać, aby usunąć
        # w przypadku gdy grip opuści go
        self._polygon_to_restore_opaque = None

    def is_first_grip(self):
        return self.grip_indexes[1] == 0

    def accept_map_level_change(self):
        return False

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
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

    def get_id(self):
        return self.parent.get_id()

    def get_grip_indexes(self):
        return self.grip_indexes

    def node_grip_has_numeration(self):
        data_level = self.parent.current_data_x
        poly_num, node_num = self.grip_indexes
        return self.parent.data0.get_poly_node(data_level, poly_num, node_num).node_has_numeration()

    def node_grip_get_numeration(self):
        data_level = self.parent.current_data_x
        poly_num, node_num = self.grip_indexes
        return self.parent.data0.get_poly_node(data_level, poly_num, node_num).get_numbers_definition()

    def node_grip_get_calculated_numeration(self):
        data_level = self.parent.current_data_x
        poly_num, node_num = self.grip_indexes
        return self.parent.data0.get_calculated_housenumber_defs_for_node(data_level, poly_num, node_num)

    def node_grip_get_hlevel(self):
        data_level = self.parent.current_data_x
        poly_num, node_num = self.grip_indexes
        return self.parent.data0.get_poly_node(data_level, poly_num, node_num).get_hlevel_definition()

    def node_grip_set_numeration(self, numeration):
        self.parent.command_set_numeration_to_node(self, numeration)

    def node_grip_set_hlevel(self, hlevel):
        self.parent.command_set_hlevel_to_node(self, hlevel)

    def hoverEnterEvent(self, event):
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        self.grabKeyboard()
        self.scene().disable_maplevel_shortcuts()
        self.scene().disable_tools_actions_shortcuts()
        super().hoverEnterEvent(event)
        self._setHover(True)

    def hoverLeaveEvent(self, event):
        self.clearFocus()
        self.ungrabKeyboard()
        self.scene().enable_maplevel_shortcuts()
        self.scene().enable_tools_actions_shortcuts()
        super().hoverLeaveEvent(event)
        self._setHover(False)
        # w przypadku gdy grip został przesunięty bo został dociągnięty do węzła, wtedy ucieka spod myszy
        # w takim przypadku jeśli pojawiło się kółko dociągające wtedy usuń je bo inaczej zostawało
        if self.parent._closest_node_circle is not None:
            self.scene().removeItem(self.parent._closest_node_circle)
            self.parent._closest_node_circle = None
        # to samo dla modyfikatora ctrl,
        self.parent._stick_to_neighbours_nodes = False

    def keyPressEvent(self, event):
        if event.text() == 's':
            # print('dziele polyline na tym wezle')
            self.split_polyline()
        else:
            super().keyPressEvent(event)

    def mouseMoveEvent(self, event):
        polygons_under_cursor = [a for a in self.scene().items(self.mapToScene(event.pos())) if
                                 isinstance(a, PolygonQGraphicsPathItem)]
        if polygons_under_cursor:
            if self._polygon_to_restore_opaque is None:
                self._polygon_to_restore_opaque = polygons_under_cursor[0]
                self._polygon_to_restore_opaque.hover_enter_for_create_mode = True
            else:
                if self._polygon_to_restore_opaque != polygons_under_cursor[0]:
                    self._polygon_to_restore_opaque.hover_enter_for_create_mode = False
                    self._polygon_to_restore_opaque = polygons_under_cursor[0]
                    self._polygon_to_restore_opaque.hover_enter_for_create_mode = True
        else:
            if self._polygon_to_restore_opaque is not None:
                self._polygon_to_restore_opaque.hover_enter_for_create_mode = False
                self._polygon_to_restore_opaque = None
        super().mouseMoveEvent(event)


    def mousePressEvent(self, event):
        if (event.button() == Qt.MouseButton.LeftButton and event.modifiers() == Qt.KeyboardModifier.ControlModifier):
            # hover enter event switched off shortcuts, when remove grip, enable them at first
            self.scene().enable_maplevel_shortcuts()
            self.scene().enable_tools_actions_shortcuts()
            self.parent.setSelected(True)
            self.parent.remove_grip(self)
        elif (event.button() == Qt.MouseButton.LeftButton and event.modifiers() == Qt.KeyboardModifier.ShiftModifier):
            print('z shiftem')
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        print('kolko myszy')
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
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
            if not bool(self.flags() & QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations):
                self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
                return True
        else:
            if bool(self.flags() & QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations):
                self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, False)
                return True
        return False

    def split_polyline(self):
        # the grip is removed on splitting, then turn shortcuts again
        self.scene().enable_maplevel_shortcuts()
        self.scene().enable_tools_actions_shortcuts()
        self.parent.command_split_poly(self)

    def decorate(self):
        # simulate decorate, we can do it here, or design in future what to do
        pass

    def undecorate(self):
        # simulate undecorate, we can do it here, or design in future what to do
        pass


class DirectionArrowHead(QGraphicsPathItem):
    pen = QPen(Qt.GlobalColor.black, 1)
    brush = QBrush(Qt.GlobalColor.black)
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
            if not bool(self.flags() & QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations):
                self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
                return True
        else:
            if bool(self.flags() & QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations):
                self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, False)
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
    pen = QPen(Qt.GlobalColor.black, 2)
    pen.setCosmetic(True)
    brush = QBrush(Qt.GlobalColor.black)
    ruler = QPainterPath()
    screen_coord_1 = QPoint(10, 10)
    # screen_coord_2 = QPoint(50, 10)
    _accept_map_level_change = False
    cm_per_inch = 2.54

    def __init__(self,  map_render, projection):
        self.map_render = map_render
        self._projection = projection
        super().__init__()
        self.one_cm_geo_distance = None
        self.distance_label = None
        self.screen_dpi = self.map_render.physicalDpiX()
        print('Screen dpi: ', self.screen_dpi)
        self.draw_ruler()

    @staticmethod
    def accept_map_level_change():
        return False

    def draw_ruler(self):
        if self.distance_label is not None:
            self.remove_distance_label()
        point1 = self.map_render.mapToScene(self.screen_coord_1)
        # point2 = self.map_render.mapToScene(self.screen_coord_2)
        point2 = self.calculate_point_2()
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
        if self.one_cm_geo_distance < 1000:
            label = '%.1f m' % self.one_cm_geo_distance
        else:
            label = '%.1f km' % (self.one_cm_geo_distance / 1000)
        # print(self.geo_distance / (40 / self.map_render.physicalDpiX() * 2.54 / 100))
        self.distance_label = MapRulerLabel(label, self)
        self.distance_label.setPos(point1)
        self.distance_label.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)

    def remove_distance_label(self):
        self.scene().removeItem(self.distance_label)
        self.distance_label = None

    def move_to(self):
        self.draw_ruler()

    def scale_to(self):
        self.one_cm_geo_distance = None
        self.draw_ruler()

    def calculate_geo_distance(self):
        if self.one_cm_geo_distance is not None:
            return
        point1 = self.map_render.mapToScene(self.screen_coord_1)
        point2 = self.calculate_point_2()
        start_point = self._projection.canvas_to_geo(point1.x(), point1.y())
        end_point = self._projection.canvas_to_geo(point2.x(), point2.y())
        # end_point1 = self._projection.canvas_to_geo(point1.x() + 1, point1.y())
        self.one_cm_geo_distance = geometry.vincenty_distance(start_point, end_point)
        # print(geometry.vincenty_distance(start_point, end_point1))

    def calculate_point_2(self):
        point2 = self.screen_coord_1 + QPoint(int(self.screen_dpi/self.cm_per_inch), 0)
        return self.map_render.mapToScene(point2)

    def get_map_scale(self):
        self.calculate_geo_distance()
        return self.one_cm_geo_distance * 100


class PolygonAnnotation(QGraphicsPolygonItem):
    # https://stackoverflow.com/questions/77350670/how-to-insert-a-vertex-into-a-qgraphicspolygonitem
    _threshold = None
    _pen = QPen(QColor("green"), 2)
    normalBrush = QBrush(Qt.BrushStyle.NoBrush)
    hoverBrush = QBrush(QColor(255, 0, 0, 100))

    def __init__(self, *args):
        super().__init__()
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable | QGraphicsItem.GraphicsItemFlag.ItemIsMovable
                      | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
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
            perp = QLineF.fromPolar(self.threshold(), line.angle() + 90).translated(pos)
            if line.intersects(perp, inters) != QLineF.IntersectionType.BoundedIntersection:
                # no intersection, reverse the perpendicular line by 180°
                perp.setAngle(perp.angle() + 180)
                if line.intersects(perp, inters) != QLineF.IntersectionType.BoundedIntersection:
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
        if event.button() == Qt.MouseButton.LeftButton and event.modifiers() == Qt.KeyboardModifier.ShiftModifier:
            dist, pos, index = self.closestPointToPoly(event.pos())
            if index >= 0 and dist <= self.threshold():
                self.insertPoint(index, pos)
                return
        super().mousePressEvent(event)


def map_item_from_record(record, map_objects_properties, _projection):
    """Tworzy element sceny (POI, polylinie, polygon) z rekordu pliku MP (pwm_core.mp_file.MpRecord); None dla
    rekordow, ktorych nie obslugujemy."""
    map_object = mp_file.create_map_object(record, object_classes=MAP_ITEM_CLASSES,
                                           map_objects_properties=map_objects_properties, projection=_projection)
    if map_object is not None:
        map_object.set_mp_data()
    return map_object


MAP_ITEM_CLASSES = {
    mp_format.MAP_OBJECT_POI: PoiAsPixmap,
    mp_format.MAP_OBJECT_POLYLINE: PolylineQGraphicsPathItem,
    mp_format.MAP_OBJECT_POLYGON: PolygonQGraphicsPathItem,
}
