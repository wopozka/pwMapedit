// Dane GPS: upraszczanie sladow.
#include <algorithm>
#include <cmath>

#include "../core/gps_data.hpp"
#include "test_framework.hpp"

using namespace pwm::gps;

namespace {
// punkty co ~1 m na linii prostej wzdluz rownoleznika 52
std::vector<Point> straight(int n) {
    std::vector<Point> pts;
    for (int i = 0; i < n; ++i) pts.push_back({52.0, 21.0 + i * 1.0 / 68600.0, std::nullopt, std::nullopt});
    return pts;
}
}  // namespace

TEST(gps_simplify_straight_line_keeps_ends) {
    auto idx = simplify(straight(100), 3.0);
    CHECK_EQ(idx.size(), size_t{2});
    CHECK_EQ(idx.front(), size_t{0});
    CHECK_EQ(idx.back(), size_t{99});
}

TEST(gps_simplify_keeps_corner) {
    // litera L: 50 m na wschod, potem 50 m na polnoc; rog musi zostac
    std::vector<Point> pts = straight(51);
    for (int i = 1; i <= 50; ++i) pts.push_back({52.0 + i / 111200.0, pts[50].lon, std::nullopt, std::nullopt});
    auto idx = simplify(pts, 3.0);
    CHECK_EQ(idx.size(), size_t{3});
    CHECK_EQ(idx[1], size_t{50});
}

TEST(gps_simplify_small_noise_removed_large_kept) {
    std::vector<Point> pts = straight(41);
    pts[10].lat += 1.0 / 111200.0;   // 1 m odchylenia - ponizej tolerancji
    pts[30].lat += 10.0 / 111200.0;  // 10 m - zostaje
    auto idx = simplify(pts, 3.0);
    CHECK(std::find(idx.begin(), idx.end(), size_t{10}) == idx.end());
    CHECK(std::find(idx.begin(), idx.end(), size_t{30}) != idx.end());
}

TEST(gps_simplify_zero_tolerance_and_short) {
    CHECK_EQ(simplify(straight(10), 0).size(), size_t{10});
    CHECK_EQ(simplify(straight(2), 5).size(), size_t{2});
    CHECK_EQ(simplify({}, 5).size(), size_t{0});
}
