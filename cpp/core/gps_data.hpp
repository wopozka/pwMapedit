// Dane GPS wczytane jako podklad do rysowania (GPX, pozniej GDB): punkty, waypointy, slady.
// Nie sa czescia mapy i nie sa zapisywane do pliku mp.
#pragma once

#include <optional>
#include <string>
#include <vector>

namespace pwm::gps {

struct Point {
    double lat = 0;
    double lon = 0;
    std::optional<double> ele;   // m
    std::optional<std::string> time;  // tekst jak w pliku (GPX: ISO 8601)
};

struct Waypoint {
    Point pos;
    std::string name;     // UTF-8
    std::string comment;  // UTF-8 (GPX: cmt, a gdy brak - desc)
    std::string symbol;   // GPX: sym
};

// Slad albo trasa: jedna lub kilka czesci (GPX trkseg).
struct Track {
    std::string name;  // UTF-8
    std::vector<std::vector<Point>> segments;
    bool route = false;  // z <rte>
};

struct File {
    std::string path;
    std::vector<Waypoint> waypoints;
    std::vector<Track> tracks;
    size_t point_count() const;
};

// Uproszczenie linii algorytmem Douglasa-Peuckera z tolerancja w metrach. Zwraca indeksy zachowanych punktow
// (zawsze pierwszy i ostatni). Odleglosci liczone w lokalnym ukladzie metrycznym (wystarcza dla sladow GPS).
std::vector<size_t> simplify(const std::vector<Point>& points, double tolerance_m);

}  // namespace pwm::gps
