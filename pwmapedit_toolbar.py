from PyQt5.QtWidgets import QToolBar, QAction

class PwMapeditToolbar(QToolBar):
    def __init__(self, title, parent):
        super().__init__(title, parent)
        self.save = QAction('Zapisz')
        self.create_poi = QAction('Utwórz poi')
        self.create_polyline = QAction('Utwórz polyline')
        self.create_polygone = QAction('Utwórz polygon')