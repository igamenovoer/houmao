"""Runtime and `houmao-mgr` helpers for the single-agent wake-up demo."""

from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any, Iterator, Mapping, Sequence

import click

from houmao.agents.realm_controller.agent_identity import AGENT_DEF_DIR_ENV_VAR
from houmao.agents.realm_controller.backends.tmux_runtime import (
    TmuxCommandError,
    attach_tmux_session,
    capture_tmux_pane,
    resolve_tmux_pane,
)
from houmao.agents.realm_controller.loaders import parse_env_file
from houmao.agents.realm_controller.loaders import load_brain_manifest
from houmao.agents.realm_controller.manifest import (
    load_session_manifest,
    parse_session_manifest_payload,
    runtime_owned_session_root_from_manifest_path,
)
from houmao.owned_paths import (
    HOUMAO_GLOBAL_MAILBOX_DIR_ENV_VAR,
    HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR,
    HOUMAO_GLOBAL_RUNTIME_DIR_ENV_VAR,
    HOUMAO_JOB_DIR_ENV_VAR,
    HOUMAO_LOCAL_JOBS_DIR_ENV_VAR,
)
from houmao.project.catalog import PROJECT_CATALOG_FILENAME, ProjectCatalog
from houmao.project.overlay import (
    PROJECT_CONFIG_FILENAME,
    PROJECT_CONTENT_DIRNAME,
    PROJECT_EASY_DIRNAME,
    PROJECT_MAILBOX_DIRNAME,
    PROJECT_OVERLAY_DIR_ENV_VAR,
    load_project_overlay,
)
from houmao.srv_ctrl.commands.managed_agents import (
    managed_agent_detail_payload,
    resolve_managed_agent_target,
)

from .models import (
    CommandResult,
    DemoPaths,
    FIXED_DEMO_PROJECT_AUTHOR_EMAIL,
    FIXED_DEMO_PROJECT_AUTHOR_NAME,
    FIXED_DEMO_PROJECT_COMMIT_MESSAGE,
    FIXED_DEMO_PROJECT_COMMIT_UTC,
    MANAGED_PROJECT_METADATA_NAME,
    PACK_NAME,
    ToolParameters,
    write_json,
)


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

    return ["pixi", "run", "houmao-mgr", "--print-json", *args]


def build_demo_environment(
    *,
    paths: DemoPaths,
    base_env: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Return the demo-owned environment for demo command invocations."""

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


def prepare_output_root(*, paths: DemoPaths, allow_reprovision: bool) -> None:
    """Create or reset the managed demo output layout."""

    cleanup_paths = (
        paths.control_dir,
        paths.logs_dir,
        paths.runtime_root,
        paths.registry_root,
        paths.jobs_root,
        paths.deliveries_dir,
        paths.evidence_dir,
        paths.project_dir,
        paths.overlay_dir / PROJECT_MAILBOX_DIRNAME,
    )
    create_paths = (
        paths.output_root,
        paths.control_dir,
        paths.logs_dir,
        paths.runtime_root,
        paths.registry_root,
        paths.jobs_root,
        paths.deliveries_dir,
        paths.evidence_dir,
        paths.overlay_dir,
    )
    if allow_reprovision:
        for target in cleanup_paths:
            if target.exists():
                shutil.rmtree(target)
    for target in create_paths:
        target.mkdir(parents=True, exist_ok=True)


def prepare_persistent_overlay_roots(*, paths: DemoPaths) -> None:
    """Ensure the reusable overlay-backed specialist roots are present."""

    persistent_paths = (
        paths.overlay_dir / "agents",
        paths.overlay_dir / PROJECT_CONTENT_DIRNAME,
        paths.overlay_dir / PROJECT_EASY_DIRNAME,
    )
    for target in persistent_paths:
        target.mkdir(parents=True, exist_ok=True)


def overlay_persistent_state_present(*, paths: DemoPaths) -> bool:
    """Return whether reusable overlay-backed specialist state is already present."""

    required_paths = (
        paths.overlay_dir / PROJECT_CONFIG_FILENAME,
        paths.overlay_dir / PROJECT_CATALOG_FILENAME,
        paths.overlay_dir / "agents",
        paths.overlay_dir / PROJECT_CONTENT_DIRNAME,
        paths.overlay_dir / PROJECT_EASY_DIRNAME,
    )
    return all(path.exists() for path in required_paths)


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


def initialize_project_overlay(
    *,
    paths: DemoPaths,
    env: Mapping[str, str],
    timeout_seconds: float,
) -> dict[str, Any]:
    """Initialize the redirected project overlay for the copied project."""

    payload = run_json_command(
        manager_cli_command(["project", "init"]),
        cwd=paths.project_dir,
        stdout_path=paths.logs_dir / "project-init.stdout",
        stderr_path=paths.logs_dir / "project-init.stderr",
        env=env,
        timeout_seconds=timeout_seconds,
    )
    write_json(paths.project_init_path, payload)
    return payload


def import_project_auth_from_fixture(
    *,
    paths: DemoPaths,
    env: Mapping[str, str],
    tool: str,
    tool_parameters: ToolParameters,
    repo_root: Path,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Import one project-local auth bundle from a tracked fixture directory."""

    fixture_dir = (
        tool_parameters.auth_fixture_dir
        if tool_parameters.auth_fixture_dir.is_absolute()
        else (repo_root / tool_parameters.auth_fixture_dir).resolve()
    )
    if not fixture_dir.is_dir():
        raise DemoRuntimeError(f"fixture auth bundle not found: {fixture_dir}")

    env_path = (fixture_dir / "env" / "vars.env").resolve()
    env_values = parse_env_file(env_path)
    files_root = (fixture_dir / "files").resolve()
    overlay = load_project_overlay(paths.overlay_dir / PROJECT_CONFIG_FILENAME)
    try:
        ProjectCatalog.from_overlay(overlay).load_auth_profile(
            tool=tool,
            name=tool_parameters.auth_name,
        )
        auth_operation = "set"
    except FileNotFoundError:
        auth_operation = "add"
    command = [
        "project",
        "credentials",
        tool,
        auth_operation,
        "--name",
        tool_parameters.auth_name,
    ]
    if tool == "claude":
        _extend_if_present(command, "--api-key", env_values.get("ANTHROPIC_API_KEY"))
        _extend_if_present(command, "--auth-token", env_values.get("ANTHROPIC_AUTH_TOKEN"))
        _extend_if_present(command, "--base-url", env_values.get("ANTHROPIC_BASE_URL"))
        _extend_if_present(command, "--model", env_values.get("ANTHROPIC_MODEL"))
        _extend_if_present(
            command,
            "--small-fast-model",
            env_values.get("ANTHROPIC_SMALL_FAST_MODEL"),
        )
        _extend_if_present(
            command,
            "--subagent-model",
            env_values.get("CLAUDE_CODE_SUBAGENT_MODEL"),
        )
        _extend_if_present(
            command,
            "--default-opus-model",
            env_values.get("ANTHROPIC_DEFAULT_OPUS_MODEL"),
        )
        _extend_if_present(
            command,
            "--default-sonnet-model",
            env_values.get("ANTHROPIC_DEFAULT_SONNET_MODEL"),
        )
        _extend_if_present(
            command,
            "--default-haiku-model",
            env_values.get("ANTHROPIC_DEFAULT_HAIKU_MODEL"),
        )
        state_template = files_root / "claude_state.template.json"
        if state_template.is_file():
            command.extend(["--state-template-file", str(state_template)])
        if not (
            env_values.get("ANTHROPIC_API_KEY", "").strip()
            or env_values.get("ANTHROPIC_AUTH_TOKEN", "").strip()
        ):
            raise DemoRuntimeError(
                f"Claude fixture `{fixture_dir}` must set `ANTHROPIC_API_KEY` or "
                "`ANTHROPIC_AUTH_TOKEN`."
            )
    elif tool == "codex":
        _extend_if_present(command, "--api-key", env_values.get("OPENAI_API_KEY"))
        _extend_if_present(command, "--base-url", env_values.get("OPENAI_BASE_URL"))
        _extend_if_present(command, "--org-id", env_values.get("OPENAI_ORG_ID"))
        auth_json = files_root / "auth.json"
        if auth_json.is_file():
            command.extend(["--auth-json", str(auth_json)])
        if not env_values.get("OPENAI_API_KEY", "").strip():
            raise DemoRuntimeError(
                f"Codex fixture `{fixture_dir}` must set `OPENAI_API_KEY` in `{env_path}`."
            )
    else:
        raise DemoRuntimeError(f"unsupported auth import tool: {tool}")

    payload = run_json_command(
        manager_cli_command(command),
        cwd=paths.project_dir,
        stdout_path=paths.logs_dir / "auth-import.stdout",
        stderr_path=paths.logs_dir / "auth-import.stderr",
        env=env,
        timeout_seconds=timeout_seconds,
    )
    payload = {"auth_operation": auth_operation, **payload}
    write_json(paths.auth_import_path, payload)
    return payload


def create_specialist(
    *,
    paths: DemoPaths,
    env: Mapping[str, str],
    specialist_name: str,
    tool: str,
    tool_parameters: ToolParameters,
    system_prompt_file: Path,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Create one project-local specialist through `project easy`."""

    payload = run_json_command(
        manager_cli_command(
            [
                "project",
                "easy",
                "specialist",
                "create",
                "--name",
                specialist_name,
                "--tool",
                tool,
                "--setup",
                tool_parameters.setup,
                "--credential",
                tool_parameters.auth_name,
                "--system-prompt-file",
                str(system_prompt_file),
            ]
        ),
        cwd=paths.project_dir,
        stdout_path=paths.logs_dir / "specialist-create.stdout",
        stderr_path=paths.logs_dir / "specialist-create.stderr",
        env=env,
        timeout_seconds=timeout_seconds,
    )
    write_json(paths.specialist_create_path, payload)
    return payload


def ensure_specialist(
    *,
    paths: DemoPaths,
    env: Mapping[str, str],
    specialist_name: str,
    tool: str,
    tool_parameters: ToolParameters,
    system_prompt_file: Path,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Reuse one project-local specialist when present or create it when absent."""

    try:
        payload = get_specialist(
            paths=paths,
            env=env,
            specialist_name=specialist_name,
            timeout_seconds=timeout_seconds,
        )
        write_json(
            paths.specialist_create_path,
            {
                "status": "reused",
                "specialist": specialist_name,
                "tool": tool,
            },
        )
        return payload
    except DemoRuntimeError as exc:
        if "not found" not in str(exc).lower():
            raise

    create_specialist(
        paths=paths,
        env=env,
        specialist_name=specialist_name,
        tool=tool,
        tool_parameters=tool_parameters,
        system_prompt_file=system_prompt_file,
        timeout_seconds=timeout_seconds,
    )
    return get_specialist(
        paths=paths,
        env=env,
        specialist_name=specialist_name,
        timeout_seconds=timeout_seconds,
    )


def get_specialist(
    *,
    paths: DemoPaths,
    env: Mapping[str, str],
    specialist_name: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Inspect one persisted project-local specialist definition."""

    payload = run_json_command(
        manager_cli_command(
            [
                "project",
                "easy",
                "specialist",
                "get",
                "--name",
                specialist_name,
            ]
        ),
        cwd=paths.project_dir,
        stdout_path=paths.logs_dir / "specialist-get.stdout",
        stderr_path=paths.logs_dir / "specialist-get.stderr",
        env=env,
        timeout_seconds=timeout_seconds,
    )
    write_json(paths.specialist_get_path, payload)
    return payload


def initialize_project_mailbox(
    *,
    paths: DemoPaths,
    env: Mapping[str, str],
    timeout_seconds: float,
) -> dict[str, Any]:
    """Initialize the project mailbox under the redirected overlay."""

    payload = run_json_command(
        manager_cli_command(["project", "mailbox", "init"]),
        cwd=paths.project_dir,
        stdout_path=paths.logs_dir / "project-mailbox-init.stdout",
        stderr_path=paths.logs_dir / "project-mailbox-init.stderr",
        env=env,
        timeout_seconds=timeout_seconds,
    )
    write_json(paths.project_mailbox_init_path, payload)
    return payload


def register_project_mailbox_account(
    *,
    paths: DemoPaths,
    env: Mapping[str, str],
    address: str,
    principal_id: str,
    output_path: Path,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Register one project-mailbox account under the redirected overlay."""

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
            ]
        ),
        cwd=paths.project_dir,
        stdout_path=paths.logs_dir / f"{output_path.stem}.stdout",
        stderr_path=paths.logs_dir / f"{output_path.stem}.stderr",
        env=env,
        timeout_seconds=timeout_seconds,
    )
    write_json(output_path, payload)
    return payload


def launch_instance(
    *,
    paths: DemoPaths,
    env: Mapping[str, str],
    specialist_name: str,
    instance_name: str,
    session_name: str,
    mail_root: Path,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Launch one TUI managed-agent instance from the selected specialist."""

    result = run_command(
        manager_cli_command(
            [
                "project",
                "easy",
                "instance",
                "launch",
                "--specialist",
                specialist_name,
                "--name",
                instance_name,
                "--session-name",
                session_name,
                "--mail-transport",
                "filesystem",
                "--mail-root",
                str(mail_root),
            ]
        ),
        cwd=paths.project_dir,
        stdout_path=paths.logs_dir / "instance-launch.stdout",
        stderr_path=paths.logs_dir / "instance-launch.stderr",
        env=env,
        timeout_seconds=timeout_seconds,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "instance launch failed"
        raise DemoRuntimeError(detail)
    payload = parse_launch_output(result.stdout)
    payload.update(
        {
            "specialist_name": specialist_name,
            "instance_name": instance_name,
            "session_name_requested": session_name,
            "stdout_path": str(result.stdout_path),
            "stderr_path": str(result.stderr_path),
        }
    )
    write_json(paths.instance_launch_path, payload)
    return payload


def parse_launch_output(stdout: str) -> dict[str, Any]:
    """Parse the local launch result payload from modern JSON or legacy plain text."""

    payload: dict[str, Any] = {"raw_stdout": stdout}
    decoder = json.JSONDecoder()
    index = 0
    decoded_any = False
    while index < len(stdout):
        while index < len(stdout) and stdout[index].isspace():
            index += 1
        if index >= len(stdout):
            break
        try:
            parsed, next_index = decoder.raw_decode(stdout, index)
        except json.JSONDecodeError:
            break
        if isinstance(parsed, dict):
            payload.update(parsed)
            decoded_any = True
        index = next_index
    if not decoded_any:
        for line in stdout.splitlines():
            stripped = line.strip()
            if "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            payload[key] = value
    if "manifest_path" not in payload:
        raise DemoRuntimeError("unable to parse local launch output for `manifest_path`")
    return payload


def get_instance(
    *,
    paths: DemoPaths,
    env: Mapping[str, str],
    instance_name: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Inspect one running managed-agent instance through `project easy`."""

    payload = run_json_command(
        manager_cli_command(
            [
                "project",
                "easy",
                "instance",
                "get",
                "--name",
                instance_name,
            ]
        ),
        cwd=paths.project_dir,
        stdout_path=paths.logs_dir / "instance-get.stdout",
        stderr_path=paths.logs_dir / "instance-get.stderr",
        env=env,
        timeout_seconds=timeout_seconds,
    )
    write_json(paths.instance_get_path, payload)
    return payload


def query_agent_show(
    *,
    paths: DemoPaths,
    env: Mapping[str, str],
    agent_name: str,
) -> dict[str, Any]:
    """Query one managed-agent detail view and persist the result."""

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
    paths: DemoPaths,
    env: Mapping[str, str],
    agent_name: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Query one managed-agent summary view and persist the result."""

    payload = run_json_command(
        manager_cli_command(["agents", "state", "--agent-name", agent_name]),
        cwd=paths.project_dir,
        stdout_path=paths.logs_dir / "agent-state.stdout",
        stderr_path=paths.logs_dir / "agent-state.stderr",
        env=env,
        timeout_seconds=timeout_seconds,
    )
    write_json(paths.agent_state_path, payload)
    return payload


def register_live_mailbox_binding(
    *,
    paths: DemoPaths,
    env: Mapping[str, str],
    agent_name: str,
    mailbox_principal_id: str,
    mailbox_address: str,
    mailbox_root: Path,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Register one explicit live mailbox binding for the running managed agent."""

    payload = run_json_command(
        manager_cli_command(
            [
                "agents",
                "mailbox",
                "register",
                "--agent-name",
                agent_name,
                "--mailbox-root",
                str(mailbox_root),
                "--principal-id",
                mailbox_principal_id,
                "--address",
                mailbox_address,
                "--mode",
                "force",
            ]
        ),
        cwd=paths.project_dir,
        stdout_path=paths.logs_dir / "mailbox-register.stdout",
        stderr_path=paths.logs_dir / "mailbox-register.stderr",
        env=env,
        timeout_seconds=timeout_seconds,
    )
    write_json(paths.mailbox_register_path, payload)
    return payload


def attach_gateway(
    *,
    paths: DemoPaths,
    env: Mapping[str, str],
    agent_name: str,
    timeout_seconds: float,
    foreground: bool = False,
) -> dict[str, Any]:
    """Attach the live gateway for the selected managed agent."""

    command = ["agents", "gateway", "attach", "--agent-name", agent_name]
    if foreground:
        command.append("--foreground")
    payload = run_json_command(
        manager_cli_command(command),
        cwd=paths.project_dir,
        stdout_path=paths.logs_dir / "gateway-attach.stdout",
        stderr_path=paths.logs_dir / "gateway-attach.stderr",
        env=env,
        timeout_seconds=timeout_seconds,
    )
    write_json(paths.gateway_attach_path, payload)
    return payload


def gateway_status(
    *,
    paths: DemoPaths,
    env: Mapping[str, str],
    agent_name: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Query the live gateway status for one managed agent."""

    return run_json_command(
        manager_cli_command(["agents", "gateway", "status", "--agent-name", agent_name]),
        cwd=paths.project_dir,
        stdout_path=paths.logs_dir / "gateway-status.stdout",
        stderr_path=paths.logs_dir / "gateway-status.stderr",
        env=env,
        timeout_seconds=timeout_seconds,
    )


def enable_notifier(
    *,
    paths: DemoPaths,
    env: Mapping[str, str],
    agent_name: str,
    interval_seconds: int,
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
        cwd=paths.project_dir,
        stdout_path=paths.logs_dir / "notifier-enable.stdout",
        stderr_path=paths.logs_dir / "notifier-enable.stderr",
        env=env,
        timeout_seconds=timeout_seconds,
    )
    write_json(paths.notifier_enable_path, payload)
    return payload


def enable_notifier_with_retry(
    *,
    paths: DemoPaths,
    env: Mapping[str, str],
    agent_name: str,
    interval_seconds: int,
    timeout_seconds: float,
    attempts: int = 3,
) -> dict[str, Any]:
    """Enable notifier polling with one bounded retry window after attach."""

    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return enable_notifier(
                paths=paths,
                env=env,
                agent_name=agent_name,
                interval_seconds=interval_seconds,
                timeout_seconds=timeout_seconds,
            )
        except DemoRuntimeError as exc:
            last_error = exc
            if attempt == attempts:
                break
            try:
                gateway_status(
                    paths=paths,
                    env=env,
                    agent_name=agent_name,
                    timeout_seconds=30.0,
                )
            except DemoRuntimeError:
                pass
    raise DemoRuntimeError(str(last_error) if last_error is not None else "notifier enable failed")


def notifier_status(
    *,
    paths: DemoPaths,
    env: Mapping[str, str],
    agent_name: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Query gateway mail-notifier status for one managed agent."""

    return run_json_command(
        manager_cli_command(
            ["agents", "gateway", "mail-notifier", "status", "--agent-name", agent_name]
        ),
        cwd=paths.project_dir,
        stdout_path=paths.logs_dir / "notifier-status.stdout",
        stderr_path=paths.logs_dir / "notifier-status.stderr",
        env=env,
        timeout_seconds=timeout_seconds,
    )


def disable_notifier(
    *,
    paths: DemoPaths,
    env: Mapping[str, str],
    agent_name: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Disable gateway mail-notifier behavior for one managed agent."""

    return run_json_command(
        manager_cli_command(
            ["agents", "gateway", "mail-notifier", "disable", "--agent-name", agent_name]
        ),
        cwd=paths.project_dir,
        stdout_path=paths.logs_dir / "notifier-disable.stdout",
        stderr_path=paths.logs_dir / "notifier-disable.stderr",
        env=env,
        timeout_seconds=timeout_seconds,
    )


def attach_to_demo_session(*, session_name: str) -> None:
    """Attach the caller terminal to the live demo tmux session."""

    try:
        attach_tmux_session(session_name=session_name)
    except TmuxCommandError as exc:
        raise DemoRuntimeError(str(exc)) from exc


def capture_gateway_console(
    *,
    paths: DemoPaths,
    env: Mapping[str, str],
    agent_name: str,
    fallback_session_name: str | None,
    timeout_seconds: float,
    lines: int,
) -> dict[str, Any]:
    """Capture the current gateway console text from the authoritative tmux window."""

    status_payload = gateway_status(
        paths=paths,
        env=env,
        agent_name=agent_name,
        timeout_seconds=timeout_seconds,
    )
    session_name = str(
        status_payload.get("tmux_session_name") or fallback_session_name or ""
    ).strip()
    if not session_name:
        raise DemoRuntimeError("gateway status did not include a tmux session name")
    window_index = status_payload.get("gateway_tmux_window_index")
    if window_index is None:
        raise DemoRuntimeError(
            "gateway is not attached in a watchable auxiliary tmux window for this demo"
        )
    try:
        pane = resolve_tmux_pane(session_name=session_name, window_index=str(window_index))
        full_text = capture_tmux_pane(target=pane.pane_id)
    except TmuxCommandError as exc:
        raise DemoRuntimeError(str(exc)) from exc
    tail_lines = full_text.splitlines()[-lines:] if lines > 0 else full_text.splitlines()
    return {
        "gateway_status": status_payload,
        "session_name": session_name,
        "window_index": str(window_index),
        "pane_id": pane.pane_id,
        "text": "\n".join(tail_lines) + ("\n" if tail_lines else ""),
    }


def stop_instance(
    *,
    paths: DemoPaths,
    env: Mapping[str, str],
    instance_name: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Stop one managed-agent instance through `project easy`."""

    return run_json_command(
        manager_cli_command(["project", "easy", "instance", "stop", "--name", instance_name]),
        cwd=paths.project_dir,
        stdout_path=paths.logs_dir / "instance-stop.stdout",
        stderr_path=paths.logs_dir / "instance-stop.stderr",
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

    resolved_fixture = project_fixture.resolve()
    resolved_project_dir = project_dir.resolve()
    if not resolved_fixture.is_dir():
        raise DemoRuntimeError(f"dummy project fixture directory not found: {resolved_fixture}")
    if resolved_project_dir.exists():
        if not allow_reprovision:
            raise DemoRuntimeError(
                "demo project directory already exists before a stopped demo state was found: "
                f"{resolved_project_dir}"
            )
        shutil.rmtree(resolved_project_dir)

    shutil.copytree(resolved_fixture, resolved_project_dir)
    _write_managed_project_metadata(
        project_workdir=resolved_project_dir, fixture_dir=resolved_fixture
    )
    _initialize_demo_git_repo(project_workdir=resolved_project_dir)
    return resolved_project_dir


def expose_project_mailbox_skills(
    *,
    project_workdir: Path,
    brain_manifest_path: Path,
    brain_home_path: Path,
    launch_helper_path: Path,
) -> None:
    """Keep the copied project free of mailbox skill mirrors.

    The runtime-owned mailbox skills are installed into the selected tool's
    native runtime home. This supported demo intentionally avoids staging a
    second project-local `skills/` mirror so the maintained contract stays on
    the native skill surface.
    """

    del project_workdir
    del brain_manifest_path
    del brain_home_path
    del launch_helper_path
    return None


def _write_managed_project_metadata(*, project_workdir: Path, fixture_dir: Path) -> None:
    """Write the demo-owned metadata marker for one copied repo."""

    write_json(
        project_workdir / MANAGED_PROJECT_METADATA_NAME,
        {
            "schema_version": 1,
            "managed_by": PACK_NAME,
            "fixture_dir": str(fixture_dir.resolve()),
            "prepared_at": FIXED_DEMO_PROJECT_COMMIT_UTC,
        },
    )


def _initialize_demo_git_repo(*, project_workdir: Path) -> None:
    """Initialize one copied fixture as a standalone git repo."""

    fixed_identity_env = {
        "GIT_AUTHOR_NAME": FIXED_DEMO_PROJECT_AUTHOR_NAME,
        "GIT_AUTHOR_EMAIL": FIXED_DEMO_PROJECT_AUTHOR_EMAIL,
        "GIT_COMMITTER_NAME": FIXED_DEMO_PROJECT_AUTHOR_NAME,
        "GIT_COMMITTER_EMAIL": FIXED_DEMO_PROJECT_AUTHOR_EMAIL,
        "GIT_AUTHOR_DATE": FIXED_DEMO_PROJECT_COMMIT_UTC,
        "GIT_COMMITTER_DATE": FIXED_DEMO_PROJECT_COMMIT_UTC,
    }
    _run_required_git_command(["git", "init", "--initial-branch", "main"], cwd=project_workdir)
    _run_required_git_command(["git", "add", "--all"], cwd=project_workdir)
    _run_required_git_command(
        [
            "git",
            "commit",
            "--allow-empty",
            "--no-gpg-sign",
            "-m",
            FIXED_DEMO_PROJECT_COMMIT_MESSAGE,
        ],
        cwd=project_workdir,
        env=fixed_identity_env,
    )


def _run_required_git_command(
    args: list[str],
    *,
    cwd: Path,
    env: Mapping[str, str] | None = None,
) -> None:
    """Run one required git command or raise clearly."""

    merged_env = dict(os.environ)
    if env is not None:
        merged_env.update(env)
    result = subprocess.run(
        args,
        cwd=str(cwd.resolve()),
        check=False,
        capture_output=True,
        text=True,
        env=merged_env,
    )
    if result.returncode == 0:
        return
    detail = result.stderr.strip() or result.stdout.strip() or "git command failed"
    raise DemoRuntimeError(f"`{' '.join(args)}` failed: {detail}")


def _extend_if_present(command: list[str], flag: str, value: str | None) -> None:
    """Append one CLI option when the value is non-empty."""

    if value is None or not value.strip():
        return
    command.extend([flag, value.strip()])


def _require_json_object(payload: object) -> dict[str, Any]:
    """Require one decoded JSON object payload."""

    if not isinstance(payload, dict):
        raise DemoRuntimeError("command did not return a JSON object")
    return dict(payload)
