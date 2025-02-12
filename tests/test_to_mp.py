import pytest
import sys
import os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))
import map_items
import projection

NODE_TEST = (
        ((12.23456, 12.23456, 5), '(12.23456,12.23456)',),
        ((12.23456, 12.23456, 6), '(12.234560,12.234560)',),
)

@pytest.mark.parametrize('target, answer', NODE_TEST)
def test_get_mp_coords(target, answer):
    proj = projection.Mercator(None)
    node = map_items.Node(latitude=target[0], longitude=target[1], projection=proj)
    assert node.get_mp_coords(target[2]) == answer
