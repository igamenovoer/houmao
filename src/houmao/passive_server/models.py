"""Pydantic models for passive-server API contracts."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from houmao.server.models import (
    HoumaoParsedSurface,
    HoumaoProbeSnapshot,
    HoumaoRecentTransition,
    HoumaoStabilityMetadata,
    HoumaoTrackedDiagnostics,
    HoumaoTrackedLastTurn,
    HoumaoTrackedSurface,
    HoumaoTrackedTurn,
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
