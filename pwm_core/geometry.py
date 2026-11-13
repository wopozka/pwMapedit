# -*- coding: utf-8 -*-
"""Proste typy geometryczne i funkcje wektorowe, bez zaleznosci od Qt.

Point i Line maja ten sam interfejs co uzywana dotad czesc QPointF i QLineF (x(), y(), length(), pointAt()...),
dzieki czemu kod danych nie musial sie zmieniac. Na granicy z GUI punkty zamienia sie na QPointF(*point).
"""
import math

# tak samo jak QPointF == (qFuzzyIsNull roznicy wspolrzednych)
_FUZZY = 1e-12


class Point(object):
    __slots__ = ('_x', '_y')

    def __init__(self, x=0.0, y=0.0):
        self._x = float(x)
        self._y = float(y)

    def x(self):
        return self._x

    def y(self):
        return self._y

    def setX(self, x):
        self._x = float(x)

    def setY(self, y):
        self._y = float(y)

    def __iter__(self):
        yield self._x
        yield self._y

    def __eq__(self, other):
        if not hasattr(other, 'x') or not hasattr(other, 'y'):
            return NotImplemented
        return abs(self._x - other.x()) <= _FUZZY and abs(self._y - other.y()) <= _FUZZY

    __hash__ = None

    def __add__(self, other):
        return Point(self._x + other.x(), self._y + other.y())

    def __sub__(self, other):
        return Point(self._x - other.x(), self._y - other.y())

    def __mul__(self, factor):
        return Point(self._x * factor, self._y * factor)

    def __truediv__(self, divisor):
        return Point(self._x / divisor, self._y / divisor)

    def __repr__(self):
        return f'Point({self._x!r}, {self._y!r})'


class Line(object):
    """Odcinek od p1 do p2."""
    __slots__ = ('_p1', '_p2')

    def __init__(self, x1, y1, x2, y2):
        self._p1 = Point(x1, y1)
        self._p2 = Point(x2, y2)

    @classmethod
    def from_points(cls, p1, p2):
        return cls(p1.x(), p1.y(), p2.x(), p2.y())

    def p1(self):
        return Point(self._p1.x(), self._p1.y())

    def p2(self):
        return Point(self._p2.x(), self._p2.y())

    def dx(self):
        return self._p2.x() - self._p1.x()

    def dy(self):
        return self._p2.y() - self._p1.y()

    def length(self):
        return math.hypot(self.dx(), self.dy())

    def pointAt(self, t):
        return Point(self._p1.x() + self.dx() * t, self._p1.y() + self.dy() * t)

    def __eq__(self, other):
        if not isinstance(other, Line):
            return NotImplemented
        return self._p1 == other._p1 and self._p2 == other._p2

    __hash__ = None

    def __repr__(self):
        return f'Line({self._p1.x()!r}, {self._p1.y()!r}, {self._p2.x()!r}, {self._p2.y()!r})'


def vector_angle(x, y, clockwise=False, screen_coord_system=False):
    if screen_coord_system:
        y = -y
    if x == 0:
        if clockwise:
            return 90 if y < 0 else 270
        return 90 if y > 0 else 270
    y_by_x = round(y / x, 5)
    if y_by_x == 0:
        return 0 if x > 0 else 180
    calc_degrees = math.degrees(math.atan(y_by_x))
    if x > 0:
        if clockwise:
            return -calc_degrees if y < 0 else 360 - calc_degrees
        else:
            return calc_degrees if y > 0 else 360 + calc_degrees
    return 180 - calc_degrees if clockwise else 180 + calc_degrees


def vector_length(x, y):
    return math.sqrt(x*x + y*y)


def unit_vector(x, y):
    vector_l = vector_length(x, y)
    return x/vector_l, y/vector_l


def vector_rotated(x, y, rotation_angle, clockwise=False, screen_coord_system=False):
    _vector_angle = vector_angle(x, y, clockwise=clockwise, screen_coord_system=screen_coord_system)
    _vector_length = vector_length(x, y)
    new_angle_radians = (_vector_angle + rotation_angle) / 180 * math.pi
    _new_vector = (_vector_length * math.cos(new_angle_radians), _vector_length * math.sin(new_angle_radians))
    if screen_coord_system:
        _new_vector = list(_new_vector)
        _new_vector[1] = - _new_vector[1]
    return tuple(_new_vector)


def unit_vector_rotated(x, y, rotation_angle, clockwise=False, screen_coord_system=False):
    vr = vector_rotated(x, y, rotation_angle, clockwise=clockwise, screen_coord_system=screen_coord_system)
    vector_rotated_length = vector_length(vr[0], vr[1])
    return vr[0] / vector_rotated_length, vr[1] / vector_rotated_length


def calculate_label_angle(angle):
    if 0 <= angle <= 90:
        return angle
    elif 90 < angle < 180:
        return 180 + angle
    elif angle == 180:
        return 0
    elif 180 < angle <= 270:
        return angle - 180
    else:
        return angle


def great_circle_distance(coord1, coord2):
    lat1 = math.radians(coord1[0])
    lon1 = math.radians(coord1[1])
    lat2 = math.radians(coord2[0])
    lon2 = math.radians(coord1[1])
    return 6371 * math.acos(math.sin(lat1) * math.sin(lat2) + math.cos(lat1) *
                            math.cos(lat2) * math.cos(lon1 - lon2))


def vincenty_distance(coord1, coord2):
    """
    calculates distance between two earth points
    Parameters
    ----------
    coord1: tuple(latitude, longitude)
    coord2 tuple(latitude, longitude)

    Returns: distance in meters
    -------

    """
    # https://nathanrooy.github.io/posts/2016-12-18/vincenty-formula-with-python/
    a = 6378137.0  # radius at equator in meters (WGS-84)
    f = 1 / 298.257223563  # flattening of the ellipsoid (WGS-84)
    b = (1 - f) * a
    maxIter = 200
    tol = 10**-12

    # lat=phi_?   latitude (N, S) of the points
    # lon=L_?  longitude (E, W) of points
    phi_1, L_1 = coord1
    phi_2, L_2 = coord2

    u_1 = math.atan((1 - f) * math.tan(math.radians(phi_1)))
    u_2 = math.atan((1 - f) * math.tan(math.radians(phi_2)))

    L = math.radians(L_2 - L_1)

    Lambda = L  # set initial value of lambda to L

    sin_u1 = math.sin(u_1)
    cos_u1 = math.cos(u_1)
    sin_u2 = math.sin(u_2)
    cos_u2 = math.cos(u_2)

    # --- BEGIN ITERATIONS -----------------------------+
    iters = 0
    for i in range(0, maxIter):
        iters += 1

        cos_lambda = math.cos(Lambda)
        sin_lambda = math.sin(Lambda)
        sin_sigma = math.sqrt((cos_u2 * math.sin(Lambda)) ** 2 +
                              (cos_u1 * sin_u2 - sin_u1 * cos_u2 * cos_lambda) ** 2)
        cos_sigma = sin_u1 * sin_u2 + cos_u1 * cos_u2 * cos_lambda
        sigma = math.atan2(sin_sigma, cos_sigma)
        sin_alpha = (cos_u1 * cos_u2 * sin_lambda) / sin_sigma
        cos_sq_alpha = 1 - sin_alpha ** 2
        cos2_sigma_m = cos_sigma - ((2 * sin_u1 * sin_u2) / cos_sq_alpha)
        C = (f / 16) * cos_sq_alpha * (4 + f * (4 - 3 * cos_sq_alpha))
        Lambda_prev = Lambda
        Lambda = L + (1 - C) * f * sin_alpha * (sigma + C * sin_sigma *
                                                (cos2_sigma_m + C * cos_sigma * (-1 + 2 * cos2_sigma_m ** 2)))

        # successful convergence
        diff = abs(Lambda_prev - Lambda)
        if diff <= tol:
            break

    u_sq = cos_sq_alpha * ((a ** 2 - b ** 2) / b ** 2)
    A = 1 + (u_sq / 16384) * (4096 + u_sq * (-768 + u_sq * (320 - 175 * u_sq)))
    B = (u_sq / 1024) * (256 + u_sq * (-128 + u_sq * (74 - 47 * u_sq)))
    delta_sig = B * sin_sigma * (cos2_sigma_m + 0.25 * B * (
                cos_sigma * (-1 + 2 * cos2_sigma_m ** 2) - (1 / 6) * B * cos2_sigma_m * (
                    -3 + 4 * sin_sigma ** 2) * (-3 + 4 * cos2_sigma_m ** 2)))

    m = b * A * (sigma - delta_sig)  # output distance in meters
    return m
