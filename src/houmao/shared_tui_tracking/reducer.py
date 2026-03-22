"""Compatibility replay helpers over the standalone tracker session."""

from __future__ import annotations

import json
import logging
import threading
from typing import Any, Callable

from reactivex import abc
from reactivex.testing import TestScheduler

from houmao.shared_tui_tracking.models import (
    DetectedTurnSignals,
    RecordedInputEvent,
    RecordedObservation,
    ReplayEvent,
    RuntimeObservation,
    TrackerConfig,
    TrackedDiagnosticsAvailability,
    TrackedTimelineState,
)
from houmao.shared_tui_tracking.registry import app_id_from_tool
from houmao.shared_tui_tracking.session import TuiTrackerSession


TraceWriter = Callable[[str, dict[str, Any]], None]
LOGGER = logging.getLogger(__name__)


class StreamStateReducer:
    """Compatibility wrapper that replays recorded observations through the tracker session."""

    def __init__(
        self,
        *,
        tool: str,
        observed_version: str | None,
        settle_seconds: float,
        scheduler: abc.SchedulerBase,
        trace_writer: TraceWriter | None = None,
    ) -> None:
        """Initialize one compatibility reducer."""

        self.m_lock: threading.RLock = threading.RLock()
        self.m_tool: str = tool
        self.m_observed_version: str | None = observed_version
        self.m_session = TuiTrackerSession.from_config(
            app_id=app_id_from_tool(tool=tool),
            observed_version=observed_version,
            config=TrackerConfig(
                settle_seconds=settle_seconds,
                stability_threshold_seconds=0.0,
            ),
            scheduler=scheduler,
            trace_writer=trace_writer,
        )
        self.m_latest_observation: RecordedObservation | None = None
        self.m_seen_supported_process: bool = False
        self.m_all_events: list[ReplayEvent] = []
        self.m_pending_events: list[ReplayEvent] = []
        self._log_debug(
            "stream_state_reducer_initialized",
            tool=self.m_tool,
            observed_version=self.m_observed_version,
            settle_seconds=settle_seconds,
        )

    @property
    def detector_name(self) -> str:
        """Return the selected detector family name."""

        return self.m_session.detector_name

    @property
    def latest_observation(self) -> RecordedObservation | None:
        """Return the latest consumed observation."""

        with self.m_lock:
            return self.m_latest_observation

    @property
    def latest_signals(self) -> DetectedTurnSignals | None:
        """Return the latest detector payload for compatibility callers."""

        return self.m_session.latest_signals

    @property
    def events(self) -> list[ReplayEvent]:
        """Return all emitted compatibility events so far."""

        with self.m_lock:
            self._sync_events_locked(default_sample_id=None)
            return list(self.m_all_events)

    def drain_events(self) -> list[ReplayEvent]:
        """Return newly emitted compatibility events and clear the pending queue."""

        with self.m_lock:
            self._sync_events_locked(default_sample_id=None)
            events = list(self.m_pending_events)
            self.m_pending_events.clear()
            return events

    def process_input_event(self, event: RecordedInputEvent) -> None:
        """Arm explicit-input authority for a later terminal outcome."""

        with self.m_lock:
            self._log_debug(
                "input_event_processed",
                event_id=event.event_id,
                elapsed_seconds=event.elapsed_seconds,
                source=event.source,
            )
            self.m_session.on_input_submitted()
            self._sync_events_locked(default_sample_id=None, include_input_events=False)
            del event

    def process_observation(self, observation: RecordedObservation) -> TrackedTimelineState:
        """Reduce one recorded observation and return its compatibility timeline row."""

        with self.m_lock:
            self.m_latest_observation = observation
            supported_process_seen_before = self.m_seen_supported_process
            if observation.runtime is not None and observation.runtime.supported_process_alive:
                self.m_seen_supported_process = True
            availability, availability_reason = _classify_runtime_availability(
                runtime=observation.runtime,
                supported_process_seen=self.m_seen_supported_process,
            )
            if availability == "available":
                self.m_session.on_snapshot(observation.output_text)
            self._sync_events_locked(default_sample_id=observation.sample_id)
            state = self.m_session.current_state()
            timeline_state = TrackedTimelineState(
                sample_id=observation.sample_id,
                elapsed_seconds=observation.elapsed_seconds,
                ts_utc=observation.ts_utc,
                diagnostics_availability=availability,
                surface_accepting_input=state.surface_accepting_input,
                surface_editing_input=state.surface_editing_input,
                surface_ready_posture=state.surface_ready_posture,
                turn_phase=state.turn_phase if availability == "available" else "unknown",
                last_turn_result=state.last_turn_result,
                last_turn_source=state.last_turn_source,
                detector_name=state.detector_name,
                detector_version=state.detector_version,
                active_reasons=state.active_reasons,
                notes=state.notes,
            )
            self._log_debug(
                "observation_processed",
                sample_id=observation.sample_id,
                elapsed_seconds=observation.elapsed_seconds,
                output_text_length=len(observation.output_text),
                runtime=_summarize_runtime_observation(observation.runtime),
                availability=availability,
                availability_reason=availability_reason,
                supported_process_seen_before=supported_process_seen_before,
                supported_process_seen_after=self.m_seen_supported_process,
                snapshot_applied=availability == "available",
                state=_summarize_timeline_state(timeline_state),
            )
            return timeline_state

    def _sync_events_locked(
        self,
        *,
        default_sample_id: str | None,
        include_input_events: bool = True,
    ) -> None:
        """Drain pending session events into compatibility replay events."""

        synced_events: list[dict[str, Any]] = []
        for item in self.m_session.drain_events():
            if item.source == "input" and not include_input_events:
                continue
            event = ReplayEvent(
                source="observation" if item.source != "timer" else "timer",
                at_seconds=item.at_seconds,
                diagnostics_availability="available",
                turn_phase=item.turn_phase,
                last_turn_result=item.last_turn_result,
                last_turn_source=item.last_turn_source,
                sample_id=item.sample_id or default_sample_id,
                note=item.note,
            )
            self.m_all_events.append(event)
            self.m_pending_events.append(event)
            synced_events.append(
                {
                    "source": event.source,
                    "sample_id": event.sample_id,
                    "note": event.note,
                    "turn_phase": event.turn_phase,
                    "last_turn_result": event.last_turn_result,
                    "last_turn_source": event.last_turn_source,
                    "at_seconds": event.at_seconds,
                }
            )
        if synced_events:
            self._log_debug(
                "replay_events_synced",
                default_sample_id=default_sample_id,
                include_input_events=include_input_events,
                events=synced_events,
            )

    def _log_debug(self, event: str, **payload: Any) -> None:
        """Emit one compact structured reducer debug log when enabled."""

        if not LOGGER.isEnabledFor(logging.DEBUG):
            return
        LOGGER.debug(
            "shared_tui_tracking.reducer %s",
            json.dumps({"event": event, **payload}, sort_keys=True, default=str),
        )


def replay_timeline(
    *,
    observations: list[RecordedObservation],
    tool: str,
    observed_version: str | None,
    settle_seconds: float,
    input_events: list[RecordedInputEvent] | None = None,
) -> tuple[list[TrackedTimelineState], list[ReplayEvent]]:
    """Replay one recorded observation list through the compatibility reducer."""

    if LOGGER.isEnabledFor(logging.DEBUG):
        LOGGER.debug(
            "shared_tui_tracking.reducer %s",
            json.dumps(
                {
                    "event": "replay_timeline_started",
                    "tool": tool,
                    "observed_version": observed_version,
                    "observation_count": len(observations),
                    "input_event_count": len(input_events or []),
                    "settle_seconds": settle_seconds,
                },
                sort_keys=True,
                default=str,
            ),
        )
    scheduler = TestScheduler()
    tracker = StreamStateReducer(
        tool=tool,
        observed_version=observed_version,
        settle_seconds=settle_seconds,
        scheduler=scheduler,
    )
    timeline: list[TrackedTimelineState] = []

    for event in input_events or []:
        scheduler.schedule_absolute(
            event.elapsed_seconds,
            _build_input_emit_action(tracker=tracker, event=event),
        )
    for observation in observations:
        scheduler.schedule_absolute(
            observation.elapsed_seconds,
            _build_observation_emit_action(
                tracker=tracker, observation=observation, timeline=timeline
            ),
        )
    if observations:
        scheduler.advance_to(observations[-1].elapsed_seconds + settle_seconds + 1.0)
    tracker.drain_events()
    events = tracker.events
    if LOGGER.isEnabledFor(logging.DEBUG):
        LOGGER.debug(
            "shared_tui_tracking.reducer %s",
            json.dumps(
                {
                    "event": "replay_timeline_completed",
                    "tool": tool,
                    "timeline_count": len(timeline),
                    "event_count": len(events),
                    "last_sample_id": timeline[-1].sample_id if timeline else None,
                },
                sort_keys=True,
                default=str,
            ),
        )
    return timeline, events


def classify_runtime_availability(
    *,
    runtime: RuntimeObservation | None,
    supported_process_seen: bool = False,
) -> TrackedDiagnosticsAvailability:
    """Classify diagnostics availability from optional runtime evidence."""

    availability, _reason = _classify_runtime_availability(
        runtime=runtime,
        supported_process_seen=supported_process_seen,
    )
    return availability


def _classify_runtime_availability(
    *,
    runtime: RuntimeObservation | None,
    supported_process_seen: bool = False,
) -> tuple[TrackedDiagnosticsAvailability, str]:
    """Classify diagnostics availability and describe the selected reason."""

    if runtime is None:
        return "available", "no_runtime_sample"
    if not runtime.session_exists or not runtime.pane_exists:
        return "unavailable", "session_or_pane_missing"
    if runtime.pane_dead:
        return "tui_down", "pane_marked_dead"
    if runtime.supported_process_pid is not None and not runtime.supported_process_alive:
        return "tui_down", "supported_process_pid_dead"
    if supported_process_seen and not runtime.supported_process_alive:
        return "tui_down", "supported_process_missing_after_seen"
    if runtime.pane_pid is not None and not runtime.pane_pid_alive:
        return "tui_down", "pane_pid_dead"
    return "available", "runtime_healthy"


def _build_observation_emit_action(
    *,
    tracker: StreamStateReducer,
    observation: RecordedObservation,
    timeline: list[TrackedTimelineState],
) -> Callable[[abc.SchedulerBase, object | None], abc.DisposableBase | None]:
    """Return one scheduled observation emission callback."""

    def _emit(
        _scheduler: abc.SchedulerBase,
        _state: object | None = None,
    ) -> abc.DisposableBase | None:
        """Emit one observation into the compatibility reducer."""

        timeline.append(tracker.process_observation(observation))
        return None

    return _emit


def _build_input_emit_action(
    *,
    tracker: StreamStateReducer,
    event: RecordedInputEvent,
) -> Callable[[abc.SchedulerBase, object | None], abc.DisposableBase | None]:
    """Return one scheduled input emission callback."""

    def _emit(
        _scheduler: abc.SchedulerBase,
        _state: object | None = None,
    ) -> abc.DisposableBase | None:
        """Emit one input event into the compatibility reducer."""

        tracker.process_input_event(event)
        return None

    return _emit


def _summarize_runtime_observation(runtime: RuntimeObservation | None) -> dict[str, Any] | None:
    """Return one compact debug payload for runtime evidence."""

    if runtime is None:
        return None
    return {
        "session_exists": runtime.session_exists,
        "pane_exists": runtime.pane_exists,
        "pane_dead": runtime.pane_dead,
        "pane_pid": runtime.pane_pid,
        "pane_pid_alive": runtime.pane_pid_alive,
        "supported_process_pid": runtime.supported_process_pid,
        "supported_process_alive": runtime.supported_process_alive,
    }


def _summarize_timeline_state(state: TrackedTimelineState) -> dict[str, Any]:
    """Return one compact debug payload for replay timeline state."""

    return {
        "sample_id": state.sample_id,
        "diagnostics_availability": state.diagnostics_availability,
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
