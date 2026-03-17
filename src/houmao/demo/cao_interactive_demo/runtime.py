"""Runtime orchestration helpers for the interactive CAO demo."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Sequence

from houmao.agents.realm_controller.backends.shadow_parser_stack import (
    ShadowParserStack,
)
from houmao.cao.rest_client import CaoRestClient

from houmao.demo.cao_interactive_demo.models import (
    DEFAULT_STARTUP_HEARTBEAT_INITIAL_DELAY_SECONDS,
    DEFAULT_STARTUP_HEARTBEAT_INTERVAL_SECONDS,
    DEFAULT_TERMINAL_LOG_RELATIVE_DIR,
    FIXED_CAO_BASE_URL,
    STALE_STOP_MARKERS,
    UNKNOWN_TOOL_STATE,
    CommandResult,
    CommandRunner,
    DemoEnvironment,
    DemoPaths,
    DemoState,
    DemoWorkflowError,
    OutputTextTailResult,
    ProgressWriter,
)
from houmao.demo.cao_interactive_demo.rendering import (
    _emit_startup_progress,
    _format_elapsed_seconds,
    _join_command,
    _parse_json_output,
    _require_non_empty_string,
)


def run_subprocess_command(
    command: Sequence[str],
    cwd: Path,
    stdout_path: Path,
    stderr_path: Path,
    timeout_seconds: float,
) -> CommandResult:
    """Run a subprocess command and persist its captured logs."""

    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stderr_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        completed = subprocess.run(
            list(command),
            check=False,
            capture_output=True,
            text=True,
            cwd=str(cwd),
            timeout=timeout_seconds,
        )
    except FileNotFoundError as exc:
        raise DemoWorkflowError(f"Command not found: `{command[0]}`.") from exc
    except subprocess.TimeoutExpired as exc:
        raise DemoWorkflowError(
            f"Command timed out after {timeout_seconds:.1f}s: `{_join_command(command)}`."
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


def _run_subprocess_command_with_wait_feedback(
    command: Sequence[str],
    cwd: Path,
    stdout_path: Path,
    stderr_path: Path,
    timeout_seconds: float,
    *,
    waiting_message: str,
    initial_delay_seconds: float = DEFAULT_STARTUP_HEARTBEAT_INITIAL_DELAY_SECONDS,
    heartbeat_interval_seconds: float = DEFAULT_STARTUP_HEARTBEAT_INTERVAL_SECONDS,
    progress_writer: ProgressWriter | None = None,
) -> CommandResult:
    """Run a subprocess while emitting recurring wait feedback on stderr."""

    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stderr_path.parent.mkdir(parents=True, exist_ok=True)
    writer = progress_writer or _emit_startup_progress
    started_at = time.monotonic()
    deadline = started_at + timeout_seconds
    next_heartbeat = started_at + max(initial_delay_seconds, 0.0)
    heartbeat_interval = max(heartbeat_interval_seconds, 0.1)

    try:
        with (
            stdout_path.open("w", encoding="utf-8") as stdout_handle,
            stderr_path.open("w", encoding="utf-8") as stderr_handle,
        ):
            process = subprocess.Popen(
                list(command),
                cwd=str(cwd),
                stdout=stdout_handle,
                stderr=stderr_handle,
                text=True,
            )
            while True:
                returncode = process.poll()
                if returncode is not None:
                    break

                now = time.monotonic()
                if now >= deadline:
                    process.kill()
                    process.wait()
                    raise DemoWorkflowError(
                        f"Command timed out after {timeout_seconds:.1f}s: `{_join_command(command)}`."
                    )

                if now >= next_heartbeat:
                    elapsed = _format_elapsed_seconds(now - started_at)
                    writer(f"{waiting_message} (elapsed: {elapsed})")
                    next_heartbeat = now + heartbeat_interval

                sleep_seconds = min(0.2, max(0.01, min(deadline - now, next_heartbeat - now)))
                time.sleep(sleep_seconds)
    except FileNotFoundError as exc:
        raise DemoWorkflowError(f"Command not found: `{command[0]}`.") from exc

    stdout = stdout_path.read_text(encoding="utf-8")
    stderr = stderr_path.read_text(encoding="utf-8")
    return CommandResult(
        args=tuple(str(part) for part in command),
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
    )


def _build_brain(
    *,
    paths: DemoPaths,
    env: DemoEnvironment,
    recipe_path: Path,
    run_command: CommandRunner,
) -> dict[str, object]:
    """Build the recipe-selected brain manifest used by the interactive demo."""

    command = _runtime_cli_command(
        [
            "build-brain",
            "--agent-def-dir",
            str(env.agent_def_dir),
            "--runtime-root",
            str(paths.runtime_root),
            "--recipe",
            str(recipe_path),
        ]
    )
    result = run_command(
        command,
        env.repo_root,
        paths.logs_dir / "build-brain.stdout",
        paths.logs_dir / "build-brain.stderr",
        env.timeout_seconds,
    )
    if result.returncode != 0:
        raise DemoWorkflowError(
            f"Failed to build the interactive demo brain manifest (see `{result.stderr_path}`)."
        )
    payload = _parse_json_output(result.stdout, context="build-brain output")
    _require_non_empty_string(
        payload.get("manifest_path"), context="build-brain missing manifest_path"
    )
    _require_non_empty_string(payload.get("home_path"), context="build-brain missing home_path")
    return payload


def _start_runtime_session(
    *,
    paths: DemoPaths,
    env: DemoEnvironment,
    tool: str,
    agent_identity: str,
    brain_manifest_path: Path,
    run_command: CommandRunner,
) -> dict[str, object]:
    """Launch the CAO-backed runtime session with a fixed loopback target."""

    command = _runtime_cli_command(
        [
            "start-session",
            "--agent-def-dir",
            str(env.agent_def_dir),
            "--runtime-root",
            str(paths.runtime_root),
            "--brain-manifest",
            str(brain_manifest_path),
            "--role",
            env.role_name,
            "--backend",
            "cao_rest",
            "--cao-base-url",
            FIXED_CAO_BASE_URL,
            "--cao-profile-store",
            str(_cao_profile_store(env.launcher_home_dir)),
            "--workdir",
            str(env.workdir),
            "--agent-identity",
            agent_identity,
        ]
    )
    stdout_path = paths.logs_dir / "start-session.stdout"
    stderr_path = paths.logs_dir / "start-session.stderr"
    if run_command is run_subprocess_command:
        result = _run_subprocess_command_with_wait_feedback(
            command,
            env.repo_root,
            stdout_path,
            stderr_path,
            env.timeout_seconds,
            waiting_message=(
                "Still waiting for the interactive "
                f"{_tool_display_name(tool)} session to launch and become "
                "ready for input."
            ),
        )
    else:
        result = run_command(
            command,
            env.repo_root,
            stdout_path,
            stderr_path,
            env.timeout_seconds,
        )
    if result.returncode != 0:
        raise DemoWorkflowError(
            f"Failed to start the interactive CAO session (see `{result.stderr_path}`)."
        )
    payload = _parse_json_output(result.stdout, context="start-session output")
    _require_non_empty_string(
        payload.get("session_manifest"),
        context="start-session output missing session_manifest",
    )
    return payload


def _kill_tmux_session(
    *,
    paths: DemoPaths,
    env: DemoEnvironment,
    session_name: str,
    run_command: CommandRunner,
) -> None:
    """Best-effort kill of one leftover tmux session."""

    has_session_result = run_command(
        ["tmux", "has-session", "-t", session_name],
        env.repo_root,
        paths.logs_dir / "tmux-has-session.stdout",
        paths.logs_dir / "tmux-has-session.stderr",
        env.timeout_seconds,
    )
    if has_session_result.returncode != 0:
        return

    kill_result = run_command(
        ["tmux", "kill-session", "-t", session_name],
        env.repo_root,
        paths.logs_dir / "tmux-kill-session.stdout",
        paths.logs_dir / "tmux-kill-session.stderr",
        env.timeout_seconds,
    )
    if kill_result.returncode != 0:
        raise DemoWorkflowError(
            f"Failed to kill stale tmux session `{session_name}` (see `{kill_result.stderr_path}`)."
        )


def _discover_tmux_sessions_for_agent_identity(
    *,
    paths: DemoPaths,
    env: DemoEnvironment,
    agent_identity: str,
    run_command: CommandRunner,
) -> list[str]:
    """Discover live tmux sessions whose persisted metadata matches one identity."""

    result = run_command(
        ["tmux", "list-sessions", "-F", "#{session_name}"],
        env.repo_root,
        paths.logs_dir / "tmux-list-sessions.stdout",
        paths.logs_dir / "tmux-list-sessions.stderr",
        env.timeout_seconds,
    )
    if result.returncode != 0:
        return _legacy_exact_tmux_session_names(
            paths=paths,
            env=env,
            agent_identity=agent_identity,
            run_command=run_command,
        )

    matches: list[str] = []
    for raw_line in result.stdout.splitlines():
        session_name = raw_line.strip()
        if not session_name:
            continue
        manifest_path = _read_tmux_manifest_path(
            paths=paths,
            env=env,
            session_name=session_name,
            run_command=run_command,
        )
        if manifest_path is None:
            continue
        if _manifest_matches_agent_identity(
            manifest_path=manifest_path,
            agent_identity=agent_identity,
            session_name=session_name,
        ):
            matches.append(session_name)

    for session_name in _legacy_exact_tmux_session_names(
        paths=paths,
        env=env,
        agent_identity=agent_identity,
        run_command=run_command,
    ):
        if session_name not in matches:
            matches.append(session_name)
    return matches


def _legacy_exact_tmux_session_names(
    *,
    paths: DemoPaths,
    env: DemoEnvironment,
    agent_identity: str,
    run_command: CommandRunner,
) -> list[str]:
    """Return the exact canonical tmux session name when it still exists."""

    result = run_command(
        ["tmux", "has-session", "-t", agent_identity],
        env.repo_root,
        paths.logs_dir / "tmux-has-session-legacy.stdout",
        paths.logs_dir / "tmux-has-session-legacy.stderr",
        env.timeout_seconds,
    )
    if result.returncode == 0:
        return [agent_identity]
    return []


def _read_tmux_manifest_path(
    *,
    paths: DemoPaths,
    env: DemoEnvironment,
    session_name: str,
    run_command: CommandRunner,
) -> Path | None:
    """Read the tmux-published manifest path for one live session."""

    safe_name = session_name.replace("/", "_")
    result = run_command(
        ["tmux", "show-environment", "-t", session_name, "AGENTSYS_MANIFEST_PATH"],
        env.repo_root,
        paths.logs_dir / f"tmux-show-environment-{safe_name}.stdout",
        paths.logs_dir / f"tmux-show-environment-{safe_name}.stderr",
        env.timeout_seconds,
    )
    if result.returncode != 0:
        return None

    for raw_line in result.stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        prefix = "AGENTSYS_MANIFEST_PATH="
        if not line.startswith(prefix):
            continue
        value = line[len(prefix) :].strip()
        if not value:
            return None
        manifest_path = Path(value)
        if not manifest_path.is_absolute():
            return None
        resolved_manifest_path = manifest_path.resolve()
        if not resolved_manifest_path.is_file():
            return None
        return resolved_manifest_path
    return None


def _manifest_matches_agent_identity(
    *,
    manifest_path: Path,
    agent_identity: str,
    session_name: str,
) -> bool:
    """Return whether one manifest binds the canonical identity to the session."""

    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return False
    if not isinstance(payload, dict):
        return False

    persisted_agent_identity = str(payload.get("agent_name", "")).strip()
    persisted_session_name = str(payload.get("tmux_session_name", "")).strip()
    return (
        persisted_agent_identity == agent_identity
        and persisted_session_name == session_name
    )


def _stop_remote_session(
    *,
    paths: DemoPaths,
    env: DemoEnvironment,
    agent_identity: str,
    run_command: CommandRunner,
    tolerate_stale: bool,
    log_prefix: str,
) -> CommandResult:
    """Issue `stop-session` against the persisted name-based agent identity."""

    result = run_command(
        _runtime_cli_command(
            [
                "stop-session",
                "--agent-identity",
                agent_identity,
            ]
        ),
        env.repo_root,
        paths.logs_dir / f"{log_prefix}.stdout",
        paths.logs_dir / f"{log_prefix}.stderr",
        env.timeout_seconds,
    )
    if result.returncode == 0:
        return result
    if tolerate_stale and _looks_like_stale_stop_failure(result):
        return result
    raise DemoWorkflowError(
        f"Failed to stop the interactive CAO session (see `{result.stderr_path}`)."
    )


def _looks_like_stale_stop_failure(result: CommandResult) -> bool:
    """Return whether a failed stop looks like a stale or missing remote session."""

    haystack = "\n".join([result.stdout, result.stderr]).lower()
    if any(marker in haystack for marker in STALE_STOP_MARKERS):
        return True

    if result.stdout.strip():
        try:
            payload = _parse_json_output(result.stdout, context="stop-session output")
        except DemoWorkflowError:
            return False
        detail = str(payload.get("detail", "")).lower()
        return any(marker in detail for marker in STALE_STOP_MARKERS)
    return False


def _runtime_cli_command(args: list[str]) -> list[str]:
    """Build a `realm_controller` CLI subprocess command."""

    return ["pixi", "run", "python", "-m", "houmao.agents.realm_controller", *args]


def _launcher_cli_command(args: list[str]) -> list[str]:
    """Build a `cao_server_launcher` CLI subprocess command."""

    return ["pixi", "run", "python", "-m", "houmao.cao.tools.cao_server_launcher", *args]


def _cao_profile_store(launcher_home_dir: Path) -> Path:
    """Return the CAO profile store path derived from launcher home."""

    return launcher_home_dir / ".aws" / "cli-agent-orchestrator" / "agent-store"


def _terminal_log_path(terminal_id: str, *, launcher_home_dir: Path) -> str:
    """Return the CAO terminal log path under the effective launcher home."""

    return str(
        (
            launcher_home_dir.expanduser().resolve()
            / DEFAULT_TERMINAL_LOG_RELATIVE_DIR
            / f"{terminal_id}.log"
        )
    )


def _resolved_terminal_log_path_for_state(state: DemoState) -> str:
    """Resolve the effective terminal log path for persisted demo state."""

    launcher_home_dir = _launcher_home_dir_from_cao_profile_store(state.cao_profile_store)
    if launcher_home_dir is None:
        return str(Path(state.terminal_log_path).expanduser())
    return _terminal_log_path(state.terminal_id, launcher_home_dir=launcher_home_dir)


def _launcher_home_dir_from_cao_profile_store(cao_profile_store: str) -> Path | None:
    """Infer launcher home from the persisted CAO profile-store path."""

    profile_store = Path(cao_profile_store).expanduser()
    if profile_store.name != "agent-store":
        return None
    if profile_store.parent.name != "cli-agent-orchestrator":
        return None
    if profile_store.parent.parent.name != ".aws":
        return None
    return profile_store.parent.parent.parent


def _best_effort_tool_state(*, terminal_id: str, client: CaoRestClient) -> str:
    """Return live CAO terminal status or `unknown` when lookup fails."""

    try:
        terminal = client.get_terminal(terminal_id)
    except Exception:
        return UNKNOWN_TOOL_STATE
    if terminal.status is None:
        return UNKNOWN_TOOL_STATE
    return terminal.status.value


def _best_effort_output_text_tail(
    *,
    tool: str,
    terminal_id: str,
    output_text_tail_chars: int,
    client: CaoRestClient,
) -> OutputTextTailResult:
    """Return a clean projected dialog tail for live inspection."""

    tool_label = _tool_display_name(tool)

    try:
        terminal_output = client.get_terminal_output(terminal_id, mode="full")
    except Exception as exc:
        return OutputTextTailResult(
            output_text_tail=None,
            note=(
                f"clean projected {tool_label} dialog tail unavailable: "
                f"live CAO output could not be fetched ({exc})"
            ),
        )

    try:
        parsed_snapshot = ShadowParserStack(tool=tool).parse_snapshot(
            terminal_output.output,
            baseline_pos=0,
        )
    except Exception as exc:
        return OutputTextTailResult(
            output_text_tail=None,
            note=(
                f"clean projected {tool_label} dialog tail unavailable: projection failed ({exc})"
            ),
        )

    if parsed_snapshot.surface_assessment.availability != "supported":
        return OutputTextTailResult(
            output_text_tail=None,
            note=(
                f"clean projected {tool_label} dialog tail unavailable: "
                f"live output did not match a supported {tool_label} surface"
            ),
        )

    dialog_text = parsed_snapshot.dialog_projection.dialog_text
    return OutputTextTailResult(
        output_text_tail=dialog_text[-output_text_tail_chars:],
        note=None,
    )


def _tool_display_name(tool: str) -> str:
    """Return a short operator-facing label for one demo tool."""

    tool_name = tool.strip()
    if tool_name == "claude":
        return "Claude"
    if tool_name == "codex":
        return "Codex"
    return tool_name
