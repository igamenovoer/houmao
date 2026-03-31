"""Managed headless turn commands for `houmao-mgr agents`."""

from __future__ import annotations

import click

from ..common import (
    managed_agent_selector_options,
    pair_port_option,
    resolve_prompt_text,
)
from ..output import emit
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
@managed_agent_selector_options
def submit_turn_command(
    port: int | None,
    prompt: str | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Submit one managed headless turn for a headless agent."""

    target = resolve_managed_agent_target(agent_id=agent_id, agent_name=agent_name, port=port)
    emit(submit_headless_turn(target, prompt=resolve_prompt_text(prompt=prompt)))


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
def events_turn_command(
    port: int | None,
    agent_id: str | None,
    agent_name: str | None,
    turn_id: str,
) -> None:
    """Show structured events for one managed headless turn."""

    target = resolve_managed_agent_target(agent_id=agent_id, agent_name=agent_name, port=port)
    emit(headless_turn_events(target, turn_id=turn_id))


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
