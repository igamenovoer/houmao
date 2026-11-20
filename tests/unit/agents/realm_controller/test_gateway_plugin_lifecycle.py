"""Verify one plugin lifecycle for embedded and post-bind gateway hosting."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import cast

from fastapi import APIRouter
from fastapi.testclient import TestClient
from tests.fixtures.gateway_access import (
    FixtureProofAuth,
    enroll_fixture_admin,
    fixture_admin_key,
    gateway_fixture_client,
    self_fixture_auth,
)
import httpx
from pydantic import BaseModel, ConfigDict
import pytest
import uvicorn

from houmao.agents.realm_controller.agent_identity import derive_agent_id_from_name
from houmao.agents.realm_controller.errors import GatewayError
import houmao.agents.realm_controller.gateway_plugin_host as host_module
from houmao.agents.realm_controller.gateway_service import (
    GatewayServiceRuntime,
    _GatewayUvicornServer,
    create_app,
)
from houmao.agents.realm_controller.gateway_storage import (
    GatewayCapabilityPublication,
    ensure_gateway_capability,
    load_gateway_desired_config,
    write_gateway_desired_config,
)
from houmao.agents.realm_controller.manifest import (
    SessionManifestRequest,
    build_session_manifest_payload,
    default_manifest_path,
    write_session_manifest,
)
from houmao.agents.realm_controller.models import LaunchPlan, RoleInjectionPlan
from houmao.gateway.plugins import (
    GatewayPluginConfiguration,
    PluginContext,
    PluginDefinition,
    PluginInstanceConfiguration,
    PluginListener,
    plugin_route_access,
)
from houmao.gateway.plugins.discovery import LoadedPluginDefinition
from houmao.gateway.deployment import GatewayDeployment

pytestmark = pytest.mark.usefixtures("gateway_fixture_access")


class _Settings(BaseModel):
    """Declare the minimal independent plugin schema."""

    model_config = ConfigDict(extra="forbid", strict=True)


class _ObservedPlugin:
    """Observe lifecycle ordering through only the public plugin contracts."""

    def __init__(self, context: PluginContext, *, hold: bool) -> None:
        """Prepare a router and cooperative startup gate without resources."""

        self.m_context: PluginContext = context
        self.m_hold: bool = hold
        self.m_gate: asyncio.Event = asyncio.Event()
        self.m_router: APIRouter = APIRouter()
        self.m_enters: int = 0
        self.m_exits: int = 0
        self.m_listener: PluginListener | None = None

        @self.m_router.get("/ordinary", openapi_extra=plugin_route_access("private"))
        def ordinary() -> dict[str, str]:
            """Return the plugin's owner-bound identity under its ordinary route."""

            return {"instance": self.m_context.instance_id}

        @self.m_router.post("/control")
        def control() -> dict[str, bool]:
            """Expose a control with the default admin access class."""

            return {"accepted": True}

    @property
    def router(self) -> APIRouter:
        """Return ordinary declarations for the real host."""

        return self.m_router

    @asynccontextmanager
    async def lifespan(self) -> AsyncIterator[None]:
        """Capture listener metadata and expose bounded, cooperative startup."""

        self.m_enters += 1
        self.m_listener = self.m_context.listener
        try:
            if self.m_hold:
                await self.m_gate.wait()
            self.m_context.report_connection("connected")
            yield
        finally:
            self.m_exits += 1


def _runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    plugins_enabled: bool = True,
    port: int = 12345,
    hold_start: bool = False,
) -> tuple[GatewayServiceRuntime, list[_ObservedPlugin], list[str]]:
    """Use normal persisted gateway state and actual runtime worker lifecycle."""

    plan = LaunchPlan(
        backend="claude_headless",
        tool="claude",
        executable="claude",
        args=["-p"],
        working_directory=tmp_path,
        home_env_var="CLAUDE_CONFIG_DIR",
        home_path=tmp_path / "home",
        env={},
        env_var_names=[],
        role_injection=RoleInjectionPlan(
            method="native_append_system_prompt", role_name="role", prompt="test role"
        ),
        metadata={},
    )
    manifest_path = default_manifest_path(tmp_path, "claude_headless", "session-one")
    write_session_manifest(
        manifest_path,
        build_session_manifest_payload(
            SessionManifestRequest(
                launch_plan=plan,
                role_name="role",
                brain_manifest_path=tmp_path / "brain.yaml",
                agent_name="HOUMAO-plugin-lifecycle",
                agent_id=derive_agent_id_from_name("HOUMAO-plugin-lifecycle"),
                tmux_session_name="HOUMAO-plugin-lifecycle",
                session_id="session-one",
                agent_def_dir=tmp_path / "agents",
                backend_state={"session_id": "native-session-one"},
            )
        ),
    )
    paths = ensure_gateway_capability(
        GatewayCapabilityPublication(
            manifest_path=manifest_path,
            backend="claude_headless",
            tool="claude",
            session_id="session-one",
            tmux_session_name="HOUMAO-plugin-lifecycle",
            working_directory=tmp_path,
            backend_state={"session_id": "native-session-one"},
            agent_def_dir=tmp_path / "agents",
        )
    )
    if plugins_enabled:
        desired = load_gateway_desired_config(paths.desired_config_path)
        write_gateway_desired_config(
            paths.desired_config_path,
            desired.model_copy(
                update={
                    "desired_plugins": GatewayPluginConfiguration(
                        plugins={"one": PluginInstanceConfiguration(implementation="observed")},
                        startup_timeout_seconds=2.0,
                        shutdown_timeout_seconds=0.1,
                    )
                }
            ),
        )
    observed: list[_ObservedPlugin] = []

    def create(context: PluginContext, _settings: _Settings) -> _ObservedPlugin:
        """Create an ordinary external-style implementation."""

        plugin = _ObservedPlugin(context, hold=hold_start)
        observed.append(plugin)
        return plugin

    definition = PluginDefinition(
        config_model=_Settings, binding_identity=lambda _settings: "account-one", create=create
    )
    loaded = LoadedPluginDefinition(
        definition=cast(PluginDefinition[BaseModel], definition),
        distribution="observed-external",
        distribution_version="1.0",
    )
    monkeypatch.setattr(host_module, "load_plugin_definition", lambda _name: loaded)
    runtime = GatewayServiceRuntime.from_gateway_root(
        gateway_root=paths.gateway_root, host="127.0.0.1", port=port
    )
    transitions: list[str] = []
    original_start = runtime.start
    original_shutdown = runtime.shutdown

    def start() -> None:
        """Observe genuine core startup without substituting a fake runtime."""

        transitions.append("core_start")
        original_start()

    def shutdown() -> None:
        """Require resource exit before the real core loses its facilities."""

        if observed and observed[0].m_enters:
            assert observed[0].m_exits == 1
        transitions.append("core_stop")
        original_shutdown()

    monkeypatch.setattr(runtime, "start", start)
    monkeypatch.setattr(runtime, "shutdown", shutdown)
    return runtime, observed, transitions


async def _wait_running(runtime: GatewayServiceRuntime) -> None:
    """Wait for the independent host task without issuing provider I/O."""

    async with asyncio.timeout(1.0):
        while runtime.m_plugin_host.status()[0].lifecycle != "running":
            await asyncio.sleep(0.001)


def test_plugin_private_access_precedes_lifecycle_and_uses_current_policy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Plugin routes apply open and keyed admission before handling lifecycle."""

    runtime, observed, _ = _runtime(tmp_path, monkeypatch, hold_start=True)
    app = create_app(runtime=runtime)
    ordinary_path = "/v1/plugins/one/ordinary"
    control_path = "/v1/plugins/one/control"
    with TestClient(app, base_url=runtime.owner_connect_url) as client:
        self_auth = self_fixture_auth(runtime)
        assert client.get(ordinary_path).status_code == 503
        assert client.get(ordinary_path, auth=self_auth).status_code == 503
        assert client.post(control_path).status_code == 503
        assert client.portal is not None
        client.portal.call(observed[0].m_gate.set)
        client.portal.call(_wait_running, runtime)
        assert client.post(control_path).status_code == 200
        assert client.get(ordinary_path).json() == {"instance": "one"}
        assert client.get(ordinary_path, auth=self_auth).json() == {"instance": "one"}

        key, signer = fixture_admin_key(tmp_path, "plugin-admin")
        enroll_fixture_admin(client, key, signer)
        admin_auth = FixtureProofAuth(signer, purpose="admin")
        assert client.post(control_path).status_code == 401
        assert client.get(ordinary_path).status_code == 401
        assert client.post(control_path, auth=self_auth).status_code == 403
        assert client.post(control_path, auth=admin_auth).status_code == 200
        assert client.get(ordinary_path, auth=self_auth).status_code == 200
        assert client.get(ordinary_path, auth=admin_auth).status_code == 200


def test_embedded_app_owns_exactly_one_core_and_plugin_lifecycle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The supported app factory activates resources without a CLI wrapper."""

    runtime, observed, transitions = _runtime(tmp_path, monkeypatch)
    app = create_app(runtime=runtime)
    assert transitions == [] and observed[0].m_enters == 0
    with gateway_fixture_client(runtime, app=app) as client:
        assert client.get("/health").status_code == 200
        for _ in range(100):
            if client.get("/v1/plugins/one/_status").json()["lifecycle"] == "running":
                break
        else:
            pytest.fail("embedded plugin did not activate")
        assert transitions == ["core_start"]
        assert observed[0].m_enters == 1 and observed[0].m_exits == 0
        assert runtime.m_worker_thread.is_alive()
        assert runtime.m_paths.current_instance_path.is_file()
    assert transitions == ["core_start", "core_stop"]
    assert observed[0].m_exits == 1
    assert not runtime.m_paths.current_instance_path.exists()


def test_embedded_app_preserves_external_core_ownership_when_already_started(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Embedding a running core starts and stops only the plugin resources."""

    runtime, observed, transitions = _runtime(tmp_path, monkeypatch)
    runtime.start()
    try:
        with gateway_fixture_client(runtime) as client:
            assert client.get("/health").status_code == 200
        assert transitions == ["core_start"]
        assert observed[0].m_enters == 1 and observed[0].m_exits == 1
        assert runtime.m_worker_thread.is_alive()
    finally:
        runtime.shutdown()


def test_second_app_cannot_replace_the_original_live_host(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A second app factory call cannot orphan the original resource supervisor."""

    runtime, observed, transitions = _runtime(tmp_path, monkeypatch)
    app = create_app(runtime=runtime)
    original_host = runtime.m_plugin_host
    with gateway_fixture_client(runtime, app=app) as client:
        assert client.get("/health").status_code == 200
        for _ in range(100):
            if client.get("/v1/plugins/one/_status").json()["lifecycle"] == "running":
                break
        else:
            pytest.fail("original host did not activate")
        with pytest.raises(GatewayError, match="only one application"):
            create_app(runtime=runtime)
        assert runtime.m_plugin_host is original_host
        assert len(observed) == 1 and observed[0].m_enters == 1
        assert observed[0].m_exits == 0
        assert client.get("/v1/plugins/one/_status").json()["lifecycle"] == "running"
    assert observed[0].m_exits == 1
    assert transitions == ["core_start", "core_stop"]


def test_no_plugin_app_keeps_existing_explicit_core_lifecycle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An empty selection does not create implicit runtime worker threads."""

    runtime, observed, transitions = _runtime(tmp_path, monkeypatch, plugins_enabled=False)
    try:
        with gateway_fixture_client(runtime) as client:
            assert client.get("/health").status_code == 200
            assert client.get("/v1/plugins").json()["plugins"] == []
        assert transitions == [] and not observed
        assert runtime.m_worker_thread is None
    finally:
        runtime.shutdown()


def test_embedded_start_failure_releases_already_started_core(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Lifespan cleanup also covers an exception before its yield point."""

    runtime, _observed, transitions = _runtime(tmp_path, monkeypatch)
    original_start_plugins = runtime.start_plugins

    async def fail_after_schedule() -> None:
        """Fail coordinator setup after it has scheduled instance activation."""

        await original_start_plugins()
        raise RuntimeError("coordinator failure")

    monkeypatch.setattr(runtime, "start_plugins", fail_after_schedule)
    with pytest.raises(RuntimeError, match="coordinator failure"):
        with gateway_fixture_client(runtime):
            pytest.fail("startup unexpectedly succeeded")
    assert transitions == ["core_start", "core_stop"]
    assert not runtime.m_paths.current_instance_path.exists()
    assert not runtime.m_worker_thread.is_alive()


@pytest.mark.parametrize("host", ["127.0.0.1", "0.0.0.0"])
def test_production_binds_ephemeral_port_before_plugin_start_without_waiting_for_service(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, host: str
) -> None:
    """A pending service startup does not block the actual core listener."""

    runtime, observed, transitions = _runtime(tmp_path, monkeypatch, port=0, hold_start=True)
    runtime.m_host = host
    monkeypatch.setattr(
        "houmao.agents.realm_controller.gateway_service.load_gateway_deployment",
        lambda _path: GatewayDeployment(bind_host=host),
    )
    app = create_app(runtime=runtime)
    config = uvicorn.Config(app, host=host, port=0, log_level="error", lifespan="on")
    server = _GatewayUvicornServer(config, runtime=runtime, requested_host=host)
    config.load()
    server.lifespan = config.lifespan_class(config)

    async def exercise() -> None:
        """Exercise real Uvicorn socket binding with the post-bind coordinator."""

        try:
            async with asyncio.timeout(1.0):
                await server.startup()
            assert transitions == ["core_start"]
            assert runtime.m_port > 0
            assert runtime.m_worker_thread.is_alive()
            assert runtime.m_plugin_host.status()[0].lifecycle == "starting"
            async with httpx.AsyncClient(
                base_url=runtime.owner_connect_url, auth=self_fixture_auth(runtime)
            ) as client:
                assert (await client.get("/health")).status_code == 200
                status = (await client.get("/v1/plugins/one/_status")).json()
                assert status["lifecycle"] == "starting"
            assert observed[0].m_enters == 1 and observed[0].m_exits == 0
            listener = observed[0].m_listener
            assert listener is not None and listener.port == runtime.m_port
            assert listener.host == host and listener.base_url == runtime.owner_connect_url
            assert listener.port != config.port
            observed[0].m_gate.set()
            await _wait_running(runtime)
            await server.startup()
        finally:
            await server.shutdown()
            await server.shutdown()

    asyncio.run(exercise())
    assert transitions == ["core_start", "core_stop"]
    assert observed[0].m_enters == observed[0].m_exits == 1
    assert not runtime.m_paths.current_instance_path.exists()


def test_production_partial_core_start_failure_shuts_down_bound_listener(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A startup exception after core resources exist closes both lifecycles."""

    runtime, observed, transitions = _runtime(tmp_path, monkeypatch, port=0)
    app = create_app(runtime=runtime)
    original_start = runtime.start

    def fail_after_start() -> None:
        """Fail after the actual runtime worker threads have been created."""

        original_start()
        raise RuntimeError("core setup failed")

    monkeypatch.setattr(runtime, "start", fail_after_start)
    config = uvicorn.Config(app, host="127.0.0.1", port=0, log_level="error", lifespan="on")
    server = _GatewayUvicornServer(config, runtime=runtime, requested_host="127.0.0.1")
    config.load()
    server.lifespan = config.lifespan_class(config)

    async def exercise() -> None:
        """Start a bound listener and verify error cleanup is idempotent."""

        with pytest.raises(RuntimeError, match="core setup failed"):
            await server.startup()
        await server.shutdown()
        assert all(not listener.is_serving() for listener in server.servers)

    asyncio.run(exercise())
    assert transitions == ["core_start", "core_stop"]
    assert observed[0].m_enters == observed[0].m_exits == 0
    assert not runtime.m_worker_thread.is_alive()
