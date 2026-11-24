"""Persist current gateway policy and its owner-side authorization fence."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import closing, contextmanager
import hashlib
import os
from pathlib import Path
import sqlite3
import time
from uuid import uuid4

from pydantic import TypeAdapter, ValidationError

from houmao.gateway._access_storage import (
    GatewayAccessError,
    _file_lock,
    _private_directory,
    _read_file,
    _require_private_file,
    _write_file,
)
from houmao.gateway.access_models import GatewayOwner, MAX_ACCESS_DOCUMENT, parse_access_document
from houmao.gateway.authorization_models import (
    Action,
    AuthorizationAuditEntry,
    AuthorizationDecision,
    Credential,
    Identifier,
    PolicySnapshot,
)

_DATABASE = "authorization.sqlite3"
_INITIALIZED = ".authorization-initialized"
_INITIALIZATION_LOCK = ".authorization-initialize.lock"
_DATABASE_VERSION = 1
_APPLICATION_ID = 0x484D415A
_AUDIT_READ_LIMIT = 1024
_IDENTIFIER = TypeAdapter(Identifier)
_ACTION = TypeAdapter(Action)
_DEFINITION = (
    """CREATE TABLE policy (
        singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
        payload BLOB NOT NULL
    )""",
    """CREATE TABLE audit (
        event_id INTEGER PRIMARY KEY,
        recorded_at INTEGER NOT NULL,
        actor TEXT NOT NULL,
        action TEXT NOT NULL,
        operation_id TEXT,
        policy_revision INTEGER NOT NULL
    )""",
    """CREATE TABLE handoffs (
        operation_id TEXT PRIMARY KEY,
        decision BLOB NOT NULL
    )""",
)


class AuthorizationTransaction:
    """Expose a consistent policy revision inside a short owner-side write fence."""

    def __init__(self, connection: sqlite3.Connection, snapshot: PolicySnapshot) -> None:
        """Bind this transaction to the open database and its validated policy."""

        self.m_connection: sqlite3.Connection = connection
        self.m_snapshot: PolicySnapshot = snapshot

    @property
    def snapshot(self) -> PolicySnapshot:
        """Return the validated policy visible to this transaction."""

        return self.m_snapshot

    def replace(
        self,
        candidate: PolicySnapshot,
        *,
        actor: str,
        action: str,
        operation_id: str | None = None,
    ) -> PolicySnapshot:
        """Commit policy rows and their audit evidence under the same writer lock."""

        try:
            updated = _advance_policy(self.m_snapshot, candidate)
        except ValidationError:
            raise GatewayAccessError(422, "invalid_policy") from None
        self.m_connection.execute(
            "UPDATE policy SET payload = ? WHERE singleton = 1", (_encode_policy(updated),)
        )
        self.m_snapshot = updated
        self._audit(actor, action, operation_id)
        return updated

    def record_handoff(self, operation_id: str, decision: AuthorizationDecision) -> None:
        """Persist a fresh authorization handoff exactly once before releasing the fence."""

        operation_id = _IDENTIFIER.validate_python(operation_id)
        if (
            decision.target.owner != self.m_snapshot.owner
            or decision.policy_id != self.m_snapshot.policy_id
            or decision.policy_revision != self.m_snapshot.revision
        ):
            raise GatewayAccessError(409, "authorization_handoff_conflict")
        inserted = self.m_connection.execute(
            "INSERT OR IGNORE INTO handoffs (operation_id, decision) VALUES (?, ?)",
            (operation_id, decision.model_dump_json().encode()),
        )
        if inserted.rowcount != 1:
            raise GatewayAccessError(409, "authorization_handoff_conflict")
        self._audit(decision.actor.principal_id or "anonymous", "operation.handoff", operation_id)

    def _audit(self, actor: str, action: str, operation_id: str | None) -> None:
        """Store bounded provenance without proof, paths, or request content."""

        self.m_connection.execute(
            """INSERT INTO audit (recorded_at, actor, action, operation_id, policy_revision)
               VALUES (?, ?, ?, ?, ?)""",
            (
                int(time.time()),
                _IDENTIFIER.validate_python(actor),
                _ACTION.validate_python(action),
                _IDENTIFIER.validate_python(operation_id) if operation_id is not None else None,
                self.m_snapshot.revision,
            ),
        )


class AuthorizationStore:
    """Maintain one versioned SQLite policy in a selected owner-private directory."""

    def __init__(self, root: Path, owner: GatewayOwner) -> None:
        """Select retained state for a verified owner without initializing it."""

        self.m_root: Path = root
        self.m_owner: GatewayOwner = owner
        owner_digest = hashlib.sha256(owner.model_dump_json().encode()).hexdigest()
        self.m_marker: bytes = f"houmao-gateway-authorization-v1 {owner_digest}\n".encode()
        self.m_retired_entries: tuple[str, str] = (owner_digest, f"{owner_digest}.initialized")

    @property
    def owner(self) -> GatewayOwner:
        """Return the domain to which all records must belong."""

        return self.m_owner

    def initialize(
        self, seed: PolicySnapshot | None = None, *, allow_retired: bool = False
    ) -> PolicySnapshot:
        """Explicitly provision a new policy or return its already-initialized state."""

        if seed is None:
            seed = PolicySnapshot(owner=self.m_owner)
        if (
            seed.owner != self.m_owner
            or seed.revision != 0
            or seed.roster_revision != 0
            or seed.open_epoch != 0
        ):
            raise GatewayAccessError(422, "invalid_policy_seed")
        try:
            seed = parse_access_document(PolicySnapshot, _encode_policy(seed))
        except ValueError:
            raise GatewayAccessError(422, "invalid_policy_seed") from None
        try:
            with _private_directory(self.m_root, create=True) as directory:
                with _file_lock(directory, _INITIALIZATION_LOCK, create=True):
                    try:
                        self._require_marker(directory)
                    except FileNotFoundError:
                        if not allow_retired and self._has_retired_entry(directory):
                            raise GatewayAccessError(503, "retired_policy_requires_owner_init")
                        self._initialize_database(directory, seed)
                        return seed
                    return self.snapshot()
        except (OSError, sqlite3.Error, ValueError):
            raise GatewayAccessError(503, "policy_unavailable") from None

    def snapshot(self) -> PolicySnapshot:
        """Read and validate the latest committed policy independently of a live gateway."""

        with self._open() as connection:
            return self._snapshot(connection)

    def handoff_evidence(self, operation_id: str) -> AuthorizationDecision | None:
        """Read a committed handoff without claiming or replaying the operation."""

        operation_id = _IDENTIFIER.validate_python(operation_id)
        with self._open() as connection:
            row = connection.execute(
                "SELECT decision FROM handoffs WHERE operation_id = ?", (operation_id,)
            ).fetchone()
            if row is None:
                return None
            return parse_access_document(AuthorizationDecision, row["decision"])

    @contextmanager
    def transaction(self) -> Iterator[AuthorizationTransaction]:
        """Order policy mutation and accepted handoff under the same database writer lock."""

        with self._open() as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            yield AuthorizationTransaction(connection, self._snapshot(connection))

    def update(
        self,
        transform: Callable[[PolicySnapshot], PolicySnapshot],
        *,
        actor: str,
        action: str,
        expected_revision: int | None = None,
        operation_id: str | None = None,
    ) -> PolicySnapshot:
        """Transform the current policy atomically with optional revision comparison."""

        with self.transaction() as transaction:
            current = transaction.snapshot
            if expected_revision is not None and expected_revision != current.revision:
                raise GatewayAccessError(409, "policy_revision_conflict")
            try:
                candidate = transform(current)
            except ValidationError:
                raise GatewayAccessError(422, "invalid_policy") from None
            return transaction.replace(
                candidate, actor=actor, action=action, operation_id=operation_id
            )

    def audit_entries(self, *, limit: int = 100) -> tuple[AuthorizationAuditEntry, ...]:
        """Read the latest bounded batch of safe owner audit records."""

        if not 1 <= limit <= _AUDIT_READ_LIMIT:
            raise ValueError("invalid audit read limit")
        with self._open() as connection, connection:
            connection.execute("BEGIN")
            self._snapshot(connection)
            cursor = connection.execute(
                """SELECT event_id, recorded_at, actor, action, operation_id, policy_revision
                   FROM audit ORDER BY event_id DESC LIMIT ?""",
                (limit,),
            )
            return tuple(AuthorizationAuditEntry.model_validate(dict(row)) for row in cursor)

    def _initialize_database(self, directory: int, seed: PolicySnapshot) -> None:
        """Create the only database for this binding before publishing its marker."""

        payload = _encode_policy(seed)
        os.close(
            os.open(
                _DATABASE,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW,
                0o600,
                dir_fd=directory,
            )
        )
        with _connect(directory) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            for definition in _DEFINITION:
                connection.execute(definition)
            connection.execute(f"PRAGMA application_id = {_APPLICATION_ID}")
            connection.execute(f"PRAGMA user_version = {_DATABASE_VERSION}")
            connection.execute("INSERT INTO policy VALUES (1, ?)", (payload,))
            connection.execute(
                """INSERT INTO audit (recorded_at, actor, action, policy_revision)
                   VALUES (?, 'owner', 'policy.initialize', 0)""",
                (int(time.time()),),
            )
        _write_file(directory, _INITIALIZED, self.m_marker)

    @contextmanager
    def _open(self) -> Iterator[sqlite3.Connection]:
        """Refuse missing, obsolete, unsafe, or foreign retained state."""

        try:
            with _private_directory(self.m_root) as directory:
                self._require_marker(directory)
                with _connect(directory) as connection:
                    if (
                        connection.execute("PRAGMA application_id").fetchone()[0] != _APPLICATION_ID
                        or connection.execute("PRAGMA user_version").fetchone()[0]
                        != _DATABASE_VERSION
                    ):
                        raise ValueError("invalid policy schema")
                    yield connection
        except (OSError, sqlite3.Error, ValueError):
            raise GatewayAccessError(503, "policy_unavailable") from None

    def _require_marker(self, directory: int) -> None:
        """Check the owner-bound marker separately from the mutable database."""

        if _read_file(directory, _INITIALIZED, len(self.m_marker)) != self.m_marker:
            raise ValueError("invalid policy initialization marker")

    def _has_retired_entry(self, directory: int) -> bool:
        """Detect earlier owner state without opening or parsing it."""

        for entry in self.m_retired_entries:
            try:
                os.stat(entry, dir_fd=directory, follow_symlinks=False)
            except FileNotFoundError:
                continue
            return True
        return False

    def _snapshot(self, connection: sqlite3.Connection) -> PolicySnapshot:
        """Load one bounded strict policy record and verify its owner."""

        row = connection.execute(
            "SELECT payload FROM policy WHERE singleton = 1 AND length(payload) <= ?",
            (MAX_ACCESS_DOCUMENT,),
        ).fetchone()
        if row is None or not isinstance(row["payload"], bytes):
            raise ValueError("policy document is unavailable")
        state = parse_access_document(PolicySnapshot, row["payload"])
        if state.owner != self.m_owner:
            raise ValueError("policy belongs to a different owner")
        return state


@contextmanager
def _connect(directory: int) -> Iterator[sqlite3.Connection]:
    """Open SQLite under the verified directory and reject unsafe state inodes."""

    _check_database_file(directory, _DATABASE, required=True)
    for suffix in ("-journal", "-wal", "-shm"):
        _check_database_file(directory, _DATABASE + suffix, required=False)
    # Resolve the database within the validated open directory, even if an
    # ancestor moves after validation.
    uri = f"file:/proc/self/fd/{directory}/{_DATABASE}?mode=rw"
    with closing(sqlite3.connect(uri, uri=True, timeout=2.0)) as connection:
        connection.execute("PRAGMA trusted_schema = OFF")
        connection.execute("PRAGMA synchronous = FULL")
        connection.row_factory = sqlite3.Row
        yield connection


def _check_database_file(directory: int, name: str, *, required: bool) -> None:
    """Check a database file or journal through a no-follow descriptor."""

    try:
        descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    except FileNotFoundError:
        if required:
            raise
    else:
        try:
            _require_private_file(descriptor)
        finally:
            os.close(descriptor)


def _advance_policy(before: PolicySnapshot, candidate: PolicySnapshot) -> PolicySnapshot:
    """Assign credential versions, roster revisions, and open-mode transition epochs."""

    if (candidate.owner, candidate.policy_id) != (before.owner, before.policy_id):
        raise GatewayAccessError(409, "policy_owner_conflict")
    revision = before.revision + 1
    previous = {key.enrollment_id: key for key in before.credentials}
    credentials = tuple(
        _advance_credential(key, previous.get(key.enrollment_id), revision)
        for key in candidate.credentials
    )
    old_admins = _admin_qualifications(before.credentials)
    new_admins = _admin_qualifications(credentials)
    updated = candidate.model_copy(
        update={
            "revision": revision,
            "roster_revision": before.roster_revision + (old_admins != new_admins),
            "open_epoch": before.open_epoch + (bool(old_admins) != bool(new_admins)),
            "credentials": credentials,
        }
    )
    return PolicySnapshot.model_validate_json(updated.model_dump_json())


def _advance_credential(key: Credential, previous: Credential | None, revision: int) -> Credential:
    """Retain live enrollment identity and allocate fresh qualification on change."""

    if previous is not None and (key.public_key, key.principal_id) != (
        previous.public_key,
        previous.principal_id,
    ):
        raise GatewayAccessError(409, "credential_binding_conflict")
    qualification = None
    if key.admin_revision is not None:
        qualification = previous.admin_revision if previous is not None else None
        if qualification is None:
            qualification = revision
    return key.model_copy(
        update={
            "enrollment_id": key.enrollment_id if previous is not None else uuid4().hex,
            "admin_revision": qualification,
        }
    )


def _admin_qualifications(keys: tuple[Credential, ...]) -> set[tuple[str, int]]:
    """Identify the live per-key admin enrollments that determine roster transitions."""

    return {
        (key.enrollment_id, key.admin_revision) for key in keys if key.admin_revision is not None
    }


def _encode_policy(state: PolicySnapshot) -> bytes:
    """Reject owner policy documents exceeding the retained size bound."""

    payload = state.model_dump_json().encode()
    if len(payload) > MAX_ACCESS_DOCUMENT:
        raise GatewayAccessError(413, "policy_too_large")
    return payload
