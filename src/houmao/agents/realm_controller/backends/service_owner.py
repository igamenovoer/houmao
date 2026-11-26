"""Supervise a single persistent native connection behind a private Unix socket."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from contextlib import suppress
from dataclasses import asdict
import json
import os
from pathlib import Path
import signal
import socketserver
import tempfile
import threading
import time
from typing import Any, cast

from houmao.agents.realm_controller.backends.dispatch_control import (
    _dispatch_origin_birth_token,
    headless_dispatch_permission_allowed,
)
from houmao.agents.realm_controller.backends.headless_bridge import (
    _adopted_children,
    _own_detached_descendants,
)
from houmao.agents.realm_controller.backends.service_runtime import (
    _MAX_FRAME,
    ServiceDescriptor,
    ServiceOperationContext,
    ServiceOutcome,
    ServiceOwnerConfig,
    ServicePromptResult,
    ServiceProvider,
    ServiceRequest,
    ServiceRequestSnapshot,
    read_service_record,
    service_now,
    service_peer,
    service_turn_dir,
    write_service_record,
)
from houmao.agents.realm_controller.errors import (
    BackendExecutionError,
    ServiceStartupCompatibilityError,
)
from houmao.agents.realm_controller.managed_control import ManagedControlObservationV1
from houmao.agents.realm_controller.models import SessionEvent
from houmao.agents.realm_controller.owner_admission import OwnerPromptClaim


_RETAINED_EVENTS = 256


class ServiceOwner:
    """Serialize full native operations while keeping state and cancellation available."""

    def __init__(self, config: ServiceOwnerConfig, provider: ServiceProvider) -> None:
        """Bind the owned provider and keep attribution independent of a socket caller."""

        self.m_config: ServiceOwnerConfig = config
        self.m_provider: ServiceProvider = provider
        self.m_lock: threading.RLock = threading.RLock()
        self.m_stopping: threading.Event = threading.Event()
        self.m_active: ServiceRequestSnapshot | None = None
        self.m_last: ServiceRequestSnapshot | None = None
        self.m_cancelling: str | None = None
        self.m_unresolved: bool = False

    @property
    def stopping(self) -> threading.Event:
        """Expose the process owner's terminal shutdown signal."""

        return self.m_stopping

    def handle(
        self, request: ServiceRequest, *, caller_pid: int, emit: Callable[[dict[str, Any]], None]
    ) -> dict[str, Any]:
        """Dispatch a finite operation only to this exact service incarnation."""

        config = self.m_config
        if (
            request.generation_id != config.generation_id
            or request.service_incarnation != config.service_incarnation
        ):
            raise BackendExecutionError("Service request addresses a retired owner")
        operation = request.operation
        if operation == "prompt":
            if request.request_id is None or request.prompt is None or not request.prompt.strip():
                raise BackendExecutionError(
                    "Service prompt requires exact request identity and input"
                )
            snapshot = self._prompt(request, caller_pid=caller_pid, emit=emit)
            return {"request": snapshot.model_dump(mode="json")}
        if request.prompt is not None or request.execution_model is not None:
            raise BackendExecutionError("Unexpected payload for service operation")
        if operation == "interrupt":
            if request.request_id is None:
                raise BackendExecutionError(
                    "Service interruption requires exact operation identity"
                )
            return {"detail": self._interrupt(request.request_id)}
        if request.request_id is not None:
            raise BackendExecutionError("Unexpected request identity for service operation")
        if operation == "probe":
            if self.m_stopping.is_set() or not self.m_provider.connection_ready:
                raise BackendExecutionError("Native service connection is unavailable")
            return {"native_session_id": self.m_provider.native_session_id}
        if operation == "stop":
            self.stop()
            return {"detail": "Service owner is shutting down"}
        return {"observation": self.observe().model_dump(mode="json")}

    def _claim(self, request_id: str) -> OwnerPromptClaim:
        """Address the same generation-qualified reservation used by all front doors."""

        return OwnerPromptClaim(
            self.m_config.manifest_path, self.m_config.generation_id, request_id, "service"
        )

    def _check_input(self, claim: OwnerPromptClaim, caller_pid: int, turn_dir: Path) -> None:
        """Bind caller kernel identity, expiry, and the live registry reservation."""

        from houmao.agents.realm_controller.runtime import require_active_managed_control_manifest

        guard = turn_dir / ".dispatch-permission.json"
        try:
            proof = json.loads(read_service_record(guard))
            valid = (
                isinstance(proof, dict)
                and proof.get("origin_pid") == caller_pid
                and proof.get("attempt_id") == claim.request_id
                and proof.get("manifest_path") == str(claim.manifest_path)
                and proof.get("registry_generation_id") == claim.generation_id
                and headless_dispatch_permission_allowed(guard)
                and claim.active()
            )
            if valid:
                config = self.m_config
                authority = require_active_managed_control_manifest(
                    config.manifest_path,
                    generation_id=config.generation_id,
                    agent_id=config.agent_id,
                )
                valid = (
                    authority.runtime.session_id == config.runtime_session_id
                    and authority.backend == config.backend
                    and authority.mode == "service"
                    and authority.backend_state.get("service_incarnation")
                    == config.service_incarnation
                    and authority.backend_state.get("native_session_id")
                    == self.m_provider.native_session_id
                    and headless_dispatch_permission_allowed(guard)
                )
        except (OSError, ValueError, RuntimeError):
            valid = False
        if not valid or self.m_stopping.is_set():
            raise BackendExecutionError("Service input permission is unavailable or revoked")

    def _prompt(
        self, request: ServiceRequest, *, caller_pid: int, emit: Callable[[dict[str, Any]], None]
    ) -> ServiceRequestSnapshot:
        """Own a request from private acceptance until an attributable native result."""

        assert request.request_id is not None and request.prompt is not None
        request_id = request.request_id
        claim = self._claim(request_id)
        turn_dir = service_turn_dir(self.m_config.manifest_path, request_id)
        record = turn_dir / "service-request.json"
        with self.m_lock:
            self._check_input(claim, caller_pid, turn_dir)
            if (
                self.m_active is not None
                or self.m_cancelling is not None
                or self.m_unresolved
                or not self.m_provider.connection_ready
            ):
                raise BackendExecutionError("Service owner cannot admit another operation")
            if record.exists():
                raise BackendExecutionError("Service owner has already observed this request")
            self._save_active(
                ServiceRequestSnapshot(
                    request_id=request_id,
                    generation_id=self.m_config.generation_id,
                    service_incarnation=self.m_config.service_incarnation,
                    native_session_id=self.m_provider.native_session_id,
                    state="reserved",
                    accepted_at_utc=service_now(),
                ),
                record,
            )

        def authorize() -> None:
            """Make the last revocation check immediately before the provider write."""

            with self.m_lock:
                snapshot = self._require_active(request_id)
                if snapshot.state != "reserved" or self.m_cancelling == request_id:
                    raise BackendExecutionError("Service request no longer owns the native write")
                self._check_input(claim, caller_pid, turn_dir)
                self._save_active(snapshot.model_copy(update={"state": "submitting"}), record)

        def handoff(native_turn_id: str | None) -> None:
            """Persist actual native acceptance before notifying the optional live caller."""

            first = False
            with self.m_lock:
                snapshot = self._require_active(request_id)
                if snapshot.state not in {"submitting", "handed_off"}:
                    raise BackendExecutionError(
                        "Service received native acceptance before authorized write"
                    )
                if native_turn_id is not None and snapshot.native_turn_id not in {
                    None,
                    native_turn_id,
                }:
                    raise BackendExecutionError("Service native turn identity changed")
                first = snapshot.handoff_at_utc is None
                self._save_active(
                    snapshot.model_copy(
                        update={
                            "state": "handed_off",
                            "handoff_at_utc": snapshot.handoff_at_utc or service_now(),
                            "native_turn_id": native_turn_id or snapshot.native_turn_id,
                        }
                    ),
                    record,
                )
                if first:
                    claim.handoff()
            if first:
                emit({"handoff": True})

        def publish(event: SessionEvent) -> None:
            """Store a bounded progress suffix without retaining the submitted prompt."""

            with self.m_lock:
                snapshot = self._require_active(request_id)
                events = _retain_events([*snapshot.events, event])
                self._save_active(snapshot.model_copy(update={"events": events}), record)

        operation = ServiceOperationContext(request_id, turn_dir, authorize, handoff, publish)
        try:
            result = self.m_provider.prompt(
                request.prompt, execution_model=request.execution_model, operation=operation
            )
        except Exception:
            with self.m_lock:
                snapshot = self._require_active(request_id)
                result = ServicePromptResult(
                    outcome="failed" if snapshot.state == "reserved" else "uncertain"
                )

        with self.m_lock:
            snapshot = self._require_active(request_id)
            outcome: ServiceOutcome = result.outcome
            if snapshot.state == "reserved" and outcome in {"completed", "interrupted"}:
                outcome = "failed"
            if snapshot.state == "submitting" and outcome in {"completed", "interrupted"}:
                handoff(result.native_turn_id)
                snapshot = self._require_active(request_id)
            if snapshot.native_turn_id is not None and result.native_turn_id not in {
                None,
                snapshot.native_turn_id,
            }:
                outcome = "uncertain"
            terminal = snapshot.model_copy(
                update={
                    "state": outcome,
                    "completed_at_utc": service_now(),
                    "native_turn_id": snapshot.native_turn_id or result.native_turn_id,
                    "events": _retain_events(result.events or snapshot.events),
                }
            )
            write_service_record(record, terminal)
            self.m_active = None
            self.m_last = terminal
            self.m_unresolved = outcome == "uncertain"
            self.observe(persist=True)
            claim.finish(outcome, evidence="service_native" if outcome != "uncertain" else None)
        return terminal

    def _require_active(self, request_id: str) -> ServiceRequestSnapshot:
        """Refuse a late provider callback from a different request."""

        snapshot = self.m_active
        if snapshot is None or snapshot.request_id != request_id:
            raise BackendExecutionError("Service request no longer owns native work")
        return snapshot

    def _save_active(self, snapshot: ServiceRequestSnapshot, record: Path) -> None:
        """Update durable operation evidence before publishing its observation."""

        write_service_record(record, snapshot)
        self.m_active = snapshot
        self.observe(persist=True)

    def _interrupt(self, request_id: str) -> str:
        """Keep a later request out until the exact current cancellation settles."""

        with self.m_lock:
            snapshot = self.m_active
            if snapshot is None or snapshot.request_id != request_id:
                raise BackendExecutionError("Service operation has settled or changed")
            if self.m_cancelling is not None:
                raise BackendExecutionError("Service cancellation already in progress")
            self.m_cancelling = request_id
        try:
            if not self.m_provider.cancel(request_id):
                raise BackendExecutionError(
                    "Provider could not verify this exact service cancellation"
                )
            return "Cancellation sent to the captured service operation"
        finally:
            with self.m_lock:
                if self.m_cancelling == request_id:
                    self.m_cancelling = None

    def observe(self, *, persist: bool = False) -> ManagedControlObservationV1:
        """Distinguish a living owner from current native provider readiness."""

        with self.m_lock:
            active, last = self.m_active, self.m_last
            if active is None and self.m_unresolved:
                active = last
            ready = not self.m_stopping.is_set() and self.m_provider.connection_ready
            observation = ManagedControlObservationV1(
                source="service_native",
                freshness="current",
                observed_at_utc=service_now(),
                owner_available=True,
                connection_ready=ready,
                can_accept_prompt_now=ready and active is None and self.m_cancelling is None,
                service_incarnation=self.m_config.service_incarnation,
                native_session_id=self.m_provider.native_session_id,
                active_request_id=active.request_id if active is not None else None,
                active_turn_id=active.native_turn_id if active is not None else None,
                last_request_id=last.request_id if last is not None else None,
                last_turn_id=last.native_turn_id if last is not None else None,
                last_outcome=_outcome(last),
            )
            if persist:
                write_service_record(self.m_config.root / "last-observation.json", observation)
            return observation

    def stop(self) -> None:
        """Refuse future input before beginning bounded native cleanup."""

        self.m_stopping.set()


def _outcome(snapshot: ServiceRequestSnapshot | None) -> ServiceOutcome | None:
    """Return only actual terminal state vocabulary in the public observation."""

    if snapshot is not None and snapshot.state in {
        "completed",
        "interrupted",
        "failed",
        "uncertain",
    }:
        return cast(ServiceOutcome, snapshot.state)
    return None


def _retain_events(events: list[SessionEvent]) -> list[SessionEvent]:
    """Retain a recent suffix within both the durable record and response bounds."""

    remaining = _MAX_FRAME // 2
    retained: list[SessionEvent] = []
    for event in reversed(events[-_RETAINED_EVENTS:]):
        size = len(json.dumps(asdict(event), ensure_ascii=False).encode("utf-8"))
        remaining -= size
        if remaining <= 0:
            break
        retained.append(event)
    return list(reversed(retained))


class _ServiceServer(socketserver.ThreadingUnixStreamServer):
    """Provide one private bounded framing channel under the exact owner."""

    daemon_threads = True
    block_on_close = False

    def __init__(self, path: Path, owner: ServiceOwner) -> None:
        self.m_owner: ServiceOwner = owner
        super().__init__(str(path), _ServiceHandler)
        self.timeout = 0.1


class _ServiceHandler(socketserver.StreamRequestHandler):
    """Verify same-account kernel credentials before decoding a finite request."""

    def handle(self) -> None:
        """Serve one read or mutation, retaining durable evidence if the caller disconnects."""

        assert isinstance(self.server, _ServiceServer)
        self.connection.settimeout(5.0)
        write_lock = threading.Lock()

        def emit(payload: dict[str, Any]) -> None:
            """Write complete bounded notices without letting caller loss stop native work."""

            data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode() + b"\n"
            if len(data) > _MAX_FRAME:
                data = b'{"ok":false,"detail":"Service response exceeded its bound"}\n'
            with write_lock, suppress(OSError):
                self.connection.sendall(data)

        try:
            caller_pid, caller_uid = service_peer(self.connection)
            if caller_uid != os.geteuid() or caller_pid <= 0:
                raise BackendExecutionError("Service caller does not own this socket")
            data = self.rfile.readline(_MAX_FRAME + 1)
            if len(data) > _MAX_FRAME or not data.endswith(b"\n"):
                raise BackendExecutionError("Invalid or oversized service request")
            request = ServiceRequest.model_validate_json(data)
            response = self.server.m_owner.handle(request, caller_pid=caller_pid, emit=emit)
            emit({"ok": True, **response})
        except BackendExecutionError as error:
            emit({"ok": False, "detail": str(error)})
        except (OSError, ValueError, RuntimeError):
            emit({"ok": False, "detail": "Service owner could not verify the request"})


def _provider(config: ServiceOwnerConfig) -> ServiceProvider:
    """Select a packaged adapter, never an import path supplied by a requester."""

    if config.backend == "dsh_acp":
        from houmao.agents.realm_controller.backends.dsh_acp_service import (
            create_dsh_service_provider,
        )

        return create_dsh_service_provider(config)
    if config.backend == "kimi_acp":
        from houmao.agents.realm_controller.backends.kimi_acp_service import (
            create_kimi_service_provider,
        )

        return create_kimi_service_provider(config)
    if config.backend == "codex_app_server":
        from houmao.agents.realm_controller.backends.codex_app_server import (
            create_codex_service_provider,
        )

        return create_codex_service_provider(config)
    if config.backend == "hermes_service":
        from houmao.agents.realm_controller.backends.hermes_acp_service import (
            create_hermes_service_provider,
        )

        return create_hermes_service_provider(config)
    raise BackendExecutionError("Selected native service provider is unsupported")


def _serve(config: ServiceOwnerConfig, provider: ServiceProvider) -> None:
    """Publish the initialized native binding and retain the one owner until stop."""

    owner = ServiceOwner(config, provider)

    def stop(_signum: int, _frame: object) -> None:
        """The signal handler only ends admission; the owner performs cleanup."""

        owner.stop()

    for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(signum, stop)
    birth = _dispatch_origin_birth_token(os.getpid())
    native_birth = provider.process_birth_token
    if (
        birth is None
        or native_birth is None
        or not provider.connection_ready
        or _dispatch_origin_birth_token(provider.process_id) != native_birth
        or (config.session_id is not None and provider.native_session_id != config.session_id)
    ):
        raise BackendExecutionError(
            "Native service did not initialize its exact process and session"
        )
    with tempfile.TemporaryDirectory(prefix=f"houmao-svc-{os.geteuid()}-", dir="/tmp") as temporary:
        socket_path = Path(temporary) / "owner.sock"
        with _ServiceServer(socket_path, owner) as server:
            socket_path.chmod(0o600)
            entry = socket_path.stat()
            descriptor = ServiceDescriptor(
                agent_id=config.agent_id,
                manifest_path=config.manifest_path,
                runtime_session_id=config.runtime_session_id,
                generation_id=config.generation_id,
                service_incarnation=config.service_incarnation,
                native_session_id=provider.native_session_id,
                owner_pid=os.getpid(),
                owner_birth_token=birth,
                native_pid=provider.process_id,
                native_birth_token=native_birth,
                socket_path=socket_path,
                socket_device=entry.st_dev,
                socket_inode=entry.st_ino,
            )
            owner.observe(persist=True)
            write_service_record(config.root / "descriptor.json", descriptor)
            while not owner.stopping.is_set():
                server.handle_request()


def _close(provider: ServiceProvider) -> None:
    """Close native pipes then kill only detached descendants adopted by this owner."""

    try:
        provider.close()
    finally:
        deadline = time.monotonic() + 2.0
        while children := _adopted_children(provider.process_id):
            for child in children:
                with suppress(ChildProcessError, ProcessLookupError):
                    reaped, _ = os.waitpid(child, os.WNOHANG)
                    if not reaped:
                        os.kill(child, signal.SIGKILL)
            if time.monotonic() >= deadline:
                raise BackendExecutionError("Native descendant cleanup did not settle")
            time.sleep(0.01)


def main() -> int:
    """Read one private startup record and run only its owned provider."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    path = parser.parse_args().input
    os.umask(0o077)
    config = ServiceOwnerConfig.model_validate_json(read_service_record(path))
    path.unlink()
    provider = None
    try:

        def cancel_startup(_signum: int, _frame: object) -> None:
            """Unwind an interrupted startup so the provider can close its partial connection."""

            raise KeyboardInterrupt

        for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            signal.signal(signum, cancel_startup)
        pid = os.getpid()
        birth = _dispatch_origin_birth_token(pid)
        if birth is None:
            raise BackendExecutionError("Starting service owner process is unavailable")
        write_service_record(
            config.root / "startup-owner.json",
            {
                "pid": pid,
                "birth_token": birth,
                "service_incarnation": config.service_incarnation,
                "generation_id": config.generation_id,
            },
        )
        _own_detached_descendants()
        provider = _provider(config)
        _serve(config, provider)
        return 0
    except (Exception, KeyboardInterrupt) as error:
        failure = {"error": type(error).__name__}
        if isinstance(error, ServiceStartupCompatibilityError):
            failure["check"] = error.check.name
        write_service_record(config.root / "startup-failure.json", failure)
        return 1
    finally:
        if provider is not None:
            _close(provider)


if __name__ == "__main__":
    raise SystemExit(main())
