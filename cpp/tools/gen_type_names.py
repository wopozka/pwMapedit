#!/usr/bin/env python3
"""Generuje cpp/gui/type_names.cpp z list typow w icons/*.py (nazwy typow POI, linii i polygonow do panelu
wlasciwosci). Pliki icons/*.py to same slowniki, wiec nie jest potrzebne PyQt6:  python gen_type_names.py

Roznica wzgledem Pythona: aliasy z type_2_alias sa dopasowywane numerycznie. Python porownywal tekst
str(hex(typ)) z kluczem, wiec klucze z zerem wiodacym ('0x0600') nigdy nie pasowaly i te aliasy ginely.
"""
import importlib.util
import os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
OUT = os.path.join(ROOT, 'cpp', 'gui', 'type_names.cpp')


def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, 'icons', name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def c_str(text):
    return '"' + text.replace('\\', '\\\\').replace('"', '\\"') + '"'


def main():
    icon_types = load('icons_names').icon_types
    aliases = {int(k, 16): v for k, v in load('type_aliases').type_2_alias.items()}
    names = load('line_polygon_names')
    out = ['// Plik generowany przez cpp/tools/gen_type_names.py z icons/*.py - nie edytowac recznie.',
           '#include "type_names.hpp"', '', 'namespace pwm::gui {', '',
           'const std::vector<PoiTypeName>& poi_type_names() {',
           '    static const std::vector<PoiTypeName> names = {']
    for poi_type, (category, name) in icon_types.items():
        alias = '/'.join(aliases.get(poi_type, [])).upper()
        out.append(f'        {{0x{poi_type:x}, {c_str(category)}, {c_str(name)}, {c_str(alias)}}},')
    out += ['    };', '    return names;', '}', '']
    for func, table in (('line_type_names', names.line_type_2_name), ('polygon_type_names', names.polygon_type_2_name)):
        out += [f'const std::vector<PolyTypeName>& {func}() {{',
                '    static const std::vector<PolyTypeName> names = {']
        for poly_type, (category, name_en, name_pl) in table.items():
            out.append(f'        {{0x{poly_type:x}, {c_str(category)}, {c_str(name_en)}, {c_str(name_pl or "")}}},')
        out += ['    };', '    return names;', '}', '']
    out += ['}  // namespace pwm::gui', '']
    with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(out))
    print(f'zapisano {OUT}')


if __name__ == '__main__':
    main()
