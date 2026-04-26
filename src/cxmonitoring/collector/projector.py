from __future__ import annotations

import json
import logging
from typing import Any

from .models import (
    ActiveTool,
    CommandState,
    CurrentThreadSnapshot,
    ThreadRecord,
    TimelineEntry,
    TokenUsage,
    epoch_to_iso,
    normalize_timestamp,
)


def summarize_text(value: Any, limit: int = 240) -> str:
    text = " ".join(str(value or "").split())
    if not text:
        return ""
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def _duration_to_seconds(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dict):
        secs = float(value.get("secs", 0))
        nanos = float(value.get("nanos", 0))
        return round(secs + nanos / 1_000_000_000, 3)
    return None


def _first_meaningful_line(value: str | None) -> str | None:
    if not value:
        return None
    for line in value.splitlines():
        cleaned = line.strip()
        if cleaned:
            return cleaned
    return None


class RolloutProjector:
    def __init__(self, timeline_limit: int = 20) -> None:
        self._timeline_limit = timeline_limit
        self._logger = logging.getLogger(__name__)
        self.unknown_event_count = 0

    def create_snapshot(self, thread: ThreadRecord) -> CurrentThreadSnapshot:
        return CurrentThreadSnapshot(
            thread_id=thread.id,
            title=thread.title,
            cwd=thread.cwd,
            source=thread.source,
            rollout_path=thread.rollout_path,
            status="unknown",
            updated_at=thread.updated_at,
        )

    def _choice_metadata(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        choices = self._normalize_choices(payload.get("choices") or payload.get("options"))
        if not choices:
            return None

        metadata: dict[str, Any] = {"choices": choices}
        prompt = payload.get("message") or payload.get("prompt") or payload.get("question")
        if prompt:
            metadata["prompt"] = prompt

        request_id = payload.get("request_id") or payload.get("call_id") or payload.get("id")
        if request_id is not None:
            metadata["request_id"] = str(request_id)
        return metadata

    def _normalize_choices(self, value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []

        normalized: list[dict[str, Any]] = []
        for item in value:
            normalized_item = self._normalize_choice_item(item)
            if normalized_item is not None:
                normalized.append(normalized_item)
        return normalized

    def _normalize_choice_item(self, value: Any) -> dict[str, Any] | None:
        if isinstance(value, str):
            text = summarize_text(value, 120)
            if not text:
                return None
            return {"label": text, "value": text}

        if isinstance(value, dict):
            label = value.get("label") or value.get("text") or value.get("title") or value.get("value")
            choice_value = value.get("value") or value.get("label") or value.get("text") or value.get("title")
            if label is None and choice_value is None:
                return None

            normalized: dict[str, Any] = {
                "label": str(label or choice_value).strip(),
                "value": str(choice_value or label).strip(),
            }
            for key in ("id", "reply_to", "replyTo", "request_id"):
                if value.get(key) is not None:
                    normalized[key] = value.get(key)
            return normalized

        text = summarize_text(value, 120)
        if not text:
            return None
        return {"label": text, "value": text}

    def apply_event(
        self, snapshot: CurrentThreadSnapshot, event: dict[str, Any]
    ) -> list[TimelineEntry]:
        timeline_entries: list[TimelineEntry] = []
        timestamp = normalize_timestamp(event.get("timestamp")) or snapshot.updated_at
        payload = event.get("payload") or {}
        outer_type = event.get("type")
        inner_type = payload.get("type")

        if timestamp:
            snapshot.last_event_at = timestamp
            snapshot.updated_at = timestamp

        if outer_type == "event_msg":
            self._apply_event_message(snapshot, payload, inner_type, timestamp, timeline_entries)
        elif outer_type == "response_item":
            self._apply_response_item(snapshot, payload, inner_type, timestamp, timeline_entries)
        elif outer_type in {"session_meta", "turn_context", "compacted"}:
            pass
        else:
            self._mark_unknown(outer_type, inner_type)

        for entry in timeline_entries:
            snapshot.timeline.append(entry)
        if len(snapshot.timeline) > self._timeline_limit:
            snapshot.timeline = snapshot.timeline[-self._timeline_limit :]
        return timeline_entries

    def _apply_event_message(
        self,
        snapshot: CurrentThreadSnapshot,
        payload: dict[str, Any],
        inner_type: str | None,
        timestamp: str | None,
        timeline_entries: list[TimelineEntry],
    ) -> None:
        if inner_type == "task_started":
            snapshot.status = "running"
            snapshot.turn_id = payload.get("turn_id")
            snapshot.started_at = epoch_to_iso(payload.get("started_at")) or timestamp
            snapshot.collaboration_mode = payload.get("collaboration_mode_kind")
            summary = "Codex started a new task."
            if snapshot.collaboration_mode:
                summary = f"Codex started a new task in {snapshot.collaboration_mode} mode."
            timeline_entries.append(
                self._timeline(timestamp, "status", "Task started", summary, "running")
            )
            return

        if inner_type in {"choice_request", "decision_request"}:
            message = payload.get("message") or payload.get("prompt") or payload.get("question")
            metadata = self._choice_metadata(payload)
            prompt_source = message
            if prompt_source is None and metadata:
                prompt_source = metadata.get("prompt")
            prompt = str(prompt_source or "Choose a reply.")
            snapshot.last_agent_message = prompt
            timeline_entries.append(
                self._timeline(
                    timestamp,
                    "choice",
                    "Decision needed",
                    summarize_text(prompt),
                    payload.get("phase"),
                    details=prompt,
                    metadata=metadata,
                )
            )
            return

        if inner_type == "agent_message":
            metadata = self._choice_metadata(payload)
            message = (
                payload.get("message")
                or payload.get("prompt")
                or payload.get("question")
                or (metadata.get("prompt") if metadata else None)
                or ("Choose a reply." if metadata else None)
            )
            if message:
                message_text = str(message)
                snapshot.last_agent_message = message_text
                kind = "choice" if metadata else "agent"
                label = "Decision needed" if kind == "choice" else "Codex"
                timeline_entries.append(
                    self._timeline(
                        timestamp,
                        kind,
                        label,
                        summarize_text(message_text),
                        payload.get("phase"),
                        details=message_text,
                        metadata=metadata,
                    )
                )
            return

        if inner_type == "user_message":
            message = payload.get("message")
            if message:
                message_text = str(message)
                snapshot.last_user_message = summarize_text(message_text)
                timeline_entries.append(
                    self._timeline(
                        timestamp,
                        "user",
                        "Prompt",
                        summarize_text(message_text),
                        None,
                        details=message_text,
                    )
                )
            return

        if inner_type == "exec_command_end":
            command = self._parse_command(payload, timestamp)
            snapshot.last_command = command
            timeline_entries.append(
                self._timeline(
                    timestamp,
                    "command",
                    "Command",
                    command.summary or command.command or "Command executed",
                    command.status,
                )
            )
            return

        if inner_type == "patch_apply_end":
            summary = self._patch_summary(payload)
            snapshot.last_tool_output_summary = summary
            if snapshot.active_tool and payload.get("call_id") == snapshot.active_tool.call_id:
                snapshot.active_tool.status = "completed" if payload.get("success") else "failed"
                snapshot.active_tool.summary = summary
            timeline_entries.append(
                self._timeline(
                    timestamp,
                    "patch",
                    "Patch",
                    summary,
                    "completed" if payload.get("success") else "failed",
                )
            )
            return

        if inner_type == "token_count":
            token_usage = self._parse_token_usage(payload)
            if token_usage:
                snapshot.token_usage = token_usage
            return

        if inner_type == "task_complete":
            snapshot.status = "complete"
            message = payload.get("last_agent_message")
            if message:
                snapshot.last_agent_message = message
            timeline_entries.append(
                self._timeline(
                    timestamp,
                    "status",
                    "Task complete",
                    summarize_text(message or "Codex completed the task."),
                    "complete",
                )
            )
            return

        if inner_type == "turn_aborted":
            snapshot.status = "aborted"
            timeline_entries.append(
                self._timeline(
                    timestamp,
                    "status",
                    "Task aborted",
                    "The current turn was aborted.",
                    "aborted",
                )
            )
            return

        if inner_type in {"thread_rolled_back", "item_completed"}:
            return

        self._mark_unknown("event_msg", inner_type)

    def _apply_response_item(
        self,
        snapshot: CurrentThreadSnapshot,
        payload: dict[str, Any],
        inner_type: str | None,
        timestamp: str | None,
        timeline_entries: list[TimelineEntry],
    ) -> None:
        if inner_type in {"function_call", "custom_tool_call"}:
            tool = self._parse_tool_call(payload, timestamp)
            snapshot.active_tool = tool
            timeline_entries.append(
                self._timeline(
                    timestamp,
                    "tool",
                    "Tool",
                    tool.summary or tool.name or "Tool invoked",
                    tool.status,
                )
            )
            return

        if inner_type in {"function_call_output", "custom_tool_call_output"}:
            summary = self._tool_output_summary(payload)
            snapshot.last_tool_output_summary = summary
            if snapshot.active_tool and payload.get("call_id") == snapshot.active_tool.call_id:
                snapshot.active_tool.status = "completed"
                snapshot.active_tool.summary = summary
            timeline_entries.append(
                self._timeline(timestamp, "tool", "Tool output", summary, "completed")
            )
            return

        if inner_type in {"reasoning", "message"}:
            return

        self._mark_unknown("response_item", inner_type)

    def _parse_command(
        self, payload: dict[str, Any], timestamp: str | None
    ) -> CommandState:
        command_text = self._command_text(payload)
        exit_code = payload.get("exit_code")
        status = payload.get("status")
        if status is None:
            status = "completed" if exit_code in {0, None} else "failed"
        duration_seconds = _duration_to_seconds(payload.get("duration"))

        summary = command_text or "Command executed"
        if status == "failed":
            summary = f"{command_text or 'Command'} failed"
            if exit_code is not None:
                summary += f" with exit code {exit_code}"
            output_line = _first_meaningful_line(
                payload.get("formatted_output")
                or payload.get("aggregated_output")
                or payload.get("stderr")
            )
            if output_line:
                summary = f"{summary}: {summarize_text(output_line, 120)}"
        elif duration_seconds is not None:
            summary = f"{command_text or 'Command'} completed in {duration_seconds:.2f}s"

        return CommandState(
            command=command_text,
            exit_code=exit_code,
            duration_seconds=duration_seconds,
            status=status,
            summary=summary,
            ts=timestamp,
        )

    def _parse_tool_call(
        self, payload: dict[str, Any], timestamp: str | None
    ) -> ActiveTool:
        name = payload.get("name")
        status = payload.get("status") or "running"
        if payload.get("type") == "function_call":
            status = "pending"
        summary = f"{name or 'Tool'} {status}"
        return ActiveTool(
            name=name,
            call_id=payload.get("call_id"),
            status=status,
            summary=summary,
            ts=timestamp,
        )

    def _tool_output_summary(self, payload: dict[str, Any]) -> str:
        output = payload.get("output")
        if isinstance(output, str):
            try:
                parsed = json.loads(output)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, dict):
                text = parsed.get("output")
                if text:
                    return summarize_text(_first_meaningful_line(text) or text)
        if isinstance(output, str):
            return summarize_text(_first_meaningful_line(output) or output)
        return "Tool produced output."

    def _patch_summary(self, payload: dict[str, Any]) -> str:
        changes = payload.get("changes") or {}
        changed_files = len(changes)
        if payload.get("success"):
            if changed_files == 1:
                return "Patched 1 file successfully."
            if changed_files > 1:
                return f"Patched {changed_files} files successfully."
            return "Patch applied successfully."
        if changed_files:
            return f"Patch failed after touching {changed_files} files."
        return "Patch application failed."

    def _parse_token_usage(self, payload: dict[str, Any]) -> TokenUsage | None:
        info = payload.get("info") or {}
        usage = info.get("total_token_usage") or info.get("last_token_usage")
        if not usage:
            return None
        return TokenUsage(
            input_tokens=usage.get("input_tokens"),
            cached_input_tokens=usage.get("cached_input_tokens"),
            output_tokens=usage.get("output_tokens"),
            reasoning_output_tokens=usage.get("reasoning_output_tokens"),
            total_tokens=usage.get("total_tokens"),
            model_context_window=info.get("model_context_window"),
        )

    def _command_text(self, payload: dict[str, Any]) -> str | None:
        parsed = payload.get("parsed_cmd") or []
        if parsed and isinstance(parsed[0], dict):
            command = parsed[0].get("cmd")
            if command:
                return command
        raw_command = payload.get("command")
        if isinstance(raw_command, list):
            return " ".join(str(part) for part in raw_command)
        if isinstance(raw_command, str):
            return raw_command
        return None

    def _timeline(
        self,
        timestamp: str | None,
        kind: str,
        label: str,
        summary: str,
        raw_status: str | None,
        *,
        details: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TimelineEntry:
        return TimelineEntry(
            ts=timestamp or "",
            kind=kind,
            label=label,
            summary=summary,
            raw_status=raw_status,
            details=details,
            metadata=metadata,
        )

    def _mark_unknown(self, outer_type: str | None, inner_type: str | None) -> None:
        self.unknown_event_count += 1
        self._logger.debug(
            "Ignoring unknown rollout event",
            extra={"outer_type": outer_type, "inner_type": inner_type},
        )
