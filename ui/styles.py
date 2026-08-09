from __future__ import annotations

# Catppuccin Mocha palette
COLORS = {
    "base": "#1e1e2e",
    "mantle": "#181825",
    "crust": "#11111b",
    "text": "#cdd6f4",
    "subtext": "#a6adc8",
    "blue": "#89b4fa",
    "lavender": "#b4befe",
    "overlay": "#45475a",
    "surface": "#313244",
    "green": "#a6e3a1",
    "red": "#f38ba8",
    "yellow": "#f9e2af",
}

QSS = f"""
/* App base */
QMainWindow {{
    background-color: {COLORS["crust"]};
    color: {COLORS["text"]};
}}

QWidget {{
    background-color: transparent;
    color: {COLORS["text"]};
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 10px;
}}

QToolBar {{
    background-color: {COLORS["surface"]};
    border: none;
    padding: 6px;
    spacing: 10px;
}}

QToolButton {{
    background-color: transparent;
    border: none;
    padding: 8px;
    border-radius: 8px;
}}

QToolButton:hover {{
    background-color: {COLORS["overlay"]};
}}

QPushButton {{
    background-color: {COLORS["blue"]};
    color: {COLORS["crust"]};
    border: none;
    padding: 8px 14px;
    border-radius: 8px;
    font-weight: 700;
}}

QPushButton:hover {{
    background-color: {COLORS["lavender"]};
}}

QPushButton:pressed {{
    background-color: {COLORS["overlay"]};
}}

QPushButton:disabled {{
    background-color: {COLORS["overlay"]};
    color: {COLORS["subtext"]};
}}

QLineEdit, QSpinBox {{
    background-color: {COLORS["surface"]};
    border: 1px solid {COLORS["overlay"]};
    border-radius: 8px;
    padding: 8px;
    color: {COLORS["text"]};
}}

QLineEdit:focus, QSpinBox:focus {{
    border: 1px solid {COLORS["blue"]};
}}

QCheckBox {{
    spacing: 6px;
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid {COLORS["overlay"]};
    background-color: {COLORS["surface"]};
}}

QCheckBox::indicator:checked {{
    background-color: {COLORS["blue"]};
    border: 1px solid {COLORS["blue"]};
}}

QTabWidget::pane {{
    border: 1px solid {COLORS["overlay"]};
    border-radius: 12px;
    background-color: {COLORS["mantle"]};
}}

QTabBar::tab {{
    background-color: {COLORS["surface"]};
    color: {COLORS["subtext"]};
    padding: 10px 18px;
    margin-right: 4px;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
}}

QTabBar::tab:selected {{
    background-color: {COLORS["blue"]};
    color: {COLORS["crust"]};
}}

QLabel {{
    background-color: transparent;
    color: {COLORS["text"]};
}}

QTextEdit {{
    background-color: {COLORS["surface"]};
    border: 1px solid {COLORS["overlay"]};
    border-radius: 10px;
    padding: 10px;
    color: {COLORS["text"]};
}}

QListWidget, QListView {{
    background-color: {COLORS["mantle"]};
    border: 1px solid {COLORS["overlay"]};
    border-radius: 12px;
}}

QListWidget::item {{
    padding: 10px 14px;
    border-radius: 8px;
}}

QListWidget::item:selected {{
    background-color: {COLORS["blue"]};
    color: {COLORS["crust"]};
}}

QProgressBar {{
    border: 1px solid {COLORS["overlay"]};
    border-radius: 8px;
    background-color: {COLORS["surface"]};
    text-align: center;
    color: {COLORS["text"]};
}}

QProgressBar::chunk {{
    background-color: {COLORS["blue"]};
    border-radius: 6px;
}}

"""

def load_qss() -> str:
    return QSS.strip()
