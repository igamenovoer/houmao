"""Capture-frequency sweep workflow for recorded tracked-TUI fixtures."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from houmao.shared_tui_tracking.models import (
    RecordedObservation,
    TrackedLastTurnResult,
    TrackedTimelineState,
)
from houmao.shared_tui_tracking.reducer import replay_timeline
from houmao.terminal_record.models import TerminalRecordManifest, load_manifest

from .config import ResolvedDemoConfig, SweepContractConfig, SweepStateLabel
from .groundtruth import load_fixture_inputs
from .models import (
    DEMO_PACK_SCHEMA_VERSION,
    RecordedFixtureManifest,
    RecordedSweepPaths,
    ToolName,
    ensure_directory_layout,
    load_input_events,
    overwrite_ndjson,
    save_json,
)
from .reporting import IssueNote, write_issue_documents
from .tooling import now_utc_iso


_FIXTURE_MANIFEST_NAME = "fixture_manifest.json"


@dataclass(frozen=True)
class SweepVariantOutcome:
    """Contract-evaluation result for one sweep variant."""

    variant_name: str
    sample_interval_seconds: float
    sample_count: int
    transition_labels: tuple[SweepStateLabel, ...]
    required_labels: tuple[SweepStateLabel, ...]
    missing_labels: tuple[SweepStateLabel, ...]
    order_matches: bool
    actual_terminal_result: TrackedLastTurnResult
    required_terminal_result: TrackedLastTurnResult | None
    forbidden_terminal_results: tuple[TrackedLastTurnResult, ...]
    drift_exceeded_labels: tuple[SweepStateLabel, ...]
    drift_by_label_seconds: dict[str, float]
    skipped_reason: str | None
    passed: bool

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-serializable payload."""

        return asdict(self)


@dataclass(frozen=True)
class RecordedSweepResult:
    """Summary of one completed recorded sweep."""

    run_root: Path
    summary_path: Path
    outcome_count: int


def run_recorded_sweep(
    *,
    repo_root: Path,
    demo_config: ResolvedDemoConfig,
    sweep_name: str,
    fixture_root: Path,
    output_root: Path | None,
) -> RecordedSweepResult:
    """Run one config-defined capture-frequency sweep on a recorded fixture."""

    if sweep_name not in demo_config.sweeps:
        raise ValueError(f"Unknown demo-config sweep: {sweep_name}")
    sweep = demo_config.sweeps[sweep_name]
    effective_fixture_root = fixture_root.expanduser().resolve()
    fixture_manifest = _load_fixture_manifest(effective_fixture_root)
    case_id = fixture_manifest.case_id if fixture_manifest is not None else effective_fixture_root.name
    if case_id not in sweep.contracts:
        raise ValueError(
            f"Sweep `{sweep_name}` does not define a contract for case `{case_id}`"
        )
    tool = fixture_manifest.tool if fixture_manifest is not None else _infer_tool_from_path(effective_fixture_root)
    settle_seconds = (
        fixture_manifest.settle_seconds
        if fixture_manifest is not None
        else demo_config.semantics.settle_seconds
    )
    observed_version = fixture_manifest.observed_version if fixture_manifest is not None else None
    run_root = _resolve_sweep_run_root(
        repo_root=repo_root,
        demo_config=demo_config,
        sweep_name=sweep_name,
        case_id=case_id,
        output_root=output_root,
    )
    if run_root.exists():
        raise RuntimeError(f"Run root already exists: {run_root}")
    paths = RecordedSweepPaths.from_run_root(run_root=run_root)
    ensure_directory_layout(paths)
    save_json(paths.resolved_config_path, demo_config.to_payload())

    recording_root = _resolve_recording_root(effective_fixture_root)
    recorder_manifest = _load_recorder_manifest(recording_root)
    source_sample_interval_seconds = (
        recorder_manifest.sample_interval_seconds
        if recorder_manifest is not None
        else demo_config.evidence.sample_interval_seconds
    )
    runtime_path = effective_fixture_root / "runtime_observations.ndjson"
    fixture_inputs = load_fixture_inputs(
        recording_root=recording_root,
        runtime_observations_path=runtime_path if runtime_path.is_file() else None,
    )
    input_events = load_input_events(recording_root / "input_events.ndjson")
    save_json(
        paths.manifest_path,
        {
            "schema_version": DEMO_PACK_SCHEMA_VERSION,
            "run_id": run_root.name,
            "sweep_name": sweep_name,
            "repo_root": str(repo_root.resolve()),
            "run_root": str(run_root),
            "fixture_root": str(effective_fixture_root),
            "recording_root": str(recording_root),
            "case_id": case_id,
            "tool": tool,
            "observed_version": observed_version,
            "settle_seconds": settle_seconds,
            "source_sample_interval_seconds": source_sample_interval_seconds,
            "resolved_config_path": str(paths.resolved_config_path),
            "started_at_utc": now_utc_iso(),
        },
    )

    variant_timelines: dict[str, list[TrackedTimelineState]] = {}
    variant_outcomes: list[SweepVariantOutcome] = []
    contract = sweep.contracts[case_id]
    baseline_variant_name = sweep.baseline_variant or sweep.variants[0].name
    baseline_first_occurrence: dict[SweepStateLabel, float] | None = None

    for variant in sweep.variants:
        target_interval = (
            source_sample_interval_seconds
            if variant.uses_source_cadence
            else _require_sample_interval(variant.sample_interval_seconds)
        )
        variant_dir = paths.variants_dir / variant.name
        variant_dir.mkdir(parents=True, exist_ok=True)
        skipped_reason: str | None = None
        if target_interval + 1e-9 < source_sample_interval_seconds:
            skipped_reason = (
                "target cadence is faster than the source recording cadence and cannot be synthesized"
            )
            outcome = SweepVariantOutcome(
                variant_name=variant.name,
                sample_interval_seconds=target_interval,
                sample_count=0,
                transition_labels=(),
                required_labels=contract.required_labels,
                missing_labels=contract.required_labels,
                order_matches=False,
                actual_terminal_result="none",
                required_terminal_result=contract.required_terminal_result,
                forbidden_terminal_results=contract.forbidden_terminal_results,
                drift_exceeded_labels=(),
                drift_by_label_seconds={},
                skipped_reason=skipped_reason,
                passed=False,
            )
            save_json(variant_dir / "verdict.json", outcome.to_payload())
            variant_outcomes.append(outcome)
            continue

        observations = _downsample_observations(
            observations=fixture_inputs.observations,
            target_interval_seconds=target_interval,
        )
        replay_timeline_rows, replay_events = replay_timeline(
            observations=observations,
            tool=tool,
            observed_version=observed_version,
            settle_seconds=settle_seconds,
            input_events=input_events,
        )
        overwrite_ndjson(
            variant_dir / "replay_timeline.ndjson",
            [item.to_payload() for item in replay_timeline_rows],
        )
        overwrite_ndjson(
            variant_dir / "replay_events.ndjson",
            [item.to_payload() for item in replay_events],
        )
        variant_timelines[variant.name] = replay_timeline_rows
        if variant.name == baseline_variant_name and baseline_first_occurrence is None:
            baseline_first_occurrence = _first_occurrence_times(replay_timeline_rows)

    if baseline_first_occurrence is None:
        raise RuntimeError(f"Baseline sweep variant `{baseline_variant_name}` did not produce a replay timeline")

    for variant in sweep.variants:
        variant_dir = paths.variants_dir / variant.name
        existing_verdict = variant_dir / "verdict.json"
        if existing_verdict.is_file():
            continue
        replay_timeline_rows = variant_timelines[variant.name]
        outcome = _evaluate_variant(
            variant_name=variant.name,
            sample_interval_seconds=(
                source_sample_interval_seconds
                if variant.uses_source_cadence
                else _require_sample_interval(variant.sample_interval_seconds)
            ),
            timeline=replay_timeline_rows,
            contract=contract,
            baseline_first_occurrence=baseline_first_occurrence,
        )
        save_json(existing_verdict, outcome.to_payload())
        variant_outcomes.append(outcome)

    variant_outcomes.sort(key=lambda item: item.sample_interval_seconds)
    save_json(
        paths.summary_json_path,
        {"variants": [item.to_payload() for item in variant_outcomes]},
    )
    issues = _build_sweep_issues(
        sweep_name=sweep_name,
        case_id=case_id,
        outcomes=variant_outcomes,
    )
    issue_paths = write_issue_documents(issues_dir=paths.issues_dir, issues=issues)
    report = _build_sweep_summary_report(
        sweep_name=sweep_name,
        case_id=case_id,
        fixture_root=effective_fixture_root,
        source_sample_interval_seconds=source_sample_interval_seconds,
        resolved_config_path=paths.resolved_config_path,
        outcomes=variant_outcomes,
        issue_paths=issue_paths,
    )
    paths.report_path.write_text(report, encoding="utf-8")
    return RecordedSweepResult(
        run_root=paths.run_root,
        summary_path=paths.report_path,
        outcome_count=len(variant_outcomes),
    )


def _evaluate_variant(
    *,
    variant_name: str,
    sample_interval_seconds: float,
    timeline: list[TrackedTimelineState],
    contract: SweepContractConfig,
    baseline_first_occurrence: dict[SweepStateLabel, float],
) -> SweepVariantOutcome:
    """Evaluate one replay timeline against one transition contract."""

    transition_labels = _transition_labels(timeline)
    first_occurrence = _first_occurrence_times(timeline)
    missing_labels = tuple(
        label for label in contract.required_labels if label not in first_occurrence
    )
    order_matches = _required_label_order_matches(
        required_labels=contract.required_labels,
        first_occurrence=first_occurrence,
    )
    drift_by_label_seconds: dict[str, float] = {}
    drift_exceeded_labels: list[SweepStateLabel] = []
    for label in contract.required_labels:
        if label not in first_occurrence or label not in baseline_first_occurrence:
            continue
        drift_seconds = abs(first_occurrence[label] - baseline_first_occurrence[label])
        drift_by_label_seconds[label] = drift_seconds
        if drift_seconds > contract.max_first_occurrence_drift_seconds:
            drift_exceeded_labels.append(label)
    actual_terminal_result = timeline[-1].last_turn_result if timeline else "none"
    terminal_result_ok = (
        contract.required_terminal_result is None
        or actual_terminal_result == contract.required_terminal_result
    )
    forbidden_terminal_result_seen = actual_terminal_result in contract.forbidden_terminal_results
    passed = (
        not missing_labels
        and order_matches
        and not drift_exceeded_labels
        and terminal_result_ok
        and not forbidden_terminal_result_seen
    )
    return SweepVariantOutcome(
        variant_name=variant_name,
        sample_interval_seconds=sample_interval_seconds,
        sample_count=len(timeline),
        transition_labels=transition_labels,
        required_labels=contract.required_labels,
        missing_labels=missing_labels,
        order_matches=order_matches,
        actual_terminal_result=actual_terminal_result,
        required_terminal_result=contract.required_terminal_result,
        forbidden_terminal_results=contract.forbidden_terminal_results,
        drift_exceeded_labels=tuple(drift_exceeded_labels),
        drift_by_label_seconds=drift_by_label_seconds,
        skipped_reason=None,
        passed=passed,
    )


def _build_sweep_issues(
    *,
    sweep_name: str,
    case_id: str,
    outcomes: list[SweepVariantOutcome],
) -> list[IssueNote]:
    """Build issue docs for failed sweep variants."""

    issues: list[IssueNote] = []
    for outcome in outcomes:
        if outcome.passed:
            continue
        details = [
            f"Sweep: `{sweep_name}`",
            f"Case: `{case_id}`",
            f"Variant: `{outcome.variant_name}`",
            f"Sample interval seconds: `{outcome.sample_interval_seconds}`",
            f"Missing labels: `{', '.join(outcome.missing_labels) or 'none'}`",
            f"Transition order matches: `{outcome.order_matches}`",
            f"Actual terminal result: `{outcome.actual_terminal_result}`",
            f"Required terminal result: `{outcome.required_terminal_result or 'none'}`",
            f"Forbidden terminal results: `{', '.join(outcome.forbidden_terminal_results) or 'none'}`",
            f"Drift-exceeded labels: `{', '.join(outcome.drift_exceeded_labels) or 'none'}`",
            f"Skipped reason: `{outcome.skipped_reason or 'none'}`",
        ]
        issues.append(
            IssueNote(
                slug=f"sweep-{case_id}-{outcome.variant_name}",
                title=f"Sweep Variant Failed: {outcome.variant_name}",
                summary=(
                    "The cadence-sweep variant did not satisfy the configured transition contract."
                ),
                details=details,
            )
        )
    return issues


def _build_sweep_summary_report(
    *,
    sweep_name: str,
    case_id: str,
    fixture_root: Path,
    source_sample_interval_seconds: float,
    resolved_config_path: Path,
    outcomes: list[SweepVariantOutcome],
    issue_paths: list[Path],
) -> str:
    """Render the Markdown summary report for one recorded sweep."""

    what_worked = [
        "Resolved the cadence sweep from the demo-owned config.",
        "Replayed each supported cadence variant through the standalone tracker.",
    ]
    what_failed = [
        (
            f"{outcome.variant_name} failed its transition contract."
            if outcome.skipped_reason is None
            else f"{outcome.variant_name} could not run: {outcome.skipped_reason}"
        )
        for outcome in outcomes
        if not outcome.passed
    ]
    if not what_failed:
        what_failed = ["No sweep failures were detected."]
    lines = [
        "# Shared TUI Tracking Sweep Report",
        "",
        f"- Sweep: `{sweep_name}`",
        f"- Case: `{case_id}`",
        f"- Fixture root: `{fixture_root}`",
        f"- Source sample interval seconds: `{source_sample_interval_seconds}`",
        f"- Resolved demo config: `{resolved_config_path}`",
        "",
        "## What Worked",
        "",
        *[f"- {item}" for item in what_worked],
        "",
        "## What Did Not",
        "",
        *[f"- {item}" for item in what_failed],
        "",
        "## Variants",
        "",
    ]
    for outcome in outcomes:
        lines.extend(
            [
                f"- `{outcome.variant_name}`: "
                f"interval=`{outcome.sample_interval_seconds}` "
                f"passed=`{outcome.passed}` "
                f"terminal=`{outcome.actual_terminal_result}` "
                f"labels=`{', '.join(outcome.transition_labels) or 'none'}`",
            ]
        )
    lines.extend(
        [
            "",
            "## Issue Docs",
            "",
            f"- `{', '.join(str(path) for path in issue_paths) or 'none'}`",
            "",
        ]
    )
    return "\n".join(lines)


def _downsample_observations(
    *,
    observations: list[RecordedObservation],
    target_interval_seconds: float,
) -> list[RecordedObservation]:
    """Downsample one recorded observation stream to a slower effective cadence."""

    if not observations:
        return []
    selected: list[RecordedObservation] = [observations[0]]
    next_deadline = observations[0].elapsed_seconds + target_interval_seconds
    for observation in observations[1:]:
        if observation.elapsed_seconds + 1e-9 < next_deadline:
            continue
        selected.append(observation)
        next_deadline = observation.elapsed_seconds + target_interval_seconds
    if selected[-1].sample_id != observations[-1].sample_id:
        selected.append(observations[-1])
    return selected


def _transition_labels(timeline: list[TrackedTimelineState]) -> tuple[SweepStateLabel, ...]:
    """Return the ordered unique state-label sequence for one replay timeline."""

    labels: list[SweepStateLabel] = []
    previous: SweepStateLabel | None = None
    for item in timeline:
        current = _state_label(item)
        if current != previous:
            labels.append(current)
            previous = current
    return tuple(labels)


def _first_occurrence_times(
    timeline: list[TrackedTimelineState],
) -> dict[SweepStateLabel, float]:
    """Return the first observed elapsed-seconds value for each label."""

    first_occurrence: dict[SweepStateLabel, float] = {}
    for item in timeline:
        label = _state_label(item)
        first_occurrence.setdefault(label, item.elapsed_seconds)
    return first_occurrence


def _required_label_order_matches(
    *,
    required_labels: tuple[SweepStateLabel, ...],
    first_occurrence: dict[SweepStateLabel, float],
) -> bool:
    """Return whether required labels appear in nondecreasing order."""

    last_seconds = -1.0
    for label in required_labels:
        if label not in first_occurrence:
            return False
        current_seconds = first_occurrence[label]
        if current_seconds + 1e-9 < last_seconds:
            return False
        last_seconds = current_seconds
    return True


def _state_label(item: TrackedTimelineState) -> SweepStateLabel:
    """Collapse one public tracked-state row into a sweep-level label."""

    if item.diagnostics_availability == "tui_down":
        return "tui_down"
    if item.diagnostics_availability == "unavailable":
        return "unavailable"
    if item.diagnostics_availability == "error":
        return "error"
    if item.last_turn_result == "success":
        return "ready_success"
    if item.last_turn_result == "interrupted":
        return "ready_interrupted"
    if item.last_turn_result == "known_failure":
        return "ready_known_failure"
    if item.turn_phase == "active":
        return "active"
    if item.turn_phase == "ready":
        return "ready"
    return "unknown"


def _resolve_sweep_run_root(
    *,
    repo_root: Path,
    demo_config: ResolvedDemoConfig,
    sweep_name: str,
    case_id: str,
    output_root: Path | None,
) -> Path:
    """Return the run root for one recorded sweep."""

    if output_root is not None:
        return output_root.expanduser().resolve()
    stamp = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S")
    del repo_root
    return (demo_config.sweeps_root_path() / sweep_name / case_id / stamp).resolve()


def _load_fixture_manifest(fixture_root: Path) -> RecordedFixtureManifest | None:
    """Load fixture metadata when present."""

    path = fixture_root / _FIXTURE_MANIFEST_NAME
    if not path.is_file():
        return None
    return RecordedFixtureManifest.from_payload(json.loads(path.read_text(encoding="utf-8")))


def _resolve_recording_root(fixture_root: Path) -> Path:
    """Return the recording root inside one fixture or run root."""

    recording_root = fixture_root / "recording"
    if recording_root.is_dir():
        return recording_root
    return fixture_root


def _load_recorder_manifest(recording_root: Path) -> TerminalRecordManifest | None:
    """Load the recorder manifest when present."""

    path = recording_root / "manifest.json"
    if not path.is_file():
        return None
    return load_manifest(path)


def _infer_tool_from_path(path: Path) -> ToolName:
    """Infer the tool name from the fixture path when no manifest is present."""

    lowered_parts = {part.lower() for part in path.parts}
    if "claude" in lowered_parts:
        return "claude"
    if "codex" in lowered_parts:
        return "codex"
    raise ValueError(f"Could not infer tool name from fixture path: {path}")


def _require_sample_interval(value: float | None) -> float:
    """Return one required sample interval for a concrete sweep variant."""

    if value is None:
        raise ValueError("sweep variant sample interval is missing")
    return value
