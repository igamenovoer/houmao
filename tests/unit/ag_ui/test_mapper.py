from __future__ import annotations

import json

from houmao.ag_ui.mapper import AgUiEventMapper
from houmao.ag_ui.runtime import AgUiTuiObservation
from houmao.agents.realm_controller.backends.headless_output import CanonicalHeadlessEvent


def _payloads(events: list[object]) -> list[dict[str, object]]:
    """Return JSON payloads from Pydantic AG-UI events."""

    return [event.model_dump(mode="json", by_alias=True, exclude_none=True) for event in events]  # type: ignore[attr-defined]


def test_mapper_maps_headless_assistant_text_sequence() -> None:
    mapper = AgUiEventMapper(thread_id="thread-1", run_id="run-1")
    event = CanonicalHeadlessEvent(
        kind="assistant",
        message="assistant",
        turn_index=2,
        provider="codex",
        provider_event_type="assistant.text",
        data={"text": "hello from headless"},
    )

    payloads = _payloads(mapper.map_headless_event(event, sequence_index=5))

    assert [payload["type"] for payload in payloads] == [
        "TEXT_MESSAGE_START",
        "TEXT_MESSAGE_CONTENT",
        "TEXT_MESSAGE_END",
    ]
    assert payloads[0]["messageId"] == payloads[1]["messageId"] == payloads[2]["messageId"]
    assert payloads[1]["delta"] == "hello from headless"


def test_mapper_maps_headless_tool_call_and_result_with_stable_id() -> None:
    mapper = AgUiEventMapper(thread_id="thread-1", run_id="run-1")
    request_event = CanonicalHeadlessEvent(
        kind="action_request",
        message="command echo",
        turn_index=1,
        provider="codex",
        provider_event_type="assistant.tool_call",
        data={
            "action_id": "action-1",
            "name": "command",
            "command": "echo ok",
            "arguments_summary": "echo ok",
        },
    )
    result_event = CanonicalHeadlessEvent(
        kind="action_result",
        message="command completed",
        turn_index=1,
        provider="codex",
        provider_event_type="assistant.tool_result",
        data={
            "action_id": "action-1",
            "name": "command",
            "status": "completed",
            "result_summary": "ok",
        },
    )

    request_payloads = _payloads(mapper.map_headless_event(request_event, sequence_index=1))
    result_payloads = _payloads(mapper.map_headless_event(result_event, sequence_index=2))

    assert [payload["type"] for payload in request_payloads] == [
        "TOOL_CALL_START",
        "TOOL_CALL_ARGS",
        "TOOL_CALL_END",
    ]
    assert request_payloads[0]["toolCallId"] == "run-1:tool:action-1"
    assert request_payloads[0]["toolCallName"] == "command"
    assert json.loads(str(request_payloads[1]["delta"])) == {"command": "echo ok"}
    assert result_payloads[0]["type"] == "TOOL_CALL_RESULT"
    assert result_payloads[0]["toolCallId"] == "run-1:tool:action-1"
    assert result_payloads[0]["content"] == "ok"


def test_mapper_redacts_reasoning_by_default_without_readable_content() -> None:
    mapper = AgUiEventMapper(thread_id="thread-1", run_id="run-1")
    event = CanonicalHeadlessEvent(
        kind="reasoning",
        message="private chain",
        turn_index=1,
        provider="codex",
        provider_event_type="reasoning",
        data={"text": "private chain"},
    )

    payloads = _payloads(mapper.map_headless_event(event, sequence_index=1))

    assert payloads == [
        {
            "type": "CUSTOM",
            "name": "houmao.reasoning_redacted",
            "value": {
                "source": "houmao.headless",
                "kind": "reasoning",
                "redacted": True,
                "provider": "codex",
                "turnIndex": 1,
            },
        }
    ]


def test_mapper_maps_progress_and_diagnostics_to_activity_or_custom() -> None:
    mapper = AgUiEventMapper(thread_id="thread-1", run_id="run-1")
    progress = CanonicalHeadlessEvent(
        kind="progress",
        message="working",
        turn_index=1,
        provider="codex",
        provider_event_type="progress",
        data={"status": "running"},
    )
    diagnostic = CanonicalHeadlessEvent(
        kind="diagnostic",
        message="warning",
        turn_index=1,
        provider="codex",
        provider_event_type="stderr",
        data={"severity": "warning"},
    )

    progress_payload = _payloads(mapper.map_headless_event(progress, sequence_index=1))[0]
    diagnostic_payload = _payloads(mapper.map_headless_event(diagnostic, sequence_index=2))[0]

    assert progress_payload["type"] == "ACTIVITY_SNAPSHOT"
    assert progress_payload["activityType"] == "houmao.gateway.progress"
    assert json.loads(str(progress_payload["content"]))["message"] == "working"
    assert diagnostic_payload["type"] == "CUSTOM"
    assert diagnostic_payload["name"] == "houmao.gateway.diagnostic"
    assert diagnostic_payload["value"]["message"] == "warning"  # type: ignore[index]


def test_mapper_maps_tui_status_and_final_text_without_tool_calls() -> None:
    mapper = AgUiEventMapper(thread_id="thread-1", run_id="run-1")
    observation = AgUiTuiObservation(
        available=True,
        status={"backend": "local_interactive", "turnPhase": "ready"},
        activity="TUI ready",
        final_text="final answer",
    )

    payloads = _payloads(
        mapper.map_tui_observation(observation, sequence_index=4, include_final_text=True)
    )

    assert [payload["type"] for payload in payloads] == [
        "ACTIVITY_SNAPSHOT",
        "TEXT_MESSAGE_START",
        "TEXT_MESSAGE_CONTENT",
        "TEXT_MESSAGE_END",
    ]
    assert payloads[0]["activityType"] == "houmao.tui.status"
    assert payloads[2]["delta"] == "final answer"
    assert "TOOL_CALL_START" not in {payload["type"] for payload in payloads}
