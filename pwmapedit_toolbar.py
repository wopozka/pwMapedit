from PyQt6.QtWidgets import QToolBar, QComboBox
from PyQt6.QtGui import QIcon, QAction, QActionGroup
import os.path
import pwmapedit_constants

class PwMapeditToolbar(QToolBar):
    maps_scales_to_select = (3000, 2000, 1500, 1000, 700, 500, 300, 200, 150, 100, 70, 50, 30, 20, 15, 10, 7, 5, 3, 2, 1.5, 1,
                   0.7, 0.5, 0.3, 0.2, 0.15, 0.1, 0.07, 0.05, 0.03, 0.02, 0.015, 0.01,)
    def __init__(self, title, parent):
        self.actions = {}
        self.icons_folder = os.path.join('icons', 'toolbar_icons')
        super().__init__(title, parent)
        self.actions['save'] = QAction('Zapisz')
        self.actions['save'].triggered.connect(self.save_map)
        self.insertAction(None, self.actions['save'])
        self.actions['open'] = QAction('Otwórz')
        self.actions['open'].triggered.connect(self.open_file)
        self.insertAction(None, self.actions['open'])
        self.addSeparator()
        self.actions['undo'] = QAction('Undo')
        self.actions['undo'].triggered.connect(self.undo)
        self.insertAction(None, self.actions['undo'])
        self.actions['redo'] = QAction('Redo')
        self.actions['redo'].triggered.connect(self.redo)
        self.insertAction(None, self.actions['redo'])
        self.addSeparator()
        self.actions['cut'] = QAction('Wytnij')

        self.insertAction(None, self.actions['cut'])
        self.actions['copy'] = QAction('Kopiuj')
        self.insertAction(None, self.actions['copy'])
        self.actions['paste'] = QAction('Wklej')
        self.insertAction(None, self.actions['paste'])
        self.addSeparator()
        self.tools_action_group = QActionGroup(self)
        self.actions[pwmapedit_constants.Tools.SELECT_OBJECTS] = QAction('Zaznacz')
        self.insertAction(None, self.actions[pwmapedit_constants.Tools.SELECT_OBJECTS])
        self.actions[pwmapedit_constants.Tools.EDIT_NODES] = QAction('Edytuj węzły')
        self.insertAction(None, self.actions[pwmapedit_constants.Tools.EDIT_NODES])
        self.addSeparator()
        self.actions[pwmapedit_constants.Tools.CREATE_POINT] = QAction('Utwórz poi')
        self.insertAction(None, self.actions[pwmapedit_constants.Tools.CREATE_POINT])
        self.actions[pwmapedit_constants.Tools.CREATE_POLYLINE] = QAction('Utwórz polyline')
        self.insertAction(None, self.actions[pwmapedit_constants.Tools.CREATE_POLYLINE])
        self.actions[pwmapedit_constants.Tools.CREATE_POLYGON] = QAction('Utwórz polygon')
        self.insertAction(None, self.actions[pwmapedit_constants.Tools.CREATE_POLYGON])
        self.addSeparator()
        self.scale_selector = self.create_scale_selector()
        self.insertWidget(None, self.scale_selector)
        self.addSeparator()
        self.actions['split_polyline'] = QAction('Podziel polyline')
        self.insertAction(None, self.actions['split_polyline'])
        self.actions['merge_polyline'] = QAction('Połącz polyline/polygon')
        self.insertAction(None, self.actions['merge_polyline'])
        self.set_actions_icons()
        self.add_tools_actions_to_group()

    def open_file(self):
        self.parent().open_file()

    def add_tools_actions_to_group(self):
        for tool in pwmapedit_constants.Tools:
            if tool in self.actions:
                self.tools_action_group.addAction(self.actions[tool])
                self.actions[tool].setCheckable(True)
                self.actions[tool].setChecked(False)
                self.actions[tool].setData(tool)
        self.tools_action_group.triggered.connect(self.tools_actions_trigered)

    def get_undo_button(self):
        return self.actions['undo']

    def get_redo_button(self):
        return self.actions['redo']

    def redo(self):
        self.parent().undo_redo_stack.redo()

    def save_map(self):
        self.parent().save_map()

    def create_scale_selector(self):
        scale_km = QComboBox()
        for km in self.maps_scales_to_select:
            if km < 1:
                scale_km.addItem(f'{1000 * km} m')
            else:
                scale_km.addItem(f'{km} km')
        return scale_km

    def set_actions_icons(self):
        self.actions['save'].setIcon(QIcon(os.path.join(self.icons_folder, 'save_48.png')))
        self.actions['open'].setIcon(QIcon(os.path.join(self.icons_folder, 'open_48.png')))
        self.actions['redo'].setIcon(QIcon(os.path.join(self.icons_folder, 'redo_48.png')))
        self.actions['undo'].setIcon(QIcon(os.path.join(self.icons_folder, 'undo_48.png')))
        self.actions['cut'].setIcon(QIcon(os.path.join(self.icons_folder, 'cut_48.png')))
        self.actions['copy'].setIcon(QIcon(os.path.join(self.icons_folder, 'copy_48.png')))
        self.actions['paste'].setIcon(QIcon(os.path.join(self.icons_folder, 'paste_48.png')))
        self.actions[pwmapedit_constants.Tools.SELECT_OBJECTS].setIcon(QIcon(os.path.join(self.icons_folder,
                                                                                          'select_48.png')))
        self.actions[pwmapedit_constants.Tools.EDIT_NODES].setIcon(QIcon(os.path.join(self.icons_folder,
                                                                                      'nodes_48.png')))
        self.actions[pwmapedit_constants.Tools.CREATE_POINT].setIcon(QIcon(os.path.join(self.icons_folder,
                                                                                        'create_poi_48.png')))
        self.actions[pwmapedit_constants.Tools.CREATE_POLYLINE].setIcon(QIcon(os.path.join(self.icons_folder,
                                                                                           'create_polyline_48.png')))
        self.actions[pwmapedit_constants.Tools.CREATE_POLYGON].setIcon(QIcon(os.path.join(self.icons_folder,
                                                                                          'create_polygon_48.png')))

    def set_tool(self, tool):
        if tool in self.actions:
            self.actions[tool].setChecked(True)

    def set_undo_reto_tooltips(self):
        self.actions['undo'].setTooltip(self.parent().undo_redo_stack.undoText())
        self.actions['redo'].setTooltip(self.parent().undo_redo_stack.redoText())

    def tools_actions_trigered(self, action_button):
        self.parent().toolbar_action_trigered(action_button.data())

    def undo(self):
        self.parent().undo_redo_stack.undo()
