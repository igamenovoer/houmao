"""Gate: blind-label integrity (plan G3).

Verifies complete non-overlapping coverage, all eight public fields per
range, manifest binding to the frozen recording digest, and that labeling
preceded any replay artifact.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    EIGHT_PUBLIC_FIELDS,
    expand_range_samples,
    load_label_ranges,
    load_snapshot_index,
    result,
    sha256_file,
)


def get_assert(output: dict, context) -> dict:  # noqa: ARG001 - promptfoo contract
    """Check ground-truth label completeness, ordering, and independence."""

    recording_root = Path(output["recording_root"])
    labels_path = Path(output["labels_path"])
    manifest_path = Path(output["labels_manifest_path"])

    problems: list[str] = []
    if not labels_path.is_file():
        return result(passed=False, reason=f"missing labels at {labels_path}")
    if not manifest_path.is_file():
        return result(passed=False, reason=f"missing labels manifest at {manifest_path}")

    sample_order = load_snapshot_index(recording_root)
    ranges = load_label_ranges(labels_path)

    for label_range in ranges:
        missing = [
            field for field in EIGHT_PUBLIC_FIELDS if field not in label_range["expectations"]
        ]
        if missing:
            problems.append(f"{label_range['label_id']}: missing fields {missing}")
        if not expand_range_samples(label_range, sample_order):
            problems.append(f"{label_range['label_id']}: range not resolvable in sample order")

    covered: dict[str, str] = {}
    for label_range in ranges:
        for sample_id in expand_range_samples(label_range, sample_order):
            if sample_id in covered:
                problems.append(
                    f"overlap at {sample_id}: {covered[sample_id]} vs {label_range['label_id']}"
                )
            covered[sample_id] = label_range["label_id"]
    uncovered = [sample_id for sample_id in sample_order if sample_id not in covered]
    if uncovered:
        problems.append(f"coverage gap: {len(uncovered)} samples unlabeled (e.g. {uncovered[:3]})")

    labels_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    recording_digest = sha256_file(recording_root / "pane_snapshots.ndjson")
    if labels_manifest.get("source_recording_sha256") != recording_digest:
        problems.append("labels manifest does not bind the current recording digest")
    if labels_manifest.get("labels_sha256") != sha256_file(labels_path):
        problems.append("labels manifest digest does not match labels.json")

    labeled_at = str(labels_manifest.get("labeled_at_utc") or "")
    replay_paths = [
        Path(path)
        for variant in (output.get("replay") or {}).values()
        for path in (variant.get("state_observed_path"), variant.get("parser_observed_path"))
        if path
    ]
    if labeled_at and replay_paths:
        from datetime import UTC, datetime

        labeled_dt = datetime.fromisoformat(labeled_at)
        if labeled_dt.tzinfo is None:
            labeled_dt = labeled_dt.replace(tzinfo=UTC)
        for replay_path in replay_paths:
            if replay_path.is_file():
                replay_dt = datetime.fromtimestamp(replay_path.stat().st_mtime, tz=UTC)
                if replay_dt < labeled_dt:
                    problems.append(f"replay artifact predates label freeze: {replay_path.name}")

    if problems:
        return result(passed=False, reason="; ".join(problems))
    return result(
        passed=True,
        reason=f"labels complete over {len(sample_order)} samples, {len(ranges)} ranges",
    )
