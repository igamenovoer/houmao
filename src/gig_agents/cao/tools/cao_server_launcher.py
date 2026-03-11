"""CLI entrypoint for `cao-server` lifecycle management."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from gig_agents.cao.server_launcher import (
    CaoServerLauncherConfigOverrides,
    CaoServerLauncherError,
    CaoServerLauncherConfig,
    CaoServerStartResult,
    CaoServerStatusResult,
    CaoServerStopResult,
    ProxyPolicy,
    dataclass_to_json_payload,
    load_cao_server_launcher_config,
    start_cao_server,
    status_cao_server,
    stop_cao_server,
)


def main(argv: list[str] | None = None) -> int:
    """Run CAO server launcher CLI.

    Parameters
    ----------
    argv:
        Optional argument list. Defaults to `sys.argv[1:]`.

    Returns
    -------
    int
        Process exit code.
    """

    parser = _build_parser()
    args = parser.parse_args(argv or sys.argv[1:])

    try:
        if args.command == "status":
            status_result = _cmd_status(args)
            print(json.dumps(dataclass_to_json_payload(status_result), indent=2, sort_keys=True))
            return 0 if status_result.healthy else 2

        if args.command == "start":
            start_result = _cmd_start(args)
            print(json.dumps(dataclass_to_json_payload(start_result), indent=2, sort_keys=True))
            return 0 if start_result.healthy else 2

        if args.command == "stop":
            stop_result = _cmd_stop(args)
            print(json.dumps(dataclass_to_json_payload(stop_result), indent=2, sort_keys=True))
            if stop_result.stopped or stop_result.already_stopped:
                return 0
            return 2
    except CaoServerLauncherError as exc:
        error_payload = {"ok": False, "error": str(exc)}
        print(json.dumps(error_payload, indent=2, sort_keys=True), file=sys.stderr)
        return 2

    parser.print_help()
    return 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manage local `cao-server` lifecycle using a schema-validated config.",
    )
    subparsers = parser.add_subparsers(dest="command")

    status_cmd = subparsers.add_parser("status", help="Probe `GET /health` only")
    _add_common_config_args(status_cmd)
    status_cmd.add_argument(
        "--status-timeout-seconds",
        type=float,
        default=3.0,
        help="Health request timeout (seconds).",
    )

    start_cmd = subparsers.add_parser(
        "start", help="Start local `cao-server` or reuse existing healthy server"
    )
    _add_common_config_args(start_cmd)
    start_cmd.add_argument(
        "--status-timeout-seconds",
        type=float,
        default=3.0,
        help="Health request timeout for each startup probe (seconds).",
    )
    start_cmd.add_argument(
        "--poll-interval-seconds",
        type=float,
        default=0.2,
        help="Polling interval while waiting for startup.",
    )

    stop_cmd = subparsers.add_parser("stop", help="Stop pidfile-tracked `cao-server`")
    _add_common_config_args(stop_cmd)
    stop_cmd.add_argument(
        "--grace-period-seconds",
        type=float,
        default=10.0,
        help="Grace period after SIGTERM before SIGKILL fallback.",
    )
    stop_cmd.add_argument(
        "--poll-interval-seconds",
        type=float,
        default=0.2,
        help="Polling interval while waiting for exit.",
    )

    return parser


def _add_common_config_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Path to launcher TOML config file.",
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help=(
            "Optional base_url override "
            "(supported loopback URLs: http://localhost:<port> or http://127.0.0.1:<port>)."
        ),
    )
    parser.add_argument(
        "--runtime-root",
        type=Path,
        default=None,
        help="Optional runtime_root override.",
    )
    parser.add_argument(
        "--home-dir",
        type=Path,
        default=None,
        help="Optional home_dir override (absolute path).",
    )
    parser.add_argument(
        "--proxy-policy",
        choices=[policy.value for policy in ProxyPolicy],
        default=None,
        help="Optional proxy policy override.",
    )
    parser.add_argument(
        "--startup-timeout-seconds",
        type=float,
        default=None,
        help="Optional startup timeout override.",
    )


def _build_overrides(args: argparse.Namespace) -> CaoServerLauncherConfigOverrides:
    proxy_policy = ProxyPolicy(args.proxy_policy) if args.proxy_policy else None
    return CaoServerLauncherConfigOverrides(
        base_url=args.base_url,
        runtime_root=args.runtime_root,
        home_dir=args.home_dir,
        proxy_policy=proxy_policy,
        startup_timeout_seconds=args.startup_timeout_seconds,
    )


def _load_config(args: argparse.Namespace) -> CaoServerLauncherConfig:
    return load_cao_server_launcher_config(
        args.config,
        overrides=_build_overrides(args),
    )


def _cmd_status(args: argparse.Namespace) -> CaoServerStatusResult:
    config = _load_config(args)
    return status_cao_server(config, timeout_seconds=float(args.status_timeout_seconds))


def _cmd_start(args: argparse.Namespace) -> CaoServerStartResult:
    config = _load_config(args)
    return start_cao_server(
        config,
        status_timeout_seconds=float(args.status_timeout_seconds),
        poll_interval_seconds=float(args.poll_interval_seconds),
    )


def _cmd_stop(args: argparse.Namespace) -> CaoServerStopResult:
    config = _load_config(args)
    return stop_cao_server(
        config,
        grace_period_seconds=float(args.grace_period_seconds),
        poll_interval_seconds=float(args.poll_interval_seconds),
    )


if __name__ == "__main__":
    raise SystemExit(main())
