#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import QDockWidget, QFrame, QLabel, QHBoxLayout, QVBoxLayout, QComboBox, QLineEdit, QCheckBox
from PyQt5.QtWidgets import QTextEdit, QWidget


class MapObjPropDock(QDockWidget):
    def __init__(self, parent, *args, **kwargs):
        self.parent = parent
        super(MapObjPropDock, self).__init__(parent, *args, **kwargs)
        dock_widget = QWidget()
        dock_box = QVBoxLayout()
        self.setWidget(dock_widget)
        dock_widget.setLayout(dock_box)
        type_box = QHBoxLayout()
        type_label = QLabel('Type')
        self.type_selector = QComboBox()
        type_box.addWidget(type_label)
        # type_box.addStretch(1)
        type_box.addWidget(self.type_selector)
        dock_box.addLayout(type_box)

        label1 = QLabel('Label')
        self.label1_entry = QLineEdit()
        label1_box = QHBoxLayout()
        label1_box.addWidget(label1)
        # label1_box.addStretch(1)
        label1_box.addWidget(self.label1_entry)
        dock_box.addLayout(label1_box)

        label2 = QLabel('Label2')
        self.label2_entry = QLineEdit()
        label2_box = QHBoxLayout()
        label2_box.addWidget(label2)
        # label2_box.addStretch(1)
        label2_box.addWidget(self.label2_entry)
        dock_box.addLayout(label2_box)

        label3 = QLabel('Label3')
        self.label3_entry = QLineEdit()
        label3_box = QHBoxLayout()
        label3_box.addWidget(label3)
        # label3_box.addStretch(1)
        label3_box.addWidget(self.label3_entry)
        dock_box.addLayout(label3_box)

        polyline_direction = QLabel('Polyline has direction')
        self.poly_direction = QCheckBox()
        dir_box = QHBoxLayout()
        dir_box.addWidget(polyline_direction)
        # dir_box.addStretch(1)
        dir_box.addWidget(self.poly_direction)
        dock_box.addLayout(dir_box)

        comment_label = QLabel("Comment (mapper's private note stored in MP file only)")
        self.comment_text_edit = QTextEdit()
        comment_box = QVBoxLayout()
        comment_box.addWidget(comment_label)
        comment_box.addWidget(self.comment_text_edit)
        dock_box.addLayout(comment_box)



