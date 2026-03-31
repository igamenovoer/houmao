"""Local filesystem mailbox administration commands for `houmao-mgr`."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import click

from houmao.owned_paths import resolve_mailbox_root

from .common import build_destructive_confirmation_callback, emit_json, overwrite_confirm_option
from .mailbox_support import (
    cleanup_mailbox_root,
    get_mailbox_account,
    get_mailbox_message,
    init_mailbox_root,
    list_mailbox_accounts,
    list_mailbox_messages,
    mailbox_root_status_payload,
    register_mailbox_at_root,
    repair_mailbox_root,
    unregister_mailbox_at_root,
)


def _mailbox_root_option(function: Callable[..., Any]) -> Callable[..., Any]:
    """Attach the shared filesystem mailbox root option."""

    return click.option(
        "--mailbox-root",
        type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
        default=None,
        help=(
            "Filesystem mailbox root override. Defaults to `AGENTSYS_GLOBAL_MAILBOX_DIR` "
            "or the shared Houmao mailbox root."
        ),
    )(function)


@click.group(name="mailbox")
def mailbox_group() -> None:
    """Local filesystem mailbox administration without `houmao-server`."""


@mailbox_group.command(name="init")
@_mailbox_root_option
def init_mailbox_command(mailbox_root: Path | None) -> None:
    """Bootstrap or validate one filesystem mailbox root."""

    emit_json(init_mailbox_root(resolve_mailbox_root(explicit_root=mailbox_root)))


@mailbox_group.command(name="status")
@_mailbox_root_option
def status_mailbox_command(mailbox_root: Path | None) -> None:
    """Inspect one filesystem mailbox root and return a structured summary."""

    emit_json(mailbox_root_status_payload(resolve_mailbox_root(explicit_root=mailbox_root)))


@mailbox_group.command(name="register")
@_mailbox_root_option
@click.option(
    "--address",
    required=True,
    help="Full mailbox address, for example `AGENTSYS-agent@agents.localhost`.",
)
@click.option("--principal-id", required=True, help="Mailbox owner principal id.")
@click.option(
    "--mode",
    type=click.Choice(("safe", "force", "stash")),
    default="safe",
    show_default=True,
    help="Filesystem mailbox registration mode.",
)
@overwrite_confirm_option
def register_mailbox_command(
    mailbox_root: Path | None,
    address: str,
    principal_id: str,
    mode: str,
    yes: bool,
) -> None:
    """Register one filesystem mailbox address under the resolved root."""

    emit_json(
        register_mailbox_at_root(
            mailbox_root=resolve_mailbox_root(explicit_root=mailbox_root),
            address=address,
            principal_id=principal_id,
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
@_mailbox_root_option
@click.option(
    "--address",
    required=True,
    help="Full mailbox address, for example `AGENTSYS-agent@agents.localhost`.",
)
@click.option(
    "--mode",
    type=click.Choice(("deactivate", "purge")),
    default="deactivate",
    show_default=True,
    help="Filesystem mailbox deregistration mode.",
)
def unregister_mailbox_command(mailbox_root: Path | None, address: str, mode: str) -> None:
    """Deactivate or purge one filesystem mailbox address."""

    emit_json(
        unregister_mailbox_at_root(
            mailbox_root=resolve_mailbox_root(explicit_root=mailbox_root),
            address=address,
            mode=mode,
        )
    )


@mailbox_group.command(name="repair")
@_mailbox_root_option
@click.option(
    "--cleanup-staging/--no-cleanup-staging",
    default=True,
    show_default=True,
    help="Clean staging artifacts during repair.",
)
@click.option(
    "--quarantine-staging/--remove-staging",
    default=True,
    show_default=True,
    help="Quarantine staging artifacts instead of deleting them.",
)
def repair_mailbox_command(
    mailbox_root: Path | None,
    cleanup_staging: bool,
    quarantine_staging: bool,
) -> None:
    """Rebuild filesystem mailbox index state locally."""

    emit_json(
        repair_mailbox_root(
            mailbox_root=resolve_mailbox_root(explicit_root=mailbox_root),
            cleanup_staging=cleanup_staging,
            quarantine_staging=quarantine_staging,
        )
    )


@mailbox_group.command(name="cleanup")
@_mailbox_root_option
@click.option(
    "--inactive-older-than-seconds",
    default=0,
    show_default=True,
    type=click.IntRange(min=0),
    help="Only clean inactive registrations older than this threshold.",
)
@click.option(
    "--stashed-older-than-seconds",
    default=0,
    show_default=True,
    type=click.IntRange(min=0),
    help="Only clean stashed registrations older than this threshold.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview inactive or stashed mailbox cleanup candidates without deleting them.",
)
def cleanup_mailbox_command(
    mailbox_root: Path | None,
    inactive_older_than_seconds: int,
    stashed_older_than_seconds: int,
    dry_run: bool,
) -> None:
    """Clean inactive or stashed mailbox registrations without deleting canonical mail."""

    emit_json(
        cleanup_mailbox_root(
            mailbox_root=resolve_mailbox_root(explicit_root=mailbox_root),
            inactive_older_than_seconds=inactive_older_than_seconds,
            stashed_older_than_seconds=stashed_older_than_seconds,
            dry_run=dry_run,
        )
    )


@mailbox_group.group(name="accounts")
def mailbox_accounts_group() -> None:
    """Inspect mailbox registrations under one resolved mailbox root."""


@mailbox_accounts_group.command(name="list")
@_mailbox_root_option
def list_mailbox_accounts_command(mailbox_root: Path | None) -> None:
    """List mailbox registrations as operator-facing accounts."""

    emit_json(list_mailbox_accounts(mailbox_root=resolve_mailbox_root(explicit_root=mailbox_root)))


@mailbox_accounts_group.command(name="get")
@_mailbox_root_option
@click.option("--address", required=True, help="Full mailbox address.")
def get_mailbox_account_command(mailbox_root: Path | None, address: str) -> None:
    """Inspect one mailbox registration as an operator-facing account."""

    try:
        payload = get_mailbox_account(
            mailbox_root=resolve_mailbox_root(explicit_root=mailbox_root),
            address=address,
        )
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc
    emit_json(payload)


@mailbox_group.group(name="messages")
def mailbox_messages_group() -> None:
    """Inspect structural message projections under one resolved mailbox root."""


@mailbox_messages_group.command(name="list")
@_mailbox_root_option
@click.option("--address", required=True, help="Full mailbox address.")
def list_mailbox_messages_command(mailbox_root: Path | None, address: str) -> None:
    """List structurally projected messages for one selected address."""

    try:
        payload = list_mailbox_messages(
            mailbox_root=resolve_mailbox_root(explicit_root=mailbox_root),
            address=address,
        )
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc
    emit_json(payload)


@mailbox_messages_group.command(name="get")
@_mailbox_root_option
@click.option("--address", required=True, help="Full mailbox address.")
@click.option("--message-id", required=True, help="Canonical mailbox message id.")
def get_mailbox_message_command(
    mailbox_root: Path | None,
    address: str,
    message_id: str,
) -> None:
    """Get one structurally projected message for a selected address."""

    try:
        payload = get_mailbox_message(
            mailbox_root=resolve_mailbox_root(explicit_root=mailbox_root),
            address=address,
            message_id=message_id,
        )
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc
    emit_json(payload)
