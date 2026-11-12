// Port map_object_properties.py: wyglad obiektow mapy (ikony POI, kolory i style linii, wypelnienia polygonow).
#pragma once

#include <QBrush>
#include <QColor>
#include <QHash>
#include <QPen>
#include <QPixmap>
#include <QString>

namespace pwm::gui {

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
