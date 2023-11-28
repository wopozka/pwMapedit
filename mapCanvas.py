#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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

class mapCanvas(QGraphicsScene):
    """The main map canvas definitions residue here"""
    def __init__(self, parent, *args, projection=None, map_viewer=None, **kwargs):
        self.parent = parent
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
        mp_data_range = ('Data0', 'Data1', 'Data2', 'Data3', 'Data4')
        if isinstance(mapobject, map_items.Poi):
            # group_item = QGraphicsItemGroup()
            # nodes = mapobject.obj_datax_get('Data0')[0]
            # x, y = nodes[0].get_canvas_coords()
            poi_icon = self.map_objects_properties.get_poi_icon(mapobject.obj_param_get('Type'))
            if isinstance(poi_icon, QPainterPath):
                poi = map_items.PoiAsPath(projection, poi_icon)
                poi_icon_brush = self.map_objects_properties.get_nonpixmap_poi_brush(
                    mapobject.obj_param_get('Type'))
            elif isinstance(poi_icon, QPixmap):
                poi = map_items.PoiAsPixmap(projection, poi_icon)
                poi_icon_brush = False
            elif isinstance(poi_icon, str):
                poi = map_items.AddrLabel(projection, '__tmp__')
                poi_icon_brush = False
            for data_x in mp_data_range:
                if mapobject.obj_datax_get(data_x):
                    poi.set_mp_data(data_x, mapobject.obj_datax_get(data_x))
            if poi_icon_brush:
                poi.setBrush(poi_icon_brush)
            self.addItem(poi)
            if mapobject.obj_param_get('Label'):
                poi.add_label(mapobject.obj_param_get('Label'))
            if mapobject.obj_param_get('EndLevel'):
                poi.set_mp_end_level(mapobject.obj_param_get('EndLevel'))
            poi.set_map_level()
        elif isinstance(mapobject, map_items.Polyline):
            # https://stackoverflow.com/questions/47061629/how-can-i-color-qpainterpath-subpaths-differently
            # pomysl jak narysowac  roznokolorowe może dla mostow inne grubosci?
            polyline_path_item = map_items.PolylineQGraphicsPathItem(self.projection)
            for data_x in mp_data_range:
                if mapobject.obj_datax_get(data_x):
                    polyline_path_item.set_mp_data(data_x, mapobject.obj_datax_get(data_x))
                if mapobject.get_hlevels(data_x):
                    polyline_path_item.set_mp_hlevels(data_x, mapobject.get_hlevels(data_x))
            self.addItem(polyline_path_item)
            if mapobject.obj_param_get('DirIndicator'):
                polyline_path_item.set_mp_dir_indicator(True)
            if mapobject.obj_param_get('Label'):
                polyline_path_item.set_mp_label(mapobject.obj_param_get('Label'))
            if mapobject.obj_param_get('EndLevel'):
                polyline_path_item.set_mp_end_level(mapobject.obj_param_get('EndLevel'))
            polyline_path_item.set_map_level()
            pen = self.map_objects_properties.get_polyline_qpen(mapobject.obj_param_get('Type'))
            polyline_path_item.setPen(pen)
            polyline_path_item.add_hlevel_labels()
        elif isinstance(mapobject, map_items.Polygon):
            polygon = map_items.PolygonQGraphicsPathItem(self.projection)
            for data_x in mp_data_range:
                if mapobject.obj_datax_get(data_x):
                    polygon.set_mp_data(data_x, mapobject.obj_datax_get(data_x))
            polygon.setZValue(self.map_objects_properties.get_polygon_z_value(mapobject.obj_param_get('Type')))
            polygon.setPen(self.map_objects_properties.get_polygon_qpen(mapobject.obj_param_get('Type')))
            color = self.map_objects_properties.get_polygon_fill_colour(mapobject.obj_param_get('Type'))
            polygon.setBrush(QBrush(color))
            self.addItem(polygon)
            if mapobject.obj_param_get('Label'):
                polygon.set_mp_label(mapobject.obj_param_get('Label'))
            if mapobject.obj_param_get('EndLevel'):
                polygon.set_mp_end_level(mapobject.obj_param_get('EndLevel'))
            polygon.set_map_level()
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
        for item in self.items():
            if item.accept_map_level_change():
                item.set_map_level()

    def get_map_level(self):
        return self.current_map_level

    # # bindings and the binding functions
    # def apply_bindings(self):
    #
    #     # bindings for magnifying: -, ctrl+roll up scalling down; =, ctrl+roll down scallling
    #     self.bind_all("<equal>", self.scaleup)
    #     self.bind_all("<minus>", self.scaledown)
    #     self.bind_all("<Control-MouseWheel>", self.windows_scale)
    #     self.bind_all("<Control-4>", self.scaledown)
    #     self.bind_all("<Control-5>", self.scaleup)
    #
    #     # bindings for scrolling a map with mouse wheel - NS direction
    #     self.bind_all("<MouseWheel>", self.scroll_map_NS)
    #     self.bind_all("<4>", self.scroll_map_NS)
    #     self.bind_all("<5>", self.scroll_map_NS)
    #
    #     # bindings for scrolling a map with mouse wheel - EW directions
    #     self.bind_all("<Shift-MouseWheel>", self.scroll_map_EW)
    #     self.bind_all("<Shift-4>", self.scroll_map_EW)
    #     self.bind_all("<Shift-5>", self.scroll_map_EW)
    #
    #     # bindings for polygon render kit
    #     self.bind_all('<t>', self.switch_plygon_render_kit)
    #
    #     # bindings for mode switching
    #     self.bind_all('<s>', lambda e: self.change_mode(e, mode='select'))
    #     self.bind_all('<m>', lambda e: self.change_mode(e, mode='edit'))
    #     # lets try to bind selecting object
    #     # self.bind_all("<Button-1>",self.mouse_1)
    #     # self.bind_all("<ButtonRelease-1>",self.mouse_2)
    #
    # # def mouse_1(self,event):
    #     # we have to register the object the mouse pointer is over. For further actions
    #     # a=self.find_withtag('current')
    #     # if a:
    #     #   if self.object_clicked:
    #     #        del(self.object_clicked[0])
    #     #        self.object_clicked.append(a)
    #     #    else:
    #     #       self.object_clicked.append(a)
    #
    #
    # # def mouse_2(self,event):
    # #     if self.object_clicked:
    # #        self.itemconfig(self.object_clicked[0],fill='blue',dash=(5,5))
    #
    # def change_mode(self, event, mode=None):
    #
    #     # if actual mode was selected, do nothing
    #     if mode == self.mode_name:
    #         return
    #     print('zmieniam mode na %s' % mode)
    #     self.mode.unregister_mode()
    #     self.mode_name = mode
    #     if mode == 'edit':
    #         self.mode = modes.editNodeMode(self)
    #     elif mode == 'select':
    #         self.mode = modes.selectMode(self)
    #     else:
    #         pass

    # def switch_plygon_render_kit(self, event):
    #     if self.polygonFill == 'solid':
    #         self.itemconfig('POLYGON', fill='')
    #         self.polygonFill = 'transparent'
    #     else:
    #         self.polygonFill = 'solid'
    #         for a in self.find_withtag('POLYGON'):
    #             for b in [c for c in self.gettags(a) if c.startswith('Type=')]:
    #                 d = b.split('=')[-1]
    #                 if d in self.map_objects_properties.polygonePropertiesFillColour:
    #                     self.itemconfig(a, fill=self.map_objects_properties.polygonePropertiesFillColour[d])
    #                 else:
    #                     self.itemconfig(a, fill='grey')

    def selection_change_actions(self):
        mode = self.get_pw_mapedit_mode()
        if mode == 'select_objects':
            pass
        elif mode == 'edit_nodes':
            if any(isinstance(a, QGraphicsPixmapItem) for a in self.selectedItems()):
                return
            if any(hasattr(a, 'hover_drag_mode') and a.hover_drag_mode for a in self.selectedItems()):
                return
            if self.selected_objects:
                self.selected_objects[0].undecorate()
            self.selected_objects = self.selectedItems()
            for obj in self.selected_objects:
                obj.decorate()
