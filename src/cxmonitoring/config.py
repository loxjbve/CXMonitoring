from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class Settings:
    codex_home: Path
    state_db_path: Path
    logs_db_path: Path
    host: str = "0.0.0.0"
    port: int = 3180
    thread_poll_interval: float = 1.0
    rollout_poll_interval: float = 0.3
    timeline_limit: int = 20

    @property
    def static_dir(self) -> Path:
        return Path(__file__).resolve().parent / "static"

    @property
    def bridge_db_path(self) -> Path:
        return self.codex_home / "cxmonitoring_bridge.sqlite"

    @classmethod
    def from_env(cls) -> "Settings":
        codex_home = Path(
            os.environ.get("CXMONITORING_CODEX_HOME", str(Path.home() / ".codex"))
        ).expanduser()
        return cls(
            codex_home=codex_home,
            state_db_path=codex_home / "state_5.sqlite",
            logs_db_path=codex_home / "logs_2.sqlite",
            host=os.environ.get("CXMONITORING_HOST", "0.0.0.0"),
            port=int(os.environ.get("CXMONITORING_PORT", "3180")),
            thread_poll_interval=float(
                os.environ.get("CXMONITORING_THREAD_POLL", "1.0")
            ),
            rollout_poll_interval=float(
                os.environ.get("CXMONITORING_ROLLOUT_POLL", "0.3")
            ),
            timeline_limit=20,
        )
