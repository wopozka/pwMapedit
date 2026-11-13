// Testy edycji w GUI (etap 3b): komendy undo/redo na scenie oraz przeciaganie obiektu mysza.
// Uruchamiane bez okna: gui_tests -platform offscreen (tak robi ctest).
#include <QSignalSpy>
#include <QUndoStack>
#include <QtTest>
#include <memory>

#include "map_items.hpp"
#include "map_scene.hpp"
#include "map_styles.hpp"
#include "map_view.hpp"

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

QTEST_MAIN(EditTests)
#include "test_edit.moc"
