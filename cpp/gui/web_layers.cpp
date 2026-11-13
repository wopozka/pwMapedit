#include "web_layers.hpp"

#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QGraphicsPixmapItem>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QNetworkRequest>
#include <QStandardPaths>

#include "map_items.hpp"
#include "map_scene.hpp"
#include "map_view.hpp"

namespace pwm::gui {

namespace {
// Kafelki pod wszystkimi obiektami mapy.
constexpr double WEB_LAYER_Z_VALUE = -1000;
// Zabezpieczenie przed lawina pobieran przy nietypowych proporcjach skali i widoku.
constexpr int MAX_TILES = 400;
}  // namespace

WebLayers::WebLayers(MapView* view, QObject* parent)
    : QObject(parent), view_(view), network_(new QNetworkAccessManager(this)) {
    cache_dir_ = QDir(QStandardPaths::writableLocation(QStandardPaths::CacheLocation)).filePath("weblayers");
    url_provider_ = [](web::Layer layer, int zoom, int x, int y) {
        return QUrl(QString::fromStdString(web::tile_url(layer, zoom, x, y)));
    };
    update_timer_.setSingleShot(true);
    update_timer_.setInterval(50);
    connect(&update_timer_, &QTimer::timeout, this, &WebLayers::update_now);
}

WebLayers::~WebLayers() { abort_downloads(); }

void WebLayers::set_layer(std::optional<web::Layer> layer) {
    if (layer == layer_) return;
    clear();
    layer_ = layer;
    zoom_ = -1;
    if (layer_) update_now();
}

void WebLayers::update() {
    if (layer_) update_timer_.start();
}

void WebLayers::clear() {
    update_timer_.stop();
    abort_downloads();
    remove_tiles();
}

void WebLayers::remove_tiles() {
    if (items_.isEmpty()) return;
    for (QGraphicsPixmapItem* item : std::as_const(items_)) delete item;
    items_.clear();
    emit tiles_changed();
}

void WebLayers::abort_downloads(const QSet<QString>& keep) {
    const QStringList keys = downloads_.keys();
    for (const QString& key : keys) {
        if (keep.contains(key)) continue;
        QNetworkReply* reply = downloads_.take(key);
        reply->abort();  // finished -> deleteLater
    }
}

void WebLayers::update_now() {
    MapScene* scene = view_->map_scene();
    const Projection* projection = view_->projection();
    if (!layer_ || !scene || !scene->map() || !projection || !view_->ruler()) return;
    // widoczny prostokat w stopniach (get_corners_geo_coordinates) i zoom ze skali linijki
    const QPointF lt = view_->mapToScene(0, 0);
    const QPointF rb = view_->mapToScene(view_->viewport()->width(), view_->viewport()->height());
    GeoPoint lt_geo, rb_geo;
    try {
        lt_geo = projection->canvas_to_geo(lt.x(), lt.y());
        rb_geo = projection->canvas_to_geo(rb.x(), rb.y());
    } catch (const std::exception&) {
        return;
    }
    const int zoom = web::zoom_from_scale(*layer_, view_->ruler()->map_scale());
    if (zoom != zoom_) {
        // inny zoom - kafelki z poprzedniego sa w innej skali (jak set_web_layer_graphic w Pythonie)
        abort_downloads();
        remove_tiles();
        zoom_ = zoom;
    }
    std::vector<web::Tile> tiles =
        web::tiles_for_area(lt_geo.latitude, lt_geo.longitude, rb_geo.latitude, rb_geo.longitude, zoom);
    if (tiles.size() > static_cast<size_t>(MAX_TILES)) tiles.resize(MAX_TILES);

    QSet<QString> wanted;
    for (const web::Tile& tile : tiles) wanted.insert(QString::fromStdString(web::tile_path(*layer_, zoom, tile.x, tile.y)));
    abort_downloads(wanted);  // kafelki, ktore wyszly poza widok, nie sa juz potrzebne

    const QDir cache(cache_dir_);
    for (const web::Tile& tile : tiles) {
        const QString key = QString::fromStdString(web::tile_path(*layer_, zoom, tile.x, tile.y));
        if (items_.contains(key) || downloads_.contains(key)) continue;
        const QString file = cache.filePath(key);
        if (QFileInfo::exists(file) && add_tile_item(tile, key, file)) continue;
        download(tile, key, file);
    }
}

bool WebLayers::add_tile_item(const web::Tile& tile, const QString& key, const QString& file) {
    MapScene* scene = view_->map_scene();
    const Projection* projection = view_->projection();
    if (!scene || !projection) return false;
    QPixmap pixmap(file);
    if (pixmap.isNull() || pixmap.width() == 0) {
        // uszkodzony plik (np. strona bledu zamiast obrazka) - usuwamy, zostanie pobrany ponownie
        QFile::remove(file);
        return false;
    }
    const PointF p1 = projection->geo_to_canvas(tile.left_top_lat, tile.left_top_lon);
    const PointF p2 = projection->geo_to_canvas(tile.right_bott_lat, tile.right_bott_lon);
    auto* item = new QGraphicsPixmapItem(pixmap);
    item->setPos(p1.x, p1.y);
    item->setScale((p2.x - p1.x) / pixmap.width());
    item->setZValue(WEB_LAYER_Z_VALUE);
    item->setAcceptedMouseButtons(Qt::NoButton);
    item->setTransformationMode(Qt::SmoothTransformation);
    scene->addItem(item);
    items_.insert(key, item);
    emit tiles_changed();
    return true;
}

void WebLayers::download(const web::Tile& tile, const QString& key, const QString& file) {
    QNetworkRequest request(url_provider_(*layer_, zoom_, tile.x, tile.y));
    request.setHeader(QNetworkRequest::UserAgentHeader, QStringLiteral("pwMapedit"));
    request.setTransferTimeout(WEBLAYER_DOWNLOAD_TIMEOUT * 1000);
    QNetworkReply* reply = network_->get(request);
    downloads_.insert(key, reply);
    const std::optional<web::Layer> layer = layer_;
    const int zoom = zoom_;
    connect(reply, &QNetworkReply::finished, this, [this, reply, tile, key, file, layer, zoom] {
        reply->deleteLater();
        const bool current = downloads_.value(key) == reply;
        if (current) downloads_.remove(key);
        if (!current || reply->error() != QNetworkReply::NoError) return;  // przerwane albo blad - pomijamy
        const QByteArray data = reply->readAll();
        if (data.isEmpty()) return;
        QDir().mkpath(QFileInfo(file).absolutePath());
        QFile out(file);
        if (!out.open(QIODevice::WriteOnly) || out.write(data) != data.size()) return;
        out.close();
        // warstwa albo zoom mogly sie zmienic w trakcie pobierania
        if (layer_ == layer && zoom_ == zoom && !items_.contains(key)) add_tile_item(tile, key, file);
    });
}

}  // namespace pwm::gui
