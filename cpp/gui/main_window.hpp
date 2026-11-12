// Port pwMapEdit.py: glowne okno aplikacji (menu, pasek narzedzi, pasek stanu, otwieranie i zapis mapy).
#pragma once

#include <QFutureWatcher>
#include <QMainWindow>
#include <memory>

#include "constants.hpp"
#include "map_data.hpp"

class QActionGroup;
class QLabel;
class QProgressBar;
class QUndoStack;

namespace pwm::gui {

class MapScene;
class MapView;
class MapStyles;
class MapRuler;

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
    void select_map_level(int level);

    MapView* view() const { return view_; }
    MapScene* scene() const { return scene_; }

signals:
    void map_loaded(bool ok);

protected:
    void closeEvent(QCloseEvent* event) override;

private slots:
    void open_file_dialog();
    void file_loaded();
    void save_map();
    void save_map_as();
    void copy_action();
    void go_to_position();
    void set_progress(int value, int maximum);
    void escape_pressed();

private:
    void create_actions_and_menus();
    void create_toolbar();
    void create_shortcuts();
    bool write_map(const QString& file_name);
    void update_window_title();
    void show_message(const QString& text);

    std::unique_ptr<MapStyles> styles_;
    std::unique_ptr<MapData> map_;
    std::unique_ptr<Projection> default_projection_;
    QString map_file_name_;
    MapScene* scene_ = nullptr;
    MapView* view_ = nullptr;
    MapRuler* ruler_ = nullptr;
    QUndoStack* undo_stack_ = nullptr;
    QProgressBar* progress_bar_ = nullptr;
    QLabel* info_text_ = nullptr;
    QLabel* message_label_ = nullptr;
    QActionGroup* map_level_group_ = nullptr;
    QList<QAction*> map_level_actions_;
    QActionGroup* tools_group_ = nullptr;
    QFutureWatcher<std::shared_ptr<LoadResult>>* load_watcher_ = nullptr;
    QString icons_dir_;
};

}  // namespace pwm::gui
