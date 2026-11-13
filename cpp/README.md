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
| `gui/properties_dock.*` | `map_obj_properties_dockwidget.py` (panel właściwości) |
| `core/gps_data.*` | (nowe) dane GPS i upraszczanie śladu (Douglas-Peucker) |
| `core/gdb_reader.*` | (nowe) czytnik plików Garmin GDB |
| `gui/gpx_reader.*`, `gui/gps_layers.*`, `gui/gps_dock.*` | (nowe) czytnik GPX, ślady na scenie, panel „Ślady GPS” |
| `core/web_tiles.*` | `web_layers.py` (kafelki: zoom ze skali, numery kafelków, adresy OSM/Geoportal/Google) |
| `gui/web_layers.*` | warstwy WWW z `mapRender.py`/`mapCanvas.py` (pobieranie w tle, kafelki na scenie) |
| `gui/type_names.*` | `icons/icons_names.py`, `type_aliases.py`, `line_polygon_names.py` (generowane przez `tools/gen_type_names.py`) |
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

### Etap 3b.3 (zrobione): panel właściwości

Panel „Właściwości” po prawej stronie okna pokazuje jedyny zaznaczony obiekt:
- **Główny**: typ (lista z nazwami i ikonami POI, wpisany tekst filtruje listę), Label/Label2/Label3, EndLevel,
  DirIndicator i odwrócenie polilinii, komentarz (zapis po opuszczeniu pola), Extras (menu kontekstowe: dodaj
  i usuń wiersz);
- **Adres** (POI): StreetDesc, HouseNumber, Phone;
- **Elements**: części obiektu na poziomach Data (zewnętrzne i wewnętrzne części polygonu, pierwszy punkt,
  liczba węzłów); wybrana część jest podświetlana na mapie;
- **Routing** (polilinie): 12 wartości RouteParam;
- **Węzły** (tryb edycji węzłów, po kliknięciu uchwytu): numeracja adresowa po obu stronach i HLevel węzła.

Panel nie trzyma kopii danych. Każda zmiana pola to kopia obiektu ze zmienioną wartością przekazana do
`MapScene::replace_object` (jedna komenda undo, tylko gdy zapis obiektu do mp rzeczywiście się zmienia). Po każdej
zmianie stosu undo panel wypełnia się od nowa z danych. Zmiana typu przerysowuje element (ikona, kolor, wypełnienie).

Różnice względem Pythona (celowe):
- Aliasy typów POI są dopasowywane numerycznie; Python porównywał tekst `hex(typ)` z kluczem, więc aliasy typów
  zapisanych z zerem wiodącym (np. `0x0600`) nie pojawiały się na liście.
- Karta Routing pokazuje wartości obiektu także wtedy, gdy wszystkie są zerami (Python zostawiał wtedy wartości
  poprzednio pokazanego obiektu).
- W trybie edycji węzłów, dopóki nie kliknięto uchwytu, panel pokazuje właściwości obiektu (w Pythonie był pusty).
- Po edycji panel zostaje na bieżącej karcie (Python wracał na kartę Główny).
- Puste pole (etykieta, adres) usuwa wartość z obiektu; puste końcowe wiersze komentarza są pomijane.
- Karta Elements nie ma kolumny „Obszar” ani menu „Usuń/Kopiuj do” (w Pythonie nie były zaimplementowane).

### Etap 3b.4 (zrobione): kopiuj, wytnij, wklej

- `Ctrl+C` kopiuje zaznaczone obiekty (bez zaznaczenia: współrzędne kursora, jak dotąd), `Ctrl+X` wycina
  (kopiuje i usuwa, tylko w trybie zaznaczania), `Ctrl+V` wkleja; przyciski na pasku.
- Schowek ma format wersji Python: `application/json` (lista rekordów, każdy zaczyna się od `MouseScenePos=x,y`
  i kończy `[END]`) oraz tekst rekordów mp, więc obiekty można przenosić między obiema wersjami programu
  i wklejać rekordy mp skopiowane z edytora tekstu.
- Wklejone obiekty są przesuwane o wektor od miejsca kliknięcia przy kopiowaniu (`MouseScenePos`) do bieżącej
  pozycji kursora; wklejone z samego tekstu trafiają w oryginalne miejsce. Wklejenie to jedna komenda undo
  (`AddObjectCmd` dla każdego obiektu), a wklejone obiekty zostają zaznaczone.
- Obiekt z rekordu tworzy `MapData::object_from_record` (rdzeń, z testem).

Różnice względem Pythona (celowe):
- Wszystkie kopiowane obiekty mają wspólny punkt odniesienia (ostatnie kliknięcie), więc po wklejeniu zachowują
  wzajemne położenie (w Pythonie każdy obiekt miał własny punkt, ostatnie kliknięcie na nim).
- Wklejony obiekt jest przesuwany na wszystkich poziomach Data (Python przesuwał tylko pokazywany poziom).
- Wytnij działa (w Pythonie akcja była w menu, ale niepodłączona).
- `Ctrl+C/X/V` w polach panelu właściwości nie dotyczą obiektów mapy.

### Etap 3c.1 (zrobione): tworzenie obiektów i przyciąganie

Narzędzia w menu Tools i na pasku (skróty jak w Pythonie):
- **Point** (`a`): kliknięcie tworzy POI;
- **Polyline** (`b`) i **Polygon** (`f`): kliknięcia (albo `Insert`) dodają węzły, `Backspace` usuwa ostatni,
  `Enter` kończy (polilinia co najmniej 2 węzły, polygon 3), `Esc` porzuca rysowany obiekt; podgląd w trakcie;
- **Polyline: circle**: pierwsze kliknięcie to punkt na okręgu, kursor wyznacza środek, drugie kliknięcie tworzy
  zamkniętą polilinię; liczba boków taka, żeby bok miał co najmniej 7 m (`MINIMAL_GEO_DISTANCE`), jak w Pythonie.

Nowy obiekt dostaje typ ostatnio wybrany w panelu właściwości dla danego rodzaju (`last_used_type`). Po utworzeniu
włącza się narzędzie zaznaczania i nowy obiekt jest zaznaczony. Tworzenie to jedna komenda undo (`AddObjectCmd`).

Przyciąganie: z wciśniętym `Ctrl` nowy węzeł (przy rysowaniu) albo przeciągany uchwyt (w edycji węzłów) trafia
w najbliższy węzeł innej polilinii lub polygonu w promieniu 15 pikseli; niebieskie kółko pokazuje to miejsce.

Różnice względem Pythona (celowe):
- Promień przyciągania jest w pikselach ekranu (w Pythonie w jednostkach sceny, więc zależał od powiększenia).
- Akcje „Polygon: stripe/rectangle/disc” nie zostały przeniesione - w Pythonie były w menu, ale nic nie robiły.
- Zmiana narzędzia porzuca rysowany obiekt.

### Etap 3c.2 (zrobione): warstwy WWW

Menu Weblayers: OSM, Geoportal (ortofotomapa), Google (ortofotomapa) - jedna warstwa naraz albo żadna;
`E` włącza i wyłącza ostatnio używaną warstwę (jak `background_on_off`). Po każdej zmianie widoku zoom kafelków
jest liczony ze skali linijki, a kafelki pokrywające widok są układane pod obiektami mapy. Brakujące kafelki są
pobierane w tle (`QNetworkAccessManager`, nagłówek `User-Agent: pwMapedit`, limit czasu 15 s). Kafelki, które
wyszły poza widok przed pobraniem, nie są pobierane.

Matematyka kafelków (`core/web_tiles.*`) jest bez Qt; testy porównują z wartościami policzonymi oryginalnym
`web_layers.py`. Test GUI pobiera kafelki z lokalnego pliku (bez sieci). Zrzut z podkładem:
`pwmapedit plik.mp --screenshot x.png --weblayer osm|geoportal|google`.

Różnice względem Pythona (celowe):
- Pamięć podręczna kafelków jest trwała (`<cache użytkownika>/weblayers`, na Windows w `%LOCALAPPDATA%`);
  Python używał katalogu tymczasowego, więc w każdej sesji pobierał kafelki od nowa.
- Kafelki leżą pod wszystkimi obiektami mapy i nie reagują na mysz.
- Wyliczenie serwera Google (`(x + 2) * y % 2`) jest liczone na 64 bitach - przy 32 bitach przepełniało się
  dla dużych zoomów (Python liczy na dowolnie dużych liczbach).

### Uzupełnienia z nowszej wersji Python

- File → Open recent: do 10 ostatnio otwieranych plików (dopisywane przy otwarciu i „Save map as”), zapisane
  w `~/.pwmapedit.ini` pod kluczem `recent_files` - ten sam plik i klucz co w wersji Python, więc lista jest wspólna.
  Brakujący plik jest usuwany z listy z komunikatem. Okno otwierania zaczyna w katalogu ostatniego pliku.
  Zmienna `PWMAPEDIT_SETTINGS` wskazuje inny plik ustawień (używają jej testy).
- Niezapisane zmiany przy zamykaniu programu i przy otwieraniu innego pliku: Zapisz / Nie zapisuj / Anuluj;
  gdy zapis się nie uda, program nie zamyka mapy.
- Tabela Extras: `Ctrl+C`/`Ctrl+X`/`Ctrl+V` i menu kontekstowe Kopiuj/Wklej (format jak `ExtrasTable` w Pythonie:
  JSON z parami [klucz, wartość] i tekst `klucz<TAB>wartość`; wkleja się też tekst `klucz=wartość`). `Delete`
  w tabeli czyści zaznaczone komórki (wcześniej usuwał zaznaczony obiekt mapy).

### Ślady GPS jako podkład do rysowania (nowa funkcja, nie ma jej w wersji Python)

Ślady i punkty z plików GPX i GDB są tylko podkładem w bieżącej sesji: nie są częścią mapy i nie zapisują się w pliku mp.
- Wczytywanie: File → „Wczytaj ślady GPS…” (wiele plików naraz), przycisk w panelu albo przeciągnięcie plików
  `.gpx`/`.gdb` na okno (wymaga otwartej mapy - ślady są rysowane w jej układzie). GPX: `<wpt>`, `<trk>/<trkseg>`
  i `<rte>` (GPX 1.0 i 1.1); punkty bez poprawnych współrzędnych są pomijane z ostrzeżeniem.
  Po wczytaniu widok przesuwa się na ślad, jeśli nie było go widać, a obszar przewijania obejmuje ślady
  (wcześniej był ograniczony do mapy).
- Na mapie: ślady jako cienkie linie (każdy plik w innym kolorze), przy powiększeniu z punktami GPS; waypointy
  jako romby z nazwą. Leżą nad podkładem WWW, pod obiektami mapy i nie reagują na mysz. Po otwarciu innej mapy
  zostają wczytane i są rysowane w jej układzie.
- Panel „Ślady GPS” (karta obok „Właściwości”): pliki z polem widoczności i kolorem, ślady (i ich części),
  waypointy. Zaznaczona pozycja jest podświetlana, podwójne kliknięcie centruje na niej widok.
- Rysowanie: `Ctrl` przyciąga węzły (rysowanie, przeciąganie uchwytów) także do punktów śladów i waypointów.
- „Utwórz obiekty” / menu kontekstowe: ślad lub jego część → polilinia z ostatnio użytym typem, uproszczona
  algorytmem Douglasa-Peuckera z tolerancją z panelu (domyślnie 3 m; 0 - wszystkie punkty); waypointy → POI
  (`Label` = nazwa, komentarz = `cmt`/`desc`). Każde polecenie to jedna komenda undo. Wykorzystane elementy
  są szare (tylko oznaczenie w sesji - cofnięcie nie zdejmuje go).
- Zrzut ze śladami: `pwmapedit plik.mp --screenshot x.png --gps slad.gpx`.

Pliki GDB (Garmin MapSource/BaseCamp, wersje 1-3) czyta `core/gdb_reader.*`: ślady, waypointy (nazwa, pozycja,
wysokość, komentarz, symbol) i trasy. Trasa staje się śladem (w panelu „Trasa:”): punkty kolejnych odcinków (dla tras
wyznaczonych przez MapSource - geometria drogi) sklejone bez powtórzonych punktów; odcinek bez punktów bierze pozycję
waypointu o swojej nazwie. Dane za odcinkami, które GPSMapEdit czytał jako komentarz trasy, są binarne i są pomijane. Format opisany na podstawie `GdbFile.h`/`GdbLoader.cpp`
z GPSMapEdit, kod napisany od nowa: każdy odczyt sprawdza granice rekordu, współrzędne w `double` (GPSMapEdit liczył
waypointy we `float`, z błędem rzędu metrów). Uszkodzony ślad (mniej punktów niż w nagłówku) i ucięty plik są wczytywane
do miejsca uszkodzenia z ostrzeżeniem. Za rekordem wersji programu może stać „MapSource” albo „BaseCamp”. Testy: pliki
BaseCamp i MapSource w `tests/gdb/` (liczby rekordów i wartości porównane z niezależnym skryptem; trasy zaczynają
odcinki na waypointach o podanych nazwach) oraz pliki budowane w teście (v1 z cp1250, v3 z UTF-8, uszkodzenia).

### Następne kroki

- Etap 3 przeniesiony w całości; dalsze kroki do ustalenia (np. poprawki błędów z wersji Python opisanych wyżej,
  etap 2 - moduł pybind11).


Etap 2 (moduł pybind11) odłożony.
