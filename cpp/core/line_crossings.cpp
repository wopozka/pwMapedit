#include "line_crossings.hpp"

#include <cmath>
#include <optional>
#include <utility>

namespace pwm {

namespace {

double cross(double ax, double ay, double bx, double by) { return ax * by - ay * bx; }

// Sasiedzi wezla k czesci (dla linii zamknietej, np. ronda, pierwszy i ostatni wezel to ten sam punkt
// w srodku linii). Koniec otwartej linii nie ma sasiada z jednej strony - nullopt.
std::optional<std::pair<PointF, PointF>> neighbours(const LinePart& part, size_t k) {
    const size_t n = part.size();
    const bool closed = n > 3 && part.front().x == part.back().x && part.front().y == part.back().y;
    if (k > 0 && k + 1 < n) return std::make_pair(part[k - 1], part[k + 1]);
    if (closed) return std::make_pair(part[n - 2], part[1]);
    return std::nullopt;
}

// Czy wezel k czesci part przechodzi na druga strone prostej przez odcinek (p, q).
bool passes_through(const LinePart& part, size_t k, const PointF& p, const PointF& q) {
    const auto nb = neighbours(part, k);
    if (!nb) return false;  // koniec linii lezacy na drugiej - styk "T"
    const double sx = q.x - p.x, sy = q.y - p.y;
    const double side1 = cross(sx, sy, nb->first.x - p.x, nb->first.y - p.y);
    const double side2 = cross(sx, sy, nb->second.x - p.x, nb->second.y - p.y);
    return side1 * side2 < 0;
}

}  // namespace

std::vector<PointF> line_crossings(const std::vector<LinePart>& a, const std::vector<LinePart>& b,
                                   double merge_distance) {
    std::vector<PointF> result;
    auto add = [&](const PointF& p) {
        for (const PointF& r : result)
            if (std::hypot(r.x - p.x, r.y - p.y) < merge_distance) return;
        result.push_back(p);
    };
    const double eps = 1e-9;  // tolerancja parametru na odcinku (konce odcinkow)
    for (const LinePart& pa : a) {
        for (size_t i = 0; i + 1 < pa.size(); ++i) {
            const PointF a0 = pa[i], a1 = pa[i + 1];
            const double rx = a1.x - a0.x, ry = a1.y - a0.y;
            const double rlen = std::hypot(rx, ry);
            if (rlen == 0) continue;
            for (const LinePart& pb : b) {
                for (size_t j = 0; j + 1 < pb.size(); ++j) {
                    const PointF b0 = pb[j], b1 = pb[j + 1];
                    const double sx = b1.x - b0.x, sy = b1.y - b0.y;
                    const double slen = std::hypot(sx, sy);
                    if (slen == 0) continue;
                    const double denom = cross(rx, ry, sx, sy);
                    if (std::fabs(denom) <= 1e-12 * rlen * slen) continue;  // rownolegle albo nakladajace sie
                    const double qx = b0.x - a0.x, qy = b0.y - a0.y;
                    const double t = cross(qx, qy, sx, sy) / denom;
                    const double u = cross(qx, qy, rx, ry) / denom;
                    if (t < -eps || t > 1 + eps || u < -eps || u > 1 + eps) continue;
                    const bool t_end = t <= eps || t >= 1 - eps;
                    const bool u_end = u <= eps || u >= 1 - eps;
                    const PointF p{a0.x + t * rx, a0.y + t * ry};
                    if (!t_end && !u_end) {
                        add(p);
                    } else if (t_end && u_end) {
                        continue;  // wezel na wezle: wspolny wezel albo styk koncami
                    } else if (t_end) {
                        // wezel linii a lezy we wnetrzu odcinka linii b
                        if (passes_through(pa, t < 0.5 ? i : i + 1, b0, b1)) add(p);
                    } else {
                        // wezel linii b lezy we wnetrzu odcinka linii a
                        if (passes_through(pb, u < 0.5 ? j : j + 1, a0, a1)) add(p);
                    }
                }
            }
        }
    }
    return result;
}

}  // namespace pwm
