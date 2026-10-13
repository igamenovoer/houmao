from __future__ import annotations

from reactivex.testing import TestScheduler

from houmao.shared_tui_tracking import TrackerConfig, TuiTrackerSession
from houmao.shared_tui_tracking.apps.claude_code.profile import (
    ClaudeCodeSignalDetectorV2_1_X,
)


_CLAUDE_RULE = "────────────────────────────────────────────────────────────────"
_CLAUDE_BUSY_FOOTER = "  ⏵⏵ bypass permissions on (shift+tab to cycle) · esc to interrupt"
_CLAUDE_IDLE_FOOTER = "  ⏵⏵ bypass permissions on (shift+tab to cycle)"
_CLAUDE_GHOST_STYLE = "\x1b[38;5;246m❯ \x1b[7m\x1b[39mP\x1b[0;2m"

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
_CLAUDE_GHOST_SUGGESTION_READY_SURFACE = (
    "\x1b[38;5;244m────────────────────────────────────────────────────────────────\n"
    "\x1b[38;5;239m\x1b[48;5;237m❯ \x1b[38;5;231mReview the latest mailbox item\x1b[39m\n"
    "\x1b[38;5;244m────────────────────────────────────────────────────────────────\n"
    "\x1b[39m  \x1b[38;5;211m⏵⏵ bypass permissions on\x1b[38;5;246m (shift+tab to cycle)\x1b[39m\n"
)
_CLAUDE_ACTIVE_SURFACE = (
    "❯ explain the repository carefully\n\n"
    "✢ Unfurling…\n\n"
    f"{_CLAUDE_RULE}\n"
    "❯\n"
    f"{_CLAUDE_RULE}\n"
    f"{_CLAUDE_BUSY_FOOTER}\n"
)
_CLAUDE_SUFFIXLESS_SPINNER_SURFACE = (
    "❯ explain the repository carefully\n\n"
    "✻ Cerebrating… \n\n"
    f"{_CLAUDE_RULE}\n"
    "❯\n"
    f"{_CLAUDE_RULE}\n"
    f"{_CLAUDE_BUSY_FOOTER}\n"
)
_CLAUDE_SUCCESS_SURFACE = (
    f"● READY\n\n✻ Worked for 3s\n\n{_CLAUDE_RULE}\n❯\n{_CLAUDE_RULE}\n{_CLAUDE_IDLE_FOOTER}\n"
)
_CLAUDE_SUCCESS_SURFACE_MINUTES = (
    "❯ explain the repository carefully\n\n"
    "● Detailed explanation follows.\n\n"
    "✻ Cogitated for 1m 16s\n\n"
    f"{_CLAUDE_RULE}\n"
    "❯\n"
    f"{_CLAUDE_RULE}\n"
    f"{_CLAUDE_IDLE_FOOTER}\n"
)
_CLAUDE_SUCCESS_SURFACE_WITH_TIP = (
    "● READY\n\n"
    "✻ Worked for 3s\n\n"
    "Tip: run /doctor to check your setup\n\n"
    f"{_CLAUDE_RULE}\n"
    "❯\n"
    f"{_CLAUDE_RULE}\n"
    f"{_CLAUDE_IDLE_FOOTER}\n"
)
_CLAUDE_STALE_DOCK_ACTIVE_SURFACE = (
    "❯ first prompt\n\n"
    "● First answer.\n\n"
    "✻ Worked for 3s\n\n"
    "❯ second prompt\n\n"
    "✢ Unfurling…\n\n"
    f"{_CLAUDE_RULE}\n"
    "❯\n"
    f"{_CLAUDE_RULE}\n"
    f"{_CLAUDE_BUSY_FOOTER}\n"
)
_CLAUDE_OLD_DOCK_READY_SURFACE = (
    "❯ Review the mailbox continuation request\n\n"
    "● Reading story/02-see-it-properly.md\n"
    "  ⎿ Read 152 lines\n\n"
    "─ Worked for 1m 16s ─────────────────────────────────────────────\n\n"
    "The review file is written.\n\n"
    f"{_CLAUDE_RULE}\n"
    "❯\n"
    f"{_CLAUDE_RULE}\n"
    f"{_CLAUDE_IDLE_FOOTER}\n"
)
_CLAUDE_INTERRUPTED_READY_SURFACE = (
    "❯ Explain reducer semantics carefully\n"
    "  ⎿ Interrupted · What should Claude do instead?\n\n"
    f"{_CLAUDE_RULE}\n"
    "❯\n"
    f"{_CLAUDE_RULE}\n"
    f"{_CLAUDE_IDLE_FOOTER}\n"
)
_CLAUDE_USER_REJECTED_READY_SURFACE = (
    "❯ Explain the plan\n"
    "  ⎿ User rejected the proposed plan\n\n"
    f"{_CLAUDE_RULE}\n"
    "❯\n"
    f"{_CLAUDE_RULE}\n"
    f"{_CLAUDE_IDLE_FOOTER}\n"
)
_CLAUDE_INTERRUPTED_READY_WITH_DRAFT_SURFACE = (
    "❯ Explain reducer semantics carefully\n"
    "  ⎿ Interrupted · What should Claude do instead?\n\n"
    f"{_CLAUDE_RULE}\n"
    "\x1b[39m❯ Review staged change\x1b[7ms\x1b[0m\n"
    f"{_CLAUDE_RULE}\n"
    f"{_CLAUDE_IDLE_FOOTER}\n"
)
_CLAUDE_RESTORED_DRAFT_IDLE_SURFACE = (
    "❯ Explain reducer semantics carefully\n\n"
    f"{_CLAUDE_RULE}\n"
    "❯ Explain reducer semantics carefully\n"
    f"{_CLAUDE_RULE}\n"
    f"{_CLAUDE_IDLE_FOOTER}\n"
)
_CLAUDE_OVERLAPPING_ACTIVE_DRAFT_SURFACE = (
    "❯ Explain reducer semantics carefully\n\n"
    "✢ Unfurling…\n\n"
    f"{_CLAUDE_RULE}\n"
    "\x1b[39m❯ Review staged change\x1b[7ms\x1b[0m\n"
    f"{_CLAUDE_RULE}\n"
    f"{_CLAUDE_BUSY_FOOTER}\n"
)
_CLAUDE_SLASH_MENU_BLINK_SURFACE = (
    "❯ explain the repository carefully\n\n"
    "  /model - pick a model\n"
    "  /mode - pick a mode\n\n"
    f"{_CLAUDE_RULE}\n"
    "❯ /mod\n"
    f"{_CLAUDE_RULE}\n"
    f"{_CLAUDE_IDLE_FOOTER}\n"
)
_CLAUDE_PICKER_MODAL_SURFACE = (
    "Select model\n\n"
    "❯ 1. Sonnet 4.5\n"
    "  2. Opus 4.5\n\n"
    "▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔\n"
)
_CLAUDE_TRUST_MODAL_SURFACE = (
    "Quick safety check\n\n"
    "❯ 1. Yes, I trust this folder\n"
    "  2. No, quit\n\n"
    "▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔\n"
)
_CLAUDE_APPROVAL_MODAL_SURFACE = (
    "❯ Bash(ls -la)\n\n"
    "Do you want to proceed?\n\n"
    "❯ 1. Yes\n"
    "  2. No\n\n"
    "  esc to cancel · tab to amend\n"
)
_CLAUDE_PICKER_DISMISSED_IDLE_SURFACE = (
    f"❯ /model\n\n{_CLAUDE_RULE}\n❯\n{_CLAUDE_RULE}\n{_CLAUDE_IDLE_FOOTER}\n"
)
_CLAUDE_NO_COMPOSER_SURFACE = "✢ Working…\n\n  esc to interrupt\n"


def _claude_queue_placeholder_surface(*, queued: bool) -> str:
    """Build one busy 2.1.296 surface with or without the queued placeholder."""

    composer = "\x1b[39m❯\xa0\x1b[7m \x1b[0m"
    if queued:
        composer = f"{_CLAUDE_GHOST_STYLE}ress up to edit queued messages\x1b[0m"
    return (
        "❯ Run the active task.\n\n"
        "✢ Working…\n\n"
        f"{_CLAUDE_RULE}\n"
        f"{composer}\n"
        f"{_CLAUDE_RULE}\n"
        f"{_CLAUDE_BUSY_FOOTER}\n"
    )


def _claude_session(*, scheduler: TestScheduler) -> TuiTrackerSession:
    return TuiTrackerSession.from_config(
        app_id="claude_code",
        observed_version="2.1.296 (Claude Code)",
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
    assert state.surface_pending_input == "no"


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


def test_claude_pending_input_reads_queued_composer_placeholder() -> None:
    detector = ClaudeCodeSignalDetectorV2_1_X()

    queued = detector.detect(output_text=_claude_queue_placeholder_surface(queued=True))
    empty = detector.detect(output_text=_claude_queue_placeholder_surface(queued=False))

    assert queued.pending_input == "yes"
    assert empty.pending_input == "no"


def test_claude_pending_input_blocks_missing_composer() -> None:
    detector = ClaudeCodeSignalDetectorV2_1_X()

    signals = detector.detect(output_text=_CLAUDE_NO_COMPOSER_SURFACE)

    assert signals.prompt_visible is False
    assert signals.pending_input == "no"
    assert signals.accepting_input == "no"
    assert signals.ready_posture == "no"
    assert "prompt_missing_blocked" in signals.notes


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


def test_claude_detector_matches_verb_dock_completion() -> None:
    detector = ClaudeCodeSignalDetectorV2_1_X()

    seconds = detector.detect(output_text=_CLAUDE_SUCCESS_SURFACE)
    minutes = detector.detect(output_text=_CLAUDE_SUCCESS_SURFACE_MINUTES)

    assert seconds.completion_marker is not None
    assert seconds.success_candidate is True
    assert minutes.completion_marker is not None
    assert minutes.success_candidate is True


def test_claude_detector_ignores_pre_296_dock_format() -> None:
    detector = ClaudeCodeSignalDetectorV2_1_X()

    signals = detector.detect(output_text=_CLAUDE_OLD_DOCK_READY_SURFACE)

    assert signals.completion_marker is None
    assert signals.success_candidate is True


def test_claude_detector_scopes_completion_to_latest_turn_region() -> None:
    detector = ClaudeCodeSignalDetectorV2_1_X()

    signals = detector.detect(output_text=_CLAUDE_STALE_DOCK_ACTIVE_SURFACE)

    assert signals.completion_marker is None
    assert signals.active_evidence is True
    assert signals.success_candidate is False


def test_claude_detector_asserts_not_ready_while_busy() -> None:
    detector = ClaudeCodeSignalDetectorV2_1_X()

    signals = detector.detect(output_text=_CLAUDE_ACTIVE_SURFACE)

    assert signals.active_evidence is True
    assert signals.ready_posture == "no"
    assert signals.footer_interruptable is True


def test_claude_detector_matches_suffixless_spinner() -> None:
    detector = ClaudeCodeSignalDetectorV2_1_X()

    signals = detector.detect(output_text=_CLAUDE_SUFFIXLESS_SPINNER_SURFACE)

    assert signals.active_evidence is True
    assert "thinking_line" in signals.active_reasons


def test_claude_detector_matches_user_rejected_interrupt() -> None:
    detector = ClaudeCodeSignalDetectorV2_1_X()

    signals = detector.detect(output_text=_CLAUDE_USER_REJECTED_READY_SURFACE)

    assert signals.interrupted is True
    assert signals.ready_posture == "yes"


def test_claude_detector_shields_trust_dialog() -> None:
    detector = ClaudeCodeSignalDetectorV2_1_X()

    signals = detector.detect(output_text=_CLAUDE_TRUST_MODAL_SURFACE)

    assert signals.accepting_input == "no"
    assert signals.editing_input == "no"
    assert signals.ready_posture == "no"
    assert signals.pending_input == "no"
    assert signals.active_evidence is False
    assert signals.active_reasons == ()
    assert signals.ambiguous_interactive_surface is True
    assert "modal_2_1_296" in signals.notes


def test_claude_detector_shields_approval_panel() -> None:
    detector = ClaudeCodeSignalDetectorV2_1_X()

    signals = detector.detect(output_text=_CLAUDE_APPROVAL_MODAL_SURFACE)

    assert signals.accepting_input == "no"
    assert signals.editing_input == "no"
    assert signals.ready_posture == "no"
    assert signals.pending_input == "no"
    assert signals.active_evidence is False
    assert signals.ambiguous_interactive_surface is True


def test_claude_detector_shields_model_picker() -> None:
    detector = ClaudeCodeSignalDetectorV2_1_X()

    signals = detector.detect(output_text=_CLAUDE_PICKER_MODAL_SURFACE)

    assert signals.accepting_input == "no"
    assert signals.editing_input == "no"
    assert signals.ready_posture == "no"
    assert signals.pending_input == "no"
    assert signals.active_evidence is False
    assert signals.ambiguous_interactive_surface is True


def test_claude_detector_refuses_success_while_editing() -> None:
    detector = ClaudeCodeSignalDetectorV2_1_X()
    surface = _CLAUDE_SUCCESS_SURFACE.replace("❯\n", "❯ Review staged changes\n")

    signals = detector.detect(output_text=surface)

    assert signals.completion_marker is not None
    assert signals.editing_input == "yes"
    assert signals.success_candidate is False


def test_claude_signature_ignores_furniture_churn() -> None:
    detector = ClaudeCodeSignalDetectorV2_1_X()

    plain = detector.detect(output_text=_CLAUDE_SUCCESS_SURFACE)
    tipped = detector.detect(output_text=_CLAUDE_SUCCESS_SURFACE_WITH_TIP)

    assert plain.surface_signature == tipped.surface_signature


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


def test_claude_session_settles_success_with_verb_dock() -> None:
    scheduler = TestScheduler()
    session = _claude_session(scheduler=scheduler)

    scheduler.advance_to(1.0)
    session.on_snapshot(_CLAUDE_ACTIVE_SURFACE)
    scheduler.advance_to(1.4)
    session.on_snapshot(_CLAUDE_SUCCESS_SURFACE)

    assert session.current_state().last_turn_result == "none"

    scheduler.advance_to(2.6)
    settled = session.current_state()

    assert settled.last_turn_result == "success"
    assert settled.turn_phase == "ready"


def test_claude_session_infers_silent_abort_and_preserves_outcome_across_draft() -> None:
    scheduler = TestScheduler()
    session = _claude_session(scheduler=scheduler)

    scheduler.advance_to(1.0)
    session.on_snapshot(_CLAUDE_ACTIVE_SURFACE)

    assert session.current_state().turn_phase == "active"

    scheduler.advance_to(1.2)
    session.on_snapshot(_CLAUDE_RESTORED_DRAFT_IDLE_SURFACE)
    state = session.current_state()

    assert state.last_turn_result == "interrupted"
    assert state.surface_editing_input == "yes"
    assert state.turn_phase == "ready"

    scheduler.advance_to(1.4)
    session.on_snapshot(_CLAUDE_RESTORED_DRAFT_IDLE_SURFACE)
    held = session.current_state()

    assert held.last_turn_result == "interrupted"
    assert held.surface_editing_input == "yes"


def test_claude_session_carries_busy_evidence_across_slash_menu_blink() -> None:
    scheduler = TestScheduler()
    session = _claude_session(scheduler=scheduler)

    scheduler.advance_to(1.0)
    session.on_snapshot(_CLAUDE_ACTIVE_SURFACE)
    scheduler.advance_to(1.2)
    session.on_snapshot(_CLAUDE_SLASH_MENU_BLINK_SURFACE)
    state = session.current_state()

    assert state.turn_phase == "active"
    assert state.surface_ready_posture == "no"
    assert "busy_evidence_blink_carry" in state.active_reasons


def test_claude_session_restores_interrupted_after_picker_dismissal() -> None:
    scheduler = TestScheduler()
    session = _claude_session(scheduler=scheduler)

    scheduler.advance_to(1.0)
    session.on_snapshot(_CLAUDE_USER_REJECTED_READY_SURFACE)

    assert session.current_state().last_turn_result == "interrupted"

    scheduler.advance_to(1.2)
    session.on_snapshot(_CLAUDE_PICKER_MODAL_SURFACE)
    modal_state = session.current_state()

    assert modal_state.turn_phase == "unknown"
    assert modal_state.surface_accepting_input == "no"

    scheduler.advance_to(1.4)
    session.on_snapshot(_CLAUDE_PICKER_DISMISSED_IDLE_SURFACE)
    restored = session.current_state()

    assert restored.last_turn_result == "interrupted"


def test_claude_session_draft_editing_preserves_interrupted_outcome() -> None:
    scheduler = TestScheduler()
    session = _claude_session(scheduler=scheduler)

    scheduler.advance_to(1.0)
    session.on_snapshot(_CLAUDE_INTERRUPTED_READY_SURFACE)

    assert session.current_state().last_turn_result == "interrupted"

    scheduler.advance_to(1.4)
    session.on_snapshot(_CLAUDE_TYPED_DRAFT_READY_SURFACE)
    state = session.current_state()

    assert state.turn_phase == "ready"
    assert state.surface_editing_input == "yes"
    assert state.last_turn_result == "interrupted"
    assert state.last_turn_source != "none"


def test_claude_session_second_active_turn_clears_interrupted_outcome() -> None:
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


def test_claude_session_explicit_input_clears_settled_success() -> None:
    scheduler = TestScheduler()
    session = _claude_session(scheduler=scheduler)

    scheduler.advance_to(1.0)
    session.on_snapshot(_CLAUDE_ACTIVE_SURFACE)
    scheduler.advance_to(1.4)
    session.on_snapshot(_CLAUDE_SUCCESS_SURFACE)
    scheduler.advance_to(2.6)

    assert session.current_state().last_turn_result == "success"

    session.on_input_submitted()
    state = session.current_state()

    assert state.turn_phase == "active"
    assert state.last_turn_result == "none"
    assert state.last_turn_source == "none"
