// Czytnik plikow GPX (1.0 i 1.1): waypointy <wpt>, slady <trk>/<trkseg>/<trkpt> i trasy <rte>/<rtept>.
#pragma once

#include <QString>
#include <optional>

#include "gps_data.hpp"

namespace pwm::gui {

// Wczytuje plik; przy bledzie zwraca brak wyniku i opis w error.
std::optional<gps::File> read_gpx_file(const QString& path, QString* error = nullptr);
std::optional<gps::File> read_gpx(const QByteArray& data, QString* error = nullptr);

}  // namespace pwm::gui
