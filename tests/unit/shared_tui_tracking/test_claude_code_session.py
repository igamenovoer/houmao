from __future__ import annotations

from reactivex.testing import TestScheduler

from houmao.shared_tui_tracking import TrackerConfig, TuiTrackerSession
from houmao.shared_tui_tracking.apps.claude_code.profile import (
    ClaudeCodeSignalDetectorV2_1_X,
    FallbackClaudeDetector,
)


_CLAUDE_PLACEHOLDER_READY_SURFACE = (
    "\x1b[38;5;244m────────────────────────────────────────────────────────────────\n"
    '\x1b[39m❯\xa0\x1b[7mT\x1b[0;2mry\x1b[0m \x1b[2m"fix\x1b[0m '
    '\x1b[2mtypecheck\x1b[0m \x1b[2merrors"\x1b[0m\n'
    "\x1b[38;5;244m────────────────────────────────────────────────────────────────\n"
    "\x1b[39m  \x1b[38;5;211m⏵⏵ bypass permissions on\x1b[38;5;246m (shift+tab to cycle)\x1b[39m\n"
)
_CLAUDE_TYPED_DRAFT_READY_SURFACE = (
    "\x1b[38;5;244m────────────────────────────────────────────────────────────────\n"
    "\x1b[39m❯ Review staged change\x1b[7ms\x1b[0m\n"
    "\x1b[38;5;244m────────────────────────────────────────────────────────────────\n"
    "\x1b[39m  \x1b[38;5;211m⏵⏵ bypass permissions on\x1b[38;5;246m (shift+tab to cycle)\x1b[39m\n"
)
_CLAUDE_UNRECOGNIZED_STYLED_READY_SURFACE = (
    "\x1b[38;5;244m────────────────────────────────────────────────────────────────\n"
    "\x1b[39m❯\xa0\x1b[33mReview staged changes\x1b[0m\n"
    "\x1b[38;5;244m────────────────────────────────────────────────────────────────\n"
    "\x1b[39m  \x1b[38;5;211m⏵⏵ bypass permissions on\x1b[38;5;246m (shift+tab to cycle)\x1b[39m\n"
)


def _claude_session(*, scheduler: TestScheduler) -> TuiTrackerSession:
    return TuiTrackerSession.from_config(
        app_id="claude_code",
        observed_version="2.1.81 (Claude Code)",
        config=TrackerConfig(settle_seconds=1.0, stability_threshold_seconds=0.0),
        scheduler=scheduler,
    )


def test_claude_startup_placeholder_prompt_does_not_count_as_editing() -> None:
    scheduler = TestScheduler()
    session = _claude_session(scheduler=scheduler)

    scheduler.advance_to(1.0)
    session.on_snapshot(_CLAUDE_PLACEHOLDER_READY_SURFACE)

    state = session.current_state()

    assert state.surface_accepting_input == "yes"
    assert state.surface_ready_posture == "yes"
    assert state.surface_editing_input == "no"
    assert state.turn_phase == "ready"


def test_claude_typed_draft_counts_as_editing() -> None:
    detector = ClaudeCodeSignalDetectorV2_1_X()

    signals = detector.detect(output_text=_CLAUDE_TYPED_DRAFT_READY_SURFACE)

    assert signals.accepting_input == "yes"
    assert signals.editing_input == "yes"
    assert signals.prompt_text == "Review staged changes"
    assert "prompt_behavior_variant=2.1.x" in signals.notes
    assert "prompt_kind=draft" in signals.notes


def test_claude_placeholder_prompt_keeps_prompt_text_empty() -> None:
    detector = ClaudeCodeSignalDetectorV2_1_X()

    signals = detector.detect(output_text=_CLAUDE_PLACEHOLDER_READY_SURFACE)

    assert signals.accepting_input == "yes"
    assert signals.editing_input == "no"
    assert signals.prompt_text is None
    assert "prompt_behavior_variant=2.1.x" in signals.notes
    assert "prompt_kind=placeholder" in signals.notes


def test_claude_unrecognized_styled_prompt_degrades_to_unknown_editing() -> None:
    detector = ClaudeCodeSignalDetectorV2_1_X()

    signals = detector.detect(output_text=_CLAUDE_UNRECOGNIZED_STYLED_READY_SURFACE)

    assert signals.accepting_input == "yes"
    assert signals.editing_input == "unknown"
    assert signals.prompt_text is None
    assert "unrecognized_prompt_presentation" in signals.notes
    assert "prompt_behavior_variant=2.1.x" in signals.notes


def test_fallback_claude_detector_keeps_nonempty_prompt_unknown() -> None:
    detector = FallbackClaudeDetector()

    signals = detector.detect(output_text=_CLAUDE_TYPED_DRAFT_READY_SURFACE)

    assert signals.accepting_input == "yes"
    assert signals.editing_input == "unknown"
    assert signals.prompt_text is None
    assert "fallback_detector" in signals.notes
    assert "prompt_behavior_variant=fallback" in signals.notes
