from __future__ import annotations

from pathlib import Path

from reactivex.testing import TestScheduler

from houmao.shared_tui_tracking import TrackerConfig, TuiTrackerSession, app_id_from_tool
from houmao.shared_tui_tracking.apps.kimi_code.profile import (
    KimiCodeSignalDetector,
    KimiCodeSignalDetectorV2_1_X,
    analyze_kimi_surface,
    kimi_trust_modal_present,
)


_FIXTURE_ROOT = (
    Path(__file__).resolve().parents[2] / "fixtures" / "shared_tui_tracking" / "kimi_code"
)


def _fixture(name: str) -> str:
    """Return one recorded Kimi 2.1.1 visible-surface fixture."""

    return (_FIXTURE_ROOT / name).read_text(encoding="utf-8")


_KIMI_IDLE_READY = _fixture("idle_ready.txt")
_KIMI_EDITING_DRAFT = _fixture("editing_draft.txt")
_KIMI_BUSY_THINKING = _fixture("busy_thinking.txt")
_KIMI_BUSY_TOOL_MOON = _fixture("busy_tool_moon.txt")
_KIMI_APPROVAL = _fixture("approval_panel.txt")
_KIMI_PLAN_REVIEW = _fixture("plan_review.txt")
_KIMI_QUESTION_DIALOG = _fixture("question_dialog.txt")
_KIMI_TRUST_MODAL = _fixture("startup_trust_modal.txt")
_KIMI_QUEUE_PENDING = _fixture("queue_pending.txt")
_KIMI_INTERRUPT_RESUME = _fixture("interrupt_resume.txt")
_KIMI_SUBAGENT_RUNNING = _fixture("subagent_running.txt")


def _kimi_session(*, scheduler: TestScheduler) -> TuiTrackerSession:
    return TuiTrackerSession.from_config(
        app_id="kimi_code",
        observed_version="2.1.1",
        config=TrackerConfig(settle_seconds=1.0, stability_threshold_seconds=0.0),
        scheduler=scheduler,
    )


def test_app_id_from_tool_maps_kimi_to_kimi_code() -> None:
    assert app_id_from_tool(tool="kimi") == "kimi_code"


def test_kimi_detector_alias_points_at_maintained_profile() -> None:
    assert KimiCodeSignalDetector is KimiCodeSignalDetectorV2_1_X
    assert KimiCodeSignalDetectorV2_1_X.qualified_through_version == "2.1.1"


def test_kimi_idle_ready_fixture_reads_ready_and_accepting() -> None:
    scheduler = TestScheduler()
    session = _kimi_session(scheduler=scheduler)

    scheduler.advance_to(1.0)
    session.on_snapshot(_KIMI_IDLE_READY)
    state = session.current_state()

    assert state.detector_name == "kimi_code"
    assert state.detector_version == "2.1.x"
    assert state.turn_phase == "ready"
    assert state.surface_accepting_input == "yes"
    assert state.surface_editing_input == "no"
    assert state.surface_ready_posture == "yes"
    assert state.surface_pending_input == "no"


def test_kimi_editing_draft_marks_editing_without_active_turn() -> None:
    scheduler = TestScheduler()
    session = _kimi_session(scheduler=scheduler)

    scheduler.advance_to(1.0)
    session.on_snapshot(_KIMI_EDITING_DRAFT)
    state = session.current_state()

    assert state.turn_phase == "ready"
    assert state.surface_accepting_input == "yes"
    assert state.surface_editing_input == "yes"
    assert state.last_turn_result == "none"


def test_kimi_braille_thinking_phase_marks_turn_active() -> None:
    scheduler = TestScheduler()
    session = _kimi_session(scheduler=scheduler)

    scheduler.advance_to(1.0)
    session.on_snapshot(_KIMI_BUSY_THINKING)
    state = session.current_state()

    assert state.turn_phase == "active"
    assert state.surface_ready_posture == "no"
    assert "activity_2_1_label" in state.active_reasons


def test_kimi_composer_accepts_input_while_turn_is_active() -> None:
    detector = KimiCodeSignalDetectorV2_1_X()

    signals = detector.detect(output_text=_KIMI_BUSY_THINKING)

    assert signals.active_evidence is True
    assert signals.accepting_input == "yes"
    assert signals.ready_posture == "no"


def test_kimi_moon_spinner_tool_phase_marks_turn_active() -> None:
    detector = KimiCodeSignalDetectorV2_1_X()

    signals = detector.detect(output_text=_KIMI_BUSY_TOOL_MOON)

    assert signals.active_evidence is True
    assert "moon_spinner" in signals.active_reasons
    assert signals.accepting_input == "yes"
    assert signals.ready_posture == "no"


def test_kimi_approval_panel_reports_modal_blocked_active_turn() -> None:
    scheduler = TestScheduler()
    session = _kimi_session(scheduler=scheduler)

    scheduler.advance_to(1.0)
    session.on_snapshot(_KIMI_APPROVAL)
    state = session.current_state()
    analysis = analyze_kimi_surface(_KIMI_APPROVAL)

    assert analysis.approval_visible is True
    assert state.turn_phase == "active"
    assert "modal_blocked" in state.active_reasons
    assert "approval_panel" in state.active_reasons
    assert state.surface_accepting_input == "no"
    assert state.surface_editing_input == "no"
    assert state.surface_ready_posture == "no"
    assert state.surface_pending_input == "no"


def test_kimi_plan_review_reports_modal_blocked_active_turn() -> None:
    detector = KimiCodeSignalDetectorV2_1_X()

    signals = detector.detect(output_text=_KIMI_PLAN_REVIEW)

    assert signals.ambiguous_interactive_surface is True
    assert signals.active_evidence is True
    assert "modal_blocked" in signals.active_reasons
    assert signals.accepting_input == "no"
    assert signals.ready_posture == "no"


def test_kimi_question_dialog_reports_modal_blocked_active_turn() -> None:
    detector = KimiCodeSignalDetectorV2_1_X()

    signals = detector.detect(output_text=_KIMI_QUESTION_DIALOG)

    assert signals.ambiguous_interactive_surface is True
    assert signals.active_evidence is True
    assert "question_dialog" in signals.active_reasons
    assert "modal_blocked" in signals.active_reasons
    assert signals.accepting_input == "no"
    assert signals.editing_input == "no"
    assert signals.ready_posture == "no"
    assert signals.pending_input == "no"


def test_kimi_trust_modal_reports_startup_modal_blocked() -> None:
    detector = KimiCodeSignalDetectorV2_1_X()

    signals = detector.detect(output_text=_KIMI_TRUST_MODAL)

    assert kimi_trust_modal_present(_KIMI_TRUST_MODAL) is True
    assert signals.ambiguous_interactive_surface is True
    assert signals.active_evidence is True
    assert "trust_modal" in signals.active_reasons
    assert "modal_blocked" in signals.active_reasons
    assert signals.accepting_input == "no"
    assert signals.editing_input == "no"
    assert signals.ready_posture == "no"
    assert signals.pending_input == "no"


def test_kimi_queue_hint_marks_pending_input_and_active_turn() -> None:
    detector = KimiCodeSignalDetectorV2_1_X()

    signals = detector.detect(output_text=_KIMI_QUEUE_PENDING)
    analysis = analyze_kimi_surface(_KIMI_QUEUE_PENDING, activity_window_lines=4)

    assert analysis.queue_visible is True
    assert signals.active_evidence is True
    assert "queued_message" in signals.active_reasons
    assert signals.pending_input == "yes"
    assert signals.accepting_input == "yes"
    assert signals.ready_posture == "no"


def test_kimi_stale_interrupt_notice_does_not_outrank_resumed_activity() -> None:
    detector = KimiCodeSignalDetectorV2_1_X()

    signals = detector.detect(output_text=_KIMI_INTERRUPT_RESUME)

    assert signals.interrupted is False
    assert signals.active_evidence is True
    assert signals.ready_posture == "no"


def test_kimi_subagent_running_row_is_busy_evidence() -> None:
    detector = KimiCodeSignalDetectorV2_1_X()

    signals = detector.detect(output_text=_KIMI_SUBAGENT_RUNNING)

    assert signals.active_evidence is True
    assert signals.ready_posture == "no"


def test_kimi_pending_input_remains_binary_for_one_two_or_three_rows() -> None:
    detector = KimiCodeSignalDetectorV2_1_X()

    for count in (1, 2, 3):
        rows = "\n".join(f"  ❯ queued follow-up {index}" for index in range(1, count + 1))
        surface = (
            "🌑 · Tip: ctrl+s: steer mid-turn\n"
            f"{rows}\n"
            "  ↑ to edit · will send after current task\n"
            "╭────────────────────────╮\n"
            "│ >                      │\n"
            "╰────────────────────────╯\n"
            "auto  kimi-for-coding-highspeed thinking  context: 1.0%\n"
        )

        assert detector.detect(output_text=surface).pending_input == "yes"


def test_kimi_pending_input_handles_wrapping_consumption_and_incomplete_capture() -> None:
    detector = KimiCodeSignalDetectorV2_1_X()
    wrapped = (
        "  ❯ queued follow-up with a wrapped body\n"
        "    continuing on a resized pane\n"
        "  ↑ to edit · will send after compaction\n"
        "╭────────────────╮\n"
        "│ >              │\n"
        "╰────────────────╯\n"
    )
    consumed = (
        "● Finished queued follow-up.\n╭────────────────╮\n│ >              │\n╰────────────────╯\n"
    )

    assert detector.detect(output_text=wrapped).pending_input == "yes"
    assert detector.detect(output_text=consumed).pending_input == "no"
    assert detector.detect(output_text="│ >\n").pending_input == "unknown"


def test_kimi_restart_does_not_reuse_prompt_above_latest_shell_launch() -> None:
    """Kimi readiness belongs to provider chrome below the replacement launch."""

    detector = KimiCodeSignalDetectorV2_1_X()
    stale_surface = f"{_KIMI_IDLE_READY}\nbash-5.2$ /tmp/kimi-launch.sh\n"
    fresh_surface = f"{stale_surface}│ > \nkimi-for-coding kimi-k2.5 thinking\n"

    stale = detector.detect(output_text=stale_surface)
    fresh = detector.detect(output_text=fresh_surface)

    assert stale.ready_posture == "unknown"
    assert stale.accepting_input == "unknown"
    assert "provider_surface_not_fresh" in stale.notes
    assert fresh.ready_posture == "yes"
    assert fresh.accepting_input == "yes"
