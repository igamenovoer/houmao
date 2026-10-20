"""Unit tests for the Codex hook event normalizer."""

from __future__ import annotations

import json
from typing import Any

import pytest

from houmao.hook_observation.codex_normalizer import CodexEventNormalizer
from houmao.hook_observation.models import HookEventEnvelope, HookObservation

SESSION_ID = "session-1"
TURN_ID = "01a15785-9567-7093-b921-201af65bd4b0"
OTHER_TURN_ID = "01a15785-ad78-75e0-b940-bad4dfc80868"
TOOL_USE_ID = "exec-a78c846f-d864-46fd-b610-6d24a009b007"


def _payload(event_name: str, **fields: Any) -> dict[str, Any]:
    return {
        "hook_event_name": event_name,
        "session_id": SESSION_ID,
        "model": "gpt-6.1-sol",
        "permission_mode": "default",
        "cwd": "/workdir",
        "transcript_path": "/codex-home/sessions/rollout-01.jsonl",
        **fields,
    }


def _normalize(
    normalizer: CodexEventNormalizer,
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


def test_session_start_sources_map_to_session_evidence() -> None:
    normalizer = CodexEventNormalizer()
    startup = _normalize(normalizer, "SessionStart", source="startup")
    assert startup.kind == "session_started"
    assert startup.source == "startup"
    assert startup.session_id == SESSION_ID
    assert startup.turn_id is None

    resume = _normalize(normalizer, "SessionStart", sequence=2, source="resume")
    assert resume.kind == "session_started"
    assert resume.source == "resume"

    compact = _normalize(normalizer, "SessionStart", sequence=3, source="compact")
    assert compact.kind == "session_started"
    assert compact.source == "compact"


def test_compaction_events_carry_trigger_evidence() -> None:
    normalizer = CodexEventNormalizer()
    started = _normalize(
        normalizer,
        "PreCompact",
        sequence=1,
        turn_id="compact-turn",
        trigger="manual",
    )
    assert started.kind == "maintenance_started"
    assert started.turn_state_hint == "maintenance"
    assert started.maintenance_trigger == "manual"

    ended = _normalize(
        normalizer,
        "PostCompact",
        sequence=2,
        turn_id="compact-turn",
        trigger="auto",
    )
    assert ended.kind == "maintenance_ended"
    assert ended.maintenance_trigger == "auto"


def test_prompt_submission_carries_turn_epoch_and_detects_steer() -> None:
    normalizer = CodexEventNormalizer()
    first = _normalize(normalizer, "UserPromptSubmit", sequence=1, turn_id=TURN_ID)
    assert first.kind == "prompt_submitted"
    assert first.turn_id == TURN_ID
    assert first.prompt_id == TURN_ID
    assert first.steer is False
    assert first.provider_initiated is False

    steer = _normalize(normalizer, "UserPromptSubmit", sequence=2, turn_id=TURN_ID)
    assert steer.kind == "prompt_submitted"
    assert steer.steer is True
    assert normalizer.summary.steer_events == 1

    terminal = _normalize(
        normalizer,
        "Stop",
        sequence=3,
        turn_id=TURN_ID,
        stop_hook_active=False,
    )
    assert terminal.kind == "turn_completed"

    fresh = _normalize(normalizer, "UserPromptSubmit", sequence=4, turn_id=TURN_ID)
    assert fresh.steer is False
    assert normalizer.summary.steer_events == 1


def test_stop_hook_active_keeps_the_turn_epoch_open() -> None:
    normalizer = CodexEventNormalizer()
    _normalize(normalizer, "UserPromptSubmit", sequence=1, turn_id=TURN_ID)
    continuation = _normalize(
        normalizer,
        "Stop",
        sequence=2,
        turn_id=TURN_ID,
        stop_hook_active=True,
    )
    assert continuation.kind == "turn_completed"
    assert continuation.stop_hook_active is True

    repeated = _normalize(normalizer, "UserPromptSubmit", sequence=3, turn_id=TURN_ID)
    assert repeated.steer is True

    _normalize(normalizer, "Stop", sequence=4, turn_id=TURN_ID, stop_hook_active=False)
    after = _normalize(normalizer, "UserPromptSubmit", sequence=5, turn_id=TURN_ID)
    assert after.steer is False


def test_interrupt_maps_to_interrupted_terminal_and_clears_the_epoch() -> None:
    normalizer = CodexEventNormalizer()
    _normalize(normalizer, "UserPromptSubmit", sequence=1, turn_id=TURN_ID)
    interrupt = _normalize(normalizer, "Interrupt", sequence=2, turn_id=TURN_ID)

    assert interrupt.kind == "turn_interrupted"
    assert interrupt.terminal_hint == "interrupted"
    assert interrupt.turn_state_hint == "ended"

    repeated = _normalize(normalizer, "UserPromptSubmit", sequence=3, turn_id=TURN_ID)
    assert repeated.steer is False


def test_session_end_maps_to_presence_ending_evidence() -> None:
    normalizer = CodexEventNormalizer()
    ended = _normalize(normalizer, "SessionEnd", reason="other")

    assert ended.kind == "session_ended"
    assert ended.turn_state_hint == "ended"
    assert ended.session_id == SESSION_ID


def test_tool_events_pair_by_tool_use_id() -> None:
    normalizer = CodexEventNormalizer()
    _normalize(normalizer, "UserPromptSubmit", sequence=1, turn_id=TURN_ID)
    started = _normalize(
        normalizer,
        "PreToolUse",
        sequence=2,
        turn_id=TURN_ID,
        tool_name="Bash",
        tool_use_id=TOOL_USE_ID,
        tool_input={"command": "echo hi"},
    )
    assert started.kind == "tool_started"
    assert started.tool_name == "Bash"
    assert started.tool_use_id == TOOL_USE_ID

    completed = _normalize(
        normalizer,
        "PostToolUse",
        sequence=3,
        turn_id=TURN_ID,
        tool_name="Bash",
        tool_use_id=TOOL_USE_ID,
        tool_input={"command": "echo hi"},
        tool_response="hi\n",
    )
    assert completed.kind == "tool_completed"
    assert completed.tool_use_id == TOOL_USE_ID
    assert normalizer.summary.unpaired_post_tool_uses == 0


def test_post_tool_use_without_pre_tool_use_is_counted() -> None:
    normalizer = CodexEventNormalizer()
    completed = _normalize(
        normalizer,
        "PostToolUse",
        sequence=1,
        turn_id=TURN_ID,
        tool_name="Bash",
        tool_use_id=TOOL_USE_ID,
    )

    assert completed.kind == "tool_completed"
    assert normalizer.summary.unpaired_post_tool_uses == 1


def test_permission_request_pairs_back_to_preceding_pre_tool_use() -> None:
    normalizer = CodexEventNormalizer()
    _normalize(normalizer, "UserPromptSubmit", sequence=1, turn_id=TURN_ID)
    _normalize(
        normalizer,
        "PreToolUse",
        sequence=2,
        turn_id=TURN_ID,
        tool_name="Bash",
        tool_use_id=TOOL_USE_ID,
        tool_input={"command": "printf hello > /tmp/x"},
    )
    request = _normalize(
        normalizer,
        "PermissionRequest",
        sequence=3,
        turn_id=TURN_ID,
        tool_name="Bash",
        tool_input={
            "command": "printf hello > /tmp/x",
            "description": "May I write the file?",
        },
    )

    assert request.kind == "permission_requested"
    assert request.tool_use_id == TOOL_USE_ID
    assert request.turn_state_hint == "blocked"
    summary = normalizer.summary
    assert summary.permission_requests == 1
    assert summary.permission_pairings == 1
    assert summary.unpaired_permission_requests == 0


def test_permission_request_command_mismatch_does_not_pair() -> None:
    normalizer = CodexEventNormalizer()
    _normalize(normalizer, "UserPromptSubmit", sequence=1, turn_id=TURN_ID)
    _normalize(
        normalizer,
        "PreToolUse",
        sequence=2,
        turn_id=TURN_ID,
        tool_name="Bash",
        tool_use_id=TOOL_USE_ID,
        tool_input={"command": "echo first"},
    )
    request = _normalize(
        normalizer,
        "PermissionRequest",
        sequence=3,
        turn_id=TURN_ID,
        tool_name="Bash",
        tool_input={"command": "echo second", "description": "other call"},
    )

    assert request.kind == "permission_requested"
    assert request.tool_use_id is None
    assert normalizer.summary.permission_pairings == 0
    assert normalizer.summary.unpaired_permission_requests == 1


def test_permission_request_from_another_turn_does_not_pair() -> None:
    normalizer = CodexEventNormalizer()
    _normalize(normalizer, "UserPromptSubmit", sequence=1, turn_id=TURN_ID)
    _normalize(
        normalizer,
        "PreToolUse",
        sequence=2,
        turn_id=TURN_ID,
        tool_name="Bash",
        tool_use_id=TOOL_USE_ID,
        tool_input={"command": "echo hi"},
    )
    request = _normalize(
        normalizer,
        "PermissionRequest",
        sequence=3,
        turn_id=OTHER_TURN_ID,
        tool_name="Bash",
        tool_input={"command": "echo hi"},
    )

    assert request.tool_use_id is None
    assert normalizer.summary.unpaired_permission_requests == 1


def test_a_new_epoch_clears_the_previous_pairing_candidate() -> None:
    normalizer = CodexEventNormalizer()
    _normalize(normalizer, "UserPromptSubmit", sequence=1, turn_id=TURN_ID)
    _normalize(
        normalizer,
        "PreToolUse",
        sequence=2,
        turn_id=TURN_ID,
        tool_name="Bash",
        tool_use_id=TOOL_USE_ID,
        tool_input={"command": "echo hi"},
    )
    _normalize(normalizer, "Stop", sequence=3, turn_id=TURN_ID, stop_hook_active=False)
    _normalize(normalizer, "UserPromptSubmit", sequence=4, turn_id=OTHER_TURN_ID)
    request = _normalize(
        normalizer,
        "PermissionRequest",
        sequence=5,
        turn_id=OTHER_TURN_ID,
        tool_name="Bash",
        tool_input={"command": "echo hi"},
    )

    assert request.tool_use_id is None
    assert normalizer.summary.unpaired_permission_requests == 1


def test_subagent_and_model_request_families_are_counted_not_mapped() -> None:
    normalizer = CodexEventNormalizer()
    model_request = _normalize(normalizer, "PreModelRequest", sequence=1, turn_id=TURN_ID)
    subagent = _normalize(
        normalizer,
        "SubagentStart",
        sequence=2,
        turn_id=TURN_ID,
        agent_id="agent-7",
        agent_type="explorer",
    )

    assert model_request.kind == "unknown"
    assert subagent.kind == "unknown"
    assert subagent.agent_id == "agent-7"
    summary = normalizer.summary
    assert summary.unknown_events == 2
    assert summary.unknown_event_names == ("PreModelRequest", "SubagentStart")
    assert "PreModelRequest" not in summary.unavailable_families
    assert "SubagentStart" not in summary.unavailable_families
    assert "PostModelRequest" in summary.unavailable_families
    assert "SubagentStop" in summary.unavailable_families


def test_unknown_event_name_is_tolerated_and_counted() -> None:
    normalizer = CodexEventNormalizer()
    observation = _normalize(normalizer, "Notification", sequence=1, message="SECRET")

    assert observation.kind == "unknown"
    assert observation.malformed is False
    assert normalizer.summary.unknown_events == 1
    assert "SECRET" not in json.dumps(observation.to_payload())


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
    normalizer = CodexEventNormalizer()
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


def test_prompt_and_tool_text_never_reach_the_observation() -> None:
    normalizer = CodexEventNormalizer()
    _normalize(
        normalizer,
        "UserPromptSubmit",
        sequence=1,
        turn_id=TURN_ID,
        prompt="SECRET_PROMPT",
    )
    _normalize(
        normalizer,
        "PreToolUse",
        sequence=2,
        turn_id=TURN_ID,
        tool_name="Bash",
        tool_use_id=TOOL_USE_ID,
        tool_input={"command": "cat SECRET_COMMAND"},
    )
    request = _normalize(
        normalizer,
        "PermissionRequest",
        sequence=3,
        turn_id=TURN_ID,
        tool_name="Bash",
        tool_input={"command": "cat SECRET_COMMAND", "description": "SECRET_DESCRIPTION"},
    )
    completed = _normalize(
        normalizer,
        "PostToolUse",
        sequence=4,
        turn_id=TURN_ID,
        tool_name="Bash",
        tool_use_id=TOOL_USE_ID,
        tool_response="SECRET_OUTPUT",
    )
    stop = _normalize(
        normalizer,
        "Stop",
        sequence=5,
        turn_id=TURN_ID,
        stop_hook_active=False,
        last_assistant_message="SECRET_ANSWER",
    )

    for observation in (request, completed, stop):
        serialized = json.dumps(observation.to_payload())
        assert "SECRET" not in serialized


def test_envelope_normalization_carries_stamps_and_generation_boundaries() -> None:
    normalizer = CodexEventNormalizer()
    event = normalizer.normalize_envelope(
        HookEventEnvelope(
            received_at_utc="2026-10-20T04:00:00+00:00",
            channel_generation=2,
            via="http",
            provider_event=_payload("UserPromptSubmit", turn_id=TURN_ID),
            sequence=7,
        )
    )
    assert event.channel_generation == 2
    assert event.sequence == 7

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
