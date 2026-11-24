"""Verify gateway terminal polling restores the owner-selected tmux server."""

from __future__ import annotations

from threading import Event

import pytest

from houmao.execution.tmux import (
    TmuxObservationUnavailable,
    current_tmux_socket_path,
    tmux_server_scope,
)
from houmao.server.models import HoumaoTrackedSessionIdentity
from houmao.shared_tui_tracking import ownership


def test_background_terminal_poll_retries_unavailable_saved_socket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The tracking worker survives a checked failure and retries the same owner socket."""

    seen: list[tuple[str, str | None]] = []
    polled = Event()

    def observe_tmux(*, session_name: str, allow_missing_server: bool) -> bool:
        """Capture the actual worker context without creating a tmux server."""

        assert allow_missing_server
        seen.append((session_name, current_tmux_socket_path()))
        if len(seen) == 1:
            raise TmuxObservationUnavailable("tmux exited with status 23", returncode=23)
        polled.set()
        return False

    monkeypatch.setattr(ownership, "tmux_session_exists", observe_tmux)
    tracker = ownership.SingleSessionTrackingRuntime(
        identity=HoumaoTrackedSessionIdentity(
            tracked_session_id="test",
            tool="kimi",
            session_name="agent",
            tmux_session_name="agent",
        ),
        tmux_socket_path="/example/owner.sock",
        watch_poll_interval_seconds=0.01,
    )
    with tmux_server_scope("/example/caller.sock"):
        tracker.start()
        try:
            assert polled.wait(timeout=2)
        finally:
            tracker.stop()
        assert current_tmux_socket_path() == "/example/caller.sock"
    assert seen[:2] == [("agent", "/example/owner.sock")] * 2
    assert tracker.current_state().diagnostics.transport_state == "tmux_missing"


def test_managed_terminal_tracking_with_no_socket_does_not_use_ambient_tmux(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _unexpected(**kwargs: object) -> bool:
        pytest.fail("Managed observation requires owner authority")

    monkeypatch.setattr(ownership, "tmux_session_exists", _unexpected)
    tracker = ownership.SingleSessionTrackingRuntime(
        identity=HoumaoTrackedSessionIdentity(
            tracked_session_id="test",
            tool="kimi",
            session_name="agent",
            tmux_session_name="agent",
            manifest_path="/example/managed/manifest.json",
        )
    )

    diagnostics = tracker.refresh_once().diagnostics

    assert diagnostics.transport_state == "probe_error"
    assert diagnostics.probe_error is not None
    assert "saved tmux socket" in diagnostics.probe_error.message
