"""Unit tests for the evidence freeze gate."""

from __future__ import annotations

import json
from pathlib import Path

from tui_pending_state_capture.freeze import file_digest, freeze_recording, save_frozen_evidence
from tui_pending_state_capture.models import FileDigest


def test_file_digest_computes_sha256_and_rows(tmp_path: Path) -> None:
    path = tmp_path / "rows.ndjson"
    path.write_text('{"a": 1}\n{"b": 2}\n\n', encoding="utf-8")
    digest = file_digest(path)

    assert digest.path == str(path)
    assert len(digest.sha256) == 64
    assert digest.bytes == path.stat().st_size
    assert digest.rows == 2


def test_freeze_recording_includes_expected_artifacts(tmp_path: Path) -> None:
    recording_root = tmp_path / "recording"
    recording_root.mkdir()
    for name in ("manifest.json", "pane_snapshots.ndjson", "input_events.ndjson", "session.cast"):
        (recording_root / name).write_text(f"{name}\n", encoding="utf-8")

    lifecycle = tmp_path / "lifecycle.json"
    labels = tmp_path / "labels.json"
    summary = tmp_path / "labels-summary.json"
    lifecycle.write_text("{}", encoding="utf-8")
    labels.write_text("{}", encoding="utf-8")
    summary.write_text("{}", encoding="utf-8")

    video = FileDigest(path=str(tmp_path / "video.mp4"), sha256="a" * 64, bytes=123)

    evidence = freeze_recording(
        recording_root=recording_root,
        lifecycle_manifest_path=lifecycle,
        labels_path=labels,
        labels_summary_path=summary,
        provider="codex",
        calibrated_version="test",
        run_tainted=True,
        taint_reasons=("unsupported_pending_behavior",),
        transition_times={"active_onset": 1.0},
        video_digest=video,
    )

    assert evidence.run_tainted
    assert "unsupported_pending_behavior" in evidence.taint_reasons
    artifact_paths = {item.path for item in evidence.artifacts}
    assert any(str(recording_root / "manifest.json") in item for item in artifact_paths)
    assert any(str(lifecycle) in item for item in artifact_paths)
    assert evidence.video is not None
    assert evidence.video.sha256 == "a" * 64


def test_save_frozen_evidence_round_trip(tmp_path: Path) -> None:
    recording_root = tmp_path / "recording"
    recording_root.mkdir()
    (recording_root / "manifest.json").write_text("{}", encoding="utf-8")
    (recording_root / "pane_snapshots.ndjson").write_text("\n", encoding="utf-8")
    (recording_root / "input_events.ndjson").write_text("\n", encoding="utf-8")
    (recording_root / "session.cast").write_text("\n", encoding="utf-8")

    lifecycle = tmp_path / "lifecycle.json"
    labels = tmp_path / "labels.json"
    summary = tmp_path / "labels-summary.json"
    for path in (lifecycle, labels, summary):
        path.write_text("{}", encoding="utf-8")

    evidence = freeze_recording(
        recording_root=recording_root,
        lifecycle_manifest_path=lifecycle,
        labels_path=labels,
        labels_summary_path=summary,
        provider="kimi",
        calibrated_version="test",
        run_tainted=False,
        taint_reasons=(),
        transition_times={"active_onset": None},
    )

    from tui_pending_state_capture.freeze import load_frozen_evidence

    output = tmp_path / "frozen-evidence.json"
    save_frozen_evidence(path=output, evidence=evidence)
    loaded = load_frozen_evidence(output)

    assert loaded.provider == "kimi"
    assert loaded.run_tainted is False
    assert loaded.transition_times["active_onset"] is None
    assert json.loads(output.read_text(encoding="utf-8"))["schema_version"] == 1


def test_freeze_without_video_digest_omits_video(tmp_path: Path) -> None:
    recording_root = tmp_path / "recording"
    recording_root.mkdir()
    (recording_root / "manifest.json").write_text("{}", encoding="utf-8")
    (recording_root / "pane_snapshots.ndjson").write_text("\n", encoding="utf-8")
    (recording_root / "input_events.ndjson").write_text("\n", encoding="utf-8")
    (recording_root / "session.cast").write_text("\n", encoding="utf-8")

    lifecycle = tmp_path / "lifecycle.json"
    labels = tmp_path / "labels.json"
    summary = tmp_path / "labels-summary.json"
    for path in (lifecycle, labels, summary):
        path.write_text("{}", encoding="utf-8")

    evidence = freeze_recording(
        recording_root=recording_root,
        lifecycle_manifest_path=lifecycle,
        labels_path=labels,
        labels_summary_path=summary,
        provider="claude",
        calibrated_version="test",
        run_tainted=False,
        taint_reasons=(),
        transition_times={},
    )

    assert evidence.video is None
