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
from typing import Literal, cast

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import ValidationError

from houmao.agents.mailbox_runtime_support import resolved_mailbox_config_from_payload
from houmao.agents.realm_controller.errors import GatewayError, SessionManifestError
from houmao.agents.realm_controller.gateway_models import (
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
    GatewayMailNotifierPutV1,
    GatewayMailNotifierStatusV1,
    GatewayRecoveryState,
    GatewayRequestCreateV1,
    GatewayRequestPayloadInterruptV1,
    GatewayRequestPayloadSubmitPromptV1,
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
from houmao.mailbox import resolve_active_mailbox_local_sqlite_path
from houmao.cao.rest_client import CaoApiError, CaoRestClient

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
    """Unread mailbox-local message summary used for notifier prompts."""

    message_id: str
    thread_id: str
    created_at_utc: str
    subject: str


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
        self.m_log_lock = threading.Lock()
        self.m_stop_event = threading.Event()
        self.m_worker_thread: threading.Thread | None = None
        self.m_notifier_thread: threading.Thread | None = None
        self.m_current_epoch = 1
        self.m_current_instance_id: str | None = None
        self.m_rate_limited_logs: dict[str, tuple[float, int]] = {}

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
                self._load_notifier_mailbox_config()
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
            self._load_notifier_mailbox_config()
        except GatewayError as exc:
            return False, str(exc)
        return True, None

    def _load_notifier_mailbox_config(self):  # type: ignore[no-untyped-def]
        """Load the manifest-backed mailbox config required by the notifier."""

        manifest_path = self.m_attach_contract.manifest_path
        if manifest_path is None:
            raise GatewayError(
                "Gateway attach contract is missing runtime-owned `manifest_path`; mail notifier is unsupported."
            )
        try:
            handle = load_session_manifest(Path(manifest_path))
            payload = parse_session_manifest_payload(handle.payload, source=str(handle.path))
        except SessionManifestError as exc:
            raise GatewayError(
                f"Runtime-owned session manifest is unreadable for mail notifier support: {exc}"
            ) from exc

        try:
            mailbox = resolved_mailbox_config_from_payload(payload.launch_plan.mailbox)
        except ValueError as exc:
            raise GatewayError(
                f"Runtime-owned session manifest has an invalid mailbox binding: {exc}"
            ) from exc
        if mailbox is None:
            raise GatewayError(
                "Runtime-owned session manifest launch plan has no mailbox binding; mail notifier is unsupported."
            )
        return mailbox

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
                mailbox = self._load_notifier_mailbox_config()
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
                unread_messages = self._load_unread_mailbox_messages(mailbox)
            except GatewayError as exc:
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

    def _load_unread_mailbox_messages(self, mailbox) -> list[_UnreadMailboxMessage]:  # type: ignore[no-untyped-def]
        """Load unread mailbox-local messages for notifier polling."""

        try:
            local_sqlite_path = resolve_active_mailbox_local_sqlite_path(
                mailbox.filesystem_root,
                address=mailbox.address,
            )
        except Exception as exc:
            raise GatewayError(f"Failed to resolve mailbox-local SQLite path: {exc}") from exc

        try:
            with sqlite3.connect(local_sqlite_path) as connection:
                rows = connection.execute(
                    """
                    SELECT message_id, thread_id, created_at_utc, subject
                    FROM message_state
                    WHERE is_read = 0
                    ORDER BY created_at_utc ASC, message_id ASC
                    """
                ).fetchall()
        except sqlite3.DatabaseError as exc:
            raise GatewayError(
                f"Mailbox-local SQLite is unreadable for notifier polling: {local_sqlite_path}"
            ) from exc

        return [
            _UnreadMailboxMessage(
                message_id=str(row[0]),
                thread_id=str(row[1]),
                created_at_utc=str(row[2]),
                subject=str(row[3]),
            )
            for row in rows
        ]

    def _mail_notifier_digest(self, unread_messages: list[_UnreadMailboxMessage]) -> str:
        """Build a stable digest for one unread-mail snapshot."""

        digest_source = "\n".join(message.message_id for message in unread_messages)
        return hashlib.sha256(digest_source.encode("utf-8")).hexdigest()

    def _build_mail_notifier_prompt(self, unread_messages: list[_UnreadMailboxMessage]) -> str:
        """Build the reminder prompt submitted through the internal notifier path."""

        lines = [
            "You have unread filesystem mailbox messages.",
            "Use the runtime-owned mailbox skill to inspect and process them.",
            "Only mark a message read after you have processed it successfully.",
            "",
            "Unread messages:",
        ]
        for message in unread_messages[:10]:
            lines.append(f"- {message.created_at_utc} | {message.message_id} | {message.subject}")
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
                    message_id=message.message_id,
                    thread_id=message.thread_id,
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
            terminal_id = self.m_current_instance_id
            if terminal_id is None:
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
