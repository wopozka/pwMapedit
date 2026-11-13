# -*- coding: utf-8 -*-
"""Odczyt i zapis pliku MP (polish format).

Plik sklada sie z naglowka (np. [IMG ID] ... [END-IMG ID]), rekordow obiektow zakonczonych [END] oraz opcjonalnych
zalacznikow na koncu pliku (linie ;@File ..., ;@WEBMAP ...).
"""
from collections import namedtuple

from pwm_core import mp_format
from pwm_core.map_data import MapData
from pwm_core.map_object import Poi, Polyline, Polygon

MP_ENCODING = 'cp1250'

# kind: '[POI]', '[POLYLINE]', '[POLYGON]', '[RESTRICT]', '[SIGN]'; comments i fields jak w
# mp_format.map_strings_record_to_dict_record; line_num: numer linii pliku, na ktorej konczy sie rekord
MpRecord = namedtuple('MpRecord', ['kind', 'comments', 'fields', 'line_num'])

CORE_OBJECT_CLASSES = {
    mp_format.MAP_OBJECT_POI: Poi,
    mp_format.MAP_OBJECT_POLYLINE: Polyline,
    mp_format.MAP_OBJECT_POLYGON: Polygon,
}


class MpFileReader(object):
    """Czyta plik MP. Naglowek i zalaczniki sa dostepne od razu, rekordy obiektow zwraca generator records(),
    zeby przy duzych mapach nie trzymac w pamieci wszystkich rekordow naraz."""

    def __init__(self, filename=None, lines=None):
        if lines is None:
            with open(filename, 'r', encoding=MP_ENCODING) as mp_file:
                lines = mp_file.readlines()
        lines = list(lines)
        # zalaczniki na koncu pliku: ;@File * (pliki), ;@WEBMAP * (warstwy www)
        attachments = []
        while lines and (lines[-1].startswith(';@') or not lines[-1].strip()):
            if lines[-1].startswith(';@'):
                attachments.insert(0, lines[-1].strip())
            del lines[-1]
        self._lines = lines
        self.attachments = attachments
        self.line_count = len(lines)
        self._body_start = self._find_body_start()
        # naglowek zapisujemy z powrotem do pliku bez zmian, dlatego linie zostaja z koncami linii
        self.header = lines[:self._body_start]

    def _find_body_start(self):
        # pierwszy obiekt; komentarze tuz przed nim naleza do obiektu, nie do naglowka
        first_object = next((num for num, line in enumerate(self._lines)
                             if line.strip() in mp_format.MAP_OBJECT_TYPES), len(self._lines))
        start = first_object
        while start > 0 and self._lines[start - 1].strip().startswith(';'):
            start -= 1
        return start

    def records(self):
        record = []
        for line_num in range(self._body_start, self.line_count):
            line = self._lines[line_num]
            if line.strip().startswith(mp_format.MAP_OBJECT_END):
                parsed = self._parse(record, line_num)
                if parsed is not None:
                    yield parsed
                record = []
            else:
                record.append(line)
        # ostatni rekord bez [END]
        parsed = self._parse(record, self.line_count - 1)
        if parsed is not None:
            yield parsed

    @staticmethod
    def _parse(record, line_num):
        if not any(line.strip() for line in record):
            return None
        poi_poly_type, comments, fields = mp_format.map_strings_record_to_dict_record(record)
        if not poi_poly_type:
            # same komentarze albo smieci bez sekcji obiektu
            return None
        return MpRecord(poi_poly_type[0], comments, fields, line_num)


def create_map_object(record, object_classes=None, map_objects_properties=None, projection=None):
    """Tworzy obiekt mapy z rekordu. object_classes: slownik rodzaj rekordu -> klasa obiektu (GUI podaje swoje
    klasy). Zwraca None dla rekordow, ktorych nie obslugujemy ([RESTRICT], [SIGN])."""
    if object_classes is None:
        object_classes = CORE_OBJECT_CLASSES
    obj_class = object_classes.get(record.kind)
    if obj_class is None:
        return None
    map_object = obj_class(None, map_objects_properties=map_objects_properties, _projection=projection)
    map_object.set_data(record.comments, record.fields)
    return map_object


def add_object_to_map(map_data, map_object):
    map_data.add_map_object(map_object)
    map_data.set_map_bounding_box(map_object.obj_bounding_box)


def new_map_data(reader, filename, map_objects_properties=None, projection=None):
    map_data = MapData(filename, map_objects_properties=map_objects_properties, projection=projection)
    map_data.map_header = list(reader.header)
    map_data.listOfAttachments = list(reader.attachments)
    return map_data


def load_map_data(filename, projection, object_classes=None, map_objects_properties=None):
    """Wczytuje cala mape do MapData (bez GUI)."""
    reader = MpFileReader(filename)
    map_data = new_map_data(reader, filename, map_objects_properties=map_objects_properties, projection=projection)
    for record in reader.records():
        map_object = create_map_object(record, object_classes=object_classes,
                                       map_objects_properties=map_objects_properties, projection=projection)
        if map_object is not None:
            add_object_to_map(map_data, map_object)
    return map_data


def map_object_mp_lines(map_object, default_precision=None):
    """Linie rekordu obiektu w pliku MP, razem z [END] i pusta linia oddzielajaca."""
    return [line + '\n' for line in map_object.to_mp_record(default_precision)] + [mp_format.MAP_OBJECT_END + '\n',
                                                                                   '\n']


def write_mp_file(map_data, filename=None, progress=None):
    """Zapisuje mape do pliku (domyslnie do pliku mapy). progress(n) jest wywolywane po kazdym obiekcie.
    Zalaczniki (;@File, ;@WEBMAP) nie sa zapisywane."""
    if filename is None:
        filename = map_data.get_map_file_name()
    precision = map_data.get_precision()
    with open(filename, 'w', encoding=MP_ENCODING) as map_file:
        map_file.writelines(map_data.map_header)
        for map_object_num, map_object in enumerate(map_data.get_all_map_objects()):
            if map_object is not None and not map_object.is_deleted():
                map_file.writelines(map_object_mp_lines(map_object, precision))
            if progress is not None:
                progress(map_object_num + 1)
