from __future__ import annotations

from pathlib import Path
import time

import pytest

from houmao.server.tui.registry import KnownSessionRecord
from houmao.server.tui.supervisor import SessionWatchWorker, TuiTrackingSupervisor


class _RuntimeDouble:
    def __init__(self) -> None:
        self.m_live_sessions: dict[str, KnownSessionRecord] = {}
        self.m_ensured: list[str] = []
        self.m_polled: list[str] = []
        self.m_poll_errors: list[tuple[str, str]] = []
        self.m_released: list[str] = []
        self.m_interval_seconds = 0.01
        self.m_raise_poll_once = False
        self.m_raise_reconcile_once = False
        self.m_stop_after_success = False

    def watch_poll_interval_seconds(self) -> float:
        return self.m_interval_seconds

    def load_live_known_sessions(self) -> dict[str, KnownSessionRecord]:
        if self.m_raise_reconcile_once:
            self.m_raise_reconcile_once = False
            raise RuntimeError("boom")
        return dict(self.m_live_sessions)

    def ensure_known_session(self, record: KnownSessionRecord) -> None:
        self.m_ensured.append(record.tracked_session_id)

    def poll_known_session(self, tracked_session_id: str) -> bool:
        self.m_polled.append(tracked_session_id)
        if self.m_raise_poll_once:
            self.m_raise_poll_once = False
            raise RuntimeError("boom")
        if self.m_stop_after_success:
            return False
        return True

    def handle_poll_exception(self, tracked_session_id: str, exc: Exception) -> None:
        self.m_poll_errors.append((tracked_session_id, str(exc)))

    def release_known_session(self, tracked_session_id: str) -> None:
        self.m_released.append(tracked_session_id)


def _record(tmp_path: Path) -> KnownSessionRecord:
    return KnownSessionRecord(
        tracked_session_id="cao-gpu",
        session_name="cao-gpu",
        tool="codex",
        terminal_id="abcd1234",
        tmux_session_name="HOUMAO-gpu",
        tmux_window_name="developer-1",
        manifest_path=(tmp_path / "manifest.json").resolve(),
        session_root=(tmp_path / "session-root").resolve(),
        agent_name="HOUMAO-gpu",
        agent_id="HOUMAO-gpu",
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
    assert runtime.m_released == ["cao-gpu"]


def test_worker_survives_one_unexpected_poll_exception() -> None:
    runtime = _RuntimeDouble()
    runtime.m_raise_poll_once = True
    runtime.m_stop_after_success = True
    worker = SessionWatchWorker(runtime=runtime, tracked_session_id="cao-gpu")

    worker.start()
    deadline = time.monotonic() + 1.0
    while worker.is_alive() and time.monotonic() < deadline:
        time.sleep(0.01)

    assert worker.is_alive() is False
    assert runtime.m_poll_errors == [("cao-gpu", "boom")]
    assert runtime.m_polled == ["cao-gpu", "cao-gpu"]


def test_supervisor_survives_one_unexpected_reconcile_exception(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    started: list[str] = []

    monkeypatch.setattr(
        SessionWatchWorker,
        "start",
        lambda self: started.append(self.m_tracked_session_id),
    )
    monkeypatch.setattr(SessionWatchWorker, "stop", lambda self, *, join=True: None)
    monkeypatch.setattr(SessionWatchWorker, "is_alive", lambda self: True)

    runtime = _RuntimeDouble()
    runtime.m_raise_reconcile_once = True
    runtime.m_live_sessions = {"cao-gpu": _record(tmp_path)}
    supervisor = TuiTrackingSupervisor(runtime=runtime)

    supervisor.start()
    deadline = time.monotonic() + 1.0
    while not started and time.monotonic() < deadline:
        time.sleep(0.01)

    assert supervisor.m_thread.is_alive() is True
    assert started == ["cao-gpu"]

    supervisor.stop()
