"""Shared replay reducer for official tracked-TUI state."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Callable

import reactivex
from reactivex import abc
from reactivex.disposable import SerialDisposable
from reactivex.subject import Subject
from reactivex.testing import TestScheduler

from houmao.shared_tui_tracking.detectors import select_tracked_turn_signal_detector
from houmao.shared_tui_tracking.models import (
    RecordedInputEvent,
    RecordedObservation,
    ReplayEvent,
    RuntimeObservation,
    TrackedDiagnosticsAvailability,
    TrackedLastTurnResult,
    TrackedLastTurnSource,
    TrackedTimelineState,
    TurnPhase,
)


TraceWriter = Callable[[str, dict[str, Any]], None]


@dataclass
class _ReducerState:
    """Mutable public state for the shared replay reducer."""

    diagnostics_availability: TrackedDiagnosticsAvailability = "unknown"
    turn_phase: TurnPhase = "unknown"
    last_turn_result: TrackedLastTurnResult = "none"
    last_turn_source: TrackedLastTurnSource = "none"


class StreamStateReducer:
    """Shared reducer for live-appended observations and offline replay."""

    def __init__(
        self,
        *,
        tool: str,
        observed_version: str | None,
        settle_seconds: float,
        scheduler: abc.SchedulerBase,
        trace_writer: TraceWriter | None = None,
    ) -> None:
        """Initialize one reducer instance."""

        self.m_detector = select_tracked_turn_signal_detector(
            tool=tool,
            observed_version=observed_version,
        )
        self.m_scheduler = scheduler
        self.m_settle_seconds = settle_seconds
        self.m_trace_writer = trace_writer
        self.m_state = _ReducerState()
        self.m_latest_observation: RecordedObservation | None = None
        self.m_latest_signals = None
        self.m_pending_success_signature: str | None = None
        self.m_settled_success_signature: str | None = None
        self.m_pending_success = SerialDisposable()
        self.m_all_events: list[ReplayEvent] = []
        self.m_pending_events: list[ReplayEvent] = []
        self.m_lock = threading.Lock()
        self.m_armed_turn_source: TrackedLastTurnSource | None = None

    @property
    def detector_name(self) -> str:
        """Return the selected detector family name."""

        return self.m_detector.detect(output_text="", parsed_surface=None).detector_name

    @property
    def latest_observation(self) -> RecordedObservation | None:
        """Return the latest consumed observation."""

        with self.m_lock:
            return self.m_latest_observation

    @property
    def latest_signals(self):
        """Return the latest detected surface signals."""

        with self.m_lock:
            return self.m_latest_signals

    @property
    def events(self) -> list[ReplayEvent]:
        """Return all emitted public-state events so far."""

        with self.m_lock:
            return list(self.m_all_events)

    def drain_events(self) -> list[ReplayEvent]:
        """Return newly emitted events and clear the pending queue."""

        with self.m_lock:
            events = list(self.m_pending_events)
            self.m_pending_events.clear()
            return events

    def process_input_event(self, event: RecordedInputEvent) -> None:
        """Arm explicit-input authority for a later terminal outcome."""

        with self.m_lock:
            self.m_armed_turn_source = "explicit_input"
            self._trace(
                "input_events",
                {
                    "event_id": event.event_id,
                    "elapsed_seconds": event.elapsed_seconds,
                    "source": event.source,
                    "armed_turn_source": self.m_armed_turn_source,
                },
            )

    def process_observation(self, observation: RecordedObservation) -> TrackedTimelineState:
        """Reduce one observation and return its aligned public tracked state."""

        with self.m_lock:
            signals = self.m_detector.detect(
                output_text=observation.output_text,
                parsed_surface=observation.surface_context,
            )
            self.m_latest_observation = observation
            self.m_latest_signals = signals
            availability = classify_runtime_availability(runtime=observation.runtime)
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
                    last_turn_source=self.m_state.last_turn_source,
                    sample_id=observation.sample_id,
                    note="diagnostics_path",
                )
                return self._timeline_state_locked(observation=observation, signals=signals)

            if signals.interrupted:
                self._cancel_success_timer_locked()
                self.m_settled_success_signature = None
                turn_source = self._terminal_turn_source_locked()
                self._emit_state_locked(
                    source="observation",
                    at_seconds=observation.elapsed_seconds,
                    diagnostics_availability=availability,
                    turn_phase="ready",
                    last_turn_result="interrupted",
                    last_turn_source=turn_source,
                    sample_id=observation.sample_id,
                    note="interrupted_signal",
                )
                self.m_armed_turn_source = None
                return self._timeline_state_locked(observation=observation, signals=signals)

            if signals.known_failure:
                self._cancel_success_timer_locked()
                self.m_settled_success_signature = None
                turn_source = self._terminal_turn_source_locked()
                self._emit_state_locked(
                    source="observation",
                    at_seconds=observation.elapsed_seconds,
                    diagnostics_availability=availability,
                    turn_phase="ready",
                    last_turn_result="known_failure",
                    last_turn_source=turn_source,
                    sample_id=observation.sample_id,
                    note="known_failure_signal",
                )
                self.m_armed_turn_source = None
                return self._timeline_state_locked(observation=observation, signals=signals)

            if signals.active_evidence:
                self._cancel_success_timer_locked()
                if self.m_armed_turn_source is None:
                    self.m_armed_turn_source = "surface_inference"
                self._emit_state_locked(
                    source="observation",
                    at_seconds=observation.elapsed_seconds,
                    diagnostics_availability=availability,
                    turn_phase="active",
                    last_turn_result=self.m_state.last_turn_result,
                    last_turn_source=self.m_state.last_turn_source,
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
                        last_turn_source="none",
                        sample_id=observation.sample_id,
                        note="success_invalidated",
                    )
                self._emit_state_locked(
                    source="observation",
                    at_seconds=observation.elapsed_seconds,
                    diagnostics_availability=availability,
                    turn_phase="ready",
                    last_turn_result=self.m_state.last_turn_result,
                    last_turn_source=self.m_state.last_turn_source,
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
                last_turn_source=self.m_state.last_turn_source,
                sample_id=observation.sample_id,
                note="default_observation",
            )
            return self._timeline_state_locked(observation=observation, signals=signals)

    def _timeline_state_locked(
        self, *, observation: RecordedObservation, signals
    ) -> TrackedTimelineState:
        """Build one observation-aligned timeline state under lock."""

        return TrackedTimelineState(
            sample_id=observation.sample_id,
            elapsed_seconds=observation.elapsed_seconds,
            ts_utc=observation.ts_utc,
            diagnostics_availability=self.m_state.diagnostics_availability,
            surface_accepting_input=signals.accepting_input,
            surface_editing_input=signals.editing_input,
            surface_ready_posture=signals.ready_posture,
            turn_phase=self.m_state.turn_phase,
            last_turn_result=self.m_state.last_turn_result,
            last_turn_source=self.m_state.last_turn_source,
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
            availability = classify_runtime_availability(runtime=observation.runtime)
            if availability != "available":
                return
            if not signals.success_candidate:
                return
            if signals.current_error_present:
                return
            if signals.surface_signature != self.m_pending_success_signature:
                return
            turn_source = self._terminal_turn_source_locked()
            self._emit_state_locked(
                source="timer",
                at_seconds=at_seconds,
                diagnostics_availability=availability,
                turn_phase="ready",
                last_turn_result="success",
                last_turn_source=turn_source,
                sample_id=sample_id,
                note="success_settled",
            )
            self.m_settled_success_signature = self.m_pending_success_signature
            self.m_armed_turn_source = None
            self._cancel_success_timer_locked()

    def _terminal_turn_source_locked(self) -> TrackedLastTurnSource:
        """Return the best available public source for one terminal outcome."""

        if self.m_armed_turn_source is not None:
            return self.m_armed_turn_source
        if self.m_state.last_turn_result != "none" and self.m_state.last_turn_source != "none":
            return self.m_state.last_turn_source
        return "surface_inference"

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
        source: str,
        at_seconds: float,
        diagnostics_availability: TrackedDiagnosticsAvailability,
        turn_phase: TurnPhase,
        last_turn_result: TrackedLastTurnResult,
        last_turn_source: TrackedLastTurnSource,
        sample_id: str | None,
        note: str,
    ) -> None:
        """Emit one public-state event under lock."""

        if (
            self.m_state.diagnostics_availability == diagnostics_availability
            and self.m_state.turn_phase == turn_phase
            and self.m_state.last_turn_result == last_turn_result
            and self.m_state.last_turn_source == last_turn_source
        ):
            return
        self.m_state = _ReducerState(
            diagnostics_availability=diagnostics_availability,
            turn_phase=turn_phase,
            last_turn_result=last_turn_result,
            last_turn_source=last_turn_source,
        )
        event = ReplayEvent(
            source=source,
            at_seconds=at_seconds,
            diagnostics_availability=diagnostics_availability,
            turn_phase=turn_phase,
            last_turn_result=last_turn_result,
            last_turn_source=last_turn_source,
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
                "last_turn_source": last_turn_source,
                "note": note,
            },
        )

    def _trace(self, category: str, payload: dict[str, Any]) -> None:
        """Write one optional dense-trace payload."""

        if self.m_trace_writer is None:
            return
        self.m_trace_writer(category, payload)


def replay_timeline(
    *,
    observations: list[RecordedObservation],
    tool: str,
    observed_version: str | None,
    settle_seconds: float,
    input_events: list[RecordedInputEvent] | None = None,
) -> tuple[list[TrackedTimelineState], list[ReplayEvent]]:
    """Replay one recorded observation list through the shared reducer."""

    scheduler = TestScheduler()
    subject: Subject[RecordedObservation] = Subject()
    tracker = StreamStateReducer(
        tool=tool,
        observed_version=observed_version,
        settle_seconds=settle_seconds,
        scheduler=scheduler,
    )
    timeline: list[TrackedTimelineState] = []
    subject.subscribe(lambda observation: timeline.append(tracker.process_observation(observation)))

    for event in input_events or []:
        scheduler.schedule_absolute(
            event.elapsed_seconds,
            _build_input_emit_action(tracker=tracker, event=event),
        )
    for observation in observations:
        scheduler.schedule_absolute(
            observation.elapsed_seconds,
            _build_observation_emit_action(subject=subject, observation=observation),
        )
    if observations:
        scheduler.advance_to(observations[-1].elapsed_seconds + settle_seconds + 1.0)

    return timeline, tracker.events


def classify_runtime_availability(
    *, runtime: RuntimeObservation | None
) -> TrackedDiagnosticsAvailability:
    """Classify diagnostics availability from optional runtime evidence."""

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


def _build_observation_emit_action(
    *,
    subject: Subject[RecordedObservation],
    observation: RecordedObservation,
) -> Callable[[TestScheduler, object | None], None]:
    """Return one scheduled emission action for a replay observation."""

    def _emit(_scheduler: TestScheduler, _state: object | None = None) -> None:
        """Emit one recorded observation into the replay subject."""

        subject.on_next(observation)

    return _emit


def _build_input_emit_action(
    *,
    tracker: StreamStateReducer,
    event: RecordedInputEvent,
) -> Callable[[TestScheduler, object | None], None]:
    """Return one scheduled emission action for an input event."""

    def _emit(_scheduler: TestScheduler, _state: object | None = None) -> None:
        """Arm explicit-input authority when one input event is replayed."""

        tracker.process_input_event(event)

    return _emit
