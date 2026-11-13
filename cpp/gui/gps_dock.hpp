// Panel "Slady GPS": lista wczytanych plikow (widocznosc, kolor), ich slady i waypointy; zamiana na obiekty mapy.
#pragma once

#include <QDockWidget>

class QDoubleSpinBox;
class QTreeWidget;
class QTreeWidgetItem;

namespace pwm::gui {

class GpsLayers;
class MapScene;
class MapView;

class GpsDock : public QDockWidget {
    Q_OBJECT
public:
    GpsDock(GpsLayers* layers, MapScene* scene, MapView* view, QWidget* parent = nullptr);

    // rodzaj pozycji na liscie (Qt::UserRole)
    enum ItemKind { FileItem = 1, TrackItem, SegmentItem, WaypointsItem, WaypointItem };
    QTreeWidget* tree() const { return tree_; }
    QDoubleSpinBox* tolerance() const { return tolerance_; }

    // Akcje dla zaznaczonej pozycji (menu kontekstowe, przyciski) - dostepne dla testow.
    void create_from_selection();
    void remove_selected_file();

signals:
    // prosba o okno wyboru plikow (okno glowne)
    void load_requested();

private:
    void rebuild();
    void selection_changed();
    void item_changed(QTreeWidgetItem* item, int column);
    void show_context_menu(const QPoint& pos);
    void center_on(QTreeWidgetItem* item);
    QPainterPath item_path(QTreeWidgetItem* item, bool* polygon) const;

    GpsLayers* layers_;
    MapScene* scene_;
    MapView* view_;
    QTreeWidget* tree_ = nullptr;
    QDoubleSpinBox* tolerance_ = nullptr;
    bool rebuilding_ = false;
};

}  // namespace pwm::gui
