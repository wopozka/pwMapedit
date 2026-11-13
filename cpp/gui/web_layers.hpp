// Port czesci warstw WWW z mapRender.py/mapCanvas.py: kafelki pod mapa (OSM, Geoportal, Google).
//
// Po kazdej zmianie widoku (przesuniecie, powiekszenie, zmiana rozmiaru) liczony jest zoom ze skali linijki
// i lista kafelkow pokrywajacych widok (core/web_tiles). Kafelki z pamieci podrecznej na dysku trafiaja od razu
// na scene, brakujace sa pobierane w tle (QNetworkAccessManager) i zapisywane w pamieci podrecznej.
#pragma once

#include <QHash>
#include <QObject>
#include <QSet>
#include <QString>
#include <QTimer>
#include <QUrl>
#include <functional>
#include <optional>

#include "web_tiles.hpp"

class QGraphicsPixmapItem;
class QNetworkAccessManager;
class QNetworkReply;

namespace pwm::gui {

class MapView;

class WebLayers : public QObject {
    Q_OBJECT
public:
    explicit WebLayers(MapView* view, QObject* parent = nullptr);
    ~WebLayers() override;

    // Wlaczenie warstwy (brak - wylaczenie i usuniecie kafelkow ze sceny).
    void set_layer(std::optional<web::Layer> layer);
    std::optional<web::Layer> layer() const { return layer_; }

    // Przeliczenie kafelkow dla biezacego widoku (z opoznieniem - kolejne zmiany widoku sa laczone).
    void update();
    void update_now();
    // Usuniecie kafelkow ze sceny i przerwanie pobierania - przed wyczyszczeniem sceny (nowa mapa).
    void clear();

    // Katalog pamieci podrecznej (domyslnie <cache uzytkownika>/weblayers, trwaly miedzy uruchomieniami).
    void set_cache_dir(const QString& dir) { cache_dir_ = dir; }
    const QString& cache_dir() const { return cache_dir_; }
    // Adres kafelka (domyslnie web::tile_url); testy podstawiaja plik lokalny.
    void set_url_provider(std::function<QUrl(web::Layer, int, int, int)> provider) { url_provider_ = std::move(provider); }

    int zoom() const { return zoom_; }
    int tile_count() const { return static_cast<int>(items_.size()); }
    int pending_downloads() const { return static_cast<int>(downloads_.size()); }

signals:
    // Kafelki na scenie sie zmienily (dodany kafelek albo wyczyszczenie).
    void tiles_changed();

private:
    void remove_tiles();
    void abort_downloads(const QSet<QString>& keep = {});
    bool add_tile_item(const web::Tile& tile, const QString& key, const QString& file);
    void download(const web::Tile& tile, const QString& key, const QString& file);

    MapView* view_;
    std::optional<web::Layer> layer_;
    int zoom_ = -1;
    QString cache_dir_;
    std::function<QUrl(web::Layer, int, int, int)> url_provider_;
    QHash<QString, QGraphicsPixmapItem*> items_;  // klucz: sciezka wzgledna kafelka
    QHash<QString, QNetworkReply*> downloads_;
    QNetworkAccessManager* network_;
    QTimer update_timer_;
};

}  // namespace pwm::gui
