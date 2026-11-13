// Testy edycji w GUI (etap 3b): komendy undo/redo na scenie oraz przeciaganie obiektu mysza.
// Uruchamiane bez okna: gui_tests -platform offscreen (tak robi ctest).
#include <QJsonArray>
#include <QJsonDocument>
#include <QMimeData>
#include <QSignalSpy>
#include <QUndoStack>
#include <QtTest>
#include <memory>

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
#include <QCheckBox>
#include <QComboBox>
#include <QLineEdit>
#include <QPlainTextEdit>
#include <QTabWidget>
#include <QTableWidget>
#include <QTreeWidget>

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

    Fixture() {
        map->load_from_string(SAMPLE_MAP);
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
    void move_polyline_undo_redo();
    void move_poi_and_undo();
    void delete_and_undo();
    void reverse_all_levels_and_undo();
    void reverse_without_polyline_does_nothing();
    void mouse_drag_moves_polyline();
    void mouse_drag_moves_poi_when_zoomed_in();
    // 3b.2: edycja wezlow
    void edit_nodes_tool_decorates_selection();
    void move_remove_insert_node_undo();
    void remove_node_keeps_minimum();
    void insert_node_extends_polyline_end();
    void split_and_merge_polyline();
    void grip_drag_ctrl_click_and_split_key();
    void shift_click_inserts_node();
    // 3b.3: panel wlasciwosci
    void dock_follows_selection();
    void dock_labels_endlevel_direction();
    void dock_type_comment_extras();
    void dock_address_and_routing();
    void dock_node_hlevel_and_numbers();
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

void EditTests::mouse_drag_moves_poi_when_zoomed_in() {
    // Powyzej skali 1 ikony POI maja ItemIgnoresTransformations - Qt przelicza wtedy ruch inaczej.
    Fixture f;
    auto* poi = static_cast<QGraphicsPixmapItem*>(f.poi()->graphics_item());
    if (poi->pixmap().isNull()) QSKIP("brak ikon POI (katalog icons nie znaleziony)");
    MapView view(&f.scene);
    view.set_projection(&f.map->projection());
    view.resize(800, 600);
    view.show();
    QVERIFY(QTest::qWaitForWindowExposed(&view));
    for (int i = 0; i < 8; ++i) view.zoom_in();
    QVERIFY(view.map_scale() > IGNORE_TRANSFORMATION_TRESHOLD);
    QVERIFY(poi->flags().testFlag(QGraphicsItem::ItemIgnoresTransformations));

    const PointF p = f.node(0, 0, 0).pos();
    view.centerOn(QPointF(p.x, p.y));
    // srodek ikony: QGraphicsPixmapItem trafia tylko w nieprzezroczyste piksele (MaskShape)
    const QPoint press = view.mapFromScene(QPointF(p.x, p.y)) + poi->boundingRect().center().toPoint();
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

QTEST_MAIN(EditTests)
#include "test_edit.moc"
