"""Shared helpers for iteration-1 assertion scripts.

Assert scripts follow promptfoo's Python assertion contract
(``get_assert(output, context) -> dict``) and read frozen run artifacts only:
``pane_snapshots.ndjson``, ``labels.json``, replay ``state_observed_*`` /
``parser_observed_*`` outputs, and ``frozen-evidence.json``. They never re-run
sessions and never inspect live detector state.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

EIGHT_PUBLIC_FIELDS = (
    "diagnostics_availability",
    "surface_accepting_input",
    "surface_editing_input",
    "surface_ready_posture",
    "surface_pending_input",
    "turn_phase",
    "last_turn_result",
    "last_turn_source",
)


def load_ndjson(path: Path) -> list[dict[str, Any]]:
    """Load one NDJSON file into a row list."""

    if not path.is_file():
        return []
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def sha256_file(path: Path) -> str:
    """Return the SHA-256 hex digest of one file."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_snapshot_index(recording_root: Path) -> list[str]:
    """Return ordered sample IDs from the frozen pane snapshot stream."""

    return [row["sample_id"] for row in load_ndjson(recording_root / "pane_snapshots.ndjson")]


def load_label_ranges(labels_path: Path) -> list[dict[str, Any]]:
    """Load labels.json into normalized inclusive sample ranges."""

    payload = json.loads(labels_path.read_text(encoding="utf-8"))
    ranges: list[dict[str, Any]] = []
    for item in payload.get("labels", []):
        ranges.append(
            {
                "label_id": item["label_id"],
                "family": label_family(item["label_id"]),
                "scenario_id": item.get("scenario_id"),
                "sample_id": item["sample_id"],
                "sample_end_id": item.get("sample_end_id") or item["sample_id"],
                "expectations": item.get("expectations") or {},
                "note": item.get("note"),
            }
        )
    return ranges


def label_family(label_id: str) -> str:
    """Return the state-family prefix of one label ID (``active-003`` → ``active``)."""

    head, _, tail = label_id.rpartition("-")
    if head and tail.isdigit():
        return head
    return label_id


def expand_range_samples(label_range: dict[str, Any], sample_order: list[str]) -> list[str]:
    """Expand one inclusive label range to ordered sample IDs."""

    try:
        start = sample_order.index(label_range["sample_id"])
        end = sample_order.index(label_range["sample_end_id"])
    except ValueError:
        return []
    if end < start:
        return []
    return sample_order[start : end + 1]


def sample_family_map(
    label_ranges: list[dict[str, Any]], sample_order: list[str]
) -> dict[str, str]:
    """Map every covered sample ID to its label family."""

    mapping: dict[str, str] = {}
    for label_range in label_ranges:
        for sample_id in expand_range_samples(label_range, sample_order):
            mapping[sample_id] = label_range["family"]
    return mapping


def sample_label_map(
    label_ranges: list[dict[str, Any]], sample_order: list[str]
) -> dict[str, dict[str, Any]]:
    """Map every covered sample ID to its label expectations."""

    mapping: dict[str, dict[str, Any]] = {}
    for label_range in label_ranges:
        for sample_id in expand_range_samples(label_range, sample_order):
            mapping[sample_id] = label_range["expectations"]
    return mapping


def result(
    *,
    passed: bool,
    reason: str,
    named_scores: dict[str, float] | None = None,
    component_results: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build one promptfoo-contract assertion result."""

    payload: dict[str, Any] = {"pass": passed, "score": 1.0 if passed else 0.0, "reason": reason}
    if named_scores:
        payload["named_scores"] = named_scores
    if component_results:
        payload["component_results"] = component_results
    return payload
