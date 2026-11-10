#include "misc.hpp"

#include <cmath>
#include <fstream>
#include <sstream>

#include "map_data.hpp"
#include "pyutil.hpp"

namespace pwm::misc {

using py::degrees;
using py::radians;

double vector_angle(double x, double y, bool clockwise, bool screen_coord_system) {
    if (screen_coord_system) y = -y;
    if (x == 0) {
        if (clockwise) return y < 0 ? 90 : 270;
        return y > 0 ? 90 : 270;
    }
    double y_by_x = py::round(y / x, 5);
    if (y_by_x == 0) return x > 0 ? 0 : 180;
    double calc_degrees = degrees(std::atan(y_by_x));
    if (x > 0) {
        if (clockwise) return y < 0 ? -calc_degrees : 360 - calc_degrees;
        return y > 0 ? calc_degrees : 360 + calc_degrees;
    }
    return clockwise ? 180 - calc_degrees : 180 + calc_degrees;
}

double vector_length(double x, double y) { return std::sqrt(x * x + y * y); }

PointF unit_vector(double x, double y) {
    double l = vector_length(x, y);
    return {x / l, y / l};
}

PointF vector_rotated(double x, double y, double rotation_angle, bool clockwise, bool screen_coord_system) {
    double angle = vector_angle(x, y, clockwise, screen_coord_system);
    double length = vector_length(x, y);
    double new_angle_radians = (angle + rotation_angle) / 180 * py::PI;
    PointF v{length * std::cos(new_angle_radians), length * std::sin(new_angle_radians)};
    if (screen_coord_system) v.y = -v.y;
    return v;
}

PointF unit_vector_rotated(double x, double y, double rotation_angle, bool clockwise, bool screen_coord_system) {
    PointF vr = vector_rotated(x, y, rotation_angle, clockwise, screen_coord_system);
    double l = vector_length(vr.x, vr.y);
    return {vr.x / l, vr.y / l};
}

double calculate_label_angle(double angle) {
    if (0 <= angle && angle <= 90) return angle;
    if (90 < angle && angle < 180) return 180 + angle;
    if (angle == 180) return 0;
    if (180 < angle && angle <= 270) return angle - 180;
    return angle;
}

double great_circle_distance(GeoPoint coord1, GeoPoint coord2) {
    double lat1 = radians(coord1.latitude);
    double lon1 = radians(coord1.longitude);
    double lat2 = radians(coord2.latitude);
    double lon2 = radians(coord1.longitude);  // blad z oryginalu zachowany
    return 6371 * std::acos(std::sin(lat1) * std::sin(lat2) + std::cos(lat1) * std::cos(lat2) * std::cos(lon1 - lon2));
}

double vincenty_distance(GeoPoint coord1, GeoPoint coord2) {
    const double a = 6378137.0;
    const double f = 1 / 298.257223563;
    const double b = (1 - f) * a;
    const int max_iter = 200;
    const double tol = 1e-12;

    double phi_1 = coord1.latitude, L_1 = coord1.longitude;
    double phi_2 = coord2.latitude, L_2 = coord2.longitude;
    double u_1 = std::atan((1 - f) * std::tan(radians(phi_1)));
    double u_2 = std::atan((1 - f) * std::tan(radians(phi_2)));
    double L = radians(L_2 - L_1);
    double Lambda = L;
    double sin_u1 = std::sin(u_1), cos_u1 = std::cos(u_1);
    double sin_u2 = std::sin(u_2), cos_u2 = std::cos(u_2);

    double sin_sigma = 0, cos_sigma = 0, sigma = 0, cos_sq_alpha = 0, cos2_sigma_m = 0;
    for (int i = 0; i < max_iter; ++i) {
        double cos_lambda = std::cos(Lambda);
        double sin_lambda = std::sin(Lambda);
        sin_sigma = std::sqrt(std::pow(cos_u2 * std::sin(Lambda), 2) +
                              std::pow(cos_u1 * sin_u2 - sin_u1 * cos_u2 * cos_lambda, 2));
        cos_sigma = sin_u1 * sin_u2 + cos_u1 * cos_u2 * cos_lambda;
        sigma = std::atan2(sin_sigma, cos_sigma);
        double sin_alpha = (cos_u1 * cos_u2 * sin_lambda) / sin_sigma;
        cos_sq_alpha = 1 - std::pow(sin_alpha, 2);
        cos2_sigma_m = cos_sigma - ((2 * sin_u1 * sin_u2) / cos_sq_alpha);
        double C = (f / 16) * cos_sq_alpha * (4 + f * (4 - 3 * cos_sq_alpha));
        double Lambda_prev = Lambda;
        Lambda = L + (1 - C) * f * sin_alpha *
                         (sigma + C * sin_sigma * (cos2_sigma_m + C * cos_sigma * (-1 + 2 * std::pow(cos2_sigma_m, 2))));
        if (std::fabs(Lambda_prev - Lambda) <= tol) break;
    }
    double u_sq = cos_sq_alpha * ((std::pow(a, 2) - std::pow(b, 2)) / std::pow(b, 2));
    double A = 1 + (u_sq / 16384) * (4096 + u_sq * (-768 + u_sq * (320 - 175 * u_sq)));
    double B = (u_sq / 1024) * (256 + u_sq * (-128 + u_sq * (74 - 47 * u_sq)));
    double delta_sig =
        B * sin_sigma *
        (cos2_sigma_m + 0.25 * B *
                            (cos_sigma * (-1 + 2 * std::pow(cos2_sigma_m, 2)) -
                             (1.0 / 6) * B * cos2_sigma_m * (-3 + 4 * std::pow(sin_sigma, 2)) *
                                 (-3 + 4 * std::pow(cos2_sigma_m, 2))));
    return b * A * (sigma - delta_sig);
}

std::pair<std::string, std::string> return_icon_definition(const std::vector<std::string>& icon_def) {
    std::string l_type, l_subtype;
    std::string l_icon = "/* XPM */\n static const unsigned char * day_xpm[] = {\n";
    bool in_xpm_def = false;
    for (const std::string& l_line : icon_def) {
        if (in_xpm_def) {
            l_icon += l_line;
            l_icon += '\n';
            continue;
        }
        if (py::starts_with(l_line, "Type=")) {
            l_type = std::string(py::strip(std::string_view(l_line).substr(l_line.find('=') + 1)));
        } else if (py::starts_with(l_line, "SubType=")) {
            l_subtype = std::string(py::strip(std::string_view(l_line).substr(l_line.find('=') + 1)));
        } else if (size_t p = l_line.find("xpm="); p != std::string::npos) {
            // split('xpm=', 1)[-1]
            l_icon += l_line.substr(p + 4);
            l_icon += '\n';
            in_xpm_def = true;
        }
    }
    // l_subtype.split('x')[-1].strip()
    size_t x = l_subtype.rfind('x');
    std::string_view sub = x == std::string::npos ? std::string_view(l_subtype) : std::string_view(l_subtype).substr(x + 1);
    return {l_type + std::string(py::strip(sub)), l_icon};
}

std::map<std::string, std::string> read_icons_from_skin_file(const std::string& skin_filename) {
    std::map<std::string, std::string> poi_type_icon;
    std::ifstream f(skin_filename, std::ios::binary);
    if (!f) return poi_type_icon;
    std::stringstream ss;
    ss << f.rdbuf();
    std::string content = ss.str();
    std::vector<std::string> icon_def;
    bool in_poi = false;
    for (std::string_view linia : split_lines(content)) {
        if (in_poi) {
            if (linia.find("[end]") != std::string_view::npos) {
                in_poi = false;
                auto [type, icon] = return_icon_definition(icon_def);
                poi_type_icon[type] = icon;
                icon_def.clear();
            } else {
                icon_def.emplace_back(py::strip(linia));
            }
            continue;
        }
        if (linia.find("[_point]") != std::string_view::npos) in_poi = true;
    }
    return poi_type_icon;
}

}  // namespace pwm::misc

namespace pwm::encoding {

namespace {
// Znaki Unicode dla bajtow 0x80-0xFF w cp1250 (0 = bajt niezdefiniowany).
constexpr char16_t CP1250_HIGH[128] = {
    0x20AC, 0,      0x201A, 0,      0x201E, 0x2026, 0x2020, 0x2021, 0,      0x2030, 0x0160, 0x2039, 0x015A, 0x0164, 0x017D, 0x0179,
    0,      0x2018, 0x2019, 0x201C, 0x201D, 0x2022, 0x2013, 0x2014, 0,      0x2122, 0x0161, 0x203A, 0x015B, 0x0165, 0x017E, 0x017A,
    0x00A0, 0x02C7, 0x02D8, 0x0141, 0x00A4, 0x0104, 0x00A6, 0x00A7, 0x00A8, 0x00A9, 0x015E, 0x00AB, 0x00AC, 0x00AD, 0x00AE, 0x017B,
    0x00B0, 0x00B1, 0x02DB, 0x0142, 0x00B4, 0x00B5, 0x00B6, 0x00B7, 0x00B8, 0x0105, 0x015F, 0x00BB, 0x013D, 0x02DD, 0x013E, 0x017C,
    0x0154, 0x00C1, 0x00C2, 0x0102, 0x00C4, 0x0139, 0x0106, 0x00C7, 0x010C, 0x00C9, 0x0118, 0x00CB, 0x011A, 0x00CD, 0x00CE, 0x010E,
    0x0110, 0x0143, 0x0147, 0x00D3, 0x00D4, 0x0150, 0x00D6, 0x00D7, 0x0158, 0x016E, 0x00DA, 0x0170, 0x00DC, 0x00DD, 0x0162, 0x00DF,
    0x0155, 0x00E1, 0x00E2, 0x0103, 0x00E4, 0x013A, 0x0107, 0x00E7, 0x010D, 0x00E9, 0x0119, 0x00EB, 0x011B, 0x00ED, 0x00EE, 0x010F,
    0x0111, 0x0144, 0x0148, 0x00F3, 0x00F4, 0x0151, 0x00F6, 0x00F7, 0x0159, 0x016F, 0x00FA, 0x0171, 0x00FC, 0x00FD, 0x0163, 0x02D9,
};

void append_utf8(std::string& out, char32_t cp) {
    if (cp < 0x80) {
        out += static_cast<char>(cp);
    } else if (cp < 0x800) {
        out += static_cast<char>(0xC0 | (cp >> 6));
        out += static_cast<char>(0x80 | (cp & 0x3F));
    } else if (cp < 0x10000) {
        out += static_cast<char>(0xE0 | (cp >> 12));
        out += static_cast<char>(0x80 | ((cp >> 6) & 0x3F));
        out += static_cast<char>(0x80 | (cp & 0x3F));
    } else {
        out += static_cast<char>(0xF0 | (cp >> 18));
        out += static_cast<char>(0x80 | ((cp >> 12) & 0x3F));
        out += static_cast<char>(0x80 | ((cp >> 6) & 0x3F));
        out += static_cast<char>(0x80 | (cp & 0x3F));
    }
}
}  // namespace

std::string cp1250_to_utf8(const std::string& in) {
    std::string out;
    out.reserve(in.size() + in.size() / 8);
    for (unsigned char c : in) {
        if (c < 0x80) {
            out += static_cast<char>(c);
        } else {
            char16_t u = CP1250_HIGH[c - 0x80];
            append_utf8(out, u ? u : 0xFFFD);
        }
    }
    return out;
}

std::string utf8_to_cp1250(const std::string& in, bool* ok) {
    std::string out;
    out.reserve(in.size());
    bool all_ok = true;
    for (size_t i = 0; i < in.size();) {
        unsigned char c = static_cast<unsigned char>(in[i]);
        char32_t cp;
        size_t len;
        if (c < 0x80) {
            cp = c;
            len = 1;
        } else if ((c >> 5) == 0x6 && i + 1 < in.size()) {
            cp = ((c & 0x1F) << 6) | (in[i + 1] & 0x3F);
            len = 2;
        } else if ((c >> 4) == 0xE && i + 2 < in.size()) {
            cp = ((c & 0x0F) << 12) | ((in[i + 1] & 0x3F) << 6) | (in[i + 2] & 0x3F);
            len = 3;
        } else if ((c >> 3) == 0x1E && i + 3 < in.size()) {
            cp = ((c & 0x07) << 18) | ((in[i + 1] & 0x3F) << 12) | ((in[i + 2] & 0x3F) << 6) | (in[i + 3] & 0x3F);
            len = 4;
        } else {
            cp = 0xFFFD;
            len = 1;
        }
        i += len;
        if (cp < 0x80) {
            out += static_cast<char>(cp);
            continue;
        }
        char found = 0;
        for (int k = 0; k < 128; ++k) {
            if (CP1250_HIGH[k] == cp) {
                found = static_cast<char>(0x80 + k);
                break;
            }
        }
        if (found) {
            out += found;
        } else {
            out += '?';
            all_ok = false;
        }
    }
    if (ok) *ok = all_ok;
    return out;
}

}  // namespace pwm::encoding
