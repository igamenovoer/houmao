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
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable, Sequence, TypeAlias, TypeVar

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from gig_agents.agents.brain_launch_runtime.agent_identity import (
    normalize_agent_identity_name,
)

FIXED_CAO_BASE_URL = "http://127.0.0.1:9889"
DEFAULT_AGENT_NAME = "cao-interactive-demo"
DEFAULT_CONFIG_PROFILE = "default"
DEFAULT_CREDENTIAL_PROFILE = "personal-a-default"
DEFAULT_ROLE_NAME = "gpu-kernel-coder"
DEFAULT_TIMEOUT_SECONDS = 180.0
DEFAULT_TOOL_NAME = "claude"
DEFAULT_SKILLS: tuple[str, ...] = ("openspec-apply-change",)
DEFAULT_TERMINAL_LOG_ROOT = "~/.aws/cli-agent-orchestrator/logs/terminal"
EMPTY_RESPONSE_ERROR = "interactive CAO turn returned an empty response"
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
    agent_def_dir: Path
    launcher_home_dir: Path
    workdir: Path
    role_name: str
    config_profile: str
    credential_profile: str
    skills: tuple[str, ...]
    timeout_seconds: float


@dataclass(frozen=True)
class CommandResult:
    """Captured subprocess result plus persisted log locations."""

    args: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str
    stdout_path: Path
    stderr_path: Path


CommandRunner: TypeAlias = Callable[
    [Sequence[str], Path, Path, Path, float],
    CommandResult,
]
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
    paths = DemoPaths.from_workspace_root(args.workspace_root)
    env = DemoEnvironment(
        repo_root=args.repo_root.expanduser().resolve(),
        agent_def_dir=args.agent_def_dir.expanduser().resolve(),
        launcher_home_dir=args.launcher_home_dir.expanduser().resolve(),
        workdir=args.workdir.expanduser().resolve(),
        role_name=str(args.role_name),
        config_profile=str(args.config_profile),
        credential_profile=str(args.credential_profile),
        skills=tuple(args.skills or DEFAULT_SKILLS),
        timeout_seconds=float(args.timeout_seconds),
    )
    runner = run_command or run_subprocess_command

    try:
        if args.command == "start":
            payload = start_demo(
                paths=paths,
                env=env,
                agent_name=str(args.agent_name),
                run_command=runner,
            )
            _print_json(payload)
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
            inspect_demo(paths=paths, as_json=bool(args.json))
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

    _ensure_workspace(paths)
    _require_tool("pixi")
    _require_tool("tmux")

    previous_state = load_demo_state(paths.state_path)
    replaced_agent_identity: str | None = None
    if previous_state is not None and previous_state.active:
        replaced_agent_identity = previous_state.agent_identity
        _stop_remote_session(
            paths=paths,
            env=env,
            state=previous_state,
            run_command=run_command,
            tolerate_stale=True,
            log_prefix="replacement-stop",
        )

    _reset_turn_artifacts(paths)
    _write_launcher_config(paths.launcher_config_path, env=env, runtime_root=paths.runtime_root)
    _ensure_cao_server(paths=paths, env=env, run_command=run_command)

    normalized_identity = normalize_agent_identity_name(agent_name)
    build_payload = _build_brain(paths=paths, env=env, run_command=run_command)
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
        terminal_log_path=_terminal_log_path(terminal_id),
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
            "send-turn failed via `brain_launch_runtime send-prompt` "
            f"(see `{stderr_path}`)"
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


def inspect_demo(*, paths: DemoPaths, as_json: bool) -> None:
    """Render stored inspection metadata for the active or latest session."""

    state = load_demo_state(paths.state_path)
    if state is None:
        raise DemoWorkflowError(
            "No interactive demo state was found. Run `start` before `inspect`."
        )

    payload = {
        "active": state.active,
        "agent_identity": state.agent_identity,
        "session_manifest": state.session_manifest,
        "tmux_target": state.tmux_target,
        "tmux_attach_command": f"tmux attach -t {state.tmux_target}",
        "terminal_id": state.terminal_id,
        "terminal_log_path": state.terminal_log_path,
        "terminal_log_tail_command": f"tail -f {state.terminal_log_path}",
        "workspace_dir": state.workspace_dir,
        "runtime_root": state.runtime_root,
        "updated_at": state.updated_at,
    }
    if as_json:
        _print_json(payload)
        return

    lines = [
        f"active: {state.active}",
        f"agent_identity: {state.agent_identity}",
        f"session_manifest: {state.session_manifest}",
        f"tmux_attach: tmux attach -t {state.tmux_target}",
        f"terminal_log_tail: tail -f {state.terminal_log_path}",
        f"workspace_dir: {state.workspace_dir}",
        f"runtime_root: {state.runtime_root}",
        f"updated_at: {state.updated_at}",
    ]
    print("\n".join(lines))


def verify_demo(*, paths: DemoPaths) -> VerificationReport:
    """Generate a verification report from persisted turn artifacts."""

    state = load_demo_state(paths.state_path)
    if state is None:
        raise DemoWorkflowError(
            "No interactive demo state was found. Run `start` before `verify`."
        )

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
            raise DemoWorkflowError(
                f"Turn {record.turn_index} has an empty response_text."
            )
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
        terminal_log_path=state.terminal_log_path,
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
        raise DemoWorkflowError(
            "No interactive demo state was found. Run `start` before `stop`."
        )
    if not state.active:
        raise DemoWorkflowError("Interactive demo state is already inactive.")

    result = _stop_remote_session(
        paths=paths,
        env=env,
        state=state,
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


def _build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser for the interactive demo."""

    parser = argparse.ArgumentParser(
        description="Interactive CAO full-pipeline demo commands."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root used as command cwd and default workdir.",
    )
    parser.add_argument(
        "--workspace-root",
        type=Path,
        default=Path.cwd() / "tmp" / "cao_interactive_full_pipeline_demo",
        help="Stable workspace root for state, turns, and reports.",
    )
    parser.add_argument(
        "--agent-def-dir",
        type=Path,
        default=Path.cwd() / "tests" / "fixtures" / "agents",
        help="Agent definition root for runtime commands.",
    )
    parser.add_argument(
        "--launcher-home-dir",
        type=Path,
        default=Path.cwd() / "tmp" / "cao_interactive_full_pipeline_demo",
        help="Home directory used by the CAO launcher-managed profile store.",
    )
    parser.add_argument(
        "--workdir",
        type=Path,
        default=Path.cwd(),
        help="Working directory passed to `brain_launch_runtime start-session`.",
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

    send_turn_parser = subparsers.add_parser(
        "send-turn", help="Send one prompt to the active interactive session"
    )
    send_turn_group = send_turn_parser.add_mutually_exclusive_group(required=True)
    send_turn_group.add_argument("--prompt", help="Inline prompt text")
    send_turn_group.add_argument("--prompt-file", type=Path, help="Path to prompt text file")

    inspect = subparsers.add_parser("inspect", help="Show tmux/log inspection commands")
    inspect.add_argument("--json", action="store_true", help="Print machine-readable JSON")

    subparsers.add_parser("verify", help="Generate a verification report from recorded turns")
    subparsers.add_parser("stop", help="Stop the active interactive session")
    return parser


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
    """Ensure the local loopback CAO server is healthy and launcher-owned."""

    status_result = run_command(
        _launcher_cli_command(["status", "--config", str(paths.launcher_config_path)]),
        env.repo_root,
        paths.logs_dir / "cao-status.stdout",
        paths.logs_dir / "cao-status.stderr",
        env.timeout_seconds,
    )
    if status_result.returncode != 0 and shutil.which("cao-server") is None:
        raise DemoWorkflowError(
            "CAO server is unavailable at the fixed loopback target and "
            "`cao-server` is not available on PATH."
        )

    start_result = run_command(
        _launcher_cli_command(["start", "--config", str(paths.launcher_config_path)]),
        env.repo_root,
        paths.logs_dir / "cao-start.stdout",
        paths.logs_dir / "cao-start.stderr",
        env.timeout_seconds,
    )
    if start_result.returncode != 0:
        raise DemoWorkflowError(
            "Failed to start or attach the CAO server via launcher "
            f"(see `{start_result.stderr_path}`)."
        )

    start_payload = _parse_json_output(
        start_result.stdout,
        context="CAO launcher start output",
    )
    reused_existing = bool(start_payload.get("reused_existing_process"))
    pid_value = start_payload.get("pid")
    if reused_existing and pid_value is None:
        retry_stop_result = run_command(
            _launcher_cli_command(["stop", "--config", str(paths.launcher_config_path)]),
            env.repo_root,
            paths.logs_dir / "cao-stop-untracked.stdout",
            paths.logs_dir / "cao-stop-untracked.stderr",
            env.timeout_seconds,
        )
        if retry_stop_result.returncode != 0:
            # The existing demos treat this as best-effort, so keep going to the retry.
            pass
        retry_start_result = run_command(
            _launcher_cli_command(["start", "--config", str(paths.launcher_config_path)]),
            env.repo_root,
            paths.logs_dir / "cao-start-retry.stdout",
            paths.logs_dir / "cao-start-retry.stderr",
            env.timeout_seconds,
        )
        if retry_start_result.returncode != 0:
            raise DemoWorkflowError(
                "CAO launcher retry failed after ownership mismatch "
                f"(see `{retry_start_result.stderr_path}`)."
            )
        retry_payload = _parse_json_output(
            retry_start_result.stdout,
            context="CAO launcher retry start output",
        )
        if bool(retry_payload.get("reused_existing_process")) and retry_payload.get("pid") is None:
            raise DemoWorkflowError(
                "CAO launcher detected an untracked server on the fixed loopback target. "
                "Stop the external server and retry."
            )


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
            "Failed to build the interactive demo brain manifest "
            f"(see `{result.stderr_path}`)."
        )
    payload = _parse_json_output(result.stdout, context="build-brain output")
    _require_non_empty_string(payload.get("manifest_path"), context="build-brain missing manifest_path")
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
    result = run_command(
        command,
        env.repo_root,
        paths.logs_dir / "start-session.stdout",
        paths.logs_dir / "start-session.stderr",
        env.timeout_seconds,
    )
    if result.returncode != 0:
        raise DemoWorkflowError(
            "Failed to start the interactive CAO session "
            f"(see `{result.stderr_path}`)."
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
    state: DemoState,
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
                state.agent_identity,
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
        "Failed to stop the interactive CAO session "
        f"(see `{result.stderr_path}`)."
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


def _terminal_log_path(terminal_id: str) -> str:
    """Return the conventional CAO terminal log path for a terminal id."""

    return f"{DEFAULT_TERMINAL_LOG_ROOT}/{terminal_id}.log"


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


def _print_json(payload: dict[str, object]) -> None:
    """Print a JSON payload to stdout."""

    print(json.dumps(payload, indent=2, sort_keys=True))


def _utc_now() -> str:
    """Return the current UTC timestamp in stable ISO-8601 format."""

    return datetime.now(UTC).isoformat(timespec="seconds")


if __name__ == "__main__":
    raise SystemExit(main())
