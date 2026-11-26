#include "type_selector.hpp"

#include <QAbstractItemView>
#include <QCompleter>
#include <QDialogButtonBox>
#include <QIcon>
#include <QKeyEvent>
#include <QLabel>
#include <QLineEdit>
#include <QPushButton>
#include <QSignalBlocker>
#include <QVBoxLayout>

#include "map_styles.hpp"
#include "type_names.hpp"

namespace pwm::gui {

TypeComboBox::TypeComboBox(QWidget* parent) : QComboBox(parent) {
    setEditable(true);
    setInsertPolicy(QComboBox::NoInsert);
    setFocusPolicy(Qt::StrongFocus);
    completer()->setFilterMode(Qt::MatchContains);
    completer()->setCaseSensitivity(Qt::CaseInsensitive);
    completer()->setCompletionMode(QCompleter::PopupCompletion);
    // Enter bez wybrania pozycji z listy podpowiedzi: QComboBox z NoInsert wybiera tylko pozycje o identycznym
    // tekscie, inaczej zostawia wpisany fragment. Slot podpiety po slocie QComboBox, wiec dziala po nim.
    connect(lineEdit(), &QLineEdit::returnPressed, this, &TypeComboBox::resolve_text);
}

void TypeComboBox::resolve_text() {
    const QString text = lineEdit()->text();
    if (text == itemText(currentIndex())) return;
    int index = findText(text, Qt::MatchFixedString);  // bez wielkosci liter
    if (index < 0 && !text.isEmpty()) {
        // pierwsza pasujaca podpowiedz (completer filtruje wedlug prefiksu ustawionego przy wpisywaniu)
        completer()->setCompletionPrefix(text);
        QAbstractItemModel* matches = completer()->completionModel();
        if (matches->rowCount() > 0) index = findText(matches->index(0, modelColumn()).data().toString());
    }
    if (index >= 0) {
        setCurrentIndex(index);
        emit activated(index);
    }
    if (QAbstractItemView* popup = completer()->popup()) popup->hide();
    lineEdit()->setText(itemText(currentIndex()));
}

void TypeComboBox::set_kind(ObjectKind kind, const MapStyles* styles) {
    if (static_cast<int>(kind) == kind_) return;
    QSignalBlocker block(this);
    clear();
    if (kind == ObjectKind::Poi) {
        for (const PoiTypeName& t : poi_type_names()) {
            const QString text = QString("0x%1 (%2), %3, %4")
                                     .arg(t.type, 0, 16)
                                     .arg(QString::fromUtf8(t.category), QString::fromUtf8(t.name),
                                          QString::fromUtf8(t.aliases));
            if (styles)
                addItem(QIcon(styles->poi_icon(t.type)), text, t.type);
            else
                addItem(text, t.type);
        }
    } else {
        const auto& names = kind == ObjectKind::Polyline ? line_type_names() : polygon_type_names();
        for (const PolyTypeName& t : names) {
            QString text = QString("0x%1 (%2), %3").arg(t.type, 0, 16).arg(QString::fromUtf8(t.category),
                                                                            QString::fromUtf8(t.name_en));
            if (*t.name_pl) text += ", " + QString::fromUtf8(t.name_pl);
            addItem(text, t.type);
        }
    }
    kind_ = static_cast<int>(kind);
}

void TypeComboBox::set_type(std::optional<long long> type) {
    QSignalBlocker block(this);
    const int index = type ? findData(QVariant::fromValue<long long>(*type)) : -1;
    setCurrentIndex(index);
    // typ spoza listy: pokazujemy sama wartosc
    if (index < 0) setEditText(type ? QString("0x%1").arg(*type, 0, 16) : QString());
}

std::optional<long long> TypeComboBox::current_type() const {
    const int index = currentIndex();
    if (index < 0 || lineEdit()->text() != itemText(index)) return std::nullopt;
    return itemData(index).toLongLong();
}

// ---------------------------------------------------------------- ChangeTypeDialog
ChangeTypeDialog::ChangeTypeDialog(ObjectKind kind, std::optional<long long> type, int count,
                                   const MapStyles* styles, QWidget* parent)
    : QDialog(parent) {
    setWindowTitle(tr("Zamień type dla zaznaczenia"));
    auto* box = new QVBoxLayout(this);
    QString what;
    switch (kind) {
        case ObjectKind::Poi: what = tr("POI"); break;
        case ObjectKind::Polyline: what = tr("polilinie"); break;
        default: what = tr("polygony"); break;
    }
    box->addWidget(new QLabel(tr("Nowy Type dla zaznaczonych obiektów (%1: %2):").arg(what).arg(count), this));
    type_ = new TypeComboBox(this);
    type_->set_kind(kind, styles);
    type_->set_type(type);
    type_->setMinimumContentsLength(40);
    box->addWidget(type_);
    auto* buttons = new QDialogButtonBox(QDialogButtonBox::Ok | QDialogButtonBox::Cancel, this);
    connect(buttons, &QDialogButtonBox::accepted, this, &QDialog::accept);
    connect(buttons, &QDialogButtonBox::rejected, this, &QDialog::reject);
    box->addWidget(buttons);
    // Enter na liscie podpowiedzi zjada QCompleter (wybiera typ, ale okno zostaje) - zamykamy okno po nim
    type_->completer()->popup()->installEventFilter(this);
    type_->setFocus();
    type_->lineEdit()->selectAll();
}

bool ChangeTypeDialog::eventFilter(QObject* watched, QEvent* event) {
    if (watched == type_->completer()->popup() && event->type() == QEvent::KeyPress) {
        const int key = static_cast<QKeyEvent*>(event)->key();
        if (key == Qt::Key_Return || key == Qt::Key_Enter)
            QMetaObject::invokeMethod(this, &ChangeTypeDialog::accept, Qt::QueuedConnection);
    }
    return QDialog::eventFilter(watched, event);
}

void ChangeTypeDialog::accept() {
    // OK z wpisanym fragmentem dziala jak Enter; bez typu z listy okno zostaje otwarte
    type_->resolve_text();
    if (!type_->current_type()) {
        type_->setFocus();
        return;
    }
    QDialog::accept();
}

}  // namespace pwm::gui
