"""Unit tests for the Codex posture rules in the hook posture reducer."""

from __future__ import annotations

import json

from houmao.hook_observation.models import (
    HookObservation,
    HookPosture,
    NormalizedHookKind,
)
from houmao.hook_observation.reducer import HookPostureReducer


TURN_1 = "turn-1"
TURN_2 = "turn-2"
TOOL_1 = "tool-1"
TOOL_2 = "tool-2"
SESSION = "session-1"


def _obs(
    kind: NormalizedHookKind,
    *,
    event_name: str | None = None,
    generation: int = 1,
    sequence: int | None = None,
    received_at_utc: str = "2026-10-20T04:00:00+00:00",
    turn_id: str | None = None,
    steer: bool = False,
    prompt_id: str | None = None,
    session_id: str | None = SESSION,
    tool_name: str | None = None,
    tool_use_id: str | None = None,
    source: str | None = None,
    maintenance_trigger: str | None = None,
    stop_hook_active: bool | None = None,
    last_assistant_message_present: bool | None = None,
    background_work_pending: bool | None = None,
    error_class: str | None = None,
    malformed: bool = False,
    malformed_reason: str | None = None,
) -> HookObservation:
    return HookObservation(
        kind=kind,
        event_name=event_name or kind,
        channel_generation=generation,
        received_at_utc=received_at_utc,
        sequence=sequence,
        session_id=session_id,
        prompt_id=prompt_id,
        turn_id=turn_id,
        steer=steer,
        tool_name=tool_name,
        tool_use_id=tool_use_id,
        source=source,
        maintenance_trigger=maintenance_trigger,
        stop_hook_active=stop_hook_active,
        last_assistant_message_present=last_assistant_message_present,
        background_work_pending=background_work_pending,
        error_class=error_class,
        malformed=malformed,
        malformed_reason=malformed_reason,
    )


def _reducer() -> HookPostureReducer:
    return HookPostureReducer(adapter="codex")


def _start(reducer: HookPostureReducer, *, source: str = "startup") -> HookPosture:
    return reducer.reduce(
        _obs("session_started", event_name="SessionStart", sequence=1, source=source)
    )


def _prompt(reducer: HookPostureReducer, turn_id: str = TURN_1, **fields: object) -> HookPosture:
    return reducer.reduce(
        _obs(
            "prompt_submitted",
            event_name="UserPromptSubmit",
            turn_id=turn_id,
            prompt_id=turn_id,
            **fields,  # type: ignore[arg-type]
        )
    )


def test_stop_latches_success_and_clears_the_epoch() -> None:
    reducer = _reducer()
    posture = _start(reducer)
    assert posture.presence == "present"
    assert posture.turn_phase == "ready"
    assert posture.session_started is True

    posture = _prompt(reducer)
    assert posture.turn_phase == "active"
    assert posture.turn_id == TURN_1
    assert posture.armed_prompt_count == 1

    posture = reducer.reduce(
        _obs(
            "tool_started",
            event_name="PreToolUse",
            turn_id=TURN_1,
            tool_name="Bash",
            tool_use_id=TOOL_1,
        )
    )
    assert posture.turn_phase == "active"

    posture = reducer.reduce(
        _obs(
            "tool_completed",
            event_name="PostToolUse",
            turn_id=TURN_1,
            tool_name="Bash",
            tool_use_id=TOOL_1,
        )
    )
    assert posture.turn_phase == "active"

    posture = reducer.reduce(
        _obs(
            "turn_completed",
            event_name="Stop",
            turn_id=TURN_1,
            prompt_id=TURN_1,
            stop_hook_active=False,
            last_assistant_message_present=True,
        )
    )
    assert posture.turn_phase == "ready"
    assert posture.terminal_result == "success"
    assert posture.terminal_consumed_prompt_id == TURN_1
    assert posture.terminal_stop_hook_active is False
    assert posture.turn_id is None
    assert posture.armed_prompt_count == 0
    assert posture.work == "unknown"
    assert posture.settled is False
    assert posture.counters.turn_epochs == 1


def test_stop_hook_active_is_a_continuation_not_a_terminal() -> None:
    reducer = _reducer()
    _start(reducer)
    _prompt(reducer)

    posture = reducer.reduce(
        _obs(
            "turn_completed",
            event_name="Stop",
            turn_id=TURN_1,
            stop_hook_active=True,
        )
    )
    assert posture.turn_phase == "active"
    assert posture.terminal_result == "none"
    assert posture.turn_id == TURN_1
    assert posture.diagnostics[-1].kind == "hook_stop_hook_active"

    posture = reducer.reduce(
        _obs(
            "turn_completed",
            event_name="Stop",
            turn_id=TURN_1,
            stop_hook_active=False,
        )
    )
    assert posture.terminal_result == "success"
    assert posture.turn_phase == "ready"


def test_interrupt_settles_interrupted_from_hook_evidence() -> None:
    reducer = _reducer()
    _start(reducer)
    _prompt(reducer)

    posture = reducer.reduce(_obs("turn_interrupted", event_name="Interrupt", turn_id=TURN_1))
    assert posture.turn_phase == "ready"
    assert posture.terminal_result == "interrupted"
    assert posture.terminal_consumed_prompt_id == TURN_1
    assert posture.turn_id is None
    assert posture.counters.orphan_terminals == 0
    assert posture.counters.deny_settles == 0
    assert posture.counters.allow_settles == 0


def test_blocked_allow_settles_only_on_the_paired_post_tool_use() -> None:
    reducer = _reducer()
    _start(reducer)
    _prompt(reducer)
    reducer.reduce(
        _obs(
            "tool_started",
            event_name="PreToolUse",
            turn_id=TURN_1,
            tool_name="Bash",
            tool_use_id=TOOL_1,
        )
    )

    posture = reducer.reduce(
        _obs(
            "permission_requested",
            event_name="PermissionRequest",
            turn_id=TURN_1,
            tool_name="Bash",
            tool_use_id=TOOL_1,
        )
    )
    assert posture.turn_phase == "blocked"
    assert posture.blocked is True
    assert posture.blocked_tool_name == "Bash"
    assert posture.blocked_tool_use_id == TOOL_1
    assert posture.counters.allow_settles == 0

    posture = reducer.reduce(
        _obs(
            "tool_completed",
            event_name="PostToolUse",
            turn_id=TURN_1,
            tool_name="Bash",
            tool_use_id=TOOL_2,
        )
    )
    assert posture.turn_phase == "blocked"
    assert posture.blocked is True
    assert posture.diagnostics[-1].kind == "hook_blocked_tool_mismatch"

    posture = reducer.reduce(
        _obs(
            "tool_completed",
            event_name="PostToolUse",
            turn_id=TURN_1,
            tool_name="Bash",
            tool_use_id=TOOL_1,
        )
    )
    assert posture.turn_phase == "active"
    assert posture.blocked is False
    assert posture.blocked_tool_use_id is None
    assert posture.counters.allow_settles == 1

    posture = reducer.reduce(
        _obs("turn_completed", event_name="Stop", turn_id=TURN_1, stop_hook_active=False)
    )
    assert posture.terminal_result == "success"


def test_blocked_deny_aborts_the_turn_on_interrupt() -> None:
    reducer = _reducer()
    _start(reducer)
    _prompt(reducer)
    reducer.reduce(
        _obs(
            "tool_started",
            event_name="PreToolUse",
            turn_id=TURN_1,
            tool_name="Bash",
            tool_use_id=TOOL_1,
        )
    )
    reducer.reduce(
        _obs(
            "permission_requested",
            event_name="PermissionRequest",
            turn_id=TURN_1,
            tool_name="Bash",
            tool_use_id=TOOL_1,
        )
    )

    posture = reducer.reduce(_obs("turn_interrupted", event_name="Interrupt", turn_id=TURN_1))
    assert posture.turn_phase == "ready"
    assert posture.blocked is False
    assert posture.blocked_tool_name is None
    assert posture.terminal_result == "interrupted"
    assert posture.counters.deny_settles == 1
    assert posture.counters.allow_settles == 0
    assert posture.counters.terminal_gaps == 0
    assert any(item.kind == "hook_deny_aborted_turn" for item in posture.diagnostics)


def test_permission_request_without_an_open_turn_does_not_block() -> None:
    reducer = _reducer()
    _start(reducer)

    posture = reducer.reduce(
        _obs(
            "permission_requested",
            event_name="PermissionRequest",
            turn_id=TURN_1,
            tool_name="Bash",
            tool_use_id=TOOL_1,
        )
    )
    assert posture.turn_phase == "ready"
    assert posture.blocked is False
    assert posture.blocked_tool_use_id is None
    assert posture.diagnostics[-1].kind == "permission_without_armed_prompt"


def test_unpaired_permission_request_still_blocks_with_turn_scope() -> None:
    reducer = _reducer()
    _start(reducer)
    _prompt(reducer)

    posture = reducer.reduce(
        _obs(
            "permission_requested",
            event_name="PermissionRequest",
            turn_id=TURN_1,
            tool_name="Bash",
            tool_use_id=None,
        )
    )
    assert posture.turn_phase == "blocked"
    assert posture.blocked_tool_use_id is None
    assert posture.diagnostics[-1].kind == "hook_permission_pair_unresolved"

    posture = reducer.reduce(
        _obs("tool_completed", event_name="PostToolUse", turn_id=TURN_1, tool_use_id=TOOL_2)
    )
    assert posture.turn_phase == "active"
    assert posture.blocked is False
    assert posture.counters.allow_settles == 1


def test_terminal_gap_on_stream_end_is_truthful_unknown() -> None:
    reducer = _reducer()
    _start(reducer)
    posture = _prompt(reducer)
    assert posture.turn_phase == "active"

    posture = reducer.finish()
    assert posture.presence == "lost"
    assert posture.turn_phase == "unknown"
    assert posture.terminal_result == "none"
    assert posture.turn_id is None
    assert posture.armed_prompt_count == 0
    assert posture.counters.terminal_gaps == 1
    assert any(item.kind == "hook_terminal_gap" for item in posture.diagnostics)

    again = reducer.finish()
    assert again.presence == posture.presence
    assert again.turn_phase == posture.turn_phase
    assert again.counters.terminal_gaps == 1
    assert len(again.diagnostics) == len(posture.diagnostics)


def test_session_end_with_open_turn_is_a_session_end_gap() -> None:
    reducer = _reducer()
    _start(reducer)
    _prompt(reducer)

    posture = reducer.reduce(_obs("session_ended", event_name="SessionEnd"))
    assert posture.presence == "lost"
    assert posture.turn_phase == "unknown"
    assert posture.terminal_result == "none"
    assert posture.turn_id is None
    assert posture.counters.terminal_gaps == 1
    assert any(item.kind == "hook_session_end_with_open_turn" for item in posture.diagnostics)


def test_session_end_after_a_settled_turn_keeps_the_latch() -> None:
    reducer = _reducer()
    _start(reducer)
    _prompt(reducer)
    reducer.reduce(
        _obs("turn_completed", event_name="Stop", turn_id=TURN_1, stop_hook_active=False)
    )

    posture = reducer.reduce(_obs("session_ended", event_name="SessionEnd"))
    assert posture.presence == "lost"
    assert posture.turn_phase == "ready"
    assert posture.terminal_result == "success"
    assert posture.counters.terminal_gaps == 0


def test_compaction_window_holds_posture_and_next_turn_is_a_new_epoch() -> None:
    reducer = _reducer()
    _start(reducer)
    _prompt(reducer)
    reducer.reduce(
        _obs("turn_completed", event_name="Stop", turn_id=TURN_1, stop_hook_active=False)
    )

    posture = reducer.reduce(
        _obs(
            "maintenance_started",
            event_name="PreCompact",
            turn_id="compact-turn",
            maintenance_trigger="manual",
        )
    )
    assert posture.maintenance_active is True
    assert posture.turn_phase == "ready"
    assert posture.terminal_result == "success"
    assert posture.turn_id is None

    posture = reducer.reduce(
        _obs(
            "maintenance_ended",
            event_name="PostCompact",
            turn_id="compact-turn",
            maintenance_trigger="manual",
        )
    )
    assert posture.maintenance_active is False
    assert posture.terminal_result == "success"

    posture = reducer.reduce(_obs("session_started", event_name="SessionStart", source="compact"))
    assert posture.maintenance_active is False
    assert posture.terminal_result == "success"
    assert posture.turn_phase == "ready"
    assert posture.counters.compaction_boundaries == 1

    posture = _prompt(reducer, turn_id=TURN_2)
    assert posture.turn_phase == "active"
    assert posture.turn_id == TURN_2
    assert posture.terminal_result == "none"
    assert posture.counters.turn_epochs == 2
    assert posture.counters.compaction_boundaries == 1


def test_compaction_while_active_does_not_interrupt_the_turn() -> None:
    reducer = _reducer()
    _start(reducer)
    _prompt(reducer)

    posture = reducer.reduce(_obs("maintenance_started", event_name="PreCompact"))
    assert posture.maintenance_active is True
    assert posture.turn_phase == "active"
    assert posture.turn_id == TURN_1

    posture = reducer.reduce(_obs("maintenance_ended", event_name="PostCompact"))
    assert posture.maintenance_active is False
    assert posture.turn_phase == "active"
    assert posture.turn_id == TURN_1


def test_generation_change_resets_and_old_generation_events_are_dropped() -> None:
    reducer = _reducer()
    _start(reducer)
    _prompt(reducer)
    assert reducer.posture.generation == 1

    posture = reducer.reduce(
        _obs(
            "session_started",
            event_name="SessionStart",
            generation=2,
            sequence=1,
            source="resume",
        )
    )
    assert posture.generation == 2
    assert posture.presence == "present"
    assert posture.turn_phase == "ready"
    assert posture.terminal_result == "none"
    assert posture.armed_prompt_count == 0

    _prompt(reducer, turn_id=TURN_2, generation=2, sequence=2)  # type: ignore[arg-type]
    posture = reducer.reduce(
        _obs(
            "turn_completed",
            event_name="Stop",
            generation=2,
            sequence=3,
            turn_id=TURN_2,
            stop_hook_active=False,
        )
    )
    assert posture.terminal_result == "success"
    assert posture.counters.turn_epochs == 2

    posture = reducer.reduce(
        _obs(
            "prompt_submitted",
            event_name="UserPromptSubmit",
            generation=1,
            sequence=9,
            turn_id="stale",
        )
    )
    assert posture.generation == 2
    assert posture.turn_phase == "ready"
    assert posture.counters.orphan_generations == 1
    assert posture.diagnostics[-1].kind == "hook_orphan_generation"


def test_resume_resets_turn_state_but_keeps_session_identity() -> None:
    reducer = _reducer()
    _start(reducer)
    _prompt(reducer)
    reducer.reduce(
        _obs("turn_completed", event_name="Stop", turn_id=TURN_1, stop_hook_active=False)
    )

    posture = reducer.reduce(
        _obs(
            "session_started",
            event_name="SessionStart",
            sequence=2,
            source="resume",
            session_id=SESSION,
        )
    )
    assert posture.session_id == SESSION
    assert posture.session_start_source == "resume"
    assert posture.turn_phase == "ready"
    assert posture.terminal_result == "none"
    assert posture.turn_id is None


def test_orphan_terminal_never_manufactures_last_turn() -> None:
    reducer = _reducer()
    _start(reducer)

    posture = reducer.reduce(
        _obs("turn_completed", event_name="Stop", turn_id=TURN_1, prompt_id=TURN_1)
    )
    assert posture.terminal_result == "none"
    assert posture.turn_phase == "ready"
    assert posture.counters.orphan_terminals == 1
    assert posture.diagnostics[-1].kind == "hook_orphan_terminal"


def test_late_interrupt_does_not_override_a_latched_success() -> None:
    reducer = _reducer()
    _start(reducer)
    _prompt(reducer)
    reducer.reduce(
        _obs("turn_completed", event_name="Stop", turn_id=TURN_1, stop_hook_active=False)
    )

    posture = reducer.reduce(_obs("turn_interrupted", event_name="Interrupt", turn_id=TURN_1))
    assert posture.terminal_result == "success"
    assert posture.counters.orphan_terminals == 1
    assert posture.counters.deny_settles == 0


def test_terminal_turn_mismatch_is_an_orphan() -> None:
    reducer = _reducer()
    _start(reducer)
    _prompt(reducer)

    posture = reducer.reduce(
        _obs("turn_completed", event_name="Stop", turn_id=TURN_2, stop_hook_active=False)
    )
    assert posture.turn_phase == "active"
    assert posture.terminal_result == "none"
    assert posture.counters.orphan_terminals == 1
    assert "turn_mismatch" in (posture.diagnostics[-1].detail or "")


def test_steer_stays_in_the_running_epoch() -> None:
    reducer = _reducer()
    _start(reducer)
    _prompt(reducer)

    posture = reducer.reduce(
        _obs(
            "prompt_submitted",
            event_name="UserPromptSubmit",
            turn_id=TURN_1,
            prompt_id=TURN_1,
            steer=True,
        )
    )
    assert posture.turn_phase == "active"
    assert posture.turn_id == TURN_1
    assert posture.armed_prompt_count == 1
    assert posture.counters.turn_epochs == 1
    assert posture.counters.steer_events == 1
    assert posture.diagnostics[-1].kind == "hook_steer_same_turn"

    posture = reducer.reduce(
        _obs("turn_completed", event_name="Stop", turn_id=TURN_1, stop_hook_active=False)
    )
    assert posture.terminal_result == "success"
    assert posture.counters.turn_epochs == 1


def test_new_prompt_supersedes_an_open_epoch() -> None:
    reducer = _reducer()
    _start(reducer)
    _prompt(reducer)

    posture = _prompt(reducer, turn_id=TURN_2)
    assert posture.turn_phase == "active"
    assert posture.turn_id == TURN_2
    assert posture.armed_prompt_count == 1
    assert posture.counters.turn_epochs == 2
    assert posture.diagnostics[-1].kind == "hook_turn_epoch_superseded"


def test_work_axis_stays_unknown_and_never_claims_settled() -> None:
    reducer = _reducer()
    _start(reducer)
    _prompt(reducer)
    posture = reducer.reduce(
        _obs("turn_completed", event_name="Stop", turn_id=TURN_1, stop_hook_active=False)
    )

    assert posture.work == "unknown"
    assert posture.settled is False
    payload = json.dumps(posture.to_payload())
    assert '"work": "unknown"' in payload


def test_unavailable_families_are_diagnostics_at_stream_end() -> None:
    reducer = _reducer()
    _start(reducer)
    _prompt(reducer)
    reducer.reduce(
        _obs(
            "tool_started",
            event_name="PreToolUse",
            turn_id=TURN_1,
            tool_name="Bash",
            tool_use_id=TOOL_1,
        )
    )
    reducer.reduce(
        _obs(
            "permission_requested",
            event_name="PermissionRequest",
            turn_id=TURN_1,
            tool_name="Bash",
            tool_use_id=TOOL_1,
        )
    )
    reducer.reduce(
        _obs("tool_completed", event_name="PostToolUse", turn_id=TURN_1, tool_use_id=TOOL_1)
    )
    reducer.reduce(
        _obs("turn_completed", event_name="Stop", turn_id=TURN_1, stop_hook_active=False)
    )
    _prompt(reducer, turn_id=TURN_2)
    reducer.reduce(_obs("turn_interrupted", event_name="Interrupt", turn_id=TURN_2))
    reducer.reduce(_obs("maintenance_started", event_name="PreCompact"))
    reducer.reduce(_obs("maintenance_ended", event_name="PostCompact"))
    reducer.reduce(_obs("session_ended", event_name="SessionEnd"))

    posture = reducer.finish()
    kinds = [item.kind for item in posture.diagnostics]
    assert kinds.count("hook_unavailable_event_family") == 4
    families = {
        item.event_name
        for item in posture.diagnostics
        if item.kind == "hook_unavailable_event_family"
    }
    assert families == {
        "PostModelRequest",
        "PreModelRequest",
        "SubagentStart",
        "SubagentStop",
    }


def test_unknown_and_malformed_observations_are_counted() -> None:
    reducer = _reducer()
    _start(reducer)

    posture = reducer.reduce(_obs("unknown", event_name="PreModelRequest", turn_id=TURN_1))
    assert posture.counters.unknown_events == 1
    assert posture.diagnostics[-1].kind == "hook_unknown_event"

    posture = reducer.reduce(
        _obs(
            "unknown",
            event_name="<malformed>",
            malformed=True,
            malformed_reason="missing_event_name",
        )
    )
    assert posture.counters.malformed_events == 1
    assert posture.diagnostics[-1].kind == "hook_malformed_event"


def test_default_adapter_keeps_claude_semantics() -> None:
    reducer = HookPostureReducer()
    posture = reducer.reduce(
        _obs("prompt_submitted", event_name="UserPromptSubmit", prompt_id="p1")
    )
    assert posture.turn_phase == "active"
    assert posture.presence == "unknown"

    posture = reducer.reduce(
        _obs(
            "turn_completed",
            event_name="Stop",
            prompt_id="p1",
            background_work_pending=False,
        )
    )
    assert posture.terminal_result == "success"
    assert posture.work == "clear"
    assert posture.settled is True
