"""Pin stock Kimi Web's check-and-send and exact native result semantics."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
import json
from pathlib import Path
import shlex
import stat
import time
from types import SimpleNamespace
from typing import Any
from urllib.parse import parse_qs, unquote, urlsplit

import pytest

from houmao.agents.realm_controller.backends.dispatch_control import HeadlessDispatchControl
from houmao.agents.realm_controller.backends.dsh_web_client import DshWebError
from houmao.agents.realm_controller.backends.kimi_web import (
    KimiWebSession,
    KimiWebSessionState,
    recover_kimi_web_prompt_result,
)
from houmao.agents.realm_controller.backends.kimi_web_client import KimiWebClient
from houmao.agents.realm_controller.errors import BackendExecutionError
from houmao.agents.realm_controller.gateway_models import GatewayAttachBackendMetadataWebV1
from houmao.agents.realm_controller.models import (
    LaunchPlan,
    RelaunchChatSessionSelection,
    RoleInjectionPlan,
    SessionControlResult,
)
from houmao.agents.realm_controller.web_observation import WebObservation
from houmao.hook_observation.kimi_journal import kimi_native_workspace_path


class _Native:
    """Model the bounded stock HTTP contract and an append-only native journal."""

    def __init__(self, journal: Path, workspace: Path) -> None:
        """Start with a known exact conversation and no active browser work."""

        self.m_journal: Path = journal
        self.m_workspace: Path = workspace
        self.m_busy: bool = False
        self.m_lose_response: bool = False
        self.m_refuse_preflight: bool = False
        self.m_abort_result: bool | DshWebError = True
        self.m_refuse_session_create: bool = False
        self.m_wrap_profile: bool = False
        self.m_activity_override: str | None = None
        self.m_pending_interaction: str = "none"
        self.m_calls: list[tuple[str, str]] = []
        self.m_permission: str = "manual"
        self.m_reported_permission: str | None = None
        self.m_host_incarnation: str = "host"

    @property
    def origin(self) -> str:
        """Return the only allowed test listener."""

        return "http://127.0.0.1:8080"

    def credential(self) -> str:
        """Provide synthetic sign-in bytes in place of a local token file."""

        return "native-token-with-+=padding"

    def append(self, *rows: dict[str, Any]) -> None:
        """Write native rows without coupling them to a gateway execution lifecycle."""

        with self.m_journal.open("a") as stream:
            for row in rows:
                stream.write(json.dumps({"agentId": "main", **row}) + "\n")

    def request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        *,
        before_send: Callable[[], None] | None = None,
    ) -> dict[str, Any]:
        """Return one exact receipt, optionally after the browser wins the race."""

        if before_send:
            before_send()
        self.m_calls.append((method, path))
        if (method, path) == ("GET", "/meta"):
            return {"server_id": self.m_host_incarnation}
        if (method, path) == ("POST", "/sessions") and self.m_refuse_session_create:
            raise DshWebError("invalid_request", "Native session API is unavailable")
        profile_update = (method, path) == ("POST", "/sessions/session_selected/profile")
        if profile_update:
            assert body is not None
            self.m_permission = body["agent_config"]["permission_mode"]
        if (method, path) in {
            ("GET", "/sessions/session_selected"),
            ("POST", "/sessions/session_selected/profile"),
            ("POST", "/sessions"),
        }:
            session = {
                "id": "session_selected",
                "archived": False,
                "pending_interaction": self.m_pending_interaction,
            }
            if self.m_wrap_profile:
                current_activity = "turn" if self.m_busy else "idle"
                session.update(
                    cwd=str(self.m_workspace),
                    activity=self.m_activity_override or current_activity,
                )
                if profile_update:
                    return {
                        "session": session,
                        "agent": {
                            "permission_mode": self.m_reported_permission or self.m_permission
                        },
                    }
            else:
                session.update(
                    metadata={"cwd": str(self.m_workspace)},
                    busy=self.m_busy,
                    main_turn_active=self.m_busy,
                )
            return session
        if method == "GET" and path.endswith("/prompts"):
            return {
                "active": None,
                "queued": ["browser pending"] if self.m_refuse_preflight else [],
            }
        if method == "POST" and path.endswith("/prompts"):
            assert body is not None
            self.write_turn("browser_prompt", 0, "unrelated browser text")
            prompt_id = body["prompt_id"]
            self.write_turn(prompt_id, 1, "exact managed text")
            if self.m_lose_response:
                raise DshWebError("outcome_uncertain", "Native HTTP response lost")
            return {"prompt_id": prompt_id, "status": "queued"}
        if method == "POST" and path.endswith(":abort"):
            assert body == {}
            if isinstance(self.m_abort_result, DshWebError):
                raise self.m_abort_result
            return {"aborted": self.m_abort_result}
        pytest.fail(f"Unexpected native request {method} {path}")

    def write_turn(self, prompt_id: str, turn: int, text: str) -> None:
        """Record one native start, assistant output, and two matching terminal facts."""

        self.append({"type": "turn.prompt", "promptId": prompt_id, "turnId": turn})
        self.finish_turn(prompt_id, turn, text)

    def finish_turn(self, prompt_id: str, turn: int, text: str) -> None:
        """Complete an existing turn and return the synthetic session to idle."""

        self.m_busy = False
        self.append(
            {
                "type": "context.append_loop_event",
                "event": {
                    "type": "content.part",
                    "turnId": str(turn),
                    "part": {"type": "text", "text": text},
                },
            },
            {"type": "turn.ended", "turnId": turn, "reason": "completed"},
            {"type": "prompt.completed", "promptId": prompt_id, "reason": "completed"},
        )

    def start_task_notification(self, prompt_id: str, turn: int) -> None:
        """Open a task-origin turn with the identity Kimi assigns to its notification."""

        self.m_busy = True
        self.append(
            {
                "type": "turn.prompt",
                "turnId": turn,
                "promptId": prompt_id,
                "origin": {"kind": "task", "notificationId": prompt_id},
            }
        )


@pytest.fixture
def web(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[KimiWebSession, _Native]:
    """Construct a verified fixture owner with no tmux or network dependency."""

    home = tmp_path / "home"
    workspace = tmp_path / "project"
    workspace.mkdir()
    session = kimi_native_workspace_path(home, workspace) / "session_selected"
    journal = session / "agents/main/wire.jsonl"
    journal.parent.mkdir(parents=True)
    journal.touch(mode=0o600)
    state_path = session / "state.json"
    state_path.touch(mode=0o600)
    state_path.write_text(json.dumps({"id": session.name, "cwd": str(workspace)}))
    identity = {
        "protocol_version": 1,
        "agent_id": "agent",
        "runtime_session_id": "runtime",
        "native_session_id": session.name,
        "generation": "generation",
        "host_incarnation": "host",
        "agent_incarnation": "instance",
    }
    state = KimiWebSessionState(
        origin="http://127.0.0.1:8080",
        web_identity=identity,
        bootstrap_path=str(home / "bootstrap.json"),
        cookie_path=str(home / "server.token"),
        control_path=str(home / "control.json"),
        supervisor_pid=39,
        supervisor_birth_token="proc:5",
        tmux_session_name="test",
        evidence_path=str(journal),
        working_directory=str(workspace),
        native_pid=40,
        native_birth_token="proc:6",
    )
    adapter = KimiWebSession()
    adapter.m_state = state
    adapter.m_manifest_path = tmp_path / "manifest.json"
    adapter.manifest_path.write_text(
        json.dumps(
            {
                "backend": "kimi_web",
                "registry_generation_id": "generation",
                "agent_id": "agent",
                "runtime_session_id": "runtime",
                "working_directory": str(workspace),
                "backend_state": state.to_payload(),
                "launch_plan": {"home_selector": {"home_path": str(home)}},
            }
        )
    )
    native = _Native(journal, workspace)
    monkeypatch.setattr(adapter, "_client", lambda: native)
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.kimi_web.UsageService.begin_headless_turn",
        lambda *_args, **_kwargs: None,
    )
    return adapter, native


def test_browser_entry_uses_verified_exact_conversation_and_private_fragment(
    web: tuple[KimiWebSession, _Native],
) -> None:
    """Resolve the qualified stock link without checking prompt admission or starting work."""

    adapter, native = web
    native.m_busy = True
    entry = adapter.browser_entry()
    location = urlsplit(entry.redirect_url(expected_origin=adapter.state.origin))
    assert location.path == "/sessions/session_selected" and location.query == ""
    assert parse_qs(location.fragment) == {"token": [native.credential()]}
    assert native.credential() not in repr(entry)
    assert native.m_calls == [("GET", "/meta"), ("GET", "/sessions/session_selected")]


def test_browser_entry_checks_host_incarnation_before_releasing_fragment(
    web: tuple[KimiWebSession, _Native],
) -> None:
    """A different server with the same address cannot grant browser access."""

    adapter, native = web
    native.m_host_incarnation = "replacement"
    with pytest.raises(DshWebError, match="Kimi Web host incarnation changed") as failed:
        adapter.browser_entry()
    assert native.credential() not in str(failed.value)
    assert native.m_calls == [("GET", "/meta")]


@pytest.fixture
def web_startup_plan(
    web: tuple[KimiWebSession, _Native],
    monkeypatch: pytest.MonkeyPatch,
) -> LaunchPlan:
    """Provide an admitted newer version and bypass only host process startup."""

    adapter, native = web
    native.m_wrap_profile = True
    prior_state = adapter.state
    home = Path(prior_state.cookie_path).parent
    plan = LaunchPlan(
        backend="kimi_web",
        tool="kimi",
        executable="kimi",
        args=["web", "--no-open", "--host", "127.0.0.1", "--port", "0"],
        working_directory=Path(prior_state.working_directory),
        home_path=home,
        home_env_var="KIMI_CODE_HOME",
        env={},
        env_var_names=[],
        role_injection=RoleInjectionPlan(
            method="native_home_system_prompt", role_name="r", prompt="role"
        ),
        metadata={
            "kimi_web": {"detected_version": "2.7.2", "permission_mode": "auto"},
            "managed_web_identity": {
                field: prior_state.web_identity[field]
                for field in ("agent_id", "runtime_session_id", "generation")
            },
        },
    )
    module = "houmao.agents.realm_controller.backends.kimi_web"
    process = {
        "supervisor_pid": prior_state.supervisor_pid,
        "supervisor_birth_token": prior_state.supervisor_birth_token,
    }
    client = SimpleNamespace(
        origin=prior_state.origin,
        pid=prior_state.native_pid,
        birth=prior_state.native_birth_token,
        token_file=Path(prior_state.cookie_path),
        request=native.request,
    )
    monkeypatch.setattr(f"{module}.tmux_session_exists", lambda **_: False)
    monkeypatch.setattr(f"{module}.create_tmux_session", lambda **_: None)
    monkeypatch.setattr(f"{module}.run_tmux", lambda *_: SimpleNamespace(returncode=0))
    monkeypatch.setattr(
        f"{module}.prepare_headless_agent_window",
        lambda **_: SimpleNamespace(pane_id="%1", window_id="@1"),
    )
    monkeypatch.setattr(
        KimiWebSession,
        "_wait_for_host",
        staticmethod(lambda *_: (process, client, {"server_id": "host"})),
    )
    monkeypatch.setattr(KimiWebSession, "_client", lambda _: client)
    monkeypatch.setattr(KimiWebSession, "_owns_tmux", staticmethod(lambda *_: False))
    monkeypatch.setattr(
        KimiWebSession, "terminate", lambda _: SessionControlResult("ok", "terminate", "stopped")
    )
    return plan


@pytest.mark.parametrize(
    ("version", "permission_mode"), [("2.6.0", "auto"), ("2.7.2", "manual"), ("2.7.2", None)]
)
def test_web_projects_permission_only_during_native_startup(
    web: tuple[KimiWebSession, _Native],
    web_startup_plan: LaunchPlan,
    version: str,
    permission_mode: str | None,
) -> None:
    """Apply the selected mode on birth and exact relaunch while observation remains passive."""

    adapter, native = web
    native.m_wrap_profile = version != "2.6.0"
    plan = replace(
        web_startup_plan,
        metadata={
            **web_startup_plan.metadata,
            "kimi_web": {"detected_version": version, "permission_mode": permission_mode},
        },
    )
    launched = KimiWebSession.from_launch_plan(
        launch_plan=plan,
        session_manifest_path=adapter.manifest_path,
        role_name="r",
        provider_start=True,
    )
    profile_write = ("POST", "/sessions/session_selected/profile")
    assert native.m_calls == [("POST", "/sessions"), *([profile_write] if permission_mode else [])]
    assert native.m_permission == (permission_mode or "manual")
    native.m_permission = "yolo"
    native.m_calls.clear()
    manifest = json.loads(adapter.manifest_path.read_text())
    manifest["backend_state"] = launched.state.to_payload()
    adapter.manifest_path.write_text(json.dumps(manifest))
    reattached = KimiWebSession.from_launch_plan(
        launch_plan=plan,
        session_manifest_path=adapter.manifest_path,
        role_name="r",
        state=launched.state,
    )
    assert reattached.observe_web_state()["admission"]["ready_only"]
    assert native.m_calls == [("GET", "/sessions/session_selected")]
    assert native.m_permission == "yolo"

    native.m_calls.clear()
    result = reattached.relaunch(
        chat_session=RelaunchChatSessionSelection(mode="exact", session_id="session_selected")
    )
    assert result.status == "ok"
    assert native.m_calls == [
        ("GET", "/sessions/session_selected"),
        *([profile_write] if permission_mode else []),
    ]
    assert native.m_permission == (permission_mode or "yolo")
    assert reattached.state.web_identity["native_session_id"] == "session_selected"


def test_web_publishes_before_starting_private_supervisor(
    web: tuple[KimiWebSession, _Native],
    web_startup_plan: LaunchPlan,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The owned pane receives its resolved env before native host startup."""

    adapter, _ = web
    plan = replace(
        web_startup_plan,
        public_env={"REVIEW_FLAG": "enabled"},
        env={"REVIEW_FLAG": "enabled", "PROVIDER_KEY": "synthetic-private"},
    )
    monkeypatch.setenv("PATH", "/undeclared-manager-path")
    calls: list[str] = []
    artifact: Path | None = None

    def publish(*, session_name: str, launch_plan: LaunchPlan) -> None:
        assert session_name == "owned-test-web"
        assert launch_plan.public_env == {"REVIEW_FLAG": "enabled"}
        calls.append("publish")

    def run_tmux(args: list[str]) -> SimpleNamespace:
        nonlocal artifact
        if args[0] == "respawn-pane":
            calls.append("spawn")
            assert "synthetic-private" not in args[-1]
            artifact = Path(shlex.split(args[-1])[-1])
            assert stat.S_IMODE(artifact.stat().st_mode) == 0o600
            environment = json.loads(artifact.read_text())["environment"]
            assert environment["KIMI_CODE_HOME"] == str(plan.home_path.resolve())
            assert environment["REVIEW_FLAG"] == "enabled"
            assert environment["PROVIDER_KEY"] == "synthetic-private"
            assert environment["HOUMAO_SELF_TMUX_SESSION"] == "owned-test-web"
            assert "PATH" not in environment
        return SimpleNamespace(returncode=0)

    module = "houmao.agents.realm_controller.backends.kimi_web"
    monkeypatch.setattr(f"{module}.publish_tmux_launch_environment", publish)
    monkeypatch.setattr(f"{module}.run_tmux", run_tmux)
    KimiWebSession.from_launch_plan(
        launch_plan=plan,
        session_manifest_path=adapter.manifest_path,
        role_name="r",
        tmux_session_name="owned-test-web",
        provider_start=True,
    )

    assert calls == ["publish", "spawn"]
    assert artifact is not None and not artifact.exists()


@pytest.mark.parametrize(
    ("failure", "message"),
    [
        ("api", "native session API failed"),
        ("identity", "session or workspace changed"),
        ("activity", "session activity could not be verified"),
        ("permission", "did not confirm permission mode"),
    ],
)
def test_web_newer_version_cannot_publish_an_unverified_session(
    web: tuple[KimiWebSession, _Native],
    web_startup_plan: LaunchPlan,
    failure: str,
    message: str,
) -> None:
    """Verify the newer build's session API and ownership before publishing a binding."""

    adapter, native = web
    if failure == "api":
        native.m_refuse_session_create = True
    elif failure == "identity":
        native.m_workspace = web_startup_plan.working_directory.parent / "wrong-workspace"
    elif failure == "activity":
        native.m_activity_override = "unknown"
    else:
        native.m_reported_permission = "manual"
    with pytest.raises(BackendExecutionError, match=message):
        KimiWebSession.from_launch_plan(
            launch_plan=web_startup_plan,
            session_manifest_path=adapter.manifest_path,
            role_name="r",
            provider_start=True,
        )
    assert native.m_calls[0] == ("POST", "/sessions")
    assert not list(web_startup_plan.home_path.glob("houmao-web/*/bootstrap.json"))


def test_web_below_floor_plan_does_not_start_native_host(
    web: tuple[KimiWebSession, _Native], web_startup_plan: LaunchPlan
) -> None:
    """Validate the declared version floor before creating an owner or issuing requests."""

    adapter, native = web
    plan = replace(
        web_startup_plan,
        metadata={**web_startup_plan.metadata, "kimi_web": {"detected_version": "2.5.9"}},
    )
    with pytest.raises(BackendExecutionError, match=r"Kimi Web .*>=2\.6\.0"):
        KimiWebSession.from_launch_plan(
            launch_plan=plan,
            session_manifest_path=adapter.manifest_path,
            role_name="r",
            provider_start=True,
        )
    assert not native.m_calls
    assert not (plan.home_path / "houmao-web").exists()


def test_web_host_wait_reports_incompatible_meta_api(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keep the native /meta diagnostic after an owned listener fails verification."""

    module = "houmao.agents.realm_controller.backends.kimi_web"
    root, home = tmp_path / "owner", tmp_path / "home"
    instances = home / "server/instances"
    root.mkdir()
    instances.mkdir(parents=True)
    (root / "supervisor.json").write_text(json.dumps({"native_pid": 40, "native_birth_token": "p"}))
    (instances / "native.json").write_text(
        json.dumps({"pid": 40, "host": "127.0.0.1", "port": 8080})
    )

    def request(method: str, path: str, *, authenticated: bool) -> dict[str, Any]:
        """Simulate an owned listener whose API exposes no compatible /meta endpoint."""

        assert (method, path, authenticated) == ("GET", "/meta", False)
        (root / "exit.json").touch()
        raise DshWebError("invalid_request", "Kimi Web refused the native request")

    monkeypatch.setattr(f"{module}.owned_listener", lambda *_: True)
    monkeypatch.setattr(f"{module}.KimiWebClient", lambda *_: SimpleNamespace(request=request))
    with pytest.raises(BackendExecutionError, match=r"Kimi Web native /meta verification failed"):
        KimiWebSession._wait_for_host(home, root)


def test_reports_native_queue_receipt_before_settlement(
    web: tuple[KimiWebSession, _Native],
) -> None:
    """Preserve a late browser win and attribute only the managed native answer."""

    adapter, native = web
    receipt = adapter.manifest_path.parent / "manifest.turn-artifacts/request/web-receipt.json"
    handed_off: list[str] = []
    control = HeadlessDispatchControl.from_callbacks(
        allowed=lambda: True,
        confirmed=lambda: handed_off.append(json.loads(receipt.read_text())["status"]),
        deadline=time.monotonic() + 2,
    )
    adapter.configure_request_dispatch(control)
    events = adapter.send_web_prompt("input", turn_artifact_dir_name="request")
    assert handed_off == ["queued"]
    assert control.m_input_started.is_set()
    assert events[0].payload and events[0].payload["native_status"] == "queued"
    assert [event.message for event in events if event.kind == "assistant"] == [
        "exact managed text"
    ]
    terminal = json.loads(receipt.with_name("web-result.json").read_text())
    native_receipt = json.loads(receipt.read_text())
    assert json.loads(receipt.with_name("web-handoff.json").read_text()) == {
        "operation_id": "request",
        "identity": native_receipt["identity"],
        "message_id": native_receipt["message_id"],
    }
    assert terminal["receipt"]["turns"] == [1]
    assert terminal["outcome"] == "completed"


def test_passive_read_and_rejected_preflight_send_no_prompt(
    web: tuple[KimiWebSession, _Native],
) -> None:
    """Use non-mutating session state passively, then respect a checked pending queue."""

    adapter, native = web
    assert adapter.observe_web_state()["admission"]["ready_only"]
    assert native.m_calls == [("GET", "/sessions/session_selected")]
    native.m_refuse_preflight = True
    with pytest.raises(DshWebError, match="not_ready"):
        adapter.send_web_prompt("input", turn_artifact_dir_name="refused")
    assert all(method == "GET" for method, _ in native.m_calls)


def test_newer_web_background_activity_blocks_input(web: tuple[KimiWebSession, _Native]) -> None:
    """Require idle activity before dispatch even when the main turn is inactive."""

    adapter, native = web
    native.m_wrap_profile = True
    native.m_activity_override = "background"
    observation = adapter.observe_web_state()
    assert observation["native_agent_live"] and observation["active_turn"] is None
    assert not observation["admission"]["ready_only"]
    with pytest.raises(DshWebError, match="not_ready"):
        adapter.send_web_prompt("input", turn_artifact_dir_name="background")
    assert native.m_calls == [("GET", "/sessions/session_selected")] * 2


def test_native_task_history_preserves_prompt_ids_and_journal_offsets(
    web: tuple[KimiWebSession, _Native],
) -> None:
    """Read the task start and settlement in order from both incremental and initial cursors."""

    adapter, native = web
    native.write_turn("houmao_managed", 1, "managed result")
    baseline = adapter.observe_web_state()["sequence"]
    assert baseline == native.m_journal.stat().st_size
    task_id = "task:bash-example:completed"
    native.start_task_notification(task_id, 2)
    start = native.m_journal.stat().st_size
    assert adapter.observe_web_state()["active_turn"] == {"turn": 2, "start_sequence": start}
    native.append({"type": "turn.ended", "turnId": 2, "reason": "completed"})
    end = native.m_journal.stat().st_size
    native.append({"type": "prompt.completed", "promptId": task_id, "reason": "completed"})
    settled = native.m_journal.stat().st_size
    native.m_busy = False
    state = adapter.observe_web_state()
    assert state["active_turn"] is None
    assert state["last_turn"] == {"turn": 2, "end_sequence": end, "result": "completed"}
    assert state["sequence"] == settled

    for after in (-1, baseline, baseline):
        page = adapter.observe_web_history(after_sequence=after)
        assert page["previous_sequence"] == after
        assert not page["truncated"]
        transitions = [
            (row["sequence"], row["event"], row.get("message_id"))
            for row in page["entries"]
            if row["sequence"] > baseline
        ]
        assert transitions == [
            (start, "turn/started", task_id),
            (end, "turn/ended", None),
            (settled, "inbox/settled", task_id),
        ]
    assert native.m_calls == [("GET", "/sessions/session_selected")] * 3


def test_gateway_observes_native_task_readiness_and_closes_on_lost_authority(
    web: tuple[KimiWebSession, _Native],
) -> None:
    """A verified active notification stays visible until native work and interactions clear."""

    adapter, native = web
    observer = WebObservation(
        metadata=GatewayAttachBackendMetadataWebV1.model_validate(
            {
                "tool": "kimi",
                "origin": native.origin,
                "browser_url": native.origin,
                "identity": adapter.state.web_identity,
            }
        ),
        state=adapter.observe_web_state,
        history=adapter.observe_web_history,
        source="gateway",
        sparse_history=True,
    )
    task_id = "task:bash-example:completed"
    native.start_task_notification(task_id, 2)
    active = observer.refresh()
    assert active.availability == "available" and not active.can_accept_prompt_now
    assert active.active_turn and active.active_turn.turn == 2
    native.finish_turn(task_id, 2, "background task output")
    native.m_pending_interaction = "approval"
    waiting = observer.refresh()
    assert waiting.active_turn is None
    assert waiting.interaction_waits == ["approval"] and not waiting.can_accept_prompt_now
    native.m_pending_interaction = "none"
    assert observer.refresh().can_accept_prompt_now
    assert [row.metadata.get("message_id") for row in observer.history().entries] == [
        task_id,
        None,
        task_id,
    ]

    adapter.manifest_path.unlink()
    unavailable = observer.refresh()
    assert unavailable.availability == "unavailable" and not unavailable.can_accept_prompt_now
    assert native.m_calls == [("GET", "/sessions/session_selected")] * 3


def test_native_task_cannot_settle_an_unrelated_managed_attempt(
    web: tuple[KimiWebSession, _Native], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reconcile a lost submission only when the journal contains its exact result."""

    adapter, native = web
    native.m_lose_response = True
    with monkeypatch.context() as pending:
        pending.setattr(native, "write_turn", lambda *_args: None)
        with pytest.raises(DshWebError, match="outcome_uncertain"):
            adapter.send_web_prompt("managed work", turn_artifact_dir_name="lost")

    task_id = "task:bash-example:completed"
    native.start_task_notification(task_id, 1)
    native.finish_turn(task_id, 1, "unrelated task output")
    directory = adapter.manifest_path.parent / "manifest.turn-artifacts/lost"
    attempt = json.loads((directory / "web-attempt.json").read_text())
    result = directory / "web-result.json"
    adapter.recover_web_prompt_result("lost")
    assert not result.exists()

    native.write_turn(attempt["message_id"], 2, "managed output")
    adapter.recover_web_prompt_result("lost")
    terminal = json.loads(result.read_text())
    assert terminal["assistant_text"] == "managed output"
    assert terminal["receipt"]["turns"] == [2]
    assert [call for call in native.m_calls if call[0] == "POST"] == [
        ("POST", "/sessions/session_selected/prompts")
    ]


def test_final_native_readiness_follows_dispatch_authorization(
    web: tuple[KimiWebSession, _Native],
) -> None:
    """Refuse native work that starts while the managed permission is being checked."""

    adapter, native = web
    checks = 0

    def allow() -> bool:
        """Start browser work during the final gateway permission callback."""

        nonlocal checks
        checks += 1
        if checks == 2:
            native.m_busy = True
        return True

    control = HeadlessDispatchControl.from_callbacks(
        allowed=allow, confirmed=lambda: None, deadline=time.monotonic() + 2
    )
    adapter.configure_request_dispatch(control)
    with pytest.raises(DshWebError, match="not_ready"):
        adapter.send_web_prompt("input", turn_artifact_dir_name="late-browser")
    assert native.m_calls == [("GET", "/sessions/session_selected")]
    assert not control.m_input_started.is_set()


def test_lost_http_response_recovers_exact_journal_without_repeat(
    web: tuple[KimiWebSession, _Native],
) -> None:
    """Recover native completion from the saved exact attempt instead of replaying input."""

    adapter, native = web
    native.m_lose_response = True
    with pytest.raises(DshWebError, match="outcome_uncertain"):
        adapter.send_web_prompt("input", turn_artifact_dir_name="lost")
    recover_kimi_web_prompt_result(adapter.manifest_path, "generation", "lost")
    result_path = adapter.manifest_path.parent / "manifest.turn-artifacts/lost/web-result.json"
    result = json.loads(result_path.read_text())
    assert result["assistant_text"] == "exact managed text"
    assert result["receipt"]["native_status"] == "unknown"
    assert [item for item in native.m_calls if item[0] == "POST"] == [
        ("POST", "/sessions/session_selected/prompts")
    ]


@pytest.mark.parametrize(
    ("current_activity_shape", "prompt_id", "encoded_id"),
    [
        (False, "active_prompt", "active_prompt"),
        (True, "active_prompt", "active_prompt"),
        (True, "task:bash-example:completed", "task%3Abash-example%3Acompleted"),
        (True, "notes/step%2F1?q#2", "notes%2Fstep%252F1%3Fq%232"),
    ],
)
def test_interrupt_uses_captured_native_prompt(
    web: tuple[KimiWebSession, _Native],
    current_activity_shape: bool,
    prompt_id: str,
    encoded_id: str,
) -> None:
    """Encode the exact active prompt as one route segment, including literal percent sequences."""

    adapter, native = web
    native.m_wrap_profile = current_activity_shape
    native.m_busy = True
    native.append({"type": "turn.prompt", "promptId": prompt_id, "turnId": 2})
    captured = adapter.observe_web_state()["active_turn"]
    assert captured and captured["turn"] == 2
    assert (
        adapter.interrupt_web_turn(
            adapter.state.web_identity,
            turn_start_seq=captured["start_sequence"],
        ).status
        == "ok"
    )
    posts = [path for method, path in native.m_calls if method == "POST"]
    assert posts == [f"/sessions/session_selected/prompts/{encoded_id}:abort"]
    wire_segment = urlsplit(posts[0]).path.rsplit("/", 1)[1].removesuffix(":abort")
    assert unquote(wire_segment) == prompt_id


def test_interrupt_refuses_unrelated_targets_before_abort(
    web: tuple[KimiWebSession, _Native],
) -> None:
    """Refuse the wrong session, host, completed managed operation, and superseded turn."""

    adapter, native = web
    adapter.send_web_prompt("managed work", turn_artifact_dir_name="prior")
    native.m_calls.clear()
    native.m_busy = True
    identity = adapter.state.web_identity
    native.append({"type": "turn.prompt", "promptId": "active_prompt", "turnId": 2})
    captured = adapter.observe_web_state()["active_turn"]["start_sequence"]
    for field in ("native_session_id", "host_incarnation"):
        wrong_identity = {**identity, field: "another"}
        result = adapter.interrupt_web_turn(wrong_identity, turn_start_seq=captured)
        assert result.status == "error"
    result = adapter.interrupt_web_turn(identity, turn_start_seq=captured, operation_id="prior")
    assert result.status == "error"

    native.append(
        {"type": "turn.ended", "turnId": 2, "reason": "completed"},
        {"type": "prompt.completed", "promptId": "active_prompt", "reason": "completed"},
        {"type": "turn.prompt", "promptId": "later_prompt", "turnId": 3},
    )
    assert adapter.interrupt_web_turn(identity, turn_start_seq=captured).status == "error"
    assert all(method == "GET" for method, _ in native.m_calls)


@pytest.mark.parametrize(
    "abort_result",
    [False, DshWebError("invalid_request", "Kimi no longer has this prompt")],
    ids=["negative-receipt", "native-error"],
)
def test_interrupt_returns_native_refusal_without_retargeting(
    web: tuple[KimiWebSession, _Native], abort_result: bool | DshWebError
) -> None:
    """Surface an abort refusal from Kimi after one attempt on the captured prompt."""

    adapter, native = web
    native.m_busy = True
    native.m_abort_result = abort_result
    native.append({"type": "turn.prompt", "promptId": "active_prompt", "turnId": 2})
    captured = adapter.observe_web_state()["active_turn"]["start_sequence"]
    result = adapter.interrupt_web_turn(adapter.state.web_identity, turn_start_seq=captured)
    assert result.status == "error"
    assert [item for item in native.m_calls if item[0] == "POST"] == [
        ("POST", "/sessions/session_selected/prompts/active_prompt:abort")
    ]


def test_wrong_listener_never_reads_private_credential(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject changed kernel listener ownership before reading or sending a bearer."""

    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.kimi_web_client.owned_listener",
        lambda *_args: False,
    )
    client = KimiWebClient("http://127.0.0.1:8080", 1234, "proc:99", tmp_path / "token")
    with pytest.raises(DshWebError, match="stale_identity"):
        client.request("GET", "/meta")


def test_explicit_browser_open_keeps_credential_out_of_process_arguments(
    web: tuple[KimiWebSession, _Native],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Use a 0600 local browser bootstrap whose public result contains no bearer."""

    adapter, _ = web
    sentinel = "synthetic-native-browser-token"
    seen: list[str] = []
    monkeypatch.setattr(adapter, "browser_credentials", lambda: (adapter.state.origin, sentinel))
    monkeypatch.setattr("webbrowser.open", lambda path: not seen.append(path))
    result = adapter.open_browser()
    assert result.status == "ok"
    browser_source = Path(unquote(urlsplit(seen[0]).path))
    assert browser_source.stat().st_mode & 0o777 == 0o600
    assert f"{adapter.state.origin}/#token={sentinel}" in browser_source.read_text()
    assert sentinel not in seen[0] and sentinel not in result.detail
