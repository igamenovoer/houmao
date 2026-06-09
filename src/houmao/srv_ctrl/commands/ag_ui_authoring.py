"""`houmao-mgr internals ag-ui` authoring commands."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

import click

from houmao.ag_ui.authoring import (
    HoumaoAgUiValidationError,
    component_schema_payload,
    list_component_summaries,
    render_component_events,
    render_events_as_json,
    render_events_as_jsonl,
    render_events_as_sse,
    validate_ag_ui_event_sequence,
    validate_component_payload,
)

from .output import emit


@click.group(name="ag-ui")
def ag_ui_authoring_group() -> None:
    """Generate and validate Houmao-authored standard AG-UI messages."""


@ag_ui_authoring_group.group(name="components")
def ag_ui_components_group() -> None:
    """Discover and validate Houmao AG-UI component schemas."""


@ag_ui_authoring_group.group(name="events")
def ag_ui_events_group() -> None:
    """Render and validate standard AG-UI event batches."""


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

    if output_format == "jsonl":
        click.echo(render_events_as_jsonl(events), nl=False)
        return
    if output_format == "sse":
        click.echo(render_events_as_sse(events), nl=False)
        return
    click.echo(render_events_as_json(events))


@ag_ui_events_group.command(name="validate")
@click.option(
    "--input",
    "input_path",
    required=True,
    help="AG-UI event batch JSON file, or `-` to read stdin.",
)
def validate_events_command(input_path: str) -> None:
    """Validate one standard AG-UI event batch."""

    try:
        payload = _read_json_document(input_path)
        events = validate_ag_ui_event_sequence(payload)
    except HoumaoAgUiValidationError as exc:
        raise click.ClickException(_error_message(exc)) from exc
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    emit({"ok": True, "eventCount": len(events)})


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


__all__ = ["ag_ui_authoring_group"]
