"""Фоновые задачи для GUI."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import partial

from PyQt6.QtCore import QThread, pyqtSignal

from models import AIModel
from network import NetworkClient


class SendPromptWorker(QThread):
    """Отправляет промт во все активные модели в фоновом потоке."""

    progress = pyqtSignal(str, int, int)
    result_ready = pyqtSignal(int, str, str)
    finished_all = pyqtSignal()
    failed = pyqtSignal(str)

    def __init__(
        self,
        network: NetworkClient,
        models: list[AIModel],
        prompt_text: str,
        prompt_id: int | None,
    ) -> None:
        super().__init__()
        self._network = network
        self._models = models
        self._prompt_text = prompt_text
        self._prompt_id = prompt_id

    def run(self) -> None:
        if not self._models:
            self.failed.emit("Нет активных моделей с API-ключом в .env")
            return

        total = len(self._models)
        completed = 0

        send = partial(
            self._network.send_prompt,
            prompt_text=self._prompt_text,
            prompt_id=self._prompt_id,
            log_requests=False,
        )

        with ThreadPoolExecutor(max_workers=min(total, 4)) as executor:
            futures = {
                executor.submit(send, model): model for model in self._models
            }
            for future in as_completed(futures):
                model = futures[future]
                try:
                    response = future.result()
                except Exception as exc:
                    response = f"Неожиданная ошибка: {exc}"
                completed += 1
                self.progress.emit(model.name, completed, total)
                self.result_ready.emit(model.id, model.name, response)

        self.finished_all.emit()
