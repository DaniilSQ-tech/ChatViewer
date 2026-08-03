"""Окно просмотра ответа с форматированием."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QLabel, QMainWindow, QTextEdit, QVBoxLayout, QWidget


class ResponseViewWindow(QMainWindow):
    """Отдельное окно с отформатированным текстом ответа модели."""

    def __init__(
        self,
        model_name: str,
        response_text: str,
        prompt_text: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Ответ — {model_name}")
        self.setMinimumSize(640, 480)
        self.resize(900, 650)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(12, 12, 12, 12)

        title = QLabel(f"<b>{model_name}</b>")
        title.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(title)

        if prompt_text:
            prompt_label = QLabel("Промт:")
            prompt_label.setStyleSheet("color: #666; font-weight: bold;")
            layout.addWidget(prompt_label)

            prompt_view = QTextEdit()
            prompt_view.setReadOnly(True)
            prompt_view.setMaximumHeight(100)
            prompt_view.setPlainText(prompt_text)
            layout.addWidget(prompt_view)

        response_label = QLabel("Ответ:")
        response_label.setStyleSheet("color: #666; font-weight: bold;")
        layout.addWidget(response_label)

        self.response_view = QTextEdit()
        self.response_view.setReadOnly(True)
        self.response_view.setFont(QFont("Segoe UI", 10))
        self._set_formatted_text(response_text)
        layout.addWidget(self.response_view)

        self.setCentralWidget(container)

    def _set_formatted_text(self, text: str) -> None:
        """Показывает markdown, если возможно, иначе обычный текст."""
        stripped = text.strip()
        if not stripped:
            self.response_view.setPlainText("")
            return

        looks_like_markdown = any(
            marker in stripped
            for marker in ("```", "**", "__", "\n#", "\n- ", "\n* ", "`", "> ")
        ) or stripped.startswith("#")

        if looks_like_markdown:
            self.response_view.setMarkdown(stripped)
        else:
            self.response_view.setPlainText(stripped)
