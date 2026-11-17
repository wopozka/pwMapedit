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


def test_moved_poi_keeps_position_after_map_level_change(window):
    scene = window.map_canvas
    map_items.PoiAsPixmap.last_used_type = 0x2f01
    scene.command_create_poi(scene.sceneRect().center())
    window.toolbar_action_trigered(pwmapedit_constants.Tools.SELECT_OBJECTS)
    poi = next(i for i in scene.items() if isinstance(i, map_items.PoiAsPixmap))
    poi.recorded_pos = poi.pos()
    new_pos = poi.pos() + QPointF(30, 20)
    poi.setPos(new_pos)
    poi.command_move_poi()
    scene.set_map_level(1)
    scene.set_map_level(0)
    assert poi.pos() == new_pos
    window.undo_redo_stack.undo()
    scene.set_map_level(1)
    scene.set_map_level(0)
    assert poi.pos() == poi.recorded_pos


def first_polyline(window):
    return next(i for i in window.map_canvas.items() if isinstance(i, map_items.PolylineQGraphicsPathItem))


def path_points(item):
    return [(p.x(), p.y()) for poly in item.path().toSubpathPolygons() for p in poly]


@pytest.mark.parametrize('edit', ['move', 'reverse'])
def test_repeated_undo_redo_restores_polyline(window, tmp_path, edit):
    # undo przywracalo kopie danych bez kopiowania, kolejne redo zmienialo te kopie i drugie undo nic nie cofalo
    line = first_polyline(window)
    original = saved_map(window, tmp_path / 'a.mp')
    if edit == 'move':
        line.recorded_pos = line.pos()
        line.setPos(QPointF(15, -10))
        line.command_move_item()
    else:
        line.command_reverse_poly()
    edited = saved_map(window, tmp_path / 'b.mp')
    assert edited != original
    stack = window.undo_redo_stack
    for _ in range(2):
        stack.undo()
        assert saved_map(window, tmp_path / 'c.mp') == original
        stack.redo()
        assert saved_map(window, tmp_path / 'd.mp') == edited


def test_polyline_shape_follows_data(window):
    scene = window.map_canvas
    line = first_polyline(window)
    window.toolbar_action_trigered(pwmapedit_constants.Tools.EDIT_NODES)
    scene.clearSelection()
    line.set_selected(True)
    grip = [g for g in line.node_grip_items if g.grip_indexes.node_index == 1][0]
    grip.setPos(grip.pos() + QPointF(12, -9))
    moved = path_points(line)
    assert moved[1] == (grip.pos().x(), grip.pos().y())
    line.command_insert_point(0, 1, QPointF(*moved[0]) + QPointF(1, 1))
    assert len(path_points(line)) == len(moved) + 1
    shape = path_points(line)
    scene.set_map_level(1)
    scene.set_map_level(0)
    assert path_points(line) == shape
    data = [node.get_canvas_coords() for node in line.map_object.data0.get_polys_for_data_level(0)[0]]
    assert data == shape


@pytest.mark.parametrize('attribute', ['numbers', 'hlevel'])
def test_node_attribute_undo_redo(window, tmp_path, attribute):
    scene = window.map_canvas
    line = first_polyline(window)
    window.toolbar_action_trigered(pwmapedit_constants.Tools.EDIT_NODES)
    scene.clearSelection()
    line.set_selected(True)
    grip = [g for g in line.node_grip_items if g.grip_indexes.node_index == 1][0]
    original = saved_map(window, tmp_path / 'a.mp')
    if attribute == 'numbers':
        assert grip.node_grip_get_numeration() is not None
        grip.node_grip_set_numeration(None)
    else:
        grip.node_grip_set_hlevel(3)
    edited = saved_map(window, tmp_path / 'b.mp')
    assert edited != original
    stack = window.undo_redo_stack
    for _ in range(2):
        stack.undo()
        assert saved_map(window, tmp_path / 'c.mp') == original
        stack.redo()
        assert saved_map(window, tmp_path / 'd.mp') == edited
