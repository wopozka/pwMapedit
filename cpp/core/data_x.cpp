#include "data_x.hpp"

#include <algorithm>
#include <cmath>

#include "projection.hpp"
#include "pyutil.hpp"

namespace pwm {

// ------------------------------------------------------------------ pomocnicze

size_t py_index(long idx, size_t size) {
    long s = static_cast<long>(size);
    long i = idx < 0 ? idx + s : idx;
    if (i < 0 || i >= s) throw MpError("IndexError: indeks wezla/poly poza zakresem");
    return static_cast<size_t>(i);
}

std::string opt_to_str(const OptInt& v) { return v ? std::to_string(*v) : std::string("None"); }
std::string opt_to_str(const OptStr& v) { return v ? *v : std::string("None"); }

static void require(bool cond, const char* msg) {
    if (!cond) throw MpError(msg);
}

// ------------------------------------------------------------------ NumbersDefinition

bool NumbersDefinition::operator==(const NumbersDefinition& o) const {
    return left_side_numbering_style == o.left_side_numbering_style &&
           left_side_number_before == o.left_side_number_before &&
           left_side_number_after == o.left_side_number_after &&
           right_side_numbering_style == o.right_side_numbering_style &&
           right_side_number_before == o.right_side_number_before &&
           right_side_number_after == o.right_side_number_after && left_side_zip_code == o.left_side_zip_code &&
           right_side_zip_code == o.right_side_zip_code && left_side_city == o.left_side_city &&
           left_side_region == o.left_side_region && left_side_country == o.left_side_country &&
           right_side_city == o.right_side_city && right_side_region == o.right_side_region &&
           right_side_country == o.right_side_country;
}

NumbersDefinition NumbersDefinition::reversed() const {
    NumbersDefinition r;
    r.left_side_numbering_style = right_side_numbering_style;
    r.right_side_numbering_style = left_side_numbering_style;
    r.left_side_number_before = right_side_number_after;
    r.left_side_number_after = right_side_number_before;
    r.right_side_number_before = left_side_number_after;
    r.right_side_number_after = left_side_number_before;
    r.left_side_zip_code = right_side_zip_code;
    r.right_side_zip_code = left_side_zip_code;
    r.left_side_city = right_side_city;
    r.right_side_city = left_side_city;
    r.left_side_region = right_side_region;
    r.right_side_region = left_side_region;
    r.left_side_country = right_side_country;
    r.right_side_country = left_side_country;
    return r;
}

void NumbersDefinition::clear_all_but_before() {
    left_side_numbering_style.reset();
    left_side_number_after.reset();
    right_side_numbering_style.reset();
    right_side_number_after.reset();
    left_side_zip_code.reset();
    right_side_zip_code.reset();
    left_side_city.reset();
    left_side_region.reset();
    left_side_country.reset();
    right_side_city.reset();
    right_side_region.reset();
    right_side_country.reset();
}

std::string NumbersDefinition::dump() const {
    std::string s = opt_to_str(left_side_numbering_style);
    s += '|' + opt_to_str(left_side_number_before);
    s += '|' + opt_to_str(left_side_number_after);
    s += '|' + opt_to_str(right_side_numbering_style);
    s += '|' + opt_to_str(right_side_number_before);
    s += '|' + opt_to_str(right_side_number_after);
    s += '|' + opt_to_str(left_side_zip_code);
    s += '|' + opt_to_str(right_side_zip_code);
    s += '|' + opt_to_str(left_side_city);
    s += '|' + opt_to_str(left_side_region);
    s += '|' + opt_to_str(left_side_country);
    s += '|' + opt_to_str(right_side_city);
    s += '|' + opt_to_str(right_side_region);
    s += '|' + opt_to_str(right_side_country);
    return s;
}

// ------------------------------------------------------------------ Node

Node::Node(const Node& o)
    : pos_(o.pos_), numbers_(o.numbers_ ? std::make_unique<NumbersDefinition>(*o.numbers_) : nullptr), hlevel_(o.hlevel_) {}

Node& Node::operator=(const Node& o) {
    if (this != &o) {
        pos_ = o.pos_;
        numbers_ = o.numbers_ ? std::make_unique<NumbersDefinition>(*o.numbers_) : nullptr;
        hlevel_ = o.hlevel_;
    }
    return *this;
}

NumbersDefinition& Node::numbers_or_create() {
    if (!numbers_) numbers_ = std::make_unique<NumbersDefinition>();
    return *numbers_;
}

void Node::set_numbers(const NumbersDefinition* def) {
    numbers_ = def ? std::make_unique<NumbersDefinition>(*def) : nullptr;
}

void Node::set_numbers(std::optional<NumbersDefinition> def) {
    numbers_ = def ? std::make_unique<NumbersDefinition>(std::move(*def)) : nullptr;
}

bool Node::starts_numeration() const {
    return numbers_ && (numbers_->left_side_number_after || numbers_->right_side_number_after);
}

bool Node::ends_numeration() const {
    return numbers_ && (numbers_->left_side_number_before || numbers_->right_side_number_before);
}

bool Node::has_numeration() const { return numbers_ && (starts_numeration() || ends_numeration()); }

void Node::update_numbers_after_poly_reversing() {
    if (!numbers_) return;
    *numbers_ = numbers_->reversed();
}

void Node::append_mp_coords(std::string& out, const Projection& proj, int precision) const {
    GeoPoint g = proj.canvas_to_geo(pos_.x, pos_.y);
    out += '(';
    py::append_fixed(out, g.latitude, precision);
    out += ',';
    py::append_fixed(out, g.longitude, precision);
    out += ')';
}

std::string Node::mp_coords(const Projection& proj, int precision) const {
    std::string s;
    append_mp_coords(s, proj, precision);
    return s;
}

// ------------------------------------------------------------------ DataX: wczytywanie

int DataX::add_nodes_from_string(std::string_view data_level_key, std::string_view data_string) {
    auto lvl = py::to_int(data_level_key.substr(std::min<size_t>(4, data_level_key.size())));
    require(lvl.has_value(), "ValueError: niepoprawny numer poziomu Data");
    require(projection_ != nullptr, "Brak projekcji dla DataX");
    int level = static_cast<int>(*lvl);

    // coords_from_data_to_nodes
    std::string_view coordlist = py::rstrip(py::lstrip(py::strip(data_string), '('), ')');
    Poly poly;
    int precision = 0;
    size_t pos = 0;
    while (true) {
        size_t f = coordlist.find("),(", pos);
        std::string_view a = coordlist.substr(pos, f == std::string_view::npos ? std::string_view::npos : f - pos);
        size_t comma = a.find(',');
        require(comma != std::string_view::npos && a.find(',', comma + 1) == std::string_view::npos,
                "ValueError: wspolrzedna musi miec postac (lat,lon)");
        std::string_view lat_s = a.substr(0, comma);
        std::string_view lon_s = a.substr(comma + 1);
        if (precision == 0) {
            auto decimals = [](std::string_view s) -> int {
                size_t d = s.find('.');
                return d == std::string_view::npos ? 0 : static_cast<int>(s.size() - d - 1);
            };
            precision = std::max(decimals(lat_s), decimals(lon_s));
        }
        auto lat = py::to_float(lat_s);
        auto lon = py::to_float(lon_s);
        require(lat && lon, "ValueError: niepoprawna wspolrzedna");
        set_obj_bounding_box(*lat, *lon);
        PointF p = projection_->geo_to_canvas(*lat, *lon);
        poly.emplace_back(p.x, p.y);
        if (f == std::string_view::npos) break;
        pos = f + 3;
    }

    auto idx = data_level_index(level);
    if (!idx) {
        levels_.push_back(level);
        polys_.emplace_back();
        idx = levels_.size() - 1;
    }
    perimeter_ = std::max(perimeter_, calculate_poly_perimeter(poly));
    polys_[*idx].push_back(std::move(poly));
    last_data_level_ = level;
    last_poly_index_ = polys_[*idx].size() - 1;
    return precision <= 6 ? precision : -1;
}

void DataX::add_housenumbers_from_string(std::string_view num_string) {
    auto [level, poly_num] = last_data_level_and_last_index();
    size_t eq = num_string.find('=');
    std::string_view definition = eq == std::string_view::npos ? num_string : num_string.substr(eq + 1);
    add_housenumbers_to_nodes(level, poly_num, definition);
}

void DataX::add_housenumbers_to_nodes(int data_level, size_t poly_num, std::string_view definition) {
    auto num_data = py::split(definition, ",");
    require(num_data.size() >= 7, "IndexError: za malo pol w definicji Numbers");
    auto node_num = py::to_int(num_data[0]);
    require(node_num.has_value(), "ValueError: numer wezla w Numbers");
    std::string left_style(num_data[1]);
    std::string right_style(num_data[4]);
    OptInt left_start, left_end, right_start, right_end;
    if (left_style != "N") {
        left_start = py::to_int(num_data[2]);
        left_end = py::to_int(num_data[3]);
        require(left_start && left_end, "ValueError: numer domu w Numbers");
    }
    if (right_style != "N") {
        right_start = py::to_int(num_data[5]);
        right_end = py::to_int(num_data[6]);
        require(right_start && right_end, "ValueError: numer domu w Numbers");
    }
    // Kod pocztowy: jesli pole daje sie sparsowac jako liczba (np. -1), jest ignorowane - tak jak w Pythonie.
    OptStr left_zip, right_zip;
    if (num_data.size() > 7 && !py::to_int(num_data[7])) left_zip = std::string(num_data[7]);
    if (num_data.size() > 8 && !py::to_int(num_data[8])) right_zip = std::string(num_data[8]);

    Poly& poly = poly_ref(data_level, poly_num);
    require(!poly.empty(), "IndexError: pusta linia");
    Node& node = poly[py_index(static_cast<long>(*node_num), poly.size())];
    node.numbers_or_create().left_side_numbering_style = left_style;
    node.numbers_or_create().left_side_number_after = left_start;
    node.numbers_or_create().right_side_numbering_style = right_style;
    node.numbers_or_create().right_side_number_after = right_start;
    if (left_zip || right_zip) {
        node.numbers_or_create().left_side_zip_code = left_zip;
        node.numbers_or_create().right_side_zip_code = right_zip;
    }
    Node& last = poly.back();
    std::optional<NumbersDefinition> last_node_def;
    if (last.numbers()) last_node_def = *last.numbers();
    if (last_node_def) {
        node.numbers_or_create().left_side_number_before = last_node_def->left_side_number_before;
        node.numbers_or_create().right_side_number_before = last_node_def->right_side_number_before;
        last.clear_numbers();
    }
    if (left_start || right_start) {
        last.numbers_or_create().left_side_number_before = left_end;
        last.numbers_or_create().right_side_number_before = right_end;
    }
}

void DataX::add_hlevels_from_string(std::string_view hlevels_definition) {
    if (py::starts_with(hlevels_definition, "HLevel")) {
        size_t eq = hlevels_definition.find('=');
        require(eq != std::string_view::npos, "IndexError: HLevel bez '='");
        hlevels_definition = hlevels_definition.substr(eq + 1);
    }
    std::string_view body = py::rstrip(py::lstrip(hlevels_definition, '('), ')');
    for (std::string_view hlevel_def : py::split(body, "),(")) {
        auto parts = py::split(hlevel_def, ",");
        require(parts.size() == 2, "ValueError: HLevel musi miec postac (wezel,poziom)");
        auto node_num = py::to_int(parts[0]);
        auto level_val = py::to_int(parts[1]);
        require(node_num && level_val, "ValueError: HLevel");
        set_hlevel_to_node(last_data_level_, last_poly_index_, static_cast<long>(*node_num), *level_val);
    }
}

double DataX::calculate_poly_perimeter(const Poly& coords) {
    double perimeter = 0.0;
    for (size_t i = 1; i < coords.size(); ++i) perimeter += LineF(coords[i - 1].pos(), coords[i].pos()).length();
    return perimeter;
}

void DataX::set_obj_bounding_box(double latitude, double longitude) {
    if (!bbox_.valid) {
        bbox_.valid = true;
        bbox_.S = bbox_.N = latitude;
        bbox_.E = bbox_.W = longitude;
        return;
    }
    if (latitude <= bbox_.S)
        bbox_.S = latitude;
    else if (latitude >= bbox_.N)
        bbox_.N = latitude;
    if (longitude <= bbox_.W)
        bbox_.W = longitude;
    else if (longitude >= bbox_.E)
        bbox_.E = longitude;
}

// ------------------------------------------------------------------ DataX: odczyt

std::optional<size_t> DataX::data_level_index(int data_level) const {
    for (size_t i = 0; i < levels_.size(); ++i)
        if (levels_[i] == data_level) return i;
    return std::nullopt;
}

size_t DataX::level_index_or_throw(int data_level) const {
    auto idx = data_level_index(data_level);
    require(idx.has_value(), "IndexError: brak poziomu Data");
    return *idx;
}

Poly& DataX::poly_ref(int data_level, size_t poly_num) {
    auto& polys = polys_[level_index_or_throw(data_level)];
    require(poly_num < polys.size(), "IndexError: numer poly poza zakresem");
    return polys[poly_num];
}

const Poly& DataX::poly_ref(int data_level, size_t poly_num) const {
    const auto& polys = polys_[level_index_or_throw(data_level)];
    require(poly_num < polys.size(), "IndexError: numer poly poza zakresem");
    return polys[poly_num];
}

const std::vector<Poly>* DataX::polys_for_data_level(int data_level) const {
    auto idx = data_level_index(data_level);
    return idx ? &polys_[*idx] : nullptr;
}

std::vector<Poly>* DataX::polys_for_data_level(int data_level) {
    auto idx = data_level_index(data_level);
    return idx ? &polys_[*idx] : nullptr;
}

const Node* DataX::poly_node(int data_level, size_t poly_num, long node_num) const {
    if (!data_level_index(data_level)) return nullptr;
    const Poly& poly = poly_ref(data_level, poly_num);
    return &poly[py_index(node_num, poly.size())];
}

Node* DataX::poly_node(int data_level, size_t poly_num, long node_num) {
    if (!data_level_index(data_level)) return nullptr;
    Poly& poly = poly_ref(data_level, poly_num);
    return &poly[py_index(node_num, poly.size())];
}

std::vector<const NumbersDefinition*> DataX::housenumbers_for_poly(int data_level, size_t poly_num) const {
    std::vector<const NumbersDefinition*> out;
    for (const Node& n : poly_ref(data_level, poly_num)) out.push_back(n.numbers());
    return out;
}

std::vector<OptInt> DataX::hlevels_for_poly(int data_level, size_t poly_num) const {
    std::vector<OptInt> out;
    for (const Node& n : poly_ref(data_level, poly_num)) out.push_back(n.hlevel());
    return out;
}

std::vector<size_t> DataX::nodes_indexes_with_housenumbers(int data_level, size_t poly_num) const {
    std::vector<size_t> out;
    const Poly& poly = poly_ref(data_level, poly_num);
    for (size_t i = 0; i < poly.size(); ++i)
        if (poly[i].has_numeration()) out.push_back(i);
    return out;
}

std::vector<LineF> DataX::poly_vectors(int data_level, size_t poly_num, size_t start_node_idx,
                                       size_t end_node_idx) const {
    const Poly& poly = poly_ref(data_level, poly_num);
    std::vector<LineF> out;
    for (size_t i = start_node_idx; i < end_node_idx; ++i) {
        require(i + 1 < poly.size(), "IndexError: wektor poza linia");
        out.emplace_back(poly[i].pos(), poly[i + 1].pos());
    }
    return out;
}

// ------------------------------------------------------------------ DataX: numeracja

std::vector<long long> DataX::numbers_between(long long start_point, long long end_point, std::string_view style) {
    long long diff = start_point - end_point;
    if (diff == -1 || diff == 0 || diff == 1) return {};
    long long step;
    if (start_point > end_point) {
        step = -1;
        start_point -= 1;
    } else {
        step = 1;
        start_point += 1;
    }
    std::vector<long long> numbers;
    for (long long a = start_point; step > 0 ? a < end_point : a > end_point; a += step) {
        long long mod2 = ((a % 2) + 2) % 2;  // modulo jak w Pythonie
        if (style == "E") {
            if (mod2 == 0) numbers.push_back(a);
        } else if (style == "O") {
            if (mod2 == 1) numbers.push_back(a);
        } else {
            numbers.push_back(a);
        }
    }
    return numbers;
}

std::vector<InterpolatedNumber> DataX::interpolated_numbers_coordinates(std::vector<LineF> poly_vectors,
                                                                        std::vector<long long> numbers) {
    // W Pythonie funkcja rekurencyjna; tu iteracyjnie, z ta sama kolejnoscia operacji zmiennoprzecinkowych.
    std::vector<InterpolatedNumber> out;
    if (numbers.empty()) return out;
    std::vector<double> lengths;
    lengths.reserve(poly_vectors.size());
    for (const auto& v : poly_vectors) lengths.push_back(v.length());
    double all_polys_length = py::sum(lengths);
    double default_num_distance = all_polys_length / static_cast<double>(numbers.size() + 1);
    double current_num_distance = default_num_distance;
    size_t vi = 0, ni = 0;
    while (ni < numbers.size()) {
        require(vi < poly_vectors.size(), "IndexError: zabraklo odcinkow przy interpolacji numerow");
        const LineF& vec = poly_vectors[vi];
        double poly_length = vec.length();
        if (poly_length > current_num_distance) {
            PointF position = vec.pointAt(current_num_distance / poly_length);
            long long num = numbers[ni++];
            LineF vector;
            if (current_num_distance + default_num_distance <= poly_length) {
                current_num_distance += default_num_distance;
                vector = vec;
            } else {
                current_num_distance = default_num_distance - (poly_length - current_num_distance);
                vector = vec;
                ++vi;
            }
            out.push_back({vector, position, num});
        } else if (poly_length == current_num_distance) {
            PointF position = vec.p2;
            LineF vector = vec;
            ++vi;
            long long num = numbers[ni++];
            current_num_distance = default_num_distance;
            out.push_back({vector, position, num});
        } else {
            current_num_distance = current_num_distance - poly_length;
            ++vi;
        }
    }
    return out;
}

InterpolatedNumbers DataX::interpolated_housenumbers_for_poly(int data_level, size_t poly_num) const {
    InterpolatedNumbers result;
    auto idx = nodes_indexes_with_housenumbers(data_level, poly_num);
    for (size_t i = 1; i < idx.size(); ++i) {
        auto part = interpolated_housenumbers_for_poly_section(data_level, poly_num, idx[i - 1], idx[i]);
        result.left.insert(result.left.end(), part.left.begin(), part.left.end());
        result.right.insert(result.right.end(), part.right.begin(), part.right.end());
    }
    return result;
}

InterpolatedNumbers DataX::interpolated_housenumbers_for_poly_section(int data_level, size_t poly_num,
                                                                     size_t start_node_idx,
                                                                     size_t end_node_idx) const {
    InterpolatedNumbers result;
    const Node* node_with_num = poly_node(data_level, poly_num, static_cast<long>(start_node_idx));
    const Node* node_with_num_plus = poly_node(data_level, poly_num, static_cast<long>(end_node_idx));
    require(node_with_num && node_with_num_plus, "AttributeError: brak wezla");
    auto vectors = poly_vectors(data_level, poly_num, start_node_idx, end_node_idx);
    require(node_with_num->numbers() != nullptr, "AttributeError: wezel bez numeracji");
    const NumbersDefinition& s = *node_with_num->numbers();

    auto side = [&](const OptStr& style, const OptInt& start, bool left) -> std::vector<InterpolatedNumber> {
        if (!style || *style == "N") return {};
        require(node_with_num_plus->numbers() != nullptr, "AttributeError: wezel bez numeracji");
        const NumbersDefinition& e = *node_with_num_plus->numbers();
        const OptInt& end = left ? e.left_side_number_before : e.right_side_number_before;
        require(start && end, "TypeError: brak numeru przy interpolacji");
        return interpolated_numbers_coordinates(vectors, numbers_between(*start, *end, *style));
    };
    result.left = side(s.left_side_numbering_style, s.left_side_number_after, true);
    result.right = side(s.right_side_numbering_style, s.right_side_number_after, false);
    return result;
}

std::pair<long long, long long> DataX::housenumber_for_node_from_interpolated_numbers(
    int data_level, size_t poly_num, size_t start_node_idx, size_t end_node_idx, size_t node_idx,
    bool left_side) const {
    auto lengths = [](const std::vector<LineF>& v) {
        std::vector<double> l;
        for (const auto& x : v) l.push_back(x.length());
        return py::sum(l);
    };
    double segment_length = lengths(poly_vectors(data_level, poly_num, start_node_idx, end_node_idx));
    double segment_to_node_length = lengths(poly_vectors(data_level, poly_num, start_node_idx, node_idx));
    const NumbersDefinition* s = poly_node(data_level, poly_num, static_cast<long>(start_node_idx))->numbers();
    const NumbersDefinition* e = poly_node(data_level, poly_num, static_cast<long>(end_node_idx))->numbers();
    require(s && e, "AttributeError: wezel bez numeracji");
    const OptInt& start = left_side ? s->left_side_number_after : s->right_side_number_after;
    const OptInt& end = left_side ? e->left_side_number_before : e->right_side_number_before;
    const OptStr& style = left_side ? s->left_side_numbering_style : s->right_side_numbering_style;
    require(start && end, "TypeError: brak numeru przy interpolacji");
    std::vector<long long> numbers{*start};
    for (long long n : numbers_between(*start, *end, style ? std::string_view(*style) : std::string_view("None")))
        numbers.push_back(n);
    numbers.push_back(*end);
    double distance = segment_length / static_cast<double>(numbers.size() - 1);
    require(distance != 0.0, "ZeroDivisionError: odcinek o zerowej dlugosci");
    double q = py::floordiv(segment_to_node_length, distance);
    long long before_idx = static_cast<long long>(q);
    long long after_idx = static_cast<long long>(q + 1);
    require(before_idx >= 0 && after_idx >= 0 && static_cast<size_t>(before_idx) < numbers.size() &&
                static_cast<size_t>(after_idx) < numbers.size(),
            "IndexError: numer poza lista interpolowanych numerow");
    return {numbers[before_idx], numbers[after_idx]};
}

std::optional<NumbersDefinition> DataX::calculated_housenumber_defs_for_node(int data_level, size_t poly_num,
                                                                             size_t node_num) const {
    auto idx = nodes_indexes_with_housenumbers(data_level, poly_num);
    for (size_t i = 1; i < idx.size(); ++i) {
        size_t start_node_idx = idx[i - 1], end_node_idx = idx[i];
        if (!(start_node_idx < node_num && node_num < end_node_idx)) continue;
        const Node& start_node = *poly_node(data_level, poly_num, static_cast<long>(start_node_idx));
        const Node& end_node = *poly_node(data_level, poly_num, static_cast<long>(end_node_idx));
        const NumbersDefinition& sd = *start_node.numbers();
        const NumbersDefinition& ed = *end_node.numbers();
        NumbersDefinition d;
        auto inter = interpolated_housenumbers_for_poly_section(data_level, poly_num, start_node_idx, end_node_idx);
        auto copy_left = [&] {
            d.left_side_numbering_style = sd.left_side_numbering_style;
            d.left_side_zip_code = sd.left_side_zip_code;
            d.left_side_city = sd.left_side_city;
            d.left_side_region = sd.left_side_region;
            d.left_side_country = sd.left_side_country;
        };
        auto copy_right = [&] {
            d.right_side_numbering_style = sd.right_side_numbering_style;
            d.right_side_zip_code = sd.right_side_zip_code;
            d.right_side_city = sd.right_side_city;
            d.right_side_region = sd.right_side_region;
            d.right_side_country = sd.right_side_country;
        };
        if (!inter.left.empty()) {
            copy_left();
            auto [b, a] = housenumber_for_node_from_interpolated_numbers(data_level, poly_num, start_node_idx,
                                                                         end_node_idx, node_num, true);
            d.left_side_number_before = b;
            d.left_side_number_after = a;
        } else if (start_node.has_numeration() && start_node.starts_numeration()) {
            copy_left();
            d.left_side_number_after = ed.left_side_number_before;
            d.left_side_number_before = sd.left_side_number_after;
        }
        if (!inter.right.empty()) {
            copy_right();
            auto [b, a] = housenumber_for_node_from_interpolated_numbers(data_level, poly_num, start_node_idx,
                                                                         end_node_idx, node_num, false);
            d.right_side_number_before = b;
            d.right_side_number_after = a;
        } else if (start_node.has_numeration() && start_node.starts_numeration()) {
            copy_right();
            d.right_side_number_after = ed.right_side_number_before;
            d.right_side_number_before = sd.right_side_number_after;
        }
        return d;
    }
    return std::nullopt;
}

void DataX::clean_numbers_definitions(int data_level, size_t poly_num) {
    Poly& poly = poly_ref(data_level, poly_num);
    std::vector<size_t> with_numbers;
    for (size_t i = 0; i < poly.size(); ++i)
        if (poly[i].has_numeration()) with_numbers.push_back(i);
    if (with_numbers.empty()) return;
    clean_numbers_definition_first_and_last_nodes(poly);
    if (with_numbers.size() == 1) {
        clean_numbers_definitions_only_one_node_case(poly, with_numbers[0]);
        return;
    }
    clean_numbers_definitions_multiple_nodes_case(poly);
}

void DataX::clean_numbers_definition_first_and_last_nodes(Poly& poly) {
    // pierwszy wezel: "przed" nie ma sensu
    if (poly.front().has_numeration()) {
        poly.front().numbers_or_create().left_side_number_before.reset();
        poly.front().numbers_or_create().right_side_number_before.reset();
    }
    // ostatni wezel: "po" nie ma sensu
    Node& last = poly.back();
    if (last.has_numeration()) last.numbers_or_create().clear_all_but_before();
}

void DataX::clean_numbers_definitions_only_one_node_case(Poly& poly, size_t node_with_numbers_idx) {
    Node& last = poly.back();
    const Node& first_num = poly[node_with_numbers_idx];
    require(first_num.numbers() != nullptr, "AttributeError: wezel bez numeracji");
    if (!first_num.numbers()->left_side_number_after) {
        last.numbers_or_create().left_side_number_before.reset();
    } else if (!last.has_numeration() || !last.numbers()->left_side_number_before) {
        last.numbers_or_create().left_side_number_before = 0;
    }
    // first_num moze byc tym samym wezlem co last - odczytujemy po modyfikacji, jak w Pythonie
    if (!poly[node_with_numbers_idx].numbers()->right_side_number_after) {
        last.numbers_or_create().right_side_number_before.reset();
    } else if (!last.has_numeration() || !last.numbers()->right_side_number_before) {
        last.numbers_or_create().right_side_number_before = 0;
    }
}

void DataX::clean_numbers_definitions_multiple_nodes_case(Poly& poly) {
    Node& last = poly.back();
    if (!last.has_numeration()) {
        last.numbers_or_create().left_side_number_before = 0;
        last.numbers_or_create().right_side_number_before = 0;
    }
    std::vector<size_t> with_numbers;
    for (size_t i = 0; i < poly.size(); ++i)
        if (poly[i].has_numeration()) with_numbers.push_back(i);
    for (size_t k = 0; k + 1 < with_numbers.size(); ++k) {
        Node& node_start = poly[with_numbers[k]];
        Node& node_end = poly[with_numbers[k + 1]];
        if (node_start.starts_numeration()) {
            const NumbersDefinition& s = *node_start.numbers();
            NumbersDefinition& e = node_end.numbers_or_create();
            if (!s.left_side_number_after)
                e.left_side_number_before.reset();
            else if (!e.left_side_number_before)
                e.left_side_number_before = 0;
            if (!s.right_side_number_after)
                e.right_side_number_before.reset();
            else if (!e.right_side_number_before)
                e.right_side_number_before = 0;
        } else {
            // wezel startowy nie zaczyna numeracji: "przed" na koncowym jest juz niepotrzebne
            if (node_end.has_numeration() && node_end.starts_numeration()) {
                node_end.numbers_or_create().left_side_number_before.reset();
                node_end.numbers_or_create().right_side_number_before.reset();
            } else {
                node_end.clear_numbers();
            }
        }
    }
}

// ------------------------------------------------------------------ DataX: edycja

void DataX::set_hlevel_to_node(int data_level, size_t poly_num, long node_num, OptInt level_val) {
    if (!data_level_index(data_level)) return;
    Poly& poly = poly_ref(data_level, poly_num);
    poly[py_index(node_num, poly.size())].set_hlevel(level_val);
}

void DataX::insert_node_at_position(int data_level, size_t poly_num, long index, double x, double y) {
    Poly& poly = poly_ref(data_level, poly_num);
    long s = static_cast<long>(poly.size());
    long pos;
    if (index == -1) {
        pos = s;  // na koniec
    } else if (index < 0) {
        pos = std::max(0L, s + index);  // polygon[:index] + [new] + polygon[index:]
    } else {
        pos = std::min(index, s);
    }
    poly.insert(poly.begin() + pos, Node(x, y));
}

void DataX::delete_node_at_position(int data_level, size_t poly_num, long index) {
    Poly& poly = poly_ref(data_level, poly_num);
    poly.erase(poly.begin() + static_cast<long>(py_index(index, poly.size())));
    if (!poly.empty()) clean_numbers_definitions(data_level, poly_num);
}

// ------------------------------------------------------------------ DataX: czesci i poziomy (karta Elements)

void DataX::recalculate_perimeter() {
    perimeter_ = 0.0;
    for (const auto& polys : polys_)
        for (const Poly& poly : polys) perimeter_ = std::max(perimeter_, calculate_poly_perimeter(poly));
}

size_t DataX::sorted_insert_index(int data_level) const {
    size_t i = 0;
    while (i < levels_.size() && levels_[i] < data_level) ++i;
    return i;
}

int DataX::max_data_level() const {
    int m = -1;
    for (int level : levels_) m = std::max(m, level);
    return m;
}

void DataX::delete_polys(int data_level, std::vector<size_t> poly_nums) {
    auto idx = data_level_index(data_level);
    if (!idx) return;
    std::sort(poly_nums.begin(), poly_nums.end());
    poly_nums.erase(std::unique(poly_nums.begin(), poly_nums.end()), poly_nums.end());
    auto& polys = polys_[*idx];
    for (auto it = poly_nums.rbegin(); it != poly_nums.rend(); ++it)
        if (*it < polys.size()) polys.erase(polys.begin() + static_cast<long>(*it));
    if (polys.empty()) {
        levels_.erase(levels_.begin() + static_cast<long>(*idx));
        polys_.erase(polys_.begin() + static_cast<long>(*idx));
    }
    recalculate_bounding_box();
    recalculate_perimeter();
}

DataX DataX::extract_polys(int data_level, const std::vector<size_t>& poly_nums) const {
    DataX result(projection_);
    auto idx = data_level_index(data_level);
    if (!idx) return result;
    std::vector<size_t> nums = poly_nums;
    std::sort(nums.begin(), nums.end());
    nums.erase(std::unique(nums.begin(), nums.end()), nums.end());
    std::vector<Poly> polys;
    for (size_t n : nums)
        if (n < polys_[*idx].size()) polys.push_back(polys_[*idx][n]);  // kopia z numeracja i HLevel wezlow
    if (polys.empty()) return result;
    result.levels_.push_back(data_level);
    result.polys_.push_back(std::move(polys));
    result.last_data_level_ = data_level;
    result.recalculate_bounding_box();
    result.recalculate_perimeter();
    return result;
}

bool DataX::copy_data_level(int from_level, int to_level) {
    auto from = data_level_index(from_level);
    if (!from || from_level == to_level || data_level_index(to_level)) return false;
    std::vector<Poly> copy = polys_[*from];
    const size_t at = sorted_insert_index(to_level);
    levels_.insert(levels_.begin() + static_cast<long>(at), to_level);
    polys_.insert(polys_.begin() + static_cast<long>(at), std::move(copy));
    return true;
}

bool DataX::move_data_level(int from_level, int to_level) {
    auto from = data_level_index(from_level);
    if (!from || from_level == to_level || data_level_index(to_level)) return false;
    std::vector<Poly> moved = std::move(polys_[*from]);
    levels_.erase(levels_.begin() + static_cast<long>(*from));
    polys_.erase(polys_.begin() + static_cast<long>(*from));
    const size_t at = sorted_insert_index(to_level);
    levels_.insert(levels_.begin() + static_cast<long>(at), to_level);
    polys_.insert(polys_.begin() + static_cast<long>(at), std::move(moved));
    if (last_data_level_ == from_level) last_data_level_ = to_level;
    return true;
}

void DataX::delete_poly_at_data_level(int data_level, size_t poly_num) {
    auto idx = data_level_index(data_level);
    if (!idx || poly_num >= polys_[*idx].size()) return;
    polys_[*idx].erase(polys_[*idx].begin() + static_cast<long>(poly_num));
    if (polys_[*idx].empty()) {
        levels_.erase(levels_.begin() + static_cast<long>(*idx));
        polys_.erase(polys_.begin() + static_cast<long>(*idx));
    }
}

void DataX::update_node_coordinates(int data_level, size_t poly_num, long index, PointF position) {
    Poly& poly = poly_ref(data_level, poly_num);
    poly[py_index(index, poly.size())].set_pos(position);
}

bool DataX::set_poly_from_node_list(int data_level, size_t poly_num, Poly poly) {
    auto* polys = polys_for_data_level(data_level);
    if (polys && !polys->empty() && polys->size() > poly_num) {
        (*polys)[poly_num] = std::move(poly);
        return true;
    }
    return false;
}

void DataX::reverse_poly(int data_level) {
    auto* polys = polys_for_data_level(data_level);
    require(polys != nullptr, "TypeError: brak poziomu Data do odwrocenia");
    for (size_t poly_num = 0; poly_num < polys->size(); ++poly_num) {
        Poly& poly = (*polys)[poly_num];
        std::reverse(poly.begin(), poly.end());
        std::vector<Node*> with_numbers;
        for (Node& n : poly)
            if (n.has_numeration()) with_numbers.push_back(&n);
        for (Node* n : with_numbers) n->update_numbers_after_poly_reversing();
        // styl numeracji opisuje odcinek ZA wezlem, wiec po odwroceniu przesuwamy go o jeden wezel
        with_numbers.clear();
        for (Node& n : poly)
            if (n.has_numeration()) with_numbers.push_back(&n);
        for (size_t k = 0; k + 1 < with_numbers.size(); ++k) {
            OptStr left_style = with_numbers[k + 1]->numbers()->left_side_numbering_style;
            OptStr right_style = with_numbers[k + 1]->numbers()->right_side_numbering_style;
            with_numbers[k]->numbers_or_create().left_side_numbering_style = left_style;
            with_numbers[k]->numbers_or_create().right_side_numbering_style = right_style;
        }
        clean_numbers_definitions(data_level, poly_num);
    }
}

bool same_node_position(const Node& a, const Node& b) {
    return std::abs(a.x() - b.x()) <= SAME_NODE_TOLERANCE && std::abs(a.y() - b.y()) <= SAME_NODE_TOLERANCE;
}

Poly DataX::single_line_copy(int data_level, bool reverse) const {
    // kopia (ewentualnie odwrocona) jedynej linii z danego poziomu, z numeracja i hlevel
    DataX tmp(projection_);
    tmp.levels_.push_back(data_level);
    tmp.polys_.push_back({poly_ref(data_level, 0)});
    if (reverse) tmp.reverse_poly(data_level);
    return std::move(tmp.polys_[0][0]);
}

Node DataX::join_nodes(const Node& node_end, const Node& node_start, bool hlevel_from_start) {
    // Wezel styku: konczy przedzial numeracji linii poprzedniej (*_number_before) i zaczyna przedzial nastepnej.
    Node joint = node_start;
    if (const NumbersDefinition* end_def = node_end.numbers()) {
        if (end_def->left_side_number_before)
            joint.numbers_or_create().left_side_number_before = end_def->left_side_number_before;
        if (end_def->right_side_number_before)
            joint.numbers_or_create().right_side_number_before = end_def->right_side_number_before;
    }
    if (hlevel_from_start)
        joint.set_hlevel(node_start.has_hlevel() ? node_start.hlevel() : node_end.hlevel());
    else
        joint.set_hlevel(node_end.has_hlevel() ? node_end.hlevel() : node_start.hlevel());
    return joint;
}

std::pair<Poly, bool> DataX::chain_lines(const std::vector<const DataX*>& data_objs, int data_level) {
    Poly chain = data_objs[0]->single_line_copy(data_level, false);
    std::vector<const DataX*> remaining(data_objs.begin() + 1, data_objs.end());
    bool reversed_any = false;
    while (!remaining.empty()) {
        bool joined = false;
        for (size_t idx = 0; idx < remaining.size(); ++idx) {
            const Poly& line = remaining[idx]->poly_ref(data_level, 0);
            bool reverse;
            if (same_node_position(chain.back(), line.front()) || same_node_position(chain.back(), line.back())) {
                reverse = !same_node_position(chain.back(), line.front());
                Poly add = remaining[idx]->single_line_copy(data_level, reverse);
                Node joint = join_nodes(chain.back(), add.front(), false);
                chain.back() = std::move(joint);
                chain.insert(chain.end(), std::make_move_iterator(add.begin() + 1), std::make_move_iterator(add.end()));
            } else if (same_node_position(chain.front(), line.back()) ||
                       same_node_position(chain.front(), line.front())) {
                reverse = !same_node_position(chain.front(), line.back());
                Poly add = remaining[idx]->single_line_copy(data_level, reverse);
                add.back() = join_nodes(add.back(), chain.front(), true);
                add.insert(add.end(), std::make_move_iterator(chain.begin() + 1), std::make_move_iterator(chain.end()));
                chain = std::move(add);
            } else {
                continue;
            }
            reversed_any = reversed_any || reverse;
            remaining.erase(remaining.begin() + static_cast<long>(idx));
            joined = true;
            break;
        }
        if (!joined)
            throw MergeError("Linie na poziomie Data" + std::to_string(data_level) +
                             " nie tworzą ciągłego łańcucha - każda kolejna linia musi zaczynać się albo kończyć "
                             "na końcu poprzednich.");
    }
    return {std::move(chain), reversed_any};
}

MergeResult DataX::merge_polylines(const std::vector<const DataX*>& data_objs) {
    if (data_objs.size() < 2) throw MergeError("Do połączenia potrzebne są co najmniej dwie linie.");
    const DataX& first = *data_objs[0];
    std::vector<int> all_levels;
    for (const DataX* d : data_objs)
        for (int level : d->levels_)
            if (std::find(all_levels.begin(), all_levels.end(), level) == all_levels.end()) all_levels.push_back(level);
    std::vector<int> common_levels = first.levels_;
    std::sort(common_levels.begin(), common_levels.end());
    common_levels.erase(std::remove_if(common_levels.begin(), common_levels.end(),
                                       [&](int level) {
                                           for (const DataX* d : data_objs)
                                               if (!d->data_level_index(level)) return true;
                                           return false;
                                       }),
                        common_levels.end());
    if (common_levels.empty()) throw MergeError("Linie nie mają wspólnego poziomu Data, nie da się ich połączyć.");
    for (const DataX* d : data_objs)
        for (int level : common_levels)
            if (d->polys_for_data_level(level)->size() != 1)
                throw MergeError("Jedna z linii ma kilka części na poziomie Data" + std::to_string(level) +
                                 ". Łączenie linii wieloczęściowych nie jest obsługiwane.");

    MergeResult result{DataX(first.projection_), {}, false};
    DataX& merged = result.data;
    for (int level : all_levels)
        if (std::find(common_levels.begin(), common_levels.end(), level) == common_levels.end())
            result.skipped_levels.push_back(level);
    for (int level : common_levels) {
        std::pair<Poly, bool> chained;
        try {
            chained = chain_lines(data_objs, level);
        } catch (const MergeError&) {
            // najnizszy wspolny poziom musi sie dac skleic, wyzsze (uproszczone) w razie problemow pomijamy
            if (level == common_levels.front()) throw;
            result.skipped_levels.push_back(level);
            continue;
        }
        if (level == common_levels.front()) result.reversed_any = chained.second;
        merged.levels_.push_back(level);
        merged.perimeter_ = std::max(merged.perimeter_, calculate_poly_perimeter(chained.first));
        merged.polys_.push_back({std::move(chained.first)});
        merged.clean_numbers_definitions(level, 0);
    }
    // obwiednie zrodel moga byc nieustawione (czesc z podzialu linii) albo nieaktualne (po przesunieciu wezlow)
    merged.recalculate_bounding_box();
    std::sort(result.skipped_levels.begin(), result.skipped_levels.end());
    return result;
}

void DataX::recalculate_bounding_box() {
    bbox_ = GeoBBox{};
    if (!projection_) return;
    for (const auto& polys : polys_)
        for (const Poly& poly : polys)
            for (const Node& n : poly) {
                GeoPoint g = projection_->canvas_to_geo(n.x(), n.y());
                set_obj_bounding_box(g.latitude, g.longitude);
            }
}

void DataX::translate_data_level(int data_level, PointF delta) {
    auto* polys = polys_for_data_level(data_level);
    require(polys != nullptr, "brak poziomu Data do przesuniecia");
    for (Poly& poly : *polys)
        for (Node& n : poly) n.set_pos(PointF{n.x() + delta.x, n.y() + delta.y});
}

bool DataX::is_splitting_possible(int data_level, size_t poly_num, long node_num) const {
    auto idx = data_level_index(data_level);
    if (!idx) return false;
    if (poly_num >= polys_[*idx].size()) return false;
    return 1 <= node_num && node_num < static_cast<long>(polys_[*idx][poly_num].size()) - 1;
}

std::vector<DataX> DataX::split_data_x(int data_level, size_t poly_num, long node_num) const {
    if (!is_splitting_possible(data_level, poly_num, node_num)) return {};
    const Node* split_node = poly_node(data_level, poly_num, node_num);
    std::optional<NumbersDefinition> node_num_def;
    if (split_node->has_numeration())
        node_num_def = *split_node->numbers();
    else
        node_num_def = calculated_housenumber_defs_for_node(data_level, poly_num, static_cast<size_t>(node_num));

    const Poly& poly = poly_ref(data_level, poly_num);
    Poly first, second;
    for (long n = 0; n < static_cast<long>(poly.size()); ++n) {
        if (n < node_num) {
            first.push_back(poly[n]);
        } else if (n == node_num) {
            first.push_back(poly[n]);
            second.push_back(poly[n]);
        } else {
            second.push_back(poly[n]);
        }
    }
    first.back().set_numbers(node_num_def);
    second.front().set_numbers(node_num_def);

    DataX poly1 = *this;
    poly1.set_poly_from_node_list(data_level, poly_num, std::move(first));
    poly1.clean_numbers_definitions(data_level, poly_num);

    DataX poly2(projection_);
    poly2.levels_.push_back(data_level);
    poly2.polys_.push_back({std::move(second)});
    // W Pythonie: poly2.clean_numbers_definitions(data_level, poly_num) - przy poly_num > 0 albo
    // poziomie innym niz Data0 konczylo sie IndexError. Druga czesc ma zawsze jedna linie o indeksie 0.
    poly2.clean_numbers_definitions(data_level, 0);
    std::vector<DataX> out;
    out.push_back(std::move(poly1));
    out.push_back(std::move(poly2));
    return out;
}

// ------------------------------------------------------------------ DataX: zapis

std::vector<std::string> DataX::to_mp_record(int precision) const {
    require(projection_ != nullptr, "Brak projekcji dla DataX");
    std::vector<std::string> poly_points;
    for (size_t li = 0; li < levels_.size(); ++li) {
        int data_level = levels_[li];
        const auto& polys = polys_[li];
        for (size_t poly_num = 0; poly_num < polys.size(); ++poly_num) {
            const Poly& poly = polys[poly_num];
            std::string line = "Data" + std::to_string(data_level) + "=";
            line.reserve(line.size() + poly.size() * (2 * precision + 10));
            for (size_t i = 0; i < poly.size(); ++i) {
                if (i) line += ',';
                poly[i].append_mp_coords(line, *projection_, precision);
            }
            poly_points.push_back(std::move(line));

            std::vector<size_t> nodes_with_nums, nodes_with_hlevel;
            for (size_t i = 0; i < poly.size(); ++i) {
                if (poly[i].has_numeration()) nodes_with_nums.push_back(i);
                if (poly[i].has_hlevel()) nodes_with_hlevel.push_back(i);
            }
            if (nodes_with_nums.size() >= 2) {
                int number_num = 1;
                for (size_t k = 0; k + 1 < nodes_with_nums.size(); ++k) {
                    poly_points.push_back("Numbers" + std::to_string(number_num) + "=" +
                                          numbers_to_mp(nodes_with_nums[k], poly[nodes_with_nums[k]],
                                                        poly[nodes_with_nums[k + 1]]));
                    ++number_num;
                }
                // ostatni numerowany wezel nie jest ostatnim wezlem - zaznacz, gdzie konczy sie numeracja
                size_t last_idx = nodes_with_nums.back();
                if (last_idx < poly.size() - 1 && !poly[last_idx].starts_numeration()) {
                    poly_points.push_back("Numbers" + std::to_string(number_num) + "=" + std::to_string(last_idx) +
                                          ",N,-1,-1,N,-1,-1");
                }
            }
            if (!nodes_with_hlevel.empty()) {
                std::string h = "HLevel" + std::to_string(poly_num) + "=";
                for (size_t k = 0; k < nodes_with_hlevel.size(); ++k) {
                    if (k) h += ',';
                    h += "(" + std::to_string(nodes_with_hlevel[k]) + "," +
                         opt_to_str(poly[nodes_with_hlevel[k]].hlevel()) + ")";
                }
                poly_points.push_back(std::move(h));
            }
        }
    }
    return poly_points;
}

std::string DataX::numbers_to_mp(size_t start_node_num, const Node& start_node, const Node& end_node) const {
    const NumbersDefinition& s = *start_node.numbers();
    const NumbersDefinition& e = *end_node.numbers();
    std::string out = std::to_string(start_node_num);
    if (s.left_side_numbering_style && *s.left_side_numbering_style != "N") {
        out += "," + *s.left_side_numbering_style + "," + opt_to_str(s.left_side_number_after) + "," +
               opt_to_str(e.left_side_number_before);
    } else {
        out += ",N,-1,-1";
    }
    if (s.right_side_numbering_style && *s.right_side_numbering_style != "N") {
        out += "," + *s.right_side_numbering_style + "," + opt_to_str(s.right_side_number_after) + "," +
               opt_to_str(e.right_side_number_before);
    } else {
        out += ",N,-1,-1";
    }
    if (s.left_side_zip_code || s.right_side_zip_code) {
        out += "," + (s.left_side_zip_code ? *s.left_side_zip_code : std::string("-1"));
        out += "," + (s.right_side_zip_code ? *s.right_side_zip_code : std::string("-1"));
        out += ",-1,-1";
    }
    return out;
}

}  // namespace pwm
