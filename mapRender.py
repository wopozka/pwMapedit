#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import QGraphicsView
from singleton_store import Store

class mapRender(QGraphicsView):
    """The main map canvas definitions residue here"""
    def __init__(self, master):
        super(mapRender, self).__init__(master)
        self.main_window_status_bar = None
        self._curent_scene_mouse_coords = None
        self._curent_view_mouse_coords = None

    def set_main_window_status_bar(self, status_bar):
        self.main_window_status_bar = status_bar

    def curent_scene_mouse_coords(self):
        return self._curent_scene_mouse_coords

    def curent_view_mouse_coords(self):
        return self._curent_view_mouse_coords

    # new events definitions:
    def mouseMoveEvent(self, event):
        self._curent_view_mouse_coords = event.pos()
        self._curent_scene_mouse_coords = self.mapToScene(self._curent_view_mouse_coords)
        x = self._curent_scene_mouse_coords.x()
        y = self._curent_scene_mouse_coords.y()
        lon, lat = Store.projection.canvas_to_geo(x, y)
        self.main_window_status_bar.showMessage('(%.7f, %.7f)' % (lon, lat))
