# pwMapEdit – krótka instrukcja

Edytor map w formacie MP (Polish Format, np. mapy UMP) dla Windows 10/11 64-bit.

## 1. Pierwsze uruchomienie

1. Pobierz zip ze strony [wydań](https://github.com/wopozka/pwMapedit/releases) i **rozpakuj cały folder** `pwMapEdit`
   (program potrzebuje plików DLL i folderu `icons` obok siebie).
2. Uruchom `pwmapedit.exe` – nie trzeba niczego instalować.
3. Otwórz mapę: **File → Open**, przeciągnij plik `.mp` na okno albo na ikonę programu,
   albo **File → Open recent** (ostatnio otwierane pliki).

> ⚠️ **Pracuj na kopii mapy.** Zapis nie zachowuje jeszcze części danych (szczegóły w punkcie 8).

## 2. Oglądanie mapy

| Co chcesz zrobić | Jak |
|---|---|
| przesunąć mapę | przeciągnij **prawym** przyciskiem myszy |
| powiększyć / pomniejszyć | **Ctrl + kółko** myszy albo klawisze **=** i **-** |
| zmienić poziom szczegółów | klawisze **0–4** (View → Levels) |
| włączyć podkład z internetu | menu **Weblayers** (OSM, Geoportal, Google); **E** włącza/wyłącza |
| przejść do współrzędnych | **Ctrl+G** i wpisz np. `52.123456, 21.123456` |

## 3. Zaznaczanie i podstawowa edycja (narzędzie Select, klawisz **s**)

| Co chcesz zrobić | Jak |
|---|---|
| zaznaczyć obiekt | kliknij go; kolejne kliknięcia przełączają między obiektami leżącymi jeden na drugim |
| zaznaczyć kilka | **Ctrl+klik** (dodaje także mniejszy obiekt leżący na zaznaczonym) |
| odznaczyć | **Esc** |
| przesunąć obiekt | przeciągnij go lewym przyciskiem |
| usunąć | **Delete** |
| kopiować / wyciąć / wkleić | **Ctrl+C / Ctrl+X / Ctrl+V** – wklejone obiekty trafiają pod kursor |
| cofnąć / ponowić | **Ctrl+Z / Ctrl+Y** (działa dla każdej zmiany) |
| zmienić typ, nazwę, adres, routing… | panel **Właściwości** po prawej (zaznacz jeden obiekt) |
| odwrócić kierunek linii | **Edit → Odwróć polilinię** albo przycisk w panelu Właściwości |

## 4. Edycja węzłów (klawisz **m**)

Kliknij linię albo polygon – na węzłach pojawią się kwadraty (pierwszy węzeł jest czerwony).

| Co chcesz zrobić | Jak |
|---|---|
| przesunąć węzeł | przeciągnij kwadrat |
| dociągnąć węzeł do węzła innego obiektu | przeciągaj z wciśniętym **Ctrl** (niebieskie kółko pokazuje miejsce) |
| usunąć węzeł | **Ctrl+klik** na kwadracie |
| dodać węzeł | **Shift+klik** na krawędzi albo **Insert** pod kursorem (za końcem linii – przedłuża ją) |
| podzielić linię w węźle | najedź na kwadrat i naciśnij **s** |
| ustawić numerację adresową / HLevel węzła | kliknij kwadrat → karta **Węzły** w panelu Właściwości |
| połączyć linie | zaznacz je (Ctrl+klik, w kolejności) → **Edit → Połącz polilinie** |

## 5. Rysowanie nowych obiektów

| Obiekt | Jak |
|---|---|
| punkt (POI) | klawisz **a**, kliknij na mapie |
| polilinia | klawisz **b**, klikaj kolejne węzły, **Enter** kończy |
| polygon | klawisz **f**, klikaj kolejne węzły, **Enter** kończy |
| okrąg (polilinia) | Tools → Polyline: circle; klik na okręgu, potem klik w środku |

- **Backspace** usuwa ostatni węzeł, **Esc** porzuca rysowany obiekt.
- Z wciśniętym **Ctrl** węzły przyciągają się do węzłów innych obiektów i punktów śladów GPS.
- Nowy obiekt dostaje typ ostatnio wybrany w panelu Właściwości – ustaw go od razu po narysowaniu.

## 6. Rysowanie po śladach GPS

1. Otwórz mapę, potem **File → Wczytaj ślady GPS** (pliki `.gpx` oraz `.gdb` z Garmin MapSource/BaseCamp)
   albo przeciągnij pliki na okno. Widok przesunie się na ślad.
2. Ślady i punkty są tylko podkładem – **nie zapisują się w mapie**. Lista jest w panelu **Ślady GPS**.
3. Rysuj drogę po śladzie: **b** i klikanie z **Ctrl** (węzły trafiają w punkty GPS),
   albo w panelu Ślady GPS prawy przycisk na śladzie → **Utwórz polilinię**
   (pole „Uproszczenie śladu” – im więcej metrów, tym mniej węzłów).
4. Waypoint → POI: prawy przycisk na waypoincie → **Utwórz POI** (nazwa trafia do Label).

## 7. Polygony i poziomy Data

- **Odejmowanie:** zaznacz duży polygon, potem **Ctrl+klik** mniejszy → **Tools → Odejmij polygony**
  (mniejszy wewnątrz → dziura; częściowo → wycięcie). Wariant „i usuń drugi” usuwa też odejmowany.
- **Zamiana:** zaznacz polygon albo polilinię → **Tools → Zamień polygon na polilinię / polilinię na polygon**
  (menu Tools pokazuje tylko operacje pasujące do zaznaczenia).
- **Części i poziomy:** panel Właściwości → karta **Elements**, prawy przycisk:
  - na „Poly: N” – **Usuń element**, **Ekstrahuj element** (część staje się osobnym obiektem),
  - na „DataN” – **Przenieś na poziom** / **Skopiuj na poziom**.

## 8. Zapis

- **Ctrl+S** zapisuje, **File → Save map as** zapisuje pod nową nazwą. Przy zamykaniu z niezapisanymi zmianami
  program pyta: Zapisz / Nie zapisuj / Anuluj.
- Zapis **nie zachowuje jeszcze**: rekordów `[RESTRICT]` i `[SIGN]`, pól `CityName`, `CountryName`, `RegionName`,
  `CountryCode`, `ZipCode`, `DistrictName`, `RoadID`, linii `Nod*`, załączników z końca pliku (`;@File`, `;@WEBMAP`)
  oraz kodów pocztowych zapisanych samymi cyframi w `Numbers`.
- Program trzyma listę ostatnich plików w `.pwmapedit.ini` w katalogu użytkownika, a pobrane kafelki podkładu
  w `%LOCALAPPDATA%\pwMapEdit\cache\weblayers` (można je usunąć w dowolnej chwili).

Nowe wersje: https://github.com/wopozka/pwMapedit/releases
