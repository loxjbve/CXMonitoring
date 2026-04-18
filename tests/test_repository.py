from __future__ import annotations

import sqlite3
import sys
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cxmonitoring.collector.repository import ThreadRepository


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


class ThreadRepositoryTests(unittest.TestCase):
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

    def create_database(self, path: Path) -> None:
        connection = sqlite3.connect(path)
        try:
            connection.execute(THREADS_SCHEMA)
            connection.commit()
        finally:
            connection.close()

    def test_returns_latest_vscode_thread_with_rollout(self) -> None:
        with self.tempdir() as tmpdir:
            db_path = Path(tmpdir) / "state_5.sqlite"
            self.create_database(db_path)
            connection = sqlite3.connect(db_path)
            try:
                connection.executemany(
                    """
                    INSERT INTO threads (
                        id, rollout_path, created_at, updated_at, source, model_provider, cwd,
                        title, sandbox_policy, approval_mode, tokens_used, has_user_event,
                        archived, archived_at, git_sha, git_branch, git_origin_url, cli_version,
                        first_user_message, agent_nickname, agent_role, memory_mode, model,
                        reasoning_effort, agent_path
                    ) VALUES (?, ?, 0, ?, ?, '', ?, ?, '', '', 0, 0, 0, 0, '', '', '', '', ?, '', '', '', ?, ?, '')
                    """,
                    [
                        (
                            "thread-1",
                            "C:\\Users\\me\\.codex\\sessions\\one.jsonl",
                            10,
                            "vscode",
                            "\\\\?\\E:\\Dev\\One",
                            "Old thread",
                            "Old prompt",
                            "gpt-5.4",
                            "high",
                        ),
                        (
                            "thread-2",
                            "C:\\Users\\me\\.codex\\sessions\\two.jsonl",
                            20,
                            "vscode",
                            "\\\\?\\E:\\Dev\\Two",
                            "Newest thread",
                            "Newest thread",
                            "gpt-5.4",
                            "xhigh",
                        ),
                    ],
                )
                connection.commit()
            finally:
                connection.close()

            repository = ThreadRepository(db_path)
            thread = repository.get_latest_thread()

            self.assertIsNotNone(thread)
            self.assertEqual(thread.id, "thread-2")
            self.assertEqual(thread.cwd, "E:\\Dev\\Two")
            self.assertEqual(thread.title, "Newest thread")

    def test_ignores_non_vscode_rows_and_empty_rollout_path(self) -> None:
        with self.tempdir() as tmpdir:
            db_path = Path(tmpdir) / "state_5.sqlite"
            self.create_database(db_path)
            connection = sqlite3.connect(db_path)
            try:
                connection.executemany(
                    """
                    INSERT INTO threads (
                        id, rollout_path, created_at, updated_at, source, model_provider, cwd,
                        title, sandbox_policy, approval_mode, tokens_used, has_user_event,
                        archived, archived_at, git_sha, git_branch, git_origin_url, cli_version,
                        first_user_message, agent_nickname, agent_role, memory_mode, model,
                        reasoning_effort, agent_path
                    ) VALUES (?, ?, 0, ?, ?, '', ?, ?, '', '', 0, 0, 0, 0, '', '', '', '', ?, '', '', '', ?, ?, '')
                    """,
                    [
                        (
                            "thread-1",
                            "",
                            20,
                            "vscode",
                            "E:\\Dev\\Skip",
                            "Missing rollout",
                            "Prompt 1",
                            "gpt-5.4",
                            "high",
                        ),
                        (
                            "thread-2",
                            "C:\\rollout.jsonl",
                            30,
                            "cli",
                            "E:\\Dev\\Skip",
                            "Not vscode",
                            "Prompt 2",
                            "gpt-5.4",
                            "high",
                        ),
                    ],
                )
                connection.commit()
            finally:
                connection.close()

            repository = ThreadRepository(db_path)
            self.assertIsNone(repository.get_latest_thread())
