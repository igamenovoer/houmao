"""ReactiveX-driven replay tracker for recorded Claude observations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Callable, Literal

import reactivex
from reactivex import abc
from reactivex.disposable import SerialDisposable
from reactivex.subject import Subject
from reactivex.testing import TestScheduler

from houmao.explore.claude_code_state_tracking.detectors import select_claude_detector
from houmao.explore.claude_code_state_tracking.groundtruth import classify_availability
from houmao.explore.claude_code_state_tracking.models import (
    Availability,
    LastTurnResult,
    RecordedObservation,
    ReplayEvent,
    TimelineState,
    TurnPhase,
)


@dataclass
class _ReplayState:
    """Mutable replay state for current phase and last terminal outcome."""

    diagnostics_availability: Availability = "unknown"
    turn_phase: TurnPhase = "unknown"
    last_turn_result: LastTurnResult = "none"


class ReplayTracker:
    """Independent replay tracker using ReactiveX timers."""

    def __init__(
        self, *, observed_version: str | None, settle_seconds: float, scheduler: TestScheduler
    ) -> None:
        """Initialize one replay tracker."""

        self.m_detector = select_claude_detector(observed_version=observed_version)
        self.m_settle_seconds = settle_seconds
        self.m_scheduler = scheduler
        self.m_events: list[ReplayEvent] = []
        self.m_state = _ReplayState()
        self.m_latest_observation: RecordedObservation | None = None
        self.m_latest_signals: object | None = None
        self.m_pending_success_signature: str | None = None
        self.m_settled_success_signature: str | None = None
        self.m_pending_success = SerialDisposable()

    @property
    def events(self) -> list[ReplayEvent]:
        """Return emitted replay state-change events."""

        return list(self.m_events)

    def on_observation(self, observation: RecordedObservation) -> None:
        """Consume one replay observation."""

        self.m_latest_observation = observation
        signals = self.m_detector.detect(output_text=observation.output_text)
        self.m_latest_signals = signals
        availability = classify_availability(observation=observation)

        if availability != "available":
            self._cancel_success_timer()
            self.m_settled_success_signature = None
            self._emit_state(
                source="observation",
                at_seconds=observation.elapsed_seconds,
                diagnostics_availability=availability,
                turn_phase="unknown",
                last_turn_result=self.m_state.last_turn_result,
                sample_id=observation.sample_id,
                note="diagnostics_path",
            )
            return

        if getattr(signals, "interrupted"):
            self._cancel_success_timer()
            self.m_settled_success_signature = None
            self._emit_state(
                source="observation",
                at_seconds=observation.elapsed_seconds,
                diagnostics_availability=availability,
                turn_phase="ready",
                last_turn_result="interrupted",
                sample_id=observation.sample_id,
                note="interrupted_signal",
            )
            return

        if getattr(signals, "known_failure"):
            self._cancel_success_timer()
            self.m_settled_success_signature = None
            self._emit_state(
                source="observation",
                at_seconds=observation.elapsed_seconds,
                diagnostics_availability=availability,
                turn_phase="ready",
                last_turn_result="known_failure",
                sample_id=observation.sample_id,
                note="known_failure_signal",
            )
            return

        if getattr(signals, "active_evidence"):
            self._cancel_success_timer()
            if self.m_state.last_turn_result == "success":
                self.m_settled_success_signature = None
            self._emit_state(
                source="observation",
                at_seconds=observation.elapsed_seconds,
                diagnostics_availability=availability,
                turn_phase="active",
                last_turn_result="none"
                if self.m_state.last_turn_result == "success"
                else self.m_state.last_turn_result,
                sample_id=observation.sample_id,
                note="active_signal",
            )
            return

        if getattr(signals, "success_candidate"):
            current_signature = getattr(signals, "surface_signature")
            if (
                self.m_state.last_turn_result == "success"
                and self.m_settled_success_signature is not None
                and current_signature != self.m_settled_success_signature
            ):
                self.m_settled_success_signature = None
                self._emit_state(
                    source="observation",
                    at_seconds=observation.elapsed_seconds,
                    diagnostics_availability=availability,
                    turn_phase="ready",
                    last_turn_result="none",
                    sample_id=observation.sample_id,
                    note="success_invalidated",
                )
            self._emit_state(
                source="observation",
                at_seconds=observation.elapsed_seconds,
                diagnostics_availability=availability,
                turn_phase="ready",
                last_turn_result=self.m_state.last_turn_result,
                sample_id=observation.sample_id,
                note="success_candidate",
            )
            self._arm_success_timer(
                sample_id=observation.sample_id,
                at_seconds=observation.elapsed_seconds,
                surface_signature=getattr(signals, "surface_signature"),
            )
            return

        self._cancel_success_timer()
        phase: TurnPhase = "ready" if getattr(signals, "ready_posture") == "yes" else "unknown"
        self._emit_state(
            source="observation",
            at_seconds=observation.elapsed_seconds,
            diagnostics_availability=availability,
            turn_phase=phase,
            last_turn_result=self.m_state.last_turn_result,
            sample_id=observation.sample_id,
            note="default_observation",
        )

    def _arm_success_timer(
        self, *, sample_id: str, at_seconds: float, surface_signature: str
    ) -> None:
        """Arm or retain a pending success timer for one candidate surface."""

        if self.m_pending_success_signature == surface_signature:
            return
        self._cancel_success_timer()
        self.m_pending_success_signature = surface_signature
        self.m_pending_success.disposable = reactivex.timer(
            timedelta(seconds=self.m_settle_seconds),
            scheduler=self.m_scheduler,
        ).subscribe(
            _build_success_timer_callback(
                tracker=self,
                sample_id=sample_id,
                at_seconds=at_seconds + self.m_settle_seconds,
            )
        )

    def _on_success_timer(self, *, sample_id: str, at_seconds: float) -> None:
        """Handle one settled-success timer firing."""

        if self.m_latest_signals is None or self.m_latest_observation is None:
            return
        signals = self.m_latest_signals
        observation = self.m_latest_observation
        availability = classify_availability(observation=observation)
        if availability != "available":
            return
        if not getattr(signals, "success_candidate"):
            return
        if getattr(signals, "current_error_present"):
            return
        if getattr(signals, "surface_signature") != self.m_pending_success_signature:
            return
        self._emit_state(
            source="timer",
            at_seconds=at_seconds,
            diagnostics_availability=availability,
            turn_phase="ready",
            last_turn_result="success",
            sample_id=sample_id,
            note="success_settled",
        )
        self.m_settled_success_signature = self.m_pending_success_signature
        self._cancel_success_timer()

    def _cancel_success_timer(self) -> None:
        """Cancel any pending success timer."""

        self.m_pending_success.dispose()
        self.m_pending_success = SerialDisposable()
        self.m_pending_success_signature = None

    def _emit_state(
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
        """Emit one state-change event when the public state changes."""

        if (
            self.m_state.diagnostics_availability == diagnostics_availability
            and self.m_state.turn_phase == turn_phase
            and self.m_state.last_turn_result == last_turn_result
        ):
            return
        self.m_state = _ReplayState(
            diagnostics_availability=diagnostics_availability,
            turn_phase=turn_phase,
            last_turn_result=last_turn_result,
        )
        self.m_events.append(
            ReplayEvent(
                source=source,
                at_seconds=at_seconds,
                diagnostics_availability=diagnostics_availability,
                turn_phase=turn_phase,
                last_turn_result=last_turn_result,
                sample_id=sample_id,
                note=note,
            )
        )


def replay_timeline(
    *,
    observations: list[RecordedObservation],
    observed_version: str | None,
    settle_seconds: float,
) -> tuple[list[TimelineState], list[ReplayEvent]]:
    """Replay one recorded observation list through the independent tracker."""

    scheduler = TestScheduler()
    subject: Subject[RecordedObservation] = Subject()
    tracker = ReplayTracker(
        observed_version=observed_version,
        settle_seconds=settle_seconds,
        scheduler=scheduler,
    )
    subject.subscribe(tracker.on_observation)

    for observation in observations:
        scheduler.schedule_absolute(
            observation.elapsed_seconds,
            _build_emit_action(subject=subject, observation=observation),
        )
    if observations:
        scheduler.advance_to(observations[-1].elapsed_seconds + settle_seconds + 1.0)

    timeline: list[TimelineState] = []
    for observation in observations:
        state = _state_at_time(events=tracker.events, at_seconds=observation.elapsed_seconds)
        signals = tracker.m_detector.detect(output_text=observation.output_text)
        timeline.append(
            TimelineState(
                sample_id=observation.sample_id,
                elapsed_seconds=observation.elapsed_seconds,
                ts_utc=observation.ts_utc,
                diagnostics_availability=state.diagnostics_availability,
                surface_accepting_input=signals.accepting_input,
                surface_editing_input=signals.editing_input,
                surface_ready_posture=signals.ready_posture,
                turn_phase=state.turn_phase,
                last_turn_result=state.last_turn_result,
                detector_name=signals.detector_name,
                detector_version=signals.detector_version,
                active_reasons=signals.active_reasons,
                notes=signals.notes,
            )
        )
    return timeline, tracker.events


def _state_at_time(*, events: list[ReplayEvent], at_seconds: float) -> _ReplayState:
    """Return the latest replay state at one observation time."""

    state = _ReplayState()
    for event in events:
        if event.at_seconds > at_seconds:
            break
        state = _ReplayState(
            diagnostics_availability=event.diagnostics_availability,
            turn_phase=event.turn_phase,
            last_turn_result=event.last_turn_result,
        )
    return state


def _build_success_timer_callback(
    *,
    tracker: ReplayTracker,
    sample_id: str,
    at_seconds: float,
) -> Callable[[int], None]:
    """Return one typed callback for a success-settle timer."""

    def _callback(_value: int) -> None:
        tracker._on_success_timer(sample_id=sample_id, at_seconds=at_seconds)

    return _callback


def _build_emit_action(
    *,
    subject: Subject[RecordedObservation],
    observation: RecordedObservation,
) -> Callable[[abc.SchedulerBase, object | None], abc.DisposableBase | None]:
    """Return one typed scheduler action for an observation emission."""

    def _action(_scheduler: abc.SchedulerBase, _state: object | None) -> abc.DisposableBase | None:
        subject.on_next(observation)
        return None

    return _action
