"""Typed models for the manual Kimi writer-team demo pack."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

PACK_NAME = "kimi-writer-team-manual"
DEMO_STATE_SCHEMA_VERSION = 1
DEFAULT_DEMO_OUTPUT_DIR_RELATIVE = f"scripts/demo/{PACK_NAME}/outputs"
DEFAULT_PARAMETERS_RELATIVE = f"scripts/demo/{PACK_NAME}/inputs/demo_parameters.json"
DEFAULT_COMMAND_TIMEOUT_SECONDS = 180.0
DEFAULT_READY_TIMEOUT_SECONDS = 180.0
DEFAULT_NOTIFIER_INTERVAL_SECONDS = 5

TeamRole = Literal["story", "character", "review"]


class _DemoModel(BaseModel):
    """Base model for strict demo payloads."""

    model_config = ConfigDict(extra="forbid")


class TeamMemberParameters(_DemoModel):
    """Tracked setup values for one writer-team participant."""

    role: TeamRole
    specialist_name: str
    profile_name: str
    agent_name: str
    system_prompt_file: Path
    mailbox_principal_id: str
    mailbox_address: str
    session_name_prefix: str

    @field_validator(
        "specialist_name",
        "profile_name",
        "agent_name",
        "mailbox_principal_id",
        "mailbox_address",
        "session_name_prefix",
    )
    @classmethod
    def _validate_non_empty_string(cls, value: str) -> str:
        """Require non-empty string configuration."""

        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped


class OperatorParameters(_DemoModel):
    """Tracked operator mailbox identity for structural mailbox setup."""

    principal_id: str
    address: str

    @field_validator("principal_id", "address")
    @classmethod
    def _validate_non_empty_string(cls, value: str) -> str:
        """Require non-empty string configuration."""

        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped


class DemoParameters(_DemoModel):
    """Tracked operator-facing defaults for the demo pack."""

    schema_version: int = 1
    demo_id: str = PACK_NAME
    story_source_dir: Path = Path("examples/writer-team")
    start_charter_template: Path = Path(
        f"scripts/demo/{PACK_NAME}/inputs/start-charter-template.md"
    )
    credential_name: str = "writer-team-kimi"
    setup_name: str = "default"
    command_timeout_seconds: float = DEFAULT_COMMAND_TIMEOUT_SECONDS
    ready_timeout_seconds: float = DEFAULT_READY_TIMEOUT_SECONDS
    notifier_interval_seconds: int = DEFAULT_NOTIFIER_INTERVAL_SECONDS
    default_chapter_count: int = 1
    run_id_prefix: str = "kimi-writer-team"
    notifier_appendix_text: str
    operator: OperatorParameters
    team: list[TeamMemberParameters]

    @field_validator("schema_version")
    @classmethod
    def _validate_schema_version(cls, value: int) -> int:
        """Require the supported parameters schema version."""

        if value != 1:
            raise ValueError("demo parameters must use schema_version=1")
        return value

    @field_validator("demo_id", "credential_name", "setup_name", "run_id_prefix")
    @classmethod
    def _validate_non_empty_string(cls, value: str) -> str:
        """Require non-empty string configuration."""

        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped

    @field_validator("command_timeout_seconds", "ready_timeout_seconds")
    @classmethod
    def _validate_positive_float(cls, value: float) -> float:
        """Require positive timeout values."""

        if value <= 0:
            raise ValueError("must be > 0")
        return value

    @field_validator("notifier_interval_seconds", "default_chapter_count")
    @classmethod
    def _validate_positive_int(cls, value: int) -> int:
        """Require positive integer values."""

        if value <= 0:
            raise ValueError("must be > 0")
        return value

    @model_validator(mode="after")
    def _validate_team(self) -> "DemoParameters":
        """Require the fixed three-role writer-team shape."""

        roles = {member.role for member in self.team}
        if roles != {"story", "character", "review"}:
            raise ValueError("team must include exactly story, character, and review roles")
        agent_names = [member.agent_name for member in self.team]
        if len(set(agent_names)) != len(agent_names):
            raise ValueError("team agent names must be unique")
        return self

    @property
    def story_member(self) -> TeamMemberParameters:
        """Return the master story participant."""

        for member in self.team:
            if member.role == "story":
                return member
        raise ValueError("story member missing")

    def member_by_agent_name(self, agent_name: str) -> TeamMemberParameters:
        """Return one participant by managed-agent name."""

        for member in self.team:
            if member.agent_name == agent_name:
                return member
        raise ValueError(f"unknown team agent: {agent_name}")


@dataclass(frozen=True)
class DemoPaths:
    """Resolved filesystem layout rooted under one selected output directory."""

    output_root: Path
    control_dir: Path
    logs_dir: Path
    deliveries_dir: Path
    evidence_dir: Path
    project_dir: Path
    overlay_dir: Path
    runtime_root: Path
    registry_root: Path
    jobs_root: Path
    state_path: Path

    @classmethod
    def from_output_root(cls, *, output_root: Path) -> "DemoPaths":
        """Build the canonical demo layout for one selected output root."""

        resolved_output_root = output_root.resolve()
        overlay_dir = resolved_output_root / "overlay"
        control_dir = resolved_output_root / "control"
        return cls(
            output_root=resolved_output_root,
            control_dir=control_dir,
            logs_dir=resolved_output_root / "logs",
            deliveries_dir=resolved_output_root / "deliveries",
            evidence_dir=resolved_output_root / "evidence",
            project_dir=resolved_output_root / "project",
            overlay_dir=overlay_dir,
            runtime_root=overlay_dir / "runtime",
            registry_root=resolved_output_root / "registry",
            jobs_root=overlay_dir / "jobs",
            state_path=control_dir / "demo_state.json",
        )

    @property
    def mailbox_root(self) -> Path:
        """Return the redirected project mailbox root."""

        return self.overlay_dir / "mailbox"

    def log_paths(self, stem: str) -> tuple[Path, Path]:
        """Return stdout and stderr paths for one command stem."""

        return self.logs_dir / f"{stem}.stdout", self.logs_dir / f"{stem}.stderr"

    def control_json_path(self, stem: str) -> Path:
        """Return one control JSON path for a command stem."""

        return self.control_dir / f"{stem}.json"


@dataclass(frozen=True)
class CommandResult:
    """Captured subprocess result persisted by the demo driver."""

    args: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str
    stdout_path: Path
    stderr_path: Path


class AgentRuntimeState(_DemoModel):
    """Persisted runtime metadata for one launched team member."""

    role: TeamRole
    specialist_name: str
    profile_name: str
    agent_name: str
    session_name: str
    mailbox_principal_id: str
    mailbox_address: str
    launch_payload: dict[str, Any] = Field(default_factory=dict)
    tmux_session_name: str | None = None
    manifest_path: Path | None = None
    gateway_host: str | None = None
    gateway_port: int | None = None


class DemoState(_DemoModel):
    """Persisted demo state used by follow-up commands."""

    schema_version: int = DEMO_STATE_SCHEMA_VERSION
    active: bool = True
    created_at_utc: str
    stopped_at_utc: str | None = None
    repo_root: Path
    output_root: Path
    project_workdir: Path
    overlay_root: Path
    credential_name: str
    credential_source: str
    run_id: str
    notifier_interval_seconds: int
    operator_principal_id: str
    operator_address: str
    team: list[AgentRuntimeState]

    @field_validator("schema_version")
    @classmethod
    def _validate_schema_version(cls, value: int) -> int:
        """Require the supported state schema version."""

        if value != DEMO_STATE_SCHEMA_VERSION:
            raise ValueError(f"demo state must use schema_version={DEMO_STATE_SCHEMA_VERSION}")
        return value

    def agent(self, agent_name: str) -> AgentRuntimeState:
        """Return one launched agent by managed-agent name."""

        for agent in self.team:
            if agent.agent_name == agent_name:
                return agent
        raise ValueError(f"unknown active demo agent: {agent_name}")


def utc_now_iso() -> str:
    """Return a stable UTC timestamp string."""

    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_demo_layout(*, demo_output_dir: Path) -> DemoPaths:
    """Build the resolved demo path layout."""

    return DemoPaths.from_output_root(output_root=demo_output_dir)


def default_demo_output_dir(*, repo_root: Path) -> Path:
    """Return the canonical pack-local output root."""

    return (repo_root / DEFAULT_DEMO_OUTPUT_DIR_RELATIVE).resolve()


def resolve_repo_relative_path(value: str | Path, *, repo_root: Path) -> Path:
    """Resolve a path that may be absolute or repository-relative."""

    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()
