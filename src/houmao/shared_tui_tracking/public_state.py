"""Shared public-state helpers used by official/runtime adapters."""

from __future__ import annotations

from houmao.shared_tui_tracking.models import (
    CompletionState,
    DetectedTurnSignals,
    ParseStatus,
    ProcessState,
    TrackedDiagnosticsAvailability,
    TrackedLastTurnResult,
    TrackedLastTurnSource,
    TransportState,
    Tristate,
    TurnPhase,
)


def diagnostics_availability(
    *,
    transport_state: TransportState,
    process_state: ProcessState,
    parse_status: ParseStatus,
    probe_error_present: bool,
    parse_error_present: bool,
    parsed_surface_available: bool,
) -> TrackedDiagnosticsAvailability:
    """Map low-level observation outcomes into tracked diagnostic availability."""

    if (
        probe_error_present
        or parse_error_present
        or transport_state == "probe_error"
        or process_state == "probe_error"
        or parse_status in {"probe_error", "parse_error"}
    ):
        return "error"
    if transport_state == "tmux_missing":
        return "unavailable"
    if process_state == "tui_down":
        return "tui_down"
    if process_state == "unsupported_tool" or parse_status == "unsupported_tool":
        return "unknown"
    if parse_status == "parsed" and parsed_surface_available:
        return "available"
    return "unknown"


def turn_phase_from_signals(
    *,
    diagnostics_availability_value: TrackedDiagnosticsAvailability,
    surface_ready_posture: Tristate,
    active_turn_anchor_present: bool,
    reduction_completion_state: CompletionState,
    detected_turn_signals: DetectedTurnSignals,
    last_turn_result: TrackedLastTurnResult,
) -> TurnPhase:
    """Map normalized signals plus lifecycle state into the public turn phase."""

    if diagnostics_availability_value in {"error", "tui_down", "unavailable"}:
        return "unknown"
    if active_turn_anchor_present:
        if (
            last_turn_result == "success"
            and reduction_completion_state == "completed"
            and surface_ready_posture == "yes"
            and not detected_turn_signals.success_blocked
        ):
            return "ready"
        return "active"
    if detected_turn_signals.active_evidence:
        return "active"
    if detected_turn_signals.ambiguous_interactive_surface:
        return "unknown"
    if surface_ready_posture == "yes":
        return "ready"
    return "unknown"


def tracked_last_turn_source_from_anchor_source(
    anchor_source: str,
) -> TrackedLastTurnSource:
    """Map one internal anchor source to the public last-turn source enum."""

    if anchor_source == "terminal_input":
        return "explicit_input"
    return "surface_inference"
