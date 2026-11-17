"""Obiekty mapy z rdzenia (pwm_core.map_object) - bez Qt."""
import pytest
from pwm_core import mp_format, projection
from pwm_core.data_x import MergeError
from pwm_core.map_object import Poi, Polyline, Polygon

PROJ = projection.Mercator(None)

LINE = [';komentarz', '[POLYLINE]', 'Type=0x6', 'Label=Prosta', 'DirIndicator=1',
        'RouteParam=3,2,1,0,0,0,0,0,0,0,0,0',
        'Data0=(52.00000,20.00000),(52.00100,20.00100),(52.00200,20.00200),(52.00300,20.00300)',
        'Miasto=Testowo']


def make(cls, record, obj_id=1):
    _, comments, fields = mp_format.map_strings_record_to_dict_record(record)
    obj = cls(obj_id, _projection=PROJ)
    obj.set_data(comments, fields)
    return obj


def data0_line(obj):
    return [line for line in obj.to_mp_record() if line.startswith('Data0=')]


def test_record_header_and_str():
    poi = make(Poi, ['[POI]', 'Type=0x2f00', 'Data0=(52.00000,20.00000)'], obj_id=5)
    polygon = make(Polygon, ['[POLYGON]', 'Type=0x4e', 'Data0=(52.0,20.0),(52.1,20.0),(52.1,20.1)'])
    assert poi.to_mp_record()[0] == '[POI]'
    assert polygon.to_mp_record()[0] == '[POLYGON]'
    assert str(poi) == '<POI, Object ID: 5, Type: 12032>'


def test_poi_position():
    poi = make(Poi, ['[POI]', 'Type=0x2f00', 'Data0=(52.00000,20.00000)', 'Data1=(52.10000,20.10000)'])
    assert poi.get_position(2) is None
    x, y = poi.get_position(0).get_canvas_coords()
    target = poi.get_position(1)
    poi.set_position(0, target)
    assert poi.get_position(0).get_canvas_coords() == target.get_canvas_coords() != (x, y)
    assert 'Data0=(52.10000,20.10000)' in poi.to_mp_record()


def test_is_oneway():
    line = make(Polyline, LINE)
    assert line.is_oneway()
    line.set_route_params([3, 2, 0])
    assert not line.is_oneway()


def test_split_keeps_properties():
    line = make(Polyline, LINE, obj_id=7)
    line1, line2 = line.split(0, 0, 2)
    assert line1.get_id() == 7
    assert line2.get_id() is None
    assert data0_line(line1) == ['Data0=(52.00000,20.00000),(52.00100,20.00100),(52.00200,20.00200)']
    assert data0_line(line2) == ['Data0=(52.00200,20.00200),(52.00300,20.00300)']
    for part in (line1, line2):
        assert isinstance(part, Polyline)
        record = part.to_mp_record()
        assert record[:2] == [';komentarz', '[POLYLINE]']
        assert 'Label=Prosta' in record and 'DirIndicator=1' in record and 'Miasto=Testowo' in record
    # oryginal bez zmian
    assert data0_line(line) == [LINE[6]]


def test_split_at_end_is_not_possible():
    line = make(Polyline, LINE)
    assert line.split(0, 0, 0) is None


def test_merged_with():
    first = make(Polyline, LINE, obj_id=3)
    second = make(Polyline, ['[POLYLINE]', 'Type=0x1', 'Label=Inna',
                             'Data0=(52.00400,20.00400),(52.00300,20.00300)'], obj_id=4)
    merged, skipped, reversed_any = first.merged_with([second])
    assert merged.get_id() == 3
    assert skipped == [] and reversed_any
    assert merged.get_label1() == 'Prosta' and merged.get_type() == 0x6
    assert data0_line(merged) == ['Data0=(52.00000,20.00000),(52.00100,20.00100),(52.00200,20.00200),'
                                  '(52.00300,20.00300),(52.00400,20.00400)']
    assert merged.obj_bounding_box['N'] == pytest.approx(52.004)


def test_merged_with_disconnected_lines():
    first = make(Polyline, LINE)
    far = make(Polyline, ['[POLYLINE]', 'Type=0x1', 'Data0=(53.00000,21.00000),(53.00100,21.00100)'])
    with pytest.raises(MergeError):
        first.merged_with([far])
