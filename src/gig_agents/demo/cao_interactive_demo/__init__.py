"""Public package surface for the interactive CAO demo."""

from importlib import import_module as _import_module
from typing import Any as _Any

from gig_agents.demo.cao_interactive_demo.commands import (
    inspect_demo,
    load_control_records,
    load_demo_state,
    load_turn_records,
    require_active_state,
    save_demo_state,
    send_control_input,
    send_turn,
    start_demo,
    stop_demo,
    verify_demo,
)
from gig_agents.demo.cao_interactive_demo.models import (
    CURRENT_RUN_ROOT_FILENAME,
    DEFAULT_AGENT_NAME,
    DEFAULT_CAO_SERVICE_NAME,
    DEFAULT_CAO_STOP_CLEAR_POLL_SECONDS,
    DEFAULT_CAO_STOP_CLEAR_TIMEOUT_SECONDS,
    DEFAULT_CONFIG_PROFILE,
    DEFAULT_CREDENTIAL_PROFILE,
    DEFAULT_DEMO_ROOT_DIRNAME,
    DEFAULT_LIVE_CAO_TIMEOUT_SECONDS,
    DEFAULT_ROLE_NAME,
    DEFAULT_SKILLS,
    DEFAULT_STARTUP_HEARTBEAT_INITIAL_DELAY_SECONDS,
    DEFAULT_STARTUP_HEARTBEAT_INTERVAL_SECONDS,
    DEFAULT_TERMINAL_LOG_RELATIVE_DIR,
    DEFAULT_TIMEOUT_SECONDS,
    DEFAULT_TOOL_NAME,
    DEFAULT_WORKTREE_DIRNAME,
    EMPTY_RESPONSE_ERROR,
    FIXED_CAO_BASE_URL,
    PORT_LISTEN_STATE,
    STALE_STOP_MARKERS,
    TEST_LOOPBACK_PORT_LISTENING_ENV,
    UNKNOWN_CLAUDE_CODE_STATE,
    CommandResult,
    CommandRunner,
    ControlActionSummary,
    ControlInputRecord,
    DemoEnvironment,
    DemoInvocation,
    DemoPaths,
    DemoState,
    DemoWorkflowError,
    OutputTextTailResult,
    ProgressWriter,
    TurnRecord,
    VerificationReport,
    VerificationTurnSummary,
)
from gig_agents.demo.cao_interactive_demo.runtime import run_subprocess_command

_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "main": ("gig_agents.demo.cao_interactive_demo.cli", "main"),
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
    "DEFAULT_AGENT_NAME",
    "DEFAULT_CAO_SERVICE_NAME",
    "DEFAULT_CAO_STOP_CLEAR_POLL_SECONDS",
    "DEFAULT_CAO_STOP_CLEAR_TIMEOUT_SECONDS",
    "DEFAULT_CONFIG_PROFILE",
    "DEFAULT_CREDENTIAL_PROFILE",
    "DEFAULT_DEMO_ROOT_DIRNAME",
    "DEFAULT_LIVE_CAO_TIMEOUT_SECONDS",
    "DEFAULT_ROLE_NAME",
    "DEFAULT_SKILLS",
    "DEFAULT_STARTUP_HEARTBEAT_INITIAL_DELAY_SECONDS",
    "DEFAULT_STARTUP_HEARTBEAT_INTERVAL_SECONDS",
    "DEFAULT_TERMINAL_LOG_RELATIVE_DIR",
    "DEFAULT_TIMEOUT_SECONDS",
    "DEFAULT_TOOL_NAME",
    "DEFAULT_WORKTREE_DIRNAME",
    "EMPTY_RESPONSE_ERROR",
    "FIXED_CAO_BASE_URL",
    "PORT_LISTEN_STATE",
    "STALE_STOP_MARKERS",
    "TEST_LOOPBACK_PORT_LISTENING_ENV",
    "UNKNOWN_CLAUDE_CODE_STATE",
    "CommandResult",
    "CommandRunner",
    "ControlActionSummary",
    "ControlInputRecord",
    "DemoEnvironment",
    "DemoInvocation",
    "DemoPaths",
    "DemoState",
    "DemoWorkflowError",
    "OutputTextTailResult",
    "ProgressWriter",
    "TurnRecord",
    "VerificationReport",
    "VerificationTurnSummary",
    "inspect_demo",
    "load_control_records",
    "load_demo_state",
    "load_turn_records",
    "main",
    "require_active_state",
    "run_subprocess_command",
    "save_demo_state",
    "send_control_input",
    "send_turn",
    "start_demo",
    "stop_demo",
    "verify_demo",
]
