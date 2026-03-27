"""CLI entrypoint for the Houmao-server agent API demo pack."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from houmao.demo.houmao_server_agent_api_demo_pack.commands import (
    auto_demo,
    default_expected_report_path,
    inspect_demo,
    interrupt_demo,
    preflight_demo,
    prompt_demo,
    resolve_demo_output_dir,
    resolve_pack_paths,
    start_demo,
    stop_demo,
    verify_demo,
)
from houmao.demo.houmao_server_agent_api_demo_pack.provisioning import (
    DEFAULT_HISTORY_LIMIT,
    LANE_IDS,
    SuiteConfig,
    SuiteError,
)


def _positive_float(value: str) -> float:
    """Parse one positive float value."""

    parsed = float(value)
    if parsed <= 0.0:
        raise argparse.ArgumentTypeError("must be > 0")
    return parsed


def _positive_int(value: str) -> int:
    """Parse one positive integer value."""

    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be > 0")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    """Build the demo-pack CLI parser."""

    parser = argparse.ArgumentParser(
        description="Houmao-server direct managed-agent API demo-pack commands."
    )
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--repo-root", type=Path, default=None)
    common.add_argument("--pack-dir", type=Path, default=None)
    common.add_argument("--demo-output-dir", type=Path, default=None)
    common.add_argument("--lane", action="append", choices=LANE_IDS, default=[])
    common.add_argument("--port", type=int, default=None)
    common.add_argument(
        "--compat-http-timeout-seconds",
        type=_positive_float,
        default=20.0,
    )
    common.add_argument(
        "--compat-create-timeout-seconds",
        type=_positive_float,
        default=90.0,
    )
    common.add_argument(
        "--compat-provider-ready-timeout-seconds",
        type=_positive_float,
        default=90.0,
    )
    common.add_argument(
        "--health-timeout-seconds",
        type=_positive_float,
        default=30.0,
    )
    common.add_argument(
        "--prompt-timeout-seconds",
        type=_positive_float,
        default=120.0,
    )
    common.add_argument(
        "--prompt-poll-interval-seconds",
        type=_positive_float,
        default=2.0,
    )
    common.add_argument(
        "--history-limit",
        type=_positive_int,
        default=DEFAULT_HISTORY_LIMIT,
    )
    common.add_argument("--json", action="store_true")

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser(
        "start",
        help="Start the owned server and provision lanes",
        parents=[common],
    )

    inspect = subparsers.add_parser(
        "inspect",
        help="Inspect managed-agent routes",
        parents=[common],
    )
    inspect.add_argument(
        "--with-dialog-tail",
        type=_positive_int,
        default=None,
        metavar="NUM_CHARS",
    )

    prompt = subparsers.add_parser(
        "prompt",
        help="Submit one prompt to the selected lanes",
        parents=[common],
    )
    prompt_group = prompt.add_mutually_exclusive_group(required=False)
    prompt_group.add_argument("--prompt", default=None)
    prompt_group.add_argument("--prompt-file", type=Path, default=None)

    subparsers.add_parser(
        "interrupt",
        help="Submit one interrupt to the selected lanes",
        parents=[common],
    )

    verify = subparsers.add_parser(
        "verify",
        help="Build and verify the sanitized report",
        parents=[common],
    )
    verify.add_argument("--expected-report", type=Path, default=None)
    verify.add_argument("--snapshot-report", action="store_true")

    stop = subparsers.add_parser(
        "stop",
        help="Stop all lanes and the owned server",
        parents=[common],
    )
    stop.add_argument("--stop-timeout-seconds", type=_positive_float, default=10.0)

    auto = subparsers.add_parser(
        "auto",
        help="Run start -> inspect -> prompt -> verify -> stop",
        parents=[common],
    )
    auto.add_argument("--expected-report", type=Path, default=None)
    auto.add_argument("--snapshot-report", action="store_true")

    subparsers.add_parser("preflight", help=argparse.SUPPRESS, parents=[common])
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the demo-pack CLI."""

    parser = build_parser()
    args = parser.parse_args(argv or sys.argv[1:])
    pack_paths = resolve_pack_paths(repo_root=args.repo_root, pack_dir=args.pack_dir)
    demo_output_dir = resolve_demo_output_dir(
        command_name=args.command,
        pack_paths=pack_paths,
        raw_demo_output_dir=args.demo_output_dir,
    )
    config = SuiteConfig(
        selected_lane_ids=tuple(args.lane),
        pack_dir=pack_paths.pack_dir,
        output_root=demo_output_dir,
        port=args.port,
        compat_http_timeout_seconds=float(args.compat_http_timeout_seconds),
        compat_create_timeout_seconds=float(args.compat_create_timeout_seconds),
        compat_provider_ready_timeout_seconds=float(args.compat_provider_ready_timeout_seconds),
        health_timeout_seconds=float(args.health_timeout_seconds),
        prompt_timeout_seconds=float(args.prompt_timeout_seconds),
        prompt_poll_interval_seconds=float(args.prompt_poll_interval_seconds),
        history_limit=int(args.history_limit),
    )

    expected_report_path = (
        args.expected_report.resolve()
        if getattr(args, "expected_report", None) is not None
        else default_expected_report_path(pack_paths.pack_dir)
    )

    try:
        if args.command == "start":
            payload = start_demo(
                pack_paths=pack_paths,
                demo_output_dir=demo_output_dir,
                config=config,
            )
        elif args.command == "inspect":
            payload = inspect_demo(
                demo_output_dir=demo_output_dir,
                history_limit=int(args.history_limit),
                with_dialog_tail=getattr(args, "with_dialog_tail", None),
            )
        elif args.command == "prompt":
            payload = prompt_demo(
                pack_dir=pack_paths.pack_dir,
                demo_output_dir=demo_output_dir,
                prompt=getattr(args, "prompt", None),
                prompt_file=getattr(args, "prompt_file", None),
                lane_ids=tuple(args.lane),
            )
        elif args.command == "interrupt":
            payload = interrupt_demo(
                pack_dir=pack_paths.pack_dir,
                demo_output_dir=demo_output_dir,
                lane_ids=tuple(args.lane),
            )
        elif args.command == "verify":
            payload = verify_demo(
                demo_output_dir=demo_output_dir,
                expected_report_path=expected_report_path,
                snapshot=bool(getattr(args, "snapshot_report", False)),
            )
        elif args.command == "stop":
            payload = stop_demo(
                demo_output_dir=demo_output_dir,
                timeout_seconds=float(getattr(args, "stop_timeout_seconds", 10.0)),
            )
        elif args.command == "auto":
            payload = auto_demo(
                pack_paths=pack_paths,
                demo_output_dir=demo_output_dir,
                config=config,
                expected_report_path=expected_report_path,
                snapshot=bool(getattr(args, "snapshot_report", False)),
            )
        elif args.command == "preflight":
            payload = preflight_demo(
                pack_paths=pack_paths,
                demo_output_dir=demo_output_dir,
                config=config,
            )
        else:
            parser.error(f"unsupported command: {args.command}")
            return 2
    except SuiteError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if bool(args.json):
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
