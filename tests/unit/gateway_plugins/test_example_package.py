"""Exercise the standalone example's HTTP and resource contracts."""

from __future__ import annotations

import asyncio
import importlib
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from houmao.gateway.plugins import (
    PluginContext,
    PluginDispatchError,
    PluginDispatchResult,
    PluginOwner,
)


@pytest.fixture
def example(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """Load the independent source only for focused example contract tests."""

    source = Path(__file__).resolve().parents[3] / "examples/gateway-plugin/src"
    monkeypatch.syspath_prepend(str(source))
    return importlib.import_module("houmao_example_plugin")


def _context(tmp_path: Path) -> SimpleNamespace:
    """Create observable narrow SDK capabilities without gateway internals."""

    return SimpleNamespace(
        owner=PluginOwner(agent_id="owner-1", runtime_session_id="session-1"),
        instance_id="notifications",
        binding_id="opaque-owner-account",
        listener=None,
        events=SimpleNamespace(
            dispatch=AsyncMock(return_value=PluginDispatchResult(source_event_id="event-1"))
        ),
        workers=SimpleNamespace(start_soon=Mock()),
        credentials=SimpleNamespace(read=Mock(return_value={"account": "team"})),
        state=SimpleNamespace(path=lambda relative: tmp_path / relative),
        report_connection=Mock(),
        log=Mock(),
    )


def _plugin(example: ModuleType, context: SimpleNamespace, **settings: Any) -> Any:
    """Construct a resource-free plugin from its advertised public definition."""

    definition = example.definition
    config = definition.config_model(account="team", **settings)
    return definition.create(cast(PluginContext, context), config)


def _client(plugin: Any) -> TestClient:
    """Expose the example router without internal host dependencies."""

    app = FastAPI()
    app.include_router(plugin.router, prefix="/v1/plugins/notifications")
    return TestClient(app)


def test_example_stages_resources_then_starts_no_auth_worker(
    example: ModuleType, tmp_path: Path
) -> None:
    """Keep construction inert and omit credential reads in no-auth mode."""

    context = _context(tmp_path)
    plugin = _plugin(example, context)
    context.credentials.read.assert_not_called()
    context.workers.start_soon.assert_not_called()

    async def activate() -> None:
        """Exercise the actual asynchronous resource boundary."""

        async with plugin.lifespan():
            context.report_connection.assert_called_once_with("connected")
            context.workers.start_soon.assert_called_once()
            assert context.workers.start_soon.call_args.args[0] == "heartbeat"
            context.credentials.read.assert_not_called()

    asyncio.run(activate())
    response = _client(plugin).post("/v1/plugins/notifications/refresh-credentials", json={})
    assert response.json() == {"refreshed": False}
    context.credentials.read.assert_not_called()


def test_example_success_advances_only_source_cursor(example: ModuleType, tmp_path: Path) -> None:
    """Confirm dispatch before writing a non-message cursor."""

    context = _context(tmp_path)
    plugin = _plugin(example, context)
    response = _client(plugin).post(
        "/v1/plugins/notifications/notify",
        json={"source_event_id": "event-1", "text": "Synthetic body", "metadata": {}},
    )
    assert response.status_code == 200
    assert response.json() == {"disposition": "dispatched", "source_event_id": "event-1"}
    context.events.dispatch.assert_awaited_once()
    assert (tmp_path / "last-dispatched-id.txt").read_text() == "event-1\n"
    assert [path.name for path in tmp_path.iterdir()] == ["last-dispatched-id.txt"]


@pytest.mark.parametrize("status_code", (409, 503, 422))
def test_example_propagates_typed_failure_without_cursor(
    example: ModuleType, tmp_path: Path, status_code: int
) -> None:
    """Let the sender observe a failed handoff and retain its event."""

    context = _context(tmp_path)
    error = PluginDispatchError(
        error_code="fixture_failure",
        status_code=status_code,
        retryable=status_code != 422,
        source_event_id="event-1",
    )
    context.events.dispatch.side_effect = error
    response = _client(_plugin(example, context)).post(
        "/v1/plugins/notifications/notify", json={"source_event_id": "event-1", "text": "Synthetic"}
    )
    assert response.status_code == status_code
    assert response.json() == {"detail": error.to_detail()}
    assert list(tmp_path.iterdir()) == []


def test_example_owner_and_refresh_reject_caller_overrides(
    example: ModuleType, tmp_path: Path
) -> None:
    """Fix owner/account identity and deny alternate credential sources."""

    context = _context(tmp_path)
    client = _client(_plugin(example, context, require_credentials=True))
    owner = client.get("/v1/plugins/notifications/owner").json()
    assert owner["agent_id"] == "owner-1"
    assert owner["account"] == "team"
    assert (
        client.post(
            "/v1/plugins/notifications/refresh-credentials", json={"file": "/another/file"}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/v1/plugins/notifications/notify",
            json={"source_event_id": "event-1", "text": "Synthetic", "agent_id": "another-owner"},
        ).status_code
        == 422
    )
    context.credentials.read.assert_not_called()
    assert client.post("/v1/plugins/notifications/refresh-credentials", json={}).status_code == 200
    context.credentials.read.assert_called_once()


def test_example_credentials_must_match_configured_account(
    example: ModuleType, tmp_path: Path
) -> None:
    """Refuse another account before starting any worker."""

    context = _context(tmp_path)
    context.credentials.read.return_value = {"account": "someone-else", "token": "private-value"}
    plugin = _plugin(example, context, require_credentials=True)

    async def activate() -> None:
        """Attempt credential-backed startup."""

        async with plugin.lifespan():
            pytest.fail("Mismatched account activated")

    with pytest.raises(ValueError, match="Selected credentials do not match") as error:
        asyncio.run(activate())
    assert "private-value" not in str(error.value)
    context.workers.start_soon.assert_not_called()


@pytest.mark.parametrize(
    "override",
    [
        {"implementation": "fixture-startup-failure"},
        {"install": {"distribution": "another-package"}},
        {"packages": ["another-package"]},
        {"config": {"account": "another-account"}},
    ],
)
def test_example_route_callers_cannot_replace_implementation_or_install_packages(
    example: ModuleType, tmp_path: Path, override: dict[str, Any]
) -> None:
    """Reject operator-only changes before service access or event dispatch."""

    context = _context(tmp_path)
    client = _client(_plugin(example, context, require_credentials=True))
    event = {"source_event_id": "event-1", "text": "Synthetic", **override}
    assert client.post("/v1/plugins/notifications/notify", json=event).status_code == 422
    assert (
        client.post("/v1/plugins/notifications/refresh-credentials", json=override).status_code
        == 422
    )
    context.events.dispatch.assert_not_awaited()
    context.credentials.read.assert_not_called()
    context.workers.start_soon.assert_not_called()
    assert list(tmp_path.iterdir()) == []
