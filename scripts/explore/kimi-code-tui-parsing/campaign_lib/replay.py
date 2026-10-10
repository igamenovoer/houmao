"""Arm A replay harness: current detector vs monkey-patched 2.1.x candidate.

Both variants replay the same frozen ``pane_snapshots.ndjson`` through the
maintained ``analyze_terminal_record`` path with ``observed_version=2.1.1``.
The baseline runs unpatched in a subprocess (repo code as merged); the
candidate runs in-process under :func:`campaign_lib.patches.kimi_2_1_x_patch`.
Outputs land in the recording root as ``parser_observed_<tag>.ndjson`` and
``state_observed_<tag>.ndjson`` per the recorder's output-tag contract.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[4]

BASELINE_TAG = "baseline"
CANDIDATE_TAG = "candidate-2.1.x"
OBSERVED_VERSION = "2.1.1"


def run_arm_a(*, recording_root: Path, replay_root: Path) -> dict[str, Any]:
    """Replay one frozen recording under both detector variants.

    Parameters
    ----------
    recording_root:
        The recorder run root containing ``pane_snapshots.ndjson``.
    replay_root:
        Campaign replay directory for the replay manifest.

    Returns
    -------
    dict
        Replay manifest rows for both variants.
    """

    replay_root.mkdir(parents=True, exist_ok=True)
    results = [
        _run_baseline(recording_root=recording_root),
        _run_candidate(recording_root=recording_root),
    ]
    manifest = {
        "schema_version": 1,
        "recording_root": str(recording_root),
        "observed_version": OBSERVED_VERSION,
        "replayed_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "variants": results,
    }
    (replay_root / "replay-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def _run_baseline(*, recording_root: Path) -> dict[str, Any]:
    """Replay unpatched via the maintained analyze CLI in a subprocess."""

    command = [
        sys.executable,
        "-m",
        "tools.terminal_record",
        "analyze",
        "--run-root",
        str(recording_root),
        "--tool",
        "kimi",
        "--observed-version",
        OBSERVED_VERSION,
        "--output-tag",
        BASELINE_TAG,
    ]
    completed = subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True, timeout=1800)
    row: dict[str, Any] = {
        "tag": BASELINE_TAG,
        "detector_patch": None,
        "command": " ".join(command),
        "returncode": completed.returncode,
    }
    if completed.returncode != 0:
        row["status"] = "error"
        row["error"] = completed.stderr[-2000:]
        return row
    payload = json.loads(completed.stdout.strip().splitlines()[-1])
    row.update(
        status="ok",
        detector_name="kimi_code",
        detector_version=">=0.34.0",
        parser_observed_path=payload["parser_observed_path"],
        state_observed_path=payload["state_observed_path"],
        sample_count=payload["sample_count"],
    )
    return row


def _run_candidate(*, recording_root: Path) -> dict[str, Any]:
    """Replay with the monkey-patched candidate detector in-process."""

    from campaign_lib.patches import CANDIDATE_DETECTOR_VERSION, kimi_2_1_x_patch
    from houmao.terminal_record.service import analyze_terminal_record

    row: dict[str, Any] = {"tag": CANDIDATE_TAG, "detector_patch": "campaign_lib.patches"}
    try:
        with kimi_2_1_x_patch():
            payload = analyze_terminal_record(
                run_root=recording_root,
                tool="kimi",
                observed_version=OBSERVED_VERSION,
                output_tag=CANDIDATE_TAG,
            )
    except Exception as exc:  # noqa: BLE001 - replay failures are evidence
        row.update(status="error", error=repr(exc))
        return row
    row.update(
        status="ok",
        detector_name="kimi_code",
        detector_version=CANDIDATE_DETECTOR_VERSION,
        parser_observed_path=payload["parser_observed_path"],
        state_observed_path=payload["state_observed_path"],
        sample_count=payload["sample_count"],
        returncode=0,
    )
    return row
