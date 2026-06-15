"""Runtime helpers for the manual Kimi writer-team demo pack."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from typing import Any, Mapping, Sequence

from houmao.agents.realm_controller.agent_identity import AGENT_DEF_DIR_ENV_VAR
from houmao.agents.realm_controller.backends.tmux_runtime import (
    TmuxCommandError,
    attach_tmux_session,
)
from houmao.agents.realm_controller.loaders import parse_env_file
from houmao.owned_paths import (
    HOUMAO_GLOBAL_MAILBOX_DIR_ENV_VAR,
    HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR,
    HOUMAO_GLOBAL_RUNTIME_DIR_ENV_VAR,
    HOUMAO_JOB_DIR_ENV_VAR,
    HOUMAO_LOCAL_JOBS_DIR_ENV_VAR,
)
from houmao.project.overlay import PROJECT_OVERLAY_DIR_ENV_VAR

from .models import CommandResult, DemoPaths, TeamMemberParameters
from .store import write_json


class DemoRuntimeError(RuntimeError):
    """Raised when the demo runtime flow cannot continue safely."""


def manager_cli_command(args: Sequence[str]) -> list[str]:
    """Build a `houmao-mgr` subprocess command."""

    return ["pixi", "run", "houmao-mgr", "--print-json", *args]


def uses_headless_backend(member: TeamMemberParameters) -> bool:
    """Return whether one writer-team member should launch through headless Kimi."""

    return member.role == "review"


def prompt_mode_for_member(member: TeamMemberParameters) -> str:
    """Return the launch prompt mode for one writer-team member."""

    del member
    return "unattended"


def build_demo_environment(
    *,
    paths: DemoPaths,
    base_env: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Return the demo-owned environment for command invocations."""

    env = dict(os.environ if base_env is None else base_env)
    for env_var_name in (
        AGENT_DEF_DIR_ENV_VAR,
        HOUMAO_GLOBAL_RUNTIME_DIR_ENV_VAR,
        HOUMAO_GLOBAL_MAILBOX_DIR_ENV_VAR,
        HOUMAO_LOCAL_JOBS_DIR_ENV_VAR,
        HOUMAO_JOB_DIR_ENV_VAR,
    ):
        env.pop(env_var_name, None)
    env[HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR] = str(paths.registry_root)
    env[PROJECT_OVERLAY_DIR_ENV_VAR] = str(paths.overlay_dir)
    return env


def prepare_output_root(*, paths: DemoPaths, reset: bool) -> None:
    """Create or reset the managed demo output layout."""

    cleanup_paths = (
        paths.control_dir,
        paths.logs_dir,
        paths.deliveries_dir,
        paths.evidence_dir,
        paths.project_dir,
        paths.overlay_dir,
        paths.registry_root,
    )
    if reset:
        for target in cleanup_paths:
            if target.exists():
                shutil.rmtree(target)
    for target in (
        paths.output_root,
        paths.control_dir,
        paths.logs_dir,
        paths.deliveries_dir,
        paths.evidence_dir,
        paths.overlay_dir,
        paths.runtime_root,
        paths.registry_root,
        paths.jobs_root,
    ):
        target.mkdir(parents=True, exist_ok=True)


def provision_writer_team_project(*, source_dir: Path, project_dir: Path, reset: bool) -> Path:
    """Copy the writer-team source material into the demo project workdir."""

    if not source_dir.is_dir():
        raise DemoRuntimeError(f"writer-team source not found: {source_dir}")
    if project_dir.exists():
        if not reset:
            return project_dir.resolve()
        shutil.rmtree(project_dir)
    shutil.copytree(source_dir, project_dir, symlinks=True)
    return project_dir.resolve()


def run_command(
    command: Sequence[str],
    *,
    cwd: Path,
    stdout_path: Path,
    stderr_path: Path,
    env: Mapping[str, str] | None = None,
    timeout_seconds: float,
    stdin_text: str | None = None,
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
            input=stdin_text,
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
    stdin_text: str | None = None,
) -> dict[str, Any]:
    """Run one command and parse its stdout as a JSON object."""

    result = run_command(
        command,
        cwd=cwd,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        env=env,
        timeout_seconds=timeout_seconds,
        stdin_text=stdin_text,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "command failed"
        raise DemoRuntimeError(detail)
    return parse_json_object_output(result.stdout, command=command)


def parse_json_object_output(stdout: str, *, command: Sequence[str]) -> dict[str, Any]:
    """Parse the first JSON object from command stdout."""

    decoder = json.JSONDecoder()
    index = 0
    while index < len(stdout):
        while index < len(stdout) and stdout[index].isspace():
            index += 1
        if index >= len(stdout):
            break
        try:
            parsed, next_index = decoder.raw_decode(stdout, index)
        except json.JSONDecodeError as exc:
            raise DemoRuntimeError(f"command did not return JSON: {' '.join(command)}") from exc
        if isinstance(parsed, dict):
            return parsed
        index = next_index
    raise DemoRuntimeError(f"command did not return a JSON object: {' '.join(command)}")


def initialize_project_overlay(
    *,
    paths: DemoPaths,
    env: Mapping[str, str],
    timeout_seconds: float,
) -> dict[str, Any]:
    """Initialize the redirected Houmao project overlay."""

    stdout_path, stderr_path = paths.log_paths("project-init")
    payload = run_json_command(
        manager_cli_command(["project", "init"]),
        cwd=paths.project_dir,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        env=env,
        timeout_seconds=timeout_seconds,
    )
    write_json(paths.control_json_path("project-init"), payload)
    return payload


def initialize_project_mailbox(
    *,
    paths: DemoPaths,
    env: Mapping[str, str],
    timeout_seconds: float,
) -> dict[str, Any]:
    """Initialize the demo-local project mailbox root."""

    stdout_path, stderr_path = paths.log_paths("project-mailbox-init")
    payload = run_json_command(
        manager_cli_command(["project", "mailbox", "init"]),
        cwd=paths.project_dir,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        env=env,
        timeout_seconds=timeout_seconds,
    )
    write_json(paths.control_json_path("project-mailbox-init"), payload)
    return payload


def register_project_mailbox_account(
    *,
    paths: DemoPaths,
    env: Mapping[str, str],
    address: str,
    principal_id: str,
    stem: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Register or replace one project mailbox account."""

    stdout_path, stderr_path = paths.log_paths(stem)
    payload = run_json_command(
        manager_cli_command(
            [
                "project",
                "mailbox",
                "register",
                "--address",
                address,
                "--principal-id",
                principal_id,
                "--mode",
                "force",
                "--yes",
            ]
        ),
        cwd=paths.project_dir,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        env=env,
        timeout_seconds=timeout_seconds,
    )
    write_json(paths.control_json_path(stem), payload)
    return payload


def credential_exists(
    *,
    paths: DemoPaths,
    env: Mapping[str, str],
    credential_name: str,
    timeout_seconds: float,
) -> bool:
    """Return whether a Kimi credential exists in the active project overlay."""

    stdout_path, stderr_path = paths.log_paths("credential-kimi-get")
    result = run_command(
        manager_cli_command(["project", "credentials", "kimi", "get", "--name", credential_name]),
        cwd=paths.project_dir,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        env=env,
        timeout_seconds=timeout_seconds,
    )
    return result.returncode == 0


def upsert_kimi_credential(
    *,
    paths: DemoPaths,
    env: Mapping[str, str],
    credential_name: str,
    credential_args: Sequence[str],
    timeout_seconds: float,
) -> dict[str, Any]:
    """Create or update one project-scoped Kimi credential."""

    operation = (
        "set"
        if credential_exists(
            paths=paths,
            env=env,
            credential_name=credential_name,
            timeout_seconds=timeout_seconds,
        )
        else "add"
    )
    stdout_path, stderr_path = paths.log_paths("credential-kimi-upsert")
    payload = run_json_command(
        manager_cli_command(
            [
                "project",
                "credentials",
                "kimi",
                operation,
                "--name",
                credential_name,
                *credential_args,
            ]
        ),
        cwd=paths.project_dir,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        env=env,
        timeout_seconds=timeout_seconds,
    )
    wrapped = {"operation": operation, **payload}
    write_json(paths.control_json_path("credential-kimi-upsert"), wrapped)
    return wrapped


def build_kimi_credential_args_from_bundle(*, bundle_dir: Path) -> tuple[list[str], str]:
    """Build Kimi credential CLI args from a fixture-style auth bundle."""

    if not bundle_dir.is_dir():
        raise DemoRuntimeError(f"Kimi auth bundle not found: {bundle_dir}")
    env_values = parse_env_file(bundle_dir / "env" / "vars.env")
    files_root = bundle_dir / "files"
    args = build_kimi_credential_args(
        api_key=env_values.get("KIMI_MODEL_API_KEY"),
        model_name=env_values.get("KIMI_MODEL_NAME"),
        base_url=env_values.get("KIMI_MODEL_BASE_URL"),
        provider_type=env_values.get("KIMI_MODEL_PROVIDER_TYPE"),
        code_base_url=env_values.get("KIMI_CODE_BASE_URL"),
        code_oauth_host=env_values.get("KIMI_CODE_OAUTH_HOST"),
        oauth_host=env_values.get("KIMI_OAUTH_HOST"),
        disable_telemetry=_is_truthy(env_values.get("KIMI_DISABLE_TELEMETRY")),
        code_home=None,
        config_toml=files_root / "config.toml",
        credential_json=files_root / "credentials" / "kimi-code.json",
        require_existing_files=False,
    )
    return args, f"auth-bundle:{bundle_dir}"


def build_kimi_credential_args(
    *,
    api_key: str | None,
    model_name: str | None,
    base_url: str | None,
    provider_type: str | None,
    code_base_url: str | None,
    code_oauth_host: str | None,
    oauth_host: str | None,
    disable_telemetry: bool,
    code_home: Path | None,
    config_toml: Path | None,
    credential_json: Path | None,
    require_existing_files: bool = True,
) -> list[str]:
    """Build validated Kimi credential CLI arguments."""

    if code_home is not None and (config_toml is not None or credential_json is not None):
        raise DemoRuntimeError("`--kimi-code-home` cannot be combined with Kimi file inputs")
    args: list[str] = []
    _extend_if_present(args, "--api-key", api_key)
    _extend_if_present(args, "--model-name", model_name)
    _extend_if_present(args, "--base-url", base_url)
    _extend_if_present(args, "--provider-type", provider_type)
    _extend_if_present(args, "--code-base-url", code_base_url)
    _extend_if_present(args, "--code-oauth-host", code_oauth_host)
    _extend_if_present(args, "--oauth-host", oauth_host)
    if disable_telemetry:
        args.append("--disable-telemetry")
    if code_home is not None:
        _require_dir(code_home, "`--kimi-code-home`")
        args.extend(["--code-home", str(code_home.resolve())])
    else:
        if config_toml is not None:
            if config_toml.is_file():
                args.extend(["--config-toml", str(config_toml.resolve())])
            elif require_existing_files:
                raise DemoRuntimeError(f"`--kimi-config-toml` file not found: {config_toml}")
        if credential_json is not None:
            if credential_json.is_file():
                args.extend(["--credential-json", str(credential_json.resolve())])
            elif require_existing_files:
                raise DemoRuntimeError(
                    f"`--kimi-credential-json` file not found: {credential_json}"
                )
    if not args:
        raise DemoRuntimeError(
            "Kimi credential input is required. Pass `--kimi-code-home`, "
            "`--kimi-auth-bundle`, `--kimi-config-toml`, `--kimi-credential-json`, "
            "or `--api-key`."
        )
    return args


def create_specialist(
    *,
    paths: DemoPaths,
    env: Mapping[str, str],
    member: TeamMemberParameters,
    credential_name: str,
    setup_name: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Create or replace one Kimi writer-team specialist."""

    stdout_path, stderr_path = paths.log_paths(f"specialist-{member.agent_name}")
    command = [
        "project",
        "specialist",
        "create",
        "--name",
        member.specialist_name,
        "--tool",
        "kimi",
        "--setup",
        setup_name,
        "--credential",
        credential_name,
        "--system-prompt-file",
        str(paths.project_dir / member.system_prompt_file),
    ]
    if prompt_mode_for_member(member) == "as_is":
        command.append("--no-unattended")
    command.extend(
        [
            "--system-skills-mode",
            "replace",
            "--system-skill-set",
            "core",
            "--yes",
        ]
    )
    payload = run_json_command(
        manager_cli_command(command),
        cwd=paths.project_dir,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        env=env,
        timeout_seconds=timeout_seconds,
    )
    write_json(paths.control_json_path(f"specialist-{member.agent_name}"), payload)
    return payload


def create_profile(
    *,
    paths: DemoPaths,
    env: Mapping[str, str],
    member: TeamMemberParameters,
    credential_name: str,
    notifier_appendix_text: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Create or replace one mailbox-enabled Kimi project profile."""

    stdout_path, stderr_path = paths.log_paths(f"profile-{member.agent_name}")
    prompt_mode = prompt_mode_for_member(member)
    payload = run_json_command(
        manager_cli_command(
            [
                "project",
                "profile",
                "create",
                "--name",
                member.profile_name,
                "--specialist",
                member.specialist_name,
                "--agent-name",
                member.agent_name,
                "--workdir",
                str(paths.project_dir),
                "--auth",
                credential_name,
                "--prompt-mode",
                prompt_mode,
                "--mail-transport",
                "filesystem",
                "--mail-root",
                str(paths.mailbox_root),
                "--mail-principal-id",
                member.mailbox_principal_id,
                "--mail-address",
                member.mailbox_address,
                "--gateway-mail-notifier-appendix-text",
                notifier_appendix_text,
                "--yes",
            ]
        ),
        cwd=paths.project_dir,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        env=env,
        timeout_seconds=timeout_seconds,
    )
    write_json(paths.control_json_path(f"profile-{member.agent_name}"), payload)
    return payload


def launch_agent(
    *,
    paths: DemoPaths,
    env: Mapping[str, str],
    member: TeamMemberParameters,
    session_name: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Launch one Kimi agent from its project profile."""

    stdout_path, stderr_path = paths.log_paths(f"launch-{member.agent_name}")
    command = [
        "project",
        "agents",
        "launch",
        "--profile",
        member.profile_name,
        "--name",
        member.agent_name,
        "--session-name",
        session_name,
    ]
    if uses_headless_backend(member):
        command.append("--headless")
    command.append("--gateway-background")
    payload = run_json_command(
        manager_cli_command(command),
        cwd=paths.project_dir,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        env=env,
        timeout_seconds=timeout_seconds,
    )
    write_json(paths.control_json_path(f"launch-{member.agent_name}"), payload)
    return payload


def enable_notifier(
    *,
    paths: DemoPaths,
    env: Mapping[str, str],
    agent_name: str,
    interval_seconds: int,
    appendix_text: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Enable gateway mail-notifier polling for one managed agent."""

    stdout_path, stderr_path = paths.log_paths(f"notifier-enable-{agent_name}")
    payload = run_json_command(
        manager_cli_command(
            [
                "agents",
                "single",
                "--agent-name",
                agent_name,
                "gateway",
                "mail-notifier",
                "enable",
                "--interval-seconds",
                str(interval_seconds),
                "--mode",
                "unread_only",
                "--appendix-text",
                appendix_text,
            ]
        ),
        cwd=paths.project_dir,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        env=env,
        timeout_seconds=timeout_seconds,
    )
    write_json(paths.control_json_path(f"notifier-enable-{agent_name}"), payload)
    return payload


def scoped_agent_json(
    *,
    paths: DemoPaths,
    env: Mapping[str, str],
    agent_name: str,
    args: Sequence[str],
    stem: str,
    timeout_seconds: float,
    stdin_text: str | None = None,
) -> dict[str, Any]:
    """Run one scoped managed-agent command and parse JSON output."""

    stdout_path, stderr_path = paths.log_paths(stem)
    return run_json_command(
        manager_cli_command(["agents", "single", "--agent-name", agent_name, *args]),
        cwd=paths.project_dir,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        env=env,
        timeout_seconds=timeout_seconds,
        stdin_text=stdin_text,
    )


def notifier_status(
    *,
    paths: DemoPaths,
    env: Mapping[str, str],
    agent_name: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Query gateway mail-notifier state for one managed agent."""

    return scoped_agent_json(
        paths=paths,
        env=env,
        agent_name=agent_name,
        args=["gateway", "mail-notifier", "status"],
        stem=f"notifier-status-{agent_name}",
        timeout_seconds=timeout_seconds,
    )


def disable_notifier(
    *,
    paths: DemoPaths,
    env: Mapping[str, str],
    agent_name: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Disable gateway mail-notifier polling for one managed agent."""

    return scoped_agent_json(
        paths=paths,
        env=env,
        agent_name=agent_name,
        args=["gateway", "mail-notifier", "disable"],
        stem=f"notifier-disable-{agent_name}",
        timeout_seconds=timeout_seconds,
    )


def agent_state(
    *,
    paths: DemoPaths,
    env: Mapping[str, str],
    agent_name: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Query operational state for one managed agent."""

    return scoped_agent_json(
        paths=paths,
        env=env,
        agent_name=agent_name,
        args=["state"],
        stem=f"agent-state-{agent_name}",
        timeout_seconds=timeout_seconds,
    )


def gateway_status(
    *,
    paths: DemoPaths,
    env: Mapping[str, str],
    agent_name: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Query live gateway state for one managed agent."""

    return scoped_agent_json(
        paths=paths,
        env=env,
        agent_name=agent_name,
        args=["gateway", "status"],
        stem=f"gateway-status-{agent_name}",
        timeout_seconds=timeout_seconds,
    )


def gateway_tui_state(
    *,
    paths: DemoPaths,
    env: Mapping[str, str],
    agent_name: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Query raw gateway-owned TUI state for one managed agent."""

    return scoped_agent_json(
        paths=paths,
        env=env,
        agent_name=agent_name,
        args=["gateway", "tui", "state"],
        stem=f"gateway-tui-state-{agent_name}",
        timeout_seconds=timeout_seconds,
    )


def mailbox_status(
    *,
    paths: DemoPaths,
    env: Mapping[str, str],
    agent_name: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Query late mailbox binding state for one managed agent."""

    return scoped_agent_json(
        paths=paths,
        env=env,
        agent_name=agent_name,
        args=["mailbox", "status"],
        stem=f"mailbox-status-{agent_name}",
        timeout_seconds=timeout_seconds,
    )


def project_agent_get(
    *,
    paths: DemoPaths,
    env: Mapping[str, str],
    agent_name: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Inspect one project-local managed-agent instance."""

    stdout_path, stderr_path = paths.log_paths(f"project-agent-get-{agent_name}")
    return run_json_command(
        manager_cli_command(["project", "agents", "get", "--name", agent_name]),
        cwd=paths.project_dir,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        env=env,
        timeout_seconds=timeout_seconds,
    )


def prompt_agent(
    *,
    paths: DemoPaths,
    env: Mapping[str, str],
    agent_name: str,
    prompt_text: str,
    stem: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Submit one prompt to a managed agent through the scoped CLI."""

    payload = scoped_agent_json(
        paths=paths,
        env=env,
        agent_name=agent_name,
        args=["prompt"],
        stem=stem,
        timeout_seconds=timeout_seconds,
        stdin_text=prompt_text,
    )
    write_json(paths.control_json_path(stem), payload)
    return payload


def send_agent_mail(
    *,
    paths: DemoPaths,
    env: Mapping[str, str],
    from_agent_name: str,
    to_address: str,
    subject: str,
    body_text: str,
    stem: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Send one managed-agent mailbox message."""

    payload = scoped_agent_json(
        paths=paths,
        env=env,
        agent_name=from_agent_name,
        args=[
            "mail",
            "send",
            "--to",
            to_address,
            "--subject",
            subject,
            "--body-content",
            body_text,
        ],
        stem=stem,
        timeout_seconds=timeout_seconds,
    )
    write_json(paths.control_json_path(stem), payload)
    return payload


def stop_agent(
    *,
    paths: DemoPaths,
    env: Mapping[str, str],
    agent_name: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Stop one managed agent."""

    return scoped_agent_json(
        paths=paths,
        env=env,
        agent_name=agent_name,
        args=["stop"],
        stem=f"stop-{agent_name}",
        timeout_seconds=timeout_seconds,
    )


def wait_for_team_ready(
    *,
    paths: DemoPaths,
    env: Mapping[str, str],
    agent_names: Sequence[str],
    timeout_seconds: float,
) -> dict[str, Any]:
    """Wait until every launched agent has a healthy gateway and enabled notifier."""

    deadline = time.monotonic() + timeout_seconds
    last_payload: dict[str, Any] = {}
    while time.monotonic() < deadline:
        agents: dict[str, Any] = {}
        ready = True
        for agent_name in agent_names:
            try:
                gateway_payload = gateway_status(
                    paths=paths,
                    env=env,
                    agent_name=agent_name,
                    timeout_seconds=30.0,
                )
                notifier_payload = notifier_status(
                    paths=paths,
                    env=env,
                    agent_name=agent_name,
                    timeout_seconds=30.0,
                )
            except DemoRuntimeError as exc:
                agents[agent_name] = {"ready": False, "error": str(exc)}
                ready = False
                continue
            agent_ready = bool(notifier_payload.get("enabled")) and (
                gateway_payload.get("gateway_health") in {"healthy", "starting"}
            )
            agents[agent_name] = {
                "ready": agent_ready,
                "gateway_status": gateway_payload,
                "notifier_status": notifier_payload,
            }
            ready = ready and agent_ready
        last_payload = {"agents": agents}
        if ready:
            payload = {"status": "ready", **last_payload}
            write_json(paths.control_json_path("ready-wait"), payload)
            return payload
        time.sleep(1.0)
    payload = {"status": "timeout", **last_payload}
    write_json(paths.control_json_path("ready-wait"), payload)
    raise DemoRuntimeError(f"team did not become ready within {timeout_seconds:.1f}s")


def attach_to_tmux_session(*, session_name: str) -> None:
    """Attach the caller terminal to one tmux session."""

    try:
        attach_tmux_session(session_name=session_name)
    except TmuxCommandError as exc:
        raise DemoRuntimeError(str(exc)) from exc


def ensure_kimi_command_available() -> str:
    """Return an available Kimi command name or fail early."""

    for command_name in ("kimi", "kimi-code"):
        if shutil.which(command_name) is not None:
            return command_name
    raise DemoRuntimeError("Neither `kimi` nor `kimi-code` was found on PATH")


def _extend_if_present(args: list[str], flag: str, value: str | None) -> None:
    """Append one CLI flag when a non-empty value is present."""

    if value is None:
        return
    stripped = value.strip()
    if stripped:
        args.extend([flag, stripped])


def _is_truthy(value: str | None) -> bool:
    """Return whether a text env value means true."""

    return value is not None and value.strip().lower() in {"1", "true", "yes", "on"}


def _require_dir(path: Path, label: str) -> None:
    """Require an existing directory."""

    if not path.is_dir():
        raise DemoRuntimeError(f"{label} directory not found: {path}")
