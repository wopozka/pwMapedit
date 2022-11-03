#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import QGraphicsView
from singleton_store import Store

class mapRender(QGraphicsView):
    """The main map canvas definitions residue here"""
    def __init__(self, master):
        super(mapRender, self).__init__(master)
        self.main_window_status_bar = None

    def set_main_window_status_bar(self, status_bar):
        self.main_window_status_bar = status_bar

    # new events definitions:
    def mouseMoveEvent(self, event):
        map_coords = self.mapToScene(event.pos())
        lon, lat = Store.projection.canvas_to_geo(map_coords.x(), map_coords.y())
        self.main_window_status_bar.showMessage('(%.7f, %.7f)' % (lon, lat))
