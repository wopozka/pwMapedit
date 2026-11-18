#include "bench.hpp"

#include <QDateTime>
#include <QElapsedTimer>
#include <QFile>
#include <QFileInfo>
#include <QGraphicsScene>
#include <QTextStream>

#include "main_window.hpp"
#include "map_scene.hpp"
#include "constants.hpp"
#include "map_view.hpp"

namespace pwm::gui {

namespace {

bool bsp_mode(const IndexBenchOptions& opt) { return opt.index != QLatin1String("none"); }

void enable_bsp(QGraphicsScene* scene, int depth) {
    scene->setItemIndexMethod(QGraphicsScene::BspTreeIndex);
    // glebokosc jest zapisana w obiekcie indeksu - po kazdym setItemIndexMethod trzeba ja ustawic od nowa
    if (depth < 0) depth = SCENE_BSP_TREE_DEPTH;
    if (depth > 0) scene->setBspTreeDepth(depth);
}

double elapsed_ms(const QElapsedTimer& t) { return static_cast<double>(t.nsecsElapsed()) / 1e6; }

class Bench {
public:
    Bench(MainWindow& window, const IndexBenchOptions& opt) : w_(window), opt_(opt) {}

    // Rysowanie calego widoku synchronicznie. Pierwsze po zmianie zawiera leniwa budowe indeksu BSP.
    double paint() {
        QElapsedTimer t;
        t.start();
        w_.view()->viewport()->repaint();
        return elapsed_ms(t);
    }

    // Jak hover: QGraphicsView::items(QPoint) w kilku punktach przy srodku widoku, srednia.
    double hover() {
        const QPoint c = w_.view()->viewport()->rect().center();
        const int n = 10;
        QElapsedTimer t;
        t.start();
        for (int i = 0; i < n; ++i) (void)w_.view()->items(c + QPoint(7 * i, 5 * i));
        return elapsed_ms(t) / n;
    }

    void step(const QString& name, double action_ms, const QString& note = QString()) {
        const double p1 = paint();
        const double p2 = paint();
        const double h = hover();
        rows_ << QStringLiteral("%1 %2 %3 %4 %5  %6")
                     .arg(name, -24)
                     .arg(action_ms, 10, 'f', 1)
                     .arg(p1, 10, 'f', 1)
                     .arg(p2, 10, 'f', 1)
                     .arg(h, 10, 'f', 1)
                     .arg(note);
    }

    void zoom(int steps) {
        QElapsedTimer t;
        t.start();
        for (int i = 0; i < steps; ++i) w_.view()->zoom_in();
        for (int i = 0; i < -steps; ++i) w_.view()->zoom_out();
        const double ms = elapsed_ms(t);
        step(QStringLiteral("zoom %1%2").arg(steps > 0 ? "+" : "").arg(steps), ms);
    }

    void level(int level) {
        QGraphicsScene* scene = w_.scene();
        const bool toggle = opt_.index == QLatin1String("bsp-toggle");
        double off = 0, on = 0;
        QElapsedTimer total;
        total.start();
        if (toggle) {
            QElapsedTimer t;
            t.start();
            scene->setItemIndexMethod(QGraphicsScene::NoIndex);
            off = elapsed_ms(t);
        }
        QElapsedTimer t;
        t.start();
        w_.select_map_level(level);
        const double change = elapsed_ms(t);
        if (toggle) {
            QElapsedTimer t2;
            t2.start();
            enable_bsp(scene, opt_.bsp_depth);
            on = elapsed_ms(t2);
        }
        const double ms = elapsed_ms(total);
        step(QStringLiteral("poziom %1").arg(level), ms,
             toggle ? QStringLiteral("wyl. indeksu %1 ms, zmiana %2 ms, wl. indeksu %3 ms")
                          .arg(off, 0, 'f', 1)
                          .arg(change, 0, 'f', 1)
                          .arg(on, 0, 'f', 1)
                    : QString());
    }

    const QStringList& rows() const { return rows_; }

private:
    MainWindow& w_;
    const IndexBenchOptions& opt_;
    QStringList rows_;
};

}  // namespace

void apply_index_mode(MainWindow& window, const IndexBenchOptions& opt) {
    if (opt.index.isEmpty()) {  // indeks jak w programie; ewentualnie inna glebokosc
        if (opt.bsp_depth >= 0) enable_bsp(window.scene(), opt.bsp_depth);
        return;
    }
    if (bsp_mode(opt))
        enable_bsp(window.scene(), opt.bsp_depth);
    else
        window.scene()->setItemIndexMethod(QGraphicsScene::NoIndex);
}

bool run_index_bench(MainWindow& window, const IndexBenchOptions& opt, const QString& map_file) {
    // poziom 0 i wylaczenie trybu automatycznego - inaczej timer trybu automatycznego zmienialby poziom
    // w trakcie pomiaru (processEvents przy zmianie poziomu)
    window.select_map_level(0);

    Bench bench(window, opt);
    bench.step(QStringLiteral("start (cala mapa)"), 0);
    bench.zoom(opt.zoom);
    bench.level(opt.level);
    bench.level(0);
    bench.zoom(-opt.zoom);
    bench.level(opt.level);
    bench.level(0);

    // dopiero na koncu - items() sortuje wszystkie elementy, a przy BSP buduje indeks
    MapScene* scene = window.scene();
    const qsizetype scene_items = scene->items().size();
    const size_t objects = scene->map() ? scene->map()->objects().size() : 0;

    QFile file(opt.output);
    if (!file.open(QIODevice::WriteOnly | QIODevice::Append | QIODevice::Text)) return false;
    QTextStream out(&file);
    QString mode = opt.index.isEmpty() ? QStringLiteral("domyslny") : opt.index;
    out << "=== " << QDateTime::currentDateTime().toString(Qt::ISODate) << "  indeks: " << mode << '\n';
    out << "mapa: " << QFileInfo(map_file).fileName() << ", obiektow " << objects << ", elementow sceny "
        << scene_items << ", widok " << window.view()->viewport()->width() << 'x'
        << window.view()->viewport()->height();
    if (scene->itemIndexMethod() == QGraphicsScene::BspTreeIndex)
        out << ", indeks BSP, bspTreeDepth() " << scene->bspTreeDepth();
    else
        out << ", bez indeksu";
    out << '\n';
    out << QStringLiteral("%1 %2 %3 %4 %5  %6\n")
               .arg(QStringLiteral("krok"), -24)
               .arg(QStringLiteral("akcja ms"), 10)
               .arg(QStringLiteral("rys.1 ms"), 10)
               .arg(QStringLiteral("rys.2 ms"), 10)
               .arg(QStringLiteral("hover ms"), 10)
               .arg(QStringLiteral("uwagi"));
    for (const QString& row : bench.rows()) out << row << '\n';
    out << '\n';
    return true;
}

}  // namespace pwm::gui
