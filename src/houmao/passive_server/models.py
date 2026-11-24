"""Pydantic models for passive-server API contracts."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from houmao.agents.realm_controller.gateway_models import (
    GatewayChatSessionSelectorV1,
    GatewayExecutionOverrideV1,
    GatewayWebControlStateV1,
    GatewayWebHistoryV1,
)
from houmao.agents.realm_controller.native_surface import NativeSurfaceV1
from houmao.agents.realm_controller.models import BackendKind
from houmao.agents.realm_controller.run_modes import RunMode
from houmao.gateway.access_models import GatewayLaunchSeed, GatewayTarget
from houmao.server.models import (
    HoumaoHeadlessLaunchMailboxesOptions,
    HoumaoHeadlessTurnEvent,
    HoumaoObservationChannel,
    HoumaoParsedSurface,
    HoumaoProbeSnapshot,
    HoumaoRecentTransition,
    HoumaoStabilityMetadata,
    HoumaoTrackedDiagnostics,
    HoumaoTrackedLastTurn,
    HoumaoTrackedSurface,
    HoumaoTrackedTurn,
    ManagedAgentTurnStatus,
)


class _PassiveModel(BaseModel):
    """Shared strict base model for passive-server payloads."""

    model_config = ConfigDict(extra="forbid", strict=True)


class PassiveProofEndpoint(_PassiveModel):
    """Describe one selected target on the current passive proof listener."""

    target: GatewayTarget
    presence_id: str = Field(pattern=r"^[A-Za-z0-9_][A-Za-z0-9_.:-]{0,127}$")
    admin_mode: Literal["open", "keyed"]
    proof_protocol: Literal["sshsig-v2"] = "sshsig-v2"
    challenge_path: str


class PassiveWorkRequestReceipt(_PassiveModel):
    """Evidence for a single direct passive work request."""

    request_id: str
    request_kind: Literal["submit_work_request"] = "submit_work_request"
    outcome: Literal["handed_off", "not_sent", "unknown"]
    error_code: str | None = None


class PassiveHealthResponse(_PassiveModel):
    """Health endpoint response."""

    status: Literal["ok"] = "ok"
    houmao_service: Literal["houmao-passive-server"] = "houmao-passive-server"


class PassiveCurrentInstance(_PassiveModel):
    """Current live server instance metadata."""

    schema_version: int = 1
    status: Literal["ok"] = "ok"
    pid: int
    api_base_url: str
    server_root: str
    started_at_utc: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds")
    )


class PassiveShutdownResponse(_PassiveModel):
    """Shutdown acknowledgement response."""

    status: Literal["ok"] = "ok"


class DiscoveredAgentSummary(_PassiveModel):
    """Projection of one discovered agent from the registry."""

    agent_id: str
    agent_name: str
    generation_id: str
    tool: str
    backend: BackendKind
    tmux_session_name: str
    manifest_path: str
    session_root: str
    has_gateway: bool
    has_mailbox: bool
    published_at: str
    lease_expires_at: str
    native_surface_kind: Literal["terminal", "web"] | None = None
    mode: RunMode
    browser_origin: str | None = None
    native_session_id: str | None = None
    native_surface: NativeSurfaceV1 | None = None


class DiscoveredAgentListResponse(_PassiveModel):
    """Response for ``GET /houmao/agents``."""

    agents: list[DiscoveredAgentSummary] = Field(default_factory=list)


class DiscoveredAgentConflictResponse(_PassiveModel):
    """Response for 409 ambiguous agent name resolution."""

    detail: str
    agent_ids: list[str]


class PassiveAgentGatewayAddress(_PassiveModel):
    """Volatile current gateway coordinates for an agent-address resolution."""

    host: str
    port: int
    protocol_version: str


class PassiveAgentAddressCandidate(_PassiveModel):
    """Safe identity metadata for an ambiguous known-agent address match."""

    agent_id: str
    agent_name: str
    lifecycle_state: str
    relaunchable: bool
    tool: str
    backend: str
    manifest_path: str
    session_root: str | None = None


class PassiveAgentAddressResolveResponse(_PassiveModel):
    """Response for agent-address AG-UI attachment resolution."""

    status: Literal[
        "unknown",
        "ambiguous",
        "offline",
        "live_without_gateway",
        "live_with_gateway",
    ]
    detail: str
    agent_ref: str
    agent_id: str | None = None
    agent_name: str | None = None
    generation_id: str | None = None
    lifecycle_state: str | None = None
    relaunchable: bool | None = None
    tool: str | None = None
    backend: str | None = None
    manifest_path: str | None = None
    session_root: str | None = None
    gateway: PassiveAgentGatewayAddress | None = None
    candidates: list[PassiveAgentAddressCandidate] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Agent TUI observation response models
# ---------------------------------------------------------------------------


class AgentTuiStateResponse(_PassiveModel):
    """Compact observation state for one discovered agent.

    Omits ``probe_snapshot`` and ``parsed_surface`` — use the detail endpoint
    for the full observation payload.
    """

    agent_id: str
    agent_name: str
    diagnostics: HoumaoTrackedDiagnostics
    surface: HoumaoTrackedSurface
    turn: HoumaoTrackedTurn
    last_turn: HoumaoTrackedLastTurn
    observation_channels: list[HoumaoObservationChannel] | None = None
    stability: HoumaoStabilityMetadata


class AgentTuiDetailResponse(_PassiveModel):
    """Full observation state for one discovered agent.

    Extends the compact response with ``probe_snapshot`` and ``parsed_surface``.
    """

    agent_id: str
    agent_name: str
    diagnostics: HoumaoTrackedDiagnostics
    probe_snapshot: HoumaoProbeSnapshot | None = None
    parsed_surface: HoumaoParsedSurface | None = None
    surface: HoumaoTrackedSurface
    turn: HoumaoTrackedTurn
    last_turn: HoumaoTrackedLastTurn
    observation_channels: list[HoumaoObservationChannel] | None = None
    stability: HoumaoStabilityMetadata


class AgentTuiHistoryResponse(_PassiveModel):
    """Recent state transitions for one discovered agent."""

    agent_id: str
    agent_name: str
    entries: list[HoumaoRecentTransition] = Field(default_factory=list)


class AgentWebStateResponse(_PassiveModel):
    """Compact native Web state without terminal or local browser draft signals."""

    transport: Literal["web"] = "web"
    agent_id: str
    agent_name: str
    web: GatewayWebControlStateV1


class AgentWebHistoryResponse(_PassiveModel):
    """Bounded native Web transitions for one discovered logical agent."""

    transport: Literal["web"] = "web"
    agent_id: str
    agent_name: str
    web: GatewayWebHistoryV1


# ---------------------------------------------------------------------------
# Request / response models for Tier 5–7
# ---------------------------------------------------------------------------


def _require_non_empty(value: str | None) -> str | None:
    """Validate optional strings are non-empty when present."""

    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        raise ValueError("must not be empty")
    return stripped


class PassivePromptRequest(_PassiveModel):
    """Request body for ``POST /houmao/agents/{agent_ref}/requests``."""

    prompt: str

    @field_validator("prompt")
    @classmethod
    def _prompt_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("prompt must not be empty")
        return stripped


class PassiveHeadlessLaunchRequest(_PassiveModel):
    """Request body for ``POST /houmao/agents/headless/launches``."""

    tool: str
    working_directory: str
    agent_def_dir: str
    brain_manifest_path: str
    role_name: str | None = None
    agent_name: str | None = None
    agent_id: str | None = None
    agent_id_mode: Literal["uuid", "name-hash"] | None = None
    headless_display_style: Literal["plain", "json", "fancy"] | None = None
    headless_display_detail: Literal["concise", "detail"] | None = None
    mailboxes: HoumaoHeadlessLaunchMailboxesOptions | None = None
    gateway_admin_seed: GatewayLaunchSeed | None = None

    @model_validator(mode="after")
    def _identity_selection(self) -> PassiveHeadlessLaunchRequest:
        """Reject ambiguous identity inputs before starting a body."""

        if self.agent_id is not None and self.agent_id_mode is not None:
            raise ValueError("agent_id and explicit agent_id_mode cannot be combined")
        return self

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
        return _require_non_empty(value)


class PassiveHeadlessTurnRequest(_PassiveModel):
    """Request body for ``POST /houmao/agents/{agent_ref}/turns``."""

    prompt: str
    chat_session: GatewayChatSessionSelectorV1 | None = None
    execution: GatewayExecutionOverrideV1 | None = None

    @field_validator("prompt")
    @classmethod
    def _prompt_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("prompt must not be empty")
        return value


class PassiveRequestAcceptedResponse(_PassiveModel):
    """Response for gateway-mediated prompt delivery."""

    status: Literal["ok"] = "ok"
    request_id: str
    detail: str = "Request forwarded to gateway"


class PassiveAgentActionResponse(_PassiveModel):
    """Response for agent interrupt / stop actions."""

    status: Literal["ok"] = "ok"
    agent_id: str
    detail: str


class PassiveHeadlessLaunchResponse(_PassiveModel):
    """Response for ``POST /houmao/agents/headless/launches``."""

    status: Literal["ok"] = "ok"
    tracked_agent_id: str
    agent_name: str
    manifest_path: str
    session_root: str
    detail: str


class PassiveHeadlessTurnAcceptedResponse(_PassiveModel):
    """Response for ``POST /houmao/agents/{agent_ref}/turns``."""

    status: Literal["ok"] = "ok"
    tracked_agent_id: str
    turn_id: str
    turn_index: int
    turn_status: ManagedAgentTurnStatus
    detail: str


class PassiveHeadlessTurnStatusResponse(_PassiveModel):
    """Response for ``GET /houmao/agents/{agent_ref}/turns/{turn_id}``."""

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
    error: str | None = None


class PassiveHeadlessTurnEventsResponse(_PassiveModel):
    """Response for ``GET /houmao/agents/{agent_ref}/turns/{turn_id}/events``."""

    tracked_agent_id: str
    turn_id: str
    entries: list[HoumaoHeadlessTurnEvent] = Field(default_factory=list)


class PassiveNotImplementedResponse(_PassiveModel):
    """Response body for 501 Not Implemented endpoints."""

    detail: str
