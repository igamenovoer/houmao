"""`houmao-mgr ag-ui` authoring commands."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

import click

from houmao.ag_ui.authoring import (
    HoumaoAgUiValidationError,
    component_schema_payload,
    implementation_category_payload,
    implementation_schema_payload,
    list_component_summaries,
    list_implementation_summaries,
    render_component_events,
    render_events_as_json,
    render_events_as_jsonl,
    render_events_as_sse,
    render_implementation_events,
    render_protocol_tool_call_events,
    template_graphic_trace_catalog_payload,
    validate_ag_ui_event_sequence,
    validate_component_payload,
    validate_implementation_payload,
)

from .output import emit


@click.group(name="ag-ui")
def ag_ui_authoring_group() -> None:
    """Generate and validate Houmao-authored standard AG-UI messages."""


@ag_ui_authoring_group.group(name="protocol")
def ag_ui_protocol_group() -> None:
    """Validate and frame schema-agnostic AG-UI protocol events."""


@ag_ui_protocol_group.group(name="events")
def ag_ui_protocol_events_group() -> None:
    """Validate and frame standard AG-UI event batches."""


@ag_ui_protocol_group.group(name="tool-call")
def ag_ui_protocol_tool_call_group() -> None:
    """Render schema-agnostic AG-UI tool-call events."""


@ag_ui_authoring_group.group(name="impl")
def ag_ui_impl_group() -> None:
    """Discover and validate Houmao AG-UI implementation schemas."""


@ag_ui_impl_group.group(name="templated-graphics")
def ag_ui_templated_graphics_group() -> None:
    """Discover Houmao templated graphics implementation schemas."""


@ag_ui_impl_group.group(name="freeform-graphics")
def ag_ui_freeform_graphics_group() -> None:
    """Discover Houmao freeform graphics implementation schemas."""


@ag_ui_impl_group.group(name="new-component")
def ag_ui_new_component_group() -> None:
    """Render custom component tool calls without Houmao implementation schemas."""


@ag_ui_authoring_group.group(name="components")
def ag_ui_components_group() -> None:
    """Discover and validate Houmao AG-UI component schemas."""


@ag_ui_authoring_group.group(name="events")
def ag_ui_events_group() -> None:
    """Render and validate standard AG-UI event batches."""


@ag_ui_protocol_events_group.command(name="validate")
@click.option(
    "--input",
    "input_path",
    required=True,
    help="AG-UI event batch JSON file, or `-` to read stdin.",
)
def validate_protocol_events_command(input_path: str) -> None:
    """Validate one standard AG-UI event batch."""

    _validate_events(input_path)


@ag_ui_protocol_events_group.command(name="frame")
@click.option(
    "--input",
    "input_path",
    required=True,
    help="AG-UI event batch JSON file, or `-` to read stdin.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "jsonl", "sse"]),
    default="json",
    show_default=True,
    help="Machine output format for framed AG-UI events.",
)
def frame_protocol_events_command(
    input_path: str,
    output_format: Literal["json", "jsonl", "sse"],
) -> None:
    """Frame one validated standard AG-UI event batch."""

    try:
        payload = _read_json_document(input_path)
        events = validate_ag_ui_event_sequence(payload)
    except HoumaoAgUiValidationError as exc:
        raise click.ClickException(_error_message(exc)) from exc
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    _emit_events(events, output_format)


@ag_ui_protocol_tool_call_group.command(name="render")
@click.option("--tool-name", required=True, help="AG-UI tool-call name to emit.")
@click.option(
    "--args",
    "args_path",
    required=True,
    help="Tool-call JSON object arguments, or `-` to read stdin.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "jsonl", "sse"]),
    default="json",
    show_default=True,
    help="Machine output format for generated AG-UI events.",
)
@click.option("--message-id", default=None, help="Optional parent message id.")
@click.option("--tool-call-id", default=None, help="Optional tool-call id.")
def render_protocol_tool_call_command(
    tool_name: str,
    args_path: str,
    output_format: Literal["json", "jsonl", "sse"],
    message_id: str | None,
    tool_call_id: str | None,
) -> None:
    """Render one schema-agnostic JSON argument object as AG-UI tool-call events."""

    try:
        args = _read_json_document(args_path)
        events = render_protocol_tool_call_events(
            tool_name=tool_name,
            args=args,
            message_id=message_id,
            tool_call_id=tool_call_id,
        )
    except HoumaoAgUiValidationError as exc:
        raise click.ClickException(_error_message(exc)) from exc
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    _emit_events(events, output_format)


@ag_ui_impl_group.command(name="list")
def list_implementations_command() -> None:
    """List Houmao AG-UI implementation schemas."""

    emit({"implementations": list_implementation_summaries()})


@ag_ui_impl_group.command(name="schema")
@click.argument("implementation")
def implementation_schema_command(implementation: str) -> None:
    """Return one Houmao AG-UI implementation schema."""

    try:
        emit(implementation_schema_payload(implementation))
    except HoumaoAgUiValidationError as exc:
        raise click.ClickException(_error_message(exc)) from exc


@ag_ui_impl_group.command(name="validate")
@click.argument("implementation")
@click.option(
    "--input",
    "input_path",
    required=True,
    help="Implementation payload JSON file, or `-` to read stdin.",
)
def validate_implementation_command(implementation: str, input_path: str) -> None:
    """Validate one Houmao AG-UI implementation payload."""

    _validate_implementation(implementation, input_path)


@ag_ui_impl_group.command(name="render")
@click.argument("implementation")
@click.option(
    "--input",
    "input_path",
    required=True,
    help="Implementation payload JSON file, or `-` to read stdin.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "jsonl", "sse"]),
    default="json",
    show_default=True,
    help="Machine output format for generated AG-UI events.",
)
@click.option("--message-id", default=None, help="Optional parent message id.")
@click.option("--tool-call-id", default=None, help="Optional tool-call id.")
def render_implementation_command(
    implementation: str,
    input_path: str,
    output_format: Literal["json", "jsonl", "sse"],
    message_id: str | None,
    tool_call_id: str | None,
) -> None:
    """Render one implementation payload as standard AG-UI events."""

    try:
        payload = _read_json_document(input_path)
        events = render_implementation_events(
            implementation=implementation,
            payload=payload,
            message_id=message_id,
            tool_call_id=tool_call_id,
        )
    except HoumaoAgUiValidationError as exc:
        raise click.ClickException(_error_message(exc)) from exc
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    _emit_events(events, output_format)


@ag_ui_templated_graphics_group.command(name="list")
def list_templated_graphics_command() -> None:
    """List Houmao templated graphics implementation schemas."""

    emit(implementation_category_payload("templated-graphics"))


@ag_ui_freeform_graphics_group.command(name="list")
def list_freeform_graphics_command() -> None:
    """List Houmao freeform graphics implementation schemas."""

    emit(implementation_category_payload("freeform-graphics"))


@ag_ui_new_component_group.command(name="render")
@click.option("--tool-name", required=True, help="Custom AG-UI tool-call name to emit.")
@click.option(
    "--args",
    "args_path",
    required=True,
    help="Custom tool-call JSON object arguments, or `-` to read stdin.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "jsonl", "sse"]),
    default="json",
    show_default=True,
    help="Machine output format for generated AG-UI events.",
)
@click.option("--message-id", default=None, help="Optional parent message id.")
@click.option("--tool-call-id", default=None, help="Optional tool-call id.")
def render_new_component_command(
    tool_name: str,
    args_path: str,
    output_format: Literal["json", "jsonl", "sse"],
    message_id: str | None,
    tool_call_id: str | None,
) -> None:
    """Render custom component args as AG-UI tool-call events."""

    try:
        args = _read_json_document(args_path)
        events = render_protocol_tool_call_events(
            tool_name=tool_name,
            args=args,
            message_id=message_id,
            tool_call_id=tool_call_id,
        )
    except HoumaoAgUiValidationError as exc:
        raise click.ClickException(_error_message(exc)) from exc
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    _emit_events(events, output_format)


@ag_ui_impl_group.command(name="catalog")
@click.argument("implementation")
@click.argument("catalog_name")
def implementation_catalog_command(implementation: str, catalog_name: str) -> None:
    """Return one discoverable implementation catalog."""

    if implementation == "houmao.graphic.template" and catalog_name == "traces":
        emit(template_graphic_trace_catalog_payload(), plain_renderer=_render_trace_catalog_plain)
        return
    raise click.ClickException(
        json.dumps(
            {
                "ok": False,
                "implementation": implementation,
                "catalog": catalog_name,
                "message": "Unknown AG-UI implementation catalog.",
                "repairHint": "Run `houmao-mgr ag-ui impl schema IMPLEMENTATION`.",
            },
            sort_keys=True,
        )
    )


@ag_ui_components_group.command(name="list")
def list_components_command() -> None:
    """List Houmao AG-UI component schemas."""

    emit({"components": list_component_summaries()})


@ag_ui_components_group.command(name="schema")
@click.argument("component")
def component_schema_command(component: str) -> None:
    """Return one Houmao AG-UI component schema."""

    try:
        emit(component_schema_payload(component))
    except HoumaoAgUiValidationError as exc:
        raise click.ClickException(_error_message(exc)) from exc


@ag_ui_components_group.command(name="traces")
def template_traces_command() -> None:
    """List supported Plotly 2D template graphic trace types."""

    emit(template_graphic_trace_catalog_payload(), plain_renderer=_render_trace_catalog_plain)


@ag_ui_components_group.command(name="validate")
@click.argument("component")
@click.option(
    "--input",
    "input_path",
    required=True,
    help="Component payload JSON file, or `-` to read stdin.",
)
def validate_component_command(component: str, input_path: str) -> None:
    """Validate one Houmao AG-UI component payload."""

    _validate_component(component, input_path)


@ag_ui_events_group.command(name="render")
@click.argument("component")
@click.option(
    "--input",
    "input_path",
    required=True,
    help="Component payload JSON file, or `-` to read stdin.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "jsonl", "sse"]),
    default="json",
    show_default=True,
    help="Machine output format for generated AG-UI events.",
)
@click.option("--message-id", default=None, help="Optional parent message id.")
@click.option("--tool-call-id", default=None, help="Optional tool-call id.")
def render_events_command(
    component: str,
    input_path: str,
    output_format: Literal["json", "jsonl", "sse"],
    message_id: str | None,
    tool_call_id: str | None,
) -> None:
    """Render one component payload as standard AG-UI events."""

    try:
        payload = _read_json_document(input_path)
        events = render_component_events(
            component=component,
            payload=payload,
            message_id=message_id,
            tool_call_id=tool_call_id,
        )
    except HoumaoAgUiValidationError as exc:
        raise click.ClickException(_error_message(exc)) from exc
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    _emit_events(events, output_format)


@ag_ui_events_group.command(name="validate")
@click.option(
    "--input",
    "input_path",
    required=True,
    help="AG-UI event batch JSON file, or `-` to read stdin.",
)
def validate_events_command(input_path: str) -> None:
    """Validate one standard AG-UI event batch."""

    _validate_events(input_path)


def _validate_component(component: str, input_path: str) -> None:
    """Validate one component payload and emit a compact success payload."""

    try:
        payload = _read_json_document(input_path)
        validated = validate_component_payload(component, payload)
    except HoumaoAgUiValidationError as exc:
        raise click.ClickException(_error_message(exc)) from exc
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    emit(
        {
            "ok": True,
            "component": component,
            "schemaVersion": validated.get("schemaVersion", 1),
        }
    )


def _validate_implementation(implementation: str, input_path: str) -> None:
    """Validate one implementation payload and emit a compact success payload."""

    try:
        payload = _read_json_document(input_path)
        validated = validate_implementation_payload(implementation, payload)
    except HoumaoAgUiValidationError as exc:
        raise click.ClickException(_error_message(exc)) from exc
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    emit(
        {
            "ok": True,
            "implementation": implementation,
            "schemaVersion": validated.get("schemaVersion", 1),
        }
    )


def _validate_events(input_path: str) -> None:
    """Validate one standard AG-UI event batch and emit a compact success payload."""

    try:
        payload = _read_json_document(input_path)
        events = validate_ag_ui_event_sequence(payload)
    except HoumaoAgUiValidationError as exc:
        raise click.ClickException(_error_message(exc)) from exc
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    emit({"ok": True, "eventCount": len(events)})


def _emit_events(
    events: list[dict[str, Any]], output_format: Literal["json", "jsonl", "sse"]
) -> None:
    """Emit normalized AG-UI events in the requested wire format."""

    if output_format == "jsonl":
        click.echo(render_events_as_jsonl(events), nl=False)
        return
    if output_format == "sse":
        click.echo(render_events_as_sse(events), nl=False)
        return
    click.echo(render_events_as_json(events))


def _read_json_document(raw_input_path: str) -> Any:
    """Read one JSON document from stdin or a file path."""

    if raw_input_path == "-":
        raw = click.get_text_stream("stdin").read()
        source = "stdin"
    else:
        path = Path(raw_input_path)
        source = str(path)
        raw = path.read_text(encoding="utf-8")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {source}: {exc}") from exc


def _error_message(exc: HoumaoAgUiValidationError) -> str:
    """Return a compact safe CLI validation message."""

    payload = exc.to_payload()
    return json.dumps(payload, sort_keys=True)


def _render_trace_catalog_plain(payload: object) -> None:
    """Render the template trace catalog in a compact plain-text form."""

    if not isinstance(payload, dict):
        click.echo(str(payload))
        return
    supported = payload.get("supportedTraceTypes")
    excluded = payload.get("excludedTraceTypes")
    if not isinstance(supported, list):
        click.echo(str(payload))
        return
    click.echo(f"supportedTraceTypes ({len(supported)}):")
    for trace_type in supported:
        click.echo(f"  - {trace_type}")
    if isinstance(excluded, dict) and excluded:
        click.echo(f"excludedTraceTypes ({len(excluded)}):")
        for trace_type, reason in sorted(excluded.items()):
            click.echo(f"  - {trace_type}: {reason}")


__all__ = ["ag_ui_authoring_group"]
