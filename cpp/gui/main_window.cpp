#include "main_window.hpp"

#include <QAction>
#include <QActionGroup>
#include <QApplication>
#include <QClipboard>
#include <QCloseEvent>
#include <QDir>
#include <QElapsedTimer>
#include <QFile>
#include <QFileDialog>
#include <QFileInfo>
#include <QInputDialog>
#include <QKeySequence>
#include <QLabel>
#include <QMenuBar>
#include <QMessageBox>
#include <QProgressBar>
#include <QSaveFile>
#include <QShortcut>
#include <QStatusBar>
#include <QToolBar>
#include <QUndoStack>
#include <QtConcurrent/QtConcurrentRun>

#include "map_items.hpp"
#include "map_scene.hpp"
#include "map_styles.hpp"
#include "map_view.hpp"

namespace pwm::gui {

namespace {

std::shared_ptr<LoadResult> load_map_file(const QString& file_name) {
    auto result = std::make_shared<LoadResult>();
    result->file_name = file_name;
    QElapsedTimer timer;
    timer.start();
    QFile file(file_name);
    if (!file.open(QIODevice::ReadOnly)) {
        result->error = QObject::tr("Nie można otworzyć pliku: %1").arg(file.errorString());
        return result;
    }
    QByteArray bytes = file.readAll();
    try {
        auto map = std::make_unique<MapData>(std::make_unique<MercatorProjection>());
        map->load_from_string(std::string(bytes.constData(), static_cast<size_t>(bytes.size())));
        result->map = std::move(map);
    } catch (const std::exception& e) {
        result->error = QObject::tr("Błąd wczytywania pliku: %1").arg(QString::fromLocal8Bit(e.what()));
    }
    result->seconds = timer.elapsed() / 1000.0;
    return result;
}

}  // namespace

MainWindow::MainWindow(const QString& icons_dir, QWidget* parent)
    : QMainWindow(parent), icons_dir_(icons_dir) {
    styles_ = std::make_unique<MapStyles>(icons_dir_);
    default_projection_ = std::make_unique<MercatorProjection>();
    undo_stack_ = new QUndoStack(this);

    auto* status = new QStatusBar(this);
    progress_bar_ = new QProgressBar(status);
    progress_bar_->setMaximumWidth(200);
    info_text_ = new QLabel(status);
    message_label_ = new QLabel(status);
    status->addWidget(progress_bar_);
    status->addWidget(info_text_);
    status->addPermanentWidget(message_label_);
    setStatusBar(status);

    scene_ = new MapScene(this);
    scene_->setSceneRect(0, 0, 400, 200);
    view_ = new MapView(scene_, this);
    view_->set_projection(default_projection_.get());
    setCentralWidget(view_);
    ruler_ = new MapRuler(view_, default_projection_.get());
    scene_->add_persistent_item(ruler_);
    view_->set_ruler(ruler_);

    connect(scene_, &MapScene::progress, this, &MainWindow::set_progress);
    connect(view_, &MapView::status_message, info_text_, &QLabel::setText);
    connect(undo_stack_, &QUndoStack::cleanChanged, this, &MainWindow::update_window_title);

    create_actions_and_menus();
    create_toolbar();
    create_shortcuts();
    update_window_title();
    resize(1200, 800);
}

MainWindow::~MainWindow() {
    // elementy sceny wskazuja na map_, wiec trzeba je usunac wczesniej
    if (load_watcher_) load_watcher_->waitForFinished();
    // widok nie moze odwolywac sie do linijki i sceny w trakcie ich niszczenia
    view_->set_ruler(nullptr);
    view_->setScene(nullptr);
    scene_->clear_map();
}

void MainWindow::create_actions_and_menus() {
    QMenu* file_menu = menuBar()->addMenu(tr("&File"));
    QAction* open = file_menu->addAction(tr("&Open"), this, &MainWindow::open_file_dialog);
    open->setShortcut(QKeySequence::Open);
    file_menu->addSeparator();
    QAction* save = file_menu->addAction(tr("&Save map"), this, &MainWindow::save_map);
    save->setShortcut(QKeySequence::Save);
    QAction* save_as = file_menu->addAction(tr("Save map &as"), this, &MainWindow::save_map_as);
    save_as->setShortcut(QKeySequence::SaveAs);
    file_menu->addSeparator();
    file_menu->addAction(tr("&Zamknij"), this, &QWidget::close);

    QMenu* edit_menu = menuBar()->addMenu(tr("&Edit"));
    QAction* undo = undo_stack_->createUndoAction(this, tr("&Undo"));
    undo->setShortcut(QKeySequence::Undo);
    QAction* redo = undo_stack_->createRedoAction(this, tr("&Redo"));
    redo->setShortcut(QKeySequence::Redo);
    edit_menu->addAction(undo);
    edit_menu->addAction(redo);
    edit_menu->addSeparator();
    QAction* copy = edit_menu->addAction(tr("&Copy"), this, &MainWindow::copy_action);
    copy->setShortcut(QKeySequence::Copy);
    edit_menu->addSeparator();
    QAction* go_to = edit_menu->addAction(tr("&Idź do współrzędnych"), this, &MainWindow::go_to_position);
    go_to->setShortcut(QKeySequence(tr("Ctrl+G")));

    QMenu* view_menu = menuBar()->addMenu(tr("&View"));
    view_menu->addAction(tr("&Zoom in"), view_, &MapView::zoom_in);
    view_menu->addAction(tr("&Zoom out"), view_, &MapView::zoom_out);
    QMenu* level_menu = view_menu->addMenu(tr("&Levels"));
    map_level_group_ = new QActionGroup(this);
    for (int level = 0; level < MAP_LEVELS; ++level) {
        QAction* act = level_menu->addAction(tr("&Level %1").arg(level));
        act->setCheckable(true);
        act->setChecked(level == 0);
        act->setData(level);
        // skrot klawiszowy 0-4 jak w wersji Python
        act->setShortcut(QKeySequence(QString::number(level)));
        connect(act, &QAction::triggered, this, [this, level] { select_map_level(level); });
        map_level_group_->addAction(act);
        map_level_actions_.append(act);
    }

    QMenu* tools_menu = menuBar()->addMenu(tr("&Tools"));
    tools_group_ = new QActionGroup(this);
    QAction* select = tools_menu->addAction(tr("&Select objects"));
    select->setCheckable(true);
    select->setChecked(true);
    select->setShortcut(QKeySequence(tr("s")));
    connect(select, &QAction::triggered, this, [this] {
        scene_->clearSelection();
        scene_->set_tool(Tool::SelectObjects);
    });
    tools_group_->addAction(select);
}

void MainWindow::create_toolbar() {
    QToolBar* bar = addToolBar(tr("Pasek narzędzi"));
    QDir toolbar_icons(QDir(icons_dir_).filePath("toolbar_icons"));
    auto icon = [&](const char* name) { return QIcon(toolbar_icons.filePath(QString::fromLatin1(name))); };
    bar->addAction(icon("save_48.png"), tr("Zapisz"), this, &MainWindow::save_map);
    bar->addAction(icon("open_48.png"), tr("Otwórz"), this, &MainWindow::open_file_dialog);
    bar->addSeparator();
    QAction* undo = undo_stack_->createUndoAction(bar, tr("Undo"));
    undo->setIcon(icon("undo_48.png"));
    bar->addAction(undo);
    QAction* redo = undo_stack_->createRedoAction(bar, tr("Redo"));
    redo->setIcon(icon("redo_48.png"));
    bar->addAction(redo);
    bar->addSeparator();
    bar->addAction(icon("copy_48.png"), tr("Kopiuj"), this, &MainWindow::copy_action);
    bar->addSeparator();
    QAction* select = tools_group_->actions().value(0);
    if (select) {
        select->setIcon(icon("select_48.png"));
        bar->addAction(select);
    }
}

void MainWindow::create_shortcuts() {
    auto* zoom_out = new QShortcut(QKeySequence(QStringLiteral("-")), this);
    connect(zoom_out, &QShortcut::activated, view_, &MapView::zoom_out);
    auto* zoom_in = new QShortcut(QKeySequence(QStringLiteral("=")), this);
    connect(zoom_in, &QShortcut::activated, view_, &MapView::zoom_in);
    auto* escape = new QShortcut(QKeySequence(Qt::Key_Escape), this);
    connect(escape, &QShortcut::activated, this, &MainWindow::escape_pressed);
}

void MainWindow::update_window_title() {
    QString name = map_file_name_.isEmpty() ? QString() : QFileInfo(map_file_name_).fileName() + " - ";
    setWindowTitle(name + "pwMapEdit" + (undo_stack_->isClean() ? "" : " *"));
}

void MainWindow::show_message(const QString& text) {
    message_label_->setText(text);
}

void MainWindow::set_progress(int value, int maximum) {
    progress_bar_->setMaximum(maximum);
    progress_bar_->setValue(value);
}

void MainWindow::open_file_dialog() {
    QString file_name = QFileDialog::getOpenFileName(this, tr("File to open"), QString(),
                                                     tr("Pliki map (*.mp *.MP *.txt);;Wszystkie pliki (*)"));
    if (!file_name.isEmpty()) open_file(file_name);
}

void MainWindow::open_file(const QString& file_name) {
    if (load_watcher_) return;  // wczytywanie juz trwa
    if (!undo_stack_->isClean()) {
        auto answer = QMessageBox::question(this, tr("Otwieranie pliku"),
                                            tr("Bieżąca mapa nie jest zapisana. Czy na pewno otworzyć inny plik?"),
                                            QMessageBox::Ok | QMessageBox::Cancel);
        if (answer != QMessageBox::Ok) return;
    }
    info_text_->setText(tr("Wczytuję %1…").arg(QDir::toNativeSeparators(file_name)));
    progress_bar_->setRange(0, 0);
    QApplication::setOverrideCursor(Qt::WaitCursor);
    load_watcher_ = new QFutureWatcher<std::shared_ptr<LoadResult>>(this);
    connect(load_watcher_, &QFutureWatcherBase::finished, this, &MainWindow::file_loaded);
    load_watcher_->setFuture(QtConcurrent::run(load_map_file, file_name));
}

void MainWindow::file_loaded() {
    std::shared_ptr<LoadResult> result = load_watcher_->result();
    load_watcher_->deleteLater();
    load_watcher_ = nullptr;
    QApplication::restoreOverrideCursor();
    progress_bar_->setRange(0, 1);
    progress_bar_->reset();
    if (!result || !result->map) {
        QMessageBox::warning(this, tr("Otwieranie pliku"), result ? result->error : tr("Nieznany błąd"));
        info_text_->clear();
        emit map_loaded(false);
        return;
    }

    QElapsedTimer timer;
    timer.start();
    scene_->clear_map();
    undo_stack_->clear();
    map_ = std::move(result->map);
    map_file_name_ = result->file_name;
    Projection& projection = map_->projection();
    projection.set_map_bounding_box(map_->map_bounding_box());
    projection.calculate_data_offset();
    view_->set_projection(&projection);

    view_->setScene(nullptr);  // bez podlaczonego widoku dodawanie elementow jest szybsze
    // prostokat sceny musi byc ustawiony przed dodaniem elementow - wedlug niego budowany jest indeks BSP
    scene_->set_canvas_rectangle(map_->map_bounding_box(), projection);
    scene_->set_map(map_.get(), styles_.get());
    view_->setScene(scene_);
    view_->centerOn(scene_->sceneRect().center());
    ruler_->scale_to();
    update_window_title();

    QString msg = tr("Wczytano %1 obiektów w %2 s, rysowanie %3 s")
                      .arg(map_->records_number())
                      .arg(result->seconds, 0, 'f', 2)
                      .arg(timer.elapsed() / 1000.0, 0, 'f', 2);
    if (!map_->warnings().empty()) msg += tr(", ostrzeżeń: %1").arg(map_->warnings().size());
    show_message(msg);
    view_->update_status(false);
    emit map_loaded(true);
}

bool MainWindow::write_map(const QString& file_name) {
    if (!map_ || !map_->contains_data()) return false;
    QApplication::setOverrideCursor(Qt::WaitCursor);
    std::string content = map_->to_mp_string();
    QSaveFile file(file_name);
    bool ok = file.open(QIODevice::WriteOnly) &&
              file.write(content.data(), static_cast<qint64>(content.size())) == static_cast<qint64>(content.size()) &&
              file.commit();
    QApplication::restoreOverrideCursor();
    if (!ok) {
        QMessageBox::warning(this, tr("Zapis mapy"), tr("Nie udało się zapisać pliku: %1").arg(file.errorString()));
        return false;
    }
    undo_stack_->setClean();
    show_message(tr("Zapisano %1").arg(QDir::toNativeSeparators(file_name)));
    return true;
}

void MainWindow::save_map() {
    // jak w Pythonie: zapis tylko, gdy mapa byla zmieniona
    if (undo_stack_->isClean() || map_file_name_.isEmpty()) return;
    write_map(map_file_name_);
}

void MainWindow::save_map_as() {
    if (!map_ || !map_->contains_data()) return;
    QString file_name = QFileDialog::getSaveFileName(this, tr("Zapisz mapę jako"), map_file_name_,
                                                     tr("Pliki map (*.mp *.MP *.txt)"));
    if (file_name.isEmpty()) return;
    if (write_map(file_name)) {
        map_file_name_ = file_name;
        update_window_title();
    }
}

void MainWindow::copy_action() {
    QApplication::clipboard()->setMimeData(view_->copy());
}

void MainWindow::go_to_position() {
    bool ok = false;
    QString text = QInputDialog::getText(this, tr("Idź do współrzędnych"),
                                         tr("Format współrzędnych: 55.123456, 38.123456 (<lat, lon>)"),
                                         QLineEdit::Normal, QString(), &ok);
    if (!ok) return;
    QStringList parts = text.split(',');
    if (parts.size() != 2) return;
    bool ok_lat = false, ok_lon = false;
    double lat = parts[0].trimmed().toDouble(&ok_lat);
    double lon = parts[1].trimmed().toDouble(&ok_lon);
    if (!ok_lat || !ok_lon || lat < -90 || lat > 90 || lon < -180 || lon > 180) return;
    const Projection& projection = map_ ? map_->projection() : *default_projection_;
    PointF p = projection.geo_to_canvas(lat, lon);
    view_->centerOn(p.x, p.y);
}

void MainWindow::select_map_level(int level) {
    if (level < 0 || level >= map_level_actions_.size()) return;
    map_level_actions_[level]->setChecked(true);
    QApplication::setOverrideCursor(Qt::WaitCursor);
    scene_->set_map_level(level);
    QApplication::restoreOverrideCursor();
}

void MainWindow::escape_pressed() {
    scene_->clearSelection();
}

void MainWindow::closeEvent(QCloseEvent* event) {
    if (!undo_stack_->isClean()) {
        auto answer = QMessageBox::question(this, tr("Zamykanie aplikacji"),
                                            tr("Plik niezapisany. Czy na pewno zamknąć?"),
                                            QMessageBox::Ok | QMessageBox::Cancel);
        if (answer != QMessageBox::Ok) {
            event->ignore();
            return;
        }
    }
    event->accept();
}

}  // namespace pwm::gui
