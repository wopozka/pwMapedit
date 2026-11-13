import pytest
from pwm_core import projection
from pwm_core.data_x import Data_X, MergeError
from pwm_core.map_object import BasicMapItem

PROJ = projection.Mercator(None)

A = 'Data0=(52.00000,20.00000),(52.00100,20.00100),(52.00200,20.00200)'
B = 'Data0=(52.00200,20.00200),(52.00300,20.00300)'
B_REV = 'Data0=(52.00300,20.00300),(52.00200,20.00200)'
BEFORE_A = 'Data0=(51.99900,19.99900),(52.00000,20.00000)'
C = 'Data0=(52.00300,20.00300),(52.00400,20.00400),(52.00500,20.00500)'
FAR = 'Data0=(53.00000,21.00000),(53.00100,21.00100)'


def data_obj(*lines):
    obj = Data_X(projection=PROJ)
    for line in lines:
        if line.startswith('Numbers'):
            obj.add_housenumbers_from_string(line)
        elif line.startswith('HLevel'):
            obj.add_hlevels_from_string(line)
        else:
            level, data_string = line.split('=', 1)
            obj.add_nodes_from_string(level, data_string)
    return obj


def coords(merged, level=0):
    return [tuple(round(c, 5) for c in node.get_geo_coordinates())
            for node in merged.get_polys_for_data_level(level)[0]]


def test_end_to_start():
    merged, skipped, reversed_any = Data_X.merge_polylines([data_obj(A), data_obj(B)])
    assert coords(merged) == [(52.0, 20.0), (52.001, 20.001), (52.002, 20.002), (52.003, 20.003)]
    assert skipped == [] and reversed_any is False


def test_end_to_end_reverses_second():
    merged, _, reversed_any = Data_X.merge_polylines([data_obj(A), data_obj(B_REV)])
    assert coords(merged)[-1] == (52.003, 20.003)
    assert len(coords(merged)) == 4
    assert reversed_any is True


def test_prepend_keeps_first_direction():
    merged, _, reversed_any = Data_X.merge_polylines([data_obj(A), data_obj(BEFORE_A)])
    assert coords(merged) == [(51.999, 19.999), (52.0, 20.0), (52.001, 20.001), (52.002, 20.002)]
    assert reversed_any is False


def test_three_lines_any_order():
    # C dotyka dopiero B, wiec przy pierwszym przejsciu musi poczekac
    merged, _, _ = Data_X.merge_polylines([data_obj(A), data_obj(C), data_obj(B)])
    assert coords(merged)[0] == (52.0, 20.0)
    assert coords(merged)[-1] == (52.005, 20.005)
    assert len(coords(merged)) == 6


def test_not_touching_raises():
    with pytest.raises(MergeError):
        Data_X.merge_polylines([data_obj(A), data_obj(FAR)])


def test_multipart_raises():
    with pytest.raises(MergeError):
        Data_X.merge_polylines([data_obj(A, FAR), data_obj(B)])


def test_level_missing_in_one_line_is_skipped():
    merged, skipped, _ = Data_X.merge_polylines([data_obj(A, A.replace('Data0', 'Data1')), data_obj(B)])
    assert merged.get_data_levels() == [0]
    assert skipped == [1]


def test_higher_level_not_touching_is_skipped():
    merged, skipped, _ = Data_X.merge_polylines(
        [data_obj(A, A.replace('Data0', 'Data1')), data_obj(B, FAR.replace('Data0', 'Data1'))])
    assert merged.get_data_levels() == [0]
    assert skipped == [1]


def test_source_objects_not_modified():
    a, b = data_obj(A), data_obj(B_REV)
    Data_X.merge_polylines([a, b])
    assert len(a.get_polys_for_data_level(0)[0]) == 3
    assert [tuple(round(c, 5) for c in n.get_geo_coordinates()) for n in b.get_polys_for_data_level(0)[0]] == \
        [(52.003, 20.003), (52.002, 20.002)]


def test_numbers_and_hlevel_at_joint():
    a = data_obj(A, 'Numbers1=0,O,1,5,E,2,6')
    b = data_obj(B, 'Numbers1=0,O,7,9,E,8,10', 'HLevel0=(0,1)')
    merged, _, _ = Data_X.merge_polylines([a, b])
    joint = merged.get_polys_for_data_level(0)[0][2]
    numbers = joint.get_numbers_definition()
    # koniec przedzialu z pierwszej linii, poczatek przedzialu z drugiej
    assert numbers.left_side_number_before == 5 and numbers.right_side_number_before == 6
    assert numbers.left_side_number_after == 7 and numbers.right_side_number_after == 8
    assert joint.get_hlevel_definition() == 1
    record = merged.to_mp_record()
    assert record[1:] == ['Numbers1=0,O,1,5,E,2,6', 'Numbers2=2,O,7,9,E,8,10', 'HLevel0=(2,1)']


def test_bounding_box_covers_all():
    merged, _, _ = Data_X.merge_polylines([data_obj(A), data_obj(B)])
    bbox = merged.get_obj_bounding_box()
    assert round(bbox['S'], 5) == 52.0 and round(bbox['N'], 5) == 52.003
    assert round(bbox['W'], 5) == 20.0 and round(bbox['E'], 5) == 20.003


def test_merge_after_split_has_bounding_box():
    # druga czesc z podzialu linii ma Data_X bez obwiedni (None)
    _, part2 = data_obj(A).split_data_x(0, 0, 1)
    assert part2.get_obj_bounding_box()['N'] is None
    merged, _, _ = Data_X.merge_polylines([part2, data_obj(B)])
    bbox = merged.get_obj_bounding_box()
    assert round(bbox['S'], 5) == 52.001 and round(bbox['N'], 5) == 52.003


def test_basic_item_bounding_box_with_none():
    item = BasicMapItem(None, _projection=PROJ)
    item.set_obj_bounding_box({'S': None, 'N': None, 'E': None, 'W': None})
    item.set_obj_bounding_box({'S': 1.0, 'N': 2.0, 'E': 4.0, 'W': 3.0})
    item.set_obj_bounding_box({'S': None, 'N': None, 'E': None, 'W': None})
    assert item.obj_bounding_box == {'S': 1.0, 'N': 2.0, 'E': 4.0, 'W': 3.0}
