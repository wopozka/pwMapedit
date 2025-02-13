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
    (['[POLYLINE]', 'Type=0x1', 'Data0=(51.81940,19.30379),(51.81887,19.30638)', '[END]'], 'Data0=(51.81940,19.30379),(51.81887,19.30638)'),
)

@pytest.mark.parametrize('target, answer', DATA_TEST)
def test_data_to_mp_record(target, answer):
    _map_object_properties = map_object_properties.MapObjectsProperties()
    _projection = projection.Mercator({})
    poi_poly_type, obj_comment, obj_data = misc_functions.map_strings_record_to_dict_record(target)
    map_object = map_items.PolylineQGraphicsPathItem(1,
                                                     map_objects_properties=_map_object_properties,
                                                     projection=_projection)
    map_object.set_data(obj_comment, obj_data)
    map_object.set_mp_data()
    assert map_object.data0.data_to_mp_record(target) == answer
