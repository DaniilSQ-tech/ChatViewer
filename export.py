"""Экспорт результатов в Markdown и JSON."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from session import SessionRow


def export_markdown(
    prompt_text: str,
    rows: list[SessionRow],
    path: Path,
) -> None:
    lines = [
        f"# Результаты ChatList",
        "",
        f"**Промт:** {prompt_text}",
        "",
        f"**Дата:** {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
    ]
    for row in rows:
        lines.extend(
            [
                f"## {row.model_name}",
                "",
                row.response_text,
                "",
                "---",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def export_json(
    prompt_text: str,
    prompt_id: int | None,
    rows: list[SessionRow],
    path: Path,
) -> None:
    payload = {
        "prompt_id": prompt_id,
        "prompt_text": prompt_text,
        "exported_at": datetime.now(UTC).isoformat(),
        "results": [
            {
                "model_id": row.model_id,
                "model_name": row.model_name,
                "response_text": row.response_text,
                "selected": row.selected,
            }
            for row in rows
        ],
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
