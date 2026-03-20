"""CLI entrypoint for the Claude Code state-tracking explore harness."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from houmao.explore.claude_code_state_tracking.compare import compare_timelines
from houmao.explore.claude_code_state_tracking.groundtruth import classify_groundtruth
from houmao.explore.claude_code_state_tracking.interactive_watch import (
    inspect_interactive_watch,
    run_dashboard,
    start_interactive_watch,
    stop_interactive_watch,
)
from houmao.explore.claude_code_state_tracking.live import run_live_capture
from houmao.explore.claude_code_state_tracking.models import (
    HarnessPaths,
    RecordedInputEvent,
    RecordedObservation,
    RuntimeObservation,
    load_ndjson,
    load_runtime_observations,
    load_timeline,
    overwrite_ndjson,
    save_json,
)
from houmao.explore.claude_code_state_tracking.replay import replay_timeline
from houmao.explore.claude_code_state_tracking.scenario import load_scenario


def main(argv: list[str] | None = None) -> int:
    """Run the explore harness CLI."""

    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "capture":
        scenario_path = _resolve_scenario_path(Path(args.scenario))
        scenario = load_scenario(scenario_path)
        result = run_live_capture(
            repo_root=_repo_root(),
            scenario=scenario,
            output_root=Path(args.output_root).expanduser().resolve() if args.output_root else None,
            cleanup_session=not args.keep_session,
        )
        print(result.run_root)
        return 0
    if args.command == "replay":
        run_root = Path(args.run_root).expanduser().resolve()
        _run_replay_workflow(
            recording_root=Path(args.recording_root).expanduser().resolve()
            if args.recording_root
            else None,
            run_root=run_root,
            observed_version=args.observed_version,
            settle_seconds=float(args.settle_seconds),
        )
        print(run_root)
        return 0
    if args.command == "compare":
        paths = HarnessPaths.from_run_root(run_root=Path(args.run_root).expanduser().resolve())
        groundtruth = load_timeline(paths.groundtruth_timeline_path)
        replay = load_timeline(paths.replay_timeline_path)
        comparison, markdown = compare_timelines(groundtruth=groundtruth, replay=replay)
        save_json(paths.comparison_json_path, comparison.to_payload())
        paths.comparison_markdown_path.write_text(markdown, encoding="utf-8")
        print(paths.comparison_json_path)
        return 0
    if args.command == "run":
        scenario_path = _resolve_scenario_path(Path(args.scenario))
        scenario = load_scenario(scenario_path)
        result = run_live_capture(
            repo_root=_repo_root(),
            scenario=scenario,
            output_root=Path(args.output_root).expanduser().resolve() if args.output_root else None,
            cleanup_session=not args.keep_session,
        )
        _run_replay_workflow(
            recording_root=result.terminal_record_run_root,
            run_root=result.run_root,
            observed_version=result.observed_version,
            settle_seconds=scenario.launch.settle_seconds,
        )
        print(result.run_root)
        return 0
    if args.command == "signal-note-init":
        output_path = Path(args.output_path).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            _signal_note_template(slug=args.slug, observed_version=args.observed_version),
            encoding="utf-8",
        )
        print(output_path)
        return 0
    if args.command == "start":
        result = start_interactive_watch(
            repo_root=_repo_root(),
            output_root=Path(args.output_root).expanduser().resolve() if args.output_root else None,
            recipe_path=Path(args.recipe).expanduser().resolve() if args.recipe else None,
            sample_interval_seconds=float(args.sample_interval_seconds),
            settle_seconds=float(args.settle_seconds),
            trace_enabled=bool(args.trace),
        )
        payload = {
            "run_root": str(result.run_root),
            "runtime_root": result.manifest.runtime_root,
            "brain_home_path": result.manifest.brain_home_path,
            "brain_manifest_path": result.manifest.brain_manifest_path,
            "claude_attach_command": result.manifest.claude_attach_command,
            "dashboard_attach_command": result.manifest.dashboard_attach_command,
        }
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(result.run_root)
        return 0
    if args.command == "inspect":
        payload = inspect_interactive_watch(
            repo_root=_repo_root(),
            run_root=Path(args.run_root).expanduser().resolve() if args.run_root else None,
        )
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(payload["run_root"])
        return 0
    if args.command == "stop":
        payload = stop_interactive_watch(
            repo_root=_repo_root(),
            run_root=Path(args.run_root).expanduser().resolve() if args.run_root else None,
            stop_reason=str(args.reason),
        )
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(payload["report_path"])
        return 0
    if args.command == "dashboard":
        return run_dashboard(run_root=Path(args.run_root).expanduser().resolve())
    raise ValueError(f"Unsupported command: {args.command}")


def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""

    parser = argparse.ArgumentParser(description="Claude Code state-tracking explore harness")
    subparsers = parser.add_subparsers(dest="command", required=True)

    capture = subparsers.add_parser("capture", help="Capture one live Claude scenario")
    capture.add_argument("--scenario", required=True)
    capture.add_argument("--output-root")
    capture.add_argument("--keep-session", action="store_true")

    replay = subparsers.add_parser("replay", help="Replay one recorded run into timelines")
    replay.add_argument("--run-root", required=True)
    replay.add_argument("--recording-root")
    replay.add_argument("--observed-version")
    replay.add_argument("--settle-seconds", type=float, default=1.0)

    compare = subparsers.add_parser("compare", help="Compare existing timelines")
    compare.add_argument("--run-root", required=True)

    run = subparsers.add_parser("run", help="Capture and replay one live scenario")
    run.add_argument("--scenario", required=True)
    run.add_argument("--output-root")
    run.add_argument("--keep-session", action="store_true")

    signal_note = subparsers.add_parser("signal-note-init", help="Create one signal-note template")
    signal_note.add_argument("--slug", required=True)
    signal_note.add_argument("--output-path", required=True)
    signal_note.add_argument("--observed-version", default="2.1.80 (Claude Code)")

    start = subparsers.add_parser("start", help="Start one interactive Claude watch run")
    start.add_argument("--output-root")
    start.add_argument("--recipe")
    start.add_argument("--sample-interval-seconds", type=float, default=0.25)
    start.add_argument("--settle-seconds", type=float, default=1.0)
    start.add_argument("--trace", action="store_true")
    start.add_argument("--json", action="store_true")

    inspect = subparsers.add_parser("inspect", help="Inspect one interactive watch run")
    inspect.add_argument("--run-root")
    inspect.add_argument("--json", action="store_true")

    stop = subparsers.add_parser("stop", help="Stop one interactive watch run")
    stop.add_argument("--run-root")
    stop.add_argument("--reason", default="operator_requested")
    stop.add_argument("--json", action="store_true")

    dashboard = subparsers.add_parser("dashboard", help="Run the interactive watch dashboard loop")
    dashboard.add_argument("--run-root", required=True)
    return parser


def _run_replay_workflow(
    *,
    recording_root: Path | None,
    run_root: Path,
    observed_version: str | None,
    settle_seconds: float,
) -> None:
    """Run groundtruth, replay, and comparison for one capture root."""

    paths = HarnessPaths.from_run_root(run_root=run_root)
    source_root = recording_root or paths.terminal_record_run_root
    observations = _load_recorded_observations(
        recording_root=source_root,
        runtime_path=paths.runtime_observations_path,
    )
    groundtruth = classify_groundtruth(
        observations=observations,
        observed_version=observed_version,
        settle_seconds=settle_seconds,
    )
    input_events = _load_recorded_input_events(recording_root=source_root)
    replay, replay_events = replay_timeline(
        observations=observations,
        observed_version=observed_version,
        settle_seconds=settle_seconds,
        input_events=input_events,
    )
    overwrite_ndjson(paths.groundtruth_timeline_path, [item.to_payload() for item in groundtruth])
    overwrite_ndjson(paths.replay_timeline_path, [item.to_payload() for item in replay])
    overwrite_ndjson(paths.replay_events_path, [item.to_payload() for item in replay_events])
    comparison, markdown = compare_timelines(groundtruth=groundtruth, replay=replay)
    save_json(paths.comparison_json_path, comparison.to_payload())
    paths.comparison_markdown_path.write_text(markdown, encoding="utf-8")


def _load_recorded_observations(
    *, recording_root: Path, runtime_path: Path
) -> list[RecordedObservation]:
    """Load and align pane snapshots with runtime observations."""

    runtime_rows = load_runtime_observations(runtime_path)
    snapshot_payloads = load_ndjson(recording_root / "pane_snapshots.ndjson")
    observations: list[RecordedObservation] = []
    runtime_index = 0
    for payload in snapshot_payloads:
        elapsed_seconds = float(payload["elapsed_seconds"])
        matched_runtime: RuntimeObservation | None = None
        while (
            runtime_index < len(runtime_rows)
            and runtime_rows[runtime_index].elapsed_seconds <= elapsed_seconds
        ):
            matched_runtime = runtime_rows[runtime_index]
            runtime_index += 1
        observations.append(
            RecordedObservation(
                sample_id=str(payload["sample_id"]),
                elapsed_seconds=elapsed_seconds,
                ts_utc=str(payload["ts_utc"]),
                output_text=str(payload["output_text"]),
                runtime=matched_runtime,
            )
        )
    return observations


def _load_recorded_input_events(*, recording_root: Path) -> list[RecordedInputEvent]:
    """Load structured input events captured with one terminal-record run."""

    input_path = recording_root / "input_events.ndjson"
    events: list[RecordedInputEvent] = []
    for payload in load_ndjson(input_path):
        events.append(
            RecordedInputEvent(
                event_id=str(payload["event_id"]),
                elapsed_seconds=float(payload["elapsed_seconds"]),
                ts_utc=str(payload["ts_utc"]),
                source=str(payload.get("source", "unknown")),
            )
        )
    return events


def _resolve_scenario_path(path: Path) -> Path:
    """Resolve one scenario name or path into a JSON file path."""

    if path.is_file():
        return path.resolve()
    candidate = (
        _repo_root()
        / "scripts"
        / "explore"
        / "claude-code-state-tracking"
        / "scenarios"
        / f"{path.name}.json"
    )
    if candidate.is_file():
        return candidate.resolve()
    raise FileNotFoundError(f"Scenario not found: {path}")


def _repo_root() -> Path:
    """Return the repository root from this module location."""

    return Path(__file__).resolve().parents[4]


def _signal_note_template(*, slug: str, observed_version: str) -> str:
    """Return a state-discovery signal note template."""

    title = slug.replace("-", " ").title()
    return (
        "\n".join(
            [
                f"# {title}",
                "",
                "## Context",
                "",
                "- Tool: Claude Code",
                f"- Observed version: `{observed_version}`",
                "- Primary artifacts:",
                "  - `<artifact-path>`",
                "",
                "## Classification",
                "",
                "- Supported state or outcome: `<turn_active|turn_success|turn_interrupted|turn_known_failure|turn_unknown>`",
                "",
                "## Required Conditions",
                "",
                "1. `<condition>`",
                "2. `<condition>`",
                "",
                "## Non-Match Guidance",
                "",
                "- `<non-match>`",
                "",
                "## Example Surface",
                "",
                "```text",
                "<captured surface>",
                "```",
                "",
            ]
        )
        + "\n"
    )
