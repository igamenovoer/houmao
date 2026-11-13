"""Exercise plugin lifespans, scoped authority, and immediate request fencing."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
import json
from pathlib import Path
import threading
from typing import cast

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.testclient import TestClient
import httpx
from pydantic import BaseModel, ConfigDict
import pytest

import houmao.agents.realm_controller.gateway_plugin_host as host_module
from houmao.agents.realm_controller.gateway_plugin_host import (
    GatewayPluginHost,
    PluginDispatchCallback,
)
from houmao.gateway.plugins import (
    GatewayPluginConfiguration,
    PluginContext,
    PluginCredentialReference,
    PluginDefinition,
    PluginDispatchError,
    PluginDispatchResult,
    PluginEvent,
    PluginInstanceConfiguration,
    PluginOwner,
)
from houmao.gateway.plugins.discovery import LoadedPluginDefinition


class _Settings(BaseModel):
    """Pure service settings used by an otherwise external-style plugin."""

    model_config = ConfigDict(extra="forbid", strict=True)
    account: str = "service-one"
    fail_start: bool = False
    hold_start: bool = False
    worker: str = "none"
    values: dict[str, int] = {}


class _FixturePlugin:
    """Use public context ports while exposing observations only to the test."""

    def __init__(self, context: PluginContext, settings: _Settings) -> None:
        """Construct ordinary routes without opening any resources."""

        self.m_context: PluginContext = context
        self.m_settings: _Settings = settings
        self.m_router: APIRouter = APIRouter()
        self.m_opened: bool = False
        self.m_closed: bool = False
        self.m_worker_closed: bool = False

        @self.m_router.get("/connection")
        async def connection() -> dict[str, str]:
            """Serve an ordinary resource-free custom route."""

            return {"instance": context.instance_id}

        @self.m_router.post("/events")
        async def event(payload: PluginEvent) -> PluginDispatchResult:
            """Forward the sender-owned request to the immediate dispatch port."""

            return await context.events.dispatch(payload)

    @property
    def router(self) -> APIRouter:
        """Return declarations for the host to stage."""

        return self.m_router

    @asynccontextmanager
    async def lifespan(self) -> AsyncIterator[None]:
        """Acquire resources and always release partially acquired resources."""

        self.m_opened = True
        try:
            if self.m_settings.hold_start:
                await asyncio.Event().wait()
            if self.m_settings.fail_start:
                raise RuntimeError("private-provider-secret")
            self.m_context.report_connection("connected")
            if self.m_settings.worker != "none":
                self.m_context.workers.start_soon("listener", self._worker)
            yield
        finally:
            self.m_closed = True

    async def _worker(self) -> None:
        """Run one cooperative listener or intentionally fail its owner."""

        try:
            if self.m_settings.worker == "return":
                return
            if self.m_settings.worker == "raise":
                raise RuntimeError("private-worker-secret")
            if self.m_settings.worker == "cancel":
                raise asyncio.CancelledError
            await asyncio.Event().wait()
        finally:
            self.m_worker_closed = True


def _selection(**config: object) -> PluginInstanceConfiguration:
    """Build validated selected plugin settings without implicit credentials."""

    return PluginInstanceConfiguration.model_validate(
        {"implementation": "fixture", "config": config}
    )


def _confirmed(
    event: PluginEvent,
    *,
    instance_id: str,
    binding_id: str,
    timeout_seconds: float,
    is_active: Callable[[], bool],
) -> PluginDispatchResult:
    """Simulate the parent runtime's confirmed semantic input handoff."""

    assert instance_id and binding_id and timeout_seconds > 0 and is_active()
    return PluginDispatchResult(source_event_id=event.source_event_id)


def _make_host(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    selections: dict[str, PluginInstanceConfiguration] | None = None,
    dispatch: PluginDispatchCallback = _confirmed,
    listener_host: str = "127.0.0.1",
    owner_id: str = "agent-one",
    binding: Callable[[_Settings], str] | None = None,
    prepare: Callable[[_FixturePlugin], None] | None = None,
    bounds: dict[str, float | int] | None = None,
) -> tuple[GatewayPluginHost, FastAPI, dict[str, _FixturePlugin]]:
    """Assemble a host with selected-only fake entry-point discovery."""

    gateway_root = tmp_path / "gateway"
    gateway_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    project_root = tmp_path / "checkout"
    project_root.mkdir(exist_ok=True)
    (project_root / ".git").mkdir(exist_ok=True)
    plugins: dict[str, _FixturePlugin] = {}

    def create(context: PluginContext, settings: _Settings) -> _FixturePlugin:
        """Keep a test observation reference without adding host hooks."""

        plugin = _FixturePlugin(context, settings)
        if prepare is not None:
            prepare(plugin)
        plugins[context.instance_id] = plugin
        return plugin

    definition = PluginDefinition(
        config_model=_Settings,
        binding_identity=binding or (lambda settings: settings.account),
        create=create,
    )
    loaded = LoadedPluginDefinition(
        definition=cast(PluginDefinition[BaseModel], definition),
        distribution="external-fixture",
        distribution_version="1.0",
    )
    monkeypatch.setattr(host_module, "load_plugin_definition", lambda _name: loaded)
    configuration = GatewayPluginConfiguration.model_validate(
        {
            "plugins": selections if selections is not None else {"one": _selection()},
            "startup_timeout_seconds": 0.1,
            "shutdown_timeout_seconds": 0.1,
            "dispatch_timeout_seconds": 0.1,
            **(bounds or {}),
        }
    )
    host = GatewayPluginHost.from_config(
        configuration=configuration,
        owner=PluginOwner(agent_id=owner_id, runtime_session_id="session-one"),
        gateway_root=gateway_root,
        project_root=project_root,
        listener_host=listener_host,
        dispatch=dispatch,
    )
    app = FastAPI()

    @app.get("/health")
    def health() -> dict[str, bool]:
        """Represent core functionality independent of a plugin."""

        return {"ok": True}

    return host, app, plugins


async def _wait_state(host: GatewayPluginHost, instance_id: str, state: str) -> None:
    """Yield until a cooperative supervisor publishes the expected snapshot."""

    async with asyncio.timeout(2.0):
        while (current := host.status_for(instance_id)) is None or current.lifecycle != state:
            await asyncio.sleep(0.001)


def test_nonloopback_is_disabled_before_implementation_loading(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An exposed listener retains safe status but imports no selected code."""

    host, app, plugins = _make_host(tmp_path, monkeypatch, listener_host="0.0.0.0")

    def forbidden(_name: str) -> LoadedPluginDefinition:
        """Fail the test if staging attempts an implementation import."""

        raise AssertionError("implementation loaded")

    monkeypatch.setattr(host_module, "load_plugin_definition", forbidden)
    host.stage(app)
    with TestClient(app) as client:
        assert client.get("/health").json() == {"ok": True}
        assert client.get("/v1/plugins/unknown/_status").status_code == 404
        status = client.get("/v1/plugins/one/_status").json()
        assert status["lifecycle"] == "disabled_by_listener_policy"
        assert client.get("/v1/plugins/one/connection").status_code == 503
        assert client.get("/v1/plugins").json()["configuration_digest"] == host.config_digest
    assert not plugins


def test_staging_is_resource_free_and_binding_identity_is_validated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Factories have inactive context ports and unstable bindings fail safely."""

    host, app, plugins = _make_host(tmp_path, monkeypatch)
    host.stage(app)
    context = plugins["one"].m_context
    assert not plugins["one"].m_opened
    assert context.listener is None
    with pytest.raises(PluginDispatchError, match="credentials"):
        context.credentials.read()
    with pytest.raises(RuntimeError):
        context.workers.start_soon("premature", lambda: asyncio.sleep(0))
    assert not context.state.path("cursor.json").parent.exists()

    counter = iter(["first", "second"])
    unstable, other_app, _ = _make_host(
        tmp_path / "unstable", monkeypatch, binding=lambda _settings: next(counter)
    )
    unstable.stage(other_app)
    assert unstable.status()[0].error_code == "invalid_binding_identity"


def test_validation_failures_exclude_configuration_values_and_preserve_healthy_instance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Dynamic mapping keys and provider exceptions never become diagnostics."""

    host, app, _ = _make_host(
        tmp_path,
        monkeypatch,
        selections={
            "one": _selection(values={"private-secret-key": "bad"}),
            "healthy": _selection(),
        },
    )
    host.stage(app)
    serialized = host.status_for("one").model_dump_json()
    assert "private-secret-key" not in serialized
    assert "bad" not in serialized
    assert "values.*" in serialized
    assert "invalid_plugin_configuration" in serialized

    async def exercise() -> None:
        """Activate a valid peer while the invalid instance remains inactive."""

        await host.start()
        await _wait_state(host, "healthy", "running")
        assert host.status_for("one").lifecycle == "failed"
        await host.stop()

    asyncio.run(exercise())


def test_factory_exception_is_sanitized_before_activation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An author factory error cannot expose its private input or acquire resources."""

    def fail_factory(_plugin: _FixturePlugin) -> None:
        """Simulate an implementation constructing its router unsuccessfully."""

        raise RuntimeError("private-factory-secret")

    host, app, _plugins = _make_host(tmp_path, monkeypatch, prepare=fail_factory)
    host.stage(app)
    assert host.status()[0].error_code == "plugin_factory_failed"
    assert "private-factory-secret" not in host.status()[0].model_dump_json()


def test_http_handler_exception_is_sanitized_without_failing_core(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """A provider exception cannot reach the server's default traceback logger."""

    def prepare(plugin: _FixturePlugin) -> None:
        """Add an intentionally unhandled provider-style operation failure."""

        @plugin.router.post("/failing-operation")
        async def failure() -> None:
            """Model a provider exception that includes private material."""

            raise RuntimeError("private-handler-secret")

        @plugin.router.post("/expected-conflict")
        async def expected_conflict() -> None:
            """Keep an ordinary documented plugin HTTP refusal authoritative."""

            raise HTTPException(
                status_code=409, detail="Expected service conflict", headers={"X-Fixture": "public"}
            )

    host, app, _plugins = _make_host(tmp_path, monkeypatch, prepare=prepare)
    host.stage(app)

    async def exercise() -> None:
        """Obtain an explicit safe failure while keeping independent core healthy."""

        await host.start()
        await _wait_state(host, "one", "running")
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://localhost"
        ) as client:
            response = await client.post("/v1/plugins/one/failing-operation")
            assert response.status_code == 503
            assert response.json()["detail"]["error_code"] == "plugin_request_failed"
            assert response.json()["detail"]["dispatch_outcome"] == "unknown"
            assert "private-handler-secret" not in response.text
            conflict = await client.post("/v1/plugins/one/expected-conflict")
            assert conflict.status_code == 409
            assert conflict.json() == {"detail": "Expected service conflict"}
            assert conflict.headers["X-Fixture"] == "public"
            assert (await client.get("/health")).status_code == 200
            assert (await client.get("/v1/plugins/one/_status")).status_code == 200
        await host.stop()

    asyncio.run(exercise())
    assert "private-handler-secret" not in caplog.text


def test_route_conflicts_are_staged_before_any_instance_resources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Disable complete conflicting instances while mounting healthy routes."""

    def prepare(plugin: _FixturePlugin) -> None:
        """Create an equivalent-parameter conflict inside one selected router."""

        if plugin.m_context.instance_id == "broken":
            plugin.router.add_api_route("/messages/{id}", lambda: None, methods=["GET"])
            plugin.router.add_api_route("/messages/{name}", lambda: None, methods=["GET"])

    host, app, plugins = _make_host(
        tmp_path,
        monkeypatch,
        selections={"healthy": _selection(), "broken": _selection()},
        prepare=prepare,
    )
    host.stage(app)
    broken = host.status_for("broken")
    assert broken is not None and broken.error_code == "route_conflict"
    assert len(broken.conflicts) == 2
    assert not plugins["broken"].m_opened

    async def exercise() -> None:
        """Start only the survivor and check host-owned failure visibility."""

        await host.start()
        await _wait_state(host, "healthy", "running")
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://localhost"
        ) as client:
            assert (await client.get("/v1/plugins/broken/messages/value")).status_code == 503
            assert (await client.get("/v1/plugins/broken/_status")).status_code == 200
            assert (await client.get("/v1/plugins/healthy/connection")).status_code == 200
        await host.stop()

    asyncio.run(exercise())
    assert not plugins["broken"].m_opened


def test_core_collision_disables_every_participant_in_any_configuration_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Inventory the core and full candidate set before selecting survivors."""

    snapshots: list[dict[str, list[dict[str, str]]]] = []

    def prepare(plugin: _FixturePlugin) -> None:
        """Declare the same relative endpoint in independently prefixed routers."""

        plugin.router.add_api_route("/cross/value", lambda: None, methods=["GET"])

    for index, names in enumerate((["one", "two"], ["two", "one"])):
        host, app, plugins = _make_host(
            tmp_path / str(index),
            monkeypatch,
            selections={name: _selection() for name in names},
            prepare=prepare,
        )
        app.add_api_route("/v1/plugins/{plugin_id}/cross/{id}", lambda: None, methods=["GET"])
        host.stage(app)
        snapshots.append({item.instance_id: item.conflicts for item in host.status()})
        assert all(item.lifecycle == "failed" for item in host.status())
        assert not any(plugin.m_opened for plugin in plugins.values())
        assert all(item.conflicts[0]["counterpart_instance"] == "core" for item in host.status())
    assert snapshots[0] == snapshots[1]


def test_cleanup_timeout_is_bounded_and_safe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A cooperative cleanup deadline does not hold the rest of the host open."""

    host, app, plugins = _make_host(
        tmp_path, monkeypatch, bounds={"shutdown_timeout_seconds": 0.01}
    )
    host.stage(app)

    @asynccontextmanager
    async def slow_cleanup() -> AsyncIterator[None]:
        """Exercise timeout during a plugin's cooperative exit path."""

        try:
            yield
        finally:
            await asyncio.sleep(5.0)

    monkeypatch.setattr(plugins["one"], "lifespan", slow_cleanup)

    async def exercise() -> None:
        """Stop a running instance and observe a finite failure snapshot."""

        await host.start()
        await _wait_state(host, "one", "running")
        async with asyncio.timeout(0.5):
            await host.stop()
        assert host.status_for("one").error_code == "cleanup_timeout"

    asyncio.run(exercise())


def test_stop_before_scheduled_start_is_idempotent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cancel an activation task before its first scheduling without stale state."""

    host, app, plugins = _make_host(tmp_path, monkeypatch)
    host.stage(app)

    async def exercise() -> None:
        """Do not yield between scheduling activation and initiating shutdown."""

        await host.start()
        await host.stop()
        await host.stop()
        assert host.status_for("one").lifecycle == "stopped"

    asyncio.run(exercise())
    assert not plugins["one"].m_opened


def test_lifespans_are_independent_and_cleanup_partial_startup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One failed or slow service leaves healthy routes and core operational."""

    host, app, plugins = _make_host(
        tmp_path,
        monkeypatch,
        selections={
            "healthy": _selection(worker="wait"),
            "broken": _selection(fail_start=True),
            "slow": _selection(hold_start=True),
        },
        bounds={"startup_timeout_seconds": 0.03},
    )
    host.stage(app)

    async def exercise() -> None:
        """Use the same async loop for host resources and ASGI requests."""

        await host.start(port=12345)
        await host.start(port=12345)
        await _wait_state(host, "healthy", "running")
        await _wait_state(host, "broken", "failed")
        await _wait_state(host, "slow", "failed")
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://localhost"
        ) as client:
            assert (await client.get("/health")).status_code == 200
            assert (await client.get("/v1/plugins/healthy/connection")).status_code == 200
            assert (await client.get("/v1/plugins/broken/connection")).status_code == 503
            assert (await client.get("/v1/plugins/broken/_status")).status_code == 200
        listener = plugins["healthy"].m_context.listener
        assert listener is not None and listener.base_url == "http://127.0.0.1:12345"
        await host.stop()
        await host.stop()

    asyncio.run(exercise())
    assert plugins["broken"].m_closed and plugins["slow"].m_closed
    assert plugins["healthy"].m_closed and plugins["healthy"].m_worker_closed
    assert host.status_for("slow").error_code == "startup_timeout"
    snapshot = (tmp_path / "gateway/plugins/status.json").read_text()
    assert "private-provider-secret" not in snapshot
    assert "private-worker-secret" not in snapshot
    assert host.status_for("healthy").lifecycle == "stopped"


@pytest.mark.parametrize("worker", ["return", "raise", "cancel"])
def test_worker_failure_is_scoped_to_its_instance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, worker: str
) -> None:
    """Both unexpected return and exception close only their owning lifespan."""

    host, app, plugins = _make_host(
        tmp_path,
        monkeypatch,
        selections={"healthy": _selection(), "broken": _selection(worker=worker)},
    )
    host.stage(app)

    async def exercise() -> None:
        """Wait for the isolated worker exception and healthy activation."""

        await host.start()
        await _wait_state(host, "healthy", "running")
        await _wait_state(host, "broken", "failed")
        await asyncio.sleep(0)
        assert host.status_for("broken").worker_failures == ["listener"]
        assert host.status_for("healthy").lifecycle == "running"
        await host.stop()

    asyncio.run(exercise())
    assert plugins["broken"].m_closed


def test_credentials_are_selected_private_rotatable_and_lifespan_scoped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Read the explicit source afresh and retain no authority after shutdown."""

    credential = tmp_path / "private.json"
    credential.write_text('{"key":"first-synthetic-value"}')
    credential.chmod(0o600)
    selected = _selection().model_copy(
        update={"credential_ref": PluginCredentialReference(file=credential)}
    )
    host, app, plugins = _make_host(tmp_path, monkeypatch, selections={"one": selected})
    host.stage(app)
    context = plugins["one"].m_context

    async def exercise() -> None:
        """Verify rotation and reject world-readable replacements immediately."""

        await host.start()
        await _wait_state(host, "one", "running")
        assert context.credentials.read() == {"key": "first-synthetic-value"}
        credential.write_text('{"key":"rotated-synthetic-value"}')
        assert context.credentials.read() == {"key": "rotated-synthetic-value"}
        actual_uid = host_module.os.getuid()
        with monkeypatch.context() as owner_patch:
            owner_patch.setattr(host_module.os, "getuid", lambda: actual_uid + 1)
            with pytest.raises(PluginDispatchError):
                context.credentials.read()
        credential.chmod(0o644)
        with pytest.raises(PluginDispatchError):
            context.credentials.read()
        await host.stop()

    asyncio.run(exercise())
    with pytest.raises(PluginDispatchError):
        context.credentials.read()
    snapshot = (tmp_path / "gateway/plugins/status.json").read_text()
    assert str(credential) not in snapshot and "synthetic-value" not in snapshot


@pytest.mark.parametrize("source", ["missing", "checkout", "symlink", "no-reference"])
def test_credentials_reject_unsafe_sources_and_never_use_ambient_auth(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, source: str
) -> None:
    """Missing or unsafe explicit sources cannot select another credential."""

    monkeypatch.setenv("API_KEY", "ambient-synthetic-secret")
    path = tmp_path / "credentials.json"
    selected = _selection()
    if source == "checkout":
        path = tmp_path / "checkout" / "credentials.json"
        path.parent.mkdir()
    if source in {"checkout", "symlink"}:
        path.write_text('{"key":"synthetic-secret"}')
        path.chmod(0o600)
    if source == "symlink":
        linked = tmp_path / "linked.json"
        linked.symlink_to(path)
        path = linked
    if source != "no-reference":
        selected = selected.model_copy(
            update={"credential_ref": PluginCredentialReference(file=path)}
        )
    host, app, plugins = _make_host(tmp_path, monkeypatch, selections={"one": selected})
    host.stage(app)

    async def exercise() -> None:
        """Activate only the selected credential reader, without fallback."""

        await host.start()
        await _wait_state(host, "one", "running")
        with pytest.raises(PluginDispatchError) as raised:
            plugins["one"].m_context.credentials.read()
        assert raised.value.error_code == "credential_unavailable"
        assert str(path) not in str(raised.value)
        await host.stop()

    asyncio.run(exercise())


def test_state_identity_and_paths_are_bound_to_account_and_owner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Account or owner replacement creates another scope; operational settings do not."""

    hosts: list[GatewayPluginHost] = []
    scopes: list[Path] = []
    for index, (owner, account, worker) in enumerate(
        [("a", "x", "none"), ("a", "x", "wait"), ("a", "y", "none"), ("b", "x", "none")]
    ):
        host, app, plugins = _make_host(
            tmp_path / str(index),
            monkeypatch,
            selections={"one": _selection(account=account, worker=worker)},
            owner_id=owner,
        )
        host.stage(app)
        hosts.append(host)
        scopes.append(plugins["one"].m_context.state.path("cursor.json"))
    assert hosts[0].status()[0].binding_id == hosts[1].status()[0].binding_id
    assert len({host.status()[0].binding_id for host in hosts}) == 3
    state = plugins["one"].m_context.state
    for bad in ("../escape", "/absolute", "nested/../../escape", "bad\\path"):
        with pytest.raises(ValueError):
            state.path(bad)
    scopes[-1].parent.mkdir(mode=0o700, parents=True)
    scopes[-1].symlink_to(tmp_path / "outside.json")
    with pytest.raises(ValueError):
        state.path("cursor.json")
    scopes[-1].unlink()
    bindings = scopes[-1].parent.parent
    displaced_bindings = tmp_path / "outside-bindings"
    bindings.rename(displaced_bindings)
    bindings.symlink_to(displaced_bindings, target_is_directory=True)
    with pytest.raises(ValueError):
        state.path("cursor.json")


def test_recreated_host_preserves_cursor_and_never_replays_payloads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A fresh host reuses only the same account's private successful-event cursor."""

    dispatched: list[str] = []

    def record(
        event: PluginEvent,
        *,
        instance_id: str,
        binding_id: str,
        timeout_seconds: float,
        is_active: Callable[[], bool],
    ) -> PluginDispatchResult:
        """Observe every actual runtime dispatch, including any unexpected replay."""

        dispatched.append(event.source_event_id)
        return _confirmed(
            event,
            instance_id=instance_id,
            binding_id=binding_id,
            timeout_seconds=timeout_seconds,
            is_active=is_active,
        )

    first, first_app, first_plugins = _make_host(tmp_path, monkeypatch, dispatch=record)
    first.stage(first_app)
    first_context = first_plugins["one"].m_context

    async def exercise() -> None:
        """Tear down all live objects and construct a new configured host."""

        await first.start()
        await _wait_state(first, "one", "running")
        await first_context.events.dispatch(
            PluginEvent(source_event_id="last-success", text="text")
        )
        cursor = first_context.state.path("last-success.txt")
        cursor.write_text("last-success\n", encoding="utf-8")
        await first.stop()
        replacement, replacement_app, replacement_plugins = _make_host(
            tmp_path, monkeypatch, dispatch=record
        )
        replacement.stage(replacement_app)
        await replacement.start()
        await _wait_state(replacement, "one", "running")
        context = replacement_plugins["one"].m_context
        assert context.binding_id == first_context.binding_id
        assert context.state.path("last-success.txt") == cursor
        assert context.state.path("last-success.txt").read_text() == "last-success\n"
        await asyncio.sleep(0)
        assert dispatched == ["last-success"]
        with pytest.raises(PluginDispatchError):
            await first_context.events.dispatch(PluginEvent(source_event_id="old", text="text"))
        await replacement.stop()

    asyncio.run(exercise())


def test_connection_reports_are_snapshots_independent_of_core_health(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Disconnect, bounded retry progress, and recovery never invoke a health callback."""

    host, app, plugins = _make_host(tmp_path, monkeypatch)
    host.stage(app)
    context = plugins["one"].m_context

    async def exercise() -> None:
        """Read HTTP snapshots while a plugin reports only local connection facts."""

        await host.start()
        await _wait_state(host, "one", "running")
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://localhost"
        ) as client:
            for state, retry_at in (
                ("disconnected", None),
                ("reconnecting", "2026-11-13T12:00:00Z"),
                ("degraded", None),
                ("connected", None),
            ):
                context.report_connection(state, retry_at=retry_at)
                response = await client.get("/v1/plugins/one/_status")
                status = response.json()
                assert response.status_code == 200
                assert status["connection"] == state and status["retry_at"] == retry_at
                assert status["lifecycle"] == "running"
                assert (await client.get("/health")).json() == {"ok": True}
                snapshot = json.loads((tmp_path / "gateway/plugins/status.json").read_text())
                assert snapshot["plugins"][0]["connection"] == state
        await host.stop()
        assert host.status()[0].connection == "disconnected"
        with pytest.raises(RuntimeError):
            context.report_connection("connected")

    asyncio.run(exercise())


@pytest.mark.parametrize("finish", ["timeout", "cancel", "shutdown"])
def test_request_revocation_fences_late_thread_dispatch_without_replay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, finish: str
) -> None:
    """A surviving callback cannot dispatch after its request loses authority."""

    entered = threading.Event()
    release = threading.Event()
    callbacks: list[Callable[[], bool]] = []
    delivered: list[str] = []

    def delayed(
        event: PluginEvent,
        *,
        instance_id: str,
        binding_id: str,
        timeout_seconds: float,
        is_active: Callable[[], bool],
    ) -> PluginDispatchResult:
        """Wait until the original request has timed out, canceled, or stopped."""

        callbacks.append(is_active)
        entered.set()
        assert release.wait(2.0)
        if is_active():
            delivered.append(event.text)
        return PluginDispatchResult(source_event_id=event.source_event_id)

    host, app, plugins = _make_host(
        tmp_path,
        monkeypatch,
        dispatch=delayed,
        bounds={"dispatch_timeout_seconds": 0.03 if finish == "timeout" else 1.0},
    )
    host.stage(app)

    async def exercise() -> None:
        """Keep the uncooperative thread alive beyond revocation, then release it."""

        await host.start()
        await _wait_state(host, "one", "running")
        task = asyncio.create_task(
            plugins["one"].m_context.events.dispatch(
                PluginEvent(source_event_id="event-one", text="request-private-body")
            )
        )
        async with asyncio.timeout(1.0):
            while not entered.is_set():
                await asyncio.sleep(0.001)
        assert host.status()[0].active_requests == 1
        assert callbacks[0]()
        if finish == "cancel":
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        else:
            if finish == "shutdown":
                await host.stop()
            with pytest.raises(PluginDispatchError) as raised:
                await task
            assert raised.value.status_code == 503
            assert raised.value.dispatch_outcome == "unknown"
        assert not callbacks[0]()
        release.set()
        await host.stop()
        assert host.status()[0].active_requests == 0

    try:
        asyncio.run(exercise())
    finally:
        release.set()
    assert not delivered
    files = [path for path in (tmp_path / "gateway").rglob("*") if path.is_file()]
    assert files == [tmp_path / "gateway/plugins/status.json"]
    assert "request-private-body" not in files[0].read_text()


def test_confirmed_event_returns_only_after_callback_and_validates_size(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Successful dispatch is correlated and oversized requests never reach runtime."""

    calls: list[str] = []

    def confirmed(
        event: PluginEvent,
        *,
        instance_id: str,
        binding_id: str,
        timeout_seconds: float,
        is_active: Callable[[], bool],
    ) -> PluginDispatchResult:
        """Return confirmed dispatch while the original request remains active."""

        assert is_active()
        calls.append(event.source_event_id)
        return PluginDispatchResult(source_event_id=event.source_event_id)

    host, app, plugins = _make_host(
        tmp_path, monkeypatch, dispatch=confirmed, bounds={"max_event_bytes": 512}
    )
    host.stage(app)

    async def exercise() -> None:
        """Exercise the public ASGI route and equivalent SDK errors."""

        await host.start()
        await _wait_state(host, "one", "running")
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://localhost"
        ) as client:
            response = await client.post(
                "/v1/plugins/one/events", json={"source_event_id": "first", "text": "/new"}
            )
            assert response.status_code == 200
            assert response.json() == {"disposition": "dispatched", "source_event_id": "first"}
            refused = await client.post(
                "/v1/plugins/one/events", json={"source_event_id": "large", "text": "x" * 1024}
            )
            assert refused.status_code == 422
            assert refused.json()["detail"]["retryable"] is False
        await host.stop()

    asyncio.run(exercise())
    assert calls == ["first"]
    assert plugins["one"].m_closed
    assert (
        json.loads((tmp_path / "gateway/plugins/status.json").read_text())["plugins"][0][
            "active_requests"
        ]
        == 0
    )
