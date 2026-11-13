#include "gpx_reader.hpp"

#include <QFile>
#include <QXmlStreamReader>

namespace pwm::gui {

namespace {

// Wspolne pola punktu (wpt, trkpt, rtept): atrybuty lat/lon i elementy ele, time oraz - dla waypointow - name,
// cmt, desc, sym. Czyta do zamkniecia elementu punktu.
bool read_point(QXmlStreamReader& xml, gps::Point& point, gps::Waypoint* waypoint) {
    bool ok_lat = false, ok_lon = false;
    point.lat = xml.attributes().value("lat").toDouble(&ok_lat);
    point.lon = xml.attributes().value("lon").toDouble(&ok_lon);
    QString desc;
    while (xml.readNextStartElement()) {
        const auto name = xml.name();
        if (name == QLatin1String("ele")) {
            bool ok = false;
            const double ele = xml.readElementText().toDouble(&ok);
            if (ok) point.ele = ele;
        } else if (name == QLatin1String("time")) {
            point.time = xml.readElementText().toStdString();
        } else if (waypoint && name == QLatin1String("name")) {
            waypoint->name = xml.readElementText().trimmed().toStdString();
        } else if (waypoint && name == QLatin1String("cmt")) {
            waypoint->comment = xml.readElementText().trimmed().toStdString();
        } else if (waypoint && name == QLatin1String("desc")) {
            desc = xml.readElementText().trimmed();
        } else if (waypoint && name == QLatin1String("sym")) {
            waypoint->symbol = xml.readElementText().trimmed().toStdString();
        } else {
            xml.skipCurrentElement();
        }
    }
    if (waypoint && waypoint->comment.empty()) waypoint->comment = desc.toStdString();
    return ok_lat && ok_lon && point.lat >= -90 && point.lat <= 90 && point.lon >= -180 && point.lon <= 180;
}

}  // namespace

std::optional<gps::File> read_gpx(const QByteArray& data, QString* error) {
    gps::File file;
    QXmlStreamReader xml(data);
    if (!xml.readNextStartElement() || xml.name() != QLatin1String("gpx")) {
        if (error) *error = QObject::tr("To nie jest plik GPX.");
        return std::nullopt;
    }
    int skipped = 0;
    while (xml.readNextStartElement()) {
        const auto name = xml.name();
        if (name == QLatin1String("wpt")) {
            gps::Waypoint wpt;
            if (read_point(xml, wpt.pos, &wpt))
                file.waypoints.push_back(std::move(wpt));
            else
                ++skipped;
        } else if (name == QLatin1String("trk") || name == QLatin1String("rte")) {
            const bool route = name == QLatin1String("rte");
            gps::Track track;
            track.route = route;
            if (route) track.segments.emplace_back();
            while (xml.readNextStartElement()) {
                const auto child = xml.name();
                if (child == QLatin1String("name")) {
                    track.name = xml.readElementText().trimmed().toStdString();
                } else if (!route && child == QLatin1String("trkseg")) {
                    std::vector<gps::Point> segment;
                    while (xml.readNextStartElement()) {
                        if (xml.name() != QLatin1String("trkpt")) {
                            xml.skipCurrentElement();
                            continue;
                        }
                        gps::Point p;
                        if (read_point(xml, p, nullptr))
                            segment.push_back(std::move(p));
                        else
                            ++skipped;
                    }
                    if (!segment.empty()) track.segments.push_back(std::move(segment));
                } else if (route && child == QLatin1String("rtept")) {
                    gps::Waypoint rtept;  // nazwy punktow trasy pomijamy - trasa jest rysowana jak slad
                    if (read_point(xml, rtept.pos, &rtept))
                        track.segments.back().push_back(rtept.pos);
                    else
                        ++skipped;
                } else {
                    xml.skipCurrentElement();
                }
            }
            if (route && track.segments.back().empty()) track.segments.clear();
            if (!track.segments.empty()) file.tracks.push_back(std::move(track));
        } else {
            xml.skipCurrentElement();
        }
    }
    if (xml.hasError()) {
        if (error)
            *error = QObject::tr("Błąd w pliku GPX (linia %1): %2").arg(xml.lineNumber()).arg(xml.errorString());
        return std::nullopt;
    }
    if (error) *error = skipped ? QObject::tr("Pominięto punktów bez poprawnych współrzędnych: %1").arg(skipped) : QString();
    return file;
}

std::optional<gps::File> read_gpx_file(const QString& path, QString* error) {
    QFile f(path);
    if (!f.open(QIODevice::ReadOnly)) {
        if (error) *error = QObject::tr("Nie można otworzyć pliku: %1").arg(f.errorString());
        return std::nullopt;
    }
    auto file = read_gpx(f.readAll(), error);
    if (file) file->path = path.toStdString();
    return file;
}

}  // namespace pwm::gui
