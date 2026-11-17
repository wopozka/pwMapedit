#!/bin/sh
# Dodaje pwMapEdit do menu aplikacji biezacego uzytkownika (bez roota).
# Uruchom z rozpakowanego katalogu pwMapEdit:  ./zainstaluj-skrot.sh
# Usuniecie skrotu:                             ./zainstaluj-skrot.sh --usun
set -e
DIR=$(cd "$(dirname "$0")" && pwd)
APPS="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
ICONS="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/scalable/apps"
if [ "$1" = "--usun" ]; then
    rm -f "$APPS/pwmapedit.desktop" "$ICONS/pwmapedit.svg"
    echo "Usunieto skrot pwMapEdit z menu."
    exit 0
fi
mkdir -p "$APPS" "$ICONS"
cp "$DIR/pwmapedit.svg" "$ICONS/pwmapedit.svg"
sed "s|^Exec=.*|Exec=\"$DIR/pwmapedit\" %f|" "$DIR/pwmapedit.desktop" > "$APPS/pwmapedit.desktop"
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$APPS" 2>/dev/null || true
echo "Dodano pwMapEdit do menu aplikacji (program: $DIR/pwmapedit)."
