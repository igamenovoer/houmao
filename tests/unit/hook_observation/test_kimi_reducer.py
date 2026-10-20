"""Unit tests for the Kimi posture rules in the hook posture reducer."""

from __future__ import annotations

import json

import pytest

from houmao.hook_observation.models import HookObservation, HookPosture, NormalizedHookKind
from houmao.hook_observation.reducer import HookPostureReducer


TURN_0 = "0"
TURN_1 = "1"
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
    reason: str | None = None,
    maintenance_trigger: str | None = None,
    stop_hook_active: bool | None = None,
    permission_decision: str | None = None,
    origin_kind: str | None = None,
    origin_name: str | None = None,
    agent_name: str | None = None,
    queue_length: int | None = None,
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
        reason=reason,
        maintenance_trigger=maintenance_trigger,
        stop_hook_active=stop_hook_active,
        permission_decision=permission_decision,
        origin_kind=origin_kind,
        origin_name=origin_name,
        agent_name=agent_name,
        queue_length=queue_length,
        error_class=error_class,
        malformed=malformed,
        malformed_reason=malformed_reason,
    )


def _reducer() -> HookPostureReducer:
    return HookPostureReducer(adapter="kimi")


def _start(reducer: HookPostureReducer, *, source: str = "startup") -> HookPosture:
    return reducer.reduce(
        _obs("session_started", event_name="SessionStart", sequence=1, source=source)
    )


def _arm(reducer: HookPostureReducer, **fields: object) -> HookPosture:
    return reducer.reduce(
        _obs(
            "prompt_submitted",
            event_name="UserPromptSubmit",
            **fields,  # type: ignore[arg-type]
        )
    )


def _bind(
    reducer: HookPostureReducer,
    turn_id: str = TURN_0,
    **fields: object,
) -> HookPosture:
    return reducer.reduce(
        _obs(
            "turn_started",
            event_name="TurnStarted",
            turn_id=turn_id,
            origin_kind="user",
            **fields,  # type: ignore[arg-type]
        )
    )


def _stop(reducer: HookPostureReducer, **fields: object) -> HookPosture:
    return reducer.reduce(
        _obs(
            "turn_completed",
            event_name="Stop",
            stop_hook_active=False,
            **fields,  # type: ignore[arg-type]
        )
    )


def test_arm_and_bind_turn_correlation() -> None:
    reducer = _reducer()
    posture = _start(reducer)
    assert posture.presence == "present"
    assert posture.turn_phase == "ready"
    assert posture.session_started is True

    posture = _arm(reducer)
    assert posture.turn_phase == "active"
    assert posture.turn_id is None
    assert posture.armed_prompt_count == 1
    assert posture.counters.turn_epochs == 1

    posture = _bind(reducer)
    assert posture.turn_phase == "active"
    assert posture.turn_id == TURN_0
    assert posture.counters.turn_epochs == 1

    reducer.reduce(
        _obs("tool_started", event_name="PreToolUse", tool_name="Bash", tool_use_id=TOOL_1)
    )
    posture = reducer.reduce(
        _obs("tool_completed", event_name="PostToolUse", tool_name="Bash", tool_use_id=TOOL_1)
    )
    assert posture.turn_phase == "active"
    assert posture.turn_id == TURN_0

    posture = _stop(reducer)
    assert posture.turn_phase == "ready"
    assert posture.terminal_result == "success"
    assert posture.terminal_source == "hook_observation"
    assert posture.terminal_consumed_prompt_id == TURN_0
    assert posture.turn_id is None
    assert posture.armed_prompt_count == 0
    assert posture.work == "unknown"
    assert posture.settled is False
    assert posture.counters.turn_epochs == 1
    assert posture.counters.orphan_terminals == 0


def test_turn_started_without_a_prompt_arms_defensively() -> None:
    reducer = _reducer()
    _start(reducer)

    posture = _bind(reducer, turn_id="3")
    assert posture.turn_phase == "active"
    assert posture.turn_id == "3"
    assert posture.counters.turn_epochs == 1
    assert posture.diagnostics[-1].kind == "hook_turn_started_without_prompt"


def test_duplicate_turn_started_is_counted() -> None:
    reducer = _reducer()
    _start(reducer)
    _arm(reducer)
    _bind(reducer)

    posture = _bind(reducer)
    assert posture.turn_phase == "active"
    assert posture.turn_id == TURN_0
    assert posture.counters.duplicate_events == 1
    assert posture.diagnostics[-1].kind == "hook_duplicate_event"
    assert posture.counters.turn_epochs == 1


def test_turn_started_with_a_new_id_supersedes_the_open_epoch() -> None:
    reducer = _reducer()
    _start(reducer)
    _arm(reducer)
    _bind(reducer)

    posture = _bind(reducer, turn_id=TURN_1)
    assert posture.turn_phase == "active"
    assert posture.turn_id == TURN_1
    assert posture.counters.turn_epochs == 2
    assert posture.diagnostics[-1].kind == "hook_turn_epoch_superseded"


def test_turn_started_without_turn_id_is_diagnosed() -> None:
    reducer = _reducer()
    _start(reducer)
    _arm(reducer)

    posture = reducer.reduce(
        _obs("turn_started", event_name="TurnStarted", origin_kind="user", turn_id=None)
    )
    assert posture.turn_phase == "active"
    assert posture.turn_id is None
    assert posture.armed_prompt_count == 1
    assert posture.diagnostics[-1].kind == "hook_turn_started_without_turn_id"


def test_stop_hook_active_is_a_continuation_not_a_terminal() -> None:
    reducer = _reducer()
    _start(reducer)
    _arm(reducer)
    _bind(reducer)

    posture = reducer.reduce(_obs("turn_completed", event_name="Stop", stop_hook_active=True))
    assert posture.turn_phase == "active"
    assert posture.terminal_result == "none"
    assert posture.turn_id == TURN_0
    assert posture.diagnostics[-1].kind == "hook_stop_hook_active"

    posture = _stop(reducer)
    assert posture.terminal_result == "success"
    assert posture.turn_phase == "ready"


def test_interrupt_settles_interrupted_from_hook_evidence() -> None:
    reducer = _reducer()
    _start(reducer)
    _arm(reducer)
    _bind(reducer)

    posture = reducer.reduce(
        _obs("turn_interrupted", event_name="Interrupt", turn_id=TURN_0, reason="cancelled")
    )
    assert posture.turn_phase == "ready"
    assert posture.terminal_result == "interrupted"
    assert posture.terminal_source == "hook_observation"
    assert posture.terminal_consumed_prompt_id == TURN_0
    assert posture.turn_id is None
    assert posture.counters.interrupts == 1
    assert posture.counters.orphan_terminals == 0
    assert posture.counters.deny_settles == 0
    assert posture.counters.allow_settles == 0


def test_late_interrupt_does_not_override_a_latched_success() -> None:
    reducer = _reducer()
    _start(reducer)
    _arm(reducer)
    _bind(reducer)
    _stop(reducer)

    posture = reducer.reduce(
        _obs("turn_interrupted", event_name="Interrupt", turn_id=TURN_0, reason="cancelled")
    )
    assert posture.terminal_result == "success"
    assert posture.counters.orphan_terminals == 1
    assert posture.counters.interrupts == 1
    assert posture.counters.deny_settles == 0


def test_blocked_allow_settles_at_permission_result() -> None:
    reducer = _reducer()
    _start(reducer)
    _arm(reducer)
    _bind(reducer)
    reducer.reduce(
        _obs("tool_started", event_name="PreToolUse", tool_name="Write", tool_use_id=TOOL_1)
    )

    posture = reducer.reduce(
        _obs(
            "permission_requested",
            event_name="PermissionRequest",
            turn_id=TURN_0,
            tool_name="Write",
            tool_use_id=TOOL_1,
        )
    )
    assert posture.turn_phase == "blocked"
    assert posture.blocked is True
    assert posture.blocked_tool_name == "Write"
    assert posture.blocked_tool_use_id == TOOL_1
    assert posture.counters.permission_requests == 1
    assert posture.counters.blocked_windows == 1

    # The allow path executes the tool before the result arrives.
    posture = reducer.reduce(
        _obs("tool_completed", event_name="PostToolUse", tool_name="Write", tool_use_id=TOOL_1)
    )
    assert posture.turn_phase == "blocked"
    assert posture.blocked is True
    assert posture.counters.allow_settles == 0

    posture = reducer.reduce(
        _obs(
            "permission_resolved",
            event_name="PermissionResult",
            turn_id=TURN_0,
            tool_name="Write",
            tool_use_id=TOOL_1,
            permission_decision="approved",
        )
    )
    assert posture.turn_phase == "active"
    assert posture.blocked is False
    assert posture.blocked_tool_use_id is None
    assert posture.counters.allow_settles == 1
    assert posture.counters.deny_settles == 0

    posture = _stop(reducer)
    assert posture.terminal_result == "success"


def test_blocked_deny_is_non_terminal_and_the_turn_continues() -> None:
    reducer = _reducer()
    _start(reducer)
    _arm(reducer)
    _bind(reducer)
    reducer.reduce(
        _obs("tool_started", event_name="PreToolUse", tool_name="Write", tool_use_id=TOOL_1)
    )
    reducer.reduce(
        _obs(
            "permission_requested",
            event_name="PermissionRequest",
            turn_id=TURN_0,
            tool_name="Write",
            tool_use_id=TOOL_1,
        )
    )

    posture = reducer.reduce(
        _obs(
            "permission_resolved",
            event_name="PermissionResult",
            turn_id=TURN_0,
            tool_name="Write",
            tool_use_id=TOOL_1,
            permission_decision="rejected",
        )
    )
    assert posture.turn_phase == "active"
    assert posture.blocked is False
    assert posture.counters.deny_settles == 1
    assert posture.counters.allow_settles == 0

    posture = reducer.reduce(
        _obs(
            "tool_failed",
            event_name="PostToolUseFailure",
            tool_name="Write",
            tool_use_id=TOOL_1,
            error_class="internal",
        )
    )
    assert posture.turn_phase == "active"
    assert posture.terminal_result == "none"
    assert posture.turn_id == TURN_0
    assert posture.counters.interrupts == 0

    posture = _stop(reducer)
    assert posture.terminal_result == "success"
    assert posture.counters.terminal_gaps == 0
    assert posture.counters.deny_settles == 1


def test_permission_request_without_an_open_epoch_does_not_block() -> None:
    reducer = _reducer()
    _start(reducer)

    posture = reducer.reduce(
        _obs(
            "permission_requested",
            event_name="PermissionRequest",
            turn_id=TURN_0,
            tool_name="Write",
            tool_use_id=TOOL_1,
        )
    )
    assert posture.turn_phase == "ready"
    assert posture.blocked is False
    assert posture.diagnostics[-1].kind == "permission_without_armed_prompt"


def test_permission_request_binds_an_unbound_epoch() -> None:
    reducer = _reducer()
    _start(reducer)
    _arm(reducer)

    posture = reducer.reduce(
        _obs(
            "permission_requested",
            event_name="PermissionRequest",
            turn_id=TURN_0,
            tool_name="Write",
            tool_use_id=TOOL_1,
        )
    )
    assert posture.turn_phase == "blocked"
    assert posture.turn_id == TURN_0

    posture = reducer.reduce(
        _obs(
            "permission_resolved",
            event_name="PermissionResult",
            turn_id=TURN_0,
            tool_use_id=TOOL_1,
            permission_decision="approved",
        )
    )
    assert posture.turn_phase == "active"
    posture = _stop(reducer)
    assert posture.terminal_result == "success"


def test_permission_turn_mismatch_is_diagnosed_but_still_blocks() -> None:
    reducer = _reducer()
    _start(reducer)
    _arm(reducer)
    _bind(reducer)

    posture = reducer.reduce(
        _obs(
            "permission_requested",
            event_name="PermissionRequest",
            turn_id=TURN_1,
            tool_name="Write",
            tool_use_id=TOOL_1,
        )
    )
    assert posture.turn_phase == "blocked"
    assert posture.turn_id == TURN_0
    assert posture.diagnostics[-1].kind == "hook_permission_turn_mismatch"


def test_permission_result_without_a_blocked_window_is_ignored() -> None:
    reducer = _reducer()
    _start(reducer)
    _arm(reducer)
    _bind(reducer)

    posture = reducer.reduce(
        _obs(
            "permission_resolved",
            event_name="PermissionResult",
            turn_id=TURN_0,
            permission_decision="approved",
        )
    )
    assert posture.turn_phase == "active"
    assert posture.counters.allow_settles == 0
    assert posture.diagnostics[-1].kind == "hook_permission_result_without_blocked"


def test_blocked_window_settles_with_a_tool_call_id_mismatch() -> None:
    reducer = _reducer()
    _start(reducer)
    _arm(reducer)
    _bind(reducer)
    reducer.reduce(
        _obs(
            "permission_requested",
            event_name="PermissionRequest",
            turn_id=TURN_0,
            tool_name="Write",
            tool_use_id=TOOL_1,
        )
    )

    posture = reducer.reduce(
        _obs(
            "permission_resolved",
            event_name="PermissionResult",
            turn_id=TURN_0,
            tool_use_id=TOOL_2,
            permission_decision="approved",
        )
    )
    assert posture.turn_phase == "active"
    assert posture.blocked is False
    assert posture.counters.allow_settles == 1
    assert posture.diagnostics[-1].kind == "hook_blocked_tool_mismatch"


def test_nested_subagent_scopes_do_not_settle_the_parent_turn() -> None:
    reducer = _reducer()
    _start(reducer)
    _arm(reducer)
    _bind(reducer)
    reducer.reduce(
        _obs("tool_started", event_name="PreToolUse", tool_name="Agent", tool_use_id=TOOL_1)
    )

    posture = reducer.reduce(
        _obs(
            "turn_started",
            event_name="TurnStarted",
            turn_id=TURN_0,
            origin_kind="system_trigger",
            origin_name="subagent",
        )
    )
    assert posture.turn_phase == "active"
    assert posture.turn_id == TURN_0
    assert posture.counters.turn_epochs == 1
    assert posture.diagnostics[-1].kind == "hook_nested_scope_opened"

    posture = reducer.reduce(
        _obs("subagent_started", event_name="SubagentStart", agent_name="explore")
    )
    assert posture.turn_phase == "active"

    posture = _stop(reducer)
    assert posture.turn_phase == "active"
    assert posture.terminal_result == "none"
    assert posture.turn_id == TURN_0
    assert posture.diagnostics[-1].kind == "hook_nested_scope_closed"

    posture = reducer.reduce(
        _obs("subagent_stopped", event_name="SubagentStop", agent_name="explore")
    )
    assert posture.turn_phase == "active"
    assert posture.counters.subagent_starts == 1
    assert posture.counters.subagent_stops == 1

    posture = _stop(reducer)
    assert posture.turn_phase == "ready"
    assert posture.terminal_result == "success"
    assert posture.counters.turn_epochs == 1


def test_queued_prompt_is_queue_evidence_without_a_second_epoch() -> None:
    reducer = _reducer()
    _start(reducer)
    _arm(reducer)
    _bind(reducer)

    posture = reducer.reduce(
        _obs(
            "prompt_queued",
            event_name="UserPromptQueued",
            prompt_id="msg_1",
            queue_length=1,
        )
    )
    assert posture.turn_phase == "active"
    assert posture.turn_id == TURN_0
    assert posture.counters.queued_prompts == 1
    assert posture.counters.turn_epochs == 1
    assert posture.diagnostics[-1].kind == "hook_prompt_queued"

    posture = _stop(reducer)
    assert posture.terminal_result == "success"
    assert posture.counters.turn_epochs == 1


def test_heartbeat_is_liveness_only() -> None:
    reducer = _reducer()
    _start(reducer)
    _arm(reducer)
    _bind(reducer)

    posture = reducer.reduce(_obs("session_heartbeat", event_name="SessionHeartbeat"))
    assert posture.turn_phase == "active"
    assert posture.turn_id == TURN_0
    assert posture.counters.heartbeats == 1

    _stop(reducer)
    posture = reducer.reduce(_obs("session_heartbeat", event_name="SessionHeartbeat"))
    assert posture.turn_phase == "ready"
    assert posture.terminal_result == "success"
    assert posture.counters.heartbeats == 2


def test_compaction_window_holds_ready_posture_and_next_epoch_is_fresh() -> None:
    reducer = _reducer()
    _start(reducer)
    _arm(reducer)
    _bind(reducer)
    _stop(reducer)

    posture = reducer.reduce(
        _obs(
            "maintenance_started",
            event_name="PreCompact",
            maintenance_trigger="manual",
        )
    )
    assert posture.maintenance_active is True
    assert posture.turn_phase == "ready"
    assert posture.terminal_result == "success"
    assert posture.turn_id is None
    assert posture.counters.compaction_boundaries == 1

    posture = reducer.reduce(
        _obs(
            "maintenance_ended",
            event_name="PostCompact",
            maintenance_trigger="manual",
        )
    )
    assert posture.maintenance_active is False
    assert posture.terminal_result == "success"

    posture = _arm(reducer)
    assert posture.turn_phase == "active"
    assert posture.turn_id is None
    assert posture.terminal_result == "none"
    assert posture.counters.turn_epochs == 2

    posture = _bind(reducer, turn_id=TURN_1)
    assert posture.turn_id == TURN_1
    assert posture.counters.turn_epochs == 2

    posture = _stop(reducer)
    assert posture.terminal_result == "success"
    assert posture.counters.compaction_boundaries == 1


def test_compaction_while_active_does_not_interrupt_the_turn() -> None:
    reducer = _reducer()
    _start(reducer)
    _arm(reducer)
    _bind(reducer)

    posture = reducer.reduce(
        _obs("maintenance_started", event_name="PreCompact", maintenance_trigger="auto")
    )
    assert posture.maintenance_active is True
    assert posture.turn_phase == "active"
    assert posture.turn_id == TURN_0
    assert posture.terminal_result == "none"

    posture = reducer.reduce(
        _obs("maintenance_ended", event_name="PostCompact", maintenance_trigger="auto")
    )
    assert posture.maintenance_active is False
    assert posture.turn_phase == "active"
    assert posture.turn_id == TURN_0


def test_session_end_with_open_turn_is_a_terminal_gap() -> None:
    reducer = _reducer()
    _start(reducer)
    _arm(reducer)
    _bind(reducer)

    posture = reducer.reduce(_obs("session_ended", event_name="SessionEnd", reason="exit"))
    assert posture.presence == "lost"
    assert posture.turn_phase == "unknown"
    assert posture.terminal_result == "none"
    assert posture.turn_id is None
    assert posture.counters.terminal_gaps == 1
    assert any(item.kind == "hook_session_end_with_open_turn" for item in posture.diagnostics)


def test_session_end_after_a_settled_turn_keeps_the_latch() -> None:
    reducer = _reducer()
    _start(reducer)
    _arm(reducer)
    _bind(reducer)
    _stop(reducer)

    posture = reducer.reduce(_obs("session_ended", event_name="SessionEnd", reason="exit"))
    assert posture.presence == "lost"
    assert posture.turn_phase == "ready"
    assert posture.terminal_result == "success"
    assert posture.counters.terminal_gaps == 0


def test_terminal_gap_on_stream_end_is_truthful_unknown() -> None:
    reducer = _reducer()
    _start(reducer)
    _arm(reducer)
    posture = _bind(reducer)
    assert posture.turn_phase == "active"

    posture = reducer.finish()
    assert posture.presence == "lost"
    assert posture.turn_phase == "unknown"
    assert posture.terminal_result == "none"
    assert posture.turn_id is None
    assert posture.armed_prompt_count == 0
    assert posture.counters.terminal_gaps == 1
    kinds = [item.kind for item in posture.diagnostics]
    assert "hook_terminal_gap" in kinds
    assert "hook_heartbeat_liveness_unavailable" in kinds

    again = reducer.finish()
    assert again.presence == posture.presence
    assert again.turn_phase == posture.turn_phase
    assert again.counters.terminal_gaps == 1
    assert len(again.diagnostics) == len(posture.diagnostics)


def test_headless_clean_exit_names_the_missing_session_end() -> None:
    reducer = _reducer()
    _start(reducer)
    _arm(reducer)
    _bind(reducer)
    _stop(reducer)

    posture = reducer.finish(headless=True, process_returncode=0)
    assert posture.presence == "lost"
    assert posture.turn_phase == "ready"
    assert posture.terminal_result == "success"
    assert posture.counters.terminal_gaps == 0
    assert any(item.kind == "hook_headless_session_end_gap" for item in posture.diagnostics)


def test_headless_nonzero_exit_is_not_terminal_settled() -> None:
    reducer = _reducer()
    _start(reducer)
    _arm(reducer)
    _bind(reducer)
    _stop(reducer)

    posture = reducer.finish(headless=True, process_returncode=1)
    assert posture.presence == "unknown"
    assert posture.terminal_result == "success"
    assert not any(item.kind == "hook_headless_session_end_gap" for item in posture.diagnostics)


def test_generation_change_resets_turn_state_and_keeps_counters() -> None:
    reducer = _reducer()
    _start(reducer)
    _arm(reducer)
    _bind(reducer)
    _stop(reducer)
    assert reducer.posture.generation == 1
    assert reducer.posture.counters.turn_epochs == 1

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
    assert posture.session_start_source == "resume"
    assert posture.turn_phase == "ready"
    assert posture.terminal_result == "none"
    assert posture.armed_prompt_count == 0
    assert posture.counters.turn_epochs == 1

    _arm(reducer, generation=2, sequence=2)
    _bind(reducer, turn_id=TURN_1, generation=2, sequence=3)
    posture = _stop(reducer, generation=2, sequence=4)
    assert posture.terminal_result == "success"
    assert posture.counters.turn_epochs == 2

    posture = reducer.reduce(
        _obs(
            "prompt_submitted",
            event_name="UserPromptSubmit",
            generation=1,
            sequence=9,
        )
    )
    assert posture.generation == 2
    assert posture.turn_phase == "ready"
    assert posture.counters.orphan_generations == 1
    assert posture.diagnostics[-1].kind == "hook_orphan_generation"


def test_resume_start_clears_last_turn_but_keeps_session_identity() -> None:
    reducer = _reducer()
    _start(reducer)
    _arm(reducer)
    _bind(reducer)
    _stop(reducer)

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


def test_work_axis_stays_unknown_and_never_claims_settled() -> None:
    reducer = _reducer()
    _start(reducer)
    _arm(reducer)
    _bind(reducer)
    posture = _stop(reducer)

    assert posture.work == "unknown"
    assert posture.settled is False
    payload = json.dumps(posture.to_payload())
    assert '"work": "unknown"' in payload


def test_unavailable_families_are_diagnostics_at_stream_end() -> None:
    reducer = _reducer()
    _start(reducer)
    _arm(reducer)
    _bind(reducer)
    _stop(reducer)
    reducer.reduce(_obs("session_ended", event_name="SessionEnd", reason="exit"))

    posture = reducer.finish()
    families = {
        item.event_name
        for item in posture.diagnostics
        if item.kind == "hook_unavailable_event_family"
    }
    assert families == {"StopFailure", "TaskStarted", "Notification"}


def test_unknown_and_malformed_observations_are_counted() -> None:
    reducer = _reducer()
    _start(reducer)

    posture = reducer.reduce(_obs("unknown", event_name="TaskStarted"))
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


def test_unknown_adapter_is_rejected() -> None:
    with pytest.raises(ValueError):
        HookPostureReducer(adapter="other")  # type: ignore[arg-type]
