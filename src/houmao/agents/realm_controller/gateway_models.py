"""Typed gateway boundary and persistence models.

This module centralizes the strict schemas used by gateway capability
publication, durable gateway storage, and the HTTP surface exposed by a live
gateway instance.
"""

from __future__ import annotations

from typing import Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from houmao.agents.realm_controller.models import BackendKind, CaoParsingMode

GatewayHost = Literal["127.0.0.1", "0.0.0.0"]
GatewayProtocolVersion = Literal["v1"]
GatewayRequestKind = Literal["submit_prompt", "interrupt"]
GatewayStoredRequestKind = Literal["submit_prompt", "interrupt", "mail_notifier_prompt"]
GatewayHealthState = Literal["healthy", "not_attached"]
GatewayConnectivityState = Literal["connected", "unavailable"]
GatewayRecoveryState = Literal["idle", "awaiting_rebind", "reconciliation_required"]
GatewayAdmissionState = Literal[
    "open",
    "blocked_unavailable",
    "blocked_reconciliation",
]
GatewaySurfaceEligibilityState = Literal["ready", "unknown", "not_ready"]
GatewayExecutionState = Literal["idle", "running"]
GatewayStoredRequestState = Literal[
    "accepted",
    "running",
    "completed",
    "failed",
]
GatewayJsonScalar: TypeAlias = str | int | float | bool | None
GatewayJsonValue: TypeAlias = (
    GatewayJsonScalar | list["GatewayJsonValue"] | dict[str, "GatewayJsonValue"]
)
GatewayJsonObject: TypeAlias = dict[str, GatewayJsonValue]

GATEWAY_ATTACH_SCHEMA_VERSION = 1
GATEWAY_PROTOCOL_VERSION: GatewayProtocolVersion = "v1"
GATEWAY_STATE_SCHEMA_VERSION = 1
GATEWAY_DESIRED_CONFIG_SCHEMA_VERSION = 1
GATEWAY_CURRENT_INSTANCE_SCHEMA_VERSION = 1
GATEWAY_REQUEST_SCHEMA_VERSION = 1
GATEWAY_MAIL_NOTIFIER_SCHEMA_VERSION = 1


class _StrictGatewayModel(BaseModel):
    """Base configuration for strict gateway payload models."""

    model_config = ConfigDict(extra="forbid", strict=True)


class BlueprintGatewayDefaults(_StrictGatewayModel):
    """Optional gateway defaults accepted from an agent blueprint."""

    host: GatewayHost | None = None
    port: int | None = None

    @field_validator("port")
    @classmethod
    def _validate_port(cls, value: int | None) -> int | None:
        """Validate the optional blueprint port range."""

        if value is None:
            return None
        if value < 1 or value > 65535:
            raise ValueError("must be between 1 and 65535")
        return value


class GatewayAttachBackendMetadataHeadlessV1(_StrictGatewayModel):
    """Attach metadata for tmux-backed headless runtimes."""

    session_id: str | None = None
    tool: str

    @field_validator("session_id")
    @classmethod
    def _optional_not_blank(cls, value: str | None) -> str | None:
        """Validate the optional persisted headless session identifier."""

        if value is None:
            return None
        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @field_validator("tool")
    @classmethod
    def _tool_not_blank(cls, value: str) -> str:
        """Validate the required headless tool name."""

        if not value.strip():
            raise ValueError("must not be empty")
        return value


class GatewayAttachBackendMetadataCaoV1(_StrictGatewayModel):
    """Attach metadata for runtime-owned `cao_rest` sessions."""

    api_base_url: str
    terminal_id: str
    profile_name: str
    profile_path: str
    parsing_mode: CaoParsingMode
    tmux_window_name: str | None = None

    @field_validator(
        "api_base_url",
        "terminal_id",
        "profile_name",
        "profile_path",
    )
    @classmethod
    def _not_blank(cls, value: str) -> str:
        """Validate that required CAO metadata fields are non-empty."""

        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @field_validator("tmux_window_name")
    @classmethod
    def _optional_tmux_window_name(cls, value: str | None) -> str | None:
        """Validate the optional tmux window name."""

        if value is None:
            return None
        if not value.strip():
            raise ValueError("must not be empty")
        return value


class GatewayAttachBackendMetadataHoumaoServerV1(_StrictGatewayModel):
    """Attach metadata for runtime-owned `houmao_server_rest` sessions."""

    api_base_url: str
    session_name: str
    terminal_id: str
    parsing_mode: CaoParsingMode
    tmux_window_name: str | None = None

    @field_validator("api_base_url", "session_name", "terminal_id")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @field_validator("tmux_window_name")
    @classmethod
    def _optional_tmux_window_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("must not be empty")
        return value


class GatewayAttachContractV1(_StrictGatewayModel):
    """Stable gateway attachability contract for one live tmux session."""

    schema_version: int = Field(default=GATEWAY_ATTACH_SCHEMA_VERSION)
    attach_identity: str
    backend: BackendKind
    tmux_session_name: str
    working_directory: str
    backend_metadata: (
        GatewayAttachBackendMetadataHeadlessV1
        | GatewayAttachBackendMetadataCaoV1
        | GatewayAttachBackendMetadataHoumaoServerV1
    )
    manifest_path: str | None = None
    agent_def_dir: str | None = None
    runtime_session_id: str | None = None
    desired_host: GatewayHost | None = None
    desired_port: int | None = None

    @field_validator(
        "attach_identity",
        "tmux_session_name",
        "working_directory",
        "manifest_path",
        "agent_def_dir",
        "runtime_session_id",
    )
    @classmethod
    def _optional_not_blank(cls, value: str | None) -> str | None:
        """Validate optional attach-contract string fields."""

        if value is None:
            return None
        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @field_validator("desired_port")
    @classmethod
    def _desired_port_range(cls, value: int | None) -> int | None:
        """Validate the optional desired gateway port."""

        if value is None:
            return None
        if value < 1 or value > 65535:
            raise ValueError("must be between 1 and 65535")
        return value

    @model_validator(mode="after")
    def _validate_schema_and_backend_metadata(self) -> "GatewayAttachContractV1":
        """Validate schema version and backend-specific metadata shape."""

        if self.schema_version != GATEWAY_ATTACH_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {GATEWAY_ATTACH_SCHEMA_VERSION}")
        if self.backend == "cao_rest":
            if not isinstance(self.backend_metadata, GatewayAttachBackendMetadataCaoV1):
                raise ValueError(
                    "backend_metadata must use the CAO attach schema for backend=cao_rest"
                )
        elif self.backend == "houmao_server_rest":
            if not isinstance(
                self.backend_metadata,
                GatewayAttachBackendMetadataHoumaoServerV1,
            ):
                raise ValueError(
                    "backend_metadata must use the houmao-server attach schema for "
                    "backend=houmao_server_rest"
                )
        elif self.backend in {
            "codex_headless",
            "claude_headless",
            "gemini_headless",
        }:
            if not isinstance(self.backend_metadata, GatewayAttachBackendMetadataHeadlessV1):
                raise ValueError(
                    "backend_metadata must use the headless attach schema "
                    "for tmux-backed headless backends"
                )
        else:
            raise ValueError(f"backend={self.backend!r} is not gateway-capable in v1")
        return self


class GatewayDesiredConfigV1(_StrictGatewayModel):
    """Persisted desired listener configuration for a gateway root."""

    schema_version: int = Field(default=GATEWAY_DESIRED_CONFIG_SCHEMA_VERSION)
    desired_host: GatewayHost | None = None
    desired_port: int | None = None

    @field_validator("desired_port")
    @classmethod
    def _port_range(cls, value: int | None) -> int | None:
        """Validate the optional desired listener port."""

        if value is None:
            return None
        if value < 1 or value > 65535:
            raise ValueError("must be between 1 and 65535")
        return value

    @model_validator(mode="after")
    def _validate_schema(self) -> "GatewayDesiredConfigV1":
        """Validate the desired-config schema version."""

        if self.schema_version != GATEWAY_DESIRED_CONFIG_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {GATEWAY_DESIRED_CONFIG_SCHEMA_VERSION}")
        return self


class GatewayCurrentInstanceV1(_StrictGatewayModel):
    """Ephemeral run-state metadata for one live gateway process."""

    schema_version: int = Field(default=GATEWAY_CURRENT_INSTANCE_SCHEMA_VERSION)
    protocol_version: GatewayProtocolVersion = Field(default=GATEWAY_PROTOCOL_VERSION)
    pid: int
    host: GatewayHost
    port: int
    managed_agent_instance_epoch: int
    managed_agent_instance_id: str | None = None

    @field_validator("pid", "port", "managed_agent_instance_epoch")
    @classmethod
    def _positive_int(cls, value: int) -> int:
        """Validate positive integer run-state counters."""

        if value <= 0:
            raise ValueError("must be > 0")
        return value

    @field_validator("managed_agent_instance_id")
    @classmethod
    def _optional_instance_id(cls, value: str | None) -> str | None:
        """Validate the optional managed-agent instance identifier."""

        if value is None:
            return None
        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @model_validator(mode="after")
    def _validate_schema(self) -> "GatewayCurrentInstanceV1":
        """Validate the current-instance schema version."""

        if self.schema_version != GATEWAY_CURRENT_INSTANCE_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {GATEWAY_CURRENT_INSTANCE_SCHEMA_VERSION}")
        return self


class GatewayHealthResponseV1(_StrictGatewayModel):
    """`GET /health` response."""

    protocol_version: GatewayProtocolVersion = Field(default=GATEWAY_PROTOCOL_VERSION)
    status: Literal["ok"] = "ok"


class GatewayRequestPayloadSubmitPromptV1(_StrictGatewayModel):
    """Public payload for `submit_prompt` requests."""

    prompt: str

    @field_validator("prompt")
    @classmethod
    def _prompt_not_blank(cls, value: str) -> str:
        """Validate that submitted prompts are non-empty."""

        if not value.strip():
            raise ValueError("must not be empty")
        return value


class GatewayRequestPayloadInterruptV1(_StrictGatewayModel):
    """Public payload for `interrupt` requests."""

    pass


class GatewayRequestCreateV1(_StrictGatewayModel):
    """`POST /v1/requests` request body."""

    schema_version: int = Field(default=GATEWAY_REQUEST_SCHEMA_VERSION)
    kind: GatewayRequestKind
    payload: GatewayRequestPayloadSubmitPromptV1 | GatewayRequestPayloadInterruptV1

    @model_validator(mode="after")
    def _validate_payload_shape(self) -> "GatewayRequestCreateV1":
        """Validate request schema version and payload-kind correspondence."""

        if self.schema_version != GATEWAY_REQUEST_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {GATEWAY_REQUEST_SCHEMA_VERSION}")
        if self.kind == "submit_prompt" and not isinstance(
            self.payload, GatewayRequestPayloadSubmitPromptV1
        ):
            raise ValueError("submit_prompt requires submit_prompt payload")
        if self.kind == "interrupt" and not isinstance(
            self.payload, GatewayRequestPayloadInterruptV1
        ):
            raise ValueError("interrupt requires interrupt payload")
        return self


class GatewayAcceptedRequestV1(_StrictGatewayModel):
    """Accepted queue record returned from `POST /v1/requests`."""

    request_id: str
    request_kind: GatewayRequestKind
    state: GatewayStoredRequestState
    accepted_at_utc: str
    queue_depth: int
    managed_agent_instance_epoch: int

    @field_validator("request_id", "accepted_at_utc")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        """Validate non-empty accepted-request identifiers and timestamps."""

        if not value.strip():
            raise ValueError("must not be empty")
        return value


class GatewayMailNotifierPutV1(_StrictGatewayModel):
    """`PUT /v1/mail-notifier` request body."""

    schema_version: int = Field(default=GATEWAY_MAIL_NOTIFIER_SCHEMA_VERSION)
    enabled: Literal[True] = True
    interval_seconds: int

    @field_validator("interval_seconds")
    @classmethod
    def _positive_interval_seconds(cls, value: int) -> int:
        """Validate a positive notifier polling interval."""

        if value <= 0:
            raise ValueError("must be > 0")
        return value

    @model_validator(mode="after")
    def _validate_schema(self) -> "GatewayMailNotifierPutV1":
        """Validate the notifier request schema version."""

        if self.schema_version != GATEWAY_MAIL_NOTIFIER_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {GATEWAY_MAIL_NOTIFIER_SCHEMA_VERSION}")
        return self


class GatewayMailNotifierStatusV1(_StrictGatewayModel):
    """`GET|PUT|DELETE /v1/mail-notifier` response body."""

    schema_version: int = Field(default=GATEWAY_MAIL_NOTIFIER_SCHEMA_VERSION)
    enabled: bool
    interval_seconds: int | None = None
    supported: bool
    support_error: str | None = None
    last_poll_at_utc: str | None = None
    last_notification_at_utc: str | None = None
    last_error: str | None = None

    @field_validator("interval_seconds")
    @classmethod
    def _optional_positive_interval(cls, value: int | None) -> int | None:
        """Validate the optional notifier interval."""

        if value is None:
            return None
        if value <= 0:
            raise ValueError("must be > 0")
        return value

    @field_validator(
        "support_error",
        "last_poll_at_utc",
        "last_notification_at_utc",
        "last_error",
    )
    @classmethod
    def _optional_not_blank_text(cls, value: str | None) -> str | None:
        """Validate optional notifier status text fields."""

        if value is None:
            return None
        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @model_validator(mode="after")
    def _validate_notifier_status(self) -> "GatewayMailNotifierStatusV1":
        """Validate notifier status invariants."""

        if self.schema_version != GATEWAY_MAIL_NOTIFIER_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {GATEWAY_MAIL_NOTIFIER_SCHEMA_VERSION}")
        if self.enabled and self.interval_seconds is None:
            raise ValueError("enabled notifier status requires interval_seconds")
        return self


class GatewayStatusV1(_StrictGatewayModel):
    """Stable gateway status shared by `state.json` and `GET /v1/status`."""

    schema_version: int = Field(default=GATEWAY_STATE_SCHEMA_VERSION)
    protocol_version: GatewayProtocolVersion = Field(default=GATEWAY_PROTOCOL_VERSION)
    attach_identity: str
    backend: BackendKind
    tmux_session_name: str
    gateway_health: GatewayHealthState
    managed_agent_connectivity: GatewayConnectivityState
    managed_agent_recovery: GatewayRecoveryState
    request_admission: GatewayAdmissionState
    terminal_surface_eligibility: GatewaySurfaceEligibilityState
    active_execution: GatewayExecutionState
    queue_depth: int
    gateway_host: GatewayHost | None = None
    gateway_port: int | None = None
    managed_agent_instance_epoch: int
    managed_agent_instance_id: str | None = None

    @field_validator(
        "attach_identity",
        "tmux_session_name",
        "managed_agent_instance_id",
    )
    @classmethod
    def _optional_not_blank(cls, value: str | None) -> str | None:
        """Validate optional status string fields."""

        if value is None:
            return None
        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @field_validator("queue_depth", "managed_agent_instance_epoch")
    @classmethod
    def _non_negative_int(cls, value: int) -> int:
        """Validate non-negative queue and epoch counters."""

        if value < 0:
            raise ValueError("must be >= 0")
        return value

    @field_validator("gateway_port")
    @classmethod
    def _gateway_port_range(cls, value: int | None) -> int | None:
        """Validate the optional published live gateway port."""

        if value is None:
            return None
        if value < 1 or value > 65535:
            raise ValueError("must be between 1 and 65535")
        return value

    @model_validator(mode="after")
    def _validate_schema(self) -> "GatewayStatusV1":
        """Validate schema version and offline-status invariants."""

        if self.schema_version != GATEWAY_STATE_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {GATEWAY_STATE_SCHEMA_VERSION}")
        if self.gateway_health == "not_attached":
            if self.gateway_host is not None or self.gateway_port is not None:
                raise ValueError("offline gateway status must omit live gateway host and port")
        return self


def format_gateway_validation_error(prefix: str, exc: ValidationError) -> str:
    """Format gateway validation errors for operator-facing messages.

    Parameters
    ----------
    prefix:
        Human-readable prefix describing the payload being validated.
    exc:
        Pydantic validation error raised for the payload.

    Returns
    -------
    str
        Concise message containing the first few field-level validation errors.
    """

    details: list[str] = []
    for issue in exc.errors(include_url=False):
        location = _format_error_location(issue.get("loc", ()))
        details.append(f"{location}: {issue.get('msg', 'validation failed')}")
        if len(details) >= 3:
            break
    joined = "; ".join(details) if details else "validation failed"
    return f"{prefix}: {joined}"


def _format_error_location(location: object) -> str:
    """Render one pydantic error location as a dotted field path."""

    if not isinstance(location, tuple) or not location:
        return "$"

    path = "$"
    for item in location:
        if isinstance(item, int):
            path += f"[{item}]"
            continue
        path += f".{item}"
    return path
