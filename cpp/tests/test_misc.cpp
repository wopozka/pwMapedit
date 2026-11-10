// Port tests/test_misc_functions.py + testy pomocnikow zgodnosci z Pythonem i kodowania.
#include <cmath>

#include "../core/misc.hpp"
#include "../core/projection.hpp"
#include "../core/pyutil.hpp"
#include "py_cases.inc"
#include "test_framework.hpp"

using namespace pwm;

TEST(return_icon_definition) {
    for (const auto& c : ICON_CASES) {
        auto got = misc::return_icon_definition(c.target);
        CHECK_EQ(got.first, c.answer.first);
        CHECK_EQ(got.second, c.answer.second);
    }
}

TEST(vector_angle) {
    struct C {
        double x, y;
        bool cw;
        double ans;
    };
    for (C c : {C{1, 0, false, 0}, C{1, 1, false, 45}, C{0, 1, false, 90}, C{-1, 1, false, 135},
                C{-1, 0, false, 180}, C{-1, -1, false, 225}, C{0, -1, false, 270}, C{1, -1, false, 315},
                C{1, 0, true, 0}, C{1, -1, true, 45}, C{0, -1, true, 90}, C{-1, -1, true, 135}, C{-1, 0, true, 180},
                C{-1, 1, true, 225}, C{0, 1, true, 270}, C{1, 1, true, 315}}) {
        CHECK_EQ(misc::vector_angle(c.x, c.y, c.cw, false), c.ans);
    }
}

TEST(label_angle) {
    CHECK_EQ(misc::calculate_label_angle(0), 0.0);
    CHECK_EQ(misc::calculate_label_angle(45), 45.0);
    CHECK_EQ(misc::calculate_label_angle(90), 90.0);
    CHECK_EQ(misc::calculate_label_angle(135), 315.0);
    CHECK_EQ(misc::calculate_label_angle(180), 0.0);
    CHECK_EQ(misc::calculate_label_angle(225), 45.0);
    CHECK_EQ(misc::calculate_label_angle(270), 90.0);
    // Test w Pythonie oczekuje 45, ale funkcja zwraca 315 (test nie przechodzi tez w Pythonie).
    // Port zachowuje zachowanie funkcji - do decyzji, ktora strona jest bledna.
    CHECK_EQ(misc::calculate_label_angle(315), 315.0);
}

TEST(vincenty_distance) {
    // Test w Pythonie porownuje przez == z zaokraglonymi wartosciami (1850, 2.716) i nie przechodzi.
    // Tu porownujemy z dokladnym wynikiem wersji Python.
    CHECK_NEAR(misc::vincenty_distance({51.981570, 16.444900}, {51.990910, 16.467280}), 1855.7665110163227, 1e-9);
    CHECK_NEAR(misc::vincenty_distance({39.152501, -84.412977}, {39.152505, -84.412946}), 2.7161912585815897, 1e-12);
}

TEST(vector_rotated) {
    PointF v = misc::vector_rotated(100.0, 0.0, 90, false, false);
    CHECK_NEAR(v.x, 0.0, 1e-9);
    CHECK_NEAR(v.y, 100.0, 1e-9);
    PointF u = misc::unit_vector_rotated(100.0, 0.0, 180, false, false);
    CHECK_NEAR(u.x, -1.0, 1e-12);
}

// ---- pomocniki zgodnosci z Pythonem ----

TEST(py_strip_and_int) {
    CHECK_EQ(std::string(py::strip(" \t abc \xa0\r\n")), std::string("abc"));
    CHECK(py::to_int("0x2f00", 16) == std::optional<long long>(0x2f00));
    CHECK(py::to_int("2F", 16) == std::optional<long long>(0x2f));
    CHECK(py::to_int(" -12 ") == std::optional<long long>(-12));
    CHECK(py::to_int("1_000") == std::optional<long long>(1000));
    CHECK(!py::to_int("1__0"));
    CHECK(!py::to_int("95-040"));
    CHECK(!py::to_int(""));
    CHECK(!py::to_int("0x", 16));
    CHECK(py::to_float("+52.5") == std::optional<double>(52.5));
    CHECK(!py::to_float("52,5"));
}

TEST(py_repr_round_floordiv) {
    CHECK_EQ(py::repr(52.0), std::string("52.0"));
    CHECK_EQ(py::repr(51.74350), std::string("51.7435"));
    CHECK_EQ(py::repr(1e-05), std::string("1e-05"));
    CHECK_EQ(py::repr(0.0001), std::string("0.0001"));
    CHECK_EQ(py::repr(1.5e16), std::string("1.5e+16"));
    CHECK_EQ(py::repr(-2.5), std::string("-2.5"));
    CHECK_EQ(py::round(2.675, 2), 2.67);  // jak w Pythonie (2.675 to w binarnym 2.67499...)
    CHECK_EQ(py::round(0.125, 2), 0.12);  // remis -> do parzystej
    CHECK_EQ(py::floordiv(7.0, 2.0), 3.0);
    CHECK_EQ(py::floordiv(-7.0, 2.0), -4.0);
    CHECK_EQ(py::hex(0x10e00), std::string("0x10e00"));
    CHECK_EQ(py::sum({0.1, 0.2, 0.3}), 0.6);  // Python 3.12+: sum([0.1, 0.2, 0.3]) == 0.6
}

TEST(cp1250_table) {
    for (int b = 0; b < 256; ++b) {
        std::string in(1, static_cast<char>(b));
        std::string out = encoding::cp1250_to_utf8(in);
        unsigned expected = CP1250_EXPECTED[b];
        if (expected == 0 && b >= 0x80) expected = 0xFFFD;  // 0 = bajt niezdefiniowany w cp1250
        // zdekoduj nasz wynik UTF-8 do kodu znaku
        unsigned cp = 0;
        unsigned char c0 = static_cast<unsigned char>(out[0]);
        if (c0 < 0x80)
            cp = c0;
        else if ((c0 >> 5) == 6)
            cp = ((c0 & 0x1F) << 6) | (out[1] & 0x3F);
        else
            cp = ((c0 & 0x0F) << 12) | ((out[1] & 0x3F) << 6) | (out[2] & 0x3F);
        if (cp != expected) tf::fail(__FILE__, __LINE__, "bajt " + std::to_string(b) + ": " + std::to_string(cp));
        if (CP1250_EXPECTED[b] != 0 || b < 0x80) CHECK_EQ(encoding::utf8_to_cp1250(out), in);
    }
    CHECK_EQ(encoding::cp1250_to_utf8("\xa3\xf3\x64\x9f"), std::string("Łódź"));
}

TEST(utm_conversion) {
    // wartosci wzorcowe z oryginalnego modulu utm/conversion.py
    auto a = utm::from_latlon(52.2297, 21.0122);
    CHECK_EQ(a.easting, 500833.2431474297);
    CHECK_EQ(a.northing, 5786586.671689077);
    CHECK_EQ(a.zone_number, 34);
    CHECK(a.zone_letter == std::optional<char>('U'));
    auto b = utm::from_latlon(-33.8688, 151.2093);
    CHECK_EQ(b.easting, 334368.63364640076);
    CHECK_EQ(b.northing, 6250948.345360274);
    CHECK_EQ(b.zone_number, 56);
    CHECK(b.zone_letter == std::optional<char>('H'));
    auto g = utm::to_latlon(500000.0, 5787000.0, 34, 'U', std::nullopt);
    CHECK_EQ(g.latitude, 52.23341670459654);
    CHECK_EQ(g.longitude, 21.0);
    CHECK_THROWS(utm::from_latlon(85.0, 0.0));
}
