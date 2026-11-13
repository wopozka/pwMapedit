#include "gps_dock.hpp"

#include <QDoubleSpinBox>
#include <QFileInfo>
#include <QHBoxLayout>
#include <QHeaderView>
#include <QLabel>
#include <QMenu>
#include <QPainter>
#include <QPainterPath>
#include <QPixmap>
#include <QPushButton>
#include <QTreeWidget>
#include <QVBoxLayout>
#include <map>
#include <tuple>

#include "gps_layers.hpp"
#include "map_scene.hpp"
#include "map_view.hpp"

namespace pwm::gui {

namespace {
constexpr int KindRole = Qt::UserRole;
constexpr int FileRole = Qt::UserRole + 1;
constexpr int TrackRole = Qt::UserRole + 2;
constexpr int IndexRole = Qt::UserRole + 3;  // czesc sladu albo waypoint

QIcon color_icon(const QColor& color) {
    QPixmap pix(12, 12);
    pix.fill(color);
    return QIcon(pix);
}
}  // namespace

GpsDock::GpsDock(GpsLayers* layers, MapScene* scene, MapView* view, QWidget* parent)
    : QDockWidget(parent), layers_(layers), scene_(scene), view_(view) {
    setWindowTitle(tr("Ślady GPS"));
    setObjectName("gps_dock");
    auto* page = new QWidget(this);
    auto* box = new QVBoxLayout(page);

    auto* buttons = new QHBoxLayout;
    auto* load = new QPushButton(tr("Wczytaj…"), page);
    connect(load, &QPushButton::clicked, this, &GpsDock::load_requested);
    buttons->addWidget(load);
    auto* create = new QPushButton(tr("Utwórz obiekty"), page);
    create->setToolTip(tr("Zaznaczony ślad lub jego część - polilinia, waypointy - POI"));
    connect(create, &QPushButton::clicked, this, &GpsDock::create_from_selection);
    buttons->addWidget(create);
    auto* remove = new QPushButton(tr("Usuń"), page);
    remove->setToolTip(tr("Usuń zaznaczony plik z widoku (mapa się nie zmienia)"));
    connect(remove, &QPushButton::clicked, this, &GpsDock::remove_selected_file);
    buttons->addWidget(remove);
    box->addLayout(buttons);

    auto* tol_box = new QHBoxLayout;
    tol_box->addWidget(new QLabel(tr("Uproszczenie śladu:"), page));
    tolerance_ = new QDoubleSpinBox(page);
    tolerance_->setRange(0, 100);
    tolerance_->setDecimals(1);
    tolerance_->setSingleStep(0.5);
    tolerance_->setValue(3.0);
    tolerance_->setSuffix(" m");
    tolerance_->setToolTip(tr("Punkty śladu odchylone od tworzonej linii o mniej niż tyle metrów są pomijane"));
    tol_box->addWidget(tolerance_);
    tol_box->addStretch();
    box->addLayout(tol_box);

    tree_ = new QTreeWidget(page);
    tree_->setColumnCount(2);
    tree_->setHeaderLabels({tr("Nazwa"), tr("Punkty")});
    tree_->header()->setStretchLastSection(false);
    tree_->header()->setSectionResizeMode(0, QHeaderView::Stretch);
    tree_->setSelectionMode(QAbstractItemView::ExtendedSelection);
    tree_->setContextMenuPolicy(Qt::CustomContextMenu);
    connect(tree_, &QTreeWidget::itemSelectionChanged, this, &GpsDock::selection_changed);
    connect(tree_, &QTreeWidget::itemChanged, this, &GpsDock::item_changed);
    connect(tree_, &QTreeWidget::itemDoubleClicked, this, [this](QTreeWidgetItem* item) { center_on(item); });
    connect(tree_, &QTreeWidget::customContextMenuRequested, this, &GpsDock::show_context_menu);
    box->addWidget(tree_);
    setWidget(page);

    connect(layers_, &GpsLayers::files_changed, this, &GpsDock::rebuild);
    rebuild();
}

void GpsDock::rebuild() {
    rebuilding_ = true;
    tree_->clear();
    for (int f = 0; f < layers_->file_count(); ++f) {
        const GpsFileEntry& e = layers_->file(f);
        auto* file_item = new QTreeWidgetItem(tree_);
        file_item->setText(0, QFileInfo(QString::fromStdString(e.data.path)).fileName());
        file_item->setToolTip(0, QString::fromStdString(e.data.path));
        file_item->setText(1, QString::number(e.data.point_count()));
        file_item->setIcon(0, color_icon(e.color));
        file_item->setFlags(file_item->flags() | Qt::ItemIsUserCheckable);
        file_item->setCheckState(0, e.visible ? Qt::Checked : Qt::Unchecked);
        file_item->setData(0, KindRole, FileItem);
        file_item->setData(0, FileRole, f);
        for (int t = 0; t < static_cast<int>(e.data.tracks.size()); ++t) {
            const gps::Track& track = e.data.tracks[static_cast<size_t>(t)];
            auto* track_item = new QTreeWidgetItem(file_item);
            const QString name = QString::fromStdString(track.name);
            track_item->setText(0, (track.route ? tr("Trasa: ") : tr("Ślad: ")) + (name.isEmpty() ? tr("(bez nazwy)") : name));
            size_t points = 0;
            for (const auto& seg : track.segments) points += seg.size();
            track_item->setText(1, QString::number(points));
            track_item->setData(0, KindRole, TrackItem);
            track_item->setData(0, FileRole, f);
            track_item->setData(0, TrackRole, t);
            bool all_used = true;
            for (int s = 0; s < static_cast<int>(track.segments.size()); ++s) {
                const bool used = e.used_segments[static_cast<size_t>(t)][static_cast<size_t>(s)];
                all_used = all_used && used;
                if (track.segments.size() < 2) continue;
                auto* seg_item = new QTreeWidgetItem(track_item);
                seg_item->setText(0, tr("część %1").arg(s + 1) + (used ? tr(" (użyta)") : QString()));
                seg_item->setText(1, QString::number(track.segments[static_cast<size_t>(s)].size()));
                seg_item->setData(0, KindRole, SegmentItem);
                seg_item->setData(0, FileRole, f);
                seg_item->setData(0, TrackRole, t);
                seg_item->setData(0, IndexRole, s);
                if (used) seg_item->setForeground(0, QBrush(Qt::gray));
            }
            if (all_used) {
                track_item->setForeground(0, QBrush(Qt::gray));
                track_item->setText(0, track_item->text(0) + tr(" (użyty)"));
            }
        }
        if (!e.data.waypoints.empty()) {
            auto* wpts = new QTreeWidgetItem(file_item);
            wpts->setText(0, tr("Waypointy"));
            wpts->setText(1, QString::number(e.data.waypoints.size()));
            wpts->setData(0, KindRole, WaypointsItem);
            wpts->setData(0, FileRole, f);
            for (int w = 0; w < static_cast<int>(e.data.waypoints.size()); ++w) {
                const gps::Waypoint& wpt = e.data.waypoints[static_cast<size_t>(w)];
                auto* item = new QTreeWidgetItem(wpts);
                const QString name = QString::fromStdString(wpt.name);
                const bool used = e.used_waypoints[static_cast<size_t>(w)];
                item->setText(0, (name.isEmpty() ? tr("(bez nazwy)") : name) + (used ? tr(" (użyty)") : QString()));
                if (!wpt.comment.empty()) item->setToolTip(0, QString::fromStdString(wpt.comment));
                item->setData(0, KindRole, WaypointItem);
                item->setData(0, FileRole, f);
                item->setData(0, IndexRole, w);
                if (used) item->setForeground(0, QBrush(Qt::gray));
            }
        }
        file_item->setExpanded(true);
    }
    rebuilding_ = false;
}

void GpsDock::item_changed(QTreeWidgetItem* item, int column) {
    if (rebuilding_ || column != 0 || item->data(0, KindRole).toInt() != FileItem) return;
    layers_->set_visible(item->data(0, FileRole).toInt(), item->checkState(0) == Qt::Checked);
}

QPainterPath GpsDock::item_path(QTreeWidgetItem* item, bool* polygon) const {
    *polygon = false;
    const int f = item->data(0, FileRole).toInt();
    switch (item->data(0, KindRole).toInt()) {
        case TrackItem:
            return layers_->segment_path(f, item->data(0, TrackRole).toInt(), -1);
        case SegmentItem:
            return layers_->segment_path(f, item->data(0, TrackRole).toInt(), item->data(0, IndexRole).toInt());
        case WaypointItem: {
            QPainterPath path;
            if (auto pos = layers_->waypoint_position(f, item->data(0, IndexRole).toInt())) {
                path.addEllipse(*pos, 10, 10);
                *polygon = true;
            }
            return path;
        }
        default:
            return {};
    }
}

void GpsDock::selection_changed() {
    const QList<QTreeWidgetItem*> selected = tree_->selectedItems();
    bool polygon = false;
    QPainterPath path = selected.size() == 1 ? item_path(selected.front(), &polygon) : QPainterPath();
    scene_->highlight_path(path, polygon);
}

void GpsDock::center_on(QTreeWidgetItem* item) {
    bool polygon = false;
    const QPainterPath path = item_path(item, &polygon);
    if (!path.isEmpty()) view_->centerOn(path.boundingRect().center());
}

void GpsDock::create_from_selection() {
    const QList<QTreeWidgetItem*> selected = tree_->selectedItems();
    // waypointy z tego samego pliku - jedna komenda; slady - kazdy osobno
    std::map<int, std::vector<int>> waypoints;
    std::vector<QTreeWidgetItem*> tracks;
    for (QTreeWidgetItem* item : selected) {
        const int f = item->data(0, FileRole).toInt();
        switch (item->data(0, KindRole).toInt()) {
            case WaypointItem:
                waypoints[f].push_back(item->data(0, IndexRole).toInt());
                break;
            case WaypointsItem:
                for (int w = 0; w < item->childCount(); ++w) waypoints[f].push_back(w);
                break;
            case TrackItem:
            case SegmentItem:
                tracks.push_back(item);
                break;
            default:
                break;
        }
    }
    // pozycje listy zostana przebudowane po pierwszym utworzeniu - najpierw zbieramy dane
    std::vector<std::tuple<int, int, int>> track_refs;
    for (QTreeWidgetItem* item : tracks)
        track_refs.emplace_back(item->data(0, FileRole).toInt(), item->data(0, TrackRole).toInt(),
                                item->data(0, KindRole).toInt() == SegmentItem ? item->data(0, IndexRole).toInt() : -1);
    for (const auto& [f, t, s] : track_refs) layers_->create_polylines(f, t, s, tolerance_->value());
    for (const auto& [f, wpts] : waypoints) layers_->create_pois(f, wpts);
}

void GpsDock::remove_selected_file() {
    const QList<QTreeWidgetItem*> selected = tree_->selectedItems();
    if (selected.isEmpty()) return;
    QTreeWidgetItem* item = selected.front();
    while (item->parent()) item = item->parent();
    scene_->highlight_path(QPainterPath(), false);
    layers_->remove_file(item->data(0, FileRole).toInt());
}

void GpsDock::show_context_menu(const QPoint& pos) {
    QTreeWidgetItem* item = tree_->itemAt(pos);
    if (!item) return;
    if (!item->isSelected()) {
        tree_->clearSelection();
        item->setSelected(true);
    }
    QMenu menu;
    const int kind = item->data(0, KindRole).toInt();
    if (kind == TrackItem || kind == SegmentItem)
        menu.addAction(tr("Utwórz polilinię"), this, &GpsDock::create_from_selection);
    if (kind == WaypointItem || kind == WaypointsItem)
        menu.addAction(kind == WaypointItem ? tr("Utwórz POI") : tr("Utwórz POI ze wszystkich"), this,
                       &GpsDock::create_from_selection);
    if (kind != FileItem && kind != WaypointsItem)
        menu.addAction(tr("Pokaż na mapie"), this, [this, item] { center_on(item); });
    if (kind == FileItem) menu.addAction(tr("Usuń z widoku"), this, &GpsDock::remove_selected_file);
    if (!menu.isEmpty()) menu.exec(tree_->viewport()->mapToGlobal(pos));
}

}  // namespace pwm::gui
