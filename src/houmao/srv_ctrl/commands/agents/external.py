"""External communication-only managed-agent commands."""

from __future__ import annotations

import click

from ..common import managed_agent_selector_options
from ..managed_agents import (
    get_external_managed_agent,
    list_external_managed_agents,
    register_external_managed_agent,
    remove_external_managed_agent,
    verify_external_managed_agent,
)
from ..output import emit
from ..renderers.agents import (
    render_external_agent_detail_fancy,
    render_external_agent_detail_plain,
    render_external_agent_list_fancy,
    render_external_agent_list_plain,
)


@click.group(name="external")
def external_group() -> None:
    """Manage local imports for remotely owned communication-only agents."""


@external_group.command(name="register")
@click.option("--name", "local_name", required=True, help="Local external-agent alias.")
@click.option(
    "--api-base-url",
    required=True,
    help="Remote houmao-passive-server base URL, for example http://127.0.0.1:9891.",
)
@click.option("--agent-ref", required=True, help="Remote managed-agent id or name.")
@click.option(
    "--gateway-enabled/--no-gateway-enabled",
    "gateway_expected",
    default=False,
    show_default=True,
    help="Require a reachable remote managed-agent gateway during registration and verify.",
)
@click.option("--replace", is_flag=True, help="Replace an existing external import by name.")
def register_external_command(
    local_name: str,
    api_base_url: str,
    agent_ref: str,
    gateway_expected: bool,
    replace: bool,
) -> None:
    """Register a remote managed agent for local communication-only control."""

    emit(
        register_external_managed_agent(
            local_name=local_name,
            api_base_url=api_base_url,
            agent_ref=agent_ref,
            gateway_expected=gateway_expected,
            replace=replace,
        ),
        plain_renderer=render_external_agent_detail_plain,
        fancy_renderer=render_external_agent_detail_fancy,
    )


@external_group.command(name="list")
def list_external_command() -> None:
    """List locally registered external communication-only agents."""

    emit(
        list_external_managed_agents(),
        plain_renderer=render_external_agent_list_plain,
        fancy_renderer=render_external_agent_list_fancy,
    )


@external_group.command(name="get")
@managed_agent_selector_options
def get_external_command(agent_id: str | None, agent_name: str | None) -> None:
    """Show one local external managed-agent import."""

    emit(
        get_external_managed_agent(agent_id=agent_id, agent_name=agent_name),
        plain_renderer=render_external_agent_detail_plain,
        fancy_renderer=render_external_agent_detail_fancy,
    )


@external_group.command(name="verify")
@managed_agent_selector_options
def verify_external_command(agent_id: str | None, agent_name: str | None) -> None:
    """Verify one remote external authority and refresh cached identity."""

    emit(
        verify_external_managed_agent(agent_id=agent_id, agent_name=agent_name),
        plain_renderer=render_external_agent_detail_plain,
        fancy_renderer=render_external_agent_detail_fancy,
    )


@external_group.command(name="remove")
@managed_agent_selector_options
def remove_external_command(agent_id: str | None, agent_name: str | None) -> None:
    """Remove one local external import without remote side effects."""

    emit(
        remove_external_managed_agent(agent_id=agent_id, agent_name=agent_name),
        plain_renderer=render_external_agent_detail_plain,
        fancy_renderer=render_external_agent_detail_fancy,
    )
