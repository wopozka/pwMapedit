// Port misc_functions.py (czesc niezalezna od Qt) i konwersja kodowania cp1250 <-> UTF-8.
#pragma once

#include <map>
#include <string>
#include <utility>
#include <vector>

#include "geometry.hpp"

namespace pwm::misc {

double vector_angle(double x, double y, bool clockwise = false, bool screen_coord_system = false);
double vector_length(double x, double y);
PointF unit_vector(double x, double y);
PointF vector_rotated(double x, double y, double rotation_angle, bool clockwise = false,
                      bool screen_coord_system = false);
PointF unit_vector_rotated(double x, double y, double rotation_angle, bool clockwise = false,
                           bool screen_coord_system = false);
double calculate_label_angle(double angle);

// Uwaga: wersja Python ma blad (lon2 = coord1[1]) - zachowany 1:1, funkcja nieuzywana w programie.
double great_circle_distance(GeoPoint coord1, GeoPoint coord2);
// Odleglosc w metrach (wzor Vincenty'ego, WGS-84).
double vincenty_distance(GeoPoint coord1, GeoPoint coord2);

// Odczyt ikon POI z pliku skorki: typ -> definicja XPM. Pusty slownik, gdy pliku nie ma.
std::map<std::string, std::string> read_icons_from_skin_file(const std::string& skin_filename);
std::pair<std::string, std::string> return_icon_definition(const std::vector<std::string>& icon_def);

}  // namespace pwm::misc

namespace pwm::encoding {

// Bajty cp1250 -> UTF-8. Bajty nieobslugiwane przez cp1250 (0x81, 0x83, 0x88, 0x90, 0x98) zamieniane na U+FFFD.
std::string cp1250_to_utf8(const std::string& in);
// UTF-8 -> cp1250. Znaki spoza cp1250 zamieniane na '?'; ok = false, gdy wystapila taka zamiana.
std::string utf8_to_cp1250(const std::string& in, bool* ok = nullptr);

}  // namespace pwm::encoding
