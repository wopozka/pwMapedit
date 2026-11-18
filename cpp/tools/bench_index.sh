#!/bin/bash
# Pomiar indeksu sceny: kazdy wariant w osobnym procesie, wyniki dopisywane do jednego pliku.
# uzycie: cpp/tools/bench_index.sh mapa.mp wyniki.txt [program] [warianty...]
#   wariant = "indeks:glebokosc", np. none:0 bsp:8 bsp-toggle:10 bsp:0 (0 = glebokosc automatyczna Qt)
# Na Windows (msys2) przed uruchomieniem: export PATH=/c/msys64/mingw64/bin:$PATH
MAP=$1
OUT=$2
EXE=${3:-cpp/build-cmake/pwmapedit.exe}
shift 3 2>/dev/null || shift $#
VARIANTS=${*:-"none:0 bsp:6 bsp:8 bsp:10 bsp:12 bsp-toggle:8 bsp-toggle:10"}
for v in $VARIANTS; do
    index=${v%%:*}
    depth=${v##*:}
    echo "wariant $index, glebokosc $depth"
    start=$(date +%s)
    "$EXE" "$MAP" --bench "$OUT" --index "$index" --bsp-depth "$depth" || echo "=== $index:$depth - blad (kod $?)" >> "$OUT"
    echo "  $(( $(date +%s) - start )) s"
done
