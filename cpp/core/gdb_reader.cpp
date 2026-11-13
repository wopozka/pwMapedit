#include "gdb_reader.hpp"

#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <map>
#include <optional>
#include <sstream>

#include "misc.hpp"

namespace pwm::gps {

namespace {

// Kursor po danych rekordu: kazdy odczyt sprawdza, czy dane sa w granicach.
class Cursor {
public:
    Cursor(const char* begin, const char* end) : p_(begin), end_(end) {}
    size_t left() const { return static_cast<size_t>(end_ - p_); }
    bool skip(size_t n) {
        if (left() < n) return fail();
        p_ += n;
        return true;
    }
    template <typename T>
    bool read(T& v) {
        if (left() < sizeof(T)) return fail();
        std::memcpy(&v, p_, sizeof(T));  // plik w kolejnosci little-endian, jak x86/ARM
        p_ += sizeof(T);
        return true;
    }
    bool read_cstring(std::string& s) {
        const void* zero = std::memchr(p_, 0, left());
        if (!zero) return fail();
        const char* z = static_cast<const char*>(zero);
        s.assign(p_, z);
        p_ = z + 1;
        return true;
    }
    // bajt "jest/nie ma" i - gdy jest - wartosc typu T
    template <typename T>
    bool read_optional(std::optional<T>& v) {
        uint8_t has = 0;
        if (!read(has)) return false;
        if (!has) return true;
        T value{};
        if (!read(value)) return false;
        v = value;
        return true;
    }
    bool ok() const { return ok_; }

private:
    bool fail() {
        ok_ = false;
        return false;
    }
    const char* p_;
    const char* end_;
    bool ok_ = true;
};

double semicircles_to_deg(int32_t v) { return v * (180.0 / 2147483648.0); }

// Sekundy od 1970-01-01 (UTC) -> "RRRR-MM-DDTGG:MM:SSZ" (jak <time> w GPX).
std::string iso_time(uint32_t seconds) {
    int64_t days = seconds / 86400;
    const int64_t rest = seconds % 86400;
    // civil_from_days (H. Hinnant)
    days += 719468;
    const int64_t era = days / 146097;
    const int64_t doe = days - era * 146097;
    const int64_t yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
    int64_t y = yoe + era * 400;
    const int64_t doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    const int64_t mp = (5 * doy + 2) / 153;
    const int64_t d = doy - (153 * mp + 2) / 5 + 1;
    const int64_t m = mp < 10 ? mp + 3 : mp - 9;
    if (m <= 2) ++y;
    char buf[32];
    std::snprintf(buf, sizeof buf, "%04lld-%02lld-%02lldT%02lld:%02lld:%02lldZ", static_cast<long long>(y),
                  static_cast<long long>(m), static_cast<long long>(d), static_cast<long long>(rest / 3600),
                  static_cast<long long>(rest / 60 % 60), static_cast<long long>(rest % 60));
    return buf;
}

class Reader {
public:
    explicit Reader(GdbResult& r) : r_(r) {}

    std::string text(const std::string& raw) const {
        return version_ >= 3 ? raw : encoding::cp1250_to_utf8(raw);
    }

    void waypoint(Cursor c) {
        Waypoint w;
        std::string name;
        int32_t lat = 0, lon = 0;
        // nazwa, czesc stala (klasa, kraj, identyfikatory mapy, podklasy - 27 bajtow), wspolrzedne
        if (!c.read_cstring(name) || !c.skip(27) || !c.read(lat) || !c.read(lon)) {
            r_.warnings.push_back("Uszkodzony waypoint (pominięty)");
            return;
        }
        w.name = text(name);
        w.pos.lat = semicircles_to_deg(lat);
        w.pos.lon = semicircles_to_deg(lon);
        // dalej: wysokosc, komentarz, zasieg, sposob wyswietlania, kolor, symbol; reszty nie potrzebujemy
        std::optional<double> ele, proximity;
        std::string comment;
        uint32_t show = 0, color = 0, symbol = 0;
        if (c.read_optional(ele) && c.read_cstring(comment) && c.read_optional(proximity) && c.read(show) &&
            c.read(color) && c.read(symbol)) {
            w.pos.ele = ele;
            w.comment = text(comment);
            w.symbol = std::to_string(symbol);
        } else if (!c.ok()) {
            r_.warnings.push_back("Waypoint \"" + w.name + "\": niepełny rekord, wczytano tylko pozycję");
        }
        if (w.pos.lat < -90 || w.pos.lat > 90 || w.pos.lon < -180 || w.pos.lon > 180) {
            r_.warnings.push_back("Waypoint \"" + w.name + "\": niepoprawne współrzędne (pominięty)");
            return;
        }
        waypoints_by_name_.emplace(w.name, w.pos);
        r_.file.waypoints.push_back(std::move(w));
    }

    void track(Cursor c) {
        Track t;
        std::string name;
        uint8_t display = 0;
        uint32_t color = 0, count = 0;
        if (!c.read_cstring(name) || !c.read(display) || !c.read(color) || !c.read(count)) {
            r_.warnings.push_back("Uszkodzony ślad (pominięty)");
            return;
        }
        t.name = text(name);
        std::vector<Point> points;
        points.reserve(std::min<size_t>(count, c.left() / 12 + 1));
        for (uint32_t i = 0; i < count; ++i) {
            int32_t lat = 0, lon = 0;
            std::optional<double> ele, depth, temperature;
            std::optional<uint32_t> time;
            if (!c.read(lat) || !c.read(lon) || !c.read_optional(ele) || !c.read_optional(time) ||
                !c.read_optional(depth) || !c.read_optional(temperature)) {
                // jak w GPSMapEdit: liczba punktow w naglowku wieksza niz dane - zostawiamy wczytane punkty
                r_.warnings.push_back("Ślad \"" + t.name + "\" jest uszkodzony: wczytano " + std::to_string(points.size()) +
                                      " z " + std::to_string(count) + " punktów");
                break;
            }
            Point p;
            p.lat = semicircles_to_deg(lat);
            p.lon = semicircles_to_deg(lon);
            p.ele = ele;
            if (time) p.time = iso_time(*time);
            points.push_back(std::move(p));
        }
        if (points.empty()) return;
        t.segments.push_back(std::move(points));
        r_.file.tracks.push_back(std::move(t));
    }

    // Trasa: nazwa, znaczniki, opcjonalny prostokat ograniczajacy, potem odcinki ("linki"): nazwa waypointu
    // poczatkowego, czesc stala, punkty odcinka (dla tras wyznaczonych przez MapSource - geometria drogi),
    // bajt "ostatni odcinek", prostokat odcinka. Ostatni odcinek nie ma punktow (to punkt docelowy). Odcinek
    // konczy sie w punkcie, w ktorym zaczyna sie nastepny, wiec przy sklejaniu punkt styku jest pomijany.
    // Dane za odcinkami (linki, w v3 dalsze pola) nie sa potrzebne.
    void route(Cursor c) {
        Track t;
        t.route = true;
        std::string name;
        uint8_t auto_named = 0, no_bounds = 0;
        uint32_t links = 0;
        if (!c.read_cstring(name) || !c.read(auto_named) || !c.read(no_bounds) ||
            (!no_bounds && (!skip_xyz(c) || !skip_xyz(c))) || !c.read(links)) {
            r_.warnings.push_back("Uszkodzona trasa (pominięta)");
            return;
        }
        t.name = text(name);
        std::vector<Point> points;
        bool damaged = false;
        for (uint32_t link = 0; link < links && !damaged; ++link) {
            std::string wpt_name;
            uint32_t count = 0;
            if (!c.read_cstring(wpt_name) || !c.skip(27)) {
                damaged = true;
                break;
            }
            // trasy utworzone w odbiorniku maja tu 8 bajtow 0xFF (jak w GPSMapEdit)
            uint8_t marker = 0;
            if (Cursor peek = c; peek.read(marker) && marker == 0xFF && !c.skip(8)) {
                damaged = true;
                break;
            }
            if (!c.skip(19) || !c.read(count)) {
                damaged = true;
                break;
            }
            std::vector<Point> link_points;
            for (uint32_t i = 0; i < count; ++i) {
                int32_t lat = 0, lon = 0;
                std::optional<double> ele;
                if (!c.read(lat) || !c.read(lon) || !c.read_optional(ele)) {
                    damaged = true;
                    break;
                }
                Point p;
                p.lat = semicircles_to_deg(lat);
                p.lon = semicircles_to_deg(lon);
                p.ele = ele;
                link_points.push_back(p);
            }
            if (link_points.empty()) {
                // odcinek bez geometrii: punkt z waypointu o tej nazwie (ostatni odcinek - punkt docelowy)
                auto it = waypoints_by_name_.find(text(wpt_name));
                if (it != waypoints_by_name_.end()) link_points.push_back(it->second);
            }
            // pomijany punkt styku z poprzednim odcinkiem i kazdy punkt rowny poprzedniemu (odcinki o zerowej
            // dlugosci - np. dwa waypointy w tym samym miejscu), zeby polilinia nie dostala podwojnych wezlow
            for (const Point& p : link_points) {
                if (!points.empty() && points.back().lat == p.lat && points.back().lon == p.lon) continue;
                points.push_back(p);
            }
            if (damaged) break;
            uint8_t last = 0;
            if (!c.read(last) || (link + 1 < links && (!skip_xyz(c) || !skip_xyz(c))) ||
                (version_ == 2 && !c.skip(8)) || (version_ >= 3 && !c.skip(10))) {
                damaged = link + 1 < links;  // brak danych po ostatnim odcinku nie szkodzi geometrii
                break;
            }
        }
        if (damaged)
            r_.warnings.push_back("Trasa \"" + t.name + "\" jest uszkodzona: wczytano " + std::to_string(points.size()) +
                                  " punktów");
        if (points.size() < 2) return;
        t.segments.push_back(std::move(points));
        r_.file.tracks.push_back(std::move(t));
    }

    void set_version(int v) { version_ = v; }

private:
    // punkt z opcjonalna wysokoscia (prostokaty ograniczajace tras) - pomijany
    static bool skip_xyz(Cursor& c) {
        std::optional<double> ele;
        return c.skip(8) && c.read_optional(ele);
    }
    GdbResult& r_;
    int version_ = 1;
    std::map<std::string, Point> waypoints_by_name_;  // dla odcinkow tras bez punktow
};

}  // namespace

GdbResult read_gdb(std::string_view data) {
    GdbResult r;
    static const char SIGNATURE[6] = {'M', 's', 'R', 'c', 'f', '\0'};
    if (data.size() < 6 || std::memcmp(data.data(), SIGNATURE, 6) != 0) {
        r.error = "To nie jest plik GDB (brak sygnatury MsRcf).";
        return r;
    }
    Reader reader(r);
    size_t off = 6;
    bool version_seen = false;
    while (off + 5 <= data.size()) {
        uint32_t len = 0;
        std::memcpy(&len, data.data() + off, 4);
        const char type = data[off + 4];
        const size_t body = off + 5;
        if (len > data.size() - body) {
            // ostatni rekord dluzszy niz plik - czytamy to, co jest (np. uciety slad)
            r.warnings.push_back("Plik jest ucięty");
            len = static_cast<uint32_t>(data.size() - body);
        }
        Cursor c(data.data() + body, data.data() + body + len);
        size_t next = body + len;
        switch (type) {
            case 'D': {
                uint16_t v = 0;
                if (c.read(v)) {
                    r.version = v >= 0x6B ? v - 0x6B + 1 : 0;
                    reader.set_version(r.version);
                    version_seen = true;
                    if (v > 0x6D) r.warnings.push_back("Nieznana, nowsza wersja formatu GDB - wynik może być niepełny");
                }
                break;
            }
            case 'A': {
                // za rekordem nazwa programu zakonczona zerem ("MapSource", "BaseCamp")
                const void* zero = std::memchr(data.data() + next, 0, std::min<size_t>(32, data.size() - next));
                if (zero) {
                    const char* z = static_cast<const char*>(zero);
                    bool letters = z > data.data() + next;
                    for (const char* q = data.data() + next; q < z; ++q)
                        letters = letters && ((*q >= 'A' && *q <= 'Z') || (*q >= 'a' && *q <= 'z') || *q == ' ');
                    if (letters) next = static_cast<size_t>(z - data.data()) + 1;
                }
                break;
            }
            case 'W':
                reader.waypoint(c);
                break;
            case 'T':
                reader.track(c);
                break;
            case 'R':
                reader.route(c);
                break;
            default:
                break;  // 'L' (mapa), 'V' (koniec) i inne - pomijamy
        }
        off = next;
    }
    if (!version_seen) {
        r.error = "Brak rekordu wersji formatu GDB.";
        return r;
    }
    r.ok = true;
    return r;
}

GdbResult read_gdb_file(const std::string& path) {
    // sciezka w UTF-8 (np. "Mój zbiór.gdb") - na Windows zwykly std::ifstream(std::string) jej nie otworzy
    std::ifstream f(std::filesystem::u8path(path), std::ios::binary);
    if (!f) {
        GdbResult r;
        r.error = "Nie można otworzyć pliku: " + path;
        return r;
    }
    std::ostringstream ss;
    ss << f.rdbuf();
    GdbResult r = read_gdb(ss.str());
    r.file.path = path;
    return r;
}

}  // namespace pwm::gps
