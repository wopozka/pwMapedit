#!/usr/bin/env python3
"""Generuje cpp/tests/py_cases.inc z danych testowych w tests/*.py (oryginalne testy Pythona).

Uruchamiac interpreterem z PyQt6:  QT_QPA_PLATFORM=offscreen python gen_py_cases.py
"""
import importlib.util
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
sys.path.insert(0, ROOT)


def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, 'tests', name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def lit(s):
    assert ')PWM"' not in s
    return 'R"PWM(' + s + ')PWM"'


def str_list(items):
    return '{' + ', '.join(lit(s) for s in items) + '}'


out = ['// WYGENEROWANE przez cpp/tools/gen_py_cases.py z tests/*.py - nie edytowac recznie.',
       '#pragma once', '#include <string>', '#include <utility>', '#include <vector>', '',
       'struct StrListCase { std::vector<std::string> target; std::vector<std::string> answer; };',
       'struct IconCase { std::vector<std::string> target; std::pair<std::string, std::string> answer; };', '']

to_mp = load('test_to_mp')
out.append('inline const std::vector<StrListCase> DATA_TO_MP_CASES = {')
for target, answer in to_mp.DATA_TEST:
    out.append('    {' + str_list(target) + ', ' + str_list(answer) + '},')
out.append('};')
out.append('inline const std::vector<StrListCase> OBJ_TO_MP_CASES = {')
for target, answer in to_mp.OBJ_TO_MP_TEST:
    out.append('    {' + str_list(target) + ', ' + str_list(answer) + '},')
out.append('};')

misc = load('test_misc_functions')
out.append('inline const std::vector<IconCase> ICON_CASES = {')
for target, answer in misc.TEST_RETURN_ICON_DEFINITION:
    out.append('    {' + str_list(target) + ', {' + lit(answer[0]) + ', ' + lit(answer[1]) + '}},')
out.append('};')

# Wzorcowa tablica cp1250 z codeca Pythona: dla kazdego bajtu kod Unicode albo 0, gdy bajt niezdefiniowany.
codes = []
for b in range(256):
    try:
        codes.append(str(ord(bytes([b]).decode('cp1250'))))
    except UnicodeDecodeError:
        codes.append('0')
out.append('inline const unsigned CP1250_EXPECTED[256] = {' + ', '.join(codes) + '};')

path = os.path.join(ROOT, 'cpp', 'tests', 'py_cases.inc')
with open(path, 'w', encoding='utf-8', newline='\n') as f:
    f.write('\n'.join(out) + '\n')
print('zapisano', path, file=sys.stderr)
