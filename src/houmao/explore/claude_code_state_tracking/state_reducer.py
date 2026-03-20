"""Shared ReactiveX state reducer for Claude Code observation streams."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Callable, Literal

import reactivex
from reactivex import abc
from reactivex.disposable import SerialDisposable

from houmao.explore.claude_code_state_tracking.detectors import select_claude_detector
from houmao.explore.claude_code_state_tracking.groundtruth import classify_availability
from houmao.explore.claude_code_state_tracking.models import (
    Availability,
    DetectedSignals,
    LastTurnResult,
    RecordedObservation,
    ReplayEvent,
    TimelineState,
    TurnPhase,
)


TraceWriter = Callable[[str, dict[str, Any]], None]


@dataclass
class _ReducerState:
    """Mutable public state for the shared reducer."""

    diagnostics_availability: Availability = "unknown"
    turn_phase: TurnPhase = "unknown"
    last_turn_result: LastTurnResult = "none"


class StreamStateReducer:
    """Shared reducer for live appended observations and offline replay."""

    def __init__(
        self,
        *,
        observed_version: str | None,
        settle_seconds: float,
        scheduler: abc.SchedulerBase,
        trace_writer: TraceWriter | None = None,
    ) -> None:
        """Initialize one reducer instance.

        Parameters
        ----------
        observed_version:
            Observed Claude version string used for closest-compatible detector
            selection.
        settle_seconds:
            Success settle window in seconds.
        scheduler:
            ReactiveX scheduler used for settle timers.
        trace_writer:
            Optional local trace sink for dense reducer/debug events.
        """

        self.m_detector = select_claude_detector(observed_version=observed_version)
        self.m_scheduler = scheduler
        self.m_settle_seconds = settle_seconds
        self.m_trace_writer = trace_writer
        self.m_state = _ReducerState()
        self.m_latest_observation: RecordedObservation | None = None
        self.m_latest_signals: DetectedSignals | None = None
        self.m_pending_success_signature: str | None = None
        self.m_settled_success_signature: str | None = None
        self.m_pending_success = SerialDisposable()
        self.m_all_events: list[ReplayEvent] = []
        self.m_pending_events: list[ReplayEvent] = []
        self.m_lock = threading.Lock()

    @property
    def detector_name(self) -> str:
        """Return the selected detector family name."""

        return self.m_detector.detector_name

    @property
    def detector_version(self) -> str:
        """Return the selected detector version selector."""

        return self.m_detector.detector_version

    @property
    def events(self) -> list[ReplayEvent]:
        """Return all emitted public-state events so far."""

        with self.m_lock:
            return list(self.m_all_events)

    @property
    def latest_observation(self) -> RecordedObservation | None:
        """Return the latest consumed observation."""

        with self.m_lock:
            return self.m_latest_observation

    @property
    def latest_signals(self) -> DetectedSignals | None:
        """Return the latest detected surface signals."""

        with self.m_lock:
            return self.m_latest_signals

    @property
    def current_state(self) -> _ReducerState:
        """Return the latest public state snapshot."""

        with self.m_lock:
            return _ReducerState(
                diagnostics_availability=self.m_state.diagnostics_availability,
                turn_phase=self.m_state.turn_phase,
                last_turn_result=self.m_state.last_turn_result,
            )

    def drain_events(self) -> list[ReplayEvent]:
        """Return newly emitted events and clear the pending queue."""

        with self.m_lock:
            events = list(self.m_pending_events)
            self.m_pending_events.clear()
            return events

    def process_observation(self, observation: RecordedObservation) -> TimelineState:
        """Reduce one observation and return its aligned public timeline state."""

        with self.m_lock:
            signals = self.m_detector.detect(output_text=observation.output_text)
            self.m_latest_observation = observation
            self.m_latest_signals = signals
            availability = classify_availability(observation=observation)
            self._trace(
                "detector_signals",
                {
                    "sample_id": observation.sample_id,
                    "elapsed_seconds": observation.elapsed_seconds,
                    "availability": availability,
                    "signals": signals.to_payload(),
                },
            )

            if availability != "available":
                self._cancel_success_timer_locked()
                self.m_settled_success_signature = None
                self._emit_state_locked(
                    source="observation",
                    at_seconds=observation.elapsed_seconds,
                    diagnostics_availability=availability,
                    turn_phase="unknown",
                    last_turn_result=self.m_state.last_turn_result,
                    sample_id=observation.sample_id,
                    note="diagnostics_path",
                )
                return self._timeline_state_locked(observation=observation, signals=signals)

            if signals.interrupted:
                self._cancel_success_timer_locked()
                self.m_settled_success_signature = None
                self._emit_state_locked(
                    source="observation",
                    at_seconds=observation.elapsed_seconds,
                    diagnostics_availability=availability,
                    turn_phase="ready",
                    last_turn_result="interrupted",
                    sample_id=observation.sample_id,
                    note="interrupted_signal",
                )
                return self._timeline_state_locked(observation=observation, signals=signals)

            if signals.known_failure:
                self._cancel_success_timer_locked()
                self.m_settled_success_signature = None
                self._emit_state_locked(
                    source="observation",
                    at_seconds=observation.elapsed_seconds,
                    diagnostics_availability=availability,
                    turn_phase="ready",
                    last_turn_result="known_failure",
                    sample_id=observation.sample_id,
                    note="known_failure_signal",
                )
                return self._timeline_state_locked(observation=observation, signals=signals)

            if signals.active_evidence:
                self._cancel_success_timer_locked()
                self._emit_state_locked(
                    source="observation",
                    at_seconds=observation.elapsed_seconds,
                    diagnostics_availability=availability,
                    turn_phase="active",
                    last_turn_result=self.m_state.last_turn_result,
                    sample_id=observation.sample_id,
                    note="active_signal",
                )
                return self._timeline_state_locked(observation=observation, signals=signals)

            if signals.success_candidate:
                current_signature = signals.surface_signature
                if (
                    self.m_state.last_turn_result == "success"
                    and self.m_settled_success_signature is not None
                    and current_signature != self.m_settled_success_signature
                ):
                    self.m_settled_success_signature = None
                    self._emit_state_locked(
                        source="observation",
                        at_seconds=observation.elapsed_seconds,
                        diagnostics_availability=availability,
                        turn_phase="ready",
                        last_turn_result="none",
                        sample_id=observation.sample_id,
                        note="success_invalidated",
                    )
                self._emit_state_locked(
                    source="observation",
                    at_seconds=observation.elapsed_seconds,
                    diagnostics_availability=availability,
                    turn_phase="ready",
                    last_turn_result=self.m_state.last_turn_result,
                    sample_id=observation.sample_id,
                    note="success_candidate",
                )
                self._arm_success_timer_locked(
                    sample_id=observation.sample_id,
                    at_seconds=observation.elapsed_seconds,
                    surface_signature=current_signature,
                )
                return self._timeline_state_locked(observation=observation, signals=signals)

            self._cancel_success_timer_locked()
            phase: TurnPhase = "ready" if signals.ready_posture == "yes" else "unknown"
            self._emit_state_locked(
                source="observation",
                at_seconds=observation.elapsed_seconds,
                diagnostics_availability=availability,
                turn_phase=phase,
                last_turn_result=self.m_state.last_turn_result,
                sample_id=observation.sample_id,
                note="default_observation",
            )
            return self._timeline_state_locked(observation=observation, signals=signals)

    def _timeline_state_locked(
        self, *, observation: RecordedObservation, signals: DetectedSignals
    ) -> TimelineState:
        """Build one observation-aligned timeline state under lock."""

        return TimelineState(
            sample_id=observation.sample_id,
            elapsed_seconds=observation.elapsed_seconds,
            ts_utc=observation.ts_utc,
            diagnostics_availability=self.m_state.diagnostics_availability,
            surface_accepting_input=signals.accepting_input,
            surface_editing_input=signals.editing_input,
            surface_ready_posture=signals.ready_posture,
            turn_phase=self.m_state.turn_phase,
            last_turn_result=self.m_state.last_turn_result,
            detector_name=signals.detector_name,
            detector_version=signals.detector_version,
            active_reasons=signals.active_reasons,
            notes=signals.notes,
        )

    def _arm_success_timer_locked(
        self, *, sample_id: str, at_seconds: float, surface_signature: str
    ) -> None:
        """Arm or retain a pending success timer for one candidate surface."""

        if self.m_pending_success_signature == surface_signature:
            return
        self._cancel_success_timer_locked()
        self.m_pending_success_signature = surface_signature
        self._trace(
            "rx_events",
            {
                "event": "success_timer_armed",
                "sample_id": sample_id,
                "at_seconds": at_seconds,
                "surface_signature": surface_signature,
            },
        )
        self.m_pending_success.disposable = reactivex.timer(
            timedelta(seconds=self.m_settle_seconds),
            scheduler=self.m_scheduler,
        ).subscribe(
            lambda _unused: self._on_success_timer(
                sample_id=sample_id,
                at_seconds=at_seconds + self.m_settle_seconds,
            )
        )

    def _on_success_timer(self, *, sample_id: str, at_seconds: float) -> None:
        """Handle one settled-success timer firing."""

        with self.m_lock:
            if self.m_latest_signals is None or self.m_latest_observation is None:
                return
            signals = self.m_latest_signals
            observation = self.m_latest_observation
            availability = classify_availability(observation=observation)
            if availability != "available":
                return
            if not signals.success_candidate:
                return
            if signals.current_error_present:
                return
            if signals.surface_signature != self.m_pending_success_signature:
                return
            self._emit_state_locked(
                source="timer",
                at_seconds=at_seconds,
                diagnostics_availability=availability,
                turn_phase="ready",
                last_turn_result="success",
                sample_id=sample_id,
                note="success_settled",
            )
            self.m_settled_success_signature = self.m_pending_success_signature
            self._cancel_success_timer_locked()

    def _cancel_success_timer_locked(self) -> None:
        """Cancel any pending success timer under lock."""

        self.m_pending_success.dispose()
        self.m_pending_success = SerialDisposable()
        if self.m_pending_success_signature is not None:
            self._trace(
                "rx_events",
                {
                    "event": "success_timer_canceled",
                    "surface_signature": self.m_pending_success_signature,
                },
            )
        self.m_pending_success_signature = None

    def _emit_state_locked(
        self,
        *,
        source: Literal["observation", "timer"],
        at_seconds: float,
        diagnostics_availability: Availability,
        turn_phase: TurnPhase,
        last_turn_result: LastTurnResult,
        sample_id: str | None,
        note: str,
    ) -> None:
        """Emit one public-state event under lock."""

        if (
            self.m_state.diagnostics_availability == diagnostics_availability
            and self.m_state.turn_phase == turn_phase
            and self.m_state.last_turn_result == last_turn_result
        ):
            return
        self.m_state = _ReducerState(
            diagnostics_availability=diagnostics_availability,
            turn_phase=turn_phase,
            last_turn_result=last_turn_result,
        )
        event = ReplayEvent(
            source=source,
            at_seconds=at_seconds,
            diagnostics_availability=diagnostics_availability,
            turn_phase=turn_phase,
            last_turn_result=last_turn_result,
            sample_id=sample_id,
            note=note,
        )
        self.m_all_events.append(event)
        self.m_pending_events.append(event)
        self._trace(
            "rx_events",
            {
                "event": "public_state_emitted",
                "source": source,
                "at_seconds": at_seconds,
                "sample_id": sample_id,
                "diagnostics_availability": diagnostics_availability,
                "turn_phase": turn_phase,
                "last_turn_result": last_turn_result,
                "note": note,
            },
        )

    def _trace(self, category: str, payload: dict[str, Any]) -> None:
        """Write one optional dense-trace payload."""

        if self.m_trace_writer is None:
            return
        self.m_trace_writer(category, payload)
