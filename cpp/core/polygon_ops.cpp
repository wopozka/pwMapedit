#include "polygon_ops.hpp"

#include <clipper2/clipper.h>

#include <cmath>

namespace pwm::geom {

namespace {

// 1 jednostka Clipper64 = 1 mm (wspolrzedne sceny sa w ~metrach). Liczby calkowite daja odpornosc na wspolne
// krawedzie i wierzcholki (typowe przy rysowaniu z przyciaganiem).
constexpr double SCALE = 1000.0;

Clipper2Lib::Paths64 to_paths(const std::vector<Ring>& rings) {
    Clipper2Lib::Paths64 paths;
    for (const Ring& ring : rings) {
        if (ring.size() < 3) continue;
        Clipper2Lib::Path64 path;
        path.reserve(ring.size());
        for (const PointF& p : ring)
            path.emplace_back(static_cast<int64_t>(std::llround(p.x * SCALE)), static_cast<int64_t>(std::llround(p.y * SCALE)));
        paths.push_back(std::move(path));
    }
    return paths;
}

Ring to_ring(const Clipper2Lib::Path64& path) {
    Ring ring;
    ring.reserve(path.size());
    for (const auto& p : path) ring.push_back(PointF{p.x / SCALE, p.y / SCALE});
    return ring;
}

double area_m2(const Clipper2Lib::Path64& path) { return std::fabs(Clipper2Lib::Area(path)) / (SCALE * SCALE); }

// Czesc zewnetrzna, potem jej dziury; wyspy w dziurach jako kolejne czesci zewnetrzne.
void collect(const Clipper2Lib::PolyPath64& node, std::vector<Ring>& out, double min_area) {
    for (const auto& child : node) {
        const Clipper2Lib::Path64& outer = child->Polygon();
        if (outer.size() >= 3 && area_m2(outer) >= min_area) {
            out.push_back(to_ring(outer));
            for (const auto& hole : *child) {
                const Clipper2Lib::Path64& h = hole->Polygon();
                if (h.size() >= 3 && area_m2(h) >= min_area) out.push_back(to_ring(h));
            }
        }
        for (const auto& hole : *child) collect(*hole, out, min_area);
    }
}

}  // namespace

SubtractResult subtract(const std::vector<Ring>& a, const std::vector<Ring>& b, double min_area) {
    SubtractResult result;
    const Clipper2Lib::Paths64 pa = to_paths(a), pb = to_paths(b);
    if (pa.empty() || pb.empty()) return result;

    // czy w ogole sie nakladaja (wspolna czesc o niezerowym polu)
    const Clipper2Lib::Paths64 common = Clipper2Lib::Intersect(pa, pb, Clipper2Lib::FillRule::EvenOdd);
    double common_area = 0;
    for (const auto& p : common) common_area += area_m2(p);
    if (common_area < min_area) return result;

    Clipper2Lib::Clipper64 clipper;
    clipper.PreserveCollinear(true);  // wezly na prostych odcinkach zostaja (np. wspolne z sasiednim obiektem)
    clipper.AddSubject(pa);
    clipper.AddClip(pb);
    Clipper2Lib::PolyTree64 tree;
    clipper.Execute(Clipper2Lib::ClipType::Difference, Clipper2Lib::FillRule::EvenOdd, tree);
    collect(tree, result.rings, min_area);
    result.status = result.rings.empty() ? SubtractResult::Status::Empty : SubtractResult::Status::Ok;
    return result;
}

}  // namespace pwm::geom
