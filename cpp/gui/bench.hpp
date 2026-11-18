#pragma once
// Pomiar wplywu indeksu sceny (NoIndex / BSP o stalej glebokosci / BSP wylaczany na czas zmiany poziomu)
// na rysowanie, przyblizanie, zmiane poziomu mapy i zapytanie o elementy pod kursorem (hover).
// Uruchamiany z linii polecen: pwmapedit mapa.mp --bench wyniki.txt [--index none|bsp|bsp-toggle] [--bsp-depth N]
//                                               [--bench-level L] [--bench-zoom Z]
#include <QString>

namespace pwm::gui {

class MainWindow;

struct IndexBenchOptions {
    QString output;              // plik wynikow (wyniki sa dopisywane)
    QString index = "none";      // none | bsp | bsp-toggle (BSP, ale NoIndex na czas zmiany poziomu)
    int bsp_depth = 0;           // 0 = glebokosc wybierana automatycznie przez Qt
    int level = 1;               // poziom, na ktory przelacza pomiar (i z powrotem na 0)
    int zoom = 40;               // liczba krokow przyblizenia (1,1^40 = ok. 45x, widok ulic)
};

// Ustawia indeks sceny - wywolac przed wczytaniem mapy.
void apply_index_mode(MainWindow& window, const IndexBenchOptions& opt);
// Pomiar na wczytanej mapie (wywolac od razu po map_loaded, zanim widok sie przerysuje); wynik dopisuje do pliku.
bool run_index_bench(MainWindow& window, const IndexBenchOptions& opt, const QString& map_file);

}  // namespace pwm::gui
