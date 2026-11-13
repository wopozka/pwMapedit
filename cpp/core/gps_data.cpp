#include "gps_data.hpp"

#include <algorithm>
#include <cmath>
#include <utility>

namespace pwm::gps {

size_t File::point_count() const {
    size_t n = waypoints.size();
    for (const Track& t : tracks)
        for (const auto& seg : t.segments) n += seg.size();
    return n;
}

std::vector<size_t> simplify(const std::vector<Point>& points, double tolerance_m) {
    const size_t n = points.size();
    if (n <= 2 || tolerance_m <= 0) {
        std::vector<size_t> all(n);
        for (size_t i = 0; i < n; ++i) all[i] = i;
        return all;
    }
    // lokalny uklad w metrach (rownoodleglosciowy wokol sredniej szerokosci)
    constexpr double DEG = 3.14159265358979323846 / 180.0;
    constexpr double EARTH_R = 6371000.0;
    double lat_sum = 0;
    for (const Point& p : points) lat_sum += p.lat;
    const double kx = std::cos(lat_sum / n * DEG) * EARTH_R * DEG;
    const double ky = EARTH_R * DEG;
    std::vector<std::pair<double, double>> xy(n);
    for (size_t i = 0; i < n; ++i) xy[i] = {points[i].lon * kx, points[i].lat * ky};

    auto distance = [&](size_t i, size_t a, size_t b) {
        const double ax = xy[a].first, ay = xy[a].second;
        const double dx = xy[b].first - ax, dy = xy[b].second - ay;
        const double px = xy[i].first - ax, py = xy[i].second - ay;
        const double len2 = dx * dx + dy * dy;
        if (len2 == 0) return std::hypot(px, py);
        const double t = std::clamp((px * dx + py * dy) / len2, 0.0, 1.0);
        return std::hypot(px - t * dx, py - t * dy);
    };

    std::vector<bool> keep(n, false);
    keep[0] = keep[n - 1] = true;
    std::vector<std::pair<size_t, size_t>> stack{{0, n - 1}};  // iteracyjnie - dlugie slady bez glebokiej rekurencji
    while (!stack.empty()) {
        const auto [a, b] = stack.back();
        stack.pop_back();
        double max_d = -1;
        size_t max_i = a;
        for (size_t i = a + 1; i < b; ++i) {
            const double d = distance(i, a, b);
            if (d > max_d) {
                max_d = d;
                max_i = i;
            }
        }
        if (max_d > tolerance_m) {
            keep[max_i] = true;
            stack.emplace_back(a, max_i);
            stack.emplace_back(max_i, b);
        }
    }
    std::vector<size_t> result;
    for (size_t i = 0; i < n; ++i)
        if (keep[i]) result.push_back(i);
    return result;
}

}  // namespace pwm::gps
