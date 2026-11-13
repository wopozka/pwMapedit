#include "gps_layers.hpp"

#include <QFile>
#include <QFileInfo>
#include <QGraphicsSimpleTextItem>
#include <QPainter>
#include <QUndoStack>
#include <algorithm>

#include "gdb_reader.hpp"
#include "gpx_reader.hpp"
#include "map_scene.hpp"
#include "misc.hpp"

namespace pwm::gui {

namespace {

// Kolory kolejnych plikow - jaskrawe, spoza palety obiektow mapy.
const QColor FILE_COLORS[] = {QColor(255, 0, 255), QColor(255, 128, 0), QColor(0, 200, 255), QColor(120, 220, 0),
                              QColor(255, 40, 40),  QColor(140, 70, 255), QColor(0, 160, 120)};
const QColor USED_COLOR(150, 150, 150);

// Slady nad kafelkami WWW (-1000), pod obiektami mapy.
constexpr double GPS_TRACK_Z = -500;
constexpr double GPS_WAYPOINT_Z = -400;
// Punkty GPS na sladzie widac od tej skali widoku.
constexpr double GPS_POINTS_SCALE = 0.5;

double viewer_scale_of(const QGraphicsItem* item) {
    auto* s = item->scene() ? qobject_cast<MapScene*>(item->scene()) : nullptr;
    return s ? s->viewer_scale() : 1.0;
}

}  // namespace

// ================================================================ elementy
GpsTrackItem::GpsTrackItem(const QPolygonF& points, const QColor& color) : points_(points), color_(color) {
    QPainterPath path;
    path.addPolygon(points);
    setPath(path);
    set_used(false);
    setZValue(GPS_TRACK_Z);
    setAcceptedMouseButtons(Qt::NoButton);
}

void GpsTrackItem::set_used(bool used) {
    QPen pen(used ? USED_COLOR : color_, 2);
    pen.setCosmetic(true);  // 2 piksele niezaleznie od skali
    setPen(pen);
    setOpacity(used ? 0.6 : 0.85);
}

void GpsTrackItem::snap_points(std::vector<QPointF>& out) const { out.insert(out.end(), points_.begin(), points_.end()); }

void GpsTrackItem::paint(QPainter* painter, const QStyleOptionGraphicsItem* option, QWidget* widget) {
    QGraphicsPathItem::paint(painter, option, widget);
    if (viewer_scale_of(this) < GPS_POINTS_SCALE) return;
    QPen dots(pen().color(), 5, Qt::SolidLine, Qt::RoundCap);
    dots.setCosmetic(true);
    painter->setPen(dots);
    painter->drawPoints(points_);
}

GpsWaypointItem::GpsWaypointItem(const QPointF& pos, const QString& name, const QColor& color) : color_(color) {
    QPainterPath diamond;
    diamond.moveTo(0, -7);
    diamond.lineTo(6, 0);
    diamond.lineTo(0, 7);
    diamond.lineTo(-6, 0);
    diamond.closeSubpath();
    setPath(diamond);
    setPen(QPen(Qt::black, 1));
    setPos(pos);
    setFlag(QGraphicsItem::ItemIgnoresTransformations, true);
    setZValue(GPS_WAYPOINT_Z);
    setAcceptedMouseButtons(Qt::NoButton);
    if (!name.isEmpty()) {
        auto* label = new QGraphicsSimpleTextItem(name, this);
        label->setPos(8, -8);
        label->setBrush(QBrush(Qt::black));
    }
    set_used(false);
}

void GpsWaypointItem::set_used(bool used) { setBrush(QBrush(used ? USED_COLOR : color_)); }

// ================================================================ GpsLayers
GpsLayers::GpsLayers(MapScene* scene, QObject* parent) : QObject(parent), scene_(scene) {}

GpsLayers::~GpsLayers() = default;  // elementy naleza do sceny; przed jej wyczyszczeniem wolane jest clear_items()

std::optional<QPointF> GpsLayers::to_scene(const gps::Point& p) const {
    if (!scene_->map()) return std::nullopt;
    const PointF c = scene_->map()->projection().geo_to_canvas(p.lat, p.lon);
    return QPointF(c.x, c.y);
}

QString GpsLayers::load_file(const QString& path, QString* warning) {
    if (!scene_->map()) return tr("Najpierw otwórz mapę - ślady są rysowane w jej układzie współrzędnych.");
    const QString suffix = QFileInfo(path).suffix().toLower();
    QString message;
    std::optional<gps::File> file;
    if (suffix == QLatin1String("gdb")) {
        // GDB (Garmin MapSource/BaseCamp) - czytnik w rdzeniu; plik czytany przez QFile (polskie nazwy na Windows)
        QFile f(path);
        if (!f.open(QIODevice::ReadOnly)) return tr("Nie można otworzyć pliku: %1").arg(f.errorString());
        const QByteArray data = f.readAll();
        gps::GdbResult r = gps::read_gdb(std::string_view(data.constData(), static_cast<size_t>(data.size())));
        if (!r.ok) return QString::fromStdString(r.error);
        QStringList warnings;
        for (const std::string& w : r.warnings) warnings << QString::fromStdString(w);
        message = warnings.join("; ");
        r.file.path = path.toStdString();
        file = std::move(r.file);
    } else {
        file = read_gpx_file(path, &message);
        if (!file) return message;
    }
    if (file->waypoints.empty() && file->tracks.empty()) return tr("Plik nie zawiera śladów ani punktów.");
    if (warning) *warning = message;
    add_file(std::move(*file));
    return {};
}

void GpsLayers::add_file(gps::File file) {
    GpsFileEntry entry;
    entry.data = std::move(file);
    entry.color = FILE_COLORS[next_color_++ % (sizeof(FILE_COLORS) / sizeof(FILE_COLORS[0]))];
    for (const gps::Track& t : entry.data.tracks) entry.used_segments.emplace_back(t.segments.size(), false);
    entry.used_waypoints.assign(entry.data.waypoints.size(), false);
    files_.push_back(std::move(entry));
    build_items(files_.back());
    emit files_changed();
}

void GpsLayers::remove_file(int index) {
    if (index < 0 || index >= file_count()) return;
    delete_items(files_[static_cast<size_t>(index)]);
    files_.erase(files_.begin() + index);
    emit files_changed();
}

void GpsLayers::set_visible(int index, bool visible) {
    if (index < 0 || index >= file_count()) return;
    GpsFileEntry& e = files_[static_cast<size_t>(index)];
    e.visible = visible;
    for (auto& segs : e.track_items)
        for (GpsTrackItem* item : segs) item->setVisible(visible);
    for (GpsWaypointItem* item : e.waypoint_items) item->setVisible(visible);
}

void GpsLayers::clear_items() {
    for (GpsFileEntry& e : files_) delete_items(e);
}

void GpsLayers::rebuild_items() {
    for (GpsFileEntry& e : files_) {
        delete_items(e);
        build_items(e);
    }
}

void GpsLayers::delete_items(GpsFileEntry& e) {
    for (auto& segs : e.track_items)
        for (GpsTrackItem* item : segs) delete item;
    for (GpsWaypointItem* item : e.waypoint_items) delete item;
    e.track_items.clear();
    e.waypoint_items.clear();
}

void GpsLayers::build_items(GpsFileEntry& e) {
    if (!scene_->map()) return;
    for (size_t t = 0; t < e.data.tracks.size(); ++t) {
        e.track_items.emplace_back();
        for (size_t s = 0; s < e.data.tracks[t].segments.size(); ++s) {
            QPolygonF poly;
            for (const gps::Point& p : e.data.tracks[t].segments[s])
                if (auto q = to_scene(p)) poly.append(*q);
            auto* item = new GpsTrackItem(poly, e.color);
            item->set_used(e.used_segments[t][s]);
            item->setVisible(e.visible);
            scene_->addItem(item);
            e.track_items.back().push_back(item);
        }
    }
    for (size_t w = 0; w < e.data.waypoints.size(); ++w) {
        const gps::Waypoint& wpt = e.data.waypoints[w];
        auto pos = to_scene(wpt.pos);
        if (!pos) continue;
        auto* item = new GpsWaypointItem(*pos, QString::fromStdString(wpt.name), e.color);
        item->set_used(e.used_waypoints[w]);
        item->setVisible(e.visible);
        scene_->addItem(item);
        e.waypoint_items.push_back(item);
    }
    // Prostokat sceny obejmuje tylko mape - bez rozszerzenia slady lezace dalej bylyby poza zasiegiem przewijania.
    QRectF bounds;
    for (const auto& segs : e.track_items)
        for (const GpsTrackItem* item : segs) bounds |= item->sceneBoundingRect();
    for (const GpsWaypointItem* item : e.waypoint_items) bounds |= QRectF(item->pos(), QSizeF(1, 1));
    if (!bounds.isEmpty()) {
        const double margin = std::max(bounds.width(), bounds.height()) * 0.05 + 100;
        scene_->setSceneRect(scene_->sceneRect().united(bounds.adjusted(-margin, -margin, margin, margin)));
    }
}

QPainterPath GpsLayers::segment_path(int file, int track, int segment) const {
    QPainterPath path;
    if (file < 0 || file >= file_count()) return path;
    const auto& tracks = files_[static_cast<size_t>(file)].data.tracks;
    if (track < 0 || track >= static_cast<int>(tracks.size())) return path;
    const auto& segments = tracks[static_cast<size_t>(track)].segments;
    for (int s = 0; s < static_cast<int>(segments.size()); ++s) {
        if (segment >= 0 && s != segment) continue;
        QPolygonF poly;
        for (const gps::Point& p : segments[static_cast<size_t>(s)])
            if (auto q = to_scene(p)) poly.append(*q);
        path.addPolygon(poly);
    }
    return path;
}

std::optional<QPointF> GpsLayers::first_point(int file) const {
    if (file < 0 || file >= file_count()) return std::nullopt;
    const gps::File& f = files_[static_cast<size_t>(file)].data;
    for (const gps::Track& t : f.tracks)
        for (const auto& seg : t.segments)
            if (!seg.empty()) return to_scene(seg.front());
    if (!f.waypoints.empty()) return to_scene(f.waypoints.front().pos);
    return std::nullopt;
}

std::optional<QPointF> GpsLayers::waypoint_position(int file, int waypoint) const {
    if (file < 0 || file >= file_count()) return std::nullopt;
    const auto& wpts = files_[static_cast<size_t>(file)].data.waypoints;
    if (waypoint < 0 || waypoint >= static_cast<int>(wpts.size())) return std::nullopt;
    return to_scene(wpts[static_cast<size_t>(waypoint)].pos);
}

int GpsLayers::create_polylines(int file, int track, int segment, double tolerance_m) {
    if (file < 0 || file >= file_count() || !scene_->map()) return 0;
    GpsFileEntry& e = files_[static_cast<size_t>(file)];
    if (track < 0 || track >= static_cast<int>(e.data.tracks.size())) return 0;
    const auto& segments = e.data.tracks[static_cast<size_t>(track)].segments;
    QUndoStack* stack = scene_->undo_stack();
    int created = 0;
    if (stack) stack->beginMacro(tr("Utwórz polilinię ze śladu"));
    for (int s = 0; s < static_cast<int>(segments.size()); ++s) {
        if (segment >= 0 && s != segment) continue;
        const auto& points = segments[static_cast<size_t>(s)];
        std::vector<QPointF> nodes;
        for (size_t i : gps::simplify(points, tolerance_m))
            if (auto q = to_scene(points[i])) nodes.push_back(*q);
        if (nodes.size() < 2) continue;
        if (scene_->create_object(ObjectKind::Polyline, nodes)) {
            ++created;
            e.used_segments[static_cast<size_t>(track)][static_cast<size_t>(s)] = true;
            if (track < static_cast<int>(e.track_items.size()) && s < static_cast<int>(e.track_items[track].size()))
                e.track_items[track][s]->set_used(true);
        }
    }
    if (stack) stack->endMacro();
    emit files_changed();
    return created;
}

int GpsLayers::create_pois(int file, const std::vector<int>& waypoints) {
    if (file < 0 || file >= file_count() || !scene_->map()) return 0;
    GpsFileEntry& e = files_[static_cast<size_t>(file)];
    QUndoStack* stack = scene_->undo_stack();
    int created = 0;
    if (stack) stack->beginMacro(waypoints.size() == 1 ? tr("Utwórz POI z waypointu") : tr("Utwórz POI z waypointów"));
    for (int w : waypoints) {
        if (w < 0 || w >= static_cast<int>(e.data.waypoints.size())) continue;
        const gps::Waypoint& wpt = e.data.waypoints[static_cast<size_t>(w)];
        auto pos = to_scene(wpt.pos);
        if (!pos) continue;
        // tekst obiektu mapy w cp1250, jak w pliku mp
        std::vector<std::string> fields;
        if (!wpt.name.empty()) fields.push_back("Label=" + encoding::utf8_to_cp1250(wpt.name));
        std::vector<std::string> comments;
        if (!wpt.comment.empty())
            for (const QString& line : QString::fromStdString(wpt.comment).split('\n'))
                if (!line.trimmed().isEmpty()) comments.push_back(encoding::utf8_to_cp1250(line.trimmed().toStdString()));
        if (scene_->create_object(ObjectKind::Poi, {*pos}, fields, comments)) {
            ++created;
            e.used_waypoints[static_cast<size_t>(w)] = true;
            for (GpsWaypointItem* item : e.waypoint_items)
                if (item->pos() == *pos) item->set_used(true);
        }
    }
    if (stack) stack->endMacro();
    emit files_changed();
    return created;
}

}  // namespace pwm::gui
