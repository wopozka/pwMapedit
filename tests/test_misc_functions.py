import pytest
import sys
import os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))
import misc_functions
from PyQt5.QtGui import QPainterPath, QPolygonF
from PyQt5.QtCore import QPointF, QLineF


TEST_RETURN_ICON_DEFINITION = ((['Type=0x15', 'SubType=0x00', 'Marine=Y', 'string1=0x04,Map', 'string2=0x15,Mapa',
                                 'dayxpm="24 24 14 1",',
                                 '"       c None",',
                                 '".      c #000000",',
                                 '"+      c #FFFFFF",',
                                 '"@      c #999999",',
                                 '"$      c #8E99A2",',
                                 '"&      c #666666",',
                                 '"*      c #003399",',
                                 '"=      c #0047AD",',
                                 '"-      c #0066CC",',
                                 '";      c #006AD0",',
                                 '">      c #007FE5",',
                                 '",      c #0099FF",',
                                 '"\'      c #FF0000",',
                                 '")      c #0069CF",',
                                 '"                        ",',
                                 '"                        ",',
                                 '"                        ",',
                                 '"      ++++++++++++      ",',
                                 '"      +@@@@@@$$@@+      ",',
                                 '"      +&*=---;>,@+      ",',
                                 '"      +&*=---;>,@+      ",',
                                 '"      +&*\'\'\'\'\'\',@+      ",',
                                 '"      +&*\'\'\'\'\'\',@+      ",',
                                 '"      +&*=---)>,@+      ",',
                                 '"      +&*=---)>,@+      ",',
                                 '"      +&*=---)>,@+      ",',
                                 '"      +&*=---)>,@+      ",',
                                 '"      +&*=---)>,@+      ",',
                                 '"      +&*=---)>,@+      ",',
                                 '"      +&*=---->,@+      ",}'],
                                ('0x1500', '/* XPM */\n static const unsigned char * day_xpm[] = {\n"24 24 14 1",\n"       c None",\n".      c #000000",\n"+      c #FFFFFF",\n"@      c #999999",\n"$      c #8E99A2",\n"&      c #666666",\n"*      c #003399",\n"=      c #0047AD",\n"-      c #0066CC",\n";      c #006AD0",\n">      c #007FE5",\n",      c #0099FF",\n"\'      c #FF0000",\n")      c #0069CF",\n"                        ",\n"                        ",\n"                        ",\n"      ++++++++++++      ",\n"      +@@@@@@$$@@+      ",\n"      +&*=---;>,@+      ",\n"      +&*=---;>,@+      ",\n"      +&*\'\'\'\'\'\',@+      ",\n"      +&*\'\'\'\'\'\',@+      ",\n"      +&*=---)>,@+      ",\n"      +&*=---)>,@+      ",\n"      +&*=---)>,@+      ",\n"      +&*=---)>,@+      ",\n"      +&*=---)>,@+      ",\n"      +&*=---)>,@+      ",\n"      +&*=---->,@+      ",}\n')),
                               )

@pytest.mark.parametrize('target, answer', TEST_RETURN_ICON_DEFINITION)
def test_return_icon_definiton(target, answer):
    assert misc_functions.return_icon_definition(target) == answer

TEST_VECTOR_ANGLE =(
    ((1, 0, False), 0),
    ((1, 1, False), 45),
    ((0, 1, False), 90),
    ((-1, 1, False), 135),
    ((-1, 0, False), 180),
    ((-1, -1, False), 225),
    ((0, -1, False), 270),
    ((1, -1, False), 315),
    ((1, 0, True), 0),
    ((1, -1, True), 45),
    ((0, -1, True), 90),
    ((-1, -1, True), 135),
    ((-1, 0, True), 180),
    ((-1, 1, True), 225),
    ((0, 1, True), 270),
    ((1, 1, True), 315),
)

@pytest.mark.parametrize('target, answer', TEST_VECTOR_ANGLE)
def test_vector_angle(target, answer):
    assert misc_functions.vector_angle(target[0], target[1], clockwise=target[2], screen_coord_system=False) == answer

TEST_LABEL_ANGLE = (
    (0, 0),
    (45, 45),
    (90, 90),
    (135, 315),
    (180, 0),
    (225, 45),
    (270, 90),
    (315, 45)
)

@pytest.mark.parametrize('target, answer', TEST_LABEL_ANGLE)
def test_label_angle(target, answer):
    assert misc_functions.calculate_label_angle(target) == answer

TEST_DISTANCE = (
    ([(51.981570, 16.444900), (51.990910, 16.467280)], 1850),
    ([(39.152501, -84.412977), (39.152505, -84.412946)], 2.716),
)

# @pytest.mark.parametrize('target, answer', TEST_DISTANCE)
# def test_great_circle_distance(target, answer):
#     assert misc_functions.great_circle_distance(target[0], target[1]) == answer / 1000

@pytest.mark.parametrize('target, answer', TEST_DISTANCE)
def test_vincenty_distance(target, answer):
    assert misc_functions.vincenty_distance(target[0], target[1]) == answer

TEST_CLOSEST_POINT_TO_POLY_JOINT = (
    (QPointF(2.0, 0.0), (0, QPointF(2.0, 0.0), 1),),
    (QPointF(0.0, -2.0), (0, QPointF(0.0, -2.0), 2),),
    (QPointF(-2.0, 0.0), (0, QPointF(-2.0, 0.0), 3),),
    (QPointF(0.0, 2.0), (0, QPointF(0.0, 2.0), 4),),
    (QPointF(1.0, 0.0), (0, QPointF(1.0, 0.0), 6),),
    (QPointF(0.0, -1.0), (0, QPointF(0.0, -1.0), 7),),
    (QPointF(-1.0, 0.0), (0, QPointF(-1.0, 0.0), 8),),
    (QPointF(0.0, 1.0), (0, QPointF(0.0, 1.0), 9),),
    (QPointF(5.0, 3.0), (0, QPointF(5.0, 3.0), 11),),
    (QPointF(3.0, 2.0), (0, QPointF(3.0, 2.0), 12),),
    (QPointF(3.0, 3.0), (0, QPointF(3.0, 3.0), 13),),
    (QPointF(4.0, 4.0), (0, QPointF(4.0, 4.0), 14),),
)

@pytest.mark.parametrize('target, answer', TEST_CLOSEST_POINT_TO_POLY_JOINT)
def test_closest_point_to_poly3(target, answer):
    poly0 = QPolygonF([QPointF(1.0, 1.0), QPointF(1.0, -1.0), QPointF(-1.0, -1.0), QPointF(-1.0, 1.0)])
    poly = QPolygonF([QPointF(2.0, 2.0), QPointF(2.0, -2.0), QPointF(-2.0, -2.0), QPointF(-2.0, 2.0)])
    poly2 = QPolygonF([QPointF(5.0, 4.0), QPointF(5.0, 2.0), QPointF(3.0, 2.0), QPointF(3.0, 4.0)])
    pp0 = QPainterPath()
    pp0.addPolygon(poly0)
    pp = QPainterPath()
    pp.addPolygon(poly)
    pp = pp.subtracted(pp0)
    pp1 = QPainterPath()
    pp1.addPolygon(poly2)
    pp3 = QPainterPath()
    pp3.addPath(pp)
    pp3.addPath(pp1)
    treshold = 1
    assert misc_functions.closest_point_to_poly(target, pp3, treshold, polygon=True) == answer
