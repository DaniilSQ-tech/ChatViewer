"""Логика работы с нейросетями (моделями API)."""

from __future__ import annotations

import os
from dataclasses import dataclass

from db import Database, ModelRecord

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODELS_CATALOG_VERSION = "free_openrouter_v2"

# Модели, которые не поддерживают chat/completions (TTS, rerank и т.д.)
NON_CHAT_API_IDS = frozenset(
    {
        "fish-audio/s2.1-pro-free:free",
        "voyageai/rerank-2.5-lite",
    }
)

DEFAULT_MODELS: list[dict[str, str | bool]] = [
    {
        "name": "Fish Audio: S2.1 Pro Free",
        "api_url": OPENROUTER_API_URL,
        "api_id": "fish-audio/s2.1-pro-free:free",
        "api_key_env": "OPENROUTER_API_KEY",
        "provider": "openrouter",
        "is_active": False,
    },
    {
        "name": "VoyageAI: rerank-2.5-lite",
        "api_url": OPENROUTER_API_URL,
        "api_id": "voyageai/rerank-2.5-lite",
        "api_key_env": "OPENROUTER_API_KEY",
        "provider": "openrouter",
        "is_active": False,
    },
    {
        "name": "Ling-3.0-flash (free)",
        "api_url": OPENROUTER_API_URL,
        "api_id": "inclusionai/ling-3.0-flash:free",
        "api_key_env": "OPENROUTER_API_KEY",
        "provider": "openrouter",
        "is_active": False,
    },
    {
        "name": "Poolside: Laguna XS 2.1 (free)",
        "api_url": OPENROUTER_API_URL,
        "api_id": "poolside/laguna-xs-2.1:free",
        "api_key_env": "OPENROUTER_API_KEY",
        "provider": "openrouter",
        "is_active": False,
    },
    {
        "name": "Cohere: North Mini Code (free)",
        "api_url": OPENROUTER_API_URL,
        "api_id": "cohere/north-mini-code:free",
        "api_key_env": "OPENROUTER_API_KEY",
        "provider": "openrouter",
        "is_active": False,
    },
]


@dataclass
class AIModel:
    id: int
    name: str
    api_url: str
    api_id: str
    api_key_env: str
    provider: str
    is_active: bool

    @classmethod
    def from_record(cls, record: ModelRecord) -> AIModel:
        return cls(
            id=record.id,
            name=record.name,
            api_url=record.api_url,
            api_id=record.api_id,
            api_key_env=record.api_key_env,
            provider=record.provider,
            is_active=record.is_active,
        )


class ModelValidationError(Exception):
    """Ошибка валидации модели (например, отсутствует API-ключ)."""


class ModelManager:
    def __init__(self, database: Database) -> None:
        self._db = database

    def load_all(self) -> list[AIModel]:
        return [AIModel.from_record(r) for r in self._db.list_models()]

    def load_active(self) -> list[AIModel]:
        return [AIModel.from_record(r) for r in self._db.list_models(active_only=True)]

    def get_by_id(self, model_id: int) -> AIModel | None:
        record = self._db.get_model(model_id)
        return AIModel.from_record(record) if record else None

    @staticmethod
    def get_api_key(model: AIModel) -> str | None:
        value = os.environ.get(model.api_key_env, "").strip()
        return value or None

    def validate_model(self, model: AIModel) -> None:
        if not model.is_active:
            return
        if not self.get_api_key(model):
            raise ModelValidationError(
                f"Модель «{model.name}» активна, но переменная "
                f"{model.api_key_env} не задана в .env"
            )

    def validate_active_models(self) -> list[ModelValidationError]:
        errors: list[ModelValidationError] = []
        for model in self.load_active():
            try:
                self.validate_model(model)
            except ModelValidationError as exc:
                errors.append(exc)
        return errors

    def get_ready_active_models(self) -> list[AIModel]:
        """Активные модели с заполненным API-ключом."""
        ready: list[AIModel] = []
        for model in self.load_active():
            if self.get_api_key(model):
                ready.append(model)
        return ready

    def _insert_default_models(self) -> int:
        for item in DEFAULT_MODELS:
            self._db.create_model(
                name=str(item["name"]),
                api_url=str(item["api_url"]),
                api_id=str(item["api_id"]),
                api_key_env=str(item["api_key_env"]),
                provider=str(item["provider"]),
                is_active=bool(item["is_active"]),
            )
        return len(DEFAULT_MODELS)

    def apply_models_catalog(self) -> int:
        """Синхронизирует таблицу models с актуальным каталогом DEFAULT_MODELS."""
        current = self._db.get_setting("models_catalog_version")
        if current == MODELS_CATALOG_VERSION and self._db.count_models() > 0:
            return 0

        self._db.clear_all_models()
        count = self._insert_default_models()
        self._deactivate_non_chat_models()
        self._db.set_setting("models_catalog_version", MODELS_CATALOG_VERSION)
        return count

    def _deactivate_non_chat_models(self) -> None:
        for model in self.load_all():
            if model.api_id in NON_CHAT_API_IDS:
                self._db.set_model_active(model.id, False)

    def seed_defaults(self) -> int:
        """Добавляет или обновляет набор моделей по умолчанию."""
        return self.apply_models_catalog()

    def ensure_default_models(self) -> int:
        """Добавляет отсутствующие модели из DEFAULT_MODELS (миграция)."""
        return self.apply_models_catalog()

    def activate_if_key_present(self, model: AIModel) -> AIModel | None:
        """Активирует модель, если ключ найден в окружении."""
        if self.get_api_key(model):
            record = self._db.set_model_active(model.id, True)
            return AIModel.from_record(record) if record else None
        return None

    def get_chat_models(self, ready_only: bool = False) -> list[AIModel]:
        if ready_only:
            models = self.get_ready_active_models()
        else:
            models = self.load_all()
        return [model for model in models if model.api_id not in NON_CHAT_API_IDS]

    def sync_activation_from_env(self) -> int:
        """Активирует chat-модели, для которых есть ключ в .env."""
        activated = 0
        for model in self.load_all():
            if model.api_id in NON_CHAT_API_IDS:
                continue
            if not model.is_active and self.get_api_key(model):
                if self._db.set_model_active(model.id, True):
                    activated += 1
        return activated
