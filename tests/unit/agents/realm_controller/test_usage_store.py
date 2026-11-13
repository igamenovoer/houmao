"""Persistence, crash, concurrency, and cursor tests for the usage ledger."""

from __future__ import annotations

import base64
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import sqlite3

import pytest

from houmao.agents.realm_controller.usage_models import (
    UsageCheckpoint,
    UsageCollectionHealth,
    UsageFinalization,
    UsageObservation,
    UsageRecord,
    UsageSourceBinding,
    UsageTurnSnapshot,
)
from houmao.agents.realm_controller.usage_store import (
    UsageCheckpointConflictError,
    UsageConflictError,
    UsageCursorError,
    UsageStore,
    UsageStoreError,
    UsageStoreSchemaError,
)


def _store(tmp_path: Path) -> UsageStore:
    """Create an independent runtime ledger."""

    return UsageStore.from_path(tmp_path / "usage" / "records.sqlite3", "runtime-a")


def _record(turn_id: str, *, started: str = "2026-11-13T00:00:00Z") -> UsageRecord:
    """Build a record whose input times do not affect stream sequence."""

    return UsageRecord(
        agent_id="agent-a",
        runtime_session_id="runtime-a",
        turn_id=turn_id,
        backend="codex_headless",
        provider="codex",
        generation_id="generation-a",
        outcome="completed",
        started_at_utc=started,
        completed_at_utc="2026-11-13T00:01:00Z",
    )


def _binding() -> UsageSourceBinding:
    """Build a private persisted ownership boundary."""

    return UsageSourceBinding(
        binding_id="binding-a",
        agent_id="agent-a",
        runtime_session_id="runtime-a",
        provider="codex",
        home_path="/private/provider",
        provider_session_id="thread-a",
        collection_boundary={"source-a": 100},
    )


def _checkpoint(offset: int = 120) -> UsageCheckpoint:
    """Build the next complete JSONL source position."""

    return UsageCheckpoint(
        binding_id="binding-a", source_id="source-a", file_identity="inode-a", offset=offset
    )


def _observation(identifier: str = "response-a", *, source: str = "native:1") -> UsageObservation:
    """Build one scoped request observation."""

    return UsageObservation(
        observation_id=identifier,
        provider="codex",
        provider_session_id="thread-a",
        provider_turn_id="native-a",
        request_id=identifier,
        measurement_scope="request",
        values={"input_tokens": 10},
        source_ref=source,
    )


def _snapshot(turn_id: str = "turn-a") -> UsageTurnSnapshot:
    """Build original generation and timing evidence."""

    return UsageTurnSnapshot(
        agent_id="agent-a",
        runtime_session_id="runtime-a",
        turn_id=turn_id,
        backend="codex_headless",
        provider="codex",
        generation_id="generation-a",
        started_at_utc="2026-11-13T00:00:00Z",
        binding_id="binding-a",
    )


def test_initial_empty_cursor_remains_resumable_after_append(tmp_path: Path) -> None:
    """An empty first page has a useful cursor for future finalized turns."""

    store = _store(tmp_path)
    empty = store.read_page()
    assert empty.records == []
    assert empty.next_cursor is not None
    assert empty.has_more is False
    assert store.finalize(_record("turn-a")) is True
    page = store.read_page(after=empty.next_cursor)
    assert [record.turn_id for record in page.records] == ["turn-a"]
    assert page.next_cursor is not None
    assert page.has_more is False
    again = store.read_page(after=page.next_cursor)
    assert again.records == []
    assert again.next_cursor == page.next_cursor


def test_pages_order_by_finalization_and_preserve_late_turns(tmp_path: Path) -> None:
    """Late finalization is visible even when its start time is earlier."""

    store = _store(tmp_path)
    for turn_id in ("newer-a", "newer-b", "newer-c"):
        store.finalize(_record(turn_id))
    first = store.read_page(limit=2)
    assert first.has_more is True
    second = store.read_page(after=first.next_cursor, limit=2)
    assert [record.turn_id for record in second.records] == ["newer-c"]
    store.finalize(_record("late-old", started="2026-11-12T00:00:00Z"))
    assert [record.turn_id for record in store.read_page(after=second.next_cursor).records] == [
        "late-old"
    ]


def test_finalization_replay_is_immutable_and_does_not_advance_cursor(tmp_path: Path) -> None:
    """Equivalent replay is a no-op and conflicting accounting stays explicit."""

    store = _store(tmp_path)
    record = _record("turn-a")
    assert store.finalize(record)
    cursor = store.read_page().next_cursor
    assert store.finalize(record) is False
    assert store.read_page().next_cursor == cursor
    with pytest.raises(UsageConflictError):
        store.finalize(record.model_copy(update={"outcome": "interrupted"}))
    assert store.get_record("turn-a") == record


def test_restart_and_provider_reset_preserve_runtime_stream(tmp_path: Path) -> None:
    """A controller replacement does not reset history or cursor identity."""

    store = _store(tmp_path)
    store.finalize(_record("turn-a"))
    first = store.read_page()
    restarted = UsageStore.from_path(store.path, "runtime-a")
    assert restarted.stream_id == store.stream_id
    restarted.finalize(
        _record("turn-b").model_copy(
            update={"generation_id": "generation-b", "provider_session_id": "new-chat"}
        )
    )
    page = restarted.read_page(after=first.next_cursor)
    assert [record.turn_id for record in page.records] == ["turn-b"]
    assert page.records[0].generation_id == "generation-b"


@pytest.mark.parametrize("cursor", ["", "garbage", "%%%%", "eyJ2ZXJzaW9uIjoxfQ"])
def test_malformed_cursors_fail_without_restarting_history(tmp_path: Path, cursor: str) -> None:
    """Invalid tokens never fall back to an unbounded initial query."""

    with pytest.raises(UsageCursorError):
        _store(tmp_path).read_page(after=cursor)


def test_wrong_stream_future_position_and_invalid_limits_fail(tmp_path: Path) -> None:
    """Enforce stream incarnation and caller page bounds."""

    store = _store(tmp_path)
    other = UsageStore.from_path(tmp_path / "other.sqlite3", "runtime-a")
    with pytest.raises(UsageCursorError):
        store.read_page(after=other.read_page().next_cursor)
    future = base64.urlsafe_b64encode(
        json.dumps({"version": 1, "stream_id": store.stream_id, "sequence": 10}).encode()
    ).decode()
    with pytest.raises(UsageCursorError):
        store.read_page(after=future)
    for limit in (0, 501, True):
        with pytest.raises(UsageCursorError):
            store.read_page(limit=limit)


def test_replaced_store_has_new_stream_incarnation(tmp_path: Path) -> None:
    """Deleting a database cannot silently reuse issued cursor positions."""

    original = _store(tmp_path)
    cursor = original.read_page().next_cursor
    original.path.unlink()
    replacement = UsageStore.from_path(original.path, "runtime-a")
    assert replacement.stream_id != original.stream_id
    with pytest.raises(UsageCursorError):
        replacement.read_page(after=cursor)
    with pytest.raises(UsageStoreSchemaError):
        original.read_page()


def test_foreign_database_and_schema_mismatch_are_not_migrated(tmp_path: Path) -> None:
    """Reject unrelated gateway storage without mutating it."""

    foreign = tmp_path / "queue.sqlite"
    with sqlite3.connect(foreign) as connection:
        connection.execute("CREATE TABLE gateway_queue (request_id TEXT)")
    original = hashlib.sha256(foreign.read_bytes()).digest()
    with pytest.raises(UsageStoreSchemaError):
        UsageStore.from_path(foreign, "runtime-a")
    assert hashlib.sha256(foreign.read_bytes()).digest() == original
    store = _store(tmp_path)
    with sqlite3.connect(store.path) as connection:
        connection.execute("UPDATE store_metadata SET value='99' WHERE key='schema_version'")
    with pytest.raises(UsageStoreSchemaError):
        UsageStore.from_path(store.path, "runtime-a")


def test_runtime_identity_mismatch_and_corrupt_database_are_explicit(tmp_path: Path) -> None:
    """Ownership and unreadability never become successful empty history."""

    store = _store(tmp_path)
    with pytest.raises(UsageStoreSchemaError):
        UsageStore.from_path(store.path, "another-runtime")
    corrupt = tmp_path / "corrupt.sqlite3"
    corrupt.write_text("not a database", encoding="utf-8")
    with pytest.raises(UsageStoreError, match="unavailable or unreadable"):
        UsageStore.from_path(corrupt, "runtime-a")


def test_ingestion_commits_evidence_and_checkpoint_together(tmp_path: Path) -> None:
    """Checkpoint progress represents only accepted observations."""

    store = _store(tmp_path)
    store.put_binding(_binding())
    checkpoint = store.ingest_batch(checkpoint=_checkpoint(), observations=[_observation()])
    assert checkpoint.version == 1
    assert store.get_checkpoint("binding-a", "source-a") == checkpoint
    assert len(store.list_observations(binding_id="binding-a", provider_turn_id="native-a")) == 1
    with pytest.raises(UsageCheckpointConflictError):
        store.ingest_batch(
            checkpoint=_checkpoint(140),
            observations=[_observation("lost-response")],
            expected_version=0,
        )
    assert len(store.list_observations()) == 1
    assert store.get_checkpoint("binding-a", "source-a") == checkpoint


def test_crash_between_observation_and_checkpoint_rolls_back_batch(tmp_path: Path) -> None:
    """An injected checkpoint-write failure leaves the whole batch reprocessable."""

    store = _store(tmp_path)
    store.put_binding(_binding())
    with sqlite3.connect(store.path) as connection:
        connection.execute(
            "CREATE TRIGGER checkpoint_failure BEFORE INSERT ON source_checkpoints BEGIN SELECT RAISE(ABORT,'injected'); END"
        )
    with pytest.raises(UsageStoreError):
        store.ingest_batch(checkpoint=_checkpoint(), observations=[_observation()])
    assert store.get_checkpoint("binding-a", "source-a") is None
    assert store.list_observations() == []
    with sqlite3.connect(store.path) as connection:
        connection.execute("DROP TRIGGER checkpoint_failure")
    store.ingest_batch(checkpoint=_checkpoint(), observations=[_observation()])
    assert len(store.list_observations()) == 1


def test_competing_collectors_have_one_checkpoint_winner(tmp_path: Path) -> None:
    """Concurrent stale batches cannot both advance source progress."""

    store = _store(tmp_path)
    store.put_binding(_binding())

    def ingest(identifier: str) -> bool:
        """Attempt the same initial source position from a separate connection."""

        try:
            store.ingest_batch(checkpoint=_checkpoint(), observations=[_observation(identifier)])
            return True
        except UsageCheckpointConflictError:
            return False

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(ingest, ("response-a", "response-b")))
    assert sorted(results) == [False, True]
    assert len(store.list_observations()) == 1


def test_provisional_variants_are_retained_but_identical_replay_is_not(tmp_path: Path) -> None:
    """The assembler can reconcile stdout/native evidence for one request."""

    store = _store(tmp_path)
    store.put_binding(_binding())
    first = store.ingest_batch(checkpoint=_checkpoint(), observations=[_observation()])
    second = store.ingest_batch(
        checkpoint=_checkpoint(140),
        observations=[_observation(), _observation(source="stdout:3")],
        expected_version=first.version,
    )
    assert second.version == 2
    observations = store.list_observations()
    assert len(observations) == 2
    assert {item.observation_id for item in observations} == {"response-a"}


def test_native_alias_prevents_independent_managed_and_native_turns(tmp_path: Path) -> None:
    """Provider association resolves to one pending accounting identity."""

    store = _store(tmp_path)
    pending = store.put_pending_turn(_snapshot())
    associated = store.associate_provider_turn(
        pending.snapshot.turn_id,
        binding_id="binding-a",
        provider_session_id="thread-a",
        provider_turn_id="native-a",
    )
    assert associated.snapshot.provider_turn_id == "native-a"
    assert (
        store.resolve_turn_id(
            binding_id="binding-a", provider_session_id="thread-a", provider_turn_id="native-a"
        )
        == "turn-a"
    )
    with pytest.raises(UsageConflictError):
        store.put_pending_turn(
            associated.snapshot.model_copy(update={"turn_id": "another-accounting-turn"})
        )
    assert store.get_pending_turn("another-accounting-turn") is None


def test_finalization_closes_pending_work_and_preserves_original_facts(tmp_path: Path) -> None:
    """Normal and recovery paths use the same identity and terminal facts."""

    store = _store(tmp_path)
    snapshot = _snapshot()
    store.put_pending_turn(snapshot)
    terminal = UsageFinalization(
        turn_id="turn-a",
        outcome="completed",
        completed_at_utc="2026-11-13T00:01:00Z",
        wall_time_ms=60_000,
    )
    store.set_finalization("turn-a", terminal)
    assert store.finalize(_record("turn-a"))
    assert store.list_pending_turns() == []
    assert store.list_pending_turns(include_finalized=True)[0].finalization == terminal
    with pytest.raises(UsageConflictError):
        store.put_pending_turn(snapshot.model_copy(update={"generation_id": "new-generation"}))


def test_failed_pending_close_rolls_back_final_row(tmp_path: Path) -> None:
    """A final row cannot commit while its pending turn remains unfinished."""

    store = _store(tmp_path)
    store.put_pending_turn(_snapshot())
    with sqlite3.connect(store.path) as connection:
        connection.execute(
            "CREATE TRIGGER pending_failure BEFORE UPDATE ON pending_turns BEGIN SELECT RAISE(ABORT,'injected'); END"
        )
    with pytest.raises(UsageStoreError):
        store.finalize(_record("turn-a"))
    assert store.get_record("turn-a") is None
    assert len(store.list_pending_turns()) == 1


def test_degraded_collection_health_does_not_erase_history(tmp_path: Path) -> None:
    """Collection diagnostics are mutable independently of finalized records."""

    store = _store(tmp_path)
    store.finalize(_record("turn-a"))
    store.set_collection_health(
        UsageCollectionHealth(status="degraded", diagnostics=["source_unreadable"])
    )
    page = store.read_page()
    assert page.collection.status == "degraded"
    assert [record.turn_id for record in page.records] == ["turn-a"]
