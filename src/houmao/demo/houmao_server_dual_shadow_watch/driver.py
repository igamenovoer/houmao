"""Standalone driver for the Houmao-server dual shadow-watch demo pack."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from houmao.agents.brain_builder import (
    BuildRequest,
    BuildResult,
    build_brain_home,
    load_brain_recipe,
)
from houmao.agents.realm_controller.agent_identity import (
    derive_agent_id_from_name,
    normalize_agent_identity_name,
)
from houmao.agents.realm_controller.backends.tmux_runtime import (
    has_tmux_session,
    kill_tmux_session,
    tmux_error_detail,
)
from houmao.agents.realm_controller.loaders import parse_allowlisted_env
from houmao.agents.realm_controller.manifest import default_manifest_path, load_session_manifest
from houmao.owned_paths import (
    AGENTSYS_GLOBAL_REGISTRY_DIR_ENV_VAR,
    AGENTSYS_GLOBAL_RUNTIME_DIR_ENV_VAR,
    AGENTSYS_LOCAL_JOBS_DIR_ENV_VAR,
)
from houmao.server.client import HoumaoServerClient
from houmao.cao.models import CaoSessionDetail
from houmao.cao.rest_client import CaoApiError
from houmao.demo.launch_support import resolve_demo_preset_launch

from houmao.demo.houmao_server_dual_shadow_watch.models import (
    DEFAULT_COMPLETION_STABILITY_SECONDS,
    DEFAULT_LAUNCH_TIMEOUT_SECONDS,
    DEFAULT_POLL_INTERVAL_SECONDS,
    DEFAULT_PROFILE_NAME,
    DEFAULT_SERVER_START_TIMEOUT_SECONDS,
    DEFAULT_STABILITY_THRESHOLD_SECONDS,
    DEFAULT_STOP_TIMEOUT_SECONDS,
    DEFAULT_UNKNOWN_TO_STALLED_TIMEOUT_SECONDS,
    AgentSessionState,
    DemoPaths,
    HoumaoServerDualShadowWatchState,
    MonitorSessionState,
    ServerProcessState,
    load_demo_state,
    save_demo_state,
)


FIXED_DEMO_PROJECT_COMMIT_UTC = "2026-03-18T12:00:00Z"
FIXED_DEMO_PROJECT_COMMIT_MESSAGE = "Initial projection demo snapshot"
FIXED_DEMO_PROJECT_AUTHOR_NAME = "Houmao Demo Fixture"
FIXED_DEMO_PROJECT_AUTHOR_EMAIL = "houmao-demo-fixture@example.invalid"

_PROVIDER_BY_SLOT = {"claude": "claude_code", "codex": "codex"}


class HoumaoServerDualShadowWatchError(RuntimeError):
    """Raised when the standalone demo cannot proceed safely."""


@dataclass(frozen=True)
class LanePreflight:
    """Resolved preflight and runtime-home preparation inputs for one lane."""

    slot: str
    tool: str
    provider: str
    blueprint_path: Path
    brain_recipe_path: Path
    role_name: str
    config_profile: str
    credential_profile: str
    config_profile_dir: Path
    credential_profile_dir: Path
    credential_env_path: Path
    required_credential_paths: tuple[Path, ...]
    optional_credential_paths: tuple[Path, ...]
    selected_allowlisted_env: dict[str, str]
    selected_allowlisted_env_keys: tuple[str, ...]
    launch_executable: str
    home_selector_env_var: str

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-friendly representation."""

        return {
            "slot": self.slot,
            "tool": self.tool,
            "provider": self.provider,
            "blueprint_path": str(self.blueprint_path),
            "brain_recipe_path": str(self.brain_recipe_path),
            "role_name": self.role_name,
            "config_profile": self.config_profile,
            "credential_profile": self.credential_profile,
            "config_profile_dir": str(self.config_profile_dir),
            "credential_profile_dir": str(self.credential_profile_dir),
            "credential_env_path": str(self.credential_env_path),
            "required_credential_paths": [str(path) for path in self.required_credential_paths],
            "optional_credential_paths": [str(path) for path in self.optional_credential_paths],
            "selected_allowlisted_env_keys": list(self.selected_allowlisted_env_keys),
            "launch_executable": self.launch_executable,
            "home_selector_env_var": self.home_selector_env_var,
        }


@dataclass(frozen=True)
class PreparedLane:
    """Runtime-prepared lane inputs ready for launch."""

    slot: str
    tool: str
    provider: str
    workdir: Path
    session_name: str
    preflight: LanePreflight
    build_result: BuildResult


def main(argv: list[str] | None = None) -> int:
    """Run the standalone Houmao-server dual shadow-watch driver."""

    parser = _build_parser()
    args = parser.parse_args(argv or sys.argv[1:])
    try:
        if args.command == "preflight":
            payload = preflight_demo(
                repo_root=_repo_root(),
                run_root=_optional_path(args.run_root),
                agent_def_dir=_optional_path(args.agent_def_dir),
                project_fixture=_optional_path(args.project_fixture),
                profile_path=_optional_path(args.profile_path),
                port=args.port,
                json_output=bool(args.json),
            )
            _emit_payload(payload, json_output=bool(args.json))
            return 0 if bool(payload["ok"]) else 2
        if args.command == "start":
            payload = start_demo(
                repo_root=_repo_root(),
                run_root=_optional_path(args.run_root),
                agent_def_dir=_optional_path(args.agent_def_dir),
                project_fixture=_optional_path(args.project_fixture),
                profile_path=_optional_path(args.profile_path),
                port=args.port,
                poll_interval_seconds=float(args.poll_interval_seconds),
                stability_threshold_seconds=float(args.stability_threshold_seconds),
                completion_stability_seconds=float(args.completion_stability_seconds),
                unknown_to_stalled_timeout_seconds=float(args.unknown_to_stalled_timeout_seconds),
                server_start_timeout_seconds=float(args.server_start_timeout_seconds),
                launch_timeout_seconds=float(args.launch_timeout_seconds),
                stop_timeout_seconds=float(args.stop_timeout_seconds),
                json_output=bool(args.json),
            )
            _emit_payload(payload, json_output=bool(args.json))
            return 0
        if args.command == "inspect":
            payload = inspect_demo(
                repo_root=_repo_root(),
                run_root=_optional_path(args.run_root),
                json_output=bool(args.json),
            )
            _emit_payload(payload, json_output=bool(args.json))
            return 0
        if args.command == "stop":
            payload = stop_demo(
                repo_root=_repo_root(),
                run_root=_optional_path(args.run_root),
                json_output=bool(args.json),
            )
            _emit_payload(payload, json_output=bool(args.json))
            return 0
    except (HoumaoServerDualShadowWatchError, CaoApiError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    parser.print_help()
    return 1


def preflight_demo(
    *,
    repo_root: Path,
    run_root: Path | None,
    agent_def_dir: Path | None,
    project_fixture: Path | None,
    profile_path: Path | None,
    port: int | None,
    json_output: bool,
) -> dict[str, Any]:
    """Collect fail-fast prerequisites without launching live sessions."""

    del json_output
    resolved_agent_def_dir = (
        agent_def_dir.resolve() if agent_def_dir is not None else _default_agent_def_dir(repo_root)
    )
    resolved_project_fixture = (
        project_fixture.resolve()
        if project_fixture is not None
        else _default_project_fixture(repo_root)
    )
    resolved_profile_path = (
        profile_path.resolve() if profile_path is not None else _default_profile_path(repo_root)
    )
    selected_run_root = run_root.resolve() if run_root is not None else _default_run_root(repo_root)
    selected_port = _select_port(port)
    blockers: list[str] = []

    command_checks = {
        name: _command_check_payload(name)
        for name in (
            "pixi",
            "git",
            "tmux",
            "cao",
            "houmao-server",
            "houmao-mgr",
            "claude",
            "codex",
        )
    }
    for name, payload in command_checks.items():
        if not bool(payload["ok"]):
            blockers.append(f"missing required executable `{name}` on PATH")

    lane_payloads: dict[str, dict[str, Any]] = {}
    for slot in ("claude", "codex"):
        try:
            lane = _resolve_lane_preflight(
                repo_root=repo_root,
                agent_def_dir=resolved_agent_def_dir,
                slot=slot,
            )
        except Exception as exc:
            blockers.append(f"{slot}: {exc}")
            lane_payloads[slot] = {"slot": slot, "ok": False, "error": str(exc)}
            continue
        missing_paths = [
            path
            for path in (
                lane.blueprint_path,
                lane.brain_recipe_path,
                lane.config_profile_dir,
                lane.credential_profile_dir,
                lane.credential_env_path,
                *lane.required_credential_paths,
            )
            if not path.exists()
        ]
        if missing_paths:
            blockers.append(
                f"{slot}: missing prerequisite paths: {', '.join(str(path) for path in missing_paths)}"
            )
        lane_payloads[slot] = {"ok": not missing_paths, **lane.to_payload()}

    if not resolved_agent_def_dir.is_dir():
        blockers.append(f"agent definition directory not found: {resolved_agent_def_dir}")
    if not resolved_project_fixture.is_dir():
        blockers.append(f"project fixture not found: {resolved_project_fixture}")
    if not resolved_profile_path.is_file():
        blockers.append(f"projection-demo profile not found: {resolved_profile_path}")

    output_root_status = _output_root_status(
        repo_root=repo_root,
        selected_run_root=selected_run_root,
    )
    if not bool(output_root_status["ok"]):
        blockers.append(str(output_root_status["reason"]))

    port_payload = {
        "selected_port": selected_port,
        "api_base_url": f"http://127.0.0.1:{selected_port}",
        "available": _port_is_available(selected_port),
    }
    if not port_payload["available"]:
        blockers.append(f"selected port is unavailable: {selected_port}")

    return {
        "change": "houmao-server-dual-shadow-watch",
        "ok": not blockers,
        "blockers": blockers,
        "run_root": str(selected_run_root),
        "agent_def_dir": str(resolved_agent_def_dir),
        "project_fixture": str(resolved_project_fixture),
        "profile_path": str(resolved_profile_path),
        "commands": command_checks,
        "lanes": lane_payloads,
        "port": port_payload,
        "output_root": output_root_status,
    }


def start_demo(
    *,
    repo_root: Path,
    run_root: Path | None,
    agent_def_dir: Path | None,
    project_fixture: Path | None,
    profile_path: Path | None,
    port: int | None,
    poll_interval_seconds: float,
    stability_threshold_seconds: float,
    completion_stability_seconds: float,
    unknown_to_stalled_timeout_seconds: float,
    server_start_timeout_seconds: float,
    launch_timeout_seconds: float,
    stop_timeout_seconds: float,
    json_output: bool,
) -> dict[str, Any]:
    """Start the demo-owned Houmao server, both agent sessions, and the monitor."""

    del json_output
    _require_positive(poll_interval_seconds, context="--poll-interval-seconds")
    _require_positive(stability_threshold_seconds, context="--stability-threshold-seconds")
    _require_positive(
        completion_stability_seconds,
        context="--completion-stability-seconds",
    )
    _require_positive(
        unknown_to_stalled_timeout_seconds,
        context="--unknown-to-stalled-timeout-seconds",
    )
    _require_positive(server_start_timeout_seconds, context="--server-start-timeout-seconds")
    _require_positive(launch_timeout_seconds, context="--launch-timeout-seconds")
    _require_positive(stop_timeout_seconds, context="--stop-timeout-seconds")

    selected_run_root = run_root.resolve() if run_root is not None else _default_run_root(repo_root)
    preflight = preflight_demo(
        repo_root=repo_root,
        run_root=selected_run_root,
        agent_def_dir=agent_def_dir,
        project_fixture=project_fixture,
        profile_path=profile_path,
        port=port,
        json_output=True,
    )
    if not bool(preflight["ok"]):
        raise HoumaoServerDualShadowWatchError(
            "preflight failed before live launch:\n- " + "\n- ".join(preflight["blockers"])
        )

    paths = DemoPaths.from_run_root(repo_root=repo_root, run_root=selected_run_root)
    _prepare_layout(paths, allow_reprovision=bool(preflight["output_root"]["status"] == "reusable"))
    paths.preflight_report_path.write_text(
        json.dumps(preflight, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_current_run_root(paths.current_run_root_path, paths.run_root)

    resolved_agent_def_dir = Path(preflight["agent_def_dir"]).resolve()
    resolved_project_fixture = Path(preflight["project_fixture"]).resolve()
    resolved_profile_path = Path(preflight["profile_path"]).resolve()
    api_base_url = str(preflight["port"]["api_base_url"])
    selected_port = int(preflight["port"]["selected_port"])

    _provision_project_fixture(
        fixture_path=resolved_project_fixture,
        project_workdir=paths.claude_project_dir,
    )
    _provision_project_fixture(
        fixture_path=resolved_project_fixture,
        project_workdir=paths.codex_project_dir,
    )

    lane_requirements = {
        slot: _resolve_lane_preflight(
            repo_root=repo_root,
            agent_def_dir=resolved_agent_def_dir,
            slot=slot,
        )
        for slot in ("claude", "codex")
    }
    prepared_lanes = {
        slot: _prepare_lane(
            repo_root=repo_root,
            agent_def_dir=resolved_agent_def_dir,
            paths=paths,
            slot=slot,
            lane_preflight=lane_requirements[slot],
            workdir=paths.claude_project_dir if slot == "claude" else paths.codex_project_dir,
            session_name=_session_name(paths.run_root, slot),
        )
        for slot in ("claude", "codex")
    }

    server_env = _build_demo_environment(paths=paths, lanes=prepared_lanes)
    server_process = _start_server_process(
        api_base_url=api_base_url,
        paths=paths,
        poll_interval_seconds=poll_interval_seconds,
        stability_threshold_seconds=stability_threshold_seconds,
        completion_stability_seconds=completion_stability_seconds,
        unknown_to_stalled_timeout_seconds=unknown_to_stalled_timeout_seconds,
        timeout_seconds=server_start_timeout_seconds,
        env=server_env,
    )

    _install_projection_profile(
        api_base_url=api_base_url,
        profile_path=resolved_profile_path,
        provider="claude_code",
        env=server_env,
        stdout_path=paths.logs_dir / "install-claude.stdout.log",
        stderr_path=paths.logs_dir / "install-claude.stderr.log",
    )
    _install_projection_profile(
        api_base_url=api_base_url,
        profile_path=resolved_profile_path,
        provider="codex",
        env=server_env,
        stdout_path=paths.logs_dir / "install-codex.stdout.log",
        stderr_path=paths.logs_dir / "install-codex.stderr.log",
    )

    client = HoumaoServerClient(api_base_url, timeout_seconds=5.0)
    agent_states: dict[str, AgentSessionState] = {}
    monitor_session_name: str | None = None
    try:
        for slot, lane in prepared_lanes.items():
            state = _launch_lane(
                client=client,
                lane=lane,
                paths=paths,
                timeout_seconds=launch_timeout_seconds,
                env=server_env,
            )
            agent_states[slot] = state

        created_at_utc = _now_utc_iso()
        monitor_session_name = _monitor_session_name(paths.run_root)
        monitor_command = (
            sys.executable,
            str((_demo_pack_dir(repo_root) / "scripts" / "watch_dashboard.py").resolve()),
            "--state-file",
            str(paths.state_path),
        )
        demo_state = HoumaoServerDualShadowWatchState(
            schema_version=1,
            active=True,
            created_at_utc=created_at_utc,
            stopped_at_utc=None,
            repo_root=str(repo_root.resolve()),
            run_root=str(paths.run_root),
            agent_def_dir=str(resolved_agent_def_dir),
            project_fixture=str(resolved_project_fixture),
            profile_path=str(resolved_profile_path),
            poll_interval_seconds=poll_interval_seconds,
            stability_threshold_seconds=stability_threshold_seconds,
            completion_stability_seconds=completion_stability_seconds,
            unknown_to_stalled_timeout_seconds=unknown_to_stalled_timeout_seconds,
            server_start_timeout_seconds=server_start_timeout_seconds,
            launch_timeout_seconds=launch_timeout_seconds,
            stop_timeout_seconds=stop_timeout_seconds,
            server=ServerProcessState(
                api_base_url=api_base_url,
                port=selected_port,
                runtime_root=str(paths.server_runtime_root),
                home_dir=str(paths.server_home_dir),
                pid=server_process.pid,
                started_by_demo=True,
                stdout_log_path=str(paths.logs_dir / "houmao-server.stdout.log"),
                stderr_log_path=str(paths.logs_dir / "houmao-server.stderr.log"),
            ),
            agents=agent_states,
            monitor=MonitorSessionState(
                tmux_session_name=monitor_session_name,
                command=monitor_command,
                samples_path=str(paths.monitor_dir / "samples.ndjson"),
                transitions_path=str(paths.monitor_dir / "transitions.ndjson"),
                dashboard_log_path=str(paths.logs_dir / "monitor-dashboard.log"),
            ),
        )
        save_demo_state(paths.state_path, demo_state)
        _start_monitor_tmux_session(
            session_name=monitor_session_name,
            working_directory=paths.run_root,
            command=monitor_command,
            log_path=Path(demo_state.monitor.dashboard_log_path),
            timeout_seconds=launch_timeout_seconds,
        )
    except Exception:
        _cleanup_partial_start(
            client=client,
            agent_states=agent_states,
            monitor_session_name=monitor_session_name,
            server_pid=server_process.pid,
            stop_timeout_seconds=stop_timeout_seconds,
        )
        raise

    return inspect_demo(repo_root=repo_root, run_root=paths.run_root, json_output=True)


def inspect_demo(
    *,
    repo_root: Path,
    run_root: Path | None,
    json_output: bool,
) -> dict[str, Any]:
    """Inspect persisted demo state and current server-owned session state."""

    del json_output
    state = _load_selected_demo_state(repo_root=repo_root, run_root=run_root)
    payload: dict[str, Any] = {
        "change": "houmao-server-dual-shadow-watch",
        "active": state.active,
        "created_at_utc": state.created_at_utc,
        "stopped_at_utc": state.stopped_at_utc,
        "run_root": state.run_root,
        "profile_path": state.profile_path,
        "server": {
            "api_base_url": state.server.api_base_url,
            "port": state.server.port,
            "pid": state.server.pid,
            "started_by_demo": state.server.started_by_demo,
            "stdout_log_path": state.server.stdout_log_path,
            "stderr_log_path": state.server.stderr_log_path,
            "timing_posture": {
                "stability_threshold_seconds": state.stability_threshold_seconds,
                "completion_stability_seconds": state.completion_stability_seconds,
                "unknown_to_stalled_timeout_seconds": state.unknown_to_stalled_timeout_seconds,
            },
            "healthy": _server_health_payload(state.server.api_base_url),
        },
        "agents": {},
        "monitor": {
            "tmux_session_name": state.monitor.tmux_session_name,
            "tmux_alive": _tmux_session_exists(state.monitor.tmux_session_name),
            "attach_command": f"tmux attach -t {state.monitor.tmux_session_name}",
            "poll_interval_seconds": state.poll_interval_seconds,
            "samples_path": state.monitor.samples_path,
            "transitions_path": state.monitor.transitions_path,
            "dashboard_log_path": state.monitor.dashboard_log_path,
        },
    }
    client = HoumaoServerClient(state.server.api_base_url, timeout_seconds=3.0)
    for slot, session in state.agents.items():
        agent_payload: dict[str, Any] = {
            "tool": session.tool,
            "provider": session.provider,
            "profile_name": session.profile_name,
            "session_name": session.session_name,
            "terminal_id": session.terminal_id,
            "tmux_session_name": session.tmux_session_name,
            "tmux_alive": _tmux_session_exists(session.tmux_session_name),
            "attach_command": f"tmux attach -t {session.tmux_session_name}",
            "workdir": session.workdir,
            "brain_home_path": session.brain_home_path,
            "brain_manifest_path": session.brain_manifest_path,
            "session_manifest_path": session.session_manifest_path,
            "session_root": session.session_root,
            "launch_stdout_path": session.launch_stdout_path,
            "launch_stderr_path": session.launch_stderr_path,
            "tracked_state": None,
            "session_payload": None,
            "error": None,
        }
        try:
            agent_payload["session_payload"] = client.get_session(session.session_name).model_dump(
                mode="json"
            )
            agent_payload["tracked_state"] = client.terminal_state(session.terminal_id).model_dump(
                mode="json"
            )
        except Exception as exc:
            agent_payload["error"] = str(exc)
        payload["agents"][slot] = agent_payload
    return payload


def stop_demo(
    *,
    repo_root: Path,
    run_root: Path | None,
    json_output: bool,
) -> dict[str, Any]:
    """Stop both agent sessions, the monitor, and the demo-owned server."""

    del json_output
    state = _load_selected_demo_state(repo_root=repo_root, run_root=run_root)
    client = HoumaoServerClient(state.server.api_base_url, timeout_seconds=3.0)
    stop_results: dict[str, Any] = {"agents": {}, "monitor": None, "server": None}

    for slot, session in state.agents.items():
        try:
            delete_payload = client.delete_session(session.session_name)
            _wait_for_session_absent(
                client=client,
                session_name=session.session_name,
                timeout_seconds=state.stop_timeout_seconds,
            )
            stop_results["agents"][slot] = {
                "status": "stopped",
                "session_name": session.session_name,
                "delete_payload": delete_payload,
            }
        except Exception as exc:
            stop_results["agents"][slot] = {
                "status": "error",
                "session_name": session.session_name,
                "detail": str(exc),
            }

    monitor_status = "already_stopped"
    if _tmux_session_exists(state.monitor.tmux_session_name):
        kill_tmux_session(session_name=state.monitor.tmux_session_name)
        monitor_status = "stopped"
    stop_results["monitor"] = {
        "session_name": state.monitor.tmux_session_name,
        "status": monitor_status,
    }

    stop_results["server"] = _stop_server_process(
        pid=state.server.pid,
        api_base_url=state.server.api_base_url,
        timeout_seconds=state.stop_timeout_seconds,
    )

    updated_state = replace(
        state,
        active=False,
        stopped_at_utc=_now_utc_iso(),
    )
    save_demo_state(Path(updated_state.run_root) / "control" / "demo_state.json", updated_state)
    return {
        "change": "houmao-server-dual-shadow-watch",
        "run_root": updated_state.run_root,
        "active": updated_state.active,
        "stopped_at_utc": updated_state.stopped_at_utc,
        "artifacts": {
            "preflight_path": str(
                DemoPaths.from_run_root(
                    repo_root=repo_root, run_root=Path(updated_state.run_root)
                ).preflight_report_path
            ),
            "samples_path": updated_state.monitor.samples_path,
            "transitions_path": updated_state.monitor.transitions_path,
            "dashboard_log_path": updated_state.monitor.dashboard_log_path,
            "server_stdout_log_path": updated_state.server.stdout_log_path,
            "server_stderr_log_path": updated_state.server.stderr_log_path,
        },
        "stop_results": stop_results,
    }


def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for the standalone demo driver."""

    parser = argparse.ArgumentParser(
        description="Standalone Houmao-server dual shadow-watch demo driver.",
    )
    subparsers = parser.add_subparsers(dest="command")

    preflight_parser = subparsers.add_parser("preflight", help="Check prerequisites")
    _add_common_args(preflight_parser)
    preflight_parser.add_argument("--json", action="store_true")

    start_parser = subparsers.add_parser("start", help="Start the dual-agent demo")
    _add_common_args(start_parser)
    start_parser.add_argument(
        "--poll-interval-seconds",
        type=float,
        default=DEFAULT_POLL_INTERVAL_SECONDS,
    )
    start_parser.add_argument(
        "--stability-threshold-seconds",
        type=float,
        default=DEFAULT_STABILITY_THRESHOLD_SECONDS,
    )
    start_parser.add_argument(
        "--completion-stability-seconds",
        type=float,
        default=DEFAULT_COMPLETION_STABILITY_SECONDS,
    )
    start_parser.add_argument(
        "--unknown-to-stalled-timeout-seconds",
        type=float,
        default=DEFAULT_UNKNOWN_TO_STALLED_TIMEOUT_SECONDS,
    )
    start_parser.add_argument(
        "--server-start-timeout-seconds",
        type=float,
        default=DEFAULT_SERVER_START_TIMEOUT_SECONDS,
    )
    start_parser.add_argument(
        "--launch-timeout-seconds",
        type=float,
        default=DEFAULT_LAUNCH_TIMEOUT_SECONDS,
    )
    start_parser.add_argument(
        "--stop-timeout-seconds",
        type=float,
        default=DEFAULT_STOP_TIMEOUT_SECONDS,
    )
    start_parser.add_argument("--json", action="store_true")

    inspect_parser = subparsers.add_parser("inspect", help="Inspect persisted demo state")
    inspect_parser.add_argument("--run-root")
    inspect_parser.add_argument("--json", action="store_true")

    stop_parser = subparsers.add_parser("stop", help="Stop the demo and preserve artifacts")
    stop_parser.add_argument("--run-root")
    stop_parser.add_argument("--json", action="store_true")
    return parser


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    """Add arguments shared across preflight and startup."""

    parser.add_argument("--run-root")
    parser.add_argument("--agent-def-dir")
    parser.add_argument("--project-fixture")
    parser.add_argument("--profile-path")
    parser.add_argument("--port", type=int)


def _repo_root() -> Path:
    """Return the repository root derived from this source module location."""

    return Path(__file__).resolve().parents[4]


def _demo_pack_dir(repo_root: Path) -> Path:
    """Return the standalone pack directory."""

    return (repo_root / "scripts" / "demo" / "houmao-server-dual-shadow-watch").resolve()


def _optional_path(value: str | None) -> Path | None:
    """Resolve one optional path-like CLI argument."""

    if value is None or not value.strip():
        return None
    return Path(value).expanduser().resolve()


def _default_agent_def_dir(repo_root: Path) -> Path:
    """Return the default tracked agent-definition root for the demo."""

    return (repo_root.resolve() / "tests" / "fixtures" / "agents").resolve()


def _default_project_fixture(repo_root: Path) -> Path:
    """Return the default projection-oriented dummy-project fixture path."""

    return (
        repo_root.resolve() / "tests" / "fixtures" / "dummy-projects" / "projection-demo-python"
    ).resolve()


def _default_profile_path(repo_root: Path) -> Path:
    """Return the tracked demo-owned projection profile."""

    return (_demo_pack_dir(repo_root) / "profiles" / f"{DEFAULT_PROFILE_NAME}.md").resolve()


def _default_run_root(repo_root: Path) -> Path:
    """Return one fresh timestamped run root under `tmp/demo/`."""

    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    return (
        repo_root.resolve()
        / "tmp"
        / "demo"
        / "houmao-server-dual-shadow-watch"
        / f"{timestamp}-{os.getpid()}"
    ).resolve()


def _prepare_layout(paths: DemoPaths, *, allow_reprovision: bool) -> None:
    """Create the required directory structure for one selected run root."""

    if paths.run_root.exists():
        if not allow_reprovision:
            raise HoumaoServerDualShadowWatchError(
                f"Run root already exists; choose another --run-root: {paths.run_root}"
            )
        shutil.rmtree(paths.run_root)

    for path in (
        paths.run_root,
        paths.control_dir,
        paths.runtime_root,
        paths.registry_root,
        paths.jobs_root,
        paths.server_dir,
        paths.projects_dir,
        paths.monitor_dir,
        paths.logs_dir,
    ):
        path.mkdir(parents=True, exist_ok=True)


def _output_root_status(*, repo_root: Path, selected_run_root: Path) -> dict[str, Any]:
    """Return whether the selected output root is fresh or safely reusable."""

    paths = DemoPaths.from_run_root(repo_root=repo_root, run_root=selected_run_root)
    if not selected_run_root.exists():
        return {"status": "fresh", "ok": True, "reason": "run root does not exist yet"}
    if paths.state_path.exists():
        state = load_demo_state(paths.state_path)
        if not state.active:
            return {
                "status": "reusable",
                "ok": True,
                "reason": "existing stopped run may be reprovisioned",
            }
        return {
            "status": "blocked",
            "ok": False,
            "reason": "run root already contains an active demo state",
        }
    return {
        "status": "blocked",
        "ok": False,
        "reason": "run root already exists without a stopped demo state",
    }


def _resolve_lane_preflight(*, repo_root: Path, agent_def_dir: Path, slot: str) -> LanePreflight:
    """Resolve tracked prerequisite paths for one selected tool lane."""

    del repo_root
    tool = slot
    provider = _PROVIDER_BY_SLOT[slot]
    resolved_launch = resolve_demo_preset_launch(
        agent_def_dir=agent_def_dir,
        preset_path=agent_def_dir / "roles" / "projection-demo" / "presets" / tool / "default.yaml",
    )
    blueprint_path = resolved_launch.preset_path
    recipe = resolved_launch.preset
    adapter = resolved_launch.adapter
    config_profile_dir = resolved_launch.setup_path
    if resolved_launch.auth_path is None or resolved_launch.auth_env_path is None:
        raise HoumaoServerDualShadowWatchError(
            f"selected preset does not declare auth-backed launch inputs: {resolved_launch.preset_path}"
        )
    credential_profile_dir = resolved_launch.auth_path
    credential_env_path = resolved_launch.auth_env_path
    selected_env, selected_env_names = parse_allowlisted_env(
        credential_env_path,
        adapter.credential_env_allowlist,
    )
    required_paths = resolved_launch.required_auth_paths
    optional_paths = resolved_launch.optional_auth_paths
    launch_executable = shutil.which(adapter.launch_executable)
    if launch_executable is None:
        raise HoumaoServerDualShadowWatchError(
            f"selected tool executable not found on PATH: {adapter.launch_executable}"
        )

    return LanePreflight(
        slot=slot,
        tool=recipe.tool,
        provider=provider,
        blueprint_path=blueprint_path,
        brain_recipe_path=resolved_launch.preset_path,
        role_name=resolved_launch.role_name,
        config_profile=recipe.config_profile,
        credential_profile=recipe.credential_profile,
        config_profile_dir=config_profile_dir,
        credential_profile_dir=credential_profile_dir,
        credential_env_path=credential_env_path,
        required_credential_paths=required_paths,
        optional_credential_paths=optional_paths,
        selected_allowlisted_env=selected_env,
        selected_allowlisted_env_keys=tuple(selected_env_names),
        launch_executable=launch_executable,
        home_selector_env_var=adapter.home_selector_env_var,
    )


def _prepare_lane(
    *,
    repo_root: Path,
    agent_def_dir: Path,
    paths: DemoPaths,
    slot: str,
    lane_preflight: LanePreflight,
    workdir: Path,
    session_name: str,
) -> PreparedLane:
    """Build and bootstrap one provider home for live launch."""

    recipe = load_brain_recipe(lane_preflight.brain_recipe_path)
    build_result = build_brain_home(
        BuildRequest(
            agent_def_dir=agent_def_dir,
            runtime_root=paths.runtime_root,
            tool=lane_preflight.tool,
            skills=list(recipe.skills),
            config_profile=lane_preflight.config_profile,
            credential_profile=lane_preflight.credential_profile,
            recipe_path=lane_preflight.brain_recipe_path,
            recipe_launch_overrides=recipe.launch_overrides,
            agent_name=recipe.default_agent_name,
            home_id=f"projection-demo-{slot}",
            reuse_home=False,
            operator_prompt_mode=recipe.operator_prompt_mode,
        )
    )
    del repo_root
    return PreparedLane(
        slot=slot,
        tool=lane_preflight.tool,
        provider=lane_preflight.provider,
        workdir=workdir,
        session_name=session_name,
        preflight=lane_preflight,
        build_result=build_result,
    )


def _build_demo_environment(*, paths: DemoPaths, lanes: dict[str, PreparedLane]) -> dict[str, str]:
    """Return the shared environment used by the demo-owned server and helper CLIs."""

    env = dict(os.environ)
    env["HOME"] = str(paths.server_home_dir)
    env[AGENTSYS_GLOBAL_RUNTIME_DIR_ENV_VAR] = str(paths.runtime_root)
    env[AGENTSYS_GLOBAL_REGISTRY_DIR_ENV_VAR] = str(paths.registry_root)
    env[AGENTSYS_LOCAL_JOBS_DIR_ENV_VAR] = str(paths.jobs_root)
    for lane in lanes.values():
        env.update(lane.preflight.selected_allowlisted_env)
        env[lane.preflight.home_selector_env_var] = str(lane.build_result.home_path)
    return env


def _start_server_process(
    *,
    api_base_url: str,
    paths: DemoPaths,
    poll_interval_seconds: float,
    stability_threshold_seconds: float,
    completion_stability_seconds: float,
    unknown_to_stalled_timeout_seconds: float,
    timeout_seconds: float,
    env: dict[str, str],
) -> subprocess.Popen[bytes]:
    """Start the demo-owned Houmao server and wait for health."""

    stdout_path = paths.logs_dir / "houmao-server.stdout.log"
    stderr_path = paths.logs_dir / "houmao-server.stderr.log"
    stdout_handle = stdout_path.open("wb")
    stderr_handle = stderr_path.open("wb")
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "houmao.server",
            "serve",
            "--api-base-url",
            api_base_url,
            "--runtime-root",
            str(paths.server_runtime_root),
            "--watch-poll-interval-seconds",
            str(poll_interval_seconds),
            "--stability-threshold-seconds",
            str(stability_threshold_seconds),
            "--completion-stability-seconds",
            str(completion_stability_seconds),
            "--unknown-to-stalled-timeout-seconds",
            str(unknown_to_stalled_timeout_seconds),
        ],
        cwd=str(_repo_root()),
        stdout=stdout_handle,
        stderr=stderr_handle,
        env=env,
        start_new_session=True,
    )
    stdout_handle.close()
    stderr_handle.close()
    _wait_for_server_health(api_base_url=api_base_url, timeout_seconds=timeout_seconds)
    return process


def _wait_for_server_health(*, api_base_url: str, timeout_seconds: float) -> None:
    """Wait until the target Houmao server is healthy or fail explicitly."""

    client = HoumaoServerClient(api_base_url, timeout_seconds=1.0)
    deadline = time.monotonic() + timeout_seconds
    last_error = "server did not become healthy"
    while time.monotonic() < deadline:
        try:
            health = client.health_extended()
            cao_health = client.health()
        except Exception as exc:
            last_error = str(exc)
            time.sleep(0.25)
            continue
        if (
            health.status == "ok"
            and health.houmao_service == "houmao-server"
            and cao_health.status == "ok"
        ):
            return
        last_error = json.dumps(
            {
                "houmao": health.model_dump(mode="json"),
                "cao": cao_health.model_dump(mode="json"),
            },
            sort_keys=True,
        )
        time.sleep(0.25)
    raise HoumaoServerDualShadowWatchError(
        f"timed out waiting for demo-owned houmao-server health at {api_base_url}: {last_error}"
    )


def _install_projection_profile(
    *,
    api_base_url: str,
    profile_path: Path,
    provider: str,
    env: dict[str, str],
    stdout_path: Path,
    stderr_path: Path,
) -> None:
    """Install the tracked demo profile into the demo-owned CAO home."""

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "houmao.srv_ctrl",
            "install",
            str(profile_path),
            "--provider",
            provider,
            "--port",
            api_base_url.rsplit(":", 1)[-1],
        ],
        cwd=str(_repo_root()),
        check=False,
        capture_output=True,
        env=env,
    )
    stdout_path.write_bytes(result.stdout)
    stderr_path.write_bytes(result.stderr)
    if result.returncode != 0:
        detail = (
            result.stderr.decode("utf-8", errors="replace").strip()
            or result.stdout.decode(
                "utf-8",
                errors="replace",
            ).strip()
        )
        raise HoumaoServerDualShadowWatchError(
            f"failed to install projection-demo profile for `{provider}`: {detail}"
        )


def _launch_lane(
    *,
    client: HoumaoServerClient,
    lane: PreparedLane,
    paths: DemoPaths,
    timeout_seconds: float,
    env: dict[str, str],
) -> AgentSessionState:
    """Launch one live session through `houmao-mgr` and persist its metadata."""

    stdout_path = paths.logs_dir / f"launch-{lane.slot}.stdout.log"
    stderr_path = paths.logs_dir / f"launch-{lane.slot}.stderr.log"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "houmao.srv_ctrl",
            "launch",
            "--headless",
            "--yolo",
            "--session-name",
            lane.session_name,
            "--provider",
            lane.provider,
            "--agents",
            DEFAULT_PROFILE_NAME,
            "--port",
            str(client.base_url.rsplit(":", 1)[-1]),
        ],
        cwd=str(lane.workdir),
        check=False,
        capture_output=True,
        env=env,
    )
    stdout_path.write_bytes(result.stdout)
    stderr_path.write_bytes(result.stderr)
    if result.returncode != 0:
        detail = (
            result.stderr.decode("utf-8", errors="replace").strip()
            or result.stdout.decode(
                "utf-8",
                errors="replace",
            ).strip()
        )
        raise HoumaoServerDualShadowWatchError(
            f"timed out or failed while launching `{lane.slot}` through houmao-mgr: {detail}"
        )

    session_payload = _wait_for_session_registration(
        client=client,
        session_name=lane.session_name,
        timeout_seconds=timeout_seconds,
    )
    terminal_id = _terminal_id_from_session_payload(session_payload, session_name=lane.session_name)
    manifest_path = default_manifest_path(
        paths.runtime_root, "houmao_server_rest", lane.session_name
    )
    handle = load_session_manifest(manifest_path)
    payload = handle.payload
    agent_name = str(payload.get("agent_name", "")).strip()
    agent_id = str(payload.get("agent_id", "")).strip()
    if not agent_name:
        normalized = normalize_agent_identity_name(lane.session_name)
        agent_name = normalized.canonical_name
    if not agent_id:
        agent_id = derive_agent_id_from_name(agent_name)

    return AgentSessionState(
        slot=lane.slot,
        tool=lane.tool,
        provider=lane.provider,
        profile_name=DEFAULT_PROFILE_NAME,
        session_name=lane.session_name,
        terminal_id=terminal_id,
        tmux_session_name=lane.session_name,
        workdir=str(lane.workdir),
        agent_name=agent_name,
        agent_id=agent_id,
        blueprint_path=str(lane.preflight.blueprint_path),
        brain_recipe_path=str(lane.preflight.brain_recipe_path),
        role_name=lane.preflight.role_name,
        config_profile=lane.preflight.config_profile,
        credential_profile=lane.preflight.credential_profile,
        brain_home_path=str(lane.build_result.home_path),
        brain_manifest_path=str(lane.build_result.manifest_path),
        launch_helper_path=str(lane.build_result.launch_helper_path),
        session_manifest_path=str(manifest_path),
        session_root=str(manifest_path.parent),
        launch_stdout_path=str(stdout_path),
        launch_stderr_path=str(stderr_path),
    )


def _wait_for_session_registration(
    *,
    client: HoumaoServerClient,
    session_name: str,
    timeout_seconds: float,
) -> CaoSessionDetail:
    """Wait until a launched session is visible through Houmao server queries."""

    deadline = time.monotonic() + timeout_seconds
    last_error = "session did not appear"
    while time.monotonic() < deadline:
        try:
            payload = client.get_session(session_name)
        except Exception as exc:
            last_error = str(exc)
            time.sleep(0.25)
            continue
        if payload.terminals:
            return payload
        last_error = f"session `{session_name}` had no terminals yet"
        time.sleep(0.25)
    raise HoumaoServerDualShadowWatchError(
        f"timed out waiting for session registration for `{session_name}`: {last_error}"
    )


def _wait_for_session_absent(
    *,
    client: HoumaoServerClient,
    session_name: str,
    timeout_seconds: float,
) -> None:
    """Wait until one session disappears from server queries."""

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            client.get_session(session_name)
        except CaoApiError as exc:
            if exc.status_code == 404:
                return
        except Exception:
            return
        time.sleep(0.25)
    raise HoumaoServerDualShadowWatchError(
        f"timed out waiting for `{session_name}` to disappear from houmao-server"
    )


def _terminal_id_from_session_payload(payload: CaoSessionDetail, *, session_name: str) -> str:
    """Extract the first terminal id from one session payload."""

    terminals = payload.terminals
    if not terminals:
        raise HoumaoServerDualShadowWatchError(
            f"houmao-server did not return terminals for `{session_name}`"
        )
    terminal_id = terminals[0].id.strip()
    if not terminal_id:
        raise HoumaoServerDualShadowWatchError(
            f"houmao-server terminal payload is missing `id` for `{session_name}`"
        )
    return terminal_id


def _start_monitor_tmux_session(
    *,
    session_name: str,
    working_directory: Path,
    command: tuple[str, ...],
    log_path: Path,
    timeout_seconds: float,
) -> None:
    """Start the Rich monitor in its own detached tmux session."""

    log_path.parent.mkdir(parents=True, exist_ok=True)
    quoted_command = shlex.join([*command, "--dashboard-log-path", str(log_path)])
    result = subprocess.run(
        [
            "tmux",
            "new-session",
            "-d",
            "-s",
            session_name,
            "-c",
            str(working_directory),
            quoted_command,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = tmux_error_detail(result)
        raise HoumaoServerDualShadowWatchError(
            f"Failed to start monitor tmux session `{session_name}`: {detail or 'unknown tmux error'}"
        )

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if _tmux_session_exists(session_name):
            return
        time.sleep(0.2)
    raise HoumaoServerDualShadowWatchError(
        f"timed out waiting for monitor tmux session `{session_name}` to appear"
    )


def _provision_project_fixture(*, fixture_path: Path, project_workdir: Path) -> None:
    """Copy a tracked dummy project and initialize a fresh standalone git repo."""

    resolved_fixture = fixture_path.resolve()
    resolved_project_workdir = project_workdir.resolve()
    if (resolved_fixture / ".git").exists():
        raise HoumaoServerDualShadowWatchError(
            "Dummy project fixture must stay source-only and may not contain `.git`: "
            f"{resolved_fixture}"
        )
    shutil.copytree(resolved_fixture, resolved_project_workdir, symlinks=False)
    _initialize_demo_git_repo(resolved_project_workdir)


def _initialize_demo_git_repo(project_workdir: Path) -> None:
    """Initialize one copied dummy project as a fresh standalone git repository."""

    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": FIXED_DEMO_PROJECT_AUTHOR_NAME,
        "GIT_AUTHOR_EMAIL": FIXED_DEMO_PROJECT_AUTHOR_EMAIL,
        "GIT_COMMITTER_NAME": FIXED_DEMO_PROJECT_AUTHOR_NAME,
        "GIT_COMMITTER_EMAIL": FIXED_DEMO_PROJECT_AUTHOR_EMAIL,
        "GIT_AUTHOR_DATE": FIXED_DEMO_PROJECT_COMMIT_UTC,
        "GIT_COMMITTER_DATE": FIXED_DEMO_PROJECT_COMMIT_UTC,
    }
    _run_git(["git", "init", "--initial-branch", "main"], cwd=project_workdir, env=env)
    _run_git(["git", "add", "--all"], cwd=project_workdir, env=env)
    _run_git(
        [
            "git",
            "commit",
            "--allow-empty",
            "--no-gpg-sign",
            "-m",
            FIXED_DEMO_PROJECT_COMMIT_MESSAGE,
        ],
        cwd=project_workdir,
        env=env,
    )


def _run_git(args: list[str], *, cwd: Path, env: dict[str, str]) -> None:
    """Run one required git command for fixture provisioning."""

    result = subprocess.run(
        args,
        cwd=str(cwd),
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return
    detail = result.stderr.strip() or result.stdout.strip() or "git command failed"
    raise HoumaoServerDualShadowWatchError(f"{' '.join(args)} failed in {cwd}: {detail}")


def _command_check_payload(command_name: str) -> dict[str, Any]:
    """Return whether one required executable is currently available."""

    path = shutil.which(command_name)
    return {"ok": path is not None, "path": path}


def _select_port(requested_port: int | None) -> int:
    """Select one loopback port for the demo-owned server."""

    if requested_port is not None:
        return requested_port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _port_is_available(port: int) -> bool:
    """Return whether one loopback port is currently free to bind."""

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def _session_name(run_root: Path, slot: str) -> str:
    """Return one explicit CAO session name for one lane."""

    return f"cao-houmao-shadow-watch-{run_root.name}-{slot}"


def _monitor_session_name(run_root: Path) -> str:
    """Return one unique tmux session name for the live monitor."""

    return f"houmao-shadow-watch-monitor-{run_root.name}"


def _server_health_payload(api_base_url: str) -> dict[str, Any]:
    """Return one health payload or an error wrapper for inspection."""

    client = HoumaoServerClient(api_base_url, timeout_seconds=2.0)
    try:
        return {"ok": True, "payload": client.health_extended().model_dump(mode="json")}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _cleanup_partial_start(
    *,
    client: HoumaoServerClient,
    agent_states: dict[str, AgentSessionState],
    monitor_session_name: str | None,
    server_pid: int,
    stop_timeout_seconds: float,
) -> None:
    """Best-effort cleanup after a partial startup failure."""

    for session in agent_states.values():
        try:
            client.delete_session(session.session_name)
        except Exception:
            continue
    if monitor_session_name is not None and _tmux_session_exists(monitor_session_name):
        try:
            kill_tmux_session(session_name=monitor_session_name)
        except Exception:
            pass
    try:
        _stop_server_process(
            pid=server_pid,
            api_base_url=client.base_url,
            timeout_seconds=stop_timeout_seconds,
        )
    except Exception:
        pass


def _stop_server_process(*, pid: int, api_base_url: str, timeout_seconds: float) -> dict[str, Any]:
    """Stop the demo-owned Houmao server process and wait for exit."""

    if pid <= 0:
        return {"status": "already_stopped", "pid": pid}
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return {"status": "already_stopped", "pid": pid}

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if not _pid_exists(pid) and not _server_health_payload(api_base_url)["ok"]:
            return {"status": "stopped", "pid": pid}
        time.sleep(0.25)

    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        return {"status": "stopped", "pid": pid, "forced": False}
    time.sleep(0.2)
    return {"status": "forced", "pid": pid}


def _pid_exists(pid: int) -> bool:
    """Return whether one process id currently exists."""

    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _load_selected_demo_state(
    *, repo_root: Path, run_root: Path | None
) -> HoumaoServerDualShadowWatchState:
    """Load demo state from one explicit or pointer-selected run root."""

    if run_root is not None:
        state_path = DemoPaths.from_run_root(repo_root=repo_root, run_root=run_root).state_path
        if not state_path.is_file():
            raise HoumaoServerDualShadowWatchError(f"Demo state not found: {state_path}")
        return load_demo_state(state_path)

    pointer_path = (
        repo_root.resolve()
        / "tmp"
        / "demo"
        / "houmao-server-dual-shadow-watch"
        / "current_run_root.txt"
    ).resolve()
    if not pointer_path.is_file():
        raise HoumaoServerDualShadowWatchError(
            "No current demo run root recorded; start a run first or pass --run-root."
        )
    selected_run_root = Path(pointer_path.read_text(encoding="utf-8").strip()).resolve()
    state_path = DemoPaths.from_run_root(repo_root=repo_root, run_root=selected_run_root).state_path
    if not state_path.is_file():
        raise HoumaoServerDualShadowWatchError(f"Demo state not found: {state_path}")
    return load_demo_state(state_path)


def _write_current_run_root(pointer_path: Path, run_root: Path) -> None:
    """Persist the latest run-root pointer for inspect/stop convenience."""

    pointer_path.parent.mkdir(parents=True, exist_ok=True)
    pointer_path.write_text(f"{run_root.resolve()}\n", encoding="utf-8")


def _emit_payload(payload: dict[str, Any], *, json_output: bool) -> None:
    """Render one command payload as JSON or concise text."""

    if json_output:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return

    print(f"change: {payload['change']}")
    if "ok" in payload:
        print(f"ok: {payload['ok']}")
    if "run_root" in payload:
        print(f"run_root: {payload['run_root']}")
    if "active" in payload:
        print(f"active: {payload['active']}")
    if "server" in payload and isinstance(payload["server"], dict):
        print(f"api_base_url: {payload['server'].get('api_base_url')}")
    if "monitor" in payload and isinstance(payload["monitor"], dict):
        print(f"monitor_attach: {payload['monitor'].get('attach_command')}")
    for slot, agent in payload.get("agents", {}).items():
        if not isinstance(agent, dict):
            continue
        print(
            f"{slot}_attach: {agent.get('attach_command')} "
            f"(terminal={agent.get('terminal_id')}, session={agent.get('session_name')})"
        )
    if payload.get("blockers"):
        print("blockers:")
        for blocker in payload["blockers"]:
            print(f"  - {blocker}")


def _require_positive(value: float, *, context: str) -> None:
    """Require one CLI float option to be positive."""

    if value <= 0:
        raise HoumaoServerDualShadowWatchError(f"{context} must be > 0")


def _tmux_session_exists(session_name: str) -> bool:
    """Return whether the selected tmux session currently exists."""

    result = has_tmux_session(session_name=session_name)
    return result.returncode == 0


def _now_utc_iso() -> str:
    """Return one current UTC timestamp string."""

    return datetime.now(UTC).isoformat(timespec="seconds")
