// Punkty przeciecia dwoch linii (Tools -> Dodaj bojki wiadukt).
#pragma once

#include <vector>

#include "geometry.hpp"

namespace pwm {

// Czesc linii: kolejne wezly (wspolrzedne sceny).
using LinePart = std::vector<PointF>;

// Punkty, w ktorych linia a przechodzi przez linie b (obie moga miec kilka czesci). Liczy sie tylko
// prawdziwe przeciecie - jedna linia przechodzi na druga strone drugiej:
//  - odcinki przecinaja sie we wnetrzach obu,
//  - albo wezel wewnetrzny jednej linii lezy we wnetrzu odcinka drugiej, a sasiednie wezly sa po przeciwnych
//    stronach tego odcinka.
// Pomijane: wspolny wezel (zwykle skrzyzowanie), koniec linii na drugiej (styk "T"), odcinki rownolegle
// i nakladajace sie. Punkty blizsze niz merge_distance sa laczone w jeden.
std::vector<PointF> line_crossings(const std::vector<LinePart>& a, const std::vector<LinePart>& b,
                                   double merge_distance);

}  // namespace pwm
