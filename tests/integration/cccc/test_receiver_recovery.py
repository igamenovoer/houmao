"""Exercise retained receiver authority across actual CCCC process failures.

Select a patched binary with ``HOUMAO_CCCC_TEST_BINARY`` and an external private
scratch parent with ``HOUMAO_CCCC_RECOVERY_ROOT``. Each test owns its process,
loopback port, and disposable home. No shared development service is stopped.
"""

from __future__ import annotations

from collections.abc import Iterator
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
from typing import Any
import uuid

import httpx
import pytest


def _result(response: httpx.Response) -> dict[str, Any]:
    """Extract successful data without exposing grant-bearing responses on failure."""

    assert response.status_code == 200, f"Provider returned HTTP {response.status_code}"
    envelope = response.json()
    assert envelope.get("ok"), "Provider returned an unsuccessful envelope"
    return dict(envelope["result"])


class _Provider:
    """Own one isolated real provider and its explicitly provisioned Actors."""

    def __init__(self) -> None:
        """Declare the owned lifecycle and HTTP resources."""

        self.m_binary: Path = Path()
        self.m_root: Path = Path()
        self.m_endpoint: str = ""
        self.m_environment: dict[str, str] = {}
        self.m_process: subprocess.Popen[bytes] | None = None
        self.m_client: httpx.Client | None = None
        self.m_group: str = ""
        self.m_grants: dict[str, dict[str, Any]] = {}

    @classmethod
    def create(cls, binary: Path, root: Path) -> _Provider:
        """Start a private process and provision three independent receiver grants."""

        provider = cls()
        provider.m_binary = binary
        provider.m_root = root
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        provider.m_endpoint = f"http://127.0.0.1:{port}"
        provider.m_environment = {
            key: value for key, value in os.environ.items() if not key.startswith("CCCC_")
        }
        provider.m_environment.update(CCCC_HOME=str(root / "data"), CCCC_WEB_HOST="127.0.0.1")
        provider.m_client = httpx.Client(
            base_url=provider.m_endpoint,
            headers={"Origin": provider.m_endpoint, "Referer": provider.m_endpoint + "/"},
            trust_env=False,
            follow_redirects=False,
            timeout=10,
        )
        try:
            provider.start()
            provider.m_group = _result(
                provider.client.post(
                    "/api/v1/groups", json={"title": "recovery-" + uuid.uuid4().hex}
                )
            )["group_id"]
            for actor in ("sender", "receiver", "other"):
                provider.add_actor(actor)
            return provider
        except BaseException:
            provider.close()
            raise

    @property
    def client(self) -> httpx.Client:
        """Return the open client for this process's local operator surface."""

        assert self.m_client is not None
        return self.m_client

    @property
    def group(self) -> str:
        """Return the isolated Group registration."""

        return self.m_group

    def start(self) -> None:
        """Launch the combined daemon/Web host and wait for actual daemon health."""

        assert self.m_process is None
        descriptor = os.open(
            self.m_root / "provider.log", os.O_CREAT | os.O_APPEND | os.O_WRONLY, 0o600
        )
        with os.fdopen(descriptor, "ab") as log:
            self.m_process = subprocess.Popen(
                [
                    str(self.m_binary),
                    "--headless",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    self.m_endpoint.rsplit(":", 1)[1],
                ],
                cwd=self.m_root,
                env=self.m_environment,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            assert self.m_process.poll() is None, "Owned provider exited during startup"
            try:
                if self.client.get("/api/v1/health").status_code == 200:
                    return
            except httpx.TransportError:
                pass
            time.sleep(0.1)
        raise AssertionError("Owned provider did not become ready")

    def crash(self) -> None:
        """Kill only the spawned host, including its embedded daemon, without cleanup."""

        assert self.m_process is not None
        self.m_process.kill()
        self.m_process.wait(timeout=10)
        self.m_process = None

    def close(self) -> None:
        """Release only resources created by this test."""

        if self.m_process is not None:
            self.m_process.terminate()
            try:
                self.m_process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                self.m_process.kill()
                self.m_process.wait(timeout=10)
            self.m_process = None
        if self.m_client is not None:
            self.m_client.close()
            self.m_client = None

    def add_actor(self, actor: str) -> dict[str, Any]:
        """Register an inert Actor and explicitly convert it into an external receiver."""

        _result(
            self.client.post(
                f"/api/v1/groups/{self.group}/actors",
                json={"actor_id": actor, "runtime": "custom", "command": ["/bin/true"]},
            )
        )
        return self.issue_grant(actor)

    def issue_grant(self, actor: str) -> dict[str, Any]:
        """Issue a normal Actor grant through the selected local operator surface."""

        grant = _result(
            self.client.post(
                "/api/v1/external-receiver/v2/grants",
                json={"group_id": self.group, "actor_id": actor},
            )
        )
        self.m_grants[actor] = grant
        return grant

    def rpc(
        self,
        actor: str,
        operation: str,
        arguments: dict[str, Any] | None = None,
        *,
        grant: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Call the Actor protocol with the current or deliberately selected old grant."""

        selected = grant if grant is not None else self.m_grants[actor]
        return self.client.post(
            "/api/v1/external-receiver/v2/rpc",
            headers={"Authorization": "Bearer " + selected["token"]},
            json={"operation": operation, "arguments": arguments or {}},
        )

    def lease(self, actor: str) -> dict[str, Any]:
        """Acquire intake authority and return only the fields accepted by lease operations."""

        lease = _result(self.rpc(actor, "lease.acquire"))
        assert lease["expires_in_seconds"] == 45
        return {key: lease[key] for key in ("lease_id", "lease_generation")}

    def start_dispatch(
        self,
        actor: str,
        lease: dict[str, Any],
        offers: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Durably authorize the exact ordered members of one handoff."""

        args = {
            **lease,
            "dispatch_id": uuid.uuid4().hex,
            "attempt_ids": [offer["attempt_id"] for offer in offers],
        }
        result = _result(self.rpc(actor, "lease.start", args))
        assert result["outcome"] == "started" and result["attempt_ids"] == args["attempt_ids"]
        return {**lease, "dispatch_id": args["dispatch_id"]}

    def send(self, *recipients: str) -> str:
        """Store a fresh sender-authored source event and return its durable identity."""

        sent = _result(
            self.rpc(
                "sender",
                "chat.send",
                {
                    "operation_id": uuid.uuid4().hex,
                    "to": list(recipients or ("receiver",)),
                    "text": "synthetic recovery payload",
                    "mode": "send",
                },
            )
        )
        return str(sent["event"]["id"])

    def receipts(self, event: str) -> list[dict[str, Any]]:
        """Read authoritative attempt metadata through its source author's grant."""

        return list(
            _result(self.rpc("sender", "chat.deliveries", {"event_id": event}))["deliveries"]
        )


@pytest.fixture
def provider() -> Iterator[_Provider]:
    """Require explicit binary/root inputs and remove only this test's private home."""

    binary_setting = os.environ.get("HOUMAO_CCCC_TEST_BINARY")
    root_setting = os.environ.get("HOUMAO_CCCC_RECOVERY_ROOT")
    assert binary_setting, "Recovery qualification requires HOUMAO_CCCC_TEST_BINARY"
    assert root_setting, "Recovery qualification requires HOUMAO_CCCC_RECOVERY_ROOT"
    binary = Path(binary_setting).expanduser().resolve()
    root = Path(root_setting).expanduser().resolve()
    checkout = Path(__file__).resolve().parents[3]
    assert not root.is_relative_to(checkout), "Recovery state must stay outside the checkout"
    assert binary.is_file() and os.access(binary, os.X_OK), (
        "Select an executable patched CCCC binary"
    )
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.TemporaryDirectory(prefix="receiver-recovery-", dir=root) as directory:
        instance = _Provider.create(binary, Path(directory))
        try:
            yield instance
        finally:
            instance.close()


def test_actual_daemon_restart_retains_authority_without_replaying_offer(
    provider: _Provider,
) -> None:
    """A SIGKILL leaves an uncertain attempt and a live lease that a replacement cannot steal."""

    lease = provider.lease("receiver")
    event = provider.send()
    [offer] = _result(provider.rpc("receiver", "lease.next", lease))["offers"]
    started = provider.start_dispatch("receiver", lease, [offer])
    provider.crash()
    provider.start()

    assert _result(provider.rpc("receiver", "binding"))["actor_id"] == "receiver"
    assert provider.rpc("receiver", "lease.acquire").status_code == 409
    assert _result(provider.rpc("receiver", "lease.next", lease))["offers"] == []
    assert provider.receipts(event)[0]["state"] == "uncertain"
    late = {**started, "outcome": "accepted"}
    assert provider.rpc("receiver", "lease.settle", late).status_code == 409
    retry = {"event_id": event, "actor_ids": ["receiver"]}
    assert provider.rpc("sender", "chat.retry", retry).status_code == 409

    _result(provider.rpc("sender", "chat.retry", {**retry, "allow_uncertain_retry": True}))
    [replacement] = _result(provider.rpc("receiver", "lease.next", lease))["offers"]
    assert replacement["event_id"] == event
    assert replacement["attempt_id"] != offer["attempt_id"]
    dispatch = provider.start_dispatch("receiver", lease, [replacement])
    _result(provider.rpc("receiver", "lease.settle", {**dispatch, "outcome": "accepted"}))
    assert [item["state"] for item in provider.receipts(event)] == ["accepted", "uncertain"]
    history = _result(provider.rpc("sender", "chat.history", {"event_id": event}))
    assert history["messages"][0]["id"] == event


def test_real_lease_expiry_fences_late_acknowledgement(provider: _Provider) -> None:
    """Wait for the negotiated 45-second lease rather than editing retained provider state."""

    started = time.monotonic()
    lease = provider.lease("receiver")
    event = provider.send()
    [offer] = _result(provider.rpc("receiver", "lease.next", lease))["offers"]
    dispatch = provider.start_dispatch("receiver", lease, [offer])
    assert provider.rpc("receiver", "lease.acquire").status_code == 409
    deadline = started + 50
    while time.monotonic() < deadline:
        response = provider.rpc("receiver", "lease.acquire")
        if response.status_code == 200:
            replacement = _result(response)
            break
        assert response.status_code == 409, "Unexpected failure while awaiting natural lease expiry"
        time.sleep(0.4)
    else:
        raise AssertionError("The negotiated receiver lease did not expire")
    assert time.monotonic() - started >= 44.5
    assert replacement["lease_generation"] > lease["lease_generation"]
    late = {**dispatch, "outcome": "accepted"}
    assert provider.rpc("receiver", "lease.settle", late).status_code == 409
    new_lease = {key: replacement[key] for key in ("lease_id", "lease_generation")}
    assert _result(provider.rpc("receiver", "lease.next", new_lease))["offers"] == []
    assert provider.receipts(event)[0]["state"] == "uncertain"


def test_grant_revocation_retires_authority_without_replay(provider: _Provider) -> None:
    """An operator can retire an issued grant while preserving source and terminal receipt."""

    lease = provider.lease("receiver")
    event = provider.send()
    [offer] = _result(provider.rpc("receiver", "lease.next", lease))["offers"]
    provider.start_dispatch("receiver", lease, [offer])
    grant = provider.m_grants["receiver"]
    _result(provider.client.delete("/api/v1/external-receiver/v2/grants/" + grant["grant_id"]))
    assert provider.rpc("receiver", "binding", grant=grant).status_code == 401
    provider.issue_grant("receiver")
    replacement = provider.lease("receiver")
    assert _result(provider.rpc("receiver", "lease.next", replacement))["offers"] == []
    assert provider.receipts(event)[0]["state"] == "uncertain"


def test_actor_recreation_invalidates_previous_registration(provider: _Provider) -> None:
    """A reused Actor name gets a new generation and cannot inherit the old credential."""

    old = provider.m_grants["receiver"]
    lease = provider.lease("receiver")
    event = provider.send()
    _result(provider.rpc("receiver", "lease.next", lease))
    _result(provider.client.delete(f"/api/v1/groups/{provider.group}/actors/receiver"))
    new = provider.add_actor("receiver")
    assert new["actor_generation"] != old["actor_generation"]
    assert provider.rpc("receiver", "binding", grant=old).status_code in {401, 422}
    replacement = provider.lease("receiver")
    assert _result(provider.rpc("receiver", "lease.next", replacement))["offers"] == []
    assert provider.receipts(event)[0]["actor_generation"] == old["actor_generation"]


def test_partial_delivery_and_repeated_acknowledgement_are_recipient_scoped(
    provider: _Provider,
) -> None:
    """One accepted handoff survives a repeated acknowledgement and another recipient's refusal."""

    leases = {actor: provider.lease(actor) for actor in ("receiver", "other")}
    event = provider.send("receiver", "other")
    offers = {
        actor: _result(provider.rpc(actor, "lease.next", lease))["offers"][0]
        for actor, lease in leases.items()
    }
    for actor, outcome in (("receiver", "accepted"), ("other", "refused")):
        dispatch = provider.start_dispatch(actor, leases[actor], [offers[actor]])
        arguments = {**dispatch, "outcome": outcome}
        _result(provider.rpc(actor, "lease.settle", arguments))
        # Treat the first successful HTTP response as lost, then repeat only settlement.
        _result(provider.rpc(actor, "lease.settle", arguments))
        assert _result(provider.rpc(actor, "lease.next", leases[actor]))["offers"] == []
    assert {item["actor_id"]: item["state"] for item in provider.receipts(event)} == {
        "receiver": "accepted",
        "other": "refused",
    }
    assert (
        provider.rpc(
            "sender", "chat.retry", {"event_id": event, "actor_ids": ["receiver"]}
        ).status_code
        == 409
    )
    _result(provider.rpc("sender", "chat.retry", {"event_id": event, "actor_ids": ["other"]}))
    [fresh] = _result(provider.rpc("other", "lease.next", leases["other"]))["offers"]
    assert fresh["attempt_id"] != offers["other"]["attempt_id"]
    assert _result(provider.rpc("receiver", "lease.next", leases["receiver"]))["offers"] == []


def test_group_stop_retires_intake_without_controlling_external_body(provider: _Provider) -> None:
    """CCCC Group lifecycle stops receiver intake while an independently owned body remains alive."""

    body = subprocess.Popen(["/bin/sleep", "120"], stdin=subprocess.DEVNULL)
    try:
        lease = provider.lease("receiver")
        event = provider.send()
        [offer] = _result(provider.rpc("receiver", "lease.next", lease))["offers"]
        provider.start_dispatch("receiver", lease, [offer])
        _result(provider.client.post(f"/api/v1/groups/{provider.group}/stop"))
        assert body.poll() is None
        assert provider.rpc("receiver", "lease.renew", lease).status_code == 503
        assert provider.receipts(event)[0]["state"] == "uncertain"
        snapshot = json.dumps(_result(provider.client.get(f"/api/v1/groups/{provider.group}")))
        assert '"external_receiver": true' in snapshot
        assert '"command": []' in snapshot
    finally:
        body.terminate()
        body.wait(timeout=10)


def test_first_delivery_recovers_from_chat_commit_before_state_projection(
    provider: _Provider,
) -> None:
    """Replay the retained chat with the exact pre-send receiver state after a crash."""

    lease = provider.lease("receiver")
    state_path = (
        provider.m_root / "data" / "groups" / provider.group / "state" / "external_receiver.json"
    )
    before = state_path.read_bytes()
    event = provider.send()
    original = provider.receipts(event)[0]
    assert original["state"] == "pending"
    provider.crash()
    state_path.write_bytes(before)
    provider.start()
    [offer] = _result(provider.rpc("receiver", "lease.next", lease))["offers"]
    assert offer["event_id"] == event and offer["attempt_id"] == original["attempt_id"]
    assert _result(provider.rpc("receiver", "lease.next", lease))["offers"] == []
    _result(provider.rpc("receiver", "lease.release", lease))
    replacement = provider.lease("receiver")
    [resumed] = _result(provider.rpc("receiver", "lease.next", replacement))["offers"]
    assert resumed["attempt_id"] == original["attempt_id"]
    assert (
        provider.rpc(
            "receiver",
            "lease.start",
            {
                **lease,
                "dispatch_id": uuid.uuid4().hex,
                "attempt_ids": [offer["attempt_id"]],
            },
        ).status_code
        == 409
    )


def test_exact_batch_start_defer_and_settlement_are_fenced(provider: _Provider) -> None:
    """Settling one admitted batch preserves exact membership across readiness races."""

    lease = provider.lease("receiver")
    events = [provider.send(), provider.send()]
    offers = _result(provider.rpc("receiver", "lease.next", lease))["offers"]
    assert [item["event_id"] for item in offers] == events
    first = provider.start_dispatch("receiver", lease, offers)
    same_request = {**first, "attempt_ids": [item["attempt_id"] for item in offers]}
    assert _result(provider.rpc("receiver", "lease.start", same_request))["outcome"] == "started"
    assert (
        provider.rpc(
            "receiver",
            "lease.start",
            {
                **first,
                "attempt_ids": same_request["attempt_ids"][:1],
            },
        ).status_code
        == 409
    )
    deferred = {**first, "outcome": "deferred"}
    _result(provider.rpc("receiver", "lease.settle", deferred))
    _result(provider.rpc("receiver", "lease.settle", deferred))
    assert (
        provider.rpc(
            "receiver",
            "lease.start",
            {
                **lease,
                "dispatch_id": uuid.uuid4().hex,
                "attempt_ids": same_request["attempt_ids"][:1],
            },
        ).status_code
        == 409
    )
    second = provider.start_dispatch("receiver", lease, offers)
    assert second["dispatch_id"] != first["dispatch_id"]
    assert (
        provider.rpc("receiver", "lease.settle", {**first, "outcome": "accepted"}).status_code
        == 409
    )
    settled = _result(provider.rpc("receiver", "lease.settle", {**second, "outcome": "accepted"}))
    assert settled["attempt_ids"] == same_request["attempt_ids"]
    assert [provider.receipts(event)[0]["state"] for event in events] == ["accepted", "accepted"]
    provider.crash()
    provider.start()
    assert [provider.receipts(event)[0]["state"] for event in events] == ["accepted", "accepted"]


def test_direct_receipt_expiry_fences_old_generation_and_leaves_no_replay(
    provider: _Provider,
) -> None:
    """A retained direct exposure becomes uncertain after its independent receipt expires."""

    grant = _result(
        provider.rpc("receiver", "lease.acquire", {"transport": "pull", "receiver": "direct"})
    )
    lease = {key: grant[key] for key in ("lease_id", "lease_generation")}
    event = provider.send()
    batch = _result(provider.rpc("receiver", "lease.next", lease))
    _result(provider.rpc("receiver", "lease.release", lease))
    state_path = (
        provider.m_root / "data" / "groups" / provider.group / "state" / "external_receiver.json"
    )
    provider.crash()
    # Restore the same receipt image with only its clock deadline elapsed.
    state = json.loads(state_path.read_bytes())
    read = next(item for item in state["direct_reads"] if item["receipt"] == batch["receipt"])
    read["expires_ms"] = 0
    for attempt in state["attempts"]:
        if attempt["id"] in read["attempt_ids"]:
            attempt["deadline_ms"] = 0
    state_path.write_text(json.dumps(state))
    provider.start()
    receipt = {"receipt": batch["receipt"]}
    expired = provider.rpc("receiver", "chat.ack", receipt)
    assert expired.status_code == 422 and expired.json()["error"]["code"] == "receipt_expired"
    new_lease = provider.lease("receiver")
    assert _result(provider.rpc("receiver", "lease.next", new_lease))["offers"] == []
    assert provider.receipts(event)[0]["state"] == "uncertain"
    _result(provider.client.delete(f"/api/v1/groups/{provider.group}/actors/receiver"))
    provider.add_actor("receiver")
    assert provider.rpc("receiver", "chat.ack", receipt).status_code == 404


def test_pending_capacity_and_age_have_distinct_provider_receipts(provider: _Provider) -> None:
    """Exercise retained full-queue and expired-work images through the real provider."""

    caps = _result(provider.rpc("receiver", "capabilities"))["limits"]
    event = provider.send()
    state_path = (
        provider.m_root / "data" / "groups" / provider.group / "state" / "external_receiver.json"
    )
    provider.crash()
    state = json.loads(state_path.read_bytes())
    [pending] = state["attempts"]
    # Unrelated pending entries fill the selection budget without 1,023 RPCs.
    for sequence in range(2, caps["max_pending_messages"] + 1):
        state["attempts"].append(
            {
                **pending,
                "id": uuid.uuid4().hex,
                "event_id": uuid.uuid4().hex,
                "sequence": sequence,
            }
        )
    state["sequence"] = caps["max_pending_messages"]
    state_path.write_text(json.dumps(state))
    provider.start()
    refused = provider.send()
    receipt = provider.receipts(refused)[0]
    assert receipt["state"] == "refused" and receipt["error_code"] == "pending_capacity"
    provider.crash()

    state = json.loads(state_path.read_bytes())
    # Keep genuine entries for the provider's age-boundary check.
    state["attempts"] = [
        attempt for attempt in state["attempts"] if attempt["event_id"] in {event, refused}
    ]
    for attempt in state["attempts"]:
        if attempt["event_id"] == event:
            attempt["expiry_ms"] = 0
    state_path.write_text(json.dumps(state))
    provider.start()
    receipt = provider.receipts(event)[0]
    assert receipt["state"] == "failed" and receipt["error_code"] == "pending_expired"
