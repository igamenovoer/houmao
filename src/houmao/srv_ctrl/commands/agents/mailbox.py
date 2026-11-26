"""Offline registry membership commands for managed agents."""

from __future__ import annotations

from pathlib import Path

import click

from houmao.srv_ctrl.commands.common import managed_agent_selector_options
from houmao.srv_ctrl.commands.output import emit
from houmao.srv_ctrl.commands.project_aware_wording import mailbox_root_option_help
from houmao.srv_ctrl.commands.managed_agents import (
    mailbox_status,
    register_mailbox_binding,
    resolve_managed_agent_target,
    unregister_mailbox_binding,
)


@click.group(name="mailbox")
def mailbox_group() -> None:
    """Configure independent offline and online mail slots."""


@mailbox_group.group(name="offline")
def offline_mailbox_group() -> None:
    """Join or leave the selected registry without restarting the agent body."""


@offline_mailbox_group.command(name="status")
@managed_agent_selector_options
def status_mailbox_command(agent_id: str | None, agent_name: str | None) -> None:
    """Report the selected agent's offline membership."""

    target = resolve_managed_agent_target(agent_id=agent_id, agent_name=agent_name, port=None)
    emit(mailbox_status(target))


@offline_mailbox_group.command(name="join")
@click.option(
    "--mailbox-root",
    type=click.Path(path_type=Path, file_okay=False),
    default=None,
    help=mailbox_root_option_help(),
)
@click.option("--address", default=None, help="Requested offline address in the selected registry.")
@click.option(
    "--registry-url", default=None, help="Remote HTTPS or tunneled loopback registry URL."
)
@click.option(
    "--credential-file",
    type=click.Path(path_type=Path, dir_okay=False),
    default=None,
    help="Private local member credential; prepared before enrollment and reused on retry.",
)
@click.option(
    "--admin-credential-file",
    type=click.Path(path_type=Path, dir_okay=False, exists=True),
    default=None,
    help="Private local administrator credential authorizing remote enrollment.",
)
@managed_agent_selector_options
def register_mailbox_command(
    mailbox_root: Path | None,
    address: str | None,
    registry_url: str | None,
    credential_file: Path | None,
    admin_credential_file: Path | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Claim an offline address; occupied addresses fail without takeover."""

    target = resolve_managed_agent_target(agent_id=agent_id, agent_name=agent_name, port=None)
    emit(
        register_mailbox_binding(
            target,
            mailbox_root=mailbox_root,
            address=address,
            registry_url=registry_url,
            credential_file=credential_file,
            admin_credential_file=admin_credential_file,
        )
    )


@offline_mailbox_group.command(name="leave")
@click.option(
    "--mode",
    type=click.Choice(("deactivate", "purge")),
    default="deactivate",
    show_default=True,
    help="Explicit release retention policy.",
)
@managed_agent_selector_options
def unregister_mailbox_command(mode: str, agent_id: str | None, agent_name: str | None) -> None:
    """Release offline membership while preserving configured online mail."""

    target = resolve_managed_agent_target(agent_id=agent_id, agent_name=agent_name, port=None)
    emit(unregister_mailbox_binding(target, mode=mode))


@mailbox_group.group(name="online")
def online_mailbox_group() -> None:
    """Attach an existing online account through a live gateway companion."""


@online_mailbox_group.command(name="status")
@managed_agent_selector_options
def online_status_command(agent_id: str | None, agent_name: str | None) -> None:
    """Read safe configured online identity without probing provider credentials."""

    from houmao.srv_ctrl.commands.managed_agents import online_mailbox_status

    target = resolve_managed_agent_target(agent_id=agent_id, agent_name=agent_name, port=None)
    emit(online_mailbox_status(target))


@online_mailbox_group.command(name="attach")
@click.option("--provider", type=click.Choice(("stalwart",)), default="stalwart")
@click.option("--address", required=True, help="Authorized sending address, separate from login.")
@click.option(
    "--login-identity", required=True, help="Existing normal-account authentication login."
)
@click.option(
    "--credential-source",
    type=click.Path(path_type=Path, dir_okay=False),
    required=True,
    help="Owner-private password JSON on the agent host; contents are never CLI arguments.",
)
@click.option("--jmap-url", default=None, help="Exact JMAP session-discovery URL.")
@click.option("--base-url", default=None, help="Derive /.well-known/jmap from this server base.")
@click.option(
    "--trust-jmap-origin",
    multiple=True,
    metavar="ORIGIN",
    help="Approve an exact JMAP scheme, host, and port. HTTP permits plaintext credentials.",
)
@click.option(
    "--account-id", default=None, help="Explicit JMAP account when discovery is ambiguous."
)
@click.option(
    "--replace", is_flag=True, help="Authorize another account or endpoint with a fresh binding ID."
)
@click.option("--expected-revision", default=None, help="Pin an observed online slot revision.")
@click.option("--timeout-seconds", type=click.FloatRange(min=0.01, max=120), default=10.0)
@managed_agent_selector_options
def online_attach_command(
    provider: str,
    address: str,
    login_identity: str,
    credential_source: Path,
    jmap_url: str | None,
    base_url: str | None,
    trust_jmap_origin: tuple[str, ...],
    account_id: str | None,
    replace: bool,
    expected_revision: str | None,
    timeout_seconds: float,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Validate and attach an existing account without restarting the agent body."""

    from pydantic import ValidationError

    from houmao.mailbox.online_models import OnlineAttachRequest
    from houmao.srv_ctrl.commands.managed_agents import (
        control_online_mailbox,
        online_mailbox_status,
    )

    target = resolve_managed_agent_target(agent_id=agent_id, agent_name=agent_name, port=None)
    revision = expected_revision or online_mailbox_status(target).revision
    try:
        request = OnlineAttachRequest(
            provider=provider,  # type: ignore[arg-type]
            expected_revision=revision,
            address=address,
            login_identity=login_identity,
            credential_source_ref=str(credential_source),
            jmap_url=jmap_url,
            base_url=base_url,
            trusted_jmap_origins=list(trust_jmap_origin),
            account_id=account_id,
            replace=replace,
            timeout_seconds=timeout_seconds,
        )
    except ValidationError:
        raise click.ClickException(
            "Select exactly one valid --jmap-url or --base-url and all account options."
        ) from None
    emit(control_online_mailbox(target, "attach", request))


def _online_control_command(operation: str) -> click.Command:
    """Build identical revision-pinned controls with explicit credential refresh."""

    @click.command(name=operation)
    @click.option("--expected-revision", default=None, help="Pin an observed online slot revision.")
    @click.option(
        "--credential-source",
        type=click.Path(path_type=Path, dir_okay=False),
        default=None,
        help="Refresh only: owner-private password JSON on the agent host.",
    )
    @click.option("--timeout-seconds", type=click.FloatRange(min=0.01, max=120), default=10.0)
    @managed_agent_selector_options
    def command(
        expected_revision: str | None,
        credential_source: Path | None,
        timeout_seconds: float,
        agent_id: str | None,
        agent_name: str | None,
    ) -> None:
        """Change the online connection without restarting the agent body."""

        from houmao.mailbox.online_models import OnlineControlRequest
        from houmao.srv_ctrl.commands.managed_agents import (
            control_online_mailbox,
            online_mailbox_status,
        )

        if operation != "refresh" and credential_source is not None:
            raise click.ClickException("Only refresh accepts --credential-source.")
        target = resolve_managed_agent_target(agent_id=agent_id, agent_name=agent_name, port=None)
        revision = expected_revision or online_mailbox_status(target).revision
        request = OnlineControlRequest(
            expected_revision=revision,
            credential_source_ref=str(credential_source) if credential_source is not None else None,
            timeout_seconds=timeout_seconds,
        )
        emit(control_online_mailbox(target, operation, request))

    return command


for _operation in ("refresh", "reconnect", "detach"):
    online_mailbox_group.add_command(_online_control_command(_operation))
