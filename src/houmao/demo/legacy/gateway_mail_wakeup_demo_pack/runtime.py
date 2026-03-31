"""Runtime and `houmao-mgr` control helpers for the gateway wake-up demo pack."""

from __future__ import annotations

from contextlib import contextmanager
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence, cast

import click

from houmao.agents.brain_builder import BuildResult
from houmao.agents.realm_controller.agent_identity import AGENT_DEF_DIR_ENV_VAR
from houmao.agents.realm_controller.gateway_client import GatewayClient, GatewayEndpoint
from houmao.agents.realm_controller.loaders import load_brain_manifest
from houmao.agents.realm_controller.manifest import (
    load_session_manifest,
    parse_session_manifest_payload,
    runtime_owned_session_root_from_manifest_path,
)
from houmao.demo.legacy.mail_ping_pong_gateway_demo_pack.agents import (
    ensure_project_workdir_from_fixture,
    expose_runtime_skills_in_project,
)
from houmao.owned_paths import (
    HOUMAO_GLOBAL_MAILBOX_DIR_ENV_VAR,
    HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR,
    HOUMAO_GLOBAL_RUNTIME_DIR_ENV_VAR,
    HOUMAO_LOCAL_JOBS_DIR_ENV_VAR,
)
from houmao.srv_ctrl.commands.managed_agents import (
    managed_agent_detail_payload,
    resolve_managed_agent_target,
)

from .models import CommandResult, DemoPaths, DemoState, write_json


class DemoRuntimeError(RuntimeError):
    """Raised when the demo runtime flow cannot continue safely."""


@contextmanager
def _temporary_environment(env: Mapping[str, str]) -> Iterator[None]:
    """Temporarily apply one mapping of environment overrides."""

    previous: dict[str, str | None] = {}
    changed_keys: list[str] = []
    for key, value in env.items():
        current = os.environ.get(key)
        if current == value:
            continue
        previous[key] = current
        os.environ[key] = value
        changed_keys.append(key)
    try:
        yield
    finally:
        for key in changed_keys:
            prior = previous[key]
            if prior is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = prior


def manager_cli_command(args: list[str]) -> list[str]:
    """Build a `houmao-mgr` subprocess command."""

    return ["pixi", "run", "houmao-mgr", *args]


def build_demo_environment(
    *,
    paths: DemoPaths,
    agent_def_dir: Path,
    base_env: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Return the demo-owned environment for `houmao-mgr` invocations."""

    env = dict(os.environ if base_env is None else base_env)
    env[HOUMAO_GLOBAL_RUNTIME_DIR_ENV_VAR] = str(paths.runtime_root)
    env[HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR] = str(paths.registry_root)
    env[HOUMAO_GLOBAL_MAILBOX_DIR_ENV_VAR] = str(paths.mailbox_root)
    env[HOUMAO_LOCAL_JOBS_DIR_ENV_VAR] = str(paths.jobs_root)
    env[AGENT_DEF_DIR_ENV_VAR] = str(agent_def_dir)
    return env


def prepare_output_root(*, paths: DemoPaths, allow_reprovision: bool) -> None:
    """Create or reset the managed demo output layout."""

    cleanup_paths = (
        paths.control_dir,
        paths.logs_dir,
        paths.runtime_root,
        paths.registry_root,
        paths.mailbox_root,
        paths.jobs_root,
        paths.deliveries_dir,
        paths.project_dir,
        paths.outputs_dir,
        paths.evidence_dir,
    )
    create_paths = (
        paths.control_dir,
        paths.logs_dir,
        paths.runtime_root,
        paths.registry_root,
        paths.mailbox_root,
        paths.jobs_root,
        paths.deliveries_dir,
        paths.outputs_dir,
        paths.evidence_dir,
    )
    if allow_reprovision:
        for target in cleanup_paths:
            if target.exists():
                shutil.rmtree(target)
    for target in create_paths:
        target.mkdir(parents=True, exist_ok=True)


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


def run_launch_command(
    *,
    cwd: Path,
    stdout_path: Path,
    stderr_path: Path,
    selector: str,
    provider: str,
    agent_name: str,
    session_name: str,
    env: Mapping[str, str],
    timeout_seconds: float,
) -> dict[str, Any]:
    """Launch one serverless local interactive agent through `houmao-mgr`."""

    result = run_command(
        manager_cli_command(
            [
                "agents",
                "launch",
                "--agents",
                selector,
                "--provider",
                provider,
                "--agent-name",
                agent_name,
                "--session-name",
                session_name,
                "--yolo",
            ]
        ),
        cwd=cwd,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        env=env,
        timeout_seconds=timeout_seconds,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "launch failed"
        raise DemoRuntimeError(detail)
    payload = parse_launch_output(result.stdout)
    payload.update(
        {
            "selector": selector,
            "provider": provider,
            "agent_name_requested": agent_name,
            "session_name_requested": session_name,
            "stdout_path": str(stdout_path),
            "stderr_path": str(stderr_path),
        }
    )
    return payload


def parse_launch_output(stdout: str) -> dict[str, Any]:
    """Parse the plain-text `houmao-mgr agents launch` result payload."""

    payload: dict[str, Any] = {"raw_stdout": stdout}
    for line in stdout.splitlines():
        stripped = line.strip()
        if "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        payload[key] = value
    if "manifest_path" not in payload:
        raise DemoRuntimeError(
            "unable to parse `houmao-mgr agents launch` output for `manifest_path`"
        )
    return payload


def initialize_mailbox(
    *,
    repo_root: Path,
    paths: DemoPaths,
    env: Mapping[str, str],
    timeout_seconds: float,
) -> dict[str, Any]:
    """Initialize the pack-local filesystem mailbox root."""

    payload = run_json_command(
        manager_cli_command(["mailbox", "init", "--mailbox-root", str(paths.mailbox_root)]),
        cwd=repo_root,
        stdout_path=paths.logs_dir / "mailbox-init.stdout",
        stderr_path=paths.logs_dir / "mailbox-init.stderr",
        env=env,
        timeout_seconds=timeout_seconds,
    )
    write_json(paths.mailbox_init_path, payload)
    return payload


def query_agent_show(
    *,
    repo_root: Path,
    paths: DemoPaths,
    agent_name: str,
    env: Mapping[str, str],
    timeout_seconds: float,
) -> dict[str, Any]:
    """Query one managed-agent detail view and persist the result."""

    del repo_root, timeout_seconds
    stdout_path = paths.logs_dir / "agent-show.stdout"
    stderr_path = paths.logs_dir / "agent-show.stderr"
    try:
        with _temporary_environment(env):
            target = resolve_managed_agent_target(agent_id=None, agent_name=agent_name, port=None)
            payload = managed_agent_detail_payload(target).model_dump(mode="json")
    except (click.ClickException, RuntimeError, ValueError) as exc:
        stdout_path.write_text("", encoding="utf-8")
        stderr_path.write_text(f"{exc}\n", encoding="utf-8")
        raise DemoRuntimeError(str(exc)) from exc

    stdout_path.write_text(f"{json.dumps(payload, indent=2)}\n", encoding="utf-8")
    stderr_path.write_text("", encoding="utf-8")
    write_json(paths.agent_show_path, payload)
    return payload


def query_agent_state(
    *,
    repo_root: Path,
    paths: DemoPaths,
    agent_name: str,
    env: Mapping[str, str],
    timeout_seconds: float,
) -> dict[str, Any]:
    """Query one managed-agent summary view and persist the result."""

    payload = run_json_command(
        manager_cli_command(["agents", "state", "--agent-name", agent_name]),
        cwd=repo_root,
        stdout_path=paths.logs_dir / "agent-state.stdout",
        stderr_path=paths.logs_dir / "agent-state.stderr",
        env=env,
        timeout_seconds=timeout_seconds,
    )
    write_json(paths.agent_state_path, payload)
    return payload


def register_mailbox(
    *,
    repo_root: Path,
    paths: DemoPaths,
    agent_name: str,
    mailbox_principal_id: str,
    mailbox_address: str,
    env: Mapping[str, str],
    timeout_seconds: float,
) -> dict[str, Any]:
    """Register one filesystem mailbox binding for the live managed agent."""

    payload = run_json_command(
        manager_cli_command(
            [
                "agents",
                "mailbox",
                "register",
                "--agent-name",
                agent_name,
                "--mailbox-root",
                str(paths.mailbox_root),
                "--principal-id",
                mailbox_principal_id,
                "--address",
                mailbox_address,
            ]
        ),
        cwd=repo_root,
        stdout_path=paths.logs_dir / "mailbox-register.stdout",
        stderr_path=paths.logs_dir / "mailbox-register.stderr",
        env=env,
        timeout_seconds=timeout_seconds,
    )
    write_json(paths.mailbox_register_path, payload)
    return payload


def attach_gateway(
    *,
    repo_root: Path,
    paths: DemoPaths,
    agent_name: str,
    env: Mapping[str, str],
    timeout_seconds: float,
) -> dict[str, Any]:
    """Attach the live gateway for the selected managed agent."""

    payload = run_json_command(
        manager_cli_command(["agents", "gateway", "attach", "--agent-name", agent_name]),
        cwd=repo_root,
        stdout_path=paths.logs_dir / "gateway-attach.stdout",
        stderr_path=paths.logs_dir / "gateway-attach.stderr",
        env=env,
        timeout_seconds=timeout_seconds,
    )
    write_json(paths.gateway_attach_path, payload)
    return payload


def gateway_status(
    *,
    repo_root: Path,
    paths: DemoPaths,
    agent_name: str,
    env: Mapping[str, str],
    timeout_seconds: float,
) -> dict[str, Any]:
    """Query the live gateway status for one managed agent."""

    return run_json_command(
        manager_cli_command(["agents", "gateway", "status", "--agent-name", agent_name]),
        cwd=repo_root,
        stdout_path=paths.logs_dir / "gateway-status.stdout",
        stderr_path=paths.logs_dir / "gateway-status.stderr",
        env=env,
        timeout_seconds=timeout_seconds,
    )


def enable_notifier(
    *,
    repo_root: Path,
    paths: DemoPaths,
    agent_name: str,
    interval_seconds: int,
    env: Mapping[str, str],
    timeout_seconds: float,
) -> dict[str, Any]:
    """Enable gateway unread-mail polling for one managed agent."""

    payload = run_json_command(
        manager_cli_command(
            [
                "agents",
                "gateway",
                "mail-notifier",
                "enable",
                "--agent-name",
                agent_name,
                "--interval-seconds",
                str(interval_seconds),
            ]
        ),
        cwd=repo_root,
        stdout_path=paths.logs_dir / "notifier-enable.stdout",
        stderr_path=paths.logs_dir / "notifier-enable.stderr",
        env=env,
        timeout_seconds=timeout_seconds,
    )
    write_json(paths.notifier_enable_path, payload)
    return payload


def notifier_status(
    *,
    repo_root: Path,
    paths: DemoPaths,
    agent_name: str,
    env: Mapping[str, str],
    timeout_seconds: float,
) -> dict[str, Any]:
    """Query gateway mail-notifier status for one managed agent."""

    return run_json_command(
        manager_cli_command(
            ["agents", "gateway", "mail-notifier", "status", "--agent-name", agent_name]
        ),
        cwd=repo_root,
        stdout_path=paths.logs_dir / "notifier-status.stdout",
        stderr_path=paths.logs_dir / "notifier-status.stderr",
        env=env,
        timeout_seconds=timeout_seconds,
    )


def disable_notifier(
    *,
    repo_root: Path,
    paths: DemoPaths,
    agent_name: str,
    env: Mapping[str, str],
    timeout_seconds: float,
) -> dict[str, Any]:
    """Disable gateway mail-notifier behavior for one managed agent."""

    return run_json_command(
        manager_cli_command(
            ["agents", "gateway", "mail-notifier", "disable", "--agent-name", agent_name]
        ),
        cwd=repo_root,
        stdout_path=paths.logs_dir / "notifier-disable.stdout",
        stderr_path=paths.logs_dir / "notifier-disable.stderr",
        env=env,
        timeout_seconds=timeout_seconds,
    )


def stop_agent(
    *,
    repo_root: Path,
    paths: DemoPaths,
    agent_name: str,
    env: Mapping[str, str],
    timeout_seconds: float,
) -> dict[str, Any]:
    """Stop one managed agent."""

    return run_json_command(
        manager_cli_command(["agents", "stop", "--agent-name", agent_name]),
        cwd=repo_root,
        stdout_path=paths.logs_dir / "agent-stop.stdout",
        stderr_path=paths.logs_dir / "agent-stop.stderr",
        env=env,
        timeout_seconds=timeout_seconds,
    )


def load_session_details(*, session_manifest_path: Path) -> dict[str, Any]:
    """Load session and brain-manifest details needed by the demo."""

    handle = load_session_manifest(session_manifest_path)
    payload = parse_session_manifest_payload(handle.payload, source=str(handle.path))
    session_root = runtime_owned_session_root_from_manifest_path(session_manifest_path)
    if session_root is None:
        raise DemoRuntimeError(f"unable to resolve session root from `{session_manifest_path}`")
    brain_manifest_path = Path(payload.brain_manifest_path).resolve()
    brain_manifest = load_brain_manifest(brain_manifest_path)
    runtime_payload = _require_json_object(brain_manifest.get("runtime"))
    home_path = Path(str(runtime_payload["home_path"])).resolve()
    launch_helper_path = Path(str(runtime_payload["launch_helper"])).resolve()
    terminal_id = None if payload.local_interactive is None else None
    return {
        "tracked_agent_id": None,
        "agent_name": payload.agent_name,
        "agent_id": payload.agent_id,
        "tmux_session_name": payload.tmux_session_name,
        "terminal_id": terminal_id,
        "session_root": session_root,
        "brain_manifest_path": brain_manifest_path,
        "brain_home_path": home_path,
        "launch_helper_path": launch_helper_path,
    }


def provision_project_workdir(
    *,
    project_fixture: Path,
    project_dir: Path,
    allow_reprovision: bool,
) -> Path:
    """Provision the copied dummy project under the selected output root."""

    return ensure_project_workdir_from_fixture(
        project_fixture=project_fixture,
        project_workdir=project_dir,
        allow_reprovision=allow_reprovision,
    )


def expose_project_mailbox_skills(
    *,
    project_workdir: Path,
    brain_manifest_path: Path,
    brain_home_path: Path,
    launch_helper_path: Path,
) -> None:
    """Mirror the runtime mailbox skill surface into the copied project."""

    build_result = BuildResult(
        home_id=brain_home_path.name,
        home_path=brain_home_path,
        manifest_path=brain_manifest_path,
        launch_helper_path=launch_helper_path,
        launch_preview="",
        manifest={},
    )
    expose_runtime_skills_in_project(project_workdir=project_workdir, build_result=build_result)


def build_gateway_client(*, state: DemoState) -> GatewayClient:
    """Return an HTTP client bound to the persisted live gateway endpoint."""

    endpoint = GatewayEndpoint(host=cast(Any, state.gateway_host), port=state.gateway_port)
    return GatewayClient(endpoint=endpoint)


def _require_json_object(payload: object) -> dict[str, Any]:
    """Require one decoded JSON object payload."""

    if not isinstance(payload, dict):
        raise DemoRuntimeError("command did not return a JSON object")
    return dict(payload)
