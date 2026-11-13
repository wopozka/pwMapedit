// Port klas Node, Numbers_Definition i Data_X z map_items.py.
//
// Roznice wzgledem Pythona (celowe, opisane w cpp/README.md):
//  * Data_X.precision bylo zmienna klasowa (globalna dla procesu). Tu precyzje przechowuje MapData
//    i przekazuje jawnie do to_mp_record().
//  * Czesc metod w Pythonie indeksowala _poly_data_points numerem poziomu (Data1 -> [1]) zamiast
//    indeksem z _data_levels. Dziala to tylko, gdy poziomy ida po kolei od Data0; w innym wypadku
//    Python rzucal IndexError albo modyfikowal zly poziom. Tu zawsze uzywamy poprawnego indeksu.
//  * Tam, gdzie Python rzucal wyjatek (np. bledny numer wezla), rzucamy MpError.
#pragma once

#include <memory>
#include <optional>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

#include "geometry.hpp"

namespace pwm {

class Projection;

struct MpError : std::runtime_error {
    using std::runtime_error::runtime_error;
};

// Linii nie da sie polaczyc (MergeError z Pythona); komunikat jest dla uzytkownika (UTF-8).
struct MergeError : std::runtime_error {
    using std::runtime_error::runtime_error;
};

// Tolerancja (we wspolrzednych sceny), w ktorej konce linii uznajemy za ten sam wezel (SAME_NODE_TOLERANCE).
constexpr double SAME_NODE_TOLERANCE = 1e-3;

using OptStr = std::optional<std::string>;
using OptInt = std::optional<long long>;

// Numbers_Definition: numeracja adresowa przypisana do wezla.
// "before" - numer konczacy odcinek przed wezlem, "after" - numer zaczynajacy odcinek za wezlem.
struct NumbersDefinition {
    OptStr left_side_numbering_style;
    OptInt left_side_number_before;
    OptInt left_side_number_after;
    OptStr right_side_numbering_style;
    OptInt right_side_number_before;
    OptInt right_side_number_after;
    OptStr left_side_zip_code;
    OptStr right_side_zip_code;
    OptStr left_side_city;
    OptStr left_side_region;
    OptStr left_side_country;
    OptStr right_side_city;
    OptStr right_side_region;
    OptStr right_side_country;

    bool operator==(const NumbersDefinition& o) const;
    bool operator!=(const NumbersDefinition& o) const { return !(*this == o); }
    // Zamiana stron i kierunku (left<->right, before<->after) po odwroceniu linii.
    NumbersDefinition reversed() const;
    // Ustawia na None wszystkie pola poza *_number_before (ostatni wezel linii).
    void clear_all_but_before();
    // Reprezentacja tekstowa do porownan z Pythonem: pola rozdzielone '|', None jako "None".
    std::string dump() const;
};

class Node {
public:
    Node() = default;
    Node(double x, double y) : pos_{x, y} {}
    Node(const Node& o);
    Node& operator=(const Node& o);
    Node(Node&&) noexcept = default;
    Node& operator=(Node&&) noexcept = default;

    double x() const { return pos_.x; }
    double y() const { return pos_.y; }
    PointF pos() const { return pos_; }
    void set_pos(PointF p) { pos_ = p; }

    // numeracja
    const NumbersDefinition* numbers() const { return numbers_.get(); }
    NumbersDefinition& numbers_or_create();  // jak set_numbers_definition_field_name: tworzy pusta definicje
    void set_numbers(const NumbersDefinition* def);
    void set_numbers(std::optional<NumbersDefinition> def);
    void clear_numbers() { numbers_.reset(); }
    bool starts_numeration() const;
    bool ends_numeration() const;
    bool has_numeration() const;
    void update_numbers_after_poly_reversing();

    // hlevel
    const OptInt& hlevel() const { return hlevel_; }
    void set_hlevel(OptInt v) { hlevel_ = v; }
    bool has_hlevel() const { return hlevel_.has_value(); }

    // "(lat,lon)" w formacie pliku mp
    void append_mp_coords(std::string& out, const Projection& proj, int precision) const;
    std::string mp_coords(const Projection& proj, int precision) const;

private:
    PointF pos_;
    std::unique_ptr<NumbersDefinition> numbers_;
    OptInt hlevel_;
};

using Poly = std::vector<Node>;

struct InterpolatedNumber {
    LineF vector;
    PointF position;
    long long number;
    bool operator==(const InterpolatedNumber& o) const {
        return vector == o.vector && position == o.position && number == o.number;
    }
};

struct InterpolatedNumbers {
    std::vector<InterpolatedNumber> left;
    std::vector<InterpolatedNumber> right;
};

struct MergeResult;

class DataX {
public:
    explicit DataX(const Projection* projection = nullptr) : projection_(projection) {}

    const Projection* projection() const { return projection_; }
    void set_projection(const Projection* p) { projection_ = p; }

    // ---- wczytywanie z pliku ----
    // data_level_key: "Data0".."Data4"; zwraca precyzje wspolrzednych (liczbe cyfr po kropce
    // pierwszej wspolrzednej) albo -1, jesli nie powinna wplywac na globalna precyzje (> 6).
    int add_nodes_from_string(std::string_view data_level_key, std::string_view data_string);
    void add_housenumbers_from_string(std::string_view num_string);
    void add_hlevels_from_string(std::string_view hlevels_definition);

    // ---- odczyt ----
    const std::vector<int>& data_levels() const { return levels_; }
    std::optional<size_t> data_level_index(int data_level) const;
    const std::vector<Poly>* polys_for_data_level(int data_level) const;
    std::vector<Poly>* polys_for_data_level(int data_level);
    const Node* poly_node(int data_level, size_t poly_num, long node_num) const;
    Node* poly_node(int data_level, size_t poly_num, long node_num);
    std::pair<int, size_t> last_data_level_and_last_index() const { return {last_data_level_, last_poly_index_}; }
    const GeoBBox& obj_bounding_box() const { return bbox_; }
    double perimeter() const { return perimeter_; }
    std::vector<const NumbersDefinition*> housenumbers_for_poly(int data_level, size_t poly_num) const;
    std::vector<OptInt> hlevels_for_poly(int data_level, size_t poly_num) const;
    std::vector<size_t> nodes_indexes_with_housenumbers(int data_level, size_t poly_num) const;
    std::vector<LineF> poly_vectors(int data_level, size_t poly_num, size_t start_node_idx, size_t end_node_idx) const;

    // ---- numeracja ----
    static std::vector<long long> numbers_between(long long start_point, long long end_point, std::string_view style);
    static std::vector<InterpolatedNumber> interpolated_numbers_coordinates(std::vector<LineF> poly_vectors,
                                                                            std::vector<long long> numbers);
    InterpolatedNumbers interpolated_housenumbers_for_poly(int data_level, size_t poly_num) const;
    InterpolatedNumbers interpolated_housenumbers_for_poly_section(int data_level, size_t poly_num,
                                                                   size_t start_node_idx, size_t end_node_idx) const;
    std::pair<long long, long long> housenumber_for_node_from_interpolated_numbers(int data_level, size_t poly_num,
                                                                                   size_t start_node_idx,
                                                                                   size_t end_node_idx,
                                                                                   size_t node_idx,
                                                                                   bool left_side) const;
    std::optional<NumbersDefinition> calculated_housenumber_defs_for_node(int data_level, size_t poly_num,
                                                                          size_t node_num) const;
    void clean_numbers_definitions(int data_level, size_t poly_num);

    // ---- edycja ----
    void set_hlevel_to_node(int data_level, size_t poly_num, long node_num, OptInt level_val);
    void insert_node_at_position(int data_level, size_t poly_num, long index, double x, double y);
    void delete_node_at_position(int data_level, size_t poly_num, long index);
    void delete_poly_at_data_level(int data_level, size_t poly_num);
    void update_node_coordinates(int data_level, size_t poly_num, long index, PointF position);
    bool set_poly_from_node_list(int data_level, size_t poly_num, Poly poly);
    void reverse_poly(int data_level);
    // Przesuwa wszystkie wezly poziomu o wektor (we wspolrzednych sceny) - odpowiednik petli
    // update_node_coordinates w SelectModeMoveItem/SelectModeMovePoi. Rzuca MpError, gdy poziomu nie ma.
    void translate_data_level(int data_level, PointF delta);
    bool is_splitting_possible(int data_level, size_t poly_num, long node_num) const;
    // Zwraca {czesc1, czesc2} albo pusty wektor, gdy podzial niemozliwy.
    std::vector<DataX> split_data_x(int data_level, size_t poly_num, long node_num) const;
    // Port Data_X.merge_polylines: skleja linie (po jednej czesci na poziomie) w jedna. Kierunek i kolejnosc
    // wyznacza pierwsza linia, pozostale sa w razie potrzeby odwracane. Rzuca MergeError.
    static MergeResult merge_polylines(const std::vector<const DataX*>& data_objs);
    // Obwiednia liczona od nowa z wezlow (recalculate_bounding_box).
    void recalculate_bounding_box();

    // ---- zapis ----
    std::vector<std::string> to_mp_record(int precision) const;
    std::string numbers_to_mp(size_t start_node_num, const Node& start_node, const Node& end_node) const;

    // Dostep do surowych danych (np. dla GUI): polys_[indeks_poziomu][numer_poly][numer_wezla]
    const std::vector<std::vector<Poly>>& raw_polys() const { return polys_; }

private:
    Poly single_line_copy(int data_level, bool reverse) const;
    static Node join_nodes(const Node& node_end, const Node& node_start, bool hlevel_from_start);
    static std::pair<Poly, bool> chain_lines(const std::vector<const DataX*>& data_objs, int data_level);
    size_t level_index_or_throw(int data_level) const;
    Poly& poly_ref(int data_level, size_t poly_num);
    const Poly& poly_ref(int data_level, size_t poly_num) const;
    void set_obj_bounding_box(double latitude, double longitude);
    static double calculate_poly_perimeter(const Poly& coords);
    void add_housenumbers_to_nodes(int data_level, size_t poly_num, std::string_view definition);
    void clean_numbers_definition_first_and_last_nodes(Poly& poly);
    void clean_numbers_definitions_only_one_node_case(Poly& poly, size_t node_with_numbers_idx);
    void clean_numbers_definitions_multiple_nodes_case(Poly& poly);

    const Projection* projection_ = nullptr;
    std::vector<int> levels_;               // _data_levels: kolejnosc pojawiania sie poziomow
    std::vector<std::vector<Poly>> polys_;  // _poly_data_points
    GeoBBox bbox_;
    int last_data_level_ = 0;
    size_t last_poly_index_ = 0;
    double perimeter_ = 0.0;
};

struct MergeResult {
    DataX data;
    std::vector<int> skipped_levels;  // poziomy pominiete (nie ma ich kazda linia albo nie tworza lancucha)
    bool reversed_any = false;        // czy na najnizszym wspolnym poziomie ktoras linie trzeba bylo odwrocic
};

bool same_node_position(const Node& a, const Node& b);

// Indeksowanie jak w Pythonie: ujemne indeksy licza od konca. Rzuca MpError, gdy poza zakresem.
size_t py_index(long idx, size_t size);

std::string opt_to_str(const OptInt& v);
std::string opt_to_str(const OptStr& v);

}  // namespace pwm
