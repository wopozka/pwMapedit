// pwMapEdit - edytor map w formacie mp (port C++/Qt6 wersji Python).
//   pwmapedit [plik.mp] [--screenshot plik.png] [--zoom N] [--level L] [--select N] [--edit-nodes]
//             [--weblayer osm|geoportal|google] [--gps plik.gpx]
// --screenshot: po wczytaniu mapy zapisuje zrzut okna i konczy program (do testow bez klikania);
// --zoom N: N razy powieksz (N > 0) albo pomniejsz (N < 0) przed zrzutem; --level L: poziom mapy;
// --select N: zaznacz obiekt o indeksie N i wysrodkuj na nim widok; --edit-nodes: tryb edycji wezlow;
// --weblayer: wlacz warstwe WWW (zrzut po pobraniu kafelkow, najwyzej 15 s).
#include <QApplication>
#include <QMessageBox>
#include <QStyleFactory>
#include <QElapsedTimer>
#include <QTimer>

#include "main_window.hpp"
#include "map_items.hpp"
#include "map_scene.hpp"
#include "web_layers.hpp"
#include "gps_dock.hpp"
#include "map_styles.hpp"
#include "map_view.hpp"

int main(int argc, char* argv[]) {
    QApplication app(argc, argv);
    QApplication::setApplicationName("pwMapEdit");
    app.setStyle(QStyleFactory::create("Fusion"));

    QString file_name, screenshot;
    int zoom = 0, level = 0, select = -1;
    bool edit_nodes = false;
    QString weblayer;
    QStringList gps_files;
    const QStringList args = QApplication::arguments();
    for (int i = 1; i < args.size(); ++i) {
        if (args[i] == "--screenshot" && i + 1 < args.size())
            screenshot = args[++i];
        else if (args[i] == "--zoom" && i + 1 < args.size())
            zoom = args[++i].toInt();
        else if (args[i] == "--level" && i + 1 < args.size())
            level = args[++i].toInt();
        else if (args[i] == "--select" && i + 1 < args.size())
            select = args[++i].toInt();
        else if (args[i] == "--edit-nodes")
            edit_nodes = true;
        else if (args[i] == "--weblayer" && i + 1 < args.size())
            weblayer = args[++i].toLower();
        else if (args[i] == "--gps" && i + 1 < args.size())
            gps_files << args[++i];
        else
            file_name = args[i];
    }

    QString icons_dir = pwm::gui::MapStyles::find_icons_dir();
    if (icons_dir.isEmpty() && screenshot.isEmpty()) {
        QMessageBox::warning(nullptr, "pwMapEdit",
                             "Nie znaleziono katalogu z ikonami (icons). Ustaw zmienną PWMAPEDIT_ICONS "
                             "albo umieść katalog icons obok programu.");
    }

    pwm::gui::MainWindow window(icons_dir);
    window.show();
    if (!screenshot.isEmpty()) {
        QObject::connect(&window, &pwm::gui::MainWindow::map_loaded, &window, [&](bool ok) {
            if (!ok) {
                QApplication::exit(1);
                return;
            }
            for (int i = 0; i < zoom; ++i) window.view()->zoom_in();
            for (int i = 0; i < -zoom; ++i) window.view()->zoom_out();
            if (level) window.select_map_level(level);
            if (edit_nodes) window.select_tool(pwm::gui::Tool::EditNodes);
            if (!gps_files.isEmpty()) window.load_gps_files(gps_files);
            if (select >= 0) {
                if (auto* item = window.scene()->item_for_object(static_cast<size_t>(select))) {
                    item->graphics_item()->setSelected(true);
                    window.view()->centerOn(item->graphics_item());
                }
            }
            if (!weblayer.isEmpty()) {
                const pwm::web::Layer layer = weblayer == "google"      ? pwm::web::Layer::GoogleOrto
                                              : weblayer == "geoportal" ? pwm::web::Layer::GeoportalOrto
                                                                        : pwm::web::Layer::Osm;
                window.web_layers()->set_layer(layer);
            }
            // zrzut, gdy nie ma juz pobieranych kafelkow (najwyzej po 15 s)
            auto* poll = new QTimer(&window);
            auto* waited = new QElapsedTimer;
            waited->start();
            QObject::connect(poll, &QTimer::timeout, &window, [&, poll, waited] {
                if (window.web_layers()->pending_downloads() > 0 && waited->elapsed() < 15000) return;
                poll->stop();
                delete waited;
                if (!window.grab().save(screenshot)) QApplication::exit(2);
                else QApplication::quit();
            });
            poll->start(300);
        });
    }
    if (!file_name.isEmpty()) window.open_file(file_name);
    return app.exec();
}
