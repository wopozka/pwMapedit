#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import calendar

from PyQt5.QtWidgets import QGraphicsScene, QGraphicsPathItem, QGraphicsPolygonItem, QGraphicsRectItem, QGraphicsItem
from PyQt5.QtWidgets import QGraphicsPixmapItem, QGraphicsSimpleTextItem, QGraphicsItemGroup, QGraphicsLineItem
from PyQt5.QtSvg import QGraphicsSvgItem
from PyQt5.QtGui import QPainterPath, QPolygonF, QBrush, QPen, QColor, QPixmap, QPainter
from PyQt5.QtCore import QPointF, Qt
import platform
import modes
import math
import projection
import tempfile
import misc_functions
import os.path
import map_items
import map_object_properties
from singleton_store import Store
from datetime import datetime

class mapCanvas(QGraphicsScene):
    """The main map canvas definitions residue here"""
    def __init__(self, parent, *args, projection=None, map_viewer=None, **kwargs):
        self.parent = parent
        self.properties_dock = self.parent.properties_dock
        super(mapCanvas, self).__init__(*args, **kwargs)
        self.map_viewer = map_viewer
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

    def get_item_ignores_transformations(self):
        return self.self.views()[0].get_item_ignores_transformations()

    def get_pw_mapedit_mode(self):
        return self.parent.pw_mapedit_mode

    def get_viewer_scale(self):
        return self.views()[0].map_scale

    def get_viewer_physicalDpiX(self):
        return self.views()[0].physicalDpiX()

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
            poi_icon = self.map_objects_properties.get_poi_icon(mapobject.get_param('Type'))
            if isinstance(poi_icon, QPainterPath):
                poi_icon_brush = self.map_objects_properties.get_nonpixmap_poi_brush(mapobject.get_param('Type'))
            elif isinstance(poi_icon, QPixmap):
                poi_icon_brush = False
            elif isinstance(poi_icon, str):
                poi_icon_brush = False
            mapobject.set_mp_data()
            if isinstance(poi_icon_brush, QBrush):
                mapobject.setBrush(poi_icon_brush)
            self.addItem(mapobject)
            mapobject.add_label()
            mapobject.set_map_level()
        elif isinstance(mapobject, map_items.PolylineQGraphicsPathItem):
            # https://stackoverflow.com/questions/47061629/how-can-i-color-qpainterpath-subpaths-differently
            # pomysl jak narysowac  roznokolorowe może dla mostow inne grubosci?
            # polyline_path_item = map_items.PolylineQGraphicsPathItem(self.projection)
            # for data_x in mp_data_range:
            #     if mapobject.get_datax(data_x):
            mapobject.set_mp_data()
            #    if mapobject.get_hlevels(data_x):
            mapobject.set_mp_hlevels()
            self.addItem(mapobject)
            if mapobject.get_param('DirIndicator'):
                mapobject.set_mp_dir_indicator(True)
            mapobject.add_label()
            # if mapobject.get_param('EndLevel'):
            #     polyline_path_item.set_mp_end_level(mapobject.get_param('EndLevel'))
            mapobject.set_map_level()
            pen = self.map_objects_properties.get_polyline_qpen(mapobject.get_param('Type'))
            mapobject.setPen(pen)
            # mapobject.add_hlevel_labels()
        elif isinstance(mapobject, map_items.PolygonQGraphicsPathItem):
            # polygon = map_items.PolygonQGraphicsPathItem(self.projection)
            # for data_x in mp_data_range:
            #     if mapobject.get_datax(data_x):
            mapobject.set_mp_data()
            mapobject.setZValue(self.map_objects_properties.get_polygon_z_value(mapobject.get_param('Type')))
            mapobject.setPen(self.map_objects_properties.get_polygon_qpen(mapobject.get_param('Type')))
            color = self.map_objects_properties.get_polygon_fill_colour(mapobject.get_param('Type'))
            mapobject.setBrush(QBrush(color))
            self.addItem(mapobject)
            mapobject.add_label()
            # if mapobject.get_param('EndLevel'):
            #     polygon.set_mp_end_level(mapobject.get_param('EndLevel'))
            mapobject.set_map_level()
        else:
            pass

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
        if isinstance(map_level, str):
            map_level = int(map_level)
        if map_level == self.current_map_level:
            return
        self.current_map_level = map_level
        self.clearSelection()
        num_screen_items = 0
        start = datetime.now().replace(microsecond=0)
        for item in self.items():
            num_screen_items += 1
            if item._accept_map_level_change:
                item.set_map_level()
        print('num screen items: %s' % num_screen_items)
        print('realizacja: %s' % (datetime.now().replace(microsecond=0) - start))

    def get_map_level(self):
        return self.current_map_level

    def selection_change_actions(self):
        mode = self.get_pw_mapedit_mode()
        if mode == 'select_objects':
            if len(self.selectedItems()) == 1:
                self.properties_dock.set_map_object_id(self.selectedItems()[0])
                self.properties_dock.fill_map_object_properties()
        elif mode == 'edit_nodes':
            selected_items = self.selectedItems()
            print(selected_items, self.selected_objects)
            if any(isinstance(a, QGraphicsPixmapItem) for a in selected_items):
                for obj in self.selected_objects:
                    obj.undecorate()
                return
            if any(hasattr(a, 'hover_drag_mode') and a.hover_drag_mode for a in selected_items):
                print('selekcja sie zmienila na uchwyty')
                return
            # przypadku gdy obiekt juz jest w trybie edycji wezlow nie rob nic. Zachodzi gdy mamy kliknięty uchwyt
            # a potem klikniemy z shiftem na podswietlony obiekt tak aby dodac wezel. Wtedy zmienia sie selekcja na nowy
            # obiekt ktory ma juz uchwyty. Nie rob nic w takim przypadku.
            if selected_items and selected_items[0].is_in_node_edit_mode():
                return
            if self.selected_objects:
                print('usuwam dekoracje selection change', self.selected_objects)
                for obj in self.selected_objects:
                    obj.undecorate()
            self.selected_objects = selected_items
            for obj in self.selected_objects:
                obj.decorate()
