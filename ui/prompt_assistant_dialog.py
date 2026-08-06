"""Диалог с результатами улучшения промта."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from prompt_assistant import PromptImprovementResult

ADAPTATION_LABELS = {
    "code": "Код",
    "analysis": "Анализ",
    "creative": "Креатив",
}


class PromptAssistantDialog(QDialog):
    apply_requested = pyqtSignal(str)

    def __init__(
        self,
        result: PromptImprovementResult,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("AI-ассистент — улучшение промта")
        self.setMinimumSize(720, 560)
        self.resize(820, 640)

        layout = QVBoxLayout(self)

        layout.addWidget(self._section_label("Исходный промт"))
        original_view = QTextEdit()
        original_view.setReadOnly(True)
        original_view.setPlainText(result.original)
        original_view.setMaximumHeight(100)
        layout.addWidget(original_view)

        layout.addWidget(self._section_label("Улучшенный промт"))
        improved_row = QHBoxLayout()
        improved_view = QTextEdit()
        improved_view.setReadOnly(True)
        improved_view.setPlainText(result.improved)
        improved_row.addWidget(improved_view)
        improved_row.addWidget(self._apply_button(result.improved))
        layout.addLayout(improved_row)

        if result.alternatives:
            alt_group = QGroupBox("Альтернативные варианты")
            alt_layout = QVBoxLayout(alt_group)
            for index, alternative in enumerate(result.alternatives, start=1):
                alt_layout.addLayout(
                    self._variant_row(f"Вариант {index}", alternative)
                )
            layout.addWidget(alt_group)

        if result.adaptations:
            tabs = QTabWidget()
            for key, label in ADAPTATION_LABELS.items():
                text = result.adaptations.get(key, "")
                if not text:
                    continue
                tab = QWidget()
                tab_layout = QVBoxLayout(tab)
                view = QTextEdit()
                view.setReadOnly(True)
                view.setPlainText(text)
                tab_layout.addWidget(view)
                tab_layout.addWidget(
                    self._apply_button(text),
                    alignment=Qt.AlignmentFlag.AlignRight,
                )
                tabs.addTab(tab, label)
            layout.addWidget(tabs)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        close_btn = buttons.button(QDialogButtonBox.StandardButton.Close)
        if close_btn:
            close_btn.setText("Закрыть")
        layout.addWidget(buttons)

    @staticmethod
    def _section_label(text: str) -> QLabel:
        return QLabel(f"<b>{text}</b>")

    def _apply_button(self, text: str) -> QPushButton:
        button = QPushButton("Подставить")
        button.clicked.connect(lambda: self._apply(text))
        return button

    def _variant_row(self, title: str, text: str) -> QHBoxLayout:
        row = QHBoxLayout()
        label = QLabel(f"<b>{title}</b>")
        row.addWidget(label)
        view = QTextEdit()
        view.setReadOnly(True)
        view.setPlainText(text)
        view.setMaximumHeight(90)
        row.addWidget(view)
        row.addWidget(self._apply_button(text))
        return row

    def _apply(self, text: str) -> None:
        self.apply_requested.emit(text)
        self.accept()
