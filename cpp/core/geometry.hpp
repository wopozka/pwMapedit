// Minimalne odpowiedniki QPointF/QLineF, zeby rdzen nie zalezal od Qt.
// Wzory sa identyczne z Qt6 (QLineF::length() == hypot z libm, pointAt jak w Qt).
#pragma once

#include <cmath>

namespace pwm {

struct PointF {
    double x = 0.0;
    double y = 0.0;
    bool operator==(const PointF& o) const { return x == o.x && y == o.y; }
    bool operator!=(const PointF& o) const { return !(*this == o); }
};

struct LineF {
    PointF p1;
    PointF p2;
    LineF() = default;
    LineF(PointF a, PointF b) : p1(a), p2(b) {}
    LineF(double x1, double y1, double x2, double y2) : p1{x1, y1}, p2{x2, y2} {}
    double dx() const { return p2.x - p1.x; }
    double dy() const { return p2.y - p1.y; }
    double length() const { return std::hypot(dx(), dy()); }
    PointF pointAt(double t) const { return {p1.x + (p2.x - p1.x) * t, p1.y + (p2.y - p1.y) * t}; }
    bool operator==(const LineF& o) const { return p1 == o.p1 && p2 == o.p2; }
};

// Prostokat ograniczajacy we wspolrzednych geograficznych (jak slownik {'N','S','W','E'} w Pythonie).
struct GeoBBox {
    bool valid = false;
    double S = 0.0, N = 0.0, W = 0.0, E = 0.0;

    void extend(const GeoBBox& o) {
        if (!o.valid) return;
        if (!valid) {
            *this = o;
            return;
        }
        if (o.E > E) E = o.E;
        if (o.W < W) W = o.W;
        if (o.N > N) N = o.N;
        if (o.S < S) S = o.S;
    }
};

struct GeoPoint {
    double latitude = 0.0;
    double longitude = 0.0;
};

}  // namespace pwm
