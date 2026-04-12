"""Pydantic models for `houmao-server` contracts.

This module defines the public API payloads exposed by the server-owned live
TUI tracker, alongside the registration request/response models used by the
runtime bridge.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from houmao.agents.mailbox_runtime_models import MailboxTransport
from houmao.agents.realm_controller.gateway_models import (
    GatewayAcceptedRequestV1,
    GatewayAdmissionState,
    GatewayChatSessionSelectorV1,
    GatewayConnectivityState,
    GatewayCurrentExecutionMode,
    GatewayExecutionOverrideV1,
    GatewayExecutionState,
    GatewayHeadlessChatSessionStateV1,
    GatewayHeadlessControlStateV1,
    GatewayHeadlessNextPromptSessionRequestV1,
    GatewayHealthState,
    GatewayHost,
    GatewayMailActionResponseV1,
    GatewayMailCheckRequestV1,
    GatewayMailCheckResponseV1,
    GatewayMailPostRequestV1,
    GatewayMailReplyRequestV1,
    GatewayMailSendRequestV1,
    GatewayMailStateRequestV1,
    GatewayMailStateResponseV1,
    GatewayMailStatusV1,
    GatewayPromptControlRequestV1,
    GatewayPromptControlResultV1,
    GatewayRecoveryState,
    GatewayRequestCreateV1,
)
from houmao.cao.models import CaoHealthResponse, CaoSuccessResponse
from houmao.shared_tui_tracking.models import (
    CompletionState,
    ParseStatus,
    ProcessState,
    ReadinessState,
    TrackedDiagnosticsAvailability,
    TrackedLastTurnResult,
    TrackedLastTurnSource,
    Tristate,
    TransportState,
    TurnPhase as ManagedAgentTurnPhase,
)

TerminalId = Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{8}$")]
ManagedAgentTransportKind = Literal["tui", "headless"]
ManagedAgentAvailability = Literal["available", "unavailable", "error"]
ManagedAgentLastTurnResult = Literal["success", "interrupted", "known_failure", "none", "unknown"]
ManagedAgentTurnStatus = Literal["active", "completed", "failed", "interrupted", "unknown"]
ManagedAgentRequestKind = Literal["submit_prompt", "interrupt"]
ManagedAgentRequestDisposition = Literal["accepted", "no_op"]
OperatorStatus = Literal[
    "ready",
    "processing",
    "waiting_user_answer",
    "completed",
    "tui_down",
    "unavailable",
    "error",
    "unknown",
]
CompletionAuthority = Literal["turn_anchored", "unanchored_background"]
TurnAnchorState = Literal["active", "absent", "lost"]

__all__ = (
    "CompletionState",
    "ParseStatus",
    "ProcessState",
    "ReadinessState",
    "TrackedDiagnosticsAvailability",
    "TransportState",
)


class _HoumaoModel(BaseModel):
    """Shared strict base model for Houmao payloads."""

    model_config = ConfigDict(extra="forbid", strict=True)


class ChildCaoStatus(_HoumaoModel):
    """Child-CAO health and lifecycle metadata."""

    api_base_url: str
    healthy: bool
    health_status: str | None = None
    service: str | None = None
    error: str | None = None
    derived_port: int
    ownership_file: str | None = None


class HoumaoHealthResponse(CaoHealthResponse):
    """Compatibility-safe health payload with Houmao extensions."""

    houmao_service: Literal["houmao-server"] = "houmao-server"
    child_cao: ChildCaoStatus | None = None


class HoumaoCurrentInstance(_HoumaoModel):
    """Current live server instance metadata."""

    schema_version: int = 1
    status: Literal["ok"] = "ok"
    pid: int
    api_base_url: str
    server_root: str
    started_at_utc: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds")
    )
    child_cao: ChildCaoStatus | None = None


class WorkingDirectoryResponse(_HoumaoModel):
    """Response for `GET /terminals/{terminal_id}/working-directory`."""

    working_directory: str | None = None


class HoumaoErrorDetail(_HoumaoModel):
    """Structured probe or parse failure detail."""

    kind: str
    message: str
    details: dict[str, str] = Field(default_factory=dict)

    @field_validator("kind", "message")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        """Require non-empty string fields."""

        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped


class HoumaoTrackedSessionIdentity(_HoumaoModel):
    """Tracked-session identity owned by `houmao-server`."""

    tracked_session_id: str
    session_name: str
    tool: str
    observed_tool_version: str | None = None
    tmux_session_name: str
    tmux_window_name: str | None = None
    terminal_aliases: list[str] = Field(default_factory=list)
    agent_name: str | None = None
    agent_id: str | None = None
    manifest_path: str | None = None
    session_root: str | None = None

    @field_validator(
        "tracked_session_id",
        "session_name",
        "tool",
        "observed_tool_version",
        "tmux_session_name",
        "tmux_window_name",
        "agent_name",
        "agent_id",
        "manifest_path",
        "session_root",
    )
    @classmethod
    def _optional_not_blank(cls, value: str | None) -> str | None:
        """Require optional string fields to be non-empty when present."""

        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped


class HoumaoProbeSnapshot(_HoumaoModel):
    """Latest direct tmux/process probe snapshot."""

    observed_at_utc: str
    pane_id: str | None = None
    pane_pid: int | None = None
    captured_text_hash: str | None = None
    captured_text_length: int = 0
    captured_text_excerpt: str = ""
    matched_process_names: list[str] = Field(default_factory=list)


class HoumaoParsedSurface(_HoumaoModel):
    """Latest parsed supported-TUI surface."""

    parser_family: str
    parser_preset_id: str | None = None
    parser_preset_version: str | None = None
    availability: str
    business_state: str
    input_mode: str
    ui_context: str
    normalized_projection_text: str
    dialog_text: str
    dialog_head: str
    dialog_tail: str
    anomaly_codes: list[str] = Field(default_factory=list)
    baseline_invalidated: bool = False
    operator_blocked_excerpt: str | None = None

    @field_validator(
        "parser_family",
        "availability",
        "business_state",
        "input_mode",
        "ui_context",
        "normalized_projection_text",
        "dialog_text",
        "dialog_head",
        "dialog_tail",
        "parser_preset_id",
        "parser_preset_version",
        "operator_blocked_excerpt",
    )
    @classmethod
    def _allow_blank_projection_fields(cls, value: str | None) -> str | None:
        """Normalize optional string fields without forbidding empty projections."""

        if value is None:
            return None
        return value


class HoumaoOperatorState(_HoumaoModel):
    """Derived operator-facing live state."""

    status: OperatorStatus
    readiness_state: ReadinessState
    completion_state: CompletionState
    detail: str
    projection_changed: bool = False
    updated_at_utc: str


class HoumaoLifecycleTimingMetadata(_HoumaoModel):
    """Lifecycle timing metadata for server-owned unknown and completion windows."""

    readiness_unknown_elapsed_seconds: float | None = None
    completion_unknown_elapsed_seconds: float | None = None
    completion_candidate_elapsed_seconds: float | None = None
    unknown_to_stalled_timeout_seconds: float
    completion_stability_seconds: float
    stale_active_recovery_seconds: float


class HoumaoLifecycleAuthorityMetadata(_HoumaoModel):
    """Structured lifecycle-authority metadata for tracked-state consumers."""

    completion_authority: CompletionAuthority
    turn_anchor_state: TurnAnchorState
    completion_monitoring_armed: bool
    detail: str
    anchor_armed_at_utc: str | None = None
    anchor_lost_at_utc: str | None = None
    anchor_loss_reason: str | None = None


class HoumaoStabilityMetadata(_HoumaoModel):
    """Stability timing for the current visible live-state signature."""

    signature: str
    stable: bool
    stable_for_seconds: float
    stable_since_utc: str


class HoumaoRecentTransition(_HoumaoModel):
    """One bounded recent live-state transition."""

    recorded_at_utc: str
    summary: str
    changed_fields: list[str] = Field(default_factory=list)
    diagnostics_availability: TrackedDiagnosticsAvailability
    turn_phase: ManagedAgentTurnPhase
    last_turn_result: TrackedLastTurnResult
    last_turn_source: TrackedLastTurnSource
    transport_state: TransportState
    process_state: ProcessState
    parse_status: ParseStatus
    operator_status: OperatorStatus | None = Field(default=None, exclude=True)


class HoumaoTrackedDiagnostics(_HoumaoModel):
    """Low-level diagnostics for one tracked-state sample."""

    availability: TrackedDiagnosticsAvailability
    transport_state: TransportState
    process_state: ProcessState
    parse_status: ParseStatus
    probe_error: HoumaoErrorDetail | None = None
    parse_error: HoumaoErrorDetail | None = None


class HoumaoTrackedSurface(_HoumaoModel):
    """Foundational surface observables for one tracked-state sample."""

    accepting_input: Tristate
    editing_input: Tristate
    ready_posture: Tristate


class HoumaoTrackedTurn(_HoumaoModel):
    """Current public turn posture for one tracked terminal."""

    phase: ManagedAgentTurnPhase


class HoumaoTrackedLastTurn(_HoumaoModel):
    """Most recent public terminal outcome for one tracked terminal."""

    result: TrackedLastTurnResult
    source: TrackedLastTurnSource
    updated_at_utc: str | None = None


class HoumaoTerminalStateResponse(_HoumaoModel):
    """Houmao extension route for live tracked terminal state."""

    terminal_id: str
    tracked_session: HoumaoTrackedSessionIdentity
    diagnostics: HoumaoTrackedDiagnostics
    probe_snapshot: HoumaoProbeSnapshot | None = None
    parsed_surface: HoumaoParsedSurface | None = None
    surface: HoumaoTrackedSurface
    turn: HoumaoTrackedTurn
    last_turn: HoumaoTrackedLastTurn
    stability: HoumaoStabilityMetadata
    recent_transitions: list[HoumaoRecentTransition] = Field(default_factory=list)
    transport_state: TransportState = Field(default="tmux_missing", exclude=True)
    process_state: ProcessState = Field(default="unknown", exclude=True)
    parse_status: ParseStatus = Field(default="transport_unavailable", exclude=True)
    probe_error: HoumaoErrorDetail | None = Field(default=None, exclude=True)
    parse_error: HoumaoErrorDetail | None = Field(default=None, exclude=True)
    operator_state: HoumaoOperatorState | None = Field(default=None, exclude=True)
    lifecycle_timing: HoumaoLifecycleTimingMetadata | None = Field(default=None, exclude=True)
    lifecycle_authority: HoumaoLifecycleAuthorityMetadata | None = Field(default=None, exclude=True)


class HoumaoTerminalHistoryResponse(_HoumaoModel):
    """Houmao extension route for bounded in-memory recent history."""

    terminal_id: str
    tracked_session_id: str
    entries: list[HoumaoRecentTransition]


class HoumaoTerminalSnapshotHistoryEntry(_HoumaoModel):
    """One bounded recent tracked TUI snapshot."""

    recorded_at_utc: str
    diagnostics: HoumaoTrackedDiagnostics
    probe_snapshot: HoumaoProbeSnapshot | None = None
    parsed_surface: HoumaoParsedSurface | None = None
    surface: HoumaoTrackedSurface
    turn: HoumaoTrackedTurn
    last_turn: HoumaoTrackedLastTurn
    stability: HoumaoStabilityMetadata

    @field_validator("recorded_at_utc")
    @classmethod
    def _recorded_at_not_blank(cls, value: str) -> str:
        """Require a non-empty snapshot timestamp."""

        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped


class HoumaoTerminalSnapshotHistoryResponse(_HoumaoModel):
    """Houmao extension route for bounded in-memory tracked snapshot history."""

    terminal_id: str
    tracked_session_id: str
    entries: list[HoumaoTerminalSnapshotHistoryEntry] = Field(default_factory=list)

    @field_validator("terminal_id", "tracked_session_id")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        """Require non-empty tracked snapshot history identifiers."""

        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped


class HoumaoRegisterLaunchRequest(_HoumaoModel):
    """Registration request for delegated CLI launches."""

    session_name: str
    terminal_id: str | None = None
    tool: str
    observed_tool_version: str | None = None
    manifest_path: str | None = None
    session_root: str | None = None
    agent_name: str | None = None
    agent_id: str | None = None
    tmux_session_name: str | None = None
    tmux_window_name: str | None = None

    @field_validator(
        "session_name",
        "tool",
        "terminal_id",
        "observed_tool_version",
        "manifest_path",
        "session_root",
        "agent_name",
        "agent_id",
        "tmux_session_name",
        "tmux_window_name",
    )
    @classmethod
    def _optional_not_blank(cls, value: str | None) -> str | None:
        """Require optional string inputs to be non-empty when present."""

        if value is None:
            return None
        if not value.strip():
            raise ValueError("must not be empty")
        return value


class HoumaoRegisterLaunchResponse(CaoSuccessResponse):
    """Registration response for delegated CLI launches."""

    session_name: str
    terminal_id: str


class HoumaoManagedAgentIdentity(_HoumaoModel):
    """Transport-neutral managed-agent identity."""

    tracked_agent_id: str
    transport: ManagedAgentTransportKind
    tool: str
    session_name: str | None = None
    terminal_id: str | None = None
    runtime_session_id: str | None = None
    tmux_session_name: str | None = None
    tmux_window_name: str | None = None
    manifest_path: str | None = None
    session_root: str | None = None
    agent_name: str | None = None
    agent_id: str | None = None

    @field_validator(
        "tracked_agent_id",
        "tool",
        "session_name",
        "terminal_id",
        "runtime_session_id",
        "tmux_session_name",
        "tmux_window_name",
        "manifest_path",
        "session_root",
        "agent_name",
        "agent_id",
    )
    @classmethod
    def _optional_not_blank(cls, value: str | None) -> str | None:
        """Require optional string fields to be non-empty when present."""

        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped


class HoumaoManagedAgentListResponse(_HoumaoModel):
    """Response for `GET /houmao/agents`."""

    agents: list[HoumaoManagedAgentIdentity] = Field(default_factory=list)


class HoumaoManagedAgentTurnView(_HoumaoModel):
    """Shared coarse turn posture for one managed agent."""

    phase: ManagedAgentTurnPhase
    active_turn_id: str | None = None

    @field_validator("active_turn_id")
    @classmethod
    def _active_turn_not_blank(cls, value: str | None) -> str | None:
        """Require optional active-turn ids to be non-empty when present."""

        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped


class HoumaoManagedAgentLastTurnView(_HoumaoModel):
    """Shared coarse last-turn summary."""

    result: ManagedAgentLastTurnResult
    turn_id: str | None = None
    turn_index: int | None = None
    updated_at_utc: str | None = None

    @field_validator("turn_id", "updated_at_utc")
    @classmethod
    def _optional_not_blank(cls, value: str | None) -> str | None:
        """Require optional string fields to be non-empty when present."""

        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped


class HoumaoManagedAgentMailboxSummaryView(_HoumaoModel):
    """Redacted mailbox posture for one managed agent."""

    transport: MailboxTransport
    principal_id: str | None = None
    address: str | None = None

    @field_validator("principal_id", "address")
    @classmethod
    def _optional_not_blank(cls, value: str | None) -> str | None:
        """Require optional mailbox strings to be non-empty when present."""

        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped


class HoumaoManagedAgentGatewaySummaryView(_HoumaoModel):
    """Redacted gateway posture for one managed agent."""

    gateway_health: GatewayHealthState
    managed_agent_connectivity: GatewayConnectivityState
    managed_agent_recovery: GatewayRecoveryState
    request_admission: GatewayAdmissionState
    active_execution: GatewayExecutionState
    queue_depth: int
    gateway_host: GatewayHost | None = None
    gateway_port: int | None = None

    @field_validator("queue_depth")
    @classmethod
    def _non_negative_queue_depth(cls, value: int) -> int:
        """Require non-negative queue depth values."""

        if value < 0:
            raise ValueError("must be >= 0")
        return value

    @field_validator("gateway_port")
    @classmethod
    def _optional_gateway_port(cls, value: int | None) -> int | None:
        """Require optional gateway ports to stay within the TCP range."""

        if value is None:
            return None
        if value < 1 or value > 65535:
            raise ValueError("must be between 1 and 65535")
        return value


class HoumaoManagedAgentStateResponse(_HoumaoModel):
    """Response for `GET /houmao/agents/{agent_ref}/state`."""

    tracked_agent_id: str
    identity: HoumaoManagedAgentIdentity
    availability: ManagedAgentAvailability
    turn: HoumaoManagedAgentTurnView
    last_turn: HoumaoManagedAgentLastTurnView
    diagnostics: list[HoumaoErrorDetail] = Field(default_factory=list)
    mailbox: HoumaoManagedAgentMailboxSummaryView | None = None
    gateway: HoumaoManagedAgentGatewaySummaryView | None = None
    memory_dir: str | None = None

    @field_validator("tracked_agent_id", "memory_dir")
    @classmethod
    def _tracked_agent_id_not_blank(cls, value: str | None) -> str | None:
        """Require optional string identifiers to be non-empty when present."""

        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped


class HoumaoManagedAgentHistoryEntry(_HoumaoModel):
    """One bounded coarse managed-agent history entry."""

    recorded_at_utc: str
    summary: str
    availability: ManagedAgentAvailability
    turn_phase: ManagedAgentTurnPhase
    last_turn_result: ManagedAgentLastTurnResult
    turn_id: str | None = None

    @field_validator("recorded_at_utc", "summary", "turn_id")
    @classmethod
    def _optional_not_blank(cls, value: str | None) -> str | None:
        """Require optional string fields to be non-empty when present."""

        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped


class HoumaoManagedAgentHistoryResponse(_HoumaoModel):
    """Response for `GET /houmao/agents/{agent_ref}/history`."""

    tracked_agent_id: str
    entries: list[HoumaoManagedAgentHistoryEntry] = Field(default_factory=list)

    @field_validator("tracked_agent_id")
    @classmethod
    def _tracked_agent_id_not_blank(cls, value: str) -> str:
        """Require a non-empty tracked-agent id."""

        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped


class HoumaoManagedAgentTuiDetailView(_HoumaoModel):
    """Curated TUI projection exposed under the managed-agent detail route."""

    transport: Literal["tui"] = "tui"
    terminal_id: str
    canonical_terminal_state_route: str
    canonical_terminal_history_route: str
    diagnostics: HoumaoTrackedDiagnostics
    probe_snapshot: HoumaoProbeSnapshot | None = None
    parsed_surface: HoumaoParsedSurface | None = None
    surface: HoumaoTrackedSurface
    stability: HoumaoStabilityMetadata

    @field_validator(
        "terminal_id",
        "canonical_terminal_state_route",
        "canonical_terminal_history_route",
    )
    @classmethod
    def _not_blank(cls, value: str) -> str:
        """Require non-empty route and terminal identifiers."""

        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped


class HoumaoManagedAgentHeadlessDetailView(_HoumaoModel):
    """Execution-centric detail for one managed headless agent."""

    transport: Literal["headless"] = "headless"
    runtime_resumable: bool
    tmux_session_live: bool
    can_accept_prompt_now: bool
    interruptible: bool
    chat_session: GatewayHeadlessChatSessionStateV1 | None = None
    turn: HoumaoManagedAgentTurnView
    last_turn: HoumaoManagedAgentLastTurnView
    active_turn_started_at_utc: str | None = None
    active_turn_interrupt_requested_at_utc: str | None = None
    last_turn_status: ManagedAgentTurnStatus | None = None
    last_turn_started_at_utc: str | None = None
    last_turn_completed_at_utc: str | None = None
    last_turn_completion_source: str | None = None
    last_turn_returncode: int | None = None
    last_turn_history_summary: str | None = None
    last_turn_error: str | None = None
    mailbox: HoumaoManagedAgentMailboxSummaryView | None = None
    gateway: HoumaoManagedAgentGatewaySummaryView | None = None
    diagnostics: list[HoumaoErrorDetail] = Field(default_factory=list)

    @field_validator(
        "active_turn_started_at_utc",
        "active_turn_interrupt_requested_at_utc",
        "last_turn_started_at_utc",
        "last_turn_completed_at_utc",
        "last_turn_completion_source",
        "last_turn_history_summary",
        "last_turn_error",
    )
    @classmethod
    def _optional_not_blank(cls, value: str | None) -> str | None:
        """Require optional headless detail strings to be non-empty when present."""

        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped


ManagedAgentDetailPayload = Annotated[
    HoumaoManagedAgentTuiDetailView | HoumaoManagedAgentHeadlessDetailView,
    Field(discriminator="transport"),
]


class HoumaoManagedAgentDetailResponse(_HoumaoModel):
    """Response for `GET /houmao/agents/{agent_ref}/state/detail`."""

    tracked_agent_id: str
    identity: HoumaoManagedAgentIdentity
    summary_state: HoumaoManagedAgentStateResponse
    detail: ManagedAgentDetailPayload

    @field_validator("tracked_agent_id")
    @classmethod
    def _tracked_agent_id_not_blank(cls, value: str) -> str:
        """Require a non-empty tracked-agent id."""

        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped


class HoumaoManagedAgentSubmitPromptRequest(_HoumaoModel):
    """Typed prompt-submission payload for the managed-agent request route."""

    request_kind: Literal["submit_prompt"] = "submit_prompt"
    prompt: str
    execution: GatewayExecutionOverrideV1 | None = None

    @field_validator("prompt")
    @classmethod
    def _prompt_not_blank(cls, value: str) -> str:
        """Require a non-empty prompt string."""

        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped


class HoumaoManagedAgentInterruptRequest(_HoumaoModel):
    """Typed interrupt payload for the managed-agent request route."""

    request_kind: Literal["interrupt"] = "interrupt"


HoumaoManagedAgentRequestEnvelope = Annotated[
    HoumaoManagedAgentSubmitPromptRequest | HoumaoManagedAgentInterruptRequest,
    Field(discriminator="request_kind"),
]


class HoumaoManagedAgentRequestAcceptedResponse(CaoSuccessResponse):
    """Accepted response for `POST /houmao/agents/{agent_ref}/requests`."""

    tracked_agent_id: str
    request_id: str
    request_kind: ManagedAgentRequestKind
    disposition: ManagedAgentRequestDisposition = "accepted"
    detail: str
    headless_turn_id: str | None = None
    headless_turn_index: int | None = None

    @field_validator(
        "tracked_agent_id",
        "request_id",
        "detail",
        "headless_turn_id",
    )
    @classmethod
    def _optional_not_blank(cls, value: str | None) -> str | None:
        """Require optional string fields to be non-empty when present."""

        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped


class HoumaoManagedAgentGatewayRequestCreate(GatewayRequestCreateV1):
    """Gateway-mediated managed-agent request payload."""


class HoumaoManagedAgentGatewayAttachRequest(_HoumaoModel):
    """Optional execution-mode selection for managed-agent gateway attach."""

    execution_mode: GatewayCurrentExecutionMode | None = None


class HoumaoManagedAgentGatewayRequestAcceptedResponse(GatewayAcceptedRequestV1):
    """Accepted response for `POST /houmao/agents/{agent_ref}/gateway/requests`."""


class HoumaoManagedAgentGatewayPromptControlRequest(GatewayPromptControlRequestV1):
    """Direct prompt-control request for `POST /houmao/agents/{agent_ref}/gateway/control/prompt`."""


class HoumaoManagedAgentGatewayPromptControlResponse(GatewayPromptControlResultV1):
    """Success response for `POST /houmao/agents/{agent_ref}/gateway/control/prompt`."""


class HoumaoManagedAgentGatewayHeadlessControlStateResponse(GatewayHeadlessControlStateV1):
    """Managed-agent gateway headless control-state payload."""


class HoumaoManagedAgentGatewayNextPromptSessionRequest(GatewayHeadlessNextPromptSessionRequestV1):
    """Managed-agent gateway next-prompt-session request payload."""


class HoumaoManagedAgentGatewayInternalHeadlessPromptRequest(_HoumaoModel):
    """Internal direct-execution request used by an attached gateway for headless prompts."""

    prompt: str
    turn_id: str | None = None
    chat_session: GatewayChatSessionSelectorV1 | None = None
    execution: GatewayExecutionOverrideV1 | None = None

    @field_validator("prompt", "turn_id")
    @classmethod
    def _optional_not_blank(cls, value: str | None) -> str | None:
        """Require prompt and optional turn id to be non-empty when present."""

        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped


class HoumaoManagedAgentMailStatusResponse(GatewayMailStatusV1):
    """Pair-owned managed-agent mail status payload."""


class HoumaoManagedAgentMailCheckRequest(GatewayMailCheckRequestV1):
    """Pair-owned managed-agent mail-check request payload."""


class HoumaoManagedAgentMailCheckResponse(GatewayMailCheckResponseV1):
    """Pair-owned managed-agent mail-check response payload."""


class HoumaoManagedAgentMailSendRequest(GatewayMailSendRequestV1):
    """Pair-owned managed-agent mail-send request payload."""


class HoumaoManagedAgentMailPostRequest(GatewayMailPostRequestV1):
    """Pair-owned managed-agent mail-post request payload."""


class HoumaoManagedAgentMailReplyRequest(GatewayMailReplyRequestV1):
    """Pair-owned managed-agent mail-reply request payload."""


class HoumaoManagedAgentMailStateRequest(GatewayMailStateRequestV1):
    """Pair-owned managed-agent mail-state request payload."""


class HoumaoManagedAgentMailActionResponse(GatewayMailActionResponseV1):
    """Pair-owned managed-agent mail action response payload."""


class HoumaoManagedAgentMailStateResponse(GatewayMailStateResponseV1):
    """Pair-owned managed-agent mail-state response payload."""


class HoumaoHeadlessLaunchMailboxOptions(_HoumaoModel):
    """Optional mailbox overrides for native headless launch."""

    transport: MailboxTransport | None = None
    filesystem_root: str | None = None
    principal_id: str | None = None
    address: str | None = None
    stalwart_base_url: str | None = None
    stalwart_jmap_url: str | None = None
    stalwart_management_url: str | None = None
    stalwart_login_identity: str | None = None

    @field_validator(
        "filesystem_root",
        "principal_id",
        "address",
        "stalwart_base_url",
        "stalwart_jmap_url",
        "stalwart_management_url",
        "stalwart_login_identity",
    )
    @classmethod
    def _optional_not_blank(cls, value: str | None) -> str | None:
        """Require optional mailbox override strings to be non-empty when present."""

        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped


class HoumaoHeadlessLaunchRequest(_HoumaoModel):
    """Resolved native headless launch request."""

    tool: str
    working_directory: str
    agent_def_dir: str
    brain_manifest_path: str
    role_name: str | None = None
    agent_name: str | None = None
    agent_id: str | None = None
    headless_display_style: Literal["plain", "json", "fancy"] | None = None
    headless_display_detail: Literal["concise", "detail"] | None = None
    mailbox: HoumaoHeadlessLaunchMailboxOptions | None = None

    @field_validator(
        "tool",
        "working_directory",
        "agent_def_dir",
        "brain_manifest_path",
        "role_name",
        "agent_name",
        "agent_id",
    )
    @classmethod
    def _optional_not_blank(cls, value: str | None) -> str | None:
        """Require optional string inputs to be non-empty when present."""

        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped


class HoumaoHeadlessLaunchResponse(CaoSuccessResponse):
    """Response for native headless launch."""

    tracked_agent_id: str
    identity: HoumaoManagedAgentIdentity
    manifest_path: str
    session_root: str
    detail: str


class HoumaoManagedAgentActionResponse(CaoSuccessResponse):
    """Generic success response for managed-agent actions."""

    tracked_agent_id: str
    detail: str
    turn_id: str | None = None

    @field_validator("tracked_agent_id", "detail", "turn_id")
    @classmethod
    def _optional_not_blank(cls, value: str | None) -> str | None:
        """Require optional string fields to be non-empty when present."""

        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped


class HoumaoHeadlessTurnRequest(_HoumaoModel):
    """Prompt submission for one managed headless turn."""

    prompt: str
    chat_session: GatewayChatSessionSelectorV1 | None = None
    execution: GatewayExecutionOverrideV1 | None = None

    @field_validator("prompt")
    @classmethod
    def _prompt_not_blank(cls, value: str) -> str:
        """Require a non-empty prompt."""

        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped


class HoumaoHeadlessTurnAcceptedResponse(CaoSuccessResponse):
    """Acceptance response for one managed headless turn."""

    tracked_agent_id: str
    turn_id: str
    turn_index: int
    status: ManagedAgentTurnStatus
    detail: str

    @field_validator("tracked_agent_id", "turn_id", "detail")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        """Require non-empty string fields."""

        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped


class HoumaoHeadlessTurnStatusResponse(_HoumaoModel):
    """Status response for one persisted headless turn."""

    tracked_agent_id: str
    turn_id: str
    turn_index: int
    status: ManagedAgentTurnStatus
    started_at_utc: str
    completed_at_utc: str | None = None
    returncode: int | None = None
    completion_source: str | None = None
    stdout_path: str | None = None
    stderr_path: str | None = None
    status_path: str | None = None
    history_summary: str | None = None
    error: str | None = None

    @field_validator(
        "tracked_agent_id",
        "turn_id",
        "started_at_utc",
        "completed_at_utc",
        "completion_source",
        "stdout_path",
        "stderr_path",
        "status_path",
        "history_summary",
        "error",
    )
    @classmethod
    def _optional_not_blank(cls, value: str | None) -> str | None:
        """Require optional string fields to be non-empty when present."""

        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped


class HoumaoHeadlessTurnEvent(_HoumaoModel):
    """Structured headless turn event."""

    kind: str
    message: str
    turn_index: int
    timestamp_utc: str
    payload: dict[str, object] | None = None

    @field_validator("kind", "message", "timestamp_utc")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        """Require non-empty string fields."""

        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped


class HoumaoHeadlessTurnEventsResponse(_HoumaoModel):
    """Structured event list for one headless turn."""

    tracked_agent_id: str
    turn_id: str
    entries: list[HoumaoHeadlessTurnEvent] = Field(default_factory=list)

    @field_validator("tracked_agent_id", "turn_id")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        """Require non-empty string fields."""

        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped
