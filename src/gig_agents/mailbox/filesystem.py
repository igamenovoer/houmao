"""Filesystem mailbox bootstrap helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path
import sqlite3
import stat

from gig_agents.mailbox.errors import MailboxBootstrapError
from gig_agents.mailbox.protocol import MAILBOX_PROTOCOL_VERSION, MailboxPrincipal

_PROTOCOL_VERSION_FILENAME = "protocol-version.txt"
_SQLITE_JOURNAL_MODE = "DELETE"
_MAILBOX_PLACEHOLDER_DIRS = ("inbox", "sent", "archive", "drafts")

_SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS principals (
        principal_id TEXT PRIMARY KEY,
        address TEXT NOT NULL,
        display_name TEXT,
        manifest_path_hint TEXT,
        role TEXT,
        mailbox_kind TEXT NOT NULL,
        mailbox_path TEXT NOT NULL,
        created_at_utc TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS messages (
        message_id TEXT PRIMARY KEY,
        thread_id TEXT NOT NULL,
        in_reply_to TEXT,
        created_at_utc TEXT NOT NULL,
        canonical_path TEXT NOT NULL,
        subject TEXT NOT NULL,
        body_markdown TEXT NOT NULL,
        headers_json TEXT NOT NULL DEFAULT '{}'
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS message_recipients (
        message_id TEXT NOT NULL,
        principal_id TEXT NOT NULL,
        recipient_kind TEXT NOT NULL,
        ordinal INTEGER NOT NULL,
        PRIMARY KEY (message_id, principal_id, recipient_kind),
        FOREIGN KEY (message_id) REFERENCES messages(message_id) ON DELETE CASCADE,
        FOREIGN KEY (principal_id) REFERENCES principals(principal_id) ON DELETE RESTRICT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS attachments (
        attachment_id TEXT PRIMARY KEY,
        kind TEXT NOT NULL,
        locator TEXT NOT NULL,
        media_type TEXT NOT NULL,
        sha256 TEXT,
        size_bytes INTEGER,
        label TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS message_attachments (
        message_id TEXT NOT NULL,
        attachment_id TEXT NOT NULL,
        ordinal INTEGER NOT NULL,
        PRIMARY KEY (message_id, attachment_id),
        FOREIGN KEY (message_id) REFERENCES messages(message_id) ON DELETE CASCADE,
        FOREIGN KEY (attachment_id) REFERENCES attachments(attachment_id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS mailbox_projections (
        principal_id TEXT NOT NULL,
        message_id TEXT NOT NULL,
        folder_name TEXT NOT NULL,
        projection_path TEXT NOT NULL,
        PRIMARY KEY (principal_id, message_id, folder_name),
        FOREIGN KEY (principal_id) REFERENCES principals(principal_id) ON DELETE CASCADE,
        FOREIGN KEY (message_id) REFERENCES messages(message_id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS mailbox_state (
        principal_id TEXT NOT NULL,
        message_id TEXT NOT NULL,
        is_read INTEGER NOT NULL DEFAULT 0,
        is_starred INTEGER NOT NULL DEFAULT 0,
        is_archived INTEGER NOT NULL DEFAULT 0,
        is_deleted INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (principal_id, message_id),
        FOREIGN KEY (principal_id) REFERENCES principals(principal_id) ON DELETE CASCADE,
        FOREIGN KEY (message_id) REFERENCES messages(message_id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS thread_summaries (
        thread_id TEXT PRIMARY KEY,
        normalized_subject TEXT NOT NULL,
        latest_message_id TEXT,
        latest_message_created_at_utc TEXT,
        unread_count INTEGER NOT NULL DEFAULT 0
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_messages_thread_id ON messages(thread_id)",
    "CREATE INDEX IF NOT EXISTS idx_recipients_principal_id ON message_recipients(principal_id)",
    "CREATE INDEX IF NOT EXISTS idx_state_principal_id ON mailbox_state(principal_id)",
)


@dataclass(frozen=True)
class FilesystemMailboxPaths:
    """Resolved filesystem mailbox paths."""

    root: Path
    protocol_version_file: Path
    sqlite_path: Path
    rules_dir: Path
    rules_protocols_dir: Path
    rules_scripts_dir: Path
    rules_skills_dir: Path
    locks_dir: Path
    principal_locks_dir: Path
    messages_dir: Path
    attachments_managed_dir: Path
    mailboxes_dir: Path
    staging_dir: Path

    def principal_mailbox_dir(self, principal_id: str) -> Path:
        """Return the mailbox directory for an in-root principal."""

        return self.mailboxes_dir / principal_id


def resolve_filesystem_mailbox_paths(mailbox_root: Path) -> FilesystemMailboxPaths:
    """Resolve canonical filesystem mailbox paths.

    Parameters
    ----------
    mailbox_root:
        Root directory of the filesystem mailbox.

    Returns
    -------
    FilesystemMailboxPaths
        Canonical paths rooted at ``mailbox_root``.
    """

    root = mailbox_root.resolve()
    rules_dir = root / "rules"
    return FilesystemMailboxPaths(
        root=root,
        protocol_version_file=root / _PROTOCOL_VERSION_FILENAME,
        sqlite_path=root / "index.sqlite",
        rules_dir=rules_dir,
        rules_protocols_dir=rules_dir / "protocols",
        rules_scripts_dir=rules_dir / "scripts",
        rules_skills_dir=rules_dir / "skills",
        locks_dir=root / "locks",
        principal_locks_dir=root / "locks" / "principals",
        messages_dir=root / "messages",
        attachments_managed_dir=root / "attachments" / "managed",
        mailboxes_dir=root / "mailboxes",
        staging_dir=root / "staging",
    )


def bootstrap_filesystem_mailbox(
    mailbox_root: Path,
    *,
    principal: MailboxPrincipal | None = None,
) -> FilesystemMailboxPaths:
    """Create or validate a filesystem mailbox root.

    Parameters
    ----------
    mailbox_root:
        Target mailbox root.
    principal:
        Optional in-root principal to register during bootstrap.

    Returns
    -------
    FilesystemMailboxPaths
        Resolved mailbox paths for the bootstrapped root.
    """

    paths = resolve_filesystem_mailbox_paths(mailbox_root)
    _ensure_directory_layout(paths)
    _ensure_protocol_version(paths.protocol_version_file)
    materialize_managed_rules_assets(paths)
    initialize_sqlite_schema(paths.sqlite_path)

    if principal is not None:
        _register_in_root_principal(paths, principal)

    return paths


def read_protocol_version(protocol_version_file: Path) -> int:
    """Read and validate the mailbox on-disk protocol version."""

    try:
        raw_value = protocol_version_file.read_text(encoding="utf-8").strip()
    except FileNotFoundError as exc:
        raise MailboxBootstrapError(
            f"missing protocol version file: {protocol_version_file}"
        ) from exc

    if raw_value != str(MAILBOX_PROTOCOL_VERSION):
        raise MailboxBootstrapError(
            "unsupported mailbox protocol version: "
            f"expected {MAILBOX_PROTOCOL_VERSION}, found {raw_value or '<empty>'}"
        )
    return MAILBOX_PROTOCOL_VERSION


def _ensure_directory_layout(paths: FilesystemMailboxPaths) -> None:
    """Create the base directory layout for a filesystem mailbox."""

    directory_paths = (
        paths.root,
        paths.rules_dir,
        paths.rules_protocols_dir,
        paths.rules_scripts_dir,
        paths.rules_skills_dir,
        paths.locks_dir,
        paths.principal_locks_dir,
        paths.messages_dir,
        paths.attachments_managed_dir,
        paths.mailboxes_dir,
        paths.staging_dir,
    )
    for path in directory_paths:
        path.mkdir(parents=True, exist_ok=True)


def _ensure_protocol_version(protocol_version_file: Path) -> None:
    """Create or validate the mailbox protocol-version file."""

    if protocol_version_file.exists():
        read_protocol_version(protocol_version_file)
        return
    protocol_version_file.write_text(f"{MAILBOX_PROTOCOL_VERSION}\n", encoding="utf-8")


def initialize_sqlite_schema(sqlite_path: Path) -> None:
    """Create or validate the filesystem mailbox SQLite schema."""

    with sqlite3.connect(sqlite_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(f"PRAGMA journal_mode={_SQLITE_JOURNAL_MODE}")
        for statement in _SCHEMA_STATEMENTS:
            connection.execute(statement)
        connection.commit()


def materialize_managed_rules_assets(paths: FilesystemMailboxPaths) -> None:
    """Copy managed mailbox `rules/` assets into the target mailbox root.

    Parameters
    ----------
    paths:
        Resolved filesystem mailbox paths.
    """

    source_root = resources.files("gig_agents.mailbox.assets") / "rules"
    _copy_resource_tree(source_root, paths.rules_dir)


def _copy_resource_tree(source_root: Traversable, destination_root: Path) -> None:
    """Copy packaged text resources into the mailbox rules tree."""

    for child in source_root.iterdir():
        destination_path = destination_root / child.name
        if child.is_dir():
            destination_path.mkdir(parents=True, exist_ok=True)
            _copy_resource_tree(child, destination_path)
            continue

        destination_path.parent.mkdir(parents=True, exist_ok=True)
        destination_path.write_text(child.read_text(encoding="utf-8"), encoding="utf-8")
        if destination_path.suffix == ".py":
            destination_path.chmod(
                destination_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
            )


def _register_in_root_principal(
    paths: FilesystemMailboxPaths,
    principal: MailboxPrincipal,
) -> None:
    """Register an in-root principal mailbox in SQLite and on disk."""

    principal_root = paths.principal_mailbox_dir(principal.principal_id)
    for directory_name in _MAILBOX_PLACEHOLDER_DIRS:
        (principal_root / directory_name).mkdir(parents=True, exist_ok=True)

    mailbox_path = str(principal_root)
    created_at_utc = datetime.now(UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")

    with sqlite3.connect(paths.sqlite_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        existing_row = connection.execute(
            """
            SELECT address, mailbox_kind, mailbox_path
            FROM principals
            WHERE principal_id = ?
            """,
            (principal.principal_id,),
        ).fetchone()

        if existing_row is not None:
            existing_address, existing_kind, existing_path = existing_row
            if existing_kind != "in_root" or existing_path != mailbox_path:
                raise MailboxBootstrapError(
                    f"principal `{principal.principal_id}` is already registered at a different mailbox path"
                )
            if existing_address != principal.address:
                raise MailboxBootstrapError(
                    f"principal `{principal.principal_id}` is already registered with a different address"
                )
            return

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
                principal.principal_id,
                principal.address,
                principal.display_name,
                principal.manifest_path_hint,
                principal.role,
                "in_root",
                mailbox_path,
                created_at_utc,
            ),
        )
        connection.commit()
