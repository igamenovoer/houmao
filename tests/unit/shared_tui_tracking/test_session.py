from __future__ import annotations

import threading

import pytest
from reactivex.testing import TestScheduler

from houmao.shared_tui_tracking import (
    DetectorProfileRegistry,
    TrackerConfig,
    TuiTrackerSession,
    UnsupportedToolVersionError,
)


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

_CODEX_TMUX_READY_SURFACE = (
    "Worked for 1s • 2:09 PM\n"
    "\x1b[1m›\x1b[0m \x1b[2mAsk Codex to do anything\x1b[0m\n"
    "  GPT-6.1-Sol medium · /tmp/workdir\n"
    "  ? for shortcuts\n"
)


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


def test_detector_profile_registry_uses_bounded_compatible_interval() -> None:
    registry = DetectorProfileRegistry.default()

    exact_family = registry.resolve(
        app_id="claude_code",
        observed_version="2.1.80 (Claude Code)",
    )
    fallback_family = registry.resolve(
        app_id="claude_code",
        observed_version="1.9.0",
    )
    future_family = registry.resolve(
        app_id="claude_code",
        observed_version="2.2.0",
    )

    assert exact_family.detector_version == "2.1.x"
    assert exact_family.minimum_supported_version == (2, 1, 0)
    assert exact_family.maximum_supported_version == (2, 2, 0)
    assert fallback_family.detector_version == "fallback"
    assert future_family.detector_version == "fallback"


def test_detector_profile_registry_resolves_floor_gated_codex_family() -> None:
    registry = DetectorProfileRegistry.default()

    floor_family = registry.resolve(app_id="codex_tui", observed_version="0.162.1 (Codex)")
    above_floor_family = registry.resolve(app_id="codex_tui", observed_version="0.163.0")
    far_future_family = registry.resolve(app_id="codex_tui", observed_version="1.0.0")

    assert floor_family.detector_version == "0.162.x"
    assert floor_family.minimum_supported_version == (0, 162, 1)
    assert floor_family.maximum_supported_version is None
    assert floor_family.qualified_through_version == "0.162.1"
    assert above_floor_family.detector_version == "0.162.x"
    assert above_floor_family.qualified_through_version == "0.162.1"
    assert far_future_family.detector_version == "0.162.x"


def test_detector_profile_registry_raises_for_codex_below_the_floor() -> None:
    registry = DetectorProfileRegistry.default()

    with pytest.raises(UnsupportedToolVersionError, match="below the supported floor") as caught:
        registry.resolve(app_id="codex_tui", observed_version="0.144.0")

    assert caught.value.app_id == "codex_tui"
    assert caught.value.observed_version == "0.144.0"
    assert caught.value.minimum_supported_version == (0, 162, 1)
    assert "upgrade codex" in str(caught.value)


def test_detector_profile_registry_raises_for_unparseable_codex_version() -> None:
    registry = DetectorProfileRegistry.default()

    with pytest.raises(UnsupportedToolVersionError, match="could not be determined"):
        registry.resolve(app_id="codex_tui", observed_version=None)
    with pytest.raises(UnsupportedToolVersionError, match="could not be parsed"):
        registry.resolve(app_id="codex_tui", observed_version="not-a-version")


def test_detector_profile_registry_resolves_floor_gated_kimi_family() -> None:
    registry = DetectorProfileRegistry.default()

    floor_family = registry.resolve(app_id="kimi_code", observed_version="2.1.1")
    above_floor_family = registry.resolve(app_id="kimi_code", observed_version="2.3.0")
    far_future_family = registry.resolve(app_id="kimi_code", observed_version="8.1.0")

    assert floor_family.detector_version == "2.1.x"
    assert floor_family.minimum_supported_version == (2, 1, 1)
    assert floor_family.maximum_supported_version is None
    assert floor_family.qualified_through_version == "2.1.1"
    assert above_floor_family.detector_version == "2.1.x"
    assert above_floor_family.qualified_through_version == "2.1.1"
    assert far_future_family.detector_version == "2.1.x"


def test_detector_profile_registry_raises_for_kimi_below_the_floor() -> None:
    registry = DetectorProfileRegistry.default()

    with pytest.raises(UnsupportedToolVersionError, match="below the supported floor") as caught:
        registry.resolve(app_id="kimi_code", observed_version="0.34.0")

    assert caught.value.app_id == "kimi_code"
    assert caught.value.observed_version == "0.34.0"
    assert caught.value.minimum_supported_version == (2, 1, 1)
    assert "upgrade kimi-code" in str(caught.value)


def test_detector_profile_registry_raises_for_unparseable_kimi_version() -> None:
    registry = DetectorProfileRegistry.default()

    with pytest.raises(UnsupportedToolVersionError, match="could not be determined"):
        registry.resolve(app_id="kimi_code", observed_version=None)
    with pytest.raises(UnsupportedToolVersionError, match="could not be parsed"):
        registry.resolve(app_id="kimi_code", observed_version="not-a-version")


def test_detector_profile_registry_rejects_unknown_experimental_override() -> None:
    registry = DetectorProfileRegistry.default()

    with pytest.raises(ValueError, match="is not registered"):
        registry.resolve(
            app_id="kimi_code",
            observed_version="2.1.1",
            detector_version_override="0.34.x-experimental",
        )


def test_tracker_session_accepts_direct_tmux_raw_text_fixture() -> None:
    session = TuiTrackerSession.from_config(
        app_id="codex_tui",
        observed_version="0.162.1 (Codex)",
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
