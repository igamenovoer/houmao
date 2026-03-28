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
    fps: float,
    width: int = FRAME_WIDTH,
    height: int = FRAME_HEIGHT,
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
            width=width,
            height=height,
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
    *,
    frames_dir: Path,
    output_path: Path,
    fps: float,
    codec: str = "libx264",
    pixel_format: str = "yuv420p",
) -> subprocess.CompletedProcess[str]:
    """Encode staged review frames into one H.264 MP4."""

    command = build_ffmpeg_command(
        frames_dir=frames_dir,
        output_path=output_path,
        fps=fps,
        codec=codec,
        pixel_format=pixel_format,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return subprocess.run(command, check=True, capture_output=True, text=True)


def build_ffmpeg_command(
    *,
    frames_dir: Path,
    output_path: Path,
    fps: float,
    codec: str = "libx264",
    pixel_format: str = "yuv420p",
) -> list[str]:
    """Return the `ffmpeg` command used for review-video encoding."""

    fps_text = f"{fps:.6f}".rstrip("0").rstrip(".")
    return [
        "ffmpeg",
        "-y",
        "-framerate",
        fps_text,
        "-i",
        str(frames_dir / "frame-%06d.png"),
        "-c:v",
        codec,
        "-pix_fmt",
        pixel_format,
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
    width: int,
    height: int,
) -> Image.Image:
    """Render one 1080p frame for a single snapshot/state pair."""

    image = Image.new("RGB", (width, height), _BACKGROUND)
    draw = ImageDraw.Draw(image)
    draw.rectangle([(0, 0), (width, 118)], fill=_BANNER)
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
        transition_left = max(40, width - 540)
        transition_right = width - 40
        draw.rounded_rectangle(
            [(transition_left, 16), (transition_right, 92)],
            radius=14,
            fill=_TRANSITION,
        )
        draw.text(
            (transition_left + 30, 40),
            "GROUND TRUTH CHANGE",
            font=small_font,
            fill="#172400",
        )

    body_text = _ANSI_RE.sub("", snapshot.output_text).replace("\t", "    ")
    top = 150
    left = 52
    line_height = 30
    max_lines = max(1, (height - top - 50) // line_height)
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
