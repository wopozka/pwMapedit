#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import calendar
from collections import OrderedDict

from PyQt5.QtWidgets import (QGraphicsScene, QGraphicsPathItem, QGraphicsEllipseItem, QGraphicsPolygonItem,
                             QGraphicsRectItem, QGraphicsItem)
from PyQt5.QtWidgets import QGraphicsPixmapItem, QGraphicsSimpleTextItem, QGraphicsItemGroup, QGraphicsLineItem
from PyQt5.QtGui import QPainterPath, QPolygonF, QBrush, QPen, QColor, QPixmap, QPainter
from PyQt5.QtCore import QPointF, Qt, QLineF
import platform

import commands
import modes
import math
import projection
import tempfile
import misc_functions
import os.path
import map_items
import map_object_properties
import pwmapedit_constants
from datetime import datetime

class mapCanvas(QGraphicsScene):
    web_layer_z_value = 1
    closest_node_circle_definition = QGraphicsEllipseItem(- 10, - 10, 20, 20)
    closest_node_circle_definition.setZValue(150)
    closest_node_circle_definition.setPen(QPen(QColor("blue")))
    closest_node_circle_definition.setBrush(QBrush(QColor("blue")))
    closest_node_circle_definition.setFlag(QGraphicsPathItem.ItemIgnoresTransformations, True)
    closest_node_circle_definition.setOpacity(0.5)
    closest_node_min_distance = 15
    closest_node_circle_pen = QPen(QColor("blue"))
    closest_node_circle_brush = QBrush(QColor("blue"))
    """The main map canvas definitions residue here"""
    def __init__(self, parent, *args, projection=None, undo_redo_stack=None, **kwargs):
        self.parent = parent
        self.properties_dock = self.parent.properties_dock
        super(mapCanvas, self).__init__(*args, **kwargs)
        self.undo_redo_stack = undo_redo_stack
        self.projection = None
        if projection is not None:
            self.projection = projection
        self.map_objects_properties = map_object_properties.MapObjectsProperties()
        # self.apply_bindings()
        self.operatingSystem = platform.system()
        self.polygonFill = 'solid' #there are 2 options avialable here, solid and transparent
        self.selected_objects = []
        # self.mode = modes.selectMode(self)
        self.mode_name = 'select'
        self.current_map_level = 0

        # selection changed slot conection
        self.selectionChanged.connect(self.selection_change_actions)

        self.web_layer_graphics = None
        self.web_layer_graphic_zoom = -1

        # closest node circle
        self._closest_node_circle = None
        self._stick_to_neighbours_nodes = False

    def closest_point_to_point(self, event_pos, excluded_item=None):
        circle = QPainterPath()
        circle.addEllipse(event_pos, 30, 30)
        items_under_circle = self.items(circle)
        if excluded_item in items_under_circle:
            items_under_circle.remove(excluded_item)
        items_under_circle = [a for a in items_under_circle if (isinstance(a, map_items.PolylineQGraphicsPathItem)
                                                                or isinstance(a, map_items.PolygonQGraphicsPathItem))]
        if items_under_circle:
            point_node_dist = []
            for item_under_c in items_under_circle:
                for polygon in item_under_c.get_polygons_from_path(item_under_c.path()):
                    for point in polygon:
                        point_event_l = QLineF(event_pos, point)
                        if point_event_l.length() <= self.closest_node_min_distance:
                            point_node_dist.append(point_event_l)
            if point_node_dist:
                closes_point = sorted(point_node_dist, key=lambda a: a.length())[0]
                self._closest_node_circle = self.closest_node_circle_definition
                self._closest_node_circle.setPos(closes_point.p2())
                self.addItem(self._closest_node_circle)

    def closest_node_circle_remove(self):
        if self._closest_node_circle is not None:
            self.removeItem(self._closest_node_circle)
            self._closest_node_circle = None

    def closest_node_circle_position(self):
        return None if self._closest_node_circle is None else self._closest_node_circle.pos()

    def command_create_poi(self, position):
        # creates new POI object
        new_poi = map_items.PoiAsPixmap(None, map_objects_properties=self.map_objects_properties,
                                        projection=self.projection)
        _pos = self.projection.canvas_to_geo(position.x(), position.y())
        obj_data = OrderedDict({(0, 'Type'): '0x0', (1, 'Data0'): str(_pos)})
        new_poi.set_data('', obj_data)
        new_poi.set_mp_data()
        command = commands.CreateNewPoiCmd(new_poi, self.parent.map_objects, self, 'Utwórz POI')
        self.undo_redo_stack.push(command)

    def stick_to_neighbours(self):
        return self._stick_to_neighbours_nodes

    def get_item_ignores_transformations(self):
        return self.self.views()[0].get_item_ignores_transformations()

    def get_pw_mapedit_mode(self):
        return self.parent.get_mapedit_mode()

    def get_viewer_scale(self):
        # if there is a view connected return real scale
        if self.views():
            return self.views()[0].map_scale
        # otherwise return 1
        return 1.0

    def get_viewer_physicalDpiX(self):
        return self.views()[0].physicalDpiX()

    def get_viewer_corners_geo_coordinates(self):
        viewer = self.views()[0]
        left_top_corner = viewer.mapToScene(viewer.sceneRect().upperLeft())
        right_bottom_corner = viewer.mapToScene(viewer.sceneRect().bottomRight())
        print(left_top_corner, right_bottom_corner)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Control:
            self._stick_to_neighbours_nodes = True
            print('Wlaczam przyciaganie')
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Control:
            self._stick_to_neighbours_nodes = False
            print('wylaczam przyciaganie')
        super().keyReleaseEvent(event)

    def set_canvas_rectangle(self, map_bounding_box):
        start_x, start_y = self.projection.geo_to_canvas(map_bounding_box['N'], map_bounding_box['W'])
        end_x, end_y = self.projection.geo_to_canvas(map_bounding_box['S'], map_bounding_box['E'])
        self.setSceneRect(start_x, start_y, end_x-start_x, end_y-start_y)
        # print('start_x: %s, start_y: %s, end_x: %s, end_y: %s' %(start_x, start_y, end_x, end_y))
        return

    def draw_all_objects_on_map(self, obj_list):
        for num, obj in enumerate(obj_list):
            self.draw_object_on_map(obj)
        # print('Ilosc wszystkich polygonow: %s, ilosc dodanych: %s, ilosć odjetych: %s.'
        #       % (self.num_polygons, self.num_polygons_added, self.num_polygons_subtracted))

    def draw_object_on_map(self, mapobject):
        if isinstance(mapobject, map_items.PoiAsPath) or isinstance(mapobject, map_items.PoiAsPixmap) \
                or isinstance(mapobject, map_items.AddrLabel):
            # group_item = QGraphicsItemGroup()
            # nodes = mapobject.obj_datax_get('Data0')[0]
            # x, y = nodes[0].get_canvas_coords()
            # poi_icon = self.map_objects_properties.get_poi_icon(mapobject.get_param('Type'))
            # if isinstance(poi_icon, QPainterPath):
            #     poi_icon_brush = self.map_objects_properties.get_nonpixmap_poi_brush(mapobject.get_param('Type'))
            # elif isinstance(poi_icon, QPixmap):
            #     poi_icon_brush = False
            # elif isinstance(poi_icon, str):
            #     poi_icon_brush = False
            # mapobject.set_mp_data()
            # if isinstance(poi_icon_brush, QBrush):
            #     mapobject.setBrush(poi_icon_brush)
            self.addItem(mapobject)
            mapobject.add_label()
            mapobject.set_map_level()
        elif isinstance(mapobject, map_items.PolylineQGraphicsPathItem):
            # https://stackoverflow.com/questions/47061629/how-can-i-color-qpainterpath-subpaths-differently
            # pomysl jak narysowac  roznokolorowe może dla mostow inne grubosci?
            # polyline_path_item = map_items.PolylineQGraphicsPathItem(self.projection)
            # for data_x in mp_data_range:
            #     if mapobject.get_datax(data_x):
            # mapobject.set_mp_data()
            #    if mapobject.get_hlevels(data_x):
            # mapobject.set_mp_hlevels()
            self.addItem(mapobject)
            if mapobject.get_param('DirIndicator'):
                mapobject.set_mp_dir_indicator(True)
            mapobject.add_label()
            # if mapobject.get_param('EndLevel'):
            #     polyline_path_item.set_mp_end_level(mapobject.get_param('EndLevel'))
            mapobject.set_map_level()
            mapobject.set_pen()
        elif isinstance(mapobject, map_items.PolygonQGraphicsPathItem):
            # polygon = map_items.PolygonQGraphicsPathItem(self.projection)
            # for data_x in mp_data_range:
            #     if mapobject.get_datax(data_x):
            # mapobject.set_mp_data()
            mapobject.set_z_value()
            mapobject.set_pen()
            mapobject.set_brush()
            self.addItem(mapobject)
            mapobject.add_label()
            # if mapobject.get_param('EndLevel'):
            #     polygon.set_mp_end_level(mapobject.get_param('EndLevel'))
            mapobject.set_map_level()
        else:
            pass

    def delete_object(self):
        mode = self.get_pw_mapedit_mode()
        if mode == pwmapedit_constants.Tools.SELECT_OBJECTS:
            if len(self.selectedItems()):
                command = commands.DeleteObjectsCmd(self.selectedItems(),
                                                    self.parent.map_objects, 'Usuwanie obiektu z mapy')
                self.undo_redo_stack.push(command)

    def remove_all_objects_from_map(self):
        print('usuwam wszystkie obiekty')
        self.delete('all')
        self.update_idletasks()
        print('usuniete')

    def change_projection(self, proj, map_bounding_box, map_object_list):
        old_proj = self.projection
        if proj == 'UTM':
            newProj = projection.UTM(map_bounding_box)
            if not newProj.calculate_data_offset():
                self.projection = newProj
                print(self.projection.projectionName)
                self.remove_all_objects_from_map()
                self.draw_all_objects_on_map(map_object_list)
                return 0
            else:
                return 1
        elif proj == 'Mercator':
            self.projection = projection.Mercator(map_bounding_box)
            print(self.projection.projectionName)
            self.remove_all_objects_from_map()
            self.draw_all_objects_on_map(map_object_list)
            return 0
        else:
            return 0

    def set_map_level(self, map_level):
        self.setFocus(False)
        if isinstance(map_level, str):
            map_level = int(map_level)
        if map_level == self.current_map_level:
            return
        self.current_map_level = map_level
        self.clearSelection()
        start = datetime.now().replace(microsecond=0)
        # self.views()[0].setInteractive(False)
        map_items = self.items()
        one_perc = len(map_items) // 100
        self.parent.update_progress_bar('set_maximum', len(map_items))
        self.parent.update_progress_bar('set_value', 0)
        for item_num, item in enumerate(map_items):
            if item._accept_map_level_change:
                item.set_map_level()
            if item_num % one_perc == 0:
                self.parent.update_progress_bar('set_value', item_num)
                # self.parent.update()
        # self.views()[0].setInteractive(True)
        self.parent.update_progress_bar('set_value', len(map_items))
        print('num screen items: %s' % len(map_items))
        print('realizacja: %s' % (datetime.now().replace(microsecond=0) - start))

    def get_map_level(self):
        return self.current_map_level

    def get_undo_redo_stack(self):
        return self.undo_redo_stack

    def disable_maplevel_shortcuts(self):
        self.parent.disable_maplevel_shortcuts()

    def enable_maplevel_shortcuts(self):
        self.parent.enable_maplevel_shortcuts()

    def selection_change_actions(self):
        self.properties_dock.set_dock_off()
        mode = self.get_pw_mapedit_mode()
        if mode == pwmapedit_constants.Tools.SELECT_OBJECTS:
            if len(self.selectedItems()) == 1:
                self.properties_dock.set_map_object_id(self.selectedItems()[0])
                self.properties_dock.fill_map_object_properties()
        elif mode == pwmapedit_constants.Tools.EDIT_NODES:
            selected_items = self.selectedItems()
            print(selected_items, self.selected_objects)
            if any(isinstance(a, QGraphicsPixmapItem) for a in selected_items):
                for obj in self.selected_objects:
                    obj.undecorate()
                return
            if any(hasattr(a, 'hover_drag_mode') and a.hover_drag_mode for a in selected_items):
                print('selekcja sie zmienila na uchwyty')
                print('wypelniam docka, ale tylko noda')
                self.properties_dock.set_map_object_id(self.selectedItems()[0])
                self.properties_dock.fill_map_object_properties()
                return
            # przypadku gdy obiekt juz jest w trybie edycji wezlow nie rob nic. Zachodzi gdy mamy kliknięty uchwyt
            # a potem klikniemy z shiftem na podswietlony obiekt tak aby dodac wezel. Wtedy zmienia sie selekcja na nowy
            # obiekt ktory ma juz uchwyty. Nie rob nic w takim przypadku.
            if selected_items and selected_items[0].decorated():
                return
            if self.selected_objects:
                print('usuwam dekoracje selection change', self.selected_objects)
                for obj in self.selected_objects:
                    obj.undecorate()
            self.selected_objects = selected_items
            for obj in self.selected_objects:
                obj.decorate()

    def remove_web_layer_graphics(self):
        if self.web_layer_graphics is None:
            return
        for graphic_item in self.web_layer_graphics:
            self.removeItem(self.web_layer_graphics[graphic_item])
        self.web_layer_graphics.clear()
        self.web_layer_graphics = None

    def set_web_layer_graphic(self, tile_def, zoom):
        if zoom != self.web_layer_graphic_zoom:
            self.remove_web_layer_graphics()
            self.web_layer_graphic_zoom = zoom
        if self.web_layer_graphics is None:
            self.web_layer_graphics = dict()
        if tile_def.file_path in self.web_layer_graphics:
            # nie dodawaj ponownie dodanego juz obrazka
            return
        pixmap = QPixmap(tile_def.file_path)
        if pixmap.isNull():
            print(f'pixmap jest Null, usuwam plik: {tile_def.file_path}.')
            try:
                os.remove(tile_def.file_path)
            except PermissionError:
                print(f'PermissionError. Nie mogłem usunąć pixmapy: {tile_def.file_path}. Pozostawiam.')
            except FileNotFoundError:
                print(f'FileNotFoundError: nie znalazłem pliku: {tile_def.file_path}.')
            return
        web_layer_pic = QGraphicsPixmapItem(pixmap)
        x, y = self.projection.geo_to_canvas(tile_def.left_top_lat, tile_def.left_top_lon)
        x2, y2 = self.projection.geo_to_canvas(tile_def.right_bott_lat, tile_def.right_bott_lon)
        web_layer_pic.setPos(x, y)
        # tu raz dostałem division by zero, wiec czasami obrazek nie zaladuje sie, nie wiadomo czemu. Trzeba
        # sprawdzac czy nie null
        web_layer_pic.setScale((x2 - x)/web_layer_pic.boundingRect().width())
        self.addItem(web_layer_pic)
        self.web_layer_graphics[tile_def.file_path] = web_layer_pic

    def set_undo_redo_stack(self, undo_redo_stack):
        self.undo_redo_stack = undo_redo_stack

    def set_projection(self, _projection):
        self.projection = _projection
