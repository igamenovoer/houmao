"""Unit tests for automated binary labeling."""

from __future__ import annotations

from houmao.terminal_record.models import TerminalRecordPaneSnapshot

from tui_pending_state_capture.labels import analyze_snapshots
from tui_pending_state_capture.models import LifecycleManifest, PatternSpec, PendingCountPatterns


def _snapshot(sample_id: str, output_text: str) -> TerminalRecordPaneSnapshot:
    return TerminalRecordPaneSnapshot(
        sample_id=sample_id,
        elapsed_seconds=0.0,
        ts_utc="2026-01-01T00:00:00",
        target_pane_id="%0",
        output_text=output_text,
        target_pane_width=80,
        target_pane_height=24,
    )


def _manifest() -> LifecycleManifest:
    return LifecycleManifest(
        schema_version=1,
        provider="codex",
        calibrated_version="test",
        patterns={
            "ready": PatternSpec(name="ready", regex="prompt ❯", description=""),
            "active": PatternSpec(name="active", regex="Working", description=""),
            "pending": PatternSpec(name="pending", regex="pending", description=""),
        },
        prompts={},
        steps=(),
    )


def test_ready_snapshot_labels_accept_input() -> None:
    snapshots = (_snapshot("s1", "prompt ❯ "),)
    labels, summary = analyze_snapshots(manifest=_manifest(), snapshots=snapshots)

    row = labels["s1"]
    assert row.can_accept_input == "yes"
    assert row.has_pending_message == "no"
    assert row.pending_count == 0
    assert "ready" in row.evidence_note


def test_active_snapshot_labels_busy() -> None:
    snapshots = (_snapshot("s1", "Working on it..."),)
    labels, summary = analyze_snapshots(manifest=_manifest(), snapshots=snapshots)

    row = labels["s1"]
    assert row.can_accept_input == "no"
    assert row.has_pending_message == "no"
    assert row.pending_count == 0


def test_pending_snapshot_labels_busy_and_pending() -> None:
    snapshots = (_snapshot("s1", "Working (1 tool) | pending message"),)
    labels, summary = analyze_snapshots(manifest=_manifest(), snapshots=snapshots)

    row = labels["s1"]
    assert row.can_accept_input == "no"
    assert row.has_pending_message == "yes"
    assert row.pending_count == "unknown"


def test_unknown_when_no_patterns_match() -> None:
    snapshots = (_snapshot("s1", "garbage text"),)
    labels, summary = analyze_snapshots(manifest=_manifest(), snapshots=snapshots)

    row = labels["s1"]
    assert row.can_accept_input == "unknown"
    assert row.has_pending_message == "unknown"
    assert row.pending_count == "unknown"


def test_summary_counts_and_spans() -> None:
    snapshots = (
        _snapshot("s1", "prompt ❯ "),
        _snapshot("s2", "prompt ❯ "),
        _snapshot("s3", "Working..."),
        _snapshot("s4", "Working..."),
    )
    labels, summary = analyze_snapshots(manifest=_manifest(), snapshots=snapshots)

    assert summary.total_samples == 4
    assert summary.counts["can_accept_input_yes"] == 2
    assert summary.counts["can_accept_input_no"] == 2
    assert summary.counts["pending_count_0"] == 4
    assert len(summary.spans) == 2
    assert summary.spans[0].first_sample_id == "s1"
    assert summary.spans[0].last_sample_id == "s2"
    assert summary.spans[1].first_sample_id == "s3"
    assert summary.spans[1].last_sample_id == "s4"


def _manifest_with_count_markers(marker_regex: str) -> LifecycleManifest:
    return LifecycleManifest(
        schema_version=1,
        provider="codex",
        calibrated_version="test",
        patterns={
            "ready": PatternSpec(name="ready", regex="prompt ❯", description=""),
            "active": PatternSpec(name="active", regex="Working", description=""),
            "pending": PatternSpec(name="pending", regex="pending", description=""),
        },
        pending_count_patterns=PendingCountPatterns(
            extractor="count_markers",
            marker_regex=marker_regex,
        ),
        prompts={},
        steps=(),
    )


def test_pending_count_from_markers() -> None:
    text = "pending:\n  ↳ first\n  ↳ second\n  ↳ third"
    snapshots = (_snapshot("s1", text),)
    manifest = _manifest_with_count_markers(r"^\s*↳\s")
    labels, summary = analyze_snapshots(manifest=manifest, snapshots=snapshots)

    assert labels["s1"].pending_count == 3
    assert summary.counts["pending_count_3"] == 1


def test_pending_count_caps_at_unknown_when_markers_exceed_three() -> None:
    text = "pending:\n  ↳ a\n  ↳ b\n  ↳ c\n  ↳ d"
    snapshots = (_snapshot("s1", text),)
    manifest = _manifest_with_count_markers(r"^\s*↳\s")
    labels, summary = analyze_snapshots(manifest=manifest, snapshots=snapshots)

    assert labels["s1"].pending_count == "unknown"


def test_pending_count_regex_group_extractor() -> None:
    manifest = LifecycleManifest(
        schema_version=1,
        provider="codex",
        calibrated_version="test",
        patterns={
            "ready": PatternSpec(name="ready", regex="prompt ❯", description=""),
            "active": PatternSpec(name="active", regex="Working", description=""),
            "pending": PatternSpec(name="pending", regex="pending", description=""),
        },
        pending_count_patterns=PendingCountPatterns(
            extractor="regex_group",
            regex=r"(\d+) messages to be submitted",
            group_index=1,
        ),
        prompts={},
        steps=(),
    )
    snapshots = (_snapshot("s1", "pending: 2 messages to be submitted after next tool call"),)
    labels, summary = analyze_snapshots(manifest=manifest, snapshots=snapshots)

    assert labels["s1"].pending_count == 2
    assert summary.counts["pending_count_2"] == 1
