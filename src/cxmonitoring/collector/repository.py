from __future__ import annotations

import sqlite3
from pathlib import Path

from .models import ThreadRecord, epoch_to_iso, normalize_windows_path


class ThreadRepository:
    def __init__(self, state_db_path: Path) -> None:
        self._state_db_path = state_db_path

    @property
    def state_db_path(self) -> Path:
        return self._state_db_path

    def get_latest_thread(self) -> ThreadRecord | None:
        if not self._state_db_path.exists():
            return None

        query = """
            SELECT
                id,
                COALESCE(NULLIF(title, ''), NULLIF(first_user_message, '')) AS title,
                source,
                cwd,
                rollout_path,
                updated_at,
                model,
                reasoning_effort
            FROM threads
            WHERE source = 'vscode'
              AND rollout_path IS NOT NULL
              AND rollout_path != ''
            ORDER BY updated_at DESC
            LIMIT 1
        """

        connection = sqlite3.connect(str(self._state_db_path), timeout=1.0)
        try:
            connection.row_factory = sqlite3.Row
            row = connection.execute(query).fetchone()
        finally:
            connection.close()

        if row is None:
            return None

        return ThreadRecord(
            id=row["id"],
            title=row["title"],
            source=row["source"],
            cwd=normalize_windows_path(row["cwd"]),
            rollout_path=normalize_windows_path(row["rollout_path"]) or "",
            updated_at=epoch_to_iso(row["updated_at"]),
            model=row["model"],
            reasoning_effort=row["reasoning_effort"],
        )
