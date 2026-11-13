// Odejmowanie polygonow (core/polygon_ops, Clipper2).
#include <cmath>

#include "../core/polygon_ops.hpp"
#include "test_framework.hpp"

using namespace pwm;
using namespace pwm::geom;

namespace {

Ring rect(double x1, double y1, double x2, double y2) { return {{x1, y1}, {x2, y1}, {x2, y2}, {x1, y2}}; }

// pole wedlug zasady parzystosci: zewnetrzne dodatnio, dziury (czesci w innych czesciach) ujemnie
double ring_area(const Ring& r) {
    double a = 0;
    for (size_t i = 0; i < r.size(); ++i) {
        const PointF& p = r[i];
        const PointF& q = r[(i + 1) % r.size()];
        a += p.x * q.y - q.x * p.y;
    }
    return std::fabs(a) / 2;
}

bool contains_point(const Ring& r, const PointF& pt) {
    for (const PointF& p : r)
        if (std::fabs(p.x - pt.x) < 1e-6 && std::fabs(p.y - pt.y) < 1e-6) return true;
    return false;
}

}  // namespace

TEST(subtract_inside_makes_hole) {
    auto r = subtract({rect(0, 0, 100, 100)}, {rect(30, 30, 60, 60)});
    CHECK(r.status == SubtractResult::Status::Ok);
    CHECK_EQ(r.rings.size(), size_t{2});
    CHECK_NEAR(ring_area(r.rings[0]), 10000, 1e-6);  // najpierw czesc zewnetrzna
    CHECK_NEAR(ring_area(r.rings[1]), 900, 1e-6);    // potem dziura
}

TEST(subtract_partial_overlap) {
    auto r = subtract({rect(0, 0, 100, 100)}, {rect(50, -20, 150, 120)});
    CHECK(r.status == SubtractResult::Status::Ok);
    CHECK_EQ(r.rings.size(), size_t{1});
    CHECK_NEAR(ring_area(r.rings[0]), 5000, 1e-6);
}

TEST(subtract_splits_into_two_parts) {
    auto r = subtract({rect(0, 0, 100, 100)}, {rect(40, -10, 60, 110)});
    CHECK(r.status == SubtractResult::Status::Ok);
    CHECK_EQ(r.rings.size(), size_t{2});
    CHECK_NEAR(ring_area(r.rings[0]) + ring_area(r.rings[1]), 8000, 1e-6);
}

TEST(subtract_with_existing_hole) {
    // A ma dziure 20..40; B nachodzi na nia czesciowo - dziury sie lacza (pole sumy 400 + 400 - 100)
    auto r = subtract({rect(0, 0, 100, 100), rect(20, 20, 40, 40)}, {rect(30, 30, 50, 50)});
    CHECK(r.status == SubtractResult::Status::Ok);
    CHECK_EQ(r.rings.size(), size_t{2});
    CHECK_NEAR(ring_area(r.rings[0]) - ring_area(r.rings[1]), 9300, 1e-6);
}

TEST(subtract_shared_edges_and_collinear_nodes) {
    // B przylega do A wspolna krawedzia, ale sie nie naklada
    CHECK(subtract({rect(0, 0, 100, 100)}, {rect(100, 0, 200, 100)}).status == SubtractResult::Status::NoOverlap);
    // B pokrywa prawa polowe A ze wspolnymi krawedziami (jak przy rysowaniu z przyciaganiem)
    auto r = subtract({rect(0, 0, 100, 100)}, {rect(50, 0, 100, 100)});
    CHECK(r.status == SubtractResult::Status::Ok);
    CHECK_EQ(r.rings.size(), size_t{1});
    CHECK_NEAR(ring_area(r.rings[0]), 5000, 1e-6);
    // wezel na prostym odcinku A (np. wspolny z sasiednim obiektem) zostaje
    Ring a{{0, 0}, {25, 0}, {100, 0}, {100, 100}, {0, 100}};
    auto r2 = subtract({a}, {rect(60, 60, 80, 80)});
    CHECK(r2.status == SubtractResult::Status::Ok);
    CHECK(contains_point(r2.rings[0], PointF{25, 0}));
    // wspolrzedne zachowane z dokladnoscia 1 mm
    Ring b{{0.123456, 0}, {100, 0}, {100, 100}, {0, 100}};
    auto r3 = subtract({b}, {rect(60, 60, 80, 80)});
    bool found = false;
    for (const PointF& p : r3.rings[0]) found = found || (std::fabs(p.x - 0.123456) <= 0.0005 && p.y == 0);
    CHECK(found);
}

TEST(subtract_no_overlap_and_full_cover) {
    CHECK(subtract({rect(0, 0, 10, 10)}, {rect(20, 20, 30, 30)}).status == SubtractResult::Status::NoOverlap);
    CHECK(subtract({rect(0, 0, 10, 10)}, {rect(-5, -5, 15, 15)}).status == SubtractResult::Status::Empty);
    CHECK(subtract({}, {rect(0, 0, 1, 1)}).status == SubtractResult::Status::NoOverlap);
}
