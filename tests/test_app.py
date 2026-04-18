from __future__ import annotations

import asyncio
import importlib.util
import json
import sqlite3
import sys
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

FASTAPI_AVAILABLE = bool(importlib.util.find_spec("fastapi"))

if FASTAPI_AVAILABLE:
    from cxmonitoring.config import Settings
    from cxmonitoring.server.app import create_app


THREADS_SCHEMA = """
CREATE TABLE threads (
    id TEXT,
    rollout_path TEXT,
    created_at INTEGER,
    updated_at INTEGER,
    source TEXT,
    model_provider TEXT,
    cwd TEXT,
    title TEXT,
    sandbox_policy TEXT,
    approval_mode TEXT,
    tokens_used INTEGER,
    has_user_event INTEGER,
    archived INTEGER,
    archived_at INTEGER,
    git_sha TEXT,
    git_branch TEXT,
    git_origin_url TEXT,
    cli_version TEXT,
    first_user_message TEXT,
    agent_nickname TEXT,
    agent_role TEXT,
    memory_mode TEXT,
    model TEXT,
    reasoning_effort TEXT,
    agent_path TEXT
)
"""


@unittest.skipUnless(FASTAPI_AVAILABLE, "fastapi/httpx are required for integration tests")
class AppIntegrationTests(unittest.IsolatedAsyncioTestCase):
    @contextmanager
    def tempdir(self):
        root = Path.cwd() / ".test-tmp"
        root.mkdir(exist_ok=True)
        workdir = root / uuid.uuid4().hex
        workdir.mkdir(parents=True, exist_ok=True)
        try:
            yield str(workdir)
        finally:
            pass

    def create_thread_db(self, db_path: Path, rollout_path: Path) -> None:
        connection = sqlite3.connect(db_path)
        try:
            connection.execute(THREADS_SCHEMA)
            connection.execute(
                """
                INSERT INTO threads (
                    id, rollout_path, created_at, updated_at, source, model_provider, cwd,
                    title, sandbox_policy, approval_mode, tokens_used, has_user_event,
                    archived, archived_at, git_sha, git_branch, git_origin_url, cli_version,
                    first_user_message, agent_nickname, agent_role, memory_mode, model,
                    reasoning_effort, agent_path
                ) VALUES (?, ?, 0, ?, 'vscode', '', ?, ?, '', '', 0, 0, 0, 0, '', '', '', '', ?, '', '', '', ?, ?, '')
                """,
                (
                    "thread-1",
                    str(rollout_path),
                    50,
                    "E:\\Dev\\CXMonitoring",
                    "LAN monitor rollout",
                    "Please mirror Codex progress to the LAN dashboard",
                    "gpt-5.4",
                    "xhigh",
                ),
            )
            connection.commit()
        finally:
            connection.close()

    def event(self, outer_type: str, inner_type: str, **payload: object) -> str:
        return json.dumps(
            {
                "timestamp": "2026-04-14T15:12:41.464Z",
                "type": outer_type,
                "payload": {"type": inner_type, **payload},
            }
        )

    async def test_current_and_stream_reflect_rollout_changes(self) -> None:
        with self.tempdir() as tmpdir:
            codex_home = Path(tmpdir)
            rollout_path = codex_home / "rollout.jsonl"
            rollout_path.write_text(
                self.event(
                    "event_msg",
                    "task_started",
                    turn_id="turn-1",
                    started_at=1776179561,
                    collaboration_mode_kind="plan",
                )
                + "\n"
                + self.event(
                    "event_msg",
                    "agent_message",
                    message="Inspecting the rollout file now.",
                )
                + "\n",
                encoding="utf-8",
            )

            state_db_path = codex_home / "state_5.sqlite"
            logs_db_path = codex_home / "logs_2.sqlite"
            self.create_thread_db(state_db_path, rollout_path)
            logs_db_path.touch()

            settings = Settings(
                codex_home=codex_home,
                state_db_path=state_db_path,
                logs_db_path=logs_db_path,
                host="127.0.0.1",
                port=3180,
                thread_poll_interval=0.05,
                rollout_poll_interval=0.05,
                timeline_limit=20,
            )

            app = create_app(settings=settings)
            monitor = app.state.monitor
            await monitor.start()
            try:
                await asyncio.sleep(0.2)

                current_endpoint = self.route_endpoint(app, "/api/current")
                snapshot = await current_endpoint()
                self.assertEqual(snapshot["status"], "running")
                self.assertEqual(snapshot["last_agent_message"], "Inspecting the rollout file now.")

                stream_endpoint = self.route_endpoint(app, "/api/stream")
                request = self.FakeRequest()
                response = await stream_endpoint(request)
                iterator = response.body_iterator

                first_event, first_payload = await self.read_sse_event(iterator)
                self.assertEqual(first_event, "snapshot")
                self.assertEqual(first_payload["thread_id"], "thread-1")

                with rollout_path.open("a", encoding="utf-8") as handle:
                    handle.write(
                        self.event(
                            "event_msg",
                            "task_complete",
                            last_agent_message="The task is complete.",
                        )
                        + "\n"
                    )

                event_name = ""
                payload = {}
                deadline = asyncio.get_running_loop().time() + 3
                while asyncio.get_running_loop().time() < deadline:
                    event_name, payload = await self.read_sse_event(iterator)
                    if event_name == "snapshot" and payload.get("status") == "complete":
                        break

                self.assertEqual(event_name, "snapshot")
                self.assertEqual(payload["status"], "complete")
                self.assertEqual(payload["last_agent_message"], "The task is complete.")
                request.disconnect()
                await iterator.aclose()
            finally:
                await monitor.stop()

    class FakeRequest:
        def __init__(self) -> None:
            self._disconnected = False

        async def is_disconnected(self) -> bool:
            return self._disconnected

        def disconnect(self) -> None:
            self._disconnected = True

    def route_endpoint(self, app, path: str):
        for route in app.router.routes:
            if getattr(route, "path", None) == path:
                return route.endpoint
        raise AssertionError(f"Route {path} was not found")

    async def read_sse_event(self, iterator) -> tuple[str, dict[str, object]]:
        chunk = await asyncio.wait_for(anext(iterator), timeout=2)
        if isinstance(chunk, bytes):
            chunk = chunk.decode("utf-8")

        event_name = ""
        data = ""
        for line in chunk.splitlines():
            if line.startswith("event: "):
                event_name = line.removeprefix("event: ")
            elif line.startswith("data: "):
                data = line.removeprefix("data: ")

        if not event_name:
            raise AssertionError(f"Unexpected SSE chunk: {chunk!r}")
        return event_name, json.loads(data)
