"""Owner selection plumbing and persistence tests with deterministic launch seams."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from click.testing import CliRunner
import pytest
from pydantic import BaseModel

from houmao.agents.realm_controller import runtime
from houmao.agents.realm_controller.errors import (
    GatewayAttachError,
    GatewayHttpError,
    SessionManifestError,
)
from houmao.agents.realm_controller.errors import BackendExecutionError
from houmao.agents.realm_controller.backends.dispatch_control import HeadlessDispatchControl
from houmao.agents.realm_controller.backends.tmux_runtime import TmuxCommandError
from houmao.agents.realm_controller.gateway_client import GatewayEndpoint
from houmao.agents.realm_controller.gateway_models import (
    GatewayCurrentInstanceV1,
    GatewayDesiredConfigV1,
    GatewayTuiTrackingTimingConfigV1,
)
from houmao.agents.realm_controller.gateway_storage import (
    GatewayCapabilityPublication,
    GatewayPaths,
    ensure_gateway_capability,
    gateway_paths_from_session_root,
    load_gateway_desired_config,
    write_gateway_current_instance,
    write_gateway_desired_config,
)
from houmao.agents.realm_controller.models import LaunchPlan, RoleInjectionPlan
from houmao.execution.tmux import TmuxPaneRecord
from houmao.gateway.deployment import GatewayDeployment
from houmao.gateway.plugins import (
    GatewayPluginConfiguration,
    GatewayPluginStatusResponse,
    PluginInstanceConfiguration,
)
from houmao.gateway.plugins.configuration import (
    apply_plugin_config_overrides,
    parse_plugin_config_overrides,
)
from houmao.srv_ctrl.commands.main import cli


def _selection(account: str = "example") -> GatewayPluginConfiguration:
    """Return a non-secret typed whole-set selection."""

    return GatewayPluginConfiguration(
        plugins={
            "events": PluginInstanceConfiguration(
                implementation="external-example", config={"account": account}
            )
        }
    )


@pytest.fixture
def controller(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> runtime.RuntimeSessionController:
    """Create a local controller whose launch and registry work stays hermetic."""

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
            method="native_append_system_prompt", role_name="role", prompt="example"
        ),
        metadata={},
    )
    value = runtime.RuntimeSessionController(
        launch_plan=plan,
        role_name="role",
        brain_manifest_path=tmp_path / "brain.yaml",
        manifest_path=tmp_path / "session" / "manifest.json",
        backend_session=SimpleNamespace(),
        agent_id="owner-alpha",
        tmux_session_name="HOUMAO-example",
    )
    monkeypatch.setattr(
        runtime.RuntimeSessionController, "refresh_shared_registry_record", lambda _: None
    )
    return value


@pytest.fixture
def paths(
    controller: runtime.RuntimeSessionController, monkeypatch: pytest.MonkeyPatch
) -> GatewayPaths:
    """Persist actual desired configuration while replacing unrelated publication."""

    value = gateway_paths_from_session_root(session_root=controller.manifest_path.parent)
    value.gateway_root.mkdir(parents=True)
    value.logs_dir.mkdir(parents=True)
    write_gateway_desired_config(
        value.desired_config_path, GatewayDesiredConfigV1(desired_plugins=_selection())
    )
    monkeypatch.setattr(runtime, "_require_gateway_paths_for_controller", lambda _: value)
    monkeypatch.setattr(
        runtime,
        "resolve_internal_gateway_attach_contract",
        lambda _: SimpleNamespace(desired_host=None, desired_port=None),
    )
    monkeypatch.setattr(runtime, "_live_gateway_for_plugin_attach", lambda **_: None)
    store = SimpleNamespace(snapshot=lambda: SimpleNamespace(admin_mode="open"))
    access = SimpleNamespace(
        store=store,
        require_self_signing_state=lambda: None,
        target=SimpleNamespace(incarnation="fixture"),
    )
    monkeypatch.setattr(runtime, "gateway_access_for_manifest", lambda _path: access)
    monkeypatch.setattr(runtime, "load_gateway_deployment", lambda _path: None)

    return value


def test_launch_plugin_override_requires_launch_time_attach(tmp_path: Path) -> None:
    """Reject launch-only selection before reading or creating any runtime input."""

    with pytest.raises(SessionManifestError, match="plugin selections require"):
        runtime.start_runtime_session(
            agent_def_dir=tmp_path / "missing",
            brain_manifest_path=tmp_path / "missing.yaml",
            role_name=None,
            gateway_plugins=_selection(),
        )
    assert list(tmp_path.iterdir()) == []


def test_attach_omission_preserves_and_explicit_empty_clears(
    controller: runtime.RuntimeSessionController,
    paths: GatewayPaths,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Selection replacement is visible before child startup and survives retries."""

    observed: list[GatewayPluginConfiguration | None] = []

    def launch(**_: object) -> int:
        """Observe the real persisted selection a child would read."""

        observed.append(load_gateway_desired_config(paths.desired_config_path).desired_plugins)
        return 43123

    monkeypatch.setattr(runtime, "_start_gateway_process", launch)
    assert controller.attach_gateway().status == "ok"
    assert observed == [_selection()]
    empty = GatewayPluginConfiguration(plugins={})
    assert controller.attach_gateway(plugin_config=empty).status == "ok"
    assert observed == [_selection(), empty]
    assert load_gateway_desired_config(paths.desired_config_path).desired_plugins == empty
    assert controller.attach_gateway(plugin_config=_selection("new-account")).status == "ok"
    assert observed[-1] == _selection("new-account")


@pytest.mark.parametrize("selection", [_selection(), None])
def test_live_equivalent_plugin_selection_reuses_gateway(
    controller: runtime.RuntimeSessionController,
    paths: GatewayPaths,
    monkeypatch: pytest.MonkeyPatch,
    selection: GatewayPluginConfiguration | None,
) -> None:
    """An equivalent explicit or preserved selection starts no replacement process."""

    current = GatewayCurrentInstanceV1(
        pid=4242, host="127.0.0.1", port=43123, managed_agent_instance_epoch=1
    )
    monkeypatch.setattr(runtime, "_live_gateway_for_plugin_attach", lambda *args, **_: current)
    monkeypatch.setattr(
        runtime,
        "owner_gateway_client_for_controller",
        lambda *args, **_: SimpleNamespace(
            get_plugins=lambda: GatewayPluginStatusResponse(
                configuration_digest=_selection().configuration_digest
            )
        ),
    )
    monkeypatch.setattr(
        runtime,
        "_start_gateway_process",
        lambda *args, **_: pytest.fail("equivalent live gateway restarted"),
    )
    before = paths.desired_config_path.read_bytes()
    result = controller.attach_gateway(plugin_config=selection)
    assert result.status == "ok"
    assert (result.gateway_host, result.gateway_port) == ("127.0.0.1", 43123)
    assert paths.desired_config_path.read_bytes() == before


@pytest.mark.parametrize("selection", [_selection("other-account"), GatewayPluginConfiguration()])
def test_live_changed_selection_conflicts_without_mutation(
    controller: runtime.RuntimeSessionController,
    paths: GatewayPaths,
    monkeypatch: pytest.MonkeyPatch,
    selection: GatewayPluginConfiguration,
) -> None:
    """A changed or cleared live selection preserves desired and active authority."""

    current = GatewayCurrentInstanceV1(
        pid=4242, host="127.0.0.1", port=43123, managed_agent_instance_epoch=1
    )
    monkeypatch.setattr(runtime, "_live_gateway_for_plugin_attach", lambda *args, **_: current)
    monkeypatch.setattr(
        runtime,
        "owner_gateway_client_for_controller",
        lambda *args, **_: SimpleNamespace(
            get_plugins=lambda: GatewayPluginStatusResponse(
                configuration_digest=_selection().configuration_digest
            )
        ),
    )
    monkeypatch.setattr(
        runtime, "_start_gateway_process", lambda *args, **_: pytest.fail("live gateway restarted")
    )
    monkeypatch.setattr(
        runtime,
        "_clear_stale_gateway_runtime_state",
        lambda *args, **_: pytest.fail("live publication cleared"),
    )
    before = paths.desired_config_path.read_bytes()
    result = controller.attach_gateway(plugin_config=selection)
    assert result.status == "error"
    assert "Detach and attach" in result.detail
    assert paths.desired_config_path.read_bytes() == before


def test_live_unverifiable_selection_preserves_publication(
    controller: runtime.RuntimeSessionController,
    paths: GatewayPaths,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unavailable status endpoint cannot authorize a selection mutation."""

    current = GatewayCurrentInstanceV1(
        pid=4242, host="127.0.0.1", port=43123, managed_agent_instance_epoch=1
    )

    def unavailable() -> GatewayPluginStatusResponse:
        """Model a listener whose active selection cannot be read."""

        raise GatewayHttpError(
            method="GET", url="http://127.0.0.1/v1/plugins", detail="unavailable"
        )

    monkeypatch.setattr(runtime, "_live_gateway_for_plugin_attach", lambda *args, **_: current)
    monkeypatch.setattr(
        runtime,
        "owner_gateway_client_for_controller",
        lambda *args, **_: SimpleNamespace(get_plugins=unavailable),
    )
    monkeypatch.setattr(
        runtime,
        "_clear_stale_gateway_runtime_state",
        lambda *args, **_: pytest.fail("live publication cleared"),
    )
    before = paths.desired_config_path.read_bytes()
    result = controller.attach_gateway(plugin_config=_selection("other"))
    assert result.status == "error"
    assert "Cannot verify" in result.detail
    assert paths.desired_config_path.read_bytes() == before


def test_live_deployment_conflict_preserves_selection_and_listener(
    controller: runtime.RuntimeSessionController,
    paths: GatewayPaths,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Require detach before an access setting or signer changes."""

    retained = GatewayDeployment(bind_port=43123, advertised_url="https://gateway.example.org/a")
    current = GatewayCurrentInstanceV1(
        pid=4242, host="127.0.0.1", port=43123, managed_agent_instance_epoch=1
    )
    monkeypatch.setattr(runtime, "_live_gateway_for_plugin_attach", lambda **_: current)
    monkeypatch.setattr(runtime, "load_gateway_deployment", lambda _path: retained)
    monkeypatch.setattr(
        runtime,
        "owner_gateway_client_for_controller",
        lambda *args, **kwargs: SimpleNamespace(
            get_plugins=lambda: GatewayPluginStatusResponse(
                configuration_digest=_selection().configuration_digest
            )
        ),
    )
    monkeypatch.setattr(
        runtime, "save_gateway_deployment", lambda *args: pytest.fail("live deployment rewritten")
    )
    monkeypatch.setattr(
        runtime, "_start_gateway_process", lambda **_: pytest.fail("live process replaced")
    )
    before = paths.desired_config_path.read_bytes()
    assert controller.attach_gateway(access_config=retained).gateway_port == 43123
    changed = controller.attach_gateway(
        access_config=retained.model_copy(update={"public_input_enabled": True})
    )
    assert changed.status == "error"
    assert "Detach and attach" in changed.detail
    assert paths.desired_config_path.read_bytes() == before


@pytest.mark.parametrize("mode", ["detached_process", "tmux_auxiliary_window"])
def test_successful_gateway_launch_preserves_selection(
    controller: runtime.RuntimeSessionController,
    paths: GatewayPaths,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
) -> None:
    """Both real launch branches retain selected plugins in listener rewrites."""

    endpoint = GatewayEndpoint(host="127.0.0.1", port=43123)
    monkeypatch.setattr(runtime, "_wait_for_gateway_endpoint", lambda **_: endpoint)
    monkeypatch.setattr(runtime, "_wait_for_same_session_gateway_endpoint", lambda **_: endpoint)
    monkeypatch.setattr(
        runtime, "_launch_same_session_gateway_window", lambda **_: SimpleNamespace(pane_id="%9")
    )
    monkeypatch.setattr(runtime, "_find_tmux_pane", lambda **_: SimpleNamespace(pane_dead=False))
    monkeypatch.setattr(
        runtime,
        "GatewayClient",
        lambda **_: SimpleNamespace(health=lambda: SimpleNamespace(protocol_version="v1")),
    )
    monkeypatch.setattr(runtime, "refresh_internal_gateway_publication", lambda _: None)
    monkeypatch.setattr(runtime, "publish_live_gateway_env", lambda **_: None)
    monkeypatch.setattr(
        runtime.subprocess, "Popen", lambda *_, **__: SimpleNamespace(pid=4242, poll=lambda: None)
    )
    port = runtime._start_gateway_process(
        controller=controller,
        paths=paths,
        host="127.0.0.1",
        port=0,
        execution_mode=mode,
        tui_tracking_timings=GatewayTuiTrackingTimingConfigV1(),
    )
    assert port == 43123
    persisted = load_gateway_desired_config(paths.desired_config_path)
    assert persisted.desired_plugins == _selection()
    assert persisted.desired_execution_mode == mode


def test_gateway_capability_refresh_preserves_plugin_selection(tmp_path: Path) -> None:
    """Capability publication retains typed selections through repeated refreshes."""

    manifest = tmp_path / "runtime" / "sessions" / "cao_rest" / "session-1" / "manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("{}\n", encoding="utf-8")
    publication = GatewayCapabilityPublication(
        manifest_path=manifest,
        backend="cao_rest",
        tool="codex",
        session_id="session-1",
        tmux_session_name="HOUMAO-example",
        working_directory=tmp_path,
        backend_state={
            "api_base_url": "http://localhost:9889",
            "terminal_id": "example",
            "profile_name": "example",
            "profile_path": str(tmp_path / "profile.md"),
            "parsing_mode": "shadow_only",
        },
        agent_def_dir=tmp_path / "agents",
    )
    paths = ensure_gateway_capability(publication)
    assert load_gateway_desired_config(paths.desired_config_path).desired_plugins is None
    write_gateway_desired_config(
        paths.desired_config_path, GatewayDesiredConfigV1(desired_plugins=_selection())
    )
    ensure_gateway_capability(publication)
    assert load_gateway_desired_config(paths.desired_config_path).desired_plugins == _selection()


def test_maintained_cli_passes_the_public_typed_selection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Scoped manager configuration is equivalent to the Python attach boundary."""

    document = tmp_path / "plugins.yaml"
    document.write_text(
        "schema_version: 1\ngateway:\n  plugins:\n    events:\n      implementation: external-example\n      config: {account: example}\n",
        encoding="utf-8",
    )
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.resolve_managed_agent_target", lambda **_: "target"
    )

    def attach(target: object, **kwargs: object) -> dict[str, str]:
        """Capture exactly the selection crossing the maintained CLI boundary."""

        captured.update(kwargs)
        return {"status": "ok"}

    monkeypatch.setattr("houmao.srv_ctrl.commands.agents.gateway.attach_gateway", attach)
    result = CliRunner().invoke(
        cli,
        [
            "agents",
            "single",
            "--agent-id",
            "owner-alpha",
            "gateway",
            "attach",
            "--plugins-config",
            str(document),
        ],
    )
    assert result.exit_code == 0, result.output
    assert captured["plugin_config"] == _selection()


def test_maintained_cli_rejects_invalid_selection_before_target_resolution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Invalid owner configuration causes no runtime discovery or persistence."""

    document = tmp_path / "invalid.yaml"
    document.write_text(
        "schema_version: 1\ngateway:\n  plugins: {}\n  plugins: {}\n", encoding="utf-8"
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.resolve_managed_agent_target",
        lambda **_: pytest.fail("target resolution ran"),
    )
    result = CliRunner().invoke(
        cli,
        [
            "agents",
            "single",
            "--agent-id",
            "owner-alpha",
            "gateway",
            "attach",
            "--plugins-config",
            str(document),
        ],
    )
    assert result.exit_code == 1
    assert "Duplicate plugin configuration key" in result.output


def test_launch_overrides_merge_selected_instances_and_validate_models(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Use the selected plugin's validation and leave sibling instances intact."""

    class Settings(BaseModel):
        """Represent a plugin-owned config model with a typed nested object."""

        account: str
        timing: dict[str, float]

    monkeypatch.setattr(
        "houmao.gateway.plugins.discovery.load_plugin_definition",
        lambda _: SimpleNamespace(definition=SimpleNamespace(config_model=Settings)),
    )
    selected = GatewayPluginConfiguration.model_validate(
        {
            "plugins": {
                "team": {
                    "implementation": "example",
                    "config": {"account": "owner", "timing": {"quiet": 1.0, "max": 9.0}},
                },
                "other": {
                    "implementation": "example",
                    "config": {"account": "other", "timing": {"quiet": 2.0}},
                },
            }
        }
    )
    overrides = parse_plugin_config_overrides(
        (
            'team={"timing":{"quiet":2.0}}',
            'team={"timing":{"quiet":3.0}}',
        )
    )
    result = apply_plugin_config_overrides(selected, overrides)
    assert result.plugins["team"].config == {
        "account": "owner",
        "timing": {"quiet": 3.0, "max": 9.0},
    }
    assert result.plugins["other"] == selected.plugins["other"]
    from houmao.gateway.plugins import PluginConfigurationError

    with pytest.raises(PluginConfigurationError, match="selected instance"):
        apply_plugin_config_overrides(selected, {"missing": {}})
    with pytest.raises(PluginConfigurationError, match="failed validation"):
        apply_plugin_config_overrides(selected, {"team": {"timing": "invalid"}})


def test_maintained_cli_parses_repeatable_plugin_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    """Send strict override objects through the maintained attach command."""

    captured: dict[str, object] = {}

    def attach(_target: object, **kwargs: object) -> dict[str, str]:
        """Capture the exact override structure crossing the attach boundary."""

        captured.update(kwargs)
        return {"status": "ok"}

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.resolve_managed_agent_target", lambda **_: "target"
    )
    monkeypatch.setattr("houmao.srv_ctrl.commands.agents.gateway.attach_gateway", attach)
    result = CliRunner().invoke(
        cli,
        [
            "agents",
            "single",
            "--agent-id",
            "owner-alpha",
            "gateway",
            "attach",
            "--plugin-config-override",
            'team={"delivery":{"transport":"push"}}',
            "--plugin-config-override",
            'team={"delivery":{"push_policy":"asap"}}',
        ],
    )
    assert result.exit_code == 0, result.output
    assert captured["plugin_config_overrides"] == {
        "team": {"delivery": {"transport": "push", "push_policy": "asap"}}
    }


@pytest.mark.parametrize("generation", ["new-generation", None])
def test_stale_dispatch_worker_cannot_overwrite_replacement_manifest(
    controller: runtime.RuntimeSessionController,
    monkeypatch: pytest.MonkeyPatch,
    generation: str | None,
) -> None:
    """Late completion cannot persist an old controller over a replacement body."""

    control = HeadlessDispatchControl.from_callbacks(
        allowed=lambda: False, confirmed=lambda: None, deadline=0.0, generation_id="old-generation"
    )

    class Session:
        """Complete execution while retaining its original selected generation."""

        m_dispatch_control = control

        def send_prompt(self, *args: object, **kwargs: object) -> list[object]:
            """Finish work without accessing the native backend."""

            return []

    monkeypatch.setattr(runtime, "HeadlessInteractiveSession", Session)
    controller.backend_session = Session()
    monkeypatch.setattr(
        runtime,
        "load_session_manifest",
        lambda _: SimpleNamespace(payload={"registry_generation_id": generation}),
    )
    monkeypatch.setattr(
        runtime.RuntimeSessionController,
        "persist_manifest",
        lambda *_, **__: pytest.fail("stale manifest persisted"),
    )
    with pytest.raises(BackendExecutionError, match="execution identity is no longer current"):
        controller.send_prompt("ordinary example")


def test_confirmed_turn_can_persist_after_dispatch_deadline(
    controller: runtime.RuntimeSessionController, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Completed ordinary work may outlive its caller's handoff deadline."""

    control = HeadlessDispatchControl.from_callbacks(
        allowed=lambda: False, confirmed=lambda: None, deadline=0.0, generation_id="same-generation"
    )

    class Session:
        """Return completed work after its immediate dispatch deadline."""

        m_dispatch_control = control

        def send_prompt(self, *args: object, **kwargs: object) -> list[object]:
            """Finish without rechecking a deadline after handoff."""

            return []

    monkeypatch.setattr(runtime, "HeadlessInteractiveSession", Session)
    controller.backend_session = Session()
    monkeypatch.setattr(
        runtime,
        "load_session_manifest",
        lambda _: SimpleNamespace(payload={"registry_generation_id": "same-generation"}),
    )
    persisted: list[bool] = []
    monkeypatch.setattr(
        runtime.RuntimeSessionController,
        "persist_manifest",
        lambda *_, **__: persisted.append(True),
    )
    assert controller.send_prompt("ordinary example") == []
    assert persisted == [True]


def test_gateway_window_cleanup_succeeds_when_last_window_removes_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """After body death, killing the last gateway window can remove its session."""

    current = GatewayCurrentInstanceV1(
        pid=4242,
        host="127.0.0.1",
        port=43123,
        execution_mode="tmux_auxiliary_window",
        tmux_window_id="@9",
        tmux_window_index="1",
        tmux_pane_id="%9",
        managed_agent_instance_epoch=1,
    )
    killed = False

    def observe(_server: object, session_name: str) -> tuple[TmuxPaneRecord, ...] | None:
        """Report the exact remaining gateway pane until its window is killed."""

        assert session_name == "HOUMAO-example"
        if killed:
            return None
        return (TmuxPaneRecord("%9", session_name, "@9", "1", "gateway", "0", False),)

    def kill(_server: object, args: list[str]) -> None:
        """Accept only the confirmed window and model synchronous last-window teardown."""

        nonlocal killed
        assert args == ["kill-window", "-t", "@9"]
        killed = True

    monkeypatch.setattr(runtime.TmuxServer, "observe_session", observe)
    monkeypatch.setattr(runtime.TmuxServer, "checked_command", kill)
    assert (
        runtime._stop_same_session_gateway_surface(
            session_name="HOUMAO-example", current_instance=current, strict=True
        )
        is True
    )
    assert (
        runtime._same_session_gateway_is_alive(
            session_name="HOUMAO-example", current_instance=current
        )
        is False
    )


def test_gateway_cleanup_preserves_unrelated_tmux_inspection_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An inspection failure still propagates when the selected session exists."""

    def failed(_server: object, _session_name: str) -> tuple[object, ...]:
        """Report a non-absence tmux failure."""

        raise TmuxCommandError("Inspection failed")

    monkeypatch.setattr(runtime.TmuxServer, "observe_session", failed)
    with pytest.raises(TmuxCommandError, match="Inspection failed"):
        runtime._find_tmux_pane(session_name="HOUMAO-example", pane_id="%9")


def test_failed_auxiliary_teardown_preserves_gateway_receipt(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Keep the current gateway discoverable when checked window teardown fails."""

    paths = gateway_paths_from_session_root(session_root=tmp_path)
    paths.current_instance_path.parent.mkdir(parents=True)
    current = GatewayCurrentInstanceV1(
        pid=123,
        host="127.0.0.1",
        port=12345,
        execution_mode="tmux_auxiliary_window",
        tmux_window_id="@9",
        tmux_window_index="1",
        tmux_pane_id="%9",
        managed_agent_instance_epoch=1,
    )
    write_gateway_current_instance(paths.current_instance_path, current)
    receipt = paths.current_instance_path.read_bytes()
    monkeypatch.setattr(runtime, "_tmux_session_name_for_controller", lambda _controller: "owner")
    monkeypatch.setattr(
        runtime.TmuxServer,
        "observe_session",
        lambda _server, name: (TmuxPaneRecord("%9", name, "@9", "1", "gateway", "0", False),),
    )

    def refused(_server: object, args: list[str]) -> None:
        """Fail the exact kill without claiming the old window is gone."""

        assert args == ["kill-window", "-t", "@9"]
        raise TmuxCommandError("tmux kill-window exited with status 2", returncode=2)

    monkeypatch.setattr(runtime.TmuxServer, "checked_command", refused)
    with pytest.raises(GatewayAttachError, match="status 2"):
        runtime._clear_stale_gateway_runtime_state(
            controller=SimpleNamespace(), paths=paths, attach_contract=SimpleNamespace()
        )
    assert paths.current_instance_path.read_bytes() == receipt
