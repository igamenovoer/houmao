from __future__ import annotations

from reactivex.testing import TestScheduler

from houmao.shared_tui_tracking import TrackerConfig, TuiTrackerSession, app_id_from_tool
from houmao.shared_tui_tracking.apps.kimi_code.profile import analyze_kimi_surface


_KIMI_READY_WITH_FOOTER_THINKING = (
    "╭────────────────────────────────────────╮\n"
    "│ >                                      │\n"
    "╰────────────────────────────────────────╯\n"
    "Kimi-k2.6 thinking  /model: switch model\n"
    "context: 0.0%\n"
)
_KIMI_DRAFT = (
    "╭────────────────────────────────────────╮\n"
    "│ > summarize the current status         │\n"
    "╰────────────────────────────────────────╯\n"
)
_KIMI_ACTIVE = (
    "User asked a question\n"
    "⠋ working...\n"
    "╭────────────────────────────────────────╮\n"
    "│ >                                      │\n"
    "╰────────────────────────────────────────╯\n"
)
_KIMI_APPROVAL = (
    "────────────────────────────────────────\n"
    "  ▶ Run this command?\n"
    "\n"
    "  cwd: /tmp/project\n"
    "  $ pwd\n"
    "\n"
    "  ▶ 1. Approve once\n"
    "    2. Approve for this session\n"
    "    3. Reject\n"
    "    4. Reject with feedback\n"
    "────────────────────────────────────────\n"
    "╭────────────────────────────────────────╮\n"
    "│ >                                      │\n"
    "╰────────────────────────────────────────╯\n"
)


def _kimi_session(*, scheduler: TestScheduler) -> TuiTrackerSession:
    return TuiTrackerSession.from_config(
        app_id="kimi_code",
        observed_version="0.11.0",
        config=TrackerConfig(settle_seconds=1.0, stability_threshold_seconds=0.0),
        scheduler=scheduler,
    )


def test_app_id_from_tool_maps_kimi_to_kimi_code() -> None:
    assert app_id_from_tool(tool="kimi") == "kimi_code"


def test_kimi_ready_footer_thinking_does_not_mark_active() -> None:
    scheduler = TestScheduler()
    session = _kimi_session(scheduler=scheduler)

    scheduler.advance_to(1.0)
    session.on_snapshot(_KIMI_READY_WITH_FOOTER_THINKING)
    state = session.current_state()

    assert state.detector_name == "kimi_code"
    assert state.turn_phase == "ready"
    assert state.surface_accepting_input == "yes"
    assert state.surface_ready_posture == "yes"
    assert "footer_thinking_metadata_ignored" in state.notes


def test_kimi_draft_marks_editing_without_active_turn() -> None:
    scheduler = TestScheduler()
    session = _kimi_session(scheduler=scheduler)

    scheduler.advance_to(1.0)
    session.on_snapshot(_KIMI_DRAFT)
    state = session.current_state()

    assert state.turn_phase == "ready"
    assert state.surface_accepting_input == "yes"
    assert state.surface_editing_input == "yes"
    assert state.last_turn_result == "none"


def test_kimi_activity_spinner_marks_turn_active() -> None:
    scheduler = TestScheduler()
    session = _kimi_session(scheduler=scheduler)

    scheduler.advance_to(1.0)
    session.on_snapshot(_KIMI_ACTIVE)
    state = session.current_state()

    assert state.turn_phase == "active"
    assert state.surface_accepting_input == "no"
    assert "braille_spinner" in state.active_reasons


def test_kimi_approval_panel_marks_operator_blocked_active_turn() -> None:
    scheduler = TestScheduler()
    session = _kimi_session(scheduler=scheduler)

    scheduler.advance_to(1.0)
    session.on_snapshot(_KIMI_APPROVAL)
    state = session.current_state()
    analysis = analyze_kimi_surface(_KIMI_APPROVAL)

    assert analysis.approval_visible is True
    assert analysis.approval_choice_count == 4
    assert state.turn_phase == "active"
    assert state.surface_accepting_input == "no"
    assert state.surface_ready_posture == "no"
    assert "approval_panel" in state.active_reasons
