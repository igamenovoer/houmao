"""Private client and provider contract for an owned persistent native service."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager, suppress
from dataclasses import dataclass, field
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import select
import shlex
import signal
import socket
import stat
import sys
import time
from typing import Any, Literal, Protocol
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from houmao.agents.model_selection import ModelConfig
from houmao.agents.realm_controller.backends.dispatch_control import (
    HeadlessDispatchControl,
    _dispatch_origin_birth_token,
)
from houmao.agents.realm_controller.backends.headless_runner import (
    HeadlessProcessMetadata,
    _pinned_worker,
    _signal_worker,
)
from houmao.agents.realm_controller.backends.tmux_runtime import (
    cleanup_tmux_session,
    create_tmux_session,
    has_tmux_session,
    list_tmux_panes,
    prepare_headless_agent_window,
    run_tmux,
    TmuxCommandError,
    TmuxPaneRecord,
)
from houmao.agents.realm_controller.errors import BackendExecutionError
from houmao.agents.realm_controller.managed_control import ManagedControlObservationV1
from houmao.agents.realm_controller.models import (
    BackendKind,
    HeadlessTurnSessionSelection,
    LaunchPlan,
    RelaunchChatSessionSelection,
    SessionControlResult,
    SessionEvent,
)
from houmao.execution.tmux import tmux_server_scope


_MAX_FRAME = 16 * 1024 * 1024
_PROMPT_TIMEOUT = 360.0
ServiceOutcome = Literal["completed", "interrupted", "failed", "uncertain"]
ServiceRequestState = Literal[
    "reserved", "submitting", "handed_off", "completed", "interrupted", "failed", "uncertain"
]


class ServiceOwnerConfig(BaseModel):
    """Private startup material consumed by the exact owner inside tmux."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    backend: BackendKind
    executable: str
    arguments: list[str]
    working_directory: Path
    home_path: Path
    environment: dict[str, str]
    metadata: dict[str, Any]
    role_prompt: str | None = None
    root: Path
    manifest_path: Path
    agent_id: str
    runtime_session_id: str
    generation_id: str
    service_incarnation: str
    session_id: str | None = None


@dataclass(frozen=True)
class ServiceOperationContext:
    """Bind one native frame to its authorized request and private evidence path."""

    request_id: str
    turn_dir: Path
    authorize_native_write: Callable[[], None]
    record_handoff: Callable[[str | None], None]
    publish_event: Callable[[SessionEvent], None]

    def confirm_native_handoff(self, native_turn_id: str | None = None) -> None:
        """Record evidence of this request at the provider's actual handoff boundary."""

        self.record_handoff(native_turn_id)


@dataclass(frozen=True)
class ServicePromptResult:
    """Return semantic provider events and exact terminal attribution.

    After authorizing native input, report uncertainty if the provider may
    have accepted work whose outcome cannot be attributed to this request.
    """

    events: list[SessionEvent] = field(default_factory=list)
    outcome: ServiceOutcome = "uncertain"
    native_turn_id: str | None = None


class ServiceProvider(Protocol):
    """One initialized persistent native connection owned by the supervisor."""

    @property
    def native_session_id(self) -> str: ...

    @property
    def connection_ready(self) -> bool: ...

    @property
    def process_id(self) -> int: ...

    @property
    def process_birth_token(self) -> str | None: ...

    def prompt(
        self,
        prompt: str,
        *,
        execution_model: ModelConfig | None,
        operation: ServiceOperationContext,
    ) -> ServicePromptResult: ...

    def cancel(self, operation_id: str) -> bool: ...

    def close(self) -> None: ...


class ServiceRequestSnapshot(BaseModel):
    """Durable request state bound to one service incarnation and native session."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    request_id: str
    generation_id: str
    service_incarnation: str
    native_session_id: str
    native_turn_id: str | None = None
    state: ServiceRequestState
    accepted_at_utc: str
    handoff_at_utc: str | None = None
    completed_at_utc: str | None = None
    events: list[SessionEvent] = Field(default_factory=list)


class ManagedServiceSessionState(BaseModel):
    """Secret-free backend manifest state. No socket details cross this boundary."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    runtime_session_id: str
    generation_id: str
    service_incarnation: str
    native_session_id: str
    tmux_session_name: str
    tmux_pane_id: str
    working_directory: str
    tmux_window_id: str | None = None

    @classmethod
    def from_payload(cls, payload: object) -> ManagedServiceSessionState:
        """Read a persisted binding without starting a provider."""

        return cls.model_validate(payload)

    def to_payload(self) -> dict[str, Any]:
        """Return backend authority suitable for the private manifest."""

        return self.model_dump(mode="json")


class ServiceDescriptor(BaseModel):
    """Owner socket and process identities published only in private runtime storage."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    agent_id: str
    manifest_path: Path
    runtime_session_id: str
    generation_id: str
    service_incarnation: str
    native_session_id: str
    owner_pid: int
    owner_birth_token: str
    native_pid: int
    native_birth_token: str
    socket_path: Path
    socket_device: int
    socket_inode: int


class ServiceRequest(BaseModel):
    """Finite service owner operations on a verified private local connection."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    operation: Literal["probe", "observe", "prompt", "interrupt", "stop"]
    generation_id: str
    service_incarnation: str
    request_id: str | None = None
    prompt: str | None = None
    execution_model: ModelConfig | None = None


def service_now() -> str:
    """Return a timestamp with enough precision to compare admission boundaries."""

    return datetime.now(UTC).isoformat(timespec="microseconds")


def service_component(value: str) -> str:
    """Use only one directory component for a private authority reference."""

    if value in {"", ".", ".."} or Path(value).name != value or any(c in value for c in "\x00\r\n"):
        raise BackendExecutionError("Invalid service authority identity")
    return value


def service_turn_dir(manifest: Path, request_id: str) -> Path:
    """Locate the common owner reservation's exact artifact directory."""

    return manifest.parent / f"{manifest.stem}.turn-artifacts" / service_component(request_id)


def write_service_record(path: Path, value: BaseModel | dict[str, Any]) -> None:
    """Atomically store a private data record, including process and native identity."""

    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else value
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, separators=(",", ":"))
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def read_service_record(path: Path) -> bytes:
    """Open only a bounded, owner-private regular file without following links."""

    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        entry = os.fstat(stream.fileno())
        if not stat.S_ISREG(entry.st_mode) or entry.st_uid != os.geteuid() or entry.st_mode & 0o077:
            raise ValueError("Service record must remain private")
        payload = stream.read(_MAX_FRAME + 1)
        if len(payload) > _MAX_FRAME:
            raise ValueError("Service record exceeds its read bound")
        return payload


class ManagedServiceSession:
    """Reconnect manager and gateway callers to one long-lived private owner."""

    def __init__(self) -> None:
        """Initialize a controller with no authority until its factory binds it."""

        self.m_plan: LaunchPlan | None = None
        self.m_manifest_path: Path | None = None
        self.m_state: ManagedServiceSessionState | None = None
        self.m_dispatch_control: HeadlessDispatchControl | None = None
        self.m_force_cleanup: bool = False
        self.m_prompt_request_id: str | None = None

    @classmethod
    def from_launch_plan(
        cls,
        *,
        launch_plan: LaunchPlan,
        session_manifest_path: Path,
        role_name: str | None = None,
        agent_def_dir: Path | None = None,
        tmux_session_name: str | None = None,
        state: ManagedServiceSessionState | None = None,
        provider_start: bool = False,
        session_id: str | None = None,
    ) -> ManagedServiceSession:
        """Start a provider at birth or reconstruct a saved private controller."""

        del role_name, agent_def_dir
        instance = cls()
        instance.m_plan = launch_plan
        instance.m_manifest_path = session_manifest_path.resolve()
        instance.m_state = state
        if provider_start:
            instance._start_owner(tmux_session_name=tmux_session_name, session_id=session_id)
        elif (
            state is None
            or Path(state.working_directory) != launch_plan.working_directory.resolve()
        ):
            raise BackendExecutionError(
                "Service reconstruction requires its saved owner and workspace"
            )
        return instance

    @property
    def backend(self) -> BackendKind:
        """Return the backend belonging to the saved service owner."""

        return self.plan.backend

    @property
    def plan(self) -> LaunchPlan:
        """Return the immutable launch configuration for the managed home."""

        if self.m_plan is None:
            raise BackendExecutionError("Service launch configuration is unavailable")
        return self.m_plan

    @property
    def state(self) -> ManagedServiceSessionState:
        """Return the saved service identity without requiring a live listener."""

        if self.m_state is None:
            raise BackendExecutionError("Service owner identity is unavailable")
        return self.m_state

    @property
    def manifest_path(self) -> Path:
        """Return the canonical private owner manifest path."""

        if self.m_manifest_path is None:
            raise BackendExecutionError("Service manifest path is unavailable")
        return self.m_manifest_path

    def runtime_state_payload(self) -> dict[str, Any]:
        """Persist the mode's current execution identity."""

        return self.state.to_payload()

    def update_launch_plan(self, launch_plan: LaunchPlan) -> None:
        """Advance generation metadata while preserving the service home and workspace."""

        if (
            launch_plan.backend != self.backend
            or launch_plan.home_path.resolve() != self.plan.home_path.resolve()
            or launch_plan.working_directory.resolve() != self.plan.working_directory.resolve()
        ):
            raise BackendExecutionError("Service relaunch requires its recorded home and workspace")
        self.m_plan = launch_plan

    def configure_stop_force_cleanup(self, *, force_cleanup: bool) -> None:
        """Select whether explicit stop also removes the owned tmux envelope."""

        self.m_force_cleanup = force_cleanup

    def set_force_cleanup(self, force_cleanup: bool) -> None:
        """Select exact envelope cleanup using the shared lifecycle setting."""

        self.configure_stop_force_cleanup(force_cleanup=force_cleanup)

    def configure_request_dispatch(self, control: HeadlessDispatchControl | None) -> None:
        """Use this caller's per-request dispatch permission and handoff callback."""

        self.m_dispatch_control = control

    def close(self) -> None:
        """Release caller-local state without closing the persistent provider."""

        self.m_dispatch_control = None

    def close_control_connection(self) -> None:
        """Release local connection state without stopping the owner."""

        self.close()

    def _owner_root(self, incarnation: str) -> Path:
        """Resolve a private incarnation-specific descriptor directory."""

        return self.manifest_path.parent / "service" / service_component(incarnation)

    def _managed_identity(self) -> dict[str, str]:
        """Read the explicit runtime identity selected by lifecycle authority."""

        identity = self.plan.metadata.get("managed_service_identity")
        if not isinstance(identity, dict) or any(
            not isinstance(identity.get(key), str) or not identity[key]
            for key in ("agent_id", "runtime_session_id", "generation")
        ):
            raise BackendExecutionError("Service launch requires its exact managed generation")
        return {key: str(identity[key]) for key in ("agent_id", "runtime_session_id", "generation")}

    def _socket_scope(self) -> AbstractContextManager[None]:
        """Select the saved tmux server for every supervisor lifecycle operation."""

        recorded = self.plan.metadata.get("tmux_socket_path")
        binding = self.plan.execution_binding
        socket_path = (binding.tmux_socket if binding is not None else None) or recorded
        if not isinstance(socket_path, str) or not socket_path:
            raise BackendExecutionError("Service lifecycle requires its recorded tmux server")
        return tmux_server_scope(socket_path)

    def _saved_supervisor_pane(self) -> TmuxPaneRecord:
        """Find the exact saved pane, including a stopped supervisor retaining its pane."""

        state = self.state
        candidates = [
            pane
            for pane in list_tmux_panes(session_name=state.tmux_session_name)
            if pane.pane_id == state.tmux_pane_id
            and pane.window_index == "0"
            and (state.tmux_window_id is None or pane.window_id == state.tmux_window_id)
        ]
        if len(candidates) != 1:
            raise BackendExecutionError("Service tmux owner identity changed")
        return candidates[0]

    def _start_owner(self, *, tmux_session_name: str | None, session_id: str | None) -> None:
        """Launch a fresh owner in the recorded tmux server and await native readiness."""

        identity = self._managed_identity()
        incarnation = uuid4().hex
        root = self._owner_root(incarnation)
        root.mkdir(parents=True, mode=0o700)
        root.parent.chmod(0o700)
        name = tmux_session_name or f"HOUMAO-service-{incarnation[:12]}"
        config = ServiceOwnerConfig(
            backend=self.backend,
            executable=self.plan.executable,
            arguments=list(self.plan.args),
            working_directory=self.plan.working_directory.resolve(),
            home_path=self.plan.home_path.resolve(),
            environment={
                **{
                    key: os.environ[key]
                    for key in ("PATH", "LANG", "LC_ALL", "TMPDIR")
                    if key in os.environ
                },
                **self.plan.env,
            },
            metadata=dict(self.plan.metadata),
            role_prompt=self.plan.role_injection.prompt,
            root=root,
            manifest_path=self.manifest_path,
            agent_id=identity["agent_id"],
            runtime_session_id=identity["runtime_session_id"],
            generation_id=identity["generation"],
            service_incarnation=incarnation,
            session_id=session_id,
        )
        path = root / "startup.json"
        write_service_record(path, config)
        created = False
        try:
            with self._socket_scope():
                if has_tmux_session(session_name=name).returncode != 0:
                    create_tmux_session(
                        session_name=name, working_directory=config.working_directory
                    )
                    created = True
                elif self.m_state is None or self.state.tmux_session_name != name:
                    raise BackendExecutionError(
                        "Service refuses to reuse an unrelated tmux session"
                    )
                surface = (
                    prepare_headless_agent_window(session_name=name, fresh_session=True)
                    if created
                    else self._saved_supervisor_pane()
                )
                deadline = time.monotonic() + 1.0
                while not created and not surface.pane_dead:
                    if time.monotonic() >= deadline:
                        raise BackendExecutionError("Old service supervisor pane has not stopped")
                    time.sleep(0.02)
                    surface = self._saved_supervisor_pane()
                command = "exec " + shlex.join(
                    [
                        sys.executable,
                        "-m",
                        "houmao.agents.realm_controller.backends.service_owner",
                        "--input",
                        str(path),
                    ]
                )
                if run_tmux(
                    ["set-option", "-w", "-t", surface.window_id, "remain-on-exit", "on"]
                ).returncode:
                    raise BackendExecutionError("Service supervisor pane could not be retained")
                if run_tmux(["respawn-pane", "-k", "-t", surface.pane_id, command]).returncode:
                    raise BackendExecutionError("Service supervisor could not be launched")
            deadline = time.monotonic() + 45.0
            while time.monotonic() < deadline:
                if (root / "startup-failure.json").is_file():
                    raise BackendExecutionError(
                        "Native service startup failed; inspect its private diagnostics"
                    )
                if (root / "descriptor.json").is_file():
                    descriptor = self._read_descriptor(
                        incarnation, generation=identity["generation"]
                    )
                    if descriptor.runtime_session_id != identity["runtime_session_id"]:
                        raise BackendExecutionError("Service supervisor reached the wrong runtime")
                    response = self._exchange(descriptor, "probe")
                    if response.get("native_session_id") != descriptor.native_session_id:
                        raise BackendExecutionError(
                            "Service startup did not establish native session authority"
                        )
                    self.m_state = ManagedServiceSessionState(
                        runtime_session_id=descriptor.runtime_session_id,
                        generation_id=descriptor.generation_id,
                        service_incarnation=incarnation,
                        native_session_id=descriptor.native_session_id,
                        tmux_session_name=name,
                        tmux_pane_id=surface.pane_id,
                        tmux_window_id=surface.window_id,
                        working_directory=str(config.working_directory),
                    )
                    return
                time.sleep(0.05)
            raise BackendExecutionError("Native service startup timed out")
        except BaseException:
            with suppress(OSError, ValueError, BackendExecutionError):
                startup = json.loads(read_service_record(root / "startup-owner.json"))
                if (
                    isinstance(startup, dict)
                    and startup.get("service_incarnation") == incarnation
                    and startup.get("generation_id") == identity["generation"]
                    and type(startup.get("pid")) is int
                    and isinstance(startup.get("birth_token"), str)
                ):
                    _stop_service_process(startup["pid"], startup["birth_token"])
            if created:
                with self._socket_scope():
                    cleanup_tmux_session(session_name=name)
            raise
        finally:
            path.unlink(missing_ok=True)

    def _read_descriptor(self, incarnation: str, *, generation: str) -> ServiceDescriptor:
        """Read the exact private descriptor without following a replacement socket."""

        try:
            descriptor = ServiceDescriptor.model_validate_json(
                read_service_record(self._owner_root(incarnation) / "descriptor.json")
            )
        except (OSError, ValueError):
            raise BackendExecutionError("Service descriptor is unavailable") from None
        if (
            descriptor.manifest_path != self.manifest_path
            or descriptor.generation_id != generation
            or descriptor.service_incarnation != incarnation
            or descriptor.agent_id != self._managed_identity()["agent_id"]
        ):
            raise BackendExecutionError("Service descriptor belongs to another owner generation")
        return descriptor

    def _descriptor(self) -> ServiceDescriptor:
        """Bind the exact currently selected native service to its descriptor."""

        state = self.state
        descriptor = self._read_descriptor(
            state.service_incarnation, generation=state.generation_id
        )
        if (
            descriptor.runtime_session_id != state.runtime_session_id
            or descriptor.native_session_id != state.native_session_id
        ):
            raise BackendExecutionError("Service descriptor has a different native identity")
        return descriptor

    def _exchange(
        self,
        descriptor: ServiceDescriptor,
        operation: Literal["probe", "observe", "prompt", "interrupt", "stop"],
        *,
        request_id: str | None = None,
        prompt: str | None = None,
        execution_model: ModelConfig | None = None,
        handoff: Callable[[], None] | None = None,
    ) -> dict[str, Any]:
        """Use the private socket once. A broken response never retries native input."""

        request = ServiceRequest(
            operation=operation,
            generation_id=descriptor.generation_id,
            service_incarnation=descriptor.service_incarnation,
            request_id=request_id,
            prompt=prompt,
            execution_model=execution_model,
        )
        payload = request.model_dump_json().encode() + b"\n"
        if len(payload) > _MAX_FRAME:
            raise BackendExecutionError("Service request exceeds its private transport bound")
        try:
            verify_service_socket(descriptor)
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                client.settimeout(_PROMPT_TIMEOUT if operation == "prompt" else 3.0)
                client.connect(str(descriptor.socket_path))
                if service_peer(client) != (descriptor.owner_pid, os.geteuid()):
                    raise ValueError("Service socket peer does not match its descriptor")
                client.sendall(payload)
                with client.makefile("rb") as stream:
                    while line := stream.readline(_MAX_FRAME + 1):
                        if len(line) > _MAX_FRAME or not line.endswith(b"\n"):
                            raise ValueError("Service response exceeded its bound")
                        result = json.loads(line)
                        if not isinstance(result, dict):
                            raise ValueError("Invalid service response")
                        if result.get("handoff") is True:
                            if handoff is not None:
                                handoff()
                            continue
                        if result.get("ok") is not True:
                            detail = result.get("detail")
                            raise BackendExecutionError(
                                detail
                                if isinstance(detail, str)
                                else "Service operation was refused"
                            )
                        return result
        except (OSError, ValueError):
            raise BackendExecutionError(
                "Service connection was lost or failed identity verification"
            ) from None
        raise BackendExecutionError("Service owner closed its response before settlement")

    def observe_managed_service(self) -> ManagedControlObservationV1:
        """Report live owner and provider readiness, or attributable stale evidence."""

        try:
            result = self._exchange(self._descriptor(), "observe")
            return ManagedControlObservationV1.model_validate(result["observation"])
        except (BackendExecutionError, KeyError, ValueError):
            state = self.state
            root = self._owner_root(state.service_incarnation)
            try:
                saved = ManagedControlObservationV1.model_validate_json(
                    read_service_record(root / "last-observation.json")
                )
            except (OSError, ValueError):
                saved = ManagedControlObservationV1(
                    source="service_native",
                    freshness="unknown",
                    native_session_id=state.native_session_id,
                    service_incarnation=state.service_incarnation,
                )
            unavailable: dict[str, Any] = {
                "freshness": "stale",
                "owner_available": False,
                "connection_ready": False,
                "can_accept_prompt_now": False,
            }
            if saved.active_request_id is not None:
                request = self._read_snapshot(saved.active_request_id)
                if request is not None and request.state in {"completed", "interrupted", "failed"}:
                    unavailable.update(
                        active_request_id=None,
                        active_turn_id=None,
                        last_request_id=request.request_id,
                        last_turn_id=request.native_turn_id,
                        last_outcome=request.state,
                    )
                else:
                    unavailable.update(
                        last_request_id=saved.active_request_id,
                        last_turn_id=saved.active_turn_id,
                        last_outcome="uncertain",
                    )
            return saved.model_copy(update=unavailable)

    def read_request(self, request_id: str) -> ServiceRequestSnapshot | None:
        """Read exact durable evidence independently of the caller and live pipes."""

        request = self._read_snapshot(request_id)
        if request is not None and request.state in {"reserved", "submitting", "handed_off"}:
            current = self.observe_managed_service()
            if current.owner_available is not True or current.connection_ready is not True:
                return request.model_copy(update={"state": "uncertain"})
        return request

    def _read_snapshot(self, request_id: str) -> ServiceRequestSnapshot | None:
        """Accept only durable snapshots tied to the currently selected incarnation."""

        path = service_turn_dir(self.manifest_path, request_id) / "service-request.json"
        try:
            request = ServiceRequestSnapshot.model_validate_json(read_service_record(path))
        except (OSError, ValueError):
            return None
        state = self.state
        if (
            request.request_id != request_id
            or request.generation_id != state.generation_id
            or request.service_incarnation != state.service_incarnation
            or request.native_session_id != state.native_session_id
        ):
            return None
        return request

    def send_prompt(
        self,
        prompt: str,
        *,
        turn_artifact_dir_name: str | None = None,
        session_selection: HeadlessTurnSessionSelection | None = None,
        execution_model: ModelConfig | None = None,
    ) -> list[SessionEvent]:
        """Submit once to the currently bound provider without replacing its connection."""

        from houmao.agents.realm_controller.owner_admission import reserve_owner_prompt

        if not prompt.strip() or (
            session_selection is not None
            and (
                session_selection.mode != "exact"
                or session_selection.session_id != self.state.native_session_id
            )
        ):
            raise BackendExecutionError(
                "Service input requires a prompt and its bound native conversation"
            )
        control = self.m_dispatch_control
        request_id = turn_artifact_dir_name or f"svc-{uuid4().hex}"
        if control is None:
            claim = reserve_owner_prompt(
                self.manifest_path,
                self.state.generation_id,
                request_id=request_id,
                origin="runtime",
            )
            control = HeadlessDispatchControl.from_callbacks(
                allowed=claim.active,
                confirmed=claim.handoff,
                deadline=time.monotonic() + _PROMPT_TIMEOUT,
                manifest_path=self.manifest_path,
                generation_id=self.state.generation_id,
            )
        turn = service_turn_dir(self.manifest_path, request_id)
        turn.mkdir(parents=True, exist_ok=True, mode=0o700)
        control.prepare_bridge_permission(turn)
        self.m_prompt_request_id = request_id
        try:
            self._exchange(
                self._descriptor(),
                "prompt",
                request_id=request_id,
                prompt=prompt,
                execution_model=execution_model,
                handoff=control.confirm_durable_handoff,
            )
        finally:
            self.m_prompt_request_id = None
        settled = self.read_request(request_id)
        if (
            settled is None
            or settled.completed_at_utc is None
            or settled.state
            not in {
                "completed",
                "interrupted",
                "failed",
                "uncertain",
            }
        ):
            raise BackendExecutionError(
                "Service prompt has no attributable settlement; it was not retried"
            )
        if settled.handoff_at_utc is not None:
            control.confirm_durable_handoff()
        return [
            *settled.events,
            SessionEvent(
                kind="done",
                message=f"Native service outcome: {settled.state}",
                turn_index=settled.events[-1].turn_index if settled.events else 0,
                payload={
                    "outcome": settled.state,
                    "request_id": request_id,
                    "native_turn_id": settled.native_turn_id,
                },
            ),
        ]

    def cancel_request_dispatch(self, control: HeadlessDispatchControl) -> None:
        """Revoke this attempt and cancel only that same operation if it crossed the wire."""

        control.cancel()
        request = self.m_prompt_request_id
        if self.m_dispatch_control is control and request is not None:
            self.interrupt(operation_id=request)

    def interrupt(self, operation_id: str | None = None) -> SessionControlResult:
        """Fence cancellation to an exact operation captured before the request."""

        target = operation_id or self.observe_managed_service().active_request_id
        if target is None:
            return SessionControlResult(
                status="ok", action="interrupt", detail="No active service operation"
            )
        try:
            response = self._exchange(self._descriptor(), "interrupt", request_id=target)
        except BackendExecutionError as error:
            return SessionControlResult(status="error", action="interrupt", detail=str(error))
        return SessionControlResult(status="ok", action="interrupt", detail=str(response["detail"]))

    def plugin_execution_identity(self) -> tuple[str, ...]:
        """Return the verified generation and live native service binding."""

        current = self.observe_managed_service()
        if current.owner_available is not True or current.connection_ready is not True:
            raise BackendExecutionError("Native service connection is unavailable")
        return (
            self.state.generation_id,
            self.state.service_incarnation,
            self.state.native_session_id,
        )

    def terminate(self) -> SessionControlResult:
        """Stop only the selected owner and optionally remove its exact tmux envelope."""

        state = self.state
        try:
            descriptor = self._descriptor()
            if _dispatch_origin_birth_token(descriptor.owner_pid) == descriptor.owner_birth_token:
                try:
                    self._exchange(descriptor, "stop")
                except BackendExecutionError:
                    _stop_service_process(descriptor.owner_pid, descriptor.owner_birth_token)
            deadline = time.monotonic() + 10.0
            while any(
                (
                    _dispatch_origin_birth_token(descriptor.owner_pid)
                    == descriptor.owner_birth_token,
                    _dispatch_origin_birth_token(descriptor.native_pid)
                    == descriptor.native_birth_token,
                )
            ):
                if time.monotonic() >= deadline:
                    _stop_service_process(descriptor.owner_pid, descriptor.owner_birth_token)
                    _stop_service_process(descriptor.native_pid, descriptor.native_birth_token)
                    break
                if (
                    _dispatch_origin_birth_token(descriptor.owner_pid)
                    != descriptor.owner_birth_token
                ):
                    _stop_service_process(descriptor.native_pid, descriptor.native_birth_token)
                    break
                time.sleep(0.05)
            _remove_retired_service_socket(descriptor)
            if self.m_force_cleanup:
                with self._socket_scope():
                    if has_tmux_session(session_name=state.tmux_session_name).returncode == 0:
                        self._saved_supervisor_pane()
                        cleanup_tmux_session(session_name=state.tmux_session_name)
        except (OSError, TmuxCommandError, BackendExecutionError) as error:
            return SessionControlResult(status="error", action="terminate", detail=str(error))
        return SessionControlResult(
            status="ok", action="terminate", detail="Stopped the owned service"
        )

    def relaunch(
        self, *, chat_session: RelaunchChatSessionSelection | None = None
    ) -> SessionControlResult:
        """Explicitly start a new service incarnation with new or exact native selection."""

        selection = chat_session or RelaunchChatSessionSelection(mode="new")
        if selection.mode not in {"exact", "new"} or (
            selection.mode == "exact" and selection.session_id != self.state.native_session_id
        ):
            return SessionControlResult(
                status="error",
                action="relaunch",
                detail="Service relaunch requires new or its exact recorded native session",
            )
        force_cleanup, self.m_force_cleanup = self.m_force_cleanup, False
        previous = self.state
        try:
            stopped = self.terminate()
            if stopped.status != "ok":
                return SessionControlResult(
                    status="error", action="relaunch", detail=stopped.detail
                )
            self._start_owner(
                tmux_session_name=previous.tmux_session_name, session_id=selection.session_id
            )
        except (OSError, TmuxCommandError, BackendExecutionError) as error:
            return SessionControlResult(status="error", action="relaunch", detail=str(error))
        finally:
            self.m_force_cleanup = force_cleanup
        return SessionControlResult(
            status="ok", action="relaunch", detail="Relaunched the owned service"
        )


def _stop_service_process(pid: int, birth_token: str) -> None:
    """Escalate only the descriptor's exact process when orderly shutdown is unavailable."""

    if _dispatch_origin_birth_token(pid) != birth_token:
        return
    try:
        metadata = HeadlessProcessMetadata(child_pid=pid, child_birth_token=birth_token)
        with _pinned_worker(metadata) as descriptor:
            poll = select.poll()
            poll.register(descriptor, select.POLLIN)
            _signal_worker(descriptor, signal.SIGTERM)
            if not poll.poll(1500):
                _signal_worker(descriptor, signal.SIGKILL)
                if not poll.poll(1000):
                    raise BackendExecutionError("Owned service process cleanup has not settled")
    except (OSError, ValueError) as error:
        if _dispatch_origin_birth_token(pid) == birth_token:
            raise BackendExecutionError(
                "Owned service process could not be safely stopped"
            ) from error


def _remove_retired_service_socket(descriptor: ServiceDescriptor) -> None:
    """Remove only the recorded short socket after its exact owner has exited."""

    path = descriptor.socket_path
    prefix = f"houmao-svc-{os.geteuid()}-"
    if (
        path.name != "owner.sock"
        or path.parent.parent != Path("/tmp")
        or not path.parent.name.startswith(prefix)
        or _dispatch_origin_birth_token(descriptor.owner_pid) == descriptor.owner_birth_token
    ):
        return
    with suppress(OSError):
        parent = path.parent.lstat()
        entry = path.lstat()
        if (
            stat.S_ISDIR(parent.st_mode)
            and parent.st_uid == os.geteuid()
            and not parent.st_mode & 0o077
            and stat.S_ISSOCK(entry.st_mode)
            and entry.st_uid == os.geteuid()
            and entry.st_dev == descriptor.socket_device
            and entry.st_ino == descriptor.socket_inode
        ):
            path.unlink()
            path.parent.rmdir()


def verify_service_socket(descriptor: ServiceDescriptor) -> None:
    """Verify daemon, socket inode, and owner-private parent before connection."""

    path = descriptor.socket_path
    parent = path.parent.lstat()
    entry = path.lstat()
    if (
        _dispatch_origin_birth_token(descriptor.owner_pid) != descriptor.owner_birth_token
        or not stat.S_ISDIR(parent.st_mode)
        or parent.st_uid != os.geteuid()
        or parent.st_mode & 0o077
        or not stat.S_ISSOCK(entry.st_mode)
        or entry.st_uid != os.geteuid()
        or entry.st_mode & 0o077
        or entry.st_dev != descriptor.socket_device
        or entry.st_ino != descriptor.socket_inode
    ):
        raise ValueError("Stale or unsafe service socket")


def service_peer(connection: socket.socket) -> tuple[int, int]:
    """Read effective process and user identity from the kernel's private socket peer."""

    import struct

    if not hasattr(socket, "SO_PEERCRED"):
        raise OSError("Private service peer identity is unavailable")
    pid, uid, _ = struct.unpack(
        "3i", connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
    )
    return pid, uid
