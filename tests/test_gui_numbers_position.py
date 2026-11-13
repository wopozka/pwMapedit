"""Testy czesci graficznej (wymagaja PyQt6)."""
import pytest
pytest.importorskip('PyQt6')
from PyQt6.QtCore import QPointF, QLineF
import map_items


TEST_ADRESS_NUMBER_POSITION = (
    # node_coords, line_segment_vector,
    # subj_position
    ((QLineF(QPointF(0.0, 0.0), QPointF(100.0, 0.0)), 'left_side_number_after',), QPointF(20.0, 20.0)),
    ((QLineF(QPointF(0.0, 0.0), QPointF(100.0, 0.0)), 'right_side_number_after',), QPointF(20.0, -20.0)),
    ((QLineF(QPointF(0.0, 0.0), QPointF(100.0, 0.0)), 'left_side_number_before',), QPointF(80, 20.0)),
    ((QLineF(QPointF(0.0, 0.0), QPointF(100.0, 0.0)), 'right_side_number_before',), QPointF(80.0, -20.0)),
    ((QLineF(QPointF(0.0, 0.0), QPointF(0.0, 100.0)), 'left_side_number_after',), QPointF(-20.0, 20.0)),
    ((QLineF(QPointF(0.0, 0.0), QPointF(0.0, 100.0)), 'right_side_number_after',), QPointF(20.0, 20.0)),
    ((QLineF(QPointF(0.0, 0.0), QPointF(0.0, 100.0)), 'left_side_number_before',), QPointF(-20, 80.0)),
    ((QLineF(QPointF(0.0, 0.0), QPointF(0.0, 100.0)), 'right_side_number_before',), QPointF(20.0, 80.0)),
    ((QLineF(QPointF(0.0, 0.0), QPointF(-100.0, 0.0)), 'left_side_number_after',), QPointF(-20.0, -20.0)),
    ((QLineF(QPointF(0.0, 0.0), QPointF(-100.0, 0.0)), 'right_side_number_after',), QPointF(-20.0, 20.0)),
    ((QLineF(QPointF(0.0, 0.0), QPointF(-100.0, 0.0)), 'left_side_number_before',), QPointF(-80.0, -20.0)),
    ((QLineF(QPointF(0.0, 0.0), QPointF(-100.0, 0.0)), 'right_side_number_before',), QPointF(-80.0, 20.0)),
    ((QLineF(QPointF(0.0, 0.0), QPointF(0.0, -100.0)), 'left_side_number_after',), QPointF(20.0, -20.0)),
    ((QLineF(QPointF(0.0, 0.0), QPointF(0.0, -100.0)), 'right_side_number_after',), QPointF(-20.0, -20.0)),
    ((QLineF(QPointF(0.0, 0.0), QPointF(0.0, -100.0)), 'left_side_number_before',), QPointF(20, -80.0)),
    ((QLineF(QPointF(0.0, 0.0), QPointF(0.0, -100.0)), 'right_side_number_before',), QPointF(-20.0, -80.0)),

)

@pytest.mark.parametrize('target, answer', TEST_ADRESS_NUMBER_POSITION)
def test_get_numbers_position(target, answer):
    assert map_items.PolylineQGraphicsPathItem.get_numbers_position(target[0], target[1], testing=True).p2() == answer

