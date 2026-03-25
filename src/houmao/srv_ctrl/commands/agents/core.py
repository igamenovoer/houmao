"""Server-backed managed-agent commands for `houmao-mgr`."""

from __future__ import annotations

import click

from houmao.server.models import (
    HoumaoManagedAgentInterruptRequest,
    HoumaoManagedAgentSubmitPromptRequest,
)

from .gateway import gateway_group
from .mail import mail_group
from .turn import turn_group
from ..common import (
    emit_json,
    managed_agent_argument,
    pair_port_option,
    pair_request,
    resolve_pair_client,
    resolve_prompt_text,
)


@click.group(name="agents")
def agents_group() -> None:
    """Server-backed managed-agent operations routed through `houmao-server`."""


@agents_group.command(name="list")
@pair_port_option()
def list_agents_command(port: int | None) -> None:
    """List managed agents through the pair authority."""

    client = resolve_pair_client(port=port)
    emit_json(pair_request(client.list_managed_agents))


@agents_group.command(name="show")
@pair_port_option()
@managed_agent_argument
def show_agent_command(port: int | None, agent_ref: str) -> None:
    """Show the detail-oriented managed-agent view from `state/detail`."""

    client = resolve_pair_client(port=port)
    emit_json(pair_request(client.get_managed_agent_state_detail, agent_ref))


@agents_group.command(name="state")
@pair_port_option()
@managed_agent_argument
def state_agent_command(port: int | None, agent_ref: str) -> None:
    """Show the operational managed-agent summary view."""

    client = resolve_pair_client(port=port)
    emit_json(pair_request(client.get_managed_agent_state, agent_ref))


@agents_group.command(name="history")
@click.option("--limit", default=20, type=int, show_default=True, help="History entry limit.")
@pair_port_option()
@managed_agent_argument
def history_agent_command(port: int | None, limit: int, agent_ref: str) -> None:
    """Show bounded managed-agent history through the pair authority."""

    client = resolve_pair_client(port=port)
    emit_json(pair_request(client.get_managed_agent_history, agent_ref, limit=limit))


@agents_group.command(name="prompt")
@click.option(
    "--prompt",
    default=None,
    help="Prompt text to submit. If omitted, piped stdin is used.",
)
@pair_port_option(help_text="Houmao server port to use for the default prompt path")
@managed_agent_argument
def prompt_agent_command(port: int | None, prompt: str | None, agent_ref: str) -> None:
    """Submit the default transport-neutral prompt path for one managed agent."""

    client = resolve_pair_client(port=port)
    emit_json(
        pair_request(
            client.submit_managed_agent_request,
            agent_ref,
            HoumaoManagedAgentSubmitPromptRequest(prompt=resolve_prompt_text(prompt=prompt)),
        )
    )


@agents_group.command(name="interrupt")
@pair_port_option()
@managed_agent_argument
def interrupt_agent_command(port: int | None, agent_ref: str) -> None:
    """Request an interrupt through the managed-agent server authority."""

    client = resolve_pair_client(port=port)
    emit_json(
        pair_request(
            client.submit_managed_agent_request,
            agent_ref,
            HoumaoManagedAgentInterruptRequest(),
        )
    )


@agents_group.command(name="stop")
@pair_port_option()
@managed_agent_argument
def stop_agent_command(port: int | None, agent_ref: str) -> None:
    """Stop a managed agent through the shared pair lifecycle."""

    client = resolve_pair_client(port=port)
    emit_json(pair_request(client.stop_managed_agent, agent_ref))

agents_group.add_command(gateway_group)
agents_group.add_command(mail_group)
agents_group.add_command(turn_group)
