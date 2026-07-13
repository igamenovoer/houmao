"""Tests for bounded blind-review frame derivation."""

from pathlib import Path

import pytest

from houmao.demo.shared_tui_tracking_demo_pack.review_video import (
    render_unlabeled_review_frames,
)
from houmao.terminal_record.models import TerminalRecordPaneSnapshot


def test_unlabeled_review_uses_requested_rate(tmp_path: Path) -> None:
    """A 20 Hz source does not expand into 20 Hz PNGs for a 2 Hz review."""

    snapshots = [
        TerminalRecordPaneSnapshot(
            sample_id=f"s{index:06d}",
            elapsed_seconds=index / 20,
            ts_utc=f"2026-07-13T00:00:{index:02d}Z",
            target_pane_id="%1",
            output_text=f"frame {index}",
        )
        for index in range(21)
    ]

    paths = render_unlabeled_review_frames(
        snapshots=snapshots,
        output_dir=tmp_path / "frames",
        fps=2.0,
        width=640,
        height=360,
    )

    assert [item.name for item in paths] == [
        "frame-000001.png",
        "frame-000002.png",
        "frame-000003.png",
    ]


def test_unlabeled_review_rejects_nonpositive_rate(tmp_path: Path) -> None:
    """Review schedules require a positive cadence."""

    with pytest.raises(ValueError, match="fps must be positive"):
        render_unlabeled_review_frames(snapshots=[], output_dir=tmp_path, fps=0)
