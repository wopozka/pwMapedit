# pwMapEdit – instalacja

Gotowe pakiety są na stronie [wydań](https://github.com/wopozka/pwMapedit/releases):

| plik | system |
|---|---|
| `pwMapEdit-<wersja>-win64.zip` | Windows 10/11 64-bit |
| `pwMapEdit-<wersja>-x86_64.AppImage` | Linux – jeden plik, działa bez instalowania bibliotek (zalecany) |
| `pwMapEdit-<wersja>-linux-x86_64.tar.gz` | Linux – mały pakiet, korzysta z Qt6 zainstalowanego w systemie |

Program nie wymaga instalatora ani uprawnień administratora. Usunięcie programu to usunięcie jego pliku albo katalogu.

---

## Windows

1. Pobierz `pwMapEdit-<wersja>-win64.zip`.
2. Rozpakuj **cały** folder `pwMapEdit` w dowolne miejsce, np. `C:\Programy\pwMapEdit` albo na pulpit.
   Program potrzebuje plików DLL i folderu `icons`, które leżą obok `pwmapedit.exe`. Nie uruchamiaj go bezpośrednio z okna
   archiwum zip i nie przenoś samego `pwmapedit.exe`.
3. Uruchom `pwmapedit.exe`. Skrót: prawy przycisk na `pwmapedit.exe` → *Pokaż więcej opcji* → *Wyślij do* →
   *Pulpit (utwórz skrót)*.

Jeśli Windows pokaże „System Windows ochronił ten komputer” (program nie ma podpisu cyfrowego), kliknij
*Więcej informacji* → *Uruchom mimo to*.

Aktualizacja: usuń stary folder i rozpakuj nowy w to samo miejsce.

---

## Linux – AppImage (zalecany)

Jeden plik z programem, ikonami i bibliotekami Qt w środku. Nie trzeba instalować Qt ani innych pakietów.

### Wymagania

- komputer 64-bit (x86_64);
- glibc ≥ 2.38 i libstdc++ z GCC ≥ 13. Spełniają to m.in. Ubuntu 24.04 i nowsze (oraz Linux Mint 22, Pop!_OS 24.04),
  Debian 13, Fedora 39 i nowsze, Arch / Manjaro, openSUSE Tumbleweed;
- **FUSE 2** do uruchamiania plików AppImage (w większości dystrybucji jest domyślnie). Gdy go brak:
  - Ubuntu 24.04 / Debian 13: `sudo apt install libfuse2t64`
  - Fedora: `sudo dnf install fuse fuse-libs`
  - Arch: `sudo pacman -S fuse2`

  Bez FUSE program da się uruchomić poleceniem `./pwMapEdit-<wersja>-x86_64.AppImage --appimage-extract-and-run`;
- środowisko graficzne X11 albo Wayland (na Waylandzie program działa przez XWayland).

### Instalacja

```sh
mkdir -p ~/Aplikacje
mv ~/Pobrane/pwMapEdit-*-x86_64.AppImage ~/Aplikacje/
chmod +x ~/Aplikacje/pwMapEdit-*-x86_64.AppImage
~/Aplikacje/pwMapEdit-*-x86_64.AppImage [plik.mp]
```

Zamiast `chmod` można w menedżerze plików otworzyć *Właściwości* pliku → *Uprawnienia* i zaznaczyć *Zezwól na
uruchamianie jako program*, a potem uruchomić go dwuklikiem.

**Skrót w menu aplikacji (opcjonalnie).** Najprościej przez program *Gear Lever* (Flathub) albo *AppImageLauncher*,
które same dodają AppImage do menu. Ręcznie:

```sh
APP=$(ls ~/Aplikacje/pwMapEdit-*-x86_64.AppImage | tail -1)
mkdir -p ~/.local/share/applications
cat > ~/.local/share/applications/pwmapedit.desktop <<EOF
[Desktop Entry]
Type=Application
Name=pwMapEdit
Comment=Edytor map w formacie MP
Exec="$APP" %f
Terminal=false
Categories=Science;Geography;
EOF
```

**Aktualizacja:** usuń stary plik `.AppImage`, a na jego miejsce wstaw nowy, jak przy instalacji. Jeśli skrót był tworzony ręcznie,
popraw w nim nazwę pliku (albo nadawaj plikowi stałą nazwę, np. `pwMapEdit.AppImage`).
**Usunięcie:** skasuj plik `.AppImage` i ewentualnie `~/.local/share/applications/pwmapedit.desktop`.

---

## Linux – tar.gz

Sam program (ok. 1 MB po spakowaniu) z ikonami i narzędziem wiersza poleceń `mptool`. Biblioteki Qt6 pochodzą z
dystrybucji, więc pakiet jest mały i korzysta z wyglądu i poprawek systemowego Qt.

### Wymagania

- komputer 64-bit (x86_64), glibc ≥ 2.38, libstdc++ z GCC ≥ 13 – te same dystrybucje co przy AppImage;
- **Qt ≥ 6.4** z modułami Widgets, Network i SVG, z dystrybucji:

  | dystrybucja | polecenie |
  |---|---|
  | Ubuntu 24.04+, Mint 22+, Debian 13 | `sudo apt install libqt6widgets6 libqt6network6 libqt6svg6` |
  | Fedora 39+ | `sudo dnf install qt6-qtbase-gui qt6-qtsvg` |
  | Arch / Manjaro | `sudo pacman -S qt6-base qt6-svg` |

  Na pulpitach KDE Plasma 6 te biblioteki zwykle już są zainstalowane.

### Instalacja

```sh
mkdir -p ~/Aplikacje
tar -xzf ~/Pobrane/pwMapEdit-*-linux-x86_64.tar.gz -C ~/Aplikacje
cd ~/Aplikacje/pwMapEdit-*-linux-x86_64
./pwmapedit [plik.mp]
./zainstaluj-skrot.sh          # opcjonalnie: dodaje pwMapEdit do menu aplikacji (bez roota)
```

Katalog `icons` musi zostać obok programu `pwmapedit`. Nie przenoś samego pliku `pwmapedit`, tylko cały katalog.
Skrót w menu wskazuje katalog, w którym go utworzono. Po przeniesieniu katalogu uruchom `./zainstaluj-skrot.sh` ponownie.

Jeśli program nie startuje i pokazuje błąd o brakującej bibliotece `libQt6…so.6` albo o wtyczce platformy „xcb”,
brakuje pakietów Qt z tabeli wyżej. Listę brakujących bibliotek pokaże `ldd ./pwmapedit | grep "not found"`.

**Aktualizacja:** rozpakuj nowy pakiet i uruchom w nim `./zainstaluj-skrot.sh`, a potem usuń stary katalog.
**Usunięcie:** w katalogu programu uruchom `./zainstaluj-skrot.sh --usun`, a potem usuń katalog.

---

## Który pakiet wybrać na Linuksie?

| | AppImage | tar.gz |
|---|---|---|
| rozmiar | ok. 35 MB | ok. 1 MB |
| trzeba doinstalować Qt6 | nie | tak (Qt ≥ 6.4) |
| trzeba doinstalować FUSE | czasem (`libfuse2`) | nie |
| wygląd | według Qt dołączonego do programu | zgodny z systemowym Qt (np. motyw KDE) |
| poprawki bezpieczeństwa Qt/OpenSSL | z nowym wydaniem pwMapEdit | z aktualizacjami systemu |
| `mptool` (narzędzie CLI) | nie | tak |

Jeśli nie wiesz, który wybrać, pobierz AppImage.

---

Budowanie ze źródeł: [BUDOWANIE.md](BUDOWANIE.md). Tworzenie pakietów dla Linuksa:
`cpp/packaging/linux/make_linux_release.sh` (opis w BUDOWANIE.md).
