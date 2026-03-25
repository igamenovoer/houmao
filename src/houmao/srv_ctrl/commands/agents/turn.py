"""Managed headless turn commands for `houmao-mgr agents`."""

from __future__ import annotations

import click

from ..common import emit_json, pair_port_option, resolve_prompt_text
from ..managed_agents import (
    headless_turn_artifact_text,
    headless_turn_events,
    headless_turn_status,
    resolve_managed_agent_target,
    submit_headless_turn,
)


@click.group(name="turn")
def turn_group() -> None:
    """Managed headless turn submission and inspection commands."""


@turn_group.command(name="submit")
@click.option(
    "--prompt",
    default=None,
    help="Prompt text to submit. If omitted, piped stdin is used.",
)
@pair_port_option()
@click.argument("agent_ref")
def submit_turn_command(port: int | None, prompt: str | None, agent_ref: str) -> None:
    """Submit one managed headless turn for a headless agent."""

    target = resolve_managed_agent_target(agent_ref=agent_ref, port=port)
    emit_json(submit_headless_turn(target, prompt=resolve_prompt_text(prompt=prompt)))


@turn_group.command(name="status")
@pair_port_option()
@click.argument("agent_ref")
@click.argument("turn_id")
def status_turn_command(port: int | None, agent_ref: str, turn_id: str) -> None:
    """Show one managed headless turn status payload."""

    target = resolve_managed_agent_target(agent_ref=agent_ref, port=port)
    emit_json(headless_turn_status(target, turn_id=turn_id))


@turn_group.command(name="events")
@pair_port_option()
@click.argument("agent_ref")
@click.argument("turn_id")
def events_turn_command(port: int | None, agent_ref: str, turn_id: str) -> None:
    """Show structured events for one managed headless turn."""

    target = resolve_managed_agent_target(agent_ref=agent_ref, port=port)
    emit_json(headless_turn_events(target, turn_id=turn_id))


@turn_group.command(name="stdout")
@pair_port_option()
@click.argument("agent_ref")
@click.argument("turn_id")
def stdout_turn_command(port: int | None, agent_ref: str, turn_id: str) -> None:
    """Print the raw persisted stdout artifact for one managed headless turn."""

    target = resolve_managed_agent_target(agent_ref=agent_ref, port=port)
    click.echo(
        headless_turn_artifact_text(target, turn_id=turn_id, artifact_name="stdout"),
        nl=False,
    )


@turn_group.command(name="stderr")
@pair_port_option()
@click.argument("agent_ref")
@click.argument("turn_id")
def stderr_turn_command(port: int | None, agent_ref: str, turn_id: str) -> None:
    """Print the raw persisted stderr artifact for one managed headless turn."""

    target = resolve_managed_agent_target(agent_ref=agent_ref, port=port)
    click.echo(
        headless_turn_artifact_text(target, turn_id=turn_id, artifact_name="stderr"),
        nl=False,
    )
