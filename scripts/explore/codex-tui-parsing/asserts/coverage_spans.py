"""Gate/measure: state-family coverage spans (plan G2).

Verifies each required label family appears with at least one contiguous
range of ``min_span_samples`` samples. ``optional: true`` families report a
coverage gap in the reason without failing the case.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    expand_range_samples,
    load_label_ranges,
    load_snapshot_index,
    result,
)


def get_assert(output: dict, context) -> dict:
    """Check that required state families have sufficiently long spans."""

    recording_root = Path(output["recording_root"])
    labels_path = Path(output["labels_path"])
    config = getattr(context, "assert_config", None) or {}
    required = list(config.get("required_spans") or [])
    min_samples = int(config.get("min_span_samples") or 3)
    optional = bool(config.get("optional") or False)

    sample_order = load_snapshot_index(recording_root)
    ranges = load_label_ranges(labels_path)

    span_lengths: dict[str, int] = {}
    for label_range in ranges:
        length = len(expand_range_samples(label_range, sample_order))
        span_lengths[label_range["family"]] = max(
            span_lengths.get(label_range["family"], 0), length
        )

    missing = [family for family in required if span_lengths.get(family, 0) < min_samples]
    named = {f"span_{family}": float(span_lengths.get(family, 0)) for family in required}
    if not missing:
        return result(
            passed=True,
            reason=f"all required spans present (>= {min_samples} samples)",
            named_scores=named,
        )
    if optional:
        return result(
            passed=True,
            reason=f"coverage gap (optional): {', '.join(missing)}",
            named_scores=named,
        )
    return result(
        passed=False,
        reason=f"missing or short spans: {', '.join(missing)}",
        named_scores=named,
    )
