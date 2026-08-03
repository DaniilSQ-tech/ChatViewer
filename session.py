"""Временная таблица результатов текущего запроса (в памяти)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SessionRow:
    model_id: int
    model_name: str
    response_text: str
    selected: bool = False


class SessionResults:
    """Хранит результаты текущей сессии до нажатия «Сохранить»."""

    def __init__(self) -> None:
        self.prompt_text: str | None = None
        self.prompt_id: int | None = None
        self._rows: list[SessionRow] = []

    @property
    def rows(self) -> list[SessionRow]:
        return list(self._rows)

    def __len__(self) -> int:
        return len(self._rows)

    def is_empty(self) -> bool:
        return len(self._rows) == 0

    def set_prompt(self, text: str, prompt_id: int | None = None) -> None:
        self.prompt_text = text
        self.prompt_id = prompt_id

    def clear(self) -> None:
        self.prompt_text = None
        self.prompt_id = None
        self._rows.clear()

    def add_result(
        self,
        model_id: int,
        model_name: str,
        response_text: str,
        selected: bool = False,
    ) -> None:
        self._rows.append(
            SessionRow(
                model_id=model_id,
                model_name=model_name,
                response_text=response_text,
                selected=selected,
            )
        )

    def get_selected(self) -> list[SessionRow]:
        return [row for row in self._rows if row.selected]

    def set_selected(self, row_index: int, selected: bool) -> None:
        if row_index < 0 or row_index >= len(self._rows):
            raise IndexError(f"Индекс строки вне диапазона: {row_index}")
        self._rows[row_index].selected = selected

    def toggle_selected(self, row_index: int) -> bool:
        if row_index < 0 or row_index >= len(self._rows):
            raise IndexError(f"Индекс строки вне диапазона: {row_index}")
        self._rows[row_index].selected = not self._rows[row_index].selected
        return self._rows[row_index].selected

    def select_all(self, selected: bool = True) -> None:
        for row in self._rows:
            row.selected = selected

    def get_row(self, row_index: int) -> SessionRow:
        if row_index < 0 or row_index >= len(self._rows):
            raise IndexError(f"Индекс строки вне диапазона: {row_index}")
        return self._rows[row_index]
