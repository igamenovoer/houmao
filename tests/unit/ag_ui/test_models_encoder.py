from __future__ import annotations

import json

from ag_ui.core import BaseEvent

from houmao.ag_ui.encoder import SSE_CONTENT_TYPE, AgUiSseEncoder, encode_sse_event
from houmao.ag_ui.models import AgUiConnectInput, AgUiEventType, AgUiStateSnapshotEvent


def _connect_payload() -> dict[str, object]:
    """Return one valid AG-UI connect payload with camelCase fields."""

    return {
        "threadId": "thread-1",
        "runId": "run-1",
        "parentRunId": "run-parent",
        "state": {"existing": "state"},
        "messages": [
            {
                "id": "message-1",
                "role": "user",
                "content": "hello",
            }
        ],
        "tools": [],
        "context": [],
        "forwardedProps": {
            "authorization": "Bearer secret",
            "safeClientName": "test-client",
        },
        "lastSeenEventId": "event-12",
    }


def test_connect_input_accepts_ag_ui_camel_case_fields() -> None:
    connect_input = AgUiConnectInput.model_validate(_connect_payload())

    assert connect_input.thread_id == "thread-1"
    assert connect_input.run_id == "run-1"
    assert connect_input.parent_run_id == "run-parent"
    assert connect_input.forwarded_props == {
        "authorization": "Bearer secret",
        "safeClientName": "test-client",
    }
    assert connect_input.last_seen_event_id == "event-12"

    dumped = connect_input.model_dump(mode="json", by_alias=True)
    assert dumped["threadId"] == "thread-1"
    assert dumped["runId"] == "run-1"
    assert dumped["parentRunId"] == "run-parent"
    assert dumped["forwardedProps"] == {
        "authorization": "Bearer secret",
        "safeClientName": "test-client",
    }
    assert dumped["lastSeenEventId"] == "event-12"
    assert "thread_id" not in dumped
    assert "last_seen_event_id" not in dumped


def test_sse_encoder_uses_text_event_stream_frames_and_omits_null_fields() -> None:
    event = BaseEvent(
        type=AgUiEventType.RAW,
        timestamp=1648214400000,
        raw_event=None,
    )

    encoder = AgUiSseEncoder()
    encoded = encoder.encode(event)

    assert encoder.content_type() == SSE_CONTENT_TYPE
    assert encoded == encode_sse_event(event)
    assert encoded.startswith("data: ")
    assert encoded.endswith("\n\n")

    payload = json.loads(encoded.removeprefix("data: ").removesuffix("\n\n"))
    assert payload == {
        "type": "RAW",
        "timestamp": 1648214400000,
    }
    assert "rawEvent" not in payload
    assert "raw_event" not in payload


def test_sse_encoder_can_include_event_id() -> None:
    event = BaseEvent(type=AgUiEventType.RAW, raw_event={"ok": True})

    encoded = encode_sse_event(event, event_id="event-1")

    lines = encoded.splitlines()
    assert lines[0] == "id: event-1"
    assert lines[1].startswith("data: ")
    assert json.loads(lines[1].removeprefix("data: ")) == {
        "type": "RAW",
        "rawEvent": {"ok": True},
    }


def test_state_snapshot_sse_frame_contains_camel_case_nested_houmao_state() -> None:
    event = AgUiStateSnapshotEvent(
        snapshot={
            "houmao": {
                "connection": {
                    "connectionId": "agui-1",
                    "threadId": "thread-1",
                    "runId": "run-1",
                }
            }
        }
    )

    encoded = encode_sse_event(event)
    payload = json.loads(encoded.removeprefix("data: ").removesuffix("\n\n"))

    assert payload["type"] == "STATE_SNAPSHOT"
    assert payload["snapshot"]["houmao"]["connection"]["connectionId"] == "agui-1"
    assert "rawEvent" not in payload
