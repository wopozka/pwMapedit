#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from urllib.error import URLError

from PyQt5.QtWidgets import QGraphicsView, QGraphicsPathItem
from PyQt5.QtCore import QPointF, Qt, QEvent, QObject, pyqtSignal, QThreadPool, QRunnable
from PyQt5.QtGui import QMouseEvent, QPainterPath, QPolygonF, QBrush
import math

import map_items
import pwmapedit_constants
from pwmapedit_constants import IGNORE_TRANSFORMATION_TRESHOLD
import os.path
import urllib.request
from web_layers import WebLayerTile
from pathlib import Path

import misc_functions
from singleton_store import Store


class GetWebLayerPictureSignals(QObject):
    # https://www.pythonguis.com/tutorials/multithreading-pyqt-applications-qthreadpool/
    download_failed = pyqtSignal(str, name='DownloadFailed')
    download_finished = pyqtSignal(tuple, name='DownloadFinished')

class GetWebLayerPictureWorker(QRunnable):
    # https://realpython.com/python-pyqt-qthread/

    def __init__(self, tile_def, tile_url, web_layer, current_zoom):
        self.tile_def = tile_def
        self.tile_url = tile_url
        self.web_layer = web_layer
        self.current_zoom = current_zoom
        self.www_signals = GetWebLayerPictureSignals()
        super(GetWebLayerPictureWorker, self).__init__()

    def run(self):
        req = urllib.request.Request(url=self.tile_url, headers={'User-Agent': 'pwMapedit'})
        try:
            with urllib.request.urlopen(req) as f:
                content = f.read()
                # print('obrazek przeczytany')
        except urllib.error.HTTPError as http_error:
            print('Nie moglem sciagnac obrazka http_error: ', http_error.url)
            self.www_signals.download_failed.emit(self.tile_url)
        except urllib.error.URLError as url_error:
            print('Nie moglem sciagnac obrazka: ', self.tile_url)
            print(url_error.reason)
            self.www_signals.download_failed.emit(self.tile_url)
        except ConnectionResetError as connection_error:
            print('Nie moglem sciagnac obrazka: ', self.tile_url)
            self.www_signals.download_failed.emit(self.tile_url)
        else:
            try:
                with open(self.tile_def.file_path, 'wb') as f:
                    f.write(content)
                    print('obrazek zapisany')
                self.www_signals.download_finished.emit((self.tile_url, self.web_layer,
                                                         self.current_zoom, self.tile_def,))
            except FileNotFoundError:
                self.www_signals.download_failed.emit(self.tile_url)
                print(f'Nie moglem zapisac obrazka: {self.tile_def.file_path}')
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
        self._hand_made_right_button_press_event = False
        self._hand_made_right_button_release_event = False
        self.web_layer = None
        self.currently_downloading_web_layer_files = set()
        self._poly_creation_nodes = None
        self._poly_creation_drawn_poly = None
        self._mouse_scene_coordinates = None
        self._items_under_cursor = []
        self._item_under_cursor_index = None

    def get_corners_geo_coordinates(self):
        left_top_corner = self.mapToScene(0, 0)
        right_bottom_corner = self.mapToScene(self.viewport().size().width(), self.viewport().size().height())
        left_top_geo = self.projection.canvas_to_geo(left_top_corner.x(), left_top_corner.y())
        right_bottom_geo =  self.projection.canvas_to_geo(right_bottom_corner.x(), right_bottom_corner.y())
        return left_top_geo, right_bottom_geo

    def get_item_ignores_transformations(self):
        return self.item_ignores_transformations

    # def get_pw_mapedit_mode(self):
    #     return self.parent.pw_mapedit_mode

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
            # self.main_window_status_bar.showMessage(msg_coords + msg_view_render + msg_map_scale)
            self.main_window_status_bar.set_info_text(msg_coords + msg_view_render + msg_map_scale)
        else:
            # cur_msg = self.main_window_status_bar.currentMessage()
            cur_msg = self.main_window_status_bar.get_info_text()
            new_msg = cur_msg.split('view_render')[0]
            # self.main_window_status_bar.showMessage(new_msg + msg_view_render + msg_map_scale)
            self.main_window_status_bar.set_info_text(new_msg + msg_view_render + msg_map_scale)

    def set_web_layer(self, layer):
        # uzywane przy wlaczaniu i wylaczaniu weblayer
        self.web_layer = layer
        if self.web_layer is not None:
            # self.weblayers_get_picture_names()
            self.weblayers_put_background_weblayer_pictures()
        else:
            self.scene().remove_web_layer_graphics()

    def keyPressEvent(self, event):
        mode = self.scene().get_pw_mapedit_mode()
        if mode == pwmapedit_constants.Tools.CREATE_POLYLINE or mode == pwmapedit_constants.Tools.CREATE_POLYGON:
            # if self._poly_creation_nodes is not None:
            if self.scene().closest_node_circle_position() is not None:
                position = self.scene().closest_node_circle_position()
            else:
                position = self._mouse_scene_coordinates
            if event.key() == Qt.Key_A:
                if self._poly_creation_nodes is None:
                    self._poly_creation_nodes = [position]
                else:
                    self._poly_creation_nodes.append(position)
            elif event.key() == Qt.Key_D:
                if self._poly_creation_nodes is not None:
                    if len(self._poly_creation_nodes) > 1:
                        self._poly_creation_nodes.pop()
                    else:
                        self._poly_creation_nodes = None
            elif event.key() == Qt.Key_Space:
                print(self._poly_creation_nodes)
                if mode == pwmapedit_constants.Tools.CREATE_POLYLINE:
                    self.scene().command_create_polyline(self._poly_creation_nodes)
                elif mode == pwmapedit_constants.Tools.CREATE_POLYGON:
                    self.scene().command_create_polygon(self._poly_creation_nodes)
                self._poly_creation_nodes = None
                self.scene().removeItem(self._poly_creation_drawn_poly)
                self._poly_creation_drawn_poly = None

        print('key pressed', event.key())
        super().keyPressEvent(event)

    # new events definitions:
    def mouseMoveEvent(self, event):
        if self.scene() is None:
            return
        self._mouse_scene_coordinates = self.mapToScene(event.pos())
        if event.buttons() == Qt.RightButton:
            super(mapRender, self).mouseMoveEvent(event)
            if self.ruler is not None:
                self.ruler.move_to()
            # self.weblayers_get_picture_names()
            self.weblayers_put_background_weblayer_pictures()
        else:
            self.scene().closest_node_circle_remove()
            if self.scene().stick_to_neighbours():
                self.scene().closest_point_to_point(self.mapToScene(event.pos()), excluded_item=None)
            mode = self.scene().get_pw_mapedit_mode()
            if mode == pwmapedit_constants.Tools.CREATE_POLYLINE or mode == pwmapedit_constants.Tools.CREATE_POLYGON:
                # jesli nody nowo utworzonego polygonu i polyline sa obecne wtedy go stworz
                if self._poly_creation_nodes is not None:
                    if self._poly_creation_drawn_poly is None:
                        self._poly_creation_drawn_poly = QGraphicsPathItem()
                        self.scene().addItem(self._poly_creation_drawn_poly)
                        self._poly_creation_drawn_poly.setZValue(pwmapedit_constants.NEW_OBJECT_CREATION_Z_VAL)
                    qpp = QPainterPath()
                    qpp.addPolygon(QPolygonF(self._poly_creation_nodes + [self.mapToScene(event.pos())]))
                    if mode == pwmapedit_constants.Tools.CREATE_POLYGON:
                        qpp.closeSubpath()
                    self._poly_creation_drawn_poly.setPath(qpp)
                    if mode == pwmapedit_constants.Tools.CREATE_POLYGON:
                        self._poly_creation_drawn_poly.setBrush(Qt.yellow)
                else:
                    # w przeciwnym przypadku oznacza to ze usunales wszystkie nody, usun tez nowo utworzony obiekt
                    # ale tylko w przypadku gdy on istnieje
                    if self._poly_creation_drawn_poly is not None:
                        self.scene().removeItem(self._poly_creation_drawn_poly)
                        self._poly_creation_drawn_poly = None


            super(mapRender, self).mouseMoveEvent(event)
            self.set_status_bar(event=event)

    def mousePressEvent(self, event):
        if self.scene() is None:
            return
        mode = self.scene().get_pw_mapedit_mode()
        # w przypadku gdy klikniesz prawym przyciskiem myszy to emulujesz drag mode. Wtedy mousePressEvent jest
        # generowany ponownie z handmade_eventem, ale chcemy tylko aby super() zostało wywołane
        if self._hand_made_right_button_press_event:
            self._hand_made_right_button_press_event = False
        else:
            # support for tools
            if self._right_mouse_button_event_position is None and event.button() == Qt.LeftButton:
                if mode == pwmapedit_constants.Tools.CREATE_POINT:
                    pass
                elif mode == pwmapedit_constants.Tools.CREATE_POLYLINE:
                    pass
                elif mode == pwmapedit_constants.Tools.CREATE_POLYGON:
                    pass
                else:
                    pass

            # https://stackoverflow.com/questions/55642436/change-scrollhanddrag-form-left-click-to-middle-click-pyqt5
            if event.button() == Qt.RightButton:
                self._hand_made_right_button_press_event = True
                self.setDragMode(QGraphicsView.ScrollHandDrag)
                self._right_mouse_button_event_position = event.pos()
                handmade_event = QMouseEvent(QEvent.MouseButtonPress, QPointF(event.pos()), Qt.LeftButton,
                                             event.buttons(), Qt.KeyboardModifiers())
                self.setInteractive(False)
                self.mousePressEvent(handmade_event)
        # klikniecie na obiekt powinno go podswietlic - zaznaczyc. Ale tylo w trybie select albo nodes
        if mode == pwmapedit_constants.Tools.SELECT_OBJECTS or mode == pwmapedit_constants.Tools.EDIT_NODES:
            items_under_cursor = self.items(event.pos())
            if (not items_under_cursor or isinstance(items_under_cursor[0], map_items.GripItem) or
                    isinstance(items_under_cursor[0], map_items.PoiAsPixmap) or len(items_under_cursor) == 1):
                super().mousePressEvent(event)
                return
            else:
                if isinstance(items_under_cursor[0], map_items.HoveredShapePainterPath):
                    items_under_cursor = items_under_cursor[1:]
                if items_under_cursor != self._items_under_cursor:
                    self._items_under_cursor = items_under_cursor
                    self._item_under_cursor_index = None
                if self._item_under_cursor_index is None:
                    self._item_under_cursor_index = 0
                else:
                    self._item_under_cursor_index += 1
                    if self._item_under_cursor_index >= len(items_under_cursor):
                        self._item_under_cursor_index = 0

                self.scene().clearSelection()
                self._items_under_cursor[self._item_under_cursor_index].setSelected(True)

                # if not items_under_cursor:
                #     super().mousePressEvent(event)
                # elif len(items_under_cursor) == 1:
                #     super().mousePressEvent(event)
                # elif isinstance(items_under_cursor[0], map_items.HoveredShapePainterPath):
                #     super().mousePressEvent(event)
                # else:
                #     if self.scene() is not None:
                #         self.scene().clearSelection()
                #     if items_under_cursor:
                #         items_under_cursor[1].setSelected(True)
        else:
            print('mode aktualne:', mode)
        super().mousePressEvent(event)


    def mouseReleaseEvent(self, event):
        if self.scene() is None:
            return
        if self._hand_made_right_button_release_event:
            self._hand_made_right_button_release_event = False
        else:
            mode = self.scene().get_pw_mapedit_mode()
            print(self._right_mouse_button_event_position)
            if self._right_mouse_button_event_position is None and event.button() == Qt.LeftButton:
                print('rysuje')
                if self.scene().closest_node_circle_position() is not None:
                    position = self.scene().closest_node_circle_position()
                else:
                    position = self.mapToScene(event.pos())
                if mode == pwmapedit_constants.Tools.CREATE_POINT:
                    self.scene().command_create_poi(position)
                elif mode == pwmapedit_constants.Tools.CREATE_POLYLINE or mode == pwmapedit_constants.Tools.CREATE_POLYGON:
                    if self._poly_creation_nodes is None:
                        self._poly_creation_nodes = [position]
                    else:
                        self._poly_creation_nodes.append(position)
                else:
                    pass
            # https://stackoverflow.com/questions/55642436/change-scrollhanddrag-form-left-click-to-middle-click-pyqt5
            if event.button() == Qt.RightButton:
                self._right_mouse_button_event_position = None
                self._hand_made_right_button_release_event = True
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
                    worker.www_signals.download_finished.connect(self.weblayers_get_data_from_thread)
                    worker.www_signals.download_failed.connect(self.weblayers_download_error)
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

