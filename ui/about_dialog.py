"""Диалог «О программе»."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QVBoxLayout

APP_NAME = "ChatList"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = (
    "Приложение для отправки одного промта в несколько нейросетей "
    "и сравнения их ответов. Поддерживает OpenRouter, SQLite, "
    "AI-ассистент для улучшения промтов и экспорт результатов."
)
APP_STACK = "Python 3 · PyQt6 · SQLite · httpx · OpenRouter"


class AboutDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"О программе — {APP_NAME}")
        self.setMinimumWidth(460)

        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        icon_label = QLabel()
        icon_path = Path("app.ico")
        if icon_path.exists():
            pixmap = QPixmap(str(icon_path)).scaled(
                64,
                64,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            icon_label.setPixmap(pixmap)
            self.setWindowIcon(QIcon(str(icon_path)))
        header.addWidget(icon_label)

        title = QLabel(
            f"<h2>{APP_NAME}</h2>"
            f"<p style='color:#6366f1;'><b>версия {APP_VERSION}</b></p>"
        )
        title.setTextFormat(Qt.TextFormat.RichText)
        header.addWidget(title, stretch=1)
        layout.addLayout(header)

        desc = QLabel(
            f"<p>{APP_DESCRIPTION}</p>"
            f"<p><b>Стек:</b> {APP_STACK}</p>"
            f"<p><b>Автор:</b> ChatViewer Project</p>"
        )
        desc.setTextFormat(Qt.TextFormat.RichText)
        desc.setWordWrap(True)
        layout.addWidget(desc)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn:
            ok_btn.setText("Закрыть")
        layout.addWidget(buttons)
