"""Exercise CCCC plugin authority, immediate handoff, and connection retirement."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import importlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, Mock

from fastapi import FastAPI
import httpx
from pydantic import ValidationError
import pytest

from houmao.gateway.plugins import (
    PluginDispatchError,
    PluginDispatchResult,
    PluginOwner,
)


@pytest.fixture
def implementation(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Import optional source only within the focused unit-test fixture."""

    source = Path(__file__).resolve().parents[3] / "packages/houmao-cccc/src"
    monkeypatch.syspath_prepend(str(source))
    return importlib.import_module("houmao_cccc.plugin")


class Service:
    """Supply an observable provider wire boundary for plugin-only tests."""

    def __init__(self) -> None:
        """Create isolated scripted transport and worker observations."""

        self.m_dispatches: dict[str, list[str]] = {}
        self.m_calls: list[tuple[str, dict[str, Any]]] = []
        self.m_offers: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self.m_notices: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self.m_outcomes: list[dict[str, Any]] = []
        self.m_failures: dict[str, Exception] = {}
        self.m_clients: list[Client] = []
        self.m_history: dict[str, Any] = {"messages": [], "has_more": False}
        self.m_queue_enabled: bool = False
        self.m_chat: dict[str, dict[str, Any]] = {}
        self.m_reads: dict[tuple[str, str], dict[str, Any]] = {}
        self.m_claim_started: asyncio.Event = asyncio.Event()
        self.m_block_claim: asyncio.Event | None = None
        self.m_lose_claim_result: bool = False
        self.m_block_send: asyncio.Event | None = None
        self.m_send_started: asyncio.Event = asyncio.Event()
        self.m_binding: dict[str, Any] = {
            "protocol_version": 2,
            "group_id": "g1",
            "actor_id": "a1",
            "actor_generation": "gen1",
        }

    def new_client(self, _configuration: Any, _token: str) -> Client:
        """Return one close-observable client per connection epoch."""

        client = Client()
        client.m_service = self
        self.m_clients.append(client)
        return client


class Client:
    """Implement the selected asynchronous transport protocol without HTTP retries."""

    def __init__(self) -> None:
        """Initialize close state and its owning scripted service."""

        self.m_service: Service | None = None
        self.m_closed: bool = False

    async def request(self, operation: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Produce the exact provider results observed by the plugin worker."""

        assert self.m_service is not None
        service = self.m_service
        service.m_calls.append((operation, dict(arguments)))
        if operation in service.m_failures:
            raise service.m_failures[operation]
        if operation == "binding":
            return service.m_binding
        if operation == "capabilities":
            capabilities: dict[str, Any] = {
                "protocol_version": 2,
                "operations": [
                    "binding",
                    "capabilities",
                    "members",
                    "lease.acquire",
                    "lease.renew",
                    "lease.release",
                    "lease.next",
                    "lease.outcome",
                    "lease.notice.next",
                    "lease.start",
                    "lease.settle",
                    "lease.stream",
                    "chat.send",
                    "chat.reply",
                    "chat.retry",
                    "chat.history",
                    "chat.deliveries",
                    "mail.read",
                ],
                "features": {
                    "chat_pending": True,
                    "chat_batch_pull": True,
                    "chat_push_stream": True,
                    "chat_batch_settlement": True,
                },
                "limits": {
                    "max_batch_messages": 32,
                    "max_batch_bytes": 65536,
                    "max_handoff_seconds": 15,
                    "max_event_bytes": 65536,
                    "max_history_limit": 100,
                    "max_response_bytes": 262144,
                    "lease_seconds": 45,
                },
            }
            if service.m_queue_enabled:
                capabilities["features"]["chat_gateway_queue_reads"] = True
                capabilities["operations"].extend(
                    ["chat.gateway-read.claim", "chat.gateway-read.result", "chat.ack"]
                )
            return capabilities
        if operation == "lease.acquire":
            return {"lease_id": "lease1", "lease_generation": 1, "expires_in_seconds": 45}
        if operation == "lease.next":
            batch = []
            while not service.m_offers.empty() and len(batch) < arguments["limit"]:
                batch.append(service.m_offers.get_nowait())
            service.m_chat.update({item["attempt_id"]: item for item in batch})
            return {"offers": batch}
        if operation == "lease.notice.next":
            return {"offer": None if service.m_notices.empty() else service.m_notices.get_nowait()}
        if operation == "lease.start":
            identifier = arguments["dispatch_id"]
            service.m_dispatches[identifier] = arguments["attempt_ids"]
            return {
                "dispatch_id": identifier,
                "attempt_ids": arguments["attempt_ids"],
                "outcome": "started",
            }
        if operation == "lease.settle":
            identifier = arguments["dispatch_id"]
            decision = {**arguments, "attempt_ids": service.m_dispatches[identifier]}
            service.m_outcomes.append(decision)
            return decision
        if operation == "lease.outcome":
            service.m_outcomes.append(dict(arguments))
            return {"recorded": True}
        if operation in {"lease.renew", "lease.release"}:
            return {"ok": True}
        if operation == "chat.history":
            return service.m_history
        if operation == "members":
            return {
                "members": [
                    {
                        "id": "a2",
                        "title": "Peer",
                        "role": "peer",
                        "enabled": True,
                        "receive_status": "connected",
                        "env": {"SECRET": "private"},
                    }
                ]
            }
        if operation in {"chat.send", "chat.reply"}:
            service.m_send_started.set()
            if service.m_block_send is not None:
                await service.m_block_send.wait()
            return {"stored": True, "event": event("outgoing"), "deliveries": []}
        if operation == "chat.deliveries":
            return {
                "event_id": arguments["event_id"],
                "deliveries": [{"state": "uncertain", "actor_id": "a2"}],
                "has_more": False,
            }
        if operation == "chat.gateway-read.claim":
            service.m_claim_started.set()
            if service.m_block_claim is not None:
                await service.m_block_claim.wait()
            message_fields = (
                "attempt_id",
                "event_id",
                "sequence",
                "sender",
                "timestamp",
                "message_mode",
                "text",
            )
            result = {
                "found": True,
                "operation_id": arguments["operation_id"],
                "snapshot_fingerprint": arguments["snapshot_fingerprint"],
                "receipt": "f" * 32,
                "status": "pending",
                "groups": [
                    [
                        {key: service.m_chat[attempt][key] for key in message_fields}
                        for attempt in batch
                    ]
                    for batch in arguments["groups"]
                ],
            }
            service.m_reads[(arguments["binding_tag"], arguments["operation_id"])] = result
            if service.m_lose_claim_result:
                from houmao_cccc.client import ProviderError

                raise ProviderError("provider_unavailable", 503, True, "unknown")
            return result
        if operation == "chat.gateway-read.result":
            key = (arguments["binding_tag"], arguments["operation_id"])
            return service.m_reads.get(key, {"found": False, "operation_id": key[1]})
        if operation == "chat.ack":
            result = next(
                result
                for (binding, _), result in service.m_reads.items()
                if binding == arguments["binding_tag"] and result["receipt"] == arguments["receipt"]
            )
            result["status"] = "acknowledged"
            return {
                "receipt": result["receipt"],
                "acknowledged": True,
                "attempt_ids": [item["attempt_id"] for batch in result["groups"] for item in batch],
            }
        if operation == "chat.retry":
            return {"deliveries": [{"state": "uncertain", "actor_id": "a2"}]}
        raise AssertionError(operation)

    async def verify_binding(self) -> None:
        """Exercise the service binding error contract on every connection."""

        binding = await self.request("binding", {})
        if binding["protocol_version"] != 2 or binding["actor_generation"] != "gen1":
            from houmao_cccc.client import ProviderError

            raise ProviderError("receiver_incompatible", 503, False)

    async def capabilities(self) -> dict[str, Any]:
        """Return the provider capabilities negotiated by the worker."""

        return await self.request("capabilities", {})

    async def offer_stream(
        self, lease_id: str, generation: int, **kwargs: Any
    ) -> AsyncIterator[dict[str, Any]]:
        """Supply chat independently of empty Mail intake."""

        assert self.m_service is not None
        queue = (
            self.m_service.m_notices if kwargs["kind"] == "mail_notice" else self.m_service.m_offers
        )
        for _ in range(kwargs["limit"]):
            try:
                result = await asyncio.wait_for(queue.get(), timeout=0.03)
            except TimeoutError:
                return
            if result["sequence"] > kwargs["after_sequence"]:
                if kwargs["kind"] == "chat":
                    self.m_service.m_chat[result["attempt_id"]] = result
                yield result

    async def aclose(self) -> None:
        """Record transport cleanup without retaining request bodies."""

        self.m_closed = True


def event(identifier: str) -> dict[str, Any]:
    """Create a synthetic native CCCC history event."""

    return {
        "id": identifier,
        "kind": "chat.message",
        "by": "a2",
        "ts": "2026-01-01T00:00:00Z",
        "data": {"text": "Synthetic text", "to": ["a1"], "message_mode": "send"},
    }


def offer(**overrides: Any) -> dict[str, Any]:
    """Create one current finite delivery offer with full registration scope."""

    return {
        "attempt_id": "attempt1",
        "sequence": 1,
        "timestamp": "2026-01-01T00:00:00Z",
        "event_id": "event1",
        "group_id": "g1",
        "actor_id": "a1",
        "actor_generation": "gen1",
        "lease_generation": 1,
        "message_mode": "send",
        "text": "Synthetic incoming chat",
        "sender": "a2",
        "reply_to": None,
        "remaining_seconds": 1.0,
        **overrides,
    }


async def eventually(predicate: Any) -> None:
    """Bound waiting for a background event without hiding worker failures."""

    async with asyncio.timeout(2):
        while not predicate():
            await asyncio.sleep(0.005)


@asynccontextmanager
async def harness(
    implementation: Any,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    start: bool = True,
    queue: bool = False,
    delivery: Any = None,
) -> AsyncIterator[SimpleNamespace]:
    """Activate the real plugin lifespan against isolated public SDK capabilities."""

    service = Service()
    service.m_queue_enabled = queue
    monkeypatch.setattr(implementation.ProviderClient, "from_config", service.new_client)
    config = implementation.CcccConfiguration(
        endpoint="http://127.0.0.1:8848",
        group_id="g1",
        actor_id="a1",
        actor_generation="gen1",
        delivery=delivery or implementation.DeliverySettings(pull_interval=0.02),
        reconnect_delay_seconds=0.05,
        renew_interval_seconds=0.01,
    )
    tasks: list[asyncio.Task[None]] = []

    def start_worker(_name: str, worker: Any) -> None:
        """Emulate host-owned asynchronous worker supervision."""

        if start:
            tasks.append(asyncio.create_task(worker()))

    context = SimpleNamespace(
        owner=PluginOwner(agent_id="owner1", runtime_session_id="runtime1"),
        instance_id="team",
        binding_id="binding1",
        listener=None,
        credentials=SimpleNamespace(
            read=Mock(
                return_value={
                    "agent_id": "owner1",
                    "endpoint": config.endpoint,
                    "group_id": "g1",
                    "actor_id": "a1",
                    "actor_generation": "gen1",
                    "token": "synthetic-actor-token",
                }
            )
        ),
        state=SimpleNamespace(path=lambda name: tmp_path / name),
        events=SimpleNamespace(
            dispatch=AsyncMock(return_value=PluginDispatchResult(source_event_id="event1")),
            wait_until_ready=AsyncMock(return_value=object()),
            validate=Mock(),
        ),
        workers=SimpleNamespace(start_soon=start_worker),
        report_connection=Mock(),
        log=Mock(),
    )
    plugin = implementation.CcccPlugin.from_config(context, config)
    app = FastAPI()
    app.include_router(plugin.router, prefix="/v1/plugins/team")
    async with plugin.lifespan():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://local"
        ) as http:
            if start:
                await eventually(lambda: plugin.m_phase == "connected")
            try:
                yield SimpleNamespace(
                    plugin=plugin, service=service, context=context, http=http, tasks=tasks
                )
            finally:
                for task in tasks:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)


def test_factory_stages_routes_without_resources(implementation: Any, tmp_path: Path) -> None:
    """Construction must neither read credentials nor private reference state."""

    context = SimpleNamespace(credentials=Mock(), state=Mock(), workers=Mock())
    config = implementation.CcccConfiguration(
        endpoint="http://127.0.0.1:8848", group_id="g1", actor_id="a1", actor_generation="gen1"
    )
    plugin = implementation.CcccPlugin.from_config(context, config)
    assert plugin.router.routes
    context.credentials.read.assert_not_called()
    context.state.path.assert_not_called()
    context.workers.start_soon.assert_not_called()


@pytest.mark.parametrize(
    "overrides",
    [
        {"to": []},
        {"to": ["someone@example.test"]},
        {"to": ["user", "peer"]},
        {"to": ["peer", "peer"]},
        {"mode": "mail"},
        {"by": "user"},
        {"text": "  "},
    ],
)
def test_send_schema_rejects_unsupported_authority(implementation: Any, overrides: Any) -> None:
    """Reject recipient translation, deferred mode, and ordinary sender overrides."""

    with pytest.raises(ValidationError):
        implementation.SendRequest.model_validate(
            {
                "connection_token": "current",
                "operation_id": "op1",
                "to": ["peer"],
                "text": "Synthetic",
                **overrides,
            }
        )


def test_status_members_and_capabilities_are_safe(
    implementation: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Snapshot reads avoid network calls and capabilities exclude unimplemented Mail."""

    async def exercise() -> None:
        """Read actual routes while observing the scripted provider."""

        async with harness(implementation, monkeypatch, tmp_path) as h:
            before = len(h.service.m_calls)
            binding = await h.http.get("/v1/plugins/team/binding")
            capabilities = await h.http.get("/v1/plugins/team/capabilities")
            assert len(h.service.m_calls) == before
            assert binding.json()["agent_id"] == "owner1"
            assert "token" not in binding.text
            assert "mail.read" not in capabilities.json()["operations"]
            assert capabilities.json()["mail"]["available"] is False
            assert capabilities.json()["mail"]["qualified"] is False
            members = await h.http.get("/v1/plugins/team/members")
            assert members.status_code == 200
            assert "SECRET" not in members.text and "env" not in members.text
            assert members.json()["connection_token"] == h.plugin.m_connection_token
            discovery = await h.http.get("/v1/plugins/team/discovery")
            assert discovery.status_code == 200
            assert discovery.json() == {
                "endpoint": "http://127.0.0.1:8848",
                "group_id": "g1",
                "actor_id": "a1",
                "actor_generation": "gen1",
                "protocol_version": 2,
                "operations": h.plugin.m_provider_capabilities["operations"],
            }
            rejected = await h.http.get("/v1/plugins/team/binding?sender=other")
            assert rejected.status_code == 422

    asyncio.run(exercise())


def test_members_asserts_the_selected_group_without_switching_provider_scope(
    implementation: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Compare an optional Group assertion before reading the existing membership."""

    async def exercise() -> None:
        """Check both successful calls and the requests rejected before provider access."""

        async with harness(implementation, monkeypatch, tmp_path) as h:
            route = "/v1/plugins/team/members"
            plain = await h.http.get(route)
            matching = await h.http.get(route, params={"expected_group_id": "g1"})
            assert plain.status_code == matching.status_code == 200
            assert matching.json() == plain.json()
            mismatch = await h.http.get(route, params={"expected_group_id": "private-other-group"})
            assert mismatch.status_code == 409
            assert mismatch.json()["detail"]["error_code"] == "group_conflict"
            assert "gateway URL and instance" in mismatch.json()["detail"]["guidance"]
            assert "private-other-group" not in mismatch.text
            for params in (
                [("expected_group_id", "")],
                [("expected_group_id", " g1")],
                [("expected_group_id", "g\x00private")],
                [("expected_group_id", "g" * 257)],
                [("expected_group_id", "g1"), ("expected_group_id", "g1")],
            ):
                rejected = await h.http.get(route, params=params)
                assert rejected.status_code == 422
                assert rejected.json()["detail"]["error_code"] == "invalid_group_assertion"
            assert [args for op, args in h.service.m_calls if op == "members"] == [{}, {}]

    asyncio.run(exercise())


def test_delivery_receipts_select_the_same_events_by_handle_or_reference(
    implementation: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Incoming, outgoing, and history handles all use the original receipt operation."""

    async def exercise() -> None:
        """Compare both target forms against the recorded provider calls."""

        async with harness(implementation, monkeypatch, tmp_path) as h:
            await h.service.m_offers.put(offer())
            await eventually(lambda: len(h.service.m_outcomes) == 1)
            ingress = h.context.events.dispatch.call_args.args[0]
            incoming_handle = ingress.presentation.messages[0].handle
            h.service.m_history = {"messages": [event("event1")], "has_more": False}
            selected = await h.http.get("/v1/plugins/team/chat/history?event_id=event1")
            historical = selected.json()["messages"][0]
            sent = await h.http.post(
                "/v1/plugins/team/chat/send",
                json={
                    "connection_token": h.plugin.m_connection_token,
                    "operation_id": "send1",
                    "to": ["a2"],
                    "text": "Synthetic",
                },
            )
            replied = await h.http.post(
                "/v1/plugins/team/chat/reply",
                json={"handle": incoming_handle, "operation_id": "reply1", "text": "Synthetic"},
            )
            assert selected.status_code == sent.status_code == replied.status_code == 200
            assert incoming_handle != historical["handle"]
            route = "/v1/plugins/team/chat/deliveries"
            for handle, target in (
                (incoming_handle, historical),
                (historical["handle"], historical),
                (sent.json()["event"]["handle"], sent.json()["event"]),
                (replied.json()["event"]["handle"], replied.json()["event"]),
            ):
                by_handle = await h.http.get(route, params={"handle": handle, "limit": 1})
                by_ref = await h.http.get(
                    route, params={"event_ref": target["event_ref"], "limit": 1}
                )
                assert by_handle.status_code == by_ref.status_code == 200
                assert by_handle.json() == by_ref.json()
                assert by_handle.json()["event_id"] == target["event_id"]
            assert [args for op, args in h.service.m_calls if op == "chat.deliveries"] == [
                {"event_id": target, "limit": 1} for target in ["event1"] * 4 + ["outgoing"] * 4
            ]
            assert len(h.service.m_outcomes) == 1

    asyncio.run(exercise())


def test_delivery_receipts_reject_invalid_or_foreign_targets_before_provider_read(
    implementation: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Reject malformed, expired, or foreign selectors with scope-specific diagnostics."""

    async def exercise() -> None:
        """Check the gateway route directly, including duplicate HTTP parameters."""

        async with harness(implementation, monkeypatch, tmp_path) as h:
            route = "/v1/plugins/team/chat/deliveries"
            reference = h.plugin._references().encode("event", {"event_id": "event1"})
            handle = h.plugin._mint_handle("event1")
            for params in (
                [],
                [("handle", "")],
                [("event_ref", "")],
                [("handle", "h" * 129)],
                [("event_ref", "r" * 8193)],
                [("handle", handle), ("event_ref", reference)],
                [("handle", handle), ("handle", handle)],
                [("event_ref", reference), ("event_ref", reference)],
            ):
                invalid = await h.http.get(route, params=params)
                assert invalid.status_code == 422
                assert invalid.json()["detail"]["error_code"] == "invalid_delivery_target"
            native = await h.http.get(route, params={"event_id": "event1"})
            assert native.status_code == 422
            assert native.json()["detail"]["error_code"] == "unsupported_query"

            foreign_context = SimpleNamespace(
                **{
                    **vars(h.context),
                    "owner": PluginOwner(agent_id="other", runtime_session_id="other-runtime"),
                    "binding_id": "other-binding",
                }
            )
            foreign = implementation.CcccPlugin.from_config(
                foreign_context, h.plugin.m_config.model_copy(update={"group_id": "other-group"})
            )
            foreign_handle = foreign._mint_handle("event1")
            foreign_ref = implementation.ReferenceCodec.from_context(foreign_context).encode(
                "event", {"event_id": "event1"}
            )
            monkeypatch.setattr(implementation, "_HANDLE_TTL_SECONDS", 0.0)
            expired_handle = h.plugin._mint_handle("event1")
            for stale in (foreign_handle, expired_handle):
                result = await h.http.get(route, params={"handle": stale})
                assert result.status_code == 409
                assert result.json()["detail"]["error_code"] == "message_handle_stale"
                assert "authorized CCCC chat history" in result.json()["detail"]["guidance"]
            for invalid_ref in (foreign_ref, "mistyped"):
                result = await h.http.get(route, params={"event_ref": invalid_ref})
                assert result.status_code == 422
                assert result.json()["detail"]["error_code"] == "reference_scope_error"
                assert "authorized CCCC chat history" in result.json()["detail"]["guidance"]
            assert all(op != "chat.deliveries" for op, _ in h.service.m_calls)

    asyncio.run(exercise())


def test_send_and_reply_preserve_actor_and_native_references(
    implementation: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Use one service mutation and scoped reply references without sender fields."""

    async def exercise() -> None:
        """Call the real HTTP handlers and inspect provider arguments."""

        async with harness(implementation, monkeypatch, tmp_path) as h:
            sent = await h.http.post(
                "/v1/plugins/team/chat/send",
                json={
                    "connection_token": h.plugin.m_connection_token,
                    "operation_id": "send1",
                    "to": ["a2"],
                    "text": "Synthetic",
                },
            )
            assert sent.status_code == 200
            result = sent.json()
            assert result["stored"] is True and result["event"]["event_id"] == "outgoing"
            replied = await h.http.post(
                "/v1/plugins/team/chat/reply",
                json={
                    "operation_id": "reply1",
                    "handle": result["event"]["handle"],
                    "text": "Reply",
                },
            )
            assert replied.status_code == 200
            calls = [(op, args) for op, args in h.service.m_calls if op.startswith("chat.")]
            assert [op for op, _ in calls] == ["chat.send", "chat.reply"]
            assert calls[1][1]["event_id"] == "outgoing"
            assert all("by" not in args and "actor_id" not in args for _, args in calls)

    asyncio.run(exercise())


def test_stale_binding_and_foreign_reference_fail_before_provider(
    implementation: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Never interpret stale handles through a newly selected owner binding."""

    async def exercise() -> None:
        """Submit invalid operation targeting while observing provider mutations."""

        async with harness(implementation, monkeypatch, tmp_path) as h:
            stale = await h.http.post(
                "/v1/plugins/team/chat/send",
                json={
                    "connection_token": "another",
                    "operation_id": "send1",
                    "to": ["a2"],
                    "text": "Synthetic",
                },
            )
            foreign = await h.http.post(
                "/v1/plugins/team/chat/reply",
                json={
                    "operation_id": "reply1",
                    "handle": "foreign",
                    "text": "Synthetic",
                },
            )
            assert stale.status_code == 409 and foreign.status_code == 409
            assert not any(op.startswith("chat.") for op, _ in h.service.m_calls)

    asyncio.run(exercise())


def test_expired_handle_requires_exact_history_selection(
    implementation: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Issue a fresh handle only for an explicitly selected Actor-visible event."""

    async def exercise() -> None:
        async with harness(implementation, monkeypatch, tmp_path) as h:
            monkeypatch.setattr(implementation, "_HANDLE_TTL_SECONDS", 0.0)
            expired = h.plugin._mint_handle("event1")
            stale = await h.http.get(f"/v1/plugins/team/messages/{expired}")
            assert stale.status_code == 409
            assert stale.json()["detail"]["error_code"] == "message_handle_stale"
            assert not any(op == "chat.history" for op, _ in h.service.m_calls)
            monkeypatch.setattr(implementation, "_HANDLE_TTL_SECONDS", 60.0)
            h.service.m_history = {"messages": [event("event1")], "has_more": False}
            selected = await h.http.get("/v1/plugins/team/chat/history?event_id=event1")
            refreshed = selected.json()["messages"][0]["handle"]
            assert selected.status_code == 200 and refreshed != expired
            assert (await h.http.get(f"/v1/plugins/team/messages/{refreshed}")).status_code == 200

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "status,outcome,expected",
    [
        (503, "not_sent", "failed"),
        (503, "unknown", "uncertain"),
    ],
)
def test_refused_dispatch_reports_failure_without_replay(
    implementation: Any,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    status: int,
    outcome: str,
    expected: str,
) -> None:
    """Readiness recovery alone never dispatches a formerly refused payload."""

    async def exercise() -> None:
        """Fail one provider attempt then let the body become ready."""

        async with harness(implementation, monkeypatch, tmp_path) as h:
            h.context.events.dispatch.side_effect = PluginDispatchError(
                error_code="invalid_event",
                status_code=status,
                retryable=True,
                dispatch_outcome=outcome,
            )
            await h.service.m_offers.put(offer())
            await eventually(lambda: len(h.service.m_outcomes) == 1)
            assert h.service.m_outcomes[0]["outcome"] == expected
            h.context.events.dispatch.side_effect = None
            await asyncio.sleep(0.08)
            assert h.context.events.dispatch.await_count == 1
            assert sorted(p.name for p in tmp_path.iterdir()) == ["reference-key"]

    asyncio.run(exercise())


def test_successful_offer_contains_reply_handle_and_ordinary_content(
    implementation: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The body receives an ordinary event with a usable reply hint for this instance."""

    async def exercise() -> None:
        """Dispatch ordinary content and exercise its advertised reply command."""

        async with harness(implementation, monkeypatch, tmp_path) as h:
            await h.service.m_offers.put(offer(text="/compact"))
            await h.service.m_offers.put(
                offer(attempt_id="attempt2", event_id="event2", sequence=2, sender="a3")
            )
            await eventually(lambda: len(h.service.m_outcomes) == 1)
            assert h.service.m_outcomes[0]["outcome"] == "accepted"
            assert h.service.m_outcomes[0]["attempt_ids"] == ["attempt1", "attempt2"]
            h.context.events.dispatch.assert_awaited_once()

            envelope = h.context.events.dispatch.call_args.args[0]
            assert envelope.text is None
            projection = envelope.presentation
            assert projection.binding.group_id == "g1"
            assert projection.binding.actor_id == "a1"
            assert [item.sender for item in projection.messages] == ["a2", "a3"]
            assert projection.messages[0].text == "/compact"
            handle = projection.messages[0].handle
            assert handle.startswith("msg_team.") and len(handle) < 36

            h.service.m_history = {"messages": [event("event1")], "has_more": False}
            details = await h.http.get(f"/v1/plugins/team/messages/{handle}")
            assert details.status_code == 200
            assert details.json() == {
                "handle": handle,
                "sender": "a2",
                "timestamp": "2026-01-01T00:00:00Z",
                "mode": "send",
                "text": "Synthetic text",
                "reply_to": None,
            }
            for _ in range(2):
                reply = await h.http.post(
                    "/v1/plugins/team/chat/reply",
                    json={
                        "handle": handle,
                        "operation_id": "reply1",
                        "text": "Observed correctly",
                    },
                )
                assert reply.status_code == 200
            assert [arguments for op, arguments in h.service.m_calls if op == "chat.reply"] == [
                {
                    "operation_id": "reply1",
                    "event_id": "event1",
                    "text": "Observed correctly",
                    "mode": "send",
                }
            ] * 2

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "overrides",
    [
        {"actor_generation": "old"},
        {"lease_generation": 2},
        {"message_mode": "mail"},
        {"remaining_seconds": 0},
        {"remaining_seconds": float("nan")},
        {"text": "x" * 65536},
    ],
)
def test_invalid_offers_never_reach_body(
    implementation: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, overrides: Any
) -> None:
    """Reject scope, mode, deadline, sender, and complete envelope violations."""

    async def exercise() -> None:
        """Report permanent rejection before any SDK dispatch."""

        async with harness(implementation, monkeypatch, tmp_path) as h:
            await h.service.m_offers.put(offer(**overrides))
            await eventually(lambda: h.plugin.m_phase == "degraded")
            assert not h.service.m_outcomes
            h.context.events.dispatch.assert_not_awaited()

    asyncio.run(exercise())


def test_offer_deadline_cancels_sdk_dispatch(
    implementation: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Cancellation reaches the SDK's request fence before a late body handoff."""

    async def exercise() -> None:
        """Use a pending dispatcher to observe deadline cancellation."""

        cancelled = asyncio.Event()

        async def pending(_event: Any, **_kwargs: Any) -> Any:
            """Represent a handoff that cannot confirm before expiry."""

            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        async with harness(implementation, monkeypatch, tmp_path) as h:
            h.context.events.dispatch.side_effect = pending
            await h.service.m_offers.put(offer(remaining_seconds=0.06))
            await eventually(lambda: len(h.service.m_outcomes) == 1)
            assert cancelled.is_set()
            assert h.service.m_outcomes[0]["outcome"] == "uncertain"

    asyncio.run(exercise())


def test_deferred_start_retries_the_same_batch_with_a_fresh_start_id(
    implementation: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Preserve a sealed pull batch through a definitive late readiness loss."""

    async def exercise() -> None:
        async with harness(implementation, monkeypatch, tmp_path) as h:
            h.context.events.dispatch.side_effect = [
                PluginDispatchError(error_code="not_ready", status_code=409, retryable=True),
                PluginDispatchResult(source_event_id="event1"),
            ]
            await h.service.m_offers.put(offer())
            await h.service.m_offers.put(offer(attempt_id="attempt2", sequence=2))
            await eventually(lambda: len(h.service.m_outcomes) == 2)
            deferred, accepted = h.service.m_outcomes
            assert deferred["outcome"] == "deferred" and accepted["outcome"] == "accepted"
            assert deferred["dispatch_id"] != accepted["dispatch_id"]
            assert deferred["attempt_ids"] == accepted["attempt_ids"] == ["attempt1", "attempt2"]

    asyncio.run(exercise())


def test_transport_switch_waits_for_active_handoff_and_fences_handles(
    implementation: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Apply a revision, drain the old start, and acquire a push lease after release."""

    async def exercise() -> None:
        async with harness(implementation, monkeypatch, tmp_path) as h:
            route = "/v1/plugins/team/delivery"
            initial = (await h.http.get(route)).json()
            assert initial["effective"]["transport"] == "pull"
            started, finish = asyncio.Event(), asyncio.Event()

            async def dispatch(_event: Any, **_kwargs: Any) -> Any:
                started.set()
                await finish.wait()
                return PluginDispatchResult(source_event_id="event1")

            h.context.events.dispatch.side_effect = dispatch
            await h.service.m_offers.put(offer())
            async with asyncio.timeout(2):
                await started.wait()
            old_token = h.plugin.m_connection_token
            old_event = h.context.events.dispatch.call_args.args[0]
            old_handle = old_event.presentation.messages[0].handle
            settings = {"transport": "push", "push_policy": "asap"}
            transition = await h.http.put(route, json={"revision": 0, "settings": settings})
            assert transition.status_code == 200
            assert transition.json()["desired"]["transport"] == "push"
            assert transition.json()["effective"]["transport"] == "pull"
            assert transition.json()["transition"] == "applying"
            conflict = await h.http.put(route, json={"revision": 0, "settings": settings})
            assert conflict.status_code == 409
            finish.set()
            await eventually(
                lambda: (
                    h.plugin.m_effective is not None and h.plugin.m_effective.transport == "push"
                )
            )
            assert h.service.m_outcomes[0]["outcome"] == "accepted"
            assert h.plugin.m_connection_token != old_token
            operations = [op for op, _ in h.service.m_calls]
            assert operations.index("lease.settle") < operations.index("lease.release")
            assert [
                args["transport"] for op, args in h.service.m_calls if op == "lease.acquire"
            ] == ["pull", "push"]
            old = await h.http.get(f"/v1/plugins/team/messages/{old_handle}")
            assert (
                old.status_code == 409
                and old.json()["detail"]["error_code"] == "message_handle_stale"
            )

            h.context.events.wait_until_ready.side_effect = None
            await h.service.m_offers.put(offer(attempt_id="attempt2", sequence=2))
            await h.service.m_offers.put(offer(attempt_id="attempt3", sequence=3))
            await eventually(lambda: len(h.service.m_outcomes) == 3)
            assert [r["attempt_ids"] for r in h.service.m_outcomes] == [
                ["attempt1"],
                ["attempt2"],
                ["attempt3"],
            ]

    asyncio.run(exercise())


def test_notice_admission_uses_independent_credit_while_chat_waits(
    implementation: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Send a typed notice through immediate admission while a timed batch stays open."""

    async def exercise() -> None:
        async with harness(implementation, monkeypatch, tmp_path) as h:
            notice = AsyncMock()
            monkeypatch.setattr(h.plugin, "_offer", notice)
            response = await h.http.put(
                "/v1/plugins/team/delivery",
                json={
                    "revision": 0,
                    "settings": {
                        "transport": "push",
                        "push_policy": "batch",
                        "quiet_interval": 1.0,
                        "max_wait": 2.0,
                    },
                },
            )
            assert response.status_code == 200
            await eventually(
                lambda: (
                    h.plugin.m_effective is not None and h.plugin.m_effective.transport == "push"
                )
            )
            await h.service.m_offers.put(offer(remaining_seconds=3.0))
            await eventually(lambda: h.plugin.m_buffer.deadline is not None)
            deadline = h.plugin.m_buffer.deadline
            await h.service.m_notices.put(offer(sequence=2, kind="mail_notice"))
            await eventually(lambda: notice.await_count == 1)
            assert h.plugin.m_buffer.deadline == deadline
            h.context.events.dispatch.assert_not_awaited()

    asyncio.run(exercise())


def test_history_pages_are_scoped_and_non_consuming(
    implementation: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Continue only the same bounded history query without reading Mail."""

    async def exercise() -> None:
        """Exercise history continuations through actual HTTP query validation."""

        async with harness(implementation, monkeypatch, tmp_path) as h:
            h.service.m_history = {"messages": [event("e2"), event("e1")], "has_more": True}
            first = await h.http.get("/v1/plugins/team/chat/history?limit=2")
            assert first.status_code == 200
            cursor = first.json()["cursor"]
            second = await h.http.get(
                "/v1/plugins/team/chat/history", params={"limit": 2, "cursor": cursor}
            )
            assert second.status_code == 200
            changed = await h.http.get(
                "/v1/plugins/team/chat/history", params={"limit": 3, "cursor": cursor}
            )
            assert changed.status_code == 422
            calls = [args for op, args in h.service.m_calls if op == "chat.history"]
            assert calls[1]["before_event_id"] == "e1"
            assert all(not op.startswith("mail.") for op, _ in h.service.m_calls)
            h.context.events.dispatch.assert_not_awaited()

    asyncio.run(exercise())


def test_refresh_rejects_another_actor_without_retiring_old_connection(
    implementation: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A bad candidate credential must not replace a working Actor binding."""

    async def exercise() -> None:
        """Change only the selected document and invoke the actual refresh route."""

        async with harness(implementation, monkeypatch, tmp_path) as h:
            old = h.plugin.m_client
            h.context.credentials.read.return_value = {"agent_id": "someone-else"}
            result = await h.http.post(
                "/v1/plugins/team/connection/refresh-credentials",
                json={"expected_binding_id": "binding1"},
            )
            assert result.status_code == 422
            assert h.plugin.m_client is old and h.plugin.m_phase == "connected"

    asyncio.run(exercise())


def test_disconnect_retires_pending_send_with_uncertain_outcome(
    implementation: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Drain one started mutation without resubmitting through another epoch."""

    async def exercise() -> None:
        """Disconnect while the provider has a live send request."""

        async with harness(implementation, monkeypatch, tmp_path) as h:
            h.service.m_block_send = asyncio.Event()
            pending = asyncio.create_task(
                h.http.post(
                    "/v1/plugins/team/chat/send",
                    json={
                        "connection_token": h.plugin.m_connection_token,
                        "operation_id": "send1",
                        "to": ["a2"],
                        "text": "Synthetic",
                    },
                )
            )
            await h.service.m_send_started.wait()
            stopped = await h.http.post(
                "/v1/plugins/team/connection/disconnect", json={"expected_binding_id": "binding1"}
            )
            sent = await pending
            assert stopped.status_code == 200
            assert (
                sent.status_code == 503 and sent.json()["detail"]["dispatch_outcome"] == "unknown"
            )
            assert h.plugin.m_phase == "disconnected"
            assert len([1 for op, _ in h.service.m_calls if op == "chat.send"]) == 1
            assert all(client.m_closed for client in h.service.m_clients)

    asyncio.run(exercise())


def test_lease_conflict_does_not_force_takeover(
    implementation: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A crashed receiver lease causes bounded waiting, never forced acquisition."""

    async def exercise() -> None:
        """Observe all acquisition arguments during an ordinary reconnect conflict."""

        async with harness(implementation, monkeypatch, tmp_path) as h:
            h.service.m_failures["lease.acquire"] = implementation.ProviderError(
                "receiver_lease_conflict", 409, True, retry_after_seconds=0.02
            )
            result = await h.http.post(
                "/v1/plugins/team/connection/reconnect", json={"expected_binding_id": "binding1"}
            )
            assert result.status_code == 200
            await eventually(lambda: h.plugin.m_error_code == "receiver_lease_conflict")
            assert all(
                args == {"transport": "pull", "receiver": "gateway", "max_offer_bytes": 65408}
                for op, args in h.service.m_calls
                if op == "lease.acquire"
            )
            assert h.plugin.m_phase == "reconnecting"

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "binding_change", [{"actor_generation": "recreated"}, {"protocol_version": True}]
)
def test_incompatible_binding_never_acquires_receiver(
    implementation: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, binding_change: Any
) -> None:
    """Protocol and registration validation precede receiver authority acquisition."""

    async def exercise() -> None:
        """Let the actual worker observe an incompatible registration snapshot."""

        async with harness(implementation, monkeypatch, tmp_path, start=False) as h:
            h.service.m_binding.update(binding_change)
            h.tasks.append(asyncio.create_task(h.plugin._connection_worker()))
            await eventually(lambda: h.plugin.m_phase == "degraded")
            assert not any(op == "lease.acquire" for op, _ in h.service.m_calls)
            h.context.events.dispatch.assert_not_awaited()

    asyncio.run(exercise())


def test_disconnect_cancels_live_offer_without_replaying_on_connect(
    implementation: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A new connection epoch cannot resume another attempt's pending payload."""

    async def exercise() -> None:
        """Retire an active SDK handoff, then restore connectivity explicitly."""

        started, cancelled = asyncio.Event(), asyncio.Event()

        async def pending(_event: Any, **_kwargs: Any) -> Any:
            """Observe cancellation of the old request-scoped dispatch."""

            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        async with harness(implementation, monkeypatch, tmp_path) as h:
            h.context.events.dispatch.side_effect = pending
            await h.service.m_offers.put(offer())
            await started.wait()
            stopped = await h.http.post(
                "/v1/plugins/team/connection/disconnect", json={"expected_binding_id": "binding1"}
            )
            assert stopped.status_code == 200 and cancelled.is_set()
            assert h.service.m_outcomes[-1]["outcome"] == "uncertain"
            h.context.events.dispatch.side_effect = None
            connected = await h.http.post(
                "/v1/plugins/team/connection/connect", json={"expected_binding_id": "binding1"}
            )
            assert connected.status_code == 200
            await eventually(lambda: h.plugin.m_phase == "connected")
            await asyncio.sleep(0.08)
            assert h.context.events.dispatch.await_count == 1

    asyncio.run(exercise())


def test_started_send_timeout_is_not_repeated(
    implementation: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Unknown outbound mutation failures remain sender-visible and single attempt."""

    async def exercise() -> None:
        """Submit one HTTP send through the real plugin handler."""

        async with harness(implementation, monkeypatch, tmp_path) as h:
            h.service.m_failures["chat.send"] = implementation.ProviderError(
                "provider_unavailable", 503, True, outcome="unknown"
            )
            result = await h.http.post(
                "/v1/plugins/team/chat/send",
                json={
                    "connection_token": h.plugin.m_connection_token,
                    "operation_id": "send1",
                    "to": ["a2"],
                    "text": "Synthetic",
                },
            )
            assert result.status_code == 503
            assert result.json()["detail"]["dispatch_outcome"] == "unknown"
            assert len([1 for op, _ in h.service.m_calls if op == "chat.send"]) == 1

    asyncio.run(exercise())


def test_rotation_preserves_reference_scope_and_retires_old_client(
    implementation: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Same-account credential refresh retains targeting but revokes the old epoch."""

    async def exercise() -> None:
        """Rotate the selected token and reconnect through the actual route."""

        async with harness(implementation, monkeypatch, tmp_path) as h:
            old_client = h.plugin.m_client
            old_epoch = h.plugin.m_epoch
            old_ref = h.plugin._references().encode("event", {"event_id": "before-rotation"})
            old_handle = h.plugin._mint_handle("before-rotation")
            h.context.credentials.read.return_value["token"] = "synthetic-rotated-grant"
            response = await h.http.post(
                "/v1/plugins/team/connection/refresh-credentials",
                json={"expected_binding_id": "binding1"},
            )
            assert response.status_code == 200
            await eventually(lambda: h.plugin.m_phase == "connected")
            assert old_client.m_closed and h.plugin.m_epoch > old_epoch
            assert h.plugin.m_client is not old_client
            assert h.plugin._references().decode(old_ref, "event") == {
                "event_id": "before-rotation"
            }
            assert h.context.credentials.read.call_count == 2
            route = "/v1/plugins/team/chat/deliveries"
            stale = await h.http.get(route, params={"handle": old_handle})
            assert stale.status_code == 409
            assert stale.json()["detail"]["error_code"] == "message_handle_stale"
            assert all(op != "chat.deliveries" for op, _ in h.service.m_calls)
            valid = await h.http.get(route, params={"event_ref": old_ref})
            assert valid.status_code == 200
            assert valid.json()["event_id"] == "before-rotation"

    asyncio.run(exercise())


def test_history_byte_limit_and_invalid_anchor_are_explicit(
    implementation: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Oversized or stale pages fail without consuming or fabricating empty history."""

    async def exercise() -> None:
        """Read oversize history, then let the provider reject a scoped stale anchor."""

        async with harness(implementation, monkeypatch, tmp_path) as h:
            h.plugin.m_config = h.plugin.m_config.model_copy(update={"max_response_bytes": 1024})
            large = event("large")
            large["data"]["text"] = "x" * 2048
            h.service.m_history = {"messages": [large], "has_more": False}
            oversized = await h.http.get("/v1/plugins/team/chat/history?limit=1")
            assert oversized.status_code == 422
            assert oversized.json()["detail"]["error_code"] == "history_response_too_large"
            cursor = h.plugin._references().encode(
                "history", {"before_event_id": "gone", "limit": 1}
            )
            h.service.m_failures["chat.history"] = implementation.ProviderError(
                "event_not_found", 404, False
            )
            stale = await h.http.get(
                "/v1/plugins/team/chat/history", params={"limit": 1, "cursor": cursor}
            )
            assert stale.status_code == 404
            assert stale.json()["detail"]["error_code"] == "event_not_found"
            assert all(not op.startswith("mail.") for op, _ in h.service.m_calls)
            h.context.events.dispatch.assert_not_awaited()

    asyncio.run(exercise())


def test_malformed_mutation_result_preserves_uncertainty_and_operation_id(
    implementation: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A malformed post-send result cannot establish that the send did not occur."""

    async def exercise() -> None:
        """Return incomplete provider storage metadata after its send boundary."""

        async with harness(implementation, monkeypatch, tmp_path) as h:
            monkeypatch.setattr(
                h.plugin, "_call", AsyncMock(return_value={"stored": True, "event": {"data": {}}})
            )
            result = await h.http.post(
                "/v1/plugins/team/chat/send",
                json={
                    "connection_token": h.plugin.m_connection_token,
                    "operation_id": "send1",
                    "to": ["a2"],
                    "text": "Synthetic",
                },
            )
            assert result.status_code == 503
            assert result.json()["detail"]["dispatch_outcome"] == "unknown"
            assert result.json()["detail"]["operation_id"] == "send1"

    asyncio.run(exercise())


_QUEUE_ROUTE = "/v1/plugins/team/chat/queue"


def park_chat_body(harness_state: SimpleNamespace) -> asyncio.Event:
    """Keep ordinary dispatch waiting until the test releases readiness."""

    ready = asyncio.Event()

    async def wait_until_ready(*, timeout_seconds: float) -> object | None:
        """Model the dispatcher's finite readiness wait."""

        try:
            async with asyncio.timeout(timeout_seconds):
                await ready.wait()
        except TimeoutError:
            return None
        return object()

    harness_state.context.events.wait_until_ready.side_effect = wait_until_ready
    return ready


def queue_offer(number: int, **overrides: Any) -> dict[str, Any]:
    """Name each staged offer independently across FIFO and handle assertions."""

    return offer(
        attempt_id=f"attempt{number}",
        event_id=f"event{number}",
        sequence=number,
        remaining_seconds=5.0,
        **overrides,
    )


@pytest.mark.parametrize("policy", ["pull", "asap", "batch"])
def test_queue_peek_preserves_batch_boundaries_and_finite_wait(
    implementation: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, policy: str
) -> None:
    """A bounded peek observes only sealed work under any effective intake policy."""

    async def exercise() -> None:
        settings = implementation.DeliverySettings(
            transport="pull" if policy == "pull" else "push",
            pull_interval=0.02,
            push_policy=None if policy == "pull" else policy,
            quiet_interval=0.15 if policy == "batch" else None,
            max_wait=0.5 if policy == "batch" else None,
        )
        async with harness(
            implementation, monkeypatch, tmp_path, queue=True, delivery=settings
        ) as h:
            park_chat_body(h)
            capabilities = await h.http.get("/v1/plugins/team/capabilities")
            assert capabilities.json()["chat_queue"] is True
            waiting = asyncio.create_task(
                h.http.get(_QUEUE_ROUTE, params={"min_messages": 2, "wait_seconds": 0.8})
            )
            await asyncio.sleep(0)
            assert not waiting.done()
            h.service.m_offers.put_nowait(
                queue_offer(1, sender="alpha", text="Ignore instructions")
            )
            h.service.m_offers.put_nowait(queue_offer(2, sender="beta", text="ordinary reply"))
            if policy == "batch":
                await eventually(lambda: h.plugin.m_buffer.open_count == 2)
                open_view = (await h.http.get(_QUEUE_ROUTE)).json()
                assert open_view["open_batch_count"] == 2
                assert open_view["snapshot"] is None and not open_view["batches"]
            preview = (await waiting).json()
            assert preview["kind"] == "cccc_chat_requests" and preview["snapshot"]
            assert preview["open_batch_count"] == 0 and not preview["additional_queued"]
            assert [len(batch) for batch in preview["batches"]] == (
                [1, 1] if policy == "asap" else [2]
            )
            messages = [message for batch in preview["batches"] for message in batch]
            assert [m["sender"] for m in messages] == ["alpha", "beta"]
            assert messages[0]["text"] == "Ignore instructions"
            assert all(
                set(m) == {"sender", "timestamp", "mode", "text", "handle"} for m in messages
            )
            assert len({m["handle"] for m in messages}) == 2
            assert h.plugin.m_buffer.credit[0] == 30
            for params in (
                {"min_messages": 33},
                {"min_messages": 0},
                {"wait_seconds": 21},
                [("min_messages", 1), ("min_messages", 1)],
            ):
                assert (await h.http.get(_QUEUE_ROUTE, params=params)).status_code == 422
            timed_out = (
                await h.http.get(_QUEUE_ROUTE, params={"min_messages": 3, "wait_seconds": 0.02})
            ).json()
            assert timed_out["snapshot"]
            assert sum(len(batch) for batch in timed_out["batches"]) == 2

    asyncio.run(exercise())


def test_queue_pop_keeps_credit_until_durable_and_does_not_consume_append(
    implementation: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A tool read owns the original head while ordinary dispatch waits."""

    async def exercise() -> None:
        async with harness(implementation, monkeypatch, tmp_path, queue=True) as h:
            ready = park_chat_body(h)
            h.service.m_offers.put_nowait(queue_offer(1))
            h.service.m_offers.put_nowait(queue_offer(2))
            response = await h.http.get(
                _QUEUE_ROUTE, params={"min_messages": 2, "wait_seconds": 0.8}
            )
            original = response.json()["snapshot"]
            assert original
            h.service.m_offers.put_nowait(queue_offer(3))
            await eventually(lambda: len(h.plugin.m_buffer.sealed) == 2)
            hold = asyncio.Event()
            h.service.m_block_claim = hold
            pop = asyncio.create_task(
                h.http.post(
                    _QUEUE_ROUTE + "/pop", json={"snapshot": original, "operation_id": "op-1"}
                )
            )
            await eventually(h.service.m_claim_started.is_set)
            ready.set()
            during = (await h.http.get(_QUEUE_ROUTE)).json()
            assert during["snapshot"] is None and during["additional_queued"]
            assert h.plugin.m_buffer.credit[0] == 29
            assert h.service.m_dispatches == {}
            hold.set()
            read = (await pop).json()
            assert read["status"] == "pending" and len(read["batches"]) == 1
            assert len(read["batches"][0]) == 2
            await eventually(lambda: len(h.service.m_outcomes) == 1)
            assert h.service.m_outcomes[0]["attempt_ids"] == ["attempt3"]
            assert h.plugin.m_buffer.credit[0] == 32
            ack = await h.http.post(_QUEUE_ROUTE + "/ack", json={"receipt": read["receipt"]})
            assert ack.json() == {"acknowledged": True, "receipt": read["receipt"]}
            recovered = (await h.http.get(_QUEUE_ROUTE + "/pops/op-1")).json()
            assert recovered["status"] == "acknowledged" and recovered["receipt"] == read["receipt"]
            handle = recovered["batches"][0][1]["handle"]
            reply = await h.http.post(
                "/v1/plugins/team/chat/reply",
                json={"handle": handle, "operation_id": "reply1", "text": "Confirmed"},
            )
            assert reply.status_code == 200
            assert [args["event_id"] for op, args in h.service.m_calls if op == "chat.reply"] == [
                "event2"
            ]
            repeated = await h.http.post(
                _QUEUE_ROUTE + "/pop", json={"snapshot": original, "operation_id": "op-1"}
            )
            assert repeated.json()["receipt"] == read["receipt"]
            assert len([op for op, _ in h.service.m_calls if op == "chat.gateway-read.claim"]) == 1

    asyncio.run(exercise())


def test_queue_stale_pop_loses_to_ordinary_prompt(
    implementation: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """An already-started prompt fences stale previews before a provider claim."""

    async def exercise() -> None:
        async with harness(implementation, monkeypatch, tmp_path, queue=True) as h:
            ready = park_chat_body(h)
            hold = asyncio.Event()

            async def dispatch(*_args: Any, **_kwargs: Any) -> PluginDispatchResult:
                """Leave the ordinary start reserved while a stale pop competes."""

                await hold.wait()
                return PluginDispatchResult(source_event_id="event1")

            h.context.events.dispatch.side_effect = dispatch
            h.service.m_offers.put_nowait(queue_offer(1))
            snapshot = (await h.http.get(_QUEUE_ROUTE, params={"wait_seconds": 0.8})).json()[
                "snapshot"
            ]
            ready.set()
            await eventually(lambda: h.context.events.dispatch.await_count == 1)
            denial = await h.http.post(
                _QUEUE_ROUTE + "/pop", json={"snapshot": snapshot, "operation_id": "too-late"}
            )
            assert denial.status_code == 409
            assert denial.json()["detail"]["error_code"] == "queue_snapshot_stale"
            assert not h.service.m_claim_started.is_set()
            hold.set()
            await eventually(lambda: len(h.service.m_outcomes) == 1)
            assert h.service.m_outcomes[0]["outcome"] == "accepted"
            assert h.service.m_outcomes[0]["attempt_ids"] == ["attempt1"]

    asyncio.run(exercise())


def test_queue_pop_can_claim_a_definitively_deferred_prompt_batch(
    implementation: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A pre-handoff refusal releases its exact unchanged batch for tool access."""

    async def exercise() -> None:
        async with harness(implementation, monkeypatch, tmp_path, queue=True) as h:
            ready = park_chat_body(h)

            async def dispatch(*_args: Any, **_kwargs: Any) -> PluginDispatchResult:
                """Reject this ready-only handoff before dispatching any content."""

                ready.clear()
                raise PluginDispatchError(error_code="not_ready", status_code=409, retryable=True)

            h.context.events.dispatch.side_effect = dispatch
            h.service.m_offers.put_nowait(queue_offer(1))
            h.service.m_offers.put_nowait(queue_offer(2))
            peek = (
                await h.http.get(_QUEUE_ROUTE, params={"min_messages": 2, "wait_seconds": 0.8})
            ).json()
            ready.set()
            await eventually(lambda: len(h.service.m_outcomes) == 1)
            assert h.service.m_outcomes[0]["outcome"] == "deferred"
            read = (
                await h.http.post(
                    _QUEUE_ROUTE + "/pop",
                    json={"snapshot": peek["snapshot"], "operation_id": "deferred"},
                )
            ).json()
            assert [len(batch) for batch in read["batches"]] == [2]
            assert h.context.events.dispatch.await_count == 1
            claim = next(args for op, args in h.service.m_calls if op == "chat.gateway-read.claim")
            assert claim["groups"] == [h.service.m_outcomes[0]["attempt_ids"]]

    asyncio.run(exercise())


def test_queue_canceled_claim_reconciles_after_lost_response_and_rotation(
    implementation: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """One abandoned transport can finish without re-exposing the claimed work."""

    async def exercise() -> None:
        async with harness(implementation, monkeypatch, tmp_path, queue=True) as h:
            park_chat_body(h)
            h.service.m_offers.put_nowait(queue_offer(1))
            peek = (await h.http.get(_QUEUE_ROUTE, params={"wait_seconds": 0.8})).json()
            hold = asyncio.Event()
            h.service.m_block_claim = hold
            h.service.m_lose_claim_result = True
            request = {"snapshot": peek["snapshot"], "operation_id": "recover-me"}
            abandoned = asyncio.create_task(h.http.post(_QUEUE_ROUTE + "/pop", json=request))
            await eventually(h.service.m_claim_started.is_set)
            abandoned.cancel()
            with pytest.raises(asyncio.CancelledError):
                await abandoned
            assert h.plugin.m_buffer.reserved and h.plugin.m_buffer.credit[0] == 31
            hold.set()
            await eventually(lambda: h.plugin.m_buffer.credit[0] == 32)
            read = (await h.http.get(_QUEUE_ROUTE + "/pops/recover-me")).json()
            first_handle = read["batches"][0][0]["handle"]
            current_token = h.plugin.m_connection_token
            rotated = await h.http.post(
                "/v1/plugins/team/connection/reconnect", json={"expected_binding_id": "binding1"}
            )
            assert rotated.status_code == 200
            await eventually(
                lambda: (
                    h.plugin.m_phase == "connected" and h.plugin.m_connection_token != current_token
                )
            )
            assert (
                await h.http.get(f"/v1/plugins/team/messages/{first_handle}")
            ).status_code == 409
            recovered = (await h.http.post(_QUEUE_ROUTE + "/pop", json=request)).json()
            assert recovered["receipt"] == read["receipt"]
            assert recovered["batches"][0][0]["handle"] != first_handle
            conflict = await h.http.post(
                _QUEUE_ROUTE + "/pop", json={**request, "snapshot": "changed"}
            )
            assert conflict.status_code == 409
            assert conflict.json()["detail"]["error_code"] == "operation_conflict"
            ack = await h.http.post(_QUEUE_ROUTE + "/ack", json={"receipt": recovered["receipt"]})
            assert ack.json()["acknowledged"] is True
            stale = await h.http.post(
                _QUEUE_ROUTE + "/pop", json={**request, "operation_id": "new-operation"}
            )
            assert stale.status_code == 409
            assert stale.json()["detail"]["error_code"] == "queue_snapshot_stale"
            assert len([op for op, _ in h.service.m_calls if op == "chat.gateway-read.claim"]) == 1
            h.context.events.dispatch.assert_not_awaited()

    asyncio.run(exercise())


def test_queue_unresolved_claim_retires_lease_before_releasing_credit(
    implementation: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Failure to determine a commit cannot resume dispatch on the same lease."""

    async def exercise() -> None:
        async with harness(implementation, monkeypatch, tmp_path, queue=True) as h:
            park_chat_body(h)
            initial_token = h.plugin.m_connection_token
            h.service.m_failures["chat.gateway-read.claim"] = implementation.ProviderError(
                "provider_unavailable", 503, True, "unknown"
            )
            h.service.m_offers.put_nowait(queue_offer(1))
            peek = (await h.http.get(_QUEUE_ROUTE, params={"wait_seconds": 0.8})).json()
            response = await h.http.post(
                _QUEUE_ROUTE + "/pop",
                json={"snapshot": peek["snapshot"], "operation_id": "unknown"},
            )
            assert response.status_code == 503
            assert response.json()["detail"]["error_code"] == "queue_claim_unknown"
            assert response.json()["detail"]["dispatch_outcome"] == "unknown"
            assert response.json()["detail"]["operation_id"] == "unknown"
            await eventually(
                lambda: (
                    h.plugin.m_phase == "connected" and h.plugin.m_connection_token != initial_token
                )
            )
            h.context.events.dispatch.assert_not_awaited()
            result = await h.http.get(_QUEUE_ROUTE + "/pops/unknown")
            assert result.json() == {"found": False, "operation_id": "unknown"}

    asyncio.run(exercise())


def test_queue_wait_ends_when_lease_retires(
    implementation: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A waiting peek returns a typed error without crossing connection generations."""

    async def exercise() -> None:
        async with harness(implementation, monkeypatch, tmp_path, queue=True) as h:
            waiting = asyncio.create_task(
                h.http.get(_QUEUE_ROUTE, params={"min_messages": 2, "wait_seconds": 20})
            )
            await asyncio.sleep(0.01)
            assert not waiting.done()
            response = await h.http.post(
                "/v1/plugins/team/connection/disconnect", json={"expected_binding_id": "binding1"}
            )
            assert response.status_code == 200
            async with asyncio.timeout(0.5):
                retired = await waiting
            assert retired.status_code == 503
            assert retired.json()["detail"]["error_code"] == "receiver_unavailable"

    asyncio.run(exercise())


def test_queue_budget_rejects_oversized_head_without_consuming_it(
    implementation: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The response bound includes handles and both complete result envelopes."""

    async def exercise() -> None:
        async with harness(implementation, monkeypatch, tmp_path, queue=True) as h:
            ready = park_chat_body(h)
            h.plugin.m_provider_capabilities["limits"]["max_response_bytes"] = 1300
            h.service.m_offers.put_nowait(queue_offer(1, text="π" * 480))
            failure = await h.http.get(_QUEUE_ROUTE, params={"wait_seconds": 0.8})
            assert failure.status_code == 422
            assert failure.json()["detail"]["error_code"] == "content_limit"
            assert h.plugin.m_buffer.credit[0] == 31
            ready.set()
            await eventually(lambda: len(h.service.m_outcomes) == 1)
            assert h.service.m_outcomes[0]["attempt_ids"] == ["attempt1"]

    asyncio.run(exercise())


def test_queue_peek_leaves_later_whole_batches_when_budget_is_exhausted(
    implementation: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A useful prefix fits both the public and provider envelopes under credit."""

    async def exercise() -> None:
        settings = implementation.DeliverySettings(transport="push", push_policy="asap")
        async with harness(
            implementation, monkeypatch, tmp_path, queue=True, delivery=settings
        ) as h:
            park_chat_body(h)
            h.plugin.m_provider_capabilities["limits"]["max_response_bytes"] = 1300
            for number in range(1, 4):
                h.service.m_offers.put_nowait(queue_offer(number, text=str(number) * 475))
            await eventually(lambda: len(h.plugin.m_buffer.sealed) == 3)
            peek = (await h.http.get(_QUEUE_ROUTE)).json()
            assert peek["additional_queued"] and len(peek["batches"]) == 1
            assert peek["batches"][0][0]["text"] == "1" * 475
            read = (
                await h.http.post(
                    _QUEUE_ROUTE + "/pop",
                    json={"snapshot": peek["snapshot"], "operation_id": "short-prefix"},
                )
            ).json()
            assert len(read["batches"]) == 1
            later = (await h.http.get(_QUEUE_ROUTE)).json()
            assert later["batches"][0][0]["text"] == "2" * 475

    asyncio.run(exercise())


def test_ordinary_v2_provider_keeps_automatic_delivery_without_queue_access(
    implementation: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A missing additive capability disables only the queue routes."""

    async def exercise() -> None:
        async with harness(implementation, monkeypatch, tmp_path) as h:
            capabilities = (await h.http.get("/v1/plugins/team/capabilities")).json()
            assert capabilities["chat_queue"] is False
            rejection = await h.http.get(_QUEUE_ROUTE)
            assert rejection.status_code == 422
            assert rejection.json()["detail"]["error_code"] == "queue_access_unsupported"
            h.service.m_offers.put_nowait(queue_offer(1))
            await eventually(lambda: len(h.service.m_outcomes) == 1)
            assert h.service.m_outcomes[0]["outcome"] == "accepted"

    asyncio.run(exercise())


@pytest.mark.parametrize("condition", ["unavailable", "wrong_owner", "connected"])
def test_real_host_keeps_core_health_and_protects_receipts(
    implementation: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, condition: str
) -> None:
    """Mount CCCC behind real host route guards and action admission."""

    async def exercise() -> None:
        """Use actual host discovery, credential checks, lifecycle, and route guards."""

        from houmao.agents.realm_controller.gateway_admission import GatewayAdmissionMiddleware
        import houmao.agents.realm_controller.gateway_plugin_host as host_module
        from houmao.gateway.access import GatewayAccessError
        from houmao.gateway.operations import GatewayOperation
        from houmao.gateway.plugins import (
            GatewayPluginConfiguration,
            PluginCredentialReference,
            PluginInstanceConfiguration,
        )
        from houmao.gateway.plugins.discovery import LoadedPluginDefinition

        service = Service()
        service.m_queue_enabled = True
        if condition == "unavailable":
            service.m_failures["binding"] = implementation.ProviderError(
                "provider_unavailable", 503, True
            )
        monkeypatch.setattr(implementation.ProviderClient, "from_config", service.new_client)
        config = implementation.CcccConfiguration(
            endpoint="http://127.0.0.1:8848",
            group_id="g1",
            actor_id="a1",
            actor_generation="gen1",
            reconnect_delay_seconds=0.05,
        )
        credentials = tmp_path / "private-actor.json"
        credentials.write_text(
            json.dumps(
                {
                    "agent_id": "wrong-owner" if condition == "wrong_owner" else "owner1",
                    "endpoint": config.endpoint,
                    "group_id": "g1",
                    "actor_id": "a1",
                    "actor_generation": "gen1",
                    "token": "synthetic-grant",
                }
            )
        )
        credentials.chmod(0o600)
        project = tmp_path / "checkout"
        (project / ".git").mkdir(parents=True)
        gateway = tmp_path / "gateway"
        gateway.mkdir(mode=0o700)
        package = importlib.import_module("houmao_cccc")
        loaded = LoadedPluginDefinition(
            definition=package.definition, distribution="houmao-cccc", distribution_version="0.1.0"
        )
        monkeypatch.setattr(host_module, "load_plugin_definition", lambda _name: loaded)
        host = host_module.GatewayPluginHost.from_config(
            configuration=GatewayPluginConfiguration(
                plugins={
                    "team": PluginInstanceConfiguration(
                        implementation="cccc",
                        credential_ref=PluginCredentialReference(file=credentials),
                        config=config.model_dump(mode="json"),
                    )
                }
            ),
            owner=PluginOwner(agent_id="owner1", runtime_session_id="runtime1"),
            gateway_root=gateway,
            project_root=project,
            listener_host="127.0.0.1",
            dispatch=Mock(),
        )
        app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)

        @app.get("/health")
        async def health() -> dict[str, bool]:
            """Represent an unrelated core route behind the actual host middleware."""

            return {"ok": True}

        host.stage(app)
        allow_receipts = True

        def admit(*, operation: GatewayOperation, **_kwargs: Any) -> None:
            """Use a scoped test policy at the runtime admission boundary."""

            permission = operation.permission
            if permission is not None and permission.action == "plugin.cccc.chat.deliveries.read":
                assert permission.resource == host.instance_resource("team")
                if not allow_receipts:
                    raise GatewayAccessError(403, "insufficient_authority")
            if permission is not None and permission.action == "plugin.cccc.chat.queue.consume":
                assert permission.resource == host.instance_resource("team")
                raise GatewayAccessError(403, "insufficient_authority")

        app.add_middleware(
            GatewayAdmissionMiddleware,
            gateway=app,
            plugin_host=host,
            admit=admit,
            reserve_public_input=Mock(),
            log_denial=Mock(),
        )
        await host.start(port=12345)
        try:
            wanted = "failed" if condition == "wrong_owner" else "running"
            await eventually(lambda: host.status_for("team").lifecycle == wanted)
            if condition == "unavailable":
                await eventually(lambda: host.status_for("team").connection == "reconnecting")
            if condition == "connected":
                await eventually(lambda: host.status_for("team").connection == "connected")
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://local"
            ) as http:
                assert (await http.get("/health")).json() == {"ok": True}
                status = await http.get("/v1/plugins/team/_status")
                assert status.status_code == 200 and status.json()["lifecycle"] == wanted
                if condition == "wrong_owner":
                    assert (await http.get("/v1/plugins/team/binding")).status_code == 503
                if condition == "connected":
                    service.m_history = {"messages": [event("event1")], "has_more": False}
                    history = await http.get("/v1/plugins/team/chat/history?event_id=event1")
                    handle = history.json()["messages"][0]["handle"]
                    route = "/v1/plugins/team/chat/deliveries"
                    allow_receipts = False
                    denied = await http.get(route, params={"handle": handle})
                    assert denied.status_code == 403
                    assert all(op != "chat.deliveries" for op, _ in service.m_calls)
                    allow_receipts = True
                    receipt = await http.get(route, params={"handle": handle})
                    assert receipt.status_code == 200 and receipt.json()["event_id"] == "event1"
                    assert (await http.get(_QUEUE_ROUTE)).status_code == 200
                    denied_pop = await http.post(
                        _QUEUE_ROUTE + "/pop",
                        json={"snapshot": "existing-snapshot", "operation_id": "op-1"},
                    )
                    assert denied_pop.status_code == 403
                    assert (await http.get(_QUEUE_ROUTE + "/pops/op-1")).status_code == 403
                    assert (
                        await http.post(_QUEUE_ROUTE + "/ack", json={"receipt": "f" * 32})
                    ).status_code == 403
                    assert not any(op.startswith("chat.gateway-read") for op, _ in service.m_calls)
                assert "synthetic-grant" not in status.text
                assert str(credentials) not in status.text
        finally:
            await host.stop()
        if condition != "wrong_owner":
            stopped = host.status_for("team")
            assert stopped is not None
            assert stopped.lifecycle == "stopped"
            assert stopped.connection == "disconnected"
            assert stopped.error_code is None
            assert stopped.workers == []

    asyncio.run(exercise())
