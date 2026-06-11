from __future__ import annotations

import json

import pytest

from houmao.ag_ui.authoring import (
    HoumaoAgUiValidationError,
    component_schema_payload,
    list_component_summaries,
    render_component_events,
    render_events_as_jsonl,
    render_events_as_sse,
    validate_ag_ui_event_sequence,
    validate_component_payload,
)


def test_component_registry_exposes_initial_schemas_and_examples() -> None:
    summaries = list_component_summaries()
    names = {summary["name"] for summary in summaries}

    assert names == {
        "houmao.graphic.template",
        "houmao.chart.bar",
        "houmao.chart.line",
        "houmao.chart.pie",
        "houmao.table",
        "houmao.metric_grid",
        "houmao.dashboard",
    }

    schema = component_schema_payload("houmao.chart.bar")

    assert schema["name"] == "houmao.chart.bar"
    assert schema["schemaVersion"] == 1
    assert schema["protocol"] == "houmao.application.ag-ui"
    assert schema["example"]["schemaVersion"] == 1
    assert "schema" in schema

    template_schema = component_schema_payload("houmao.graphic.template")
    assert template_schema["name"] == "houmao.graphic.template"
    assert template_schema["example"]["chartType"] == "bar"
    assert template_schema["example"]["renderer"]["preferred"] == "vega-lite"


def test_valid_examples_validate_offline() -> None:
    for summary in list_component_summaries():
        schema = component_schema_payload(str(summary["name"]))

        validated = validate_component_payload(str(summary["name"]), schema["example"])

        assert validated["schemaVersion"] == 1


def test_template_graphic_payload_validates_with_safe_vega_lite_extra() -> None:
    payload = {
        "schemaVersion": 1,
        "chartType": "bar",
        "renderer": {"preferred": "vega-lite", "fallback": ["recharts"]},
        "title": "Build Results",
        "data": {
            "values": [
                {"status": "passed", "count": 42},
                {"status": "failed", "count": 2},
            ]
        },
        "encoding": {
            "x": {"field": "status", "type": "nominal", "title": "Status"},
            "y": {"field": "count", "type": "quantitative", "title": "Count"},
        },
        "extra": {
            "vega-lite": {
                "config": {"axis": {"labelFontSize": 12}},
                "mark": {"cornerRadiusTopLeft": 3},
            }
        },
    }

    validated = validate_component_payload("houmao.graphic.template", payload)

    assert validated["chartType"] == "bar"
    assert validated["renderer"]["preferred"] == "vega-lite"
    assert validated["extra"]["vega-lite"]["config"]["axis"]["labelFontSize"] == 12


def test_template_graphic_rejects_raw_vega_lite_spec_in_extra() -> None:
    payload = {
        "schemaVersion": 1,
        "chartType": "bar",
        "title": "Raw Spec Attempt",
        "data": {"values": [{"status": "passed", "count": 42}]},
        "encoding": {
            "x": {"field": "status", "type": "nominal"},
            "y": {"field": "count", "type": "quantitative"},
        },
        "extra": {
            "vega-lite": {
                "data": {"url": "https://example.invalid/data.json"},
                "mark": "bar",
            }
        },
    }

    with pytest.raises(HoumaoAgUiValidationError) as raised:
        validate_component_payload("houmao.graphic.template", payload)

    diagnostic = raised.value.to_payload()
    assert diagnostic["component"] == "houmao.graphic.template"
    assert "https://example.invalid" not in json.dumps(diagnostic)


def test_template_graphic_renders_to_standard_tool_call_events() -> None:
    payload = {
        "schemaVersion": 1,
        "chartType": "line",
        "renderer": {"preferred": "recharts", "fallback": ["vega-lite"]},
        "title": "Latency",
        "data": {
            "values": [
                {"time": "09:00", "p95": 120},
                {"time": "10:00", "p95": 98},
            ]
        },
        "encoding": {
            "x": {"field": "time", "type": "ordinal", "title": "Time"},
            "y": {"field": "p95", "type": "quantitative", "title": "ms"},
        },
    }

    events = render_component_events(
        component="houmao.graphic.template",
        payload=payload,
        message_id="message-1",
        tool_call_id="tool-1",
    )

    assert [event["type"] for event in events] == [
        "TOOL_CALL_START",
        "TOOL_CALL_ARGS",
        "TOOL_CALL_END",
    ]
    assert events[0]["toolCallName"] == "houmao.graphic.template"
    args = json.loads(str(events[1]["delta"]))
    assert args["schemaVersion"] == 1
    assert args["chartType"] == "line"
    assert validate_ag_ui_event_sequence(events) == events


def test_invalid_table_payload_reports_field_path_without_raw_values() -> None:
    payload = {
        "schemaVersion": 1,
        "title": "Bad Table",
        "columns": [{"key": "name", "label": "Name"}],
        "rows": [{"other": "private-value"}],
    }

    with pytest.raises(HoumaoAgUiValidationError) as raised:
        validate_component_payload("houmao.table", payload)

    diagnostic = raised.value.to_payload()
    assert diagnostic["component"] == "houmao.table"
    assert "private-value" not in json.dumps(diagnostic)
    assert diagnostic["fieldPaths"]


def test_unsafe_payload_is_rejected_before_event_rendering() -> None:
    payload = {
        "schemaVersion": 1,
        "title": "Unsafe",
        "data": [{"label": "<script>alert(1)</script>", "value": 1}],
    }

    with pytest.raises(HoumaoAgUiValidationError) as raised:
        render_component_events(component="houmao.chart.bar", payload=payload)

    assert "unsafe inline content" in str(raised.value)


def test_component_renders_to_standard_tool_call_events() -> None:
    payload = {
        "schemaVersion": 1,
        "title": "Quarterly Revenue",
        "data": [{"label": "Q1", "value": 120000}],
    }

    events = render_component_events(
        component="houmao.chart.bar",
        payload=payload,
        message_id="message-1",
        tool_call_id="tool-1",
    )

    assert [event["type"] for event in events] == [
        "TOOL_CALL_START",
        "TOOL_CALL_ARGS",
        "TOOL_CALL_END",
    ]
    assert events[0]["toolCallName"] == "houmao.chart.bar"
    assert events[0]["parentMessageId"] == "message-1"
    assert json.loads(str(events[1]["delta"]))["title"] == "Quarterly Revenue"
    assert validate_ag_ui_event_sequence(events) == events


def test_event_sequence_validation_rejects_args_before_start() -> None:
    events = [{"type": "TOOL_CALL_ARGS", "toolCallId": "tool-1", "delta": "{}"}]

    with pytest.raises(HoumaoAgUiValidationError) as raised:
        validate_ag_ui_event_sequence(events)

    assert raised.value.event_index == 0
    assert "unknown tool call" in str(raised.value)


def test_event_sequence_validation_rejects_oversized_batches() -> None:
    events = [{"type": "RAW"} for _ in range(101)]

    with pytest.raises(HoumaoAgUiValidationError) as raised:
        validate_ag_ui_event_sequence(events)

    assert "above the limit" in str(raised.value)


def test_event_render_formats_jsonl_and_sse() -> None:
    payload = {
        "schemaVersion": 1,
        "title": "Build Health",
        "metrics": [{"label": "Pass rate", "value": "98%"}],
    }
    events = render_component_events(component="houmao.metric_grid", payload=payload)

    jsonl = render_events_as_jsonl(events)
    sse = render_events_as_sse(events)

    assert len(jsonl.strip().splitlines()) == 3
    assert sse.count("data: ") == 3
    assert "TOOL_CALL_START" in sse
