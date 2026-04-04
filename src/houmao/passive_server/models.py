"""Pydantic models for passive-server API contracts."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from houmao.agents.realm_controller.gateway_models import GatewayChatSessionSelectorV1
from houmao.server.models import (
    HoumaoHeadlessLaunchMailboxOptions,
    HoumaoHeadlessTurnEvent,
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
    backend: str
    tmux_session_name: str
    manifest_path: str
    session_root: str
    has_gateway: bool
    has_mailbox: bool
    published_at: str
    lease_expires_at: str


class DiscoveredAgentListResponse(_PassiveModel):
    """Response for ``GET /houmao/agents``."""

    agents: list[DiscoveredAgentSummary] = Field(default_factory=list)


class DiscoveredAgentConflictResponse(_PassiveModel):
    """Response for 409 ambiguous agent name resolution."""

    detail: str
    agent_ids: list[str]


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
    stability: HoumaoStabilityMetadata


class AgentTuiHistoryResponse(_PassiveModel):
    """Recent state transitions for one discovered agent."""

    agent_id: str
    agent_name: str
    entries: list[HoumaoRecentTransition] = Field(default_factory=list)


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
        return _require_non_empty(value)


class PassiveHeadlessTurnRequest(_PassiveModel):
    """Request body for ``POST /houmao/agents/{agent_ref}/turns``."""

    prompt: str
    chat_session: GatewayChatSessionSelectorV1 | None = None

    @field_validator("prompt")
    @classmethod
    def _prompt_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("prompt must not be empty")
        return stripped


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
