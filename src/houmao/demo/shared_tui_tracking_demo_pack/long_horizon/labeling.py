"""Blind-review artifacts and completion checks for long-horizon recordings."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, cast

from houmao.demo.shared_tui_tracking_demo_pack.groundtruth import (
    expand_labels_to_groundtruth_timeline,
    load_fixture_inputs,
)
from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.attempts import (
    load_attempt_state,
    transition_attempt,
)
from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.paths import save_json_atomic
from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.projects import (
    recording_evidence_sha256,
)
from houmao.demo.shared_tui_tracking_demo_pack.review_video import (
    encode_review_video,
    render_unlabeled_review_frames,
)


_REQUIRED_FIELDS = (
    "diagnostics_availability",
    "surface_accepting_input",
    "surface_editing_input",
    "surface_ready_posture",
    "turn_phase",
    "last_turn_result",
    "last_turn_source",
)


def prepare_blind_review(
    *,
    attempt_root: Path,
    fps: float = 5.0,
    render_video: bool = True,
) -> dict[str, Any]:
    """Create terminal-only review assets and an empty aligned label template."""

    state = load_attempt_state(attempt_root=attempt_root)
    if state.phase != "awaiting_manual_labels":
        raise ValueError(f"Blind review requires awaiting_manual_labels, got {state.phase}")
    _require_replay_empty(attempt_root=attempt_root)
    recording_root = attempt_root / "recording" / "terminal-record"
    recording_digest = recording_evidence_sha256(recording_root)
    if state.input_digests.get("recording") != recording_digest:
        raise ValueError("Frozen recording digest changed before manual labeling")
    fixture = load_fixture_inputs(recording_root=recording_root)
    labels_dir = attempt_root / "labels"
    template_path = labels_dir / "label-template.json"
    payload = {
        "schema_version": 1,
        "recording_sha256": recording_digest,
        "required_expectation_fields": list(_REQUIRED_FIELDS),
        "sample_count": len(fixture.snapshots),
        "samples": [
            {
                "sample_id": item.sample_id,
                "elapsed_seconds": item.elapsed_seconds,
                "ts_utc": item.ts_utc,
            }
            for item in fixture.snapshots
        ],
        "labels": [],
    }
    save_json_atomic(template_path, payload)
    if render_video:
        frames_dir = labels_dir / "blind-review-frames"
        render_unlabeled_review_frames(
            snapshots=fixture.snapshots,
            output_dir=frames_dir,
            fps=fps,
        )
        encode_review_video(
            frames_dir=frames_dir,
            output_path=labels_dir / "blind-review.mp4",
            fps=fps,
        )
        shutil.rmtree(frames_dir)
    manifest = {
        "schema_version": 1,
        "recording_sha256": recording_digest,
        "sample_count": len(fixture.snapshots),
        "template_path": str(template_path),
        "review_video_path": str(labels_dir / "blind-review.mp4") if render_video else None,
        "tracker_artifacts_present": False,
    }
    save_json_atomic(labels_dir / "blind-review-manifest.json", manifest)
    return manifest


def complete_manual_labels(*, attempt_root: Path, labels_path: Path) -> dict[str, Any]:
    """Validate, copy, digest, and freeze one complete blind label set."""

    state = load_attempt_state(attempt_root=attempt_root)
    if state.phase != "awaiting_manual_labels":
        raise ValueError(f"Label completion requires awaiting_manual_labels, got {state.phase}")
    _require_replay_empty(attempt_root=attempt_root)
    recording_root = attempt_root / "recording" / "terminal-record"
    recording_digest = recording_evidence_sha256(recording_root)
    if state.input_digests.get("recording") != recording_digest:
        raise ValueError("Frozen recording digest changed before label completion")
    payload = _load_object(labels_path)
    declared_digest = payload.pop("recording_sha256", recording_digest)
    if declared_digest != recording_digest:
        raise ValueError("Label recording digest does not match frozen recording")
    effective_labels = attempt_root / "labels" / "labels.json"
    save_json_atomic(effective_labels, payload)
    try:
        timeline = expand_labels_to_groundtruth_timeline(
            recording_root=recording_root,
            labels_path=effective_labels,
        )
    except BaseException:
        effective_labels.unlink(missing_ok=True)
        raise
    label_digest = hashlib.sha256(effective_labels.read_bytes()).hexdigest()
    completion = {
        "schema_version": 1,
        "recording_sha256": recording_digest,
        "labels_sha256": label_digest,
        "sample_count": len(timeline),
        "labels_path": str(effective_labels),
    }
    save_json_atomic(attempt_root / "labels" / "labels-complete.json", completion)
    transition_attempt(
        attempt_root=attempt_root,
        expected_phase="awaiting_manual_labels",
        new_phase="labels_complete",
        input_digests={"recording": recording_digest, "labels": label_digest},
    )
    return completion


def validate_label_completion(*, attempt_root: Path) -> dict[str, Any]:
    """Validate frozen recording and label digests for replay admission."""

    state = load_attempt_state(attempt_root=attempt_root)
    if state.phase not in {"labels_complete", "replaying", "reported"}:
        raise ValueError(f"Labels are not complete: {state.phase}")
    completion = _load_object(attempt_root / "labels" / "labels-complete.json")
    recording_root = attempt_root / "recording" / "terminal-record"
    labels_path = attempt_root / "labels" / "labels.json"
    observed_recording = recording_evidence_sha256(recording_root)
    observed_labels = hashlib.sha256(labels_path.read_bytes()).hexdigest()
    if completion.get("recording_sha256") != observed_recording:
        raise ValueError("Completed recording digest is stale")
    if completion.get("labels_sha256") != observed_labels:
        raise ValueError("Completed label digest is stale")
    if state.input_digests.get("recording") != observed_recording:
        raise ValueError("Attempt recording digest is stale")
    if state.input_digests.get("labels") != observed_labels:
        raise ValueError("Attempt labels digest is stale")
    return completion


def _require_replay_empty(*, attempt_root: Path) -> None:
    """Reject any tracker artifact before blind labels are complete."""

    replay_dir = attempt_root / "replay"
    if replay_dir.exists() and any(replay_dir.iterdir()):
        raise ValueError("Replay artifacts exist before manual label completion")


def _load_object(path: Path) -> dict[str, Any]:
    """Load one JSON object."""

    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return cast(dict[str, Any], value)
