"""Standalone reactive session for tracked TUI state."""

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable

import reactivex
from reactivex import abc
from reactivex.disposable import SerialDisposable
from reactivex.scheduler import TimeoutScheduler
from reactivex.subject import Subject

from houmao.shared_tui_tracking.models import (
    DetectedTurnSignals,
    TrackerConfig,
    TrackedLastTurnResult,
    TrackedLastTurnSource,
    TrackedStateSnapshot,
    TrackedStateTransition,
    Tristate,
    TurnPhase,
)
from houmao.shared_tui_tracking.registry import DetectorProfileRegistry, ResolvedDetectorProfile


TraceWriter = Callable[[str, dict[str, Any]], None]


@dataclass
class _MutableTrackerState:
    """Mutable tracker-owned state without derived stability fields."""

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


class TuiTrackerSession:
    """Thread-safe standalone session for raw-snapshot TUI tracking."""

    def __init__(
        self,
        *,
        app_id: str,
        observed_version: str | None,
        config: TrackerConfig,
        scheduler: abc.SchedulerBase | None = None,
        registry: DetectorProfileRegistry | None = None,
        trace_writer: TraceWriter | None = None,
    ) -> None:
        """Initialize one tracker session."""

        self.m_scheduler: abc.SchedulerBase = scheduler or TimeoutScheduler.singleton()
        self.m_registry: DetectorProfileRegistry = registry or DetectorProfileRegistry.default()
        self.m_trace_writer: TraceWriter | None = trace_writer
        self.m_lock: threading.RLock = threading.RLock()
        self.m_snapshot_subject: Subject[str] = Subject()
        self.m_input_subject: Subject[None] = Subject()
        self.m_pending_success: SerialDisposable = SerialDisposable()
        self.m_config: TrackerConfig = config
        self.m_resolved_profile: ResolvedDetectorProfile = self.m_registry.resolve(
            app_id=app_id,
            observed_version=observed_version,
        )
        self.m_all_events: list[TrackedStateTransition] = []
        self.m_pending_events: list[TrackedStateTransition] = []
        self.m_latest_signals: DetectedTurnSignals | None = None
        self.m_armed_turn_source: TrackedLastTurnSource | None = None
        self.m_pending_success_signature: str | None = None
        self.m_pending_success_sample_id: str | None = None
        self.m_settled_success_signature: str | None = None
        self.m_started_at_seconds: float = _absolute_seconds(self.m_scheduler.now)
        initial_signals = self.m_resolved_profile.detector.detect(output_text="")
        self.m_latest_signals = initial_signals
        self.m_state = _MutableTrackerState(
            surface_accepting_input="unknown",
            surface_editing_input="unknown",
            surface_ready_posture="unknown",
            turn_phase="unknown",
            last_turn_result="none",
            last_turn_source="none",
            detector_name=initial_signals.detector_name,
            detector_version=initial_signals.detector_version,
            active_reasons=(),
            notes=(),
        )
        self.m_state_signature: str = _state_signature(self.m_state)
        self.m_stable_since_seconds: float = 0.0
        self.m_snapshot_subject.subscribe(self._handle_snapshot_event)
        self.m_input_subject.subscribe(self._handle_input_event)

    @classmethod
    def from_config(
        cls,
        *,
        app_id: str,
        observed_version: str | None,
        config: TrackerConfig,
        scheduler: abc.SchedulerBase | None = None,
        registry: DetectorProfileRegistry | None = None,
        trace_writer: TraceWriter | None = None,
    ) -> "TuiTrackerSession":
        """Construct one tracker session from explicit configuration."""

        return cls(
            app_id=app_id,
            observed_version=observed_version,
            config=config,
            scheduler=scheduler,
            registry=registry,
            trace_writer=trace_writer,
        )

    @property
    def latest_signals(self) -> DetectedTurnSignals | None:
        """Return the latest raw detector output."""

        with self.m_lock:
            return self.m_latest_signals

    @property
    def detector_name(self) -> str:
        """Return the resolved detector family name."""

        with self.m_lock:
            return self.m_state.detector_name

    @property
    def detector_version(self) -> str:
        """Return the resolved detector profile version."""

        with self.m_lock:
            return self.m_state.detector_version

    @property
    def events(self) -> list[TrackedStateTransition]:
        """Return all emitted tracker events."""

        with self.m_lock:
            return list(self.m_all_events)

    def on_snapshot(self, raw_text: str) -> None:
        """Feed one raw snapshot string into the tracker."""

        self.m_snapshot_subject.on_next(raw_text)

    def on_input_submitted(self) -> None:
        """Record one explicit input-authority event."""

        self.m_input_subject.on_next(None)

    def current_state(self) -> TrackedStateSnapshot:
        """Return the latest tracker-owned state snapshot."""

        with self.m_lock:
            return self._snapshot_locked(at_seconds=self._current_seconds_locked())

    def drain_events(self) -> list[TrackedStateTransition]:
        """Return newly emitted tracker events and clear the pending queue."""

        with self.m_lock:
            events = list(self.m_pending_events)
            self.m_pending_events.clear()
            return events

    def close(self) -> None:
        """Dispose timer resources held by the tracker."""

        with self.m_lock:
            self.m_pending_success.dispose()

    def _handle_input_event(self, _unused: None) -> None:
        """Apply one explicit input event under lock."""

        with self.m_lock:
            self._cancel_success_timer_locked()
            self.m_armed_turn_source = "explicit_input"
            self._emit_state_locked(
                source="input",
                note="input_submitted",
                sample_id=None,
                surface_accepting_input=self.m_state.surface_accepting_input,
                surface_editing_input=self.m_state.surface_editing_input,
                surface_ready_posture=self.m_state.surface_ready_posture,
                turn_phase="active",
                last_turn_result=self.m_state.last_turn_result,
                last_turn_source=self.m_state.last_turn_source,
                detector_name=self.m_state.detector_name,
                detector_version=self.m_state.detector_version,
                active_reasons=self.m_state.active_reasons,
                notes=self.m_state.notes,
            )

    def _handle_snapshot_event(self, raw_text: str) -> None:
        """Apply one raw snapshot event under lock."""

        with self.m_lock:
            signals = self.m_resolved_profile.detector.detect(output_text=raw_text)
            self.m_latest_signals = signals
            self._trace(
                "detector_signals",
                {
                    "detector_name": signals.detector_name,
                    "detector_version": signals.detector_version,
                    "signals": signals.to_payload(),
                },
            )

            if signals.interrupted:
                self._cancel_success_timer_locked()
                self.m_settled_success_signature = None
                self._emit_state_from_signals_locked(
                    signals=signals,
                    note="interrupted_signal",
                    turn_phase="ready",
                    last_turn_result="interrupted",
                    last_turn_source=self._terminal_turn_source_locked(),
                )
                self.m_armed_turn_source = None
                return

            if signals.known_failure:
                self._cancel_success_timer_locked()
                self.m_settled_success_signature = None
                self._emit_state_from_signals_locked(
                    signals=signals,
                    note="known_failure_signal",
                    turn_phase="ready",
                    last_turn_result="known_failure",
                    last_turn_source=self._terminal_turn_source_locked(),
                )
                self.m_armed_turn_source = None
                return

            if signals.active_evidence:
                self._cancel_success_timer_locked()
                if self.m_armed_turn_source is None:
                    self.m_armed_turn_source = "surface_inference"
                self._emit_state_from_signals_locked(
                    signals=signals,
                    note="active_signal",
                    turn_phase="active",
                    last_turn_result=self.m_state.last_turn_result,
                    last_turn_source=self.m_state.last_turn_source,
                )
                return

            if signals.success_candidate:
                if (
                    self.m_state.last_turn_result == "success"
                    and self.m_settled_success_signature is not None
                    and signals.surface_signature != self.m_settled_success_signature
                ):
                    self.m_settled_success_signature = None
                    self._emit_state_from_signals_locked(
                        signals=signals,
                        note="success_invalidated",
                        turn_phase="ready",
                        last_turn_result="none",
                        last_turn_source="none",
                    )
                self._emit_state_from_signals_locked(
                    signals=signals,
                    note="success_candidate",
                    turn_phase="ready",
                    last_turn_result=self.m_state.last_turn_result,
                    last_turn_source=self.m_state.last_turn_source,
                )
                self._arm_success_timer_locked(surface_signature=signals.surface_signature)
                return

            self._cancel_success_timer_locked()
            default_phase: TurnPhase = "ready" if signals.ready_posture == "yes" else "unknown"
            self._emit_state_from_signals_locked(
                signals=signals,
                note="default_snapshot",
                turn_phase=default_phase,
                last_turn_result=self.m_state.last_turn_result,
                last_turn_source=self.m_state.last_turn_source,
            )

    def _emit_state_from_signals_locked(
        self,
        *,
        signals: DetectedTurnSignals,
        note: str,
        turn_phase: TurnPhase,
        last_turn_result: TrackedLastTurnResult,
        last_turn_source: TrackedLastTurnSource,
    ) -> None:
        """Emit one public state using the current detector payload."""

        self._emit_state_locked(
            source="snapshot",
            note=note,
            sample_id=None,
            surface_accepting_input=signals.accepting_input,
            surface_editing_input=signals.editing_input,
            surface_ready_posture=signals.ready_posture,
            turn_phase=turn_phase,
            last_turn_result=last_turn_result,
            last_turn_source=last_turn_source,
            detector_name=signals.detector_name,
            detector_version=signals.detector_version,
            active_reasons=signals.active_reasons,
            notes=signals.notes,
        )

    def _arm_success_timer_locked(self, *, surface_signature: str) -> None:
        """Arm or retain the current success timer."""

        if self.m_pending_success_signature == surface_signature:
            return
        self._cancel_success_timer_locked()
        self.m_pending_success_signature = surface_signature
        self.m_pending_success.disposable = reactivex.timer(
            timedelta(seconds=self.m_config.settle_seconds),
            scheduler=self.m_scheduler,
        ).subscribe(lambda _unused: self._handle_success_timer())
        self._trace(
            "rx_events",
            {
                "event": "success_timer_armed",
                "surface_signature": surface_signature,
                "at_seconds": self._current_seconds_locked(),
            },
        )

    def _handle_success_timer(self) -> None:
        """Settle one success candidate after the configured delay."""

        with self.m_lock:
            signals = self.m_latest_signals
            if signals is None:
                return
            if not signals.success_candidate:
                return
            if signals.current_error_present:
                return
            if signals.surface_signature != self.m_pending_success_signature:
                return
            self._emit_state_locked(
                source="timer",
                note="success_settled",
                sample_id=self.m_pending_success_sample_id,
                surface_accepting_input=signals.accepting_input,
                surface_editing_input=signals.editing_input,
                surface_ready_posture=signals.ready_posture,
                turn_phase="ready",
                last_turn_result="success",
                last_turn_source=self._terminal_turn_source_locked(),
                detector_name=signals.detector_name,
                detector_version=signals.detector_version,
                active_reasons=signals.active_reasons,
                notes=signals.notes,
            )
            self.m_settled_success_signature = self.m_pending_success_signature
            self.m_armed_turn_source = None
            self._cancel_success_timer_locked()

    def _terminal_turn_source_locked(self) -> TrackedLastTurnSource:
        """Return the best available turn source for one terminal outcome."""

        if self.m_armed_turn_source is not None:
            return self.m_armed_turn_source
        if self.m_state.last_turn_result != "none" and self.m_state.last_turn_source != "none":
            return self.m_state.last_turn_source
        return "surface_inference"

    def _cancel_success_timer_locked(self) -> None:
        """Cancel the active success timer if one exists."""

        self.m_pending_success.dispose()
        self.m_pending_success = SerialDisposable()
        if self.m_pending_success_signature is not None:
            self._trace(
                "rx_events",
                {
                    "event": "success_timer_canceled",
                    "surface_signature": self.m_pending_success_signature,
                    "at_seconds": self._current_seconds_locked(),
                },
            )
        self.m_pending_success_signature = None
        self.m_pending_success_sample_id = None

    def _emit_state_locked(
        self,
        *,
        source: str,
        note: str,
        sample_id: str | None,
        surface_accepting_input: Tristate,
        surface_editing_input: Tristate,
        surface_ready_posture: Tristate,
        turn_phase: TurnPhase,
        last_turn_result: TrackedLastTurnResult,
        last_turn_source: TrackedLastTurnSource,
        detector_name: str,
        detector_version: str,
        active_reasons: tuple[str, ...],
        notes: tuple[str, ...],
    ) -> None:
        """Apply one state change and emit a transition when it is visible."""

        next_state = _MutableTrackerState(
            surface_accepting_input=surface_accepting_input,
            surface_editing_input=surface_editing_input,
            surface_ready_posture=surface_ready_posture,
            turn_phase=turn_phase,
            last_turn_result=last_turn_result,
            last_turn_source=last_turn_source,
            detector_name=detector_name,
            detector_version=detector_version,
            active_reasons=active_reasons,
            notes=notes,
        )
        if next_state == self.m_state:
            return

        self.m_state = next_state
        if source == "snapshot" and self.m_latest_signals is not None:
            self.m_pending_success_sample_id = sample_id
        at_seconds = self._current_seconds_locked()
        next_signature = _state_signature(next_state)
        if next_signature != self.m_state_signature:
            self.m_state_signature = next_signature
            self.m_stable_since_seconds = at_seconds
        snapshot = self._snapshot_locked(at_seconds=at_seconds)
        transition = TrackedStateTransition(
            source=source,
            at_seconds=at_seconds,
            note=note,
            sample_id=sample_id,
            surface_accepting_input=snapshot.surface_accepting_input,
            surface_editing_input=snapshot.surface_editing_input,
            surface_ready_posture=snapshot.surface_ready_posture,
            turn_phase=snapshot.turn_phase,
            last_turn_result=snapshot.last_turn_result,
            last_turn_source=snapshot.last_turn_source,
            detector_name=snapshot.detector_name,
            detector_version=snapshot.detector_version,
            active_reasons=snapshot.active_reasons,
            notes=snapshot.notes,
            stability_signature=snapshot.stability_signature,
            stable=snapshot.stable,
            stable_for_seconds=snapshot.stable_for_seconds,
            stable_since_seconds=snapshot.stable_since_seconds,
        )
        self.m_all_events.append(transition)
        self.m_pending_events.append(transition)
        self._trace(
            "rx_events",
            {
                "event": "public_state_emitted",
                "source": source,
                "at_seconds": at_seconds,
                "note": note,
                "surface_accepting_input": snapshot.surface_accepting_input,
                "surface_editing_input": snapshot.surface_editing_input,
                "surface_ready_posture": snapshot.surface_ready_posture,
                "turn_phase": snapshot.turn_phase,
                "last_turn_result": snapshot.last_turn_result,
                "last_turn_source": snapshot.last_turn_source,
            },
        )

    def _snapshot_locked(self, *, at_seconds: float) -> TrackedStateSnapshot:
        """Return the current tracker snapshot under lock."""

        stable_for_seconds = max(at_seconds - self.m_stable_since_seconds, 0.0)
        return TrackedStateSnapshot(
            surface_accepting_input=self.m_state.surface_accepting_input,
            surface_editing_input=self.m_state.surface_editing_input,
            surface_ready_posture=self.m_state.surface_ready_posture,
            turn_phase=self.m_state.turn_phase,
            last_turn_result=self.m_state.last_turn_result,
            last_turn_source=self.m_state.last_turn_source,
            detector_name=self.m_state.detector_name,
            detector_version=self.m_state.detector_version,
            active_reasons=self.m_state.active_reasons,
            notes=self.m_state.notes,
            stability_signature=self.m_state_signature,
            stable=stable_for_seconds >= self.m_config.stability_threshold_seconds,
            stable_for_seconds=stable_for_seconds,
            stable_since_seconds=self.m_stable_since_seconds,
            observed_at_seconds=at_seconds,
        )

    def _current_seconds_locked(self) -> float:
        """Return current scheduler-relative seconds."""

        return max(_absolute_seconds(self.m_scheduler.now) - self.m_started_at_seconds, 0.0)

    def _trace(self, category: str, payload: dict[str, Any]) -> None:
        """Emit one optional dense trace payload."""

        if self.m_trace_writer is None:
            return
        self.m_trace_writer(category, payload)


def _absolute_seconds(value: datetime) -> float:
    """Convert one scheduler timestamp to floating-point seconds."""

    return value.timestamp()


def _state_signature(state: _MutableTrackerState) -> str:
    """Return a stable hash for one tracker state."""

    payload = json.dumps(
        {
            "surface_accepting_input": state.surface_accepting_input,
            "surface_editing_input": state.surface_editing_input,
            "surface_ready_posture": state.surface_ready_posture,
            "turn_phase": state.turn_phase,
            "last_turn_result": state.last_turn_result,
            "last_turn_source": state.last_turn_source,
            "detector_name": state.detector_name,
            "detector_version": state.detector_version,
            "active_reasons": list(state.active_reasons),
            "notes": list(state.notes),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()
