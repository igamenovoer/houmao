"""Arm A replay harness: fallback baseline, 0.144.x baseline, patched candidate.

Arm A1 replays the frozen ``pane_snapshots.ndjson`` through the maintained
``analyze_terminal_record`` path with ``observed_version=0.162.1`` — the
resolution operators get today (the fallback detector). Arm A2 replays the same
stream with ``observed_version=0.144.0``, forcing the newest maintained
profile. The candidate variant (added after the gap analysis) runs in-process
under ``campaign_lib.patches.codex_0_162_x_patch`` with the true observed
version. Outputs land in the recording root as ``parser_observed_<tag>.ndjson``
and ``state_observed_<tag>.ndjson`` per the recorder's output-tag contract.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[4]

BASELINE_FALLBACK_TAG = "baseline-fallback"
BASELINE_0144_TAG = "baseline-0.144.x"
CANDIDATE_TAG = "candidate-0.162.x"
OBSERVED_VERSION_LIVE = "0.162.1"
OBSERVED_VERSION_0144 = "0.144.0"


def run_arm_a(
    *, recording_root: Path, replay_root: Path, include_candidate: bool = True
) -> dict[str, Any]:
    """Replay one frozen recording under the declared detector variants.

    Parameters
    ----------
    recording_root:
        The recorder run root containing ``pane_snapshots.ndjson``.
    replay_root:
        Campaign replay directory for the replay manifest.
    include_candidate:
        When true, also run the monkey-patched candidate variant. Set false
        for the pre-repair baselines, before a candidate patch exists.

    Returns
    -------
    dict
        Replay manifest rows for all variants.
    """

    replay_root.mkdir(parents=True, exist_ok=True)
    results = [
        _run_baseline(
            recording_root=recording_root,
            tag=BASELINE_FALLBACK_TAG,
            observed_version=OBSERVED_VERSION_LIVE,
        ),
        _run_baseline(
            recording_root=recording_root,
            tag=BASELINE_0144_TAG,
            observed_version=OBSERVED_VERSION_0144,
        ),
    ]
    if include_candidate:
        results.append(_run_candidate(recording_root=recording_root))
    manifest = {
        "schema_version": 1,
        "recording_root": str(recording_root),
        "replayed_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "variants": results,
    }
    (replay_root / "replay-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def _run_baseline(*, recording_root: Path, tag: str, observed_version: str) -> dict[str, Any]:
    """Replay unpatched via the maintained analyze CLI in a subprocess."""

    command = [
        sys.executable,
        "-m",
        "tools.terminal_record",
        "analyze",
        "--run-root",
        str(recording_root),
        "--tool",
        "codex",
        "--observed-version",
        observed_version,
        "--output-tag",
        tag,
    ]
    completed = subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True, timeout=1800)
    row: dict[str, Any] = {
        "tag": tag,
        "detector_patch": None,
        "observed_version": observed_version,
        "command": " ".join(command),
        "returncode": completed.returncode,
    }
    if completed.returncode != 0:
        row["status"] = "error"
        row["error"] = completed.stderr[-2000:]
        return row
    text = completed.stdout.strip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        payload = json.loads(text[start:]) if start >= 0 else {}
    row.update(
        status="ok",
        detector_name="codex_tui",
        parser_observed_path=payload["parser_observed_path"],
        state_observed_path=payload["state_observed_path"],
        sample_count=payload["sample_count"],
    )
    return row


def _run_candidate(*, recording_root: Path) -> dict[str, Any]:
    """Replay with the monkey-patched candidate detector in-process."""

    from campaign_lib.patches import CANDIDATE_DETECTOR_VERSION, codex_0_162_x_patch
    from houmao.terminal_record.service import analyze_terminal_record

    row: dict[str, Any] = {"tag": CANDIDATE_TAG, "detector_patch": "campaign_lib.patches"}
    try:
        with codex_0_162_x_patch():
            payload = analyze_terminal_record(
                run_root=recording_root,
                tool="codex",
                observed_version=OBSERVED_VERSION_LIVE,
                output_tag=CANDIDATE_TAG,
            )
    except Exception as exc:  # noqa: BLE001 - replay failures are evidence
        row.update(status="error", error=repr(exc))
        return row
    row.update(
        status="ok",
        detector_name="codex_tui",
        detector_version=CANDIDATE_DETECTOR_VERSION,
        parser_observed_path=payload["parser_observed_path"],
        state_observed_path=payload["state_observed_path"],
        sample_count=payload["sample_count"],
        returncode=0,
    )
    return row
