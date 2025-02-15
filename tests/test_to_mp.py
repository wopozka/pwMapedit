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
    (['Data0=(51.81940,19.30379),(51.81887,19.30638)'], ['Data0=(51.81940,19.30379),(51.81887,19.30638)']),
    (['Data0=(51.819400,19.303790),(51.818870,19.306380)'], ['Data0=(51.819400,19.303790),(51.818870,19.306380)']),
    (['Data0=(51.58380,19.16071),(51.58308,19.16061),(51.58270,19.16055),(51.58242,19.16077),(51.58112,19.16071)', 'Numbers1=0,B,61,61,N,-1,-1', 'Numbers2=1,B,61,61,N,-1,-1', 'Numbers3=2,B,60,60,N,-1,-1', 'Numbers4=3,B,266,266,B,59,59'], ['Data0=(51.58380,19.16071),(51.58308,19.16061),(51.58270,19.16055),(51.58242,19.16077),(51.58112,19.16071)', 'Numbers1=0,B,61,61,N,-1,-1', 'Numbers2=1,B,61,61,N,-1,-1', 'Numbers3=2,B,60,60,N,-1,-1', 'Numbers4=3,B,266,266,B,59,59'],),
)

@pytest.mark.parametrize('target, answer', DATA_TEST)
def test_data_to_mp_record(target, answer):
    _projection = projection.Mercator(None)
    data_x = map_items.Data_X(projection=_projection)
    for data_line in target:
        if data_line.startswith('Data'):
            data_level, data_string = data_line.split('=', 1)
            data_x.add_nodes_from_string(data_level, data_string)
        elif data_line.startswith('Numbers'):
            data_x.add_housenumbers_from_string(data_line)
    assert data_x.to_mp_record() == answer
