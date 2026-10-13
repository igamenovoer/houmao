"""Codex 0.162.x TUI detector and tracker-session behavior tests.

Fixtures follow the 0.162.1 surface shapes captured in the 2026-10-12 debug
campaign's frozen recordings (`tmp/houmao-dev-tui-testing/2026-10-12-codex-*`):
transcript echoes render as `› <text>` above the composer, the composer is a
bold-`›` dim-placeholder line, the footer carries the model line
`<model> · <workdir>`, and the completion dock renders `Worked for Ns • HH:MM`
with no box-drawing prefix.
"""

from __future__ import annotations

from reactivex.testing import TestScheduler

from houmao.shared_tui_tracking import TrackerConfig, TuiTrackerSession, app_id_from_tool
from houmao.shared_tui_tracking.apps.codex_tui.profile import (
    CodexTuiSignalDetector,
    CodexTuiSignalDetectorV0_162_X,
)


_CODEX_COMPOSER_PLACEHOLDER = "\x1b[1m›\x1b[0m \x1b[2mAsk Codex to do anything\x1b[0m"
_CODEX_COMPOSER_EMPTY = "\x1b[1m›\x1b[0m"
_CODEX_FOOTER = "  GPT-6.1-Sol medium · /tmp/demo/workdir\n  ? for shortcuts"


def _codex_surface(*cells: str, composer: str | None = _CODEX_COMPOSER_PLACEHOLDER) -> str:
    """Assemble one 0.162.x-shaped surface from transcript cells plus composer/footer."""

    parts = [cell for cell in cells if cell]
    if composer is not None:
        parts.append(composer)
    parts.append(_CODEX_FOOTER)
    return "\n\n".join(parts) + "\n"


_CODEX_READY_SURFACE = _codex_surface(
    "• Here is the summary.",
    "  Worked for 3s • 2:09 PM",
)
_CODEX_ACTIVE_SURFACE = _codex_surface(
    "› Summarize the repository layout",
    "• Working (3s • esc to interrupt)",
)
_CODEX_ACTIVE_SURFACE_SECOND_TURN = _codex_surface(
    "› Summarize the repository layout",
    "■ Conversation interrupted - use /feedback if something went wrong",
    "› Now summarize the terminal recording flow",
    "• Working (0s • esc to interrupt)",
)
_CODEX_COMPACTION_SURFACE = _codex_surface(
    "› Summarize the repository layout",
    "• Compacting context (3s • esc to interrupt)",
)
_CODEX_COMPACTION_DONE_SURFACE = _codex_surface(
    "• Here is the compacted context summary.",
    "  Worked for 8s • 2:13 PM",
)
_CODEX_INTERRUPTED_SURFACE = _codex_surface(
    "› Summarize the repository layout",
    "• Partial answer text",
    "■ Conversation interrupted - use /feedback if something went wrong",
)
_CODEX_TYPED_DRAFT_SURFACE = _codex_surface(
    composer="\x1b[1m›\x1b[0m Find and fix a bug in @filename",
)
_CODEX_INTERRUPTED_READY_WITH_DRAFT_SURFACE = _codex_surface(
    "› Summarize the repository layout",
    "■ Conversation interrupted - use /feedback if something went wrong",
    composer="\x1b[1m›\x1b[0m Now summarize the terminal recording flow",
)
_CODEX_STALE_INTERRUPTED_SCROLLBACK_WITH_SUCCESS_SURFACE = _codex_surface(
    "› Summarize the repository layout",
    "■ Conversation interrupted - use /feedback if something went wrong",
    "› Reply with the single word RECOVERED and stop",
    "• RECOVERED",
    "  Worked for 2s • 2:30 PM",
)
_CODEX_DIM_PLACEHOLDER_READY_SURFACE = _codex_surface(
    "  Worked for 3s • 2:09 PM",
)
_CODEX_DISABLED_INPUT_SURFACE = _codex_surface(
    composer="\x1b[2m› Input disabled for test.\x1b[0m",
)
_CODEX_UNRECOGNIZED_STYLED_PROMPT_SURFACE = _codex_surface(
    composer="\x1b[1m›\x1b[0m \x1b[33mReview staged changes\x1b[0m",
)
_CODEX_QUEUED_ECHO_SURFACE = _codex_surface(
    "› Read every Python file under boltons",
    "• I’ll read every Python file directly under boltons/ and map the modules.",
    "› Check the remaining test coverage next",
    "• Working (8s • esc to interrupt)",
)
_CODEX_TURN_STARTING_ECHO_SURFACE = _codex_surface(
    "• 1 passed.",
    "  Worked for 11s • 2:12 PM",
    "› Check the remaining test coverage next",
    "• Working (0s • esc to interrupt)",
)
_CODEX_COLLAPSED_QUEUE_SURFACE = _codex_surface(
    "› Read every Python file under boltons",
    "• I’ll read every Python file directly under boltons/ and map the modules.",
    "  + 1 lines (^t to expand)",
    "• Working (25s • esc to interrupt)",
)
_CODEX_SETTLED_HISTORICAL_ECHO_SURFACE = _codex_surface(
    "› Read every Python file under boltons",
    "• Mapped 42 modules to representative public symbols.",
    "  Worked for 31s • 2:20 PM",
)
_CODEX_TRUST_SCREEN_SURFACE = (
    "  Trust this folder? Codex can read, edit, and run files here, subject to your settings.\n\n"
    "› 1. Trust and continue\n"
    "  2. Cancel\n\n"
    "  enter continue · esc back\n"
)
_CODEX_MODEL_SELECTOR_SURFACE = (
    "  Select Model and Effort\n\n"
    "› 1. GPT-6.1-Sol medium (current)  Balanced agentic coding model.\n"
    "  2. GPT-6.1-Sol high              Stronger reasoning model.\n\n"
    "  enter select · esc back\n"
)
_CODEX_LEGACY_MODEL_SELECTOR_SURFACE = (
    "  Select Model and Effort\n\n"
    "› 1. GPT-6.1-Sol medium (current)  Balanced agentic coding model.\n"
    "  2. GPT-6.1-Sol high              Stronger reasoning model.\n\n"
    "  Press enter to confirm or esc to go back\n"
)
_CODEX_WARNINGS_SCREEN_SURFACE = (
    "  Warnings · 1 of 1 · Startup\n\n"
    "  MCP startup incomplete (failed: alpha)\n\n"
    "  k keep & next · esc dismiss & close\n"
)
_CODEX_SEND_INPUT_DIALOG_SURFACE = (
    "  Would you like to send input to terminal 42?\n\n"
    "› 1. Yes, send the input\n"
    "  2. No\n\n"
    "  Press enter to confirm or esc to cancel\n"
)
_CODEX_APPROVAL_SURFACE = (
    "  Would you like to run the following command?\n\n"
    "  python -m pytest -q\n\n"
    "  Press enter to confirm or esc to cancel\n"
)
_CODEX_EXITED_SURFACE = (
    "To continue this session, run:\n"
    "  codex resume 01a12eba-3cb1-7422-9164-ba4e4a7acdf8\n"
    "Or run codex resume and select Report checkout status ST03-01.\n"
)
_CODEX_STARTUP_SPLASH_SURFACE = (
    "\x1b[1m›\x1b[0m \x1b[2mAsk Codex to do anything\x1b[0m\n  ? for shortcuts\n"
)
_CODEX_ERROR_SURFACE = _codex_surface(
    "■ Message exceeds the maximum length of 1048576 characters (1048577 provided).",
    composer=_CODEX_COMPOSER_EMPTY,
)
# Source-backed: `Error running remote compact task: ...` (codex-rs core tools
# tests) plus `stream disconnected before completion` (protocol/src/error.rs).
_CODEX_COMPACT_DEGRADED_SURFACE = _codex_surface(
    "■ Error running remote compact task: stream disconnected before completion.",
    composer=_CODEX_COMPOSER_EMPTY,
)
# Source-backed: `Codex ran out of room in the model's context window. ...`
# (codex-rs/protocol/src/error.rs).
_CODEX_CONTEXT_WINDOW_ERROR_SURFACE = _codex_surface(
    "■ Codex ran out of room in the model's context window. "
    "Start a new thread or clear earlier history before retrying.",
    composer=_CODEX_COMPOSER_EMPTY,
)
# Qualification-pending: server-emitted error text families (no 0.162.x
# client-side literal); synthetic fixtures built from the family tokens.
_CODEX_SERVER_ERROR_DEGRADED_SURFACE = _codex_surface(
    "■ Error running remote compact task: internal server error (500)",
    composer=_CODEX_COMPOSER_EMPTY,
)
_CODEX_UNKNOWN_PARAMETER_DEGRADED_SURFACE = _codex_surface(
    '■ Error running remote compact task: unsupported parameter "reasoning"',
    composer=_CODEX_COMPOSER_EMPTY,
)
_CODEX_WARNING_OVERLOADED_SURFACE = _codex_surface(
    "⚠ server overloaded",
    composer=_CODEX_COMPOSER_EMPTY,
)
_CODEX_WARNING_HIGH_DEMAND_SURFACE = _codex_surface(
    "⚠ We're currently experiencing high demand, which may cause temporary errors.",
    composer=_CODEX_COMPOSER_EMPTY,
)
# Source-backed live-edge reconnect forms (chatwidget/tests/status_and_layout.rs
# `Reconnecting... 2/5`; chatwidget/reconnect.rs `Reconnecting to server…`).
_CODEX_RETRY_STATUS_SURFACE = _codex_surface(
    "› Summarize the repository layout",
    "Reconnecting to model stream (2/5)",
)
_CODEX_RETRY_SERVER_STATUS_SURFACE = _codex_surface(
    "› Summarize the repository layout",
    "• Reconnecting to server… (4s)",
)
_CODEX_RETRY_DOTS_STATUS_SURFACE = _codex_surface(
    "› Summarize the repository layout",
    "Reconnecting... 2/5",
)
_CODEX_AMBIENT_WARNING_SURFACE = _codex_surface(
    "⚠ MCP startup incomplete (failed: alpha)",
)
_CODEX_PROMPT_ADJACENT_AUTH_ERROR_SURFACE = _codex_surface(
    "› Reply with exactly TRACKING_SMOKE_OK and nothing else.",
    "■ Your access token could not be refreshed because your",
)
_CODEX_STALE_COMPACT_ERROR_SCROLLBACK_SURFACE = _codex_surface(
    "› Summarize the inbox",
    "■ Error running remote compact task: stream disconnected before completion.",
    "› Reply with RECOVERED",
    "• RECOVERED",
    "  Worked for 2s • 2:31 PM",
)
_CODEX_STALE_WARNING_SCROLLBACK_SURFACE = _codex_surface(
    "› Ask for a status check",
    "⚠ server overloaded",
    "› Reply with RECOVERED",
    "• RECOVERED",
    "  Worked for 2s • 2:31 PM",
)
_CODEX_NON_ADJACENT_COMPACT_ERROR_SAME_TURN_SURFACE = _codex_surface(
    "› Investigate compact failures",
    "■ Error running remote compact task: stream disconnected before completion.",
    "• Later transcript text means the old error is not prompt-adjacent.",
    "• More transcript text keeps the live edge away from the old error.",
)
_CODEX_STALE_RESTART_SURFACE = (
    "OpenAI Codex (v0.162.1)\n"
    "\x1b[1m›\x1b[0m \x1b[2mAsk Codex to do anything\x1b[0m\n\n"
    "  GPT-6.1-Sol medium · /tmp/demo/workdir\n"
    "bash-5.2$ /tmp/codex-launch.sh\n"
)
_CODEX_FRESH_RESTART_SURFACE = (
    "bash-5.2$ /tmp/codex-launch.sh\n"
    "OpenAI Codex (v0.162.1)\n"
    "\x1b[1m›\x1b[0m \x1b[2mAsk Codex to do anything\x1b[0m\n\n"
    "  GPT-6.1-Sol medium · /tmp/demo/workdir\n"
)
_CODEX_TRANSCRIPT_GROWTH_START = _codex_surface(
    "› Write the release notes",
    "• Draft answer",
)
_CODEX_TRANSCRIPT_GROWTH_CONTINUES = _codex_surface(
    "› Write the release notes",
    "• Draft answer\n"
    "  continuing with a much longer explanation line that materially grows the turn\n"
    "  and a second line so the latest-turn region clearly keeps expanding",
)
_CODEX_NON_TURN_REDRAW_START = _codex_surface("  banner line one")
_CODEX_NON_TURN_REDRAW_GROWN = _codex_surface(
    "  banner line one\n"
    "  a second banner-style line that is long enough to clear the growth floor\n"
    "  and a third line so the region clearly changes shape"
)
_CODEX_BLINK_ACTIVE_SURFACE = _codex_surface(
    "› Summarize the repository layout",
    "• Partial answer text",
    "• Working (3s • esc to interrupt)",
)
_CODEX_BLINK_HIDDEN_SURFACE = _codex_surface(
    "› Summarize the repository layout",
    "• Partial answer text",
)


def _codex_session(*, scheduler: TestScheduler) -> TuiTrackerSession:
    return TuiTrackerSession.from_config(
        app_id="codex_tui",
        observed_version="0.162.1 (Codex)",
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
    assert "transcript_growth_undocked" in state.active_reasons


def test_codex_tui_sparse_window_does_not_infer_active() -> None:
    scheduler = TestScheduler()
    session = _codex_session(scheduler=scheduler)

    scheduler.advance_to(1.0)
    session.on_snapshot(_CODEX_TRANSCRIPT_GROWTH_START)
    scheduler.advance_to(4.5)
    session.on_snapshot(_CODEX_TRANSCRIPT_GROWTH_CONTINUES)

    state = session.current_state()

    assert state.turn_phase == "ready"
    assert "transcript_growth_undocked" not in state.active_reasons


def test_codex_tui_non_turn_redraw_does_not_manufacture_activity() -> None:
    scheduler = TestScheduler()
    session = _codex_session(scheduler=scheduler)

    scheduler.advance_to(1.0)
    session.on_snapshot(_CODEX_NON_TURN_REDRAW_START)
    scheduler.advance_to(1.5)
    session.on_snapshot(_CODEX_NON_TURN_REDRAW_GROWN)

    state = session.current_state()

    assert state.turn_phase == "ready"
    assert "transcript_growth_undocked" not in state.active_reasons


def test_codex_tui_docked_marker_ends_temporal_hints() -> None:
    scheduler = TestScheduler()
    session = _codex_session(scheduler=scheduler)

    scheduler.advance_to(1.0)
    session.on_snapshot(_CODEX_TRANSCRIPT_GROWTH_START)
    scheduler.advance_to(1.5)
    session.on_snapshot(_CODEX_TRANSCRIPT_GROWTH_CONTINUES)
    assert session.current_state().turn_phase == "active"

    scheduler.advance_to(2.0)
    session.on_snapshot(_CODEX_READY_SURFACE)

    state = session.current_state()
    assert state.turn_phase == "ready"


def test_codex_tui_status_row_blink_carries_active() -> None:
    scheduler = TestScheduler()
    session = _codex_session(scheduler=scheduler)

    scheduler.advance_to(1.0)
    session.on_snapshot(_CODEX_BLINK_ACTIVE_SURFACE)
    scheduler.advance_to(1.5)
    session.on_snapshot(_CODEX_BLINK_HIDDEN_SURFACE)

    state = session.current_state()

    assert state.turn_phase == "active"
    assert "status_row_blink_carry" in state.active_reasons

    scheduler.advance_to(3.0)
    session.on_snapshot(_CODEX_BLINK_HIDDEN_SURFACE)

    settled = session.current_state()
    assert settled.turn_phase == "ready"


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


def test_codex_tui_explicit_input_clears_stale_success() -> None:
    scheduler = TestScheduler()
    session = _codex_session(scheduler=scheduler)

    scheduler.advance_to(1.0)
    session.on_snapshot(_CODEX_ACTIVE_SURFACE)
    scheduler.advance_to(1.3)
    session.on_snapshot(_CODEX_READY_SURFACE)
    scheduler.advance_to(2.6)

    assert session.current_state().last_turn_result == "success"

    session.on_input_submitted()
    state = session.current_state()

    assert state.turn_phase == "active"
    assert state.last_turn_result == "none"
    assert state.last_turn_source == "none"


def test_codex_tui_visible_draft_preserves_stale_success() -> None:
    scheduler = TestScheduler()
    session = _codex_session(scheduler=scheduler)

    scheduler.advance_to(1.0)
    session.on_snapshot(_CODEX_ACTIVE_SURFACE)
    scheduler.advance_to(1.3)
    session.on_snapshot(_CODEX_READY_SURFACE)
    scheduler.advance_to(2.6)

    settled = session.current_state()
    assert settled.last_turn_result == "success"

    scheduler.advance_to(2.8)
    session.on_snapshot(_CODEX_TYPED_DRAFT_SURFACE)
    state = session.current_state()

    assert state.turn_phase == "ready"
    assert state.surface_editing_input == "yes"
    assert state.last_turn_result == settled.last_turn_result
    assert state.last_turn_source == settled.last_turn_source


def test_codex_tui_visible_draft_preserves_success_after_settle_window() -> None:
    scheduler = TestScheduler()
    session = _codex_session(scheduler=scheduler)

    scheduler.advance_to(1.0)
    session.on_snapshot(_CODEX_ACTIVE_SURFACE)
    scheduler.advance_to(1.3)
    session.on_snapshot(_CODEX_READY_SURFACE)
    scheduler.advance_to(2.6)

    settled = session.current_state()
    assert settled.last_turn_result == "success"

    scheduler.advance_to(2.8)
    session.on_snapshot(_CODEX_TYPED_DRAFT_SURFACE)
    scheduler.advance_to(4.2)
    state = session.current_state()

    assert state.turn_phase == "ready"
    assert state.surface_editing_input == "yes"
    assert state.last_turn_result == settled.last_turn_result
    assert state.last_turn_source == settled.last_turn_source


def test_codex_tui_visible_draft_preserves_stale_interrupted_result() -> None:
    scheduler = TestScheduler()
    session = _codex_session(scheduler=scheduler)

    scheduler.advance_to(1.0)
    session.on_snapshot(_CODEX_ACTIVE_SURFACE)
    scheduler.advance_to(1.4)
    session.on_snapshot(_CODEX_INTERRUPTED_SURFACE)

    assert session.current_state().last_turn_result == "interrupted"

    scheduler.advance_to(1.8)
    session.on_snapshot(_CODEX_TYPED_DRAFT_SURFACE)
    state = session.current_state()

    assert state.turn_phase == "ready"
    assert state.surface_editing_input == "yes"
    assert state.last_turn_result == "interrupted"
    assert state.last_turn_source != "none"


def test_codex_tui_visible_draft_preserves_interrupted_outcome_with_stale_interrupt_signal() -> (
    None
):
    scheduler = TestScheduler()
    session = _codex_session(scheduler=scheduler)

    scheduler.advance_to(1.0)
    session.on_snapshot(_CODEX_ACTIVE_SURFACE)
    scheduler.advance_to(1.4)
    session.on_snapshot(_CODEX_INTERRUPTED_SURFACE)

    assert session.current_state().last_turn_result == "interrupted"

    scheduler.advance_to(1.8)
    session.on_snapshot(_CODEX_INTERRUPTED_READY_WITH_DRAFT_SURFACE)
    state = session.current_state()

    assert state.turn_phase == "ready"
    assert state.surface_editing_input == "yes"
    assert state.last_turn_result == "interrupted"
    assert state.last_turn_source != "none"

    scheduler.advance_to(2.0)
    session.on_snapshot(_CODEX_INTERRUPTED_READY_WITH_DRAFT_SURFACE)
    repeated = session.current_state()

    assert repeated.turn_phase == "ready"
    assert repeated.surface_editing_input == "yes"
    assert repeated.last_turn_result == "interrupted"
    assert repeated.last_turn_source != "none"


def test_codex_tui_second_active_turn_clears_stale_interrupted_result() -> None:
    scheduler = TestScheduler()
    session = _codex_session(scheduler=scheduler)

    scheduler.advance_to(1.0)
    session.on_snapshot(_CODEX_ACTIVE_SURFACE)
    scheduler.advance_to(1.4)
    session.on_snapshot(_CODEX_INTERRUPTED_SURFACE)

    assert session.current_state().last_turn_result == "interrupted"

    scheduler.advance_to(1.8)
    session.on_snapshot(_CODEX_ACTIVE_SURFACE_SECOND_TURN)
    state = session.current_state()

    assert state.turn_phase == "active"
    assert state.last_turn_result == "none"
    assert state.last_turn_source == "none"


def test_codex_detector_ignores_stale_interrupted_scrollback_above_current_success() -> None:
    detector = CodexTuiSignalDetector()

    signals = detector.detect(output_text=_CODEX_STALE_INTERRUPTED_SCROLLBACK_WITH_SUCCESS_SURFACE)

    assert signals.interrupted is False
    assert signals.ready_posture == "yes"
    assert signals.active_evidence is False
    assert signals.success_candidate is True
    assert signals.chat_context == "current"


def test_codex_detector_visible_draft_does_not_count_as_success_candidate() -> None:
    detector = CodexTuiSignalDetector()

    signals = detector.detect(output_text=_CODEX_TYPED_DRAFT_SURFACE)

    assert signals.editing_input == "yes"
    assert signals.success_candidate is False
    assert signals.chat_context == "current"


def test_codex_tui_stale_interrupted_scrollback_does_not_block_final_success() -> None:
    scheduler = TestScheduler()
    session = _codex_session(scheduler=scheduler)

    scheduler.advance_to(1.0)
    session.on_snapshot(_CODEX_ACTIVE_SURFACE)
    scheduler.advance_to(1.4)
    session.on_snapshot(_CODEX_INTERRUPTED_SURFACE)

    assert session.current_state().last_turn_result == "interrupted"

    scheduler.advance_to(1.8)
    session.on_snapshot(_CODEX_ACTIVE_SURFACE_SECOND_TURN)

    active = session.current_state()
    assert active.turn_phase == "active"
    assert active.last_turn_result == "none"
    assert active.last_turn_source == "none"

    scheduler.advance_to(5.4)
    session.on_snapshot(_CODEX_STALE_INTERRUPTED_SCROLLBACK_WITH_SUCCESS_SURFACE)

    candidate = session.current_state()
    assert candidate.turn_phase == "ready"
    assert candidate.last_turn_result == "none"
    assert candidate.last_turn_source == "none"

    scheduler.advance_to(6.6)
    settled = session.current_state()

    assert settled.last_turn_result == "success"
    assert settled.last_turn_source == "surface_inference"


def test_codex_tui_dim_placeholder_does_not_count_as_editing() -> None:
    detector = CodexTuiSignalDetector()

    signals = detector.detect(output_text=_CODEX_DIM_PLACEHOLDER_READY_SURFACE)

    assert signals.accepting_input == "yes"
    assert signals.editing_input == "no"
    assert signals.prompt_text is None


def test_codex_tui_literal_placeholder_phrase_still_counts_as_user_editing() -> None:
    detector = CodexTuiSignalDetector()

    signals = detector.detect(output_text=_CODEX_TYPED_DRAFT_SURFACE)

    assert signals.accepting_input == "yes"
    assert signals.editing_input == "yes"
    assert signals.prompt_text == "Find and fix a bug in @filename"


def test_codex_tui_disabled_input_placeholder_stays_non_editing() -> None:
    detector = CodexTuiSignalDetector()

    signals = detector.detect(output_text=_CODEX_DISABLED_INPUT_SURFACE)

    assert signals.accepting_input == "yes"
    assert signals.editing_input == "no"
    assert signals.prompt_text is None


def test_codex_tui_unrecognized_styled_prompt_degrades_to_unknown_editing() -> None:
    detector = CodexTuiSignalDetector()

    signals = detector.detect(output_text=_CODEX_UNRECOGNIZED_STYLED_PROMPT_SURFACE)

    assert signals.accepting_input == "yes"
    assert signals.editing_input == "unknown"
    assert signals.prompt_text is None
    assert "unrecognized_prompt_presentation" in signals.notes
    assert "prompt_behavior_variant=0.162.x" in signals.notes


def test_codex_0_162_detector_tracks_current_collaboration_wait_until_finished() -> None:
    detector = CodexTuiSignalDetectorV0_162_X()
    waiting = _codex_surface(
        "• Spawned Robie [explorer] (gpt-6.1-sol medium)",
        "• Waiting for Robie [explorer]",
    )
    finished = _codex_surface(
        "• Waiting for Robie [explorer]",
        "• Finished waiting\n  └ Robie [explorer]: Completed - Done",
        "  Worked for 21s • 2:40 PM",
    )

    waiting_signals = detector.detect(output_text=waiting)
    finished_signals = detector.detect(output_text=finished)

    assert waiting_signals.active_evidence is True
    assert "collaboration_cell" in waiting_signals.active_reasons
    assert waiting_signals.ready_posture == "no"
    assert finished_signals.active_evidence is False
    assert finished_signals.ready_posture == "yes"
    assert "prompt_behavior_variant=0.162.x" in finished_signals.notes


def test_codex_0_162_response_supersedes_stale_working_row() -> None:
    detector = CodexTuiSignalDetectorV0_162_X()
    surface = _codex_surface(
        "› Reply with READY.",
        "• Working (1s • esc to interrupt)",
        "• READY",
        "  Worked for 1s • 2:41 PM",
        composer="\x1b[1m›\x1b[0m Implement {feature}",
    )

    signals = detector.detect(output_text=surface)

    assert signals.active_evidence is False
    assert signals.ready_posture == "yes"


def test_codex_detector_compaction_status_row_is_busy_with_maintenance_reason() -> None:
    detector = CodexTuiSignalDetectorV0_162_X()

    signals = detector.detect(output_text=_CODEX_COMPACTION_SURFACE)

    assert signals.active_evidence is True
    assert "compaction_status" in signals.active_reasons
    assert "status_row" not in signals.active_reasons
    assert signals.footer_interruptable is True
    assert signals.ready_posture == "no"


def test_codex_tui_compaction_after_interrupt_preserves_interrupted_result() -> None:
    scheduler = TestScheduler()
    session = _codex_session(scheduler=scheduler)

    scheduler.advance_to(1.0)
    session.on_snapshot(_CODEX_ACTIVE_SURFACE)
    scheduler.advance_to(1.4)
    session.on_snapshot(_CODEX_INTERRUPTED_SURFACE)

    assert session.current_state().last_turn_result == "interrupted"

    scheduler.advance_to(2.0)
    session.on_snapshot(_CODEX_COMPACTION_SURFACE)
    compaction_state = session.current_state()

    assert compaction_state.turn_phase == "active"
    assert compaction_state.last_turn_result == "interrupted"
    assert "compaction_status" in compaction_state.active_reasons

    scheduler.advance_to(5.0)
    session.on_snapshot(_CODEX_COMPACTION_DONE_SURFACE)
    scheduler.advance_to(7.0)
    settled = session.current_state()

    assert settled.turn_phase == "ready"
    assert settled.last_turn_result == "interrupted"

    scheduler.advance_to(8.0)
    session.on_snapshot(_CODEX_ACTIVE_SURFACE)
    state = session.current_state()

    assert state.turn_phase == "active"
    assert state.last_turn_result == "none"
    assert state.last_turn_source == "none"


def test_codex_tui_compaction_after_success_neither_clears_nor_resettles() -> None:
    scheduler = TestScheduler()
    session = _codex_session(scheduler=scheduler)

    scheduler.advance_to(1.0)
    session.on_snapshot(_CODEX_ACTIVE_SURFACE)
    scheduler.advance_to(1.3)
    session.on_snapshot(_CODEX_READY_SURFACE)
    scheduler.advance_to(2.6)

    assert session.current_state().last_turn_result == "success"
    session.drain_events()

    scheduler.advance_to(3.0)
    session.on_snapshot(_CODEX_COMPACTION_SURFACE)
    scheduler.advance_to(5.0)
    session.on_snapshot(_CODEX_COMPACTION_DONE_SURFACE)
    scheduler.advance_to(7.0)

    state = session.current_state()
    events = session.drain_events()

    assert state.last_turn_result == "success"
    assert all(event.last_turn_result != "none" for event in events)
    assert all(event.note != "success_settled" for event in events)


def test_codex_detector_queued_echo_marks_pending_and_active() -> None:
    detector = CodexTuiSignalDetectorV0_162_X()

    signals = detector.detect(output_text=_CODEX_QUEUED_ECHO_SURFACE)

    assert signals.pending_input == "yes"
    assert signals.active_evidence is True
    assert "queued_follow_up" in signals.active_reasons
    assert signals.ready_posture == "no"


def test_codex_detector_turn_starting_echo_is_not_pending_input() -> None:
    detector = CodexTuiSignalDetectorV0_162_X()

    signals = detector.detect(output_text=_CODEX_TURN_STARTING_ECHO_SURFACE)

    assert signals.pending_input == "no"
    assert signals.active_evidence is True
    assert "queued_follow_up" not in signals.active_reasons


def test_codex_detector_collapsed_queue_echo_has_no_pending_evidence() -> None:
    detector = CodexTuiSignalDetectorV0_162_X()

    signals = detector.detect(output_text=_CODEX_COLLAPSED_QUEUE_SURFACE)

    assert signals.pending_input == "no"
    assert signals.active_evidence is True
    assert "queued_follow_up" not in signals.active_reasons


def test_codex_detector_settled_historical_echo_is_not_pending_input() -> None:
    detector = CodexTuiSignalDetectorV0_162_X()

    signals = detector.detect(output_text=_CODEX_SETTLED_HISTORICAL_ECHO_SURFACE)

    assert signals.pending_input == "no"
    assert signals.ready_posture == "yes"


def test_codex_session_emits_pending_input_transitions_for_queued_echo() -> None:
    scheduler = TestScheduler()
    session = _codex_session(scheduler=scheduler)

    session.on_snapshot(_CODEX_ACTIVE_SURFACE)
    assert session.current_state().surface_pending_input == "no"
    session.drain_events()

    session.on_snapshot(_CODEX_QUEUED_ECHO_SURFACE)
    pending_events = session.drain_events()
    assert session.current_state().surface_pending_input == "yes"
    assert any(event.surface_pending_input == "yes" for event in pending_events)

    session.on_snapshot(_CODEX_ACTIVE_SURFACE)
    consumed_events = session.drain_events()
    assert session.current_state().surface_pending_input == "no"
    assert any(event.surface_pending_input == "no" for event in consumed_events)

    session.on_input_submitted()
    assert session.current_state().surface_pending_input == "no"


def test_codex_detector_trust_screen_blocks_admission() -> None:
    detector = CodexTuiSignalDetectorV0_162_X()

    signals = detector.detect(output_text=_CODEX_TRUST_SCREEN_SURFACE)

    assert signals.ambiguous_interactive_surface is True
    assert signals.accepting_input == "no"
    assert signals.editing_input == "no"
    assert signals.ready_posture == "no"
    assert signals.pending_input == "no"
    assert signals.active_evidence is False
    assert signals.success_candidate is False
    assert signals.success_blocked is True


def test_codex_detector_model_selector_blocks_admission_via_0_162_footer() -> None:
    detector = CodexTuiSignalDetectorV0_162_X()

    signals = detector.detect(output_text=_CODEX_MODEL_SELECTOR_SURFACE)

    assert signals.ambiguous_interactive_surface is True
    assert signals.accepting_input == "no"
    assert signals.editing_input == "no"
    assert signals.ready_posture == "no"
    assert signals.pending_input == "no"
    assert signals.active_evidence is False
    assert signals.success_candidate is False


def test_codex_detector_legacy_list_selection_footer_still_blocks() -> None:
    detector = CodexTuiSignalDetectorV0_162_X()

    signals = detector.detect(output_text=_CODEX_LEGACY_MODEL_SELECTOR_SURFACE)

    assert signals.ambiguous_interactive_surface is True
    assert signals.ready_posture == "no"


def test_codex_detector_warnings_screen_blocks_admission() -> None:
    detector = CodexTuiSignalDetectorV0_162_X()

    signals = detector.detect(output_text=_CODEX_WARNINGS_SCREEN_SURFACE)

    assert signals.ambiguous_interactive_surface is True
    assert signals.accepting_input == "no"
    assert signals.ready_posture == "no"
    assert signals.pending_input == "no"


def test_codex_detector_send_input_dialog_blocks_admission() -> None:
    detector = CodexTuiSignalDetectorV0_162_X()

    signals = detector.detect(output_text=_CODEX_SEND_INPUT_DIALOG_SURFACE)

    assert signals.ambiguous_interactive_surface is True
    assert signals.accepting_input == "no"
    assert signals.ready_posture == "no"
    assert signals.success_candidate is False


def test_codex_detector_exec_approval_blocks_admission() -> None:
    detector = CodexTuiSignalDetectorV0_162_X()

    signals = detector.detect(output_text=_CODEX_APPROVAL_SURFACE)

    assert signals.ambiguous_interactive_surface is True
    assert signals.accepting_input == "no"
    assert signals.ready_posture == "no"


def test_codex_tui_overlay_session_reports_blocked_posture() -> None:
    scheduler = TestScheduler()
    session = _codex_session(scheduler=scheduler)

    scheduler.advance_to(1.0)
    session.on_snapshot(_CODEX_APPROVAL_SURFACE)

    state = session.current_state()

    assert state.surface_accepting_input == "no"
    assert state.surface_ready_posture == "no"
    assert state.turn_phase == "unknown"
    assert state.chat_context == "current"


def test_codex_detector_exited_surface_without_composer_is_blocked() -> None:
    detector = CodexTuiSignalDetectorV0_162_X()

    signals = detector.detect(output_text=_CODEX_EXITED_SURFACE)

    assert signals.prompt_visible is False
    assert signals.accepting_input == "no"
    assert signals.editing_input == "no"
    assert signals.ready_posture == "no"


def test_codex_detector_startup_splash_blocks_until_footer_lands() -> None:
    detector = CodexTuiSignalDetectorV0_162_X()

    signals = detector.detect(output_text=_CODEX_STARTUP_SPLASH_SURFACE)

    assert signals.prompt_visible is True
    assert signals.accepting_input == "no"
    assert signals.editing_input == "no"
    assert signals.ready_posture == "no"
    assert signals.pending_input == "no"
    assert "startup_splash" in signals.notes


def test_codex_tui_generic_error_blocks_success_without_degrading_prompt_readiness() -> None:
    scheduler = TestScheduler()
    session = _codex_session(scheduler=scheduler)

    scheduler.advance_to(1.0)
    session.on_snapshot(_CODEX_ACTIVE_SURFACE)
    scheduler.advance_to(1.4)
    session.on_snapshot(_CODEX_ERROR_SURFACE)
    scheduler.advance_to(3.0)

    state = session.current_state()

    assert state.turn_phase == "ready"
    assert state.surface_accepting_input == "yes"
    assert state.surface_editing_input == "no"
    assert state.surface_ready_posture == "yes"
    assert state.last_turn_result == "none"
    assert state.chat_context == "current"


def test_codex_tui_prompt_ready_compact_error_marks_degraded_context() -> None:
    scheduler = TestScheduler()
    session = _codex_session(scheduler=scheduler)

    scheduler.advance_to(1.0)
    session.on_snapshot(_CODEX_ACTIVE_SURFACE)
    scheduler.advance_to(1.4)
    session.on_snapshot(_CODEX_COMPACT_DEGRADED_SURFACE)
    scheduler.advance_to(3.0)

    state = session.current_state()
    signals = session.latest_signals
    assert signals is not None

    assert state.turn_phase == "ready"
    assert state.surface_ready_posture == "yes"
    assert state.last_turn_result == "none"
    assert state.chat_context == "degraded"
    assert state.chat_context_diagnostic is not None
    assert state.chat_context_diagnostic.tool_name == "codex"
    assert (
        state.chat_context_diagnostic.degraded_error_type
        == "codex_remote_compact_stream_disconnected"
    )
    assert "chat_context=degraded" in state.notes
    assert signals.current_error_present is True
    assert signals.chat_context_diagnostic == state.chat_context_diagnostic
    assert signals.success_candidate is False
    assert signals.known_failure is False


def test_codex_tui_warning_failure_preserves_readiness_without_success() -> None:
    scheduler = TestScheduler()
    session = _codex_session(scheduler=scheduler)

    scheduler.advance_to(1.0)
    session.on_snapshot(_CODEX_ACTIVE_SURFACE)
    scheduler.advance_to(1.4)
    session.on_snapshot(_CODEX_WARNING_OVERLOADED_SURFACE)
    scheduler.advance_to(3.0)

    state = session.current_state()
    signals = session.latest_signals
    assert signals is not None

    assert state.turn_phase == "ready"
    assert state.surface_accepting_input == "yes"
    assert state.surface_editing_input == "no"
    assert state.surface_ready_posture == "yes"
    assert state.last_turn_result == "known_failure"
    assert state.chat_context == "current"
    assert signals.current_error_present is True
    assert signals.known_failure is True
    assert signals.success_candidate is False


def test_codex_detector_retry_status_forms_remain_active() -> None:
    detector = CodexTuiSignalDetectorV0_162_X()

    for surface in (
        _CODEX_RETRY_STATUS_SURFACE,
        _CODEX_RETRY_SERVER_STATUS_SURFACE,
        _CODEX_RETRY_DOTS_STATUS_SURFACE,
    ):
        signals = detector.detect(output_text=surface)

        assert signals.active_evidence is True
        assert "stream_retry_status" in signals.active_reasons
        assert signals.ready_posture == "no"
        assert signals.current_error_present is False
        assert signals.known_failure is False
        assert signals.success_candidate is False
        assert signals.success_blocked is True


def test_codex_tui_retry_status_remains_active_in_session() -> None:
    scheduler = TestScheduler()
    session = _codex_session(scheduler=scheduler)

    scheduler.advance_to(1.0)
    session.on_snapshot(_CODEX_RETRY_STATUS_SURFACE)
    scheduler.advance_to(3.0)

    state = session.current_state()

    assert state.turn_phase == "active"
    assert state.surface_ready_posture == "no"
    assert state.last_turn_result == "none"
    assert "stream_retry_status" in state.active_reasons


def test_codex_detector_retry_prose_does_not_mark_active() -> None:
    detector = CodexTuiSignalDetectorV0_162_X()
    surface = _codex_surface(
        "› /",
        "  /approve       approve one retry of a recent auto-review denial",
        composer="\x1b[1m›\x1b[0m Draft text",
    )

    signals = detector.detect(output_text=surface)

    assert signals.active_evidence is False
    assert "stream_retry_status" not in signals.active_reasons


def test_codex_detector_generic_error_does_not_mark_degraded_context() -> None:
    detector = CodexTuiSignalDetectorV0_162_X()

    signals = detector.detect(output_text=_CODEX_ERROR_SURFACE)

    assert signals.current_error_present is True
    assert signals.known_failure is False
    assert signals.chat_context == "current"
    assert signals.chat_context_diagnostic is None
    assert "chat_context=degraded" not in signals.notes


def test_codex_detector_warning_failure_blocks_success_without_exact_literal() -> None:
    detector = CodexTuiSignalDetectorV0_162_X()

    for surface in (_CODEX_WARNING_OVERLOADED_SURFACE, _CODEX_WARNING_HIGH_DEMAND_SURFACE):
        signals = detector.detect(output_text=surface)

        assert signals.accepting_input == "yes"
        assert signals.editing_input == "no"
        assert signals.ready_posture == "yes"
        assert signals.current_error_present is True
        assert signals.known_failure is True
        assert signals.success_candidate is False
        assert signals.success_blocked is True
        assert signals.chat_context == "current"
        assert "known_failure_signal_detected" in signals.notes


def test_codex_detector_red_context_window_failure_is_known_failure() -> None:
    detector = CodexTuiSignalDetectorV0_162_X()

    signals = detector.detect(output_text=_CODEX_CONTEXT_WINDOW_ERROR_SURFACE)

    assert signals.ready_posture == "yes"
    assert signals.current_error_present is True
    assert signals.known_failure is True
    assert signals.success_candidate is False
    assert signals.success_blocked is True
    assert signals.chat_context == "current"


def test_codex_detector_server_error_family_marks_degraded_context() -> None:
    detector = CodexTuiSignalDetectorV0_162_X()

    signals = detector.detect(output_text=_CODEX_SERVER_ERROR_DEGRADED_SURFACE)

    assert signals.current_error_present is True
    assert signals.chat_context == "degraded"
    assert signals.chat_context_diagnostic is not None
    assert (
        signals.chat_context_diagnostic.degraded_error_type == "codex_remote_compact_server_error"
    )


def test_codex_detector_unknown_parameter_family_marks_degraded_context() -> None:
    detector = CodexTuiSignalDetectorV0_162_X()

    signals = detector.detect(output_text=_CODEX_UNKNOWN_PARAMETER_DEGRADED_SURFACE)

    assert signals.current_error_present is True
    assert signals.chat_context == "degraded"
    assert signals.chat_context_diagnostic is not None
    assert (
        signals.chat_context_diagnostic.degraded_error_type
        == "codex_remote_compact_unknown_parameter"
    )


def test_codex_detector_ambient_warning_does_not_mutate_turn_state() -> None:
    detector = CodexTuiSignalDetectorV0_162_X()

    signals = detector.detect(output_text=_CODEX_AMBIENT_WARNING_SURFACE)

    assert signals.ready_posture == "yes"
    assert signals.active_evidence is False
    assert signals.current_error_present is False
    assert signals.known_failure is False
    assert signals.success_candidate is True
    assert signals.chat_context == "current"


def test_codex_detector_prompt_adjacent_wrapped_error_blocks_success() -> None:
    detector = CodexTuiSignalDetectorV0_162_X()

    signals = detector.detect(output_text=_CODEX_PROMPT_ADJACENT_AUTH_ERROR_SURFACE)

    assert signals.current_error_present is True
    assert signals.success_candidate is False
    assert signals.success_blocked is True
    assert signals.chat_context == "current"
    assert "chat_context=degraded" not in signals.notes
    assert signals.editing_input == "no"


def test_codex_detector_ignores_historical_compact_error_outside_live_edge() -> None:
    detector = CodexTuiSignalDetectorV0_162_X()

    signals = detector.detect(output_text=_CODEX_STALE_COMPACT_ERROR_SCROLLBACK_SURFACE)

    assert signals.current_error_present is False
    assert signals.ready_posture == "yes"
    assert signals.success_candidate is True
    assert signals.chat_context == "current"


def test_codex_detector_ignores_historical_warning_outside_live_edge() -> None:
    detector = CodexTuiSignalDetectorV0_162_X()

    signals = detector.detect(output_text=_CODEX_STALE_WARNING_SCROLLBACK_SURFACE)

    assert signals.current_error_present is False
    assert signals.known_failure is False
    assert signals.ready_posture == "yes"
    assert signals.success_candidate is True
    assert signals.chat_context == "current"


def test_codex_detector_ignores_non_adjacent_compact_error_in_current_turn() -> None:
    detector = CodexTuiSignalDetectorV0_162_X()

    signals = detector.detect(output_text=_CODEX_NON_ADJACENT_COMPACT_ERROR_SAME_TURN_SURFACE)

    assert signals.current_error_present is False
    assert signals.ready_posture == "yes"
    assert signals.chat_context == "current"


def test_codex_restart_does_not_reuse_prompt_above_latest_shell_launch() -> None:
    """Codex readiness belongs to the replacement process generation."""

    detector = CodexTuiSignalDetectorV0_162_X()

    stale = detector.detect(output_text=_CODEX_STALE_RESTART_SURFACE)
    fresh = detector.detect(output_text=_CODEX_FRESH_RESTART_SURFACE)

    assert stale.ready_posture == "no"
    assert stale.accepting_input == "no"
    assert "provider_surface_not_fresh" in stale.notes
    assert fresh.ready_posture == "yes"
    assert fresh.accepting_input == "yes"
