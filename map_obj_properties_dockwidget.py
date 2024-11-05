#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import (QDockWidget, QMenu, QLabel, QHBoxLayout, QVBoxLayout, QComboBox, QLineEdit, QCheckBox,
                             QPushButton, QGroupBox)
from PyQt5.QtWidgets import QFormLayout, QTabWidget
from PyQt5.QtWidgets import QPlainTextEdit, QWidget, QTableWidget, QTableWidgetItem
from PyQt5.QtCore import Qt
from enum import Enum

import map_items


class RouteParams(Enum):
    speed_limit = 0
    route_class = 1
    one_way = 2
    route_is_toll = 3
    no_emergency = 4
    no_delivery = 5
    no_car_motorcycle = 6
    no_bus = 7
    no_taxi = 8
    no_pedestrian = 9
    no_bicycle = 10
    no_truck = 11

class MapObjPropDock(QDockWidget):
    def __init__(self, parent, *args, **kwargs):
        self.parent = parent
        self.map_object_id = None
        super(MapObjPropDock, self).__init__(parent, *args, **kwargs)
        self.setWindowTitle("Właściwości")
        self.tab_widget = QTabWidget()
        self.tab_names_vs_index = dict()
        # tab_widget.setTabPosition(QTabWidget.West)
        dock_widget = QWidget()
        self.tab_names_vs_index['glowny'] = self.tab_widget.addTab(dock_widget, 'Glowny')
        dock_box = QVBoxLayout()
        self.setWidget(self.tab_widget)
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
        self.label1_entry.editingFinished.connect(self.command_label1_entry_edited)
        labels_layout.addRow('Label', self.label1_entry)
        self.label2_entry = QLineEdit(dock_widget)
        self.label2_entry.editingFinished.connect(self.command_label2_entry_edited)
        labels_layout.addRow('Label2', self.label2_entry)
        self.label3_entry = QLineEdit(dock_widget)
        self.label3_entry.editingFinished.connect(self.command_label3_entry_edited)
        labels_layout.addRow('Label3', self.label3_entry)
        self.end_level = QLineEdit(dock_widget)
        self.end_level.editingFinished.connect(self.command_end_level_entry_edited)
        labels_layout.addRow('EndLevel', self.end_level)

        dock_box.addLayout(labels_layout)

        polyline_direction = QLabel('Polyline has direction', dock_widget)
        self.poly_direction = QCheckBox(dock_widget)
        self.poly_direction.clicked.connect(self.command_dirindicator_changed)
        dir_box = QHBoxLayout()
        dir_box.addWidget(polyline_direction)
        # dir_box.addStretch(1)
        self.reverse_direction_button = QPushButton('Revert direction', dock_widget)
        self.reverse_direction_button.clicked.connect(self.reverse_polyline)
        dir_box.addWidget(self.poly_direction)
        dir_box.addWidget(self.reverse_direction_button)
        dock_box.addLayout(dir_box)

        comment_label = QLabel("Comment (mapper's private note stored in MP file only)", dock_widget)
        self.comment_text_edit = QPlainTextEdit(dock_widget)
        comment_box = QVBoxLayout()
        comment_box.addWidget(comment_label)
        comment_box.addWidget(self.comment_text_edit)
        dock_box.addLayout(comment_box)

        extras_label = QLabel('Extras', dock_widget)
        self.extras_table = ExtrasTable(3, 2, dock_widget)
        self.extras_table.setHorizontalHeaderLabels(['Key', 'Label'])
        extras_box = QVBoxLayout()
        extras_box.addWidget(extras_label)
        extras_box.addWidget(self.extras_table)
        dock_box.addLayout(extras_box)

        # karta adres, dla poi
        address_widget =QWidget()
        self.tab_names_vs_index['adres'] = self.tab_widget.addTab(address_widget, 'Adres')
        address_phone_layout = QFormLayout()
        address_widget.setLayout(address_phone_layout)
        self.streetdesc = QLineEdit(address_widget)
        self.streetdesc.editingFinished.connect(self.command_streetdesc_edited)
        address_phone_layout.addRow('Street name', self.streetdesc)
        self.housenumber = QLineEdit(address_widget)
        self.housenumber.editingFinished.connect(self.command_housenumber_edited)
        address_phone_layout.addRow('House number', self.housenumber)
        self.phone = QLineEdit(address_widget)
        self.phone.editingFinished.connect(self.command_phone_edited)
        address_phone_layout.addRow('Phone number', self.phone)

        # karta elements,
        elements_widgets = QWidget()
        self.tab_names_vs_index['elements'] = self.tab_widget.addTab(elements_widgets, 'Elements')
        self.elements_table = QTableWidget()
        elements_layout_box = QVBoxLayout()
        elements_widgets.setLayout(elements_layout_box)
        elements_layout_box.addWidget(self.elements_table)
        self.elements_table.setRowCount(0)
        self.elements_table.setColumnCount(6)
        self.elements_table.setHorizontalHeaderLabels(['#', 'Level', 'Lat/Lon 1 punkt', 'Węzły', 'Obszar', 'Typ'])

        # karta routing
        routing_widget = QWidget()
        self.tab_names_vs_index['routing'] = self.tab_widget.addTab(routing_widget, 'Routing')
        routing_widget_layout = QFormLayout()
        routing_widget.setLayout(routing_widget_layout)
        self.route_params = [None for a in range(12)]

        # 0
        routing_pos = RouteParams.speed_limit.value
        self.route_params[routing_pos] = QComboBox(routing_widget)
        self.route_params[routing_pos].activated.connect(self.command_route_params_edited)
        self.route_params[routing_pos].addItems(['(0) 3mph/5kmh', '(1) 15mph/20kmh',
                                                                   '(2) 25mph/40kmh', '(3) 35mph/60kmh',
                                                                   '(4) 50mph/80kmh', '(5) 60mph/90kmh',
                                                                   '(6) 70mph/110kmh', '(7) no limit'])
        routing_widget_layout.addRow('Speed limit', self.route_params[routing_pos])

        # 1
        routing_pos = RouteParams.route_class.value
        self.route_params[routing_pos] = QComboBox(routing_widget)
        self.route_params[routing_pos].activated.connect(self.command_route_params_edited)
        self.route_params[routing_pos].addItems(['(0) residential/alley/unpaved/trail',
                                                                   '(1) roundabout/collector',
                                                                   '(2) arterial/other HW', '(3) principal HW',
                                                                   '(4) major HW/ramp'])
        routing_widget_layout.addRow('Route class', self.route_params[routing_pos])

        # 2
        routing_pos = RouteParams.one_way.value
        self.route_params[routing_pos] = QCheckBox(routing_widget)
        self.route_params[routing_pos].clicked.connect(self.command_route_params_edited)
        routing_widget_layout.addRow('One way', self.route_params[routing_pos])

        # 3
        routing_pos = RouteParams.route_is_toll.value
        self.route_params[routing_pos] = QCheckBox(routing_widget)
        self.route_params[routing_pos].clicked.connect(self.command_route_params_edited)
        routing_widget_layout.addRow('Route is toll', self.route_params[routing_pos])

        # 4
        routing_pos = RouteParams.no_emergency.value
        self.route_params[routing_pos] = QCheckBox(routing_widget)
        self.route_params[routing_pos].clicked.connect(self.command_route_params_edited)
        routing_widget_layout.addRow('No emergency', self.route_params[routing_pos])

        # 5
        routing_pos = RouteParams.no_delivery.value
        self.route_params[routing_pos] = QCheckBox(routing_widget)
        self.route_params[routing_pos].clicked.connect(self.command_route_params_edited)
        routing_widget_layout.addRow('No delivery', self.route_params[routing_pos])

        # 6
        routing_pos = RouteParams.no_car_motorcycle.value
        self.route_params[routing_pos] = QCheckBox(routing_widget)
        self.route_params[routing_pos].clicked.connect(self.command_route_params_edited)
        routing_widget_layout.addRow('No car/motorcycle', self.route_params[routing_pos])

        # 7
        routing_pos = RouteParams.no_bus.value
        self.route_params[routing_pos] = QCheckBox(routing_widget)
        self.route_params[routing_pos].clicked.connect(self.command_route_params_edited)
        routing_widget_layout.addRow('No bus', self.route_params[routing_pos])

        # 8
        routing_pos = RouteParams.no_taxi.value
        self.route_params[routing_pos] = QCheckBox(routing_widget)
        self.route_params[routing_pos].clicked.connect(self.command_route_params_edited)
        routing_widget_layout.addRow('No taxi', self.route_params[routing_pos])

        # 9
        routing_pos = RouteParams.no_pedestrian.value
        self.route_params[routing_pos] = QCheckBox(routing_widget)
        self.route_params[routing_pos].clicked.connect(self.command_route_params_edited)
        routing_widget_layout.addRow('No pedestrian', self.route_params[routing_pos])

        # 10
        routing_pos = RouteParams.no_bicycle.value
        self.route_params[routing_pos] = QCheckBox(routing_widget)
        self.route_params[routing_pos].clicked.connect(self.command_route_params_edited)
        routing_widget_layout.addRow('No bicycle', self.route_params[routing_pos])

        # 11
        routing_pos = RouteParams.no_truck.value
        self.route_params[routing_pos] = QCheckBox(routing_widget)
        self.route_params[routing_pos].clicked.connect(self.command_route_params_edited)
        routing_widget_layout.addRow('No truck', self.route_params[routing_pos])

        # karta właściwości wezlow
        node_widget = QWidget()
        self.tab_names_vs_index['nody'] = self.tab_widget.addTab(node_widget, 'Węzły')
        node_widget_layout = QVBoxLayout()
        node_widget.setLayout(node_widget_layout)
        node_has_numeration_layout = QFormLayout()
        self.node_has_numeration = QCheckBox()
        self.node_has_numeration.toggled.connect(self.switch_on_of_numerations)
        node_has_numeration_layout.addRow('Węzeł ma numerację', self.node_has_numeration)
        node_widget_layout.addLayout(node_has_numeration_layout)

        node_properties_layout = QVBoxLayout()
        node_widget_layout.addLayout(node_properties_layout)
        left_side_gb = QGroupBox('Lewa strona numeracji po węźle')
        node_properties_layout.addWidget(left_side_gb)
        left_side_numbering = QFormLayout()
        left_side_gb.setLayout(left_side_numbering)
        self.left_side_num_data = {'left_side_numbering_style': QComboBox()}
        self.left_side_num_data['left_side_numbering_style'].addItem('None')
        self.left_side_num_data['left_side_numbering_style'].addItem('Parzysty (2, 4, 6, 8)')
        self.left_side_num_data['left_side_numbering_style'].addItem('Nieparzysty (1, 3, 5, 7)')
        self.left_side_num_data['left_side_numbering_style'].addItem('Ciągły (1, 2, 3, 4)')
        left_side_numbering.addRow('Styl numeracji', self.left_side_num_data['left_side_numbering_style'])
        self.left_side_num_data['left_side_number_after'] = QLineEdit()
        left_side_numbering.addRow('Zacznij od', self.left_side_num_data['left_side_number_after'])
        self.left_side_num_data['left_side_zip_code'] = QLineEdit()
        left_side_numbering.addRow('Kod poczt.', self.left_side_num_data['left_side_zip_code'])
        self.left_side_num_data['left_side_city'] = QLineEdit()
        left_side_numbering.addRow('Miasto', self.left_side_num_data['left_side_city'])
        self.left_side_num_data['left_side_region'] = QLineEdit()
        left_side_numbering.addRow('Region', self.left_side_num_data['left_side_region'])
        self.left_side_num_data['left_side_country'] = QLineEdit()
        left_side_numbering.addRow('Państwo', self.left_side_num_data['left_side_country'])

        left_side_gb_przed = QGroupBox('Lewa strona numeracji przed węzłem')
        node_properties_layout.addWidget(left_side_gb_przed)
        self.left_side_num_data['left_side_number_before'] = QLineEdit()
        left_side_numbering_przed = QFormLayout()
        left_side_gb_przed.setLayout(left_side_numbering_przed)
        left_side_numbering_przed.addRow('Skończ na', self.left_side_num_data['left_side_number_before'])

        right_side_gb = QGroupBox('Prawa strona numeracji po węźle')
        node_properties_layout.addWidget(right_side_gb)
        right_side_numbering = QFormLayout()
        right_side_gb.setLayout(right_side_numbering)
        self.right_side_num_data = {'right_side_numbering_style': QComboBox()}
        self.right_side_num_data['right_side_numbering_style'].addItem('None')
        self.right_side_num_data['right_side_numbering_style'].addItem('Parzysty (2, 4, 6, 8)')
        self.right_side_num_data['right_side_numbering_style'].addItem('Nieparzysty (1, 3, 5, 7)')
        self.right_side_num_data['right_side_numbering_style'].addItem('Ciągły (1, 2, 3, 4)')
        right_side_numbering.addRow('Styl numeracji', self.right_side_num_data['right_side_numbering_style'])
        self.right_side_num_data['right_side_number_after'] = QLineEdit()
        right_side_numbering.addRow('Zacznij od', self.right_side_num_data['right_side_number_after'])
        self.right_side_num_data['right_side_zip_code'] = QLineEdit()
        right_side_numbering.addRow('Kod poczt.', self.right_side_num_data['right_side_zip_code'])
        self.right_side_num_data['right_side_city'] = QLineEdit()
        right_side_numbering.addRow('Miasto', self.right_side_num_data['right_side_city'])
        self.right_side_num_data['right_side_region'] = QLineEdit()
        right_side_numbering.addRow('Region', self.right_side_num_data['right_side_region'])
        self.right_side_num_data['right_side_country'] = QLineEdit()
        right_side_numbering.addRow('Państwo', self.right_side_num_data['right_side_country'])

        right_side_gb_przed = QGroupBox('Prawa strona numeracji przed węzłem')
        node_properties_layout.addWidget(right_side_gb_przed)
        self.right_side_num_data['right_side_number_before'] = QLineEdit()
        right_side_numbering_przed = QFormLayout()
        right_side_gb_przed.setLayout(right_side_numbering_przed)
        right_side_numbering_przed.addRow('Skończ na', self.right_side_num_data['right_side_number_before'])
        self.switch_on_of_numerations(False)

    def reverse_polyline(self, event):
        print(self.map_object_id)
        if self.map_object_id is not None:
            self.map_object_id.command_reverse_poly()

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
        if not isinstance(self.map_object_id, map_items.PolylineQGraphicsPathItem):
            self.poly_direction.setDisabled(True)
            self.reverse_direction_button.setDisabled(True)
        else:
            self.poly_direction.setDisabled(False)
            self.reverse_direction_button.setDisabled(False)
            if self.map_object_id.get_dirindicator():
                self.poly_direction.setChecked(True)
            else:
                self.poly_direction.setChecked(False)
        if self.map_object_id.get_endlevel():
            self.end_level.setText(str(self.map_object_id.get_endlevel()))
        else:
            self.end_level.setText('')
        if self.map_object_id.get_comment():
            self.comment_text_edit.setPlainText('\n'.join(self.map_object_id.get_comment()) + '\n')
        else:
            self.comment_text_edit.setPlainText('')

        # wypelniamy adresy, ale tylko dla poi
        if not isinstance(self.map_object_id, map_items.PoiAsPixmap):
            self.tab_widget.setTabEnabled(self.tab_names_vs_index['adres'], False)
        else:
            self.tab_widget.setTabEnabled(self.tab_names_vs_index['adres'], True)
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

        # wypelniamy elements:
        self.elements_table.setRowCount(0)
        for data_level_num, data_level in enumerate(self.map_object_id.data0.get_data_levels()):
            for poly_num, poly in enumerate(self.map_object_id.data0.get_polys_for_data_level(data_level)):
                row_num = data_level_num + poly_num
                self.elements_table.insertRow(row_num)
                self.elements_table.setItem(row_num, 0, QTableWidgetItem(str(row_num)))
                self.elements_table.setItem(row_num, 1, QTableWidgetItem(str(data_level)))
                lat, lot = poly[0].get_geo_coordinates()
                self.elements_table.setItem(row_num, 2, QTableWidgetItem(f"{lat:.6f}, {lot:.6f}"))
                self.elements_table.setItem(row_num, 3, QTableWidgetItem(str(len(poly))))

        if not isinstance(self.map_object_id, map_items.PolylineQGraphicsPathItem):
            self.tab_widget.setTabEnabled(self.tab_names_vs_index['routing'], False)
        else:
            self.tab_widget.setTabEnabled(self.tab_names_vs_index['routing'], True)
            # jesli route param ma dany obiekt to wypelnij je
            if self.map_object_id.get_route_params() is not None:
                routing_data = self.map_object_id.get_route_params()
                if all(a == 0 for a in routing_data):
                    return
                for index, val in enumerate(routing_data):
                    if index == RouteParams.speed_limit.value or index == RouteParams.route_class.value:
                        self.route_params[index].setCurrentIndex(0)
                        self.route_params[index].setCurrentIndex(val)
                    else:
                        self.route_params[index].setChecked(False)
                        self.route_params[index].setChecked(bool(val))
            else:
                # w przeciwnym wypadku ustaw wszystko jako nieustawione
                for route_param in RouteParams:
                    if route_param == RouteParams.speed_limit or route_param == RouteParams.route_class:
                        self.route_params[route_param.value].setCurrentIndex(0)
                    else:
                        self.route_params[route_param.value].setChecked(False)


        others = self.map_object_id.get_others()
        if others:
            self.extras_table.setRowCount(0)
            self.extras_table.setRowCount(len(others) + 1)
            for row, item in enumerate(others):
                self.extras_table.setItem(row, 0, QTableWidgetItem(item[0]))
                self.extras_table.setItem(row, 1, QTableWidgetItem(item[1]))
        else:
            for row in range(self.extras_table.rowCount()):
                self.extras_table.setItem(row, 0, QTableWidgetItem(''))
                self.extras_table.setItem(row, 1, QTableWidgetItem(''))

    def  fill_map_object_properties_node(self, node):
        if node.node_has_numeration():
            self.node_has_numeration.setChecket(True)

    def switch_on_of_numerations(self, val):
        if val:
            for num_key in self.right_side_num_data:
                self.right_side_num_data[num_key].setEnabled(True)
            for num_key in self.left_side_num_data:
                self.left_side_num_data[num_key].setEnabled(True)
        else:
            for num_key in self.right_side_num_data:
                self.right_side_num_data[num_key].setEnabled(False)
            for num_key in self.left_side_num_data:
                self.left_side_num_data[num_key].setEnabled(False)
        # self.map_object_id.data0.get_calculated_housenumber_defs_for_node(data_level, poly_num, node_num)

    def command_dirindicator_changed(self):
        print(self.poly_direction.checkState())
        self.map_object_id.command_set_dirindicator(bool(self.poly_direction.checkState()))

    def command_label1_entry_edited(self):
        if self.map_object_id is not None:
            self.map_object_id.command_update_labels(1, self.label1_entry.text())

    def command_label2_entry_edited(self):
        if self.map_object_id is not None:
            self.map_object_id.command_update_labels(2, self.label2_entry.text())

    def command_label3_entry_edited(self):
        if self.map_object_id is not None:
            self.map_object_id.command_update_labels(3, self.label3_entry.text())

    def command_end_level_entry_edited(self):
        return

    def command_streetdesc_edited(self):
        self.map_object_id.command_update_address(self.streetdesc.text(), 'StreetDesc')

    def command_housenumber_edited(self):
        self.map_object_id.command_update_address(self.housenumber.text(), 'HouseNumber')

    def command_phone_edited(self):
        self.map_object_id.command_update_address(self.phone.text(), 'PhoneNumber')

    def command_route_params_edited(self, value):
        route_defs = list()
        for item_num in range(len(self.route_params)):
            if item_num == RouteParams.speed_limit.value or item_num == RouteParams.route_class.value:
                route_defs.append(self.route_params[item_num].currentIndex())
            else:
                route_defs.append(1 if self.route_params[item_num].checkState() >= 1 else 0)
        self.map_object_id.command_set_route_params(route_defs)


class ExtrasTable(QTableWidget):
    def __init__(self, rows, columns, parent):
        super(ExtrasTable, self).__init__(rows, columns, parent)
        self.setContextMenuPolicy(Qt.DefaultContextMenu)

    # https://stackoverflow.com/questions/65371143/create-a-context-menu-with-pyqt5
    def contextMenuEvent(self, event):
        menu = QMenu()
        add_row_action = menu.addAction('Dodaj wiersz')
        add_row_action.triggered.connect(self.add_row)
        delete_row_action = menu.addAction('Usun wiersz')
        delete_row_action.triggered.connect(self.remove_row)
        res = menu.exec_(event.globalPos())


    def remove_row(self, event):
        self.removeRow(self.currentRow())

    def add_row(self, event):
        self.insertRow(self.currentRow())
