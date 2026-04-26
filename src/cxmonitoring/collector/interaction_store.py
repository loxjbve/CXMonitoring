from __future__ import annotations

import sqlite3
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from .models import TimelineEntry, utc_now_iso
from .projector import summarize_text


@dataclass(slots=True)
class InteractionRecord:
    id: int
    thread_id: str
    kind: str
    content: str
    created_at: str
    reply_to: str | None = None
    source: str = "mobile"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_timeline_entry(self) -> TimelineEntry:
        metadata: dict[str, Any] = {
            "kind": self.kind,
            "source": self.source,
        }
        if self.reply_to:
            metadata["reply_to"] = self.reply_to

        return TimelineEntry(
            ts=self.created_at,
            kind="user",
            label="You",
            summary=summarize_text(self.content),
            raw_status=self.kind,
            details=self.content,
            metadata=metadata,
        )


class InteractionStore:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    @property
    def db_path(self) -> Path:
        return self._db_path

    def initialize(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(str(self._db_path), timeout=1.0)
        try:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS interaction_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    thread_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    content TEXT NOT NULL,
                    reply_to TEXT,
                    source TEXT NOT NULL DEFAULT 'mobile',
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_interaction_messages_thread_created
                ON interaction_messages(thread_id, created_at, id)
                """
            )
            connection.commit()
        finally:
            connection.close()

    def append_message(
        self,
        *,
        thread_id: str,
        content: str,
        kind: str = "instruction",
        reply_to: str | None = None,
        source: str = "mobile",
    ) -> InteractionRecord:
        self.initialize()
        created_at = utc_now_iso()
        connection = sqlite3.connect(str(self._db_path), timeout=1.0)
        try:
            cursor = connection.execute(
                """
                INSERT INTO interaction_messages (
                    thread_id, kind, content, reply_to, source, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (thread_id, kind, content, reply_to, source, created_at),
            )
            connection.commit()
            record_id = int(cursor.lastrowid)
        finally:
            connection.close()

        return InteractionRecord(
            id=record_id,
            thread_id=thread_id,
            kind=kind,
            content=content,
            created_at=created_at,
            reply_to=reply_to,
            source=source,
        )

    def list_timeline_entries(self, thread_id: str) -> list[TimelineEntry]:
        self.initialize()
        connection = sqlite3.connect(str(self._db_path), timeout=1.0)
        try:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT id, thread_id, kind, content, reply_to, source, created_at
                FROM interaction_messages
                WHERE thread_id = ?
                ORDER BY created_at ASC, id ASC
                """,
                (thread_id,),
            ).fetchall()
        finally:
            connection.close()

        entries: list[TimelineEntry] = []
        for row in rows:
            record = InteractionRecord(
                id=int(row["id"]),
                thread_id=row["thread_id"],
                kind=row["kind"],
                content=row["content"],
                created_at=row["created_at"],
                reply_to=row["reply_to"],
                source=row["source"],
            )
            entries.append(record.to_timeline_entry())
        return entries
