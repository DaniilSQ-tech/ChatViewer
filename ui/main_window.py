"""Главное окно ChatList."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QStatusBar,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from db import Database, Prompt, Result
from export import export_json, export_markdown
from models import AIModel, ModelManager, ModelValidationError
from network import NetworkClient, SUPPORTED_PROVIDERS
from prompt_assistant import PromptAssistant, PromptImprovementResult
from session import SessionResults
from ui.about_dialog import AboutDialog
from ui.app_theme import (
    THEME_DARK,
    THEME_LIGHT,
    apply_appearance,
    get_font_size,
    get_theme,
)
from ui.prompt_assistant_dialog import PromptAssistantDialog
from ui.response_view import ResponseViewWindow
from workers import ImprovePromptWorker, SendPromptWorker


class ModelDialog(QDialog):
    def __init__(
        self,
        parent: QWidget | None = None,
        model: AIModel | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Редактирование модели" if model else "Новая модель")
        self._model_id = model.id if model else None

        self.name_edit = QLineEdit(model.name if model else "")
        self.url_edit = QLineEdit(model.api_url if model else "")
        self.api_id_edit = QLineEdit(model.api_id if model else "")
        self.key_env_edit = QLineEdit(model.api_key_env if model else "OPENROUTER_API_KEY")
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(sorted(SUPPORTED_PROVIDERS))
        if model:
            idx = self.provider_combo.findText(model.provider)
            if idx >= 0:
                self.provider_combo.setCurrentIndex(idx)
        self.active_check = QCheckBox("Активна")
        self.active_check.setChecked(model.is_active if model else True)

        form = QFormLayout()
        form.addRow("Название:", self.name_edit)
        form.addRow("API URL:", self.url_edit)
        form.addRow("ID модели:", self.api_id_edit)
        form.addRow("Переменная .env:", self.key_env_edit)
        form.addRow("Провайдер:", self.provider_combo)
        form.addRow("", self.active_check)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def values(self) -> dict[str, str | bool]:
        return {
            "name": self.name_edit.text().strip(),
            "api_url": self.url_edit.text().strip(),
            "api_id": self.api_id_edit.text().strip(),
            "api_key_env": self.key_env_edit.text().strip(),
            "provider": self.provider_combo.currentText(),
            "is_active": self.active_check.isChecked(),
        }


class MainWindow(QMainWindow):
    def __init__(
        self,
        database: Database,
        model_manager: ModelManager,
        network: NetworkClient,
    ) -> None:
        super().__init__()
        self.db = database
        self.model_manager = model_manager
        self.network = network
        self.session = SessionResults()
        self._prompt_assistant = PromptAssistant()
        self._worker: SendPromptWorker | None = None
        self._improve_worker: ImprovePromptWorker | None = None
        self._assistant_model: AIModel | None = None
        self._current_prompt_id: int | None = None
        self._updating_prompt_combo = False
        self._response_windows: list[ResponseViewWindow] = []

        self.setWindowTitle("ChatList")
        width = int(self.db.get_setting("window_width", "1200") or "1200")
        height = int(self.db.get_setting("window_height", "800") or "800")
        self.resize(width, height)
        self.setMinimumSize(900, 600)

        self._build_menu()
        self._build_tabs()
        self._build_status_bar()
        self._refresh_all()

    def _build_menu(self) -> None:
        menu = self.menuBar().addMenu("Файл")
        export_md = QAction("Экспорт результатов в Markdown", self)
        export_md.triggered.connect(lambda: self._export_results("md"))
        menu.addAction(export_md)
        export_json_action = QAction("Экспорт результатов в JSON", self)
        export_json_action.triggered.connect(lambda: self._export_results("json"))
        menu.addAction(export_json_action)
        menu.addSeparator()
        quit_action = QAction("Выход", self)
        quit_action.triggered.connect(self.close)
        menu.addAction(quit_action)

        help_menu = self.menuBar().addMenu("Справка")
        about_action = QAction("О программе", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _build_status_bar(self) -> None:
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumWidth(250)
        self.status_bar.addPermanentWidget(self.progress_bar)

    def _build_tabs(self) -> None:
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.tabs.addTab(self._build_query_tab(), "Запрос")
        self.tabs.addTab(self._build_results_tab(), "Результаты")
        self.tabs.addTab(self._build_history_tab(), "История")
        self.tabs.addTab(self._build_models_tab(), "Модели")
        self.tabs.addTab(self._build_settings_tab(), "Настройки")
        self.tabs.addTab(self._build_logs_tab(), "Логи")

    def _build_query_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        saved_group = QGroupBox("Сохранённые промты")
        saved_layout = QVBoxLayout(saved_group)
        search_row = QHBoxLayout()
        self.prompt_search = QLineEdit()
        self.prompt_search.setPlaceholderText("Поиск по тексту или тегам...")
        self.prompt_search.textChanged.connect(self._filter_prompt_combo)
        search_row.addWidget(self.prompt_search)
        saved_layout.addLayout(search_row)

        self.prompt_combo = QComboBox()
        self.prompt_combo.setPlaceholderText("Выберите сохранённый промт")
        self.prompt_combo.currentIndexChanged.connect(self._on_prompt_selected)
        saved_layout.addWidget(self.prompt_combo)
        layout.addWidget(saved_group)

        layout.addWidget(QLabel("Новый промт:"))
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText("Введите текст запроса...")
        self.prompt_edit.setMinimumHeight(120)
        layout.addWidget(self.prompt_edit)

        tags_row = QHBoxLayout()
        tags_row.addWidget(QLabel("Теги:"))
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("python, api, test")
        tags_row.addWidget(self.tags_edit)
        layout.addLayout(tags_row)

        btn_row = QHBoxLayout()
        self.improve_btn = QPushButton("Улучшить промт")
        self.improve_btn.clicked.connect(self._on_improve_prompt)
        self.improve_btn.setToolTip(
            "Отправить промт в AI-ассистент для улучшения и переформулировки"
        )
        self.send_btn = QPushButton("Отправить")
        self.send_btn.clicked.connect(self._on_send)
        btn_row.addWidget(self.improve_btn)
        btn_row.addWidget(self.send_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        return widget

    def _build_results_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        btn_row = QHBoxLayout()
        self.save_btn = QPushButton("Сохранить выбранные")
        self.save_btn.clicked.connect(self._on_save_results)
        self.select_all_btn = QPushButton("Выбрать все")
        self.select_all_btn.clicked.connect(lambda: self._set_all_selected(True))
        self.deselect_all_btn = QPushButton("Снять выделение")
        self.deselect_all_btn.clicked.connect(lambda: self._set_all_selected(False))
        btn_row.addWidget(self.save_btn)
        btn_row.addWidget(self.select_all_btn)
        btn_row.addWidget(self.deselect_all_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.results_table = QTableWidget(0, 4)
        self.results_table.setHorizontalHeaderLabels(["", "Модель", "Ответ", ""])
        self.results_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self.results_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self.results_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self.results_table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents
        )
        self.results_table.setSortingEnabled(False)
        self.results_table.itemChanged.connect(self._on_result_item_changed)
        layout.addWidget(self.results_table)

        return widget

    def _build_history_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        search_row = QHBoxLayout()
        self.history_search = QLineEdit()
        self.history_search.setPlaceholderText("Поиск по промту, модели или ответу...")
        self.history_search.textChanged.connect(self._refresh_history)
        search_row.addWidget(self.history_search)
        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self._refresh_history)
        search_row.addWidget(refresh_btn)
        layout.addLayout(search_row)

        self.history_table = QTableWidget(0, 5)
        self.history_table.setHorizontalHeaderLabels(
            ["Дата", "Промт", "Модель", "Ответ", "ID"]
        )
        self.history_table.setColumnHidden(4, True)
        self.history_table.setSortingEnabled(True)
        header = self.history_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.history_table)

        return widget

    def _build_models_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("Добавить")
        add_btn.clicked.connect(self._on_add_model)
        edit_btn = QPushButton("Редактировать")
        edit_btn.clicked.connect(self._on_edit_model)
        toggle_btn = QPushButton("Вкл./Выкл.")
        toggle_btn.clicked.connect(self._on_toggle_model)
        delete_btn = QPushButton("Удалить")
        delete_btn.clicked.connect(self._on_delete_model)
        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self._refresh_models)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(edit_btn)
        btn_row.addWidget(toggle_btn)
        btn_row.addWidget(delete_btn)
        btn_row.addWidget(refresh_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.models_table = QTableWidget(0, 7)
        self.models_table.setHorizontalHeaderLabels(
            ["ID", "Название", "URL", "ID модели", "Переменная .env", "Провайдер", "Активна"]
        )
        self.models_table.setColumnHidden(0, True)
        self.models_table.setSortingEnabled(True)
        header = self.models_table.horizontalHeader()
        for col in (1, 2, 3, 4, 5):
            mode = QHeaderView.ResizeMode.Stretch if col == 2 else QHeaderView.ResizeMode.ResizeToContents
            header.setSectionResizeMode(col, mode)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.models_table)

        return widget

    def _build_settings_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        form = QFormLayout()
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(5, 600)
        self.timeout_spin.setSuffix(" сек")
        form.addRow("Таймаут запросов:", self.timeout_spin)

        self.db_path_edit = QLineEdit()
        form.addRow("Путь к БД:", self.db_path_edit)

        self.width_spin = QSpinBox()
        self.width_spin.setRange(640, 3840)
        form.addRow("Ширина окна:", self.width_spin)

        self.height_spin = QSpinBox()
        self.height_spin.setRange(480, 2160)
        form.addRow("Высота окна:", self.height_spin)

        appearance_group = QGroupBox("Внешний вид")
        appearance_layout = QFormLayout(appearance_group)
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Светлая", THEME_LIGHT)
        self.theme_combo.addItem("Тёмная", THEME_DARK)
        appearance_layout.addRow("Тема:", self.theme_combo)
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 24)
        self.font_size_spin.setSuffix(" pt")
        appearance_layout.addRow("Размер шрифта:", self.font_size_spin)

        assistant_group = QGroupBox("AI-ассистент промтов")
        assistant_layout = QFormLayout(assistant_group)
        self.assistant_enabled_check = QCheckBox("Использовать AI-ассистент")
        assistant_layout.addRow("", self.assistant_enabled_check)
        self.assistant_model_combo = QComboBox()
        assistant_layout.addRow("Модель ассистента:", self.assistant_model_combo)
        layout.addLayout(form)
        layout.addWidget(appearance_group)
        layout.addWidget(assistant_group)

        save_btn = QPushButton("Сохранить настройки")
        save_btn.clicked.connect(self._on_save_settings)
        layout.addWidget(save_btn)
        layout.addStretch()

        return widget

    def _build_logs_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        btn_row = QHBoxLayout()
        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self._refresh_logs)
        btn_row.addWidget(refresh_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.logs_table = QTableWidget(0, 6)
        self.logs_table.setHorizontalHeaderLabels(
            ["Дата", "Модель", "Статус", "мс", "Ошибка", "Prompt ID"]
        )
        self.logs_table.setSortingEnabled(True)
        header = self.logs_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.logs_table)

        return widget

    def _refresh_all(self) -> None:
        self._refresh_prompt_combo()
        self._refresh_results()
        self._refresh_history()
        self._refresh_models()
        self._refresh_settings()
        self._refresh_logs()
        self._update_improve_button_state()
        ready = len(self.model_manager.get_ready_active_models())
        active = len(self.model_manager.load_active())
        self.status_bar.showMessage(
            f"Готово. Активных моделей: {active}, с ключом: {ready}."
        )

    def _refresh_prompt_combo(self) -> None:
        self._updating_prompt_combo = True
        query = self.prompt_search.text().strip() if hasattr(self, "prompt_search") else ""
        prompts = (
            self.db.search_prompts(query) if query else self.db.list_prompts()
        )
        self.prompt_combo.clear()
        self.prompt_combo.addItem("— новый промт —", None)
        for prompt in prompts:
            label = prompt.text.replace("\n", " ")[:80]
            if prompt.tags:
                label += f" [{prompt.tags}]"
            self.prompt_combo.addItem(label, prompt.id)
        self._updating_prompt_combo = False

    def _filter_prompt_combo(self) -> None:
        self._refresh_prompt_combo()

    def _on_prompt_selected(self, index: int) -> None:
        if self._updating_prompt_combo or index < 0:
            return
        prompt_id = self.prompt_combo.itemData(index)
        if prompt_id is None:
            self._current_prompt_id = None
            return
        prompt = self.db.get_prompt(int(prompt_id))
        if prompt:
            self._current_prompt_id = prompt.id
            self.prompt_edit.setPlainText(prompt.text)
            self.tags_edit.setText(prompt.tags)

    def _refresh_results(self) -> None:
        self.results_table.blockSignals(True)
        self.results_table.setRowCount(0)
        for row in self.session.rows:
            idx = self.results_table.rowCount()
            self.results_table.insertRow(idx)

            check_item = QTableWidgetItem()
            check_item.setFlags(
                Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled
            )
            check_item.setCheckState(
                Qt.CheckState.Checked if row.selected else Qt.CheckState.Unchecked
            )
            self.results_table.setItem(idx, 0, check_item)
            self.results_table.setItem(idx, 1, QTableWidgetItem(row.model_name))

            response_item = QTableWidgetItem(row.response_text)
            response_item.setToolTip(row.response_text)
            self.results_table.setItem(idx, 2, response_item)

            open_btn = QPushButton("Открыть")
            open_btn.clicked.connect(
                lambda _checked=False, name=row.model_name, text=row.response_text: (
                    self._open_response(name, text)
                )
            )
            self.results_table.setCellWidget(idx, 3, open_btn)

        self.results_table.blockSignals(False)

    def _open_response(self, model_name: str, response_text: str) -> None:
        window = ResponseViewWindow(
            model_name=model_name,
            response_text=response_text,
            prompt_text=self.session.prompt_text,
            parent=self,
        )
        window.show()
        self._response_windows.append(window)
        window.destroyed.connect(
            lambda _obj=None, w=window: self._response_windows.remove(w)
            if w in self._response_windows
            else None
        )

    def _on_result_item_changed(self, item: QTableWidgetItem) -> None:
        if item.column() != 0:
            return
        row_index = item.row()
        selected = item.checkState() == Qt.CheckState.Checked
        if row_index < len(self.session.rows):
            self.session.set_selected(row_index, selected)

    def _set_all_selected(self, selected: bool) -> None:
        self.session.select_all(selected)
        self._refresh_results()

    def _refresh_history(self) -> None:
        query = self.history_search.text().strip().lower()
        prompts = {p.id: p for p in self.db.list_prompts()}
        models = {m.id: m for m in self.db.list_models()}

        self.history_table.setSortingEnabled(False)
        self.history_table.setRowCount(0)
        for result in self.db.list_results():
            prompt = prompts.get(result.prompt_id)
            model = models.get(result.model_id)
            prompt_text = prompt.text if prompt else f"#{result.prompt_id}"
            model_name = model.name if model else f"#{result.model_id}"
            haystack = f"{prompt_text} {model_name} {result.response_text}".lower()
            if query and query not in haystack:
                continue
            idx = self.history_table.rowCount()
            self.history_table.insertRow(idx)
            self.history_table.setItem(idx, 0, QTableWidgetItem(result.created_at))
            prompt_item = QTableWidgetItem(prompt_text.replace("\n", " ")[:120])
            prompt_item.setToolTip(prompt_text)
            self.history_table.setItem(idx, 1, prompt_item)
            self.history_table.setItem(idx, 2, QTableWidgetItem(model_name))
            response_item = QTableWidgetItem(result.response_text[:500])
            response_item.setToolTip(result.response_text)
            self.history_table.setItem(idx, 3, response_item)
            self.history_table.setItem(idx, 4, QTableWidgetItem(str(result.id)))
        self.history_table.setSortingEnabled(True)

    def _refresh_models(self) -> None:
        models = self.model_manager.load_all()
        self.models_table.setSortingEnabled(False)
        self.models_table.setRowCount(0)
        for model in models:
            idx = self.models_table.rowCount()
            self.models_table.insertRow(idx)
            has_key = "да" if self.model_manager.get_api_key(model) else "нет"
            active = "да" if model.is_active else "нет"
            self.models_table.setItem(idx, 0, QTableWidgetItem(str(model.id)))
            self.models_table.setItem(idx, 1, QTableWidgetItem(model.name))
            self.models_table.setItem(idx, 2, QTableWidgetItem(model.api_url))
            self.models_table.setItem(idx, 3, QTableWidgetItem(model.api_id))
            env_item = QTableWidgetItem(f"{model.api_key_env} ({has_key})")
            self.models_table.setItem(idx, 4, env_item)
            self.models_table.setItem(idx, 5, QTableWidgetItem(model.provider))
            self.models_table.setItem(idx, 6, QTableWidgetItem(active))
        self.models_table.setSortingEnabled(True)

    def _refresh_settings(self) -> None:
        self.timeout_spin.setValue(
            int(self.db.get_setting("request_timeout", "60") or "60")
        )
        self.db_path_edit.setText(self.db.get_setting("db_path", "data/chatlist.db") or "")
        self.width_spin.setValue(
            int(self.db.get_setting("window_width", "1200") or "1200")
        )
        self.height_spin.setValue(
            int(self.db.get_setting("window_height", "800") or "800")
        )
        theme = get_theme(self.db)
        theme_index = self.theme_combo.findData(theme)
        if theme_index >= 0:
            self.theme_combo.setCurrentIndex(theme_index)
        self.font_size_spin.setValue(get_font_size(self.db))
        self.assistant_enabled_check.setChecked(
            self.db.get_setting("assistant_enabled", "1") == "1"
        )
        self._refresh_assistant_model_combo()
        saved_id = self.db.get_setting("assistant_model_id", "") or ""
        if saved_id:
            index = self.assistant_model_combo.findData(int(saved_id))
            if index >= 0:
                self.assistant_model_combo.setCurrentIndex(index)
        elif self.assistant_model_combo.count() > 0:
            first_id = self.assistant_model_combo.itemData(0)
            if first_id is not None:
                self.db.set_setting("assistant_model_id", str(first_id))

    def _refresh_assistant_model_combo(self) -> None:
        self.assistant_model_combo.clear()
        chat_models = self.model_manager.get_chat_models(ready_only=True)
        if not chat_models:
            chat_models = self.model_manager.get_chat_models(ready_only=False)
        for model in chat_models:
            has_key = "✓" if self.model_manager.get_api_key(model) else "✗"
            self.assistant_model_combo.addItem(
                f"{model.name} ({has_key})",
                model.id,
            )
        if self.assistant_model_combo.count() == 0:
            self.assistant_model_combo.addItem("— нет доступных моделей —", None)

    def _get_assistant_model(self) -> AIModel | None:
        if self.db.get_setting("assistant_enabled", "1") != "1":
            return None
        saved_id = self.db.get_setting("assistant_model_id", "") or ""
        if saved_id:
            model = self.model_manager.get_by_id(int(saved_id))
            if model and self.model_manager.get_api_key(model):
                if model in self.model_manager.get_chat_models():
                    return model
        for model in self.model_manager.get_chat_models(ready_only=True):
            return model
        return None

    def _update_improve_button_state(self) -> None:
        enabled_setting = self.db.get_setting("assistant_enabled", "1") == "1"
        model = self._get_assistant_model()
        busy = (
            self._improve_worker is not None and self._improve_worker.isRunning()
        ) or (self._worker is not None and self._worker.isRunning())
        can_improve = enabled_setting and model is not None and not busy
        self.improve_btn.setEnabled(can_improve)
        if not enabled_setting:
            tip = "AI-ассистент отключён в настройках"
        elif model is None:
            tip = "Выберите модель ассистента с API-ключом в настройках"
        elif busy:
            tip = "Дождитесь завершения текущего запроса"
        else:
            tip = f"Улучшить промт через «{model.name}»"
        self.improve_btn.setToolTip(tip)

    def _refresh_logs(self) -> None:
        models = {m.id: m.name for m in self.model_manager.load_all()}
        logs = self.db.list_request_logs(limit=200)
        self.logs_table.setSortingEnabled(False)
        self.logs_table.setRowCount(0)
        for log in logs:
            idx = self.logs_table.rowCount()
            self.logs_table.insertRow(idx)
            self.logs_table.setItem(idx, 0, QTableWidgetItem(log.created_at))
            self.logs_table.setItem(
                idx, 1, QTableWidgetItem(models.get(log.model_id, f"#{log.model_id}"))
            )
            self.logs_table.setItem(idx, 2, QTableWidgetItem(log.status))
            ms = str(log.duration_ms) if log.duration_ms is not None else ""
            self.logs_table.setItem(idx, 3, QTableWidgetItem(ms))
            err_item = QTableWidgetItem(log.error_message or "")
            self.logs_table.setItem(idx, 4, err_item)
            pid = str(log.prompt_id) if log.prompt_id is not None else ""
            self.logs_table.setItem(idx, 5, QTableWidgetItem(pid))
        self.logs_table.setSortingEnabled(True)

    def _resolve_prompt(self, text: str, tags: str) -> tuple[int, Prompt]:
        if self._current_prompt_id is not None:
            existing = self.db.get_prompt(self._current_prompt_id)
            if existing and existing.text == text:
                if tags != existing.tags:
                    updated = self.db.update_prompt(existing.id, text, tags)
                    if updated:
                        return updated.id, updated
                return existing.id, existing

        prompt = self.db.create_prompt(text, tags)
        self._current_prompt_id = prompt.id
        return prompt.id, prompt

    def _on_send(self) -> None:
        if self._worker and self._worker.isRunning():
            return

        text = self.prompt_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Запрос", "Введите текст промта.")
            return

        errors = self.model_manager.validate_active_models()
        if errors:
            QMessageBox.warning(
                self,
                "Модели",
                "\n".join(str(e) for e in errors),
            )
            return

        ready = self.model_manager.get_ready_active_models()
        if not ready:
            QMessageBox.warning(
                self,
                "Модели",
                "Нет активных моделей с API-ключом. Проверьте вкладку «Модели» и .env.",
            )
            return

        tags = self.tags_edit.text().strip()
        prompt_id, _ = self._resolve_prompt(text, tags)

        self.session.clear()
        self.session.set_prompt(text, prompt_id)
        self._refresh_results()
        self._refresh_prompt_combo()

        self.send_btn.setEnabled(False)
        self.improve_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(len(ready))
        self.status_bar.showMessage("Отправка запросов...")

        self._worker = SendPromptWorker(
            self.network, ready, text, prompt_id
        )
        self._worker.progress.connect(self._on_send_progress)
        self._worker.result_ready.connect(self._on_result_ready)
        self._worker.finished_all.connect(self._on_send_finished)
        self._worker.failed.connect(self._on_send_failed)
        self._worker.start()

    def _on_improve_prompt(self) -> None:
        if self._improve_worker and self._improve_worker.isRunning():
            return
        if self._worker and self._worker.isRunning():
            return

        text = self.prompt_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "AI-ассистент", "Введите текст промта.")
            return

        model = self._get_assistant_model()
        if model is None:
            QMessageBox.warning(
                self,
                "AI-ассистент",
                "Модель ассистента не выбрана или отсутствует API-ключ.",
            )
            return

        self._assistant_model = model
        self.improve_btn.setEnabled(False)
        self.send_btn.setEnabled(False)
        self.status_bar.showMessage(f"Улучшение промта через «{model.name}»...")

        self._improve_worker = ImprovePromptWorker(
            self._prompt_assistant,
            self.network,
            model,
            text,
        )
        self._improve_worker.finished.connect(self._on_improve_finished)
        self._improve_worker.failed.connect(self._on_improve_failed)
        self._improve_worker.start()

    def _on_improve_finished(self, result: PromptImprovementResult) -> None:
        self.send_btn.setEnabled(True)
        self._update_improve_button_state()
        if self._assistant_model:
            self.db.create_request_log(
                model_id=self._assistant_model.id,
                prompt_id=None,
                status="success",
                duration_ms=None,
                error_message="prompt_assistant",
            )
            self._refresh_logs()
        self.status_bar.showMessage("Промт улучшен. Выберите вариант для подстановки.")
        dialog = PromptAssistantDialog(result, parent=self)
        dialog.apply_requested.connect(self._apply_improved_prompt)
        dialog.exec()

    def _on_improve_failed(self, message: str) -> None:
        self.send_btn.setEnabled(True)
        self._update_improve_button_state()
        if self._assistant_model:
            self.db.create_request_log(
                model_id=self._assistant_model.id,
                prompt_id=None,
                status="error",
                duration_ms=None,
                error_message=f"prompt_assistant: {message[:200]}",
            )
            self._refresh_logs()
        QMessageBox.warning(self, "AI-ассистент", message)
        self.status_bar.showMessage(message)

    def _apply_improved_prompt(self, text: str) -> None:
        self.prompt_edit.setPlainText(text)
        self._current_prompt_id = None
        self.status_bar.showMessage("Выбранный вариант подставлен в поле ввода.")

    def _on_send_progress(self, model_name: str, current: int, total: int) -> None:
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.status_bar.showMessage(f"Ответ от «{model_name}» ({current}/{total})")

    def _on_result_ready(self, model_id: int, model_name: str, response: str) -> None:
        self.session.add_result(model_id, model_name, response)
        self._refresh_results()

    def _on_send_finished(self) -> None:
        self.send_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self._update_improve_button_state()
        self._refresh_logs()
        self.tabs.setCurrentIndex(1)
        self.status_bar.showMessage(
            f"Получено ответов: {len(self.session.rows)}. Выберите строки для сохранения."
        )

    def _on_send_failed(self, message: str) -> None:
        self.send_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self._update_improve_button_state()
        QMessageBox.warning(self, "Отправка", message)
        self.status_bar.showMessage(message)

    def _on_save_results(self) -> None:
        selected = self.session.get_selected()
        if not selected:
            QMessageBox.information(self, "Сохранение", "Не выбрано ни одной строки.")
            return
        if self.session.prompt_id is None or self.session.prompt_text is None:
            QMessageBox.warning(self, "Сохранение", "Нет привязанного промта.")
            return

        items = [(row.model_id, row.response_text) for row in selected]
        self.db.create_results_batch(self.session.prompt_id, items)
        self.session.clear()
        self._refresh_results()
        self._refresh_history()
        self.status_bar.showMessage(f"Сохранено результатов: {len(items)}.")
        QMessageBox.information(self, "Сохранение", f"Сохранено строк: {len(items)}.")

    def _selected_model_id(self) -> int | None:
        row = self.models_table.currentRow()
        if row < 0:
            return None
        item = self.models_table.item(row, 0)
        return int(item.text()) if item else None

    def _on_add_model(self) -> None:
        dialog = ModelDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        values = dialog.values()
        if not all([values["name"], values["api_url"], values["api_id"], values["api_key_env"]]):
            QMessageBox.warning(self, "Модель", "Заполните все обязательные поля.")
            return
        try:
            if values["is_active"]:
                temp = AIModel(
                    id=0,
                    name=str(values["name"]),
                    api_url=str(values["api_url"]),
                    api_id=str(values["api_id"]),
                    api_key_env=str(values["api_key_env"]),
                    provider=str(values["provider"]),
                    is_active=True,
                )
                self.model_manager.validate_model(temp)
            self.db.create_model(
                name=str(values["name"]),
                api_url=str(values["api_url"]),
                api_id=str(values["api_id"]),
                api_key_env=str(values["api_key_env"]),
                provider=str(values["provider"]),
                is_active=bool(values["is_active"]),
            )
        except ModelValidationError as exc:
            QMessageBox.warning(self, "Модель", str(exc))
            return
        self._refresh_models()
        self._refresh_all()

    def _on_edit_model(self) -> None:
        model_id = self._selected_model_id()
        if model_id is None:
            QMessageBox.information(self, "Модель", "Выберите модель в таблице.")
            return
        model = self.model_manager.get_by_id(model_id)
        if not model:
            return
        dialog = ModelDialog(self, model)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        values = dialog.values()
        try:
            if values["is_active"]:
                temp = AIModel(
                    id=model.id,
                    name=str(values["name"]),
                    api_url=str(values["api_url"]),
                    api_id=str(values["api_id"]),
                    api_key_env=str(values["api_key_env"]),
                    provider=str(values["provider"]),
                    is_active=True,
                )
                self.model_manager.validate_model(temp)
            self.db.update_model(
                model.id,
                str(values["name"]),
                str(values["api_url"]),
                str(values["api_id"]),
                str(values["api_key_env"]),
                str(values["provider"]),
                bool(values["is_active"]),
            )
        except ModelValidationError as exc:
            QMessageBox.warning(self, "Модель", str(exc))
            return
        self._refresh_models()
        self._refresh_all()

    def _on_toggle_model(self) -> None:
        model_id = self._selected_model_id()
        if model_id is None:
            return
        model = self.model_manager.get_by_id(model_id)
        if not model:
            return
        new_active = not model.is_active
        if new_active:
            try:
                self.model_manager.validate_model(
                    AIModel(
                        id=model.id,
                        name=model.name,
                        api_url=model.api_url,
                        api_id=model.api_id,
                        api_key_env=model.api_key_env,
                        provider=model.provider,
                        is_active=True,
                    )
                )
            except ModelValidationError as exc:
                QMessageBox.warning(self, "Модель", str(exc))
                return
        self.db.set_model_active(model_id, new_active)
        self._refresh_models()
        self._refresh_all()

    def _on_delete_model(self) -> None:
        model_id = self._selected_model_id()
        if model_id is None:
            return
        reply = QMessageBox.question(
            self,
            "Удаление",
            "Удалить модель? Если есть сохранённые результаты, операция может быть отклонена.",
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            if not self.db.delete_model(model_id):
                QMessageBox.warning(self, "Удаление", "Модель не найдена.")
                return
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Удаление",
                f"Не удалось удалить модель: {exc}\nРекомендуется деактивировать модель.",
            )
            return
        self._refresh_models()
        self._refresh_all()

    def _on_save_settings(self) -> None:
        self.db.set_setting("request_timeout", str(self.timeout_spin.value()))
        self.db.set_setting("db_path", self.db_path_edit.text().strip())
        self.db.set_setting("window_width", str(self.width_spin.value()))
        self.db.set_setting("window_height", str(self.height_spin.value()))
        self.db.set_setting("theme", self.theme_combo.currentData())
        self.db.set_setting("font_size", str(self.font_size_spin.value()))
        self.db.set_setting(
            "assistant_enabled",
            "1" if self.assistant_enabled_check.isChecked() else "0",
        )
        model_id = self.assistant_model_combo.currentData()
        self.db.set_setting(
            "assistant_model_id",
            str(model_id) if model_id is not None else "",
        )
        self.network.timeout = float(self.timeout_spin.value())
        self.resize(self.width_spin.value(), self.height_spin.value())

        app = QApplication.instance()
        if isinstance(app, QApplication):
            apply_appearance(app, self.db)

        QMessageBox.information(self, "Настройки", "Настройки сохранены.")
        self._refresh_all()

    def _show_about(self) -> None:
        AboutDialog(self).exec()

    def _export_results(self, fmt: str) -> None:
        rows = self.session.get_selected() or self.session.rows
        if not rows:
            QMessageBox.information(self, "Экспорт", "Нет результатов для экспорта.")
            return
        prompt_text = self.session.prompt_text or ""
        path = ""
        if fmt == "md":
            path, _ = QFileDialog.getSaveFileName(
                self, "Экспорт Markdown", "results.md", "Markdown (*.md)"
            )
            if path:
                export_markdown(prompt_text, rows, Path(path))
        else:
            path, _ = QFileDialog.getSaveFileName(
                self, "Экспорт JSON", "results.json", "JSON (*.json)"
            )
            if path:
                export_json(prompt_text, self.session.prompt_id, rows, Path(path))
        if path:
            self.status_bar.showMessage(f"Экспортировано в {path}")

    def closeEvent(self, event) -> None:
        self.db.set_setting("window_width", str(self.width()))
        self.db.set_setting("window_height", str(self.height()))
        if self._worker and self._worker.isRunning():
            self._worker.wait(3000)
        if self._improve_worker and self._improve_worker.isRunning():
            self._improve_worker.wait(3000)
        super().closeEvent(event)
