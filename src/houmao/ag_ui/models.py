"""AG-UI protocol and Houmao extension models used by the gateway adapter."""

from __future__ import annotations

from typing import Any, Literal

from ag_ui.core import (
    AgentCapabilities as AgUiAgentCapabilities,
    EventType as AgUiEventType,
    RunAgentInput,
    StateSnapshotEvent as AgUiStateSnapshotEvent,
)
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class _HoumaoAgUiModel(BaseModel):
    """Base model for Houmao-owned AG-UI payload extensions."""

    model_config = ConfigDict(
        extra="forbid",
        alias_generator=to_camel,
        populate_by_name=True,
    )


class AgUiConnectInput(RunAgentInput):
    """AG-UI connect input accepted by Houmao attachment streams."""

    last_seen_event_id: str | None = None


class HoumaoAgUiFeatureSupport(_HoumaoAgUiModel):
    """Conservative feature flags for this AG-UI attachment milestone."""

    http_sse: bool
    gui_connect: bool
    text_input_parsing: bool
    state_snapshots: bool
    task_run_submission: bool
    state_deltas: bool
    frontend_tool_execution: bool
    generated_graphics: bool
    open_generative_ui: bool
    multimodal_input: bool


class HoumaoAgUiMetadata(_HoumaoAgUiModel):
    """Houmao-specific lifecycle and replay metadata for AG-UI clients."""

    schema_version: int = Field(default=1)
    agent_lifecycle_managed_by_gui: bool
    lifecycle_boundary: str
    replay_support: Literal["current_snapshot_only", "event_log_since_cursor"]
    connect_stream_keepalive: Literal["sse_comment_heartbeat"]
    features: HoumaoAgUiFeatureSupport
    gateway: dict[str, Any]


class HoumaoAgUiCapabilitiesResponse(_HoumaoAgUiModel):
    """Response payload for `GET /v1/ag-ui/capabilities`."""

    capabilities: AgUiAgentCapabilities
    houmao: HoumaoAgUiMetadata


class AgUiDetachResponse(_HoumaoAgUiModel):
    """Response payload for explicit AG-UI GUI detachment."""

    status: Literal["detached", "not_found"]
    connection_id: str
    detached: bool
    detail: str


class AgUiRunsUnavailableResponse(_HoumaoAgUiModel):
    """Deterministic response for unavailable AG-UI run submission."""

    status: Literal["unavailable"] = "unavailable"
    code: Literal["ag_ui_runs_unavailable"] = "ag_ui_runs_unavailable"
    detail: str = "AG-UI task runs are not enabled for this Houmao gateway milestone."


class AgUiEventPublishRequest(_HoumaoAgUiModel):
    """Request body for publishing already-standard AG-UI events to one gateway."""

    thread_id: str | None = None
    run_id: str | None = None
    connection_id: str | None = None
    events: list[dict[str, Any]]


class AgUiEventPublishResponse(_HoumaoAgUiModel):
    """Response body for a published AG-UI event batch."""

    status: Literal["accepted"] = "accepted"
    accepted_count: int
    stored_count: int = 0
    delivered_count: int
    replay: Literal["none", "event_log_since_cursor"] = "none"
    thread_id: str | None = None
    run_id: str | None = None
    connection_id: str | None = None


__all__ = [
    "AgUiAgentCapabilities",
    "AgUiConnectInput",
    "AgUiDetachResponse",
    "AgUiEventPublishRequest",
    "AgUiEventPublishResponse",
    "AgUiEventType",
    "AgUiRunsUnavailableResponse",
    "AgUiStateSnapshotEvent",
    "HoumaoAgUiCapabilitiesResponse",
    "HoumaoAgUiFeatureSupport",
    "HoumaoAgUiMetadata",
]
