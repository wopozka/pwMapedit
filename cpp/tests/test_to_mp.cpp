// Port tests/test_to_mp.py. Dane testowe generowane z oryginalu (py_cases.inc).
#include <algorithm>

#include "../core/map_data.hpp"
#include "../core/map_object.hpp"
#include "../core/projection.hpp"
#include "py_cases.inc"
#include "test_framework.hpp"

using namespace pwm;

TEST(get_mp_coords) {
    MercatorProjection p;
    PointF c = p.geo_to_canvas(12.23456, 12.23456);
    Node n(c.x, c.y);
    CHECK_EQ(n.mp_coords(p, 5), std::string("(12.23456,12.23456)"));
    CHECK_EQ(n.mp_coords(p, 6), std::string("(12.234560,12.234560)"));
}

// W Pythonie precyzja byla globalna (Data_X.precision), wiec wynik zalezal od kolejnosci testow -
// 4 przypadki nie przechodzily w pelnym przebiegu pytest. Tu precyzja jest liczona dla kazdego przypadku.
TEST(data_to_mp_record) {
    MercatorProjection p;
    for (const auto& c : DATA_TO_MP_CASES) {
        DataX d(&p);
        int precision = 0;
        for (const auto& line : c.target) {
            size_t eq = line.find('=');
            if (line.rfind("Data", 0) == 0) {
                precision = std::max(precision, d.add_nodes_from_string(line.substr(0, eq), line.substr(eq + 1)));
            } else if (line.rfind("Numbers", 0) == 0) {
                d.add_housenumbers_from_string(line);
            } else if (line.rfind("HLevel", 0) == 0) {
                d.add_hlevels_from_string(line);
            }
        }
        CHECK_EQ(d.to_mp_record(precision), c.answer);
    }
}

TEST(obj_to_mp_record) {
    MercatorProjection p;
    for (const auto& c : OBJ_TO_MP_CASES) {
        std::vector<std::string_view> lines(c.target.begin(), c.target.end());
        ParsedRecord rec = parse_record(lines);
        MapObject obj(ObjectKind::Basic, &p);
        int precision = 0;
        std::vector<std::string> warnings;
        obj.set_data(rec.comments, rec.fields, precision, warnings);
        CHECK(warnings.empty());
        CHECK_EQ(obj.to_mp_record(precision), c.answer);
    }
}

// ---- testy dodatkowe: wczytywanie i zapis calego pliku ----

namespace {
const char* SAMPLE =
    "[IMG ID]\r\n"
    "Name=test\r\n"
    "[END-IMG ID]\r\n"
    "\r\n"
    ";komentarz obiektu\r\n"
    "[POI]\r\n"
    "Type=0x2f00\r\n"
    "Label=Sklep\xa0\r\n"  // NBSP (cp1250 0xA0) na koncu - Python strip() go usuwa
    "Data0=(52.10000,21.00000)\r\n"
    "Miasto=Warszawa\r\n"
    "[END]\r\n"
    "\r\n"
    "[RESTRICT]\r\n"
    "Nod=1\r\n"
    "[END]\r\n"
    "\r\n"
    "[POLYLINE]\r\n"
    "Type=0x6\r\n"
    "Data0=(52.10000,21.00000),(52.10100,21.00100),(52.10200,21.00200)\r\n"
    "Numbers1=0,O,1,5,N,-1,-1\r\n"
    "Nod1=0,123,0\r\n"
    "RoadID=77\r\n"
    "[END]\r\n"
    "\r\n"
    ";@File plik.txt\r\n";
}

TEST(load_save_sample) {
    MapData m;
    LoadStats st = m.load_from_string(SAMPLE);
    CHECK_EQ(m.records_number(), size_t{2});
    CHECK_EQ(st.skipped_records, size_t{1});
    CHECK_EQ(m.header(), (std::vector<std::string>{"[IMG ID]", "Name=test", "[END-IMG ID]", ""}));
    CHECK_EQ(m.attachments(), (std::vector<std::string>{";@File plik.txt"}));
    CHECK_EQ(m.precision(), 5);
    const MapObject& poi = m.objects()[0];
    CHECK(poi.kind() == ObjectKind::Poi);
    CHECK(poi.comment == std::optional<std::vector<std::string>>(std::vector<std::string>{"komentarz obiektu"}));
    CHECK(poi.label1 == std::optional<std::string>("Sklep"));
    CHECK(m.objects()[1].roadid == std::optional<long long>(77));
    const std::string expected =
        "[IMG ID]\n"
        "Name=test\n"
        "[END-IMG ID]\n"
        "\n"
        ";komentarz obiektu\n"
        "[POI]\n"
        "Type=0x2f00\n"
        "Label=Sklep\n"
        "Data0=(52.10000,21.00000)\n"
        "Miasto=Warszawa\n"
        "[END]\n"
        "\n"
        "[POLYLINE]\n"
        "Type=0x6\n"
        "Data0=(52.10000,21.00000),(52.10100,21.00100),(52.10200,21.00200)\n"
        "Numbers1=0,O,1,5,N,-1,-1\n"
        "[END]\n"
        "\n";
    CHECK_EQ(m.to_mp_string(), expected);
}

TEST(load_without_header_and_objects) {
    MapData m;
    m.load_from_string("[POI]\nType=0x1\nData0=(1.0,2.0)\n[END]\n");
    CHECK_EQ(m.records_number(), size_t{1});
    CHECK(m.header().empty());
    MapData empty;
    empty.load_from_string("[IMG ID]\nName=x\n[END-IMG ID]\n");
    CHECK_EQ(empty.records_number(), size_t{0});
    CHECK_EQ(empty.warnings().size(), size_t{1});
}

TEST(deleted_objects_not_saved) {
    MapData m;
    m.load_from_string("[POI]\nType=0x1\nData0=(1.0,2.0)\n[END]\n\n[POI]\nType=0x2\nData0=(1.0,2.0)\n[END]\n");
    m.set_map_object_deleted(0);
    CHECK_EQ(m.to_mp_string(), std::string("[POI]\nType=0x2\nData0=(1.0,2.0)\n[END]\n\n"));
}

TEST(warnings_instead_of_crash) {
    MapData m;
    m.load_from_string("[POLYLINE]\nType=0x1\nNumbers1=0,O,1,5,N,-1,-1\nData0=(1.0,2.0),(1.1,2.1)\nEndLevel=x\n[END]\n");
    CHECK_EQ(m.records_number(), size_t{1});
    CHECK_EQ(m.warnings().size(), size_t{2});  // Numbers przed Data, EndLevel nie-liczba
}

TEST(object_from_record_roundtrip) {
    pwm::MapData map;
    map.load_from_string("[IMG ID]\nName=x\n[END-IMG ID]\n\n[POLYLINE]\nType=0x6\nLabel=Ulica\n"
                         "Data0=(52.10000,21.00000),(52.10100,21.00100)\n[END]\n\n");
    const auto record = map.objects()[0].to_mp_record(map.precision());
    auto obj = map.object_from_record(record);
    CHECK(obj.has_value());
    CHECK(obj->kind() == pwm::ObjectKind::Polyline);
    CHECK(obj->to_mp_record(map.precision()) == record);
    std::vector<std::string> with_end = record;
    with_end.push_back("[END]");
    CHECK(map.object_from_record(with_end).has_value());
    CHECK(!map.object_from_record({"[RESTRICT]", "Nod=1"}).has_value());
    CHECK(!map.object_from_record({"[POI]", "Type=0x2f00"}).has_value());  // bez wspolrzednych
}
