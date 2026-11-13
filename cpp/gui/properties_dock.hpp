// Port map_obj_properties_dockwidget.py: panel wlasciwosci zaznaczonego obiektu.
//
// Karty: Główny (typ, etykiety, EndLevel, kierunek, komentarz, Extras), Adres (POI), Elements (czesci obiektu
// na poziomach Data), Routing (polilinie), Węzły (numeracja adresowa i HLevel wezla - w trybie edycji wezlow,
// po kliknieciu uchwytu).
//
// Panel nie trzyma kopii danych: pola wypelnia z obiektu w MapData, a kazda zmiana to kopia obiektu ze zmienionym
// polem przekazana do MapScene::replace_object (jedna komenda undo). Po kazdej zmianie stosu undo panel
// wypelnia sie od nowa, wiec po cofnieciu pokazuje przywrocone wartosci.
#pragma once

#include <QDockWidget>
#include <functional>
#include <optional>

#include "map_scene.hpp"

class QCheckBox;
class QMimeData;
class QComboBox;
class QGroupBox;
class QLineEdit;
class QPlainTextEdit;
class QPushButton;
class QTabWidget;
class QTableWidget;
class QTreeWidget;

namespace pwm::gui {

class PropertiesDock : public QDockWidget {
    Q_OBJECT
public:
    explicit PropertiesDock(MapScene* scene, QWidget* parent = nullptr);

    // Ustala, co pokazac (zaznaczony obiekt albo wezel aktywnego uchwytu), i wypelnia pola.
    void refresh();

    enum Tab { MainTab, AddressTab, ElementsTab, RoutingTab, NodesTab };
    QTabWidget* tabs() const { return tabs_; }
    std::optional<size_t> shown_object() const { return obj_; }
    bool shows_node() const { return grip_.has_value(); }

    // ---- schowek tabeli Extras (jak ExtrasTable.copy/paste w Pythonie) ----
    // Zaznaczone komorki: application/json (lista par [klucz, wartosc]) i tekst "klucz<TAB>wartosc".
    QMimeData* copy_extras() const;
    // Wkleja pary od biezacego wiersza w dol (dopisuje wiersze) i zapisuje zmiane jedna komenda.
    void paste_extras(const QMimeData* mime);
    void clear_selected_extras();

    // ---- karta Elements: czesci obiektu i poziomy Data ----
    // Usuniecie czesci (polygon: zewnetrzna razem z jej dziurami); ostatnia czesc poziomu usuwa poziom,
    // ostatnia czesc obiektu - obiekt.
    void delete_element(int level, const std::vector<size_t>& polys);
    // Czesci jako nowy obiekt o tych samych wlasciwosciach (nie dla jedynego elementu poziomu).
    void extract_element(int level, const std::vector<size_t>& polys);
    // Przeniesienie/kopia calego poziomu na wolny poziom; EndLevel podnoszony, gdy jest za niski.
    void move_level(int from_level, int to_level, bool copy);

    // Pola dostepne dla testow.
    QComboBox* type_selector() const { return type_; }
    QLineEdit* label_edit(int num) const { return labels_[num - 1]; }
    QComboBox* end_level() const { return end_level_; }
    QCheckBox* dir_indicator() const { return dir_indicator_; }
    QPlainTextEdit* comment() const { return comment_; }
    QTableWidget* extras() const { return extras_; }
    QLineEdit* street_desc() const { return street_desc_; }
    QLineEdit* house_number() const { return house_number_; }
    QLineEdit* phone() const { return phone_; }
    QTreeWidget* elements() const { return elements_; }
    QComboBox* route_combo(int index) const { return route_combos_[index]; }
    QCheckBox* route_check(int index) const { return route_checks_[index]; }
    QCheckBox* node_has_numbers() const { return node_has_numbers_; }
    QComboBox* numbering_style(bool left) const { return left ? left_.style : right_.style; }
    QLineEdit* number_after(bool left) const { return left ? left_.after : right_.after; }
    QLineEdit* number_before(bool left) const { return left ? left_.before : right_.before; }
    QComboBox* node_hlevel() const { return hlevel_; }

signals:
    // komunikat dla paska stanu okna
    void message(const QString& text);

protected:
    bool eventFilter(QObject* watched, QEvent* event) override;

private:
    struct NumberingSide {
        QGroupBox* box = nullptr;
        QComboBox* style = nullptr;
        QLineEdit* after = nullptr;   // "Zacznij od" (*_number_after)
        QLineEdit* before = nullptr;  // "Skończ na" (*_number_before)
        QLineEdit* zip = nullptr;
        QLineEdit* city = nullptr;
        QLineEdit* region = nullptr;
        QLineEdit* country = nullptr;
    };

    QWidget* build_main_tab();
    QWidget* build_address_tab();
    QWidget* build_elements_tab();
    QWidget* build_routing_tab();
    QWidget* build_nodes_tab();
    NumberingSide build_numbering_side(const QString& title);

    const MapObject* object() const;
    void fill_object();
    void fill_type();
    void fill_elements();
    void fill_routing();
    void fill_node();
    void set_numbering_fields_enabled(bool enabled);

    // Kopia obiektu -> change -> komenda (gdy zapis obiektu do mp sie zmienil).
    void commit(const QString& text, const std::function<void(MapObject&)>& change);
    void commit_node(const QString& text, const std::function<void(DataX&, const GripRef&)>& change);

    void type_chosen(int index);
    void comment_edited();
    void extras_edited();
    void route_params_edited();
    void numbering_edited();
    void node_numbers_toggled(bool on);
    void element_selected();
    void elements_context_menu(const QPoint& pos);

    MapScene* scene_;
    std::optional<size_t> obj_;
    std::optional<GripRef> grip_;
    std::optional<size_t> last_obj_;  // obiekt pokazany poprzednio (czy zostawic biezaca karte)
    int type_list_kind_ = -1;  // ObjectKind, dla ktorego zbudowano liste typow
    bool filling_ = false;
    QString comment_at_focus_;

    QTabWidget* tabs_ = nullptr;
    QComboBox* type_ = nullptr;
    QLineEdit* labels_[3] = {};
    QComboBox* end_level_ = nullptr;
    QCheckBox* dir_indicator_ = nullptr;
    QPushButton* reverse_ = nullptr;
    QPlainTextEdit* comment_ = nullptr;
    QTableWidget* extras_ = nullptr;
    QLineEdit* street_desc_ = nullptr;
    QLineEdit* house_number_ = nullptr;
    QLineEdit* phone_ = nullptr;
    QTreeWidget* elements_ = nullptr;
    QComboBox* route_combos_[2] = {};
    QCheckBox* route_checks_[12] = {};  // indeksy 2-11
    QCheckBox* node_has_numbers_ = nullptr;
    NumberingSide left_, right_;
    QComboBox* hlevel_ = nullptr;
};

}  // namespace pwm::gui
