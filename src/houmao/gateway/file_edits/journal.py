"""Retain exact push intent and receipts independently of the gateway listener."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import closing, contextmanager
import fcntl
import hashlib
import os
from pathlib import Path
import sqlite3

from houmao.gateway._access_storage import (
    GatewayAccessError,
    _file_lock,
    _private_directory,
    _require_private_file,
)
from houmao.gateway.authorization_models import AuthorizationDecision
from houmao.gateway.file_edits.contracts import (
    FileActor,
    FileEditModel,
    FilePushReceipt,
    FilePushRequest,
)

_JOURNAL = "pushes.sqlite3"


class PushRecord(FileEditModel):
    """Keep the first admitted identity and intent with the latest safe receipt."""

    request: FilePushRequest
    decision: AuthorizationDecision
    receipt: FilePushReceipt
    attempt: int = 0

    @property
    def handoff_id(self) -> str:
        """Identify the exact admitted operation within shared owner authorization."""

        identity = (
            f"{self.request.mount_id}\0{self.request.target.incarnation}\0"
            f"{self.request.operation_id}"
        )
        if self.attempt:
            identity += f"\0{self.attempt}"
        return "file-push:" + hashlib.sha256(identity.encode()).hexdigest()

    def matches(self, request: FilePushRequest, decision: AuthorizationDecision) -> bool:
        """Compare repeat intent and stable caller identity across listener restarts."""

        old_actor = self.decision.actor
        new_actor = decision.actor
        return (
            self.request.model_dump(exclude={"presence_id"})
            == request.model_dump(exclude={"presence_id"})
            and (old_actor.kind, old_actor.principal_id) == (new_actor.kind, new_actor.principal_id)
            and (
                old_actor.kind != "anonymous"
                or (
                    self.decision.policy_id == decision.policy_id
                    and self.decision.open_epoch == decision.open_epoch
                    and self.decision.default_permission_revision
                    == decision.default_permission_revision
                )
            )
        )


class PushJournal:
    """Persist one attempt per mount and operation ID under owner-private storage."""

    def __init__(self, root: Path) -> None:
        """Select the initialized mount's private journal location."""

        self.m_root: Path = root

    def begin(
        self, request: FilePushRequest, decision: AuthorizationDecision, publisher: FileActor
    ) -> tuple[PushRecord, bool]:
        """Claim a new operation ID or return its matching retained record."""

        with self._connect() as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = self._get(connection, request.operation_id)
            if existing is not None:
                if not existing.matches(request, decision):
                    raise GatewayAccessError(409, "file_operation_id_conflict")
                return existing, False
            record = PushRecord(
                request=request,
                decision=decision,
                receipt=FilePushReceipt(
                    operation_id=request.operation_id,
                    candidate=request.commit_id,
                    expected_base=request.expected_base,
                    publisher=publisher,
                    outcome="queued" if request.when_idle else "pending",
                ),
            )
            connection.execute(
                "INSERT INTO file_pushes VALUES (?, ?, ?)",
                (request.operation_id, record.handoff_id, record.model_dump_json()),
            )
            return record, True

    def scheduled(self, generation: str) -> tuple[PushRecord, ...]:
        """Find work awaiting idle or recovery after an interrupted dispatch."""

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT record FROM file_pushes WHERE json_extract(record, '$.request.when_idle')
                AND (
                    json_extract(record, '$.receipt.outcome') IN ('queued', 'pending')
                    OR (
                        json_extract(record, '$.request.target.incarnation') = ?
                        AND json_extract(record, '$.receipt.outcome') IN ('unknown', 'published')
                        AND (
                            json_extract(record, '$.receipt.native_ready') IS NOT 1
                            OR json_extract(record, '$.receipt.native_settled') IS NOT 1
                        )
                    )
                ) ORDER BY rowid
                """,
                (generation,),
            ).fetchall()
        return tuple(PushRecord.model_validate_json(row[0]) for row in rows)

    def start_scheduled(self, record: PushRecord) -> PushRecord:
        """Record a new native attempt before acquiring any external reservation."""

        updated = record.model_copy(
            update={
                "attempt": record.attempt + 1,
                "receipt": record.receipt.model_copy(update={"outcome": "pending", "reason": None}),
            }
        )
        return self._save(record, updated)

    def read(self, operation_id: str) -> PushRecord:
        """Read a retained receipt by operation ID without admitting effects."""

        with self._connect() as connection:
            record = self._get(connection, operation_id)
        if record is None:
            raise GatewayAccessError(404, "unknown_file_operation")
        return record

    def for_marker(self, base: str, candidate: str, handoff_id: str | None) -> PushRecord:
        """Find the exact attempt named by the native publication marker."""

        with self._connect() as connection:
            row = connection.execute(
                "SELECT record FROM file_pushes WHERE handoff_id = ?", (handoff_id,)
            ).fetchone()
        if row is None:
            raise GatewayAccessError(409, "file_projection_conflict")
        record = PushRecord.model_validate_json(row[0])
        if (record.request.expected_base, record.request.commit_id, record.handoff_id) != (
            base,
            candidate,
            handoff_id,
        ):
            raise GatewayAccessError(409, "file_projection_conflict")
        return record

    @contextmanager
    def dispatch_guard(self) -> Iterator[bool]:
        """Prevent simultaneous dispatch and recovery for one mount across processes."""

        with _private_directory(self.m_root) as directory:
            descriptor = os.open(
                ".file-push.lock",
                os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK,
                0o600,
                dir_fd=directory,
            )
            try:
                _require_private_file(descriptor)
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    yield False
                else:
                    yield True
            finally:
                os.close(descriptor)

    def save(self, record: PushRecord, receipt: FilePushReceipt) -> FilePushReceipt:
        """Advance only the journal state the caller actually observed."""

        return self._save(record, record.model_copy(update={"receipt": receipt})).receipt

    def _save(self, record: PushRecord, updated: PushRecord) -> PushRecord:
        """Keep the journal record and its native attempt index in sync."""

        with self._connect() as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            current = self._get(connection, record.request.operation_id)
            if current == record:
                connection.execute(
                    "UPDATE file_pushes SET record = ?, handoff_id = ? WHERE operation_id = ?",
                    (updated.model_dump_json(), updated.handoff_id, record.request.operation_id),
                )
                return updated
        if current is None:
            raise GatewayAccessError(503, "file_journal_unavailable")
        return current

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        """Open SQLite within the validated mount directory."""

        try:
            with _private_directory(self.m_root) as directory:
                with _file_lock(directory, ".push-journal.lock", create=True):
                    descriptor = os.open(
                        _JOURNAL,
                        os.O_CREAT | os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                        0o600,
                        dir_fd=directory,
                    )
                    try:
                        _require_private_file(descriptor)
                    finally:
                        os.close(descriptor)
                uri = f"file:/proc/self/fd/{directory}/{_JOURNAL}?mode=rw"
                with closing(sqlite3.connect(uri, uri=True, timeout=3.0)) as connection:
                    connection.execute("PRAGMA trusted_schema = OFF")
                    connection.execute("PRAGMA synchronous = FULL")
                    connection.execute(
                        """CREATE TABLE IF NOT EXISTS file_pushes (
                           operation_id TEXT PRIMARY KEY, handoff_id TEXT UNIQUE NOT NULL,
                           record TEXT NOT NULL
                        )"""
                    )
                    yield connection
        except (OSError, sqlite3.Error, ValueError):
            raise GatewayAccessError(503, "file_journal_unavailable") from None

    @staticmethod
    def _get(connection: sqlite3.Connection, operation_id: str) -> PushRecord | None:
        """Load a single validated journal row."""

        row = connection.execute(
            "SELECT record FROM file_pushes WHERE operation_id = ?", (operation_id,)
        ).fetchone()
        return None if row is None else PushRecord.model_validate_json(row[0])
