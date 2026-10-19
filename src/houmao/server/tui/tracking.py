"""In-memory live tracking and reduction for server-owned TUI state."""

from __future__ import annotations

import hashlib
import json
import threading
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

import reactivex
from reactivex import abc
from reactivex.disposable import SerialDisposable
from reactivex.scheduler import HistoricalScheduler
from reactivex.subject import Subject

from houmao.hook_observation.health import HookChannelHealthSnapshot, HookChannelState
from houmao.hook_observation.models import (
    HookObservation,
    HookPosture,
    HookPostureCounters,
    HookWorkState,
)
from houmao.hook_observation.reader import HookChannelCycle, HookObservationChannel
from houmao.hook_observation.reducer import build_hook_posture_pipeline
from houmao.lifecycle import (
    AnchoredCompletionSnapshot,
    LifecycleObservation,
    ReadinessSnapshot,
    TurnAnchor,
    build_anchored_completion_pipeline,
    build_readiness_pipeline,
    normalize_projection_text,
)
from houmao.shared_tui_tracking.models import (
    TrackerConfig,
    TrackedLastTurnResult,
    TrackedLastTurnSource,
    TrackedStateSnapshot,
    TurnPhase,
)
from houmao.shared_tui_tracking.registry import UnsupportedToolVersionError, app_id_from_tool
from houmao.shared_tui_tracking.session import TuiTrackerSession
from houmao.shared_tui_tracking.public_state import (
    diagnostics_availability as shared_diagnostics_availability,
)
from houmao.shared_tui_tracking.surface import ANSI_ESCAPE_RE
from houmao.server.models import (
    CompletionState,
    HoumaoDegradedChatContextDiagnostic,
    HoumaoHookObservationCounters,
    HoumaoObservationChannel,
    HoumaoTrackedDiagnostics,
    HoumaoErrorDetail,
    HoumaoTrackedLastTurn,
    HoumaoLifecycleAuthorityMetadata,
    HoumaoLifecycleTimingMetadata,
    HoumaoOperatorState,
    HoumaoParsedSurface,
    HoumaoProbeSnapshot,
    HoumaoRecentTransition,
    HoumaoStabilityMetadata,
    HoumaoTrackedSurface,
    HoumaoTerminalHistoryResponse,
    HoumaoTerminalSnapshotHistoryEntry,
    HoumaoTerminalSnapshotHistoryResponse,
    HoumaoTerminalStateResponse,
    HoumaoTrackedTurn,
    HoumaoTrackedSessionIdentity,
    OperatorStatus,
    ParseStatus,
    ProcessState,
    ReadinessState,
    TransportState,
)
from houmao.server.tracking_debug import TrackingDebugSink


def utc_now_iso() -> str:
    """Return one current UTC timestamp string."""

    return datetime.now(UTC).isoformat(timespec="seconds")


@dataclass(frozen=True)
class SurfaceReduction:
    """Derived readiness/completion state for one tracked observation."""

    readiness_state: ReadinessState
    completion_state: CompletionState
    projection_changed: bool
    readiness_unknown_elapsed_seconds: float | None
    completion_unknown_elapsed_seconds: float | None
    completion_candidate_elapsed_seconds: float | None


@dataclass(frozen=True)
class _LostTurnAnchor:
    """Metadata for the most recent lost or invalidated turn anchor."""

    lost_at_utc: str
    reason: str


@dataclass(frozen=True)
class _StaleActiveRecoveryCandidate:
    """Recovery candidate for one stale active tracked state."""

    signature: str
    active_reasons: tuple[str, ...]


@dataclass(frozen=True)
class _FinalStableActiveRecoveryCandidate:
    """Final recovery candidate for a stable false-active tracked state."""

    signature: str
    active_reasons: tuple[str, ...]


EXPLICIT_INPUT_CORRELATION_SECONDS = 30.0
HOOK_CONFLICT_REASON_LIMIT = 8


@dataclass(frozen=True)
class _HookTurnLatch:
    """One hook terminal result latched for the current hook turn."""

    result: TrackedLastTurnResult
    error_class: str | None
    explicit_input: bool
    consumed_prompt_id: str | None
    generation: int | None
    sequence: int | None
    armed_at_monotonic: float | None
    at_utc: str
    epoch: int
    created_cycle: int

    def identity(self) -> tuple[object, ...]:
        """Return a stable identity for suppression bookkeeping."""

        return (self.generation, self.sequence, self.consumed_prompt_id, self.result, self.epoch)


@dataclass(frozen=True)
class _DegradedTuiSettlement:
    """One TUI settlement observed while the hook channel was degraded."""

    result: TrackedLastTurnResult
    source: TrackedLastTurnSource
    at_utc: str


@dataclass(frozen=True)
class _HookProjection:
    """Merged hook authority facts for one published tracked state."""

    health: HookChannelHealthSnapshot
    posture: HookPosture
    turn_phase: TurnPhase
    last_turn: HoumaoTrackedLastTurn
    work: HookWorkState
    settled: bool
    blocked: bool
    holds_lifecycle: bool
    conflict_reasons: tuple[str, ...]
    latch: _HookTurnLatch | None
    reader_orphan_generations: int = 0


class LiveSessionTracker:
    """Own one tracked session's in-memory live state and recent history."""

    def __init__(
        self,
        *,
        identity: HoumaoTrackedSessionIdentity,
        recent_transition_limit: int,
        snapshot_history_limit: int = 1000,
        stability_threshold_seconds: float,
        completion_stability_seconds: float,
        unknown_to_stalled_timeout_seconds: float,
        stale_active_recovery_seconds: float = 5.0,
        final_stable_active_recovery_seconds: float = 20.0,
        tracking_debug_sink: TrackingDebugSink | None = None,
        hook_channel: HookObservationChannel | None = None,
    ) -> None:
        """Initialize the live session tracker."""

        self.m_identity = identity
        self.m_recent_transition_limit = recent_transition_limit
        self.m_snapshot_history_limit = snapshot_history_limit
        self.m_stability_threshold_seconds = stability_threshold_seconds
        self.m_completion_stability_seconds = completion_stability_seconds
        self.m_unknown_to_stalled_timeout_seconds = unknown_to_stalled_timeout_seconds
        self.m_stale_active_recovery_seconds = stale_active_recovery_seconds
        self.m_final_stable_active_recovery_seconds = final_stable_active_recovery_seconds
        self.m_tracking_debug_sink = tracking_debug_sink
        self.m_lock = threading.RLock()
        self.m_scheduler = HistoricalScheduler()
        self.m_tracker_app_id = app_id_from_tool(tool=identity.tool)
        self.m_tracker_observed_tool_version = identity.observed_tool_version
        self.m_tracker_config = TrackerConfig(
            settle_seconds=completion_stability_seconds,
            stability_threshold_seconds=stability_threshold_seconds,
        )
        self.m_tracker_session: TuiTrackerSession | None = None
        self.m_tracker_resolution_error: UnsupportedToolVersionError | None = None
        self._create_tracker_session_locked()
        self.m_last_scheduler_monotonic: float | None = None
        self.m_observation_subject: Subject[LifecycleObservation] = Subject()
        self.m_readiness_snapshot_queue: deque[ReadinessSnapshot] = deque()
        self.m_completion_snapshot_queue: deque[AnchoredCompletionSnapshot] = deque()
        self.m_readiness_subscription: abc.DisposableBase = build_readiness_pipeline(
            self.m_observation_subject,
            stall_timeout_seconds=unknown_to_stalled_timeout_seconds,
            scheduler=self.m_scheduler,
        ).subscribe(self.m_readiness_snapshot_queue.append)
        self.m_completion_subscription: abc.DisposableBase | None = None
        self.m_last_readiness_snapshot: ReadinessSnapshot | None = None
        self.m_last_completion_snapshot: AnchoredCompletionSnapshot | None = None
        self.m_recent_transitions: list[HoumaoRecentTransition] = []
        self.m_recent_snapshots: list[HoumaoTerminalSnapshotHistoryEntry] = []
        self.m_last_signature_payload: str | None = None
        self.m_stable_since_monotonic: float | None = None
        self.m_stable_since_utc: str = utc_now_iso()
        self.m_baseline_pos: int | None = None
        self.m_cycle_seq = 0
        self.m_next_anchor_id = 1
        self.m_active_turn_anchor: TurnAnchor | None = None
        self.m_active_turn_previous_last_turn: HoumaoTrackedLastTurn
        self.m_lost_turn_anchor: _LostTurnAnchor | None = None
        self.m_anchor_should_expire_after_publish = False
        self.m_last_published_turn_anchor_id: int | None = None
        self.m_pending_stale_active_recovery: SerialDisposable = SerialDisposable()
        self.m_pending_stale_active_recovery_signature: str | None = None
        self.m_recovered_stale_active_signature: str | None = None
        self.m_pending_final_stable_active_recovery: SerialDisposable = SerialDisposable()
        self.m_pending_final_stable_active_recovery_signature: str | None = None
        self.m_recovered_final_stable_active_signature: str | None = None
        self.m_last_state = _build_initial_state(
            identity=identity,
            completion_stability_seconds=completion_stability_seconds,
            unknown_to_stalled_timeout_seconds=unknown_to_stalled_timeout_seconds,
            stale_active_recovery_seconds=stale_active_recovery_seconds,
            final_stable_active_recovery_seconds=final_stable_active_recovery_seconds,
        )
        self.m_active_turn_previous_last_turn = self.m_last_state.last_turn
        self.m_hook_channel: HookObservationChannel | None = None
        self.m_hook_subject: Subject[HookObservation] | None = None
        self.m_hook_posture_queue: deque[HookPosture] = deque()
        self.m_hook_posture: HookPosture | None = None
        self.m_hook_previous_posture: HookPosture | None = None
        self.m_hook_subscription: abc.DisposableBase | None = None
        self.m_hook_health: HookChannelHealthSnapshot | None = None
        self.m_hook_last_cycle: HookChannelCycle | None = None
        self.m_hook_cycle_reasons: tuple[str, ...] = ()
        self.m_hook_previous_counters: HookPostureCounters | None = None
        self.m_hook_latch: _HookTurnLatch | None = None
        self.m_hook_suppressed_latch_identity: tuple[object, ...] | None = None
        self.m_hook_pending_explicit: deque[float] = deque(maxlen=32)
        self.m_hook_armed_explicit: deque[bool] = deque()
        self.m_hook_armed_at_monotonic: deque[float] = deque()
        self.m_hook_armed_epochs: deque[int] = deque()
        self.m_hook_next_turn_epoch: int = 0
        self.m_hook_blocked_cleared_key: tuple[int | None, int | None] | None = None
        self.m_hook_blocked_key: tuple[int | None, int | None] | None = None
        self.m_hook_tui_interrupt_epoch: int | None = None
        self.m_hook_tui_interrupt_applied_epoch: int | None = None
        self.m_hook_maintenance_epoch: int | None = None
        self.m_hook_reader_orphan_generations: int = 0
        self.m_hook_degraded_tui_settlement: _DegradedTuiSettlement | None = None
        self.m_hook_recovered_this_cycle: bool = False
        self.m_hook_previous_health_state: HookChannelState | None = None
        self.m_hook_last_tui_signature: str | None = None
        self.m_hook_previous_tui_last_turn_result: TrackedLastTurnResult = "none"
        self.m_previous_parsed_ui_context: str | None = None
        if hook_channel is not None:
            self._attach_hook_channel_locked(hook_channel)
        if self.m_tracker_resolution_error is not None:
            self.m_last_state = self.m_last_state.model_copy(
                update={
                    "operator_state": HoumaoOperatorState(
                        status="error",
                        readiness_state="unknown",
                        completion_state="inactive",
                        detail=str(self.m_tracker_resolution_error),
                        projection_changed=False,
                        updated_at_utc=utc_now_iso(),
                    )
                }
            )

    @property
    def baseline_pos(self) -> int | None:
        """Return the current parser baseline position."""

        with self.m_lock:
            return self.m_baseline_pos

    def set_baseline_pos(self, value: int | None) -> None:
        """Update the parser baseline position."""

        with self.m_lock:
            self.m_baseline_pos = value

    def set_identity(self, identity: HoumaoTrackedSessionIdentity) -> None:
        """Refresh tracked-session identity while preserving live state."""

        with self.m_lock:
            self.m_identity = identity
            tracker_rebuilt = self._ensure_tracker_session_locked(
                tool=identity.tool,
                observed_tool_version=identity.observed_tool_version,
            )
            update: dict[str, object] = {
                "terminal_id": _terminal_alias(identity),
                "tracked_session": identity,
            }
            if tracker_rebuilt:
                tracker_session = self.m_tracker_session
                assert tracker_session is not None
                tracker_state = tracker_session.current_state()
                update.update(
                    {
                        "surface": HoumaoTrackedSurface(
                            accepting_input=tracker_state.surface_accepting_input,
                            editing_input=tracker_state.surface_editing_input,
                            ready_posture=tracker_state.surface_ready_posture,
                            pending_input=tracker_state.surface_pending_input,
                        ),
                        "turn": HoumaoTrackedTurn(phase=tracker_state.turn_phase),
                        "last_turn": HoumaoTrackedLastTurn(
                            result=tracker_state.last_turn_result,
                            source=tracker_state.last_turn_source,
                            updated_at_utc=None,
                        ),
                        "chat_context": tracker_state.chat_context,
                        "chat_context_diagnostic": _build_chat_context_diagnostic(tracker_state),
                    }
                )
            self.m_last_state = self.m_last_state.model_copy(update=update)

    @property
    def tracking_error(self) -> UnsupportedToolVersionError | None:
        """Return the tracker resolution error when the session is unsupported."""

        return self.m_tracker_resolution_error

    @property
    def hook_channel_state(self) -> HookChannelState | None:
        """Return the hook observation channel health state, when configured."""

        with self.m_lock:
            if self.m_hook_health is None:
                return None
            return self.m_hook_health.state

    def ensure_hook_channel_from_session_root(self, session_root: str | None) -> bool:
        """Attach the session-local hook channel when one becomes available.

        Parameters
        ----------
        session_root:
            Session root that owns the hook subtree.

        Returns
        -------
        bool
            Whether a channel is attached after this call.
        """

        with self.m_lock:
            if self.m_hook_channel is not None:
                return True
            if self.m_identity.tool != "claude":
                return False
            channel = HookObservationChannel.from_session_root(session_root)
            if channel is None:
                return False
            self._attach_hook_channel_locked(channel)
            return True

    def _attach_hook_channel_locked(self, channel: HookObservationChannel) -> None:
        """Attach one hook channel and its posture pipeline to this tracker."""

        self.m_hook_channel = channel
        self.m_hook_subject = Subject()
        self.m_hook_posture_queue = deque()
        self.m_hook_posture = channel.reducer.posture
        self.m_hook_previous_posture = self.m_hook_posture
        self.m_hook_subscription = build_hook_posture_pipeline(
            self.m_hook_subject,
            scheduler=self.m_scheduler,
            reducer=channel.reducer,
        ).subscribe(self.m_hook_posture_queue.append)
        self.m_hook_health = channel.health.snapshot()
        self.m_hook_previous_health_state = self.m_hook_health.state
        self.m_hook_previous_counters = channel.reducer.posture.counters

    @property
    def resolved_detector_version(self) -> str | None:
        """Return the resolved detector profile version for parser provenance."""

        session = self.m_tracker_session
        return session.detector_version if session is not None else None

    def _create_tracker_session_locked(self) -> None:
        """Build the standalone tracker, containing unsupported-version errors."""

        try:
            self.m_tracker_session = TuiTrackerSession.from_config(
                app_id=self.m_tracker_app_id,
                observed_version=self.m_tracker_observed_tool_version,
                config=self.m_tracker_config,
                scheduler=self.m_scheduler,
            )
        except UnsupportedToolVersionError as exc:
            self.m_tracker_session = None
            self.m_tracker_resolution_error = exc
        else:
            self.m_tracker_resolution_error = None

    def _degraded_tracker_state(self) -> TrackedStateSnapshot:
        """Return the placeholder tracker state for an unsupported-version session."""

        error = self.m_tracker_resolution_error
        return TrackedStateSnapshot(
            surface_accepting_input="unknown",
            surface_editing_input="unknown",
            surface_ready_posture="unknown",
            surface_pending_input="unknown",
            turn_phase="unknown",
            last_turn_result="none",
            last_turn_source="none",
            detector_name=self.m_tracker_app_id,
            detector_version="unsupported",
            active_reasons=(),
            notes=(
                ("unsupported_tool_version", str(error))
                if error is not None
                else ("unsupported_tool_version",)
            ),
            stability_signature="",
            stable=False,
            stable_for_seconds=0.0,
            stable_since_seconds=0.0,
            observed_at_seconds=0.0,
        )

    def _ensure_tracker_session_locked(
        self,
        *,
        tool: str,
        observed_tool_version: str | None,
    ) -> bool:
        """Rebuild the standalone tracker when the tracked detector identity changes."""

        tracker_app_id = app_id_from_tool(tool=tool)
        if (
            tracker_app_id == self.m_tracker_app_id
            and observed_tool_version == self.m_tracker_observed_tool_version
        ):
            return False
        self._cancel_stale_active_recovery_locked(reason="tracker_rebuilt")
        self._cancel_final_stable_active_recovery_locked(reason="tracker_rebuilt")
        if self.m_tracker_session is not None:
            self.m_tracker_session.close()
        self.m_tracker_app_id = tracker_app_id
        self.m_tracker_observed_tool_version = observed_tool_version
        self._create_tracker_session_locked()
        return self.m_tracker_session is not None

    def current_state(self) -> HoumaoTerminalStateResponse:
        """Return the latest in-memory live state."""

        with self.m_lock:
            return self.m_last_state

    def history(self, *, limit: int) -> HoumaoTerminalHistoryResponse:
        """Return bounded recent in-memory transitions."""

        with self.m_lock:
            entries = list(
                self.m_recent_transitions[-limit:] if limit > 0 else self.m_recent_transitions
            )
            return HoumaoTerminalHistoryResponse(
                terminal_id=self.m_last_state.terminal_id,
                tracked_session_id=self.m_identity.tracked_session_id,
                entries=entries,
            )

    def snapshot_history(self, *, limit: int) -> HoumaoTerminalSnapshotHistoryResponse:
        """Return bounded recent in-memory snapshot history."""

        with self.m_lock:
            entries = list(
                self.m_recent_snapshots[-limit:] if limit > 0 else self.m_recent_snapshots
            )
            return HoumaoTerminalSnapshotHistoryResponse(
                terminal_id=self.m_last_state.terminal_id,
                tracked_session_id=self.m_identity.tracked_session_id,
                entries=entries,
            )

    def _emit_debug(
        self,
        *,
        stream: str,
        event_type: str,
        monotonic_ts: float | None = None,
        cycle_seq: int | None = None,
        anchor_id: int | None = None,
        data: dict[str, object] | None = None,
    ) -> None:
        """Emit one structured tracker debug event when enabled."""

        if self.m_tracking_debug_sink is None:
            return
        self.m_tracking_debug_sink.emit(
            stream=stream,
            event_type=event_type,
            monotonic_ts=monotonic_ts,
            terminal_id=self.m_last_state.terminal_id,
            tracked_session_id=self.m_identity.tracked_session_id,
            tool=self.m_identity.tool,
            cycle_seq=cycle_seq,
            anchor_id=anchor_id,
            data=data,
        )

    def _arm_turn_anchor(
        self,
        *,
        source: Literal["terminal_input"],
        baseline_projection_text: str,
        observed_at_utc: str,
        monotonic_ts: float,
        message_excerpt: str | None,
        cycle_seq: int | None = None,
        reason: str | None = None,
    ) -> TurnAnchor:
        """Arm one active turn anchor and completion subscription."""

        self._dispose_completion_subscription()
        anchor = TurnAnchor(
            anchor_id=self.m_next_anchor_id,
            source=source,
            baseline_projection_text=baseline_projection_text,
            armed_at_utc=observed_at_utc,
            armed_monotonic_ts=monotonic_ts,
            message_excerpt=message_excerpt,
        )
        self.m_active_turn_anchor = anchor
        self.m_active_turn_previous_last_turn = self.m_last_state.last_turn
        self.m_next_anchor_id += 1
        self.m_lost_turn_anchor = None
        self.m_last_published_turn_anchor_id = None
        self.m_last_completion_snapshot = None
        self.m_anchor_should_expire_after_publish = False
        self.m_completion_subscription = build_anchored_completion_pipeline(
            self.m_observation_subject,
            baseline_projection_text=baseline_projection_text,
            stability_seconds=self.m_completion_stability_seconds,
            stall_timeout_seconds=self.m_unknown_to_stalled_timeout_seconds,
            scheduler=self.m_scheduler,
        ).subscribe(self.m_completion_snapshot_queue.append)
        self._emit_debug(
            stream="tracker-anchor",
            event_type="turn_anchor_armed",
            monotonic_ts=monotonic_ts,
            cycle_seq=cycle_seq,
            anchor_id=anchor.anchor_id,
            data={
                "source": source,
                "reason": reason,
                "message_excerpt": message_excerpt,
                "baseline_projection_sha1": _sha1_text(baseline_projection_text),
                "baseline_projection_length": len(baseline_projection_text),
            },
        )
        return anchor

    def note_prompt_submission(
        self,
        *,
        message: str,
        observed_at_utc: str,
        monotonic_ts: float,
    ) -> HoumaoTerminalStateResponse:
        """Arm one server-owned turn anchor after a successful input submission."""

        with self.m_lock:
            self._ensure_tracker_session_locked(
                tool=self.m_identity.tool,
                observed_tool_version=self.m_identity.observed_tool_version,
            )
            self._cancel_stale_active_recovery_locked(reason="input_submitted")
            self._cancel_final_stable_active_recovery_locked(reason="input_submitted")
            self._advance_scheduler(monotonic_ts=monotonic_ts)
            self._drain_pipeline_snapshots()
            if self.m_hook_channel is not None:
                self.m_hook_latch = None
                self.m_hook_suppressed_latch_identity = None
                self.m_hook_tui_interrupt_epoch = None
                self.m_hook_pending_explicit.append(monotonic_ts)
            if self.m_tracker_session is not None:
                self.m_tracker_session.on_input_submitted()

            baseline_projection_text = ""
            if self.m_last_state.parsed_surface is not None:
                baseline_projection_text = normalize_projection_text(
                    self.m_last_state.parsed_surface.normalized_projection_text
                )
            anchor = self._arm_turn_anchor(
                source="terminal_input",
                baseline_projection_text=baseline_projection_text,
                observed_at_utc=observed_at_utc,
                monotonic_ts=monotonic_ts,
                message_excerpt=_message_excerpt(message),
                reason="server_input_route",
            )

            operator_state = _require_operator_state(self.m_last_state)
            if operator_state.completion_state in {"candidate_complete", "completed"}:
                operator_status: OperatorStatus = operator_state.status
                if operator_status == "completed" and operator_state.readiness_state == "ready":
                    operator_status = "ready"
                operator_state = operator_state.model_copy(
                    update={
                        "status": operator_status,
                        "completion_state": "inactive",
                        "detail": "Server accepted input and armed turn-anchored completion monitoring.",
                        "projection_changed": False,
                        "updated_at_utc": observed_at_utc,
                    }
                )

            lifecycle_authority = self._current_lifecycle_authority()
            lifecycle_timing = _require_lifecycle_timing(self.m_last_state)
            tracker_state = (
                self.m_tracker_session.current_state()
                if self.m_tracker_session is not None
                else self._degraded_tracker_state()
            )
            self._note_tui_last_turn_transition_locked(
                tracker_state=tracker_state,
                monotonic_ts=monotonic_ts,
                observed_at_utc=observed_at_utc,
            )
            hook_projection = self._project_hook_state_locked(
                tracker_state=tracker_state,
                previous_last_turn=self.m_last_state.last_turn,
                observed_at_utc=observed_at_utc,
            )
            published_work: HookWorkState = (
                hook_projection.work if hook_projection is not None else "unknown"
            )
            published_phase = tracker_state.turn_phase
            updated = self.m_last_state.model_copy(
                update={
                    "surface": HoumaoTrackedSurface(
                        accepting_input=tracker_state.surface_accepting_input,
                        editing_input=tracker_state.surface_editing_input,
                        ready_posture=tracker_state.surface_ready_posture,
                        pending_input=tracker_state.surface_pending_input,
                    ),
                    "turn": HoumaoTrackedTurn(phase=published_phase),
                    "last_turn": _build_tracker_last_turn(
                        previous=self.m_last_state.last_turn,
                        tracker_state=tracker_state,
                        observed_at_utc=observed_at_utc,
                    ),
                    "chat_context": tracker_state.chat_context,
                    "chat_context_diagnostic": _build_chat_context_diagnostic(tracker_state),
                    "diagnostics": _update_diagnostics_with_hook(
                        self.m_last_state.diagnostics, hook_projection
                    ),
                    "work": published_work,
                    "settled": published_phase == "ready" and published_work == "clear",
                    "observation_channels": _build_observation_channels(hook_projection),
                    "operator_state": operator_state,
                    "lifecycle_timing": lifecycle_timing.model_copy(
                        update={"completion_candidate_elapsed_seconds": None}
                    ),
                    "lifecycle_authority": lifecycle_authority,
                }
            )
            updated = self._publish_state(
                response=updated,
                monotonic_ts=monotonic_ts,
                observed_at_utc=observed_at_utc,
            )
            updated_lifecycle_authority = _require_lifecycle_authority(updated)
            self._emit_debug(
                stream="tracker-anchor",
                event_type="note_prompt_submission_applied",
                monotonic_ts=monotonic_ts,
                anchor_id=anchor.anchor_id,
                data={
                    "completion_authority": updated_lifecycle_authority.completion_authority,
                    "turn_anchor_state": updated_lifecycle_authority.turn_anchor_state,
                    "completion_monitoring_armed": updated_lifecycle_authority.completion_monitoring_armed,
                },
            )
            return updated

    def record_cycle(
        self,
        *,
        identity: HoumaoTrackedSessionIdentity,
        observed_at_utc: str,
        monotonic_ts: float,
        transport_state: TransportState,
        process_state: ProcessState,
        parse_status: ParseStatus,
        probe_snapshot: HoumaoProbeSnapshot | None,
        probe_error: HoumaoErrorDetail | None,
        parse_error: HoumaoErrorDetail | None,
        parsed_surface: HoumaoParsedSurface | None,
        output_text: str | None = None,
    ) -> HoumaoTerminalStateResponse:
        """Record one tracking cycle and return the updated public state."""

        with self.m_lock:
            self.m_identity = identity
            self._ensure_tracker_session_locked(
                tool=identity.tool,
                observed_tool_version=identity.observed_tool_version,
            )
            self.m_cycle_seq += 1
            cycle_seq = self.m_cycle_seq
            self._advance_scheduler(monotonic_ts=monotonic_ts)
            self._drain_pipeline_snapshots()
            self._drain_hook_channel_locked(
                monotonic_ts=monotonic_ts,
                observed_at_utc=observed_at_utc,
                output_text=output_text,
            )
            if output_text is not None and self.m_tracker_session is not None:
                self.m_tracker_session.on_snapshot(output_text)
            previous_operator_state = _require_operator_state(self.m_last_state)
            previous_lifecycle_authority = _require_lifecycle_authority(self.m_last_state)
            self._emit_debug(
                stream="tracker-cycle",
                event_type="record_cycle_start",
                monotonic_ts=monotonic_ts,
                cycle_seq=cycle_seq,
                data={
                    "transport_state": transport_state,
                    "process_state": process_state,
                    "parse_status": parse_status,
                    "probe_error": _error_message(probe_error),
                    "parse_error": _error_message(parse_error),
                    "output_text_length": len(output_text) if output_text is not None else 0,
                    "parsed_surface": _parsed_surface_debug_payload(parsed_surface),
                    "previous_operator_status": previous_operator_state.status,
                    "previous_completion_state": previous_operator_state.completion_state,
                    "previous_completion_authority": previous_lifecycle_authority.completion_authority,
                    "previous_turn_anchor_state": previous_lifecycle_authority.turn_anchor_state,
                },
            )

            reduction = _default_surface_reduction()
            if parsed_surface is not None:
                self._emit_debug(
                    stream="tracker-cycle",
                    event_type="lifecycle_observation_emitted",
                    monotonic_ts=monotonic_ts,
                    cycle_seq=cycle_seq,
                    anchor_id=(
                        self.m_active_turn_anchor.anchor_id
                        if self.m_active_turn_anchor is not None
                        else None
                    ),
                    data=_parsed_surface_debug_payload(parsed_surface),
                )
                self.m_observation_subject.on_next(
                    _lifecycle_observation_from_parsed_surface(
                        parsed_surface=parsed_surface,
                        monotonic_ts=monotonic_ts,
                    )
                )
                self._drain_pipeline_snapshots()
                reduction = self._reduction_from_current_snapshots(
                    parsed_surface=parsed_surface,
                    cycle_seq=cycle_seq,
                )
            elif self.m_active_turn_anchor is not None:
                self._lose_turn_anchor(
                    lost_at_utc=observed_at_utc,
                    reason=_anchor_loss_reason(
                        transport_state=transport_state,
                        process_state=process_state,
                        parse_status=parse_status,
                        probe_error=probe_error,
                        parse_error=parse_error,
                    ),
                    monotonic_ts=monotonic_ts,
                    cycle_seq=cycle_seq,
                )

            lifecycle_authority = self._current_lifecycle_authority()
            operator_state = _build_operator_state(
                identity=identity,
                observed_at_utc=observed_at_utc,
                transport_state=transport_state,
                process_state=process_state,
                parse_status=parse_status,
                probe_error=probe_error,
                parse_error=parse_error,
                parsed_surface=parsed_surface,
                reduction=reduction,
            )
            self._emit_debug(
                stream="tracker-operator-state",
                event_type="operator_state_built",
                monotonic_ts=monotonic_ts,
                cycle_seq=cycle_seq,
                anchor_id=(
                    self.m_active_turn_anchor.anchor_id
                    if self.m_active_turn_anchor is not None
                    else None
                ),
                data={
                    "status": operator_state.status,
                    "readiness_state": operator_state.readiness_state,
                    "completion_state": operator_state.completion_state,
                    "projection_changed": operator_state.projection_changed,
                    "detail": operator_state.detail,
                },
            )
            diagnostics = _build_tracked_diagnostics(
                transport_state=transport_state,
                process_state=process_state,
                parse_status=parse_status,
                probe_error=probe_error,
                parse_error=parse_error,
                parsed_surface=parsed_surface,
            )
            tracker_state = (
                self.m_tracker_session.current_state()
                if self.m_tracker_session is not None
                else self._degraded_tracker_state()
            )
            self._note_tui_last_turn_transition_locked(
                tracker_state=tracker_state,
                monotonic_ts=monotonic_ts,
                observed_at_utc=observed_at_utc,
            )
            self._note_tui_evidence_locked(
                parsed_surface=parsed_surface,
                monotonic_ts=monotonic_ts,
                observed_at_utc=observed_at_utc,
            )
            hook_projection = self._project_hook_state_locked(
                tracker_state=tracker_state,
                previous_last_turn=self.m_last_state.last_turn,
                observed_at_utc=observed_at_utc,
            )
            diagnostics = _update_diagnostics_with_hook(diagnostics, hook_projection)
            if self.m_active_turn_anchor is not None:
                active_anchor_id = self.m_active_turn_anchor.anchor_id
                if tracker_state.last_turn_result in {"success", "interrupted", "known_failure"}:
                    if (
                        active_anchor_id == self.m_last_published_turn_anchor_id
                        and self.m_last_state.last_turn.result == tracker_state.last_turn_result
                    ):
                        self.m_anchor_should_expire_after_publish = True
                    else:
                        self.m_last_published_turn_anchor_id = active_anchor_id
                else:
                    self.m_last_published_turn_anchor_id = None
            surface = HoumaoTrackedSurface(
                accepting_input=tracker_state.surface_accepting_input,
                editing_input=tracker_state.surface_editing_input,
                ready_posture=tracker_state.surface_ready_posture,
                pending_input=tracker_state.surface_pending_input,
            )
            last_turn = (
                hook_projection.last_turn
                if hook_projection is not None
                else _build_tracker_last_turn(
                    previous=self.m_last_state.last_turn,
                    tracker_state=tracker_state,
                    observed_at_utc=observed_at_utc,
                )
            )
            turn = HoumaoTrackedTurn(
                phase=(
                    hook_projection.turn_phase
                    if hook_projection is not None
                    else tracker_state.turn_phase
                )
            )
            operator_state = _align_operator_state_with_tracker_state(
                operator_state=operator_state,
                tracker_state=tracker_state,
                diagnostics=diagnostics,
                observed_at_utc=observed_at_utc,
                merged_turn_phase=turn.phase,
                hook_failure=(
                    hook_projection is not None
                    and hook_projection.latch is not None
                    and hook_projection.latch.result == "known_failure"
                    and self.m_hook_suppressed_latch_identity != hook_projection.latch.identity()
                ),
            )
            if self.m_tracker_resolution_error is not None:
                operator_state = operator_state.model_copy(
                    update={
                        "status": "error",
                        "detail": str(self.m_tracker_resolution_error),
                        "updated_at_utc": observed_at_utc,
                    }
                )
            stale_active_candidate = _build_stale_active_recovery_candidate(
                parsed_surface=parsed_surface,
                diagnostics=diagnostics,
                surface=surface,
                turn=turn,
                tracker_state=tracker_state,
                active_turn_anchor_present=self.m_active_turn_anchor is not None,
                hook_lifecycle_hold=(
                    hook_projection.holds_lifecycle if hook_projection is not None else False
                ),
            )
            stale_active_recovered = self._update_stale_active_recovery_locked(
                candidate=stale_active_candidate,
                monotonic_ts=monotonic_ts,
                cycle_seq=cycle_seq,
            )
            self._emit_debug(
                stream="tracker-public-state",
                event_type="public_state_built",
                monotonic_ts=monotonic_ts,
                cycle_seq=cycle_seq,
                anchor_id=(
                    self.m_active_turn_anchor.anchor_id
                    if self.m_active_turn_anchor is not None
                    else None
                ),
                data={
                    "diagnostics_availability": diagnostics.availability,
                    "turn_phase": turn.phase,
                    "last_turn_result": last_turn.result,
                    "last_turn_source": last_turn.source,
                    "chat_context": tracker_state.chat_context,
                    "accepting_input": surface.accepting_input,
                    "editing_input": surface.editing_input,
                    "ready_posture": surface.ready_posture,
                    "signal_notes": list(tracker_state.notes),
                },
            )
            if stale_active_recovered:
                surface = surface.model_copy(update={"ready_posture": "yes"})
                turn = turn.model_copy(update={"phase": "ready"})
                operator_state = operator_state.model_copy(
                    update={
                        "status": "ready",
                        "readiness_state": "ready",
                        "detail": (
                            "Tracker recovered a stale active phase after "
                            f"{self.m_stale_active_recovery_seconds:.1f} seconds of stable "
                            "submit-ready posture."
                        ),
                        "updated_at_utc": observed_at_utc,
                    }
                )
                self._emit_debug(
                    stream="tracker-recovery",
                    event_type="stale_active_recovery_applied",
                    monotonic_ts=monotonic_ts,
                    cycle_seq=cycle_seq,
                    data={
                        "recovery_signature_sha1": _sha1_text(
                            stale_active_candidate.signature
                            if stale_active_candidate is not None
                            else None
                        ),
                        "active_reasons": list(
                            stale_active_candidate.active_reasons
                            if stale_active_candidate is not None
                            else ()
                        ),
                    },
                )
            final_stable_active_candidate = _build_final_stable_active_recovery_candidate(
                turn=turn,
                rendered_surface_signature=_rendered_surface_signature(output_text),
                hook_lifecycle_hold=(
                    hook_projection.holds_lifecycle if hook_projection is not None else False
                ),
            )
            final_stable_active_recovered = self._update_final_stable_active_recovery_locked(
                candidate=final_stable_active_candidate,
                monotonic_ts=monotonic_ts,
                cycle_seq=cycle_seq,
            )
            if final_stable_active_recovered:
                surface = surface.model_copy(update={"ready_posture": "yes"})
                turn = turn.model_copy(update={"phase": "ready"})
                operator_state = operator_state.model_copy(
                    update={
                        "status": "ready",
                        "readiness_state": "ready",
                        "detail": (
                            "Tracker recovered a stable false-active phase after "
                            f"{self.m_final_stable_active_recovery_seconds:.1f} seconds of "
                            "unchanged prompt-ready posture."
                        ),
                        "updated_at_utc": observed_at_utc,
                    }
                )
                self._expire_turn_anchor_for_final_recovery_locked(
                    observed_at_utc=observed_at_utc,
                    monotonic_ts=monotonic_ts,
                    cycle_seq=cycle_seq,
                )
                lifecycle_authority = self._current_lifecycle_authority()
                self._emit_debug(
                    stream="tracker-recovery",
                    event_type="final_stable_active_recovery_applied",
                    monotonic_ts=monotonic_ts,
                    cycle_seq=cycle_seq,
                    data={
                        "recovery_signature_sha1": _sha1_text(
                            final_stable_active_candidate.signature
                            if final_stable_active_candidate is not None
                            else None
                        ),
                        "active_reasons": list(
                            final_stable_active_candidate.active_reasons
                            if final_stable_active_candidate is not None
                            else ()
                        ),
                    },
                )
            stability = self._build_stability(
                diagnostics=diagnostics,
                parsed_surface=parsed_surface,
                surface=surface,
                turn=turn,
                last_turn=last_turn,
                chat_context=tracker_state.chat_context,
                chat_context_diagnostic=_build_chat_context_diagnostic(tracker_state),
                monotonic_ts=monotonic_ts,
                observed_at_utc=observed_at_utc,
                cycle_seq=cycle_seq,
            )
            response = HoumaoTerminalStateResponse(
                terminal_id=_terminal_alias(identity),
                tracked_session=identity,
                diagnostics=diagnostics,
                transport_state=transport_state,
                process_state=process_state,
                parse_status=parse_status,
                probe_snapshot=probe_snapshot,
                probe_error=probe_error,
                parse_error=parse_error,
                parsed_surface=parsed_surface,
                surface=surface,
                turn=turn,
                last_turn=last_turn,
                chat_context=tracker_state.chat_context,
                chat_context_diagnostic=_build_chat_context_diagnostic(tracker_state),
                work=hook_projection.work if hook_projection is not None else "unknown",
                settled=hook_projection.settled if hook_projection is not None else False,
                observation_channels=_build_observation_channels(hook_projection),
                operator_state=operator_state,
                lifecycle_timing=HoumaoLifecycleTimingMetadata(
                    readiness_unknown_elapsed_seconds=reduction.readiness_unknown_elapsed_seconds,
                    completion_unknown_elapsed_seconds=reduction.completion_unknown_elapsed_seconds,
                    completion_candidate_elapsed_seconds=reduction.completion_candidate_elapsed_seconds,
                    unknown_to_stalled_timeout_seconds=self.m_unknown_to_stalled_timeout_seconds,
                    completion_stability_seconds=self.m_completion_stability_seconds,
                    stale_active_recovery_seconds=self.m_stale_active_recovery_seconds,
                    final_stable_active_recovery_seconds=(
                        self.m_final_stable_active_recovery_seconds
                    ),
                ),
                lifecycle_authority=lifecycle_authority,
                stability=stability,
                recent_transitions=list(self.m_recent_transitions),
            )
            response = self._publish_state(
                response=response,
                monotonic_ts=monotonic_ts,
                observed_at_utc=observed_at_utc,
            )
            if self.m_anchor_should_expire_after_publish:
                self._expire_turn_anchor_after_publish(
                    monotonic_ts=monotonic_ts,
                    cycle_seq=cycle_seq,
                )
            return response

    def _reduction_from_current_snapshots(
        self,
        *,
        parsed_surface: HoumaoParsedSurface,
        cycle_seq: int,
    ) -> SurfaceReduction:
        """Build the current surface reduction from the latest shared-kernel snapshots."""

        readiness_snapshot = self.m_last_readiness_snapshot
        if readiness_snapshot is None:
            raise RuntimeError("Readiness snapshot is missing after parsed observation emission.")

        if self.m_active_turn_anchor is not None and self.m_last_completion_snapshot is not None:
            completion_snapshot = self.m_last_completion_snapshot
            completion_state: CompletionState = completion_snapshot.status
            completion_unknown_elapsed_seconds = completion_snapshot.unknown_elapsed_seconds
            completion_candidate_elapsed_seconds = completion_snapshot.candidate_elapsed_seconds
            projection_changed = completion_snapshot.projection_changed
            self._emit_debug(
                stream="tracker-reduction",
                event_type="reduction_anchored_snapshot",
                monotonic_ts=completion_snapshot.observation.monotonic_ts,
                cycle_seq=cycle_seq,
                anchor_id=self.m_active_turn_anchor.anchor_id,
                data={
                    "readiness_state": readiness_snapshot.status,
                    "completion_state": completion_state,
                    "projection_changed": projection_changed,
                    "completion_unknown_elapsed_seconds": completion_unknown_elapsed_seconds,
                    "completion_candidate_elapsed_seconds": completion_candidate_elapsed_seconds,
                    "saw_working": completion_snapshot.saw_working,
                    "saw_projection_change": completion_snapshot.saw_projection_change,
                },
            )
            return SurfaceReduction(
                readiness_state=readiness_snapshot.status,
                completion_state=completion_state,
                projection_changed=projection_changed,
                readiness_unknown_elapsed_seconds=readiness_snapshot.unknown_elapsed_seconds,
                completion_unknown_elapsed_seconds=completion_unknown_elapsed_seconds,
                completion_candidate_elapsed_seconds=completion_candidate_elapsed_seconds,
            )

        background_completion_state = _background_completion_state(
            parsed_surface=parsed_surface,
            readiness_state=readiness_snapshot.status,
        )
        completion_unknown_elapsed_seconds = (
            readiness_snapshot.unknown_elapsed_seconds
            if background_completion_state in {"unknown", "stalled"}
            else None
        )
        self._emit_debug(
            stream="tracker-reduction",
            event_type="reduction_background_snapshot",
            monotonic_ts=readiness_snapshot.observation.monotonic_ts,
            cycle_seq=cycle_seq,
            data={
                "readiness_state": readiness_snapshot.status,
                "completion_state": background_completion_state,
                "projection_changed": False,
                "completion_unknown_elapsed_seconds": completion_unknown_elapsed_seconds,
                "submit_ready": _is_submit_ready(parsed_surface),
                "business_state": parsed_surface.business_state,
                "input_mode": parsed_surface.input_mode,
                "ui_context": parsed_surface.ui_context,
                "baseline_invalidated": parsed_surface.baseline_invalidated,
            },
        )
        return SurfaceReduction(
            readiness_state=readiness_snapshot.status,
            completion_state=background_completion_state,
            projection_changed=False,
            readiness_unknown_elapsed_seconds=readiness_snapshot.unknown_elapsed_seconds,
            completion_unknown_elapsed_seconds=completion_unknown_elapsed_seconds,
            completion_candidate_elapsed_seconds=None,
        )

    def _current_lifecycle_authority(self) -> HoumaoLifecycleAuthorityMetadata:
        """Return the current lifecycle-authority metadata for the tracker."""

        if self.m_active_turn_anchor is not None:
            return HoumaoLifecycleAuthorityMetadata(
                completion_authority="turn_anchored",
                turn_anchor_state="active",
                completion_monitoring_armed=True,
                detail="Server-owned turn anchor is active for completion monitoring.",
                anchor_armed_at_utc=self.m_active_turn_anchor.armed_at_utc,
            )
        if self.m_lost_turn_anchor is not None:
            return HoumaoLifecycleAuthorityMetadata(
                completion_authority="unanchored_background",
                turn_anchor_state="lost",
                completion_monitoring_armed=False,
                detail=(
                    "Server-owned turn anchor was lost before completion monitoring reached a "
                    "terminal outcome."
                ),
                anchor_lost_at_utc=self.m_lost_turn_anchor.lost_at_utc,
                anchor_loss_reason=self.m_lost_turn_anchor.reason,
            )
        return HoumaoLifecycleAuthorityMetadata(
            completion_authority="unanchored_background",
            turn_anchor_state="absent",
            completion_monitoring_armed=False,
            detail=(
                "No active server-owned turn anchor is armed; background watch suppresses "
                "authoritative candidate-complete and completed states."
            ),
        )

    def _advance_scheduler(self, *, monotonic_ts: float) -> None:
        """Advance the internal scheduler to the provided monotonic timestamp."""

        previous_monotonic = self.m_last_scheduler_monotonic
        if previous_monotonic is None:
            self.m_last_scheduler_monotonic = monotonic_ts
            return
        elapsed_seconds = max(monotonic_ts - previous_monotonic, 0.0)
        if elapsed_seconds > 0:
            self.m_scheduler.advance_by(timedelta(seconds=elapsed_seconds))
        self.m_last_scheduler_monotonic = monotonic_ts

    def _drain_pipeline_snapshots(self) -> None:
        """Drain queued shared-kernel snapshots into the latest in-memory state."""

        while self.m_readiness_snapshot_queue:
            self.m_last_readiness_snapshot = self.m_readiness_snapshot_queue.popleft()
        while self.m_completion_snapshot_queue:
            self.m_last_completion_snapshot = self.m_completion_snapshot_queue.popleft()

    def _drain_hook_channel_locked(
        self,
        *,
        monotonic_ts: float,
        observed_at_utc: str,
        output_text: str | None,
    ) -> None:
        """Read and fold new hook observations at one poll-cycle boundary."""

        channel = self.m_hook_channel
        if channel is None or self.m_hook_subject is None:
            return
        signature = _rendered_surface_signature(output_text)
        tui_changed = signature is not None and signature != self.m_hook_last_tui_signature
        if signature is not None:
            self.m_hook_last_tui_signature = signature
        previous_health_state = self.m_hook_health.state if self.m_hook_health is not None else None
        cycle = channel.read_cycle(
            now_monotonic=monotonic_ts,
            now_utc=observed_at_utc,
            tui_changed=tui_changed,
        )
        self.m_hook_last_cycle = cycle
        self.m_hook_health = cycle.health
        for observation in cycle.observations:
            self.m_hook_subject.on_next(observation)
            while self.m_hook_posture_queue:
                self.m_hook_posture = self.m_hook_posture_queue.popleft()
            if self.m_hook_posture is not None:
                self._note_hook_fold_locked(
                    posture=self.m_hook_posture,
                    monotonic_ts=monotonic_ts,
                    observed_at_utc=observed_at_utc,
                )
        if self.m_hook_posture is None:
            self.m_hook_posture = channel.reducer.posture
        self.m_hook_reader_orphan_generations += cycle.dropped_old_generation_lines
        self.m_hook_cycle_reasons = self._hook_cycle_reasons_locked(
            posture=self.m_hook_posture,
            cycle=cycle,
        )
        self.m_hook_previous_counters = self.m_hook_posture.counters
        self.m_hook_recovered_this_cycle = (
            previous_health_state in {"stale", "error"} and cycle.health.state == "active"
        )
        self.m_hook_previous_health_state = previous_health_state
        self._emit_debug(
            stream="tracker-hook",
            event_type="hook_channel_cycle",
            monotonic_ts=monotonic_ts,
            cycle_seq=self.m_cycle_seq,
            data={
                "health_state": cycle.health.state,
                "observation_count": len(cycle.observations),
                "current_generation": cycle.current_generation,
                "skipped_garbage_lines": cycle.skipped_garbage_lines,
                "skipped_invalid_lines": cycle.skipped_invalid_lines,
                "skipped_oversized_lines": cycle.skipped_oversized_lines,
                "dropped_old_generation_lines": cycle.dropped_old_generation_lines,
                "retried_partial_line": cycle.retried_partial_line,
                "read_error": cycle.read_error,
            },
        )

    def _hook_cycle_reasons_locked(
        self,
        *,
        posture: HookPosture,
        cycle: HookChannelCycle,
    ) -> tuple[str, ...]:
        """Return §9 diagnostics caused by this cycle's newly folded events."""

        reasons: list[str] = []
        previous = self.m_hook_previous_counters
        counters = posture.counters
        if previous is not None:
            if counters.unknown_events > previous.unknown_events:
                reasons.append("hook_unknown_event")
            if counters.malformed_events > previous.malformed_events:
                reasons.append("hook_malformed_event")
            if counters.orphan_terminals > previous.orphan_terminals:
                reasons.append("hook_orphan_terminal")
            if counters.duplicate_events > previous.duplicate_events:
                reasons.append("hook_duplicate_event")
            if counters.orphan_generations > previous.orphan_generations:
                reasons.append("hook_orphan_generation")
        if cycle.dropped_old_generation_lines > 0:
            reasons.append("hook_orphan_generation")
        return _bounded_hook_reasons(reasons)

    def _note_hook_fold_locked(
        self,
        *,
        posture: HookPosture,
        monotonic_ts: float,
        observed_at_utc: str,
    ) -> None:
        """Track per-observation hook turn arming and terminal latching."""

        previous = self.m_hook_previous_posture
        same_generation = previous is not None and previous.generation == posture.generation
        if previous is None or not same_generation:
            self._reset_hook_turn_tracking_locked()
            previous_armed_count = 0
        else:
            previous_armed_count = len(previous.armed_prompts)
        consumed_explicit: list[bool] = []
        consumed_armed_at: list[float] = []
        consumed_epochs: list[int] = []
        if len(posture.armed_prompts) > previous_armed_count:
            for _ in range(len(posture.armed_prompts) - previous_armed_count):
                self.m_hook_armed_explicit.append(
                    self._consume_explicit_submission_locked(monotonic_ts)
                )
                self.m_hook_armed_at_monotonic.append(monotonic_ts)
                self.m_hook_next_turn_epoch += 1
                self.m_hook_armed_epochs.append(self.m_hook_next_turn_epoch)
        elif len(posture.armed_prompts) < previous_armed_count:
            for _ in range(previous_armed_count - len(posture.armed_prompts)):
                consumed_explicit.append(
                    self.m_hook_armed_explicit.popleft() if self.m_hook_armed_explicit else False
                )
                if self.m_hook_armed_at_monotonic:
                    consumed_armed_at.append(self.m_hook_armed_at_monotonic.popleft())
                if self.m_hook_armed_epochs:
                    consumed_epochs.append(self.m_hook_armed_epochs.popleft())
        new_terminal = posture.terminal_result != "none" and (
            previous is None
            or not same_generation
            or previous.terminal_result == "none"
            or bool(consumed_explicit)
        )
        if new_terminal:
            self.m_hook_latch = _HookTurnLatch(
                result=posture.terminal_result,
                error_class=posture.terminal_error_class,
                explicit_input=consumed_explicit[0] if consumed_explicit else False,
                consumed_prompt_id=posture.terminal_consumed_prompt_id,
                generation=posture.generation,
                sequence=posture.last_sequence,
                armed_at_monotonic=consumed_armed_at[0] if consumed_armed_at else None,
                at_utc=observed_at_utc,
                epoch=(
                    consumed_epochs[0]
                    if consumed_epochs
                    else (self.m_hook_latch.epoch if self.m_hook_latch else 0)
                ),
                created_cycle=self.m_cycle_seq,
            )
            self.m_hook_suppressed_latch_identity = None
        elif (
            previous is not None
            and same_generation
            and previous.terminal_result != "none"
            and posture.terminal_result == "none"
        ):
            self.m_hook_latch = None
            self.m_hook_suppressed_latch_identity = None
        if posture.blocked:
            if previous is None or not previous.blocked or not same_generation:
                self.m_hook_blocked_key = (posture.generation, posture.last_sequence)
                self.m_hook_blocked_cleared_key = None
        else:
            self.m_hook_blocked_key = None
            self.m_hook_blocked_cleared_key = None
        previous_maintenance = (
            previous.maintenance_active if previous is not None and same_generation else False
        )
        if posture.maintenance_active and not previous_maintenance:
            self.m_hook_maintenance_epoch = self._current_hook_turn_epoch_locked()
            if (
                self.m_hook_maintenance_epoch is not None
                and self.m_hook_tui_interrupt_epoch == self.m_hook_maintenance_epoch
            ):
                self.m_hook_tui_interrupt_epoch = None
        self.m_hook_previous_posture = posture

    def _current_hook_turn_epoch_locked(self) -> int | None:
        """Return the turn epoch that currently owns hook lifecycle authority."""

        if self.m_hook_armed_epochs:
            return self.m_hook_armed_epochs[0]
        if self.m_hook_latch is not None:
            return self.m_hook_latch.epoch
        return None

    def _note_tui_evidence_locked(
        self,
        *,
        parsed_surface: HoumaoParsedSurface | None,
        monotonic_ts: float,
        observed_at_utc: str,
    ) -> None:
        """Record TUI modal-dismissal evidence for the hook blocked exit."""

        del observed_at_utc
        modal_dismissed = False
        if parsed_surface is not None:
            if (
                self.m_previous_parsed_ui_context == "modal"
                and parsed_surface.ui_context != "modal"
            ):
                modal_dismissed = True
            self.m_previous_parsed_ui_context = parsed_surface.ui_context
        posture = self.m_hook_posture
        if posture is None or not posture.blocked:
            return
        current_epoch = self._current_hook_turn_epoch_locked()
        maintenance_contaminated = (
            current_epoch is not None and self.m_hook_maintenance_epoch == current_epoch
        )
        interrupt_evidence = (
            current_epoch is not None
            and self.m_hook_tui_interrupt_epoch == current_epoch
            and not posture.maintenance_active
            and not maintenance_contaminated
        )
        if (modal_dismissed and not posture.maintenance_active) or interrupt_evidence:
            if self.m_hook_blocked_key is not None:
                self.m_hook_blocked_cleared_key = self.m_hook_blocked_key
            self._emit_debug(
                stream="tracker-hook",
                event_type="hook_blocked_cleared_by_tui_evidence",
                monotonic_ts=monotonic_ts,
                cycle_seq=self.m_cycle_seq,
                data={
                    "modal_dismissed": modal_dismissed,
                    "tui_interrupt_evidence": interrupt_evidence,
                },
            )

    def _consume_explicit_submission_locked(self, monotonic_ts: float) -> bool:
        """Consume one unconsumed gateway submission within the correlation window."""

        while self.m_hook_pending_explicit:
            submitted_at = self.m_hook_pending_explicit[0]
            if monotonic_ts - submitted_at > EXPLICIT_INPUT_CORRELATION_SECONDS:
                self.m_hook_pending_explicit.popleft()
                continue
            self.m_hook_pending_explicit.popleft()
            return True
        return False

    def _reset_hook_turn_tracking_locked(self) -> None:
        """Clear turn-scoped hook correlation after a generation change."""

        self.m_hook_latch = None
        self.m_hook_suppressed_latch_identity = None
        self.m_hook_armed_explicit.clear()
        self.m_hook_armed_at_monotonic.clear()
        self.m_hook_armed_epochs.clear()
        self.m_hook_blocked_cleared_key = None
        self.m_hook_blocked_key = None
        self.m_hook_tui_interrupt_epoch = None
        self.m_hook_tui_interrupt_applied_epoch = None
        self.m_hook_maintenance_epoch = None

    def _note_tui_last_turn_transition_locked(
        self,
        *,
        tracker_state: TrackedStateSnapshot,
        monotonic_ts: float,
        observed_at_utc: str,
    ) -> None:
        """Track TUI settlement and interrupt transitions for hook resolution."""

        result = tracker_state.last_turn_result
        if result == self.m_hook_previous_tui_last_turn_result:
            return
        self.m_hook_previous_tui_last_turn_result = result
        if result == "interrupted":
            epoch = self._current_hook_turn_epoch_locked()
            armed_epoch = self.m_hook_armed_epochs[0] if self.m_hook_armed_epochs else None
            latch_epoch = self.m_hook_latch.epoch if self.m_hook_latch is not None else None
            same_cycle_latch_epoch = (
                latch_epoch
                if self.m_hook_latch is not None
                and self.m_hook_latch.created_cycle == self.m_cycle_seq
                else None
            )
            armed_at = self.m_hook_armed_at_monotonic[0] if self.m_hook_armed_at_monotonic else None
            if (
                epoch is not None
                and epoch != self.m_hook_maintenance_epoch
                and epoch in {armed_epoch, same_cycle_latch_epoch}
                and (armed_at is None or monotonic_ts >= armed_at)
            ):
                self.m_hook_tui_interrupt_epoch = epoch
            else:
                self.m_hook_tui_interrupt_epoch = None
        elif result == "none":
            self.m_hook_degraded_tui_settlement = None
        health_state = self.m_hook_health.state if self.m_hook_health is not None else None
        degraded_window = "stale" in {health_state, self.m_hook_previous_health_state}
        if degraded_window and result in {"success", "known_failure", "interrupted"}:
            self.m_hook_degraded_tui_settlement = _DegradedTuiSettlement(
                result=result,
                source=tracker_state.last_turn_source,
                at_utc=observed_at_utc,
            )

    def _project_hook_state_locked(
        self,
        *,
        tracker_state: TrackedStateSnapshot,
        previous_last_turn: HoumaoTrackedLastTurn,
        observed_at_utc: str,
    ) -> _HookProjection | None:
        """Merge the current hook posture and health into projection facts.

        A maintenance window holds an armed turn active but makes no lifecycle
        claim when no prompt is armed; TUI surface facts govern admission during
        operator-invoked compaction (state-transitions section 3, rules 7-8).
        """

        channel = self.m_hook_channel
        if channel is None:
            return None
        posture = self.m_hook_posture or channel.reducer.posture
        health = self.m_hook_health if self.m_hook_health is not None else channel.health.snapshot()
        reasons: list[str] = list(self.m_hook_cycle_reasons)
        if health.state != "active":
            if health.state == "stale":
                reasons.append("hook_stale_tui_authoritative")
            latched_last_turn = self._latched_last_turn_locked()
            return _HookProjection(
                health=health,
                posture=posture,
                turn_phase=tracker_state.turn_phase,
                last_turn=(
                    latched_last_turn
                    if latched_last_turn is not None
                    else _build_tracker_last_turn(
                        previous=previous_last_turn,
                        tracker_state=tracker_state,
                        observed_at_utc=observed_at_utc,
                    )
                ),
                work="unknown",
                settled=False,
                blocked=False,
                holds_lifecycle=False,
                conflict_reasons=_bounded_hook_reasons(reasons),
                latch=None,
                reader_orphan_generations=self.m_hook_reader_orphan_generations,
            )

        blocked = posture.blocked and not self._hook_blocked_cleared(posture)
        armed_turn = posture.armed_prompt_count > 0
        holds_lifecycle = armed_turn
        if blocked:
            turn_phase: TurnPhase = "blocked"
        elif armed_turn:
            turn_phase = "active"
        elif self.m_hook_latch is not None:
            turn_phase = "ready"
        else:
            turn_phase = tracker_state.turn_phase

        if armed_turn and not blocked and tracker_state.turn_phase == "ready":
            reasons.append("hook_active_tui_ready")
        if blocked and tracker_state.turn_phase == "ready":
            reasons.append("hook_blocked_tui_ready")
        if self.m_hook_latch is not None and tracker_state.turn_phase == "active":
            reasons.append("hook_terminal_tui_active")

        last_turn, last_turn_reasons = self._merge_hook_last_turn_locked(
            tracker_state=tracker_state,
            previous=previous_last_turn,
            observed_at_utc=observed_at_utc,
        )
        reasons.extend(last_turn_reasons)
        work: HookWorkState = posture.work
        return _HookProjection(
            health=health,
            posture=posture,
            turn_phase=turn_phase,
            last_turn=last_turn,
            work=work,
            settled=(turn_phase == "ready" and work == "clear"),
            blocked=blocked,
            holds_lifecycle=holds_lifecycle,
            conflict_reasons=_bounded_hook_reasons(reasons),
            latch=self.m_hook_latch,
            reader_orphan_generations=self.m_hook_reader_orphan_generations,
        )

    def _merge_hook_last_turn_locked(
        self,
        *,
        tracker_state: TrackedStateSnapshot,
        previous: HoumaoTrackedLastTurn,
        observed_at_utc: str,
    ) -> tuple[HoumaoTrackedLastTurn, list[str]]:
        """Apply hook terminal authority to the tracked last-turn record."""

        reasons: list[str] = []
        tui_last_turn = _build_tracker_last_turn(
            previous=previous,
            tracker_state=tracker_state,
            observed_at_utc=observed_at_utc,
        )
        latch = self.m_hook_latch
        if latch is None:
            return tui_last_turn, reasons
        latch_identity = latch.identity()
        if self.m_hook_recovered_this_cycle and self.m_hook_degraded_tui_settlement is not None:
            settlement = self.m_hook_degraded_tui_settlement
            self.m_hook_degraded_tui_settlement = None
            if settlement.result == latch.result:
                self.m_hook_suppressed_latch_identity = latch_identity
                return (
                    HoumaoTrackedLastTurn(
                        result=settlement.result,
                        source=settlement.source,
                        updated_at_utc=settlement.at_utc,
                    ),
                    reasons,
                )
            if settlement.result == "interrupted":
                self.m_hook_suppressed_latch_identity = latch_identity
                self.m_hook_tui_interrupt_applied_epoch = latch.epoch
                if latch.result == "success":
                    reasons.append("hook_success_tui_interrupted")
                return tui_last_turn, reasons
            reasons.append("hook_correction_after_staleness")
            if latch.result == "known_failure" and settlement.result == "success":
                reasons.append("hook_failure_tui_success")
            self._emit_debug(
                stream="tracker-hook",
                event_type="hook_correction_after_staleness",
                monotonic_ts=None,
                cycle_seq=self.m_cycle_seq,
                data={
                    "tui_result": settlement.result,
                    "tui_source": settlement.source,
                    "hook_result": latch.result,
                    "hook_source": (
                        "explicit_input" if latch.explicit_input else "hook_observation"
                    ),
                },
            )
        if self.m_hook_suppressed_latch_identity == latch_identity:
            if self._tui_interrupt_for_latch(tracker_state, latch):
                reasons.append("hook_success_tui_interrupted")
            return tui_last_turn, reasons
        result: TrackedLastTurnResult = latch.result
        source: TrackedLastTurnSource = (
            "explicit_input" if latch.explicit_input else "hook_observation"
        )
        if result == "success" and self._tui_interrupt_for_latch(tracker_state, latch):
            result = "interrupted"
            reasons.append("hook_success_tui_interrupted")
        if result == "known_failure" and tracker_state.last_turn_result == "success":
            reasons.append("hook_failure_tui_success")
        return (
            HoumaoTrackedLastTurn(
                result=result,
                source=source,
                updated_at_utc=latch.at_utc,
                error_class=latch.error_class if result == "known_failure" else None,
            ),
            reasons,
        )

    def _tui_interrupt_for_latch(
        self,
        tracker_state: TrackedStateSnapshot,
        latch: _HookTurnLatch,
    ) -> bool:
        """Return whether TUI interrupt evidence belongs to the latched turn.

        Interrupt evidence is keyed to the turn epoch that produced the latch.
        Evidence observed during or after a maintenance window for that epoch is
        not interrupt evidence: compaction repaints can trip the TUI detector's
        silent-abort inference even though the turn already terminated normally.
        Once applied, the interrupt outcome sticks to the latch for its lifetime.
        """

        if tracker_state.last_turn_result != "interrupted":
            return False
        if self.m_hook_tui_interrupt_applied_epoch == latch.epoch:
            return True
        if self.m_hook_tui_interrupt_epoch != latch.epoch:
            return False
        if self.m_hook_maintenance_epoch == latch.epoch:
            return False
        self.m_hook_tui_interrupt_applied_epoch = latch.epoch
        return True

    def _latched_last_turn_locked(self) -> HoumaoTrackedLastTurn | None:
        """Return the hook-latched last turn for degraded-channel publication."""

        latch = self.m_hook_latch
        if latch is None:
            return None
        result: TrackedLastTurnResult = latch.result
        if self.m_hook_tui_interrupt_applied_epoch == latch.epoch:
            result = "interrupted"
        return HoumaoTrackedLastTurn(
            result=result,
            source=("explicit_input" if latch.explicit_input else "hook_observation"),
            updated_at_utc=latch.at_utc,
            error_class=latch.error_class if result == "known_failure" else None,
        )

    def _hook_blocked_cleared(self, posture: HookPosture) -> bool:
        """Return whether TUI evidence already dismissed the hook blocked mark."""

        return (
            posture.blocked
            and self.m_hook_blocked_key is not None
            and self.m_hook_blocked_cleared_key == self.m_hook_blocked_key
        )

    def _update_stale_active_recovery_locked(
        self,
        *,
        candidate: _StaleActiveRecoveryCandidate | None,
        monotonic_ts: float,
        cycle_seq: int,
    ) -> bool:
        """Refresh stale-active recovery timing and return whether recovery applies now."""

        if candidate is None:
            self._cancel_stale_active_recovery_locked(
                reason="candidate_cleared",
                monotonic_ts=monotonic_ts,
                cycle_seq=cycle_seq,
            )
            return False
        if self.m_recovered_stale_active_signature == candidate.signature:
            return True
        if self.m_pending_stale_active_recovery_signature == candidate.signature:
            return False
        self._cancel_stale_active_recovery_locked(
            reason="candidate_replaced",
            monotonic_ts=monotonic_ts,
            cycle_seq=cycle_seq,
        )
        self.m_pending_stale_active_recovery_signature = candidate.signature
        self.m_pending_stale_active_recovery.disposable = reactivex.timer(
            timedelta(seconds=self.m_stale_active_recovery_seconds),
            scheduler=self.m_scheduler,
        ).subscribe(
            lambda _unused: self._handle_stale_active_recovery_timer(
                candidate_signature=candidate.signature
            )
        )
        self._emit_debug(
            stream="tracker-recovery",
            event_type="stale_active_recovery_armed",
            monotonic_ts=monotonic_ts,
            cycle_seq=cycle_seq,
            data={
                "recovery_signature_sha1": _sha1_text(candidate.signature),
                "active_reasons": list(candidate.active_reasons),
                "recovery_seconds": self.m_stale_active_recovery_seconds,
            },
        )
        return False

    def _handle_stale_active_recovery_timer(self, *, candidate_signature: str) -> None:
        """Mark one stale-active candidate signature as recovered."""

        with self.m_lock:
            if self.m_pending_stale_active_recovery_signature != candidate_signature:
                self._emit_debug(
                    stream="tracker-recovery",
                    event_type="stale_active_recovery_timer_skipped",
                    monotonic_ts=self.m_last_scheduler_monotonic,
                    data={
                        "reason": "candidate_signature_mismatch",
                        "pending_signature_sha1": _sha1_text(
                            self.m_pending_stale_active_recovery_signature
                        ),
                        "timer_signature_sha1": _sha1_text(candidate_signature),
                    },
                )
                return
            self.m_pending_stale_active_recovery_signature = None
            self.m_recovered_stale_active_signature = candidate_signature
            self._emit_debug(
                stream="tracker-recovery",
                event_type="stale_active_recovery_timer_fired",
                monotonic_ts=self.m_last_scheduler_monotonic,
                data={"recovery_signature_sha1": _sha1_text(candidate_signature)},
            )

    def _cancel_stale_active_recovery_locked(
        self,
        *,
        reason: str,
        monotonic_ts: float | None = None,
        cycle_seq: int | None = None,
    ) -> None:
        """Cancel or clear stale-active recovery state."""

        had_pending = self.m_pending_stale_active_recovery_signature is not None
        had_recovered = self.m_recovered_stale_active_signature is not None
        self.m_pending_stale_active_recovery.dispose()
        self.m_pending_stale_active_recovery = SerialDisposable()
        self.m_pending_stale_active_recovery_signature = None
        self.m_recovered_stale_active_signature = None
        if not had_pending and not had_recovered:
            return
        self._emit_debug(
            stream="tracker-recovery",
            event_type="stale_active_recovery_cleared",
            monotonic_ts=monotonic_ts,
            cycle_seq=cycle_seq,
            data={
                "reason": reason,
                "had_pending": had_pending,
                "had_recovered": had_recovered,
            },
        )

    def _update_final_stable_active_recovery_locked(
        self,
        *,
        candidate: _FinalStableActiveRecoveryCandidate | None,
        monotonic_ts: float,
        cycle_seq: int,
    ) -> bool:
        """Refresh final stable-active recovery timing and return whether recovery applies."""

        if candidate is None:
            self._cancel_final_stable_active_recovery_locked(
                reason="candidate_cleared",
                monotonic_ts=monotonic_ts,
                cycle_seq=cycle_seq,
            )
            return False
        if self.m_recovered_final_stable_active_signature == candidate.signature:
            return True
        if self.m_pending_final_stable_active_recovery_signature == candidate.signature:
            return False
        self._cancel_final_stable_active_recovery_locked(
            reason="candidate_replaced",
            monotonic_ts=monotonic_ts,
            cycle_seq=cycle_seq,
        )
        self.m_pending_final_stable_active_recovery_signature = candidate.signature
        self.m_pending_final_stable_active_recovery.disposable = reactivex.timer(
            timedelta(seconds=self.m_final_stable_active_recovery_seconds),
            scheduler=self.m_scheduler,
        ).subscribe(
            lambda _unused: self._handle_final_stable_active_recovery_timer(
                candidate_signature=candidate.signature
            )
        )
        self._emit_debug(
            stream="tracker-recovery",
            event_type="final_stable_active_recovery_armed",
            monotonic_ts=monotonic_ts,
            cycle_seq=cycle_seq,
            data={
                "recovery_signature_sha1": _sha1_text(candidate.signature),
                "active_reasons": list(candidate.active_reasons),
                "recovery_seconds": self.m_final_stable_active_recovery_seconds,
            },
        )
        return False

    def _handle_final_stable_active_recovery_timer(self, *, candidate_signature: str) -> None:
        """Mark one final stable-active candidate signature as recovered."""

        with self.m_lock:
            if self.m_pending_final_stable_active_recovery_signature != candidate_signature:
                self._emit_debug(
                    stream="tracker-recovery",
                    event_type="final_stable_active_recovery_timer_skipped",
                    monotonic_ts=self.m_last_scheduler_monotonic,
                    data={
                        "reason": "candidate_signature_mismatch",
                        "pending_signature_sha1": _sha1_text(
                            self.m_pending_final_stable_active_recovery_signature
                        ),
                        "timer_signature_sha1": _sha1_text(candidate_signature),
                    },
                )
                return
            self.m_pending_final_stable_active_recovery_signature = None
            self.m_recovered_final_stable_active_signature = candidate_signature
            self._emit_debug(
                stream="tracker-recovery",
                event_type="final_stable_active_recovery_timer_fired",
                monotonic_ts=self.m_last_scheduler_monotonic,
                data={"recovery_signature_sha1": _sha1_text(candidate_signature)},
            )

    def _cancel_final_stable_active_recovery_locked(
        self,
        *,
        reason: str,
        monotonic_ts: float | None = None,
        cycle_seq: int | None = None,
    ) -> None:
        """Cancel or clear final stable-active recovery state."""

        had_pending = self.m_pending_final_stable_active_recovery_signature is not None
        had_recovered = self.m_recovered_final_stable_active_signature is not None
        self.m_pending_final_stable_active_recovery.dispose()
        self.m_pending_final_stable_active_recovery = SerialDisposable()
        self.m_pending_final_stable_active_recovery_signature = None
        self.m_recovered_final_stable_active_signature = None
        if not had_pending and not had_recovered:
            return
        self._emit_debug(
            stream="tracker-recovery",
            event_type="final_stable_active_recovery_cleared",
            monotonic_ts=monotonic_ts,
            cycle_seq=cycle_seq,
            data={
                "reason": reason,
                "had_pending": had_pending,
                "had_recovered": had_recovered,
            },
        )

    def _build_stability(
        self,
        *,
        diagnostics: HoumaoTrackedDiagnostics,
        parsed_surface: HoumaoParsedSurface | None,
        surface: HoumaoTrackedSurface,
        turn: HoumaoTrackedTurn,
        last_turn: HoumaoTrackedLastTurn,
        chat_context: str,
        chat_context_diagnostic: HoumaoDegradedChatContextDiagnostic | None,
        monotonic_ts: float,
        observed_at_utc: str,
        cycle_seq: int,
    ) -> HoumaoStabilityMetadata:
        """Build stability metadata for the current visible response signature."""

        signature_payload = json.dumps(
            _visible_signature_payload(
                diagnostics=diagnostics,
                parsed_surface=parsed_surface,
                surface=surface,
                turn=turn,
                last_turn=last_turn,
                chat_context=chat_context,
                chat_context_diagnostic=chat_context_diagnostic,
            ),
            sort_keys=True,
            separators=(",", ":"),
        )
        previous_signature = self.m_last_signature_payload
        signature_changed = signature_payload != previous_signature
        if signature_payload != self.m_last_signature_payload:
            self.m_last_signature_payload = signature_payload
            self.m_stable_since_monotonic = monotonic_ts
            self.m_stable_since_utc = observed_at_utc
        assert self.m_stable_since_monotonic is not None
        stable_for_seconds = max(monotonic_ts - self.m_stable_since_monotonic, 0.0)
        stability = HoumaoStabilityMetadata(
            signature=hashlib.sha1(signature_payload.encode("utf-8")).hexdigest(),
            stable=stable_for_seconds >= self.m_stability_threshold_seconds,
            stable_for_seconds=stable_for_seconds,
            stable_since_utc=self.m_stable_since_utc,
        )
        self._emit_debug(
            stream="tracker-stability",
            event_type="stability_updated",
            monotonic_ts=monotonic_ts,
            cycle_seq=cycle_seq,
            anchor_id=(
                self.m_active_turn_anchor.anchor_id
                if self.m_active_turn_anchor is not None
                else None
            ),
            data={
                "signature_changed": signature_changed,
                "previous_signature_sha1": _sha1_text(previous_signature),
                "current_signature_sha1": stability.signature,
                "stable": stability.stable,
                "stable_for_seconds": stability.stable_for_seconds,
                "stable_since_utc": stability.stable_since_utc,
            },
        )
        return stability

    def _publish_state(
        self,
        *,
        response: HoumaoTerminalStateResponse,
        monotonic_ts: float,
        observed_at_utc: str,
    ) -> HoumaoTerminalStateResponse:
        """Store one response as the current state and append recent history."""

        transition = _build_transition(previous=self.m_last_state, current=response)
        response_operator_state = _require_operator_state(response)
        response_lifecycle_authority = _require_lifecycle_authority(response)
        if transition is not None:
            self.m_recent_transitions.append(transition)
            self.m_recent_transitions = self.m_recent_transitions[-self.m_recent_transition_limit :]
            response = response.model_copy(
                update={"recent_transitions": list(self.m_recent_transitions)}
            )
            self._emit_debug(
                stream="tracker-transition",
                event_type="transition_published",
                monotonic_ts=monotonic_ts,
                anchor_id=(
                    self.m_active_turn_anchor.anchor_id
                    if self.m_active_turn_anchor is not None
                    else None
                ),
                data={
                    "summary": transition.summary,
                    "changed_fields": list(transition.changed_fields),
                    "operator_status": response_operator_state.status,
                    "completion_state": response_operator_state.completion_state,
                    "completion_authority": response_lifecycle_authority.completion_authority,
                },
            )
        else:
            self._emit_debug(
                stream="tracker-transition",
                event_type="transition_suppressed",
                monotonic_ts=monotonic_ts,
                anchor_id=(
                    self.m_active_turn_anchor.anchor_id
                    if self.m_active_turn_anchor is not None
                    else None
                ),
                data={
                    "operator_status": response_operator_state.status,
                    "completion_state": response_operator_state.completion_state,
                    "completion_authority": response_lifecycle_authority.completion_authority,
                },
            )
        self.m_recent_snapshots.append(
            HoumaoTerminalSnapshotHistoryEntry(
                recorded_at_utc=observed_at_utc,
                diagnostics=response.diagnostics,
                probe_snapshot=response.probe_snapshot,
                parsed_surface=response.parsed_surface,
                surface=response.surface,
                turn=response.turn,
                last_turn=response.last_turn,
                chat_context=response.chat_context,
                chat_context_diagnostic=response.chat_context_diagnostic,
                stability=response.stability,
            )
        )
        self.m_recent_snapshots = self.m_recent_snapshots[-self.m_snapshot_history_limit :]
        self.m_last_state = response
        return response

    def _lose_turn_anchor(
        self,
        *,
        lost_at_utc: str,
        reason: str,
        monotonic_ts: float,
        cycle_seq: int,
    ) -> None:
        """Invalidate the current turn anchor and return to unanchored semantics."""

        previous_anchor_id = (
            self.m_active_turn_anchor.anchor_id if self.m_active_turn_anchor is not None else None
        )
        self._dispose_completion_subscription()
        self.m_active_turn_anchor = None
        self.m_active_turn_previous_last_turn = self.m_last_state.last_turn
        self.m_last_published_turn_anchor_id = None
        self.m_last_completion_snapshot = None
        self.m_anchor_should_expire_after_publish = False
        self.m_lost_turn_anchor = _LostTurnAnchor(lost_at_utc=lost_at_utc, reason=reason)
        self._emit_debug(
            stream="tracker-anchor",
            event_type="turn_anchor_lost",
            monotonic_ts=monotonic_ts,
            cycle_seq=cycle_seq,
            anchor_id=previous_anchor_id,
            data={"lost_at_utc": lost_at_utc, "reason": reason},
        )

    def _expire_turn_anchor_for_final_recovery_locked(
        self,
        *,
        observed_at_utc: str,
        monotonic_ts: float,
        cycle_seq: int,
    ) -> None:
        """Expire the active turn anchor when final stable-active recovery fires."""

        if self.m_active_turn_anchor is None:
            return
        previous_anchor_id = self.m_active_turn_anchor.anchor_id
        self._dispose_completion_subscription()
        self.m_active_turn_anchor = None
        self.m_active_turn_previous_last_turn = self.m_last_state.last_turn
        self.m_last_published_turn_anchor_id = None
        self.m_last_completion_snapshot = None
        self.m_anchor_should_expire_after_publish = False
        self.m_lost_turn_anchor = _LostTurnAnchor(
            lost_at_utc=observed_at_utc,
            reason="final_stable_active_recovery",
        )
        self._emit_debug(
            stream="tracker-anchor",
            event_type="turn_anchor_expired_by_final_stable_active_recovery",
            monotonic_ts=monotonic_ts,
            cycle_seq=cycle_seq,
            anchor_id=previous_anchor_id,
            data={"lost_at_utc": observed_at_utc},
        )

    def _expire_turn_anchor_after_publish(
        self,
        *,
        monotonic_ts: float,
        cycle_seq: int,
    ) -> None:
        """Expire the current turn anchor after publishing its terminal outcome."""

        previous_anchor_id = (
            self.m_active_turn_anchor.anchor_id if self.m_active_turn_anchor is not None else None
        )
        self._dispose_completion_subscription()
        self.m_active_turn_anchor = None
        self.m_active_turn_previous_last_turn = self.m_last_state.last_turn
        self.m_last_published_turn_anchor_id = None
        self.m_last_completion_snapshot = None
        self.m_anchor_should_expire_after_publish = False
        self._emit_debug(
            stream="tracker-anchor",
            event_type="turn_anchor_expired_after_publish",
            monotonic_ts=monotonic_ts,
            cycle_seq=cycle_seq,
            anchor_id=previous_anchor_id,
            data={},
        )

    def _dispose_completion_subscription(self) -> None:
        """Dispose the active anchored completion subscription if present."""

        if self.m_completion_subscription is not None:
            self.m_completion_subscription.dispose()
            self.m_completion_subscription = None
        self.m_completion_snapshot_queue.clear()


def _build_initial_state(
    *,
    identity: HoumaoTrackedSessionIdentity,
    completion_stability_seconds: float,
    unknown_to_stalled_timeout_seconds: float,
    stale_active_recovery_seconds: float,
    final_stable_active_recovery_seconds: float,
) -> HoumaoTerminalStateResponse:
    """Return the initial unknown state for a newly admitted tracked session."""

    observed_at_utc = utc_now_iso()
    return HoumaoTerminalStateResponse(
        terminal_id=_terminal_alias(identity),
        tracked_session=identity,
        diagnostics=HoumaoTrackedDiagnostics(
            availability="unknown",
            transport_state="tmux_missing",
            process_state="unknown",
            parse_status="transport_unavailable",
            probe_error=None,
            parse_error=None,
        ),
        transport_state="tmux_missing",
        process_state="unknown",
        parse_status="transport_unavailable",
        probe_snapshot=None,
        probe_error=None,
        parse_error=None,
        parsed_surface=None,
        surface=HoumaoTrackedSurface(
            accepting_input="unknown",
            editing_input="unknown",
            ready_posture="unknown",
            pending_input="unknown",
        ),
        turn=HoumaoTrackedTurn(phase="unknown"),
        last_turn=HoumaoTrackedLastTurn(
            result="none",
            source="none",
            updated_at_utc=None,
        ),
        operator_state=HoumaoOperatorState(
            status="unknown",
            readiness_state="unknown",
            completion_state="inactive",
            detail="Live tracking has not recorded an observation yet.",
            projection_changed=False,
            updated_at_utc=observed_at_utc,
        ),
        lifecycle_timing=HoumaoLifecycleTimingMetadata(
            readiness_unknown_elapsed_seconds=None,
            completion_unknown_elapsed_seconds=None,
            completion_candidate_elapsed_seconds=None,
            unknown_to_stalled_timeout_seconds=unknown_to_stalled_timeout_seconds,
            completion_stability_seconds=completion_stability_seconds,
            stale_active_recovery_seconds=stale_active_recovery_seconds,
            final_stable_active_recovery_seconds=final_stable_active_recovery_seconds,
        ),
        lifecycle_authority=HoumaoLifecycleAuthorityMetadata(
            completion_authority="unanchored_background",
            turn_anchor_state="absent",
            completion_monitoring_armed=False,
            detail=(
                "No active server-owned turn anchor is armed; background watch suppresses "
                "authoritative candidate-complete and completed states."
            ),
        ),
        stability=HoumaoStabilityMetadata(
            signature="",
            stable=False,
            stable_for_seconds=0.0,
            stable_since_utc=observed_at_utc,
        ),
        recent_transitions=[],
    )


def _build_operator_state(
    *,
    identity: HoumaoTrackedSessionIdentity,
    observed_at_utc: str,
    transport_state: TransportState,
    process_state: ProcessState,
    parse_status: ParseStatus,
    probe_error: HoumaoErrorDetail | None,
    parse_error: HoumaoErrorDetail | None,
    parsed_surface: HoumaoParsedSurface | None,
    reduction: SurfaceReduction,
) -> HoumaoOperatorState:
    """Build the operator-facing state view for one cycle."""

    status: OperatorStatus
    detail: str
    if (
        probe_error is not None
        or transport_state == "probe_error"
        or process_state == "probe_error"
    ):
        status = "error"
        detail = probe_error.message if probe_error is not None else "Direct probe failed."
    elif transport_state == "tmux_missing":
        status = "unavailable"
        detail = "Tracked tmux session is no longer live."
    elif process_state == "tui_down":
        status = "tui_down"
        detail = "Supported TUI process is not running in the tracked tmux pane."
    elif process_state == "unsupported_tool" or parse_status == "unsupported_tool":
        status = "unknown"
        detail = f"Tool `{identity.tool}` is not supported by the official live parser."
    elif parse_error is not None or parse_status == "parse_error":
        status = "error"
        detail = (
            parse_error.message
            if parse_error is not None
            else "Official parser failed for this cycle."
        )
    elif parsed_surface is None:
        status = "unknown"
        detail = "Live parsed surface is unavailable for this cycle."
    elif reduction.completion_state == "completed":
        status = "completed"
        detail = "Parsed live state has remained stable long enough to be treated as complete."
    elif reduction.readiness_state == "stalled" or reduction.completion_state == "stalled":
        status = "unknown"
        detail = "Parsed live state has remained unknown long enough to be treated as stalled."
    elif reduction.readiness_state == "blocked":
        status = "waiting_user_answer"
        detail = "Parsed live state requires operator interaction."
    elif reduction.completion_state == "candidate_complete":
        status = "ready"
        detail = "Parsed live state looks complete but is still inside the stability window."
    elif reduction.completion_state == "in_progress" or parsed_surface.business_state == "working":
        status = "processing"
        detail = "Supported TUI is actively processing."
    elif reduction.readiness_state == "ready":
        status = "ready"
        detail = "Supported TUI is ready for input."
    else:
        status = "unknown"
        detail = (
            "Parsed live surface is "
            f"{parsed_surface.availability}/{parsed_surface.business_state}/{parsed_surface.input_mode}."
        )

    return HoumaoOperatorState(
        status=status,
        readiness_state=reduction.readiness_state,
        completion_state=reduction.completion_state,
        detail=detail,
        projection_changed=reduction.projection_changed,
        updated_at_utc=observed_at_utc,
    )


def _require_operator_state(response: HoumaoTerminalStateResponse) -> HoumaoOperatorState:
    """Return the required operator state for one published response."""

    if response.operator_state is None:
        raise RuntimeError("Live session tracker invariant violated: operator_state is missing.")
    return response.operator_state


def _require_lifecycle_timing(
    response: HoumaoTerminalStateResponse,
) -> HoumaoLifecycleTimingMetadata:
    """Return the required lifecycle timing metadata for one published response."""

    if response.lifecycle_timing is None:
        raise RuntimeError("Live session tracker invariant violated: lifecycle_timing is missing.")
    return response.lifecycle_timing


def _require_lifecycle_authority(
    response: HoumaoTerminalStateResponse,
) -> HoumaoLifecycleAuthorityMetadata:
    """Return the required lifecycle authority metadata for one published response."""

    if response.lifecycle_authority is None:
        raise RuntimeError(
            "Live session tracker invariant violated: lifecycle_authority is missing."
        )
    return response.lifecycle_authority


def _visible_signature_payload(
    *,
    diagnostics: HoumaoTrackedDiagnostics,
    parsed_surface: HoumaoParsedSurface | None,
    surface: HoumaoTrackedSurface,
    turn: HoumaoTrackedTurn,
    last_turn: HoumaoTrackedLastTurn,
    chat_context: str,
    chat_context_diagnostic: HoumaoDegradedChatContextDiagnostic | None,
) -> dict[str, object]:
    """Return the operator-visible signature payload used for stability timing."""

    return {
        "diagnostics": diagnostics.model_dump(
            mode="json",
            exclude={"hook_channel_state", "hook_counters", "hook_conflict_reasons"},
        ),
        "parsed_surface": parsed_surface.model_dump(mode="json")
        if parsed_surface is not None
        else None,
        "surface": surface.model_dump(mode="json"),
        "turn": turn.model_dump(mode="json"),
        "last_turn": last_turn.model_dump(mode="json"),
        "chat_context": chat_context,
        "chat_context_diagnostic": chat_context_diagnostic.model_dump(mode="json")
        if chat_context_diagnostic is not None
        else None,
    }


def _build_transition(
    *,
    previous: HoumaoTerminalStateResponse,
    current: HoumaoTerminalStateResponse,
) -> HoumaoRecentTransition | None:
    """Return one recent transition when the visible state changed."""

    field_pairs: list[tuple[str, object, object]] = [
        (
            "diagnostics_availability",
            previous.diagnostics.availability,
            current.diagnostics.availability,
        ),
        ("transport_state", previous.transport_state, current.transport_state),
        ("process_state", previous.process_state, current.process_state),
        ("parse_status", previous.parse_status, current.parse_status),
        (
            "surface_accepting_input",
            previous.surface.accepting_input,
            current.surface.accepting_input,
        ),
        (
            "surface_editing_input",
            previous.surface.editing_input,
            current.surface.editing_input,
        ),
        (
            "surface_ready_posture",
            previous.surface.ready_posture,
            current.surface.ready_posture,
        ),
        (
            "surface_pending_input",
            previous.surface.pending_input,
            current.surface.pending_input,
        ),
        ("turn_phase", previous.turn.phase, current.turn.phase),
        ("last_turn_result", previous.last_turn.result, current.last_turn.result),
        ("last_turn_source", previous.last_turn.source, current.last_turn.source),
        ("chat_context", previous.chat_context, current.chat_context),
        (
            "chat_context_diagnostic",
            _chat_context_diagnostic_signature(previous.chat_context_diagnostic),
            _chat_context_diagnostic_signature(current.chat_context_diagnostic),
        ),
        ("probe_error", _error_message(previous.probe_error), _error_message(current.probe_error)),
        ("parse_error", _error_message(previous.parse_error), _error_message(current.parse_error)),
        (
            "surface_business_state",
            _surface_field(previous.parsed_surface, "business_state"),
            _surface_field(current.parsed_surface, "business_state"),
        ),
        (
            "surface_input_mode",
            _surface_field(previous.parsed_surface, "input_mode"),
            _surface_field(current.parsed_surface, "input_mode"),
        ),
        (
            "surface_ui_context",
            _surface_field(previous.parsed_surface, "ui_context"),
            _surface_field(current.parsed_surface, "ui_context"),
        ),
    ]
    changed_fields = [field_name for field_name, before, after in field_pairs if before != after]
    if not changed_fields:
        return None

    summary = "; ".join(
        f"{field_name}: {before!r} -> {after!r}"
        for field_name, before, after in field_pairs
        if before != after
    )
    current_operator_state = _require_operator_state(current)
    return HoumaoRecentTransition(
        recorded_at_utc=current.last_turn.updated_at_utc or current_operator_state.updated_at_utc,
        summary=summary,
        changed_fields=list(changed_fields),
        diagnostics_availability=current.diagnostics.availability,
        surface_pending_input=current.surface.pending_input,
        turn_phase=current.turn.phase,
        last_turn_result=current.last_turn.result,
        last_turn_source=current.last_turn.source,
        transport_state=current.transport_state,
        process_state=current.process_state,
        parse_status=current.parse_status,
        operator_status=current_operator_state.status,
    )


def _build_tracked_diagnostics(
    *,
    transport_state: TransportState,
    process_state: ProcessState,
    parse_status: ParseStatus,
    probe_error: HoumaoErrorDetail | None,
    parse_error: HoumaoErrorDetail | None,
    parsed_surface: HoumaoParsedSurface | None,
) -> HoumaoTrackedDiagnostics:
    """Build the low-level diagnostics view for one tracked sample."""

    return HoumaoTrackedDiagnostics(
        availability=shared_diagnostics_availability(
            transport_state=transport_state,
            process_state=process_state,
            parse_status=parse_status,
            probe_error_present=probe_error is not None,
            parse_error_present=parse_error is not None,
            parsed_surface_available=(
                parsed_surface is not None and parsed_surface.availability == "supported"
            ),
        ),
        transport_state=transport_state,
        process_state=process_state,
        parse_status=parse_status,
        probe_error=probe_error,
        parse_error=parse_error,
    )


def _build_tracker_last_turn(
    *,
    previous: HoumaoTrackedLastTurn,
    tracker_state: TrackedStateSnapshot,
    observed_at_utc: str,
) -> HoumaoTrackedLastTurn:
    """Merge standalone tracker last-turn state into the live server contract."""

    if (
        tracker_state.last_turn_result == previous.result
        and tracker_state.last_turn_source == previous.source
    ):
        return previous
    updated_at_utc = observed_at_utc if tracker_state.last_turn_result != "none" else None
    return HoumaoTrackedLastTurn(
        result=tracker_state.last_turn_result,
        source=tracker_state.last_turn_source,
        updated_at_utc=updated_at_utc,
    )


def _bounded_hook_reasons(reasons: Iterable[str]) -> tuple[str, ...]:
    """Return deduplicated conflict reasons bounded for public diagnostics."""

    return tuple(dict.fromkeys(reasons))[:HOOK_CONFLICT_REASON_LIMIT]


def _hook_counters_payload(
    posture: HookPosture,
    *,
    reader_orphan_generations: int = 0,
) -> HoumaoHookObservationCounters:
    """Return the public counter payload for one posture."""

    counters = posture.counters
    return HoumaoHookObservationCounters(
        events_seen=counters.events_seen,
        normalized_events=counters.normalized_events,
        unknown_events=counters.unknown_events,
        malformed_events=counters.malformed_events,
        orphan_terminals=counters.orphan_terminals,
        orphan_generations=counters.orphan_generations + reader_orphan_generations,
        duplicate_events=counters.duplicate_events,
    )


def _build_observation_channels(
    projection: _HookProjection | None,
) -> list[HoumaoObservationChannel] | None:
    """Build the additive observation-channel payload when configured."""

    if projection is None:
        return None
    posture = projection.posture
    return [
        HoumaoObservationChannel(
            channel="hook",
            provider="claude",
            state=projection.health.state,
            detail=projection.health.detail,
            generation=posture.generation,
            last_event_name=posture.last_event_name,
            last_event_at_utc=posture.last_event_at_utc,
            last_sequence=posture.last_sequence,
            counters=_hook_counters_payload(
                posture,
                reader_orphan_generations=projection.reader_orphan_generations,
            ),
            conflict_reasons=list(projection.conflict_reasons),
        )
    ]


def _update_diagnostics_with_hook(
    diagnostics: HoumaoTrackedDiagnostics,
    projection: _HookProjection | None,
) -> HoumaoTrackedDiagnostics:
    """Return diagnostics updated with additive hook channel facts."""

    if projection is None:
        return diagnostics
    return diagnostics.model_copy(
        update={
            "hook_channel_state": projection.health.state,
            "hook_counters": _hook_counters_payload(
                projection.posture,
                reader_orphan_generations=projection.reader_orphan_generations,
            ),
            "hook_conflict_reasons": list(projection.conflict_reasons),
        }
    )


def _build_chat_context_diagnostic(
    tracker_state: TrackedStateSnapshot,
) -> HoumaoDegradedChatContextDiagnostic | None:
    """Return the public degraded context diagnostic for one tracker state."""

    diagnostic = tracker_state.chat_context_diagnostic
    if diagnostic is None:
        return None
    return HoumaoDegradedChatContextDiagnostic(
        tool_name=diagnostic.tool_name,
        detector_name=diagnostic.detector_name,
        detector_version=diagnostic.detector_version,
        degraded_error_type=diagnostic.degraded_error_type,
        message_preview=diagnostic.message_preview,
    )


def _chat_context_diagnostic_signature(
    diagnostic: HoumaoDegradedChatContextDiagnostic | None,
) -> dict[str, object] | None:
    """Return a stable transition-comparison payload for one diagnostic."""

    if diagnostic is None:
        return None
    return diagnostic.model_dump(mode="json")


def _align_operator_state_with_tracker_state(
    *,
    operator_state: HoumaoOperatorState,
    tracker_state: TrackedStateSnapshot,
    diagnostics: HoumaoTrackedDiagnostics,
    observed_at_utc: str,
    merged_turn_phase: TurnPhase | None = None,
    hook_failure: bool = False,
) -> HoumaoOperatorState:
    """Return operator state corrected by authoritative tracker terminal facts."""

    turn_phase = merged_turn_phase if merged_turn_phase is not None else tracker_state.turn_phase
    if turn_phase == "blocked":
        return operator_state.model_copy(
            update={
                "status": "waiting_user_answer",
                "readiness_state": "blocked",
                "completion_state": "blocked",
                "detail": "Provider hook reports the turn is blocked on operator action.",
                "projection_changed": False,
                "updated_at_utc": observed_at_utc,
            }
        )
    if diagnostics.availability != "available":
        return operator_state
    if turn_phase == "active":
        return operator_state.model_copy(
            update={
                "status": "processing",
                "readiness_state": "waiting",
                "completion_state": "in_progress",
                "detail": "Tracker-owned TUI signals indicate the current turn is still active.",
                "projection_changed": False,
                "updated_at_utc": observed_at_utc,
            }
        )
    if hook_failure:
        readiness_state: ReadinessState = (
            "ready" if tracker_state.surface_ready_posture == "yes" else "failed"
        )
        status: OperatorStatus = (
            "ready" if tracker_state.surface_ready_posture == "yes" else "error"
        )
        return operator_state.model_copy(
            update={
                "status": status,
                "readiness_state": readiness_state,
                "completion_state": "failed",
                "detail": "Provider hook reported a terminal failure for the current turn.",
                "projection_changed": False,
                "updated_at_utc": observed_at_utc,
            }
        )
    if tracker_state.last_turn_result == "known_failure":
        readiness_state = "ready" if tracker_state.surface_ready_posture == "yes" else "failed"
        status = "ready" if tracker_state.surface_ready_posture == "yes" else "error"
        return operator_state.model_copy(
            update={
                "status": status,
                "readiness_state": readiness_state,
                "completion_state": "failed",
                "detail": "Tracker recognized a terminal failure surface for the current turn.",
                "projection_changed": False,
                "updated_at_utc": observed_at_utc,
            }
        )
    if "current_error_present" in tracker_state.notes:
        readiness_state = "ready" if tracker_state.surface_ready_posture == "yes" else "unknown"
        status = "ready" if tracker_state.surface_ready_posture == "yes" else "unknown"
        return operator_state.model_copy(
            update={
                "status": status,
                "readiness_state": readiness_state,
                "completion_state": "inactive",
                "detail": (
                    "Tracker recognized a current terminal error surface and blocked "
                    "success settlement."
                ),
                "projection_changed": False,
                "updated_at_utc": observed_at_utc,
            }
        )
    return operator_state


def _terminal_alias(identity: HoumaoTrackedSessionIdentity) -> str:
    """Return the primary terminal compatibility alias for one identity."""

    if identity.terminal_aliases:
        return identity.terminal_aliases[0]
    return identity.tracked_session_id


def _default_surface_reduction() -> SurfaceReduction:
    """Return the default reduction used when no parsed surface exists."""

    return SurfaceReduction(
        readiness_state="unknown",
        completion_state="inactive",
        projection_changed=False,
        readiness_unknown_elapsed_seconds=None,
        completion_unknown_elapsed_seconds=None,
        completion_candidate_elapsed_seconds=None,
    )


def _lifecycle_observation_from_parsed_surface(
    *,
    parsed_surface: HoumaoParsedSurface,
    monotonic_ts: float,
) -> LifecycleObservation:
    """Convert one parsed surface into the shared lifecycle observation shape."""

    return LifecycleObservation(
        availability=parsed_surface.availability,
        business_state=parsed_surface.business_state,
        input_mode=parsed_surface.input_mode,
        ui_context=parsed_surface.ui_context,
        normalized_projection_text=normalize_projection_text(
            parsed_surface.normalized_projection_text
        ),
        baseline_invalidated=parsed_surface.baseline_invalidated,
        operator_blocked_excerpt=parsed_surface.operator_blocked_excerpt,
        monotonic_ts=monotonic_ts,
        parser_family=parsed_surface.parser_family,
    )


def _background_completion_state(
    *,
    parsed_surface: HoumaoParsedSurface,
    readiness_state: ReadinessState,
) -> CompletionState:
    """Return the conservative unanchored completion state for one parsed surface."""

    if readiness_state == "failed":
        return "failed"
    if readiness_state == "blocked":
        return "blocked"
    if readiness_state == "unknown":
        return "unknown"
    if readiness_state == "stalled":
        return "stalled"
    if parsed_surface.business_state == "working":
        return "in_progress"
    if _is_submit_ready(parsed_surface):
        return "inactive"
    return "waiting"


def _is_submit_ready(parsed_surface: HoumaoParsedSurface) -> bool:
    """Return whether one parsed surface is submit-ready."""

    return (
        parsed_surface.availability == "supported"
        and parsed_surface.business_state == "idle"
        and parsed_surface.input_mode == "freeform"
    )


def _anchor_loss_reason(
    *,
    transport_state: TransportState,
    process_state: ProcessState,
    parse_status: ParseStatus,
    probe_error: HoumaoErrorDetail | None,
    parse_error: HoumaoErrorDetail | None,
) -> str:
    """Return a human-readable turn-anchor loss reason for the current cycle."""

    if probe_error is not None:
        return probe_error.message
    if parse_error is not None:
        return parse_error.message
    if transport_state == "tmux_missing":
        return (
            "Tracked tmux session disappeared before the anchored cycle reached a terminal outcome."
        )
    if transport_state == "probe_error":
        return "A tmux probe error invalidated the anchored cycle before terminal outcome."
    if process_state == "tui_down":
        return "Supported TUI process exited before the anchored cycle reached a terminal outcome."
    if process_state == "probe_error":
        return "A process probe error invalidated the anchored cycle before terminal outcome."
    if parse_status == "parse_error":
        return "Parsed surface became unavailable before the anchored cycle reached a terminal outcome."
    return "Anchored completion monitoring lost its authoritative parsed surface before terminal outcome."


def _build_stale_active_recovery_candidate(
    *,
    parsed_surface: HoumaoParsedSurface | None,
    diagnostics: HoumaoTrackedDiagnostics,
    surface: HoumaoTrackedSurface,
    turn: HoumaoTrackedTurn,
    tracker_state: TrackedStateSnapshot,
    active_turn_anchor_present: bool,
    hook_lifecycle_hold: bool = False,
) -> _StaleActiveRecoveryCandidate | None:
    """Return one stale-active recovery candidate when the state is submit-ready but stuck active."""

    if hook_lifecycle_hold:
        return None
    if active_turn_anchor_present:
        return None
    if parsed_surface is None or diagnostics.availability != "available":
        return None
    if not _is_submit_ready(parsed_surface):
        return None
    if surface.accepting_input != "yes" or surface.editing_input != "no":
        return None
    if turn.phase != "active":
        return None
    active_reasons = tracker_state.active_reasons
    if active_reasons and not set(active_reasons).issubset({"status_row", "compaction_status"}):
        return None
    signature_payload = json.dumps(
        {
            "parsed_surface": {
                "availability": parsed_surface.availability,
                "business_state": parsed_surface.business_state,
                "input_mode": parsed_surface.input_mode,
                "ui_context": parsed_surface.ui_context,
                "normalized_projection_text": parsed_surface.normalized_projection_text,
            },
            "surface": surface.model_dump(mode="json"),
            "turn_phase": turn.phase,
            "last_turn_result": tracker_state.last_turn_result,
            "last_turn_source": tracker_state.last_turn_source,
            "active_reasons": list(active_reasons),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return _StaleActiveRecoveryCandidate(
        signature=hashlib.sha1(signature_payload.encode("utf-8")).hexdigest(),
        active_reasons=active_reasons,
    )


def _build_final_stable_active_recovery_candidate(
    *,
    turn: HoumaoTrackedTurn,
    rendered_surface_signature: str | None,
    hook_lifecycle_hold: bool = False,
) -> _FinalStableActiveRecoveryCandidate | None:
    """Return one final stable-active recovery candidate keyed only on rendered-surface stability.

    The recovery is the parser-independent backstop for detector misclassification.
    Its candidate signature is the rendered-surface signature alone, and the only
    preconditions are that `turn.phase` is currently `active` (something to
    recover) and that the rendered-surface signature is observable. Parser
    output, tracker state, and active-reason flags are intentionally not
    consulted so the recovery cannot be vetoed by the same activity-detection
    pipeline whose faults it exists to repair. Hook lifecycle authority does
    veto the recovery, because an active hook turn is authoritative evidence
    that the TUI surface is stale rather than misclassified.
    """

    if hook_lifecycle_hold:
        return None
    if turn.phase != "active":
        return None
    if rendered_surface_signature is None:
        return None
    return _FinalStableActiveRecoveryCandidate(
        signature=rendered_surface_signature,
        active_reasons=(),
    )


def _rendered_surface_signature(output_text: str | None) -> str | None:
    """Return a parser-independent stability signature of the rendered surface.

    The signature is a `sha256` hex of the tmux capture text after stripping
    ANSI escape sequences and right-trimming each line. It survives styling
    jitter and trailing-pad-width differences between captures while flipping
    on any visible text change. It is intentionally independent of any
    activity-detection or tracker output so that final stable-active recovery
    can judge purely from rendered-surface stability.
    """

    if output_text is None:
        return None
    stripped = ANSI_ESCAPE_RE.sub("", output_text).replace(" ", " ")
    normalized = "\n".join(line.rstrip() for line in stripped.splitlines())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _message_excerpt(message: str) -> str | None:
    """Return a short message excerpt for anchor diagnostics."""

    collapsed = " ".join(message.split())
    if not collapsed:
        return None
    if len(collapsed) <= 120:
        return collapsed
    return f"{collapsed[:119]}…"


def _parsed_surface_debug_payload(
    parsed_surface: HoumaoParsedSurface | None,
) -> dict[str, object] | None:
    """Return a compact parsed-surface payload for tracking diagnostics."""

    if parsed_surface is None:
        return None
    normalized_projection_text = normalize_projection_text(
        parsed_surface.normalized_projection_text
    )
    return {
        "availability": parsed_surface.availability,
        "business_state": parsed_surface.business_state,
        "input_mode": parsed_surface.input_mode,
        "ui_context": parsed_surface.ui_context,
        "baseline_invalidated": parsed_surface.baseline_invalidated,
        "operator_blocked_excerpt": parsed_surface.operator_blocked_excerpt,
        "projection_sha1": _sha1_text(normalized_projection_text),
        "projection_length": len(normalized_projection_text),
    }


def _sha1_text(value: str | None) -> str | None:
    """Return the SHA-1 digest for one optional text payload."""

    if value is None:
        return None
    return hashlib.sha1(value.encode("utf-8")).hexdigest()


def _error_message(detail: HoumaoErrorDetail | None) -> str | None:
    """Return the error message for optional error detail."""

    if detail is None:
        return None
    return detail.message


def _surface_field(parsed_surface: HoumaoParsedSurface | None, field_name: str) -> object:
    """Return one optional parsed-surface field."""

    if parsed_surface is None:
        return None
    return getattr(parsed_surface, field_name)
