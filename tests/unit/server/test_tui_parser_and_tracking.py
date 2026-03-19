from __future__ import annotations

from pathlib import Path

from houmao.server.models import (
    HoumaoErrorDetail,
    HoumaoParsedSurface,
    HoumaoProbeSnapshot,
    HoumaoTrackedSessionIdentity,
)
from houmao.server.tui import OfficialTuiParserAdapter
from houmao.server.tui.tracking import LiveSessionTracker


def _identity() -> HoumaoTrackedSessionIdentity:
    return HoumaoTrackedSessionIdentity(
        tracked_session_id="cao-gpu",
        session_name="cao-gpu",
        tool="codex",
        tmux_session_name="AGENTSYS-gpu",
        terminal_aliases=("abcd1234",),
    )


def _ready_surface() -> HoumaoParsedSurface:
    return HoumaoParsedSurface(
        parser_family="codex_shadow",
        parser_preset_id="codex",
        parser_preset_version="1.0.0",
        availability="supported",
        business_state="idle",
        input_mode="freeform",
        ui_context="normal_prompt",
        normalized_projection_text="ready",
        dialog_text="ready",
        dialog_head="ready",
        dialog_tail="ready",
        anomaly_codes=(),
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
        anomaly_codes=(),
        baseline_invalidated=False,
        operator_blocked_excerpt=None,
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
    )
    probe_snapshot = HoumaoProbeSnapshot(
        observed_at_utc="2026-03-19T10:00:00+00:00",
        pane_id="%9",
        pane_pid=4321,
        matched_process_names=("codex",),
    )

    first = tracker.record_cycle(
        identity=_identity(),
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
    second = tracker.record_cycle(
        identity=_identity(),
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
    third = tracker.record_cycle(
        identity=_identity(),
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
    fourth = tracker.record_cycle(
        identity=_identity(),
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
    )

    state = tracker.record_cycle(
        identity=_identity(),
        observed_at_utc="2026-03-19T10:00:00+00:00",
        monotonic_ts=10.0,
        transport_state="tmux_up",
        process_state="tui_up",
        parse_status="parse_error",
        probe_snapshot=None,
        probe_error=None,
        parse_error=HoumaoErrorDetail(kind="parse_error", message="bad snapshot"),
        parsed_surface=None,
    )

    assert state.parse_status == "parse_error"
    assert state.parsed_surface is None
    assert state.parse_error is not None
    assert state.operator_state.status == "error"
