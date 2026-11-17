#!/bin/bash
# Buduje wydanie pwMapEdit dla Linuksa: AppImage i tar.gz.
#
#   cpp/packaging/linux/make_linux_release.sh [opcje]
#
#   --version V    wersja w nazwach plikow (domyslnie <data z tagu>-<commit>, np. 2026-11-17-7b0d9b4)
#   --only tar|appimage   zbuduj tylko jeden pakiet
#   --out DIR      katalog na gotowe pakiety (domyslnie cpp/dist)
#   --work DIR     katalog roboczy: budowanie, narzedzia linuxdeploy (domyslnie cpp/build-release)
#   --no-tests     pomin ctest
#
# Zmienne: QMAKE - qmake z Qt6 uzywanym do AppImage (domyslnie qmake6 albo qmake z PATH),
#          CMAKE_PREFIX_PATH - gdzie szukac Qt6 (gdy nie systemowe).
#
# Wynik:
#   pwMapEdit-<wersja>-x86_64.AppImage       - Qt w srodku, dziala bez instalowania Qt
#   pwMapEdit-<wersja>-linux-x86_64.tar.gz   - sam program + ikony, wymaga Qt6 z dystrybucji
set -euo pipefail

HERE=$(cd "$(dirname "$0")" && pwd)
CPP=$(cd "$HERE/../.." && pwd)
REPO=$(cd "$CPP/.." && pwd)

VERSION=""
ONLY=""
OUT="$CPP/dist"
WORK="$CPP/build-release"
TESTS=1
while [ $# -gt 0 ]; do
    case "$1" in
        --version) VERSION="$2"; shift 2 ;;
        --only) ONLY="$2"; shift 2 ;;
        --out) OUT="$2"; shift 2 ;;
        --work) WORK="$2"; shift 2 ;;
        --no-tests) TESTS=0; shift ;;
        -h|--help) sed -n '2,19p' "$0"; exit 0 ;;
        *) echo "Nieznana opcja: $1" >&2; exit 2 ;;
    esac
done
case "$ONLY" in ""|tar|appimage) ;; *) echo "--only: tar albo appimage" >&2; exit 2 ;; esac
if [ -z "$VERSION" ]; then
    # Jak przy wydaniach Windows: <data z ostatniego tagu pwmapedit-RRRR-MM-DD>-<skrot commita>[-dirty]
    TAG=$(git -C "$REPO" describe --tags --abbrev=0 --match 'pwmapedit-*' 2>/dev/null || echo "pwmapedit-$(date +%Y-%m-%d)")
    VERSION="${TAG#pwmapedit-}-$(git -C "$REPO" rev-parse --short=7 HEAD)"
    [ -z "$(git -C "$REPO" status --porcelain)" ] || VERSION="$VERSION-dirty"
fi
ARCH=$(uname -m)
mkdir -p "$OUT" "$WORK"
OUT=$(cd "$OUT" && pwd)
WORK=$(cd "$WORK" && pwd)

echo "== pwMapEdit $VERSION ($ARCH) -> $OUT"

# ---------- budowanie ----------
BUILD="$WORK/build"
GEN=()
command -v ninja >/dev/null 2>&1 && GEN=(-G Ninja)
cmake -S "$CPP" -B "$BUILD" "${GEN[@]}" -DCMAKE_BUILD_TYPE=Release
cmake --build "$BUILD" -j"$(nproc)"
[ -x "$BUILD/pwmapedit" ] || { echo "Nie zbudowano pwmapedit - brak Qt6? (zobacz komunikaty cmake)" >&2; exit 1; }
if [ "$TESTS" = 1 ]; then
    ctest --test-dir "$BUILD" --output-on-failure
fi

# Katalog icons z repozytorium bez plikow Pythona.
copy_icons() {
    (cd "$REPO" && tar cf - --exclude=__pycache__ --exclude='*.py' icons) | (cd "$1" && tar xf -)
}

# ---------- tar.gz ----------
if [ "$ONLY" != appimage ]; then
    NAME="pwMapEdit-$VERSION-linux-$ARCH"
    STAGE="$WORK/stage/$NAME"
    rm -rf "$WORK/stage"
    mkdir -p "$STAGE"
    install -m755 -s "$BUILD/pwmapedit" "$STAGE/pwmapedit"
    install -m755 -s "$BUILD/mptool" "$STAGE/mptool"
    copy_icons "$STAGE"
    install -m644 "$HERE/pwmapedit.desktop" "$HERE/pwmapedit.svg" "$STAGE/"
    install -m755 "$HERE/zainstaluj-skrot.sh" "$STAGE/"
    install -m644 "$REPO/LICENSE" "$CPP/INSTRUKCJA.md" "$CPP/INSTALACJA.md" "$STAGE/"
    tar -C "$WORK/stage" -czf "$OUT/$NAME.tar.gz" --owner=0 --group=0 "$NAME"
    echo "== tar.gz: $OUT/$NAME.tar.gz"
fi

# ---------- AppImage ----------
if [ "$ONLY" != tar ]; then
    TOOLS="$WORK/tools"
    mkdir -p "$TOOLS"
    for t in linuxdeploy/linuxdeploy linuxdeploy/linuxdeploy-plugin-qt; do
        f="$TOOLS/$(basename "$t")-$ARCH.AppImage"
        if [ ! -x "$f" ]; then
            echo "== pobieranie $(basename "$f")"
            curl -fL --retry 3 -o "$f.part" \
                "https://github.com/linuxdeploy/$(basename "$t")/releases/download/continuous/$(basename "$t")-$ARCH.AppImage"
            chmod +x "$f.part" && mv "$f.part" "$f"
        fi
    done

    if [ -z "${QMAKE:-}" ]; then
        QMAKE=$(command -v qmake6 || command -v qmake || true)
    fi
    [ -n "$QMAKE" ] || { echo "Nie znaleziono qmake z Qt6 (ustaw QMAKE)" >&2; exit 1; }
    export QMAKE

    APPDIR="$WORK/AppDir"
    rm -rf "$APPDIR"
    mkdir -p "$APPDIR/usr/bin"
    install -m755 "$BUILD/pwmapedit" "$APPDIR/usr/bin/pwmapedit"
    # Program szuka icons/ obok siebie i do 3 katalogow wyzej - usr/icons jest o jeden wyzej niz usr/bin.
    copy_icons "$APPDIR/usr"

    # Wtyczki Qt ladowane dynamicznie (nie wynikaja z linkowania): SVG (ikony, formaty obrazow).
    export EXTRA_QT_MODULES="svg"
    export EXTRA_QT_PLUGINS="svg"
    # linuxdeploy sam jest AppImage - uruchamiamy go bez FUSE.
    export APPIMAGE_EXTRACT_AND_RUN=1
    export LINUXDEPLOY_OUTPUT_VERSION="$VERSION"
    APPIMAGE="pwMapEdit-$VERSION-$ARCH.AppImage"
    export OUTPUT="$APPIMAGE"
    (cd "$WORK" && "$TOOLS/linuxdeploy-$ARCH.AppImage" --appdir "$APPDIR" \
        --executable "$APPDIR/usr/bin/pwmapedit" \
        --desktop-file "$HERE/pwmapedit.desktop" \
        --icon-file "$HERE/pwmapedit.svg" \
        --plugin qt --output appimage)
    mv -f "$WORK/$APPIMAGE" "$OUT/$APPIMAGE"
    echo "== AppImage: $OUT/$APPIMAGE"
fi

# Minimalne wersje glibc/libstdc++ wymagane przez program (i biblioteki w AppImage, ktore pochodza z tego systemu).
FILES=("$BUILD/pwmapedit")
[ -d "$WORK/AppDir/usr/lib" ] && [ "$ONLY" != tar ] && FILES+=("$WORK"/AppDir/usr/lib/*.so*)
need() { for f in "${FILES[@]}"; do objdump -T "$f" 2>/dev/null; done | grep -o "$1[0-9.]*" | sort -uV | tail -n1; }
echo "== Wymagane na docelowym systemie: $(need GLIBC_2\\.) i $(need GLIBCXX_3\\.4\\.) (libstdc++)."
