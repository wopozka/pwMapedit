// Wczytane slady GPS (GPX) jako podklad do rysowania: elementy na scenie, przyciaganie, zamiana na obiekty mapy.
//
// Slady nie sa czescia mapy i nie sa zapisywane. Leza nad kafelkami WWW, a pod obiektami mapy, nie reaguja na mysz.
// Wezly przyciagaja sie do ich punktow (Ctrl), a slad mozna zamienic na polilinie, waypoint na POI (komendy undo).
#pragma once

#include <QColor>
#include <QGraphicsPathItem>
#include <QObject>
#include <QString>
#include <vector>

#include "gps_data.hpp"
#include "map_items.hpp"

namespace pwm::gui {

class MapScene;

// Czesc sladu (jeden trkseg) na scenie; przy powiekszeniu rysuje tez punkty GPS.
class GpsTrackItem : public QGraphicsPathItem, public SnapSource {
public:
    GpsTrackItem(const QPolygonF& points, const QColor& color);
    int type() const override { return GpsTrackItemType; }
    void snap_points(std::vector<QPointF>& out) const override;
    void set_used(bool used);
    void paint(QPainter* painter, const QStyleOptionGraphicsItem* option, QWidget* widget) override;

private:
    QPolygonF points_;
    QColor color_;
};

// Waypoint: romb o stalej wielkosci na ekranie z nazwa obok.
class GpsWaypointItem : public QGraphicsPathItem, public SnapSource {
public:
    GpsWaypointItem(const QPointF& pos, const QString& name, const QColor& color);
    int type() const override { return GpsWaypointItemType; }
    void snap_points(std::vector<QPointF>& out) const override { out.push_back(pos()); }
    void set_used(bool used);

private:
    QColor color_;
};

struct GpsFileEntry {
    gps::File data;
    QColor color;
    bool visible = true;
    // elementy na scenie: [slad][czesc] i [waypoint]; puste, gdy nie ma mapy (brak projekcji)
    std::vector<std::vector<GpsTrackItem*>> track_items;
    std::vector<GpsWaypointItem*> waypoint_items;
    // wykorzystane do utworzenia obiektow (szare) - tylko w tej sesji
    std::vector<std::vector<bool>> used_segments;
    std::vector<bool> used_waypoints;
};

class GpsLayers : public QObject {
    Q_OBJECT
public:
    explicit GpsLayers(MapScene* scene, QObject* parent = nullptr);
    ~GpsLayers() override;

    // Wczytuje plik GPX albo GDB (wymaga otwartej mapy - projekcja); zwraca opis bledu albo pusty napis.
    // warning: ostrzezenie przy udanym wczytaniu (np. pominiete punkty).
    QString load_file(const QString& path, QString* warning = nullptr);
    void add_file(gps::File file);
    void remove_file(int index);
    void set_visible(int index, bool visible);

    int file_count() const { return static_cast<int>(files_.size()); }
    const GpsFileEntry& file(int index) const { return files_[static_cast<size_t>(index)]; }

    // Przed wyczyszczeniem sceny (nowa mapa) i po wczytaniu mapy (inna projekcja) - dane zostaja.
    void clear_items();
    void rebuild_items();

    // Czesc sladu (segment < 0: wszystkie czesci) jako polilinie z ostatnio uzytym typem, po uproszczeniu
    // (tolerancja w metrach). Jedna komenda undo. Zwraca liczbe utworzonych polilinii.
    int create_polylines(int file, int track, int segment, double tolerance_m);
    // Waypointy jako POI (Label = nazwa, komentarz = opis). Jedna komenda undo. Zwraca liczbe POI.
    int create_pois(int file, const std::vector<int>& waypoints);

    QPainterPath segment_path(int file, int track, int segment) const;
    std::optional<QPointF> waypoint_position(int file, int waypoint) const;
    // Pierwszy punkt pliku (sladu albo waypoint) na scenie - do pokazania wczytanego pliku.
    std::optional<QPointF> first_point(int file) const;

signals:
    void files_changed();

private:
    void build_items(GpsFileEntry& entry);
    void delete_items(GpsFileEntry& entry);
    std::optional<QPointF> to_scene(const gps::Point& p) const;

    MapScene* scene_;
    std::vector<GpsFileEntry> files_;
    int next_color_ = 0;
};

}  // namespace pwm::gui
