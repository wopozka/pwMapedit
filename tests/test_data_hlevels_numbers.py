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
        data_level, data_string = dataline.split('=', 1)
        data_obj.add_nodes_from_string(data_level, data_string)
    assert data_obj.get_data_levels() == answer


DATA_TEST1 = (
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
@pytest.mark.parametrize('target, answer', DATA_TEST1)
def test_data_levels(target, answer):
    proj = projection.Mercator(None)
    data_obj = map_items.Data_X(projection=proj)
    for dataline in target:
        data_level, data_string = dataline.split('=', 1)
        data_obj.add_nodes_from_string(data_level, data_string)
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

NUMBERS_BETWEEN = (
    ((1, 9, 'odd'), ([3, 5, 7])),
    ((9, 1, 'odd'), ([7, 5, 3])),
    ((2, 10, 'odd'), ([3, 5, 7, 9])),
    ((2, 10, 'even'), ([4, 6, 8])),
    ((10, 2, 'even'), ([8, 6, 4])),
    ((1, 11, 'even'), ([2, 4, 6, 8, 10])),
    ((11, 1, 'both'), ([10, 9, 8, 7, 6, 5, 4, 3, 2])),

)
@pytest.mark.parametrize('target, answer', NUMBERS_BETWEEN)
def test_get_numbers_between(target, answer):
    assert map_items.Data_X.get_numbers_between(target[0], target[1], target[2]) == answer

INTERPOLATED_NUMS_COORDS = (
    (([QLineF(0, 0, 1, 0)], [3]), [(QLineF(0, 0, 1, 0), QPointF(0.5, 0), 3),],),
    (([QLineF(0, 0, 0, 4)], [1, 2, 3]), [(QLineF(0, 0, 0, 4), QPointF(0, 1), 1), (QLineF(0, 0, 0, 4), QPointF(0, 2), 2), (QLineF(0, 0, 0, 4),QPointF(0, 3), 3)],),
    (([QLineF(0, 0, 0, 1), QLineF(0, 1, 0, 3)], [3]), [(QLineF(0, 1, 0, 3), QPointF(0, 1.5), 3)],),
    (([QLineF(0, 0, 100, 0), QLineF(100, 0, 200, 0), QLineF(200, 0, 300, 0), QLineF(300, 0, 400, 0), QLineF(400, 0, 500, 0)], [1, 2, 3, 4]), [(QLineF(0, 0, 100, 0), QPointF(99, 0), 1), (QLineF(100, 0, 200, 0), QPointF(199, 0), 2), (QLineF(200, 0, 300, 0), QPointF(299, 0), 3), (QLineF(300, 0, 400, 0), QPointF(399, 0), 4)],),
)

@pytest.mark.parametrize('target, answer', INTERPOLATED_NUMS_COORDS)
def test_interpolated_number_coordinates(target, answer):
    answer_list = [tuple(a) for a in map_items.Data_X.get_interpolated_numbers_coordinates(target[0], target[1])]
    assert answer_list == answer

INTERPOLATED_ADDRESSES = (
        (('(53.14643,16.72784),(53.14661,16.72864),(53.14683,16.72958),(53.14712,16.73131),(53.14735,16.73287),(53.14748,16.73392),(53.14758,16.73477),(53.14766,16.73534)',
          'Numbers1=0,E,50,48,O,31,29',
          'Numbers2=1,E,46,46,O,27,21',
          'Numbers3=2,E,44,32,N,-1,-1',
          'Numbers4=3,E,30,20,O,13,11',
          'Numbers5=4,E,18,14,O,9,7',
          'Numbers6=5,E,12,6,O,5,1',
          'Numbers7=6,E,4,2,N,-1,-1',),([])),
)


@pytest.mark.parametrize('target, answer', INTERPOLATED_ADDRESSES)
def test_address_adding_from_str(target, answer):
    proj = projection.Mercator(None)
    data_obj = map_items.Data_X(projection=proj)
    data_obj.add_nodes_from_string('Data0', target[0])
    data_obj.add_housenumbers_from_string(target[1])
    data_obj.add_housenumbers_from_string(target[2])
    data_obj.add_housenumbers_from_string(target[3])
    data_obj.add_housenumbers_from_string(target[4])
    data_obj.add_housenumbers_from_string(target[5])
    data_obj.add_housenumbers_from_string(target[6])
    data_obj.add_housenumbers_from_string(target[7])

    assert data_obj.get_interpolated_housenumbers_for_poly(0, 0) == answer
