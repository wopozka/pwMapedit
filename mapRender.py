#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import QGraphicsView
from PyQt5.QtCore import QPointF, Qt
from singleton_store import Store

class mapRender(QGraphicsView):
    """The main map canvas definitions residue here"""
    def __init__(self, master, zoom_in_funct, zoom_out_funct, *args, projection=None, **kwargs):
        super(mapRender, self).__init__(master, *args, **kwargs)
        self.master = master
        self.zoom_in_funct = zoom_in_funct
        self.zoom_out_funct = zoom_out_funct
        self.map_scale = 1
        self.main_window_status_bar = None
        self._curent_scene_mouse_coords = None
        self._curent_view_mouse_coords = None
        self.projection = None
        if projection is not None:
            self.projection = projection

    def set_main_window_status_bar(self, status_bar):
        self.main_window_status_bar = status_bar

    def curent_scene_mouse_coords(self):
        return self._curent_scene_mouse_coords

    def curent_view_mouse_coords(self):
        return self._curent_view_mouse_coords

    def set_map_scale(self, map_scale_factor):
        self.map_scale *= map_scale_factor
        self.set_status_bar()

    def set_status_bar(self, event=None):
        if event is not None:
            self._curent_view_mouse_coords = event.pos()
            self._curent_scene_mouse_coords = self.mapToScene(self._curent_view_mouse_coords)
            x = self._curent_scene_mouse_coords.x()
            y = self._curent_scene_mouse_coords.y()
            lon, lat = self.projection.canvas_to_geo(x, y)
            self.main_window_status_bar.showMessage('(%.7f, %.7f), mapscale: %.7f' % (lon, lat, self.map_scale))
        else:
            cur_msg = self.main_window_status_bar.currentMessage()
            new_msg = cur_msg.split('mapscale')[0] + 'mapscale: %.7f' % self.map_scale
            self.main_window_status_bar.showMessage(new_msg)

    # new events definitions:
    def mouseMoveEvent(self, event):
        super(mapRender, self).mouseMoveEvent(event)
        self.set_status_bar(event=event)

    def wheelEvent(self, event):
        if event.modifiers() == Qt.ControlModifier:
            if event.angleDelta().y() < 0:
                self.zoom_out_funct()
            elif event.angleDelta().y() > 0:
                self.zoom_in_funct()
        else:
            super(mapRender, self).wheelEvent(event)
