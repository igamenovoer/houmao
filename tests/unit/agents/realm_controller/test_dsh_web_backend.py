"""Verify semantic Web output and exact supervisor cleanup authority."""

from pathlib import Path
import threading
import time
from unittest.mock import Mock

import pytest

import houmao.agents.realm_controller.backends.dsh_web as backend_module
from houmao.agents.realm_controller.backends.dsh_web import DshWebSession, DshWebSessionState
from houmao.agents.realm_controller.backends.dispatch_control import HeadlessDispatchControl
from houmao.agents.realm_controller.errors import BackendExecutionError


def test_native_tool_output_remains_a_tool_result_in_its_claimed_turn() -> None:
    """Tool text cannot become fabricated assistant output or a later human result."""

    session = DshWebSession()
    session.m_state = Mock(
        spec=DshWebSessionState, web_identity={"native_session_id": "native"}, turn_index=2
    )
    entry = {
        "type": "tool/result",
        "turn": 3,
        "native_sequence": 15,
        "call_id": "call-1",
        "name": "bash",
        "content": [{"type": "text", "text": "controlled tool stdout"}],
        "is_error": False,
    }
    events = session._semantic_events(entry, {3})
    assert [event.kind for event in events] == ["tool_result"]
    assert events[0].payload["content"] == entry["content"]
    assert events[0].payload["native_turn"] == 3
    assert session._semantic_events({**entry, "turn": 4}, {3}) == []


def test_supervisor_pid_reuse_never_authorizes_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A private artifact cannot authorize signalling a replacement PID."""

    path = tmp_path / "supervisor.json"
    path.write_text('{"supervisor_pid": 12345, "supervisor_birth_token": "original"}')
    monkeypatch.setattr(backend_module, "_dispatch_origin_birth_token", lambda _: "replacement")
    signal_process = Mock(side_effect=AssertionError("Never signal a replacement process"))
    monkeypatch.setattr(backend_module.os, "kill", signal_process)
    DshWebSession._stop_supervisor_file(path)
    signal_process.assert_not_called()


def test_changed_supervisor_marker_refuses_tmux_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Force cleanup cannot remove another session that reused the captured name."""

    session = DshWebSession()
    session.m_state = Mock(
        spec=DshWebSessionState,
        web_identity={"native_session_id": "native"},
        bootstrap_path=str(tmp_path / "bootstrap.json"),
        tmux_session_name="old-name",
        control_path=str(tmp_path / "control.json"),
    )
    session.m_client = Mock()
    session.configure_stop_force_cleanup(force_cleanup=True)
    monkeypatch.setattr(backend_module, "has_tmux_session", lambda **_: Mock(returncode=0))
    monkeypatch.setattr(
        backend_module, "run_tmux", lambda _: Mock(returncode=0, stdout="replacement")
    )
    remove_session = Mock(side_effect=AssertionError("Never remove a replacement session"))
    monkeypatch.setattr(backend_module, "kill_tmux_session", remove_session)
    result = session.terminate()
    assert result.status == "error"
    remove_session.assert_not_called()


def test_reconstruction_refuses_a_different_workspace_before_any_connection(tmp_path: Path) -> None:
    """A saved Web binding cannot be silently reused under another workspace."""

    plan = Mock(working_directory=tmp_path / "new-workspace")
    state = Mock(spec=DshWebSessionState, working_directory=str(tmp_path / "original"))
    with pytest.raises(BackendExecutionError, match="recorded workspace"):
        DshWebSession.from_launch_plan(
            launch_plan=plan,
            session_manifest_path=tmp_path / "manifest.json",
            role_name="controlled",
            state=state,
        )


def test_dispatch_cancellation_revokes_permission_without_waiting_for_http_lock(
    tmp_path: Path,
) -> None:
    """Caller cancellation is immediate even while native preparation owns the API lock."""

    control = HeadlessDispatchControl.from_callbacks(
        allowed=lambda: True, confirmed=lambda: None, deadline=time.monotonic() + 30
    )
    permission = control.prepare_bridge_permission(tmp_path)
    session = DshWebSession()
    session.m_state = Mock(spec=DshWebSessionState, web_identity={"native_session_id": "native"})
    entered, release, settled = threading.Event(), threading.Event(), threading.Event()

    def interrupt(*_args: object, **_kwargs: object) -> None:
        """Represent a client call waiting for an in-flight native prompt preparation."""

        entered.set()
        try:
            assert release.wait(5)
        finally:
            settled.set()

    session.m_client = Mock(interrupt=interrupt)
    session.m_active_operations[id(control)] = "original-operation"
    try:
        started = time.monotonic()
        session.cancel_request_dispatch(control)
        assert time.monotonic() - started < 0.5
        assert control.m_cancelled.is_set()
        assert '"active": false' in permission.read_text()
        assert entered.wait(1)
    finally:
        release.set()
        assert settled.wait(2)
