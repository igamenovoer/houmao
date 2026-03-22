"""Standalone driver for the shared tracked-TUI demo pack."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .live_watch import inspect_live_watch, run_dashboard, start_live_watch, stop_live_watch
from .models import DEFAULT_REVIEW_VIDEO_FPS
from .recorded import run_recorded_capture, validate_fixture_corpus, validate_recorded_fixture
from .scenario import load_scenario


def main(argv: list[str] | None = None) -> int:
    """Run the tracked-TUI demo pack driver."""

    parser = _build_parser()
    args = parser.parse_args(argv or sys.argv[1:])
    try:
        if args.command == "recorded-capture":
            scenario = load_scenario(_resolve_path(args.scenario))
            capture_result = run_recorded_capture(
                repo_root=_repo_root(),
                scenario=scenario,
                output_root=_optional_path(args.output_root),
                cleanup_session=not args.keep_session,
            )
            _emit_payload(
                {
                    "run_root": str(capture_result.run_root),
                    "recording_root": str(capture_result.recording_root),
                    "scenario_id": capture_result.scenario_id,
                    "tool": capture_result.tool,
                    "observed_version": capture_result.observed_version,
                },
                json_output=bool(args.json),
            )
            return 0
        if args.command == "recorded-validate":
            validation_result = validate_recorded_fixture(
                repo_root=_repo_root(),
                fixture_root=_resolve_path(args.fixture_root),
                output_root=_optional_path(args.output_root),
                tool=args.tool,
                observed_version=args.observed_version,
                settle_seconds=args.settle_seconds,
                labels_path=_optional_path(args.labels_path),
                render_review_video=not args.skip_video,
                review_video_fps=int(args.review_video_fps),
            )
            _emit_payload(
                {
                    "run_root": str(validation_result.run_root),
                    "manifest": validation_result.manifest.to_payload(),
                    "comparison": validation_result.comparison.to_payload(),
                },
                json_output=bool(args.json),
            )
            return 0
        if args.command == "recorded-validate-corpus":
            validation_results = validate_fixture_corpus(
                repo_root=_repo_root(),
                fixtures_root=_resolve_path(args.fixtures_root),
                output_root=_optional_path(args.output_root),
                render_review_video=not args.skip_video,
                review_video_fps=int(args.review_video_fps),
            )
            _emit_payload(
                {
                    "result_count": len(validation_results),
                    "run_roots": [str(item.run_root) for item in validation_results],
                },
                json_output=bool(args.json),
            )
            return 0
        if args.command == "start":
            live_result = start_live_watch(
                repo_root=_repo_root(),
                tool=args.tool,
                output_root=_optional_path(args.output_root),
                recipe_path=_optional_path(args.recipe),
                sample_interval_seconds=float(args.sample_interval_seconds),
                settle_seconds=float(args.settle_seconds),
                trace_enabled=bool(args.trace),
            )
            _emit_payload(
                {
                    "run_root": str(live_result.run_root),
                    "runtime_root": live_result.manifest.runtime_root,
                    "brain_home_path": live_result.manifest.brain_home_path,
                    "brain_manifest_path": live_result.manifest.brain_manifest_path,
                    "tool_attach_command": live_result.manifest.tool_attach_command,
                    "dashboard_attach_command": live_result.manifest.dashboard_attach_command,
                },
                json_output=bool(args.json),
            )
            return 0
        if args.command == "inspect":
            inspect_payload = inspect_live_watch(
                repo_root=_repo_root(),
                run_root=_optional_path(args.run_root),
            )
            _emit_payload(inspect_payload, json_output=bool(args.json))
            return 0
        if args.command == "stop":
            stop_payload = stop_live_watch(
                repo_root=_repo_root(),
                run_root=_optional_path(args.run_root),
                stop_reason=str(args.reason),
            )
            _emit_payload(stop_payload, json_output=bool(args.json))
            return 0
        if args.command == "dashboard":
            return run_dashboard(run_root=_resolve_path(args.run_root))
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    parser.print_help()
    return 1


def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""

    parser = argparse.ArgumentParser(description="Shared tracked-TUI demo pack")
    subparsers = parser.add_subparsers(dest="command", required=True)

    capture = subparsers.add_parser("recorded-capture", help="Capture one real recorded session")
    capture.add_argument("--scenario", required=True)
    capture.add_argument("--output-root")
    capture.add_argument("--keep-session", action="store_true")
    capture.add_argument("--json", action="store_true")

    validate = subparsers.add_parser(
        "recorded-validate",
        help="Replay one recorded fixture and compare against labels",
    )
    validate.add_argument("--fixture-root", required=True)
    validate.add_argument("--output-root")
    validate.add_argument("--tool", choices=["claude", "codex"], default=None)
    validate.add_argument("--observed-version", default=None)
    validate.add_argument("--settle-seconds", type=float, default=None)
    validate.add_argument("--labels-path", default=None)
    validate.add_argument("--review-video-fps", type=int, default=DEFAULT_REVIEW_VIDEO_FPS)
    validate.add_argument("--skip-video", action="store_true")
    validate.add_argument("--json", action="store_true")

    validate_corpus = subparsers.add_parser(
        "recorded-validate-corpus",
        help="Validate every committed fixture in one corpus root",
    )
    validate_corpus.add_argument(
        "--fixtures-root",
        default="tests/fixtures/shared_tui_tracking/recorded",
    )
    validate_corpus.add_argument("--output-root")
    validate_corpus.add_argument("--review-video-fps", type=int, default=DEFAULT_REVIEW_VIDEO_FPS)
    validate_corpus.add_argument("--skip-video", action="store_true")
    validate_corpus.add_argument("--json", action="store_true")

    start = subparsers.add_parser("start", help="Start one live watch run")
    start.add_argument("--tool", choices=["claude", "codex"], required=True)
    start.add_argument("--output-root")
    start.add_argument("--recipe")
    start.add_argument("--sample-interval-seconds", type=float, default=0.25)
    start.add_argument("--settle-seconds", type=float, default=1.0)
    start.add_argument("--trace", action="store_true")
    start.add_argument("--json", action="store_true")

    inspect = subparsers.add_parser("inspect", help="Inspect one live watch run")
    inspect.add_argument("--run-root")
    inspect.add_argument("--json", action="store_true")

    stop = subparsers.add_parser("stop", help="Stop one live watch run")
    stop.add_argument("--run-root")
    stop.add_argument("--reason", default="operator_requested")
    stop.add_argument("--json", action="store_true")

    dashboard = subparsers.add_parser("dashboard", help="Run the live dashboard loop")
    dashboard.add_argument("--run-root", required=True)
    return parser


def _repo_root() -> Path:
    """Return the repository root from this module location."""

    return Path(__file__).resolve().parents[4]


def _resolve_path(value: str | Path) -> Path:
    """Resolve one mandatory filesystem path."""

    return Path(value).expanduser().resolve()


def _optional_path(value: str | None) -> Path | None:
    """Resolve one optional filesystem path."""

    if value is None:
        return None
    return _resolve_path(value)


def _emit_payload(payload: dict[str, Any], *, json_output: bool) -> None:
    """Emit one payload to stdout."""

    if json_output:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    run_root = payload.get("run_root")
    if isinstance(run_root, str):
        print(run_root)
        return
    print(json.dumps(payload, indent=2, sort_keys=True))
