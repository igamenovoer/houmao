"""Typed models and constants for the Houmao-server interactive demo."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from houmao.agents.realm_controller.boundary_models import HoumaoServerSectionV1
from houmao.server.models import HoumaoManagedAgentRequestAcceptedResponse


DEFAULT_DEMO_ROOT_DIRNAME = "houmao-server-interactive-full-pipeline-demo"
DEFAULT_WORKTREE_DIRNAME = "wktree"
CURRENT_RUN_ROOT_FILENAME = "current_run_root.txt"
DEFAULT_PROVIDER = "claude_code"
DEFAULT_AGENT_PROFILE = "gpu-kernel-coder"
DEFAULT_SERVER_START_TIMEOUT_SECONDS = 20.0
DEFAULT_REQUEST_SETTLE_TIMEOUT_SECONDS = 15.0
DEFAULT_REQUEST_POLL_INTERVAL_SECONDS = 0.25
DEFAULT_SERVER_STOP_TIMEOUT_SECONDS = 10.0
DEFAULT_HISTORY_LIMIT = 20
PROVIDER_CHOICES = ("claude_code", "codex")
STALE_STOP_MARKERS: tuple[str, ...] = (
    "404",
    "connection refused",
    "does not exist",
    "not found",
    "no such session",
    "session missing",
)


class DemoWorkflowError(RuntimeError):
    """Raised when the interactive demo cannot proceed safely."""


class _StrictModel(BaseModel):
    """Shared strict model configuration for demo artifacts."""

    model_config = ConfigDict(extra="forbid", strict=True)


class ManagedAgentSnapshot(_StrictModel):
    """Sanitized managed-agent state snapshot."""

    tracked_agent_id: str
    transport: str
    tool: str
    session_name: str | None = None
    terminal_id: str | None = None
    manifest_path: str | None = None
    availability: str
    turn_phase: str
    active_turn_id: str | None = None
    last_turn_result: str
    last_turn_id: str | None = None
    last_turn_index: int | None = None
    last_turn_updated_at_utc: str | None = None
    detail_transport: str
    terminal_state_route: str | None = None
    terminal_history_route: str | None = None
    parsed_surface_present: bool | None = None
    ready_posture: str | None = None
    stable: bool | None = None
    stable_for_seconds: float | None = None
    can_accept_prompt_now: bool | None = None
    interruptible: bool | None = None
    diagnostic_count: int = 0
    gateway_queue_depth: int | None = None

    @field_validator(
        "tracked_agent_id",
        "transport",
        "tool",
        "session_name",
        "terminal_id",
        "manifest_path",
        "availability",
        "turn_phase",
        "active_turn_id",
        "last_turn_result",
        "last_turn_id",
        "last_turn_updated_at_utc",
        "detail_transport",
        "terminal_state_route",
        "terminal_history_route",
        "ready_posture",
    )
    @classmethod
    def _optional_not_blank(cls, value: str | None) -> str | None:
        """Require present strings to stay non-empty."""

        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped

    @field_validator("diagnostic_count")
    @classmethod
    def _non_negative_diagnostics(cls, value: int) -> int:
        """Require non-negative diagnostic counters."""

        if value < 0:
            raise ValueError("must be >= 0")
        return value

    @field_validator("gateway_queue_depth")
    @classmethod
    def _optional_non_negative_queue_depth(cls, value: int | None) -> int | None:
        """Require optional queue depth values to be non-negative."""

        if value is None:
            return None
        if value < 0:
            raise ValueError("must be >= 0")
        return value

    @field_validator("stable_for_seconds")
    @classmethod
    def _optional_non_negative_stability(cls, value: float | None) -> float | None:
        """Require optional stability durations to be non-negative."""

        if value is None:
            return None
        if value < 0.0:
            raise ValueError("must be >= 0")
        return value


class ManagedAgentHistorySnapshot(_StrictModel):
    """Sanitized managed-agent history summary."""

    entry_count: int
    latest_recorded_at_utc: str | None = None
    latest_summary: str | None = None
    latest_turn_phase: str | None = None
    latest_last_turn_result: str | None = None

    @field_validator(
        "latest_recorded_at_utc",
        "latest_summary",
        "latest_turn_phase",
        "latest_last_turn_result",
    )
    @classmethod
    def _optional_not_blank(cls, value: str | None) -> str | None:
        """Require present strings to stay non-empty."""

        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped

    @field_validator("entry_count")
    @classmethod
    def _non_negative_entry_count(cls, value: int) -> int:
        """Require non-negative history counts."""

        if value < 0:
            raise ValueError("must be >= 0")
        return value


class TerminalSnapshot(_StrictModel):
    """Sanitized tracked-terminal summary."""

    terminal_id: str
    parser_family: str | None = None
    availability: str | None = None
    business_state: str | None = None
    input_mode: str | None = None
    ui_context: str | None = None
    parsed_surface_present: bool
    ready_posture: str
    turn_phase: str
    last_turn_result: str
    stable: bool
    stable_for_seconds: float
    recent_transition_count: int
    probe_captured_text_length: int | None = None

    @field_validator(
        "terminal_id",
        "parser_family",
        "availability",
        "business_state",
        "input_mode",
        "ui_context",
        "ready_posture",
        "turn_phase",
        "last_turn_result",
    )
    @classmethod
    def _optional_not_blank(cls, value: str | None) -> str | None:
        """Require present strings to stay non-empty."""

        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped

    @field_validator("stable_for_seconds")
    @classmethod
    def _non_negative_stability(cls, value: float) -> float:
        """Require non-negative stability durations."""

        if value < 0.0:
            raise ValueError("must be >= 0")
        return value

    @field_validator("recent_transition_count", "probe_captured_text_length")
    @classmethod
    def _optional_non_negative_count(cls, value: int | None) -> int | None:
        """Require optional counters to be non-negative."""

        if value is None:
            return None
        if value < 0:
            raise ValueError("must be >= 0")
        return value


class DemoState(_StrictModel):
    """Persisted lifecycle state for the interactive demo."""

    active: bool
    provider: str
    tool: str
    agent_profile: str
    variant_id: str
    api_base_url: str
    agent_identity: str
    agent_ref: str
    requested_session_name: str | None = None
    session_manifest_path: str
    session_root: str
    session_name: str
    terminal_id: str
    tracked_agent_id: str | None = None
    runtime_root: str
    registry_root: str
    jobs_root: str
    workspace_dir: str
    workdir: str
    server_home_dir: str
    server_runtime_root: str
    server_pid: int
    server_stdout_log_path: str
    server_stderr_log_path: str
    install_profile_source: str
    install_stdout_log_path: str
    install_stderr_log_path: str
    houmao_server: HoumaoServerSectionV1
    updated_at: str
    prompt_turn_count: int = 0
    interrupt_count: int = 0

    @field_validator(
        "provider",
        "tool",
        "agent_profile",
        "variant_id",
        "api_base_url",
        "agent_identity",
        "agent_ref",
        "requested_session_name",
        "session_manifest_path",
        "session_root",
        "session_name",
        "terminal_id",
        "tracked_agent_id",
        "runtime_root",
        "registry_root",
        "jobs_root",
        "workspace_dir",
        "workdir",
        "server_home_dir",
        "server_runtime_root",
        "server_stdout_log_path",
        "server_stderr_log_path",
        "install_profile_source",
        "install_stdout_log_path",
        "install_stderr_log_path",
        "updated_at",
    )
    @classmethod
    def _optional_not_blank(cls, value: str | None) -> str | None:
        """Require present strings to stay non-empty."""

        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped

    @field_validator("server_pid", "prompt_turn_count", "interrupt_count")
    @classmethod
    def _non_negative_ints(cls, value: int) -> int:
        """Require non-negative counters and process ids."""

        if value < 0:
            raise ValueError("must be >= 0")
        return value

    @model_validator(mode="after")
    def _validate_agent_ref_contract(self) -> "DemoState":
        """Require the persisted v1 `agent_ref` to match `session_name`."""

        if self.agent_ref != self.session_name:
            raise ValueError("agent_ref must match session_name for the v1 route contract")
        return self


class StartupPayload(_StrictModel):
    """Machine-readable startup payload."""

    state: DemoState
    replaced_previous_session_name: str | None = None

    @field_validator("replaced_previous_session_name")
    @classmethod
    def _optional_not_blank(cls, value: str | None) -> str | None:
        """Require present strings to stay non-empty."""

        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped


class InspectPayload(_StrictModel):
    """Machine-readable inspect payload."""

    active: bool
    provider: str
    tool: str
    agent_profile: str
    variant_id: str
    api_base_url: str
    agent_identity: str
    agent_ref: str
    session_name: str
    terminal_id: str
    tracked_agent_id: str | None = None
    workspace_dir: str
    workdir: str
    session_manifest_path: str
    updated_at: str
    managed_agent: ManagedAgentSnapshot | None = None
    history: ManagedAgentHistorySnapshot | None = None
    terminal: TerminalSnapshot | None = None
    dialog_tail: str | None = None
    dialog_tail_chars_requested: int | None = None
    live_error: str | None = None

    @field_validator(
        "provider",
        "tool",
        "agent_profile",
        "variant_id",
        "api_base_url",
        "agent_identity",
        "agent_ref",
        "session_name",
        "terminal_id",
        "tracked_agent_id",
        "workspace_dir",
        "workdir",
        "session_manifest_path",
        "updated_at",
        "dialog_tail",
        "live_error",
    )
    @classmethod
    def _optional_not_blank(cls, value: str | None) -> str | None:
        """Require present strings to stay non-empty."""

        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped

    @field_validator("dialog_tail_chars_requested")
    @classmethod
    def _optional_positive_chars(cls, value: int | None) -> int | None:
        """Require positive dialog-tail lengths when requested."""

        if value is None:
            return None
        if value <= 0:
            raise ValueError("must be > 0")
        return value


class TurnArtifact(_StrictModel):
    """Recorded artifact for one prompt or interrupt request."""

    artifact_kind: Literal["send-turn", "interrupt"]
    sequence_number: int
    request_kind: Literal["submit_prompt", "interrupt"]
    prompt: str | None = None
    agent_ref: str
    tracked_agent_id: str
    requested_at_utc: str
    settled_at_utc: str
    poll_iterations: int
    state_change_observed: bool
    request: HoumaoManagedAgentRequestAcceptedResponse
    state_before: ManagedAgentSnapshot
    state_after: ManagedAgentSnapshot
    history_after: ManagedAgentHistorySnapshot
    terminal_after: TerminalSnapshot | None = None

    @field_validator(
        "prompt",
        "agent_ref",
        "tracked_agent_id",
        "requested_at_utc",
        "settled_at_utc",
    )
    @classmethod
    def _optional_not_blank(cls, value: str | None) -> str | None:
        """Require present strings to stay non-empty."""

        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped

    @field_validator("sequence_number", "poll_iterations")
    @classmethod
    def _positive_counts(cls, value: int) -> int:
        """Require positive sequence counters."""

        if value <= 0:
            raise ValueError("must be > 0")
        return value


class VerificationRequestSummary(_StrictModel):
    """Stable request summary embedded in verification reports."""

    artifact_kind: Literal["send-turn", "interrupt"]
    sequence_number: int
    request_kind: Literal["submit_prompt", "interrupt"]
    request_id: str
    tracked_agent_id: str
    prompt_present: bool
    state_change_observed: bool
    after_turn_phase: str
    after_last_turn_result: str
    after_last_turn_id: str | None = None
    after_last_turn_index: int | None = None
    history_entry_count: int

    @field_validator(
        "request_id",
        "tracked_agent_id",
        "after_turn_phase",
        "after_last_turn_result",
        "after_last_turn_id",
    )
    @classmethod
    def _optional_not_blank(cls, value: str | None) -> str | None:
        """Require present strings to stay non-empty."""

        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped

    @field_validator("sequence_number")
    @classmethod
    def _positive_sequence(cls, value: int) -> int:
        """Require positive sequence counters."""

        if value <= 0:
            raise ValueError("must be > 0")
        return value

    @field_validator("history_entry_count")
    @classmethod
    def _non_negative_history_count(cls, value: int) -> int:
        """Require non-negative history counts."""

        if value < 0:
            raise ValueError("must be >= 0")
        return value


class VerificationReport(_StrictModel):
    """Stable verification report for the interactive workflow."""

    status: Literal["ok"]
    backend: Literal["houmao_server_rest"] = "houmao_server_rest"
    evidence_source: Literal["live_server", "captured_artifacts"]
    provider: str
    tool: str
    agent_profile: str
    variant_id: str
    api_base_url: str
    agent_identity: str
    agent_ref: str
    session_name: str
    terminal_id: str
    tracked_agent_id: str | None = None
    session_manifest_path: str
    workspace_dir: str
    workdir: str
    accepted_prompt_count: int
    accepted_interrupt_count: int
    request_summaries: list[VerificationRequestSummary]
    current_managed_agent: ManagedAgentSnapshot
    current_history: ManagedAgentHistorySnapshot
    current_terminal: TerminalSnapshot | None = None
    generated_at_utc: str

    @field_validator(
        "provider",
        "tool",
        "agent_profile",
        "variant_id",
        "api_base_url",
        "agent_identity",
        "agent_ref",
        "session_name",
        "terminal_id",
        "tracked_agent_id",
        "session_manifest_path",
        "workspace_dir",
        "workdir",
        "generated_at_utc",
    )
    @classmethod
    def _optional_not_blank(cls, value: str | None) -> str | None:
        """Require present strings to stay non-empty."""

        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped

    @field_validator("accepted_prompt_count", "accepted_interrupt_count")
    @classmethod
    def _non_negative_counts(cls, value: int) -> int:
        """Require non-negative request counters."""

        if value < 0:
            raise ValueError("must be >= 0")
        return value


class StopPayload(_StrictModel):
    """Machine-readable stop payload."""

    state: DemoState
    session_delete_status: str
    stale_session_tolerated: bool
    server_stop_status: str

    @field_validator("session_delete_status", "server_stop_status")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        """Require non-empty status strings."""

        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped


@dataclass(frozen=True)
class DemoPaths:
    """Resolved filesystem layout for one interactive demo workspace."""

    workspace_root: Path
    runtime_root: Path
    registry_root: Path
    jobs_root: Path
    logs_dir: Path
    turns_dir: Path
    interrupts_dir: Path
    state_path: Path
    report_path: Path
    server_home_dir: Path
    server_runtime_root: Path
    workdir: Path

    @classmethod
    def from_workspace_root(cls, workspace_root: Path) -> "DemoPaths":
        """Create the canonical path layout from the selected workspace root."""

        root = workspace_root.expanduser().resolve()
        return cls(
            workspace_root=root,
            runtime_root=root / "runtime",
            registry_root=root / "registry",
            jobs_root=root / "jobs",
            logs_dir=root / "logs",
            turns_dir=root / "turns",
            interrupts_dir=root / "interrupts",
            state_path=root / "state.json",
            report_path=root / "report.json",
            server_home_dir=root / "server" / "home",
            server_runtime_root=root / "server" / "runtime",
            workdir=root / DEFAULT_WORKTREE_DIRNAME,
        )


@dataclass(frozen=True)
class DemoEnvironment:
    """Resolved operator configuration for one CLI invocation."""

    repo_root: Path
    demo_base_root: Path
    current_run_root_path: Path
    provision_worktree: bool
    server_start_timeout_seconds: float
    request_settle_timeout_seconds: float
    request_poll_interval_seconds: float
    server_stop_timeout_seconds: float


@dataclass(frozen=True)
class DemoInvocation:
    """Resolved path and environment inputs for one CLI invocation."""

    paths: DemoPaths
    env: DemoEnvironment


def tool_for_provider(provider: str) -> str:
    """Return the stable tool label for one supported provider."""

    if provider == "claude_code":
        return "claude"
    if provider == "codex":
        return "codex"
    raise DemoWorkflowError(
        f"Unsupported provider `{provider}`. Expected one of: {', '.join(PROVIDER_CHOICES)}."
    )
