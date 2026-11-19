// Testy edycji w GUI (etap 3b): komendy undo/redo na scenie oraz przeciaganie obiektu mysza.
// Uruchamiane bez okna: gui_tests -platform offscreen (tak robi ctest).
#include <QJsonArray>
#include <QJsonDocument>
#include <QMimeData>
#include <QSignalSpy>
#include <QUndoStack>
#include <QRandomGenerator>
#include <QtTest>
#include <memory>

#include "constants.hpp"
#include "map_items.hpp"
#include "map_scene.hpp"
#include "map_styles.hpp"
#include "map_view.hpp"
#include "properties_dock.hpp"
#include "gps_dock.hpp"
#include "gps_layers.hpp"
#include "gpx_reader.hpp"
#include <QDoubleSpinBox>
#include "main_window.hpp"
#include <QMessageBox>
#include <QAbstractButton>
#include <QFile>
#include <QProgressBar>
#include "web_layers.hpp"
#include <QTemporaryDir>
#include <QImage>
#include <QPainter>
#include <QCheckBox>
#include <QComboBox>
#include <QLineEdit>
#include <QVBoxLayout>
#include <QAction>
#include <QActionGroup>
#include <QPlainTextEdit>
#include <QPushButton>
#include <QTabWidget>
#include <QTableWidget>
#include <QTreeWidget>
#include <QMenu>

using namespace pwm;
using namespace pwm::gui;

namespace {

const char* SAMPLE_MAP =
    "[IMG ID]\n"
    "Name=test\n"
    "[END-IMG ID]\n"
    "\n"
    "[POI]\n"
    "Type=0x2f00\n"
    "Label=Stacja\n"
    "Data0=(52.10000,21.00000)\n"
    "[END]\n"
    "\n"
    "[POLYLINE]\n"
    "Type=0x6\n"
    "Label=Ulica\n"
    "DirIndicator=1\n"
    "Data0=(52.10000,21.00000),(52.10100,21.00100),(52.10200,21.00300)\n"
    "Numbers1=0,O,1,5,E,2,6\n"
    "Data1=(52.10000,21.00000),(52.10200,21.00300)\n"
    "[END]\n"
    "\n";

// Mapa, scena i stos undo przygotowane tak jak w MainWindow::file_loaded.
struct Fixture {
    std::unique_ptr<MapData> map = std::make_unique<MapData>(std::make_unique<MercatorProjection>());
    MapStyles styles{MapStyles::find_icons_dir()};
    QUndoStack stack;
    MapScene scene;
    std::string original;

    explicit Fixture(const char* mp = SAMPLE_MAP) {
        map->load_from_string(mp);
        Projection& projection = map->projection();
        projection.set_map_bounding_box(map->map_bounding_box());
        projection.calculate_data_offset();
        scene.set_canvas_rectangle(map->map_bounding_box(), projection);
        scene.set_undo_stack(&stack);
        scene.set_map(map.get(), &styles);
        original = map->to_mp_string();
    }
    ~Fixture() { scene.clear_map(); }

    MapObjectItem* poi() const { return scene.item_for_object(0); }
    MapObjectItem* polyline() const { return scene.item_for_object(1); }
    const Node& node(size_t obj, int level, size_t i) const {
        return map->objects()[obj].data->polys_for_data_level(level)->front()[i];
    }
    void select_only(MapObjectItem* item) {
        scene.clearSelection();
        item->graphics_item()->setSelected(true);
    }
    size_t node_count(size_t obj, int level = 0) const {
        return map->objects()[obj].data->polys_for_data_level(level)->front().size();
    }
    PolyItem* poly(size_t obj) const { return dynamic_cast<PolyItem*>(scene.item_for_object(obj)); }
    std::vector<GripItem*> grips(size_t obj) const {
        std::vector<GripItem*> result;
        for (QGraphicsItem* child : poly(obj)->childItems())
            if (child->type() == GripItemType) result.push_back(static_cast<GripItem*>(child));
        return result;
    }
};

// Panel wlasciwosci podlaczony do sceny tak jak w MainWindow.
struct DockFixture : Fixture {
    PropertiesDock dock{&scene};
    DockFixture() {
        QObject::connect(&scene, &QGraphicsScene::selectionChanged, &dock, &PropertiesDock::refresh);
        QObject::connect(&scene, &MapScene::active_grip_changed, &dock, &PropertiesDock::refresh);
        QObject::connect(&scene, &MapScene::tool_changed, &dock, &PropertiesDock::refresh);
        QObject::connect(&stack, &QUndoStack::indexChanged, &dock, &PropertiesDock::refresh);
    }
    const MapObject& obj(size_t i) const { return map->objects()[i]; }
    void edit_line(QLineEdit* edit, const QString& text) {
        edit->setText(text);
        emit edit->editingFinished();
    }
};

// Widok do testow z mysza: polilinia na srodku, bez zmiany skali.
struct ViewFixture : Fixture {
    MapView view{&scene};
    ViewFixture() {
        view.set_projection(&map->projection());
        view.resize(800, 600);
        view.show();
        QVERIFY(QTest::qWaitForWindowExposed(&view));
        const PointF a = node(1, 0, 0).pos(), b = node(1, 0, 1).pos();
        view.centerOn(QPointF((a.x + b.x) / 2, (a.y + b.y) / 2));
    }
    QPoint view_pos(const PointF& p) const { return view.mapFromScene(QPointF(p.x, p.y)); }
    QWidget* vp() const { return view.viewport(); }
};

}  // namespace

class EditTests : public QObject {
    Q_OBJECT
private slots:
    void transparent_polygon_fill();
    void move_polyline_undo_redo();
    void move_poi_and_undo();
    void delete_and_undo();
    void reverse_all_levels_and_undo();
    void reverse_without_polyline_does_nothing();
    void mouse_drag_moves_polyline();
    void mouse_drag_moves_poi_when_zoomed_in();
    void mouse_drag_moves_poi_when_zoomed_out();
    // element na poziom Data, indeks BSP
    void scene_uses_bsp_index();
    void poi_icons_drawn_by_layer();
    void geometric_hit_test_matches_shape();
    void item_per_data_level();
    void refresh_syncs_data_level_items();
    // 3b.2: edycja wezlow
    void edit_nodes_tool_decorates_selection();
    void interpolated_numbers_in_edit_nodes_mode();
    void edit_nodes_cross_cursor_over_edges();
    void drag_from_edge_inserts_and_moves_node();
    void move_remove_insert_node_undo();
    void remove_node_keeps_minimum();
    void insert_node_extends_polyline_end();
    void split_and_merge_polyline();
    void grip_drag_ctrl_click_and_split_key();
    void shift_click_inserts_node();
    // 3b.3: panel wlasciwosci
    void dock_follows_selection();
    void dock_labels_endlevel_direction();
    void dock_endlevel_digit_keys();
    void dock_type_comment_extras();
    void dock_address_and_routing();
    void dock_node_hlevel_and_numbers();
    void dock_numbers_on_road_without_numbering();
    void ctrl_click_last_node_with_dock();
    void dock_elements_highlight();
    // 3b.4: schowek
    void copy_paste_at_cursor_and_undo();
    void copy_paste_several_objects();
    void paste_plain_text_keeps_position();
    void copy_without_selection_gives_nothing();
    // 3c.1: tworzenie obiektow i przyciaganie
    void create_poi_with_click();
    void create_polyline_and_polygon_with_keys();
    void create_circle();
    void snap_to_node_when_creating();
    void snap_grip_to_other_object();
    // 3c.2: warstwy WWW
    void web_layer_download_cache_and_toggle();
    // poprawki po klikaniu: schowek Extras, ostatnie pliki, pytanie przy zamykaniu
    void extras_copy_paste_between_objects();
    void window_recent_files_and_close_prompt();
    // slady GPS (GPX) jako podklad do rysowania
    void gpx_reader_parses_tracks_waypoints_routes();
    void gps_layer_items_snapping_and_visibility();
    void gps_track_to_polyline_and_waypoints_to_pois();
    void gps_dock_lists_and_creates();
    void gps_load_gdb_far_from_map();
    // karta Elements: menu czesci i poziomow
    void elements_move_copy_level_endlevel();
    void elements_delete_extract_polygon_parts();
    // odejmowanie polygonow
    void subtract_polygons_hole_partial_and_delete();
    void ctrl_click_adds_polygon_lying_on_selected_one();
    void convert_polyline_polygon_both_ways();
    void road_casing_under_roads_only();
    void trail_icon_positions_along_line();
    void trail_icons_drawn_on_trails_only();
    void map_level_for_scale_ranges();
    void shift_wheel_rotates_object_in_edit_nodes();
    void viaduct_pois_at_crossings();
    void dead_end_pois_at_unconnected_ends();
    void marker_poi_key_sequences();
    void auto_map_level_follows_scale();
    void dock_prev_next_node_buttons();
    void node_step_shortcuts();
};

void EditTests::move_polyline_undo_redo() {
    Fixture f;
    QVERIFY(f.poi() && f.polyline());
    const PointF n0 = f.node(1, 0, 0).pos();
    const PointF level1 = f.node(1, 1, 0).pos();
    // tak jak po przeciagnieciu: element jest juz przesuniety, komenda zapisuje to w danych
    f.polyline()->graphics_item()->setPos(5, -3);
    f.scene.move_objects({{f.polyline(), QPointF(5, -3)}});
    QCOMPARE(f.stack.count(), 1);
    QCOMPARE(f.node(1, 0, 0).x(), n0.x + 5);
    QCOMPARE(f.node(1, 0, 0).y(), n0.y - 3);
    QVERIFY(f.node(1, 1, 0).pos() == level1);  // przesuwany jest tylko pokazywany poziom
    QCOMPARE(f.polyline()->graphics_item()->pos(), QPointF(0, 0));
    auto* path_item = static_cast<QGraphicsPathItem*>(f.polyline()->graphics_item());
    QCOMPARE(path_item->path().elementAt(0).x, n0.x + 5);

    f.stack.undo();
    QCOMPARE(f.map->to_mp_string(), f.original);
    QCOMPARE(path_item->path().elementAt(0).x, n0.x);
    f.stack.redo();
    QCOMPARE(f.node(1, 0, 0).x(), n0.x + 5);
    f.stack.undo();
    QCOMPARE(f.map->to_mp_string(), f.original);
}

void EditTests::move_poi_and_undo() {
    Fixture f;
    const PointF p = f.node(0, 0, 0).pos();
    f.scene.move_objects({{f.poi(), QPointF(-7, 2)}});
    QCOMPARE(f.poi()->graphics_item()->pos(), QPointF(p.x - 7, p.y + 2));
    f.stack.undo();
    QCOMPARE(f.poi()->graphics_item()->pos(), QPointF(p.x, p.y));
    QCOMPARE(f.map->to_mp_string(), f.original);
}

void EditTests::delete_and_undo() {
    Fixture f;
    f.poi()->graphics_item()->setSelected(true);
    f.polyline()->graphics_item()->setSelected(true);
    f.scene.delete_selected();
    QCOMPARE(f.stack.count(), 1);
    QVERIFY(f.map->objects()[0].deleted && f.map->objects()[1].deleted);
    QVERIFY(!f.poi()->graphics_item()->isVisible());
    QVERIFY(!f.polyline()->graphics_item()->isVisible());
    QVERIFY(f.scene.selectedItems().isEmpty());
    QVERIFY(f.map->to_mp_string().find("[POLYLINE]") == std::string::npos);
    // usuniety obiekt nie pojawia sie po zmianie poziomu mapy
    f.scene.set_map_level(1);
    QVERIFY(!f.polyline()->graphics_item()->isVisible());
    f.scene.set_map_level(0);

    f.stack.undo();
    QVERIFY(f.poi()->graphics_item()->isVisible());
    QVERIFY(f.polyline()->graphics_item()->isVisible());
    QCOMPARE(f.map->to_mp_string(), f.original);
}

void EditTests::reverse_all_levels_and_undo() {
    Fixture f;
    const PointF first0 = f.node(1, 0, 0).pos();
    const PointF last0 = f.node(1, 0, 2).pos();
    const PointF last1 = f.node(1, 1, 1).pos();
    f.select_only(f.polyline());
    f.poi()->graphics_item()->setSelected(true);  // POI jest pomijane
    f.scene.reverse_selected_polylines();
    QCOMPARE(f.stack.count(), 1);
    QVERIFY(f.node(1, 0, 0).pos() == last0);
    QVERIFY(f.node(1, 0, 2).pos() == first0);
    QVERIFY(f.node(1, 1, 0).pos() == last1);
    f.stack.undo();
    QCOMPARE(f.map->to_mp_string(), f.original);
}

void EditTests::reverse_without_polyline_does_nothing() {
    Fixture f;
    f.select_only(f.poi());
    f.scene.reverse_selected_polylines();
    QCOMPARE(f.stack.count(), 0);
}

void EditTests::mouse_drag_moves_polyline() {
    Fixture f;
    MapView view(&f.scene);
    view.set_projection(&f.map->projection());
    view.resize(800, 600);
    view.show();
    QVERIFY(QTest::qWaitForWindowExposed(&view));
    const PointF n0 = f.node(1, 0, 0).pos();
    const PointF n1 = f.node(1, 0, 1).pos();
    const QPointF on_line((n0.x + n1.x) / 2, (n0.y + n1.y) / 2);
    view.centerOn(on_line);
    const QPoint press = view.mapFromScene(on_line);
    QWidget* vp = view.viewport();

    // ruch ponizej progu MIN_MOVE_DISTANCE nie przesuwa obiektu
    QTest::mousePress(vp, Qt::LeftButton, Qt::NoModifier, press);
    QTest::mouseMove(vp, press + QPoint(2, 0));
    QTest::mouseRelease(vp, Qt::LeftButton, Qt::NoModifier, press + QPoint(2, 0));
    QVERIFY(f.polyline()->graphics_item()->isSelected());
    QCOMPARE(f.stack.count(), 0);

    QTest::mousePress(vp, Qt::LeftButton, Qt::NoModifier, press);
    for (int dx = 10; dx <= 40; dx += 10) QTest::mouseMove(vp, press + QPoint(dx, 0));
    QTest::mouseRelease(vp, Qt::LeftButton, Qt::NoModifier, press + QPoint(40, 0));
    QCOMPARE(f.stack.count(), 1);
    const double moved = f.node(1, 0, 0).x() - n0.x;
    const double expected = view.mapToScene(press + QPoint(40, 0)).x() - view.mapToScene(press).x();
    QVERIFY2(qAbs(moved - expected) < 1e-6, qPrintable(QString("moved %1, expected %2").arg(moved).arg(expected)));
    QCOMPARE(f.node(1, 0, 0).y(), n0.y);
    QCOMPARE(f.polyline()->graphics_item()->pos(), QPointF(0, 0));

    f.stack.undo();
    QCOMPARE(f.map->to_mp_string(), f.original);
}

namespace {
// Przeciagniecie ikony POI mysza po zoom_steps krokach przyblizenia (ujemne - oddalenia). POI sa w ukladzie sceny;
// ikona ma powyzej skali 1 stala wielkosc na ekranie, ponizej jest zmniejszona (shape, paint, PoiIconLayer).
void drag_poi(int zoom_steps) {
    Fixture f;
    auto* poi = static_cast<QGraphicsPixmapItem*>(f.poi()->graphics_item());
    if (poi->pixmap().isNull()) QSKIP("brak ikon POI (katalog icons nie znaleziony)");
    MapView view(&f.scene);
    view.set_projection(&f.map->projection());
    view.resize(800, 600);
    view.show();
    QVERIFY(QTest::qWaitForWindowExposed(&view));
    for (int i = 0; i < zoom_steps; ++i) view.zoom_in();
    for (int i = 0; i < -zoom_steps; ++i) view.zoom_out();
    QVERIFY(!poi->flags().testFlag(QGraphicsItem::ItemIgnoresTransformations));
    const double size = std::min(f.scene.viewer_scale(), 1.0);
    // ikona na ekranie: pelny rozmiar powyzej skali 1, ponizej zmniejszona
    const QRectF on_screen =
        view.mapFromScene(poi->mapToScene(static_cast<PoiItem*>(f.poi())->icon_rect())).boundingRect();
    QVERIFY2(qAbs(on_screen.width() - poi->pixmap().width() * size) <= 2,
             qPrintable(QString("ikona %1 px, oczekiwano %2").arg(on_screen.width()).arg(poi->pixmap().width() * size)));

    const PointF p = f.node(0, 0, 0).pos();
    view.centerOn(QPointF(p.x, p.y));
    // srodek ikony: QGraphicsPixmapItem trafia tylko w nieprzezroczyste piksele (MaskShape)
    const QPoint press = view.mapFromScene(QPointF(p.x, p.y)) + (poi->boundingRect().center() * size).toPoint();
    QWidget* vp = view.viewport();
    QTest::mousePress(vp, Qt::LeftButton, Qt::NoModifier, press);
    QVERIFY(poi->isSelected());
    for (int dx = 10; dx <= 40; dx += 10) QTest::mouseMove(vp, press + QPoint(dx, dx / 2));
    QTest::mouseRelease(vp, Qt::LeftButton, Qt::NoModifier, press + QPoint(40, 20));
    QCOMPARE(f.stack.count(), 1);

    const QPointF expected = view.mapToScene(press + QPoint(40, 20)) - view.mapToScene(press);
    const PointF moved{f.node(0, 0, 0).x() - p.x, f.node(0, 0, 0).y() - p.y};
    QVERIFY2(qAbs(moved.x - expected.x()) < 1e-6 && qAbs(moved.y - expected.y()) < 1e-6,
             qPrintable(QString("moved (%1, %2), expected (%3, %4)")
                            .arg(moved.x).arg(moved.y).arg(expected.x()).arg(expected.y())));
    QCOMPARE(poi->pos(), QPointF(f.node(0, 0, 0).x(), f.node(0, 0, 0).y()));
    f.stack.undo();
    QCOMPARE(f.map->to_mp_string(), f.original);
}
}  // namespace

void EditTests::mouse_drag_moves_poi_when_zoomed_in() {
    drag_poi(8);
}

void EditTests::mouse_drag_moves_poi_when_zoomed_out() {
    drag_poi(-5);  // skala ok. 0,6: ikona zmniejszona, ale jeszcze rysowana (SCALE_WITHOUT_POIS = 0,25)
}

void EditTests::scene_uses_bsp_index() {
    Fixture f;
    QCOMPARE(f.scene.itemIndexMethod(), QGraphicsScene::BspTreeIndex);
    QCOMPARE(f.scene.bspTreeDepth(), SCENE_BSP_TREE_DEPTH);
    // po wyczyszczeniu i ponownym wczytaniu mapy indeks zostaje
    f.scene.clear_map();
    f.scene.set_map(f.map.get(), &f.styles);
    QCOMPARE(f.scene.itemIndexMethod(), QGraphicsScene::BspTreeIndex);
    QCOMPARE(f.scene.bspTreeDepth(), SCENE_BSP_TREE_DEPTH);
}

namespace {
std::vector<int> item_levels(const MapScene& scene, size_t obj) {
    std::vector<int> levels;
    for (const MapObjectItem* item : scene.items_for_object(obj)) levels.push_back(item->data_level());
    return levels;
}
}  // namespace

// Ikony POI rysuje PoiIconLayer; POI rysuje sie sam tylko zaznaczony. Zaden element mapy nie ma
// ItemIgnoresTransformations - takie elementy indeks BSP przeglada przy kazdym zapytaniu.
void EditTests::poi_icons_drawn_by_layer() {
    Fixture f;
    for (MapObjectItem* item : f.scene.object_items())
        QVERIFY(!item->graphics_item()->flags().testFlag(QGraphicsItem::ItemIgnoresTransformations));
    auto* poi = static_cast<PoiItem*>(f.poi());
    if (poi->pixmap().isNull()) QSKIP("brak ikon POI (katalog icons nie znaleziony)");
    QVERIFY(!poi->paints_itself());
    QGraphicsItem* layer = nullptr;
    for (QGraphicsItem* item : f.scene.items())
        if (item->type() == PoiIconLayerItemType) layer = item;
    QVERIFY(layer);
    // POI znajdowane przez indeks w swoim polozeniu
    const PointF p = f.node(0, 0, 0).pos();
    QVERIFY(f.scene.items(QRectF(p.x - 1e-3, p.y - 1e-3, 2e-3, 2e-3), Qt::IntersectsItemBoundingRect).contains(poi));

    // ikone rysuje warstwa: obraz sceny wokol POI z warstwa rozni sie od obrazu bez niej (w tym miejscu zaczyna sie
    // tez polilinia; opisy ukryte - etykieta obok ikony)
    f.scene.annotation_layer()->setVisible(false);
    auto render = [&] {
        QImage image(64, 64, QImage::Format_ARGB32);
        image.fill(Qt::white);
        QPainter painter(&image);
        const QRectF icon = poi->mapToScene(poi->icon_rect()).boundingRect();
        f.scene.render(&painter, QRectF(0, 0, 64, 64), icon.adjusted(-2, -2, 2, 2));
        return image;
    };
    layer->setVisible(false);
    const QImage without = render();
    layer->setVisible(true);
    QVERIFY(render() != without);

    f.select_only(poi);
    QVERIFY(poi->paints_itself());
    f.scene.clearSelection();
    QVERIFY(!poi->paints_itself());
}

namespace {
const char* HIT_MAP =
    "[IMG ID]\n"
    "Name=test\n"
    "[END-IMG ID]\n"
    "\n"
    "[POLYGON]\n"
    "Type=0x50\n"
    "Data0=(52.10000,21.00000),(52.10000,21.01000),(52.09000,21.01000),(52.09000,21.00000)\n"
    "Data0=(52.09700,21.00300),(52.09700,21.00700),(52.09300,21.00700),(52.09300,21.00300)\n"
    "[END]\n"
    "\n"
    "[POLYLINE]\n"
    "Type=0x6\n"
    "Data0=(52.10000,21.00000),(52.09500,21.00500),(52.09800,21.01000),(52.09000,21.01200)\n"
    "[END]\n"
    "\n";

// Trafienie geometryczne (collidesWithPath/contains) w losowych punktach i prostokatach zgadza sie z ksztaltem:
// obrys o polszerokosci half_width, a dla polygonu (fill) takze wnetrze wedlug reguly parzystosci - tak jak polygon
// jest rysowany. (shape() Qt laczy obrys z wypelnieniem regula winding, wiec dziura o tym samym kierunku obiegu
// co obwod liczyla sie tam jako trafienie.) Pomijane punkty w pasie granicy obrysu i przy wezlach
// (konce i zalamania: zaokraglone zamiast scietych).
void compare_hits(PolyItem* item, double half_width, bool fill) {
    std::vector<std::pair<QPointF, QPointF>> segments;
    std::vector<QPointF> nodes;
    for (const QPolygonF& poly : item->path().toSubpathPolygons()) {
        for (int i = 0; i + 1 < poly.size(); ++i) segments.emplace_back(poly[i], poly[i + 1]);
        if (fill && !poly.isEmpty() && poly.first() != poly.last()) segments.emplace_back(poly.last(), poly.first());
        for (const QPointF& p : poly) nodes.push_back(p);
    }
    auto dist_segments = [&](const QPointF& p) {
        double best = 1e300;
        for (const auto& [a, b] : segments) {
            const QPointF d = b - a;
            const double len2 = QPointF::dotProduct(d, d);
            const double t = len2 > 0 ? std::clamp(QPointF::dotProduct(p - a, d) / len2, 0.0, 1.0) : 0.0;
            best = std::min(best, QLineF(p, a + d * t).length());
        }
        return best;
    };
    QPainterPathStroker stroker;
    stroker.setWidth(2 * half_width);
    const QPainterPath stroke = stroker.createStroke(item->path());
    auto expected_point = [&](const QPointF& p) { return stroke.contains(p) || (fill && item->path().contains(p)); };
    auto expected_rect = [&](const QRectF& r) { return stroke.intersects(r) || (fill && item->path().intersects(r)); };
    auto boundary = [&](const QPointF& p) {
        if (std::abs(dist_segments(p) - half_width) < 0.25 * half_width) return true;
        for (const QPointF& n : nodes)
            if (QLineF(p, n).length() < 2 * half_width) return true;
        return false;
    };
    const QRectF br = item->boundingRect();
    QRandomGenerator rng(12345);
    int compared = 0, hits = 0;
    for (int i = 0; i < 6000; ++i) {
        QPointF p;
        if (i % 2 == 0) {
            p = QPointF(br.left() + rng.generateDouble() * br.width(), br.top() + rng.generateDouble() * br.height());
        } else {  // przy odcinku, w odleglosci do 3 polszerokosci
            const auto& [a, b] = segments[rng.bounded(static_cast<int>(segments.size()))];
            const QLineF ab(a, b);
            const QLineF normal = ab.normalVector().unitVector();
            const QPointF n = normal.p2() - normal.p1();
            p = ab.pointAt(rng.generateDouble()) + n * ((rng.generateDouble() * 2 - 1) * 3 * half_width);
        }
        if (!br.contains(p) || boundary(p)) continue;
        const bool expected = expected_point(p);
        QVERIFY2(item->contains(p) == expected,
                 qPrintable(QString("punkt (%1, %2), odleglosc %3, oczekiwano %4")
                                .arg(p.x(), 0, 'f', 3).arg(p.y(), 0, 'f', 3).arg(dist_segments(p)).arg(expected)));
        // maly prostokat (jak zapytanie widoku o piksel pod kursorem)
        const QRectF r(p, QSizeF(half_width / 10, half_width / 10));
        if (!boundary(r.bottomRight())) {
            QPainterPath rect_path;
            rect_path.addRect(r);
            QCOMPARE(item->collidesWithPath(rect_path), expected_rect(r));
        }
        ++compared;
        if (expected) ++hits;
    }
    QVERIFY2(compared > 2000 && hits > 500, qPrintable(QString("porownano %1, trafien %2").arg(compared).arg(hits)));
}
}  // namespace

void EditTests::geometric_hit_test_matches_shape() {
    Fixture f(HIT_MAP);
    auto* polygon = f.poly(0);
    auto* polyline = f.poly(1);
    QVERIFY(polygon && polygon->is_polygon());
    QVERIFY(polyline && !polyline->is_polygon());
    // polilinia: obrys 2 * pioro, polygon: wypelnienie z dziura + pol piora
    compare_hits(polyline, polyline->pen().width(), false);
    compare_hits(polygon, std::max(polygon->pen().widthF(), 1e-8) / 2, true);
    // srodek dziury polygonu nie jest trafieniem, srodek pierscienia jest
    const QRectF hole = polygon->path().toSubpathPolygons().at(1).boundingRect();
    QVERIFY(!polygon->contains(hole.center()));
    QVERIFY(polygon->contains(QPointF(hole.center().x(), (polygon->boundingRect().top() + hole.top()) / 2)));
    // polygon w edycji wezlow: tylko krawedz
    f.select_only(polygon);
    f.scene.set_tool(Tool::EditNodes);
    QVERIFY(polygon->decorated());
    QVERIFY(!polygon->contains(QPointF(hole.center().x(), (polygon->boundingRect().top() + hole.top()) / 2)));
    f.scene.clearSelection();
    f.scene.set_tool(Tool::SelectObjects);
    QVERIFY(!polygon->decorated());
}

// Polilinia z Data0 i Data1 ma dwa elementy o stalej geometrii; zmiana poziomu przelacza tylko widocznosc.
void EditTests::item_per_data_level() {
    Fixture f;
    QCOMPARE(item_levels(f.scene, 0), std::vector<int>{0});
    QCOMPARE(item_levels(f.scene, 1), (std::vector<int>{0, 1}));
    auto* data0 = static_cast<PolyItem*>(f.scene.items_for_object(1)[0]);
    auto* data1 = static_cast<PolyItem*>(f.scene.items_for_object(1)[1]);
    const QPainterPath path0 = data0->path(), path1 = data1->path();
    QVERIFY(path0 != path1);
    QCOMPARE(path0.elementCount(), 3);
    QCOMPARE(path1.elementCount(), 2);
    QCOMPARE(f.scene.object_items().size(), size_t(3));

    QVERIFY(data0->isVisible());
    QVERIFY(!data1->isVisible());
    QCOMPARE(f.scene.item_for_object(1), static_cast<MapObjectItem*>(data0));
    QCOMPARE(data0->shown_data_level(), 0);

    f.scene.set_map_level(1);
    QVERIFY(!data0->isVisible());
    QVERIFY(data1->isVisible());
    QCOMPARE(f.scene.item_for_object(1), static_cast<MapObjectItem*>(data1));
    QCOMPARE(data1->shown_data_level(), 1);
    QCOMPARE(data0->path(), path0);
    QCOMPARE(data1->path(), path1);
    QVERIFY(!f.scene.item_for_object(0)->graphics_item()->isVisible());  // POI tylko Data0, EndLevel 0

    f.scene.set_map_level(0);
    QVERIFY(data0->isVisible());
    QVERIFY(!data1->isVisible());
    QVERIFY(f.scene.item_for_object(0)->graphics_item()->isVisible());
}

// Zmiana poziomow Data obiektu (komenda i undo): zbedne elementy usuwane, brakujace tworzone, pozostale zostaja.
void EditTests::refresh_syncs_data_level_items() {
    Fixture f;
    MapObjectItem* data0 = f.scene.items_for_object(1)[0];
    MapObject after = f.map->objects()[1];
    QVERIFY(after.data->move_data_level(1, 2));
    f.scene.replace_object(1, after, "przenies Data1");
    QCOMPARE(item_levels(f.scene, 1), (std::vector<int>{0, 2}));
    QCOMPARE(f.scene.items_for_object(1)[0], data0);
    QCOMPARE(f.scene.object_items().size(), size_t(3));
    f.scene.set_map_level(2);
    QCOMPARE(f.scene.item_for_object(1)->data_level(), 2);
    QVERIFY(f.scene.item_for_object(1)->graphics_item()->isVisible());
    f.scene.set_map_level(1);
    // brak Data1, EndLevel 0 - obiekt ukryty
    QVERIFY(!f.scene.item_for_object(1)->graphics_item()->isVisible());

    f.stack.undo();
    QCOMPARE(item_levels(f.scene, 1), (std::vector<int>{0, 1}));
    QCOMPARE(f.scene.items_for_object(1)[0], data0);
    QVERIFY(f.scene.item_for_object(1)->graphics_item()->isVisible());
    QCOMPARE(f.scene.item_for_object(1)->data_level(), 1);
    QCOMPARE(f.map->to_mp_string(), f.original);

    // usuniecie obiektu ukrywa wszystkie jego elementy, undo przywraca
    f.select_only(f.scene.item_for_object(1));
    f.scene.delete_selected();
    for (MapObjectItem* item : f.scene.items_for_object(1)) QVERIFY(!item->graphics_item()->isVisible());
    f.stack.undo();
    QVERIFY(f.scene.item_for_object(1)->graphics_item()->isVisible());
}

void EditTests::edit_nodes_tool_decorates_selection() {
    Fixture f;
    f.select_only(f.polyline());
    QVERIFY(!f.poly(1)->decorated());  // w trybie zaznaczania nie ma uchwytow
    f.scene.set_tool(Tool::EditNodes);
    QVERIFY(f.poly(1)->decorated());
    QCOMPARE(f.grips(1).size(), size_t{3});
    QVERIFY(!(f.poly(1)->flags() & QGraphicsItem::ItemIsMovable));
    f.scene.clearSelection();
    QVERIFY(!f.poly(1)->decorated());
    f.select_only(f.polyline());
    QVERIFY(f.poly(1)->decorated());
    f.scene.set_tool(Tool::SelectObjects);
    QVERIFY(!f.poly(1)->decorated());
    QVERIFY(f.poly(1)->flags() & QGraphicsItem::ItemIsMovable);
    // POI nie dostaje uchwytow, a Delete w trybie edycji wezlow nie usuwa obiektow
    f.scene.set_tool(Tool::EditNodes);
    f.select_only(f.poi());
    f.scene.delete_selected();
    QCOMPARE(f.stack.count(), 0);
}

void EditTests::interpolated_numbers_in_edit_nodes_mode() {
    Fixture f;
    auto labels = [&] {
        QStringList texts;
        for (const Annotation& a : f.poly(1)->annotations())
            if (a.kind == Annotation::Kind::Label || a.kind == Annotation::Kind::AddressNumber)
                texts << a.text.text();
        texts.sort();
        return texts;
    };
    const QStringList plain = labels();
    // Numbers1=0,O,1,5,E,2,6: miedzy wezlami z numeracja lewa strona 3, prawa 4
    f.scene.set_tool(Tool::EditNodes);
    f.select_only(f.polyline());
    QStringList expected = plain;
    expected << "3" << "4";
    expected.sort();
    QCOMPARE(labels(), expected);
    // przesuniecie wezla przebudowuje uchwyty i numery (bez dublowania)
    QVERIFY(f.scene.move_node(1, 0, 0, 1, QPointF(f.node(1, 0, 1).x() + 5, f.node(1, 0, 1).y())));
    QCOMPARE(labels(), expected);
    f.scene.clearSelection();
    QCOMPARE(labels(), plain);
}

void EditTests::edit_nodes_cross_cursor_over_edges() {
    // jak w Pythonie: krzyzyk tylko nad obiektem w edycji wezlow (zaznaczonym, z uchwytami)
    ViewFixture f;
    const PointF a = f.node(1, 0, 0).pos(), b = f.node(1, 0, 1).pos();
    const QPoint mid = f.view_pos(PointF{(a.x + b.x) / 2, (a.y + b.y) / 2});
    const QPoint away = mid + QPoint(0, 200);
    auto shape_at = [&](const QPoint& p) {
        QTest::mouseMove(f.vp(), away + QPoint(1, 0));
        QTest::mouseMove(f.vp(), p);
        return f.vp()->cursor().shape();
    };
    f.select_only(f.polyline());
    QCOMPARE(shape_at(mid), Qt::ArrowCursor);  // tryb zaznaczania
    f.scene.set_tool(Tool::EditNodes);
    QCOMPARE(shape_at(mid), Qt::CrossCursor);
    QCOMPARE(shape_at(away), Qt::ArrowCursor);
    f.scene.clearSelection();  // niezaznaczona droga - zwykly kursor
    QCOMPARE(shape_at(mid), Qt::ArrowCursor);
    f.select_only(f.polyline());
    QCOMPARE(shape_at(mid), Qt::CrossCursor);
    f.scene.set_tool(Tool::SelectObjects);
    QCOMPARE(shape_at(mid), Qt::ArrowCursor);

    // polygon w edycji: krzyzyk tylko na krawedzi, wnetrze nie nalezy do ksztaltu
    QMimeData mime;
    mime.setText("[POLYGON]\nType=0x4e\nData0=(52.1002,21.0020),(52.1002,21.0028),(52.1008,21.0028),"
                 "(52.1008,21.0020)\n[END]\n");
    QCOMPARE(f.scene.paste(&mime, std::nullopt), 1);
    auto* polygon = f.poly(f.map->objects().size() - 1);
    const auto& poly_nodes = f.map->objects().back().data->polys_for_data_level(0)->front();
    const PointF p0 = poly_nodes[0].pos(), p1 = poly_nodes[1].pos(), p2 = poly_nodes[2].pos();
    f.view.centerOn(QPointF((p0.x + p2.x) / 2, (p0.y + p2.y) / 2));
    const QPoint edge = f.view_pos(PointF{(p0.x + p1.x) / 2, (p0.y + p1.y) / 2});
    const QPoint inside = f.view_pos(PointF{(p0.x + p2.x) / 2, (p0.y + p2.y) / 2});
    f.scene.set_tool(Tool::EditNodes);
    f.select_only(polygon);
    QVERIFY(polygon->decorated());
    QCOMPARE(shape_at(edge), Qt::CrossCursor);
    QCOMPARE(shape_at(inside), Qt::ArrowCursor);
    f.scene.clearSelection();
    QCOMPARE(shape_at(edge), Qt::ArrowCursor);
}

void EditTests::drag_from_edge_inserts_and_moves_node() {
    ViewFixture f;
    f.scene.set_tool(Tool::EditNodes);
    f.select_only(f.polyline());
    const PointF a = f.node(1, 0, 0).pos(), b = f.node(1, 0, 1).pos();
    const QPoint mid = f.view_pos(PointF{(a.x + b.x) / 2, (a.y + b.y) / 2});
    const QPoint target = mid + QPoint(15, 25);

    // samo klikniecie na krawedzi niczego nie dodaje, obiekt zostaje w edycji
    QTest::mouseClick(f.vp(), Qt::LeftButton, Qt::NoModifier, mid);
    QTest::qWait(20);
    QCOMPARE(f.stack.count(), 0);
    QVERIFY(f.poly(1)->decorated());
    QCOMPARE(f.grips(1).size(), size_t{3});  // kwadrat podgladu znika
    QCOMPARE(f.poly(1)->path().elementCount(), 3);

    // nacisniecie na krawedzi i przeciagniecie: nowy wezel jedzie za kursorem, jedna komenda po puszczeniu
    QTest::mousePress(f.vp(), Qt::LeftButton, Qt::NoModifier, mid);
    // od razu po nacisnieciu: nowy wezel na krawedzi z kwadratem uchwytu
    QCOMPARE(f.grips(1).size(), size_t{4});
    QCOMPARE(f.poly(1)->path().elementCount(), 4);
    auto new_grip = [&]() -> GripItem* {
        for (GripItem* g : f.grips(1))
            if (!g->acceptHoverEvents()) return g;
        return nullptr;
    };
    QVERIFY(new_grip());
    QVERIFY((f.view.mapFromScene(new_grip()->scenePos()) - mid).manhattanLength() <= 2);
    for (int d = 1; d <= 5; ++d) QTest::mouseMove(f.vp(), mid + (target - mid) * d / 5);
    QCOMPARE(f.stack.count(), 0);  // w trakcie tylko podglad
    QCOMPARE(f.view.mapFromScene(new_grip()->scenePos()), target);
    QCOMPARE(f.poly(1)->path().elementCount(), 4);
    QTest::mouseRelease(f.vp(), Qt::LeftButton, Qt::NoModifier, target);
    QCOMPARE(f.stack.count(), 1);
    QCOMPARE(f.node_count(1), size_t{4});
    const QPointF expected = f.view.mapToScene(target);
    QVERIFY(qAbs(f.node(1, 0, 1).x() - expected.x()) < 1e-6);
    QVERIFY(qAbs(f.node(1, 0, 1).y() - expected.y()) < 1e-6);
    QVERIFY(f.poly(1)->decorated());
    QCOMPARE(f.grips(1).size(), size_t{4});
    f.stack.undo();
    QCOMPARE(f.map->to_mp_string(), f.original);

    // daleko od krawedzi przeciaganie nie dodaje wezla
    QTest::mousePress(f.vp(), Qt::LeftButton, Qt::NoModifier, mid + QPoint(0, 200));
    QTest::mouseMove(f.vp(), mid + QPoint(30, 230));
    QTest::mouseRelease(f.vp(), Qt::LeftButton, Qt::NoModifier, mid + QPoint(30, 230));
    QCOMPARE(f.stack.index(), 0);
    QCOMPARE(f.node_count(1), size_t{3});
}

void EditTests::move_remove_insert_node_undo() {
    Fixture f;
    f.scene.set_tool(Tool::EditNodes);
    f.select_only(f.polyline());
    const PointF n1 = f.node(1, 0, 1).pos();

    QVERIFY(f.scene.move_node(1, 0, 0, 1, QPointF(n1.x + 3, n1.y - 4)));
    QCOMPARE(f.node(1, 0, 1).x(), n1.x + 3);
    QCOMPARE(f.grips(1)[1]->pos(), QPointF(n1.x + 3, n1.y - 4));
    QVERIFY(f.node(1, 1, 0).pos() == f.node(1, 1, 0).pos());

    QVERIFY(f.scene.insert_node(1, 0, 0, 1, QPointF(n1.x - 1, n1.y - 1)));
    QCOMPARE(f.node_count(1), size_t{4});
    QCOMPARE(f.grips(1).size(), size_t{4});

    QVERIFY(f.scene.remove_node(1, 0, 0, 2));
    QCOMPARE(f.node_count(1), size_t{3});
    QCOMPARE(f.grips(1).size(), size_t{3});
    QCOMPARE(f.stack.count(), 3);

    f.stack.undo();
    f.stack.undo();
    f.stack.undo();
    QCOMPARE(f.map->to_mp_string(), f.original);
    QCOMPARE(f.grips(1).size(), size_t{3});
    QVERIFY(f.poly(1)->decorated());
}

void EditTests::remove_node_keeps_minimum() {
    Fixture f;
    f.scene.set_tool(Tool::EditNodes);
    f.select_only(f.polyline());
    QVERIFY(f.scene.remove_node(1, 0, 0, 0));
    QCOMPARE(f.node_count(1), size_t{2});
    QVERIFY(!f.scene.remove_node(1, 0, 0, 0));  // polilinia musi miec co najmniej 2 wezly
    QCOMPARE(f.stack.count(), 1);
}

void EditTests::insert_node_extends_polyline_end() {
    Fixture f;
    f.scene.set_tool(Tool::EditNodes);
    f.select_only(f.polyline());
    const PointF b = f.node(1, 0, 1).pos(), c = f.node(1, 0, 2).pos();
    const QPointF beyond(c.x + (c.x - b.x), c.y + (c.y - b.y));  // za ostatnim wezlem, na przedluzeniu
    QVERIFY(f.scene.insert_node_at(beyond));
    QCOMPARE(f.node_count(1), size_t{4});
    QCOMPARE(f.node(1, 0, 3).x(), beyond.x());
    QCOMPARE(f.node(1, 0, 3).y(), beyond.y());
    f.stack.undo();
    QCOMPARE(f.map->to_mp_string(), f.original);
}

void EditTests::split_and_merge_polyline() {
    Fixture f;
    f.scene.set_tool(Tool::EditNodes);
    f.select_only(f.polyline());
    QVERIFY(!f.scene.split_polyline(1, 0, 0, 0));  // nie na pierwszym wezle
    QVERIFY(!f.scene.split_polyline(0, 0, 0, 0));  // nie POI
    QVERIFY(f.scene.split_polyline(1, 0, 0, 1));
    QCOMPARE(f.stack.count(), 1);
    QCOMPARE(f.map->objects().size(), size_t{3});
    QCOMPARE(f.node_count(1), size_t{2});
    QCOMPARE(f.node_count(2), size_t{2});
    QVERIFY(f.node(1, 0, 1).pos() == f.node(2, 0, 0).pos());
    QVERIFY(f.scene.item_for_object(2) && f.scene.item_for_object(2)->graphics_item()->isVisible());
    QVERIFY(f.map->objects()[2].label1 == f.map->objects()[1].label1);
    const std::string split = f.map->to_mp_string();

    f.stack.undo();
    QCOMPARE(f.map->to_mp_string(), f.original);
    QVERIFY(!f.scene.item_for_object(2)->graphics_item()->isVisible());
    f.stack.redo();
    QCOMPARE(f.map->to_mp_string(), split);

    // polaczenie z powrotem: wlasciwosci z pierwszej zaznaczonej linii
    f.scene.set_tool(Tool::SelectObjects);
    std::vector<const DataX*> data{&*f.map->objects()[1].data, &*f.map->objects()[2].data};
    MergeResult merged = DataX::merge_polylines(data);
    f.scene.merge_objects({1, 2}, std::move(merged.data), "merge");
    QCOMPARE(f.node_count(1), size_t{3});
    QVERIFY(f.map->objects()[2].deleted);
    QVERIFY(f.polyline()->graphics_item()->isSelected());
    f.stack.undo();
    QCOMPARE(f.map->to_mp_string(), split);
    f.stack.undo();
    QCOMPARE(f.map->to_mp_string(), f.original);
}

void EditTests::grip_drag_ctrl_click_and_split_key() {
    ViewFixture f;
    f.scene.set_tool(Tool::EditNodes);
    f.select_only(f.polyline());
    const PointF n1 = f.node(1, 0, 1).pos();
    const QPoint grip = f.view_pos(n1);

    // przeciagniecie uchwytu: podglad w trakcie, jedna komenda po puszczeniu
    QTest::mousePress(f.vp(), Qt::LeftButton, Qt::NoModifier, grip);
    for (int d = 5; d <= 20; d += 5) QTest::mouseMove(f.vp(), grip + QPoint(d, d));
    QTest::mouseRelease(f.vp(), Qt::LeftButton, Qt::NoModifier, grip + QPoint(20, 20));
    QTRY_COMPARE(f.stack.count(), 1);
    const QPointF expected = f.view.mapToScene(grip + QPoint(20, 20)) - f.view.mapToScene(grip);
    QVERIFY(qAbs(f.node(1, 0, 1).x() - n1.x - expected.x()) < 1e-6);
    QVERIFY(qAbs(f.node(1, 0, 1).y() - n1.y - expected.y()) < 1e-6);
    QVERIFY(f.poly(1)->isSelected() && f.poly(1)->decorated());
    f.stack.undo();
    QCOMPARE(f.map->to_mp_string(), f.original);

    // Ctrl+klik na uchwycie usuwa wezel
    QTest::mouseClick(f.vp(), Qt::LeftButton, Qt::ControlModifier, grip);
    QTRY_COMPARE(f.stack.index(), 1);
    QTest::qWait(20);
    QCOMPARE(f.stack.count(), 1);  // tylko usuniecie wezla, bez pustego przesuniecia
    QCOMPARE(f.node_count(1), size_t{2});
    f.stack.undo();
    QCOMPARE(f.node_count(1), size_t{3});

    // klawisz 's' nad uchwytem dzieli linie; w tym czasie skroty jednoliterowe sa wylaczane
    QSignalSpy hover_spy(&f.scene, &MapScene::grip_hover_changed);
    QTest::mouseMove(f.vp(), grip);
    QTRY_VERIFY(!hover_spy.isEmpty());
    QCOMPARE(hover_spy.last().at(0).toBool(), true);
    QTest::keyClick(f.vp(), Qt::Key_S);
    QTRY_COMPARE(f.map->objects().size(), size_t{3});
    QCOMPARE(f.node_count(1), size_t{2});
    // uchwyty zostaly przebudowane, wiec uchwyt pod kursorem zniknal - skroty wracaja
    QCOMPARE(hover_spy.last().at(0).toBool(), false);
    f.stack.undo();
    QCOMPARE(f.map->to_mp_string(), f.original);
}

void EditTests::shift_click_inserts_node() {
    ViewFixture f;
    f.scene.set_tool(Tool::EditNodes);
    f.select_only(f.polyline());
    const PointF a = f.node(1, 0, 0).pos(), b = f.node(1, 0, 1).pos();
    const QPoint mid = f.view_pos(PointF{(a.x + b.x) / 2, (a.y + b.y) / 2});
    QTest::mouseClick(f.vp(), Qt::LeftButton, Qt::ShiftModifier, mid);
    QCOMPARE(f.stack.count(), 1);
    QCOMPARE(f.node_count(1), size_t{4});
    // nowy wezel lezy na odcinku miedzy wezlami 0 i 1
    const PointF n = f.node(1, 0, 1).pos();
    const double cross = (b.x - a.x) * (n.y - a.y) - (b.y - a.y) * (n.x - a.x);
    QVERIFY(qAbs(cross) < 1e-3 * QLineF(a.x, a.y, b.x, b.y).length());
    // daleko od krawedzi Shift+klik nic nie dodaje
    QTest::mouseClick(f.vp(), Qt::LeftButton, Qt::ShiftModifier, mid + QPoint(0, 200));
    QCOMPARE(f.stack.count(), 1);
    f.stack.undo();
    QCOMPARE(f.map->to_mp_string(), f.original);
}

void EditTests::dock_follows_selection() {
    DockFixture f;
    QVERIFY(!f.dock.shown_object());
    QVERIFY(!f.dock.tabs()->isTabEnabled(PropertiesDock::MainTab));
    f.select_only(f.poi());
    QCOMPARE(f.dock.shown_object(), std::optional<size_t>(0));
    QVERIFY(f.dock.tabs()->isTabEnabled(PropertiesDock::AddressTab));
    QVERIFY(!f.dock.tabs()->isTabEnabled(PropertiesDock::RoutingTab));
    QCOMPARE(f.dock.label_edit(1)->text(), QString("Stacja"));
    f.select_only(f.polyline());
    QCOMPARE(f.dock.shown_object(), std::optional<size_t>(1));
    QVERIFY(!f.dock.tabs()->isTabEnabled(PropertiesDock::AddressTab));
    QVERIFY(f.dock.tabs()->isTabEnabled(PropertiesDock::RoutingTab));
    QCOMPARE(f.dock.tabs()->currentIndex(), int(PropertiesDock::MainTab));
    QCOMPARE(f.dock.label_edit(1)->text(), QString("Ulica"));
    QVERIFY(f.dock.dir_indicator()->isChecked());
    f.poi()->graphics_item()->setSelected(true);  // kilka obiektow - panel pusty
    QVERIFY(!f.dock.shown_object());
    QCOMPARE(f.dock.tabs()->currentIndex(), int(PropertiesDock::MainTab));
}

void EditTests::dock_labels_endlevel_direction() {
    DockFixture f;
    f.select_only(f.polyline());
    f.edit_line(f.dock.label_edit(1), QString::fromUtf8("Górczewska"));
    QCOMPARE(f.stack.count(), 1);
    QCOMPARE(*f.obj(1).label1, std::string("G\xf3rczewska"));  // cp1250
    f.edit_line(f.dock.label_edit(1), QString::fromUtf8("Górczewska"));  // bez zmiany - bez komendy
    QCOMPARE(f.stack.count(), 1);
    f.edit_line(f.dock.label_edit(2), "Druga");
    QCOMPARE(*f.obj(1).label2, std::string("Druga"));

    emit f.dock.end_level()->activated(3);
    QCOMPARE(f.obj(1).endlevel, 3LL);

    f.dock.dir_indicator()->click();
    QVERIFY(!f.obj(1).dirindicator);
    QCOMPARE(f.stack.count(), 4);

    f.stack.undo();
    QVERIFY(f.obj(1).dirindicator);
    QVERIFY(f.dock.dir_indicator()->isChecked());
    f.stack.undo();
    f.stack.undo();
    QVERIFY(!f.obj(1).label2);
    QCOMPARE(f.dock.label_edit(2)->text(), QString());
    f.stack.undo();
    QCOMPARE(f.dock.label_edit(1)->text(), QString("Ulica"));
    QCOMPARE(f.map->to_mp_string(), f.original);
}

void EditTests::dock_endlevel_digit_keys() {
    // Lista EndLevel z fokusem: cyfra wybiera EndLevel obiektu, a globalny skrot poziomu mapy (View->Levels)
    // nie odpala. Bez fokusu na liscie skrot dziala jak dotad.
    QWidget window;  // przed f: panel (dziecko okna) niszczony pierwszy i sam odpina sie od okna
    DockFixture f;
    auto* layout = new QVBoxLayout(&window);
    auto* other = new QLineEdit(&window);
    layout->addWidget(other);
    layout->addWidget(&f.dock);
    int level_shortcut = -1;
    for (int level = 0; level < 5; ++level) {
        auto* act = new QAction(&window);
        act->setShortcut(QKeySequence(QString::number(level)));
        QObject::connect(act, &QAction::triggered, [&level_shortcut, level] { level_shortcut = level; });
        window.addAction(act);
    }
    window.show();
    QApplication::setActiveWindow(&window);
    QVERIFY(QTest::qWaitForWindowActive(&window));
    f.select_only(f.polyline());

    f.dock.end_level()->setFocus();
    QTest::keyClick(f.dock.end_level(), Qt::Key_2);
    QCOMPARE(f.obj(1).endlevel, 2LL);
    QCOMPARE(level_shortcut, -1);
    QTest::keyClick(f.dock.end_level(), Qt::Key_5);  // 5 tez, choc nie ma takiego poziomu mapy
    QCOMPARE(f.obj(1).endlevel, 5LL);
    QCOMPARE(f.dock.end_level()->currentIndex(), 5);
    const int commands = f.stack.count();
    QTest::keyClick(f.dock.end_level(), Qt::Key_5);  // ten sam poziom - bez komendy
    QCOMPARE(f.stack.count(), commands);

    window.setFocus();
    QTest::keyClick(&window, Qt::Key_3);
    QCOMPARE(level_shortcut, 3);
    QCOMPARE(f.obj(1).endlevel, 5LL);
}

void EditTests::dock_type_comment_extras() {
    DockFixture f;
    f.select_only(f.polyline());
    QComboBox* type = f.dock.type_selector();
    QCOMPARE(type->currentData().toLongLong(), 0x6LL);
    const int motorway = type->findData(QVariant::fromValue<long long>(0x1));
    QVERIFY(motorway >= 0);
    type->setCurrentIndex(motorway);
    emit type->activated(motorway);
    QCOMPARE(*f.obj(1).type, 0x1LL);
    QVERIFY(f.map->to_mp_string().find("Type=0x1\n") != std::string::npos);
    // element dostal wyglad nowego typu (widac po odznaczeniu)
    f.scene.clearSelection();
    auto* line = static_cast<QGraphicsPathItem*>(f.polyline()->graphics_item());
    QCOMPARE(line->pen().color(), f.styles.polyline_pen(0x1).color());
    QVERIFY(line->pen().color() != f.styles.polyline_pen(0x6).color());
    f.select_only(f.polyline());

    QPlainTextEdit* comment = f.dock.comment();
    QFocusEvent focus_in(QEvent::FocusIn), focus_out(QEvent::FocusOut);
    QCoreApplication::sendEvent(comment, &focus_in);
    comment->setPlainText(QString::fromUtf8("pierwsza\nłódź\n\n"));
    QCoreApplication::sendEvent(comment, &focus_out);
    QVERIFY(f.obj(1).comment);
    QCOMPARE(f.obj(1).comment->size(), size_t{2});
    QCOMPARE(f.obj(1).comment->at(1), std::string("\xb3\xf3\x64\x9f"));

    QTableWidget* extras = f.dock.extras();
    QCOMPARE(extras->rowCount(), 1);  // tylko pusty wiersz na nowy wpis
    extras->setItem(0, 0, new QTableWidgetItem("Miasto"));
    extras->setItem(0, 1, new QTableWidgetItem("Wola"));
    emit extras->cellChanged(0, 1);
    QCOMPARE(f.obj(1).others.size(), size_t{1});
    QCOMPARE(f.obj(1).others[0].first, std::string("Miasto"));
    QCOMPARE(extras->rowCount(), 2);
    QCOMPARE(f.stack.count(), 3);

    f.stack.undo();
    f.stack.undo();
    f.stack.undo();
    QCOMPARE(f.map->to_mp_string(), f.original);
    QCOMPARE(type->currentData().toLongLong(), 0x6LL);
}

void EditTests::dock_address_and_routing() {
    DockFixture f;
    f.select_only(f.poi());
    f.edit_line(f.dock.street_desc(), "Prosta");
    f.edit_line(f.dock.house_number(), "12a");
    f.edit_line(f.dock.phone(), "123");
    QCOMPARE(*f.obj(0).streetdesc, std::string("Prosta"));
    QCOMPARE(*f.obj(0).housenumber, std::string("12a"));
    QCOMPARE(*f.obj(0).phone, std::string("123"));

    f.select_only(f.polyline());
    QVERIFY(!f.obj(1).routeparam);
    f.dock.route_check(2)->click();  // One way
    QVERIFY(f.obj(1).routeparam);
    QCOMPARE((*f.obj(1).routeparam)[2], 1LL);
    f.dock.route_combo(0)->setCurrentIndex(4);
    emit f.dock.route_combo(0)->activated(4);
    QCOMPARE((*f.obj(1).routeparam)[0], 4LL);
    QVERIFY(f.map->to_mp_string().find("RouteParam=4,0,1,0,0,0,0,0,0,0,0,0") != std::string::npos);
    QCOMPARE(f.stack.count(), 5);
    for (int i = 0; i < 5; ++i) f.stack.undo();
    QCOMPARE(f.map->to_mp_string(), f.original);
}

void EditTests::dock_node_hlevel_and_numbers() {
    DockFixture f;
    f.scene.set_tool(Tool::EditNodes);
    f.select_only(f.polyline());
    QVERIFY(!f.dock.shows_node());
    f.scene.set_active_grip(1, 0, 0, 1);
    QVERIFY(f.dock.shows_node());
    QCOMPARE(f.dock.tabs()->currentIndex(), int(PropertiesDock::NodesTab));
    QVERIFY(!f.dock.tabs()->isTabEnabled(PropertiesDock::MainTab));
    QVERIFY(!f.dock.node_has_numbers()->isChecked());

    QComboBox* hlevel = f.dock.node_hlevel();
    const int two = hlevel->findData(QVariant::fromValue<long long>(2));
    hlevel->setCurrentIndex(two);
    emit hlevel->activated(two);
    QCOMPARE(f.node(1, 0, 1).hlevel(), OptInt(2));
    QVERIFY(f.dock.shows_node());  // po zmianie panel dalej pokazuje ten wezel
    QCOMPARE(hlevel->currentIndex(), two);

    // numeracja w wezle srodkowym: wartosci wyliczone z odcinka 1-5 / 2-6
    f.dock.node_has_numbers()->click();
    QVERIFY(f.node(1, 0, 1).numbers() != nullptr);
    QVERIFY(f.dock.node_has_numbers()->isChecked());
    f.dock.number_after(true)->setText("31");
    emit f.dock.number_after(true)->editingFinished();
    QCOMPARE(f.node(1, 0, 1).numbers()->left_side_number_after, OptInt(31));
    QCOMPARE(f.stack.count(), 3);

    f.dock.node_has_numbers()->click();
    QVERIFY(f.node(1, 0, 1).numbers() == nullptr);
    for (int i = 0; i < 4; ++i) f.stack.undo();
    QCOMPARE(f.map->to_mp_string(), f.original);
    QCOMPARE(f.dock.node_hlevel()->currentIndex(), 0);
}

void EditTests::dock_numbers_on_road_without_numbering() {
    // Droga bez numeracji: pusta numeracja nie zmienia rekordu MP, wiec checkbox nie moze sie od razu odznaczac
    // (wczesniej odznaczal sie i pola zostawaly wylaczone). Jak w Pythonie numeracje zapisuje dopiero wybor stylu.
    DockFixture f;
    QMimeData mime;
    mime.setText("[POLYLINE]\nType=0x6\nData0=(52.1000,21.0000),(52.1005,21.0010),(52.1010,21.0020)\n[END]\n");
    QCOMPARE(f.scene.paste(&mime, std::nullopt), 1);
    const size_t obj = f.map->objects().size() - 1;
    const int start = f.stack.count();
    f.scene.set_tool(Tool::EditNodes);
    f.scene.clearSelection();
    f.scene.item_for_object(obj)->graphics_item()->setSelected(true);
    f.scene.set_active_grip(obj, 0, 0, 0);
    QVERIFY(f.dock.shows_node());
    QVERIFY(!f.dock.node_has_numbers()->isChecked());
    QVERIFY(!f.dock.number_after(true)->isEnabled());

    f.dock.node_has_numbers()->click();
    QVERIFY(f.dock.node_has_numbers()->isChecked());
    QVERIFY(f.dock.numbering_style(true)->isEnabled());
    QVERIFY(!f.dock.number_after(true)->isEnabled());  // styl None: bez numeru poczatkowego
    QCOMPARE(f.stack.count(), start);  // jeszcze nic do zapisania

    // wybor stylu (nieparzyste) zapisuje numeracje z numerem poczatkowym 0, potem wpisany numer
    QComboBox* style = f.dock.numbering_style(true);
    style->setCurrentIndex(2);
    emit style->activated(2);
    QCOMPARE(f.stack.count(), start + 1);
    QCOMPARE(f.node(obj, 0, 0).numbers()->left_side_numbering_style, OptStr("O"));
    QVERIFY(f.dock.number_after(true)->isEnabled());
    f.dock.number_after(true)->setText("1");
    emit f.dock.number_after(true)->editingFinished();
    QCOMPARE(f.node(obj, 0, 0).numbers()->left_side_number_after, OptInt(1));
    QVERIFY(f.dock.node_has_numbers()->isChecked());
    bool found = false;
    for (const std::string& line : f.map->objects()[obj].to_mp_record(f.map->precision()))
        if (line.rfind("Numbers1=0,O,1,", 0) == 0) found = true;
    QVERIFY(found);

    // wybor "None" wylacza numeracje strony: czysci numer poczatkowy (wczesniej zostawal i numeracja trwala)
    style->setCurrentIndex(0);
    emit style->activated(0);
    QVERIFY(f.dock.number_after(true)->text().isEmpty());
    QVERIFY(!f.dock.number_after(true)->isEnabled());
    QVERIFY(!f.node(obj, 0, 0).starts_numeration());
    for (const std::string& line : f.map->objects()[obj].to_mp_record(f.map->precision()))
        QVERIFY(line.rfind("Numbers1=", 0) != 0);
    // wezel bez numerow nie ma numeracji: zadnej pustej definicji ani numeru "przed" na koncu linii,
    // checkbox odznaczony (wczesniej zostawal zaznaczony i nie dawal sie odznaczyc)
    QVERIFY(f.node(obj, 0, 0).numbers() == nullptr);
    QVERIFY(f.node(obj, 0, 2).numbers() == nullptr);
    QVERIFY(!f.dock.node_has_numbers()->isChecked());
    f.dock.node_has_numbers()->click();
    QVERIFY(f.dock.node_has_numbers()->isChecked());
    style->setCurrentIndex(2);
    emit style->activated(2);
    QCOMPARE(f.node(obj, 0, 0).numbers()->left_side_number_after, OptInt(0));

    // odznaczenie usuwa numeracje
    f.dock.node_has_numbers()->click();
    QVERIFY(!f.dock.node_has_numbers()->isChecked());
    QVERIFY(f.node(obj, 0, 0).numbers() == nullptr);
}

void EditTests::ctrl_click_last_node_with_dock() {
    // Ctrl+klik na ostatnim wezle: aktywny wezel wskazywal poza linie i panel wywracal program (MpError)
    DockFixture f;
    MapView view{&f.scene};
    view.set_projection(&f.map->projection());
    view.resize(800, 600);
    view.show();
    QVERIFY(QTest::qWaitForWindowExposed(&view));
    const PointF a = f.node(1, 0, 1).pos(), b = f.node(1, 0, 2).pos();
    view.centerOn(QPointF((a.x + b.x) / 2, (a.y + b.y) / 2));
    f.scene.set_tool(Tool::EditNodes);
    f.select_only(f.polyline());
    const QPoint last = view.mapFromScene(QPointF(b.x, b.y));
    QTest::mouseMove(view.viewport(), last);
    QTest::mouseClick(view.viewport(), Qt::LeftButton, Qt::ControlModifier, last);
    QTRY_COMPARE(f.stack.count(), 1);
    QCOMPARE(f.node_count(1), size_t{2});
    QVERIFY(!f.scene.active_grip());
    QVERIFY(!f.dock.shows_node());

    // ten sam przypadek przez undo: aktywny ostatni wezel, cofniecie dodania wezla
    f.stack.undo();
    QCOMPARE(f.node_count(1), size_t{3});
    QVERIFY(f.scene.insert_node(1, 0, 0, 3, QPointF(b.x + 10, b.y)));
    f.scene.set_active_grip(1, 0, 0, 3);
    QVERIFY(f.dock.shows_node());
    f.stack.undo();
    QVERIFY(!f.scene.active_grip());
    QCOMPARE(f.map->to_mp_string(), f.original);
}

void EditTests::dock_elements_highlight() {
    DockFixture f;
    f.select_only(f.polyline());
    QTreeWidget* tree = f.dock.elements();
    QCOMPARE(tree->topLevelItemCount(), 2);  // Data0, Data1
    QCOMPARE(tree->topLevelItem(0)->text(0), QString("Data0"));
    QTreeWidgetItem* poly = tree->topLevelItem(0)->child(0);
    QCOMPARE(poly->text(3), QString("3"));
    auto highlighted = [&] {
        int n = 0;
        for (QGraphicsItem* item : f.scene.items())
            if (item->zValue() == HIGHLIGHTED_POLY_Z_VAL) ++n;
        return n;
    };
    QCOMPARE(highlighted(), 0);
    poly->setSelected(true);
    QCOMPARE(highlighted(), 1);
    f.scene.clearSelection();
    QCOMPARE(highlighted(), 0);
}

void EditTests::copy_paste_at_cursor_and_undo() {
    Fixture f;
    f.select_only(f.polyline());
    const PointF n0 = f.node(1, 0, 0).pos();
    const PointF level1 = f.node(1, 1, 0).pos();
    std::unique_ptr<QMimeData> mime(f.scene.copy_selected(QPointF(n0.x, n0.y)));
    QVERIFY(mime);
    QVERIFY(mime->hasFormat("application/json"));
    QVERIFY(mime->text().startsWith("[POLYLINE]\nType=0x6\nLabel=Ulica\n"));
    // format jak w Pythonie: [MouseScenePos=x,y, linie rekordu..., [END]]
    const QJsonArray records = QJsonDocument::fromJson(mime->data("application/json")).array();
    QCOMPARE(records.size(), 1);
    QVERIFY(records[0].toArray().first().toString().startsWith("MouseScenePos="));
    QCOMPARE(records[0].toArray().last().toString(), QString("[END]"));

    QCOMPARE(f.scene.paste(mime.get(), QPointF(n0.x + 10, n0.y - 5)), 1);
    QCOMPARE(f.stack.count(), 1);
    QCOMPARE(f.map->objects().size(), size_t{3});
    const MapObject& pasted = f.map->objects()[2];
    QCOMPARE(*pasted.label1, std::string("Ulica"));
    QVERIFY(pasted.dirindicator);
    QVERIFY(qAbs(f.node(2, 0, 0).x() - (n0.x + 10)) < 1e-6);
    QVERIFY(qAbs(f.node(2, 0, 0).y() - (n0.y - 5)) < 1e-6);
    // przesuwane sa wszystkie poziomy
    QVERIFY(qAbs(f.node(2, 1, 0).x() - (level1.x + 10)) < 1e-6);
    QVERIFY(f.node(1, 0, 0).pos() == n0);  // oryginal bez zmian
    QVERIFY(f.scene.item_for_object(2)->graphics_item()->isSelected());
    QVERIFY(!f.polyline()->graphics_item()->isSelected());
    const std::string after_paste = f.map->to_mp_string();

    f.stack.undo();
    QCOMPARE(f.map->to_mp_string(), f.original);
    QVERIFY(!f.scene.item_for_object(2)->graphics_item()->isVisible());
    f.stack.redo();
    QCOMPARE(f.map->to_mp_string(), after_paste);
}

void EditTests::copy_paste_several_objects() {
    Fixture f;
    f.poi()->graphics_item()->setSelected(true);
    f.polyline()->graphics_item()->setSelected(true);
    std::unique_ptr<QMimeData> mime(f.scene.copy_selected(QPointF(0, 0)));
    QCOMPARE(f.scene.paste(mime.get(), QPointF(3, 4)), 2);
    QCOMPARE(f.stack.count(), 1);
    QCOMPARE(f.stack.text(0), QString("Wklej obiekty (2)"));
    QCOMPARE(f.map->objects()[2].kind(), ObjectKind::Poi);
    QCOMPARE(f.map->objects()[3].kind(), ObjectKind::Polyline);
    QCOMPARE(f.scene.selected_object_items().size(), size_t{2});
    // obiekty przesuniete o ten sam wektor - wzajemne polozenie zachowane
    QVERIFY(qAbs(f.node(2, 0, 0).x() - f.node(0, 0, 0).x() - 3) < 1e-6);
    QVERIFY(qAbs(f.node(3, 0, 0).y() - f.node(1, 0, 0).y() - 4) < 1e-6);
    f.stack.undo();
    QCOMPARE(f.map->to_mp_string(), f.original);
}

void EditTests::paste_plain_text_keeps_position() {
    Fixture f;
    QMimeData mime;
    mime.setText(QString::fromUtf8("[POI]\nType=0x2f00\nLabel=Łódź\nData0=(52.10000,21.00000)\n[END]\n\n"
                                   "tekst bez rekordu\n"));
    QCOMPARE(f.scene.paste(&mime, QPointF(100, 100)), 1);
    QCOMPARE(*f.map->objects()[2].label1, std::string("\xa3\xf3\x64\x9f"));
    QVERIFY(f.node(2, 0, 0).pos() == f.node(0, 0, 0).pos());  // bez MouseScenePos - oryginalne miejsce
    QMimeData empty;
    QCOMPARE(f.scene.paste(&empty, QPointF()), 0);
    QCOMPARE(f.stack.count(), 1);
}

void EditTests::copy_without_selection_gives_nothing() {
    Fixture f;
    QVERIFY(f.scene.copy_selected(QPointF()) == nullptr);
}

void EditTests::create_poi_with_click() {
    ViewFixture f;
    f.scene.set_last_used_type(ObjectKind::Poi, 0x2f00);
    f.scene.set_tool(Tool::CreatePoint);
    const QPoint click = f.view_pos(f.node(1, 0, 1).pos()) + QPoint(60, 0);
    const QPointF expected = f.view.mapToScene(click);
    QTest::mouseClick(f.vp(), Qt::LeftButton, Qt::NoModifier, click);
    QCOMPARE(f.stack.count(), 1);
    QCOMPARE(f.stack.text(0), QString::fromUtf8("Utwórz POI"));
    QCOMPARE(f.map->objects().size(), size_t{3});
    const MapObject& poi = f.map->objects()[2];
    QCOMPARE(poi.kind(), ObjectKind::Poi);
    QCOMPARE(*poi.type, 0x2f00LL);
    QVERIFY(qAbs(f.node(2, 0, 0).x() - expected.x()) < 1e-3);
    QVERIFY(qAbs(f.node(2, 0, 0).y() - expected.y()) < 1e-3);
    // po utworzeniu: narzedzie zaznaczania i zaznaczony nowy obiekt
    QCOMPARE(f.scene.tool(), Tool::SelectObjects);
    QVERIFY(f.scene.item_for_object(2)->graphics_item()->isSelected());
    // zapis z precyzja mapy (5 miejsc), a nie z 10 uzytymi przy tworzeniu
    QVERIFY(f.map->to_mp_string().find("Data0=(52.10000,21.00000)") != std::string::npos);
    f.stack.undo();
    QCOMPARE(f.map->to_mp_string(), f.original);
}

void EditTests::create_polyline_and_polygon_with_keys() {
    ViewFixture f;
    f.scene.set_tool(Tool::CreatePolyline);
    const QPoint base = f.view_pos(f.node(1, 0, 1).pos()) + QPoint(40, 0);
    QTest::mouseClick(f.vp(), Qt::LeftButton, Qt::NoModifier, base);
    QTest::keyClick(f.vp(), Qt::Key_Return);  // jeden wezel - za malo
    QCOMPARE(f.stack.count(), 0);
    QTest::mouseClick(f.vp(), Qt::LeftButton, Qt::NoModifier, base + QPoint(30, 0));
    QTest::mouseClick(f.vp(), Qt::LeftButton, Qt::NoModifier, base + QPoint(30, 30));
    QCOMPARE(f.view.creation_nodes().size(), size_t{3});
    QTest::keyClick(f.vp(), Qt::Key_Backspace);
    QCOMPARE(f.view.creation_nodes().size(), size_t{2});
    QTest::keyClick(f.vp(), Qt::Key_Return);
    QCOMPARE(f.stack.count(), 1);
    QCOMPARE(f.map->objects()[2].kind(), ObjectKind::Polyline);
    QCOMPARE(f.node_count(2), size_t{2});
    QVERIFY(f.view.creation_nodes().empty());
    QCOMPARE(f.scene.tool(), Tool::SelectObjects);

    f.scene.set_tool(Tool::CreatePolygon);
    QTest::mouseClick(f.vp(), Qt::LeftButton, Qt::NoModifier, base + QPoint(0, 60));
    QTest::mouseClick(f.vp(), Qt::LeftButton, Qt::NoModifier, base + QPoint(30, 60));
    QTest::keyClick(f.vp(), Qt::Key_Return);  // polygon wymaga 3 wezlow
    QCOMPARE(f.stack.count(), 1);
    f.view.creation_add_node();  // Insert: wezel pod kursorem
    QTest::mouseMove(f.vp(), base + QPoint(15, 90));
    f.view.creation_add_node();
    QTest::keyClick(f.vp(), Qt::Key_Return);
    QCOMPARE(f.stack.count(), 2);
    QCOMPARE(f.map->objects()[3].kind(), ObjectKind::Polygon);
    QCOMPARE(f.node_count(3), size_t{4});

    // Esc / zmiana narzedzia porzuca rysowany obiekt
    f.scene.set_tool(Tool::CreatePolyline);
    QTest::mouseClick(f.vp(), Qt::LeftButton, Qt::NoModifier, base);
    QCOMPARE(f.view.creation_nodes().size(), size_t{1});
    f.scene.set_tool(Tool::SelectObjects);
    QVERIFY(f.view.creation_nodes().empty());
    f.stack.undo();
    f.stack.undo();
    QCOMPARE(f.map->to_mp_string(), f.original);
}

void EditTests::create_circle() {
    ViewFixture f;
    f.scene.set_tool(Tool::CreatePolylineCircle);
    const QPoint first = f.view_pos(f.node(1, 0, 1).pos()) + QPoint(50, 0);
    QTest::mouseClick(f.vp(), Qt::LeftButton, Qt::NoModifier, first);
    QTest::mouseMove(f.vp(), first + QPoint(80, 0));
    QTest::mouseClick(f.vp(), Qt::LeftButton, Qt::NoModifier, first + QPoint(80, 0));
    QCOMPARE(f.stack.count(), 1);
    const MapObject& circle = f.map->objects()[2];
    QCOMPARE(circle.kind(), ObjectKind::Polyline);
    const size_t n = f.node_count(2);
    QVERIFY2(n > 4, qPrintable(QString::number(n)));
    QVERIFY(f.node(2, 0, 0).pos() == f.node(2, 0, n - 1).pos());  // okrag zamkniety
    // wszystkie wezly w tej samej odleglosci od srodka
    const QPointF center = f.view.mapToScene(first + QPoint(80, 0));
    const double r0 = std::hypot(f.node(2, 0, 0).x() - center.x(), f.node(2, 0, 0).y() - center.y());
    for (size_t i = 0; i < n; ++i) {
        const double r = std::hypot(f.node(2, 0, i).x() - center.x(), f.node(2, 0, i).y() - center.y());
        QVERIFY(qAbs(r - r0) < 1e-3 * r0);
    }
}

void EditTests::snap_to_node_when_creating() {
    ViewFixture f;
    f.scene.set_tool(Tool::CreatePoint);
    const PointF n1 = f.node(1, 0, 1).pos();
    const QPoint near = f.view_pos(n1) + QPoint(6, 4);
    QTest::mouseMove(f.vp(), near, -1);
    QMouseEvent move(QEvent::MouseMove, QPointF(near), f.vp()->mapToGlobal(QPointF(near)), Qt::NoButton,
                     Qt::NoButton, Qt::ControlModifier);
    QCoreApplication::sendEvent(f.vp(), &move);
    QVERIFY(f.scene.snap_indicator_visible());
    QTest::mouseClick(f.vp(), Qt::LeftButton, Qt::ControlModifier, near);
    QCOMPARE(f.stack.count(), 1);
    QVERIFY(qAbs(f.node(2, 0, 0).x() - n1.x) < 1e-3);
    QVERIFY(qAbs(f.node(2, 0, 0).y() - n1.y) < 1e-3);
    // bez Ctrl - punkt pod kursorem
    f.scene.set_tool(Tool::CreatePoint);
    QTest::mouseClick(f.vp(), Qt::LeftButton, Qt::NoModifier, near);
    const QPointF under = f.view.mapToScene(near);
    QVERIFY(qAbs(f.node(3, 0, 0).x() - under.x()) < 1e-3);
}

void EditTests::snap_grip_to_other_object() {
    ViewFixture f;
    // druga polilinia obok pierwszej (kopia przesunieta), potem przeciagniecie jej wezla z Ctrl do wezla pierwszej
    f.select_only(f.polyline());
    std::unique_ptr<QMimeData> mime(f.scene.copy_selected(QPointF(0, 0)));
    const PointF n1 = f.node(1, 0, 1).pos();
    // wklejenie 40 pikseli w prawo (punkt odniesienia (0, 0))
    f.scene.paste(mime.get(), f.view.mapToScene(QPoint(40, 0)) - f.view.mapToScene(QPoint(0, 0)));
    QCOMPARE(f.map->objects().size(), size_t{3});
    f.scene.set_tool(Tool::EditNodes);
    f.select_only(f.scene.item_for_object(2));
    const QPoint grip = f.view_pos(f.node(2, 0, 1).pos());
    const QPoint target = f.view_pos(n1) + QPoint(3, 3);
    QTest::mousePress(f.vp(), Qt::LeftButton, Qt::NoModifier, grip);
    QTest::mouseMove(f.vp(), (grip + target) / 2);
    QMouseEvent move(QEvent::MouseMove, QPointF(target), f.vp()->mapToGlobal(QPointF(target)), Qt::NoButton,
                     Qt::LeftButton, Qt::ControlModifier);
    QCoreApplication::sendEvent(f.vp(), &move);
    QVERIFY(f.scene.snap_indicator_visible());
    QTest::mouseRelease(f.vp(), Qt::LeftButton, Qt::ControlModifier, target);
    QTRY_COMPARE(f.stack.count(), 2);
    QVERIFY(qAbs(f.node(2, 0, 1).x() - n1.x) < 1e-9);
    QVERIFY(qAbs(f.node(2, 0, 1).y() - n1.y) < 1e-9);
    QVERIFY(!f.scene.snap_indicator_visible());
}

void EditTests::web_layer_download_cache_and_toggle() {
    ViewFixture f;
    MapRuler ruler(&f.view, &f.map->projection());
    f.view.set_ruler(&ruler);
    QTemporaryDir cache, source;
    QVERIFY(cache.isValid() && source.isValid());
    // "serwer" kafelkow: lokalny obrazek 256x256 (bez sieci)
    const QString tile_png = source.filePath("tile.png");
    QImage image(256, 256, QImage::Format_RGB32);
    image.fill(Qt::darkCyan);
    QVERIFY(image.save(tile_png));

    WebLayers web(&f.view);
    web.set_cache_dir(cache.path());
    int requests = 0;
    web.set_url_provider([&](web::Layer, int, int, int) {
        ++requests;
        return QUrl::fromLocalFile(tile_png);
    });
    web.set_layer(web::Layer::Osm);
    QVERIFY(requests > 0);
    QTRY_VERIFY(web.pending_downloads() == 0);
    const int tiles = web.tile_count();
    QCOMPARE(tiles, requests);
    QVERIFY(web.zoom() >= 0 && web.zoom() <= 19);
    // kafelki zapisane w pamieci podrecznej: <warstwa>/<zoom>/<x>/<y>.png
    QVERIFY(QDir(cache.filePath(QString("OSM/%1").arg(web.zoom()))).exists());
    // kafelki pod obiektami mapy i bez obslugi myszy
    int under = 0;
    for (QGraphicsItem* item : f.scene.items())
        if (item->type() == QGraphicsPixmapItem::Type && item->zValue() < 0) {
            ++under;
            QCOMPARE(item->acceptedMouseButtons(), Qt::NoButton);
        }
    QCOMPARE(under, tiles);
    // klikniecie w obiekt nad kafelkiem nadal go zaznacza
    const PointF a = f.node(1, 0, 0).pos(), b = f.node(1, 0, 1).pos();
    QTest::mouseClick(f.vp(), Qt::LeftButton, Qt::NoModifier, f.view_pos(PointF{(a.x + b.x) / 2, (a.y + b.y) / 2}));
    QVERIFY(f.polyline()->graphics_item()->isSelected());

    // wylaczenie usuwa kafelki; ponowne wlaczenie bierze je z pamieci podrecznej (bez pobierania)
    web.set_layer(std::nullopt);
    QCOMPARE(web.tile_count(), 0);
    web.set_layer(web::Layer::Osm);
    QCOMPARE(web.tile_count(), tiles);
    QCOMPARE(requests, tiles);

    // inny zoom: stare kafelki znikaja, nowe sa pobierane
    for (int i = 0; i < 15; ++i) f.view.zoom_in();
    web.update_now();
    QTRY_VERIFY(web.pending_downloads() == 0);
    QVERIFY(requests > tiles);
    QVERIFY(web.tile_count() > 0);
    web.clear();
    QCOMPARE(web.tile_count(), 0);
    f.view.set_ruler(nullptr);
}

void EditTests::extras_copy_paste_between_objects() {
    DockFixture f;
    f.select_only(f.polyline());
    auto set_row = [&](int row, const char* key, const char* value) {
        QTableWidget* t = f.dock.extras();
        t->setItem(row, 0, new QTableWidgetItem(key));
        t->setItem(row, 1, new QTableWidgetItem(value));
        emit t->cellChanged(row, 1);
    };
    set_row(0, "Miasto", "Wola");
    set_row(1, "Plik", "a.txt");
    QCOMPARE(f.obj(1).others.size(), size_t{2});

    f.dock.extras()->selectAll();
    std::unique_ptr<QMimeData> mime(f.dock.copy_extras());
    QVERIFY(mime);
    QCOMPARE(mime->text(), QString("Miasto\tWola\nPlik\ta.txt\n"));

    // Ctrl+Alt+C: cala tabela bez zaznaczania - ten sam wynik co po zaznaczeniu wszystkiego
    f.dock.extras()->clearSelection();
    QVERIFY(!std::unique_ptr<QMimeData>(f.dock.copy_extras()));
    std::unique_ptr<QMimeData> all(f.dock.copy_extras(true));
    QVERIFY(all);
    QCOMPARE(all->text(), mime->text());
    QCOMPARE(all->data("application/json"), mime->data("application/json"));

    // wklejenie do innego obiektu - jedna komenda
    f.select_only(f.poi());
    f.dock.extras()->setCurrentCell(0, 0);
    f.dock.paste_extras(mime.get());
    QCOMPARE(f.obj(0).others.size(), size_t{2});
    QCOMPARE(f.obj(0).others[0], std::make_pair(std::string("Miasto"), std::string("Wola")));
    QCOMPARE(f.stack.count(), 3);

    // tekst "klucz=wartosc" (np. z pliku mp) - dopisany w biezacym wierszu
    QMimeData text;
    text.setText("Typ=droga\n");
    f.dock.extras()->setCurrentCell(2, 0);
    f.dock.paste_extras(&text);
    QCOMPARE(f.obj(0).others.size(), size_t{3});
    QCOMPARE(f.obj(0).others[2].first, std::string("Typ"));

    // obiekty mapy ze schowka (JSON rekordow) nie trafiaja do tabeli
    f.select_only(f.polyline());
    std::unique_ptr<QMimeData> objects(f.scene.copy_selected(QPointF()));
    f.select_only(f.poi());
    f.dock.paste_extras(objects.get());
    QCOMPARE(f.obj(0).others.size(), size_t{3});

    // Delete/wytnij: wyczyszczenie zaznaczonych komorek usuwa wpis
    f.dock.extras()->clearSelection();
    f.dock.extras()->item(0, 1)->setSelected(true);
    f.dock.clear_selected_extras();
    QCOMPARE(f.obj(0).others.size(), size_t{2});
    QCOMPARE(f.obj(0).others[0].first, std::string("Plik"));

    while (f.stack.canUndo()) f.stack.undo();
    QCOMPARE(f.map->to_mp_string(), f.original);
}

namespace {
// Odpowiada na okno pytania (QMessageBox), gdy sie pojawi.
void answer_message_box(QMessageBox::StandardButton button) {
    auto* timer = new QTimer;
    auto tries = std::make_shared<int>(0);
    QObject::connect(timer, &QTimer::timeout, [timer, tries, button] {
        if (auto* box = qobject_cast<QMessageBox*>(QApplication::activeModalWidget())) {
            timer->stop();
            timer->deleteLater();
            box->button(button)->click();
        } else if (++*tries > 200) {
            timer->stop();
            timer->deleteLater();
        }
    });
    timer->start(20);
}
}  // namespace

void EditTests::window_recent_files_and_close_prompt() {
    QTemporaryDir dir;
    QVERIFY(dir.isValid());
    qputenv("PWMAPEDIT_SETTINGS", dir.filePath("settings.ini").toUtf8());
    const QString map_file = dir.filePath("mapa.mp");
    {
        QFile f(map_file);
        QVERIFY(f.open(QIODevice::WriteOnly));
        f.write(SAMPLE_MAP);
    }
    {
        MainWindow w(MapStyles::find_icons_dir());
        w.show();
        QSignalSpy loaded(&w, &MainWindow::map_loaded);
        w.open_file(map_file);
        QVERIFY(loaded.wait(10000));
        QCOMPARE(w.recent_files(), QStringList{QDir::toNativeSeparators(QFileInfo(map_file).absoluteFilePath())});
        QFile saved_before(map_file);
        QVERIFY(saved_before.open(QIODevice::ReadOnly));
        const QByteArray before = saved_before.readAll();
        saved_before.close();

        // zmiana: usuniecie POI
        w.scene()->item_for_object(0)->graphics_item()->setSelected(true);
        w.scene()->delete_selected();

        answer_message_box(QMessageBox::Cancel);  // Anuluj - okno zostaje
        QVERIFY(!w.close());
        QVERIFY(w.isVisible());

        answer_message_box(QMessageBox::Save);  // Zapisz - zapis i zamkniecie
        QVERIFY(w.close());
        // pasek postepu pokazal zapis wszystkich obiektow
        QCOMPARE(w.progress_bar()->maximum(), 2);
        QCOMPARE(w.progress_bar()->value(), 2);
        QFile saved(map_file);
        QVERIFY(saved.open(QIODevice::ReadOnly));
        const QByteArray after = saved.readAll();
        QVERIFY(after != before);
        QVERIFY(!after.contains("[POI]"));
    }
    {
        // nowe okno widzi liste ostatnich plikow; "Nie zapisuj" zamyka bez zapisu
        MainWindow w(MapStyles::find_icons_dir());
        QCOMPARE(w.recent_files().size(), 1);
        w.show();
        QSignalSpy loaded(&w, &MainWindow::map_loaded);
        w.open_file(map_file);
        QVERIFY(loaded.wait(10000));
        w.scene()->item_for_object(0)->graphics_item()->setSelected(true);
        w.scene()->delete_selected();
        QFile f(map_file);
        QVERIFY(f.open(QIODevice::ReadOnly));
        const QByteArray before = f.readAll();
        f.close();
        answer_message_box(QMessageBox::Discard);
        QVERIFY(w.close());
        QVERIFY(f.open(QIODevice::ReadOnly));
        QCOMPARE(f.readAll(), before);
    }
    qunsetenv("PWMAPEDIT_SETTINGS");
}

namespace {
// Slad wzdluz linii z SAMPLE_MAP (52.100,21.000 -> 52.102,21.003) z punktami co ok. 1 m i drobnym szumem,
// druga czesc sladu, trasa i dwa waypointy (jeden z polskimi znakami).
QByteArray sample_gpx() {
    QByteArray gpx = R"(<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="test" xmlns="http://www.topografix.com/GPX/1/1">
  <wpt lat="52.10050" lon="21.00080"><ele>101.5</ele><name>Stacja Łódź</name><cmt>przy drodze</cmt><sym>Fuel</sym></wpt>
  <wpt lat="52.10150" lon="21.00200"><name>Most</name><desc>opis zamiast komentarza</desc></wpt>
  <wpt lat="abc" lon="21.0"><name>zly</name></wpt>
  <trk><name>Przejazd</name><trkseg>
)";
    for (int i = 0; i <= 200; ++i) {
        const double t = i / 200.0;
        const double noise = (i % 2 ? 0.000004 : -0.000004);  // ok. 0,4 m
        gpx += QString("    <trkpt lat=\"%1\" lon=\"%2\"><ele>100</ele><time>2026-11-13T10:00:%3Z</time></trkpt>\n")
                   .arg(52.100 + 0.002 * t + noise, 0, 'f', 7)
                   .arg(21.000 + 0.003 * t, 0, 'f', 7)
                   .arg(i % 60, 2, 10, QChar('0'))
                   .toUtf8();
    }
    gpx += R"(  </trkseg><trkseg>
    <trkpt lat="52.10300" lon="21.00400"/><trkpt lat="52.10310" lon="21.00420"/>
  </trkseg></trk>
  <rte><name>Trasa</name><rtept lat="52.1000" lon="21.0000"><name>A</name></rtept><rtept lat="52.1010" lon="21.0010"/></rte>
  <extensions><foo/></extensions>
</gpx>
)";
    return gpx;
}
}  // namespace

void EditTests::gpx_reader_parses_tracks_waypoints_routes() {
    QString message;
    auto file = read_gpx(sample_gpx(), &message);
    QVERIFY2(file, qPrintable(message));
    QVERIFY(message.contains("1"));  // pominiety waypoint bez wspolrzednych
    QCOMPARE(file->waypoints.size(), size_t{2});
    QCOMPARE(QString::fromStdString(file->waypoints[0].name), QString::fromUtf8("Stacja Łódź"));
    QCOMPARE(file->waypoints[0].comment, std::string("przy drodze"));
    QCOMPARE(file->waypoints[0].symbol, std::string("Fuel"));
    QCOMPARE(*file->waypoints[0].pos.ele, 101.5);
    QCOMPARE(file->waypoints[1].comment, std::string("opis zamiast komentarza"));
    QCOMPARE(file->tracks.size(), size_t{2});
    QCOMPARE(file->tracks[0].name, std::string("Przejazd"));
    QCOMPARE(file->tracks[0].segments.size(), size_t{2});
    QCOMPARE(file->tracks[0].segments[0].size(), size_t{201});
    QVERIFY(file->tracks[0].segments[0][5].time);
    QVERIFY(file->tracks[1].route);
    QCOMPARE(file->tracks[1].segments[0].size(), size_t{2});

    QVERIFY(!read_gpx("<kml></kml>", &message));
    QVERIFY(!read_gpx("<gpx><trk><trkseg><trkpt lat='1' lon='2'>", &message));  // urwany plik
    QVERIFY(message.contains(QString::fromUtf8("Błąd")));
}

void EditTests::gps_layer_items_snapping_and_visibility() {
    ViewFixture f;
    GpsLayers layers(&f.scene);
    auto file = read_gpx(sample_gpx());
    file->path = "test.gpx";
    layers.add_file(std::move(*file));
    QCOMPARE(layers.file_count(), 1);
    int tracks = 0, waypoints = 0;
    for (QGraphicsItem* item : f.scene.items()) {
        if (item->type() == GpsTrackItemType) {
            ++tracks;
            QVERIFY(item->zValue() < 0);
            QCOMPARE(item->acceptedMouseButtons(), Qt::NoButton);
        }
        if (item->type() == GpsWaypointItemType) ++waypoints;
    }
    QCOMPARE(tracks, 3);  // 2 czesci sladu + trasa
    QCOMPARE(waypoints, 2);

    // przyciaganie: kursor kilka pikseli od waypointu "Most" (daleko od obiektow mapy)
    const QPointF most = *layers.waypoint_position(0, 1);
    auto snapped = f.scene.closest_node(most + QPointF(3, -2), 15);
    QVERIFY(snapped);
    QCOMPARE(*snapped, most);
    // klikniecie na sladzie (druga czesc - za koncem drogi, bez obiektow mapy) niczego nie zaznacza
    f.scene.clearSelection();
    const QPointF on_track = layers.segment_path(0, 0, 1).elementAt(0);
    f.view.centerOn(on_track);
    QVERIFY(!f.scene.items(on_track).isEmpty());
    QTest::mouseClick(f.vp(), Qt::LeftButton, Qt::NoModifier, f.view.mapFromScene(on_track));
    QVERIFY(f.scene.selectedItems().isEmpty());

    // ukrycie pliku: elementy niewidoczne i bez przyciagania
    layers.set_visible(0, false);
    QVERIFY(!f.scene.closest_node(most + QPointF(3, -2), 15) || *f.scene.closest_node(most + QPointF(3, -2), 15) != most);
    layers.set_visible(0, true);

    // nowa mapa: elementy usuwane przed wyczyszczeniem sceny i budowane od nowa
    layers.clear_items();
    f.scene.clear_map();
    f.scene.set_map(f.map.get(), &f.styles);
    layers.rebuild_items();
    int after = 0;
    for (QGraphicsItem* item : f.scene.items())
        if (item->type() == GpsTrackItemType || item->type() == GpsWaypointItemType) ++after;
    QCOMPARE(after, 5);
    layers.clear_items();
}

void EditTests::gps_track_to_polyline_and_waypoints_to_pois() {
    Fixture f;
    GpsLayers layers(&f.scene);
    auto file = read_gpx(sample_gpx());
    layers.add_file(std::move(*file));
    f.scene.set_last_used_type(ObjectKind::Polyline, 0x6);
    const size_t before = f.map->objects().size();

    // pierwsza czesc sladu (201 punktow, prosta z szumem 0,4 m) -> polilinia z 2 wezlami przy tolerancji 3 m
    QCOMPARE(layers.create_polylines(0, 0, 0, 3.0), 1);
    QCOMPARE(f.map->objects().size(), before + 1);
    const MapObject& line = f.map->objects()[before];
    QCOMPARE(line.kind(), ObjectKind::Polyline);
    QCOMPARE(*line.type, 0x6LL);
    QCOMPARE(f.node_count(before), size_t{2});
    QVERIFY(layers.file(0).used_segments[0][0]);
    QCOMPARE(f.stack.count(), 1);
    // bez upraszczania - wszystkie punkty
    QCOMPARE(layers.create_polylines(0, 0, 0, 0.0), 1);
    QCOMPARE(f.node_count(before + 1), size_t{201});
    // caly slad (2 czesci) - jedna komenda
    QCOMPARE(layers.create_polylines(0, 0, -1, 3.0), 2);
    QCOMPARE(f.stack.count(), 3);

    // waypointy -> POI z nazwa w Label (cp1250) i komentarzem
    QCOMPARE(layers.create_pois(0, {0, 1}), 2);
    QCOMPARE(f.stack.count(), 4);
    const MapObject& poi = f.map->objects()[f.map->objects().size() - 2];
    QCOMPARE(poi.kind(), ObjectKind::Poi);
    QCOMPARE(*poi.label1, std::string("Stacja \xa3\xf3\x64\x9f"));
    QVERIFY(poi.comment && poi.comment->front() == "przy drodze");
    QVERIFY(layers.file(0).used_waypoints[0] && layers.file(0).used_waypoints[1]);
    // zapis mapy zawiera nowe obiekty, a slady nie
    const std::string saved = f.map->to_mp_string();
    QVERIFY(saved.find("Label=Most") != std::string::npos);
    QVERIFY(saved.find("Przejazd") == std::string::npos);

    while (f.stack.canUndo()) f.stack.undo();
    QCOMPARE(f.map->to_mp_string(), f.original);
}

void EditTests::gps_dock_lists_and_creates() {
    ViewFixture f;
    GpsLayers layers(&f.scene);
    GpsDock dock(&layers, &f.scene, &f.view);
    auto file = read_gpx(sample_gpx());
    file->path = "C:/slady/test.gpx";
    layers.add_file(std::move(*file));
    QTreeWidget* tree = dock.tree();
    QCOMPARE(tree->topLevelItemCount(), 1);
    QTreeWidgetItem* file_item = tree->topLevelItem(0);
    QCOMPARE(file_item->text(0), QString("test.gpx"));
    QCOMPARE(file_item->childCount(), 3);  // slad, trasa, waypointy
    QTreeWidgetItem* track = file_item->child(0);
    QCOMPARE(track->childCount(), 2);  // dwie czesci
    QTreeWidgetItem* wpts = file_item->child(2);
    QCOMPARE(wpts->childCount(), 2);

    // ukrycie przez pole wyboru
    file_item->setCheckState(0, Qt::Unchecked);
    QVERIFY(!layers.file(0).visible);
    file_item->setCheckState(0, Qt::Checked);

    // zaznaczenie podswietla, "Utworz obiekty" tworzy polilinie i POI jedna komenda na rodzaj
    track->child(1)->setSelected(true);
    wpts->child(1)->setSelected(true);
    int highlighted = 0;
    for (QGraphicsItem* item : f.scene.items())
        if (item->zValue() == HIGHLIGHTED_POLY_Z_VAL) ++highlighted;
    QCOMPARE(highlighted, 0);  // dwie pozycje zaznaczone - bez podswietlenia
    const size_t before = f.map->objects().size();
    dock.create_from_selection();
    QCOMPARE(f.map->objects().size(), before + 2);
    QCOMPARE(f.stack.count(), 2);
    // lista pokazuje wykorzystane elementy
    QVERIFY(tree->topLevelItem(0)->child(0)->child(1)->text(0).contains(QString::fromUtf8("użyta")));
    dock.tree()->topLevelItem(0)->setSelected(true);
    dock.remove_selected_file();
    QCOMPARE(layers.file_count(), 0);
    QCOMPARE(tree->topLevelItemCount(), 0);
}

void EditTests::gps_load_gdb_far_from_map() {
    ViewFixture f;
    GpsLayers layers(&f.scene);
    QString warning;
    // plik BaseCamp z polska nazwa; slady leza ok. 60 km od mapy testowej
    const QString path = QString::fromUtf8(PWM_TEST_DATA_DIR "/gdb/Mój zbiór.gdb");
    QCOMPARE(layers.load_file(path, &warning), QString());
    QCOMPARE(layers.file_count(), 1);
    QCOMPARE(layers.file(0).data.tracks.size(), size_t{2});
    // prostokat sceny obejmuje slad, wiec da sie do niego przewinac
    const QPointF first = *layers.first_point(0);
    QVERIFY(f.scene.sceneRect().contains(first));
    f.view.centerOn(first);
    QVERIFY(f.view.mapToScene(f.view.viewport()->rect()).boundingRect().contains(first));
    // zamiana na polilinie dziala tak samo jak dla GPX
    QCOMPARE(layers.create_polylines(0, 1, -1, 3.0), 1);
    QVERIFY(f.node_count(2) > 2 && f.node_count(2) < 1488);
    QCOMPARE(layers.load_file(QString::fromUtf8(PWM_TEST_DATA_DIR "/gdb/nie_ma.gdb")).isEmpty(), false);
    layers.clear_items();
}

void EditTests::elements_move_copy_level_endlevel() {
    DockFixture f;
    f.select_only(f.polyline());
    QSignalSpy messages(&f.dock, &PropertiesDock::message);
    QCOMPARE(f.obj(1).data->data_levels(), (std::vector<int>{0, 1}));
    QCOMPARE(f.obj(1).endlevel, 0LL);

    // przeniesienie Data0 na wolny poziom 2: poziomy rosnaco, EndLevel podniesiony (wariant 2a)
    f.dock.move_level(0, 2, false);
    QCOMPARE(f.stack.count(), 1);
    QCOMPARE(f.obj(1).data->data_levels(), (std::vector<int>{1, 2}));
    QCOMPARE(f.obj(1).endlevel, 2LL);
    QVERIFY(messages.last().at(0).toString().contains("EndLevel"));
    const std::string saved = f.map->to_mp_string();
    QVERIFY(saved.find("EndLevel=2") != std::string::npos);
    QVERIFY(saved.find("Data1=") < saved.find("Data2="));
    // numeracja przeszla razem z wezlami
    QVERIFY(saved.find("Numbers1=") != std::string::npos);

    // zajety poziom docelowy - nic sie nie dzieje (wariant 1c, w menu pozycja wyszarzona)
    f.dock.move_level(1, 2, false);
    QCOMPARE(f.stack.count(), 1);

    // obiekt nie ma juz Data0, wiec na ogladanym poziomie 0 jest niewidoczny (i odznaczony)
    QVERIFY(!f.polyline()->graphics_item()->isVisible());
    QVERIFY(messages.last().at(0).toString().contains(QString::fromUtf8("widoczny od poziomu 1")));
    f.scene.set_map_level(1);
    f.select_only(f.polyline());

    // kopia: oryginal zostaje
    f.dock.move_level(1, 4, true);
    QCOMPARE(f.obj(1).data->data_levels(), (std::vector<int>{1, 2, 4}));
    QCOMPARE(f.obj(1).endlevel, 4LL);
    // karta Elements pokazuje nowe poziomy
    QCOMPARE(f.dock.elements()->topLevelItemCount(), 3);
    QCOMPARE(f.dock.elements()->topLevelItem(2)->text(0), QString("Data4"));

    f.stack.undo();
    f.stack.undo();
    QCOMPARE(f.map->to_mp_string(), f.original);
    f.scene.set_map_level(0);
}

void EditTests::elements_delete_extract_polygon_parts() {
    DockFixture f;
    // polygon: czesc A z dziura i osobna czesc B (wszystkie na Data0)
    QMimeData mime;
    mime.setText("[POLYGON]\nType=0x4e\nLabel=Dzialki\n"
                 "Data0=(52.1000,21.0000),(52.1000,21.0100),(52.1100,21.0100),(52.1100,21.0000)\n"
                 "Data0=(52.1030,21.0030),(52.1030,21.0060),(52.1060,21.0060),(52.1060,21.0030)\n"
                 "Data0=(52.1200,21.0200),(52.1200,21.0300),(52.1300,21.0300)\n[END]\n");
    QCOMPARE(f.scene.paste(&mime, std::nullopt), 1);
    const size_t poly = 2;
    QCOMPARE(f.obj(poly).data->polys_for_data_level(0)->size(), size_t{3});
    f.select_only(f.scene.item_for_object(poly));
    const std::string before = f.map->to_mp_string();
    const int commands = f.stack.count();

    // karta Elements: A (Outer) z dziura (Inner) jako dzieckiem, B osobno
    QTreeWidgetItem* level = f.dock.elements()->topLevelItem(0);
    QCOMPARE(level->childCount(), 2);
    QCOMPARE(level->child(0)->childCount(), 1);
    QCOMPARE(level->child(0)->child(0)->text(1), QString("Inner"));

    // ekstrakcja A razem z dziura (wariant 3a): nowy obiekt z 2 czesciami i tymi samymi wlasciwosciami
    f.dock.extract_element(0, {0, 1});
    QCOMPARE(f.stack.count(), commands + 1);
    QCOMPARE(f.map->objects().size(), size_t{4});
    QCOMPARE(f.obj(3).kind(), ObjectKind::Polygon);
    QCOMPARE(*f.obj(3).label1, std::string("Dzialki"));
    QCOMPARE(f.obj(3).data->polys_for_data_level(0)->size(), size_t{2});
    QCOMPARE(f.obj(poly).data->polys_for_data_level(0)->size(), size_t{1});
    QVERIFY(f.scene.item_for_object(3)->graphics_item()->isVisible());

    // jedyny element poziomu - nie da sie wyekstrahowac (komunikat, bez komendy)
    QSignalSpy messages(&f.dock, &PropertiesDock::message);
    f.dock.extract_element(0, {0});
    QCOMPARE(f.stack.count(), commands + 1);
    QVERIFY(messages.last().at(0).toString().contains(QString::fromUtf8("jedynego")));

    // usuniecie ostatniej czesci obiektu = usuniecie obiektu
    f.dock.delete_element(0, {0});
    QVERIFY(f.obj(poly).deleted);
    QVERIFY(!f.scene.item_for_object(poly)->graphics_item()->isVisible());
    f.stack.undo();
    f.stack.undo();
    QCOMPARE(f.map->to_mp_string(), before);

    // usuniecie A z dziura - zostaje B; usuniecie czesci poziomu Data1 linii usuwa caly poziom
    f.select_only(f.scene.item_for_object(poly));
    f.dock.delete_element(0, {0, 1});
    QCOMPARE(f.obj(poly).data->polys_for_data_level(0)->size(), size_t{1});
    f.select_only(f.polyline());
    f.dock.delete_element(1, {0});
    QCOMPARE(f.obj(1).data->data_levels(), std::vector<int>{0});
    while (f.stack.index() > commands) f.stack.undo();
    QCOMPARE(f.map->to_mp_string(), before);
}

void EditTests::subtract_polygons_hole_partial_and_delete() {
    DockFixture f;
    // A: kwadrat; B: maly kwadrat wewnatrz A; C: prostokat nachodzacy na A czesciowo; D: daleko
    QMimeData mime;
    mime.setText("[POLYGON]\nType=0x4e\nLabel=A\nEndLevel=1\n"
                 "Data0=(52.1000,21.0000),(52.1000,21.0100),(52.1100,21.0100),(52.1100,21.0000)\n"
                 "Data1=(52.1000,21.0000),(52.1000,21.0100),(52.1100,21.0100)\n[END]\n"
                 "[POLYGON]\nType=0x4e\nLabel=B\n"
                 "Data0=(52.1030,21.0030),(52.1030,21.0060),(52.1060,21.0060),(52.1060,21.0030)\n[END]\n"
                 "[POLYGON]\nType=0x4e\nLabel=C\n"
                 "Data0=(52.1050,21.0050),(52.1050,21.0200),(52.1200,21.0200),(52.1200,21.0050)\n[END]\n"
                 "[POLYGON]\nType=0x4e\nLabel=D\n"
                 "Data0=(52.3000,21.3000),(52.3000,21.3100),(52.3100,21.3100)\n[END]\n");
    QCOMPARE(f.scene.paste(&mime, std::nullopt), 4);
    const size_t A = 2, B = 3, C = 4, D = 5;
    const std::string before = f.map->to_mp_string();
    const int commands = f.stack.count();
    auto select = [&](size_t first, size_t second) {
        f.scene.clearSelection();
        f.scene.item_for_object(first)->graphics_item()->setSelected(true);
        f.scene.item_for_object(second)->graphics_item()->setSelected(true);
    };
    bool changed = false;

    // zle zaznaczenie: jeden obiekt, polilinia
    f.select_only(f.scene.item_for_object(A));
    f.scene.subtract_selected_polygons(false, &changed);
    QVERIFY(!changed);
    select(A, 1);
    f.scene.subtract_selected_polygons(false, &changed);
    QVERIFY(!changed);
    // brak nakladania
    select(A, D);
    QVERIFY(f.scene.subtract_selected_polygons(false, &changed).contains(QString::fromUtf8("nie nakładają")));
    QVERIFY(!changed);
    // B pokrywa cale A? odwrotnie: od B odejmujemy A - wynik pusty
    select(B, A);
    QVERIFY(f.scene.subtract_selected_polygons(false, &changed).contains(QString::fromUtf8("pokrywa cały")));
    QVERIFY(!changed);
    QCOMPARE(f.stack.count(), commands);

    // B wewnatrz A - dziura; Data1 bez zmian (tylko ogladany poziom)
    select(A, B);
    f.scene.subtract_selected_polygons(false, &changed);
    QVERIFY(changed);
    QCOMPARE(f.stack.count(), commands + 1);
    QCOMPARE(f.obj(A).data->polys_for_data_level(0)->size(), size_t{2});
    QCOMPARE(f.obj(A).data->polys_for_data_level(1)->size(), size_t{1});
    QCOMPARE(f.obj(A).data->polys_for_data_level(1)->front().size(), size_t{3});
    QVERIFY(!f.obj(B).deleted);
    QVERIFY(f.scene.item_for_object(A)->graphics_item()->isSelected());
    QCOMPARE(*f.obj(A).label1, std::string("A"));
    // w karcie Elements druga czesc to dziura - zapis ma dwie linie Data0
    const std::string saved = f.map->to_mp_string();
    const size_t a_rec = saved.find("Label=A");
    QVERIFY(saved.find("Data0=", saved.find("Data0=", a_rec) + 1) < saved.find("[END]", a_rec));

    // C nachodzi czesciowo - odjecie z usunieciem C (jedna komenda)
    select(A, C);
    f.scene.subtract_selected_polygons(true, &changed);
    QVERIFY(changed);
    QCOMPARE(f.stack.count(), commands + 2);
    QVERIFY(f.obj(C).deleted);
    QVERIFY(!f.scene.item_for_object(C)->graphics_item()->isVisible());

    f.stack.undo();
    QVERIFY(!f.obj(C).deleted);
    f.stack.undo();
    QCOMPARE(f.map->to_mp_string(), before);
}

void EditTests::ctrl_click_adds_polygon_lying_on_selected_one() {
    ViewFixture f;
    // duzy polygon i maly lezacy w calosci na nim (bez obiektow mapy w poblizu)
    QMimeData mime;
    mime.setText("[POLYGON]\nType=0x4e\nLabel=Duzy\n"
                 "Data0=(52.2000,21.2000),(52.2000,21.2030),(52.2020,21.2030),(52.2020,21.2000)\n[END]\n"
                 "[POLYGON]\nType=0x4e\nLabel=Maly\n"
                 "Data0=(52.2008,21.2012),(52.2008,21.2018),(52.2012,21.2018),(52.2012,21.2012)\n[END]\n");
    QCOMPARE(f.scene.paste(&mime, std::nullopt), 2);
    MapObjectItem* big = f.scene.item_for_object(2);
    MapObjectItem* small = f.scene.item_for_object(3);
    f.scene.clearSelection();
    f.view.centerOn(small->graphics_item());
    const QPoint on_small = f.view.mapFromScene(small->graphics_item()->sceneBoundingRect().center());
    const QPointF big_corner = big->graphics_item()->sceneBoundingRect().topLeft();
    const QPoint on_big_only = f.view.mapFromScene(big_corner) + QPoint(5, 5);

    // klik na samym duzym - zaznaczony duzy
    QTest::mouseClick(f.vp(), Qt::LeftButton, Qt::NoModifier, on_big_only);
    QVERIFY(big->graphics_item()->isSelected());
    QVERIFY(!small->graphics_item()->isSelected());
    // Ctrl+klik na malym (pod kursorem oba) - dochodzi maly, duzy zostaje
    QTest::mouseClick(f.vp(), Qt::LeftButton, Qt::ControlModifier, on_small);
    QVERIFY(big->graphics_item()->isSelected());
    QVERIFY(small->graphics_item()->isSelected());
    // kolejnosc zaznaczania: najpierw duzy (od niego odejmujemy maly)
    const auto order = f.scene.selected_object_items_in_order();
    QCOMPARE(order.size(), size_t{2});
    QCOMPARE(order[0], big);
    QCOMPARE(order[1], small);
    bool changed = false;
    f.scene.subtract_selected_polygons(false, &changed);
    QVERIFY(changed);
    QCOMPARE(f.map->objects()[2].data->polys_for_data_level(0)->size(), size_t{2});  // dziura
    f.stack.undo();

    // wszystkie pod kursorem zaznaczone - Ctrl+klik odznacza najwyzszy, kolejny znow dodaje
    f.scene.clearSelection();
    QTest::mouseClick(f.vp(), Qt::LeftButton, Qt::NoModifier, on_big_only);
    QTest::mouseClick(f.vp(), Qt::LeftButton, Qt::ControlModifier, on_small);
    QTest::mouseClick(f.vp(), Qt::LeftButton, Qt::ControlModifier, on_small);
    QCOMPARE(f.scene.selected_object_items().size(), size_t{1});
    QTest::mouseClick(f.vp(), Qt::LeftButton, Qt::ControlModifier, on_small);
    QCOMPARE(f.scene.selected_object_items().size(), size_t{2});
    // zwykly klik nadal przelacza miedzy obiektami pod kursorem (jeden zaznaczony)
    QTest::mouseClick(f.vp(), Qt::LeftButton, Qt::NoModifier, on_small);
    QCOMPARE(f.scene.selected_object_items().size(), size_t{1});
}

void EditTests::convert_polyline_polygon_both_ways() {
    DockFixture f;
    f.scene.set_last_used_type(ObjectKind::Polygon, 0x4e);
    f.scene.set_last_used_type(ObjectKind::Polyline, 0x1c);
    bool changed = false;

    // polilinia z mapy testowej ma na Data1 tylko 2 wezly - nie da sie z niej zrobic polygonu (komunikat, bez zmian)
    f.select_only(f.polyline());
    QVERIFY(f.scene.has_selected(ObjectKind::Polyline));
    QVERIFY(!f.scene.has_selected(ObjectKind::Polygon));
    QVERIFY(f.scene.convert_selected(ObjectKind::Polyline, &changed).contains("Ulica"));
    QVERIFY(!changed);
    QCOMPARE(f.stack.count(), 0);

    // polilinia z DirIndicator, numeracja i HLevel -> polygon: pola linii usuniete, etykieta i komentarz zostaja
    QMimeData mime;
    mime.setText(";uwaga\n[POLYLINE]\nType=0x6\nLabel=Petla\nDirIndicator=1\n"
                 "Data0=(52.3000,21.3000),(52.3000,21.3100),(52.3100,21.3100),(52.3000,21.3000)\n"
                 "Numbers1=0,O,1,5,N,-1,-1\nHLevel0=(1,1)\n[END]\n");
    QCOMPARE(f.scene.paste(&mime, std::nullopt), 1);
    const int base = f.stack.count();
    const std::string before = f.map->to_mp_string();
    QCOMPARE(f.scene.selected_object_items().size(), size_t{1});  // wklejony obiekt zaznaczony
    const QString msg = f.scene.convert_selected(ObjectKind::Polyline, &changed);
    QVERIFY(changed);
    QVERIFY(msg.contains("DirIndicator") && msg.contains("Numbers") && msg.contains("HLevel"));
    QCOMPARE(f.stack.count(), base + 1);
    QVERIFY(f.obj(2).deleted);
    const MapObject& polygon = f.obj(3);
    QCOMPARE(polygon.kind(), ObjectKind::Polygon);
    QCOMPARE(*polygon.type, 0x4eLL);
    QCOMPARE(*polygon.label1, std::string("Petla"));
    QVERIFY(polygon.comment && polygon.comment->front() == "uwaga");
    QVERIFY(!polygon.dirindicator);
    QCOMPARE(polygon.data->polys_for_data_level(0)->front().size(), size_t{3});  // bez powtorzonego wezla
    QVERIFY(f.scene.item_for_object(3)->graphics_item()->type() == PolygonItemType);
    QVERIFY(f.scene.item_for_object(3)->graphics_item()->isSelected());
    // rekord nowego polygonu (w pliku jest tez polilinia "Ulica" z numeracja)
    std::string record;
    for (const std::string& l : polygon.to_mp_record(f.map->precision())) record += l + '\n';
    QVERIFY(record.find("[POLYGON]") != std::string::npos);
    QVERIFY(record.find("Numbers") == std::string::npos);
    QVERIFY(record.find("HLevel") == std::string::npos);
    QVERIFY(record.find("DirIndicator") == std::string::npos);

    // i z powrotem: polygon -> zamknieta polilinia z ostatnio uzytym typem linii
    QVERIFY(f.scene.has_selected(ObjectKind::Polygon));
    f.scene.convert_selected(ObjectKind::Polygon, &changed);
    QVERIFY(changed);
    const MapObject& line = f.obj(4);
    QCOMPARE(line.kind(), ObjectKind::Polyline);
    QCOMPARE(*line.type, 0x1cLL);
    const Poly& ring = line.data->polys_for_data_level(0)->front();
    QCOMPARE(ring.size(), size_t{4});
    QVERIFY(ring.front().pos() == ring.back().pos());
    QVERIFY(f.scene.item_for_object(4)->graphics_item()->type() == PolylineItemType);

    f.stack.undo();
    f.stack.undo();
    QCOMPARE(f.map->to_mp_string(), before);
}

void EditTests::transparent_polygon_fill() {
    // polygon na bialym tle: w trybie transparentnym srodek jest jasniejszy (opacity 0.5), zaznaczony - jak dotad
    auto map = std::make_unique<MapData>(std::make_unique<MercatorProjection>());
    map->load_from_string(
        "[IMG ID]\nName=test\n[END-IMG ID]\n\n[POLYGON]\nType=0x4e\n"
        "Data0=(52.10000,21.00000),(52.10000,21.01000),(52.11000,21.01000),(52.11000,21.00000)\n[END]\n\n");
    Projection& projection = map->projection();
    projection.set_map_bounding_box(map->map_bounding_box());
    projection.calculate_data_offset();
    MapStyles styles{MapStyles::find_icons_dir()};
    MapScene scene;
    scene.set_canvas_rectangle(map->map_bounding_box(), projection);
    scene.set_map(map.get(), &styles);
    QGraphicsItem* item = scene.item_for_object(0)->graphics_item();
    const QRectF rect = item->sceneBoundingRect();
    auto centre = [&] {
        QImage image(100, 100, QImage::Format_ARGB32);
        image.fill(Qt::white);
        QPainter painter(&image);
        scene.render(&painter, QRectF(0, 0, 100, 100), rect);
        painter.end();
        return image.pixelColor(50, 50);
    };
    const QColor solid = centre();
    QVERIFY(solid != QColor(Qt::white));
    scene.set_transparent_polygons(true);
    const QColor transparent = centre();
    QVERIFY(transparent.lightness() > solid.lightness());
    QVERIFY(transparent != QColor(Qt::white));
    item->setSelected(true);  // zaznaczony: ta sama przezroczystosc, bez podwajania
    QCOMPARE(centre(), transparent);
    scene.set_transparent_polygons(false);
    QCOMPARE(centre(), transparent);  // zaznaczony jest przezroczysty takze w trybie stalym
    item->setSelected(false);
    QCOMPARE(centre(), solid);
    scene.clear_map();
}

void EditTests::road_casing_under_roads_only() {
    // Dwie drogi 0x5 (jasnozolte) krzyzujace sie pod katem prostym i rzeka 0x1f obok.
    auto map = std::make_unique<MapData>(std::make_unique<MercatorProjection>());
    map->load_from_string(
        "[IMG ID]\nName=test\n[END-IMG ID]\n\n"
        "[POLYLINE]\nType=0x5\nData0=(52.10000,21.00000),(52.10000,21.00200)\n[END]\n\n"
        "[POLYLINE]\nType=0x5\nData0=(52.09900,21.00100),(52.10100,21.00100)\n[END]\n\n"
        "[POLYLINE]\nType=0x1f\nData0=(52.10060,21.00000),(52.10060,21.00200)\n[END]\n\n"
        "[POLYLINE]\nType=0x14\nData0=(52.09940,21.00000),(52.09940,21.00200)\n[END]\n\n");
    Projection& projection = map->projection();
    projection.set_map_bounding_box(map->map_bounding_box());
    projection.calculate_data_offset();
    MapStyles styles{MapStyles::find_icons_dir()};
    MapScene scene;
    scene.set_canvas_rectangle(map->map_bounding_box(), projection);
    scene.set_map(map.get(), &styles);
    QVERIFY(!scene.road_casing());

    const QRectF lines = scene.item_for_object(0)->graphics_item()->sceneBoundingRect().united(
        scene.item_for_object(1)->graphics_item()->sceneBoundingRect());
    const QRectF rect(lines.center() - QPointF(lines.width() / 2, lines.width() / 2), QSizeF(lines.width(), lines.width()));
    const int size = 200;
    const QColor background(200, 200, 200);  // szare, zeby odroznic biale tlo kolei od tla obrazu
    auto render = [&] {
        QImage image(size, size, QImage::Format_ARGB32);
        image.fill(background);
        QPainter painter(&image);
        scene.render(&painter, QRectF(0, 0, size, size), rect);
        painter.end();
        return image;
    };
    auto to_image = [&](const QPointF& scene_point) {
        return QPoint(int((scene_point.x() - rect.left()) * size / rect.width()),
                      int((scene_point.y() - rect.top()) * size / rect.height()));
    };
    const QColor road = styles.polyline_colour(0x5);
    const QColor road_casing = styles.road_casing_pen(0x5).color();
    const QColor river_casing = styles.road_casing_pen(0x1f).color();
    const QPoint crossing = to_image(scene.item_for_object(1)->graphics_item()->sceneBoundingRect().center());
    const int river_y = to_image(scene.item_for_object(2)->graphics_item()->sceneBoundingRect().center()).y();
    auto count_in_column = [&](const QImage& image, int x, int y_from, int y_to, const QColor& colour) {
        int n = 0;
        // rgb(): kolor z darker() ma skladowe 16-bitowe, piksel obrazu 8-bitowe
        for (int y = y_from; y <= y_to; ++y) n += image.pixel(x, y) == colour.rgb();
        return n;
    };
    const int x = crossing.x() - 40;  // na drodze poziomej, daleko od skrzyzowania

    QImage plain = render();
    QCOMPARE(plain.pixelColor(x, crossing.y()), road);
    QCOMPARE(count_in_column(plain, x, crossing.y() - 8, crossing.y() + 8, road_casing), 0);

    scene.set_road_casing(true);
    QVERIFY(scene.road_casing());
    QImage cased = render();
    QCOMPARE(cased.pixelColor(x, crossing.y()), road);
    // obwodka po obu stronach drogi (po 1 pikselu)
    QCOMPARE(count_in_column(cased, x, crossing.y() - 8, crossing.y() - 1, road_casing), 1);
    QCOMPARE(count_in_column(cased, x, crossing.y() + 1, crossing.y() + 8, road_casing), 1);
    // skrzyzowanie: obwodka drogi pionowej nie przecina poziomej (wszystkie obwodki pod wszystkimi drogami)
    for (int dx = -4; dx <= 4; ++dx) QCOMPARE(cased.pixelColor(crossing.x() + dx, crossing.y()), road);
    // rzeka nie jest droga - bez obwodki
    QCOMPARE(count_in_column(cased, x, river_y - 8, river_y + 8, river_casing), 0);
    // kolej: bez obwodek przerwy miedzy czarnymi odcinkami maja kolor tla; z obwodkami czarny brzeg z obu stron,
    // a w srodku tylko czarne odcinki i biale przerwy
    const int rail_y = to_image(scene.item_for_object(3)->graphics_item()->sceneBoundingRect().center()).y();
    auto row_colours = [&](const QImage& image, int y) {
        QSet<QRgb> colours;
        for (int rx = crossing.x() - 80; rx <= crossing.x() - 20; ++rx) colours.insert(image.pixel(rx, y));
        return colours;
    };
    const QRgb black = QColor(Qt::black).rgb(), white = QColor(Qt::white).rgb();
    QCOMPARE(row_colours(plain, rail_y), (QSet<QRgb>{black, background.rgb()}));
    QCOMPARE(row_colours(cased, rail_y), (QSet<QRgb>{black, white}));
    // odcinki i przerwy pol na pol (okres 18 px przy szerokosci 3 px, okno 61 px)
    int black_count = 0, white_count = 0;
    for (int rx = crossing.x() - 80; rx <= crossing.x() - 20; ++rx) {
        black_count += cased.pixel(rx, rail_y) == black;
        white_count += cased.pixel(rx, rail_y) == white;
    }
    QVERIFY2(std::abs(black_count - white_count) <= 9,
             qPrintable(QString("czarne %1, biale %2").arg(black_count).arg(white_count)));
    // w przekroju przez przerwe: tlo, czarny brzeg, biale (szerokosc kolei 3 px), czarny brzeg, tlo
    int gap_x = -1;
    for (int rx = crossing.x() - 80; rx <= crossing.x() - 20 && gap_x < 0; ++rx)
        if (cased.pixel(rx, rail_y) == white) gap_x = rx;
    QVERIFY(gap_x >= 0);
    const QList<QRgb> expected_section{background.rgb(), black, white, white, white, black, background.rgb()};
    QList<QRgb> section;
    for (int y = rail_y - 3; y <= rail_y + 3; ++y) section.append(cased.pixel(gap_x, y));
    QCOMPARE(section, expected_section);
    // warstwa nie przechwytuje myszy: pod kursorem na drodze jest droga
    const QPointF on_road = scene.item_for_object(0)->graphics_item()->sceneBoundingRect().center() +
                            QPointF(-lines.width() / 4, 0);
    const QList<QGraphicsItem*> under = scene.items(on_road);
    QVERIFY(!under.isEmpty());
    for (QGraphicsItem* item : under) QVERIFY(item->type() != RoadCasingItemType);

    scene.set_road_casing(false);
    QCOMPARE(render(), plain);
    scene.clear_map();
}

void EditTests::trail_icon_positions_along_line() {
    constexpr double D = TRAIL_ICON_SIZE_PX;
    auto positions = [](const QPainterPath& path, int slot, const QTransform& t = QTransform()) {
        std::vector<QPointF> out;
        TrailIconLayer::icon_positions(path, t, slot, out);
        return out;
    };
    QPainterPath line;
    line.moveTo(0, 0);
    line.lineTo(400, 0);
    line.lineTo(1000, 0);  // wezel w srodku nie zmienia rozmieszczenia
    // 1000 px: 5 ikon co 200 px; slot 6 przesuwa o -0,5 * (D + 2)
    const std::vector<QPointF> p6 = positions(line, 6);
    QCOMPARE(p6.size(), size_t(5));
    const double first = 100 - 0.5 * (D + 2);
    for (size_t i = 0; i < p6.size(); ++i) {
        QVERIFY(qAbs(p6[i].x() - (first + 200.0 * i)) < 1e-6);
        QCOMPARE(p6[i].y(), 0.0);
    }
    // inny typ szlaku: te same odstepy, przesuniete o roznice numerow * (D + 2)
    const std::vector<QPointF> p8 = positions(line, 8);
    QCOMPARE(p8.size(), size_t(5));
    QVERIFY(qAbs(p8[0].x() - p6[0].x() - 2 * (D + 2)) < 1e-6);
    // przesuniecie poza odstep zawija sie (ikony dalej co 200 px, zadna nie wypada poza linie)
    for (int slot = 0; slot <= 13; ++slot) {
        const std::vector<QPointF> p = positions(line, slot);
        QVERIFY(!p.empty());
        for (const QPointF& q : p) QVERIFY(q.x() >= D / 2 && q.x() <= 1000 - D / 2);
        for (size_t i = 1; i < p.size(); ++i) QVERIFY(qAbs(p[i].x() - p[i - 1].x() - 200) < 1e-6);
    }
    // krotka linia: ponizej 1,5 ikony bez ikony, dluzsza - jedna ikona w granicach linii
    QPainterPath short_line;
    short_line.moveTo(0, 0);
    short_line.lineTo(1.5 * D - 1, 0);
    QVERIFY(positions(short_line, 0).empty());
    short_line = QPainterPath();
    short_line.moveTo(0, 0);
    short_line.lineTo(60, 0);
    const std::vector<QPointF> one = positions(short_line, 0);  // srodek 30 - 6,5 * 18 -> obciete do D/2
    QCOMPARE(one.size(), size_t(1));
    QCOMPARE(one[0].x(), D / 2);
    // dwie czesci liczone osobno; przeksztalcenie na ekran (skala 2: 100 -> 200 px)
    QPainterPath parts;
    parts.moveTo(0, 0);
    parts.lineTo(100, 0);
    parts.moveTo(0, 50);
    parts.lineTo(0, 150);
    const std::vector<QPointF> two = positions(parts, 6, QTransform::fromScale(2, 2));
    QCOMPARE(two.size(), size_t(2));
    QVERIFY(qAbs(two[0].x() - (100 - 0.5 * (D + 2))) < 1e-6 && two[0].y() == 0);
    QVERIFY(two[1].x() == 0 && qAbs(two[1].y() - (100 + 100 - 0.5 * (D + 2))) < 1e-6);
}

void EditTests::trail_icons_drawn_on_trails_only() {
    // typy z ikona i poprawione kolory szlakow
    QCOMPARE(MapStyles::trail_icon(0x10e00), TrailIcon::Hiking);
    QCOMPARE(MapStyles::trail_icon(0x10e07), TrailIcon::Hiking);
    QCOMPARE(MapStyles::trail_icon(0x16), TrailIcon::Hiking);
    QCOMPARE(MapStyles::trail_icon(0x10e0d), TrailIcon::Bike);
    QCOMPARE(MapStyles::trail_icon(0xd), TrailIcon::Bike);
    QCOMPARE(MapStyles::trail_icon(0x10e0f), TrailIcon::None);
    QCOMPARE(MapStyles::trail_icon(0x5), TrailIcon::None);
    QCOMPARE(MapStyles::trail_icon_slot(0x10e05), -1);
    MapStyles styles{MapStyles::find_icons_dir()};
    QCOMPARE(styles.polyline_colour(0x10e0a), QColor("#399520"));  // rowerowy zielony (byl zolty)
    QVERIFY(styles.polyline_colour(0x10e07).isValid());              // pieszy kolorowy (byl bledny zapis)
    QCOMPARE(styles.polyline_colour(0x10e07), QColor("#a959a9"));

    // czerwony szlak pieszy i droga 0x5 rownolegle
    auto map = std::make_unique<MapData>(std::make_unique<MercatorProjection>());
    map->load_from_string(
        "[IMG ID]\nName=test\n[END-IMG ID]\n\n"
        "[POLYLINE]\nType=0x10e00\nData0=(52.10000,21.00000),(52.10000,21.00600)\n[END]\n\n"
        "[POLYLINE]\nType=0x5\nData0=(52.10100,21.00000),(52.10100,21.00600)\n[END]\n\n");
    Projection& projection = map->projection();
    projection.set_map_bounding_box(map->map_bounding_box());
    projection.calculate_data_offset();
    MapScene scene;
    scene.set_canvas_rectangle(map->map_bounding_box(), projection);
    scene.set_map(map.get(), &styles);
    QVERIFY(scene.trail_icons());

    const QRectF trail = scene.item_for_object(0)->graphics_item()->sceneBoundingRect();
    const QRectF road = scene.item_for_object(1)->graphics_item()->sceneBoundingRect();
    const QRectF both = trail.united(road);
    const double side = both.width() * 1.1;
    const QRectF rect(both.center() - QPointF(side / 2, side / 2), QSizeF(side, side));
    const QColor background(200, 200, 200);
    // rysowanie przez widok, jak w programie: QGraphicsScene::render oznacza juz narysowane elementy
    // (itemDiscovered) i indeks sceny nie zwraca ich warstwie ikon - linie lezace pod warstwa by zniknely
    auto render = [&](int size) {
        QGraphicsView view(&scene);
        view.setFrameShape(QFrame::NoFrame);
        view.setHorizontalScrollBarPolicy(Qt::ScrollBarAlwaysOff);
        view.setVerticalScrollBarPolicy(Qt::ScrollBarAlwaysOff);
        view.setBackgroundBrush(background);
        view.resize(size, size);
        view.setTransform(QTransform::fromScale(size / rect.width(), size / rect.height()));
        view.centerOn(rect.center());
        return view.viewport()->grab().toImage().convertToFormat(QImage::Format_ARGB32);
    };
    // biale piksele (rysunek pieszego na czerwonym krazku) w pasie wokol linii
    auto white_in_band = [&](const QImage& image, const QRectF& line) {
        const double k = image.width() / rect.width();
        const int y = int((line.center().y() - rect.top()) * k);
        int n = 0;
        for (int yy = std::max(0, y - 10); yy <= std::min(image.height() - 1, y + 10); ++yy)
            for (int x = 0; x < image.width(); ++x) n += image.pixel(x, yy) == QColor(Qt::white).rgb();
        return n;
    };
    const int size = 600;
    QVERIFY(size / rect.width() >= SCALE_WITHOUT_TRAIL_ICONS);
    const QImage with_icons = render(size);
    QVERIFY(white_in_band(with_icons, trail) > 0);
    QCOMPARE(white_in_band(with_icons, road), 0);  // droga bez ikon

    scene.set_trail_icons(false);
    QVERIFY(!scene.trail_icons());
    const QImage without = render(size);
    QCOMPARE(white_in_band(without, trail), 0);
    scene.set_trail_icons(true);
    // ponizej progu skali ikony nie sa rysowane
    const int small = int(rect.width() * SCALE_WITHOUT_TRAIL_ICONS * 0.8);
    scene.set_trail_icons(false);
    const QImage small_without = render(small);
    scene.set_trail_icons(true);
    QCOMPARE(render(small), small_without);
    // warstwa nie przechwytuje myszy
    for (QGraphicsItem* item : scene.items(trail.center())) QVERIFY(item->type() != TrailIconLayerItemType);
    scene.clear_map();
}

namespace {
void send_wheel(QWidget* viewport, const QPoint& pos, int delta, Qt::KeyboardModifiers modifiers) {
    QWheelEvent ev(QPointF(pos), QPointF(viewport->mapToGlobal(pos)), QPoint(), QPoint(0, delta), Qt::NoButton,
                   modifiers, Qt::NoScrollPhase, false);
    QApplication::sendEvent(viewport, &ev);
}

// Kat (stopnie, uklad sceny) wektora od srodka do wezla.
double node_angle(const PointF& center, const Node& n) {
    return std::atan2(n.y() - center.y, n.x() - center.x) * 180 / std::acos(-1.0);
}
}  // namespace

void EditTests::shift_wheel_rotates_object_in_edit_nodes() {
    {
        ViewFixture f;
        QStringList messages;
        QObject::connect(&f.scene, &MapScene::message, [&](const QString& m) { messages << m; });
        // pozycja w widoku liczona przy kazdym zdarzeniu: Shift+kolko poza obiektem przewija widok
        auto on_line = [&] {
            const PointF a = f.node(1, 0, 0).pos(), b = f.node(1, 0, 1).pos();
            return f.view_pos(PointF{(a.x + b.x) / 2, (a.y + b.y) / 2});
        };
        auto away = [&] { return on_line() + QPoint(0, 200); };
        const PointF center = *f.map->objects()[1].data->centroid(0, false);
        const double angle0 = node_angle(center, f.node(1, 0, 0));
        const PointF level1_node = f.node(1, 1, 1).pos();
        const double angle1 = node_angle(center, f.node(1, 1, 1));

        // w trybie zaznaczania Shift+kolko nie obraca
        f.select_only(f.polyline());
        send_wheel(f.vp(), on_line(), 120, Qt::ShiftModifier);
        QCOMPARE(f.stack.count(), 0);

        f.scene.set_tool(Tool::EditNodes);
        f.select_only(f.polyline());
        // poza obiektem - nic
        send_wheel(f.vp(), away(), 120, Qt::ShiftModifier);
        QCOMPARE(f.stack.count(), 0);
        // 3 zabki od siebie: 3 stopnie przeciwnie do wskazowek zegara (w ukladzie sceny z osia y w dol kat maleje)
        for (int i = 0; i < 3; ++i) send_wheel(f.vp(), on_line(), 120, Qt::ShiftModifier);
        QCOMPARE(f.stack.count(), 1);  // jeden gest - jeden krok undo
        QCOMPARE(f.stack.text(0), QString("Obróć obiekt"));
        QVERIFY(f.scene.rotation_active());
        QCOMPARE(messages.last(), QString("Obrót: +3.0°"));
        QVERIFY(qAbs(node_angle(center, f.node(1, 0, 0)) - (angle0 - 3)) < 1e-6);
        // drugi poziom Data obrocony o ten sam kat wokol tego samego srodka
        QVERIFY(qAbs(node_angle(center, f.node(1, 1, 1)) - (angle1 - 3)) < 1e-6);
        QVERIFY(f.node(1, 1, 1).pos() != level1_node);
        // uchwyty przebudowane w nowych miejscach wezlow
        QCOMPARE(f.grips(1).size(), f.node_count(1));
        QVERIFY(QLineF(f.grips(1)[0]->scenePos(), QPointF(f.node(1, 0, 0).x(), f.node(1, 0, 0).y())).length() < 1e-6);
        // Ctrl: 0,1 stopnia, w druga strone; nadal ten sam gest
        send_wheel(f.vp(), on_line(), -120, Qt::ShiftModifier | Qt::ControlModifier);
        QCOMPARE(f.stack.count(), 1);
        QCOMPARE(messages.last(), QString("Obrót: +2.9°"));
        QVERIFY(qAbs(node_angle(center, f.node(1, 0, 0)) - (angle0 - 2.9)) < 1e-6);
        // cofniecie przywraca mape
        f.stack.undo();
        QCOMPARE(f.map->to_mp_string(), f.original);
        QVERIFY(!f.scene.rotation_active());
        // po czasie gestu kolejny obrot to nowy krok undo
        f.stack.redo();
        send_wheel(f.vp(), on_line(), 120, Qt::ShiftModifier);
        QCOMPARE(f.stack.count(), 2);
        QTRY_VERIFY_WITH_TIMEOUT(!f.scene.rotation_active(), MapScene::ROTATION_GESTURE_MS * 3);
        send_wheel(f.vp(), on_line(), 120, Qt::ShiftModifier);
        QCOMPARE(f.stack.count(), 3);
    }
    {
        // polygon: obraca sie takze z kursorem we wnetrzu; srodek ciezkosci zostaje na miejscu
        Fixture f(
            "[IMG ID]\nName=test\n[END-IMG ID]\n\n"
            "[POLYGON]\nType=0x13\n"
            "Data0=(52.10000,21.00000),(52.10000,21.00300),(52.10100,21.00300),(52.10100,21.00000)\n[END]\n\n");
        MapView view(&f.scene);
        view.set_projection(&f.map->projection());
        view.resize(800, 600);
        view.show();
        QVERIFY(QTest::qWaitForWindowExposed(&view));
        const PointF center = *f.map->objects()[0].data->centroid(0, true);
        view.centerOn(QPointF(center.x, center.y));
        f.scene.set_tool(Tool::EditNodes);
        f.select_only(f.scene.item_for_object(0));
        const QPoint inside = view.mapFromScene(QPointF(center.x, center.y)) + QPoint(5, 3);
        const double angle0 = node_angle(center, f.node(0, 0, 2));
        for (int i = 0; i < 90; ++i) send_wheel(view.viewport(), inside, 120, Qt::ShiftModifier);
        QCOMPARE(f.stack.count(), 1);
        QVERIFY(qAbs(node_angle(center, f.node(0, 0, 2)) - (angle0 - 90)) < 1e-6);
        const PointF after = *f.map->objects()[0].data->centroid(0, true);
        QVERIFY(std::hypot(after.x - center.x, after.y - center.y) < 1e-6);
        f.stack.undo();
        QCOMPARE(f.map->to_mp_string(), f.original);
    }
    {
        // rondo: zamknieta polilinia z 12 wezlami; obraca sie z kursorem w srodku i tuz przy wezle od zewnatrz
        // (tam zaden odcinek nie lezy "naprzeciw" kursora, a mimo to kursor jest przy linii)
        std::string mp = "[IMG ID]\nName=test\n[END-IMG ID]\n\n[POLYLINE]\nType=0xc\nData0=";
        for (int i = 0; i <= 12; ++i) {
            const double a = 2 * std::acos(-1.0) * (i % 12) / 12;
            mp += QString::asprintf("%s(%.6f,%.6f)", i ? "," : "", 52.1 + 0.0003 * std::sin(a),
                                    21.0 + 0.0005 * std::cos(a))
                      .toStdString();
        }
        mp += "\n[END]\n\n";
        Fixture f(mp.c_str());
        MapView view(&f.scene);
        view.set_projection(&f.map->projection());
        view.resize(800, 600);
        view.show();
        QVERIFY(QTest::qWaitForWindowExposed(&view));
        const PointF center = *f.map->objects()[0].data->centroid(0, false);
        view.centerOn(QPointF(center.x, center.y));
        f.scene.set_tool(Tool::EditNodes);
        f.select_only(f.scene.item_for_object(0));
        const double angle0 = node_angle(center, f.node(0, 0, 3));
        // srodek ronda
        send_wheel(view.viewport(), view.mapFromScene(QPointF(center.x, center.y)), 120, Qt::ShiftModifier);
        QCOMPARE(f.stack.count(), 1);
        QVERIFY(qAbs(node_angle(center, f.node(0, 0, 3)) - (angle0 - 1)) < 1e-6);
        // 3 piksele od wezla na zewnatrz ronda
        auto outside_node = [&] {
            const Node& n = f.node(0, 0, 3);
            const QPointF radial = QPointF(n.x() - center.x, n.y() - center.y);
            const QPointF unit = radial / std::hypot(radial.x(), radial.y());
            return view.mapFromScene(QPointF(n.x(), n.y())) + (unit * 3).toPoint();
        };
        send_wheel(view.viewport(), outside_node(), 120, Qt::ShiftModifier);
        QVERIFY(qAbs(node_angle(center, f.node(0, 0, 3)) - (angle0 - 2)) < 1e-6);
        // daleko poza rondem - bez obrotu
        send_wheel(view.viewport(), view.mapFromScene(QPointF(center.x, center.y)) + QPoint(300, 0), 120,
                   Qt::ShiftModifier);
        QVERIFY(qAbs(node_angle(center, f.node(0, 0, 3)) - (angle0 - 2)) < 1e-6);
        QCOMPARE(f.stack.count(), 1);
    }
}

void EditTests::viaduct_pois_at_crossings() {
    // A pozioma (3 wezly), B przecina A, C krzyzuje sie z A we wspolnym wezle (zwykle skrzyzowanie), D daleko
    Fixture f(
        "[IMG ID]\nName=test\n[END-IMG ID]\n\n"
        "[POLYLINE]\nType=0x6\nData0=(52.10000,21.00000),(52.10000,21.00150),(52.10000,21.00300)\n[END]\n\n"
        "[POLYLINE]\nType=0x6\nData0=(52.09900,21.00050),(52.10100,21.00050)\n[END]\n\n"
        "[POLYLINE]\nType=0x6\nData0=(52.09900,21.00150),(52.10000,21.00150),(52.10100,21.00150)\n[END]\n\n"
        "[POLYLINE]\nType=0x6\nData0=(52.10500,21.00000),(52.10500,21.00300)\n[END]\n\n");
    auto select = [&](std::initializer_list<size_t> objs) {
        f.scene.clearSelection();
        for (size_t i : objs) f.scene.item_for_object(i)->graphics_item()->setSelected(true);
    };
    bool changed = true;
    select({0});
    QVERIFY(f.scene.add_viaduct_pois(&changed).contains("co najmniej dwie"));
    QVERIFY(!changed);
    select({0, 3});
    QCOMPARE(f.scene.add_viaduct_pois(&changed), QString("Nie znaleziono przecięć zaznaczonych dróg."));
    QVERIFY(!changed);
    select({0, 2});  // wspolny wezel - skrzyzowanie, nie wiadukt
    QCOMPARE(f.scene.add_viaduct_pois(&changed), QString("Nie znaleziono przecięć zaznaczonych dróg."));
    QCOMPARE(f.stack.count(), 0);

    // A + B + C: jedno przeciecie (A z B); B i C sie nie przecinaja
    select({0, 1, 2});
    QCOMPARE(f.scene.add_viaduct_pois(&changed), QString("Dodano bojki wiadukt: 1"));
    QVERIFY(changed);
    QCOMPARE(f.stack.count(), 1);
    QCOMPARE(f.stack.text(0), QString("Dodaj bojki wiadukt (1)"));
    const auto& objects = f.map->objects();
    QCOMPARE(objects.size(), size_t{5});
    const MapObject& poi = objects.back();
    QCOMPARE(poi.kind(), ObjectKind::Poi);
    QCOMPARE(poi.type.value_or(0), VIADUCT_POI_TYPE);
    const PointF b0 = f.node(1, 0, 0).pos();
    const PointF a0 = f.node(0, 0, 0).pos();
    const PointF at = poi.data->raw_polys()[0][0][0].pos();
    QVERIFY(std::hypot(at.x - b0.x, at.y - a0.y) < 1e-3);  // x drogi B, y drogi A
    QVERIFY(f.map->to_mp_string().find("Type=0x1709") != std::string::npos);
    QVERIFY(f.scene.item_for_object(4) != nullptr);

    // ponownie - POI juz stoi, nic nie dodaje
    QCOMPARE(f.scene.add_viaduct_pois(&changed), QString("Wszystkie przecięcia (1) mają już POI wiadukt."));
    QVERIFY(!changed);
    QCOMPARE(f.stack.count(), 1);
    f.stack.undo();
    QVERIFY(f.map->objects()[4].deleted);
    QCOMPARE(f.map->to_mp_string(), f.original);
}

void EditTests::dead_end_pois_at_unconnected_ends() {
    Fixture f(
        "[IMG ID]\nName=test\n[END-IMG ID]\n\n"
        // 0 A: poczatek styka sie tylko z kolejka (nie droga), koniec ma wspolny wezel z C
        "[POLYLINE]\nType=0x6\nData0=(52.10000,21.00000),(52.10000,21.00100),(52.10000,21.00200)\n[END]\n\n"
        // 1 B: zaczyna sie w srodkowym wezle A
        "[POLYLINE]\nType=0x6\nData0=(52.10000,21.00100),(52.10100,21.00100)\n[END]\n\n"
        // 2 C: zaczyna sie na koncu A
        "[POLYLINE]\nType=0x6\nData0=(52.10000,21.00200),(52.10100,21.00250)\n[END]\n\n"
        // 3 kolej przy poczatku A
        "[POLYLINE]\nType=0x14\nData0=(52.10000,21.00000),(52.09900,21.00000)\n[END]\n\n"
        // 4 rondo (zamkniete)
        "[POLYLINE]\nType=0xc\nData0=(52.10500,21.00000),(52.10500,21.00050),(52.10550,21.00050),"
        "(52.10500,21.00000)\n[END]\n\n"
        // 5 D: osobna droga
        "[POLYLINE]\nType=0x6\nData0=(52.10800,21.00000),(52.10800,21.00100)\n[END]\n\n");
    auto select = [&](std::initializer_list<size_t> objs) {
        f.scene.clearSelection();
        for (size_t i : objs) f.scene.item_for_object(i)->graphics_item()->setSelected(true);
    };
    auto pois_at = [&](const PointF& p) {
        int n = 0;
        for (const MapObject& obj : f.map->objects())
            if (!obj.deleted && obj.kind() == ObjectKind::Poi && obj.type.value_or(0) == DEAD_END_POI_TYPE &&
                std::hypot(obj.data->raw_polys()[0][0][0].x() - p.x, obj.data->raw_polys()[0][0][0].y() - p.y) < 1e-3)
                ++n;
        return n;
    };
    bool changed = true;
    f.scene.clearSelection();
    QCOMPARE(f.scene.add_dead_end_pois(&changed), QString("Zaznacz co najmniej jedną drogę."));
    QVERIFY(!changed);
    select({4});
    QVERIFY(f.scene.add_dead_end_pois(&changed).startsWith("Nie znaleziono ślepych końców"));
    QCOMPARE(f.stack.count(), 0);

    // A: tylko poczatek (kolej nie jest droga); koniec polaczony z C
    select({0});
    QCOMPARE(f.scene.add_dead_end_pois(&changed), QString("Dodano bojki ślepy: 1"));
    QVERIFY(changed);
    QCOMPARE(f.stack.text(0), QString("Dodaj bojki ślepy (1)"));
    QCOMPARE(pois_at(f.node(0, 0, 0).pos()), 1);
    QCOMPARE(pois_at(f.node(0, 0, 2).pos()), 0);

    // B, C, D: konce B i C (poczatki polaczone z A) i oba konce D
    select({1, 2, 5});
    QCOMPARE(f.scene.add_dead_end_pois(&changed), QString("Dodano bojki ślepy: 4"));
    QCOMPARE(pois_at(f.node(1, 0, 0).pos()), 0);
    QCOMPARE(pois_at(f.node(1, 0, 1).pos()), 1);
    QCOMPARE(pois_at(f.node(2, 0, 0).pos()), 0);
    QCOMPARE(pois_at(f.node(2, 0, 1).pos()), 1);
    QCOMPARE(pois_at(f.node(5, 0, 0).pos()), 1);
    QCOMPARE(pois_at(f.node(5, 0, 1).pos()), 1);
    QVERIFY(f.map->to_mp_string().find("Type=0x1708") != std::string::npos);

    // ponownie A - POI juz jest
    select({0});
    QCOMPARE(f.scene.add_dead_end_pois(&changed), QString("Wszystkie ślepe końce (1) mają już POI ślepy."));
    QVERIFY(!changed);
    QCOMPARE(f.stack.count(), 2);
    f.stack.undo();
    f.stack.undo();
    QCOMPARE(f.map->to_mp_string(), f.original);
}

void EditTests::map_level_for_scale_ranges() {
    QCOMPARE(map_level_for_scale(0), 0);
    QCOMPARE(map_level_for_scale(2500), 0);
    QCOMPARE(map_level_for_scale(9999), 0);
    QCOMPARE(map_level_for_scale(10000), 1);
    QCOMPARE(map_level_for_scale(49999), 1);
    QCOMPARE(map_level_for_scale(50000), 2);
    QCOMPARE(map_level_for_scale(199999), 2);
    QCOMPARE(map_level_for_scale(200000), 3);
    QCOMPARE(map_level_for_scale(999999), 3);
    QCOMPARE(map_level_for_scale(1000000), 4);
    QCOMPARE(map_level_for_scale(5e7), 4);
}

void EditTests::marker_poi_key_sequences() {
    // skroty d,w (bojki wiadukt) i d,s (bojki slepy); dzialaja tez po otwarciu menu Tools bez zaznaczenia,
    // ktore ukrywa te akcje (ukryta akcja nie reaguje na skrot)
    QTemporaryDir dir;
    QVERIFY(dir.isValid());
    qputenv("PWMAPEDIT_SETTINGS", dir.filePath("settings.ini").toUtf8());
    const QString map_file = dir.filePath("mapa.mp");
    {
        QFile f(map_file);
        QVERIFY(f.open(QIODevice::WriteOnly));
        f.write("[IMG ID]\nName=test\n[END-IMG ID]\n\n"
                "[POLYLINE]\nType=0x6\nData0=(52.10000,21.00000),(52.10000,21.00300)\n[END]\n\n"
                "[POLYLINE]\nType=0x6\nData0=(52.09900,21.00150),(52.10100,21.00150)\n[END]\n\n");
    }
    MainWindow w(MapStyles::find_icons_dir());
    w.set_quiet(true);
    w.show();
    QApplication::setActiveWindow(&w);
    QVERIFY(QTest::qWaitForWindowActive(&w));
    QSignalSpy loaded(&w, &MainWindow::map_loaded);
    w.open_file(map_file);
    QVERIFY(loaded.wait(10000));
    QMenu* tools = nullptr;
    for (QMenu* m : w.findChildren<QMenu*>())
        if (m->title() == "&Tools" || m->title() == "Tools") tools = m;
    QVERIFY(tools);
    emit tools->aboutToShow();  // nic nie zaznaczone - akcje bojek ukryte
    emit tools->aboutToHide();

    auto count_type = [&](long long type) {
        int n = 0;
        for (const MapObject& o : w.scene()->map()->objects())
            if (o.kind() == ObjectKind::Poi && o.type && *o.type == type) ++n;
        return n;
    };
    for (size_t i : {0, 1}) w.scene()->item_for_object(i)->graphics_item()->setSelected(true);
    w.view()->setFocus();
    QTest::keyClick(w.view(), Qt::Key_D);
    QTest::keyClick(w.view(), Qt::Key_W);
    QCOMPARE(count_type(0x1709), 1);

    w.scene()->clearSelection();
    for (size_t i : {0, 1}) w.scene()->item_for_object(i)->graphics_item()->setSelected(true);
    QTest::keyClick(w.view(), Qt::Key_D);
    QTest::keyClick(w.view(), Qt::Key_S);
    QCOMPARE(count_type(0x1708), 4);  // cztery wolne konce
    w.scene()->undo_stack()->setClean();  // bez pytania o zapis przy zamykaniu
}

void EditTests::auto_map_level_follows_scale() {
    QTemporaryDir dir;
    QVERIFY(dir.isValid());
    qputenv("PWMAPEDIT_SETTINGS", dir.filePath("settings.ini").toUtf8());
    const QString map_file = dir.filePath("mapa.mp");
    {
        QFile f(map_file);
        QVERIFY(f.open(QIODevice::WriteOnly));
        f.write(SAMPLE_MAP);
    }
    auto auto_action = [](MainWindow& w) -> QAction* {
        for (QAction* act : w.findChildren<QAction*>())
            if (act->text().startsWith("&Automatycznie")) return act;
        return nullptr;
    };
    auto expected_level = [](MainWindow& w) { return map_level_for_scale(w.view()->ruler()->map_scale()); };
    {
        // tryb automatyczny wlaczony od uruchomienia
        MainWindow w(MapStyles::find_icons_dir());
        QAction* act = auto_action(w);
        QVERIFY(act);
        QVERIFY(act->isCheckable() && act->isChecked() && w.auto_map_level());
        QCOMPARE(act->actionGroup()->isExclusive(), true);  // jedna kropka: poziomy albo Automatycznie
        QString status;
        QObject::connect(w.view(), &MapView::status_message, &w, [&](const QString& text) { status = text; });
        w.show();
        QSignalSpy loaded(&w, &MainWindow::map_loaded);
        w.open_file(map_file);
        QVERIFY(loaded.wait(10000));
        QVERIFY(w.auto_map_level());
        QCOMPARE(w.scene()->map_level(), expected_level(w));
        QVERIFY(act->text().contains(QString("Level %1").arg(w.scene()->map_level())));
        QVERIFY2(status.endsWith(QString("map level: %1").arg(w.scene()->map_level())), qPrintable(status));

        // oddalanie az skala wypadnie w innym przedziale - poziom zmienia sie sam (z opoznieniem)
        const int start = w.scene()->map_level();
        for (int i = 0; i < 200 && expected_level(w) == start; ++i) w.view()->zoom_out();
        QVERIFY(expected_level(w) != start);
        QTRY_COMPARE_WITH_TIMEOUT(w.scene()->map_level(), expected_level(w), 5000);
        QVERIFY(w.scene()->map_level() > start);
        // pasek stanu pokazuje nowy poziom
        QVERIFY2(status.endsWith(QString("map level: %1").arg(w.scene()->map_level())), qPrintable(status));
        // i z powrotem przy przyblizaniu
        for (int i = 0; i < 200 && expected_level(w) != start; ++i) w.view()->zoom_in();
        QTRY_COMPARE_WITH_TIMEOUT(w.scene()->map_level(), start, 5000);
        QVERIFY2(status.endsWith(QString("map level: %1").arg(start)), qPrintable(status));
    }
    {
        // wybor konkretnego poziomu wylacza tryb automatyczny
        MainWindow w(MapStyles::find_icons_dir());
        QVERIFY(w.auto_map_level());
        w.show();
        QSignalSpy loaded(&w, &MainWindow::map_loaded);
        w.open_file(map_file);
        QVERIFY(loaded.wait(10000));
        QCOMPARE(w.scene()->map_level(), expected_level(w));
        const int other = expected_level(w) == 1 ? 2 : 1;
        w.select_map_level(other);
        QVERIFY(!w.auto_map_level());
        QVERIFY(!auto_action(w)->isChecked());
        QCOMPARE(w.scene()->map_level(), other);
        // zmiana skali nie zmienia juz poziomu
        for (int i = 0; i < 30; ++i) w.view()->zoom_out();
        QTest::qWait(MainWindow::AUTO_LEVEL_DELAY_MS * 2);
        QCOMPARE(w.scene()->map_level(), other);

        // klawisz '.' wlacza tryb automatyczny, cyfra wybiera poziom i go wylacza
        QApplication::setActiveWindow(&w);
        QVERIFY(QTest::qWaitForWindowActive(&w));
        w.view()->setFocus();
        QTest::keyClick(w.view(), Qt::Key_Period);
        QVERIFY(w.auto_map_level());
        QCOMPARE(w.scene()->map_level(), expected_level(w));
        QTest::keyClick(w.view(), Qt::Key_Period);  // ponowne wcisniecie nie wylacza
        QVERIFY(w.auto_map_level());
        const int digit_level = expected_level(w) == 1 ? 2 : 1;
        QTest::keyClick(w.view(), Qt::Key(Qt::Key_0 + digit_level));
        QVERIFY(!w.auto_map_level());
        QCOMPARE(w.scene()->map_level(), digit_level);

        // kropka w polu tekstowym (etykieta "ul. Dluga") wpisuje sie i nie wlacza trybu automatycznego
        w.scene()->item_for_object(1)->graphics_item()->setSelected(true);
        QLineEdit* label = w.properties_dock()->label_edit(1);
        QVERIFY(label->isEnabled());
        label->setFocus();
        label->clear();
        QTest::keyClicks(label, "ul. Dluga");
        QCOMPARE(label->text(), QString("ul. Dluga"));
        QVERIFY(!w.auto_map_level());
    }
    {
        // wybor konkretnego poziomu nie jest zapamietywany - kolejne uruchomienie znow w trybie automatycznym
        MainWindow w(MapStyles::find_icons_dir());
        QVERIFY(w.auto_map_level());
    }
    qunsetenv("PWMAPEDIT_SETTINGS");
}

void EditTests::dock_prev_next_node_buttons() {
    // Poprzedni/Nastepny: wezly kolejnych czesci poziomu Data po kolei, przyciski wyszarzone na koncach,
    // widok przewijany do wezla, ktorego nie widac.
    DockFixture f;
    QMimeData mime;
    mime.setText("[POLYLINE]\nType=0x6\nData0=(52.1000,21.0000),(52.1002,21.0002)\n"
                 "Data0=(52.1015,21.0025),(52.1017,21.0027),(52.1019,21.0029)\n[END]\n");
    QCOMPARE(f.scene.paste(&mime, std::nullopt), 1);
    const size_t obj = f.map->objects().size() - 1;
    MapView view(&f.scene);
    view.set_projection(&f.map->projection());
    view.resize(400, 300);
    view.show();
    QVERIFY(QTest::qWaitForWindowExposed(&view));
    const auto& polys = *f.obj(obj).data->polys_for_data_level(0);
    view.centerOn(QPointF(polys[0][0].x(), polys[0][0].y()));
    view.scale(20, 20);
    view.centerOn(QPointF(polys[0][0].x(), polys[0][0].y()));
    const QPointF last(polys[1][2].x(), polys[1][2].y());
    QVERIFY(!view.viewport()->rect().contains(view.mapFromScene(last)));

    f.scene.set_tool(Tool::EditNodes);
    f.select_only(f.scene.item_for_object(obj));
    f.scene.set_active_grip(obj, 0, 0, 0);
    QVERIFY(f.dock.shows_node());
    QVERIFY(!f.dock.prev_node()->isEnabled());
    QVERIFY(f.dock.next_node()->isEnabled());
    const int start = f.stack.count();

    f.dock.next_node()->click();
    QCOMPARE(f.scene.active_grip()->poly, size_t(0));
    QCOMPARE(f.scene.active_grip()->node, size_t(1));
    f.dock.next_node()->click();  // druga czesc
    QCOMPARE(f.scene.active_grip()->poly, size_t(1));
    QCOMPARE(f.scene.active_grip()->node, size_t(0));
    QVERIFY(f.dock.prev_node()->isEnabled());
    f.dock.next_node()->click();
    f.dock.next_node()->click();
    QCOMPARE(f.scene.active_grip()->node, size_t(2));
    QVERIFY(f.dock.shows_node());
    QVERIFY(!f.dock.next_node()->isEnabled());
    QVERIFY(f.dock.prev_node()->isEnabled());
    QVERIFY(view.viewport()->rect().contains(view.mapFromScene(last)));  // widok przesuniety

    f.dock.prev_node()->click();
    QCOMPARE(f.scene.active_grip()->node, size_t(1));
    f.dock.prev_node()->click();
    f.dock.prev_node()->click();  // z powrotem na ostatni wezel pierwszej czesci
    QCOMPARE(f.scene.active_grip()->poly, size_t(0));
    QCOMPARE(f.scene.active_grip()->node, size_t(1));
    QCOMPARE(f.stack.count(), start);  // przechodzenie niczego nie zmienia
}

void EditTests::node_step_shortcuts() {
    // N/P z fokusem na mapie przechodza po wezlach tylko przy pokazanej karcie wezlow.
    QTemporaryDir dir;
    QVERIFY(dir.isValid());
    qputenv("PWMAPEDIT_SETTINGS", dir.filePath("settings.ini").toUtf8());
    const QString map_file = dir.filePath("mapa.mp");
    {
        QFile f(map_file);
        QVERIFY(f.open(QIODevice::WriteOnly));
        f.write("[IMG ID]\nName=test\n[END-IMG ID]\n\n"
                "[POLYLINE]\nType=0x6\nData0=(52.10000,21.00000),(52.10000,21.00100),(52.10000,21.00200)\n"
                "[END]\n\n");
    }
    MainWindow w(MapStyles::find_icons_dir());
    w.set_quiet(true);
    w.show();
    QApplication::setActiveWindow(&w);
    QVERIFY(QTest::qWaitForWindowActive(&w));
    QSignalSpy loaded(&w, &MainWindow::map_loaded);
    w.open_file(map_file);
    QVERIFY(loaded.wait(10000));
    MapScene* scene = w.scene();

    // bez trybu edycji wezlow karta wezlow jest ukryta - N nic nie robi
    scene->item_for_object(0)->graphics_item()->setSelected(true);
    w.view()->setFocus();
    QTest::keyClick(w.view(), Qt::Key_N);
    QVERIFY(!scene->active_grip());

    scene->set_tool(Tool::EditNodes);
    scene->clearSelection();
    scene->item_for_object(0)->graphics_item()->setSelected(true);
    scene->set_active_grip(0, 0, 0, 0);
    QVERIFY(w.properties_dock()->shows_node());
    w.view()->setFocus();    QTest::keyClick(w.view(), Qt::Key_N);
    QCOMPARE(scene->active_grip()->node, size_t(1));
    QTest::keyClick(w.view(), Qt::Key_N);
    QCOMPARE(scene->active_grip()->node, size_t(2));
    QTest::keyClick(w.view(), Qt::Key_N);  // ostatni wezel - przycisk wylaczony, skrot tez
    QCOMPARE(scene->active_grip()->node, size_t(2));
    QTest::keyClick(w.view(), Qt::Key_P);
    QCOMPARE(scene->active_grip()->node, size_t(1));
    w.scene()->undo_stack()->setClean();  // bez pytania o zapis przy zamykaniu
    qunsetenv("PWMAPEDIT_SETTINGS");
}

QTEST_MAIN(EditTests)
#include "test_edit.moc"
