// Operacje na obszarach polygonow (Clipper2): odejmowanie jednego polygonu od drugiego.
//
// Obiekt mp to zestaw czesci (pierscieni) na poziomie Data, rysowanych zasada parzystosci: czesc lezaca w innej
// czesci jest dziura. Tak samo traktujemy wejscie i tak zapisujemy wynik: kazda czesc zewnetrzna, a po niej
// jej dziury (kolejnosc jak w karcie Elements).
#pragma once

#include <vector>

#include "geometry.hpp"

namespace pwm::geom {

using Ring = std::vector<PointF>;  // pierscien bez powtorzonego pierwszego punktu na koncu

struct SubtractResult {
    enum class Status {
        Ok,         // A zmieniony
        NoOverlap,  // polygony sie nie nakladaja - bez zmian
        Empty,      // B pokrywa cale A - wynik pusty
    };
    Status status = Status::NoOverlap;
    std::vector<Ring> rings;  // wynik dla Ok
};

// A - B we wspolrzednych sceny (Mercator, jednostki ~metry). Wspolrzedne sa zaokraglane do 1 mm, wierzcholki
// wspolliniowe zostaja (wspolne wezly z sasiednimi obiektami nie znikaja), okruchy ponizej min_area sa pomijane.
SubtractResult subtract(const std::vector<Ring>& a, const std::vector<Ring>& b, double min_area = 0.01);

}  // namespace pwm::geom
