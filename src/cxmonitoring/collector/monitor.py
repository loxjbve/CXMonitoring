from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from ..config import Settings
from .models import CurrentThreadSnapshot, MonitorHealth, StreamEvent, ThreadRecord, utc_now_iso
from .projector import RolloutProjector
from .repository import ThreadRepository


class RolloutMonitor:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._repository = ThreadRepository(settings.state_db_path)
        self._projector = RolloutProjector(settings.timeline_limit)
        self._snapshot = CurrentThreadSnapshot()
        self._health = MonitorHealth(
            state_db_path=str(settings.state_db_path),
            logs_db_path=str(settings.logs_db_path),
        )
        self._logger = logging.getLogger(__name__)
        self._state_lock = asyncio.Lock()
        self._subscribers: set[asyncio.Queue[StreamEvent]] = set()
        self._runner: asyncio.Task[None] | None = None
        self._current_thread: ThreadRecord | None = None
        self._rollout_offset = 0
        self._pending_bytes = b""

    async def start(self) -> None:
        if self._runner is None or self._runner.done():
            await self._refresh_active_thread()
            await self._read_rollout_updates()
            self._runner = asyncio.create_task(self._run(), name="cxmonitoring-rollout-monitor")

    async def stop(self) -> None:
        if self._runner is None:
            return
        self._runner.cancel()
        try:
            await self._runner
        except asyncio.CancelledError:
            pass
        self._runner = None

    async def subscribe(self) -> asyncio.Queue[StreamEvent]:
        queue: asyncio.Queue[StreamEvent] = asyncio.Queue(maxsize=128)
        self._subscribers.add(queue)
        async with self._state_lock:
            self._health.subscriber_count = len(self._subscribers)
        return queue

    async def unsubscribe(self, queue: asyncio.Queue[StreamEvent]) -> None:
        self._subscribers.discard(queue)
        async with self._state_lock:
            self._health.subscriber_count = len(self._subscribers)

    async def get_snapshot(self) -> dict[str, Any]:
        async with self._state_lock:
            return self._snapshot.to_dict()

    async def get_health(self) -> dict[str, Any]:
        async with self._state_lock:
            self._health.subscriber_count = len(self._subscribers)
            self._health.unknown_event_count = self._projector.unknown_event_count
            self._health.status = self._derive_health_status()
            return self._health.to_dict()

    async def _run(self) -> None:
        next_thread_refresh = 0.0
        next_rollout_refresh = 0.0
        loop = asyncio.get_running_loop()
        while True:
            now = loop.time()
            if now >= next_thread_refresh:
                await self._refresh_active_thread()
                next_thread_refresh = now + self._settings.thread_poll_interval
            if now >= next_rollout_refresh:
                await self._read_rollout_updates()
                next_rollout_refresh = now + self._settings.rollout_poll_interval
            await asyncio.sleep(0.05)

    async def _refresh_active_thread(self) -> None:
        try:
            latest_thread = await asyncio.to_thread(self._repository.get_latest_thread)
            async with self._state_lock:
                self._health.last_thread_refresh_at = utc_now_iso()
            if self._thread_changed(latest_thread):
                await self._switch_thread(latest_thread)
        except Exception as exc:  # pragma: no cover
            async with self._state_lock:
                self._health.last_error = f"Thread refresh failed: {exc}"
            self._logger.exception("Failed to refresh active thread")

    def _thread_changed(self, latest_thread: ThreadRecord | None) -> bool:
        if self._current_thread is None and latest_thread is None:
            return False
        if self._current_thread is None or latest_thread is None:
            return True
        return (
            self._current_thread.id != latest_thread.id
            or self._current_thread.rollout_path != latest_thread.rollout_path
        )

    async def _switch_thread(self, thread: ThreadRecord | None) -> None:
        if thread is None:
            async with self._state_lock:
                self._current_thread = None
                self._snapshot = CurrentThreadSnapshot()
                self._rollout_offset = 0
                self._pending_bytes = b""
                self._health.current_thread_id = None
                self._health.rollout_path = None
            await self._broadcast("thread-switched", {"thread_id": None})
            await self._broadcast("snapshot", self._snapshot.to_dict())
            return

        snapshot = await asyncio.to_thread(self._replay_thread, thread)
        rollout_path = Path(thread.rollout_path)
        async with self._state_lock:
            self._current_thread = thread
            self._snapshot = snapshot
            self._rollout_offset = rollout_path.stat().st_size if rollout_path.exists() else 0
            self._pending_bytes = b""
            self._health.current_thread_id = thread.id
            self._health.rollout_path = thread.rollout_path
            self._health.last_successful_event_at = snapshot.last_event_at
            self._health.last_error = None
        await self._broadcast(
            "thread-switched",
            {"thread_id": thread.id, "title": thread.title, "rollout_path": thread.rollout_path},
        )
        await self._broadcast("snapshot", snapshot.to_dict())

    def _replay_thread(self, thread: ThreadRecord) -> CurrentThreadSnapshot:
        snapshot = self._projector.create_snapshot(thread)
        rollout_path = Path(thread.rollout_path)
        if not rollout_path.exists():
            return snapshot
        with rollout_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                self._projector.apply_event(snapshot, event)
        return snapshot

    async def _read_rollout_updates(self) -> None:
        async with self._state_lock:
            thread = self._current_thread
            current_offset = self._rollout_offset
            pending_bytes = self._pending_bytes

        if thread is None:
            return

        rollout_path = Path(thread.rollout_path)
        if not rollout_path.exists():
            async with self._state_lock:
                self._health.last_error = f"Rollout file is missing: {rollout_path}"
            return

        current_size = rollout_path.stat().st_size
        if current_size < current_offset:
            await self._switch_thread(thread)
            return
        if current_size == current_offset:
            return

        try:
            with rollout_path.open("rb") as handle:
                handle.seek(current_offset)
                chunk = handle.read()
                new_offset = handle.tell()
        except OSError as exc:
            async with self._state_lock:
                self._health.last_error = f"Failed to read rollout: {exc}"
            self._logger.exception("Failed to tail rollout file")
            return

        raw_lines = (pending_bytes + chunk).split(b"\n")
        pending = raw_lines.pop() if raw_lines else b""
        updates: list[StreamEvent] = []

        async with self._state_lock:
            for raw_line in raw_lines:
                line = raw_line.rstrip(b"\r")
                if not line:
                    continue
                try:
                    event = json.loads(line.decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                    self._health.last_error = f"Failed to parse rollout line: {exc}"
                    self._logger.debug("Skipping malformed rollout line", exc_info=exc)
                    continue

                timeline_entries = self._projector.apply_event(self._snapshot, event)
                self._health.last_successful_event_at = self._snapshot.last_event_at
                for entry in timeline_entries:
                    updates.append(StreamEvent("timeline", entry.to_dict()))
                updates.append(StreamEvent("snapshot", self._snapshot.to_dict()))

            self._rollout_offset = new_offset
            self._pending_bytes = pending
            self._health.last_rollout_read_at = utc_now_iso()
            self._health.last_error = None

        for update in updates:
            await self._broadcast(update.event, update.payload)

    async def _broadcast(self, event_name: str, payload: dict[str, Any]) -> None:
        if not self._subscribers:
            return

        event = StreamEvent(event_name, payload)
        dead_queues: list[asyncio.Queue[StreamEvent]] = []
        for queue in list(self._subscribers):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                try:
                    queue.get_nowait()
                    queue.put_nowait(event)
                except (asyncio.QueueEmpty, asyncio.QueueFull):
                    dead_queues.append(queue)

        for queue in dead_queues:
            self._subscribers.discard(queue)

    def _derive_health_status(self) -> str:
        if self._health.last_error:
            return "degraded"
        if self._current_thread is None:
            return "idle"
        return "ok"
