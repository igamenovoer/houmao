"""Qualify deferred Mail through actual Actor-authenticated CCCC HTTP operations."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import importlib
import json
from pathlib import Path
from threading import Barrier
from typing import Any
import uuid

import httpx
import pytest

from tests.integration.cccc.test_receiver_provider import _result, _rpc, actors as actors


def _send(client: httpx.Client, sender: dict[str, Any], text: str = "deferred") -> dict[str, Any]:
    """Store Mail explicitly, deriving all sender authority from its normal grant."""

    return _result(
        _rpc(
            client,
            sender,
            "mail.send",
            {"operation_id": uuid.uuid4().hex, "to": ["receiver"], "text": text},
        )
    )


def test_actual_direct_cli_keeps_chat_pull_and_mail_read_separate(
    actors: tuple[Any, ...],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Use one Actor profile for ordered chat and explicit Mail with separate receipts."""

    source = Path(__file__).resolve().parents[3] / "packages/houmao-cccc/src"
    monkeypatch.syspath_prepend(str(source))
    monkeypatch.delenv("HOUMAO_MANIFEST_PATH", raising=False)
    cli = importlib.import_module("houmao_cccc.cli")
    client, group, (sender, receiver) = actors
    owner = str(uuid.uuid4())
    profile = tmp_path / "receiver.json"
    profile.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "agent_id": owner,
                "endpoint": str(client.base_url).rstrip("/"),
                "group_id": group,
                "actor_id": "receiver",
                "actor_generation": receiver["actor_generation"],
                "token": receiver["token"],
            }
        )
    )
    profile.chmod(0o600)
    selected = ["--direct-profile", str(profile), "--agent-id", owner]

    def run(*arguments: str) -> dict[str, Any]:
        """Drive one CLI command through the selected provider without using a gateway."""

        assert cli.run([*selected, *arguments]) == 0
        captured = capsys.readouterr()
        assert not captured.err and receiver["token"] not in captured.out
        return dict(json.loads(captured.out))

    event_id = _send(client, sender, "actual direct CLI Mail")["event"]["id"]
    sent = [
        _result(
            _rpc(
                client,
                sender,
                "chat.send",
                {
                    "operation_id": uuid.uuid4().hex,
                    "to": ["receiver"],
                    "text": f"chat-{index}",
                    "mode": "request_reply",
                },
            )
        )["event"]
        for index in range(2)
    ]
    pulled = run("chat", "pull")
    assert [message["text"] for message in pulled["messages"]] == ["chat-0", "chat-1"]
    assert [message["timestamp"] for message in pulled["messages"]] == [
        event["ts"] for event in sent
    ]
    assert run("chat", "ack", "--receipt", pulled["receipt"])["acknowledged"] is True
    chat_reply = run(
        "chat",
        "reply",
        "--event-ref",
        pulled["messages"][1]["event_ref"],
        "--operation-id",
        uuid.uuid4().hex,
        "--text",
        "chat reply",
    )
    assert chat_reply["event"]["data"]["reply_to"] == sent[1]["id"]

    initial = run("mail", "cursor")["cursor"]["event_id"]
    assert initial == ""
    assert run("mail", "peek")["messages"][0]["id"] == event_id
    assert run("mail", "cursor")["cursor"]["event_id"] == initial
    operation = uuid.uuid4().hex
    read_arguments = ("mail", "read", "--expected-cursor", initial, "--operation-id", operation)
    first = run(*read_arguments)
    assert first["outcome"] == "consumed" and first["receipt"]["event_ids"] == [event_id]
    repeated = run(*read_arguments)
    assert repeated["outcome"] == "already_completed" and repeated["messages"] == []
    assert run("mail", "reads", "--operation-id", operation)["receipt"] == first["receipt"]
    reply = run(
        "mail",
        "reply",
        "--event-id",
        event_id,
        "--operation-id",
        uuid.uuid4().hex,
        "--text",
        "direct reply",
    )
    assert reply["event"]["data"]["reply_to"] == event_id


def test_mail_stays_deferred_and_reply_does_not_consume(actors: tuple[Any, ...]) -> None:
    """Repeated inspection and an ancestral deferred reply leave the read cursor intact."""

    client, _group, (sender, receiver) = actors
    lease = _result(_rpc(client, receiver, "lease.acquire"))
    lease_args = {key: lease[key] for key in ("lease_id", "lease_generation")}
    sent = _send(client, sender)
    event = sent["event"]["id"]
    assert sent["stored"] and sent["consumed"] is False
    assert sent["event"]["data"]["message_mode"] == "mail"
    assert _result(_rpc(client, receiver, "lease.next", lease_args))["offers"] == []
    before = _result(_rpc(client, receiver, "mail.cursor"))
    for _ in range(2):
        assert _result(_rpc(client, receiver, "mail.peek"))["messages"][0]["id"] == event
        _result(_rpc(client, receiver, "chat.history", {"event_id": event}))
    reply = _result(
        _rpc(
            client,
            receiver,
            "mail.reply",
            {"operation_id": uuid.uuid4().hex, "event_id": event, "text": "deferred reply"},
        )
    )
    assert reply["event"]["data"]["message_mode"] == "mail"
    assert reply["event"]["data"]["reply_to"] == event
    assert _result(_rpc(client, receiver, "mail.cursor")) == before
    read = _result(
        _rpc(
            client,
            receiver,
            "mail.read",
            {
                "operation_id": uuid.uuid4().hex,
                "expected_cursor": before["cursor"]["event_id"],
                "limit": 1,
            },
        )
    )
    assert read["outcome"] == "consumed"
    assert read["receipt"]["event_ids"] == [event]
    assert read["cursor"]["event_id"] == event


def test_read_budget_includes_complete_response_and_reference_reserve(
    actors: tuple[Any, ...],
) -> None:
    """An oversized head fails before commit; accepted prefixes honor caller wrapper reserves."""

    client, _group, (sender, receiver) = actors
    events = [_send(client, sender, "x" * 8000)["event"]["id"] for _ in range(3)]
    operation_id = uuid.uuid4().hex
    rejected = {"operation_id": operation_id, "expected_cursor": "", "limit": 3, "max_bytes": 4096}
    assert _rpc(client, receiver, "mail.read", rejected).status_code == 422
    assert _result(_rpc(client, receiver, "mail.cursor"))["cursor"]["event_id"] == ""
    assert (
        _result(_rpc(client, receiver, "mail.read-receipts", {"operation_id": operation_id}))[
            "found"
        ]
        is False
    )
    arguments = {
        **rejected,
        "max_bytes": 14500,
        "response_overhead_bytes": 2000,
        "per_event_overhead_bytes": 2000,
    }
    response = _rpc(client, receiver, "mail.read", arguments)
    read = _result(response)
    assert [event["id"] for event in read["messages"]] == events[:1]
    assert read["has_more"] is True
    encoded = len(json.dumps(response.json(), separators=(",", ":"), ensure_ascii=False).encode())
    assert encoded + 2000 + len(read["messages"]) * 2000 <= arguments["max_bytes"]
    assert _result(_rpc(client, receiver, "mail.peek"))["messages"][0]["id"] == events[1]
    duplicate = _result(_rpc(client, receiver, "mail.read", arguments))
    assert duplicate["outcome"] == "already_completed" and duplicate["messages"] == []
    assert duplicate["receipt"] == read["receipt"]
    assert _rpc(client, receiver, "mail.read", {**arguments, "limit": 2}).status_code == 409
    for invalid in (0, 201, True, "2"):
        assert _rpc(client, receiver, "mail.peek", {"limit": invalid}).status_code == 422


def test_empty_read_and_interleaved_direct_traffic(actors: tuple[Any, ...]) -> None:
    """An empty operation remains completed after arrival; reads exclude all direct chat."""

    client, _group, (sender, receiver) = actors
    arguments = {"operation_id": uuid.uuid4().hex, "expected_cursor": ""}
    assert _result(_rpc(client, receiver, "mail.read", arguments))["outcome"] == "empty"
    direct = _result(
        _rpc(
            client,
            sender,
            "chat.send",
            {
                "operation_id": uuid.uuid4().hex,
                "to": ["receiver"],
                "text": "direct",
                "mode": "send",
            },
        )
    )
    event = _send(client, sender)["event"]["id"]
    duplicate = _result(_rpc(client, receiver, "mail.read", arguments))
    assert duplicate["outcome"] == "already_completed"
    assert duplicate["receipt"]["outcome"] == "empty"
    assert _result(_rpc(client, receiver, "mail.cursor"))["cursor"]["event_id"] == ""
    read = _result(
        _rpc(
            client, receiver, "mail.read", {"operation_id": uuid.uuid4().hex, "expected_cursor": ""}
        )
    )
    assert read["receipt"]["event_ids"] == [event]
    assert direct["event"]["id"] not in read["receipt"]["event_ids"]
    assert (
        _result(
            _rpc(client, sender, "mail.read-receipts", {"operation_id": arguments["operation_id"]})
        )["found"]
        is False
    )


def test_concurrent_explicit_readers_commit_only_one_batch(actors: tuple[Any, ...]) -> None:
    """Two distinct callers from one cursor cannot silently consume successive batches."""

    client, _group, (sender, receiver) = actors
    events = [_send(client, sender)["event"]["id"] for _ in range(2)]
    barrier = Barrier(2)

    def consume() -> httpx.Response:
        """Race one owner-authorized consuming operation with its peer."""

        barrier.wait()
        return _rpc(
            client,
            receiver,
            "mail.read",
            {"operation_id": uuid.uuid4().hex, "expected_cursor": "", "limit": 1},
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(consume) for _ in range(2)]
        responses = [future.result(timeout=15) for future in futures]
    assert sorted(response.status_code for response in responses) == [200, 409]
    winner = _result(next(response for response in responses if response.status_code == 200))
    assert winner["receipt"]["event_ids"] == events[:1]
    assert _result(_rpc(client, receiver, "mail.peek"))["messages"][0]["id"] == events[1]


def test_native_and_actor_readers_serialize_the_same_cursor(actors: tuple[Any, ...]) -> None:
    """Native Web consumption shares the provider's precondition and commit lock."""

    client, group, (sender, receiver) = actors
    events = [_send(client, sender)["event"]["id"] for _ in range(2)]
    barrier = Barrier(2)

    def native() -> httpx.Response:
        """Issue a native operator read concurrently with the scoped gateway operation."""

        barrier.wait()
        return client.post(f"/api/v1/groups/{group}/inbox/receiver/read", json={"limit": 1})

    with ThreadPoolExecutor(max_workers=2) as pool:
        native_result = pool.submit(native)
        barrier.wait()
        gateway = _rpc(
            client,
            receiver,
            "mail.read",
            {"operation_id": uuid.uuid4().hex, "expected_cursor": "", "limit": 1},
        )
        native_read = _result(native_result.result(timeout=15))
    if gateway.status_code == 409:
        assert native_read["messages"][0]["id"] == events[0]
        assert _result(_rpc(client, receiver, "mail.peek"))["messages"][0]["id"] == events[1]
    else:
        assert _result(gateway)["receipt"]["event_ids"] == events[:1]
        assert native_read["messages"][0]["id"] == events[1]


def test_mail_rejects_human_email_and_foreign_scope_before_mutation(
    actors: tuple[Any, ...],
) -> None:
    """Mail accepts qualified bound-Group Actors and never changes human chat semantics."""

    client, group, (sender, receiver) = actors
    for audience in (
        ["user"],
        ["user", "receiver"],
        ["outside@example.test"],
        ["offline:somewhere"],
        ["other-group::receiver"],
    ):
        response = _rpc(
            client,
            sender,
            "mail.send",
            {"operation_id": uuid.uuid4().hex, "to": audience, "text": "invalid deferred audience"},
        )
        assert response.status_code == 422
    assert _result(_rpc(client, receiver, "mail.peek"))["messages"] == []
    human = _result(
        client.post(
            f"/api/v1/groups/{group}/send",
            json={"to": ["receiver"], "text": "human direct source", "message_mode": "send"},
        )
    )["event"]
    response = _rpc(
        client,
        receiver,
        "mail.reply",
        {
            "operation_id": uuid.uuid4().hex,
            "event_id": human["id"],
            "text": "deferred reply to human unsupported",
        },
    )
    assert response.status_code == 422
    assert _result(_rpc(client, receiver, "mail.cursor"))["cursor"]["event_id"] == ""
