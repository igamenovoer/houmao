"""Live FastAPI gateway companion process for one runtime-owned session."""

from __future__ import annotations

import argparse
import json
import os
import socket
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import ValidationError

from gig_agents.agents.realm_controller.errors import GatewayError, SessionManifestError
from gig_agents.agents.realm_controller.gateway_models import (
    GatewayAcceptedRequestV1,
    GatewayAdmissionState,
    GatewayAttachContractV1,
    GatewayAttachBackendMetadataCaoV1,
    GatewayConnectivityState,
    GatewayCurrentInstanceV1,
    GatewayExecutionState,
    GatewayHealthResponseV1,
    GatewayHost,
    GatewayJsonObject,
    GatewayRecoveryState,
    GatewayRequestCreateV1,
    GatewayRequestPayloadInterruptV1,
    GatewayRequestPayloadSubmitPromptV1,
    GatewayRequestKind,
    GatewayStatusV1,
)
from gig_agents.agents.realm_controller.gateway_storage import (
    append_gateway_event,
    delete_gateway_current_instance,
    gateway_health_response,
    gateway_paths_from_session_root,
    generate_gateway_request_id,
    load_attach_contract,
    load_gateway_current_instance,
    now_utc_iso,
    queue_depth_from_sqlite,
    write_gateway_current_instance,
    write_gateway_status,
)
from gig_agents.agents.realm_controller.manifest import (
    load_session_manifest,
    parse_session_manifest_payload,
)
from gig_agents.cao.rest_client import CaoApiError, CaoRestClient

_QUEUE_POLL_INTERVAL_SECONDS = 0.2
_GatewayRequestTerminalState = Literal["completed", "failed"]


@dataclass(frozen=True)
class _QueuedGatewayRequestRecord:
    """Durable queue record promoted into active execution.

    Attributes
    ----------
    request_id:
        Stable request identifier from the durable queue.
    request_kind:
        Public request kind being executed.
    payload_json:
        Serialized request payload stored in SQLite.
    managed_agent_instance_epoch:
        Managed-agent epoch captured when the request was accepted.
    """

    request_id: str
    request_kind: GatewayRequestKind
    payload_json: str
    managed_agent_instance_epoch: int


class CaoGatewayAdapter:
    """Gateway adapter for runtime-owned `cao_rest` sessions."""

    def __init__(self, *, attach_contract_path: Path) -> None:
        """Load CAO-specific gateway attach metadata.

        Parameters
        ----------
        attach_contract_path:
            Path to the strict gateway attach contract for the managed session.
        """

        self.m_attach_contract_path = attach_contract_path.resolve()
        self.m_attach_contract = load_attach_contract(self.m_attach_contract_path)
        metadata = self.m_attach_contract.backend_metadata
        if self.m_attach_contract.backend != "cao_rest":
            raise GatewayError(
                f"Gateway adapter only supports backend='cao_rest' in v1, got "
                f"{self.m_attach_contract.backend!r}."
            )
        metadata = cast(GatewayAttachBackendMetadataCaoV1, metadata)
        self.m_client = CaoRestClient(metadata.api_base_url)

    @property
    def attach_contract(self) -> GatewayAttachContractV1:
        """Return the strict attach contract."""

        return self.m_attach_contract

    def read_current_terminal_id(self) -> str:
        """Return the latest runtime-owned CAO terminal id."""

        manifest_path = self.m_attach_contract.manifest_path
        if manifest_path is None:
            metadata = cast(
                GatewayAttachBackendMetadataCaoV1,
                self.m_attach_contract.backend_metadata,
            )
            return metadata.terminal_id

        handle = load_session_manifest(Path(manifest_path))
        payload = parse_session_manifest_payload(handle.payload, source=str(handle.path))
        if payload.cao is None:
            raise GatewayError(
                "Runtime-owned CAO manifest is missing the `cao` payload required for "
                "gateway attach."
            )
        return payload.cao.terminal_id

    def inspect_connectivity(self, terminal_id: str) -> GatewayConnectivityState:
        """Return whether the addressed CAO terminal is reachable."""

        try:
            self.m_client.get_terminal(terminal_id)
        except CaoApiError:
            return "unavailable"
        return "connected"

    def submit_prompt(self, *, terminal_id: str, prompt: str) -> None:
        """Submit one prompt to the CAO terminal."""

        result = self.m_client.send_terminal_input(terminal_id, prompt)
        if not result.success:
            raise GatewayError("CAO prompt submission returned success=false.")

    def interrupt(self, *, terminal_id: str) -> None:
        """Interrupt the CAO terminal."""

        result = self.m_client.exit_terminal(terminal_id)
        if not result.success:
            raise GatewayError("CAO interrupt returned success=false.")


class GatewayServiceRuntime:
    """Mutable runtime for one live gateway process."""

    def __init__(self, *, gateway_root: Path, host: GatewayHost, port: int) -> None:
        """Initialize the gateway runtime state.

        Parameters
        ----------
        gateway_root:
            Gateway root or parent session root used to resolve gateway assets.
        host:
            Requested bind host for the live listener.
        port:
            Requested or resolved bind port for the live listener.
        """

        self.m_paths = gateway_paths_from_session_root(
            session_root=gateway_root.resolve().parent
            if gateway_root.resolve().name == "gateway"
            else gateway_root.resolve()
        )
        self.m_host: GatewayHost = host
        self.m_port: int = port
        self.m_attach_contract = load_attach_contract(self.m_paths.attach_path)
        self.m_adapter = CaoGatewayAdapter(attach_contract_path=self.m_paths.attach_path)
        self.m_lock = threading.Lock()
        self.m_stop_event = threading.Event()
        self.m_worker_thread: threading.Thread | None = None
        self.m_current_epoch = 1
        self.m_current_instance_id: str | None = None

    @classmethod
    def from_gateway_root(
        cls,
        *,
        gateway_root: Path,
        host: GatewayHost,
        port: int,
    ) -> "GatewayServiceRuntime":
        """Create a runtime from a runtime-owned gateway root.

        Parameters
        ----------
        gateway_root:
            Gateway root or session root used to locate gateway assets.
        host:
            Requested bind host for the gateway listener.
        port:
            Requested bind port for the gateway listener.

        Returns
        -------
        GatewayServiceRuntime
            Initialized service runtime.
        """

        return cls(gateway_root=gateway_root, host=host, port=port)

    def start(self) -> None:
        """Initialize current-instance state and start the queue worker."""

        with self.m_lock:
            self._mark_running_requests_failed()
            self._initialize_instance_state()
            self._refresh_status_snapshot(active_execution="idle")

        self.m_worker_thread = threading.Thread(
            target=self._worker_loop,
            name="gateway-worker",
            daemon=True,
        )
        self.m_worker_thread.start()

    def set_listener(self, *, host: GatewayHost, port: int) -> None:
        """Update the live listener bindings before runtime startup."""

        if port < 1 or port > 65535:
            raise GatewayError(f"Gateway listener port must be between 1 and 65535, got {port}.")
        self.m_host = host
        self.m_port = port

    def shutdown(self) -> None:
        """Stop the queue worker and remove ephemeral run metadata."""

        self.m_stop_event.set()
        if self.m_worker_thread is not None:
            self.m_worker_thread.join(timeout=2.0)
        with self.m_lock:
            delete_gateway_current_instance(self.m_paths)

    def health(self) -> GatewayHealthResponseV1:
        """Return the gateway-local health payload."""

        return gateway_health_response()

    def status(self) -> GatewayStatusV1:
        """Return the latest gateway status snapshot."""

        with self.m_lock:
            return self._refresh_status_snapshot(active_execution=self._active_execution_state())

    def create_request(self, request_payload: GatewayRequestCreateV1) -> GatewayAcceptedRequestV1:
        """Validate admission and persist one gateway-managed request."""

        with self.m_lock:
            status = self._refresh_status_snapshot(active_execution=self._active_execution_state())
            if status.request_admission == "blocked_reconciliation":
                raise HTTPException(
                    status_code=409,
                    detail="Gateway admission is blocked pending managed-agent reconciliation.",
                )
            if status.request_admission != "open":
                raise HTTPException(
                    status_code=503,
                    detail="Gateway admission is blocked because the managed agent is unavailable.",
                )

            request_id = generate_gateway_request_id()
            accepted_at_utc = now_utc_iso()
            payload_json = request_payload.payload.model_dump(mode="json")
            with sqlite3.connect(self.m_paths.queue_path) as connection:
                connection.execute(
                    """
                    INSERT INTO gateway_requests (
                        request_id,
                        request_kind,
                        payload_json,
                        state,
                        accepted_at_utc,
                        managed_agent_instance_epoch
                    )
                    VALUES (?, ?, ?, 'accepted', ?, ?)
                    """,
                    (
                        request_id,
                        request_payload.kind,
                        json.dumps(payload_json, sort_keys=True),
                        accepted_at_utc,
                        self.m_current_epoch,
                    ),
                )
                connection.commit()

            append_gateway_event(
                self.m_paths,
                {
                    "kind": "accepted",
                    "request_id": request_id,
                    "request_kind": request_payload.kind,
                    "accepted_at_utc": accepted_at_utc,
                },
            )
            status = self._refresh_status_snapshot(active_execution=self._active_execution_state())
            return GatewayAcceptedRequestV1(
                request_id=request_id,
                request_kind=request_payload.kind,
                state="accepted",
                accepted_at_utc=accepted_at_utc,
                queue_depth=status.queue_depth,
                managed_agent_instance_epoch=self.m_current_epoch,
            )

    def _worker_loop(self) -> None:
        """Process accepted requests serially until shutdown."""

        while not self.m_stop_event.is_set():
            request_record = self._take_next_request()
            if request_record is None:
                with self.m_lock:
                    self._refresh_status_snapshot(active_execution=self._active_execution_state())
                time.sleep(_QUEUE_POLL_INTERVAL_SECONDS)
                continue
            self._execute_request(request_record=request_record)

    def _take_next_request(self) -> _QueuedGatewayRequestRecord | None:
        """Promote the next accepted request into the running state.

        Returns
        -------
        _QueuedGatewayRequestRecord | None
            Next durable request ready for execution, if admission is open.
        """

        with self.m_lock:
            status = self._refresh_status_snapshot(active_execution=self._active_execution_state())
            if status.request_admission != "open":
                return None

            with sqlite3.connect(self.m_paths.queue_path) as connection:
                row = connection.execute(
                    """
                    SELECT request_id, request_kind, payload_json, managed_agent_instance_epoch
                    FROM gateway_requests
                    WHERE state = 'accepted'
                    ORDER BY accepted_at_utc ASC
                    LIMIT 1
                    """
                ).fetchone()
                if row is None:
                    return None
                request_id, request_kind, payload_json, epoch = row
                connection.execute(
                    """
                    UPDATE gateway_requests
                    SET state = 'running', started_at_utc = ?
                    WHERE request_id = ?
                    """,
                    (now_utc_iso(), request_id),
                )
                connection.commit()

            self._refresh_status_snapshot(active_execution="running")
            return _QueuedGatewayRequestRecord(
                request_id=str(request_id),
                request_kind=cast(GatewayRequestKind, request_kind),
                payload_json=str(payload_json),
                managed_agent_instance_epoch=int(epoch),
            )

    def _execute_request(self, *, request_record: _QueuedGatewayRequestRecord) -> None:
        """Execute one running request against the managed CAO terminal.

        Parameters
        ----------
        request_record:
            Durable queue record promoted into active execution.
        """

        request_id = request_record.request_id
        request_kind = request_record.request_kind
        payload_json = request_record.payload_json
        accepted_epoch = request_record.managed_agent_instance_epoch

        with self.m_lock:
            self._refresh_status_snapshot(active_execution="running")
            if accepted_epoch != self.m_current_epoch:
                self._finish_request(
                    request_id=request_id,
                    state="failed",
                    error_detail=(
                        "Request was accepted for a previous managed-agent instance epoch and "
                        "will not be replayed automatically."
                    ),
                    result_json=None,
                )
                return
            terminal_id = self.m_current_instance_id
            if terminal_id is None:
                self._finish_request(
                    request_id=request_id,
                    state="failed",
                    error_detail="Managed agent is unavailable.",
                    result_json=None,
                )
                return

        try:
            if request_kind == "submit_prompt":
                payload = GatewayRequestPayloadSubmitPromptV1.model_validate_json(payload_json)
                self.m_adapter.submit_prompt(terminal_id=terminal_id, prompt=payload.prompt)
            elif request_kind == "interrupt":
                GatewayRequestPayloadInterruptV1.model_validate_json(payload_json)
                self.m_adapter.interrupt(terminal_id=terminal_id)
            else:
                raise GatewayError(f"Unsupported gateway request kind: {request_kind!r}.")
        except (GatewayError, CaoApiError, ValidationError) as exc:
            self._finish_request(
                request_id=request_id,
                state="failed",
                error_detail=str(exc),
                result_json=None,
            )
            return

        self._finish_request(
            request_id=request_id,
            state="completed",
            error_detail=None,
            result_json={"request_kind": request_kind, "completed_at_utc": now_utc_iso()},
        )

    def _finish_request(
        self,
        *,
        request_id: str,
        state: _GatewayRequestTerminalState,
        error_detail: str | None,
        result_json: GatewayJsonObject | None,
    ) -> None:
        """Persist one completed or failed request outcome."""

        with self.m_lock, sqlite3.connect(self.m_paths.queue_path) as connection:
            connection.execute(
                """
                UPDATE gateway_requests
                SET state = ?, finished_at_utc = ?, error_detail = ?, result_json = ?
                WHERE request_id = ?
                """,
                (
                    state,
                    now_utc_iso(),
                    error_detail,
                    json.dumps(result_json, sort_keys=True) if result_json is not None else None,
                    request_id,
                ),
            )
            connection.commit()
            append_gateway_event(
                self.m_paths,
                {
                    "kind": state,
                    "request_id": request_id,
                    "error_detail": error_detail,
                    "result_json": result_json,
                },
            )
            self._refresh_status_snapshot(active_execution=self._active_execution_state())

    def _mark_running_requests_failed(self) -> None:
        """Mark requests left running by a prior gateway process as failed."""

        with sqlite3.connect(self.m_paths.queue_path) as connection:
            connection.execute(
                """
                UPDATE gateway_requests
                SET state = 'failed',
                    finished_at_utc = ?,
                    error_detail = ?
                WHERE state = 'running'
                """,
                (
                    now_utc_iso(),
                    "Gateway process restarted before request completion; request will not "
                    "be replayed automatically.",
                ),
            )
            connection.commit()

    def _initialize_instance_state(self) -> None:
        """Write the current-instance run-state payload."""

        previous_epoch = 0
        previous_instance_id: str | None = None
        try:
            previous = load_gateway_current_instance(self.m_paths.current_instance_path)
        except SessionManifestError:
            previous = None
        if previous is not None:
            previous_epoch = previous.managed_agent_instance_epoch
            previous_instance_id = previous.managed_agent_instance_id

        current_instance_id = self.m_adapter.read_current_terminal_id()
        if previous_instance_id is None or previous_instance_id == current_instance_id:
            self.m_current_epoch = max(previous_epoch, 1)
        else:
            self.m_current_epoch = previous_epoch + 1
        self.m_current_instance_id = current_instance_id

        write_gateway_current_instance(
            self.m_paths.current_instance_path,
            GatewayCurrentInstanceV1(
                pid=self._current_pid(),
                host=self.m_host,
                port=self.m_port,
                managed_agent_instance_epoch=self.m_current_epoch,
                managed_agent_instance_id=current_instance_id,
            ),
        )

    def _refresh_status_snapshot(
        self,
        *,
        active_execution: GatewayExecutionState,
    ) -> GatewayStatusV1:
        """Refresh and persist the current gateway status snapshot."""

        current_instance_id = self.m_adapter.read_current_terminal_id()
        if self.m_current_instance_id is None:
            self.m_current_instance_id = current_instance_id
        elif current_instance_id != self.m_current_instance_id:
            self.m_current_epoch += 1
            self.m_current_instance_id = current_instance_id

        connectivity = self.m_adapter.inspect_connectivity(current_instance_id)
        recovery: GatewayRecoveryState = "idle"
        admission: GatewayAdmissionState = "open"
        if connectivity != "connected":
            recovery = "awaiting_rebind"
            admission = "blocked_unavailable"
        elif self.m_current_epoch > 1:
            recovery = "reconciliation_required"
            admission = "blocked_reconciliation"

        status = GatewayStatusV1(
            attach_identity=self.m_attach_contract.attach_identity,
            backend=self.m_attach_contract.backend,
            tmux_session_name=self.m_attach_contract.tmux_session_name,
            gateway_health="healthy",
            managed_agent_connectivity=connectivity,
            managed_agent_recovery=recovery,
            request_admission=admission,
            terminal_surface_eligibility="ready" if connectivity == "connected" else "unknown",
            active_execution=active_execution,
            queue_depth=queue_depth_from_sqlite(self.m_paths.queue_path),
            gateway_host=self.m_host,
            gateway_port=self.m_port,
            managed_agent_instance_epoch=self.m_current_epoch,
            managed_agent_instance_id=self.m_current_instance_id,
        )
        write_gateway_status(self.m_paths.state_path, status)
        write_gateway_current_instance(
            self.m_paths.current_instance_path,
            GatewayCurrentInstanceV1(
                pid=self._current_pid(),
                host=self.m_host,
                port=self.m_port,
                managed_agent_instance_epoch=self.m_current_epoch,
                managed_agent_instance_id=self.m_current_instance_id,
            ),
        )
        return status

    def _active_execution_state(self) -> GatewayExecutionState:
        """Return whether a queue item is currently running."""

        with sqlite3.connect(self.m_paths.queue_path) as connection:
            row = connection.execute(
                """
                SELECT COUNT(*)
                FROM gateway_requests
                WHERE state = 'running'
                """
            ).fetchone()
        if row is None or int(row[0]) == 0:
            return "idle"
        return "running"

    def _current_pid(self) -> int:
        """Return the current process id."""

        return os.getpid()


def create_app(*, runtime: GatewayServiceRuntime) -> FastAPI:
    """Create the FastAPI app bound to one gateway runtime.

    Parameters
    ----------
    runtime:
        Gateway runtime backing the HTTP handlers.

    Returns
    -------
    FastAPI
        Configured FastAPI application.
    """

    app = FastAPI()

    @app.get("/health", response_model=GatewayHealthResponseV1)
    def _health() -> GatewayHealthResponseV1:
        """Serve the lightweight liveness route."""

        return runtime.health()

    @app.get("/v1/status", response_model=GatewayStatusV1)
    def _status() -> GatewayStatusV1:
        """Serve the structured gateway status snapshot."""

        return runtime.status()

    @app.post("/v1/requests", response_model=GatewayAcceptedRequestV1)
    def _create_request(request_payload: GatewayRequestCreateV1) -> GatewayAcceptedRequestV1:
        """Accept one gateway-managed request."""

        return runtime.create_request(request_payload)

    return app


class _GatewayUvicornServer(uvicorn.Server):
    """Uvicorn server wrapper that wires runtime startup after listener bind."""

    def __init__(
        self,
        config: uvicorn.Config,
        *,
        runtime: GatewayServiceRuntime,
        requested_host: GatewayHost,
    ) -> None:
        """Initialize the Uvicorn wrapper used by the gateway process.

        Parameters
        ----------
        config:
            Uvicorn server configuration.
        runtime:
            Gateway runtime started after the listener is bound.
        requested_host:
            Requested host passed to the bind operation.
        """

        super().__init__(config)
        self.m_runtime = runtime
        self.m_requested_host: GatewayHost = requested_host
        self.m_runtime_started = False

    async def startup(self, sockets: list[socket.socket] | None = None) -> None:
        """Bind the listener, resolve the actual port, then start the runtime."""

        await super().startup(sockets=sockets)
        if self.should_exit:
            return
        try:
            resolved_port = _bound_port_from_server(self)
            self.m_runtime.set_listener(
                host=self.m_requested_host,
                port=resolved_port,
            )
            self.m_runtime.start()
            self.m_runtime_started = True
        except Exception:
            if self.started:
                await super().shutdown(sockets=sockets)
            raise

    async def shutdown(self, sockets: list[socket.socket] | None = None) -> None:
        """Stop runtime-owned workers before shutting down the HTTP listener."""

        try:
            if self.m_runtime_started:
                self.m_runtime.shutdown()
        finally:
            await super().shutdown(sockets=sockets)


def _bound_port_from_server(server: uvicorn.Server) -> int:
    """Return the bound TCP port after Uvicorn listener startup.

    Parameters
    ----------
    server:
        Running Uvicorn server with initialized listener sockets.

    Returns
    -------
    int
        Resolved bound TCP port.
    """

    for listener in getattr(server, "servers", ()):
        sockets = getattr(listener, "sockets", None)
        if not sockets:
            continue
        sockname = sockets[0].getsockname()
        if isinstance(sockname, tuple) and len(sockname) >= 2:
            return int(sockname[1])
    raise GatewayError("Gateway server did not expose a bound TCP listener.")


def main(argv: list[str] | None = None) -> int:
    """Run the gateway companion process.

    Parameters
    ----------
    argv:
        Optional command-line arguments overriding `sys.argv[1:]`.

    Returns
    -------
    int
        Process exit code.
    """

    parser = argparse.ArgumentParser(description="Run one runtime-owned agent gateway.")
    parser.add_argument("--gateway-root", required=True)
    parser.add_argument("--host", required=True, choices=["127.0.0.1", "0.0.0.0"])
    parser.add_argument("--port", required=True, type=int)
    args = parser.parse_args(argv)

    gateway_root = Path(args.gateway_root).resolve()
    runtime = GatewayServiceRuntime.from_gateway_root(
        gateway_root=gateway_root,
        host=args.host,
        port=int(args.port),
    )
    app = create_app(runtime=runtime)
    config = uvicorn.Config(
        app,
        host=args.host,
        port=int(args.port),
        log_level="warning",
        access_log=False,
    )
    server = _GatewayUvicornServer(
        config,
        runtime=runtime,
        requested_host=cast(GatewayHost, args.host),
    )
    server.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
