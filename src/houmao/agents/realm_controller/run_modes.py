"""Resolve an agent's native entrypoint before preparing its execution state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, Literal

from houmao.agents.realm_controller.errors import LaunchPlanError
from houmao.agents.realm_controller.native_surface import NativeSurfaceKind

if TYPE_CHECKING:
    from houmao.agents.realm_controller.models import BackendKind


RunMode = Literal["headless", "service", "tui", "web"]
RunModeEntrypoint = Literal["project", "runtime", "passive_headless"]
RUN_MODES: Final[tuple[RunMode, ...]] = ("headless", "service", "tui", "web")

_TOOL_MODE_BACKENDS: Final[dict[str, dict[RunMode, BackendKind]]] = {
    "claude": {"headless": "claude_headless", "tui": "local_interactive"},
    "codex": {
        "headless": "codex_headless",
        "service": "codex_app_server",
        "tui": "local_interactive",
    },
    "dsh": {"headless": "dsh_headless", "service": "dsh_acp", "web": "dsh_web"},
    "kimi": {
        "headless": "kimi_headless",
        "service": "kimi_acp",
        "tui": "local_interactive",
        "web": "kimi_web",
    },
}
_MODE_BY_BACKEND: Final[dict[BackendKind, RunMode]] = {
    backend: mode for modes in _TOOL_MODE_BACKENDS.values() for mode, backend in modes.items()
} | {"cao_rest": "tui", "houmao_server_rest": "tui"}
_COMPATIBILITY_TUI_TOOLS: Final[dict[str, frozenset[str]]] = {
    "cao_rest": frozenset({"claude", "codex", "kimi"}),
    "houmao_server_rest": frozenset({"claude", "codex", "kimi", "kiro_cli", "q_cli"}),
}


@dataclass(frozen=True)
class RunModeSelection:
    """A qualified native entrypoint and the human surface it is expected to expose."""

    tool: str
    mode: RunMode
    backend: BackendKind
    human_surface_kind: NativeSurfaceKind | None


def mode_for_backend(backend: BackendKind) -> RunMode:
    """Return the mode belonging to a known backend identity."""

    try:
        return _MODE_BY_BACKEND[backend]
    except KeyError as exc:
        raise ValueError(f"Unknown runtime backend {backend!r}") from exc


def human_surface_for_mode(mode: RunMode) -> NativeSurfaceKind | None:
    """Return the kind of human surface associated with the selected entrypoint."""

    if mode == "tui":
        return "terminal"
    if mode == "web":
        return "web"
    return None


def validate_mode_binding(tool: str, mode: RunMode, backend: BackendKind) -> None:
    """Require a coherent tool, mode, and backend identity for a stored record."""

    if mode_for_backend(backend) == mode and (
        _TOOL_MODE_BACKENDS.get(tool, {}).get(mode) == backend
        or tool in _COMPATIBILITY_TUI_TOOLS.get(backend, ())
    ):
        return
    raise ValueError(f"Tool {tool!r}, mode {mode!r}, and backend {backend!r} do not agree.")


def resolve_run_mode(
    tool: str,
    *,
    mode: RunMode | None = None,
    backend: BackendKind | None = None,
    entrypoint: RunModeEntrypoint = "runtime",
) -> RunModeSelection:
    """Resolve a mode or explicit backend against the qualified launch matrix."""

    tool_modes = _TOOL_MODE_BACKENDS.get(tool)
    if tool_modes is None:
        raise LaunchPlanError(f"No qualified managed run modes for tool {tool!r}.")
    if entrypoint == "passive_headless":
        if mode is not None and mode != "headless":
            raise LaunchPlanError("Passive headless launches require mode 'headless'.")
        mode = "headless"
    if backend is not None:
        try:
            backend_mode = mode_for_backend(backend)
            validate_mode_binding(tool, backend_mode, backend)
        except ValueError as exc:
            raise LaunchPlanError(str(exc)) from exc
        if mode is not None and mode != backend_mode:
            raise LaunchPlanError(
                f"Requested mode {mode!r} conflicts with backend {backend!r} "
                f"in mode {backend_mode!r}."
            )
        mode = backend_mode
    if mode is None:
        if tool == "dsh":
            mode = "web"
        else:
            mode = "tui" if entrypoint == "project" else "headless"
    selected_backend = backend if backend is not None else tool_modes.get(mode)
    if selected_backend is None:
        supported_modes = ", ".join(tool_modes)
        raise LaunchPlanError(
            f"Tool {tool!r} does not support mode {mode!r}. Supported modes: {supported_modes}."
        )
    return RunModeSelection(
        tool=tool,
        mode=mode,
        backend=selected_backend,
        human_surface_kind=human_surface_for_mode(mode),
    )
