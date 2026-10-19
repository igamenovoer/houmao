"""Unit tests for Claude hook event normalization."""

from __future__ import annotations

import json

import pytest

import houmao.hook_observation.normalizer as normalizer_module
from houmao.hook_observation.models import HookEventEnvelope, HookObservation
from houmao.hook_observation.normalizer import normalize_envelope, normalize_provider_event


def _envelope(
    payload: object,
    *,
    generation: int = 1,
    sequence: int | None = 1,
    received_at_utc: str = "2026-10-19T13:17:58+00:00",
) -> HookEventEnvelope:
    return HookEventEnvelope(
        received_at_utc=received_at_utc,
        channel_generation=generation,
        via="http",
        provider_event=payload if isinstance(payload, dict) else {},
        sequence=sequence,
    )


def _normalize(payload: object) -> HookObservation:
    return normalize_provider_event(
        payload,
        channel_generation=1,
        received_at_utc="2026-10-19T13:17:58+00:00",
        sequence=1,
    )


def test_prompt_text_never_reaches_the_observation() -> None:
    payload = {
        "hook_event_name": "UserPromptSubmit",
        "session_id": "session-1",
        "prompt_id": "prompt-1",
        "prompt": "Reply with exactly: SECRET_PROMPT",
        "permission_mode": "bypassPermissions",
    }
    observation = _normalize(payload)

    assert observation.kind == "prompt_submitted"
    assert observation.turn_state_hint == "active"
    assert observation.prompt_id == "prompt-1"
    assert observation.provider_initiated is False
    assert "SECRET_PROMPT" not in json.dumps(observation.to_payload())


def test_ghost_turn_prompt_is_provider_initiated() -> None:
    payload = {
        "hook_event_name": "UserPromptSubmit",
        "session_id": "session-1",
        "prompt_id": "ghost-1",
        "prompt": (
            "<task-notification>\n"
            "<task-id>byx3d0ps2</task-id>\n"
            "<tool-use-id>toolu-1</tool-use-id>\n"
            "<status>completed</status>\n"
            "<summary>Background command completed (exit code 0)</summary>\n"
            "</task-notification>"
        ),
    }
    observation = _normalize(payload)

    assert observation.kind == "prompt_submitted"
    assert observation.provider_initiated is True
    assert "task-notification" not in json.dumps(observation.to_payload())


def test_session_start_variants_carry_source_and_identity() -> None:
    startup = _normalize(
        {
            "hook_event_name": "SessionStart",
            "session_id": "session-1",
            "source": "startup",
            "model": "deepseek-flash[1m]",
            "cwd": "/tmp/workdir",
            "transcript_path": "/tmp/transcript.jsonl",
            "unknown_field": {"nested": True},
        }
    )
    assert startup.kind == "session_started"
    assert startup.source == "startup"
    assert startup.session_id == "session-1"
    assert startup.turn_state_hint == "none"
    assert startup.malformed is False

    compact = _normalize(
        {
            "hook_event_name": "SessionStart",
            "session_id": "session-1",
            "source": "compact",
            "prompt_id": "compact-prompt",
        }
    )
    assert compact.kind == "session_started"
    assert compact.source == "compact"
    assert compact.prompt_id == "compact-prompt"

    resume = _normalize(
        {
            "hook_event_name": "SessionStart",
            "session_id": "session-1",
            "source": "resume",
            "context_tokens": 55846,
            "estimated_cache_write_usd": 0.349,
            "prompt_cache_likely_expired": False,
            "seconds_since_last_response": 2,
        }
    )
    assert resume.kind == "session_started"
    assert resume.source == "resume"
    assert resume.session_id == "session-1"


def test_permission_request_matches_observed_shape() -> None:
    observation = _normalize(
        {
            "hook_event_name": "PermissionRequest",
            "session_id": "session-1",
            "prompt_id": "prompt-1",
            "permission_mode": "default",
            "effort": {"level": "max"},
            "tool_name": "Write",
            "tool_input": {"file_path": "/tmp/x", "content": "SECRET"},
            "permission_suggestions": [
                {"type": "setMode", "destination": "session", "mode": "acceptEdits"}
            ],
        }
    )

    assert observation.kind == "permission_requested"
    assert observation.turn_state_hint == "blocked"
    assert observation.tool_name == "Write"
    assert observation.tool_use_id is None
    assert "SECRET" not in json.dumps(observation.to_payload())


def test_post_tool_use_is_activity_with_correlation_ids() -> None:
    observation = _normalize(
        {
            "hook_event_name": "PostToolUse",
            "session_id": "session-1",
            "prompt_id": "prompt-1",
            "tool_name": "Bash",
            "tool_use_id": "toolu-1",
            "tool_input": {"command": "cat /tmp/x"},
            "tool_response": {"interrupted": False},
            "duration_ms": 44,
        }
    )

    assert observation.kind == "activity"
    assert observation.turn_state_hint == "active"
    assert observation.tool_name == "Bash"
    assert observation.tool_use_id == "toolu-1"
    assert observation.is_interrupt is None


@pytest.mark.parametrize("is_interrupt", [True, False])
def test_post_tool_use_failure_carries_tool_interrupt(is_interrupt: bool) -> None:
    observation = _normalize(
        {
            "hook_event_name": "PostToolUseFailure",
            "session_id": "session-1",
            "prompt_id": "prompt-1",
            "tool_name": "Bash",
            "tool_use_id": "toolu-1",
            "error": "tool failed",
            "is_interrupt": is_interrupt,
            "duration_ms": 12,
        }
    )

    assert observation.kind == "activity"
    assert observation.turn_state_hint == "active"
    assert observation.is_interrupt is is_interrupt
    assert observation.tool_use_id == "toolu-1"


def test_compaction_events_carry_trigger() -> None:
    started = _normalize(
        {
            "hook_event_name": "PreCompact",
            "session_id": "session-1",
            "prompt_id": "compact-prompt",
            "trigger": "manual",
            "custom_instructions": None,
        }
    )
    assert started.kind == "maintenance_started"
    assert started.turn_state_hint == "maintenance"
    assert started.maintenance_trigger == "manual"

    ended = _normalize(
        {
            "hook_event_name": "PostCompact",
            "session_id": "session-1",
            "prompt_id": "compact-prompt",
            "trigger": "manual",
            "compact_summary": "SECRET_SUMMARY",
        }
    )
    assert ended.kind == "maintenance_ended"
    assert ended.turn_state_hint == "none"
    assert ended.maintenance_trigger == "manual"
    assert "SECRET_SUMMARY" not in json.dumps(ended.to_payload())


def test_stop_summarizes_background_work_without_text() -> None:
    observation = _normalize(
        {
            "hook_event_name": "Stop",
            "session_id": "session-1",
            "prompt_id": "prompt-1",
            "permission_mode": "bypassPermissions",
            "stop_hook_active": False,
            "last_assistant_message": "SECRET_ANSWER",
            "background_tasks": [
                {
                    "command": "sleep 90",
                    "description": "SECRET_TASK",
                    "id": "byx3d0ps2",
                    "status": "running",
                    "type": "shell",
                }
            ],
            "session_crons": [],
            "effort": {"level": "max"},
        }
    )

    assert observation.kind == "turn_completed"
    assert observation.terminal_hint == "success"
    assert observation.turn_state_hint == "ended"
    assert observation.stop_hook_active is False
    assert observation.background_work_pending is True
    assert len(observation.background_tasks) == 1
    assert observation.background_tasks[0].task_id == "byx3d0ps2"
    assert observation.background_tasks[0].status == "running"
    assert observation.background_tasks[0].task_type == "shell"
    assert observation.last_assistant_message_present is True
    serialized = json.dumps(observation.to_payload())
    assert "SECRET_ANSWER" not in serialized
    assert "SECRET_TASK" not in serialized
    assert "sleep 90" not in serialized


def test_stop_empty_and_malformed_background_tasks() -> None:
    empty = _normalize(
        {
            "hook_event_name": "Stop",
            "last_assistant_message": "",
            "background_tasks": [],
            "stop_hook_active": False,
        }
    )
    assert empty.background_work_pending is False
    assert empty.background_tasks == ()
    assert empty.last_assistant_message_present is False

    malformed = _normalize(
        {
            "hook_event_name": "Stop",
            "background_tasks": "not-an-array",
            "stop_hook_active": "false",
        }
    )
    assert malformed.background_work_pending is None
    assert malformed.stop_hook_active is None
    assert malformed.last_assistant_message_present is None


@pytest.mark.parametrize(
    ("error", "error_details", "expected"),
    [
        ("rate_limit_error", None, "rate_limit_error"),
        ({"type": "overloaded_error", "message": "SECRET"}, None, "overloaded_error"),
        (None, {"code": "context_length_exceeded"}, "context_length_exceeded"),
        (None, None, None),
        ("x" * 200, None, "unclassified"),
    ],
)
def test_stop_failure_records_bounded_error_class(
    error: object,
    error_details: object,
    expected: str | None,
) -> None:
    observation = _normalize(
        {
            "hook_event_name": "StopFailure",
            "session_id": "session-1",
            "prompt_id": "prompt-1",
            "error": error,
            "error_details": error_details,
            "last_assistant_message": "SECRET_API_ERROR",
        }
    )

    assert observation.kind == "turn_failed"
    assert observation.terminal_hint == "known_failure"
    assert observation.turn_state_hint == "ended"
    assert observation.error_class == expected
    assert observation.background_work_pending is None
    assert observation.last_assistant_message_present is True
    assert "SECRET" not in json.dumps(observation.to_payload())


def test_unknown_event_is_tolerated_and_not_malformed() -> None:
    observation = _normalize(
        {
            "hook_event_name": "Notification",
            "session_id": "session-1",
            "notification_type": "permission_prompt",
            "message": "SECRET",
        }
    )

    assert observation.kind == "unknown"
    assert observation.event_name == "Notification"
    assert observation.malformed is False
    assert "SECRET" not in json.dumps(observation.to_payload())


@pytest.mark.parametrize(
    ("payload", "reason"),
    [
        (None, "not_object"),
        ([], "not_object"),
        ("payload", "not_object"),
        ({"session_id": "session-1"}, "missing_event_name"),
        ({"hook_event_name": 5}, "missing_event_name"),
        ({"hook_event_name": ""}, "missing_event_name"),
    ],
)
def test_malformed_payloads_are_counted_observations(payload: object, reason: str) -> None:
    observation = _normalize(payload)

    assert observation.kind == "unknown"
    assert observation.malformed is True
    assert observation.malformed_reason == reason


def test_oversized_payload_is_malformed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(normalizer_module, "MAX_PROVIDER_EVENT_BYTES", 200)
    observation = _normalize(
        {
            "hook_event_name": "Stop",
            "last_assistant_message": "x" * 300,
        }
    )

    assert observation.kind == "unknown"
    assert observation.malformed is True
    assert observation.malformed_reason == "oversized"
    assert "xxx" not in json.dumps(observation.to_payload())


def test_non_serializable_payload_is_malformed() -> None:
    observation = normalize_provider_event(
        {"hook_event_name": "Stop", "value": object()},
        channel_generation=1,
        received_at_utc="2026-10-19T13:17:58+00:00",
        sequence=1,
    )

    assert observation.malformed is True
    assert observation.malformed_reason == "not_serializable"


def test_generation_boundary_normalizes_to_generation_started() -> None:
    envelope = HookEventEnvelope(
        received_at_utc="2026-10-19T13:17:58+00:00",
        channel_generation=2,
        via="http",
        provider_event={},
        sequence=None,
        record_type="generation_boundary",
    )

    observation = normalize_envelope(envelope)

    assert observation.kind == "generation_started"
    assert observation.event_name == "generation_boundary"
    assert observation.channel_generation == 2
    assert observation.sequence is None
    assert observation.malformed is False


def test_envelope_normalization_carries_stamps() -> None:
    observation = normalize_envelope(
        _envelope(
            {"hook_event_name": "UserPromptSubmit", "prompt_id": "p1"},
            generation=3,
            sequence=17,
            received_at_utc="2026-10-19T14:00:00+00:00",
        )
    )

    assert observation.channel_generation == 3
    assert observation.sequence == 17
    assert observation.received_at_utc == "2026-10-19T14:00:00+00:00"
