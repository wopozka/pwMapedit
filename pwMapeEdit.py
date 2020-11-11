#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter
import tkinter.ttk
import tkinter.filedialog
import string
import sys
import tkinter.scrolledtext
import tkinter.messagebox
import mapData
import mapCanvas


class pwMapeditPy(tkinter.Tk):
    """klasa przechowuje dane z pliku *.mp, czyli punkty, polylinie i polygony"""

    def __init__(self, parent, filename):
        tkinter.Tk.__init__(self, parent)
        self.parent = parent
        self.filename = filename
        self.initialize()

    def initialize(self):
        # self.protocol("WM_DELETE_WINDOW", self.Quit)
        self.generate_menu()

        ramkaglowna = tkinter.Frame(self)
        ramkaglowna.pack(expand=1, fill='both')
        canvasScrollFrame=tkinter.Frame(ramkaglowna)
        canvasScrollFrame.pack(side='top',fill='both',expand=1)
        rightScroll=tkinter.Scrollbar(canvasScrollFrame)
        bottomScroll=tkinter.Scrollbar(ramkaglowna,orient='horizontal')
        self.mapa = mapCanvas.mapCanvas(canvasScrollFrame,yscrollcommand=rightScroll.set,
                                        xscrollcommand=bottomScroll.set, background='white',
                                        width=800, height=500)
        self.mapa.pack(expand=1, fill='both',side='left')
        rightScroll.config(command=self.mapa.yview)
        bottomScroll.config(command=self.mapa.xview)
        rightScroll.pack(side='right',fill='y')
        bottomScroll.pack(side='bottom',fill='x')

        #if the filename was added as a run parameter, then open a file here
        if self.filename:
            map_objects=mapData.mapData(self.filename)
            map_objects.wczytaj_rekordy()
            self.mapa.MapData = map_objects
            self.mapa.draw_all_objects_on_map()
        self.mapa.config(scrollregion=self.mapa.bbox('all'))

    def generate_menu(self):
        menubar = tkinter.Menu(self)

        # File menu
        menuFile = tkinter.Menu(menubar, tearoff=0)
        menuFile.add_command(label='Open...', command=self.open_file)
        menuFile.add_command(label='Add...')
        menuFile.add_command(label='Close')
        menuFile.add_separator()
        menuFile.add_command(label='Save map')
        menuFile.add_command(label='Save map as...')
        menuFile.add_separator()
        menuFile.add_command(label='Import')
        menuFile.add_command(label='Export')
        menuFile.add_separator()
        menuFile.add_command(label='Exit',command=self.destroy)
        menuFile.add('radiobutton',label='Cos')
        menubar.add_cascade(label=u'File',menu=menuFile)

        # Edit menu
        menuEdit = tkinter.Menu(menubar, tearoff=0)
        menuEdit.add_command(label='Undo')
        menuEdit.add_command(label='Redp')
        menuEdit.add_separator()
        menuEdit.add_command(label='Cut')
        menuEdit.add_command(label='Copy')
        menuEdit.add_command(label='Paste')
        menuEdit.add_command(label='Paste here')
        menuEdit.add_command(label='Delete')
        menuEdit.add_separator()
        # select submenu
        menuSelect=tkinter.Menu(menubar,tearoff=0)
        menuSelect.add_command(label='All objects')
        menuSelect.add_command(label='All points')
        menuSelect.add_command(label='All polylines')
        menuSelect.add_command(label='All polygones')
        menuSelect.add_command(label='All roads')
        menuSelect.add_separator()
        menuSelect.add_command(label='All bookmarks')
        menuSelect.add_command(label='All note drivings')
        menuSelect.add_separator()
        menuSelect.add_command(label='All tracks')
        menuSelect.add_command(label='All waypoints')
        menuSelect.add_command(label='All routes')
        menuSelect.add_command(label='All raster images')
        menuSelect.add_command(label='All attached files')
        menuSelect.add_separator()
        menuSelect.add_command(label='By type')
        menuSelect.add_command(label='By label')

        menuEdit.add_cascade(label='Select',menu=menuSelect)
        menuEdit.add_command(label='Unselect')
        menuEdit.add_command(label='Find')
        menubar.add_cascade(label=u'Edit',menu=menuEdit)

        # View menu
        menuView = tkinter.Menu(menubar,tearoff=0)
        menuView.add_command(label='Zoom in', accelerator='(=)', command=self.menu_scaleup_command)
        menuView.add_command(label='Zoom out',accelerator='(-)', command=self.menu_scaledown_command)
        menubar.add_cascade(label='View',menu=menuView)

        # projection submenu
        self.menuProjectionVar = tkinter.StringVar()
        self.menuProjectionVar.set('Mercator')
        menuProjection = tkinter.Menu(menuView,tearoff=0)
        menuProjection.add('radiobutton', label='Mercator', command=self.menu_change_projection, variable=self.menuProjectionVar)
        menuProjection.add('radiobutton', label='UTM', command = self.menu_change_projection, variable=self.menuProjectionVar)
        menuView.add_cascade(label='Projection',menu=menuProjection)



        self.config(menu=menubar)


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
    app = pwMapeditPy(None,file_to_open)
    app.title(u'pwMapedit')

    app.mainloop()