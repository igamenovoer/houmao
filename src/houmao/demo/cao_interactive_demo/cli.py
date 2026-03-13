"""CLI entrypoint for the interactive CAO demo package."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from houmao.demo.cao_interactive_demo.commands import (
    _latest_demo_run_root,
    _read_current_run_root,
    _run_timestamp_slug,
    inspect_demo,
    send_control_input,
    send_turn,
    start_demo,
    stop_demo,
    verify_demo,
)
from houmao.demo.cao_interactive_demo.models import (
    DEFAULT_BRAIN_RECIPE_SELECTOR,
    CURRENT_RUN_ROOT_FILENAME,
    DEFAULT_DEMO_ROOT_DIRNAME,
    DEFAULT_ROLE_NAME,
    DEFAULT_TIMEOUT_SECONDS,
    DEFAULT_WORKTREE_DIRNAME,
    CommandRunner,
    DemoEnvironment,
    DemoInvocation,
    DemoPaths,
    DemoWorkflowError,
)
from houmao.demo.cao_interactive_demo.rendering import (
    _positive_int,
    _print_json,
    _render_start_output,
)
from houmao.demo.cao_interactive_demo.runtime import run_subprocess_command


def main(
    argv: list[str] | None = None,
    *,
    run_command: CommandRunner | None = None,
) -> int:
    """Run the interactive CAO demo CLI."""

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
                agent_name_override=getattr(args, "agent_name", None),
                brain_recipe_selector=getattr(args, "brain_recipe", None),
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
        if args.command == "send-keys":
            record = send_control_input(
                paths=paths,
                env=env,
                key_stream=_resolve_key_stream(args),
                as_raw_string=bool(args.as_raw_string),
                run_command=runner,
            )
            _print_json(record.model_dump(mode="json"))
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


def _build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser for the interactive demo."""

    parser = argparse.ArgumentParser(description="Interactive CAO demo commands.")
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
            "Working directory passed to `realm_controller start-session`. "
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
        help="Role name passed to `realm_controller start-session`.",
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
        default=None,
        help="Optional override for the selected recipe's default agent name.",
    )
    start.add_argument(
        "--brain-recipe",
        default=None,
        help=(
            "Brain recipe selector relative to `brains/brain-recipes/`. "
            f"Defaults to `{DEFAULT_BRAIN_RECIPE_SELECTOR}`. Optional `.yaml` "
            "suffix and basename-only lookup are supported."
        ),
    )
    start.add_argument("--json", action="store_true", help="Print machine-readable JSON")

    send_turn_parser = subparsers.add_parser(
        "send-turn", help="Send one prompt to the active interactive session"
    )
    send_turn_group = send_turn_parser.add_mutually_exclusive_group(required=True)
    send_turn_group.add_argument("--prompt", help="Inline prompt text")
    send_turn_group.add_argument("--prompt-file", type=Path, help="Path to prompt text file")

    send_keys_parser = subparsers.add_parser(
        "send-keys", help="Send one raw control-input sequence to the active interactive session"
    )
    send_keys_parser.add_argument("key_stream", help="Mixed literal/special-key key stream")
    send_keys_parser.add_argument(
        "--as-raw-string",
        action="store_true",
        help="Send the full key stream literally without parsing <[key-name]> tokens",
    )

    inspect = subparsers.add_parser("inspect", help="Show tmux/log inspection commands")
    inspect.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    inspect.add_argument(
        "--with-output-text",
        type=_positive_int,
        metavar="NUM_TAIL_CHARS",
        help=(
            "Include the last NUM_TAIL_CHARS of clean projected tool dialog text "
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
        timeout_seconds=float(args.timeout_seconds),
        yes_to_all=bool(args.yes),
        provision_worktree=provision_worktree,
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


def _resolve_prompt_text(args: argparse.Namespace) -> str:
    """Resolve prompt text from inline or file-based CLI inputs."""

    if args.prompt is not None:
        prompt = str(args.prompt)
    else:
        prompt = args.prompt_file.read_text(encoding="utf-8")
    if not prompt.strip():
        raise DemoWorkflowError("Prompt text must not be empty.")
    return prompt


def _resolve_key_stream(args: argparse.Namespace) -> str:
    """Resolve and validate the positional key-stream CLI input."""

    key_stream = str(args.key_stream)
    if not key_stream.strip():
        raise DemoWorkflowError("Key stream must not be empty.")
    return key_stream


if __name__ == "__main__":
    raise SystemExit(main())
