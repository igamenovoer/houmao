"""Qualify the actual patched CCCC HTTP authority with isolated Actor registrations.

Select a dedicated compatible loopback instance using HOUMAO_CCCC_TEST_URL.
These checks deliberately fail setup when that explicit prerequisite is absent.
"""

from __future__ import annotations

from collections.abc import Iterator
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
                                "/api/v1/external-receiver/v1/grants",
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
        "/api/v1/external-receiver/v1/rpc",
        headers={"Authorization": "Bearer " + grant["token"]},
        json={"operation": operation, "arguments": arguments or {}},
    )


def test_grants_cannot_impersonate_or_administer(actors: tuple[Any, ...]) -> None:
    """Exercise actual HTTP authentication including the local operator fallback boundary."""

    client, group_id, grants = actors
    sender = grants[0]
    bound = _result(_rpc(client, sender, "binding"))
    assert bound["actor_id"] == "sender"
    assert _rpc(client, sender, "binding", {"actor_id": "receiver"}).status_code == 422
    response = client.post(
        "/api/v1/external-receiver/v1/takeover",
        headers={"Authorization": "Bearer " + sender["token"]},
        json={"group_id": group_id, "actor_id": "receiver"},
    )
    assert response.status_code == 403
    assert _rpc(client, sender, "unsupported.operation").status_code in {403, 422}


def test_current_lease_and_explicit_operator_takeover(actors: tuple[Any, ...]) -> None:
    """A second ordinary receiver cannot silently steal valid intake authority."""

    client, group_id, grants = actors
    receiver = grants[1]
    lease = _result(_rpc(client, receiver, "lease.acquire"))
    assert _rpc(client, receiver, "lease.acquire").status_code == 409
    assert _rpc(client, receiver, "lease.acquire", {"force": True}).status_code in {403, 422}
    _result(
        client.post(
            "/api/v1/external-receiver/v1/takeover",
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
    offer = _result(_rpc(client, receiver, "lease.next", lease_args))["offer"]
    assert offer["event_id"] == event_id
    refused = {
        **lease_args,
        "attempt_id": offer["attempt_id"],
        "outcome": "refused",
        "retryable": True,
    }
    _result(_rpc(client, receiver, "lease.outcome", refused))
    _result(_rpc(client, receiver, "lease.release", lease_args))
    lease = _result(_rpc(client, receiver, "lease.acquire"))
    lease_args = {k: lease[k] for k in ("lease_id", "lease_generation")}
    assert _result(_rpc(client, receiver, "lease.next", lease_args))["offer"] is None
    duplicate = _result(_rpc(client, sender, "chat.send", send))
    assert duplicate["event"]["id"] == event_id
    assert _result(_rpc(client, receiver, "lease.next", lease_args))["offer"] is None
    assert _rpc(client, sender, "chat.send", {**send, "text": "different"}).status_code == 409
    assert (
        _rpc(
            client, receiver, "chat.retry", {"event_id": event_id, "actor_ids": ["receiver"]}
        ).status_code
        == 403
    )
    _result(_rpc(client, sender, "chat.retry", {"event_id": event_id, "actor_ids": ["receiver"]}))
    retried = _result(_rpc(client, receiver, "lease.next", lease_args))["offer"]
    assert retried["attempt_id"] != offer["attempt_id"]
    _result(
        _rpc(
            client,
            receiver,
            "lease.outcome",
            {**lease_args, "attempt_id": retried["attempt_id"], "outcome": "accepted"},
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
