#!/usr/bin/env bash
# Porownanie portu C++ z oryginalna wersja Python na pliku mp.
#   compare.sh <python_z_PyQt6> <plik.mp> <mptool>
# Sprawdza: zapis pliku (bajt w bajt), zrzut modelu danych (bity wspolrzednych, numeracja, hlevel)
# i operacje na numeracji (interpolacja, wyliczanie numeracji, podzial, odwracanie).
set -euo pipefail

PY="$1"
MP="$2"
MPTOOL="$3"
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$(mktemp -d "${TMPDIR:-/tmp}/pwm-compare.XXXXXX")"
export QT_QPA_PLATFORM=offscreen

status=0
check() {
    local name="$1" a="$2" b="$3"
    if cmp -s "$a" "$b"; then
        echo "  [ OK ] $name identyczne ($(wc -c <"$a") bajtow)"
    else
        echo "  [BLAD] $name rozne:"
        diff --text "$a" "$b" | head -20
        status=1
    fi
}

echo "Plik: $MP"
"$PY" -W ignore "$HERE/py_reference.py" roundtrip "$MP" "$OUT/py.mp" 2> "$OUT/py_err.txt" || { cat "$OUT/py_err.txt"; exit 1; }
grep '^python:' "$OUT/py_err.txt" | sed 's/^/  /'
"$MPTOOL" roundtrip "$MP" "$OUT/cpp.mp" 2>&1 | sed 's/^/  /'
check "zapis" "$OUT/py.mp" "$OUT/cpp.mp"

"$PY" -W ignore "$HERE/py_reference.py" dump "$MP" > "$OUT/py_dump.txt" 2>/dev/null
"$MPTOOL" dump "$MP" > "$OUT/cpp_dump.txt"
check "zrzut modelu" "$OUT/py_dump.txt" "$OUT/cpp_dump.txt"

"$PY" -W ignore "$HERE/py_reference.py" ops "$MP" > "$OUT/py_ops.txt" 2>/dev/null
"$MPTOOL" ops "$MP" > "$OUT/cpp_ops.txt"
check "operacje na numeracji" "$OUT/py_ops.txt" "$OUT/cpp_ops.txt"

if [ "$status" -eq 0 ]; then rm -rf "$OUT"; else echo "  wyniki w: $OUT"; fi
exit "$status"
