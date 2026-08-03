"""Доступ к SQLite. Все SQL-запросы инкапсулированы в этом модуле."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_DB_PATH = Path("data/chatlist.db")

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS prompts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at  TEXT    NOT NULL,
    text        TEXT    NOT NULL,
    tags        TEXT    DEFAULT ''
);

CREATE TABLE IF NOT EXISTS models (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    api_url     TEXT    NOT NULL,
    api_id      TEXT    NOT NULL,
    api_key_env TEXT    NOT NULL,
    provider    TEXT    NOT NULL DEFAULT 'openai',
    is_active   INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS results (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_id     INTEGER NOT NULL,
    model_id      INTEGER NOT NULL,
    response_text TEXT    NOT NULL,
    created_at    TEXT    NOT NULL,
    FOREIGN KEY (prompt_id) REFERENCES prompts(id) ON DELETE CASCADE,
    FOREIGN KEY (model_id)  REFERENCES models(id)  ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS request_logs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id      INTEGER NOT NULL,
    prompt_id     INTEGER,
    status        TEXT    NOT NULL,
    duration_ms   INTEGER,
    error_message TEXT,
    created_at    TEXT    NOT NULL,
    FOREIGN KEY (model_id)  REFERENCES models(id)  ON DELETE CASCADE,
    FOREIGN KEY (prompt_id) REFERENCES prompts(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_prompts_created_at ON prompts(created_at);
CREATE INDEX IF NOT EXISTS idx_models_is_active   ON models(is_active);
CREATE INDEX IF NOT EXISTS idx_results_prompt_id  ON results(prompt_id);
CREATE INDEX IF NOT EXISTS idx_results_model_id   ON results(model_id);
CREATE INDEX IF NOT EXISTS idx_results_created_at ON results(created_at);
"""

DEFAULT_SETTINGS: dict[str, str] = {
    "db_path": "data/chatlist.db",
    "request_timeout": "60",
    "window_width": "1200",
    "window_height": "800",
}


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass
class Prompt:
    id: int
    created_at: str
    text: str
    tags: str


@dataclass
class ModelRecord:
    id: int
    name: str
    api_url: str
    api_id: str
    api_key_env: str
    provider: str
    is_active: bool


@dataclass
class Result:
    id: int
    prompt_id: int
    model_id: int
    response_text: str
    created_at: str


@dataclass
class RequestLog:
    id: int
    model_id: int
    prompt_id: int | None
    status: str
    duration_ms: int | None
    error_message: str | None
    created_at: str


class Database:
    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self.init_schema()

    def close(self) -> None:
        self._conn.close()

    def init_schema(self) -> None:
        self._conn.executescript(SCHEMA_SQL)
        for key, value in DEFAULT_SETTINGS.items():
            self._conn.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, value),
            )
        self._conn.commit()

    def _fetchone(self, sql: str, params: tuple[Any, ...] = ()) -> sqlite3.Row | None:
        return self._conn.execute(sql, params).fetchone()

    def _fetchall(self, sql: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        return self._conn.execute(sql, params).fetchall()

    # --- prompts ---

    def create_prompt(self, text: str, tags: str = "") -> Prompt:
        created_at = utc_now_iso()
        cursor = self._conn.execute(
            "INSERT INTO prompts (created_at, text, tags) VALUES (?, ?, ?)",
            (created_at, text, tags),
        )
        self._conn.commit()
        return Prompt(id=cursor.lastrowid, created_at=created_at, text=text, tags=tags)

    def get_prompt(self, prompt_id: int) -> Prompt | None:
        row = self._fetchone("SELECT * FROM prompts WHERE id = ?", (prompt_id,))
        return self._row_to_prompt(row) if row else None

    def list_prompts(self, order: str = "DESC") -> list[Prompt]:
        direction = "DESC" if order.upper() == "DESC" else "ASC"
        rows = self._fetchall(f"SELECT * FROM prompts ORDER BY created_at {direction}")
        return [self._row_to_prompt(row) for row in rows]

    def search_prompts(self, query: str) -> list[Prompt]:
        pattern = f"%{query}%"
        rows = self._fetchall(
            """
            SELECT * FROM prompts
            WHERE text LIKE ? OR tags LIKE ?
            ORDER BY created_at DESC
            """,
            (pattern, pattern),
        )
        return [self._row_to_prompt(row) for row in rows]

    def update_prompt(self, prompt_id: int, text: str, tags: str) -> Prompt | None:
        self._conn.execute(
            "UPDATE prompts SET text = ?, tags = ? WHERE id = ?",
            (text, tags, prompt_id),
        )
        self._conn.commit()
        return self.get_prompt(prompt_id)

    def delete_prompt(self, prompt_id: int) -> bool:
        cursor = self._conn.execute("DELETE FROM prompts WHERE id = ?", (prompt_id,))
        self._conn.commit()
        return cursor.rowcount > 0

    @staticmethod
    def _row_to_prompt(row: sqlite3.Row) -> Prompt:
        return Prompt(
            id=row["id"],
            created_at=row["created_at"],
            text=row["text"],
            tags=row["tags"] or "",
        )

    # --- models ---

    def create_model(
        self,
        name: str,
        api_url: str,
        api_id: str,
        api_key_env: str,
        provider: str = "openai",
        is_active: bool = True,
    ) -> ModelRecord:
        cursor = self._conn.execute(
            """
            INSERT INTO models (name, api_url, api_id, api_key_env, provider, is_active)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (name, api_url, api_id, api_key_env, provider, int(is_active)),
        )
        self._conn.commit()
        return ModelRecord(
            id=cursor.lastrowid,
            name=name,
            api_url=api_url,
            api_id=api_id,
            api_key_env=api_key_env,
            provider=provider,
            is_active=is_active,
        )

    def get_model(self, model_id: int) -> ModelRecord | None:
        row = self._fetchone("SELECT * FROM models WHERE id = ?", (model_id,))
        return self._row_to_model(row) if row else None

    def list_models(self, active_only: bool = False) -> list[ModelRecord]:
        if active_only:
            rows = self._fetchall(
                "SELECT * FROM models WHERE is_active = 1 ORDER BY name"
            )
        else:
            rows = self._fetchall("SELECT * FROM models ORDER BY name")
        return [self._row_to_model(row) for row in rows]

    def update_model(
        self,
        model_id: int,
        name: str,
        api_url: str,
        api_id: str,
        api_key_env: str,
        provider: str,
        is_active: bool,
    ) -> ModelRecord | None:
        self._conn.execute(
            """
            UPDATE models
            SET name = ?, api_url = ?, api_id = ?, api_key_env = ?,
                provider = ?, is_active = ?
            WHERE id = ?
            """,
            (name, api_url, api_id, api_key_env, provider, int(is_active), model_id),
        )
        self._conn.commit()
        return self.get_model(model_id)

    def set_model_active(self, model_id: int, is_active: bool) -> ModelRecord | None:
        self._conn.execute(
            "UPDATE models SET is_active = ? WHERE id = ?",
            (int(is_active), model_id),
        )
        self._conn.commit()
        return self.get_model(model_id)

    def delete_model(self, model_id: int) -> bool:
        cursor = self._conn.execute("DELETE FROM models WHERE id = ?", (model_id,))
        self._conn.commit()
        return cursor.rowcount > 0

    def clear_all_models(self) -> int:
        """Удаляет все модели и связанные результаты/логи."""
        self._conn.execute("DELETE FROM results")
        self._conn.execute("DELETE FROM request_logs")
        cursor = self._conn.execute("DELETE FROM models")
        self._conn.commit()
        return cursor.rowcount

    def count_models(self) -> int:
        row = self._fetchone("SELECT COUNT(*) AS cnt FROM models")
        return int(row["cnt"]) if row else 0

    @staticmethod
    def _row_to_model(row: sqlite3.Row) -> ModelRecord:
        return ModelRecord(
            id=row["id"],
            name=row["name"],
            api_url=row["api_url"],
            api_id=row["api_id"],
            api_key_env=row["api_key_env"],
            provider=row["provider"],
            is_active=bool(row["is_active"]),
        )

    # --- results ---

    def create_result(
        self, prompt_id: int, model_id: int, response_text: str
    ) -> Result:
        created_at = utc_now_iso()
        cursor = self._conn.execute(
            """
            INSERT INTO results (prompt_id, model_id, response_text, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (prompt_id, model_id, response_text, created_at),
        )
        self._conn.commit()
        return Result(
            id=cursor.lastrowid,
            prompt_id=prompt_id,
            model_id=model_id,
            response_text=response_text,
            created_at=created_at,
        )

    def create_results_batch(
        self,
        prompt_id: int,
        items: list[tuple[int, str]],
    ) -> list[Result]:
        created_at = utc_now_iso()
        results: list[Result] = []
        for model_id, response_text in items:
            cursor = self._conn.execute(
                """
                INSERT INTO results (prompt_id, model_id, response_text, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (prompt_id, model_id, response_text, created_at),
            )
            results.append(
                Result(
                    id=cursor.lastrowid,
                    prompt_id=prompt_id,
                    model_id=model_id,
                    response_text=response_text,
                    created_at=created_at,
                )
            )
        self._conn.commit()
        return results

    def get_result(self, result_id: int) -> Result | None:
        row = self._fetchone("SELECT * FROM results WHERE id = ?", (result_id,))
        return self._row_to_result(row) if row else None

    def list_results(
        self,
        prompt_id: int | None = None,
        model_id: int | None = None,
    ) -> list[Result]:
        sql = "SELECT * FROM results WHERE 1=1"
        params: list[Any] = []
        if prompt_id is not None:
            sql += " AND prompt_id = ?"
            params.append(prompt_id)
        if model_id is not None:
            sql += " AND model_id = ?"
            params.append(model_id)
        sql += " ORDER BY created_at DESC"
        rows = self._fetchall(sql, tuple(params))
        return [self._row_to_result(row) for row in rows]

    def delete_result(self, result_id: int) -> bool:
        cursor = self._conn.execute("DELETE FROM results WHERE id = ?", (result_id,))
        self._conn.commit()
        return cursor.rowcount > 0

    @staticmethod
    def _row_to_result(row: sqlite3.Row) -> Result:
        return Result(
            id=row["id"],
            prompt_id=row["prompt_id"],
            model_id=row["model_id"],
            response_text=row["response_text"],
            created_at=row["created_at"],
        )

    # --- settings ---

    def get_setting(self, key: str, default: str | None = None) -> str | None:
        row = self._fetchone("SELECT value FROM settings WHERE key = ?", (key,))
        if row is None:
            return default
        return row["value"]

    def set_setting(self, key: str, value: str) -> None:
        self._conn.execute(
            """
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )
        self._conn.commit()

    def list_settings(self) -> dict[str, str]:
        rows = self._fetchall("SELECT key, value FROM settings ORDER BY key")
        return {row["key"]: row["value"] or "" for row in rows}

    def delete_setting(self, key: str) -> bool:
        cursor = self._conn.execute("DELETE FROM settings WHERE key = ?", (key,))
        self._conn.commit()
        return cursor.rowcount > 0

    # --- request_logs ---

    def create_request_log(
        self,
        model_id: int,
        status: str,
        prompt_id: int | None = None,
        duration_ms: int | None = None,
        error_message: str | None = None,
    ) -> RequestLog:
        created_at = utc_now_iso()
        cursor = self._conn.execute(
            """
            INSERT INTO request_logs
                (model_id, prompt_id, status, duration_ms, error_message, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (model_id, prompt_id, status, duration_ms, error_message, created_at),
        )
        self._conn.commit()
        return RequestLog(
            id=cursor.lastrowid,
            model_id=model_id,
            prompt_id=prompt_id,
            status=status,
            duration_ms=duration_ms,
            error_message=error_message,
            created_at=created_at,
        )

    def list_request_logs(self, limit: int = 100) -> list[RequestLog]:
        rows = self._fetchall(
            "SELECT * FROM request_logs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        return [self._row_to_request_log(row) for row in rows]

    @staticmethod
    def _row_to_request_log(row: sqlite3.Row) -> RequestLog:
        return RequestLog(
            id=row["id"],
            model_id=row["model_id"],
            prompt_id=row["prompt_id"],
            status=row["status"],
            duration_ms=row["duration_ms"],
            error_message=row["error_message"],
            created_at=row["created_at"],
        )
