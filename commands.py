from PyQt5.QtWidgets import QUndoCommand, QUndoStack
import copy

class InsertNodeCmd(QUndoCommand):
    def __init__(self, map_object, index, pos, description, polygons, type_polygon=None):
        super(InsertNodeCmd, self).__init__(description)
        self.data0_copy = copy.copy(map_object.data0)
        self.path_copy = map_object.path()
        self.map_object = map_object
        self.path_num, self.coord_num = index
        self.pos = pos
        self.polygons = polygons
        self.type_polygon = type_polygon

    def redo(self):
        self.map_object.data0.insert_node_at_position(self.map_object.current_data_x, self.path_num, self.coord_num,
                                                      self.pos.x(), self.pos.y())
        self.map_object.setPath(self.map_object.create_painter_path(self.polygons, type_polygon=self.type_polygon))
        self.update_children()
        return

    def undo(self):
        self.map_object.scene().clearSelection()
        self.map_object.undecorate()
        self.map_object.data0 = self.data0_copy
        self.map_object.setPath(self.path_copy)
        self.update_children()
        self.map_object.setSelected(True)
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
        self.map_object.setPath(self.map_object.create_painter_path(polygons, type_polygon=False))
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

