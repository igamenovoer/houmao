"""CLI entrypoint for the passive-server parallel validation demo pack."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from houmao.demo.legacy.passive_server_parallel_validation_demo_pack.commands import (
    auto_demo,
    default_expected_report_path,
    gateway_demo,
    headless_demo,
    inspect_demo,
    preflight_demo,
    resolve_demo_output_dir,
    resolve_pack_paths,
    start_demo,
    stop_demo,
    verify_demo,
)
from houmao.demo.legacy.passive_server_parallel_validation_demo_pack.provisioning import (
    ParallelConfig,
    SuiteError,
)
from houmao.demo.legacy.passive_server_parallel_validation_demo_pack.models import (
    DEFAULT_COMPAT_CODEX_WARMUP_SECONDS,
    DEFAULT_COMPAT_PROVIDER_READY_TIMEOUT_SECONDS,
    DEFAULT_COMPAT_SHELL_READY_TIMEOUT_SECONDS,
    DEFAULT_DISCOVERY_TIMEOUT_SECONDS,
    DEFAULT_HEALTH_TIMEOUT_SECONDS,
    DEFAULT_HISTORY_LIMIT,
    DEFAULT_OLD_SERVER_PORT,
    DEFAULT_PASSIVE_SERVER_PORT,
    DEFAULT_PROVIDER,
    DEFAULT_REQUEST_POLL_INTERVAL_SECONDS,
    DEFAULT_REQUEST_TIMEOUT_SECONDS,
    PROVIDER_CHOICES,
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
        description="Passive-server parallel validation demo-pack commands."
    )
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--repo-root", type=Path, default=None)
    common.add_argument("--pack-dir", type=Path, default=None)
    common.add_argument("--demo-output-dir", type=Path, default=None)
    common.add_argument("--provider", choices=PROVIDER_CHOICES, default=DEFAULT_PROVIDER)
    common.add_argument("--old-server-port", type=int, default=DEFAULT_OLD_SERVER_PORT)
    common.add_argument("--passive-server-port", type=int, default=DEFAULT_PASSIVE_SERVER_PORT)
    common.add_argument(
        "--health-timeout-seconds",
        type=_positive_float,
        default=DEFAULT_HEALTH_TIMEOUT_SECONDS,
    )
    common.add_argument(
        "--discovery-timeout-seconds",
        type=_positive_float,
        default=DEFAULT_DISCOVERY_TIMEOUT_SECONDS,
    )
    common.add_argument(
        "--request-timeout-seconds",
        type=_positive_float,
        default=DEFAULT_REQUEST_TIMEOUT_SECONDS,
    )
    common.add_argument(
        "--request-poll-interval-seconds",
        type=_positive_float,
        default=DEFAULT_REQUEST_POLL_INTERVAL_SECONDS,
    )
    common.add_argument(
        "--history-limit",
        type=_positive_int,
        default=DEFAULT_HISTORY_LIMIT,
    )
    common.add_argument(
        "--compat-shell-ready-timeout-seconds",
        type=_positive_float,
        default=DEFAULT_COMPAT_SHELL_READY_TIMEOUT_SECONDS,
    )
    common.add_argument(
        "--compat-provider-ready-timeout-seconds",
        type=_positive_float,
        default=DEFAULT_COMPAT_PROVIDER_READY_TIMEOUT_SECONDS,
    )
    common.add_argument(
        "--compat-codex-warmup-seconds",
        type=_positive_float,
        default=DEFAULT_COMPAT_CODEX_WARMUP_SECONDS,
    )
    common.add_argument("--json", action="store_true")

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser(
        "start",
        help="Start both authorities and launch the shared interactive validation agent",
        parents=[common],
    )
    subparsers.add_parser(
        "inspect",
        help="Compare shared interactive discovery and managed-state parity",
        parents=[common],
    )
    subparsers.add_parser(
        "gateway",
        help="Attach a local gateway and validate the passive-server gateway proxy path",
        parents=[common],
    )
    subparsers.add_parser(
        "headless",
        help="Launch a passive-server-managed headless agent and verify old-server visibility",
        parents=[common],
    )

    verify = subparsers.add_parser(
        "verify",
        help="Build and verify the sanitized dual-authority report",
        parents=[common],
    )
    verify.add_argument("--expected-report", type=Path, default=None)
    verify.add_argument("--snapshot-report", action="store_true")

    stop = subparsers.add_parser(
        "stop",
        help="Stop the shared validation agents and both authorities",
        parents=[common],
    )
    stop.add_argument("--stop-timeout-seconds", type=_positive_float, default=10.0)

    auto = subparsers.add_parser(
        "auto",
        help="Run start -> inspect -> gateway -> headless -> stop -> verify",
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
    config = ParallelConfig(
        provider=args.provider,
        pack_dir=pack_paths.pack_dir,
        output_root=demo_output_dir,
        old_server_port=int(args.old_server_port),
        passive_server_port=int(args.passive_server_port),
        health_timeout_seconds=float(args.health_timeout_seconds),
        discovery_timeout_seconds=float(args.discovery_timeout_seconds),
        request_timeout_seconds=float(args.request_timeout_seconds),
        request_poll_interval_seconds=float(args.request_poll_interval_seconds),
        history_limit=int(args.history_limit),
        compat_shell_ready_timeout_seconds=float(args.compat_shell_ready_timeout_seconds),
        compat_provider_ready_timeout_seconds=float(args.compat_provider_ready_timeout_seconds),
        compat_codex_warmup_seconds=float(args.compat_codex_warmup_seconds),
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
            )
        elif args.command == "gateway":
            payload = gateway_demo(demo_output_dir=demo_output_dir)
        elif args.command == "headless":
            payload = headless_demo(demo_output_dir=demo_output_dir)
        elif args.command == "stop":
            payload = stop_demo(
                demo_output_dir=demo_output_dir,
                timeout_seconds=float(getattr(args, "stop_timeout_seconds", 10.0)),
            )
        elif args.command == "verify":
            payload = verify_demo(
                demo_output_dir=demo_output_dir,
                expected_report_path=expected_report_path,
                snapshot=bool(getattr(args, "snapshot_report", False)),
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
        else:  # pragma: no cover - argparse keeps this unreachable
            raise AssertionError(f"Unhandled command: {args.command}")
    except SuiteError as exc:
        if args.json:
            print(json.dumps({"status": "error", "detail": str(exc)}, indent=2, sort_keys=True))
        else:
            print(str(exc), file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0
