"""HTTP-запросы к API нейросетей."""

from __future__ import annotations

import time
from typing import Callable

import httpx

from db import Database
from models import AIModel, ModelManager

SUPPORTED_PROVIDERS = frozenset({"openai", "deepseek", "groq", "openrouter"})

ChatAdapter = Callable[[AIModel, list[dict[str, str]], str, float], str]


def _extract_chat_content(data: dict) -> str:
    choices = data.get("choices")
    if not choices:
        raise ValueError("API вернул пустой список choices")

    message = choices[0].get("message") or {}
    content = message.get("content")
    if content is None or str(content).strip() == "":
        raise ValueError("API вернул пустой ответ")

    return str(content).strip()


def _openai_compatible_chat(
    model: AIModel,
    messages: list[dict[str, str]],
    api_key: str,
    timeout: float,
    extra_headers: dict[str, str] | None = None,
) -> str:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if extra_headers:
        headers.update(extra_headers)
    payload = {
        "model": model.api_id,
        "messages": messages,
    }

    with httpx.Client(timeout=timeout) as client:
        response = client.post(model.api_url, headers=headers, json=payload)
        response.raise_for_status()
        return _extract_chat_content(response.json())


def _openrouter_chat(
    model: AIModel,
    messages: list[dict[str, str]],
    api_key: str,
    timeout: float,
) -> str:
    return _openai_compatible_chat(
        model,
        messages,
        api_key,
        timeout,
        extra_headers={
            "HTTP-Referer": "https://github.com/chatlist",
            "X-Title": "ChatList",
        },
    )


PROVIDER_CHAT_ADAPTERS: dict[str, ChatAdapter] = {
    "openai": _openai_compatible_chat,
    "deepseek": _openai_compatible_chat,
    "groq": _openai_compatible_chat,
    "openrouter": _openrouter_chat,
}


def _format_http_error(exc: httpx.HTTPStatusError) -> str:
    status = exc.response.status_code
    if status == 401:
        return "Ошибка авторизации (401): проверьте API-ключ."
    if status == 429:
        return "Превышен лимит запросов (429): повторите позже."
    if status >= 500:
        return f"Ошибка сервера ({status}): сервис временно недоступен."
    try:
        body = exc.response.json()
        detail = body.get("error", {}).get("message") or body.get("message")
        if detail:
            return f"Ошибка API ({status}): {detail}"
    except Exception:
        pass
    return f"Ошибка API ({status}): {exc.response.text[:200]}"


class NetworkClient:
    def __init__(
        self,
        database: Database,
        model_manager: ModelManager,
        timeout: float | None = None,
        log_requests: bool = True,
    ) -> None:
        self._db = database
        self._models = model_manager
        if timeout is None:
            raw = database.get_setting("request_timeout", "60")
            timeout = float(raw or "60")
        self.timeout = timeout
        self.log_requests = log_requests

    def send_prompt(
        self,
        model: AIModel,
        prompt_text: str,
        prompt_id: int | None = None,
        *,
        log_requests: bool | None = None,
    ) -> str:
        return self.send_messages(
            model,
            [{"role": "user", "content": prompt_text}],
            prompt_id=prompt_id,
            log_requests=log_requests,
        )

    def send_messages(
        self,
        model: AIModel,
        messages: list[dict[str, str]],
        prompt_id: int | None = None,
        *,
        log_requests: bool | None = None,
    ) -> str:
        should_log = self.log_requests if log_requests is None else log_requests
        api_key = self._models.get_api_key(model)
        if not api_key:
            message = (
                f"API-ключ не найден: задайте переменную {model.api_key_env} в .env"
            )
            self._log(model, prompt_id, "error", 0, message, should_log)
            return message

        adapter = PROVIDER_CHAT_ADAPTERS.get(model.provider)
        if adapter is None:
            message = f"Неподдерживаемый провайдер: {model.provider}"
            self._log(model, prompt_id, "error", 0, message, should_log)
            return message

        started = time.perf_counter()
        try:
            result = adapter(model, messages, api_key, self.timeout)
            duration_ms = int((time.perf_counter() - started) * 1000)
            self._log(model, prompt_id, "success", duration_ms, None, should_log)
            return result
        except httpx.TimeoutException:
            duration_ms = int((time.perf_counter() - started) * 1000)
            message = f"Таймаут запроса ({self.timeout:.0f} с) к модели «{model.name}»"
            self._log(model, prompt_id, "timeout", duration_ms, message, should_log)
            return message
        except httpx.HTTPStatusError as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            message = _format_http_error(exc)
            self._log(model, prompt_id, "error", duration_ms, message, should_log)
            return message
        except httpx.RequestError as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            message = f"Сетевая ошибка: {exc}"
            self._log(model, prompt_id, "error", duration_ms, message, should_log)
            return message
        except ValueError as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            message = str(exc)
            self._log(model, prompt_id, "error", duration_ms, message, should_log)
            return message

    def send_to_active_models(
        self,
        prompt_text: str,
        prompt_id: int | None = None,
    ) -> list[tuple[AIModel, str]]:
        results: list[tuple[AIModel, str]] = []
        for model in self._models.get_ready_active_models():
            response = self.send_prompt(model, prompt_text, prompt_id)
            results.append((model, response))
        return results

    def _log(
        self,
        model: AIModel,
        prompt_id: int | None,
        status: str,
        duration_ms: int,
        error_message: str | None = None,
        should_log: bool | None = None,
    ) -> None:
        if should_log is None:
            should_log = self.log_requests
        if not should_log:
            return
        self._db.create_request_log(
            model_id=model.id,
            prompt_id=prompt_id,
            status=status,
            duration_ms=duration_ms,
            error_message=error_message,
        )
