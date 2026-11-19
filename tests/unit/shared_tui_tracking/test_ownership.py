"""Verify gateway terminal polling restores the owner-selected tmux server."""

from __future__ import annotations

from threading import Event

import pytest

from houmao.execution.tmux import current_tmux_socket_path, tmux_server_scope
from houmao.server.models import HoumaoTrackedSessionIdentity
from houmao.shared_tui_tracking import ownership


def test_background_terminal_poll_uses_saved_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    """The tracking worker probes its own socket independently of the caller context."""

    seen: list[tuple[str, str | None]] = []
    polled = Event()

    def observe_tmux(*, session_name: str) -> bool:
        """Capture the actual worker context without creating a tmux server."""

        seen.append((session_name, current_tmux_socket_path()))
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
    )
    with tmux_server_scope("/example/caller.sock"):
        tracker.start()
        try:
            assert polled.wait(timeout=2)
        finally:
            tracker.stop()
        assert current_tmux_socket_path() == "/example/caller.sock"
    assert seen[0] == ("agent", "/example/owner.sock")
