"""Markdown reporting helpers for the tracked-TUI demo pack."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from houmao.terminal_record.models import TerminalRecordManifest

from .comparison import TimelineComparison
from .models import LiveWatchManifest, RecordedValidationManifest, save_json


@dataclass(frozen=True)
class IssueNote:
    """One actionable issue note to persist under the run root."""

    slug: str
    title: str
    summary: str
    details: list[str]


def write_issue_documents(*, issues_dir: Path, issues: list[IssueNote]) -> list[Path]:
    """Persist one Markdown file per issue."""

    issues_dir.mkdir(parents=True, exist_ok=True)
    output_paths: list[Path] = []
    for index, issue in enumerate(issues, start=1):
        path = issues_dir / f"{index:03d}-{_slugify(issue.slug)}.md"
        lines = [
            f"# {issue.title}",
            "",
            issue.summary,
            "",
            "## Details",
            "",
            *[f"- {line}" for line in issue.details],
            "",
        ]
        path.write_text("\n".join(lines), encoding="utf-8")
        output_paths.append(path)
    return output_paths


def build_recorded_run_issues(
    *,
    comparison: TimelineComparison,
    recorder_manifest: TerminalRecordManifest | None,
) -> list[IssueNote]:
    """Return recorded-run issue notes from comparison and capture metadata."""

    issues: list[IssueNote] = []
    if recorder_manifest is not None and recorder_manifest.run_tainted:
        issues.append(
            IssueNote(
                slug="authoritative-capture-tainted",
                title="Authoritative Capture Was Tainted",
                summary="The recorder lost exclusive active-capture posture, so explicit-input provenance may be incomplete.",
                details=[
                    f"Recorder input capture level: `{recorder_manifest.input_capture_level}`",
                    f"Taint reasons: `{', '.join(recorder_manifest.taint_reasons) or 'none'}`",
                ],
            )
        )
    if comparison.mismatch_count > 0:
        issues.append(
            IssueNote(
                slug="replay-mismatch",
                title="Replay Did Not Match Ground Truth",
                summary="The standalone tracker diverged from the human-authored ground truth for at least one sample.",
                details=[
                    f"Mismatch count: `{comparison.mismatch_count}`",
                    f"First divergence sample: `{comparison.first_divergence_sample_id}`",
                    "First divergence fields: "
                    f"`{', '.join(comparison.first_divergence_fields) or 'none'}`",
                ],
            )
        )
    if not comparison.transition_order_matches:
        issues.append(
            IssueNote(
                slug="transition-order-mismatch",
                title="Transition Ordering Diverged",
                summary="The replay and ground-truth timelines reached different ordered state transitions.",
                details=[
                    f"First divergence sample: `{comparison.first_divergence_sample_id}`",
                ],
            )
        )
    return issues


def build_recorded_summary_report(
    *,
    manifest: RecordedValidationManifest,
    comparison: TimelineComparison,
    recorder_manifest: TerminalRecordManifest | None,
    issue_paths: list[Path],
    artifact_paths: dict[str, Path],
) -> str:
    """Render the summary report for one recorded-validation run."""

    verdict = "passed" if comparison.mismatch_count == 0 else "failed"
    what_worked = [
        "Replay completed from recorder pane snapshots.",
        "Ground truth expanded from structured labels.",
    ]
    what_failed: list[str] = []
    if comparison.mismatch_count > 0:
        what_failed.append(
            f"Replay mismatched ground truth on `{comparison.mismatch_count}` samples."
        )
    if recorder_manifest is not None and recorder_manifest.run_tainted:
        what_failed.append("Recorder active-capture authority was tainted during capture.")
    if not what_failed:
        what_failed.append("No validation failures were detected.")

    lines = [
        "# Shared TUI Tracking Recorded Validation Report",
        "",
        f"- Verdict: `{verdict}`",
        f"- Case: `{manifest.case_id}`",
        f"- Tool: `{manifest.tool}`",
        f"- Fixture root: `{manifest.fixture_root}`",
        f"- Recording root: `{manifest.recording_root}`",
        f"- Observed version: `{manifest.observed_version or 'unknown'}`",
        f"- Capture sample interval seconds: `{manifest.capture_sample_interval_seconds}`",
        f"- Review video fps: `{manifest.review_video_fps}`",
        f"- Resolved demo config: `{manifest.resolved_config_path}`",
        "",
        "## What Worked",
        "",
        *[f"- {line}" for line in what_worked],
        "",
        "## What Did Not",
        "",
        *[f"- {line}" for line in what_failed],
        "",
        "## Artifacts",
        "",
        *[f"- {label}: `{path}`" for label, path in artifact_paths.items()],
        f"- Issue docs: `{', '.join(str(path) for path in issue_paths) or 'none'}`",
        "",
        "## Comparison",
        "",
        f"- Sample count: `{comparison.sample_count}`",
        f"- Mismatch count: `{comparison.mismatch_count}`",
        f"- Transition order matches: `{comparison.transition_order_matches}`",
        f"- First divergence sample: `{comparison.first_divergence_sample_id}`",
    ]
    return "\n".join(lines) + "\n"


def build_live_run_issues(
    *,
    comparison: TimelineComparison | None,
    labels_present: bool,
) -> list[IssueNote]:
    """Return live-watch issue notes."""

    issues: list[IssueNote] = []
    if not labels_present:
        issues.append(
            IssueNote(
                slug="ground-truth-missing",
                title="Ground Truth Missing For Live Run",
                summary="The live watch run retained recorder evidence, but no labels were present to build a ground-truth comparison.",
                details=[
                    "Add `labels.json` beside the recorder artifacts and re-run offline validation to compare against ground truth.",
                ],
            )
        )
        return issues
    if comparison is not None and comparison.mismatch_count > 0:
        issues.extend(build_recorded_run_issues(comparison=comparison, recorder_manifest=None))
    return issues


def build_live_summary_report(
    *,
    manifest: LiveWatchManifest,
    comparison: TimelineComparison | None,
    labels_present: bool,
    issue_paths: list[Path],
    artifact_paths: dict[str, Path],
) -> str:
    """Render the summary report for one live-watch run."""

    if not labels_present:
        verdict = "incomplete"
    elif comparison is not None and comparison.mismatch_count == 0:
        verdict = "passed"
    else:
        verdict = "failed"
    what_worked = [
        "Live dashboard persisted latest state, state samples, and transitions.",
        "Recorder evidence was retained for offline replay.",
    ]
    what_failed: list[str] = []
    if not labels_present:
        what_failed.append("No labels were present, so no ground-truth comparison was produced.")
    elif comparison is not None and comparison.mismatch_count > 0:
        what_failed.append(
            f"Replay mismatched ground truth on `{comparison.mismatch_count}` samples."
        )
    if not what_failed:
        what_failed.append("No live-watch validation failures were detected.")

    lines = [
        "# Shared TUI Tracking Live Watch Report",
        "",
        f"- Verdict: `{verdict}`",
        f"- Tool: `{manifest.tool}`",
        f"- Run root: `{manifest.run_root}`",
        f"- Recipe: `{manifest.recipe_path}`",
        f"- Brain home: `{manifest.brain_home_path}`",
        f"- Recorder root: `{manifest.terminal_record_run_root}`",
        f"- Observed version: `{manifest.observed_version or 'unknown'}`",
        f"- Sample interval seconds: `{manifest.sample_interval_seconds}`",
        f"- Runtime observer interval seconds: `{manifest.runtime_observer_interval_seconds}`",
        f"- Resolved demo config: `{manifest.resolved_config_path}`",
        "",
        "## What Worked",
        "",
        *[f"- {line}" for line in what_worked],
        "",
        "## What Did Not",
        "",
        *[f"- {line}" for line in what_failed],
        "",
        "## Artifacts",
        "",
        *[f"- {label}: `{path}`" for label, path in artifact_paths.items()],
        f"- Issue docs: `{', '.join(str(path) for path in issue_paths) or 'none'}`",
    ]
    if comparison is not None:
        lines.extend(
            [
                "",
                "## Comparison",
                "",
                f"- Sample count: `{comparison.sample_count}`",
                f"- Mismatch count: `{comparison.mismatch_count}`",
                f"- Transition order matches: `{comparison.transition_order_matches}`",
                f"- First divergence sample: `{comparison.first_divergence_sample_id}`",
            ]
        )
    return "\n".join(lines) + "\n"


def save_report_metadata(path: Path, payload: dict[str, Any]) -> None:
    """Persist one machine-readable report metadata payload."""

    save_json(path, payload)


def _slugify(value: str) -> str:
    """Return one filesystem-safe slug."""

    lowered = value.strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", lowered)
    return normalized.strip("-") or "issue"
