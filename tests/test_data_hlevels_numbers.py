import pytest
from pwm_core import projection
from pwm_core.data_x import Data_X
from pwm_core.geometry import Point, Line

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
    data_obj = Data_X(projection=proj)
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
    data_obj = Data_X(projection=proj)
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
    data_obj = Data_X(projection=proj)
    data_obj.add_nodes_from_string('Data0', target[0])
    data_obj.add_housenumbers_from_string(target[1])
    data_obj.add_housenumbers_from_string(target[2])
    for node_num, definition in enumerate(data_obj.get_housenumbers_for_poly(0, 0)):
        def_ = {a: b for a, b in definition._asdict().items() if b is not None}
        def_['n'] = node_num
        assert def_ == answer[node_num]


NUMBERS_BETWEEN = (
    ((1, 9, 'O'), ([3, 5, 7])),
    ((9, 1, 'O'), ([7, 5, 3])),
    ((2, 10, 'O'), ([3, 5, 7, 9])),
    ((2, 10, 'E'), ([4, 6, 8])),
    ((10, 2, 'E'), ([8, 6, 4])),
    ((1, 11, 'E'), ([2, 4, 6, 8, 10])),
    ((11, 1, 'B'), ([10, 9, 8, 7, 6, 5, 4, 3, 2])),

)
@pytest.mark.parametrize('target, answer', NUMBERS_BETWEEN)
def test_get_numbers_between(target, answer):
    assert Data_X.get_numbers_between(target[0], target[1], target[2]) == answer

INTERPOLATED_NUMS_COORDS = (
    (([Line(0, 0, 1, 0)], [3]), [(Line(0, 0, 1, 0), Point(0.5, 0), 3),],),
    (([Line(0, 0, 0, 3)], [1, 2]), [(Line(0, 0, 0, 3), Point(0, 1), 1), (Line(0, 0, 0, 3), Point(0, 2), 2),],),
    (([Line(0, 0, 0, 4)], [1, 2, 3]), [(Line(0, 0, 0, 4), Point(0, 1), 1), (Line(0, 0, 0, 4), Point(0, 2), 2), (Line(0, 0, 0, 4),Point(0, 3), 3)],),
    (([Line(0, 0, 0, 1), Line(0, 1, 0, 3)], [3]), [(Line(0, 1, 0, 3), Point(0, 1.5), 3)],),
    (([Line(0, 0, 5, 0), Line(5, 0, 10, 0)], [1, 2, 3, 4, 5, 6, 7, 8, 9]),
     [(Line(0, 0, 5, 0), Point(1, 0), 1), (Line(0, 0, 5, 0), Point(2, 0), 2),
      (Line(0, 0, 5, 0), Point(3, 0), 3), (Line(0, 0, 5, 0), Point(4, 0), 4),
      (Line(0, 0, 5, 0), Point(5, 0), 5),
      (Line(5, 0, 10, 0), Point(6, 0), 6), (Line(5, 0, 10, 0), Point(7, 0), 7),
      (Line(5, 0, 10, 0), Point(8, 0), 8), (Line(5, 0, 10, 0), Point(9, 0), 9)],
     ),
    (([Line(0, 0, 4, 0), Line(4, 0, 5, 0), Line(5, 0, 6, 0), Line(6, 0, 9, 0)], [1, 2]),
     [(Line(0, 0, 4, 0), Point(3, 0), 1), (Line(5, 0, 6, 0), Point(6, 0), 2),]
     ),
    (([Line(0, 0, 100, 0), Line(100, 0, 200, 0), Line(200, 0, 300, 0), Line(300, 0, 400, 0), Line(400, 0, 500, 0)], [1, 2, 3, 4]), [(Line(0, 0, 100, 0), Point(100, 0), 1), (Line(100, 0, 200, 0), Point(200, 0), 2), (Line(200, 0, 300, 0), Point(300, 0), 3), (Line(300, 0, 400, 0), Point(400, 0), 4)],),

)

@pytest.mark.parametrize('target, answer', INTERPOLATED_NUMS_COORDS)
def test_interpolated_number_coordinates(target, answer):
    answer_list = [tuple(a) for a in Data_X.get_interpolated_numbers_coordinates(target[0], target[1])]
    assert answer_list == answer

ADDRESSES = (
        (('(52.85431,16.02645),(52.85454,16.02758)', 'Numbers1=0,O,1,9,E,2,10',), ([{'left_side_number_after': 10,
          'left_side_numbering_style': 'E', 'right_side_number_after': 9, 'right_side_numbering_style': 'O'},
          {'left_side_number_before': 2, 'right_side_number_before': 1}]),),
        # (('(52.85431,16.02645),(52.85454,16.02758),(52.85465,16.02808),(52.85470,16.02828),(52.85482,16.02884),(52.85490,16.02918),(52.85515,16.03006),(52.85520,16.03026),(52.85534,16.03117),(52.85545,16.03166),(52.85556,16.03215),(52.85570,16.03275),(52.85576,16.03302),(52.85585,16.03341),(52.85600,16.03417),(52.85610,16.03462),(52.85636,16.03508)',
        #   'Numbers1=0,O,45,41,E,46,40',
        #   'Numbers2=1,B,39,39,N,-1,-1',
        #   'Numbers3=2,B,38,38,B,37,37',
        #   'Numbers4=3,O,35,33,E,36,32',
        #   'Numbers5=4,B,30,30,B,31,31',
        #   'Numbers6=5,B,29,28,N,-1,-1',
        #   'Numbers7=6,B,26,26,B,25,25',
        #   'Numbers8=7,B,23,23,N,-1,-1',
        #   'Numbers9=8,B,20,20,B,22,22',
        #   'Numbers10=9,B,19,19,B,18,17',
        #   'Numbers11=10,B,15,13,B,16,16',
        #   'Numbers12=11,B,13,12,B,11,11',
        #   'Numbers13=12,B,9,8,B,10,10',
        #   'Numbers14=13,B,6,6,O,7,5',
        #   'Numbers15=14,B,3,3,B,4,4',
        #   'Numbers16=15,N,-1,-1,B,2,2',),
        #  ([])),
)


@pytest.mark.parametrize('target, answer', ADDRESSES)
def test_invert_poly_addresses(target, answer):
    proj = projection.Mercator(None)
    data_obj = Data_X(projection=proj)
    data_obj.add_nodes_from_string('Data0', target[0])
    for num_num in range(1, 2):
        data_obj.add_housenumbers_from_string(target[num_num])

    adr_ans = []
    data_obj.reverse_poly(0)
    for adr in data_obj.get_housenumbers_for_poly(0, 0):
        adr_ans.append({a: b for a, b in adr._asdict().items() if b is not None})

    assert adr_ans == answer


# obiekty, ktorych poziomy nie ida po kolei (np. tylko Data0 i Data2) - _poly_data_points jest indeksowane pozycja
# poziomu, a nie jego numerem
def _data_obj_from_lines(lines):
    data_obj = Data_X(projection=projection.Mercator(None))
    for dataline in lines:
        if dataline.startswith('Numbers'):
            data_obj.add_housenumbers_from_string(dataline)
        else:
            data_level, data_string = dataline.split('=', 1)
            data_obj.add_nodes_from_string(data_level, data_string)
    return data_obj


DATA0_DATA2 = ('Data0=(52.42016,20.68638),(52.42011,20.68643),(52.42007,20.68651)',
               'Data2=(52.43016,20.69638),(52.43011,20.69643),(52.43007,20.69651),(52.43001,20.69660)')


def test_insert_node_not_consecutive_levels():
    data_obj = _data_obj_from_lines(DATA0_DATA2)
    data_obj.insert_node_at_position(2, 0, -1, 10.0, 20.0)
    assert len(data_obj.get_polys_for_data_level(2)[0]) == 5
    assert len(data_obj.get_polys_for_data_level(0)[0]) == 3


def test_split_not_consecutive_levels():
    data_obj = _data_obj_from_lines(DATA0_DATA2)
    assert data_obj.is_splitting_possible(2, 0, 2)
    poly1, poly2 = data_obj.split_data_x(2, 0, 2)
    assert len(poly1.get_polys_for_data_level(2)[0]) == 3
    assert len(poly1.get_polys_for_data_level(0)[0]) == 3
    assert poly2.get_data_levels() == [2]
    assert len(poly2.get_polys_for_data_level(2)[0]) == 2


def test_split_second_poly_on_level():
    # druga linia na tym samym poziomie - nowy obiekt ma tylko jedna linie (numer 0)
    data_obj = _data_obj_from_lines((DATA0_DATA2[0], DATA0_DATA2[1].replace('Data2', 'Data0')))
    poly1, poly2 = data_obj.split_data_x(0, 1, 2)
    assert len(poly2.get_polys_for_data_level(0)) == 1


def test_delete_poly_not_consecutive_levels():
    data_obj = _data_obj_from_lines(DATA0_DATA2)
    data_obj.delete_poly_at_data_level(2, 0)
    assert data_obj.get_data_levels() == [0]
    assert len(data_obj.get_polys_for_data_level(0)[0]) == 3


def test_housenumbers_on_data1_only():
    data_obj = _data_obj_from_lines(('Data1=(51.43507,16.10151),(51.43477,16.10183),(51.43465,16.10206)',
                                     'Numbers1=0,O,157,157,E,154,154', 'Numbers2=1,E,156,156,O,155,155'))
    numbers = data_obj.get_housenumbers_for_poly(1, 0)
    assert numbers[0].left_side_number_after == 157
    assert numbers[2].right_side_number_before == 155
