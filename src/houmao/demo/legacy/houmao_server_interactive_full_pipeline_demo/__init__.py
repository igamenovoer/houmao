"""Public package surface for the interactive full-pipeline demo."""

from importlib import import_module as _import_module
from typing import Any as _Any

from houmao.demo.legacy.houmao_server_interactive_full_pipeline_demo.commands import (
    inspect_demo,
    interrupt_demo,
    load_demo_state,
    load_interrupt_artifacts,
    load_turn_artifacts,
    require_active_state,
    save_demo_state,
    send_turn,
    start_demo,
    stop_demo,
    verify_demo,
)
from houmao.demo.legacy.houmao_server_interactive_full_pipeline_demo.models import (
    CURRENT_RUN_ROOT_FILENAME,
    DEFAULT_AGENT_PROFILE,
    DEFAULT_DEMO_ROOT_DIRNAME,
    DEFAULT_HISTORY_LIMIT,
    DEFAULT_PROVIDER,
    DEFAULT_REQUEST_POLL_INTERVAL_SECONDS,
    DEFAULT_REQUEST_SETTLE_TIMEOUT_SECONDS,
    DEFAULT_WORKTREE_DIRNAME,
    DemoEnvironment,
    DemoInvocation,
    DemoPaths,
    DemoRequestRecord,
    DemoState,
    DemoWorkflowError,
    InspectPayload,
    ManagedAgentHistorySnapshot,
    ManagedAgentSnapshot,
    PROVIDER_CHOICES,
    STALE_STOP_MARKERS,
    StartupPayload,
    StopPayload,
    TerminalSnapshot,
    TurnArtifact,
    VerificationReport,
    VerificationRequestSummary,
    tool_for_provider,
)

_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "main": ("houmao.demo.legacy.houmao_server_interactive_full_pipeline_demo.cli", "main"),
}


def __getattr__(name: str) -> _Any:
    """Resolve lazy package re-exports on first access."""

    if name not in _LAZY_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attribute_name = _LAZY_EXPORTS[name]
    value = getattr(_import_module(module_name), attribute_name)
    globals()[name] = value
    return value


__all__ = [
    "CURRENT_RUN_ROOT_FILENAME",
    "DEFAULT_AGENT_PROFILE",
    "DEFAULT_DEMO_ROOT_DIRNAME",
    "DEFAULT_HISTORY_LIMIT",
    "DEFAULT_PROVIDER",
    "DEFAULT_REQUEST_POLL_INTERVAL_SECONDS",
    "DEFAULT_REQUEST_SETTLE_TIMEOUT_SECONDS",
    "DEFAULT_WORKTREE_DIRNAME",
    "DemoEnvironment",
    "DemoInvocation",
    "DemoPaths",
    "DemoRequestRecord",
    "DemoState",
    "DemoWorkflowError",
    "InspectPayload",
    "ManagedAgentHistorySnapshot",
    "ManagedAgentSnapshot",
    "PROVIDER_CHOICES",
    "STALE_STOP_MARKERS",
    "StartupPayload",
    "StopPayload",
    "TerminalSnapshot",
    "TurnArtifact",
    "VerificationReport",
    "VerificationRequestSummary",
    "inspect_demo",
    "interrupt_demo",
    "load_demo_state",
    "load_interrupt_artifacts",
    "load_turn_artifacts",
    "main",
    "require_active_state",
    "save_demo_state",
    "send_turn",
    "start_demo",
    "stop_demo",
    "tool_for_provider",
    "verify_demo",
]
