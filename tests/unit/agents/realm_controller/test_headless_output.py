from __future__ import annotations

import pytest

from houmao.agents.realm_controller.backends.headless_output import (
    canonical_headless_events_from_provider_output,
)


@pytest.mark.parametrize(
    ("provider", "stdout_text", "expected_kinds", "expected_session_id"),
    [
        (
            "claude",
            "\n".join(
                [
                    (
                        '{"type":"assistant","session_id":"claude-session","message":'
                        '{"model":"claude","content":[{"type":"text","text":"hello from claude"}]}}'
                    ),
                    (
                        '{"type":"result","session_id":"claude-session","subtype":"success",'
                        '"usage":{"input_tokens":1,"output_tokens":2,"total_tokens":3}}'
                    ),
                ]
            ),
            ["assistant", "completion"],
            "claude-session",
        ),
        (
            "codex",
            "\n".join(
                [
                    '{"type":"thread.started","thread_id":"thread-123"}',
                    (
                        '{"type":"item.started","item":{"id":"cmd-1","type":"command_execution",'
                        '"command":"ls -la"}}'
                    ),
                    (
                        '{"type":"item.completed","item":{"id":"cmd-1","type":"command_execution",'
                        '"command":"ls -la","status":"completed","aggregated_output":"done"}}'
                    ),
                    (
                        '{"type":"item.completed","item":{"id":"msg-1","type":"agent_message",'
                        '"text":"hello from codex"}}'
                    ),
                    (
                        '{"type":"turn.completed","usage":{"input_tokens":3,"output_tokens":5,'
                        '"total_tokens":8}}'
                    ),
                ]
            ),
            ["session", "action_request", "action_result", "assistant", "completion"],
            "thread-123",
        ),
        (
            "kimi",
            "\n".join(
                [
                    '{"role":"assistant","content":"hello from kimi"}',
                    (
                        '{"role":"assistant","tool_calls":[{"type":"function","id":"tool-1",'
                        '"function":{"name":"Bash","arguments":"{\\"command\\":\\"pwd\\"}"}}]}'
                    ),
                    '{"role":"tool","tool_call_id":"tool-1","content":"/tmp/project"}',
                    (
                        '{"role":"meta","type":"session.resume_hint",'
                        '"session_id":"kimi-session","command":"kimi -r kimi-session"}'
                    ),
                ]
            ),
            ["assistant", "action_request", "action_result", "session"],
            "kimi-session",
        ),
    ],
)
def test_canonical_headless_events_from_provider_output_normalizes_supported_streams(
    provider: str,
    stdout_text: str,
    expected_kinds: list[str],
    expected_session_id: str,
) -> None:
    events = canonical_headless_events_from_provider_output(
        provider=provider,  # type: ignore[arg-type]
        output_format="stream-json",
        stdout_text=stdout_text,
        turn_index=3,
    )

    assert [event.kind for event in events] == expected_kinds
    assert {event.turn_index for event in events} == {3}
    assert events[-1].session_id == expected_session_id


def test_kimi_canonical_parser_preserves_unknowns_and_parses_tool_arguments() -> None:
    events = canonical_headless_events_from_provider_output(
        provider="kimi",
        output_format="stream-json",
        stdout_text="\n".join(
            [
                (
                    '{"role":"assistant","tool_calls":[{"type":"function","id":"tool-1",'
                    '"function":{"name":"Edit","arguments":"{\\"file\\":\\"a.py\\"}"}}]}'
                ),
                '{"role":"tool","tool_call_id":"tool-1","content":"ok"}',
                '{"role":"meta","type":"session.resume_hint","session_id":"session-kimi-1"}',
                '{"type":"provider.note","message":"kept"}',
                '{"type":"error","message":"provider warning"}',
            ]
        ),
        turn_index=7,
    )

    assert [event.kind for event in events] == [
        "action_request",
        "action_result",
        "session",
        "passthrough",
        "diagnostic",
    ]
    assert events[0].data["name"] == "Edit"
    assert events[0].data["arguments"] == {"file": "a.py"}
    assert events[1].data["result_text"] == "ok"
    assert events[2].session_id == "session-kimi-1"
    assert events[3].provider_event_type == "provider.note"
    assert events[4].data["severity"] == "error"
