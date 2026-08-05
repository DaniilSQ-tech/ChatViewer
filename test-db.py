"""Тестовая утилита для просмотра и редактирования SQLite-баз."""

from __future__ import annotations

import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


@dataclass
class ColumnInfo:
    name: str
    type: str
    notnull: bool
    default: str | None
    pk: int


class SqliteReader:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row

    def close(self) -> None:
        self._conn.close()

    def list_tables(self) -> list[str]:
        rows = self._conn.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()
        return [row["name"] for row in rows]

    def get_columns(self, table: str) -> list[ColumnInfo]:
        rows = self._conn.execute(f"PRAGMA table_info({self._quote(table)})").fetchall()
        return [
            ColumnInfo(
                name=row["name"],
                type=row["type"],
                notnull=bool(row["notnull"]),
                default=row["dflt_value"],
                pk=int(row["pk"]),
            )
            for row in rows
        ]

    def count_rows(self, table: str) -> int:
        row = self._conn.execute(
            f"SELECT COUNT(*) AS cnt FROM {self._quote(table)}"
        ).fetchone()
        return int(row["cnt"]) if row else 0

    def fetch_page(
        self, table: str, limit: int, offset: int
    ) -> tuple[list[str], list[dict[str, Any]]]:
        columns = [col.name for col in self.get_columns(table)]
        rows = self._conn.execute(
            f"SELECT rowid AS __rowid__, * FROM {self._quote(table)} "
            f"LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        data = [dict(row) for row in rows]
        return columns, data

    def insert_row(self, table: str, values: dict[str, Any]) -> None:
        columns = self.get_columns(table)
        editable = [col for col in columns if col.pk == 0 or not self._is_autoincrement(col)]
        names = [col.name for col in editable if col.name in values]
        if not names:
            raise ValueError("Нет данных для вставки")
        placeholders = ", ".join("?" for _ in names)
        cols_sql = ", ".join(self._quote(name) for name in names)
        params = [values[name] for name in names]
        self._conn.execute(
            f"INSERT INTO {self._quote(table)} ({cols_sql}) VALUES ({placeholders})",
            params,
        )
        self._conn.commit()

    def update_row(
        self,
        table: str,
        rowid: int,
        values: dict[str, Any],
    ) -> None:
        columns = self.get_columns(table)
        pk_names = {col.name for col in columns if col.pk}
        set_parts: list[str] = []
        params: list[Any] = []
        for col in columns:
            if col.name not in values:
                continue
            if col.name in pk_names and self._is_autoincrement(col):
                continue
            set_parts.append(f"{self._quote(col.name)} = ?")
            params.append(values[col.name])
        if not set_parts:
            return
        params.append(rowid)
        self._conn.execute(
            f"UPDATE {self._quote(table)} SET {', '.join(set_parts)} WHERE rowid = ?",
            params,
        )
        self._conn.commit()

    def delete_row(self, table: str, rowid: int) -> None:
        self._conn.execute(
            f"DELETE FROM {self._quote(table)} WHERE rowid = ?",
            (rowid,),
        )
        self._conn.commit()

    @staticmethod
    def _quote(identifier: str) -> str:
        return '"' + identifier.replace('"', '""') + '"'

    @staticmethod
    def _is_autoincrement(column: ColumnInfo) -> bool:
        return column.pk > 0 and column.type.upper() == "INTEGER"


class RowDialog(QDialog):
    def __init__(
        self,
        columns: list[ColumnInfo],
        title: str,
        initial: dict[str, Any] | None = None,
        edit_mode: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self._columns = columns
        self._fields: dict[str, QLineEdit] = {}
        initial = initial or {}

        form = QFormLayout()
        for col in columns:
            if edit_mode and col.pk > 0 and SqliteReader._is_autoincrement(col):
                continue
            field = QLineEdit()
            value = initial.get(col.name)
            if value is not None:
                field.setText(str(value))
            if col.notnull and not col.default:
                field.setPlaceholderText("обязательное поле")
            form.addRow(f"{col.name} ({col.type}):", field)
            self._fields[col.name] = field

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def values(self, columns: list[ColumnInfo]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for col in columns:
            if col.name not in self._fields:
                continue
            raw = self._fields[col.name].text().strip()
            if raw == "":
                result[col.name] = None
            elif col.type.upper() in {"INTEGER", "INT"}:
                result[col.name] = int(raw)
            elif col.type.upper() in {"REAL", "FLOAT", "DOUBLE"}:
                result[col.name] = float(raw)
            else:
                result[col.name] = raw
        return result


class TableWindow(QMainWindow):
    def __init__(
        self,
        reader: SqliteReader,
        table_name: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.reader = reader
        self.table_name = table_name
        self.columns = reader.get_columns(table_name)
        self.current_page = 0
        self.page_size = 25
        self.total_rows = reader.count_rows(table_name)

        self.setWindowTitle(f"Таблица: {table_name}")
        self.setMinimumSize(900, 550)
        self.resize(1000, 600)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.info_label = QLabel()
        layout.addWidget(self.info_label)

        self.table = QTableWidget(0, 0)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        pagination = QHBoxLayout()
        self.prev_btn = QPushButton("← Назад")
        self.prev_btn.clicked.connect(self._prev_page)
        self.next_btn = QPushButton("Вперёд →")
        self.next_btn.clicked.connect(self._next_page)
        self.page_label = QLabel()
        pagination.addWidget(self.prev_btn)
        pagination.addWidget(self.next_btn)
        pagination.addWidget(self.page_label)
        pagination.addStretch()
        pagination.addWidget(QLabel("Строк на странице:"))
        self.page_size_spin = QSpinBox()
        self.page_size_spin.setRange(5, 500)
        self.page_size_spin.setValue(self.page_size)
        self.page_size_spin.valueChanged.connect(self._on_page_size_changed)
        pagination.addWidget(self.page_size_spin)
        layout.addLayout(pagination)

        crud = QHBoxLayout()
        self.add_btn = QPushButton("Добавить")
        self.add_btn.clicked.connect(self._add_row)
        self.edit_btn = QPushButton("Изменить")
        self.edit_btn.clicked.connect(self._edit_row)
        self.delete_btn = QPushButton("Удалить")
        self.delete_btn.clicked.connect(self._delete_row)
        self.refresh_btn = QPushButton("Обновить")
        self.refresh_btn.clicked.connect(self._reload)
        crud.addWidget(self.add_btn)
        crud.addWidget(self.edit_btn)
        crud.addWidget(self.delete_btn)
        crud.addWidget(self.refresh_btn)
        crud.addStretch()
        layout.addLayout(crud)

        self._rowids: list[int] = []
        self._load_page()

    def _total_pages(self) -> int:
        if self.total_rows == 0:
            return 1
        return (self.total_rows + self.page_size - 1) // self.page_size

    def _load_page(self) -> None:
        offset = self.current_page * self.page_size
        column_names, rows = self.reader.fetch_page(
            self.table_name, self.page_size, offset
        )
        display_columns = [name for name in column_names if name != "__rowid__"]

        self.table.setColumnCount(len(display_columns))
        self.table.setHorizontalHeaderLabels(display_columns)
        self.table.setRowCount(len(rows))
        self._rowids.clear()

        for row_idx, row in enumerate(rows):
            self._rowids.append(int(row["__rowid__"]))
            for col_idx, name in enumerate(display_columns):
                value = row.get(name)
                text = "" if value is None else str(value)
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row_idx, col_idx, item)

        page_num = self.current_page + 1
        total_pages = self._total_pages()
        self.page_label.setText(f"Страница {page_num} из {total_pages}")
        self.info_label.setText(
            f"Таблица «{self.table_name}»: всего строк {self.total_rows}"
        )
        self.prev_btn.setEnabled(self.current_page > 0)
        self.next_btn.setEnabled(self.current_page < total_pages - 1)

    def _reload(self) -> None:
        self.total_rows = self.reader.count_rows(self.table_name)
        if self.current_page >= self._total_pages():
            self.current_page = max(0, self._total_pages() - 1)
        self._load_page()

    def _prev_page(self) -> None:
        if self.current_page > 0:
            self.current_page -= 1
            self._load_page()

    def _next_page(self) -> None:
        if self.current_page < self._total_pages() - 1:
            self.current_page += 1
            self._load_page()

    def _on_page_size_changed(self, value: int) -> None:
        self.page_size = value
        self.current_page = 0
        self._reload()

    def _selected_rowid(self) -> int | None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._rowids):
            return None
        return self._rowids[row]

    def _selected_row_data(self) -> dict[str, Any]:
        row = self.table.currentRow()
        if row < 0:
            return {}
        data: dict[str, Any] = {}
        for col in range(self.table.columnCount()):
            header = self.table.horizontalHeaderItem(col)
            name = header.text() if header else f"col{col}"
            item = self.table.item(row, col)
            data[name] = item.text() if item else ""
        return data

    def _add_row(self) -> None:
        dialog = RowDialog(self.columns, f"Добавить — {self.table_name}", parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            values = dialog.values(self.columns)
            self.reader.insert_row(self.table_name, values)
        except Exception as exc:
            QMessageBox.warning(self, "Ошибка", f"Не удалось добавить строку:\n{exc}")
            return
        self._reload()

    def _edit_row(self) -> None:
        rowid = self._selected_rowid()
        if rowid is None:
            QMessageBox.information(self, "Изменение", "Выберите строку в таблице.")
            return
        initial = self._selected_row_data()
        dialog = RowDialog(
            self.columns,
            f"Изменить — {self.table_name}",
            initial=initial,
            edit_mode=True,
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            values = dialog.values(self.columns)
            self.reader.update_row(self.table_name, rowid, values)
        except Exception as exc:
            QMessageBox.warning(self, "Ошибка", f"Не удалось изменить строку:\n{exc}")
            return
        self._reload()

    def _delete_row(self) -> None:
        rowid = self._selected_rowid()
        if rowid is None:
            QMessageBox.information(self, "Удаление", "Выберите строку в таблице.")
            return
        reply = QMessageBox.question(
            self,
            "Удаление",
            f"Удалить строку rowid={rowid}?",
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            self.reader.delete_row(self.table_name, rowid)
        except Exception as exc:
            QMessageBox.warning(self, "Ошибка", f"Не удалось удалить строку:\n{exc}")
            return
        self._reload()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SQLite Explorer — test-db")
        self.setMinimumSize(480, 400)
        self.resize(520, 450)

        self.reader: SqliteReader | None = None
        self._table_windows: list[TableWindow] = []

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        file_group = QGroupBox("Файл базы данных")
        file_layout = QHBoxLayout(file_group)
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Выберите файл .db / .sqlite ...")
        browse_btn = QPushButton("Обзор...")
        browse_btn.clicked.connect(self._browse_db)
        file_layout.addWidget(self.path_edit)
        file_layout.addWidget(browse_btn)
        layout.addWidget(file_group)

        layout.addWidget(QLabel("Таблицы:"))
        self.tables_list = QListWidget()
        self.tables_list.itemDoubleClicked.connect(lambda _: self._open_table())
        layout.addWidget(self.tables_list)

        btn_row = QHBoxLayout()
        self.open_btn = QPushButton("Открыть")
        self.open_btn.clicked.connect(self._open_table)
        self.open_btn.setEnabled(False)
        refresh_btn = QPushButton("Обновить список")
        refresh_btn.clicked.connect(self._load_tables)
        btn_row.addWidget(self.open_btn)
        btn_row.addWidget(refresh_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        default_db = Path("data/chatlist.db")
        if default_db.exists():
            self.path_edit.setText(str(default_db))
            self._connect_db(default_db)

    def _browse_db(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите SQLite-базу",
            str(Path.cwd()),
            "SQLite (*.db *.sqlite *.sqlite3);;Все файлы (*.*)",
        )
        if path:
            self.path_edit.setText(path)
            self._connect_db(Path(path))

    def _connect_db(self, path: Path) -> None:
        if self.reader:
            self.reader.close()
            self.reader = None
        if not path.exists():
            QMessageBox.warning(self, "Ошибка", f"Файл не найден:\n{path}")
            return
        try:
            self.reader = SqliteReader(path)
        except Exception as exc:
            QMessageBox.warning(self, "Ошибка", f"Не удалось открыть базу:\n{exc}")
            return
        self._load_tables()

    def _load_tables(self) -> None:
        self.tables_list.clear()
        path_text = self.path_edit.text().strip()
        if not path_text:
            self.open_btn.setEnabled(False)
            return
        if self.reader is None:
            self._connect_db(Path(path_text))
            if self.reader is None:
                return
        try:
            tables = self.reader.list_tables()
        except Exception as exc:
            QMessageBox.warning(self, "Ошибка", f"Не удалось прочитать таблицы:\n{exc}")
            return
        self.tables_list.addItems(tables)
        self.open_btn.setEnabled(bool(tables))
        self.setWindowTitle(f"SQLite Explorer — {Path(path_text).name}")

    def _open_table(self) -> None:
        if self.reader is None:
            return
        item = self.tables_list.currentItem()
        if item is None:
            QMessageBox.information(self, "Открыть", "Выберите таблицу из списка.")
            return
        table_name = item.text()
        window = TableWindow(self.reader, table_name, parent=self)
        window.show()
        self._table_windows.append(window)
        window.destroyed.connect(
            lambda _obj=None, w=window: self._table_windows.remove(w)
            if w in self._table_windows
            else None
        )

    def closeEvent(self, event) -> None:
        if self.reader:
            self.reader.close()
        super().closeEvent(event)


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("test-db")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
