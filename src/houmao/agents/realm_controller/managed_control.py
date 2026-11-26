"""Shared capability and observation projections for owner-bound agent control."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from houmao.agents.realm_controller.errors import BackendExecutionError
from houmao.agents.realm_controller.models import BackendKind
from houmao.agents.realm_controller.native_surface import (
    NativeSurfaceV1,
    TerminalNativeSurfaceV1,
    WebNativeSurfaceV1,
)
from houmao.agents.realm_controller.run_modes import (
    MANAGED_SERVICE_BACKENDS as MANAGED_SERVICE_BACKENDS,
    MANAGED_STRUCTURED_TUI_BACKENDS as MANAGED_STRUCTURED_TUI_BACKENDS,
    MANAGED_WEB_BACKENDS as MANAGED_WEB_BACKENDS,
    RunMode,
    validate_mode_binding,
)

if TYPE_CHECKING:
    from houmao.server.models import HoumaoTerminalStateResponse


ManagedControlOperation = Literal[
    "prompt",
    "interrupt",
    "state",
    "events",
    "usage",
    "stop",
    "relaunch",
    "send_keys",
    "human_handoff",
    "native_refresh",
]
ManagedControlEvidenceSource = Literal[
    "headless_artifacts",
    "terminal_tracker",
    "tui_native",
    "web_native",
    "service_native",
    "owner_registry",
]
ManagedControlCorrelation = Literal["none", "surface", "request", "native_turn"]
ManagedControlOutcome = Literal["completed", "failed", "interrupted", "uncertain"]


class ManagedControlCapabilitiesV1(BaseModel):
    """Describe qualified operations and the strongest available evidence for one mode."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    tool: str
    mode: RunMode
    backend: BackendKind
    operations: tuple[ManagedControlOperation, ...]
    evidence_source: ManagedControlEvidenceSource
    correlation: ManagedControlCorrelation

    @model_validator(mode="after")
    def _validate_mode(self) -> ManagedControlCapabilitiesV1:
        """Keep operation support coherent with the verified provider mode."""

        validate_mode_binding(self.tool, self.mode, self.backend)
        if "send_keys" in self.operations and self.mode != "tui":
            raise ValueError("Raw input requires terminal mode")
        if "human_handoff" in self.operations and self.mode not in {"tui", "web"}:
            raise ValueError("Human handoff requires terminal or Web mode")
        return self

    def require(self, operation: ManagedControlOperation) -> None:
        """Reject an unsupported operation before reaching a provider."""

        if operation not in self.operations:
            raise BackendExecutionError(
                f"Managed control operation {operation!r} is unsupported for "
                f"{self.tool} {self.mode} ({self.backend})."
            )


class ManagedControlObservationV1(BaseModel):
    """Project attributable readiness and activity without private connection data."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source: ManagedControlEvidenceSource
    freshness: Literal["current", "stale", "unknown"]
    observed_at_utc: str | None = None
    owner_available: bool | None = None
    connection_ready: bool | None = None
    can_accept_prompt_now: bool | None = None
    service_incarnation: str | None = None
    native_session_id: str | None = None
    active_request_id: str | None = None
    active_turn_id: str | None = None
    last_request_id: str | None = None
    last_turn_id: str | None = None
    last_outcome: ManagedControlOutcome | None = None
    native_admission_id: str | None = None
    native_admission_state: str | None = None
    terminal_attachment: Literal["attached", "detached", "unverified", "other_session"] | None = (
        None
    )

    @field_validator(
        "observed_at_utc",
        "service_incarnation",
        "native_session_id",
        "active_request_id",
        "active_turn_id",
        "last_request_id",
        "last_turn_id",
        "native_admission_id",
    )
    @classmethod
    def _require_identifier(cls, value: str | None) -> str | None:
        """Require a nonempty single-line value for optional evidence identifiers."""

        if value is not None and (not value.strip() or any(c in value for c in "\x00\r\n")):
            raise ValueError("Observation values must be nonempty single-line strings")
        return value

    @model_validator(mode="after")
    def _validate_readiness(self) -> ManagedControlObservationV1:
        """Prevent stale or disconnected evidence from opening admission."""

        if self.can_accept_prompt_now is True and (
            self.freshness != "current"
            or self.owner_available is False
            or self.connection_ready is False
            or self.active_request_id is not None
            or self.active_turn_id is not None
        ):
            raise ValueError("Ready observations require current, available and idle evidence")
        return self


_INSPECT_AND_LIFECYCLE: tuple[ManagedControlOperation, ...] = ("state", "stop", "relaunch")
_TURN_CONTROL: tuple[ManagedControlOperation, ...] = (
    *_INSPECT_AND_LIFECYCLE,
    "prompt",
    "interrupt",
    "events",
    "usage",
)


def managed_control_capabilities(
    *, tool: str, mode: RunMode, backend: BackendKind, native_surface: NativeSurfaceV1 | None
) -> ManagedControlCapabilitiesV1:
    """Select operations and evidence from a verified runtime rather than a supervisor pane."""

    operations = _INSPECT_AND_LIFECYCLE
    source: ManagedControlEvidenceSource = "owner_registry"
    correlation: ManagedControlCorrelation = "none"
    if mode == "headless":
        operations, source, correlation = _TURN_CONTROL, "headless_artifacts", "request"
    elif backend in MANAGED_STRUCTURED_TUI_BACKENDS:
        operations = _TURN_CONTROL
        if isinstance(native_surface, TerminalNativeSurfaceV1):
            operations = (*operations, "human_handoff")
        source, correlation = "tui_native", "native_turn"
    elif mode == "tui" and isinstance(native_surface, TerminalNativeSurfaceV1):
        operations = (*_TURN_CONTROL, "send_keys", "human_handoff")
        source, correlation = "terminal_tracker", "surface"
    elif mode == "web" and isinstance(native_surface, WebNativeSurfaceV1):
        operations = (*_TURN_CONTROL, "human_handoff")
        if backend == "dsh_web":
            operations = (*operations, "native_refresh")
        source, correlation = "web_native", "native_turn"
    elif mode == "service":
        source = "service_native"
        if backend in MANAGED_SERVICE_BACKENDS:
            operations, correlation = _TURN_CONTROL, "native_turn"
        if backend == "dsh_acp":
            operations = (*operations, "native_refresh")
    return ManagedControlCapabilitiesV1(
        tool=tool,
        mode=mode,
        backend=backend,
        operations=operations,
        evidence_source=source,
        correlation=correlation,
    )


def terminal_prompt_not_ready_reasons(
    state: HoumaoTerminalStateResponse, *, require_stable: bool = True
) -> list[str]:
    """Report which verified terminal observations prevent ordinary prompt admission."""

    reasons: list[str] = []
    if state.turn.phase != "ready":
        reasons.append(f"turn.phase={state.turn.phase!r}")
    if state.surface.accepting_input != "yes":
        reasons.append(f"surface.accepting_input={state.surface.accepting_input!r}")
    if state.surface.editing_input != "no":
        reasons.append(f"surface.editing_input={state.surface.editing_input!r}")
    if state.surface.ready_posture != "yes":
        reasons.append(f"surface.ready_posture={state.surface.ready_posture!r}")
    if require_stable and not state.stability.stable:
        reasons.append("stability.stable=false")
    parsed = state.parsed_surface
    if parsed is not None:
        if parsed.business_state != "idle":
            reasons.append(f"parsed_surface.business_state={parsed.business_state!r}")
        if parsed.input_mode != "freeform":
            reasons.append(f"parsed_surface.input_mode={parsed.input_mode!r}")
    return reasons
