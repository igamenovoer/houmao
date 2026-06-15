from __future__ import annotations

import pytest
from ag_ui.core import RunAgentInput

from houmao.ag_ui.prompt import AgUiPromptConversionError, convert_run_agent_input


def _run_input(**overrides: object) -> RunAgentInput:
    """Build one AG-UI run input for prompt conversion tests."""

    payload: dict[str, object] = {
        "threadId": "thread-1",
        "runId": "run-1",
        "state": {},
        "messages": [
            {
                "id": "message-1",
                "role": "user",
                "content": "hello",
            }
        ],
        "tools": [],
        "context": [],
        "forwardedProps": {},
    }
    payload.update(overrides)
    return RunAgentInput.model_validate(payload)


def test_prompt_conversion_uses_latest_user_message_and_structured_context() -> None:
    converted = convert_run_agent_input(
        _run_input(
            state={"ticket": "AGUI-2"},
            messages=[
                {"id": "system-1", "role": "system", "content": "system context"},
                {"id": "user-1", "role": "user", "content": "prior request"},
                {"id": "assistant-1", "role": "assistant", "content": "prior answer"},
                {
                    "id": "activity-1",
                    "role": "activity",
                    "activityType": "status",
                    "content": {"status": "busy"},
                },
                {"id": "user-2", "role": "user", "content": "current request"},
            ],
            context=[{"description": "workspace", "value": "/repo"}],
            forwardedProps={
                "authorization": "Bearer secret",
                "houmao": {
                    "chatSession": {"mode": "new"},
                    "execution": {"model": {"name": "gpt-5.4", "reasoning": {"level": 4}}},
                    "ignored": "secret value",
                },
            },
            resume=[{"interruptId": "interrupt-1", "status": "resolved", "payload": {"ok": True}}],
        )
    )

    assert converted.primary_message_id == "user-2"
    assert converted.primary_message_role == "user"
    assert converted.forwarded_props.chat_session == {"mode": "new"}
    assert converted.forwarded_props.execution == {
        "model": {"name": "gpt-5.4", "reasoning": {"level": 4}}
    }
    assert "Primary task:\ncurrent request" in converted.prompt
    assert "prior request" in converted.prompt
    assert "AG-UI state:" in converted.prompt
    assert "AG-UI context entries:" in converted.prompt
    assert "AG-UI resume data:" in converted.prompt
    assert "omittedForwardedPropKeys" in converted.prompt
    assert "authorization" in converted.prompt
    assert "Bearer secret" not in converted.prompt
    assert "secret value" not in converted.prompt
    assert "busy" not in converted.prompt


def test_prompt_conversion_uses_latest_tool_result_as_primary_body() -> None:
    converted = convert_run_agent_input(
        _run_input(
            messages=[
                {"id": "user-1", "role": "user", "content": "look up status"},
                {
                    "id": "tool-1",
                    "role": "tool",
                    "toolCallId": "tool-call-1",
                    "content": "tool result payload",
                },
            ]
        )
    )

    assert converted.primary_message_id == "tool-1"
    assert converted.primary_message_role == "tool"
    assert "Tool result for toolCallId `tool-call-1`:\ntool result payload" in converted.prompt
    assert "look up status" in converted.prompt


def test_prompt_conversion_rejects_unsupported_multimodal_input() -> None:
    run_input = _run_input(
        messages=[
            {
                "id": "user-1",
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "url", "value": "https://example.invalid/image.png"},
                    }
                ],
            }
        ]
    )

    with pytest.raises(AgUiPromptConversionError, match="multimodal"):
        convert_run_agent_input(run_input)


def test_prompt_conversion_accepts_text_content_parts() -> None:
    converted = convert_run_agent_input(
        _run_input(
            messages=[
                {
                    "id": "user-1",
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "line one"},
                        {"type": "text", "text": "line two"},
                    ],
                }
            ]
        )
    )

    assert "line one\nline two" in converted.prompt
