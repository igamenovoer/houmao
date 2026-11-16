"""Qualify Web accounting against actual native v4 journals and exact input claims."""

from collections.abc import Callable
import json
import time
from typing import Any

from houmao.agents.realm_controller.usage_support import UsageService
from tests.integration.agents.dsh.web.conftest import NativeWebGates, NativeWebHost
from tests.integration.agents.dsh.web.test_native_control import (
    deadline,
    native_prompt,
    wait_terminal,
)


def _usage(host: NativeWebHost, *, new: bool = True) -> UsageService:
    """Bind verified identities before creating a public manifest or accepting input."""

    service = UsageService.from_manifest(host.root / "runtime" / "manifest.json")
    service.m_home_path = host.root / "dsh-home"
    service.bind_dsh_web(
        identity=host.identity, evidence_path=host.root / "evidence.jsonl", new_session=new
    )
    return service


def _idle(host: NativeWebHost, *, last_turn: int) -> None:
    """Wait for a specific native terminal boundary, independently of usage collection."""

    limit = time.monotonic() + 15
    while time.monotonic() < limit:
        state = host.client.state(host.identity)
        if (
            state["active_turn"] is None
            and state["last_turn"]
            and state["last_turn"]["turn"] >= last_turn
        ):
            return
        time.sleep(0.02)
    raise AssertionError("Native conversation did not reach the expected boundary")


def test_native_web_managed_human_followup_and_relaunch_charge_exactly_once(
    native_web_factory: Callable[..., NativeWebHost],
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
) -> None:
    """Human follow-up before caller settlement stays separate across gateway/host recovery."""

    host = native_web_factory()
    usage = _usage(host)
    usage.begin_dsh_web_turn(operation_id="managed-1", turn_index=1)
    host.client.prompt(
        host.identity, "Managed accounting", operation_id="managed-1", deadline_epoch_ms=deadline()
    )
    receipt = wait_terminal(host, "managed-1")
    native_prompt(host, "Human before managed waiter settles")
    _idle(host, last_turn=2)
    usage.settle_dsh_web_turn(operation_id="managed-1", receipt=receipt)
    records = usage.get_usage().records
    assert len(records) == 2
    assert [record.token_usage.total_tokens.value for record in records] == [16, 16]
    assert {record.turn_origin for record in records} == {"managed", "native_observed"}
    assert (
        next(record for record in records if record.turn_id == "managed-1").provider_turn_id == "1"
    )
    assert receipt["mixed_input"] is False
    assert usage.store.runtime_session_id == "web-runtime"
    first_cutoffs = {
        record.turn_id: usage.store.get_pending_turn(record.turn_id).finalization
        for record in records
    }
    # Reconstruct a recorder as a gateway would, then explicitly relaunch the
    # native host. Neither operation is permitted to replay or rebaseline work.
    _usage(host, new=False).reconcile_dsh_web()
    old_identity = dict(host.identity)
    host.close()
    restored = native_web_factory(
        root=host.root,
        mode="exact",
        session_id=old_identity["native_session_id"],
        generation="web-generation-2",
    )
    recovered = _usage(restored, new=False)
    native_prompt(restored, "Human after explicit host restoration")
    _idle(restored, last_turn=3)
    recovered.reconcile_dsh_web()
    final = recovered.get_usage().records
    assert len(final) == 3
    assert final[:2] == records
    assert [record.generation_id for record in final] == [
        "web-generation",
        "web-generation",
        "web-generation-2",
    ]
    assert [record.token_usage.total_tokens.value for record in final] == [16, 16, 16]
    assert len(controlled_messages_server[1]) == 3
    for record in records:
        assert (
            recovered.store.get_pending_turn(record.turn_id).finalization
            == first_cutoffs[record.turn_id]
        )
    assert "Managed accounting" not in json.dumps(
        [item.model_dump() for item in recovered.store.list_observations()]
    )


def test_native_web_human_steering_shares_one_managed_charge(
    native_web_factory: Callable[..., NativeWebHost],
    native_web_gates: NativeWebGates,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
) -> None:
    """Prove mixed attribution from actual native input IDs within the same turn."""

    native_web_gates.hold("step", "Managed mixed accounting")
    host = native_web_factory(extra_plugins=[native_web_gates.plugin])
    usage = _usage(host)
    usage.begin_dsh_web_turn(operation_id="mixed", turn_index=1)
    host.client.prompt(
        host.identity,
        "Managed mixed accounting",
        operation_id="mixed",
        deadline_epoch_ms=deadline(),
    )
    native_web_gates.wait("step")
    native_prompt(host, "Human native steering", mode="steer")
    native_web_gates.release("step")
    receipt = wait_terminal(host, "mixed")
    _idle(host, last_turn=1)
    usage.settle_dsh_web_turn(operation_id="mixed", receipt=receipt)
    records = usage.get_usage().records
    assert receipt["mixed_input"] is True
    assert len(receipt["input_claims"]) == 2
    assert len(records) == 1
    assert records[0].turn_id == "mixed"
    assert "dsh_web_mixed_input" in records[0].diagnostics
    assert records[0].token_usage.total_tokens.value == 16 * len(controlled_messages_server[1])


def test_native_web_actual_changed_model_is_retained_per_request(
    native_web_factory: Callable[..., NativeWebHost],
) -> None:
    """Retain actual native routes after a browser-equivalent model selection."""

    models = [
        {"id": name, "context_window": 131072, "max_output_tokens": 128, "reasoning": False}
        for name in ["controlled", "browser-selected"]
    ]
    host = native_web_factory(models=models)
    usage = _usage(host)
    native_prompt(host, "Human original model")
    _idle(host, last_turn=1)
    usage.reconcile_dsh_web()
    first = usage.get_usage().records[0]
    host.client.set_model(host.identity, provider="deepseek-official", model="browser-selected")
    native_prompt(host, "Human changed model")
    _idle(host, last_turn=2)
    usage.reconcile_dsh_web()
    records = usage.get_usage().records
    assert len(records) == 2
    assert records[0] == first
    routes = [
        {
            source.accounting.get("model")
            for source in record.sources
            if source.accounting.get("model")
        }
        for record in records
    ]
    assert routes == [{"controlled"}, {"browser-selected"}]
    assert all(
        source.accounting.get("provider") == "deepseek-official"
        for record in records
        for source in record.sources
        if source.accounting.get("model")
    )


def test_native_web_attachment_excludes_preexisting_human_history(
    native_web_host: NativeWebHost,
) -> None:
    """Establish the first accounting boundary without charging old conversation work."""

    host = native_web_host
    native_prompt(host, "Human history before Houmao attachment")
    _idle(host, last_turn=1)
    usage = _usage(host, new=False)
    native_prompt(host, "Human work after attachment")
    _idle(host, last_turn=2)
    usage.reconcile_dsh_web()
    records = usage.get_usage().records
    assert len(records) == 1
    assert records[0].provider_turn_id == "2"
    assert records[0].token_usage.total_tokens.value == 16


def test_native_web_lost_receipt_recovers_usage_without_resubmission(
    native_web_host: NativeWebHost,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
) -> None:
    """A recorder that never receives the receipt recovers the exact persisted claim."""

    host = native_web_host
    usage = _usage(host)
    usage.begin_dsh_web_turn(operation_id="lost-receipt", turn_index=1)
    host.client.prompt(
        host.identity,
        "Never submit this twice",
        operation_id="lost-receipt",
        deadline_epoch_ms=deadline(),
    )
    _idle(host, last_turn=1)
    recovered = _usage(host, new=False)
    recovered.settle_dsh_web_turn(operation_id="lost-receipt")
    record = recovered.get_usage().records[0]
    assert record.turn_id == "lost-receipt"
    assert record.turn_origin == "managed" and record.provider_turn_id == "1"
    assert record.token_usage.total_tokens.value == 16
    assert len(controlled_messages_server[1]) == 1
    recovered.reconcile_dsh_web()
    assert recovered.get_usage().records == [record]


def test_native_web_queued_managed_inputs_keep_distinct_native_charges(
    native_web_factory: Callable[..., NativeWebHost],
    native_web_gates: NativeWebGates,
) -> None:
    """Native next-turn queuing consumes one explicit operation in each real turn."""

    native_web_gates.hold("step", "Hold first native turn")
    host = native_web_factory(extra_plugins=[native_web_gates.plugin])
    usage = _usage(host)
    native_prompt(host, "Hold first native turn")
    native_web_gates.wait("step")
    for index, operation in enumerate(["queued-first", "queued-second"], start=1):
        usage.begin_dsh_web_turn(operation_id=operation, turn_index=index)
        host.client.prompt(
            host.identity,
            operation,
            operation_id=operation,
            deadline_epoch_ms=deadline(),
            admission_policy="always",
            operator=True,
        )
    native_web_gates.release("step")
    first = wait_terminal(host, "queued-first")
    second = wait_terminal(host, "queued-second")
    usage.reconcile_dsh_web()
    assert first["turns"] == [2]
    assert second["turns"] == [3]
    records = usage.get_usage().records
    assert len(records) == 3
    assert sum(record.token_usage.total_tokens.value or 0 for record in records) == 48
    secondary = next(record for record in records if record.turn_id == "queued-second")
    assert secondary.token_usage.total_tokens.value == 16
    assert secondary.provider_turn_id == "3"
