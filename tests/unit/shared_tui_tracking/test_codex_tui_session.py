from __future__ import annotations

from reactivex.testing import TestScheduler

from houmao.shared_tui_tracking import TrackerConfig, TuiTrackerSession, app_id_from_tool


_CODEX_READY_SURFACE = "› \n\n  ? for shortcuts            100% context left\n"
_CODEX_ACTIVE_SURFACE = "› Run the tests\n\n• Working (0s • esc to interrupt)\n"
_CODEX_INTERRUPTED_SURFACE = (
    "■ Conversation interrupted - tell the model what to do differently. "
    "Something went wrong? Hit `/feedback` to report the issue.\n\n"
    "› \n"
)
_CODEX_STEER_HANDOFF_SURFACE = (
    "• Model interrupted to submit steer instructions.\n\n"
    "› Run `sleep 30` in the shell, then respond with AFTERSLEEP only.\n\n"
    "• Working (0s • esc to interrupt)\n"
)
_CODEX_ERROR_SURFACE = (
    "■ Message exceeds the maximum length of 1048576 characters (1048577 provided).\n\n› \n"
)
_CODEX_OVERLAY_SURFACE = (
    "  Would you like to grant these permissions?\n\n"
    "› 1. Yes, grant these permissions (y)\n"
    "  2. No, continue without permissions (n)\n\n"
    "  Press enter to confirm or esc to cancel\n"
)
_CODEX_TRANSCRIPT_GROWTH_START = "• Draft answer\n\n› \n"
_CODEX_TRANSCRIPT_GROWTH_CONTINUES = (
    "• Draft answer\n"
    "  continuing with a much longer explanation line that materially grows the turn\n"
    "  and a second line so the latest-turn region clearly keeps expanding\n\n"
    "› \n"
)


def _codex_session(*, scheduler: TestScheduler) -> TuiTrackerSession:
    return TuiTrackerSession.from_config(
        app_id="codex_tui",
        observed_version=None,
        config=TrackerConfig(settle_seconds=1.0, stability_threshold_seconds=0.0),
        scheduler=scheduler,
    )


def test_app_id_from_tool_maps_codex_to_codex_tui() -> None:
    assert app_id_from_tool(tool="codex") == "codex_tui"


def test_codex_tui_temporal_growth_marks_turn_active() -> None:
    scheduler = TestScheduler()
    session = _codex_session(scheduler=scheduler)

    scheduler.advance_to(1.0)
    session.on_snapshot(_CODEX_TRANSCRIPT_GROWTH_START)
    scheduler.advance_to(1.5)
    session.on_snapshot(_CODEX_TRANSCRIPT_GROWTH_CONTINUES)

    state = session.current_state()

    assert state.turn_phase == "active"
    assert "transcript_growth" in state.active_reasons


def test_codex_tui_sparse_window_does_not_infer_active() -> None:
    scheduler = TestScheduler()
    session = _codex_session(scheduler=scheduler)

    scheduler.advance_to(1.0)
    session.on_snapshot(_CODEX_TRANSCRIPT_GROWTH_START)
    scheduler.advance_to(4.5)
    session.on_snapshot(_CODEX_TRANSCRIPT_GROWTH_CONTINUES)

    state = session.current_state()

    assert state.turn_phase == "ready"
    assert "transcript_growth" not in state.active_reasons


def test_codex_tui_initial_idle_ready_posture_does_not_settle_success() -> None:
    scheduler = TestScheduler()
    session = _codex_session(scheduler=scheduler)

    scheduler.advance_to(1.0)
    session.on_snapshot(_CODEX_READY_SURFACE)
    scheduler.advance_to(3.0)

    state = session.current_state()

    assert state.turn_phase == "ready"
    assert state.last_turn_result == "none"


def test_codex_tui_snapshot_only_surface_inference_can_settle_success() -> None:
    scheduler = TestScheduler()
    session = _codex_session(scheduler=scheduler)

    scheduler.advance_to(1.0)
    session.on_snapshot(_CODEX_ACTIVE_SURFACE)
    scheduler.advance_to(1.3)
    session.on_snapshot(_CODEX_READY_SURFACE)

    candidate = session.current_state()
    assert candidate.last_turn_result == "none"

    scheduler.advance_to(2.6)
    settled = session.current_state()

    assert settled.last_turn_result == "success"
    assert settled.last_turn_source == "surface_inference"


def test_codex_tui_exact_interruption_wins_over_ready_return() -> None:
    scheduler = TestScheduler()
    session = _codex_session(scheduler=scheduler)

    scheduler.advance_to(1.0)
    session.on_snapshot(_CODEX_ACTIVE_SURFACE)
    scheduler.advance_to(1.4)
    session.on_snapshot(_CODEX_INTERRUPTED_SURFACE)

    state = session.current_state()

    assert state.turn_phase == "ready"
    assert state.last_turn_result == "interrupted"


def test_codex_tui_steer_handoff_surface_stays_active() -> None:
    scheduler = TestScheduler()
    session = _codex_session(scheduler=scheduler)

    scheduler.advance_to(1.0)
    session.on_snapshot(_CODEX_STEER_HANDOFF_SURFACE)

    state = session.current_state()

    assert state.turn_phase == "active"
    assert state.last_turn_result == "none"
    assert "steer_handoff" in state.active_reasons


def test_codex_tui_generic_error_blocks_success_and_degrades_posture() -> None:
    scheduler = TestScheduler()
    session = _codex_session(scheduler=scheduler)

    scheduler.advance_to(1.0)
    session.on_snapshot(_CODEX_ACTIVE_SURFACE)
    scheduler.advance_to(1.4)
    session.on_snapshot(_CODEX_ERROR_SURFACE)
    scheduler.advance_to(3.0)

    state = session.current_state()

    assert state.turn_phase == "unknown"
    assert state.last_turn_result == "none"


def test_codex_tui_overlay_degrades_to_unknown() -> None:
    scheduler = TestScheduler()
    session = _codex_session(scheduler=scheduler)

    scheduler.advance_to(1.0)
    session.on_snapshot(_CODEX_OVERLAY_SURFACE)

    state = session.current_state()

    assert state.surface_ready_posture == "unknown"
    assert state.turn_phase == "unknown"
