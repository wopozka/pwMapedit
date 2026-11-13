// Czytnik plikow Garmin MapSource/BaseCamp GDB (wersje 1-3): slady i waypointy.
//
// Format opisany na podstawie GdbFile.h/GdbLoader.cpp z GPSMapEdit (K. Galichsky) i sprawdzony na plikach
// BaseCamp. Kod jest napisany od nowa: kazdy odczyt sprawdza granice rekordu, liczby sa kopiowane bajt po bajcie
// (bez rzutowania wskaznikow), wspolrzedne liczone w double. Trasy ('R') sa pomijane z ostrzezeniem.
//
// Plik: "MsRcf\0", potem rekordy [uint32 dlugosc][char typ][dane]:
//   'D' wersja formatu (uint16: 0x6B, 0x6C, 0x6D = GDB v1, v2, v3; v3 - teksty UTF-8, wczesniej strona kodowa
//       Windows - u nas cp1250), 'A' wersja programu (za rekordem nazwa programu zakonczona zerem, np. "MapSource",
//       "BaseCamp"), 'W' waypoint, 'T' slad, 'R' trasa, 'L' mapa, 'V' koniec.
// Wspolrzedne: int32 w "semicircles" - stopnie = wartosc * 180 / 2^31; najpierw szerokosc, potem dlugosc.
#pragma once

#include <string>
#include <string_view>
#include <vector>

#include "gps_data.hpp"

namespace pwm::gps {

struct GdbResult {
    bool ok = false;
    std::string error;                  // gdy !ok
    std::vector<std::string> warnings;  // np. uszkodzony slad, pominiete trasy
    int version = 0;                    // 1, 2 albo 3
    File file;
};

GdbResult read_gdb(std::string_view data);
GdbResult read_gdb_file(const std::string& path);

}  // namespace pwm::gps
