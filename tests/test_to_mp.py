import pytest
import sys
import os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))
import map_items
import projection
import misc_functions
import map_object_properties

NODE_TEST = (
        ((12.23456, 12.23456, 5), '(12.23456,12.23456)',),
        ((12.23456, 12.23456, 6), '(12.234560,12.234560)',),
)

@pytest.mark.parametrize('target, answer', NODE_TEST)
def test_get_mp_coords(target, answer):
    proj = projection.Mercator(None)
    node = map_items.Node(latitude=target[0], longitude=target[1], projection=proj)
    assert node.get_mp_coords(target[2]) == answer

DATA_TEST = (
    ('Data0=(51.81940,19.30379),(51.81887,19.30638)', ['Data0=(51.81940,19.30379),(51.81887,19.30638)']),
    ('Data0=(51.819400,19.303790),(51.818870,19.306380)', ['Data0=(51.819400,19.303790),(51.818870,19.306380)'])
)

@pytest.mark.parametrize('target, answer', DATA_TEST)
def test_data_to_mp_record(target, answer):
    _projection = projection.Mercator(None)
    data_x = map_items.Data_X(projection=_projection)
    data_level, data_string = target.split('=', 1)
    data_x.add_nodes_from_string(data_level, data_string)
    assert data_x.to_mp_record() == answer
