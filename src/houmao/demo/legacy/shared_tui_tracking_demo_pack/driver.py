"""Standalone driver for the shared tracked-TUI demo pack."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

from .config import resolve_demo_config
from .live_watch import inspect_live_watch, run_dashboard, start_live_watch, stop_live_watch
from .ownership import cleanup_demo_run
from .recorded import run_recorded_capture, validate_fixture_corpus, validate_recorded_fixture
from .scenario import load_scenario
from .sweep import run_recorded_sweep

_TRACKER_LOG_LEVEL_ENV_VAR = "HOUMAO_SHARED_TUI_TRACKING_LOG_LEVEL"
_DEBUG_LOGGER_PREFIXES = (
    "houmao.shared_tui_tracking",
    "houmao.demo.legacy.shared_tui_tracking_demo_pack",
)


def _removed_fixture_root_error() -> str:
    """Return the archived-demo guard message for this entry point."""

    return (
        "Archived demo `shared_tui_tracking_demo_pack` is not runnable. "
        "This legacy workflow depends on the removed `tests/fixtures/agents/` "
        "fixture-root contract. Use the maintained "
        "`scripts/demo/shared-tui-tracking-demo-pack/` surface instead."
    )


def main(argv: list[str] | None = None) -> int:
    """Run the tracked-TUI demo pack driver."""

    _configure_logging_from_env()
    parser = _build_parser()
    args = parser.parse_args(argv or sys.argv[1:])
    try:
        raise RuntimeError(_removed_fixture_root_error())
        if args.command == "recorded-capture":
            scenario = load_scenario(_resolve_path(args.scenario))
            demo_config = resolve_demo_config(
                repo_root=_repo_root(),
                config_path=_optional_path(args.demo_config),
                profile_name=args.profile,
                scenario_id=scenario.scenario_id,
                cli_overrides=_demo_config_cli_overrides(
                    tool=scenario.tool,
                    recipe_path=args.recipe,
                    sample_interval_seconds=args.sample_interval_seconds,
                    runtime_observer_interval_seconds=args.runtime_observer_interval_seconds,
                    settle_seconds=args.settle_seconds,
                    ready_timeout_seconds=args.ready_timeout_seconds,
                ),
            )
            capture_result = run_recorded_capture(
                repo_root=_repo_root(),
                scenario=scenario,
                demo_config=demo_config,
                output_root=_optional_path(args.output_root),
                cleanup_session=demo_config.evidence.cleanup_session and not args.keep_session,
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
            demo_config = resolve_demo_config(
                repo_root=_repo_root(),
                config_path=_optional_path(args.demo_config),
                profile_name=args.profile,
                cli_overrides=_demo_config_cli_overrides(
                    review_video_fps=args.review_video_fps,
                    settle_seconds=args.settle_seconds,
                ),
            )
            validation_result = validate_recorded_fixture(
                repo_root=_repo_root(),
                demo_config=demo_config,
                fixture_root=_resolve_path(args.fixture_root),
                output_root=_optional_path(args.output_root),
                tool=args.tool,
                observed_version=args.observed_version,
                settle_seconds=args.settle_seconds,
                labels_path=_optional_path(args.labels_path),
                render_review_video=not args.skip_video,
                review_video_fps=args.review_video_fps,
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
            demo_config = resolve_demo_config(
                repo_root=_repo_root(),
                config_path=_optional_path(args.demo_config),
                profile_name=args.profile,
                cli_overrides=_demo_config_cli_overrides(review_video_fps=args.review_video_fps),
            )
            validation_results = validate_fixture_corpus(
                repo_root=_repo_root(),
                demo_config=demo_config,
                fixtures_root=(
                    _resolve_path(args.fixtures_root)
                    if args.fixtures_root is not None
                    else demo_config.fixtures_root_path()
                ),
                output_root=_optional_path(args.output_root),
                render_review_video=not args.skip_video,
                review_video_fps=args.review_video_fps,
            )
            _emit_payload(
                {
                    "result_count": len(validation_results),
                    "run_roots": [str(item.run_root) for item in validation_results],
                },
                json_output=bool(args.json),
            )
            return 0
        if args.command == "recorded-sweep":
            demo_config = resolve_demo_config(
                repo_root=_repo_root(),
                config_path=_optional_path(args.demo_config),
                profile_name=args.profile,
            )
            sweep_result = run_recorded_sweep(
                repo_root=_repo_root(),
                demo_config=demo_config,
                sweep_name=str(args.sweep),
                fixture_root=_resolve_path(args.fixture_root),
                output_root=_optional_path(args.output_root),
            )
            _emit_payload(
                {
                    "run_root": str(sweep_result.run_root),
                    "summary_path": str(sweep_result.summary_path),
                    "outcome_count": sweep_result.outcome_count,
                },
                json_output=bool(args.json),
            )
            return 0
        if args.command == "start":
            demo_config = resolve_demo_config(
                repo_root=_repo_root(),
                config_path=_optional_path(args.demo_config),
                profile_name=args.profile,
                cli_overrides=_demo_config_cli_overrides(
                    tool=args.tool,
                    recipe_path=args.recipe,
                    sample_interval_seconds=args.sample_interval_seconds,
                    runtime_observer_interval_seconds=args.runtime_observer_interval_seconds,
                    settle_seconds=args.settle_seconds,
                    live_watch_recorder_enabled=args.live_watch_recorder_enabled,
                ),
            )
            live_result = start_live_watch(
                repo_root=_repo_root(),
                demo_config=demo_config,
                tool=args.tool,
                output_root=_optional_path(args.output_root),
                recipe_path=_optional_path(args.recipe),
                sample_interval_seconds=demo_config.evidence.sample_interval_seconds,
                runtime_observer_interval_seconds=demo_config.evidence.runtime_observer_interval_seconds,
                settle_seconds=demo_config.semantics.settle_seconds,
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
            demo_config = resolve_demo_config(
                repo_root=_repo_root(),
                config_path=_optional_path(args.demo_config),
                profile_name=args.profile,
            )
            inspect_payload = inspect_live_watch(
                repo_root=_repo_root(),
                demo_config=demo_config,
                run_root=_optional_path(args.run_root),
            )
            _emit_payload(inspect_payload, json_output=bool(args.json))
            return 0
        if args.command == "stop":
            demo_config = resolve_demo_config(
                repo_root=_repo_root(),
                config_path=_optional_path(args.demo_config),
                profile_name=args.profile,
            )
            stop_payload = stop_live_watch(
                repo_root=_repo_root(),
                demo_config=demo_config,
                run_root=_optional_path(args.run_root),
                stop_reason=str(args.reason),
            )
            _emit_payload(stop_payload, json_output=bool(args.json))
            return 0
        if args.command == "cleanup":
            demo_config = resolve_demo_config(
                repo_root=_repo_root(),
                config_path=_optional_path(args.demo_config),
                profile_name=args.profile,
            )
            cleanup_payload = cleanup_demo_run(
                demo_config=demo_config,
                run_root=_optional_path(args.run_root),
            )
            _emit_payload(cleanup_payload, json_output=bool(args.json))
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
    capture.add_argument("--demo-config")
    capture.add_argument("--profile")
    capture.add_argument("--output-root")
    capture.add_argument("--recipe")
    capture.add_argument("--sample-interval-seconds", type=float, default=None)
    capture.add_argument("--runtime-observer-interval-seconds", type=float, default=None)
    capture.add_argument("--settle-seconds", type=float, default=None)
    capture.add_argument("--ready-timeout-seconds", type=float, default=None)
    capture.add_argument("--keep-session", action="store_true")
    capture.add_argument("--json", action="store_true")

    validate = subparsers.add_parser(
        "recorded-validate",
        help="Replay one recorded fixture and compare against labels",
    )
    validate.add_argument("--fixture-root", required=True)
    validate.add_argument("--demo-config")
    validate.add_argument("--profile")
    validate.add_argument("--output-root")
    validate.add_argument("--tool", choices=["claude", "codex"], default=None)
    validate.add_argument("--observed-version", default=None)
    validate.add_argument("--settle-seconds", type=float, default=None)
    validate.add_argument("--labels-path", default=None)
    validate.add_argument("--review-video-fps", type=float, default=None)
    validate.add_argument("--skip-video", action="store_true")
    validate.add_argument("--json", action="store_true")

    validate_corpus = subparsers.add_parser(
        "recorded-validate-corpus",
        help="Validate every committed fixture in one corpus root",
    )
    validate_corpus.add_argument("--demo-config")
    validate_corpus.add_argument("--profile")
    validate_corpus.add_argument("--fixtures-root")
    validate_corpus.add_argument("--output-root")
    validate_corpus.add_argument("--review-video-fps", type=float, default=None)
    validate_corpus.add_argument("--skip-video", action="store_true")
    validate_corpus.add_argument("--json", action="store_true")

    sweep = subparsers.add_parser(
        "recorded-sweep",
        help="Run one config-defined capture-frequency sweep on a recorded fixture",
    )
    sweep.add_argument("--fixture-root", required=True)
    sweep.add_argument("--sweep", required=True)
    sweep.add_argument("--demo-config")
    sweep.add_argument("--profile")
    sweep.add_argument("--output-root")
    sweep.add_argument("--json", action="store_true")

    start = subparsers.add_parser("start", help="Start one live watch run")
    start.add_argument("--tool", choices=["claude", "codex"], required=True)
    start.add_argument("--demo-config")
    start.add_argument("--profile")
    start.add_argument("--output-root")
    start.add_argument("--recipe")
    start.add_argument("--sample-interval-seconds", type=float, default=None)
    start.add_argument("--runtime-observer-interval-seconds", type=float, default=None)
    start.add_argument("--settle-seconds", type=float, default=None)
    recorder_group = start.add_mutually_exclusive_group()
    recorder_group.add_argument(
        "--with-recorder",
        dest="live_watch_recorder_enabled",
        action="store_true",
        help="Enable recorder-backed capture for replay debugging",
    )
    recorder_group.add_argument(
        "--without-recorder",
        dest="live_watch_recorder_enabled",
        action="store_false",
        help="Disable recorder-backed capture even if the selected config enables it",
    )
    start.set_defaults(live_watch_recorder_enabled=None)
    start.add_argument("--trace", action="store_true")
    start.add_argument("--json", action="store_true")

    inspect = subparsers.add_parser("inspect", help="Inspect one live watch run")
    inspect.add_argument("--demo-config")
    inspect.add_argument("--profile")
    inspect.add_argument("--run-root")
    inspect.add_argument("--json", action="store_true")

    stop = subparsers.add_parser("stop", help="Stop one live watch run")
    stop.add_argument("--demo-config")
    stop.add_argument("--profile")
    stop.add_argument("--run-root")
    stop.add_argument("--reason", default="operator_requested")
    stop.add_argument("--json", action="store_true")

    cleanup = subparsers.add_parser(
        "cleanup",
        help="Forcefully reap one demo run's owned tmux sessions",
    )
    cleanup.add_argument("--demo-config")
    cleanup.add_argument("--profile")
    cleanup.add_argument("--run-root")
    cleanup.add_argument("--json", action="store_true")

    dashboard = subparsers.add_parser("dashboard", help="Run the live dashboard loop")
    dashboard.add_argument("--run-root", required=True)
    return parser


def _configure_logging_from_env() -> None:
    """Enable targeted shared-TUI debug logs when the env requests them."""

    raw_level = os.environ.get(_TRACKER_LOG_LEVEL_ENV_VAR)
    if raw_level is None or not raw_level.strip():
        return
    level_name = raw_level.strip().upper()
    numeric_level = getattr(logging, level_name, None)
    if not isinstance(numeric_level, int):
        raise ValueError(
            f"invalid {_TRACKER_LOG_LEVEL_ENV_VAR} value `{raw_level}`; use a standard logging level"
        )
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    for logger_name in _DEBUG_LOGGER_PREFIXES:
        logging.getLogger(logger_name).setLevel(numeric_level)


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


def _demo_config_cli_overrides(
    *,
    tool: str | None = None,
    recipe_path: str | None = None,
    sample_interval_seconds: float | None = None,
    runtime_observer_interval_seconds: float | None = None,
    settle_seconds: float | None = None,
    ready_timeout_seconds: float | None = None,
    review_video_fps: float | None = None,
    live_watch_recorder_enabled: bool | None = None,
) -> dict[str, Any]:
    """Build a raw config-override mapping from CLI arguments."""

    overrides: dict[str, Any] = {}
    if tool is not None and recipe_path is not None:
        overrides.setdefault("tools", {}).setdefault(tool, {})["recipe_path"] = recipe_path
    if sample_interval_seconds is not None:
        overrides.setdefault("evidence", {})["sample_interval_seconds"] = sample_interval_seconds
    if runtime_observer_interval_seconds is not None:
        overrides.setdefault("evidence", {})["runtime_observer_interval_seconds"] = (
            runtime_observer_interval_seconds
        )
    if settle_seconds is not None:
        overrides.setdefault("semantics", {})["settle_seconds"] = settle_seconds
    if ready_timeout_seconds is not None:
        overrides.setdefault("evidence", {})["ready_timeout_seconds"] = ready_timeout_seconds
    if live_watch_recorder_enabled is not None:
        overrides.setdefault("evidence", {})["live_watch_recorder_enabled"] = (
            live_watch_recorder_enabled
        )
    if review_video_fps is not None:
        overrides.setdefault("presentation", {}).setdefault("review_video", {})[
            "match_capture_cadence"
        ] = False
        overrides.setdefault("presentation", {}).setdefault("review_video", {})["fps"] = (
            review_video_fps
        )
    return overrides
