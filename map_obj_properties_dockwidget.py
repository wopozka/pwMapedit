#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import (QDockWidget, QMenu, QLabel, QHBoxLayout, QVBoxLayout, QComboBox, QLineEdit, QCheckBox,
                             QPushButton, QGroupBox, QCompleter, QApplication)
from PyQt5.QtWidgets import QFormLayout, QTabWidget
from PyQt5.QtWidgets import QPlainTextEdit, QWidget, QTableWidget, QTableWidgetItem, QTreeWidget, QTreeWidgetItem
from PyQt5.QtCore import Qt, QSortFilterProxyModel, QObject, pyqtSignal, QMimeData, QByteArray
from PyQt5.QtGui import QIcon, QPainterPath
from enum import Enum
import json
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
        self.current_labels_vals = []
        self.current_address_vals = []
        # tab_widget.setTabPosition(QTabWidget.West)
        dock_widget = QWidget()
        self.tab_names_vs_index['glowny'] = self.tab_widget.addTab(dock_widget, 'Główny')
        dock_box = QVBoxLayout()
        self.setWidget(self.tab_widget)
        dock_widget.setLayout(dock_box)
        type_labels_layout = QFormLayout()
        self.type_selector = TypeComboBox(dock_widget)
        self.type_selector.currentIndexChanged.connect(self.command_type_changed)
        self.type_selector.setEditable(True)
        type_labels_layout.addRow('Type', self.type_selector)
        self.label1_entry = QLineEdit(dock_widget)
        self.label1_entry.editingFinished.connect(self.command_label1_entry_edited)
        type_labels_layout.addRow('Label', self.label1_entry)
        self.label2_entry = QLineEdit(dock_widget)
        self.label2_entry.editingFinished.connect(self.command_label2_entry_edited)
        type_labels_layout.addRow('Label2', self.label2_entry)
        self.label3_entry = QLineEdit(dock_widget)
        self.label3_entry.editingFinished.connect(self.command_label3_entry_edited)
        type_labels_layout.addRow('Label3', self.label3_entry)
        self.end_level = QComboBox(dock_widget)
        for a in range(6):
            self.end_level.addItem(str(a))
        self.connect_end_level_widget_signals()
        type_labels_layout.addRow('EndLevel', self.end_level)

        dock_box.addLayout(type_labels_layout)

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
        self.comment_text_edit = CommentTextEdit(dock_widget)
        self.comment_text_edit.signals.comment_changed.connect(self.command_comment_changed)
        comment_box = QVBoxLayout()
        comment_box.addWidget(comment_label)
        comment_box.addWidget(self.comment_text_edit)
        dock_box.addLayout(comment_box)

        # pozostałe elementy - Extras
        extras_label = QLabel('Extras', dock_widget)
        self.extras_table = ExtrasTable(3, 2, dock_widget)
        self.extras_table.cellChanged.connect(self.command_extras_table_changed)
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
        self.elements_table = ElementsTable(dock_widget)
        self.elements_table.itemSelectionChanged.connect(self.elements_item_highlighted)
        elements_layout_box = QVBoxLayout()
        elements_widgets.setLayout(elements_layout_box)
        elements_layout_box.addWidget(self.elements_table)

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
        self.node_has_numeration.clicked.connect(self.switch_on_of_numerations)
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
        self.left_side_num_data['left_side_number_after'] = NumberEdit(only_numbers=True)
        left_side_numbering.addRow('Zacznij od', self.left_side_num_data['left_side_number_after'])
        self.left_side_num_data['left_side_number_before'] = NumberEdit(only_numbers=True)
        left_side_numbering.addRow('Skończ na', self.left_side_num_data['left_side_number_before'])
        self.left_side_num_data['left_side_zip_code'] = NumberEdit(only_numbers=False)
        left_side_numbering.addRow('Kod poczt.', self.left_side_num_data['left_side_zip_code'])
        self.left_side_num_data['left_side_city'] = NumberEdit(only_numbers=False)
        left_side_numbering.addRow('Miasto', self.left_side_num_data['left_side_city'])
        self.left_side_num_data['left_side_region'] = NumberEdit(only_numbers=False)
        left_side_numbering.addRow('Region', self.left_side_num_data['left_side_region'])
        self.left_side_num_data['left_side_country'] = NumberEdit(only_numbers=False)
        left_side_numbering.addRow('Państwo', self.left_side_num_data['left_side_country'])

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
        self.right_side_num_data['right_side_number_after'] = NumberEdit(only_numbers=True)
        right_side_numbering.addRow('Zacznij od', self.right_side_num_data['right_side_number_after'])
        self.right_side_num_data['right_side_number_before'] = NumberEdit(only_numbers=True)
        right_side_numbering.addRow('Skończ na', self.right_side_num_data['right_side_number_before'])
        self.right_side_num_data['right_side_zip_code'] = NumberEdit(only_numbers=False)
        right_side_numbering.addRow('Kod poczt.', self.right_side_num_data['right_side_zip_code'])
        self.right_side_num_data['right_side_city'] = NumberEdit(only_numbers=False)
        right_side_numbering.addRow('Miasto', self.right_side_num_data['right_side_city'])
        self.right_side_num_data['right_side_region'] = NumberEdit(only_numbers=False)
        right_side_numbering.addRow('Region', self.right_side_num_data['right_side_region'])
        self.right_side_num_data['right_side_country'] = NumberEdit(only_numbers=False)
        right_side_numbering.addRow('Państwo', self.right_side_num_data['right_side_country'])
        self.connect_numbering_widgets_signals()

        hlevel_gb = QGroupBox('Hlevel na węźle')
        node_properties_layout.addWidget(hlevel_gb)
        hlevel_layout = QFormLayout()
        hlevel_gb.setLayout(hlevel_layout)
        self.node_hlevel = QComboBox()
        self.node_hlevel.addItem('Brak')
        for a in range(-2, 16):
            self.node_hlevel.addItem(str(a))
        self.connect_hlevel_widget_signal()
        hlevel_layout.addRow('Hlevel dla węzła', self.node_hlevel)
        node_widget_layout.addStretch()
        self.switch_on_numerations_fields()
        self.set_dock_off()

    def address_changed(self):
        if [a.text().strip() for a in (self.streetdesc, self.housenumber, self.phone)] != self.current_address_vals:
            return True
        return False

    def clear_numeration_fields(self):
        self.disconnect_numbering_widgets_signals()
        for left_right in (self.left_side_num_data, self.right_side_num_data):
            for key, val in left_right.items():
                if 'style' in key:
                    val.setCurrentIndex(-1)
                else:
                    val.clear()
        self.connect_numbering_widgets_signals()

    def command_comment_changed(self):
        self.map_object_id.command_update_comment(self.comment_text_edit.toPlainText())

    def command_dirindicator_changed(self):
        self.map_object_id.command_set_dirindicator(bool(self.poly_direction.checkState()))

    def command_hlevel_changed(self):
        if self.node_hlevel.currentIndex() > 0:
            self.map_object_id.node_grip_set_hlevel(self.node_hlevel.itemText(self.node_hlevel.currentIndex()))
        else:
            self.map_object_id.node_grip_set_hlevel(None)

    def command_label1_entry_edited(self):
        if not self.labels_changed():
            return
        if self.map_object_id is not None:
            self.map_object_id.command_update_labels(1, self.label1_entry.text())

    def command_label2_entry_edited(self):
        if not self.labels_changed():
            return
        if self.map_object_id is not None:
            self.map_object_id.command_update_labels(2, self.label2_entry.text())

    def command_label3_entry_edited(self):
        if not self.labels_changed():
            return
        if self.map_object_id is not None:
            self.map_object_id.command_update_labels(3, self.label3_entry.text())

    def command_end_level_changed(self):
        self.map_object_id.command_update_endlevel(int(self.end_level.currentText()))

    def command_extras_table_changed(self, row, column):
        if not self.extras_table.is_table_modified():
            return
        if self.map_object_id is not None:
            self.map_object_id.command_update_extras(self.extras_table.get_current_content())
        #     print('tabela zmodyfikowan')
        #     print(self.extras_table.get_current_content())
        #     print('zapisuje nowy content')
        #     self.extras_table.save_current_content()
        # else:
        #     print('tabela niezmodyfikowana')

    def command_streetdesc_edited(self):
        if self.address_changed():
            self.map_object_id.command_update_address(self.streetdesc.text(), 'StreetDesc')

    def command_housenumber_edited(self):
        if self.address_changed():
            self.map_object_id.command_update_address(self.housenumber.text(), 'HouseNumber')

    def command_phone_edited(self):
        if self.address_changed():
            self.map_object_id.command_update_address(self.phone.text(), 'PhoneNumber')

    def command_route_params_edited(self, value):
        route_defs = list()
        for item_num in range(len(self.route_params)):
            if item_num == RouteParams.speed_limit.value or item_num == RouteParams.route_class.value:
                route_defs.append(self.route_params[item_num].currentIndex())
            else:
                route_defs.append(1 if self.route_params[item_num].checkState() >= 1 else 0)
        self.map_object_id.command_set_route_params(route_defs)

    def command_numeration_style_edited(self, new_index):
        if self.left_side_num_data['left_side_numbering_style'].currentIndex() > 0:
            if not self.left_side_num_data['left_side_number_after'].text():
                self.left_side_num_data['left_side_number_after'].setText('0')
            self.left_side_num_data['left_side_number_after'].set_empty_not_allowed()
        else:
            self.left_side_num_data['left_side_number_after'].clear()
            self.left_side_num_data['left_side_number_after'].set_empty_allowed()
        if self.right_side_num_data['right_side_numbering_style'].currentIndex() > 0:
            if not self.right_side_num_data['right_side_number_after'].text():
                self.right_side_num_data['right_side_number_after'].setText('0')
            self.right_side_num_data['right_side_number_after'].set_empty_not_allowed()
        else:
            self.right_side_num_data['right_side_number_after'].clear()
            self.right_side_num_data['right_side_number_after'].set_empty_allowed()
        print('num style edited')
        self.command_set_numeration_to_node()

    def command_set_numeration_to_node(self):
        print('Uaktualniam numeracje, nowa numeracja: ', self.get_node_numeration_definition_from_form())
        # return
        self.map_object_id.node_grip_set_numeration(self.get_node_numeration_definition_from_form())

    def command_type_changed(self, new_index):
        self.map_object_id.command_update_type(self.type_selector.itemData(new_index))

    def connect_end_level_widget_signals(self):
        self.end_level.currentIndexChanged.connect(self.command_end_level_changed)

    def connect_numbering_widgets_signals(self):
        for left_right in (self.left_side_num_data, self.right_side_num_data):
            for key, val in left_right.items():
                if 'style' in key:
                    val.currentIndexChanged.connect(self.command_numeration_style_edited)
                else:
                    val.signals.comment_changed.connect(self.command_set_numeration_to_node)

    def connect_hlevel_widget_signal(self):
        self.node_hlevel.currentIndexChanged.connect(self.command_hlevel_changed)

    def disconnect_end_level_widget_signal(self):
        self.end_level.currentIndexChanged.disconnect()

    def disconnect_hlevel_widget_signal(self):
        self.node_hlevel.currentIndexChanged.disconnect()

    def disconnect_numbering_widgets_signals(self):
        for left_right in (self.left_side_num_data, self.right_side_num_data):
            for key, val in left_right.items():
                if 'style' in key:
                    val.currentIndexChanged.disconnect()
                else:
                    val.signals.comment_changed.disconnect()

    def fill_map_object_properties(self):
        if self.map_object_id is None:
            return
        if isinstance(self.map_object_id, map_items.GripItem):
            self.fill_map_object_properties_node_when_selected()
            self.tab_widget.setCurrentIndex(self.tab_names_vs_index['nody'])
        else:
            self.fill_map_object_properties_type()
            self.fill_map_object_properties_labels()
            self.fill_map_object_properties_poly_direction()
            self.fill_map_object_properties_endlevel()
            self.fill_map_object_properties_comment()
            self.fill_map_object_properties_poi_address()
            self.fill_map_object_properteies_elements()
            self.fill_map_object_properties_routing()
            self.fill_map_object_properties_others()
        self.tab_widget.update()


    def fill_map_object_properties_poi_address(self):
        if not isinstance(self.map_object_id, map_items.PoiAsPixmap):
            self.tab_widget.setTabEnabled(self.tab_names_vs_index['adres'], False)
        else:
            self.tab_widget.setTabEnabled(self.tab_names_vs_index['adres'], True)
            if self.map_object_id.get_street_desc():
                self.streetdesc.setText(self.map_object_id.get_street_desc())
            else:
                self.streetdesc.clear()
            if self.map_object_id.get_house_number():
                self.housenumber.setText(self.map_object_id.get_house_number())
            else:
                self.housenumber.clear()
            if self.map_object_id.get_phone_number():
                self.phone.setText(self.map_object_id.get_phone_number())
            else:
                self.phone.clear()
            self.save_current_address()

    def fill_map_object_properties_comment(self):
        if self.map_object_id.get_comment():
            self.comment_text_edit.setPlainText('\n'.join(self.map_object_id.get_comment()) + '\n')
        else:
            self.comment_text_edit.clear()

    def fill_map_object_properteies_elements(self):
        # sprawdzic czy nie trzeba wlaczac i wylaczac sygnalu
        # self.elements_table.itemSelectionChanged.disconnect()
        self.elements_table.clear()
        if isinstance(self.map_object_id, map_items.PoiAsPixmap):
            data_level = self.map_object_id.data0.get_data_levels()[0]
            data_item = ElementsItem(self.elements_table)
            data_item.setText(0, str('Data' + str(data_level)))
            scene_coords = self.map_object_id.data0.get_polys_for_data_level(data_level)[0][0]
            lat, lon = scene_coords.get_geo_coordinates()
            poly_item = ElementsItem(data_item)
            poly_item.setText(0, 'POI')
            poly_item.setText(1, '')
            poly_item.set(2, f"{lat:.6f}, {lon:.6f}")
            poly_item.setData(2, Qt.UserRole, scene_coords)
        else:
            for data_level_num, data_level in enumerate(self.map_object_id.data0.get_data_levels()):
                data_level_polygons = self.map_object_id._mp_data[data_level].toSubpathPolygons()
                data_item = ElementsItem(self.elements_table)
                data_item.setText(0, str('Data' + str(data_level)))
                # poly_pp = QPainterPath()
                outer_poly = None
                for poly_num, poly in enumerate(self.map_object_id.data0.get_polys_for_data_level(data_level)):
                    if outer_poly is None:
                        poly_pp = QPainterPath()
                        outer_poly = ElementsItem(data_item)
                        lat, lon = poly[0].get_geo_coordinates()
                        outer_poly.setText(0, f'Poly: {poly_num}')
                        outer_poly.setText(1, 'Outer')
                        outer_poly.setText(2, f"{lat:.6f}, {lon:.6f}")
                        outer_poly.setData(0, Qt.UserRole, data_level_num)
                        outer_poly.setData(1, Qt.UserRole, poly_num)
                        poly_pp.addPolygon(data_level_polygons[poly_num])
                        outer_poly.setData(2, Qt.UserRole, poly_pp)
                        if not self.map_object_id.is_polygon():
                            outer_poly = None
                        continue
                    else:
                        poly_item = ElementsItem()
                        lat, lon = poly[0].get_geo_coordinates()
                        poly_item.setText(0, f'Poly: {poly_num}')
                        poly_item.setText(2, f"{lat:.6f}, {lon:.6f}")
                    poly_item.setData(0, Qt.UserRole, data_level_num)
                    poly_item.setData(1, Qt.UserRole, poly_num)
                    poly_pp1 = QPainterPath()
                    poly_pp1.addPolygon(data_level_polygons[poly_num])
                    poly_item.setData(2, Qt.UserRole, poly_pp1)
                    if poly_pp.contains(poly_pp1):
                        outer_poly.addChild(poly_item)
                        poly_item.setText(1, 'Inner')
                        poly_pp.addPath(poly_pp1)
                    else:
                        data_item.addChild(poly_item)
                        poly_item.setText(1, 'outer')
                        outer_poly = poly_item
                        poly_pp = poly_pp1
        # sprawdzic czy nie trzeba wlaczac i wylaczac sygnalu
        # self.elements_table.itemSelectionChanged.connect(self.elements_item_highlighted)

    def fill_map_object_properties_endlevel(self):
        self.disconnect_end_level_widget_signal()
        if self.map_object_id.get_endlevel():
            self.end_level.setCurrentIndex(self.map_object_id.get_endlevel())
        else:
            self.end_level.setCurrentIndex(0)
        self.connect_end_level_widget_signals()

    def fill_map_object_properties_others(self):
        others = self.map_object_id.get_others()
        self.extras_table.cellChanged.disconnect()
        if others:
            self.extras_table.clear_contents()
            self.extras_table.setRowCount(0)
            self.extras_table.setRowCount(len(others) + 1)
            for row, key_val in enumerate(others):
                self.extras_table.set_items(row, key_val)
        else:
            self.extras_table.clear_contents()
        self.tab_widget.setCurrentIndex(self.tab_names_vs_index['glowny'])
        self.extras_table.cellChanged.connect(self.command_extras_table_changed)

    def fill_map_object_properties_labels(self):
        if self.map_object_id.get_label1():
            self.label1_entry.setText(self.map_object_id.get_label1())
        else:
            self.label1_entry.clear()
        if self.map_object_id.get_label2():
            self.label2_entry.setText(self.map_object_id.get_label2())
        else:
            self.label2_entry.clear()
        if self.map_object_id.get_label3():
            self.label3_entry.setText(self.map_object_id.get_label3())
        else:
            self.label3_entry.clear()
        self.save_current_labels()

    def fill_map_object_properties_poly_direction(self):
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

    def fill_map_object_properties_routing(self):
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

    def fill_map_object_properties_type(self):
        # wypełniamy type
        self.type_selector.currentIndexChanged.disconnect()
        self.type_selector.clear()
        if isinstance(self.map_object_id, map_items.PoiAsPixmap):
            cur_index = -1
            for poi_type, val in self.map_object_id._map_objects_properties.get_poi_type_name_alias().items():
                cur_index += 1
                icon = QIcon(val[0])
                p_type = str(hex(poi_type)) + ' '
                category = '(' + val[1] + '), '
                name = val[2] + ', '
                aliases = val[3]
                self.type_selector.addItem(icon, p_type + category + name + aliases, userData=poi_type)
                if poi_type == self.map_object_id.get_type():
                    self.type_selector.setCurrentIndex(cur_index)
                self.type_selector.setItemData(cur_index, poi_type)
        else:
            if isinstance(self.map_object_id, map_items.PolylineQGraphicsPathItem):
                poly_types = self.map_object_id._map_objects_properties.get_line_type_names()
            else:
                poly_types = self.map_object_id._map_objects_properties.get_polygon_type_names()
            cur_index = -1
            for poly_type, val in poly_types.items():
                cur_index += 1
                p_type = str(hex(poly_type)) + ' '
                category = '(' + val[0] + '), '
                name_en = val[1]
                name_pl = ', ' + val[2] if val[2] else ''
                self.type_selector.addItem(p_type + category + name_en + name_pl)
                if poly_type == self.map_object_id.get_type():
                    self.type_selector.setCurrentIndex(cur_index)
                self.type_selector.setItemData(cur_index, poly_type)
        self.type_selector.currentIndexChanged.connect(self.command_type_changed)

    def fill_map_object_properties_node_when_selected(self):
        # w tym przypadku map_object_id jest grip_item, więc musimy się dopytać grip_item o dane odnośnie numeracji
        # oraz hlevel
        if self.map_object_id.node_grip_has_numeration():
            self.node_has_numeration.setChecked(True)
            print(self.map_object_id.node_grip_get_numeration())
            self.fill_map_object_properties_node_numeration(self.map_object_id.node_grip_get_numeration())
        else:
            self.node_has_numeration.setChecked(False)
            self.clear_numeration_fields()
            self.switch_off_numerations_fields()
        self.fill_map_object_properties_node_hlevel(self.map_object_id.node_grip_get_hlevel())

    def fill_map_object_properties_node_numeration(self, number_definition):
        print(number_definition)
        self.disconnect_numbering_widgets_signals()
        if number_definition is not None:
            self.switch_on_numerations_fields()
            num_dict = number_definition._asdict()
            for key in num_dict:
                if 'left' in key:
                    side_of_road = self.left_side_num_data
                else:
                    side_of_road = self.right_side_num_data
                if 'style' in key:
                    num_style = {None: 0, 'N': 0, 'E': 1, 'O': 2, 'B': 3}
                    side_of_road[key].setCurrentIndex(num_style[num_dict[key]])
                else:
                    if num_dict[key] is None:
                       side_of_road[key].clear()
                       if 'before' in key:
                           side_of_road[key].set_empty_allowed()
                    else:
                        side_of_road[key].setText(str(num_dict[key]))
                        side_of_road[key].set_empty_not_allowed()
        self.connect_numbering_widgets_signals()

    def fill_map_object_properties_node_hlevel(self, hlevel_definition):
        self.disconnect_hlevel_widget_signal()
        if hlevel_definition is None:
            self.node_hlevel.setCurrentIndex(0)
        else:
            self.node_hlevel.setCurrentIndex(int(hlevel_definition) + 3)
        self.connect_hlevel_widget_signal()

    def get_node_numeration_definition_from_form(self):
        definition = dict()
        for left_right in (self.left_side_num_data, self.right_side_num_data):
            for key, widget in left_right.items():
                if 'style' in key:
                    _index = widget.currentIndex()
                    if _index == 1:
                        definition[key] = 'E'
                    elif _index == 2:
                        definition[key] = 'O'
                    elif _index == 3:
                        definition[key] = 'B'
                    else:
                        definition[key] = None
                elif 'before' in key or 'after' in key:
                    if widget.text():
                        definition[key] = int(widget.text())
                    else:
                        definition[key] = None
                else:
                    if widget.text():
                        definition[key] = widget.text().strip()
                    else:
                        definition[key] = None
        return map_items.Numbers_Definition(**definition)

    def labels_changed(self):
        if ([a.text().strip() for a in (self.label1_entry, self.label2_entry, self.label3_entry)]
                != self.current_labels_vals):
            return True
        return False

    def reverse_polyline(self, event):
        print(self.map_object_id)
        if self.map_object_id is not None:
            self.map_object_id.command_reverse_poly()

    def set_map_object_id(self, obj_id):
        if isinstance(obj_id, map_items.GripItem):
            self.set_dock_mode_edit_nodes()
        else:
            self.set_dock_mode_select()
        self.map_object_id = obj_id

    def switch_on_of_numerations(self, val):
        if val:
            self.switch_on_numerations_fields()
            numeration = self.map_object_id.node_grip_get_calculated_numeration()
            self.fill_map_object_properties_node_numeration(numeration)
            self.command_set_numeration_to_node()
        else:
            self.clear_numeration_fields()
            self.switch_off_numerations_fields()
            self.map_object_id.node_grip_set_numeration(None)

    def switch_off_numerations_fields(self):
        for num_key in self.right_side_num_data:
            self.right_side_num_data[num_key].setEnabled(False)
        for num_key in self.left_side_num_data:
            self.left_side_num_data[num_key].setEnabled(False)

    def switch_on_numerations_fields(self):
        for num_key in self.right_side_num_data:
            self.right_side_num_data[num_key].setEnabled(True)
        for num_key in self.left_side_num_data:
            self.left_side_num_data[num_key].setEnabled(True)

    def save_current_address(self):
        self.current_address_vals = [a.text().strip() for a in (self.streetdesc, self.housenumber, self.phone)]

    def save_current_labels(self):
        self.current_labels_vals = [a.text().strip() for a in (self.label1_entry, self.label2_entry, self.label3_entry)]

    def set_dock_mode_edit_nodes(self):
        for tab_name, tab_index in self.tab_names_vs_index.items():
            if tab_name != 'nody':
                print('wylaczam', tab_name)
                self.tab_widget.setTabEnabled(tab_index, False)
            else:
                self.tab_widget.setTabEnabled(tab_index, True)
        self.tab_widget.setCurrentIndex(self.tab_names_vs_index['nody'])
        self.tab_widget.update()

    def set_dock_mode_select(self):
        print('wlaczam select mode')
        for tab_name, tab_index in self.tab_names_vs_index.items():
            if tab_name == 'nody':
                self.tab_widget.setTabEnabled(tab_index, False)
            else:
                print('wlaczam', tab_name)
                self.tab_widget.setTabEnabled(tab_index, True)
        self.tab_widget.setCurrentIndex(self.tab_names_vs_index['glowny'])
        self.tab_widget.update()

    def set_dock_off(self):
        print('wylaczam dock')
        self.tab_widget.setCurrentIndex(self.tab_names_vs_index['glowny'])
        for tab_name, tab_index in self.tab_names_vs_index.items():
            if tab_name != 'glowny':
                self.tab_widget.setTabEnabled(tab_index, False)
        self.tab_widget.setTabEnabled(self.tab_names_vs_index['glowny'], False)
        self.tab_widget.update()

    def elements_item_highlighted(self):
        # jesli jest jakis element zaznaczony
        if self.elements_table.selectedItems():
            ppp = self.elements_table.selectedItems()[0].data(2, Qt.UserRole)
            self.map_object_id.scene().highlight_element(ppp, self.map_object_id.is_polygon())
        # gdy nie ma żadnego elementu zaznaczonego to i tak wywolaj funkcję. W razie czego usuwamy podswietlony element
        else:
            self.map_object_id.scene().highlight_element(None, False)
        return


class ExtrasTable(QTableWidget):
    def __init__(self, rows, columns, parent):
        super(ExtrasTable, self).__init__(rows, columns, parent)
        self.setHorizontalHeaderLabels(['Klucz', 'Wartość'])
        self.setContextMenuPolicy(Qt.DefaultContextMenu)
        self.current_table_content = list()

    # https://stackoverflow.com/questions/65371143/create-a-context-menu-with-pyqt5
    def contextMenuEvent(self, event):
        menu = QMenu()
        copy_text_action = menu.addAction('Kopiuj')
        paste_text_action = menu.addAction('Wklej')
        add_row_action_below = menu.addAction('Dodaj wiersz powyżej')
        add_row_action_below.triggered.connect(self.add_row_above)
        add_row_action_above = menu.addAction('Dodaj wiersz poniżej')
        add_row_action_above.triggered.connect(self.add_row_below)
        delete_row_action = menu.addAction('Usun wiersz')
        delete_row_action.triggered.connect(self.remove_row)
        res = menu.exec_(event.globalPos())

    def delete(self):
        for item in self.selectedItems():
            item.setText('')

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Down:
            if self.currentRow() == self.rowCount() - 1:
                self.add_row_below(event)
        super().keyPressEvent(event)

    def remove_row(self, event):
        cur_row = self.currentRow()
        self.removeRow(self.currentRow())
        self.cellChanged.emit(cur_row, 0)

    def set_items(self, row, key_val):
        self.setItem(row, 0, QTableWidgetItem(key_val[0]))
        self.setItem(row, 1, QTableWidgetItem(key_val[1]))
        self.current_table_content.append((key_val[0], key_val[1],))

    def add_row_above(self, event):
        self.insertRow(self.currentRow())

    def add_row_below(self, event):
        self.insertRow(self.currentRow() + 1)

    def copy(self):
        cells_indexes_to_copy = [(cell.row(), cell.column(),) for cell in self.selectedIndexes()]
        copy_content = []
        text_copy = ''
        for row in range(self.rowCount()):
            key = ''
            value = ''
            if (row, 0) in cells_indexes_to_copy:
                key = self.item(row, 0).text()
            if (row, 1) in cells_indexes_to_copy:
                value = self.item(row, 1).text()
            if key or value:
                copy_content.append([key, value,])
                text_copy += f'{key}\t{value}\n'
        if copy_content or text_copy:
            table_mime_data = QMimeData()
            table_mime_data_str = json.dumps(copy_content)
            print(table_mime_data_str)
            table_mime_data.setData('application/json', QByteArray(table_mime_data_str.encode('utf-8')))
            table_mime_data.setText(text_copy)
            return table_mime_data
        return None

    def cut(self):
        pass

    def clear_contents(self):
        self.clearContents()
        self.current_table_content.clear()

    def get_current_content(self):
        extras_data = list()
        for row_num in range(self.rowCount()):
            key_item = self.item(row_num, 0)
            if key_item is not None:
                key = key_item.text().strip()
            else:
                key = ''
            value_item = self.item(row_num, 1)
            if value_item is not None:
                value = self.item(row_num, 1).text().strip()
            else:
                value = ''
            if key and '=' not in key and value:
                extras_data.append((key, value,))
        return extras_data

    def paste(self, mime_data=None):
        if mime_data is None:
            mime_data = QApplication.clipboard().mimeData()
        if mime_data and mime_data.hasFormat('application/json'):
            _data = json.loads(mime_data.data('application/json').data().decode('utf-8'))
        elif mime_data and mime_data.hasText():
            _data = mime_data.text()
        else:
            return
        # wklejaj od tej pozycji do końca
        cur_row = self.currentRow()
        for row_num, row_content in enumerate(_data):
            row = row_num + cur_row
            if row >= self.rowCount():
                self.insertRow(self.rowCount())
            if row_content[0]:
                self.setItem(row, 0, QTableWidgetItem(row_content[0]))
            if row_content[1]:
                self.setItem(row, 1, QTableWidgetItem(row_content[1]))

    def save_current_content(self):
        self.current_table_content = self.get_current_content()

    def is_table_modified(self):
        current_list = self.get_current_content()
        orig_list = self.current_table_content
        print(current_list, orig_list)
        if current_list != orig_list:
            return True
        return False

class TypeComboBox(QComboBox):
    def __init__(self, parent=None):
        super(TypeComboBox, self).__init__(parent)

        self.setFocusPolicy(Qt.StrongFocus)
        self.setEditable(True)

        # add a filter model to filter matching items
        self.pFilterModel = QSortFilterProxyModel(self)
        self.pFilterModel.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.pFilterModel.setSourceModel(self.model())

        # add a completer, which uses the filter model
        self.completer = QCompleter(self.pFilterModel, self)
        # always show all (filtered) completions
        self.completer.setCompletionMode(QCompleter.UnfilteredPopupCompletion)
        self.setCompleter(self.completer)

        # connect signals
        self.lineEdit().textEdited[str].connect(self.pFilterModel.setFilterFixedString)
        self.completer.activated.connect(self.on_completer_activated)

    # on selection of an item from the completer, select the corresponding item from combobox
    def on_completer_activated(self, text):
        if text:
            index = self.findText(text)
            self.setCurrentIndex(index)
            self.activated[str].emit(self.itemText(index))

    # on model change, update the models of the filter and completer as well
    def setModel(self, model):
        super(TypeComboBox, self).setModel(model)
        self.pFilterModel.setSourceModel(model)
        self.completer.setModel(self.pFilterModel)

    # on model column change, update the model column of the filter and completer as well
    def setModelColumn(self, column):
        self.completer.setCompletionColumn(column)
        self.pFilterModel.setFilterKeyColumn(column)
        super(TypeComboBox, self).setModelColumn(column)


class CommentChangedSignal(QObject):
    comment_changed = pyqtSignal(str)

class CommentTextEdit(QPlainTextEdit):

    def __init__(self, parent):
        self.parent = parent
        self.old_text = ''
        self.signals = CommentChangedSignal()
        super(CommentTextEdit, self).__init__(parent)

    def focusOutEvent(self, event):
        if self.toPlainText() != self.old_text:
            self.old_text = self.toPlainText()
            self.signals.comment_changed.emit(self.toPlainText())
        super().focusOutEvent(event)

    def focusInEvent(self, event):
        self.old_text = self.toPlainText()
        super().focusInEvent(event)


class NumberEdit(QLineEdit):
    def __init__(self, only_numbers=False):
        self.only_numbers = only_numbers
        self.old_text = ''
        self.signals = CommentChangedSignal()
        self.valid_value = True
        self.empty_allowed = True
        super(NumberEdit, self).__init__()

    def focusInEvent(self, event):
        self.old_text = self.text().strip()
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        self.number_edited()
        super().focusOutEvent(event)

    def keyPressEvent(self, event):
        super().keyPressEvent(event)
        if self.only_numbers:
            text = self.text().strip()
            print('sprawdzam text', text)
            if text:
                try:
                    num_val = int(text)
                    if num_val < 0:
                        print('blad wartosci')
                        self.set_invalid()
                except ValueError:
                    self.set_invalid()
                else:
                    print('poprawna wartosc')
                    self.set_valid()
            else:
                if self.empty_allowed:
                    self.set_valid()
                else:
                    self.set_invalid()
        print(event.key(), Qt.Key_Enter)
        if event.key() == Qt.Key_Enter or event.key() == Qt.Key_Return:
            self.number_edited()

    def set_invalid(self):
        self.valid_value = False
        self.setStyleSheet("background-color: red")

    def set_valid(self):
        self.setStyleSheet("background-color: white")
        self.valid_value = True

    def number_edited(self):
        new_text = self.text().strip()
        if self.is_valid() and new_text != self.old_text:
            print('generuje number edited')
            self.signals.comment_changed.emit(new_text)

    def is_valid(self):
        if self.empty_allowed:
            if self.text().strip() and self.valid_value:
                return True
        return self.valid_value

    def set_empty_allowed(self):
        self.empty_allowed = True

    def set_empty_not_allowed(self):
        self.empty_allowed = False


class ElementsTable(QTreeWidget):
    def __init__(self, parent=None):
        super(ElementsTable, self).__init__(parent)
        self.setColumnCount(5)
        self.setHeaderLabels(['Nr Data/Nr poly', 'Inner/Outer', 'Lat/Lon 1 punkt', 'Węzły', 'Obszar'])
        self.setContextMenuPolicy(Qt.DefaultContextMenu)
        # self.customContextMenuRequested.connect(self.context_menu_requested)
        # self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        # self.setSortingEnabled(True)

    def contextMenuEvent(self, event):
        menu = QMenu()
        delete_action = menu.addAction('Usuń')
        delete_action.triggered.connect(self.command_delete_poly)
        paste_to_action = menu.addAction('Kopiuj do')
        # paste_text_action.triggered.connect(self.paste)
        res = menu.exec_(event.globalPos())

    def command_delete_poly(self):
        data_level = self.currentItem().data(0, Qt.UserRole)
        poly_num = self.currentItem().data(1, Qt.UserRole)
        print(f'data_level: {data_level}, poly_num: {poly_num}')
        return

class ElementsItem(QTreeWidgetItem):
    def __init__(self, parent=None):
        super(ElementsItem, self).__init__(parent)
        self.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        # self.setCheckState(0, Qt.Unchecked)
        self.setData(2, Qt.UserRole, None)  # to store QPainterPath

