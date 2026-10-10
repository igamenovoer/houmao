"""Gate: recording integrity (plan G1/G5).

Verifies the recorder finalized cleanly and every file bound in
``capture/frozen-evidence.json`` still matches its recorded digest.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import result, sha256_file  # noqa: E402


def get_assert(output: dict, context) -> dict:  # noqa: ARG001 - promptfoo contract
    """Check recorder finalization and frozen-evidence digest integrity."""

    run_root = Path(output["run_root"])
    recording_root = Path(output["recording_root"])
    manifest_path = recording_root / "manifest.json"
    frozen_path = run_root / "capture" / "frozen-evidence.json"

    problems: list[str] = []
    if not manifest_path.is_file():
        return result(passed=False, reason=f"missing recorder manifest at {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not manifest.get("stopped_at_utc") or not manifest.get("stop_reason"):
        problems.append("recorder never stopped (no stopped_at_utc/stop_reason)")
    for required in ("pane_snapshots.ndjson", "input_events.ndjson"):
        if not (recording_root / required).is_file():
            problems.append(f"missing {required}")

    taints = list(manifest.get("taint_reasons") or [])
    if not frozen_path.is_file():
        problems.append("missing capture/frozen-evidence.json")
    else:
        frozen = json.loads(frozen_path.read_text(encoding="utf-8"))
        for relative, entry in frozen.get("files", {}).items():
            path = run_root / relative
            if not entry.get("present"):
                continue
            if not path.is_file():
                problems.append(f"bound file now missing: {relative}")
                continue
            if sha256_file(path) != entry.get("sha256"):
                problems.append(f"digest mismatch: {relative}")

    reason = "recording intact"
    if taints:
        reason = f"taint recorded: {', '.join(taints)}"
    if problems:
        return result(passed=False, reason="; ".join(problems))
    return result(passed=True, reason=reason)
