"""Shared data models and constants for the interactive CAO demo."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal, Sequence, TypeAlias, TypeVar

from pydantic import BaseModel, ConfigDict, field_validator

FIXED_CAO_BASE_URL = "http://127.0.0.1:9889"
DEFAULT_CAO_SERVICE_NAME = "cli-agent-orchestrator"
DEFAULT_DEMO_ROOT_DIRNAME = "cao-interactive-full-pipeline-demo"
DEFAULT_ROLE_NAME = "gpu-kernel-coder"
DEFAULT_WORKTREE_DIRNAME = "wktree"
DEFAULT_TIMEOUT_SECONDS = 180.0
DEFAULT_BRAIN_RECIPE_SELECTOR = "claude/gpu-kernel-coder-default"
BRAIN_RECIPES_RELATIVE_DIR = Path("brains") / "brain-recipes"
DEFAULT_LIVE_CAO_TIMEOUT_SECONDS = 5.0
DEFAULT_STARTUP_HEARTBEAT_INITIAL_DELAY_SECONDS = 2.0
DEFAULT_STARTUP_HEARTBEAT_INTERVAL_SECONDS = 5.0
DEFAULT_TERMINAL_LOG_RELATIVE_DIR = Path(".aws") / "cli-agent-orchestrator" / "logs" / "terminal"
DEFAULT_CAO_STOP_CLEAR_TIMEOUT_SECONDS = 2.0
DEFAULT_CAO_STOP_CLEAR_POLL_SECONDS = 0.1
PORT_LISTEN_STATE = "0A"
CURRENT_RUN_ROOT_FILENAME = "current_run_root.txt"
EMPTY_RESPONSE_ERROR = "interactive CAO turn returned an empty response"
UNKNOWN_TOOL_STATE = "unknown"
TEST_LOOPBACK_PORT_LISTENING_ENV = "AGENTSYS_TEST_INTERACTIVE_DEMO_FIXED_PORT_LISTENING"
STALE_STOP_MARKERS: tuple[str, ...] = (
    "agent not found",
    "connection refused",
    "does not exist",
    "manifest pointer missing",
    "manifest pointer stale",
    "no such session",
    "not found",
    "404",
)


class DemoWorkflowError(RuntimeError):
    """Raised when the interactive demo workflow cannot proceed safely."""


class _StrictModel(BaseModel):
    """Shared strict model config for persisted demo artifacts."""

    model_config = ConfigDict(extra="forbid", strict=True)


class DemoState(_StrictModel):
    """Persisted lifecycle state for the interactive demo."""

    active: bool
    agent_identity: str
    tool: str
    variant_id: str
    brain_recipe: str
    session_manifest: str
    session_name: str
    tmux_target: str
    terminal_id: str
    terminal_log_path: str
    runtime_root: str
    workspace_dir: str
    brain_home: str
    brain_manifest: str
    cao_base_url: str
    cao_profile_store: str
    launcher_config_path: str
    updated_at: str
    turn_count: int = 0
    control_count: int = 0

    @field_validator(
        "agent_identity",
        "tool",
        "variant_id",
        "brain_recipe",
        "session_manifest",
        "session_name",
        "tmux_target",
        "terminal_id",
        "terminal_log_path",
        "runtime_root",
        "workspace_dir",
        "brain_home",
        "brain_manifest",
        "cao_base_url",
        "cao_profile_store",
        "launcher_config_path",
        "updated_at",
    )
    @classmethod
    def _not_blank(cls, value: str) -> str:
        """Require non-empty string payload fields."""

        if not value.strip():
            raise ValueError("must not be empty")
        return value


class TurnRecord(_StrictModel):
    """Persisted artifact for one `send-turn` execution."""

    turn_index: int
    agent_identity: str
    prompt: str
    started_at_utc: str
    completed_at_utc: str
    exit_status: int
    response_text: str
    response_text_source: str = "done_message"
    events: list[dict[str, object]]
    stdout_path: str
    stderr_path: str

    @field_validator(
        "agent_identity",
        "prompt",
        "started_at_utc",
        "completed_at_utc",
        "response_text_source",
        "stdout_path",
        "stderr_path",
    )
    @classmethod
    def _record_string_not_blank(cls, value: str) -> str:
        """Require non-empty turn record string fields."""

        if not value.strip():
            raise ValueError("must not be empty")
        return value


class ControlActionSummary(_StrictModel):
    """Stable summary of one runtime control-input result."""

    status: Literal["ok", "error"]
    action: Literal["control_input"]
    detail: str

    @field_validator("detail")
    @classmethod
    def _control_detail_not_blank(cls, value: str) -> str:
        """Require non-empty control-result detail text."""

        if not value.strip():
            raise ValueError("must not be empty")
        return value


class ControlInputRecord(_StrictModel):
    """Persisted artifact for one `send-keys` execution."""

    control_index: int
    agent_identity: str
    key_stream: str
    as_raw_string: bool
    started_at_utc: str
    completed_at_utc: str
    exit_status: int
    result: ControlActionSummary
    stdout_path: str
    stderr_path: str

    @field_validator(
        "agent_identity",
        "key_stream",
        "started_at_utc",
        "completed_at_utc",
        "stdout_path",
        "stderr_path",
    )
    @classmethod
    def _control_record_string_not_blank(cls, value: str) -> str:
        """Require non-empty control record string fields."""

        if not value.strip():
            raise ValueError("must not be empty")
        return value


class VerificationTurnSummary(_StrictModel):
    """Stable turn summary embedded in verification reports."""

    turn_index: int
    agent_identity: str
    exit_status: int
    response_text: str
    response_text_source: str = "done_message"
    response_text_present: bool

    @field_validator("agent_identity", "response_text_source")
    @classmethod
    def _summary_string_not_blank(cls, value: str) -> str:
        """Require non-empty verification turn string fields."""

        if not value.strip():
            raise ValueError("must not be empty")
        return value


class VerificationReport(_StrictModel):
    """Machine-readable verification report for the interactive workflow."""

    status: str
    backend: str
    tool: str
    variant_id: str
    brain_recipe: str
    cao_base_url: str
    agent_identity: str
    unique_agent_identity_count: int
    turn_count: int
    turns: list[VerificationTurnSummary]
    session_manifest: str
    workspace_dir: str
    tmux_target: str
    terminal_id: str
    terminal_log_path: str
    generated_at_utc: str

    @field_validator(
        "status",
        "backend",
        "tool",
        "variant_id",
        "brain_recipe",
        "cao_base_url",
        "agent_identity",
        "session_manifest",
        "workspace_dir",
        "tmux_target",
        "terminal_id",
        "terminal_log_path",
        "generated_at_utc",
    )
    @classmethod
    def _report_string_not_blank(cls, value: str) -> str:
        """Require non-empty verification report string fields."""

        if not value.strip():
            raise ValueError("must not be empty")
        return value


@dataclass(frozen=True)
class DemoPaths:
    """Resolved filesystem layout for the interactive demo workspace."""

    workspace_root: Path
    runtime_root: Path
    logs_dir: Path
    turns_dir: Path
    controls_dir: Path
    state_path: Path
    report_path: Path
    launcher_config_path: Path

    @classmethod
    def from_workspace_root(cls, workspace_root: Path) -> "DemoPaths":
        """Create demo path layout from the workspace root."""

        root = workspace_root.expanduser().resolve()
        return cls(
            workspace_root=root,
            runtime_root=root / "runtime",
            logs_dir=root / "logs",
            turns_dir=root / "turns",
            controls_dir=root / "controls",
            state_path=root / "state.json",
            report_path=root / "report.json",
            launcher_config_path=root / "cao-server-launcher.toml",
        )


@dataclass(frozen=True)
class DemoEnvironment:
    """Resolved operator configuration for one CLI invocation."""

    repo_root: Path
    demo_base_root: Path
    current_run_root_path: Path
    agent_def_dir: Path
    launcher_home_dir: Path
    workdir: Path
    role_name: str
    timeout_seconds: float
    yes_to_all: bool
    provision_worktree: bool


@dataclass(frozen=True)
class DemoInvocation:
    """Resolved path and environment inputs for one CLI command."""

    paths: DemoPaths
    env: DemoEnvironment


@dataclass(frozen=True)
class CommandResult:
    """Captured subprocess result plus persisted log locations."""

    args: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str
    stdout_path: Path
    stderr_path: Path


@dataclass(frozen=True)
class OutputTextTailResult:
    """Best-effort clean output-tail payload for `inspect`."""

    output_text_tail: str | None
    note: str | None


CommandRunner: TypeAlias = Callable[
    [Sequence[str], Path, Path, Path, float],
    CommandResult,
]
ProgressWriter: TypeAlias = Callable[[str], None]
_ModelT = TypeVar("_ModelT", bound="_StrictModel")
