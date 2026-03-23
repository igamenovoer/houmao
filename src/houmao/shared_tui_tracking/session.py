"""Standalone reactive session for tracked TUI state."""

from __future__ import annotations

import hashlib
import json
import logging
import threading
from collections import deque
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
    RecentProfileFrame,
    TemporalHintSignals,
    TrackerEventSource,
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
LOGGER = logging.getLogger(__name__)


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
        self.m_app_id: str = app_id
        self.m_observed_version: str | None = observed_version
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
        self.m_latest_effective_signals: DetectedTurnSignals | None = None
        self.m_latest_temporal_hints: TemporalHintSignals | None = None
        self.m_recent_frames: deque[RecentProfileFrame] = deque()
        self.m_armed_turn_source: TrackedLastTurnSource | None = None
        self.m_pending_success_signature: str | None = None
        self.m_pending_success_sample_id: str | None = None
        self.m_settled_success_signature: str | None = None
        self.m_started_at_seconds: float = _absolute_seconds(self.m_scheduler.now)
        initial_signals = self.m_resolved_profile.profile.detect(output_text="")
        self.m_latest_signals = initial_signals
        self.m_latest_effective_signals = initial_signals
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
        self._log_debug(
            "tracker_session_initialized",
            app_id=self.m_app_id,
            observed_version=self.m_observed_version,
            config=self.m_config.to_payload(),
            resolved_profile={
                "app_id": self.m_resolved_profile.app_id,
                "detector_name": self.m_state.detector_name,
                "detector_version": self.m_state.detector_version,
            },
        )

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
            self._log_debug(
                "input_event_received",
                at_seconds=self._current_seconds_locked(),
                armed_turn_source_before=self.m_armed_turn_source,
                state=_summarize_mutable_tracker_state(self.m_state),
            )
            self._cancel_success_timer_locked()
            self.m_armed_turn_source = "explicit_input"
            self._log_debug(
                "turn_authority_armed",
                at_seconds=self._current_seconds_locked(),
                reason="input_submitted",
                armed_turn_source=self.m_armed_turn_source,
            )
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
            at_seconds = self._current_seconds_locked()
            signals = self.m_resolved_profile.profile.detect(output_text=raw_text)
            self.m_latest_signals = signals
            temporal_frame = self.m_resolved_profile.profile.build_temporal_frame(
                output_text=raw_text,
                signals=signals,
                observed_at_seconds=at_seconds,
            )
            if temporal_frame is not None:
                self.m_recent_frames.append(
                    RecentProfileFrame(observed_at_seconds=at_seconds, payload=temporal_frame)
                )
            self._evict_recent_frames_locked()
            temporal_hints = self.m_resolved_profile.profile.derive_temporal_hints(
                recent_frames=tuple(self.m_recent_frames)
            )
            self.m_latest_temporal_hints = temporal_hints
            effective_signals = _merge_temporal_hints(signals=signals, hints=temporal_hints)
            effective_signals = self._apply_success_authority_guard_locked(effective_signals)
            self.m_latest_effective_signals = effective_signals
            self._log_debug(
                "snapshot_processed",
                at_seconds=at_seconds,
                raw_text_length=len(raw_text),
                recent_frame_count=len(self.m_recent_frames),
                armed_turn_source=self.m_armed_turn_source,
                pending_success_signature=_short_signature(self.m_pending_success_signature),
                settled_success_signature=_short_signature(self.m_settled_success_signature),
                signals=_summarize_detected_turn_signals(signals),
                temporal_hints=_summarize_temporal_hint_signals(temporal_hints),
                effective_signals=_summarize_detected_turn_signals(effective_signals),
            )
            self._trace(
                "detector_signals",
                {
                    "detector_name": signals.detector_name,
                    "detector_version": signals.detector_version,
                    "signals": signals.to_payload(),
                },
            )
            self._trace("temporal_hints", {"hints": temporal_hints.to_payload()})
            self._trace(
                "effective_signals",
                {
                    "signals": effective_signals.to_payload(),
                },
            )

            if effective_signals.interrupted:
                self._log_debug(
                    "snapshot_decision",
                    at_seconds=at_seconds,
                    decision="interrupted_signal",
                    effective_signals=_summarize_detected_turn_signals(effective_signals),
                )
                self._cancel_success_timer_locked()
                self.m_settled_success_signature = None
                self._emit_state_from_signals_locked(
                    signals=effective_signals,
                    note="interrupted_signal",
                    turn_phase="ready",
                    last_turn_result="interrupted",
                    last_turn_source=self._terminal_turn_source_locked(),
                )
                self.m_armed_turn_source = None
                return

            if effective_signals.known_failure:
                self._log_debug(
                    "snapshot_decision",
                    at_seconds=at_seconds,
                    decision="known_failure_signal",
                    effective_signals=_summarize_detected_turn_signals(effective_signals),
                )
                self._cancel_success_timer_locked()
                self.m_settled_success_signature = None
                self._emit_state_from_signals_locked(
                    signals=effective_signals,
                    note="known_failure_signal",
                    turn_phase="ready",
                    last_turn_result="known_failure",
                    last_turn_source=self._terminal_turn_source_locked(),
                )
                self.m_armed_turn_source = None
                return

            if effective_signals.active_evidence:
                self._cancel_success_timer_locked()
                if self.m_armed_turn_source is None:
                    self.m_armed_turn_source = "surface_inference"
                    self._log_debug(
                        "turn_authority_armed",
                        at_seconds=at_seconds,
                        reason="active_surface",
                        armed_turn_source=self.m_armed_turn_source,
                        active_reasons=list(effective_signals.active_reasons),
                    )
                self._log_debug(
                    "snapshot_decision",
                    at_seconds=at_seconds,
                    decision="active_signal",
                    effective_signals=_summarize_detected_turn_signals(effective_signals),
                )
                self._emit_state_from_signals_locked(
                    signals=effective_signals,
                    note="active_signal",
                    turn_phase="active",
                    last_turn_result=self.m_state.last_turn_result,
                    last_turn_source=self.m_state.last_turn_source,
                )
                return

            if effective_signals.success_candidate:
                self._log_debug(
                    "snapshot_decision",
                    at_seconds=at_seconds,
                    decision="success_candidate",
                    effective_signals=_summarize_detected_turn_signals(effective_signals),
                )
                if (
                    self.m_state.last_turn_result == "success"
                    and self.m_settled_success_signature is not None
                    and effective_signals.surface_signature != self.m_settled_success_signature
                ):
                    self.m_settled_success_signature = None
                    self._emit_state_from_signals_locked(
                        signals=effective_signals,
                        note="success_invalidated",
                        turn_phase="ready",
                        last_turn_result="none",
                        last_turn_source="none",
                    )
                self._emit_state_from_signals_locked(
                    signals=effective_signals,
                    note="success_candidate",
                    turn_phase="ready",
                    last_turn_result=self.m_state.last_turn_result,
                    last_turn_source=self.m_state.last_turn_source,
                )
                self._arm_success_timer_locked(
                    surface_signature=effective_signals.surface_signature
                )
                return

            self._cancel_success_timer_locked()
            default_phase: TurnPhase = (
                "ready" if effective_signals.ready_posture == "yes" else "unknown"
            )
            self._log_debug(
                "snapshot_decision",
                at_seconds=at_seconds,
                decision="default_snapshot",
                default_phase=default_phase,
                effective_signals=_summarize_detected_turn_signals(effective_signals),
            )
            self._emit_state_from_signals_locked(
                signals=effective_signals,
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
            self._log_debug(
                "success_timer_retained",
                at_seconds=self._current_seconds_locked(),
                surface_signature=_short_signature(surface_signature),
            )
            return
        self._cancel_success_timer_locked()
        self.m_pending_success_signature = surface_signature
        self.m_pending_success.disposable = reactivex.timer(
            timedelta(seconds=self.m_config.settle_seconds),
            scheduler=self.m_scheduler,
        ).subscribe(lambda _unused: self._handle_success_timer())
        self._log_debug(
            "success_timer_armed",
            at_seconds=self._current_seconds_locked(),
            surface_signature=_short_signature(surface_signature),
            settle_seconds=self.m_config.settle_seconds,
        )
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
            signals = self.m_latest_effective_signals
            if signals is None:
                self._log_debug(
                    "success_timer_skipped",
                    at_seconds=self._current_seconds_locked(),
                    reason="no_effective_signals",
                )
                return
            if not signals.success_candidate:
                self._log_debug(
                    "success_timer_skipped",
                    at_seconds=self._current_seconds_locked(),
                    reason="success_candidate_cleared",
                    effective_signals=_summarize_detected_turn_signals(signals),
                )
                return
            if signals.current_error_present:
                self._log_debug(
                    "success_timer_skipped",
                    at_seconds=self._current_seconds_locked(),
                    reason="current_error_present",
                    effective_signals=_summarize_detected_turn_signals(signals),
                )
                return
            if signals.surface_signature != self.m_pending_success_signature:
                self._log_debug(
                    "success_timer_skipped",
                    at_seconds=self._current_seconds_locked(),
                    reason="surface_signature_mismatch",
                    pending_success_signature=_short_signature(self.m_pending_success_signature),
                    current_surface_signature=_short_signature(signals.surface_signature),
                )
                return
            self._log_debug(
                "success_timer_fired",
                at_seconds=self._current_seconds_locked(),
                surface_signature=_short_signature(signals.surface_signature),
                terminal_turn_source=self._terminal_turn_source_locked(),
            )
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

    def _evict_recent_frames_locked(self) -> None:
        """Evict expired profile frames from the temporal recent window."""

        window_seconds = self.m_resolved_profile.profile.temporal_window_seconds
        if window_seconds <= 0.0:
            self.m_recent_frames.clear()
            return
        cutoff_seconds = self._current_seconds_locked() - window_seconds
        while self.m_recent_frames and self.m_recent_frames[0].observed_at_seconds < cutoff_seconds:
            self.m_recent_frames.popleft()

    def _apply_success_authority_guard_locked(
        self,
        signals: DetectedTurnSignals,
    ) -> DetectedTurnSignals:
        """Return signals with ready-return success blocked until authority is armed."""

        if not signals.success_candidate:
            return signals
        if self._has_armed_turn_authority_locked():
            return signals
        if self.m_state.last_turn_result == "success" and self.m_settled_success_signature is not None:
            # Allow later same-turn observations to invalidate or reconfirm a settled success.
            return signals
        notes = tuple(dict.fromkeys((*signals.notes, "success_candidate_requires_authority")))
        self._log_debug(
            "success_candidate_blocked",
            at_seconds=self._current_seconds_locked(),
            reason="missing_turn_authority",
            armed_turn_source=self.m_armed_turn_source,
            effective_signals=_summarize_detected_turn_signals(signals),
        )
        return DetectedTurnSignals(
            detector_name=signals.detector_name,
            detector_version=signals.detector_version,
            accepting_input=signals.accepting_input,
            editing_input=signals.editing_input,
            ready_posture=signals.ready_posture,
            prompt_visible=signals.prompt_visible,
            prompt_text=signals.prompt_text,
            footer_interruptable=signals.footer_interruptable,
            active_evidence=signals.active_evidence,
            active_reasons=signals.active_reasons,
            interrupted=signals.interrupted,
            known_failure=signals.known_failure,
            current_error_present=signals.current_error_present,
            success_candidate=False,
            completion_marker=signals.completion_marker,
            latest_status_line=signals.latest_status_line,
            ambiguous_interactive_surface=signals.ambiguous_interactive_surface,
            success_blocked=True,
            surface_signature=signals.surface_signature,
            notes=notes,
        )

    def _has_armed_turn_authority_locked(self) -> bool:
        """Return whether the current session has prior armed turn authority."""

        return self.m_armed_turn_source in {"explicit_input", "surface_inference"}

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
            self._log_debug(
                "success_timer_canceled",
                at_seconds=self._current_seconds_locked(),
                surface_signature=_short_signature(self.m_pending_success_signature),
            )
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
        source: TrackerEventSource,
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

        previous_state = self.m_state
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
            self._log_debug(
                "public_state_unchanged",
                at_seconds=self._current_seconds_locked(),
                source=source,
                note=note,
                sample_id=sample_id,
                state=_summarize_mutable_tracker_state(self.m_state),
            )
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
        self._log_debug(
            "public_state_emitted",
            at_seconds=at_seconds,
            source=source,
            note=note,
            sample_id=sample_id,
            previous_state=_summarize_mutable_tracker_state(previous_state),
            next_state=_summarize_mutable_tracker_state(self.m_state),
            stability_signature=_short_signature(snapshot.stability_signature),
            stable=snapshot.stable,
            stable_for_seconds=snapshot.stable_for_seconds,
        )
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

    def _log_debug(self, event: str, **payload: Any) -> None:
        """Emit one compact structured debug log when enabled."""

        if not LOGGER.isEnabledFor(logging.DEBUG):
            return
        LOGGER.debug(
            "shared_tui_tracking.session %s",
            json.dumps({"event": event, **payload}, sort_keys=True, default=str),
        )


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


def _short_signature(value: str | None) -> str | None:
    """Return a compact prefix for one hash-like signature."""

    if value is None:
        return None
    return value[:12]


def _summarize_mutable_tracker_state(state: _MutableTrackerState) -> dict[str, Any]:
    """Return one compact debug payload for mutable tracker state."""

    return {
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
    }


def _summarize_detected_turn_signals(signals: DetectedTurnSignals) -> dict[str, Any]:
    """Return one compact debug payload for detector output."""

    return {
        "detector_name": signals.detector_name,
        "detector_version": signals.detector_version,
        "accepting_input": signals.accepting_input,
        "editing_input": signals.editing_input,
        "ready_posture": signals.ready_posture,
        "prompt_visible": signals.prompt_visible,
        "prompt_text_present": bool(signals.prompt_text),
        "prompt_text_length": len(signals.prompt_text or ""),
        "footer_interruptable": signals.footer_interruptable,
        "active_evidence": signals.active_evidence,
        "active_reasons": list(signals.active_reasons),
        "interrupted": signals.interrupted,
        "known_failure": signals.known_failure,
        "current_error_present": signals.current_error_present,
        "success_candidate": signals.success_candidate,
        "completion_marker_visible": signals.completion_marker is not None,
        "latest_status_line": signals.latest_status_line,
        "ambiguous_interactive_surface": signals.ambiguous_interactive_surface,
        "success_blocked": signals.success_blocked,
        "surface_signature": _short_signature(signals.surface_signature),
        "notes": list(signals.notes),
    }


def _summarize_temporal_hint_signals(hints: TemporalHintSignals) -> dict[str, Any]:
    """Return one compact debug payload for temporal hints."""

    return {
        "accepting_input": hints.accepting_input,
        "editing_input": hints.editing_input,
        "ready_posture": hints.ready_posture,
        "active_evidence": hints.active_evidence,
        "active_reasons": list(hints.active_reasons),
        "interrupted": hints.interrupted,
        "known_failure": hints.known_failure,
        "current_error_present": hints.current_error_present,
        "success_candidate": hints.success_candidate,
        "success_blocked": hints.success_blocked,
        "notes": list(hints.notes),
    }


def _merge_temporal_hints(
    *,
    signals: DetectedTurnSignals,
    hints: TemporalHintSignals,
) -> DetectedTurnSignals:
    """Return one effective signal payload after applying temporal hints."""

    accepting_input = (
        hints.accepting_input if hints.accepting_input is not None else signals.accepting_input
    )
    editing_input = (
        hints.editing_input if hints.editing_input is not None else signals.editing_input
    )
    ready_posture = (
        hints.ready_posture if hints.ready_posture is not None else signals.ready_posture
    )
    active_evidence = (
        hints.active_evidence if hints.active_evidence is not None else signals.active_evidence
    )
    interrupted = hints.interrupted if hints.interrupted is not None else signals.interrupted
    known_failure = (
        hints.known_failure if hints.known_failure is not None else signals.known_failure
    )
    current_error_present = (
        hints.current_error_present
        if hints.current_error_present is not None
        else signals.current_error_present
    )
    success_candidate = (
        hints.success_candidate
        if hints.success_candidate is not None
        else signals.success_candidate
    )
    success_blocked = (
        hints.success_blocked if hints.success_blocked is not None else signals.success_blocked
    )
    active_reasons = tuple(dict.fromkeys((*signals.active_reasons, *hints.active_reasons)))
    notes = tuple(dict.fromkeys((*signals.notes, *hints.notes)))
    if active_evidence and hints.active_reasons:
        success_blocked = True
    if current_error_present or interrupted or known_failure:
        success_candidate = False
        success_blocked = True
    if active_evidence and hints.ready_posture is None and ready_posture == "yes":
        ready_posture = "no"
    return DetectedTurnSignals(
        detector_name=signals.detector_name,
        detector_version=signals.detector_version,
        accepting_input=accepting_input,
        editing_input=editing_input,
        ready_posture=ready_posture,
        prompt_visible=signals.prompt_visible,
        prompt_text=signals.prompt_text,
        footer_interruptable=signals.footer_interruptable,
        active_evidence=active_evidence,
        active_reasons=active_reasons if active_evidence else (),
        interrupted=interrupted,
        known_failure=known_failure,
        current_error_present=current_error_present,
        success_candidate=success_candidate and not success_blocked,
        completion_marker=signals.completion_marker,
        latest_status_line=signals.latest_status_line,
        ambiguous_interactive_surface=signals.ambiguous_interactive_surface,
        success_blocked=success_blocked or active_evidence,
        surface_signature=signals.surface_signature,
        notes=notes,
    )
