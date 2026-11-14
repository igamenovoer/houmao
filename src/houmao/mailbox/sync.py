"""Bounded account-scoped metadata observation backed by gateway-owned SQLite.

Email object checkpoints and filtered query states are deliberately separate. This
module stores disposable metadata, never message bodies or delivery acknowledgments.
Network calls finish before the short, binding-fenced local commit boundary.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from contextlib import AbstractContextManager
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import time
from typing import Any, Literal, Protocol, TypeVar

from houmao.mailbox.stalwart import StalwartError
from houmao.mailbox.stalwart_models import (
    JmapEmailChanges,
    JmapMetadataBatch,
    JmapMetadataPage,
    JmapMetadataQuery,
    JmapOperationMeter,
    JmapQueryChanges,
)

SyncPhase = Literal["idle", "catching_up", "rebasing", "degraded", "unsupported"]
CommitGuard = Callable[[Callable[[], None]], bool]
_T = TypeVar("_T")
_RECOVERABLE_STATES = {"cannotCalculateChanges", "tooManyChanges", "stateMismatch", "staleCursor"}
_UNSUPPORTED_STATES = {"unknownMethod", "unsupportedMethod", "unsupportedFilter"}
_METADATA_FIELDS = frozenset(
    {
        "id",
        "threadId",
        "receivedAt",
        "messageId",
        "inReplyTo",
        "references",
        "from",
        "to",
        "cc",
        "replyTo",
        "subject",
        "preview",
        "keywords",
        "mailboxIds",
        "hasAttachment",
        "read",
        "answered",
        "archived",
        "box",
        "unread",
    }
)


class SyncClient(Protocol):
    """Validated metadata-only provider connection used by an observer."""

    @property
    def method_call_count(self) -> int:
        """Return the connection's cumulative JMAP method count."""
        ...

    def operation_meter(
        self,
        *,
        max_method_calls: int | None = None,
        timeout_seconds: float | None = None,
    ) -> AbstractContextManager[JmapOperationMeter]:
        """Meter this execution context, including nested calls and failures."""
        ...

    @property
    def max_objects_in_get(self) -> int:
        """Return the provider's effective finite metadata-get cap."""
        ...

    def email_state(self, *, timeout_seconds: float | None = None) -> str:
        """Capture an email-object state without retrieving messages."""
        ...

    def query_metadata_page(
        self,
        *,
        query: JmapMetadataQuery,
        limit: int = 50,
        position: int = 0,
        expected_query_state: str | None = None,
        timeout_seconds: float | None = None,
        max_method_calls: int | None = None,
    ) -> JmapMetadataPage:
        """Fetch one finite filtered metadata page."""
        ...

    def get_metadata(
        self,
        *,
        email_ids: Sequence[str],
        timeout_seconds: float | None = None,
    ) -> JmapMetadataBatch:
        """Fetch bounded metadata and authoritative missing IDs."""
        ...

    def changes(
        self,
        *,
        since_state: str,
        max_changes: int = 100,
        timeout_seconds: float | None = None,
    ) -> JmapEmailChanges:
        """Read one bounded, possibly intermediate email change batch."""
        ...

    def metadata_matches_query(self, message: dict[str, Any], query: JmapMetadataQuery) -> bool:
        """Evaluate eligibility using already cached roles, without network I/O."""
        ...

    def query_fingerprint(self, query: JmapMetadataQuery) -> str:
        """Fingerprint the exact cached wire filter, account, sort, and role IDs."""
        ...

    def query_changes(
        self,
        *,
        query: JmapMetadataQuery,
        since_query_state: str,
        max_changes: int = 100,
        timeout_seconds: float | None = None,
    ) -> JmapQueryChanges:
        """Read one qualified exact-query delta, without email-change pagination."""
        ...


@dataclass(frozen=True)
class SyncScope:
    """Durable account/view identity, independent of credential and process epochs."""

    agent_id: str
    binding_id: str
    account_id: str
    query_fingerprint: str
    channel: Literal["online"] = "online"
    query_policy_json: str = "{}"

    @classmethod
    def for_query(
        cls,
        *,
        agent_id: str,
        binding_id: str,
        account_id: str,
        query: JmapMetadataQuery,
        client: SyncClient,
    ) -> SyncScope:
        """Construct the exact persisted account and query-policy scope."""
        return cls(
            agent_id,
            binding_id,
            account_id,
            client.query_fingerprint(query),
            query_policy_json=json.dumps(asdict(query), sort_keys=True),
        )

    @property
    def key(self) -> str:
        """Return a stable opaque SQLite key for this scope."""
        payload = [
            self.agent_id,
            self.channel,
            self.binding_id,
            self.account_id,
            self.query_fingerprint,
        ]
        return hashlib.sha256(json.dumps(payload, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class SyncBudget:
    """Finite cycle limits, additionally constrained by provider capabilities."""

    max_method_calls: int = 5
    max_seconds: float = 10.0
    change_batch: int = 100
    window_size: int = 50
    max_cached_messages: int = 200

    def __post_init__(self) -> None:
        """Reject unlimited or out-of-policy operational limits."""
        if (
            self.max_method_calls < 1
            or self.max_seconds <= 0
            or not math.isfinite(self.max_seconds)
        ):
            raise ValueError("sync cycle budgets must be finite and positive")
        if not 1 <= self.change_batch <= 500:
            raise ValueError("sync change batch must be between 1 and 500")
        if not 1 <= self.window_size <= 200 or not 1 <= self.max_cached_messages <= 200:
            raise ValueError("sync metadata windows must be between 1 and 200")
        if self.window_size > self.max_cached_messages:
            raise ValueError("sync window exceeds the metadata cache bound")


@dataclass(frozen=True)
class SyncView:
    """Safe bounded observation and progress returned to notifier scheduling."""

    messages: tuple[dict[str, Any], ...] = ()
    complete: bool = False
    has_more: bool = False
    email_state: str | None = None
    query_state: str | None = None
    phase: SyncPhase = "rebasing"
    method_calls: int = 0
    budget_limited: bool = False
    incremental_supported: bool | None = None
    last_success_utc: str | None = None
    error_code: str | None = None
    retry_after_utc: float | None = None
    confirmed_ineligible: tuple[str, ...] = ()
    superseded: bool = False


@dataclass(frozen=True)
class _Snapshot:
    """One revision of the account-scoped disposable metadata cache."""

    view: SyncView = SyncView()
    version: int = 0
    needs_refill: bool = True
    failures: int = 0


class _BudgetExhausted(Exception):
    """Stop work at a resumable cycle boundary."""


class _Superseded(Exception):
    """Reject a worker whose binding fence or local snapshot is obsolete."""

    def __init__(self, error_code: str = "binding_superseded") -> None:
        """Retain the safe authority or query-policy retirement reason."""
        self.m_error_code: str = error_code
        super().__init__(error_code)

    @property
    def error_code(self) -> str:
        """Return the reason this observation cannot publish."""
        return self.m_error_code


class _Cycle:
    """Track actual JMAP method use and remaining wall-clock time."""

    def __init__(self, budget: SyncBudget) -> None:
        self.m_budget: SyncBudget = budget
        self.m_deadline: float = time.monotonic() + budget.max_seconds
        self.m_calls: int = 0

    @property
    def remaining_calls(self) -> int:
        """Return the unspent JMAP method allowance."""
        return self.m_budget.max_method_calls - self.m_calls

    @property
    def remaining_seconds(self) -> float:
        """Return the finite timeout available to the next network call."""
        return max(0.0, self.m_deadline - time.monotonic())

    def invoke(self, client: SyncClient, call: Callable[[float], _T], *, minimum: int = 1) -> _T:
        """Charge actual wire methods, including methods that return an error."""
        if self.remaining_calls < minimum or self.remaining_seconds <= 0:
            raise _BudgetExhausted
        meter: JmapOperationMeter | None = None
        try:
            with client.operation_meter(
                max_method_calls=self.remaining_calls, timeout_seconds=self.remaining_seconds
            ) as meter:
                return call(self.remaining_seconds)
        finally:
            self.m_calls += meter.attempted_methods if meter is not None else 0
            if self.m_calls > self.m_budget.max_method_calls:
                raise ValueError("provider exceeded the sync method budget")


class SyncObserver:
    """Observe one provider account/view using short fenced SQLite transactions."""

    def __init__(self) -> None:
        self.m_sqlite_path: Path | None = None
        self.m_client: SyncClient | None = None
        self.m_scope: SyncScope | None = None
        self.m_commit_guard: CommitGuard | None = None
        self.m_use_query_changes: bool = False

    @classmethod
    def from_config(
        cls,
        *,
        sqlite_path: Path,
        client: SyncClient,
        scope: SyncScope,
        commit_guard: CommitGuard,
        use_query_changes: bool = False,
    ) -> SyncObserver:
        """Bind a validated connection, durable scope, and revision/epoch guard.

        Parameters
        ----------
        sqlite_path : Path
            Existing gateway-owned database; tables use a mail-sync prefix.
        client : SyncClient
            Immutable validated provider connection with cached role discovery.
        scope : SyncScope
            Owner, online binding, provider account, and exact query policy.
        commit_guard : callable
            Run the callback only while its captured binding fence is current.
            The callback performs local SQLite work and never network I/O.
        """
        instance = cls()
        instance.m_sqlite_path = sqlite_path
        instance.m_client = client
        instance.m_scope = scope
        instance.m_commit_guard = commit_guard
        instance.m_use_query_changes = use_query_changes
        instance._initialize()
        return instance

    def snapshot(self) -> SyncView:
        """Read persisted observation without contacting the provider."""
        return self._load().view

    def observe(self, query: JmapMetadataQuery, budget: SyncBudget | None = None) -> SyncView:
        """Apply only fully reconciled bounded batches, then yield safe progress."""
        assert self.m_scope is not None and self.m_client is not None
        if self.client.query_fingerprint(query) != self.m_scope.query_fingerprint:
            raise ValueError("sync query does not match its persisted view scope")
        limits = budget or SyncBudget()
        cycle = _Cycle(limits)
        snapshot = self._load()
        if snapshot.view.retry_after_utc and snapshot.view.retry_after_utc > time.time():
            return snapshot.view
        ineligible: set[str] = set()
        try:
            if snapshot.view.email_state is None:
                state = cycle.invoke(
                    self.m_client,
                    lambda timeout: self.client.email_state(timeout_seconds=timeout),
                )
                snapshot = self._commit(
                    snapshot,
                    replace(snapshot.view, email_state=state, phase="rebasing", error_code=None),
                    needs_refill=True,
                )
            if (
                snapshot.needs_refill
                or snapshot.view.incremental_supported is False
                or self.m_use_query_changes
                or snapshot.view.phase in {"catching_up", "degraded"}
            ):
                snapshot = self._query(snapshot, query, limits, cycle)
            while snapshot.view.incremental_supported is not False:
                if cycle.remaining_calls < 2:
                    if snapshot.view.phase != "idle":
                        raise _BudgetExhausted
                    break
                try:
                    snapshot, lost = self._changes(snapshot, query, limits, cycle)
                    ineligible.update(lost)
                except Exception as exc:
                    kind = _method_error(exc)
                    if kind not in _RECOVERABLE_STATES | _UNSUPPORTED_STATES:
                        raise
                    unsupported = kind in _UNSUPPORTED_STATES
                    snapshot = self._commit(
                        snapshot,
                        replace(
                            snapshot.view,
                            messages=(),
                            email_state=None,
                            query_state=None,
                            phase="rebasing",
                            complete=False,
                            has_more=True,
                            incremental_supported=False
                            if unsupported
                            else snapshot.view.incremental_supported,
                            error_code=kind,
                        ),
                        needs_refill=True,
                    )
                    state = cycle.invoke(
                        self.m_client,
                        lambda timeout: self.client.email_state(timeout_seconds=timeout),
                    )
                    snapshot = self._commit(
                        snapshot, replace(snapshot.view, email_state=state), needs_refill=True
                    )
                    snapshot = self._query(snapshot, query, limits, cycle)
                    break
                if snapshot.view.phase == "idle":
                    if snapshot.needs_refill:
                        snapshot = self._query(snapshot, query, limits, cycle)
                    break
                # A current filtered sample can expose work during a long archive catch-up.
                if cycle.remaining_calls >= 2 and (
                    not snapshot.view.messages or snapshot.needs_refill
                ):
                    snapshot = self._query(snapshot, query, limits, cycle)
                    break
        except _BudgetExhausted:
            return replace(
                snapshot.view,
                method_calls=cycle.m_calls,
                budget_limited=True,
                confirmed_ineligible=tuple(sorted(ineligible)),
            )
        except _Superseded as exc:
            return SyncView(
                phase="degraded",
                error_code=exc.error_code,
                method_calls=cycle.m_calls,
                superseded=True,
            )
        except Exception as exc:
            code = (
                "local_commit_failed"
                if isinstance(exc, sqlite3.Error)
                else (_method_error(exc) or "provider_unavailable")
            )
            failures = min(snapshot.failures + 1, 10)
            failed = replace(
                snapshot.view,
                phase="degraded",
                error_code=code,
                retry_after_utc=time.time() + min(60.0, 2.0**failures),
            )
            try:
                snapshot = self._commit(
                    snapshot, failed, needs_refill=snapshot.needs_refill, failures=failures
                )
            except _Superseded as superseded:
                return SyncView(
                    phase="degraded",
                    error_code=superseded.error_code,
                    method_calls=cycle.m_calls,
                    superseded=True,
                )
            except sqlite3.Error:
                pass
            return replace(
                failed, method_calls=cycle.m_calls, confirmed_ineligible=tuple(sorted(ineligible))
            )
        return replace(
            snapshot.view,
            method_calls=cycle.m_calls,
            confirmed_ineligible=tuple(sorted(ineligible)),
        )

    @property
    def client(self) -> SyncClient:
        """Narrow the factory-initialized client for callback closures."""
        assert self.m_client is not None
        return self.m_client

    def _query(
        self, snapshot: _Snapshot, query: JmapMetadataQuery, budget: SyncBudget, cycle: _Cycle
    ) -> _Snapshot:
        """Replace the bounded eligible window without borrowing its get-state."""
        if self.m_use_query_changes and snapshot.view.query_state is not None:
            try:
                delta = cycle.invoke(
                    self.client,
                    lambda timeout: self.client.query_changes(
                        query=query,
                        since_query_state=snapshot.view.query_state or "",
                        max_changes=budget.change_batch,
                        timeout_seconds=timeout,
                    ),
                )
                if delta.old_query_state != snapshot.view.query_state:
                    raise ValueError("provider returned a mismatched query state")
                if not delta.added and not delta.removed:
                    return self._commit(
                        snapshot,
                        replace(
                            snapshot.view,
                            query_state=delta.new_query_state,
                            last_success_utc=_now(),
                            error_code=None,
                            retry_after_utc=None,
                        ),
                        needs_refill=False,
                    )
            except Exception as exc:
                if _method_error(exc) not in _RECOVERABLE_STATES | _UNSUPPORTED_STATES:
                    raise
            # A query delta has no hasMoreChanges. Rebuild a finite exact-filter page.
            snapshot = self._commit(
                snapshot,
                replace(
                    snapshot.view,
                    messages=(),
                    query_state=None,
                    complete=False,
                    has_more=True,
                    phase="rebasing",
                ),
                needs_refill=True,
            )
        page = cycle.invoke(
            self.client,
            lambda timeout: self.client.query_metadata_page(
                query=query,
                limit=budget.window_size,
                timeout_seconds=timeout,
                max_method_calls=cycle.remaining_calls,
            ),
            minimum=2,
        )
        messages = tuple(_safe_metadata(message) for message in page.messages)
        view = replace(
            snapshot.view,
            messages=messages[: budget.max_cached_messages],
            complete=page.complete and not page.has_more,
            has_more=page.has_more or len(messages) > budget.max_cached_messages,
            query_state=page.query_state,
            phase="unsupported" if snapshot.view.incremental_supported is False else "catching_up",
            last_success_utc=_now(),
            error_code=None,
            retry_after_utc=None,
        )
        return self._commit(snapshot, view, needs_refill=False, failures=0)

    def _changes(
        self, snapshot: _Snapshot, query: JmapMetadataQuery, budget: SyncBudget, cycle: _Cycle
    ) -> tuple[_Snapshot, set[str]]:
        """Reconcile one exact email-object batch before committing its state."""
        assert snapshot.view.email_state is not None
        cap = max(1, self.client.max_objects_in_get)
        batch_limit = min(budget.change_batch, cap * (cycle.remaining_calls - 1))
        changes = cycle.invoke(
            self.client,
            lambda timeout: self.client.changes(
                since_state=snapshot.view.email_state or "",
                max_changes=batch_limit,
                timeout_seconds=timeout,
            ),
        )
        if changes.old_state != snapshot.view.email_state:
            raise ValueError("provider returned a mismatched email checkpoint")
        changed_ids = tuple(dict.fromkeys([*changes.created, *changes.updated]))
        fetched: dict[str, dict[str, Any]] = {}
        missing: set[str] = set(changes.destroyed)
        for start in range(0, len(changed_ids), cap):
            selected = changed_ids[start : start + cap]
            result = cycle.invoke(
                self.client,
                lambda timeout: self.client.get_metadata(
                    email_ids=selected, timeout_seconds=timeout
                ),
            )
            returned = {str(message["id"]): _safe_metadata(message) for message in result.messages}
            reconciled = set(returned) | set(result.not_found)
            if reconciled != set(selected):
                raise ValueError("provider metadata batch did not reconcile its requested IDs")
            fetched.update(returned)
            missing.update(result.not_found)
            # result.state may be newer than an intermediate changes.new_state: ignore it.
        messages = {str(message["id"]): message for message in snapshot.view.messages}
        lost = set(missing)
        for email_id in missing:
            messages.pop(email_id, None)
        for email_id, message in fetched.items():
            if self.client.metadata_matches_query(message, query):
                messages[email_id] = message
            else:
                lost.add(email_id)
                messages.pop(email_id, None)
        ordered = sorted(
            messages.values(),
            key=lambda message: (str(message.get("receivedAt", "")), str(message["id"])),
            reverse=True,
        )
        overflow = len(ordered) > budget.max_cached_messages
        needs_refill = (
            bool(lost.intersection(str(message["id"]) for message in snapshot.view.messages))
            and snapshot.view.has_more
        )
        view = replace(
            snapshot.view,
            messages=tuple(ordered[: budget.max_cached_messages]),
            complete=snapshot.view.complete and not overflow,
            has_more=snapshot.view.has_more or overflow,
            email_state=changes.new_state,
            phase="catching_up" if changes.has_more_changes else "idle",
            incremental_supported=True,
            last_success_utc=_now(),
            error_code=None,
            retry_after_utc=None,
        )
        return self._commit(snapshot, view, needs_refill=needs_refill, failures=0), lost

    def _initialize(self) -> None:
        """Add disposable sync tables to the selected gateway database."""
        assert self.m_sqlite_path is not None
        self.m_sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        new = not self.m_sqlite_path.exists()
        with self._connect() as connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS mail_sync_observations (
                scope_key TEXT PRIMARY KEY, agent_id TEXT NOT NULL, channel TEXT NOT NULL,
                binding_id TEXT NOT NULL, account_id TEXT NOT NULL, query_fingerprint TEXT NOT NULL,
                version INTEGER NOT NULL, snapshot_json TEXT NOT NULL,
                query_policy_json TEXT NOT NULL DEFAULT '{}')""")
            columns = {
                row[1] for row in connection.execute("PRAGMA table_info(mail_sync_observations)")
            }
            if "query_policy_json" not in columns:
                connection.execute(
                    "ALTER TABLE mail_sync_observations ADD COLUMN query_policy_json TEXT NOT NULL DEFAULT '{}'"
                )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS mail_sync_owner_account ON mail_sync_observations(agent_id,binding_id,account_id)"
            )
        if new:
            self.m_sqlite_path.chmod(0o600)

    def _connect(self) -> sqlite3.Connection:
        """Open finite-timeout local persistence without acquiring a network lock."""
        assert self.m_sqlite_path is not None
        return sqlite3.connect(self.m_sqlite_path, timeout=2.0)

    def _load(self) -> _Snapshot:
        """Load only this exact owner/account/view scope."""
        assert self.m_scope is not None
        with self._connect() as connection:
            row = connection.execute(
                "SELECT version,snapshot_json FROM mail_sync_observations WHERE scope_key=?",
                (self.m_scope.key,),
            ).fetchone()
        if row is None:
            return _Snapshot()
        version = int(row[0])
        try:
            data = json.loads(row[1])
            view_data = data["view"]
            if (
                view_data["phase"]
                not in {"idle", "catching_up", "rebasing", "degraded", "unsupported"}
                or len(view_data["messages"]) > 200
            ):
                raise ValueError("invalid disposable observation")
            view_data["messages"] = tuple(
                _safe_metadata(message) for message in view_data["messages"]
            )
            view_data["confirmed_ineligible"] = ()
            return _Snapshot(
                SyncView(**view_data), version, bool(data["needs_refill"]), int(data["failures"])
            )
        except (ValueError, TypeError, KeyError, AttributeError):
            # A disposable cache can be rebased; preserve the row version so the
            # first replacement still compares and commits under binding authority.
            return _Snapshot(version=version)

    def _commit(
        self, previous: _Snapshot, view: SyncView, *, needs_refill: bool, failures: int = 0
    ) -> _Snapshot:
        """Commit metadata and its checkpoint atomically under current binding authority."""
        assert self.m_scope is not None and self.m_commit_guard is not None
        scope = self.m_scope
        self._require_current_query_policy()
        persisted = replace(
            view, method_calls=0, budget_limited=False, confirmed_ineligible=(), superseded=False
        )
        payload = json.dumps(
            {"view": asdict(persisted), "needs_refill": needs_refill, "failures": failures},
            separators=(",", ":"),
            sort_keys=True,
        )

        def write() -> None:
            """Reject competing snapshots before atomically publishing a batch."""
            self._require_current_query_policy()
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute(
                    "SELECT version FROM mail_sync_observations WHERE scope_key=?", (scope.key,)
                ).fetchone()
                version = int(row[0]) if row else 0
                if version != previous.version:
                    raise _Superseded
                self._require_current_query_policy()
                connection.execute(
                    """INSERT INTO mail_sync_observations VALUES(?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(scope_key) DO UPDATE SET version=excluded.version,snapshot_json=excluded.snapshot_json,query_policy_json=excluded.query_policy_json""",
                    (
                        scope.key,
                        scope.agent_id,
                        scope.channel,
                        scope.binding_id,
                        scope.account_id,
                        scope.query_fingerprint,
                        version + 1,
                        payload,
                        scope.query_policy_json,
                    ),
                )

        if not self.m_commit_guard(write):
            raise _Superseded
        return _Snapshot(persisted, previous.version + 1, needs_refill, failures)

    def _require_current_query_policy(self) -> None:
        """Fence cached-role changes without performing provider I/O in the commit section."""
        assert self.m_scope is not None
        try:
            policy = json.loads(self.m_scope.query_policy_json)
            if not isinstance(policy, dict):
                raise ValueError("invalid cached query policy")
            query = JmapMetadataQuery(**policy)
            current = self.client.query_fingerprint(query)
        except (TypeError, ValueError, StalwartError):
            raise _Superseded("query_policy_changed") from None
        if current != self.m_scope.query_fingerprint:
            raise _Superseded("query_policy_changed")


def query_fingerprint(query: JmapMetadataQuery) -> str:
    """Fingerprint exact filter policy and the fixed non-collapsed sort contract."""
    payload = {
        "filter": asdict(query),
        "sort": "receivedAt-desc",
        "collapseThreads": False,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _safe_metadata(message: dict[str, Any]) -> dict[str, Any]:
    """Whitelist bounded metadata so bodies or provider credentials cannot persist."""
    result = {key: value for key, value in message.items() if key in _METADATA_FIELDS}
    if not isinstance(result.get("id"), str) or not result["id"]:
        raise ValueError("provider metadata has no message identity")
    if isinstance(result.get("preview"), str):
        result["preview"] = result["preview"][:512]
    if len(json.dumps(result).encode()) > 65536:
        raise ValueError("provider metadata exceeds the per-message cache budget")
    return result


def _method_error(exc: Exception) -> str | None:
    """Expose only recognized protocol codes, never raw provider exception text."""
    value = getattr(exc, "error_type", None)
    return (
        value
        if isinstance(value, str) and value in _RECOVERABLE_STATES | _UNSUPPORTED_STATES
        else None
    )


def _now() -> str:
    """Return a timezone-aware, safe last-success timestamp."""
    return datetime.now(UTC).isoformat()
