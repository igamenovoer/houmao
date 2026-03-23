"""Typed state models for the dual-agent shadow-watch demo pack."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from typing import Final, Literal


DEMO_STATE_SCHEMA_VERSION = 1
DEFAULT_POLL_INTERVAL_SECONDS = 0.5
DEFAULT_COMPLETION_STABILITY_SECONDS = 1.0
DEFAULT_UNKNOWN_TO_STALLED_TIMEOUT_SECONDS = 30.0
DEFAULT_SHADOW_PARSING_MODE: Final[Literal["shadow_only"]] = "shadow_only"


@dataclass(frozen=True)
class DemoPaths:
    """Resolved filesystem layout for one dual-shadow-watch demo run."""

    run_root: Path
    control_dir: Path
    runtime_root: Path
    projects_dir: Path
    claude_project_dir: Path
    codex_project_dir: Path
    monitor_dir: Path
    logs_dir: Path
    state_path: Path
    launcher_config_path: Path
    current_run_root_path: Path

    @classmethod
    def from_run_root(cls, *, repo_root: Path, run_root: Path) -> "DemoPaths":
        """Build the canonical demo layout for one selected run root."""

        resolved_run_root = run_root.resolve()
        base_root = (repo_root.resolve() / "tmp" / "demo" / "cao-dual-shadow-watch").resolve()
        control_dir = resolved_run_root / "control"
        projects_dir = resolved_run_root / "projects"
        monitor_dir = resolved_run_root / "monitor"
        return cls(
            run_root=resolved_run_root,
            control_dir=control_dir,
            runtime_root=resolved_run_root / "runtime",
            projects_dir=projects_dir,
            claude_project_dir=projects_dir / "claude",
            codex_project_dir=projects_dir / "codex",
            monitor_dir=monitor_dir,
            logs_dir=resolved_run_root / "logs",
            state_path=control_dir / "demo_state.json",
            launcher_config_path=control_dir / "cao-server-launcher.toml",
            current_run_root_path=base_root / "current_run_root.txt",
        )


@dataclass(frozen=True)
class DemoLauncherState:
    """Persisted launcher metadata for the shared CAO server."""

    config_path: str
    base_url: str
    runtime_root: str
    home_dir: str
    profile_store: str
    started_new_process: bool
    reused_existing_process: bool
    artifact_dir: str
    log_file: str
    ownership_file: str


@dataclass(frozen=True)
class AgentSessionState:
    """Persisted metadata for one live demo-owned agent session."""

    slot: str
    tool: str
    blueprint_path: str
    brain_recipe_path: str
    role_name: str
    workdir: str
    brain_home_path: str
    brain_manifest_path: str
    launch_helper_path: str
    session_manifest_path: str
    agent_identity: str
    agent_id: str
    tmux_session_name: str
    cao_session_name: str
    terminal_id: str
    parsing_mode: str
    startup_warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class MonitorSessionState:
    """Persisted metadata for the monitor tmux session and artifacts."""

    tmux_session_name: str
    command: tuple[str, ...]
    samples_path: str
    transitions_path: str
    dashboard_log_path: str


@dataclass(frozen=True)
class DualShadowWatchDemoState:
    """Full persisted run-state payload for the standalone demo."""

    schema_version: int
    active: bool
    created_at_utc: str
    stopped_at_utc: str | None
    repo_root: str
    run_root: str
    agent_def_dir: str
    project_fixture: str
    parsing_mode: str
    poll_interval_seconds: float
    completion_stability_seconds: float
    unknown_to_stalled_timeout_seconds: float
    launcher: DemoLauncherState
    agents: dict[str, AgentSessionState]
    monitor: MonitorSessionState

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-serializable payload for disk persistence."""

        return asdict(self)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "DualShadowWatchDemoState":
        """Parse one persisted JSON payload into typed demo state."""

        launcher_payload = _require_mapping(payload.get("launcher"), context="launcher")
        launcher = DemoLauncherState(
            config_path=_require_string(
                launcher_payload.get("config_path"), context="launcher.config_path"
            ),
            base_url=_require_string(launcher_payload.get("base_url"), context="launcher.base_url"),
            runtime_root=_require_string(
                launcher_payload.get("runtime_root"),
                context="launcher.runtime_root",
            ),
            home_dir=_require_string(launcher_payload.get("home_dir"), context="launcher.home_dir"),
            profile_store=_require_string(
                launcher_payload.get("profile_store"),
                context="launcher.profile_store",
            ),
            started_new_process=bool(launcher_payload.get("started_new_process")),
            reused_existing_process=bool(launcher_payload.get("reused_existing_process")),
            artifact_dir=_require_string(
                launcher_payload.get("artifact_dir"),
                context="launcher.artifact_dir",
            ),
            log_file=_require_string(launcher_payload.get("log_file"), context="launcher.log_file"),
            ownership_file=_require_string(
                launcher_payload.get("ownership_file"),
                context="launcher.ownership_file",
            ),
        )
        agents_payload = _require_mapping(payload.get("agents"), context="agents")
        agents: dict[str, AgentSessionState] = {}
        for slot, raw_agent in agents_payload.items():
            agent_payload = _require_mapping(raw_agent, context=f"agents.{slot}")
            startup_warnings_raw = agent_payload.get("startup_warnings", [])
            if not isinstance(startup_warnings_raw, list) or not all(
                isinstance(item, str) for item in startup_warnings_raw
            ):
                raise ValueError(f"agents.{slot}.startup_warnings must be a list[str]")
            agents[slot] = AgentSessionState(
                slot=_require_string(agent_payload.get("slot"), context=f"agents.{slot}.slot"),
                tool=_require_string(agent_payload.get("tool"), context=f"agents.{slot}.tool"),
                blueprint_path=_require_string(
                    agent_payload.get("blueprint_path"),
                    context=f"agents.{slot}.blueprint_path",
                ),
                brain_recipe_path=_require_string(
                    agent_payload.get("brain_recipe_path"),
                    context=f"agents.{slot}.brain_recipe_path",
                ),
                role_name=_require_string(
                    agent_payload.get("role_name"),
                    context=f"agents.{slot}.role_name",
                ),
                workdir=_require_string(
                    agent_payload.get("workdir"), context=f"agents.{slot}.workdir"
                ),
                brain_home_path=_require_string(
                    agent_payload.get("brain_home_path"),
                    context=f"agents.{slot}.brain_home_path",
                ),
                brain_manifest_path=_require_string(
                    agent_payload.get("brain_manifest_path"),
                    context=f"agents.{slot}.brain_manifest_path",
                ),
                launch_helper_path=_require_string(
                    agent_payload.get("launch_helper_path"),
                    context=f"agents.{slot}.launch_helper_path",
                ),
                session_manifest_path=_require_string(
                    agent_payload.get("session_manifest_path"),
                    context=f"agents.{slot}.session_manifest_path",
                ),
                agent_identity=_require_string(
                    agent_payload.get("agent_identity"),
                    context=f"agents.{slot}.agent_identity",
                ),
                agent_id=_require_string(
                    agent_payload.get("agent_id"), context=f"agents.{slot}.agent_id"
                ),
                tmux_session_name=_require_string(
                    agent_payload.get("tmux_session_name"),
                    context=f"agents.{slot}.tmux_session_name",
                ),
                cao_session_name=_require_string(
                    agent_payload.get("cao_session_name"),
                    context=f"agents.{slot}.cao_session_name",
                ),
                terminal_id=_require_string(
                    agent_payload.get("terminal_id"),
                    context=f"agents.{slot}.terminal_id",
                ),
                parsing_mode=_require_string(
                    agent_payload.get("parsing_mode"),
                    context=f"agents.{slot}.parsing_mode",
                ),
                startup_warnings=tuple(startup_warnings_raw),
            )
        monitor_payload = _require_mapping(payload.get("monitor"), context="monitor")
        command_raw = monitor_payload.get("command", [])
        if not isinstance(command_raw, list) or not all(
            isinstance(item, str) for item in command_raw
        ):
            raise ValueError("monitor.command must be a list[str]")
        monitor = MonitorSessionState(
            tmux_session_name=_require_string(
                monitor_payload.get("tmux_session_name"),
                context="monitor.tmux_session_name",
            ),
            command=tuple(command_raw),
            samples_path=_require_string(
                monitor_payload.get("samples_path"),
                context="monitor.samples_path",
            ),
            transitions_path=_require_string(
                monitor_payload.get("transitions_path"),
                context="monitor.transitions_path",
            ),
            dashboard_log_path=_require_string(
                monitor_payload.get("dashboard_log_path"),
                context="monitor.dashboard_log_path",
            ),
        )
        schema_version = int(payload.get("schema_version", 0))
        if schema_version != DEMO_STATE_SCHEMA_VERSION:
            raise ValueError(
                "Unsupported demo-state schema version: "
                f"expected {DEMO_STATE_SCHEMA_VERSION}, got {schema_version}"
            )
        return cls(
            schema_version=schema_version,
            active=bool(payload.get("active")),
            created_at_utc=_require_string(payload.get("created_at_utc"), context="created_at_utc"),
            stopped_at_utc=_optional_string(payload.get("stopped_at_utc")),
            repo_root=_require_string(payload.get("repo_root"), context="repo_root"),
            run_root=_require_string(payload.get("run_root"), context="run_root"),
            agent_def_dir=_require_string(payload.get("agent_def_dir"), context="agent_def_dir"),
            project_fixture=_require_string(
                payload.get("project_fixture"),
                context="project_fixture",
            ),
            parsing_mode=_require_string(payload.get("parsing_mode"), context="parsing_mode"),
            poll_interval_seconds=float(
                payload.get("poll_interval_seconds", DEFAULT_POLL_INTERVAL_SECONDS)
            ),
            completion_stability_seconds=float(
                payload.get(
                    "completion_stability_seconds",
                    DEFAULT_COMPLETION_STABILITY_SECONDS,
                )
            ),
            unknown_to_stalled_timeout_seconds=float(
                payload.get(
                    "unknown_to_stalled_timeout_seconds",
                    DEFAULT_UNKNOWN_TO_STALLED_TIMEOUT_SECONDS,
                )
            ),
            launcher=launcher,
            agents=agents,
            monitor=monitor,
        )


@dataclass(frozen=True)
class MonitorObservation:
    """One parsed or synthesized monitor observation for one agent."""

    slot: str
    tool: str
    terminal_id: str
    tmux_session_name: str
    cao_status: str
    parser_family: str
    parser_preset_id: str | None
    parser_preset_version: str | None
    availability: str
    business_state: str
    input_mode: str
    ui_context: str
    normalized_projection_text: str
    dialog_tail: str
    operator_blocked_excerpt: str | None
    anomaly_codes: tuple[str, ...]
    baseline_invalidated: bool
    monotonic_ts: float
    error_detail: str | None = None


@dataclass(frozen=True)
class AgentDashboardState:
    """Current operator-facing state for one monitored agent."""

    slot: str
    tool: str
    terminal_id: str
    tmux_session_name: str
    cao_status: str
    parser_family: str
    parser_preset_id: str | None
    parser_preset_version: str | None
    availability: str
    business_state: str
    input_mode: str
    ui_context: str
    readiness_state: str
    completion_state: str
    unknown_elapsed_seconds: float | None
    stable_elapsed_seconds: float | None
    projection_changed: bool
    baseline_invalidated: bool
    anomaly_codes: tuple[str, ...]
    dialog_tail: str
    operator_blocked_excerpt: str | None
    error_detail: str | None = None

    def transition_signature(self) -> tuple[Any, ...]:
        """Return the state signature used for transition logging."""

        return (
            self.cao_status,
            self.availability,
            self.business_state,
            self.input_mode,
            self.ui_context,
            self.readiness_state,
            self.completion_state,
            self.projection_changed,
            self.baseline_invalidated,
            self.anomaly_codes,
            self.error_detail,
        )


@dataclass(frozen=True)
class MonitorTransitionEvent:
    """One persisted transition-log event emitted by the live monitor."""

    ts_utc: str
    slot: str
    tool: str
    summary: str
    changed_fields: tuple[str, ...] = field(default_factory=tuple)

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-serializable transition payload."""

        return asdict(self)


def save_demo_state(path: Path, state: DualShadowWatchDemoState) -> None:
    """Persist one typed demo-state payload to disk."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(state.to_payload(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_demo_state(path: Path) -> DualShadowWatchDemoState:
    """Load one typed demo-state payload from disk."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Demo state must be a JSON object: {path}")
    return DualShadowWatchDemoState.from_payload(payload)


def _require_mapping(value: Any, *, context: str) -> dict[str, Any]:
    """Return one mapping value or raise a clear validation error."""

    if not isinstance(value, dict):
        raise ValueError(f"{context} must be an object")
    return value


def _require_string(value: Any, *, context: str) -> str:
    """Return one non-empty string value or raise a validation error."""

    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context} must be a non-empty string")
    return value


def _optional_string(value: Any) -> str | None:
    """Return one optional string value."""

    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Optional string field must be a string when provided")
    stripped = value.strip()
    return stripped or None
