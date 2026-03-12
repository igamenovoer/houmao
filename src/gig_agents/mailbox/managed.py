"""Helpers for managed mailbox scripts."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import time
from typing import Iterator, Sequence

from gig_agents.mailbox.filesystem import initialize_sqlite_schema
from gig_agents.mailbox.protocol import MailboxMessage, MailboxPrincipal, parse_message_document

MAILBOX_PROTOCOL_VERSION = 1
_MESSAGE_ID_PATTERN = re.compile(r"^msg-\d{8}T\d{6}Z-[0-9a-f]{32}$")
_MAILBOX_PLACEHOLDER_DIRS = ("inbox", "sent", "archive", "drafts")


class ManagedMailboxOperationError(RuntimeError):
    """Raised when a managed mailbox script cannot complete safely."""


@dataclass(frozen=True)
class ManagedPrincipal:
    """Principal metadata used by managed mailbox scripts."""

    principal_id: str
    address: str

    @classmethod
    def from_payload(cls, payload: object) -> "ManagedPrincipal":
        """Build a principal from a JSON payload mapping."""

        if not isinstance(payload, dict):
            raise ManagedMailboxOperationError("principal payload must be a mapping")
        principal_id = _require_str(payload, "principal_id")
        address = _require_str(payload, "address")
        return cls(principal_id=principal_id, address=address)


@dataclass(frozen=True)
class DeliveryRequest:
    """Structured delivery request for `deliver_message.py`."""

    staged_message_path: Path
    message_id: str
    thread_id: str
    in_reply_to: str | None
    references: tuple[str, ...]
    created_at_utc: str
    sender: ManagedPrincipal
    to: tuple[ManagedPrincipal, ...]
    cc: tuple[ManagedPrincipal, ...]
    reply_to: tuple[ManagedPrincipal, ...]
    subject: str
    attachments: tuple[dict[str, object], ...]
    headers: dict[str, object]

    @classmethod
    def from_payload(cls, payload: object) -> "DeliveryRequest":
        """Build a delivery request from JSON payload data."""

        if not isinstance(payload, dict):
            raise ManagedMailboxOperationError("delivery payload must be a mapping")

        staged_message_path = Path(_require_str(payload, "staged_message_path")).resolve()
        message_id = _validate_message_id(_require_str(payload, "message_id"))
        thread_id = _validate_message_id(_require_str(payload, "thread_id"))
        in_reply_to_raw = payload.get("in_reply_to")
        in_reply_to = _validate_optional_message_id(in_reply_to_raw)
        references = _parse_message_id_list(payload.get("references", []))
        created_at_utc = _normalize_timestamp(_require_str(payload, "created_at_utc"))
        sender = ManagedPrincipal.from_payload(payload.get("sender"))
        to = _parse_principal_list(payload.get("to"))
        cc = _parse_principal_list(payload.get("cc", []))
        reply_to = _parse_principal_list(payload.get("reply_to", []))
        subject = _require_str(payload, "subject")
        attachments = _parse_attachment_list(payload.get("attachments", []))
        headers = _parse_object_mapping(payload.get("headers", {}), field_name="headers")

        if not to:
            raise ManagedMailboxOperationError(
                "delivery payload must include at least one recipient"
            )
        if in_reply_to is None:
            if thread_id != message_id:
                raise ManagedMailboxOperationError(
                    "root deliveries must use message_id as thread_id"
                )
            if references:
                raise ManagedMailboxOperationError("root deliveries must not include references")
        else:
            if not references:
                raise ManagedMailboxOperationError("reply deliveries must include references")
            if references[-1] != in_reply_to:
                raise ManagedMailboxOperationError("references must end with in_reply_to")

        return cls(
            staged_message_path=staged_message_path,
            message_id=message_id,
            thread_id=thread_id,
            in_reply_to=in_reply_to,
            references=references,
            created_at_utc=created_at_utc,
            sender=sender,
            to=to,
            cc=cc,
            reply_to=reply_to,
            subject=subject,
            attachments=attachments,
            headers=headers,
        )


@dataclass(frozen=True)
class StateUpdateRequest:
    """Structured mailbox-state mutation request."""

    principal_id: str
    message_id: str
    read: bool | None
    starred: bool | None
    archived: bool | None
    deleted: bool | None

    @classmethod
    def from_payload(cls, payload: object) -> "StateUpdateRequest":
        """Build a state update request from JSON payload data."""

        if not isinstance(payload, dict):
            raise ManagedMailboxOperationError("state update payload must be a mapping")

        read = _optional_bool(payload.get("read"), field_name="read")
        starred = _optional_bool(payload.get("starred"), field_name="starred")
        archived = _optional_bool(payload.get("archived"), field_name="archived")
        deleted = _optional_bool(payload.get("deleted"), field_name="deleted")
        if read is starred is archived is deleted is None:
            raise ManagedMailboxOperationError("state update payload must set at least one field")

        return cls(
            principal_id=_require_str(payload, "principal_id"),
            message_id=_validate_message_id(_require_str(payload, "message_id")),
            read=read,
            starred=starred,
            archived=archived,
            deleted=deleted,
        )


@dataclass(frozen=True)
class RepairRequest:
    """Structured mailbox repair or reindex request."""

    cleanup_staging: bool = True
    quarantine_staging: bool = True

    @classmethod
    def from_payload(cls, payload: object) -> "RepairRequest":
        """Build a repair request from JSON payload data."""

        if payload is None:
            return cls()
        if not isinstance(payload, dict):
            raise ManagedMailboxOperationError("repair payload must be a mapping")

        cleanup_staging = _optional_bool(
            payload.get("cleanup_staging"), field_name="cleanup_staging"
        )
        quarantine_staging = _optional_bool(
            payload.get("quarantine_staging"),
            field_name="quarantine_staging",
        )
        return cls(
            cleanup_staging=True if cleanup_staging is None else cleanup_staging,
            quarantine_staging=True if quarantine_staging is None else quarantine_staging,
        )


@dataclass(frozen=True)
class RegisteredPrincipal:
    """Resolved mailbox registration for one principal."""

    principal_id: str
    address: str
    mailbox_kind: str
    mailbox_path: Path


@dataclass(frozen=True)
class _RecoveredMessageDocument:
    """Canonical mailbox message plus its on-disk document text."""

    canonical_path: Path
    document_text: str
    message: MailboxMessage


@dataclass(frozen=True)
class _RecoveredPrincipalRecord:
    """Recovered principal row to persist during repair."""

    principal_id: str
    address: str
    display_name: str | None
    manifest_path_hint: str | None
    role: str | None
    mailbox_kind: str
    mailbox_path: Path
    created_at_utc: str


@dataclass(frozen=True)
class _IndexSnapshot:
    """Existing mailbox index data preserved across reindex."""

    principals: dict[str, _RecoveredPrincipalRecord]
    mailbox_state: dict[tuple[str, str], tuple[bool, bool, bool, bool]]
    backup_path: Path | None


def load_json_payload(path: Path) -> object:
    """Load a JSON payload file for a managed mailbox script."""

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ManagedMailboxOperationError(f"payload file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ManagedMailboxOperationError(f"payload file is not valid JSON: {path}") from exc


def deliver_message(
    mailbox_root: Path,
    request: DeliveryRequest,
    *,
    lock_timeout_seconds: float = 5.0,
) -> dict[str, object]:
    """Commit a staged mailbox message into the filesystem transport."""

    paths = _resolve_paths(mailbox_root)
    _ensure_protocol_version(paths["protocol_version_file"])
    staged_message_path = request.staged_message_path.resolve()
    _ensure_staged_message_path(paths["staging_dir"], staged_message_path)

    recipient_principals = _unique_principals((*request.to, *request.cc))
    affected_principal_ids = tuple(
        sorted(
            {
                request.sender.principal_id,
                *(principal.principal_id for principal in recipient_principals),
            }
        )
    )

    with sqlite3.connect(paths["sqlite_path"]) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        registrations = _load_principal_registrations(connection, affected_principal_ids)
        _validate_registered_principal(
            registrations[request.sender.principal_id], paths["mailboxes_dir"]
        )
        for principal in recipient_principals:
            registration = registrations.get(principal.principal_id)
            if registration is None:
                raise ManagedMailboxOperationError(
                    f"missing principal registration for `{principal.principal_id}`"
                )
            _validate_registered_principal(registration, paths["mailboxes_dir"])
            if registration.address != principal.address:
                raise ManagedMailboxOperationError(
                    f"registered address mismatch for `{principal.principal_id}`"
                )

        canonical_dir = paths["messages_dir"] / request.created_at_utc[:10]
        canonical_path = canonical_dir / f"{request.message_id}.md"
        projection_targets = _build_projection_targets(
            registrations=registrations,
            sender_principal_id=request.sender.principal_id,
            recipient_principals=recipient_principals,
            message_id=request.message_id,
        )

        created_projection_paths: list[Path] = []
        moved_to_canonical = False

        with _acquired_lock_set(
            paths, affected_principal_ids, timeout_seconds=lock_timeout_seconds
        ):
            try:
                if canonical_path.exists():
                    raise ManagedMailboxOperationError(
                        f"canonical message already exists: {canonical_path}"
                    )

                canonical_dir.mkdir(parents=True, exist_ok=True)
                staged_message_path.replace(canonical_path)
                moved_to_canonical = True

                for projection_path in projection_targets:
                    _create_projection_symlink(projection_path, canonical_path)
                    created_projection_paths.append(projection_path)

                connection.execute("BEGIN IMMEDIATE")
                _insert_message_record(connection, request, canonical_path)
                _insert_recipient_records(connection, request)
                _insert_attachment_records(connection, request)
                _insert_projection_records(
                    connection=connection,
                    sender_principal_id=request.sender.principal_id,
                    recipient_principals=recipient_principals,
                    projection_paths=projection_targets,
                    message_id=request.message_id,
                )
                _insert_mailbox_state_records(
                    connection=connection,
                    sender_principal_id=request.sender.principal_id,
                    recipient_principals=recipient_principals,
                    message_id=request.message_id,
                )
                _recompute_thread_summary(connection, request.thread_id)
                connection.commit()
            except Exception:
                connection.rollback()
                for projection_path in reversed(created_projection_paths):
                    if projection_path.is_symlink() or projection_path.exists():
                        projection_path.unlink(missing_ok=True)
                if (
                    moved_to_canonical
                    and canonical_path.exists()
                    and not staged_message_path.exists()
                ):
                    canonical_path.replace(staged_message_path)
                raise

    return {
        "ok": True,
        "message_id": request.message_id,
        "canonical_path": str(canonical_path),
        "recipient_count": len(recipient_principals),
    }


def update_mailbox_state(
    mailbox_root: Path,
    request: StateUpdateRequest,
    *,
    lock_timeout_seconds: float = 5.0,
) -> dict[str, object]:
    """Apply a mailbox-state mutation for one principal and message."""

    paths = _resolve_paths(mailbox_root)
    _ensure_protocol_version(paths["protocol_version_file"])

    with sqlite3.connect(paths["sqlite_path"]) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        registrations = _load_principal_registrations(connection, (request.principal_id,))
        registration = registrations.get(request.principal_id)
        if registration is None:
            raise ManagedMailboxOperationError(
                f"missing principal registration for `{request.principal_id}`"
            )
        _validate_registered_principal(registration, paths["mailboxes_dir"])

        message_row = connection.execute(
            "SELECT thread_id FROM messages WHERE message_id = ?",
            (request.message_id,),
        ).fetchone()
        if message_row is None:
            raise ManagedMailboxOperationError(f"unknown message id `{request.message_id}`")
        thread_id = str(message_row[0])

        with _acquired_lock_set(
            paths,
            (request.principal_id,),
            timeout_seconds=lock_timeout_seconds,
        ):
            connection.execute("BEGIN IMMEDIATE")
            existing_state = connection.execute(
                """
                SELECT 1
                FROM mailbox_state
                WHERE principal_id = ? AND message_id = ?
                """,
                (request.principal_id, request.message_id),
            ).fetchone()
            if existing_state is None:
                projection_exists = connection.execute(
                    """
                    SELECT 1
                    FROM mailbox_projections
                    WHERE principal_id = ? AND message_id = ?
                    """,
                    (request.principal_id, request.message_id),
                ).fetchone()
                if projection_exists is None:
                    connection.rollback()
                    raise ManagedMailboxOperationError(
                        f"message `{request.message_id}` is not projected into principal `{request.principal_id}`"
                    )
                connection.execute(
                    """
                    INSERT INTO mailbox_state (
                        principal_id,
                        message_id,
                        is_read,
                        is_starred,
                        is_archived,
                        is_deleted
                    )
                    VALUES (?, ?, 0, 0, 0, 0)
                    """,
                    (request.principal_id, request.message_id),
                )

            assignments: list[str] = []
            parameters: list[object] = []
            if request.read is not None:
                assignments.append("is_read = ?")
                parameters.append(int(request.read))
            if request.starred is not None:
                assignments.append("is_starred = ?")
                parameters.append(int(request.starred))
            if request.archived is not None:
                assignments.append("is_archived = ?")
                parameters.append(int(request.archived))
            if request.deleted is not None:
                assignments.append("is_deleted = ?")
                parameters.append(int(request.deleted))
            parameters.extend((request.principal_id, request.message_id))
            connection.execute(
                f"""
                UPDATE mailbox_state
                SET {", ".join(assignments)}
                WHERE principal_id = ? AND message_id = ?
                """,
                tuple(parameters),
            )
            _recompute_thread_summary(connection, thread_id)
            state_row = connection.execute(
                """
                SELECT is_read, is_starred, is_archived, is_deleted
                FROM mailbox_state
                WHERE principal_id = ? AND message_id = ?
                """,
                (request.principal_id, request.message_id),
            ).fetchone()
            connection.commit()

    assert state_row is not None
    return {
        "ok": True,
        "principal_id": request.principal_id,
        "message_id": request.message_id,
        "read": bool(state_row[0]),
        "starred": bool(state_row[1]),
        "archived": bool(state_row[2]),
        "deleted": bool(state_row[3]),
    }


def repair_mailbox_index(
    mailbox_root: Path,
    request: RepairRequest,
    *,
    lock_timeout_seconds: float = 5.0,
) -> dict[str, object]:
    """Rebuild mailbox indexes from canonical messages and clean staging artifacts."""

    paths = _resolve_paths(mailbox_root)
    _ensure_protocol_version(paths["protocol_version_file"])
    discovered_mailboxes = _discover_mailbox_paths(paths["mailboxes_dir"])

    with _acquired_lock_set(
        paths,
        tuple(sorted(discovered_mailboxes)),
        timeout_seconds=lock_timeout_seconds,
    ):
        recovered_messages = _load_recovery_messages(paths["messages_dir"])
        snapshot = _snapshot_existing_index(paths["sqlite_path"])
        initialize_sqlite_schema(paths["sqlite_path"])
        staging_results = (
            _cleanup_staging_artifacts(
                paths["staging_dir"],
                quarantine=request.quarantine_staging,
            )
            if request.cleanup_staging
            else []
        )

        with sqlite3.connect(paths["sqlite_path"]) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("BEGIN IMMEDIATE")
            principal_records = _recover_principal_records(
                connection=connection,
                discovered_mailboxes=discovered_mailboxes,
                snapshot=snapshot,
                recovered_messages=recovered_messages,
                mailboxes_dir=paths["mailboxes_dir"],
            )
            projection_count = 0
            restored_state_count = 0
            defaulted_state_count = 0
            thread_ids: set[str] = set()

            for recovered_message in recovered_messages:
                thread_ids.add(recovered_message.message.thread_id)
                _insert_recovered_message_record(connection, recovered_message)
                _insert_recovered_recipient_records(connection, recovered_message.message)
                _insert_recovered_attachment_records(connection, recovered_message.message)
                projection_count += _repair_projection_records(
                    connection=connection,
                    principal_records=principal_records,
                    recovered_message=recovered_message,
                )
                restored_count, defaulted_count = _insert_recovered_mailbox_state_records(
                    connection=connection,
                    snapshot=snapshot,
                    principal_records=principal_records,
                    message=recovered_message.message,
                )
                restored_state_count += restored_count
                defaulted_state_count += defaulted_count

            for thread_id in sorted(thread_ids):
                _recompute_thread_summary(connection, thread_id)
            connection.commit()

    return {
        "ok": True,
        "message_count": len(recovered_messages),
        "projection_count": projection_count,
        "principal_count": len(principal_records),
        "restored_state_count": restored_state_count,
        "defaulted_state_count": defaulted_state_count,
        "staging_action": "quarantine" if request.quarantine_staging else "remove",
        "staging_artifact_count": len(staging_results),
        "staging_artifact_paths": [str(path) for path in staging_results],
        "backed_up_index_path": None if snapshot.backup_path is None else str(snapshot.backup_path),
    }


def _resolve_paths(mailbox_root: Path) -> dict[str, Path]:
    """Resolve the filesystem paths used by managed mailbox scripts."""

    root = mailbox_root.resolve()
    return {
        "root": root,
        "protocol_version_file": root / "protocol-version.txt",
        "sqlite_path": root / "index.sqlite",
        "messages_dir": root / "messages",
        "mailboxes_dir": root / "mailboxes",
        "staging_dir": root / "staging",
        "index_lock": root / "locks" / "index.lock",
        "principal_locks_dir": root / "locks" / "principals",
    }


def _ensure_protocol_version(protocol_version_file: Path) -> None:
    """Validate the mailbox protocol version file."""

    try:
        value = protocol_version_file.read_text(encoding="utf-8").strip()
    except FileNotFoundError as exc:
        raise ManagedMailboxOperationError(
            f"missing protocol version file: {protocol_version_file}"
        ) from exc
    if value != str(MAILBOX_PROTOCOL_VERSION):
        raise ManagedMailboxOperationError(
            f"unsupported mailbox protocol version: expected {MAILBOX_PROTOCOL_VERSION}, found {value or '<empty>'}"
        )


def _ensure_staged_message_path(staging_dir: Path, staged_message_path: Path) -> None:
    """Require staged messages to live under the mailbox staging directory."""

    try:
        staged_message_path.relative_to(staging_dir.resolve())
    except ValueError as exc:
        raise ManagedMailboxOperationError(
            "staged message must live under the mailbox staging directory"
        ) from exc
    if not staged_message_path.is_file():
        raise ManagedMailboxOperationError(f"staged message not found: {staged_message_path}")


def _load_principal_registrations(
    connection: sqlite3.Connection,
    principal_ids: Sequence[str],
) -> dict[str, RegisteredPrincipal]:
    """Load principal registrations keyed by principal id."""

    if not principal_ids:
        return {}

    placeholders = ", ".join("?" for _ in principal_ids)
    rows = connection.execute(
        f"""
        SELECT principal_id, address, mailbox_kind, mailbox_path
        FROM principals
        WHERE principal_id IN ({placeholders})
        """,
        tuple(principal_ids),
    ).fetchall()
    return {
        str(row[0]): RegisteredPrincipal(
            principal_id=str(row[0]),
            address=str(row[1]),
            mailbox_kind=str(row[2]),
            mailbox_path=Path(str(row[3])),
        )
        for row in rows
    }


def _validate_registered_principal(
    registration: RegisteredPrincipal,
    mailboxes_dir: Path,
) -> None:
    """Validate an existing principal registration target."""

    mailbox_path = registration.mailbox_path
    if not mailbox_path.exists() or not mailbox_path.is_dir():
        raise ManagedMailboxOperationError(
            f"invalid mailbox registration for `{registration.principal_id}`: {mailbox_path}"
        )
    if registration.mailbox_kind == "symlink":
        symlink_entry = mailboxes_dir / registration.principal_id
        if not symlink_entry.is_symlink():
            raise ManagedMailboxOperationError(
                f"symlink registration missing for `{registration.principal_id}`"
            )
    for directory_name in _MAILBOX_PLACEHOLDER_DIRS:
        if not (mailbox_path / directory_name).is_dir():
            raise ManagedMailboxOperationError(
                f"mailbox registration for `{registration.principal_id}` is missing `{directory_name}/`"
            )


def _build_projection_targets(
    *,
    registrations: dict[str, RegisteredPrincipal],
    sender_principal_id: str,
    recipient_principals: Sequence[ManagedPrincipal],
    message_id: str,
) -> list[Path]:
    """Compute inbox and sent projection targets for a delivery."""

    targets: list[Path] = []
    sender_registration = registrations[sender_principal_id]
    targets.append(sender_registration.mailbox_path / "sent" / f"{message_id}.md")
    for principal in recipient_principals:
        registration = registrations[principal.principal_id]
        targets.append(registration.mailbox_path / "inbox" / f"{message_id}.md")
    return targets


def _create_projection_symlink(projection_path: Path, canonical_path: Path) -> None:
    """Create one mailbox projection symlink."""

    if projection_path.exists() or projection_path.is_symlink():
        raise ManagedMailboxOperationError(f"projection already exists: {projection_path}")
    projection_path.symlink_to(canonical_path)


def _insert_message_record(
    connection: sqlite3.Connection,
    request: DeliveryRequest,
    canonical_path: Path,
) -> None:
    """Insert the canonical message row."""

    connection.execute(
        """
        INSERT INTO messages (
            message_id,
            thread_id,
            in_reply_to,
            created_at_utc,
            canonical_path,
            subject,
            body_markdown,
            headers_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            request.message_id,
            request.thread_id,
            request.in_reply_to,
            request.created_at_utc,
            str(canonical_path),
            request.subject,
            canonical_path.read_text(encoding="utf-8"),
            json.dumps(request.headers, sort_keys=True),
        ),
    )


def _insert_recipient_records(connection: sqlite3.Connection, request: DeliveryRequest) -> None:
    """Insert canonical recipient associations."""

    ordinal = 0
    for recipient_kind, principals in (("to", request.to), ("cc", request.cc)):
        for principal in principals:
            connection.execute(
                """
                INSERT INTO message_recipients (
                    message_id,
                    principal_id,
                    recipient_kind,
                    ordinal
                )
                VALUES (?, ?, ?, ?)
                """,
                (request.message_id, principal.principal_id, recipient_kind, ordinal),
            )
            ordinal += 1


def _insert_attachment_records(connection: sqlite3.Connection, request: DeliveryRequest) -> None:
    """Insert attachment metadata rows."""

    for ordinal, attachment in enumerate(request.attachments):
        attachment_id = _require_str(attachment, "attachment_id")
        connection.execute(
            """
            INSERT INTO attachments (
                attachment_id,
                kind,
                locator,
                media_type,
                sha256,
                size_bytes,
                label
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                attachment_id,
                _require_str(attachment, "kind"),
                _require_str(attachment, "path"),
                _require_str(attachment, "media_type"),
                _optional_str(attachment.get("sha256"), field_name="sha256"),
                _optional_int(attachment.get("size_bytes"), field_name="size_bytes"),
                _optional_str(attachment.get("label"), field_name="label"),
            ),
        )
        connection.execute(
            """
            INSERT INTO message_attachments (
                message_id,
                attachment_id,
                ordinal
            )
            VALUES (?, ?, ?)
            """,
            (request.message_id, attachment_id, ordinal),
        )


def _insert_projection_records(
    *,
    connection: sqlite3.Connection,
    sender_principal_id: str,
    recipient_principals: Sequence[ManagedPrincipal],
    projection_paths: Sequence[Path],
    message_id: str,
) -> None:
    """Insert projection catalog rows."""

    connection.execute(
        """
        INSERT INTO mailbox_projections (
            principal_id,
            message_id,
            folder_name,
            projection_path
        )
        VALUES (?, ?, ?, ?)
        """,
        (sender_principal_id, message_id, "sent", str(projection_paths[0])),
    )
    for principal, projection_path in zip(recipient_principals, projection_paths[1:], strict=True):
        connection.execute(
            """
            INSERT INTO mailbox_projections (
                principal_id,
                message_id,
                folder_name,
                projection_path
            )
            VALUES (?, ?, ?, ?)
            """,
            (principal.principal_id, message_id, "inbox", str(projection_path)),
        )


def _insert_mailbox_state_records(
    *,
    connection: sqlite3.Connection,
    sender_principal_id: str,
    recipient_principals: Sequence[ManagedPrincipal],
    message_id: str,
) -> None:
    """Insert deterministic default mailbox-state rows."""

    affected_principal_ids = {
        sender_principal_id,
        *(principal.principal_id for principal in recipient_principals),
    }
    for principal_id in sorted(affected_principal_ids):
        connection.execute(
            """
            INSERT INTO mailbox_state (
                principal_id,
                message_id,
                is_read,
                is_starred,
                is_archived,
                is_deleted
            )
            VALUES (?, ?, ?, 0, 0, 0)
            """,
            (principal_id, message_id, int(principal_id == sender_principal_id)),
        )


def _recompute_thread_summary(connection: sqlite3.Connection, thread_id: str) -> None:
    """Recompute cached thread summary state."""

    latest_row = connection.execute(
        """
        SELECT message_id, created_at_utc, subject
        FROM messages
        WHERE thread_id = ?
        ORDER BY created_at_utc DESC, message_id DESC
        LIMIT 1
        """,
        (thread_id,),
    ).fetchone()
    if latest_row is None:
        return

    unread_count = int(
        connection.execute(
            """
            SELECT COUNT(*)
            FROM mailbox_state AS state
            JOIN messages AS message ON message.message_id = state.message_id
            WHERE message.thread_id = ? AND state.is_read = 0
            """,
            (thread_id,),
        ).fetchone()[0]
    )
    connection.execute(
        """
        INSERT INTO thread_summaries (
            thread_id,
            normalized_subject,
            latest_message_id,
            latest_message_created_at_utc,
            unread_count
        )
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(thread_id) DO UPDATE SET
            normalized_subject = excluded.normalized_subject,
            latest_message_id = excluded.latest_message_id,
            latest_message_created_at_utc = excluded.latest_message_created_at_utc,
            unread_count = excluded.unread_count
        """,
        (
            thread_id,
            str(latest_row[2]).strip().lower(),
            str(latest_row[0]),
            str(latest_row[1]),
            unread_count,
        ),
    )


@contextmanager
def _acquired_lock_set(
    paths: dict[str, Path],
    principal_ids: Sequence[str],
    *,
    timeout_seconds: float,
) -> Iterator[None]:
    """Acquire principal locks in lexicographic order, then the shared index lock."""

    lock_paths = [
        paths["principal_locks_dir"] / f"{principal_id}.lock"
        for principal_id in sorted(principal_ids)
    ]
    lock_paths.append(paths["index_lock"])
    acquired_paths: list[Path] = []
    try:
        for lock_path in lock_paths:
            _acquire_lock_file(lock_path, timeout_seconds=timeout_seconds)
            acquired_paths.append(lock_path)
        yield
    finally:
        for lock_path in reversed(acquired_paths):
            lock_path.unlink(missing_ok=True)


def _acquire_lock_file(lock_path: Path, *, timeout_seconds: float) -> None:
    """Acquire one lock file with bounded waiting."""

    deadline = time.monotonic() + timeout_seconds
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    while True:
        try:
            with lock_path.open("x", encoding="utf-8") as handle:
                handle.write(f"pid={os.getpid()} acquired_at_utc={datetime.now(UTC).isoformat()}\n")
            return
        except FileExistsError as exc:
            if time.monotonic() >= deadline:
                raise ManagedMailboxOperationError(
                    f"timed out acquiring lock: {lock_path}"
                ) from exc
            time.sleep(0.05)


def _unique_principals(principals: Sequence[ManagedPrincipal]) -> tuple[ManagedPrincipal, ...]:
    """Deduplicate principals by id while preserving the first-seen address."""

    ordered: dict[str, ManagedPrincipal] = {}
    for principal in principals:
        existing = ordered.get(principal.principal_id)
        if existing is not None and existing.address != principal.address:
            raise ManagedMailboxOperationError(
                f"conflicting addresses for principal `{principal.principal_id}`"
            )
        ordered.setdefault(principal.principal_id, principal)
    return tuple(ordered.values())


def _parse_principal_list(payload: object) -> tuple[ManagedPrincipal, ...]:
    """Parse a JSON principal list."""

    if not isinstance(payload, list):
        raise ManagedMailboxOperationError("principal lists must be arrays")
    return tuple(ManagedPrincipal.from_payload(item) for item in payload)


def _parse_attachment_list(payload: object) -> tuple[dict[str, object], ...]:
    """Parse attachment payloads as immutable mappings."""

    if not isinstance(payload, list):
        raise ManagedMailboxOperationError("attachments must be an array")
    parsed: list[dict[str, object]] = []
    for item in payload:
        if not isinstance(item, dict):
            raise ManagedMailboxOperationError("attachment payloads must be mappings")
        parsed.append(dict(item))
    return tuple(parsed)


def _discover_mailbox_paths(mailboxes_dir: Path) -> dict[str, tuple[str, Path]]:
    """Discover mailbox registration paths from the mailboxes directory."""

    discovered: dict[str, tuple[str, Path]] = {}
    if not mailboxes_dir.exists():
        return discovered

    for entry in sorted(mailboxes_dir.iterdir(), key=lambda path: path.name):
        mailbox_kind = "symlink" if entry.is_symlink() else "in_root"
        mailbox_path = entry.resolve()
        if mailbox_path.exists() and mailbox_path.is_dir():
            _ensure_mailbox_placeholder_dirs(mailbox_path)
        discovered[entry.name] = (mailbox_kind, mailbox_path)
    return discovered


def _load_recovery_messages(messages_dir: Path) -> list[_RecoveredMessageDocument]:
    """Load and validate canonical message documents for repair."""

    if not messages_dir.exists():
        return []

    recovered_messages: list[_RecoveredMessageDocument] = []
    for canonical_path in sorted(messages_dir.rglob("*.md")):
        document_text = canonical_path.read_text(encoding="utf-8")
        try:
            message = parse_message_document(document_text)
        except Exception as exc:
            raise ManagedMailboxOperationError(
                f"invalid canonical mailbox message `{canonical_path}`: {exc}"
            ) from exc
        expected_filename = f"{message.message_id}.md"
        if canonical_path.name != expected_filename:
            raise ManagedMailboxOperationError(
                f"canonical mailbox message filename does not match message_id: {canonical_path}"
            )
        expected_date_dir = message.created_at_utc[:10]
        if canonical_path.parent.name != expected_date_dir:
            raise ManagedMailboxOperationError(
                f"canonical mailbox message date directory does not match created_at_utc: {canonical_path}"
            )
        recovered_messages.append(
            _RecoveredMessageDocument(
                canonical_path=canonical_path,
                document_text=document_text,
                message=message,
            )
        )

    recovered_messages.sort(
        key=lambda item: (item.message.created_at_utc, item.message.message_id),
    )
    return recovered_messages


def _snapshot_existing_index(sqlite_path: Path) -> _IndexSnapshot:
    """Snapshot recoverable principal and mailbox-state rows from an existing index."""

    if not sqlite_path.exists():
        return _IndexSnapshot(principals={}, mailbox_state={}, backup_path=None)

    try:
        with sqlite3.connect(sqlite_path) as connection:
            principal_rows = connection.execute(
                """
                SELECT
                    principal_id,
                    address,
                    display_name,
                    manifest_path_hint,
                    role,
                    mailbox_kind,
                    mailbox_path,
                    created_at_utc
                FROM principals
                """
            ).fetchall()
            state_rows = connection.execute(
                """
                SELECT
                    principal_id,
                    message_id,
                    is_read,
                    is_starred,
                    is_archived,
                    is_deleted
                FROM mailbox_state
                """
            ).fetchall()
    except sqlite3.DatabaseError:
        backup_path = _backup_replaced_index(sqlite_path, suffix="unusable")
        return _IndexSnapshot(principals={}, mailbox_state={}, backup_path=backup_path)

    principals = {
        str(row[0]): _RecoveredPrincipalRecord(
            principal_id=str(row[0]),
            address=str(row[1]),
            display_name=None if row[2] is None else str(row[2]),
            manifest_path_hint=None if row[3] is None else str(row[3]),
            role=None if row[4] is None else str(row[4]),
            mailbox_kind=str(row[5]),
            mailbox_path=Path(str(row[6])),
            created_at_utc=str(row[7]),
        )
        for row in principal_rows
    }
    mailbox_state = {
        (str(row[0]), str(row[1])): (bool(row[2]), bool(row[3]), bool(row[4]), bool(row[5]))
        for row in state_rows
    }
    sqlite_path.unlink(missing_ok=True)
    return _IndexSnapshot(principals=principals, mailbox_state=mailbox_state, backup_path=None)


def _recover_principal_records(
    *,
    connection: sqlite3.Connection,
    discovered_mailboxes: dict[str, tuple[str, Path]],
    snapshot: _IndexSnapshot,
    recovered_messages: Sequence[_RecoveredMessageDocument],
    mailboxes_dir: Path,
) -> dict[str, _RecoveredPrincipalRecord]:
    """Recover principal rows from previous index state plus canonical messages."""

    principal_records = dict(snapshot.principals)
    for recovered_message in recovered_messages:
        message = recovered_message.message
        for principal in (message.sender, *message.to, *message.cc):
            existing = principal_records.get(principal.principal_id)
            mailbox_kind, mailbox_path = discovered_mailboxes.get(
                principal.principal_id,
                (
                    existing.mailbox_kind if existing is not None else "recovered_missing",
                    existing.mailbox_path
                    if existing is not None
                    else mailboxes_dir / principal.principal_id,
                ),
            )
            principal_records[principal.principal_id] = _RecoveredPrincipalRecord(
                principal_id=principal.principal_id,
                address=existing.address if existing is not None else principal.address,
                display_name=(
                    existing.display_name if existing is not None else principal.display_name
                ),
                manifest_path_hint=(
                    existing.manifest_path_hint
                    if existing is not None
                    else principal.manifest_path_hint
                ),
                role=existing.role if existing is not None else principal.role,
                mailbox_kind=mailbox_kind,
                mailbox_path=mailbox_path,
                created_at_utc=(
                    existing.created_at_utc if existing is not None else message.created_at_utc
                ),
            )

    for principal_id, (mailbox_kind, mailbox_path) in discovered_mailboxes.items():
        existing = principal_records.get(principal_id)
        if existing is None:
            continue
        principal_records[principal_id] = _RecoveredPrincipalRecord(
            principal_id=existing.principal_id,
            address=existing.address,
            display_name=existing.display_name,
            manifest_path_hint=existing.manifest_path_hint,
            role=existing.role,
            mailbox_kind=mailbox_kind,
            mailbox_path=mailbox_path,
            created_at_utc=existing.created_at_utc,
        )

    for principal_id, principal_record in sorted(principal_records.items()):
        connection.execute(
            """
            INSERT INTO principals (
                principal_id,
                address,
                display_name,
                manifest_path_hint,
                role,
                mailbox_kind,
                mailbox_path,
                created_at_utc
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                principal_record.principal_id,
                principal_record.address,
                principal_record.display_name,
                principal_record.manifest_path_hint,
                principal_record.role,
                principal_record.mailbox_kind,
                str(principal_record.mailbox_path),
                principal_record.created_at_utc,
            ),
        )
    return principal_records


def _insert_recovered_message_record(
    connection: sqlite3.Connection,
    recovered_message: _RecoveredMessageDocument,
) -> None:
    """Insert one recovered canonical message row."""

    message = recovered_message.message
    connection.execute(
        """
        INSERT INTO messages (
            message_id,
            thread_id,
            in_reply_to,
            created_at_utc,
            canonical_path,
            subject,
            body_markdown,
            headers_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            message.message_id,
            message.thread_id,
            message.in_reply_to,
            message.created_at_utc,
            str(recovered_message.canonical_path),
            message.subject,
            recovered_message.document_text,
            json.dumps(message.headers, sort_keys=True),
        ),
    )


def _insert_recovered_recipient_records(
    connection: sqlite3.Connection,
    message: MailboxMessage,
) -> None:
    """Insert recovered recipient associations for one message."""

    ordinal = 0
    for recipient_kind, principals in (("to", message.to), ("cc", message.cc)):
        for principal in principals:
            connection.execute(
                """
                INSERT INTO message_recipients (
                    message_id,
                    principal_id,
                    recipient_kind,
                    ordinal
                )
                VALUES (?, ?, ?, ?)
                """,
                (message.message_id, principal.principal_id, recipient_kind, ordinal),
            )
            ordinal += 1


def _insert_recovered_attachment_records(
    connection: sqlite3.Connection,
    message: MailboxMessage,
) -> None:
    """Insert recovered attachment metadata rows for one message."""

    for ordinal, attachment in enumerate(message.attachments):
        connection.execute(
            """
            INSERT INTO attachments (
                attachment_id,
                kind,
                locator,
                media_type,
                sha256,
                size_bytes,
                label
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                attachment.attachment_id,
                attachment.kind,
                attachment.path,
                attachment.media_type,
                attachment.sha256,
                attachment.size_bytes,
                attachment.label,
            ),
        )
        connection.execute(
            """
            INSERT INTO message_attachments (
                message_id,
                attachment_id,
                ordinal
            )
            VALUES (?, ?, ?)
            """,
            (message.message_id, attachment.attachment_id, ordinal),
        )


def _repair_projection_records(
    *,
    connection: sqlite3.Connection,
    principal_records: dict[str, _RecoveredPrincipalRecord],
    recovered_message: _RecoveredMessageDocument,
) -> int:
    """Repair projection symlinks and rebuild the projection catalog for one message."""

    message = recovered_message.message
    projection_count = 0
    projection_specs: list[tuple[str, str]] = [(message.sender.principal_id, "sent")]
    projection_specs.extend(
        (principal.principal_id, "inbox")
        for principal in _unique_mailbox_principals((*message.to, *message.cc))
    )

    for principal_id, folder_name in projection_specs:
        principal_record = principal_records[principal_id]
        if not principal_record.mailbox_path.exists():
            continue
        if not principal_record.mailbox_path.is_dir():
            raise ManagedMailboxOperationError(
                f"invalid recovered mailbox path for `{principal_id}`: {principal_record.mailbox_path}"
            )

        _ensure_mailbox_placeholder_dirs(principal_record.mailbox_path)
        projection_path = principal_record.mailbox_path / folder_name / f"{message.message_id}.md"
        if projection_path.is_symlink():
            if projection_path.resolve() != recovered_message.canonical_path:
                raise ManagedMailboxOperationError(
                    f"projection target mismatch for `{projection_path}`"
                )
        elif projection_path.exists():
            raise ManagedMailboxOperationError(
                f"projection path exists but is not a symlink: {projection_path}"
            )
        else:
            projection_path.symlink_to(recovered_message.canonical_path)

        connection.execute(
            """
            INSERT INTO mailbox_projections (
                principal_id,
                message_id,
                folder_name,
                projection_path
            )
            VALUES (?, ?, ?, ?)
            """,
            (principal_id, message.message_id, folder_name, str(projection_path)),
        )
        projection_count += 1

    return projection_count


def _insert_recovered_mailbox_state_records(
    *,
    connection: sqlite3.Connection,
    snapshot: _IndexSnapshot,
    principal_records: dict[str, _RecoveredPrincipalRecord],
    message: MailboxMessage,
) -> tuple[int, int]:
    """Insert restored or default mailbox-state rows for one recovered message."""

    restored_state_count = 0
    defaulted_state_count = 0
    affected_principal_ids = {
        message.sender.principal_id,
        *(
            principal.principal_id
            for principal in _unique_mailbox_principals((*message.to, *message.cc))
        ),
    }
    for principal_id in sorted(affected_principal_ids):
        if principal_id not in principal_records:
            raise ManagedMailboxOperationError(
                f"missing recovered principal record for `{principal_id}`"
            )
        prior_state = snapshot.mailbox_state.get((principal_id, message.message_id))
        if prior_state is None:
            state_values = (int(principal_id == message.sender.principal_id), 0, 0, 0)
            defaulted_state_count += 1
        else:
            read_state, starred_state, archived_state, deleted_state = prior_state
            state_values = (
                int(read_state),
                int(starred_state),
                int(archived_state),
                int(deleted_state),
            )
            restored_state_count += 1

        connection.execute(
            """
            INSERT INTO mailbox_state (
                principal_id,
                message_id,
                is_read,
                is_starred,
                is_archived,
                is_deleted
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                principal_id,
                message.message_id,
                *state_values,
            ),
        )

    return restored_state_count, defaulted_state_count


def _cleanup_staging_artifacts(staging_dir: Path, *, quarantine: bool) -> list[Path]:
    """Remove or quarantine orphaned staging artifacts."""

    if not staging_dir.exists():
        return []

    cleanup_results: list[Path] = []
    quarantine_root = staging_dir / "quarantine" / _timestamp_label()
    for staging_path in sorted(staging_dir.iterdir(), key=lambda path: path.name):
        if staging_path.name == "quarantine":
            continue
        if quarantine:
            quarantine_root.mkdir(parents=True, exist_ok=True)
            destination_path = _unique_destination_path(quarantine_root / staging_path.name)
            staging_path.replace(destination_path)
            cleanup_results.append(destination_path)
            continue

        if staging_path.is_dir():
            shutil.rmtree(staging_path)
        else:
            staging_path.unlink(missing_ok=True)
        cleanup_results.append(staging_path)
    return cleanup_results


def _backup_replaced_index(sqlite_path: Path, *, suffix: str) -> Path:
    """Move a replaced SQLite index aside using a timestamped suffix."""

    backup_path = sqlite_path.with_name(f"{sqlite_path.name}.{suffix}-{_timestamp_label()}.bak")
    sqlite_path.replace(backup_path)
    return backup_path


def _unique_destination_path(destination_path: Path) -> Path:
    """Return a unique destination path for staging quarantine artifacts."""

    if not destination_path.exists():
        return destination_path
    stem = destination_path.stem
    suffix = destination_path.suffix
    counter = 1
    while True:
        candidate = destination_path.with_name(f"{stem}-{counter}{suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def _timestamp_label() -> str:
    """Return a filesystem-friendly UTC timestamp label."""

    return datetime.now(UTC).replace(microsecond=0).strftime("%Y%m%dT%H%M%SZ")


def _ensure_mailbox_placeholder_dirs(mailbox_path: Path) -> None:
    """Ensure the standard mailbox placeholder directories exist."""

    for directory_name in _MAILBOX_PLACEHOLDER_DIRS:
        (mailbox_path / directory_name).mkdir(parents=True, exist_ok=True)


def _unique_mailbox_principals(
    principals: Sequence[MailboxPrincipal],
) -> tuple[MailboxPrincipal, ...]:
    """Deduplicate canonical mailbox principals by principal id."""

    ordered: dict[str, MailboxPrincipal] = {}
    for principal in principals:
        existing = ordered.get(principal.principal_id)
        if existing is not None and existing.address != principal.address:
            raise ManagedMailboxOperationError(
                f"conflicting addresses for principal `{principal.principal_id}`"
            )
        ordered.setdefault(principal.principal_id, principal)
    return tuple(ordered.values())


def _parse_object_mapping(payload: object, *, field_name: str) -> dict[str, object]:
    """Require a JSON object payload."""

    if not isinstance(payload, dict):
        raise ManagedMailboxOperationError(f"{field_name} must be a mapping")
    return dict(payload)


def _parse_message_id_list(payload: object) -> tuple[str, ...]:
    """Parse and validate a list of message ids."""

    if not isinstance(payload, list):
        raise ManagedMailboxOperationError("references must be an array")
    return tuple(_validate_message_id(_require_str({"value": item}, "value")) for item in payload)


def _validate_message_id(value: str) -> str:
    """Validate canonical mailbox message-id formatting."""

    if not _MESSAGE_ID_PATTERN.fullmatch(value):
        raise ManagedMailboxOperationError(
            "message_id must match msg-{YYYYMMDDTHHMMSSZ}-{uuid4-no-dashes}"
        )
    return value


def _validate_optional_message_id(value: object) -> str | None:
    """Validate an optional message id payload field."""

    if value is None:
        return None
    if not isinstance(value, str):
        raise ManagedMailboxOperationError("optional message ids must be strings when present")
    return _validate_message_id(value)


def _normalize_timestamp(value: str) -> str:
    """Normalize a UTC timestamp to RFC3339 seconds precision."""

    if not value.endswith("Z"):
        raise ManagedMailboxOperationError("created_at_utc must end in Z")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ManagedMailboxOperationError(
            "created_at_utc must be a valid RFC3339 UTC timestamp"
        ) from exc
    if parsed.tzinfo is None:
        raise ManagedMailboxOperationError("created_at_utc must be timezone-aware")
    return parsed.astimezone(UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def _require_str(payload: dict[str, object], key: str) -> str:
    """Require a non-empty string field from a JSON mapping."""

    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ManagedMailboxOperationError(f"missing string field `{key}`")
    return value.strip()


def _optional_str(value: object, *, field_name: str) -> str | None:
    """Validate an optional string payload field."""

    if value is None:
        return None
    if not isinstance(value, str):
        raise ManagedMailboxOperationError(f"{field_name} must be a string when present")
    stripped = value.strip()
    if not stripped:
        raise ManagedMailboxOperationError(f"{field_name} must not be empty")
    return stripped


def _optional_int(value: object, *, field_name: str) -> int | None:
    """Validate an optional integer payload field."""

    if value is None:
        return None
    if not isinstance(value, int):
        raise ManagedMailboxOperationError(f"{field_name} must be an integer when present")
    return value


def _optional_bool(value: object, *, field_name: str) -> bool | None:
    """Validate an optional boolean payload field."""

    if value is None:
        return None
    if not isinstance(value, bool):
        raise ManagedMailboxOperationError(f"{field_name} must be a boolean when present")
    return value
