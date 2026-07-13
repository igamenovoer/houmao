"""Render UC-03 trace videos from replay-ready long-horizon recordings.

Each output video shows:
- the tmux pane content (terminal text, ANSI codes stripped) on the left,
- the legacy-reference UC-03 label,
- the tracker UC-03 label,
- the public tracked-state fields that determined the labels,
all in a right-hand info panel so the terminal screen remains fully visible.

The script renders every sample at the original 20 Hz capture cadence.

Usage
-----
    pixi run python scripts/qualification/tui-prompt-admission/uc03_render_trace_video.py \
        --run-root tmp/tui-state-tracking-long-horizon/2026-07-13-all-providers \
        --output-root tmp/uc03-trace-videos

Or render a single attempt:

    pixi run python scripts/qualification/tui-prompt-admission/uc03_render_trace_video.py \
        tmp/tui-state-tracking-long-horizon/2026-07-13-all-providers/sessions/claude-st-01/attempts/a007 \
        --output-root tmp/uc03-trace-videos
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from uc03_label import Uc03ReadinessLabel, map_public_state_to_uc03_label


ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
FONT_SIZE = 14
LINE_HEIGHT = 18
MARGIN = 12
INFO_PANEL_WIDTH = 520
INFO_PANEL_MIN_HEIGHT = 360
MAX_VISIBLE_ROWS = 36
FPS = 20


def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from terminal output."""
    return ANSI_ESCAPE_RE.sub("", text)


def _load_ndjson(path: Path) -> list[dict[str, Any]]:
    """Load a newline-delimited JSON file."""
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def _map_sample(record: dict[str, Any]) -> Uc03ReadinessLabel:
    """Map a tracker-timeline or legacy-reference record to a UC-03 label."""

    notes = {str(item) for item in record.get("notes") or []}
    return map_public_state_to_uc03_label(
        turn_phase=record.get("turn_phase"),
        surface_ready_posture=record.get("surface_ready_posture"),
        surface_editing_input=record.get("surface_editing_input"),
        surface_accepting_input=record.get("surface_accepting_input"),
        diagnostics_availability=record.get("diagnostics_availability"),
        active_reasons=record.get("active_reasons") or [],
        ambiguous_interactive_surface=bool(
            record.get("ambiguous_interactive_surface") is True
            or notes
            & {
                "ambiguous_interactive_surface",
                "approval_panel_visible",
                "approval_required",
            }
        ),
    )


def _label_color(label: Uc03ReadinessLabel) -> str:
    """Return a color for a UC-03 label."""
    colors = {
        Uc03ReadinessLabel.READY_IMMEDIATE: "#00aa00",
        Uc03ReadinessLabel.BUSY_ACTIVE: "#cc0000",
        Uc03ReadinessLabel.BUSY_DRAFT: "#ff8800",
        Uc03ReadinessLabel.BUSY_OVERLAY: "#0066cc",
        Uc03ReadinessLabel.INDETERMINATE: "#888888",
    }
    return colors[label]


def _state_summary(record: dict[str, Any]) -> str:
    """Return a short text summary of the public state fields."""
    return (
        f"turn={record.get('turn_phase', '-')}, "
        f"ready={record.get('surface_ready_posture', '-')}, "
        f"editing={record.get('surface_editing_input', '-')}, "
        f"accepting={record.get('surface_accepting_input', '-')}, "
        f"diag={record.get('diagnostics_availability', '-')}, "
        f"active={record.get('active_reasons') or []}"
    )


def _draw_wrapped_text(
    draw: ImageDraw.ImageDraw,
    position: tuple[int, int],
    text: str,
    fill: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
) -> int:
    """Draw comma-separated text wrapped to a maximum width.

    Returns
    -------
    int
        The y-coordinate just below the last drawn line.
    """
    x, y = position
    words = text.split(", ")
    line = ""
    for word in words:
        test_line = f"{line}, {word}" if line else word
        bbox = draw.textbbox((0, 0), test_line, font=font)
        if bbox[2] - bbox[0] <= max_width:
            line = test_line
        else:
            draw.text((x, y), line, fill=fill, font=font)
            y += LINE_HEIGHT
            line = word
    if line:
        draw.text((x, y), line, fill=fill, font=font)
        y += LINE_HEIGHT
    return y


def render_frame(
    snapshot_text: str,
    sample_id: str,
    elapsed: float,
    tracker_label: Uc03ReadinessLabel,
    groundtruth_label: Uc03ReadinessLabel,
    tracker_state: dict[str, Any],
    groundtruth_state: dict[str, Any],
    width: int,
    height: int,
    font: ImageFont.FreeTypeFont,
) -> Image.Image:
    """Render one video frame with the terminal screen on the left and info on the right."""
    image = Image.new("RGB", (width, height), "#1e1e1e")
    draw = ImageDraw.Draw(image)

    # Terminal content on the left, bottom-aligned so the current visible pane
    # stays in a consistent position even when snapshots include scrollback.
    content_lines = snapshot_text.splitlines()
    content_height = len(content_lines) * LINE_HEIGHT
    start_y = max(MARGIN, height - content_height - MARGIN)
    y = start_y
    for line in content_lines:
        draw.text((MARGIN, y), line, fill="#d4d4d4", font=font)
        y += LINE_HEIGHT

    # Vertical separator between terminal and info panel.
    terminal_width = width - INFO_PANEL_WIDTH
    draw.line([(terminal_width, 0), (terminal_width, height)], fill="#444444", width=2)

    # Info panel background on the right.
    draw.rectangle([(terminal_width, 0), (width, height)], fill="#252526")

    # Labels and metadata in the right panel.
    panel_x = terminal_width + MARGIN
    panel_y = MARGIN
    max_text_width = INFO_PANEL_WIDTH - 2 * MARGIN

    draw.text((panel_x, panel_y), f"Sample: {sample_id}", fill="#cccccc", font=font)
    draw.text(
        (panel_x, panel_y + LINE_HEIGHT),
        f"Time: {elapsed:.3f}s",
        fill="#cccccc",
        font=font,
    )

    draw.text(
        (panel_x, panel_y + 3 * LINE_HEIGHT),
        "Legacy reference:",
        fill="#999999",
        font=font,
    )
    draw.text(
        (panel_x, panel_y + 4 * LINE_HEIGHT),
        f"  {groundtruth_label.value}",
        fill=_label_color(groundtruth_label),
        font=font,
    )

    draw.text((panel_x, panel_y + 6 * LINE_HEIGHT), "Tracker:", fill="#999999", font=font)
    draw.text(
        (panel_x, panel_y + 7 * LINE_HEIGHT),
        f"  {tracker_label.value}",
        fill=_label_color(tracker_label),
        font=font,
    )

    # State summaries.
    state_y = panel_y + 9 * LINE_HEIGHT
    draw.text((panel_x, state_y), "GT state:", fill="#999999", font=font)
    state_y = _draw_wrapped_text(
        draw,
        (panel_x, state_y + LINE_HEIGHT),
        _state_summary(groundtruth_state),
        fill="#aaaaaa",
        font=font,
        max_width=max_text_width,
    )

    state_y += LINE_HEIGHT
    draw.text((panel_x, state_y), "TR state:", fill="#999999", font=font)
    _draw_wrapped_text(
        draw,
        (panel_x, state_y + LINE_HEIGHT),
        _state_summary(tracker_state),
        fill="#aaaaaa",
        font=font,
        max_width=max_text_width,
    )

    return image


def render_attempt_video(
    attempt_path: Path,
    output_root: Path,
    schedule: str = "canonical",
    cleanup_frames: bool = True,
) -> Path | None:
    """Render a video for one attempt.

    Parameters
    ----------
    attempt_path
        Root directory of the attempt.
    output_root
        Directory where the output video will be written.
    schedule
        Replay schedule name to read.
    cleanup_frames
        If True, delete temporary PNG frames after encoding.

    Returns
    -------
    Path | None
        Path to the rendered MP4, or None if rendering failed.
    """
    replay_dir = attempt_path / "replay" / "schedules" / schedule
    tracker_path = replay_dir / "tracker-timeline.ndjson"
    groundtruth_path = replay_dir / "groundtruth.ndjson"
    snapshots_path = attempt_path / "recording" / "terminal-record" / "pane_snapshots.ndjson"

    for required_path in (tracker_path, groundtruth_path, snapshots_path):
        if not required_path.exists():
            print(f"Skipping {attempt_path}: missing {required_path.name}", file=sys.stderr)
            return None

    tracker_samples = _load_ndjson(tracker_path)
    groundtruth_samples = _load_ndjson(groundtruth_path)
    snapshots = _load_ndjson(snapshots_path)

    if not tracker_samples or not snapshots:
        print(f"Skipping {attempt_path}: empty data", file=sys.stderr)
        return None

    gt_by_id = {sample["sample_id"]: sample for sample in groundtruth_samples}

    # Determine terminal dimensions from all snapshots so later resizes or
    # content changes do not truncate the interface. Render only the bottom
    # MAX_VISIBLE_ROWS lines of each snapshot (the visible pane), which keeps
    # the video compact while handling the 36-row resize used by ST-04.
    font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    terminal_width = 0
    for snapshot in snapshots:
        for line in strip_ansi(snapshot.get("output_text", "")).splitlines():
            line_width = int(font.getlength(line))
            if line_width > terminal_width:
                terminal_width = line_width
    terminal_width += 2 * MARGIN
    terminal_height = MAX_VISIBLE_ROWS * LINE_HEIGHT + 2 * MARGIN

    # Side-by-side layout: terminal on the left, info panel on the right.
    total_width = terminal_width + INFO_PANEL_WIDTH
    total_height = max(terminal_height, INFO_PANEL_MIN_HEIGHT)

    # libx264/yuv420p requires even dimensions.
    total_width = (total_width + 1) // 2 * 2
    total_height = (total_height + 1) // 2 * 2

    # attempt_path = .../sessions/<provider-cell>/attempts/<attempt>
    cell_name = attempt_path.parent.parent.name
    attempt_name = attempt_path.name
    video_name = f"{cell_name}-{attempt_name}"
    output_dir = output_root / video_name
    output_dir.mkdir(parents=True, exist_ok=True)
    frames_dir = output_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    output_video = output_dir / "trace.mp4"

    print(f"Rendering {video_name}: {len(snapshots)} frames at {total_width}x{total_height}...")

    for index, snapshot in enumerate(snapshots):
        sample_id = snapshot.get("sample_id", f"s{index:06d}")
        tracker_sample = next((s for s in tracker_samples if s["sample_id"] == sample_id), None)
        groundtruth_sample = gt_by_id.get(sample_id)

        if tracker_sample is None or groundtruth_sample is None:
            continue

        tracker_label = _map_sample(tracker_sample)
        groundtruth_label = _map_sample(groundtruth_sample)

        # Keep only the bottom MAX_VISIBLE_ROWS lines (visible pane).
        snapshot_lines = strip_ansi(snapshot.get("output_text", "")).splitlines()
        snapshot_text = "\n".join(snapshot_lines[-MAX_VISIBLE_ROWS:])
        frame = render_frame(
            snapshot_text=snapshot_text,
            sample_id=sample_id,
            elapsed=snapshot.get("elapsed_seconds", 0.0),
            tracker_label=tracker_label,
            groundtruth_label=groundtruth_label,
            tracker_state={
                "turn_phase": tracker_sample.get("turn_phase"),
                "surface_ready_posture": tracker_sample.get("surface_ready_posture"),
                "surface_editing_input": tracker_sample.get("surface_editing_input"),
                "surface_accepting_input": tracker_sample.get("surface_accepting_input"),
                "diagnostics_availability": tracker_sample.get("diagnostics_availability"),
                "active_reasons": tracker_sample.get("active_reasons") or [],
            },
            groundtruth_state={
                "turn_phase": groundtruth_sample.get("turn_phase"),
                "surface_ready_posture": groundtruth_sample.get("surface_ready_posture"),
                "surface_editing_input": groundtruth_sample.get("surface_editing_input"),
                "surface_accepting_input": groundtruth_sample.get("surface_accepting_input"),
                "diagnostics_availability": groundtruth_sample.get("diagnostics_availability"),
                "active_reasons": groundtruth_sample.get("active_reasons") or [],
            },
            width=total_width,
            height=total_height,
            font=font,
        )
        frame.save(frames_dir / f"frame_{index:06d}.png")

    # Encode with ffmpeg.
    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-framerate",
        str(FPS),
        "-i",
        str(frames_dir / "frame_%06d.png"),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-crf",
        "23",
        str(output_video),
    ]
    subprocess.run(ffmpeg_cmd, check=True, capture_output=True, text=True)

    if cleanup_frames:
        shutil.rmtree(frames_dir)

    print(f"Wrote {output_video}")
    return output_video


# Replay-ready attempts listed in 20260713T095944Z-long-horizon-test-report.md.
REPLAY_READY_ATTEMPTS: list[tuple[str, str, str]] = [
    ("claude", "st-01", "a007"),
    ("claude", "st-02", "a001"),
    ("claude", "st-03", "a001"),
    ("codex", "st-01", "a004"),
    ("codex", "st-03", "a004"),
    ("codex", "st-04", "a002"),
    ("codex", "st-05", "a004"),
    ("kimi", "st-03", "a008"),
    ("kimi", "st-04", "a003"),
]


def _resolve_attempts_from_run_root(run_root: Path) -> list[Path]:
    """Resolve the known replay-ready attempt paths under a run root."""
    attempts: list[Path] = []
    for provider, cell, attempt in REPLAY_READY_ATTEMPTS:
        attempt_path = run_root / "sessions" / f"{provider}-{cell}" / "attempts" / attempt
        if attempt_path.exists():
            attempts.append(attempt_path)
        else:
            print(
                f"Warning: expected replay-ready attempt not found: {attempt_path}",
                file=sys.stderr,
            )
    return attempts


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Render UC-03 trace videos from replay-ready recordings."
    )
    parser.add_argument(
        "attempts",
        nargs="*",
        type=Path,
        help="Attempt root directories to render.",
    )
    parser.add_argument(
        "--run-root",
        type=Path,
        help="Long-horizon run root; render known replay-ready attempts.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("tmp/uc03-trace-videos"),
        help="Output directory for rendered videos (default: tmp/uc03-trace-videos).",
    )
    parser.add_argument(
        "--schedule",
        default="canonical",
        help="Replay schedule to read (default: canonical).",
    )
    parser.add_argument(
        "--keep-frames",
        action="store_true",
        help="Keep temporary PNG frames after encoding.",
    )
    args = parser.parse_args()

    attempt_paths: list[Path] = list(args.attempts)
    if args.run_root:
        attempt_paths.extend(_resolve_attempts_from_run_root(args.run_root))

    if not attempt_paths:
        parser.error("Provide at least one attempt path or --run-root.")

    args.output_root.mkdir(parents=True, exist_ok=True)

    rendered: list[Path] = []
    for attempt_path in attempt_paths:
        video_path = render_attempt_video(
            attempt_path,
            args.output_root,
            schedule=args.schedule,
            cleanup_frames=not args.keep_frames,
        )
        if video_path:
            rendered.append(video_path)

    print(f"Rendered {len(rendered)} video(s) to {args.output_root}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
