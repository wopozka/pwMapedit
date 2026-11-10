#include "pyutil.hpp"

#include <charconv>
#include <cmath>
#include <cstdio>
#include <cstdlib>

namespace pwm::py {

bool is_space(unsigned char c) {
    return c == ' ' || (c >= 0x09 && c <= 0x0D) || (c >= 0x1C && c <= 0x1F) || c == 0xA0;
}

std::string_view strip(std::string_view s) {
    size_t b = 0, e = s.size();
    while (b < e && is_space(static_cast<unsigned char>(s[b]))) ++b;
    while (e > b && is_space(static_cast<unsigned char>(s[e - 1]))) --e;
    return s.substr(b, e - b);
}

std::string_view lstrip(std::string_view s, char c) {
    size_t b = 0;
    while (b < s.size() && s[b] == c) ++b;
    return s.substr(b);
}

std::string_view rstrip(std::string_view s, char c) {
    size_t e = s.size();
    while (e > 0 && s[e - 1] == c) --e;
    return s.substr(0, e);
}

std::vector<std::string_view> split(std::string_view s, std::string_view sep) {
    std::vector<std::string_view> out;
    size_t pos = 0;
    while (true) {
        size_t f = s.find(sep, pos);
        if (f == std::string_view::npos) {
            out.push_back(s.substr(pos));
            return out;
        }
        out.push_back(s.substr(pos, f - pos));
        pos = f + sep.size();
    }
}

static int digit_value(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'z') return c - 'a' + 10;
    if (c >= 'A' && c <= 'Z') return c - 'A' + 10;
    return 99;
}

std::optional<long long> to_int(std::string_view s, int base) {
    s = strip(s);
    bool neg = false;
    if (!s.empty() && (s[0] == '+' || s[0] == '-')) {
        neg = s[0] == '-';
        s.remove_prefix(1);
    }
    bool after_prefix = false;
    if (base == 16 && s.size() >= 2 && s[0] == '0' && (s[1] == 'x' || s[1] == 'X')) {
        s.remove_prefix(2);
        after_prefix = true;
    }
    if (s.empty()) return std::nullopt;
    unsigned long long value = 0;
    bool prev_digit = after_prefix;  // po "0x" wolno postawic '_'
    bool any_digit = false;
    for (char c : s) {
        if (c == '_') {
            if (!prev_digit) return std::nullopt;
            prev_digit = false;
            continue;
        }
        int d = digit_value(c);
        if (d >= base) return std::nullopt;
        if (value > (~0ULL - d) / base) return std::nullopt;  // poza zakresem long long - traktujemy jak blad
        value = value * base + d;
        prev_digit = true;
        any_digit = true;
    }
    if (!any_digit || !prev_digit) return std::nullopt;
    constexpr unsigned long long max_pos = 9223372036854775807ULL;
    if (value > max_pos + (neg ? 1ULL : 0ULL)) return std::nullopt;
    if (neg) return value == max_pos + 1ULL ? (-9223372036854775807LL - 1) : -static_cast<long long>(value);
    return static_cast<long long>(value);
}

std::optional<double> to_float(std::string_view s) {
    s = strip(s);
    if (!s.empty() && s[0] == '+') {
        s.remove_prefix(1);
        if (!s.empty() && (s[0] == '+' || s[0] == '-')) return std::nullopt;
    }
    if (s.empty()) return std::nullopt;
    double v = 0;
    auto res = std::from_chars(s.data(), s.data() + s.size(), v);
    if (res.ec != std::errc() || res.ptr != s.data() + s.size()) {
        if (res.ec == std::errc::result_out_of_range && res.ptr == s.data() + s.size()) {
            // Python: float('1e999') == inf, float('1e-999') == 0.0
            std::string tmp(s);
            return std::strtod(tmp.c_str(), nullptr);
        }
        return std::nullopt;
    }
    return v;
}

void append_fixed(std::string& out, double v, int precision) {
    char buf[400];
    auto res = std::to_chars(buf, buf + sizeof(buf), v, std::chars_format::fixed, precision);
    if (res.ec == std::errc()) {
        out.append(buf, res.ptr);
    } else {
        std::string big(4096, '\0');
        int n = std::snprintf(big.data(), big.size(), "%.*f", precision, v);
        out.append(big.data(), n);
    }
}

std::string format_fixed(double v, int precision) {
    std::string s;
    append_fixed(s, v, precision);
    return s;
}

double round(double v, int ndigits) {
    if (!std::isfinite(v)) return v;
    // CPython: zaokraglenie przez poprawnie zaokraglona reprezentacje dziesietna.
    std::string s = format_fixed(v, ndigits);
    return std::strtod(s.c_str(), nullptr);
}

double floordiv(double vx, double wx) {
    double mod = std::fmod(vx, wx);
    double div = (vx - mod) / wx;
    if (mod != 0.0) {
        if ((wx < 0) != (mod < 0)) div -= 1.0;
    }
    double floordiv;
    if (div != 0.0) {
        floordiv = std::floor(div);
        if (div - floordiv > 0.5) floordiv += 1.0;
    } else {
        floordiv = std::copysign(0.0, vx / wx);
    }
    return floordiv;
}

double sum(const std::vector<double>& values) {
    double f_result = 0.0;
    double c = 0.0;
    for (double x : values) {
        double t = f_result + x;
        if (std::fabs(f_result) >= std::fabs(x)) {
            c += (f_result - t) + x;
        } else {
            c += (x - t) + f_result;
        }
        f_result = t;
    }
    if (c != 0.0 && std::isfinite(c)) f_result += c;
    return f_result;
}

std::string repr(double v) {
    if (std::isnan(v)) return "nan";
    if (std::isinf(v)) return v > 0 ? "inf" : "-inf";
    char buf[64];
    auto res = std::to_chars(buf, buf + sizeof(buf), v, std::chars_format::scientific);
    std::string_view s(buf, res.ptr - buf);
    bool neg = false;
    if (!s.empty() && s[0] == '-') {
        neg = true;
        s.remove_prefix(1);
    }
    size_t e = s.find('e');
    std::string digits;
    for (char c : s.substr(0, e))
        if (c != '.') digits += c;
    int exp10 = std::atoi(std::string(s.substr(e + 1)).c_str());
    // usun zera na koncu mantysy (to_chars daje najkrotsza postac, ale dla pewnosci)
    while (digits.size() > 1 && digits.back() == '0') digits.pop_back();
    int decpt = exp10 + 1;
    int nd = static_cast<int>(digits.size());
    std::string out = neg ? "-" : "";
    if (decpt <= -4 || decpt > 16) {
        out += digits[0];
        if (nd > 1) {
            out += '.';
            out += digits.substr(1);
        }
        char eb[16];
        std::snprintf(eb, sizeof(eb), "e%c%02d", exp10 < 0 ? '-' : '+', exp10 < 0 ? -exp10 : exp10);
        out += eb;
    } else if (decpt <= 0) {
        out += "0.";
        out.append(static_cast<size_t>(-decpt), '0');
        out += digits;
    } else if (decpt >= nd) {
        out += digits;
        out.append(static_cast<size_t>(decpt - nd), '0');
        out += ".0";
    } else {
        out += digits.substr(0, decpt);
        out += '.';
        out += digits.substr(decpt);
    }
    return out;
}

std::string hex(long long v) {
    char buf[32];
    if (v < 0) {
        std::snprintf(buf, sizeof(buf), "-0x%llx", static_cast<unsigned long long>(-(v + 1)) + 1ULL);
    } else {
        std::snprintf(buf, sizeof(buf), "0x%llx", static_cast<unsigned long long>(v));
    }
    return buf;
}

double radians(double deg) {
    static const double deg_to_rad = PI / 180.0;
    return deg * deg_to_rad;
}

double degrees(double rad) {
    static const double rad_to_deg = 180.0 / PI;
    return rad * rad_to_deg;
}

}  // namespace pwm::py
