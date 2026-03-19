"""In-memory live tracking and reduction for server-owned TUI state."""

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from houmao.server.models import (
    CompletionState,
    HoumaoErrorDetail,
    HoumaoLifecycleTimingMetadata,
    HoumaoOperatorState,
    HoumaoParsedSurface,
    HoumaoProbeSnapshot,
    HoumaoRecentTransition,
    HoumaoStabilityMetadata,
    HoumaoTerminalHistoryResponse,
    HoumaoTerminalStateResponse,
    HoumaoTrackedSessionIdentity,
    OperatorStatus,
    ParseStatus,
    ProcessState,
    ReadinessState,
    TransportState,
)


def utc_now_iso() -> str:
    """Return one current UTC timestamp string."""

    return datetime.now(UTC).isoformat(timespec="seconds")


@dataclass(frozen=True)
class SurfaceReduction:
    """Derived readiness/completion state for one parsed surface cycle."""

    readiness_state: ReadinessState
    completion_state: CompletionState
    projection_changed: bool
    readiness_unknown_elapsed_seconds: float | None
    completion_unknown_elapsed_seconds: float | None
    completion_candidate_elapsed_seconds: float | None


@dataclass(frozen=True)
class SurfaceObservation:
    """Input observation for continuous parsed-surface reduction."""

    availability: str
    business_state: str
    input_mode: str
    ui_context: str
    normalized_projection_text: str
    operator_blocked_excerpt: str | None
    baseline_invalidated: bool
    monotonic_ts: float
    error_detail: str | None = None


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
    ) -> None:
        """Initialize the live session tracker."""

        self.m_identity = identity
        self.m_recent_transition_limit = recent_transition_limit
        self.m_stability_threshold_seconds = stability_threshold_seconds
        self.m_completion_stability_seconds = completion_stability_seconds
        self.m_unknown_to_stalled_timeout_seconds = unknown_to_stalled_timeout_seconds
        self.m_lock = threading.RLock()
        self.m_surface_reducer = _SurfaceStateReducer(
            completion_stability_seconds=completion_stability_seconds,
            unknown_to_stalled_timeout_seconds=unknown_to_stalled_timeout_seconds,
        )
        self.m_recent_transitions: list[HoumaoRecentTransition] = []
        self.m_last_signature_payload: str | None = None
        self.m_stable_since_monotonic: float | None = None
        self.m_stable_since_utc: str = utc_now_iso()
        self.m_baseline_pos: int | None = None
        self.m_last_state = _build_initial_state(
            identity=identity,
            completion_stability_seconds=completion_stability_seconds,
            unknown_to_stalled_timeout_seconds=unknown_to_stalled_timeout_seconds,
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
            entries = list(self.m_recent_transitions[-limit:] if limit > 0 else self.m_recent_transitions)
            return HoumaoTerminalHistoryResponse(
                terminal_id=self.m_last_state.terminal_id,
                tracked_session_id=self.m_identity.tracked_session_id,
                entries=entries,
            )

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
    ) -> HoumaoTerminalStateResponse:
        """Record one tracking cycle and return the updated public state."""

        with self.m_lock:
            self.m_identity = identity
            reduction = _default_surface_reduction()
            if parsed_surface is not None:
                reduction = self.m_surface_reducer.observe(
                    SurfaceObservation(
                        availability=parsed_surface.availability,
                        business_state=parsed_surface.business_state,
                        input_mode=parsed_surface.input_mode,
                        ui_context=parsed_surface.ui_context,
                        normalized_projection_text=parsed_surface.normalized_projection_text,
                        operator_blocked_excerpt=parsed_surface.operator_blocked_excerpt,
                        baseline_invalidated=parsed_surface.baseline_invalidated,
                        monotonic_ts=monotonic_ts,
                        error_detail=None,
                    )
                )

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
            signature_payload = json.dumps(
                _visible_signature_payload(
                    transport_state=transport_state,
                    process_state=process_state,
                    parse_status=parse_status,
                    probe_error=probe_error,
                    parse_error=parse_error,
                    parsed_surface=parsed_surface,
                    operator_state=operator_state,
                ),
                sort_keys=True,
                separators=(",", ":"),
            )
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
            response = HoumaoTerminalStateResponse(
                terminal_id=_terminal_alias(identity),
                tracked_session=identity,
                transport_state=transport_state,
                process_state=process_state,
                parse_status=parse_status,
                probe_snapshot=probe_snapshot,
                probe_error=probe_error,
                parse_error=parse_error,
                parsed_surface=parsed_surface,
                operator_state=operator_state,
                lifecycle_timing=HoumaoLifecycleTimingMetadata(
                    readiness_unknown_elapsed_seconds=reduction.readiness_unknown_elapsed_seconds,
                    completion_unknown_elapsed_seconds=reduction.completion_unknown_elapsed_seconds,
                    completion_candidate_elapsed_seconds=reduction.completion_candidate_elapsed_seconds,
                    unknown_to_stalled_timeout_seconds=self.m_unknown_to_stalled_timeout_seconds,
                    completion_stability_seconds=self.m_completion_stability_seconds,
                ),
                stability=stability,
                recent_transitions=list(self.m_recent_transitions),
            )
            transition = _build_transition(previous=self.m_last_state, current=response)
            if transition is not None:
                self.m_recent_transitions.append(transition)
                self.m_recent_transitions = self.m_recent_transitions[
                    -self.m_recent_transition_limit :
                ]
                response = response.model_copy(
                    update={"recent_transitions": list(self.m_recent_transitions)}
                )
            self.m_last_state = response
            return response


class _SurfaceStateReducer:
    """Continuous readiness/completion reducer adapted for live tracking."""

    def __init__(
        self,
        *,
        completion_stability_seconds: float,
        unknown_to_stalled_timeout_seconds: float,
    ) -> None:
        """Initialize the reducer."""

        self.m_completion_stability_seconds = completion_stability_seconds
        self.m_unknown_to_stalled_timeout_seconds = unknown_to_stalled_timeout_seconds
        self.m_last_business_state: str | None = None
        self.m_readiness_unknown_started_at: float | None = None
        self.m_readiness_stalled = False
        self.m_completion_unknown_started_at: float | None = None
        self.m_completion_stalled = False
        self.m_last_ready_projection_key: str | None = None
        self.m_last_ready_projection_streak = 0
        self.m_cycle_baseline_projection_key: str | None = None
        self.m_cycle_frozen_projection_key: str | None = None
        self.m_cycle_saw_working = False
        self.m_cycle_saw_projection_change = False
        self.m_candidate_started_at: float | None = None
        self.m_candidate_signature: tuple[Any, ...] | None = None

    def observe(self, observation: SurfaceObservation) -> SurfaceReduction:
        """Consume one parsed-surface observation."""

        readiness_state, readiness_unknown_elapsed_seconds = self._reduce_readiness(observation)
        (
            completion_state,
            completion_unknown_elapsed_seconds,
            completion_candidate_elapsed_seconds,
            projection_changed,
        ) = self._reduce_completion(observation)
        self.m_last_business_state = observation.business_state
        return SurfaceReduction(
            readiness_state=readiness_state,
            completion_state=completion_state,
            projection_changed=projection_changed,
            readiness_unknown_elapsed_seconds=readiness_unknown_elapsed_seconds,
            completion_unknown_elapsed_seconds=completion_unknown_elapsed_seconds,
            completion_candidate_elapsed_seconds=completion_candidate_elapsed_seconds,
        )

    def _reduce_readiness(
        self,
        observation: SurfaceObservation,
    ) -> tuple[ReadinessState, float | None]:
        """Update readiness state from one observation."""

        classification = _classify_readiness(observation)
        if classification == "unknown":
            if self.m_readiness_unknown_started_at is None:
                self.m_readiness_unknown_started_at = observation.monotonic_ts
            elapsed = observation.monotonic_ts - self.m_readiness_unknown_started_at
            if elapsed >= self.m_unknown_to_stalled_timeout_seconds:
                self.m_readiness_stalled = True
                return "stalled", elapsed
            return "unknown", elapsed

        self.m_readiness_unknown_started_at = None
        self.m_readiness_stalled = False
        return classification, None

    def _reduce_completion(
        self,
        observation: SurfaceObservation,
    ) -> tuple[CompletionState, float | None, float | None, bool]:
        """Update completion state from one observation."""

        classification = _classify_completion_surface(observation)
        was_submit_ready = _is_submit_ready(observation)
        previous_ready_projection_key = self.m_last_ready_projection_key
        previous_ready_projection_streak = self.m_last_ready_projection_streak
        if classification == "unknown":
            if self.m_completion_unknown_started_at is None:
                self.m_completion_unknown_started_at = observation.monotonic_ts
            elapsed = observation.monotonic_ts - self.m_completion_unknown_started_at
            if elapsed >= self.m_unknown_to_stalled_timeout_seconds:
                self.m_completion_stalled = True
                return "stalled", elapsed, None, self.m_cycle_saw_projection_change
            return "unknown", elapsed, None, self.m_cycle_saw_projection_change

        self.m_completion_unknown_started_at = None
        self.m_completion_stalled = False

        if classification in {"failed", "blocked"}:
            self.m_candidate_started_at = None
            self.m_candidate_signature = None
            if was_submit_ready:
                self.m_last_ready_projection_key = observation.normalized_projection_text
            return classification, None, None, self.m_cycle_saw_projection_change

        if observation.business_state == "working" and self.m_last_business_state != "working":
            self.m_cycle_baseline_projection_key = (
                self.m_last_ready_projection_key or observation.normalized_projection_text
            )
            self.m_cycle_frozen_projection_key = None
            self.m_cycle_saw_working = False
            self.m_cycle_saw_projection_change = False
            self.m_candidate_started_at = None
            self.m_candidate_signature = None

        effective_projection_key = observation.normalized_projection_text
        if observation.baseline_invalidated:
            if self.m_cycle_frozen_projection_key is None:
                self.m_cycle_frozen_projection_key = effective_projection_key
            effective_projection_key = self.m_cycle_frozen_projection_key
        elif self.m_cycle_frozen_projection_key is not None:
            effective_projection_key = self.m_cycle_frozen_projection_key

        if (
            was_submit_ready
            and self.m_cycle_baseline_projection_key is None
            and previous_ready_projection_key is not None
            and previous_ready_projection_streak >= 2
            and effective_projection_key != previous_ready_projection_key
        ):
            self.m_cycle_baseline_projection_key = previous_ready_projection_key
            self.m_cycle_saw_projection_change = True

        if observation.business_state == "working":
            if self.m_cycle_baseline_projection_key is None:
                self.m_cycle_baseline_projection_key = (
                    self.m_last_ready_projection_key or observation.normalized_projection_text
                )
            self.m_cycle_saw_working = True
            self.m_candidate_started_at = None
            self.m_candidate_signature = None
            return "in_progress", None, None, self.m_cycle_saw_projection_change

        if self.m_cycle_baseline_projection_key is not None:
            self.m_cycle_saw_projection_change = self.m_cycle_saw_projection_change or (
                effective_projection_key != self.m_cycle_baseline_projection_key
            )

        if was_submit_ready and (
            self.m_cycle_saw_working or self.m_cycle_saw_projection_change
        ):
            signature = (
                observation.availability,
                observation.business_state,
                observation.input_mode,
                effective_projection_key,
                self.m_cycle_saw_working,
                self.m_cycle_saw_projection_change,
            )
            if signature != self.m_candidate_signature:
                self.m_candidate_signature = signature
                self.m_candidate_started_at = observation.monotonic_ts
            assert self.m_candidate_started_at is not None
            candidate_elapsed_seconds = observation.monotonic_ts - self.m_candidate_started_at
            if candidate_elapsed_seconds >= self.m_completion_stability_seconds:
                self._remember_submit_ready_projection(effective_projection_key)
                return (
                    "completed",
                    None,
                    candidate_elapsed_seconds,
                    self.m_cycle_saw_projection_change,
                )
            self._remember_submit_ready_projection(effective_projection_key)
            return (
                "candidate_complete",
                None,
                candidate_elapsed_seconds,
                self.m_cycle_saw_projection_change,
            )
        elif self.m_cycle_baseline_projection_key is None:
            self.m_candidate_started_at = None
            self.m_candidate_signature = None
            if was_submit_ready:
                self._remember_submit_ready_projection(effective_projection_key)
            return "inactive", None, None, self.m_cycle_saw_projection_change
        else:
            self.m_candidate_started_at = None
            self.m_candidate_signature = None
            if was_submit_ready:
                self._remember_submit_ready_projection(effective_projection_key)
            return "waiting", None, None, self.m_cycle_saw_projection_change

    def _remember_submit_ready_projection(self, projection_key: str) -> None:
        """Track consecutive ready observations for one projection surface."""

        if self.m_last_ready_projection_key == projection_key:
            self.m_last_ready_projection_streak += 1
            return
        self.m_last_ready_projection_key = projection_key
        self.m_last_ready_projection_streak = 1


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
        transport_state="tmux_missing",
        process_state="unknown",
        parse_status="transport_unavailable",
        probe_snapshot=None,
        probe_error=None,
        parse_error=None,
        parsed_surface=None,
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
    transport_state: TransportState,
    process_state: ProcessState,
    parse_status: ParseStatus,
    probe_error: HoumaoErrorDetail | None,
    parse_error: HoumaoErrorDetail | None,
    parsed_surface: HoumaoParsedSurface | None,
    operator_state: HoumaoOperatorState,
) -> dict[str, object]:
    """Return the operator-visible signature payload used for stability timing."""

    return {
        "transport_state": transport_state,
        "process_state": process_state,
        "parse_status": parse_status,
        "probe_error": probe_error.model_dump(mode="json") if probe_error is not None else None,
        "parse_error": parse_error.model_dump(mode="json") if parse_error is not None else None,
        "parsed_surface": parsed_surface.model_dump(mode="json")
        if parsed_surface is not None
        else None,
        "operator_state": {
            "status": operator_state.status,
            "readiness_state": operator_state.readiness_state,
            "completion_state": operator_state.completion_state,
            "detail": operator_state.detail,
            "projection_changed": operator_state.projection_changed,
        },
    }


def _build_transition(
    *,
    previous: HoumaoTerminalStateResponse,
    current: HoumaoTerminalStateResponse,
) -> HoumaoRecentTransition | None:
    """Return one recent transition when the visible state changed."""

    field_pairs: list[tuple[str, object, object]] = [
        ("transport_state", previous.transport_state, current.transport_state),
        ("process_state", previous.process_state, current.process_state),
        ("parse_status", previous.parse_status, current.parse_status),
        ("operator_status", previous.operator_state.status, current.operator_state.status),
        (
            "readiness_state",
            previous.operator_state.readiness_state,
            current.operator_state.readiness_state,
        ),
        (
            "completion_state",
            previous.operator_state.completion_state,
            current.operator_state.completion_state,
        ),
        (
            "projection_changed",
            previous.operator_state.projection_changed,
            current.operator_state.projection_changed,
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
    return HoumaoRecentTransition(
        recorded_at_utc=current.operator_state.updated_at_utc,
        summary=summary,
        changed_fields=list(changed_fields),
        transport_state=current.transport_state,
        process_state=current.process_state,
        parse_status=current.parse_status,
        operator_status=current.operator_state.status,
    )


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


def _classify_readiness(observation: SurfaceObservation) -> str:
    """Return readiness classification for one parsed observation."""

    if observation.availability in {"unsupported", "disconnected"}:
        return "failed"
    if _is_operator_blocked(observation):
        return "blocked"
    if _is_unknown_for_stall(observation):
        return "unknown"
    if _is_submit_ready(observation):
        return "ready"
    return "waiting"


def _classify_completion_surface(observation: SurfaceObservation) -> str:
    """Return base completion classification before stability timing."""

    if observation.availability in {"unsupported", "disconnected"}:
        return "failed"
    if _is_operator_blocked(observation):
        return "blocked"
    if _is_unknown_for_stall(observation):
        return "unknown"
    if observation.business_state == "working":
        return "in_progress"
    return "waiting"


def _is_submit_ready(observation: SurfaceObservation) -> bool:
    """Return whether the parsed surface is prompt-submit ready."""

    return (
        observation.availability == "supported"
        and observation.business_state == "idle"
        and observation.input_mode == "freeform"
    )


def _is_operator_blocked(observation: SurfaceObservation) -> bool:
    """Return whether the parsed surface requires operator attention."""

    return (
        observation.availability == "supported"
        and observation.business_state == "awaiting_operator"
    )


def _is_unknown_for_stall(observation: SurfaceObservation) -> bool:
    """Return whether the parsed surface is effectively unknown."""

    return observation.availability == "unknown" or (
        observation.availability == "supported" and observation.business_state == "unknown"
    )


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
