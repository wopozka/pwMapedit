// Port mapData.py oraz logiki MapFileOpener/MapFileSaver z pwMapEdit.py (bez Qt).
//
// Tekst jest przechowywany jako bajty cp1250 (tak jak w pliku) - konwersja do UTF-8 bedzie w warstwie GUI.
#pragma once

#include <functional>
#include <memory>
#include <optional>
#include <string>
#include <vector>

#include "map_object.hpp"
#include "projection.hpp"

namespace pwm {

struct LoadStats {
    double read_seconds = 0;
    double parse_seconds = 0;
    size_t lines = 0;
    size_t records = 0;
    size_t skipped_records = 0;  // [RESTRICT], [SIGN] i rekordy bez typu (Python je pomijal)
};

class MapData {
public:
    explicit MapData(std::unique_ptr<Projection> projection = nullptr);
    MapData(const MapData&) = delete;
    MapData& operator=(const MapData&) = delete;
    MapData(MapData&&) = default;
    MapData& operator=(MapData&&) = default;

    // Wczytanie pliku mp. Rzuca std::runtime_error, gdy pliku nie da sie odczytac.
    LoadStats load(const std::string& path);
    LoadStats load_from_string(std::string content);

    // Zapis jak MapFileSaver: naglowek, potem rekordy (bez usunietych), kazdy zakonczony "[END]" i pusta linia.
    void save(const std::string& path) const;
    // progress(zapisane, wszystkie) - wywolywane co pewna liczbe obiektow i na koniec (jak sygnal progress
    // MapFileSaver w Pythonie).
    std::string to_mp_string(const std::function<void(size_t, size_t)>& progress = {}) const;

    const std::vector<MapObject>& objects() const { return objects_; }
    std::vector<MapObject>& objects() { return objects_; }
    size_t records_number() const { return objects_.size(); }
    bool contains_data() const { return !objects_.empty(); }

    // Obiekt z jednego rekordu mp (linie jak w pliku, [END] opcjonalnie) - np. ze schowka przy wklejaniu.
    // Wspolrzedne przeliczane projekcja mapy. Brak wyniku, gdy rekord nie jest POI/polilinia/polygonem z danymi.
    std::optional<MapObject> object_from_record(const std::vector<std::string>& lines,
                                                std::vector<std::string>* warnings = nullptr);

    // Dodaje obiekt; jesli nie ma id, dostaje kolejny numer (jak mapData.add_map_object).
    MapObject& add_map_object(MapObject obj);
    void set_map_object_deleted(size_t id, bool deleted = true);

    const std::vector<std::string>& header() const { return header_; }
    // Linie ";@..." z konca pliku. Uwaga: wersja Python je gubila przy zapisie - tu tez nie sa zapisywane (etap 1).
    const std::vector<std::string>& attachments() const { return attachments_; }
    const std::vector<std::string>& warnings() const { return warnings_; }
    const GeoBBox& map_bounding_box() const { return bbox_; }
    int precision() const { return precision_; }
    void set_precision(int p) { precision_ = p; }
    const Projection& projection() const { return *projection_; }
    Projection& projection() { return *projection_; }

private:
    std::unique_ptr<Projection> projection_;
    std::vector<std::string> header_;
    std::vector<std::string> attachments_;
    std::vector<MapObject> objects_;
    std::vector<std::string> warnings_;
    GeoBBox bbox_;
    int precision_ = 0;
};

// Podzial na linie jak readlines() w trybie tekstowym (uniwersalne konce linii: \n, \r\n, \r).
std::vector<std::string_view> split_lines(std::string_view content);

}  // namespace pwm
