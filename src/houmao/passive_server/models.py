"""Pydantic models for passive-server API contracts."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


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
