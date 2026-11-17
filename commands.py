from PyQt6.QtGui import QUndoCommand
from PyQt6.QtCore import QPointF
import copy
import time
import pwmapedit_constants

class CreateNewPoiCmd(QUndoCommand):
    def __init__(self, new_poi_map_object, map_objects, scene, description, mouse_scene_pos=None):
        super(CreateNewPoiCmd, self).__init__(description)
        self.new_poi_map_object = new_poi_map_object
        self.map_objects = map_objects
        self.scene = scene
        self.mouse_scene_pos = mouse_scene_pos
        # wklejany obiekt jest umieszczany przy kursorze tylko przy pierwszym redo, kolejne (po undo) przywracaja go
        # w tym samym miejscu
        self._placed = mouse_scene_pos is None

    def redo(self):
        self.map_objects.add_map_object(self.new_poi_map_object.map_object)
        self.scene.draw_object_on_map(self.new_poi_map_object)
        if not self._placed:
            self._placed = True
            poi = self.new_poi_map_object
            cur_mouse_scene_pos = self.scene.views()[0].current_scene_mouse_coords()
            poi.map_object.set_position(poi.current_data_x, cur_mouse_scene_pos)
            poi.update_from_map_object()

    def undo(self):
        self.scene.removeItem(self.new_poi_map_object)
        self.map_objects.set_map_object_deleted(self.new_poi_map_object.map_object)


class CreateNewPolyCmd(QUndoCommand):
    def __init__(self, new_poly_map_object, map_objects, scene, description, mouse_scene_pos=None):
        super(CreateNewPolyCmd, self).__init__(description)
        self.new_poly_map_object = new_poly_map_object
        self.map_objects = map_objects
        self.scene = scene
        self.mouse_scene_pos = mouse_scene_pos
        # wklejany obiekt jest przesuwany do kursora tylko przy pierwszym redo, kolejne (po undo) przywracaja go
        # w tym samym miejscu
        self._placed = mouse_scene_pos is None

    def redo(self):
        self.map_objects.add_map_object(self.new_poly_map_object.map_object)
        self.scene.draw_object_on_map(self.new_poly_map_object)
        if not self._placed:
            self._placed = True
            poly = self.new_poly_map_object
            offset = self.scene.views()[0].current_scene_mouse_coords() - self.mouse_scene_pos
            poly.map_object.translate(poly.current_data_x, offset.x(), offset.y())
            poly.update_from_map_object()

    def undo(self):
        if self.new_poly_map_object.isSelected():
            self.new_poly_map_object.set_selected(False)
        self.scene.removeItem(self.new_poly_map_object)
        self.map_objects.set_map_object_deleted(self.new_poly_map_object.map_object)


class DeleteObjectsCmd(QUndoCommand):
    def __init__(self, map_objects_to_be_removed, map_objects, description):
        super(DeleteObjectsCmd, self).__init__(description)
        self.map_objects_to_be_removed = map_objects_to_be_removed
        self.map_objects = map_objects
        self.scene = map_objects_to_be_removed[0].scene()

    def redo(self):
        for map_obj in self.map_objects_to_be_removed:
            self.scene.removeItem(map_obj)
            map_obj.map_object.set_deleted()

    def undo(self):
        for map_obj in self.map_objects_to_be_removed:
            map_obj.map_object.set_undeleted()
            self.scene.addItem(map_obj)


class EditPolyGeometryCmd(QUndoCommand):
    """Wspolna czesc komend zmieniajacych ksztalt linii albo polygonu: redo zmienia dane obiektu (change_data),
    undo przywraca kopie danych sprzed zmiany; ksztalt na scenie jest potem odtwarzany z danych."""
    def __init__(self, item, description):
        super().__init__(description)
        self.item = item
        self.data_level = item.current_data_x
        self.data0_copy = item.map_object.data0.copy()

    def change_data(self):
        raise NotImplementedError

    def redo(self):
        self.change_data()
        self.item.update_from_map_object()

    def undo(self):
        self.item.scene().clearSelection()
        self.item.undecorate()
        self.item.map_object.data0 = self.data0_copy.copy()
        self.item.update_from_map_object()
        self.item.set_selected(True)
        if self.item.scene().get_pw_mapedit_mode() == pwmapedit_constants.Tools.EDIT_NODES:
            self.item.decorate()

    def select_after_redo(self, modes):
        if self.item.scene().get_pw_mapedit_mode() in modes:
            self.item.set_selected(True)


class InsertNodeCmd(EditPolyGeometryCmd):
    def __init__(self, item, path_num, coord_num, pos, description):
        super().__init__(item, description)
        self.path_num = path_num
        self.coord_num = coord_num
        self.pos = QPointF(pos)

    def change_data(self):
        self.item.map_object.data0.insert_node_at_position(self.data_level, self.path_num, self.coord_num,
                                                           self.pos.x(), self.pos.y())

    def redo(self):
        if self.item.isSelected():
            self.item.set_selected(False)
        super().redo()
        self.select_after_redo((pwmapedit_constants.Tools.EDIT_NODES, pwmapedit_constants.Tools.SELECT_OBJECTS))


class RemoveNodeCmd(EditPolyGeometryCmd):
    def __init__(self, item, index, description):
        super().__init__(item, description)
        self.path_num, self.coord_num = index

    def change_data(self):
        self.item.map_object.data0.delete_node_at_position(self.data_level, self.path_num, self.coord_num)

    def redo(self):
        self.item.scene().clearSelection()
        super().redo()
        self.item.set_selected(True)


class ReversePolylineCmd(EditPolyGeometryCmd):
    def change_data(self):
        self.item.map_object.data0.reverse_poly(self.data_level)

    def undo(self):
        self.item.map_object.data0 = self.data0_copy.copy()
        self.item.update_from_map_object()


class MoveGripCmd(EditPolyGeometryCmd):
    def __init__(self, item, grip, description):
        super().__init__(item, description)
        self.index = grip.grip_indexes
        self.pos = QPointF(grip.pos())
        self.cmd_time = time.time()

    def id(self):
        return self.item.map_object.get_id()

    def change_data(self):
        grip_poly_num, grip_coord_num = self.index
        self.item.map_object.data0.update_node_coordinates(self.data_level, grip_poly_num, grip_coord_num, self.pos)

    def mergeWith(self, other):
        if other.id() != self.id():
            return False
        if other.cmd_time - self.cmd_time > 1:
            return False
        self.pos = other.pos
        return True


class SelectModeMoveItem(EditPolyGeometryCmd):
    def __init__(self, item, description):
        """item zostal juz przesuniety na scenie (myszka) - jego pozycja to przesuniecie obiektu"""
        super().__init__(item, description)
        self.offset = QPointF(item.pos())

    def change_data(self):
        self.item.map_object.translate(self.data_level, self.offset.x(), self.offset.y())


class SelectModeMovePoi(QUndoCommand):
    def __init__(self, item, description):
        """item zostal juz przesuniety na scenie (myszka); undo przywraca dane obiektu sprzed przesuniecia"""
        super(SelectModeMovePoi, self).__init__(description)
        self.pos = QPointF(item.pos())
        self.data0_copy = item.map_object.data0.copy()
        self.item = item
        self.data_level = item.current_data_x

    def redo(self):
        self.item.map_object.set_position(self.data_level, self.pos)
        self.item.update_from_map_object()

    def undo(self):
        self.item.map_object.data0 = self.data0_copy.copy()
        self.item.update_from_map_object()
        if self.item.scene().get_pw_mapedit_mode() == pwmapedit_constants.Tools.SELECT_OBJECTS:
            self.item.set_selected(True)


class SelectModeSetDirindicator(QUndoCommand):
    def __init__(self, item, dirindicator, description):
        super(SelectModeSetDirindicator, self).__init__(description)
        self.item = item
        self.old_dirindicator = item.map_object.get_dirindicator()
        self.new_dirindicator = dirindicator

    def redo(self):
        self.item.scene().clearSelection()
        self.item.map_object.set_dirindicator(self.new_dirindicator)
        self.item.set_mp_dir_indicator(self.new_dirindicator)
        self.item.set_selected(True)

    def undo(self):
        self.item.scene().clearSelection()
        self.item.map_object.set_dirindicator(self.old_dirindicator)
        self.item.set_mp_dir_indicator(self.old_dirindicator)
        if self.item.scene().get_pw_mapedit_mode() == pwmapedit_constants.Tools.SELECT_OBJECTS:
            self.item.set_selected(True)


class SelectModeSetEndlevel(QUndoCommand):
    def __init__(self, item, endlevel, description):
        super(SelectModeSetEndlevel, self).__init__(description)
        self.item = item
        self.old_endlevel = item.map_object.get_endlevel()
        self.new_endlevel = endlevel

    def redo(self):
        self.item.map_object.set_endlevel(self.new_endlevel)
        self.item.set_map_level()
        if self.item.scene().get_pw_mapedit_mode() == pwmapedit_constants.Tools.SELECT_OBJECTS:
            self.item.scene().clearSelection()
            self.item.set_selected(True)

    def undo(self):
        self.item.map_object.set_endlevel(self.old_endlevel)
        self.item.set_map_level()
        if self.item.scene().get_pw_mapedit_mode() == pwmapedit_constants.Tools.SELECT_OBJECTS:
            self.item.scene().clearSelection()
            self.item.set_selected(True)


class SelectModeRouteParams(QUndoCommand):
    def __init__(self, item, route_params):
        super(SelectModeRouteParams, self).__init__('modyfikacja RouteParams')
        self.item = item
        self.old_route_params = copy.copy(self.item.map_object.get_route_params())
        self.new_route_params = copy.copy(route_params)

    def redo(self):
        self.item.map_object.set_route_params(self.new_route_params)
        if self.item.scene().get_pw_mapedit_mode() == pwmapedit_constants.Tools.SELECT_OBJECTS:
            if self.item not in self.item.scene().selectedItems():
                self.item.scene().clearSelection()
                self.item.set_selected(True)

    def undo(self):
        self.item.map_object.set_route_params(self.old_route_params)
        if self.item.scene().get_pw_mapedit_mode() == pwmapedit_constants.Tools.SELECT_OBJECTS:
            self.item.scene().clearSelection()
            self.item.set_selected(True)
        self.item.scene().views()[0].centerOn(self.item)


class SetNodeAttributeCmd(QUndoCommand):
    """Wspolna czesc komend zmieniajacych atrybut wezla linii (HLevel, numeracja adresowa). Undo przywraca kopie
    danych obiektu - zmiana atrybutu jednego wezla moze zmienic tez inne wezly."""
    def __init__(self, item, grip, new_value, description):
        super().__init__(description)
        self.item = item
        self.grip = grip
        self.poly_num, self.node_num = grip.grip_indexes
        self.pos = QPointF(grip.pos())
        self.data_level = item.current_data_x
        self.new_value = new_value
        self.data0_copy = item.map_object.data0.copy()

    def set_value(self, value):
        raise NotImplementedError

    def update_labels(self):
        raise NotImplementedError

    def redo(self):
        self.set_value(self.new_value)
        self.update_labels()
        if self.item.scene().get_pw_mapedit_mode() == pwmapedit_constants.Tools.EDIT_NODES:
            if not (self.grip in self.item.scene().items(self.pos) and self.grip.isSelected()):
                self.select_item()

    def undo(self):
        self.item.map_object.data0 = self.data0_copy.copy()
        self.update_labels()
        if self.item.scene().get_pw_mapedit_mode() == pwmapedit_constants.Tools.EDIT_NODES:
            self.select_item()

    def select_item(self):
        self.item.scene().clearSelection()
        self.item.set_selected(True)
        self.item.scene().views()[0].centerOn(self.pos)


class SetHlevelToNode(SetNodeAttributeCmd):
    def set_value(self, value):
        self.item.map_object.set_node_hlevel(self.data_level, self.poly_num, self.node_num, value)

    def update_labels(self):
        self.item.update_hlevel_labels()


class SetNumbersToNode(SetNodeAttributeCmd):
    def set_value(self, value):
        self.item.map_object.set_node_numbers(self.data_level, self.poly_num, self.node_num, value)

    def update_labels(self):
        self.item.update_housenumber_labels()
        self.item.update_interpolated_housenumber_labels()


class SplitPolylineCmd(QUndoCommand):
    def __init__(self, item, map_object1, map_object2, map_objects, description):
        super(SplitPolylineCmd, self).__init__(description)
        self.orig_map_object = item
        self.map_object1 = map_object1
        self.map_object2 = map_object2
        self.scene = item.scene()
        self.map_objects = map_objects

    def redo(self):
        self.scene.clearSelection()
        self.scene.removeItem(self.orig_map_object)
        self.scene.addItem(self.map_object1)
        if self.map_object1.map_object.get_param('DirIndicator'):
            self.map_object1.set_mp_dir_indicator(True)
        self.map_object1.add_label()
        self.map_object1.set_map_level()
        self.map_object1.set_pen()

        self.scene.addItem(self.map_object2)
        if self.map_object2.map_object.get_param('DirIndicator'):
            self.map_object2.set_mp_dir_indicator(True)
        self.map_object2.add_label()
        self.map_object2.set_map_level()
        self.map_object2.set_pen()

        self.map_objects.update_map_object(self.map_object1.map_object)
        self.map_objects.add_map_object(self.map_object2.map_object)
        if self.scene.get_pw_mapedit_mode() in (pwmapedit_constants.Tools.SELECT_OBJECTS,
                                                pwmapedit_constants.Tools.EDIT_NODES):
            self.map_object1.set_selected(True)

    def undo(self):
        self.scene.clearSelection()
        self.scene.removeItem(self.map_object1)
        self.scene.removeItem(self.map_object2)
        self.scene.addItem(self.orig_map_object)
        self.map_objects.update_map_object(self.orig_map_object.map_object)
        self.map_objects.set_map_object_deleted(self.map_object2.map_object)
        if self.scene.get_pw_mapedit_mode() in (pwmapedit_constants.Tools.SELECT_OBJECTS,
                                                pwmapedit_constants.Tools.EDIT_NODES):
            self.orig_map_object.set_selected(True)

    def update_children(self):
        self.map_object1.update_arrow_heads()
        self.map_object1.update_label_pos()
        self.map_object1.update_hlevel_labels()
        self.map_object1.update_housenumber_labels()
        self.map_object1.update_interpolated_housenumber_labels()


class MergePolylinesCmd(QUndoCommand):
    def __init__(self, source_objects, merged_object, map_objects, description):
        """
        source_objects: laczone obiekty, pierwszy ma to samo id co merged_object i zostaje przez niego zastapiony,
        pozostale sa oznaczane jako usuniete
        """
        super(MergePolylinesCmd, self).__init__(description)
        self.source_objects = source_objects
        self.merged_object = merged_object
        self.map_objects = map_objects
        self.scene = source_objects[0].scene()
        self._merged_drawn = False

    def redo(self):
        self.scene.clearSelection()
        for map_obj in self.source_objects:
            self.scene.removeItem(map_obj)
        if self._merged_drawn:
            self.scene.addItem(self.merged_object)
        else:
            # przy pierwszym redo tworzymy etykiety, strzalki itd., potem obiekt ma je juz jako dzieci
            self.scene.draw_object_on_map(self.merged_object)
            self._merged_drawn = True
        self.map_objects.update_map_object(self.merged_object.map_object)
        for map_obj in self.source_objects[1:]:
            map_obj.map_object.set_deleted()
        if self.scene.get_pw_mapedit_mode() == pwmapedit_constants.Tools.SELECT_OBJECTS:
            self.merged_object.set_selected(True)

    def undo(self):
        self.scene.clearSelection()
        self.scene.removeItem(self.merged_object)
        for map_obj in self.source_objects:
            self.scene.addItem(map_obj)
        self.map_objects.update_map_object(self.source_objects[0].map_object)
        for map_obj in self.source_objects[1:]:
            map_obj.map_object.set_undeleted()
        if self.scene.get_pw_mapedit_mode() == pwmapedit_constants.Tools.SELECT_OBJECTS:
            for map_obj in self.source_objects:
                map_obj.set_selected(True)


class UpdateComment(QUndoCommand):
    def __init__(self, item, new_comment, description):
        super(UpdateComment, self).__init__(description)
        self.item = item
        self.new_comment = new_comment.split('\n')
        self.old_comment = copy.copy(self.item.map_object.get_comment())

    def redo(self):
        self.item.map_object.set_comment(self.new_comment)
        if self.item.scene().get_pw_mapedit_mode() == pwmapedit_constants.Tools.SELECT_OBJECTS:
            if not self.item.isSelected():
                self.item.scene().clearSelection()
                self.item.set_selected(True)

    def undo(self):
        self.item.map_object.set_comment(self.old_comment)
        if self.item.scene().get_pw_mapedit_mode() == pwmapedit_constants.Tools.SELECT_OBJECTS:
            self.item.scene().clearSelection()
            self.item.set_selected(True)


class UpdateLabel123(QUndoCommand):
    def __init__(self, item, label_num, new_label, description):
        super(UpdateLabel123, self).__init__(description + str(label_num))
        self.item = item
        self.new_label = new_label
        if label_num == 1:
            self.old_label = item.map_object.get_label1()
        elif label_num == 2:
            self.old_label = item.map_object.get_label2()
        else:
            self.old_label = item.map_object.get_label3()
        self.label_num = label_num

    def redo(self):
        if self.label_num == 1:
            self.item.map_object.set_label1(self.new_label)
            self.item.remove_label()
            self.item.add_label()
        elif self.label_num == 2:
            self.item.map_object.set_label2(self.new_label)
        elif self.label_num == 3:
            self.item.map_object.set_label3(self.new_label)
        if self.item.scene().get_pw_mapedit_mode() == pwmapedit_constants.Tools.SELECT_OBJECTS:
            if self.item not in self.item.scene().selectedItems():
                self.item.scene().clearSelection()
                self.item.set_selected(True)

    def undo(self):
        if self.label_num == 1:
            self.item.map_object.set_label1(self.old_label)
            self.item.remove_label()
            self.item.add_label()
        elif self.label_num == 2:
            self.item.map_object.set_label2(self.old_label)
        elif self.label_num == 3:
            self.item.map_object.set_label3(self.old_label)

        if self.item.scene().get_pw_mapedit_mode() == pwmapedit_constants.Tools.SELECT_OBJECTS:
            self.item.scene().clearSelection()
            self.item.set_selected(True)
        self.item.scene().views()[0].centerOn(self.item)


class UpdateAddressComponents(QUndoCommand):
    def __init__(self, item, new_value, description):
        super(UpdateAddressComponents, self).__init__('zmiana ' + description)
        self.item = item
        self.new_value = new_value
        self.address_component = description
        if self.address_component == 'StreetDesc':
            self.old_value = item.map_object.get_street_desc()
        elif self.address_component == 'HouseNumber':
            self.old_value = item.map_object.get_house_number()
        elif self.address_component == 'PhoneNumber':
            self.old_value = item.map_object.get_phone_number()
        else:
            self.old_value = ''

    def redo(self):
        if self.address_component == 'StreetDesc':
            self.item.map_object.set_street_desc(self.new_value)
        elif self.address_component == 'HouseNumber':
            self.item.map_object.set_house_number(self.new_value)
        elif self.address_component == 'PhoneNumber':
            self.item.map_object.set_phone_number(self.new_value)
        if self.item.scene().get_pw_mapedit_mode() == pwmapedit_constants.Tools.SELECT_OBJECTS:
            if self.item not in self.item.scene().selectedItems():
                self.item.scene().clearSelection()
                self.item.set_selected(True)

    def undo(self):
        if self.address_component == 'StreetDesc':
            self.item.map_object.set_street_desc(self.old_value)
        elif self.address_component == 'HouseNumber':
            self.item.map_object.set_house_number(self.old_value)
        elif self.address_component == 'PhoneNumber':
            self.item.map_object.set_phone_number(self.old_value)
        if self.item.scene().get_pw_mapedit_mode() == pwmapedit_constants.Tools.SELECT_OBJECTS:
            self.item.scene().clearSelection()
            self.item.set_selected(True)
        self.item.scene().views()[0].centerOn(self.item)


class UpdateExtras(QUndoCommand):
    def __init__(self, item, new_extras, description):
        super(UpdateExtras, self).__init__(description)
        self.item = item
        self.new_extras = new_extras
        self.old_extras = [a for a in item.map_object.get_others()]

    def redo(self):
        self.item.map_object.clear_others()
        for other_item in self.new_extras:
            self.item.map_object.set_others(*other_item)
        if self.item.scene().get_pw_mapedit_mode() == pwmapedit_constants.Tools.SELECT_OBJECTS:
            if self.item not in self.item.scene().selectedItems():
                self.item.scene().clearSelection()
                self.item.set_selected(True)

    def undo(self):
        self.item.map_object.clear_others()
        for other_item in self.old_extras:
            self.item.map_object.set_others(*other_item)
        if self.item.scene().get_pw_mapedit_mode() == pwmapedit_constants.Tools.SELECT_OBJECTS:
            self.item.scene().clearSelection()
            self.item.set_selected(True)
        self.item.scene().views()[0].centerOn(self.item)


class UpdatePoiType(QUndoCommand):
    def __init__(self, item, new_type, description):
        super(UpdatePoiType, self).__init__(description)
        self.item = item
        self.new_type = new_type
        self.old_type = self.item.map_object.get_type()

    def redo(self):
        self.item.map_object.set_type(self.new_type)
        self.update_after_type_change()
        if self.item.scene().get_pw_mapedit_mode() == pwmapedit_constants.Tools.SELECT_OBJECTS:
            if self.item not in self.item.scene().selectedItems():
                self.item.scene().clearSelection()
                self.item.set_selected(True)

    def undo(self):
        self.item.map_object.set_type(self.old_type)
        self.update_after_type_change()
        if self.item.scene().get_pw_mapedit_mode() == pwmapedit_constants.Tools.SELECT_OBJECTS:
            if self.item not in self.item.scene().selectedItems():
                self.item.scene().clearSelection()
                self.item.set_selected(True)

    def update_after_type_change(self):
        self.item.set_pixmap()
        self.item.remove_label()
        self.item.add_label()


class UpdatePolyType(QUndoCommand):
    def __init__(self, item, new_type, description):
        super(UpdatePolyType, self).__init__(description)
        self.item = item
        self.new_type = new_type
        self.old_type = self.item.map_object.get_type()

    def redo(self):
        self.item.map_object.set_type(self.new_type)
        self.item.set_pen()
        if self.item.scene().get_pw_mapedit_mode() == pwmapedit_constants.Tools.SELECT_OBJECTS:
            if self.item not in self.item.scene().selectedItems():
                self.item.scene().clearSelection()
                self.item.set_selected(True)

    def undo(self):
        self.item.map_object.set_type(self.old_type)
        self.item.set_pen()
        if self.item.scene().get_pw_mapedit_mode() == pwmapedit_constants.Tools.SELECT_OBJECTS:
            if self.item not in self.item.scene().selectedItems():
                self.item.scene().clearSelection()
                self.item.set_selected(True)


class UpdatePolygonType(QUndoCommand):
    def __init__(self, item, new_type, description):
        super(UpdatePolygonType, self).__init__(description)
        self.item = item
        self.new_type = new_type
        self.old_type = self.item.map_object.get_type()

    def redo(self):
        self.item.map_object.set_type(self.new_type)
        self.update_after_type_change()
        if self.item.scene().get_pw_mapedit_mode() == pwmapedit_constants.Tools.SELECT_OBJECTS:
            if self.item not in self.item.scene().selectedItems():
                self.item.scene().clearSelection()
                self.item.set_selected(True)

    def undo(self):
        self.item.map_object.set_type(self.old_type)
        self.update_after_type_change()
        if self.item.scene().get_pw_mapedit_mode() == pwmapedit_constants.Tools.SELECT_OBJECTS:
            if self.item not in self.item.scene().selectedItems():
                self.item.scene().clearSelection()
                self.item.set_selected(True)

    def update_after_type_change(self):
        self.item.set_z_value()
        self.item.set_pen()
        self.item.set_brush()