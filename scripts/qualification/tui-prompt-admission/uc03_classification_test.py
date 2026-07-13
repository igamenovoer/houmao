"""UC-03 classification-correctness comparator.

This script compares the shared tracker/detector's public tracked-state output
against either reviewer-approved direct labels or the older derived state-label
artifact for a set of replay-ready long-horizon recordings. Both streams are mapped to UC-03 readiness labels
(``ready_immediate``, ``busy_active``, ``busy_draft``, ``busy_overlay``,
``indeterminate``) before comparison.

The script expects the existing replay artifacts produced by the long-horizon
qualification harness:

    <attempt-root>/replay/schedules/canonical/tracker-timeline.ndjson
    <attempt-root>/replay/schedules/canonical/groundtruth.ndjson

Usage
-----
    pixi run python scripts/qualification/tui-prompt-admission/uc03_classification_test.py \
        tmp/tui-state-tracking-long-horizon/2026-07-13-all-providers/sessions/claude-st-01/attempts/a007

Or pass a run root to scan all known replay-ready cells:

    pixi run python scripts/qualification/tui-prompt-admission/uc03_classification_test.py \
        --run-root tmp/tui-state-tracking-long-horizon/2026-07-13-all-providers
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from houmao.demo.shared_tui_tracking_demo_pack.groundtruth import load_fixture_inputs
from houmao.demo.shared_tui_tracking_demo_pack.models import load_input_events
from houmao.shared_tui_tracking.reducer import replay_timeline

from uc03_label import Uc03ReadinessLabel, map_public_state_to_uc03_label


@dataclass
class SampleComparison:
    """Per-sample comparison result."""

    sample_id: str
    elapsed_seconds: float
    tracker_label: Uc03ReadinessLabel
    groundtruth_label: Uc03ReadinessLabel
    tracker_state: dict[str, Any]
    groundtruth_state: dict[str, Any]
    sequence_index: int
    fields_differ: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class MismatchInterval:
    """One consecutive mismatch run classified as boundary noise or sustained."""

    first_sample_id: str
    last_sample_id: str
    first_elapsed_seconds: float
    last_elapsed_seconds: float
    sample_count: int
    duration_seconds: float
    classification: str


@dataclass
class AttemptReport:
    """Classification-correctness report for one attempt."""

    attempt_path: Path
    schedule: str
    total_samples: int = 0
    mismatch_count: int = 0
    first_mismatch_sample_id: str | None = None
    reference_kind: str = "legacy_derived_state_labels"
    current_detector_replayed: bool = True
    label_counts: dict[str, dict[str, int]] = field(default_factory=dict)
    mismatches: list[SampleComparison] = field(default_factory=list)
    mismatch_intervals: list[MismatchInterval] = field(default_factory=list)
    admission_mismatches: list[SampleComparison] = field(default_factory=list)
    admission_mismatch_intervals: list[MismatchInterval] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Initialize nested label counters."""
        if not self.label_counts:
            self.label_counts = {"tracker": {}, "reference": {}}

    def to_payload(self) -> dict[str, Any]:
        """Return a compact JSON-compatible qualification summary."""

        sustained = [item for item in self.mismatch_intervals if item.classification == "sustained"]
        false_ready_count = sum(
            1
            for item in self.admission_mismatches
            if item.tracker_label == Uc03ReadinessLabel.READY_IMMEDIATE
        )
        return {
            "attempt_path": str(self.attempt_path),
            "schedule": self.schedule,
            "reference_kind": self.reference_kind,
            "current_detector_replayed": self.current_detector_replayed,
            "total_samples": self.total_samples,
            "mismatch_count": self.mismatch_count,
            "first_mismatch_sample_id": self.first_mismatch_sample_id,
            "mismatch_interval_count": len(self.mismatch_intervals),
            "sustained_interval_count": len(sustained),
            "boundary_interval_count": len(self.mismatch_intervals) - len(sustained),
            "label_counts": self.label_counts,
            "mismatch_intervals": [item.__dict__ for item in self.mismatch_intervals],
            "admission_mismatch_count": len(self.admission_mismatches),
            "false_ready_count": false_ready_count,
            "false_busy_count": len(self.admission_mismatches) - false_ready_count,
            "admission_mismatch_interval_count": len(self.admission_mismatch_intervals),
            "admission_mismatch_intervals": [
                item.__dict__ for item in self.admission_mismatch_intervals
            ],
        }


def _load_ndjson(path: Path) -> list[dict[str, Any]]:
    """Load a newline-delimited JSON file."""
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def _map_sample(record: dict[str, Any]) -> Uc03ReadinessLabel:
    """Map a tracker-timeline or groundtruth record to a UC-03 label."""
    return map_public_state_to_uc03_label(
        turn_phase=record.get("turn_phase"),
        surface_ready_posture=record.get("surface_ready_posture"),
        surface_editing_input=record.get("surface_editing_input"),
        surface_accepting_input=record.get("surface_accepting_input"),
        diagnostics_availability=record.get("diagnostics_availability"),
        active_reasons=record.get("active_reasons") or [],
        ambiguous_interactive_surface=_has_explicit_overlay_evidence(record),
    )


def _has_explicit_overlay_evidence(record: dict[str, Any]) -> bool:
    """Return whether one tracker row affirmatively identifies an overlay."""

    if record.get("ambiguous_interactive_surface") is True:
        return True
    notes = {str(item) for item in record.get("notes") or []}
    return bool(
        notes
        & {
            "ambiguous_interactive_surface",
            "approval_panel_visible",
            "approval_required",
        }
    )


def _public_state_diff(tracker: dict[str, Any], groundtruth: dict[str, Any]) -> list[str]:
    """Return public tracked-state fields that differ between two records."""
    public_fields = [
        "diagnostics_availability",
        "surface_accepting_input",
        "surface_editing_input",
        "surface_ready_posture",
        "turn_phase",
        "last_turn_result",
        "last_turn_source",
    ]
    diffs: list[str] = []
    for field_name in public_fields:
        if tracker.get(field_name) != groundtruth.get(field_name):
            diffs.append(field_name)
    return diffs


def compare_attempt(
    attempt_path: Path,
    schedule: str = "canonical",
    *,
    replay_current_detector: bool = True,
    direct_labels_path: Path | None = None,
) -> AttemptReport:
    """Compare tracker timeline against groundtruth for one attempt.

    Parameters
    ----------
    attempt_path
        Root directory of the attempt (e.g., ``.../claude-st-01/attempts/a007``).
    schedule
        Replay schedule name to read. Defaults to ``canonical``.

    Returns
    -------
    AttemptReport
        Classification-correctness report.
    """
    replay_dir = attempt_path / "replay" / "schedules" / schedule
    tracker_path = replay_dir / "tracker-timeline.ndjson"
    groundtruth_path = replay_dir / "groundtruth.ndjson"

    if not tracker_path.exists():
        raise FileNotFoundError(f"Missing tracker timeline: {tracker_path}")
    if not groundtruth_path.exists():
        raise FileNotFoundError(f"Missing groundtruth timeline: {groundtruth_path}")

    tracker_samples = (
        _replay_current_tracker(attempt_path=attempt_path, schedule=schedule)
        if replay_current_detector
        else _load_ndjson(tracker_path)
    )
    groundtruth_samples = _load_ndjson(groundtruth_path)

    reference_kind = (
        "reviewer_approved_direct_labels"
        if direct_labels_path is not None
        else "legacy_derived_state_labels"
    )
    report = AttemptReport(
        attempt_path=attempt_path,
        schedule=schedule,
        reference_kind=reference_kind,
        current_detector_replayed=replay_current_detector,
    )
    report.total_samples = len(tracker_samples)

    gt_by_id = {sample["sample_id"]: sample for sample in groundtruth_samples}
    direct_labels = (
        _load_direct_labels(
            direct_labels_path, sample_ids=[item["sample_id"] for item in tracker_samples]
        )
        if direct_labels_path is not None
        else None
    )

    for sequence_index, tracker_sample in enumerate(tracker_samples):
        sample_id = tracker_sample["sample_id"]
        groundtruth_sample = gt_by_id.get(sample_id)
        if groundtruth_sample is None:
            continue

        tracker_label = _map_sample(tracker_sample)
        groundtruth_label = (
            direct_labels[sample_id]
            if direct_labels is not None
            else _map_sample(groundtruth_sample)
        )

        report.label_counts["tracker"][tracker_label.value] = (
            report.label_counts["tracker"].get(tracker_label.value, 0) + 1
        )
        report.label_counts["reference"][groundtruth_label.value] = (
            report.label_counts["reference"].get(groundtruth_label.value, 0) + 1
        )

        fields_differ = _public_state_diff(tracker_sample, groundtruth_sample)

        if tracker_label != groundtruth_label:
            report.mismatch_count += 1
            if report.first_mismatch_sample_id is None:
                report.first_mismatch_sample_id = sample_id

            comparison = SampleComparison(
                sample_id=sample_id,
                elapsed_seconds=tracker_sample.get("elapsed_seconds", 0.0),
                tracker_label=tracker_label,
                groundtruth_label=groundtruth_label,
                tracker_state={
                    k: tracker_sample.get(k)
                    for k in [
                        "turn_phase",
                        "surface_ready_posture",
                        "surface_editing_input",
                        "surface_accepting_input",
                        "diagnostics_availability",
                        "active_reasons",
                    ]
                },
                groundtruth_state={"direct_label": groundtruth_label.value}
                if direct_labels is not None
                else {
                    k: groundtruth_sample.get(k)
                    for k in [
                        "turn_phase",
                        "surface_ready_posture",
                        "surface_editing_input",
                        "surface_accepting_input",
                        "diagnostics_availability",
                        "active_reasons",
                    ]
                },
                sequence_index=sequence_index,
                fields_differ=fields_differ,
            )
            report.mismatches.append(comparison)
            if _accepts_prompt_immediately(tracker_label) != _accepts_prompt_immediately(
                groundtruth_label
            ):
                report.admission_mismatches.append(comparison)

    report.mismatch_intervals = _mismatch_intervals(report.mismatches)
    report.admission_mismatch_intervals = _mismatch_intervals(report.admission_mismatches)
    return report


def _replay_current_tracker(*, attempt_path: Path, schedule: str) -> list[dict[str, Any]]:
    """Replay raw recording evidence through the detector code in this checkout."""

    recording_root = attempt_path / "recording" / "terminal-record"
    fixture = load_fixture_inputs(
        recording_root=recording_root,
        runtime_observations_path=attempt_path / "runtime" / "runtime-observations.ndjson",
    )
    mappings = _load_ndjson(
        attempt_path / "replay" / "schedules" / schedule / "source-mapping.ndjson"
    )
    observations_by_id = {item.sample_id: item for item in fixture.observations}
    observations = [
        replace(
            observations_by_id[str(item["source_sample_id"])],
            sample_id=str(item["derived_sample_id"]),
            elapsed_seconds=float(item["target_elapsed_seconds"]),
        )
        for item in mappings
    ]
    manifest = json.loads(
        (attempt_path / "runtime" / "provider-launch-manifest.json").read_text(encoding="utf-8")
    )
    provider = str(manifest["provider"])
    observed_version = str(manifest.get("observed_version", "")) or None
    timeline, _events = replay_timeline(
        observations=observations,
        tool=provider,
        observed_version=observed_version,
        settle_seconds=1.0,
        input_events=load_input_events(recording_root / "input_events.ndjson"),
    )
    return [item.to_payload() for item in timeline]


def _load_direct_labels(path: Path, *, sample_ids: list[str]) -> dict[str, Uc03ReadinessLabel]:
    """Load complete reviewer-approved direct UC-03 label intervals."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    provenance = payload.get("provenance") or {}
    if (
        not provenance.get("labeler")
        or not provenance.get("reviewer")
        or not provenance.get("rubric_digest")
        or provenance.get("review_status") != "approved"
    ):
        raise ValueError(f"Direct labels lack approved labeler/reviewer/rubric provenance: {path}")
    index_by_id = {sample_id: index for index, sample_id in enumerate(sample_ids)}
    expanded: dict[str, Uc03ReadinessLabel] = {}
    for item in payload.get("labels") or []:
        if not item.get("visible_evidence"):
            raise ValueError("Direct label interval lacks visible_evidence")
        first = str(item["start_sample_id"])
        last = str(item.get("end_sample_id", first))
        if first not in index_by_id or last not in index_by_id:
            raise ValueError(f"Direct label range is outside the replay schedule: {first}..{last}")
        start_index = index_by_id[first]
        end_index = index_by_id[last]
        if end_index < start_index:
            raise ValueError(f"Direct label range is reversed: {first}..{last}")
        label = Uc03ReadinessLabel(str(item["label"]))
        for sample_id in sample_ids[start_index : end_index + 1]:
            if sample_id in expanded:
                raise ValueError(f"Direct labels overlap at {sample_id}")
            expanded[sample_id] = label
    missing = [sample_id for sample_id in sample_ids if sample_id not in expanded]
    if missing:
        raise ValueError(
            f"Direct labels do not cover {len(missing)} samples; first is {missing[0]}"
        )
    return expanded


def _mismatch_intervals(mismatches: list[SampleComparison]) -> list[MismatchInterval]:
    """Group consecutive mismatches and distinguish boundary noise from sustained errors."""

    if not mismatches:
        return []
    grouped: list[list[SampleComparison]] = [[mismatches[0]]]
    for item in mismatches[1:]:
        if item.sequence_index == grouped[-1][-1].sequence_index + 1:
            grouped[-1].append(item)
        else:
            grouped.append([item])
    intervals: list[MismatchInterval] = []
    for group in grouped:
        duration = max(0.0, group[-1].elapsed_seconds - group[0].elapsed_seconds)
        intervals.append(
            MismatchInterval(
                first_sample_id=group[0].sample_id,
                last_sample_id=group[-1].sample_id,
                first_elapsed_seconds=group[0].elapsed_seconds,
                last_elapsed_seconds=group[-1].elapsed_seconds,
                sample_count=len(group),
                duration_seconds=duration,
                classification="sustained" if duration >= 1.0 else "transition_boundary",
            )
        )
    return intervals


def _accepts_prompt_immediately(label: Uc03ReadinessLabel) -> bool:
    """Return the downstream prompt-admission decision for one UC-03 label."""

    return label == Uc03ReadinessLabel.READY_IMMEDIATE


def _format_report(report: AttemptReport, verbose: bool = False) -> str:
    """Format a report as human-readable text."""
    lines: list[str] = []
    try:
        rel_path = report.attempt_path.relative_to(Path.cwd())
    except ValueError:
        rel_path = report.attempt_path
    lines.append(f"Attempt: {rel_path} ({report.schedule})")
    lines.append(f"  Total samples: {report.total_samples}")
    lines.append(f"  Mismatches: {report.mismatch_count}")
    lines.append(f"  First mismatch: {report.first_mismatch_sample_id}")
    lines.append(f"  Reference: {report.reference_kind}")
    lines.append(f"  Current detector replayed: {report.current_detector_replayed}")
    sustained = [item for item in report.mismatch_intervals if item.classification == "sustained"]
    lines.append(
        "  Mismatch intervals: "
        f"{len(report.mismatch_intervals)} total, {len(sustained)} sustained, "
        f"{len(report.mismatch_intervals) - len(sustained)} transition-boundary"
    )
    false_ready_count = sum(
        1
        for item in report.admission_mismatches
        if item.tracker_label == Uc03ReadinessLabel.READY_IMMEDIATE
    )
    lines.append(
        "  Prompt-admission mismatches: "
        f"{len(report.admission_mismatches)} "
        f"({false_ready_count} false-ready, "
        f"{len(report.admission_mismatches) - false_ready_count} false-busy)"
    )
    lines.append(f"  Prompt-admission intervals: {len(report.admission_mismatch_intervals)}")
    lines.append("  Tracker label counts:")
    for label, count in sorted(report.label_counts["tracker"].items()):
        lines.append(f"    {label}: {count}")
    lines.append("  Reference label counts:")
    for label, count in sorted(report.label_counts["reference"].items()):
        lines.append(f"    {label}: {count}")

    if verbose and report.mismatches:
        lines.append("  First 10 mismatches:")
        for mismatch in report.mismatches[:10]:
            lines.append(
                f"    {mismatch.sample_id} @ {mismatch.elapsed_seconds:.3f}s: "
                f"tracker={mismatch.tracker_label.value} "
                f"reference={mismatch.groundtruth_label.value}"
            )
            if mismatch.fields_differ:
                lines.append(f"      differing fields: {', '.join(mismatch.fields_differ)}")
            lines.append(f"      tracker: {mismatch.tracker_state}")
            lines.append(f"      reference: {mismatch.groundtruth_state}")

    return "\n".join(lines)


# Replay-ready attempts listed in 20260713T095944Z-long-horizon-test-report.md.
REPLAY_READY_ATTEMPTS: list[tuple[str, str, str]] = [
    ("claude", "st-01", "a007"),
    ("claude", "st-02", "a001"),
    ("claude", "st-03", "a001"),
    ("codex", "st-01", "a004"),
    ("codex", "st-03", "a004"),
    ("codex", "st-04", "a002"),
    ("codex", "st-05", "a004"),
    ("kimi", "st-03", "a008"),
    ("kimi", "st-04", "a003"),
]


def _resolve_attempts_from_run_root(run_root: Path) -> list[Path]:
    """Resolve the known replay-ready attempt paths under a run root."""
    attempts: list[Path] = []
    for provider, cell, attempt in REPLAY_READY_ATTEMPTS:
        attempt_path = run_root / "sessions" / f"{provider}-{cell}" / "attempts" / attempt
        if attempt_path.exists():
            attempts.append(attempt_path)
        else:
            print(
                f"Warning: expected replay-ready attempt not found: {attempt_path}",
                file=sys.stderr,
            )
    return attempts


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Compare current UC-03 tracker labels with direct or legacy references."
    )
    parser.add_argument(
        "attempts",
        nargs="*",
        type=Path,
        help="Attempt root directories to compare.",
    )
    parser.add_argument(
        "--run-root",
        type=Path,
        help="Long-horizon run root; scan known replay-ready attempts.",
    )
    parser.add_argument(
        "--schedule",
        default="canonical",
        help="Replay schedule to read (default: canonical).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed mismatch samples.",
    )
    parser.add_argument(
        "--archived-tracker",
        action="store_true",
        help="Read the archived tracker timeline instead of replaying current detector code.",
    )
    parser.add_argument(
        "--direct-labels",
        type=Path,
        help="Reviewer-approved direct UC-03 label file for a single attempt.",
    )
    parser.add_argument(
        "--summary-json",
        type=Path,
        help="Write the compact interval summary as JSON.",
    )
    parser.add_argument(
        "--allow-mismatches",
        action="store_true",
        help="Exit successfully after reporting mismatches.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-attempt text while retaining the overall and JSON summaries.",
    )
    args = parser.parse_args()

    attempt_paths: list[Path] = list(args.attempts)
    if args.run_root:
        attempt_paths.extend(_resolve_attempts_from_run_root(args.run_root))

    if not attempt_paths:
        parser.error("Provide at least one attempt path or --run-root.")
    if args.direct_labels is not None and len(attempt_paths) != 1:
        parser.error("--direct-labels requires exactly one attempt path.")

    overall_mismatches = 0
    overall_samples = 0
    overall_admission_mismatches = 0

    reports: list[AttemptReport] = []
    for attempt_path in attempt_paths:
        try:
            report = compare_attempt(
                attempt_path,
                schedule=args.schedule,
                replay_current_detector=not args.archived_tracker,
                direct_labels_path=args.direct_labels,
            )
        except FileNotFoundError as exc:
            print(f"Skipping {attempt_path}: {exc}", file=sys.stderr)
            continue

        if not args.quiet:
            print(_format_report(report, verbose=args.verbose))
            print()
        overall_mismatches += report.mismatch_count
        overall_samples += report.total_samples
        overall_admission_mismatches += len(report.admission_mismatches)
        reports.append(report)

    print("=" * 60)
    print(f"Overall: {overall_mismatches}/{overall_samples} samples mismatched")
    print(
        f"Prompt admission: {overall_admission_mismatches}/{overall_samples} decisions mismatched"
    )
    if args.summary_json is not None:
        args.summary_json.parent.mkdir(parents=True, exist_ok=True)
        args.summary_json.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "overall_mismatches": overall_mismatches,
                    "overall_samples": overall_samples,
                    "overall_admission_mismatches": overall_admission_mismatches,
                    "reports": [item.to_payload() for item in reports],
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    return 0 if overall_mismatches == 0 or args.allow_mismatches else 1


if __name__ == "__main__":
    sys.exit(main())
