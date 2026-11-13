import pytest
pytest.importorskip('PyQt6')
import map_items
from pwm_core import projection
from map_object_properties import MapObjectsProperties
from PyQt6.QtGui import QPainterPath, QPolygonF
from PyQt6.QtCore import QPointF, QLineF


DATA_TEST = ()

@pytest.mark.parametrize('target, answer', DATA_TEST)
def test_closest_point_to_poly_insert_node(target, answer):
    proj = projection.Mercator(None)
    map_obj_properties = MapObjectsProperties()
    map_item = map_items.PolyQGraphicsPathItem(map_obj_id=1, map_objects_properties=map_obj_properties,
                                               _projection=proj)
    for dataline in target:
        data_level, data_string = dataline.split('=', 1)
        data_obj.add_nodes_from_string(data_level, data_string)
    assert data_obj.get_data_levels() == answer