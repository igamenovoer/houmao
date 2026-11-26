"""Verify gateway terminal polling restores the owner-selected tmux server."""

from __future__ import annotations

from threading import Event
from unittest.mock import patch

import pytest

from houmao.agents.realm_controller.boundary_models import SessionManifestTmuxSectionV1
from houmao.execution.tmux import (
    TmuxPaneRecord,
    TmuxServer,
    TmuxObservationUnavailable,
    current_tmux_socket_path,
    tmux_server_scope,
)
from houmao.server.models import HoumaoTrackedSessionIdentity
from houmao.server.tui.process import PaneProcessInspection
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


@pytest.mark.parametrize(
    ("observed_version", "qualified"),
    [("2.0.99", False), (None, False), ("dev-build", False), ("2.1.1", True), ("9.0.0", True)],
)
def test_saved_pane_observation_requires_qualified_detector_version(
    monkeypatch: pytest.MonkeyPatch, observed_version: str | None, qualified: bool
) -> None:
    """Observe the recorded pane and pass the selected version to the real parser."""

    binding = SessionManifestTmuxSectionV1(
        session_name="agent",
        socket_path="/example/owner.sock",
        primary_window_id="@4",
        primary_pane_id="%2",
    )
    primary = TmuxPaneRecord(
        session_name="agent",
        window_id="@4",
        window_index="0",
        window_name="agent",
        pane_index="0",
        pane_id="%2",
        pane_pid=123,
        pane_active=False,
        pane_dead=False,
    )
    neighbor = TmuxPaneRecord(
        session_name="agent",
        window_id="@4",
        window_index="0",
        window_name="agent",
        pane_index="1",
        pane_id="%3",
        pane_pid=124,
        pane_active=True,
        pane_dead=False,
    )

    def observe(server: TmuxServer, session_name: str) -> tuple[TmuxPaneRecord, ...]:
        assert server.socket_path == binding.socket_path
        assert session_name == binding.session_name
        return (neighbor, primary)

    monkeypatch.setattr(TmuxServer, "observe_session", observe)
    runtime = ownership.SingleSessionTrackingRuntime(
        identity=HoumaoTrackedSessionIdentity(
            tracked_session_id="test",
            tool="kimi",
            session_name="agent",
            tmux_session_name="agent",
            observed_tool_version=observed_version,
        ),
        primary_binding=binding,
    )
    with (
        patch.object(
            runtime.m_process_inspector,
            "inspect",
            return_value=PaneProcessInspection(
                process_state="tui_up", matched_process_names=("kimi",), matched_processes=()
            ),
        ) as inspect,
        patch.object(runtime.m_transport_resolver, "capture_text", return_value="") as capture,
        patch.object(
            runtime.m_parser_adapter, "parse", wraps=runtime.m_parser_adapter.parse
        ) as parse,
    ):
        state = runtime.refresh_once()

    inspect.assert_called_once_with(tool="kimi", pane_pid=123)
    assert state.probe_snapshot is not None and state.probe_snapshot.pane_id == "%2"
    if qualified:
        assert state.diagnostics.availability == "available"
        assert state.parsed_surface is not None
        assert state.parsed_surface.parser_preset_version == "2.1.x"
        parse.assert_called_once_with(
            tool="kimi", output_text="", baseline_pos=0, detector_version="2.1.x"
        )
    else:
        assert state.diagnostics.availability == "error"
        assert state.diagnostics.parse_error is not None
        assert state.diagnostics.parse_error.kind == "unsupported_tool_version"
        assert state.parsed_surface is None
        capture.assert_not_called()
        parse.assert_not_called()
