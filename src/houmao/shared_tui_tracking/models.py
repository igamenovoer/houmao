"""Neutral tracked-TUI models shared by official/runtime adapters."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal, cast


Tristate = Literal["yes", "no", "unknown"]
TrackedDiagnosticsAvailability = Literal["available", "unavailable", "tui_down", "error", "unknown"]
TurnPhase = Literal["ready", "active", "unknown"]
TrackedLastTurnResult = Literal["success", "interrupted", "known_failure", "none"]
TrackedLastTurnSource = Literal["explicit_input", "surface_inference", "none"]
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
ReadinessState = Literal["ready", "waiting", "blocked", "failed", "unknown", "stalled"]
CompletionState = Literal[
    "inactive",
    "in_progress",
    "candidate_complete",
    "completed",
    "waiting",
    "blocked",
    "failed",
    "unknown",
    "stalled",
]
TrackerEventSource = Literal["snapshot", "timer", "input"]
ChatContextState = Literal["current", "degraded", "unknown"]


@dataclass(frozen=True)
class TrackerConfig:
    """Configuration for one standalone tracker session."""

    settle_seconds: float
    stability_threshold_seconds: float = 0.0

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-serializable payload."""

        return asdict(self)


@dataclass(frozen=True)
class TrackedStateSnapshot:
    """Current standalone tracker state."""

    surface_accepting_input: Tristate
    surface_editing_input: Tristate
    surface_ready_posture: Tristate
    turn_phase: TurnPhase
    last_turn_result: TrackedLastTurnResult
    last_turn_source: TrackedLastTurnSource
    detector_name: str
    detector_version: str
    active_reasons: tuple[str, ...]
    notes: tuple[str, ...]
    stability_signature: str
    stable: bool
    stable_for_seconds: float
    stable_since_seconds: float
    observed_at_seconds: float
    chat_context: ChatContextState = "current"

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-serializable payload."""

        return asdict(self)


@dataclass(frozen=True)
class TrackedStateTransition:
    """One emitted standalone tracker transition."""

    source: TrackerEventSource
    at_seconds: float
    note: str
    sample_id: str | None
    surface_accepting_input: Tristate
    surface_editing_input: Tristate
    surface_ready_posture: Tristate
    turn_phase: TurnPhase
    last_turn_result: TrackedLastTurnResult
    last_turn_source: TrackedLastTurnSource
    detector_name: str
    detector_version: str
    active_reasons: tuple[str, ...]
    notes: tuple[str, ...]
    stability_signature: str
    stable: bool
    stable_for_seconds: float
    stable_since_seconds: float
    chat_context: ChatContextState = "current"

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-serializable payload."""

        return asdict(self)


@dataclass(frozen=True)
class ParsedSurfaceContext:
    """Minimal parsed-surface context used by official/runtime detectors."""

    business_state: str
    input_mode: str
    ui_context: str


@dataclass(frozen=True)
class RuntimeObservation:
    """One runtime liveness sample captured alongside pane snapshots."""

    ts_utc: str
    elapsed_seconds: float
    session_exists: bool
    pane_exists: bool
    pane_dead: bool
    pane_pid: int | None
    pane_pid_alive: bool
    supported_process_pid: int | None
    supported_process_alive: bool

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-serializable payload."""

        return asdict(self)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "RuntimeObservation":
        """Parse one runtime-observation payload."""

        return cls(
            ts_utc=str(payload["ts_utc"]),
            elapsed_seconds=float(payload["elapsed_seconds"]),
            session_exists=bool(payload["session_exists"]),
            pane_exists=bool(payload["pane_exists"]),
            pane_dead=bool(payload.get("pane_dead", False)),
            pane_pid=_optional_int(payload.get("pane_pid")),
            pane_pid_alive=bool(payload.get("pane_pid_alive", False)),
            supported_process_pid=_optional_int(payload.get("supported_process_pid")),
            supported_process_alive=bool(payload.get("supported_process_alive", False)),
        )


@dataclass(frozen=True)
class RecordedInputEvent:
    """One authoritative input event aligned to a tracked observation stream."""

    event_id: str
    elapsed_seconds: float
    ts_utc: str
    source: str


@dataclass(frozen=True)
class RecordedObservation:
    """One replay-grade observation combining pane text and runtime diagnostics."""

    sample_id: str
    elapsed_seconds: float
    ts_utc: str
    output_text: str
    runtime: RuntimeObservation | None
    surface_context: ParsedSurfaceContext | None = None


@dataclass(frozen=True)
class DetectedTurnSignals:
    """Normalized tracked turn signals for one visible surface."""

    detector_name: str
    detector_version: str
    accepting_input: Tristate
    editing_input: Tristate
    ready_posture: Tristate
    prompt_visible: bool
    prompt_text: str | None
    footer_interruptable: bool
    active_evidence: bool
    active_reasons: tuple[str, ...]
    interrupted: bool
    known_failure: bool
    current_error_present: bool
    success_candidate: bool
    completion_marker: str | None
    latest_status_line: str | None
    ambiguous_interactive_surface: bool
    success_blocked: bool
    surface_signature: str
    notes: tuple[str, ...]
    chat_context: ChatContextState = "current"

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-serializable payload."""

        return asdict(self)


@dataclass(frozen=True)
class TemporalHintSignals:
    """Temporal lifecycle hints derived from recent ordered profile frames."""

    accepting_input: Tristate | None = None
    editing_input: Tristate | None = None
    ready_posture: Tristate | None = None
    active_evidence: bool | None = None
    active_reasons: tuple[str, ...] = ()
    interrupted: bool | None = None
    known_failure: bool | None = None
    current_error_present: bool | None = None
    success_candidate: bool | None = None
    success_blocked: bool | None = None
    notes: tuple[str, ...] = ()

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-serializable payload."""

        return asdict(self)


@dataclass(frozen=True)
class RecentProfileFrame:
    """One session-owned profile frame held in the temporal recent-window."""

    observed_at_seconds: float
    payload: object


@dataclass(frozen=True)
class TrackedTimelineState:
    """One sample-aligned tracked-state row in the official vocabulary."""

    sample_id: str
    elapsed_seconds: float
    ts_utc: str
    diagnostics_availability: TrackedDiagnosticsAvailability
    surface_accepting_input: Tristate
    surface_editing_input: Tristate
    surface_ready_posture: Tristate
    turn_phase: TurnPhase
    last_turn_result: TrackedLastTurnResult
    last_turn_source: TrackedLastTurnSource
    detector_name: str
    detector_version: str
    active_reasons: tuple[str, ...]
    notes: tuple[str, ...]

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-serializable payload."""

        return asdict(self)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "TrackedTimelineState":
        """Parse one tracked timeline payload."""

        return cls(
            sample_id=str(payload["sample_id"]),
            elapsed_seconds=float(payload["elapsed_seconds"]),
            ts_utc=str(payload["ts_utc"]),
            diagnostics_availability=cast(
                TrackedDiagnosticsAvailability,
                str(payload["diagnostics_availability"]),
            ),
            surface_accepting_input=cast(Tristate, str(payload["surface_accepting_input"])),
            surface_editing_input=cast(Tristate, str(payload["surface_editing_input"])),
            surface_ready_posture=cast(Tristate, str(payload["surface_ready_posture"])),
            turn_phase=cast(TurnPhase, str(payload["turn_phase"])),
            last_turn_result=cast(TrackedLastTurnResult, str(payload["last_turn_result"])),
            last_turn_source=cast(TrackedLastTurnSource, str(payload["last_turn_source"])),
            detector_name=str(payload["detector_name"]),
            detector_version=str(payload["detector_version"]),
            active_reasons=tuple(str(item) for item in payload.get("active_reasons", [])),
            notes=tuple(str(item) for item in payload.get("notes", [])),
        )


@dataclass(frozen=True)
class ReplayEvent:
    """One internal replay/public-state transition event."""

    source: Literal["observation", "timer"]
    at_seconds: float
    diagnostics_availability: TrackedDiagnosticsAvailability
    turn_phase: TurnPhase
    last_turn_result: TrackedLastTurnResult
    last_turn_source: TrackedLastTurnSource
    sample_id: str | None
    note: str

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-serializable payload."""

        return asdict(self)


def _optional_int(value: object) -> int | None:
    """Return one optional integer from a JSON-like payload value."""

    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError("boolean is not a valid integer value")
    if not isinstance(value, (int, str, bytes, bytearray)):
        raise ValueError(f"unsupported integer payload value: {type(value)!r}")
    return int(value)
