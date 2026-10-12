"""Qualification gate for the codex 0.162.x detector against frozen campaign labels.

Replays the two blind-labeled 5 fps recordings of codex-cli 0.162.1 captured by
the 2026-10-12 debug campaign (`context/campaigns/debug/2026-10-12-codex-tui-parsing/`)
through the maintained `analyze_terminal_record` production path and joins the
resulting `state_observed` rows with the frozen ground-truth labels by sample id.

Gate (per the campaign's measured candidate scores):

- session 1 (lifecycle): >=99.8% agreement on both `surface_accepting_input`
  and `surface_ready_posture`
- session 2 (operator surfaces): 100% agreement on both booleans

The pre-change fallback detector produced 147/1907 and 68/437 false-ready
samples on these recordings (see the campaign's repair report); this gate locks
in the repaired 0.162.x behavior.
"""

from __future__ import annotations

import gzip
import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from houmao.terminal_record.service import analyze_terminal_record

_FIXTURE_ROOT = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "shared_tui_tracking"
    / "codex"
    / "qualification"
)
_BOOLEAN_FIELDS = ("surface_accepting_input", "surface_ready_posture")
_MIN_BOOLEAN_AGREEMENT = {
    "session1_lifecycle": 0.998,
    "session2_operator_surfaces": 1.0,
}


def _materialize_run_root(*, fixture_dir: Path, tmp_path: Path) -> Path:
    """Unpack one gzipped fixture recording into a recorder run root."""

    run_root = tmp_path / fixture_dir.name
    run_root.mkdir()
    shutil.copy(fixture_dir / "manifest.json", run_root / "manifest.json")
    shutil.copy(fixture_dir / "input_events.ndjson", run_root / "input_events.ndjson")
    with (
        gzip.open(fixture_dir / "pane_snapshots.ndjson.gz", "rb") as source,
        (run_root / "pane_snapshots.ndjson").open("wb") as target,
    ):
        shutil.copyfileobj(source, target)
    return run_root


def _load_ndjson(path: Path) -> list[dict[str, Any]]:
    """Load one NDJSON file into a row list."""

    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def _label_expectations_by_sample(
    *, labels_path: Path, sample_order: list[str]
) -> dict[str, dict[str, Any]]:
    """Expand inclusive frozen label ranges over the ordered sample stream."""

    payload = json.loads(labels_path.read_text(encoding="utf-8"))
    expectations_by_sample: dict[str, dict[str, Any]] = {}
    for item in payload.get("labels", []):
        start_id = item["sample_id"]
        end_id = item.get("sample_end_id") or start_id
        try:
            start = sample_order.index(start_id)
            end = sample_order.index(end_id)
        except ValueError:
            continue
        if end < start:
            continue
        for sample_id in sample_order[start : end + 1]:
            expectations_by_sample[sample_id] = item.get("expectations") or {}
    return expectations_by_sample


@pytest.mark.parametrize("session_fixture", ["session1_lifecycle", "session2_operator_surfaces"])
def test_codex_0_162_x_replay_matches_frozen_campaign_labels(
    session_fixture: str, tmp_path: Path
) -> None:
    fixture_dir = _FIXTURE_ROOT / session_fixture
    run_root = _materialize_run_root(fixture_dir=fixture_dir, tmp_path=tmp_path)

    analyze_terminal_record(
        run_root=run_root,
        tool="codex",
        observed_version="0.162.1",
        output_tag="qualification",
    )

    sample_order = [row["sample_id"] for row in _load_ndjson(run_root / "pane_snapshots.ndjson")]
    expectations_by_sample = _label_expectations_by_sample(
        labels_path=fixture_dir / "labels.json",
        sample_order=sample_order,
    )
    rows = _load_ndjson(run_root / "state_observed_qualification.ndjson")

    compared = 0
    boolean_matches = {field: 0 for field in _BOOLEAN_FIELDS}
    false_ready_samples: list[str] = []
    false_busy_samples: list[str] = []
    for row in rows:
        expected = expectations_by_sample.get(row["sample_id"])
        if expected is None:
            continue
        compared += 1
        for field in _BOOLEAN_FIELDS:
            if row.get(field) == expected.get(field):
                boolean_matches[field] += 1
        if (
            row.get("surface_ready_posture") == "yes" or row.get("turn_phase") == "ready"
        ) and expected.get("surface_ready_posture") == "no":
            false_ready_samples.append(row["sample_id"])
        if (
            row.get("surface_ready_posture") != "yes"
            and expected.get("surface_ready_posture") == "yes"
        ):
            false_busy_samples.append(row["sample_id"])

    threshold = _MIN_BOOLEAN_AGREEMENT[session_fixture]
    assert compared == len(expectations_by_sample)
    for field in _BOOLEAN_FIELDS:
        agreement = boolean_matches[field] / compared
        assert agreement >= threshold, (
            f"{session_fixture} {field} agreement {agreement:.4f} < {threshold} "
            f"({boolean_matches[field]}/{compared}); "
            f"false-ready={false_ready_samples[:8]} false-busy={false_busy_samples[:8]}"
        )
