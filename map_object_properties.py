import os.path
import glob
import json
from PyQt5.QtGui import QPixmap, QColor, QPen, QFont, QBrush, QPainterPath
from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtWidgets import QGraphicsPixmapItem, QGraphicsEllipseItem, QGraphicsTextItem

import map_items


class MapObjectsProperties(object):
    """here this class contains definitions of all map objects: the points, polylines and polygons"""
    def __init__(self):
        # couple if definitions
        # points definitions
        self.poi_pixmap_icons = self.read_icons('xpm')
        self.poi_png_icons = self.read_icons('png')
        self.non_pixmap_icons = self.create_nonpixmap_icons()
        self.non_pixmap_brushes = self.create_nonpixmap_brushes()
        self.question_mark_icon = self.create_question_mark_icon()
        self.poi_type_vs_name = self.create_poi_type_vs_name()

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
                                          0xe: QColor('#A4A4A4'),
                                          0x1a: QColor('gray'),
                                          0x14: Qt.black,
                                          0x16: QColor('chocolate'),
                                          0x18: Qt.blue,
                                          0x19: Qt.green,  # timezone
                                          0x1c: QColor('gray'),
                                          0x1f: Qt.blue,
                                          0x2f: Qt.blue,
                                          0x4b: Qt.red,
                                          0x10e00: QColor('#ff0000'),  # hiking trial red
                                          0x10e01: QColor('#ffff41'),  # hiking trial yellow
                                          0x10e02: QColor('#399520'),  # hiking trial green
                                          0x10e03: QColor('#3965ff'),  # hiking trial blue
                                          0x10e04: Qt.black        ,   # hiking trial czarny
                                          0x10e07: QColor('#a959a9"'), # hiking trial multicolor
                                          0x10e08: Qt.red,             # rowerowy czerwony
                                          0x10e09: QColor('#ffff41'),  # rowerowy zolty
                                          0x10e0a: QColor('#ffff41'),  # rowerowy zielony
                                          0x10e0b: QColor('#3965ff'),  # rowerowy niebieski
                                          0x10e0c: Qt.black,           # rowerowy czarny
                                          0x10e0d: QColor('#a959a9'),  # rowerowy inny
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
                                          0x10e00: 2,
                                          0x10e01: 2,
                                          0x10e02: 2,
                                          0x10e03: 2,
                                          0x10e04: 2,
                                          0x10e07: 2,
                                          0x10e08: 3,
                                          0x10e09: 3,
                                          0x10e0a: 3,
                                          0x10e0b: 3,
                                          0x10e0c: 3,
                                          0x10e0d: 3,
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
                                        0x10e00: Qt.DashLine,
                                        0x10e01: Qt.DashLine,
                                        0x10e02: Qt.DashLine,
                                        0x10e03: Qt.DashLine,
                                        0x10e04: Qt.DashLine,
                                        0x10e07: Qt.DashLine,
                                        0x10e08: Qt.DotLine,
                                        0x10e09: Qt.DotLine,
                                        0x10e0a: Qt.DotLine,
                                        0x10e0b: Qt.DotLine,
                                        0x10e0c: Qt.DotLine,
                                        0x10e0d: Qt.DotLine,
                                        0x10e11: Qt.DashLine,
                                        0x10e12: Qt.DashLine,
                                        0x10e13: Qt.DashLine,
                                        0x10e14: Qt.DashLine,
                                        0x10e15: Qt.DashLine
                                       }

        self.polyline_type_vs_name = self.create_polyline_type_vs_name()

        #polygon definitions
        self.polygon_properties_fill_colour = {0x1: QColor('#d5d5d5'),
                                               0x2: QColor('#e6e6e6'),
                                               0x3: QColor('#ac9d93'),
                                               0x4: QColor('#bdca6a'),
                                               0x5: QColor('#d5d5d5'),
                                               0x6: QColor('#ce9a00'),
                                               0x7: QColor('#ffba84'),
                                               0x8: QColor('#bdcab4'),
                                               0x9: QColor('#ffba84'),
                                               0xa: QColor('#ffcab4'),
                                               0xb: QColor('#dd858a'),
                                               0xc: QColor('#dddddd'),
                                               0xd: QColor('#ff9955'),
                                               0xe: QColor('#e7e3e7'),
                                               0x13: QColor('#bd656a'),
                                               0x14: QColor('#7bff00'),
                                               0x15: QColor('#7bff00'),
                                               0x16: Qt.green,
                                               0x17: QColor('#39ff00'),
                                               0x18: QColor('#39ca20'),
                                               0x19: QColor('#ffba84'),
                                               0x1a: QColor('#C5C5C5'),
                                               0x28: Qt.blue,
                                               0x29: Qt.blue,
                                               0x32: QColor('#3995ff'),
                                               0x3b: QColor('#3995ff'),
                                               0x3c: QColor('#3995ff'),
                                               0x3d: QColor('#3995ff'),
                                               0x3e: QColor('#3995ff'),
                                               0x3f: QColor('#3995ff'),
                                               0x40: QColor('#3995ff'),
                                               0x41: QColor('#3995ff'),
                                               0x42: QColor('#3995ff'),
                                               0x43: QColor('#3995ff'),
                                               0x44: QColor('#3995ff'),
                                               0x45: QColor('#3995ff'),
                                               0x46: QColor('#3995ff'),
                                               0x47: QColor('#3995ff'),
                                               0x48: QColor('#3995ff'),
                                               0x49: QColor('#3995ff'),
                                               0x4b: QColor('#ffffff'),
                                               0x4c: QColor('#aeecb8'),
                                               0x4d: QColor('#88ffff'),
                                               0x4e: QColor('#39ff00'),
                                               0x4f: QColor('#00CA00'),
                                               0x50: QColor('#ee0000'),
                                               0x51: QColor('#a9e6ec'),
                                               0x53: QColor('#ffffd5'),
                                               0x01101e: QColor('#3995ff'),
                                               0x01101f: QColor('#3995ff'),
                                             }

        self.polygon_properties_z_value = {0x1: 1, # Large urban area > 200K
                                           0x2: 1, # small urban area < 200K
                                           0x3: 1, # rural housing area
                                           0x4: 1, # military base
                                           0x5: 1, # parking lot
                                           0x6: 1, # parking garage
                                           0x7: 1, # airport
                                           0x8: 3, # shopping center
                                           0x9: 1, # marina
                                           0xa: 2, # university/college
                                           0xb: 2, # hospital
                                           0xc: 2, # industrial complex
                                           0xd: 2, # reservation
                                           0xe: 2, # airport runway
                                           0x13: 2, # building/man-made area
                                           0x14: 2, # national park
                                           0x15: 2, # national park
                                           0x16: 2, # national park
                                           0x17: 3, # city park
                                           0x18: 3, # golf course
                                           0x19: 3, # sport complex
                                           0x1a: 4, # cemetery
                                           0x1e: 2, # state park
                                           0x1f: 2, # state park
                                           0x20: 2, # state park
                                           0x28: 1, # sea/ocean
                                           0x29: 1, # blue-unknown
                                           0x32: 1, # sea
                                           0x3b: 1, # blue-unknown
                                           0x3c: 8, # large lake 250-600 km2
                                           0x3d: 8, # large lake 77-250 km2
                                           0x3e: 8, # medium lake 25-77 km2
                                           0x3f: 8, # medium lake 11-25 km2
                                           0x40: 8, # small lake 0.25-11 km2
                                           0x41: 8, # small lake < 0.25 km2
                                           0x42: 8, # major lake > 3.3 tkm2
                                           0x43: 8, # major lake, 1.1-3.3 tkm2
                                           0x44: 4, # large lake 0.6-1.1 tkm2
                                           0x45: 2, # blue unknown
                                           0x46: 2, # major river > 1km
                                           0x47: 2, # large river 200m-1km
                                           0x48: 3, # medium river 20-200m
                                           0x49: 4, # small river < 20 m
                                           0x4c: 5, # intermittent water
                                           0x4d: 5, # glacier
                                           0x4e: 5, # orchard/plantation
                                           0x4f: 5, # scrub
                                           0x50: 3, # forest
                                           0x51: 6, # wetland/swamp
                                           0x52: 4, # tundra
                                           0x53: 5, # sand/tidal/mud flat
                                           }

        self.polygon_type_vs_name = self.create_polygon_type_vs_name()

    @staticmethod
    def read_icons(icon_type):
        icons_defs = dict()
        if icon_type == 'xpm':
            icons_files = os.path.join('icons', '*.xpm')
        else:
            icons_files = os.path.join('icons/icons_png', '*.png')
        for icon_type_file_name in glob.glob(icons_files):
            if 'question_mark' in icon_type_file_name:
                icons_defs['question_mark'] = QPixmap(icon_type_file_name)
            else:
                if '_' in os.path.basename(icon_type_file_name):
                    icon_type, icon_file_name = os.path.basename(icon_type_file_name).split('_', 1)
                else:
                    icon_type = os.path.splitext(os.path.basename(icon_type_file_name))[0]
                icons_defs[int('0x' + icon_type, 16)] = QPixmap(icon_type_file_name)
                if icons_defs[int('0x' + icon_type, 16)].isNull():
                    print('Problem z odczytaniem pliku ikony: %s' % icon_type_file_name)
        return icons_defs

    @staticmethod
    def create_poi_type_vs_name():
        poi_type_name = dict()
        icons_files = os.path.join('icons', '*.xpm')
        for icon_type_file_name in glob.glob(icons_files):
            icon_defs = os.path.basename(icon_type_file_name).split('_')
            try:
                icon_type = int(icon_defs[0], 16)
                icon_name_en = icon_defs[1]
                icon_name_pl = icon_defs[2]
            except (ValueError, IndexError):
                continue
            poi_type_name[icon_type] = {'en': icon_name_en, 'pl': icon_name_pl}
        return poi_type_name

    def get_poi_icon(self, poi_type):
        if self.poi_type_has_pixmap_icon(poi_type):
            return self.poi_pixmap_icons[poi_type]
            # px0, py0, pheight, pwidth = qpi.boundingRect().getRect()
            # qpi.setOffset(px0 - pheight/2, py0 - pwidth)
        elif self.poi_type_has_png_icon(poi_type):
            return self.poi_png_icons[poi_type]
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
            return QBrush(Qt.red)

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

    def poi_type_has_png_icon(self, poi_type):
        return poi_type in self.poi_png_icons

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
        non_pixmaps[0x200] = False
        non_pixmaps[0x300] = QBrush(Qt.black)
        non_pixmaps[0x400] = False
        non_pixmaps[0x500] = QBrush(Qt.black)
        non_pixmaps[0x600] = QBrush(Qt.black)
        non_pixmaps[0x700] = QBrush(Qt.black)
        non_pixmaps[0x800] = False
        non_pixmaps[0x900] = False
        non_pixmaps[0xa00] = QBrush(Qt.black)
        non_pixmaps[0xb00] = QBrush(Qt.black)
        non_pixmaps[0xc00] = False
        non_pixmaps[0xd00] = QBrush(Qt.black)
        non_pixmaps[0xe00] = QBrush(Qt.black)
        non_pixmaps[0xf00] = QBrush(Qt.black)
        non_pixmaps[0x1000] = False
        non_pixmaps[0x1100] = False
        non_pixmaps[0x2800] = QBrush(Qt.black)
        return non_pixmaps

    @staticmethod
    def create_polyline_type_vs_name():
        with open(os.path.join('icons', 'line_names.json'), 'r') as lines_names:
            return json.load(lines_names)

    @staticmethod
    def create_polygon_type_vs_name():
        with open(os.path.join('icons', 'polygon_names.json'), 'r') as lines_names:
            return json.load(lines_names)

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
        return 'adr'




