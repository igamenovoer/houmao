"""Exact Web input accounting, durable attachment boundaries, and recovery."""

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
from typing import Any

import pytest

from houmao.agents.realm_controller.usage_support import UsageService
from tests.unit.agents.realm_controller.test_dsh_usage_adapter import (
    _header,
    _message,
    _row,
    _write,
)


def _identity(**updates: Any) -> dict[str, Any]:
    """Build a verified synthetic native execution identity."""

    return {
        "protocol_version": 1,
        "agent_id": "agent",
        "runtime_session_id": "logical-runtime",
        "generation": "generation-1",
        "host_incarnation": "host-1",
        "agent_incarnation": "agent-1",
        "native_session_id": "native-1",
        **updates,
    }


def _service(tmp_path: Path, *, identity: dict[str, Any] | None = None) -> UsageService:
    """Bind before any manifest exists, like the first managed Web launch."""

    evidence = tmp_path / "evidence.jsonl"
    evidence.touch(exist_ok=True)
    service = UsageService.from_manifest(tmp_path / "session" / "manifest.json")
    service.m_home_path = tmp_path / "home"
    service.bind_dsh_web(
        identity=identity or _identity(),
        evidence_path=evidence,
        new_session=not evidence.stat().st_size,
    )
    return service


def _turn(
    tmp_path: Path,
    *,
    turn: int = 1,
    operation: str | None = None,
    mixed: bool = False,
    proof: bool = True,
    identity: dict[str, Any] | None = None,
) -> None:
    """Append native usage and independently persisted metadata-only input claims."""

    path = tmp_path / "home" / "sessions" / "workspace" / "native-1" / "session.v4.jsonl"
    rows = (
        [json.loads(line) for line in path.read_text().splitlines()]
        if path.exists()
        else [_header()]
    )
    offset = len(rows) - 1
    rows.extend(
        [
            _row(offset, "turn/start", {"turn": turn}),
            _row(
                offset + 1,
                "user/message",
                {
                    "id": f"input-{turn}",
                    "source": {"kind": "user"},
                    "role": "user",
                    "content": [{"type": "text", "text": "PRIVATE PROMPT key=secret"}],
                },
            ),
        ]
    )
    if mixed:
        rows.append(
            _row(
                offset + 2,
                "user/message",
                {
                    "id": f"human-{turn}",
                    "source": {"kind": "user"},
                    "role": "user",
                    "content": "PRIVATE STEERING",
                },
            )
        )
    step = len(rows) - 1
    rows.extend(
        [
            _row(step, "step/start", {"turn": turn, "step": 1}),
            _message(step + 1, turn=turn),
            _row(step + 2, "step/end", {"turn": turn, "step": 1}),
            _row(step + 3, "turn/end", {"turn": turn, "reason": {"kind": "completed"}}),
        ]
    )
    _write(path, rows)
    if not proof:
        return
    fields = {
        "identity": identity or _identity(),
        "observed_at_utc": "2026-11-16T00:00:00Z",
        "turn": turn,
    }
    events = [
        {**fields, "event": "turn/start", "native_sequence": offset},
        {
            **fields,
            "event": "inbox/claimed",
            "native_sequence": offset + 1,
            "message_id": f"input-{turn}",
            "operation_id": operation,
        },
    ]
    if mixed:
        events.append(
            {
                **fields,
                "event": "inbox/claimed",
                "native_sequence": offset + 2,
                "message_id": f"human-{turn}",
                "operation_id": None,
            }
        )
    events.append({**fields, "event": "turn/end", "native_sequence": step + 3})
    start_sequence = len((tmp_path / "evidence.jsonl").read_text().splitlines())
    with (tmp_path / "evidence.jsonl").open("a") as handle:
        for sequence, event in enumerate(events, start=start_sequence):
            handle.write(
                json.dumps(
                    {**event, "sequence": sequence, "forbidden_prompt": "PRIVATE EVIDENCE secret"}
                )
                + "\n"
            )


def test_first_binding_uses_verified_logical_identity_before_manifest(tmp_path: Path) -> None:
    service = _service(tmp_path)
    assert service.store.runtime_session_id == "logical-runtime"
    assert service.store.list_bindings()[0].agent_id == "agent"
    assert service.m_generation_id == "generation-1"


def test_managed_mixed_and_distinct_human_turns_charge_once(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.begin_dsh_web_turn(operation_id="managed", turn_index=1)
    _turn(tmp_path, operation="managed", mixed=True)
    _turn(tmp_path, turn=2)
    service.settle_dsh_web_turn(operation_id="managed", receipt={"turns": [1]})
    records = service.get_usage().records
    assert len(records) == 2
    assert [record.token_usage.total_tokens.value for record in records] == [26, 26]
    managed = next(record for record in records if record.turn_id == "managed")
    assert managed.provider_turn_id == "1"
    assert "dsh_web_mixed_input" in managed.diagnostics
    assert (
        next(record for record in records if record.provider_turn_id == "2").turn_origin
        == "native_observed"
    )
    assert "tiny-model" in json.dumps(managed.model_dump())
    for _ in range(2):
        service.reconcile_dsh_web()
    assert service.get_usage().records == records
    assert "PRIVATE" not in json.dumps(
        [item.model_dump() for item in service.store.list_observations()]
    )


def test_unrelated_pending_managed_operation_does_not_absorb_human_work(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.begin_dsh_web_turn(operation_id="waiting", turn_index=1)
    _turn(tmp_path)
    service.reconcile_dsh_web()
    assert len(service.get_usage().records) == 1
    assert service.get_usage().records[0].turn_origin == "native_observed"
    assert not service.store.get_pending_turn("waiting").finalized


def test_native_terminal_waits_for_exact_companion_claims(tmp_path: Path) -> None:
    service = _service(tmp_path)
    _turn(tmp_path, proof=False)
    service.reconcile_dsh_web()
    assert service.get_usage().records == []


def test_attachment_excludes_history_and_relaunch_preserves_original_rows(tmp_path: Path) -> None:
    (tmp_path / "evidence.jsonl").touch()
    _turn(tmp_path)
    service = _service(tmp_path)
    _turn(tmp_path, turn=2)
    service.reconcile_dsh_web()
    first = service.get_usage().records[0]
    assert first.provider_turn_id == "2"
    identity = _identity(
        generation="generation-2", host_incarnation="host-2", agent_incarnation="agent-2"
    )
    restored = _service(tmp_path, identity=identity)
    _turn(tmp_path, turn=3, identity=identity)
    restored.reconcile_dsh_web()
    records = restored.get_usage().records
    assert len(records) == 2
    assert records[0] == first
    assert {record.generation_id for record in records} == {"generation-1", "generation-2"}


def test_concurrent_reconciliation_preserves_generation_and_cutoff(tmp_path: Path) -> None:
    service = _service(tmp_path)
    _turn(tmp_path)
    with ThreadPoolExecutor(max_workers=4) as workers:
        list(workers.map(lambda _: _service(tmp_path).reconcile_dsh_web(), range(8)))
    service.reconcile_dsh_web()
    first = service.get_usage().records[0]
    cutoff = service.store.get_pending_turn(first.turn_id).finalization
    with ThreadPoolExecutor(max_workers=4) as workers:
        list(workers.map(lambda _: _service(tmp_path).reconcile_dsh_web(), range(8)))
    assert service.get_usage().records == [first]
    assert service.store.get_pending_turn(first.turn_id).finalization == cutoff


def test_multiple_managed_inputs_share_one_charge_with_explicit_unknown_allocation(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    service.begin_dsh_web_turn(operation_id="first", turn_index=1)
    service.begin_dsh_web_turn(operation_id="second", turn_index=2)
    _turn(tmp_path, operation="first", mixed=True)
    evidence = tmp_path / "evidence.jsonl"
    evidence.write_text(
        evidence.read_text().replace('"operation_id": null', '"operation_id": "second"')
    )
    service.reconcile_dsh_web()
    records = service.get_usage().records
    assert len(records) == 2
    assert (
        next(item for item in records if item.turn_id == "first").token_usage.total_tokens.value
        == 26
    )
    second = next(item for item in records if item.turn_id == "second")
    assert second.token_usage.total_tokens.value is None
    assert "dsh_web_usage_shared_with_another_operation" in second.diagnostics
    assert (
        service.store.get_pending_turn("second").snapshot.metadata["dsh_web_shared_accounting_turn"]
        == "first"
    )
    service.reconcile_dsh_web()
    assert service.get_usage().records == records


@pytest.mark.parametrize("failure", ["sequence", "replacement", "partial", "native-boundary"])
def test_observation_gaps_never_guess_native_ownership(tmp_path: Path, failure: str) -> None:
    service = _service(tmp_path)
    _turn(tmp_path)
    evidence = tmp_path / "evidence.jsonl"
    if failure == "sequence":
        rows = [json.loads(line) for line in evidence.read_text().splitlines()]
        rows[1]["sequence"] += 2
        _write(evidence, rows)
    elif failure == "replacement":
        service.reconcile_dsh_web()
        original = service.get_usage().records
        evidence.unlink()
        evidence.write_text("{}\n")
    elif failure == "partial":
        evidence.write_bytes(evidence.read_bytes().rstrip(b"\n"))
    else:
        rows = [json.loads(line) for line in evidence.read_text().splitlines()]
        rows[0]["native_sequence"] += 1
        _write(evidence, rows)
    service.reconcile_dsh_web()
    if failure == "replacement":
        assert service.get_usage().records == original
    else:
        assert service.get_usage().records == []
    assert service.get_usage().collection.status == "degraded" or failure == "partial"


def test_unknown_incarnation_is_rejected_without_staging_or_finalizing(tmp_path: Path) -> None:
    service = _service(tmp_path)
    _turn(tmp_path, identity=_identity(host_incarnation="alien"))
    service.reconcile_dsh_web()
    assert service.get_usage().records == []
    assert "dsh_web_claim_evidence_gap" in service.get_usage().collection.diagnostics


def test_new_host_preactivation_abandonment_closes_original_pending_attempt(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.begin_dsh_web_turn(operation_id="abandoned", turn_index=1)
    identity = _identity(
        generation="generation-2", host_incarnation="host-2", agent_incarnation="agent-2"
    )
    replacement_evidence = tmp_path / "replacement-evidence.jsonl"
    _write(
        replacement_evidence,
        [
            {
                "sequence": 0,
                "event": "reconciled",
                "identity": identity,
                "operation_id": "abandoned",
                "message_id": "abandoned-message",
                "observed_at_utc": "2026-11-16T01:00:00Z",
            }
        ],
    )
    service.bind_dsh_web(identity=identity, evidence_path=replacement_evidence)
    service.reconcile_dsh_web()
    record = service.get_usage().records[0]
    assert record.turn_id == "abandoned"
    assert record.generation_id == "generation-1"
    assert record.outcome == "failed"
    assert record.token_usage.total_tokens.value is None
    assert "dsh_web_abandoned_before_claim" in record.diagnostics


def test_web_native_journal_copy_preserves_immutable_final_record(tmp_path: Path) -> None:
    service = _service(tmp_path)
    _turn(tmp_path)
    service.reconcile_dsh_web()
    records = service.get_usage().records
    journal = tmp_path / "home/sessions/workspace/native-1/session.v4.jsonl"
    replacement = journal.with_suffix(".copy")
    replacement.write_bytes(journal.read_bytes())
    replacement.replace(journal)
    service.reconcile_dsh_web()
    assert service.get_usage().records == records
    assert len(records) == 1


def test_uncertain_transport_loss_stays_pending_and_definitive_refusal_has_no_charge(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    service.begin_dsh_web_turn(operation_id="uncertain", turn_index=1)
    service.settle_dsh_web_turn(operation_id="uncertain")
    assert not service.store.get_pending_turn("uncertain").finalized
    service.begin_dsh_web_turn(operation_id="refused", turn_index=2)
    service.settle_dsh_web_turn(operation_id="refused", outcome="failed")
    record = service.get_usage().records[0]
    assert record.turn_id == "refused" and record.outcome == "failed"
    assert record.token_usage.total_tokens.value is None
