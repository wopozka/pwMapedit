// Motyw okna: jasny, ciemny albo wedlug systemu (menu View -> Motyw, klucz "theme" w ustawieniach).
// Ustawia palete aplikacji i podaje kolory dla paska narzedzi i ikon. Mapa nie zmienia kolorow
// (zawsze jasna - kolory Garmina sa dobrane pod jasne tlo).
//
// Ikony paska narzedzi (icons/toolbar_icons/line/*.svg) maja kolory jako znaczniki:
//   currentColor - kontur, #3d7bd9 - akcent;
// themed_icon() podmienia je na kolory biezacego motywu (osobno dla ikony nieaktywnej).
#pragma once

#include <QColor>
#include <QIcon>
#include <QObject>
#include <QPalette>
#include <QString>

namespace pwm::gui {

enum class ThemeMode { System, Light, Dark };

// "system" / "light" / "dark" (zapis w ustawieniach); nieznana nazwa -> System
QString theme_mode_name(ThemeMode mode);
ThemeMode theme_mode_from_name(const QString& name);

struct ThemeColours {
    QColor icon;           // kontur ikon
    QColor icon_disabled;  // kontur i akcent ikony nieaktywnej
    QColor accent;         // akcent ikon i zaznaczone narzedzie
    QColor toolbar;        // tlo paska narzedzi
    QColor toolbar_border;
    QColor hover;          // tlo przycisku pod mysza
    QColor pressed;
    QColor separator;
};

class Theme : public QObject {
    Q_OBJECT
public:
    static Theme* instance();

    ThemeMode mode() const { return mode_; }
    // Ustawia tryb i stosuje palete (takze gdy tryb sie nie zmienil). W trybie System sledzi zmiany
    // schematu kolorow systemu.
    void set_mode(ThemeMode mode);
    // Faktycznie uzywany wariant (System rozstrzygniety wedlug QStyleHints::colorScheme()).
    bool dark() const { return dark_; }
    const ThemeColours& colours() const;

    // Arkusz stylu paska narzedzi dla biezacego motywu.
    QString toolbar_style_sheet() const;
    // Ikona z pliku SVG z podmienionymi kolorami biezacego motywu. Pusta ikona, gdy pliku nie ma.
    QIcon themed_icon(const QString& svg_file) const;

    static QPalette light_palette();
    static QPalette dark_palette();

signals:
    void changed();

private:
    Theme();
    void apply();

    ThemeMode mode_ = ThemeMode::System;
    bool dark_ = false;
    bool applying_ = false;
};

}  // namespace pwm::gui
