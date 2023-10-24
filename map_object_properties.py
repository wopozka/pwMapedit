import os.path
import glob
from PyQt5.QtGui import QPixmap, QColor
from PyQt5.QtCore import Qt

class MapObjectsProperties(object):
    """here this class contains definitions of all map objects: the points, polylines and polygones"""
    def __init__(self):
        # couple if definitions
        # points definitions
        self.poi_icons = self.read_icons()

        # polylines definitions
        #dictionary where key is Type
        self.polylinePropertiesColour = {'0x0': Qt.black,
                                         '0x1': QColor('#0000ff'),
                                         '0x2': QColor('#ff0000'),
                                         '0x3': QColor('#bd3020'),
                                         '0x4': QColor('#ff9500'),
                                         '0x5': QColor('#ffff8b'),
                                         '0x6': QColor('gray'),
                                         '0x7': QColor('lightgrey'),
                                         '0x8': QColor('orange'),
                                         '0x9': Qt.blue,
                                         '0xa': QColor('lightgrey'),
                                         '0xc': QColor('darkorange'),
                                         '0xd': QColor('brown'),
                                         '0x1a': QColor('gray'),
                                         '0x14': Qt.black,
                                         '0x16': QColor('chocolate'),
                                         '0x18': Qt.blue,
                                         '0x1c': QColor('gray'),
                                         '0x1f': Qt.blue,
                                         '0x4b': Qt.red,
                                         '0x10e11': QColor('cyan'),
                                         '0x10e12': QColor('cyan'),
                                         '0x10e13': QColor('darkred'),
                                         '0x10e14': Qt.black,
                                         '0x10e15': QColor('#a4a4a4')
                                         }

        self.polylinePropertiesWidth = {'0x1': 5,
                                        '0x2': 5,
                                        '0x3': 4,
                                        '0x4': 3,
                                        '0x5': 3,
                                        '0x6': 3,
                                        '0x7': 3,
                                        '0x8': 2,
                                        '0x9': 2,
                                        '0xa': 2,
                                        '0xc': 2,
                                        '0xd': 2,
                                        '0x14': 5,
                                        '0x1f': 3,
                                        '0x10e11': 2,
                                        '0x10e12': 3,
                                        '0x10e13': 3,
                                        '0x10e14': 5,
                                        '0x10e15': 5
                                        }

        self.polylinePropertiesDash = {'0xa': Qt.DotLine,
                                       '0xd': Qt.DotLine,
                                       '0x14': Qt.DashLine,
                                       '0x1c': Qt.DashDotLine,
                                       '0x18': Qt.DashLine,
                                       '0x4b': Qt.DashLine,
                                       '0x10e11': Qt.DashLine,
                                       '0x10e12': Qt.DashLine,
                                       '0x10e13': Qt.DashLine,
                                       '0x10e14': Qt.DashLine,
                                       '0x10e15': Qt.DashLine
                                       }

        #polygone definitions
        self.polygonePropertiesFillColour = {'0x4': QColor('olive'),
                                             '0x5': QColor('silver'),
                                             '0x13': QColor('brown'),
                                             '0x14': Qt.green, '0x15': Qt.green, '0x16': Qt.green, '0x17': Qt.green,
                                             '0x19': QColor('mistyrose'),
                                             '0x1a': QColor('gray'),
                                             '0x28': Qt.blue,
                                             '0x29': Qt.blue,
                                             '0x32': Qt.blue,
                                             '0x3b': Qt.blue,
                                             '0x3c': Qt.blue,
                                             '0x3d': Qt.blue,
                                             '0x3e': Qt.blue,
                                             '0x3f': Qt.blue,
                                             '0x40': Qt.blue,
                                             '0x41': Qt.blue,
                                             '0x42': Qt.blue,
                                             '0x43': Qt.blue,
                                             '0x44': Qt.blue,
                                             '0x45': Qt.blue,
                                             '0x46': Qt.blue,
                                             '0x47': Qt.blue,
                                             '0x48': Qt.blue,
                                             '0x49': Qt.blue,
                                             '0x4e': QColor('limegreen'),
                                             '0x4f': QColor('yellowgreen')
                                             }

    @staticmethod
    def read_icons(self):
        icons_defs = dict()
        icons_files = os.path.join('icons', '*.xpm')
        for icon_type_file_name in glob.glob(icons_files):
            icon_type, icon_file_name = icon_type_file_name.split('_', 1)
            icons_defs[icon_type] = QPixmap(icon_file_name)
        return icons_defs
