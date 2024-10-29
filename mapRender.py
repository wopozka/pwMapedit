#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import QGraphicsView
from PyQt5.QtCore import QPointF, Qt, QEvent, QObject, pyqtSignal, QThreadPool, QRunnable
from PyQt5.QtGui import QMouseEvent
import math
from pwmapedit_constants import IGNORE_TRANSFORMATION_TRESHOLD
import os.path
import urllib.request
from web_layers import WebLayerTile
from pathlib import Path

import misc_functions
from singleton_store import Store


class GetWebLayerPictureSignals(QObject):
    # https://www.pythonguis.com/tutorials/multithreading-pyqt-applications-qthreadpool/
    download_failed = pyqtSignal(str)
    download_finished = pyqtSignal(tuple)

class GetWebLayerPictureWorker(QRunnable):
    # https://realpython.com/python-pyqt-qthread/

    def __init__(self, tile_def, tile_url, web_layer, current_zoom):
        self.tile_def = tile_def
        self.tile_url = tile_url
        self.web_layer = web_layer
        self.current_zoom = current_zoom
        self.signals = GetWebLayerPictureSignals()
        super(GetWebLayerPictureWorker, self).__init__()

    def run(self):
        req = urllib.request.Request(url=self.tile_url, headers={'User-Agent': 'pwMapedit'})
        try:
            with urllib.request.urlopen(req) as f:
                content = f.read()
                print('obrazek przeczytany')
        except urllib.error.HTTPError:
            print('Nie moglem sciagnac obrazka: ', self.tile_url)
            self.signals.download_failed(self.tile_url)
        else:
            with open(self.tile_def.file_path, 'wb') as f:
                f.write(content)
                print('obrazek zapisany')
            self.signals.download_finished.emit((self.tile_url, self.web_layer, self.current_zoom, self.tile_def,))
        # self.emit.finished(self.tile_def)


class mapRender(QGraphicsView):
    """The main map canvas definitions residue here"""
    def __init__(self, parent, *args, projection=None, **kwargs):
        super(mapRender, self).__init__(parent, *args, **kwargs)
        self.parent = parent
        self.ruler = None
        self.map_scale = 1
        self.item_ignores_transformations = None
        self.main_window_status_bar = None
        self._curent_scene_mouse_coords = None
        self._curent_view_mouse_coords = None
        self.projection = None
        if projection is not None:
            self.projection = projection

        self._right_mouse_button_event_position = None
        self.web_layer = None
        self.currently_downloading_web_layer_files = set()

    def get_corners_geo_coordinates(self):
        left_top_corner = self.mapToScene(0, 0)
        right_bottom_corner = self.mapToScene(self.viewport().size().width(), self.viewport().size().height())
        left_top_geo = self.projection.canvas_to_geo(left_top_corner.x(), left_top_corner.y())
        right_bottom_geo =  self.projection.canvas_to_geo(right_bottom_corner.x(), right_bottom_corner.y())
        return left_top_geo, right_bottom_geo

    def get_item_ignores_transformations(self):
        return self.item_ignores_transformations

    def get_pw_mapedit_mode(self):
        return self.parent.pw_mapedit_mode

    def set_ruler(self, ruler):
        self.ruler = ruler

    def set_main_window_status_bar(self, status_bar):
        self.main_window_status_bar = status_bar

    def curent_scene_mouse_coords(self):
        return self._curent_scene_mouse_coords

    def curent_view_mouse_coords(self):
        return self._curent_view_mouse_coords

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.ruler is not None:
            self.ruler.move_to()
        # self.weblayers_get_picture_names()
        self.weblayers_put_background_weblayer_pictures()

    def set_map_scale(self, map_scale_factor):
        self.map_scale *= map_scale_factor
        self.set_status_bar()
        # coords1 = self.projection.canvas_to_geo(self.mapToScene(0, 0).x(), self.mapToScene(0, 0).y())
        # coords2 = self.projection.canvas_to_geo(self.mapToScene(0, 10).x(), self.mapToScene(0, 10).y())
        # print(misc_functions.vincenty_distance(coords1, coords2))

    def get_map_scale(self):
        return self.map_scale

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

    def set_web_layer(self, layer):
        # uzywane przy wlaczaniu i wylaczaniu weblayer
        self.web_layer = layer
        if self.web_layer is not None:
            # self.weblayers_get_picture_names()
            self.weblayers_put_background_weblayer_pictures()
        else:
            self.scene().remove_web_layer_graphics()


    # new events definitions:
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.RightButton:
            super(mapRender, self).mouseMoveEvent(event)
            if self.ruler is not None:
                self.ruler.move_to()
            # self.weblayers_get_picture_names()
            self.weblayers_put_background_weblayer_pictures()
        else:
            super(mapRender, self).mouseMoveEvent(event)
            self.set_status_bar(event=event)

    def mousePressEvent(self, event):
        # https://stackoverflow.com/questions/55642436/change-scrollhanddrag-form-left-click-to-middle-click-pyqt5
        if event.button() == Qt.RightButton:
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            self._right_mouse_button_event_position = event.pos()
            handmade_event = QMouseEvent(QEvent.MouseButtonPress, QPointF(event.pos()), Qt.LeftButton,
                                         event.buttons(), Qt.KeyboardModifiers())
            self.setInteractive(False)
            self.mousePressEvent(handmade_event)

        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        # https://stackoverflow.com/questions/55642436/change-scrollhanddrag-form-left-click-to-middle-click-pyqt5
        if event.button() == Qt.RightButton:
            self._right_mouse_button_event_position = None
            self.setDragMode(QGraphicsView.NoDrag)
            self.setInteractive(True)
            handmade_event = QMouseEvent(QEvent.MouseButtonRelease, QPointF(event.pos()), Qt.LeftButton,
                                         event.buttons(), Qt.KeyboardModifiers())
            self.mouseReleaseEvent(handmade_event)
        super().mouseReleaseEvent(event)


    def weblayers_download_error(self, tile_url):
        # if for any reason file will not be downloaded from web, remove the file from currently downloaded files
        self.currently_downloading_web_layer_files.remove(tile_url)

    def weblayers_get_data_from_thread(self, tile_def):
        # zakonczylem pobieranie, usun informacje ze plik jest teraz w trakcie sciagania
        self.currently_downloading_web_layer_files.remove(tile_def[0])

        # jesli w trakcie sciagania obrazkow w watku wylaczymy warstwę www, wtedy sefl.web_layer będzie None
        # dodatkowo potwierdz ze obrazek jest dla danego, aktualnie wlaczonego weblayer, inaczej zignoruj
        if (self.web_layer is not None and tile_def[1] == self.web_layer.get_current_web_layer()
                and tile_def[2] == self.web_layer.get_zoom()):
            self.scene().set_web_layer_graphic(tile_def[3], self.web_layer.get_zoom())

    def weblayers_get_picture_names(self):
        scene_geo_coords = self.get_corners_geo_coordinates()
        self.web_layer.set_zoom_from_scale(self.ruler.get_map_scale())
        picture_paths = self.web_layer.get_tiles_paths(scene_geo_coords[0][0], scene_geo_coords[0][1],
                                                       scene_geo_coords[1][0], scene_geo_coords[1][1])
        print(picture_paths)
        return picture_paths

    def weblayers_put_background_weblayer_pictures(self):
        if self.web_layer is None:
            return
        tiles_defs = self.weblayers_get_picture_names()
        self.weblayers_put_files_to_scene(tiles_defs)

    def weblayers_put_files_to_scene(self, tiles_defs):
        pool = QThreadPool.globalInstance()
        for tile_def in tiles_defs:
            if os.path.exists(tile_def.file_path):
                self.scene().set_web_layer_graphic(tile_def, self.web_layer.get_zoom())
            else:
                tile_url = self.web_layer.get_tile_url(tile_def.xtile, tile_def.ytile)
                if tile_url not in self.currently_downloading_web_layer_files:
                    self.currently_downloading_web_layer_files.add(tile_url)
                    directory = Path(os.path.dirname(tile_def.file_path))
                    if not directory.exists():
                        directory.mkdir(parents=True, exist_ok=True)

                    # web_layer_thread = QThread()
                    worker = GetWebLayerPictureWorker(tile_def, tile_url, self.web_layer.get_current_web_layer(),
                                                      self.web_layer.get_zoom())
                    worker.signals.download_finished.connect(self.weblayers_get_data_from_thread)
                    worker.signals.download_failed.connect(self.weblayers_download_error)
                    pool.start(worker)

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
        # self.weblayers_get_picture_names()
        self.weblayers_put_background_weblayer_pictures()

    def zoom_in_command(self):
        self.setInteractive(False)
        previous_map_scale = self.get_map_scale()
        center_coords = self.mapToScene(self.width() // 2, self.height() // 2)
        curent_mouse_coords = self.curent_scene_mouse_coords()
        mouse_center_vector = center_coords - curent_mouse_coords
        mouse_center_vector_lenght = math.sqrt(mouse_center_vector.x() ** 2 + mouse_center_vector.y() ** 2)
        self.set_map_scale(1.1)
        if self.get_map_scale() < IGNORE_TRANSFORMATION_TRESHOLD <= previous_map_scale:
            self.item_ignores_transformations = -1
        else:
            self.item_ignores_transformations = 0
        self.scale(1.1, 1.1)
        center_coords1 = self.mapToScene(self.width() // 2, self.height() // 2)
        curent_mouse_coords1 = self.mapToScene(self.curent_view_mouse_coords())
        mouse_center_vector1 = center_coords1 - curent_mouse_coords1
        vector_lenght_factor = math.sqrt(mouse_center_vector1.x() ** 2 + mouse_center_vector1.y() ** 2) / \
                               mouse_center_vector_lenght
        new_position = curent_mouse_coords + mouse_center_vector * vector_lenght_factor
        self.centerOn(new_position)
        self.setInteractive(True)

    def zoom_out_command(self):
        self.setInteractive(False)
        previous_map_scale = self.get_map_scale()
        self.set_map_scale(0.9)
        if self.get_map_scale() > IGNORE_TRANSFORMATION_TRESHOLD >= previous_map_scale:
            self.item_ignores_transformations = 1
        else:
            self.item_ignores_transformations = 0
        self.scale(0.9, 0.9)
        self.setInteractive(True)

