// pwMapEdit - edytor map w formacie mp (port C++/Qt6 wersji Python).
//   pwmapedit [plik.mp] [--screenshot plik.png] [--zoom N] [--level L]
// --screenshot: po wczytaniu mapy zapisuje zrzut okna i konczy program (do testow bez klikania);
// --zoom N: N razy powieksz (N > 0) albo pomniejsz (N < 0) przed zrzutem; --level L: poziom mapy.
#include <QApplication>
#include <QMessageBox>
#include <QStyleFactory>
#include <QTimer>

#include "main_window.hpp"
#include "map_styles.hpp"
#include "map_view.hpp"

int main(int argc, char* argv[]) {
    QApplication app(argc, argv);
    QApplication::setApplicationName("pwMapEdit");
    app.setStyle(QStyleFactory::create("Fusion"));

    QString file_name, screenshot;
    int zoom = 0, level = 0;
    const QStringList args = QApplication::arguments();
    for (int i = 1; i < args.size(); ++i) {
        if (args[i] == "--screenshot" && i + 1 < args.size())
            screenshot = args[++i];
        else if (args[i] == "--zoom" && i + 1 < args.size())
            zoom = args[++i].toInt();
        else if (args[i] == "--level" && i + 1 < args.size())
            level = args[++i].toInt();
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
            QTimer::singleShot(300, &window, [&] {
                if (!window.grab().save(screenshot)) QApplication::exit(2);
                else QApplication::quit();
            });
        });
    }
    if (!file_name.isEmpty()) window.open_file(file_name);
    return app.exec();
}
