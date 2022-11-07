#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import QGraphicsScene, QGraphicsPathItem, QGraphicsPolygonItem, QGraphicsRectItem, QGraphicsItem
from PyQt5.QtWidgets import QGraphicsPixmapItem, QGraphicsEllipseItem
from PyQt5.QtGui import QPainterPath, QPolygonF, QBrush, QPen, QColor, QPixmap
from PyQt5.QtCore import QPointF, Qt
import platform
import modes
import math
import projection
import misc_functions
import os.path
from singleton_store import Store

class mapCanvas(QGraphicsScene):
    """The main map canvas definitions residue here"""
    def __init__(self, master, *options):
        self.master = master
        self.MapData = None
        print(*options)
        super(mapCanvas, self).__init__(*options)
        self.mapScale = 1
        self.mOP = mapObjectsProperties()
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

    def set_canvas_rectangle(self):
        start_x, start_y = Store.projection.geo_to_canvas(self.MapData.map_bounding_box['N'],
                                                          self.MapData.map_bounding_box['W'])
        end_x, end_y = Store.projection.geo_to_canvas(self.MapData.map_bounding_box['S'],
                                                      self.MapData.map_bounding_box['E'])
        self.setSceneRect(start_x, start_y, end_x-start_x, end_y-start_y)
        # print('start_x: %s, start_y: %s, end_x: %s, end_y: %s' %(start_x, start_y, end_x, end_y))
        return

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

    def draw_poi_on_canvas(self, mapobject):
        for key in mapobject.Points:
            for coord_pair in mapobject.Points[key]:
                x, y = coord_pair.return_canvas_coords()
        if mapobject.Type in self.mOP.poi_icons:
            poi = QGraphicsPixmapItem(self.mOP.poi_icons[mapobject.Type])
            print(self.mOP.poi_icons[mapobject.Type].size().height(), self.mOP.poi_icons[mapobject.Type].size().width())
            poi.setPos(x, y)
            poi.setZValue(20)
            self.addItem(QGraphicsPixmapItem(poi))
        else:
            poi = QGraphicsEllipseItem(x, y, 10, 10)
            brush = QBrush(Qt.black)
            poi.setBrush(brush)
            poi.setZValue(20)
            self.addItem(poi)

    def draw_polyline_on_canvas(self, mapobject):
        # return
        coordslist = []
        colour = Qt.black
        if mapobject.Type in self.mOP.polylinePropertiesColour:
            colour = self.mOP.polylinePropertiesColour[mapobject.Type]
        width = 1
        if mapobject.Type in self.mOP.polylinePropertiesWidth:
            width = self.mOP.polylinePropertiesWidth[mapobject.Type]
        dash = Qt.SolidLine
        if mapobject.Type in self.mOP.polylinePropertiesDash:
            dash = self.mOP.polylinePropertiesDash[mapobject.Type]
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
            pen = QPen(colour)
            pen.setWidth(width)
            pen.setStyle(dash)
            graphics_path_item.setPath(polyline)
            graphics_path_item.setPen(pen)
            graphics_path_item.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable)
            graphics_path_item.setZValue(10)
            self.addItem(graphics_path_item)
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
        fill_colour = QColor('gainsboro')
        if mapobject.Type in self.mOP.polygonePropertiesFillColour:
            fill_colour = self.mOP.polygonePropertiesFillColour[mapobject.Type]
        if self.polygonFill == 'transparent':
            fill_colour = ''
        for key in mapobject.Points.keys():  # because might be multiple Data (Data0_0, Data0_1, Data1_0 etc)
            for points in mapobject.Points[key]:
                x, y = points.return_canvas_coords()
                 # print('x: %s, y: %s' %(x, y))
                coordslist.append(QPointF(x, y))
        q_polygon = QGraphicsPolygonItem(QPolygonF(coordslist))
        brush = QBrush(fill_colour)
        q_polygon.setBrush(brush)
        q_polygon.setZValue(0)
        self.addItem(q_polygon)
        return

    def draw_all_objects_on_map(self):
        """this functions prints all objects on map
        :return None
        """
        print('rysuje wszystkie %s obiekty' % len(self.MapData.mapObjectsList))
        [self.draw_object_on_map(a) for a in self.MapData.mapObjectsList]
        self.set_canvas_rectangle()
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
            newProj = projection.UTM(self.MapData.map_bounding_box)
            if not newProj.calculate_data_ofset():
                Store.projection = newProj
                print(Store.projection.projectionName)
                self.remove_all_objects_from_map()
                self.draw_all_objects_on_map()
                return 0
            else:
                return 1
        elif proj == 'Mercator':
            Store.projection = projection.Mercator(self.MapData.map_bounding_box)
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
                    if d in self.mOP.polygonePropertiesFillColour:
                        self.itemconfig(a, fill=self.mOP.polygonePropertiesFillColour[d])
                    else:
                        self.itemconfig(a, fill='grey')

class mapObjectsProperties(object):
    """here this class contains definitions of all map objects: the points, polylines and polygones"""
    def __init__(self):
        # couple if definitions
        # points definitions
        self.poi_icons = {}
        self.read_icons()

        # polylines definitions
        #dictionary where key is Type
        self.polylinePropertiesColour = {'0x0': Qt.black,
                                         '0x1': QColor('#0000ff'),
                                         '0x2': QColor('#ff0000'),
                                         '0x3': QColor('#bd3020'),
                                         '0x4': QColor('#ff9500'),
                                         '0x5': QColor('#ffff8b'),
                                         '0x6': QColor('gray'),
                                         '0x7': QColor('lightgrey'),
                                         '0x8': QColor('orange'),
                                         '0x9': Qt.blue,
                                         '0xa': QColor('lightgrey'),
                                         '0xc': QColor('darkorange'),
                                         '0xd': QColor('brown'),
                                         '0x1a': QColor('gray'),
                                         '0x14': Qt.black,
                                         '0x16': QColor('chocolate'),
                                         '0x18': Qt.blue,
                                         '0x1c': QColor('gray'),
                                         '0x1f': Qt.blue,
                                         '0x4b': Qt.red,
                                         '0x10e11': QColor('cyan'),
                                         '0x10e12': QColor('cyan'),
                                         '0x10e13': QColor('darkred'),
                                         '0x10e14': Qt.black,
                                         '0x10e15': QColor('#a4a4a4')
                                         }

        self.polylinePropertiesWidth = {'0x1': 5,
                                        '0x2': 5,
                                        '0x3': 4,
                                        '0x4': 3,
                                        '0x5': 3,
                                        '0x6': 3,
                                        '0x7': 3,
                                        '0x8': 2,
                                        '0x9': 2,
                                        '0xa': 2,
                                        '0xc': 2,
                                        '0xd': 2,
                                        '0x14': 5,
                                        '0x1f': 3,
                                        '0x10e11': 2,
                                        '0x10e12': 3,
                                        '0x10e13': 3,
                                        '0x10e14': 5,
                                        '0x10e15': 5
                                        }

        self.polylinePropertiesDash = {'0xa': Qt.DotLine,
                                       '0xd': Qt.DotLine,
                                       '0x14': Qt.DashLine,
                                       '0x1c': Qt.DashDotLine,
                                       '0x18': Qt.DashLine,
                                       '0x4b': Qt.DashLine,
                                       '0x10e11': Qt.DashLine,
                                       '0x10e12': Qt.DashLine,
                                       '0x10e13': Qt.DashLine,
                                       '0x10e14': Qt.DashLine,
                                       '0x10e15': Qt.DashLine
                                       }

        #polygone definitions
        self.polygonePropertiesFillColour = {'0x4': QColor('olive'),
                                             '0x5': QColor('silver'),
                                             '0x13': QColor('brown'),
                                             '0x14': Qt.green, '0x15': Qt.green, '0x16': Qt.green, '0x17': Qt.green,
                                             '0x19': QColor('mistyrose'),
                                             '0x1a': QColor('gray'),
                                             '0x28': Qt.blue,
                                             '0x29': Qt.blue,
                                             '0x32': Qt.blue,
                                             '0x3b': Qt.blue,
                                             '0x3c': Qt.blue,
                                             '0x3d': Qt.blue,
                                             '0x3e': Qt.blue,
                                             '0x3f': Qt.blue,
                                             '0x40': Qt.blue,
                                             '0x41': Qt.blue,
                                             '0x42': Qt.blue,
                                             '0x43': Qt.blue,
                                             '0x44': Qt.blue,
                                             '0x45': Qt.blue,
                                             '0x46': Qt.blue,
                                             '0x47': Qt.blue,
                                             '0x48': Qt.blue,
                                             '0x49': Qt.blue,
                                             '0x4e': QColor('limegreen'),
                                             '0x4f': QColor('yellowgreen')
                                             }

    def read_icons(self):
        filename = os.path.join('icons', 'skorka.txt')
        for poi_type, icon in misc_functions.read_icons_from_skin_file(filename).items():
            self.poi_icons[poi_type] = QPixmap(icon)

