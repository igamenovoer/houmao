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
_CLAUDE_COLOR_STYLED_DRAFT_READY_SURFACE = (
    "\x1b[38;5;244m────────────────────────────────────────────────────────────────\n"
    "\x1b[39m❯\xa0\x1b[38;5;33mReview staged changes\x1b[49m\x1b[0m\n"
    "\x1b[38;5;244m────────────────────────────────────────────────────────────────\n"
    "\x1b[39m  \x1b[38;5;211m⏵⏵ bypass permissions on\x1b[38;5;246m (shift+tab to cycle)\x1b[39m\n"
)
_CLAUDE_GHOST_SUGGESTION_READY_SURFACE = (
    "\x1b[38;5;244m────────────────────────────────────────────────────────────────\n"
    "\x1b[38;5;239m\x1b[48;5;237m❯ \x1b[38;5;231mReview the latest mailbox item\x1b[39m\n"
    "\x1b[38;5;244m────────────────────────────────────────────────────────────────\n"
    "\x1b[39m  \x1b[38;5;211m⏵⏵ bypass permissions on\x1b[38;5;246m (shift+tab to cycle)\x1b[39m\n"
)
_CLAUDE_UNRECOGNIZED_NON_COLOR_STYLED_READY_SURFACE = (
    "\x1b[38;5;244m────────────────────────────────────────────────────────────────\n"
    "\x1b[39m❯\xa0\x1b[4mReview staged changes\x1b[0m\n"
    "\x1b[38;5;244m────────────────────────────────────────────────────────────────\n"
    "\x1b[39m  \x1b[38;5;211m⏵⏵ bypass permissions on\x1b[38;5;246m (shift+tab to cycle)\x1b[39m\n"
)
_CLAUDE_INTERRUPTED_READY_SURFACE = (
    "❯ Explain reducer semantics carefully\n"
    "  ⎿ Interrupted · What should Claude do instead?\n\n"
    "────────────────────────────────────────────────────────────────\n"
    "❯\n"
    "────────────────────────────────────────────────────────────────\n"
    "  ⏵⏵ bypass permissions on (shift+tab to cycle)\n"
)
_CLAUDE_INTERRUPTED_READY_WITH_DRAFT_SURFACE = (
    "❯ Explain reducer semantics carefully\n"
    "  ⎿ Interrupted · What should Claude do instead?\n\n"
    "────────────────────────────────────────────────────────────────\n"
    "\x1b[39m❯ Review staged change\x1b[7ms\x1b[0m\n"
    "────────────────────────────────────────────────────────────────\n"
    "  ⏵⏵ bypass permissions on (shift+tab to cycle)\n"
)
_CLAUDE_STALE_INTERRUPTED_SCROLLBACK_WITH_DRAFT_SURFACE = (
    "❯ Explain reducer semantics carefully\n"
    "  ⎿ Interrupted · What should Claude do instead?\n\n"
    "● Prior turn already settled cleanly.\n\n"
    "────────────────────────────────────────────────────────────────\n"
    "\x1b[39m❯ Review staged change\x1b[7ms\x1b[0m\n"
    "────────────────────────────────────────────────────────────────\n"
    "  ⏵⏵ bypass permissions on (shift+tab to cycle)\n"
)
_CLAUDE_OVERLAPPING_ACTIVE_DRAFT_SURFACE = (
    "❯ Explain reducer semantics carefully\n\n"
    "✢ Unfurling…\n\n"
    "────────────────────────────────────────────────────────────────\n"
    "\x1b[39m❯ Review staged change\x1b[7ms\x1b[0m\n"
    "────────────────────────────────────────────────────────────────\n"
    "  ⏵⏵ bypass permissions on (shift+tab to cycle) · esc to interrupt\n"
)
_CLAUDE_STALE_THINKING_SCROLLBACK_READY_SURFACE = (
    "❯ Review the mailbox continuation request\n\n"
    "✢ Musing…\n\n"
    "● Reading story/02-see-it-properly.md\n"
    "  ⎿ Read 152 lines\n\n"
    "● Writing consistency notes\n"
    "  ⎿ Updated story/review/20260409-chapter-02-see-it-properly.md\n\n"
    "─ Worked for 1m 16s ─────────────────────────────────────────────\n\n"
    "I’ve got the chapter context now and the review file is written.\n\n"
    "────────────────────────────────────────────────────────────────\n"
    "❯\n"
    "────────────────────────────────────────────────────────────────\n"
    "  ⏵⏵ bypass permissions on (shift+tab to cycle)\n"
)
_CLAUDE_STALE_THINKING_VISIBLE_TAIL_READY_SURFACE = (
    "─ Worked for 1m 16s ─────────────────────────────────────────────\n\n"
    "I’ve got the chapter context now and the review file is written.\n\n"
    "────────────────────────────────────────────────────────────────\n"
    "❯\n"
    "────────────────────────────────────────────────────────────────\n"
    "  ⏵⏵ bypass permissions on (shift+tab to cycle)\n"
)
_CLAUDE_PROSE_ONLY_ACTIVITY_WORDS_READY_SURFACE = (
    "❯ Review the mailbox continuation request\n\n"
    "Musing…\n\n"
    "Running…\n\n"
    "Reading story/02-see-it-properly.md\n\n"
    "The transcript above mentions work words, but no spinner is active now.\n\n"
    "────────────────────────────────────────────────────────────────\n"
    "❯\n"
    "────────────────────────────────────────────────────────────────\n"
    "  ⏵⏵ bypass permissions on (shift+tab to cycle)\n"
)
_CLAUDE_CURRENT_SPINNER_READY_SURFACE = (
    "❯ Review the mailbox continuation request\n\n"
    "✢ Musing…\n\n"
    "────────────────────────────────────────────────────────────────\n"
    "❯\n"
    "────────────────────────────────────────────────────────────────\n"
    "  ⏵⏵ bypass permissions on (shift+tab to cycle)\n"
)
_CLAUDE_RULE = "────────────────────────────────────────────────────────────────"
_CLAUDE_QUEUED_STYLE = "\x1b[38;5;239m\x1b[48;5;237m❯ \x1b[38;5;231m"
_CLAUDE_GHOST_STYLE = "\x1b[38;5;246m❯ \x1b[7m\x1b[39mP\x1b[0;2m"


def _claude_pending_surface(
    *,
    queued_lines: tuple[str, ...],
    suggestion: str | None = "Press up to edit queued messages",
    rule: str = _CLAUDE_RULE,
) -> str:
    """Build one bounded Claude busy composer with queued-preview rows."""

    composer = "\x1b[39m❯\xa0\x1b[7m \x1b[0m"
    if suggestion is not None:
        composer = f"{_CLAUDE_GHOST_STYLE}{suggestion}\x1b[0m"
    return (
        "❯ Run the active task.\n\n"
        "✢ Working…\n\n" + "\n".join(queued_lines) + f"\n{rule}\n{composer}\n{rule}\n"
        "  ⏵⏵ bypass permissions on · esc to interrupt\n"
    )


def _queued_row(text: str, *, style: str = _CLAUDE_QUEUED_STYLE) -> str:
    """Return one indented Claude queued-preview row."""

    return f"  {style}{text}\x1b[39m\x1b[49m"


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
    assert state.surface_pending_input == "unknown"


def test_claude_pending_input_uses_queued_row_not_suggestion_wording() -> None:
    detector = ClaudeCodeSignalDetectorV2_1_X()

    arbitrary = detector.detect(
        output_text=_claude_pending_surface(
            queued_lines=(_queued_row("Continue with the audit."),),
            suggestion="Reprendre le message en attente",
        )
    )
    empty_composer = detector.detect(
        output_text=_claude_pending_surface(
            queued_lines=(_queued_row("Continue with the audit."),),
            suggestion=None,
        )
    )

    assert arbitrary.pending_input == "yes"
    assert empty_composer.pending_input == "yes"
    assert (
        FallbackClaudeDetector()
        .detect(
            output_text=_claude_pending_surface(
                queued_lines=(_queued_row("Continue with the audit."),),
            )
        )
        .pending_input
        == "yes"
    )


def test_claude_pending_input_handles_multiple_wrapped_and_resized_rows() -> None:
    detector = ClaudeCodeSignalDetectorV2_1_X()
    multiple = _claude_pending_surface(
        queued_lines=(
            _queued_row("First follow-up."),
            _queued_row("Second follow-up."),
        )
    )
    wrapped = _claude_pending_surface(
        queued_lines=(
            _queued_row("Review the long wrapped follow-up and"),
            "    continue checking its final clause.",
        ),
        rule="────────────────────────",
    )

    assert detector.detect(output_text=multiple).pending_input == "yes"
    assert detector.detect(output_text=wrapped).pending_input == "yes"


def test_claude_pending_input_allows_one_live_composer_spacer_but_not_two() -> None:
    detector = ClaudeCodeSignalDetectorV2_1_X()
    direct = _claude_pending_surface(
        queued_lines=(_queued_row("Continue after the shell command."),)
    )
    one_spacer = direct.replace(f"\n{_CLAUDE_RULE}\n", f"\n\n{_CLAUDE_RULE}\n", 1)
    two_spacers = direct.replace(f"\n{_CLAUDE_RULE}\n", f"\n\n\n{_CLAUDE_RULE}\n", 1)

    assert detector.detect(output_text=one_spacer).pending_input == "yes"
    assert detector.detect(output_text=two_spacers).pending_input == "no"


def test_claude_pending_input_rejects_non_queue_lookalikes() -> None:
    detector = ClaudeCodeSignalDetectorV2_1_X()
    queue_prose = _claude_pending_surface(
        queued_lines=("The transcript says Press up to edit queued messages.",)
    )
    separated_history = _claude_pending_surface(
        queued_lines=(
            _queued_row("Historical user cell."),
            "● Later assistant output separates the old cell.",
        )
    )

    assert (
        detector.detect(output_text="\n" + _CLAUDE_GHOST_SUGGESTION_READY_SURFACE).pending_input
        == "no"
    )
    assert detector.detect(output_text=queue_prose).pending_input == "no"
    assert detector.detect(output_text=separated_history).pending_input == "no"
    assert (
        detector.detect(output_text="\n" + _CLAUDE_TYPED_DRAFT_READY_SURFACE).pending_input == "no"
    )


def test_claude_pending_input_degrades_cropped_or_unrecognized_structure() -> None:
    detector = ClaudeCodeSignalDetectorV2_1_X()
    cropped = "❯ composer without its frame\n"
    unrecognized_style = _claude_pending_surface(
        queued_lines=(_queued_row("Queued-looking row.", style="\x1b[4m❯ "),)
    )

    assert detector.detect(output_text=cropped).pending_input == "unknown"
    assert detector.detect(output_text=unrecognized_style).pending_input == "unknown"


def test_claude_ghost_suggestion_prompt_does_not_count_as_editing() -> None:
    scheduler = TestScheduler()
    session = _claude_session(scheduler=scheduler)

    scheduler.advance_to(1.0)
    session.on_snapshot(_CLAUDE_GHOST_SUGGESTION_READY_SURFACE)

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
    assert signals.chat_context == "current"
    assert signals.chat_context_diagnostic is None


def test_claude_placeholder_prompt_keeps_prompt_text_empty() -> None:
    detector = ClaudeCodeSignalDetectorV2_1_X()

    signals = detector.detect(output_text=_CLAUDE_PLACEHOLDER_READY_SURFACE)

    assert signals.accepting_input == "yes"
    assert signals.editing_input == "no"
    assert signals.prompt_text is None
    assert "prompt_behavior_variant=2.1.x" in signals.notes
    assert "prompt_kind=placeholder" in signals.notes


def test_claude_color_styled_draft_counts_as_editing() -> None:
    detector = ClaudeCodeSignalDetectorV2_1_X()

    signals = detector.detect(output_text=_CLAUDE_COLOR_STYLED_DRAFT_READY_SURFACE)

    assert signals.accepting_input == "yes"
    assert signals.editing_input == "yes"
    assert signals.prompt_text == "Review staged changes"
    assert "prompt_kind=draft" in signals.notes
    assert "unrecognized_prompt_presentation" not in signals.notes


def test_claude_non_color_styled_prompt_degrades_to_unknown_editing() -> None:
    detector = ClaudeCodeSignalDetectorV2_1_X()

    signals = detector.detect(output_text=_CLAUDE_UNRECOGNIZED_NON_COLOR_STYLED_READY_SURFACE)

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


def test_claude_detector_ignores_stale_interrupted_scrollback_above_current_draft() -> None:
    detector = ClaudeCodeSignalDetectorV2_1_X()

    signals = detector.detect(output_text=_CLAUDE_STALE_INTERRUPTED_SCROLLBACK_WITH_DRAFT_SURFACE)

    assert signals.interrupted is False
    assert signals.editing_input == "yes"
    assert signals.prompt_text == "Review staged changes"


def test_claude_detector_matches_interrupted_signal_above_current_draft() -> None:
    detector = ClaudeCodeSignalDetectorV2_1_X()

    signals = detector.detect(output_text=_CLAUDE_INTERRUPTED_READY_WITH_DRAFT_SURFACE)

    assert signals.interrupted is True
    assert signals.editing_input == "yes"
    assert signals.prompt_text == "Review staged changes"


def test_claude_detector_keeps_overlapping_active_draft_visible() -> None:
    detector = ClaudeCodeSignalDetectorV2_1_X()

    signals = detector.detect(output_text=_CLAUDE_OVERLAPPING_ACTIVE_DRAFT_SURFACE)

    assert signals.active_evidence is True
    assert "thinking_line" in signals.active_reasons
    assert signals.interrupted is False
    assert signals.editing_input == "yes"
    assert signals.prompt_text == "Review staged changes"


def test_claude_detector_ignores_stale_thinking_scrollback_above_ready_prompt() -> None:
    detector = ClaudeCodeSignalDetectorV2_1_X()

    full_signals = detector.detect(output_text=_CLAUDE_STALE_THINKING_SCROLLBACK_READY_SURFACE)
    tail_signals = detector.detect(output_text=_CLAUDE_STALE_THINKING_VISIBLE_TAIL_READY_SURFACE)

    assert full_signals.accepting_input == tail_signals.accepting_input == "yes"
    assert full_signals.ready_posture == tail_signals.ready_posture == "yes"
    assert full_signals.editing_input == tail_signals.editing_input == "no"
    assert full_signals.active_evidence is False
    assert tail_signals.active_evidence is False
    assert "thinking_line" not in full_signals.active_reasons
    assert full_signals.success_candidate is True


def test_claude_detector_ignores_prose_only_activity_words_above_ready_prompt() -> None:
    detector = ClaudeCodeSignalDetectorV2_1_X()

    signals = detector.detect(output_text=_CLAUDE_PROSE_ONLY_ACTIVITY_WORDS_READY_SURFACE)

    assert signals.accepting_input == "yes"
    assert signals.ready_posture == "yes"
    assert signals.editing_input == "no"
    assert signals.active_evidence is False
    assert signals.active_reasons == ()


def test_claude_detector_keeps_current_spinner_active() -> None:
    detector = ClaudeCodeSignalDetectorV2_1_X()

    signals = detector.detect(output_text=_CLAUDE_CURRENT_SPINNER_READY_SURFACE)

    assert signals.active_evidence is True
    assert "thinking_line" in signals.active_reasons
    assert signals.accepting_input == "yes"
    assert signals.editing_input == "no"


def test_claude_session_clears_interrupted_result_when_stale_scrollback_turn_is_visible() -> None:
    scheduler = TestScheduler()
    session = _claude_session(scheduler=scheduler)

    scheduler.advance_to(1.0)
    session.on_snapshot(_CLAUDE_INTERRUPTED_READY_SURFACE)

    assert session.current_state().last_turn_result == "interrupted"

    scheduler.advance_to(1.4)
    session.on_snapshot(_CLAUDE_STALE_INTERRUPTED_SCROLLBACK_WITH_DRAFT_SURFACE)
    state = session.current_state()

    assert state.turn_phase == "ready"
    assert state.surface_editing_input == "yes"
    assert state.last_turn_result == "none"
    assert state.last_turn_source == "none"


def test_claude_session_stale_thinking_scrollback_stays_ready() -> None:
    scheduler = TestScheduler()
    session = _claude_session(scheduler=scheduler)

    scheduler.advance_to(1.0)
    session.on_snapshot(_CLAUDE_STALE_THINKING_SCROLLBACK_READY_SURFACE)
    state = session.current_state()

    assert state.surface_accepting_input == "yes"
    assert state.surface_ready_posture == "yes"
    assert state.surface_editing_input == "no"
    assert state.turn_phase == "ready"
    assert "thinking_line" not in state.active_reasons


def test_claude_session_prose_only_activity_words_stays_ready() -> None:
    scheduler = TestScheduler()
    session = _claude_session(scheduler=scheduler)

    scheduler.advance_to(1.0)
    session.on_snapshot(_CLAUDE_PROSE_ONLY_ACTIVITY_WORDS_READY_SURFACE)
    state = session.current_state()

    assert state.surface_accepting_input == "yes"
    assert state.surface_ready_posture == "yes"
    assert state.surface_editing_input == "no"
    assert state.turn_phase == "ready"
    assert state.active_reasons == ()


def test_claude_session_keeps_overlapping_active_draft_visible() -> None:
    scheduler = TestScheduler()
    session = _claude_session(scheduler=scheduler)

    scheduler.advance_to(1.0)
    session.on_snapshot(_CLAUDE_INTERRUPTED_READY_SURFACE)

    assert session.current_state().last_turn_result == "interrupted"

    scheduler.advance_to(1.4)
    session.on_snapshot(_CLAUDE_OVERLAPPING_ACTIVE_DRAFT_SURFACE)
    state = session.current_state()

    assert state.turn_phase == "active"
    assert state.surface_editing_input == "yes"
    assert state.last_turn_result == "none"
    assert state.last_turn_source == "none"
