"""Strict models for the shared live-agent registry contract."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from houmao.agents.mailbox_runtime_models import MailboxTransport
from houmao.agents.realm_controller.agent_identity import normalize_agent_identity_name
from houmao.agents.realm_controller.gateway_models import GatewayHost, GatewayProtocolVersion
from houmao.agents.realm_controller.models import BackendKind

REGISTRY_SCHEMA_VERSION = 2
TERMINAL_KIND_TMUX: Literal["tmux"] = "tmux"


class _StrictRegistryModel(BaseModel):
    """Shared config for strict registry payloads."""

    model_config = ConfigDict(extra="forbid", strict=True)


class RegistryIdentityV1(_StrictRegistryModel):
    """Identity metadata for one live published agent."""

    backend: BackendKind
    tool: str

    @field_validator("tool")
    @classmethod
    def _tool_not_blank(cls, value: str) -> str:
        """Validate that the tool name is non-empty."""

        if not value.strip():
            raise ValueError("must not be empty")
        return value


class RegistryRuntimeV1(_StrictRegistryModel):
    """Pointers to runtime-owned state for one live session."""

    manifest_path: str
    session_root: str | None = None
    agent_def_dir: str | None = None

    @field_validator("manifest_path", "session_root", "agent_def_dir")
    @classmethod
    def _optional_not_blank(cls, value: str | None) -> str | None:
        """Validate optional runtime pointer strings."""

        if value is None:
            return None
        if not value.strip():
            raise ValueError("must not be empty")
        return value


class RegistryTerminalV1(_StrictRegistryModel):
    """Terminal-container hints for the live published session."""

    kind: Literal["tmux"] = Field(default=TERMINAL_KIND_TMUX)
    session_name: str

    @field_validator("session_name")
    @classmethod
    def _session_name_not_blank(cls, value: str) -> str:
        """Validate the terminal session name."""

        if not value.strip():
            raise ValueError("must not be empty")
        return value


class RegistryGatewayV1(_StrictRegistryModel):
    """Stable and live gateway metadata published into the registry."""

    gateway_root: str
    attach_path: str
    host: GatewayHost | None = None
    port: int | None = None
    state_path: str | None = None
    protocol_version: GatewayProtocolVersion | None = None

    @field_validator("gateway_root", "attach_path", "state_path")
    @classmethod
    def _optional_path_not_blank(cls, value: str | None) -> str | None:
        """Validate gateway pointer strings."""

        if value is None:
            return None
        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @field_validator("port")
    @classmethod
    def _port_range(cls, value: int | None) -> int | None:
        """Validate the optional live gateway port."""

        if value is None:
            return None
        if value < 1 or value > 65535:
            raise ValueError("must be between 1 and 65535")
        return value

    @model_validator(mode="after")
    def _validate_live_fields(self) -> "RegistryGatewayV1":
        """Require live gateway fields to appear as one complete group."""

        live_fields = (
            self.host is not None,
            self.port is not None,
            self.state_path is not None,
            self.protocol_version is not None,
        )
        if any(live_fields) and not all(live_fields):
            raise ValueError("host, port, state_path, and protocol_version must be set together")
        return self


class RegistryMailboxV1(_StrictRegistryModel):
    """Mailbox identity metadata for one live published session."""

    transport: MailboxTransport
    principal_id: str
    address: str
    filesystem_root: str
    bindings_version: str

    @field_validator("principal_id", "address", "filesystem_root", "bindings_version")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        """Validate non-empty mailbox metadata."""

        if not value.strip():
            raise ValueError("must not be empty")
        return value


class LiveAgentRegistryRecordV2(_StrictRegistryModel):
    """Shared-registry ``record.json`` contract for one live published agent."""

    schema_version: int = Field(default=REGISTRY_SCHEMA_VERSION)
    agent_name: str
    agent_id: str
    generation_id: str
    published_at: str
    lease_expires_at: str
    identity: RegistryIdentityV1
    runtime: RegistryRuntimeV1
    terminal: RegistryTerminalV1
    gateway: RegistryGatewayV1 | None = None
    mailbox: RegistryMailboxV1 | None = None

    @field_validator(
        "agent_name",
        "agent_id",
        "generation_id",
        "published_at",
        "lease_expires_at",
    )
    @classmethod
    def _not_blank(cls, value: str) -> str:
        """Validate non-empty top-level registry strings."""

        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @field_validator("agent_id")
    @classmethod
    def _agent_id_safe_for_paths(cls, value: str) -> str:
        """Validate that ``agent_id`` is safe for filesystem keying."""

        stripped = value.strip()
        if "/" in stripped or "\\" in stripped:
            raise ValueError("agent_id must not contain path separators")
        return stripped

    @model_validator(mode="after")
    def _validate_schema_and_identity(self) -> "LiveAgentRegistryRecordV2":
        """Validate schema version, canonical name, and lease ordering."""

        if self.schema_version != REGISTRY_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {REGISTRY_SCHEMA_VERSION}")

        normalized = normalize_agent_identity_name(self.agent_name)
        if normalized.canonical_name != self.agent_name:
            raise ValueError("agent_name must use canonical `AGENTSYS-...` form")

        published_at = _parse_iso8601_timestamp(self.published_at, field_name="published_at")
        lease_expires_at = _parse_iso8601_timestamp(
            self.lease_expires_at,
            field_name="lease_expires_at",
        )
        if lease_expires_at <= published_at:
            raise ValueError("lease_expires_at must be later than published_at")
        return self


def canonicalize_registry_agent_name(value: str) -> str:
    """Canonicalize registry-facing agent input to ``AGENTSYS-...`` form."""

    return normalize_agent_identity_name(value).canonical_name


def format_registry_validation_error(prefix: str, exc: ValidationError) -> str:
    """Return a short actionable Pydantic validation error string."""

    details: list[str] = []
    for issue in exc.errors(include_url=False):
        location = _format_error_location(issue.get("loc", ()))
        message = str(issue.get("msg", "validation failed"))
        details.append(f"{location}: {message}")
        if len(details) >= 3:
            break
    joined = "; ".join(details) if details else "validation failed"
    return f"{prefix}: {joined}"


def _format_error_location(location: object) -> str:
    """Format one Pydantic error location into a compact JSONPath-like string."""

    if not isinstance(location, tuple) or not location:
        return "$"

    path = "$"
    for item in location:
        if isinstance(item, int):
            path += f"[{item}]"
            continue
        path += f".{item}"
    return path


def _parse_iso8601_timestamp(value: str, *, field_name: str) -> datetime:
    """Parse one ISO-8601 timestamp and raise a consistent field error on failure."""

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a valid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field_name} must be a timezone-aware ISO-8601 timestamp")
    return parsed
