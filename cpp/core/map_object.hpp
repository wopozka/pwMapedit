// Port czesci danych z BasicMapItem (map_items.py) oraz misc_functions.map_strings_record_to_dict_record.
// Klasy graficzne (QGraphicsItem) beda w etapie GUI; tu tylko dane i zapis do formatu mp.
#pragma once

#include <array>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

#include "data_x.hpp"

namespace pwm {

enum class ObjectKind { Basic, Poi, Polyline, Polygon };

const char* object_kind_section(ObjectKind kind);  // "[POI]" itd., "" dla Basic

struct RecordField {
    std::string_view key;
    std::string_view value;
};

// Wynik map_strings_record_to_dict_record.
struct ParsedRecord {
    // Pierwszy element poi_poly_type: znacznik sekcji ("[POI]"...) albo wartosc Type= (gdy wystapila wczesniej).
    enum class Head { None, Section, TypeValue } head = Head::None;
    std::string_view section;
    std::vector<std::string_view> comments;  // bez poczatkowego ';'
    std::vector<RecordField> fields;         // w kolejnosci z pliku, klucze moga sie powtarzac
    std::vector<std::string_view> unknown_lines;
    bool type_parse_error = false;  // Type= nie dalo sie sparsowac (Python: ValueError)
};

ParsedRecord parse_record(const std::vector<std::string_view>& lines);

bool is_map_object_type(std::string_view stripped_line);  // [POI] [POLYGON] [POLYLINE]
bool is_any_map_object(std::string_view stripped_line);   // + [RESTRICT] [SIGN]

class MapObject {
public:
    MapObject(ObjectKind kind, const Projection* projection) : kind_(kind), projection_(projection) {}

    // Ustawia wlasciwosci z rekordu pliku. Bledy pojedynczych linii (tam, gdzie Python przerwalby
    // wczytywanie wyjatkiem) trafiaja do warnings, a linia jest pomijana.
    // max_precision - aktualizowana precyzja wspolrzednych (odpowiednik Data_X.precision).
    void set_data(const std::vector<std::string_view>& comments, const std::vector<RecordField>& fields,
                  int& max_precision, std::vector<std::string>& warnings);

    std::vector<std::string> to_mp_record(int precision) const;

    ObjectKind kind() const { return kind_; }
    // Zmiana rodzaju (zamiana polygon <-> polilinia); pola nieobslugiwane przez nowy rodzaj czysci wywolujacy.
    void set_kind(ObjectKind kind) { kind_ = kind; }
    const Projection* projection() const { return projection_; }

    std::optional<size_t> id;
    bool deleted = false;
    std::optional<std::vector<std::string>> comment;
    std::optional<long long> type;
    std::optional<std::string> label1, label2, label3;
    bool dirindicator = false;
    long long endlevel = 0;
    std::optional<std::string> streetdesc, housenumber, phone;
    std::optional<std::string> cityname, countryname, regionname, countrycode, zipcode, districtname;
    std::optional<long long> roadid;
    std::optional<std::array<long long, 12>> routeparam;
    std::vector<std::pair<std::string, std::string>> others;
    std::optional<DataX> data;
    GeoBBox bbox;

    void set_route_params(const std::vector<std::string_view>& values);
    void set_dirindicator(std::string_view value) { dirindicator = value != "0"; }

private:
    void set_datax(std::string_view key, std::string_view value, int& max_precision);
    void set_hlevels(std::string_view hlevel_items);

    ObjectKind kind_;
    const Projection* projection_;
};

}  // namespace pwm
