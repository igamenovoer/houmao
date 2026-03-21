from __future__ import annotations

import threading

from reactivex.testing import TestScheduler

from houmao.shared_tui_tracking import DetectorProfileRegistry, TrackerConfig, TuiTrackerSession


_CLAUDE_ACTIVE_SURFACE = (
    "❯ explain the repository carefully\n\n"
    "✢ Unfurling…\n\n"
    "────────────────────────────────────────────────────────────────────────────────\n"
    "❯\n"
    "────────────────────────────────────────────────────────────────────────────────\n"
    "  ⏵⏵ bypass permissions on (shift+tab to cycle) · esc to interrupt\n"
)

_CLAUDE_SUCCESS_SURFACE = (
    "● READY\n\n"
    "✻ Worked for 3s\n\n"
    "────────────────────────────────────────────────────────────────────────────────\n"
    "❯\n"
    "────────────────────────────────────────────────────────────────────────────────\n"
    "  ⏵⏵ bypass permissions on (shift+tab to cycle)\n"
)

_CODEX_TMUX_READY_SURFACE = "─ Worked for 1s ─\n› \n"


def test_tracker_session_settles_success_with_virtual_time() -> None:
    scheduler = TestScheduler()
    session = TuiTrackerSession.from_config(
        app_id="claude_code",
        observed_version="2.1.80 (Claude Code)",
        config=TrackerConfig(settle_seconds=1.0, stability_threshold_seconds=0.5),
        scheduler=scheduler,
    )

    session.on_snapshot(_CLAUDE_ACTIVE_SURFACE)
    session.drain_events()
    scheduler.advance_to(1.0)
    session.on_snapshot(_CLAUDE_SUCCESS_SURFACE)

    candidate = session.current_state()
    assert candidate.last_turn_result == "none"
    assert candidate.stable is False

    scheduler.advance_to(1.6)
    stable_candidate = session.current_state()
    assert stable_candidate.stable is True

    scheduler.advance_to(2.1)
    settled_events = session.drain_events()
    settled = session.current_state()

    assert settled.last_turn_result == "success"
    assert any(item.note == "success_settled" for item in settled_events)


def test_detector_profile_registry_uses_closest_compatible_floor() -> None:
    registry = DetectorProfileRegistry.default()

    exact_family = registry.resolve(
        app_id="claude_code",
        observed_version="2.1.80 (Claude Code)",
    )
    fallback_family = registry.resolve(
        app_id="claude_code",
        observed_version="1.9.0",
    )

    assert exact_family.detector_version == "2.1.x"
    assert fallback_family.detector_version == "fallback"


def test_tracker_session_accepts_direct_tmux_raw_text_fixture() -> None:
    session = TuiTrackerSession.from_config(
        app_id="codex_tui",
        observed_version=None,
        config=TrackerConfig(settle_seconds=1.0),
        scheduler=TestScheduler(),
    )

    session.on_snapshot(_CODEX_TMUX_READY_SURFACE)
    state = session.current_state()

    assert state.surface_accepting_input == "yes"
    assert state.surface_ready_posture == "yes"
    assert state.turn_phase == "ready"


def test_tracker_session_is_safe_for_concurrent_reads_and_writes() -> None:
    session = TuiTrackerSession.from_config(
        app_id="claude_code",
        observed_version="2.1.80 (Claude Code)",
        config=TrackerConfig(settle_seconds=1.0),
        scheduler=TestScheduler(),
    )
    errors: list[BaseException] = []

    def _writer() -> None:
        try:
            for index in range(50):
                session.on_snapshot(
                    _CLAUDE_ACTIVE_SURFACE if index % 2 == 0 else _CLAUDE_SUCCESS_SURFACE
                )
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    def _reader() -> None:
        try:
            for _ in range(50):
                session.current_state()
                session.drain_events()
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    writer = threading.Thread(target=_writer)
    reader = threading.Thread(target=_reader)
    writer.start()
    reader.start()
    writer.join(timeout=5.0)
    reader.join(timeout=5.0)

    assert not errors
