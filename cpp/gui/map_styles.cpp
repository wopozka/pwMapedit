#include "map_styles.hpp"

#include <QCoreApplication>
#include <QDebug>
#include <QDir>
#include <QFileInfo>

namespace pwm::gui {

namespace {

// Nazwa pliku ikony: "<typ hex>_<nazwa_en>_<nazwa_pl>_<day|night>.xpm" albo "<typ hex>.png".
bool icon_type_from_file_name(const QString& file_name, long long& type) {
    QString base = QFileInfo(file_name).completeBaseName();
    QString type_str = base.contains('_') ? base.section('_', 0, 0) : base;
    bool ok = false;
    type = type_str.toLongLong(&ok, 16);
    return ok;
}

}  // namespace

MapStyles::MapStyles(const QString& icons_dir) : icons_dir_(icons_dir) {
    read_icons();

    // ---- polilinie: kolor wedlug typu ----
    polyline_colour_ = {
        {0x0, QColor(Qt::black)},
        {0x1, QColor("#0000ff")},    // Motorway
        {0x2, QColor("#cc00ff")},    // Principal Highway
        {0x3, QColor("#bd3020")},    // Principal Highway
        {0x4, QColor("#ff9500")},    // Arterial Road
        {0x5, QColor("#ffff8b")},    // Collector Road
        {0x6, QColor("#404040")},    // Residential street
        {0x7, QColor("#909090")},    // Alleyway
        {0x8, QColor("#ff6500")},    // highway ramp low speed
        {0x9, QColor(Qt::blue)},     // highway ramp high speed
        {0xa, QColor("lightgrey")},  // unpaved road
        {0xb, QColor("#ffff8b")},    // highway connector
        {0xc, QColor("darkorange")}, // rondo
        {0xd, QColor("brown")},      // bike route
        {0xe, QColor("#bd3020")},    // tunel
        {0xf, QColor("lightgrey")},  // unpaved 4x4
        {0x14, QColor(Qt::black)},   // railroad
        {0x15, QColor("#bdca8b")},   // coastline
        {0x16, QColor("#bd6520")},   // walkway
        {0x18, QColor(Qt::blue)},
        {0x19, QColor(Qt::green)},   // timezone
        {0x1a, QColor("#00ffff\"")}, // (jak w Pythonie: bledny zapis koloru -> kolor niepoprawny)
        {0x1c, QColor("gray")},
        {0x1f, QColor(Qt::blue)},    // rzeka
        {0x20, QColor("#AAAA00")},   // elevation minor land contour
        {0x21, QColor("#AAAA00")},   // elevation interm land contour
        {0x22, QColor("#AAAA00")},   // elevation major land contour
        {0x23, QColor("#39caff")},   // elevation minor depth contour
        {0x24, QColor("#39caff")},   // elevation interm depth contour
        {0x25, QColor("#39caff")},   // elevation major depth contour
        {0x26, QColor("#39caff")},   // strumien okresowy
        {0x27, QColor(Qt::blue)},    // airport runway centerline
        {0x28, QColor(Qt::gray)},    // oil or water pipeline
        {0x29, QColor(Qt::black)},   // power line
        {0x2a, QColor(Qt::red)},     // marine boundary
        {0x2b, QColor("#FAA500")},   // marine hazard
        {0x2f, QColor(Qt::blue)},    // znak drogowy
        {0x4b, QColor(Qt::red)},
        {0x10e00, QColor("#ff0000")},   // hiking trial red
        {0x10e01, QColor("#ffff41")},   // hiking trial yellow
        {0x10e02, QColor("#399520")},   // hiking trial green
        {0x10e03, QColor("#3965ff")},   // hiking trial blue
        {0x10e04, QColor(Qt::black)},   // hiking trial czarny
        {0x10e07, QColor("#a959a9\"")}, // hiking trial multicolor (bledny zapis jak w Pythonie)
        {0x10e08, QColor(Qt::red)},     // rowerowy czerwony
        {0x10e09, QColor("#ffff41")},   // rowerowy zolty
        {0x10e0a, QColor("#ffff41")},   // rowerowy zielony
        {0x10e0b, QColor("#3965ff")},   // rowerowy niebieski
        {0x10e0c, QColor(Qt::black)},   // rowerowy czarny
        {0x10e0d, QColor("#a959a9")},   // rowerowy inny
        {0x10e0f, QColor(Qt::black)},   // trial other
        {0x10e10, QColor("#0000ff")},   // tramwaj
        {0x10e11, QColor("#39caff")},   // planowana ulica
        {0x10e12, QColor("#39caff")},   // planowana
        {0x10e13, QColor("#e80020")},   // w budowie
        {0x10e14, QColor(Qt::black)},   // railroad
        {0x10e15, QColor("#a4a4a4")},
    };

    polyline_width_ = {
        {0x1, 5},     {0x2, 5},     {0x3, 4},     {0x4, 3},     {0x5, 3},     {0x6, 3},
        {0x7, 3},     {0x8, 2},     {0x9, 2},     {0xa, 2},     {0xc, 3},     {0xd, 3},
        {0xe, 3},     {0xf, 2},     {0x14, 3},    {0x15, 2},    {0x1f, 3},    {0x25, 3},
        {0x26, 2},    {0x2a, 2},    {0x10e00, 2}, {0x10e01, 2}, {0x10e02, 2}, {0x10e03, 2},
        {0x10e04, 2}, {0x10e07, 2}, {0x10e08, 3}, {0x10e09, 3}, {0x10e0a, 3}, {0x10e0b, 3},
        {0x10e0c, 3}, {0x10e0d, 3}, {0x10e0f, 3}, {0x10e11, 2}, {0x10e12, 3}, {0x10e13, 3},
        {0x10e14, 5}, {0x10e15, 3},
    };

    polyline_dash_ = {
        {0xa, Qt::DotLine},       {0xd, Qt::DotLine},       {0x14, Qt::DashLine},
        {0x1c, Qt::DashDotLine},  {0x16, Qt::DashLine},     {0x18, Qt::DashLine},
        {0x21, Qt::DotLine},      {0x22, Qt::DashLine},     {0x23, Qt::DashLine},
        {0x28, Qt::DotLine},      {0x2a, Qt::DashLine},     {0x2b, Qt::DashLine},
        {0x4b, Qt::DashLine},     {0x10e00, Qt::DashLine},  {0x10e01, Qt::DashLine},
        {0x10e02, Qt::DashLine},  {0x10e03, Qt::DashLine},  {0x10e04, Qt::DashLine},
        {0x10e07, Qt::DashLine},  {0x10e08, Qt::DotLine},   {0x10e09, Qt::DotLine},
        {0x10e0a, Qt::DotLine},   {0x10e0b, Qt::DotLine},   {0x10e0c, Qt::DotLine},
        {0x10e0d, Qt::DotLine},   {0x10e0f, Qt::DotLine},   {0x10e11, Qt::DashLine},
        {0x10e12, Qt::DashLine},  {0x10e13, Qt::DashLine},  {0x10e14, Qt::DashLine},
        {0x10e15, Qt::DashLine},
    };

    // ---- polygony ----
    polygon_fill_ = {
        {0x1, QColor("#d5d5d5")},  {0x2, QColor("#e6e6e6")},  {0x3, QColor("#ac9d93")},
        {0x4, QColor("#bdca6a")},  {0x5, QColor("#d5d5d5")},  {0x6, QColor("#ce9a00")},
        {0x7, QColor("#ffba84")},  {0x8, QColor("#bdcab4")},  {0x9, QColor("#ffba84")},
        {0xa, QColor("#ffcab4")},  {0xb, QColor("#dd858a")},  {0xc, QColor("#dddddd")},
        {0xd, QColor("#ff9955")},  {0xe, QColor("#e7e3e7")},  {0x13, QColor("#bd656a")},
        {0x14, QColor("#7bff00")}, {0x15, QColor("#7bff00")}, {0x16, QColor(Qt::green)},
        {0x17, QColor("#39ff00")}, {0x18, QColor("#39ca20")}, {0x19, QColor("#ffba84")},
        {0x1a, QColor("#C5C5C5")}, {0x28, QColor(Qt::blue)},  {0x29, QColor(Qt::blue)},
        {0x32, QColor("#3995ff")}, {0x3b, QColor("#3995ff")}, {0x3c, QColor("#3995ff")},
        {0x3d, QColor("#3995ff")}, {0x3e, QColor("#3995ff")}, {0x3f, QColor("#3995ff")},
        {0x40, QColor("#3995ff")}, {0x41, QColor("#3995ff")}, {0x42, QColor("#3995ff")},
        {0x43, QColor("#3995ff")}, {0x44, QColor("#3995ff")}, {0x45, QColor("#3995ff")},
        {0x46, QColor("#3995ff")}, {0x47, QColor("#3995ff")}, {0x48, QColor("#3995ff")},
        {0x49, QColor("#3995ff")}, {0x4b, QColor("#ffffff")}, {0x4c, QColor("#aeecb8")},
        {0x4d, QColor("#88ffff")}, {0x4e, QColor("#39ff00")}, {0x4f, QColor("#00CA00")},
        {0x50, QColor("#ee0000")}, {0x51, QColor("#a9e6ec")}, {0x53, QColor("#ffffd5")},
        {0x01101e, QColor("#3995ff")}, {0x01101f, QColor("#3995ff")},
    };

    polygon_z_ = {
        {0x1, 1},  {0x2, 1},  {0x3, 1},  {0x4, 1},  {0x5, 1},  {0x6, 1},  {0x7, 1},  {0x8, 3},
        {0x9, 1},  {0xa, 2},  {0xb, 2},  {0xc, 2},  {0xd, 2},  {0xe, 2},  {0x13, 2}, {0x14, 2},
        {0x15, 2}, {0x16, 2}, {0x17, 3}, {0x18, 3}, {0x19, 3}, {0x1a, 4}, {0x1e, 2}, {0x1f, 2},
        {0x20, 2}, {0x28, 1}, {0x29, 1}, {0x32, 1}, {0x3b, 1}, {0x3c, 8}, {0x3d, 8}, {0x3e, 8},
        {0x3f, 8}, {0x40, 8}, {0x41, 8}, {0x42, 8}, {0x43, 8}, {0x44, 4}, {0x45, 2}, {0x46, 2},
        {0x47, 2}, {0x48, 3}, {0x49, 4}, {0x4c, 5}, {0x4d, 5}, {0x4e, 5}, {0x4f, 5}, {0x50, 3},
        {0x51, 6}, {0x52, 4}, {0x53, 5},
    };
}

void MapStyles::read_icons() {
    QDir dir(icons_dir_);
    // Dla kilku typow sa ikony _day i _night. W Pythonie wygrywala ta, ktora glob zwrocil pozniej
    // (zalezne od systemu plikow); tu zawsze wygrywa _day.
    const QStringList xpms = dir.entryList({"*.xpm"}, QDir::Files, QDir::Name);
    for (const QString& name : xpms) {
        QString path = dir.filePath(name);
        if (name.contains("question_mark")) {
            question_mark_ = QPixmap(path);
            continue;
        }
        long long type = 0;
        if (!icon_type_from_file_name(name, type)) continue;
        if (xpm_icons_.contains(type) && !name.contains("_day")) continue;
        QPixmap pm(path);
        if (pm.isNull()) qWarning() << "Problem z odczytaniem pliku ikony:" << path;
        xpm_icons_.insert(type, pm);
    }
    QDir png_dir(dir.filePath("icons_png"));
    const QStringList pngs = png_dir.entryList({"*.png"}, QDir::Files, QDir::Name);
    for (const QString& name : pngs) {
        long long type = 0;
        if (!icon_type_from_file_name(name, type)) continue;
        QPixmap pm(png_dir.filePath(name));
        if (pm.isNull()) qWarning() << "Problem z odczytaniem pliku ikony:" << png_dir.filePath(name);
        png_icons_.insert(type, pm);
    }
    if (question_mark_.isNull()) {
        // brak pliku z ikona - rysujemy wlasny znak zapytania
        question_mark_ = QPixmap(16, 16);
        question_mark_.fill(Qt::transparent);
    }
}

const QPixmap& MapStyles::poi_icon(long long poi_type) const {
    auto it = xpm_icons_.constFind(poi_type);
    if (it != xpm_icons_.constEnd()) return *it;
    it = png_icons_.constFind(poi_type);
    if (it != png_icons_.constEnd()) return *it;
    return question_mark_;
}

QBrush MapStyles::nonpixmap_poi_brush(long long poi_type) const {
    switch (poi_type) {
        case 0x100: case 0x300: case 0x500: case 0x600: case 0x700: case 0xa00: case 0xb00:
        case 0xd00: case 0xe00: case 0xf00: case 0x2800:
            return QBrush(Qt::black);
        default:
            return QBrush(Qt::red);
    }
}

QColor MapStyles::polyline_colour(long long poly_type) const {
    return polyline_colour_.value(poly_type, QColor(Qt::black));
}

int MapStyles::polyline_width(long long poly_type) const {
    return polyline_width_.value(poly_type, 1);
}

Qt::PenStyle MapStyles::polyline_dash(long long poly_type) const {
    return polyline_dash_.value(poly_type, Qt::SolidLine);
}

QPen MapStyles::polyline_pen(long long poly_type) const {
    QPen pen;
    pen.setWidth(polyline_width(poly_type));
    pen.setBrush(polyline_colour(poly_type));
    pen.setStyle(polyline_dash(poly_type));
    pen.setCosmetic(true);
    return pen;
}

QColor MapStyles::polygon_fill_colour(long long poly_type) const {
    return polygon_fill_.value(poly_type, QColor("gainsboro"));
}

QPen MapStyles::polygon_pen(long long poly_type) const {
    QPen pen;
    pen.setBrush(polygon_fill_colour(poly_type));
    return pen;
}

int MapStyles::polygon_z_value(long long poly_type) const {
    return polygon_z_.value(poly_type, 0);
}

QString MapStyles::find_icons_dir() {
    auto looks_ok = [](const QString& d) { return !d.isEmpty() && QFileInfo(d + "/question_mark.xpm").exists(); };
    QString env = qEnvironmentVariable("PWMAPEDIT_ICONS");
    if (looks_ok(env)) return env;
    QDir app_dir(QCoreApplication::applicationDirPath());
    for (int up = 0; up < 4; ++up) {
        if (looks_ok(app_dir.filePath("icons"))) return app_dir.filePath("icons");
        if (!app_dir.cdUp()) break;
    }
    if (looks_ok(QDir::current().filePath("icons"))) return QDir::current().filePath("icons");
#ifdef PWM_SOURCE_ICONS_DIR
    if (looks_ok(PWM_SOURCE_ICONS_DIR)) return QStringLiteral(PWM_SOURCE_ICONS_DIR);
#endif
    return QString();
}

}  // namespace pwm::gui
