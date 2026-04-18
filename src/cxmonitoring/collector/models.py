from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

SnapshotStatus = Literal["idle", "running", "complete", "aborted", "unknown"]


def utc_now_iso() -> str:
    return datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")


def epoch_to_iso(value: int | float | None) -> str | None:
    if value is None:
        return None
    return datetime.fromtimestamp(float(value), tz=UTC).isoformat().replace("+00:00", "Z")


def normalize_timestamp(value: str | None) -> str | None:
    if not value:
        return None
    if value.endswith("Z"):
        return value
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return value
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).isoformat().replace("+00:00", "Z")


def normalize_windows_path(value: str | None) -> str | None:
    if not value:
        return value
    if value.startswith("\\\\?\\"):
        return value[4:]
    return value


@dataclass(slots=True)
class ThreadRecord:
    id: str
    title: str | None
    source: str | None
    cwd: str | None
    rollout_path: str
    updated_at: str | None
    model: str | None
    reasoning_effort: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ActiveTool:
    name: str | None = None
    call_id: str | None = None
    status: str | None = None
    summary: str | None = None
    ts: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class CommandState:
    command: str | None = None
    exit_code: int | None = None
    duration_seconds: float | None = None
    status: str | None = None
    summary: str | None = None
    ts: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class TokenUsage:
    input_tokens: int | None = None
    cached_input_tokens: int | None = None
    output_tokens: int | None = None
    reasoning_output_tokens: int | None = None
    total_tokens: int | None = None
    model_context_window: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class TimelineEntry:
    ts: str
    kind: str
    label: str
    summary: str
    raw_status: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class CurrentThreadSnapshot:
    thread_id: str | None = None
    turn_id: str | None = None
    title: str | None = None
    cwd: str | None = None
    source: str | None = None
    rollout_path: str | None = None
    status: SnapshotStatus = "idle"
    started_at: str | None = None
    updated_at: str | None = None
    last_event_at: str | None = None
    collaboration_mode: str | None = None
    last_user_message: str | None = None
    last_agent_message: str | None = None
    active_tool: ActiveTool | None = None
    last_command: CommandState | None = None
    last_tool_output_summary: str | None = None
    token_usage: TokenUsage | None = None
    timeline: list[TimelineEntry] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class MonitorHealth:
    state_db_path: str
    logs_db_path: str
    rollout_path: str | None = None
    current_thread_id: str | None = None
    last_thread_refresh_at: str | None = None
    last_rollout_read_at: str | None = None
    last_successful_event_at: str | None = None
    last_error: str | None = None
    subscriber_count: int = 0
    unknown_event_count: int = 0
    status: str = "idle"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class StreamEvent:
    event: str
    payload: dict[str, Any]
