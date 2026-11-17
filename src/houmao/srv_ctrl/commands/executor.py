"""Fixed private execution-owner entrypoint for native OS delegation."""

from __future__ import annotations

from pathlib import Path

import click

from houmao.execution.owner import serve_stdio


@click.group(name="executor")
def executor_group() -> None:
    """Perform finite operations under provisioned execution-owner policy."""


@executor_group.command(name="serve-stdio")
@click.option("--policy", required=True, type=click.Path(path_type=Path))
def serve_stdio_command(policy: Path) -> None:
    """Read one bounded execution request and return one JSON response."""

    raise click.exceptions.Exit(serve_stdio(policy))


@click.group(name="executors")
def admin_executors_group() -> None:
    """Maintain operator locators without provisioning execution contexts."""


@admin_executors_group.command(name="reconcile")
@click.option("--executor", required=True)
@click.option("--agent-id", required=True)
def reconcile_command(executor: str, agent_id: str) -> None:
    """Publish a locator after verifying an existing owner's admitted agent."""

    from houmao.execution.router import reconcile_executor_agent
    from houmao.srv_ctrl.commands.output import emit

    emit(reconcile_executor_agent(executor, agent_id))


@admin_executors_group.command(name="forget")
@click.option("--agent-id", required=True)
def forget_command(agent_id: str) -> None:
    """Remove only a locator, leaving the owning agent and files intact."""

    from houmao.execution.locators import forget_executor_locator
    from houmao.srv_ctrl.commands.output import emit

    emit({"agent_id": agent_id, "locator_removed": forget_executor_locator(agent_id)})
