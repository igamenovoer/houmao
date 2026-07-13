from __future__ import annotations

import json

import pytest

from houmao.agents.realm_controller.backends.headless_output import (
    canonical_headless_events_from_provider_output,
    render_canonical_headless_events,
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


def test_codex_canonical_parser_normalizes_collaboration_lifecycle() -> None:
    stdout_text = "\n".join(
        [
            '{"type":"thread.started","thread_id":"thread-parent"}',
            (
                '{"type":"item.started","item":{"id":"collab-1",'
                '"type":"collab_tool_call","tool":"spawn_agent",'
                '"sender_thread_id":"thread-parent","receiver_thread_ids":[],'
                '"prompt":"draft a plan","agents_states":{},"status":"in_progress"}}'
            ),
            (
                '{"type":"item.updated","item":{"id":"collab-1",'
                '"type":"collab_tool_call","tool":"spawn_agent",'
                '"sender_thread_id":"thread-parent",'
                '"receiver_thread_ids":["thread-child"],"prompt":"draft a plan",'
                '"agents_states":{"thread-child":{"status":"running","message":null}},'
                '"status":"in_progress"}}'
            ),
            (
                '{"type":"item.completed","item":{"id":"collab-1",'
                '"type":"collab_tool_call","tool":"spawn_agent",'
                '"sender_thread_id":"thread-parent",'
                '"receiver_thread_ids":["thread-child"],"prompt":"draft a plan",'
                '"agents_states":{"thread-child":{"status":"completed",'
                '"message":"plan ready"}},"status":"completed"}}'
            ),
            (
                '{"type":"item.completed","item":{"id":"collab-2",'
                '"type":"collab_tool_call","tool":"wait",'
                '"sender_thread_id":"thread-parent","receiver_thread_ids":[],'
                '"agents_states":{},"status":"failed"}}'
            ),
        ]
    )

    events = canonical_headless_events_from_provider_output(
        provider="codex",
        output_format="stream-json",
        stdout_text=stdout_text,
        turn_index=4,
    )

    assert [event.kind for event in events] == [
        "session",
        "action_request",
        "progress",
        "action_result",
        "action_result",
    ]
    request_data = events[1].data or {}
    assert request_data["tool"] == "spawn_agent"
    assert request_data["sender_thread_id"] == "thread-parent"
    assert request_data["prompt"] == "draft a plan"
    assert (events[2].data or {})["receiver_thread_ids"] == ["thread-child"]
    assert (events[3].data or {})["agents_states"]["thread-child"]["status"] == "completed"
    assert "thread-child=completed" in events[3].message
    assert (events[4].data or {})["status"] == "failed"


def test_codex_canonical_parser_handles_partial_collaboration_payload() -> None:
    events = canonical_headless_events_from_provider_output(
        provider="codex",
        output_format="stream-json",
        stdout_text=(
            '{"type":"item.completed","item":{"id":"collab-partial",'
            '"type":"collab_tool_call","status":"failed"}}'
        ),
        turn_index=2,
    )

    assert len(events) == 1
    assert events[0].kind == "action_result"
    assert (events[0].data or {})["name"] == "collab_tool"
    assert (events[0].data or {})["receiver_thread_ids"] == []
    assert (events[0].data or {})["status"] == "failed"


def test_codex_collaboration_renders_consistently_across_styles() -> None:
    events = canonical_headless_events_from_provider_output(
        provider="codex",
        output_format="stream-json",
        stdout_text="\n".join(
            [
                (
                    '{"type":"item.started","item":{"id":"collab-1",'
                    '"type":"collab_tool_call","tool":"spawn_agent",'
                    '"sender_thread_id":"parent","receiver_thread_ids":[],'
                    '"prompt":"draft a plan","agents_states":{},"status":"in_progress"}}'
                ),
                (
                    '{"type":"item.completed","item":{"id":"collab-1",'
                    '"type":"collab_tool_call","tool":"spawn_agent",'
                    '"sender_thread_id":"parent","receiver_thread_ids":["child"],'
                    '"prompt":"draft a plan","agents_states":{"child":'
                    '{"status":"running","message":null}},"status":"completed"}}'
                ),
            ]
        ),
        turn_index=1,
    )

    rendered: dict[str, str] = {}
    for style in ("plain", "fancy", "json"):
        chunks: list[str] = []
        render_canonical_headless_events(
            events=events,
            style=style,  # type: ignore[arg-type]
            detail="detail",
            sink=chunks.append,
        )
        rendered[style] = "".join(chunks)

    assert "[action] spawn_agent draft a plan" in rendered["plain"]
    assert "[result] spawn_agent completed" in rendered["plain"]
    assert "Action: spawn_agent draft a plan" in rendered["fancy"]
    assert "Result: spawn_agent completed" in rendered["fancy"]
    json_records = [json.loads(line) for line in rendered["json"].splitlines()]
    assert [record["kind"] for record in json_records] == ["action_request", "action_result"]


def test_kimi_retry_meta_becomes_canonical_progress() -> None:
    raw_line = (
        '{"role":"meta","type":"turn.step.retrying","failed_attempt":1,'
        '"next_attempt":2,"max_attempts":4,"delay_ms":1500,'
        '"error_name":"RateLimitError","error_message":"slow down","status_code":429}'
    )
    events = canonical_headless_events_from_provider_output(
        provider="kimi",
        output_format="stream-json",
        stdout_text=raw_line,
        turn_index=8,
    )

    assert len(events) == 1
    event = events[0]
    assert event.kind == "progress"
    assert event.provider_event_type == "turn.step.retrying"
    assert event.message == "attempt 2/4 after 1500ms: slow down"
    assert event.data == {
        "summary": "attempt 2/4 after 1500ms: slow down",
        "status": "retrying",
        "failed_attempt": 1,
        "next_attempt": 2,
        "max_attempts": 4,
        "delay_ms": 1500,
        "error_name": "RateLimitError",
        "error_message": "slow down",
        "status_code": 429,
    }
    assert event.raw_payload == json.loads(raw_line)
