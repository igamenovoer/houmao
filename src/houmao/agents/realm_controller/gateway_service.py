"""Live FastAPI gateway companion process for one runtime-owned session."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol, cast

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import ValidationError

from houmao.agents.mailbox_runtime_support import resolved_mailbox_config_from_payload
from houmao.agents.mailbox_runtime_models import MailboxResolvedConfig
from houmao.agents.realm_controller.errors import GatewayError, SessionManifestError
from houmao.agents.realm_controller.errors import LaunchPlanError
from houmao.agents.realm_controller.gateway_mailbox import (
    GatewayMailboxAdapter,
    GatewayMailboxError,
    build_gateway_mailbox_adapter,
)
from houmao.agents.realm_controller.gateway_models import (
    GatewayAcceptedRequestV1,
    GatewayAdmissionState,
    GatewayAttachBackendMetadataCaoV1,
    GatewayAttachBackendMetadataHeadlessV1,
    GatewayAttachContractV1,
    GatewayAttachBackendMetadataHoumaoServerV1,
    GatewayConnectivityState,
    GatewayCurrentInstanceV1,
    GatewayExecutionState,
    GatewayHealthResponseV1,
    GatewayHost,
    GatewayMailActionResponseV1,
    GatewayMailCheckRequestV1,
    GatewayMailCheckResponseV1,
    GatewayMailReplyRequestV1,
    GatewayMailSendRequestV1,
    GatewayMailStatusV1,
    GatewayJsonObject,
    GatewayMailNotifierPutV1,
    GatewayMailNotifierStatusV1,
    GatewayRecoveryState,
    GatewayRequestCreateV1,
    GatewayRequestPayloadInterruptV1,
    GatewayRequestPayloadSubmitPromptV1,
    GatewaySurfaceEligibilityState,
    GatewayStoredRequestKind,
    GatewayStatusV1,
)
from houmao.agents.realm_controller.gateway_storage import (
    GatewayNotifierAuditUnreadMessage,
    append_gateway_event,
    append_gateway_notifier_audit_record,
    build_gateway_mail_notifier_status,
    delete_gateway_current_instance,
    gateway_health_response,
    gateway_paths_from_session_root,
    generate_gateway_request_id,
    load_attach_contract,
    load_gateway_current_instance,
    read_gateway_mail_notifier_record,
    now_utc_iso,
    queue_depth_from_sqlite,
    write_gateway_mail_notifier_record,
    write_gateway_current_instance,
    write_gateway_status,
)
from houmao.agents.realm_controller.manifest import (
    load_session_manifest,
    parse_session_manifest_payload,
)
from houmao.agents.realm_controller.runtime import resume_runtime_session
from houmao.agents.realm_controller.backends.tmux_runtime import tmux_session_exists
from houmao.cao.rest_client import CaoApiError, CaoRestClient
from houmao.server.client import HoumaoServerClient
from houmao.server.models import (
    HoumaoManagedAgentInterruptRequest,
    HoumaoManagedAgentSubmitPromptRequest,
)

_QUEUE_POLL_INTERVAL_SECONDS = 0.2
_NOTIFIER_IDLE_CHECK_INTERVAL_SECONDS = 0.2
_NOTIFIER_RATE_LIMIT_SECONDS = 30.0
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
    request_kind: GatewayStoredRequestKind
    payload_json: str
    managed_agent_instance_epoch: int


@dataclass(frozen=True)
class _UnreadMailboxMessage:
    """Unread mailbox message summary used for notifier prompts."""

    message_ref: str
    thread_ref: str | None
    created_at_utc: str
    subject: str


@dataclass(frozen=True)
class _GatewayTargetState:
    """Execution posture for the currently addressed gateway target."""

    instance_id: str
    connectivity: GatewayConnectivityState
    terminal_surface_eligibility: GatewaySurfaceEligibilityState
    prompt_admission_open: bool


class GatewayExecutionAdapter(Protocol):
    """Execution adapter boundary for one gateway-managed target."""

    @property
    def attach_contract(self) -> GatewayAttachContractV1:
        """Return the strict attach contract."""

    def inspect_target(self) -> _GatewayTargetState:
        """Return current target posture for status and reconciliation."""

    def submit_prompt(self, *, prompt: str) -> None:
        """Submit one prompt to the addressed managed target."""

    def interrupt(self) -> None:
        """Interrupt the addressed managed target."""


class _RestBackedGatewayAdapter:
    """Execution adapter for runtime-owned REST-backed tmux sessions."""

    def __init__(self, *, attach_contract: GatewayAttachContractV1) -> None:
        """Load CAO-specific gateway attach metadata.

        Parameters
        ----------
        attach_contract:
            Strict gateway attach contract for the managed session.
        """

        self.m_attach_contract = attach_contract
        metadata = attach_contract.backend_metadata
        if self.m_attach_contract.backend not in {"cao_rest", "houmao_server_rest"}:
            raise GatewayError(
                "Gateway adapter only supports backend in "
                "{'cao_rest', 'houmao_server_rest'} in v1, got "
                f"{self.m_attach_contract.backend!r}."
            )
        if self.m_attach_contract.backend == "cao_rest":
            cao_metadata = cast(GatewayAttachBackendMetadataCaoV1, metadata)
            self.m_client = CaoRestClient(cao_metadata.api_base_url)
        else:
            houmao_metadata = cast(GatewayAttachBackendMetadataHoumaoServerV1, metadata)
            self.m_client = CaoRestClient(
                houmao_metadata.api_base_url,
                path_prefix="/cao",
            )

    @property
    def attach_contract(self) -> GatewayAttachContractV1:
        """Return the strict attach contract."""

        return self.m_attach_contract

    def inspect_target(self) -> _GatewayTargetState:
        """Return current execution posture for the REST-backed target."""

        terminal_id = self._read_current_terminal_id()
        connectivity = self._inspect_connectivity(terminal_id)
        return _GatewayTargetState(
            instance_id=terminal_id,
            connectivity=connectivity,
            terminal_surface_eligibility="ready" if connectivity == "connected" else "unknown",
            prompt_admission_open=connectivity == "connected",
        )

    def submit_prompt(self, *, prompt: str) -> None:
        """Submit one prompt to the current runtime-owned terminal."""

        terminal_id = self._read_current_terminal_id()
        result = self.m_client.send_terminal_input(terminal_id, prompt)
        if not result.success:
            raise GatewayError("CAO prompt submission returned success=false.")

    def interrupt(self) -> None:
        """Interrupt the current runtime-owned terminal."""

        terminal_id = self._read_current_terminal_id()
        result = self.m_client.exit_terminal(terminal_id)
        if not result.success:
            raise GatewayError("CAO interrupt returned success=false.")

    def _read_current_terminal_id(self) -> str:
        """Return the latest runtime-owned CAO terminal id."""

        manifest_path = self.m_attach_contract.manifest_path
        if manifest_path is None:
            if self.m_attach_contract.backend == "cao_rest":
                cao_metadata = cast(
                    GatewayAttachBackendMetadataCaoV1,
                    self.m_attach_contract.backend_metadata,
                )
                return cao_metadata.terminal_id

            houmao_metadata = cast(
                GatewayAttachBackendMetadataHoumaoServerV1,
                self.m_attach_contract.backend_metadata,
            )
            return houmao_metadata.terminal_id

        handle = load_session_manifest(Path(manifest_path))
        payload = parse_session_manifest_payload(handle.payload, source=str(handle.path))
        if self.m_attach_contract.backend == "cao_rest":
            if payload.cao is None:
                raise GatewayError(
                    "Runtime-owned CAO manifest is missing the `cao` payload required for "
                    "gateway attach."
                )
            return payload.cao.terminal_id
        if payload.houmao_server is None:
            raise GatewayError(
                "Runtime-owned houmao-server manifest is missing the `houmao_server` payload "
                "required for gateway attach."
            )
        return payload.houmao_server.terminal_id

    def _inspect_connectivity(self, terminal_id: str) -> GatewayConnectivityState:
        """Return whether the addressed CAO terminal is reachable."""

        try:
            self.m_client.get_terminal(terminal_id)
        except CaoApiError:
            return "unavailable"
        return "connected"


class _LocalHeadlessGatewayAdapter:
    """Execution adapter for runtime-owned local headless sessions."""

    def __init__(self, *, attach_contract: GatewayAttachContractV1) -> None:
        """Resume local runtime authority from the strict attach contract."""

        self.m_attach_contract = attach_contract
        if attach_contract.backend not in {"claude_headless", "codex_headless", "gemini_headless"}:
            raise GatewayError(
                "Local headless gateway adapter only supports native headless backends, got "
                f"{attach_contract.backend!r}."
            )
        manifest_path_value = attach_contract.manifest_path
        agent_def_dir_value = attach_contract.agent_def_dir
        if manifest_path_value is None or agent_def_dir_value is None:
            raise GatewayError(
                "Headless gateway attach requires manifest_path and agent_def_dir in the attach contract."
            )
        try:
            self.m_controller = resume_runtime_session(
                agent_def_dir=Path(agent_def_dir_value).expanduser().resolve(),
                session_manifest_path=Path(manifest_path_value).expanduser().resolve(),
            )
        except (LaunchPlanError, SessionManifestError, RuntimeError) as exc:
            raise GatewayError(f"Failed to resume runtime-owned headless session: {exc}") from exc
        self.m_instance_id = attach_contract.runtime_session_id or attach_contract.attach_identity

    @property
    def attach_contract(self) -> GatewayAttachContractV1:
        """Return the strict attach contract."""

        return self.m_attach_contract

    def inspect_target(self) -> _GatewayTargetState:
        """Return current execution posture for the local headless target."""

        connected = tmux_session_exists(session_name=self.m_attach_contract.tmux_session_name)
        connectivity: GatewayConnectivityState = "connected" if connected else "unavailable"
        return _GatewayTargetState(
            instance_id=self.m_instance_id,
            connectivity=connectivity,
            terminal_surface_eligibility="ready" if connected else "unknown",
            prompt_admission_open=connected,
        )

    def submit_prompt(self, *, prompt: str) -> None:
        """Submit one prompt through resumed local headless runtime control."""

        self._require_live_tmux_session()
        try:
            self.m_controller.send_prompt(prompt)
        except RuntimeError as exc:
            raise GatewayError(f"Local headless prompt submission failed: {exc}") from exc

    def interrupt(self) -> None:
        """Interrupt one resumed local headless runtime."""

        self._require_live_tmux_session()
        result = self.m_controller.interrupt()
        if result.status != "ok":
            raise GatewayError(result.detail)

    def _require_live_tmux_session(self) -> None:
        """Require the headless tmux session to still be live."""

        if not tmux_session_exists(session_name=self.m_attach_contract.tmux_session_name):
            raise GatewayError(
                f"Headless tmux session `{self.m_attach_contract.tmux_session_name}` is unavailable."
            )


class _ServerManagedHeadlessGatewayAdapter:
    """Execution adapter for server-managed native headless agents."""

    def __init__(self, *, attach_contract: GatewayAttachContractV1) -> None:
        """Initialize the server-managed headless execution adapter."""

        self.m_attach_contract = attach_contract
        if attach_contract.backend not in {"claude_headless", "codex_headless", "gemini_headless"}:
            raise GatewayError(
                "Server-managed headless gateway adapter only supports native headless backends, "
                f"got {attach_contract.backend!r}."
            )
        metadata = cast(
            GatewayAttachBackendMetadataHeadlessV1,
            attach_contract.backend_metadata,
        )
        if metadata.managed_api_base_url is None or metadata.managed_agent_ref is None:
            raise GatewayError(
                "Server-managed headless gateway adapter requires managed_api_base_url and "
                "managed_agent_ref metadata."
            )
        self.m_managed_agent_ref = metadata.managed_agent_ref
        self.m_client = HoumaoServerClient(metadata.managed_api_base_url)

    @property
    def attach_contract(self) -> GatewayAttachContractV1:
        """Return the strict attach contract."""

        return self.m_attach_contract

    def inspect_target(self) -> _GatewayTargetState:
        """Return current execution posture for the server-managed target."""

        try:
            response = self.m_client.get_managed_agent_state_detail(self.m_managed_agent_ref)
        except CaoApiError:
            return _GatewayTargetState(
                instance_id=self.m_managed_agent_ref,
                connectivity="unavailable",
                terminal_surface_eligibility="unknown",
                prompt_admission_open=False,
            )
        detail = response.detail
        if detail.transport != "headless":
            raise GatewayError(
                "Server-managed headless gateway adapter resolved a non-headless managed agent."
            )
        connectivity: GatewayConnectivityState = (
            "connected" if response.summary_state.availability == "available" else "unavailable"
        )
        can_accept_prompt_now = detail.can_accept_prompt_now
        return _GatewayTargetState(
            instance_id=response.tracked_agent_id,
            connectivity=connectivity,
            terminal_surface_eligibility=(
                "ready"
                if can_accept_prompt_now
                else ("not_ready" if connectivity == "connected" else "unknown")
            ),
            prompt_admission_open=can_accept_prompt_now,
        )

    def submit_prompt(self, *, prompt: str) -> None:
        """Submit one prompt through the managed-agent server API."""

        response = self.m_client.submit_managed_agent_request(
            self.m_managed_agent_ref,
            HoumaoManagedAgentSubmitPromptRequest(prompt=prompt),
        )
        if response.disposition != "accepted":
            raise GatewayError(f"Managed-agent prompt request did not execute: {response.detail}")

    def interrupt(self) -> None:
        """Interrupt the managed-agent target through the server API."""

        self.m_client.submit_managed_agent_request(
            self.m_managed_agent_ref,
            HoumaoManagedAgentInterruptRequest(),
        )


def _build_gateway_execution_adapter(
    *,
    attach_contract: GatewayAttachContractV1,
) -> GatewayExecutionAdapter:
    """Build the execution adapter for one gateway attach contract."""

    if attach_contract.backend in {"cao_rest", "houmao_server_rest"}:
        return _RestBackedGatewayAdapter(attach_contract=attach_contract)
    if attach_contract.backend in {"claude_headless", "codex_headless", "gemini_headless"}:
        metadata = cast(
            GatewayAttachBackendMetadataHeadlessV1,
            attach_contract.backend_metadata,
        )
        if metadata.managed_api_base_url is not None and metadata.managed_agent_ref is not None:
            return _ServerManagedHeadlessGatewayAdapter(attach_contract=attach_contract)
        return _LocalHeadlessGatewayAdapter(attach_contract=attach_contract)
    raise GatewayError(
        f"Gateway execution adapter is not implemented for backend={attach_contract.backend!r}."
    )


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
        self.m_adapter: GatewayExecutionAdapter = _build_gateway_execution_adapter(
            attach_contract=self.m_attach_contract
        )
        self.m_lock = threading.Lock()
        self.m_log_lock = threading.Lock()
        self.m_stop_event = threading.Event()
        self.m_worker_thread: threading.Thread | None = None
        self.m_notifier_thread: threading.Thread | None = None
        self.m_current_epoch = 1
        self.m_current_instance_id: str | None = None
        self.m_rate_limited_logs: dict[str, tuple[float, int]] = {}
        self.m_mailbox_adapter: GatewayMailboxAdapter | None = None
        self.m_mailbox_bindings_version: str | None = None

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
            self._log(
                f"gateway started host={self.m_host} port={self.m_port} attach_identity={self.m_attach_contract.attach_identity}"
            )

        self.m_worker_thread = threading.Thread(
            target=self._worker_loop,
            name="gateway-worker",
            daemon=True,
        )
        self.m_worker_thread.start()
        self.m_notifier_thread = threading.Thread(
            target=self._notifier_loop,
            name="gateway-mail-notifier",
            daemon=True,
        )
        self.m_notifier_thread.start()

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
        if self.m_notifier_thread is not None:
            self.m_notifier_thread.join(timeout=2.0)
        with self.m_lock:
            self._flush_rate_limited_logs()
            self._log("gateway stopping")
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
            self._log(
                f"accepted public gateway request request_id={request_id} kind={request_payload.kind}"
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

    def get_mail_status(self) -> GatewayMailStatusV1:
        """Return shared mailbox availability for the attached session."""

        with self.m_lock:
            self._require_loopback_mail_surface()
            try:
                return self._mailbox_adapter_locked().status()
            except GatewayError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc

    def check_mail(self, request_payload: GatewayMailCheckRequestV1) -> GatewayMailCheckResponseV1:
        """Run one shared mailbox check request."""

        with self.m_lock:
            self._require_loopback_mail_surface()
            try:
                adapter = self._mailbox_adapter_locked()
            except GatewayError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            try:
                messages = adapter.check(
                    unread_only=request_payload.unread_only,
                    limit=request_payload.limit,
                    since=request_payload.since,
                )
            except GatewayMailboxError as exc:
                raise HTTPException(status_code=502, detail=str(exc)) from exc
            status = adapter.status()
            unread_count = sum(1 for message in messages if message.unread is True)
            return GatewayMailCheckResponseV1(
                transport=status.transport,
                principal_id=status.principal_id,
                address=status.address,
                unread_only=request_payload.unread_only,
                message_count=len(messages),
                unread_count=unread_count,
                messages=messages,
            )

    def send_mail(self, request_payload: GatewayMailSendRequestV1) -> GatewayMailActionResponseV1:
        """Run one shared mailbox send request."""

        with self.m_lock:
            self._require_loopback_mail_surface()
            try:
                adapter = self._mailbox_adapter_locked()
            except GatewayError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            try:
                message = adapter.send(
                    to_addresses=request_payload.to,
                    cc_addresses=request_payload.cc,
                    subject=request_payload.subject,
                    body_content=request_payload.body_content,
                    attachments=request_payload.attachments,
                )
            except GatewayMailboxError as exc:
                raise HTTPException(status_code=502, detail=str(exc)) from exc
            status = adapter.status()
            return GatewayMailActionResponseV1(
                operation="send",
                transport=status.transport,
                principal_id=status.principal_id,
                address=status.address,
                message=message,
            )

    def reply_mail(self, request_payload: GatewayMailReplyRequestV1) -> GatewayMailActionResponseV1:
        """Run one shared mailbox reply request."""

        with self.m_lock:
            self._require_loopback_mail_surface()
            try:
                adapter = self._mailbox_adapter_locked()
            except GatewayError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            try:
                message = adapter.reply(
                    message_ref=request_payload.message_ref,
                    body_content=request_payload.body_content,
                    attachments=request_payload.attachments,
                )
            except GatewayMailboxError as exc:
                raise HTTPException(status_code=502, detail=str(exc)) from exc
            status = adapter.status()
            return GatewayMailActionResponseV1(
                operation="reply",
                transport=status.transport,
                principal_id=status.principal_id,
                address=status.address,
                message=message,
            )

    def get_mail_notifier(self) -> GatewayMailNotifierStatusV1:
        """Return the current notifier configuration and runtime status."""

        with self.m_lock:
            return self._mail_notifier_status_locked()

    def put_mail_notifier(
        self,
        request_payload: GatewayMailNotifierPutV1,
    ) -> GatewayMailNotifierStatusV1:
        """Enable or reconfigure the gateway mail notifier."""

        with self.m_lock:
            try:
                self._mailbox_adapter_locked()
            except GatewayError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            record = write_gateway_mail_notifier_record(
                self.m_paths.queue_path,
                enabled=True,
                interval_seconds=request_payload.interval_seconds,
                last_error=None,
            )
            self._log(f"mail notifier enabled interval_seconds={request_payload.interval_seconds}")
            return build_gateway_mail_notifier_status(
                record=record,
                supported=True,
                support_error=None,
            )

    def delete_mail_notifier(self) -> GatewayMailNotifierStatusV1:
        """Disable the gateway mail notifier explicitly."""

        with self.m_lock:
            record = write_gateway_mail_notifier_record(
                self.m_paths.queue_path,
                enabled=False,
                interval_seconds=None,
                last_notified_digest=None,
                last_error=None,
            )
            supported, support_error = self._notifier_support_status()
            self._log("mail notifier disabled")
            return build_gateway_mail_notifier_status(
                record=record,
                supported=supported,
                support_error=support_error,
            )

    def _mail_notifier_status_locked(self) -> GatewayMailNotifierStatusV1:
        """Return the notifier status while the runtime lock is held."""

        record = read_gateway_mail_notifier_record(self.m_paths.queue_path)
        supported, support_error = self._notifier_support_status()
        return build_gateway_mail_notifier_status(
            record=record,
            supported=supported,
            support_error=support_error,
        )

    def _notifier_support_status(self) -> tuple[bool, str | None]:
        """Return whether notifier behavior is currently supported."""

        try:
            self._mailbox_adapter_locked()
        except GatewayError as exc:
            return False, str(exc)
        return True, None

    def _load_mailbox_config(self) -> MailboxResolvedConfig:
        """Load the manifest-backed mailbox config required by mailbox routes."""

        manifest_path = self.m_attach_contract.manifest_path
        if manifest_path is None:
            raise GatewayError(
                "Gateway attach contract is missing runtime-owned `manifest_path`; mailbox support is unavailable."
            )
        try:
            handle = load_session_manifest(Path(manifest_path))
            payload = parse_session_manifest_payload(handle.payload, source=str(handle.path))
        except SessionManifestError as exc:
            raise GatewayError(
                f"Runtime-owned session manifest is unreadable for mailbox support: {exc}"
            ) from exc

        try:
            mailbox = resolved_mailbox_config_from_payload(
                payload.launch_plan.mailbox,
                manifest_path=handle.path,
            )
        except ValueError as exc:
            raise GatewayError(
                f"Runtime-owned session manifest has an invalid mailbox binding: {exc}"
            ) from exc
        if mailbox is None:
            raise GatewayError(
                "Runtime-owned session manifest launch plan has no mailbox binding; mailbox support is unavailable."
            )
        return mailbox

    def _mailbox_adapter_locked(self) -> GatewayMailboxAdapter:
        """Return the cached mailbox adapter while the runtime lock is held."""

        mailbox = self._load_mailbox_config()
        if (
            self.m_mailbox_adapter is not None
            and self.m_mailbox_bindings_version == mailbox.bindings_version
        ):
            return self.m_mailbox_adapter
        try:
            adapter = build_gateway_mailbox_adapter(mailbox)
        except GatewayMailboxError as exc:
            raise GatewayError(str(exc)) from exc
        self.m_mailbox_adapter = adapter
        self.m_mailbox_bindings_version = mailbox.bindings_version
        return adapter

    def _require_loopback_mail_surface(self) -> None:
        """Reject mailbox HTTP routes when the gateway is not loopback-bound."""

        if self.m_host != "127.0.0.1":
            raise HTTPException(
                status_code=503,
                detail="Gateway mailbox routes are unavailable when the listener is bound to 0.0.0.0.",
            )

    def _notifier_loop(self) -> None:
        """Poll mailbox-local unread state when the notifier is enabled."""

        next_poll_monotonic: float | None = None
        scheduled_interval_seconds: int | None = None
        while not self.m_stop_event.is_set():
            record = read_gateway_mail_notifier_record(self.m_paths.queue_path)
            if not record.enabled or record.interval_seconds is None:
                next_poll_monotonic = None
                scheduled_interval_seconds = None
                self.m_stop_event.wait(_NOTIFIER_IDLE_CHECK_INTERVAL_SECONDS)
                continue

            now_monotonic = time.monotonic()
            if next_poll_monotonic is None or scheduled_interval_seconds != record.interval_seconds:
                next_poll_monotonic = now_monotonic + record.interval_seconds
                scheduled_interval_seconds = record.interval_seconds

            remaining = next_poll_monotonic - now_monotonic
            if remaining > 0:
                self.m_stop_event.wait(min(remaining, _NOTIFIER_IDLE_CHECK_INTERVAL_SECONDS))
                continue

            self._run_notifier_cycle()
            record = read_gateway_mail_notifier_record(self.m_paths.queue_path)
            if not record.enabled or record.interval_seconds is None:
                next_poll_monotonic = None
                scheduled_interval_seconds = None
            else:
                scheduled_interval_seconds = record.interval_seconds
                next_poll_monotonic = time.monotonic() + record.interval_seconds

    def _run_notifier_cycle(self) -> None:
        """Execute one notifier polling cycle."""

        with self.m_lock:
            record = read_gateway_mail_notifier_record(self.m_paths.queue_path)
            if not record.enabled or record.interval_seconds is None:
                return

            poll_time_utc = now_utc_iso()
            status = self._refresh_status_snapshot(active_execution=self._active_execution_state())
            try:
                adapter = self._mailbox_adapter_locked()
            except GatewayError as exc:
                write_gateway_mail_notifier_record(
                    self.m_paths.queue_path,
                    enabled=False,
                    interval_seconds=None,
                    last_error=str(exc),
                )
                self._append_notifier_audit_record(
                    poll_time_utc=poll_time_utc,
                    status=status,
                    unread_messages=[],
                    unread_count=None,
                    unread_digest=None,
                    outcome="poll_error",
                    detail=str(exc),
                )
                self._log(f"mail notifier disabled: {exc}")
                return

            try:
                unread_messages = [
                    _UnreadMailboxMessage(
                        message_ref=message.message_ref,
                        thread_ref=message.thread_ref,
                        created_at_utc=message.created_at_utc,
                        subject=message.subject,
                    )
                    for message in adapter.check(unread_only=True, limit=None, since=None)
                ]
            except GatewayMailboxError as exc:
                write_gateway_mail_notifier_record(
                    self.m_paths.queue_path,
                    last_poll_at_utc=poll_time_utc,
                    last_error=str(exc),
                )
                self._append_notifier_audit_record(
                    poll_time_utc=poll_time_utc,
                    status=status,
                    unread_messages=[],
                    unread_count=None,
                    unread_digest=None,
                    outcome="poll_error",
                    detail=str(exc),
                )
                self._log_rate_limited(
                    "mail_notifier_error",
                    f"mail notifier poll error: {exc}",
                )
                return

            if not unread_messages:
                write_gateway_mail_notifier_record(
                    self.m_paths.queue_path,
                    last_poll_at_utc=poll_time_utc,
                    last_notified_digest=None,
                    last_error=None,
                )
                self._append_notifier_audit_record(
                    poll_time_utc=poll_time_utc,
                    status=status,
                    unread_messages=[],
                    unread_count=0,
                    unread_digest=None,
                    outcome="empty",
                )
                self._log_rate_limited("mail_notifier_empty", "mail notifier poll: no unread mail")
                return

            unread_digest = self._mail_notifier_digest(unread_messages)
            if unread_digest == record.last_notified_digest:
                write_gateway_mail_notifier_record(
                    self.m_paths.queue_path,
                    last_poll_at_utc=poll_time_utc,
                    last_error=None,
                )
                self._append_notifier_audit_record(
                    poll_time_utc=poll_time_utc,
                    status=status,
                    unread_messages=unread_messages,
                    unread_count=len(unread_messages),
                    unread_digest=unread_digest,
                    outcome="dedup_skip",
                    detail="Unread set matched the last delivered reminder digest.",
                )
                self._log_rate_limited(
                    "mail_notifier_dedup",
                    "mail notifier poll: unread mail unchanged; skipping duplicate reminder",
                )
                return

            if (
                status.request_admission != "open"
                or status.active_execution != "idle"
                or status.queue_depth > 0
            ):
                busy_detail = (
                    "mail notifier poll deferred because the managed session is busy "
                    f"(admission={status.request_admission}, "
                    f"active_execution={status.active_execution}, "
                    f"queue_depth={status.queue_depth})"
                )
                write_gateway_mail_notifier_record(
                    self.m_paths.queue_path,
                    last_poll_at_utc=poll_time_utc,
                    last_error=None,
                )
                self._append_notifier_audit_record(
                    poll_time_utc=poll_time_utc,
                    status=status,
                    unread_messages=unread_messages,
                    unread_count=len(unread_messages),
                    unread_digest=unread_digest,
                    outcome="busy_skip",
                    detail=busy_detail,
                )
                self._log_rate_limited(
                    "mail_notifier_busy",
                    busy_detail,
                )
                return

            prompt = self._build_mail_notifier_prompt(unread_messages)
            request_id = self._enqueue_internal_prompt(prompt=prompt)
            write_gateway_mail_notifier_record(
                self.m_paths.queue_path,
                last_poll_at_utc=poll_time_utc,
                last_notification_at_utc=poll_time_utc,
                last_notified_digest=unread_digest,
                last_error=None,
            )
            self._append_notifier_audit_record(
                poll_time_utc=poll_time_utc,
                status=status,
                unread_messages=unread_messages,
                unread_count=len(unread_messages),
                unread_digest=unread_digest,
                outcome="enqueued",
                enqueued_request_id=request_id,
            )
            self._log(
                f"mail notifier enqueued request_id={request_id} unread_count={len(unread_messages)}"
            )

    def _mail_notifier_digest(self, unread_messages: list[_UnreadMailboxMessage]) -> str:
        """Build a stable digest for one unread-mail snapshot."""

        digest_source = "\n".join(message.message_ref for message in unread_messages)
        return hashlib.sha256(digest_source.encode("utf-8")).hexdigest()

    def _build_mail_notifier_prompt(self, unread_messages: list[_UnreadMailboxMessage]) -> str:
        """Build the reminder prompt submitted through the internal notifier path."""

        lines = [
            "You have unread mailbox messages.",
            "Use the runtime-owned mailbox skill to inspect and process them.",
            "Only mark a message read after you have processed it successfully.",
            "",
            "Unread messages:",
        ]
        for message in unread_messages[:10]:
            lines.append(f"- {message.created_at_utc} | {message.message_ref} | {message.subject}")
        if len(unread_messages) > 10:
            lines.append(f"- ... and {len(unread_messages) - 10} more unread messages")
        return "\n".join(lines)

    def _enqueue_internal_prompt(self, *, prompt: str) -> str:
        """Insert one internal notifier prompt into durable queue storage."""

        request_id = generate_gateway_request_id()
        accepted_at_utc = now_utc_iso()
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
                    "mail_notifier_prompt",
                    json.dumps({"prompt": prompt}, sort_keys=True),
                    accepted_at_utc,
                    self.m_current_epoch,
                ),
            )
            connection.commit()

        append_gateway_event(
            self.m_paths,
            {
                "kind": "accepted_internal",
                "request_id": request_id,
                "request_kind": "mail_notifier_prompt",
                "accepted_at_utc": accepted_at_utc,
            },
        )
        self._refresh_status_snapshot(active_execution=self._active_execution_state())
        return request_id

    def _append_notifier_audit_record(
        self,
        *,
        poll_time_utc: str,
        status: GatewayStatusV1,
        unread_messages: list[_UnreadMailboxMessage],
        unread_count: int | None,
        unread_digest: str | None,
        outcome: Literal["empty", "dedup_skip", "busy_skip", "enqueued", "poll_error"],
        enqueued_request_id: str | None = None,
        detail: str | None = None,
    ) -> None:
        """Persist one structured notifier audit row."""

        append_gateway_notifier_audit_record(
            self.m_paths.queue_path,
            poll_time_utc=poll_time_utc,
            unread_count=unread_count,
            unread_digest=unread_digest,
            unread_summary=tuple(
                GatewayNotifierAuditUnreadMessage(
                    message_ref=message.message_ref,
                    thread_ref=message.thread_ref,
                    created_at_utc=message.created_at_utc,
                    subject=message.subject,
                )
                for message in unread_messages
            ),
            request_admission=status.request_admission,
            active_execution=status.active_execution,
            queue_depth=status.queue_depth,
            outcome=outcome,
            enqueued_request_id=enqueued_request_id,
            detail=detail,
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
                request_kind=cast(GatewayStoredRequestKind, request_kind),
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
            if self.m_current_instance_id is None:
                self._finish_request(
                    request_id=request_id,
                    state="failed",
                    error_detail="Managed agent is unavailable.",
                    result_json=None,
                )
                return
            self._log(f"executing gateway request request_id={request_id} kind={request_kind}")

        try:
            if request_kind in {"submit_prompt", "mail_notifier_prompt"}:
                payload = GatewayRequestPayloadSubmitPromptV1.model_validate_json(payload_json)
                self.m_adapter.submit_prompt(prompt=payload.prompt)
            elif request_kind == "interrupt":
                GatewayRequestPayloadInterruptV1.model_validate_json(payload_json)
                self.m_adapter.interrupt()
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
            if state == "completed":
                self._log(f"completed gateway request request_id={request_id}")
            else:
                self._log(
                    f"failed gateway request request_id={request_id} detail={error_detail or 'unknown error'}"
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

        target_state = self.m_adapter.inspect_target()
        current_instance_id = target_state.instance_id
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

        target_state = self.m_adapter.inspect_target()
        current_instance_id = target_state.instance_id
        if self.m_current_instance_id is None:
            self.m_current_instance_id = current_instance_id
        elif current_instance_id != self.m_current_instance_id:
            self.m_current_epoch += 1
            self.m_current_instance_id = current_instance_id

        connectivity = target_state.connectivity
        recovery: GatewayRecoveryState = "idle"
        admission: GatewayAdmissionState = (
            "open" if target_state.prompt_admission_open else "blocked_unavailable"
        )
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
            terminal_surface_eligibility=target_state.terminal_surface_eligibility,
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

    def _log(self, message: str) -> None:
        """Emit one tail-friendly gateway log line to the stable gateway log."""

        line = f"{now_utc_iso()} {message}"
        with self.m_log_lock:
            self.m_paths.logs_dir.mkdir(parents=True, exist_ok=True)
            with self.m_paths.log_path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        print(line, flush=True)

    def _log_rate_limited(self, key: str, message: str) -> None:
        """Emit one gateway log line with coarse repetition suppression."""

        now_monotonic = time.monotonic()
        last_logged_at, suppressed_count = self.m_rate_limited_logs.get(key, (0.0, 0))
        if now_monotonic - last_logged_at >= _NOTIFIER_RATE_LIMIT_SECONDS:
            suffix = f" (suppressed {suppressed_count} repeats)" if suppressed_count > 0 else ""
            self._log(message + suffix)
            self.m_rate_limited_logs[key] = (now_monotonic, 0)
            return
        self.m_rate_limited_logs[key] = (last_logged_at, suppressed_count + 1)

    def _flush_rate_limited_logs(self) -> None:
        """Flush any suppressed rate-limited notifier log counters."""

        for key, (_, suppressed_count) in list(self.m_rate_limited_logs.items()):
            if suppressed_count <= 0:
                continue
            self._log(f"{key}: suppressed {suppressed_count} repeated messages")
            self.m_rate_limited_logs[key] = (time.monotonic(), 0)


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

    @app.get("/v1/mail/status", response_model=GatewayMailStatusV1)
    def _mail_status() -> GatewayMailStatusV1:
        """Serve shared mailbox availability for the attached session."""

        return runtime.get_mail_status()

    @app.post("/v1/mail/check", response_model=GatewayMailCheckResponseV1)
    def _mail_check(request_payload: GatewayMailCheckRequestV1) -> GatewayMailCheckResponseV1:
        """Run one shared mailbox check request."""

        return runtime.check_mail(request_payload)

    @app.post("/v1/mail/send", response_model=GatewayMailActionResponseV1)
    def _mail_send(request_payload: GatewayMailSendRequestV1) -> GatewayMailActionResponseV1:
        """Run one shared mailbox send request."""

        return runtime.send_mail(request_payload)

    @app.post("/v1/mail/reply", response_model=GatewayMailActionResponseV1)
    def _mail_reply(request_payload: GatewayMailReplyRequestV1) -> GatewayMailActionResponseV1:
        """Run one shared mailbox reply request."""

        return runtime.reply_mail(request_payload)

    @app.get("/v1/mail-notifier", response_model=GatewayMailNotifierStatusV1)
    def _get_mail_notifier() -> GatewayMailNotifierStatusV1:
        """Serve notifier configuration and runtime status."""

        return runtime.get_mail_notifier()

    @app.put("/v1/mail-notifier", response_model=GatewayMailNotifierStatusV1)
    def _put_mail_notifier(
        request_payload: GatewayMailNotifierPutV1,
    ) -> GatewayMailNotifierStatusV1:
        """Enable or reconfigure the gateway mail notifier."""

        return runtime.put_mail_notifier(request_payload)

    @app.delete("/v1/mail-notifier", response_model=GatewayMailNotifierStatusV1)
    def _delete_mail_notifier() -> GatewayMailNotifierStatusV1:
        """Disable the gateway mail notifier."""

        return runtime.delete_mail_notifier()

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
