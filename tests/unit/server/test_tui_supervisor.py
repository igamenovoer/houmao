from __future__ import annotations

from pathlib import Path

import pytest

from houmao.server.tui.registry import KnownSessionRecord
from houmao.server.tui.supervisor import SessionWatchWorker, TuiTrackingSupervisor


class _RuntimeDouble:
    def __init__(self) -> None:
        self.m_live_sessions: dict[str, KnownSessionRecord] = {}
        self.m_ensured: list[str] = []
        self.m_polled: list[str] = []

    def watch_poll_interval_seconds(self) -> float:
        return 0.1

    def load_live_known_sessions(self) -> dict[str, KnownSessionRecord]:
        return dict(self.m_live_sessions)

    def ensure_known_session(self, record: KnownSessionRecord) -> None:
        self.m_ensured.append(record.tracked_session_id)

    def poll_known_session(self, tracked_session_id: str) -> bool:
        self.m_polled.append(tracked_session_id)
        return True


def _record(tmp_path: Path) -> KnownSessionRecord:
    return KnownSessionRecord(
        tracked_session_id="cao-gpu",
        session_name="cao-gpu",
        tool="codex",
        terminal_id="abcd1234",
        tmux_session_name="AGENTSYS-gpu",
        tmux_window_name="developer-1",
        manifest_path=(tmp_path / "manifest.json").resolve(),
        session_root=(tmp_path / "session-root").resolve(),
        agent_name="AGENTSYS-gpu",
        agent_id="AGENTSYS-gpu",
    )


def test_supervisor_reconciles_worker_lifecycle(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    started: list[str] = []
    stopped: list[str] = []

    monkeypatch.setattr(
        SessionWatchWorker,
        "start",
        lambda self: started.append(self.m_tracked_session_id),
    )
    monkeypatch.setattr(
        SessionWatchWorker,
        "stop",
        lambda self, *, join=True: stopped.append(self.m_tracked_session_id),
    )
    monkeypatch.setattr(SessionWatchWorker, "is_alive", lambda self: True)

    runtime = _RuntimeDouble()
    supervisor = TuiTrackingSupervisor(runtime=runtime)
    runtime.m_live_sessions = {"cao-gpu": _record(tmp_path)}

    supervisor._reconcile_once()
    runtime.m_live_sessions = {}
    supervisor._reconcile_once()

    assert runtime.m_ensured == ["cao-gpu"]
    assert started == ["cao-gpu"]
    assert stopped == ["cao-gpu"]
