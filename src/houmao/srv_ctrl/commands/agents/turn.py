"""Managed headless turn commands for `houmao-srv-ctrl agents`."""

from __future__ import annotations

import click

from houmao.server.client import HoumaoServerClient
from houmao.server.models import HoumaoHeadlessTurnRequest, HoumaoManagedAgentIdentity

from ..common import (
    emit_json,
    pair_port_option,
    pair_request,
    resolve_managed_agent_identity,
    resolve_pair_client,
    resolve_prompt_text,
)


@click.group(name="turn")
def turn_group() -> None:
    """Server-backed managed headless turn submission and inspection commands."""


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

    client = resolve_pair_client(port=port)
    identity = _require_headless_identity(client, agent_ref=agent_ref)
    emit_json(
        pair_request(
            client.submit_headless_turn,
            identity.tracked_agent_id,
            HoumaoHeadlessTurnRequest(prompt=resolve_prompt_text(prompt=prompt)),
        )
    )


@turn_group.command(name="status")
@pair_port_option()
@click.argument("agent_ref")
@click.argument("turn_id")
def status_turn_command(port: int | None, agent_ref: str, turn_id: str) -> None:
    """Show one managed headless turn status payload."""

    client = resolve_pair_client(port=port)
    identity = _require_headless_identity(client, agent_ref=agent_ref)
    emit_json(pair_request(client.get_headless_turn_status, identity.tracked_agent_id, turn_id))


@turn_group.command(name="events")
@pair_port_option()
@click.argument("agent_ref")
@click.argument("turn_id")
def events_turn_command(port: int | None, agent_ref: str, turn_id: str) -> None:
    """Show structured events for one managed headless turn."""

    client = resolve_pair_client(port=port)
    identity = _require_headless_identity(client, agent_ref=agent_ref)
    emit_json(pair_request(client.get_headless_turn_events, identity.tracked_agent_id, turn_id))


@turn_group.command(name="stdout")
@pair_port_option()
@click.argument("agent_ref")
@click.argument("turn_id")
def stdout_turn_command(port: int | None, agent_ref: str, turn_id: str) -> None:
    """Print the raw persisted stdout artifact for one managed headless turn."""

    client = resolve_pair_client(port=port)
    identity = _require_headless_identity(client, agent_ref=agent_ref)
    click.echo(
        pair_request(
            client.get_headless_turn_artifact_text,
            identity.tracked_agent_id,
            turn_id,
            artifact_name="stdout",
        ),
        nl=False,
    )


@turn_group.command(name="stderr")
@pair_port_option()
@click.argument("agent_ref")
@click.argument("turn_id")
def stderr_turn_command(port: int | None, agent_ref: str, turn_id: str) -> None:
    """Print the raw persisted stderr artifact for one managed headless turn."""

    client = resolve_pair_client(port=port)
    identity = _require_headless_identity(client, agent_ref=agent_ref)
    click.echo(
        pair_request(
            client.get_headless_turn_artifact_text,
            identity.tracked_agent_id,
            turn_id,
            artifact_name="stderr",
        ),
        nl=False,
    )


def _require_headless_identity(
    client: HoumaoServerClient,
    *,
    agent_ref: str,
) -> HoumaoManagedAgentIdentity:
    """Resolve one agent and require native headless transport for turn commands."""

    identity = resolve_managed_agent_identity(client, agent_ref=agent_ref)
    if identity.transport != "headless":
        raise click.ClickException(
            "Managed headless turn commands are unavailable for TUI-backed agents. "
            "Use `houmao-srv-ctrl agents prompt` for the default prompt path."
        )
    return identity
