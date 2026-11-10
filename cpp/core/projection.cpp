#include "projection.hpp"

#include <cctype>
#include <cmath>

#include "pyutil.hpp"

namespace pwm {

using py::degrees;
using py::PI;
using py::radians;

PointF DirectProjection::geo_to_canvas(double latitude, double longitude) const {
    return {earth_radius * longitude, -earth_radius * latitude};
}

GeoPoint DirectProjection::canvas_to_geo(double x, double y) const {
    return {-y / earth_radius, x / earth_radius};
}

PointF MercatorProjection::geo_to_canvas(double latitude, double longitude) const {
    double x = radians(longitude) * earth_radius;
    double y = std::log(std::tan(PI / 4.0 + radians(latitude) / 2.0)) * earth_radius;
    // ekran: y rosnie w dol, wiec -y
    return {x, -y};
}

GeoPoint MercatorProjection::canvas_to_geo(double x, double y) const {
    double longitude = degrees(x / earth_radius);
    y = -y;
    double latitude = degrees(2.0 * std::atan(std::exp(y / earth_radius)) - PI / 2.0);
    return {latitude, longitude};
}

UtmProjection::UtmProjection(GeoBBox bbox) : Projection("UTM", bbox) { map_data_offset_ = calculate_data_offset(); }

int UtmProjection::calculate_data_offset() {
    // UTM obejmuje maksymalnie 6 stopni dlugosci. Jesli mapa jest wezsza, ale lezy w 2 strefach,
    // liczymy przesuniecie, aby przeniesc dane do jednej strefy. -1 = mapa szersza niz 6 stopni.
    if (!map_bbox_.valid) return -1;
    if (map_bbox_.E - map_bbox_.W > 6) return -1;
    if (py::floordiv(map_bbox_.E, 6) == py::floordiv(map_bbox_.W, 6)) return 0;
    return static_cast<int>(std::fmod(std::fmod(map_bbox_.W, 6.0) + 6.0, 6.0));
}

PointF UtmProjection::geo_to_canvas(double latitude, double longitude) const {
    auto c = utm::from_latlon(latitude, longitude - map_data_offset_);
    int northern = 1;
    if (c.zone_letter && *c.zone_letter >= 'B' && *c.zone_letter <= 'M') northern = -1;
    return {c.easting, -(northern * c.northing)};
}

GeoPoint UtmProjection::canvas_to_geo(double, double) const {
    throw std::logic_error("UTM canvas_to_geo nie jest zaimplementowane (tak jak w wersji Python)");
}

namespace utm {

namespace {
constexpr double K0 = 0.9996;
constexpr double E = 0.00669438;
constexpr double E2 = E * E;
constexpr double E3 = E2 * E;
constexpr double E_P2 = E / (1.0 - E);
const double SQRT_E = std::sqrt(1 - E);
const double _E = (1 - SQRT_E) / (1 + SQRT_E);
const double _E2 = _E * _E;
const double _E3 = _E2 * _E;
const double _E4 = _E3 * _E;
const double _E5 = _E4 * _E;
constexpr double M1 = (1 - E / 4 - 3 * E2 / 64 - 5 * E3 / 256);
constexpr double M2 = (3 * E / 8 + 3 * E2 / 32 + 45 * E3 / 1024);
constexpr double M3 = (15 * E2 / 256 + 45 * E3 / 1024);
constexpr double M4 = (35 * E3 / 3072);
const double P2 = (3. / 2 * _E - 27. / 32 * _E3 + 269. / 512 * _E5);
const double P3 = (21. / 16 * _E2 - 55. / 32 * _E4);
const double P4 = (151. / 96 * _E3 - 417. / 128 * _E5);
const double P5 = (1097. / 512 * _E4);
constexpr double R = 6378137;

struct ZoneLetter {
    int lat_min;
    char letter;  // 0 = None
};
constexpr ZoneLetter ZONE_LETTERS[] = {{84, 0},    {72, 'X'},  {64, 'W'},  {56, 'V'},  {48, 'U'},  {40, 'T'},
                                       {32, 'S'},  {24, 'R'},  {16, 'Q'},  {8, 'P'},   {0, 'N'},   {-8, 'M'},
                                       {-16, 'L'}, {-24, 'K'}, {-32, 'J'}, {-40, 'H'}, {-48, 'G'}, {-56, 'F'},
                                       {-64, 'E'}, {-72, 'D'}, {-80, 'C'}};
}  // namespace

std::optional<char> latitude_to_zone_letter(double latitude) {
    for (const auto& z : ZONE_LETTERS) {
        if (latitude >= z.lat_min) {
            if (z.letter == 0) return std::nullopt;
            return z.letter;
        }
    }
    return std::nullopt;
}

int latlon_to_zone_number(double latitude, double longitude) {
    if (56 <= latitude && latitude <= 64 && 3 <= longitude && longitude <= 12) return 32;
    if (72 <= latitude && latitude <= 84 && longitude >= 0) {
        if (longitude <= 9) return 31;
        if (longitude <= 21) return 33;
        if (longitude <= 33) return 35;
        if (longitude <= 42) return 37;
    }
    return static_cast<int>((longitude + 180) / 6) + 1;
}

int zone_number_to_central_longitude(int zone_number) { return (zone_number - 1) * 6 - 180 + 3; }

UtmCoord from_latlon(double latitude, double longitude, std::optional<int> force_zone_number) {
    if (!(-80.0 <= latitude && latitude <= 84.0))
        throw OutOfRangeError("latitude out of range (must be between 80 deg S and 84 deg N)");
    if (!(-180.0 <= longitude && longitude <= 180.0))
        throw OutOfRangeError("northing out of range (must be between 180 deg W and 180 deg E)");

    double lat_rad = radians(latitude);
    double lat_sin = std::sin(lat_rad);
    double lat_cos = std::cos(lat_rad);
    double lat_tan = lat_sin / lat_cos;
    double lat_tan2 = lat_tan * lat_tan;
    double lat_tan4 = lat_tan2 * lat_tan2;

    int zone_number = force_zone_number ? *force_zone_number : latlon_to_zone_number(latitude, longitude);
    auto zone_letter = latitude_to_zone_letter(latitude);

    double lon_rad = radians(longitude);
    double central_lon = zone_number_to_central_longitude(zone_number);
    double central_lon_rad = radians(central_lon);

    double n = R / std::sqrt(1 - E * std::pow(lat_sin, 2));
    double c = E_P2 * std::pow(lat_cos, 2);

    double a = lat_cos * (lon_rad - central_lon_rad);
    double a2 = a * a;
    double a3 = a2 * a;
    double a4 = a3 * a;
    double a5 = a4 * a;
    double a6 = a5 * a;

    double m = R * (M1 * lat_rad - M2 * std::sin(2 * lat_rad) + M3 * std::sin(4 * lat_rad) - M4 * std::sin(6 * lat_rad));

    double easting =
        K0 * n * (a + a3 / 6 * (1 - lat_tan2 + c) + a5 / 120 * (5 - 18 * lat_tan2 + lat_tan4 + 72 * c - 58 * E_P2)) +
        500000;
    double northing = K0 * (m + n * lat_tan *
                                    (a2 / 2 + a4 / 24 * (5 - lat_tan2 + 9 * c + 4 * std::pow(c, 2)) +
                                     a6 / 720 * (61 - 58 * lat_tan2 + lat_tan4 + 600 * c - 330 * E_P2)));
    if (latitude < 0) northing += 10000000;
    return {easting, northing, zone_number, zone_letter};
}

GeoPoint to_latlon(double easting, double northing, int zone_number, std::optional<char> zone_letter,
                   std::optional<bool> northern) {
    if (!zone_letter && !northern) throw std::invalid_argument("either zone_letter or northern needs to be set");
    if (zone_letter && northern) throw std::invalid_argument("set either zone_letter or northern, but not both");
    if (!(100000 <= easting && easting < 1000000))
        throw OutOfRangeError("easting out of range (must be between 100.000 m and 999.999 m)");
    if (!(0 <= northing && northing <= 10000000))
        throw OutOfRangeError("northing out of range (must be between 0 m and 10.000.000 m)");
    if (!(1 <= zone_number && zone_number <= 60))
        throw OutOfRangeError("zone number out of range (must be between 1 and 60)");

    bool is_northern;
    if (zone_letter) {
        char zl = static_cast<char>(std::toupper(static_cast<unsigned char>(*zone_letter)));
        if (!('C' <= zl && zl <= 'X') || zl == 'I' || zl == 'O')
            throw OutOfRangeError("zone letter out of range (must be between C and X)");
        is_northern = zl >= 'N';
    } else {
        is_northern = *northern;
    }

    double x = easting - 500000;
    double y = northing;
    if (!is_northern) y -= 10000000;

    double m = y / K0;
    double mu = m / (R * M1);

    double p_rad = (mu + P2 * std::sin(2 * mu) + P3 * std::sin(4 * mu) + P4 * std::sin(6 * mu) + P5 * std::sin(8 * mu));
    double p_sin = std::sin(p_rad);
    double p_sin2 = p_sin * p_sin;
    double p_cos = std::cos(p_rad);
    double p_tan = p_sin / p_cos;
    double p_tan2 = p_tan * p_tan;
    double p_tan4 = p_tan2 * p_tan2;

    double ep_sin = 1 - E * p_sin2;
    double ep_sin_sqrt = std::sqrt(1 - E * p_sin2);

    double n = R / ep_sin_sqrt;
    double r = (1 - E) / ep_sin;

    double c = _E * std::pow(p_cos, 2);
    double c2 = c * c;

    double d = x / (n * K0);
    double d2 = d * d;
    double d3 = d2 * d;
    double d4 = d3 * d;
    double d5 = d4 * d;
    double d6 = d5 * d;

    // Uwaga: nawiasowanie identyczne z oryginalem (wyraz d6 jest poza mnozeniem przez p_tan/r).
    double latitude = (p_rad - (p_tan / r) * (d2 / 2 - d4 / 24 * (5 + 3 * p_tan2 + 10 * c - 4 * c2 - 9 * E_P2)) +
                       d6 / 720 * (61 + 90 * p_tan2 + 298 * c + 45 * p_tan4 - 252 * E_P2 - 3 * c2));
    double longitude =
        (d - d3 / 6 * (1 + 2 * p_tan2 + c) + d5 / 120 * (5 - 2 * c + 28 * p_tan2 - 3 * c2 + 8 * E_P2 + 24 * p_tan4)) /
        p_cos;

    return {degrees(latitude), degrees(longitude) + zone_number_to_central_longitude(zone_number)};
}

}  // namespace utm

}  // namespace pwm
