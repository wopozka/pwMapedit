// Port map_object_properties.py: wyglad obiektow mapy (ikony POI, kolory i style linii, wypelnienia polygonow).
#pragma once

#include <QBrush>
#include <QColor>
#include <QHash>
#include <QPen>
#include <QPixmap>
#include <QString>
#include <array>
#include <optional>

namespace pwm::gui {

enum class TrailIcon { None, Hiking, Bike };

class MapStyles {
public:
    // icons_dir: katalog z plikami *.xpm i podkatalogiem icons_png.
    explicit MapStyles(const QString& icons_dir);

    // Ikona POI: najpierw xpm, potem png, w ostatecznosci znak zapytania.
    const QPixmap& poi_icon(long long poi_type) const;
    QBrush nonpixmap_poi_brush(long long poi_type) const;

    QColor polyline_colour(long long poly_type) const;
    int polyline_width(long long poly_type) const;
    Qt::PenStyle polyline_dash(long long poly_type) const;
    QPen polyline_pen(long long poly_type) const;
    // Drogi (typy 0x0-0xf i chodnik 0x16, bez promow) i kolej (0x14, 0x10e14, podziemna/rozebrana 0x10e15) - dostaja obwodke, gdy jest wlaczona.
    static bool is_road(long long poly_type);
    static bool is_railway(long long poly_type);
    // Szlaki piesze i rowerowe 0x10e00-0x10e0f - osobna warstwa (View -> Warstwy -> Szlaki). Chodnik 0x16 i droga
    // dla rowerow 0xd to drogi, zostaja w warstwie polilinii.
    static bool is_trail(long long poly_type);
    static bool has_casing(long long poly_type);
    // Obwodka: kolor drogi przyciemniony (kolej: czarny), linia ciagla szersza o 1 piksel z kazdej strony.
    QPen road_casing_pen(long long poly_type) const;
    // Drugie pociagniecie warstwy obwodek, nad wszystkimi obwodkami: tlo pod linia przerywana (kolej - biale).
    std::optional<QPen> casing_base_pen(long long poly_type) const;
    // Ikona wzdluz linii (TrailIconLayer): pieszy - szlaki piesze 0x10e00-0x10e04, 0x10e07 i chodnik 0x16; rower -
    // szlaki rowerowe 0x10e08-0x10e0d i droga dla rowerow 0xd.
    static TrailIcon trail_icon(long long poly_type);
    // Numer typu szlaku 0-13 (-1: bez ikony): przesuniecie ikon wzdluz linii, zeby szlaki roznych kolorow
    // biegnace ta sama droga nie zaslanialy sobie ikon.
    static int trail_icon_slot(long long poly_type);
    // Ikony routingu drog 0x1-0xf (TrailIconLayer): zakaz ruchu - w RouteParam ustawiony ktorys z zakazow
    // No emergency, No delivery, No car/motorcycle, No bus, No taxi, No truck (pozycje 4-8, 11); zakaz pieszych
    // i rowerow - No pedestrian (9), No bicycle (10), wynik to suma BAN_PEDESTRIAN i BAN_BICYCLE (0 - bez zakazu);
    // oplata - Route is toll (pozycja 3).
    static constexpr int BAN_PEDESTRIAN = 1;
    static constexpr int BAN_BICYCLE = 2;
    static bool road_restricted(long long poly_type, const std::optional<std::array<long long, 12>>& routeparam);
    static int road_pedestrian_bicycle_ban(long long poly_type,
                                           const std::optional<std::array<long long, 12>>& routeparam);
    static bool road_toll(long long poly_type, const std::optional<std::array<long long, 12>>& routeparam);

    QColor polygon_fill_colour(long long poly_type) const;
    QPen polygon_pen(long long poly_type) const;
    int polygon_z_value(long long poly_type) const;

    const QString& icons_dir() const { return icons_dir_; }

    // Szuka katalogu icons: zmienna PWMAPEDIT_ICONS, obok programu i wyzej, biezacy katalog, katalog zrodel.
    static QString find_icons_dir();

private:
    void read_icons();

    QString icons_dir_;
    QHash<long long, QPixmap> xpm_icons_;
    QHash<long long, QPixmap> png_icons_;
    QPixmap question_mark_;
    QHash<long long, QColor> polyline_colour_;
    QHash<long long, int> polyline_width_;
    QHash<long long, Qt::PenStyle> polyline_dash_;
    QHash<long long, QColor> polygon_fill_;
    QHash<long long, int> polygon_z_;
};

}  // namespace pwm::gui
