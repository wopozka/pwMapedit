#!/usr/bin/env python3
"""Uruchamia ORYGINALNY kod pwMapedit (Python) bez GUI, jako wzorzec dla portu C++.

Uzycie:
  py_reference.py roundtrip <wejscie.mp> <wyjscie.mp>   wczytaj i zapisz (MapFileOpener + MapFileSaver)
  py_reference.py dump <wejscie.mp>                     zrzut modelu danych (bity wspolrzednych, numeracja)
  py_reference.py ops <wejscie.mp>                      operacje na Data_X: reverse/split/interpolacja
  py_reference.py batch <lista.txt> <katalog>           wiele plikow: N.mp, N.dump, N.ops (lub N.err)

Wymaga PyQt6, uruchamiac z QT_QPA_PLATFORM=offscreen.
"""
import os
import struct
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

from PyQt6.QtWidgets import QApplication  # noqa: E402

app = QApplication.instance() or QApplication(['py_reference'])

import pwMapEdit  # noqa: E402
import map_items  # noqa: E402


def load(path):
    opener = pwMapEdit.MapFileOpener(None, path, None, None, None)
    objects = []
    result = {}

    def collect(objs, map_objects):
        objects.extend(objs)
        if map_objects is not None:
            result['map'] = map_objects

    opener.draw_poi_polyline_polygon.connect(collect)
    t0 = time.perf_counter()
    opener.wczytaj_rekordy()
    t1 = time.perf_counter()
    return result['map'], t1 - t0


def bits(v):
    return struct.unpack('<q', struct.pack('<d', v))[0]


def opt(v):
    return 'None' if v is None else str(v)


def dump_numbers(nd):
    if nd is None:
        return '-'
    return '|'.join(opt(v) for v in nd)


def dump_data(dx, out):
    if dx is None:
        out.append(' nodata')
        return
    out.append(' levels ' + ','.join(str(a) for a in dx.get_data_levels()))
    for lvl_idx, polys in enumerate(dx._poly_data_points):
        for poly_num, poly in enumerate(polys):
            out.append(f'  L{lvl_idx} P{poly_num} n={len(poly)}')
            for node in poly:
                hl = node.get_hlevel_definition()
                out.append(f'   {bits(node.x())} {bits(node.y())} h={opt(hl)} n={dump_numbers(node.get_numbers_definition())}')


def dump_text(mp):
    out = []
    for obj in mp.get_all_map_objects():
        out.append(f'OBJ {type(obj).__name__} id={obj.get_id()} type={obj.get_type()} end={obj.get_endlevel()} '
                   f'dir={opt(obj.dirindicator)} rp={opt(obj.routeparam)} roadid={opt(obj.roadid)} '
                   f'city={opt(obj.cityname)} zip={opt(obj.zipcode)}')
        out.append(f' bbox {obj.obj_bounding_box.get("S")} {obj.obj_bounding_box.get("N")} '
                   f'{obj.obj_bounding_box.get("W")} {obj.obj_bounding_box.get("E")}')
        dump_data(obj.data0, out)
    bb = mp.get_map_bounding_box()
    out.append(f'MAPBBOX {bb.get("S")} {bb.get("N")} {bb.get("W")} {bb.get("E")}')
    out.append(f'PRECISION {map_items.Data_X.precision}')
    return '\n'.join(out) + '\n'


def cmd_dump(path):
    mp, _ = load(path)
    sys.stdout.write(dump_text(mp))


def save(mp, out_path):
    mp.set_map_file_name(out_path)
    saver = pwMapEdit.MapFileSaver(None, mp)
    saver.run()


def cmd_roundtrip(path, out_path):
    mp, t_load = load(path)
    mp.set_map_file_name(out_path)
    saver = pwMapEdit.MapFileSaver(None, mp)
    t0 = time.perf_counter()
    saver.run()
    t1 = time.perf_counter()
    print(f'python: objects={mp.records_number()} load={t_load:.2f}s save={t1 - t0:.2f}s', file=sys.stderr)


def ops_text(mp):
    """Na kazdej polilinii z numeracja: interpolacja, wyliczona numeracja dla wezlow, split, reverse."""
    out = []
    prec = map_items.Data_X.precision
    for obj in mp.get_all_map_objects():
        if not isinstance(obj, map_items.PolylineQGraphicsPathItem) or obj.data0 is None:
            continue
        dx = obj.data0
        level = dx.get_data_levels()[0]
        if dx.get_data_level_index(level) != level:
            continue
        polys = dx.get_polys_for_data_level(level)
        if not any(n.node_has_numeration() for n in polys[0]):
            continue
        out.append(f'OBJ {obj.get_id()}')
        try:
            inter = dx.get_interpolated_housenumbers_for_poly(level, 0)
            for side in ('left', 'right'):
                for item in inter[side]:
                    out.append(f' I {side} {item.number} {bits(item.position.x())} {bits(item.position.y())}')
        except Exception as e:  # noqa: BLE001
            out.append(f' I EXC {type(e).__name__}')
        for node_num in range(len(polys[0])):
            try:
                d = dx.get_calculated_housenumber_defs_for_node(level, 0, node_num)
                out.append(f' C {node_num} {dump_numbers(d)}')
            except Exception as e:  # noqa: BLE001
                out.append(f' C {node_num} EXC {type(e).__name__}')
        for node_num in range(1, len(polys[0]) - 1):
            try:
                res = dx.split_data_x(level, 0, node_num)
                for part in res:
                    out.append(f' S {node_num} ' + ' # '.join(part.to_mp_record()))
            except Exception as e:  # noqa: BLE001
                out.append(f' S {node_num} EXC {type(e).__name__}')
        try:
            rev = dx.copy()
            rev.reverse_poly(level)
            out.append(' R ' + ' # '.join(rev.to_mp_record()))
        except Exception as e:  # noqa: BLE001
            out.append(f' R EXC {type(e).__name__}')
    out.append(f'PRECISION {prec}')
    return '\n'.join(out) + '\n'


def cmd_ops(path):
    mp, _ = load(path)
    sys.stdout.write(ops_text(mp))


def cmd_batch(list_file, out_dir):
    """Wiele plikow w jednym procesie. Dla pliku nr N zapisuje N.mp, N.dump, N.ops albo N.err.
    Data_X.precision jest globalna dla procesu - zerujemy ja przed kazdym plikiem, zeby wynik byl
    taki sam jak przy otwarciu pliku w swiezo uruchomionym programie."""
    with open(list_file, encoding='utf-8') as f:
        paths = [line.rstrip('\n') for line in f if line.strip()]
    for num, path in enumerate(paths):
        base = os.path.join(out_dir, str(num))
        map_items.Data_X.precision = 0
        try:
            mp, _ = load(path)
            save(mp, base + '.mp')
            with open(base + '.dump', 'w', encoding='cp1250', newline='\n') as f:
                f.write(dump_text(mp))
            with open(base + '.ops', 'w', encoding='cp1250', newline='\n') as f:
                f.write(ops_text(mp))
        except Exception as e:  # noqa: BLE001
            with open(base + '.err', 'w', encoding='utf-8') as f:
                f.write(f'{type(e).__name__}: {e}\n')
        if num % 100 == 0:
            print(f'python batch: {num}/{len(paths)}', file=sys.stderr)


if __name__ == '__main__':
    import builtins
    import io
    # wyjscie w cp1250 - tak jak bajty w pliku mp, zeby porownywac z C++ bajt w bajt
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='cp1250', newline='\n')
    _print = builtins.print
    # oryginalny kod drukuje duzo komunikatow diagnostycznych na stdout - kierujemy je na stderr
    builtins.print = lambda *a, **k: _print(*a, **{**k, 'file': k.get('file', sys.stderr)})
    cmd = sys.argv[1]
    # oryginalny kod laduje ikony sciezkami wzglednymi - pracujemy z katalogu repozytorium
    sys.argv[2:] = [os.path.abspath(a) for a in sys.argv[2:]]
    os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
    if cmd == 'roundtrip':
        cmd_roundtrip(sys.argv[2], sys.argv[3])
    elif cmd == 'dump':
        cmd_dump(sys.argv[2])
    elif cmd == 'ops':
        cmd_ops(sys.argv[2])
    elif cmd == 'batch':
        cmd_batch(sys.argv[2], sys.argv[3])
    else:
        sys.exit(__doc__)
    sys.stdout.flush()
