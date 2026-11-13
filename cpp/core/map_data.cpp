#include "map_data.hpp"

#include <chrono>
#include <cstdio>
#include <fstream>
#include <sstream>
#include <stdexcept>

#include "pyutil.hpp"

namespace pwm {

namespace {
double seconds_since(std::chrono::steady_clock::time_point t0) {
    return std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
}
}  // namespace

std::vector<std::string_view> split_lines(std::string_view content) {
    std::vector<std::string_view> lines;
    lines.reserve(content.size() / 40 + 16);
    size_t start = 0;
    const size_t n = content.size();
    for (size_t i = 0; i < n; ++i) {
        char c = content[i];
        if (c == '\n') {
            lines.push_back(content.substr(start, i - start));
            start = i + 1;
        } else if (c == '\r') {
            lines.push_back(content.substr(start, i - start));
            if (i + 1 < n && content[i + 1] == '\n') ++i;
            start = i + 1;
        }
    }
    if (start < n) lines.push_back(content.substr(start));
    return lines;
}

MapData::MapData(std::unique_ptr<Projection> projection) : projection_(std::move(projection)) {
    if (!projection_) projection_ = std::make_unique<MercatorProjection>();
}

LoadStats MapData::load(const std::string& path) {
    auto t0 = std::chrono::steady_clock::now();
    std::ifstream f(path, std::ios::binary);
    if (!f) throw std::runtime_error("Nie mozna otworzyc pliku: " + path);
    std::string content;
    f.seekg(0, std::ios::end);
    auto size = f.tellg();
    f.seekg(0, std::ios::beg);
    if (size > 0) {
        content.resize(static_cast<size_t>(size));
        f.read(content.data(), size);
    }
    double read_s = seconds_since(t0);
    LoadStats st = load_from_string(std::move(content));
    st.read_seconds = read_s;
    return st;
}

LoadStats MapData::load_from_string(std::string content) {
    auto t0 = std::chrono::steady_clock::now();
    LoadStats st;
    header_.clear();
    attachments_.clear();
    objects_.clear();
    warnings_.clear();
    bbox_ = GeoBBox{};

    std::vector<std::string_view> lines = split_lines(content);
    st.lines = lines.size();

    // Na koncu pliku moga byc zalaczniki: ";@File ..." / ";@WEBMAP ...".
    while (!lines.empty() && py::starts_with(lines.back(), ";@")) {
        attachments_.insert(attachments_.begin(), std::string(lines.back()));
        lines.pop_back();
    }
    // puste linie az do ostatniego [END]
    while (!lines.empty() && py::strip(lines.back()).empty()) lines.pop_back();

    const long n = static_cast<long>(lines.size());
    if (n == 0) return st;
    auto at = [&](long i) -> std::string_view { return lines[static_cast<size_t>(i < 0 ? i + n : i)]; };

    // Naglowek: wszystko przed pierwszym [POI]/[POLYGON]/[POLYLINE], bez komentarzy bezposrednio nad nim
    // (te naleza do pierwszego obiektu). Algorytm 1:1 z MapFileOpener.wczytaj_rekordy.
    long b = -1;
    bool found_object = false;
    while (b < n) {
        if (!is_map_object_type(py::strip(at(b)))) {
            b += 1;
            if (b >= n) break;  // Python: IndexError - plik bez obiektow
            header_.emplace_back(at(b));
        } else {
            b -= 1;
            if (!header_.empty()) header_.pop_back();
            found_object = true;
            break;
        }
    }
    if (!found_object) {
        // Plik bez obiektow - Python konczyl sie wyjatkiem. Calosc traktujemy jako naglowek.
        warnings_.emplace_back("Brak obiektow mapy w pliku");
        return st;
    }
    while (b >= 0 && py::starts_with(py::strip(at(b)), ";")) {
        b -= 1;
        if (!header_.empty()) header_.pop_back();
    }
    // Python: dla plikow bez naglowka b == -1 wskazywalo na ostatnia linie i wczytywanie sie wywracalo.
    if (b < 0) b = 0;

    std::vector<std::string_view> mp_record;
    while (b < n) {
        mp_record.clear();
        std::string_view line = py::strip(at(b));
        while (!py::starts_with(line, "[END]") && b < n - 1) {
            mp_record.push_back(line);
            b += 1;
            line = at(b);
        }
        ParsedRecord rec = parse_record(mp_record);
        for (std::string_view u : rec.unknown_lines)
            warnings_.push_back("Nieznana linia bez '=': " + std::string(u.substr(0, 80)));

        ObjectKind kind = ObjectKind::Basic;
        if (rec.head == ParsedRecord::Head::Section) {
            if (rec.section == "[POI]")
                kind = ObjectKind::Poi;
            else if (rec.section == "[POLYLINE]")
                kind = ObjectKind::Polyline;
            else if (rec.section == "[POLYGON]")
                kind = ObjectKind::Polygon;
        } else if (rec.head == ParsedRecord::Head::None && !mp_record.empty()) {
            warnings_.push_back("Rekord bez typu obiektu zostal pominiety (linia " + std::to_string(b + 1) + ")");
        }
        if (rec.type_parse_error)
            warnings_.push_back("Niepoprawne Type= w rekordzie (linia " + std::to_string(b + 1) + ")");

        if (kind != ObjectKind::Basic) {
            MapObject obj(kind, projection_.get());
            std::vector<std::string> obj_warnings;
            obj.set_data(rec.comments, rec.fields, precision_, obj_warnings);
            for (auto& w : obj_warnings)
                warnings_.push_back("Obiekt " + std::to_string(objects_.size()) + ": " + std::move(w));
            MapObject& added = add_map_object(std::move(obj));
            bbox_.extend(added.bbox);
            ++st.records;
        } else if (!mp_record.empty()) {
            ++st.skipped_records;
        }
        b += 1;
    }
    st.parse_seconds = seconds_since(t0);
    return st;
}

std::optional<MapObject> MapData::object_from_record(const std::vector<std::string>& lines,
                                                     std::vector<std::string>* warnings) {
    std::vector<std::string_view> views;
    for (const std::string& line : lines) {
        std::string_view v = py::strip(line);
        if (v == "[END]") break;
        views.push_back(v);
    }
    ParsedRecord rec = parse_record(views);
    if (rec.head != ParsedRecord::Head::Section) return std::nullopt;
    ObjectKind kind;
    if (rec.section == "[POI]")
        kind = ObjectKind::Poi;
    else if (rec.section == "[POLYLINE]")
        kind = ObjectKind::Polyline;
    else if (rec.section == "[POLYGON]")
        kind = ObjectKind::Polygon;
    else
        return std::nullopt;
    MapObject obj(kind, projection_.get());
    std::vector<std::string> obj_warnings;
    obj.set_data(rec.comments, rec.fields, precision_, obj_warnings);
    if (warnings) warnings->insert(warnings->end(), obj_warnings.begin(), obj_warnings.end());
    if (!obj.data || obj.data->data_levels().empty()) return std::nullopt;
    return obj;
}

MapObject& MapData::add_map_object(MapObject obj) {
    if (!obj.id) obj.id = objects_.size();
    const size_t id = *obj.id;
    if (id < objects_.size()) {
        // obiekt o istniejacym id zastepuje poprzedni (np. undo/redo)
        objects_[id] = std::move(obj);
        return objects_[id];
    }
    objects_.push_back(std::move(obj));
    return objects_.back();
}

void MapData::set_map_object_deleted(size_t id, bool deleted) {
    if (id < objects_.size()) objects_[id].deleted = deleted;
}

std::string MapData::to_mp_string() const {
    std::string out;
    size_t estimate = 0;
    for (const auto& h : header_) estimate += h.size() + 1;
    out.reserve(estimate + objects_.size() * 300);
    for (const auto& h : header_) {
        out += h;
        out += '\n';
    }
    for (const MapObject& obj : objects_) {
        if (obj.deleted) continue;
        for (const std::string& line : obj.to_mp_record(precision_)) {
            out += line;
            out += '\n';
        }
        out += "[END]\n\n";
    }
    return out;
}

void MapData::save(const std::string& path) const {
    std::string content = to_mp_string();
    std::FILE* f = std::fopen(path.c_str(), "wb");
    if (!f) throw std::runtime_error("Nie mozna zapisac pliku: " + path);
    size_t written = std::fwrite(content.data(), 1, content.size(), f);
    int closed = std::fclose(f);
    if (written != content.size() || closed != 0) throw std::runtime_error("Blad zapisu pliku: " + path);
}

}  // namespace pwm
