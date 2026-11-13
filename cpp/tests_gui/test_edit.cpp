// Testy edycji w GUI (etap 3b): komendy undo/redo na scenie oraz przeciaganie obiektu mysza.
// Uruchamiane bez okna: gui_tests -platform offscreen (tak robi ctest).
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

QTEST_MAIN(EditTests)
#include "test_edit.moc"
