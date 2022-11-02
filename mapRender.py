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
        Store.status_bar.showMessage('(%s,%s)' % (event.pos().x(), event.pos().y()))
