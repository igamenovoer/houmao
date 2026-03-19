"""Pydantic models for Houmao server contracts."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from houmao.cao.models import (
    CaoHealthResponse,
    CaoSuccessResponse,
    CaoTerminal,
)

TerminalId = Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{8}$")]


class _HoumaoModel(BaseModel):
    """Shared base model for Houmao server payloads."""

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


class HoumaoRawObservation(_HoumaoModel):
    """Latest raw observation captured by a watch worker."""

    observed_at_utc: str
    terminal_id: str
    session_name: str
    backend_status: str | None = None
    output_hash: str | None = None
    output_length: int = 0
    output_excerpt: str = ""


class HoumaoOwnedWork(_HoumaoModel):
    """Server-owned active or last-known request lifecycle."""

    request_id: str | None = None
    submitted_at_utc: str | None = None
    completed_at_utc: str | None = None
    message_excerpt: str | None = None
    state: Literal["idle", "submitted", "completed"] = "idle"


class HoumaoExternalActivity(_HoumaoModel):
    """External-activity reduction derived from raw observation changes."""

    last_changed_at_utc: str | None = None
    output_hash: str | None = None


class HoumaoOperatorState(_HoumaoModel):
    """Operator-facing reduced terminal state."""

    status: Literal[
        "ready",
        "processing",
        "waiting_user_answer",
        "completed",
        "unknown",
        "unavailable",
        "error",
    ]
    detail: str
    updated_at_utc: str


class HoumaoTerminalStateResponse(_HoumaoModel):
    """Houmao extension route for live terminal state."""

    terminal: CaoTerminal
    raw_observation: HoumaoRawObservation | None = None
    owned_work: HoumaoOwnedWork
    external_activity: HoumaoExternalActivity
    operator_state: HoumaoOperatorState


class HoumaoTerminalHistoryEntry(_HoumaoModel):
    """One append-only terminal history entry."""

    recorded_at_utc: str
    kind: Literal["sample", "transition"]
    payload: dict[str, object]


class HoumaoTerminalHistoryResponse(_HoumaoModel):
    """Houmao extension route for append-only terminal history."""

    terminal_id: str
    entries: list[HoumaoTerminalHistoryEntry]


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

    @field_validator(
        "session_name",
        "tool",
        "terminal_id",
        "manifest_path",
        "session_root",
        "agent_name",
        "agent_id",
        "tmux_session_name",
    )
    @classmethod
    def _optional_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("must not be empty")
        return value


class HoumaoRegisterLaunchResponse(CaoSuccessResponse):
    """Registration response for delegated CLI launches."""

    session_name: str
    terminal_id: str


class HoumaoTerminalStateRecord(_HoumaoModel):
    """Persisted compatibility mirror for one terminal state snapshot."""

    schema_version: int = 1
    state: HoumaoTerminalStateResponse
