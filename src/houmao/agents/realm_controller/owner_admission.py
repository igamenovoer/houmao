"""Coordinate managed prompts and owner maintenance across processes."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import UTC, datetime
import fcntl
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import stat
from time import monotonic
from typing import Literal, cast

from houmao.agents.realm_controller.backends.dispatch_control import _dispatch_origin_birth_token
from houmao.agents.realm_controller.boundary_models import SessionManifestPayloadV4
from houmao.agents.realm_controller.errors import BackendExecutionError, SessionManifestError
from houmao.agents.realm_controller.gateway_storage import (
    gateway_paths_from_manifest_path,
    generate_gateway_request_id,
)
from houmao.agents.realm_controller.gateway_models import (
    GatewayJsonObject,
    GatewayWebExecutionIdentityV1,
)
from houmao.agents.realm_controller.run_modes import RunMode
from houmao.execution.context import current_execution_deadline


OwnerPromptTerminal = Literal["completed", "interrupted", "failed", "settled", "uncertain"]
OwnerPromptState = Literal[
    "reserved", "handed_off", "completed", "interrupted", "failed", "settled", "uncertain"
]
OwnerMaintenanceState = Literal["reserved", "handed_off", "uncertain", "settled", "fenced"]

_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS managed_prompt_attempts (
        request_id TEXT PRIMARY KEY,
        manifest_path TEXT NOT NULL,
        generation_id TEXT NOT NULL,
        mode TEXT NOT NULL,
        origin TEXT NOT NULL,
        state TEXT NOT NULL,
        reserved_at_utc TEXT NOT NULL,
        handoff_at_utc TEXT,
        settled_at_utc TEXT,
        caller_pid INTEGER NOT NULL,
        caller_birth_token TEXT NOT NULL,
        evidence TEXT
    )
"""
_INDEX_SQL = """
    CREATE UNIQUE INDEX IF NOT EXISTS managed_prompt_active_slot
    ON managed_prompt_attempts (manifest_path, generation_id)
    WHERE state IN ('reserved', 'handed_off', 'uncertain') AND origin != 'gateway_deferred'
"""
_MAINTENANCE_TABLE = """
    CREATE TABLE IF NOT EXISTS managed_owner_maintenance (
        operation_id TEXT NOT NULL,
        manifest_path TEXT NOT NULL,
        generation_id TEXT NOT NULL,
        claim_id TEXT NOT NULL UNIQUE,
        state TEXT NOT NULL CHECK (state IN ('reserved', 'handed_off', 'uncertain',
                                             'settled', 'fenced')),
        reserved_at_utc TEXT NOT NULL,
        handoff_at_utc TEXT,
        settled_at_utc TEXT,
        caller_pid INTEGER NOT NULL,
        caller_birth_token TEXT NOT NULL,
        evidence TEXT,
        PRIMARY KEY (manifest_path, generation_id, operation_id)
    )
"""
_MAINTENANCE_INDEX = """
    CREATE UNIQUE INDEX IF NOT EXISTS managed_owner_maintenance_slot
    ON managed_owner_maintenance (manifest_path, generation_id)
    WHERE state IN ('reserved', 'handed_off', 'uncertain')
"""
_OWNER_OPERATION_GUARDS: ContextVar[frozenset[tuple[int, Path]]] = ContextVar(
    "owner_operation_guards", default=frozenset()
)
_MAINTENANCE_ID = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.:-]{0,127}")
_ACTIVE_MAINTENANCE = frozenset({"reserved", "handed_off", "uncertain"})


class OwnerAdmissionError(BackendExecutionError):
    """Describe a refused or unverified managed owner admission."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code


@dataclass(frozen=True)
class OwnerPromptAttempt:
    """Prompt claim metadata without retaining prompt text or native credentials."""

    request_id: str
    manifest_path: Path
    generation_id: str
    mode: RunMode
    origin: str
    state: OwnerPromptState
    reserved_at_utc: str
    handoff_at_utc: str | None
    settled_at_utc: str | None
    caller_pid: int
    caller_birth_token: str
    evidence: str | None

    @property
    def turn_dir(self) -> Path:
        """Return this request's owner-private native artifact directory."""

        manifest = self.manifest_path
        return manifest.parent / f"{manifest.stem}.turn-artifacts" / self.request_id


@dataclass(frozen=True)
class OwnerPromptClaim:
    """Exclusive generation-qualified right to attempt one native prompt handoff."""

    manifest_path: Path
    generation_id: str
    request_id: str
    mode: RunMode

    @property
    def turn_dir(self) -> Path:
        """Return the owner-private artifact directory for this exact operation."""

        return (
            self.manifest_path.parent
            / f"{self.manifest_path.stem}.turn-artifacts"
            / self.request_id
        )

    def active(self) -> bool:
        """Recheck ownership and the current attempt immediately before native input."""

        try:
            _owner_manifest(self.manifest_path, self.generation_id)
            with _connection(self.manifest_path) as connection:
                attempt = _get_attempt(connection, self.request_id)
                return (
                    attempt is not None
                    and attempt.manifest_path == self.manifest_path
                    and attempt.generation_id == self.generation_id
                    and attempt.state in {"reserved", "handed_off"}
                )
        except OwnerAdmissionError:
            return False

    def handoff(self) -> None:
        """Record confirmed native handoff and retain the active runtime slot."""

        with _connection(self.manifest_path) as connection:
            connection.execute(
                """
                UPDATE managed_prompt_attempts
                SET state='handed_off', handoff_at_utc=?
                WHERE request_id=? AND generation_id=? AND state='reserved'
                """,
                (_now(), self.request_id, self.generation_id),
            )

    def finish(self, outcome: OwnerPromptTerminal, *, evidence: str | None = None) -> None:
        """Record terminal or uncertain evidence for this attempt only."""

        with _connection(self.manifest_path) as connection:
            _finish_attempt(connection, self.request_id, self.generation_id, outcome, evidence)


@dataclass(frozen=True)
class OwnerMaintenanceClaim:
    """Persist one owner maintenance attempt independently of its gateway process."""

    manifest_path: Path
    generation_id: str
    operation_id: str
    claim_id: str

    def state(self) -> OwnerMaintenanceState | None:
        """Read the state of this exact claim, including after an owner fence."""

        with _connection(self.manifest_path) as connection:
            row = self._read(connection)
            return cast(OwnerMaintenanceState, row["state"]) if row is not None else None

    def active(self) -> bool:
        """Allow effects only for a current generation and unfenced origin."""

        try:
            _owner_manifest(self.manifest_path, self.generation_id)
            with _connection(self.manifest_path) as connection:
                row = self._read(connection)
                return (
                    row is not None
                    and row["state"] in {"reserved", "handed_off"}
                    and _maintenance_caller_is_current(row)
                )
        except OwnerAdmissionError:
            return False

    def handoff(self) -> None:
        """Record the original process's one exact effect handoff."""

        with _connection(self.manifest_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = self._read(connection)
            if row is None or row["state"] != "reserved" or not _maintenance_caller_is_current(row):
                raise OwnerAdmissionError(
                    "duplicate_request", "Owner maintenance cannot dispatch this handoff."
                )
            _owner_manifest(self.manifest_path, self.generation_id)
            connection.execute(
                "UPDATE managed_owner_maintenance SET state='handed_off', handoff_at_utc=? "
                "WHERE claim_id=?",
                (_now(), self.claim_id),
            )

    def release_before_handoff(self, *, evidence: str) -> None:
        """Release a reservation after a definite refusal before any native effect."""

        self._finish_before_handoff("settled", evidence)

    def retain_before_handoff(self, *, evidence: str) -> None:
        """Yield an unresolved pre-handoff claim to reconciliation without reopening admission."""

        self._finish_before_handoff("uncertain", evidence)

    def finish(self, *, evidence: str, settled: bool, ready: bool) -> bool:
        """Release admission only when attributed settlement and readiness are both known."""

        with _connection(self.manifest_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = self._read(connection)
            if row is None or row["state"] not in _ACTIVE_MAINTENANCE:
                return False
            if row["state"] == "reserved" and _maintenance_caller_is_alive(row):
                return False
            _owner_manifest(self.manifest_path, self.generation_id)
            released = settled and ready
            self._record_outcome(connection, "settled" if released else "uncertain", evidence)
            return released

    def fence_after_recovery(self) -> None:
        """Retire this lost owner's claim after a guarded lifecycle stop succeeded."""

        if (os.getpid(), self.manifest_path) not in _OWNER_OPERATION_GUARDS.get():
            raise OwnerAdmissionError("unavailable", "Owner maintenance recovery is unguarded.")
        with _connection(self.manifest_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = self._read(connection)
            if row is not None and row["state"] in _ACTIVE_MAINTENANCE:
                if _maintenance_caller_is_alive(row):
                    raise OwnerAdmissionError("not_ready", "The maintenance caller is still live.")
                self._record_outcome(connection, "fenced", "owner_lifecycle_stop")

    def _finish_before_handoff(self, state: Literal["settled", "uncertain"], evidence: str) -> None:
        """Let only this reservation's original process end the pre-handoff attempt."""

        with _connection(self.manifest_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = self._read(connection)
            if (
                row is not None
                and row["state"] == "reserved"
                and _maintenance_caller_is_current(row)
            ):
                self._record_outcome(connection, state, evidence)

    def _read(self, connection: sqlite3.Connection) -> sqlite3.Row | None:
        """Load evidence for the retained operation identity and unguessable claim ID."""

        row = connection.execute(
            """
            SELECT * FROM managed_owner_maintenance
            WHERE manifest_path=? AND generation_id=? AND operation_id=? AND claim_id=?
            """,
            (str(self.manifest_path), self.generation_id, self.operation_id, self.claim_id),
        ).fetchone()
        return cast(sqlite3.Row | None, row)

    def _record_outcome(
        self,
        connection: sqlite3.Connection,
        state: Literal["settled", "uncertain", "fenced"],
        evidence: str,
    ) -> None:
        """Update the claim and keep its admission closed while the result is uncertain."""

        connection.execute(
            """
            UPDATE managed_owner_maintenance SET state=?, settled_at_utc=?, evidence=?
            WHERE claim_id=?
            """,
            (state, None if state == "uncertain" else _now(), evidence, self.claim_id),
        )


def reserve_owner_maintenance(
    manifest_path: Path,
    generation_id: str,
    *,
    operation_id: str,
    readiness: Callable[[], None] | None = None,
    reconcile_tui: Callable[[OwnerPromptAttempt], bool] | None = None,
) -> OwnerMaintenanceClaim:
    """Reserve the exact owner before attempting immediate native maintenance."""

    manifest_path = manifest_path.resolve()
    if _MAINTENANCE_ID.fullmatch(operation_id) is None:
        raise OwnerAdmissionError("invalid_request", "Invalid owner maintenance identity.")
    pid = os.getpid()
    birth = _dispatch_origin_birth_token(pid)
    if not birth:
        raise OwnerAdmissionError("unavailable", "Cannot verify the maintenance caller process.")

    with _owner_operation_gate(manifest_path), _connection(manifest_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        manifest = _owner_manifest(manifest_path, generation_id)
        ensure_owner_input_allowed(connection, manifest_path, generation_id)
        active = _reconcile_active(
            connection, manifest, manifest_path, generation_id, reconcile_tui
        )
        if active is not None:
            connection.commit()
            code = "uncertain" if active.state == "uncertain" else "not_ready"
            raise OwnerAdmissionError(code, "The owner has an unresolved prompt attempt.")
        if _gateway_work_is_pending(connection):
            raise OwnerAdmissionError("not_ready", "The owner has pending gateway requests.")
        if readiness is not None:
            readiness()
        claim_id = secrets.token_hex(24)
        created = connection.execute(
            """
            INSERT OR IGNORE INTO managed_owner_maintenance
                (operation_id, manifest_path, generation_id, claim_id, state,
                 reserved_at_utc, caller_pid, caller_birth_token)
            VALUES (?, ?, ?, ?, 'reserved', ?, ?, ?)
            """,
            (operation_id, str(manifest_path), generation_id, claim_id, _now(), pid, birth),
        )
        if created.rowcount != 1:
            raise OwnerAdmissionError("duplicate_request", "The owner has seen this maintenance.")
    return OwnerMaintenanceClaim(manifest_path, generation_id, operation_id, claim_id)


def observe_owner_maintenance(
    manifest_path: Path, generation_id: str
) -> OwnerMaintenanceClaim | None:
    """Find the unresolved maintenance claim for the selected owner generation."""

    manifest_path = manifest_path.resolve()
    with _connection(manifest_path) as connection:
        row = _active_maintenance(connection, manifest_path, generation_id)
    return _maintenance_claim(row) if row is not None else None


def load_owner_maintenance(
    manifest_path: Path, generation_id: str, operation_id: str
) -> OwnerMaintenanceClaim | None:
    """Locate owner-private evidence for an already-recorded exact attempt."""

    manifest_path = manifest_path.resolve()
    with _connection(manifest_path) as connection:
        row = connection.execute(
            "SELECT * FROM managed_owner_maintenance "
            "WHERE manifest_path=? AND generation_id=? AND operation_id=?",
            (str(manifest_path), generation_id, operation_id),
        ).fetchone()
    return _maintenance_claim(row) if row is not None else None


def ensure_owner_input_allowed(
    connection: sqlite3.Connection, manifest_path: Path, generation_id: str
) -> None:
    """Refuse ordinary admission inside the caller's immediate queue transaction."""

    if not connection.in_transaction:
        raise OwnerAdmissionError("unavailable", "Owner admission requires a queue transaction.")
    connection.execute(_MAINTENANCE_TABLE)
    row = _active_maintenance(connection, manifest_path.resolve(), generation_id)
    if row is not None:
        _raise_owner_maintenance(row)


def owner_operation_guard_exists(manifest_path: Path) -> bool:
    """Test whether this session owns the durable gateway admission layout."""

    manifest_path = manifest_path.resolve()
    paths = gateway_paths_from_manifest_path(manifest_path)
    return bool(
        paths is not None
        and (paths.queue_path.exists() or _owner_operation_lock_path(manifest_path).exists())
    )


@contextmanager
def guard_owner_operation(
    manifest_path: Path, generation_id: str, *, recover_lost_maintenance: bool = False
) -> Iterator[OwnerMaintenanceClaim | None]:
    """Serialize immediate input or lifecycle effects against maintenance reservation."""

    manifest_path = manifest_path.resolve()
    with _owner_operation_gate(manifest_path, shared=True):
        with _connection(manifest_path) as connection:
            row = _active_maintenance(connection, manifest_path, generation_id)
        recovery = None
        if row is not None:
            if not recover_lost_maintenance or _maintenance_caller_is_alive(row):
                _raise_owner_maintenance(row)
            recovery = _maintenance_claim(row)
        yield recovery


def reserve_owner_prompt(
    manifest_path: Path,
    generation_id: str,
    *,
    request_id: str | None = None,
    origin: str,
    readiness: Callable[[], None] | None = None,
    reconcile_tui: Callable[[OwnerPromptAttempt], bool] | None = None,
) -> OwnerPromptClaim:
    """Verify the owner and reserve an immediate prompt before any provider mutation."""

    manifest_path = manifest_path.resolve()
    request_id = request_id or generate_gateway_request_id()
    if Path(request_id).name != request_id or request_id in {"", ".", ".."}:
        raise OwnerAdmissionError("invalid_request", "Invalid owner prompt request identity.")
    pid = os.getpid()
    birth = _dispatch_origin_birth_token(pid)
    if not birth:
        raise OwnerAdmissionError("unavailable", "Cannot verify the prompt caller process.")
    with _connection(manifest_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        manifest = _owner_manifest(manifest_path, generation_id)
        ensure_owner_input_allowed(connection, manifest_path, generation_id)
        deferred = origin == "gateway_deferred"
        if deferred and manifest.mode != "web":
            raise OwnerAdmissionError("invalid_request", "Native deferred input requires Web mode.")
        active = _reconcile_active(
            connection, manifest, manifest_path, generation_id, reconcile_tui
        )
        if active is not None and (not deferred or active.state != "handed_off"):
            connection.commit()
            error_code = "uncertain" if active.state == "uncertain" else "not_ready"
            raise OwnerAdmissionError(error_code, "The owner has an unresolved prompt attempt.")
        if _get_attempt(connection, request_id) is not None:
            raise OwnerAdmissionError(
                "duplicate_request", "The owner has already seen this request."
            )
        if readiness is not None:
            readiness()
        connection.execute(
            """
            INSERT INTO managed_prompt_attempts
                (request_id, manifest_path, generation_id, mode, origin, state,
                 reserved_at_utc, caller_pid, caller_birth_token)
            VALUES (?, ?, ?, ?, ?, 'reserved', ?, ?, ?)
            """,
            (
                request_id,
                str(manifest_path),
                generation_id,
                manifest.mode,
                origin,
                _now(),
                pid,
                birth,
            ),
        )
    return OwnerPromptClaim(manifest_path, generation_id, request_id, manifest.mode)


def observe_owner_prompt(
    manifest_path: Path,
    generation_id: str,
    *,
    reconcile_tui: Callable[[OwnerPromptAttempt], bool] | None = None,
) -> OwnerPromptAttempt | None:
    """Read and reconcile the active attempt using only attributable native evidence."""

    manifest_path = manifest_path.resolve()
    with _connection(manifest_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        manifest = _owner_manifest(manifest_path, generation_id)
        return _reconcile_active(connection, manifest, manifest_path, generation_id, reconcile_tui)


def _now() -> str:
    """Return an unambiguous timestamp for owner operation evidence."""

    return datetime.now(UTC).isoformat(timespec="microseconds")


def _owner_manifest(manifest_path: Path, generation_id: str) -> SessionManifestPayloadV4:
    """Resolve the exact persisted owner without permitting an older body to act."""

    from houmao.agents.realm_controller.runtime import require_active_managed_control_manifest

    try:
        return require_active_managed_control_manifest(manifest_path, generation_id=generation_id)
    except (OSError, SessionManifestError):
        raise OwnerAdmissionError(
            "unavailable", "Managed owner authority is unavailable."
        ) from None


@contextmanager
def _connection(manifest_path: Path) -> Iterator[sqlite3.Connection]:
    """Open the existing owner-local request store with bounded lock waits."""

    paths = gateway_paths_from_manifest_path(manifest_path)
    if paths is None or not paths.queue_path.is_file():
        raise OwnerAdmissionError("unavailable", "Managed owner admission storage is unavailable.")
    deadline = current_execution_deadline()
    timeout = 2.0 if deadline is None else max(0.0, min(2.0, deadline - monotonic()))
    try:
        connection = sqlite3.connect(paths.queue_path, timeout=timeout)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute(_TABLE_SQL)
            connection.execute(_INDEX_SQL)
            connection.execute(_MAINTENANCE_TABLE)
            connection.execute(_MAINTENANCE_INDEX)
            with connection:
                yield connection
        finally:
            connection.close()
    except (OSError, sqlite3.Error) as exc:
        raise OwnerAdmissionError(
            "unavailable", "Managed owner admission storage is unavailable."
        ) from exc


def _owner_operation_lock_path(manifest_path: Path) -> Path:
    """Keep the stable owner guard beside its canonical runtime manifest."""

    return manifest_path.with_name(f".{manifest_path.name}.owner-operation.lock")


@contextmanager
def _owner_operation_gate(manifest_path: Path, *, shared: bool = False) -> Iterator[None]:
    """Hold a per-runtime process lock without spanning the effect with SQLite."""

    key = (os.getpid(), manifest_path)
    held = _OWNER_OPERATION_GUARDS.get()
    if key in held:
        if not shared:
            raise OwnerAdmissionError("not_ready", "A managed owner operation is running.")
        yield
        return
    try:
        descriptor = os.open(
            _owner_operation_lock_path(manifest_path),
            os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o600,
        )
    except OSError:
        raise OwnerAdmissionError(
            "unavailable", "Managed owner operation guard is unavailable."
        ) from None
    try:
        try:
            info = os.fstat(descriptor)
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_uid != os.geteuid()
                or info.st_nlink != 1
                or stat.S_IMODE(info.st_mode) & 0o077
            ):
                raise OwnerAdmissionError("unavailable", "Managed owner operation guard is unsafe.")
            mode = fcntl.LOCK_SH if shared else fcntl.LOCK_EX
            fcntl.flock(descriptor, mode | fcntl.LOCK_NB)
        except BlockingIOError:
            raise OwnerAdmissionError(
                "not_ready", "A managed owner operation is running."
            ) from None
        except OSError:
            raise OwnerAdmissionError(
                "unavailable", "Managed owner operation guard is unavailable."
            ) from None
        token = _OWNER_OPERATION_GUARDS.set(held | {key})
        try:
            yield
        finally:
            _OWNER_OPERATION_GUARDS.reset(token)
    finally:
        os.close(descriptor)


def _active_maintenance(
    connection: sqlite3.Connection, manifest_path: Path, generation_id: str
) -> sqlite3.Row | None:
    """Read the one maintenance claim that still blocks native owner admission."""

    cursor = connection.cursor()
    cursor.row_factory = sqlite3.Row
    row = cursor.execute(
        """
        SELECT * FROM managed_owner_maintenance
        WHERE manifest_path=? AND generation_id=? AND state IN ('reserved', 'handed_off', 'uncertain')
        """,
        (str(manifest_path), generation_id),
    ).fetchone()
    return cast(sqlite3.Row | None, row)


def _maintenance_claim(row: sqlite3.Row) -> OwnerMaintenanceClaim:
    """Recover a durable claim without acquiring a new owner reservation."""

    return OwnerMaintenanceClaim(
        Path(row["manifest_path"]), row["generation_id"], row["operation_id"], row["claim_id"]
    )


def _maintenance_caller_is_alive(row: sqlite3.Row) -> bool:
    """Match the caller process birth token so PID reuse cannot resume its effects."""

    return not owner_process_has_exited(row["caller_pid"], row["caller_birth_token"])


def _maintenance_caller_is_current(row: sqlite3.Row) -> bool:
    """Confirm that this process reserved the effect, as opposed to reconciling it."""

    pid = os.getpid()
    return bool(
        row["caller_pid"] == pid and _dispatch_origin_birth_token(pid) == row["caller_birth_token"]
    )


def owner_process_has_exited(pid: int, birth: str) -> bool:
    """Prove exact process loss without treating inaccessible process data as death."""

    observed = _dispatch_origin_birth_token(pid)
    if observed is not None:
        return observed.partition(":")[0] == birth.partition(":")[0] and observed != birth
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    except OSError:
        return False
    # Procfs may still report the PID while its dead process awaits reaping.
    try:
        state = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8").rpartition(")")[2].split()
    except (OSError, UnicodeError):
        return False
    return bool(state and state[0] in {"Z", "X", "x"})


def _raise_owner_maintenance(row: sqlite3.Row) -> None:
    """Report a bounded busy or uncertainty status without leaking maintenance evidence."""

    code = (
        "uncertain"
        if row["state"] == "uncertain" or not _maintenance_caller_is_alive(row)
        else "not_ready"
    )
    raise OwnerAdmissionError(code, "The owner has unresolved maintenance.")


def _gateway_work_is_pending(connection: sqlite3.Connection) -> bool:
    """Check durable gateway work before reserving the owner for a new mutation."""

    try:
        return (
            connection.execute(
                "SELECT 1 FROM gateway_requests WHERE state IN ('accepted', 'running', 'observing') LIMIT 1"
            ).fetchone()
            is not None
        )
    except sqlite3.OperationalError:
        # A prompt-only fixture or older owner can have the prompt journal alone.
        row = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='gateway_requests'"
        ).fetchone()
        if row is not None:
            raise
        return False


def _row_attempt(row: sqlite3.Row | None) -> OwnerPromptAttempt | None:
    """Hydrate a private attempt from the finite request record shape."""

    if row is None:
        return None
    return OwnerPromptAttempt(
        request_id=row["request_id"],
        manifest_path=Path(row["manifest_path"]),
        generation_id=row["generation_id"],
        mode=row["mode"],
        origin=row["origin"],
        state=row["state"],
        reserved_at_utc=row["reserved_at_utc"],
        handoff_at_utc=row["handoff_at_utc"],
        settled_at_utc=row["settled_at_utc"],
        caller_pid=row["caller_pid"],
        caller_birth_token=row["caller_birth_token"],
        evidence=row["evidence"],
    )


def _get_attempt(connection: sqlite3.Connection, request_id: str) -> OwnerPromptAttempt | None:
    """Find one durable attempt independent of the current provider generation."""

    return _row_attempt(
        connection.execute(
            "SELECT * FROM managed_prompt_attempts WHERE request_id=?", (request_id,)
        ).fetchone()
    )


def _reconcile_active(
    connection: sqlite3.Connection,
    manifest: SessionManifestPayloadV4,
    manifest_path: Path,
    generation_id: str,
    reconcile_tui: Callable[[OwnerPromptAttempt], bool] | None,
) -> OwnerPromptAttempt | None:
    """Release the slot only when evidence settles the selected attempt."""

    rows = connection.execute(
        """
        SELECT * FROM managed_prompt_attempts
        WHERE manifest_path=? AND generation_id=? AND state IN ('reserved', 'handed_off', 'uncertain')
        ORDER BY CASE state WHEN 'uncertain' THEN 0 WHEN 'reserved' THEN 1 ELSE 2 END, reserved_at_utc
        """,
        (str(manifest_path), generation_id),
    ).fetchall()
    for row in rows:
        attempt = _row_attempt(row)
        assert attempt is not None
        if attempt.mode in {"tui", "headless"} and manifest.backend in {
            "hermes_tui",
            "hermes_headless",
        }:
            terminal = _read_native_terminal(attempt, manifest=manifest)
            if (
                terminal is None
                and manifest.backend == "hermes_tui"
                and reconcile_tui is not None
                and reconcile_tui(attempt)
            ):
                terminal = _read_native_terminal(attempt, manifest=manifest)
            if terminal is not None:
                outcome, evidence = terminal
                _finish_attempt(connection, attempt.request_id, generation_id, outcome, evidence)
                continue
        if (
            attempt.mode == "tui"
            and manifest.backend != "hermes_tui"
            and attempt.handoff_at_utc is not None
            and (
                (reconcile_tui is not None and reconcile_tui(attempt))
                or _tui_usage_settled(attempt)
            )
        ):
            _finish_attempt(
                connection, attempt.request_id, generation_id, "settled", "terminal_tracker"
            )
            continue
        caller_alive = (
            _dispatch_origin_birth_token(attempt.caller_pid) == attempt.caller_birth_token
        )
        if caller_alive and attempt.state != "uncertain":
            return attempt
        terminal = _read_native_terminal(attempt, manifest=manifest)
        if terminal is not None:
            outcome, evidence = terminal
            _finish_attempt(connection, attempt.request_id, generation_id, outcome, evidence)
            continue
        if not caller_alive and attempt.state != "uncertain":
            _finish_attempt(
                connection, attempt.request_id, generation_id, "uncertain", "caller_disconnected"
            )
        return _get_attempt(connection, attempt.request_id)
    return None


def _tui_usage_settled(attempt: OwnerPromptAttempt) -> bool:
    """Use the exact managed turn's usage evidence to release terminal admission."""

    from houmao.agents.realm_controller.usage_store import UsageStoreError
    from houmao.agents.realm_controller.usage_support import UsageService

    try:
        service = UsageService.from_manifest(attempt.manifest_path)
        service.collect(max_batches=8)
        record = service.store.get_record(attempt.request_id)
        return record is not None and record.generation_id == attempt.generation_id
    except (OSError, ValueError, UsageStoreError):
        return False


def _finish_attempt(
    connection: sqlite3.Connection,
    request_id: str,
    generation_id: str,
    outcome: OwnerPromptTerminal,
    evidence: str | None,
) -> None:
    """Transition only the unresolved attempt, retaining any handoff timestamp."""

    connection.execute(
        """
        UPDATE managed_prompt_attempts SET state=?, settled_at_utc=?, evidence=?
        WHERE request_id=? AND generation_id=? AND state IN ('reserved', 'handed_off', 'uncertain')
        """,
        (outcome, _now(), evidence, request_id, generation_id),
    )


def _read_native_terminal(
    attempt: OwnerPromptAttempt,
    *,
    manifest: SessionManifestPayloadV4,
) -> tuple[OwnerPromptTerminal, str] | None:
    """Read exact durable terminal evidence after the submitting process disappeared."""

    try:
        if manifest.backend == "hermes_tui":
            from houmao.agents.realm_controller.backends.hermes_tui_receipts import (
                HERMES_TUI_ADMISSION_FILE,
                read_hermes_tui_admission,
            )

            native_session_id = manifest.backend_state.get("native_session_id")
            if not isinstance(native_session_id, str):
                return None
            receipt = read_hermes_tui_admission(
                attempt.turn_dir / HERMES_TUI_ADMISSION_FILE,
                request_id=attempt.request_id,
                generation_id=attempt.generation_id,
                native_session_id=native_session_id,
            )
            outcome = receipt.terminal_outcome if receipt is not None else None
            return (outcome, "tui_native") if outcome is not None else None
        if manifest.backend == "hermes_headless":
            from houmao.agents.realm_controller.backends.hermes_headless_protocol import (
                reconcile_hermes_headless_turn,
            )
            from houmao.agents.realm_controller.manifest import commit_hermes_headless_completion

            settlement = reconcile_hermes_headless_turn(
                attempt.turn_dir, generation_id=attempt.generation_id
            )
            if settlement.status == "completed" and (
                settlement.session_id is None
                or settlement.turn_index is None
                or not commit_hermes_headless_completion(
                    attempt.manifest_path,
                    generation_id=attempt.generation_id,
                    session_id=settlement.session_id,
                    turn_index=settlement.turn_index,
                )
            ):
                return None
            if settlement.status != "uncertain" and settlement.completion_source is not None:
                return cast(OwnerPromptTerminal, settlement.status), settlement.completion_source
            return None
        if attempt.mode == "headless":
            code = int((attempt.turn_dir / "exitcode").read_text().strip())
            if manifest.backend == "dsh_headless" and code in {0, 130}:
                from houmao.agents.realm_controller.headless_snapshots import (
                    read_dsh_cli_terminal_source,
                )

                source = read_dsh_cli_terminal_source(attempt.turn_dir, returncode=code)
                if source is None:
                    return None
                if code == 130:
                    return "interrupted", source
                if _dsh_headless_session_committed(attempt, manifest):
                    return "completed", source
                return None
            if code != 0:
                return "failed", "headless_artifacts"
            if _headless_session_committed(attempt, manifest):
                return "completed", "headless_artifacts"
        if attempt.mode == "web":
            result = exact_web_prompt_result(
                attempt.turn_dir, attempt.request_id, attempt.generation_id
            )
            if result is None and manifest.backend == "kimi_web":
                from houmao.agents.realm_controller.backends.kimi_web import (
                    recover_kimi_web_prompt_result,
                )

                recover_kimi_web_prompt_result(
                    attempt.manifest_path, attempt.generation_id, attempt.request_id
                )
                result = exact_web_prompt_result(
                    attempt.turn_dir, attempt.request_id, attempt.generation_id
                )
            expected = GatewayWebExecutionIdentityV1.model_validate(
                manifest.backend_state.get("web_identity")
            )
            if result is not None and result.get("identity") == expected.model_dump(mode="json"):
                return (cast(OwnerPromptTerminal, result["outcome"]), "web_native")
        if attempt.mode == "service":
            from houmao.agents.realm_controller.backends.service_runtime import (
                ServiceRequestSnapshot,
                read_service_record,
            )

            request = ServiceRequestSnapshot.model_validate_json(
                read_service_record(attempt.turn_dir / "service-request.json")
            )
            if (
                request.request_id == attempt.request_id
                and request.generation_id == attempt.generation_id
                and request.service_incarnation == manifest.backend_state.get("service_incarnation")
                and request.native_session_id == manifest.backend_state.get("native_session_id")
                and request.completed_at_utc is not None
                and (request.state == "failed" or request.handoff_at_utc is not None)
            ):
                match request.state:
                    case "completed" | "failed" | "interrupted" as outcome:
                        return outcome, "service_native"
    except (OSError, ValueError, AttributeError, BackendExecutionError, SessionManifestError):
        return None
    return None


def _dsh_headless_session_committed(
    attempt: OwnerPromptAttempt, manifest: SessionManifestPayloadV4
) -> bool:
    """Recover a completed CLI turn whose caller died before manifest persistence."""

    binding = json.loads((attempt.turn_dir / "dsh-native-binding.json").read_text())
    home = Path(manifest.launch_plan.home_selector.home_path)
    committed = json.loads((home / "houmao-native-session.json").read_text())
    return (
        isinstance(binding, dict)
        and binding == committed
        and binding.get("attempt_id") == attempt.request_id
        and binding.get("runtime_session_id") == manifest.runtime.session_id
        and binding.get("generation") == attempt.generation_id
        and binding.get("working_directory") == manifest.working_directory
        and isinstance(binding.get("native_session_id"), str)
        and bool(binding.get("native_session_id"))
    )


def _headless_session_committed(
    attempt: OwnerPromptAttempt, manifest: SessionManifestPayloadV4
) -> bool:
    """Require attributable completion and the saved logical session for continuation."""

    from houmao.agents.realm_controller.usage_store import UsageStoreError
    from houmao.agents.realm_controller.usage_support import UsageService

    if manifest.headless is None or manifest.headless.session_id is None:
        return False
    try:
        service = UsageService.from_manifest(attempt.manifest_path)
        service.collect(max_batches=8)
        record = service.store.get_record(attempt.request_id)
        return (
            record is not None
            and record.generation_id == attempt.generation_id
            and record.outcome == "completed"
            and record.provider_session_id == manifest.headless.session_id
        )
    except (OSError, ValueError, UsageStoreError):
        return False


def exact_web_prompt_result(
    turn_dir: Path, request_id: str, generation_id: str, *, include_assistant: bool = False
) -> GatewayJsonObject | None:
    """Project terminal evidence from the receipt of one exact native Web operation."""

    try:
        result = json.loads((turn_dir / "web-result.json").read_text())
        if not isinstance(result, dict) or result.get("operation_id") != request_id:
            return None
        identity, receipt = result.get("identity"), result.get("receipt")
        if (
            not isinstance(identity, dict)
            or identity.get("generation") != generation_id
            or not isinstance(receipt, dict)
            or receipt.get("operation_id") != request_id
            or receipt.get("identity") != identity
            or receipt.get("status") not in {"terminal", "abandoned"}
            or result.get("outcome") not in {"completed", "interrupted", "failed"}
        ):
            return None
        session = identity.get("native_session_id")
        turns = receipt.get("turns")
        if (
            not isinstance(session, str)
            or not isinstance(turns, list)
            or not all(type(turn) is int and turn >= 0 for turn in turns)
        ):
            return None
        outcome = result["outcome"]
        if outcome == "completed" and not turns:
            return None
        native_identity = GatewayWebExecutionIdentityV1.model_validate(identity)
        summary: GatewayJsonObject = {
            "operation_id": request_id,
            "source": "web_native",
            "outcome": outcome,
            "native_session_id": session,
            "native_turn_ids": [str(turn) for turn in turns],
            "identity": native_identity.model_dump(mode="json"),
        }
        assistant = result.get("assistant_text")
        if include_assistant:
            if isinstance(assistant, str) and len(assistant.encode()) <= 32768:
                summary["assistant_text"] = assistant
            native_id = receipt.get("message_id")
            if isinstance(native_id, str):
                summary["native_prompt_id"] = native_id
        return summary
    except (OSError, ValueError, AttributeError):
        return None


def exact_web_prompt_admission(
    turn_dir: Path, request_id: str, identity: GatewayWebExecutionIdentityV1
) -> tuple[Literal["queued", "handed_off"], str] | None:
    """Read a checked native receipt without loading prompt content."""

    try:
        receipt = json.loads((turn_dir / "web-receipt.json").read_text())
        if (
            not isinstance(receipt, dict)
            or receipt.get("operation_id") != request_id
            or receipt.get("identity") != identity.model_dump(mode="json")
        ):
            return None
        status, native_id = receipt.get("status"), receipt.get("message_id")
        if (
            not isinstance(native_id, str)
            or not 0 < len(native_id) <= 512
            or not native_id.replace("_", "").replace("-", "").isalnum()
            or status
            not in ("queued", "running", "blocked", "completed", "failed", "aborted", "terminal")
        ):
            return None
        return ("queued" if status == "queued" else "handed_off"), native_id
    except (OSError, ValueError):
        return None


def exact_web_prompt_handoff(
    turn_dir: Path,
    request_id: str,
    identity: GatewayWebExecutionIdentityV1,
    prompt_id: str,
) -> bool:
    """Read native turn-start evidence for one exact formerly queued prompt."""

    try:
        handoff = json.loads((turn_dir / "web-handoff.json").read_text())
    except (OSError, ValueError):
        return False
    return (
        isinstance(handoff, dict)
        and handoff.get("operation_id") == request_id
        and handoff.get("identity") == identity.model_dump(mode="json")
        and handoff.get("message_id") == prompt_id
    )
