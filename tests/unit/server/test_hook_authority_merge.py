"""Unit tests for hook authority merging in the live session tracker."""

from __future__ import annotations

import json
from pathlib import Path

from houmao.hook_observation.reader import HookObservationChannel
from houmao.hook_observation.store import HookObservationStore
from houmao.server.models import (
    HoumaoParsedSurface,
    HoumaoTrackedSessionIdentity,
    HoumaoTerminalStateResponse,
)
from houmao.server.tui.tracking import LiveSessionTracker
from houmao.shared_tui_tracking.models import TrackedStateSnapshot


class _StaticTrackerSession:
    def __init__(self, *, state: TrackedStateSnapshot) -> None:
        self.m_state = state

    def current_state(self) -> TrackedStateSnapshot:
        return self.m_state

    def on_snapshot(self, _raw_text: str) -> None:
        return

    def on_input_submitted(self) -> None:
        return

    def close(self) -> None:
        return


def _identity() -> HoumaoTrackedSessionIdentity:
    return HoumaoTrackedSessionIdentity(
        tracked_session_id="claude-session",
        session_name="claude-session",
        tool="claude",
        observed_tool_version="2.1.296",
        tmux_session_name="HOUMAO-claude",
        terminal_aliases=["abcd1234"],
    )


def _tracker_state(
    *,
    surface_ready_posture: str = "yes",
    turn_phase: str = "ready",
    last_turn_result: str = "none",
    last_turn_source: str = "none",
    active_reasons: tuple[str, ...] = (),
    notes: tuple[str, ...] = (),
) -> TrackedStateSnapshot:
    return TrackedStateSnapshot(
        surface_accepting_input="yes" if surface_ready_posture == "yes" else "no",
        surface_editing_input="no",
        surface_ready_posture=surface_ready_posture,
        surface_pending_input="no",
        turn_phase=turn_phase,
        last_turn_result=last_turn_result,
        last_turn_source=last_turn_source,
        detector_name="claude_code",
        detector_version="2.1.x",
        active_reasons=active_reasons,
        notes=notes,
        stability_signature="sig",
        stable=True,
        stable_for_seconds=0.0,
        stable_since_seconds=0.0,
        observed_at_seconds=0.0,
    )


def _surface(
    *, ui_context: str = "normal_prompt", business_state: str = "idle"
) -> HoumaoParsedSurface:
    text = f"{ui_context}-{business_state}"
    return HoumaoParsedSurface(
        parser_family="claude_shadow",
        parser_preset_id="claude",
        parser_preset_version="1.0.0",
        availability="supported",
        business_state=business_state,
        input_mode="freeform" if business_state == "idle" else "closed",
        ui_context=ui_context,
        normalized_projection_text=text,
        dialog_text=text,
        dialog_head=text,
        dialog_tail=text,
        anomaly_codes=[],
        baseline_invalidated=False,
        operator_blocked_excerpt=None,
    )


class _Harness:
    def __init__(self, tmp_path: Path, *, state: TrackedStateSnapshot | None = None) -> None:
        self.store = HookObservationStore(tmp_path, generation=1)
        channel = HookObservationChannel.from_session_root(tmp_path)
        assert channel is not None
        self.tracker = LiveSessionTracker(
            identity=_identity(),
            recent_transition_limit=8,
            stability_threshold_seconds=1.0,
            completion_stability_seconds=1.0,
            unknown_to_stalled_timeout_seconds=30.0,
            hook_channel=channel,
        )
        self.set_state(state or _tracker_state())

    def set_state(self, state: TrackedStateSnapshot) -> None:
        self.tracker.m_tracker_session = _StaticTrackerSession(state=state)

    def append(self, event_name: str, **extra: object) -> None:
        self.store.append_event({"hook_event_name": event_name, **extra})

    def cycle(
        self,
        *,
        at: float,
        surface: HoumaoParsedSurface | None = None,
        output_text: str | None = None,
    ) -> HoumaoTerminalStateResponse:
        return self.tracker.record_cycle(
            identity=_identity(),
            observed_at_utc=f"2026-10-19T13:00:{int(at) % 60:02d}+00:00",
            monotonic_ts=at,
            transport_state="tmux_up",
            process_state="tui_up",
            parse_status="parsed",
            probe_snapshot=None,
            probe_error=None,
            parse_error=None,
            parsed_surface=surface or _surface(),
            output_text=output_text,
        )


def test_fold_happens_only_at_cycle_boundaries(tmp_path: Path) -> None:
    harness = _Harness(tmp_path)
    harness.cycle(at=0.0)
    harness.append("UserPromptSubmit", prompt_id="p1")

    assert harness.tracker.current_state().turn.phase == "ready"

    state = harness.cycle(at=1.0)
    assert state.turn.phase == "active"
    assert state.diagnostics.hook_channel_state == "active"


def test_hook_terminal_settles_last_turn_without_tui_settlement(tmp_path: Path) -> None:
    harness = _Harness(tmp_path)
    harness.append("UserPromptSubmit", prompt_id="p1")
    active = harness.cycle(at=0.0)

    assert active.turn.phase == "active"
    assert "hook_active_tui_ready" in active.diagnostics.hook_conflict_reasons
    assert active.work == "unknown"

    harness.append("Stop", prompt_id="p1", background_tasks=[])
    settled = harness.cycle(at=1.0)

    assert settled.turn.phase == "ready"
    assert settled.last_turn.result == "success"
    assert settled.last_turn.source == "hook_observation"
    assert settled.work == "clear"
    assert settled.settled is True
    assert settled.surface.ready_posture == "yes"
    assert settled.diagnostics.hook_channel_state == "active"
    assert settled.diagnostics.hook_counters is not None
    assert settled.diagnostics.hook_counters.events_seen >= 3
    assert settled.observation_channels is not None
    assert settled.observation_channels[0].state == "active"
    assert settled.observation_channels[0].last_event_name == "Stop"


def test_hook_blocked_marks_turn_and_operator_waiting(tmp_path: Path) -> None:
    harness = _Harness(tmp_path)
    harness.append("UserPromptSubmit", prompt_id="p1")
    harness.append("PermissionRequest", prompt_id="p1", tool_name="Bash")

    blocked = harness.cycle(at=0.0)

    assert blocked.turn.phase == "blocked"
    assert blocked.operator_state is not None
    assert blocked.operator_state.status == "waiting_user_answer"
    assert blocked.operator_state.completion_state == "blocked"
    assert "hook_blocked_tui_ready" in blocked.diagnostics.hook_conflict_reasons
    assert blocked.observation_channels is not None
    assert blocked.observation_channels[0].conflict_reasons


def test_hook_permission_resolved_returns_active(tmp_path: Path) -> None:
    harness = _Harness(tmp_path)
    harness.append("UserPromptSubmit", prompt_id="p1")
    harness.append("PermissionRequest", prompt_id="p1", tool_name="Bash")
    assert harness.cycle(at=0.0).turn.phase == "blocked"

    harness.append("PostToolUse", prompt_id="p1", tool_name="Bash", tool_use_id="tool-1")
    assert harness.cycle(at=1.0).turn.phase == "active"


def test_tui_modal_dismissal_exits_blocked_turn(tmp_path: Path) -> None:
    harness = _Harness(tmp_path)
    harness.append("UserPromptSubmit", prompt_id="p1")
    harness.append("PermissionRequest", prompt_id="p1", tool_name="Bash")

    blocked = harness.cycle(
        at=0.0, surface=_surface(ui_context="modal", business_state="awaiting_operator")
    )
    assert blocked.turn.phase == "blocked"

    dismissed = harness.cycle(at=1.0, surface=_surface())

    assert dismissed.turn.phase == "active"
    assert dismissed.operator_state is not None
    assert dismissed.operator_state.status == "processing"


def test_tui_user_rejected_evidence_exits_blocked_turn(tmp_path: Path) -> None:
    harness = _Harness(tmp_path, state=_tracker_state())
    harness.append("UserPromptSubmit", prompt_id="p1")
    harness.append("PermissionRequest", prompt_id="p1", tool_name="Bash")
    assert harness.cycle(at=0.0).turn.phase == "blocked"

    harness.set_state(
        _tracker_state(last_turn_result="interrupted", last_turn_source="surface_inference")
    )
    state = harness.cycle(at=1.0)

    assert state.turn.phase == "active"
    assert state.last_turn.result == "interrupted"


def test_tui_interrupt_overrides_hook_success(tmp_path: Path) -> None:
    harness = _Harness(tmp_path)
    harness.append("UserPromptSubmit", prompt_id="p1")
    assert harness.cycle(at=0.0).turn.phase == "active"

    harness.append("Stop", prompt_id="p1", background_tasks=[])
    harness.set_state(
        _tracker_state(last_turn_result="interrupted", last_turn_source="surface_inference")
    )
    state = harness.cycle(at=1.0)

    assert state.turn.phase == "ready"
    assert state.last_turn.result == "interrupted"
    assert "hook_success_tui_interrupted" in state.diagnostics.hook_conflict_reasons


def test_hook_failure_records_error_class_and_wins_over_tui_success(tmp_path: Path) -> None:
    harness = _Harness(tmp_path)
    harness.append("UserPromptSubmit", prompt_id="p1")
    assert harness.cycle(at=0.0).turn.phase == "active"

    harness.append("StopFailure", prompt_id="p1", error={"type": "rate_limit"})
    harness.set_state(
        _tracker_state(last_turn_result="success", last_turn_source="surface_inference")
    )
    state = harness.cycle(at=1.0)

    assert state.last_turn.result == "known_failure"
    assert state.last_turn.source == "hook_observation"
    assert state.last_turn.error_class == "rate_limit"
    assert "hook_failure_tui_success" in state.diagnostics.hook_conflict_reasons
    assert state.operator_state is not None
    assert state.operator_state.completion_state == "failed"


def test_hook_terminal_while_tui_shows_residue_notes_conflict(tmp_path: Path) -> None:
    harness = _Harness(tmp_path)
    harness.append("UserPromptSubmit", prompt_id="p1")
    assert harness.cycle(at=0.0).turn.phase == "active"

    harness.append("Stop", prompt_id="p1", background_tasks=[])
    harness.set_state(
        _tracker_state(
            surface_ready_posture="no", turn_phase="active", active_reasons=("tool_cell",)
        )
    )
    state = harness.cycle(at=1.0, output_text="active-residue")

    assert state.turn.phase == "ready"
    assert state.surface.ready_posture == "no"
    assert "hook_terminal_tui_active" in state.diagnostics.hook_conflict_reasons


def test_maintenance_holds_active_turn(tmp_path: Path) -> None:
    harness = _Harness(tmp_path)
    harness.append("UserPromptSubmit", prompt_id="p1")
    assert harness.cycle(at=0.0).turn.phase == "active"

    harness.append("PreCompact", prompt_id="p1", trigger="auto")
    compacting = harness.cycle(at=1.0)
    assert compacting.turn.phase == "active"

    harness.append("PostCompact", prompt_id="p1", trigger="auto")
    assert harness.cycle(at=2.0).turn.phase == "active"

    harness.append("Stop", prompt_id="p1", background_tasks=[])
    assert harness.cycle(at=3.0).turn.phase == "ready"


def test_explicit_input_correlation_preserves_source(tmp_path: Path) -> None:
    harness = _Harness(tmp_path)
    harness.tracker.note_prompt_submission(
        message="Explain the failure.",
        observed_at_utc="2026-10-19T13:00:00+00:00",
        monotonic_ts=0.0,
    )
    harness.append("UserPromptSubmit", prompt_id="p1")
    harness.append("Stop", prompt_id="p1", background_tasks=[])

    state = harness.cycle(at=0.5)

    assert state.last_turn.result == "success"
    assert state.last_turn.source == "explicit_input"


def test_stale_channel_returns_authority_to_tui(tmp_path: Path) -> None:
    harness = _Harness(tmp_path)
    assert harness.cycle(at=0.0, output_text="surface-0").diagnostics.hook_channel_state == "active"

    harness.set_state(
        _tracker_state(last_turn_result="success", last_turn_source="surface_inference")
    )
    stale = harness.cycle(at=31.0, output_text="surface-1")

    assert stale.diagnostics.hook_channel_state == "stale"
    assert stale.last_turn.result == "success"
    assert stale.last_turn.source == "surface_inference"
    assert stale.work == "unknown"
    assert "hook_stale_tui_authoritative" in stale.diagnostics.hook_conflict_reasons
    assert stale.observation_channels is not None
    assert stale.observation_channels[0].state == "stale"

    harness.append("UserPromptSubmit", prompt_id="p1")
    harness.append("StopFailure", prompt_id="p1", error={"type": "api_error"})
    recovered = harness.cycle(at=32.0, output_text="surface-2")

    assert recovered.diagnostics.hook_channel_state == "active"
    assert recovered.last_turn.result == "known_failure"
    assert recovered.last_turn.source == "hook_observation"
    assert "hook_correction_after_staleness" in recovered.diagnostics.hook_conflict_reasons


def test_stale_recovery_agreement_keeps_tui_source(tmp_path: Path) -> None:
    harness = _Harness(tmp_path)
    harness.cycle(at=0.0, output_text="surface-0")
    harness.set_state(
        _tracker_state(last_turn_result="success", last_turn_source="surface_inference")
    )
    assert harness.cycle(at=31.0, output_text="surface-1").diagnostics.hook_channel_state == "stale"

    harness.append("UserPromptSubmit", prompt_id="p1")
    harness.append("Stop", prompt_id="p1", background_tasks=[])
    recovered = harness.cycle(at=32.0, output_text="surface-2")

    assert recovered.last_turn.result == "success"
    assert recovered.last_turn.source == "surface_inference"
    assert "hook_correction_after_staleness" not in recovered.diagnostics.hook_conflict_reasons


def test_background_work_axis_tracks_terminal_payloads(tmp_path: Path) -> None:
    harness = _Harness(tmp_path)
    harness.append("UserPromptSubmit", prompt_id="p1")
    harness.append(
        "Stop",
        prompt_id="p1",
        background_tasks=[{"id": "task-1", "status": "running", "type": "bash"}],
    )
    completed = harness.cycle(at=0.0)

    assert completed.last_turn.result == "success"
    assert completed.work == "pending"
    assert completed.settled is False

    harness.append("UserPromptSubmit", prompt_id="p2")
    harness.append("StopFailure", prompt_id="p2", error={"type": "api_error"})
    failed = harness.cycle(at=1.0)

    assert failed.last_turn.result == "known_failure"
    assert failed.work == "pending"
    assert failed.settled is False


def test_orphan_terminal_never_manufactures_last_turn(tmp_path: Path) -> None:
    harness = _Harness(tmp_path)
    harness.append("Stop", prompt_id="p1", background_tasks=[])

    state = harness.cycle(at=0.0)

    assert state.last_turn.result == "none"
    assert state.diagnostics.hook_counters is not None
    assert state.diagnostics.hook_counters.orphan_terminals == 1
    assert "hook_orphan_terminal" in state.diagnostics.hook_conflict_reasons


def test_unknown_and_malformed_events_are_counted_and_reported(tmp_path: Path) -> None:
    harness = _Harness(tmp_path)
    harness.append("Notification", message="ignored")
    harness.append("NotAnEvent")
    harness.store.append_event({"hook_event_name": 123})

    state = harness.cycle(at=0.0)

    assert state.diagnostics.hook_counters is not None
    assert state.diagnostics.hook_counters.unknown_events == 2
    assert state.diagnostics.hook_counters.malformed_events == 1
    assert "hook_unknown_event" in state.diagnostics.hook_conflict_reasons
    assert "hook_malformed_event" in state.diagnostics.hook_conflict_reasons
    assert state.observation_channels is not None
    assert state.observation_channels[0].conflict_reasons


def test_older_generation_events_are_dropped_and_reported(tmp_path: Path) -> None:
    store = HookObservationStore(tmp_path, generation=1)
    store.append_event({"hook_event_name": "UserPromptSubmit", "prompt_id": "old"})
    store.begin_generation(2)
    store.append_event({"hook_event_name": "UserPromptSubmit", "prompt_id": "new"})
    channel = HookObservationChannel.from_session_root(tmp_path)
    assert channel is not None
    tracker = LiveSessionTracker(
        identity=_identity(),
        recent_transition_limit=8,
        stability_threshold_seconds=1.0,
        completion_stability_seconds=1.0,
        unknown_to_stalled_timeout_seconds=30.0,
        hook_channel=channel,
    )
    tracker.m_tracker_session = _StaticTrackerSession(state=_tracker_state())

    state = tracker.record_cycle(
        identity=_identity(),
        observed_at_utc="2026-10-19T13:00:00+00:00",
        monotonic_ts=0.0,
        transport_state="tmux_up",
        process_state="tui_up",
        parse_status="parsed",
        probe_snapshot=None,
        probe_error=None,
        parse_error=None,
        parsed_surface=_surface(),
    )

    assert state.turn.phase == "active"
    assert state.observation_channels is not None
    assert state.observation_channels[0].generation == 2
    assert "hook_orphan_generation" in state.diagnostics.hook_conflict_reasons


def test_disabled_channel_publishes_tui_only_state(tmp_path: Path) -> None:
    harness = _Harness(tmp_path)
    harness.append("UserPromptSubmit", prompt_id="p1")
    harness.append("Stop", prompt_id="p1", background_tasks=[])
    status = json.loads(harness.store.channel_path.read_text(encoding="utf-8"))
    status["state"] = "disabled_by_policy"
    harness.store.channel_path.write_text(json.dumps(status), encoding="utf-8")
    harness.set_state(
        _tracker_state(last_turn_result="success", last_turn_source="surface_inference")
    )

    state = harness.cycle(at=0.0)

    assert state.last_turn.result == "success"
    assert state.last_turn.source == "surface_inference"
    assert state.turn.phase == "ready"
    assert state.work == "unknown"
    assert state.settled is False
    assert state.observation_channels is not None
    assert state.observation_channels[0].state == "disabled_by_policy"


def test_public_payload_is_additive_and_secret_free(tmp_path: Path) -> None:
    harness = _Harness(tmp_path)
    harness.append(
        "UserPromptSubmit",
        prompt_id="p1",
        prompt="SECRET_PROMPT_TEXT",
    )
    harness.append(
        "Stop",
        prompt_id="p1",
        background_tasks=[],
        last_assistant_message="SECRET_ASSISTANT_TEXT",
    )
    status = json.loads(harness.store.channel_path.read_text(encoding="utf-8"))
    status["token"] = "SECRET_TOKEN_VALUE"
    status["detail"] = "SECRET_STATUS_DETAIL"
    harness.store.channel_path.write_text(json.dumps(status), encoding="utf-8")

    state = harness.cycle(at=0.0)
    payload = state.model_dump(mode="json")
    serialized = json.dumps(payload)

    assert payload["observation_channels"] is not None
    channel_payload = payload["observation_channels"][0]
    assert channel_payload["channel"] == "hook"
    assert channel_payload["provider"] == "claude"
    assert channel_payload["state"] == "active"
    assert channel_payload["detail"] is None
    assert channel_payload["generation"] == 1
    assert channel_payload["last_event_name"] == "Stop"
    assert channel_payload["last_sequence"] == 2
    assert channel_payload["counters"]["events_seen"] == 3
    assert channel_payload["conflict_reasons"] == []
    assert payload["work"] == "clear"
    assert payload["settled"] is True
    assert payload["diagnostics"]["hook_channel_state"] == "active"
    assert payload["diagnostics"]["hook_counters"]["events_seen"] == 3
    for secret in (
        "SECRET_PROMPT_TEXT",
        "SECRET_ASSISTANT_TEXT",
        "SECRET_TOKEN_VALUE",
        "SECRET_STATUS_DETAIL",
    ):
        assert secret not in serialized


def test_tracker_attaches_channel_lazily_from_session_root(tmp_path: Path) -> None:
    tracker = LiveSessionTracker(
        identity=_identity(),
        recent_transition_limit=8,
        stability_threshold_seconds=1.0,
        completion_stability_seconds=1.0,
        unknown_to_stalled_timeout_seconds=30.0,
    )
    assert tracker.hook_channel_state is None
    store = HookObservationStore(tmp_path, generation=1)
    store.append_event({"hook_event_name": "UserPromptSubmit", "prompt_id": "p1"})

    assert tracker.ensure_hook_channel_from_session_root(str(tmp_path)) is True
    tracker.m_tracker_session = _StaticTrackerSession(state=_tracker_state())
    state = tracker.record_cycle(
        identity=_identity(),
        observed_at_utc="2026-10-19T13:00:00+00:00",
        monotonic_ts=0.0,
        transport_state="tmux_up",
        process_state="tui_up",
        parse_status="parsed",
        probe_snapshot=None,
        probe_error=None,
        parse_error=None,
        parsed_surface=_surface(),
    )

    assert state.turn.phase == "active"
    assert state.observation_channels is not None
    assert tracker.hook_channel_state == "active"


def test_channel_absent_payload_omits_observation_channels(tmp_path: Path) -> None:
    tracker = LiveSessionTracker(
        identity=_identity(),
        recent_transition_limit=8,
        stability_threshold_seconds=1.0,
        completion_stability_seconds=1.0,
        unknown_to_stalled_timeout_seconds=30.0,
    )
    state = tracker.record_cycle(
        identity=_identity(),
        observed_at_utc="2026-10-19T13:00:00+00:00",
        monotonic_ts=0.0,
        transport_state="tmux_up",
        process_state="tui_up",
        parse_status="parsed",
        probe_snapshot=None,
        probe_error=None,
        parse_error=None,
        parsed_surface=_surface(),
    )

    payload = state.model_dump(mode="json")
    assert payload["observation_channels"] is None
    assert state.model_dump(mode="json", exclude_none=True).get("observation_channels") is None
    assert payload["work"] == "unknown"
    assert payload["settled"] is False
    assert payload["diagnostics"]["hook_channel_state"] is None
    assert payload["diagnostics"]["hook_conflict_reasons"] == []
