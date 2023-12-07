#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import QDockWidget

class MapObjPropDock(QDockWidget):
    def __init__(self, parent, *args, **kwargs):
        self.parent = parent
        super(MapObjPropDock, self).__init__(*args, **kwargs)

