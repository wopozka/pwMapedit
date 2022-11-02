#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import QGraphicsView
from singleton_store import Store

class mapRender(QGraphicsView):
    """The main map canvas definitions residue here"""
    def __init__(self, master):
        super(mapRender, self).__init__(master)

    # new events definitions:
    def mouseMoveEvent(self, event):
        map_coords = self.mapToScene(event.pos())
        lon, lat = Store.projection.canvas_to_geo(map_coords.x(), map_coords.y())
        Store.status_bar.showMessage('(%s,%s)' % (lon, lat))
