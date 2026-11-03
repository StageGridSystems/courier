"""Dark / light QSS themes for Courier."""

from __future__ import annotations

from courier.branding import COLORS, FONT_MONO, FONT_UI


def stylesheet(theme: str) -> str:
    dark = theme != "light"
    bg = COLORS["dark_bg"] if dark else COLORS["light_bg"]
    surface = COLORS["dark_surface"] if dark else COLORS["light_surface"]
    surface2 = COLORS["dark_surface_2"] if dark else COLORS["light_surface_2"]
    text = COLORS["dark_text"] if dark else COLORS["light_text"]
    muted = COLORS["dark_muted"] if dark else COLORS["light_muted"]
    border = COLORS["border_dark"] if dark else COLORS["border_light"]
    primary = COLORS["primary"]
    primary_h = COLORS["primary_hover"]
    danger = COLORS["danger"]
    warning = COLORS["warning"]

    return f"""
    * {{
        font-family: {FONT_UI};
        font-size: 13px;
    }}
    QMainWindow, QDialog {{
        background-color: {bg};
        color: {text};
    }}
    QLabel {{
        background: transparent;
        border: none;
        color: {text};
    }}
    QFormLayout QLabel, QLabel#mutedLabel, QLabel#cardHeading, QLabel#sectionTitle {{
        background: transparent;
        border: none;
    }}
    QLabel#mutedLabel {{
        color: {muted};
    }}
    QLabel#cardHeading {{
        font-weight: 700;
        font-size: 14px;
    }}
    QTabWidget::pane {{
        border: 1px solid {border};
        border-radius: 10px;
        background: {surface};
        top: -1px;
        padding: 0;
        margin: 0;
    }}
    QTabBar {{
        qproperty-drawBase: 0;
        background: transparent;
    }}
    QTabBar::tab {{
        background: transparent;
        color: {muted};
        padding: 8px 16px;
        margin-right: 4px;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
        font-weight: 600;
    }}
    QTabBar::tab:selected {{
        background: {surface};
        color: {primary};
        border: 1px solid {border};
        border-bottom: 1px solid {surface};
    }}
    QTabBar::tab:hover:!selected {{
        color: {text};
        background: {surface2};
    }}
    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
        background: {bg};
        border: 1px solid {border};
        border-radius: 8px;
        padding: 8px 10px;
        selection-background-color: {primary};
        color: {text};
    }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
        border: 1px solid {primary};
    }}
    QPushButton {{
        background: {surface2};
        color: {text};
        border: 1px solid {border};
        border-radius: 8px;
        padding: 8px 14px;
        font-weight: 600;
    }}
    QPushButton:hover {{
        border-color: {primary};
    }}
    QPushButton:disabled {{
        color: {muted};
        opacity: 0.6;
    }}
    QPushButton#primaryButton {{
        background: {primary};
        color: white;
        border: 1px solid {primary_h};
    }}
    QPushButton#primaryButton:hover {{
        background: {primary_h};
    }}
    QPushButton#dangerButton {{
        background: {danger};
        color: white;
        border: 1px solid {danger};
    }}
    QLabel#brandTitle {{
        font-size: 22px;
        font-weight: 700;
        color: {primary};
        background: transparent;
    }}
    QLabel#sectionTitle {{
        font-size: 16px;
        font-weight: 700;
        background: transparent;
    }}
    QFrame#card {{
        background: {surface};
        border: 1px solid {border};
        border-radius: 12px;
    }}
    QFrame#card QLabel {{
        background: transparent;
        border: none;
    }}
    QFrame#chipField {{
        background: {bg};
        border: 1px solid {border};
        border-radius: 10px;
    }}
    QLabel#emptyState {{
        color: {muted};
        padding: 24px;
        border: 1px dashed {border};
        border-radius: 10px;
        background: transparent;
    }}
    QTableWidget {{
        background: {bg};
        border: 1px solid {border};
        border-radius: 8px;
        gridline-color: {border};
        alternate-background-color: {surface2};
    }}
    QTableWidget::item:selected {{
        background: {primary};
        color: white;
    }}
    QHeaderView::section {{
        background: {surface2};
        color: {muted};
        padding: 8px;
        border: none;
        border-bottom: 1px solid {border};
        font-weight: 600;
    }}
    QTabWidget {{
        background: transparent;
    }}
    QTabWidget > QWidget {{
        background: {surface};
    }}
    QFrame#statusOk {{
        background: rgba(13, 148, 136, 0.15);
        border: 1px solid {primary};
        border-radius: 12px;
    }}
    QFrame#statusWarn {{
        background: rgba(217, 119, 6, 0.12);
        border: 1px solid {warning};
        border-radius: 12px;
    }}
    QFrame#statusErr {{
        background: rgba(220, 38, 38, 0.12);
        border: 1px solid {danger};
        border-radius: 12px;
    }}
    QListWidget, QTreeWidget, QTableWidget {{
        background: {bg};
        border: 1px solid {border};
        border-radius: 8px;
        outline: none;
    }}
    QListWidget::item:selected, QTreeWidget::item:selected {{
        background: {primary};
        color: white;
    }}
    QProgressBar {{
        border: 1px solid {border};
        border-radius: 8px;
        background: {bg};
        text-align: center;
        height: 18px;
    }}
    QProgressBar::chunk {{
        background: {primary};
        border-radius: 7px;
    }}
    QScrollArea {{
        border: none;
        background: transparent;
    }}
    QCheckBox, QRadioButton {{
        spacing: 8px;
    }}
    QGroupBox {{
        border: 1px solid {border};
        border-radius: 10px;
        margin-top: 12px;
        padding: 12px;
        font-weight: 600;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 6px;
        color: {muted};
    }}
    QSplitter::handle {{
        background: {border};
    }}
    QToolTip {{
        background: {surface2};
        color: {text};
        border: 1px solid {border};
        padding: 6px;
    }}
    QTextBrowser {{
        background: {bg};
        border: 1px solid {border};
        border-radius: 8px;
        padding: 8px;
        font-family: {FONT_MONO};
    }}
    """
