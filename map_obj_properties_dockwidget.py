#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import QDockWidget, QFrame, QLabel, QHBoxLayout, QVBoxLayout, QComboBox, QLineEdit, QCheckBox
from PyQt5.QtWidgets import QFormLayout
from PyQt5.QtWidgets import QPlainTextEdit, QWidget, QTableWidget, QTableWidgetItem


class MapObjPropDock(QDockWidget):
    def __init__(self, parent, *args, **kwargs):
        self.parent = parent
        self.map_object_id = None
        super(MapObjPropDock, self).__init__(parent, *args, **kwargs)
        dock_widget = QWidget()
        dock_box = QVBoxLayout()
        self.setWidget(dock_widget)
        dock_widget.setLayout(dock_box)
        type_box = QHBoxLayout()
        type_label = QLabel('Type', dock_widget)
        self.type_selector = QComboBox(dock_widget)
        type_box.addWidget(type_label)
        # type_box.addStretch(1)
        type_box.addWidget(self.type_selector)
        dock_box.addLayout(type_box)

        labels_layout = QFormLayout()
        self.label1_entry = QLineEdit(dock_widget)
        labels_layout.addRow('Label', self.label1_entry)
        self.label2_entry = QLineEdit(dock_widget)
        labels_layout.addRow('Label2', self.label2_entry)
        self.label3_entry = QLineEdit(dock_widget)
        labels_layout.addRow('Label3', self.label3_entry)

        dock_box.addLayout(labels_layout)

        polyline_direction = QLabel('Polyline has direction', dock_widget)
        self.poly_direction = QCheckBox(dock_widget)
        dir_box = QHBoxLayout()
        dir_box.addWidget(polyline_direction)
        # dir_box.addStretch(1)
        dir_box.addWidget(self.poly_direction)
        dock_box.addLayout(dir_box)

        comment_label = QLabel("Comment (mapper's private note stored in MP file only)", dock_widget)
        self.comment_text_edit = QPlainTextEdit(dock_widget)
        comment_box = QVBoxLayout()
        comment_box.addWidget(comment_label)
        comment_box.addWidget(self.comment_text_edit)
        dock_box.addLayout(comment_box)

        address_phone_layout = QFormLayout()
        self.streetdesc = QLineEdit(dock_widget)
        address_phone_layout.addRow('Street name', self.streetdesc)
        self.housenumber = QLineEdit(dock_widget)
        address_phone_layout.addRow('House number', self.housenumber)
        self.phone = QLineEdit(dock_widget)
        address_phone_layout.addRow('Phone number', self.phone)
        dock_box.addLayout(address_phone_layout)

        extras_label = QLabel('Extras', dock_widget)
        self.extras_table = QTableWidget(3, 2, dock_widget)
        self.extras_table.setItem(0, 0, QTableWidgetItem('Key'))
        self.extras_table.setItem(0, 1, QTableWidgetItem('Value'))
        extras_box = QVBoxLayout()
        extras_box.addWidget(extras_label)
        extras_box.addWidget(self.extras_table)
        dock_box.addLayout(extras_box)

    def set_map_object_id(self, obj_id):
        self.map_object_id = obj_id

    def fill_map_object_properties(self):
        if self.map_object_id.get_label1():
            self.label1_entry.setText(self.map_object_id.get_label1())
        else:
            self.label1_entry.setText('')
        if self.map_object_id.get_label2():
            self.label2_entry.setText(self.map_object_id.get_label2())
        else:
            self.label2_entry.setText('')
        if self.map_object_id.get_label3():
            self.label3_entry.setText(self.map_object_id.get_label3())
        else:
            self.label3_entry.setText('')
        if self.map_object_id.get_dirindicator():
            self.poly_direction.setChecked(True)
        else:
            self.poly_direction.setChecked(False)
        if self.map_object_id.get_comment():
            self.comment_text_edit.setPlainText('\n'.join(self.map_object_id.get_comment()) + '\n')
        else:
            self.comment_text_edit.setPlainText('')
        if self.map_object_id.get_street_desc():
            self.streetdesc.setText(self.map_object_id.get_street_desc())
        else:
            self.streetdesc.setText('')
        if self.map_object_id.get_house_number():
            self.housenumber.setText(self.map_object_id.get_house_number())
        else:
            self.housenumber.setText('')
        if self.map_object_id.get_phone_number():
            self.phone.setText(self.map_object_id.get_phone_number())
        else:
            self.phone.setText('')
        others = self.map_object_id.get_others()
        if others:
            self.extras_table.setRowCount(len(others) + 1)
            for row, item in enumerate(others):
                self.extras_table.setItem(row + 1, 0, QTableWidgetItem(item[0]))
                self.extras_table.setItem(row + 1, 1, QTableWidgetItem(item[1]))
        else:
            for row in range(self.extras_table.rowCount()):
                if row == 0:
                    continue
                self.extras_table.setItem(row, 0, QTableWidgetItem(''))
                self.extras_table.setItem(row, 1, QTableWidgetItem(''))

