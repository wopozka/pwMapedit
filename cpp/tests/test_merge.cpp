// Port tests/test_merge_polylines.py: laczenie polilinii (DataX::merge_polylines).
#include <cmath>
#include <string>
#include <utility>

#include "../core/data_x.hpp"
#include "../core/projection.hpp"
#include "test_framework.hpp"

using namespace pwm;

namespace {

MercatorProjection& proj() {
    static MercatorProjection p;
    return p;
}

const std::string A = "Data0=(52.00000,20.00000),(52.00100,20.00100),(52.00200,20.00200)";
const std::string B = "Data0=(52.00200,20.00200),(52.00300,20.00300)";
const std::string B_REV = "Data0=(52.00300,20.00300),(52.00200,20.00200)";
const std::string BEFORE_A = "Data0=(51.99900,19.99900),(52.00000,20.00000)";
const std::string C = "Data0=(52.00300,20.00300),(52.00400,20.00400),(52.00500,20.00500)";
const std::string FAR = "Data0=(53.00000,21.00000),(53.00100,21.00100)";

std::string level1(const std::string& line) { return "Data1" + line.substr(5); }

DataX data_obj(const std::vector<std::string>& lines) {
    DataX d(&proj());
    for (const auto& line : lines) {
        if (line.rfind("Numbers", 0) == 0) {
            d.add_housenumbers_from_string(line);
        } else if (line.rfind("HLevel", 0) == 0) {
            d.add_hlevels_from_string(line);
        } else {
            size_t eq = line.find('=');
            d.add_nodes_from_string(line.substr(0, eq), line.substr(eq + 1));
        }
    }
    return d;
}

double r5(double v) { return std::round(v * 1e5) / 1e5; }

std::vector<std::pair<double, double>> coords(const DataX& d, int level = 0) {
    std::vector<std::pair<double, double>> out;
    for (const Node& n : d.polys_for_data_level(level)->front()) {
        GeoPoint g = proj().canvas_to_geo(n.x(), n.y());
        out.emplace_back(r5(g.latitude), r5(g.longitude));
    }
    return out;
}

using P = std::pair<double, double>;

MergeResult merge(std::vector<DataX> objs) {
    std::vector<const DataX*> ptrs;
    for (const DataX& d : objs) ptrs.push_back(&d);
    return DataX::merge_polylines(ptrs);
}

}  // namespace

std::ostream& operator<<(std::ostream& os, const P& p) { return os << "(" << p.first << ", " << p.second << ")"; }

TEST(merge_end_to_start) {
    MergeResult m = merge({data_obj({A}), data_obj({B})});
    CHECK(coords(m.data) == (std::vector<P>{{52.0, 20.0}, {52.001, 20.001}, {52.002, 20.002}, {52.003, 20.003}}));
    CHECK(m.skipped_levels.empty());
    CHECK(!m.reversed_any);
}

TEST(merge_end_to_end_reverses_second) {
    MergeResult m = merge({data_obj({A}), data_obj({B_REV})});
    CHECK(coords(m.data).back() == P(52.003, 20.003));
    CHECK_EQ(coords(m.data).size(), size_t{4});
    CHECK(m.reversed_any);
}

TEST(merge_prepend_keeps_first_direction) {
    MergeResult m = merge({data_obj({A}), data_obj({BEFORE_A})});
    CHECK(coords(m.data) == (std::vector<P>{{51.999, 19.999}, {52.0, 20.0}, {52.001, 20.001}, {52.002, 20.002}}));
    CHECK(!m.reversed_any);
}

TEST(merge_three_lines_any_order) {
    // C dotyka dopiero B, wiec przy pierwszym przejsciu musi poczekac
    MergeResult m = merge({data_obj({A}), data_obj({C}), data_obj({B})});
    CHECK(coords(m.data).front() == P(52.0, 20.0));
    CHECK(coords(m.data).back() == P(52.005, 20.005));
    CHECK_EQ(coords(m.data).size(), size_t{6});
}

TEST(merge_not_touching_throws) { CHECK_THROWS(merge({data_obj({A}), data_obj({FAR})})); }

TEST(merge_multipart_throws) { CHECK_THROWS(merge({data_obj({A, FAR}), data_obj({B})})); }

TEST(merge_single_line_throws) { CHECK_THROWS(merge({data_obj({A})})); }

TEST(merge_level_missing_in_one_line_is_skipped) {
    MergeResult m = merge({data_obj({A, level1(A)}), data_obj({B})});
    CHECK(m.data.data_levels() == std::vector<int>{0});
    CHECK(m.skipped_levels == std::vector<int>{1});
}

TEST(merge_higher_level_not_touching_is_skipped) {
    MergeResult m = merge({data_obj({A, level1(A)}), data_obj({B, level1(FAR)})});
    CHECK(m.data.data_levels() == std::vector<int>{0});
    CHECK(m.skipped_levels == std::vector<int>{1});
}

TEST(merge_source_objects_not_modified) {
    DataX a = data_obj({A}), b = data_obj({B_REV});
    DataX::merge_polylines({&a, &b});
    CHECK_EQ(a.polys_for_data_level(0)->front().size(), size_t{3});
    CHECK(coords(b) == (std::vector<P>{{52.003, 20.003}, {52.002, 20.002}}));
}

TEST(merge_numbers_and_hlevel_at_joint) {
    DataX a = data_obj({A, "Numbers1=0,O,1,5,E,2,6"});
    DataX b = data_obj({B, "Numbers1=0,O,7,9,E,8,10", "HLevel0=(0,1)"});
    MergeResult m = DataX::merge_polylines({&a, &b});
    const Node& joint = m.data.polys_for_data_level(0)->front()[2];
    const NumbersDefinition* numbers = joint.numbers();
    CHECK(numbers != nullptr);
    // koniec przedzialu z pierwszej linii, poczatek przedzialu z drugiej
    CHECK(numbers->left_side_number_before == OptInt(5) && numbers->right_side_number_before == OptInt(6));
    CHECK(numbers->left_side_number_after == OptInt(7) && numbers->right_side_number_after == OptInt(8));
    CHECK(joint.hlevel() == OptInt(1));
    std::vector<std::string> record = m.data.to_mp_record(5);
    CHECK((std::vector<std::string>(record.begin() + 1, record.end()) ==
           std::vector<std::string>{"Numbers1=0,O,1,5,E,2,6", "Numbers2=2,O,7,9,E,8,10", "HLevel0=(2,1)"}));
}

TEST(merge_bounding_box_covers_all) {
    MergeResult m = merge({data_obj({A}), data_obj({B})});
    const GeoBBox& bbox = m.data.obj_bounding_box();
    CHECK(r5(bbox.S) == 52.0 && r5(bbox.N) == 52.003);
    CHECK(r5(bbox.W) == 20.0 && r5(bbox.E) == 20.003);
}

TEST(merge_after_split_has_bounding_box) {
    // druga czesc z podzialu linii ma DataX bez obwiedni
    std::vector<DataX> parts = data_obj({A}).split_data_x(0, 0, 1);
    CHECK(!parts[1].obj_bounding_box().valid);
    DataX b = data_obj({B});
    MergeResult m = DataX::merge_polylines({&parts[1], &b});
    CHECK(r5(m.data.obj_bounding_box().S) == 52.001 && r5(m.data.obj_bounding_box().N) == 52.003);
}
