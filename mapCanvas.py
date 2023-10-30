#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import QGraphicsScene, QGraphicsPathItem, QGraphicsPolygonItem, QGraphicsRectItem, QGraphicsItem
from PyQt5.QtWidgets import QGraphicsPixmapItem, QGraphicsEllipseItem
from PyQt5.QtSvg import QGraphicsSvgItem
from PyQt5.QtGui import QPainterPath, QPolygonF, QBrush, QPen, QColor, QPixmap
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
    def __init__(self, master, *args, projection=None, **kwargs):
        self.master = master
        super(mapCanvas, self).__init__(*args, **kwargs)
        self.mapScale = 1
        self.projection = None
        if projection is not None:
            self.projection = projection
        self.map_objects_properties = map_object_properties.MapObjectsProperties()
        # self.apply_bindings()
        self.operatingSystem = platform.system()
        self.polygonFill = 'solid' #there are 2 options avialable here, solid and transparent
        self.object_clicked = []
        # self.mode = modes.selectMode(self)
        self.mode_name = 'select'


    # new events definitions:
    # def mouseMoveEvent(self, event):
    #     # Store.status_bar.showMessage('(%s,%s)' % (event.localPos().x(), event.localPos().y()))
    #     print(event.pos().x(), event.pos().y())

    def set_canvas_rectangle(self, map_bounding_box):
        start_x, start_y = self.projection.geo_to_canvas(map_bounding_box['N'], map_bounding_box['W'])
        end_x, end_y = self.projection.geo_to_canvas(map_bounding_box['S'], map_bounding_box['E'])
        self.setSceneRect(start_x, start_y, end_x-start_x, end_y-start_y)
        # print('start_x: %s, start_y: %s, end_x: %s, end_y: %s' %(start_x, start_y, end_x, end_y))
        return

    def draw_all_objects_on_map(self, obj_list, maplevel):
        for num, obj in enumerate(obj_list):
            self.draw_object_on_map(obj, maplevel)

    def draw_object_on_map(self, mapobject, maplevel):
        if maplevel in mapobject.get_obj_levels():
            if isinstance(mapobject, (map_items.Poi, map_items.Polyline, map_items.Polygon)):
                # print('adding object to map', mapobject)
                self.addItem(mapobject)
                nodes, inner_outer = mapobject.obj_datax_get('Data0')[0]
                x, y = nodes[0].return_canvas_coords()
                elipsa = QGraphicsEllipseItem()
                elipsa.setRect(x, y, 10, 10)
                elipsa.setBrush(QBrush(Qt.black))
                self.addItem(elipsa)
                # self.addEllipse(x, y, 10, 10, brush=QBrush(Qt.black))

    def remove_all_objects_from_map(self):
        print('usuwam wszystkie obiekty')
        self.delete('all')
        self.update_idletasks()
        print('usuniete')

    def change_projection(self, proj, map_bounding_box, map_object_list):
        old_proj = self.projection
        if proj == 'UTM':
            newProj = projection.UTM(map_bounding_box)
            if not newProj.calculate_data_ofset():
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

