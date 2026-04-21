"""Shared mailbox CLI payload helpers."""

from __future__ import annotations

from collections.abc import Callable
import json
from pathlib import Path
import sqlite3
from typing import Literal, cast

import click

from houmao.mailbox import (
    MailboxBootstrapError,
    bootstrap_filesystem_mailbox,
    read_protocol_version,
)
from houmao.mailbox.filesystem import (
    MailboxRegistration,
    resolve_filesystem_mailbox_paths,
    unsupported_mailbox_root_reason,
)
from houmao.mailbox.managed import (
    DeregisterMailboxRequest,
    MailboxCleanupRecord,
    MailboxCleanupResult,
    MailboxExportRequest,
    MailboxExportResult,
    MailboxMessageClearResult,
    ManagedMailboxOperationError,
    RegisterMailboxRequest,
    RepairRequest,
    clear_mailbox_messages,
    cleanup_mailbox_registrations,
    deregister_mailbox,
    export_mailbox_archive,
    register_mailbox,
    repair_mailbox_index,
)

from .cleanup_support import CleanupAction, build_cleanup_payload

MAILBOX_ROOT_FAILURE_TYPES = (
    FileNotFoundError,
    MailboxBootstrapError,
    ManagedMailboxOperationError,
    ValueError,
    sqlite3.DatabaseError,
)


def format_mailbox_root_failure(
    exc: Exception,
    *,
    init_command: str = "houmao-mgr mailbox init",
) -> str:
    """Render one mailbox-root failure as operator-facing CLI text."""

    if isinstance(exc, sqlite3.DatabaseError):
        detail = f"mailbox index is unreadable: {exc}"
    else:
        detail = str(exc).strip() or exc.__class__.__name__

    if (
        "Run `houmao-mgr mailbox init` first." in detail
        and init_command != "houmao-mgr mailbox init"
    ):
        return detail.replace(
            "Run `houmao-mgr mailbox init` first.",
            f"Run `{init_command}` first.",
        )

    bootstrap_markers = (
        "missing protocol version file:",
        "missing mailbox index:",
        "Mailbox index is missing under `",
        "unsupported mailbox protocol version:",
    )
    if any(marker in detail for marker in bootstrap_markers):
        if "Run `" not in detail:
            separator = " " if detail.endswith((".", "!", "?")) else ". "
            return f"{detail}{separator}Run `{init_command}` first."

    return detail


def init_mailbox_root(mailbox_root: Path) -> dict[str, object]:
    """Bootstrap or validate one filesystem mailbox root."""

    paths = bootstrap_filesystem_mailbox(mailbox_root.resolve())
    return {
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


def mailbox_root_status_payload(mailbox_root: Path) -> dict[str, object]:
    """Return a structured filesystem mailbox root status payload."""

    paths = resolve_filesystem_mailbox_paths(mailbox_root.resolve())
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


def register_mailbox_at_root(
    *,
    mailbox_root: Path,
    address: str,
    principal_id: str,
    mode: str,
    confirm_destructive_replace: Callable[[str], bool] | None = None,
) -> dict[str, object]:
    """Register one filesystem mailbox address under the selected root."""

    resolved_root = mailbox_root.resolve()
    try:
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
            confirm_destructive_replace=confirm_destructive_replace,
        )
    except (MailboxBootstrapError, ManagedMailboxOperationError) as exc:
        raise click.ClickException(str(exc)) from exc
    return {
        "schema_version": 1,
        "mailbox_root": str(resolved_root),
        **result,
    }


def unregister_mailbox_at_root(
    *,
    mailbox_root: Path,
    address: str,
    mode: str,
) -> dict[str, object]:
    """Deactivate or purge one filesystem mailbox address."""

    resolved_root = mailbox_root.resolve()
    result = deregister_mailbox(
        resolved_root,
        DeregisterMailboxRequest(
            mode=cast(Literal["deactivate", "purge"], mode),
            address=address,
        ),
    )
    return {
        "schema_version": 1,
        "mailbox_root": str(resolved_root),
        **result,
    }


def repair_mailbox_root(
    *,
    mailbox_root: Path,
    cleanup_staging: bool,
    quarantine_staging: bool,
) -> dict[str, object]:
    """Rebuild filesystem mailbox index state locally."""

    resolved_root = mailbox_root.resolve()
    result = repair_mailbox_index(
        resolved_root,
        RepairRequest(
            cleanup_staging=cleanup_staging,
            quarantine_staging=quarantine_staging,
        ),
    )
    return {
        "schema_version": 1,
        "mailbox_root": str(resolved_root),
        **result,
    }


def cleanup_mailbox_root(
    *,
    mailbox_root: Path,
    inactive_older_than_seconds: int,
    stashed_older_than_seconds: int,
    dry_run: bool,
) -> dict[str, object]:
    """Clean inactive or stashed mailbox registrations without deleting mail."""

    result = cleanup_mailbox_registrations(
        mailbox_root.resolve(),
        inactive_older_than_seconds=inactive_older_than_seconds,
        stashed_older_than_seconds=stashed_older_than_seconds,
        dry_run=dry_run,
    )
    return _mailbox_cleanup_payload(
        result=result,
        inactive_older_than_seconds=inactive_older_than_seconds,
        stashed_older_than_seconds=stashed_older_than_seconds,
    )


def clear_mailbox_messages_at_root(
    *,
    mailbox_root: Path,
    dry_run: bool,
) -> dict[str, object]:
    """Clear delivered messages from one mailbox root without deleting accounts."""

    result = clear_mailbox_messages(
        mailbox_root.resolve(),
        dry_run=dry_run,
    )
    return _mailbox_message_clear_payload(result=result)


def export_mailbox_root(
    *,
    mailbox_root: Path,
    output_dir: Path,
    all_accounts: bool,
    addresses: tuple[str, ...],
    symlink_mode: str,
) -> dict[str, object]:
    """Export selected mailbox state from one root into an archive directory."""

    if all_accounts and addresses:
        raise click.ClickException(
            "Choose either `--all-accounts` or one or more `--address` values, not both."
        )
    if not all_accounts and not addresses:
        raise click.ClickException(
            "Choose `--all-accounts` or one or more `--address` values for mailbox export."
        )
    try:
        request = MailboxExportRequest.from_payload(
            {
                "output_dir": str(output_dir),
                "all_accounts": all_accounts,
                "addresses": list(addresses),
                "symlink_mode": symlink_mode,
            }
        )
        result = export_mailbox_archive(mailbox_root.resolve(), request)
    except ManagedMailboxOperationError as exc:
        raise click.ClickException(str(exc)) from exc
    return _mailbox_export_payload(result=result)


def list_mailbox_accounts(*, mailbox_root: Path) -> dict[str, object]:
    """Return all mailbox registrations as operator-facing accounts."""

    resolved_root = mailbox_root.resolve()
    with _connect_index(resolved_root) as connection:
        rows = connection.execute(
            """
            SELECT
                registration_id,
                address,
                owner_principal_id,
                status,
                mailbox_kind,
                mailbox_path,
                mailbox_entry_path,
                display_name,
                manifest_path_hint,
                role,
                created_at_utc,
                deactivated_at_utc,
                replaced_by_registration_id
            FROM mailbox_registrations
            ORDER BY address ASC, created_at_utc DESC, registration_id DESC
            """
        ).fetchall()
    accounts = [_registration_payload(_row_to_registration(row)) for row in rows]
    return {
        "schema_version": 1,
        "mailbox_root": str(resolved_root),
        "accounts": accounts,
    }


def get_mailbox_account(*, mailbox_root: Path, address: str) -> dict[str, object]:
    """Return the selected mailbox registration summary for one address."""

    resolved_root = mailbox_root.resolve()
    with _connect_index(resolved_root) as connection:
        row = connection.execute(
            """
            SELECT
                registration_id,
                address,
                owner_principal_id,
                status,
                mailbox_kind,
                mailbox_path,
                mailbox_entry_path,
                display_name,
                manifest_path_hint,
                role,
                created_at_utc,
                deactivated_at_utc,
                replaced_by_registration_id
            FROM mailbox_registrations
            WHERE address = ?
            ORDER BY
                CASE status
                    WHEN 'active' THEN 0
                    WHEN 'stashed' THEN 1
                    ELSE 2
                END,
                created_at_utc DESC,
                registration_id DESC
            LIMIT 1
            """,
            (address,),
        ).fetchone()
    if row is None:
        raise FileNotFoundError(
            f"Mailbox account `{address}` was not found under `{resolved_root}`."
        )
    return {
        "schema_version": 1,
        "mailbox_root": str(resolved_root),
        "account": _registration_payload(_row_to_registration(row)),
    }


def list_mailbox_messages(*, mailbox_root: Path, address: str) -> dict[str, object]:
    """Return structural message summaries for one registered mailbox address."""

    resolved_root = mailbox_root.resolve()
    with _connect_index(resolved_root) as connection:
        registration = _require_active_registration(connection=connection, address=address)
        rows = connection.execute(
            """
            SELECT
                projection.message_id,
                message.thread_id,
                message.created_at_utc,
                message.subject,
                message.sender_address,
                message.sender_principal_id,
                projection.folder_name,
                projection.projection_path,
                message.canonical_path
            FROM mailbox_projections AS projection
            JOIN messages AS message ON message.message_id = projection.message_id
            WHERE projection.registration_id = ?
            ORDER BY message.created_at_utc DESC, projection.message_id DESC
            """,
            (registration.registration_id,),
        ).fetchall()
    messages = [
        {
            "message_id": str(row[0]),
            "thread_id": str(row[1]),
            "created_at_utc": str(row[2]),
            "subject": str(row[3]),
            "sender_address": str(row[4]),
            "sender_principal_id": str(row[5]),
            "folder": str(row[6]),
            "projection_path": str(row[7]),
            "canonical_path": str(row[8]),
        }
        for row in rows
    ]
    return {
        "schema_version": 1,
        "mailbox_root": str(resolved_root),
        "address": registration.address,
        "registration_id": registration.registration_id,
        "messages": messages,
    }


def get_mailbox_message(
    *,
    mailbox_root: Path,
    address: str,
    message_id: str,
) -> dict[str, object]:
    """Return one structurally projected message plus its metadata for one address."""

    resolved_root = mailbox_root.resolve()
    with _connect_index(resolved_root) as connection:
        registration = _require_active_registration(connection=connection, address=address)
        row = connection.execute(
            """
            SELECT
                projection.message_id,
                projection.folder_name,
                projection.projection_path,
                message.thread_id,
                message.in_reply_to,
                message.created_at_utc,
                message.subject,
                message.body_markdown,
                message.headers_json,
                message.canonical_path,
                message.sender_address,
                message.sender_principal_id,
                message.sender_display_name,
                message.sender_manifest_path_hint,
                message.sender_role
            FROM mailbox_projections AS projection
            JOIN messages AS message ON message.message_id = projection.message_id
            WHERE projection.registration_id = ? AND projection.message_id = ?
            LIMIT 1
            """,
            (registration.registration_id, message_id),
        ).fetchone()
        if row is None:
            raise FileNotFoundError(
                f"Message `{message_id}` is not visible to `{address}` under `{resolved_root}`."
            )
        recipients = connection.execute(
            """
            SELECT recipient_kind, ordinal, address, owner_principal_id, display_name, manifest_path_hint, role
            FROM message_recipients
            WHERE message_id = ?
            ORDER BY recipient_kind ASC, ordinal ASC
            """,
            (message_id,),
        ).fetchall()
        attachments = connection.execute(
            """
            SELECT
                attachment.attachment_id,
                attachment.kind,
                attachment.locator,
                attachment.media_type,
                attachment.sha256,
                attachment.size_bytes,
                attachment.label,
                binding.ordinal
            FROM message_attachments AS binding
            JOIN attachments AS attachment ON attachment.attachment_id = binding.attachment_id
            WHERE binding.message_id = ?
            ORDER BY binding.ordinal ASC, attachment.attachment_id ASC
            """,
            (message_id,),
        ).fetchall()
    return {
        "schema_version": 1,
        "mailbox_root": str(resolved_root),
        "address": registration.address,
        "registration_id": registration.registration_id,
        "message": {
            "message_id": str(row[0]),
            "folder": str(row[1]),
            "projection_path": str(row[2]),
            "thread_id": str(row[3]),
            "in_reply_to": None if row[4] is None else str(row[4]),
            "created_at_utc": str(row[5]),
            "subject": str(row[6]),
            "body_markdown": str(row[7]),
            "headers": _load_json_object(raw_value=row[8]),
            "canonical_path": str(row[9]),
            "sender": {
                "address": str(row[10]),
                "owner_principal_id": str(row[11]),
                "display_name": None if row[12] is None else str(row[12]),
                "manifest_path_hint": None if row[13] is None else str(row[13]),
                "role": None if row[14] is None else str(row[14]),
            },
            "recipients": [
                {
                    "kind": str(recipient_row[0]),
                    "ordinal": int(recipient_row[1]),
                    "address": str(recipient_row[2]),
                    "owner_principal_id": str(recipient_row[3]),
                    "display_name": None if recipient_row[4] is None else str(recipient_row[4]),
                    "manifest_path_hint": None
                    if recipient_row[5] is None
                    else str(recipient_row[5]),
                    "role": None if recipient_row[6] is None else str(recipient_row[6]),
                }
                for recipient_row in recipients
            ],
            "attachments": [
                {
                    "attachment_id": str(attachment_row[0]),
                    "kind": str(attachment_row[1]),
                    "locator": str(attachment_row[2]),
                    "media_type": str(attachment_row[3]),
                    "sha256": None if attachment_row[4] is None else str(attachment_row[4]),
                    "size_bytes": None if attachment_row[5] is None else int(attachment_row[5]),
                    "label": None if attachment_row[6] is None else str(attachment_row[6]),
                    "ordinal": int(attachment_row[7]),
                }
                for attachment_row in attachments
            ],
        },
    }


def _connect_index(mailbox_root: Path) -> sqlite3.Connection:
    """Open one mailbox index after validating the root layout."""

    resolved_root = mailbox_root.resolve()
    paths = resolve_filesystem_mailbox_paths(resolved_root)
    reason = unsupported_mailbox_root_reason(paths.root)
    if reason is not None:
        raise ValueError(reason)
    if not paths.sqlite_path.is_file():
        raise FileNotFoundError(
            f"Mailbox index is missing under `{resolved_root}`. Run `houmao-mgr mailbox init` first."
        )
    connection = sqlite3.connect(paths.sqlite_path)
    connection.row_factory = sqlite3.Row
    return connection


def _require_active_registration(
    *,
    connection: sqlite3.Connection,
    address: str,
) -> MailboxRegistration:
    """Return the active mailbox registration for one address or raise."""

    row = connection.execute(
        """
        SELECT
            registration_id,
            address,
            owner_principal_id,
            status,
            mailbox_kind,
            mailbox_path,
            mailbox_entry_path,
            display_name,
            manifest_path_hint,
            role,
            created_at_utc,
            deactivated_at_utc,
            replaced_by_registration_id
        FROM mailbox_registrations
        WHERE address = ? AND status = 'active'
        LIMIT 1
        """,
        (address,),
    ).fetchone()
    if row is None:
        raise FileNotFoundError(f"No active mailbox registration exists for `{address}`.")
    return _row_to_registration(row)


def _row_to_registration(row: sqlite3.Row | tuple[object, ...]) -> MailboxRegistration:
    """Convert one SQLite row into a registration model."""

    values = tuple(row) if isinstance(row, sqlite3.Row) else row
    return MailboxRegistration(
        registration_id=str(values[0]),
        address=str(values[1]),
        owner_principal_id=str(values[2]),
        status=str(values[3]),
        mailbox_kind=str(values[4]),
        mailbox_path=Path(str(values[5])),
        mailbox_entry_path=Path(str(values[6])),
        display_name=None if values[7] is None else str(values[7]),
        manifest_path_hint=None if values[8] is None else str(values[8]),
        role=None if values[9] is None else str(values[9]),
        created_at_utc=str(values[10]),
        deactivated_at_utc=None if values[11] is None else str(values[11]),
        replaced_by_registration_id=None if values[12] is None else str(values[12]),
    )


def _registration_payload(registration: MailboxRegistration) -> dict[str, object]:
    """Convert one registration model into CLI payload data."""

    return {
        "registration_id": registration.registration_id,
        "address": registration.address,
        "owner_principal_id": registration.owner_principal_id,
        "status": registration.status,
        "mailbox_kind": registration.mailbox_kind,
        "mailbox_path": str(registration.mailbox_path),
        "mailbox_entry_path": str(registration.mailbox_entry_path),
        "display_name": registration.display_name,
        "manifest_path_hint": registration.manifest_path_hint,
        "role": registration.role,
        "created_at_utc": registration.created_at_utc,
        "deactivated_at_utc": registration.deactivated_at_utc,
        "replaced_by_registration_id": registration.replaced_by_registration_id,
    }


def _load_json_object(*, raw_value: object) -> dict[str, object]:
    """Parse one JSON object field from the mailbox index."""

    if raw_value is None:
        return {}
    loaded = json.loads(str(raw_value))
    if not isinstance(loaded, dict):
        return {}
    return cast(dict[str, object], loaded)


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


def _mailbox_message_clear_payload(
    *,
    result: MailboxMessageClearResult,
) -> dict[str, object]:
    """Return the structured CLI payload for delivered-message clearing."""

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
            "kind": "mailbox_message_clear",
            "mailbox_root": str(result.mailbox_root),
        },
        resolution={"authority": "mailbox_root"},
        planned_actions=planned_actions,
        applied_actions=applied_actions,
        blocked_actions=blocked_actions,
        preserved_actions=preserved_actions,
    )


def _mailbox_export_payload(
    *,
    result: MailboxExportResult,
) -> dict[str, object]:
    """Return the structured CLI payload for mailbox archive export."""

    return {
        "schema_version": 1,
        "mailbox_root": str(result.mailbox_root),
        "output_dir": str(result.output_dir),
        "symlink_mode": result.symlink_mode,
        "all_accounts": result.all_accounts,
        "selected_addresses": list(result.selected_addresses),
        "account_count": result.account_count,
        "message_count": result.message_count,
        "attachment_count": result.attachment_count,
        "manifest_path": str(result.manifest_path),
        "copied_artifacts": [record.to_payload() for record in result.copied],
        "materialized_artifacts": [record.to_payload() for record in result.materialized],
        "preserved_symlinks": [record.to_payload() for record in result.preserved_symlinks],
        "skipped_artifacts": [record.to_payload() for record in result.skipped],
        "blocked_artifacts": [record.to_payload() for record in result.blocked],
    }


def _cleanup_action_from_mailbox_record(record: MailboxCleanupRecord) -> CleanupAction:
    """Translate one mailbox cleanup record into the shared cleanup payload shape."""

    details: dict[str, object] = {}
    if record.address is not None:
        details["address"] = record.address
    if record.registration_id is not None:
        details["registration_id"] = record.registration_id
    if record.registration_status is not None:
        details["registration_status"] = record.registration_status
    if record.message_id is not None:
        details["message_id"] = record.message_id
    if record.attachment_id is not None:
        details["attachment_id"] = record.attachment_id
    return CleanupAction(
        artifact_kind=record.artifact_kind,
        path=record.path,
        proposed_action="remove" if record.outcome != "preserved" else "preserve",
        reason=record.reason,
        details=details,
    )
