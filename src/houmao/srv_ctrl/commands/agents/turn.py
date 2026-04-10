"""Managed headless turn commands for `houmao-mgr agents`."""

from __future__ import annotations

import json

import click

from houmao.agents.realm_controller.backends.headless_output import (
    CanonicalHeadlessEvent,
    render_canonical_headless_events,
    renderable_public_headless_event_records,
)
from houmao.agents.realm_controller.backends.headless_output import (
    HeadlessDisplayDetail,
    resolve_headless_display_detail,
)
from ..common import (
    managed_agent_selector_options,
    pair_port_option,
    resolve_prompt_text,
)
from ..output import OutputContext, PrintStyle, emit, resolve_print_style
from ..managed_agents import (
    headless_turn_artifact_text,
    headless_turn_events,
    headless_turn_status,
    resolve_managed_agent_target,
    submit_headless_turn,
)
from houmao.server.models import HoumaoHeadlessTurnEventsResponse


@click.group(name="turn")
def turn_group() -> None:
    """Managed headless turn submission and inspection commands."""


@turn_group.command(name="submit")
@click.option(
    "--prompt",
    default=None,
    help="Prompt text to submit. If omitted, piped stdin is used.",
)
@click.option(
    "--model",
    default=None,
    help="Request-scoped headless execution model override.",
)
@click.option(
    "--reasoning-level",
    type=click.IntRange(min=0),
    default=None,
    help="Request-scoped headless tool/model-specific reasoning preset index override (>=0).",
)
@pair_port_option()
@managed_agent_selector_options
def submit_turn_command(
    port: int | None,
    prompt: str | None,
    model: str | None,
    reasoning_level: int | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Submit one managed headless turn for a headless agent."""

    target = resolve_managed_agent_target(agent_id=agent_id, agent_name=agent_name, port=port)
    emit(
        submit_headless_turn(
            target,
            prompt=resolve_prompt_text(prompt=prompt),
            model=model,
            reasoning_level=reasoning_level,
        )
    )


@turn_group.command(name="status")
@pair_port_option()
@managed_agent_selector_options
@click.argument("turn_id")
def status_turn_command(
    port: int | None,
    agent_id: str | None,
    agent_name: str | None,
    turn_id: str,
) -> None:
    """Show one managed headless turn status payload."""

    target = resolve_managed_agent_target(agent_id=agent_id, agent_name=agent_name, port=port)
    emit(headless_turn_status(target, turn_id=turn_id))


@turn_group.command(name="events")
@pair_port_option()
@managed_agent_selector_options
@click.argument("turn_id")
@click.option(
    "--detail",
    "display_detail",
    type=click.Choice(["concise", "detail"]),
    default="concise",
    show_default=True,
    help="Canonical event detail level for replay output.",
)
def events_turn_command(
    port: int | None,
    agent_id: str | None,
    agent_name: str | None,
    turn_id: str,
    display_detail: str,
) -> None:
    """Show structured events for one managed headless turn."""

    target = resolve_managed_agent_target(agent_id=agent_id, agent_name=agent_name, port=port)
    response = headless_turn_events(target, turn_id=turn_id)
    _render_turn_events_response(
        response=response,
        style=_active_print_style(),
        detail=resolve_headless_display_detail(display_detail),
    )


@turn_group.command(name="stdout")
@pair_port_option()
@managed_agent_selector_options
@click.argument("turn_id")
def stdout_turn_command(
    port: int | None,
    agent_id: str | None,
    agent_name: str | None,
    turn_id: str,
) -> None:
    """Print the raw persisted stdout artifact for one managed headless turn."""

    target = resolve_managed_agent_target(agent_id=agent_id, agent_name=agent_name, port=port)
    click.echo(
        headless_turn_artifact_text(target, turn_id=turn_id, artifact_name="stdout"),
        nl=False,
    )


@turn_group.command(name="stderr")
@pair_port_option()
@managed_agent_selector_options
@click.argument("turn_id")
def stderr_turn_command(
    port: int | None,
    agent_id: str | None,
    agent_name: str | None,
    turn_id: str,
) -> None:
    """Print the raw persisted stderr artifact for one managed headless turn."""

    target = resolve_managed_agent_target(agent_id=agent_id, agent_name=agent_name, port=port)
    click.echo(
        headless_turn_artifact_text(target, turn_id=turn_id, artifact_name="stderr"),
        nl=False,
    )


def _active_print_style() -> PrintStyle:
    """Return the current root print style for CLI rendering."""

    ctx = click.get_current_context(silent=True)
    if ctx is not None and isinstance(ctx.obj, dict):
        output = ctx.obj.get("output")
        if isinstance(output, OutputContext):
            return output.style
    return resolve_print_style(None)


def _render_turn_events_response(
    *,
    response: HoumaoHeadlessTurnEventsResponse,
    style: PrintStyle,
    detail: HeadlessDisplayDetail,
) -> None:
    """Replay one headless turn-event response with canonical rendering."""

    canonical_events = [
        CanonicalHeadlessEvent.from_public_event(entry.model_dump(mode="json"))
        for entry in response.entries
    ]
    if style == "json":
        click.echo(
            json.dumps(
                {
                    "tracked_agent_id": response.tracked_agent_id,
                    "turn_id": response.turn_id,
                    "entries": renderable_public_headless_event_records(
                        events=canonical_events,
                        detail=detail,
                    ),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return

    rendered_chunks: list[str] = []
    render_canonical_headless_events(
        events=canonical_events,
        style=style,
        detail=detail,
        sink=rendered_chunks.append,
    )
    click.echo("".join(rendered_chunks), nl=False)
