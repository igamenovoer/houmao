"""Bound ownership, checkpoint recovery, and source continuity regression tests."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
from typing import Any

import pytest

from houmao.agents.realm_controller import usage_collection
from houmao.agents.realm_controller.usage_adapters import UsageAdapter
from houmao.agents.realm_controller.usage_collection import (
    UsageCollector,
    complete_file_position,
    discover_usage_sources,
    source_file_identity,
)
from houmao.agents.realm_controller.usage_models import (
    UsageCheckpoint,
    UsageObservation,
    UsageSourceBinding,
    opaque_usage_reference,
)
from houmao.agents.realm_controller.usage_store import UsageStore


def _line(payload: dict[str, Any]) -> str:
    """Encode one complete fixture record."""

    return json.dumps(payload, separators=(",", ":")) + "\n"


def _write(path: Path, records: list[dict[str, Any]]) -> None:
    """Replace a fixture source while keeping its existing inode when present."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(_line(record) for record in records), encoding="utf-8")


def _append(path: Path, records: list[dict[str, Any]]) -> None:
    """Append complete provider records to a bound source."""

    with path.open("a", encoding="utf-8") as handle:
        handle.write("".join(_line(record) for record in records))


def _meta(session: str = "thread-a") -> dict[str, Any]:
    """Build explicit Codex thread ownership metadata."""

    return {"type": "session_meta", "payload": {"id": session}}


def _start(turn: str = "native-a", *, timestamp: str | None = None) -> dict[str, Any]:
    """Build a native turn-start marker."""

    result: dict[str, Any] = {
        "type": "event_msg",
        "payload": {"type": "task_started", "turn_id": turn},
    }
    if timestamp is not None:
        result["timestamp"] = timestamp
    return result


def _end(turn: str = "native-a", *, timestamp: str | None = None) -> dict[str, Any]:
    """Build a native terminal marker."""

    result: dict[str, Any] = {
        "type": "event_msg",
        "payload": {"type": "task_complete", "turn_id": turn},
    }
    if timestamp is not None:
        result["timestamp"] = timestamp
    return result


def _request(
    response: str = "response-a",
    turn: str = "native-a",
    *,
    session: str = "thread-a",
    timestamp: str | None = None,
) -> dict[str, Any]:
    """Build a distinct request with explicit native thread and turn identity."""

    result: dict[str, Any] = {
        "type": "token_usage_record",
        "payload": {
            "thread_id": session,
            "turn_id": turn,
            "response_id": response,
            "usage": {"input_tokens": 100, "output_tokens": 10},
        },
    }
    if timestamp is not None:
        result["timestamp"] = timestamp
    return result


def _count(total: int, last: int) -> dict[str, Any]:
    """Build a legacy snapshot relying on checkpointed native turn context."""

    return {
        "type": "event_msg",
        "payload": {
            "type": "token_count",
            "info": {
                "total_token_usage": {"input_tokens": total},
                "last_token_usage": {"input_tokens": last},
            },
        },
    }


def _binding(
    home: Path, *, provider: str = "codex", session: str = "thread-a", fresh: bool = True
) -> UsageSourceBinding:
    """Build an explicitly bound source family in a private fixture home."""

    return UsageSourceBinding(
        binding_id="binding-a",
        runtime_session_id="runtime-a",
        agent_id="agent-a",
        provider=provider,
        home_path=str(home),
        provider_session_id=session,
        generation_id="generation-a",
        metadata={"fresh_session": fresh},
    )


def _collector(tmp_path: Path, binding: UsageSourceBinding) -> UsageCollector:
    """Bind a collector to a fresh independent fixture ledger."""

    store = UsageStore.from_path(tmp_path / "ledger" / "records.sqlite3", "runtime-a")
    return UsageCollector.from_binding(store, binding)


def _requests(items: list[UsageObservation]) -> list[UsageObservation]:
    """Select request measurements independently of lifecycle observations."""

    return [item for item in items if item.kind == "request"]


def test_discovery_uses_explicit_session_ownership_and_rejects_symlink_escape(
    tmp_path: Path,
) -> None:
    """A shared home and matching filenames never merge unrelated sessions."""

    home = tmp_path / "home"
    owned = home / "sessions" / "owned.jsonl"
    foreign = home / "sessions" / "thread-a-but-foreign.jsonl"
    outside = tmp_path / "outside.jsonl"
    _write(owned, [_meta()])
    _write(foreign, [_meta("thread-b"), _request()])
    _write(outside, [_meta()])
    (home / "sessions" / "escape.jsonl").symlink_to(outside)
    assert discover_usage_sources(_binding(home)) == [owned]


def test_discovery_prefers_active_relative_rollout_without_basename_collisions(
    tmp_path: Path,
) -> None:
    """Archive copies yield to active files only at the same relative path."""

    home = tmp_path / "home"
    active = home / "sessions" / "day-a" / "rollout.jsonl"
    archived = home / "archived_sessions" / "day-a" / "rollout.jsonl"
    another = home / "sessions" / "day-b" / "rollout.jsonl"
    for path in (active, archived, another):
        _write(path, [_meta()])
    assert set(discover_usage_sources(_binding(home))) == {active, another}


def test_kimi_session_must_occupy_the_qualified_layout_position(tmp_path: Path) -> None:
    """A session name occurring only in an ancestor is not ownership evidence."""

    home = tmp_path / "session-a" / "home"
    genuine = home / "sessions" / "workspace" / "session-a" / "agents" / "main" / "wire.jsonl"
    legacy = home / "sessions" / "workspace" / "session-a" / "wire.jsonl"
    wrong = (
        home / "sessions" / "workspace" / "other-session" / "agents" / "session-a" / "wire.jsonl"
    )
    for path in (genuine, legacy, wrong):
        _write(path, [])
    assert set(discover_usage_sources(_binding(home, provider="kimi", session="session-a"))) == {
        genuine,
        legacy,
    }


def test_partial_header_completion_does_not_change_physical_source_identity(tmp_path: Path) -> None:
    """Finishing a first JSONL record is an append rather than a source reset."""

    path = tmp_path / "header.jsonl"
    path.write_text('{"type":"session_meta"', encoding="utf-8")
    before = source_file_identity(path)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(',"payload":{"id":"thread-a"}}\n')
    assert source_file_identity(path) == before


def test_earlier_partial_header_checkpoint_keeps_its_epoch(tmp_path: Path) -> None:
    """Existing partial-header checkpoint identities survive the completed header."""

    home = tmp_path / "home"
    path = home / "sessions" / "rollout.jsonl"
    _write(path, [_meta(), _start(), _request()])
    collector = _collector(tmp_path, _binding(home))
    assert collector.m_store is not None
    collector.m_store.ingest_batch(
        checkpoint=UsageCheckpoint(
            binding_id="binding-a",
            source_id=opaque_usage_reference(str(path)),
            file_identity=source_file_identity(path) + ":partial",
            metadata={
                "adapter_state": UsageAdapter.from_provider("codex", "thread-a").snapshot_state()
            },
        ),
        observations=[],
    )
    accepted = collector.collect()
    assert len(_requests(accepted)) == 1
    assert collector.diagnostics == []
    assert _requests(accepted)[0].metadata["counter_epoch"] == "initial"


def test_partial_line_waits_and_restart_restores_adapter_state(tmp_path: Path) -> None:
    """A record completed after restart keeps its prior native turn association."""

    home = tmp_path / "home"
    path = home / "sessions" / "rollout.jsonl"
    _write(path, [_meta(), _start()])
    payload = _line(_count(100, 100))
    with path.open("a", encoding="utf-8") as handle:
        handle.write(payload[:20])
    collector = _collector(tmp_path, _binding(home))
    first = collector.collect()
    assert _requests(first) == []
    assert collector.caught_up is False
    assert collector.m_store is not None
    position = complete_file_position(path)
    checkpoint = collector.m_store.get_checkpoint("binding-a", opaque_usage_reference(str(path)))
    assert checkpoint is not None and checkpoint.offset == position < path.stat().st_size
    with path.open("a", encoding="utf-8") as handle:
        handle.write(payload[20:])
    restarted = UsageCollector.from_binding(collector.m_store, _binding(home))
    requests = _requests(restarted.collect())
    assert len(requests) == 1
    assert requests[0].provider_turn_id == "native-a"
    assert requests[0].values["input_tokens"] == 100
    assert restarted.collect() == []
    assert restarted.caught_up is True


def test_attachment_replays_context_and_baseline_without_charging_history(tmp_path: Path) -> None:
    """Pre-attachment snapshots restore counters but never enter chargeable staging."""

    home = tmp_path / "home"
    path = home / "sessions" / "rollout.jsonl"
    _write(path, [_meta(), _start(), _count(100, 100), _end()])
    binding = _binding(home, fresh=False)
    source = opaque_usage_reference(str(path))
    binding.collection_boundary = {source: complete_file_position(path)}
    collector = _collector(tmp_path, binding)
    assert collector.collect() == []
    assert collector.m_store is not None
    checkpoint = collector.m_store.get_checkpoint("binding-a", source)
    assert checkpoint is not None
    assert checkpoint.baseline == {"input_tokens": 100}
    assert checkpoint.metadata["attachment_baseline"] == {"input_tokens": 100}
    assert collector.m_store.get_binding("binding-a").baseline == {"input_tokens": 100}  # type: ignore[union-attr]
    _append(path, [_start("native-b"), _count(160, 60), _end("native-b")])
    requests = _requests(collector.collect())
    assert [item.values["input_tokens"] for item in requests] == [60]
    assert requests[0].provider_turn_id == "native-b"
    assert requests[0].source_ref.startswith(source + ":")
    assert requests[0].metadata["source_offset"] >= binding.collection_boundary[source]


def test_attachment_during_turn_marks_new_requests_partial_and_excludes_old_request_replay(
    tmp_path: Path,
) -> None:
    """An existing active turn never claims complete pre-attachment coverage."""

    home = tmp_path / "home"
    path = home / "sessions" / "rollout.jsonl"
    _write(path, [_meta(), _start(), _request()])
    binding = _binding(home, fresh=False)
    binding.collection_boundary = {opaque_usage_reference(str(path)): complete_file_position(path)}
    collector = _collector(tmp_path, binding)
    assert collector.collect() == []
    _append(path, [_request(), _request("response-b"), _end()])
    requests = _requests(collector.collect())
    assert [item.request_id for item in requests] == ["response-b"]
    assert requests[0].coverage == "partial"


def test_post_attachment_copy_does_not_reintroduce_excluded_history(tmp_path: Path) -> None:
    """Historical requests remain excluded when a copied file appears later."""

    home = tmp_path / "home"
    original = home / "sessions" / "original.jsonl"
    history = [
        _meta(),
        _start(timestamp="2026-11-13T00:00:00Z"),
        _request(timestamp="2026-11-13T00:00:01Z"),
        _end(timestamp="2026-11-13T00:00:02Z"),
    ]
    _write(original, history)
    binding = _binding(home, fresh=False)
    binding.started_at_utc = "2026-11-13T01:00:00Z"
    binding.collection_boundary = {
        opaque_usage_reference(str(original)): complete_file_position(original)
    }
    collector = _collector(tmp_path, binding)
    assert collector.collect() == []
    copy = home / "sessions" / "copied.jsonl"
    _write(
        copy,
        history
        + [
            _start("native-b", timestamp="2026-11-13T02:00:00Z"),
            _request("response-b", "native-b", timestamp="2026-11-13T02:00:01Z"),
            _end("native-b", timestamp="2026-11-13T02:00:02Z"),
        ],
    )
    requests = _requests(collector.collect())
    assert [item.request_id for item in requests] == ["response-b"]


def test_rename_resumes_physical_file_without_replaying_prior_observations(tmp_path: Path) -> None:
    """An archived rename keeps its offset, parser state, and counter epoch."""

    home = tmp_path / "home"
    original = home / "sessions" / "day" / "rollout.jsonl"
    _write(original, [_meta(), _start(), _request(), _end()])
    collector = _collector(tmp_path, _binding(home))
    assert len(_requests(collector.collect())) == 1
    archived = home / "archived_sessions" / "day" / "rollout.jsonl"
    archived.parent.mkdir(parents=True)
    original.rename(archived)
    _append(archived, [_start("native-b"), _request("response-b", "native-b"), _end("native-b")])
    requests = _requests(collector.collect())
    assert [item.request_id for item in requests] == ["response-b"]
    assert requests[0].metadata["counter_epoch"] == "initial"
    assert collector.diagnostics == []


def test_same_inode_rewrite_changes_epoch_and_keeps_it_on_later_appends(tmp_path: Path) -> None:
    """Rewrites larger than the old file still invalidate cumulative continuity."""

    home = tmp_path / "home"
    path = home / "sessions" / "rollout.jsonl"
    _write(path, [_meta(), _start(), _request(), _end()])
    collector = _collector(tmp_path, _binding(home))
    collector.collect()
    original_inode = path.stat().st_ino
    rewritten_metadata = {**_meta(), "source_note": "rewritten"}
    _write(
        path,
        [
            rewritten_metadata,
            _start(),
            _request(),
            _end(),
            _start("native-b"),
            _request("response-b", "native-b"),
            _end("native-b"),
        ],
    )
    assert path.stat().st_ino == original_inode
    requests = _requests(collector.collect())
    assert [item.request_id for item in requests] == ["response-b"]
    assert "native_source_replaced_or_truncated" in collector.diagnostics
    epoch = requests[0].metadata["counter_epoch"]
    assert epoch.startswith("discontinuous-")
    _append(path, [_start("native-c"), _request("response-c", "native-c"), _end("native-c")])
    next_requests = _requests(collector.collect())
    assert [item.metadata["counter_epoch"] for item in next_requests] == [epoch]


def test_malformed_records_report_a_gap_and_preserve_progress(tmp_path: Path) -> None:
    """Malformed accounting cannot silently turn into complete zero usage."""

    home = tmp_path / "home"
    path = home / "sessions" / "rollout.jsonl"
    _write(path, [_meta(), _start()])
    with path.open("a", encoding="utf-8") as handle:
        handle.write("not JSON\n")
    _append(path, [_request(), _end()])
    collector = _collector(tmp_path, _binding(home))
    requests = _requests(collector.collect())
    assert requests[0].coverage == "partial"
    assert "native_accounting_record_invalid" in collector.diagnostics
    assert collector.m_store is not None
    health = collector.m_store.get_collection_health()
    assert health.status == "degraded"
    assert str(path) not in health.model_dump_json()
    assert collector.collect() == []


def test_foreign_record_does_not_poison_subsequent_parser_session(tmp_path: Path) -> None:
    """Reject an embedded mismatched session before changing parser state."""

    home = tmp_path / "home"
    path = home / "sessions" / "rollout.jsonl"
    _write(
        path, [_meta(), _start(), _request("foreign", session="thread-b"), _count(100, 100), _end()]
    )
    collector = _collector(tmp_path, _binding(home))
    requests = _requests(collector.collect())
    assert len(requests) == 1
    assert requests[0].provider_session_id == "thread-a"
    assert requests[0].request_id != "foreign"
    assert "native_session_identity_mismatch" in collector.diagnostics


def test_competing_collectors_retry_checkpoint_conflicts_without_duplicate_requests(
    tmp_path: Path,
) -> None:
    """Independent collectors coordinate through the persisted checkpoint version."""

    home = tmp_path / "home"
    path = home / "sessions" / "rollout.jsonl"
    _write(path, [_meta(), _start(), _request(), _end()])
    binding = _binding(home)
    first = _collector(tmp_path, binding)
    assert first.m_store is not None
    second = UsageCollector.from_binding(first.m_store, binding)
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda item: item.collect(), [first, second]))
    assert sum(len(_requests(items)) for items in results) == 1
    assert len(_requests(first.m_store.list_observations())) == 1


def test_oversized_record_does_not_block_later_complete_records(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bounded discard scans eventually reach later accounting/lifecycle records."""

    home = tmp_path / "home"
    path = home / "sessions" / "rollout.jsonl"
    _write(path, [_meta()])
    with path.open("a", encoding="utf-8") as handle:
        handle.write("x" * 700 + "\n" + _line({"type": "turn.failed", "turn_id": "tail"}))
    collector = _collector(tmp_path, _binding(home))
    monkeypatch.setattr(usage_collection, "USAGE_READ_BATCH_BYTES", 64)
    monkeypatch.setattr(usage_collection, "USAGE_MAX_SOURCE_BYTES", 128)

    def selected(
        binding: UsageSourceBinding, *, diagnostics: list[str] | None = None
    ) -> list[Path]:
        """Keep this test focused on record bounds after ownership was established."""

        return [path]

    monkeypatch.setattr(usage_collection, "discover_usage_sources", selected)
    accepted = collector.collect(max_batches=20)
    assert any(item.lifecycle == "failed" and item.provider_turn_id == "tail" for item in accepted)
    assert "native_record_exceeds_read_bound" in collector.diagnostics
    assert collector.m_store is not None
    checkpoint = collector.m_store.get_checkpoint("binding-a", opaque_usage_reference(str(path)))
    assert checkpoint is not None and checkpoint.offset == path.stat().st_size
    assert collector.caught_up is True


def test_generation_is_snapshotted_from_current_collection_context(tmp_path: Path) -> None:
    """A stable binding retains current per-turn generation provenance."""

    home = tmp_path / "home"
    path = home / "sessions" / "rollout.jsonl"
    _write(path, [_meta(), _start(), _request()])
    binding = _binding(home)
    binding.metadata["collection_generation_id"] = "generation-b"
    collector = _collector(tmp_path, binding)
    assert {item.metadata["generation_id"] for item in collector.collect()} == {"generation-b"}


def test_missing_source_reports_limitation_instead_of_silent_empty_success(tmp_path: Path) -> None:
    """Source absence is visible even before finalized accounting exists."""

    collector = _collector(tmp_path, _binding(tmp_path / "missing-home"))
    assert collector.collect() == []
    assert collector.diagnostics == ["native_source_unavailable"]
    with pytest.raises(ValueError):
        collector.collect(max_batches=0)


def test_existing_binding_cannot_be_repurposed_for_another_session(tmp_path: Path) -> None:
    """A stale caller cannot reset durable source ownership or its attach boundary."""

    binding = _binding(tmp_path / "home")
    collector = _collector(tmp_path, binding)
    assert collector.m_store is not None
    for update in (
        {"provider_session_id": "another-session"},
        {"home_path": str(tmp_path / "another-home")},
        {"collection_boundary": {"source-other": 100}},
    ):
        with pytest.raises(ValueError, match="durable ownership"):
            UsageCollector.from_binding(collector.m_store, binding.model_copy(update=update))


def test_new_provider_chat_uses_its_own_checkpoint_state_and_epoch(tmp_path: Path) -> None:
    """Resetting the provider chat cannot reuse another session's counters."""

    home = tmp_path / "home"
    first_path = home / "sessions" / "first.jsonl"
    second_path = home / "sessions" / "second.jsonl"
    _write(first_path, [_meta(), _start(), _count(1000, 1000), _end()])
    first = _collector(tmp_path, _binding(home))
    first.collect()
    assert first.m_store is not None
    old = first.m_store.get_checkpoint("binding-a", opaque_usage_reference(str(first_path)))
    _write(second_path, [_meta("thread-b"), _start("native-b"), _count(20, 20), _end("native-b")])
    next_binding = _binding(home, session="thread-b").model_copy(
        update={
            "binding_id": "binding-b",
            "counter_epoch": "new-provider-chat",
        }
    )
    second = UsageCollector.from_binding(first.m_store, next_binding)
    accepted = _requests(second.collect())
    assert [item.values["input_tokens"] for item in accepted] == [20]
    assert accepted[0].metadata["counter_epoch"] == "new-provider-chat"
    assert first.m_store.get_checkpoint("binding-a", opaque_usage_reference(str(first_path))) == old


def test_each_native_turn_start_snapshots_its_own_cumulative_baseline(tmp_path: Path) -> None:
    """The second native turn subtracts the first turn rather than attachment zero."""

    home = tmp_path / "home"
    path = home / "sessions" / "rollout.jsonl"
    total_a = _count(100, 0)
    total_b = _count(160, 0)
    del total_a["payload"]["info"]["last_token_usage"]
    del total_b["payload"]["info"]["last_token_usage"]
    _write(
        path, [_meta(), _start(), total_a, _end(), _start("native-b"), total_b, _end("native-b")]
    )
    binding = _binding(home)
    binding.baseline = {"input_tokens": 0}
    collector = _collector(tmp_path, binding)
    starts = [item for item in collector.collect() if item.lifecycle == "started"]
    assert [item.metadata["baseline"] for item in starts] == [
        {"input_tokens": 0},
        {"input_tokens": 100},
    ]
    assert starts[1].metadata["baseline_source_ids"]["input_tokens"]


def test_source_reset_discards_prior_epoch_baseline_before_native_turn(tmp_path: Path) -> None:
    """A new counter epoch cannot subtract attachment or provenance from the old file."""

    home = tmp_path / "home"
    path = home / "sessions" / "rollout.jsonl"
    old_total = _count(100, 0)
    reset_total = _count(60, 0)
    next_total = _count(90, 0)
    for total in (old_total, reset_total, next_total):
        del total["payload"]["info"]["last_token_usage"]
    _write(path, [_meta(), _start(), old_total, _end()])
    binding = _binding(home)
    binding.baseline = {"input_tokens": 20}
    collector = _collector(tmp_path, binding)
    collector.collect()
    _write(
        path,
        [
            {**_meta(), "source_note": "rewritten"},
            _start("native-reset"),
            reset_total,
            _end("native-reset"),
            _start("native-next"),
            next_total,
            _end("native-next"),
        ],
    )
    starts = [item for item in collector.collect() if item.lifecycle == "started"]
    assert [item.metadata["baseline"] for item in starts] == [{}, {"input_tokens": 60}]
    assert starts[0].metadata["baseline_source_ids"] == {}
    assert starts[1].metadata["baseline_source_ids"]["input_tokens"]
    assert all(item.metadata["counter_epoch"] != binding.counter_epoch for item in starts)


def test_collection_budget_exhaustion_is_explicit_and_later_catches_up(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A bounded prefix cannot masquerade as a complete final evidence drain."""

    home = tmp_path / "home"
    path = home / "sessions" / "rollout.jsonl"
    _write(
        path, [_meta(), _start(), *[_request(f"response-{index}") for index in range(20)], _end()]
    )
    collector = _collector(tmp_path, _binding(home))
    monkeypatch.setattr(usage_collection, "USAGE_READ_BATCH_BYTES", 256)
    monkeypatch.setattr(usage_collection, "USAGE_MAX_SOURCE_BYTES", 1024)
    collector.collect(max_batches=1)
    assert collector.caught_up is False
    assert "native_collection_backlog" in collector.diagnostics
    collector.collect(max_batches=100)
    assert collector.caught_up is True
    assert "native_collection_backlog" not in collector.diagnostics
    assert collector.m_store is not None
    assert len(_requests(collector.m_store.list_observations())) == 20
