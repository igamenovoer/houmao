"""Legacy CLI shim for the moved Houmao-server agent API demo pack."""

from __future__ import annotations

import argparse
from pathlib import Path

from houmao_server_agent_api_live_suite.suite import LANE_IDS, SuiteConfig, SuiteError, run_suite


def build_parser() -> argparse.ArgumentParser:
    """Build the legacy manual-shim CLI parser."""

    parser = argparse.ArgumentParser(
        description=(
            "Compatibility shim for the moved houmao-server managed-agent API "
            "demo pack. Prefer scripts/demo/houmao-server-agent-api-demo-pack/."
        )
    )
    parser.add_argument(
        "--lane",
        action="append",
        choices=LANE_IDS,
        default=[],
        help=("Repeat to run a subset of lanes. When omitted, the suite runs all supported lanes."),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=None,
        help=(
            "Override the demo-pack run root. When omitted, the compatibility "
            "shim writes under scripts/demo/houmao-server-agent-api-demo-pack/outputs/runs/."
        ),
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Explicit loopback port for the suite-owned houmao-server.",
    )
    parser.add_argument(
        "--compat-http-timeout-seconds",
        type=float,
        default=20.0,
        help="HTTP timeout used by the suite-owned Houmao server client.",
    )
    parser.add_argument(
        "--compat-create-timeout-seconds",
        type=float,
        default=90.0,
        help="Client-side create timeout budget used for CAO-compatible TUI lane creation.",
    )
    parser.add_argument(
        "--compat-provider-ready-timeout-seconds",
        type=float,
        default=90.0,
        help=(
            "Server-side compatibility provider-ready timeout passed to "
            "`houmao-server serve` for TUI provisioning."
        ),
    )
    parser.add_argument(
        "--health-timeout-seconds",
        type=float,
        default=30.0,
        help="Timeout for suite-owned houmao-server readiness checks.",
    )
    parser.add_argument(
        "--prompt-timeout-seconds",
        type=float,
        default=120.0,
        help="Timeout for post-request polling and headless turn completion checks.",
    )
    parser.add_argument(
        "--prompt-poll-interval-seconds",
        type=float,
        default=2.0,
        help="Polling interval used while waiting for prompt-related state changes.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the legacy manual shim and return the process exit code."""

    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        summary = run_suite(
            SuiteConfig(
                selected_lane_ids=tuple(args.lane),
                output_root=args.output_root.resolve() if args.output_root is not None else None,
                port=args.port,
                compat_http_timeout_seconds=float(args.compat_http_timeout_seconds),
                compat_create_timeout_seconds=float(args.compat_create_timeout_seconds),
                compat_provider_ready_timeout_seconds=float(
                    args.compat_provider_ready_timeout_seconds
                ),
                health_timeout_seconds=float(args.health_timeout_seconds),
                prompt_timeout_seconds=float(args.prompt_timeout_seconds),
                prompt_poll_interval_seconds=float(args.prompt_poll_interval_seconds),
            )
        )
    except SuiteError as exc:
        print("manual-houmao-server-agent-api-live-suite=FAIL")
        print(str(exc))
        return 1

    print(
        "manual-houmao-server-agent-api-live-suite=DEPRECATED "
        "(canonical path: scripts/demo/houmao-server-agent-api-demo-pack/run_demo.sh auto)"
    )
    print("manual-houmao-server-agent-api-live-suite=PASS")
    print(f"run_root={summary['run_root']}")
    print(f"selected_lanes={','.join(summary['selected_lanes'])}")
    return 0
