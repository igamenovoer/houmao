"""Exercise persistent-owner boundaries with a deterministic native peer."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import shlex
import socket
import stat
import threading
import time
from types import SimpleNamespace
from typing import Any

import pytest

from houmao.agents.realm_controller import runtime
from houmao.agents.realm_controller.backends import service_runtime
from houmao.agents.realm_controller.backends.dispatch_control import (
    HeadlessDispatchControl,
    _dispatch_origin_birth_token,
)
from houmao.agents.realm_controller.backends.service_owner import ServiceOwner
from houmao.agents.realm_controller.backends.service_runtime import (
    ManagedServiceSession,
    ManagedServiceSessionState,
    ServiceDescriptor,
    ServiceOperationContext,
    ServiceOwnerConfig,
    ServicePromptResult,
    ServiceRequest,
    ServiceRequestSnapshot,
    read_service_record,
    service_turn_dir,
    verify_service_socket,
    write_service_record,
)
from houmao.agents.realm_controller.backends.tmux_runtime import TmuxCommandError
from houmao.agents.realm_controller.errors import BackendExecutionError
from houmao.agents.realm_controller.managed_control import ManagedControlObservationV1
from houmao.agents.realm_controller.models import LaunchPlan, RoleInjectionPlan, SessionEvent
from houmao.agents.realm_controller.owner_admission import OwnerPromptClaim


class _Peer:
    """Control prompt progress without changing the native session or connection."""

    def __init__(self) -> None:
        self.native_session_id = "native-session"
        self.connection_ready = True
        self.process_id = os.getpid()
        self.process_birth_token = _dispatch_origin_birth_token(self.process_id)
        self.m_submitted: list[str] = []
        self.m_cancelled: list[str] = []
        self.m_before_write = threading.Event()
        self.m_allow_write = threading.Event()
        self.m_after_write = threading.Event()
        self.m_finish = threading.Event()
        self.m_fail_after_write = False

    def prompt(
        self, prompt: str, *, execution_model: Any, operation: ServiceOperationContext
    ) -> ServicePromptResult:
        """Wait immediately before and after the bounded native mutation."""

        assert execution_model is None
        self.m_before_write.set()
        assert self.m_allow_write.wait(5.0)
        operation.authorize_native_write()
        self.m_submitted.append(operation.request_id)
        operation.confirm_native_handoff(f"turn-{len(self.m_submitted)}")
        operation.publish_event(SessionEvent(kind="assistant", message="observed", turn_index=1))
        self.m_after_write.set()
        if self.m_fail_after_write:
            self.connection_ready = False
            raise OSError("synthetic native EOF")
        assert self.m_finish.wait(5.0)
        return ServicePromptResult(
            outcome="interrupted" if operation.request_id in self.m_cancelled else "completed",
            native_turn_id=f"turn-{len(self.m_submitted)}",
        )

    def cancel(self, operation_id: str) -> bool:
        """Settle only the captured fixture operation."""

        self.m_cancelled.append(operation_id)
        self.m_finish.set()
        return True

    def close(self) -> None:
        """Simulate closure of this exact native connection."""

        self.connection_ready = False


@pytest.mark.parametrize("publication_fails", [False, True])
def test_service_publishes_before_starting_private_supervisor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, publication_fails: bool
) -> None:
    """Startup checks the scoped session environment before entering the supervisor."""

    plan = LaunchPlan(
        backend="codex_app_server",
        tool="codex",
        executable="codex",
        args=["app-server"],
        working_directory=tmp_path,
        home_path=tmp_path / "home",
        home_env_var="CODEX_HOME",
        env={"REVIEW_FLAG": "enabled", "PROVIDER_KEY": "synthetic-private"},
        env_var_names=["REVIEW_FLAG", "PROVIDER_KEY"],
        public_env={"REVIEW_FLAG": "enabled"},
        role_injection=RoleInjectionPlan(
            method="native_home_system_prompt", role_name="r", prompt="role"
        ),
        metadata={
            "managed_service_identity": {
                "agent_id": "agent",
                "runtime_session_id": "runtime",
                "generation": "generation",
            },
            "tmux_socket_path": str(tmp_path / "owner.sock"),
        },
    )
    monkeypatch.setenv("PATH", "/undeclared-manager-path")
    calls: list[str] = []

    def publish(*, session_name: str, launch_plan: LaunchPlan) -> None:
        assert session_name == "owned-test-service"
        assert launch_plan.public_env == {"REVIEW_FLAG": "enabled"}
        calls.append("publish")
        if publication_fails:
            raise TmuxCommandError("Failed to publish tmux launch variable REVIEW_FLAG")

    def run_tmux(args: list[str]) -> SimpleNamespace:
        if args[0] == "respawn-pane":
            calls.append("spawn")
            assert "synthetic-private" not in args[-1]
            artifact = Path(shlex.split(args[-1])[-1])
            assert stat.S_IMODE(artifact.stat().st_mode) == 0o600
            payload = json.loads(artifact.read_text())
            assert payload["publishable_env_var_names"] == ["REVIEW_FLAG"]
            assert payload["environment"] == {
                **plan.env,
                "HOUMAO_SELF_TMUX_SOCKET": str(tmp_path / "owner.sock"),
                "HOUMAO_SELF_TMUX_SESSION": "owned-test-service",
            }
            return SimpleNamespace(returncode=1)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(service_runtime, "tmux_session_exists", lambda **_: False)
    monkeypatch.setattr(service_runtime, "create_tmux_session", lambda **_: None)
    monkeypatch.setattr(
        service_runtime, "cleanup_tmux_session", lambda **_: calls.append("cleanup")
    )
    monkeypatch.setattr(
        service_runtime,
        "prepare_headless_agent_window",
        lambda **_: SimpleNamespace(pane_id="%1", window_id="@1"),
    )
    monkeypatch.setattr(service_runtime, "publish_tmux_launch_environment", publish)
    monkeypatch.setattr(service_runtime, "run_tmux", run_tmux)
    error = "REVIEW_FLAG" if publication_fails else "Service supervisor could not be launched"
    with pytest.raises(BackendExecutionError, match=error):
        ManagedServiceSession.from_launch_plan(
            launch_plan=plan,
            role_name="r",
            session_manifest_path=tmp_path / "manifest.json",
            tmux_session_name="owned-test-service",
            provider_start=True,
        )

    assert calls == ["publish", *([] if publication_fails else ["spawn"]), "cleanup"]
    assert not list(tmp_path.glob("service/*/startup.json"))


def _owner(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[ServiceOwner, _Peer, Path]:
    """Supply the registry authority and use the real request permission at both boundaries."""

    manifest = tmp_path / "manifest.json"
    manifest.write_text('{"registry_generation_id":"generation"}')
    peer = _Peer()
    config = ServiceOwnerConfig(
        backend="dsh_acp",
        executable="unused",
        arguments=[],
        working_directory=tmp_path,
        home_path=tmp_path,
        environment={},
        metadata={},
        root=tmp_path,
        manifest_path=manifest,
        agent_id="agent",
        runtime_session_id="runtime",
        generation_id="generation",
        service_incarnation="incarnation",
    )
    authority = SimpleNamespace(
        runtime=SimpleNamespace(session_id="runtime"),
        backend="dsh_acp",
        mode="service",
        backend_state={
            "service_incarnation": "incarnation",
            "native_session_id": peer.native_session_id,
        },
    )
    monkeypatch.setattr(
        runtime, "require_active_managed_control_manifest", lambda *a, **k: authority
    )
    monkeypatch.setattr(OwnerPromptClaim, "active", lambda _: True)
    monkeypatch.setattr(OwnerPromptClaim, "handoff", lambda _: None)
    monkeypatch.setattr(OwnerPromptClaim, "finish", lambda *a, **k: None)
    return ServiceOwner(config, peer), peer, manifest


def _grant(manifest: Path, attempt: str) -> HeadlessDispatchControl:
    """Prepare a payload-free grant bound to the invoking process and attempt."""

    directory = service_turn_dir(manifest, attempt)
    directory.mkdir(parents=True)
    control = HeadlessDispatchControl.from_callbacks(
        allowed=lambda: True,
        confirmed=lambda: None,
        deadline=time.monotonic() + 10,
        manifest_path=manifest,
        generation_id="generation",
    )
    control.prepare_bridge_permission(directory)
    return control


def _request(
    operation: Any, *, attempt: str | None = None, prompt: str | None = None
) -> ServiceRequest:
    """Create a finite operation for the fixture's exact incarnation."""

    return ServiceRequest(
        operation=operation,
        generation_id="generation",
        service_incarnation="incarnation",
        request_id=attempt,
        prompt=prompt,
    )


@pytest.mark.parametrize("fault", ["revoke", "provider_loss", "caller_response_loss"])
def test_service_owner_persists_exact_outcome_without_replay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    """Keep native work and its durable attribution independent of socket lifetime."""

    owner, peer, manifest = _owner(tmp_path, monkeypatch)
    permission = _grant(manifest, "request")
    notices: list[dict[str, Any]] = []
    peer.m_fail_after_write = fault == "provider_loss"
    emit = (lambda _: None) if fault == "caller_response_loss" else notices.append
    with ThreadPoolExecutor(max_workers=1) as pool:
        running = pool.submit(
            owner.handle,
            _request("prompt", attempt="request", prompt="private input"),
            caller_pid=os.getpid(),
            emit=emit,
        )
        assert peer.m_before_write.wait(5)
        before = owner.observe()
        assert before.active_request_id == "request" and before.can_accept_prompt_now is False
        assert before.active_turn_id is None
        if fault == "revoke":
            permission.cancel()
        peer.m_allow_write.set()
        if fault == "caller_response_loss":
            assert peer.m_after_write.wait(5)
            active = owner.observe()
            assert active.active_request_id == "request" and active.active_turn_id == "turn-1"
        peer.m_finish.set()
        result = running.result(timeout=6)["request"]

    path = service_turn_dir(manifest, "request") / "service-request.json"
    durable = ServiceRequestSnapshot.model_validate_json(read_service_record(path))
    assert durable.model_dump(mode="json") == result
    assert "private input" not in path.read_text()
    assert (
        durable.state
        == {"revoke": "failed", "provider_loss": "uncertain", "caller_response_loss": "completed"}[
            fault
        ]
    )
    assert peer.m_submitted == ([] if fault == "revoke" else ["request"])
    with pytest.raises(BackendExecutionError):
        owner.handle(
            _request("prompt", attempt="request", prompt="duplicate"),
            caller_pid=os.getpid(),
            emit=notices.append,
        )
    assert peer.m_submitted == ([] if fault == "revoke" else ["request"])


def test_service_cancellation_requires_exact_current_operation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stale interrupt cannot cancel a successor sharing the same native session."""

    owner, peer, manifest = _owner(tmp_path, monkeypatch)
    _grant(manifest, "first")
    _grant(manifest, "second")
    peer.m_allow_write.set()
    with ThreadPoolExecutor(max_workers=1) as pool:
        first = pool.submit(
            owner.handle,
            _request("prompt", attempt="first", prompt="first"),
            caller_pid=os.getpid(),
            emit=lambda _: None,
        )
        assert peer.m_after_write.wait(5.0)
        owner.handle(
            _request("interrupt", attempt="first"), caller_pid=os.getpid(), emit=lambda _: None
        )
        assert first.result(timeout=5)["request"]["state"] == "interrupted"
        peer.m_after_write.clear()
        peer.m_finish.clear()
        second = pool.submit(
            owner.handle,
            _request("prompt", attempt="second", prompt="second"),
            caller_pid=os.getpid(),
            emit=lambda _: None,
        )
        assert peer.m_after_write.wait(5.0)
        with pytest.raises(BackendExecutionError, match="settled or changed"):
            owner.handle(
                _request("interrupt", attempt="first"), caller_pid=os.getpid(), emit=lambda _: None
            )
        assert peer.m_cancelled == ["first"]
        peer.m_finish.set()
        assert second.result(timeout=5)["request"]["state"] == "completed"


def test_service_lost_owner_marks_current_attempt_uncertain(tmp_path: Path) -> None:
    """Retain the active operation while withdrawing readiness and old completion."""

    session = ManagedServiceSession()
    session.m_manifest_path = tmp_path / "manifest.json"
    session.m_state = ManagedServiceSessionState(
        runtime_session_id="runtime",
        generation_id="generation",
        service_incarnation="incarnation",
        native_session_id="native-session",
        tmux_session_name="tmux",
        tmux_pane_id="%0",
        working_directory=str(tmp_path),
    )
    root = tmp_path / "service" / "incarnation"
    root.mkdir(parents=True)
    write_service_record(
        root / "last-observation.json",
        ManagedControlObservationV1(
            source="service_native",
            freshness="current",
            owner_available=True,
            connection_ready=True,
            can_accept_prompt_now=False,
            native_session_id="native-session",
            service_incarnation="incarnation",
            active_request_id="current",
            active_turn_id="turn-current",
            last_request_id="previous",
            last_outcome="completed",
        ),
    )
    observation = session.observe_managed_service()
    assert observation.freshness == "stale"
    assert observation.owner_available is False and observation.connection_ready is False
    assert observation.active_request_id == observation.last_request_id == "current"
    assert observation.last_outcome == "uncertain"


def test_service_descriptor_rejects_replaced_socket(tmp_path: Path) -> None:
    """Reject a newer socket even when the path and owning UID match."""

    directory = tmp_path / "socket"
    directory.mkdir(mode=0o700)
    path = directory / "owner.sock"
    birth = _dispatch_origin_birth_token(os.getpid())
    assert birth is not None
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as original:
        original.bind(str(path))
        path.chmod(0o600)
        entry = path.stat()
        descriptor = ServiceDescriptor(
            agent_id="agent",
            manifest_path=tmp_path / "manifest.json",
            runtime_session_id="runtime",
            generation_id="generation",
            service_incarnation="incarnation",
            native_session_id="native-session",
            owner_pid=os.getpid(),
            owner_birth_token=birth,
            native_pid=os.getpid(),
            native_birth_token=birth,
            socket_path=path,
            socket_device=entry.st_dev,
            socket_inode=entry.st_ino,
        )
        verify_service_socket(descriptor)
        with pytest.raises(ValueError, match="Stale or unsafe"):
            verify_service_socket(descriptor.model_copy(update={"owner_birth_token": "retired"}))
        path.unlink()
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as replacement:
            replacement.bind(str(path))
            path.chmod(0o600)
            with pytest.raises(ValueError, match="Stale or unsafe"):
                verify_service_socket(descriptor)
