#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QToolBar, QStatusBar, QAction, QActionGroup
from PyQt5.QtWidgets import QGraphicsScene, QGraphicsView, QFileDialog, QShortcut
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence
import sys
import mapData
import mapCanvas
import mapRender
import map_items
import map_object_properties
import projection
import map_obj_properties_dockwidget

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
        self.status_bar = QStatusBar(self)
        self.projection = projection.Mercator({})
        self.tools_actions_group = None
        self.map_level_action_group = None
        self.map_level_actions = list()
        self.pw_mapedit_mode = ''
        self.initialize()
        self.generate_shortcuts()
        self.properties_dock = map_obj_properties_dockwidget.MapObjPropDock(self)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.properties_dock)
        self.map_objects = None
        self.map_objects_properties = map_object_properties.MapObjectsProperties()
        self.map_ruler = None
        self.menu_tools_set_mode()


    def initialize(self):
        # self.protocol("WM_DELETE_WINDOW", self.Quit)
        # lets add toolbar
        toolbar = QToolBar("My main toolbar")
        self.addToolBar(toolbar)
        self.setStatusBar(self.status_bar)
        self.generate_menus()
        self.map_canvas = mapCanvas.mapCanvas(self, 0, 0, 400, 200, projection=self.projection, map_viewer=None)
        self.view = mapRender.mapRender(self.map_canvas, projection=self.projection)
        self.view.setMouseTracking(True)
        self.view.set_main_window_status_bar(self.status_bar)
        self.setCentralWidget(self.view)
        self.map_ruler = map_items.MapRuler(self.view, self.projection)
        self.map_canvas.addItem(self.map_ruler)
        self.view.set_ruler(self.map_ruler)



        # ramkaglowna = tkinter.Frame(self)
        # ramkaglowna.pack(expand=1, fill='both')
        # canvasScrollFrame=tkinter.Frame(ramkaglowna)
        # canvasScrollFrame.pack(side='top',fill='both',expand=1)
        # rightScroll=tkinter.Scrollbar(canvasScrollFrame)
        # bottomScroll=tkinter.Scrollbar(ramkaglowna,orient='horizontal')
        # self.mapa = mapCanvas.mapCanvas(canvasScrollFrame,yscrollcommand=rightScroll.set,
        #                                 xscrollcommand=bottomScroll.set, background='white',
        #                                 width=800, height=500)
        # self.mapa.pack(expand=1, fill='both',side='left')
        # rightScroll.config(command=self.mapa.yview)
        # bottomScroll.config(command=self.mapa.xview)
        # rightScroll.pack(side='right',fill='y')
        # bottomScroll.pack(side='bottom',fill='x')
        #
        # #if the filename was added as a run parameter, then open a file here
        # if self.filename:
        #     map_objects=mapData.mapData(self.filename)
        #     map_objects.wczytaj_rekordy()
        #     self.mapa.MapData = map_objects
        #     self.mapa.draw_all_objects_on_map()
        # self.mapa.config(scrollregion=self.mapa.bbox('all'))

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

        # projection submenu
        # self.menuProjectionVar = tkinter.StringVar()
        # self.menuProjectionVar.set('Mercator')
        projection_menu = menu.addMenu("&Projection")
        mercator_action = QAction('&Mercator', self)
        mercator_action.setCheckable(True)
        utm_action = QAction('&UTM', self)
        utm_action.setCheckable(True)
        utm_action.setChecked(True)
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

    def _create_file_actions(self):
        file_actions = list()
        file_actions.append(QAction('&Open', self))
        file_actions[-1].triggered.connect(self.open_file)
        file_actions.append(QAction('&Add', self))
        file_actions.append(QAction('&Close', self))
        file_actions.append(None)
        file_actions.append(QAction('&Save map', self))
        file_actions.append(QAction('&Save map as', self))
        file_actions.append(None)
        file_actions.append(QAction('&Import', self))
        file_actions.append(QAction('&Export', self))
        return tuple(file_actions)

    def _create_edit_actions(self):
        edit_actions = list()
        edit_actions.append(QAction('&Undo', self))
        edit_actions.append(QAction('&Redo', self))
        edit_actions.append(None)
        edit_actions.append(QAction('&Cut', self))
        edit_actions.append(QAction('&Copy', self))
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
        tools_action.append(QAction('&Drag map', self))
        tools_action[-1].setData('drag_map')
        tools_action.append(QAction('&Zoom map', self))
        tools_action[-1].setData('zoom_map')
        tools_action.append(QAction('&Select objects', self))
        tools_action[-1].setData('select_objects')
        tools_action.append(QAction('&Rotate object', self))
        tools_action[-1].setData('rotate_objects')
        tools_action.append(QAction('&Edit nodes', self))
        tools_action[-1].setData('edit_nodes')
        for act in tools_action:
            act.setCheckable(True)
            if act.data() == 'drag_map':
                act.setChecked(True)
            act.triggered.connect(self.menu_tools_set_mode)
        return tuple(tools_action)

    def _create_object_actions(self):
        obj_actions = list()
        obj_actions.append(QAction('&Point', self))
        obj_actions[-1].setData('create_point')
        obj_actions.append(None)
        obj_actions.append(QAction('&Polyline', self))
        obj_actions[-1].setData('create_polyline')
        obj_actions.append(QAction('&Polyline: circle', self))
        obj_actions[-1].setData('create_polyline_circle')
        obj_actions.append(None)
        obj_actions.append(QAction('&Polygon', self))
        obj_actions[-1].setData('create_polygon')
        obj_actions.append(QAction('&Polygon: stripe', self))
        obj_actions[-1].setData('create_polygon_stripe')
        obj_actions.append(QAction('&Polygon: rectangle', self))
        obj_actions[-1].setData('create_polygon_rectangle')
        obj_actions.append(QAction('&Polygon: disc', self))
        obj_actions[-1].setData('create_polygon_dics')
        for act in obj_actions:
            if act is None:
                continue
            act.setCheckable(True)
            act.triggered.connect(self.menu_tools_set_mode)
        return tuple(obj_actions)

    def generate_shortcuts(self):
        scale_down = QShortcut(QKeySequence('-'), self)
        scale_down.activated.connect(self.menu_zoom_out_command)
        scale_up = QShortcut(QKeySequence('='), self)
        scale_up.activated.connect(self.menu_zoom_in_command)
        cancel_selection = QShortcut(QKeySequence('Escape'), self)
        cancel_selection.activated.connect(self.map_canvas.clearSelection)
        set_maplevel_0 = QShortcut(QKeySequence('0'), self)
        set_maplevel_0.activated.connect(self.menu_view_set_map_level_0)
        set_maplevel_1 = QShortcut(QKeySequence('1'), self)
        set_maplevel_1.activated.connect(self.menu_view_set_map_level_1)
        set_maplevel_2 = QShortcut(QKeySequence('2'), self)
        set_maplevel_2.activated.connect(self.menu_view_set_map_level_2)
        set_maplevel_3 = QShortcut(QKeySequence('3'), self)
        set_maplevel_3.activated.connect(self.menu_view_set_map_level_3)
        set_maplevel_4 = QShortcut(QKeySequence('4'), self)
        set_maplevel_4.activated.connect(self.menu_view_set_map_level_4)


    def open_file(self):
        aaa = QFileDialog.getOpenFileName(self, 'File to open')
        print(aaa[0])
        print('Plik do otwarcia %s' % aaa[0])
        if aaa[0]:
            self.filename = aaa[0]
            self.map_objects = mapData.mapData(self.filename, map_objects_properties=self.map_objects_properties,
                                               projection=self.projection)
            self.map_objects.wczytaj_rekordy()
            self.map_canvas.draw_all_objects_on_map(self.map_objects.get_all_map_objects())
            self.map_canvas.set_canvas_rectangle(self.map_objects.get_map_bounding_box())
            print(self.map_canvas.sceneRect())
            self.map_objects.clean_all_map_objects()
            # print(self.map_canvas.sceneRect())
            # print(self.map_canvas.itemsBoundingRect())
            # self.view.fitInView(self.map_canvas.itemsBoundingRect(), Qt.KeepAspectRatio)
            # self.view.ensureVisible(self.map_canvas.itemsBoundingRect())

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

    def menu_select_map_level(self):
        map_level = self.map_level_action_group.checkedAction().data()
        self.map_canvas.set_map_level(map_level)

    def menu_view_set_map_level_0(self):
        self.map_level_actions[0].setChecked(True)
        self.menu_select_map_level()

    def menu_view_set_map_level_1(self):
        self.map_level_actions[1].setChecked(True)
        self.menu_select_map_level()

    def menu_view_set_map_level_2(self):
        self.map_level_actions[2].setChecked(True)
        self.menu_select_map_level()

    def menu_view_set_map_level_3(self):
        self.map_level_actions[3].setChecked(True)
        self.menu_select_map_level()

    def menu_view_set_map_level_4(self):
        self.map_level_actions[4].setChecked(True)
        self.menu_select_map_level()

    def menu_tools_set_mode(self):
        self.map_canvas.clearSelection()
        self.pw_mapedit_mode = self.tools_actions_group.checkedAction().data()
        print(self.pw_mapedit_mode)

if __name__ == "__main__":

    file_to_open = ''
    app = QApplication(sys.argv)
    w = pwMapeditPy(None, file_to_open)
    w.show()
    app.exec()
