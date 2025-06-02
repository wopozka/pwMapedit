from PyQt5.QtWidgets import QToolBar, QAction, QActionGroup
from PyQt5.QtGui import QIcon
import os.path
import pwmapedit_constants

class PwMapeditToolbar(QToolBar):
    def __init__(self, title, parent):
        self.actions = {}
        self.icons_folder = os.path.join('icons', 'toolbar_icons')
        super().__init__(title, parent)
        self.actions['save'] = QAction('Zapisz')
        save_icon = QIcon(os.path.join(self.icons_folder, 'save_48.png'))
        self.actions['save'].setIcon(save_icon)
        self.insertAction(None, self.actions['save'])
        self.actions['open'] = QAction('Otwórz')
        self.actions['open'].setIcon(QIcon(os.path.join(self.icons_folder, 'open_48.png')))
        self.insertAction(None, self.actions['open'])
        self.addSeparator()
        self.actions['redo'] = QAction('Redo')
        redo_icon = QIcon(os.path.join(self.icons_folder, 'redo_48.png'))
        self.actions['redo'].setIcon(redo_icon)
        self.insertAction(None, self.actions['redo'])
        self.actions['undo'] = QAction('Undo')
        undo_icon = QIcon(os.path.join(self.icons_folder, 'undo_48.png'))
        self.actions['undo'].setIcon(undo_icon)
        self.insertAction(None, self.actions['undo'])
        self.addSeparator()
        self.actions['cut'] = QAction('Wytnij')
        self.actions['cut'].setIcon(QIcon(os.path.join(self.icons_folder, 'cut_48.png')))
        self.insertAction(None, self.actions['cut'])
        self.actions['copy'] = QAction('Kopiuj')
        self.actions['copy'].setIcon(QIcon(os.path.join(self.icons_folder, 'copy_48.png')))
        self.insertAction(None, self.actions['copy'])
        self.actions['paste'] = QAction('Wklej')
        self.actions['paste'].setIcon(QIcon(os.path.join(self.icons_folder, 'paste_48.png')))
        self.insertAction(None, self.actions['paste'])
        self.addSeparator()
        self.tools_action_group = QActionGroup(self)
        self.actions[pwmapedit_constants.Tools.SELECT_OBJECTS] = QAction('Zaznacz')
        self.actions[pwmapedit_constants.Tools.SELECT_OBJECTS].setIcon(QIcon(os.path.join(self.icons_folder,
                                                                                          'select_48.png')))
        self.insertAction(None, self.actions[pwmapedit_constants.Tools.SELECT_OBJECTS])
        self.actions[pwmapedit_constants.Tools.EDIT_NODES] = QAction('Edytuj węzły')
        self.actions[pwmapedit_constants.Tools.EDIT_NODES].setIcon(QIcon(os.path.join(self.icons_folder,
                                                                                      'nodes_48.png')))
        self.insertAction(None, self.actions[pwmapedit_constants.Tools.EDIT_NODES])
        self.addSeparator()
        self.actions[pwmapedit_constants.Tools.CREATE_POINT] = QAction('Utwórz poi')
        self.actions[pwmapedit_constants.Tools.CREATE_POINT].setIcon(QIcon(os.path.join(self.icons_folder,
                                                                                        'create_poi_48.png')))
        self.insertAction(None, self.actions[pwmapedit_constants.Tools.CREATE_POINT])
        self.actions[pwmapedit_constants.Tools.CREATE_POLYLINE] = QAction('Utwórz polyline')
        self.actions[pwmapedit_constants.Tools.CREATE_POLYLINE].setIcon(QIcon(os.path.join(self.icons_folder,
                                                                                           'create_polyline_48.png')))
        self.insertAction(None, self.actions[pwmapedit_constants.Tools.CREATE_POLYLINE])
        self.actions[pwmapedit_constants.Tools.CREATE_POLYGON] = QAction('Utwórz polygon')
        self.actions[pwmapedit_constants.Tools.CREATE_POLYGON].setIcon(QIcon(os.path.join(self.icons_folder,
                                                                                          'create_polygon_48.png')))
        self.insertAction(None, self.actions[pwmapedit_constants.Tools.CREATE_POLYGON])
        self.add_tools_actions_to_group()

    def add_tools_actions_to_group(self):
        for tool in pwmapedit_constants.Tools:
            if tool in self.actions:
                self.tools_action_group.addAction(self.actions[tool])
                self.actions[tool].setCheckable(True)
                self.actions[tool].setChecked(False)