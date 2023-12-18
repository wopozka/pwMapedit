#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import QDockWidget, QFrame, QLabel, QHBoxLayout, QVBoxLayout, QComboBox, QLineEdit, QCheckBox
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
        self.comment_text_edit = QPlainTextEdit()
        comment_box = QVBoxLayout()
        comment_box.addWidget(comment_label)
        comment_box.addWidget(self.comment_text_edit)
        dock_box.addLayout(comment_box)

        poi_street_desc = QLabel('Street name')
        self.streetdesc = QLineEdit()
        poi_street_desc_box = QHBoxLayout()
        poi_street_desc_box.addWidget(poi_street_desc)
        poi_street_desc_box.addWidget(self.streetdesc)
        dock_box.addLayout(poi_street_desc_box)

        poi_house_number = QLabel('House number')
        self.housenumber = QLineEdit()
        poi_house_number_box = QHBoxLayout()
        poi_house_number_box.addWidget(poi_house_number)
        poi_house_number_box.addWidget(self.housenumber)
        dock_box.addLayout(poi_house_number_box)

        poi_phone = QLabel('Phone number')
        self.phone = QLineEdit()
        poi_phone_box = QHBoxLayout()
        poi_phone_box.addWidget(poi_phone)
        poi_phone_box.addWidget(self.phone)
        dock_box.addLayout(poi_phone_box)

        extras_label = QLabel('Extras')
        self.extras_table = QTableWidget(3, 2)
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

