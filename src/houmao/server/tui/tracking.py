"""In-memory live tracking and reduction for server-owned TUI state."""

from __future__ import annotations

import hashlib
import json
import threading
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

from reactivex import abc
from reactivex.scheduler import HistoricalScheduler
from reactivex.subject import Subject

from houmao.lifecycle import (
    AnchoredCompletionSnapshot,
    LifecycleObservation,
    ReadinessSnapshot,
    TurnAnchor,
    build_anchored_completion_pipeline,
    build_readiness_pipeline,
    normalize_projection_text,
)
from houmao.server.models import (
    CompletionState,
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
    HoumaoTerminalStateResponse,
    HoumaoTrackedTurn,
    HoumaoTrackedSessionIdentity,
    ManagedAgentTurnPhase,
    OperatorStatus,
    ParseStatus,
    ProcessState,
    ReadinessState,
    TrackedDiagnosticsAvailability,
    TrackedLastTurnResult,
    TrackedLastTurnSource,
    TransportState,
)
from houmao.server.tracking_debug import TrackingDebugSink
from houmao.server.tui.turn_signals import (
    DetectedTurnSignals,
    select_tracked_turn_signal_detector,
)

_SURFACE_INFERENCE_MIN_GROWTH_CHARS = 48
_SURFACE_INFERENCE_MIN_ADDED_LINES = 2


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


class LiveSessionTracker:
    """Own one tracked session's in-memory live state and recent history."""

    def __init__(
        self,
        *,
        identity: HoumaoTrackedSessionIdentity,
        recent_transition_limit: int,
        stability_threshold_seconds: float,
        completion_stability_seconds: float,
        unknown_to_stalled_timeout_seconds: float,
        tracking_debug_sink: TrackingDebugSink | None = None,
    ) -> None:
        """Initialize the live session tracker."""

        self.m_identity = identity
        self.m_recent_transition_limit = recent_transition_limit
        self.m_stability_threshold_seconds = stability_threshold_seconds
        self.m_completion_stability_seconds = completion_stability_seconds
        self.m_unknown_to_stalled_timeout_seconds = unknown_to_stalled_timeout_seconds
        self.m_tracking_debug_sink = tracking_debug_sink
        self.m_lock = threading.RLock()
        self.m_scheduler = HistoricalScheduler()
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
        self.m_settled_success_signature: str | None = None
        self.m_last_state = _build_initial_state(
            identity=identity,
            completion_stability_seconds=completion_stability_seconds,
            unknown_to_stalled_timeout_seconds=unknown_to_stalled_timeout_seconds,
        )
        self.m_active_turn_previous_last_turn = self.m_last_state.last_turn

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
            self.m_last_state = self.m_last_state.model_copy(
                update={
                    "terminal_id": _terminal_alias(identity),
                    "tracked_session": identity,
                }
            )

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
        source: Literal["terminal_input", "surface_inference"],
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
        self.m_settled_success_signature = None
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

    def _should_infer_prompt_submission(
        self,
        *,
        parsed_surface: HoumaoParsedSurface,
    ) -> tuple[bool, dict[str, object]]:
        """Return whether the current surface implies an inferred prompt submission."""

        previous_surface = self.m_last_state.parsed_surface
        if self.m_active_turn_anchor is not None or previous_surface is None:
            return False, {}
        previous_normalized = normalize_projection_text(previous_surface.normalized_projection_text)
        current_normalized = normalize_projection_text(parsed_surface.normalized_projection_text)
        growth_chars = len(current_normalized) - len(previous_normalized)
        added_lines = current_normalized.count("\n") - previous_normalized.count("\n")
        debug_data = {
            "previous_submit_ready": _is_submit_ready(previous_surface),
            "previous_stability_stable": self.m_last_state.stability.stable,
            "previous_operator_status": self.m_last_state.operator_state.status,
            "previous_projection_sha1": _sha1_text(previous_normalized),
            "current_projection_sha1": _sha1_text(current_normalized),
            "baseline_invalidated": parsed_surface.baseline_invalidated,
            "growth_chars": growth_chars,
            "added_lines": added_lines,
        }
        if not _is_submit_ready(previous_surface):
            return False, debug_data
        if not self.m_last_state.stability.stable:
            return False, debug_data
        if previous_normalized == current_normalized:
            return False, debug_data
        if (
            growth_chars < _SURFACE_INFERENCE_MIN_GROWTH_CHARS
            and added_lines < _SURFACE_INFERENCE_MIN_ADDED_LINES
        ):
            return False, debug_data
        return True, debug_data

    def note_prompt_submission(
        self,
        *,
        message: str,
        observed_at_utc: str,
        monotonic_ts: float,
    ) -> HoumaoTerminalStateResponse:
        """Arm one server-owned turn anchor after a successful input submission."""

        with self.m_lock:
            self._advance_scheduler(monotonic_ts=monotonic_ts)
            self._drain_pipeline_snapshots()

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

            operator_state = self.m_last_state.operator_state
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
            updated = self.m_last_state.model_copy(
                update={
                    "turn": HoumaoTrackedTurn(phase="active"),
                    "operator_state": operator_state,
                    "lifecycle_timing": self.m_last_state.lifecycle_timing.model_copy(
                        update={"completion_candidate_elapsed_seconds": None}
                    ),
                    "lifecycle_authority": lifecycle_authority,
                }
            )
            updated = self._publish_state(response=updated, monotonic_ts=monotonic_ts)
            self._emit_debug(
                stream="tracker-anchor",
                event_type="note_prompt_submission_applied",
                monotonic_ts=monotonic_ts,
                anchor_id=anchor.anchor_id,
                data={
                    "completion_authority": updated.lifecycle_authority.completion_authority,
                    "turn_anchor_state": updated.lifecycle_authority.turn_anchor_state,
                    "completion_monitoring_armed": (
                        updated.lifecycle_authority.completion_monitoring_armed
                    ),
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
            self.m_cycle_seq += 1
            cycle_seq = self.m_cycle_seq
            self._advance_scheduler(monotonic_ts=monotonic_ts)
            self._drain_pipeline_snapshots()
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
                    "previous_operator_status": self.m_last_state.operator_state.status,
                    "previous_completion_state": self.m_last_state.operator_state.completion_state,
                    "previous_completion_authority": (
                        self.m_last_state.lifecycle_authority.completion_authority
                    ),
                    "previous_turn_anchor_state": (
                        self.m_last_state.lifecycle_authority.turn_anchor_state
                    ),
                },
            )

            reduction = _default_surface_reduction()
            if parsed_surface is not None:
                inferred_prompt_submission, inference_debug = self._should_infer_prompt_submission(
                    parsed_surface=parsed_surface
                )
                if inferred_prompt_submission:
                    previous_surface = self.m_last_state.parsed_surface
                    assert previous_surface is not None
                    self._arm_turn_anchor(
                        source="surface_inference",
                        baseline_projection_text=normalize_projection_text(
                            previous_surface.normalized_projection_text
                        ),
                        observed_at_utc=observed_at_utc,
                        monotonic_ts=monotonic_ts,
                        message_excerpt=None,
                        cycle_seq=cycle_seq,
                        reason="submit_ready_projection_changed",
                    )
                    self._emit_debug(
                        stream="tracker-anchor",
                        event_type="inferred_prompt_submission",
                        monotonic_ts=monotonic_ts,
                        cycle_seq=cycle_seq,
                        anchor_id=(
                            self.m_active_turn_anchor.anchor_id
                            if self.m_active_turn_anchor is not None
                            else None
                        ),
                        data=inference_debug,
                    )
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
            detected_turn_signals = select_tracked_turn_signal_detector(tool=identity.tool).detect(
                output_text=output_text,
                parsed_surface=parsed_surface,
            )
            diagnostics = _build_tracked_diagnostics(
                transport_state=transport_state,
                process_state=process_state,
                parse_status=parse_status,
                probe_error=probe_error,
                parse_error=parse_error,
                parsed_surface=parsed_surface,
            )
            surface = HoumaoTrackedSurface(
                accepting_input=detected_turn_signals.accepting_input,
                editing_input=detected_turn_signals.editing_input,
                ready_posture=detected_turn_signals.ready_posture,
            )
            last_turn = self._build_last_turn(
                observed_at_utc=observed_at_utc,
                diagnostics=diagnostics,
                surface=surface,
                reduction=reduction,
                detected_turn_signals=detected_turn_signals,
            )
            turn = HoumaoTrackedTurn(
                phase=_build_turn_phase(
                    diagnostics=diagnostics,
                    surface=surface,
                    active_turn_anchor=self.m_active_turn_anchor,
                    reduction=reduction,
                    detected_turn_signals=detected_turn_signals,
                    last_turn=last_turn,
                )
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
                    "accepting_input": surface.accepting_input,
                    "editing_input": surface.editing_input,
                    "ready_posture": surface.ready_posture,
                    "signal_notes": list(detected_turn_signals.notes),
                },
            )
            stability = self._build_stability(
                diagnostics=diagnostics,
                parsed_surface=parsed_surface,
                surface=surface,
                turn=turn,
                last_turn=last_turn,
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
                operator_state=operator_state,
                lifecycle_timing=HoumaoLifecycleTimingMetadata(
                    readiness_unknown_elapsed_seconds=reduction.readiness_unknown_elapsed_seconds,
                    completion_unknown_elapsed_seconds=reduction.completion_unknown_elapsed_seconds,
                    completion_candidate_elapsed_seconds=reduction.completion_candidate_elapsed_seconds,
                    unknown_to_stalled_timeout_seconds=self.m_unknown_to_stalled_timeout_seconds,
                    completion_stability_seconds=self.m_completion_stability_seconds,
                ),
                lifecycle_authority=lifecycle_authority,
                stability=stability,
                recent_transitions=list(self.m_recent_transitions),
            )
            response = self._publish_state(response=response, monotonic_ts=monotonic_ts)
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

    def _build_stability(
        self,
        *,
        diagnostics: HoumaoTrackedDiagnostics,
        parsed_surface: HoumaoParsedSurface | None,
        surface: HoumaoTrackedSurface,
        turn: HoumaoTrackedTurn,
        last_turn: HoumaoTrackedLastTurn,
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
    ) -> HoumaoTerminalStateResponse:
        """Store one response as the current state and append visible transitions."""

        transition = _build_transition(previous=self.m_last_state, current=response)
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
                    "operator_status": response.operator_state.status,
                    "completion_state": response.operator_state.completion_state,
                    "completion_authority": response.lifecycle_authority.completion_authority,
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
                    "operator_status": response.operator_state.status,
                    "completion_state": response.operator_state.completion_state,
                    "completion_authority": response.lifecycle_authority.completion_authority,
                },
            )
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
        self.m_settled_success_signature = None
        self.m_lost_turn_anchor = _LostTurnAnchor(lost_at_utc=lost_at_utc, reason=reason)
        self._emit_debug(
            stream="tracker-anchor",
            event_type="turn_anchor_lost",
            monotonic_ts=monotonic_ts,
            cycle_seq=cycle_seq,
            anchor_id=previous_anchor_id,
            data={"lost_at_utc": lost_at_utc, "reason": reason},
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
        self.m_settled_success_signature = None
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

    def _build_last_turn(
        self,
        *,
        observed_at_utc: str,
        diagnostics: HoumaoTrackedDiagnostics,
        surface: HoumaoTrackedSurface,
        reduction: SurfaceReduction,
        detected_turn_signals: DetectedTurnSignals,
    ) -> HoumaoTrackedLastTurn:
        """Build the sticky public last-turn view for the current cycle."""

        active_anchor = self.m_active_turn_anchor
        active_anchor_id = active_anchor.anchor_id if active_anchor is not None else None
        previous_last_turn = self.m_last_state.last_turn

        should_retract_success = bool(
            active_anchor is not None
            and active_anchor_id == self.m_last_published_turn_anchor_id
            and previous_last_turn.result == "success"
            and self.m_settled_success_signature is not None
            and (
                reduction.completion_state != "completed"
                or detected_turn_signals.success_blocked
                or detected_turn_signals.surface_signature != self.m_settled_success_signature
            )
        )
        if should_retract_success:
            self.m_last_published_turn_anchor_id = None
            self.m_settled_success_signature = None
            previous_last_turn = self.m_active_turn_previous_last_turn

        if active_anchor is None:
            return previous_last_turn

        if diagnostics.availability in {"error", "tui_down", "unavailable"}:
            return previous_last_turn

        terminal_result: TrackedLastTurnResult | None = None
        if detected_turn_signals.interrupted:
            terminal_result = "interrupted"
            self.m_anchor_should_expire_after_publish = True
            self.m_settled_success_signature = None
        elif detected_turn_signals.known_failure:
            terminal_result = "known_failure"
            self.m_anchor_should_expire_after_publish = True
            self.m_settled_success_signature = None
        elif (
            reduction.completion_state == "completed"
            and surface.ready_posture == "yes"
            and not detected_turn_signals.success_blocked
        ):
            terminal_result = "success"
            if (
                active_anchor_id == self.m_last_published_turn_anchor_id
                and previous_last_turn.result == "success"
                and detected_turn_signals.surface_signature == self.m_settled_success_signature
            ):
                self.m_anchor_should_expire_after_publish = True
            else:
                self.m_settled_success_signature = detected_turn_signals.surface_signature

        if terminal_result is None:
            return previous_last_turn

        if active_anchor_id == self.m_last_published_turn_anchor_id and previous_last_turn.result == terminal_result:
            return previous_last_turn

        self.m_last_published_turn_anchor_id = active_anchor_id
        return HoumaoTrackedLastTurn(
            result=terminal_result,
            source=_tracked_last_turn_source(active_anchor),
            updated_at_utc=observed_at_utc,
        )


def _build_initial_state(
    *,
    identity: HoumaoTrackedSessionIdentity,
    completion_stability_seconds: float,
    unknown_to_stalled_timeout_seconds: float,
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


def _visible_signature_payload(
    *,
    diagnostics: HoumaoTrackedDiagnostics,
    parsed_surface: HoumaoParsedSurface | None,
    surface: HoumaoTrackedSurface,
    turn: HoumaoTrackedTurn,
    last_turn: HoumaoTrackedLastTurn,
) -> dict[str, object]:
    """Return the operator-visible signature payload used for stability timing."""

    return {
        "diagnostics": diagnostics.model_dump(mode="json"),
        "parsed_surface": parsed_surface.model_dump(mode="json")
        if parsed_surface is not None
        else None,
        "surface": surface.model_dump(mode="json"),
        "turn": turn.model_dump(mode="json"),
        "last_turn": last_turn.model_dump(mode="json"),
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
        ("turn_phase", previous.turn.phase, current.turn.phase),
        ("last_turn_result", previous.last_turn.result, current.last_turn.result),
        ("last_turn_source", previous.last_turn.source, current.last_turn.source),
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
    return HoumaoRecentTransition(
        recorded_at_utc=current.last_turn.updated_at_utc or current.operator_state.updated_at_utc,
        summary=summary,
        changed_fields=list(changed_fields),
        diagnostics_availability=current.diagnostics.availability,
        turn_phase=current.turn.phase,
        last_turn_result=current.last_turn.result,
        last_turn_source=current.last_turn.source,
        transport_state=current.transport_state,
        process_state=current.process_state,
        parse_status=current.parse_status,
        operator_status=current.operator_state.status,
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
        availability=_diagnostics_availability(
            transport_state=transport_state,
            process_state=process_state,
            parse_status=parse_status,
            probe_error=probe_error,
            parse_error=parse_error,
            parsed_surface=parsed_surface,
        ),
        transport_state=transport_state,
        process_state=process_state,
        parse_status=parse_status,
        probe_error=probe_error,
        parse_error=parse_error,
    )


def _diagnostics_availability(
    *,
    transport_state: TransportState,
    process_state: ProcessState,
    parse_status: ParseStatus,
    probe_error: HoumaoErrorDetail | None,
    parse_error: HoumaoErrorDetail | None,
    parsed_surface: HoumaoParsedSurface | None,
) -> TrackedDiagnosticsAvailability:
    """Map low-level observation outcomes into diagnostic availability."""

    if (
        probe_error is not None
        or parse_error is not None
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
    if parse_status == "parsed" and parsed_surface is not None and parsed_surface.availability == "supported":
        return "available"
    return "unknown"


def _build_turn_phase(
    *,
    diagnostics: HoumaoTrackedDiagnostics,
    surface: HoumaoTrackedSurface,
    active_turn_anchor: TurnAnchor | None,
    reduction: SurfaceReduction,
    detected_turn_signals: DetectedTurnSignals,
    last_turn: HoumaoTrackedLastTurn,
) -> ManagedAgentTurnPhase:
    """Map the current cycle into the simplified public turn phase."""

    if diagnostics.availability in {"error", "tui_down", "unavailable"}:
        return "unknown"
    if active_turn_anchor is not None:
        if (
            last_turn.result == "success"
            and reduction.completion_state == "completed"
            and surface.ready_posture == "yes"
            and not detected_turn_signals.success_blocked
        ):
            return "ready"
        return "active"
    if detected_turn_signals.active_evidence:
        return "active"
    if detected_turn_signals.ambiguous_interactive_surface:
        return "unknown"
    if surface.ready_posture == "yes":
        return "ready"
    return "unknown"


def _tracked_last_turn_source(active_turn_anchor: TurnAnchor) -> TrackedLastTurnSource:
    """Map one internal turn-anchor source to the public last-turn source enum."""

    if active_turn_anchor.source == "terminal_input":
        return "explicit_input"
    return "surface_inference"


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
