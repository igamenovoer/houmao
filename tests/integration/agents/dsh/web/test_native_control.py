"""Qualify native authenticated admission before publishing Web launch authority."""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
import json
import time
from typing import Any

import httpx
import pytest

from houmao.agents.realm_controller.backends.dsh_web_client import DshWebClient, DshWebError
from houmao.agents.realm_controller.usage_adapters.dsh import select_dsh_journal
from tests.integration.agents.dsh.web.conftest import NativeWebGates, NativeWebHost


def wait_terminal(host: NativeWebHost, operation_id: str) -> dict[str, Any]:
    """Poll metadata only until this exact admitted input reaches its terminal turn."""

    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        receipt = host.client.receipt(host.identity, operation_id)
        if receipt is not None and receipt["status"] == "terminal":
            return receipt
        time.sleep(0.02)
    raise AssertionError("Native operation did not reach a terminal receipt")


def native_prompt(host: NativeWebHost, text: str, *, mode: str = "queue") -> None:
    """Submit a human-equivalent native controller input without managed admission."""

    assert host.client.m_http is not None
    response = host.client.m_http.post(
        "/api/session/prompt",
        json={
            "type": "client-request",
            "rpcId": text,
            "method": "session/prompt",
            "payload": {
                "args": {
                    "request": {
                        "requestId": text,
                        "sessionId": host.identity["native_session_id"],
                        "mode": mode,
                        "content": [{"type": "text", "text": text}],
                    }
                }
            },
        },
    )
    assert response.status_code == 200
    assert response.json()["result"]["ok"] is True


def deadline() -> int:
    """Return a bounded dispatch deadline independent of native turn completion."""

    return int(time.time() * 1000) + 10000


def test_claimed_crash_restores_terminal_receipt_from_exact_native_journal(
    native_web_factory: Callable[..., NativeWebHost],
    native_web_gates: NativeWebGates,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
) -> None:
    """A real claimed crash settles the original receipt without replay or new charges."""

    native_web_gates.hold("step", "Claimed crash before model work")
    host = native_web_factory(extra_plugins=[native_web_gates.plugin])
    host.client.prompt(
        host.identity,
        "Claimed crash before model work",
        operation_id="claimed-crash",
        deadline_epoch_ms=deadline(),
    )
    native_web_gates.wait("step")
    claimed = host.client.receipt(host.identity, "claimed-crash")
    assert claimed is not None and claimed["status"] == "claimed"
    assert claimed["turns"] == [1]
    limit = time.monotonic() + 5
    while True:
        journal = select_dsh_journal(
            host.root / "dsh-home/sessions", host.identity["native_session_id"]
        )
        rows = [json.loads(line) for line in journal.read_text().splitlines()] if journal else []
        events = {row.get("seq"): row for row in rows if "seq" in row}
        claim_sequence = claimed["claims"][0]["native_sequence"]
        if claim_sequence in events:
            assert events[claim_sequence]["type"] == "agent/inbox/spliced"
            break
        assert time.monotonic() < limit, "Native claim did not become durable"
        time.sleep(0.01)
    original_identity = dict(claimed["identity"])
    native_id = host.identity["native_session_id"]
    host.kill()
    native_web_gates.release("step")
    restored = native_web_factory(
        root=host.root, mode="exact", session_id=native_id, generation="replacement-generation"
    )
    assert restored.identity["host_incarnation"] != original_identity["host_incarnation"]
    settled = restored.client.receipt(restored.identity, "claimed-crash")
    assert settled is not None and settled["status"] == "terminal"
    assert settled["identity"] == original_identity
    assert settled["claims"] == claimed["claims"]
    assert settled["result"] == "interrupted"
    state = restored.client.state(restored.identity)
    assert state["last_turn"]["result"] == "interrupted"
    assert state["last_turn"]["end_sequence"] == settled["end_sequence"]
    before = restored.client.conversation(restored.identity)["current_cursor"]
    assert restored.client.receipt(restored.identity, "claimed-crash") == settled
    assert restored.client.state(restored.identity)["cursor"] == before
    assert controlled_messages_server[1] == []


def test_native_authentication_and_cold_state_do_not_activate(
    native_web_factory: Callable[..., NativeWebHost],
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
) -> None:
    """Require an independent owner cookie and refuse a missing live target without creation."""

    host = native_web_factory(start=False)
    description = host.client.describe()
    assert description["protocol_version"] == 1
    assert description["identity"]["native_session_id"] is None
    assert host.client.state()["available"] is False
    with httpx.Client(trust_env=False) as anonymous:
        response = anonymous.post(host.origin + "/houmao/managed/v1/describe", json={})
        assert response.status_code == 401
    with pytest.raises(DshWebError) as refused:
        host.client.prompt(
            description["identity"],
            "must never run",
            operation_id="cold",
            deadline_epoch_ms=int(time.time() * 1000) + 5000,
        )
    assert refused.value.code == "unavailable"
    assert host.client.state()["available"] is False
    assert controlled_messages_server[1] == []


def test_native_admission_receipts_are_exact_and_payload_free(
    native_web_host: NativeWebHost,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
) -> None:
    """Exercise actual native claims, settled turns, duplicate IDs, and API revocation."""

    host = native_web_host
    snapshot = host.client.state(host.identity)
    assert snapshot["admission"]["ready_only"] is True
    assert snapshot["active_turn"] is None
    receipt = host.client.prompt(
        host.identity,
        "Native Web private prompt",
        operation_id="first",
        deadline_epoch_ms=int(time.time() * 1000) + 10000,
    )
    assert receipt["message_id"]
    settled = wait_terminal(host, "first")
    assert settled["turns"] == [1]
    before = len(controlled_messages_server[1])
    duplicate = host.client.prompt(
        host.identity,
        "different text never inserted",
        operation_id="first",
        deadline_epoch_ms=int(time.time() * 1000) + 10000,
    )
    assert duplicate["duplicate"] is True
    assert duplicate["message_id"] == receipt["message_id"]
    assert len(controlled_messages_server[1]) == before
    history = host.client.history(host.identity)
    assert {row["event"] for row in history["entries"]} >= {
        "created",
        "inbox/inserted",
        "inbox/claimed",
        "turn/start",
        "turn/end",
    }
    assert "Native Web private prompt" not in json.dumps(history)
    assert "Native Web private prompt" not in (host.root / "receipt-state.json").read_text()
    assert "different text never inserted" not in (host.root / "receipt-state.json").read_text()
    cookie = dict(host.client.m_http.cookies)
    second = DshWebClient.from_connection(host.origin, launch_token=host.launch_token)
    try:
        assert second.state(host.identity)["identity"] == host.identity
        host.client.close()
        with httpx.Client(base_url=host.origin, trust_env=False, cookies=cookie) as revoked:
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                response = revoked.post("/houmao/managed/v1/describe", json={})
                if response.status_code == 401:
                    break
                time.sleep(0.02)
            assert response.status_code == 401
        assert second.state(host.identity)["available"] is True
    finally:
        second.close()


@pytest.mark.parametrize("reason", ["maintenance", "expired", "stale_identity", "invalid_policy"])
def test_native_guarded_refusals_do_not_insert(
    native_web_factory: Callable[..., NativeWebHost],
    native_web_gates: NativeWebGates,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
    reason: str,
) -> None:
    """Reject native maintenance, expired dispatch, replacement and nonoperator queues."""

    host = native_web_factory(extra_plugins=[native_web_gates.plugin])
    identity = dict(host.identity)
    kwargs: dict[str, Any] = {"operation_id": reason, "deadline_epoch_ms": deadline()}
    if reason == "maintenance":
        native_web_gates.hold("maintenance")
        native_web_gates.wait("maintenance")
        assert host.client.state(identity)["admission"]["ready_only"] is False
    elif reason == "expired":
        kwargs["deadline_epoch_ms"] = 0
    elif reason == "stale_identity":
        identity["agent_incarnation"] = "another-body"
    else:
        kwargs["admission_policy"] = "always"
    try:
        with pytest.raises(DshWebError) as refused:
            host.client.prompt(identity, "refused input", **kwargs)
        assert refused.value.code == ("not_ready" if reason == "maintenance" else reason)
        assert host.client.receipt(host.identity, reason) is None
        assert controlled_messages_server[1] == []
    finally:
        native_web_gates.release("maintenance")


def test_native_human_first_race_rechecks_after_preparation(
    native_web_factory: Callable[..., NativeWebHost],
    native_web_gates: NativeWebGates,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
) -> None:
    """A human taking the native driver during preparation prevents ordinary insertion."""

    host = native_web_factory(extra_plugins=[native_web_gates.plugin])
    native_web_gates.hold("prepare", "ordinary-raced")
    native_web_gates.hold("step", "human-active")
    assert host.client.state(host.identity)["admission"]["ready_only"] is True
    with ThreadPoolExecutor(max_workers=1) as pool:
        attempt = pool.submit(
            host.client.prompt,
            host.identity,
            "ordinary-raced",
            operation_id="raced",
            deadline_epoch_ms=deadline(),
        )
        try:
            native_web_gates.wait("prepare")
            native_prompt(host, "human-active")
            native_web_gates.wait("step")
            native_web_gates.release("prepare")
            with pytest.raises(DshWebError) as refused:
                attempt.result(timeout=10)
            assert refused.value.code == "not_ready"
        finally:
            native_web_gates.release("prepare")
            native_web_gates.release("step")
    assert host.client.receipt(host.identity, "raced") is None
    assert all(
        "ordinary-raced" not in json.dumps(request) for request in controlled_messages_server[1]
    )


def test_native_program_first_allows_human_queue_and_scoped_interrupt(
    native_web_factory: Callable[..., NativeWebHost],
    native_web_gates: NativeWebGates,
) -> None:
    """Keep native human queueing available and refuse late cancellation of another turn."""

    host = native_web_factory(extra_plugins=[native_web_gates.plugin])
    native_web_gates.hold("step", "program-active")
    host.client.prompt(
        host.identity, "program-active", operation_id="active", deadline_epoch_ms=deadline()
    )
    native_web_gates.wait("step")
    current = host.client.state(host.identity)
    assert current["active_turn"] is not None
    native_prompt(host, "human-queued")
    pending = host.client.state(host.identity)
    assert len(pending["pending_inbox"]) == 1
    with pytest.raises(DshWebError) as refused:
        host.client.prompt(
            host.identity, "ordinary-denied", operation_id="denied", deadline_epoch_ms=deadline()
        )
    assert refused.value.code == "not_ready"
    with pytest.raises(DshWebError) as stale:
        host.client.interrupt(
            host.identity, turn_start_seq=current["active_turn"]["start_sequence"] + 100
        )
    assert stale.value.code == "stale_turn"
    result = host.client.interrupt(
        host.identity,
        turn_start_seq=current["active_turn"]["start_sequence"],
        operation_id="active",
    )
    assert result["interrupted"] is True
    assert host.client.state(host.identity)["pending_inbox"]
    native_web_gates.release("step")


@pytest.mark.parametrize("boundary", ["step", "pending", "maintenance"])
def test_native_reset_refuses_before_changing_a_busy_or_pending_binding(
    native_web_factory: Callable[..., NativeWebHost],
    native_web_gates: NativeWebGates,
    boundary: str,
) -> None:
    """Reset requires a true idle claim and empty inbox before any lifecycle effect."""

    host = native_web_factory(extra_plugins=[native_web_gates.plugin])
    native_web_gates.hold(boundary, "keep-existing")
    if boundary == "step":
        host.client.prompt(
            host.identity, "keep-existing", operation_id="existing", deadline_epoch_ms=deadline()
        )
    native_web_gates.wait(boundary)
    try:
        with pytest.raises(DshWebError) as refused:
            host.client.lifecycle_reset(host.identity)
        assert refused.value.code == ("pending_input" if boundary == "pending" else "not_ready")
        assert host.client.state(host.identity)["identity"] == host.identity
        assert (
            len(
                [
                    row
                    for row in host.client.history(host.identity)["entries"]
                    if row["event"] == "created"
                ]
            )
            == 1
        )
    finally:
        native_web_gates.release(boundary)


def test_native_reset_changes_only_the_conversation_and_agent_incarnation(
    native_web_host: NativeWebHost,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
) -> None:
    """A successful atomic reset keeps the Host and excludes old conversation context."""

    host = native_web_host
    host.client.prompt(
        host.identity,
        "old conversation marker",
        operation_id="before-reset",
        deadline_epoch_ms=deadline(),
    )
    wait_terminal(host, "before-reset")
    original = dict(host.identity)
    host.identity = host.client.lifecycle_reset(original)
    assert host.identity["host_incarnation"] == original["host_incarnation"]
    assert host.identity["native_session_id"] != original["native_session_id"]
    assert host.identity["agent_incarnation"] != original["agent_incarnation"]
    assert host.client.state(host.identity)["last_turn"] is None
    with pytest.raises(DshWebError) as stale:
        host.client.state(original)
    assert stale.value.code == "stale_identity"
    host.client.prompt(
        host.identity,
        "fresh conversation",
        operation_id="after-reset",
        deadline_epoch_ms=deadline(),
    )
    wait_terminal(host, "after-reset")
    assert "old conversation marker" not in json.dumps(controlled_messages_server[1][-1])


def test_native_pre_activation_recovery_removes_only_abandoned_ordinary_input(
    native_web_factory: Callable[..., NativeWebHost],
    native_web_gates: NativeWebGates,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
) -> None:
    """Recover a real unclaimed native inbox without replaying failed ordinary delivery."""

    host = native_web_factory(extra_plugins=[native_web_gates.plugin])
    native_web_gates.hold("settlement", "ordinary-unclaimed")
    observer = DshWebClient.from_connection(host.origin, launch_token=host.launch_token)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(
            host.client.prompt,
            host.identity,
            "ordinary-unclaimed",
            operation_id="abandoned",
            deadline_epoch_ms=deadline(),
        )
        try:
            native_web_gates.wait("settlement")
            receipt = observer.receipt(host.identity, "abandoned")
            assert receipt is not None and receipt["status"] == "admitted"
            native_prompt(host, "preserved-human")
            operator = observer.prompt(
                host.identity,
                "preserved-operator",
                operation_id="operator",
                deadline_epoch_ms=deadline(),
                admission_policy="always",
                operator=True,
            )
            assert operator["operator"] is True
            assert len(observer.state(host.identity)["pending_inbox"]) == 3
            journal_deadline = time.monotonic() + 5
            while time.monotonic() < journal_deadline:
                journals = list((host.root / "dsh-home/sessions").glob("*.jsonl"))
                if any("preserved-operator" in path.read_text() for path in journals):
                    break
                time.sleep(0.02)
            host.kill()
            with pytest.raises(DshWebError):
                pending.result(timeout=10)
        finally:
            observer.close()
            native_web_gates.release("settlement")
    old_identity = host.identity
    with pytest.raises(DshWebError) as unsafe:
        native_web_factory(
            root=host.root, mode="exact", session_id=old_identity["native_session_id"]
        )
    assert unsafe.value.code == "reconciliation_required"
    recovered = native_web_factory(
        root=host.root,
        mode="exact",
        session_id=old_identity["native_session_id"],
        abandoned_operation_ids=["abandoned"],
    )
    assert recovered.identity["native_session_id"] == old_identity["native_session_id"]
    assert recovered.identity["host_incarnation"] != old_identity["host_incarnation"]
    snapshot = recovered.client.state(recovered.identity)
    assert len(snapshot["pending_inbox"]) == 2
    assert {item["operation_id"] for item in snapshot["pending_inbox"]} == {None, "operator"}
    assert recovered.client.receipt(recovered.identity, "abandoned")["status"] == "abandoned"
    assert controlled_messages_server[1] == []


def test_native_protocol_owner_and_session_guards_precede_mutation(
    native_web_factory: Callable[..., NativeWebHost],
    native_web_gates: NativeWebGates,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
) -> None:
    """Exercise actual native nonowner Peer, protocol and wrong-session refusals."""

    host = native_web_factory(extra_plugins=[native_web_gates.plugin])
    assert host.client.m_http is not None
    for expected_code, patch, headers in [
        ("forbidden", {}, {"x-qualification-principal": "guest"}),
        ("protocol_mismatch", {"protocol_version": 99}, {}),
        (
            "stale_identity",
            {"identity": {**host.identity, "native_session_id": "other-session"}},
            {},
        ),
    ]:
        payload = {
            "protocol_version": 1,
            "identity": host.identity,
            "text": "rejected",
            "operation_id": expected_code,
            "deadline_epoch_ms": deadline(),
            **patch,
        }
        response = host.client.m_http.post(
            "/houmao/managed/v1/prompt",
            headers=headers,
            json={
                "type": "client-request",
                "rpcId": expected_code,
                "method": "managed/v1/prompt",
                "payload": payload,
            },
        )
        assert response.status_code == 200
        assert response.json()["result"]["error"]["code"] == expected_code
        assert host.client.receipt(host.identity, expected_code) is None
    assert controlled_messages_server[1] == []


@pytest.mark.parametrize("failure", ["deadline", "caller", "peer"])
def test_native_prepared_input_loses_dispatch_authority(
    native_web_factory: Callable[..., NativeWebHost],
    native_web_gates: NativeWebGates,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
    failure: str,
) -> None:
    """Recheck lifetime after native async preparation and never retain failed text."""

    host = native_web_factory(extra_plugins=[native_web_gates.plugin])
    native_web_gates.hold("prepare", "delayed-input")
    observer = DshWebClient.from_connection(host.origin, launch_token=host.launch_token)
    assert host.client.m_http is not None
    expires = int(time.time() * 1000) + (250 if failure == "deadline" else 10000)
    if failure == "caller":
        host.client.m_http.timeout = httpx.Timeout(0.3)
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(
                host.client.prompt,
                host.identity,
                "delayed-input",
                operation_id="lost-authority",
                deadline_epoch_ms=expires,
            )
            native_web_gates.wait("prepare")
            if failure in {"deadline", "caller"}:
                time.sleep(0.4)
            else:
                assert host.client.m_socket is not None
                host.client.m_socket.close()
                time.sleep(0.05)
            native_web_gates.release("prepare")
            with pytest.raises(DshWebError) as refused:
                pending.result(timeout=10)
            assert (
                refused.value.code
                == {"deadline": "expired", "caller": "outcome_uncertain", "peer": "forbidden"}[
                    failure
                ]
            )
        assert observer.receipt(host.identity, "lost-authority") is None
        assert observer.state(host.identity)["pending_inbox"] == []
        assert controlled_messages_server[1] == []
    finally:
        native_web_gates.release("prepare")
        observer.close()


@pytest.mark.parametrize("policy", ["if_no_pending", "always"])
def test_native_operator_queue_and_abandonment_are_attempt_scoped(
    native_web_factory: Callable[..., NativeWebHost],
    native_web_gates: NativeWebGates,
    policy: str,
) -> None:
    """Explicit queueing can be withdrawn without cancelling a different active input."""

    host = native_web_factory(extra_plugins=[native_web_gates.plugin])
    native_web_gates.hold("step", "first-managed")
    host.client.prompt(
        host.identity, "first-managed", operation_id="first-managed", deadline_epoch_ms=deadline()
    )
    native_web_gates.wait("step")
    first = host.client.state(host.identity)["active_turn"]
    queued = host.client.prompt(
        host.identity,
        "operator-queue",
        operation_id="queued",
        deadline_epoch_ms=deadline(),
        admission_policy=policy,
        operator=True,
    )
    assert queued["status"] == "admitted"
    removed = host.client.interrupt(host.identity, turn_start_seq=None, operation_id="queued")
    assert removed == {"interrupted": False, "removed": True}
    assert host.client.state(host.identity)["active_turn"] == first
    native_web_gates.release("step")
    wait_terminal(host, "first-managed")
    native_web_gates.hold("step", "later-human")
    native_prompt(host, "later-human")
    native_web_gates.wait("step")
    human = host.client.state(host.identity)["active_turn"]
    assert human["turn"] != first["turn"]
    with pytest.raises(DshWebError) as late:
        host.client.interrupt(
            host.identity, turn_start_seq=first["start_sequence"], operation_id="first-managed"
        )
    assert late.value.code == "stale_turn"
    assert host.client.state(host.identity)["active_turn"] == human
    assert (
        host.client.interrupt(host.identity, turn_start_seq=human["start_sequence"])["interrupted"]
        is True
    )
    native_web_gates.release("step")


def test_native_concurrent_duplicate_operations_insert_exactly_once(
    native_web_factory: Callable[..., NativeWebHost],
    native_web_gates: NativeWebGates,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
) -> None:
    """Two independent Peers completing preparation share one native admission receipt."""

    host = native_web_factory(extra_plugins=[native_web_gates.plugin])
    other = DshWebClient.from_connection(host.origin, launch_token=host.launch_token)
    native_web_gates.hold("prepare", "simultaneous duplicate")
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            attempts = [
                pool.submit(
                    client.prompt,
                    host.identity,
                    "simultaneous duplicate",
                    operation_id="concurrent",
                    deadline_epoch_ms=deadline(),
                )
                for client in [host.client, other]
            ]
            native_web_gates.wait("prepare")
            both_deadline = time.monotonic() + 5
            count_path = native_web_gates.directory / "prepare.count"
            while len(count_path.read_text().splitlines()) < 2:
                assert time.monotonic() < both_deadline
                time.sleep(0.01)
            native_web_gates.release("prepare")
            results = [attempt.result(timeout=10) for attempt in attempts]
        assert results[0]["message_id"] == results[1]["message_id"]
        assert sum(result.get("duplicate", False) for result in results) == 1
        wait_terminal(host, "concurrent")
        assert len(controlled_messages_server[1]) == 1
    finally:
        native_web_gates.release("prepare")
        other.close()


def test_native_explicit_model_and_committed_conversation_survive_exact_restore(
    native_web_factory: Callable[..., NativeWebHost],
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
) -> None:
    """Use native selected routes and bounded semantic reads without replaying request metadata."""

    models = [
        {"id": name, "context_window": 131072, "max_output_tokens": 128, "reasoning": False}
        for name in ["controlled", "second"]
    ]
    host = native_web_factory(models=models)
    host.client.prompt(
        host.identity,
        "initial model route",
        operation_id="initial-model",
        deadline_epoch_ms=deadline(),
    )
    wait_terminal(host, "initial-model")
    assert controlled_messages_server[1][-1]["model"] == "controlled"
    with pytest.raises(DshWebError) as missing:
        host.client.set_model(host.identity, provider="deepseek-official", model="not-declared")
    assert missing.value.code == "model_unavailable"
    selected = host.client.set_model(
        host.identity, provider="deepseek-official", model="second", reasoning_effort="off"
    )
    assert selected["model"]["model"] == "second"
    before = host.client.state(host.identity)["cursor"]
    host.client.prompt(
        host.identity,
        "user text excluded from semantic history",
        operation_id="model",
        deadline_epoch_ms=deadline(),
    )
    wait_terminal(host, "model")
    assert controlled_messages_server[1][-1]["model"] == "second"
    entries = []
    cursor = before
    while True:
        page = host.client.conversation(host.identity, after_native_sequence=cursor, limit=3)
        assert page["cursor"] >= cursor
        entries.extend(page["entries"])
        cursor = page["cursor"]
        if not page["has_more"]:
            break
    assert [entry for entry in entries if entry["type"] == "assistant/message"][0]["content"] == [
        {"type": "text", "text": "Controlled native result"}
    ]
    assert "user text excluded from semantic history" not in json.dumps(entries)
    assert "request/header" not in json.dumps(entries)
    assert "synthetic-controlled-only" not in json.dumps(entries)
    old_identity = dict(host.identity)
    host.close()
    restored = native_web_factory(
        root=host.root, mode="exact", session_id=old_identity["native_session_id"], models=models
    )
    snapshot = restored.client.state(restored.identity)
    assert snapshot["model"]["model"] == "second"
    assert snapshot["last_turn"]["turn"] == 2
    assert (
        restored.client.conversation(restored.identity, after_native_sequence=cursor)["entries"]
        == []
    )


def test_unknown_native_pending_state_refuses_without_insertion(
    native_web_factory: Callable[..., NativeWebHost],
    native_web_gates: NativeWebGates,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
) -> None:
    """An unavailable native pending-input fact cannot be interpreted as an empty inbox."""

    host = native_web_factory(extra_plugins=[native_web_gates.plugin])
    native_web_gates.hold("unknown")
    native_web_gates.wait("unknown")
    with pytest.raises(DshWebError) as unknown:
        host.client.prompt(
            host.identity,
            "unknown must refuse",
            operation_id="unknown",
            deadline_epoch_ms=deadline(),
        )
    assert unknown.value.code == "unknown_state"
    assert host.client.receipt(host.identity, "unknown") is None
    assert controlled_messages_server[1] == []


def test_native_same_host_exact_restore_replaces_agent_authority_without_replay(
    native_web_host: NativeWebHost,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
) -> None:
    """A fresh Agent for the same conversation cannot inherit an earlier dispatch lease."""

    host = native_web_host
    original = dict(host.identity)
    host.client.prompt(
        original, "completed native work", operation_id="complete", deadline_epoch_ms=deadline()
    )
    wait_terminal(host, "complete")
    host.client.stop(original)
    host.identity = host.client.lifecycle_start(
        mode="exact", session_id=original["native_session_id"]
    )
    assert host.identity["host_incarnation"] == original["host_incarnation"]
    assert host.identity["native_session_id"] == original["native_session_id"]
    assert host.identity["agent_incarnation"] != original["agent_incarnation"]
    with pytest.raises(DshWebError) as replaced:
        host.client.prompt(
            original,
            "failed attempt never replayed",
            operation_id="stale",
            deadline_epoch_ms=deadline(),
        )
    assert replaced.value.code == "stale_identity"
    assert host.client.receipt(host.identity, "stale") is None
    assert len(controlled_messages_server[1]) == 1
