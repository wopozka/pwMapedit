#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QToolBar, QStatusBar, QAction, QActionGroup, \
    QProgressBar, QLabel
from PyQt5.QtWidgets import QGraphicsScene, QGraphicsView, QFileDialog, QShortcut, QUndoStack
from PyQt5.QtCore import Qt, QObject, pyqtSignal, QThread
from PyQt5.QtGui import QKeySequence, QClipboard
import sys
import mapData
import mapCanvas
import mapRender
import map_items
import map_object_properties
import projection
import map_obj_properties_dockwidget
import pwmapedit_constants
import misc_functions
import web_layers
import tempfile

class MapUndoStack(QUndoStack):
    def __init__(self, parent):
        self.parent = parent
        self.undo_button = None
        self.redo_button = None
        super(MapUndoStack, self).__init__(parent)

    def set_undo_button(self, undo_button):
        self.undo_button = undo_button

    def set_redo_button(self, redo_button):
        self.redo_button = redo_button

    def push(self, command, q_undo_command=None):
        super().push(command)
        self.undo_button.setToolTip(self.undoText())


class MapFileOpener(QObject):
    # class for reading the file in background
    finished = pyqtSignal()
    map_items_map_canvas = pyqtSignal(object)
    progress = pyqtSignal(str, int)
    draw_poi_polyline_polygon = pyqtSignal(list, object)

    def __init__(self, parent, file_name, map_objects_properties, _projection, undo_redo_stack):
        self.parent = parent
        self.filename = file_name
        self.map_objects_properties = map_objects_properties
        self.projection = _projection
        self.undo_redo_stack = undo_redo_stack
        super(MapFileOpener, self).__init__()

    def run(self):
        self.wczytaj_rekordy()

    def wczytaj_rekordy(self):
        print('wczytuje rekordy')
        _map_object_properties = map_object_properties.MapObjectsProperties()
        _projection = projection.Mercator({})
        map_objects = mapData.mapData(self.filename, map_objects_properties=_map_object_properties,
                                      projection=_projection)

        # Firstly. At the end of file there might be attachments (files or weblayers). The format is as below:
        # ;@File *, for file attached
        # ;@WEBMAP *, for web layers attached
        # we have to skipp these data as well.
        with open(self.filename, 'r', encoding='cp1250') as mp_file:
            zawartosc_pliku_mp = mp_file.readlines()
        while zawartosc_pliku_mp[-1].startswith(';@'):
            print(zawartosc_pliku_mp[-1])
            # self.listOfAttachments.append(zawartosc_pliku_mp[-1].strip())
            del (zawartosc_pliku_mp[-1])

        #remove all empty lines until there is the last [END] in the file
        while not zawartosc_pliku_mp[-1].strip():
            del (zawartosc_pliku_mp[-1])

        # after removal of attachments we can measure the lenght of the whole file
        zawartosc_pliku_mp_len = len(zawartosc_pliku_mp)
        b = 0
        self.progress.emit('set_maximum', zawartosc_pliku_mp_len)
        # first lets skip the file header
        # map_canvas = mapCanvas.mapCanvas(self.parent, 0, 0, 400, 200, projection=self.projection,
        #                                  undo_redo_stack=self.undo_redo_stack)
        while b < zawartosc_pliku_mp_len:
            # print(b)
            if zawartosc_pliku_mp[b].strip() not in pwmapedit_constants.MAP_OBJECT_TYPES:
                b += 1
                map_objects.map_header.append(zawartosc_pliku_mp[b])
            else:
                b -= 1
                del(map_objects.map_header[-1])
                break

        # we skipped the header, but at the same time we might have skipped
        # the first comment, try to recover it

        print(map_objects.map_header)
        while b >= 0:
            print(zawartosc_pliku_mp[b])
            if zawartosc_pliku_mp[b].strip().startswith(';'):
                b -= 1
                del(map_objects.map_header[-1])
            else:
                break

        print(map_objects.map_header)
        print('zakonczylen obrabianie naglowka. Wartosc b: %s' % b)
        self.progress.emit('set_value', b)
        objs_to_draw = []
        while b < zawartosc_pliku_mp_len:
            # print(b)
            mp_record = []
            mpfileline = zawartosc_pliku_mp[b].strip()
            while not mpfileline.startswith(pwmapedit_constants.MAP_OBJECT_END) and b < zawartosc_pliku_mp_len-1:

                mp_record.append(mpfileline)
                b += 1
                mpfileline = zawartosc_pliku_mp[b]

            poi_poly_type, obj_comment, obj_data = misc_functions.map_strings_record_to_dict_record(mp_record)
            if poi_poly_type[0] == pwmapedit_constants.MAP_OBJECT_POI:
                map_object = map_items.PoiAsPixmap(None, map_objects_properties=_map_object_properties,
                                                   projection=_projection)
                map_object.set_data(obj_comment, obj_data)
                map_object.set_mp_data()
                # map_canvas.draw_object_on_map(map_object)
                # self.draw_poi.emit(map_object)
                objs_to_draw.append(map_object)
            elif poi_poly_type[0] == pwmapedit_constants.MAP_OBJECT_POLYLINE:
                map_object = map_items.PolylineQGraphicsPathItem(None,
                                                                 map_objects_properties=_map_object_properties,
                                                                 projection=_projection)
                map_object.set_data(obj_comment, obj_data)
                map_object.set_mp_data()
                # map_canvas.draw_object_on_map(map_object)
                # self.draw_polyline.emit(map_object)
                objs_to_draw.append(map_object)
            elif poi_poly_type[0] == pwmapedit_constants.MAP_OBJECT_POLYGON:
                map_object = map_items.PolygonQGraphicsPathItem(None,
                                                                map_objects_properties=_map_object_properties,
                                                                projection=_projection)
                map_object.set_data(obj_comment, obj_data)
                map_object.set_mp_data()
                # map_canvas.draw_object_on_map(map_object)
                # self.draw_polygon.emit(map_object)
                objs_to_draw.append(map_object)
            elif poi_poly_type[0] == pwmapedit_constants.MAP_OBJECT_RESTRICT:
                map_object = None
            elif poi_poly_type[0] == pwmapedit_constants.MAP_OBJECT_ROADSIGN:
                map_object = None
            else:
                map_object = None

            if map_object is not None:
                map_objects.add_map_object(map_object)
                map_objects.set_map_bounding_box(map_object.obj_bounding_box)
            del mp_record[:]
            if len(objs_to_draw) == 10000:
                print(f'{b}')
                self.draw_poi_polyline_polygon.emit(objs_to_draw, None)
                self.progress.emit('set_value', b)
                objs_to_draw.clear()
            b += 1
            # self.progress.emit('set_value', b)
        if objs_to_draw:
            self.draw_poi_polyline_polygon.emit(objs_to_draw, map_objects)
            self.progress.emit('set_value', b)
        self.finished.emit()
        # self.projection.set_map_bounding_box(map_objects.get_map_bounding_box())
        # self.projection.calculate_data_offset()
        #
        # print('map data ofset', self.projection.earth_radius)
        # # print('bonding box', self.map_bounding_box)

class MapFileSaver(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(str, int)

    def __init__(self, parent, map_objects):
        self.parent = parent
        self.map_objects = map_objects
        self.map_filename = map_objects.get_map_file_name()
        super(MapFileSaver, self).__init__()

    def run(self):
        try:
            with open(self.map_filename, 'w', encoding='cp1250') as map_file:
                self.progress.emit('set_maximum', self.map_objects.records_number())
                map_file.writelines(self.map_objects.map_header)
                for map_object_num, map_object in enumerate(self.map_objects.get_all_map_objects()):
                    map_file.writelines([a + '\n' for a in map_object.to_mp_record()])
                    map_file.writelines(['[END]\n', '\n'])
                    self.progress.emit('set_value', map_object_num + 1)
        except FileNotFoundError:
            pass
        except IOError:
            pass
        self.finished.emit()


class MapeEndlevelWorker(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(str, int)
    get_canvas = pyqtSignal(object, int)

    def __init__(self, map_canvas, map_level):
        self.map_canvas = map_canvas
        if isinstance(map_level, str):
            self.map_level = int(map_level)
        else:
            self.map_level = map_level
        super(MapeEndlevelWorker, self).__init__()

    def run(self):
        if self.map_level == self.map_canvas.current_map_level:
            return
        items = self.map_canvas.items()
        len_items_1_percent = len(items) // 100
        self.progress.emit('set_maximum', len(items))
        self.map_canvas.current_map_level = self.map_level
        self.map_canvas.clearSelection()
        self.map_canvas.set_map_level(self.map_level)
        for item_num, item in enumerate(items):
            if item._accept_map_level_change:
                item.set_map_level()
            if item_num % len_items_1_percent == 0:
                self.progress.emit('set_value', item_num)
        self.get_canvas.emit(self.map_canvas, self.map_level)
        self.finished.emit()

class MapStatusBar(QStatusBar):
    def __init__(self, parent):
        super(MapStatusBar, self).__init__(parent)
        self.progress_bar = QProgressBar(self)
        self.addWidget(self.progress_bar)
        self.info_text = QLabel(self)
        self.addWidget(self.info_text)

    def set_info_text(self, text):
        self.info_text.clear()
        self.info_text.setText(text)

    def get_info_text(self):
        return self.info_text.text()

    def set_progress_bar_maximum(self, val):
        self.progress_bar.setMaximum(val)

    def set_progress_bar_value(self, val):
        self.progress_bar.setValue(val)

    def reset_progress_bar(self):
        self.progress_bar.reset()


class pwMapeditPy(QMainWindow):
    """main application window"""
    map_scale_km = (3000, 2500, 2100, 1800, 1500, 1300, 1100, 920, 770, 650, 550, 460, 390, 330, 280, 240,
                    200, 170, 140, 120, 100,
                    84, 71, 60, 50, 42, 35, 29, 24, 20, 17, 14, 12, 10,
                    8.4, 7.1, 6, 5, 4.2, 3.5, 2.9, 2.4, 2, 1.7, 1.4, 1.2, 1,
                    0.84, 0.71, 0.6, 0.5, 0.42, 0.35, 0.29, 0.24, 0.2, 0.17, 0.14, 0.12, 0.1,
                    0.084, 0.071, 0.06, 0.05, 0.042, 0.035, 0.029, 0.024, 0.02, 0.017, 0.014, 0.012, 0.01,
                    0.0084, 0.0071, 0.006, 0.005, 0.0042, 0.0035, 0.0029, 0.0024, 0.0020, 0.0017, 0.0014, 0.0012, 0.0010)
    def __init__(self, parent, filename):
        super(pwMapeditPy, self).__init__()
        self.parent = parent
        self.filename = filename
        self.map_canvas = None
        self.view = None
        self.setWindowTitle("pwMapeEdit")
        self.status_bar = MapStatusBar(self)
        self.undo_redo_stack = MapUndoStack(self)
        self.projection = projection.Mercator({})
        self.weblayers_cache_folder = tempfile.TemporaryDirectory()
        print(self.weblayers_cache_folder)
        self.tools_actions_group = None
        self.map_level_action_group = None
        self.pw_mapedit_mode = ''
        self.map_level_actions = list()
        self.delete_key_action = None
        self.properties_dock = map_obj_properties_dockwidget.MapObjPropDock(self)
        self.initialize()
        self.generate_shortcuts()
        self.addDockWidget(Qt.LeftDockWidgetArea, self.properties_dock)
        self.map_objects = None
        self.map_objects_properties = map_object_properties.MapObjectsProperties()
        # as reading of file is done in separate thread, we need to know whether all objects were already drawn
        # below variable will be empty if all is drawn
        self.map_objects_to_be_drawn = set()
        self.map_ruler = None
        self.open_save_thread = None
        self.worker_file_parser = None
        self.menu_tools_set_mode()


    def initialize(self):
        # self.protocol("WM_DELETE_WINDOW", self.Quit)
        # lets add toolbar
        toolbar = QToolBar("My main toolbar")
        self.addToolBar(toolbar)
        self.setStatusBar(self.status_bar)
        self.generate_menus()
        self.map_canvas = mapCanvas.mapCanvas(self, 0, 0, 400, 200, projection=self.projection,
                                              undo_redo_stack=self.undo_redo_stack)
        self.view = mapRender.mapRender(self.map_canvas, projection=self.projection)
        self.view.setMouseTracking(True)
        self.view.set_main_window_status_bar(self.status_bar)
        self.setCentralWidget(self.view)
        self.map_ruler = map_items.MapRuler(self.view, self.projection)
        self.map_canvas.addItem(self.map_ruler)
        self.view.set_ruler(self.map_ruler)

    def generate_menus(self):
        menu = self.menuBar()

        # File menu
        file_menu = menu.addMenu("&File")
        for action in self._create_file_actions():
            if action is not None:
                file_menu.addAction(action)
            else:
                file_menu.addSeparator()

        # Edit menu
        edit_menu = menu.addMenu("&Edit")
        edit_menu.setToolTipsVisible(True)
        for action in self._create_edit_actions():
            if action is not None:
                edit_menu.addAction(action)
            else:
                edit_menu.addSeparator()
        select_menu = edit_menu.addMenu('&Select')
        edit_menu.addAction(QAction('&Unselect', self))
        edit_menu.addAction(QAction('&Find', self))
        edit_menu.addAction(QAction('&Delete', self))

        # Select submenu
        for action in self._create_select_actions():
            if action is not None:
                select_menu.addAction(action)
            else:
                select_menu.addSeparator()

        # View menu
        view_menu = menu.addMenu("&View")
        view_menu.addAction(QAction('&Zoom in', self))
        view_menu.addAction(QAction('&Zoom out', self))
        map_level_menu = view_menu.addMenu("&Levels")
        self.map_level_action_group = QActionGroup(self)
        for level in range(5):
            l_act = QAction('&Level ' + str(level), self)
            l_act.setCheckable(True)
            l_act.setData(level)
            l_act.triggered.connect(self.menu_select_map_level)
            if not level:
                l_act.setChecked(True)
            map_level_menu.addAction(l_act)
            self.map_level_actions.append(l_act)
            self.map_level_action_group.addAction(l_act)
        # self.dock_widget_button = QAction('Właściwości', self)
        # self.dock_widget_button.setCheckable(True)
        # self.dock_widget_button.setChecked(True)
        # self.dock_widget_button.triggered.connect(self.dock_widget_on_and_off)
        self.dock_widget_button = self.properties_dock.toggleViewAction()
        self.dock_widget_button.setChecked(True)
        view_menu.addAction(self.dock_widget_button)

        # projection submenu
        # self.menuProjectionVar = tkinter.StringVar()
        # self.menuProjectionVar.set('Mercator')
        projection_menu = menu.addMenu("&Projection")
        mercator_action = QAction('&Mercator', self)
        mercator_action.setCheckable(True)
        mercator_action.setChecked(True)
        utm_action = QAction('&UTM', self)
        utm_action.setCheckable(True)
        projection_menu.addAction(mercator_action)
        projection_menu.addAction(utm_action)
        projection_action_group = QActionGroup(self)
        projection_action_group.addAction(mercator_action)
        projection_action_group.addAction(utm_action)

        # Tools submenu
        tools_menu = menu.addMenu('&Tools')
        self.tools_actions_group = QActionGroup(self)
        for action in self._create_tools_actions():
            if action is not None:
                tools_menu.addAction(action)
                self.tools_actions_group.addAction(action)
            else:
                tools_menu.addSeparator()

        object_menu = tools_menu.addMenu('&Objects')
        for action in self._create_object_actions():
            if action is not None:
                object_menu.addAction(action)
                self.tools_actions_group.addAction(action)
            else:
                object_menu.addSeparator()

        # weblayer menu
        weblayers = menu.addMenu('&Weblayers')
        self.weblayers_actions_group = QActionGroup(self)
        self.weblayers_actions_group.setExclusionPolicy(QActionGroup.ExclusionPolicy.ExclusiveOptional)
        osm_action = QAction('OSM', self)
        osm_action.setCheckable(True)
        osm_action.setData(web_layers.MapLayersEnum.osm)
        osm_action.triggered.connect(self.menu_weblayer_set_weblayer)
        geoportal_action = QAction('Geoportal', self)
        geoportal_action.setCheckable(True)
        geoportal_action.setData(web_layers.MapLayersEnum.geoportal_orto)
        geoportal_action.triggered.connect(self.menu_weblayer_set_weblayer)

        google_action = QAction('Google', self)
        google_action.setCheckable(True)
        google_action.setData(web_layers.MapLayersEnum.google_orto)
        google_action.triggered.connect(self.menu_weblayer_set_weblayer)
        weblayers.addAction(osm_action)
        weblayers.addAction(geoportal_action)
        weblayers.addAction(google_action)

        self.weblayers_actions_group.addAction(osm_action)
        self.weblayers_actions_group.addAction(geoportal_action)
        self.weblayers_actions_group.addAction(google_action)


    def _create_file_actions(self):
        file_actions = list()
        file_actions.append(QAction('&Open', self))
        file_actions[-1].triggered.connect(self.open_file)
        file_actions.append(QAction('&Add', self))
        file_actions.append(QAction('&Close', self))
        file_actions.append(None)
        file_actions.append(QAction('&Save map', self))
        file_actions[-1].triggered.connect(self.save_map)
        file_actions.append(QAction('&Save map as', self))
        file_actions.append(None)
        file_actions.append(QAction('&Import', self))
        file_actions.append(QAction('&Export', self))
        file_actions.append(None)
        file_actions.append(QAction('&Zamknij', self))
        file_actions[-1].triggered.connect(self.close_app)
        return tuple(file_actions)

    def _create_edit_actions(self):
        edit_actions = list()
        edit_actions.append(QAction('&Undo', self))
        # dajemy znać undo-redo stack aby ustawial w tooltipie ostatnia komende ktora moze odwolac
        self.undo_redo_stack.set_undo_button(edit_actions[-1])
        edit_actions[-1].triggered.connect(self.undo_redo_stack.undo)
        edit_actions.append(QAction('&Redo', self))
        # dajemy znać undo-redo stack aby ustawial w tooltipie ostatnia komende ktora moze powtorzyc
        self.undo_redo_stack.set_redo_button(edit_actions[-1])
        edit_actions[-1].triggered.connect(self.undo_redo_stack.redo)
        edit_actions.append(None)
        edit_actions.append(QAction('&Cut', self))
        edit_actions.append(QAction('&Copy', self))
        edit_actions[-1].setShortcut(QKeySequence.Copy)
        edit_actions[-1].triggered.connect(self.copy_action)
        edit_actions.append(QAction('&Paste', self))
        edit_actions.append(QAction('&Paste here', self))
        edit_actions.append(QAction('&Delete', self))
        edit_actions.append(None)
        return edit_actions

    def _create_select_actions(self):
        select_actions = list()
        select_actions.append(QAction('&All objects', self))
        select_actions.append(QAction('&All points', self))
        select_actions.append(QAction('&All polylines', self))
        select_actions.append(QAction('&All polygones', self))
        select_actions.append(QAction('&All roads', self))
        select_actions.append(None)
        select_actions.append(QAction('&All bookmarks', self))
        select_actions.append(QAction('&All note drivings', self))
        select_actions.append(None)
        select_actions.append(QAction('&All tracks', self))
        select_actions.append(QAction('&All waypoints', self))
        select_actions.append(QAction('&All routes', self))
        select_actions.append(QAction('&All raster images', self))
        select_actions.append(QAction('&All attached files', self))
        select_actions.append(None)
        select_actions.append(QAction('&By type', self))
        select_actions.append(QAction('&By labels', self))
        return select_actions

    def _create_tools_actions(self):
        tools_action = list()
        # tools_action.append(QAction('&Drag map', self))
        # tools_action[-1].setData('drag_map')
        tools_action.append(QAction('&Zoom map', self))
        tools_action[-1].setData(pwmapedit_constants.Tools.ZOOM_MAP)
        tools_action.append(QAction('&Select objects', self))
        tools_action[-1].setData(pwmapedit_constants.Tools.SELECT_OBJECTS)
        tools_action.append(QAction('&Rotate object', self))
        tools_action[-1].setData(pwmapedit_constants.Tools.ROTATE_OBJECTS)
        tools_action.append(QAction('&Edit nodes', self))
        tools_action[-1].setData(pwmapedit_constants.Tools.EDIT_NODES)
        for act in tools_action:
            act.setCheckable(True)
            if act.data() == pwmapedit_constants.Tools.SELECT_OBJECTS:
                act.setChecked(True)
            act.triggered.connect(self.menu_tools_set_mode)
        return tuple(tools_action)

    def _create_object_actions(self):
        obj_actions = list()
        obj_actions.append(QAction('&Point', self))
        obj_actions[-1].setData(pwmapedit_constants.Tools.CREATE_POINT)
        obj_actions.append(None)
        obj_actions.append(QAction('&Polyline', self))
        obj_actions[-1].setData(pwmapedit_constants.Tools.CREATE_POLYLINE)
        obj_actions.append(QAction('&Polyline: circle', self))
        obj_actions[-1].setData(pwmapedit_constants.Tools.CREATE_POLYLINE_CIRCLE)
        obj_actions.append(None)
        obj_actions.append(QAction('&Polygon', self))
        obj_actions[-1].setData(pwmapedit_constants.Tools.CREATE_POLYGON)
        obj_actions.append(QAction('&Polygon: stripe', self))
        obj_actions[-1].setData(pwmapedit_constants.Tools.CREATE_POLYGON_STRIPE)
        obj_actions.append(QAction('&Polygon: rectangle', self))
        obj_actions[-1].setData(pwmapedit_constants.Tools.CREATE_POLYGON_RECTANGLE)
        obj_actions.append(QAction('&Polygon: disc', self))
        obj_actions[-1].setData(pwmapedit_constants.Tools.CREATE_POLYGON_DISC)
        for act in obj_actions:
            if act is None:
                continue
            act.setCheckable(True)
            act.triggered.connect(self.menu_tools_set_mode)
        return tuple(obj_actions)

    def close_app(self):
        self.weblayers_cache_folder.cleanup()
        self.close()

    def closeEvent(self, event):
        self.weblayers_cache_folder.cleanup()
        super().closeEvent(event)

    def copy_action(self):
        print(self.focusWidget())
        lat, lon = self.view.get_current_mouse_geo_coordinates()
        QApplication.clipboard().setText('%.7f, %.7f' %  (lat, lon))

    def generate_shortcuts(self):
        scale_down = QShortcut(QKeySequence('-'), self)
        scale_down.activated.connect(self.menu_zoom_out_command)
        scale_up = QShortcut(QKeySequence('='), self)
        scale_up.activated.connect(self.menu_zoom_in_command)
        cancel_selection = QShortcut(QKeySequence('Escape'), self)
        cancel_selection.activated.connect(self.map_canvas.clearSelection)
        self.map_level_actions.append(QShortcut(QKeySequence('0'), self))
        self.map_level_actions[-1].activated.connect(self.menu_view_set_map_level_0)
        self.map_level_actions.append(QShortcut(QKeySequence('1'), self))
        self.map_level_actions[-1].activated.connect(self.menu_view_set_map_level_1)
        self.map_level_actions.append(QShortcut(QKeySequence('2'), self))
        self.map_level_actions[-1].activated.connect(self.menu_view_set_map_level_2)
        self.map_level_actions.append(QShortcut(QKeySequence('3'), self))
        self.map_level_actions[-1].activated.connect(self.menu_view_set_map_level_3)
        self.map_level_actions.append(QShortcut(QKeySequence('4'), self))
        self.map_level_actions[-1].activated.connect(self.menu_view_set_map_level_4)
        self.delete_key_action = QShortcut(QKeySequence.Delete, self)
        self.delete_key_action.activated.connect(self.map_canvas.delete_object)


    def disable_maplevel_shortcuts(self):
        for shorcut in self.map_level_actions:
            shorcut.setEnabled(False)

    def disable_delete_key(self):
        self.delete_key_action.setEnabled(False)

    def enable_maplevel_shortcuts(self):
        for shorcut in self.map_level_actions:
            shorcut.setEnabled(True)

    def enbale_delete_key(self):
        self.delete_key_action.setEnabled(True)

    def open_file(self):
        aaa = QFileDialog.getOpenFileName(self, 'File to open')
        print(aaa[0])
        print('Plik do otwarcia %s' % aaa[0])
        if aaa[0]:
            self.open_save_thread = QThread()
            self.worker_file_parser = MapFileOpener(self, aaa[0], self.map_objects_properties, self.projection,
                                                    self.undo_redo_stack)
            self.worker_file_parser.moveToThread(self.open_save_thread)

            self.open_save_thread.started.connect(self.worker_file_parser.run)
            self.worker_file_parser.finished.connect(self.open_save_thread.quit)
            self.worker_file_parser.finished.connect(self.worker_file_parser.deleteLater)
            self.open_save_thread.finished.connect(self.worker_file_parser.deleteLater)
            self.worker_file_parser.progress.connect(self.update_progress_bar)
            self.worker_file_parser.draw_poi_polyline_polygon.connect(self.draw_poi_polyline_polygon)
            self.worker_file_parser.map_items_map_canvas.connect(self.get_map_items)
            self.open_save_thread.start()


    def draw_poi_polyline_polygon(self, pois_polylines_polygons, map_objects):
        print(f'rysuje: {len(pois_polylines_polygons)} obiektow')
        if self.view.scene() is not None:
            self.view.setScene(None)
        for poi_polyline_polygon in pois_polylines_polygons:
            poi_polyline_polygon.set_projection(self.projection)
            poi_polyline_polygon.set_map_objects_properties(self.map_objects_properties)
            self.map_objects_to_be_drawn.add(poi_polyline_polygon.get_id())
            self.map_canvas.draw_object_on_map(poi_polyline_polygon)
            self.map_objects_to_be_drawn.remove(poi_polyline_polygon.get_id())
        print('koniec rysowania')
        if map_objects is not None:
            self.map_objects = map_objects
            self.map_objects.set_projection(self.projection)
            self.map_objects.set_map_objects_properties(self.map_objects_properties)
            self.view.setScene(self.map_canvas)
            self.map_canvas.set_canvas_rectangle(self.map_objects.get_map_bounding_box())
            self.projection.set_map_bounding_box(self.map_objects.get_map_bounding_box())
            self.projection.calculate_data_offset()
            print('map data ofset', self.projection.earth_radius)
            print(self.map_canvas.sceneRect())
        return

    def get_map_items(self, map_items):
        print('getting map_items i map_canvas')
        self.map_objects = map_items
        self.map_objects.set_projection(self.projection)
        self.map_objects.set_map_objects_properties(self.map_objects_properties)
        return

    def get_mapedit_mode(self):
        return self.pw_mapedit_mode

    def menu_zoom_in_command(self):
        self.view.zoom_in_command()

    def menu_zoom_out_command(self):
        self.view.zoom_out_command()
        return

    def menu_change_projection(self):
        projection = self.menuProjectionVar.get()
        if self.mapa.change_projection(projection, self.map_objects.get_map_bounding_box(),
                                       self.map_objects.get_all_map_objects()):
            self.menuProjectionVar.set(projection)

    def menu_select_map_level_thread(self):
        self.view.setScene(None)
        self.open_save_thread = QThread()
        self.worker_file_parser = MapeEndlevelWorker(self.map_canvas,
                                                     self.map_level_action_group.checkedAction().data())
        self.worker_file_parser.moveToThread(self.open_save_thread)

        self.open_save_thread.started.connect(self.worker_file_parser.run)
        self.worker_file_parser.finished.connect(self.open_save_thread.quit)
        self.worker_file_parser.finished.connect(self.worker_file_parser.deleteLater)
        self.open_save_thread.finished.connect(self.worker_file_parser.deleteLater)
        self.worker_file_parser.progress.connect(self.update_progress_bar)
        self.worker_file_parser.get_canvas.connect(self.end_level_change_get_canvas_from_thread)
        self.open_save_thread.start()

    def end_level_change_get_canvas_from_thread(self, map_canvas, map_level):
        self.map_canvas = map_canvas
        self.map_canvas.set_map_level(map_level)
        self.view.setScene(self.map_canvas)

    def menu_select_map_level(self):
        map_level = self.map_level_action_group.checkedAction().data()
        # self.view.setScene(None)
        self.map_canvas.set_map_level(map_level)
        # self.view.setScene(self.map_canvas)

    def menu_view_set_map_level_0(self):
        self.map_level_actions[0].setChecked(True)
        self.menu_select_map_level()
        # self.menu_select_map_level_thread()

    def menu_view_set_map_level_1(self):
        self.map_level_actions[1].setChecked(True)
        self.menu_select_map_level()
        # self.menu_select_map_level_thread()

    def menu_view_set_map_level_2(self):
        self.map_level_actions[2].setChecked(True)
        self.menu_select_map_level()
        # self.menu_select_map_level_thread()

    def menu_view_set_map_level_3(self):
        self.map_level_actions[3].setChecked(True)
        self.menu_select_map_level()
        # self.menu_select_map_level_thread()

    def menu_view_set_map_level_4(self):
        self.map_level_actions[4].setChecked(True)
        self.menu_select_map_level()
        # self.menu_select_map_level_thread()

    def menu_tools_set_mode(self):
        self.map_canvas.clearSelection()
        self.pw_mapedit_mode = self.tools_actions_group.checkedAction().data()
        print(self.pw_mapedit_mode)

    def menu_weblayer_set_weblayer(self):
        self.view.set_web_layer(None)
        if self.weblayers_actions_group.checkedAction() is not None:
            self.view.set_web_layer(None)
            self.view.set_web_layer(web_layers.WebLayers(self.weblayers_actions_group.checkedAction().data(),
                                                         cache_folder=self.weblayers_cache_folder.name))

    def update_progress_bar(self, command, value):
        if command == 'set_maximum':
            print('progress maximum')
            self.status_bar.set_progress_bar_maximum(value)
        elif command == 'set_value':
            print('progres wartosc aktualna')
            self.status_bar.set_progress_bar_value(value)
        else:
            self.status_bar.reset_progress_bar()
        return

    def save_map(self):
        if self.map_objects is not None and self.map_objects.contains_data():
            self.open_save_thread = QThread()
            self.worker_file_parser = MapFileSaver(self, self.map_objects)
            self.worker_file_parser.moveToThread(self.open_save_thread)
            self.open_save_thread.started.connect(self.worker_file_parser.run)
            self.worker_file_parser.finished.connect(self.open_save_thread.quit)
            self.worker_file_parser.finished.connect(self.worker_file_parser.deleteLater)
            self.open_save_thread.finished.connect(self.worker_file_parser.deleteLater)
            self.worker_file_parser.progress.connect(self.update_progress_bar)
            self.open_save_thread.start()

    def save_map_as(self):
        return

if __name__ == "__main__":

    file_to_open = ''
    app = QApplication(sys.argv)
    w = pwMapeditPy(None, file_to_open)
    w.show()
    app.exec()
