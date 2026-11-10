// Funkcje pomocnicze odtwarzajace semantyke Pythona tam, gdzie wplywa ona na wynik
// (parsowanie liczb, strip(), round(), dzielenie calkowite, formatowanie).
// Dzieki temu port C++ daje bajt w bajt te same pliki co wersja Pythonowa.
#pragma once

#include <optional>
#include <string>
#include <string_view>
#include <vector>

namespace pwm::py {

// Bialy znak w rozumieniu str.isspace() dla tekstu zdekodowanego z cp1250
// (ASCII whitespace, 0x1C-0x1F oraz 0xA0 = U+00A0 NO-BREAK SPACE).
bool is_space(unsigned char c);

std::string_view strip(std::string_view s);
std::string_view lstrip(std::string_view s, char c);
std::string_view rstrip(std::string_view s, char c);

inline bool starts_with(std::string_view s, std::string_view prefix) {
    return s.substr(0, prefix.size()) == prefix;
}
inline bool ends_with(std::string_view s, std::string_view suffix) {
    return s.size() >= suffix.size() && s.substr(s.size() - suffix.size()) == suffix;
}

// str.split(sep) - bez limitu.
std::vector<std::string_view> split(std::string_view s, std::string_view sep);

// int(s, base): biale znaki, znak +/-, prefiks 0x dla base=16, podkreslenia miedzy cyframi.
// std::nullopt odpowiada ValueError w Pythonie.
std::optional<long long> to_int(std::string_view s, int base = 10);

// float(s): biale znaki, znak, inf/nan. std::nullopt odpowiada ValueError.
std::optional<double> to_float(std::string_view s);

// f'{v:.{precision}f}' - dopisuje do out.
void append_fixed(std::string& out, double v, int precision);
std::string format_fixed(double v, int precision);

// round(v, ndigits) dla floatow (zaokraglenie dokladnej wartosci binarnej, remis do parzystej).
double round(double v, int ndigits);

// a // b dla floatow (algorytm z CPython float_floor_div).
double floordiv(double a, double b);

// sum() dla floatow - od Pythona 3.12 sumowanie kompensowane (Neumaier), jak w CPython.
double sum(const std::vector<double>& values);

// repr(v) dla floata: najkrotsza reprezentacja jak w Pythonie ('52.0', '1e-05', '1.5e+16').
std::string repr(double v);

// hex(v): '0x1f', '-0x1f'.
std::string hex(long long v);

// math.radians / math.degrees dokladnie jak w CPython.
double radians(double deg);
double degrees(double rad);

constexpr double PI = 3.141592653589793238462643383279502884;

}  // namespace pwm::py
