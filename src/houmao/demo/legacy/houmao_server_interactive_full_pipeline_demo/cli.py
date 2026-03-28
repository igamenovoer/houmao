"""CLI entrypoint for the interactive full-pipeline demo."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from houmao.demo.legacy.houmao_server_interactive_full_pipeline_demo.commands import (
    _latest_demo_run_root,
    _read_current_run_root,
    _run_timestamp_slug,
    inspect_demo,
    interrupt_demo,
    send_turn,
    start_demo,
    stop_demo,
    verify_demo,
)
from houmao.demo.legacy.houmao_server_interactive_full_pipeline_demo.models import (
    CURRENT_RUN_ROOT_FILENAME,
    DEFAULT_COMPAT_CODEX_WARMUP_SECONDS,
    DEFAULT_COMPAT_PROVIDER_READY_TIMEOUT_SECONDS,
    DEFAULT_COMPAT_SHELL_READY_TIMEOUT_SECONDS,
    DEFAULT_DEMO_ROOT_DIRNAME,
    DEFAULT_PROVIDER,
    DEFAULT_REQUEST_POLL_INTERVAL_SECONDS,
    DEFAULT_REQUEST_SETTLE_TIMEOUT_SECONDS,
    DemoEnvironment,
    DemoInvocation,
    DemoPaths,
    DemoWorkflowError,
    PROVIDER_CHOICES,
)


def main(argv: list[str] | None = None) -> int:
    """Run the standalone interactive demo CLI."""

    parser = _build_parser()
    args = parser.parse_args(argv or sys.argv[1:])
    invocation = _resolve_demo_invocation(args)

    try:
        if args.command == "start":
            start_payload = start_demo(
                paths=invocation.paths,
                env=invocation.env,
                provider=str(args.provider),
                requested_session_name=getattr(args, "session_name", None),
            )
            if bool(getattr(args, "json", False)):
                _print_json(start_payload.model_dump(mode="json"))
            else:
                print(_render_start_output(start_payload))
            return 0
        if args.command == "inspect":
            inspect_payload = inspect_demo(
                paths=invocation.paths,
                dialog_tail_chars=getattr(args, "with_dialog_tail", None),
            )
            if bool(getattr(args, "json", False)):
                _print_json(inspect_payload.model_dump(mode="json"))
            else:
                print(_render_inspect_output(inspect_payload.model_dump(mode="json")))
            return 0
        if args.command == "send-turn":
            turn_payload = send_turn(
                paths=invocation.paths,
                env=invocation.env,
                prompt=_resolve_prompt_text(args),
            )
            _print_json(turn_payload.model_dump(mode="json"))
            return 0
        if args.command == "interrupt":
            interrupt_payload = interrupt_demo(paths=invocation.paths, env=invocation.env)
            _print_json(interrupt_payload.model_dump(mode="json"))
            return 0
        if args.command == "verify":
            verify_payload = verify_demo(paths=invocation.paths)
            _print_json(verify_payload.model_dump(mode="json"))
            return 0
        if args.command == "stop":
            stop_payload = stop_demo(paths=invocation.paths, env=invocation.env)
            _print_json(stop_payload.model_dump(mode="json"))
            return 0
    except DemoWorkflowError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    parser.print_help()
    return 1


def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for the interactive demo."""

    parser = argparse.ArgumentParser(description="Local interactive full-pipeline demo commands.")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repository root used as the base for omitted defaults.",
    )
    parser.add_argument(
        "--workspace-root",
        type=Path,
        default=None,
        help="Workspace root for persisted demo state, artifacts, and runtime files.",
    )
    parser.add_argument(
        "--request-settle-timeout-seconds",
        type=float,
        default=DEFAULT_REQUEST_SETTLE_TIMEOUT_SECONDS,
        help="Bounded wait budget for local request-state changes.",
    )
    parser.add_argument(
        "--request-poll-interval-seconds",
        type=float,
        default=DEFAULT_REQUEST_POLL_INTERVAL_SECONDS,
        help="Polling interval used while waiting for request-state changes.",
    )
    parser.add_argument(
        "--compat-shell-ready-timeout-seconds",
        type=_positive_float,
        default=DEFAULT_COMPAT_SHELL_READY_TIMEOUT_SECONDS,
        help="Bounded wait budget for the launched local shell to become available.",
    )
    parser.add_argument(
        "--compat-provider-ready-timeout-seconds",
        type=_positive_float,
        default=DEFAULT_COMPAT_PROVIDER_READY_TIMEOUT_SECONDS,
        help="Bounded wait budget for the launched local provider UI to become ready.",
    )
    parser.add_argument(
        "--compat-codex-warmup-seconds",
        type=_non_negative_float,
        default=DEFAULT_COMPAT_CODEX_WARMUP_SECONDS,
        help="Extra post-readiness warmup sleep applied only to local Codex launches.",
    )

    subparsers = parser.add_subparsers(dest="command")

    start = subparsers.add_parser("start", help="Start or replace the interactive session")
    start.add_argument(
        "--provider",
        choices=PROVIDER_CHOICES,
        default=DEFAULT_PROVIDER,
        help="Selected local managed-agent provider.",
    )
    start.add_argument(
        "--session-name",
        default=None,
        help="Optional managed-agent name and tmux-session override.",
    )
    start.add_argument("--json", action="store_true", help="Print machine-readable JSON")

    inspect = subparsers.add_parser("inspect", help="Inspect the current demo state")
    inspect.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    inspect.add_argument(
        "--with-dialog-tail",
        type=_positive_int,
        metavar="NUM_TAIL_CHARS",
        help="Include the last NUM_TAIL_CHARS of parser-derived dialog tail text.",
    )

    send_turn_parser = subparsers.add_parser(
        "send-turn", help="Submit one prompt through the managed-agent request route"
    )
    send_turn_group = send_turn_parser.add_mutually_exclusive_group(required=True)
    send_turn_group.add_argument("--prompt", help="Inline prompt text")
    send_turn_group.add_argument("--prompt-file", type=Path, help="Path to prompt text file")

    subparsers.add_parser("interrupt", help="Submit one interrupt through the managed-agent route")
    subparsers.add_parser("verify", help="Generate a sanitized verification report")
    subparsers.add_parser("stop", help="Stop the active interactive session")
    return parser


def _resolve_demo_invocation(args: argparse.Namespace) -> DemoInvocation:
    """Resolve CLI arguments into concrete paths and environment values."""

    repo_root = _resolve_repo_root(getattr(args, "repo_root", None))
    demo_base_root = repo_root / "tmp" / "demo" / DEFAULT_DEMO_ROOT_DIRNAME
    current_run_root_path = demo_base_root / CURRENT_RUN_ROOT_FILENAME
    workspace_root = _resolve_workspace_root(
        command=str(args.command),
        demo_base_root=demo_base_root,
        current_run_root_path=current_run_root_path,
        workspace_root=getattr(args, "workspace_root", None),
    )
    env = DemoEnvironment(
        repo_root=repo_root,
        demo_base_root=demo_base_root,
        current_run_root_path=current_run_root_path,
        provision_worktree=True,
        request_settle_timeout_seconds=float(args.request_settle_timeout_seconds),
        request_poll_interval_seconds=float(args.request_poll_interval_seconds),
        compat_shell_ready_timeout_seconds=float(args.compat_shell_ready_timeout_seconds),
        compat_provider_ready_timeout_seconds=float(args.compat_provider_ready_timeout_seconds),
        compat_codex_warmup_seconds=float(args.compat_codex_warmup_seconds),
    )
    return DemoInvocation(paths=DemoPaths.from_workspace_root(workspace_root), env=env)


def _resolve_repo_root(repo_root: Path | None) -> Path:
    """Resolve the effective repository root for demo defaults."""

    if repo_root is not None:
        return repo_root.expanduser().resolve()
    return Path(__file__).resolve().parents[4]


def _resolve_workspace_root(
    *,
    command: str,
    demo_base_root: Path,
    current_run_root_path: Path,
    workspace_root: Path | None,
) -> Path:
    """Resolve the effective workspace root for the selected command."""

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
        "No interactive demo workspace was found. Run `start` before this command or provide "
        "`--workspace-root`."
    )


def _resolve_prompt_text(args: argparse.Namespace) -> str:
    """Resolve prompt text from inline or file-based CLI inputs."""

    if args.prompt is not None:
        prompt = str(args.prompt)
    else:
        prompt = args.prompt_file.read_text(encoding="utf-8")
    if not prompt.strip():
        raise DemoWorkflowError("Prompt text must not be empty.")
    return prompt


def _positive_int(value: str) -> int:
    """Parse one positive integer CLI argument."""

    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be > 0")
    return parsed


def _positive_float(value: str) -> float:
    """Parse one positive floating-point CLI argument."""

    parsed = float(value)
    if parsed <= 0.0:
        raise argparse.ArgumentTypeError("value must be > 0")
    return parsed


def _non_negative_float(value: str) -> float:
    """Parse one non-negative floating-point CLI argument."""

    parsed = float(value)
    if parsed < 0.0:
        raise argparse.ArgumentTypeError("value must be >= 0")
    return parsed


def _print_json(payload: dict[str, object]) -> None:
    """Emit one stable JSON payload."""

    print(json.dumps(payload, indent=2, sort_keys=True))


def _render_start_output(payload: object) -> str:
    """Render a concise human-readable startup summary."""

    state = getattr(payload, "state")
    return "\n".join(
        [
            "Local interactive demo started.",
            f"provider: {state.provider}",
            f"tool: {state.tool}",
            f"variant: {state.variant_id}",
            f"agent_name: {state.agent_name}",
            f"agent_id: {state.agent_id}",
            f"tmux_session_name: {state.tmux_session_name}",
            f"workdir: {state.workdir}",
        ]
    )


def _render_inspect_output(payload: dict[str, object]) -> str:
    """Render a concise human-readable inspect summary."""

    lines = [
        f"active: {payload['active']}",
        f"provider: {payload['provider']}",
        f"tool: {payload['tool']}",
        f"variant: {payload['variant_id']}",
        f"agent_name: {payload['agent_name']}",
        f"agent_id: {payload['agent_id']}",
        f"tmux_session_name: {payload['tmux_session_name']}",
    ]
    managed_agent = payload.get("managed_agent")
    if isinstance(managed_agent, dict):
        lines.append(f"availability: {managed_agent['availability']}")
        lines.append(f"turn_phase: {managed_agent['turn_phase']}")
        lines.append(f"last_turn_result: {managed_agent['last_turn_result']}")
    terminal = payload.get("terminal")
    if isinstance(terminal, dict):
        lines.append(f"terminal_stable: {terminal['stable']}")
        lines.append(f"terminal_ready_posture: {terminal['ready_posture']}")
    dialog_tail = payload.get("dialog_tail")
    if isinstance(dialog_tail, str) and dialog_tail:
        lines.append("dialog_tail:")
        lines.append(dialog_tail)
    live_error = payload.get("live_error")
    if isinstance(live_error, str) and live_error:
        lines.append(f"live_error: {live_error}")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
