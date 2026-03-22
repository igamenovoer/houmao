"""Review-video rendering for recorded tracked-TUI fixtures."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from houmao.shared_tui_tracking.models import TrackedTimelineState
from houmao.terminal_record.models import TerminalRecordPaneSnapshot


FRAME_WIDTH = 1920
FRAME_HEIGHT = 1080
_BACKGROUND = "#07111b"
_TEXT = "#dfe8ef"
_DIM = "#8ea3b5"
_BANNER = "#17344e"
_TRANSITION = "#e1ff6a"
_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
_FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/dejavu/DejaVuSansMono.ttf",
)


def render_review_frames(
    *,
    snapshots: list[TerminalRecordPaneSnapshot],
    groundtruth_timeline: list[TrackedTimelineState],
    output_dir: Path,
    fps: int,
) -> list[Path]:
    """Render expanded 1080p PNG review frames for one labeled recording."""

    if len(snapshots) != len(groundtruth_timeline):
        raise ValueError("snapshots and groundtruth timeline must have equal sample counts")
    output_dir.mkdir(parents=True, exist_ok=True)
    font = _load_font(size=24)
    small_font = _load_font(size=20)
    frame_paths: list[Path] = []
    frame_index = 1
    previous_state_signature: tuple[str, ...] | None = None
    for index, (snapshot, state) in enumerate(zip(snapshots, groundtruth_timeline, strict=True)):
        current_state_signature = (
            state.diagnostics_availability,
            state.surface_accepting_input,
            state.surface_editing_input,
            state.surface_ready_posture,
            state.turn_phase,
            state.last_turn_result,
            state.last_turn_source,
        )
        is_transition = (
            previous_state_signature is not None
            and current_state_signature != previous_state_signature
        )
        previous_state_signature = current_state_signature
        if index + 1 < len(snapshots):
            duration_seconds = max(
                0.0, snapshots[index + 1].elapsed_seconds - snapshot.elapsed_seconds
            )
        else:
            duration_seconds = 1.0
        duplicates = max(1, round(duration_seconds * fps))
        rendered_image = _render_snapshot_frame(
            snapshot=snapshot,
            state=state,
            font=font,
            small_font=small_font,
            is_transition=is_transition,
        )
        sample_path = output_dir / f"sample-{index + 1:06d}.png"
        rendered_image.save(sample_path)
        for _unused in range(duplicates):
            frame_path = output_dir / f"frame-{frame_index:06d}.png"
            shutil.copyfile(sample_path, frame_path)
            frame_paths.append(frame_path)
            frame_index += 1
    return frame_paths


def encode_review_video(
    *, frames_dir: Path, output_path: Path, fps: int
) -> subprocess.CompletedProcess[str]:
    """Encode staged review frames into one H.264 MP4."""

    command = build_ffmpeg_command(frames_dir=frames_dir, output_path=output_path, fps=fps)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return subprocess.run(command, check=True, capture_output=True, text=True)


def build_ffmpeg_command(*, frames_dir: Path, output_path: Path, fps: int) -> list[str]:
    """Return the `ffmpeg` command used for review-video encoding."""

    return [
        "ffmpeg",
        "-y",
        "-framerate",
        str(fps),
        "-i",
        str(frames_dir / "frame-%06d.png"),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-crf",
        "18",
        "-preset",
        "medium",
        "-movflags",
        "+faststart",
        str(output_path),
    ]


def _render_snapshot_frame(
    *,
    snapshot: TerminalRecordPaneSnapshot,
    state: TrackedTimelineState,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    small_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    is_transition: bool,
) -> Image.Image:
    """Render one 1080p frame for a single snapshot/state pair."""

    image = Image.new("RGB", (FRAME_WIDTH, FRAME_HEIGHT), _BACKGROUND)
    draw = ImageDraw.Draw(image)
    draw.rectangle([(0, 0), (FRAME_WIDTH, 118)], fill=_BANNER)
    draw.text((40, 24), f"sample {snapshot.sample_id}", font=font, fill=_TEXT)
    draw.text(
        (420, 24),
        f"t={snapshot.elapsed_seconds:.2f}s  availability={state.diagnostics_availability}",
        font=font,
        fill=_TEXT,
    )
    draw.text(
        (40, 64),
        (
            "turn="
            f"{state.turn_phase}  last={state.last_turn_result}/{state.last_turn_source}  "
            f"input={state.surface_accepting_input}  editing={state.surface_editing_input}  "
            f"ready={state.surface_ready_posture}"
        ),
        font=small_font,
        fill=_DIM,
    )
    if is_transition:
        draw.rounded_rectangle([(1380, 16), (1880, 92)], radius=14, fill=_TRANSITION)
        draw.text((1410, 40), "GROUND TRUTH CHANGE", font=small_font, fill="#172400")

    body_text = _ANSI_RE.sub("", snapshot.output_text).replace("\t", "    ")
    top = 150
    left = 52
    line_height = 30
    max_lines = max(1, (FRAME_HEIGHT - top - 50) // line_height)
    for index, line in enumerate(body_text.splitlines()[:max_lines]):
        draw.text((left, top + (index * line_height)), line, font=font, fill=_TEXT)
    return image


def _load_font(*, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Return the preferred monospace font when available."""

    for candidate in _FONT_CANDIDATES:
        path = Path(candidate)
        if path.is_file():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()
