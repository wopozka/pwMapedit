// Testy line_crossings (Tools -> Dodaj bojki wiadukt).
#include <cmath>

#include "../core/line_crossings.hpp"
#include "test_framework.hpp"

using namespace pwm;

namespace {
bool has_point(const std::vector<PointF>& points, double x, double y) {
    for (const PointF& p : points)
        if (std::hypot(p.x - x, p.y - y) < 1e-9) return true;
    return false;
}
}  // namespace

TEST(line_crossings_proper_crossing) {
    // krzyz: pozioma i pionowa przecinaja sie w (5, 0)
    const auto pts = line_crossings({{{0, 0}, {10, 0}}}, {{{5, -5}, {5, 5}}}, 0.5);
    CHECK_EQ(pts.size(), size_t{1});
    CHECK(has_point(pts, 5, 0));
    // kolejnosc linii bez znaczenia
    CHECK(has_point(line_crossings({{{5, -5}, {5, 5}}}, {{{0, 0}, {10, 0}}}, 0.5), 5, 0));
}

TEST(line_crossings_several_and_parts) {
    // linia zygzakiem przecina pozioma trzy razy; druga czesc linii b tez przecina
    const LinePart zigzag{{0, -1}, {2, 1}, {4, -1}, {6, 1}};
    const auto pts = line_crossings({zigzag}, {{{-1, 0}, {7, 0}}, {{0.5, -5}, {0.5, 5}}}, 0.1);
    CHECK_EQ(pts.size(), size_t{4});
    CHECK(has_point(pts, 1, 0));
    CHECK(has_point(pts, 3, 0));
    CHECK(has_point(pts, 5, 0));
    CHECK(has_point(pts, 0.5, -0.5));
}

TEST(line_crossings_skips_junctions_and_touches) {
    // wspolny wezel (zwykle skrzyzowanie) - nie jest przeciecie
    CHECK(line_crossings({{{0, 0}, {5, 0}, {10, 0}}}, {{{5, -5}, {5, 0}, {5, 5}}}, 0.5).empty());
    // droga konczy sie na drugiej (styk T), koniec we wnetrzu odcinka
    CHECK(line_crossings({{{0, 0}, {10, 0}}}, {{{5, 5}, {5, 0}}}, 0.5).empty());
    // brak przeciecia, rownolegle, nakladajace sie
    CHECK(line_crossings({{{0, 0}, {10, 0}}}, {{{0, 1}, {10, 1}}}, 0.5).empty());
    CHECK(line_crossings({{{0, 0}, {10, 0}}}, {{{2, 0}, {8, 0}}}, 0.5).empty());
    CHECK(line_crossings({{{0, 0}, {10, 0}}}, {{{20, -5}, {20, 5}}}, 0.5).empty());
    // wezel jednej linii dotyka drugiej, ale linia wraca na te sama strone - nie przechodzi
    CHECK(line_crossings({{{0, 0}, {10, 0}}}, {{{3, 5}, {5, 0}, {7, 5}}}, 0.5).empty());
}

TEST(line_crossings_node_on_segment) {
    // wezel linii b lezy dokladnie na odcinku linii a i b przechodzi na druga strone - przeciecie (jedno)
    const auto pts = line_crossings({{{0, 0}, {10, 0}}}, {{{3, 5}, {5, 0}, {7, -5}}}, 0.5);
    CHECK_EQ(pts.size(), size_t{1});
    CHECK(has_point(pts, 5, 0));
    // i odwrotnie: wezel linii a na odcinku linii b
    const auto pts2 = line_crossings({{{3, 5}, {5, 0}, {7, -5}}}, {{{0, 0}, {10, 0}}}, 0.5);
    CHECK_EQ(pts2.size(), size_t{1});
}

TEST(line_crossings_roundabout_and_merge) {
    // rondo (zamkniety kwadrat) i droga przez nie: dwa przeciecia; wezel startowy ronda na drodze tez liczy sie
    const LinePart ring{{0, -2}, {2, 0}, {0, 2}, {-2, 0}, {0, -2}};
    const auto pts = line_crossings({ring}, {{{0, -5}, {0, 5}}}, 0.5);
    CHECK_EQ(pts.size(), size_t{2});
    CHECK(has_point(pts, 0, -2));
    CHECK(has_point(pts, 0, 2));
    // punkty blizsze niz merge_distance - jeden
    const LinePart close{{0, -1}, {0.1, 1}, {0.2, -1}};
    CHECK_EQ(line_crossings({close}, {{{-1, 0}, {1, 0}}}, 0.5).size(), size_t{1});
    CHECK_EQ(line_crossings({close}, {{{-1, 0}, {1, 0}}}, 0.01).size(), size_t{2});
}
