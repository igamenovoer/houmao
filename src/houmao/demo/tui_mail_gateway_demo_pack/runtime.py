"""Runtime and gateway control helpers for the TUI mail gateway demo pack."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence, cast

from houmao.agents.brain_builder import BuildResult
from houmao.agents.realm_controller.gateway_client import GatewayClient, GatewayEndpoint
from houmao.agents.realm_controller.gateway_models import (
    GatewayHost,
    GatewayMailNotifierPutV1,
)
from houmao.agents.realm_controller.manifest import (
    load_session_manifest,
    parse_session_manifest_payload,
    runtime_owned_session_root_from_manifest_path,
)
from houmao.demo.mail_ping_pong_gateway_demo_pack.agents import (
    ensure_project_workdir_from_fixture,
    expose_runtime_skills_in_project,
)
from houmao.owned_paths import (
    AGENTSYS_GLOBAL_MAILBOX_DIR_ENV_VAR,
    AGENTSYS_GLOBAL_REGISTRY_DIR_ENV_VAR,
    AGENTSYS_GLOBAL_RUNTIME_DIR_ENV_VAR,
    AGENTSYS_LOCAL_JOBS_DIR_ENV_VAR,
)

from .models import CommandResult, DemoPaths, DemoState, ToolParameters, write_json


class DemoRuntimeError(RuntimeError):
    """Raised when the demo runtime flow cannot continue safely."""


def runtime_cli_command(args: list[str]) -> list[str]:
    """Build a `realm_controller` CLI subprocess command."""

    return ["pixi", "run", "python", "-m", "houmao.agents.realm_controller", *args]


def cao_launcher_cli_command(args: list[str]) -> list[str]:
    """Build a `cao_server_launcher` CLI subprocess command."""

    return ["pixi", "run", "python", "-m", "houmao.cao.tools.cao_server_launcher", *args]


def build_demo_environment(
    *,
    paths: DemoPaths,
    base_env: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Return the demo-owned environment for runtime CLI invocations."""

    env = dict(os.environ if base_env is None else base_env)
    env[AGENTSYS_GLOBAL_RUNTIME_DIR_ENV_VAR] = str(paths.runtime_root)
    env[AGENTSYS_GLOBAL_REGISTRY_DIR_ENV_VAR] = str(paths.registry_root)
    env[AGENTSYS_GLOBAL_MAILBOX_DIR_ENV_VAR] = str(paths.mailbox_root)
    env[AGENTSYS_LOCAL_JOBS_DIR_ENV_VAR] = str(paths.jobs_root)
    return env


def prepare_output_root(*, paths: DemoPaths, allow_reprovision: bool) -> None:
    """Create or reset the managed demo output layout."""

    managed_paths = (
        paths.control_dir,
        paths.logs_dir,
        paths.runtime_root,
        paths.registry_root,
        paths.mailbox_root,
        paths.jobs_root,
        paths.deliveries_dir,
        paths.project_dir,
        paths.evidence_dir,
        paths.cao_dir,
    )
    if allow_reprovision:
        for target in managed_paths:
            if target.exists():
                shutil.rmtree(target)
    for target in managed_paths:
        target.mkdir(parents=True, exist_ok=True)


def write_launcher_config(*, paths: DemoPaths, cao_base_url: str) -> None:
    """Write the pack-local CAO launcher config."""

    content = "\n".join(
        [
            f'base_url = "{cao_base_url}"',
            f'runtime_root = "{paths.cao_runtime_root}"',
            f'home_dir = "{paths.cao_home_dir}"',
            'proxy_policy = "clear"',
            "startup_timeout_seconds = 15",
            "",
        ]
    )
    paths.launcher_config_path.parent.mkdir(parents=True, exist_ok=True)
    paths.launcher_config_path.write_text(content, encoding="utf-8")


def cao_profile_store(*, paths: DemoPaths) -> Path:
    """Return the pack-local CAO profile-store directory."""

    return paths.cao_home_dir / ".aws" / "cli-agent-orchestrator" / "agent-store"


def run_command(
    command: Sequence[str],
    *,
    cwd: Path,
    stdout_path: Path,
    stderr_path: Path,
    env: Mapping[str, str] | None = None,
    timeout_seconds: float,
) -> CommandResult:
    """Run one subprocess command and persist stdout/stderr logs."""

    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stderr_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        completed = subprocess.run(
            list(command),
            check=False,
            capture_output=True,
            cwd=str(cwd),
            env=None if env is None else dict(env),
            text=True,
            timeout=timeout_seconds,
        )
    except FileNotFoundError as exc:
        raise DemoRuntimeError(f"command not found: `{command[0]}`") from exc
    except subprocess.TimeoutExpired as exc:
        raise DemoRuntimeError(
            f"command timed out after {timeout_seconds:.1f}s: {' '.join(command)}"
        ) from exc

    stdout_path.write_text(completed.stdout, encoding="utf-8")
    stderr_path.write_text(completed.stderr, encoding="utf-8")
    return CommandResult(
        args=tuple(str(part) for part in command),
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
    )


def run_json_command(
    command: Sequence[str],
    *,
    cwd: Path,
    stdout_path: Path,
    stderr_path: Path,
    env: Mapping[str, str] | None = None,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Run one command and parse its stdout as JSON."""

    result = run_command(
        command,
        cwd=cwd,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        env=env,
        timeout_seconds=timeout_seconds,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "command failed"
        raise DemoRuntimeError(detail)
    try:
        return _require_json_object(json.loads(result.stdout))
    except json.JSONDecodeError as exc:
        raise DemoRuntimeError(f"command did not return JSON: {' '.join(command)}") from exc


def start_cao_service(
    *,
    repo_root: Path,
    paths: DemoPaths,
    cao_base_url: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Start or reuse the demo-owned CAO service."""

    write_launcher_config(paths=paths, cao_base_url=cao_base_url)
    payload = run_json_command(
        cao_launcher_cli_command(["start", "--config", str(paths.launcher_config_path)]),
        cwd=repo_root,
        stdout_path=paths.logs_dir / "cao-start.stdout",
        stderr_path=paths.logs_dir / "cao-start.stderr",
        timeout_seconds=timeout_seconds,
    )
    write_json(paths.control_dir / "cao_start.json", payload)
    return payload


def stop_cao_service(
    *,
    repo_root: Path,
    paths: DemoPaths,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Best-effort stop for the demo-owned CAO service."""

    if not paths.launcher_config_path.is_file():
        return {"operation": "stop", "status": "skipped", "detail": "launcher config missing"}
    result = run_command(
        cao_launcher_cli_command(["stop", "--config", str(paths.launcher_config_path)]),
        cwd=repo_root,
        stdout_path=paths.logs_dir / "cao-stop.stdout",
        stderr_path=paths.logs_dir / "cao-stop.stderr",
        timeout_seconds=timeout_seconds,
    )
    payload_text = result.stdout.strip() or result.stderr.strip() or "{}"
    try:
        payload = _require_json_object(json.loads(payload_text))
    except json.JSONDecodeError:
        payload = {
            "operation": "stop",
            "status": "error" if result.returncode != 0 else "ok",
            "detail": payload_text,
        }
    write_json(paths.control_dir / "cao_stop.json", payload)
    return payload


def build_brain(
    *,
    repo_root: Path,
    paths: DemoPaths,
    agent_def_dir: Path,
    blueprint_path: Path,
    env: Mapping[str, str],
    timeout_seconds: float,
) -> BuildResult:
    """Build the selected mailbox-demo brain home."""

    payload = run_json_command(
        runtime_cli_command(
            [
                "build-brain",
                "--agent-def-dir",
                str(agent_def_dir),
                "--runtime-root",
                str(paths.runtime_root),
                "--preset",
                str(blueprint_path),
            ]
        ),
        cwd=repo_root,
        stdout_path=paths.logs_dir / "build-brain.stdout",
        stderr_path=paths.logs_dir / "build-brain.stderr",
        env=env,
        timeout_seconds=timeout_seconds,
    )
    return BuildResult(
        home_id=str(payload["home_id"]),
        home_path=Path(str(payload["home_path"])).resolve(),
        manifest_path=Path(str(payload["manifest_path"])).resolve(),
        launch_helper_path=Path(str(payload["launch_helper_path"])).resolve(),
        launch_preview="",
        manifest={},
    )


def provision_project_workdir(
    *,
    project_fixture: Path,
    project_dir: Path,
    allow_reprovision: bool,
    build_result: BuildResult,
) -> Path:
    """Provision the copied dummy project and expose runtime mailbox skills inside it."""

    project_workdir = ensure_project_workdir_from_fixture(
        project_fixture=project_fixture,
        project_workdir=project_dir,
        allow_reprovision=allow_reprovision,
    )
    expose_runtime_skills_in_project(project_workdir=project_workdir, build_result=build_result)
    return project_workdir


def start_mailbox_session(
    *,
    repo_root: Path,
    paths: DemoPaths,
    agent_def_dir: Path,
    build_result: BuildResult,
    project_workdir: Path,
    tool_parameters: ToolParameters,
    role_name: str,
    cao_base_url: str,
    env: Mapping[str, str],
    timeout_seconds: float,
) -> dict[str, Any]:
    """Start the selected mailbox-enabled CAO TUI session."""

    payload = run_json_command(
        runtime_cli_command(
            [
                "start-session",
                "--agent-def-dir",
                str(agent_def_dir),
                "--runtime-root",
                str(paths.runtime_root),
                "--brain-manifest",
                str(build_result.manifest_path),
                "--role",
                role_name,
                "--backend",
                "local_interactive",
                "--cao-base-url",
                cao_base_url,
                "--cao-profile-store",
                str(cao_profile_store(paths=paths)),
                "--workdir",
                str(project_workdir),
                "--agent-identity",
                tool_parameters.agent_identity,
                "--mailbox-transport",
                "filesystem",
                "--mailbox-root",
                str(paths.mailbox_root),
                "--mailbox-principal-id",
                tool_parameters.mailbox_principal_id,
                "--mailbox-address",
                tool_parameters.mailbox_address,
            ]
        ),
        cwd=repo_root,
        stdout_path=paths.logs_dir / "start-session.stdout",
        stderr_path=paths.logs_dir / "start-session.stderr",
        env=env,
        timeout_seconds=timeout_seconds,
    )
    write_json(paths.control_dir / "session_start.json", payload)
    return payload


def attach_gateway(
    *,
    repo_root: Path,
    paths: DemoPaths,
    agent_def_dir: Path,
    session_manifest_path: Path,
    gateway_host: str,
    env: Mapping[str, str],
    timeout_seconds: float,
) -> dict[str, Any]:
    """Attach the live gateway for the selected runtime-owned session."""

    payload = run_json_command(
        runtime_cli_command(
            [
                "attach-gateway",
                "--agent-def-dir",
                str(agent_def_dir),
                "--agent-identity",
                str(session_manifest_path),
                "--gateway-host",
                gateway_host,
            ]
        ),
        cwd=repo_root,
        stdout_path=paths.logs_dir / "attach-gateway.stdout",
        stderr_path=paths.logs_dir / "attach-gateway.stderr",
        env=env,
        timeout_seconds=timeout_seconds,
    )
    write_json(paths.control_dir / "gateway_attach.json", payload)
    return payload


def load_session_details(*, session_manifest_path: Path) -> dict[str, Any]:
    """Load the persisted session manifest and derive stable session details."""

    handle = load_session_manifest(session_manifest_path)
    payload = parse_session_manifest_payload(handle.payload, source=str(handle.path))
    session_root = runtime_owned_session_root_from_manifest_path(session_manifest_path)
    if session_root is None:
        raise DemoRuntimeError(f"unable to resolve session root from `{session_manifest_path}`")
    terminal_id = None if payload.cao is None else payload.cao.terminal_id
    return {
        "agent_identity": payload.agent_name,
        "agent_name": payload.agent_name,
        "agent_id": payload.agent_id,
        "tmux_session_name": payload.tmux_session_name,
        "terminal_id": terminal_id,
        "session_root": session_root,
    }


def build_gateway_client(*, state: DemoState) -> GatewayClient:
    """Return an HTTP client bound to the persisted live gateway endpoint."""

    endpoint = GatewayEndpoint(
        host=cast(GatewayHost, state.gateway_host),
        port=state.gateway_port,
    )
    return GatewayClient(endpoint=endpoint)


def enable_notifier(*, state: DemoState) -> dict[str, Any]:
    """Enable gateway unread-mail polling for the persisted session."""

    client = build_gateway_client(state=state)
    status = client.put_mail_notifier(
        GatewayMailNotifierPutV1(interval_seconds=state.notifier_interval_seconds)
    )
    return status.model_dump(mode="json")


def disable_notifier(*, state: DemoState) -> dict[str, Any]:
    """Disable gateway unread-mail polling for the persisted session."""

    client = build_gateway_client(state=state)
    status = client.delete_mail_notifier()
    return status.model_dump(mode="json")


def stop_session(
    *,
    repo_root: Path,
    paths: DemoPaths,
    state: DemoState,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Best-effort stop for the persisted runtime-owned TUI session."""

    result = run_command(
        runtime_cli_command(
            [
                "stop-session",
                "--agent-def-dir",
                str(state.agent_def_dir),
                "--agent-identity",
                str(state.session_manifest_path),
            ]
        ),
        cwd=repo_root,
        stdout_path=paths.logs_dir / "stop-session.stdout",
        stderr_path=paths.logs_dir / "stop-session.stderr",
        env=build_demo_environment(paths=paths),
        timeout_seconds=timeout_seconds,
    )
    payload_text = result.stdout.strip() or result.stderr.strip() or "{}"
    try:
        payload = _require_json_object(json.loads(payload_text))
    except json.JSONDecodeError:
        payload = {
            "status": "error" if result.returncode != 0 else "ok",
            "detail": payload_text,
        }
    write_json(paths.control_dir / "session_stop.json", payload)
    return payload


def _require_json_object(payload: object) -> dict[str, Any]:
    """Require one decoded JSON object payload."""

    if not isinstance(payload, dict):
        raise DemoRuntimeError("command did not return a JSON object")
    return dict(payload)
