"""Evidence freeze gate: digests, sizes, and immutable metadata."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from .models import FileDigest, FrozenEvidence, ProviderName


ARTIFACT_NAMES = (
    "manifest.json",
    "pane_snapshots.ndjson",
    "input_events.ndjson",
    "session.cast",
)


def file_digest(path: Path) -> FileDigest:
    """Return SHA-256, byte size, and NDJSON row count for one path."""

    sha256 = hashlib.sha256()
    rows = 0
    with path.open("rb") as handle:
        for line in handle:
            if line.strip():
                rows += 1
            sha256.update(line)
    return FileDigest(
        path=str(path),
        sha256=sha256.hexdigest(),
        bytes=path.stat().st_size,
        rows=rows if path.suffix == ".ndjson" else None,
    )


def freeze_recording(
    *,
    recording_root: Path,
    lifecycle_manifest_path: Path,
    labels_path: Path,
    labels_summary_path: Path,
    provider: ProviderName,
    calibrated_version: str,
    run_tainted: bool,
    taint_reasons: tuple[str, ...],
    transition_times: dict[str, float | None],
    observed_pending_count: int | None = None,
    target_pending_count: int | None = None,
    video_digest: FileDigest | None = None,
) -> FrozenEvidence:
    """Compute digests and write ``frozen-evidence.json``."""

    artifacts: list[FileDigest] = []
    for name in ARTIFACT_NAMES:
        artifact_path = recording_root / name
        if artifact_path.is_file():
            artifacts.append(file_digest(artifact_path))
    for extra_path in (
        lifecycle_manifest_path,
        labels_path,
        labels_summary_path,
    ):
        if extra_path.is_file():
            artifacts.append(file_digest(extra_path))

    evidence = FrozenEvidence(
        schema_version=1,
        provider=provider,
        calibrated_version=calibrated_version,
        run_tainted=run_tainted or bool(taint_reasons),
        taint_reasons=taint_reasons,
        generated_at_utc=datetime.now(UTC).isoformat(timespec="seconds"),
        artifacts=tuple(artifacts),
        transition_times=transition_times,
        observed_pending_count=observed_pending_count,
        target_pending_count=target_pending_count,
        video=video_digest,
    )
    return evidence


def save_frozen_evidence(*, path: Path, evidence: FrozenEvidence) -> None:
    """Persist the frozen-evidence gate to disk."""

    payload = {
        "schema_version": evidence.schema_version,
        "provider": evidence.provider,
        "calibrated_version": evidence.calibrated_version,
        "run_tainted": evidence.run_tainted,
        "taint_reasons": list(evidence.taint_reasons),
        "generated_at_utc": evidence.generated_at_utc,
        "artifacts": [asdict(item) for item in evidence.artifacts],
        "transition_times": evidence.transition_times,
        "observed_pending_count": evidence.observed_pending_count,
        "target_pending_count": evidence.target_pending_count,
    }
    if evidence.video is not None:
        payload["video"] = asdict(evidence.video)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_frozen_evidence(path: Path) -> FrozenEvidence:
    """Load a previously written frozen-evidence gate."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    video_payload = payload.get("video")
    video = _video_digest_from_payload(video_payload) if video_payload is not None else None
    return FrozenEvidence(
        schema_version=int(payload.get("schema_version", 1)),
        provider=cast(ProviderName, str(payload["provider"])),
        calibrated_version=str(payload["calibrated_version"]),
        run_tainted=bool(payload.get("run_tainted")),
        taint_reasons=tuple(str(item) for item in payload.get("taint_reasons", [])),
        generated_at_utc=str(payload["generated_at_utc"]),
        artifacts=tuple(
            FileDigest(
                path=str(item["path"]),
                sha256=str(item["sha256"]),
                bytes=int(item["bytes"]),
                rows=int(item["rows"]) if item.get("rows") is not None else None,
            )
            for item in payload["artifacts"]
        ),
        transition_times={
            str(key): float(value) if value is not None else None
            for key, value in payload.get("transition_times", {}).items()
        },
        observed_pending_count=payload.get("observed_pending_count"),
        target_pending_count=payload.get("target_pending_count"),
        video=video,
    )


def _video_digest_from_payload(video_payload: dict[str, Any]) -> FileDigest:
    """Parse one video FileDigest from a frozen-evidence payload."""

    return FileDigest(
        path=str(video_payload["path"]),
        sha256=str(video_payload["sha256"]),
        bytes=int(video_payload["bytes"]),
        rows=int(video_payload["rows"]) if video_payload.get("rows") is not None else None,
    )
