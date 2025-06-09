#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import calendar
from collections import OrderedDict

from PyQt6.QtWidgets import (QGraphicsScene, QGraphicsPathItem, QGraphicsEllipseItem, QGraphicsPolygonItem,
                             QGraphicsRectItem, QGraphicsItem, QApplication)
from PyQt6.QtWidgets import QGraphicsPixmapItem, QGraphicsSimpleTextItem, QGraphicsItemGroup, QGraphicsLineItem
from PyQt6.QtGui import QPainterPath, QPolygonF, QBrush, QPen, QColor, QPixmap, QPainter
from PyQt6.QtCore import QPointF, Qt, QLineF, QMimeData, QByteArray
import platform

import commands
# import modes
import math
import projection
import json
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
    closest_node_circle_definition.setFlag(QGraphicsPathItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
    closest_node_circle_definition.setOpacity(0.5)
    closest_node_min_distance = 15
    closest_node_circle_pen = QPen(QColor("blue"))
    closest_node_circle_brush = QBrush(QColor("blue"))
    """The main map canvas definitions residue here"""
    def __init__(self, parent, *args, _projection=None, undo_redo_stack=None, **kwargs):
        self.parent = parent
        self.properties_dock = self.parent.properties_dock
        super(mapCanvas, self).__init__(*args, **kwargs)
        self.undo_redo_stack = undo_redo_stack
        self._projection = None
        if _projection is not None:
            self._projection = _projection
        self._map_objects_properties = map_object_properties.MapObjectsProperties()
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

        # highlighted element
        self._highlighted_element = None

    def change_projection(self, proj, map_bounding_box, map_object_list):
        old_proj = self._projection
        if proj == 'UTM':
            newProj = projection.UTM(map_bounding_box)
            if not newProj.calculate_data_offset():
                self._projection = newProj
                print(self._projection.projectionName)
                self.remove_all_objects_from_map()
                self.draw_all_objects_on_map(map_object_list)
                return 0
            else:
                return 1
        elif proj == 'Mercator':
            self._projection = projection.Mercator(map_bounding_box)
            print(self._projection.projectionName)
            self.remove_all_objects_from_map()
            self.draw_all_objects_on_map(map_object_list)
            return 0
        else:
            return 0

    def clearSelection(self):
        # jesli mamy podswietlony element (map_obj_properties_dockwidget, elements) to usun go
        self.remove_highlighted_element()
        print('clear selection called')
        print(self.selectedItems())
        for item in self.selectedItems():
            if (isinstance(item, map_items.PoiAsPixmap) or isinstance(item, map_items.PolylineQGraphicsPathItem) or
                    isinstance(item, map_items.PolygonQGraphicsPathItem)):
                    item.set_z_value()
        super().clearSelection()

    def closest_point_to_point(self, event_pos, excluded_item=None):
        circle = QPainterPath()
        circle.addEllipse(event_pos, 30, 30)
        items_under_circle = self.items(circle)
        if excluded_item is not None and excluded_item in items_under_circle:
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
        new_poi = map_items.PoiAsPixmap(None, map_objects_properties=self._map_objects_properties,
                                        _projection=self._projection)
        _pos = self._projection.canvas_to_geo(position.x(), position.y())
        obj_data = OrderedDict({(0, 'Type'): '0x0', (1, 'Data0'): str(_pos)})
        new_poi.set_data('', obj_data)
        new_poi.set_mp_data()
        command = commands.CreateNewPoiCmd(new_poi, self.parent.map_objects, self, 'Utwórz POI',
                                           mouse_scene_pos=None)
        self.undo_redo_stack.push(command)

    def command_create_polyline(self, coordinates):
        new_poly = map_items.PolylineQGraphicsPathItem(None,
                                                       map_objects_properties=self._map_objects_properties,
                                                       _projection=self._projection)
        print(coordinates)
        data0 = ','.join([str(self._projection.canvas_to_geo(coord.x(), coord.y())) for coord in coordinates])
        obj_data = OrderedDict({(0, 'Type'): '0x0', (1, 'Data0'): data0})
        new_poly.set_data('', obj_data)
        new_poly.set_mp_data()
        command = commands.CreateNewPolyCmd(new_poly, self.parent.map_objects, self, 'Utwórz Polyline',
                                            mouse_scene_pos=None)
        self.undo_redo_stack.push(command)

    def command_create_polygon(self, coordinates):
        new_poly = map_items.PolygonQGraphicsPathItem(None,
                                                      map_objects_properties=self._map_objects_properties,
                                                      _projection=self._projection)
        data0 = ','.join([str(self._projection.canvas_to_geo(coord.x(), coord.y())) for coord in coordinates])
        obj_data = OrderedDict({(0, 'Type'): '0x0', (1, 'Data0'): data0})
        new_poly.set_data('', obj_data)
        new_poly.set_mp_data()
        command = commands.CreateNewPolyCmd(new_poly, self.parent.map_objects, self, 'Utwórz Polygon',
                                            mouse_scene_pos=None)
        self.undo_redo_stack.push(command)

    def command_paste_poi(self, copied_poi_def, mouse_scene_pos):
        command = commands.CreateNewPoiCmd(copied_poi_def, self.parent.map_objects, self, 'Wklej POI',
                                           mouse_scene_pos=mouse_scene_pos)
        self.undo_redo_stack.push(command)

    def command_paste_polygon(self, copied_poly_def, mouse_scene_pos):
        command = commands.CreateNewPolyCmd(copied_poly_def, self.parent.map_objects, self, 'Wklej Polyline',
                                            mouse_scene_pos=mouse_scene_pos)
        self.undo_redo_stack.push(command)

    def command_paste_polyline(self, copied_poly_def, mouse_scene_pos):
        command = commands.CreateNewPolyCmd(copied_poly_def, self.parent.map_objects, self, 'Wklej Polygon',
                                            mouse_scene_pos=mouse_scene_pos)
        self.undo_redo_stack.push(command)

    def copy(self):
        print('copy canvas')
        if not self.selectedItems():
            lat, lon = self.views()[0].get_current_mouse_geo_coordinates()
            item_mime_data = QMimeData()
            item_mime_data.setText(f'{lat:.6f},{lon:.6f}')
            return item_mime_data
        items_defs = []
        for item in self.selectedItems():
            if (isinstance(item, map_items.PoiAsPixmap) or isinstance(item, map_items.PolylineQGraphicsPathItem) or
                    isinstance(item, map_items.PolygonQGraphicsPathItem)):
                m_pos = [f'MouseScenePos={item._mouse_release_scene_pos.x()},{item._mouse_release_scene_pos.y()}']
                item_def = m_pos + item.to_mp_record()
                item_def.append('[END]')
                items_defs.append(item_def)
        if not items_defs:
            print('zaznaczone obiekty nie sa typu poi, polyline i polygon')
            return None
        str_def = ''
        for item_def in items_defs:
            for i_def in item_def:
                if not i_def.startswith('MouseScenePos='):
                    str_def += i_def + '\n'
            str_def += '\n'
        item_mime_data = QMimeData()
        item_mime_data.setData('application/json', QByteArray(json.dumps(items_defs).encode('utf-8')))
        item_mime_data.setText(str_def)
        return item_mime_data

    def delete(self):
        mode = self.get_pw_mapedit_mode()
        if mode == pwmapedit_constants.Tools.SELECT_OBJECTS:
            if len(self.selectedItems()):
                command = commands.DeleteObjectsCmd(self.selectedItems(),
                                                    self.parent.map_objects, 'Usuwanie obiektu z mapy')
                self.undo_redo_stack.push(command)

    def disable_maplevel_shortcuts(self):
        self.parent.disable_maplevel_shortcuts()

    def draw_all_objects_on_map(self, obj_list):
        for num, obj in enumerate(obj_list):
            self.draw_object_on_map(obj)
        # print('Ilosc wszystkich polygonow: %s, ilosc dodanych: %s, ilosć odjetych: %s.'
        #       % (self.num_polygons, self.num_polygons_added, self.num_polygons_subtracted))

    def draw_object_on_map(self, mapobject):
        if isinstance(mapobject, map_items.PoiAsPixmap) or isinstance(mapobject, map_items.AddrLabel):
            self.addItem(mapobject)
            mapobject.add_label()
            mapobject.set_map_level()
        elif isinstance(mapobject, map_items.PolylineQGraphicsPathItem):
            self.addItem(mapobject)
            if mapobject.get_param('DirIndicator'):
                mapobject.set_mp_dir_indicator(True)
            mapobject.add_label()
            # if mapobject.get_param('EndLevel'):
            #     polyline_path_item.set_mp_end_level(mapobject.get_param('EndLevel'))
            mapobject.set_map_level()
            mapobject.set_pen()
        elif isinstance(mapobject, map_items.PolygonQGraphicsPathItem):
            mapobject.set_z_value()
            mapobject.set_pen()
            mapobject.set_brush()
            self.addItem(mapobject)
            mapobject.add_label()
            mapobject.set_map_level()
        else:
            pass

    def get_item_ignores_transformations(self):
        return self.views()[0].get_item_ignores_transformations()

    def get_map_level(self):
        return self.current_map_level

    def get_pw_mapedit_mode(self):
        return self.parent.get_mapedit_mode()

    def get_undo_redo_stack(self):
        return self.undo_redo_stack

    def get_viewer_corners_geo_coordinates(self):
        viewer = self.views()[0]
        left_top_corner = viewer.mapToScene(viewer.sceneRect().upperLeft())
        right_bottom_corner = viewer.mapToScene(viewer.sceneRect().bottomRight())
        print(left_top_corner, right_bottom_corner)

    def get_viewer_scale(self):
        # if there is a view connected return real scale
        if self.views():
            return self.views()[0].map_scale
        # otherwise return 1
        return 1.0

    def get_viewer_physicalDpiX(self):
        return self.views()[0].physicalDpiX()

    def highlight_element(self, element_path, is_polygon):
        self.remove_highlighted_element()
        if element_path is not None:
            self._highlighted_element = QGraphicsPathItem()
            self._highlighted_element.setFlag(QGraphicsPathItem.GraphicsItemFlag.ItemIsSelectable, False)
            self._highlighted_element.setFlag(QGraphicsPathItem.GraphicsItemFlag.ItemClipsToShape, False)
            self._highlighted_element.setPath(element_path)
            h_pen = QPen(Qt.GlobalColor.darkRed)
            h_pen.setWidth(5)
            h_pen.setCosmetic(True)
            self._highlighted_element.setPen(h_pen)
            self._highlighted_element.pen().setWidth(5)
            if is_polygon:
                self._highlighted_element.setBrush(QBrush(Qt.GlobalColor.darkRed))
            self._highlighted_element.setZValue(pwmapedit_constants.HIGHLIGHTED_POLY_Z_VAL)
            self._highlighted_element.setOpacity(0.5)
            self.addItem(self._highlighted_element)
            size = self.views()[0].viewport().size()
            if self._highlighted_element not in self.views()[0].items(0,0, size.height(), size.width()):
                # self.views()[0].centerOn(self._highlighted_element)
                self.views()[0].ensureVisible(self._highlighted_element)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Control:
            self._stick_to_neighbours_nodes = True
            print('Wlaczam przyciaganie')
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key.Key_Control:
            self._stick_to_neighbours_nodes = False
            self.closest_node_circle_remove()
            print('wylaczam przyciaganie')
        super().keyReleaseEvent(event)

    def mousePressEvent(self, event):
        print('Mouse press event, items at mouse press: ', self.items(event.scenePos()))
        super().mousePressEvent(event)

    def remove_all_objects_from_map(self):
        print('usuwam wszystkie obiekty')
        self.delete('all')
        self.update_idletasks()
        print('usuniete')

    def paste(self, mime_data=None):
        print('paste dla canvas')
        if mime_data is None:
            mime_data = QApplication.clipboard().mimeData()
        if mime_data.hasFormat('application/json'):
            m_data = json.loads(mime_data.data('application/json').data().decode('utf-8'))
        elif mime_data.hasText():
            m_data = []
            for s_record in mime_data.text().split('[END]'):
                if not s_record.strip():
                    continue
                m_data.append(s_record.split('\n'))
        else:
            return

        for s_data in m_data:
            mouse_scene_pos = None
            if s_data[0].startswith('MouseScenePos='):
                x, y = s_data[0].split('=')[1].split(',')
                mouse_scene_pos = QPointF(float(x), float(y))
                s_data = s_data[1:]
            poi_poly_type, obj_comment, obj_data = (misc_functions.map_strings_record_to_dict_record(s_data))
            if poi_poly_type[0] == pwmapedit_constants.MAP_OBJECT_POI:
                map_object = map_items.PoiAsPixmap(None, map_objects_properties=self._map_objects_properties,
                                                   _projection=self._projection)
                map_object.set_data(obj_comment, obj_data)
                map_object.set_mp_data()
                self.command_paste_poi(map_object, mouse_scene_pos)
            elif poi_poly_type[0] == pwmapedit_constants.MAP_OBJECT_POLYLINE:
                map_object = map_items.PolylineQGraphicsPathItem(None,
                                                                 map_objects_properties=self._map_objects_properties,
                                                                 _projection=self._projection)
                map_object.set_data(obj_comment, obj_data)
                map_object.set_mp_data()
                self.command_paste_polyline(map_object, mouse_scene_pos)
            elif poi_poly_type[0] == pwmapedit_constants.MAP_OBJECT_POLYGON:
                map_object = map_items.PolygonQGraphicsPathItem(None,
                                                                map_objects_properties=self._map_objects_properties,
                                                                _projection=self._projection)
                map_object.set_data(obj_comment, obj_data)
                map_object.set_mp_data()
                self.command_paste_polygon(map_object, mouse_scene_pos)
            else:
                return

    def remove_highlighted_element(self):
        if self._highlighted_element is not None:
            self.removeItem(self._highlighted_element)
            self._highlighted_element = None

    def remove_web_layer_graphics(self):
        if self.web_layer_graphics is None:
            return
        for graphic_item in self.web_layer_graphics:
            self.removeItem(self.web_layer_graphics[graphic_item])
        self.web_layer_graphics.clear()
        self.web_layer_graphics = None

    def set_map_level(self, map_level):
        self.clearFocus()
        if isinstance(map_level, str):
            map_level = int(map_level)
        if map_level == self.current_map_level:
            return
        self.current_map_level = map_level
        self.clearSelection()
        start = datetime.now().replace(microsecond=0)
        # self.views()[0].setInteractive(False)
        _map_items = self.items()
        if len(_map_items) < 100:
            one_perc = 1
        else:
            one_perc = len(_map_items) // 100
        self.parent.update_progress_bar('set_maximum', len(_map_items))
        self.parent.update_progress_bar('set_value', 0)
        for item_num, item in enumerate(_map_items):
            if item._accept_map_level_change:
                item.set_map_level()
            if item_num % one_perc == 0:
                self.parent.update_progress_bar('set_value', item_num)
                # self.parent.update()
        # self.views()[0].setInteractive(True)
        self.parent.update_progress_bar('set_value', len(_map_items))
        print('num screen items: %s' % len(_map_items))
        print('realizacja: %s' % (datetime.now().replace(microsecond=0) - start))

    def stick_to_neighbours(self):
        return self._stick_to_neighbours_nodes

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

    def set_canvas_rectangle(self, map_bounding_box):
        # o ile stopni rozszerzamy bounding box, aby nie bylo problemu z rysowaniem
        cor = 0.001
        start_x, start_y = self._projection.geo_to_canvas(map_bounding_box['N'] + cor, map_bounding_box['W'] - cor)
        end_x, end_y = self._projection.geo_to_canvas(map_bounding_box['S'] - cor, map_bounding_box['E'] + cor)
        self.setSceneRect(start_x, start_y, end_x-start_x, end_y-start_y)
        # print('start_x: %s, start_y: %s, end_x: %s, end_y: %s' %(start_x, start_y, end_x, end_y))
        return

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
        x, y = self._projection.geo_to_canvas(tile_def.left_top_lat, tile_def.left_top_lon)
        x2, y2 = self._projection.geo_to_canvas(tile_def.right_bott_lat, tile_def.right_bott_lon)
        web_layer_pic.setPos(x, y)
        # tu raz dostałem division by zero, wiec czasami obrazek nie zaladuje sie, nie wiadomo czemu. Trzeba
        # sprawdzac czy nie null
        web_layer_pic.setScale((x2 - x)/web_layer_pic.boundingRect().width())
        self.addItem(web_layer_pic)
        self.web_layer_graphics[tile_def.file_path] = web_layer_pic

    def set_undo_redo_stack(self, undo_redo_stack):
        self.undo_redo_stack = undo_redo_stack

    def set_projection(self, _projection):
        self._projection = _projection
