"""Unit tests for the Kimi hook event normalizer."""

from __future__ import annotations

import json
from typing import Any

import pytest

from houmao.hook_observation.kimi_normalizer import KIMI_EVENTS, KimiEventNormalizer
from houmao.hook_observation.models import HookEventEnvelope, HookObservation


SESSION_ID = "session-1"
TOOL_CALL_ID = "tool_abc123"
OTHER_TOOL_CALL_ID = "tool_def456"


def _payload(event_name: str, **fields: Any) -> dict[str, Any]:
    return {
        "hook_event_name": event_name,
        "session_id": SESSION_ID,
        "cwd": "/workdir",
        "client_type": "kimi_code_cli",
        **fields,
    }


def _normalize(
    normalizer: KimiEventNormalizer,
    event_name: str,
    *,
    sequence: int = 1,
    generation: int = 1,
    **fields: Any,
) -> HookObservation:
    return normalizer.normalize_provider_event(
        _payload(event_name, **fields),
        channel_generation=generation,
        received_at_utc=f"2026-10-20T04:00:{sequence:02d}+00:00",
        sequence=sequence,
    )


def test_event_set_covers_the_subscribed_provider_contract() -> None:
    assert len(KIMI_EVENTS) == 20
    assert {"TaskStarted", "Notification", "StopFailure", "PermissionResult"} <= set(KIMI_EVENTS)


def test_session_start_sources_map_to_session_evidence() -> None:
    normalizer = KimiEventNormalizer()
    startup = _normalize(normalizer, "SessionStart", source="startup", model="kimi-code/k3")
    assert startup.kind == "session_started"
    assert startup.source == "startup"
    assert startup.session_id == SESSION_ID
    assert startup.turn_id is None

    resume = _normalize(normalizer, "SessionStart", sequence=2, source="resume")
    assert resume.kind == "session_started"
    assert resume.source == "resume"


def test_compaction_events_carry_trigger_evidence() -> None:
    normalizer = KimiEventNormalizer()
    started = _normalize(
        normalizer,
        "PreCompact",
        sequence=1,
        trigger="manual",
        token_count=28513,
    )
    assert started.kind == "maintenance_started"
    assert started.turn_state_hint == "maintenance"
    assert started.maintenance_trigger == "manual"

    ended = _normalize(
        normalizer,
        "PostCompact",
        sequence=2,
        trigger="auto",
        estimated_token_count=29056,
    )
    assert ended.kind == "maintenance_ended"
    assert ended.maintenance_trigger == "auto"
    assert normalizer.summary.compaction_events == 2


def test_prompt_content_parts_collapse_to_joined_text() -> None:
    normalizer = KimiEventNormalizer()
    observation = _normalize(
        normalizer,
        "UserPromptSubmit",
        prompt=[
            {"type": "text", "text": "Reply with "},
            {"type": "text", "text": "exactly: OK"},
            {"type": "image", "url": "file:///workdir/shot.png"},
        ],
        is_steer=False,
    )

    assert observation.kind == "prompt_submitted"
    assert observation.prompt_text == "Reply with exactly: OK"
    assert observation.prompt_part_count == 3
    assert observation.turn_id is None
    summary = normalizer.summary
    assert summary.prompt_submissions == 1
    assert summary.content_parts_collapsed == 3
    assert summary.prompt_part_types == ("image", "text")


def test_string_prompt_is_preserved_without_content_part_shape() -> None:
    normalizer = KimiEventNormalizer()

    submitted = _normalize(normalizer, "UserPromptSubmit", prompt="plain text")
    assert submitted.prompt_text == "plain text"
    assert submitted.prompt_part_count is None

    started = _normalize(
        normalizer,
        "TurnStarted",
        sequence=2,
        turn_id=0,
        origin_kind="user",
        prompt="plain text",
    )
    assert started.prompt_text == "plain text"
    assert started.prompt_part_count is None


def test_prompt_submission_does_not_arm_a_turn_by_itself() -> None:
    normalizer = KimiEventNormalizer()
    observation = _normalize(
        normalizer,
        "UserPromptSubmit",
        prompt=[{"type": "text", "text": "hi"}],
        is_steer=False,
    )

    assert observation.kind == "prompt_submitted"
    assert observation.turn_id is None
    assert observation.prompt_id is None
    assert observation.turn_state_hint == "active"
    assert observation.steer is False


def test_steer_flag_is_counted_without_a_turn_identifier() -> None:
    normalizer = KimiEventNormalizer()
    first = _normalize(normalizer, "UserPromptSubmit", prompt="one")
    second = _normalize(normalizer, "UserPromptSubmit", sequence=2, prompt="two", is_steer=True)

    assert first.steer is False
    assert second.steer is True
    assert normalizer.summary.steer_events == 1


def test_turn_started_carries_the_integer_turn_id_as_a_decimal_string() -> None:
    normalizer = KimiEventNormalizer()
    first = _normalize(
        normalizer,
        "TurnStarted",
        turn_id=0,
        origin_kind="user",
        prompt="hi",
    )
    assert first.kind == "turn_started"
    assert first.turn_id == "0"
    assert first.origin_kind == "user"
    assert first.origin_name is None
    assert first.turn_state_hint == "active"

    numeric_string = _normalize(normalizer, "TurnStarted", sequence=2, turn_id="12")
    assert numeric_string.turn_id == "12"

    boolean = _normalize(normalizer, "TurnStarted", sequence=3, turn_id=True)
    assert boolean.turn_id is None

    assert normalizer.summary.turn_started_events == 3


def test_nested_turn_started_is_scope_evidence() -> None:
    normalizer = KimiEventNormalizer()
    nested = _normalize(
        normalizer,
        "TurnStarted",
        turn_id=0,
        origin_kind="system_trigger",
        origin_name="subagent",
        prompt="<git-context>",
    )

    assert nested.kind == "turn_started"
    assert nested.origin_kind == "system_trigger"
    assert nested.origin_name == "subagent"
    assert nested.turn_id == "0"
    assert normalizer.summary.nested_turn_events == 1


def test_tool_events_pair_by_tool_call_id() -> None:
    normalizer = KimiEventNormalizer()
    started = _normalize(
        normalizer,
        "PreToolUse",
        tool_name="Bash",
        tool_call_id=TOOL_CALL_ID,
        tool_input={"command": "echo hi"},
    )
    assert started.kind == "tool_started"
    assert started.tool_use_id == TOOL_CALL_ID
    assert started.tool_name == "Bash"
    assert started.turn_id is None

    completed = _normalize(
        normalizer,
        "PostToolUse",
        sequence=2,
        tool_name="Bash",
        tool_call_id=TOOL_CALL_ID,
        tool_output="hi\n",
    )
    assert completed.kind == "tool_completed"
    assert completed.tool_use_id == TOOL_CALL_ID

    summary = normalizer.summary
    assert summary.pre_tool_uses == 1
    assert summary.post_tool_uses == 1
    assert summary.tool_pairs == 1
    assert summary.unpaired_post_tool_uses == 0


def test_post_tool_use_without_pre_tool_use_is_counted() -> None:
    normalizer = KimiEventNormalizer()
    completed = _normalize(
        normalizer,
        "PostToolUse",
        tool_name="Bash",
        tool_call_id=TOOL_CALL_ID,
    )

    assert completed.kind == "tool_completed"
    assert normalizer.summary.unpaired_post_tool_uses == 1


def test_tool_failure_pairs_and_carries_a_bounded_error_class() -> None:
    normalizer = KimiEventNormalizer()
    _normalize(
        normalizer,
        "PreToolUse",
        tool_name="Write",
        tool_call_id=TOOL_CALL_ID,
    )
    failed = _normalize(
        normalizer,
        "PostToolUseFailure",
        sequence=2,
        tool_name="Write",
        tool_call_id=TOOL_CALL_ID,
        error={
            "code": "internal",
            "message": "Tool was not run because the user rejected the approval request.",
            "retryable": False,
        },
    )

    assert failed.kind == "tool_failed"
    assert failed.tool_use_id == TOOL_CALL_ID
    assert failed.error_class == "internal"
    assert normalizer.summary.tool_failures == 1
    assert normalizer.summary.tool_pairs == 1
    assert "rejected the approval request" not in json.dumps(failed.to_payload())


def test_permission_events_pair_by_tool_call_id_and_carry_turn_id() -> None:
    normalizer = KimiEventNormalizer()
    _normalize(normalizer, "PreToolUse", tool_name="Write", tool_call_id=TOOL_CALL_ID)
    request = _normalize(
        normalizer,
        "PermissionRequest",
        sequence=2,
        turn_id=0,
        tool_name="Write",
        tool_call_id=TOOL_CALL_ID,
        action="Writing /workdir/out.txt",
        display={"kind": "file_io", "content": "SECRET_CONTENT"},
    )

    assert request.kind == "permission_requested"
    assert request.turn_id == "0"
    assert request.tool_use_id == TOOL_CALL_ID
    assert request.turn_state_hint == "blocked"
    assert normalizer.summary.permission_requests == 1
    assert normalizer.summary.permission_pairings == 1
    assert normalizer.summary.unpaired_permission_requests == 0

    resolved = _normalize(
        normalizer,
        "PermissionResult",
        sequence=3,
        turn_id=0,
        tool_name="Write",
        tool_call_id=TOOL_CALL_ID,
        decision="approved",
    )
    assert resolved.kind == "permission_resolved"
    assert resolved.permission_decision == "approved"
    assert resolved.turn_id == "0"


def test_permission_request_without_a_pre_tool_use_is_counted() -> None:
    normalizer = KimiEventNormalizer()
    request = _normalize(
        normalizer,
        "PermissionRequest",
        turn_id=0,
        tool_name="Write",
        tool_call_id=OTHER_TOOL_CALL_ID,
    )

    assert request.tool_use_id == OTHER_TOOL_CALL_ID
    assert normalizer.summary.permission_pairings == 0
    assert normalizer.summary.unpaired_permission_requests == 1


def test_permission_result_without_tool_call_id_is_counted() -> None:
    normalizer = KimiEventNormalizer()
    _normalize(normalizer, "PreToolUse", tool_name="Write", tool_call_id=TOOL_CALL_ID)
    request = _normalize(
        normalizer,
        "PermissionRequest",
        sequence=2,
        turn_id=0,
        tool_name="Write",
    )

    assert request.tool_use_id is None
    assert normalizer.summary.unpaired_permission_requests == 1


def test_unexercised_permission_decisions_are_counted() -> None:
    normalizer = KimiEventNormalizer()
    approved = _normalize(
        normalizer,
        "PermissionResult",
        sequence=1,
        turn_id=0,
        tool_call_id=TOOL_CALL_ID,
        decision="approved",
    )
    rejected = _normalize(
        normalizer,
        "PermissionResult",
        sequence=2,
        turn_id=0,
        tool_call_id=TOOL_CALL_ID,
        decision="rejected",
    )
    cancelled = _normalize(
        normalizer,
        "PermissionResult",
        sequence=3,
        turn_id=0,
        tool_call_id=TOOL_CALL_ID,
        decision="cancelled",
    )

    assert approved.permission_decision == "approved"
    assert rejected.permission_decision == "rejected"
    assert cancelled.permission_decision == "cancelled"
    summary = normalizer.summary
    assert summary.permission_results == 3
    assert summary.unexercised_permission_decisions == 1


def test_user_prompt_queued_records_queue_evidence_only() -> None:
    normalizer = KimiEventNormalizer()
    queued = _normalize(
        normalizer,
        "UserPromptQueued",
        prompt_id="msg_123",
        prompt=[{"type": "text", "text": "steered text"}],
        queue_length=1,
    )

    assert queued.kind == "prompt_queued"
    assert queued.prompt_id == "msg_123"
    assert queued.queue_length == 1
    assert queued.turn_id is None
    assert queued.prompt_text is None
    assert normalizer.summary.queued_prompts == 1

    numeric_string = _normalize(
        normalizer,
        "UserPromptQueued",
        sequence=2,
        prompt_id="msg_124",
        queue_length="2",
    )
    assert numeric_string.queue_length == 2


def test_subagent_events_carry_scope_evidence() -> None:
    normalizer = KimiEventNormalizer()
    started = _normalize(normalizer, "SubagentStart", agent_name="explore", prompt="SECRET")
    stopped = _normalize(normalizer, "SubagentStop", sequence=2, agent_name="explore")

    assert started.kind == "subagent_started"
    assert started.agent_name == "explore"
    assert stopped.kind == "subagent_stopped"
    assert stopped.agent_name == "explore"
    assert normalizer.summary.subagent_starts == 1
    assert normalizer.summary.subagent_stops == 1


def test_session_heartbeat_is_liveness_evidence_only() -> None:
    normalizer = KimiEventNormalizer()
    heartbeat = _normalize(normalizer, "SessionHeartbeat", uptime_ms=60001)

    assert heartbeat.kind == "session_heartbeat"
    assert heartbeat.turn_id is None
    assert heartbeat.turn_state_hint == "none"
    assert normalizer.summary.heartbeats == 1


def test_interrupt_maps_to_interrupted_terminal_evidence() -> None:
    normalizer = KimiEventNormalizer()
    interrupt = _normalize(normalizer, "Interrupt", turn_id=0, reason="cancelled")

    assert interrupt.kind == "turn_interrupted"
    assert interrupt.terminal_hint == "interrupted"
    assert interrupt.turn_state_hint == "ended"
    assert interrupt.reason == "cancelled"
    assert interrupt.turn_id == "0"
    assert normalizer.summary.interrupts == 1


def test_stop_and_stop_failure_map_terminal_hints() -> None:
    normalizer = KimiEventNormalizer()
    stopped = _normalize(normalizer, "Stop", stop_hook_active=False)
    assert stopped.kind == "turn_completed"
    assert stopped.terminal_hint == "success"
    assert stopped.stop_hook_active is False
    assert stopped.turn_id is None

    failed = _normalize(
        normalizer,
        "StopFailure",
        sequence=2,
        error_type="provider_failure",
    )
    assert failed.kind == "turn_failed"
    assert failed.terminal_hint == "known_failure"
    assert failed.error_class == "provider_failure"


def test_session_end_carries_the_reason() -> None:
    normalizer = KimiEventNormalizer()
    ended = _normalize(normalizer, "SessionEnd", reason="exit")

    assert ended.kind == "session_ended"
    assert ended.reason == "exit"
    assert ended.turn_state_hint == "ended"


def test_tolerated_families_are_counted_not_mapped() -> None:
    normalizer = KimiEventNormalizer()
    task = _normalize(normalizer, "TaskStarted", kind="agent")
    notification = _normalize(normalizer, "Notification", message="SECRET")
    mystery = _normalize(normalizer, "MysteryEvent", sequence=3)

    assert task.kind == "unknown"
    assert notification.kind == "unknown"
    assert mystery.kind == "unknown"
    summary = normalizer.summary
    assert summary.unknown_events == 3
    assert summary.tolerated_family_events == 2
    assert summary.unknown_event_names == ("MysteryEvent", "Notification", "TaskStarted")
    assert "TaskStarted" not in summary.unavailable_families
    assert "Notification" not in summary.unavailable_families
    assert "StopFailure" in summary.unavailable_families
    assert "SECRET" not in json.dumps(notification.to_payload())


def test_silent_floor_families_are_reported_when_absent() -> None:
    normalizer = KimiEventNormalizer()
    _normalize(normalizer, "SessionStart", source="startup")

    summary = normalizer.summary
    assert summary.unavailable_families == ("StopFailure", "TaskStarted", "Notification")
    assert set(summary.unseen_families) == set(KIMI_EVENTS) - {"SessionStart"}


@pytest.mark.parametrize(
    ("payload", "reason"),
    [
        (None, "not_object"),
        ([], "not_object"),
        ("payload", "not_object"),
        ({"session_id": SESSION_ID}, "missing_event_name"),
        ({"hook_event_name": 5}, "missing_event_name"),
        ({"hook_event_name": ""}, "missing_event_name"),
    ],
)
def test_malformed_payloads_are_counted(payload: object, reason: str) -> None:
    normalizer = KimiEventNormalizer()
    observation = normalizer.normalize_provider_event(
        payload,
        channel_generation=1,
        received_at_utc="2026-10-20T04:00:00+00:00",
        sequence=1,
    )

    assert observation.kind == "unknown"
    assert observation.malformed is True
    assert observation.malformed_reason == reason
    assert normalizer.summary.malformed_events == 1


def test_tool_text_never_reaches_the_observation() -> None:
    normalizer = KimiEventNormalizer()
    _normalize(
        normalizer,
        "PreToolUse",
        tool_name="Bash",
        tool_call_id=TOOL_CALL_ID,
        tool_input={"command": "cat SECRET_COMMAND"},
    )
    completed = _normalize(
        normalizer,
        "PostToolUse",
        sequence=2,
        tool_name="Bash",
        tool_call_id=TOOL_CALL_ID,
        tool_output="SECRET_OUTPUT",
    )
    started = _normalize(
        normalizer,
        "SubagentStart",
        sequence=3,
        agent_name="explore",
        prompt="SECRET_SUBAGENT_PROMPT",
    )
    stopped = _normalize(
        normalizer,
        "SubagentStop",
        sequence=4,
        agent_name="explore",
        response="SECRET_SUBAGENT_RESPONSE",
    )
    request = _normalize(
        normalizer,
        "PermissionRequest",
        sequence=5,
        turn_id=0,
        tool_name="Write",
        tool_call_id=OTHER_TOOL_CALL_ID,
        tool_input={"content": "SECRET_CONTENT", "path": "/workdir/out.txt"},
        display={"kind": "file_io", "content": "SECRET_CONTENT"},
        action="Writing SECRET_CONTENT",
    )

    for observation in (completed, started, stopped, request):
        serialized = json.dumps(observation.to_payload())
        assert "SECRET" not in serialized


def test_envelope_normalization_carries_stamps_and_generation_boundaries() -> None:
    normalizer = KimiEventNormalizer()
    event = normalizer.normalize_envelope(
        HookEventEnvelope(
            received_at_utc="2026-10-20T04:00:00+00:00",
            channel_generation=2,
            via="http",
            provider_event=_payload("TurnStarted", turn_id=1, origin_kind="user"),
            sequence=7,
        )
    )
    assert event.channel_generation == 2
    assert event.sequence == 7
    assert event.turn_id == "1"

    boundary = normalizer.normalize_envelope(
        HookEventEnvelope(
            received_at_utc="2026-10-20T04:00:01+00:00",
            channel_generation=3,
            via="http",
            provider_event={},
            sequence=None,
            record_type="generation_boundary",
        )
    )
    assert boundary.kind == "generation_started"
    assert boundary.event_name == "generation_boundary"
    assert boundary.channel_generation == 3


def test_open_tool_capacity_must_be_positive() -> None:
    with pytest.raises(ValueError):
        KimiEventNormalizer(open_tool_capacity=0)
