// Port pwMapEdit.py: glowne okno aplikacji (menu, pasek narzedzi, pasek stanu, otwieranie i zapis mapy).
#pragma once

#include <QFutureWatcher>
#include <QMainWindow>
#include <QPointer>
#include <memory>

#include "constants.hpp"
#include "map_data.hpp"
#include "theme.hpp"

class QActionGroup;
class QMenu;
class QSettings;
class QLabel;
class QProgressBar;
class QTimer;
class QUndoStack;
class QToolBar;

namespace pwm::gui {

class MapScene;
class MapView;
class MapStyles;
class MapRuler;
class PropertiesDock;
class WebLayers;
class GpsLayers;
class GpsDock;

struct LoadResult {
    std::unique_ptr<MapData> map;
    QString file_name;
    QString error;
    double seconds = 0;
};

class MainWindow : public QMainWindow {
    Q_OBJECT
public:
    explicit MainWindow(const QString& icons_dir, QWidget* parent = nullptr);
    ~MainWindow() override;

    void open_file(const QString& file_name);
    // Lista ostatnio otwieranych plikow (~/.pwmapedit.ini, klucz recent_files - wspolny z wersja Python).
    QStringList recent_files() const;
    void set_recent_files(const QStringList& files);
    void add_recent_file(const QString& file_name);
    // Wybor konkretnego poziomu (menu View -> Levels, klawisze 0-4) - wylacza tez tryb automatyczny.
    void select_map_level(int level);
    // View -> Levels -> Automatycznie: poziom mapy wedlug skali (map_level_for_scale), zmieniany po
    // przyblizeniu/oddaleniu. Wylacza go wybor konkretnego poziomu. Wlaczony przy kazdym uruchomieniu.
    bool auto_map_level() const;
    // Opoznienie, z jakim tryb automatyczny reaguje na zmiane skali (kilka krokow kolka myszy - jedna przebudowa).
    static constexpr int AUTO_LEVEL_DELAY_MS = 250;
    // Wybiera narzedzie tak jak z menu Tools (zaznacza tez akcje na pasku).
    void select_tool(Tool tool);
    // Tryb bez okien komunikatow (zrzuty ekranu z linii polecen): ostrzezenia trafiaja do paska stanu.
    void set_quiet(bool quiet) { quiet_ = quiet; }
    // Motyw okna (View -> Motyw); remember - zapis w ustawieniach (opcja --theme go nie zapisuje).
    void set_theme_mode(ThemeMode mode, bool remember = true);
    QToolBar* toolbar() const { return toolbar_; }

    MapView* view() const { return view_; }
    MapScene* scene() const { return scene_; }
    PropertiesDock* properties_dock() const { return properties_; }
    WebLayers* web_layers() const { return web_layers_; }
    GpsLayers* gps_layers() const { return gps_layers_; }
    // Wczytuje slady GPS (GPX) jako podklad; bledy pokazuje w oknie komunikatu. Zwraca liczbe wczytanych plikow.
    int load_gps_files(const QStringList& files);
    QProgressBar* progress_bar() const { return progress_bar_; }

signals:
    void map_loaded(bool ok);

protected:
    void closeEvent(QCloseEvent* event) override;
    // przeciagniecie plikow na okno: *.mp otwiera mape, *.gpx wczytuje slady
    void dragEnterEvent(QDragEnterEvent* event) override;
    void dropEvent(QDropEvent* event) override;

private slots:
    void open_file_dialog();
    void file_loaded();
    void save_map();
    void save_map_as();
    void copy_action();
    void load_gps_dialog();
    void delete_action();
    void fill_recent_files_menu();
    void open_recent_file(const QString& file_name);
    void cut_action();
    void paste_action();
    void go_to_position();
    void set_progress(int value, int maximum);
    void escape_pressed();
    void merge_polylines();
    void subtract_polygons(bool delete_second);
    void convert_selected(ObjectKind from);
    // Tools -> Dodaj bojki wiadukt (MapScene::add_viaduct_pois); bez zmian - okno z informacja.
    void add_viaduct_pois();
    // Tools -> Dodaj bojki ślepy (MapScene::add_dead_end_pois); bez zmian - okno z informacja.
    void add_dead_end_pois();
    void set_single_key_shortcuts_enabled(bool enabled);
    // Tryb automatyczny: ustawia poziom wedlug biezacej skali (bez zmiany, gdy poziom sie zgadza).
    void update_auto_map_level();

private:
    void create_actions_and_menus();
    void create_toolbar();
    // Arkusz stylu paska i ikony w kolorach biezacego motywu (po kazdej zmianie motywu).
    void apply_theme();
    void create_shortcuts();
    bool write_map(const QString& file_name);
    // Niezapisane zmiany: Zapisz / Nie zapisuj / Anuluj. Zwraca true, gdy mozna kontynuowac (zamkniecie,
    // otwarcie innego pliku) - po udanym zapisie albo rezygnacji z zapisu.
    bool confirm_discard_changes(const QString& title);
    bool focus_in_extras() const;
    void update_window_title();
    void show_message(const QString& text);
    bool focus_in_properties() const;

    std::unique_ptr<MapStyles> styles_;
    std::unique_ptr<MapData> map_;
    std::unique_ptr<Projection> default_projection_;
    QString map_file_name_;
    MapScene* scene_ = nullptr;
    MapView* view_ = nullptr;
    MapRuler* ruler_ = nullptr;
    PropertiesDock* properties_ = nullptr;
    WebLayers* web_layers_ = nullptr;
    GpsLayers* gps_layers_ = nullptr;
    GpsDock* gps_dock_ = nullptr;
    QActionGroup* web_layer_group_ = nullptr;
    QAction* last_web_layer_action_ = nullptr;
    QMenu* recent_files_menu_ = nullptr;
    QSettings* settings_ = nullptr;
    QToolBar* toolbar_ = nullptr;
    QList<QPair<QPointer<QAction>, QString>> toolbar_icons_;
    QList<QAction*> theme_actions_;
    bool quiet_ = false;
    QUndoStack* undo_stack_ = nullptr;
    QProgressBar* progress_bar_ = nullptr;
    QLabel* info_text_ = nullptr;
    QLabel* message_label_ = nullptr;
    QActionGroup* map_level_group_ = nullptr;
    QList<QAction*> map_level_actions_;
    QAction* auto_level_action_ = nullptr;
    QTimer* auto_level_timer_ = nullptr;
    QActionGroup* tools_group_ = nullptr;
    QAction* split_action_ = nullptr;
    QAction* merge_action_ = nullptr;
    QFutureWatcher<std::shared_ptr<LoadResult>>* load_watcher_ = nullptr;
    QString icons_dir_;
};

}  // namespace pwm::gui
