from __future__ import annotations

from pathlib import Path

from reactivex.testing import TestScheduler

from houmao.shared_tui_tracking import TrackerConfig, TuiTrackerSession, app_id_from_tool
from houmao.shared_tui_tracking.apps.kimi_code.profile import (
    KimiCodeSignalDetectorV0_23_X,
    analyze_kimi_surface,
)


_FIXTURE_ROOT = (
    Path(__file__).resolve().parents[2] / "fixtures" / "shared_tui_tracking" / "kimi_code"
)


def _fixture(name: str) -> str:
    """Return one recorded Kimi visible-surface fixture."""

    return (_FIXTURE_ROOT / name).read_text(encoding="utf-8")


_KIMI_READY_WITH_FOOTER_THINKING = _fixture("footer_thinking_ready_prompt.txt")
_KIMI_DRAFT = (
    "╭────────────────────────────────────────╮\n"
    "│ > summarize the current status         │\n"
    "╰────────────────────────────────────────╯\n"
)
_KIMI_ACTIVE = _fixture("active_response.txt")
_KIMI_APPROVAL = _fixture("command_approval.txt")
_KIMI_STALE_RESTART = f"{_KIMI_READY_WITH_FOOTER_THINKING}\nbash-5.2$ /tmp/kimi-launch.sh\n"
_KIMI_FRESH_RESTART = f"{_KIMI_STALE_RESTART}│ > \nkimi-for-coding kimi-k2.5 thinking\n"


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


def test_kimi_completed_response_fixture_marks_ready_success_candidate() -> None:
    scheduler = TestScheduler()
    session = _kimi_session(scheduler=scheduler)

    scheduler.advance_to(1.0)
    session.on_snapshot(_fixture("completed_response.txt"))
    state = session.current_state()

    assert state.turn_phase == "ready"
    assert state.surface_accepting_input == "yes"
    assert state.surface_ready_posture == "yes"


def test_kimi_rejected_command_fixture_is_ready_not_known_failure() -> None:
    scheduler = TestScheduler()
    session = _kimi_session(scheduler=scheduler)

    scheduler.advance_to(1.0)
    session.on_snapshot(_fixture("rejected_command.txt"))
    state = session.current_state()

    assert state.turn_phase == "ready"
    assert state.surface_accepting_input == "yes"
    assert state.last_turn_result == "none"


def test_kimi_023_detector_ignores_historical_moon_spinner_after_completion() -> None:
    detector = KimiCodeSignalDetectorV0_23_X()
    completed = (
        "🌗 · Tip: ctrl+s: steer mid-turn\n\n"
        "● Finished the requested task.\n\n"
        "╭────────────────────────────────────────╮\n"
        "│ >                                      │\n"
        "╰────────────────────────────────────────╯\n"
        "auto  kimi-for-coding-highspeed thinking\n"
        "context: 10.0%\n"
    )

    signals = detector.detect(output_text=completed)

    assert signals.active_evidence is False
    assert signals.ready_posture == "yes"
    assert signals.accepting_input == "yes"
    assert "footer_thinking_metadata_ignored" in signals.notes


def test_kimi_023_detector_tracks_live_edge_moon_spinner() -> None:
    detector = KimiCodeSignalDetectorV0_23_X()
    active = (
        "✨ Inspect the repository.\n\n"
        "🌑 · Tip: ctrl+s: steer mid-turn\n"
        "╭────────────────────────────────────────╮\n"
        "│ >                                      │\n"
        "╰────────────────────────────────────────╯\n"
        "auto  kimi-for-coding-highspeed thinking  context: 0.0%\n"
    )

    signals = detector.detect(output_text=active)

    assert signals.active_evidence is True
    assert "moon_spinner" in signals.active_reasons
    assert signals.ready_posture == "no"


def test_kimi_023_detector_tracks_streaming_queue_when_spinner_is_displaced() -> None:
    detector = KimiCodeSignalDetectorV0_23_X()
    active = (
        "🌑 · Tip: ctrl+s: steer mid-turn\n"
        "────────────────────────────────────────\n"
        "  ❯ queued follow-up\n"
        "  ↑ to edit · ctrl-s to steer immediately\n"
        "╭────────────────────────────────────────╮\n"
        "│ >                                      │\n"
        "╰────────────────────────────────────────╯\n"
        "auto  kimi-for-coding-highspeed thinking  context: 1.0%\n"
    )

    signals = detector.detect(output_text=active)
    analysis = analyze_kimi_surface(active, activity_window_lines=4)

    assert analysis.queue_visible is True
    assert analysis.queue_hint == "↑ to edit · ctrl-s to steer immediately"
    assert signals.active_evidence is True
    assert signals.active_reasons == ("queued_message",)
    assert signals.ready_posture == "no"
    assert signals.success_blocked is True


def test_kimi_023_detector_tracks_each_deferred_queue_mode() -> None:
    detector = KimiCodeSignalDetectorV0_23_X()

    for hint in (
        "↑ to edit · will send after current task",
        "↑ to edit · will send after compaction",
    ):
        surface = (
            "● Current task output\n"
            "────────────────────────────────────────\n"
            "  ❯ queued follow-up\n"
            f"  {hint}\n"
            "╭────────────────────────────────────────╮\n"
            "│ >                                      │\n"
            "╰────────────────────────────────────────╯\n"
            "auto  kimi-for-coding-highspeed thinking  context: 1.0%\n"
        )

        signals = detector.detect(output_text=surface)

        assert signals.active_evidence is True
        assert "queued_message" in signals.active_reasons
        assert signals.ready_posture == "no"


def test_kimi_023_detector_ignores_historical_queue_after_settled_response() -> None:
    detector = KimiCodeSignalDetectorV0_23_X()
    historical = (
        "  ↑ to edit · ctrl-s to steer immediately\n"
        + "\n".join(f"● settled response line {index}" for index in range(30))
        + "\n╭────────────────────────────────────────╮\n"
        "│ >                                      │\n"
        "╰────────────────────────────────────────╯\n"
        "auto  kimi-for-coding-highspeed thinking  context: 2.0%\n"
    )

    signals = detector.detect(output_text=historical)

    assert signals.active_evidence is False
    assert signals.ready_posture == "yes"


def test_kimi_restart_does_not_reuse_prompt_above_latest_shell_launch() -> None:
    """Kimi readiness belongs to provider chrome below the replacement launch."""

    detector = KimiCodeSignalDetectorV0_23_X()

    stale = detector.detect(output_text=_KIMI_STALE_RESTART)
    fresh = detector.detect(output_text=_KIMI_FRESH_RESTART)

    assert stale.ready_posture == "unknown"
    assert stale.accepting_input == "unknown"
    assert "provider_surface_not_fresh" in stale.notes
    assert fresh.ready_posture == "yes"
    assert fresh.accepting_input == "yes"
