#include "theme.hpp"

#include <QApplication>
#include <QFile>
#include <QIconEngine>
#include <QImage>
#include <QPainter>
#include <QPixmap>
#include <QStyleHints>
#include <QSvgRenderer>
#include <memory>

namespace pwm::gui {

namespace {

// znaczniki kolorow w plikach SVG ikon
constexpr const char* ICON_INK = "currentColor";
constexpr const char* ICON_ACCENT = "#3d7bd9";

const ThemeColours LIGHT_COLOURS{QColor("#2b2b2b"), QColor("#a8a8a8"), QColor("#2f6fde"), QColor("#e9e9ec"),
                                 QColor("#c8c8cc"), QColor("#dcdce1"), QColor("#cdcdd3"), QColor("#bdbdc3")};
const ThemeColours DARK_COLOURS{QColor("#dfe1e5"), QColor("#6f737a"), QColor("#6ea8fe"), QColor("#313338"),
                                QColor("#1e1f22"), QColor("#3e4045"), QColor("#46494f"), QColor("#4e5157")};

// Ikona rysowana z SVG w kazdym rozmiarze (ostra przy skalowaniu ekranu); osobny rysunek dla trybu Disabled.
class ThemedSvgEngine : public QIconEngine {
public:
    ThemedSvgEngine(const QByteArray& normal, const QByteArray& disabled)
        : normal_(std::make_shared<QSvgRenderer>(normal)), disabled_(std::make_shared<QSvgRenderer>(disabled)) {}

    void paint(QPainter* painter, const QRect& rect, QIcon::Mode mode, QIcon::State) override {
        (mode == QIcon::Disabled ? disabled_ : normal_)->render(painter, rect);
    }
    QPixmap pixmap(const QSize& size, QIcon::Mode mode, QIcon::State state) override {
        return scaledPixmap(size, mode, state, 1.0);
    }
    QPixmap scaledPixmap(const QSize& size, QIcon::Mode mode, QIcon::State state, qreal scale) override {
        QImage image((QSizeF(size) * scale).toSize(), QImage::Format_ARGB32_Premultiplied);
        image.fill(Qt::transparent);
        {
            QPainter painter(&image);
            painter.setRenderHint(QPainter::Antialiasing);
            paint(&painter, image.rect(), mode, state);
        }
        QPixmap pix = QPixmap::fromImage(image);
        pix.setDevicePixelRatio(scale);
        return pix;
    }
    QSize actualSize(const QSize& size, QIcon::Mode, QIcon::State) override { return size; }
    QIconEngine* clone() const override { return new ThemedSvgEngine(*this); }
    QString key() const override { return QStringLiteral("pwm_themed_svg"); }
    bool isNull() override { return !normal_->isValid(); }

private:
    std::shared_ptr<QSvgRenderer> normal_;
    std::shared_ptr<QSvgRenderer> disabled_;
};

QByteArray recolour(QByteArray svg, const QColor& ink, const QColor& accent) {
    svg.replace(ICON_INK, ink.name().toLatin1());
    svg.replace(ICON_ACCENT, accent.name().toLatin1());
    return svg;
}

void set_colour(QPalette& p, QPalette::ColorRole role, const QColor& active, const QColor& disabled) {
    p.setColor(QPalette::Active, role, active);
    p.setColor(QPalette::Inactive, role, active);
    p.setColor(QPalette::Disabled, role, disabled);
}

void set_colour(QPalette& p, QPalette::ColorRole role, const QColor& colour) { set_colour(p, role, colour, colour); }

bool system_dark() {
    return QGuiApplication::styleHints()->colorScheme() == Qt::ColorScheme::Dark;
}

}  // namespace

QString theme_mode_name(ThemeMode mode) {
    switch (mode) {
        case ThemeMode::Light: return QStringLiteral("light");
        case ThemeMode::Dark: return QStringLiteral("dark");
        case ThemeMode::System: break;
    }
    return QStringLiteral("system");
}

ThemeMode theme_mode_from_name(const QString& name) {
    const QString n = name.trimmed().toLower();
    if (n == QLatin1String("light")) return ThemeMode::Light;
    if (n == QLatin1String("dark")) return ThemeMode::Dark;
    return ThemeMode::System;
}

Theme* Theme::instance() {
    static Theme* theme = new Theme();  // zyje do konca programu (rodzicem jest aplikacja)
    return theme;
}

Theme::Theme() : QObject(QCoreApplication::instance()) {
    // zmiana schematu w systemie (np. tryb ciemny Windows) - tylko w trybie System
    connect(QGuiApplication::styleHints(), &QStyleHints::colorSchemeChanged, this, [this] {
        if (mode_ == ThemeMode::System && !applying_) apply();
    });
}

void Theme::set_mode(ThemeMode mode) {
    mode_ = mode;
    apply();
}

void Theme::apply() {
    applying_ = true;
    QStyleHints* hints = QGuiApplication::styleHints();
#if QT_VERSION >= QT_VERSION_CHECK(6, 8, 0)
    // schemat przekazany systemowi - pasek tytulu okna (Windows) w tym samym kolorze co program
    if (mode_ == ThemeMode::System)
        hints->unsetColorScheme();
    else
        hints->setColorScheme(mode_ == ThemeMode::Dark ? Qt::ColorScheme::Dark : Qt::ColorScheme::Light);
#endif
    dark_ = mode_ == ThemeMode::Dark || (mode_ == ThemeMode::System && system_dark());
    QApplication::setPalette(dark_ ? dark_palette() : light_palette());
    applying_ = false;
    emit changed();
}

const ThemeColours& Theme::colours() const { return dark_ ? DARK_COLOURS : LIGHT_COLOURS; }

QString Theme::toolbar_style_sheet() const {
    const ThemeColours& c = colours();
    QColor checked = c.accent;
    checked.setAlphaF(dark_ ? 0.35 : 0.22);
    const QString checked_rgba = QStringLiteral("rgba(%1, %2, %3, %4)")
                                     .arg(checked.red())
                                     .arg(checked.green())
                                     .arg(checked.blue())
                                     .arg(checked.alphaF(), 0, 'f', 2);
    return QStringLiteral(
               "QToolBar { background: %1; border: none; border-bottom: 1px solid %2; spacing: 2px; padding: 3px; }"
               "QToolBar::separator { background: %3; width: 1px; height: 1px; margin: 4px 6px; }"
               "QToolButton { background: transparent; border: 1px solid transparent; border-radius: 4px;"
               " padding: 3px; }"
               "QToolButton:hover { background: %4; }"
               "QToolButton:pressed { background: %5; }"
               "QToolButton:checked { background: %6; border-color: %7; }"
               "QToolButton:disabled { background: transparent; border-color: transparent; }")
        .arg(c.toolbar.name(), c.toolbar_border.name(), c.separator.name(), c.hover.name(), c.pressed.name(),
             checked_rgba, c.accent.name());
}

QIcon Theme::themed_icon(const QString& svg_file) const {
    QFile file(svg_file);
    if (!file.open(QIODevice::ReadOnly)) return QIcon();
    const QByteArray svg = file.readAll();
    const ThemeColours& c = colours();
    return QIcon(new ThemedSvgEngine(recolour(svg, c.icon, c.accent),
                                     recolour(svg, c.icon_disabled, c.icon_disabled)));
}

QPalette Theme::light_palette() {
    // klasyczna jasna paleta stylu Fusion (taka jak przed wprowadzeniem motywow)
    QPalette p;
    const QColor disabled_text("#bebebe");
    set_colour(p, QPalette::Window, QColor("#efefef"));
    set_colour(p, QPalette::WindowText, Qt::black, disabled_text);
    set_colour(p, QPalette::Base, Qt::white, QColor("#efefef"));
    set_colour(p, QPalette::AlternateBase, QColor("#f7f7f7"));
    set_colour(p, QPalette::ToolTipBase, QColor("#ffffdc"));
    set_colour(p, QPalette::ToolTipText, Qt::black);
    set_colour(p, QPalette::PlaceholderText, QColor("#808080"), disabled_text);
    set_colour(p, QPalette::Text, Qt::black, disabled_text);
    set_colour(p, QPalette::Button, QColor("#efefef"));
    set_colour(p, QPalette::ButtonText, Qt::black, disabled_text);
    set_colour(p, QPalette::BrightText, Qt::white);
    set_colour(p, QPalette::Light, Qt::white);
    set_colour(p, QPalette::Midlight, QColor("#cacaca"));
    set_colour(p, QPalette::Mid, QColor("#b8b8b8"));
    set_colour(p, QPalette::Dark, QColor("#9f9f9f"));
    set_colour(p, QPalette::Shadow, QColor("#767676"));
    set_colour(p, QPalette::Highlight, QColor("#308cc6"), QColor("#919191"));
    set_colour(p, QPalette::HighlightedText, Qt::white);
    set_colour(p, QPalette::Link, QColor("#0000ff"));
    set_colour(p, QPalette::LinkVisited, QColor("#ff00ff"));
    set_colour(p, QPalette::Accent, QColor("#308cc6"), QColor("#919191"));
    return p;
}

QPalette Theme::dark_palette() {
    // grafit w stylu IDE; akcent #3d7bd9
    QPalette p;
    const QColor text("#dfe1e5");
    const QColor disabled_text("#6f737a");
    set_colour(p, QPalette::Window, QColor("#2b2d30"));
    set_colour(p, QPalette::WindowText, text, disabled_text);
    set_colour(p, QPalette::Base, QColor("#1e1f22"), QColor("#2b2d30"));
    set_colour(p, QPalette::AlternateBase, QColor("#26282b"));
    set_colour(p, QPalette::ToolTipBase, QColor("#3c3f41"));
    set_colour(p, QPalette::ToolTipText, text);
    set_colour(p, QPalette::PlaceholderText, QColor("#8b8e94"), disabled_text);
    set_colour(p, QPalette::Text, text, disabled_text);
    set_colour(p, QPalette::Button, QColor("#3c3f41"), QColor("#2f3134"));
    set_colour(p, QPalette::ButtonText, text, disabled_text);
    set_colour(p, QPalette::BrightText, QColor("#ff6b68"));
    set_colour(p, QPalette::Light, QColor("#4e5157"));
    set_colour(p, QPalette::Midlight, QColor("#45484d"));
    set_colour(p, QPalette::Mid, QColor("#4e5157"));
    set_colour(p, QPalette::Dark, QColor("#1b1c1f"));
    set_colour(p, QPalette::Shadow, Qt::black);
    set_colour(p, QPalette::Highlight, QColor("#3d7bd9"), QColor("#3a3d41"));
    set_colour(p, QPalette::HighlightedText, Qt::white, disabled_text);
    set_colour(p, QPalette::Link, QColor("#6ea8fe"));
    set_colour(p, QPalette::LinkVisited, QColor("#b392f0"));
    set_colour(p, QPalette::Accent, QColor("#3d7bd9"), QColor("#3a3d41"));
    return p;
}

}  // namespace pwm::gui
