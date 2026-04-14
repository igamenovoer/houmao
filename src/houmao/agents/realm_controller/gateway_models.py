"""Typed gateway boundary and persistence models.

This module centralizes the strict schemas used by gateway capability
publication, durable gateway storage, and the HTTP surface exposed by a live
gateway instance.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Literal, TypeAlias

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    ValidationInfo,
    field_validator,
    model_validator,
)

from houmao.agents.model_selection import ModelConfig, ModelReasoningConfig, parse_reasoning_level
from houmao.agents.mailbox_runtime_models import MailboxTransport
from houmao.agents.realm_controller.models import BackendKind, CaoParsingMode
from houmao.mailbox.protocol import (
    HOUMAO_NO_REPLY_POLICY_VALUE,
    HOUMAO_OPERATOR_MAILBOX_REPLY_POLICY_VALUE,
)

GatewayHost = Literal["127.0.0.1", "0.0.0.0"]
GatewayProtocolVersion = Literal["v1"]
GatewayRequestKind = Literal["submit_prompt", "interrupt"]
GatewayStoredRequestKind = Literal["submit_prompt", "interrupt", "mail_notifier_prompt"]
GatewayReminderMode = Literal["one_off", "repeat"]
GatewayReminderDeliveryKind = Literal["prompt", "send_keys"]
GatewayReminderSelectionState = Literal["effective", "blocked"]
GatewayReminderDeliveryState = Literal["scheduled", "overdue", "executing"]
GatewayHealthState = Literal["healthy", "not_attached"]
GatewayConnectivityState = Literal["connected", "unavailable"]
GatewayChatSessionSelectorMode = Literal["auto", "new", "current", "tool_last_or_new", "exact"]
GatewayHeadlessStartupDefaultMode = Literal["new", "tool_last_or_new", "exact"]
GatewayRecoveryState = Literal["idle", "awaiting_rebind", "reconciliation_required"]
GatewayAdmissionState = Literal[
    "open",
    "blocked_unavailable",
    "blocked_reconciliation",
]
GatewaySurfaceEligibilityState = Literal["ready", "unknown", "not_ready"]
GatewayExecutionState = Literal["idle", "running"]
GatewayCurrentExecutionMode = Literal["detached_process", "tmux_auxiliary_window"]
GatewayStoredRequestState = Literal[
    "accepted",
    "running",
    "completed",
    "failed",
]
GatewayMailPostReplyPolicy = Literal["none", "operator_mailbox"]
GatewayMailReadFilter = Literal["any", "read", "unread"]
GatewayMailAnsweredFilter = Literal["any", "answered", "unanswered"]
GatewayMailLifecycleOperation = Literal["mark", "move", "archive"]
GatewayJsonScalar: TypeAlias = str | int | float | bool | None
GatewayJsonValue: TypeAlias = (
    GatewayJsonScalar | list["GatewayJsonValue"] | dict[str, "GatewayJsonValue"]
)
GatewayJsonObject: TypeAlias = dict[str, GatewayJsonValue]

GATEWAY_ATTACH_SCHEMA_VERSION = 1
GATEWAY_MANIFEST_SCHEMA_VERSION = 1
GATEWAY_PROTOCOL_VERSION: GatewayProtocolVersion = "v1"
GATEWAY_STATE_SCHEMA_VERSION = 1
GATEWAY_DESIRED_CONFIG_SCHEMA_VERSION = 1
GATEWAY_CURRENT_INSTANCE_SCHEMA_VERSION = 1
GATEWAY_REQUEST_SCHEMA_VERSION = 1
GATEWAY_PROMPT_CONTROL_SCHEMA_VERSION = 1
GATEWAY_NEXT_PROMPT_SESSION_SCHEMA_VERSION = 1
GATEWAY_REMINDER_SCHEMA_VERSION = 1
GATEWAY_MAIL_NOTIFIER_SCHEMA_VERSION = 1
GATEWAY_MAIL_SCHEMA_VERSION = 1
DEFAULT_GATEWAY_TUI_WATCH_POLL_INTERVAL_SECONDS = 0.5
DEFAULT_GATEWAY_TUI_STABILITY_THRESHOLD_SECONDS = 1.0
DEFAULT_GATEWAY_TUI_COMPLETION_STABILITY_SECONDS = 1.0
DEFAULT_GATEWAY_TUI_UNKNOWN_TO_STALLED_TIMEOUT_SECONDS = 30.0
DEFAULT_GATEWAY_TUI_STALE_ACTIVE_RECOVERY_SECONDS = 5.0
DEFAULT_GATEWAY_TUI_FINAL_STABLE_ACTIVE_RECOVERY_SECONDS = 20.0


def default_gateway_execution_mode_for_backend(
    backend: BackendKind,
) -> GatewayCurrentExecutionMode:
    """Return the default gateway execution mode for one managed backend."""

    if backend == "houmao_server_rest":
        return "tmux_auxiliary_window"
    return "detached_process"


def _validate_gateway_backend_metadata_shape(
    *,
    backend: BackendKind,
    backend_metadata: (
        GatewayAttachBackendMetadataHeadlessV1
        | GatewayAttachBackendMetadataCaoV1
        | GatewayAttachBackendMetadataHoumaoServerV1
    ),
    context: str,
) -> None:
    """Validate backend-specific gateway metadata against one backend kind."""

    if backend == "cao_rest":
        if not isinstance(backend_metadata, GatewayAttachBackendMetadataCaoV1):
            raise ValueError(f"{context} must use the CAO attach schema for backend=cao_rest")
        return
    if backend == "houmao_server_rest":
        if not isinstance(
            backend_metadata,
            GatewayAttachBackendMetadataHoumaoServerV1,
        ):
            raise ValueError(
                f"{context} must use the houmao-server attach schema for backend=houmao_server_rest"
            )
        return
    if backend in {
        "local_interactive",
        "codex_headless",
        "claude_headless",
        "gemini_headless",
    }:
        if not isinstance(backend_metadata, GatewayAttachBackendMetadataHeadlessV1):
            raise ValueError(
                f"{context} must use the headless attach schema for tmux-backed "
                "local/headless backends"
            )
        return
    raise ValueError(f"backend={backend!r} is not gateway-capable in v1")


def _parse_gateway_datetime(value: str) -> datetime:
    """Parse one gateway-protocol timestamp into a UTC datetime."""

    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


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


class GatewayTuiTrackingTimingConfigV1(_StrictGatewayModel):
    """Resolved gateway-owned TUI tracking timing configuration."""

    watch_poll_interval_seconds: float = DEFAULT_GATEWAY_TUI_WATCH_POLL_INTERVAL_SECONDS
    stability_threshold_seconds: float = DEFAULT_GATEWAY_TUI_STABILITY_THRESHOLD_SECONDS
    completion_stability_seconds: float = DEFAULT_GATEWAY_TUI_COMPLETION_STABILITY_SECONDS
    unknown_to_stalled_timeout_seconds: float = (
        DEFAULT_GATEWAY_TUI_UNKNOWN_TO_STALLED_TIMEOUT_SECONDS
    )
    stale_active_recovery_seconds: float = DEFAULT_GATEWAY_TUI_STALE_ACTIVE_RECOVERY_SECONDS
    final_stable_active_recovery_seconds: float = (
        DEFAULT_GATEWAY_TUI_FINAL_STABLE_ACTIVE_RECOVERY_SECONDS
    )

    @field_validator(
        "watch_poll_interval_seconds",
        "stability_threshold_seconds",
        "completion_stability_seconds",
        "unknown_to_stalled_timeout_seconds",
        "stale_active_recovery_seconds",
        "final_stable_active_recovery_seconds",
        mode="before",
    )
    @classmethod
    def _positive_float(cls, value: object) -> float:
        """Validate one required positive timing value."""

        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ValueError("must be numeric")
        normalized = float(value)
        if not math.isfinite(normalized) or normalized <= 0:
            raise ValueError("must be > 0")
        return normalized


class GatewayTuiTrackingTimingOverridesV1(_StrictGatewayModel):
    """Partial gateway-owned TUI tracking timing overrides."""

    watch_poll_interval_seconds: float | None = None
    stability_threshold_seconds: float | None = None
    completion_stability_seconds: float | None = None
    unknown_to_stalled_timeout_seconds: float | None = None
    stale_active_recovery_seconds: float | None = None
    final_stable_active_recovery_seconds: float | None = None

    @field_validator(
        "watch_poll_interval_seconds",
        "stability_threshold_seconds",
        "completion_stability_seconds",
        "unknown_to_stalled_timeout_seconds",
        "stale_active_recovery_seconds",
        "final_stable_active_recovery_seconds",
        mode="before",
    )
    @classmethod
    def _optional_positive_float(cls, value: object) -> float | None:
        """Validate one optional positive timing override."""

        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ValueError("must be numeric")
        normalized = float(value)
        if not math.isfinite(normalized) or normalized <= 0:
            raise ValueError("must be > 0")
        return normalized

    def has_values(self) -> bool:
        """Return whether any override value is present."""

        return any(
            value is not None
            for value in (
                self.watch_poll_interval_seconds,
                self.stability_threshold_seconds,
                self.completion_stability_seconds,
                self.unknown_to_stalled_timeout_seconds,
                self.stale_active_recovery_seconds,
                self.final_stable_active_recovery_seconds,
            )
        )


GatewayTuiTrackingTimingInput: TypeAlias = (
    GatewayTuiTrackingTimingConfigV1 | GatewayTuiTrackingTimingOverridesV1
)


def resolve_gateway_tui_tracking_timing_config(
    *,
    explicit: GatewayTuiTrackingTimingInput | None = None,
    desired: GatewayTuiTrackingTimingConfigV1 | None = None,
) -> GatewayTuiTrackingTimingConfigV1:
    """Resolve effective gateway TUI tracking timings from override, desired, and default."""

    defaults = GatewayTuiTrackingTimingConfigV1()
    return GatewayTuiTrackingTimingConfigV1(
        watch_poll_interval_seconds=_resolve_tui_timing_field(
            "watch_poll_interval_seconds",
            explicit=explicit,
            desired=desired,
            defaults=defaults,
        ),
        stability_threshold_seconds=_resolve_tui_timing_field(
            "stability_threshold_seconds",
            explicit=explicit,
            desired=desired,
            defaults=defaults,
        ),
        completion_stability_seconds=_resolve_tui_timing_field(
            "completion_stability_seconds",
            explicit=explicit,
            desired=desired,
            defaults=defaults,
        ),
        unknown_to_stalled_timeout_seconds=_resolve_tui_timing_field(
            "unknown_to_stalled_timeout_seconds",
            explicit=explicit,
            desired=desired,
            defaults=defaults,
        ),
        stale_active_recovery_seconds=_resolve_tui_timing_field(
            "stale_active_recovery_seconds",
            explicit=explicit,
            desired=desired,
            defaults=defaults,
        ),
        final_stable_active_recovery_seconds=_resolve_tui_timing_field(
            "final_stable_active_recovery_seconds",
            explicit=explicit,
            desired=desired,
            defaults=defaults,
        ),
    )


def _resolve_tui_timing_field(
    field_name: str,
    *,
    explicit: GatewayTuiTrackingTimingInput | None,
    desired: GatewayTuiTrackingTimingConfigV1 | None,
    defaults: GatewayTuiTrackingTimingConfigV1,
) -> float:
    """Resolve one gateway TUI timing field by precedence."""

    if explicit is not None:
        explicit_value = getattr(explicit, field_name)
        if explicit_value is not None:
            return float(explicit_value)
    if desired is not None:
        desired_value = getattr(desired, field_name)
        if desired_value is not None:
            return float(desired_value)
    return float(getattr(defaults, field_name))


class GatewayAttachBackendMetadataHeadlessV1(_StrictGatewayModel):
    """Attach metadata for tmux-backed headless runtimes."""

    session_id: str | None = None
    tool: str
    managed_api_base_url: str | None = None
    managed_agent_ref: str | None = None

    @field_validator("session_id", "managed_api_base_url", "managed_agent_ref")
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

    @model_validator(mode="after")
    def _validate_server_managed_fields(self) -> "GatewayAttachBackendMetadataHeadlessV1":
        """Require server-managed routing fields to appear as one complete group."""

        managed_fields = (
            self.managed_api_base_url is not None,
            self.managed_agent_ref is not None,
        )
        if any(managed_fields) and not all(managed_fields):
            raise ValueError("managed_api_base_url and managed_agent_ref must be set together")
        return self


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
        _validate_gateway_backend_metadata_shape(
            backend=self.backend,
            backend_metadata=self.backend_metadata,
            context="backend_metadata",
        )
        return self


class GatewayManifestV1(_StrictGatewayModel):
    """Derived outward-facing gateway bookkeeping for one session-owned gateway root."""

    schema_version: int = Field(default=GATEWAY_MANIFEST_SCHEMA_VERSION)
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
    gateway_pid: int | None = None
    gateway_host: GatewayHost | None = None
    gateway_port: int | None = None
    gateway_protocol_version: GatewayProtocolVersion | None = None
    gateway_execution_mode: GatewayCurrentExecutionMode | None = None
    gateway_tmux_window_id: str | None = None
    gateway_tmux_window_index: str | None = None
    gateway_tmux_pane_id: str | None = None

    @field_validator(
        "attach_identity",
        "tmux_session_name",
        "working_directory",
        "manifest_path",
        "agent_def_dir",
        "runtime_session_id",
        "gateway_tmux_window_id",
        "gateway_tmux_window_index",
        "gateway_tmux_pane_id",
    )
    @classmethod
    def _optional_not_blank(cls, value: str | None) -> str | None:
        """Validate required and optional manifest string fields."""

        if value is None:
            return None
        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @field_validator("desired_port", "gateway_port")
    @classmethod
    def _optional_port_range(cls, value: int | None) -> int | None:
        """Validate desired and live gateway listener ports."""

        if value is None:
            return None
        if value < 1 or value > 65535:
            raise ValueError("must be between 1 and 65535")
        return value

    @field_validator("gateway_pid")
    @classmethod
    def _optional_gateway_pid(cls, value: int | None) -> int | None:
        """Validate the optional published gateway pid."""

        if value is None:
            return None
        if value <= 0:
            raise ValueError("must be > 0")
        return value

    @model_validator(mode="after")
    def _validate_schema_and_live_fields(self) -> "GatewayManifestV1":
        """Validate schema version, backend metadata, and live publication shape."""

        if self.schema_version != GATEWAY_MANIFEST_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {GATEWAY_MANIFEST_SCHEMA_VERSION}")
        _validate_gateway_backend_metadata_shape(
            backend=self.backend,
            backend_metadata=self.backend_metadata,
            context="backend_metadata",
        )

        live_fields = (
            self.gateway_pid is not None,
            self.gateway_host is not None,
            self.gateway_port is not None,
            self.gateway_protocol_version is not None,
            self.gateway_execution_mode is not None,
        )
        if any(live_fields) and not all(live_fields):
            raise ValueError(
                "gateway_pid, gateway_host, gateway_port, gateway_protocol_version, and "
                "gateway_execution_mode must be set together"
            )

        tmux_fields = (
            self.gateway_tmux_window_id,
            self.gateway_tmux_window_index,
            self.gateway_tmux_pane_id,
        )
        if self.gateway_execution_mode is None:
            if any(value is not None for value in tmux_fields):
                raise ValueError(
                    "gateway tmux execution handle fields require gateway_execution_mode"
                )
            return self
        if self.gateway_execution_mode == "detached_process":
            if any(value is not None for value in tmux_fields):
                raise ValueError(
                    "detached_process gateway manifest must not include tmux execution handle fields"
                )
            return self
        if any(value is None for value in tmux_fields):
            raise ValueError(
                "tmux_auxiliary_window gateway manifest requires gateway_tmux_window_id, "
                "gateway_tmux_window_index, and gateway_tmux_pane_id"
            )
        if self.gateway_tmux_window_index == "0":
            raise ValueError("tmux auxiliary gateway window must not use window index 0")
        return self


class GatewayDesiredConfigV1(_StrictGatewayModel):
    """Persisted desired listener configuration for a gateway root."""

    schema_version: int = Field(default=GATEWAY_DESIRED_CONFIG_SCHEMA_VERSION)
    desired_host: GatewayHost | None = None
    desired_port: int | None = None
    desired_execution_mode: GatewayCurrentExecutionMode = Field(default="detached_process")
    desired_tui_tracking_timings: GatewayTuiTrackingTimingConfigV1 | None = None

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
    execution_mode: GatewayCurrentExecutionMode = Field(default="detached_process")
    tmux_window_id: str | None = None
    tmux_window_index: str | None = None
    tmux_pane_id: str | None = None
    managed_agent_instance_epoch: int
    managed_agent_instance_id: str | None = None

    @field_validator("pid", "port", "managed_agent_instance_epoch")
    @classmethod
    def _positive_int(cls, value: int) -> int:
        """Validate positive integer run-state counters."""

        if value <= 0:
            raise ValueError("must be > 0")
        return value

    @field_validator(
        "managed_agent_instance_id",
        "tmux_window_id",
        "tmux_window_index",
        "tmux_pane_id",
    )
    @classmethod
    def _optional_not_blank(cls, value: str | None) -> str | None:
        """Validate optional current-instance string fields."""

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
        if self.execution_mode == "detached_process":
            if any(
                value is not None
                for value in (self.tmux_window_id, self.tmux_window_index, self.tmux_pane_id)
            ):
                raise ValueError(
                    "detached_process current-instance payload must not include tmux execution "
                    "handle fields"
                )
            return self
        if any(
            value is None
            for value in (self.tmux_window_id, self.tmux_window_index, self.tmux_pane_id)
        ):
            raise ValueError(
                "tmux_auxiliary_window current-instance payload requires tmux_window_id, "
                "tmux_window_index, and tmux_pane_id"
            )
        if self.tmux_window_index == "0":
            raise ValueError("tmux auxiliary gateway window must not use window index 0")
        return self


class GatewayHealthResponseV1(_StrictGatewayModel):
    """`GET /health` response."""

    protocol_version: GatewayProtocolVersion = Field(default=GATEWAY_PROTOCOL_VERSION)
    status: Literal["ok"] = "ok"


class GatewayChatSessionSelectorV1(_StrictGatewayModel):
    """Explicit chat-session selector for prompt submission."""

    mode: GatewayChatSessionSelectorMode
    id: str | None = None

    @field_validator("id")
    @classmethod
    def _optional_id_not_blank(cls, value: str | None) -> str | None:
        """Validate one optional provider session id."""

        if value is None:
            return None
        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @model_validator(mode="after")
    def _validate_selector(self) -> "GatewayChatSessionSelectorV1":
        """Require `id` only for exact selector mode."""

        if self.mode == "exact":
            if self.id is None:
                raise ValueError("chat_session.id is required when mode=exact")
            return self
        if self.id is not None:
            raise ValueError("chat_session.id is only allowed when mode=exact")
        return self


class GatewayExecutionModelReasoningV1(_StrictGatewayModel):
    """Normalized reasoning override for one request-scoped execution model."""

    level: int

    @field_validator("level")
    @classmethod
    def _validate_level(cls, value: int) -> int:
        """Require one normalized reasoning level."""

        parsed = parse_reasoning_level(value, source="execution.model.reasoning")
        assert parsed is not None
        return parsed


class GatewayExecutionModelV1(_StrictGatewayModel):
    """Request-scoped unified execution-model payload."""

    name: str | None = None
    reasoning: GatewayExecutionModelReasoningV1 | None = None

    @field_validator("name")
    @classmethod
    def _optional_name_not_blank(cls, value: str | None) -> str | None:
        """Require a non-empty model name when present."""

        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped

    @model_validator(mode="after")
    def _validate_not_empty(self) -> "GatewayExecutionModelV1":
        """Require at least one normalized execution-model field."""

        if self.name is None and self.reasoning is None:
            raise ValueError("execution.model must include `name` or `reasoning`")
        return self

    def to_model_config(self) -> ModelConfig:
        """Return the normalized execution-model config."""

        return ModelConfig(
            name=self.name,
            reasoning=(
                ModelReasoningConfig(level=self.reasoning.level)
                if self.reasoning is not None
                else None
            ),
        )

    @classmethod
    def from_model_config(cls, config: ModelConfig | None) -> "GatewayExecutionModelV1 | None":
        """Build one request payload from a normalized config."""

        if config is None or config.is_empty():
            return None
        return cls(
            name=config.name,
            reasoning=(
                GatewayExecutionModelReasoningV1(level=config.reasoning.level)
                if config.reasoning is not None
                else None
            ),
        )


class GatewayExecutionOverrideV1(_StrictGatewayModel):
    """Request-scoped execution override payload."""

    model: GatewayExecutionModelV1

    def to_model_config(self) -> ModelConfig:
        """Return the normalized request-scoped model override."""

        return self.model.to_model_config()

    @classmethod
    def from_model_config(cls, config: ModelConfig | None) -> "GatewayExecutionOverrideV1 | None":
        """Build one execution-override payload from a normalized config."""

        model_payload = GatewayExecutionModelV1.from_model_config(config)
        if model_payload is None:
            return None
        return cls(model=model_payload)


class GatewayHeadlessCurrentChatSessionV1(_StrictGatewayModel):
    """Pinned current provider session for one headless managed agent."""

    id: str

    @field_validator("id")
    @classmethod
    def _id_not_blank(cls, value: str) -> str:
        """Validate one pinned provider session id."""

        if not value.strip():
            raise ValueError("must not be empty")
        return value


class GatewayHeadlessStartupDefaultV1(_StrictGatewayModel):
    """Persisted first-chat fallback for one headless managed agent."""

    mode: GatewayHeadlessStartupDefaultMode
    id: str | None = None

    @field_validator("id")
    @classmethod
    def _optional_id_not_blank(cls, value: str | None) -> str | None:
        """Validate one optional exact startup session id."""

        if value is None:
            return None
        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @model_validator(mode="after")
    def _validate_startup_default(self) -> "GatewayHeadlessStartupDefaultV1":
        """Require `id` only for exact startup-default mode."""

        if self.mode == "exact":
            if self.id is None:
                raise ValueError("startup_default.id is required when mode=exact")
            return self
        if self.id is not None:
            raise ValueError("startup_default.id is only allowed when mode=exact")
        return self


class GatewayHeadlessNextPromptOverrideV1(_StrictGatewayModel):
    """One-shot override for the next accepted auto prompt."""

    mode: Literal["new"]


class GatewayHeadlessChatSessionStateV1(_StrictGatewayModel):
    """Live headless chat-session state exposed by the gateway."""

    current: GatewayHeadlessCurrentChatSessionV1 | None = None
    startup_default: GatewayHeadlessStartupDefaultV1
    next_prompt_override: GatewayHeadlessNextPromptOverrideV1 | None = None


class GatewayRequestPayloadSubmitPromptV1(_StrictGatewayModel):
    """Public payload for `submit_prompt` requests."""

    prompt: str
    turn_id: str | None = None
    chat_session: GatewayChatSessionSelectorV1 | None = None
    execution: GatewayExecutionOverrideV1 | None = None

    @field_validator("prompt", "turn_id")
    @classmethod
    def _optional_not_blank(cls, value: str | None) -> str | None:
        """Validate submitted prompt strings when present."""

        if value is None:
            return None
        if not value.strip():
            raise ValueError("must not be empty")
        return value


class GatewayRequestPayloadInterruptV1(_StrictGatewayModel):
    """Public payload for `interrupt` requests."""

    pass


class GatewayControlInputRequestV1(_StrictGatewayModel):
    """`POST /v1/control/send-keys` request body."""

    sequence: str
    escape_special_keys: bool = False

    @field_validator("sequence")
    @classmethod
    def _sequence_not_blank(cls, value: str) -> str:
        """Validate the raw control-input sequence."""

        if not value.strip():
            raise ValueError("must not be empty")
        return value


class GatewayControlInputResultV1(_StrictGatewayModel):
    """Successful raw control-input response body."""

    status: Literal["ok"] = "ok"
    action: Literal["control_input"] = "control_input"
    detail: str

    @field_validator("detail")
    @classmethod
    def _detail_not_blank(cls, value: str) -> str:
        """Validate the successful control-input detail string."""

        if not value.strip():
            raise ValueError("must not be empty")
        return value


class GatewayPromptControlRequestV1(_StrictGatewayModel):
    """`POST /v1/control/prompt` request body."""

    schema_version: int = Field(default=GATEWAY_PROMPT_CONTROL_SCHEMA_VERSION)
    prompt: str
    force: bool = False
    chat_session: GatewayChatSessionSelectorV1 | None = None
    execution: GatewayExecutionOverrideV1 | None = None

    @field_validator("prompt")
    @classmethod
    def _prompt_not_blank(cls, value: str) -> str:
        """Validate the direct-control prompt text."""

        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @model_validator(mode="after")
    def _validate_schema(self) -> "GatewayPromptControlRequestV1":
        """Validate the direct prompt-control schema version."""

        if self.schema_version != GATEWAY_PROMPT_CONTROL_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {GATEWAY_PROMPT_CONTROL_SCHEMA_VERSION}")
        return self


class GatewayPromptControlResultV1(_StrictGatewayModel):
    """Successful direct prompt-control response body."""

    status: Literal["ok"] = "ok"
    action: Literal["submit_prompt"] = "submit_prompt"
    sent: Literal[True] = True
    forced: bool
    detail: str

    @field_validator("detail")
    @classmethod
    def _detail_not_blank(cls, value: str) -> str:
        """Validate the successful prompt-control detail string."""

        if not value.strip():
            raise ValueError("must not be empty")
        return value


class GatewayHeadlessNextPromptSessionRequestV1(_StrictGatewayModel):
    """`POST /v1/control/headless/next-prompt-session` request body."""

    schema_version: int = Field(default=GATEWAY_NEXT_PROMPT_SESSION_SCHEMA_VERSION)
    mode: Literal["new"]

    @model_validator(mode="after")
    def _validate_schema(self) -> "GatewayHeadlessNextPromptSessionRequestV1":
        """Validate the next-prompt-session schema version."""

        if self.schema_version != GATEWAY_NEXT_PROMPT_SESSION_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {GATEWAY_NEXT_PROMPT_SESSION_SCHEMA_VERSION}")
        return self


class GatewayPromptControlErrorV1(_StrictGatewayModel):
    """Structured refusal payload for direct prompt control."""

    status: Literal["error"] = "error"
    action: Literal["submit_prompt"] = "submit_prompt"
    sent: Literal[False] = False
    forced: bool
    error_code: str
    detail: str

    @field_validator("error_code", "detail")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        """Validate non-empty prompt-control error fields."""

        if not value.strip():
            raise ValueError("must not be empty")
        return value


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


class GatewayReminderSendKeysV1(_StrictGatewayModel):
    """Reminder-local raw control-input payload."""

    sequence: str
    ensure_enter: bool = True

    @field_validator("sequence")
    @classmethod
    def _not_blank_sequence(cls, value: str) -> str:
        """Validate non-empty reminder send-keys payloads."""

        if not value.strip():
            raise ValueError("must not be empty")
        return value


class GatewayReminderDefinitionV1(_StrictGatewayModel):
    """Shared mutable reminder fields used by create and update routes."""

    mode: GatewayReminderMode
    title: str
    prompt: str | None = None
    send_keys: GatewayReminderSendKeysV1 | None = None
    ranking: int
    paused: bool = False
    start_after_seconds: int | float | None = None
    deliver_at_utc: str | None = None
    interval_seconds: int | float | None = None

    @field_validator("title", "prompt", "deliver_at_utc")
    @classmethod
    def _optional_not_blank_text(cls, value: str | None) -> str | None:
        """Validate non-empty reminder text and timestamp fields."""

        if value is None:
            return None
        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @field_validator("deliver_at_utc")
    @classmethod
    def _validate_deliver_at_utc(cls, value: str | None) -> str | None:
        """Validate the optional absolute delivery timestamp."""

        if value is None:
            return None
        _parse_gateway_datetime(value)
        return value

    @field_validator("start_after_seconds", "interval_seconds")
    @classmethod
    def _positive_finite_seconds(cls, value: int | float | None) -> int | float | None:
        """Validate one optional positive finite seconds value."""

        if value is None:
            return None
        numeric_value = float(value)
        if not math.isfinite(numeric_value):
            raise ValueError("must be finite")
        if numeric_value <= 0:
            raise ValueError("must be > 0")
        return value

    @model_validator(mode="after")
    def _validate_shape(self) -> "GatewayReminderDefinitionV1":
        """Validate reminder scheduling shape and mode-specific fields."""

        if (self.prompt is None) == (self.send_keys is None):
            raise ValueError("exactly one of prompt or send_keys must be set")
        if (self.start_after_seconds is None) == (self.deliver_at_utc is None):
            raise ValueError("exactly one of start_after_seconds or deliver_at_utc must be set")
        if self.mode == "repeat" and self.interval_seconds is None:
            raise ValueError("repeat reminders require interval_seconds")
        if self.mode == "one_off" and self.interval_seconds is not None:
            raise ValueError("one_off reminders must not include interval_seconds")
        return self


class GatewayReminderCreateBatchV1(_StrictGatewayModel):
    """`POST /v1/reminders` request body."""

    schema_version: int = Field(default=GATEWAY_REMINDER_SCHEMA_VERSION)
    reminders: list[GatewayReminderDefinitionV1]

    @model_validator(mode="after")
    def _validate_schema(self) -> "GatewayReminderCreateBatchV1":
        """Validate the reminder-create batch schema version and contents."""

        if self.schema_version != GATEWAY_REMINDER_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {GATEWAY_REMINDER_SCHEMA_VERSION}")
        if not self.reminders:
            raise ValueError("reminders must not be empty")
        return self


class GatewayReminderPutV1(GatewayReminderDefinitionV1):
    """`PUT /v1/reminders/{reminder_id}` request body."""

    schema_version: int = Field(default=GATEWAY_REMINDER_SCHEMA_VERSION)

    @model_validator(mode="after")
    def _validate_schema(self) -> "GatewayReminderPutV1":
        """Validate the reminder-update schema version."""

        if self.schema_version != GATEWAY_REMINDER_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {GATEWAY_REMINDER_SCHEMA_VERSION}")
        return self


class GatewayReminderV1(_StrictGatewayModel):
    """One live reminder returned by gateway reminder routes."""

    schema_version: int = Field(default=GATEWAY_REMINDER_SCHEMA_VERSION)
    reminder_id: str
    mode: GatewayReminderMode
    delivery_kind: GatewayReminderDeliveryKind
    title: str
    prompt: str | None = None
    send_keys: GatewayReminderSendKeysV1 | None = None
    ranking: int
    paused: bool
    selection_state: GatewayReminderSelectionState
    delivery_state: GatewayReminderDeliveryState
    created_at_utc: str
    next_due_at_utc: str
    interval_seconds: int | float | None = None
    last_started_at_utc: str | None = None
    blocked_by_reminder_id: str | None = None

    @field_validator(
        "reminder_id",
        "title",
        "prompt",
        "created_at_utc",
        "next_due_at_utc",
        "last_started_at_utc",
        "blocked_by_reminder_id",
    )
    @classmethod
    def _optional_not_blank(cls, value: str | None) -> str | None:
        """Validate required and optional reminder text fields."""

        if value is None:
            return None
        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @field_validator("created_at_utc", "next_due_at_utc", "last_started_at_utc")
    @classmethod
    def _optional_valid_timestamp(cls, value: str | None) -> str | None:
        """Validate reminder response timestamps."""

        if value is None:
            return None
        _parse_gateway_datetime(value)
        return value

    @field_validator("interval_seconds")
    @classmethod
    def _optional_positive_interval(cls, value: int | float | None) -> int | float | None:
        """Validate the optional repeat interval."""

        if value is None:
            return None
        numeric_value = float(value)
        if not math.isfinite(numeric_value):
            raise ValueError("must be finite")
        if numeric_value <= 0:
            raise ValueError("must be > 0")
        return value

    @model_validator(mode="after")
    def _validate_reminder_shape(self) -> "GatewayReminderV1":
        """Validate response invariants for one reminder."""

        if self.schema_version != GATEWAY_REMINDER_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {GATEWAY_REMINDER_SCHEMA_VERSION}")
        if (self.prompt is None) == (self.send_keys is None):
            raise ValueError("exactly one of prompt or send_keys must be set")
        if self.mode == "repeat" and self.interval_seconds is None:
            raise ValueError("repeat reminders require interval_seconds")
        if self.mode == "one_off" and self.interval_seconds is not None:
            raise ValueError("one_off reminders must not include interval_seconds")
        if self.delivery_kind == "prompt" and self.prompt is None:
            raise ValueError("delivery_kind=prompt requires prompt")
        if self.delivery_kind == "send_keys" and self.send_keys is None:
            raise ValueError("delivery_kind=send_keys requires send_keys")
        if self.selection_state == "effective" and self.blocked_by_reminder_id is not None:
            raise ValueError("effective reminders must not include blocked_by_reminder_id")
        if self.selection_state == "blocked" and self.blocked_by_reminder_id is None:
            raise ValueError("blocked reminders require blocked_by_reminder_id")
        return self


class GatewayReminderCreateResultV1(_StrictGatewayModel):
    """`POST /v1/reminders` response body."""

    schema_version: int = Field(default=GATEWAY_REMINDER_SCHEMA_VERSION)
    effective_reminder_id: str | None = None
    reminders: list[GatewayReminderV1]

    @field_validator("effective_reminder_id")
    @classmethod
    def _optional_not_blank_reminder_id(cls, value: str | None) -> str | None:
        """Validate one optional effective reminder identifier."""

        if value is None:
            return None
        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @model_validator(mode="after")
    def _validate_schema(self) -> "GatewayReminderCreateResultV1":
        """Validate the reminder-create result schema version."""

        if self.schema_version != GATEWAY_REMINDER_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {GATEWAY_REMINDER_SCHEMA_VERSION}")
        return self


class GatewayReminderListV1(_StrictGatewayModel):
    """`GET /v1/reminders` response body."""

    schema_version: int = Field(default=GATEWAY_REMINDER_SCHEMA_VERSION)
    effective_reminder_id: str | None = None
    reminders: list[GatewayReminderV1]

    @field_validator("effective_reminder_id")
    @classmethod
    def _optional_not_blank_reminder_id(cls, value: str | None) -> str | None:
        """Validate one optional effective reminder identifier."""

        if value is None:
            return None
        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @model_validator(mode="after")
    def _validate_schema(self) -> "GatewayReminderListV1":
        """Validate the reminder list schema version."""

        if self.schema_version != GATEWAY_REMINDER_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {GATEWAY_REMINDER_SCHEMA_VERSION}")
        return self


class GatewayReminderDeleteResultV1(_StrictGatewayModel):
    """`DELETE /v1/reminders/{reminder_id}` response body."""

    schema_version: int = Field(default=GATEWAY_REMINDER_SCHEMA_VERSION)
    status: Literal["ok"] = "ok"
    action: Literal["delete_reminder"] = "delete_reminder"
    reminder_id: str
    deleted: Literal[True] = True
    detail: str

    @field_validator("reminder_id", "detail")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        """Validate non-empty delete-response fields."""

        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @model_validator(mode="after")
    def _validate_schema(self) -> "GatewayReminderDeleteResultV1":
        """Validate the reminder deletion schema version."""

        if self.schema_version != GATEWAY_REMINDER_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {GATEWAY_REMINDER_SCHEMA_VERSION}")
        return self


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


class GatewayMailboxParticipantV1(_StrictGatewayModel):
    """Normalized mailbox participant identity."""

    address: str
    display_name: str | None = None
    principal_id: str | None = None

    @field_validator("address", "display_name", "principal_id")
    @classmethod
    def _optional_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("must not be empty")
        return value


class GatewayMailboxAttachmentV1(_StrictGatewayModel):
    """Normalized delivered attachment metadata."""

    attachment_id: str
    kind: str
    media_type: str
    locator: str | None = None
    size_bytes: int | None = None
    sha256: str | None = None
    label: str | None = None

    @field_validator("attachment_id", "kind", "media_type", "locator", "sha256", "label")
    @classmethod
    def _optional_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @field_validator("size_bytes")
    @classmethod
    def _non_negative_size(cls, value: int | None) -> int | None:
        if value is None:
            return None
        if value < 0:
            raise ValueError("must be >= 0")
        return value


class GatewayMailboxMessageV1(_StrictGatewayModel):
    """Normalized mailbox message metadata shared across mailbox routes."""

    message_ref: str
    thread_ref: str | None = None
    created_at_utc: str
    subject: str
    read: bool | None = None
    answered: bool | None = None
    archived: bool | None = None
    box: str | None = None
    unread: bool | None = None
    body_preview: str | None = None
    body_text: str | None = None
    sender: GatewayMailboxParticipantV1
    to: list[GatewayMailboxParticipantV1]
    cc: list[GatewayMailboxParticipantV1] = Field(default_factory=list)
    reply_to: list[GatewayMailboxParticipantV1] = Field(default_factory=list)
    attachments: list[GatewayMailboxAttachmentV1] = Field(default_factory=list)

    @field_validator("message_ref", "thread_ref", "created_at_utc", "subject", "box")
    @classmethod
    def _optional_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @field_validator("body_preview", "body_text")
    @classmethod
    def _optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if "\x00" in value:
            raise ValueError("must not contain NUL bytes")
        return value


class GatewayMailStatusV1(_StrictGatewayModel):
    """`GET /v1/mail/status` response body."""

    schema_version: int = Field(default=GATEWAY_MAIL_SCHEMA_VERSION)
    transport: MailboxTransport
    principal_id: str
    address: str
    bindings_version: str

    @field_validator("principal_id", "address", "bindings_version")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @model_validator(mode="after")
    def _validate_schema(self) -> "GatewayMailStatusV1":
        if self.schema_version != GATEWAY_MAIL_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {GATEWAY_MAIL_SCHEMA_VERSION}")
        return self


class GatewayMailListRequestV1(_StrictGatewayModel):
    """`POST /v1/mail/list` request body."""

    schema_version: int = Field(default=GATEWAY_MAIL_SCHEMA_VERSION)
    box: str = "inbox"
    read_state: GatewayMailReadFilter = "any"
    answered_state: GatewayMailAnsweredFilter = "any"
    archived: bool | None = None
    limit: int | None = None
    since: str | None = None
    include_body: bool = False

    @field_validator("limit")
    @classmethod
    def _positive_limit(cls, value: int | None) -> int | None:
        if value is None:
            return None
        if value <= 0:
            raise ValueError("must be > 0")
        return value

    @field_validator("box", "since")
    @classmethod
    def _optional_not_blank_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("must not be empty")
        return value.strip()

    @model_validator(mode="after")
    def _validate_schema(self) -> "GatewayMailListRequestV1":
        if self.schema_version != GATEWAY_MAIL_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {GATEWAY_MAIL_SCHEMA_VERSION}")
        return self


class GatewayMailListResponseV1(_StrictGatewayModel):
    """`POST /v1/mail/list` response body."""

    schema_version: int = Field(default=GATEWAY_MAIL_SCHEMA_VERSION)
    transport: MailboxTransport
    principal_id: str
    address: str
    box: str
    message_count: int
    open_count: int
    unread_count: int
    messages: list[GatewayMailboxMessageV1]

    @field_validator("principal_id", "address", "box")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value.strip()

    @field_validator("message_count", "open_count", "unread_count")
    @classmethod
    def _non_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("must be >= 0")
        return value

    @model_validator(mode="after")
    def _validate_response(self) -> "GatewayMailListResponseV1":
        if self.schema_version != GATEWAY_MAIL_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {GATEWAY_MAIL_SCHEMA_VERSION}")
        if self.unread_count > self.message_count:
            raise ValueError("unread_count must be <= message_count")
        if self.open_count > self.message_count:
            raise ValueError("open_count must be <= message_count")
        return self


class GatewayMailMessageRequestV1(_StrictGatewayModel):
    """`POST /v1/mail/peek|read` request body."""

    schema_version: int = Field(default=GATEWAY_MAIL_SCHEMA_VERSION)
    message_ref: str
    box: str | None = None

    @field_validator("message_ref", "box")
    @classmethod
    def _optional_not_blank_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("must not be empty")
        return value.strip()

    @model_validator(mode="after")
    def _validate_schema(self) -> "GatewayMailMessageRequestV1":
        if self.schema_version != GATEWAY_MAIL_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {GATEWAY_MAIL_SCHEMA_VERSION}")
        return self


class GatewayMailMessageResponseV1(_StrictGatewayModel):
    """`POST /v1/mail/peek|read` response body."""

    schema_version: int = Field(default=GATEWAY_MAIL_SCHEMA_VERSION)
    operation: Literal["peek", "read"]
    transport: MailboxTransport
    principal_id: str
    address: str
    message: GatewayMailboxMessageV1

    @field_validator("principal_id", "address")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value.strip()

    @model_validator(mode="after")
    def _validate_schema(self) -> "GatewayMailMessageResponseV1":
        if self.schema_version != GATEWAY_MAIL_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {GATEWAY_MAIL_SCHEMA_VERSION}")
        return self


class GatewayMailMarkRequestV1(_StrictGatewayModel):
    """`POST /v1/mail/mark` request body."""

    schema_version: int = Field(default=GATEWAY_MAIL_SCHEMA_VERSION)
    message_refs: list[str]
    read: bool | None = None
    answered: bool | None = None
    archived: bool | None = None

    @field_validator("message_refs")
    @classmethod
    def _message_refs_not_blank(cls, value: list[str]) -> list[str]:
        normalized = [item.strip() for item in value if isinstance(item, str) and item.strip()]
        if len(normalized) != len(value):
            raise ValueError("must contain only non-empty strings")
        if not normalized:
            raise ValueError("must include at least one message reference")
        if len(set(normalized)) != len(normalized):
            raise ValueError("must not contain duplicate message references")
        return normalized

    @model_validator(mode="after")
    def _validate_schema(self) -> "GatewayMailMarkRequestV1":
        if self.schema_version != GATEWAY_MAIL_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {GATEWAY_MAIL_SCHEMA_VERSION}")
        if self.read is self.answered is self.archived is None:
            raise ValueError("mark request must set at least one state field")
        return self


class GatewayMailMoveRequestV1(_StrictGatewayModel):
    """`POST /v1/mail/move` request body."""

    schema_version: int = Field(default=GATEWAY_MAIL_SCHEMA_VERSION)
    message_refs: list[str]
    destination_box: str

    @field_validator("message_refs")
    @classmethod
    def _message_refs_not_blank(cls, value: list[str]) -> list[str]:
        normalized = [item.strip() for item in value if isinstance(item, str) and item.strip()]
        if len(normalized) != len(value):
            raise ValueError("must contain only non-empty strings")
        if not normalized:
            raise ValueError("must include at least one message reference")
        if len(set(normalized)) != len(normalized):
            raise ValueError("must not contain duplicate message references")
        return normalized

    @field_validator("destination_box")
    @classmethod
    def _destination_box_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value.strip()

    @model_validator(mode="after")
    def _validate_schema(self) -> "GatewayMailMoveRequestV1":
        if self.schema_version != GATEWAY_MAIL_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {GATEWAY_MAIL_SCHEMA_VERSION}")
        return self


class GatewayMailArchiveRequestV1(_StrictGatewayModel):
    """`POST /v1/mail/archive` request body."""

    schema_version: int = Field(default=GATEWAY_MAIL_SCHEMA_VERSION)
    message_refs: list[str]

    @field_validator("message_refs")
    @classmethod
    def _message_refs_not_blank(cls, value: list[str]) -> list[str]:
        normalized = [item.strip() for item in value if isinstance(item, str) and item.strip()]
        if len(normalized) != len(value):
            raise ValueError("must contain only non-empty strings")
        if not normalized:
            raise ValueError("must include at least one message reference")
        if len(set(normalized)) != len(normalized):
            raise ValueError("must not contain duplicate message references")
        return normalized

    @model_validator(mode="after")
    def _validate_schema(self) -> "GatewayMailArchiveRequestV1":
        if self.schema_version != GATEWAY_MAIL_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {GATEWAY_MAIL_SCHEMA_VERSION}")
        return self


class GatewayMailAttachmentUploadV1(_StrictGatewayModel):
    """Local attachment input accepted by shared mailbox send/reply routes."""

    path: str
    label: str | None = None

    @field_validator("path", "label")
    @classmethod
    def _optional_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("must not be empty")
        return value


class GatewayMailSendRequestV1(_StrictGatewayModel):
    """`POST /v1/mail/send` request body."""

    schema_version: int = Field(default=GATEWAY_MAIL_SCHEMA_VERSION)
    to: list[str]
    cc: list[str] = Field(default_factory=list)
    subject: str
    body_content: str
    attachments: list[GatewayMailAttachmentUploadV1] = Field(default_factory=list)

    @field_validator("to", "cc")
    @classmethod
    def _validate_recipients(cls, value: list[str], info: ValidationInfo) -> list[str]:
        normalized = [item.strip() for item in value if isinstance(item, str) and item.strip()]
        if info.field_name == "to" and not normalized:
            raise ValueError("must include at least one recipient")
        if len(normalized) != len(value):
            raise ValueError("must contain only non-empty strings")
        return normalized

    @field_validator("subject")
    @classmethod
    def _subject_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @field_validator("body_content")
    @classmethod
    def _body_no_nul(cls, value: str) -> str:
        if "\x00" in value:
            raise ValueError("must not contain NUL bytes")
        return value

    @model_validator(mode="after")
    def _validate_schema(self) -> "GatewayMailSendRequestV1":
        if self.schema_version != GATEWAY_MAIL_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {GATEWAY_MAIL_SCHEMA_VERSION}")
        return self


class GatewayMailPostRequestV1(_StrictGatewayModel):
    """`POST /v1/mail/post` request body."""

    schema_version: int = Field(default=GATEWAY_MAIL_SCHEMA_VERSION)
    subject: str
    body_content: str
    reply_policy: GatewayMailPostReplyPolicy = Field(
        default=HOUMAO_OPERATOR_MAILBOX_REPLY_POLICY_VALUE
    )
    attachments: list[GatewayMailAttachmentUploadV1] = Field(default_factory=list)

    @field_validator("subject")
    @classmethod
    def _subject_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @field_validator("body_content")
    @classmethod
    def _body_no_nul(cls, value: str) -> str:
        if "\x00" in value:
            raise ValueError("must not contain NUL bytes")
        return value

    @field_validator("reply_policy")
    @classmethod
    def _reply_policy_known(cls, value: GatewayMailPostReplyPolicy) -> GatewayMailPostReplyPolicy:
        if value not in {
            HOUMAO_NO_REPLY_POLICY_VALUE,
            HOUMAO_OPERATOR_MAILBOX_REPLY_POLICY_VALUE,
        }:
            raise ValueError("unsupported reply policy")
        return value

    @model_validator(mode="after")
    def _validate_schema(self) -> "GatewayMailPostRequestV1":
        if self.schema_version != GATEWAY_MAIL_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {GATEWAY_MAIL_SCHEMA_VERSION}")
        return self


class GatewayMailReplyRequestV1(_StrictGatewayModel):
    """`POST /v1/mail/reply` request body."""

    schema_version: int = Field(default=GATEWAY_MAIL_SCHEMA_VERSION)
    message_ref: str
    body_content: str
    attachments: list[GatewayMailAttachmentUploadV1] = Field(default_factory=list)

    @field_validator("message_ref")
    @classmethod
    def _message_ref_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @field_validator("body_content")
    @classmethod
    def _body_no_nul(cls, value: str) -> str:
        if "\x00" in value:
            raise ValueError("must not contain NUL bytes")
        return value

    @model_validator(mode="after")
    def _validate_schema(self) -> "GatewayMailReplyRequestV1":
        if self.schema_version != GATEWAY_MAIL_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {GATEWAY_MAIL_SCHEMA_VERSION}")
        return self


class GatewayMailActionResponseV1(_StrictGatewayModel):
    """`POST /v1/mail/send|post|reply` response body."""

    schema_version: int = Field(default=GATEWAY_MAIL_SCHEMA_VERSION)
    operation: Literal["send", "post", "reply"]
    transport: MailboxTransport
    principal_id: str
    address: str
    message: GatewayMailboxMessageV1

    @field_validator("principal_id", "address")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @model_validator(mode="after")
    def _validate_schema(self) -> "GatewayMailActionResponseV1":
        if self.schema_version != GATEWAY_MAIL_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {GATEWAY_MAIL_SCHEMA_VERSION}")
        return self


class GatewayMailLifecycleResponseV1(_StrictGatewayModel):
    """`POST /v1/mail/mark|move|archive` response body."""

    schema_version: int = Field(default=GATEWAY_MAIL_SCHEMA_VERSION)
    operation: GatewayMailLifecycleOperation
    transport: MailboxTransport
    principal_id: str
    address: str
    message_count: int
    messages: list[GatewayMailboxMessageV1]

    @field_validator("principal_id", "address")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value.strip()

    @field_validator("message_count")
    @classmethod
    def _non_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("must be >= 0")
        return value

    @model_validator(mode="after")
    def _validate_schema(self) -> "GatewayMailLifecycleResponseV1":
        if self.schema_version != GATEWAY_MAIL_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {GATEWAY_MAIL_SCHEMA_VERSION}")
        if self.message_count != len(self.messages):
            raise ValueError("message_count must match messages length")
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
    execution_mode: GatewayCurrentExecutionMode = Field(default="detached_process")
    queue_depth: int
    gateway_host: GatewayHost | None = None
    gateway_port: int | None = None
    gateway_tmux_window_id: str | None = None
    gateway_tmux_window_index: str | None = None
    gateway_tmux_pane_id: str | None = None
    managed_agent_instance_epoch: int
    managed_agent_instance_id: str | None = None

    @field_validator(
        "attach_identity",
        "tmux_session_name",
        "gateway_tmux_window_id",
        "gateway_tmux_window_index",
        "gateway_tmux_pane_id",
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
        elif self.gateway_host is None or self.gateway_port is None:
            raise ValueError("healthy gateway status must include live gateway host and port")

        tmux_fields = (
            self.gateway_tmux_window_id,
            self.gateway_tmux_window_index,
            self.gateway_tmux_pane_id,
        )
        if self.execution_mode == "detached_process":
            if any(value is not None for value in tmux_fields):
                raise ValueError(
                    "detached_process gateway status must not include gateway tmux surface fields"
                )
            return self

        if self.gateway_health == "healthy":
            if self.gateway_tmux_window_id is None or self.gateway_tmux_window_index is None:
                raise ValueError(
                    "healthy tmux_auxiliary_window gateway status requires "
                    "gateway_tmux_window_id and gateway_tmux_window_index"
                )
        elif any(value is not None for value in tmux_fields):
            if self.gateway_tmux_window_id is None or self.gateway_tmux_window_index is None:
                raise ValueError(
                    "tmux_auxiliary_window gateway status requires "
                    "gateway_tmux_window_id and gateway_tmux_window_index when tmux metadata "
                    "is present"
                )
        if self.gateway_tmux_window_index == "0":
            raise ValueError("gateway tmux window index must not be 0")
        return self


class GatewayHeadlessControlStateV1(_StrictGatewayModel):
    """Read-optimized live control posture for one attached headless agent."""

    schema_version: int = Field(default=GATEWAY_STATE_SCHEMA_VERSION)
    runtime_resumable: bool
    tmux_session_live: bool
    can_accept_prompt_now: bool
    interruptible: bool
    chat_session: GatewayHeadlessChatSessionStateV1
    request_admission: GatewayAdmissionState
    active_execution: GatewayExecutionState
    queue_depth: int
    active_turn_id: str | None = None

    @field_validator("queue_depth")
    @classmethod
    def _non_negative_queue_depth(cls, value: int) -> int:
        """Validate the live queue depth."""

        if value < 0:
            raise ValueError("must be >= 0")
        return value

    @field_validator("active_turn_id")
    @classmethod
    def _active_turn_id_not_blank(cls, value: str | None) -> str | None:
        """Validate the optional active turn id."""

        if value is None:
            return None
        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @model_validator(mode="after")
    def _validate_schema(self) -> "GatewayHeadlessControlStateV1":
        """Validate the shared gateway-state schema version."""

        if self.schema_version != GATEWAY_STATE_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {GATEWAY_STATE_SCHEMA_VERSION}")
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
