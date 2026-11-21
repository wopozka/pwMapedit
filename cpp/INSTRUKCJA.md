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
| powiększyć / pomniejszyć | **Ctrl + kółko** myszy albo klawisze **=** lub **+** (także na klawiaturze numerycznej) i **-** |
| zmienić poziom szczegółów | klawisze **0–4** (View → Levels) |
| poziom szczegółów według skali | klawisz **.** (kropka) albo **View → Levels → Automatycznie**: powyżej 1:10 000 – Level 0, do 1:50 000 – 1, do 1:200 000 – 2, do 1:1 000 000 – 3, dalej – 4; włączony po uruchomieniu programu, wyłącza się po wybraniu konkretnego poziomu; bieżący poziom widać na pasku stanu („map level”) |
| ukryć POI, polilinie albo polygony, żeby mapa była czytelniejsza | **View → Warstwy → POI / Polilinie / Polygony** – wyłączona warstwa znika razem z etykietami, ikonami, obwódkami i ikonami szlaków/routingu; jej obiektów nie można kliknąć, zaznaczyć ramką ani przyciągnąć do nich węzła (zaznaczenie z nich jest zdejmowane). Gdy rysujesz, wklejasz albo dodajesz (np. bojki, zamiana polygon↔polilinia) obiekt z wyłączonej warstwy, warstwa włącza się sama. Wybór jest zapamiętywany |
| widzieć, co jest pod polygonami | **View → Wypełnienie polygonów → Transparentne** albo **Tylko kontury** – polygony bez wypełnienia, sam obrys w (przyciemnionym) kolorze polygonu; zaznaczony polygon wygląda tak samo w każdym trybie (wybór jest zapamiętywany) |
| lepiej widzieć jasne drogi (np. żółte) i kolej | **View → Obwódki dróg** – ciemniejsza obwódka pod każdą drogą, kolej z czarnym brzegiem i białymi przerwami, kolej podziemna/rozebrana tak samo, tylko szara (wybór jest zapamiętywany) |
| widzieć szlaki piesze i rowerowe | **View → Ikony szlaków** (domyślnie włączone) – wzdłuż szlaków pieszych i chodników ikona pieszego, wzdłuż szlaków rowerowych i dróg dla rowerów ikona roweru, w krążku w kolorze szlaku (chodnik i droga dla rowerów – biały krążek, szlak wielokolorowy – krążek w czterech kolorach); ikony widać od skali ok. 1:25 000 |
| widzieć zakazy ruchu i drogi płatne | **View → Ikony routingu** (domyślnie włączone) – na drogach 0x1–0xf według RouteParam: znak zakazu ruchu (pusty biały krążek w czerwonym pierścieniu) przy zakazach No emergency, No delivery, No car/motorcycle, No bus, No taxi, No truck; znak zakazu z pieszym (No pedestrian), rowerem (No bicycle) albo oboma rysunkami (oba zakazy); żółty krążek z symbolem € przy „Route is toll”; ikony jednej drogi stoją obok siebie w środku drogi (na długiej drodze – w środkach jej równych odcinków), widać je od skali ok. 1:25 000 |
| pracować w ciemnym albo jasnym oknie | **View → Motyw**: *Systemowy* (domyślnie, według ustawienia Windows lub pulpitu, zmienia się razem z nim), *Jasny* albo *Ciemny*. Zmienia się okno, panele i pasek narzędzi; sama mapa zostaje jasna. Wybór jest zapamiętywany |
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
| skopiować całą tabelę Extras zaznaczonego obiektu | **Ctrl+Alt+C** (szczegóły niżej) |
| cofnąć / ponowić | **Ctrl+Z / Ctrl+Y** (działa dla każdej zmiany) |
| zmienić typ, nazwę, adres, routing… | panel **Właściwości** po prawej (zaznacz jeden obiekt) |
| odwrócić kierunek linii | **Edit → Odwróć polilinię** albo przycisk w panelu Właściwości |

### Wybór typu obiektu

Pole **Type** w panelu Właściwości można przeszukiwać: kliknij w nie i zacznij pisać. Lista podpowiedzi pokazuje
typy, które zawierają wpisany tekst w **dowolnym miejscu** opisu (wielkość liter nie ma znaczenia) – można więc
wpisać kod (`0x2f00`, `2f0`), kategorię albo fragment nazwy po polsku lub angielsku (`stacja`, `fuel`, `las`,
`residential`). Wybierz typ z listy strzałkami i **Enter** albo kliknięciem – zmiana trafia od razu do obiektu
(i do historii **Ctrl+Z**), a nowo rysowane obiekty tego rodzaju dostaną ten sam typ.

### Schowek: obiekty jako tekst MP

- **Ctrl+C** na zaznaczonych obiektach zapisuje w schowku także ich **zapis w formacie MP** – po wklejeniu do
  Notatnika albo innego pliku `.txt` widać dokładnie te rekordy, które trafiłyby do pliku mapy, np.:

  ```
  [POLYLINE]
  Type=0x6
  Label=Ulica
  Data0=(52.10000,21.00000),(52.10100,21.00100)
  [END]
  ```

- Działa to też w drugą stronę: zaznacz w edytorze tekstu jeden lub kilka rekordów (od `[POI]`/`[POLYLINE]`/
  `[POLYGON]` do `[END]`), skopiuj je i naciśnij **Ctrl+V** w oknie mapy – obiekty zostaną dodane do mapy
  (jedna operacja do cofnięcia **Ctrl+Z**) i zaznaczone. Można w ten sposób przenosić obiekty między mapami,
  poprawiać je ręcznie w tekście albo wklejać fragmenty innych plików `.mp`.
- Obiekty wklejone **z tekstu** trafiają w miejsce zapisane we współrzędnych `Data`. Obiekty skopiowane
  **w pwMapEdit** i wklejone od razu z powrotem trafiają **pod kursor**.

### Schowek: tabela Extras

Tabela **Extras** (dodatkowe pola rekordu, np. `Miasto=…`) ma własny schowek, gdy kursor jest w tabeli:

- zaznacz komórki i **Ctrl+C / Ctrl+X / Ctrl+V** (albo prawy przycisk → Kopiuj / Wklej); wklejanie zaczyna się
  od bieżącego wiersza i w razie potrzeby dopisuje nowe wiersze; **Delete** czyści zaznaczone komórki,
- **Ctrl+Alt+C** kopiuje **całą** tabelę Extras zaznaczonego obiektu bez zaznaczania komórek (kursor może być
  gdziekolwiek) – potem zaznacz inny obiekt, kliknij w jego tabelę Extras i **Ctrl+V**,
- w edytorze tekstu skopiowane Extras wyglądają jak wiersze `klucz<TAB>wartość`; wkleić do tabeli można też
  tekst w postaci `klucz=wartość` (np. linie skopiowane z pliku `.mp`) albo dwie kolumny z arkusza.

## 4. Edycja węzłów (klawisz **m**)

Kliknij linię albo polygon – na węzłach pojawią się kwadraty (pierwszy węzeł jest czerwony).
Na drodze z numeracją adresową pojawiają się też numery interpolowane między węzłami z numeracją
(jaśniejsze, rozłożone równo wzdłuż drogi). Nad edytowaną linią albo krawędzią edytowanego obszaru kursor
zmienia się w krzyżyk.

| Co chcesz zrobić | Jak |
|---|---|
| przesunąć węzeł | przeciągnij kwadrat |
| dociągnąć węzeł do węzła innego obiektu | przeciągaj z wciśniętym **Ctrl** (niebieskie kółko pokazuje miejsce) |
| usunąć węzeł | **Ctrl+klik** na kwadracie |
| dodać węzeł | **Shift+klik** na krawędzi albo **Insert** pod kursorem (za końcem linii – przedłuża ją) |
| dodać węzeł i od razu go przesunąć | przy kursorze-krzyżyku naciśnij krawędź i przeciągnij (z **Ctrl** – dociąga do węzła) |
| podzielić linię w węźle | najedź na kwadrat i naciśnij **s** |
| obrócić obiekt wokół jego środka ciężkości | kursor nad obiektem (polygon i zamknięta linia, np. rondo – także w środku), **Shift + kółko**: 1° na ząbek, z **Ctrl** 0,1°; kółko od siebie – w lewo. Obraca wszystkie poziomy Data; czerwony krzyżyk pokazuje środek, kąt widać na pasku stanu; cały obrót cofa jedno **Ctrl+Z** |
| ustawić numerację adresową / HLevel węzła | kliknij kwadrat → karta **Węzły** w panelu Właściwości |
| przejść do następnego / poprzedniego węzła | przy otwartej karcie **Węzły**: klawisz **n** / **p** (albo przyciski Następny / Poprzedni) |
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
- **Bojki wiadukt:** zaznacz co najmniej dwie drogi (**Ctrl+klik**) → **Tools → Dodaj bojki wiadukt** albo klawisze **d**, potem **w** – w każdym
  miejscu, gdzie drogi się przecinają, powstaje POI WIADUKT (0x1709). Wspólny węzeł (zwykłe skrzyżowanie)
  i droga kończąca się na drugiej nie są przecięciem; tam, gdzie POI wiadukt już stoi, nowy nie jest dodawany.
- **Bojki ślepy:** zaznacz drogi → **Tools → Dodaj bojki ślepy** albo klawisze **d**, potem **s** – POI SLEPY (0x1708) na każdym końcu zaznaczonej
  drogi, który nie ma wspólnego węzła z żadną inną drogą na mapie (kolej, rzeka itp. się nie liczą). Zamknięta
  linia (rondo) nie ma końców; tam, gdzie POI ślepy już stoi, nowy nie jest dodawany.
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
