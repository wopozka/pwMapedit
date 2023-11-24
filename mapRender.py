#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import QGraphicsView
from PyQt5.QtCore import QPointF, Qt
import math

import misc_functions
from singleton_store import Store


class mapRender(QGraphicsView):
    """The main map canvas definitions residue here"""
    def __init__(self, master, *args, projection=None, **kwargs):
        super(mapRender, self).__init__(master, *args, **kwargs)
        self.master = master
        self.ruler = None
        self.map_scale = 1
        self.main_window_status_bar = None
        self._curent_scene_mouse_coords = None
        self._curent_view_mouse_coords = None
        self.projection = None
        if projection is not None:
            self.projection = projection

    def set_ruler(self, ruler):
        self.ruler = ruler

    def set_main_window_status_bar(self, status_bar):
        self.main_window_status_bar = status_bar

    def curent_scene_mouse_coords(self):
        return self._curent_scene_mouse_coords

    def curent_view_mouse_coords(self):
        return self._curent_view_mouse_coords

    def set_map_scale(self, map_scale_factor):
        self.map_scale *= map_scale_factor
        self.set_status_bar()
        # coords1 = self.projection.canvas_to_geo(self.mapToScene(0, 0).x(), self.mapToScene(0, 0).y())
        # coords2 = self.projection.canvas_to_geo(self.mapToScene(0, 10).x(), self.mapToScene(0, 10).y())
        # print(misc_functions.vincenty_distance(coords1, coords2))

    def set_status_bar(self, event=None):
        msg_view_render = 'view_render scale: %.3f, ' % self.map_scale
        msg_map_scale = 'map scale: 1:%.0f' % self.ruler.get_map_scale()
        if event is not None:
            self._curent_view_mouse_coords = event.pos()
            self._curent_scene_mouse_coords = self.mapToScene(self._curent_view_mouse_coords)
            x = self._curent_scene_mouse_coords.x()
            y = self._curent_scene_mouse_coords.y()
            lon, lat = self.projection.canvas_to_geo(x, y)
            msg_coords = '(%.7f, %.7f), (%.1f, %.1f), ' % (lon, lat, x, -y)
            self.main_window_status_bar.showMessage(msg_coords + msg_view_render + msg_map_scale)
        else:
            cur_msg = self.main_window_status_bar.currentMessage()
            new_msg = cur_msg.split('view_render')[0]
            self.main_window_status_bar.showMessage(new_msg + msg_view_render + msg_map_scale)

    # new events definitions:
    def mouseMoveEvent(self, event):
        super(mapRender, self).mouseMoveEvent(event)
        self.set_status_bar(event=event)

    def wheelEvent(self, event):
        if event.modifiers() == Qt.ControlModifier:
            if event.angleDelta().y() < 0:
                # self.zoom_out_funct()
                self.zoom_out_command()
            elif event.angleDelta().y() > 0:
                self.zoom_in_command()
            if self.ruler is not None:
                self.ruler.scale_to()
        else:
            super(mapRender, self).wheelEvent(event)
            if self.ruler is not None:
                self.ruler.move_to()

    def zoom_in_command(self):
        center_coords = self.mapToScene(self.width() // 2, self.height() // 2)
        curent_mouse_coords = self.curent_scene_mouse_coords()
        mouse_center_vector = center_coords - curent_mouse_coords
        mouse_center_vector_lenght = math.sqrt(mouse_center_vector.x() ** 2 + mouse_center_vector.y() ** 2)
        self.scale(1.1, 1.1)
        self.set_map_scale(1.1)
        center_coords1 = self.mapToScene(self.width() // 2, self.height() // 2)
        curent_mouse_coords1 = self.mapToScene(self.curent_view_mouse_coords())
        mouse_center_vector1 = center_coords1 - curent_mouse_coords1
        vector_lenght_factor = math.sqrt(mouse_center_vector1.x() ** 2 + mouse_center_vector1.y() ** 2) / \
                               mouse_center_vector_lenght
        new_position = curent_mouse_coords + mouse_center_vector * vector_lenght_factor
        self.centerOn(new_position)


    def zoom_out_command(self):
        self.scale(0.9, 0.9)
        self.set_map_scale(0.9)
