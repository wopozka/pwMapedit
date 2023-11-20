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
    def __init__(self, master, *args, projection=None, map_viewer=None, **kwargs):
        self.master = master
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

        # selection changed slot conection
        self.selectionChanged.connect(self.selection_change_actions)


    # new events definitions:
    # def mouseMoveEvent(self, event):
    #     # Store.status_bar.showMessage('(%s,%s)' % (event.localPos().x(), event.localPos().y()))
    #     print(event.pos().x(), event.pos().y())

    def get_viewer_scale(self):
        return self.map_viewer.map_scale

    def set_map_viewer(self, viewer):
        self.map_viewer = viewer

    def set_canvas_rectangle(self, map_bounding_box):
        start_x, start_y = self.projection.geo_to_canvas(map_bounding_box['N'], map_bounding_box['W'])
        end_x, end_y = self.projection.geo_to_canvas(map_bounding_box['S'], map_bounding_box['E'])
        self.setSceneRect(start_x, start_y, end_x-start_x, end_y-start_y)
        # print('start_x: %s, start_y: %s, end_x: %s, end_y: %s' %(start_x, start_y, end_x, end_y))
        return

    def draw_all_objects_on_map(self, obj_list, maplevel):
        for num, obj in enumerate(obj_list):
            self.draw_object_on_map(obj, maplevel)
        # print('Ilosc wszystkich polygonow: %s, ilosc dodanych: %s, ilosć odjetych: %s.'
        #       % (self.num_polygons, self.num_polygons_added, self.num_polygons_subtracted))

    def draw_object_on_map(self, mapobject, maplevel):
        if maplevel in mapobject.get_obj_levels():
            if isinstance(mapobject, map_items.Poi):
                group_item = QGraphicsItemGroup()
                nodes, inner_outer = mapobject.obj_datax_get('Data0')[0]
                x, y = nodes[0].get_canvas_coords()
                poi = self.map_objects_properties.get_poi_icon(mapobject.obj_param_get('Type'))
                poi.setPos(x, y)
                poi.setZValue(20)
                poi.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable)
                self.addItem(poi)
                # self.addItem(poi)
                # group_item.addToGroup(poi)
                x0, y0, x1, y1 = poi.boundingRect().getRect()
                if mapobject.obj_param_get('Label'):
                    poi_label = map_items.PoiLabel(mapobject.obj_param_get('Label'), poi)
                    # group_item.addToGroup(poi_label)
                # group_item.setZValue(20)
                # group_item.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable)
                # self.addItem(group_item)
            elif isinstance(mapobject, map_items.Polyline):
                # https://stackoverflow.com/questions/47061629/how-can-i-color-qpainterpath-subpaths-differently
                # pomysl jak narysowac  roznokolorowe może dla mostow inne grubosci?
                polyline = QPainterPath()
                # polyline = QGraphicsItem()
                for obj_data in mapobject.obj_datax_get('Data0'):
                    nodes, inner_outer = obj_data
                    for node_num, node in enumerate(nodes):
                        x, y = node.get_canvas_coords()
                        if node_num == 0:
                            polyline.moveTo(x, y)
                        else:
                            polyline.lineTo(x, y)
                # polyline_path_item = QGraphicsPathItem(polyline)
                polyline_path_item = map_items.PolylineQGraphicsPathItem(self.projection, polyline)
                pen = self.map_objects_properties.get_polyline_qpen(mapobject.obj_param_get('Type'))
                pen.setCosmetic(True)
                polyline_path_item.setPen(pen)
                polyline_path_item.setZValue(10)
                polyline_path_item.setAcceptHoverEvents(True)
                polyline_path_item.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable)
                self.addItem(polyline_path_item)
                if mapobject.obj_param_get('Label'):
                    poly_label = map_items.PolylineLabel(mapobject.obj_param_get('Label'), polyline_path_item)
                    # self.addItem(poly_label)
                if mapobject.obj_param_get('DirIndicator'):
                    polyline_path_item.add_arrow_heads()
            elif isinstance(mapobject, map_items.Polygon):
                outer_polygone = None
                qpainterpaths_to_add = list()
                for obj_data in mapobject.obj_datax_get('Data0'):
                    nodes, outer = obj_data
                    nodes_qpointfs = [a.get_canvas_coords_as_qpointf() for a in nodes]
                    # gdyby sie okazalo ze polygone musi byc zamkniety, ale chyba nie musi
                    # nodes_qpointfs.append(nodes_qpointfs[0])
                    if outer_polygone is not None \
                            and all(qpainterpaths_to_add[-1].contains(a) for a in nodes_qpointfs):
                            # and all(outer_polygone.containsPoint(a, Qt.OddEvenFill) for a in nodes_qpointfs):
                        qpp = QPainterPath()
                        qpp.addPolygon(QPolygonF(nodes_qpointfs))
                        qpainterpaths_to_add[-1] = qpainterpaths_to_add[-1].subtracted(qpp)
                    else:
                        outer_polygone = QPolygonF(nodes_qpointfs)
                        qpp = QPainterPath()
                        qpp.addPolygon(outer_polygone)
                        qpainterpaths_to_add.append(qpp)
                # polygon = QGraphicsPathItem()
                polygon = map_items.PolygonQGraphicsPathItem(self.projection)
                polygon.setPen(self.map_objects_properties.get_polygon_qpen(mapobject.obj_param_get('Type')))
                polygon.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable)
                polygon.setAcceptHoverEvents(True)
                for poly in qpainterpaths_to_add:
                    # polygon = QGraphicsPathItem()
                    polygon.setPath(poly)
                    color = self.map_objects_properties.get_polygon_fill_colour(mapobject.obj_param_get('Type'))
                    polygon.setBrush(QBrush(color))
                    # polygon.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable)
                    # self.addItem(polygon)
                polygon.setZValue(self.map_objects_properties.get_polygon_z_value(mapobject.obj_param_get('Type')))
                self.addItem(polygon)
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

    # bindings and the binding functions
    def apply_bindings(self):

        # bindings for magnifying: -, ctrl+roll up scalling down; =, ctrl+roll down scallling
        self.bind_all("<equal>", self.scaleup)
        self.bind_all("<minus>", self.scaledown)
        self.bind_all("<Control-MouseWheel>", self.windows_scale)
        self.bind_all("<Control-4>", self.scaledown)
        self.bind_all("<Control-5>", self.scaleup)

        # bindings for scrolling a map with mouse wheel - NS direction
        self.bind_all("<MouseWheel>", self.scroll_map_NS)
        self.bind_all("<4>", self.scroll_map_NS)
        self.bind_all("<5>", self.scroll_map_NS)

        # bindings for scrolling a map with mouse wheel - EW directions
        self.bind_all("<Shift-MouseWheel>", self.scroll_map_EW)
        self.bind_all("<Shift-4>", self.scroll_map_EW)
        self.bind_all("<Shift-5>", self.scroll_map_EW)

        # bindings for polygon render kit
        self.bind_all('<t>', self.switch_plygon_render_kit)

        # bindings for mode switching
        self.bind_all('<s>', lambda e: self.change_mode(e, mode='select'))
        self.bind_all('<m>', lambda e: self.change_mode(e, mode='edit'))
        # lets try to bind selecting object
        # self.bind_all("<Button-1>",self.mouse_1)
        # self.bind_all("<ButtonRelease-1>",self.mouse_2)

    # def mouse_1(self,event):
        # we have to register the object the mouse pointer is over. For further actions
        # a=self.find_withtag('current')
        # if a:
        #   if self.object_clicked:
        #        del(self.object_clicked[0])
        #        self.object_clicked.append(a)
        #    else:
        #       self.object_clicked.append(a)


    # def mouse_2(self,event):
    #     if self.object_clicked:
    #        self.itemconfig(self.object_clicked[0],fill='blue',dash=(5,5))

    def change_mode(self, event, mode=None):

        # if actual mode was selected, do nothing
        if mode == self.mode_name:
            return
        print('zmieniam mode na %s' % mode)
        self.mode.unregister_mode()
        self.mode_name = mode
        if mode == 'edit':
            self.mode = modes.editNodeMode(self)
        elif mode == 'select':
            self.mode = modes.selectMode(self)
        else:
            pass

    def switch_plygon_render_kit(self, event):
        if self.polygonFill == 'solid':
            self.itemconfig('POLYGON', fill='')
            self.polygonFill = 'transparent'
        else:
            self.polygonFill = 'solid'
            for a in self.find_withtag('POLYGON'):
                for b in [c for c in self.gettags(a) if c.startswith('Type=')]:
                    d = b.split('=')[-1]
                    if d in self.map_objects_properties.polygonePropertiesFillColour:
                        self.itemconfig(a, fill=self.map_objects_properties.polygonePropertiesFillColour[d])
                    else:
                        self.itemconfig(a, fill='grey')

    def selection_change_actions(self):
        if any(isinstance(a, QGraphicsPixmapItem) for a in self.selectedItems()):
            return
        if any(hasattr(a, 'hover_drag_mode') and a.hover_drag_mode for a in self.selectedItems()):
            return
        if self.selected_objects:
            self.selected_objects[0].undecorate()
        self.selected_objects = self.selectedItems()
        for obj in self.selected_objects:
            obj.decorate()
