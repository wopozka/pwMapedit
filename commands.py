from PyQt5.QtWidgets import QUndoCommand, QUndoStack
from PyQt5.QtGui import QPainterPath
from PyQt5.QtCore import QPointF
import copy
import time

class InsertNodeCmd(QUndoCommand):
    def __init__(self, map_object, index, pos, polygons, description):
        super(InsertNodeCmd, self).__init__(description)
        self.data0_copy = map_object.data0.copy()
        self.path_copy = QPainterPath(map_object.path())
        self.map_object = map_object
        self.path_num, self.coord_num = index
        self.pos = pos
        self.polygons = polygons
        self.data_level = self.map_object.current_data_x

    def redo(self):
        self.map_object.undecorate()
        self.map_object.data0.insert_node_at_position(self.data_level, self.path_num, self.coord_num,
                                                      self.pos.x(), self.pos.y())
        self.map_object.setPath(self.map_object.create_painter_path(self.polygons))
        self.update_children()
        if self.map_object.scene().get_pw_mapedit_mode() == 'edit_nodes':
            self.map_object.decorate()
        return

    def undo(self):
        self.map_object.scene().clearSelection()
        self.map_object.undecorate()
        self.map_object.data0 = self.data0_copy.copy()
        self.map_object.setPath(QPainterPath(self.path_copy))
        self.update_children()
        self.map_object.setSelected(True)
        if self.map_object.scene().get_pw_mapedit_mode() == 'edit_nodes':
            self.map_object.decorate()
        return

    def update_children(self):
        self.map_object.update_arrow_heads()
        self.map_object.update_label_pos()
        self.map_object.update_hlevel_labels()
        self.map_object.update_housenumber_labels()


class RemoveNodeCmd(QUndoCommand):
    def __init__(self, map_object, index, polygons, description):
        super(RemoveNodeCmd, self).__init__(description)
        self.data0_copy = map_object.data0.copy()
        self.path_copy = QPainterPath(map_object.path())
        self.map_object = map_object
        self.path_num, self.coord_num = index
        self.data_level = self.map_object.current_data_x
        self.polygons = polygons
        self.data_level = self.map_object.current_data_x

    def redo(self):
        polygons = copy.deepcopy(self.polygons)
        polygons[self.path_num].pop(self.coord_num)
        self.map_object.data0.delete_node_at_position(self.data_level, self.path_num, self.coord_num)
        self.map_object.setPath(self.map_object.create_painter_path(polygons))
        self.map_object.undecorate()
        self.update_children()
        if self.map_object.scene().get_pw_mapedit_mode() == 'edit_nodes':
            self.map_object.decorate()

    def undo(self):
        self.map_object.scene().clearSelection()
        self.map_object.undecorate()
        self.map_object.data0 = self.data0_copy.copy()
        self.map_object.setPath(QPainterPath(self.path_copy))
        self.update_children()
        self.map_object.setSelected(True)
        if self.map_object.scene().get_pw_mapedit_mode() == 'edit_nodes':
            self.map_object.decorate()
        return

    def update_children(self):
        self.map_object.update_arrow_heads()
        self.map_object.update_label_pos()
        self.map_object.update_hlevel_labels()
        self.map_object.update_housenumber_labels()

class ReversePolylineCmd(QUndoCommand):
    def __init__(self, map_object, description):
        super(ReversePolylineCmd, self).__init__(description)
        self.data0_copy = map_object.data0.copy()
        self.path_copy = map_object.path()
        self.map_object = map_object
        self.data_level = map_object.current_data_x

    def redo(self):
        self.map_object.data0.reverse_poly(self.data_level)
        polygons = self.map_object.data0.get_polys_for_data_level(self.data_level)
        self.map_object.setPath(self.map_object.create_painter_path(polygons))
        self.update_children()
        return

    def undo(self):
        self.map_object.data0 = self.data0_copy
        self.map_object.setPath(self.path_copy)
        self.update_children()
        return

    def update_children(self):
        self.map_object.update_arrow_heads()
        self.map_object.update_label_pos()
        self.map_object.update_hlevel_labels()
        self.map_object.update_housenumber_labels()


class MoveGripCmd(QUndoCommand):
    command_id = 1
    def __init__(self, map_object, grip, description,):
        super(MoveGripCmd, self).__init__(description)
        self.index = grip.grip_indexes
        self.pos = grip.pos()
        self.data0_copy = map_object.data0.copy()
        self.path_copy = map_object.path()
        self.map_object = map_object
        self.data_level = map_object.current_data_x
        self.cmd_time = time.time()

    def id(self):
        return self.command_id

    def redo(self):
        polygons = self.map_object.get_polygons_from_path(self.map_object.path())
        grip_poly_num, grip_coord_num = self.index
        polygons[grip_poly_num][grip_coord_num] = self.pos
        self.map_object.setPath(self.map_object.create_painter_path(polygons))
        self.map_object.data0.update_node_coordinates(self.data_level, grip_poly_num, grip_coord_num, self.pos)
        self.update_children()

    def undo(self):
        self.map_object.scene().clearSelection()
        self.map_object.undecorate()
        self.map_object.data0 = self.data0_copy
        self.map_object.setPath(self.path_copy)
        self.update_children()
        self.map_object.setSelected(True)
        if self.map_object.scene().get_pw_mapedit_mode() == 'edit_nodes':
            self.map_object.decorate()
        return

    def update_children(self):
        self.map_object.update_arrow_heads()
        self.map_object.update_label_pos()
        self.map_object.update_hlevel_labels()
        self.map_object.update_housenumber_labels()
        self.map_object.update_interpolated_housenumber_labels()

    def mergeWith(self, other):
        if other.id() != self.id():
            return False
        if other.cmd_time - self.cmd_time > 1:
            return False
        self.pos = other.pos
        return True


class SelectModeMoveItem(QUndoCommand):
    def __init__(self, map_object, description, pos):
        super(SelectModeMoveItem, self).__init__(description)
        self.pos = pos
        self.data0_copy = map_object.data0.copy()
        self.path_copy = map_object.path()
        self.map_object = map_object
        self.data_level = map_object.current_data_x
        self.polygons = self.map_object.get_polygons_from_path(self.map_object.mapToScene(self.map_object.path()))

    def redo(self):
        for polygon_num, polygon in enumerate(self.polygons):
            for coord_num, pos in enumerate(polygon):
                self.map_object.data0.update_node_coordinates(self.data_level, polygon_num, coord_num, pos)
        self.map_object.setPath(self.map_object.create_painter_path(self.polygons))
        self.map_object.setPos(0, 0)
        self.update_children()

    def undo(self):
        self.map_object.scene().clearSelection()
        self.map_object.undecorate()
        self.map_object.data0 = self.data0_copy
        self.map_object.setPath(self.path_copy)
        self.update_children()
        self.map_object.setSelected(True)
        if self.map_object.scene().get_pw_mapedit_mode() == 'edit_nodes':
            self.map_object.decorate()

        return

    def update_children(self):
        self.map_object.update_items_after_obj_move()

class SelectModeMovePoi(QUndoCommand):
    def __init__(self, map_object, orig_pos, description):
        super(SelectModeMovePoi, self).__init__(description)
        self.pos = map_object.pos()
        self.data0_copy = map_object.data0.copy()
        self.pos_copy = QPointF(orig_pos)
        self.map_object = map_object
        self.data_level = map_object.current_data_x

    def redo(self):
        self.map_object.data0.update_node_coordinates(self.data_level, 0, 0, self.pos)
        self.map_object.setPos(self.pos)
        return

    def undo(self):
        self.map_object.data0.update_node_coordinates(self.data_level, 0, 0, self.pos_copy)
        self.map_object.setPos(self.pos_copy)
        if self.map_object.scene().get_pw_mapedit_mode() == 'select_objects':
            self.map_object.setSelected(True)


class SelectModeSetDirindicator(QUndoCommand):
    def __init__(self, map_object, dirindicator, description):
        super(SelectModeSetDirindicator, self).__init__(description)
        self.map_object = map_object
        self.old_dirindicator = map_object.get_dirindicator()
        self.new_dirindicator = dirindicator

    def redo(self):
        self.map_object.scene().clearSelection()
        self.map_object.set_dirindicator(self.new_dirindicator)
        self.map_object.set_mp_dir_indicator(self.new_dirindicator)
        self.map_object.setSelected(True)

    def undo(self):
        self.map_object.scene().clearSelection()
        self.map_object.set_dirindicator(self.old_dirindicator)
        self.map_object.set_mp_dir_indicator(self.old_dirindicator)
        if self.map_object.scene().get_pw_mapedit_mode() == 'select_objects':
            self.map_object.setSelected(True)


class SelectModeRouteParams(QUndoCommand):
    def __init__(self, map_object, route_params):
        super(SelectModeRouteParams, self).__init__('modyfikacja RouteParams')
        self.map_object = map_object
        self.old_route_params = copy.copy(self.map_object.get_route_params())
        self.new_route_params = copy.copy(route_params)

    def redo(self):
        self.map_object.set_route_params(self.new_route_params)
        if self.map_object.scene().get_pw_mapedit_mode() == 'select_objects':
            self.map_object.scene().clearSelection()
            self.map_object.setSelected(True)

    def undo(self):
        self.map_object.set_route_params(self.old_route_params)
        if self.map_object.scene().get_pw_mapedit_mode() == 'select_objects':
            self.map_object.scene().clearSelection()
            self.map_object.setSelected(True)
        self.map_object.scene().views()[0].centerOn(self.map_object)


class SetNumbersToNode(QUndoCommand):
    def __init__(self, map_object, grip, num_definition, description):
        super(SetNumbersToNode, self).__init__(description)
        self.poly_num, self.node_num = grip.grip_indexes
        self.pos = grip.pos()
        self.poly_num, self.node_num = grip.grip_indexes
        self.map_object = map_object
        self.data_level = map_object.current_data_x
        self.new_num_definition = num_definition
        self.old_num_definition = self.map_object.data0.get_poly_node(self.data_level, self.poly_num,
                                                                      self.node_num, False).get_numbers_definition()


    def redo(self):
        self.map_object.data0.get_poly_node(self.data_level, self.poly_num, self.node_num,
                                        False).set_numbers_definition(self.new_num_definition)
        self.map_object.data0.clean_numbers_definitions(self.data_level, self.poly_num)
        self.map_object.update_housenumber_labels()
        self.map_object.update_interpolated_housenumber_labels()
        if self.map_object.scene().get_pw_mapedit_mode() == 'edit_nodes':
            self.map_object.scene().clearSelection()
            self.map_object.setSelected(True)
            # self.map_object.decorate()
            self.map_object.scene().views()[0].centerOn(self.pos)

    def undo(self):
        self.map_object.data0.get_poly_node(self.data_level, self.poly_num, self.node_num,
                                        False).set_numbers_definition(self.old_num_definition)
        self.map_object.data0.clean_numbers_definitions(self.data_level, self.poly_num)
        self.map_object.update_housenumber_labels()
        self.map_object.update_interpolated_housenumber_labels()
        if self.map_object.scene().get_pw_mapedit_mode() == 'edit_nodes':
            self.map_object.scene().clearSelection()
            self.map_object.setSelected(True)
            # self.map_object.decorate()
            self.map_object.scene().views()[0].centerOn(self.pos)


class UpdateLabel123(QUndoCommand):
    def __init__(self, map_object, label_num, new_label, description):
        super(UpdateLabel123, self).__init__(description + str(label_num))
        self.map_object = map_object
        self.new_label = new_label
        self.old_label = map_object.get_label1()
        self.label_num = label_num

    def redo(self):
        if self.label_num == 1:
            self.map_object.set_label1(self.new_label)
            self.map_object.remove_label()
            self.map_object.add_label()
        elif self.label_num == 2:
            self.map_object.set_label2(self.new_label)
        elif self.label_num == 3:
            self.map_object.set_label3(self.new_label)
        if self.map_object.scene().get_pw_mapedit_mode() == 'select_objects':
            self.map_object.scene().clearSelection()
            self.map_object.setSelected(True)

    def undo(self):
        if self.label_num == 1:
            self.map_object.set_label1(self.old_label)
            self.map_object.remove_label()
            self.map_object.add_label()
        elif self.label_num == 2:
            self.map_object.set_label2(self.old_label)
        elif self.label_num == 3:
            self.map_object.set_label3(self.old_label)

        if self.map_object.scene().get_pw_mapedit_mode() == 'select_objects':
            self.map_object.scene().clearSelection()
            self.map_object.setSelected(True)
        self.map_object.scene().views()[0].centerOn(self.map_object)


class UpdateAddressComponents(QUndoCommand):
    def __init__(self, map_object, new_value, description):
        super(UpdateAddressComponents, self).__init__('zmiana ' + description)
        self.map_object = map_object
        self.new_value = new_value
        self.address_component = description
        if self.address_component == 'StreetDesc':
            self.old_value = map_object.get_street_desc()
        elif self.address_component == 'HouseNumber':
            self.old_value = map_object.get_house_number()
        elif self.address_component == 'PhoneNumber':
            self.old_value = map_object.get_phone_number()
        else:
            self.old_value = ''

    def redo(self):
        if self.address_component == 'StreetDesc':
            self.map_object.set_street_desc(self.new_value)
        elif self.address_component == 'HouseNumber':
            self.map_object.set_house_number(self.new_value)
        elif self.address_component == 'PhoneNumber':
            self.map_object.set_phone_number(self.new_value)
        if self.map_object.scene().get_pw_mapedit_mode() == 'select_objects':
            self.map_object.scene().clearSelection()
            self.map_object.setSelected(True)

    def undo(self):
        if self.address_component == 'StreetDesc':
            self.map_object.set_street_desc(self.old_value)
        elif self.address_component == 'HouseNumber':
            self.map_object.set_house_number(self.old_value)
        elif self.address_component == 'Phone':
            self.map_object.set_phone_number(self.old_value)
        if self.map_object.scene().get_pw_mapedit_mode() == 'select_objects':
            self.map_object.scene().clearSelection()
            self.map_object.setSelected(True)
        self.map_object.scene().views()[0].centerOn(self.map_object)

