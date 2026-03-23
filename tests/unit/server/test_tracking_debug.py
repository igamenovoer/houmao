from __future__ import annotations

from pathlib import Path

import pytest

from houmao.server.tracking_debug import (
    TRACKING_DEBUG_ROOT_ENV_VAR,
    TrackingDebugSink,
    tracking_debug_root_from_env,
)


def test_tracking_debug_root_from_env_is_disabled_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(TRACKING_DEBUG_ROOT_ENV_VAR, raising=False)

    assert tracking_debug_root_from_env() is None
    assert TrackingDebugSink.from_env() is None


def test_tracking_debug_sink_from_env_writes_structured_ndjson(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(TRACKING_DEBUG_ROOT_ENV_VAR, str(tmp_path / "trace-root"))

    sink = TrackingDebugSink.from_env()

    assert sink is not None
    sink.emit(stream="tracker-cycle", event_type="cycle_started", monotonic_ts=10.0, data={"x": 1})
    payload = (tmp_path / "trace-root" / "events" / "tracker-cycle.ndjson").read_text(
        encoding="utf-8"
    )

    assert '"event_type": "cycle_started"' in payload
    assert '"monotonic_ts": 10.0' in payload
