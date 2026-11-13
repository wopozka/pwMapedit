"""Odczyt i zapis pliku MP w rdzeniu (bez Qt)."""
import ast
import os.path

import pytest

from pwm_core import mp_file, projection
from pwm_core.map_object import Poi, Polyline, Polygon

TESTS_DIR = os.path.dirname(__file__)

HEADER = '''; naglowek
[IMG ID]
ID=1
Name=Test
[END-IMG ID]

'''

MAP_TEXT = HEADER + ''';komentarz obiektu
[POI]
Type=0x2f00
Label=Sklep
Data0=(52.10000,20.10000)
[END]

[POLYLINE]
Type=0x6
Label=Prosta
Data0=(52.00000,20.00000),(52.00100,20.00100),(52.00200,20.00200)
Numbers1=0,O,1,5,E,2,6
HLevel0=(1,1)
Miasto=Testowo
[END]

[RESTRICT]
Nod=1
TraffPoints=1,2,3
[END]

[POLYGON]
Type=0x3
Data0=(52.000000,20.000000),(52.000000,20.001000),(52.001000,20.001000)
[END]

;@File slad.gpx
;@WEBMAP osm

'''

# RESTRICT nie jest obslugiwany (znany brak), zalaczniki ;@ nie sa zapisywane
EXPECTED_SAVED = HEADER + ''';komentarz obiektu
[POI]
Type=0x2f00
Label=Sklep
Data0=(52.10000,20.10000)
[END]

[POLYLINE]
Type=0x6
Label=Prosta
Data0=(52.00000,20.00000),(52.00100,20.00100),(52.00200,20.00200)
Numbers1=0,O,1,5,E,2,6
HLevel0=(1,1)
Miasto=Testowo
[END]

[POLYGON]
Type=0x3
Data0=(52.000000,20.000000),(52.000000,20.001000),(52.001000,20.001000)
[END]

'''


def write_text(path, text):
    with open(path, 'w', encoding=mp_file.MP_ENCODING) as f:
        f.write(text)
    return str(path)


def read_text(path):
    with open(path, encoding=mp_file.MP_ENCODING) as f:
        return f.read()


def load(path):
    return mp_file.load_map_data(path, projection.Mercator({}))


def save_and_read(map_data, path):
    mp_file.write_mp_file(map_data, str(path))
    return read_text(path)


def test_reader_splits_header_records_and_attachments(tmp_path):
    reader = mp_file.MpFileReader(write_text(tmp_path / 'm.mp', MAP_TEXT))
    assert ''.join(reader.header) == HEADER
    assert reader.attachments == [';@File slad.gpx', ';@WEBMAP osm']
    records = list(reader.records())
    assert [r.kind for r in records] == ['[POI]', '[POLYLINE]', '[RESTRICT]', '[POLYGON]']
    assert records[0].comments == ['komentarz obiektu']


def test_load_creates_core_objects(tmp_path):
    map_data = load(write_text(tmp_path / 'm.mp', MAP_TEXT))
    objs = map_data.get_all_map_objects()
    assert [type(o) for o in objs] == [Poi, Polyline, Polygon]
    assert [o.get_id() for o in objs] == [0, 1, 2]
    assert map_data.listOfAttachments == [';@File slad.gpx', ';@WEBMAP osm']
    assert map_data.get_precision() == 6
    bbox = map_data.get_map_bounding_box()
    assert (bbox['S'], bbox['N'], bbox['W'], bbox['E']) == (52.0, 52.1, 20.0, 20.1)


def test_round_trip(tmp_path):
    map_data = load(write_text(tmp_path / 'm.mp', MAP_TEXT))
    assert save_and_read(map_data, tmp_path / 'out.mp') == EXPECTED_SAVED


def test_save_skips_deleted_objects_and_reports_progress(tmp_path):
    map_data = load(write_text(tmp_path / 'm.mp', MAP_TEXT))
    map_data.set_map_object_deleted(map_data.get_all_map_objects()[1])
    progress = []
    mp_file.write_mp_file(map_data, str(tmp_path / 'out.mp'), progress=progress.append)
    assert '[POLYLINE]' not in read_text(tmp_path / 'out.mp')
    assert progress == [1, 2, 3]


def test_last_record_without_end_and_trailing_comment(tmp_path):
    text = HEADER + '[POI]\nType=0x1\nData0=(52.00000,20.00000)\n[END]\n\n;tylko komentarz\n\n' \
                    '[POI]\nType=0x2\nData0=(52.00000,20.00000)\n'
    records = list(mp_file.MpFileReader(write_text(tmp_path / 'm.mp', text)).records())
    assert [[v for (_, k), v in r.fields.items() if k == 'Type'] for r in records] == [['0x1'], ['0x2']]
    # komentarz bez obiektu po [END] przypisuje sie do kolejnego obiektu
    assert records[1].comments == ['tylko komentarz']


def test_map_without_objects(tmp_path):
    map_data = load(write_text(tmp_path / 'm.mp', HEADER))
    assert not map_data.contains_data()
    # puste linie na koncu pliku sa pomijane przy wczytywaniu
    assert save_and_read(map_data, tmp_path / 'out.mp') == HEADER.rstrip('\n') + '\n'


def test_new_object_gets_map_precision(tmp_path):
    map_data = load(write_text(tmp_path / 'm.mp', MAP_TEXT))
    drawn = Poi(None, _projection=map_data.projection)
    drawn.set_type('0x2f01')
    drawn.set_datax('Data0', '(52.1234567891234,20.1234567891234)')
    map_data.add_map_object(drawn)
    assert 'Data0=(52.123457,20.123457)' in save_and_read(map_data, tmp_path / 'out.mp')


def _map_with_test_records(tmp_path):
    # tests/wynik.mp i rekordy obiektow z test_to_mp.py
    tree = ast.parse(open(os.path.join(TESTS_DIR, 'test_to_mp.py'), encoding='utf-8').read())
    records = next(ast.literal_eval(node.value) for node in tree.body
                   if isinstance(node, ast.Assign) and getattr(node.targets[0], 'id', '') == 'OBJ_TO_MP_TEST')
    text = read_text(os.path.join(TESTS_DIR, 'wynik.mp')).rstrip() + '\n\n'
    for record, _ in records:
        text += '\n'.join(record) + '\n[END]\n\n'
    return write_text(tmp_path / 'duza.mp', text)


@pytest.mark.filterwarnings('ignore::SyntaxWarning')
def test_saving_loaded_map_is_stable(tmp_path):
    first = save_and_read(load(_map_with_test_records(tmp_path)), tmp_path / 'out1.mp')
    second = save_and_read(load(str(tmp_path / 'out1.mp')), tmp_path / 'out2.mp')
    assert first == second
    # 13 obiektow i [END] tablicy [CYFRY] z naglowka wynik.mp
    assert first.count('[END]\n') == 14
