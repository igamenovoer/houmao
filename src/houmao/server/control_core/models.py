"""Internal models for the Houmao-owned CAO-compatible control core."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

CompatibilityTerminalStatus = Literal[
    "idle",
    "processing",
    "completed",
    "waiting_user_answer",
    "error",
]
CompatibilityInboxStatus = Literal["pending", "delivered", "failed"]


class _CompatibilityModel(BaseModel):
    """Strict base model for compatibility-core persistence."""

    model_config = ConfigDict(extra="forbid", strict=True)


class CompatibilityAgentProfile(BaseModel):
    """Parsed compatibility profile markdown plus frontmatter."""

    model_config = ConfigDict(extra="allow")

    name: str
    description: str
    provider: str | None = None
    system_prompt: str = ""
    prompt: str | None = None
    mcpServers: dict[str, Any] | None = None
    tools: list[str] | None = None
    toolAliases: dict[str, str] | None = None
    allowedTools: list[str] | None = None
    toolsSettings: dict[str, Any] | None = None
    resources: list[str] | None = None
    hooks: dict[str, Any] | None = None
    useLegacyMcpJson: bool | None = None
    model: str | None = None

    @field_validator("name", "description")
    @classmethod
    def _require_non_empty(cls, value: str) -> str:
        """Require non-empty string metadata."""

        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped


class CompatibilityTerminalRecord(_CompatibilityModel):
    """Durable terminal metadata owned by the compatibility core."""

    terminal_id: str
    session_name: str
    window_name: str
    window_id: str | None = None
    window_index: str | None = None
    provider: str
    agent_profile: str
    working_directory: str
    created_at_utc: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds")
    )
    last_active_utc: str | None = None

    @field_validator(
        "terminal_id",
        "session_name",
        "window_name",
        "provider",
        "agent_profile",
        "working_directory",
        "window_id",
        "window_index",
    )
    @classmethod
    def _normalize_optional_string(cls, value: str | None) -> str | None:
        """Require present string fields to be non-empty after trimming."""

        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped


class CompatibilitySessionRecord(_CompatibilityModel):
    """Durable session metadata owned by the compatibility core."""

    session_name: str
    created_at_utc: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds")
    )
    terminal_ids: list[str] = Field(default_factory=list)

    @field_validator("session_name")
    @classmethod
    def _normalize_session_name(cls, value: str) -> str:
        """Require one non-empty session name."""

        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped


class CompatibilityInboxMessageRecord(_CompatibilityModel):
    """Terminal-scoped compatibility inbox record."""

    message_id: int
    sender_id: str
    receiver_id: str
    message: str
    status: CompatibilityInboxStatus = "pending"
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds"))

    @field_validator("sender_id", "receiver_id", "message")
    @classmethod
    def _normalize_message_fields(cls, value: str) -> str:
        """Require non-empty inbox string fields."""

        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped


class CompatibilityRegistrySnapshot(_CompatibilityModel):
    """Persisted compatibility registry state."""

    schema_version: int = 1
    sessions: list[CompatibilitySessionRecord] = Field(default_factory=list)
    terminals: list[CompatibilityTerminalRecord] = Field(default_factory=list)
    inbox_messages: list[CompatibilityInboxMessageRecord] = Field(default_factory=list)


class CompatibilityProfileIndexRecord(_CompatibilityModel):
    """Persisted compatibility-profile index entry."""

    profile_name: str
    description: str
    requested_provider: str
    resolved_provider: str
    markdown_path: str
    context_path: str
    provider_artifact_paths: dict[str, str] = Field(default_factory=dict)
    installed_at_utc: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds")
    )

    @field_validator(
        "profile_name",
        "description",
        "requested_provider",
        "resolved_provider",
        "markdown_path",
        "context_path",
    )
    @classmethod
    def _normalize_profile_strings(cls, value: str) -> str:
        """Require non-empty profile index strings."""

        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped


class CompatibilityProfileIndexSnapshot(_CompatibilityModel):
    """Persisted compatibility-profile index."""

    schema_version: int = 1
    records: list[CompatibilityProfileIndexRecord] = Field(default_factory=list)
