"""Local filesystem mailbox administration commands for `houmao-mgr`."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable

import click

from houmao.owned_paths import HOUMAO_GLOBAL_MAILBOX_DIR_ENV_VAR
from houmao.project.overlay import (
    ensure_project_aware_local_roots,
    resolve_project_aware_mailbox_root,
)

from .cleanup_support import emit_cleanup_payload
from .common import (
    build_destructive_confirmation_callback,
    confirm_destructive_action,
    overwrite_confirm_option,
)
from .mailbox_support import (
    MAILBOX_ROOT_FAILURE_TYPES,
    clear_mailbox_messages_at_root,
    cleanup_mailbox_root,
    export_mailbox_root,
    format_mailbox_root_failure,
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
from .output import emit
from .project_aware_wording import (
    describe_mailbox_root_selection,
    mailbox_root_option_help,
)


def _call_mailbox_action(
    mailbox_root: Path | None,
    action: Callable[..., dict[str, object]],
    /,
    **kwargs: object,
) -> dict[str, object]:
    """Run one mailbox action and normalize expected root-state failures."""

    try:
        return action(mailbox_root=_resolve_effective_mailbox_root(mailbox_root), **kwargs)
    except MAILBOX_ROOT_FAILURE_TYPES as exc:
        raise click.ClickException(
            format_mailbox_root_failure(exc, init_command="houmao-mgr mailbox init")
        ) from exc


def _resolve_effective_mailbox_root(mailbox_root: Path | None) -> Path:
    """Resolve one mailbox root using the project-aware maintained-command contract."""

    cwd = Path.cwd().resolve()
    if mailbox_root is None and not os.environ.get(HOUMAO_GLOBAL_MAILBOX_DIR_ENV_VAR):
        ensure_project_aware_local_roots(cwd=cwd)
    return resolve_project_aware_mailbox_root(cwd=cwd, explicit_root=mailbox_root)


def _mailbox_root_option(function: Callable[..., Any]) -> Callable[..., Any]:
    """Attach the shared filesystem mailbox root option."""

    return click.option(
        "--mailbox-root",
        type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
        default=None,
        help=mailbox_root_option_help(),
    )(function)


def _emit_mailbox_payload(*, mailbox_root: Path | None, payload: dict[str, object]) -> None:
    """Emit one mailbox payload with project-aware root selection detail."""

    emit(
        {
            **payload,
            "mailbox_root_detail": describe_mailbox_root_selection(explicit_root=mailbox_root),
        }
    )


@click.group(name="mailbox")
def mailbox_group() -> None:
    """Local filesystem mailbox administration without `houmao-server`."""


@mailbox_group.command(name="init")
@_mailbox_root_option
def init_mailbox_command(mailbox_root: Path | None) -> None:
    """Bootstrap or validate one filesystem mailbox root."""

    _emit_mailbox_payload(
        mailbox_root=mailbox_root,
        payload=_call_mailbox_action(mailbox_root, init_mailbox_root),
    )


@mailbox_group.command(name="status")
@_mailbox_root_option
def status_mailbox_command(mailbox_root: Path | None) -> None:
    """Inspect one filesystem mailbox root and return a structured summary."""

    _emit_mailbox_payload(
        mailbox_root=mailbox_root,
        payload=_call_mailbox_action(mailbox_root, mailbox_root_status_payload),
    )


@mailbox_group.command(name="register")
@_mailbox_root_option
@click.option(
    "--address",
    required=True,
    help="Full mailbox address, for example `agent@houmao.localhost`.",
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

    _emit_mailbox_payload(
        mailbox_root=mailbox_root,
        payload=_call_mailbox_action(
            mailbox_root,
            register_mailbox_at_root,
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
        ),
    )


@mailbox_group.command(name="unregister")
@_mailbox_root_option
@click.option(
    "--address",
    required=True,
    help="Full mailbox address, for example `agent@houmao.localhost`.",
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

    _emit_mailbox_payload(
        mailbox_root=mailbox_root,
        payload=_call_mailbox_action(
            mailbox_root,
            unregister_mailbox_at_root,
            address=address,
            mode=mode,
        ),
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

    _emit_mailbox_payload(
        mailbox_root=mailbox_root,
        payload=_call_mailbox_action(
            mailbox_root,
            repair_mailbox_root,
            cleanup_staging=cleanup_staging,
            quarantine_staging=quarantine_staging,
        ),
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

    emit_cleanup_payload(
        {
            **_call_mailbox_action(
                mailbox_root,
                cleanup_mailbox_root,
                inactive_older_than_seconds=inactive_older_than_seconds,
                stashed_older_than_seconds=stashed_older_than_seconds,
                dry_run=dry_run,
            ),
            "mailbox_root_detail": describe_mailbox_root_selection(explicit_root=mailbox_root),
        }
    )


@mailbox_group.command(name="clear-messages")
@_mailbox_root_option
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview delivered-message clearing without deleting mail.",
)
@click.option(
    "--yes",
    is_flag=True,
    help="Confirm delivered-message clearing non-interactively.",
)
def clear_mailbox_messages_command(
    mailbox_root: Path | None,
    dry_run: bool,
    yes: bool,
) -> None:
    """Clear delivered messages while preserving mailbox registrations."""

    if not dry_run:
        confirm_destructive_action(
            prompt=(
                "Clear all delivered messages from the resolved filesystem mailbox root while "
                "preserving mailbox registrations?"
            ),
            yes=yes,
            non_interactive_message=(
                "Mailbox message clearing would delete delivered messages. Rerun with `--yes` "
                "to confirm non-interactively or use `--dry-run` to preview."
            ),
            cancelled_message="Mailbox message clearing cancelled.",
        )
    emit_cleanup_payload(
        {
            **_call_mailbox_action(
                mailbox_root,
                clear_mailbox_messages_at_root,
                dry_run=dry_run,
            ),
            "mailbox_root_detail": describe_mailbox_root_selection(explicit_root=mailbox_root),
        }
    )


@mailbox_group.command(name="export")
@_mailbox_root_option
@click.option(
    "--output-dir",
    required=True,
    type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
    help="New archive directory to create for the mailbox export.",
)
@click.option(
    "--all-accounts",
    is_flag=True,
    help="Export every registration row and every indexed canonical message.",
)
@click.option(
    "--address",
    "addresses",
    multiple=True,
    help="Full mailbox address to export; repeat for multiple selected accounts.",
)
@click.option(
    "--symlink-mode",
    type=click.Choice(("materialize", "preserve")),
    default="materialize",
    show_default=True,
    help="Materialize symlinks by default, or preserve archive-internal projection symlinks.",
)
def export_mailbox_command(
    mailbox_root: Path | None,
    output_dir: Path,
    all_accounts: bool,
    addresses: tuple[str, ...],
    symlink_mode: str,
) -> None:
    """Export selected mailbox state into a portable archive directory."""

    _emit_mailbox_payload(
        mailbox_root=mailbox_root,
        payload=_call_mailbox_action(
            mailbox_root,
            export_mailbox_root,
            output_dir=output_dir,
            all_accounts=all_accounts,
            addresses=addresses,
            symlink_mode=symlink_mode,
        ),
    )


@mailbox_group.group(name="accounts")
def mailbox_accounts_group() -> None:
    """Inspect mailbox registrations under one resolved mailbox root."""


@mailbox_accounts_group.command(name="list")
@_mailbox_root_option
def list_mailbox_accounts_command(mailbox_root: Path | None) -> None:
    """List mailbox registrations as operator-facing accounts."""

    _emit_mailbox_payload(
        mailbox_root=mailbox_root,
        payload=_call_mailbox_action(mailbox_root, list_mailbox_accounts),
    )


@mailbox_accounts_group.command(name="get")
@_mailbox_root_option
@click.option("--address", required=True, help="Full mailbox address.")
def get_mailbox_account_command(mailbox_root: Path | None, address: str) -> None:
    """Inspect one mailbox registration as an operator-facing account."""

    payload = _call_mailbox_action(
        mailbox_root,
        get_mailbox_account,
        address=address,
    )
    _emit_mailbox_payload(mailbox_root=mailbox_root, payload=payload)


@mailbox_group.group(name="messages")
def mailbox_messages_group() -> None:
    """Inspect structural message projections under one resolved mailbox root."""


@mailbox_messages_group.command(name="list")
@_mailbox_root_option
@click.option("--address", required=True, help="Full mailbox address.")
def list_mailbox_messages_command(mailbox_root: Path | None, address: str) -> None:
    """List structurally projected messages for one selected address."""

    payload = _call_mailbox_action(
        mailbox_root,
        list_mailbox_messages,
        address=address,
    )
    _emit_mailbox_payload(mailbox_root=mailbox_root, payload=payload)


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

    payload = _call_mailbox_action(
        mailbox_root,
        get_mailbox_message,
        address=address,
        message_id=message_id,
    )
    _emit_mailbox_payload(mailbox_root=mailbox_root, payload=payload)
