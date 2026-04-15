"""Live FastAPI gateway companion process for one runtime-owned session."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
import hashlib
from importlib import resources
import json
import math
import os
import socket
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal, NoReturn, Protocol, TypeVar, cast

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import ValidationError

from houmao.agents.agent_workspace import (
    AgentMemoryPaths,
    delete_memory_page,
    list_memory_pages,
    read_memo,
    read_memory_page,
    resolve_memory_page_path,
    write_memo,
    write_memory_page,
)
from houmao.agents.mailbox_runtime_support import (
    mailbox_processing_skill_name,
    mailbox_processing_skill_reference,
    mailbox_gateway_skill_name,
    mailbox_gateway_skill_reference,
    projected_mailbox_skill_document_path,
    resolve_live_mailbox_binding,
    resolved_mailbox_config_from_payload,
)
from houmao.agents.model_selection import ModelConfig
from houmao.agents.mailbox_runtime_models import MailboxResolvedConfig
from houmao.agents.realm_controller.errors import GatewayError, SessionManifestError
from houmao.agents.realm_controller.errors import LaunchPlanError
from houmao.agents.realm_controller.gateway_mailbox import (
    GatewayMailboxAdapter,
    GatewayMailboxError,
    GatewayMailboxUnsupportedError,
    build_gateway_mailbox_adapter,
)
from houmao.agents.realm_controller.gateway_models import (
    GatewayAcceptedRequestV1,
    GatewayAdmissionState,
    GatewayAttachBackendMetadataCaoV1,
    GatewayAttachBackendMetadataHeadlessV1,
    GatewayAttachContractV1,
    GatewayAttachBackendMetadataHoumaoServerV1,
    GatewayChatSessionSelectorV1,
    GatewayConnectivityState,
    GatewayControlInputRequestV1,
    GatewayControlInputResultV1,
    GatewayCurrentInstanceV1,
    GatewayExecutionOverrideV1,
    GatewayExecutionState,
    GatewayHeadlessChatSessionStateV1,
    GatewayHeadlessControlStateV1,
    GatewayHeadlessCurrentChatSessionV1,
    GatewayHealthResponseV1,
    GatewayHeadlessNextPromptOverrideV1,
    GatewayHeadlessNextPromptSessionRequestV1,
    GatewayHeadlessStartupDefaultV1,
    GatewayHost,
    GatewayMailActionResponseV1,
    GatewayMailArchiveRequestV1,
    GatewayMailLifecycleResponseV1,
    GatewayMailListRequestV1,
    GatewayMailListResponseV1,
    GatewayMailMarkRequestV1,
    GatewayMailMessageRequestV1,
    GatewayMailMessageResponseV1,
    GatewayMailMoveRequestV1,
    GatewayMailPostRequestV1,
    GatewayMailReplyRequestV1,
    GatewayMailSendRequestV1,
    GatewayMailStatusV1,
    GatewayJsonObject,
    GatewayMailNotifierMode,
    GatewayMailNotifierPutV1,
    GatewayMailNotifierStatusV1,
    GatewayPromptControlErrorV1,
    GatewayPromptControlRequestV1,
    GatewayPromptControlResultV1,
    GatewayRecoveryState,
    GatewayRequestCreateV1,
    GatewayRequestPayloadInterruptV1,
    GatewayRequestPayloadSubmitPromptV1,
    GatewayReminderCreateBatchV1,
    GatewayReminderCreateResultV1,
    GatewayReminderDefinitionV1,
    GatewayReminderDeleteResultV1,
    GatewayReminderDeliveryKind,
    GatewayReminderDeliveryState,
    GatewayReminderListV1,
    GatewayReminderMode,
    GatewayReminderPutV1,
    GatewayReminderSendKeysV1,
    GatewayReminderSelectionState,
    GatewayReminderV1,
    GatewaySurfaceEligibilityState,
    GatewayStoredRequestKind,
    GatewayStatusV1,
    GatewayTuiTrackingTimingConfigV1,
    GatewayTuiTrackingTimingOverridesV1,
    GatewayMemoryActionResponseV1,
    GatewayMemoryMemoResponseV1,
    GatewayMemoryMemoWriteRequestV1,
    GatewayMemoryPageEntryV1,
    GatewayMemoryPagePathRequestV1,
    GatewayMemoryPagePathResolutionV1,
    GatewayMemoryPageResponseV1,
    GatewayMemoryPageTreeRequestV1,
    GatewayMemoryPageTreeResponseV1,
    GatewayMemoryPageWriteRequestV1,
    GatewayMemorySummaryV1,
    resolve_gateway_tui_tracking_timing_config,
)
from houmao.agents.realm_controller.boundary_models import SessionManifestPayloadV4
from houmao.agents.realm_controller.gateway_storage import (
    GatewayNotifierAuditUnreadMessage,
    append_gateway_event,
    append_gateway_notifier_audit_record,
    build_gateway_mail_notifier_status,
    delete_gateway_current_instance,
    gateway_health_response,
    gateway_paths_from_session_root,
    generate_gateway_request_id,
    load_gateway_current_instance,
    read_gateway_mail_notifier_record,
    now_utc_iso,
    queue_depth_from_sqlite,
    refresh_gateway_manifest_publication,
    resolve_internal_gateway_attach_contract,
    write_gateway_mail_notifier_record,
    write_gateway_current_instance,
    write_gateway_status,
)
from houmao.agents.realm_controller.manifest import (
    load_session_manifest,
    parse_session_manifest_payload,
)
from houmao.agents.realm_controller.session_authority import resolve_manifest_session_authority
from houmao.agents.realm_controller.runtime import RuntimeSessionController, resume_runtime_session
from houmao.agents.realm_controller.models import HeadlessTurnSessionSelection
from houmao.agents.realm_controller.backends.tmux_runtime import (
    HEADLESS_AGENT_WINDOW_NAME,
    tmux_session_exists,
)
from houmao.cao.rest_client import CaoApiError, CaoRestClient
from houmao.server.models import (
    HoumaoManagedAgentGatewayInternalHeadlessPromptRequest,
    HoumaoManagedAgentInterruptRequest,
    HoumaoManagedAgentSubmitPromptRequest,
    HoumaoTerminalSnapshotHistoryResponse,
    HoumaoTerminalStateResponse,
    HoumaoTrackedSessionIdentity,
)
from houmao.server.pair_client import (
    PairAuthorityClientProtocol,
    PairAuthorityConnectionError,
    UnsupportedPairAuthorityError,
    resolve_pair_authority_client,
)
from houmao.shared_tui_tracking.ownership import SingleSessionTrackingRuntime

_QUEUE_POLL_INTERVAL_SECONDS = 0.2
_REMINDER_BUSY_RETRY_INTERVAL_SECONDS = 0.2
_NOTIFIER_IDLE_CHECK_INTERVAL_SECONDS = 0.2
_NOTIFIER_RATE_LIMIT_SECONDS = 30.0
_TUI_RESET_PROMPT = "/clear"
_TUI_RESET_READY_WAIT_SECONDS = 15.0
_TUI_RESET_READY_POLL_INTERVAL_SECONDS = 0.2
_SEND_KEYS_ENTER_TOKEN = "<[Enter]>"
_GatewayRequestTerminalState = Literal["completed", "failed"]
_MemoryResponseT = TypeVar("_MemoryResponseT")
_GATEWAY_EXECUTION_MODE_ENV_VAR = "HOUMAO_GATEWAY_EXECUTION_MODE"
_GATEWAY_TMUX_WINDOW_ID_ENV_VAR = "HOUMAO_GATEWAY_TMUX_WINDOW_ID"
_GATEWAY_TMUX_WINDOW_INDEX_ENV_VAR = "HOUMAO_GATEWAY_TMUX_WINDOW_INDEX"
_GATEWAY_TMUX_PANE_ID_ENV_VAR = "HOUMAO_GATEWAY_TMUX_PANE_ID"
_MAIL_NOTIFIER_TEMPLATE_RESOURCE = "system_prompts/mailbox/mail-notifier.md"


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
    """Open mailbox message summary used for notifier prompts."""

    message_ref: str
    thread_ref: str | None
    created_at_utc: str
    sender_address: str
    sender_display_name: str | None
    subject: str


@dataclass
class _GatewayReminderRecord:
    """One in-memory reminder record owned by the live gateway runtime."""

    reminder_id: str
    mode: GatewayReminderMode
    delivery_kind: GatewayReminderDeliveryKind
    title: str
    prompt: str | None
    send_keys_sequence: str | None
    send_keys_ensure_enter: bool
    ranking: int
    paused: bool
    created_at: datetime
    next_due_at: datetime
    anchor_due_at: datetime
    interval_seconds: float | None
    last_started_at: datetime | None = None
    executing: bool = False
    delete_requested: bool = False
    deferred_signature: str | None = None


@dataclass(frozen=True)
class _GatewayTargetState:
    """Execution posture for the currently addressed gateway target."""

    instance_id: str
    connectivity: GatewayConnectivityState
    terminal_surface_eligibility: GatewaySurfaceEligibilityState
    prompt_admission_open: bool


@dataclass(frozen=True)
class _GatewayControlInputSupport:
    """Raw control-input capability summary for the attached gateway target."""

    supported: bool
    detail: str | None = None


def _sort_unread_messages(
    unread_messages: list[_UnreadMailboxMessage],
) -> list[_UnreadMailboxMessage]:
    """Return unread messages in deterministic oldest-first nomination order."""

    return sorted(
        unread_messages,
        key=lambda message: (_parse_gateway_timestamp(message.created_at_utc), message.message_ref),
    )


def _parse_gateway_timestamp(value: str) -> datetime:
    """Parse one gateway timestamp into UTC for deterministic ordering."""

    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _optional_env_string(variable_name: str) -> str | None:
    """Return one stripped environment variable when present."""

    value = os.environ.get(variable_name)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _render_mail_notifier_full_endpoint_urls(base_url: str) -> str:
    """Return one markdown block with full current mailbox endpoint URLs."""

    return "\n".join(
        [
            f"- `GET {base_url}/v1/mail/status`",
            f"- `POST {base_url}/v1/mail/list`",
            f"- `POST {base_url}/v1/mail/peek`",
            f"- `POST {base_url}/v1/mail/read`",
            f"- `POST {base_url}/v1/mail/send`",
            f"- `POST {base_url}/v1/mail/post`",
            f"- `POST {base_url}/v1/mail/reply`",
            f"- `POST {base_url}/v1/mail/mark`",
            f"- `POST {base_url}/v1/mail/move`",
            f"- `POST {base_url}/v1/mail/archive`",
        ]
    )


def _render_mail_notifier_mode_guidance(mode: GatewayMailNotifierMode) -> str:
    """Return mode-specific prompt guidance for a notifier round."""

    if mode == "unread_only":
        return "\n".join(
            [
                "This `unread_only` notification was triggered by unread, unarchived inbox mail.",
                "Start by listing unread inbox mail for this round. Read or answered inbox mail "
                "that remains unarchived will not trigger another notification by itself in this mode.",
            ]
        )
    return "\n".join(
        [
            "This `any_inbox` notification was triggered by unarchived inbox mail.",
            "List open inbox mail for this round, including mail that may already be read or answered.",
        ]
    )


def _load_mail_notifier_template() -> str:
    """Load the packaged markdown notifier prompt template."""

    return (
        resources.files("houmao.agents.realm_controller.assets") / _MAIL_NOTIFIER_TEMPLATE_RESOURCE
    ).read_text(encoding="utf-8")


class GatewayExecutionAdapter(Protocol):
    """Execution adapter boundary for one gateway-managed target."""

    @property
    def attach_contract(self) -> GatewayAttachContractV1:
        """Return the strict attach contract."""

    def inspect_target(self) -> _GatewayTargetState:
        """Return current target posture for status and reconciliation."""

    def submit_prompt(
        self,
        *,
        prompt: str,
        turn_id: str | None = None,
        session_selection: HeadlessTurnSessionSelection | None = None,
        execution_model: ModelConfig | None = None,
    ) -> None:
        """Submit one prompt to the addressed managed target."""

    def send_control_input(self, *, sequence: str, escape_special_keys: bool = False) -> str:
        """Deliver one raw control-input sequence to the addressed managed target."""

    def describe_control_input_support(self) -> _GatewayControlInputSupport:
        """Return whether the attached target can preserve raw control-input semantics."""

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
        manifest_path_value = attach_contract.manifest_path
        agent_def_dir_value = attach_contract.agent_def_dir
        self.m_manifest_path = (
            Path(manifest_path_value).expanduser().resolve()
            if manifest_path_value is not None
            else None
        )
        self.m_agent_def_dir = (
            Path(agent_def_dir_value).expanduser().resolve()
            if agent_def_dir_value is not None
            else None
        )
        self.m_controller: RuntimeSessionController | None = None
        self.m_failed_recovery_terminal_id: str | None = None

    @property
    def attach_contract(self) -> GatewayAttachContractV1:
        """Return the strict attach contract."""

        return self.m_attach_contract

    def inspect_target(self) -> _GatewayTargetState:
        """Return current execution posture for the REST-backed target."""

        terminal_id = self._read_current_terminal_id()
        connectivity = self._inspect_connectivity(terminal_id)
        if connectivity != "connected" and self._should_attempt_recovery(terminal_id):
            if self._attempt_relaunch_recovery():
                terminal_id = self._read_current_terminal_id()
                connectivity = self._inspect_connectivity(terminal_id)
                if connectivity == "connected":
                    self.m_failed_recovery_terminal_id = None
            else:
                self.m_failed_recovery_terminal_id = terminal_id
        return _GatewayTargetState(
            instance_id=terminal_id,
            connectivity=connectivity,
            terminal_surface_eligibility="ready" if connectivity == "connected" else "unknown",
            prompt_admission_open=connectivity == "connected",
        )

    def submit_prompt(
        self,
        *,
        prompt: str,
        turn_id: str | None = None,
        session_selection: HeadlessTurnSessionSelection | None = None,
        execution_model: ModelConfig | None = None,
    ) -> None:
        """Submit one prompt to the current runtime-owned terminal."""

        del turn_id, session_selection
        if execution_model is not None and not execution_model.is_empty():
            raise GatewayError(
                "Execution overrides are only supported for headless gateway targets."
            )
        terminal_id = self._read_current_terminal_id()
        result = self.m_client.send_terminal_input(terminal_id, prompt)
        if not result.success:
            raise GatewayError("CAO prompt submission returned success=false.")

    def send_control_input(self, *, sequence: str, escape_special_keys: bool = False) -> str:
        """Reject raw send-keys because REST-backed gateways lack tmux key semantics."""

        del sequence, escape_special_keys
        raise GatewayError(
            "Raw control input is unsupported for REST-backed gateway targets because the "
            "gateway cannot preserve exact tmux `<[key-name]>` semantics on that path."
        )

    def describe_control_input_support(self) -> _GatewayControlInputSupport:
        """Return the raw control-input support summary for REST-backed targets."""

        return _GatewayControlInputSupport(
            supported=False,
            detail=(
                "Raw control input is unsupported for REST-backed gateway targets because the "
                "gateway cannot preserve exact tmux `<[key-name]>` semantics on that path."
            ),
        )

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
        authority = resolve_manifest_session_authority(
            manifest_path=handle.path,
            payload=payload,
        )
        try:
            return authority.control.require_terminal_id()
        except SessionManifestError as exc:
            raise GatewayError(str(exc)) from exc

    def _inspect_connectivity(self, terminal_id: str) -> GatewayConnectivityState:
        """Return whether the addressed CAO terminal is reachable."""

        try:
            self.m_client.get_terminal(terminal_id)
        except CaoApiError:
            return "unavailable"
        return "connected"

    def _should_attempt_recovery(self, terminal_id: str) -> bool:
        """Return whether one manifest-backed relaunch recovery should run."""

        if terminal_id == self.m_failed_recovery_terminal_id:
            return False
        if self.m_manifest_path is None or self.m_agent_def_dir is None:
            return False
        session_name = self.m_attach_contract.tmux_session_name
        if not session_name.strip():
            return False
        return tmux_session_exists(session_name=session_name)

    def _attempt_relaunch_recovery(self) -> bool:
        """Try one shared relaunch recovery for the runtime-owned tmux surface."""

        try:
            result = self._resume_controller().relaunch()
        except (GatewayError, LaunchPlanError, RuntimeError, SessionManifestError):
            return False
        return result.status == "ok"

    def _resume_controller(self) -> RuntimeSessionController:
        """Return the resumed runtime controller for relaunch recovery."""

        if self.m_controller is not None:
            return self.m_controller
        if self.m_manifest_path is None or self.m_agent_def_dir is None:
            raise GatewayError(
                "REST-backed gateway recovery requires manifest_path and agent_def_dir."
            )
        try:
            self.m_controller = resume_runtime_session(
                agent_def_dir=self.m_agent_def_dir,
                session_manifest_path=self.m_manifest_path,
            )
        except (LaunchPlanError, SessionManifestError, RuntimeError) as exc:
            raise GatewayError(
                f"Failed to resume runtime-owned REST-backed session for recovery: {exc}"
            ) from exc
        return self.m_controller


class _LocalHeadlessGatewayAdapter:
    """Execution adapter for runtime-owned local tmux-backed sessions."""

    def __init__(self, *, attach_contract: GatewayAttachContractV1) -> None:
        """Resume local runtime authority from the strict attach contract."""

        self.m_attach_contract = attach_contract
        if attach_contract.backend not in {
            "local_interactive",
            "claude_headless",
            "codex_headless",
            "gemini_headless",
        }:
            raise GatewayError(
                "Local tmux gateway adapter only supports native tmux-backed backends, got "
                f"{attach_contract.backend!r}."
            )
        manifest_path_value = attach_contract.manifest_path
        agent_def_dir_value = attach_contract.agent_def_dir
        if manifest_path_value is None or agent_def_dir_value is None:
            raise GatewayError(
                "Local tmux gateway attach requires manifest_path and agent_def_dir in the "
                "attach contract."
            )
        self.m_manifest_path = Path(manifest_path_value).expanduser().resolve()
        self.m_agent_def_dir = Path(agent_def_dir_value).expanduser().resolve()
        self.m_controller: RuntimeSessionController | None = None
        self.m_instance_id = attach_contract.runtime_session_id or attach_contract.attach_identity

    @property
    def attach_contract(self) -> GatewayAttachContractV1:
        """Return the strict attach contract."""

        return self.m_attach_contract

    def inspect_target(self) -> _GatewayTargetState:
        """Return current execution posture for the local tmux-backed target."""

        connected = tmux_session_exists(session_name=self.m_attach_contract.tmux_session_name)
        if connected:
            try:
                self._resume_controller()
            except GatewayError:
                connected = False
        connectivity: GatewayConnectivityState = "connected" if connected else "unavailable"
        return _GatewayTargetState(
            instance_id=self.m_instance_id,
            connectivity=connectivity,
            terminal_surface_eligibility="ready" if connected else "unknown",
            prompt_admission_open=connected,
        )

    def submit_prompt(
        self,
        *,
        prompt: str,
        turn_id: str | None = None,
        session_selection: HeadlessTurnSessionSelection | None = None,
        execution_model: ModelConfig | None = None,
    ) -> None:
        """Submit one prompt through resumed local tmux-backed runtime control."""

        self._require_live_tmux_session()
        try:
            controller = self._resume_controller()
            controller.send_prompt(
                prompt=prompt,
                session_selection=session_selection,
                turn_artifact_dir_name=turn_id,
                execution_model=execution_model,
                refresh_registry=False,
            )
        except RuntimeError as exc:
            raise GatewayError(f"Local tmux-backed prompt submission failed: {exc}") from exc

    def interrupt(self) -> None:
        """Interrupt one resumed local tmux-backed runtime."""

        self._require_live_tmux_session()
        result = self._resume_controller().interrupt()
        if result.status != "ok":
            raise GatewayError(result.detail)

    def send_control_input(self, *, sequence: str, escape_special_keys: bool = False) -> str:
        """Deliver raw control input through resumed local runtime control."""

        self._require_live_tmux_session()
        result = self._resume_controller().send_input_ex(
            sequence,
            escape_special_keys=escape_special_keys,
        )
        if result.status != "ok":
            raise GatewayError(result.detail)
        return result.detail

    def describe_control_input_support(self) -> _GatewayControlInputSupport:
        """Return the raw control-input support summary for local tmux-backed targets."""

        return _GatewayControlInputSupport(supported=True)

    def _resume_controller(self) -> RuntimeSessionController:
        """Return the resumed local runtime controller, materializing it lazily."""

        if self.m_controller is not None:
            return self.m_controller
        try:
            self.m_controller = resume_runtime_session(
                agent_def_dir=self.m_agent_def_dir,
                session_manifest_path=self.m_manifest_path,
            )
        except (LaunchPlanError, SessionManifestError, RuntimeError) as exc:
            raise GatewayError(
                f"Failed to resume runtime-owned local tmux-backed session: {exc}"
            ) from exc
        return self.m_controller

    def _require_live_tmux_session(self) -> None:
        """Require the tmux session to still be live."""

        if not tmux_session_exists(session_name=self.m_attach_contract.tmux_session_name):
            raise GatewayError(
                f"Tmux session `{self.m_attach_contract.tmux_session_name}` is unavailable."
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
        self.m_managed_api_base_url = metadata.managed_api_base_url
        self.m_client: PairAuthorityClientProtocol | None = None

    @property
    def attach_contract(self) -> GatewayAttachContractV1:
        """Return the strict attach contract."""

        return self.m_attach_contract

    def inspect_target(self) -> _GatewayTargetState:
        """Return current execution posture for the server-managed target."""

        try:
            response = self._resolve_client().get_managed_agent_state_detail(
                self.m_managed_agent_ref
            )
        except (CaoApiError, GatewayError):
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

    def submit_prompt(
        self,
        *,
        prompt: str,
        turn_id: str | None = None,
        session_selection: HeadlessTurnSessionSelection | None = None,
        execution_model: ModelConfig | None = None,
    ) -> None:
        """Submit one prompt through the managed-agent server API."""

        client = self._resolve_client()
        execution_payload = GatewayExecutionOverrideV1.from_model_config(execution_model)
        internal_submit = getattr(
            client,
            "submit_managed_agent_gateway_internal_headless_prompt",
            None,
        )
        if callable(internal_submit):
            response = internal_submit(
                self.m_managed_agent_ref,
                HoumaoManagedAgentGatewayInternalHeadlessPromptRequest(
                    prompt=prompt,
                    turn_id=turn_id,
                    chat_session=self._selector_payload(session_selection),
                    execution=execution_payload,
                ),
            )
            if not response.success:
                raise GatewayError(
                    f"Managed-agent internal headless prompt did not execute: {response.detail}"
                )
            return

        del turn_id, session_selection
        response = client.submit_managed_agent_request(
            self.m_managed_agent_ref,
            HoumaoManagedAgentSubmitPromptRequest(
                prompt=prompt,
                execution=execution_payload,
            ),
        )
        if response.disposition != "accepted":
            raise GatewayError(f"Managed-agent prompt request did not execute: {response.detail}")

    def interrupt(self) -> None:
        """Interrupt the managed-agent target through the server API."""

        self._resolve_client().submit_managed_agent_request(
            self.m_managed_agent_ref,
            HoumaoManagedAgentInterruptRequest(),
        )

    def send_control_input(self, *, sequence: str, escape_special_keys: bool = False) -> str:
        """Reject raw send-keys for server-managed headless routes."""

        del sequence, escape_special_keys
        raise GatewayError(
            "Raw control input is unsupported for server-managed headless gateway targets."
        )

    def describe_control_input_support(self) -> _GatewayControlInputSupport:
        """Return the raw control-input support summary for server-managed headless targets."""

        return _GatewayControlInputSupport(
            supported=False,
            detail="Raw control input is unsupported for server-managed headless gateway targets.",
        )

    def _resolve_client(self) -> PairAuthorityClientProtocol:
        """Return the resolved pair-authority client for the managed target."""

        if self.m_client is not None:
            return self.m_client
        try:
            self.m_client = resolve_pair_authority_client(
                base_url=self.m_managed_api_base_url
            ).client
        except (PairAuthorityConnectionError, UnsupportedPairAuthorityError) as exc:
            raise GatewayError(
                f"Failed to resolve managed pair authority `{self.m_managed_api_base_url}`: {exc}"
            ) from exc
        return self.m_client

    def _selector_payload(
        self,
        session_selection: HeadlessTurnSessionSelection | None,
    ) -> GatewayChatSessionSelectorV1 | None:
        """Convert one resolved headless selector into the gateway payload shape."""

        if session_selection is None:
            return None
        if session_selection.mode == "exact":
            assert session_selection.session_id is not None
            return GatewayChatSessionSelectorV1(mode="exact", id=session_selection.session_id)
        return GatewayChatSessionSelectorV1(mode=session_selection.mode)


def _build_gateway_execution_adapter(
    *,
    attach_contract: GatewayAttachContractV1,
) -> GatewayExecutionAdapter:
    """Build the execution adapter for one gateway attach contract."""

    if attach_contract.backend in {"cao_rest", "houmao_server_rest"}:
        return _RestBackedGatewayAdapter(attach_contract=attach_contract)
    if attach_contract.backend in {
        "local_interactive",
        "claude_headless",
        "codex_headless",
        "gemini_headless",
    }:
        metadata = attach_contract.backend_metadata
        if (
            isinstance(metadata, GatewayAttachBackendMetadataHeadlessV1)
            and metadata.managed_api_base_url is not None
            and metadata.managed_agent_ref is not None
            and attach_contract.agent_def_dir is None
        ):
            return _ServerManagedHeadlessGatewayAdapter(attach_contract=attach_contract)
        return _LocalHeadlessGatewayAdapter(attach_contract=attach_contract)
    raise GatewayError(
        f"Gateway execution adapter is not implemented for backend={attach_contract.backend!r}."
    )


class GatewayServiceRuntime:
    """Mutable runtime for one live gateway process."""

    def __init__(
        self,
        *,
        gateway_root: Path,
        host: GatewayHost,
        port: int,
        tui_tracking_timings: GatewayTuiTrackingTimingOverridesV1 | None = None,
    ) -> None:
        """Initialize the gateway runtime state.

        Parameters
        ----------
        gateway_root:
            Gateway root or parent session root used to resolve gateway assets.
        host:
            Requested bind host for the live listener.
        port:
            Requested or resolved bind port for the live listener.
        tui_tracking_timings:
            Optional timing overrides for gateway-owned TUI tracking.
        """

        self.m_paths = gateway_paths_from_session_root(
            session_root=gateway_root.resolve().parent
            if gateway_root.resolve().name == "gateway"
            else gateway_root.resolve()
        )
        self.m_host: GatewayHost = host
        self.m_port: int = port
        self.m_tui_tracking_timings: GatewayTuiTrackingTimingConfigV1 = (
            resolve_gateway_tui_tracking_timing_config(explicit=tui_tracking_timings)
        )
        self.m_attach_contract = resolve_internal_gateway_attach_contract(self.m_paths)
        self.m_adapter: GatewayExecutionAdapter = _build_gateway_execution_adapter(
            attach_contract=self.m_attach_contract
        )
        self.m_lock = threading.Lock()
        self.m_reminder_condition = threading.Condition(self.m_lock)
        self.m_log_lock = threading.Lock()
        self.m_stop_event = threading.Event()
        self.m_worker_thread: threading.Thread | None = None
        self.m_reminder_thread: threading.Thread | None = None
        self.m_notifier_thread: threading.Thread | None = None
        self.m_current_epoch = 1
        self.m_current_instance_id: str | None = None
        self.m_rate_limited_logs: dict[str, tuple[float, int]] = {}
        self.m_mailbox_adapter: GatewayMailboxAdapter | None = None
        self.m_mailbox_bindings_version: str | None = None
        self.m_execution_mode = self._execution_mode_from_env()
        self.m_tmux_window_id = _optional_env_string(_GATEWAY_TMUX_WINDOW_ID_ENV_VAR)
        self.m_tmux_window_index = _optional_env_string(_GATEWAY_TMUX_WINDOW_INDEX_ENV_VAR)
        self.m_tmux_pane_id = _optional_env_string(_GATEWAY_TMUX_PANE_ID_ENV_VAR)
        self.m_tui_tracking: SingleSessionTrackingRuntime | None = None
        self.m_direct_prompt_thread: threading.Thread | None = None
        self.m_direct_prompt_turn_id: str | None = None
        self.m_headless_next_prompt_override: GatewayHeadlessNextPromptOverrideV1 | None = None
        self.m_reminders: dict[str, _GatewayReminderRecord] = {}
        self.m_active_reminder_id: str | None = None

    @classmethod
    def from_gateway_root(
        cls,
        *,
        gateway_root: Path,
        host: GatewayHost,
        port: int,
        tui_tracking_timings: GatewayTuiTrackingTimingOverridesV1 | None = None,
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
        tui_tracking_timings:
            Optional timing overrides for gateway-owned TUI tracking.

        Returns
        -------
        GatewayServiceRuntime
            Initialized service runtime.
        """

        return cls(
            gateway_root=gateway_root,
            host=host,
            port=port,
            tui_tracking_timings=tui_tracking_timings,
        )

    def _execution_mode_from_env(self) -> Literal["detached_process", "tmux_auxiliary_window"]:
        """Return the runtime execution mode published by the launcher."""

        raw_value = _optional_env_string(_GATEWAY_EXECUTION_MODE_ENV_VAR)
        if raw_value is None:
            return "detached_process"
        if raw_value not in {"detached_process", "tmux_auxiliary_window"}:
            raise GatewayError(f"Unsupported gateway execution mode `{raw_value}` in environment.")
        return cast(Literal["detached_process", "tmux_auxiliary_window"], raw_value)

    def start(self) -> None:
        """Initialize current-instance state and start the queue worker."""

        with self.m_lock:
            self._mark_running_requests_failed()
            self._initialize_instance_state()
            self._refresh_status_snapshot(active_execution="idle")
            refresh_gateway_manifest_publication(self.m_paths)
            self._start_tui_tracking_locked()
            self._log(
                f"gateway started host={self.m_host} port={self.m_port} attach_identity={self.m_attach_contract.attach_identity}"
            )

        self.m_worker_thread = threading.Thread(
            target=self._worker_loop,
            name="gateway-worker",
            daemon=True,
        )
        self.m_worker_thread.start()
        self.m_reminder_thread = threading.Thread(
            target=self._reminder_loop,
            name="gateway-reminder-scheduler",
            daemon=True,
        )
        self.m_reminder_thread.start()
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
        with self.m_reminder_condition:
            self.m_reminder_condition.notify_all()
        if self.m_worker_thread is not None:
            self.m_worker_thread.join(timeout=2.0)
        if self.m_reminder_thread is not None:
            self.m_reminder_thread.join(timeout=2.0)
        if self.m_notifier_thread is not None:
            self.m_notifier_thread.join(timeout=2.0)
        with self.m_lock:
            self._drop_pending_reminders_locked()
            if self.m_tui_tracking is not None:
                self.m_tui_tracking.stop()
                self.m_tui_tracking = None
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

    def memory(self) -> GatewayMemorySummaryV1:
        """Return the managed-agent memory summary."""

        paths = self._memory_paths()
        return GatewayMemorySummaryV1(
            memory_root=str(paths.memory_root),
            memo_file=str(paths.memo_file),
            pages_dir=str(paths.pages_dir),
        )

    def read_memory_memo(self) -> GatewayMemoryMemoResponseV1:
        """Return the fixed managed-agent memory memo."""

        paths = self._memory_paths()
        return GatewayMemoryMemoResponseV1(
            memo_file=str(paths.memo_file),
            content=read_memo(paths),
        )

    def write_memory_memo(
        self,
        request_payload: GatewayMemoryMemoWriteRequestV1,
        *,
        append: bool = False,
    ) -> GatewayMemoryMemoResponseV1:
        """Write or append the fixed managed-agent memory memo."""

        paths = self._memory_paths()
        write_memo(paths, request_payload.content, append=append)
        return GatewayMemoryMemoResponseV1(
            memo_file=str(paths.memo_file),
            content=read_memo(paths),
        )

    def list_memory_pages(
        self,
        request_payload: GatewayMemoryPageTreeRequestV1,
    ) -> GatewayMemoryPageTreeResponseV1:
        """Return a contained tree listing for the pages directory."""

        paths = self._memory_paths()
        entries = [
            GatewayMemoryPageEntryV1(
                path=entry.path,
                relative_link=entry.relative_link,
                absolute_path=str(entry.absolute_path),
                kind=entry.kind,
                size_bytes=entry.size_bytes,
            )
            for entry in list_memory_pages(
                paths,
                relative_path=request_payload.path,
            )
        ]
        return GatewayMemoryPageTreeResponseV1(
            root=str(paths.pages_dir),
            path=request_payload.path,
            entries=entries,
        )

    def resolve_memory_page_path(
        self,
        request_payload: GatewayMemoryPagePathRequestV1,
    ) -> GatewayMemoryPagePathResolutionV1:
        """Return contained path-discovery metadata for one pages path."""

        paths = self._memory_paths()
        resolved = resolve_memory_page_path(
            paths,
            relative_path=request_payload.path,
        )
        return GatewayMemoryPagePathResolutionV1(
            path=resolved.path,
            relative_link=resolved.relative_link,
            absolute_path=str(resolved.absolute_path),
            exists=resolved.exists,
            kind=resolved.kind,
            size_bytes=resolved.size_bytes,
        )

    def read_memory_page(
        self,
        request_payload: GatewayMemoryPagePathRequestV1,
    ) -> GatewayMemoryPageResponseV1:
        """Read a contained file from the pages directory."""

        paths = self._memory_paths()
        resolved = resolve_memory_page_path(
            paths,
            relative_path=request_payload.path,
        )
        return GatewayMemoryPageResponseV1(
            path=resolved.path,
            relative_link=resolved.relative_link,
            absolute_path=str(resolved.absolute_path),
            content=read_memory_page(
                paths,
                relative_path=request_payload.path,
            ),
        )

    def write_memory_page(
        self,
        request_payload: GatewayMemoryPageWriteRequestV1,
        *,
        append: bool = False,
    ) -> GatewayMemoryActionResponseV1:
        """Write or append a contained file in the pages directory."""

        paths = self._memory_paths()
        write_memory_page(
            paths,
            relative_path=request_payload.path,
            content=request_payload.content,
            append=append,
        )
        resolved = resolve_memory_page_path(
            paths,
            relative_path=request_payload.path,
        )
        return GatewayMemoryActionResponseV1(
            action="append_page" if append else "write_page",
            path=resolved.path,
            relative_link=resolved.relative_link,
            absolute_path=str(resolved.absolute_path),
            detail="Memory page appended." if append else "Memory page written.",
        )

    def delete_memory_page(
        self,
        request_payload: GatewayMemoryPagePathRequestV1,
    ) -> GatewayMemoryActionResponseV1:
        """Delete a contained file or directory from the pages directory."""

        paths = self._memory_paths()
        delete_memory_page(
            paths,
            relative_path=request_payload.path,
        )
        resolved = resolve_memory_page_path(
            paths,
            relative_path=request_payload.path,
        )
        return GatewayMemoryActionResponseV1(
            action="delete_page",
            path=resolved.path,
            relative_link=resolved.relative_link,
            absolute_path=str(resolved.absolute_path),
            detail="Memory page deleted.",
        )

    def _memory_paths(self) -> AgentMemoryPaths:
        """Load manifest-backed memory paths for this gateway runtime."""

        manifest_path = self.m_attach_contract.manifest_path
        if manifest_path is None:
            raise ValueError("Gateway attach contract does not expose a manifest path.")
        handle = load_session_manifest(Path(manifest_path).expanduser().resolve())
        payload = parse_session_manifest_payload(handle.payload, source=str(handle.path))
        runtime = payload.runtime
        if runtime.memory_root is None or runtime.memo_file is None or runtime.pages_dir is None:
            raise ValueError("Session manifest does not expose managed memory metadata.")
        return AgentMemoryPaths(
            memory_root=Path(runtime.memory_root).expanduser().resolve(),
            memo_file=Path(runtime.memo_file).expanduser().resolve(),
            pages_dir=Path(runtime.pages_dir).expanduser().resolve(),
        )

    def get_tui_state(self) -> HoumaoTerminalStateResponse:
        """Return gateway-owned live tracked TUI state."""

        with self.m_lock:
            tracking = self._require_tui_tracking_locked()
        return tracking.current_state()

    def get_tui_history(self, *, limit: int) -> HoumaoTerminalSnapshotHistoryResponse:
        """Return gateway-owned live tracked TUI snapshot history."""

        with self.m_lock:
            tracking = self._require_tui_tracking_locked()
        return tracking.snapshot_history(limit=limit)

    def note_tui_prompt_submission(self, *, prompt: str) -> HoumaoTerminalStateResponse:
        """Record explicit prompt evidence in the gateway-owned tracker."""

        with self.m_lock:
            tracking = self._require_tui_tracking_locked()
        return tracking.note_prompt_submission(message=prompt)

    def set_headless_next_prompt_session(
        self,
        request_payload: GatewayHeadlessNextPromptSessionRequestV1,
    ) -> GatewayHeadlessControlStateV1:
        """Store one one-shot override for the next accepted auto headless prompt."""

        del request_payload
        with self.m_lock:
            self._require_native_headless_backend_locked()
            self.m_headless_next_prompt_override = GatewayHeadlessNextPromptOverrideV1(mode="new")
            return self._build_headless_control_state_locked()

    def get_headless_control_state(self) -> GatewayHeadlessControlStateV1:
        """Return read-optimized live headless control posture."""

        with self.m_lock:
            self._require_native_headless_backend_locked()
            return self._build_headless_control_state_locked()

    def _build_headless_control_state_locked(self) -> GatewayHeadlessControlStateV1:
        """Build the current live headless control-state payload."""

        status = self._refresh_status_snapshot(active_execution=self._active_execution_state())
        active_turn_id = self._active_headless_turn_id_locked()
        tmux_session_live = status.managed_agent_connectivity == "connected"
        active_execution = status.active_execution
        can_accept_prompt_now = (
            tmux_session_live
            and status.request_admission == "open"
            and active_execution == "idle"
            and active_turn_id is None
        )
        return GatewayHeadlessControlStateV1(
            runtime_resumable=tmux_session_live,
            tmux_session_live=tmux_session_live,
            can_accept_prompt_now=can_accept_prompt_now,
            interruptible=active_execution == "running" or active_turn_id is not None,
            chat_session=self._headless_chat_session_state_locked(),
            request_admission=status.request_admission,
            active_execution=active_execution,
            queue_depth=status.queue_depth,
            active_turn_id=active_turn_id,
        )

    def _require_native_headless_backend_locked(self) -> None:
        """Require a native headless attach backend for headless-only routes."""

        if self.m_attach_contract.backend not in {
            "claude_headless",
            "codex_headless",
            "gemini_headless",
        }:
            raise HTTPException(
                status_code=422,
                detail="Gateway headless live-state routes are only available for headless backends.",
            )

    def _headless_chat_session_state_locked(self) -> GatewayHeadlessChatSessionStateV1:
        """Return the current headless chat-session state from the persisted manifest."""

        manifest_path_value = self.m_attach_contract.manifest_path
        if manifest_path_value is None:
            raise HTTPException(
                status_code=503,
                detail="Gateway headless chat-session state is unavailable without manifest_path.",
            )
        try:
            handle = load_session_manifest(Path(manifest_path_value).expanduser().resolve())
            payload = parse_session_manifest_payload(handle.payload, source=str(handle.path))
        except (OSError, SessionManifestError) as exc:
            raise HTTPException(
                status_code=503,
                detail=f"Gateway headless chat-session state is unavailable: {exc}",
            ) from exc
        if payload.headless is None:
            raise HTTPException(
                status_code=422,
                detail="Gateway headless chat-session state is only available for headless manifests.",
            )
        current = (
            GatewayHeadlessCurrentChatSessionV1(id=payload.headless.session_id)
            if payload.headless.session_id is not None
            else None
        )
        return GatewayHeadlessChatSessionStateV1(
            current=current,
            startup_default=self._startup_default_from_manifest_locked(
                resume_selection_kind=payload.headless.resume_selection_kind,
                resume_selection_value=payload.headless.resume_selection_value,
            ),
            next_prompt_override=self.m_headless_next_prompt_override,
        )

    def _startup_default_from_manifest_locked(
        self,
        *,
        resume_selection_kind: str,
        resume_selection_value: str | None,
    ) -> GatewayHeadlessStartupDefaultV1:
        """Map persisted joined-launch selector state into startup-default state."""

        if resume_selection_kind == "last":
            return GatewayHeadlessStartupDefaultV1(mode="tool_last_or_new")
        if resume_selection_kind == "exact":
            if resume_selection_value is None:
                raise HTTPException(
                    status_code=503,
                    detail="Headless manifest is missing resume_selection_value for exact startup.",
                )
            return GatewayHeadlessStartupDefaultV1(mode="exact", id=resume_selection_value)
        return GatewayHeadlessStartupDefaultV1(mode="new")

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
            if (
                self.m_attach_contract.backend
                in {"claude_headless", "codex_headless", "gemini_headless"}
                and request_payload.kind == "submit_prompt"
                and (
                    status.active_execution == "running"
                    or self._active_headless_turn_id_locked() is not None
                )
            ):
                raise HTTPException(
                    status_code=409,
                    detail="Gateway headless prompt admission is blocked because managed work is already active.",
                )
            if request_payload.kind == "submit_prompt":
                submit_payload = cast(GatewayRequestPayloadSubmitPromptV1, request_payload.payload)
                dispatch_mode = self._prompt_dispatch_mode_locked(forced=False)
                execution_rejection = self._execution_override_rejection_detail(
                    dispatch_mode=dispatch_mode,
                    request_execution=submit_payload.execution,
                )
                if execution_rejection is not None:
                    raise HTTPException(status_code=422, detail=execution_rejection)

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

    def create_reminders(
        self,
        request_payload: GatewayReminderCreateBatchV1,
    ) -> GatewayReminderCreateResultV1:
        """Register one or more in-memory reminders."""

        with self.m_reminder_condition:
            created_reminders: list[_GatewayReminderRecord] = []
            for definition in request_payload.reminders:
                self._validate_reminder_delivery_supported(definition)
            for definition in request_payload.reminders:
                created_at = datetime.now(UTC)
                due_at = self._due_at_from_reminder_definition(
                    definition,
                    reference_time=created_at,
                )
                send_keys = definition.send_keys
                reminder = _GatewayReminderRecord(
                    reminder_id=self._generate_reminder_id_locked(),
                    mode=definition.mode,
                    delivery_kind=self._reminder_delivery_kind_from_definition(definition),
                    title=definition.title,
                    prompt=definition.prompt,
                    send_keys_sequence=send_keys.sequence if send_keys is not None else None,
                    send_keys_ensure_enter=send_keys.ensure_enter
                    if send_keys is not None
                    else True,
                    ranking=definition.ranking,
                    paused=definition.paused,
                    created_at=created_at,
                    next_due_at=due_at,
                    anchor_due_at=due_at,
                    interval_seconds=(
                        float(definition.interval_seconds)
                        if definition.interval_seconds is not None
                        else None
                    ),
                )
                self.m_reminders[reminder.reminder_id] = reminder
                created_reminders.append(reminder)
                append_gateway_event(
                    self.m_paths,
                    {
                        "kind": "reminder_registered",
                        "reminder_id": reminder.reminder_id,
                        "mode": reminder.mode,
                        "delivery_kind": reminder.delivery_kind,
                        "title": reminder.title,
                        "ranking": reminder.ranking,
                        "paused": reminder.paused,
                        "prompt_preview": (
                            reminder.prompt[:120] if reminder.prompt is not None else None
                        ),
                        "sequence_preview": (
                            reminder.send_keys_sequence[:120]
                            if reminder.send_keys_sequence is not None
                            else None
                        ),
                        "ensure_enter": (
                            reminder.send_keys_ensure_enter
                            if reminder.delivery_kind == "send_keys"
                            else None
                        ),
                        "created_at_utc": self._gateway_datetime_iso(reminder.created_at),
                        "next_due_at_utc": self._gateway_datetime_iso(reminder.next_due_at),
                        "interval_seconds": reminder.interval_seconds,
                    },
                )
                self._log(
                    "registered reminder "
                    f"reminder_id={reminder.reminder_id} "
                    f"ranking={reminder.ranking} "
                    f"paused={reminder.paused} "
                    f"next_due_at_utc={self._gateway_datetime_iso(reminder.next_due_at)}"
                )
            effective_reminder_id = self._effective_reminder_id_locked()
            self.m_reminder_condition.notify_all()
            return GatewayReminderCreateResultV1(
                effective_reminder_id=effective_reminder_id,
                reminders=[
                    self._build_reminder_model_locked(
                        reminder,
                        effective_reminder_id=effective_reminder_id,
                    )
                    for reminder in created_reminders
                ],
            )

    def list_reminders(self) -> GatewayReminderListV1:
        """Return live in-memory reminder inspection state."""

        with self.m_lock:
            return self._build_reminder_list_locked()

    def get_reminder(self, *, reminder_id: str) -> GatewayReminderV1:
        """Return one live reminder by identifier."""

        with self.m_lock:
            reminder = self.m_reminders.get(reminder_id)
            if reminder is None:
                raise HTTPException(status_code=404, detail=f"Unknown reminder `{reminder_id}`.")
            effective_reminder_id = self._effective_reminder_id_locked()
            return self._build_reminder_model_locked(
                reminder,
                effective_reminder_id=effective_reminder_id,
            )

    def put_reminder(
        self,
        *,
        reminder_id: str,
        request_payload: GatewayReminderPutV1,
    ) -> GatewayReminderV1:
        """Update one in-memory reminder."""

        with self.m_reminder_condition:
            reminder = self.m_reminders.get(reminder_id)
            if reminder is None:
                raise HTTPException(status_code=404, detail=f"Unknown reminder `{reminder_id}`.")
            if reminder.executing:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"Reminder `{reminder_id}` is executing and cannot be updated until "
                        "the current reminder delivery finishes."
                    ),
                )
            self._validate_reminder_delivery_supported(request_payload)
            updated_at = datetime.now(UTC)
            due_at = self._due_at_from_reminder_definition(
                request_payload,
                reference_time=updated_at,
            )
            send_keys = request_payload.send_keys
            reminder.mode = request_payload.mode
            reminder.delivery_kind = self._reminder_delivery_kind_from_definition(request_payload)
            reminder.title = request_payload.title
            reminder.prompt = request_payload.prompt
            reminder.send_keys_sequence = send_keys.sequence if send_keys is not None else None
            reminder.send_keys_ensure_enter = (
                send_keys.ensure_enter if send_keys is not None else True
            )
            reminder.ranking = request_payload.ranking
            reminder.paused = request_payload.paused
            reminder.next_due_at = due_at
            reminder.anchor_due_at = due_at
            reminder.interval_seconds = (
                float(request_payload.interval_seconds)
                if request_payload.interval_seconds is not None
                else None
            )
            reminder.deferred_signature = None
            append_gateway_event(
                self.m_paths,
                {
                    "kind": "reminder_updated",
                    "reminder_id": reminder_id,
                    "mode": reminder.mode,
                    "delivery_kind": reminder.delivery_kind,
                    "title": reminder.title,
                    "ranking": reminder.ranking,
                    "paused": reminder.paused,
                    "prompt_preview": reminder.prompt[:120]
                    if reminder.prompt is not None
                    else None,
                    "sequence_preview": (
                        reminder.send_keys_sequence[:120]
                        if reminder.send_keys_sequence is not None
                        else None
                    ),
                    "ensure_enter": (
                        reminder.send_keys_ensure_enter
                        if reminder.delivery_kind == "send_keys"
                        else None
                    ),
                    "next_due_at_utc": self._gateway_datetime_iso(reminder.next_due_at),
                    "interval_seconds": reminder.interval_seconds,
                },
            )
            self._log(
                "updated reminder "
                f"reminder_id={reminder_id} "
                f"ranking={reminder.ranking} "
                f"paused={reminder.paused} "
                f"next_due_at_utc={self._gateway_datetime_iso(reminder.next_due_at)}"
            )
            effective_reminder_id = self._effective_reminder_id_locked()
            self.m_reminder_condition.notify_all()
            return self._build_reminder_model_locked(
                reminder,
                effective_reminder_id=effective_reminder_id,
            )

    def delete_reminder(self, *, reminder_id: str) -> GatewayReminderDeleteResultV1:
        """Delete one reminder or future repetitions for an active execution."""

        with self.m_reminder_condition:
            reminder = self.m_reminders.get(reminder_id)
            if reminder is None:
                raise HTTPException(status_code=404, detail=f"Unknown reminder `{reminder_id}`.")
            if reminder.executing:
                reminder.delete_requested = True
                detail = (
                    "Reminder deletion recorded; the already-started reminder delivery will "
                    "continue until completion."
                )
            else:
                del self.m_reminders[reminder_id]
                detail = "Reminder deleted."
            append_gateway_event(
                self.m_paths,
                {
                    "kind": "reminder_deleted",
                    "reminder_id": reminder_id,
                    "executing": reminder.executing,
                    "delete_requested": True,
                    "detail": detail,
                },
            )
            self._log(f"deleted reminder reminder_id={reminder_id} executing={reminder.executing}")
            self.m_reminder_condition.notify_all()
            return GatewayReminderDeleteResultV1(reminder_id=reminder_id, detail=detail)

    def _due_at_from_reminder_definition(
        self,
        definition: GatewayReminderDefinitionV1,
        *,
        reference_time: datetime,
    ) -> datetime:
        """Return the next due time for one validated reminder definition."""

        if definition.start_after_seconds is not None:
            return reference_time + timedelta(seconds=float(definition.start_after_seconds))
        assert definition.deliver_at_utc is not None
        return _parse_gateway_timestamp(definition.deliver_at_utc)

    def _generate_reminder_id_locked(self) -> str:
        """Return one stable opaque identifier for a live reminder."""

        seed = f"{self.m_attach_contract.attach_identity}:{time.time()}:{len(self.m_reminders)}"
        return f"greminder-{hashlib.sha1(seed.encode('utf-8')).hexdigest()[:12]}"

    def _reminder_delivery_kind_from_definition(
        self,
        definition: GatewayReminderDefinitionV1,
    ) -> GatewayReminderDeliveryKind:
        """Return the delivery kind implied by one validated reminder definition."""

        return "send_keys" if definition.send_keys is not None else "prompt"

    def _validate_reminder_delivery_supported(
        self,
        definition: GatewayReminderDefinitionV1,
    ) -> None:
        """Reject reminder delivery shapes unsupported by the attached gateway target."""

        if definition.send_keys is None:
            return
        control_input_support = self.m_adapter.describe_control_input_support()
        if control_input_support.supported:
            return
        detail = control_input_support.detail or (
            "Raw control input is unsupported for the attached gateway target."
        )
        raise HTTPException(status_code=422, detail=detail)

    def _build_reminder_send_keys_model_locked(
        self,
        reminder: _GatewayReminderRecord,
    ) -> GatewayReminderSendKeysV1 | None:
        """Build the public send-keys payload for one in-memory reminder."""

        if reminder.delivery_kind != "send_keys":
            return None
        assert reminder.send_keys_sequence is not None
        return GatewayReminderSendKeysV1(
            sequence=reminder.send_keys_sequence,
            ensure_enter=reminder.send_keys_ensure_enter,
        )

    def _reminder_sort_key_locked(
        self,
        reminder: _GatewayReminderRecord,
    ) -> tuple[int, datetime, str]:
        """Return the deterministic live reminder ordering key."""

        return (reminder.ranking, reminder.created_at, reminder.reminder_id)

    def _effective_reminder_locked(self) -> _GatewayReminderRecord | None:
        """Return the current effective reminder, if any."""

        if not self.m_reminders:
            return None
        return min(self.m_reminders.values(), key=self._reminder_sort_key_locked)

    def _effective_reminder_id_locked(self) -> str | None:
        """Return the current effective reminder identifier, if any."""

        effective_reminder = self._effective_reminder_locked()
        if effective_reminder is None:
            return None
        return effective_reminder.reminder_id

    def _build_reminder_model_locked(
        self,
        reminder: _GatewayReminderRecord,
        *,
        effective_reminder_id: str | None = None,
    ) -> GatewayReminderV1:
        """Build one public inspection model for an in-memory reminder."""

        if effective_reminder_id is None:
            effective_reminder_id = self._effective_reminder_id_locked()
        selection_state: GatewayReminderSelectionState
        blocked_by_reminder_id: str | None
        if reminder.reminder_id == effective_reminder_id:
            selection_state = "effective"
            blocked_by_reminder_id = None
        else:
            selection_state = "blocked"
            blocked_by_reminder_id = effective_reminder_id
        return GatewayReminderV1(
            reminder_id=reminder.reminder_id,
            mode=reminder.mode,
            delivery_kind=reminder.delivery_kind,
            title=reminder.title,
            prompt=reminder.prompt,
            send_keys=self._build_reminder_send_keys_model_locked(reminder),
            ranking=reminder.ranking,
            paused=reminder.paused,
            selection_state=selection_state,
            delivery_state=self._reminder_delivery_state_locked(reminder),
            created_at_utc=self._gateway_datetime_iso(reminder.created_at),
            next_due_at_utc=self._gateway_datetime_iso(reminder.next_due_at),
            interval_seconds=reminder.interval_seconds,
            last_started_at_utc=(
                self._gateway_datetime_iso(reminder.last_started_at)
                if reminder.last_started_at is not None
                else None
            ),
            blocked_by_reminder_id=blocked_by_reminder_id,
        )

    def _build_reminder_list_locked(self) -> GatewayReminderListV1:
        """Build the public inspection payload for the live reminder set."""

        reminders = sorted(self.m_reminders.values(), key=self._reminder_sort_key_locked)
        effective_reminder_id = self._effective_reminder_id_locked()
        return GatewayReminderListV1(
            effective_reminder_id=effective_reminder_id,
            reminders=[
                self._build_reminder_model_locked(
                    reminder,
                    effective_reminder_id=effective_reminder_id,
                )
                for reminder in reminders
            ],
        )

    def _reminder_delivery_state_locked(
        self,
        reminder: _GatewayReminderRecord,
    ) -> GatewayReminderDeliveryState:
        """Return the public delivery state for one live reminder."""

        if reminder.executing:
            return "executing"
        if reminder.next_due_at <= datetime.now(UTC):
            return "overdue"
        return "scheduled"

    def _gateway_datetime_iso(self, value: datetime) -> str:
        """Render one UTC datetime for the gateway HTTP surface."""

        return value.astimezone(UTC).isoformat()

    def _drop_pending_reminders_locked(self) -> None:
        """Log and clear reminders that vanish with gateway shutdown."""

        if not self.m_reminders:
            return
        effective_reminder_id = self._effective_reminder_id_locked()
        for reminder in list(self.m_reminders.values()):
            append_gateway_event(
                self.m_paths,
                {
                    "kind": "reminder_lost_on_restart",
                    "reminder_id": reminder.reminder_id,
                    "mode": reminder.mode,
                    "delivery_kind": reminder.delivery_kind,
                    "ranking": reminder.ranking,
                    "paused": reminder.paused,
                    "selection_state": (
                        "effective" if reminder.reminder_id == effective_reminder_id else "blocked"
                    ),
                    "delivery_state": self._reminder_delivery_state_locked(reminder),
                    "next_due_at_utc": self._gateway_datetime_iso(reminder.next_due_at),
                },
            )
            self._log(
                "lost in-memory reminder "
                f"reminder_id={reminder.reminder_id} "
                f"delivery_state={self._reminder_delivery_state_locked(reminder)}"
            )
        self.m_reminders.clear()
        self.m_active_reminder_id = None

    def _normalize_reminder_send_keys_sequence(
        self,
        *,
        sequence: str,
        ensure_enter: bool,
    ) -> str:
        """Normalize one reminder send-keys sequence according to `ensure_enter`."""

        if not ensure_enter:
            return sequence
        normalized = sequence
        while normalized.endswith(_SEND_KEYS_ENTER_TOKEN):
            normalized = normalized[: -len(_SEND_KEYS_ENTER_TOKEN)]
        return f"{normalized}{_SEND_KEYS_ENTER_TOKEN}"

    def control_prompt(
        self,
        request_payload: GatewayPromptControlRequestV1,
    ) -> GatewayPromptControlResultV1:
        """Dispatch one prompt immediately when the addressed target is ready."""

        dispatch_mode: Literal["tui", "local_headless", "server_headless"]
        consume_headless_override = False
        headless_session_selection: HeadlessTurnSessionSelection | None = None
        execution_model = (
            request_payload.execution.to_model_config()
            if request_payload.execution is not None
            else None
        )
        tracking: SingleSessionTrackingRuntime | None = None
        use_tui_reset_workflow = False
        prompt = request_payload.prompt
        forced = request_payload.force

        with self.m_lock:
            status = self._refresh_status_snapshot(active_execution=self._active_execution_state())
            dispatch_mode = self._prompt_dispatch_mode_locked(forced=forced)
            self._validate_prompt_control_locked(
                status=status,
                forced=forced,
                dispatch_mode=dispatch_mode,
                request_chat_session=request_payload.chat_session,
            )
            execution_rejection = self._execution_override_rejection_detail(
                dispatch_mode=dispatch_mode,
                request_execution=request_payload.execution,
            )
            if execution_rejection is not None:
                self._raise_prompt_control_http_error(
                    status_code=422,
                    forced=forced,
                    error_code="invalid_execution",
                    detail=execution_rejection,
                )
            if not forced:
                self._require_prompt_ready_locked(
                    status=status,
                    dispatch_mode=dispatch_mode,
                    forced=forced,
                )

            if dispatch_mode in {"local_headless", "server_headless"}:
                (
                    headless_session_selection,
                    consume_headless_override,
                ) = self._resolve_headless_prompt_selection_locked(
                    request_chat_session=request_payload.chat_session,
                    allow_next_prompt_override=True,
                    forced=forced,
                )
            if dispatch_mode == "local_headless":
                turn_id = self._next_direct_headless_turn_id_locked()
                return self._start_direct_headless_prompt_locked(
                    prompt=prompt,
                    turn_id=turn_id,
                    forced=forced,
                    session_selection=headless_session_selection,
                    execution_model=execution_model,
                    consume_next_prompt_override=consume_headless_override,
                )
            tracking = self.m_tui_tracking
            use_tui_reset_workflow = (
                dispatch_mode == "tui" and request_payload.chat_session is not None
            )

        try:
            if use_tui_reset_workflow:
                self._dispatch_tui_new_prompt_workflow(prompt=prompt)
            else:
                self.m_adapter.submit_prompt(
                    prompt=prompt,
                    session_selection=headless_session_selection,
                    execution_model=execution_model,
                )
        except (GatewayError, CaoApiError, ValidationError) as exc:
            self._raise_prompt_control_http_error(
                status_code=422,
                forced=forced,
                error_code="dispatch_failed",
                detail=str(exc),
            )

        if consume_headless_override:
            with self.m_lock:
                self.m_headless_next_prompt_override = None

        if tracking is not None and not use_tui_reset_workflow:
            tracking.note_prompt_submission(message=prompt)
        append_gateway_event(
            self.m_paths,
            {
                "kind": "control_prompt_submitted",
                "forced": forced,
                "submitted_at_utc": now_utc_iso(),
            },
        )
        return GatewayPromptControlResultV1(
            forced=forced,
            detail="Prompt dispatched.",
        )

    def send_control_input(
        self,
        request_payload: GatewayControlInputRequestV1,
    ) -> GatewayControlInputResultV1:
        """Deliver one raw control-input sequence without queueing prompt work."""

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

        try:
            detail = self.m_adapter.send_control_input(
                sequence=request_payload.sequence,
                escape_special_keys=request_payload.escape_special_keys,
            )
        except (GatewayError, CaoApiError, ValidationError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        append_gateway_event(
            self.m_paths,
            {
                "kind": "control_input",
                "escape_special_keys": request_payload.escape_special_keys,
                "sequence_preview": request_payload.sequence[:120],
                "submitted_at_utc": now_utc_iso(),
            },
        )
        return GatewayControlInputResultV1(detail=detail)

    def _dispatch_tui_new_prompt_workflow(self, *, prompt: str) -> None:
        """Clear the current TUI conversation, wait for readiness, then send the prompt."""

        tracking = self.m_tui_tracking
        if tracking is None:
            raise GatewayError(
                "Gateway TUI tracking is unavailable for reset-based prompt control."
            )
        self.m_adapter.submit_prompt(prompt=_TUI_RESET_PROMPT)
        tracking.note_prompt_submission(message=_TUI_RESET_PROMPT)
        self._wait_for_tui_ready_after_reset(tracking=tracking)
        self.m_adapter.submit_prompt(prompt=prompt)
        tracking.note_prompt_submission(message=prompt)

    def _wait_for_tui_ready_after_reset(
        self,
        *,
        tracking: SingleSessionTrackingRuntime,
    ) -> None:
        """Wait for the tracked TUI surface to stabilize back to prompt-ready."""

        deadline = time.monotonic() + _TUI_RESET_READY_WAIT_SECONDS
        # Give the reset prompt one poll cycle to take effect before accepting ready again.
        time.sleep(_TUI_RESET_READY_POLL_INTERVAL_SECONDS)
        while time.monotonic() < deadline:
            tracking.refresh_once()
            with self.m_lock:
                reasons = self._tui_prompt_not_ready_reasons_locked()
            if not reasons:
                return
            time.sleep(_TUI_RESET_READY_POLL_INTERVAL_SECONDS)
        raise GatewayError(
            "TUI reset prompt was submitted, but the surface did not stabilize back to "
            "prompt-ready posture in time."
        )

    def _resolve_headless_prompt_selection_locked(
        self,
        *,
        request_chat_session: GatewayChatSessionSelectorV1 | None,
        allow_next_prompt_override: bool,
        forced: bool,
    ) -> tuple[HeadlessTurnSessionSelection, bool]:
        """Resolve one headless prompt selector into the backend execution selection."""
        chat_session_state = self._headless_chat_session_state_locked()
        requested_mode = request_chat_session.mode if request_chat_session is not None else "auto"

        if requested_mode == "new":
            return HeadlessTurnSessionSelection(mode="new"), False
        if requested_mode == "tool_last_or_new":
            return HeadlessTurnSessionSelection(mode="tool_last_or_new"), False
        if requested_mode == "exact":
            assert request_chat_session is not None and request_chat_session.id is not None
            return (
                HeadlessTurnSessionSelection(
                    mode="exact",
                    session_id=request_chat_session.id,
                ),
                False,
            )
        if requested_mode == "current":
            current = chat_session_state.current
            if current is None:
                self._raise_prompt_control_http_error(
                    status_code=409,
                    forced=False,
                    error_code="missing_current_chat_session",
                    detail=(
                        "chat_session.mode=`current` requires a pinned current provider "
                        "session, but none is available."
                    ),
                )
            return HeadlessTurnSessionSelection(mode="exact", session_id=current.id), False

        if allow_next_prompt_override and chat_session_state.next_prompt_override is not None:
            return HeadlessTurnSessionSelection(mode="new"), True
        if chat_session_state.current is not None:
            return (
                HeadlessTurnSessionSelection(
                    mode="exact",
                    session_id=chat_session_state.current.id,
                ),
                False,
            )
        startup_default = chat_session_state.startup_default
        if startup_default.mode == "exact":
            assert startup_default.id is not None
            return HeadlessTurnSessionSelection(mode="exact", session_id=startup_default.id), False
        return HeadlessTurnSessionSelection(mode=startup_default.mode), False

    def _prompt_dispatch_mode_locked(
        self,
        *,
        forced: bool,
    ) -> Literal["tui", "local_headless", "server_headless"]:
        """Return the direct prompt-control execution mode for the attached backend."""

        backend = self.m_attach_contract.backend
        if backend in {"cao_rest", "houmao_server_rest", "local_interactive"}:
            return "tui"
        if backend in {"claude_headless", "codex_headless", "gemini_headless"}:
            if isinstance(self.m_adapter, _ServerManagedHeadlessGatewayAdapter):
                return "server_headless"
            if isinstance(self.m_adapter, _LocalHeadlessGatewayAdapter):
                return "local_headless"
        self._raise_prompt_control_http_error(
            status_code=501,
            forced=forced,
            error_code="unsupported_backend",
            detail=f"Gateway prompt control is not implemented for backend `{backend}`.",
        )

    def _validate_prompt_control_locked(
        self,
        *,
        status: GatewayStatusV1,
        forced: bool,
        dispatch_mode: Literal["tui", "local_headless", "server_headless"],
        request_chat_session: GatewayChatSessionSelectorV1 | None,
    ) -> None:
        """Reject prompt control for unavailable or reconciliation-blocked gateway state."""

        if status.request_admission == "blocked_reconciliation":
            self._raise_prompt_control_http_error(
                status_code=409,
                forced=forced,
                error_code="blocked_reconciliation",
                detail="Gateway prompt control is blocked pending managed-agent reconciliation.",
            )
        if status.managed_agent_connectivity != "connected":
            self._raise_prompt_control_http_error(
                status_code=503,
                forced=forced,
                error_code="unavailable",
                detail="Gateway prompt control is unavailable because the managed agent is detached.",
            )
        if request_chat_session is None:
            return
        if dispatch_mode == "tui":
            if request_chat_session.mode != "new":
                self._raise_prompt_control_http_error(
                    status_code=422,
                    forced=forced,
                    error_code="invalid_chat_session",
                    detail=(
                        "TUI prompt control only supports chat_session.mode=`new`; "
                        f"got `{request_chat_session.mode}`."
                    ),
                )
            return
        if dispatch_mode in {"local_headless", "server_headless"}:
            return
        self._raise_prompt_control_http_error(
            status_code=422,
            forced=forced,
            error_code="invalid_chat_session",
            detail="chat_session is unsupported for this gateway target.",
        )

    def _execution_override_rejection_detail(
        self,
        *,
        dispatch_mode: Literal["tui", "local_headless", "server_headless"],
        request_execution: GatewayExecutionOverrideV1 | None,
    ) -> str | None:
        """Return the rejection detail for unsupported execution overrides."""

        if request_execution is None:
            return None
        if dispatch_mode in {"local_headless", "server_headless"}:
            return None
        if dispatch_mode == "tui":
            return "Execution overrides are only supported for headless gateway targets."
        return "Execution overrides are unsupported for this gateway target."

    def _require_prompt_ready_locked(
        self,
        *,
        status: GatewayStatusV1,
        dispatch_mode: Literal["tui", "local_headless", "server_headless"],
        forced: bool,
    ) -> None:
        """Require prompt-ready posture for non-forced direct prompt control."""

        if status.active_execution != "idle" or status.queue_depth > 0:
            reasons: list[str] = []
            if status.active_execution != "idle":
                reasons.append(f"active_execution={status.active_execution!r}")
            if status.queue_depth > 0:
                reasons.append(f"queue_depth={status.queue_depth}")
            self._raise_prompt_control_http_error(
                status_code=409,
                forced=forced,
                error_code="not_ready",
                detail=(
                    "Gateway prompt rejected because gateway-managed work is already active "
                    f"({', '.join(reasons)})."
                ),
            )

        if dispatch_mode == "tui":
            self._require_tui_prompt_ready_locked(forced=forced)
            return
        if dispatch_mode == "local_headless":
            active_turn_id = self._active_headless_turn_id_locked()
            if active_turn_id is not None:
                self._raise_prompt_control_http_error(
                    status_code=409,
                    forced=forced,
                    error_code="not_ready",
                    detail=(
                        "Gateway prompt rejected because a headless turn is already active "
                        f"(`{active_turn_id}`)."
                    ),
                )
            return
        if status.terminal_surface_eligibility != "ready":
            self._raise_prompt_control_http_error(
                status_code=409,
                forced=forced,
                error_code="not_ready",
                detail=(
                    "Gateway prompt rejected because the managed headless target is not ready "
                    "to accept a new prompt."
                ),
            )

    def _require_tui_prompt_ready_locked(self, *, forced: bool) -> None:
        """Require a stable prompt-ready TUI posture for direct prompt control."""

        reasons = self._tui_prompt_not_ready_reasons_locked()
        if not reasons:
            return
        self._raise_prompt_control_http_error(
            status_code=409,
            forced=forced,
            error_code="not_ready",
            detail=(
                "Gateway prompt rejected because the TUI is not submit-ready "
                f"({', '.join(reasons)})."
            ),
        )

    def _tui_prompt_not_ready_reasons_locked(self) -> list[str]:
        """Return TUI prompt-readiness reasons when the tracked surface is not ready."""

        state = self._require_tui_tracking_locked().current_state()
        reasons: list[str] = []
        if state.turn.phase != "ready":
            reasons.append(f"turn.phase={state.turn.phase!r}")
        if state.surface.accepting_input != "yes":
            reasons.append(f"surface.accepting_input={state.surface.accepting_input!r}")
        if state.surface.editing_input != "no":
            reasons.append(f"surface.editing_input={state.surface.editing_input!r}")
        if state.surface.ready_posture != "yes":
            reasons.append(f"surface.ready_posture={state.surface.ready_posture!r}")
        if not state.stability.stable:
            reasons.append("stability.stable=false")
        parsed_surface = state.parsed_surface
        if parsed_surface is not None:
            if parsed_surface.business_state != "idle":
                reasons.append(f"parsed_surface.business_state={parsed_surface.business_state!r}")
            if parsed_surface.input_mode != "freeform":
                reasons.append(f"parsed_surface.input_mode={parsed_surface.input_mode!r}")
        return reasons

    def _notifier_dispatch_mode_locked(
        self,
    ) -> Literal["tui", "local_headless", "server_headless"] | None:
        """Return the notifier readiness mode for the attached backend."""

        backend = self.m_attach_contract.backend
        if backend in {"cao_rest", "houmao_server_rest", "local_interactive"}:
            return "tui"
        if backend in {"claude_headless", "codex_headless", "gemini_headless"}:
            if isinstance(self.m_adapter, _ServerManagedHeadlessGatewayAdapter):
                return "server_headless"
            if isinstance(self.m_adapter, _LocalHeadlessGatewayAdapter):
                return "local_headless"
        return None

    def _notifier_block_detail_locked(self, *, status: GatewayStatusV1) -> str | None:
        """Return one human-readable reason when notifier enqueueing must defer."""

        if (
            status.request_admission != "open"
            or status.active_execution != "idle"
            or status.queue_depth > 0
        ):
            return (
                "mail notifier poll deferred because the managed session is busy "
                f"(admission={status.request_admission}, "
                f"active_execution={status.active_execution}, "
                f"queue_depth={status.queue_depth})"
            )

        dispatch_mode = self._notifier_dispatch_mode_locked()
        if dispatch_mode == "tui":
            try:
                reasons = self._tui_prompt_not_ready_reasons_locked()
            except HTTPException as exc:
                return (
                    "mail notifier poll deferred because live TUI readiness is unavailable "
                    f"({exc.detail})"
                )
            if reasons:
                return (
                    "mail notifier poll deferred because the managed session is not prompt-ready "
                    f"({', '.join(reasons)})"
                )
            return None

        if dispatch_mode == "local_headless":
            active_turn_id = self._active_headless_turn_id_locked()
            if active_turn_id is not None:
                return (
                    "mail notifier poll deferred because the managed session is not prompt-ready "
                    f"(active_turn_id={active_turn_id!r})"
                )
            return None

        if dispatch_mode == "server_headless":
            if status.terminal_surface_eligibility != "ready":
                return (
                    "mail notifier poll deferred because the managed session is not prompt-ready "
                    f"(terminal_surface_eligibility={status.terminal_surface_eligibility!r})"
                )
            return None

        return None

    def _next_direct_headless_turn_id_locked(self) -> str:
        """Return the next direct-control headless turn id."""

        seed = f"{self.m_attach_contract.attach_identity}:{time.time()}"
        return f"turn-{hashlib.sha1(seed.encode('utf-8')).hexdigest()[:12]}"

    def _start_direct_headless_prompt_locked(
        self,
        *,
        prompt: str,
        turn_id: str,
        forced: bool,
        session_selection: HeadlessTurnSessionSelection | None,
        execution_model: ModelConfig | None,
        consume_next_prompt_override: bool,
    ) -> GatewayPromptControlResultV1:
        """Start one native headless prompt in the background and return immediately."""

        self.m_direct_prompt_turn_id = turn_id
        thread = threading.Thread(
            target=self._run_direct_headless_prompt,
            kwargs={
                "prompt": prompt,
                "turn_id": turn_id,
                "session_selection": session_selection,
                "execution_model": execution_model,
            },
            name=f"gateway-direct-prompt-{turn_id}",
            daemon=True,
        )
        self.m_direct_prompt_thread = thread
        thread.start()
        if consume_next_prompt_override:
            self.m_headless_next_prompt_override = None
        append_gateway_event(
            self.m_paths,
            {
                "kind": "control_prompt_submitted",
                "forced": forced,
                "submitted_at_utc": now_utc_iso(),
                "turn_id": turn_id,
            },
        )
        self._refresh_status_snapshot(active_execution=self._active_execution_state())
        return GatewayPromptControlResultV1(
            forced=forced,
            detail="Prompt dispatched.",
        )

    def _run_direct_headless_prompt(
        self,
        *,
        prompt: str,
        turn_id: str,
        session_selection: HeadlessTurnSessionSelection | None,
        execution_model: ModelConfig | None,
    ) -> None:
        """Execute one native headless direct prompt in a background thread."""

        try:
            self.m_adapter.submit_prompt(
                prompt=prompt,
                turn_id=turn_id,
                session_selection=session_selection,
                execution_model=execution_model,
            )
        except (GatewayError, CaoApiError, ValidationError) as exc:
            append_gateway_event(
                self.m_paths,
                {
                    "kind": "control_prompt_failed",
                    "turn_id": turn_id,
                    "error_detail": str(exc),
                    "finished_at_utc": now_utc_iso(),
                },
            )
            self._log(f"direct gateway prompt failed turn_id={turn_id} detail={exc}")
        else:
            append_gateway_event(
                self.m_paths,
                {
                    "kind": "control_prompt_completed",
                    "turn_id": turn_id,
                    "finished_at_utc": now_utc_iso(),
                },
            )
        finally:
            with self.m_lock:
                if self.m_direct_prompt_turn_id == turn_id:
                    self.m_direct_prompt_turn_id = None
                self.m_direct_prompt_thread = None
                self._refresh_status_snapshot(active_execution=self._active_execution_state())
                self.m_reminder_condition.notify_all()

    def _raise_prompt_control_http_error(
        self,
        *,
        status_code: int,
        forced: bool,
        error_code: str,
        detail: str,
    ) -> NoReturn:
        """Raise one structured HTTP refusal for direct prompt control."""

        payload = GatewayPromptControlErrorV1(
            forced=forced,
            error_code=error_code,
            detail=detail,
        )
        raise HTTPException(status_code=status_code, detail=payload.model_dump(mode="json"))

    def get_mail_status(self) -> GatewayMailStatusV1:
        """Return shared mailbox availability for the attached session."""

        with self.m_lock:
            self._require_loopback_mail_surface()
            try:
                return self._mailbox_adapter_locked().status()
            except GatewayError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc

    def list_mail(self, request_payload: GatewayMailListRequestV1) -> GatewayMailListResponseV1:
        """Run one shared mailbox list request."""

        with self.m_lock:
            self._require_loopback_mail_surface()
            try:
                adapter = self._mailbox_adapter_locked()
            except GatewayError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            try:
                messages = adapter.list_messages(
                    box=request_payload.box,
                    read_state=request_payload.read_state,
                    answered_state=request_payload.answered_state,
                    archived=request_payload.archived,
                    limit=request_payload.limit,
                    since=request_payload.since,
                    include_body=request_payload.include_body,
                )
            except GatewayMailboxError as exc:
                raise HTTPException(status_code=502, detail=str(exc)) from exc
            status = adapter.status()
            unread_count = sum(1 for message in messages if message.unread is True)
            open_count = sum(1 for message in messages if message.archived is not True)
            return GatewayMailListResponseV1(
                transport=status.transport,
                principal_id=status.principal_id,
                address=status.address,
                box=request_payload.box,
                message_count=len(messages),
                open_count=open_count,
                unread_count=unread_count,
                messages=messages,
            )

    def peek_mail(
        self, request_payload: GatewayMailMessageRequestV1
    ) -> GatewayMailMessageResponseV1:
        """Run one shared mailbox peek request."""

        return self._mail_message_request(operation="peek", request_payload=request_payload)

    def read_mail(
        self, request_payload: GatewayMailMessageRequestV1
    ) -> GatewayMailMessageResponseV1:
        """Run one shared mailbox read request."""

        return self._mail_message_request(operation="read", request_payload=request_payload)

    def _mail_message_request(
        self,
        *,
        operation: Literal["peek", "read"],
        request_payload: GatewayMailMessageRequestV1,
    ) -> GatewayMailMessageResponseV1:
        """Run one shared mailbox message retrieval request."""

        with self.m_lock:
            self._require_loopback_mail_surface()
            try:
                adapter = self._mailbox_adapter_locked()
            except GatewayError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            try:
                if operation == "peek":
                    message = adapter.peek(
                        message_ref=request_payload.message_ref,
                        box=request_payload.box,
                    )
                else:
                    message = adapter.read(
                        message_ref=request_payload.message_ref,
                        box=request_payload.box,
                    )
            except GatewayMailboxError as exc:
                raise HTTPException(status_code=502, detail=str(exc)) from exc
            status = adapter.status()
            return GatewayMailMessageResponseV1(
                operation=operation,
                transport=status.transport,
                principal_id=status.principal_id,
                address=status.address,
                message=message,
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
            except GatewayMailboxUnsupportedError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
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

    def post_mail(self, request_payload: GatewayMailPostRequestV1) -> GatewayMailActionResponseV1:
        """Run one shared mailbox operator-origin post request."""

        with self.m_lock:
            self._require_loopback_mail_surface()
            try:
                adapter = self._mailbox_adapter_locked()
            except GatewayError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            try:
                message = adapter.post(
                    subject=request_payload.subject,
                    body_content=request_payload.body_content,
                    reply_policy=request_payload.reply_policy,
                    attachments=request_payload.attachments,
                )
            except GatewayMailboxUnsupportedError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            except GatewayMailboxError as exc:
                raise HTTPException(status_code=502, detail=str(exc)) from exc
            status = adapter.status()
            return GatewayMailActionResponseV1(
                operation="post",
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
            except GatewayMailboxUnsupportedError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
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

    def mark_mail(
        self,
        request_payload: GatewayMailMarkRequestV1,
    ) -> GatewayMailLifecycleResponseV1:
        """Run one shared mailbox mark request."""

        return self._mail_lifecycle_request(
            operation="mark",
            request_payload=request_payload,
        )

    def move_mail(
        self,
        request_payload: GatewayMailMoveRequestV1,
    ) -> GatewayMailLifecycleResponseV1:
        """Run one shared mailbox move request."""

        return self._mail_lifecycle_request(
            operation="move",
            request_payload=request_payload,
        )

    def archive_mail(
        self,
        request_payload: GatewayMailArchiveRequestV1,
    ) -> GatewayMailLifecycleResponseV1:
        """Run one shared mailbox archive request."""

        return self._mail_lifecycle_request(
            operation="archive",
            request_payload=request_payload,
        )

    def _mail_lifecycle_request(
        self,
        *,
        operation: Literal["mark", "move", "archive"],
        request_payload: GatewayMailMarkRequestV1
        | GatewayMailMoveRequestV1
        | GatewayMailArchiveRequestV1,
    ) -> GatewayMailLifecycleResponseV1:
        """Run one shared mailbox lifecycle mutation request."""

        with self.m_lock:
            self._require_loopback_mail_surface()
            try:
                adapter = self._mailbox_adapter_locked()
            except GatewayError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            try:
                if isinstance(request_payload, GatewayMailMarkRequestV1):
                    messages = adapter.mark(
                        message_refs=request_payload.message_refs,
                        read=request_payload.read,
                        answered=request_payload.answered,
                        archived=request_payload.archived,
                    )
                elif isinstance(request_payload, GatewayMailMoveRequestV1):
                    messages = adapter.move(
                        message_refs=request_payload.message_refs,
                        destination_box=request_payload.destination_box,
                    )
                else:
                    messages = adapter.archive(message_refs=request_payload.message_refs)
            except GatewayMailboxError as exc:
                raise HTTPException(status_code=502, detail=str(exc)) from exc
            status = adapter.status()
            return GatewayMailLifecycleResponseV1(
                operation=operation,
                transport=status.transport,
                principal_id=status.principal_id,
                address=status.address,
                message_count=len(messages),
                messages=messages,
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
                self._require_live_notifier_mailbox_config_locked()
            except GatewayError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            record = write_gateway_mail_notifier_record(
                self.m_paths.queue_path,
                enabled=True,
                interval_seconds=request_payload.interval_seconds,
                mode=request_payload.mode,
                last_notified_digest=None,
                last_error=None,
            )
            self._log(
                "mail notifier enabled "
                f"interval_seconds={request_payload.interval_seconds} mode={request_payload.mode}"
            )
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
            self._require_live_notifier_mailbox_config_locked()
        except GatewayError as exc:
            return False, str(exc)
        return True, None

    def _require_live_notifier_mailbox_config_locked(self) -> MailboxResolvedConfig:
        """Return durable mailbox config only when live notifier actionability is present."""

        mailbox = self._load_mailbox_config()
        try:
            resolve_live_mailbox_binding(durable_mailbox=mailbox)
        except ValueError as exc:
            raise GatewayError(
                f"Gateway notifier requires an actionable manifest-backed mailbox binding: {exc}"
            ) from exc
        return mailbox

    def _load_mailbox_config(self) -> MailboxResolvedConfig:
        """Load the manifest-backed mailbox config required by mailbox routes."""

        payload = self._load_manifest_payload_for_mailbox_support()
        try:
            mailbox = resolved_mailbox_config_from_payload(
                payload.launch_plan.mailbox,
                manifest_path=self.m_manifest_path or Path("<unknown>"),
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

    def _load_manifest_payload_for_mailbox_support(self) -> SessionManifestPayloadV4:
        """Load and parse the runtime-owned manifest payload required by mailbox routes."""

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
        self.m_manifest_path = handle.path.resolve()
        return payload

    def _mail_notifier_skill_usage_block(self, *, mailbox: MailboxResolvedConfig) -> str:
        """Return prompt guidance about installed Houmao mailbox skills for this session."""

        payload = self._load_manifest_payload_for_mailbox_support()
        tool = payload.launch_plan.tool
        home_path = Path(payload.launch_plan.home_selector.home_path).resolve()
        gateway_base_url = f"http://{self.m_host}:{self.m_port}"
        processing_path = projected_mailbox_skill_document_path(
            tool=tool,
            home_path=home_path,
            skill_reference=mailbox_processing_skill_reference(tool=tool),
        )
        gateway_path = projected_mailbox_skill_document_path(
            tool=tool,
            home_path=home_path,
            skill_reference=mailbox_gateway_skill_reference(tool=tool),
        )

        if not processing_path.is_file():
            return "\n".join(
                [
                    "Houmao mailbox skills are not installed for this session.",
                    "List open inbox mail through the shared gateway mailbox API and use the endpoint URLs below directly for this turn.",
                ]
            )

        lines = [
            (
                "Use the installed Houmao email-processing skill "
                f"`{mailbox_processing_skill_name()}` for this round."
            ),
        ]
        if tool == "claude":
            lines.extend(
                [
                    f"/{mailbox_processing_skill_name()}",
                    "In Claude Code the standalone slash-skill line above invokes the installed "
                    "Houmao skill for this gateway-notified round.",
                ]
            )
        elif tool == "codex":
            lines.extend(
                [
                    f"${mailbox_processing_skill_name()} {gateway_base_url}",
                    "In Codex this Houmao skill is installed natively. The standalone line "
                    "above is the native skill trigger for this gateway-notified round.",
                ]
            )
        elif tool == "gemini":
            lines.append(
                "In Gemini this Houmao skill is installed natively. "
                f"Invoke `{mailbox_processing_skill_name()}` by name for this round."
            )
        else:
            lines.append(
                "Invoke the installed Houmao email-processing skill by name for this round."
            )
        lines.append(
            "Use the installed Houmao skills directly from the native tool skill surface. "
            "Do not inspect the current project or runtime home for skill files."
        )
        if gateway_path.is_file():
            if tool != "codex":
                lines.append(
                    "Use the lower-level Houmao mailbox communication skill "
                    f"`{mailbox_gateway_skill_name()}` by name when you need the exact "
                    "`/v1/mail/*` operation contract or no-gateway transport guidance for this round."
                )
            else:
                lines.append(
                    "If you need the exact `/v1/mail/*` operation contract or no-gateway "
                    "transport guidance for this round, use the lower-level Houmao mailbox "
                    "communication skill "
                    f"`{mailbox_gateway_skill_name()}` after the round skill expands."
                )
        return "\n".join(lines)

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
        """Poll mailbox-local open inbox work when the notifier is enabled."""

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
                self._require_live_notifier_mailbox_config_locked()
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
                read_state = "unread" if record.mode == "unread_only" else "any"
                unread_messages = _sort_unread_messages(
                    [
                        _UnreadMailboxMessage(
                            message_ref=message.message_ref,
                            thread_ref=message.thread_ref,
                            created_at_utc=message.created_at_utc,
                            sender_address=message.sender.address,
                            sender_display_name=message.sender.display_name,
                            subject=message.subject,
                        )
                        for message in adapter.list_messages(
                            box="inbox",
                            read_state=read_state,
                            answered_state="any",
                            archived=False,
                            limit=None,
                            since=None,
                            include_body=False,
                        )
                    ]
                )
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
                self._log(f"mail notifier poll error: {exc}")
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
                self._log(f"mail notifier poll: no open inbox mail mode={record.mode}")
                return

            unread_digest = self._mail_notifier_digest(unread_messages)
            block_detail = self._notifier_block_detail_locked(status=status)
            if block_detail is not None:
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
                    detail=block_detail,
                )
                self._log(block_detail)
                return

            prompt = self._build_mail_notifier_prompt(mode=record.mode)
            request_id = self._enqueue_internal_prompt(prompt=prompt)
            write_gateway_mail_notifier_record(
                self.m_paths.queue_path,
                last_poll_at_utc=poll_time_utc,
                last_notification_at_utc=poll_time_utc,
                last_notified_digest=None,
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
                f"mail notifier enqueued request_id={request_id} "
                f"open_mail_count={len(unread_messages)} mode={record.mode}"
            )

    def _mail_notifier_digest(self, unread_messages: list[_UnreadMailboxMessage]) -> str:
        """Build a stable digest for one open-mail snapshot."""

        digest_source = "\n".join(sorted(message.message_ref for message in unread_messages))
        return hashlib.sha256(digest_source.encode("utf-8")).hexdigest()

    def _build_mail_notifier_prompt(self, *, mode: GatewayMailNotifierMode) -> str:
        """Build the reminder prompt submitted through the internal notifier path."""

        mailbox = self._load_mailbox_config()
        base_url = f"http://{self.m_host}:{self.m_port}"
        rendered = _load_mail_notifier_template()
        mode_guidance = _render_mail_notifier_mode_guidance(mode)
        replacements = {
            "{{SKILL_USAGE_BLOCK}}": self._mail_notifier_skill_usage_block(mailbox=mailbox),
            "{{NOTIFIER_MODE}}": mode,
            "{{MODE_GUIDANCE}}": mode_guidance,
            "{{GATEWAY_BASE_URL}}": base_url,
            "{{FULL_ENDPOINT_URLS_BLOCK}}": _render_mail_notifier_full_endpoint_urls(base_url),
        }
        for placeholder, replacement in replacements.items():
            rendered = rendered.replace(placeholder, replacement)
        return rendered.rstrip()

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

    def _reminder_loop(self) -> None:
        """Deliver due effective reminders when the gateway becomes idle."""

        while not self.m_stop_event.is_set():
            reminder: _GatewayReminderRecord | None = None
            with self.m_reminder_condition:
                if self.m_stop_event.is_set():
                    return
                reminder = self._effective_due_reminder_locked()
                if reminder is None:
                    self.m_reminder_condition.wait(
                        timeout=self._next_reminder_wait_seconds_locked()
                    )
                    continue
                status = self._refresh_status_snapshot(
                    active_execution=self._active_execution_state()
                )
                if (
                    status.request_admission != "open"
                    or status.active_execution != "idle"
                    or status.queue_depth > 0
                ):
                    self._record_reminder_deferral_locked(reminder, status=status)
                    self.m_reminder_condition.wait(timeout=_REMINDER_BUSY_RETRY_INTERVAL_SECONDS)
                    continue

                reminder.executing = True
                reminder.last_started_at = datetime.now(UTC)
                reminder.deferred_signature = None
                self.m_active_reminder_id = reminder.reminder_id
                self._refresh_status_snapshot(active_execution="running")
                append_gateway_event(
                    self.m_paths,
                    {
                        "kind": "reminder_started",
                        "reminder_id": reminder.reminder_id,
                        "mode": reminder.mode,
                        "delivery_kind": reminder.delivery_kind,
                        "ranking": reminder.ranking,
                        "paused": reminder.paused,
                        "sequence_preview": (
                            reminder.send_keys_sequence[:120]
                            if reminder.send_keys_sequence is not None
                            else None
                        ),
                        "ensure_enter": (
                            reminder.send_keys_ensure_enter
                            if reminder.delivery_kind == "send_keys"
                            else None
                        ),
                        "started_at_utc": self._gateway_datetime_iso(reminder.last_started_at),
                        "delete_requested": reminder.delete_requested,
                    },
                )
                self._log(
                    "executing reminder "
                    f"reminder_id={reminder.reminder_id} "
                    f"ranking={reminder.ranking}"
                )

            error_detail: str | None = None
            assert reminder is not None
            try:
                if reminder.delivery_kind == "prompt":
                    assert reminder.prompt is not None
                    self._submit_prompt_via_adapter(
                        prompt=reminder.prompt,
                        turn_id=None,
                        session_selection=None,
                        execution_model=None,
                        note_prompt_submission=False,
                    )
                else:
                    assert reminder.send_keys_sequence is not None
                    self.m_adapter.send_control_input(
                        sequence=self._normalize_reminder_send_keys_sequence(
                            sequence=reminder.send_keys_sequence,
                            ensure_enter=reminder.send_keys_ensure_enter,
                        ),
                        escape_special_keys=False,
                    )
            except (GatewayError, CaoApiError, ValidationError) as exc:
                error_detail = str(exc)
            self._finish_reminder_execution(
                reminder_id=reminder.reminder_id,
                error_detail=error_detail,
            )

    def _effective_due_reminder_locked(self) -> _GatewayReminderRecord | None:
        """Return the effective reminder when it is eligible to dispatch."""

        reminder = self._effective_reminder_locked()
        if reminder is None:
            return None
        if reminder.executing or reminder.delete_requested or reminder.paused:
            return None
        if reminder.next_due_at > datetime.now(UTC):
            return None
        return reminder

    def _next_reminder_wait_seconds_locked(self) -> float | None:
        """Return the next condition-wait timeout for the reminder scheduler."""

        reminder = self._effective_reminder_locked()
        if reminder is None or reminder.executing:
            return None
        now = datetime.now(UTC)
        if reminder.next_due_at <= now:
            if reminder.paused:
                return None
            return 0.0
        return max(0.0, (reminder.next_due_at - now).total_seconds())

    def _record_reminder_deferral_locked(
        self,
        reminder: _GatewayReminderRecord,
        *,
        status: GatewayStatusV1,
    ) -> None:
        """Emit one deferral record when the effective reminder cannot execute yet."""

        signature = f"{status.request_admission}:{status.active_execution}:{status.queue_depth}"
        if reminder.deferred_signature == signature:
            return
        reminder.deferred_signature = signature
        detail = (
            "effective reminder deferred because the gateway is busy "
            f"(admission={status.request_admission}, "
            f"active_execution={status.active_execution}, "
            f"queue_depth={status.queue_depth})"
        )
        append_gateway_event(
            self.m_paths,
            {
                "kind": "reminder_deferred",
                "reminder_id": reminder.reminder_id,
                "mode": reminder.mode,
                "delivery_kind": reminder.delivery_kind,
                "ranking": reminder.ranking,
                "detail": detail,
                "next_due_at_utc": self._gateway_datetime_iso(reminder.next_due_at),
            },
        )
        self._log_rate_limited(f"reminder_deferred:{reminder.reminder_id}", detail)

    def _finish_reminder_execution(
        self,
        *,
        reminder_id: str,
        error_detail: str | None,
    ) -> None:
        """Finalize one reminder execution attempt and reschedule if needed."""

        with self.m_reminder_condition:
            finished_at = datetime.now(UTC)
            reminder = self.m_reminders.get(reminder_id)
            next_due_at_utc: str | None = None
            if reminder is not None:
                reminder.executing = False
                reminder.deferred_signature = None
                if (
                    reminder.mode == "repeat"
                    and reminder.interval_seconds is not None
                    and not reminder.delete_requested
                ):
                    reminder.next_due_at = self._next_repeat_due_at(
                        anchor_due_at=reminder.anchor_due_at,
                        interval_seconds=reminder.interval_seconds,
                        reference_time=finished_at,
                    )
                    next_due_at_utc = self._gateway_datetime_iso(reminder.next_due_at)
                else:
                    del self.m_reminders[reminder_id]
            if self.m_active_reminder_id == reminder_id:
                self.m_active_reminder_id = None

            if error_detail is None:
                append_gateway_event(
                    self.m_paths,
                    {
                        "kind": "reminder_completed",
                        "reminder_id": reminder_id,
                        "finished_at_utc": self._gateway_datetime_iso(finished_at),
                        "next_due_at_utc": next_due_at_utc,
                    },
                )
                if next_due_at_utc is None:
                    self._log(f"completed reminder reminder_id={reminder_id}")
                else:
                    self._log(
                        "completed reminder "
                        f"reminder_id={reminder_id} "
                        f"next_due_at_utc={next_due_at_utc}"
                    )
            else:
                append_gateway_event(
                    self.m_paths,
                    {
                        "kind": "reminder_failed",
                        "reminder_id": reminder_id,
                        "error_detail": error_detail,
                        "finished_at_utc": self._gateway_datetime_iso(finished_at),
                        "next_due_at_utc": next_due_at_utc,
                    },
                )
                if next_due_at_utc is None:
                    self._log(f"failed reminder reminder_id={reminder_id} detail={error_detail}")
                else:
                    self._log(
                        "failed reminder "
                        f"reminder_id={reminder_id} "
                        f"detail={error_detail} "
                        f"next_due_at_utc={next_due_at_utc}"
                    )
            self._refresh_status_snapshot(active_execution=self._active_execution_state())
            self.m_reminder_condition.notify_all()

    def _next_repeat_due_at(
        self,
        *,
        anchor_due_at: datetime,
        interval_seconds: float,
        reference_time: datetime,
    ) -> datetime:
        """Return the next anchored repeat boundary strictly after the reference time."""

        elapsed_seconds = max(0.0, (reference_time - anchor_due_at).total_seconds())
        interval_steps = max(1, math.floor(elapsed_seconds / interval_seconds) + 1)
        return anchor_due_at + timedelta(seconds=interval_seconds * interval_steps)

    def _submit_prompt_via_adapter(
        self,
        *,
        prompt: str,
        turn_id: str | None,
        session_selection: HeadlessTurnSessionSelection | None,
        execution_model: ModelConfig | None,
        note_prompt_submission: bool,
    ) -> None:
        """Submit one prompt through the shared gateway execution adapter."""

        self.m_adapter.submit_prompt(
            prompt=prompt,
            turn_id=turn_id,
            session_selection=session_selection,
            execution_model=execution_model,
        )
        if note_prompt_submission and self.m_tui_tracking is not None:
            self.m_tui_tracking.note_prompt_submission(message=prompt)

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
                session_selection: HeadlessTurnSessionSelection | None = None
                execution_model = (
                    payload.execution.to_model_config() if payload.execution is not None else None
                )
                with self.m_lock:
                    dispatch_mode = self._prompt_dispatch_mode_locked(forced=False)
                    execution_rejection = self._execution_override_rejection_detail(
                        dispatch_mode=dispatch_mode,
                        request_execution=payload.execution,
                    )
                    if execution_rejection is not None:
                        raise GatewayError(execution_rejection)
                    if payload.chat_session is not None:
                        if dispatch_mode not in {"local_headless", "server_headless"}:
                            raise GatewayError(
                                "Queued prompt chat_session selection is only supported for "
                                "headless gateway targets."
                            )
                        try:
                            session_selection, _ = self._resolve_headless_prompt_selection_locked(
                                request_chat_session=payload.chat_session,
                                allow_next_prompt_override=False,
                                forced=False,
                            )
                        except HTTPException as exc:
                            raise GatewayError(str(exc.detail)) from exc
                self._submit_prompt_via_adapter(
                    prompt=payload.prompt,
                    turn_id=payload.turn_id,
                    session_selection=session_selection,
                    execution_model=execution_model,
                    note_prompt_submission=request_kind == "submit_prompt",
                )
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
            self.m_reminder_condition.notify_all()

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
                execution_mode=self.m_execution_mode,
                tmux_window_id=self.m_tmux_window_id,
                tmux_window_index=self.m_tmux_window_index,
                tmux_pane_id=self.m_tmux_pane_id,
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
            execution_mode=self.m_execution_mode,
            queue_depth=queue_depth_from_sqlite(self.m_paths.queue_path),
            gateway_host=self.m_host,
            gateway_port=self.m_port,
            gateway_tmux_window_id=self.m_tmux_window_id,
            gateway_tmux_window_index=self.m_tmux_window_index,
            gateway_tmux_pane_id=self.m_tmux_pane_id,
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
                execution_mode=self.m_execution_mode,
                tmux_window_id=self.m_tmux_window_id,
                tmux_window_index=self.m_tmux_window_index,
                tmux_pane_id=self.m_tmux_pane_id,
                managed_agent_instance_epoch=self.m_current_epoch,
                managed_agent_instance_id=self.m_current_instance_id,
            ),
        )
        return status

    def _active_execution_state(self) -> GatewayExecutionState:
        """Return whether a queue item is currently running."""

        direct_prompt_thread = self.m_direct_prompt_thread
        if direct_prompt_thread is not None and direct_prompt_thread.is_alive():
            return "running"
        if self.m_active_reminder_id is not None:
            return "running"
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

    def _active_headless_turn_id_locked(self) -> str | None:
        """Return the current headless turn id from queued or running prompt work."""

        direct_prompt_thread = self.m_direct_prompt_thread
        if (
            direct_prompt_thread is not None
            and direct_prompt_thread.is_alive()
            and self.m_direct_prompt_turn_id is not None
        ):
            return self.m_direct_prompt_turn_id
        with sqlite3.connect(self.m_paths.queue_path) as connection:
            rows = connection.execute(
                """
                SELECT payload_json
                FROM gateway_requests
                WHERE request_kind = 'submit_prompt'
                  AND state IN ('accepted', 'running')
                ORDER BY accepted_at_utc ASC
                """
            ).fetchall()
        for row in rows:
            try:
                payload = GatewayRequestPayloadSubmitPromptV1.model_validate_json(str(row[0]))
            except ValidationError:
                continue
            if payload.turn_id is not None:
                return payload.turn_id
        return None

    def _start_tui_tracking_locked(self) -> None:
        """Start gateway-owned TUI tracking when the attach target is TUI-backed."""

        if self.m_tui_tracking is not None:
            return
        identity = self._tui_tracking_identity_locked()
        if identity is None:
            return
        tracking = SingleSessionTrackingRuntime(
            identity=identity,
            watch_poll_interval_seconds=self.m_tui_tracking_timings.watch_poll_interval_seconds,
            stability_threshold_seconds=self.m_tui_tracking_timings.stability_threshold_seconds,
            completion_stability_seconds=(self.m_tui_tracking_timings.completion_stability_seconds),
            unknown_to_stalled_timeout_seconds=(
                self.m_tui_tracking_timings.unknown_to_stalled_timeout_seconds
            ),
            stale_active_recovery_seconds=self.m_tui_tracking_timings.stale_active_recovery_seconds,
            final_stable_active_recovery_seconds=(
                self.m_tui_tracking_timings.final_stable_active_recovery_seconds
            ),
        )
        tracking.start()
        self.m_tui_tracking = tracking

    def _require_tui_tracking_locked(self) -> SingleSessionTrackingRuntime:
        """Require gateway-owned TUI tracking for the attached session."""

        if self.m_tui_tracking is None:
            raise HTTPException(
                status_code=422,
                detail="Gateway TUI live-state routes are only available for attached TUI backends.",
            )
        return self.m_tui_tracking

    def _tui_tracking_identity_locked(self) -> HoumaoTrackedSessionIdentity | None:
        """Build the tracked-session identity for gateway-owned TUI tracking."""

        metadata = self.m_attach_contract.backend_metadata
        tracked_session_id: str
        session_name: str
        tmux_window_name: str | None
        terminal_aliases: list[str]
        tool = "codex"
        if isinstance(metadata, GatewayAttachBackendMetadataCaoV1):
            if self.m_attach_contract.backend != "cao_rest":
                return None
            tracked_session_id = self.m_attach_contract.attach_identity
            session_name = self.m_attach_contract.attach_identity
            tmux_window_name = metadata.tmux_window_name
            terminal_aliases = [metadata.terminal_id]
        elif isinstance(metadata, GatewayAttachBackendMetadataHoumaoServerV1):
            if self.m_attach_contract.backend != "houmao_server_rest":
                return None
            tracked_session_id = metadata.session_name
            session_name = metadata.session_name
            tmux_window_name = metadata.tmux_window_name
            terminal_aliases = [metadata.terminal_id]
        elif isinstance(metadata, GatewayAttachBackendMetadataHeadlessV1):
            if self.m_attach_contract.backend != "local_interactive":
                return None
            tracked_session_id = (
                self.m_attach_contract.runtime_session_id or self.m_attach_contract.attach_identity
            )
            session_name = tracked_session_id
            tmux_window_name = HEADLESS_AGENT_WINDOW_NAME
            terminal_aliases = []
            tool = metadata.tool
        else:
            return None

        observed_tool_version: str | None = None
        agent_name: str | None = None
        agent_id: str | None = None
        manifest_path_value = self.m_attach_contract.manifest_path
        if manifest_path_value is not None:
            try:
                handle = load_session_manifest(Path(manifest_path_value))
                payload = parse_session_manifest_payload(handle.payload, source=str(handle.path))
            except SessionManifestError:
                payload = None
            if payload is not None:
                tool = payload.tool
                observed_tool_version = (
                    payload.launch_policy_provenance.detected_tool_version
                    if payload.launch_policy_provenance is not None
                    else None
                )
                agent_name = payload.agent_name
                agent_id = payload.agent_id

        return HoumaoTrackedSessionIdentity(
            tracked_session_id=tracked_session_id,
            session_name=session_name,
            tool=tool,
            observed_tool_version=observed_tool_version,
            tmux_session_name=self.m_attach_contract.tmux_session_name,
            tmux_window_name=tmux_window_name,
            terminal_aliases=terminal_aliases,
            agent_name=agent_name,
            agent_id=agent_id,
            manifest_path=self.m_attach_contract.manifest_path,
            session_root=str(self.m_paths.session_root.resolve()),
        )

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

    def _memory_call(callback: Callable[[], _MemoryResponseT]) -> _MemoryResponseT:
        """Translate memory service failures into HTTP status codes."""

        try:
            return callback()
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except OSError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/v1/memory", response_model=GatewayMemorySummaryV1)
    def _memory() -> GatewayMemorySummaryV1:
        """Serve the managed memory summary."""

        return _memory_call(runtime.memory)

    @app.get("/v1/memory/memo", response_model=GatewayMemoryMemoResponseV1)
    def _memory_memo() -> GatewayMemoryMemoResponseV1:
        """Serve the fixed managed memory memo."""

        return _memory_call(runtime.read_memory_memo)

    @app.put("/v1/memory/memo", response_model=GatewayMemoryMemoResponseV1)
    def _memory_memo_put(
        request_payload: GatewayMemoryMemoWriteRequestV1,
    ) -> GatewayMemoryMemoResponseV1:
        """Replace the fixed managed memory memo."""

        return _memory_call(lambda: runtime.write_memory_memo(request_payload))

    @app.post("/v1/memory/memo/append", response_model=GatewayMemoryMemoResponseV1)
    def _memory_memo_append(
        request_payload: GatewayMemoryMemoWriteRequestV1,
    ) -> GatewayMemoryMemoResponseV1:
        """Append to the fixed managed memory memo."""

        return _memory_call(lambda: runtime.write_memory_memo(request_payload, append=True))

    @app.post("/v1/memory/pages/tree", response_model=GatewayMemoryPageTreeResponseV1)
    def _memory_pages_tree(
        request_payload: GatewayMemoryPageTreeRequestV1,
    ) -> GatewayMemoryPageTreeResponseV1:
        """Serve a pages-directory tree listing."""

        return _memory_call(lambda: runtime.list_memory_pages(request_payload))

    @app.post("/v1/memory/pages/resolve", response_model=GatewayMemoryPagePathResolutionV1)
    def _memory_page_resolve(
        request_payload: GatewayMemoryPagePathRequestV1,
    ) -> GatewayMemoryPagePathResolutionV1:
        """Resolve one contained memory page path."""

        return _memory_call(lambda: runtime.resolve_memory_page_path(request_payload))

    @app.post("/v1/memory/pages/read", response_model=GatewayMemoryPageResponseV1)
    def _memory_page_read(
        request_payload: GatewayMemoryPagePathRequestV1,
    ) -> GatewayMemoryPageResponseV1:
        """Read one contained memory page."""

        return _memory_call(lambda: runtime.read_memory_page(request_payload))

    @app.post("/v1/memory/pages/write", response_model=GatewayMemoryActionResponseV1)
    def _memory_page_write(
        request_payload: GatewayMemoryPageWriteRequestV1,
    ) -> GatewayMemoryActionResponseV1:
        """Write one contained memory page."""

        return _memory_call(lambda: runtime.write_memory_page(request_payload))

    @app.post("/v1/memory/pages/append", response_model=GatewayMemoryActionResponseV1)
    def _memory_page_append(
        request_payload: GatewayMemoryPageWriteRequestV1,
    ) -> GatewayMemoryActionResponseV1:
        """Append to one contained memory page."""

        return _memory_call(lambda: runtime.write_memory_page(request_payload, append=True))

    @app.post("/v1/memory/pages/delete", response_model=GatewayMemoryActionResponseV1)
    def _memory_page_delete(
        request_payload: GatewayMemoryPagePathRequestV1,
    ) -> GatewayMemoryActionResponseV1:
        """Delete one contained memory page path."""

        return _memory_call(lambda: runtime.delete_memory_page(request_payload))

    @app.get("/v1/control/tui/state", response_model=HoumaoTerminalStateResponse)
    def _tui_state() -> HoumaoTerminalStateResponse:
        """Serve gateway-owned tracked TUI state."""

        return runtime.get_tui_state()

    @app.get("/v1/control/tui/history", response_model=HoumaoTerminalSnapshotHistoryResponse)
    def _tui_history(limit: int = 100) -> HoumaoTerminalSnapshotHistoryResponse:
        """Serve gateway-owned tracked TUI snapshot history."""

        return runtime.get_tui_history(limit=limit)

    @app.post("/v1/control/tui/note-prompt", response_model=HoumaoTerminalStateResponse)
    def _note_tui_prompt(
        request_payload: GatewayRequestPayloadSubmitPromptV1,
    ) -> HoumaoTerminalStateResponse:
        """Record explicit-input evidence in the gateway-owned tracker."""

        return runtime.note_tui_prompt_submission(prompt=request_payload.prompt)

    @app.post("/v1/control/send-keys", response_model=GatewayControlInputResultV1)
    def _send_control_input(
        request_payload: GatewayControlInputRequestV1,
    ) -> GatewayControlInputResultV1:
        """Deliver raw control input through the dedicated non-queued surface."""

        return runtime.send_control_input(request_payload)

    @app.post("/v1/control/prompt", response_model=GatewayPromptControlResultV1)
    def _control_prompt(
        request_payload: GatewayPromptControlRequestV1,
    ) -> GatewayPromptControlResultV1:
        """Deliver one readiness-gated prompt through the dedicated direct-control surface."""

        return runtime.control_prompt(request_payload)

    @app.get("/v1/control/headless/state", response_model=GatewayHeadlessControlStateV1)
    def _headless_state() -> GatewayHeadlessControlStateV1:
        """Serve read-optimized live headless control posture."""

        return runtime.get_headless_control_state()

    @app.post(
        "/v1/control/headless/next-prompt-session",
        response_model=GatewayHeadlessControlStateV1,
    )
    def _headless_next_prompt_session(
        request_payload: GatewayHeadlessNextPromptSessionRequestV1,
    ) -> GatewayHeadlessControlStateV1:
        """Store one one-shot override for the next accepted auto headless prompt."""

        return runtime.set_headless_next_prompt_session(request_payload)

    @app.post("/v1/requests", response_model=GatewayAcceptedRequestV1)
    def _create_request(request_payload: GatewayRequestCreateV1) -> GatewayAcceptedRequestV1:
        """Accept one gateway-managed request."""

        return runtime.create_request(request_payload)

    @app.post("/v1/reminders", response_model=GatewayReminderCreateResultV1)
    def _create_reminders(
        request_payload: GatewayReminderCreateBatchV1,
    ) -> GatewayReminderCreateResultV1:
        """Register one or more gateway-owned in-memory reminders."""

        return runtime.create_reminders(request_payload)

    @app.get("/v1/reminders", response_model=GatewayReminderListV1)
    def _list_reminders() -> GatewayReminderListV1:
        """Serve live reminder inspection state."""

        return runtime.list_reminders()

    @app.get("/v1/reminders/{reminder_id}", response_model=GatewayReminderV1)
    def _get_reminder(reminder_id: str) -> GatewayReminderV1:
        """Serve one reminder by identifier."""

        return runtime.get_reminder(reminder_id=reminder_id)

    @app.put("/v1/reminders/{reminder_id}", response_model=GatewayReminderV1)
    def _put_reminder(
        reminder_id: str,
        request_payload: GatewayReminderPutV1,
    ) -> GatewayReminderV1:
        """Update one live reminder by identifier."""

        return runtime.put_reminder(reminder_id=reminder_id, request_payload=request_payload)

    @app.delete("/v1/reminders/{reminder_id}", response_model=GatewayReminderDeleteResultV1)
    def _delete_reminder(reminder_id: str) -> GatewayReminderDeleteResultV1:
        """Delete one reminder or future reminder repetitions."""

        return runtime.delete_reminder(reminder_id=reminder_id)

    @app.get("/v1/mail/status", response_model=GatewayMailStatusV1)
    def _mail_status() -> GatewayMailStatusV1:
        """Serve shared mailbox availability for the attached session."""

        return runtime.get_mail_status()

    @app.post("/v1/mail/list", response_model=GatewayMailListResponseV1)
    def _mail_list(request_payload: GatewayMailListRequestV1) -> GatewayMailListResponseV1:
        """Run one shared mailbox list request."""

        return runtime.list_mail(request_payload)

    @app.post("/v1/mail/peek", response_model=GatewayMailMessageResponseV1)
    def _mail_peek(request_payload: GatewayMailMessageRequestV1) -> GatewayMailMessageResponseV1:
        """Run one shared mailbox peek request."""

        return runtime.peek_mail(request_payload)

    @app.post("/v1/mail/read", response_model=GatewayMailMessageResponseV1)
    def _mail_read(request_payload: GatewayMailMessageRequestV1) -> GatewayMailMessageResponseV1:
        """Run one shared mailbox read request."""

        return runtime.read_mail(request_payload)

    @app.post("/v1/mail/send", response_model=GatewayMailActionResponseV1)
    def _mail_send(request_payload: GatewayMailSendRequestV1) -> GatewayMailActionResponseV1:
        """Run one shared mailbox send request."""

        return runtime.send_mail(request_payload)

    @app.post("/v1/mail/post", response_model=GatewayMailActionResponseV1)
    def _mail_post(request_payload: GatewayMailPostRequestV1) -> GatewayMailActionResponseV1:
        """Run one shared mailbox operator-origin post request."""

        return runtime.post_mail(request_payload)

    @app.post("/v1/mail/reply", response_model=GatewayMailActionResponseV1)
    def _mail_reply(request_payload: GatewayMailReplyRequestV1) -> GatewayMailActionResponseV1:
        """Run one shared mailbox reply request."""

        return runtime.reply_mail(request_payload)

    @app.post("/v1/mail/mark", response_model=GatewayMailLifecycleResponseV1)
    def _mail_mark(request_payload: GatewayMailMarkRequestV1) -> GatewayMailLifecycleResponseV1:
        """Run one shared mailbox mark request."""

        return runtime.mark_mail(request_payload)

    @app.post("/v1/mail/move", response_model=GatewayMailLifecycleResponseV1)
    def _mail_move(request_payload: GatewayMailMoveRequestV1) -> GatewayMailLifecycleResponseV1:
        """Run one shared mailbox move request."""

        return runtime.move_mail(request_payload)

    @app.post("/v1/mail/archive", response_model=GatewayMailLifecycleResponseV1)
    def _mail_archive(
        request_payload: GatewayMailArchiveRequestV1,
    ) -> GatewayMailLifecycleResponseV1:
        """Run one shared mailbox archive request."""

        return runtime.archive_mail(request_payload)

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


def _positive_tui_timing_arg(value: str) -> float:
    """Parse one positive gateway TUI tracking timing CLI value."""

    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be numeric") from exc
    if not math.isfinite(parsed) or parsed <= 0:
        raise argparse.ArgumentTypeError("must be > 0")
    return parsed


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
    parser.add_argument("--tui-watch-poll-interval-seconds", type=_positive_tui_timing_arg)
    parser.add_argument("--tui-stability-threshold-seconds", type=_positive_tui_timing_arg)
    parser.add_argument("--tui-completion-stability-seconds", type=_positive_tui_timing_arg)
    parser.add_argument("--tui-unknown-to-stalled-timeout-seconds", type=_positive_tui_timing_arg)
    parser.add_argument("--tui-stale-active-recovery-seconds", type=_positive_tui_timing_arg)
    parser.add_argument(
        "--tui-final-stable-active-recovery-seconds",
        type=_positive_tui_timing_arg,
    )
    args = parser.parse_args(argv)

    gateway_root = Path(args.gateway_root).resolve()
    tui_tracking_timings = GatewayTuiTrackingTimingOverridesV1(
        watch_poll_interval_seconds=args.tui_watch_poll_interval_seconds,
        stability_threshold_seconds=args.tui_stability_threshold_seconds,
        completion_stability_seconds=args.tui_completion_stability_seconds,
        unknown_to_stalled_timeout_seconds=args.tui_unknown_to_stalled_timeout_seconds,
        stale_active_recovery_seconds=args.tui_stale_active_recovery_seconds,
        final_stable_active_recovery_seconds=args.tui_final_stable_active_recovery_seconds,
    )
    runtime = GatewayServiceRuntime.from_gateway_root(
        gateway_root=gateway_root,
        host=args.host,
        port=int(args.port),
        tui_tracking_timings=tui_tracking_timings,
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
