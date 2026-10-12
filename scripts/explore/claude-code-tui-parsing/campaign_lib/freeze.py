"""Freeze campaign run evidence with SHA-256 digests.

Implements the iteration-1 freeze gate (plan G1): after the recorder stops,
bind every evidence file by digest, byte size, and row count into
``capture/frozen-evidence.json``. Missing optional files are recorded as
absent rather than as empty placeholders.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_NDJSON_ROW_FILES = {
    "pane_snapshots.ndjson",
    "input_events.ndjson",
    "runtime_observations.ndjson",
    "drive_events.ndjson",
}


def freeze_run(*, run_root: Path, extra_paths: list[Path] | None = None) -> dict[str, Any]:
    """Bind all existing evidence files under one frozen-evidence document.

    Parameters
    ----------
    run_root:
        Campaign run root containing ``capture/``, ``definitions/``, and
        ``launch/`` subtrees.
    extra_paths:
        Additional files to bind beyond the standard evidence set.

    Returns
    -------
    dict
        The frozen-evidence payload, also written to
        ``capture/frozen-evidence.json``.
    """

    candidates = [
        run_root / "definitions" / "task.md",
        run_root / "definitions" / "scenario.json",
        run_root / "launch" / "launch.json",
        run_root / "capture" / "fixture_manifest.json",
        run_root / "capture" / "recording" / "manifest.json",
        run_root / "capture" / "recording" / "pane_snapshots.ndjson",
        run_root / "capture" / "recording" / "input_events.ndjson",
        run_root / "capture" / "recording" / "session.cast",
        run_root / "capture" / "runtime_observations.ndjson",
        run_root / "capture" / "drive_events.ndjson",
    ]
    for path in extra_paths or []:
        if path not in candidates:
            candidates.append(path)

    files: dict[str, Any] = {}
    for path in candidates:
        key = str(path.relative_to(run_root))
        if not path.is_file():
            files[key] = {"present": False}
            continue
        entry: dict[str, Any] = {
            "present": True,
            "sha256": _sha256(path),
            "bytes": path.stat().st_size,
        }
        if path.name in _NDJSON_ROW_FILES:
            entry["rows"] = sum(
                1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
            )
        files[key] = entry

    payload = {
        "schema_version": 1,
        "run_id": run_root.name,
        "frozen_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "files": files,
    }
    target = run_root / "capture" / "frozen-evidence.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def _sha256(path: Path) -> str:
    """Return the SHA-256 hex digest of one file."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()
