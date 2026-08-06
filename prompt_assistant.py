"""AI-ассистент для улучшения промтов."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from models import AIModel
from network import NetworkClient

ASSISTANT_SYSTEM_PROMPT = """Ты — эксперт по составлению промтов для LLM.
Пользователь присылает исходный промт. Твоя задача:
1. Улучшить промт: сделать его яснее, конкретнее и структурированнее.
2. Предложить 2–3 альтернативные переформулировки с тем же смыслом.
3. Адаптировать промт под три типа задач: code (код), analysis (анализ), creative (креатив).

Сохраняй язык исходного промта (если русский — отвечай по-русски).
Верни ответ СТРОГО как JSON без пояснений и markdown-обёртки:
{
  "improved": "улучшенная версия",
  "alternatives": ["вариант 1", "вариант 2", "вариант 3"],
  "adaptations": {
    "code": "версия для задач программирования",
    "analysis": "версия для аналитических задач",
    "creative": "версия для креативных задач"
  }
}"""


@dataclass
class PromptImprovementResult:
    original: str
    improved: str = ""
    alternatives: list[str] = field(default_factory=list)
    adaptations: dict[str, str] = field(default_factory=dict)
    error: str | None = None
    raw_response: str | None = None


class PromptAssistantError(Exception):
    """Ошибка работы ассистента."""


def _extract_json(text: str) -> dict:
    stripped = text.strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    block_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, re.DOTALL)
    if block_match:
        return json.loads(block_match.group(1))

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end > start:
        return json.loads(stripped[start : end + 1])

    raise ValueError("Не удалось извлечь JSON из ответа модели")


def _looks_like_error(response: str) -> bool:
    markers = (
        "Ошибка",
        "API-ключ",
        "Таймаут",
        "Сетевая ошибка",
        "Неподдерживаемый провайдер",
        "Превышен лимит",
    )
    return any(response.startswith(m) or m in response for m in markers)


def _parse_response(original: str, raw: str) -> PromptImprovementResult:
    if _looks_like_error(raw):
        return PromptImprovementResult(
            original=original,
            error=raw,
            raw_response=raw,
        )

    try:
        data = _extract_json(raw)
    except (ValueError, json.JSONDecodeError):
        return PromptImprovementResult(
            original=original,
            improved=raw.strip(),
            raw_response=raw,
        )

    improved = str(data.get("improved") or "").strip()
    alternatives_raw = data.get("alternatives") or []
    alternatives = [str(item).strip() for item in alternatives_raw if str(item).strip()]

    adaptations_raw = data.get("adaptations") or {}
    adaptations: dict[str, str] = {}
    if isinstance(adaptations_raw, dict):
        for key in ("code", "analysis", "creative"):
            value = adaptations_raw.get(key)
            if value:
                adaptations[key] = str(value).strip()

    if not improved:
        improved = raw.strip()

    return PromptImprovementResult(
        original=original,
        improved=improved,
        alternatives=alternatives[:3],
        adaptations=adaptations,
        raw_response=raw,
    )


class PromptAssistant:
    def improve(
        self,
        prompt_text: str,
        model: AIModel,
        network: NetworkClient,
    ) -> PromptImprovementResult:
        text = prompt_text.strip()
        if not text:
            raise PromptAssistantError("Промт пустой")

        messages = [
            {"role": "system", "content": ASSISTANT_SYSTEM_PROMPT},
            {"role": "user", "content": f"Исходный промт:\n\n{text}"},
        ]
        raw = network.send_messages(
            model,
            messages,
            log_requests=False,
        )
        return _parse_response(text, raw)
