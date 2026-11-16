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

from houmao.gateway.plugins import PluginDispatchError, PluginDispatchResult, PluginOwner


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

        self.m_calls: list[tuple[str, dict[str, Any]]] = []
        self.m_offers: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self.m_outcomes: list[dict[str, Any]] = []
        self.m_failures: dict[str, Exception] = {}
        self.m_clients: list[Client] = []
        self.m_history: dict[str, Any] = {"messages": [], "has_more": False}
        self.m_block_send: asyncio.Event | None = None
        self.m_send_started: asyncio.Event = asyncio.Event()
        self.m_binding: dict[str, Any] = {
            "protocol_version": 1,
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
            return {
                "protocol_version": 1,
                "operations": [
                    "binding",
                    "capabilities",
                    "members",
                    "lease.acquire",
                    "lease.renew",
                    "lease.release",
                    "lease.next",
                    "lease.outcome",
                    "chat.send",
                    "chat.reply",
                    "chat.retry",
                    "chat.history",
                    "chat.deliveries",
                    "mail.read",
                ],
                "limits": {
                    "max_event_bytes": 65536,
                    "max_history_limit": 100,
                    "max_response_bytes": 262144,
                    "lease_seconds": 45,
                },
            }
        if operation == "lease.acquire":
            return {"lease_id": "lease1", "lease_generation": 1, "expires_in_seconds": 45}
        if operation == "lease.next":
            try:
                offer = await asyncio.wait_for(service.m_offers.get(), timeout=0.02)
            except TimeoutError:
                offer = None
            return {"offer": offer}
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
        if operation in {"chat.retry", "chat.deliveries"}:
            return {"deliveries": [{"state": "uncertain", "actor_id": "a2"}]}
        raise AssertionError(operation)

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
    implementation: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, start: bool = True
) -> AsyncIterator[SimpleNamespace]:
    """Activate the real plugin lifespan against isolated public SDK capabilities."""

    service = Service()
    monkeypatch.setattr(implementation.ProviderClient, "from_config", service.new_client)
    config = implementation.CcccConfiguration(
        endpoint="http://127.0.0.1:8848",
        group_id="g1",
        actor_id="a1",
        actor_generation="gen1",
        poll_timeout_seconds=0.01,
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
            dispatch=AsyncMock(return_value=PluginDispatchResult(source_event_id="event1"))
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
                "expected_binding_id": "binding1",
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
            rejected = await h.http.get("/v1/plugins/team/binding?sender=other")
            assert rejected.status_code == 422

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
                    "expected_binding_id": "binding1",
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
                    "expected_binding_id": "binding1",
                    "operation_id": "reply1",
                    "event_ref": result["event"]["event_ref"],
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
                    "expected_binding_id": "another",
                    "operation_id": "send1",
                    "to": ["a2"],
                    "text": "Synthetic",
                },
            )
            foreign = await h.http.post(
                "/v1/plugins/team/chat/reply",
                json={
                    "expected_binding_id": "binding1",
                    "operation_id": "reply1",
                    "event_ref": "foreign",
                    "text": "Synthetic",
                },
            )
            assert stale.status_code == 409 and foreign.status_code == 422
            assert not any(op.startswith("chat.") for op, _ in h.service.m_calls)

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "status,outcome,expected",
    [
        (409, "not_sent", "refused"),
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
                error_code="readiness_conflict",
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
    """The real agent receives a scoped reply handle without control authority."""

    async def exercise() -> None:
        """Deliver control-looking content through the sole ordinary SDK port."""

        async with harness(implementation, monkeypatch, tmp_path) as h:
            await h.service.m_offers.put(offer(text="/compact"))
            await eventually(lambda: len(h.service.m_outcomes) == 1)
            assert h.service.m_outcomes[0]["outcome"] == "accepted"
            envelope = h.context.events.dispatch.call_args.args[0]
            assert envelope.source_event_id == "event1"
            assert "event_ref=cccc1." in envelope.text and "\n\n/compact" in envelope.text
            assert h.plugin._references().decode(envelope.metadata["event_ref"], "event") == {
                "event_id": "event1"
            }

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "overrides",
    [
        {"actor_generation": "old"},
        {"lease_generation": 2},
        {"message_mode": "mail"},
        {"remaining_seconds": 0},
        {"remaining_seconds": float("nan")},
        {"sender": "bad\nheader"},
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
            await eventually(lambda: len(h.service.m_outcomes) == 1)
            assert h.service.m_outcomes[0]["outcome"] == "failed"
            assert h.service.m_outcomes[0]["retryable"] is False
            h.context.events.dispatch.assert_not_awaited()

    asyncio.run(exercise())


def test_offer_deadline_cancels_sdk_dispatch(
    implementation: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Cancellation reaches the SDK's request fence before a late body handoff."""

    async def exercise() -> None:
        """Use a pending dispatcher to observe deadline cancellation."""

        cancelled = asyncio.Event()

        async def pending(_event: Any) -> Any:
            """Represent a handoff that cannot confirm before expiry."""

            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        async with harness(implementation, monkeypatch, tmp_path) as h:
            h.context.events.dispatch.side_effect = pending
            await h.service.m_offers.put(offer(remaining_seconds=0.02))
            await eventually(lambda: len(h.service.m_outcomes) == 1)
            assert cancelled.is_set()
            assert h.service.m_outcomes[0]["outcome"] == "uncertain"

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
                        "expected_binding_id": "binding1",
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
            assert all(not args for op, args in h.service.m_calls if op == "lease.acquire")
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

        async def pending(_event: Any) -> Any:
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
                    "expected_binding_id": "binding1",
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
                    "expected_binding_id": "binding1",
                    "operation_id": "send1",
                    "to": ["a2"],
                    "text": "Synthetic",
                },
            )
            assert result.status_code == 503
            assert result.json()["detail"]["dispatch_outcome"] == "unknown"
            assert result.json()["detail"]["operation_id"] == "send1"

    asyncio.run(exercise())


@pytest.mark.parametrize("unavailable", [True, False])
def test_real_host_keeps_core_health_during_cccc_startup_failure(
    implementation: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unavailable: bool
) -> None:
    """Mount the actual CCCC definition in the real host and preserve unrelated routes."""

    async def exercise() -> None:
        """Use actual host discovery, credential checks, lifecycle, and route guards."""

        import houmao.agents.realm_controller.gateway_plugin_host as host_module
        from houmao.gateway.plugins import (
            GatewayPluginConfiguration,
            PluginCredentialReference,
            PluginInstanceConfiguration,
        )
        from houmao.gateway.plugins.discovery import LoadedPluginDefinition

        service = Service()
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
                    "agent_id": "owner1" if unavailable else "wrong-owner",
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
        app = FastAPI()

        @app.get("/health")
        async def health() -> dict[str, bool]:
            """Represent an unrelated core route behind the actual host middleware."""

            return {"ok": True}

        host.stage(app)
        await host.start(port=12345)
        try:
            wanted = "running" if unavailable else "failed"
            await eventually(lambda: host.status_for("team").lifecycle == wanted)
            if unavailable:
                await eventually(lambda: host.status_for("team").connection == "reconnecting")
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://local"
            ) as http:
                assert (await http.get("/health")).json() == {"ok": True}
                status = await http.get("/v1/plugins/team/_status")
                assert status.status_code == 200 and status.json()["lifecycle"] == wanted
                if not unavailable:
                    assert (await http.get("/v1/plugins/team/binding")).status_code == 503
                assert "synthetic-grant" not in status.text
                assert str(credentials) not in status.text
        finally:
            await host.stop()
        if unavailable:
            stopped = host.status_for("team")
            assert stopped is not None
            assert stopped.lifecycle == "stopped"
            assert stopped.connection == "disconnected"
            assert stopped.error_code is None
            assert stopped.workers == []

    asyncio.run(exercise())
