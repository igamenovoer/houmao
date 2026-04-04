"""Late mailbox registration commands for `houmao-mgr agents`."""

from __future__ import annotations

from pathlib import Path

import click

from ..common import (
    build_destructive_confirmation_callback,
    managed_agent_selector_options,
    overwrite_confirm_option,
)
from ..output import emit
from ..project_aware_wording import mailbox_root_option_help
from ..managed_agents import (
    mailbox_status,
    register_mailbox_binding,
    resolve_managed_agent_target,
    unregister_mailbox_binding,
)


@click.group(name="mailbox")
def mailbox_group() -> None:
    """Late filesystem mailbox registration for local managed agents."""


@mailbox_group.command(name="status")
@managed_agent_selector_options
def status_mailbox_command(agent_id: str | None, agent_name: str | None) -> None:
    """Report late mailbox registration posture for one local managed agent."""

    target = resolve_managed_agent_target(agent_id=agent_id, agent_name=agent_name, port=None)
    emit(mailbox_status(target))


@mailbox_group.command(name="register")
@click.option(
    "--mailbox-root",
    type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
    default=None,
    help=mailbox_root_option_help(),
)
@click.option(
    "--principal-id",
    default=None,
    help="Optional mailbox principal id override. Defaults from the managed-agent identity.",
)
@click.option(
    "--address",
    default=None,
    help="Optional full mailbox address override. Defaults from the managed-agent identity.",
)
@click.option(
    "--mode",
    type=click.Choice(("safe", "force", "stash")),
    default="safe",
    show_default=True,
    help="Filesystem mailbox registration mode.",
)
@overwrite_confirm_option
@managed_agent_selector_options
def register_mailbox_command(
    mailbox_root: Path | None,
    principal_id: str | None,
    address: str | None,
    mode: str,
    yes: bool,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Register one filesystem mailbox binding for an existing local managed agent."""

    target = resolve_managed_agent_target(agent_id=agent_id, agent_name=agent_name, port=None)
    emit(
        register_mailbox_binding(
            target,
            mailbox_root=mailbox_root,
            principal_id=principal_id,
            address=address,
            mode=mode,
            confirm_destructive_replace=build_destructive_confirmation_callback(
                yes=yes,
                non_interactive_message=(
                    "Mailbox registration would replace existing durable mailbox state. "
                    "Rerun with `--yes` to confirm overwrite non-interactively or choose "
                    "a non-destructive registration mode."
                ),
            ),
        )
    )


@mailbox_group.command(name="unregister")
@click.option(
    "--mode",
    type=click.Choice(("deactivate", "purge")),
    default="deactivate",
    show_default=True,
    help="Filesystem mailbox deregistration mode.",
)
@managed_agent_selector_options
def unregister_mailbox_command(
    mode: str,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Remove one filesystem mailbox binding from an existing local managed agent."""

    target = resolve_managed_agent_target(agent_id=agent_id, agent_name=agent_name, port=None)
    emit(unregister_mailbox_binding(target, mode=mode))
