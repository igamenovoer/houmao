"""Typed state models for the Houmao-server dual shadow-watch demo."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


DEMO_STATE_SCHEMA_VERSION = 1
DEFAULT_POLL_INTERVAL_SECONDS = 0.5
DEFAULT_STABILITY_THRESHOLD_SECONDS = 1.0
DEFAULT_COMPLETION_STABILITY_SECONDS = 1.0
DEFAULT_UNKNOWN_TO_STALLED_TIMEOUT_SECONDS = 30.0
DEFAULT_SERVER_START_TIMEOUT_SECONDS = 20.0
DEFAULT_LAUNCH_TIMEOUT_SECONDS = 45.0
DEFAULT_STOP_TIMEOUT_SECONDS = 20.0
DEFAULT_PROFILE_NAME = "projection-demo"


@dataclass(frozen=True)
class DemoPaths:
    """Resolved filesystem layout for one selected demo run root."""

    run_root: Path
    control_dir: Path
    runtime_root: Path
    registry_root: Path
    jobs_root: Path
    server_dir: Path
    server_home_dir: Path
    server_runtime_root: Path
    projects_dir: Path
    claude_project_dir: Path
    codex_project_dir: Path
    monitor_dir: Path
    logs_dir: Path
    state_path: Path
    preflight_report_path: Path
    current_run_root_path: Path

    @classmethod
    def from_run_root(cls, *, repo_root: Path, run_root: Path) -> "DemoPaths":
        """Build the canonical layout for one run."""

        resolved_run_root = run_root.resolve()
        base_root = (
            repo_root.resolve() / "tmp" / "demo" / "houmao-server-dual-shadow-watch"
        ).resolve()
        control_dir = resolved_run_root / "control"
        projects_dir = resolved_run_root / "projects"
        server_dir = resolved_run_root / "server"
        return cls(
            run_root=resolved_run_root,
            control_dir=control_dir,
            runtime_root=resolved_run_root / "runtime",
            registry_root=resolved_run_root / "registry",
            jobs_root=resolved_run_root / "jobs",
            server_dir=server_dir,
            server_home_dir=server_dir / "home",
            server_runtime_root=server_dir / "runtime",
            projects_dir=projects_dir,
            claude_project_dir=projects_dir / "claude",
            codex_project_dir=projects_dir / "codex",
            monitor_dir=resolved_run_root / "monitor",
            logs_dir=resolved_run_root / "logs",
            state_path=control_dir / "demo_state.json",
            preflight_report_path=control_dir / "preflight.json",
            current_run_root_path=base_root / "current_run_root.txt",
        )


@dataclass(frozen=True)
class ServerProcessState:
    """Persisted metadata for the demo-owned Houmao server process."""

    api_base_url: str
    port: int
    runtime_root: str
    home_dir: str
    pid: int
    started_by_demo: bool
    stdout_log_path: str
    stderr_log_path: str


@dataclass(frozen=True)
class AgentSessionState:
    """Persisted metadata for one live demo-owned agent session."""

    slot: str
    tool: str
    provider: str
    profile_name: str
    session_name: str
    terminal_id: str
    tmux_session_name: str
    workdir: str
    agent_name: str
    agent_id: str
    blueprint_path: str
    brain_recipe_path: str
    role_name: str
    config_profile: str
    credential_profile: str
    brain_home_path: str
    brain_manifest_path: str
    launch_helper_path: str
    session_manifest_path: str
    session_root: str
    launch_stdout_path: str
    launch_stderr_path: str


@dataclass(frozen=True)
class MonitorSessionState:
    """Persisted metadata for the monitor tmux session and artifacts."""

    tmux_session_name: str
    command: tuple[str, ...]
    samples_path: str
    transitions_path: str
    dashboard_log_path: str


@dataclass(frozen=True)
class HoumaoServerDualShadowWatchState:
    """Full persisted run-state payload for the standalone demo."""

    schema_version: int
    active: bool
    created_at_utc: str
    stopped_at_utc: str | None
    repo_root: str
    run_root: str
    agent_def_dir: str
    project_fixture: str
    profile_path: str
    poll_interval_seconds: float
    stability_threshold_seconds: float
    completion_stability_seconds: float
    unknown_to_stalled_timeout_seconds: float
    server_start_timeout_seconds: float
    launch_timeout_seconds: float
    stop_timeout_seconds: float
    server: ServerProcessState
    agents: dict[str, AgentSessionState]
    monitor: MonitorSessionState

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-serializable payload."""

        return asdict(self)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "HoumaoServerDualShadowWatchState":
        """Parse one persisted JSON payload into typed demo state."""

        server_payload = _require_mapping(payload.get("server"), context="server")
        monitor_payload = _require_mapping(payload.get("monitor"), context="monitor")
        agents_payload = _require_mapping(payload.get("agents"), context="agents")

        command_raw = monitor_payload.get("command", [])
        if not isinstance(command_raw, list) or not all(
            isinstance(item, str) for item in command_raw
        ):
            raise ValueError("monitor.command must be a list[str]")

        agents: dict[str, AgentSessionState] = {}
        for slot, raw_agent in agents_payload.items():
            agent_payload = _require_mapping(raw_agent, context=f"agents.{slot}")
            agents[slot] = AgentSessionState(
                slot=_require_string(agent_payload.get("slot"), context=f"agents.{slot}.slot"),
                tool=_require_string(agent_payload.get("tool"), context=f"agents.{slot}.tool"),
                provider=_require_string(
                    agent_payload.get("provider"),
                    context=f"agents.{slot}.provider",
                ),
                profile_name=_require_string(
                    agent_payload.get("profile_name"),
                    context=f"agents.{slot}.profile_name",
                ),
                session_name=_require_string(
                    agent_payload.get("session_name"),
                    context=f"agents.{slot}.session_name",
                ),
                terminal_id=_require_string(
                    agent_payload.get("terminal_id"),
                    context=f"agents.{slot}.terminal_id",
                ),
                tmux_session_name=_require_string(
                    agent_payload.get("tmux_session_name"),
                    context=f"agents.{slot}.tmux_session_name",
                ),
                workdir=_require_string(
                    agent_payload.get("workdir"),
                    context=f"agents.{slot}.workdir",
                ),
                agent_name=_require_string(
                    agent_payload.get("agent_name"),
                    context=f"agents.{slot}.agent_name",
                ),
                agent_id=_require_string(
                    agent_payload.get("agent_id"),
                    context=f"agents.{slot}.agent_id",
                ),
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
                config_profile=_require_string(
                    agent_payload.get("config_profile"),
                    context=f"agents.{slot}.config_profile",
                ),
                credential_profile=_require_string(
                    agent_payload.get("credential_profile"),
                    context=f"agents.{slot}.credential_profile",
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
                session_root=_require_string(
                    agent_payload.get("session_root"),
                    context=f"agents.{slot}.session_root",
                ),
                launch_stdout_path=_require_string(
                    agent_payload.get("launch_stdout_path"),
                    context=f"agents.{slot}.launch_stdout_path",
                ),
                launch_stderr_path=_require_string(
                    agent_payload.get("launch_stderr_path"),
                    context=f"agents.{slot}.launch_stderr_path",
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
            profile_path=_require_string(payload.get("profile_path"), context="profile_path"),
            poll_interval_seconds=float(
                payload.get("poll_interval_seconds", DEFAULT_POLL_INTERVAL_SECONDS)
            ),
            stability_threshold_seconds=float(
                payload.get("stability_threshold_seconds", DEFAULT_STABILITY_THRESHOLD_SECONDS)
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
            server_start_timeout_seconds=float(
                payload.get(
                    "server_start_timeout_seconds",
                    DEFAULT_SERVER_START_TIMEOUT_SECONDS,
                )
            ),
            launch_timeout_seconds=float(
                payload.get("launch_timeout_seconds", DEFAULT_LAUNCH_TIMEOUT_SECONDS)
            ),
            stop_timeout_seconds=float(
                payload.get("stop_timeout_seconds", DEFAULT_STOP_TIMEOUT_SECONDS)
            ),
            server=ServerProcessState(
                api_base_url=_require_string(
                    server_payload.get("api_base_url"),
                    context="server.api_base_url",
                ),
                port=int(server_payload.get("port", 0)),
                runtime_root=_require_string(
                    server_payload.get("runtime_root"),
                    context="server.runtime_root",
                ),
                home_dir=_require_string(server_payload.get("home_dir"), context="server.home_dir"),
                pid=int(server_payload.get("pid", 0)),
                started_by_demo=bool(server_payload.get("started_by_demo")),
                stdout_log_path=_require_string(
                    server_payload.get("stdout_log_path"),
                    context="server.stdout_log_path",
                ),
                stderr_log_path=_require_string(
                    server_payload.get("stderr_log_path"),
                    context="server.stderr_log_path",
                ),
            ),
            agents=agents,
            monitor=MonitorSessionState(
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
            ),
        )


def save_demo_state(path: Path, state: HoumaoServerDualShadowWatchState) -> None:
    """Persist one typed demo-state payload to disk."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(state.to_payload(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_demo_state(path: Path) -> HoumaoServerDualShadowWatchState:
    """Load one typed demo-state payload from disk."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Demo state must be a JSON object: {path}")
    return HoumaoServerDualShadowWatchState.from_payload(payload)


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
