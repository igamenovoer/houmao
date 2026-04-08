"""Filesystem mailbox bootstrap helpers and registration lookups."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path
import sqlite3
import stat

from houmao.mailbox.errors import MailboxBootstrapError
from houmao.mailbox.protocol import (
    MAILBOX_PROTOCOL_VERSION,
    MailboxPrincipal,
    mailbox_address_path_segment,
)

_PROTOCOL_VERSION_FILENAME = "protocol-version.txt"
_SQLITE_JOURNAL_MODE = "DELETE"
_LOCAL_SQLITE_FILENAME = "mailbox.sqlite"
_MAILBOX_PLACEHOLDER_DIRS = ("inbox", "sent", "archive", "drafts")
_STASHED_ENTRY_SUFFIX_LENGTH = 32

_REGISTRATION_SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS mailbox_registrations (
        registration_id TEXT PRIMARY KEY,
        address TEXT NOT NULL,
        owner_principal_id TEXT NOT NULL,
        status TEXT NOT NULL CHECK (status IN ('active', 'inactive', 'stashed')),
        mailbox_kind TEXT NOT NULL CHECK (mailbox_kind IN ('in_root', 'symlink')),
        mailbox_path TEXT NOT NULL,
        mailbox_entry_path TEXT NOT NULL,
        display_name TEXT,
        manifest_path_hint TEXT,
        role TEXT,
        created_at_utc TEXT NOT NULL,
        deactivated_at_utc TEXT,
        replaced_by_registration_id TEXT,
        FOREIGN KEY (replaced_by_registration_id)
            REFERENCES mailbox_registrations(registration_id)
            ON DELETE SET NULL
    )
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS idx_mailbox_registrations_active_address
    ON mailbox_registrations(address)
    WHERE status = 'active'
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_mailbox_registrations_owner_principal
    ON mailbox_registrations(owner_principal_id)
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
        headers_json TEXT NOT NULL DEFAULT '{}',
        sender_principal_id TEXT NOT NULL,
        sender_address TEXT NOT NULL,
        sender_display_name TEXT,
        sender_manifest_path_hint TEXT,
        sender_role TEXT,
        sender_registration_id TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS message_recipients (
        message_id TEXT NOT NULL,
        recipient_kind TEXT NOT NULL,
        ordinal INTEGER NOT NULL,
        address TEXT NOT NULL,
        owner_principal_id TEXT NOT NULL,
        display_name TEXT,
        manifest_path_hint TEXT,
        role TEXT,
        delivered_registration_id TEXT,
        PRIMARY KEY (message_id, recipient_kind, ordinal),
        FOREIGN KEY (message_id) REFERENCES messages(message_id) ON DELETE CASCADE
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
        registration_id TEXT NOT NULL,
        message_id TEXT NOT NULL,
        folder_name TEXT NOT NULL,
        projection_path TEXT NOT NULL,
        PRIMARY KEY (registration_id, message_id, folder_name),
        FOREIGN KEY (registration_id)
            REFERENCES mailbox_registrations(registration_id)
            ON DELETE CASCADE,
        FOREIGN KEY (message_id) REFERENCES messages(message_id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS mailbox_state (
        registration_id TEXT NOT NULL,
        message_id TEXT NOT NULL,
        is_read INTEGER NOT NULL DEFAULT 0,
        is_starred INTEGER NOT NULL DEFAULT 0,
        is_archived INTEGER NOT NULL DEFAULT 0,
        is_deleted INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (registration_id, message_id),
        FOREIGN KEY (registration_id)
            REFERENCES mailbox_registrations(registration_id)
            ON DELETE CASCADE,
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
    "CREATE INDEX IF NOT EXISTS idx_recipients_address ON message_recipients(address)",
    "CREATE INDEX IF NOT EXISTS idx_state_registration_id ON mailbox_state(registration_id)",
)

_LOCAL_STATE_SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS message_state (
        message_id TEXT PRIMARY KEY,
        thread_id TEXT NOT NULL,
        created_at_utc TEXT NOT NULL,
        subject TEXT NOT NULL,
        is_read INTEGER NOT NULL DEFAULT 0,
        is_starred INTEGER NOT NULL DEFAULT 0,
        is_archived INTEGER NOT NULL DEFAULT 0,
        is_deleted INTEGER NOT NULL DEFAULT 0
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
    "CREATE INDEX IF NOT EXISTS idx_message_state_thread_id ON message_state(thread_id)",
)


@dataclass(frozen=True)
class MailboxRegistration:
    """Registration metadata loaded from the mailbox index."""

    registration_id: str
    address: str
    owner_principal_id: str
    status: str
    mailbox_kind: str
    mailbox_path: Path
    mailbox_entry_path: Path
    display_name: str | None
    manifest_path_hint: str | None
    role: str | None
    created_at_utc: str
    deactivated_at_utc: str | None
    replaced_by_registration_id: str | None

    @property
    def local_sqlite_path(self) -> Path:
        """Return the mailbox-local SQLite path for this registration."""

        return mailbox_local_sqlite_path(self.mailbox_path)


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
    address_locks_dir: Path
    messages_dir: Path
    attachments_managed_dir: Path
    mailboxes_dir: Path
    staging_dir: Path

    def mailbox_entry_path(self, address: str) -> Path:
        """Return the shared-root mailbox entry for an address."""

        return self.mailboxes_dir / mailbox_address_path_segment(address)

    def stashed_mailbox_entry_path(self, address: str, suffix: str) -> Path:
        """Return the shared-root path for a stashed mailbox artifact."""

        return self.mailboxes_dir / f"{mailbox_address_path_segment(address)}--{suffix}"

    def address_lock_path(self, address: str) -> Path:
        """Return the shared address-scoped lock path."""

        return self.address_locks_dir / f"{mailbox_address_path_segment(address)}.lock"


def mailbox_local_sqlite_path(mailbox_dir: Path) -> Path:
    """Return the stable mailbox-local SQLite path for one mailbox directory."""

    return mailbox_dir.resolve() / _LOCAL_SQLITE_FILENAME


def resolve_filesystem_mailbox_paths(mailbox_root: Path) -> FilesystemMailboxPaths:
    """Resolve canonical filesystem mailbox paths."""

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
        address_locks_dir=root / "locks" / "addresses",
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
    """Create or validate a filesystem mailbox root."""

    paths = resolve_filesystem_mailbox_paths(mailbox_root)
    reason = unsupported_mailbox_root_reason(paths.root)
    if reason is not None:
        raise MailboxBootstrapError(reason)

    _ensure_directory_layout(paths)
    _ensure_protocol_version(paths.protocol_version_file)
    materialize_managed_rules_assets(paths)
    initialize_sqlite_schema(paths.sqlite_path)

    from houmao.mailbox.managed import ensure_operator_mailbox_registration

    ensure_operator_mailbox_registration(paths.root)

    if principal is not None:
        from houmao.mailbox.managed import RegisterMailboxRequest, register_mailbox

        register_mailbox(
            paths.root,
            RegisterMailboxRequest(
                mode="safe",
                address=principal.address,
                owner_principal_id=principal.principal_id,
                mailbox_kind="in_root",
                mailbox_path=paths.mailbox_entry_path(principal.address),
                display_name=principal.display_name,
                manifest_path_hint=principal.manifest_path_hint,
                role=principal.role,
            ),
        )

    from houmao.mailbox.managed import ensure_mailbox_local_state

    ensure_mailbox_local_state(paths.root)

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


def initialize_sqlite_schema(sqlite_path: Path) -> None:
    """Create or validate the filesystem mailbox SQLite schema."""

    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(sqlite_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(f"PRAGMA journal_mode={_SQLITE_JOURNAL_MODE}")
        for statement in _REGISTRATION_SCHEMA_STATEMENTS:
            connection.execute(statement)
        connection.commit()


def initialize_mailbox_local_sqlite_schema(sqlite_path: Path) -> None:
    """Create or validate the mailbox-local SQLite schema."""

    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(sqlite_path) as connection:
        connection.execute(f"PRAGMA journal_mode={_SQLITE_JOURNAL_MODE}")
        for statement in _LOCAL_STATE_SCHEMA_STATEMENTS:
            connection.execute(statement)
        connection.commit()


def materialize_managed_rules_assets(paths: FilesystemMailboxPaths) -> None:
    """Copy managed mailbox `rules/` assets into the target mailbox root."""

    source_root = resources.files("houmao.mailbox.assets") / "rules"
    _copy_resource_tree(source_root, paths.rules_dir)


def unsupported_mailbox_root_reason(mailbox_root: Path) -> str | None:
    """Return a stale-root error message when a mailbox root is unsupported."""

    root = mailbox_root.resolve()
    if not root.exists():
        return None

    legacy_lock_dir = root / "locks" / "principals"
    if legacy_lock_dir.exists():
        return _stale_root_message(root, "legacy principal-scoped lock directory detected")

    sqlite_path = root / "index.sqlite"
    if sqlite_path.exists():
        try:
            with sqlite3.connect(sqlite_path) as connection:
                table_rows = connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
        except sqlite3.DatabaseError:
            return _stale_root_message(
                root,
                "mailbox index is unreadable and cannot be reused safely",
            )

        table_names = {str(row[0]) for row in table_rows}
        if "principals" in table_names:
            return _stale_root_message(root, "legacy principal-scoped mailbox schema detected")

    mailboxes_dir = root / "mailboxes"
    if mailboxes_dir.exists():
        try:
            entries = list(mailboxes_dir.iterdir())
        except OSError:
            entries = []
        for entry in entries:
            if _parse_mailbox_entry_name(entry.name) is None:
                return _stale_root_message(
                    root,
                    f"unsupported mailbox entry `{entry.name}` detected",
                )

    return None


def load_active_mailbox_registration(
    mailbox_root: Path,
    *,
    address: str,
) -> MailboxRegistration:
    """Load the active registration for one mailbox address."""

    paths = resolve_filesystem_mailbox_paths(mailbox_root)
    reason = unsupported_mailbox_root_reason(paths.root)
    if reason is not None:
        raise MailboxBootstrapError(reason)
    read_protocol_version(paths.protocol_version_file)

    if not paths.sqlite_path.exists():
        raise MailboxBootstrapError(f"missing mailbox index: {paths.sqlite_path}")

    with sqlite3.connect(paths.sqlite_path) as connection:
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
            """,
            (mailbox_address_path_segment(address),),
        ).fetchone()

    if row is None:
        raise MailboxBootstrapError(
            f"no active mailbox registration exists for `{mailbox_address_path_segment(address)}`"
        )
    return _row_to_mailbox_registration(row)


def resolve_active_mailbox_inbox_dir(mailbox_root: Path, *, address: str) -> Path:
    """Resolve the concrete inbox path for an active mailbox registration."""

    normalized_address = mailbox_address_path_segment(address)
    paths = resolve_filesystem_mailbox_paths(mailbox_root)
    reason = unsupported_mailbox_root_reason(paths.root)
    if reason is not None:
        raise MailboxBootstrapError(reason)

    if not paths.protocol_version_file.exists() or not paths.sqlite_path.exists():
        return paths.mailbox_entry_path(normalized_address) / "inbox"

    registration = load_active_mailbox_registration(paths.root, address=normalized_address)
    return registration.mailbox_path / "inbox"


def resolve_active_mailbox_dir(mailbox_root: Path, *, address: str) -> Path:
    """Resolve the concrete mailbox directory for an active mailbox registration."""

    normalized_address = mailbox_address_path_segment(address)
    paths = resolve_filesystem_mailbox_paths(mailbox_root)
    reason = unsupported_mailbox_root_reason(paths.root)
    if reason is not None:
        raise MailboxBootstrapError(reason)

    if not paths.protocol_version_file.exists() or not paths.sqlite_path.exists():
        return paths.mailbox_entry_path(normalized_address)

    registration = load_active_mailbox_registration(paths.root, address=normalized_address)
    return registration.mailbox_path


def resolve_active_mailbox_local_sqlite_path(mailbox_root: Path, *, address: str) -> Path:
    """Resolve the concrete mailbox-local SQLite path for an active registration."""

    return mailbox_local_sqlite_path(resolve_active_mailbox_dir(mailbox_root, address=address))


def _copy_resource_tree(source_root: Traversable, destination_root: Path) -> None:
    """Copy packaged text resources into the mailbox rules tree."""

    for child in source_root.iterdir():
        if child.name == "__pycache__" or child.name.endswith(".pyc"):
            continue
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


def _ensure_directory_layout(paths: FilesystemMailboxPaths) -> None:
    """Create the base directory layout for a filesystem mailbox."""

    directory_paths = (
        paths.root,
        paths.rules_dir,
        paths.rules_protocols_dir,
        paths.rules_scripts_dir,
        paths.rules_skills_dir,
        paths.locks_dir,
        paths.address_locks_dir,
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


def _parse_mailbox_entry_name(entry_name: str) -> tuple[str, str] | None:
    """Parse one mailbox entry name into `(address, status)`."""

    try:
        return (mailbox_address_path_segment(entry_name), "active")
    except Exception:
        if "--" not in entry_name:
            return None

    address_part, suffix = entry_name.rsplit("--", 1)
    if len(suffix) != _STASHED_ENTRY_SUFFIX_LENGTH or any(
        character not in "0123456789abcdef" for character in suffix
    ):
        return None
    try:
        return (mailbox_address_path_segment(address_part), "stashed")
    except Exception:
        return None


def _row_to_mailbox_registration(row: tuple[object, ...]) -> MailboxRegistration:
    """Convert a SQLite row into one registration record."""

    return MailboxRegistration(
        registration_id=str(row[0]),
        address=str(row[1]),
        owner_principal_id=str(row[2]),
        status=str(row[3]),
        mailbox_kind=str(row[4]),
        mailbox_path=Path(str(row[5])),
        mailbox_entry_path=Path(str(row[6])),
        display_name=None if row[7] is None else str(row[7]),
        manifest_path_hint=None if row[8] is None else str(row[8]),
        role=None if row[9] is None else str(row[9]),
        created_at_utc=str(row[10]),
        deactivated_at_utc=None if row[11] is None else str(row[11]),
        replaced_by_registration_id=None if row[12] is None else str(row[12]),
    )


def _stale_root_message(root: Path, detail: str) -> str:
    """Build a direct operator-facing stale-root error message."""

    return (
        f"unsupported stale mailbox root at `{root}`: {detail}. "
        "Delete this mailbox root and re-bootstrap it with the current address-routed v1 layout."
    )
