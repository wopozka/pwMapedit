#include "properties_dock.hpp"

#include <QCheckBox>
#include <QComboBox>
#include <QCompleter>
#include <QEvent>
#include <QFormLayout>
#include <QGroupBox>
#include <QHBoxLayout>
#include <QHeaderView>
#include <QIntValidator>
#include <QJsonArray>
#include <QJsonDocument>
#include <QLabel>
#include <QLineEdit>
#include <QMenu>
#include <QMimeData>
#include <QApplication>
#include <QClipboard>
#include <QPlainTextEdit>
#include <QPushButton>
#include <QTabWidget>
#include <QTableWidget>
#include <QTreeWidget>
#include <QVBoxLayout>

#include "map_items.hpp"
#include "map_styles.hpp"
#include "misc.hpp"
#include "type_names.hpp"

namespace pwm::gui {

namespace {

QString to_ui(const std::string& cp1250) { return QString::fromStdString(encoding::cp1250_to_utf8(cp1250)); }
QString to_ui(const std::optional<std::string>& cp1250) { return cp1250 ? to_ui(*cp1250) : QString(); }

// Tekst z pola -> wartosc w obiekcie (cp1250); puste pole to brak wartosci.
std::optional<std::string> from_ui(const QString& text) {
    const QString t = text.trimmed();
    if (t.isEmpty()) return std::nullopt;
    return encoding::utf8_to_cp1250(t.toStdString());
}

std::optional<long long> number_from_ui(const QString& text) {
    bool ok = false;
    const long long v = text.trimmed().toLongLong(&ok);
    return ok ? std::optional<long long>(v) : std::nullopt;
}

// styl numeracji <-> pozycja na liscie (jak w Pythonie: N i brak to "None")
int style_index(const std::optional<std::string>& style) {
    if (!style) return 0;
    if (*style == "E") return 1;
    if (*style == "O") return 2;
    if (*style == "B") return 3;
    return 0;
}

std::optional<std::string> style_from_index(int index) {
    switch (index) {
        case 1: return std::string("E");
        case 2: return std::string("O");
        case 3: return std::string("B");
        default: return std::nullopt;
    }
}

QString geo_text(const Projection* projection, const Node& node) {
    if (!projection) return {};
    try {
        GeoPoint g = projection->canvas_to_geo(node.x(), node.y());
        return QString::asprintf("%.6f, %.6f", g.latitude, g.longitude);
    } catch (const std::exception&) {
        return {};
    }
}

QPainterPath poly_path(const Poly& poly, bool polygon) {
    QPolygonF pp;
    for (const Node& n : poly) pp.append(QPointF(n.x(), n.y()));
    if (polygon && !pp.isEmpty() && pp.first() != pp.last()) pp.append(pp.first());
    QPainterPath path;
    path.addPolygon(pp);
    return path;
}

constexpr int ROUTE_PARAMS = 12;
const char* const ROUTE_CHECK_NAMES[ROUTE_PARAMS] = {
    nullptr, nullptr, "One way", "Route is toll", "No emergency", "No delivery", "No car/motorcycle",
    "No bus", "No taxi", "No pedestrian", "No bicycle", "No truck"};

}  // namespace

PropertiesDock::PropertiesDock(MapScene* scene, QWidget* parent) : QDockWidget(parent), scene_(scene) {
    setWindowTitle(tr("Właściwości"));
    setObjectName("properties_dock");
    tabs_ = new QTabWidget(this);
    tabs_->addTab(build_main_tab(), tr("Główny"));
    tabs_->addTab(build_address_tab(), tr("Adres"));
    tabs_->addTab(build_elements_tab(), tr("Elements"));
    tabs_->addTab(build_routing_tab(), tr("Routing"));
    tabs_->addTab(build_nodes_tab(), tr("Węzły"));
    setWidget(tabs_);
    refresh();
}

// ---------------------------------------------------------------- budowa kart
QWidget* PropertiesDock::build_main_tab() {
    auto* page = new QWidget;
    auto* box = new QVBoxLayout(page);
    auto* form = new QFormLayout;

    type_ = new QComboBox(page);
    type_->setEditable(true);
    type_->setInsertPolicy(QComboBox::NoInsert);
    type_->setFocusPolicy(Qt::StrongFocus);
    // jak TypeComboBox w Pythonie: wpisany tekst filtruje liste (dowolny fragment, bez wielkosci liter)
    type_->completer()->setFilterMode(Qt::MatchContains);
    type_->completer()->setCaseSensitivity(Qt::CaseInsensitive);
    type_->completer()->setCompletionMode(QCompleter::PopupCompletion);
    connect(type_, &QComboBox::activated, this, &PropertiesDock::type_chosen);
    form->addRow(tr("Type"), type_);

    const char* label_names[3] = {"Label", "Label2", "Label3"};
    for (int i = 0; i < 3; ++i) {
        labels_[i] = new QLineEdit(page);
        connect(labels_[i], &QLineEdit::editingFinished, this, [this, i] {
            const QString text = labels_[i]->text();
            commit(tr("Zmień label%1").arg(i + 1), [&](MapObject& o) {
                std::optional<std::string>* fields[3] = {&o.label1, &o.label2, &o.label3};
                *fields[i] = from_ui(text);
            });
        });
        form->addRow(label_names[i], labels_[i]);
    }

    end_level_ = new QComboBox(page);
    for (int i = 0; i < 6; ++i) end_level_->addItem(QString::number(i));
    connect(end_level_, &QComboBox::activated, this, [this](int index) {
        commit(tr("Zmiana endlevel"), [index](MapObject& o) { o.endlevel = index; });
    });
    form->addRow(tr("EndLevel"), end_level_);
    box->addLayout(form);

    auto* dir_box = new QHBoxLayout;
    dir_box->addWidget(new QLabel(tr("Polyline has direction"), page));
    dir_indicator_ = new QCheckBox(page);
    connect(dir_indicator_, &QCheckBox::clicked, this, [this](bool on) {
        commit(on ? tr("Dodaj jednokierunkowość") : tr("Usuń jednokierunkowość"),
               [on](MapObject& o) { o.dirindicator = on; });
    });
    dir_box->addWidget(dir_indicator_);
    reverse_ = new QPushButton(tr("Revert direction"), page);
    connect(reverse_, &QPushButton::clicked, scene_, &MapScene::reverse_selected_polylines);
    dir_box->addWidget(reverse_);
    dir_box->addStretch();
    box->addLayout(dir_box);

    box->addWidget(new QLabel(tr("Comment (mapper's private note stored in MP file only)"), page));
    comment_ = new QPlainTextEdit(page);
    comment_->installEventFilter(this);  // zapis po opuszczeniu pola, jak CommentTextEdit
    box->addWidget(comment_);

    box->addWidget(new QLabel(tr("Extras"), page));
    extras_ = new QTableWidget(0, 2, page);
    extras_->setHorizontalHeaderLabels({tr("Klucz"), tr("Wartość")});
    extras_->horizontalHeader()->setStretchLastSection(true);
    extras_->setContextMenuPolicy(Qt::CustomContextMenu);
    connect(extras_, &QTableWidget::cellChanged, this, [this] { extras_edited(); });
    connect(extras_, &QTableWidget::customContextMenuRequested, this, [this](const QPoint& pos) {
        QMenu menu;
        const int row = std::max(extras_->currentRow(), 0);
        menu.addAction(tr("Kopiuj"), [this] {
            if (QMimeData* mime = copy_extras()) QApplication::clipboard()->setMimeData(mime);
        });
        menu.addAction(tr("Wklej"), [this] { paste_extras(QApplication::clipboard()->mimeData()); });
        menu.addSeparator();
        menu.addAction(tr("Dodaj wiersz powyżej"), [this, row] { extras_->insertRow(row); });
        menu.addAction(tr("Dodaj wiersz poniżej"), [this, row] { extras_->insertRow(row + 1); });
        menu.addAction(tr("Usuń wiersz"), [this] {
            if (extras_->currentRow() < 0) return;
            extras_->removeRow(extras_->currentRow());
            extras_edited();
        });
        menu.exec(extras_->viewport()->mapToGlobal(pos));
    });
    box->addWidget(extras_);
    return page;
}

QWidget* PropertiesDock::build_address_tab() {
    auto* page = new QWidget;
    auto* form = new QFormLayout(page);
    auto add = [&](QLineEdit*& edit, const QString& name, const QString& undo_text,
                   std::optional<std::string> MapObject::*field) {
        edit = new QLineEdit(page);
        QLineEdit* e = edit;
        connect(e, &QLineEdit::editingFinished, this, [this, e, undo_text, field] {
            const QString text = e->text();
            commit(undo_text, [&](MapObject& o) { o.*field = from_ui(text); });
        });
        form->addRow(name, e);
    };
    add(street_desc_, tr("Street name"), tr("zmiana StreetDesc"), &MapObject::streetdesc);
    add(house_number_, tr("House number"), tr("zmiana HouseNumber"), &MapObject::housenumber);
    add(phone_, tr("Phone number"), tr("zmiana PhoneNumber"), &MapObject::phone);
    return page;
}

QWidget* PropertiesDock::build_elements_tab() {
    auto* page = new QWidget;
    auto* box = new QVBoxLayout(page);
    elements_ = new QTreeWidget(page);
    elements_->setColumnCount(4);
    elements_->setHeaderLabels({tr("Nr Data/Nr poly"), tr("Inner/Outer"), tr("Lat/Lon 1 punkt"), tr("Węzły")});
    connect(elements_, &QTreeWidget::itemSelectionChanged, this, &PropertiesDock::element_selected);
    box->addWidget(elements_);
    return page;
}

QWidget* PropertiesDock::build_routing_tab() {
    auto* page = new QWidget;
    auto* form = new QFormLayout(page);
    route_combos_[0] = new QComboBox(page);
    route_combos_[0]->addItems({"(0) 3mph/5kmh", "(1) 15mph/20kmh", "(2) 25mph/40kmh", "(3) 35mph/60kmh",
                                "(4) 50mph/80kmh", "(5) 60mph/90kmh", "(6) 70mph/110kmh", "(7) no limit"});
    form->addRow(tr("Speed limit"), route_combos_[0]);
    route_combos_[1] = new QComboBox(page);
    route_combos_[1]->addItems({"(0) residential/alley/unpaved/trail", "(1) roundabout/collector",
                                "(2) arterial/other HW", "(3) principal HW", "(4) major HW/ramp"});
    form->addRow(tr("Route class"), route_combos_[1]);
    for (QComboBox* combo : route_combos_)
        connect(combo, &QComboBox::activated, this, [this] { route_params_edited(); });
    for (int i = 2; i < ROUTE_PARAMS; ++i) {
        route_checks_[i] = new QCheckBox(page);
        connect(route_checks_[i], &QCheckBox::clicked, this, [this] { route_params_edited(); });
        form->addRow(tr(ROUTE_CHECK_NAMES[i]), route_checks_[i]);
    }
    return page;
}

PropertiesDock::NumberingSide PropertiesDock::build_numbering_side(const QString& title) {
    NumberingSide side;
    side.box = new QGroupBox(title);
    auto* form = new QFormLayout(side.box);
    side.style = new QComboBox(side.box);
    side.style->addItems({tr("None"), tr("Parzysty (2, 4, 6, 8)"), tr("Nieparzysty (1, 3, 5, 7)"),
                          tr("Ciągły (1, 2, 3, 4)")});
    connect(side.style, &QComboBox::activated, this, [this] { numbering_edited(); });
    form->addRow(tr("Styl numeracji"), side.style);
    auto line = [&](QLineEdit*& edit, const QString& name, bool number) {
        edit = new QLineEdit(side.box);
        if (number) edit->setValidator(new QIntValidator(0, 999999999, edit));
        connect(edit, &QLineEdit::editingFinished, this, [this] { numbering_edited(); });
        form->addRow(name, edit);
    };
    line(side.after, tr("Zacznij od"), true);
    line(side.before, tr("Skończ na"), true);
    line(side.zip, tr("Kod poczt."), false);
    line(side.city, tr("Miasto"), false);
    line(side.region, tr("Region"), false);
    line(side.country, tr("Państwo"), false);
    return side;
}

QWidget* PropertiesDock::build_nodes_tab() {
    auto* page = new QWidget;
    auto* box = new QVBoxLayout(page);
    auto* form = new QFormLayout;
    node_has_numbers_ = new QCheckBox(page);
    connect(node_has_numbers_, &QCheckBox::clicked, this, &PropertiesDock::node_numbers_toggled);
    form->addRow(tr("Węzeł ma numerację"), node_has_numbers_);
    box->addLayout(form);
    left_ = build_numbering_side(tr("Lewa strona numeracji po węźle"));
    right_ = build_numbering_side(tr("Prawa strona numeracji po węźle"));
    box->addWidget(left_.box);
    box->addWidget(right_.box);

    auto* hlevel_box = new QGroupBox(tr("Hlevel na węźle"), page);
    auto* hlevel_form = new QFormLayout(hlevel_box);
    hlevel_ = new QComboBox(hlevel_box);
    hlevel_->addItem(tr("Brak"));
    for (int v = -2; v < 16; ++v) hlevel_->addItem(QString::number(v), v);
    connect(hlevel_, &QComboBox::activated, this, [this](int index) {
        const OptInt value = index > 0 ? OptInt(hlevel_->itemData(index).toLongLong()) : std::nullopt;
        commit_node(tr("Zmiana HLevel"), [value](DataX& data, const GripRef& g) {
            data.set_hlevel_to_node(g.level, g.poly, static_cast<long>(g.node), value);
        });
    });
    hlevel_form->addRow(tr("Hlevel dla węzła"), hlevel_);
    box->addWidget(hlevel_box);
    box->addStretch();
    return page;
}

// ---------------------------------------------------------------- wypelnianie
const MapObject* PropertiesDock::object() const {
    MapData* map = scene_->map();
    if (!map || !obj_ || *obj_ >= map->objects().size()) return nullptr;
    return &map->objects()[*obj_];
}

void PropertiesDock::refresh() {
    obj_.reset();
    grip_.reset();
    const std::vector<MapObjectItem*> selected = scene_->selected_object_items();
    if (selected.size() == 1) obj_ = selected.front()->object_index();
    const MapObject* o = object();
    if (!o || o->deleted || !o->data) {
        obj_.reset();
        for (int i = 0; i < tabs_->count(); ++i) tabs_->setTabEnabled(i, false);
        tabs_->setCurrentIndex(MainTab);  // po wylaczeniu kart Qt przestawia biezaca na ostatnia
        scene_->highlight_path(QPainterPath(), false);
        last_obj_.reset();
        return;
    }
    const auto& g = scene_->active_grip();
    if (scene_->tool() == Tool::EditNodes && g && g->obj == *obj_) grip_ = *g;

    filling_ = true;
    if (grip_) {
        // jak set_dock_mode_edit_nodes: tylko karta wezlow
        for (int i = 0; i < tabs_->count(); ++i) tabs_->setTabEnabled(i, i == NodesTab);
        tabs_->setCurrentIndex(NodesTab);
        fill_node();
    } else {
        const ObjectKind kind = o->kind();
        tabs_->setTabEnabled(MainTab, true);
        tabs_->setTabEnabled(AddressTab, kind == ObjectKind::Poi);
        tabs_->setTabEnabled(ElementsTab, true);
        tabs_->setTabEnabled(RoutingTab, kind == ObjectKind::Polyline);
        tabs_->setTabEnabled(NodesTab, false);
        // nowy obiekt: karta Główny; ten sam (panel wypelnia sie od nowa po kazdej zmianie) - karta zostaje
        if (last_obj_ != obj_ || !tabs_->isTabEnabled(tabs_->currentIndex())) tabs_->setCurrentIndex(MainTab);
        fill_object();
    }
    filling_ = false;
    last_obj_ = obj_;
}

void PropertiesDock::fill_object() {
    const MapObject& o = *object();
    fill_type();
    const std::optional<std::string>* label_values[3] = {&o.label1, &o.label2, &o.label3};
    for (int i = 0; i < 3; ++i) labels_[i]->setText(to_ui(*label_values[i]));
    {
        QSignalBlocker block(end_level_);
        while (end_level_->count() <= o.endlevel) end_level_->addItem(QString::number(end_level_->count()));
        end_level_->setCurrentIndex(static_cast<int>(std::max(0LL, o.endlevel)));
    }
    const bool polyline = o.kind() == ObjectKind::Polyline;
    dir_indicator_->setEnabled(polyline);
    reverse_->setEnabled(polyline);
    dir_indicator_->setChecked(polyline && o.dirindicator);

    QStringList comment_lines;
    if (o.comment)
        for (const auto& line : *o.comment) comment_lines << to_ui(line);
    comment_->setPlainText(comment_lines.join('\n'));
    comment_at_focus_ = comment_->toPlainText();

    {
        QSignalBlocker block(extras_);
        extras_->clearContents();
        extras_->setRowCount(static_cast<int>(o.others.size()) + 1);  // pusty wiersz na nowy wpis
        for (size_t row = 0; row < o.others.size(); ++row) {
            extras_->setItem(static_cast<int>(row), 0, new QTableWidgetItem(to_ui(o.others[row].first)));
            extras_->setItem(static_cast<int>(row), 1, new QTableWidgetItem(to_ui(o.others[row].second)));
        }
    }

    street_desc_->setText(to_ui(o.streetdesc));
    house_number_->setText(to_ui(o.housenumber));
    phone_->setText(to_ui(o.phone));
    fill_elements();
    fill_routing();
}

void PropertiesDock::fill_type() {
    const MapObject& o = *object();
    QSignalBlocker block(type_);
    const int kind = static_cast<int>(o.kind());
    if (kind != type_list_kind_) {
        type_->clear();
        if (o.kind() == ObjectKind::Poi) {
            const MapStyles* styles = scene_->styles();
            for (const PoiTypeName& t : poi_type_names()) {
                QString text = QString("0x%1 (%2), %3, %4")
                                   .arg(t.type, 0, 16)
                                   .arg(QString::fromUtf8(t.category), QString::fromUtf8(t.name),
                                        QString::fromUtf8(t.aliases));
                if (styles)
                    type_->addItem(QIcon(styles->poi_icon(t.type)), text, t.type);
                else
                    type_->addItem(text, t.type);
            }
        } else {
            const auto& names = o.kind() == ObjectKind::Polyline ? line_type_names() : polygon_type_names();
            for (const PolyTypeName& t : names) {
                QString text = QString("0x%1 (%2), %3").arg(t.type, 0, 16).arg(QString::fromUtf8(t.category),
                                                                                QString::fromUtf8(t.name_en));
                if (*t.name_pl) text += ", " + QString::fromUtf8(t.name_pl);
                type_->addItem(text, t.type);
            }
        }
        type_list_kind_ = kind;
    }
    const int index = o.type ? type_->findData(QVariant::fromValue<long long>(*o.type)) : -1;
    type_->setCurrentIndex(index);
    // typ spoza listy: pokazujemy sama wartosc
    if (index < 0) type_->setEditText(o.type ? QString("0x%1").arg(*o.type, 0, 16) : QString());
}

void PropertiesDock::fill_elements() {
    const MapObject& o = *object();
    QSignalBlocker block(elements_);
    elements_->clear();
    scene_->highlight_path(QPainterPath(), false);
    const Projection* projection = o.projection();
    const bool polygon = o.kind() == ObjectKind::Polygon;
    for (int level : o.data->data_levels()) {
        const auto* polys = o.data->polys_for_data_level(level);
        if (!polys) continue;
        auto* level_item = new QTreeWidgetItem(elements_, {QString("Data%1").arg(level)});
        if (o.kind() == ObjectKind::Poi) {
            if (polys->empty() || polys->front().empty()) continue;
            auto* item = new QTreeWidgetItem(level_item, {"POI", "", geo_text(projection, polys->front().front())});
            item->setData(0, Qt::UserRole, level);
            item->setData(1, Qt::UserRole, 0);
            continue;
        }
        // Jak fill_map_object_properteies_elements: w polygonie czesc zawarta w poprzedniej zewnetrznej jest
        // wewnetrzna (dziura), inaczej zaczyna nowa czesc zewnetrzna.
        QTreeWidgetItem* outer = nullptr;
        QPainterPath outer_path;
        for (size_t poly_num = 0; poly_num < polys->size(); ++poly_num) {
            const Poly& poly = (*polys)[poly_num];
            if (poly.empty()) continue;
            const QPainterPath path = poly_path(poly, polygon);
            const bool inner = polygon && outer && outer_path.contains(path);
            auto* item = new QTreeWidgetItem(inner ? outer : level_item);
            item->setText(0, QString("Poly: %1").arg(poly_num));
            item->setText(1, inner ? "Inner" : "Outer");
            item->setText(2, geo_text(projection, poly.front()));
            item->setText(3, QString::number(poly.size()));
            item->setData(0, Qt::UserRole, level);
            item->setData(1, Qt::UserRole, static_cast<qulonglong>(poly_num));
            if (inner) {
                outer_path.addPath(path);
            } else if (polygon) {
                outer = item;
                outer_path = path;
            }
        }
    }
    elements_->expandAll();
}

void PropertiesDock::fill_routing() {
    const MapObject& o = *object();
    const std::array<long long, 12> values = o.routeparam.value_or(std::array<long long, 12>{});
    for (int i = 0; i < 2; ++i) {
        QSignalBlocker block(route_combos_[i]);
        route_combos_[i]->setCurrentIndex(static_cast<int>(values[i]) < route_combos_[i]->count()
                                              ? static_cast<int>(values[i])
                                              : -1);
    }
    for (int i = 2; i < ROUTE_PARAMS; ++i) route_checks_[i]->setChecked(values[i] != 0);
}

void PropertiesDock::set_numbering_fields_enabled(bool enabled) {
    for (NumberingSide* side : {&left_, &right_}) side->box->setEnabled(enabled);
}

void PropertiesDock::fill_node() {
    const MapObject& o = *object();
    const Node* node = o.data->poly_node(grip_->level, grip_->poly, static_cast<long>(grip_->node));
    if (!node) return;
    const NumbersDefinition* def = node->numbers();
    node_has_numbers_->setChecked(def != nullptr);
    set_numbering_fields_enabled(def != nullptr);
    const NumbersDefinition empty;
    const NumbersDefinition& d = def ? *def : empty;
    auto fill_side = [](NumberingSide& side, const OptStr& style, const OptInt& after, const OptInt& before,
                        const OptStr& zip, const OptStr& city, const OptStr& region, const OptStr& country) {
        QSignalBlocker block(side.style);
        side.style->setCurrentIndex(style_index(style));
        side.after->setText(after ? QString::number(*after) : QString());
        side.before->setText(before ? QString::number(*before) : QString());
        side.zip->setText(to_ui(zip));
        side.city->setText(to_ui(city));
        side.region->setText(to_ui(region));
        side.country->setText(to_ui(country));
    };
    fill_side(left_, d.left_side_numbering_style, d.left_side_number_after, d.left_side_number_before,
              d.left_side_zip_code, d.left_side_city, d.left_side_region, d.left_side_country);
    fill_side(right_, d.right_side_numbering_style, d.right_side_number_after, d.right_side_number_before,
              d.right_side_zip_code, d.right_side_city, d.right_side_region, d.right_side_country);
    QSignalBlocker block(hlevel_);
    const OptInt& h = node->hlevel();
    hlevel_->setCurrentIndex(h ? hlevel_->findData(QVariant::fromValue<long long>(*h)) : 0);
}

// ---------------------------------------------------------------- zmiany
void PropertiesDock::commit(const QString& text, const std::function<void(MapObject&)>& change) {
    const MapObject* o = object();
    if (filling_ || !o || grip_) return;
    MapObject after = *o;
    change(after);
    const int precision = scene_->map()->precision();
    if (after.to_mp_record(precision) == o->to_mp_record(precision)) return;  // nic sie nie zmienilo
    scene_->replace_object(*obj_, std::move(after), text);
}

void PropertiesDock::commit_node(const QString& text, const std::function<void(DataX&, const GripRef&)>& change) {
    const MapObject* o = object();
    if (filling_ || !o || !grip_ || !o->data) return;
    MapObject after = *o;
    try {
        change(*after.data, *grip_);
    } catch (const MpError&) {
        return;
    }
    const int precision = scene_->map()->precision();
    if (after.to_mp_record(precision) == o->to_mp_record(precision)) return;
    scene_->replace_object(*obj_, std::move(after), text);
}

void PropertiesDock::type_chosen(int index) {
    if (index < 0) return;
    const long long new_type = type_->itemData(index).toLongLong();
    // nowe obiekty tego rodzaju dostaja ten typ (last_used_type w Pythonie)
    if (const MapObject* o = object()) scene_->set_last_used_type(o->kind(), new_type);
    commit(tr("Edycja type na: 0x%1").arg(new_type, 0, 16), [new_type](MapObject& o) { o.type = new_type; });
}

bool PropertiesDock::eventFilter(QObject* watched, QEvent* event) {
    if (watched == comment_) {
        if (event->type() == QEvent::FocusIn)
            comment_at_focus_ = comment_->toPlainText();
        else if (event->type() == QEvent::FocusOut && comment_->toPlainText() != comment_at_focus_)
            comment_edited();
    }
    return QDockWidget::eventFilter(watched, event);
}

void PropertiesDock::comment_edited() {
    QStringList lines = comment_->toPlainText().split('\n');
    while (!lines.isEmpty() && lines.last().trimmed().isEmpty()) lines.removeLast();
    commit(tr("Zmiana komentarza"), [&](MapObject& o) {
        if (lines.isEmpty()) {
            o.comment.reset();
            return;
        }
        std::vector<std::string> comment;
        for (const QString& line : lines) comment.push_back(encoding::utf8_to_cp1250(line.toStdString()));
        o.comment = std::move(comment);
    });
}

void PropertiesDock::extras_edited() {
    // jak ExtrasTable.get_current_content: klucz bez '=' i niepusta wartosc
    std::vector<std::pair<std::string, std::string>> others;
    for (int row = 0; row < extras_->rowCount(); ++row) {
        const QTableWidgetItem* key_item = extras_->item(row, 0);
        const QTableWidgetItem* value_item = extras_->item(row, 1);
        const QString key = key_item ? key_item->text().trimmed() : QString();
        const QString value = value_item ? value_item->text().trimmed() : QString();
        if (key.isEmpty() || key.contains('=') || value.isEmpty()) continue;
        others.emplace_back(encoding::utf8_to_cp1250(key.toStdString()), encoding::utf8_to_cp1250(value.toStdString()));
    }
    commit(tr("Zmiana extras"), [&](MapObject& o) { o.others = others; });
}

QMimeData* PropertiesDock::copy_extras() const {
    // wiersze, w ktorych zaznaczono klucz albo wartosc (jak ExtrasTable.copy)
    QJsonArray pairs;
    QString text;
    for (int row = 0; row < extras_->rowCount(); ++row) {
        QString key, value;
        if (const QTableWidgetItem* k = extras_->item(row, 0); k && k->isSelected()) key = k->text();
        if (const QTableWidgetItem* v = extras_->item(row, 1); v && v->isSelected()) value = v->text();
        if (key.isEmpty() && value.isEmpty()) continue;
        pairs.append(QJsonArray{key, value});
        text += key + '\t' + value + '\n';
    }
    if (pairs.isEmpty()) return nullptr;
    auto* mime = new QMimeData;
    mime->setData(QStringLiteral("application/json"), QJsonDocument(pairs).toJson(QJsonDocument::Compact));
    mime->setText(text);
    return mime;
}

void PropertiesDock::paste_extras(const QMimeData* mime) {
    if (!mime || !object() || grip_) return;
    std::vector<std::pair<QString, QString>> pairs;
    bool from_json = false;
    if (mime->hasFormat(QStringLiteral("application/json"))) {
        // lista par [klucz, wartosc]
        const QJsonArray array = QJsonDocument::fromJson(mime->data(QStringLiteral("application/json"))).array();
        from_json = !array.isEmpty();
        for (const QJsonValue& v : array) {
            const QJsonArray pair = v.toArray();
            // inne dane JSON to obiekty mapy (rekordy mp) - nie wklejamy ich ani ich tekstu do tabeli
            if (pair.size() != 2) return;
            pairs.emplace_back(pair[0].toString(), pair[1].toString());
        }
    }
    if (!from_json && mime->hasText()) {
        // tekst: wiersze "klucz<TAB>wartosc" albo "klucz=wartosc" (np. z pliku mp albo arkusza)
        for (const QString& line : mime->text().split('\n')) {
            if (line.trimmed().isEmpty()) continue;
            int sep = line.indexOf('\t');
            if (sep < 0) sep = line.indexOf('=');
            if (sep < 0)
                pairs.emplace_back(line.trimmed(), QString());
            else
                pairs.emplace_back(line.left(sep).trimmed(), line.mid(sep + 1).trimmed());
        }
    }
    if (pairs.empty()) return;
    {
        QSignalBlocker block(extras_);
        int row = std::max(extras_->currentRow(), 0);
        for (const auto& [key, value] : pairs) {
            if (row >= extras_->rowCount()) extras_->insertRow(extras_->rowCount());
            if (!key.isEmpty()) extras_->setItem(row, 0, new QTableWidgetItem(key));
            if (!value.isEmpty()) extras_->setItem(row, 1, new QTableWidgetItem(value));
            ++row;
        }
    }
    extras_edited();
}

void PropertiesDock::clear_selected_extras() {
    const QList<QTableWidgetItem*> selected = extras_->selectedItems();
    if (selected.isEmpty()) return;
    {
        QSignalBlocker block(extras_);
        for (QTableWidgetItem* item : selected) item->setText(QString());
    }
    extras_edited();
}

void PropertiesDock::route_params_edited() {
    std::array<long long, 12> values{};
    for (int i = 0; i < 2; ++i) values[i] = std::max(route_combos_[i]->currentIndex(), 0);
    for (int i = 2; i < ROUTE_PARAMS; ++i) values[i] = route_checks_[i]->isChecked() ? 1 : 0;
    commit(tr("modyfikacja RouteParams"), [&](MapObject& o) { o.routeparam = values; });
}

void PropertiesDock::numbering_edited() {
    if (filling_ || !grip_) return;
    NumbersDefinition def;
    auto read_side = [](NumberingSide& side, OptStr& style, OptInt& after, OptInt& before, OptStr& zip, OptStr& city,
                        OptStr& region, OptStr& country) {
        style = style_from_index(side.style->currentIndex());
        // wybrany styl wymaga numeru poczatkowego (jak command_numeration_style_edited)
        if (style && side.after->text().trimmed().isEmpty()) side.after->setText("0");
        after = number_from_ui(side.after->text());
        before = number_from_ui(side.before->text());
        zip = from_ui(side.zip->text());
        city = from_ui(side.city->text());
        region = from_ui(side.region->text());
        country = from_ui(side.country->text());
    };
    read_side(left_, def.left_side_numbering_style, def.left_side_number_after, def.left_side_number_before,
              def.left_side_zip_code, def.left_side_city, def.left_side_region, def.left_side_country);
    read_side(right_, def.right_side_numbering_style, def.right_side_number_after, def.right_side_number_before,
              def.right_side_zip_code, def.right_side_city, def.right_side_region, def.right_side_country);
    commit_node(tr("Zmiana numeracji"), [&](DataX& data, const GripRef& g) {
        Node* node = data.poly_node(g.level, g.poly, static_cast<long>(g.node));
        if (!node) return;
        node->set_numbers(def);
        data.clean_numbers_definitions(g.level, g.poly);
    });
}

void PropertiesDock::node_numbers_toggled(bool on) {
    if (filling_ || !grip_) return;
    commit_node(on ? tr("Dodaj numerację") : tr("Usuń numerację"), [on](DataX& data, const GripRef& g) {
        Node* node = data.poly_node(g.level, g.poly, static_cast<long>(g.node));
        if (!node) return;
        if (on) {
            // jak switch_on_of_numerations: numeracja wyliczona z sasiednich wezlow
            std::optional<NumbersDefinition> def = data.calculated_housenumber_defs_for_node(g.level, g.poly, g.node);
            node->set_numbers(def ? *def : NumbersDefinition{});
        } else {
            node->set_numbers(std::optional<NumbersDefinition>());
        }
        data.clean_numbers_definitions(g.level, g.poly);
    });
    // gdy numeracja nie zostala zapisana (np. czyszczenie ja usunelo), pola wracaja do stanu z danych
    refresh();
}

void PropertiesDock::element_selected() {
    const MapObject* o = object();
    const QList<QTreeWidgetItem*> items = elements_->selectedItems();
    if (!o || items.isEmpty() || !items.front()->data(0, Qt::UserRole).isValid()) {
        scene_->highlight_path(QPainterPath(), false);
        return;
    }
    const int level = items.front()->data(0, Qt::UserRole).toInt();
    const size_t poly_num = items.front()->data(1, Qt::UserRole).toULongLong();
    const auto* polys = o->data->polys_for_data_level(level);
    if (!polys || poly_num >= polys->size() || (*polys)[poly_num].empty()) return;
    const Poly& poly = (*polys)[poly_num];
    if (o->kind() == ObjectKind::Poi) {
        QPainterPath path;
        path.addEllipse(QPointF(poly.front().x(), poly.front().y()), 10, 10);
        scene_->highlight_path(path, true);
    } else {
        const bool polygon = o->kind() == ObjectKind::Polygon;
        scene_->highlight_path(poly_path(poly, polygon), polygon);
    }
}

}  // namespace pwm::gui
