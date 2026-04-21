"""Strict models for the shared managed-agent registry contract."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from houmao.agents.realm_controller.agent_identity import (
    normalize_managed_agent_id,
    normalize_managed_agent_name,
)
from houmao.agents.realm_controller.errors import SessionManifestError
from houmao.agents.realm_controller.gateway_models import GatewayHost, GatewayProtocolVersion
from houmao.agents.realm_controller.models import BackendKind

REGISTRY_SCHEMA_VERSION = 3
LEGACY_REGISTRY_SCHEMA_VERSION = 2
TERMINAL_KIND_TMUX: Literal["tmux"] = "tmux"
LifecycleState = Literal["active", "stopped", "relaunching", "retired"]


class _StrictRegistryModel(BaseModel):
    """Shared config for strict registry payloads."""

    model_config = ConfigDict(extra="forbid", strict=True)


class RegistryIdentityV1(_StrictRegistryModel):
    """Identity metadata for one published managed-agent record."""

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
    """Pointers to runtime-owned state for one managed-agent record."""

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
    """Legacy live-session terminal hints for schema-version 2 registry payloads."""

    kind: Literal["tmux"] = Field(default=TERMINAL_KIND_TMUX)
    session_name: str

    @field_validator("session_name")
    @classmethod
    def _session_name_not_blank(cls, value: str) -> str:
        """Validate the terminal session name."""

        if not value.strip():
            raise ValueError("must not be empty")
        return value


class RegistryTerminalV2(_StrictRegistryModel):
    """Terminal-container hints for lifecycle-aware registry payloads."""

    kind: Literal["tmux"] = Field(default=TERMINAL_KIND_TMUX)
    current_session_name: str | None = None
    last_session_name: str | None = None

    @field_validator("current_session_name", "last_session_name")
    @classmethod
    def _optional_session_name_not_blank(cls, value: str | None) -> str | None:
        """Validate current and last-known session names."""

        if value is None:
            return None
        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @model_validator(mode="after")
    def _validate_terminal_binding(self) -> "RegistryTerminalV2":
        """Require at least one current or last-known session binding."""

        if self.current_session_name is None and self.last_session_name is None:
            raise ValueError(
                "current_session_name or last_session_name must be present for tmux records"
            )
        return self

    @property
    def session_name(self) -> str:
        """Return the current live tmux session name or the last-known fallback."""

        return self.current_session_name or self.last_session_name or ""


class RegistryLifecycleV1(_StrictRegistryModel):
    """Lifecycle metadata for one managed-agent registry record."""

    state: LifecycleState
    relaunchable: bool
    state_updated_at: str
    stopped_at: str | None = None
    stop_reason: str | None = None

    @field_validator("state_updated_at", "stopped_at", "stop_reason")
    @classmethod
    def _optional_not_blank(cls, value: str | None) -> str | None:
        """Validate optional lifecycle strings."""

        if value is None:
            return None
        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @model_validator(mode="after")
    def _validate_lifecycle_state(self) -> "RegistryLifecycleV1":
        """Validate lifecycle timestamps and per-state invariants."""

        _parse_iso8601_timestamp(self.state_updated_at, field_name="state_updated_at")
        stopped_at = (
            _parse_iso8601_timestamp(self.stopped_at, field_name="stopped_at")
            if self.stopped_at is not None
            else None
        )
        if self.state in {"stopped", "retired"} and stopped_at is None:
            raise ValueError("stopped_at is required when lifecycle.state is stopped or retired")
        if self.state in {"active", "relaunching"} and stopped_at is not None:
            raise ValueError("stopped_at is only valid for stopped or retired lifecycle states")
        if self.state in {"active", "relaunching"} and self.stop_reason is not None:
            raise ValueError("stop_reason is only valid for stopped or retired lifecycle states")
        if self.state == "retired" and self.relaunchable:
            raise ValueError("retired lifecycle records must not remain relaunchable")
        return self


class RegistryLivenessV1(_StrictRegistryModel):
    """Active-only liveness metadata for one managed-agent record."""

    published_at: str
    lease_expires_at: str

    @field_validator("published_at", "lease_expires_at")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        """Validate non-empty liveness timestamps."""

        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @model_validator(mode="after")
    def _validate_liveness(self) -> "RegistryLivenessV1":
        """Validate active lease ordering."""

        published_at = _parse_iso8601_timestamp(self.published_at, field_name="published_at")
        lease_expires_at = _parse_iso8601_timestamp(
            self.lease_expires_at,
            field_name="lease_expires_at",
        )
        if lease_expires_at <= published_at:
            raise ValueError("lease_expires_at must be later than published_at")
        return self


class RegistryGatewayV1(_StrictRegistryModel):
    """Optional live gateway connect metadata published into the registry."""

    host: GatewayHost
    port: int
    state_path: str
    protocol_version: GatewayProtocolVersion

    @field_validator("state_path")
    @classmethod
    def _path_not_blank(cls, value: str) -> str:
        """Validate gateway state-path strings."""

        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @field_validator("port")
    @classmethod
    def _port_range(cls, value: int) -> int:
        """Validate the live gateway port."""

        if value < 1 or value > 65535:
            raise ValueError("must be between 1 and 65535")
        return value


class RegistryMailboxFilesystemV1(_StrictRegistryModel):
    """Filesystem mailbox identity metadata for one published managed-agent session."""

    transport: Literal["filesystem"]
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


class RegistryMailboxStalwartV1(_StrictRegistryModel):
    """Stalwart mailbox identity metadata for one published managed-agent session."""

    transport: Literal["stalwart"]
    principal_id: str
    address: str
    bindings_version: str
    jmap_url: str
    management_url: str
    login_identity: str
    credential_ref: str

    @field_validator(
        "principal_id",
        "address",
        "bindings_version",
        "jmap_url",
        "management_url",
        "login_identity",
        "credential_ref",
    )
    @classmethod
    def _not_blank(cls, value: str) -> str:
        """Validate non-empty mailbox metadata."""

        if not value.strip():
            raise ValueError("must not be empty")
        return value


RegistryMailboxV1 = Annotated[
    RegistryMailboxFilesystemV1 | RegistryMailboxStalwartV1,
    Field(discriminator="transport"),
]


class LiveAgentRegistryRecordV2(_StrictRegistryModel):
    """Legacy v2 shared-registry ``record.json`` contract for one live agent."""

    schema_version: int = Field(default=LEGACY_REGISTRY_SCHEMA_VERSION)
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

    @model_validator(mode="after")
    def _validate_schema_and_identity(self) -> "LiveAgentRegistryRecordV2":
        """Validate schema version, canonical name, and lease ordering."""

        if self.schema_version != LEGACY_REGISTRY_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {LEGACY_REGISTRY_SCHEMA_VERSION}")

        try:
            normalized_agent_name = normalize_managed_agent_name(self.agent_name)
            normalized_agent_id = normalize_managed_agent_id(self.agent_id)
        except SessionManifestError as exc:
            raise ValueError(str(exc)) from exc
        if normalized_agent_name != self.agent_name:
            raise ValueError("agent_name must not include leading or trailing whitespace")
        if normalized_agent_id != self.agent_id:
            raise ValueError("agent_id must not include leading or trailing whitespace")

        published_at = _parse_iso8601_timestamp(self.published_at, field_name="published_at")
        lease_expires_at = _parse_iso8601_timestamp(
            self.lease_expires_at,
            field_name="lease_expires_at",
        )
        if lease_expires_at <= published_at:
            raise ValueError("lease_expires_at must be later than published_at")
        return self


class ManagedAgentRegistryRecordV3(_StrictRegistryModel):
    """Lifecycle-aware shared-registry ``record.json`` contract."""

    schema_version: int = Field(default=REGISTRY_SCHEMA_VERSION)
    agent_name: str
    agent_id: str
    generation_id: str
    lifecycle: RegistryLifecycleV1
    identity: RegistryIdentityV1
    runtime: RegistryRuntimeV1
    terminal: RegistryTerminalV2
    liveness: RegistryLivenessV1 | None = None
    gateway: RegistryGatewayV1 | None = None
    mailbox: RegistryMailboxV1 | None = None

    @field_validator("agent_name", "agent_id", "generation_id")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        """Validate non-empty top-level registry strings."""

        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @model_validator(mode="after")
    def _validate_schema_and_lifecycle(self) -> "ManagedAgentRegistryRecordV3":
        """Validate schema version, canonical identity, and lifecycle shape."""

        if self.schema_version != REGISTRY_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {REGISTRY_SCHEMA_VERSION}")

        try:
            normalized_agent_name = normalize_managed_agent_name(self.agent_name)
            normalized_agent_id = normalize_managed_agent_id(self.agent_id)
        except SessionManifestError as exc:
            raise ValueError(str(exc)) from exc
        if normalized_agent_name != self.agent_name:
            raise ValueError("agent_name must not include leading or trailing whitespace")
        if normalized_agent_id != self.agent_id:
            raise ValueError("agent_id must not include leading or trailing whitespace")

        if self.terminal.last_session_name is None:
            raise ValueError("terminal.last_session_name is required")

        if self.lifecycle.state in {"active", "relaunching"}:
            if self.liveness is None:
                raise ValueError("active or relaunching lifecycle records require liveness")
            if self.terminal.current_session_name is None:
                raise ValueError(
                    "active or relaunching lifecycle records require terminal.current_session_name"
                )
        else:
            if self.liveness is not None:
                raise ValueError("stopped or retired lifecycle records must not carry liveness")
            if self.gateway is not None:
                raise ValueError("stopped or retired lifecycle records must not carry gateway")
            if self.terminal.current_session_name is not None:
                raise ValueError(
                    "stopped or retired lifecycle records must clear terminal.current_session_name"
                )
        return self

    @property
    def is_active(self) -> bool:
        """Return whether the record represents an active live target."""

        return self.lifecycle.state == "active"

    @property
    def is_relaunchable(self) -> bool:
        """Return whether the record retains supported relaunch authority."""

        return self.lifecycle.relaunchable

    @property
    def published_at(self) -> str:
        """Return the active publication timestamp."""

        return self.require_liveness().published_at

    @property
    def lease_expires_at(self) -> str:
        """Return the active lease expiry timestamp."""

        return self.require_liveness().lease_expires_at

    def require_liveness(self) -> RegistryLivenessV1:
        """Return active liveness metadata or raise when the record is non-active."""

        if self.liveness is None:
            raise ValueError(
                f"managed-agent registry record `{self.agent_id}` has no active liveness metadata"
            )
        return self.liveness


def canonicalize_registry_agent_name(value: str) -> str:
    """Validate and normalize registry-facing agent input."""

    return normalize_managed_agent_name(value)


def parse_managed_agent_registry_record(payload: object) -> ManagedAgentRegistryRecordV3:
    """Parse one registry payload, upgrading legacy v2 records when needed."""

    if not isinstance(payload, dict):
        return ManagedAgentRegistryRecordV3.model_validate(payload)
    schema_version = payload.get("schema_version", LEGACY_REGISTRY_SCHEMA_VERSION)
    if schema_version == LEGACY_REGISTRY_SCHEMA_VERSION:
        legacy_record = LiveAgentRegistryRecordV2.model_validate(payload)
        return upgrade_live_agent_registry_record_v2(legacy_record)
    return ManagedAgentRegistryRecordV3.model_validate(payload)


def upgrade_live_agent_registry_record_v2(
    record: LiveAgentRegistryRecordV2,
) -> ManagedAgentRegistryRecordV3:
    """Map one legacy live-only record into the lifecycle-aware active shape."""

    return ManagedAgentRegistryRecordV3(
        agent_name=record.agent_name,
        agent_id=record.agent_id,
        generation_id=record.generation_id,
        lifecycle=RegistryLifecycleV1(
            state="active",
            relaunchable=record.runtime.session_root is not None,
            state_updated_at=record.published_at,
        ),
        identity=record.identity,
        runtime=record.runtime,
        terminal=RegistryTerminalV2(
            kind=record.terminal.kind,
            current_session_name=record.terminal.session_name,
            last_session_name=record.terminal.session_name,
        ),
        liveness=RegistryLivenessV1(
            published_at=record.published_at,
            lease_expires_at=record.lease_expires_at,
        ),
        gateway=record.gateway,
        mailbox=record.mailbox,
    )


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


LiveAgentRegistryRecordV2.model_rebuild()
ManagedAgentRegistryRecordV3.model_rebuild()
