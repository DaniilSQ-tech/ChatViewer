"""Темы оформления и размер шрифта приложения."""

from __future__ import annotations

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

from db import Database

THEME_LIGHT = "light"
THEME_DARK = "dark"

DEFAULT_FONT_SIZE = 10
MIN_FONT_SIZE = 8
MAX_FONT_SIZE = 24


def _light_stylesheet(font_size: int) -> str:
    return f"""
    QWidget {{
        background-color: #f5f5f7;
        color: #1a1a2e;
        font-size: {font_size}pt;
    }}
    QMainWindow, QDialog {{
        background-color: #f5f5f7;
    }}
    QTabWidget::pane {{
        border: 1px solid #d1d5db;
        background: #ffffff;
        border-radius: 4px;
    }}
    QTabBar::tab {{
        background: #e5e7eb;
        color: #374151;
        padding: 8px 16px;
        margin-right: 2px;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
    }}
    QTabBar::tab:selected {{
        background: #ffffff;
        color: #4338ca;
        font-weight: bold;
    }}
    QGroupBox {{
        border: 1px solid #d1d5db;
        border-radius: 6px;
        margin-top: 10px;
        padding-top: 10px;
        background: #ffffff;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 4px;
        color: #4338ca;
    }}
    QLineEdit, QTextEdit, QSpinBox, QComboBox {{
        background: #ffffff;
        border: 1px solid #d1d5db;
        border-radius: 4px;
        padding: 4px;
        color: #1a1a2e;
    }}
    QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QComboBox:focus {{
        border: 1px solid #6366f1;
    }}
    QPushButton {{
        background-color: #6366f1;
        color: #ffffff;
        border: none;
        border-radius: 4px;
        padding: 6px 14px;
        font-weight: bold;
    }}
    QPushButton:hover {{
        background-color: #4f46e5;
    }}
    QPushButton:disabled {{
        background-color: #c7c9d1;
        color: #6b7280;
    }}
    QTableWidget {{
        background: #ffffff;
        alternate-background-color: #f9fafb;
        gridline-color: #e5e7eb;
        border: 1px solid #d1d5db;
    }}
    QHeaderView::section {{
        background: #eef2ff;
        color: #3730a3;
        padding: 6px;
        border: none;
        border-bottom: 1px solid #c7d2fe;
        font-weight: bold;
    }}
    QStatusBar {{
        background: #eef2ff;
        color: #4338ca;
    }}
    QMenuBar {{
        background: #ffffff;
        color: #1a1a2e;
    }}
    QMenuBar::item:selected {{
        background: #eef2ff;
    }}
    QMenu {{
        background: #ffffff;
        border: 1px solid #d1d5db;
    }}
    QMenu::item:selected {{
        background: #eef2ff;
        color: #4338ca;
    }}
    QProgressBar {{
        border: 1px solid #d1d5db;
        border-radius: 4px;
        text-align: center;
        background: #ffffff;
    }}
    QProgressBar::chunk {{
        background: #6366f1;
        border-radius: 3px;
    }}
    """


def _dark_stylesheet(font_size: int) -> str:
    return f"""
    QWidget {{
        background-color: #1e1e2e;
        color: #e4e4ef;
        font-size: {font_size}pt;
    }}
    QMainWindow, QDialog {{
        background-color: #1e1e2e;
    }}
    QTabWidget::pane {{
        border: 1px solid #3d3d5c;
        background: #2a2a3d;
        border-radius: 4px;
    }}
    QTabBar::tab {{
        background: #252536;
        color: #a0a0b8;
        padding: 8px 16px;
        margin-right: 2px;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
    }}
    QTabBar::tab:selected {{
        background: #2a2a3d;
        color: #a5b4fc;
        font-weight: bold;
    }}
    QGroupBox {{
        border: 1px solid #3d3d5c;
        border-radius: 6px;
        margin-top: 10px;
        padding-top: 10px;
        background: #2a2a3d;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 4px;
        color: #a5b4fc;
    }}
    QLineEdit, QTextEdit, QSpinBox, QComboBox {{
        background: #252536;
        border: 1px solid #3d3d5c;
        border-radius: 4px;
        padding: 4px;
        color: #e4e4ef;
    }}
    QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QComboBox:focus {{
        border: 1px solid #6366f1;
    }}
    QPushButton {{
        background-color: #6366f1;
        color: #ffffff;
        border: none;
        border-radius: 4px;
        padding: 6px 14px;
        font-weight: bold;
    }}
    QPushButton:hover {{
        background-color: #818cf8;
    }}
    QPushButton:disabled {{
        background-color: #3d3d5c;
        color: #6b6b80;
    }}
    QTableWidget {{
        background: #252536;
        alternate-background-color: #2a2a3d;
        gridline-color: #3d3d5c;
        border: 1px solid #3d3d5c;
        color: #e4e4ef;
    }}
    QHeaderView::section {{
        background: #313148;
        color: #c7d2fe;
        padding: 6px;
        border: none;
        border-bottom: 1px solid #4338ca;
        font-weight: bold;
    }}
    QStatusBar {{
        background: #252536;
        color: #a5b4fc;
    }}
    QMenuBar {{
        background: #252536;
        color: #e4e4ef;
    }}
    QMenuBar::item:selected {{
        background: #313148;
    }}
    QMenu {{
        background: #2a2a3d;
        border: 1px solid #3d3d5c;
        color: #e4e4ef;
    }}
    QMenu::item:selected {{
        background: #4338ca;
    }}
    QProgressBar {{
        border: 1px solid #3d3d5c;
        border-radius: 4px;
        text-align: center;
        background: #252536;
        color: #e4e4ef;
    }}
    QProgressBar::chunk {{
        background: #6366f1;
        border-radius: 3px;
    }}
    """


def get_theme(database: Database) -> str:
    theme = (database.get_setting("theme", THEME_LIGHT) or THEME_LIGHT).lower()
    return theme if theme in (THEME_LIGHT, THEME_DARK) else THEME_LIGHT


def get_font_size(database: Database) -> int:
    raw = database.get_setting("font_size", str(DEFAULT_FONT_SIZE)) or str(
        DEFAULT_FONT_SIZE
    )
    try:
        size = int(raw)
    except ValueError:
        size = DEFAULT_FONT_SIZE
    return max(MIN_FONT_SIZE, min(MAX_FONT_SIZE, size))


def apply_appearance(app: QApplication, database: Database) -> None:
    theme = get_theme(database)
    font_size = get_font_size(database)
    stylesheet = (
        _dark_stylesheet(font_size)
        if theme == THEME_DARK
        else _light_stylesheet(font_size)
    )
    app.setStyleSheet(stylesheet)
    font = app.font()
    font.setPointSize(font_size)
    app.setFont(font)
