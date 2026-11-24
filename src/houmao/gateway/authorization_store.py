"""Persist current gateway policy and its owner-side authorization fence."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import closing, contextmanager
import hashlib
import os
from pathlib import Path
import sqlite3
import stat
import time
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat
from pydantic import TypeAdapter, ValidationError

from houmao.gateway._access_sshsig import public_key_text
from houmao.gateway._access_storage import (
    GatewayAccessError,
    _file_lock,
    _private_directory,
    _read_file,
    _require_private_file,
    _write_file,
)
from houmao.gateway.access_models import (
    GatewayOwner,
    GatewaySelfKey,
    MAX_ACCESS_DOCUMENT,
    parse_access_document,
)
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
_DATABASE_VERSION = 2
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
_SELF_DEFINITION = (
    """CREATE TABLE managed_self_registrations (
        generation_id TEXT NOT NULL,
        revision INTEGER NOT NULL CHECK (revision > 0),
        key_id TEXT NOT NULL,
        public_key TEXT NOT NULL,
        active INTEGER NOT NULL CHECK (active IN (0, 1)),
        PRIMARY KEY (generation_id, revision)
    )""",
    """CREATE INDEX managed_self_registration_keys
        ON managed_self_registrations (key_id)""",
    """CREATE UNIQUE INDEX managed_self_one_active
        ON managed_self_registrations (generation_id) WHERE active = 1""",
    """CREATE TABLE managed_self_keys (
        generation_id TEXT NOT NULL,
        key_id TEXT NOT NULL,
        private_key BLOB NOT NULL CHECK (length(private_key) = 32),
        PRIMARY KEY (generation_id, key_id)
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
        previous = {key.key_id for key in self.m_snapshot.credentials}
        for key in updated.credentials:
            if key.key_id not in previous and _registered_key(self.m_connection, key.key_id):
                raise GatewayAccessError(409, "self_credential_conflict")
        self.m_connection.execute(
            "UPDATE policy SET payload = ? WHERE singleton = 1", (_encode_policy(updated),)
        )
        self.m_snapshot = updated
        self._audit(actor, action, operation_id)
        return updated

    def load_self(self, generation_id: str) -> GatewaySelfKey | None:
        """Read the active public registration under the owner writer lock."""

        return _active_self(self.m_connection, self.m_snapshot.owner, generation_id)

    def self_revision(self, generation_id: str) -> int | None:
        """Return the latest registration revision, including revocation."""

        record = _self_registration(self.m_connection, self.m_snapshot.owner, generation_id)
        return record[0].registration_revision if record is not None else None

    def require_self_signer(self, binding: GatewaySelfKey) -> None:
        """Check that the active private record exists within this transaction."""

        if self.load_self(binding.generation_id) != binding:
            raise GatewayAccessError(503, "self_authorization_unavailable")
        _load_self_signer(self.m_connection, binding)

    def replace_self(
        self,
        generation_id: str,
        *,
        expected_revision: int | None,
        signer: Ed25519PrivateKey | None,
        actor: str,
    ) -> GatewaySelfKey:
        """Commit a verified candidate signer or record a revocation at the expected revision."""

        owner = self.m_snapshot.owner
        prior = _self_registration(self.m_connection, owner, generation_id)
        revision = prior[0].registration_revision if prior is not None else None
        if revision != expected_revision:
            raise GatewayAccessError(409, "self_registration_conflict")
        if signer is None and (prior is None or not prior[1]):
            raise GatewayAccessError(409, "self_registration_conflict")
        if signer is not None:
            public_key = public_key_text(signer.public_key())
        else:
            assert prior is not None
            public_key = prior[0].public_key
        binding = GatewaySelfKey(
            owner=owner,
            generation_id=generation_id,
            public_key=public_key,
            registration_revision=(revision or 0) + 1,
        )
        if signer is not None and (
            self.m_snapshot.find_credential(binding.key_id) is not None
            or _registered_key(self.m_connection, binding.key_id)
        ):
            raise GatewayAccessError(409, "self_credential_conflict")
        self.m_connection.execute(
            "UPDATE managed_self_registrations SET active = 0 WHERE generation_id = ? AND active = 1",
            (generation_id,),
        )
        self.m_connection.execute(
            "DELETE FROM managed_self_keys WHERE generation_id = ?", (generation_id,)
        )
        if signer is not None:
            self.m_connection.execute(
                "INSERT INTO managed_self_keys VALUES (?, ?, ?)",
                (
                    generation_id,
                    binding.key_id,
                    signer.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption()),
                ),
            )
        self.m_connection.execute(
            "INSERT INTO managed_self_registrations VALUES (?, ?, ?, ?, ?)",
            (
                generation_id,
                binding.registration_revision,
                binding.key_id,
                public_key,
                signer is not None,
            ),
        )
        action = (
            "self.revoke"
            if signer is None
            else "self.provision"
            if prior is None
            else "self.rotate"
        )
        self._audit(actor, action, generation_id)
        return binding

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

    def provision_self(self, generation_id: str) -> GatewaySelfKey:
        """Prepare a new generation idempotently, retaining all committed history."""

        with self.transaction() as transaction:
            current = transaction.load_self(generation_id)
            if current is not None:
                transaction.require_self_signer(current)
                return current
            return transaction.replace_self(
                generation_id,
                expected_revision=None,
                signer=Ed25519PrivateKey.generate(),
                actor="owner",
            )

    def load_self(self, generation_id: str) -> GatewaySelfKey | None:
        """Resolve public evidence without reading private signing material."""

        with self._open() as connection, connection:
            connection.execute("BEGIN")
            self._snapshot(connection)
            return _active_self(connection, self.m_owner, generation_id)

    def self_revision(self, generation_id: str) -> int | None:
        """Return the latest public revision even when the registration is revoked."""

        with self._open() as connection, connection:
            connection.execute("BEGIN")
            self._snapshot(connection)
            record = _self_registration(connection, self.m_owner, generation_id)
            return record[0].registration_revision if record is not None else None

    def load_self_signer(
        self, generation_id: str, *, expected: GatewaySelfKey | None = None
    ) -> Ed25519PrivateKey:
        """Load an owner-private key and verify the public binding in the same snapshot."""

        with self._open() as connection, connection:
            connection.execute("BEGIN")
            self._snapshot(connection)
            current = _active_self(connection, self.m_owner, generation_id)
            if current is None or (expected is not None and current != expected):
                raise GatewayAccessError(503, "self_authorization_unavailable")
            return _load_self_signer(connection, current)

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
        descriptor = os.open(
            _DATABASE,
            os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW,
            0o600,
            dir_fd=directory,
        )
        try:
            os.fchmod(descriptor, 0o600)
        finally:
            os.close(descriptor)
        with _connect(directory) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            for definition in (*_DEFINITION, *_SELF_DEFINITION):
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
                    if connection.execute("PRAGMA application_id").fetchone()[0] != _APPLICATION_ID:
                        raise ValueError("invalid policy schema")
                    if connection.execute("PRAGMA user_version").fetchone()[0] == 1:
                        self._migrate_self_schema(connection)
                    if connection.execute("PRAGMA user_version").fetchone()[0] != _DATABASE_VERSION:
                        raise ValueError("invalid policy schema")
                    yield connection
        except (OSError, sqlite3.Error, ValueError):
            raise GatewayAccessError(503, "policy_unavailable") from None

    def _migrate_self_schema(self, connection: sqlite3.Connection) -> None:
        """Add generation key tables while retaining the committed policy and its evidence."""

        with connection:
            connection.execute("BEGIN IMMEDIATE")
            if connection.execute("PRAGMA user_version").fetchone()[0] == 1:
                self._snapshot(connection)
                for definition in _SELF_DEFINITION:
                    connection.execute(definition)
                connection.execute(f"PRAGMA user_version = {_DATABASE_VERSION}")

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

    if stat.S_IMODE(os.fstat(directory).st_mode) != 0o700:
        raise ValueError("unsafe authorization directory mode")
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
            if stat.S_IMODE(os.fstat(descriptor).st_mode) != 0o600:
                raise ValueError("unsafe database mode")
        finally:
            os.close(descriptor)


def _registered_key(connection: sqlite3.Connection, key_id: str) -> bool:
    """Check whether a fingerprint already belongs to a managed-self registration."""

    return (
        connection.execute(
            "SELECT 1 FROM managed_self_registrations WHERE key_id = ? LIMIT 1", (key_id,)
        ).fetchone()
        is not None
    )


def _self_registration(
    connection: sqlite3.Connection, owner: GatewayOwner, generation_id: str
) -> tuple[GatewaySelfKey, bool] | None:
    """Read the latest registration and validate its public fingerprint."""

    _IDENTIFIER.validate_python(generation_id)
    row = connection.execute(
        """SELECT revision, key_id, substr(public_key, 1, 4097) AS public_key, active
           FROM managed_self_registrations WHERE generation_id = ?
           ORDER BY revision DESC LIMIT 1""",
        (generation_id,),
    ).fetchone()
    if row is None:
        return None
    binding = GatewaySelfKey(
        owner=owner,
        generation_id=generation_id,
        public_key=row["public_key"],
        registration_revision=row["revision"],
    )
    if binding.key_id != row["key_id"] or row["active"] not in (0, 1):
        raise ValueError("invalid managed-self registration")
    return binding, bool(row["active"])


def _active_self(
    connection: sqlite3.Connection, owner: GatewayOwner, generation_id: str
) -> GatewaySelfKey | None:
    """Return public registration only when its latest revision is active."""

    record = _self_registration(connection, owner, generation_id)
    return record[0] if record is not None and record[1] else None


def _load_self_signer(connection: sqlite3.Connection, binding: GatewaySelfKey) -> Ed25519PrivateKey:
    """Verify that the stored generation key matches the selected active registration."""

    row = connection.execute(
        """SELECT private_key FROM managed_self_keys
           WHERE generation_id = ? AND key_id = ? AND length(private_key) = 32""",
        (binding.generation_id, binding.key_id),
    ).fetchone()
    if row is None or not isinstance(row["private_key"], bytes):
        raise GatewayAccessError(503, "self_authorization_unavailable")
    signer = Ed25519PrivateKey.from_private_bytes(row["private_key"])
    if public_key_text(signer.public_key()) != binding.public_key:
        raise GatewayAccessError(503, "self_authorization_unavailable")
    return signer


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
    prior_default_revision = before.default_permission_revision
    if candidate.default_permission_revision not in (
        prior_default_revision,
        prior_default_revision + 1,
    ):
        raise GatewayAccessError(409, "default_permission_revision_conflict")
    default_changed = (
        candidate.default_permission_group,
        candidate.default_permission_group_version,
    ) != (before.default_permission_group, before.default_permission_group_version)
    updated = candidate.model_copy(
        update={
            "revision": revision,
            "roster_revision": before.roster_revision + (old_admins != new_admins),
            "open_epoch": before.open_epoch + (bool(old_admins) != bool(new_admins)),
            "credentials": credentials,
            "default_permission_revision": (
                prior_default_revision + 1
                if default_changed
                else candidate.default_permission_revision
            ),
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
