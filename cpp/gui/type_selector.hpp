// Wybor typu (Type) obiektu z listy: TypeComboBox (panel wlasciwosci i okno zmiany typu) i ChangeTypeDialog
// (Tools -> Zamień type dla zaznaczenia).
#pragma once

#include <QComboBox>
#include <QDialog>
#include <optional>

#include "map_object.hpp"

namespace pwm::gui {

class MapStyles;

// Lista typow jednego rodzaju obiektow (POI z ikonami, polilinie, polygony) z wyszukiwaniem jak TypeComboBox
// w Pythonie: wpisany tekst filtruje liste (dowolny fragment, bez wielkosci liter), Enter bez wybrania pozycji
// z podpowiedzi bierze pierwszy pasujacy typ (emituje activated), a gdy nic nie pasuje - przywraca nazwe
// biezacego typu. Wpisany tekst nigdy nie trafia do listy jako nowa pozycja.
class TypeComboBox : public QComboBox {
    Q_OBJECT
public:
    explicit TypeComboBox(QWidget* parent = nullptr);

    // Buduje liste typow danego rodzaju (bez przebudowy, gdy rodzaj sie nie zmienil).
    void set_kind(ObjectKind kind, const MapStyles* styles);
    // Ustawia biezacy typ; typ spoza listy pokazuje sama wartoscia, brak typu - pustym polem.
    void set_type(std::optional<long long> type);
    // Typ biezacej pozycji listy (brak, gdy pole nie pokazuje pozycji z listy).
    std::optional<long long> current_type() const;
    // Wpisany tekst -> pozycja listy (jak Enter): ta sama nazwa albo pierwsza pasujaca podpowiedz; bez
    // dopasowania pole wraca do biezacej pozycji. Emituje activated, gdy wybrano pozycje.
    void resolve_text();

private:
    int kind_ = -1;  // ObjectKind, dla ktorego zbudowano liste
};

// Okno wyboru typu dla zaznaczonych obiektow jednego rodzaju. Na starcie pokazuje wspolny typ obiektow
// (gdy roznia sie typem - puste pole); OK dziala dopiero po wybraniu typu z listy.
class ChangeTypeDialog : public QDialog {
    Q_OBJECT
public:
    ChangeTypeDialog(ObjectKind kind, std::optional<long long> type, int count, const MapStyles* styles,
                     QWidget* parent = nullptr);

    TypeComboBox* type_selector() const { return type_; }
    std::optional<long long> chosen_type() const { return type_->current_type(); }

    void accept() override;

protected:
    bool eventFilter(QObject* watched, QEvent* event) override;

private:
    TypeComboBox* type_ = nullptr;
};

}  // namespace pwm::gui
