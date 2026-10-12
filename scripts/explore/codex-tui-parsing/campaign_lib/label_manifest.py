"""Freeze blind ground-truth labels with provenance (plan G3).

Writes ``labels/labels-manifest.json`` binding the frozen recording digest,
the labels digest, labeler identity, and the independence declaration. Run
after the complete label set is authored with ``tools.terminal_record
add-label`` and before any replay.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path


def write_labels_manifest(
    *,
    run_root: Path,
    labeler: str,
    settle_seconds: float = 1.0,
    known_ambiguities: list[str] | None = None,
) -> dict:
    """Write the labels manifest and return its payload."""

    recording_path = run_root / "capture" / "recording" / "pane_snapshots.ndjson"
    labels_path = run_root / "labels" / "labels.json"
    if not recording_path.is_file():
        raise FileNotFoundError(f"missing recording at {recording_path}")
    if not labels_path.is_file():
        raise FileNotFoundError(f"missing labels at {labels_path}")

    payload = {
        "schema_version": 1,
        "run_id": run_root.name,
        "source_recording_sha256": _sha256(recording_path),
        "labels_sha256": _sha256(labels_path),
        "labeler": labeler,
        "labeled_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "public_state_schema": "houmao.shared_tui_tracking TrackedTimelineState fields (8)",
        "settle_seconds": settle_seconds,
        "independence": (
            "Labels authored from raw pane snapshots, runtime observations, and drive "
            "events only; no detector, parser, tracker, or replay output was inspected "
            "before or during labeling."
        ),
        "known_ambiguities": known_ambiguities or [],
    }
    target = run_root / "labels" / "labels-manifest.json"
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def _sha256(path: Path) -> str:
    """Return the SHA-256 hex digest of one file."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    """CLI entrypoint for freezing a labels manifest."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--labeler", default="campaign-operator")
    parser.add_argument("--settle-seconds", type=float, default=1.0)
    parser.add_argument("--ambiguity", action="append", default=[])
    args = parser.parse_args()
    payload = write_labels_manifest(
        run_root=args.run_root.resolve(),
        labeler=args.labeler,
        settle_seconds=args.settle_seconds,
        known_ambiguities=list(args.ambiguity),
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
