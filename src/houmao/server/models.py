"""Pydantic models for `houmao-server` contracts.

This module defines the public API payloads exposed by the server-owned live
TUI tracker, alongside the registration request/response models used by the
runtime bridge.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from houmao.cao.models import CaoHealthResponse, CaoSuccessResponse

TerminalId = Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{8}$")]
TransportState = Literal["tmux_up", "tmux_missing", "probe_error"]
ProcessState = Literal["tui_up", "tui_down", "unsupported_tool", "probe_error", "unknown"]
ParseStatus = Literal[
    "parsed",
    "skipped_tui_down",
    "unsupported_tool",
    "transport_unavailable",
    "probe_error",
    "parse_error",
]
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
    tmux_session_name: str
    tmux_window_name: str | None = None
    terminal_aliases: tuple[str, ...] = ()
    agent_name: str | None = None
    agent_id: str | None = None
    manifest_path: str | None = None
    session_root: str | None = None

    @field_validator(
        "tracked_session_id",
        "session_name",
        "tool",
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
    matched_process_names: tuple[str, ...] = ()


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
    anomaly_codes: tuple[str, ...] = ()
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
    readiness_state: str
    completion_state: str
    detail: str
    projection_changed: bool = False
    updated_at_utc: str


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
    changed_fields: tuple[str, ...] = ()
    transport_state: TransportState
    process_state: ProcessState
    parse_status: ParseStatus
    operator_status: OperatorStatus


class HoumaoTerminalStateResponse(_HoumaoModel):
    """Houmao extension route for live tracked terminal state."""

    terminal_id: str
    tracked_session: HoumaoTrackedSessionIdentity
    transport_state: TransportState
    process_state: ProcessState
    parse_status: ParseStatus
    probe_snapshot: HoumaoProbeSnapshot | None = None
    probe_error: HoumaoErrorDetail | None = None
    parse_error: HoumaoErrorDetail | None = None
    parsed_surface: HoumaoParsedSurface | None = None
    operator_state: HoumaoOperatorState
    stability: HoumaoStabilityMetadata
    recent_transitions: tuple[HoumaoRecentTransition, ...] = ()


class HoumaoTerminalHistoryResponse(_HoumaoModel):
    """Houmao extension route for bounded in-memory recent history."""

    terminal_id: str
    tracked_session_id: str
    entries: tuple[HoumaoRecentTransition, ...]


class HoumaoRegisterLaunchRequest(_HoumaoModel):
    """Registration request for delegated CLI launches."""

    session_name: str
    terminal_id: str | None = None
    tool: str
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
