#!/usr/bin/env bash
# Porownanie C++ z Pythonem na wielu plikach mp, paczkami (oszczednie dla dysku).
#   compare_batch.sh <python_z_PyQt6> <lista_plikow.txt> <mptool> [rozmiar_paczki]
# Dla kazdego pliku porownuje zapis, zrzut modelu i operacje na numeracji; po kazdej paczce
# usuwa wyniki. Pliki, na ktorych Python rzuca wyjatek, sa liczone osobno (C++ wczytuje je dalej).
# Pliki zrodlowe UMP (src/*.txt) czesto nie maja naglowka - loader Pythona wtedy sie wywraca
# (IndexError). Dlatego obie wersje dostaja kopie z dopisanym minimalnym naglowkiem [IMG ID].
set -uo pipefail

PY="$1"
LIST="$2"
MPTOOL="$(realpath "$3")"
CHUNK="${4:-100}"
HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/pwm-batch.XXXXXX")"
REPORT="${TMPDIR:-/tmp}/compare_batch_report.txt"
export QT_QPA_PLATFORM=offscreen

total=0 same=0 diff_files=0 py_err=0 cpp_err=0
: > "$REPORT"
split -l "$CHUNK" -d -a 4 "$LIST" "$WORK/chunk."
for chunk in "$WORK"/chunk.*; do
    rm -rf "$WORK/py" "$WORK/cpp" "$WORK/in"
    mkdir -p "$WORK/py" "$WORK/cpp" "$WORK/in"
    : > "$WORK/padded.list"
    n=0
    while IFS= read -r path; do
        [ -z "$path" ] && continue
        { printf '[IMG ID]\r\nName=pwm-compare\r\n[END-IMG ID]\r\n\r\n'; cat "$path"; } > "$WORK/in/$n.mp"
        echo "$WORK/in/$n.mp" >> "$WORK/padded.list"
        n=$((n + 1))
    done < "$chunk"
    "$PY" -W ignore "$HERE/py_reference.py" batch "$WORK/padded.list" "$WORK/py" 2>/dev/null
    "$MPTOOL" batch "$WORK/padded.list" "$WORK/cpp" 2>/dev/null
    n=0
    while IFS= read -r path; do
        [ -z "$path" ] && continue
        total=$((total + 1))
        if [ -f "$WORK/py/$n.err" ]; then
            py_err=$((py_err + 1))
            echo "PYERR $path: $(cat "$WORK/py/$n.err")" >> "$REPORT"
            if [ -f "$WORK/cpp/$n.err" ]; then
                echo "  i C++ tez: $(cat "$WORK/cpp/$n.err")" >> "$REPORT"
            fi
        elif [ -f "$WORK/cpp/$n.err" ]; then
            cpp_err=$((cpp_err + 1))
            echo "CPPERR $path: $(cat "$WORK/cpp/$n.err")" >> "$REPORT"
        else
            ok=1
            for ext in mp dump ops; do
                if ! cmp -s "$WORK/py/$n.$ext" "$WORK/cpp/$n.$ext"; then
                    ok=0
                    echo "DIFF $ext $path" >> "$REPORT"
                    diff --text "$WORK/py/$n.$ext" "$WORK/cpp/$n.$ext" | head -6 | cut -c1-200 >> "$REPORT"
                fi
            done
            if [ "$ok" -eq 1 ]; then same=$((same + 1)); else diff_files=$((diff_files + 1)); fi
        fi
        n=$((n + 1))
    done < "$chunk"
    echo "postep: $total plikow, identyczne $same, rozne $diff_files, blad Python $py_err, blad C++ $cpp_err"
done
rm -rf "$WORK"
echo "WYNIK: $total plikow, identyczne $same, rozne $diff_files, blad Python $py_err, blad C++ $cpp_err"
echo "szczegoly: $(realpath "$REPORT")"
