"""Interactive CAO full-pipeline demo lifecycle utilities.

This module implements the operator-facing lifecycle for the interactive
Claude-on-CAO demo pack. The workflow is intentionally stateful: `start`
builds a brain, launches a CAO-backed session, and persists stable metadata;
`send-turn` reuses that state to drive repeated prompts; `inspect` prints the
commands needed for live tmux/log observation; `verify` writes a machine-readable
report; and `stop` tears down the active session while tolerating stale remote
state.

Functions
---------
main
    CLI entrypoint for the interactive demo commands.
start_demo
    Start or replace the interactive CAO demo session.
send_turn
    Send one prompt turn to the active demo session.
inspect_demo
    Render human-friendly or JSON inspection output.
verify_demo
    Generate a verification report from persisted turn artifacts.
stop_demo
    Stop the active demo session and mark local state inactive.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable, Sequence, TypeAlias, TypeVar

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from gig_agents.agents.brain_launch_runtime.agent_identity import (
    normalize_agent_identity_name,
)
from gig_agents.agents.brain_launch_runtime.backends.claude_code_shadow import (
    ClaudeCodeShadowParser,
)
from gig_agents.cao.rest_client import CaoRestClient

FIXED_CAO_BASE_URL = "http://127.0.0.1:9889"
DEFAULT_AGENT_NAME = "cao-interactive-demo"
DEFAULT_CAO_SERVICE_NAME = "cli-agent-orchestrator"
DEFAULT_CONFIG_PROFILE = "default"
DEFAULT_CREDENTIAL_PROFILE = "personal-a-default"
DEFAULT_DEMO_ROOT_DIRNAME = "cao-interactive-full-pipeline-demo"
DEFAULT_ROLE_NAME = "gpu-kernel-coder"
DEFAULT_WORKTREE_DIRNAME = "wktree"
DEFAULT_TIMEOUT_SECONDS = 180.0
DEFAULT_TOOL_NAME = "claude"
DEFAULT_SKILLS: tuple[str, ...] = ("openspec-apply-change",)
DEFAULT_LIVE_CAO_TIMEOUT_SECONDS = 5.0
DEFAULT_STARTUP_HEARTBEAT_INITIAL_DELAY_SECONDS = 2.0
DEFAULT_STARTUP_HEARTBEAT_INTERVAL_SECONDS = 5.0
DEFAULT_TERMINAL_LOG_RELATIVE_DIR = Path(".aws") / "cli-agent-orchestrator" / "logs" / "terminal"
PORT_LISTEN_STATE = "0A"
CURRENT_RUN_ROOT_FILENAME = "current_run_root.txt"
EMPTY_RESPONSE_ERROR = "interactive CAO turn returned an empty response"
UNKNOWN_CLAUDE_CODE_STATE = "unknown"
STALE_STOP_MARKERS: tuple[str, ...] = (
    "agent not found",
    "does not exist",
    "manifest pointer missing",
    "manifest pointer stale",
    "no such session",
    "not found",
    "404",
)


class DemoWorkflowError(RuntimeError):
    """Raised when the interactive demo workflow cannot proceed safely."""


class _StrictModel(BaseModel):
    """Shared strict model config for persisted demo artifacts."""

    model_config = ConfigDict(extra="forbid", strict=True)


class DemoState(_StrictModel):
    """Persisted lifecycle state for the interactive demo."""

    active: bool
    agent_identity: str
    session_manifest: str
    session_name: str
    tmux_target: str
    terminal_id: str
    terminal_log_path: str
    runtime_root: str
    workspace_dir: str
    brain_home: str
    brain_manifest: str
    cao_base_url: str
    cao_profile_store: str
    launcher_config_path: str
    updated_at: str
    turn_count: int = 0

    @field_validator(
        "agent_identity",
        "session_manifest",
        "session_name",
        "tmux_target",
        "terminal_id",
        "terminal_log_path",
        "runtime_root",
        "workspace_dir",
        "brain_home",
        "brain_manifest",
        "cao_base_url",
        "cao_profile_store",
        "launcher_config_path",
        "updated_at",
    )
    @classmethod
    def _not_blank(cls, value: str) -> str:
        """Require non-empty string payload fields."""

        if not value.strip():
            raise ValueError("must not be empty")
        return value


class TurnRecord(_StrictModel):
    """Persisted artifact for one `send-turn` execution."""

    turn_index: int
    agent_identity: str
    prompt: str
    started_at_utc: str
    completed_at_utc: str
    exit_status: int
    response_text: str
    events: list[dict[str, object]]
    stdout_path: str
    stderr_path: str

    @field_validator(
        "agent_identity",
        "prompt",
        "started_at_utc",
        "completed_at_utc",
        "stdout_path",
        "stderr_path",
    )
    @classmethod
    def _record_string_not_blank(cls, value: str) -> str:
        """Require non-empty turn record string fields."""

        if not value.strip():
            raise ValueError("must not be empty")
        return value


class VerificationTurnSummary(_StrictModel):
    """Stable turn summary embedded in verification reports."""

    turn_index: int
    agent_identity: str
    exit_status: int
    response_text: str

    @field_validator("agent_identity", "response_text")
    @classmethod
    def _summary_string_not_blank(cls, value: str) -> str:
        """Require non-empty verification turn string fields."""

        if not value.strip():
            raise ValueError("must not be empty")
        return value


class VerificationReport(_StrictModel):
    """Machine-readable verification report for the interactive workflow."""

    status: str
    backend: str
    tool: str
    cao_base_url: str
    agent_identity: str
    unique_agent_identity_count: int
    turn_count: int
    turns: list[VerificationTurnSummary]
    session_manifest: str
    workspace_dir: str
    tmux_target: str
    terminal_id: str
    terminal_log_path: str
    generated_at_utc: str

    @field_validator(
        "status",
        "backend",
        "tool",
        "cao_base_url",
        "agent_identity",
        "session_manifest",
        "workspace_dir",
        "tmux_target",
        "terminal_id",
        "terminal_log_path",
        "generated_at_utc",
    )
    @classmethod
    def _report_string_not_blank(cls, value: str) -> str:
        """Require non-empty verification report string fields."""

        if not value.strip():
            raise ValueError("must not be empty")
        return value


@dataclass(frozen=True)
class DemoPaths:
    """Resolved filesystem layout for the interactive demo workspace."""

    workspace_root: Path
    runtime_root: Path
    logs_dir: Path
    turns_dir: Path
    state_path: Path
    report_path: Path
    launcher_config_path: Path

    @classmethod
    def from_workspace_root(cls, workspace_root: Path) -> "DemoPaths":
        """Create demo path layout from the workspace root."""

        root = workspace_root.expanduser().resolve()
        return cls(
            workspace_root=root,
            runtime_root=root / "runtime",
            logs_dir=root / "logs",
            turns_dir=root / "turns",
            state_path=root / "state.json",
            report_path=root / "report.json",
            launcher_config_path=root / "cao-server-launcher.toml",
        )


@dataclass(frozen=True)
class DemoEnvironment:
    """Resolved operator configuration for one CLI invocation."""

    repo_root: Path
    demo_base_root: Path
    current_run_root_path: Path
    agent_def_dir: Path
    launcher_home_dir: Path
    workdir: Path
    role_name: str
    config_profile: str
    credential_profile: str
    skills: tuple[str, ...]
    timeout_seconds: float
    yes_to_all: bool
    provision_worktree: bool


@dataclass(frozen=True)
class DemoInvocation:
    """Resolved path and environment inputs for one CLI command."""

    paths: DemoPaths
    env: DemoEnvironment


@dataclass(frozen=True)
class CommandResult:
    """Captured subprocess result plus persisted log locations."""

    args: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str
    stdout_path: Path
    stderr_path: Path


@dataclass(frozen=True)
class OutputTextTailResult:
    """Best-effort clean output-tail payload for `inspect`."""

    output_text_tail: str | None
    note: str | None


CommandRunner: TypeAlias = Callable[
    [Sequence[str], Path, Path, Path, float],
    CommandResult,
]
ProgressWriter: TypeAlias = Callable[[str], None]
_ModelT = TypeVar("_ModelT", bound="_StrictModel")


def main(
    argv: list[str] | None = None,
    *,
    run_command: CommandRunner | None = None,
) -> int:
    """Run the interactive CAO full-pipeline demo CLI.

    Parameters
    ----------
    argv:
        Optional CLI arguments. Defaults to `sys.argv[1:]`.
    run_command:
        Optional subprocess runner override used by tests.

    Returns
    -------
    int
        Process exit code.
    """

    parser = _build_parser()
    args = parser.parse_args(argv or sys.argv[1:])
    invocation = _resolve_demo_invocation(args)
    paths = invocation.paths
    env = invocation.env
    runner = run_command or run_subprocess_command

    try:
        if args.command == "start":
            payload = start_demo(
                paths=paths,
                env=env,
                agent_name=str(args.agent_name),
                run_command=runner,
            )
            if bool(getattr(args, "json", False)):
                _print_json(payload)
            else:
                print(_render_start_output(payload=payload))
            return 0
        if args.command == "send-turn":
            turn = send_turn(
                paths=paths,
                env=env,
                prompt=_resolve_prompt_text(args),
                run_command=runner,
            )
            _print_json(turn.model_dump(mode="json"))
            return 0
        if args.command == "inspect":
            inspect_demo(
                paths=paths,
                as_json=bool(args.json),
                output_text_tail_chars=getattr(args, "with_output_text", None),
            )
            return 0
        if args.command == "verify":
            report = verify_demo(paths=paths)
            _print_json(report.model_dump(mode="json"))
            return 0
        if args.command == "stop":
            payload = stop_demo(
                paths=paths,
                env=env,
                run_command=runner,
            )
            _print_json(payload)
            return 0
    except DemoWorkflowError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    parser.print_help()
    return 1


def start_demo(
    *,
    paths: DemoPaths,
    env: DemoEnvironment,
    agent_name: str,
    run_command: CommandRunner,
) -> dict[str, object]:
    """Start or replace the interactive CAO demo session."""

    _emit_startup_progress("Preparing the interactive demo workspace.")
    _require_tool("pixi")
    _require_tool("tmux")
    _ensure_workspace(paths)
    if env.provision_worktree:
        _emit_startup_progress("Provisioning the default demo git worktree.")
        _provision_default_worktree(paths=paths, env=env, run_command=run_command)

    normalized_identity = normalize_agent_identity_name(agent_name)
    _emit_startup_progress("Resetting any previous interactive demo session state.")
    replaced_agent_identity = _reset_demo_startup_state(
        paths=paths,
        env=env,
        agent_identity=normalized_identity.canonical_name,
        run_command=run_command,
    )

    _reset_turn_artifacts(paths)
    _emit_startup_progress("Writing the fixed-loopback CAO launcher configuration.")
    _write_launcher_config(paths.launcher_config_path, env=env, runtime_root=paths.runtime_root)
    _emit_startup_progress(f"Ensuring local CAO availability at {FIXED_CAO_BASE_URL}.")
    _ensure_cao_server(paths=paths, env=env, run_command=run_command)

    _emit_startup_progress("Building the Claude runtime brain for the interactive demo.")
    build_payload = _build_brain(paths=paths, env=env, run_command=run_command)
    _emit_startup_progress("Launching the interactive Claude session and waiting for readiness.")
    runtime_payload = _start_runtime_session(
        paths=paths,
        env=env,
        agent_identity=normalized_identity.canonical_name,
        brain_manifest_path=Path(str(build_payload["manifest_path"])),
        run_command=run_command,
    )

    session_manifest_path = Path(str(runtime_payload["session_manifest"])).expanduser().resolve()
    manifest_payload = _load_json_file(session_manifest_path, context="session manifest")
    cao_payload = _require_mapping(
        manifest_payload.get("cao"),
        context=f"session manifest `{session_manifest_path}` missing `cao` payload",
    )
    session_name = _require_non_empty_string(
        cao_payload.get("session_name"),
        context="session manifest missing cao.session_name",
    )
    terminal_id = _require_non_empty_string(
        cao_payload.get("terminal_id"),
        context="session manifest missing cao.terminal_id",
    )

    state = DemoState(
        active=True,
        agent_identity=_require_non_empty_string(
            runtime_payload.get("agent_identity"),
            context="start-session output missing agent_identity",
        ),
        session_manifest=str(session_manifest_path),
        session_name=session_name,
        tmux_target=session_name,
        terminal_id=terminal_id,
        terminal_log_path=_terminal_log_path(
            terminal_id,
            launcher_home_dir=env.launcher_home_dir,
        ),
        runtime_root=str(paths.runtime_root),
        workspace_dir=str(paths.workspace_root),
        brain_home=str(Path(str(build_payload["home_path"])).expanduser().resolve()),
        brain_manifest=str(Path(str(build_payload["manifest_path"])).expanduser().resolve()),
        cao_base_url=FIXED_CAO_BASE_URL,
        cao_profile_store=str(_cao_profile_store(env.launcher_home_dir)),
        launcher_config_path=str(paths.launcher_config_path),
        updated_at=_utc_now(),
        turn_count=0,
    )
    save_demo_state(paths.state_path, state)
    _write_current_run_root(env.current_run_root_path, paths.workspace_root)
    payload: dict[str, object] = {
        "state": state.model_dump(mode="json"),
        "replaced_previous_agent_identity": replaced_agent_identity,
        "warnings": list(normalized_identity.warnings),
    }
    return payload


def send_turn(
    *,
    paths: DemoPaths,
    env: DemoEnvironment,
    prompt: str,
    run_command: CommandRunner,
) -> TurnRecord:
    """Send one prompt turn through the persisted interactive session."""

    state = require_active_state(paths.state_path)
    _ensure_workspace(paths)
    turn_index = _next_turn_index(paths)
    started_at_utc = _utc_now()
    stdout_path = paths.turns_dir / f"turn-{turn_index:03d}.events.jsonl"
    stderr_path = paths.turns_dir / f"turn-{turn_index:03d}.stderr.log"

    result = run_command(
        _runtime_cli_command(
            [
                "send-prompt",
                "--agent-def-dir",
                str(env.agent_def_dir),
                "--agent-identity",
                state.agent_identity,
                "--prompt",
                prompt,
            ]
        ),
        env.repo_root,
        stdout_path,
        stderr_path,
        env.timeout_seconds,
    )
    completed_at_utc = _utc_now()
    events = _parse_events(stdout=result.stdout)
    response_text = _extract_done_message(events)
    turn = TurnRecord(
        turn_index=turn_index,
        agent_identity=state.agent_identity,
        prompt=prompt,
        started_at_utc=started_at_utc,
        completed_at_utc=completed_at_utc,
        exit_status=result.returncode,
        response_text=response_text,
        events=events,
        stdout_path=str(stdout_path),
        stderr_path=str(stderr_path),
    )
    _write_json_file(paths.turns_dir / f"turn-{turn_index:03d}.json", turn.model_dump(mode="json"))

    if result.returncode != 0:
        raise DemoWorkflowError(
            f"send-turn failed via `brain_launch_runtime send-prompt` (see `{stderr_path}`)"
        )
    if not response_text.strip():
        raise DemoWorkflowError(EMPTY_RESPONSE_ERROR)

    updated_state = state.model_copy(
        update={
            "updated_at": completed_at_utc,
            "turn_count": turn_index,
        }
    )
    save_demo_state(paths.state_path, updated_state)
    return turn


def inspect_demo(
    *,
    paths: DemoPaths,
    as_json: bool,
    output_text_tail_chars: int | None = None,
) -> None:
    """Render stored inspection metadata for the active or latest session."""

    state = load_demo_state(paths.state_path)
    if state is None:
        raise DemoWorkflowError(
            "No interactive demo state was found. Run `start` before `inspect`."
        )

    terminal_log_path = _resolved_terminal_log_path_for_state(state)
    client = CaoRestClient(
        state.cao_base_url,
        timeout_seconds=DEFAULT_LIVE_CAO_TIMEOUT_SECONDS,
    )
    payload: dict[str, object] = {
        "active": state.active,
        "session_status": "active" if state.active else "inactive",
        "agent_identity": state.agent_identity,
        "session_name": state.session_name,
        "claude_code_state": _best_effort_claude_code_state(
            terminal_id=state.terminal_id,
            client=client,
        ),
        "session_manifest": state.session_manifest,
        "tmux_target": state.tmux_target,
        "tmux_attach_command": f"tmux attach -t {state.tmux_target}",
        "terminal_id": state.terminal_id,
        "terminal_log_path": terminal_log_path,
        "terminal_log_tail_command": f"tail -f {terminal_log_path}",
        "workspace_dir": state.workspace_dir,
        "runtime_root": state.runtime_root,
        "updated_at": state.updated_at,
    }
    if output_text_tail_chars is not None:
        output_text_tail = _best_effort_output_text_tail(
            terminal_id=state.terminal_id,
            output_text_tail_chars=output_text_tail_chars,
            client=client,
        )
        payload["output_text_tail_chars_requested"] = output_text_tail_chars
        payload["output_text_tail"] = output_text_tail.output_text_tail
        if output_text_tail.note is not None:
            payload["output_text_tail_note"] = output_text_tail.note
    if as_json:
        _print_json(payload)
        return

    print(_render_human_inspect_output(payload=payload))


def verify_demo(*, paths: DemoPaths) -> VerificationReport:
    """Generate a verification report from persisted turn artifacts."""

    state = load_demo_state(paths.state_path)
    if state is None:
        raise DemoWorkflowError("No interactive demo state was found. Run `start` before `verify`.")

    turn_records = load_turn_records(paths.turns_dir)
    if len(turn_records) < 2:
        raise DemoWorkflowError(
            "Verification requires at least two recorded turns in the current workspace."
        )

    agent_identities = {record.agent_identity for record in turn_records}
    if len(agent_identities) != 1:
        raise DemoWorkflowError(
            "Verification expected exactly one reused agent_identity across recorded turns."
        )

    summaries: list[VerificationTurnSummary] = []
    for record in turn_records:
        if record.exit_status != 0:
            raise DemoWorkflowError(
                f"Turn {record.turn_index} exited non-zero ({record.exit_status})."
            )
        if not record.response_text.strip():
            raise DemoWorkflowError(f"Turn {record.turn_index} has an empty response_text.")
        summaries.append(
            VerificationTurnSummary(
                turn_index=record.turn_index,
                agent_identity=record.agent_identity,
                exit_status=record.exit_status,
                response_text=record.response_text,
            )
        )

    report = VerificationReport(
        status="ok",
        backend="cao_rest",
        tool=DEFAULT_TOOL_NAME,
        cao_base_url=state.cao_base_url,
        agent_identity=state.agent_identity,
        unique_agent_identity_count=len(agent_identities),
        turn_count=len(summaries),
        turns=summaries,
        session_manifest=state.session_manifest,
        workspace_dir=state.workspace_dir,
        tmux_target=state.tmux_target,
        terminal_id=state.terminal_id,
        terminal_log_path=_resolved_terminal_log_path_for_state(state),
        generated_at_utc=_utc_now(),
    )
    _write_json_file(paths.report_path, report.model_dump(mode="json"))
    return report


def stop_demo(
    *,
    paths: DemoPaths,
    env: DemoEnvironment,
    run_command: CommandRunner,
) -> dict[str, object]:
    """Stop the active interactive demo session and mark local state inactive."""

    state = load_demo_state(paths.state_path)
    if state is None:
        raise DemoWorkflowError("No interactive demo state was found. Run `start` before `stop`.")
    if not state.active:
        raise DemoWorkflowError("Interactive demo state is already inactive.")

    result = _stop_remote_session(
        paths=paths,
        env=env,
        agent_identity=state.agent_identity,
        run_command=run_command,
        tolerate_stale=True,
        log_prefix="stop",
    )
    inactive_state = state.model_copy(update={"active": False, "updated_at": _utc_now()})
    save_demo_state(paths.state_path, inactive_state)
    return {
        "state": inactive_state.model_dump(mode="json"),
        "stop_result": {
            "returncode": result.returncode,
            "stdout_path": str(result.stdout_path),
            "stderr_path": str(result.stderr_path),
            "stale_session_tolerated": bool(result.returncode != 0),
        },
    }


def load_demo_state(path: Path) -> DemoState | None:
    """Load demo state from disk when it exists."""

    if not path.is_file():
        return None
    payload = _load_json_file(path, context="demo state")
    return _validate_model(DemoState, payload, source=str(path))


def save_demo_state(path: Path, state: DemoState) -> None:
    """Persist demo state to disk."""

    _write_json_file(path, state.model_dump(mode="json"))


def load_turn_records(turns_dir: Path) -> list[TurnRecord]:
    """Load all persisted turn records sorted by turn index."""

    if not turns_dir.exists():
        return []

    records: list[TurnRecord] = []
    for path in sorted(turns_dir.glob("turn-*.json")):
        payload = _load_json_file(path, context="turn record")
        records.append(_validate_model(TurnRecord, payload, source=str(path)))
    return sorted(records, key=lambda record: record.turn_index)


def require_active_state(path: Path) -> DemoState:
    """Return the active demo state or raise an actionable workflow error."""

    state = load_demo_state(path)
    if state is None or not state.active:
        raise DemoWorkflowError(
            "No active interactive session exists. Run `start` before `send-turn`."
        )
    return state


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


def _build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser for the interactive demo."""

    parser = argparse.ArgumentParser(description="Interactive CAO full-pipeline demo commands.")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repository root used as command cwd and as the base for omitted defaults.",
    )
    parser.add_argument(
        "--workspace-root",
        type=Path,
        default=None,
        help=(
            "Workspace root for state, turns, reports, runtime files, and launcher config. "
            "Defaults to the current per-run demo root."
        ),
    )
    parser.add_argument(
        "--agent-def-dir",
        type=Path,
        default=None,
        help="Agent definition root for runtime commands.",
    )
    parser.add_argument(
        "--launcher-home-dir",
        type=Path,
        default=None,
        help=(
            "Home directory used by the CAO launcher-managed profile store. "
            "Defaults to the resolved workspace root."
        ),
    )
    parser.add_argument(
        "--workdir",
        type=Path,
        default=None,
        help=(
            "Working directory passed to `brain_launch_runtime start-session`. "
            "Defaults to a provisioned `<launcher-home>/wktree` git worktree."
        ),
    )
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Assume yes for demo confirmation prompts such as CAO replacement.",
    )
    parser.add_argument(
        "--role-name",
        default=DEFAULT_ROLE_NAME,
        help="Role name passed to `brain_launch_runtime start-session`.",
    )
    parser.add_argument(
        "--config-profile",
        default=DEFAULT_CONFIG_PROFILE,
        help="Config profile passed to `build-brain`.",
    )
    parser.add_argument(
        "--credential-profile",
        default=DEFAULT_CREDENTIAL_PROFILE,
        help="Credential profile passed to `build-brain`.",
    )
    parser.add_argument(
        "--skill",
        dest="skills",
        action="append",
        default=[],
        help="Repeatable build-brain skill selection. Defaults to openspec-apply-change.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="Per-command subprocess timeout budget.",
    )

    subparsers = parser.add_subparsers(dest="command")

    start = subparsers.add_parser("start", help="Start or replace the interactive session")
    start.add_argument(
        "--agent-name",
        default=DEFAULT_AGENT_NAME,
        help="Operator-facing agent identity name (canonicalized to AGENTSYS-...).",
    )
    start.add_argument("--json", action="store_true", help="Print machine-readable JSON")

    send_turn_parser = subparsers.add_parser(
        "send-turn", help="Send one prompt to the active interactive session"
    )
    send_turn_group = send_turn_parser.add_mutually_exclusive_group(required=True)
    send_turn_group.add_argument("--prompt", help="Inline prompt text")
    send_turn_group.add_argument("--prompt-file", type=Path, help="Path to prompt text file")

    inspect = subparsers.add_parser("inspect", help="Show tmux/log inspection commands")
    inspect.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    inspect.add_argument(
        "--with-output-text",
        type=_positive_int,
        metavar="NUM_TAIL_CHARS",
        help=(
            "Include the last NUM_TAIL_CHARS of clean projected Claude dialog text "
            "from the live CAO terminal."
        ),
    )

    subparsers.add_parser("verify", help="Generate a verification report from recorded turns")
    subparsers.add_parser("stop", help="Stop the active interactive session")
    return parser


def _resolve_demo_invocation(args: argparse.Namespace) -> DemoInvocation:
    """Resolve parser arguments into concrete demo paths and environment values."""

    repo_root = _resolve_repo_root(getattr(args, "repo_root", None))
    demo_base_root = repo_root / "tmp" / "demo" / DEFAULT_DEMO_ROOT_DIRNAME
    current_run_root_path = demo_base_root / CURRENT_RUN_ROOT_FILENAME
    workspace_root = _resolve_workspace_root(
        command=str(args.command),
        demo_base_root=demo_base_root,
        current_run_root_path=current_run_root_path,
        workspace_root=getattr(args, "workspace_root", None),
    )

    launcher_home_dir_arg = getattr(args, "launcher_home_dir", None)
    launcher_home_dir = (
        launcher_home_dir_arg.expanduser().resolve()
        if isinstance(launcher_home_dir_arg, Path)
        else workspace_root
    )

    workdir_arg = getattr(args, "workdir", None)
    provision_worktree = workdir_arg is None
    workdir = (
        workdir_arg.expanduser().resolve()
        if isinstance(workdir_arg, Path)
        else launcher_home_dir / DEFAULT_WORKTREE_DIRNAME
    )

    agent_def_dir_arg = getattr(args, "agent_def_dir", None)
    agent_def_dir = (
        agent_def_dir_arg.expanduser().resolve()
        if isinstance(agent_def_dir_arg, Path)
        else repo_root / "tests" / "fixtures" / "agents"
    )

    env = DemoEnvironment(
        repo_root=repo_root,
        demo_base_root=demo_base_root,
        current_run_root_path=current_run_root_path,
        agent_def_dir=agent_def_dir,
        launcher_home_dir=launcher_home_dir,
        workdir=workdir,
        role_name=str(args.role_name),
        config_profile=str(args.config_profile),
        credential_profile=str(args.credential_profile),
        skills=tuple(args.skills or DEFAULT_SKILLS),
        timeout_seconds=float(args.timeout_seconds),
        yes_to_all=bool(args.yes),
        provision_worktree=provision_worktree,
    )
    return DemoInvocation(paths=DemoPaths.from_workspace_root(workspace_root), env=env)


def _resolve_repo_root(repo_root: Path | None) -> Path:
    """Resolve the effective repository root for demo defaults."""

    if repo_root is not None:
        return repo_root.expanduser().resolve()
    return Path(__file__).resolve().parents[3]


def _resolve_workspace_root(
    *,
    command: str,
    demo_base_root: Path,
    current_run_root_path: Path,
    workspace_root: Path | None,
) -> Path:
    """Resolve the effective workspace root for the requested command."""

    if workspace_root is not None:
        return workspace_root.expanduser().resolve()
    if command == "start":
        return demo_base_root / _run_timestamp_slug()

    resolved = _read_current_run_root(current_run_root_path)
    if resolved is not None:
        return resolved

    latest_run_root = _latest_demo_run_root(demo_base_root)
    if latest_run_root is not None:
        return latest_run_root

    raise DemoWorkflowError(
        "No interactive demo workspace was found. Run `start` before this command "
        "or provide `--workspace-root`."
    )


def _read_current_run_root(path: Path) -> Path | None:
    """Read the recorded current-run workspace root when available."""

    if not path.is_file():
        return None
    raw_value = path.read_text(encoding="utf-8").strip()
    if not raw_value:
        return None
    resolved = Path(raw_value).expanduser().resolve()
    if not resolved.exists():
        return None
    return resolved


def _write_current_run_root(path: Path, workspace_root: Path) -> None:
    """Persist the latest workspace root used by wrapper-driven follow-up commands."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{workspace_root}\n", encoding="utf-8")


def _latest_demo_run_root(demo_base_root: Path) -> Path | None:
    """Return the newest demo run directory under the default demo root."""

    if not demo_base_root.exists():
        return None
    candidates = sorted(
        (
            path
            for path in demo_base_root.iterdir()
            if path.is_dir() and path.name != DEFAULT_WORKTREE_DIRNAME
        ),
        key=lambda path: path.name,
        reverse=True,
    )
    return candidates[0] if candidates else None


def _run_timestamp_slug() -> str:
    """Return a filesystem-safe UTC slug for per-run demo roots."""

    return datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%fZ")


def _resolve_prompt_text(args: argparse.Namespace) -> str:
    """Resolve prompt text from inline or file-based CLI inputs."""

    if args.prompt is not None:
        prompt = str(args.prompt)
    else:
        prompt = args.prompt_file.read_text(encoding="utf-8")
    if not prompt.strip():
        raise DemoWorkflowError("Prompt text must not be empty.")
    return prompt


def _ensure_workspace(paths: DemoPaths) -> None:
    """Create the stable demo workspace directories."""

    paths.workspace_root.mkdir(parents=True, exist_ok=True)
    paths.runtime_root.mkdir(parents=True, exist_ok=True)
    paths.logs_dir.mkdir(parents=True, exist_ok=True)
    paths.turns_dir.mkdir(parents=True, exist_ok=True)


def _reset_turn_artifacts(paths: DemoPaths) -> None:
    """Remove turn/report artifacts when starting a replacement session."""

    if paths.turns_dir.exists():
        shutil.rmtree(paths.turns_dir)
    paths.turns_dir.mkdir(parents=True, exist_ok=True)
    if paths.report_path.exists():
        paths.report_path.unlink()


def _provision_default_worktree(
    *,
    paths: DemoPaths,
    env: DemoEnvironment,
    run_command: CommandRunner,
) -> None:
    """Create the default git worktree used as the demo session workdir."""

    if env.workdir.exists():
        git_dir = env.workdir / ".git"
        if git_dir.exists():
            return
        raise DemoWorkflowError(
            f"Default demo workdir already exists and is not a git worktree: `{env.workdir}`."
        )

    env.workdir.parent.mkdir(parents=True, exist_ok=True)
    result = run_command(
        ["git", "worktree", "add", "--detach", str(env.workdir), "HEAD"],
        env.repo_root,
        paths.logs_dir / "provision-worktree.stdout",
        paths.logs_dir / "provision-worktree.stderr",
        env.timeout_seconds,
    )
    if result.returncode != 0:
        raise DemoWorkflowError(
            f"Failed to provision the default demo git worktree (see `{result.stderr_path}`)."
        )


def _reset_demo_startup_state(
    *,
    paths: DemoPaths,
    env: DemoEnvironment,
    agent_identity: str,
    run_command: CommandRunner,
) -> str | None:
    """Reset prior tutorial state so startup behaves like a fresh run."""

    previous = _load_previous_demo_state(env.current_run_root_path)
    replaced_agent_identity = (
        previous.agent_identity if previous is not None and previous.active else None
    )

    _stop_remote_session(
        paths=paths,
        env=env,
        agent_identity=agent_identity,
        run_command=run_command,
        tolerate_stale=True,
        log_prefix="replacement-stop",
    )
    _kill_tmux_session(
        paths=paths,
        env=env,
        session_name=agent_identity,
        run_command=run_command,
    )

    if previous is not None:
        previous_paths = DemoPaths.from_workspace_root(Path(previous.workspace_dir))
        _reset_turn_artifacts(previous_paths)
        _mark_state_inactive(previous_paths.state_path, previous)

    if paths.state_path.exists():
        current_state = load_demo_state(paths.state_path)
        if current_state is not None:
            _mark_state_inactive(paths.state_path, current_state)

    return replaced_agent_identity


def _load_previous_demo_state(current_run_root_path: Path) -> DemoState | None:
    """Load the previously recorded demo state from the current-run marker."""

    previous_workspace_root = _read_current_run_root(current_run_root_path)
    if previous_workspace_root is None:
        return None
    return load_demo_state(DemoPaths.from_workspace_root(previous_workspace_root).state_path)


def _mark_state_inactive(path: Path, state: DemoState) -> None:
    """Persist an inactive copy of demo state after cleanup or aborted startup."""

    if state.active:
        save_demo_state(path, state.model_copy(update={"active": False, "updated_at": _utc_now()}))


def _kill_tmux_session(
    *,
    paths: DemoPaths,
    env: DemoEnvironment,
    session_name: str,
    run_command: CommandRunner,
) -> None:
    """Best-effort kill of a leftover tmux session for the canonical demo identity."""

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


def _next_turn_index(paths: DemoPaths) -> int:
    """Return the next sequential turn index for the workspace."""

    existing = load_turn_records(paths.turns_dir)
    if not existing:
        return 1
    return max(record.turn_index for record in existing) + 1


def _write_launcher_config(
    path: Path,
    *,
    env: DemoEnvironment,
    runtime_root: Path,
) -> None:
    """Write the fixed loopback CAO launcher config file."""

    env.launcher_home_dir.mkdir(parents=True, exist_ok=True)
    content = "\n".join(
        [
            f'base_url = "{FIXED_CAO_BASE_URL}"',
            f'runtime_root = "{runtime_root}"',
            f'home_dir = "{env.launcher_home_dir}"',
            'proxy_policy = "clear"',
            "startup_timeout_seconds = 15",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _ensure_cao_server(
    *,
    paths: DemoPaths,
    env: DemoEnvironment,
    run_command: CommandRunner,
) -> None:
    """Ensure the fixed loopback CAO server is fresh for this demo run."""

    status_payload = _launcher_status_payload(paths=paths, env=env, run_command=run_command)
    if bool(status_payload.get("healthy")):
        if not _launcher_status_is_verified_cao_server(status_payload):
            service = status_payload.get("service")
            raise DemoWorkflowError(
                "The fixed loopback target is already occupied by a process that did not "
                "verify as `cao-server` "
                f"(service={service!r}). Stop that process and retry."
            )

        if not env.yes_to_all and not _prompt_yes_no(
            f"A verified local `cao-server` is already running at {FIXED_CAO_BASE_URL}. "
            "Replace it for this demo run? [y/N]: "
        ):
            raise DemoWorkflowError(
                "Startup aborted because the existing verified local `cao-server` was not replaced."
            )
        _replace_existing_cao_server(paths=paths, env=env, run_command=run_command)
    else:
        if _loopback_port_is_listening(FIXED_CAO_BASE_URL):
            detail = status_payload.get("error")
            raise DemoWorkflowError(
                "The fixed loopback target is occupied by a process that could not be "
                "safely verified as `cao-server`" + (f": {detail}" if detail else ".")
            )
        if shutil.which("cao-server") is None:
            raise DemoWorkflowError(
                "CAO server is unavailable at the fixed loopback target and "
                "`cao-server` is not available on PATH."
            )

    start_payload = _launcher_start_payload(
        paths=paths,
        env=env,
        run_command=run_command,
        log_prefix="cao-start",
    )
    if bool(start_payload.get("reused_existing_process")):
        raise DemoWorkflowError(
            "Interactive demo startup refused to reuse an existing fixed-port `cao-server`; "
            "replace the server and retry."
        )


def _launcher_status_payload(
    *,
    paths: DemoPaths,
    env: DemoEnvironment,
    run_command: CommandRunner,
) -> dict[str, object]:
    """Run launcher `status` and return its parsed JSON payload."""

    result = run_command(
        _launcher_cli_command(["status", "--config", str(paths.launcher_config_path)]),
        env.repo_root,
        paths.logs_dir / "cao-status.stdout",
        paths.logs_dir / "cao-status.stderr",
        env.timeout_seconds,
    )
    return _parse_command_json_output(
        result,
        context="CAO launcher status output",
        allow_stderr_json=True,
    )


def _launcher_start_payload(
    *,
    paths: DemoPaths,
    env: DemoEnvironment,
    run_command: CommandRunner,
    log_prefix: str,
) -> dict[str, object]:
    """Run launcher `start` and require a healthy replacement server."""

    result = run_command(
        _launcher_cli_command(["start", "--config", str(paths.launcher_config_path)]),
        env.repo_root,
        paths.logs_dir / f"{log_prefix}.stdout",
        paths.logs_dir / f"{log_prefix}.stderr",
        env.timeout_seconds,
    )
    if result.returncode != 0:
        raise DemoWorkflowError(
            "Failed to start the fixed loopback `cao-server` via launcher "
            f"(see `{result.stderr_path}`)."
        )
    return _parse_json_output(result.stdout, context="CAO launcher start output")


def _launcher_status_is_verified_cao_server(status_payload: dict[str, object]) -> bool:
    """Return whether launcher status verified a healthy local `cao-server`."""

    if not bool(status_payload.get("healthy")):
        return False
    service = status_payload.get("service")
    return isinstance(service, str) and service.strip() == DEFAULT_CAO_SERVICE_NAME


def _parse_command_json_output(
    result: CommandResult,
    *,
    context: str,
    allow_stderr_json: bool = False,
) -> dict[str, object]:
    """Parse a command result as JSON from stdout or, optionally, stderr."""

    if result.stdout.strip():
        return _parse_json_output(result.stdout, context=context)
    if allow_stderr_json and result.stderr.strip():
        return _parse_json_output(result.stderr, context=context)
    raise DemoWorkflowError(f"Missing JSON in {context}.")


def _prompt_yes_no(prompt: str) -> bool:
    """Prompt for a yes/no answer and treat all non-yes answers as negative."""

    try:
        response = input(prompt)
    except EOFError:
        return False
    return response.strip().lower() in {"y", "yes"}


def _replace_existing_cao_server(
    *,
    paths: DemoPaths,
    env: DemoEnvironment,
    run_command: CommandRunner,
) -> None:
    """Stop the currently verified loopback `cao-server` before replacement."""

    if _stop_cao_server_with_known_configs(paths=paths, env=env, run_command=run_command):
        return

    candidate_pids = _find_listening_pids_for_port(_fixed_cao_port())
    if len(candidate_pids) != 1:
        raise DemoWorkflowError(
            "Refusing to replace the fixed loopback `cao-server` because the listening "
            "process could not be uniquely identified."
        )

    pid = candidate_pids[0]
    cmdline = _read_process_cmdline(pid)
    if cmdline is None or not _looks_like_cao_server_cmdline(cmdline):
        raise DemoWorkflowError(
            "Refusing to replace the fixed loopback service because the listening "
            f"process did not verify as `cao-server` (pid={pid})."
        )

    _terminate_process(pid)
    if _loopback_port_is_listening(FIXED_CAO_BASE_URL):
        raise DemoWorkflowError(
            "Failed to clear the fixed loopback `cao-server` before replacement."
        )


def _stop_cao_server_with_known_configs(
    *,
    paths: DemoPaths,
    env: DemoEnvironment,
    run_command: CommandRunner,
) -> bool:
    """Try launcher-managed stop using the current and previously recorded demo configs."""

    config_paths = _known_launcher_config_paths(paths=paths, env=env)
    for index, config_path in enumerate(config_paths, start=1):
        result = run_command(
            _launcher_cli_command(["stop", "--config", str(config_path)]),
            env.repo_root,
            paths.logs_dir / f"cao-stop-{index}.stdout",
            paths.logs_dir / f"cao-stop-{index}.stderr",
            env.timeout_seconds,
        )
        stop_payload = _parse_command_json_output(
            result,
            context="CAO launcher stop output",
            allow_stderr_json=True,
        )
        if bool(stop_payload.get("stopped")) and not _loopback_port_is_listening(
            FIXED_CAO_BASE_URL
        ):
            return True
        if not _loopback_port_is_listening(FIXED_CAO_BASE_URL):
            return True
    return False


def _known_launcher_config_paths(*, paths: DemoPaths, env: DemoEnvironment) -> list[Path]:
    """Return launcher config candidates that may own the current fixed-port server."""

    candidates: list[Path] = [paths.launcher_config_path]
    previous_workspace_root = _read_current_run_root(env.current_run_root_path)
    if previous_workspace_root is not None:
        candidates.append(
            DemoPaths.from_workspace_root(previous_workspace_root).launcher_config_path
        )

    if env.demo_base_root.exists():
        for candidate_dir in sorted(env.demo_base_root.iterdir(), reverse=True):
            if not candidate_dir.is_dir():
                continue
            config_path = candidate_dir / "cao-server-launcher.toml"
            if config_path.exists():
                candidates.append(config_path)

    unique_candidates: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.expanduser().resolve()
        if resolved in seen or not resolved.exists():
            continue
        seen.add(resolved)
        unique_candidates.append(resolved)
    return unique_candidates


def _loopback_port_is_listening(_: str) -> bool:
    """Return whether the fixed loopback TCP port currently has a listener."""

    parsed = socket.getaddrinfo("127.0.0.1", _fixed_cao_port(), type=socket.SOCK_STREAM)
    for family, socktype, proto, _, sockaddr in parsed:
        try:
            with socket.socket(family, socktype, proto) as sock:
                sock.settimeout(0.5)
                if sock.connect_ex(sockaddr) == 0:
                    return True
        except OSError:
            continue
    return False


def _fixed_cao_port() -> int:
    """Return the TCP port used by the fixed loopback CAO base URL."""

    return int(FIXED_CAO_BASE_URL.rsplit(":", maxsplit=1)[1])


def _find_listening_pids_for_port(port: int) -> list[int]:
    """Return process identifiers listening on the given TCP port."""

    inodes = _list_listening_socket_inodes(port)
    if not inodes:
        return []
    return sorted(_find_pids_for_socket_inodes(inodes))


def _list_listening_socket_inodes(port: int) -> set[str]:
    """Collect listening TCP socket inodes for the provided port from `/proc`."""

    proc_paths = (Path("/proc/net/tcp"), Path("/proc/net/tcp6"))
    target_port = f"{port:04X}"
    inodes: set[str] = set()
    for proc_path in proc_paths:
        if not proc_path.exists():
            continue
        for raw_line in proc_path.read_text(encoding="utf-8").splitlines()[1:]:
            parts = raw_line.split()
            if len(parts) < 10:
                continue
            local_address = parts[1]
            state = parts[3]
            inode = parts[9]
            if ":" not in local_address:
                continue
            _, port_hex = local_address.rsplit(":", maxsplit=1)
            if state == PORT_LISTEN_STATE and port_hex.upper() == target_port:
                inodes.add(inode)
    return inodes


def _find_pids_for_socket_inodes(inodes: set[str]) -> set[int]:
    """Map socket inodes back to owning process identifiers."""

    matched_pids: set[int] = set()
    if not inodes:
        return matched_pids

    for proc_dir in Path("/proc").iterdir():
        if not proc_dir.name.isdigit():
            continue
        fd_dir = proc_dir / "fd"
        if not fd_dir.exists():
            continue
        for fd_path in fd_dir.iterdir():
            try:
                target = os.readlink(fd_path)
            except OSError:
                continue
            if not target.startswith("socket:["):
                continue
            inode = target.removeprefix("socket:[").removesuffix("]")
            if inode in inodes:
                matched_pids.add(int(proc_dir.name))
                break
    return matched_pids


def _read_process_cmdline(pid: int) -> str | None:
    """Read `/proc/<pid>/cmdline` and collapse it into one human-friendly string."""

    cmdline_path = Path("/proc") / str(pid) / "cmdline"
    if not cmdline_path.exists():
        return None
    try:
        raw = cmdline_path.read_bytes()
    except OSError:
        return None
    if not raw:
        return ""
    return " ".join(token for token in raw.decode("utf-8", errors="replace").split("\x00") if token)


def _looks_like_cao_server_cmdline(cmdline: str) -> bool:
    """Return whether a process command line looks like `cao-server`."""

    lowered = cmdline.lower()
    return "cao-server" in lowered or "cli_agent_orchestrator" in lowered


def _terminate_process(pid: int) -> None:
    """Terminate a process with SIGTERM and SIGKILL fallback."""

    try:
        os.kill(pid, signal.SIGTERM)
    except OSError as exc:
        raise DemoWorkflowError(f"Failed to terminate pid {pid}: {exc}.") from exc

    if _wait_for_process_exit(pid, timeout_seconds=10.0):
        return

    try:
        os.kill(pid, signal.SIGKILL)
    except OSError as exc:
        raise DemoWorkflowError(f"Failed to SIGKILL pid {pid}: {exc}.") from exc

    if not _wait_for_process_exit(pid, timeout_seconds=2.0):
        raise DemoWorkflowError(f"Process {pid} did not exit after replacement shutdown.")


def _wait_for_process_exit(pid: int, *, timeout_seconds: float) -> bool:
    """Wait until a process exits or the timeout budget is exhausted."""

    deadline = time.monotonic() + max(timeout_seconds, 0.0)
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        except PermissionError:
            return False
        time.sleep(0.1)

    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    except PermissionError:
        return False
    return False


def _build_brain(
    *,
    paths: DemoPaths,
    env: DemoEnvironment,
    run_command: CommandRunner,
) -> dict[str, object]:
    """Build the Claude brain manifest used by the interactive demo."""

    command = _runtime_cli_command(
        [
            "build-brain",
            "--agent-def-dir",
            str(env.agent_def_dir),
            "--runtime-root",
            str(paths.runtime_root),
            "--tool",
            DEFAULT_TOOL_NAME,
            *sum([["--skill", skill] for skill in env.skills], []),
            "--config-profile",
            env.config_profile,
            "--cred-profile",
            env.credential_profile,
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
                "Still waiting for the interactive Claude session to launch and become "
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
                "--agent-def-dir",
                str(env.agent_def_dir),
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
    """Build a `brain_launch_runtime` CLI subprocess command."""

    return ["pixi", "run", "python", "-m", "gig_agents.agents.brain_launch_runtime", *args]


def _launcher_cli_command(args: list[str]) -> list[str]:
    """Build a `cao_server_launcher` CLI subprocess command."""

    return ["pixi", "run", "python", "-m", "gig_agents.cao.tools.cao_server_launcher", *args]


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


def _best_effort_claude_code_state(*, terminal_id: str, client: CaoRestClient) -> str:
    """Return live CAO terminal status or `unknown` when lookup fails."""

    try:
        terminal = client.get_terminal(terminal_id)
    except Exception:
        return UNKNOWN_CLAUDE_CODE_STATE
    if terminal.status is None:
        return UNKNOWN_CLAUDE_CODE_STATE
    return terminal.status.value


def _best_effort_output_text_tail(
    *,
    terminal_id: str,
    output_text_tail_chars: int,
    client: CaoRestClient,
) -> OutputTextTailResult:
    """Return a clean projected Claude dialog tail for live inspection."""

    try:
        terminal_output = client.get_terminal_output(terminal_id, mode="full")
    except Exception as exc:
        return OutputTextTailResult(
            output_text_tail=None,
            note=(
                "clean projected Claude dialog tail unavailable: "
                f"live CAO output could not be fetched ({exc})"
            ),
        )

    try:
        parsed_snapshot = ClaudeCodeShadowParser().parse_snapshot(
            terminal_output.output,
            baseline_pos=0,
        )
    except Exception as exc:
        return OutputTextTailResult(
            output_text_tail=None,
            note=(f"clean projected Claude dialog tail unavailable: projection failed ({exc})"),
        )

    if parsed_snapshot.surface_assessment.availability != "supported":
        return OutputTextTailResult(
            output_text_tail=None,
            note=(
                "clean projected Claude dialog tail unavailable: "
                "live output did not match a supported Claude surface"
            ),
        )

    dialog_text = parsed_snapshot.dialog_projection.dialog_text
    return OutputTextTailResult(
        output_text_tail=dialog_text[-output_text_tail_chars:],
        note=None,
    )


def _render_human_inspect_output(*, payload: dict[str, object]) -> str:
    """Render a human-readable inspect surface from the machine payload."""

    lines = [
        "Interactive CAO Demo Inspect",
        "",
        "Session Summary",
        f"session_status: {payload['session_status']}",
        f"claude_code_state: {payload['claude_code_state']}",
        f"agent_identity: {payload['agent_identity']}",
        f"terminal_id: {payload['terminal_id']}",
        f"last_updated: {payload['updated_at']}",
        "",
        "Commands",
        f"tmux_attach: {payload['tmux_attach_command']}",
        f"terminal_log_tail: {payload['terminal_log_tail_command']}",
        "",
        "Artifacts",
        f"session_manifest: {payload['session_manifest']}",
        f"terminal_log_path: {payload['terminal_log_path']}",
        f"workspace_dir: {payload['workspace_dir']}",
        f"runtime_root: {payload['runtime_root']}",
    ]

    output_text_tail_chars = payload.get("output_text_tail_chars_requested")
    if isinstance(output_text_tail_chars, int):
        lines.extend(["", f"Output Text Tail (last {output_text_tail_chars} chars)"])
        note = payload.get("output_text_tail_note")
        if isinstance(note, str) and note.strip():
            lines.append(note)
        else:
            output_text_tail = payload.get("output_text_tail")
            if isinstance(output_text_tail, str) and output_text_tail:
                lines.extend(_indented_lines(output_text_tail))
            else:
                lines.append("  <empty>")

    return "\n".join(lines)


def _render_start_output(*, payload: dict[str, object]) -> str:
    """Render a human-readable startup success surface."""

    state = _require_mapping(payload.get("state"), context="start payload missing state")
    agent_identity = _require_non_empty_string(
        state.get("agent_identity"),
        context="start payload missing state.agent_identity",
    )
    tmux_target = _require_non_empty_string(
        state.get("tmux_target"),
        context="start payload missing state.tmux_target",
    )
    terminal_id = _require_non_empty_string(
        state.get("terminal_id"),
        context="start payload missing state.terminal_id",
    )
    terminal_log_path = _require_non_empty_string(
        state.get("terminal_log_path"),
        context="start payload missing state.terminal_log_path",
    )
    session_manifest = _require_non_empty_string(
        state.get("session_manifest"),
        context="start payload missing state.session_manifest",
    )
    workspace_dir = _require_non_empty_string(
        state.get("workspace_dir"),
        context="start payload missing state.workspace_dir",
    )
    runtime_root = _require_non_empty_string(
        state.get("runtime_root"),
        context="start payload missing state.runtime_root",
    )
    brain_manifest = _require_non_empty_string(
        state.get("brain_manifest"),
        context="start payload missing state.brain_manifest",
    )
    launcher_config_path = _require_non_empty_string(
        state.get("launcher_config_path"),
        context="start payload missing state.launcher_config_path",
    )
    cao_base_url = _require_non_empty_string(
        state.get("cao_base_url"),
        context="start payload missing state.cao_base_url",
    )
    updated_at = _require_non_empty_string(
        state.get("updated_at"),
        context="start payload missing state.updated_at",
    )

    lines = [
        "Interactive CAO Demo Started",
        "",
        "Session Summary",
        "session_status: active",
        f"agent_identity: {agent_identity}",
        f"terminal_id: {terminal_id}",
        f"cao_base_url: {cao_base_url}",
        f"last_updated: {updated_at}",
        "",
        "Commands",
        f"tmux_attach: tmux attach -t {tmux_target}",
        f"terminal_log_tail: tail -f {terminal_log_path}",
        "",
        "Artifacts",
        f"session_manifest: {session_manifest}",
        f"brain_manifest: {brain_manifest}",
        f"workspace_dir: {workspace_dir}",
        f"runtime_root: {runtime_root}",
        f"launcher_config_path: {launcher_config_path}",
    ]

    replaced_previous_agent_identity = payload.get("replaced_previous_agent_identity")
    warnings = payload.get("warnings")
    notes: list[str] = []
    if (
        isinstance(replaced_previous_agent_identity, str)
        and replaced_previous_agent_identity.strip()
    ):
        notes.append(f"replaced_previous_agent_identity: {replaced_previous_agent_identity}")
    if isinstance(warnings, list):
        for warning in warnings:
            if isinstance(warning, str) and warning.strip():
                notes.append(f"warning: {warning}")
    if notes:
        lines.extend(["", "Notes", *notes])

    return "\n".join(lines)


def _indented_lines(text: str) -> list[str]:
    """Indent multi-line text for human-readable inspect output."""

    lines = text.splitlines()
    if not lines:
        return ["  <empty>"]
    return [f"  {line}" for line in lines]


def _parse_events(*, stdout: str) -> list[dict[str, object]]:
    """Parse JSONL runtime events from `send-prompt` stdout."""

    events: list[dict[str, object]] = []
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            events.append(payload)
    return events


def _extract_done_message(events: list[dict[str, object]]) -> str:
    """Extract the final `done` event message from parsed runtime events."""

    response_text = ""
    for event in events:
        if event.get("kind") == "done":
            response_text = str(event.get("message", "")).strip()
    return response_text


def _load_json_file(path: Path, *, context: str) -> dict[str, object]:
    """Load a JSON file and require a top-level object payload."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DemoWorkflowError(f"{context} file not found: `{path}`.") from exc
    except json.JSONDecodeError as exc:
        raise DemoWorkflowError(f"Invalid JSON in {context} `{path}`.") from exc
    return _require_mapping(payload, context=f"{context} `{path}` must contain a JSON object")


def _write_json_file(path: Path, payload: dict[str, object]) -> None:
    """Persist a JSON object payload with stable formatting."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _parse_json_output(text: str, *, context: str) -> dict[str, object]:
    """Parse CLI stdout as a JSON object payload."""

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise DemoWorkflowError(f"Invalid JSON in {context}.") from exc
    return _require_mapping(payload, context=f"{context} must be a JSON object")


def _require_mapping(value: object, *, context: str) -> dict[str, object]:
    """Require that a value is a JSON-like object mapping."""

    if not isinstance(value, dict):
        raise DemoWorkflowError(context)
    return value


def _require_non_empty_string(value: object, *, context: str) -> str:
    """Require that a value is a non-empty string."""

    if not isinstance(value, str) or not value.strip():
        raise DemoWorkflowError(context)
    return value.strip()


def _validate_model(model: type[_ModelT], payload: object, *, source: str) -> _ModelT:
    """Validate a strict model payload with an actionable source label."""

    try:
        return model.model_validate(payload)
    except ValidationError as exc:
        raise DemoWorkflowError(f"Invalid payload for `{source}`: {exc}") from exc


def _require_tool(executable: str) -> None:
    """Require that a command-line executable is available on PATH."""

    if shutil.which(executable) is None:
        raise DemoWorkflowError(f"`{executable}` is required on PATH for this demo.")


def _join_command(command: Sequence[str]) -> str:
    """Render a subprocess command for diagnostic messages."""

    return " ".join(command)


def _emit_startup_progress(message: str) -> None:
    """Print one operator-facing startup progress line on stderr."""

    print(f"[interactive-demo:start] {message}", file=sys.stderr, flush=True)


def _format_elapsed_seconds(elapsed_seconds: float) -> str:
    """Render elapsed time for startup progress heartbeats."""

    if elapsed_seconds < 10.0:
        return f"{elapsed_seconds:.1f}s"
    return f"{elapsed_seconds:.0f}s"


def _positive_int(raw_value: str) -> int:
    """Parse a strictly positive integer CLI flag value."""

    try:
        parsed = int(raw_value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected a positive integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("expected a positive integer")
    return parsed


def _print_json(payload: dict[str, object]) -> None:
    """Print a JSON payload to stdout."""

    print(json.dumps(payload, indent=2, sort_keys=True))


def _utc_now() -> str:
    """Return the current UTC timestamp in stable ISO-8601 format."""

    return datetime.now(UTC).isoformat(timespec="seconds")


if __name__ == "__main__":
    raise SystemExit(main())
