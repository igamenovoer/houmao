"""Offline, future-aware groundtruth classification for recorded Claude sessions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from houmao.explore.claude_code_state_tracking.detectors import select_claude_detector
from houmao.explore.claude_code_state_tracking.models import (
    Availability,
    DetectedSignals,
    LastTurnResult,
    RecordedObservation,
    TimelineState,
    TurnPhase,
)


@dataclass(frozen=True)
class _ObservedRow:
    """One detected row before future-aware success settlement."""

    observation: RecordedObservation
    availability: Availability
    signals: DetectedSignals
    phase: TurnPhase


def classify_groundtruth(
    *,
    observations: list[RecordedObservation],
    observed_version: str | None,
    settle_seconds: float,
) -> list[TimelineState]:
    """Derive a groundtruth timeline from recorded observations.

    Parameters
    ----------
    observations:
        Recorded replay observations sorted by elapsed time.
    observed_version:
        Observed Claude version string used for closest-compatible detector
        selection.
    settle_seconds:
        Success settle window in seconds.
    """

    detector = select_claude_detector(observed_version=observed_version)
    rows: list[_ObservedRow] = []
    for observation in observations:
        signals = detector.detect(output_text=observation.output_text)
        availability = classify_availability(observation=observation)
        phase: TurnPhase = _phase_from_signals(availability=availability, signals=signals)
        rows.append(
            _ObservedRow(
                observation=observation,
                availability=availability,
                signals=signals,
                phase=phase,
            )
        )

    success_start_indices = _find_success_start_indices(rows=rows, settle_seconds=settle_seconds)
    timeline: list[TimelineState] = []
    last_result: LastTurnResult = "none"
    for index, row in enumerate(rows):
        signals = row.signals
        if row.availability == "available":
            if getattr(signals, "interrupted"):
                last_result = "interrupted"
            elif getattr(signals, "known_failure"):
                last_result = "known_failure"
            elif index in success_start_indices:
                last_result = "success"
        timeline.append(
            TimelineState(
                sample_id=row.observation.sample_id,
                elapsed_seconds=row.observation.elapsed_seconds,
                ts_utc=row.observation.ts_utc,
                diagnostics_availability=row.availability,
                surface_accepting_input=getattr(signals, "accepting_input"),
                surface_editing_input=getattr(signals, "editing_input"),
                surface_ready_posture=getattr(signals, "ready_posture"),
                turn_phase=row.phase,
                last_turn_result=last_result,
                detector_name=getattr(signals, "detector_name"),
                detector_version=getattr(signals, "detector_version"),
                active_reasons=getattr(signals, "active_reasons"),
                notes=getattr(signals, "notes"),
            )
        )
    return timeline


def classify_availability(*, observation: RecordedObservation) -> Availability:
    """Classify diagnostics availability from runtime evidence."""

    runtime = observation.runtime
    if runtime is None:
        return "available"
    if not runtime.session_exists or not runtime.pane_exists:
        return "unavailable"
    if runtime.pane_dead:
        return "tui_down"
    if runtime.supported_process_pid is not None and not runtime.supported_process_alive:
        return "tui_down"
    if runtime.pane_pid is not None and not runtime.pane_pid_alive:
        return "tui_down"
    return "available"


def _phase_from_signals(*, availability: Availability, signals: object) -> TurnPhase:
    """Return the current turn phase from diagnostics and normalized signals."""

    typed_signals = cast(DetectedSignals, signals)
    if availability != "available":
        return "unknown"
    if typed_signals.interrupted or typed_signals.known_failure:
        return "ready"
    if typed_signals.active_evidence:
        return "active"
    if typed_signals.ready_posture == "yes":
        return "ready"
    return "unknown"


def _find_success_start_indices(
    *,
    rows: list[_ObservedRow],
    settle_seconds: float,
) -> set[int]:
    """Return sample indices where the final stable success surface becomes valid."""

    indices: set[int] = set()
    index = 0
    while index < len(rows):
        row = rows[index]
        signals = row.signals
        if (
            row.availability != "available"
            or not getattr(signals, "success_candidate")
            or getattr(signals, "current_error_present")
        ):
            index += 1
            continue

        block_start = index
        block_end = index
        while block_end + 1 < len(rows):
            next_row = rows[block_end + 1]
            next_signals = next_row.signals
            if next_row.availability != "available":
                break
            if not getattr(next_signals, "success_candidate"):
                break
            if getattr(next_signals, "current_error_present"):
                break
            block_end += 1

        final_segment_start = block_end
        final_segment_signature = getattr(rows[block_end].signals, "surface_signature")
        while final_segment_start - 1 >= block_start and (
            getattr(rows[final_segment_start - 1].signals, "surface_signature")
            == final_segment_signature
        ):
            final_segment_start -= 1

        final_settled_index: int | None = None
        candidate_index = final_segment_start
        while candidate_index <= block_end:
            if (
                rows[candidate_index].observation.elapsed_seconds
                - rows[final_segment_start].observation.elapsed_seconds
                >= settle_seconds
            ):
                final_settled_index = candidate_index
                break
            candidate_index += 1

        if final_settled_index is not None:
            indices.add(final_settled_index)
        index = block_end + 1

    return indices
