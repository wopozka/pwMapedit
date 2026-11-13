// Czytnik GDB: prawdziwe pliki BaseCamp (tests/gdb) i pliki budowane w tescie wedlug struktury formatu.
#include <cmath>
#include <cstdint>
#include <cstring>
#include <regex>
#include <string>

#include "../core/gdb_reader.hpp"
#include "test_framework.hpp"

using namespace pwm::gps;

namespace {

const std::string DATA = PWM_TEST_DATA_DIR "/gdb/";

// --- budowanie pliku GDB w tescie ---
template <typename T>
void put(std::string& s, T v) {
    s.append(reinterpret_cast<const char*>(&v), sizeof(T));
}
void put_str(std::string& s, const std::string& v) {
    s += v;
    s += '\0';
}
int32_t semi(double deg) { return static_cast<int32_t>(std::llround(deg * 2147483648.0 / 180.0)); }
void record(std::string& file, char type, const std::string& body) {
    put<uint32_t>(file, static_cast<uint32_t>(body.size()));
    file += type;
    file += body;
}
std::string header(uint16_t version, const std::string& app) {
    std::string f = std::string("MsRcf", 5) + '\0';
    std::string d;
    put<uint16_t>(d, version);
    record(f, 'D', d);
    std::string a;
    put<uint16_t>(a, 0x258);
    put_str(a, "builder");
    put_str(a, "Nov 18 2002");
    put_str(a, "14:11:40");
    record(f, 'A', a);
    put_str(f, app);  // nazwa programu za rekordem A
    return f;
}
std::string waypoint(const std::string& name, double lat, double lon, bool with_ele, const std::string& comment,
                     uint32_t symbol) {
    std::string w;
    put_str(w, name);
    put<uint32_t>(w, 0);           // klasa
    w += '\0';                     // kraj
    put<uint32_t>(w, 0);           // segment mapy
    put<uint32_t>(w, 0xFFFFFFFF);  // obiekt mapy
    put<uint32_t>(w, 0xFFFFFFFF);
    put<uint32_t>(w, 0xFFFFFFFF);
    put<uint16_t>(w, 0);
    put<uint32_t>(w, 0xFFFFFFFF);
    put<int32_t>(w, semi(lat));
    put<int32_t>(w, semi(lon));
    put<uint8_t>(w, with_ele);
    if (with_ele) put<double>(w, 101.5);
    put_str(w, comment);
    put<uint8_t>(w, 0);  // zasieg
    put<uint32_t>(w, 1);  // wyswietlanie
    put<uint32_t>(w, 0);  // kolor
    put<uint32_t>(w, symbol);
    w += std::string(20, '\0');  // dalsze pola (miasto, stan, ...) - czytnik ich nie potrzebuje
    return w;
}
std::string track(const std::string& name, uint32_t declared, int written) {
    std::string t;
    put_str(t, name);
    put<uint8_t>(t, 1);
    put<uint32_t>(t, 9);
    put<uint32_t>(t, declared);
    for (int i = 0; i < written; ++i) {
        put<int32_t>(t, semi(52.0 + i * 0.001));
        put<int32_t>(t, semi(21.0));
        put<uint8_t>(t, i == 0);
        if (i == 0) put<double>(t, 120.0);
        put<uint8_t>(t, i == 0);
        if (i == 0) put<uint32_t>(t, 1786730400);  // 2026-08-14T18:00:00Z
        put<uint8_t>(t, 0);
        put<uint8_t>(t, 0);
    }
    return t;
}

}  // namespace

TEST(gdb_basecamp_single_track) {
    GdbResult r = read_gdb_file(DATA + "20260809-195440.gdb");
    CHECK(r.ok);
    CHECK_EQ(r.version, 3);
    CHECK(r.warnings.empty());
    CHECK_EQ(r.file.tracks.size(), size_t{1});
    CHECK(r.file.waypoints.empty());
    const Track& t = r.file.tracks[0];
    CHECK_EQ(t.name, std::string("Track 20260809-195440"));
    CHECK_EQ(t.segments.size(), size_t{1});
    CHECK_EQ(t.segments[0].size(), size_t{1488});
    CHECK_NEAR(t.segments[0][0].lat, 51.58096678555012, 1e-12);
    CHECK_NEAR(t.segments[0][0].lon, 20.319392401725054, 1e-12);
    CHECK(t.segments[0][0].ele.has_value());
    CHECK(t.segments[0][0].time.has_value());
    CHECK(std::regex_match(*t.segments[0][0].time, std::regex(R"(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ)")));
    // wszystkie punkty w Polsce
    for (const Point& p : t.segments[0]) CHECK(p.lat > 49 && p.lat < 55 && p.lon > 14 && p.lon < 25);
}

TEST(gdb_basecamp_two_tracks_utf8_file_name) {
    GdbResult r = read_gdb_file(DATA + "M\xc3\xb3j zbi\xc3\xb3r.gdb");  // "Mój zbiór.gdb"
    CHECK(r.ok);
    CHECK_EQ(r.file.tracks.size(), size_t{2});
    CHECK_EQ(r.file.tracks[0].name, std::string("Track 20250911-110754"));
    CHECK_EQ(r.file.tracks[0].segments[0].size(), size_t{481});
    CHECK_EQ(r.file.tracks[1].segments[0].size(), size_t{1488});
}

TEST(gdb_v1_waypoints_cp1250_track_route) {
    std::string f = header(0x6B, "MapSource");
    record(f, 'W', waypoint("\xa3\xf3\x64\x9f", 52.1, 21.0, true, "koment", 8));  // "Łódź" w cp1250
    record(f, 'W', waypoint("Most", 52.2, 21.1, false, "", 0));
    record(f, 'T', track("Slad", 3, 3));
    record(f, 'R', std::string(10, '\0'));
    record(f, 'V', std::string("\0\1", 2));
    GdbResult r = read_gdb(f);
    CHECK(r.ok);
    CHECK_EQ(r.version, 1);
    CHECK_EQ(r.file.waypoints.size(), size_t{2});
    CHECK_EQ(r.file.waypoints[0].name, std::string("\xc5\x81\xc3\xb3\x64\xc5\xba"));  // UTF-8
    CHECK_NEAR(r.file.waypoints[0].pos.lat, 52.1, 1e-7);
    CHECK_NEAR(r.file.waypoints[0].pos.lon, 21.0, 1e-7);
    CHECK(r.file.waypoints[0].pos.ele && *r.file.waypoints[0].pos.ele == 101.5);
    CHECK_EQ(r.file.waypoints[0].comment, std::string("koment"));
    CHECK_EQ(r.file.waypoints[0].symbol, std::string("8"));
    CHECK(!r.file.waypoints[1].pos.ele);
    CHECK_EQ(r.file.tracks.size(), size_t{1});
    CHECK_EQ(r.file.tracks[0].segments[0].size(), size_t{3});
    CHECK_EQ(*r.file.tracks[0].segments[0][0].time, std::string("2026-08-14T18:00:00Z"));
    CHECK(!r.file.tracks[0].segments[0][1].time);
    CHECK_EQ(r.warnings.size(), size_t{1});  // pominieta trasa
}

TEST(gdb_v3_utf8_names) {
    std::string f = header(0x6D, "BaseCamp");
    record(f, 'W', waypoint("\xc5\x81\xc3\xb3\x64\xc5\xba", 52.1, 21.0, false, "", 0));  // UTF-8
    GdbResult r = read_gdb(f);
    CHECK(r.ok);
    CHECK_EQ(r.version, 3);
    CHECK_EQ(r.file.waypoints[0].name, std::string("\xc5\x81\xc3\xb3\x64\xc5\xba"));
}

TEST(gdb_damaged_track_and_truncated_file) {
    // naglowek sladu deklaruje 5 punktow, a sa 2 - jak "Track is damaged" w GPSMapEdit
    std::string f = header(0x6C, "MapSource");
    record(f, 'T', track("Uszkodzony", 5, 2));
    GdbResult r = read_gdb(f);
    CHECK(r.ok);
    CHECK_EQ(r.file.tracks[0].segments[0].size(), size_t{2});
    CHECK_EQ(r.warnings.size(), size_t{1});

    // plik uciety w polowie rekordu sladu
    std::string g = header(0x6C, "MapSource");
    record(g, 'T', track("Uciety", 3, 3));
    g.resize(g.size() - 5);
    GdbResult r2 = read_gdb(g);
    CHECK(r2.ok);
    CHECK_EQ(r2.file.tracks[0].segments[0].size(), size_t{2});

    // nie GDB
    CHECK(!read_gdb("<gpx></gpx>").ok);
    CHECK(!read_gdb(std::string("MsRcf\0", 6)).ok);  // bez rekordu wersji
    CHECK(!read_gdb_file(DATA + "nie_ma.gdb").ok);
}
