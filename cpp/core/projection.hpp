// Port projection.py oraz utm/conversion.py.
#pragma once

#include <optional>
#include <stdexcept>
#include <string>

#include "geometry.hpp"

namespace pwm {

class Projection {
public:
    virtual ~Projection() = default;
    virtual PointF geo_to_canvas(double latitude, double longitude) const = 0;
    virtual GeoPoint canvas_to_geo(double x, double y) const = 0;
    virtual int calculate_data_offset() {
        earth_radius = 6378137.0;
        return 0;
    }
    const std::string& name() const { return name_; }
    void set_map_bounding_box(const GeoBBox& bbox) { map_bbox_ = bbox; }
    const GeoBBox& map_bounding_box() const { return map_bbox_; }

    double earth_radius = 6378137.0;

protected:
    explicit Projection(std::string name, GeoBBox bbox = {}) : map_bbox_(bbox), name_(std::move(name)) {}
    GeoBBox map_bbox_;

private:
    std::string name_;
};

// Prosta projekcja (glownie do testow). W Pythonie canvas_to_geo nie bylo zaimplementowane.
class DirectProjection : public Projection {
public:
    explicit DirectProjection(GeoBBox bbox = {}) : Projection("Direct", bbox) {}
    PointF geo_to_canvas(double latitude, double longitude) const override;
    GeoPoint canvas_to_geo(double x, double y) const override;
};

class MercatorProjection : public Projection {
public:
    explicit MercatorProjection(GeoBBox bbox = {}) : Projection("Mercator", bbox) {}
    PointF geo_to_canvas(double latitude, double longitude) const override;
    GeoPoint canvas_to_geo(double x, double y) const override;
};

// UTM. Jak w Pythonie: przesuniecie liczone w konstruktorze z bounding boxa,
// canvas_to_geo nie jest zaimplementowane (w Pythonie zwracalo None).
class UtmProjection : public Projection {
public:
    explicit UtmProjection(GeoBBox bbox = {});
    int calculate_data_offset() override;
    PointF geo_to_canvas(double latitude, double longitude) const override;
    GeoPoint canvas_to_geo(double x, double y) const override;
    int map_data_offset() const { return map_data_offset_; }

private:
    int map_data_offset_ = 0;
};

namespace utm {

struct OutOfRangeError : std::out_of_range {
    using std::out_of_range::out_of_range;
};

struct UtmCoord {
    double easting;
    double northing;
    int zone_number;
    std::optional<char> zone_letter;
};

UtmCoord from_latlon(double latitude, double longitude, std::optional<int> force_zone_number = std::nullopt);
GeoPoint to_latlon(double easting, double northing, int zone_number, std::optional<char> zone_letter,
                   std::optional<bool> northern);
std::optional<char> latitude_to_zone_letter(double latitude);
int latlon_to_zone_number(double latitude, double longitude);
int zone_number_to_central_longitude(int zone_number);

}  // namespace utm

}  // namespace pwm
