"""Verify semantic Web output and exact supervisor cleanup authority."""

from pathlib import Path
import json
import shlex
import stat
import threading
import time
from types import SimpleNamespace
from unittest.mock import Mock
from urllib.parse import parse_qs, urlsplit

import pytest

import houmao.agents.realm_controller.backends.dsh_web as backend_module
from houmao.agents.realm_controller.backends.dsh_web import DshWebSession, DshWebSessionState
from houmao.agents.realm_controller.backends.dispatch_control import HeadlessDispatchControl
from houmao.agents.realm_controller.errors import BackendExecutionError
from houmao.agents.realm_controller.models import LaunchPlan, RoleInjectionPlan


@pytest.fixture
def browser_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[DshWebSession, Mock, Mock]:
    """Construct an owned DSH binding and a separate temporary browser verification peer."""

    bootstrap = tmp_path / "bootstrap.json"
    origin = "http://127.0.0.1:1234"
    bootstrap.write_text(json.dumps({"version": 1, "origin": origin, "launch_token": "private+"}))
    bootstrap.chmod(0o600)
    identity = {
        "protocol_version": 1,
        "agent_id": "agent",
        "runtime_session_id": "runtime",
        "generation": "generation",
        "host_incarnation": "host",
        "native_session_id": "session",
        "agent_incarnation": "native-agent",
    }
    session = DshWebSession()
    session.m_state = DshWebSessionState(
        origin=origin,
        web_identity=identity,
        bootstrap_path=str(bootstrap),
        cookie_path=str(tmp_path / "api-credential.json"),
        control_path=str(tmp_path / "control.json"),
        supervisor_pid=42,
        supervisor_birth_token="supervisor",
        tmux_session_name="owned",
        evidence_path=str(tmp_path / "evidence.jsonl"),
        working_directory=str(tmp_path),
        native_pid=43,
        native_birth_token="native",
    )
    session.m_client = Mock()
    independent = Mock(
        state=Mock(
            return_value={
                "identity": identity,
                "available": True,
                "browser_workspace_id": "owned-workspace",
            }
        )
    )
    connect = Mock(return_value=independent)
    listener = Mock(return_value=True)
    monkeypatch.setattr(backend_module, "_dispatch_origin_birth_token", lambda _: "supervisor")
    monkeypatch.setattr(backend_module, "owns_ipv4_web_listener", listener)
    monkeypatch.setattr(backend_module.DshWebClient, "from_connection", connect)
    return session, connect, listener


def test_browser_entry_verifies_the_bound_peer_without_mutating_programmatic_connection(
    browser_session: tuple[DshWebSession, Mock, Mock],
) -> None:
    """A busy but available native Agent supplies the root browser exchange independently."""

    session, connect, listener = browser_session
    existing = session.m_client
    peer = connect.return_value
    peer.state.return_value["active_turn"] = {"turn": 2}
    entry = session.browser_entry()
    location = urlsplit(entry.redirect_url(expected_origin=session.state.origin))
    assert location.path == "/" and parse_qs(location.query) == {"token": ["private+"]}
    assert parse_qs(location.fragment) == {"houmao-entry": ["native-agent"]}
    listener.assert_called_with(43, "native", 1234)
    peer.state.assert_called_once_with(session.state.web_identity)
    peer.close.assert_called_once_with()
    assert "cookie_file" not in connect.call_args.kwargs
    assert session.m_client is existing
    assert isinstance(existing, Mock) and existing.mock_calls == []
    assert not Path(session.state.cookie_path).exists()


def test_read_only_web_state_uses_an_unpersisted_peer(
    browser_session: tuple[DshWebSession, Mock, Mock],
) -> None:
    """Inspect the exact native state without replacing or persisting the control peer."""

    session, connect, listener = browser_session
    existing = session.m_client
    cookie_path = session.state.cookie_path
    peer = connect.return_value

    assert session.observe_web_state_read_only() == peer.state.return_value
    listener.assert_called_with(43, "native", 1234)
    peer.state.assert_called_once_with(session.state.web_identity)
    peer.close.assert_called_once_with()
    assert "cookie_file" not in connect.call_args.kwargs
    assert session.m_client is existing
    assert session.state.cookie_path == cookie_path
    assert not Path(cookie_path).exists()


def test_browser_entry_requires_current_workspace_membership(
    browser_session: tuple[DshWebSession, Mock, Mock],
) -> None:
    """Withhold the destination when the live session lacks verified native membership."""

    session, connect, _ = browser_session
    peer = connect.return_value
    peer.state.return_value["browser_workspace_id"] = None

    with pytest.raises(
        BackendExecutionError, match="Managed native Session membership could not be verified"
    ):
        session.browser_entry()

    peer.close.assert_called_once_with()


@pytest.mark.parametrize("failure", ["permissions", "symlink", "origin", "bootstrap_version"])
def test_browser_entry_refuses_unverified_bootstrap(
    browser_session: tuple[DshWebSession, Mock, Mock], failure: str, tmp_path: Path
) -> None:
    """Never read from another authority, expose a credential, or adopt another host."""

    session, connect, _ = browser_session
    bootstrap = Path(session.state.bootstrap_path)
    if failure == "permissions":
        bootstrap.chmod(0o644)
    elif failure == "symlink":
        secret = tmp_path / "private-source.json"
        bootstrap.rename(secret)
        bootstrap.symlink_to(secret)
    else:
        payload = json.loads(bootstrap.read_text())
        if failure == "origin":
            payload["origin"] = "http://127.0.0.1:1235"
        else:
            payload["version"] = True
        bootstrap.write_text(json.dumps(payload))
    with pytest.raises(BackendExecutionError, match="Private DSH Web bootstrap is unavailable"):
        session.browser_entry()
    connect.assert_not_called()


def test_browser_entry_refuses_replaced_listener_or_companion_identity(
    browser_session: tuple[DshWebSession, Mock, Mock],
) -> None:
    """Port reuse and a changed Agent incarnation both withdraw the destination."""

    session, connect, listener = browser_session
    listener.return_value = False
    with pytest.raises(BackendExecutionError, match="listener ownership changed"):
        session.browser_entry()
    connect.assert_not_called()

    listener.return_value = True
    peer = connect.return_value
    peer.state.return_value["identity"] = {**session.state.web_identity, "agent_incarnation": "new"}
    with pytest.raises(BackendExecutionError, match="execution identity changed"):
        session.browser_entry()
    peer.close.assert_called_once_with()


def test_startup_reports_redacted_exit_and_native_log(tmp_path: Path) -> None:
    """The supervisor reason stays useful without copying tokens or private keys into errors."""

    (tmp_path / "exit.json").write_text(
        json.dumps({"returncode": 1, "error": "Plugin failed to activate"}), encoding="utf-8"
    )
    (tmp_path / "bootstrap.json").write_text(
        json.dumps({"launch_token": "test-launch-secret"}), encoding="utf-8"
    )
    raw = "EADDRINUSE test-launch-secret API-Key: test-key\nCookie: value=private; other=secret"
    artifact = tmp_path / "native-private.log"
    artifact.write_text(raw, encoding="utf-8")
    for path in (tmp_path / "exit.json", tmp_path / "bootstrap.json", artifact):
        path.chmod(0o600)
    summary = backend_module._startup_failure_detail(tmp_path, ("test-key",))
    assert "native exit 1" in summary
    assert "Plugin failed to activate EADDRINUSE" in summary
    assert "[REDACTED]" in summary
    assert "test-launch-secret" not in summary and "test-key" not in summary
    assert "value=private" not in summary and "other=secret" not in summary
    assert "\n" not in summary
    assert artifact.read_text() == raw


def test_dsh_publishes_before_starting_private_supervisor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Home preparation preserves declared values while deriving DSH-owned paths."""

    setup = tmp_path / "tool-params.json"
    setup.write_text(
        json.dumps(
            {
                "provider": {
                    "adapter": "pi-ai",
                    "protocol": "openai-completions",
                    "route": "fixture",
                    "base_url_env": "OPENAI_BASE_URL",
                    "api_key_env": "OPENAI_API_KEY",
                },
                "models": [
                    {
                        "id": "fixture",
                        "context_window": 4096,
                        "max_output_tokens": 256,
                        "reasoning_efforts": False,
                    }
                ],
            }
        )
    )
    home = tmp_path / "home"
    (home / "skills").mkdir(parents=True)
    public_env = {"REVIEW_BASE_URL": "http://127.0.0.1:9876"}
    plan = LaunchPlan(
        backend="dsh_web",
        tool="dsh",
        executable="dsh",
        args=[],
        working_directory=tmp_path,
        home_path=home,
        home_env_var="DSH_HOME",
        env={
            **public_env,
            "OPENAI_BASE_URL": "http://127.0.0.1:8080/v1",
            "OPENAI_API_KEY": "synthetic-private",
        },
        env_var_names=["REVIEW_BASE_URL", "OPENAI_BASE_URL", "OPENAI_API_KEY"],
        public_env=public_env,
        private_env_var_names=frozenset({"OPENAI_API_KEY"}),
        role_injection=RoleInjectionPlan(
            method="native_home_system_prompt", role_name="r", prompt="role"
        ),
        metadata={
            "managed_web_identity": {
                "agent_id": "agent",
                "runtime_session_id": "runtime",
                "generation": "generation",
            },
            "dsh": {"setup_path": str(setup)},
        },
    )
    calls: list[str] = []

    def publish(*, session_name: str, launch_plan: LaunchPlan) -> None:
        assert session_name == "owned-test-web"
        assert launch_plan.public_env == public_env
        calls.append("publish")

    def run_tmux(args: list[str]) -> SimpleNamespace:
        if args[0] == "respawn-pane":
            calls.append("spawn")
            assert "synthetic-private" not in args[-1]
            artifact = Path(shlex.split(args[-1])[-1])
            assert stat.S_IMODE(artifact.stat().st_mode) == 0o600
            environment = json.loads(artifact.read_text())["environment"]
            assert environment["DSH_HOME"] == str(home)
            assert environment["DSH_AGENTS_HOME"] == str(home / "shared-agents")
            assert environment["REVIEW_BASE_URL"] == public_env["REVIEW_BASE_URL"]
            assert environment["OPENAI_API_KEY"] == "synthetic-private"
            return SimpleNamespace(returncode=1)
        return SimpleNamespace(returncode=0, stdout="")

    monkeypatch.setattr(
        backend_module.subprocess,
        "run",
        Mock(
            return_value=SimpleNamespace(
                stdout="0.2.2-rc.3\n",
            )
        ),
    )
    monkeypatch.setattr(
        backend_module, "has_tmux_session", lambda **_: SimpleNamespace(returncode=1)
    )
    monkeypatch.setattr(backend_module, "create_tmux_session", lambda **_: None)
    monkeypatch.setattr(
        backend_module,
        "prepare_headless_agent_window",
        lambda **_: SimpleNamespace(pane_id="%1", window_id="@1"),
    )
    monkeypatch.setattr(backend_module, "publish_tmux_launch_environment", publish)
    monkeypatch.setattr(backend_module, "run_tmux", run_tmux)
    with pytest.raises(BackendExecutionError, match="DSH Web supervisor could not start"):
        DshWebSession.from_launch_plan(
            launch_plan=plan,
            session_manifest_path=tmp_path / "manifest.json",
            role_name="r",
            provider_start=True,
            tmux_session_name="owned-test-web",
        )

    assert calls == ["publish", "spawn"]
    assert not list(home.glob("houmao-web/*/supervisor-input.json"))


def test_web_control_failure_exposes_code_and_sanitized_message(tmp_path: Path) -> None:
    """Surface the native admission diagnostic without mutating request accounting semantics."""

    session = DshWebSession()
    session.m_manifest_path = tmp_path / "manifest.json"
    identity = {"native_session_id": "native"}
    session.m_state = Mock(
        spec=DshWebSessionState, web_identity=identity, evidence_path="owned", turn_index=0
    )
    session.m_client = Mock(conversation=Mock(return_value={"current_cursor": 0}))
    session.m_usage_service = Mock()
    session.m_client.prompt.side_effect = backend_module.DshWebError(
        "not_ready", "Native request could not start. Authorization: Bearer synthetic-auth"
    )
    with pytest.raises(
        BackendExecutionError, match="not_ready: Native request could not start"
    ) as failed:
        session.send_web_prompt("prompt", turn_artifact_dir_name="test-turn")
    assert "[REDACTED]" in str(failed.value) and "synthetic-auth" not in str(failed.value)
    session.m_client.prompt.assert_called_once()


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


def test_refresh_uses_independent_authority_without_blocking_native_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A long refresh cannot claim the ordinary client's HTTP serialization lock."""

    bootstrap = tmp_path / "bootstrap.json"
    bootstrap.write_text('{"origin":"http://127.0.0.1:1234","launch_token":"synthetic-only"}')
    bootstrap.chmod(0o600)
    session = DshWebSession()
    identity = {"native_session_id": "native"}
    session.m_state = Mock(
        spec=DshWebSessionState,
        supervisor_pid=123,
        supervisor_birth_token="owned",
        bootstrap_path=str(bootstrap),
        origin="http://127.0.0.1:1234",
        web_identity=identity,
    )
    session.m_client = Mock(state=Mock(return_value={"available": True}))
    entered, release, finished = threading.Event(), threading.Event(), threading.Event()

    def native_refresh(*_args: object, **_kwargs: object) -> dict[str, str]:
        """Hold only the separately authenticated refresh connection."""

        entered.set()
        assert release.wait(3)
        return {"outcome": "refreshed"}

    independent = Mock(refresh_common_plugins=native_refresh)
    connect = Mock(return_value=independent)
    monkeypatch.setattr(backend_module, "_dispatch_origin_birth_token", lambda _: "owned")
    monkeypatch.setattr(backend_module.DshWebClient, "from_connection", connect)

    def request() -> None:
        """Complete the original operation without replay or connection borrowing."""

        try:
            assert session.refresh_common_plugins(2)["outcome"] == "refreshed"
        finally:
            finished.set()

    thread = threading.Thread(target=request)
    thread.start()
    try:
        assert entered.wait(1)
        started = time.monotonic()
        assert session.observe_web_state() == {"available": True}
        assert time.monotonic() - started < 0.2
    finally:
        release.set()
        thread.join(3)
    assert finished.is_set()
    independent.close.assert_called_once()
    connect.assert_called_once()
    assert connect.call_args.args == ("http://127.0.0.1:1234",)
    assert connect.call_args.kwargs["launch_token"] == "synthetic-only"
    assert 0 < connect.call_args.kwargs["timeout_seconds"] <= 2
    assert json.loads(bootstrap.read_text())["launch_token"] == "synthetic-only"
    session.m_client.refresh_common_plugins.assert_not_called()


def test_authentication_cannot_extend_native_refresh_deadline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An authenticated connection closes without mutation after its original budget."""

    bootstrap = tmp_path / "bootstrap.json"
    bootstrap.write_text('{"origin":"http://127.0.0.1:1234","launch_token":"synthetic-only"}')
    bootstrap.chmod(0o600)
    session = DshWebSession()
    session.m_state = Mock(
        spec=DshWebSessionState,
        supervisor_pid=123,
        supervisor_birth_token="owned",
        bootstrap_path=str(bootstrap),
        origin="http://127.0.0.1:1234",
        web_identity={"native_session_id": "native"},
    )
    clock = [100.0]
    monkeypatch.setattr(backend_module.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(backend_module, "_dispatch_origin_birth_token", lambda _: "owned")
    client = Mock()

    def authenticate(*_args: object, **kwargs: object) -> Mock:
        """Consume the whole original budget during synthetic authentication."""

        assert kwargs["timeout_seconds"] == 2.0
        clock[0] = 103.0
        return client

    monkeypatch.setattr(backend_module.DshWebClient, "from_connection", authenticate)
    with pytest.raises(backend_module.DshWebError) as expired:
        session.refresh_common_plugins(30, deadline_monotonic=102.0)
    assert expired.value.code == "expired"
    client.refresh_common_plugins.assert_not_called()
    client.close.assert_called_once()


def test_authentication_cannot_retarget_refresh_to_a_replacement_agent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An explicit native reset during authentication cannot receive stale work."""

    bootstrap = tmp_path / "bootstrap.json"
    bootstrap.write_text('{"origin":"http://127.0.0.1:1234","launch_token":"synthetic-only"}')
    bootstrap.chmod(0o600)
    session = DshWebSession()
    session.m_state = Mock(
        spec=DshWebSessionState,
        supervisor_pid=123,
        supervisor_birth_token="owned",
        bootstrap_path=str(bootstrap),
        origin="http://127.0.0.1:1234",
        web_identity={"native_session_id": "old"},
    )
    monkeypatch.setattr(backend_module, "_dispatch_origin_birth_token", lambda _: "owned")
    client = Mock()

    def authenticate(*_args: object, **_kwargs: object) -> Mock:
        """Publish a replacement exactly where the native owner connection waits."""

        session.state.web_identity = {"native_session_id": "replacement"}
        return client

    monkeypatch.setattr(backend_module.DshWebClient, "from_connection", authenticate)
    with pytest.raises(backend_module.DshWebError) as stale:
        session.refresh_common_plugins(5)
    assert stale.value.code == "stale_identity"
    client.refresh_common_plugins.assert_not_called()
    client.close.assert_called_once()


def test_captured_service_identity_is_checked_before_native_authentication(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A changed Agent between service preflight and backend entry cannot be selected."""

    session = DshWebSession()
    session.m_state = Mock(
        spec=DshWebSessionState,
        web_identity={"native_session_id": "replacement"},
    )
    connect = Mock(side_effect=AssertionError("No stale authentication"))
    monkeypatch.setattr(backend_module.DshWebClient, "from_connection", connect)
    with pytest.raises(backend_module.DshWebError) as stale:
        session.refresh_common_plugins(5, expected_identity={"native_session_id": "old"})
    assert stale.value.code == "stale_identity"
    connect.assert_not_called()
