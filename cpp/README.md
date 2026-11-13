# pwMapedit – port C++ (etap 1: rdzeń bez GUI)

Rdzeń edytora map w C++17, bez zależności od Qt: wczytywanie i zapis plików MP, model danych
(węzły, poziomy Data0–4, numeracja adresowa, HLevel), operacje edycyjne (wstawianie/usuwanie węzłów,
odwracanie, dzielenie linii), projekcje (Mercator, UTM, Direct) i funkcje pomocnicze.

Zasada etapu 1: **zachowanie 1:1 z wersją Python**. Port daje te same pliki bajt w bajt i ten sam model
danych bit w bit. Błędy znalezione w oryginale są opisane niżej i świadomie nie zostały poprawione
(poza miejscami, w których Python kończył się wyjątkiem). Poprawki to osobny krok, po decyzji.

## Budowanie i testy

```sh
cd cpp
make            # build/libpwmcore.a, build/mptool, build/run_tests
make test       # testy jednostkowe
make DEBUG=1    # wersja z AddressSanitizer/UBSan w build-debug/
```

Wymagany tylko g++ ≥ 11 (C++17 z `std::from_chars`/`std::to_chars` dla double) i make.

## Porównanie z wersją Python

```sh
make compare PY=/ścieżka/do/python-z-PyQt6 MP=/ścieżka/do/mapy.mp
```

`tools/compare.sh` uruchamia **oryginalny** kod (`MapFileOpener`, `MapFileSaver`, `Data_X`) przez
`tools/py_reference.py` (bez okna, `QT_QPA_PLATFORM=offscreen`) i porównuje z `mptool`:

| porównanie | co obejmuje |
|---|---|
| zapis | plik po wczytaniu i zapisaniu, bajt w bajt |
| zrzut modelu | każdy obiekt: typ, EndLevel, RouteParam…, bounding box, a dla każdego węzła bity współrzędnych, HLevel i pełna definicja numeracji |
| operacje na numeracji | dla każdej polilinii z numeracją: interpolacja numerów (pozycje bit w bit), wyliczona numeracja w każdym węźle, podział w każdym węźle wewnętrznym, odwrócenie |

Wiele plików naraz (np. wszystkie źródła UMP), paczkami, z usuwaniem wyników po każdej paczce:

```sh
find ~/ump -path '*/src/*.txt' | sort > lista.txt
tools/compare_batch.sh /ścieżka/do/python-z-PyQt6 lista.txt build/mptool 100
```

Pliki źródłowe UMP zwykle nie mają nagłówka, a na takich plikach loader Pythona się wywraca. Dlatego
`compare_batch.sh` daje obu wersjom kopie z dopisanym minimalnym nagłówkiem `[IMG ID]`.

`tools/gen_py_cases.py` generuje `tests/py_cases.inc` z danych w oryginalnych testach `tests/*.py`.

## Wyniki (Linux, ten sam komputer)

Plik `wynik.mp`: 33 MB, 113 600 obiektów, 846 tys. węzłów. Wszystkie trzy porównania identyczne.

| | Python | C++ | przyspieszenie |
|---|---|---|---|
| wczytanie (bez rysowania) | 19,4 s | 0,78 s | ~25× |
| zapis | 4,6 s | 0,45 s | ~10× |
| pamięć (maks. RSS, wczytanie + zapis) | 1,03 GB* | 0,28 GB | ~3,7× |

\* Python tworzy przy wczytywaniu także obiekty Qt (`QPainterPath`, piksmapy), których rdzeń C++ jeszcze nie ma.

## Struktura

| plik | odpowiednik w Pythonie |
|---|---|
| `core/pyutil.*` | semantyka Pythona: `strip()` (z NBSP z cp1250), `int()`, `float()`, `round()`, `//`, `sum()` (Neumaier, Python ≥ 3.12), formatowanie |
| `core/geometry.hpp` | `QPointF`, `QLineF` (długość = `hypot` z libm, jak w Qt6) |
| `core/projection.*` | `projection.py`, `utm/conversion.py` |
| `core/data_x.*` | `Node`, `Numbers_Definition`, `Data_X` z `map_items.py` |
| `core/map_object.*` | dane `BasicMapItem`, `map_strings_record_to_dict_record` |
| `core/map_data.*` | `mapData.py`, `MapFileOpener.wczytaj_rekordy`, `MapFileSaver.run` |
| `core/misc.*` | `misc_functions.py` (część bez Qt) + konwersja cp1250 ↔ UTF-8 dla przyszłego GUI |
| `tools/mptool.cpp` | narzędzie CLI: `roundtrip`, `dump`, `ops`, `warnings` |

Tekst jest trzymany jako bajty cp1250, tak jak w pliku. Konwersja do UTF-8 będzie potrzebna dopiero w GUI.

## Różnice względem Pythona (celowe)

Tam, gdzie Python **przerywał wczytywanie wyjątkiem**, C++ zapisuje ostrzeżenie (`mptool warnings`),
pomija błędną linię lub rekord i wczytuje resztę. Na poprawnych plikach wynik jest identyczny.

- Plik bez nagłówka, plik bez obiektów, pusta linia po załącznikach `;@` wczytują się poprawnie (w Pythonie IndexError).
- Bajty nieobsługiwane przez cp1250 (0x81, 0x83, 0x88, 0x90, 0x98) przechodzą bez zmian (w Pythonie UnicodeDecodeError).
- Błędne `Numbers`/`HLevel`/`EndLevel`/`RouteParam`/współrzędne: ostrzeżenie zamiast przerwania wczytywania.
- Obiekt bez `Type=` zapisuje się bez tej linii (w Pythonie TypeError przerywał zapis).
- `Data_X.precision` w Pythonie była zmienną globalną procesu: rosła przy otwieraniu kolejnych plików
  w jednej sesji, a w testach zależała od ich kolejności. Tu precyzja należy do `MapData`.
- Część metod `Data_X` indeksowała listę poziomów numerem poziomu (`Data1` → `[1]`) zamiast pozycją.
  Działało to tylko dla poziomów od `Data0` po kolei. W innym przypadku Python rzucał IndexError
  (np. `Numbers` przy obiekcie mającym tylko `Data1`, podział linii na `Data1`) albo zmieniał zły poziom.
  Tu indeks jest zawsze poprawny.
- `split_data_x` czyściło numerację drugiej części pod indeksem `poly_num` zamiast 0 (IndexError dla `poly_num > 0`).
- `DirectProjection.canvas_to_geo` jest zaimplementowane (w Pythonie zwracało `None`).

## Błędy wykryte w wersji Python (zachowane 1:1, do decyzji)

Utrata danych przy zapisie:
1. **Załączniki z końca pliku (`;@File …`, `;@WEBMAP …`) są gubione.** Na `wynik.mp` znika linia `;@WEBMAP`.
2. Pola wczytywane, ale **niezapisywane**: `CityName`, `CountryName`, `RegionName`, `CountryCode`,
   `ZipCode`, `DistrictName`, `RoadID`.
3. Linie `Nod*` (węzły routingu) są pomijane przy wczytaniu.
4. Rekordy `[RESTRICT]` i `[SIGN]` są pomijane (giną przy zapisie).
5. Kod pocztowy w `Numbers`, który jest liczbą (np. `95040`), jest ignorowany. Zachowywane są tylko
   kody, których nie da się sparsować jako liczby (np. `95-040`).

Wczytywanie:

6. **Plik bez nagłówka** (pierwszy obiekt na początku pliku, ewentualnie poprzedzony tylko komentarzami)
   kończy wczytywanie wyjątkiem `IndexError`. Dotyczy to **1248 z 2706 plików źródłowych `~/ump/*/src/*.txt`**,
   czyli tych plików obecna wersja nie otworzy. C++ wczytuje je poprawnie.

Inne:

7. Końce linii CRLF zamieniane na LF w całym pliku. Pola nierozpoznane (np. `City=`) trafiają na koniec rekordu.
8. Projekcja UTM: `canvas_to_geo` nie jest zaimplementowane, więc mapy w UTM nie da się zapisać.
9. `great_circle_distance`: `lon2 = coord1[1]` zamiast `coord2[1]` (funkcja nieużywana).
10. Testy Pythona: 18 nie przechodzi w pełnym przebiegu. 15 z nich to skutek globalnej precyzji (pojedynczo
   przechodzą), `calculate_label_angle(315)` zwraca 315 przy oczekiwanym 45, `vincenty_distance`
   porównywane przez `==` z zaokrągloną wartością. Do tego `test_closest_point_to_poly_insert_node.py` nie
   importuje się (`map_object_properties` przed `sys.path.append`).
11. `get_interpolated_numbers_coordinates` jest rekurencyjna. Przy bardzo długim odcinku numeracji
    (>~1000 numerów) Python rzuci RecursionError. Wersja C++ jest iteracyjna.

## Etap 3: GUI w Qt6 (`gui/`)

Budowanie przez CMake (rdzeń, testy, `mptool` i GUI `pwmapedit`; GUI tylko, gdy znaleziono Qt6):

```sh
cd cpp
cmake -S . -B build-cmake -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build-cmake
ctest --test-dir build-cmake      # testy rdzenia (run_tests) i GUI (gui_tests, bez okna)
build-cmake/pwmapedit [plik.mp]
```

Testy GUI (`tests_gui/`, QtTest) budują się, gdy jest moduł Qt6 Test; uruchamiane są na platformie `offscreen`.
Uwaga: QtTest traktuje sloty o nazwie kończącej się na `_data` jako dane dla innego testu i ich nie uruchamia.

Windows (msys2, powłoka MINGW64): `pacman -S mingw-w64-x86_64-{gcc,cmake,ninja,qt6-base,qt6-svg}`.
Linux: `apt install cmake ninja-build qt6-base-dev qt6-svg-dev`.
Ikony są szukane w: `$PWMAPEDIT_ICONS`, `icons/` obok programu (i do 3 katalogów wyżej), `icons/` w bieżącym
katalogu, a na końcu w katalogu `icons/` repozytorium (ścieżka wkompilowana).

| plik | odpowiednik w Pythonie |
|---|---|
| `gui/main_window.*` | `pwMapEdit.py` (okno, menu, pasek narzędzi, pasek stanu, otwieranie/zapis) |
| `gui/commands.*` | `commands.py` (komendy undo/redo) |
| `gui/map_scene.*` | `mapCanvas.py` |
| `gui/map_view.*` | `mapRender.py` |
| `gui/map_items.*` | graficzna część `map_items.py` (POI, polilinie, polygony, etykiety, strzałki, numery adresowe, HLevel, linijka) |
| `gui/map_styles.*` | `map_object_properties.py` |
| `gui/constants.hpp` | `pwmapedit_constants.py` |

Elementy sceny nie kopiują danych: trzymają wskaźnik do `MapData` i indeks obiektu. Ścieżki rysowane są
z węzłów `DataX` dla wybranego poziomu.

### Etap 3a (zrobione): przeglądarka mapy

- otwieranie pliku w tle (także z linii poleceń), zapis i „zapisz jako”, pytanie przy zamykaniu niezapisanej mapy;
- rysowanie POI (ikony xpm/png), polilinii (kolor, grubość, styl według typu), polygonów (wypełnienie i Z według typu);
- etykiety POI, polilinii (obrócone wzdłuż linii) i polygonów, strzałki kierunku (`DirIndicator`), numery
  adresowe przy węzłach, oznaczenia `HLevel`;
- poziomy mapy 0–4 (klawisze `0`–`4`, menu View → Levels) z uwzględnieniem `EndLevel`;
- powiększanie `Ctrl`+kółko oraz `=`/`-`, przesuwanie prawym przyciskiem, linijka skali i współrzędne w pasku stanu;
- progi skali jak w Pythonie: ikony, napisy i strzałki o stałej wielkości powyżej skali 1, bez napisów poniżej 0,5,
  bez POI i małych polygonów poniżej 0,25;
- zaznaczanie kliknięciem (`Ctrl` dodaje, kolejne kliknięcia przełączają między obiektami pod kursorem),
  podświetlanie pod kursorem, `Esc` czyści zaznaczenie;
- `Ctrl+C` kopiuje współrzędne kursora, `Ctrl+G` przechodzi do podanych współrzędnych.

Test bez klikania: `pwmapedit plik.mp --screenshot zrzut.png [--zoom N] [--level L]` wczytuje mapę, zapisuje zrzut
okna i kończy działanie.

Wydajność (Windows, syntetyczna mapa 19 MB, 110 tys. obiektów z etykietami, numeracją i HLevel): wczytanie 0,4 s,
utworzenie elementów sceny 2,4 s, przełączenie poziomu mapy 3,2 s, odświeżenie widoku 45–100 ms.

Scena działa bez indeksu BSP (`NoIndex`). Przy setkach tysięcy elementów indeks BSP spowalniał każdą zmianę
geometrii (`setPath` przy zmianie poziomu: kilka ms na element, czyli minuty dla całej mapy), a przegląd liniowy
przy rysowaniu kosztuje kilkadziesiąt ms. Usuwanie wszystkich elementów idzie przez `QGraphicsScene::clear()`,
bo usuwanie pojedynczo jest kwadratowe.

Różnice względem Pythona (celowe):
- Przełączanie flagi `ItemIgnoresTransformations` robi scena przy przekroczeniu progu skali, a nie `paint()` każdego elementu.
- Na poziomie bez własnych danych (ale w zakresie `EndLevel`) polilinia i polygon pokazują dane z najwyższego niższego
  poziomu. Python pokazywał dane z poziomu oglądanego poprzednio, więc wynik zależał od kolejności przełączania.
- Etykieta polygonu pokazuje `Label` (w Pythonie była pusta, bo `_mp_label` nie był ustawiany).
- Gdy dla typu POI są ikony `_day` i `_night`, używana jest `_day` (w Pythonie zależało to od kolejności plików).
### Etap 3b.1 (zrobione): undo/redo, przesuwanie, usuwanie, odwracanie

- Stos undo/redo (Edit → Undo/Redo, `Ctrl+Z`/`Ctrl+Y`, przyciski na pasku), gwiazdka w tytule przy niezapisanych zmianach.
- Przesuwanie zaznaczonych obiektów lewym przyciskiem (POI, polilinie, polygony); przesuwany jest pokazywany poziom Data.
- Usuwanie zaznaczonych obiektów (`Delete`, Edit → Usuń); zapis pomija usunięte obiekty.
- Odwracanie zaznaczonych polilinii (Edit → Odwróć polilinię), razem z numeracją adresową.

Komendy (`gui/commands.*`) zmieniają tylko dane obiektu w `MapData`, a element sceny przebudowuje się z danych
(`MapObjectItem::refresh`). Obiekt jest wskazywany indeksem w `MapData`; usunięcie tylko oznacza obiekt jako
usunięty i ukrywa element, więc indeksy się nie zmieniają. Zmiany danych obiektu (przesunięcie, odwrócenie,
w kolejnych krokach edycja węzłów i właściwości) idą przez jedną komendę `ReplaceObjectCmd` ze stanem przed i po.

Różnice względem Pythona (celowe):
- Przeciągnięcie kilku zaznaczonych obiektów to jedna komenda undo (w Pythonie osobna dla każdego obiektu).
- Próg rozpoczęcia przesuwania (`MIN_MOVE_DISTANCE` = 3) jest liczony w pikselach ekranu, a nie w jednostkach sceny,
  więc nie zależy od powiększenia.
- Odwrócenie polilinii obejmuje wszystkie poziomy Data (w Pythonie tylko oglądany poziom, więc kierunek na
  pozostałych poziomach zostawał stary). Odwracanie jest dostępne z menu Edit (w Pythonie przyciskiem w panelu
  właściwości, który powstanie w 3b.3).

### Etap 3b.2 (zrobione): edycja węzłów, dzielenie i łączenie polilinii

Narzędzie Tools → Edit nodes (`m`, przycisk na pasku): zaznaczona polilinia lub polygon dostaje uchwyty na węzłach
pokazywanego poziomu Data (pierwszy węzeł czerwony).
- przeciągnięcie uchwytu przesuwa węzeł (podgląd w trakcie, jedna komenda undo po puszczeniu przycisku);
- `Ctrl`+klik na uchwycie usuwa węzeł (polilinia zachowuje co najmniej 2 węzły, polygon 3);
- `Shift`+klik na krawędzi dodaje węzeł na odcinku (do 8 pikseli od krawędzi);
- `Insert` dodaje węzeł pod kursorem na najbliższym odcinku, a za końcem polilinii ją przedłuża;
- `s` nad uchwytem (albo Edit → Podziel polilinię w węźle dla ostatnio klikniętego uchwytu) dzieli polilinię:
  obiekt zachowuje pierwszą część, druga staje się nowym obiektem z tymi samymi właściwościami;
- Edit → Połącz polilinie (przycisk na pasku) łączy zaznaczone polilinie w kolejności zaznaczania
  (`DataX::merge_polylines`, port `Data_X.merge_polylines` z testami z `tests/test_merge_polylines.py`).

Gdy kursor jest nad uchwytem, skróty jednoliterowe (narzędzia, poziomy) są wyłączone, tak jak w Pythonie.
Operacje zgłaszane przez uchwyt wykonują się po zakończeniu obsługi zdarzenia, bo przebudowują uchwyty.
Nowy obiekt (druga część podziału) dodaje `AddObjectCmd`; undo oznacza go jako usunięty, więc indeksy się nie zmieniają.

Zrzut z trybem edycji: `pwmapedit plik.mp --screenshot x.png --select N --edit-nodes`.

Różnice względem Pythona (celowe):
- Przeciągnięcie węzła to jedna komenda po puszczeniu przycisku (Python dodawał komendę przy każdym ruchu
  i łączył je, jeśli następowały w ciągu sekundy).
- Uchwyty nie mają podpisów z numerami (część, węzeł).
- Przyciąganie węzła do sąsiednich obiektów (`Ctrl` w trakcie przeciągania) będzie w etapie 3c.
- Usuwanie węzła sprawdza minimalną liczbę węzłów w każdej części obiektu (Python sprawdzał łączną liczbę
  uchwytów, więc w obiekcie wieloczęściowym mogła zostać część z jednym węzłem).

### Następne kroki

- 3b.3: panel właściwości (`map_obj_properties_dockwidget.py`), każda zmiana jako komenda undo.
- 3b.4: kopiuj/wklej obiektów.
- 3c: tworzenie obiektów (POI, polilinia, okrąg, polygon), przyciąganie do węzłów, warstwy WWW (`web_layers.py`).

Etap 2 (moduł pybind11) odłożony.
