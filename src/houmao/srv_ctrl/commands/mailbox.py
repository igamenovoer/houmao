"""Local filesystem mailbox administration commands for `houmao-mgr`."""

from __future__ import annotations

from pathlib import Path
import sqlite3
from typing import Any, Callable, Literal, cast

import click
from houmao.mailbox import (
    MailboxBootstrapError,
    bootstrap_filesystem_mailbox,
    read_protocol_version,
)
from houmao.mailbox.filesystem import (
    resolve_filesystem_mailbox_paths,
    unsupported_mailbox_root_reason,
)
from houmao.mailbox.managed import (
    DeregisterMailboxRequest,
    MailboxCleanupRecord,
    MailboxCleanupResult,
    RegisterMailboxRequest,
    RepairRequest,
    cleanup_mailbox_registrations,
    deregister_mailbox,
    register_mailbox,
    repair_mailbox_index,
)
from houmao.owned_paths import resolve_mailbox_root

from .cleanup_support import CleanupAction, build_cleanup_payload
from .common import emit_json


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

    resolved_root = resolve_mailbox_root(explicit_root=mailbox_root)
    paths = bootstrap_filesystem_mailbox(resolved_root)
    emit_json(
        {
            "schema_version": 1,
            "mailbox_root": str(paths.root),
            "bootstrapped": True,
            "supported": True,
            "protocol_version": read_protocol_version(paths.protocol_version_file),
            "sqlite_path": str(paths.sqlite_path),
            "rules_dir": str(paths.rules_dir),
            "mailboxes_dir": str(paths.mailboxes_dir),
            "status": "ready",
        }
    )


@mailbox_group.command(name="status")
@_mailbox_root_option
def status_mailbox_command(mailbox_root: Path | None) -> None:
    """Inspect one filesystem mailbox root and return a structured summary."""

    resolved_root = resolve_mailbox_root(explicit_root=mailbox_root)
    emit_json(_mailbox_root_status_payload(resolved_root))


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
def register_mailbox_command(
    mailbox_root: Path | None,
    address: str,
    principal_id: str,
    mode: str,
) -> None:
    """Register one filesystem mailbox address under the resolved root."""

    resolved_root = resolve_mailbox_root(explicit_root=mailbox_root)
    bootstrap_filesystem_mailbox(resolved_root)
    paths = resolve_filesystem_mailbox_paths(resolved_root)
    result = register_mailbox(
        resolved_root,
        RegisterMailboxRequest(
            mode=cast(Literal["safe", "force", "stash"], mode),
            address=address,
            owner_principal_id=principal_id,
            mailbox_kind="in_root",
            mailbox_path=paths.mailbox_entry_path(address),
        ),
    )
    emit_json(
        {
            "schema_version": 1,
            "mailbox_root": str(resolved_root),
            **result,
        }
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

    resolved_root = resolve_mailbox_root(explicit_root=mailbox_root)
    result = deregister_mailbox(
        resolved_root,
        DeregisterMailboxRequest(
            mode=cast(Literal["deactivate", "purge"], mode),
            address=address,
        ),
    )
    emit_json(
        {
            "schema_version": 1,
            "mailbox_root": str(resolved_root),
            **result,
        }
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

    resolved_root = resolve_mailbox_root(explicit_root=mailbox_root)
    result = repair_mailbox_index(
        resolved_root,
        RepairRequest(
            cleanup_staging=cleanup_staging,
            quarantine_staging=quarantine_staging,
        ),
    )
    emit_json(
        {
            "schema_version": 1,
            "mailbox_root": str(resolved_root),
            **result,
        }
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

    resolved_root = resolve_mailbox_root(explicit_root=mailbox_root)
    result = cleanup_mailbox_registrations(
        resolved_root,
        inactive_older_than_seconds=inactive_older_than_seconds,
        stashed_older_than_seconds=stashed_older_than_seconds,
        dry_run=dry_run,
    )
    emit_json(
        _mailbox_cleanup_payload(
            result=result,
            inactive_older_than_seconds=inactive_older_than_seconds,
            stashed_older_than_seconds=stashed_older_than_seconds,
        )
    )


def _mailbox_root_status_payload(mailbox_root: Path) -> dict[str, object]:
    """Return a structured filesystem mailbox root status payload."""

    paths = resolve_filesystem_mailbox_paths(mailbox_root)
    counts = {"active": 0, "inactive": 0, "stashed": 0}
    supported = True
    structural_state_readable = False
    protocol_version: int | None = None
    error: str | None = None

    unsupported_reason = unsupported_mailbox_root_reason(paths.root)
    if unsupported_reason is not None:
        supported = False
        error = unsupported_reason
    elif paths.protocol_version_file.is_file():
        try:
            protocol_version = read_protocol_version(paths.protocol_version_file)
        except MailboxBootstrapError as exc:
            supported = False
            error = str(exc)

    if supported and paths.sqlite_path.is_file():
        try:
            with sqlite3.connect(paths.sqlite_path) as connection:
                for status, count in connection.execute(
                    """
                    SELECT status, COUNT(*)
                    FROM mailbox_registrations
                    GROUP BY status
                    """
                ).fetchall():
                    if status in counts:
                        counts[str(status)] = int(count)
                structural_state_readable = True
        except sqlite3.DatabaseError as exc:
            error = f"mailbox index is unreadable: {exc}"

    return {
        "schema_version": 1,
        "mailbox_root": str(paths.root),
        "exists": paths.root.exists(),
        "bootstrapped": supported
        and paths.protocol_version_file.is_file()
        and paths.sqlite_path.is_file(),
        "supported": supported,
        "protocol_version": protocol_version,
        "registration_counts": counts,
        "structural_state_readable": structural_state_readable,
        "error": error,
    }


def _mailbox_cleanup_payload(
    *,
    result: MailboxCleanupResult,
    inactive_older_than_seconds: int,
    stashed_older_than_seconds: int,
) -> dict[str, object]:
    """Return the structured CLI payload for mailbox cleanup."""

    planned_actions: list[CleanupAction] = []
    applied_actions: list[CleanupAction] = []
    blocked_actions: list[CleanupAction] = []
    preserved_actions: list[CleanupAction] = []

    for record in result.planned:
        planned_actions.append(_cleanup_action_from_mailbox_record(record))
    for record in result.removed:
        applied_actions.append(_cleanup_action_from_mailbox_record(record))
    for record in result.blocked:
        blocked_actions.append(_cleanup_action_from_mailbox_record(record))
    for record in result.preserved:
        preserved_actions.append(_cleanup_action_from_mailbox_record(record))

    return build_cleanup_payload(
        dry_run=result.dry_run,
        scope={
            "kind": "mailbox_cleanup",
            "mailbox_root": str(result.mailbox_root),
            "inactive_older_than_seconds": inactive_older_than_seconds,
            "stashed_older_than_seconds": stashed_older_than_seconds,
        },
        resolution={"authority": "mailbox_root"},
        planned_actions=planned_actions,
        applied_actions=applied_actions,
        blocked_actions=blocked_actions,
        preserved_actions=preserved_actions,
    )


def _cleanup_action_from_mailbox_record(record: MailboxCleanupRecord) -> CleanupAction:
    """Translate one mailbox cleanup record into the shared cleanup payload shape."""

    details: dict[str, object] = {}
    if record.address is not None:
        details["address"] = record.address
    if record.registration_id is not None:
        details["registration_id"] = record.registration_id
    if record.registration_status is not None:
        details["registration_status"] = record.registration_status
    return CleanupAction(
        artifact_kind=record.artifact_kind,
        path=record.path,
        proposed_action="remove" if record.outcome != "preserved" else "preserve",
        reason=record.reason,
        details=details,
    )
