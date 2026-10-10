"""Measure: per-field agreement between replay output and ground truth.

Joins ``state_observed_<tag>.ndjson`` with frozen labels by sample ID and
reports per-field agreement ratios as ``named_scores``, led by the two
user-facing booleans (directive 2026-10-10): ``surface_accepting_input``
(ready to enter prompt) and ``surface_ready_posture`` (accept prompt). Always
returns ``pass: true``; detector mismatches are the iteration's output.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    EIGHT_PUBLIC_FIELDS,
    load_label_ranges,
    load_ndjson,
    result,
    sample_family_map,
    sample_label_map,
)

_BOOLEAN_FIELDS = ("surface_accepting_input", "surface_ready_posture")


def get_assert(output: dict, context) -> dict:
    """Compute replay-vs-label agreement for one replay variant."""

    config = getattr(context, "assert_config", None) or {}
    tag = str(config.get("replay_tag") or "baseline")
    variant = (output.get("replay") or {}).get(tag)
    if variant is None or not variant.get("state_observed_path"):
        return result(passed=True, reason=f"no replay variant {tag!r}; skipped")
    state_path = Path(variant["state_observed_path"])
    if not state_path.is_file():
        return result(passed=True, reason=f"replay output missing for {tag!r}; skipped")

    recording_root = Path(output["recording_root"])
    labels_path = Path(output["labels_path"])
    sample_order = [
        row["sample_id"] for row in load_ndjson(recording_root / "pane_snapshots.ndjson")
    ]
    ranges = load_label_ranges(labels_path)
    labels_by_sample = sample_label_map(ranges, sample_order)
    families_by_sample = sample_family_map(ranges, sample_order)

    rows = load_ndjson(state_path)
    compared = 0
    matches: dict[str, int] = {field: 0 for field in EIGHT_PUBLIC_FIELDS}
    mismatches: dict[str, int] = {field: 0 for field in EIGHT_PUBLIC_FIELDS}
    by_family: dict[str, dict[str, int]] = {}
    false_ready = 0
    false_busy = 0

    for row in rows:
        sample_id = row["sample_id"]
        expectations = labels_by_sample.get(sample_id)
        if expectations is None:
            continue
        compared += 1
        family = families_by_sample[sample_id]
        family_row = by_family.setdefault(family, {"samples": 0, "mismatches": 0})
        family_row["samples"] += 1
        row_mismatch = False
        for field in EIGHT_PUBLIC_FIELDS:
            expected = expectations.get(field)
            actual = row.get(field)
            if expected == actual:
                matches[field] += 1
            else:
                mismatches[field] += 1
                row_mismatch = True
        if row_mismatch:
            family_row["mismatches"] += 1
        if (
            row.get("surface_ready_posture") == "yes" or row.get("turn_phase") == "ready"
        ) and expectations.get("surface_ready_posture") == "no":
            false_ready += 1
        if (
            row.get("surface_ready_posture") != "yes"
            and expectations.get("surface_ready_posture") == "yes"
        ):
            false_busy += 1

    named_scores: dict[str, float] = {}
    for field in (*_BOOLEAN_FIELDS, *(f for f in EIGHT_PUBLIC_FIELDS if f not in _BOOLEAN_FIELDS)):
        total = matches[field] + mismatches[field]
        named_scores[f"agree_{field}"] = round(matches[field] / total, 4) if total else 0.0
    named_scores["false_ready_samples"] = float(false_ready)
    named_scores["false_busy_samples"] = float(false_busy)
    named_scores["compared_samples"] = float(compared)

    components = [
        {
            "pass": True,
            "reason": f"{family}: {counts['mismatches']}/{counts['samples']} samples mismatching",
            "named_scores": {
                "samples": float(counts["samples"]),
                "mismatched_samples": float(counts["mismatches"]),
            },
        }
        for family, counts in sorted(by_family.items())
    ]

    return result(
        passed=True,
        reason=(
            f"[{tag}] {compared} samples compared; "
            f"accepting={named_scores['agree_surface_accepting_input']:.3f} "
            f"ready={named_scores['agree_surface_ready_posture']:.3f} "
            f"false_ready={false_ready} false_busy={false_busy}"
        ),
        named_scores=named_scores,
        component_results=components,
    )
