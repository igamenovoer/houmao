from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner
import pytest

from houmao.ag_ui.authoring import render_component_events
from houmao.ag_ui.models import AgUiEventPublishResponse
from houmao.srv_ctrl.commands.agents import gateway as gateway_commands
from houmao.srv_ctrl.commands.main import cli


def _write_json(path: Path, payload: object) -> Path:
    """Write one JSON fixture."""

    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _template_payload() -> dict[str, object]:
    """Return one valid template graphic payload."""

    return {
        "schemaVersion": 3,
        "figureType": "plotly2d",
        "renderer": {"preferred": "plotly"},
        "title": "Build Results",
        "traces": [
            {
                "type": "bar",
                "data": {"x": ["passed", "failed"], "y": [42, 2]},
                "style": {"marker": {"color": ["#1f7a4d", "#c2410c"]}},
            }
        ],
        "layout": {"xaxis": {"title": "Status"}, "yaxis": {"title": "Count"}},
    }


def _vegalite_payload() -> dict[str, object]:
    """Return one valid Vega-Lite graphic payload."""

    return {
        "schemaVersion": 1,
        "library": "vega-lite",
        "specVersion": "6",
        "title": "Queue Status",
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
    }


def _table_payload() -> dict[str, object]:
    """Return one valid table component payload."""

    return {
        "schemaVersion": 1,
        "title": "Top Issues",
        "columns": [{"key": "id", "label": "ID"}],
        "rows": [{"id": "A"}],
    }


def test_ag_ui_components_list_and_schema_are_json_renderable() -> None:
    runner = CliRunner()

    list_result = runner.invoke(cli, ["--print-json", "internals", "ag-ui", "components", "list"])
    schema_result = runner.invoke(
        cli,
        [
            "--print-json",
            "internals",
            "ag-ui",
            "components",
            "schema",
            "houmao.graphic.template",
        ],
    )

    assert list_result.exit_code == 0, list_result.output
    assert schema_result.exit_code == 0, schema_result.output
    listed = json.loads(list_result.output)
    schema = json.loads(schema_result.output)
    assert "houmao.chart.bar" not in {item["name"] for item in listed["components"]}
    assert "houmao.graphic.template" in {item["name"] for item in listed["components"]}
    assert "houmao.graphic.vegalite" in {item["name"] for item in listed["components"]}
    assert schema["name"] == "houmao.graphic.template"
    assert schema["example"]["schemaVersion"] == 3
    assert schema["example"]["figureType"] == "plotly2d"
    assert "heatmap" in schema["traceCatalog"]["supportedTraceTypes"]

    vegalite_schema_result = runner.invoke(
        cli,
        [
            "--print-json",
            "internals",
            "ag-ui",
            "components",
            "schema",
            "houmao.graphic.vegalite",
        ],
    )
    assert vegalite_schema_result.exit_code == 0, vegalite_schema_result.output
    vegalite_schema = json.loads(vegalite_schema_result.output)
    assert vegalite_schema["name"] == "houmao.graphic.vegalite"
    assert vegalite_schema["example"]["library"] == "vega-lite"
    assert vegalite_schema["example"]["specVersion"] == "6"


def test_ag_ui_impl_list_schema_and_category_commands_are_json_renderable() -> None:
    runner = CliRunner()

    list_result = runner.invoke(cli, ["--print-json", "ag-ui", "impl", "list"])
    schema_result = runner.invoke(
        cli,
        ["--print-json", "ag-ui", "impl", "schema", "houmao.graphic.template"],
    )
    templated_result = runner.invoke(
        cli,
        ["--print-json", "ag-ui", "impl", "templated-graphics", "list"],
    )
    freeform_result = runner.invoke(
        cli,
        ["--print-json", "ag-ui", "impl", "freeform-graphics", "list"],
    )

    assert list_result.exit_code == 0, list_result.output
    assert schema_result.exit_code == 0, schema_result.output
    assert templated_result.exit_code == 0, templated_result.output
    assert freeform_result.exit_code == 0, freeform_result.output
    listed = json.loads(list_result.output)
    schema = json.loads(schema_result.output)
    templated = json.loads(templated_result.output)
    freeform = json.loads(freeform_result.output)
    assert "houmao.graphic.template" in {item["name"] for item in listed["implementations"]}
    assert "houmao.graphic.vegalite" in {item["name"] for item in listed["implementations"]}
    assert schema["category"] == "templated-graphics"
    assert schema["backend"] == "plotly"
    assert schema["renderer"] == "plotly.js"
    assert [item["name"] for item in templated["schemas"]] == ["houmao.graphic.template"]
    assert templated["schemas"][0]["catalogs"] == ["traces"]
    assert [item["name"] for item in freeform["schemas"]] == ["houmao.graphic.vegalite"]
    assert freeform["schemas"][0]["backend"] == "vega-lite"


def test_ag_ui_components_traces_lists_template_trace_catalog() -> None:
    runner = CliRunner()

    json_result = runner.invoke(
        cli,
        ["--print-json", "internals", "ag-ui", "components", "traces"],
    )
    plain_result = CliRunner().invoke(
        cli,
        ["--print-plain", "internals", "ag-ui", "components", "traces"],
    )

    assert json_result.exit_code == 0, json_result.output
    payload = json.loads(json_result.output)
    assert payload["component"] == "houmao.graphic.template"
    assert payload["schemaVersion"] == 3
    assert payload["figureType"] == "plotly2d"
    assert "heatmap" in payload["supportedTraceTypes"]
    assert "sankey" in payload["supportedTraceTypes"]
    assert payload["excludedTraceTypes"]["scatter3d"] == "true_3d_scene_trace"
    assert plain_result.exit_code == 0, plain_result.output
    assert "supportedTraceTypes (42)" in plain_result.output
    assert "scatter3d: true_3d_scene_trace" in plain_result.output


def test_ag_ui_impl_catalog_lists_template_trace_catalog() -> None:
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "--print-json",
            "ag-ui",
            "impl",
            "catalog",
            "houmao.graphic.template",
            "traces",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["implementation"] == "houmao.graphic.template"
    assert payload["component"] == "houmao.graphic.template"
    assert "heatmap" in payload["supportedTraceTypes"]


def test_ag_ui_components_retired_fixed_chart_schema_reports_migration_hint() -> None:
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "internals",
            "ag-ui",
            "components",
            "schema",
            "houmao.chart.bar",
        ],
    )

    assert result.exit_code != 0
    assert "Retired Houmao AG-UI implementation" in result.output
    assert "houmao.graphic.template" in result.output


def test_ag_ui_template_graphic_validate_and_render_accept_path_input(tmp_path: Path) -> None:
    runner = CliRunner()
    payload_path = _write_json(tmp_path / "template.json", _template_payload())

    validate_result = runner.invoke(
        cli,
        [
            "--print-json",
            "internals",
            "ag-ui",
            "components",
            "validate",
            "houmao.graphic.template",
            "--input",
            str(payload_path),
        ],
    )
    render_result = runner.invoke(
        cli,
        [
            "internals",
            "ag-ui",
            "events",
            "render",
            "houmao.graphic.template",
            "--input",
            str(payload_path),
            "--message-id",
            "message-1",
            "--tool-call-id",
            "tool-1",
        ],
    )

    assert validate_result.exit_code == 0, validate_result.output
    assert json.loads(validate_result.output) == {
        "component": "houmao.graphic.template",
        "ok": True,
        "schemaVersion": 3,
    }
    assert render_result.exit_code == 0, render_result.output
    events = json.loads(render_result.output)
    assert events[0]["toolCallName"] == "houmao.graphic.template"
    args = json.loads(events[1]["delta"])
    assert args["figureType"] == "plotly2d"
    assert args["renderer"]["preferred"] == "plotly"


def test_ag_ui_impl_template_graphic_validate_and_render_accept_path_input(
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    payload_path = _write_json(tmp_path / "template.json", _template_payload())

    validate_result = runner.invoke(
        cli,
        [
            "--print-json",
            "ag-ui",
            "impl",
            "validate",
            "houmao.graphic.template",
            "--input",
            str(payload_path),
        ],
    )
    render_result = runner.invoke(
        cli,
        [
            "ag-ui",
            "impl",
            "render",
            "houmao.graphic.template",
            "--input",
            str(payload_path),
            "--message-id",
            "message-1",
            "--tool-call-id",
            "tool-1",
        ],
    )

    assert validate_result.exit_code == 0, validate_result.output
    assert json.loads(validate_result.output) == {
        "implementation": "houmao.graphic.template",
        "ok": True,
        "schemaVersion": 3,
    }
    assert render_result.exit_code == 0, render_result.output
    events = json.loads(render_result.output)
    assert events[0]["toolCallName"] == "houmao.graphic.template"
    assert json.loads(events[1]["delta"])["figureType"] == "plotly2d"


def test_ag_ui_vegalite_validate_and_render_accept_path_input(tmp_path: Path) -> None:
    runner = CliRunner()
    payload_path = _write_json(tmp_path / "vegalite.json", _vegalite_payload())

    validate_result = runner.invoke(
        cli,
        [
            "--print-json",
            "internals",
            "ag-ui",
            "components",
            "validate",
            "houmao.graphic.vegalite",
            "--input",
            str(payload_path),
        ],
    )
    render_result = runner.invoke(
        cli,
        [
            "internals",
            "ag-ui",
            "events",
            "render",
            "houmao.graphic.vegalite",
            "--input",
            str(payload_path),
            "--message-id",
            "message-vega",
            "--tool-call-id",
            "tool-vega",
        ],
    )

    assert validate_result.exit_code == 0, validate_result.output
    assert json.loads(validate_result.output) == {
        "component": "houmao.graphic.vegalite",
        "ok": True,
        "schemaVersion": 1,
    }
    assert render_result.exit_code == 0, render_result.output
    events = json.loads(render_result.output)
    assert events[0]["toolCallName"] == "houmao.graphic.vegalite"
    assert json.loads(events[1]["delta"])["specVersion"] == "6"


def test_ag_ui_impl_vegalite_validate_and_render_accept_path_input(tmp_path: Path) -> None:
    runner = CliRunner()
    payload_path = _write_json(tmp_path / "vegalite.json", _vegalite_payload())

    validate_result = runner.invoke(
        cli,
        [
            "--print-json",
            "ag-ui",
            "impl",
            "validate",
            "houmao.graphic.vegalite",
            "--input",
            str(payload_path),
        ],
    )
    render_result = runner.invoke(
        cli,
        [
            "ag-ui",
            "impl",
            "render",
            "houmao.graphic.vegalite",
            "--input",
            str(payload_path),
            "--message-id",
            "message-vega",
            "--tool-call-id",
            "tool-vega",
        ],
    )

    assert validate_result.exit_code == 0, validate_result.output
    assert json.loads(validate_result.output) == {
        "implementation": "houmao.graphic.vegalite",
        "ok": True,
        "schemaVersion": 1,
    }
    assert render_result.exit_code == 0, render_result.output
    events = json.loads(render_result.output)
    assert events[0]["toolCallName"] == "houmao.graphic.vegalite"
    assert json.loads(events[1]["delta"])["specVersion"] == "6"


def test_ag_ui_component_validate_accepts_path_input(tmp_path: Path) -> None:
    runner = CliRunner()
    payload_path = _write_json(tmp_path / "payload.json", _table_payload())

    result = runner.invoke(
        cli,
        [
            "--print-json",
            "internals",
            "ag-ui",
            "components",
            "validate",
            "houmao.table",
            "--input",
            str(payload_path),
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload == {"component": "houmao.table", "ok": True, "schemaVersion": 1}


def test_ag_ui_component_validate_reports_invalid_payload(tmp_path: Path) -> None:
    runner = CliRunner()
    payload_path = _write_json(tmp_path / "payload.json", {"schemaVersion": 1, "title": ""})

    result = runner.invoke(
        cli,
        [
            "internals",
            "ag-ui",
            "components",
            "validate",
            "houmao.table",
            "--input",
            str(payload_path),
        ],
    )

    assert result.exit_code != 0
    assert "houmao.table" in result.output
    assert "fieldPaths" in result.output


def test_ag_ui_events_render_accepts_stdin_and_outputs_json() -> None:
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "internals",
            "ag-ui",
            "events",
            "render",
            "houmao.graphic.template",
            "--input",
            "-",
            "--message-id",
            "message-1",
            "--tool-call-id",
            "tool-1",
        ],
        input=json.dumps(_template_payload()),
    )

    assert result.exit_code == 0, result.output
    events = json.loads(result.output)
    assert [event["type"] for event in events] == [
        "TOOL_CALL_START",
        "TOOL_CALL_ARGS",
        "TOOL_CALL_END",
    ]
    assert events[0]["toolCallName"] == "houmao.graphic.template"
    assert events[0]["parentMessageId"] == "message-1"


def test_ag_ui_events_render_outputs_jsonl_and_sse() -> None:
    runner = CliRunner()

    jsonl_result = runner.invoke(
        cli,
        [
            "internals",
            "ag-ui",
            "events",
            "render",
            "houmao.metric_grid",
            "--input",
            "-",
            "--format",
            "jsonl",
        ],
        input=json.dumps(
            {
                "schemaVersion": 1,
                "metrics": [{"label": "Pass rate", "value": "98%"}],
            }
        ),
    )
    sse_result = runner.invoke(
        cli,
        [
            "internals",
            "ag-ui",
            "events",
            "render",
            "houmao.metric_grid",
            "--input",
            "-",
            "--format",
            "sse",
        ],
        input=json.dumps(
            {
                "schemaVersion": 1,
                "metrics": [{"label": "Pass rate", "value": "98%"}],
            }
        ),
    )

    assert jsonl_result.exit_code == 0, jsonl_result.output
    assert sse_result.exit_code == 0, sse_result.output
    assert len(jsonl_result.output.strip().splitlines()) == 3
    assert sse_result.output.count("data: ") == 3


def test_ag_ui_protocol_tool_call_and_new_component_render_schema_agnostic_events(
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    args_path = _write_json(
        tmp_path / "args.json",
        {"schemaVersion": 1, "items": [{"label": "A", "start": 1, "end": 2}]},
    )

    protocol_result = runner.invoke(
        cli,
        [
            "ag-ui",
            "protocol",
            "tool-call",
            "render",
            "--tool-name",
            "myapp.graphic.timeline",
            "--args",
            str(args_path),
            "--message-id",
            "message-custom",
            "--tool-call-id",
            "tool-custom",
        ],
    )
    new_component_result = runner.invoke(
        cli,
        [
            "ag-ui",
            "impl",
            "new-component",
            "render",
            "--tool-name",
            "myapp.graphic.timeline",
            "--args",
            str(args_path),
        ],
    )

    assert protocol_result.exit_code == 0, protocol_result.output
    assert new_component_result.exit_code == 0, new_component_result.output
    protocol_events = json.loads(protocol_result.output)
    new_component_events = json.loads(new_component_result.output)
    assert protocol_events[0]["toolCallName"] == "myapp.graphic.timeline"
    assert new_component_events[0]["toolCallName"] == "myapp.graphic.timeline"
    assert json.loads(protocol_events[1]["delta"])["items"][0]["label"] == "A"


def test_ag_ui_events_validate_accepts_rendered_batch(tmp_path: Path) -> None:
    runner = CliRunner()
    rendered = runner.invoke(
        cli,
        [
            "internals",
            "ag-ui",
            "events",
            "render",
            "houmao.graphic.template",
            "--input",
            "-",
        ],
        input=json.dumps(_template_payload()),
    )
    events_path = tmp_path / "events.json"
    events_path.write_text(rendered.output, encoding="utf-8")

    result = runner.invoke(
        cli,
        [
            "--print-json",
            "internals",
            "ag-ui",
            "events",
            "validate",
            "--input",
            str(events_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == {"eventCount": 3, "ok": True}


def test_ag_ui_protocol_events_validate_and_frame_accept_rendered_batch(tmp_path: Path) -> None:
    runner = CliRunner()
    rendered = runner.invoke(
        cli,
        ["ag-ui", "impl", "render", "houmao.graphic.template", "--input", "-"],
        input=json.dumps(_template_payload()),
    )
    events_path = tmp_path / "events.json"
    events_path.write_text(rendered.output, encoding="utf-8")

    validate_result = runner.invoke(
        cli,
        ["--print-json", "ag-ui", "protocol", "events", "validate", "--input", str(events_path)],
    )
    frame_result = runner.invoke(
        cli,
        [
            "ag-ui",
            "protocol",
            "events",
            "frame",
            "--input",
            str(events_path),
            "--format",
            "sse",
        ],
    )

    assert validate_result.exit_code == 0, validate_result.output
    assert json.loads(validate_result.output) == {"eventCount": 3, "ok": True}
    assert frame_result.exit_code == 0, frame_result.output
    assert frame_result.output.count("data: ") == 3


def test_ag_ui_events_validate_rejects_raw_component_payload(tmp_path: Path) -> None:
    runner = CliRunner()
    raw_path = _write_json(tmp_path / "component.json", _template_payload())

    result = runner.invoke(
        cli,
        [
            "internals",
            "ag-ui",
            "events",
            "validate",
            "--input",
            str(raw_path),
        ],
    )

    assert result.exit_code != 0
    assert "JSON array of event objects" in result.output


def test_ag_ui_components_unknown_component_reports_fix_guide() -> None:
    runner = CliRunner()

    result = runner.invoke(cli, ["internals", "ag-ui", "components", "schema", "chat.bar"])

    assert result.exit_code != 0
    assert "Unknown Houmao AG-UI implementation" in result.output
    assert "ag-ui impl list" in result.output


def test_gateway_ag_ui_publish_validates_path_input_and_posts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = CliRunner()
    events = render_component_events(
        component="houmao.graphic.template", payload=_template_payload()
    )
    events_path = _write_json(tmp_path / "events.json", events)
    calls: list[dict[str, object]] = []

    monkeypatch.setattr(
        gateway_commands, "_resolve_gateway_command_target", lambda **_kwargs: object()
    )

    def _fake_publish(target: object, *, request_model: object) -> AgUiEventPublishResponse:
        calls.append({"target": target, "request": request_model})
        return AgUiEventPublishResponse(
            accepted_count=3,
            stored_count=0,
            delivered_count=0,
            replay="none",
            thread_id="thread-1",
        )

    monkeypatch.setattr(gateway_commands, "gateway_ag_ui_publish", _fake_publish)

    result = runner.invoke(
        cli,
        [
            "--print-json",
            "agents",
            "self",
            "gateway",
            "ag-ui",
            "publish",
            "--input",
            str(events_path),
            "--thread-id",
            "thread-1",
        ],
    )

    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    request_model = calls[0]["request"]
    assert getattr(request_model, "thread_id") == "thread-1"
    assert len(getattr(request_model, "events")) == 3
    payload = json.loads(result.output)
    assert payload["accepted_count"] == 3
    assert payload["stored_count"] == 0
    assert payload["delivered_count"] == 0
    assert payload["replay"] == "none"


def test_gateway_ag_ui_publish_allows_omitted_route_and_reports_sink_warning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = CliRunner()
    events = render_component_events(
        component="houmao.graphic.template", payload=_template_payload()
    )
    events_path = _write_json(tmp_path / "events.json", events)
    calls: list[dict[str, object]] = []

    monkeypatch.setattr(
        gateway_commands, "_resolve_gateway_command_target", lambda **_kwargs: object()
    )

    def _fake_publish(target: object, *, request_model: object) -> AgUiEventPublishResponse:
        calls.append({"target": target, "request": request_model})
        return AgUiEventPublishResponse(
            accepted_count=3,
            stored_count=0,
            delivered_count=0,
            replay="none",
            destination_kind="default_sink",
            warnings=["default_sink_due_to_no_destination"],
        )

    monkeypatch.setattr(gateway_commands, "gateway_ag_ui_publish", _fake_publish)

    result = runner.invoke(
        cli,
        [
            "--print-json",
            "agents",
            "self",
            "gateway",
            "ag-ui",
            "publish",
            "--input",
            str(events_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    request_model = calls[0]["request"]
    assert getattr(request_model, "thread_id") is None
    assert getattr(request_model, "run_id") is None
    assert getattr(request_model, "connection_id") is None
    payload = json.loads(result.output)
    assert payload["destination_kind"] == "default_sink"
    assert payload["warnings"] == ["default_sink_due_to_no_destination"]
    assert payload["delivered_count"] == 0


def test_gateway_ag_ui_publish_plain_output_reports_zero_delivery_without_visibility_claim(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = CliRunner()
    events = render_component_events(
        component="houmao.graphic.template", payload=_template_payload()
    )
    events_path = _write_json(tmp_path / "events.json", events)

    monkeypatch.setattr(
        gateway_commands, "_resolve_gateway_command_target", lambda **_kwargs: object()
    )

    def _fake_publish(_target: object, *, request_model: object) -> AgUiEventPublishResponse:
        assert getattr(request_model, "thread_id") is None
        return AgUiEventPublishResponse(
            accepted_count=3,
            stored_count=0,
            delivered_count=0,
            replay="none",
            destination_kind="active_thread",
        )

    monkeypatch.setattr(gateway_commands, "gateway_ag_ui_publish", _fake_publish)

    result = runner.invoke(
        cli,
        [
            "agents",
            "self",
            "gateway",
            "ag-ui",
            "publish",
            "--input",
            str(events_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "delivered_count" in result.output
    assert "0" in result.output
    assert "visible" not in result.output.lower()
    assert "displayed" not in result.output.lower()


def test_gateway_ag_ui_publish_rejects_empty_batch_before_http(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = CliRunner()
    monkeypatch.setattr(
        gateway_commands, "_resolve_gateway_command_target", lambda **_kwargs: object()
    )

    def _fail_publish(*_args: object, **_kwargs: object) -> AgUiEventPublishResponse:
        raise AssertionError("publish should not be called")

    monkeypatch.setattr(gateway_commands, "gateway_ag_ui_publish", _fail_publish)

    result = runner.invoke(
        cli,
        [
            "agents",
            "self",
            "gateway",
            "ag-ui",
            "publish",
            "--input",
            "-",
            "--thread-id",
            "thread-1",
        ],
        input="[]",
    )

    assert result.exit_code != 0
    assert "requires at least one event" in result.output


def test_gateway_ag_ui_publish_does_not_accept_third_party_endpoint_option() -> None:
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "agents",
            "self",
            "gateway",
            "ag-ui",
            "publish",
            "--endpoint",
            "https://example.invalid/ag-ui",
            "--input",
            "-",
            "--thread-id",
            "thread-1",
        ],
        input="[]",
    )

    assert result.exit_code != 0
    assert "No such option" in result.output
    assert "--endpoint" in result.output
