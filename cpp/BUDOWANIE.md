# Budowanie pwMapedit (C++) – Linux i Windows

Projekt składa się z:

| cel | co to jest | wymaga Qt6 |
|---|---|---|
| `pwmcore` | biblioteka rdzenia (wczytywanie/zapis MP, model danych, projekcje) | nie |
| `mptool` | narzędzie wiersza poleceń (`roundtrip`, `dump`, `ops`, `warnings`) | nie |
| `run_tests` | testy rdzenia | nie |
| `pwmapedit` | edytor z GUI | tak (Widgets, Concurrent, Network; SVG do ikon) |
| `gui_tests` | testy GUI (QtTest, bez okna) | tak (+ moduł Test) |

Biblioteka Clipper2 jest dołączona w `third_party/clipper2` i buduje się razem z projektem – nie trzeba jej instalować.

Wymagania: kompilator C++17 (GCC ≥ 11, Clang ≥ 14 albo MSVC 2022), CMake ≥ 3.21, Qt ≥ 6.2 (do GUI).
Wszystkie polecenia poniżej uruchamia się w katalogu `cpp/` repozytorium.

---

## Linux (Debian / Ubuntu)

### 1. Pakiety

```sh
sudo apt install build-essential cmake ninja-build qt6-base-dev qt6-svg-dev
```

Fedora: `sudo dnf install gcc-c++ cmake ninja-build qt6-qtbase-devel qt6-qtsvg-devel`
Arch: `sudo pacman -S base-devel cmake ninja qt6-base qt6-svg`

Jeśli potrzebny jest tylko rdzeń i `mptool`, wystarczy `build-essential` (i ewentualnie `cmake`).

### 2. Budowanie

```sh
cd cpp
cmake -S . -B build-cmake -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build-cmake
```

Bez Ninja można pominąć `-G Ninja` (CMake użyje wtedy Makefile); równoległość: `cmake --build build-cmake -j$(nproc)`.

W wyniku `cmake` powinien pojawić się Qt6. Komunikat `Nie znaleziono Qt6 (...) - GUI (pwmapedit) nie bedzie budowane`
oznacza brak pakietu `qt6-base-dev` albo `qt6-svg-dev` – wtedy powstaną tylko rdzeń, `mptool` i testy.

### 3. Testy i uruchomienie

```sh
ctest --test-dir build-cmake --output-on-failure   # testy rdzenia i GUI
build-cmake/pwmapedit [plik.mp]
```

Ikony są szukane automatycznie w katalogu `icons/` repozytorium (ścieżka jest wkompilowana), więc program
zbudowany z repozytorium działa od razu.

### Pakiety do wydania (AppImage i tar.gz)

```sh
cpp/packaging/linux/make_linux_release.sh            # oba pakiety do cpp/dist/
cpp/packaging/linux/make_linux_release.sh --only tar # tylko tar.gz
cpp/packaging/linux/make_linux_release.sh --version 2026-11-20
```

Skrypt buduje program w `cpp/build-release/`, uruchamia testy i tworzy w `cpp/dist/`:

- `pwMapEdit-<wersja>-x86_64.AppImage`: program z Qt, wtyczkami (xcb, jpeg, svg, TLS) i ikonami.
  Do złożenia używa `linuxdeploy` i `linuxdeploy-plugin-qt`, które pobiera przy pierwszym uruchomieniu do `cpp/build-release/tools/`.
- `pwMapEdit-<wersja>-linux-x86_64.tar.gz`: `pwmapedit`, `mptool`, `icons/`, plik `.desktop`, ikona,
  `zainstaluj-skrot.sh` i instrukcje. Korzysta z Qt6 zainstalowanego w systemie.

Wersja domyślnie to data z ostatniego tagu `pwmapedit-RRRR-MM-DD` i skrót commita, np. `2026-11-17-7b0d9b4` – tak jak w nazwach zipów dla Windows.
Pakiety działają tylko na systemach z glibc nie starszym niż ten, na którym je zbudowano; skrypt wypisuje
ten próg na końcu. Budowanie na Ubuntu 24.04 daje pakiety dla Ubuntu 24.04+, Debiana 13, Fedory 39+ i Archa.
Wymagania i instalację po stronie użytkownika opisuje [INSTALACJA.md](INSTALACJA.md).

### Wariant bez CMake (tylko rdzeń)

```sh
cd cpp
make            # build/libpwmcore.a, build/mptool, build/run_tests
make test       # testy rdzenia
make DEBUG=1    # wersja z AddressSanitizer/UBSan w build-debug/
```

---

## Windows 10/11 (64-bit)

Zalecana droga to **MSYS2 + MinGW** – wszystko (kompilator, CMake, Qt) instaluje się jednym poleceniem.
Alternatywa z Visual Studio jest opisana niżej.

### A. MSYS2 (MinGW-w64)

1. Zainstaluj MSYS2 ze strony <https://www.msys2.org> (domyślnie do `C:\msys64`).
2. Uruchom powłokę **MSYS2 MINGW64** (nie „MSYS2 MSYS” ani UCRT – ikona z napisem MINGW64) i zaktualizuj system:

   ```sh
   pacman -Syu
   ```

   Jeśli powłoka się zamknie, uruchom ją ponownie i powtórz `pacman -Syu`.
3. Zainstaluj narzędzia i Qt:

   ```sh
   pacman -S --needed git mingw-w64-x86_64-{gcc,cmake,ninja,qt6-base,qt6-svg,qt6-tools}
   ```

   (`qt6-tools` jest potrzebny tylko do `windeployqt6` w kroku 6.)
4. Pobierz źródła i zbuduj:

   ```sh
   git clone https://github.com/wopozka/pwMapedit.git
   cd pwMapedit/cpp
   git checkout cpp-port
   cmake -S . -B build-cmake -G Ninja -DCMAKE_BUILD_TYPE=Release
   cmake --build build-cmake
   ```

5. Testy i uruchomienie (w tej samej powłoce MINGW64 – biblioteki DLL są wtedy w `PATH`):

   ```sh
   ctest --test-dir build-cmake --output-on-failure
   build-cmake/pwmapedit.exe
   ```

6. **Samodzielny katalog do uruchamiania poza MSYS2** (np. do spakowania w zip):

   ```sh
   mkdir -p dist/pwMapEdit
   cp build-cmake/pwmapedit.exe dist/pwMapEdit/
   cp -r ../icons dist/pwMapEdit/
   windeployqt6 --release --no-translations dist/pwMapEdit/pwmapedit.exe
   # biblioteki MinGW, których windeployqt nie kopiuje:
   ldd dist/pwMapEdit/pwmapedit.exe | grep -i mingw64 | awk '{print $3}' | xargs -I{} cp {} dist/pwMapEdit/
   ```

   `windeployqt6` dokłada biblioteki Qt i wtyczki (platforma `qwindows`, style, formaty obrazów
   `qjpeg`/`qsvg` dla podkładów i ikon, backend TLS dla podkładów z internetu). Polecenie `ldd` kopiuje
   pozostałe DLL z MSYS2 (`libstdc++-6.dll`, `libgcc_s_seh-1.dll`, `libwinpthread-1.dll`, ICU, zlib, …).
   Gotowy folder `dist/pwMapEdit` można spakować i uruchamiać na innym komputerze bez instalacji.
   Sprawdź to, uruchamiając `pwmapedit.exe` z Eksploratora Windows (nie z MSYS2) – brakująca biblioteka
   pojawi się w komunikacie o błędzie.

### B. Visual Studio 2022 + oficjalny instalator Qt

1. Zainstaluj Visual Studio 2022 (wystarczy Build Tools) z obciążeniem **Programowanie aplikacji klasycznych w C++**
   (zawiera CMake i Ninja).
2. Zainstaluj Qt przez **Qt Online Installer** (<https://www.qt.io/download-qt-installer>): wersja Qt 6.x,
   komponent **MSVC 2022 64-bit** oraz moduł **Qt SVG** (w „Additional Libraries” nic więcej nie jest potrzebne).
3. Otwórz **x64 Native Tools Command Prompt for VS 2022** i zbuduj (ścieżkę do Qt dopasuj do zainstalowanej wersji):

   ```bat
   cd pwMapedit\cpp
   cmake -S . -B build-msvc -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH=C:\Qt\6.8.0\msvc2022_64
   cmake --build build-msvc
   set PATH=C:\Qt\6.8.0\msvc2022_64\bin;%PATH%
   ctest --test-dir build-msvc --output-on-failure
   ```

4. Samodzielny katalog:

   ```bat
   mkdir dist\pwMapEdit
   copy build-msvc\pwmapedit.exe dist\pwMapEdit\
   xcopy /E /I ..\icons dist\pwMapEdit\icons
   C:\Qt\6.8.0\msvc2022_64\bin\windeployqt.exe --release --no-translations dist\pwMapEdit\pwmapedit.exe
   ```

   `windeployqt` kopiuje też biblioteki uruchomieniowe Visual C++ (`vc_redist`), jeśli są dostępne;
   w przeciwnym razie na docelowym komputerze trzeba zainstalować „Microsoft Visual C++ Redistributable x64”.

Zamiast konsoli można otworzyć katalog `cpp` w Visual Studio (Plik → Otwórz → Folder) – projekt CMake zostanie
wykryty automatycznie; `CMAKE_PREFIX_PATH` ustawia się wtedy w `CMakeSettings.json` / `CMakePresets.json`.

---

## Opcje CMake

| opcja | domyślnie | znaczenie |
|---|---|---|
| `-DCMAKE_BUILD_TYPE=Release\|Debug\|RelWithDebInfo` | `Release` | typ budowania |
| `-DPWM_BUILD_GUI=OFF` | `ON` | nie buduj GUI, nawet jeśli Qt6 jest dostępne |
| `-DPWM_SYSTEM_CLIPPER2=ON` | `OFF` | użyj systemowego Clipper2 zamiast dołączonego |
| `-DCMAKE_PREFIX_PATH=<katalog Qt>` | – | gdzie szukać Qt6, jeśli nie jest w ścieżkach systemowych |

## Ikony

Program potrzebuje katalogu `icons` (z repozytorium). Szuka go kolejno w:

1. zmiennej środowiskowej `PWMAPEDIT_ICONS`,
2. `icons/` obok programu i do 3 katalogów wyżej,
3. `icons/` w bieżącym katalogu,
4. katalogu `icons/` repozytorium, z którego program zbudowano (ścieżka wkompilowana).

Przy dystrybucji programu (zip) katalog `icons` musi leżeć obok `pwmapedit.exe`.

## Typowe problemy

| objaw | przyczyna / rozwiązanie |
|---|---|
| `Nie znaleziono Qt6 (Widgets, Concurrent, Network, Svg) - GUI (pwmapedit) nie bedzie budowane` | brak Qt6 lub modułu Qt Svg w ścieżkach – zainstaluj `qt6-base-dev` i `qt6-svg-dev` (Linux), `mingw-w64-x86_64-qt6-base` i `mingw-w64-x86_64-qt6-svg` (MSYS2) albo podaj `-DCMAKE_PREFIX_PATH` |
| `gui_tests` nie powstaje | brak modułu Qt6 Test w zainstalowanym Qt – GUI i tak się zbuduje, nie będzie tylko testów GUI |
| na Windows: „nie znaleziono pliku …dll” | program uruchomiony poza MSYS2 bez kroku `windeployqt6` + `ldd` |
| „This application failed to start because no Qt platform plugin could be initialized” | brak katalogu `platforms/` obok exe – uruchom `windeployqt` |
| brak ikon na toolbarze / komunikat o katalogu icons | skopiuj `icons/` obok programu albo ustaw `PWMAPEDIT_ICONS` |
| podkłady z internetu się nie ładują (Windows) | brak katalogu `tls/` lub `imageformats/` obok exe – uruchom `windeployqt` |
| błąd „CMake 3.21 or higher is required” | zaktualizuj CMake (np. `pip install cmake` albo pakiet z kitware.com) |
