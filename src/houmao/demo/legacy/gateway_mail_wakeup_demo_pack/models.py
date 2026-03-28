"""Typed models and filesystem layout helpers for the gateway wake-up demo pack."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

PACK_NAME = "gateway-mail-wakeup-demo-pack"
DEMO_STATE_SCHEMA_VERSION = 1
REPORT_SCHEMA_VERSION = 1
DEFAULT_DEMO_OUTPUT_DIR_RELATIVE = f"scripts/demo/{PACK_NAME}/outputs"
DEFAULT_PARAMETERS_RELATIVE = f"scripts/demo/{PACK_NAME}/inputs/demo_parameters.json"
DEFAULT_EXPECTED_REPORT_RELATIVE = f"scripts/demo/{PACK_NAME}/expected_report/report.json"
DEFAULT_AGENT_DEF_DIR_RELATIVE = "tests/fixtures/agents"
DEFAULT_COMMAND_TIMEOUT_SECONDS = 180.0
DEFAULT_NOTIFIER_INTERVAL_SECONDS = 1
DEFAULT_IDLE_TIMEOUT_SECONDS = 180.0
DEFAULT_OUTPUT_TIMEOUT_SECONDS = 180.0

SupportedTool = Literal["claude", "codex"]


class _DemoModel(BaseModel):
    """Base model for strict demo-pack payloads."""

    model_config = ConfigDict(extra="forbid")


class ToolParameters(_DemoModel):
    """Tracked runtime configuration for one supported tool lane."""

    selector: str
    provider: str
    agent_name_prefix: str
    session_name_prefix: str
    mailbox_principal_id: str
    mailbox_address: str

    @field_validator(
        "selector",
        "provider",
        "agent_name_prefix",
        "session_name_prefix",
        "mailbox_principal_id",
        "mailbox_address",
    )
    @classmethod
    def _validate_non_empty_string(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped


class GatewayParameters(_DemoModel):
    """Tracked gateway listener defaults."""

    host: Literal["127.0.0.1", "0.0.0.0"] = "127.0.0.1"
    notifier_interval_seconds: int = DEFAULT_NOTIFIER_INTERVAL_SECONDS

    @field_validator("notifier_interval_seconds")
    @classmethod
    def _validate_positive_int(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("must be > 0")
        return value


class AutomaticParameters(_DemoModel):
    """Tracked automatic-flow defaults."""

    idle_timeout_seconds: float = DEFAULT_IDLE_TIMEOUT_SECONDS
    output_timeout_seconds: float = DEFAULT_OUTPUT_TIMEOUT_SECONDS
    output_file_relative_path: Path = Path("outputs/wakeup-time.txt")

    @field_validator("idle_timeout_seconds", "output_timeout_seconds")
    @classmethod
    def _validate_positive_float(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("must be > 0")
        return value


class DeliveryParameters(_DemoModel):
    """Tracked delivery sender identity and canonical body template."""

    sender_principal_id: str
    sender_address: str
    subject: str
    body_file: Path

    @field_validator("sender_principal_id", "sender_address", "subject")
    @classmethod
    def _validate_non_empty_string(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped


class DemoParameters(_DemoModel):
    """Tracked operator-facing defaults for the demo pack."""

    schema_version: int = 1
    demo_id: str = PACK_NAME
    agent_def_dir: Path = Path(DEFAULT_AGENT_DEF_DIR_RELATIVE)
    project_fixture: Path = Path("tests/fixtures/dummy-projects/mailbox-demo-python")
    command_timeout_seconds: float = DEFAULT_COMMAND_TIMEOUT_SECONDS
    gateway: GatewayParameters = Field(default_factory=GatewayParameters)
    automatic: AutomaticParameters = Field(default_factory=AutomaticParameters)
    delivery: DeliveryParameters
    tools: dict[SupportedTool, ToolParameters]

    @field_validator("schema_version")
    @classmethod
    def _validate_schema_version(cls, value: int) -> int:
        if value != 1:
            raise ValueError("demo parameters must use schema_version=1")
        return value

    @field_validator("demo_id")
    @classmethod
    def _validate_demo_id(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped

    @field_validator("command_timeout_seconds")
    @classmethod
    def _validate_command_timeout(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("must be > 0")
        return value

    @model_validator(mode="after")
    def _validate_tools(self) -> "DemoParameters":
        expected = {"claude", "codex"}
        if set(self.tools.keys()) != expected:
            raise ValueError("tools must include exactly `claude` and `codex`")
        return self

    def tool_parameters(self, *, tool: SupportedTool) -> ToolParameters:
        """Return the tracked config for one selected tool."""

        return self.tools[tool]


@dataclass(frozen=True)
class DemoPaths:
    """Resolved filesystem layout rooted under one selected output directory."""

    output_root: Path
    control_dir: Path
    logs_dir: Path
    runtime_root: Path
    registry_root: Path
    mailbox_root: Path
    jobs_root: Path
    deliveries_dir: Path
    project_dir: Path
    outputs_dir: Path
    evidence_dir: Path
    state_path: Path
    mailbox_init_path: Path
    launch_path: Path
    agent_show_path: Path
    agent_state_path: Path
    mailbox_register_path: Path
    gateway_attach_path: Path
    notifier_enable_path: Path
    ready_wait_path: Path
    inspect_path: Path
    report_path: Path
    sanitized_report_path: Path

    @classmethod
    def from_output_root(cls, *, output_root: Path) -> "DemoPaths":
        """Build the canonical demo layout for one selected output root."""

        resolved_output_root = output_root.resolve()
        control_dir = resolved_output_root / "control"
        return cls(
            output_root=resolved_output_root,
            control_dir=control_dir,
            logs_dir=resolved_output_root / "logs",
            runtime_root=resolved_output_root / "runtime",
            registry_root=resolved_output_root / "registry",
            mailbox_root=resolved_output_root / "mailbox",
            jobs_root=resolved_output_root / "jobs",
            deliveries_dir=resolved_output_root / "deliveries",
            project_dir=resolved_output_root / "project",
            outputs_dir=resolved_output_root / "outputs",
            evidence_dir=resolved_output_root / "evidence",
            state_path=control_dir / "demo_state.json",
            mailbox_init_path=control_dir / "mailbox_init.json",
            launch_path=control_dir / "launch.json",
            agent_show_path=control_dir / "agent_show.json",
            agent_state_path=control_dir / "agent_state.json",
            mailbox_register_path=control_dir / "mailbox_register.json",
            gateway_attach_path=control_dir / "gateway_attach.json",
            notifier_enable_path=control_dir / "notifier_enable.json",
            ready_wait_path=control_dir / "ready_wait.json",
            inspect_path=control_dir / "inspect.json",
            report_path=control_dir / "report.json",
            sanitized_report_path=control_dir / "report.sanitized.json",
        )


class DeliveryState(_DemoModel):
    """Persisted staged-delivery metadata for one injected filesystem message."""

    delivery_index: int
    subject: str
    message_id: str
    thread_id: str
    created_at_utc: str
    body_source_path: Path | None = None
    staged_message_path: Path
    payload_path: Path
    delivery_artifact_path: Path
    unread_observed_at_utc: str | None = None
    read_observed_at_utc: str | None = None
    mailbox_state_source: str | None = None
    evidence_snapshot_path: Path | None = None
    evidence_tail_path: Path | None = None
    evidence_collected_at_utc: str | None = None

    @field_validator("delivery_index")
    @classmethod
    def _validate_delivery_index(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("must be > 0")
        return value

    @field_validator(
        "subject",
        "message_id",
        "thread_id",
        "created_at_utc",
        "unread_observed_at_utc",
        "read_observed_at_utc",
        "mailbox_state_source",
        "evidence_collected_at_utc",
    )
    @classmethod
    def _validate_optional_string(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped

    @property
    def processed(self) -> bool:
        """Return whether the harness observed this message become read."""

        return self.read_observed_at_utc is not None


class DemoState(_DemoModel):
    """Persisted lifecycle state shared by the pack commands."""

    schema_version: int = DEMO_STATE_SCHEMA_VERSION
    demo_id: str = PACK_NAME
    active: bool = True
    created_at_utc: str
    stopped_at_utc: str | None = None
    repo_root: Path
    output_root: Path
    selected_tool: SupportedTool
    provider: str
    selector: str
    run_id: str
    agent_def_dir: Path
    project_fixture: Path
    project_workdir: Path
    brain_manifest_path: Path
    brain_home_path: Path
    launch_helper_path: Path
    session_manifest_path: Path
    session_root: Path
    tracked_agent_id: str
    agent_name: str
    agent_id: str | None = None
    tmux_session_name: str | None = None
    terminal_id: str | None = None
    mailbox_principal_id: str
    mailbox_address: str
    gateway_root: Path
    gateway_host: str
    gateway_port: int
    notifier_interval_seconds: int
    idle_timeout_seconds: float
    output_timeout_seconds: float
    output_file_path: Path
    deliveries: list[DeliveryState] = Field(default_factory=list)

    @field_validator("schema_version")
    @classmethod
    def _validate_state_schema_version(cls, value: int) -> int:
        if value != DEMO_STATE_SCHEMA_VERSION:
            raise ValueError(f"demo state must use schema_version={DEMO_STATE_SCHEMA_VERSION}")
        return value

    @field_validator(
        "created_at_utc",
        "stopped_at_utc",
        "provider",
        "selector",
        "run_id",
        "tracked_agent_id",
        "agent_name",
        "agent_id",
        "tmux_session_name",
        "terminal_id",
        "mailbox_principal_id",
        "mailbox_address",
        "gateway_host",
    )
    @classmethod
    def _validate_optional_string(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped

    @field_validator("gateway_port", "notifier_interval_seconds")
    @classmethod
    def _validate_positive_int(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("must be > 0")
        return value

    @field_validator("idle_timeout_seconds", "output_timeout_seconds")
    @classmethod
    def _validate_positive_float(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("must be > 0")
        return value

    @property
    def delivery_count(self) -> int:
        """Return the number of injected messages tracked in state."""

        return len(self.deliveries)

    @property
    def processed_delivery_count(self) -> int:
        """Return the number of deliveries observed as read and complete."""

        return sum(1 for delivery in self.deliveries if delivery.processed)


@dataclass(frozen=True)
class CommandResult:
    """Captured subprocess result plus persisted log locations."""

    args: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str
    stdout_path: Path
    stderr_path: Path


def utc_now_iso() -> str:
    """Return one compact UTC timestamp with second resolution."""

    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve_repo_relative_path(path: Path | str, *, repo_root: Path) -> Path:
    """Resolve one repo-relative or absolute path."""

    candidate = Path(path).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    return (repo_root / candidate).resolve()


def default_demo_output_dir(*, repo_root: Path, tool: SupportedTool) -> Path:
    """Return the default tool-scoped output root for one selected tool."""

    return (repo_root / DEFAULT_DEMO_OUTPUT_DIR_RELATIVE / tool).resolve()


def build_demo_layout(*, demo_output_dir: Path) -> DemoPaths:
    """Return the canonical demo layout for one selected output root."""

    return DemoPaths.from_output_root(output_root=demo_output_dir)


def load_demo_parameters(path: Path) -> DemoParameters:
    """Load tracked demo parameters from JSON."""

    return DemoParameters.model_validate_json(path.read_text(encoding="utf-8"))


def load_demo_state(path: Path) -> DemoState:
    """Load persisted demo state from JSON."""

    return DemoState.model_validate_json(path.read_text(encoding="utf-8"))


def save_demo_state(path: Path, state: DemoState) -> None:
    """Persist one demo state JSON payload."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(state.model_dump_json(indent=2) + "\n", encoding="utf-8")


def write_json(path: Path, payload: Any) -> None:
    """Write one JSON payload with stable formatting."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
