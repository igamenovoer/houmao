from __future__ import annotations

import json

import pytest

from houmao.ag_ui.authoring import (
    HOUMAO_VEGALITE_GRAPHIC_MAX_BYTES,
    HoumaoAgUiValidationError,
    component_schema_payload,
    list_component_summaries,
    render_component_events,
    render_events_as_jsonl,
    render_events_as_sse,
    validate_ag_ui_event_sequence,
    validate_component_payload,
)
from houmao.ag_ui.plotly_trace_catalog import PLOTLY_2D_TRACE_CATALOG, PLOTLY_2D_TRACE_TYPES


def _template_payload(trace_type: str = "bar") -> dict[str, object]:
    """Return one valid schema version 3 template graphic payload."""

    example = PLOTLY_2D_TRACE_CATALOG[trace_type]["example"]
    trace: dict[str, object] = {"type": trace_type, "name": f"{trace_type} example"}
    trace.update(example)
    return {
        "schemaVersion": 3,
        "figureType": "plotly2d",
        "title": f"{trace_type.title()} Example",
        "renderer": {"preferred": "plotly"},
        "traces": [trace],
        "layout": {
            "xaxis": {"title": "X"},
            "yaxis": {"title": "Y"},
            "hovermode": "x unified",
        },
        "config": {"responsive": True, "displayModeBar": "hover"},
    }


def _vegalite_payload() -> dict[str, object]:
    """Return one valid Layer 2 Vega-Lite component payload."""

    return {
        "schemaVersion": 1,
        "library": "vega-lite",
        "specVersion": "6",
        "title": "Queue Status",
        "description": "Inline Vega-Lite data.",
        "spec": {
            "$schema": "https://vega.github.io/schema/vega-lite/v6.4.1.json",
            "data": {
                "values": [
                    {"status": "ready", "count": 58},
                    {"status": "queued", "count": 23},
                ]
            },
            "mark": "bar",
            "encoding": {
                "x": {"field": "status", "type": "nominal"},
                "y": {"field": "count", "type": "quantitative"},
            },
        },
        "display": {"height": 360, "caption": "Current queue status."},
    }


def test_component_registry_exposes_current_schemas_and_examples() -> None:
    summaries = list_component_summaries()
    names = {summary["name"] for summary in summaries}

    assert names == {
        "houmao.graphic.template",
        "houmao.graphic.vegalite",
        "houmao.table",
        "houmao.metric_grid",
        "houmao.dashboard",
    }

    template_schema = component_schema_payload("houmao.graphic.template")
    assert template_schema["name"] == "houmao.graphic.template"
    assert template_schema["schemaVersion"] == 3
    assert template_schema["protocol"] == "houmao.application.ag-ui"
    assert template_schema["example"]["schemaVersion"] == 3
    assert template_schema["example"]["figureType"] == "plotly2d"
    assert template_schema["example"]["renderer"]["preferred"] == "plotly"
    assert "heatmap" in template_schema["traceCatalog"]["supportedTraceTypes"]
    assert template_schema["traceCatalog"]["excludedTraceTypes"]["scatter3d"] == (
        "true_3d_scene_trace"
    )
    assert "schema" in template_schema

    vegalite_schema = component_schema_payload("houmao.graphic.vegalite")
    assert vegalite_schema["name"] == "houmao.graphic.vegalite"
    assert vegalite_schema["schemaVersion"] == 1
    assert vegalite_schema["example"]["library"] == "vega-lite"
    assert vegalite_schema["example"]["specVersion"] == "6"
    assert vegalite_schema["example"]["spec"]["data"]["values"][0]["status"] == "ready"
    assert "schema" in vegalite_schema


def test_valid_examples_validate_offline() -> None:
    for summary in list_component_summaries():
        schema = component_schema_payload(str(summary["name"]))

        validated = validate_component_payload(str(summary["name"]), schema["example"])

        assert validated["schemaVersion"] == schema["schemaVersion"]


@pytest.mark.parametrize(
    "trace_type",
    PLOTLY_2D_TRACE_TYPES,
)
def test_template_graphic_validates_inline_plotly_payloads(trace_type: str) -> None:
    validated = validate_component_payload(
        "houmao.graphic.template",
        _template_payload(trace_type),
    )

    assert validated["schemaVersion"] == 3
    assert validated["figureType"] == "plotly2d"
    assert validated["renderer"]["preferred"] == "plotly"
    assert validated["traces"][0]["type"] == trace_type
    assert "traces" in validated
    assert "chartType" not in validated
    assert "encoding" not in validated


def test_template_graphic_defaults_missing_renderer_to_plotly() -> None:
    payload = _template_payload("bar")
    payload.pop("renderer")

    validated = validate_component_payload("houmao.graphic.template", payload)

    assert validated["renderer"]["preferred"] == "plotly"


def test_template_graphic_accepts_datasource_binding_vocabulary() -> None:
    payload = {
        "schemaVersion": 3,
        "figureType": "plotly2d",
        "title": "Datasource Contract",
        "dataRefs": [
            {
                "id": "builds",
                "label": "Build rows",
                "columns": [
                    {"name": "status", "type": "string"},
                    {"name": "count", "type": "number"},
                ],
            }
        ],
        "traces": [
                {
                    "type": "bar",
                    "name": "Builds",
                    "source": {
                        "dataRef": "builds",
                        "bindings": {
                            "data.x": {"column": "status"},
                            "data.y": {"column": "count"},
                        },
                    },
                }
            ],
    }

    validated = validate_component_payload("houmao.graphic.template", payload)

    assert validated["dataRefs"][0]["id"] == "builds"
    assert validated["traces"][0]["source"]["dataRef"] == "builds"
    assert validated["traces"][0]["source"]["bindings"]["data.x"]["column"] == "status"


def test_template_graphic_rejects_invalid_datasource_binding_path() -> None:
    payload = {
        "schemaVersion": 3,
        "figureType": "plotly2d",
        "title": "Datasource Contract",
        "dataRefs": [
            {
                "id": "builds",
                "columns": [{"name": "status", "type": "string"}],
            }
        ],
        "traces": [
            {
                "type": "bar",
                "source": {
                    "dataRef": "builds",
                    "bindings": {
                        "data.notAPlotlyField": {"column": "status"},
                    },
                },
            }
        ],
    }

    with pytest.raises(HoumaoAgUiValidationError) as raised:
        validate_component_payload("houmao.graphic.template", payload)

    diagnostic = raised.value.to_payload()
    assert diagnostic["fieldPaths"] == ["traces.0.source.bindings.data.notAPlotlyField"]


def test_template_graphic_validates_safe_plotly_extra() -> None:
    payload = _template_payload("bar")
    payload["extra"] = {
            "plotly": {
                "layout": {"bargap": 0.24, "margin": {"l": 48, "r": 12, "t": 36, "b": 44}},
                "config": {"responsive": True},
                "style": {"line": {"shape": "spline"}},
            }
        }

    validated = validate_component_payload("houmao.graphic.template", payload)

    assert validated["extra"]["plotly"]["layout"]["bargap"] == 0.24
    assert validated["extra"]["plotly"]["style"]["line"]["shape"] == "spline"


def test_template_graphic_rejects_raw_plotly_replacement_in_extra() -> None:
    payload = _template_payload("bar")
    payload["extra"] = {
        "plotly": {
            "data": [{"x": ["secret"], "y": [1]}],
            "layout": {"bargap": 0.2},
        }
    }

    with pytest.raises(HoumaoAgUiValidationError) as raised:
        validate_component_payload("houmao.graphic.template", payload)

    diagnostic = raised.value.to_payload()
    assert diagnostic["component"] == "houmao.graphic.template"
    assert "extra.plotly.data" in diagnostic["message"]
    assert "secret" not in json.dumps(diagnostic)


def test_template_graphic_rejects_vega_lite_extra() -> None:
    payload = _template_payload("bar")
    payload["extra"] = {"vega-lite": {"mark": "bar"}}

    with pytest.raises(HoumaoAgUiValidationError) as raised:
        validate_component_payload("houmao.graphic.template", payload)

    diagnostic = raised.value.to_payload()
    assert diagnostic["fieldPaths"] == ["extra.vega-lite"]
    assert "Only `extra.plotly`" in diagnostic["repairHint"]


def test_template_graphic_rejects_non_plotly_renderer_and_fallback() -> None:
    payload = _template_payload("bar")
    payload["renderer"] = {"preferred": "vega-lite"}

    with pytest.raises(HoumaoAgUiValidationError) as raised:
        validate_component_payload("houmao.graphic.template", payload)

    assert raised.value.to_payload()["fieldPaths"] == ["renderer.preferred"]

    payload["renderer"] = {"preferred": "plotly", "fallback": ["recharts"]}
    with pytest.raises(HoumaoAgUiValidationError) as fallback_raised:
        validate_component_payload("houmao.graphic.template", payload)

    assert fallback_raised.value.to_payload()["fieldPaths"] == ["renderer.fallback"]


def test_template_graphic_rejects_schema_version_2_chart_type_payload() -> None:
    payload = {
        "schemaVersion": 2,
        "chartType": "bar",
        "title": "Old",
        "traces": [{"type": "bar", "x": ["passed"], "y": [42]}],
    }

    with pytest.raises(HoumaoAgUiValidationError) as raised:
        validate_component_payload("houmao.graphic.template", payload)

    diagnostic = raised.value.to_payload()
    assert diagnostic["fieldPaths"] == ["schemaVersion"]
    assert "schemaVersion 3" in diagnostic["message"]
    assert "traces[].type" in diagnostic["repairHint"]


def test_template_graphic_rejects_true_3d_trace_type() -> None:
    payload = _template_payload("bar")
    payload["traces"] = [{"type": "scatter3d", "data": {"x": [1], "y": [2]}}]

    with pytest.raises(HoumaoAgUiValidationError) as raised:
        validate_component_payload("houmao.graphic.template", payload)

    diagnostic = raised.value.to_payload()
    assert diagnostic["fieldPaths"] == ["traces.0.type"]
    assert "true_3d_scene_trace" in diagnostic["message"]


def test_template_graphic_rejects_legacy_row_encoding_payload() -> None:
    payload = {
        "schemaVersion": 1,
        "chartType": "bar",
        "title": "Legacy",
        "data": {"values": [{"status": "passed", "count": 42}]},
        "encoding": {
            "x": {"field": "status", "type": "nominal"},
            "y": {"field": "count", "type": "quantitative"},
        },
    }

    with pytest.raises(HoumaoAgUiValidationError) as raised:
        validate_component_payload("houmao.graphic.template", payload)

    diagnostic = raised.value.to_payload()
    assert diagnostic["fieldPaths"] == ["schemaVersion"]
    assert "schema version 3" in diagnostic["repairHint"]
    assert "passed" not in json.dumps(diagnostic)


def test_template_graphic_rejects_remote_urls_and_unsafe_text() -> None:
    remote_payload = _template_payload("bar")
    remote_payload["subtitle"] = "https://example.invalid/data.json"

    with pytest.raises(HoumaoAgUiValidationError) as remote_raised:
        validate_component_payload("houmao.graphic.template", remote_payload)

    assert "remote URL" in str(remote_raised.value)
    assert "example.invalid" not in json.dumps(remote_raised.value.to_payload())

    unsafe_payload = _template_payload("bar")
    unsafe_payload["title"] = "<script>alert(1)</script>"
    with pytest.raises(HoumaoAgUiValidationError) as unsafe_raised:
        render_component_events(component="houmao.graphic.template", payload=unsafe_payload)

    assert "unsafe inline content" in str(unsafe_raised.value)


def test_template_graphic_rejects_invalid_trace_shape() -> None:
    payload = _template_payload("bar")
    payload["traces"] = [{"type": "bar", "data": {"notAPlotlyField": [1]}}]

    with pytest.raises(HoumaoAgUiValidationError) as raised:
        validate_component_payload("houmao.graphic.template", payload)

    assert raised.value.to_payload()["fieldPaths"] == ["traces.0.data.notAPlotlyField"]


def test_template_graphic_rejects_plotly_remote_source_fields() -> None:
    payload = _template_payload("scatter")
    payload["traces"] = [
        {
            "type": "scatter",
            "data": {"x": [1], "y": [2]},
            "style": {"textsrc": "column:secret"},
        }
    ]

    with pytest.raises(HoumaoAgUiValidationError) as raised:
        validate_component_payload("houmao.graphic.template", payload)

    diagnostic = raised.value.to_payload()
    assert diagnostic["fieldPaths"] == ["traces.0.style.textsrc"]


def test_retired_fixed_chart_components_are_unsupported() -> None:
    for component in ("houmao.chart.bar", "houmao.chart.line", "houmao.chart.pie"):
        with pytest.raises(HoumaoAgUiValidationError) as schema_raised:
            component_schema_payload(component)
        assert "Retired Houmao AG-UI component" in str(schema_raised.value)

        with pytest.raises(HoumaoAgUiValidationError) as validate_raised:
            validate_component_payload(component, {"schemaVersion": 1})
        assert validate_raised.value.to_payload()["component"] == component


def test_template_graphic_renders_to_standard_tool_call_events() -> None:
    events = render_component_events(
        component="houmao.graphic.template",
        payload=_template_payload("scatter"),
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
    assert args["schemaVersion"] == 3
    assert args["figureType"] == "plotly2d"
    assert args["traces"][0]["type"] == "scatter"
    assert args["renderer"]["preferred"] == "plotly"
    assert "dataRefs" not in args
    assert validate_ag_ui_event_sequence(events) == events


def test_vegalite_graphic_validates_and_renders_to_standard_tool_call_events() -> None:
    events = render_component_events(
        component="houmao.graphic.vegalite",
        payload=_vegalite_payload(),
        message_id="message-vega",
        tool_call_id="tool-vega",
    )

    assert [event["type"] for event in events] == [
        "TOOL_CALL_START",
        "TOOL_CALL_ARGS",
        "TOOL_CALL_END",
    ]
    assert events[0]["toolCallName"] == "houmao.graphic.vegalite"
    args = json.loads(str(events[1]["delta"]))
    assert args["schemaVersion"] == 1
    assert args["library"] == "vega-lite"
    assert args["specVersion"] == "6"
    assert args["spec"]["$schema"] == "https://vega.github.io/schema/vega-lite/v6.4.1.json"
    assert validate_ag_ui_event_sequence(events) == events


def test_vegalite_graphic_accepts_altair_to_dict_output_without_runtime_execution() -> None:
    import altair as alt

    chart = (
        alt.Chart(
            alt.Data(
                values=[
                    {"status": "ready", "count": 58},
                    {"status": "queued", "count": 23},
                ]
            )
        )
        .mark_bar()
        .encode(x="status:N", y="count:Q")
    )
    payload = _vegalite_payload()
    payload["spec"] = chart.to_dict()

    validated = validate_component_payload("houmao.graphic.vegalite", payload)

    assert validated["spec"]["$schema"].startswith("https://vega.github.io/schema/vega-lite/v6")
    assert validated["spec"]["data"]["values"][0]["status"] == "ready"


def test_vegalite_graphic_rejects_remote_data_url_with_safe_diagnostic() -> None:
    payload = _vegalite_payload()
    payload["spec"] = {
        "$schema": "https://vega.github.io/schema/vega-lite/v6.4.1.json",
        "data": {"url": "https://example.invalid/data.json"},
        "mark": "bar",
        "encoding": {
            "x": {"field": "status", "type": "nominal"},
            "y": {"field": "count", "type": "quantitative"},
        },
    }

    with pytest.raises(HoumaoAgUiValidationError) as raised:
        validate_component_payload("houmao.graphic.vegalite", payload)

    diagnostic = raised.value.to_payload()
    assert diagnostic["component"] == "houmao.graphic.vegalite"
    assert diagnostic["fieldPaths"] == ["spec.data.url"]
    assert "example.invalid" not in json.dumps(diagnostic)


def test_vegalite_graphic_rejects_unsafe_inline_content() -> None:
    payload = _vegalite_payload()
    spec = payload["spec"]
    assert isinstance(spec, dict)
    spec["description"] = "<script>alert(1)</script>"

    with pytest.raises(HoumaoAgUiValidationError) as raised:
        render_component_events(component="houmao.graphic.vegalite", payload=payload)

    assert "unsafe inline content" in str(raised.value)


def test_vegalite_graphic_rejects_python_source_as_spec() -> None:
    payload = _vegalite_payload()
    payload["spec"] = "import altair as alt\nchart = alt.Chart(data)"

    with pytest.raises(HoumaoAgUiValidationError) as raised:
        validate_component_payload("houmao.graphic.vegalite", payload)

    diagnostic = raised.value.to_payload()
    assert diagnostic["fieldPaths"] == ["spec"]
    assert "chart.to_dict()" in str(diagnostic["repairHint"])
    assert "alt.Chart" not in json.dumps(diagnostic)


def test_vegalite_graphic_rejects_unsupported_version() -> None:
    payload = _vegalite_payload()
    payload["specVersion"] = "5"

    with pytest.raises(HoumaoAgUiValidationError) as raised:
        validate_component_payload("houmao.graphic.vegalite", payload)

    diagnostic = raised.value.to_payload()
    assert diagnostic["fieldPaths"] == ["specVersion"]
    assert "6" in diagnostic["repairHint"]


def test_vegalite_graphic_rejects_oversized_payloads() -> None:
    payload = _vegalite_payload()
    payload["title"] = "x" * HOUMAO_VEGALITE_GRAPHIC_MAX_BYTES

    with pytest.raises(HoumaoAgUiValidationError) as raised:
        validate_component_payload("houmao.graphic.vegalite", payload)

    diagnostic = raised.value.to_payload()
    assert diagnostic["fieldPaths"] == ["$"]
    assert "above the limit" in diagnostic["message"]


def test_dashboard_payload_accepts_valid_vegalite_child() -> None:
    payload = {
        "schemaVersion": 1,
        "title": "Release Dashboard",
        "children": [
            {
                "component": "houmao.graphic.vegalite",
                "width": "full",
                "props": _vegalite_payload(),
            }
        ],
    }

    validated = validate_component_payload("houmao.dashboard", payload)

    child = validated["children"][0]
    assert child["component"] == "houmao.graphic.vegalite"
    assert child["props"]["specVersion"] == "6"
    assert child["props"]["spec"]["data"]["values"][0]["status"] == "ready"


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
