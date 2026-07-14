"""Render a labeled review video from frozen snapshots and binary labels."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import cast

from PIL import Image, ImageDraw, ImageFont

from .labels import load_snapshots
from .models import LabelRow, PendingCountLabel

ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")
FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
)
FONT_SIZE = 14
LINE_HEIGHT = 18
MARGIN = 12
INFO_PANEL_WIDTH = 420
INFO_PANEL_MIN_HEIGHT = 360
MAX_VISIBLE_ROWS = 36


def _resolve_font() -> ImageFont.FreeTypeFont:
    for candidate in FONT_CANDIDATES:
        path = Path(candidate)
        if path.is_file():
            return ImageFont.truetype(str(path), FONT_SIZE)
    return cast(ImageFont.FreeTypeFont, ImageFont.load_default())


def strip_ansi(text: str) -> str:
    """Remove ANSI SGR escape sequences for rendering."""

    return ANSI_ESCAPE_RE.sub("", text)


def render_labels_video(
    *,
    snapshots_path: Path,
    labels: dict[str, LabelRow],
    output_path: Path,
    fps: int = 20,
    cleanup_frames: bool = True,
) -> Path:
    """Render an MP4 review video showing each snapshot and its binary labels."""

    snapshots = load_snapshots(snapshots_path)
    if not snapshots:
        raise ValueError(f"no snapshots found in {snapshots_path}")

    font = _resolve_font()
    terminal_width = 0
    for snapshot in snapshots:
        for content_line in strip_ansi(snapshot.output_text).splitlines():
            line_width = int(font.getlength(content_line))
            if line_width > terminal_width:
                terminal_width = line_width
    terminal_width += 2 * MARGIN
    terminal_height = MAX_VISIBLE_ROWS * LINE_HEIGHT + 2 * MARGIN

    total_width = terminal_width + INFO_PANEL_WIDTH
    total_height = max(terminal_height, INFO_PANEL_MIN_HEIGHT)
    total_width = (total_width + 1) // 2 * 2
    total_height = (total_height + 1) // 2 * 2

    output_path.parent.mkdir(parents=True, exist_ok=True)
    frames_dir = output_path.parent / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    for index, snapshot in enumerate(snapshots):
        sample_id = snapshot.sample_id
        label = labels.get(sample_id)
        frame = _render_frame(
            snapshot_text=snapshot.output_text,
            sample_id=sample_id,
            elapsed=snapshot.elapsed_seconds,
            label=label,
            width=total_width,
            height=total_height,
            font=font,
        )
        frame.save(frames_dir / f"frame_{index:06d}.png")

    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-framerate",
        str(fps),
        "-i",
        str(frames_dir / "frame_%06d.png"),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-crf",
        "23",
        str(output_path),
    ]
    subprocess.run(ffmpeg_cmd, check=True, capture_output=True, text=True)

    if cleanup_frames:
        shutil.rmtree(frames_dir)

    return output_path


def _render_frame(
    snapshot_text: str,
    sample_id: str,
    elapsed: float,
    label: LabelRow | None,
    width: int,
    height: int,
    font: ImageFont.FreeTypeFont,
) -> Image.Image:
    image = Image.new("RGB", (width, height), "#1e1e1e")
    draw = ImageDraw.Draw(image)

    content_lines = strip_ansi(snapshot_text).splitlines()
    content_height = len(content_lines) * LINE_HEIGHT
    start_y = max(MARGIN, height - content_height - MARGIN)
    y = start_y
    for content_line in content_lines:
        draw.text((MARGIN, y), content_line, fill="#d4d4d4", font=font)
        y += LINE_HEIGHT

    terminal_width = width - INFO_PANEL_WIDTH
    draw.line([(terminal_width, 0), (terminal_width, height)], fill="#444444", width=2)
    draw.rectangle([(terminal_width, 0), (width, height)], fill="#252526")

    panel_x = terminal_width + MARGIN
    panel_y = MARGIN
    line = 0

    def draw_line(text: str, fill: str = "#cccccc") -> None:
        nonlocal line
        draw.text((panel_x, panel_y + line * LINE_HEIGHT), text, fill=fill, font=font)
        line += 1

    draw_line(f"Sample: {sample_id}")
    draw_line(f"Time: {elapsed:.3f}s")
    line += 1

    draw_line("can_accept_input:", fill="#999999")
    if label is not None:
        draw_line(f"  {label.can_accept_input}", fill=_value_color(label.can_accept_input))
    else:
        draw_line("  missing", fill="#888888")
    line += 1

    draw_line("has_pending_message:", fill="#999999")
    if label is not None:
        draw_line(
            f"  {label.has_pending_message}",
            fill=_value_color(label.has_pending_message),
        )
    else:
        draw_line("  missing", fill="#888888")
    line += 1

    draw_line("pending_count:", fill="#999999")
    if label is not None:
        draw_line(
            f"  {label.pending_count}",
            fill=_count_color(label.pending_count),
        )
    else:
        draw_line("  missing", fill="#888888")
    line += 1

    draw_line("Evidence:", fill="#999999")
    evidence = label.evidence_note if label is not None else "no label"
    max_width = INFO_PANEL_WIDTH - 2 * MARGIN
    words = evidence.split()
    current = "  "
    for word in words:
        test = f"{current} {word}" if current.strip() else f"  {word}"
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = test
        else:
            draw_line(current, fill="#aaaaaa")
            current = f"  {word}"
    if current.strip():
        draw_line(current, fill="#aaaaaa")

    return image


def _value_color(value: str) -> str:
    return {
        "yes": "#00aa00",
        "no": "#cc0000",
        "unknown": "#ffaa00",
    }.get(value, "#888888")


def _count_color(value: PendingCountLabel) -> str:
    if value in (1, 2, 3):
        return "#00aa00"
    if value == 0:
        return "#cc0000"
    return "#ffaa00"
