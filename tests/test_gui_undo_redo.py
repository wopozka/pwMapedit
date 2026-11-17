"""Undo/redo tworzenia i wklejania obiektow w oknie programu (offscreen): obiekt po redo ma wrocic do zapisu mapy,
w tym samym miejscu co po pierwszym wykonaniu."""
import os
import shutil

import pytest

pytest.importorskip('PyQt6')
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PyQt6.QtCore import QPointF
from PyQt6.QtWidgets import QApplication

import map_items
import pwMapEdit
import pwmapedit_constants
from pwm_core import mp_file

TESTS_DIR = os.path.dirname(__file__)


@pytest.fixture
def window(tmp_path):
    app = QApplication.instance() or QApplication([])
    map_file = shutil.copy(os.path.join(TESTS_DIR, 'wynik.mp'), tmp_path / 'wynik.mp')
    w = pwMapEdit.pwMapeditPy(None, '')
    opener = pwMapEdit.MapFileOpener(w, str(map_file), w.map_objects_properties, w.projection, w.undo_redo_stack)
    opener.draw_poi_polyline_polygon.connect(w.draw_poi_polyline_polygon)
    opener.wczytaj_rekordy()
    app.processEvents()
    w.toolbar_action_trigered(pwmapedit_constants.Tools.SELECT_OBJECTS)
    yield w
    w.undo_redo_stack.clear()
    w.close()


def saved_map(window, path):
    mp_file.write_mp_file(window.map_objects, str(path))
    with open(path, encoding=mp_file.MP_ENCODING) as f:
        return f.read()


def undo_all_redo_all(window):
    stack = window.undo_redo_stack
    while stack.canUndo():
        stack.undo()
    while stack.canRedo():
        stack.redo()


def test_created_poi_survives_undo_redo(window, tmp_path):
    poi_type = 'Type=0x2f01'
    map_items.PoiAsPixmap.last_used_type = 0x2f01
    window.map_canvas.command_create_poi(window.map_canvas.sceneRect().center())
    assert saved_map(window, tmp_path / 'a.mp').count(poi_type) == 1
    window.undo_redo_stack.undo()
    assert poi_type not in saved_map(window, tmp_path / 'b.mp')
    window.undo_redo_stack.redo()
    assert saved_map(window, tmp_path / 'c.mp').count(poi_type) == 1


def test_pasted_polyline_keeps_position_after_undo_redo(window, tmp_path):
    scene = window.map_canvas
    line = next(i for i in scene.items() if isinstance(i, map_items.PolylineQGraphicsPathItem))
    original_data0 = [r for r in line.map_object.to_mp_record() if r.startswith('Data0=')]
    scene.clearSelection()
    line._mouse_release_scene_pos = line.boundingRect().center()
    line.set_selected(True)
    mime = scene.copy()
    window.view.current_scene_mouse_coords = lambda: line.boundingRect().center() + QPointF(40, 25)
    scene.paste(mime)
    after_paste = saved_map(window, tmp_path / 'a.mp')
    data0_lines = [r for r in after_paste.splitlines() if r.startswith('Data0=')]
    # oryginal i przesunieta kopia
    assert data0_lines.count(original_data0[0]) == 1
    assert len(data0_lines) == len(set(data0_lines))
    # kursor w czasie redo jest gdzie indziej - kopia ma wrocic tam, gdzie zostala wklejona
    window.view.current_scene_mouse_coords = lambda: QPointF(0, 0)
    undo_all_redo_all(window)
    assert saved_map(window, tmp_path / 'b.mp') == after_paste
