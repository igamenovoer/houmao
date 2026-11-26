"""Exercise native run-mode defaults and qualification across launch entrypoints."""

from __future__ import annotations

import pytest

from houmao.agents.realm_controller.errors import LaunchPlanError
from houmao.agents.realm_controller.models import BackendKind
from houmao.agents.realm_controller.native_surface import NativeSurfaceKind
from houmao.agents.realm_controller.run_modes import (
    RunMode,
    RunModeEntrypoint,
    RunModeSelection,
    resolve_run_mode,
    validate_mode_binding,
)


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
