from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from houmao.server.tracking_debug import TrackingDebugSink
from houmao.server.models import (
    HoumaoErrorDetail,
    HoumaoParsedSurface,
    HoumaoProbeSnapshot,
    HoumaoTrackedSessionIdentity,
    HoumaoTerminalStateResponse,
)
from houmao.server.tui import OfficialTuiParserAdapter
from houmao.server.tui.tracking import LiveSessionTracker

_CODEX_READY_RAW_SNAPSHOT = "› \n\n  ? for shortcuts            100% context left\n"
_CODEX_ACTIVE_RAW_SNAPSHOT = "› Explain the failure.\n\n• Working (0s • esc to interrupt)\n"
_CODEX_OPERATOR_PROMPT_RAW_SNAPSHOT = "Would you like to run the following command?\n› \n"
_UNSET_OUTPUT_TEXT = object()


def _identity(*, observed_tool_version: str | None = None) -> HoumaoTrackedSessionIdentity:
    return HoumaoTrackedSessionIdentity(
        tracked_session_id="cao-gpu",
        session_name="cao-gpu",
        tool="codex",
        observed_tool_version=observed_tool_version,
        tmux_session_name="AGENTSYS-gpu",
        terminal_aliases=["abcd1234"],
    )


def _ready_surface() -> HoumaoParsedSurface:
    return _ready_surface_with_projection("ready")


def _ready_surface_with_projection(text: str) -> HoumaoParsedSurface:
    return HoumaoParsedSurface(
        parser_family="codex_shadow",
        parser_preset_id="codex",
        parser_preset_version="1.0.0",
        availability="supported",
        business_state="idle",
        input_mode="freeform",
        ui_context="normal_prompt",
        normalized_projection_text=text,
        dialog_text=text,
        dialog_head=text,
        dialog_tail=text,
        anomaly_codes=[],
        baseline_invalidated=False,
        operator_blocked_excerpt=None,
    )


def _processing_surface() -> HoumaoParsedSurface:
    return HoumaoParsedSurface(
        parser_family="codex_shadow",
        parser_preset_id="codex",
        parser_preset_version="1.0.0",
        availability="supported",
        business_state="working",
        input_mode="closed",
        ui_context="normal_prompt",
        normalized_projection_text="processing",
        dialog_text="processing",
        dialog_head="processing",
        dialog_tail="processing",
        anomaly_codes=[],
        baseline_invalidated=False,
        operator_blocked_excerpt=None,
    )


def _arm_anchor(tracker: LiveSessionTracker, *, at: float, observed_at_utc: str) -> None:
    tracker.note_prompt_submission(
        message="Explain the failure.",
        observed_at_utc=observed_at_utc,
        monotonic_ts=at,
    )


def _output_text_for_surface(parsed_surface: HoumaoParsedSurface | None) -> str | None:
    """Return a test-only raw tmux snapshot aligned with one parsed surface."""

    if parsed_surface is None:
        return None
    if parsed_surface.availability != "supported":
        return ""
    if parsed_surface.business_state == "working":
        return _CODEX_ACTIVE_RAW_SNAPSHOT
    if parsed_surface.input_mode == "modal" or parsed_surface.business_state == "awaiting_operator":
        return _CODEX_OPERATOR_PROMPT_RAW_SNAPSHOT
    return _CODEX_READY_RAW_SNAPSHOT


def _record_cycle(
    tracker: LiveSessionTracker,
    *,
    observed_at_utc: str,
    monotonic_ts: float,
    transport_state: str,
    process_state: str,
    parse_status: str,
    probe_snapshot: HoumaoProbeSnapshot | None,
    probe_error: HoumaoErrorDetail | None,
    parse_error: HoumaoErrorDetail | None,
    parsed_surface: HoumaoParsedSurface | None,
    output_text: str | None | object = _UNSET_OUTPUT_TEXT,
) -> HoumaoTerminalStateResponse:
    """Record one cycle with raw tracker input by default."""

    resolved_output_text = (
        _output_text_for_surface(parsed_surface)
        if output_text is _UNSET_OUTPUT_TEXT
        else cast(str | None, output_text)
    )
    return tracker.record_cycle(
        identity=_identity(),
        observed_at_utc=observed_at_utc,
        monotonic_ts=monotonic_ts,
        transport_state=transport_state,
        process_state=process_state,
        parse_status=parse_status,
        probe_snapshot=probe_snapshot,
        probe_error=probe_error,
        parse_error=parse_error,
        parsed_surface=parsed_surface,
        output_text=resolved_output_text,
    )


def test_official_parser_adapter_parses_direct_tmux_fixture() -> None:
    fixture_path = (
        Path(__file__).resolve().parents[2]
        / "fixtures"
        / "shadow_parser"
        / "codex"
        / "waiting_menu.txt"
    )
    output_text = fixture_path.read_text(encoding="utf-8")
    adapter = OfficialTuiParserAdapter()

    baseline_pos = adapter.capture_baseline(tool="codex", output_text=output_text)
    result = adapter.parse(tool="codex", output_text=output_text, baseline_pos=baseline_pos)

    assert result.parse_error is None
    assert result.parsed_surface is not None
    assert result.parsed_surface.parser_family == "codex_shadow"
    assert result.parsed_surface.availability in {"supported", "unknown"}
    assert result.parsed_surface.business_state in {
        "idle",
        "working",
        "awaiting_operator",
        "unknown",
    }
    assert result.parsed_surface.dialog_text


def test_live_session_tracker_accumulates_stability_and_bounds_recent_transitions() -> None:
    tracker = LiveSessionTracker(
        identity=_identity(),
        recent_transition_limit=2,
        stability_threshold_seconds=1.0,
        completion_stability_seconds=1.0,
        unknown_to_stalled_timeout_seconds=30.0,
    )
    probe_snapshot = HoumaoProbeSnapshot(
        observed_at_utc="2026-03-19T10:00:00+00:00",
        pane_id="%9",
        pane_pid=4321,
        matched_process_names=["codex"],
    )

    first = _record_cycle(
        tracker,
        observed_at_utc="2026-03-19T10:00:00+00:00",
        monotonic_ts=10.0,
        transport_state="tmux_up",
        process_state="tui_up",
        parse_status="parsed",
        probe_snapshot=probe_snapshot,
        probe_error=None,
        parse_error=None,
        parsed_surface=_ready_surface(),
    )
    second = _record_cycle(
        tracker,
        observed_at_utc="2026-03-19T10:00:03+00:00",
        monotonic_ts=13.0,
        transport_state="tmux_up",
        process_state="tui_up",
        parse_status="parsed",
        probe_snapshot=probe_snapshot,
        probe_error=None,
        parse_error=None,
        parsed_surface=_processing_surface(),
    )
    third = _record_cycle(
        tracker,
        observed_at_utc="2026-03-19T10:00:04+00:00",
        monotonic_ts=14.0,
        transport_state="tmux_up",
        process_state="tui_down",
        parse_status="skipped_tui_down",
        probe_snapshot=probe_snapshot,
        probe_error=None,
        parse_error=None,
        parsed_surface=None,
    )
    fourth = _record_cycle(
        tracker,
        observed_at_utc="2026-03-19T10:00:06+00:00",
        monotonic_ts=16.0,
        transport_state="tmux_up",
        process_state="tui_down",
        parse_status="skipped_tui_down",
        probe_snapshot=probe_snapshot,
        probe_error=None,
        parse_error=None,
        parsed_surface=None,
    )

    assert first.stability.stable is False
    assert first.lifecycle_timing.completion_stability_seconds == 1.0
    assert first.lifecycle_timing.unknown_to_stalled_timeout_seconds == 30.0
    assert first.lifecycle_authority.completion_authority == "unanchored_background"
    assert first.lifecycle_authority.turn_anchor_state == "absent"
    assert second.operator_state.status == "processing"
    assert third.operator_state.status == "tui_down"
    assert fourth.stability.stable is True
    assert fourth.stability.stable_for_seconds == 2.0
    assert len(fourth.recent_transitions) == 2


def test_live_session_tracker_exposes_parse_failure_explicitly() -> None:
    tracker = LiveSessionTracker(
        identity=_identity(),
        recent_transition_limit=3,
        stability_threshold_seconds=1.0,
        completion_stability_seconds=1.0,
        unknown_to_stalled_timeout_seconds=30.0,
    )

    state = _record_cycle(
        tracker,
        observed_at_utc="2026-03-19T10:00:00+00:00",
        monotonic_ts=10.0,
        transport_state="tmux_up",
        process_state="tui_up",
        parse_status="parse_error",
        probe_snapshot=None,
        probe_error=None,
        parse_error=HoumaoErrorDetail(kind="parse_error", message="bad snapshot"),
        parsed_surface=None,
        output_text=_CODEX_READY_RAW_SNAPSHOT,
    )

    assert state.parse_status == "parse_error"
    assert state.parsed_surface is None
    assert state.parse_error is not None
    assert state.operator_state.status == "error"
    assert state.surface.ready_posture == "yes"


def test_live_session_tracker_reports_candidate_complete_elapsed_seconds() -> None:
    tracker = LiveSessionTracker(
        identity=_identity(),
        recent_transition_limit=3,
        stability_threshold_seconds=1.0,
        completion_stability_seconds=1.0,
        unknown_to_stalled_timeout_seconds=30.0,
    )
    probe_snapshot = HoumaoProbeSnapshot(
        observed_at_utc="2026-03-19T10:00:00+00:00",
        pane_id="%9",
        pane_pid=4321,
        matched_process_names=["codex"],
    )

    _record_cycle(
        tracker,
        observed_at_utc="2026-03-19T10:00:00+00:00",
        monotonic_ts=10.0,
        transport_state="tmux_up",
        process_state="tui_up",
        parse_status="parsed",
        probe_snapshot=probe_snapshot,
        probe_error=None,
        parse_error=None,
        parsed_surface=_ready_surface(),
    )
    _arm_anchor(tracker, at=10.2, observed_at_utc="2026-03-19T10:00:00+00:00")
    _record_cycle(
        tracker,
        observed_at_utc="2026-03-19T10:00:01+00:00",
        monotonic_ts=11.0,
        transport_state="tmux_up",
        process_state="tui_up",
        parse_status="parsed",
        probe_snapshot=probe_snapshot,
        probe_error=None,
        parse_error=None,
        parsed_surface=_processing_surface(),
    )

    candidate = _record_cycle(
        tracker,
        observed_at_utc="2026-03-19T10:00:01+00:00",
        monotonic_ts=11.4,
        transport_state="tmux_up",
        process_state="tui_up",
        parse_status="parsed",
        probe_snapshot=probe_snapshot,
        probe_error=None,
        parse_error=None,
        parsed_surface=_ready_surface(),
    )

    assert candidate.operator_state.completion_state == "candidate_complete"
    assert candidate.operator_state.status == "ready"
    assert candidate.lifecycle_timing.completion_candidate_elapsed_seconds == 0.0
    assert candidate.lifecycle_authority.completion_authority == "turn_anchored"
    assert candidate.lifecycle_authority.turn_anchor_state == "active"

    completed = _record_cycle(
        tracker,
        observed_at_utc="2026-03-19T10:00:03+00:00",
        monotonic_ts=13.0,
        transport_state="tmux_up",
        process_state="tui_up",
        parse_status="parsed",
        probe_snapshot=probe_snapshot,
        probe_error=None,
        parse_error=None,
        parsed_surface=_ready_surface(),
    )

    assert completed.operator_state.completion_state == "completed"
    assert completed.lifecycle_timing.completion_candidate_elapsed_seconds == pytest.approx(1.6)
    assert completed.lifecycle_authority.completion_authority == "turn_anchored"


def test_live_session_tracker_detects_fast_ready_to_ready_completion_cycle() -> None:
    tracker = LiveSessionTracker(
        identity=_identity(),
        recent_transition_limit=4,
        stability_threshold_seconds=1.0,
        completion_stability_seconds=1.0,
        unknown_to_stalled_timeout_seconds=30.0,
    )
    probe_snapshot = HoumaoProbeSnapshot(
        observed_at_utc="2026-03-19T10:00:00+00:00",
        pane_id="%9",
        pane_pid=4321,
        matched_process_names=["codex"],
    )

    _record_cycle(
        tracker,
        observed_at_utc="2026-03-19T10:00:00+00:00",
        monotonic_ts=10.0,
        transport_state="tmux_up",
        process_state="tui_up",
        parse_status="parsed",
        probe_snapshot=probe_snapshot,
        probe_error=None,
        parse_error=None,
        parsed_surface=_ready_surface_with_projection("prompt ready"),
    )
    _record_cycle(
        tracker,
        observed_at_utc="2026-03-19T10:00:00+00:00",
        monotonic_ts=10.2,
        transport_state="tmux_up",
        process_state="tui_up",
        parse_status="parsed",
        probe_snapshot=probe_snapshot,
        probe_error=None,
        parse_error=None,
        parsed_surface=_ready_surface_with_projection("prompt ready"),
    )
    _arm_anchor(tracker, at=10.25, observed_at_utc="2026-03-19T10:00:00+00:00")

    candidate = _record_cycle(
        tracker,
        observed_at_utc="2026-03-19T10:00:00+00:00",
        monotonic_ts=10.3,
        transport_state="tmux_up",
        process_state="tui_up",
        parse_status="parsed",
        probe_snapshot=probe_snapshot,
        probe_error=None,
        parse_error=None,
        parsed_surface=_ready_surface_with_projection("assistant answered and prompt ready"),
    )

    assert candidate.operator_state.status == "ready"
    assert candidate.operator_state.completion_state == "candidate_complete"
    assert candidate.operator_state.projection_changed is True
    assert candidate.lifecycle_timing.completion_candidate_elapsed_seconds == 0.0
    assert candidate.lifecycle_authority.completion_authority == "turn_anchored"

    completed = _record_cycle(
        tracker,
        observed_at_utc="2026-03-19T10:00:02+00:00",
        monotonic_ts=12.0,
        transport_state="tmux_up",
        process_state="tui_up",
        parse_status="parsed",
        probe_snapshot=probe_snapshot,
        probe_error=None,
        parse_error=None,
        parsed_surface=_ready_surface_with_projection("assistant answered and prompt ready"),
    )

    assert completed.operator_state.status == "completed"
    assert completed.operator_state.completion_state == "completed"
    assert completed.lifecycle_timing.completion_candidate_elapsed_seconds == pytest.approx(1.7)
    assert completed.lifecycle_authority.turn_anchor_state == "active"


def test_live_session_tracker_ignores_startup_ready_surface_churn() -> None:
    tracker = LiveSessionTracker(
        identity=_identity(),
        recent_transition_limit=4,
        stability_threshold_seconds=1.0,
        completion_stability_seconds=1.0,
        unknown_to_stalled_timeout_seconds=30.0,
    )
    probe_snapshot = HoumaoProbeSnapshot(
        observed_at_utc="2026-03-19T10:00:00+00:00",
        pane_id="%9",
        pane_pid=4321,
        matched_process_names=["codex"],
    )

    first = _record_cycle(
        tracker,
        observed_at_utc="2026-03-19T10:00:00+00:00",
        monotonic_ts=10.0,
        transport_state="tmux_up",
        process_state="tui_up",
        parse_status="parsed",
        probe_snapshot=probe_snapshot,
        probe_error=None,
        parse_error=None,
        parsed_surface=_ready_surface_with_projection("startup welcome"),
    )
    second = _record_cycle(
        tracker,
        observed_at_utc="2026-03-19T10:00:00+00:00",
        monotonic_ts=10.3,
        transport_state="tmux_up",
        process_state="tui_up",
        parse_status="parsed",
        probe_snapshot=probe_snapshot,
        probe_error=None,
        parse_error=None,
        parsed_surface=_ready_surface_with_projection("steady prompt"),
    )
    third = _record_cycle(
        tracker,
        observed_at_utc="2026-03-19T10:00:01+00:00",
        monotonic_ts=11.0,
        transport_state="tmux_up",
        process_state="tui_up",
        parse_status="parsed",
        probe_snapshot=probe_snapshot,
        probe_error=None,
        parse_error=None,
        parsed_surface=_ready_surface_with_projection("steady prompt"),
    )

    assert first.operator_state.completion_state == "inactive"
    assert second.operator_state.completion_state == "inactive"
    assert second.operator_state.projection_changed is False
    assert third.operator_state.completion_state == "inactive"
    assert third.operator_state.status == "ready"
    assert third.lifecycle_authority.turn_anchor_state == "absent"


def test_live_session_tracker_promotes_continuous_unknown_to_stalled() -> None:
    tracker = LiveSessionTracker(
        identity=_identity(),
        recent_transition_limit=3,
        stability_threshold_seconds=1.0,
        completion_stability_seconds=1.0,
        unknown_to_stalled_timeout_seconds=5.0,
    )
    probe_snapshot = HoumaoProbeSnapshot(
        observed_at_utc="2026-03-19T10:00:00+00:00",
        pane_id="%9",
        pane_pid=4321,
        matched_process_names=["codex"],
    )
    unknown_surface = HoumaoParsedSurface(
        parser_family="codex_shadow",
        parser_preset_id="codex",
        parser_preset_version="1.0.0",
        availability="unknown",
        business_state="unknown",
        input_mode="unknown",
        ui_context="unknown",
        normalized_projection_text="unknown",
        dialog_text="unknown",
        dialog_head="unknown",
        dialog_tail="unknown",
        anomaly_codes=[],
        baseline_invalidated=False,
        operator_blocked_excerpt=None,
    )

    unknown = _record_cycle(
        tracker,
        observed_at_utc="2026-03-19T10:00:00+00:00",
        monotonic_ts=10.0,
        transport_state="tmux_up",
        process_state="tui_up",
        parse_status="parsed",
        probe_snapshot=probe_snapshot,
        probe_error=None,
        parse_error=None,
        parsed_surface=unknown_surface,
    )
    stalled = _record_cycle(
        tracker,
        observed_at_utc="2026-03-19T10:00:06+00:00",
        monotonic_ts=16.0,
        transport_state="tmux_up",
        process_state="tui_up",
        parse_status="parsed",
        probe_snapshot=probe_snapshot,
        probe_error=None,
        parse_error=None,
        parsed_surface=unknown_surface,
    )

    assert unknown.operator_state.readiness_state == "unknown"
    assert unknown.lifecycle_timing.readiness_unknown_elapsed_seconds == 0.0
    assert stalled.operator_state.readiness_state == "stalled"
    assert stalled.operator_state.completion_state == "stalled"
    assert stalled.lifecycle_timing.readiness_unknown_elapsed_seconds == 6.0
    assert stalled.lifecycle_timing.completion_unknown_elapsed_seconds == 6.0


def test_live_session_tracker_note_prompt_submission_arms_turn_anchor() -> None:
    tracker = LiveSessionTracker(
        identity=_identity(),
        recent_transition_limit=3,
        stability_threshold_seconds=1.0,
        completion_stability_seconds=1.0,
        unknown_to_stalled_timeout_seconds=30.0,
    )

    _record_cycle(
        tracker,
        observed_at_utc="2026-03-19T10:00:00+00:00",
        monotonic_ts=10.0,
        transport_state="tmux_up",
        process_state="tui_up",
        parse_status="parsed",
        probe_snapshot=None,
        probe_error=None,
        parse_error=None,
        parsed_surface=_ready_surface(),
    )

    state = tracker.note_prompt_submission(
        message="Explain the failure.",
        observed_at_utc="2026-03-19T10:00:01+00:00",
        monotonic_ts=11.0,
    )

    assert state.lifecycle_authority.completion_authority == "turn_anchored"
    assert state.lifecycle_authority.turn_anchor_state == "active"
    assert state.lifecycle_authority.completion_monitoring_armed is True


def test_live_session_tracker_rebuilds_when_observed_tool_version_changes() -> None:
    tracker = LiveSessionTracker(
        identity=_identity(observed_tool_version=None),
        recent_transition_limit=3,
        stability_threshold_seconds=1.0,
        completion_stability_seconds=1.0,
        unknown_to_stalled_timeout_seconds=30.0,
    )

    fallback_session = tracker.m_tracker_session
    fallback_state = _record_cycle(
        tracker,
        observed_at_utc="2026-03-19T10:00:00+00:00",
        monotonic_ts=10.0,
        transport_state="tmux_up",
        process_state="tui_up",
        parse_status="parsed",
        probe_snapshot=None,
        probe_error=None,
        parse_error=None,
        parsed_surface=_ready_surface(),
    )

    tracker.set_identity(_identity(observed_tool_version="0.116.4 (Codex)"))
    versioned_session = tracker.m_tracker_session
    tracker.set_identity(_identity(observed_tool_version="0.116.5 (Codex)"))
    rebuilt_same_family_session = tracker.m_tracker_session
    tracker.set_identity(_identity(observed_tool_version="0.116.5 (Codex)"))

    assert fallback_session.detector_version == "fallback"
    assert fallback_state.surface.ready_posture == "yes"
    assert versioned_session is not fallback_session
    assert versioned_session.detector_version == "0.116.x"
    assert rebuilt_same_family_session is not versioned_session
    assert tracker.m_tracker_session is rebuilt_same_family_session


def test_live_session_tracker_uses_shared_raw_snapshot_surface_inference() -> None:
    tracker = LiveSessionTracker(
        identity=_identity(),
        recent_transition_limit=4,
        stability_threshold_seconds=1.0,
        completion_stability_seconds=1.0,
        unknown_to_stalled_timeout_seconds=30.0,
    )

    _record_cycle(
        tracker,
        observed_at_utc="2026-03-19T10:00:00+00:00",
        monotonic_ts=10.0,
        transport_state="tmux_up",
        process_state="tui_up",
        parse_status="parsed",
        probe_snapshot=None,
        probe_error=None,
        parse_error=None,
        parsed_surface=_ready_surface_with_projection("prompt ready"),
    )
    active = _record_cycle(
        tracker,
        observed_at_utc="2026-03-19T10:00:01+00:00",
        monotonic_ts=11.0,
        transport_state="tmux_up",
        process_state="tui_up",
        parse_status="parsed",
        probe_snapshot=None,
        probe_error=None,
        parse_error=None,
        parsed_surface=_processing_surface(),
    )
    candidate = _record_cycle(
        tracker,
        observed_at_utc="2026-03-19T10:00:02+00:00",
        monotonic_ts=12.0,
        transport_state="tmux_up",
        process_state="tui_up",
        parse_status="parsed",
        probe_snapshot=None,
        probe_error=None,
        parse_error=None,
        parsed_surface=_ready_surface_with_projection("assistant answered and prompt ready"),
    )
    settled = _record_cycle(
        tracker,
        observed_at_utc="2026-03-19T10:00:03+00:00",
        monotonic_ts=13.0,
        transport_state="tmux_up",
        process_state="tui_up",
        parse_status="parsed",
        probe_snapshot=None,
        probe_error=None,
        parse_error=None,
        parsed_surface=_ready_surface_with_projection("assistant answered and prompt ready"),
    )

    assert active.turn.phase == "active"
    assert active.lifecycle_authority.completion_authority == "unanchored_background"
    assert active.lifecycle_authority.turn_anchor_state == "absent"
    assert candidate.last_turn.result == "none"
    assert settled.last_turn.result == "success"
    assert settled.last_turn.source == "surface_inference"
    assert settled.lifecycle_authority.completion_authority == "unanchored_background"
    assert settled.lifecycle_authority.turn_anchor_state == "absent"


def test_live_session_tracker_does_not_arm_tracker_authority_from_parser_only_churn() -> None:
    tracker = LiveSessionTracker(
        identity=_identity(),
        recent_transition_limit=4,
        stability_threshold_seconds=1.0,
        completion_stability_seconds=1.0,
        unknown_to_stalled_timeout_seconds=30.0,
    )

    _record_cycle(
        tracker,
        observed_at_utc="2026-03-19T10:00:00+00:00",
        monotonic_ts=10.0,
        transport_state="tmux_up",
        process_state="tui_up",
        parse_status="parsed",
        probe_snapshot=None,
        probe_error=None,
        parse_error=None,
        parsed_surface=_ready_surface_with_projection("prompt ready"),
    )
    stable_ready = _record_cycle(
        tracker,
        observed_at_utc="2026-03-19T10:00:02+00:00",
        monotonic_ts=12.0,
        transport_state="tmux_up",
        process_state="tui_up",
        parse_status="parsed",
        probe_snapshot=None,
        probe_error=None,
        parse_error=None,
        parsed_surface=_ready_surface_with_projection("prompt ready"),
    )
    parser_only = _record_cycle(
        tracker,
        observed_at_utc="2026-03-19T10:00:02+00:00",
        monotonic_ts=12.2,
        transport_state="tmux_up",
        process_state="tui_up",
        parse_status="parsed",
        probe_snapshot=None,
        probe_error=None,
        parse_error=None,
        parsed_surface=_ready_surface_with_projection(
            "prompt ready\n"
            "Reply with the single word READY and stop.\n"
            "READY\n"
            "Tip: Use Plan Mode before making changes."
        ),
    )

    assert stable_ready.stability.stable is True
    assert parser_only.operator_state.completion_state == "inactive"
    assert parser_only.last_turn.result == "none"
    assert parser_only.last_turn.source == "none"
    assert parser_only.lifecycle_authority.completion_authority == "unanchored_background"
    assert parser_only.lifecycle_authority.turn_anchor_state == "absent"


def test_live_session_tracker_tracking_debug_emits_expected_streams(tmp_path: Path) -> None:
    tracker = LiveSessionTracker(
        identity=_identity(),
        recent_transition_limit=4,
        stability_threshold_seconds=1.0,
        completion_stability_seconds=1.0,
        unknown_to_stalled_timeout_seconds=30.0,
        tracking_debug_sink=TrackingDebugSink(root=tmp_path / "trace"),
    )

    _record_cycle(
        tracker,
        observed_at_utc="2026-03-19T10:00:00+00:00",
        monotonic_ts=10.0,
        transport_state="tmux_up",
        process_state="tui_up",
        parse_status="parsed",
        probe_snapshot=None,
        probe_error=None,
        parse_error=None,
        parsed_surface=_ready_surface(),
    )
    tracker.note_prompt_submission(
        message="Explain the failure.",
        observed_at_utc="2026-03-19T10:00:00+00:00",
        monotonic_ts=10.1,
    )
    _record_cycle(
        tracker,
        observed_at_utc="2026-03-19T10:00:01+00:00",
        monotonic_ts=11.0,
        transport_state="tmux_up",
        process_state="tui_up",
        parse_status="parsed",
        probe_snapshot=None,
        probe_error=None,
        parse_error=None,
        parsed_surface=_processing_surface(),
    )
    _record_cycle(
        tracker,
        observed_at_utc="2026-03-19T10:00:02+00:00",
        monotonic_ts=12.0,
        transport_state="tmux_up",
        process_state="tui_up",
        parse_status="parsed",
        probe_snapshot=None,
        probe_error=None,
        parse_error=None,
        parsed_surface=_ready_surface_with_projection("assistant answered and prompt ready"),
    )

    events_dir = tmp_path / "trace" / "events"
    assert (events_dir / "tracker-cycle.ndjson").is_file()
    assert (events_dir / "tracker-reduction.ndjson").is_file()
    assert (events_dir / "tracker-operator-state.ndjson").is_file()
    assert (events_dir / "tracker-stability.ndjson").is_file()
    assert (events_dir / "tracker-transition.ndjson").is_file()
    assert (events_dir / "tracker-anchor.ndjson").is_file()


def test_live_session_tracker_expires_anchor_after_completed_cycle() -> None:
    tracker = LiveSessionTracker(
        identity=_identity(),
        recent_transition_limit=4,
        stability_threshold_seconds=1.0,
        completion_stability_seconds=1.0,
        unknown_to_stalled_timeout_seconds=30.0,
    )

    _record_cycle(
        tracker,
        observed_at_utc="2026-03-19T10:00:00+00:00",
        monotonic_ts=10.0,
        transport_state="tmux_up",
        process_state="tui_up",
        parse_status="parsed",
        probe_snapshot=None,
        probe_error=None,
        parse_error=None,
        parsed_surface=_ready_surface(),
    )
    _arm_anchor(tracker, at=10.1, observed_at_utc="2026-03-19T10:00:00+00:00")
    _record_cycle(
        tracker,
        observed_at_utc="2026-03-19T10:00:01+00:00",
        monotonic_ts=11.0,
        transport_state="tmux_up",
        process_state="tui_up",
        parse_status="parsed",
        probe_snapshot=None,
        probe_error=None,
        parse_error=None,
        parsed_surface=_processing_surface(),
    )
    _record_cycle(
        tracker,
        observed_at_utc="2026-03-19T10:00:01+00:00",
        monotonic_ts=11.4,
        transport_state="tmux_up",
        process_state="tui_up",
        parse_status="parsed",
        probe_snapshot=None,
        probe_error=None,
        parse_error=None,
        parsed_surface=_ready_surface(),
    )
    completed = _record_cycle(
        tracker,
        observed_at_utc="2026-03-19T10:00:03+00:00",
        monotonic_ts=13.0,
        transport_state="tmux_up",
        process_state="tui_up",
        parse_status="parsed",
        probe_snapshot=None,
        probe_error=None,
        parse_error=None,
        parsed_surface=_ready_surface(),
    )
    next_cycle = _record_cycle(
        tracker,
        observed_at_utc="2026-03-19T10:00:04+00:00",
        monotonic_ts=14.0,
        transport_state="tmux_up",
        process_state="tui_up",
        parse_status="parsed",
        probe_snapshot=None,
        probe_error=None,
        parse_error=None,
        parsed_surface=_ready_surface(),
    )
    post_expiry_cycle = _record_cycle(
        tracker,
        observed_at_utc="2026-03-19T10:00:05+00:00",
        monotonic_ts=15.0,
        transport_state="tmux_up",
        process_state="tui_up",
        parse_status="parsed",
        probe_snapshot=None,
        probe_error=None,
        parse_error=None,
        parsed_surface=_ready_surface(),
    )

    assert completed.operator_state.completion_state == "completed"
    assert completed.lifecycle_authority.completion_authority == "turn_anchored"
    assert next_cycle.operator_state.completion_state == "completed"
    assert next_cycle.last_turn.result == "success"
    assert post_expiry_cycle.operator_state.completion_state == "inactive"
    assert post_expiry_cycle.lifecycle_authority.completion_authority == "unanchored_background"
    assert post_expiry_cycle.lifecycle_authority.turn_anchor_state == "absent"
