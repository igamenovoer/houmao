from __future__ import annotations

import json

from houmao.server.models import HoumaoHeadlessTurnEvent, HoumaoHeadlessTurnEventsResponse
from houmao.srv_ctrl.commands.agents.turn import _render_turn_events_response


def _sample_response() -> HoumaoHeadlessTurnEventsResponse:
    return HoumaoHeadlessTurnEventsResponse(
        tracked_agent_id="tracked-1",
        turn_id="turn-0001",
        entries=[
            HoumaoHeadlessTurnEvent(
                kind="assistant",
                message="hello from replay",
                turn_index=1,
                timestamp_utc="2026-03-20T09:01:00+00:00",
                payload={
                    "provider": "claude",
                    "session_id": "sess-1",
                    "provider_event_type": "assistant.text",
                    "data": {"text": "hello from replay"},
                    "raw": {"type": "assistant", "text": "hello from replay"},
                },
            ),
            HoumaoHeadlessTurnEvent(
                kind="action_request",
                message="command ls -la",
                turn_index=1,
                timestamp_utc="2026-03-20T09:01:01+00:00",
                payload={
                    "provider": "codex",
                    "session_id": "sess-1",
                    "provider_event_type": "item.started.command_execution",
                    "data": {
                        "action_id": "cmd-1",
                        "name": "command",
                        "arguments_summary": "ls -la",
                    },
                    "raw": {"type": "item.started"},
                },
            ),
            HoumaoHeadlessTurnEvent(
                kind="action_result",
                message="command completed: listed files",
                turn_index=1,
                timestamp_utc="2026-03-20T09:01:02+00:00",
                payload={
                    "provider": "codex",
                    "session_id": "sess-1",
                    "provider_event_type": "item.completed.command_execution",
                    "data": {
                        "action_id": "cmd-1",
                        "status": "completed",
                        "result_summary": "listed files",
                    },
                    "raw": {"type": "item.completed"},
                },
            ),
            HoumaoHeadlessTurnEvent(
                kind="completion",
                message="success",
                turn_index=1,
                timestamp_utc="2026-03-20T09:01:03+00:00",
                payload={
                    "provider": "claude",
                    "session_id": "sess-1",
                    "provider_event_type": "result",
                    "data": {
                        "status": "success",
                        "usage": {"input_tokens": 3, "output_tokens": 5, "total_tokens": 8},
                    },
                    "raw": {"type": "result"},
                },
            ),
        ],
    )


def test_render_turn_events_response_plain_concise_uses_canonical_renderer(capsys) -> None:
    _render_turn_events_response(
        response=_sample_response(),
        style="plain",
        detail="concise",
    )

    output = capsys.readouterr().out
    assert "hello from replay" in output
    assert "[action] command ls -la" in output
    assert "[result] command completed: listed files" in output
    assert "[complete] success | input_tokens=3, output_tokens=5, total_tokens=8" in output
    assert "provider_event_type" not in output
    assert '"type": "assistant"' not in output


def test_render_turn_events_response_json_concise_omits_detail_only_fields(capsys) -> None:
    _render_turn_events_response(
        response=_sample_response(),
        style="json",
        detail="concise",
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["tracked_agent_id"] == "tracked-1"
    assert payload["entries"][0]["payload"]["provider"] == "claude"
    assert "provider_event_type" not in payload["entries"][0]["payload"]
    assert "raw" not in payload["entries"][0]["payload"]


def test_render_turn_events_response_json_detail_includes_structured_provenance(capsys) -> None:
    _render_turn_events_response(
        response=_sample_response(),
        style="json",
        detail="detail",
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["entries"][0]["payload"]["provider_event_type"] == "assistant.text"
    assert payload["entries"][0]["payload"]["raw"] == {
        "text": "hello from replay",
        "type": "assistant",
    }
