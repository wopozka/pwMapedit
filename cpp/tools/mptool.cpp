// Narzedzie wiersza polecen dla rdzenia C++ - lustro tools/py_reference.py.
//
//   mptool roundtrip <wejscie.mp> <wyjscie.mp>   wczytaj i zapisz, wypisz czasy
//   mptool dump <wejscie.mp>                     zrzut modelu danych (format identyczny z py_reference.py)
//   mptool ops <wejscie.mp>                      operacje na DataX (format identyczny z py_reference.py)
//   mptool warnings <wejscie.mp>                 ostrzezenia z wczytywania
//   mptool batch <lista.txt> <katalog>           wiele plikow: N.mp, N.dump, N.ops (lub N.err)
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <stdexcept>
#include <iostream>
#include <string>

#include "../core/map_data.hpp"
#include "../core/pyutil.hpp"

using namespace pwm;

namespace {

long long bits(double v) {
    int64_t b;
    std::memcpy(&b, &v, sizeof(b));
    return b;
}

const char* py_class_name(ObjectKind k) {
    switch (k) {
        case ObjectKind::Poi: return "PoiAsPixmap";
        case ObjectKind::Polyline: return "PolylineQGraphicsPathItem";
        case ObjectKind::Polygon: return "PolygonQGraphicsPathItem";
        case ObjectKind::Basic: break;
    }
    return "BasicMapItem";
}

std::string opt(const std::optional<std::string>& v) { return v ? *v : "None"; }
std::string opt(const std::optional<long long>& v) { return v ? std::to_string(*v) : "None"; }

std::string bbox_str(const GeoBBox& b) {
    if (!b.valid) return "None None None None";
    return py::repr(b.S) + " " + py::repr(b.N) + " " + py::repr(b.W) + " " + py::repr(b.E);
}

std::string numbers_str(const NumbersDefinition* d) { return d ? d->dump() : "-"; }

std::string exc_name(const std::exception& e) {
    std::string m = e.what();
    size_t c = m.find(':');
    return c == std::string::npos ? m : m.substr(0, c);
}

std::string join_record(const std::vector<std::string>& rec) {
    std::string s;
    for (size_t i = 0; i < rec.size(); ++i) {
        if (i) s += " # ";
        s += rec[i];
    }
    return s;
}

int cmd_roundtrip(const std::string& in, const std::string& out) {
    MapData map;
    auto t0 = std::chrono::steady_clock::now();
    LoadStats st = map.load(in);
    auto t1 = std::chrono::steady_clock::now();
    map.save(out);
    auto t2 = std::chrono::steady_clock::now();
    std::fprintf(stderr, "c++: objects=%zu load=%.3fs (read %.3fs, parse %.3fs) save=%.3fs warnings=%zu\n",
                 map.records_number(), std::chrono::duration<double>(t1 - t0).count(), st.read_seconds,
                 st.parse_seconds, std::chrono::duration<double>(t2 - t1).count(), map.warnings().size());
    return 0;
}

std::string dump_text(const MapData& map) {
    std::string out;
    for (const MapObject& obj : map.objects()) {
        out += "OBJ ";
        out += py_class_name(obj.kind());
        out += " id=" + std::to_string(*obj.id) + " type=" + opt(obj.type) + " end=" + std::to_string(obj.endlevel);
        out += std::string(" dir=") + (obj.dirindicator ? "True" : "None");
        out += " rp=";
        if (obj.routeparam) {
            out += '[';
            for (size_t i = 0; i < obj.routeparam->size(); ++i) {
                if (i) out += ", ";
                out += std::to_string((*obj.routeparam)[i]);
            }
            out += ']';
        } else {
            out += "None";
        }
        out += " roadid=" + opt(obj.roadid) + " city=" + opt(obj.cityname) + " zip=" + opt(obj.zipcode) + "\n";
        out += " bbox " + bbox_str(obj.bbox) + "\n";
        if (!obj.data) {
            out += " nodata\n";
            continue;
        }
        const DataX& dx = *obj.data;
        out += " levels ";
        for (size_t i = 0; i < dx.data_levels().size(); ++i) {
            if (i) out += ',';
            out += std::to_string(dx.data_levels()[i]);
        }
        out += '\n';
        const auto& raw = dx.raw_polys();
        for (size_t li = 0; li < raw.size(); ++li) {
            for (size_t pn = 0; pn < raw[li].size(); ++pn) {
                const Poly& poly = raw[li][pn];
                out += "  L" + std::to_string(li) + " P" + std::to_string(pn) + " n=" + std::to_string(poly.size()) +
                       "\n";
                for (const Node& n : poly) {
                    out += "   " + std::to_string(bits(n.x())) + " " + std::to_string(bits(n.y())) +
                           " h=" + opt(n.hlevel()) + " n=" + numbers_str(n.numbers()) + "\n";
                }
            }
        }
    }
    out += "MAPBBOX " + bbox_str(map.map_bounding_box()) + "\n";
    out += "PRECISION " + std::to_string(map.precision()) + "\n";
    return out;
}

int cmd_dump(const std::string& in) {
    MapData map;
    map.load(in);
    std::string out = dump_text(map);
    std::fwrite(out.data(), 1, out.size(), stdout);
    return 0;
}

std::string ops_text(const MapData& map) {
    const int prec = map.precision();
    std::string out;
    for (const MapObject& obj : map.objects()) {
        if (obj.kind() != ObjectKind::Polyline || !obj.data) continue;
        const DataX& dx = *obj.data;
        int level = dx.data_levels()[0];
        if (*dx.data_level_index(level) != static_cast<size_t>(level)) continue;
        const Poly& poly0 = (*dx.polys_for_data_level(level))[0];
        bool any = false;
        for (const Node& n : poly0) any = any || n.has_numeration();
        if (!any) continue;
        out += "OBJ " + std::to_string(*obj.id) + "\n";
        try {
            auto inter = dx.interpolated_housenumbers_for_poly(level, 0);
            for (const auto* side : {&inter.left, &inter.right}) {
                const char* name = side == &inter.left ? "left" : "right";
                for (const auto& item : *side)
                    out += std::string(" I ") + name + " " + std::to_string(item.number) + " " +
                           std::to_string(bits(item.position.x)) + " " + std::to_string(bits(item.position.y)) + "\n";
            }
        } catch (const std::exception& e) {
            out += " I EXC " + exc_name(e) + "\n";
        }
        for (size_t node_num = 0; node_num < poly0.size(); ++node_num) {
            try {
                auto d = dx.calculated_housenumber_defs_for_node(level, 0, node_num);
                out += " C " + std::to_string(node_num) + " " + (d ? d->dump() : std::string("-")) + "\n";
            } catch (const std::exception& e) {
                out += " C " + std::to_string(node_num) + " EXC " + exc_name(e) + "\n";
            }
        }
        for (long node_num = 1; node_num < static_cast<long>(poly0.size()) - 1; ++node_num) {
            try {
                auto parts = dx.split_data_x(level, 0, node_num);
                for (const auto& part : parts)
                    out += " S " + std::to_string(node_num) + " " + join_record(part.to_mp_record(prec)) + "\n";
            } catch (const std::exception& e) {
                out += " S " + std::to_string(node_num) + " EXC " + exc_name(e) + "\n";
            }
        }
        try {
            DataX rev = dx;
            rev.reverse_poly(level);
            out += " R " + join_record(rev.to_mp_record(prec)) + "\n";
        } catch (const std::exception& e) {
            out += " R EXC " + exc_name(e) + "\n";
        }
    }
    out += "PRECISION " + std::to_string(prec) + "\n";
    return out;
}

int cmd_ops(const std::string& in) {
    MapData map;
    map.load(in);
    std::string out = ops_text(map);
    std::fwrite(out.data(), 1, out.size(), stdout);
    return 0;
}

void write_file(const std::string& path, const std::string& content) {
    std::FILE* f = std::fopen(path.c_str(), "wb");
    if (!f) throw std::runtime_error("Nie mozna zapisac: " + path);
    std::fwrite(content.data(), 1, content.size(), f);
    std::fclose(f);
}

// Wiele plikow: dla pliku nr N zapisuje N.mp, N.dump, N.ops (format jak py_reference.py batch).
int cmd_batch(const std::string& list_file, const std::string& out_dir) {
    std::ifstream f(list_file);
    if (!f) throw std::runtime_error("Nie mozna otworzyc listy: " + list_file);
    std::string path;
    size_t num = 0;
    double total_load = 0;
    while (std::getline(f, path)) {
        if (path.empty()) continue;
        std::string base = out_dir + "/" + std::to_string(num++);
        try {
            MapData map;
            auto t0 = std::chrono::steady_clock::now();
            map.load(path);
            total_load += std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
            map.save(base + ".mp");
            write_file(base + ".dump", dump_text(map));
            write_file(base + ".ops", ops_text(map));
        } catch (const std::exception& e) {
            write_file(base + ".err", std::string(e.what()) + "\n");
        }
    }
    std::fprintf(stderr, "c++ batch: %zu plikow, laczny czas wczytywania %.2fs\n", num, total_load);
    return 0;
}

int cmd_warnings(const std::string& in) {
    MapData map;
    LoadStats st = map.load(in);
    std::printf("obiekty: %zu, pominiete rekordy: %zu, zalaczniki: %zu, ostrzezenia: %zu\n", map.records_number(),
                st.skipped_records, map.attachments().size(), map.warnings().size());
    for (const auto& w : map.warnings()) std::printf("  %s\n", w.c_str());
    return 0;
}

}  // namespace

int main(int argc, char** argv) {
    try {
        std::string cmd = argc > 1 ? argv[1] : "";
        if (cmd == "roundtrip" && argc == 4) return cmd_roundtrip(argv[2], argv[3]);
        if (cmd == "dump" && argc == 3) return cmd_dump(argv[2]);
        if (cmd == "ops" && argc == 3) return cmd_ops(argv[2]);
        if (cmd == "warnings" && argc == 3) return cmd_warnings(argv[2]);
        if (cmd == "batch" && argc == 4) return cmd_batch(argv[2], argv[3]);
        std::fprintf(stderr,
                     "uzycie:\n  mptool roundtrip <we.mp> <wy.mp>\n  mptool dump <we.mp>\n  mptool ops <we.mp>\n"
                     "  mptool warnings <we.mp>\n  mptool batch <lista.txt> <katalog>\n");
        return 2;
    } catch (const std::exception& e) {
        std::fprintf(stderr, "blad: %s\n", e.what());
        return 1;
    }
}
