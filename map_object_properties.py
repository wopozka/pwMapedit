import os.path
import glob
from PyQt5.QtGui import QPixmap, QColor, QPen, QFont, QBrush, QPainterPath
from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtWidgets import QGraphicsPixmapItem, QGraphicsEllipseItem, QGraphicsTextItem


class MapObjectsProperties(object):
    """here this class contains definitions of all map objects: the points, polylines and polygons"""
    def __init__(self):
        # couple if definitions
        # points definitions
        self.poi_pixmap_icons = self.read_icons()
        self.non_pixmap_icons = self.create_nonpixmap_icons()
        self.non_pixmap_brushes = self.create_nonpixmap_brushes()
        self.question_mark_icon = self.create_question_mark_icon()

        # polylines definitions
        #dictionary where key is Type
        self.polyline_properties_colour = {0: Qt.black,
                                          0x1: QColor('#0000ff'),
                                          0x2: QColor('#ff0000'),
                                          0x3: QColor('#bd3020'),
                                          0x4: QColor('#ff9500'),
                                          0x5: QColor('#ffff8b'),
                                          0x6: QColor('gray'),
                                          0x7: QColor('lightgrey'),
                                          0x8: QColor('orange'),
                                          0x9: Qt.blue,
                                          0xa: QColor('lightgrey'),
                                          0xc: QColor('darkorange'),
                                          0xd: QColor('brown'),
                                          0x1a: QColor('gray'),
                                          0x14: Qt.black,
                                          0x16: QColor('chocolate'),
                                          0x18: Qt.blue,
                                          0x19: Qt.green,  # timezone
                                          0x1c: QColor('gray'),
                                          0x1f: Qt.blue,
                                          0x4b: Qt.red,
                                          0x10e11: QColor('cyan'),
                                          0x10e12: QColor('cyan'),
                                          0x10e13: QColor('darkred'),
                                          0x10e14: Qt.black,
                                          0x10e15: QColor('#a4a4a4')
                                         }

        self.polyline_properties_width = {0x1: 5,
                                          0x2: 5,
                                          0x3: 4,
                                          0x4: 3,
                                          0x5: 3,
                                          0x6: 3,
                                          0x7: 3,
                                          0x8: 2,
                                          0x9: 2,
                                          0xa: 2,
                                          0xc: 2,
                                          0xd: 2,
                                          0x14: 3,
                                          0x15: 2,
                                          0x1f: 3,
                                          0x10e11: 2,
                                          0x10e12: 3,
                                          0x10e13: 3,
                                          0x10e14: 5,
                                          0x10e15: 5
                                        }

        self.polyline_properties_dash = {0xa: Qt.DotLine,
                                        0xd: Qt.DotLine,
                                        0x14: Qt.DashLine,
                                        0x1c: Qt.DashDotLine,
                                        0x18: Qt.DashLine,
                                        0x4b: Qt.DashLine,
                                        0x10e11: Qt.DashLine,
                                        0x10e12: Qt.DashLine,
                                        0x10e13: Qt.DashLine,
                                        0x10e14: Qt.DashLine,
                                        0x10e15: Qt.DashLine
                                       }

        #polygon definitions
        self.polygon_properties_fill_colour = {0x4: QColor('olive'),
                                               0x5: QColor('silver'),
                                               0x13: QColor('brown'),
                                               0x14: Qt.green,
                                               0x15: Qt.green,
                                               0x16: Qt.green,
                                               0x17: Qt.green,
                                               0x19: QColor('mistyrose'),
                                               0x1a: QColor('gray'),
                                               0x28: Qt.blue,
                                               0x29: Qt.blue,
                                               0x32: Qt.blue,
                                               0x3b: Qt.blue,
                                               0x3c: Qt.blue,
                                               0x3d: Qt.blue,
                                               0x3e: Qt.blue,
                                               0x3f: Qt.blue,
                                               0x40: Qt.blue,
                                               0x41: Qt.blue,
                                               0x42: Qt.blue,
                                               0x43: Qt.blue,
                                               0x44: Qt.blue,
                                               0x45: Qt.blue,
                                               0x46: Qt.blue,
                                               0x47: Qt.blue,
                                               0x48: Qt.blue,
                                               0x49: Qt.blue,
                                               0x4e: QColor('limegreen'),
                                               0x4f: QColor('yellowgreen')
                                             }

        self.polygon_properties_z_value = {0x4: 5,
                                           0x5: 5,
                                           0x13: 5,
                                           0x14: 4,
                                           0x15: 4,
                                           0x16: 4,
                                           0x17: 4,
                                           0x19: 5,
                                           0x1a: 5,
                                           0x28: 1,
                                           0x29: 1,
                                           0x32: 1,
                                           0x3b: 1,
                                           0x3c: 1,  # large lake
                                           0x3d: 5,  # large lake
                                           0x3e: 5,  # medium lake
                                           0x3f: 5,  # medium lake
                                           0x40: 5,  # small lake
                                           0x41: 5,  # small lake
                                           0x42: 5,  # major lake
                                           0x43: 5,  # major lake,
                                           0x44: 5,  # large lake
                                           0x45: 5,  # blue unknown
                                           0x46: 5,  # major river
                                           0x47: 5,  # large river
                                           0x48: 5,  # medium river
                                           0x49: 5,  # small river
                                           0x4e: 5,  # orchard/plantation
                                           0x4f: 5,  # scrub
                                           }

    @staticmethod
    def read_icons():
        icons_defs = dict()
        icons_files = os.path.join('icons', '*.xpm')
        for icon_type_file_name in glob.glob(icons_files):
            if 'question_mark' in icon_type_file_name:
                icons_defs['question_mark'] = QPixmap(icon_type_file_name)
            else:
                icon_type, icon_file_name = os.path.basename(icon_type_file_name).split('_', 1)
                icons_defs[int('0x' + icon_type, 16)] = QPixmap(icon_type_file_name)
                if icons_defs[int('0x' + icon_type, 16)].isNull():
                    print('Problem z odczytaniem pliku ikony: %s' % icon_type_file_name)
        return icons_defs

    def get_poi_icon(self, poi_type):
        if self.poi_type_has_pixmap_icon(poi_type):
            return self.poi_pixmap_icons[poi_type]
            # px0, py0, pheight, pwidth = qpi.boundingRect().getRect()
            # qpi.setOffset(px0 - pheight/2, py0 - pwidth)
        elif self.poi_type_has_nonpixmap_icon(poi_type):
            return self.non_pixmap_icons[poi_type]()
        else:
            return self.create_question_mark_icon()

    def get_poi_pixmap(self, poi_type):
        if self.poi_type_has_pixmap_icon(poi_type):
            return self.poi_pixmap_icons[poi_type]
        return self.poi_pixmap_icons['question_mark']

    def get_nonpixmap_poi_brush(self, poi_type):
        if poi_type in self.non_pixmap_brushes:
            return self.non_pixmap_brushes[poi_type]
        else:
            return False

    def get_polyline_colour(self, poly_type):
        if poly_type in self.polyline_properties_colour:
            return self.polyline_properties_colour[poly_type]
        return Qt.black

    def get_polyline_width(self, poly_type):
        pline_width_multiplicity = 1
        if poly_type in self.polyline_properties_width:
            return self.polyline_properties_width[poly_type] * pline_width_multiplicity
        return pline_width_multiplicity

    def get_polyline_dash(self, poly_type):
        if poly_type in self.polyline_properties_dash:
            return self.polyline_properties_dash[poly_type]
        return Qt.SolidLine

    def get_polygon_fill_colour(self, poly_type):
        if poly_type in self.polygon_properties_fill_colour:
            return self.polygon_properties_fill_colour[poly_type]
        return QColor('gainsboro')

    def get_polygon_qpen(self, poly_type):
        pen = QPen()
        pen.setBrush(self.get_polygon_fill_colour(poly_type))
        return pen

    def get_polygon_z_value(self, poly_type):
        if poly_type in self.polygon_properties_z_value:
            return self.polygon_properties_z_value[poly_type]
        return 0

    def get_polyline_qpen(self, poly_type):
        pen = QPen()
        pen.setWidth(self.get_polyline_width(poly_type))
        pen.setBrush(self.get_polyline_colour(poly_type))
        pen.setStyle(self.get_polyline_dash(poly_type))
        pen.setCosmetic(True)
        return pen

    def poi_type_has_pixmap_icon(self, poi_type):
        return poi_type in self.poi_pixmap_icons

    def poi_type_has_nonpixmap_icon(self, poi_type):
        return poi_type in self.non_pixmap_icons

    def create_nonpixmap_icons(self):
        non_pixmaps = {}
        non_pixmaps[0x100] = self.create_0x100_icon
        non_pixmaps[0x200] = self.create_0x200_icon
        non_pixmaps[0x300] = self.create_0x300_icon
        non_pixmaps[0x400] = self.create_0x400_icon
        non_pixmaps[0x500] = self.create_0x500_icon
        non_pixmaps[0x600] = self.create_0x600_icon
        non_pixmaps[0x700] = self.create_0x700_icon
        non_pixmaps[0x800] = self.create_0x800_icon
        non_pixmaps[0x900] = self.create_0x900_icon
        non_pixmaps[0xa00] = self.create_0xa00_icon
        non_pixmaps[0xb00] = self.create_0xb00_icon
        non_pixmaps[0xc00] = self.create_0xc00_icon
        non_pixmaps[0xd00] = self.create_0xd00_icon
        non_pixmaps[0xe00] = self.create_0xe00_icon
        non_pixmaps[0xf00] = self.create_0xf00_icon
        non_pixmaps[0x1000] = self.create_0x1000_icon
        non_pixmaps[0x1100] = self.create_0x1100_icon
        non_pixmaps[0x2800] = self.create_2800_icon
        return non_pixmaps

    def create_nonpixmap_brushes(self):
        non_pixmaps = {}
        non_pixmaps[0x100] = QBrush(Qt.black)
        # non_pixmaps[0x200] = QBrush(Qt.black)
        non_pixmaps[0x300] = QBrush(Qt.black)
        # non_pixmaps[0x400] = self.create_0x400_icon
        non_pixmaps[0x500] = QBrush(Qt.black)
        non_pixmaps[0x600] = QBrush(Qt.black)
        non_pixmaps[0x700] = self.create_0x700_icon
        # non_pixmaps[0x800] = self.create_0x800_icon
        # non_pixmaps[0x900] = self.create_0x900_icon
        non_pixmaps[0xa00] = QBrush(Qt.black)
        non_pixmaps[0xb00] = QBrush(Qt.black)
        # non_pixmaps[0xc00] = self.create_0xc00_icon
        non_pixmaps[0xd00] = QBrush(Qt.black)
        non_pixmaps[0xe00] = QBrush(Qt.black)
        non_pixmaps[0xf00] = QBrush(Qt.black)
        # non_pixmaps[0x1000] = self.create_0x1000_icon
        # non_pixmaps[0x1100] = self.create_0x1100_icon
        non_pixmaps[0x2800] = QBrush(Qt.black)
        return non_pixmaps

    @staticmethod
    def create_question_mark_icon():
        qm_font = QFont()
        qm_font.setBold(True)
        qm = QPainterPath()
        qm.addText(0, 0, qm_font, '?')
        return qm

    @staticmethod
    def create_0x100_icon():
        ellipse = QPainterPath()
        ellipse.addEllipse(QPointF(0, 0), 5, 5)
        # ellipse.setBrush(QBrush(Qt.black))
        return ellipse

    @staticmethod
    def create_0x200_icon():
        ellipse = QPainterPath()
        ellipse.addEllipse(QPointF(0, 0), 5, 5)
        # ellipse.setBrush(QBrush(Qt.black))
        return ellipse

    @staticmethod
    def create_0x300_icon():
        ellipse = QPainterPath()
        ellipse.addEllipse(QPointF(0, 0), 4, 4)
        # ellipse.setBrush(QBrush(Qt.black))
        return ellipse

    @staticmethod
    def create_0x400_icon():
        ellipse = QPainterPath()
        ellipse.addEllipse(QPointF(0, 0), 4, 4)
        # ellipse.setBrush(QBrush(Qt.black))
        return ellipse

    @staticmethod
    def create_0x500_icon():
        ellipse = QPainterPath()
        ellipse.addEllipse(QPointF(0, 0), 3, 3)
        # ellipse.setBrush(QBrush(Qt.black))
        return ellipse

    @staticmethod
    def create_0x600_icon():
        ellipse = QPainterPath()
        ellipse.addEllipse(QPointF(0, 0), 3, 3)
        # ellipse.setBrush(QBrush(Qt.black))
        return ellipse

    @staticmethod
    def create_0x700_icon():
        ellipse = QPainterPath()
        ellipse.addEllipse(QPointF(0, 0), 3, 3)
        # ellipse.setBrush(QBrush(Qt.black))
        return ellipse

    @staticmethod
    def create_0x800_icon():
        ellipse = QPainterPath()
        ellipse.addEllipse(QPointF(0, 0), 3, 3)
        # ellipse.setBrush(QBrush(Qt.black))
        return ellipse

    @staticmethod
    def create_0x900_icon():
        ellipse = QPainterPath()
        ellipse.addEllipse(QPointF(0, 0), 3, 3)
        # ellipse.setBrush(QBrush(Qt.black))
        return ellipse

    @staticmethod
    def create_0xa00_icon():
        ellipse = QPainterPath()
        ellipse.addEllipse(QPointF(0, 0), 2, 2)
        # ellipse.setBrush(QBrush(Qt.black))
        return ellipse

    @staticmethod
    def create_0xb00_icon():
        ellipse = QPainterPath()
        ellipse.addEllipse(QPointF(0, 0), 2, 2)
        # ellipse.setBrush(QBrush(Qt.black))
        return ellipse

    @staticmethod
    def create_0xc00_icon():
        ellipse = QPainterPath()
        ellipse.addEllipse(QPointF(0, 0), 2, 2)
        # ellipse.setBrush(QBrush(Qt.black))
        return ellipse

    @staticmethod
    def create_0xd00_icon():
        ellipse = QPainterPath()
        ellipse.addEllipse(QPointF(0, 0), 1, 1)
        # ellipse.setBrush(QBrush(Qt.black))
        return ellipse

    @staticmethod
    def create_0xe00_icon():
        ellipse = QPainterPath()
        ellipse.addEllipse(QPointF(0, 0), 1, 1)
        # ellipse.setBrush(QBrush(Qt.black))
        return ellipse

    @staticmethod
    def create_0xf00_icon():
        ellipse = QPainterPath()
        ellipse.addEllipse(QPointF(0, 0), 1, 1)
        # ellipse.setBrush(QBrush(Qt.black))
        return ellipse

    @staticmethod
    def create_0x1000_icon():
        ellipse = QPainterPath()
        ellipse.addEllipse(QPointF(0, 0), 1, 1)
        # ellipse.setBrush(QBrush(Qt.black))
        return ellipse

    @staticmethod
    def create_0x1100_icon():
        ellipse = QPainterPath()
        ellipse.addEllipse(QPointF(0, 0), 1, 1)
        # ellipse.setBrush(QBrush(Qt.black))
        return ellipse


    @staticmethod
    def create_2800_icon():
        ellipse = QPainterPath()
        ellipse.addEllipse(QPointF(0, 0), 2, 2)
        # ellipse.setBrush(QBrush(Qt.black))
        return ellipse




