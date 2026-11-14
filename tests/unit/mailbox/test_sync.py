"""Deterministic provider-method tests for bounded, fenced mailbox observation."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import replace
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace
from typing import Any

import pytest

from houmao.mailbox.stalwart_models import (
    JmapEmailChanges,
    JmapMetadataBatch,
    JmapMetadataPage,
    JmapMetadataQuery,
    JmapOperationMeter,
    JmapQueryChanges,
)
from houmao.mailbox.sync import SyncBudget, SyncObserver, SyncScope, query_fingerprint
from houmao.mailbox.observation import observe_online, read_online_sync_status
from houmao.mailbox.online_models import OnlineAuthorityContext, OnlineFence
from houmao.mailbox.scope import MailScope


def _message(email_id: str, *, inbox: bool = True, read: bool = False) -> dict[str, Any]:
    """Build metadata with enough membership information to evaluate the exact filter."""
    return {
        "id": email_id,
        "threadId": "thread-" + email_id,
        "receivedAt": "2026-11-14T10:00:00Z",
        "subject": email_id,
        "from": [{"email": "sender@example.invalid"}],
        "to": [],
        "mailboxIds": {"inbox" if inbox else "archive": True},
        "keywords": {"$seen": True} if read else {},
        "read": read,
        "answered": False,
        "archived": not inbox,
    }


class _MethodError(RuntimeError):
    """Model a typed JMAP method failure with private text that must stay private."""

    def __init__(self, error_type: str) -> None:
        self.error_type = error_type
        super().__init__("private provider response containing secret-canary")


class _Provider:
    """Record every protocol method while serving scripted immutable wire results."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.messages: dict[str, dict[str, Any]] = {"a": _message("a")}
        self.boundary: str = "s0"
        self.get_state: str = "unrelated-newer-state"
        self.max_objects: int = 100
        self.change_responses: deque[JmapEmailChanges | Exception] = deque()
        self.query_responses: deque[JmapQueryChanges | Exception] = deque()
        self.fetch_failure: bool = False
        self.unreconciled: bool = False
        self.after_query: Callable[[], None] | None = None
        self.after_method: Callable[[], None] | None = None

    @property
    def method_call_count(self) -> int:
        """Count methods, including two methods in a page operation."""
        return len(self.calls)

    @property
    def max_objects_in_get(self) -> int:
        """Advertise a deliberately adjustable smaller provider cap."""
        return self.max_objects

    @contextmanager
    def operation_meter(
        self, *, max_method_calls: int | None = None, timeout_seconds: float | None = None
    ) -> Iterator[JmapOperationMeter]:
        """Supply deterministic local accounting for the single-threaded fake."""
        before = len(self.calls)
        meter = JmapOperationMeter(deadline=float("inf"), remaining_methods=max_method_calls)
        try:
            yield meter
        finally:
            meter.attempted_methods = len(self.calls) - before

    def _wire(self, name: str, **kwargs: Any) -> None:
        """Record method arguments and their finite timeout before responding."""
        assert kwargs["timeout_seconds"] > 0
        self.calls.append((name, kwargs))
        if self.after_method:
            self.after_method()

    def email_state(self, *, timeout_seconds: float | None = None) -> str:
        """Capture the bootstrap boundary before any query."""
        self._wire("Email/get-state", timeout_seconds=timeout_seconds)
        return self.boundary

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
        """Return only a bounded exact-filter page and record its two wire methods."""
        assert max_method_calls is not None and max_method_calls >= 2
        self._wire("Email/query", query=query, limit=limit, timeout_seconds=timeout_seconds)
        selected = [m for m in self.messages.values() if self.metadata_matches_query(m, query)]
        page = selected[position : position + limit]
        if page:
            self._wire(
                "Email/get-metadata", ids=[m["id"] for m in page], timeout_seconds=timeout_seconds
            )
        if self.after_query:
            self.after_query()
        more = len(selected) > position + limit
        return JmapMetadataPage(
            page,
            "q0",
            position,
            more,
            not more,
            position + limit if more else None,
            method_calls=2 if page else 1,
        )

    def get_metadata(
        self,
        *,
        email_ids: Sequence[str],
        timeout_seconds: float | None = None,
    ) -> JmapMetadataBatch:
        """Expose disappearing messages and failures before local checkpoint commit."""
        assert len(email_ids) <= self.max_objects
        self._wire("Email/get-metadata", ids=list(email_ids), timeout_seconds=timeout_seconds)
        if self.fetch_failure:
            raise OSError("secret-canary in transport diagnostics")
        messages = [self.messages[i] for i in email_ids if i in self.messages]
        missing = [] if self.unreconciled else [i for i in email_ids if i not in self.messages]
        return JmapMetadataBatch(messages, missing, self.get_state)

    def changes(
        self,
        *,
        since_state: str,
        max_changes: int = 100,
        timeout_seconds: float | None = None,
    ) -> JmapEmailChanges:
        """Return an intermediate response rather than replacing it with get-state."""
        self._wire(
            "Email/changes",
            since_state=since_state,
            max_changes=max_changes,
            timeout_seconds=timeout_seconds,
        )
        response = (
            self.change_responses.popleft()
            if self.change_responses
            else JmapEmailChanges(since_state, since_state, False, [], [], [])
        )
        if isinstance(response, Exception):
            raise response
        return response

    def query_changes(
        self,
        *,
        query: JmapMetadataQuery,
        since_query_state: str,
        max_changes: int = 100,
        timeout_seconds: float | None = None,
    ) -> JmapQueryChanges:
        """Use query states without inventing email-change pagination flags."""
        self._wire(
            "Email/queryChanges",
            query=query,
            since_query_state=since_query_state,
            max_changes=max_changes,
            timeout_seconds=timeout_seconds,
        )
        response = (
            self.query_responses.popleft()
            if self.query_responses
            else JmapQueryChanges(since_query_state, "q1", [])
        )
        if isinstance(response, Exception):
            raise response
        return response

    def metadata_matches_query(self, message: dict[str, Any], query: JmapMetadataQuery) -> bool:
        """Use full membership and keyword metadata without making a wire call."""
        if not message.get("mailboxIds", {}).get(query.box):
            return False
        if query.read_state == "unread" and message.get("read"):
            return False
        return True

    def query_fingerprint(self, query: JmapMetadataQuery) -> str:
        """Use a fixed fake role map with the exact query-policy fingerprint."""
        return query_fingerprint(query)


def _guard(callback: Callable[[], None]) -> bool:
    """Model a current immutable binding fence's short commit section."""
    callback()
    return True


def _observer(
    tmp_path: Path,
    client: _Provider,
    *,
    binding: str = "binding",
    account: str = "account",
    guard: Callable[[Callable[[], None]], bool] = _guard,
    query_changes: bool = False,
) -> SyncObserver:
    """Keep every observer on one gateway database with an explicitly scoped view."""
    query = JmapMetadataQuery()
    return SyncObserver.from_config(
        sqlite_path=tmp_path / "gateway.sqlite",
        client=client,
        scope=SyncScope.for_query(
            agent_id="agent", binding_id=binding, account_id=account, query=query, client=client
        ),
        commit_guard=guard,
        use_query_changes=query_changes,
    )


def test_bootstrap_boundary_precedes_query_and_interleaved_arrival(tmp_path: Path) -> None:
    """An arrival during the query is reconciled from the earlier object boundary."""
    provider = _Provider()
    provider.after_query = lambda: provider.messages.update(b=_message("b"))
    provider.change_responses.append(JmapEmailChanges("s0", "s1", False, ["b"], [], []))
    view = _observer(tmp_path, provider).observe(JmapMetadataQuery())
    assert [name for name, _ in provider.calls] == [
        "Email/get-state",
        "Email/query",
        "Email/get-metadata",
        "Email/changes",
        "Email/get-metadata",
    ]
    assert {m["id"] for m in view.messages} == {"a", "b"}
    assert view.email_state == "s1" and view.query_state == "q0"
    assert view.phase == "idle" and view.method_calls == 5
    assert all(args["timeout_seconds"] <= 10 for _, args in provider.calls)


def test_intermediate_checkpoint_survives_restart_without_borrowing_get_state(
    tmp_path: Path,
) -> None:
    """A new observer resumes exactly the fully applied intermediate object state."""
    provider = _Provider()
    provider.messages["b"] = _message("b")
    provider.change_responses.append(JmapEmailChanges("s0", "s1", True, ["b"], [], []))
    view = _observer(tmp_path, provider).observe(JmapMetadataQuery())
    assert view.email_state == "s1" and view.budget_limited
    resumed = _Provider()
    resumed.change_responses.append(JmapEmailChanges("s1", "s2", False, [], [], []))
    current = _observer(tmp_path, resumed).observe(JmapMetadataQuery())
    assert current.email_state == "s2" and current.phase == "idle"
    assert [name for name, _ in resumed.calls] == [
        "Email/query",
        "Email/get-metadata",
        "Email/changes",
    ]


def test_fetch_failure_keeps_batch_retryable_and_sanitizes_backoff(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No state advances when required metadata has not been reconciled."""
    provider = _Provider()
    observer = _observer(tmp_path, provider)
    observer.observe(JmapMetadataQuery(), SyncBudget(max_method_calls=3))
    provider.change_responses.append(JmapEmailChanges("s0", "s1", False, ["b"], [], []))
    provider.fetch_failure = True
    view = observer.observe(JmapMetadataQuery())
    assert view.email_state == "s0" and view.phase == "degraded"
    assert view.error_code == "provider_unavailable"
    assert "secret-canary" not in (tmp_path / "gateway.sqlite").read_bytes().decode(errors="ignore")
    before = len(provider.calls)
    observer.observe(JmapMetadataQuery())
    assert len(provider.calls) == before
    provider.fetch_failure = False
    provider.messages["b"] = _message("b")
    provider.change_responses.append(JmapEmailChanges("s0", "s1", False, ["b"], [], []))
    monkeypatch.setattr("houmao.mailbox.sync.time.time", lambda: (view.retry_after_utc or 0) + 1)
    assert observer.observe(JmapMetadataQuery()).email_state == "s1"


def test_authoritative_not_found_and_destroyed_remove_before_checkpoint(tmp_path: Path) -> None:
    """Missing/destroyed IDs are reconciled absence, not failed metadata fetches."""
    provider = _Provider()
    observer = _observer(tmp_path, provider)
    observer.observe(JmapMetadataQuery(), SyncBudget(max_method_calls=3))
    provider.messages.clear()
    provider.change_responses.append(JmapEmailChanges("s0", "s1", False, [], ["a"], ["destroyed"]))
    view = observer.observe(JmapMetadataQuery())
    assert view.email_state == "s1" and not view.messages
    assert set(view.confirmed_ineligible) == {"a", "destroyed"}


def test_unreconciled_metadata_does_not_advance_checkpoint(tmp_path: Path) -> None:
    """An omitted ID without authoritative notFound leaves its batch unapplied."""
    provider = _Provider()
    observer = _observer(tmp_path, provider)
    observer.observe(JmapMetadataQuery(), SyncBudget(max_method_calls=3))
    provider.unreconciled = True
    provider.change_responses.append(JmapEmailChanges("s0", "s1", False, ["missing"], [], []))
    assert observer.observe(JmapMetadataQuery()).email_state == "s0"


@pytest.mark.parametrize("error", ["cannotCalculateChanges", "tooManyChanges", "unknownMethod"])
def test_stale_or_unsupported_changes_rebases_bounded_filtered_view(
    tmp_path: Path, error: str
) -> None:
    """Recovery neither scans retained archive history nor advances from get-state."""
    provider = _Provider()
    observer = _observer(tmp_path, provider)
    observer.observe(JmapMetadataQuery())
    provider.calls.clear()
    provider.boundary = "s9"
    provider.messages = {
        "new": _message("new"),
        "old-archive": _message("old-archive", inbox=False),
    }
    provider.change_responses.append(_MethodError(error))
    view = observer.observe(JmapMetadataQuery())
    assert view.email_state == "s9" and [m["id"] for m in view.messages] == ["new"]
    assert view.phase == ("unsupported" if error == "unknownMethod" else "catching_up")
    assert view.method_calls <= 5
    queries = [args for name, args in provider.calls if name == "Email/query"]
    assert queries[0]["query"].box == "inbox" and queries[0]["limit"] == 50


def test_expired_view_cannot_wake_from_old_cache_when_rebase_yields(tmp_path: Path) -> None:
    """A known-invalid sample disappears until a new bounded query succeeds."""
    provider = _Provider()
    observer = _observer(tmp_path, provider)
    observer.observe(JmapMetadataQuery())
    provider.change_responses.append(_MethodError("cannotCalculateChanges"))
    view = observer.observe(JmapMetadataQuery(), SyncBudget(max_method_calls=2))
    assert not view.messages and view.budget_limited and view.phase == "rebasing"


def test_binding_account_and_query_policy_scopes_do_not_share_overlap_ids(tmp_path: Path) -> None:
    """A refreshed connection resumes; another account starts its own checkpoint."""
    old = _Provider()
    _observer(tmp_path, old).observe(JmapMetadataQuery())
    refreshed = _Provider()
    assert _observer(tmp_path, refreshed).observe(JmapMetadataQuery()).email_state == "s0"
    assert [name for name, _ in refreshed.calls] == ["Email/changes"]
    other = _Provider()
    other.boundary = "other-state"
    other.messages["a"]["subject"] = "other-account"
    view = _observer(tmp_path, other, account="other").observe(JmapMetadataQuery())
    assert view.email_state == "other-state" and view.messages[0]["subject"] == "other-account"
    assert other.calls[0][0] == "Email/get-state"
    with pytest.raises(ValueError, match="view scope"):
        _observer(tmp_path, other).observe(JmapMetadataQuery(read_state="unread"))


def test_superseded_worker_never_commits_or_exposes_old_metadata(tmp_path: Path) -> None:
    """A replacement fence can reject a completed query before publication."""
    provider = _Provider()
    alive = True

    def guard(callback: Callable[[], None]) -> bool:
        """Retire the epoch after boundary capture, before query publication."""
        if not alive:
            return False
        callback()
        return True

    def retire() -> None:
        """Simulate binding replacement while the provider request is outstanding."""
        nonlocal alive
        alive = False

    provider.after_query = retire
    observer = _observer(tmp_path, provider, guard=guard)
    view = observer.observe(JmapMetadataQuery())
    assert view.superseded and not view.messages
    assert observer.snapshot().query_state is None


def test_failed_local_transaction_keeps_metadata_and_checkpoint_together(tmp_path: Path) -> None:
    """An SQLite failure cannot persist half of a provider change response."""
    provider = _Provider()
    observer = _observer(tmp_path, provider)
    observer.observe(JmapMetadataQuery(), SyncBudget(max_method_calls=3))
    with sqlite3.connect(tmp_path / "gateway.sqlite") as connection:
        connection.execute(
            "CREATE TRIGGER reject_batch BEFORE UPDATE ON mail_sync_observations BEGIN SELECT RAISE(FAIL, 'local failure'); END"
        )
    provider.messages["b"] = _message("b")
    provider.change_responses.append(JmapEmailChanges("s0", "s1", False, ["b"], [], []))
    view = observer.observe(JmapMetadataQuery())
    assert view.error_code == "local_commit_failed"
    assert observer.snapshot().email_state == "s0"
    assert [m["id"] for m in observer.snapshot().messages] == ["a"]


def test_cache_eviction_is_a_sample_and_never_confirmed_loss_of_eligibility(tmp_path: Path) -> None:
    """The window stays finite while evicted work remains provider-owned inbox mail."""
    provider = _Provider()
    observer = _observer(tmp_path, provider)
    limits = SyncBudget(max_cached_messages=2, window_size=2)
    observer.observe(JmapMetadataQuery(), replace(limits, max_method_calls=3))
    provider.messages.update({key: _message(key) for key in ("b", "c", "d")})
    provider.change_responses.append(JmapEmailChanges("s0", "s1", False, ["b", "c", "d"], [], []))
    view = observer.observe(JmapMetadataQuery(), limits)
    assert len(view.messages) == 2 and view.has_more and not view.complete
    assert view.confirmed_ineligible == () and len(provider.messages) == 4


def test_provider_smaller_get_cap_bounds_changes_and_metadata_batch(tmp_path: Path) -> None:
    """The observer requests no more changed IDs than the remaining get budget."""
    provider = _Provider()
    provider.max_objects = 2
    observer = _observer(tmp_path, provider)
    observer.observe(JmapMetadataQuery())
    provider.calls.clear()
    provider.messages.update(b=_message("b"), c=_message("c"))
    provider.change_responses.append(JmapEmailChanges("s0", "s1", True, ["b", "c"], [], []))
    view = observer.observe(JmapMetadataQuery(), SyncBudget(max_method_calls=2))
    assert provider.calls[0][1]["max_changes"] == 2
    assert view.method_calls == 2 and view.budget_limited


def test_time_budget_yields_after_durable_boundary_without_another_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A slow state read cannot leave an unbounded timeout for the next request."""
    clock = [0.0]
    monkeypatch.setattr("houmao.mailbox.sync.time.monotonic", lambda: clock[0])
    provider = _Provider()
    provider.after_method = lambda: clock.__setitem__(0, 11.0)
    observer = _observer(tmp_path, provider)
    view = observer.observe(JmapMetadataQuery())
    assert view.budget_limited and view.email_state == "s0"
    assert len(provider.calls) == 1
    assert observer.snapshot().phase == "rebasing"


def test_persistence_excludes_bodies_credentials_and_bounds_preview(tmp_path: Path) -> None:
    """Even an over-rich provider object cannot turn the cache into a body mirror."""
    provider = _Provider()
    provider.messages["a"].update(
        body="body-canary",
        bodyValues={"x": "body-canary"},
        credential="secret-canary",
        preview="p" * 2000,
    )
    observer = _observer(tmp_path, provider)
    view = observer.observe(JmapMetadataQuery())
    assert len(view.messages[0]["preview"]) == 512
    with sqlite3.connect(tmp_path / "gateway.sqlite") as connection:
        text = connection.execute("SELECT snapshot_json FROM mail_sync_observations").fetchone()[0]
    assert "body-canary" not in text and "secret-canary" not in text
    assert "bodyValues" not in json.loads(text)["view"]["messages"][0]


@pytest.mark.parametrize("failure", ["tooManyChanges", "cannotCalculateChanges", "unknownMethod"])
def test_qualified_query_changes_errors_use_one_bounded_requery(
    tmp_path: Path, failure: str
) -> None:
    """No query delta is retried with an unlimited bound or a fictitious page flag."""
    provider = _Provider()
    observer = _observer(tmp_path, provider, query_changes=True)
    observer.observe(JmapMetadataQuery())
    provider.calls.clear()
    provider.query_responses.append(_MethodError(failure))
    view = observer.observe(JmapMetadataQuery())
    names = [name for name, _ in provider.calls]
    assert names.count("Email/queryChanges") == 1 and names.count("Email/query") == 1
    assert view.method_calls <= 5 and view.email_state == "s0"
    assert provider.calls[0][1]["max_changes"] == 100


def test_query_state_progress_never_becomes_an_email_checkpoint(tmp_path: Path) -> None:
    """An empty qualified query delta updates only its exact-filter state."""
    provider = _Provider()
    observer = _observer(tmp_path, provider, query_changes=True)
    observer.observe(JmapMetadataQuery())
    provider.query_responses.append(JmapQueryChanges("q0", "q999", []))
    view = observer.observe(JmapMetadataQuery())
    assert view.query_state == "q999" and view.email_state == "s0"
    assert view.method_calls == 2


@pytest.mark.parametrize("seconds", [0.0, float("inf"), float("nan")])
def test_sync_budget_rejects_nonfinite_time(seconds: float) -> None:
    """No configured cycle may become an unbounded network operation."""
    with pytest.raises(ValueError, match="finite"):
        SyncBudget(max_seconds=seconds)


class _Authority:
    """Supply a fake validated connection while enforcing an immutable final fence."""

    def __init__(self, provider: _Provider) -> None:
        self.provider = provider
        self.alive = True
        self.inside_commit = False
        self.fence = OnlineFence("agent", "session", "binding", "revision", "epoch", "account")

    def capture_connection(self, **kwargs: Any) -> SimpleNamespace:
        """Represent already finite/cached epoch validation, outside cycle accounting."""
        assert kwargs["expected_binding_id"] == "binding"
        return SimpleNamespace(client=self.provider, fence=self.fence)

    def commit_observation(self, fence: OnlineFence, callback: Callable[[], None]) -> bool:
        """Expose a short authority section containing SQLite only."""
        assert fence == self.fence
        if not self.alive:
            return False
        self.inside_commit = True
        try:
            callback()
        finally:
            self.inside_commit = False
        return True


def _online_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[_Provider, _Authority, dict[str, Any]]:
    """Build a selected owner/runtime connection without importing private credentials."""
    provider = _Provider()
    authority = _Authority(provider)
    monkeypatch.setattr(
        "houmao.mailbox.observation.OnlineConnectionAuthority.from_context",
        lambda context: authority,
    )
    return (
        provider,
        authority,
        {
            "context": OnlineAuthorityContext(tmp_path / "manifest.json", "agent", "session"),
            "sqlite_path": tmp_path / "gateway.sqlite",
            "binding_id": "binding",
            "mode": "any_inbox",
        },
    )


def test_online_observation_normalizes_scoped_metadata_without_body_or_network_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The reusable helper supplies direct notifier inputs and keeps I/O lock-free."""
    provider, authority, args = _online_fixture(tmp_path, monkeypatch)

    def check_lock() -> None:
        """Fail if any provider method runs inside a fenced local commit."""
        assert not authority.inside_commit

    provider.after_method = check_lock
    observation = observe_online(**args)
    scope = MailScope("agent", "online", "binding")
    assert scope.decode(observation.messages[0].message_ref) == "stalwart:a"
    assert observation.messages[0].body_text is None
    assert observation.fence == authority.fence and observation.complete
    assert observation.sync_view.method_calls <= 5


def test_revalidation_preserves_evicted_eligible_compaction_and_clears_confirmed_loss(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A sample omission is unknown until a bounded get confirms current eligibility."""
    provider, _, args = _online_fixture(tmp_path, monkeypatch)
    provider.messages.update(b=_message("b", inbox=False), c=_message("c"))
    scope = MailScope("agent", "online", "binding")
    references = {key: scope.encode("stalwart:" + key) for key in ("a", "b", "c", "missing")}
    observation = observe_online(
        **args,
        compacted=list(references.values()),
        budget=SyncBudget(window_size=1, max_cached_messages=1),
    )
    assert observation.confirmed_ineligible == tuple(
        sorted([references["b"], references["missing"]])
    )
    assert references["c"] not in observation.confirmed_ineligible
    assert not observation.complete and observation.sync_view.method_calls == 5


def test_revalidation_cursor_rotates_across_restart_with_only_one_remaining_get(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A large remembered set is checked over bounded cycles rather than rescanned."""
    provider, _, args = _online_fixture(tmp_path, monkeypatch)
    observe_online(**args)
    provider.max_objects = 2
    scope = MailScope("agent", "online", "binding")
    references = [scope.encode("stalwart:missing-" + str(i)) for i in range(6)]
    confirmed = set()
    for _ in range(3):
        observation = observe_online(
            **args, compacted=references, budget=SyncBudget(max_method_calls=2)
        )
        confirmed.update(observation.confirmed_ineligible)
        assert observation.sync_view.method_calls == 2
    assert confirmed == set(references)


def test_no_remaining_budget_preserves_uncertain_compaction_memory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A busy sync cycle cannot turn an unqueried remembered item into new work."""
    provider, _, args = _online_fixture(tmp_path, monkeypatch)
    provider.messages["b"] = _message("b")
    provider.change_responses.append(JmapEmailChanges("s0", "s1", True, ["b"], [], []))
    remembered = MailScope("agent", "online", "binding").encode("stalwart:missing")
    observation = observe_online(**args, compacted=[remembered])
    assert observation.confirmed_ineligible == ()
    assert observation.sync_view.method_calls == 5


def test_final_fence_rejects_late_revalidation_and_wakeup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Replacement between metadata observation and final admission exposes no old work."""
    provider, authority, args = _online_fixture(tmp_path, monkeypatch)
    remembered = MailScope("agent", "online", "binding").encode("stalwart:missing")

    def retire_after_last_get() -> None:
        """Invalidate the epoch after revalidation, before its result publication."""
        if provider.method_call_count == 5:
            authority.alive = False

    provider.after_method = retire_after_last_get
    result = observe_online(**args, compacted=[remembered])
    assert result.sync_view.superseded and not result.messages
    assert result.confirmed_ineligible == ()


def test_status_after_restart_is_safe_and_scoped_without_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Status reads only persisted progress for the selected owner/account/mode."""
    provider, _, args = _online_fixture(tmp_path, monkeypatch)
    observe_online(**args)
    before = provider.method_call_count
    status = read_online_sync_status(
        args["sqlite_path"],
        agent_id="agent",
        binding_id="binding",
        account_id="account",
        mode="any_inbox",
    )
    assert status["available"] and status["views"][0]["cached_count"] == 1
    assert "messages" not in json.dumps(status) and provider.method_call_count == before
    assert not read_online_sync_status(
        args["sqlite_path"],
        agent_id="agent",
        binding_id="other",
        account_id="account",
        mode="any_inbox",
    )["available"]
    assert not read_online_sync_status(
        args["sqlite_path"],
        agent_id="agent",
        binding_id="binding",
        account_id="account",
        mode="unread_only",
    )["available"]


def test_disposable_cache_loss_or_invalid_json_rebases_without_reconstructing_mail_truth(
    tmp_path: Path,
) -> None:
    """A broken metadata row is replaced through the same fenced bootstrap path."""
    provider = _Provider()
    observer = _observer(tmp_path, provider)
    observer.observe(JmapMetadataQuery())
    with sqlite3.connect(tmp_path / "gateway.sqlite") as connection:
        connection.execute("UPDATE mail_sync_observations SET snapshot_json='invalid-json'")
    provider.calls.clear()
    assert observer.observe(JmapMetadataQuery()).email_state == "s0"
    assert provider.calls[0][0] == "Email/get-state"
    with sqlite3.connect(tmp_path / "gateway.sqlite") as connection:
        connection.execute("DELETE FROM mail_sync_observations")
    provider.calls.clear()
    assert observer.observe(JmapMetadataQuery()).messages
    assert provider.calls[0][0] == "Email/get-state"


def test_query_policy_change_inside_commit_guard_keeps_old_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Recheck policy inside the short authority guard, not only before acquiring it."""
    provider = _Provider()
    fingerprint = provider.query_fingerprint
    policy_changed = False
    commits = 0

    def current(query: JmapMetadataQuery) -> str:
        """Represent a cached mailbox-role map changed by another request."""
        return "new-role-policy" if policy_changed else fingerprint(query)

    monkeypatch.setattr(provider, "query_fingerprint", current)

    def commit(callback: Callable[[], None]) -> bool:
        """Change roles after preflight but before the query snapshot write."""
        nonlocal policy_changed, commits
        commits += 1
        if commits == 2:
            policy_changed = True
        callback()
        return True

    observer = _observer(tmp_path, provider, guard=commit)
    view = observer.observe(JmapMetadataQuery())
    assert view.superseded and view.error_code == "query_policy_changed" and not view.messages
    assert observer.snapshot().email_state == "s0"
    assert observer.snapshot().query_state is None


def test_role_policy_change_before_final_revalidation_publish_discards_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A late role refresh cannot clear remembered compaction eligibility or wake old work."""
    provider, _, args = _online_fixture(tmp_path, monkeypatch)
    fingerprint = provider.query_fingerprint
    changed = False

    def current(query: JmapMetadataQuery) -> str:
        """Read a pure policy fingerprint without issuing provider requests."""
        return "new-role-policy" if changed else fingerprint(query)

    def refresh_after_revalidation() -> None:
        """Retire the captured policy after remembered-message I/O completes."""
        nonlocal changed
        if provider.method_call_count == 5:
            changed = True

    monkeypatch.setattr(provider, "query_fingerprint", current)
    provider.after_method = refresh_after_revalidation
    remembered = MailScope("agent", "online", "binding").encode("stalwart:missing")
    result = observe_online(**args, compacted=[remembered])
    assert result.sync_view.superseded and result.sync_view.error_code == "query_policy_changed"
    assert result.messages == [] and result.confirmed_ineligible == ()
    with sqlite3.connect(args["sqlite_path"]) as connection:
        assert connection.execute("SELECT count(*) FROM mail_sync_revalidation").fetchone() == (0,)
