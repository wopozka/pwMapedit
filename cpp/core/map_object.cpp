#include "map_object.hpp"

#include <algorithm>

#include "pyutil.hpp"

namespace pwm {

const char* object_kind_section(ObjectKind kind) {
    switch (kind) {
        case ObjectKind::Poi: return "[POI]";
        case ObjectKind::Polyline: return "[POLYLINE]";
        case ObjectKind::Polygon: return "[POLYGON]";
        case ObjectKind::Basic: break;
    }
    return "";
}

bool is_map_object_type(std::string_view s) { return s == "[POI]" || s == "[POLYGON]" || s == "[POLYLINE]"; }

bool is_any_map_object(std::string_view s) { return is_map_object_type(s) || s == "[RESTRICT]" || s == "[SIGN]"; }

ParsedRecord parse_record(const std::vector<std::string_view>& lines) {
    ParsedRecord rec;
    bool inside_record = false;
    for (std::string_view raw : lines) {
        std::string_view line = py::strip(raw);
        if (line.empty()) continue;
        if (line[0] == ';' && !inside_record) {
            rec.comments.push_back(line.substr(1));
        } else if (is_any_map_object(line)) {
            if (rec.head == ParsedRecord::Head::None) {
                rec.head = ParsedRecord::Head::Section;
                rec.section = line;
            }
            inside_record = true;
        } else if (line.find('=') != std::string_view::npos) {
            size_t eq = line.find('=');
            std::string_view key = line.substr(0, eq);
            std::string_view val = line.substr(eq + 1);
            rec.fields.push_back({key, val});
            if (key == "Type") {
                if (!py::to_int(val, 16)) rec.type_parse_error = true;
                if (rec.head == ParsedRecord::Head::None) rec.head = ParsedRecord::Head::TypeValue;
            }
        } else if (line == "[END]") {
            break;
        } else {
            rec.unknown_lines.push_back(line);
        }
    }
    return rec;
}

void MapObject::set_datax(std::string_view key, std::string_view value, int& max_precision) {
    if (!data) data.emplace(projection_);
    int p = data->add_nodes_from_string(key, value);
    if (p >= 0) max_precision = std::max(max_precision, p);
    bbox.extend(data->obj_bounding_box());
}

void MapObject::set_hlevels(std::string_view hlevel_items) {
    if (!data) throw MpError("AttributeError: HLevel przed Data");
    std::string_view body = py::rstrip(py::lstrip(hlevel_items, '('), ')');
    for (std::string_view item : py::split(body, "),(")) data->add_hlevels_from_string(item);
}

void MapObject::set_route_params(const std::vector<std::string_view>& values) {
    if (!routeparam) routeparam.emplace();  // przy pierwszym ustawieniu 12 zer
    for (size_t i = 0; i < values.size(); ++i) {
        // jak w Pythonie: najpierw int(), dopiero potem IndexError przy > 12 wartosciach
        auto v = py::to_int(values[i]);
        if (!v) throw MpError("ValueError: RouteParam");
        if (i >= routeparam->size()) return;
        (*routeparam)[i] = *v;
    }
}

void MapObject::set_data(const std::vector<std::string_view>& comments, const std::vector<RecordField>& fields,
                         int& max_precision, std::vector<std::string>& warnings) {
    if (!comments.empty()) comment.emplace(comments.begin(), comments.end());
    for (const RecordField& f : fields) {
        std::string_view key = f.key;
        std::string_view val = f.value;
        try {
            if (key == "Type") {
                auto t = py::to_int(val, 16);
                if (!t) throw MpError("ValueError: Type");
                type = *t;
            } else if (key == "CityName") {
                cityname = std::string(val);
            } else if (key == "CountryName") {
                countryname = std::string(val);
            } else if (key == "RegionName") {
                regionname = std::string(val);
            } else if (key == "CountryCode") {
                countrycode = std::string(val);
            } else if (key == "ZipCode") {
                zipcode = std::string(val);
            } else if (key == "DistrictName") {
                districtname = std::string(val);
            } else if (key == "Data0" || key == "Data1" || key == "Data2" || key == "Data3" || key == "Data4") {
                set_datax(key, val, max_precision);
            } else if (key == "RouteParam") {
                set_route_params(py::split(val, ","));
            } else if (key == "StreetDesc") {
                streetdesc = std::string(val);
            } else if (key == "HouseNumber") {
                housenumber = std::string(val);
            } else if (key == "Phone") {
                phone = std::string(val);
            } else if (key == "Label") {
                label1 = std::string(val);
            } else if (key == "Label2") {
                label2 = std::string(val);
            } else if (key == "Label3") {
                label3 = std::string(val);
            } else if (key == "DirIndicator") {
                set_dirindicator(val);
            } else if (key == "EndLevel") {
                auto v = py::to_int(val);
                if (!v) throw MpError("ValueError: EndLevel");
                endlevel = *v;
            } else if (key == "RoadID") {
                auto v = py::to_int(val);
                if (!v) throw MpError("ValueError: RoadID");
                roadid = *v;
            } else if (py::starts_with(key, "Nod")) {
                // pomijane (tak jak w wersji Python)
            } else if (py::starts_with(key, "Numbers")) {
                if (!data) throw MpError("AttributeError: Numbers przed Data");
                data->add_housenumbers_from_string(val);
            } else if (py::starts_with(key, "HLevel")) {
                set_hlevels(val);
            } else {
                others.emplace_back(std::string(key), std::string(val));
            }
        } catch (const std::exception& e) {
            warnings.push_back(std::string(key) + "=" + std::string(val.substr(0, 60)) + ": " + e.what());
        }
    }
}

std::vector<std::string> MapObject::to_mp_record(int precision) const {
    std::vector<std::string> rec;
    if (comment && !comment->empty())
        for (const auto& c : *comment) rec.push_back(";" + c);
    if (kind_ != ObjectKind::Basic) rec.emplace_back(object_kind_section(kind_));
    if (type) rec.push_back("Type=" + py::hex(*type));
    if (label1 && !label1->empty()) rec.push_back("Label=" + *label1);
    if (endlevel) rec.push_back("EndLevel=" + std::to_string(endlevel));
    if (dirindicator) rec.emplace_back("DirIndicator=1");
    if (routeparam) {
        std::string s = "RouteParam=";
        for (size_t i = 0; i < routeparam->size(); ++i) {
            if (i) s += ',';
            s += std::to_string((*routeparam)[i]);
        }
        rec.push_back(std::move(s));
    }
    if (housenumber && !housenumber->empty()) rec.push_back("HouseNumber=" + *housenumber);
    if (streetdesc && !streetdesc->empty()) rec.push_back("StreetDesc=" + *streetdesc);
    if (phone && !phone->empty()) rec.push_back("Phone=" + *phone);
    if (data) {
        auto d = data->to_mp_record(precision);
        rec.insert(rec.end(), std::make_move_iterator(d.begin()), std::make_move_iterator(d.end()));
    }
    if (label2 && !label2->empty()) rec.push_back("Label2=" + *label2);
    if (label3 && !label3->empty()) rec.push_back("Label3=" + *label3);
    for (const auto& [k, v] : others) rec.push_back(k + "=" + v);
    return rec;
}

}  // namespace pwm
