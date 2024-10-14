from PyQt5.QtWidgets import QUndoCommand, QUndoStack
import copy
import time

class InsertNodeCmd(QUndoCommand):
    def __init__(self, map_object, index, pos, description, polygons):
        super(InsertNodeCmd, self).__init__(description)
        self.data0_copy = copy.copy(map_object.data0)
        self.path_copy = map_object.path()
        self.map_object = map_object
        self.path_num, self.coord_num = index
        self.pos = pos
        self.polygons = polygons

    def redo(self):
        self.map_object.undecorate()
        self.map_object.data0.insert_node_at_position(self.map_object.current_data_x, self.path_num, self.coord_num,
                                                      self.pos.x(), self.pos.y())
        self.map_object.setPath(self.map_object.create_painter_path(self.polygons))
        self.update_children()
        self.map_object.decorate()
        return

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


class ReversePolylineCmd(QUndoCommand):
    def __init__(self, map_object, description):
        super(ReversePolylineCmd, self).__init__(description)
        self.data0_copy = copy.copy(map_object.data0)
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
        self.data0_copy = copy.copy(map_object.data0)
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
        self.data0_copy = copy.copy(map_object.data0)
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
