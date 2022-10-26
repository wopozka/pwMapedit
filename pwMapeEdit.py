#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QToolBar, QStatusBar
import tkinter
import tkinter.ttk
import tkinter.filedialog
import string
import sys
import tkinter.scrolledtext
import tkinter.messagebox
import mapData
import mapCanvas


class pwMapeditPy(QMainWindow):
    """main application window"""

    def __init__(self, parent, filename):
        super(pwMapeditPy, self).__init__()
        self.parent = parent
        self.filename = filename
        self.setWindowTitle("pwMapeEdit")
        self.initialize()

    def initialize(self):
        # self.protocol("WM_DELETE_WINDOW", self.Quit)
        # lets add toolbar
        toolbar = QToolBar("My main toolbar")
        self.addToolBar(toolbar)
        self.setStatusBar(QStatusBar(self))
        self.generate_menu()

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

    def generate_menu(self):
        menu = self.menuBar()

        # File menu
        file_menu = menu.addMenu("&File")
        # file_menu.add_command(label='Open...', command=self.open_file)
        # file_menu.add_command(label='Add...')
        # file_menu.add_command(label='Close')
        # file_menu.add_separator()
        # file_menu.add_command(label='Save map')
        # file_menu.add_command(label='Save map as...')
        # file_menu.add_separator()
        # file_menu.add_command(label='Import')
        # file_menu.add_command(label='Export')
        # file_menu.add_separator()
        # file_menu.add_command(label='Exit',command=self.destroy)
        # file_menu.add('radiobutton',label='Cos')
        # menubar.add_cascade(label=u'File',menu=file_menu)

        # Edit menu
        edit_menu = menu.addMenu("&Edit")
        # edit_menu.add_command(label='Undo')
        # edit_menu.add_command(label='Redp')
        # edit_menu.add_separator()
        # edit_menu.add_command(label='Cut')
        # edit_menu.add_command(label='Copy')
        # edit_menu.add_command(label='Paste')
        # edit_menu.add_command(label='Paste here')
        # edit_menu.add_command(label='Delete')
        # edit_menu.add_separator()

        # select submenu
        select_menu = menu.addMenu("&Select")
        # menuSelect.add_command(label='All objects')
        # menuSelect.add_command(label='All points')
        # menuSelect.add_command(label='All polylines')
        # menuSelect.add_command(label='All polygones')
        # menuSelect.add_command(label='All roads')
        # menuSelect.add_separator()
        # menuSelect.add_command(label='All bookmarks')
        # menuSelect.add_command(label='All note drivings')
        # menuSelect.add_separator()
        # menuSelect.add_command(label='All tracks')
        # menuSelect.add_command(label='All waypoints')
        # menuSelect.add_command(label='All routes')
        # menuSelect.add_command(label='All raster images')
        # menuSelect.add_command(label='All attached files')
        # menuSelect.add_separator()
        # menuSelect.add_command(label='By type')
        # menuSelect.add_command(label='By label')

        # edit_menu.add_cascade(label='Select',menu=menuSelect)
        # edit_menu.add_command(label='Unselect')
        # edit_menu.add_command(label='Find')
        # menubar.add_cascade(label=u'Edit',menu=edit_menu)

        # View menu
        view_menu = menu.addMenu("&View")
        # view_menu.add_command(label='Zoom in', accelerator='(=)', command=self.menu_scaleup_command)
        # view_menu.add_command(label='Zoom out',accelerator='(-)', command=self.menu_scaledown_command)
        # menubar.add_cascade(label='View',menu=view_menu)

        # projection submenu
        # self.menuProjectionVar = tkinter.StringVar()
        # self.menuProjectionVar.set('Mercator')
        projection_menu = menu.addMenu("&Projection")
        # projection_menu.add('radiobutton', label='Mercator', command=self.menu_change_projection, variable=self.menuProjectionVar)
        # projection_menu.add('radiobutton', label='UTM', command = self.menu_change_projection, variable=self.menuProjectionVar)
        # view_menu.add_cascade(label='Projection',menu=projection_menu)
        #
        # self.config(menu=menubar)


    def open_file(self):
        aaa=tkinter.filedialog.askopenfilename(title=u'File to open')
        print('Plik do otwarcia %s'%aaa)
        if aaa:
            self.filename = aaa
            map_objects=mapData.mapData(self.filename)
            map_objects.wczytaj_rekordy()
            self.mapa.MapData = map_objects
            self.mapa.draw_all_objects_on_map()
            self.mapa.config(scrollregion=self.mapa.bbox('all'))

    def menu_scaleup_command(self):
        self.mapa.scaleup()

    def menu_scaledown_command(self):
        self.mapa.scaledown()

    def menu_change_projection(self):
        projection = self.menuProjectionVar.get()
        if self.mapa.change_projection(projection):
            self.menuProjectionVar.set(projection)


if __name__ == "__main__":

    file_to_open = ''
    app = QApplication(sys.argv)
    w = pwMapeditPy(None, file_to_open)
    w.show()
    app.exec()
