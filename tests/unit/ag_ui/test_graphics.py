from __future__ import annotations

import base64
import json

import pytest
from pydantic import ValidationError

from houmao.ag_ui.graphics import (
    HOUMAO_RENDER_GRAPHIC_TOOL_NAME,
    HoumaoGraphicArtifact,
    extract_graphic_artifact_from_headless_event,
    graphic_artifact_to_tool_events,
)
from houmao.ag_ui.mapper import AgUiEventMapper
from houmao.agents.realm_controller.backends.headless_output import CanonicalHeadlessEvent


def _event_types(events: list[object]) -> list[str]:
    """Return event type strings from Pydantic AG-UI events."""

    return [str(event.model_dump(mode="json", by_alias=True)["type"]) for event in events]  # type: ignore[attr-defined]


def test_graphics_accepts_supported_safe_formats() -> None:
    payloads = [
        {
            "title": "SVG",
            "format": "svg",
            "content": '<svg viewBox="0 0 1 1"><rect width="1" height="1" /></svg>',
        },
        {"title": "HTML", "format": "html_fragment", "content": "<div><strong>ok</strong></div>"},
        {"title": "Image URL", "format": "image_url", "contentUrl": "https://example.com/a.png"},
        {
            "title": "Image Data",
            "format": "image_data_uri",
            "content": "data:image/png;base64," + base64.b64encode(b"png-bytes").decode("ascii"),
        },
        {"title": "Chart", "format": "chart_json", "content": '{"type": "bar", "data": [1]}'},
    ]

    artifacts = [HoumaoGraphicArtifact.model_validate(payload) for payload in payloads]

    assert [artifact.format for artifact in artifacts] == [
        "svg",
        "html_fragment",
        "image_url",
        "image_data_uri",
        "chart_json",
    ]
    assert artifacts[-1].content == {"type": "bar", "data": [1]}


@pytest.mark.parametrize(
    "payload",
    [
        {"title": "Bad", "format": "pdf", "content": "x"},
        {"title": "Bad", "format": "svg", "content": "<svg><script>alert(1)</script></svg>"},
        {"title": "Bad", "format": "html_fragment", "content": '<button onclick="x()">x</button>'},
        {"title": "Bad", "format": "html_fragment", "content": '<a href="javascript:x()">x</a>'},
        {"title": "Bad", "format": "image_url", "contentUrl": "file:///tmp/a.png"},
        {
            "title": "Bad",
            "format": "image_data_uri",
            "content": "data:image/svg+xml;base64,"
            + base64.b64encode(b"<svg></svg>").decode("ascii"),
        },
        {"title": "Bad", "format": "chart_json", "content": "{not json"},
    ],
)
def test_graphics_rejects_unsupported_or_unsafe_payloads(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        HoumaoGraphicArtifact.model_validate(payload)


def test_graphics_extracts_explicit_artifact_without_markdown_scraping() -> None:
    artifact_payload = {
        "title": "Chart",
        "format": "chart_json",
        "content": {"type": "line", "data": [1, 2]},
    }
    event = CanonicalHeadlessEvent(
        kind="action_request",
        message="render chart",
        turn_index=1,
        provider="codex",
        provider_event_type="assistant.tool_call",
        data={"name": HOUMAO_RENDER_GRAPHIC_TOOL_NAME, "arguments": artifact_payload},
    )
    markdown_event = CanonicalHeadlessEvent(
        kind="assistant",
        message="![chart](chart.png)",
        turn_index=1,
        provider="codex",
        provider_event_type="assistant.text",
        data={"text": "![chart](chart.png)"},
    )

    extracted = extract_graphic_artifact_from_headless_event(event)

    assert extracted is not None
    assert extracted.title == "Chart"
    assert extract_graphic_artifact_from_headless_event(markdown_event) is None


def test_graphics_tool_call_sequence_and_optional_result() -> None:
    artifact = HoumaoGraphicArtifact(
        title="Chart",
        description="Tiny chart",
        format="chart_json",
        content={"type": "bar", "data": [1]},
        alt_text="Bar chart",
    )

    events = graphic_artifact_to_tool_events(
        artifact=artifact,
        parent_message_id="message-1",
        tool_call_id="tool-1",
        emit_result=True,
    )
    payloads = [event.model_dump(mode="json", by_alias=True) for event in events]

    assert _event_types(events) == [
        "TOOL_CALL_START",
        "TOOL_CALL_ARGS",
        "TOOL_CALL_END",
        "TOOL_CALL_RESULT",
    ]
    assert payloads[0]["toolCallName"] == HOUMAO_RENDER_GRAPHIC_TOOL_NAME
    assert payloads[0]["parentMessageId"] == "message-1"
    assert json.loads(payloads[1]["delta"])["title"] == "Chart"
    assert payloads[3]["toolCallId"] == "tool-1"
    assert json.loads(payloads[3]["content"])["altText"] == "Bar chart"


def test_mapper_attaches_graphics_tool_call_to_assistant_message() -> None:
    artifact = HoumaoGraphicArtifact(
        title="SVG",
        format="svg",
        content='<svg viewBox="0 0 1 1"></svg>',
    )
    mapper = AgUiEventMapper(thread_id="thread-1", run_id="run-1", emit_graphic_results=True)

    events = mapper.graphic_artifact_events(artifact=artifact, sequence_index=3)
    payloads = [event.model_dump(mode="json", by_alias=True) for event in events]

    assert _event_types(events) == [
        "TEXT_MESSAGE_START",
        "TOOL_CALL_START",
        "TOOL_CALL_ARGS",
        "TOOL_CALL_END",
        "TOOL_CALL_RESULT",
        "TEXT_MESSAGE_END",
    ]
    assert payloads[0]["messageId"] == payloads[1]["parentMessageId"]
    assert payloads[1]["toolCallName"] == HOUMAO_RENDER_GRAPHIC_TOOL_NAME
