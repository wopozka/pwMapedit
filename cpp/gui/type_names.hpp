// Nazwy typow obiektow do wyboru w panelu wlasciwosci (icons_names.py, type_aliases.py, line_polygon_names.py).
// Tabele sa w type_names.cpp, generowanym przez tools/gen_type_names.py. Teksty w UTF-8.
#pragma once

#include <vector>

namespace pwm::gui {

struct PoiTypeName {
    long long type;
    const char* category;
    const char* name;
    const char* aliases;  // aliasy rozdzielone '/', wielkimi literami; pusty, gdy brak
};

struct PolyTypeName {
    long long type;
    const char* category;
    const char* name_en;
    const char* name_pl;  // pusty, gdy brak
};

const std::vector<PoiTypeName>& poi_type_names();
const std::vector<PolyTypeName>& line_type_names();
const std::vector<PolyTypeName>& polygon_type_names();

}  // namespace pwm::gui
