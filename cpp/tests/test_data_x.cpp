// Port tests/test_data_hlevels_numbers.py oraz testy dodatkowe dla DataX.
#include <cmath>
#include <map>

#include "../core/data_x.hpp"
#include "../core/projection.hpp"
#include "test_framework.hpp"

using namespace pwm;

namespace {

MercatorProjection& proj() {
    static MercatorProjection p;
    return p;
}

DataX make(const std::vector<std::string>& data_lines) {
    DataX d(&proj());
    for (const auto& line : data_lines) {
        size_t eq = line.find('=');
        d.add_nodes_from_string(line.substr(0, eq), line.substr(eq + 1));
    }
    return d;
}

const std::string D3 = "(52.42016,20.68638),(52.42011,20.68643),(52.42007,20.68651)";

// Odpowiednik {k: v for k, v in definition._asdict().items() if v is not None}
std::map<std::string, std::string> non_none(const NumbersDefinition* d) {
    std::map<std::string, std::string> m;
    if (!d) return m;
    auto put = [&](const char* k, const auto& v) {
        if (v) m[k] = opt_to_str(v);
    };
    put("left_side_numbering_style", d->left_side_numbering_style);
    put("left_side_number_before", d->left_side_number_before);
    put("left_side_number_after", d->left_side_number_after);
    put("right_side_numbering_style", d->right_side_numbering_style);
    put("right_side_number_before", d->right_side_number_before);
    put("right_side_number_after", d->right_side_number_after);
    put("left_side_zip_code", d->left_side_zip_code);
    put("right_side_zip_code", d->right_side_zip_code);
    put("left_side_city", d->left_side_city);
    put("left_side_region", d->left_side_region);
    put("left_side_country", d->left_side_country);
    put("right_side_city", d->right_side_city);
    put("right_side_region", d->right_side_region);
    put("right_side_country", d->right_side_country);
    return m;
}

std::string show_map(const std::map<std::string, std::string>& m) {
    std::string s = "{";
    for (const auto& [k, v] : m) s += k + ": " + v + ", ";
    return s + "}";
}

}  // namespace

// test_data_levels (pierwsza wersja - w Pythonie przeslonieta przez druga o tej samej nazwie)
TEST(data_levels) {
    CHECK_EQ(make({"Data0=" + D3}).data_levels(), (std::vector<int>{0}));
    CHECK_EQ(make({"Data0=" + D3, "Data1=" + D3}).data_levels(), (std::vector<int>{0, 1}));
    CHECK_EQ(make({"Data0=" + D3, "Data2=" + D3}).data_levels(), (std::vector<int>{0, 2}));
    CHECK_EQ(make({"Data0=" + D3, "Data1=" + D3, "Data2=" + D3}).data_levels(), (std::vector<int>{0, 1, 2}));
    CHECK_EQ(make({"Data0=" + D3, "Data0=" + D3, "Data1=" + D3, "Data1=" + D3, "Data2=" + D3, "Data2=" + D3})
                 .data_levels(),
             (std::vector<int>{0, 1, 2}));
}

TEST(last_data_level_and_last_index) {
    auto a = make({"Data0=" + D3, "Data0=" + D3, "Data1=" + D3, "Data1=" + D3, "Data2=" + D3, "Data2=" + D3,
                   "Data2=" + D3});
    CHECK(a.last_data_level_and_last_index() == std::make_pair(2, size_t{2}));
    auto b = make({"Data0=" + D3, "Data0=" + D3, "Data1=" + D3, "Data1=" + D3, "Data2=" + D3, "Data2=" + D3,
                   "Data4=" + D3});
    CHECK(b.last_data_level_and_last_index() == std::make_pair(4, size_t{0}));
}

TEST(address_adding) {
    DataX d(&proj());
    d.add_nodes_from_string("Data0", "(51.43507,16.10151),(51.43477,16.10183),(51.43465,16.10206)");
    d.add_housenumbers_from_string("Numbers1=0,O,157,157,E,154,154");
    d.add_housenumbers_from_string("Numbers2=1,E,156,156,O,155,155");
    auto defs = d.housenumbers_for_poly(0, 0);
    std::vector<std::map<std::string, std::string>> expected = {
        {{"left_side_numbering_style", "O"},
         {"left_side_number_after", "157"},
         {"right_side_numbering_style", "E"},
         {"right_side_number_after", "154"}},
        {{"left_side_numbering_style", "E"},
         {"left_side_number_before", "157"},
         {"left_side_number_after", "156"},
         {"right_side_numbering_style", "O"},
         {"right_side_number_before", "154"},
         {"right_side_number_after", "155"}},
        {{"left_side_number_before", "156"}, {"right_side_number_before", "155"}},
    };
    CHECK_EQ(defs.size(), expected.size());
    for (size_t i = 0; i < defs.size() && i < expected.size(); ++i) CHECK_EQ(show_map(non_none(defs[i])), show_map(expected[i]));
}

TEST(numbers_between) {
    CHECK_EQ(DataX::numbers_between(1, 9, "O"), (std::vector<long long>{3, 5, 7}));
    CHECK_EQ(DataX::numbers_between(9, 1, "O"), (std::vector<long long>{7, 5, 3}));
    CHECK_EQ(DataX::numbers_between(2, 10, "O"), (std::vector<long long>{3, 5, 7, 9}));
    CHECK_EQ(DataX::numbers_between(2, 10, "E"), (std::vector<long long>{4, 6, 8}));
    CHECK_EQ(DataX::numbers_between(10, 2, "E"), (std::vector<long long>{8, 6, 4}));
    CHECK_EQ(DataX::numbers_between(1, 11, "E"), (std::vector<long long>{2, 4, 6, 8, 10}));
    CHECK_EQ(DataX::numbers_between(11, 1, "B"), (std::vector<long long>{10, 9, 8, 7, 6, 5, 4, 3, 2}));
    // dodatkowe: sasiednie numery i ujemne (modulo jak w Pythonie)
    CHECK_EQ(DataX::numbers_between(5, 6, "B"), (std::vector<long long>{}));
    CHECK_EQ(DataX::numbers_between(-5, 1, "O"), (std::vector<long long>{-3, -1}));
}

namespace {
struct IN {
    LineF v;
    PointF p;
    long long n;
};
void check_interp(std::vector<LineF> vectors, std::vector<long long> numbers, std::vector<IN> expected) {
    auto got = DataX::interpolated_numbers_coordinates(vectors, numbers);
    CHECK_EQ(got.size(), expected.size());
    for (size_t i = 0; i < got.size() && i < expected.size(); ++i) {
        CHECK(got[i].vector == expected[i].v);
        // QPointF == w Qt porownuje z tolerancja (qFuzzyCompare)
        CHECK_NEAR(got[i].position.x, expected[i].p.x, 1e-9);
        CHECK_NEAR(got[i].position.y, expected[i].p.y, 1e-9);
        CHECK_EQ(got[i].number, expected[i].n);
    }
}
}  // namespace

TEST(interpolated_number_coordinates) {
    check_interp({LineF(0, 0, 1, 0)}, {3}, {{LineF(0, 0, 1, 0), {0.5, 0}, 3}});
    check_interp({LineF(0, 0, 0, 3)}, {1, 2}, {{LineF(0, 0, 0, 3), {0, 1}, 1}, {LineF(0, 0, 0, 3), {0, 2}, 2}});
    check_interp({LineF(0, 0, 0, 4)}, {1, 2, 3},
                 {{LineF(0, 0, 0, 4), {0, 1}, 1}, {LineF(0, 0, 0, 4), {0, 2}, 2}, {LineF(0, 0, 0, 4), {0, 3}, 3}});
    check_interp({LineF(0, 0, 0, 1), LineF(0, 1, 0, 3)}, {3}, {{LineF(0, 1, 0, 3), {0, 1.5}, 3}});
    check_interp({LineF(0, 0, 5, 0), LineF(5, 0, 10, 0)}, {1, 2, 3, 4, 5, 6, 7, 8, 9},
                 {{LineF(0, 0, 5, 0), {1, 0}, 1},
                  {LineF(0, 0, 5, 0), {2, 0}, 2},
                  {LineF(0, 0, 5, 0), {3, 0}, 3},
                  {LineF(0, 0, 5, 0), {4, 0}, 4},
                  {LineF(0, 0, 5, 0), {5, 0}, 5},
                  {LineF(5, 0, 10, 0), {6, 0}, 6},
                  {LineF(5, 0, 10, 0), {7, 0}, 7},
                  {LineF(5, 0, 10, 0), {8, 0}, 8},
                  {LineF(5, 0, 10, 0), {9, 0}, 9}});
    check_interp({LineF(0, 0, 4, 0), LineF(4, 0, 5, 0), LineF(5, 0, 6, 0), LineF(6, 0, 9, 0)}, {1, 2},
                 {{LineF(0, 0, 4, 0), {3, 0}, 1}, {LineF(5, 0, 6, 0), {6, 0}, 2}});
    check_interp({LineF(0, 0, 100, 0), LineF(100, 0, 200, 0), LineF(200, 0, 300, 0), LineF(300, 0, 400, 0),
                  LineF(400, 0, 500, 0)},
                 {1, 2, 3, 4},
                 {{LineF(0, 0, 100, 0), {100, 0}, 1},
                  {LineF(100, 0, 200, 0), {200, 0}, 2},
                  {LineF(200, 0, 300, 0), {300, 0}, 3},
                  {LineF(300, 0, 400, 0), {400, 0}, 4}});
    CHECK(DataX::interpolated_numbers_coordinates({LineF(0, 0, 1, 0)}, {}).empty());
}

TEST(invert_poly_addresses) {
    DataX d(&proj());
    d.add_nodes_from_string("Data0", "(52.85431,16.02645),(52.85454,16.02758)");
    d.add_housenumbers_from_string("Numbers1=0,O,1,9,E,2,10");
    d.reverse_poly(0);
    auto defs = d.housenumbers_for_poly(0, 0);
    CHECK_EQ(defs.size(), size_t{2});
    CHECK_EQ(show_map(non_none(defs[0])), show_map({{"left_side_number_after", "10"},
                                                    {"left_side_numbering_style", "E"},
                                                    {"right_side_number_after", "9"},
                                                    {"right_side_numbering_style", "O"}}));
    CHECK_EQ(show_map(non_none(defs[1])),
             show_map({{"left_side_number_before", "2"}, {"right_side_number_before", "1"}}));
}

// ---- testy dodatkowe (brak odpowiednikow w Pythonie) ----

TEST(hlevels_from_string) {
    DataX d = make({"Data0=(51.9248,19.7733),(51.92411,19.77461),(51.92374,19.77508),(51.92305,19.77562)"});
    d.add_hlevels_from_string("HLevel0=(1,0),(2,1),(3,1)");
    CHECK_EQ(d.hlevels_for_poly(0, 0), (std::vector<OptInt>{std::nullopt, 0, 1, 1}));
    CHECK_THROWS(d.add_hlevels_from_string("(7,1)"));  // wezel poza zakresem
}

TEST(numbers_with_zip_codes) {
    DataX d = make({"Data0=(51.0,19.0),(51.001,19.001),(51.002,19.002)"});
    d.add_housenumbers_from_string("Numbers1=0,O,1,9,E,2,10,95-040,-1,-1,-1");
    const NumbersDefinition* n0 = d.housenumbers_for_poly(0, 0)[0];
    CHECK(n0 != nullptr);
    CHECK(n0->left_side_zip_code == std::optional<std::string>("95-040"));
    CHECK(!n0->right_side_zip_code);  // "-1" jest liczba, wiec ignorowane
    CHECK_EQ(d.to_mp_record(5)[1], std::string("Numbers1=0,O,1,9,E,2,10,95-040,-1,-1,-1"));
}

TEST(split_and_calculated_numbers) {
    DataX d = make({"Data0=(51.00000,19.00000),(51.00100,19.00000),(51.00200,19.00000),(51.00300,19.00000)"});
    d.add_housenumbers_from_string("Numbers1=0,B,1,7,N,-1,-1");
    // wezel 1 lezy w srodku odcinka z numerami 1..7 -> numeracja wyliczana z interpolacji
    auto calc = d.calculated_housenumber_defs_for_node(0, 0, 1);
    CHECK(calc.has_value());
    auto parts = d.split_data_x(0, 0, 1);
    CHECK_EQ(parts.size(), size_t{2});
    CHECK_EQ(parts[0].raw_polys()[0][0].size(), size_t{2});
    CHECK_EQ(parts[1].raw_polys()[0][0].size(), size_t{3});
    CHECK(d.split_data_x(0, 0, 0).empty());  // nie mozna dzielic na pierwszym wezle
    CHECK(d.split_data_x(0, 0, 3).empty());  // ani na ostatnim
}

TEST(insert_delete_update_nodes) {
    DataX d = make({"Data0=(51.0,19.0),(51.1,19.1)"});
    d.insert_node_at_position(0, 0, -1, 10, 20);
    d.insert_node_at_position(0, 0, 0, 1, 2);
    d.insert_node_at_position(0, 0, 1, 3, 4);
    const Poly& p = d.raw_polys()[0][0];
    CHECK_EQ(p.size(), size_t{5});
    CHECK(p[0].pos() == (PointF{1, 2}));
    CHECK(p[1].pos() == (PointF{3, 4}));
    CHECK(p[4].pos() == (PointF{10, 20}));
    d.update_node_coordinates(0, 0, -1, {7, 8});
    CHECK(d.raw_polys()[0][0][4].pos() == (PointF{7, 8}));
    d.delete_node_at_position(0, 0, 0);
    CHECK_EQ(d.raw_polys()[0][0].size(), size_t{4});
    d.delete_poly_at_data_level(0, 0);
    CHECK(d.data_levels().empty());
}

TEST(copy_is_deep) {
    DataX d = make({"Data0=(51.0,19.0),(51.1,19.1)"});
    d.add_housenumbers_from_string("Numbers1=0,O,1,3,N,-1,-1");
    DataX c = d;
    c.reverse_poly(0);
    CHECK(d.housenumbers_for_poly(0, 0)[0]->left_side_numbering_style == std::optional<std::string>("O"));
    CHECK(c.housenumbers_for_poly(0, 0)[0]->right_side_numbering_style == std::optional<std::string>("O"));
}

TEST(non_sequential_data_levels) {
    // W Pythonie Numbers po Data1 bez Data0 konczylo sie IndexError (indeksowanie numerem poziomu).
    DataX d = make({"Data1=(51.0,19.0),(51.1,19.1)"});
    d.add_housenumbers_from_string("Numbers1=0,O,1,3,N,-1,-1");
    CHECK(d.housenumbers_for_poly(1, 0)[0] != nullptr);
    CHECK_EQ(d.to_mp_record(1).size(), size_t{2});
}

TEST(bad_input_throws) {
    DataX d(&proj());
    CHECK_THROWS(d.add_nodes_from_string("Data0", "(51.0;19.0)"));
    CHECK_THROWS(d.add_nodes_from_string("Data0", "(51.0,abc)"));
    CHECK_THROWS(d.add_nodes_from_string("DataX", "(51.0,19.0)"));
    CHECK_THROWS(d.add_housenumbers_from_string("Numbers1=0,O,1,3"));  // brak Data
}

TEST(translate_data_level_moves_only_that_level) {
    DataX d = make({"Data0=(51.0,19.0),(51.1,19.1)", "Data1=(52.0,20.0),(52.1,20.1)"});
    d.add_hlevels_from_string("0,1");
    std::vector<std::vector<Poly>> before = d.raw_polys();
    d.translate_data_level(0, PointF{10.0, -5.0});
    for (size_t i = 0; i < 2; ++i) {
        CHECK_EQ(d.raw_polys()[0][0][i].x(), before[0][0][i].x() + 10.0);
        CHECK_EQ(d.raw_polys()[0][0][i].y(), before[0][0][i].y() - 5.0);
        CHECK(d.raw_polys()[1][0][i].pos() == before[1][0][i].pos());
    }
    CHECK(d.raw_polys()[1][0][0].hlevel() == OptInt(1));  // HLevel trafia do ostatniego poziomu
    CHECK_THROWS(d.translate_data_level(3, PointF{1.0, 1.0}));
}
