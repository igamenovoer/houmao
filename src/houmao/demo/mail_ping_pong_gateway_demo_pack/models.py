"""Typed models and filesystem layout helpers for the demo pack."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


PACK_NAME = "mail-ping-pong-gateway-demo-pack"
DEMO_STATE_SCHEMA_VERSION = 1
REPORT_SCHEMA_VERSION = 1
DEFAULT_DEMO_OUTPUT_DIR_RELATIVE = f"scripts/demo/{PACK_NAME}/outputs"
DEFAULT_PARAMETERS_RELATIVE = f"scripts/demo/{PACK_NAME}/inputs/demo_parameters.json"
DEFAULT_EXPECTED_REPORT_RELATIVE = f"scripts/demo/{PACK_NAME}/expected_report/report.json"
DEFAULT_AGENT_DEF_DIR_RELATIVE = "tests/fixtures/agents"
DEFAULT_WAIT_POLL_INTERVAL_SECONDS = 2.0
DEFAULT_WAIT_TIMEOUT_SECONDS = 180.0
DEFAULT_SERVER_START_TIMEOUT_SECONDS = 20.0
DEFAULT_LAUNCH_TIMEOUT_SECONDS = 60.0
DEFAULT_STOP_TIMEOUT_SECONDS = 20.0
DEFAULT_HISTORY_LIMIT = 32
DEFAULT_GATEWAY_NOTIFIER_INTERVAL_SECONDS = 5
EXPECTED_DEFAULT_ROUND_LIMIT = 5
MANAGED_PROJECT_METADATA_NAME = ".houmao-demo-project.json"
FIXED_DEMO_PROJECT_COMMIT_UTC = "2026-03-23T00:00:00Z"
FIXED_DEMO_PROJECT_COMMIT_MESSAGE = "Initial dummy project snapshot"
FIXED_DEMO_PROJECT_AUTHOR_NAME = "Houmao Demo Fixture"
FIXED_DEMO_PROJECT_AUTHOR_EMAIL = "houmao-demo-fixture@example.invalid"


class _DemoModel(BaseModel):
    """Base model for demo-pack payloads."""

    model_config = ConfigDict(extra="forbid")


class WaitDefaults(_DemoModel):
    """Bounded polling defaults used by `wait` and snapshot refresh."""

    poll_interval_seconds: float = DEFAULT_WAIT_POLL_INTERVAL_SECONDS
    timeout_seconds: float = DEFAULT_WAIT_TIMEOUT_SECONDS
    history_limit: int = DEFAULT_HISTORY_LIMIT

    @field_validator("poll_interval_seconds", "timeout_seconds")
    @classmethod
    def _validate_positive_float(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("must be > 0")
        return value

    @field_validator("history_limit")
    @classmethod
    def _validate_positive_int(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("must be > 0")
        return value


class GatewayDefaults(_DemoModel):
    """Tracked gateway behavior defaults."""

    host: Literal["127.0.0.1", "0.0.0.0"] = "127.0.0.1"
    notifier_interval_seconds: int = DEFAULT_GATEWAY_NOTIFIER_INTERVAL_SECONDS

    @field_validator("notifier_interval_seconds")
    @classmethod
    def _validate_positive_int(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("must be > 0")
        return value


class ConversationParameters(_DemoModel):
    """Conversation contract persisted in tracked inputs."""

    round_limit: int = EXPECTED_DEFAULT_ROUND_LIMIT
    subject_template: str = "[{thread_key}] Round {round_index} ping-pong"

    @field_validator("round_limit")
    @classmethod
    def _validate_round_limit(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("must be > 0")
        return value

    @field_validator("subject_template")
    @classmethod
    def _validate_subject_template(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value


class ParticipantParameters(_DemoModel):
    """Tracked participant definition for one role."""

    tool: str
    role_name: str
    brain_recipe_path: Path
    mailbox_principal_id: str
    mailbox_address: str

    @field_validator("tool", "role_name", "mailbox_principal_id", "mailbox_address")
    @classmethod
    def _validate_non_empty_string(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped


class DemoParameters(_DemoModel):
    """Tracked operator-facing defaults for the pack."""

    schema_version: int = 1
    demo_id: str = PACK_NAME
    agent_def_dir: Path = Path(DEFAULT_AGENT_DEF_DIR_RELATIVE)
    project_fixture: Path = Path("tests/fixtures/dummy-projects/mailbox-demo-python")
    server_start_timeout_seconds: float = DEFAULT_SERVER_START_TIMEOUT_SECONDS
    launch_timeout_seconds: float = DEFAULT_LAUNCH_TIMEOUT_SECONDS
    stop_timeout_seconds: float = DEFAULT_STOP_TIMEOUT_SECONDS
    gateway: GatewayDefaults = Field(default_factory=GatewayDefaults)
    wait_defaults: WaitDefaults = Field(default_factory=WaitDefaults)
    conversation: ConversationParameters = Field(default_factory=ConversationParameters)
    initiator: ParticipantParameters
    responder: ParticipantParameters

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
            raise ValueError("demo_id must not be empty")
        return stripped

    @field_validator(
        "server_start_timeout_seconds",
        "launch_timeout_seconds",
        "stop_timeout_seconds",
    )
    @classmethod
    def _validate_positive_float(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("must be > 0")
        return value


@dataclass(frozen=True)
class DemoPaths:
    """Resolved filesystem layout rooted under one selected output directory."""

    output_root: Path
    control_dir: Path
    server_dir: Path
    server_runtime_root: Path
    server_home_dir: Path
    server_logs_dir: Path
    runtime_root: Path
    registry_root: Path
    mailbox_root: Path
    jobs_root: Path
    projects_dir: Path
    initiator_project_dir: Path
    responder_project_dir: Path
    monitor_dir: Path
    state_path: Path
    kickoff_request_path: Path
    inspect_path: Path
    events_path: Path
    report_path: Path
    sanitized_report_path: Path

    @classmethod
    def from_output_root(cls, *, output_root: Path) -> "DemoPaths":
        """Build the canonical demo layout for one selected output root."""

        resolved_output_root = output_root.resolve()
        control_dir = resolved_output_root / "control"
        server_dir = resolved_output_root / "server"
        projects_dir = resolved_output_root / "projects"
        return cls(
            output_root=resolved_output_root,
            control_dir=control_dir,
            server_dir=server_dir,
            server_runtime_root=server_dir / "runtime",
            server_home_dir=server_dir / "home",
            server_logs_dir=server_dir / "logs",
            runtime_root=resolved_output_root / "runtime",
            registry_root=resolved_output_root / "registry",
            mailbox_root=resolved_output_root / "mailbox",
            jobs_root=resolved_output_root / "jobs",
            projects_dir=projects_dir,
            initiator_project_dir=projects_dir / "initiator",
            responder_project_dir=projects_dir / "responder",
            monitor_dir=resolved_output_root / "monitor",
            state_path=control_dir / "demo_state.json",
            kickoff_request_path=control_dir / "kickoff_request.json",
            inspect_path=control_dir / "inspect.json",
            events_path=control_dir / "conversation_events.jsonl",
            report_path=control_dir / "report.json",
            sanitized_report_path=control_dir / "report.sanitized.json",
        )


class ServerProcessState(_DemoModel):
    """Persisted metadata for the demo-owned `houmao-server` process."""

    api_base_url: str
    port: int
    runtime_root: Path
    home_dir: Path
    pid: int
    started_at_utc: str
    started_by_demo: bool = True
    stdout_log_path: Path
    stderr_log_path: Path

    @field_validator("api_base_url", "started_at_utc")
    @classmethod
    def _validate_non_empty_string(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped

    @field_validator("port", "pid")
    @classmethod
    def _validate_positive_int(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("must be > 0")
        return value


class ParticipantState(_DemoModel):
    """Persisted runtime state for one managed headless participant."""

    role: Literal["initiator", "responder"]
    tool: str
    role_name: str
    mailbox_principal_id: str
    mailbox_address: str
    working_directory: Path
    brain_recipe_path: Path
    brain_home_path: Path
    brain_manifest_path: Path
    launch_helper_path: Path
    tracked_agent_id: str
    agent_name: str | None = None
    agent_id: str | None = None
    session_root: Path
    tmux_session_name: str
    gateway_host: str | None = None

    @field_validator(
        "tool",
        "role_name",
        "mailbox_principal_id",
        "mailbox_address",
        "tracked_agent_id",
        "tmux_session_name",
        "gateway_host",
        "agent_name",
        "agent_id",
    )
    @classmethod
    def _validate_optional_non_empty_string(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped


class KickoffRequestState(_DemoModel):
    """Persisted kickoff request metadata for the initiator."""

    submitted_at_utc: str
    request_id: str
    disposition: str
    headless_turn_id: str | None = None
    headless_turn_index: int | None = None
    prompt: str

    @field_validator("submitted_at_utc", "request_id", "disposition", "prompt", "headless_turn_id")
    @classmethod
    def _validate_optional_non_empty_string(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped

    @field_validator("headless_turn_index")
    @classmethod
    def _validate_positive_turn_index(cls, value: int | None) -> int | None:
        if value is None:
            return None
        if value <= 0:
            raise ValueError("must be > 0")
        return value


class DemoState(_DemoModel):
    """Persisted state contract used by all pack commands."""

    schema_version: int = DEMO_STATE_SCHEMA_VERSION
    demo_id: str = PACK_NAME
    active: bool = True
    created_at_utc: str
    stopped_at_utc: str | None = None
    repo_root: Path
    output_root: Path
    agent_def_dir: Path
    api_base_url: str
    mailbox_root: Path
    project_fixture: Path
    thread_key: str | None = None
    round_limit: int
    wait_defaults: WaitDefaults
    server: ServerProcessState
    initiator: ParticipantState
    responder: ParticipantState
    kickoff_request: KickoffRequestState | None = None

    @field_validator("schema_version")
    @classmethod
    def _validate_schema_version(cls, value: int) -> int:
        if value != DEMO_STATE_SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported demo-state schema version: expected {DEMO_STATE_SCHEMA_VERSION}, got {value}"
            )
        return value

    @field_validator("created_at_utc", "stopped_at_utc", "demo_id", "api_base_url", "thread_key")
    @classmethod
    def _validate_optional_non_empty_string(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped

    @field_validator("round_limit")
    @classmethod
    def _validate_round_limit(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("must be > 0")
        return value


class ConversationEvent(_DemoModel):
    """One normalized event written to `conversation_events.jsonl`."""

    event_type: str
    observed_at_utc: str
    agent_role: Literal["initiator", "responder"]
    tracked_agent_id: str
    thread_key: str
    round_index: int
    source_kind: str
    turn_id: str | None = None
    turn_index: int | None = None
    message_id: str | None = None
    thread_id: str | None = None
    request_id: str | None = None
    subject: str | None = None
    detail: str | None = None

    @field_validator(
        "event_type",
        "observed_at_utc",
        "tracked_agent_id",
        "thread_key",
        "source_kind",
        "turn_id",
        "thread_id",
        "request_id",
        "subject",
        "detail",
    )
    @classmethod
    def _validate_optional_non_empty_string(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped

    @field_validator("round_index")
    @classmethod
    def _validate_round_index(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("must be > 0")
        return value

    @field_validator("turn_index")
    @classmethod
    def _validate_turn_index(cls, value: int | None) -> int | None:
        if value is None:
            return None
        if value <= 0:
            raise ValueError("must be > 0")
        return value


class ConversationProgressSummary(_DemoModel):
    """Derived progress summary for wait, inspect, and report flows."""

    thread_key: str
    thread_ids: list[str]
    expected_messages: int
    expected_turns: int
    message_count: int
    completed_turn_count: int
    total_turn_count: int
    unread_by_role: dict[str, int]
    gateway_enqueued_by_role: dict[str, bool]
    success: bool
    incomplete_reason: str | None = None

    @field_validator("thread_key", "incomplete_reason")
    @classmethod
    def _validate_optional_non_empty_string(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped


class ParticipantLaunchPostureSummary(_DemoModel):
    """Stable launch-posture summary for one participant."""

    tracked_recipe_operator_prompt_mode: str | None = None
    built_brain_manifest_operator_prompt_mode: str | None = None
    live_launch_request_operator_prompt_mode: str | None = None
    launch_policy_applied: bool | None = None

    @field_validator(
        "tracked_recipe_operator_prompt_mode",
        "built_brain_manifest_operator_prompt_mode",
        "live_launch_request_operator_prompt_mode",
    )
    @classmethod
    def _validate_optional_non_empty_string(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped


class ParticipantInspectSnapshot(_DemoModel):
    """Per-participant inspect payload."""

    state: dict[str, Any]
    detail: dict[str, Any]
    gateway_status: dict[str, Any]
    gateway_mail_notifier: dict[str, Any]
    launch_posture: ParticipantLaunchPostureSummary


class InspectSnapshot(_DemoModel):
    """Persisted `inspect.json` contract."""

    schema_version: int = REPORT_SCHEMA_VERSION
    observed_at_utc: str
    demo_state_summary: dict[str, Any]
    progress: ConversationProgressSummary
    participants: dict[str, ParticipantInspectSnapshot]
    recent_events: list[ConversationEvent]

    @field_validator("observed_at_utc")
    @classmethod
    def _validate_non_empty_string(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped


class ParticipantOutcomeSummary(_DemoModel):
    """Stable per-role outcome summary for the report contract."""

    tool: str
    role_name: str
    tracked_agent_id: str
    message_count: int
    completed_turn_count: int
    unread_count: int
    notifier_enabled: bool
    gateway_health: str
    gateway_enqueued: bool
    last_turn_result: str
    launch_posture: ParticipantLaunchPostureSummary


class GatewayEvidenceSummary(_DemoModel):
    """Stable gateway evidence summary for one report."""

    kickoff_request_id: str | None = None
    later_turn_count: int
    notifier_enqueued_by_role: dict[str, bool]
    direct_request_count: int = 1

    @field_validator("kickoff_request_id")
    @classmethod
    def _validate_optional_non_empty_string(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped


class MailboxEvidenceSummary(_DemoModel):
    """Stable mailbox evidence summary for one report."""

    thread_key: str
    thread_ids: list[str]
    total_messages: int
    unread_by_role: dict[str, int]
    subjects: list[str]

    @field_validator("thread_key")
    @classmethod
    def _validate_non_empty_string(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped


class ArtifactReferences(_DemoModel):
    """Stable artifact references emitted in the report."""

    demo_state_path: Path
    inspect_path: Path
    events_path: Path
    report_path: Path
    sanitized_report_path: Path


class ReportSnapshot(_DemoModel):
    """Stable `report.json` contract."""

    schema_version: int = REPORT_SCHEMA_VERSION
    status: Literal["complete", "incomplete"]
    observed_at_utc: str
    config: dict[str, Any]
    outcome: dict[str, Any]
    counts: dict[str, int]
    per_role: dict[str, ParticipantOutcomeSummary]
    gateway_evidence: GatewayEvidenceSummary
    mailbox_evidence: MailboxEvidenceSummary
    artifact_refs: ArtifactReferences
    failures: list[str] = Field(default_factory=list)

    @field_validator("observed_at_utc")
    @classmethod
    def _validate_non_empty_string(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped


def utc_now_iso() -> str:
    """Return the current UTC timestamp in seconds precision."""

    return datetime.now(UTC).isoformat(timespec="seconds")


def read_json(path: Path) -> Any:
    """Load one JSON value from disk."""

    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    """Write one JSON value to disk."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_json_lines(path: Path, payloads: list[dict[str, Any]]) -> None:
    """Write JSON lines to disk."""

    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = "".join(json.dumps(item, sort_keys=True) + "\n" for item in payloads)
    path.write_text(rendered, encoding="utf-8")


def resolve_repo_relative_path(
    raw_path: str | Path | None,
    *,
    repo_root: Path,
    default_relative: str | Path | None = None,
) -> Path:
    """Resolve one optional path relative to the repository root."""

    if raw_path is None or (isinstance(raw_path, str) and not raw_path.strip()):
        if default_relative is None:
            raise ValueError("path is required when no default_relative is provided")
        candidate = Path(default_relative)
    else:
        candidate = Path(raw_path).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    return (repo_root.resolve() / candidate).resolve()


def build_demo_layout(*, demo_output_dir: Path) -> DemoPaths:
    """Return the resolved filesystem layout for one run."""

    return DemoPaths.from_output_root(output_root=demo_output_dir)


def load_demo_parameters(path: Path) -> DemoParameters:
    """Load tracked demo parameters from JSON."""

    return DemoParameters.model_validate(read_json(path))


def save_demo_state(path: Path, state: DemoState) -> None:
    """Persist one typed demo-state payload."""

    write_json(path, state.model_dump(mode="json"))


def load_demo_state(path: Path) -> DemoState:
    """Load one typed demo-state payload from disk."""

    return DemoState.model_validate(read_json(path))
