"""Opt-in structured tracing for server-owned live TUI lifecycle debugging."""

from __future__ import annotations

import json
import os
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

TRACKING_DEBUG_ROOT_ENV_VAR = "HOUMAO_TRACKING_DEBUG_ROOT"


def tracking_debug_root_from_env() -> Path | None:
    """Return the enabled tracking-debug root from the environment."""

    raw = os.environ.get(TRACKING_DEBUG_ROOT_ENV_VAR)
    if raw is None or not raw.strip():
        return None
    return Path(raw).expanduser().resolve()


class TrackingDebugSink:
    """Append structured tracking-debug events under one run-scoped root."""

    def __init__(self, *, root: Path) -> None:
        """Initialize the debug sink."""

        self.m_root = root.resolve()
        self.m_events_dir = (self.m_root / "events").resolve()
        self.m_lock = threading.RLock()
        self.m_event_seq = 0
        self.m_events_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_env(cls) -> "TrackingDebugSink | None":
        """Build one sink from the current environment when enabled."""

        root = tracking_debug_root_from_env()
        if root is None:
            return None
        return cls(root=root)

    @property
    def root(self) -> Path:
        """Return the resolved run-scoped debug root."""

        return self.m_root

    def emit(
        self,
        *,
        stream: str,
        event_type: str,
        monotonic_ts: float | None = None,
        terminal_id: str | None = None,
        tracked_session_id: str | None = None,
        tool: str | None = None,
        cycle_seq: int | None = None,
        anchor_id: int | None = None,
        data: dict[str, object] | None = None,
    ) -> None:
        """Append one structured event to the selected NDJSON stream."""

        with self.m_lock:
            self.m_event_seq += 1
            payload: dict[str, Any] = {
                "event_id": self.m_event_seq,
                "ts_utc": _utc_now_iso(),
                "event_type": event_type,
                "monotonic_ts": monotonic_ts,
                "terminal_id": terminal_id,
                "tracked_session_id": tracked_session_id,
                "tool": tool,
                "cycle_seq": cycle_seq,
                "anchor_id": anchor_id,
                "data": data or {},
            }
            stream_path = (self.m_events_dir / f"{stream}.ndjson").resolve()
            stream_path.parent.mkdir(parents=True, exist_ok=True)
            with stream_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, sort_keys=True, default=_json_default) + "\n")


def _utc_now_iso() -> str:
    """Return one current UTC timestamp string."""

    return datetime.now(UTC).isoformat(timespec="milliseconds")


def _json_default(value: object) -> str:
    """Return one conservative JSON fallback string."""

    return str(value)
