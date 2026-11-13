"""Transactional per-runtime-session usage staging and immutable accounting.

This database is independent of gateway queue storage. A source checkpoint and
its accepted observations commit together, and finalization sequences remain
stable across controller replacement and late turn completion.
"""

from __future__ import annotations

import base64
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Self
import uuid

from pydantic import BaseModel, ValidationError

from houmao.agents.realm_controller.usage_models import (
    DEFAULT_USAGE_PAGE_LIMIT,
    MAX_USAGE_PAGE_LIMIT,
    UsageCapability,
    UsageCheckpoint,
    UsageCollectionHealth,
    UsageCursor,
    UsageFinalization,
    UsageObservation,
    UsagePage,
    UsagePendingTurn,
    UsageRecord,
    UsageSourceBinding,
    UsageTurnSnapshot,
)

_STORE_SCHEMA_VERSION = 1
_SCHEMA = (
    "CREATE TABLE store_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)",
    "CREATE TABLE source_bindings (binding_id TEXT PRIMARY KEY, body TEXT NOT NULL)",
    """CREATE TABLE source_checkpoints (
        binding_id TEXT NOT NULL, source_id TEXT NOT NULL, version INTEGER NOT NULL,
        body TEXT NOT NULL, PRIMARY KEY(binding_id, source_id))""",
    """CREATE TABLE usage_observations (
        variant_id TEXT PRIMARY KEY, observation_id TEXT NOT NULL, binding_id TEXT NOT NULL,
        provider_turn_id TEXT, turn_id TEXT, source_ref TEXT NOT NULL, body TEXT NOT NULL)""",
    "CREATE INDEX observations_binding ON usage_observations(binding_id, provider_turn_id)",
    "CREATE INDEX observations_turn ON usage_observations(turn_id)",
    """CREATE TABLE pending_turns (
        turn_id TEXT PRIMARY KEY, finalized INTEGER NOT NULL DEFAULT 0, body TEXT NOT NULL)""",
    """CREATE TABLE provider_turn_aliases (
        binding_id TEXT NOT NULL, provider_session_id TEXT NOT NULL,
        provider_turn_id TEXT NOT NULL, turn_id TEXT NOT NULL,
        PRIMARY KEY(binding_id, provider_session_id, provider_turn_id))""",
    """CREATE TABLE usage_records (
        sequence INTEGER PRIMARY KEY AUTOINCREMENT, record_id TEXT NOT NULL UNIQUE,
        turn_id TEXT NOT NULL UNIQUE, provider_session_id TEXT, provider_turn_id TEXT,
        finalized_at_utc TEXT NOT NULL, body TEXT NOT NULL)""",
)
_REQUIRED_TABLES = frozenset(
    {
        "store_metadata",
        "source_bindings",
        "source_checkpoints",
        "usage_observations",
        "pending_turns",
        "provider_turn_aliases",
        "usage_records",
    }
)


class UsageStoreError(RuntimeError):
    """Usage storage cannot safely service the requested operation."""


class UsageStoreSchemaError(UsageStoreError):
    """Existing usage storage has an unsupported or inconsistent schema."""


class UsageConflictError(UsageStoreError):
    """Repeated accounting conflicts with durable accepted evidence."""


class UsageCheckpointConflictError(UsageConflictError):
    """A competing collector advanced a source checkpoint."""


class UsageCursorError(ValueError):
    """A cursor does not address a valid position in this usage stream."""


def _canonical(model: BaseModel) -> str:
    """Serialize stable model content for persistence and equivalence checks."""

    return json.dumps(
        model.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def _encode_cursor(cursor: UsageCursor) -> str:
    """Encode a versioned stream position as an opaque URL-safe token."""

    return base64.urlsafe_b64encode(_canonical(cursor).encode("utf-8")).decode("ascii").rstrip("=")


def _decode_cursor(value: str) -> UsageCursor:
    """Reject malformed tokens rather than substituting the first page."""

    if not value or len(value) > 4096:
        raise UsageCursorError("Invalid usage cursor")
    try:
        raw = base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)
        return UsageCursor.model_validate_json(raw)
    except (ValueError, UnicodeError, ValidationError) as exc:
        raise UsageCursorError("Invalid usage cursor") from exc


class UsageStore:
    """Own one runtime's independent usage database and immutable stream.

    Use :meth:`from_path` to initialize or validate the current schema. Each
    operation opens its own connection, making instances usable by independent
    collection threads without sharing a SQLite transaction.
    """

    def __init__(self) -> None:
        """Initialize an unconfigured store for factory construction."""

        self.m_path: Path | None = None
        self.m_runtime_session_id: str = ""
        self.m_stream_id: str = ""

    @classmethod
    def from_path(cls, path: Path, runtime_session_id: str) -> Self:
        """Open a runtime-owned ledger, rejecting foreign or incompatible files.

        Parameters
        ----------
        path:
            Full path to the independent usage SQLite database.
        runtime_session_id:
            Stable owning runtime identity. An existing database must match it.
        """

        if not runtime_session_id.strip():
            raise ValueError("A runtime session ID is required")
        instance = cls()
        instance.m_path = path.resolve()
        instance.m_runtime_session_id = runtime_session_id
        instance._initialize()
        return instance

    @property
    def path(self) -> Path:
        """Return the configured database path."""

        if self.m_path is None:
            raise UsageStoreError("Usage store is not configured")
        return self.m_path

    @property
    def runtime_session_id(self) -> str:
        """Return the stable owning runtime identity."""

        return self.m_runtime_session_id

    @property
    def stream_id(self) -> str:
        """Return this database incarnation's immutable cursor identity."""

        return self.m_stream_id

    def _initialize(self) -> None:
        """Create a fresh schema or validate existing storage without migration."""

        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(self.path, timeout=10, isolation_level=None) as connection:
                connection.execute("BEGIN IMMEDIATE")
                tables = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    )
                    if not row[0].startswith("sqlite_")
                }
                if not tables:
                    if connection.execute("PRAGMA user_version").fetchone()[0] != 0:
                        raise UsageStoreSchemaError("Unsupported usage storage schema")
                    for statement in _SCHEMA:
                        connection.execute(statement)
                    metadata = {
                        "schema_version": str(_STORE_SCHEMA_VERSION),
                        "runtime_session_id": self.runtime_session_id,
                        "stream_id": "usage-" + uuid.uuid4().hex,
                    }
                    connection.executemany(
                        "INSERT INTO store_metadata VALUES (?, ?)", metadata.items()
                    )
                    connection.execute(f"PRAGMA user_version={_STORE_SCHEMA_VERSION}")
                elif not _REQUIRED_TABLES.issubset(tables):
                    raise UsageStoreSchemaError("Unsupported usage storage schema")
                metadata = self._read_metadata(connection)
                self.m_stream_id = metadata["stream_id"]
                connection.commit()
        except (sqlite3.Error, OSError) as exc:
            raise UsageStoreError("Usage storage is unavailable or unreadable") from exc

    def _read_metadata(self, connection: sqlite3.Connection) -> dict[str, str]:
        """Check schema, runtime ownership, and the required stream identity."""

        metadata = dict(connection.execute("SELECT key, value FROM store_metadata"))
        if (
            metadata.get("schema_version") != str(_STORE_SCHEMA_VERSION)
            or connection.execute("PRAGMA user_version").fetchone()[0] != _STORE_SCHEMA_VERSION
            or metadata.get("runtime_session_id") != self.runtime_session_id
            or not metadata.get("stream_id")
        ):
            raise UsageStoreSchemaError("Usage storage schema or runtime identity is incompatible")
        return metadata

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        """Open a validated connection with bounded lock waiting."""

        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(self.path, timeout=10, isolation_level=None)
            connection.row_factory = sqlite3.Row
            metadata = self._read_metadata(connection)
            if metadata["stream_id"] != self.stream_id:
                raise UsageStoreSchemaError("Usage storage stream was replaced")
            yield connection
        except (sqlite3.Error, OSError, ValidationError) as exc:
            raise UsageStoreError("Usage storage is unavailable or unreadable") from exc
        finally:
            if connection is not None:
                connection.close()

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        """Serialize mutations and roll back every partially applied operation."""

        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                yield connection
            except BaseException:
                connection.rollback()
                raise
            else:
                connection.commit()

    def put_binding(self, binding: UsageSourceBinding) -> UsageSourceBinding:
        """Persist ownership without silently resetting an existing boundary."""

        if binding.runtime_session_id != self.runtime_session_id:
            raise UsageConflictError("Source binding belongs to another runtime")
        with self._transaction() as connection:
            row = connection.execute(
                "SELECT body FROM source_bindings WHERE binding_id=?", (binding.binding_id,)
            ).fetchone()
            if row is not None:
                previous = UsageSourceBinding.model_validate_json(row["body"])
                stable = (
                    "agent_id",
                    "runtime_session_id",
                    "provider",
                    "collection_boundary",
                    "started_at_utc",
                )
                if any(getattr(previous, key) != getattr(binding, key) for key in stable):
                    raise UsageConflictError("Source binding identity or boundary conflicts")
                if previous.provider_session_id not in (None, binding.provider_session_id):
                    raise UsageConflictError("Source binding provider identity conflicts")
            connection.execute(
                "INSERT INTO source_bindings VALUES (?, ?) ON CONFLICT(binding_id) DO UPDATE SET body=excluded.body",
                (binding.binding_id, _canonical(binding)),
            )
        return binding

    def get_binding(self, binding_id: str) -> UsageSourceBinding | None:
        """Read one persisted binding without discovering provider files."""

        with self._connection() as connection:
            row = connection.execute(
                "SELECT body FROM source_bindings WHERE binding_id=?", (binding_id,)
            ).fetchone()
            return None if row is None else UsageSourceBinding.model_validate_json(row["body"])

    def list_bindings(self) -> list[UsageSourceBinding]:
        """Read the runtime's persisted source families."""

        with self._connection() as connection:
            return [
                UsageSourceBinding.model_validate_json(row["body"])
                for row in connection.execute(
                    "SELECT body FROM source_bindings ORDER BY binding_id"
                )
            ]

    def get_checkpoint(self, binding_id: str, source_id: str) -> UsageCheckpoint | None:
        """Read complete-record progress; absent checkpoints have logical version zero."""

        with self._connection() as connection:
            row = connection.execute(
                "SELECT body FROM source_checkpoints WHERE binding_id=? AND source_id=?",
                (binding_id, source_id),
            ).fetchone()
            return None if row is None else UsageCheckpoint.model_validate_json(row["body"])

    def list_checkpoints(self, *, binding_id: str | None = None) -> list[UsageCheckpoint]:
        """Read durable progress for a source family, including moved file aliases."""

        where = "" if binding_id is None else " WHERE binding_id=?"
        arguments = () if binding_id is None else (binding_id,)
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT body FROM source_checkpoints" + where + " ORDER BY rowid", arguments
            )
            return [UsageCheckpoint.model_validate_json(row["body"]) for row in rows]

    def ingest_batch(
        self,
        *,
        checkpoint: UsageCheckpoint,
        observations: Sequence[UsageObservation],
        expected_version: int = 0,
        binding_id: str | None = None,
        source_id: str | None = None,
        diagnostics: Sequence[str] = (),
    ) -> UsageCheckpoint:
        """Atomically accept observations and compare-and-swap source progress.

        The first accepted checkpoint has version one. Distinct provisional
        representations of one logical observation are retained for the
        assembler to reconcile; identical replays insert no additional variant.
        """

        if binding_id not in (None, checkpoint.binding_id) or source_id not in (
            None,
            checkpoint.source_id,
        ):
            raise UsageConflictError("Checkpoint source identity conflicts")
        with self._transaction() as connection:
            if (
                connection.execute(
                    "SELECT 1 FROM source_bindings WHERE binding_id=?", (checkpoint.binding_id,)
                ).fetchone()
                is None
            ):
                raise UsageConflictError("Source checkpoint requires a persisted binding")
            row = connection.execute(
                "SELECT version FROM source_checkpoints WHERE binding_id=? AND source_id=?",
                (checkpoint.binding_id, checkpoint.source_id),
            ).fetchone()
            actual_version = 0 if row is None else int(row["version"])
            if actual_version != expected_version:
                raise UsageCheckpointConflictError("Source checkpoint advanced; retry collection")
            for observation in observations:
                if observation.binding_id not in (None, checkpoint.binding_id):
                    raise UsageConflictError("Observation belongs to another source binding")
                accepted = observation.model_copy(update={"binding_id": checkpoint.binding_id})
                body = _canonical(accepted)
                variant_id = hashlib.sha256(body.encode("utf-8")).hexdigest()
                connection.execute(
                    "INSERT OR IGNORE INTO usage_observations VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        variant_id,
                        accepted.observation_id,
                        checkpoint.binding_id,
                        accepted.provider_turn_id,
                        accepted.turn_id,
                        accepted.source_ref,
                        body,
                    ),
                )
            updated = checkpoint.model_copy(
                update={
                    "version": actual_version + 1,
                    "diagnostics": list(dict.fromkeys([*checkpoint.diagnostics, *diagnostics])),
                }
            )
            connection.execute(
                "INSERT INTO source_checkpoints VALUES (?, ?, ?, ?) ON CONFLICT(binding_id, source_id) DO UPDATE SET version=excluded.version, body=excluded.body",
                (updated.binding_id, updated.source_id, updated.version, _canonical(updated)),
            )
            return updated

    def list_observations(
        self,
        *,
        binding_id: str | None = None,
        turn_id: str | None = None,
        provider_turn_id: str | None = None,
        source_ref: str | None = None,
    ) -> list[UsageObservation]:
        """Read staged evidence selected by bound source or accounting turn."""

        clauses: list[str] = []
        values: list[str] = []
        for name, value in (
            ("binding_id", binding_id),
            ("turn_id", turn_id),
            ("provider_turn_id", provider_turn_id),
            ("source_ref", source_ref),
        ):
            if value is not None:
                clauses.append(name + "=?")
                values.append(value)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT body FROM usage_observations" + where + " ORDER BY rowid", values
            )
            return [UsageObservation.model_validate_json(row["body"]) for row in rows]

    def _put_alias(self, connection: sqlite3.Connection, snapshot: UsageTurnSnapshot) -> None:
        """Bind a provider turn to one accounting turn before final insertion."""

        if snapshot.provider_turn_id is None:
            return
        key = (
            snapshot.binding_id or "",
            snapshot.provider_session_id or "",
            snapshot.provider_turn_id,
        )
        row = connection.execute(
            "SELECT turn_id FROM provider_turn_aliases WHERE binding_id=? AND provider_session_id=? AND provider_turn_id=?",
            key,
        ).fetchone()
        if row is not None and row["turn_id"] != snapshot.turn_id:
            raise UsageConflictError("Provider turn already has an accounting identity")
        connection.execute(
            "INSERT OR IGNORE INTO provider_turn_aliases VALUES (?, ?, ?, ?)",
            (*key, snapshot.turn_id),
        )

    def _put_pending(
        self, connection: sqlite3.Connection, pending: UsagePendingTurn
    ) -> UsagePendingTurn:
        """Validate identity and update staged state inside the caller's transaction."""

        snapshot = pending.snapshot
        if snapshot.runtime_session_id != self.runtime_session_id:
            raise UsageConflictError("Pending turn belongs to another runtime")
        if pending.finalization is not None and pending.finalization.turn_id != snapshot.turn_id:
            raise UsageConflictError("Finalization belongs to another turn")
        row = connection.execute(
            "SELECT body, finalized FROM pending_turns WHERE turn_id=?", (snapshot.turn_id,)
        ).fetchone()
        if row is not None:
            existing = UsagePendingTurn.model_validate_json(row["body"])
            stable = (
                "agent_id",
                "runtime_session_id",
                "turn_id",
                "generation_id",
                "backend",
                "provider",
                "started_at_utc",
                "turn_origin",
            )
            if any(getattr(existing.snapshot, key) != getattr(snapshot, key) for key in stable):
                raise UsageConflictError("Pending turn's original identity or timing conflicts")
            for key in ("provider_session_id", "provider_turn_id", "binding_id"):
                old = getattr(existing.snapshot, key)
                if old is not None and old != getattr(snapshot, key):
                    raise UsageConflictError("Pending provider turn identity conflicts")
            if existing.finalized:
                if _canonical(existing) != _canonical(pending):
                    raise UsageConflictError("Finalized turn state is immutable")
                return existing
            if existing.finalization is not None:
                if pending.finalization is None:
                    pending = pending.model_copy(update={"finalization": existing.finalization})
                elif _canonical(existing.finalization) != _canonical(pending.finalization):
                    raise UsageConflictError("Durable finalization facts conflict")
        self._put_alias(connection, pending.snapshot)
        connection.execute(
            "INSERT INTO pending_turns VALUES (?, ?, ?) ON CONFLICT(turn_id) DO UPDATE SET finalized=excluded.finalized, body=excluded.body",
            (snapshot.turn_id, int(pending.finalized), _canonical(pending)),
        )
        return pending

    def put_pending_turn(
        self,
        turn: UsageTurnSnapshot | UsagePendingTurn,
        *,
        finalization: UsageFinalization | None = None,
    ) -> UsagePendingTurn:
        """Register a turn before dispatch or persist its durable terminal facts."""

        pending = (
            turn
            if isinstance(turn, UsagePendingTurn)
            else UsagePendingTurn(snapshot=turn, finalization=finalization)
        )
        if isinstance(turn, UsagePendingTurn) and finalization is not None:
            pending = turn.model_copy(update={"finalization": finalization})
        with self._transaction() as connection:
            return self._put_pending(connection, pending)

    def get_pending_turn(self, turn_id: str) -> UsagePendingTurn | None:
        """Read registered turn state, including already finalized associations."""

        with self._connection() as connection:
            row = connection.execute(
                "SELECT body FROM pending_turns WHERE turn_id=?", (turn_id,)
            ).fetchone()
            return None if row is None else UsagePendingTurn.model_validate_json(row["body"])

    def list_pending_turns(self, *, include_finalized: bool = False) -> list[UsagePendingTurn]:
        """Read durable turn work awaiting recovery or all preserved associations."""

        where = "" if include_finalized else " WHERE finalized=0"
        with self._connection() as connection:
            return [
                UsagePendingTurn.model_validate_json(row["body"])
                for row in connection.execute(
                    "SELECT body FROM pending_turns" + where + " ORDER BY rowid"
                )
            ]

    def set_finalization(self, turn_id: str, finalization: UsageFinalization) -> UsagePendingTurn:
        """Attach immutable terminal facts to an existing pending turn."""

        with self._transaction() as connection:
            row = connection.execute(
                "SELECT body FROM pending_turns WHERE turn_id=?", (turn_id,)
            ).fetchone()
            if row is None:
                raise UsageConflictError("Accounting turn is not registered")
            pending = UsagePendingTurn.model_validate_json(row["body"])
            return self._put_pending(
                connection, pending.model_copy(update={"finalization": finalization})
            )

    def associate_provider_turn(
        self,
        turn_id: str,
        *,
        binding_id: str,
        provider_session_id: str | None,
        provider_turn_id: str,
    ) -> UsagePendingTurn:
        """Resolve provider identity before managed/native finalizers can diverge."""

        with self._transaction() as connection:
            row = connection.execute(
                "SELECT body FROM pending_turns WHERE turn_id=?", (turn_id,)
            ).fetchone()
            if row is None:
                raise UsageConflictError("Accounting turn is not registered")
            pending = UsagePendingTurn.model_validate_json(row["body"])
            snapshot = pending.snapshot.model_copy(
                update={
                    "binding_id": binding_id,
                    "provider_session_id": provider_session_id,
                    "provider_turn_id": provider_turn_id,
                }
            )
            return self._put_pending(connection, pending.model_copy(update={"snapshot": snapshot}))

    def resolve_turn_id(
        self,
        *,
        binding_id: str,
        provider_turn_id: str,
        provider_session_id: str | None = None,
    ) -> str | None:
        """Resolve a verified native turn to its registered accounting identity."""

        with self._connection() as connection:
            row = connection.execute(
                "SELECT turn_id FROM provider_turn_aliases WHERE binding_id=? AND provider_session_id=? AND provider_turn_id=?",
                (binding_id, provider_session_id or "", provider_turn_id),
            ).fetchone()
            return None if row is None else str(row["turn_id"])

    def finalize(self, record: UsageRecord) -> bool:
        """Insert one immutable final row and atomically close its pending turn.

        Returns
        -------
        bool
            True for the first insertion and False for equivalent replay.
        """

        if record.runtime_session_id != self.runtime_session_id:
            raise UsageConflictError("Usage record belongs to another runtime")
        body = _canonical(record)
        with self._transaction() as connection:
            existing = connection.execute(
                "SELECT body FROM usage_records WHERE record_id=? OR turn_id=?",
                (record.record_id, record.turn_id),
            ).fetchone()
            if existing is not None:
                if existing["body"] != body:
                    raise UsageConflictError(
                        "Finalized usage record conflicts with existing accounting"
                    )
                return False
            pending_row = connection.execute(
                "SELECT body FROM pending_turns WHERE turn_id=?", (record.turn_id,)
            ).fetchone()
            pending: UsagePendingTurn | None = None
            if pending_row is not None:
                pending = UsagePendingTurn.model_validate_json(pending_row["body"])
                for key in (
                    "agent_id",
                    "runtime_session_id",
                    "turn_id",
                    "generation_id",
                    "backend",
                    "provider",
                    "turn_origin",
                    "started_at_utc",
                ):
                    if getattr(pending.snapshot, key) != getattr(record, key):
                        raise UsageConflictError(
                            "Final usage does not match the original turn snapshot"
                        )
                if pending.finalization is not None and (
                    pending.finalization.outcome != record.outcome
                    or pending.finalization.completed_at_utc != record.completed_at_utc
                ):
                    raise UsageConflictError("Final usage does not match durable terminal facts")
            connection.execute(
                "INSERT INTO usage_records(record_id, turn_id, provider_session_id, provider_turn_id, finalized_at_utc, body) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    record.record_id,
                    record.turn_id,
                    record.provider_session_id,
                    record.provider_turn_id,
                    datetime.now(UTC).isoformat(timespec="microseconds"),
                    body,
                ),
            )
            if pending is not None:
                finished = pending.model_copy(update={"finalized": True})
                connection.execute(
                    "UPDATE pending_turns SET finalized=1, body=? WHERE turn_id=?",
                    (_canonical(finished), record.turn_id),
                )
            return True

    def get_record(self, turn_id: str) -> UsageRecord | None:
        """Read one immutable finalized record by accounting turn ID."""

        with self._connection() as connection:
            row = connection.execute(
                "SELECT body FROM usage_records WHERE turn_id=?", (turn_id,)
            ).fetchone()
            return None if row is None else UsageRecord.model_validate_json(row["body"])

    def set_collection_health(self, health: UsageCollectionHealth) -> None:
        """Persist safe health information separately from immutable accounting."""

        with self._transaction() as connection:
            connection.execute(
                "INSERT INTO store_metadata VALUES ('collection_health', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (_canonical(health),),
            )

    def get_collection_health(self) -> UsageCollectionHealth:
        """Read the latest recorded collection health without contacting sources."""

        with self._connection() as connection:
            row = connection.execute(
                "SELECT value FROM store_metadata WHERE key='collection_health'"
            ).fetchone()
            return (
                UsageCollectionHealth()
                if row is None
                else UsageCollectionHealth.model_validate_json(row["value"])
            )

    def read_page(
        self,
        *,
        after: str | None = None,
        limit: int = DEFAULT_USAGE_PAGE_LIMIT,
        capability: UsageCapability | None = None,
        collection: UsageCollectionHealth | None = None,
    ) -> UsagePage:
        """Read a bounded finalization-order page with a resumable end cursor."""

        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 1 <= limit <= MAX_USAGE_PAGE_LIMIT
        ):
            raise UsageCursorError("Usage limit must be between 1 and 500")
        cursor = (
            UsageCursor(stream_id=self.stream_id, sequence=0)
            if after is None
            else _decode_cursor(after)
        )
        if cursor.stream_id != self.stream_id:
            raise UsageCursorError("Usage cursor belongs to another stream")
        with self._connection() as connection:
            connection.execute("BEGIN")
            maximum = int(
                connection.execute(
                    "SELECT COALESCE(MAX(sequence),0) FROM usage_records"
                ).fetchone()[0]
            )
            if cursor.sequence > maximum:
                raise UsageCursorError("Usage cursor is ahead of the current stream")
            rows = connection.execute(
                "SELECT sequence, body FROM usage_records WHERE sequence>? ORDER BY sequence LIMIT ?",
                (cursor.sequence, limit + 1),
            ).fetchall()
            visible = rows[:limit]
            position = cursor.sequence if not visible else int(visible[-1]["sequence"])
            records = [UsageRecord.model_validate_json(row["body"]) for row in visible]
            return UsagePage(
                runtime_session_id=self.runtime_session_id,
                stream_id=self.stream_id,
                capability=capability or UsageCapability(status="available", turn_recording=True),
                collection=collection or self.get_collection_health(),
                records=records,
                next_cursor=_encode_cursor(
                    UsageCursor(stream_id=self.stream_id, sequence=position)
                ),
                has_more=len(rows) > limit,
            )
