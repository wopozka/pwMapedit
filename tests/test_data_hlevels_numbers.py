import pytest
import sys
import os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))
import map_items
import projection
from PyQt5.QtGui import QPainterPath, QPolygonF
from PyQt5.QtCore import QPointF, QLineF

DATA_TEST = (
    (('Data0=(52.42016,20.68638),(52.42011,20.68643),(52.42007,20.68651)',), [0]),
    (('Data0=(52.42016,20.68638),(52.42011,20.68643),(52.42007,20.68651)', 'Data1=(52.42016,20.68638),(52.42011,20.68643),(52.42007,20.68651)'), [0, 1]),
    (('Data0=(52.42016,20.68638),(52.42011,20.68643),(52.42007,20.68651)', 'Data2=(52.42016,20.68638),(52.42011,20.68643),(52.42007,20.68651)'), [0, 2]),
    (('Data0=(52.42016,20.68638),(52.42011,20.68643),(52.42007,20.68651)', 'Data1=(52.42016,20.68638),(52.42011,20.68643),(52.42007,20.68651)', 'Data2=(52.42016,20.68638),(52.42011,20.68643),(52.42007,20.68651)'), [0, 1, 2]),
    (('Data0=(52.42016,20.68638),(52.42011,20.68643),(52.42007,20.68651)',
      'Data0=(52.42016,20.68638),(52.42011,20.68643),(52.42007,20.68651)',
      'Data1=(52.42016,20.68638),(52.42011,20.68643),(52.42007,20.68651)',
      'Data1=(52.42016,20.68638),(52.42011,20.68643),(52.42007,20.68651)',
      'Data2=(52.42016,20.68638),(52.42011,20.68643),(52.42007,20.68651)',
      'Data2=(52.42016,20.68638),(52.42011,20.68643),(52.42007,20.68651)'), [0, 1, 2]),

)
@pytest.mark.parametrize('target, answer', DATA_TEST)
def test_data_levels(target, answer):
    proj = projection.Mercator(None)
    data_obj = map_items.Data_X(projection=proj)
    for dataline in target:
        data_obj.add_nodes_from_string(dataline)
    assert data_obj.get_data_levels() == answer


DATA_TEST = (
    (('Data0=(52.42016,20.68638),(52.42011,20.68643),(52.42007,20.68651)',
      'Data0=(52.42016,20.68638),(52.42011,20.68643),(52.42007,20.68651)',
      'Data1=(52.42016,20.68638),(52.42011,20.68643),(52.42007,20.68651)',
      'Data1=(52.42016,20.68638),(52.42011,20.68643),(52.42007,20.68651)',
      'Data2=(52.42016,20.68638),(52.42011,20.68643),(52.42007,20.68651)',
      'Data2=(52.42016,20.68638),(52.42011,20.68643),(52.42007,20.68651)',
      'Data2=(52.42016,20.68638),(52.42011,20.68643),(52.42007,20.68651)'), (2, 2)),
    (('Data0=(52.42016,20.68638),(52.42011,20.68643),(52.42007,20.68651)',
      'Data0=(52.42016,20.68638),(52.42011,20.68643),(52.42007,20.68651)',
      'Data1=(52.42016,20.68638),(52.42011,20.68643),(52.42007,20.68651)',
      'Data1=(52.42016,20.68638),(52.42011,20.68643),(52.42007,20.68651)',
      'Data2=(52.42016,20.68638),(52.42011,20.68643),(52.42007,20.68651)',
      'Data2=(52.42016,20.68638),(52.42011,20.68643),(52.42007,20.68651)',
      'Data4=(52.42016,20.68638),(52.42011,20.68643),(52.42007,20.68651)'), (4, 0)),

)
@pytest.mark.parametrize('target, answer', DATA_TEST)
def test_data_levels(target, answer):
    proj = projection.Mercator(None)
    data_obj = map_items.Data_X(projection=proj)
    for dataline in target:
        data_obj.add_nodes_from_string(dataline)
    assert data_obj.get_last_data_level_and_last_index() == answer

TEST_ADDRESS_ADDING = (
    (('(51.43507,16.10151),(51.43477,16.10183),(51.43465,16.10206)', 'Numbers1=0,O,157,157,E,154,154', 'Numbers2=1,E,156,156,O,155,155'),
     ({'left_side_numbering_style': 'O', 'left_side_number_after': 157, 'right_side_numbering_style': 'E', 'right_side_number_after': 154, 'n': 0},
      {'left_side_numbering_style': 'E', 'left_side_number_before': 157, 'left_side_number_after': 156, 'right_side_numbering_style': 'O', 'right_side_number_before': 154, 'right_side_number_after': 155, 'n': 1},
      {'left_side_number_before': 156, 'right_side_number_before': 155, 'n': 2},
     ),
    ),
)

@pytest.mark.parametrize('target, answer', TEST_ADDRESS_ADDING)
def test_address_adding(target, answer):
    proj = projection.Mercator(None)
    data_obj = map_items.Data_X(projection=proj)
    data_obj.add_nodes_from_string('Data0', target[0])
    data_obj.add_housenumbers_from_string(target[1])
    data_obj.add_housenumbers_from_string(target[2])
    for node_num, definition in enumerate(data_obj.get_housenumbers_for_poly(0, 0)):
        def_ = {a: b for a, b in definition._asdict().items() if b is not None}
        def_['n'] = node_num
        assert def_ == answer[node_num]


TEST_ADRESS_NUMBER_POSITION = (
# node_coords, line_segment_vector, subj_position
    ((QPointF(0.0, 0.0), QPointF(100.0, 0.0), 'left_side_number_after',), QPointF(20.0, 20.0)),
    ((QPointF(0.0, 0.0), QPointF(100.0, 0.0), 'right_side_number_after',), QPointF(20.0, -20.0)),
    ((QPointF(100.0, 0.0), QPointF(100.0, 0.0), 'left_side_number_before',), QPointF(80, 20.0)),
    ((QPointF(100.0, 0.0), QPointF(100.0, 0.0), 'right_side_number_before',), QPointF(80.0, -20.0)),
    ((QPointF(0.0, 0.0), QPointF(0.0, 100.0), 'left_side_number_after',), QPointF(-20.0, 20.0)),
    ((QPointF(0.0, 0.0), QPointF(0.0, 100.0), 'right_side_number_after',), QPointF(20.0, 20.0)),
    ((QPointF(0.0, 100.0), QPointF(0.0, 100.0), 'left_side_number_before',), QPointF(-20, 80.0)),
    ((QPointF(0.0, 100.0), QPointF(0.0, 100.0), 'right_side_number_before',), QPointF(20.0, 80.0)),
    ((QPointF(0.0, 0.0), QPointF(-100.0, 0.0), 'left_side_number_after',), QPointF(-20.0, -20.0)),
    ((QPointF(0.0, 0.0), QPointF(-100.0, 0.0), 'right_side_number_after',), QPointF(-20.0, 20.0)),
    ((QPointF(-100.0, 0.0), QPointF(-100.0, 0.0), 'left_side_number_before',), QPointF(-80.0, -20.0)),
    ((QPointF(-100.0, 0.0), QPointF(-100.0, 0.0), 'right_side_number_before',), QPointF(-80.0, 20.0)),
    ((QPointF(0.0, 0.0), QPointF(0.0, -100.0), 'left_side_number_after',), QPointF(20.0, -20.0)),
    ((QPointF(0.0, 0.0), QPointF(0.0, -100.0), 'right_side_number_after',), QPointF(-20.0, -20.0)),
    ((QPointF(0.0, -100.0), QPointF(0.0, -100.0), 'left_side_number_before',), QPointF(20, -80.0)),
    ((QPointF(0.0, -100.0), QPointF(0.0, -100.0), 'right_side_number_before',), QPointF(-20.0, -80.0)),

)

@pytest.mark.parametrize('target, answer', TEST_ADRESS_NUMBER_POSITION)
def test_get_numbers_position(target, answer):
    assert map_items.PolylineQGraphicsPathItem.get_numbers_position(target[0], target[1], target[2]) == answer
