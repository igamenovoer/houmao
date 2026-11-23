"""Lifecycle tests for bound accounting, recovery, and finalized-only reads."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from concurrent.futures import ThreadPoolExecutor

import pytest

from houmao.agents.realm_controller.usage_support import UsageService, persist_terminal_evidence
from houmao.agents.realm_controller.models import LaunchPlan
from houmao.agents.realm_controller.usage_store import UsageStoreError


def _manifest(
    tmp_path: Path,
    *,
    backend: str = "local_interactive",
    session: str | None = "thread-a",
    provider: str = "codex",
) -> Path:
    """Write the manifest-owned identity used by a deterministic fake client."""

    path = tmp_path / "runtime" / "manifest.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "agent_id": "agent-a",
                "tool": provider,
                "backend": backend,
                "registry_generation_id": "generation-1",
                "runtime": {"session_id": "runtime-a"},
                "backend_state": {"session_id": session},
                "launch_plan": {"home_selector": {"home_path": str(tmp_path / "home")}},
            }
        )
    )
    return path


def _append(path: Path, payload: dict[str, Any]) -> None:
    """Append a complete fake-provider JSONL record."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        handle.write(json.dumps(payload) + "\n")


def _native(tmp_path: Path) -> Path:
    """Create one explicitly identified native source."""

    path = tmp_path / "home" / "sessions" / "rollout.jsonl"
    _append(path, {"type": "session_meta", "payload": {"id": "thread-a"}})
    return path


def _turn(path: Path, name: str, *, inputs: int = 1000) -> None:
    """Emit an identified request and final outcome for a native turn."""

    _append(
        path,
        {
            "timestamp": "2026-11-13T01:00:00Z",
            "type": "event_msg",
            "payload": {"type": "task_started", "turn_id": name},
        },
    )
    _append(
        path,
        {
            "timestamp": "2026-11-13T01:00:01Z",
            "type": "token_usage_record",
            "payload": {
                "thread_id": "thread-a",
                "turn_id": name,
                "response_id": "response-" + name,
                "usage": {
                    "input_tokens": inputs,
                    "output_tokens": 100,
                    "total_tokens": inputs + 100,
                },
            },
        },
    )
    _append(
        path,
        {
            "timestamp": "2026-11-13T01:00:02Z",
            "type": "event_msg",
            "payload": {"type": "task_complete", "turn_id": name},
        },
    )


@pytest.mark.parametrize(
    ("wrong_incarnation", "version"),
    [(False, None), (False, "2.6.0"), (False, "2.7.2"), (True, "2.6.0")],
)
@pytest.mark.parametrize("backend", ["kimi_acp", "kimi_web"])
def test_kimi_service_accounts_only_for_the_certified_interval(
    tmp_path: Path, wrong_incarnation: bool, version: str | None, backend: str
) -> None:
    """Exclude replay and occupancy and require exact owner evidence across recovery."""

    manifest = _manifest(tmp_path, backend=backend, session="session-b", provider="kimi")
    payload = json.loads(manifest.read_text())
    if backend == "kimi_web":
        payload["backend_state"] = {
            "web_identity": {"native_session_id": "session-b", "host_incarnation": "incarnation-b"}
        }
    else:
        payload["backend_state"]["service_incarnation"] = "incarnation-b"
    if version is not None:
        payload["launch_plan"]["metadata"] = {backend: {"detected_version": version}}
    manifest.write_text(json.dumps(payload))
    journal = (
        tmp_path / "home" / "sessions" / "wd_test" / "session-b" / "agents" / "main" / "wire.jsonl"
    )

    def record(kind: str, **values: Any) -> None:
        """Write one private native main-agent row."""

        _append(journal, {"type": kind, "agentId": "main", **values})

    native_usage = {"inputOther": 12, "output": 4}
    record("turn.prompt", turnId=0, promptId="old")
    record("usage.record", usageScope="turn", usage={"inputOther": 170, "output": 27})
    record("turn.ended", turnId=0, reason="completed")
    start = journal.stat().st_size

    service = UsageService.from_manifest(manifest)
    turn_dir = manifest.parent / "manifest.turn-artifacts" / "request-a"
    service.begin_headless_turn(
        turn_id="request-a", turn_dir=turn_dir, turn_index=2, new_session=False
    )
    (turn_dir / "process.json").write_text(
        json.dumps({"child_pid": 20, "child_birth_token": "proc:12"})
    )
    record("turn.prompt", turnId=1, promptId="new")
    record("usage.record", usageScope="turn", usage=native_usage)
    record("usage.record", usageScope="session", usage={"inputOther": 900})
    record("turn.ended", turnId=1, reason="completed")
    record("prompt.completed", promptId="new", reason="completed")
    complete = journal.stat()
    record("usage.record", usageScope="turn", usage={"inputOther": 999})
    (turn_dir / "kimi-native-turn.json").write_text(
        json.dumps(
            {
                "version": 1,
                "agent_id": "agent-a",
                "runtime_session_id": "runtime-a",
                "request_id": "request-a",
                "generation_id": "generation-1",
                "service_incarnation": "stale" if wrong_incarnation else "incarnation-b",
                "native_session_id": "session-b",
                "native_turn_id": 1,
                "native_prompt_id": "new",
                "terminal": "completed",
                "settled_at_utc": "2026-11-19T01:00:05+00:00",
                "process_id": 20,
                "process_birth_token": "proc:12",
                "journal_path": str(journal),
                "journal_device": complete.st_dev,
                "journal_inode": complete.st_ino,
                "journal_baseline_offset": start,
                "journal_settled_offset": complete.st_size,
            }
        )
    )
    # Simulate losing the recorder after native closure and before creating usage-final.
    if version == "2.7.2":
        payload["launch_plan"]["metadata"][backend]["detected_version"] = "2.6.0"
        manifest.write_text(json.dumps(payload))
    recovered = UsageService.from_manifest(manifest)
    recovered.reconcile()
    page = recovered.get_usage()
    if wrong_incarnation:
        assert page.records == []
        assert page.collection.status == "degraded"
    else:
        [settlement] = page.records
        assert settlement.turn_id == "request-a" and settlement.provider_turn_id == "1"
        [source] = [source for source in settlement.sources if source.accounting]
        assert source.provider_version == version
        if version == "2.7.2":
            assert source.measurement_scope == "unknown"
            assert settlement.token_usage.input_tokens.value is None
            assert settlement.token_usage.output_tokens.value is None
        else:
            assert source.measurement_scope == "request"
            assert settlement.token_usage.input_tokens.value == 12
            assert settlement.token_usage.output_tokens.value == 4
        recovered.reconcile()
        assert recovered.get_usage(after=page.next_cursor).records == []


@pytest.mark.parametrize("version", [None, "0.169.0", "0.171.0"])
def test_codex_service_recovers_only_exact_native_responses(
    tmp_path: Path, version: str | None
) -> None:
    """Charge the bound native turn once after its terminal reaches the rollout."""

    manifest = _manifest(tmp_path, backend="codex_app_server")
    workspace = str(tmp_path / "workspace")
    payload = json.loads(manifest.read_text())
    payload["working_directory"] = workspace
    payload["backend_state"]["service_incarnation"] = "codex-incarnation"
    if version is not None:
        payload["launch_plan"]["metadata"] = {"codex_app_server": {"detected_version": version}}
    manifest.write_text(json.dumps(payload))
    service = UsageService.from_manifest(manifest)
    turn_dir = manifest.parent / "manifest.turn-artifacts" / "request-c"
    service.begin_headless_turn(
        turn_id="request-c", turn_dir=turn_dir, turn_index=2, new_session=False
    )
    path = tmp_path / "home" / "sessions" / "2026" / "rollout-thread-a.jsonl"
    _append(
        path,
        {
            "type": "session_meta",
            "payload": {"id": "thread-a", "cwd": workspace, "cli_version": "0.169.0"},
        },
    )
    _turn(path, "historical")
    _append(path, {"type": "event_msg", "payload": {"type": "task_started", "turn_id": "target"}})
    _append(path, {"type": "turn_context", "payload": {"turn_id": "target", "model": "test-model"}})
    _append(
        path,
        {
            "type": "event_msg",
            "payload": {
                "type": "token_count",
                "turn_id": "target",
                "info": {"total_token_usage": {"input_tokens": 995}},
            },
        },
    )
    for thread_id in ("foreign", "thread-a"):
        _append(
            path,
            {
                "type": "token_usage_record",
                "payload": {
                    "thread_id": thread_id,
                    "turn_id": "target",
                    "root_turn_id": "target",
                    "response_id": "response-" + thread_id,
                    "usage": {"input_tokens": 14, "output_tokens": 3},
                },
            },
        )
    (turn_dir / "process.json").write_text(
        json.dumps({"child_pid": 2, "child_birth_token": "proc:3"})
    )
    (turn_dir / "codex-native-turn.json").write_text(
        json.dumps(
            {
                "version": 1,
                "agent_id": "agent-a",
                "runtime_session_id": "runtime-a",
                "generation_id": "generation-1",
                "service_incarnation": "codex-incarnation",
                "request_id": "request-c",
                "native_session_id": "thread-a",
                "native_turn_id": "target",
                "rollout_path": str(path),
                "terminal": "completed",
                "process_id": 2,
                "process_birth_token": "proc:3",
                "settled_at_utc": "2026-11-19T06:22:00+00:00",
            }
        )
    )
    usage = UsageService.from_manifest(manifest)
    usage.reconcile()
    assert usage.get_usage().records == []
    _append(path, {"type": "event_msg", "payload": {"type": "task_complete", "turn_id": "target"}})
    _turn(path, "successor")
    usage.collect()
    page = usage.get_usage()
    [record] = page.records
    assert record.turn_id == "request-c" and record.provider_turn_id == "target"
    [source] = [source for source in record.sources if source.accounting]
    assert source.provider_version == (version or "0.169.0")
    if version == "0.171.0":
        assert source.measurement_scope == "unknown"
        assert record.token_usage.input_tokens.value is None
        assert record.token_usage.output_tokens.value is None
    else:
        assert source.measurement_scope == "request"
        assert record.token_usage.input_tokens.value == 14
        assert record.token_usage.output_tokens.value == 3
    usage.reconcile()
    assert usage.get_usage(after=page.next_cursor).records == []


def test_native_turn_is_finalized_once_and_empty_cursor_resumes(tmp_path: Path) -> None:
    """A TUI source yields stable native records while polling retains its position."""

    service = UsageService.from_manifest(_manifest(tmp_path))
    native = _native(tmp_path)
    service.collect()
    empty = service.get_usage()
    assert empty.records == [] and empty.next_cursor is not None
    _turn(native, "turn-a")
    service.collect()
    page = service.get_usage(after=empty.next_cursor)
    assert len(page.records) == 1
    assert page.records[0].turn_origin == "native_observed"
    assert page.records[0].token_usage.input_tokens.value == 1000
    service.collect()
    assert service.get_usage(after=page.next_cursor).records == []
    _turn(native, "turn-b", inputs=200)
    service.collect()
    assert (
        service.get_usage(after=page.next_cursor).records[0].token_usage.input_tokens.value == 200
    )


def test_attachment_and_restart_do_not_charge_old_native_turns(tmp_path: Path) -> None:
    """Old history restores parser context but does not enter the charge stream."""

    manifest = _manifest(tmp_path)
    native = _native(tmp_path)
    _turn(native, "old")
    service = UsageService.from_manifest(manifest)
    service.collect()
    assert service.get_usage().records == []
    _turn(native, "new")
    UsageService.from_manifest(manifest).collect()
    page = service.get_usage()
    assert len(page.records) == 1 and page.records[0].provider_turn_id == "new"


def test_headless_shared_recording_and_recovery_preserve_original_facts(tmp_path: Path) -> None:
    """Output and native evidence combine without duplicate requests or replayed timing."""

    manifest = _manifest(tmp_path, backend="codex_headless", session=None)
    service = UsageService.from_manifest(manifest)
    turn_dir = manifest.parent / "manifest.turn-artifacts" / "managed-a"
    service.begin_headless_turn(
        turn_id="managed-a", turn_dir=turn_dir, turn_index=1, new_session=True
    )
    native = _native(tmp_path)
    _turn(native, "provider-a")
    _append(turn_dir / "stdout.jsonl", {"type": "thread.started", "thread_id": "thread-a"})
    _append(
        turn_dir / "stdout.jsonl",
        {"type": "turn.completed", "usage": {"input_tokens": 1000, "output_tokens": 100}},
    )
    persist_terminal_evidence(
        turn_dir, returncode=0, completed_at_utc="2026-11-13T01:00:03Z", wall_time_ms=1250
    )
    record = service.finalize_headless_turn(turn_dir, provider_session_id="thread-a")
    assert record is not None and record.provider_turn_id == "provider-a"
    assert record.token_usage.input_tokens.value == 1000
    assert record.wall_time_ms.value == 1250
    service.finalize_headless_turn(turn_dir, provider_session_id="thread-a")
    restarted = UsageService.from_manifest(manifest)
    restarted.reconcile()
    page = restarted.get_usage()
    assert len(page.records) == 1
    assert page.records[0] == record


def test_unverified_managed_native_association_does_not_create_second_charge(
    tmp_path: Path,
) -> None:
    """A delayed native acknowledgement remains explicit rather than guessed."""

    service = UsageService.from_manifest(_manifest(tmp_path))
    native = _native(tmp_path)
    service.collect()
    managed = service.register_managed_turn(turn_id="managed-a")
    _turn(native, "provider-a")
    service.collect()
    assert service.get_usage().records == []
    assert "managed_native_association_pending" in service.get_usage().collection.diagnostics
    service.note_provider_turn(
        managed, provider_turn_id="provider-a", provider_session_id="thread-a"
    )
    service.collect()
    page = service.get_usage()
    assert len(page.records) == 1 and page.records[0].turn_id == managed


def test_indexed_reads_do_not_collect_or_scan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A public read is independent of source collection and artifact recovery."""

    service = UsageService.from_manifest(_manifest(tmp_path, backend="codex_headless"))

    def forbidden(*args: Any, **kwargs: Any) -> None:
        """Reject accidental read-path source access."""
        raise AssertionError("source scan on query path")

    monkeypatch.setattr(service, "collect", forbidden)
    monkeypatch.setattr(service, "reconcile", forbidden)
    assert service.get_usage().next_cursor is not None


@pytest.mark.parametrize("canonical", ["", "{incomplete\n", '{"type":"system"}\n'])
def test_incomplete_canonical_keeps_valid_stdout_accounting(tmp_path: Path, canonical: str) -> None:
    """A crash during canonical persistence preserves independently flushed stdout."""

    service = UsageService.from_manifest(
        _manifest(tmp_path, backend="claude_headless", session=None, provider="claude")
    )
    turn_dir = tmp_path / "turn-a"
    service.begin_headless_turn(turn_id="turn-a", turn_dir=turn_dir, turn_index=1, new_session=True)
    (turn_dir / "canonical-events.jsonl").write_text(canonical)
    _append(
        turn_dir / "stdout.jsonl",
        {
            "type": "result",
            "session_id": "claude-a",
            "usage": {"input_tokens": 600, "output_tokens": 30},
            "total_cost_usd": 0.03,
            "duration_api_ms": 25,
        },
    )
    persist_terminal_evidence(
        turn_dir, returncode=0, completed_at_utc="2026-11-13T01:00:03Z", wall_time_ms=100
    )
    record = service.finalize_headless_turn(turn_dir)
    assert record is not None
    assert record.token_usage.input_tokens.value == 600
    assert record.token_usage.input_tokens.availability == "available"
    assert record.cost.amount.value == 0.03
    assert record.provider_session_id == "claude-a"


def test_stdout_and_canonical_copies_do_not_double_charge(tmp_path: Path) -> None:
    """Independent persisted copies provide provenance while requests count once."""

    service = UsageService.from_manifest(
        _manifest(tmp_path, backend="claude_headless", session=None, provider="claude")
    )
    turn_dir = tmp_path / "turn-a"
    service.begin_headless_turn(turn_id="turn-a", turn_dir=turn_dir, turn_index=1, new_session=True)
    raw = {
        "type": "assistant",
        "session_id": "claude-a",
        "message": {
            "id": "msg_a",
            "usage": {"input_tokens": 600, "output_tokens": 30},
            "stop_reason": "end_turn",
        },
    }
    _append(turn_dir / "stdout.jsonl", raw)
    _append(turn_dir / "canonical-events.jsonl", {"kind": "assistant", "raw_payload": raw})
    persist_terminal_evidence(
        turn_dir, returncode=0, completed_at_utc="2026-11-13T01:00:03Z", wall_time_ms=100
    )
    record = service.finalize_headless_turn(turn_dir)
    assert record is not None and record.token_usage.input_tokens.value == 600
    assert (
        len(
            [
                source
                for source in record.sources
                if source.accounting.get("usage", {}).get("input_tokens") == 600
            ]
        )
        == 2
    )


def test_native_turn_start_retains_generation_across_relaunch(tmp_path: Path) -> None:
    """A generation change affects the next native start, preserving active identity."""

    manifest = _manifest(tmp_path)
    service = UsageService.from_manifest(manifest)
    native = _native(tmp_path)
    service.collect()
    _append(
        native,
        {
            "timestamp": "2026-11-13T01:00:00Z",
            "type": "event_msg",
            "payload": {"type": "task_started", "turn_id": "active"},
        },
    )
    service.collect()
    payload = json.loads(manifest.read_text())
    payload["registry_generation_id"] = "generation-2"
    manifest.write_text(json.dumps(payload))
    _append(
        native,
        {
            "type": "token_usage_record",
            "payload": {
                "thread_id": "thread-a",
                "turn_id": "active",
                "response_id": "response-active",
                "usage": {"input_tokens": 50, "output_tokens": 10},
            },
        },
    )
    _append(
        native, {"type": "event_msg", "payload": {"type": "task_complete", "turn_id": "active"}}
    )
    service.collect()
    _turn(native, "next")
    service.collect()
    records = service.get_usage().records
    assert [item.generation_id for item in records] == ["generation-1", "generation-2"]


def test_late_native_accounting_is_diagnostic_without_rewriting(tmp_path: Path) -> None:
    """New charges after final cutoff cannot change a published native record."""

    service = UsageService.from_manifest(_manifest(tmp_path))
    native = _native(tmp_path)
    service.collect()
    _turn(native, "turn-a")
    service.collect()
    original = service.get_usage().records[0]
    _append(
        native,
        {
            "type": "token_usage_record",
            "payload": {
                "thread_id": "thread-a",
                "turn_id": "turn-a",
                "response_id": "late-response",
                "usage": {"input_tokens": 50, "output_tokens": 10},
            },
        },
    )
    service.collect()
    assert service.get_usage().records == [original]
    assert "late_accounting_evidence_conflict" in service.get_usage().collection.diagnostics


def test_record_cache_recovers_database_outage_without_new_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed ledger commit replays the immutable record cache after relaunch."""

    manifest = _manifest(tmp_path, backend="codex_headless", session=None)
    service = UsageService.from_manifest(manifest)
    turn_dir = manifest.parent / "manifest.turn-artifacts" / "managed-a"
    service.begin_headless_turn(
        turn_id="managed-a", turn_dir=turn_dir, turn_index=1, new_session=True
    )
    _append(turn_dir / "stdout.jsonl", {"type": "thread.started", "thread_id": "thread-a"})
    _append(
        turn_dir / "stdout.jsonl",
        {"type": "turn.completed", "usage": {"input_tokens": 1000, "output_tokens": 100}},
    )
    persist_terminal_evidence(
        turn_dir,
        returncode=1,
        completed_at_utc="2026-11-13T01:00:03Z",
        wall_time_ms=1234,
        interrupted=True,
    )

    def unavailable(*args: Any, **kwargs: Any) -> None:
        """Fail the ledger commit after durable record serialization."""
        raise UsageStoreError("simulated recorder outage")

    monkeypatch.setattr(service.store, "finalize", unavailable)
    with pytest.raises(UsageStoreError, match="simulated recorder outage"):
        service.finalize_headless_turn(turn_dir)
    cached = json.loads((turn_dir / "usage-record.json").read_text())
    assert service.get_usage().records == []
    payload = json.loads(manifest.read_text())
    payload["registry_generation_id"] = "generation-2"
    payload["backend_state"]["session_id"] = "thread-new"
    manifest.write_text(json.dumps(payload))
    restarted = UsageService.from_manifest(manifest)
    restarted.reconcile()
    record = restarted.get_usage().records[0]
    assert record.model_dump(mode="json") == cached
    assert record.generation_id == "generation-1"
    assert record.provider_session_id == "thread-a"
    assert record.wall_time_ms.value == 1234 and record.outcome == "interrupted"


def test_missing_initial_manifest_uses_eventual_runtime_identity(tmp_path: Path) -> None:
    """The initial direct backend call uses the stable session-root runtime ID."""

    manifest = tmp_path / "runtime-a" / "manifest.json"
    plan = LaunchPlan.for_joined_session(
        backend="codex_headless",
        tool="codex",
        executable="codex",
        args=[],
        working_directory=tmp_path,
        home_env_var="CODEX_HOME",
        home_path=tmp_path / "home",
        env={"HOUMAO_AGENT_ID": "agent-a"},
        env_var_names=["HOUMAO_AGENT_ID"],
        role_name="test",
        role_prompt="",
    )
    service = UsageService.from_launch(manifest, plan, None)
    service.begin_headless_turn(
        turn_id="managed-a", turn_dir=tmp_path / "turn-a", turn_index=1, new_session=True
    )
    manifest.write_text(
        json.dumps(
            {
                "tool": "codex",
                "backend": "codex_headless",
                "agent_id": "agent-a",
                "runtime": {"session_id": "runtime-a"},
                "launch_plan": {"home_selector": {"home_path": str(tmp_path / "home")}},
            }
        )
    )
    service.collect()
    assert service.get_usage().runtime_session_id == "runtime-a"
    payload = json.loads(manifest.read_text())
    payload["runtime"]["session_id"] = "different-runtime"
    manifest.write_text(json.dumps(payload))
    with pytest.raises(UsageStoreError, match="changed the runtime"):
        service.collect()


def test_background_before_first_turn_does_not_create_competing_binding(tmp_path: Path) -> None:
    """The execution owns the fresh binding and its verified zero baseline."""

    manifest = _manifest(tmp_path, backend="codex_headless", session=None)
    background = UsageService.from_manifest(manifest)
    background.collect()
    assert background.store.list_bindings() == []
    execution = UsageService.from_manifest(manifest)
    snapshot = execution.begin_headless_turn(
        turn_id="managed-a", turn_dir=tmp_path / "turn-a", turn_index=1, new_session=True
    )
    background.collect()
    assert len(background.store.list_bindings()) == 1
    assert snapshot.baseline["input_tokens"] == 0


def test_terminal_facts_are_create_once_across_controllers(tmp_path: Path) -> None:
    """Competing controller recovery cannot overwrite the original terminal facts."""

    service = UsageService.from_manifest(
        _manifest(tmp_path, backend="codex_headless", session=None)
    )
    turn_dir = tmp_path / "turn-a"
    service.begin_headless_turn(turn_id="turn-a", turn_dir=turn_dir, turn_index=1, new_session=True)
    persist_terminal_evidence(
        turn_dir, returncode=0, completed_at_utc="2026-11-13T01:00:03Z", wall_time_ms=1234
    )
    original = (turn_dir / "usage-final.json").read_bytes()
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(
                persist_terminal_evidence,
                turn_dir,
                returncode=1,
                completed_at_utc="2026-11-13T02:00:03Z",
                wall_time_ms=9999,
                interrupted=True,
            )
            for _ in range(8)
        ]
        for future in futures:
            future.result()
    assert (turn_dir / "usage-final.json").read_bytes() == original


def test_late_headless_request_reports_conflict_without_native_second_charge(
    tmp_path: Path,
) -> None:
    """Headless audit compares late evidence against its complete managed cutoff."""

    service = UsageService.from_manifest(
        _manifest(tmp_path, backend="codex_headless", session=None)
    )
    turn_dir = tmp_path / "managed-a"
    service.begin_headless_turn(
        turn_id="managed-a", turn_dir=turn_dir, turn_index=1, new_session=True
    )
    native = _native(tmp_path)
    _turn(native, "provider-a")
    _append(turn_dir / "stdout.jsonl", {"type": "thread.started", "thread_id": "thread-a"})
    _append(
        turn_dir / "stdout.jsonl",
        {"type": "turn.completed", "usage": {"input_tokens": 1000, "output_tokens": 100}},
    )
    persist_terminal_evidence(
        turn_dir, returncode=0, completed_at_utc="2026-11-13T01:00:03Z", wall_time_ms=100
    )
    original = service.finalize_headless_turn(turn_dir)
    service.collect()
    assert service.get_usage().collection.status == "healthy"
    _append(
        native,
        {
            "type": "token_usage_record",
            "payload": {
                "thread_id": "thread-a",
                "turn_id": "provider-a",
                "response_id": "late-response",
                "usage": {"input_tokens": 50, "output_tokens": 10},
            },
        },
    )
    service.collect()
    assert service.get_usage().records == [original]
    assert "late_accounting_evidence_conflict" in service.get_usage().collection.diagnostics
