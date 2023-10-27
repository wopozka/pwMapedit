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
import map_object_properties
import projection
import math

class pwMapeditPy(QMainWindow):
    """main application window"""

    def __init__(self, parent, filename):
        super(pwMapeditPy, self).__init__()
        self.parent = parent
        self.filename = filename
        self.file_actions = list()
        self.edit_actions = list()
        self.select_actions = list()
        self.map_canvas = None
        self.view = None
        self.setWindowTitle("pwMapeEdit")
        self.status_bar = QStatusBar(self)
        self.projection = projection.Projection({})
        self.initialize()
        self.map_objects = None
        self.map_objects_properties = map_object_properties.MapObjectsProperties()

    def initialize(self):
        # self.protocol("WM_DELETE_WINDOW", self.Quit)
        # lets add toolbar
        toolbar = QToolBar("My main toolbar")
        self.addToolBar(toolbar)
        self.setStatusBar(self.status_bar)
        self.generate_menus()
        self.map_canvas = mapCanvas.mapCanvas(self, 0, 0, 400, 200, projection=self.projection)
        self.generate_shortcuts()
        self.view = mapRender.mapRender(self.map_canvas, self.menu_zoom_in_command, self.menu_zoom_out_command,
                                        projection=self.projection)
        self.view.setMouseTracking(True)
        self.view.set_main_window_status_bar(self.status_bar)
        self.setCentralWidget(self.view)

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

    def _create_file_actions(self):
        self.file_actions.append(QAction('&Open', self))
        self.file_actions[-1].triggered.connect(self.open_file)
        self.file_actions.append(QAction('&Add', self))
        self.file_actions.append(QAction('&Close', self))
        self.file_actions.append(None)
        self.file_actions.append(QAction('&Save map', self))
        self.file_actions.append(QAction('&Save map as', self))
        self.file_actions.append(None)
        self.file_actions.append(QAction('&Import', self))
        self.file_actions.append(QAction('&Export', self))
        return self.file_actions

    def _create_edit_actions(self):
        self.edit_actions.append(QAction('&Undo', self))
        self.edit_actions.append(QAction('&Redo', self))
        self.edit_actions.append(None)
        self.edit_actions.append(QAction('&Cut', self))
        self.edit_actions.append(QAction('&Copy', self))
        self.edit_actions.append(QAction('&Paste', self))
        self.edit_actions.append(QAction('&Paste here', self))
        self.edit_actions.append(QAction('&Delete', self))
        self.edit_actions.append(None)
        return self.edit_actions

    def _create_select_actions(self):
        self.select_actions.append(QAction('&All objects', self))
        self.select_actions.append(QAction('&All points', self))
        self.select_actions.append(QAction('&All polylines', self))
        self.select_actions.append(QAction('&All polygones', self))
        self.select_actions.append(QAction('&All roads', self))
        self.edit_actions.append(None)
        self.select_actions.append(QAction('&All bookmarks', self))
        self.select_actions.append(QAction('&All note drivings', self))
        self.edit_actions.append(None)
        self.select_actions.append(QAction('&All tracks', self))
        self.select_actions.append(QAction('&All waypoints', self))
        self.select_actions.append(QAction('&All routes', self))
        self.select_actions.append(QAction('&All raster images', self))
        self.select_actions.append(QAction('&All attached files', self))
        self.edit_actions.append(None)
        self.select_actions.append(QAction('&By type', self))
        self.select_actions.append(QAction('&By labels', self))
        return self.select_actions

    def generate_shortcuts(self):
        scale_down = QShortcut(QKeySequence('-'), self)
        scale_down.activated.connect(self.menu_zoom_out_command)
        scale_up = QShortcut(QKeySequence('='), self)
        scale_up.activated.connect(self.menu_zoom_in_command)


    def open_file(self):
        aaa = QFileDialog.getOpenFileName(self, 'File to open')
        print(aaa[0])
        print('Plik do otwarcia %s' % aaa[0])
        if aaa[0]:
            self.filename = aaa[0]
            self.map_objects = mapData.mapData(self.filename, map_objects_properties=self.map_objects_properties,
                                               projection=self.projection)
            self.map_objects.wczytaj_rekordy()
            print(self.map_canvas.sceneRect())
            self.map_canvas.draw_all_objects_on_map()
            # print(self.map_canvas.sceneRect())
            # print(self.map_canvas.itemsBoundingRect())
            # self.view.fitInView(self.map_canvas.itemsBoundingRect(), Qt.KeepAspectRatio)
            # self.view.ensureVisible(self.map_canvas.itemsBoundingRect())
            # self.mapa.config(scrollregion=self.mapa.bbox('all'))

    def menu_zoom_in_command(self):
        center_coords = self.view.mapToScene(self.view.width() // 2, self.view.height() // 2)
        curent_mouse_coords = self.view.curent_scene_mouse_coords()
        mouse_center_vector = center_coords - curent_mouse_coords
        mouse_center_vector_lenght = math.sqrt(mouse_center_vector.x() ** 2 + mouse_center_vector.y() ** 2)
        self.view.scale(1.1, 1.1)
        center_coords1 = self.view.mapToScene(self.view.width() // 2, self.view.height() // 2)
        curent_mouse_coords1 = self.view.mapToScene(self.view.curent_view_mouse_coords())
        mouse_center_vector1 = center_coords1 - curent_mouse_coords1
        vector_lenght_factor = math.sqrt(mouse_center_vector1.x() ** 2 + mouse_center_vector1.y() ** 2) / \
                               mouse_center_vector_lenght
        new_position = curent_mouse_coords + mouse_center_vector * vector_lenght_factor
        self.view.centerOn(new_position)


    def menu_zoom_out_command(self):
        self.view.scale(0.9, 0.9)

    def menu_change_projection(self):
        projection = self.menuProjectionVar.get()
        if self.mapa.change_projection(projection, self.map_objects.get_map_bounding_box(),
                                       self.map_objects.get_all_map_objects()):
            self.menuProjectionVar.set(projection)


if __name__ == "__main__":

    file_to_open = ''
    app = QApplication(sys.argv)
    w = pwMapeditPy(None, file_to_open)
    w.show()
    app.exec()
