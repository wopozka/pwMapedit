"""Rdzen (pwm_core) musi dzialac bez PyQt6 - to warunek, zeby dane dalo sie testowac bez GUI."""
import os.path
import pkgutil
import subprocess
import sys

import pwm_core
from pwm_core.geometry import Point, Line

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# PyQt6 jest zablokowane: jego import w ktorymkolwiek module rdzenia konczy sie bledem
CHECK_SCRIPT = '''
import importlib, sys
class BlockQt:
    def find_spec(self, name, path=None, target=None):
        if name == 'PyQt6' or name.startswith('PyQt6.'):
            raise ImportError('pwm_core nie moze importowac ' + name)
        return None
sys.meta_path.insert(0, BlockQt())
for name in sys.argv[1:]:
    importlib.import_module(name)
'''


def core_modules():
    return ['pwm_core'] + [f'pwm_core.{m.name}' for m in pkgutil.walk_packages(pwm_core.__path__)]


def test_core_imports_without_qt():
    result = subprocess.run([sys.executable, '-c', CHECK_SCRIPT] + core_modules(), cwd=ROOT,
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_point_equality_like_qpointf():
    assert Point(1.0, 2.0) == Point(1.0, 2.0 + 1e-13)
    assert Point(1.0, 2.0) != Point(1.0, 2.001)
    assert list(Point(3, 4)) == [3.0, 4.0]
    assert Point(1, 1) + Point(2, 3) == Point(3, 4)
    assert (Point(4, 2) - Point(2, 2)) / 2 == Point(1, 0)


def test_line():
    line = Line(0, 0, 3, 4)
    assert line.length() == 5.0
    assert line.pointAt(0.5) == Point(1.5, 2.0)
    assert line.p1() == Point(0, 0) and line.p2() == Point(3, 4)
    assert Line.from_points(Point(0, 0), Point(3, 4)) == line
