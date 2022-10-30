#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import QGraphicsScene, QGraphicsPathItem
from PyQt5.QtGui import QPainterPath, QPolygonF
from PyQt5.QtCore import QPointF
import platform
import modes
import math
import projection
from singleton_store import Store

class mapCanvas(QGraphicsScene):
    """The main map canvas definitions residue here"""
    def __init__(self, master, *options):
        self.master = master
        self.MapData = None
        super(mapCanvas, self).__init__(*options)
        self.mapScale = 1
        self.mOP = mapObjectsProperties()
        # self.apply_bindings()
        self.operatingSystem = platform.system()
        self.polygonFill = 'solid' #there are 2 options avialable here, solid and transparent
        self.object_clicked = []
        # self.mode = modes.selectMode(self)
        self.mode_name = 'select'

    def draw_object_on_map(self, mapobject):
        """ This function draws map object on the canvas
        :return: None
        """
        #print(mapobject.object_type)
        if mapobject.object_type == '[POI]':
            self.draw_poi_on_canvas(mapobject)
        elif mapobject.object_type == '[POLYLINE]':
            self.draw_polyline_on_canvas(mapobject)
        elif mapobject.object_type == '[POLYGON]':
            self.draw_polygone_on_canvas(mapobject)
        else:
            print('Very weird object')
            print(mapobject)

    def draw_poi_on_canvas(self, mmapobject):
        return

    def draw_polyline_on_canvas(self, mapobject):
        coordslist = []
        if mapobject.Type in self.mOP.polylinePropertiesColour:
            colour = self.mOP.polylinePropertiesColour[mapobject.Type]
        else:
            colour = 'black'

        if mapobject.Type in self.mOP.polylinePropertiesWidth:
            width = self.mOP.polylinePropertiesWidth[mapobject.Type]
        else:
            width = 1

        if mapobject.Type in self.mOP.polylinePropertiesDash:
            dash = self.mOP.polylinePropertiesDash[mapobject.Type]
        else:
            dash = None

        for key in mapobject.Points.keys():  # because might be multiple Data (Data0_0, Data0_1, Data1_0 etc)
            polyline = QPainterPath()
            graphics_path_item = QGraphicsPathItem()
            for num, points in enumerate(mapobject.Points[key]):
                coordslist += points.return_canvas_coords()
                coord_x, coord_y = points.return_canvas_coords()
                if num == 0:
                    polyline.moveTo(coord_x, coord_y)
                else:
                    polyline.lineTo(coord_x, coord_y)
            graphics_path_item.setPath(polyline)
            self.addPath(polyline)
            # in case polyline has a label, place it on the map
            if mapobject.Label:
                if len(coordslist) == 4:
                    label_pos = [coordslist[0], coordslist[1]]
                    if (coordslist[3] - coordslist[1]) == 0:
                        label_angle = 90
                    else:
                        label_angle = math.atan((coordslist[2] - coordslist[1]) / (coordslist[3] - coordslist[1]))

                    # print(label_angle)
                    # self.create_text(label_pos, text = mapobject.Label, angle = label_angle)
                else:
                    pass
                    # calculate label position, lets say it will be in the meadle of the polyline
                    # label_pos = coordslist[len(coordslist) // 2]
                    # label_angle =
            del (coordslist[:])
        return

    def draw_polygone_on_canvas(self, mapobject):
        coordslist = []
        if mapobject.Type in self.mOP.polygonePropertiesFillColour:
            fill_colour = self.mOP.polygonePropertiesFillColour[mapobject.Type]
        else:
            fill_colour = 'grey'
        if self.polygonFill == 'transparent':
            fill_colour = ''
        for key in mapobject.Points.keys():  # because might be multiple Data (Data0_0, Data0_1, Data1_0 etc)
            for points in mapobject.Points[key]:
                x, y = points.return_canvas_coords()
                coordslist.append(QPointF(x, y))
            # print(coordslist)
            q_polygon = QPolygonF(coordslist)
            # q_patinter_path = QPainterPath()
            # q_patinter_path.addPolygon(q_polygon)
            self.addPolygon(q_polygon)
        return

    def draw_all_objects_on_map(self):
        """this functions prints all objects on map
        :return None
        """
        print('rysuje wszystkie %s obiekty' % len(self.MapData.mapObjectsList))
        [self.draw_object_on_map(a) for a in self.MapData.mapObjectsList]
        # for aaa in (self.MapData.mapObjectsList):
        #    self.draw_object_on_map(aaa)
        # self.config(scrollregion=self.bbox('all'))

    def remove_all_objects_from_map(self):
        print('usuwam wszystkie obiekty')
        self.delete('all')
        self.update_idletasks()
        print('usuniete')

    def change_projection(self, proj):
        old_proj = Store.projection
        if proj == 'UTM':
            newProj = projection.UTM(self.MapData.mapBoundingBox)
            if not newProj.calculate_data_ofset():
                Store.projection = newProj
                print(Store.projection.projectionName)
                self.remove_all_objects_from_map()
                self.draw_all_objects_on_map()
                return 0
            else:
                return 1
        elif proj == 'Mercator':
            Store.projection = projection.Mercator(self.MapData.mapBoundingBox)
            print(Store.projection.projectionName)
            self.remove_all_objects_from_map()
            self.draw_all_objects_on_map()
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
        print('zmieniam mode na %s'%mode)
        self.mode.unregister_mode()
        self.mode_name = mode
        if mode == 'edit':
            self.mode = modes.editNodeMode(self)
        elif mode == 'select':
            self.mode = modes.selectMode(self)
        else:
            pass

    def scaledown(self, event):
        x = self.canvasx(event.x)
        y = self.canvasy(event.y)
        self.scale('SCALABLE', x, y, 2, 2)
        self.config(scrollregion=self.bbox('all'))
        self.mode.refresh_decorating_squares()

    def scaleup(self, event):
        print('zwiekszam')
        x = self.canvasx(event.x)
        y = self.canvasy(event.y)
        self.scale('SCALABLE', x, y, 0.5, 0.5)
        self.config(scrollregion=self.bbox('all'))
        self.mode.refresh_decorating_squares()

    def windows_scale(self, event):
        print(event.delta)
        if event.delta > 0:
            self.scaleup(event)
        else:
            self.scaledown(event)
        return None

    def scroll_map_NS(self, event):
        if self.operatingSystem == 'Linux':
            if event.num == 4:
                self.yview_scroll(int(-1), "units")
            elif event.num == 5:
                self.yview_scroll(int(1), "units")
        elif self.operatingSystem == 'Windows':
            self.yview_scroll(int(-1*(event.delta/120)), "units")

    def scroll_map_EW(self, event):
        if self.operatingSystem == 'Linux':
            if event.num == 4:
                self.xview_scroll(int(-1), "units")
            elif event.num == 5:
                self.xview_scroll(int(1), "units")
        elif self.operatingSystem == 'Windows':
            self.xview_scroll(int(-1*(event.delta/120)), "units")

    def switch_plygon_render_kit(self, event):
        if self.polygonFill == 'solid':
            self.itemconfig('POLYGON', fill='')
            self.polygonFill = 'transparent'
        else:
            self.polygonFill = 'solid'
            for a in self.find_withtag('POLYGON'):
                for b in [c for c in self.gettags(a) if c.startswith('Type=')]:
                    d = b.split('=')[-1]
                    if d in self.mOP.polygonePropertiesFillColour:
                        self.itemconfig(a, fill=self.mOP.polygonePropertiesFillColour[d])
                    else:
                        self.itemconfig(a, fill='grey')

class mapObjectsProperties(object):
    """here this class contains definitions of all map objects: the points, polylines and polygones"""
    def __init__(self):
        # couple if definitions
        # points definitions
        self.pointProperties = {}


        # polylines definitions
        #dictionary where key is Type
        self.polylinePropertiesColour = {'0x0':'black',
                                         '0x1':'blue',
                                         '0x2':'orange red',
                                         '0x3':'red',
                                         '0x4':'orange',
                                         '0x5':'yellow',
                                         '0x6':'snow4',
                                         '0x7':'snow3',
                                         '0x8':'orange',
                                         '0x9':'blue',
                                         '0x14':'black',
                                         '0x18':'blue',
                                         '0x1f':'blue'}

        self.polylinePropertiesWidth = {'0x1': 3,
                                        '0x2': 3,
                                        '0x3': 3,
                                        '0x4': 2,
                                        '0x14': 3}

        self.polylinePropertiesDash = {'0x14': (50,30),
                                       '0x18': (50,30)
                                       }

        #polygone definitions
        self.polygonePropertiesFillColour = {'0x28': 'blue',
                                            '0x29': 'blue',
                                            '0x32': 'blue',
                                            '0x3b': 'blue',
                                             '0x3c': 'blue',
                                             '0x3d': 'blue',
                                             '0x3e  ': 'blue',
                                             '0x3f': 'blue',
                                             '0x40': 'blue',
                                             '0x41': 'blue',
                                             '0x42': 'blue',
                                             '0x43': 'blue',
                                             '0x44': 'blue',
                                             '0x45': 'blue',
                                             '0x46': 'blue',
                                             '0x47': 'blue',
                                             '0x48': 'blue',
                                             '0x49': 'blue'}
