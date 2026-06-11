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


def _bar_payload() -> dict[str, object]:
    """Return one valid bar chart component payload."""

    return {
        "schemaVersion": 1,
        "title": "Quarterly Revenue",
        "data": [{"label": "Q1", "value": 120000}],
    }


def _template_payload() -> dict[str, object]:
    """Return one valid template graphic payload."""

    return {
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
            "houmao.chart.bar",
        ],
    )

    assert list_result.exit_code == 0, list_result.output
    assert schema_result.exit_code == 0, schema_result.output
    listed = json.loads(list_result.output)
    schema = json.loads(schema_result.output)
    assert "houmao.chart.bar" in {item["name"] for item in listed["components"]}
    assert "houmao.graphic.template" in {item["name"] for item in listed["components"]}
    assert schema["name"] == "houmao.chart.bar"
    assert schema["example"]["schemaVersion"] == 1


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
        "schemaVersion": 1,
    }
    assert render_result.exit_code == 0, render_result.output
    events = json.loads(render_result.output)
    assert events[0]["toolCallName"] == "houmao.graphic.template"
    assert json.loads(events[1]["delta"])["renderer"]["preferred"] == "vega-lite"


def test_ag_ui_component_validate_accepts_path_input(tmp_path: Path) -> None:
    runner = CliRunner()
    payload_path = _write_json(tmp_path / "payload.json", _bar_payload())

    result = runner.invoke(
        cli,
        [
            "--print-json",
            "internals",
            "ag-ui",
            "components",
            "validate",
            "houmao.chart.bar",
            "--input",
            str(payload_path),
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload == {"component": "houmao.chart.bar", "ok": True, "schemaVersion": 1}


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
            "houmao.chart.bar",
            "--input",
            str(payload_path),
        ],
    )

    assert result.exit_code != 0
    assert "houmao.chart.bar" in result.output
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
            "houmao.chart.bar",
            "--input",
            "-",
            "--message-id",
            "message-1",
            "--tool-call-id",
            "tool-1",
        ],
        input=json.dumps(_bar_payload()),
    )

    assert result.exit_code == 0, result.output
    events = json.loads(result.output)
    assert [event["type"] for event in events] == [
        "TOOL_CALL_START",
        "TOOL_CALL_ARGS",
        "TOOL_CALL_END",
    ]
    assert events[0]["toolCallName"] == "houmao.chart.bar"
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


def test_ag_ui_events_validate_accepts_rendered_batch(tmp_path: Path) -> None:
    runner = CliRunner()
    rendered = runner.invoke(
        cli,
        [
            "internals",
            "ag-ui",
            "events",
            "render",
            "houmao.chart.bar",
            "--input",
            "-",
        ],
        input=json.dumps(_bar_payload()),
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


def test_ag_ui_events_validate_rejects_raw_component_payload(tmp_path: Path) -> None:
    runner = CliRunner()
    raw_path = _write_json(tmp_path / "component.json", _bar_payload())

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
    assert "Unknown Houmao AG-UI component" in result.output
    assert "components list" in result.output


def test_gateway_ag_ui_publish_validates_path_input_and_posts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = CliRunner()
    events = render_component_events(component="houmao.chart.bar", payload=_bar_payload())
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
    events = render_component_events(component="houmao.chart.bar", payload=_bar_payload())
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
    events = render_component_events(component="houmao.chart.bar", payload=_bar_payload())
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
    assert "No such option '--endpoint'" in result.output
