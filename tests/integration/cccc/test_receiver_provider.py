"""Qualify the actual patched CCCC HTTP authority with isolated Actor registrations.

Select a dedicated compatible loopback instance using HOUMAO_CCCC_TEST_URL.
These checks deliberately fail setup when that explicit prerequisite is absent.
"""

from __future__ import annotations

from collections.abc import Iterator
import json
import os
import uuid
from typing import Any

import httpx
import pytest


class _Grant(dict[str, Any]):
    """Keep private bearer values out of pytest argument representations."""

    def __repr__(self) -> str:
        """Return a fixed diagnostic even when an assertion includes this mapping."""

        return "<private CCCC Actor grant>"


def _result(response: httpx.Response) -> dict[str, Any]:
    """Extract a provider result without dumping secret-bearing responses on failure."""

    if response.status_code != 200:
        raise AssertionError(f"Provider request failed with HTTP {response.status_code}")
    envelope = response.json()
    if not envelope.get("ok"):
        raise AssertionError("Provider request returned an unsuccessful envelope")
    return dict(envelope["result"])


@pytest.fixture
def actors() -> Iterator[tuple[httpx.Client, str, list[dict[str, Any]]]]:
    """Provision only the test's Group and grants through explicit local administration."""

    endpoint = os.environ.get("HOUMAO_CCCC_TEST_URL")
    assert endpoint, "Actual CCCC qualification requires HOUMAO_CCCC_TEST_URL"
    assert endpoint.startswith("http://127.0.0.1:"), "Select an isolated local CCCC instance"
    with httpx.Client(
        base_url=endpoint,
        headers={"Origin": endpoint, "Referer": endpoint + "/"},
        trust_env=False,
        follow_redirects=False,
        timeout=20,
    ) as client:
        group = _result(
            client.post("/api/v1/groups", json={"title": "receiver-" + uuid.uuid4().hex})
        )
        group_id = group["group_id"]
        grants = []
        try:
            for actor_id in ("sender", "receiver"):
                _result(
                    client.post(
                        f"/api/v1/groups/{group_id}/actors",
                        json={
                            "actor_id": actor_id,
                            "runtime": "custom",
                            "command": ["/bin/true"],
                        },
                    )
                )
                grants.append(
                    _Grant(
                        _result(
                            client.post(
                                "/api/v1/external-receiver/v2/grants",
                                json={
                                    "group_id": group_id,
                                    "actor_id": actor_id,
                                },
                            )
                        )
                    )
                )
            yield client, group_id, grants
        finally:
            response = client.delete(f"/api/v1/groups/{group_id}")
            assert response.status_code == 200, "Owned test Group cleanup failed"


def _rpc(
    client: httpx.Client,
    grant: dict[str, Any],
    operation: str,
    arguments: dict[str, Any] | None = None,
) -> httpx.Response:
    """Use only a normal Actor grant on the fixed-identity protocol surface."""

    return client.post(
        "/api/v1/external-receiver/v2/rpc",
        headers={"Authorization": "Bearer " + grant["token"]},
        json={"operation": operation, "arguments": arguments or {}},
    )


def test_grants_cannot_impersonate_or_administer(actors: tuple[Any, ...]) -> None:
    """Exercise actual HTTP authentication including the local operator fallback boundary."""

    client, group_id, grants = actors
    sender = grants[0]
    bound = _result(_rpc(client, sender, "binding"))
    assert bound["actor_id"] == "sender" and bound["protocol_version"] == 2
    assert _rpc(client, sender, "binding", {"actor_id": "receiver"}).status_code == 422
    response = client.post(
        "/api/v1/external-receiver/v2/takeover",
        headers={"Authorization": "Bearer " + sender["token"]},
        json={"group_id": group_id, "actor_id": "receiver"},
    )
    assert response.status_code == 403
    assert _rpc(client, sender, "unsupported.operation").status_code in {403, 422}


def test_current_lease_and_explicit_operator_takeover(actors: tuple[Any, ...]) -> None:
    """A second ordinary receiver cannot silently steal valid intake authority."""

    client, group_id, grants = actors
    receiver = grants[1]
    lease = _result(
        _rpc(client, receiver, "lease.acquire", {"transport": "push", "receiver": "gateway"})
    )
    assert (
        _rpc(
            client, receiver, "lease.acquire", {"transport": "pull", "receiver": "direct"}
        ).status_code
        == 409
    )
    assert _rpc(client, receiver, "lease.acquire", {"force": True}).status_code in {403, 422}
    _result(
        client.post(
            "/api/v1/external-receiver/v2/takeover",
            json={
                "group_id": group_id,
                "actor_id": "receiver",
            },
        )
    )
    replacement = _result(_rpc(client, receiver, "lease.acquire"))
    assert replacement["lease_generation"] > lease["lease_generation"]
    old = {k: lease[k] for k in ("lease_id", "lease_generation")}
    assert _rpc(client, receiver, "lease.renew", old).status_code in {403, 409}


def test_handoff_receipt_retry_and_no_reconnect_replay(actors: tuple[Any, ...]) -> None:
    """Reconnection restores intake while a refused source remains sender-owned work."""

    client, _group, grants = actors
    sender, receiver = grants
    lease = _result(_rpc(client, receiver, "lease.acquire"))
    lease_args = {k: lease[k] for k in ("lease_id", "lease_generation")}
    send = {
        "operation_id": uuid.uuid4().hex,
        "to": ["receiver"],
        "text": "synthetic",
        "mode": "send",
    }
    stored = _result(_rpc(client, sender, "chat.send", send))
    event_id = stored["event"]["id"]
    [offer] = _result(_rpc(client, receiver, "lease.next", lease_args))["offers"]
    assert offer["event_id"] == event_id
    dispatch = _start(client, receiver, lease_args, [offer])
    refused = {
        **lease_args,
        "dispatch_id": dispatch,
        "outcome": "refused",
        "retryable": True,
    }
    _result(_rpc(client, receiver, "lease.settle", refused))
    _result(_rpc(client, receiver, "lease.release", lease_args))
    lease = _result(_rpc(client, receiver, "lease.acquire"))
    lease_args = {k: lease[k] for k in ("lease_id", "lease_generation")}
    assert _result(_rpc(client, receiver, "lease.next", lease_args))["offers"] == []
    duplicate = _result(_rpc(client, sender, "chat.send", send))
    assert duplicate["event"]["id"] == event_id
    assert _result(_rpc(client, receiver, "lease.next", lease_args))["offers"] == []
    assert _rpc(client, sender, "chat.send", {**send, "text": "different"}).status_code == 409
    assert (
        _rpc(
            client, receiver, "chat.retry", {"event_id": event_id, "actor_ids": ["receiver"]}
        ).status_code
        == 403
    )
    _result(_rpc(client, sender, "chat.retry", {"event_id": event_id, "actor_ids": ["receiver"]}))
    [retried] = _result(_rpc(client, receiver, "lease.next", lease_args))["offers"]
    assert retried["attempt_id"] != offer["attempt_id"]
    dispatch = _start(client, receiver, lease_args, [retried])
    _result(
        _rpc(
            client,
            receiver,
            "lease.settle",
            {**lease_args, "dispatch_id": dispatch, "outcome": "accepted"},
        )
    )
    receipts = _result(_rpc(client, sender, "chat.deliveries", {"event_id": event_id}))
    assert receipts["event_id"] == event_id
    assert receipts["has_more"] is False
    assert [
        (row["event_id"], row["attempt_id"], row["state"]) for row in receipts["deliveries"]
    ] == [
        (event_id, retried["attempt_id"], "accepted"),
        (event_id, offer["attempt_id"], "refused"),
    ]

    latest = _result(_rpc(client, sender, "chat.deliveries", {"event_id": event_id, "limit": 1}))
    assert latest["deliveries"] == receipts["deliveries"][:1]
    assert latest["has_more"] is True


def test_recipient_scope_and_history_limits(actors: tuple[Any, ...]) -> None:
    """Metadata reads and mutations enforce their declared Actor/count scope."""

    client, _group, grants = actors
    sender = grants[0]
    for i in range(3):
        _result(
            _rpc(
                client,
                sender,
                "chat.send",
                {
                    "operation_id": uuid.uuid4().hex,
                    "to": ["receiver"],
                    "text": f"synthetic-{i}",
                    "mode": "send",
                },
            )
        )
    page = _result(_rpc(client, sender, "chat.history", {"limit": 1}))
    assert len(page["messages"]) == 1 and page["has_more"]
    assert _rpc(client, sender, "chat.history", {"limit": 101}).status_code == 422
    assert (
        _rpc(
            client,
            sender,
            "chat.send",
            {
                "operation_id": uuid.uuid4().hex,
                "to": ["recipient@example.test"],
                "text": "invalid",
                "mode": "send",
            },
        ).status_code
        == 422
    )


def _start(
    client: httpx.Client,
    receiver: dict[str, Any],
    lease: dict[str, Any],
    offers: list[dict[str, Any]],
) -> str:
    """Register an exact provider dispatch and return its one-use identifier."""

    dispatch = uuid.uuid4().hex
    result = _result(
        _rpc(
            client,
            receiver,
            "lease.start",
            {
                **lease,
                "dispatch_id": dispatch,
                "attempt_ids": [offer["attempt_id"] for offer in offers],
            },
        )
    )
    assert result["outcome"] == "started"
    return dispatch


def _send_chat(
    client: httpx.Client,
    sender: dict[str, Any],
    text: str,
) -> dict[str, Any]:
    """Store one ordinary chat addressed to the selected receiver."""

    return _result(
        _rpc(
            client,
            sender,
            "chat.send",
            {
                "operation_id": uuid.uuid4().hex,
                "to": ["receiver"],
                "text": text,
            },
        )
    )


def test_pull_snapshot_retains_encounter_order_and_respects_bounds(actors: tuple[Any, ...]) -> None:
    """Pending work is available after a gateway starts and respects the pull boundary."""

    client, _group, (sender, receiver) = actors
    one = _send_chat(client, sender, "first")
    two = _send_chat(client, sender, "second")
    three = _send_chat(client, sender, "past the count bound")
    assert one["deliveries"][0]["state"] == two["deliveries"][0]["state"] == "pending"
    granted = _result(
        _rpc(client, receiver, "lease.acquire", {"transport": "pull", "receiver": "gateway"})
    )
    lease = {key: granted[key] for key in ("lease_id", "lease_generation")}
    small = _rpc(client, receiver, "lease.next", {**lease, "max_bytes": 120})
    assert _result(small)["offers"] == [] and len(small.content) <= 120
    response = _rpc(client, receiver, "lease.next", {**lease, "limit": 2, "max_bytes": 4096})
    batch = _result(response)["offers"]
    assert len(response.content) <= 4096
    assert [item["event_id"] for item in batch] == [one["event"]["id"], two["event"]["id"]]
    assert [item["timestamp"] for item in batch] == [one["event"]["ts"], two["event"]["ts"]]
    assert batch[0]["sequence"] < batch[1]["sequence"]
    new = _send_chat(client, sender, "after snapshot")
    dispatch = _start(client, receiver, lease, batch)
    _result(
        _rpc(
            client,
            receiver,
            "lease.settle",
            {**lease, "dispatch_id": dispatch, "outcome": "accepted"},
        )
    )
    [next_offer] = _result(_rpc(client, receiver, "lease.next", {**lease, "limit": 1}))["offers"]
    assert next_offer["event_id"] == three["event"]["id"]
    [later_offer] = _result(_rpc(client, receiver, "lease.next", lease))["offers"]
    assert later_offer["event_id"] == new["event"]["id"]


def _push_frames(
    client: httpx.Client,
    receiver: dict[str, Any],
    lease: dict[str, Any],
    *,
    limit: int,
    max_bytes: int = 4096,
    after_sequence: int = 0,
) -> list[dict[str, Any]]:
    """Read a finite offer stream with explicit flow credit and resume cursor."""

    with client.stream(
        "GET",
        "/api/v1/external-receiver/v2/stream",
        headers={"Authorization": "Bearer " + receiver["token"]},
        params={
            **lease,
            "limit": limit,
            "max_bytes": max_bytes,
            "kind": "chat",
            "after_sequence": after_sequence,
        },
    ) as response:
        assert (
            response.status_code == 200
            and response.headers["content-type"] == "application/x-ndjson"
        )
        return [json.loads(line) for line in response.iter_lines()]


def test_push_stream_credit_does_not_settle_or_reorder(actors: tuple[Any, ...]) -> None:
    """Repeated frames have stable identities and exhausted credit preserves pending work."""

    client, _group, (sender, receiver) = actors
    granted = _result(
        _rpc(client, receiver, "lease.acquire", {"transport": "push", "receiver": "gateway"})
    )
    lease = {key: granted[key] for key in ("lease_id", "lease_generation")}
    one = _send_chat(client, sender, "first")
    two = _send_chat(client, sender, "second")
    assert _rpc(client, receiver, "lease.next", lease).status_code == 409
    assert _push_frames(client, receiver, lease, limit=1, max_bytes=20) == []
    [frame] = _push_frames(client, receiver, lease, limit=1)
    [duplicate] = _push_frames(client, receiver, lease, limit=1)
    assert frame["kind"] == "offer"
    first = frame["offer"]
    assert first["event_id"] == one["event"]["id"]
    assert duplicate["offer"]["attempt_id"] == first["attempt_id"]
    [frame] = _push_frames(client, receiver, lease, limit=1, after_sequence=first["sequence"])
    second = frame["offer"]
    assert second["event_id"] == two["event"]["id"]
    assert second["sequence"] > first["sequence"]
    statuses = _result(_rpc(client, sender, "chat.deliveries", {"event_id": two["event"]["id"]}))
    assert statuses["deliveries"][0]["state"] == "offered"


@pytest.mark.parametrize("transport", ["pull", "push"])
def test_negotiated_offer_limit_gives_oversized_head_a_terminal_outcome(
    actors: tuple[Any, ...], transport: str
) -> None:
    """The receiver's hard limit distinguishes oversized work from temporary credit."""

    client, _group, (sender, receiver) = actors
    oversized = _send_chat(client, sender, "large head " * 160)
    following = _send_chat(client, sender, "fitting tail")
    acquired = _result(
        _rpc(
            client,
            receiver,
            "lease.acquire",
            {"transport": transport, "receiver": "gateway", "max_offer_bytes": 800},
        )
    )
    lease = {key: acquired[key] for key in ("lease_id", "lease_generation")}
    if transport == "pull":
        rejected = _rpc(client, receiver, "lease.next", lease)
    else:
        rejected = client.get(
            "/api/v1/external-receiver/v2/stream",
            headers={"Authorization": "Bearer " + receiver["token"]},
            params={**lease, "kind": "chat", "limit": 1, "max_bytes": 4096},
        )
    assert rejected.status_code == 422 and rejected.json()["error"]["code"] == "event_too_large"
    result = _result(
        _rpc(client, sender, "chat.deliveries", {"event_id": oversized["event"]["id"]})
    )
    [receipt] = result["deliveries"]
    assert receipt["state"] == "failed" and receipt["retryable"] is False
    if transport == "pull":
        [offer] = _result(_rpc(client, receiver, "lease.next", lease))["offers"]
    else:
        [frame] = _push_frames(client, receiver, lease, limit=1)
        offer = frame["offer"]
    assert offer["event_id"] == following["event"]["id"]


def test_direct_receipt_survives_lease_release_and_references_are_scoped(
    actors: tuple[Any, ...],
) -> None:
    """A direct read can settle independently of later gateway intake and reply."""

    client, _group, (sender, receiver) = actors
    original = _send_chat(client, sender, "direct pull target")
    granted = _result(
        _rpc(client, receiver, "lease.acquire", {"transport": "pull", "receiver": "direct"})
    )
    lease = {key: granted[key] for key in ("lease_id", "lease_generation")}
    batch = _result(_rpc(client, receiver, "lease.next", lease))
    [offer] = batch["offers"]
    assert offer["event_id"] == original["event"]["id"]
    receipt = {"receipt": batch["receipt"]}
    _result(_rpc(client, receiver, "lease.release", lease))
    replacement = _result(_rpc(client, receiver, "lease.acquire"))
    replacement_lease = {key: replacement[key] for key in ("lease_id", "lease_generation")}
    assert _result(_rpc(client, receiver, "lease.next", replacement_lease))["offers"] == []
    assert _rpc(client, sender, "chat.ack", receipt).status_code == 404
    ack = _result(_rpc(client, receiver, "chat.ack", receipt))
    assert ack["acknowledged"] and ack["attempt_ids"] == [offer["attempt_id"]]
    assert _result(_rpc(client, receiver, "chat.ack", receipt)) == ack
    event_ref = {"event_ref": offer["event_ref"]}
    observed = _result(_rpc(client, receiver, "chat.history", event_ref))
    assert observed["messages"][0]["id"] == original["event"]["id"]
    assert _rpc(client, sender, "chat.history", event_ref).status_code == 404
    reply = _result(
        _rpc(
            client,
            receiver,
            "chat.reply",
            {
                **event_ref,
                "operation_id": uuid.uuid4().hex,
                "text": "direct reply",
            },
        )
    )
    assert reply["event"]["data"]["reply_to"] == original["event"]["id"]
    statuses = _result(
        _rpc(client, sender, "chat.deliveries", {"event_id": original["event"]["id"]})
    )
    assert statuses["deliveries"][0]["state"] == "direct_read"
