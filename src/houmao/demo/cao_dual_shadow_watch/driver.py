"""Standalone driver for the dual-agent shadow-watch demo pack."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from houmao.agents.brain_builder import BuildRequest, build_brain_home
from houmao.agents.brain_builder import load_brain_recipe as load_brain_recipe_file
from houmao.agents.realm_controller.backends.cao_rest import CaoRestSession
from houmao.agents.realm_controller.backends.tmux_runtime import (
    ensure_tmux_available,
    has_tmux_session,
    kill_tmux_session,
    tmux_error_detail,
)
from houmao.agents.realm_controller.loaders import load_blueprint
from houmao.agents.realm_controller.runtime import (
    RuntimeSessionController,
    resume_runtime_session,
    start_runtime_session,
)
from houmao.cao.server_launcher import (
    CaoServerLauncherConfig,
    load_cao_server_launcher_config,
    resolve_cao_server_runtime_artifacts,
    start_cao_server,
    stop_cao_server,
)
from houmao.cao.server_launcher import ProxyPolicy
from houmao.cao.server_launcher import CaoServerLauncherError
from houmao.cao.no_proxy import normalize_cao_base_url

from houmao.demo.cao_dual_shadow_watch.models import (
    DEFAULT_COMPLETION_STABILITY_SECONDS,
    DEFAULT_POLL_INTERVAL_SECONDS,
    DEFAULT_SHADOW_PARSING_MODE,
    DEFAULT_UNKNOWN_TO_STALLED_TIMEOUT_SECONDS,
    AgentSessionState,
    DemoLauncherState,
    DemoPaths,
    DualShadowWatchDemoState,
    MonitorSessionState,
    load_demo_state,
    save_demo_state,
)


FIXED_DEMO_PROJECT_COMMIT_UTC = "2026-03-18T12:00:00Z"
FIXED_DEMO_PROJECT_COMMIT_MESSAGE = "Initial projection demo snapshot"
FIXED_DEMO_PROJECT_AUTHOR_NAME = "Houmao Demo Fixture"
FIXED_DEMO_PROJECT_AUTHOR_EMAIL = "houmao-demo-fixture@example.invalid"


class DualShadowWatchDemoError(RuntimeError):
    """Raised when the standalone demo cannot proceed safely."""


def main(argv: list[str] | None = None) -> int:
    """Run the standalone dual-agent shadow-watch demo driver."""

    parser = _build_parser()
    args = parser.parse_args(argv or sys.argv[1:])
    try:
        if args.command == "start":
            payload = start_demo(
                repo_root=_repo_root(),
                run_root=_optional_path(args.run_root),
                agent_def_dir=_optional_path(args.agent_def_dir),
                project_fixture=_optional_path(args.project_fixture),
                launcher_config_path=_optional_path(args.launcher_config),
                cao_base_url=args.cao_base_url,
                cao_home_dir=_optional_path(args.cao_home_dir),
                cao_profile_store=_optional_path(args.cao_profile_store),
                poll_interval_seconds=float(args.poll_interval_seconds),
                completion_stability_seconds=float(args.completion_stability_seconds),
                unknown_to_stalled_timeout_seconds=float(args.unknown_to_stalled_timeout_seconds),
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
    except (DualShadowWatchDemoError, CaoServerLauncherError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    parser.print_help()
    return 1


def start_demo(
    *,
    repo_root: Path,
    run_root: Path | None,
    agent_def_dir: Path | None,
    project_fixture: Path | None,
    launcher_config_path: Path | None,
    cao_base_url: str | None,
    cao_home_dir: Path | None,
    cao_profile_store: Path | None,
    poll_interval_seconds: float,
    completion_stability_seconds: float,
    unknown_to_stalled_timeout_seconds: float,
    json_output: bool,
) -> dict[str, Any]:
    """Start the shared CAO server, both agent sessions, and the monitor."""

    del json_output
    ensure_tmux_available()
    _require_positive(poll_interval_seconds, context="--poll-interval-seconds")
    _require_positive(
        completion_stability_seconds,
        context="--completion-stability-seconds",
    )
    _require_positive(
        unknown_to_stalled_timeout_seconds,
        context="--unknown-to-stalled-timeout-seconds",
    )
    resolved_agent_def_dir = (
        agent_def_dir.resolve() if agent_def_dir is not None else _default_agent_def_dir(repo_root)
    )
    resolved_project_fixture = (
        project_fixture.resolve()
        if project_fixture is not None
        else _default_project_fixture(repo_root)
    )
    if not resolved_agent_def_dir.is_dir():
        raise DualShadowWatchDemoError(
            f"Agent definition directory not found: {resolved_agent_def_dir}"
        )
    if not resolved_project_fixture.is_dir():
        raise DualShadowWatchDemoError(f"Project fixture not found: {resolved_project_fixture}")

    selected_run_root = run_root.resolve() if run_root is not None else _default_run_root(repo_root)
    if selected_run_root.exists():
        raise DualShadowWatchDemoError(
            f"Run root already exists; choose another --run-root: {selected_run_root}"
        )
    paths = DemoPaths.from_run_root(repo_root=repo_root, run_root=selected_run_root)
    _prepare_layout(paths)

    selected_launcher_config_path = (
        launcher_config_path.resolve()
        if launcher_config_path is not None
        else _default_launcher_config(repo_root)
    )
    launcher_config = _prepare_launcher_config(
        source_config_path=selected_launcher_config_path,
        target_config_path=paths.launcher_config_path,
        runtime_root=paths.run_root / "cao-runtime",
        cao_base_url=cao_base_url,
        cao_home_dir=cao_home_dir,
    )
    launcher_result = start_cao_server(launcher_config)
    launcher_artifacts = resolve_cao_server_runtime_artifacts(launcher_config)
    resolved_profile_store = (
        cao_profile_store.resolve()
        if cao_profile_store is not None
        else _default_cao_profile_store(launcher_config.home_dir)
    )

    started_controllers: list[RuntimeSessionController] = []
    monitor_session_name: str | None = None
    try:
        _provision_project_fixture(
            fixture_path=resolved_project_fixture,
            project_workdir=paths.claude_project_dir,
        )
        _provision_project_fixture(
            fixture_path=resolved_project_fixture,
            project_workdir=paths.codex_project_dir,
        )

        claude_session = _start_agent_session(
            repo_root=repo_root,
            slot="claude",
            blueprint_path=(
                resolved_agent_def_dir / "blueprints" / "projection-demo-claude.yaml"
            ).resolve(),
            agent_def_dir=resolved_agent_def_dir,
            runtime_root=paths.runtime_root,
            workdir=paths.claude_project_dir,
            api_base_url=launcher_config.base_url,
            cao_profile_store=resolved_profile_store,
        )
        started_controllers.append(claude_session["controller"])

        codex_session = _start_agent_session(
            repo_root=repo_root,
            slot="codex",
            blueprint_path=(
                resolved_agent_def_dir / "blueprints" / "projection-demo-codex.yaml"
            ).resolve(),
            agent_def_dir=resolved_agent_def_dir,
            runtime_root=paths.runtime_root,
            workdir=paths.codex_project_dir,
            api_base_url=launcher_config.base_url,
            cao_profile_store=resolved_profile_store,
        )
        started_controllers.append(codex_session["controller"])

        created_at_utc = _now_utc_iso()
        monitor_session_name = _monitor_session_name()
        monitor_command = (
            sys.executable,
            str(
                (
                    repo_root
                    / "scripts"
                    / "demo"
                    / "cao-dual-shadow-watch"
                    / "scripts"
                    / "watch_dashboard.py"
                ).resolve()
            ),
            "--state-file",
            str(paths.state_path),
        )
        state = DualShadowWatchDemoState(
            schema_version=1,
            active=True,
            created_at_utc=created_at_utc,
            stopped_at_utc=None,
            repo_root=str(repo_root.resolve()),
            run_root=str(paths.run_root),
            agent_def_dir=str(resolved_agent_def_dir),
            project_fixture=str(resolved_project_fixture),
            parsing_mode=DEFAULT_SHADOW_PARSING_MODE,
            poll_interval_seconds=poll_interval_seconds,
            completion_stability_seconds=completion_stability_seconds,
            unknown_to_stalled_timeout_seconds=unknown_to_stalled_timeout_seconds,
            launcher=DemoLauncherState(
                config_path=str(launcher_config.config_path),
                base_url=launcher_config.base_url,
                runtime_root=str(launcher_config.runtime_root),
                home_dir=str((launcher_config.home_dir or Path.home()).resolve()),
                profile_store=str(resolved_profile_store),
                started_new_process=launcher_result.started_new_process,
                reused_existing_process=launcher_result.reused_existing_process,
                artifact_dir=str(launcher_artifacts.artifact_dir),
                log_file=str(launcher_artifacts.log_file),
                ownership_file=str(launcher_artifacts.ownership_file),
            ),
            agents={
                "claude": claude_session["state"],
                "codex": codex_session["state"],
            },
            monitor=MonitorSessionState(
                tmux_session_name=monitor_session_name,
                command=monitor_command,
                samples_path=str(paths.monitor_dir / "samples.ndjson"),
                transitions_path=str(paths.monitor_dir / "transitions.ndjson"),
                dashboard_log_path=str(paths.logs_dir / "monitor-dashboard.log"),
            ),
        )
        save_demo_state(paths.state_path, state)
        _write_current_run_root(paths.current_run_root_path, paths.run_root)
        _start_monitor_tmux_session(
            session_name=monitor_session_name,
            working_directory=paths.run_root,
            command=monitor_command,
            log_path=Path(state.monitor.dashboard_log_path),
        )
    except Exception:
        _cleanup_partial_start(
            started_controllers=started_controllers,
            launcher_config=launcher_config,
            started_new_cao_process=launcher_result.started_new_process,
            monitor_session_name=monitor_session_name,
        )
        raise

    state = load_demo_state(paths.state_path)
    return _start_or_inspect_payload(state, include_health=True)


def inspect_demo(
    *,
    repo_root: Path,
    run_root: Path | None,
    json_output: bool,
) -> dict[str, Any]:
    """Inspect persisted demo state and current tmux liveliness."""

    del json_output
    state = _load_selected_demo_state(repo_root=repo_root, run_root=run_root)
    return _start_or_inspect_payload(state, include_health=True)


def stop_demo(
    *,
    repo_root: Path,
    run_root: Path | None,
    json_output: bool,
) -> dict[str, Any]:
    """Stop both agent sessions and the monitor tmux session."""

    del json_output
    state = _load_selected_demo_state(repo_root=repo_root, run_root=run_root)
    resolved_agent_def_dir = Path(state.agent_def_dir).resolve()
    stop_results: dict[str, Any] = {"agents": {}, "monitor": None, "cao_launcher": None}
    for slot, session in state.agents.items():
        manifest_path = Path(session.session_manifest_path).resolve()
        try:
            controller = resume_runtime_session(
                agent_def_dir=resolved_agent_def_dir,
                session_manifest_path=manifest_path,
                cao_parsing_mode=DEFAULT_SHADOW_PARSING_MODE,
            )
            result = controller.stop()
            stop_results["agents"][slot] = {
                "status": result.status,
                "detail": result.detail,
            }
        except Exception as exc:
            stop_results["agents"][slot] = {
                "status": "error",
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

    launcher_config = load_cao_server_launcher_config(Path(state.launcher.config_path))
    if state.launcher.started_new_process:
        launcher_stop_result = stop_cao_server(launcher_config)
        stop_results["cao_launcher"] = {
            "stopped": launcher_stop_result.stopped,
            "already_stopped": launcher_stop_result.already_stopped,
            "verification_passed": launcher_stop_result.verification_passed,
        }
    else:
        stop_results["cao_launcher"] = {
            "stopped": False,
            "already_stopped": True,
            "verification_passed": None,
        }

    updated_state = replace(
        state,
        active=False,
        stopped_at_utc=_now_utc_iso(),
    )
    save_demo_state(Path(updated_state.run_root) / "control" / "demo_state.json", updated_state)
    return {
        "change": "cao-dual-shadow-watch",
        "run_root": updated_state.run_root,
        "active": updated_state.active,
        "stopped_at_utc": updated_state.stopped_at_utc,
        "artifacts": {
            "samples_path": updated_state.monitor.samples_path,
            "transitions_path": updated_state.monitor.transitions_path,
            "dashboard_log_path": updated_state.monitor.dashboard_log_path,
        },
        "stop_results": stop_results,
    }


def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for the standalone demo driver."""

    parser = argparse.ArgumentParser(
        description="Standalone dual-agent CAO shadow-watch demo driver.",
    )
    subparsers = parser.add_subparsers(dest="command")

    start_parser = subparsers.add_parser("start", help="Start the dual-agent demo")
    _add_common_run_args(start_parser)
    start_parser.add_argument("--agent-def-dir")
    start_parser.add_argument("--project-fixture")
    start_parser.add_argument("--launcher-config")
    start_parser.add_argument("--cao-base-url")
    start_parser.add_argument("--cao-home-dir")
    start_parser.add_argument("--cao-profile-store")
    start_parser.add_argument(
        "--poll-interval-seconds",
        type=float,
        default=DEFAULT_POLL_INTERVAL_SECONDS,
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
    start_parser.add_argument("--json", action="store_true")

    inspect_parser = subparsers.add_parser("inspect", help="Inspect persisted demo state")
    _add_common_run_args(inspect_parser)
    inspect_parser.add_argument("--json", action="store_true")

    stop_parser = subparsers.add_parser("stop", help="Stop the demo and preserve artifacts")
    _add_common_run_args(stop_parser)
    stop_parser.add_argument("--json", action="store_true")
    return parser


def _add_common_run_args(parser: argparse.ArgumentParser) -> None:
    """Add arguments shared across the demo lifecycle commands."""

    parser.add_argument("--run-root")


def _repo_root() -> Path:
    """Return the repository root derived from this source module location."""

    return Path(__file__).resolve().parents[4]


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


def _default_launcher_config(repo_root: Path) -> Path:
    """Return the default repo-owned CAO launcher config path."""

    return (repo_root.resolve() / "config" / "cao-server-launcher" / "local.toml").resolve()


def _default_run_root(repo_root: Path) -> Path:
    """Return one fresh timestamped run root under `tmp/demo/`."""

    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    return (
        repo_root.resolve()
        / "tmp"
        / "demo"
        / "cao-dual-shadow-watch"
        / f"{timestamp}-{os.getpid()}"
    ).resolve()


def _prepare_layout(paths: DemoPaths) -> None:
    """Create the required directory structure for one selected run root."""

    paths.run_root.mkdir(parents=True, exist_ok=False)
    paths.control_dir.mkdir(parents=True, exist_ok=True)
    paths.runtime_root.mkdir(parents=True, exist_ok=True)
    paths.projects_dir.mkdir(parents=True, exist_ok=True)
    paths.monitor_dir.mkdir(parents=True, exist_ok=True)
    paths.logs_dir.mkdir(parents=True, exist_ok=True)


def _prepare_launcher_config(
    *,
    source_config_path: Path,
    target_config_path: Path,
    runtime_root: Path,
    cao_base_url: str | None,
    cao_home_dir: Path | None,
) -> CaoServerLauncherConfig:
    """Write and load a demo-local launcher config for the selected run."""

    source_config = load_cao_server_launcher_config(source_config_path)
    resolved_base_url = (
        normalize_cao_base_url(cao_base_url) if cao_base_url else source_config.base_url
    )
    resolved_home_dir = (
        cao_home_dir.resolve()
        if cao_home_dir is not None
        else (
            source_config.home_dir.resolve() if source_config.home_dir is not None else Path.home()
        )
    )
    target_config_path.parent.mkdir(parents=True, exist_ok=True)
    target_config_path.write_text(
        "\n".join(
            [
                f'base_url = "{resolved_base_url}"',
                f'runtime_root = "{runtime_root.resolve()}"',
                f'home_dir = "{resolved_home_dir}"',
                f'proxy_policy = "{ProxyPolicy.CLEAR.value}"',
                f"startup_timeout_seconds = {source_config.startup_timeout_seconds}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return load_cao_server_launcher_config(target_config_path)


def _default_cao_profile_store(cao_home_dir: Path | None) -> Path:
    """Return the default CAO profile-store path for the selected launcher HOME."""

    base_home = (cao_home_dir or Path.home()).resolve()
    return (base_home / ".aws" / "cli-agent-orchestrator" / "agent-store").resolve()


def _start_agent_session(
    *,
    repo_root: Path,
    slot: str,
    blueprint_path: Path,
    agent_def_dir: Path,
    runtime_root: Path,
    workdir: Path,
    api_base_url: str,
    cao_profile_store: Path,
) -> dict[str, Any]:
    """Build the requested brain and start one CAO-backed runtime session."""

    del repo_root
    blueprint = load_blueprint(blueprint_path)
    recipe = load_brain_recipe_file(blueprint.brain_recipe_path)
    build_result = build_brain_home(
        BuildRequest(
            agent_def_dir=agent_def_dir,
            runtime_root=runtime_root,
            tool=recipe.tool,
            skills=list(recipe.skills),
            config_profile=recipe.config_profile,
            credential_profile=recipe.credential_profile,
            recipe_path=blueprint.brain_recipe_path,
            recipe_launch_overrides=recipe.launch_overrides,
            mailbox=recipe.mailbox,
            agent_name=recipe.default_agent_name,
            operator_prompt_mode=recipe.operator_prompt_mode,
        )
    )
    requested_agent_identity = recipe.default_agent_name or f"projection-demo-{slot}"
    controller = start_runtime_session(
        agent_def_dir=agent_def_dir,
        brain_manifest_path=build_result.manifest_path,
        role_name=blueprint.role,
        runtime_root=runtime_root,
        backend="cao_rest",
        working_directory=workdir,
        api_base_url=api_base_url,
        cao_profile_store_dir=cao_profile_store,
        agent_identity=requested_agent_identity,
        cao_parsing_mode=DEFAULT_SHADOW_PARSING_MODE,
    )
    if not isinstance(controller.backend_session, CaoRestSession):
        raise DualShadowWatchDemoError(
            f"Expected CAO runtime session for {slot}, got {type(controller.backend_session).__name__}"
        )
    backend_state = controller.backend_session.state
    session_state = AgentSessionState(
        slot=slot,
        tool=controller.launch_plan.tool,
        blueprint_path=str(blueprint_path.resolve()),
        brain_recipe_path=str(blueprint.brain_recipe_path.resolve()),
        role_name=blueprint.role,
        workdir=str(workdir.resolve()),
        brain_home_path=str(build_result.home_path),
        brain_manifest_path=str(build_result.manifest_path),
        launch_helper_path=str(build_result.launch_helper_path),
        session_manifest_path=str(controller.manifest_path),
        agent_identity=controller.agent_identity or requested_agent_identity,
        agent_id=controller.agent_id or "",
        tmux_session_name=controller.tmux_session_name or backend_state.session_name,
        cao_session_name=backend_state.session_name,
        terminal_id=backend_state.terminal_id,
        parsing_mode=controller.parsing_mode or DEFAULT_SHADOW_PARSING_MODE,
        startup_warnings=tuple(controller.startup_warnings),
    )
    return {"controller": controller, "build_result": build_result, "state": session_state}


def _provision_project_fixture(*, fixture_path: Path, project_workdir: Path) -> None:
    """Copy a tracked dummy project and initialize a fresh standalone git repo."""

    resolved_fixture = fixture_path.resolve()
    resolved_project_workdir = project_workdir.resolve()
    if (resolved_fixture / ".git").exists():
        raise DualShadowWatchDemoError(
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
        ["git", "commit", "-m", FIXED_DEMO_PROJECT_COMMIT_MESSAGE],
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
    raise DualShadowWatchDemoError(f"{' '.join(args)} failed in {cwd}: {detail}")


def _monitor_session_name() -> str:
    """Return one unique tmux session name for the live monitor."""

    return f"houmao-shadow-watch-monitor-{datetime.now(UTC).strftime('%H%M%S')}"


def _start_monitor_tmux_session(
    *,
    session_name: str,
    working_directory: Path,
    command: tuple[str, ...],
    log_path: Path,
) -> None:
    """Start the `rich` monitor in its own detached tmux session."""

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
    if result.returncode == 0:
        return
    detail = tmux_error_detail(result)
    raise DualShadowWatchDemoError(
        f"Failed to start monitor tmux session `{session_name}`: {detail or 'unknown tmux error'}"
    )


def _tmux_session_exists(session_name: str) -> bool:
    """Return whether the selected tmux session currently exists."""

    result = has_tmux_session(session_name=session_name)
    return result.returncode == 0


def _cleanup_partial_start(
    *,
    started_controllers: list[RuntimeSessionController],
    launcher_config: CaoServerLauncherConfig,
    started_new_cao_process: bool,
    monitor_session_name: str | None,
) -> None:
    """Best-effort cleanup after a partial startup failure."""

    for controller in reversed(started_controllers):
        try:
            controller.stop()
        except Exception:
            continue
    if monitor_session_name is not None and _tmux_session_exists(monitor_session_name):
        try:
            kill_tmux_session(session_name=monitor_session_name)
        except Exception:
            pass
    if started_new_cao_process:
        try:
            stop_cao_server(launcher_config)
        except Exception:
            pass


def _start_or_inspect_payload(
    state: DualShadowWatchDemoState,
    *,
    include_health: bool,
) -> dict[str, Any]:
    """Render one structured summary payload for start/inspect output."""

    agent_payloads: dict[str, Any] = {}
    for slot, session in state.agents.items():
        agent_payloads[slot] = {
            "tool": session.tool,
            "agent_identity": session.agent_identity,
            "agent_id": session.agent_id,
            "tmux_session_name": session.tmux_session_name,
            "cao_session_name": session.cao_session_name,
            "terminal_id": session.terminal_id,
            "parsing_mode": session.parsing_mode,
            "workdir": session.workdir,
            "tmux_alive": _tmux_session_exists(session.tmux_session_name),
            "attach_command": f"tmux attach -t {session.tmux_session_name}",
            "session_manifest_path": session.session_manifest_path,
            "startup_warnings": list(session.startup_warnings),
        }
    monitor_payload = {
        "tmux_session_name": state.monitor.tmux_session_name,
        "tmux_alive": _tmux_session_exists(state.monitor.tmux_session_name),
        "attach_command": f"tmux attach -t {state.monitor.tmux_session_name}",
        "samples_path": state.monitor.samples_path,
        "transitions_path": state.monitor.transitions_path,
        "dashboard_log_path": state.monitor.dashboard_log_path,
    }
    payload: dict[str, Any] = {
        "change": "cao-dual-shadow-watch",
        "active": state.active,
        "created_at_utc": state.created_at_utc,
        "stopped_at_utc": state.stopped_at_utc,
        "run_root": state.run_root,
        "project_fixture": state.project_fixture,
        "parsing_mode": state.parsing_mode,
        "poll_interval_seconds": state.poll_interval_seconds,
        "completion_stability_seconds": state.completion_stability_seconds,
        "unknown_to_stalled_timeout_seconds": state.unknown_to_stalled_timeout_seconds,
        "launcher": {
            "base_url": state.launcher.base_url,
            "runtime_root": state.launcher.runtime_root,
            "home_dir": state.launcher.home_dir,
            "profile_store": state.launcher.profile_store,
            "started_new_process": state.launcher.started_new_process,
            "reused_existing_process": state.launcher.reused_existing_process,
            "config_path": state.launcher.config_path,
            "artifact_dir": state.launcher.artifact_dir,
            "log_file": state.launcher.log_file,
            "ownership_file": state.launcher.ownership_file,
        },
        "agents": agent_payloads,
        "monitor": monitor_payload,
    }
    if include_health:
        payload["launcher"]["healthy"] = _launcher_healthy(Path(state.launcher.config_path))
    return payload


def _launcher_healthy(config_path: Path) -> bool:
    """Return whether the shared CAO server is currently healthy."""

    try:
        config = load_cao_server_launcher_config(config_path)
    except Exception:
        return False
    try:
        from houmao.cao.server_launcher import status_cao_server

        return bool(status_cao_server(config).healthy)
    except Exception:
        return False


def _load_selected_demo_state(
    *, repo_root: Path, run_root: Path | None
) -> DualShadowWatchDemoState:
    """Load demo state from one explicit or pointer-selected run root."""

    if run_root is not None:
        state_path = DemoPaths.from_run_root(repo_root=repo_root, run_root=run_root).state_path
        if not state_path.is_file():
            raise DualShadowWatchDemoError(f"Demo state not found: {state_path}")
        return load_demo_state(state_path)

    pointer_path = (
        repo_root.resolve() / "tmp" / "demo" / "cao-dual-shadow-watch" / "current_run_root.txt"
    ).resolve()
    if not pointer_path.is_file():
        raise DualShadowWatchDemoError(
            "No current demo run root recorded; start a run first or pass --run-root."
        )
    selected_run_root = Path(pointer_path.read_text(encoding="utf-8").strip()).resolve()
    state_path = DemoPaths.from_run_root(repo_root=repo_root, run_root=selected_run_root).state_path
    if not state_path.is_file():
        raise DualShadowWatchDemoError(f"Demo state not found: {state_path}")
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
    print(f"run_root: {payload['run_root']}")
    print(f"active: {payload['active']}")
    print(f"parsing_mode: {payload['parsing_mode']}")
    launcher = payload["launcher"]
    print(f"cao_base_url: {launcher['base_url']}")
    print(f"cao_healthy: {launcher.get('healthy', False)}")
    print(f"cao_profile_store: {launcher['profile_store']}")
    print(f"monitor_attach: {payload['monitor']['attach_command']}")
    for slot, agent in payload.get("agents", {}).items():
        print(
            f"{slot}_attach: {agent['attach_command']} "
            f"(tmux_alive={agent['tmux_alive']}, terminal_id={agent['terminal_id']})"
        )
    if "artifacts" in payload:
        artifacts = payload["artifacts"]
        print(f"samples_path: {artifacts['samples_path']}")
        print(f"transitions_path: {artifacts['transitions_path']}")
        print(f"dashboard_log_path: {artifacts['dashboard_log_path']}")


def _now_utc_iso() -> str:
    """Return one second-precision UTC timestamp string."""

    return datetime.now(UTC).isoformat(timespec="seconds")


def _require_positive(value: float, *, context: str) -> None:
    """Validate one positive numeric CLI input."""

    if value <= 0:
        raise DualShadowWatchDemoError(f"{context} must be > 0")
