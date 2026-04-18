from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cxmonitoring.collector.models import ThreadRecord
from cxmonitoring.collector.projector import RolloutProjector


class RolloutProjectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.projector = RolloutProjector(timeline_limit=20)
        self.thread = ThreadRecord(
            id="thread-1",
            title="Monitor current Codex task",
            source="vscode",
            cwd="E:\\Dev\\CXMonitoring",
            rollout_path="E:\\rollout.jsonl",
            updated_at="2026-04-14T15:12:41Z",
            model="gpt-5.4",
            reasoning_effort="xhigh",
        )
        self.snapshot = self.projector.create_snapshot(self.thread)

    def event(self, outer_type: str, inner_type: str, **payload: object) -> dict[str, object]:
        return {
            "timestamp": "2026-04-14T15:12:41.464Z",
            "type": outer_type,
            "payload": {"type": inner_type, **payload},
        }

    def test_task_started_sets_running_status(self) -> None:
        entries = self.projector.apply_event(
            self.snapshot,
            self.event(
                "event_msg",
                "task_started",
                turn_id="turn-1",
                started_at=1776179561,
                collaboration_mode_kind="plan",
            ),
        )

        self.assertEqual(self.snapshot.status, "running")
        self.assertEqual(self.snapshot.turn_id, "turn-1")
        self.assertEqual(self.snapshot.collaboration_mode, "plan")
        self.assertEqual(entries[0].label, "Task started")

    def test_agent_message_updates_progress(self) -> None:
        self.projector.apply_event(
            self.snapshot,
            self.event("event_msg", "agent_message", message="Scanning the repo structure now."),
        )

        self.assertEqual(self.snapshot.last_agent_message, "Scanning the repo structure now.")
        self.assertEqual(self.snapshot.timeline[-1].kind, "agent")

    def test_function_call_updates_active_tool(self) -> None:
        self.projector.apply_event(
            self.snapshot,
            self.event(
                "response_item",
                "function_call",
                name="shell_command",
                call_id="call-1",
            ),
        )

        self.assertIsNotNone(self.snapshot.active_tool)
        self.assertEqual(self.snapshot.active_tool.name, "shell_command")
        self.assertEqual(self.snapshot.active_tool.status, "pending")

    def test_exec_command_end_updates_last_command(self) -> None:
        self.projector.apply_event(
            self.snapshot,
            self.event(
                "event_msg",
                "exec_command_end",
                parsed_cmd=[{"cmd": "rg --files"}],
                exit_code=1,
                status="failed",
                duration={"secs": 0, "nanos": 120_000_000},
                stderr="No files found",
            ),
        )

        self.assertIsNotNone(self.snapshot.last_command)
        self.assertEqual(self.snapshot.last_command.command, "rg --files")
        self.assertEqual(self.snapshot.last_command.status, "failed")
        self.assertIn("failed", self.snapshot.last_command.summary)

    def test_patch_apply_end_sets_summary(self) -> None:
        self.projector.apply_event(
            self.snapshot,
            self.event(
                "event_msg",
                "patch_apply_end",
                success=True,
                changes={"a.py": {}, "b.py": {}},
                call_id="call-2",
            ),
        )

        self.assertEqual(self.snapshot.last_tool_output_summary, "Patched 2 files successfully.")
        self.assertEqual(self.snapshot.timeline[-1].kind, "patch")

    def test_task_complete_sets_final_message(self) -> None:
        self.projector.apply_event(
            self.snapshot,
            self.event(
                "event_msg",
                "task_complete",
                last_agent_message="Everything is wired up and verified.",
            ),
        )

        self.assertEqual(self.snapshot.status, "complete")
        self.assertEqual(self.snapshot.last_agent_message, "Everything is wired up and verified.")

    def test_turn_aborted_sets_aborted_status(self) -> None:
        self.projector.apply_event(self.snapshot, self.event("event_msg", "turn_aborted"))
        self.assertEqual(self.snapshot.status, "aborted")

    def test_unknown_event_is_ignored_without_crash(self) -> None:
        self.projector.apply_event(self.snapshot, self.event("event_msg", "unknown_thing"))
        self.assertEqual(self.projector.unknown_event_count, 1)

