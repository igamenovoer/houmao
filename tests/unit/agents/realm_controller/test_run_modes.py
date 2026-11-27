"""Exercise native run-mode defaults and qualification across launch entrypoints."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from houmao.agents.realm_controller import runtime
from houmao.agents.realm_controller.errors import LaunchPlanError, SessionManifestError
from houmao.agents.realm_controller.gateway_models import GatewayTuiTrackingTimingOverridesV1
from houmao.agents.realm_controller.models import BackendKind, GatewayControlResult
from houmao.agents.realm_controller.native_surface import NativeSurfaceKind
from houmao.agents.realm_controller.run_modes import (
    RunMode,
    RunModeEntrypoint,
    RunModeSelection,
    gateway_backend_capabilities,
    resolve_run_mode,
    validate_mode_binding,
)
from houmao.execution.tmux_selection import ResolvedTmuxServer


@pytest.mark.parametrize(
    ("backend", "parser_backed", "manager_launch", "runtime_launch", "attach_and_process"),
    [
        ("local_interactive", True, True, True, True),
        ("cao_rest", True, True, True, True),
        ("houmao_server_rest", True, True, True, True),
        ("dsh_web", False, False, False, False),
        ("kimi_web", False, False, False, False),
        ("hermes_tui", False, False, False, False),
        ("dsh_acp", False, False, False, True),
        ("kimi_acp", False, False, False, True),
        ("codex_app_server", False, False, False, True),
        ("hermes_service", False, False, False, True),
        ("claude_headless", False, False, True, True),
        ("codex_headless", False, False, True, True),
        ("kimi_headless", False, False, True, True),
        ("dsh_headless", False, False, True, True),
        ("hermes_headless", False, False, True, True),
    ],
)
def test_gateway_backend_timing_matrix(
    backend: BackendKind,
    parser_backed: bool,
    manager_launch: bool,
    runtime_launch: bool,
    attach_and_process: bool,
) -> None:
    """Pin separate timing acceptance and parser eligibility for every backend."""

    capabilities = gateway_backend_capabilities(backend)

    assert capabilities.parser_backed_tui == parser_backed
    assert capabilities.manager_launch_timings == manager_launch
    assert capabilities.runtime_launch_timings == runtime_launch
    assert capabilities.attach_timings == attach_and_process


@pytest.mark.parametrize("explicit_timings", [False, True])
@pytest.mark.parametrize(
    ("tool", "mode", "refusal"),
    [
        ("codex", "tui", None),
        ("codex", "headless", None),
        ("codex", "service", "Managed service mode does not support"),
        ("dsh", "web", "Web mode does not support"),
        ("hermes", "tui", "Hermes TUI uses native control"),
    ],
)
def test_runtime_launch_checks_only_explicit_timings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    tool: str,
    mode: RunMode,
    refusal: str | None,
    explicit_timings: bool,
) -> None:
    """Exercise direct runtime preflight without acquiring a real terminal or provider."""

    monkeypatch.setattr(
        runtime,
        "load_brain_manifest",
        lambda _: {
            "schema_version": 3,
            "inputs": {"tool": tool},
            "runtime": {
                "launch_executable": tool,
                "hermes_profile": {} if tool == "hermes" else None,
                "launch_contract": {
                    "adapter_defaults": {"args": []},
                    "requested_overrides": {"preset": None, "direct": None},
                },
            },
        },
    )
    monkeypatch.setattr(runtime, "validate_dsh_launch_version", lambda **_: None)
    prepare = Mock(side_effect=SessionManifestError("reached owner identity"))
    monkeypatch.setattr(runtime, "_resolve_start_session_identity", prepare)
    expected = refusal if explicit_timings and refusal is not None else "reached owner identity"

    with pytest.raises(SessionManifestError, match=expected):
        runtime.start_runtime_session(
            agent_def_dir=tmp_path,
            brain_manifest_path=tmp_path / "brain.yaml",
            role_name=None,
            runtime_root=tmp_path / "runtime",
            mode=mode,
            gateway_auto_attach=True,
            resolved_tmux_server=ResolvedTmuxServer(str(tmp_path / "owner.sock"), False),
            gateway_tui_tracking_timing_overrides=(
                GatewayTuiTrackingTimingOverridesV1(watch_poll_interval_seconds=0.25)
                if explicit_timings
                else None
            ),
        )
    assert prepare.call_count == int(expected == "reached owner identity")


@pytest.mark.parametrize("explicit_timings", [False, True])
@pytest.mark.parametrize(
    ("backend", "refusal"),
    [
        ("local_interactive", None),
        ("dsh_headless", None),
        ("hermes_service", None),
        ("dsh_web", "DSH Web does not support terminal tracking timing controls."),
        ("hermes_tui", "Hermes TUI does not support terminal tracking timing controls."),
    ],
)
def test_direct_gateway_attach_checks_only_explicit_timings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    backend: BackendKind,
    refusal: str | None,
    explicit_timings: bool,
) -> None:
    """Preserve attach refusals and allow service and headless timing overrides."""

    controller = SimpleNamespace(launch_plan=SimpleNamespace(backend=backend))
    paths = SimpleNamespace(gateway_root=tmp_path)
    monkeypatch.setattr(runtime, "_require_gateway_paths_for_controller", lambda _: paths)
    resolve = Mock(side_effect=SessionManifestError("reached attach authority"))
    monkeypatch.setattr(runtime, "resolve_internal_gateway_attach_contract", resolve)
    timings = (
        GatewayTuiTrackingTimingOverridesV1(watch_poll_interval_seconds=0.25)
        if explicit_timings
        else None
    )

    def attach() -> GatewayControlResult:
        """Apply the selected timing input to the owner's attach boundary."""

        return runtime._attach_gateway_for_controller(
            controller,
            host_override=None,
            port_override=None,
            execution_mode_override=None,
            tui_tracking_timing_overrides=timings,
        )

    if explicit_timings and refusal is not None:
        result = attach()
        assert result.status == "error" and result.detail == refusal
        resolve.assert_not_called()
    else:
        with pytest.raises(SessionManifestError, match="reached attach authority"):
            attach()
        resolve.assert_called_once_with(paths)


@pytest.mark.parametrize(
    ("tool", "entrypoint", "mode", "backend", "surface"),
    [
        ("claude", "project", "tui", "local_interactive", "terminal"),
        ("codex", "project", "tui", "local_interactive", "terminal"),
        ("kimi", "project", "tui", "local_interactive", "terminal"),
        ("dsh", "project", "web", "dsh_web", "web"),
        ("hermes", "project", "service", "hermes_service", None),
        ("hermes", "runtime", "service", "hermes_service", None),
        ("codex", "runtime", "headless", "codex_headless", None),
        ("kimi", "runtime", "headless", "kimi_headless", None),
        ("claude", "passive_headless", "headless", "claude_headless", None),
        ("codex", "passive_headless", "headless", "codex_headless", None),
        ("kimi", "passive_headless", "headless", "kimi_headless", None),
        ("dsh", "passive_headless", "headless", "dsh_headless", None),
        ("hermes", "passive_headless", "headless", "hermes_headless", None),
    ],
)
def test_resolve_launch_entrypoint_default(
    tool: str,
    entrypoint: RunModeEntrypoint,
    mode: RunMode,
    backend: BackendKind,
    surface: NativeSurfaceKind | None,
) -> None:
    """Select the qualified default and expected handoff for each entrypoint."""

    assert resolve_run_mode(tool, entrypoint=entrypoint) == RunModeSelection(
        tool=tool, mode=mode, backend=backend, human_surface_kind=surface
    )


@pytest.mark.parametrize(
    ("tool", "mode", "supported"),
    [
        ("dsh", "tui", "headless, service, web"),
        ("codex", "web", "headless, service, tui"),
        ("claude", "web", "headless, tui"),
        ("hermes", "web", "tui, service, headless"),
    ],
)
def test_reject_unqualified_modes(tool: str, mode: RunMode, supported: str) -> None:
    """Report currently qualified choices for each unimplemented mode."""

    with pytest.raises(LaunchPlanError, match=f"does not support mode {mode!r}.*{supported}"):
        resolve_run_mode(tool, mode=mode, entrypoint="project")


def test_passive_headless_birth_refuses_web_path() -> None:
    """Constrain the passive birth even when the tool otherwise defaults to Web."""

    with pytest.raises(LaunchPlanError, match="require mode 'headless'"):
        resolve_run_mode("dsh", mode="web", entrypoint="passive_headless")
    with pytest.raises(LaunchPlanError, match="conflicts with backend 'dsh_web'"):
        resolve_run_mode("dsh", backend="dsh_web", entrypoint="passive_headless")
    with pytest.raises(LaunchPlanError, match="conflicts with backend 'dsh_acp'"):
        resolve_run_mode("dsh", backend="dsh_acp", entrypoint="passive_headless")


def test_explicit_backend_binds_to_its_tool_and_mode() -> None:
    """Check a direct mode, explicit backend, and their conflicting combinations."""

    assert resolve_run_mode("codex", mode="tui").backend == "local_interactive"
    assert resolve_run_mode("codex", backend="cao_rest").mode == "tui"
    assert resolve_run_mode("codex", mode="tui", backend="local_interactive").mode == "tui"
    with pytest.raises(LaunchPlanError, match="conflicts with backend 'codex_headless'"):
        resolve_run_mode("codex", mode="tui", backend="codex_headless")
    with pytest.raises(LaunchPlanError, match="backend 'kimi_headless' do not agree"):
        resolve_run_mode("codex", backend="kimi_headless")


def test_hermes_explicit_mode_overrides_service_default() -> None:
    """Resolve explicit Hermes modes and reject service on passive birth."""

    tui = resolve_run_mode("hermes", mode="tui", entrypoint="project")
    assert tui == RunModeSelection("hermes", "tui", "hermes_tui", "terminal")
    assert resolve_run_mode("hermes", backend="hermes_tui") == tui
    assert resolve_run_mode("hermes", mode="headless").backend == "hermes_headless"
    with pytest.raises(LaunchPlanError, match="require mode 'headless'"):
        resolve_run_mode("hermes", mode="service", entrypoint="passive_headless")


def test_validate_persisted_mode_binding() -> None:
    """Bind persistent DSH ACP and one-shot DSH to their native modes."""

    validate_mode_binding("dsh", "service", "dsh_acp")
    with pytest.raises(ValueError, match="do not agree"):
        validate_mode_binding("dsh", "headless", "dsh_acp")
    assert resolve_run_mode("dsh", backend="dsh_acp").mode == "service"
    assert resolve_run_mode("dsh", mode="service").human_surface_kind is None


def test_kimi_service_is_explicit_and_provider_bound() -> None:
    """Keep Kimi ACP separate from print mode, the TUI, and passive creation."""

    selected = resolve_run_mode("kimi", mode="service", entrypoint="project")
    assert selected == RunModeSelection("kimi", "service", "kimi_acp", None)
    assert resolve_run_mode("kimi", backend="kimi_acp") == selected
    with pytest.raises(LaunchPlanError, match="require mode 'headless'"):
        resolve_run_mode("kimi", mode="service", entrypoint="passive_headless")
    with pytest.raises(ValueError, match="do not agree"):
        validate_mode_binding("dsh", "service", "kimi_acp")


def test_codex_service_is_explicit_and_provider_bound() -> None:
    """Enable persistent Codex service while retaining the existing defaults."""

    selected = resolve_run_mode("codex", mode="service", entrypoint="project")
    assert selected == RunModeSelection("codex", "service", "codex_app_server", None)
    assert resolve_run_mode("codex", backend="codex_app_server") == selected
    with pytest.raises(LaunchPlanError, match="require mode 'headless'"):
        resolve_run_mode("codex", mode="service", entrypoint="passive_headless")
    with pytest.raises(ValueError, match="do not agree"):
        validate_mode_binding("kimi", "service", "codex_app_server")


@pytest.mark.parametrize("entrypoint", ["project", "runtime"])
def test_kimi_web_is_an_explicit_native_surface(entrypoint: RunModeEntrypoint) -> None:
    """Enable the Web pair independently of the existing Kimi modes."""

    web = resolve_run_mode("kimi", mode="web", entrypoint=entrypoint)
    assert web == RunModeSelection("kimi", "web", "kimi_web", "web")
    assert resolve_run_mode("kimi", backend="kimi_web", entrypoint=entrypoint) == web
    with pytest.raises(ValueError, match="do not agree"):
        validate_mode_binding("dsh", "web", "kimi_web")
    for mode, backend, surface in (
        ("headless", "kimi_headless", None),
        ("service", "kimi_acp", None),
        ("tui", "local_interactive", "terminal"),
    ):
        selected = resolve_run_mode("kimi", mode=mode, entrypoint=entrypoint)
        assert selected.backend == backend and selected.human_surface_kind == surface
