"""Pydantic models for CAO REST request/response boundaries."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal, TypeAlias

from pydantic import BaseModel, ConfigDict

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list[object] | dict[str, object]


class _CaoModel(BaseModel):
    """Base model for CAO payload parsing."""

    model_config = ConfigDict(extra="ignore")


class CaoProvider(str, Enum):
    """Provider enum exposed by CAO."""

    Q_CLI = "q_cli"
    KIRO_CLI = "kiro_cli"
    CLAUDE_CODE = "claude_code"
    CODEX = "codex"


class CaoTerminalStatus(str, Enum):
    """Terminal status values exposed by CAO."""

    IDLE = "idle"
    PROCESSING = "processing"
    COMPLETED = "completed"
    WAITING_USER_ANSWER = "waiting_user_answer"
    ERROR = "error"


class CaoInboxMessageStatus(str, Enum):
    """Inbox message status values exposed by CAO."""

    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"


class CaoHealthResponse(_CaoModel):
    """`GET /health` response."""

    status: str
    service: str


class CaoSuccessResponse(_CaoModel):
    """Common `{success: bool}` response shape."""

    success: bool


class CaoErrorResponse(_CaoModel):
    """Standard CAO error payload."""

    detail: JsonValue


class CaoSessionInfo(_CaoModel):
    """Session object returned from `GET /sessions`."""

    id: str
    name: str
    status: str


class CaoTerminal(_CaoModel):
    """Terminal response model."""

    id: str
    name: str
    provider: CaoProvider
    session_name: str
    agent_profile: str | None = None
    status: CaoTerminalStatus | None = None
    last_active: datetime | None = None


class CaoTerminalOutputResponse(_CaoModel):
    """`GET /terminals/{id}/output` response."""

    output: str
    mode: Literal["full", "last", "tail"]


class CaoInboxMessage(_CaoModel):
    """Inbox message response model."""

    id: int
    sender_id: str
    receiver_id: str
    message: str
    status: CaoInboxMessageStatus
    created_at: datetime | None = None


class CaoInboxCreateResponse(_CaoModel):
    """Response for `POST /terminals/{id}/inbox/messages`."""

    success: bool
    message_id: int
    sender_id: str
    receiver_id: str
    created_at: datetime | None = None
