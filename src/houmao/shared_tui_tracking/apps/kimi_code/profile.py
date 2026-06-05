"""Kimi Code tracked-TUI detector profile based on recorded signal contracts."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Sequence
from dataclasses import dataclass

from houmao.shared_tui_tracking.detectors import BaseTrackedTurnSignalDetector
from houmao.shared_tui_tracking.models import (
    DetectedTurnSignals,
    ParsedSurfaceContext,
    RecentProfileFrame,
    TemporalHintSignals,
    Tristate,
)
from houmao.shared_tui_tracking.surface import SurfaceView


BRAILLE_SPINNER_FRAMES = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")
MOON_SPINNER_FRAMES = ("🌑", "🌒", "🌓", "🌔", "🌕", "🌖", "🌗", "🌘")
APPROVAL_HEADERS = (
    "Run this command?",
    "Write this file?",
    "Apply these edits?",
    "Stop this task?",
    "Ready to build with this plan?",
)
ACTIVITY_LABEL_RE = re.compile(r"\b(?:working|thinking)\.\.\.")
APPROVAL_CHOICE_RE = re.compile(r"\b\d+\.\s+(?:Approve|Reject|Revise)\b")
PROMPT_TOKEN_RE = re.compile(r"^\s*[│┃]\s*>\s?(?P<body>.*)$")
TEMPORAL_WINDOW_SECONDS = 3.0
MAX_CONTIGUOUS_GAP_SECONDS = 1.5
MIN_TRANSCRIPT_GROWTH_CHARS = 48
MIN_TRANSCRIPT_GROWTH_LINES = 2


@dataclass(frozen=True)
class KimiPromptSnapshot:
    """Prompt/editor facts extracted from one Kimi surface."""

    prompt_visible: bool
    prompt_index: int | None
    prompt_text: str | None
    prompt_style: str
    editor_box_visible: bool
    raw_prompt_line: str | None


@dataclass(frozen=True)
class KimiSurfaceAnalysis:
    """Reusable Kimi surface facts for tracker and replay parser output."""

    prompt: KimiPromptSnapshot
    approval_visible: bool
    approval_header: str | None
    approval_choice_count: int
    activity_visible: bool
    activity_reasons: tuple[str, ...]
    latest_activity_line: str | None
    interrupted: bool
    footer_model_thinking: bool
    latest_turn_signature: str
    latest_turn_length: int
    latest_turn_line_count: int
    notes: tuple[str, ...]


@dataclass(frozen=True)
class _KimiFrame:
    """Profile-private Kimi frame used for temporal transcript-growth hints."""

    prompt_visible: bool
    prompt_text: str | None
    approval_visible: bool
    activity_visible: bool
    interrupted: bool
    latest_turn_signature: str
    latest_turn_length: int
    latest_turn_line_count: int


class _BaseKimiCodeSignalDetector(BaseTrackedTurnSignalDetector):
    """Tracked-TUI detector for one Kimi Code version family."""

    def __init__(self, *, detector_version: str, profile_notes: tuple[str, ...] = ()) -> None:
        """Initialize one Kimi detector profile."""

        self.m_detector_version: str = detector_version
        self.m_profile_notes: tuple[str, ...] = profile_notes

    @property
    def detector_name(self) -> str:
        """Return the detector family name."""

        return "kimi_code"

    @property
    def detector_version(self) -> str:
        """Return the detector selector version."""

        return self.m_detector_version

    @property
    def temporal_window_seconds(self) -> float:
        """Return the recent-window duration used by this profile."""

        return TEMPORAL_WINDOW_SECONDS

    def detect(
        self,
        *,
        output_text: str | None,
        parsed_surface: ParsedSurfaceContext | None = None,
    ) -> DetectedTurnSignals:
        """Return normalized tracked signals for one Kimi Code TUI surface."""

        del parsed_surface
        analysis = analyze_kimi_surface(output_text)
        prompt = analysis.prompt
        approval_visible = analysis.approval_visible
        interrupted = analysis.interrupted

        active_reasons: list[str] = list(analysis.activity_reasons)
        if approval_visible:
            active_reasons.append("approval_panel")
        active_reasons = list(dict.fromkeys(active_reasons))
        active_evidence = bool(active_reasons) and not interrupted
        accepting_input = _accepting_input_state(
            prompt_visible=prompt.prompt_visible,
            approval_visible=approval_visible,
            active_evidence=active_evidence,
        )
        editing_input = _editing_input_state(
            prompt_visible=prompt.prompt_visible,
            prompt_text=prompt.prompt_text,
            prompt_style=prompt.prompt_style,
            accepting_input=accepting_input,
        )
        ready_posture = _ready_posture_state(
            prompt_visible=prompt.prompt_visible,
            approval_visible=approval_visible,
            active_evidence=active_evidence,
        )
        success_candidate = bool(
            prompt.prompt_visible
            and ready_posture == "yes"
            and prompt.prompt_style in {"empty", "placeholder"}
            and not interrupted
        )
        notes: list[str] = [*self.m_profile_notes, *analysis.notes]
        if active_evidence:
            notes.append("active_turn_detected")
        if approval_visible:
            notes.append("approval_panel_visible")
        if interrupted:
            notes.append("interrupted_signal_detected")
        if analysis.footer_model_thinking and not active_evidence:
            notes.append("footer_thinking_metadata_ignored")

        stripped_text = "\n".join(SurfaceView.from_text(output_text or "").stripped_lines)
        surface_signature = hashlib.sha256(stripped_text.encode("utf-8")).hexdigest()
        success_blocked = bool(active_evidence or approval_visible or interrupted)
        return DetectedTurnSignals(
            detector_name=self.detector_name,
            detector_version=self.detector_version,
            accepting_input=accepting_input,
            editing_input=editing_input,
            ready_posture=ready_posture,
            prompt_visible=prompt.prompt_visible,
            prompt_text=prompt.prompt_text,
            footer_interruptable=active_evidence,
            active_evidence=active_evidence,
            active_reasons=tuple(active_reasons),
            interrupted=interrupted,
            known_failure=False,
            current_error_present=False,
            success_candidate=success_candidate,
            completion_marker=None,
            latest_status_line=analysis.latest_activity_line,
            ambiguous_interactive_surface=approval_visible,
            success_blocked=success_blocked,
            surface_signature=surface_signature,
            notes=tuple(dict.fromkeys(notes)),
        )

    def build_temporal_frame(
        self,
        *,
        output_text: str | None,
        signals: DetectedTurnSignals,
        observed_at_seconds: float,
    ) -> object | None:
        """Return one Kimi frame for recent-window inference."""

        del signals
        del observed_at_seconds
        analysis = analyze_kimi_surface(output_text)
        return _KimiFrame(
            prompt_visible=analysis.prompt.prompt_visible,
            prompt_text=analysis.prompt.prompt_text,
            approval_visible=analysis.approval_visible,
            activity_visible=analysis.activity_visible,
            interrupted=analysis.interrupted,
            latest_turn_signature=analysis.latest_turn_signature,
            latest_turn_length=analysis.latest_turn_length,
            latest_turn_line_count=analysis.latest_turn_line_count,
        )

    def derive_temporal_hints(
        self,
        *,
        recent_frames: Sequence[RecentProfileFrame],
    ) -> TemporalHintSignals:
        """Return conservative Kimi lifecycle hints from recent frames."""

        kimi_frames = [item for item in recent_frames if isinstance(item.payload, _KimiFrame)]
        if len(kimi_frames) < 2:
            return TemporalHintSignals()

        contiguous = [kimi_frames[-1]]
        for frame in reversed(kimi_frames[:-1]):
            next_frame = contiguous[0]
            if (
                next_frame.observed_at_seconds - frame.observed_at_seconds
                > MAX_CONTIGUOUS_GAP_SECONDS
            ):
                break
            contiguous.insert(0, frame)
        if len(contiguous) < 2:
            return TemporalHintSignals()

        oldest = contiguous[0].payload
        newest = contiguous[-1].payload
        if not isinstance(oldest, _KimiFrame) or not isinstance(newest, _KimiFrame):
            return TemporalHintSignals()
        if (
            newest.approval_visible
            or newest.activity_visible
            or newest.interrupted
            or not newest.prompt_visible
            or (newest.prompt_text or "").strip()
        ):
            return TemporalHintSignals()
        if newest.latest_turn_signature == oldest.latest_turn_signature:
            return TemporalHintSignals()

        growth_chars = newest.latest_turn_length - oldest.latest_turn_length
        growth_lines = newest.latest_turn_line_count - oldest.latest_turn_line_count
        if (
            growth_chars < MIN_TRANSCRIPT_GROWTH_CHARS
            and growth_lines < MIN_TRANSCRIPT_GROWTH_LINES
        ):
            return TemporalHintSignals()
        return TemporalHintSignals(
            active_evidence=True,
            active_reasons=("transcript_growth",),
            ready_posture="no",
            accepting_input="no",
            notes=("temporal_transcript_growth",),
        )


class KimiCodeSignalDetectorV0_11_X(_BaseKimiCodeSignalDetector):
    """Tracked-TUI detector for observed Kimi Code `0.11.x` surfaces."""

    def __init__(self) -> None:
        """Initialize the `0.11.x` Kimi detector family."""

        super().__init__(detector_version="0.11.x")


class FallbackKimiCodeSignalDetector(_BaseKimiCodeSignalDetector):
    """Conservative Kimi detector for unmatched Kimi versions."""

    def __init__(self) -> None:
        """Initialize the fallback Kimi detector family."""

        super().__init__(detector_version="fallback", profile_notes=("fallback_detector",))


def analyze_kimi_surface(output_text: str | None) -> KimiSurfaceAnalysis:
    """Return reusable source-backed Kimi surface facts from raw pane text."""

    surface = SurfaceView.from_text(output_text or "")
    prompt = _build_prompt_snapshot(surface)
    approval_header, approval_choice_count = _approval_panel_facts(surface)
    approval_visible = approval_header is not None and approval_choice_count > 0
    latest_turn_lines = _latest_turn_lines(surface=surface, prompt_index=prompt.prompt_index)
    activity_reasons, latest_activity_line = _activity_facts(
        lines=latest_turn_lines,
        prompt_visible=prompt.prompt_visible,
    )
    interrupted = _interrupted_visible(latest_turn_lines)
    footer_model_thinking = _footer_model_thinking(surface)
    notes: list[str] = []
    if prompt.prompt_visible:
        notes.append(f"prompt_{prompt.prompt_style}")
    if prompt.editor_box_visible:
        notes.append("editor_box_visible")
    if approval_visible:
        notes.append("approval_bounded_region")
    if footer_model_thinking:
        notes.append("footer_model_thinking")
    if latest_activity_line is not None:
        notes.append("activity_line_visible")
    joined_latest_turn = "\n".join(latest_turn_lines)
    return KimiSurfaceAnalysis(
        prompt=prompt,
        approval_visible=approval_visible,
        approval_header=approval_header,
        approval_choice_count=approval_choice_count,
        activity_visible=bool(activity_reasons),
        activity_reasons=tuple(activity_reasons),
        latest_activity_line=latest_activity_line,
        interrupted=interrupted,
        footer_model_thinking=footer_model_thinking,
        latest_turn_signature=hashlib.sha256(joined_latest_turn.encode("utf-8")).hexdigest(),
        latest_turn_length=len(joined_latest_turn),
        latest_turn_line_count=len(latest_turn_lines),
        notes=tuple(notes),
    )


def _build_prompt_snapshot(surface: SurfaceView) -> KimiPromptSnapshot:
    """Extract Kimi editor prompt facts from the latest visible editor box."""

    prompt_index: int | None = None
    prompt_text: str | None = None
    raw_prompt_line: str | None = None
    for index, raw_line, stripped_line in surface.iter_lines_with_indices():
        extracted = _extract_prompt_text(stripped_line)
        if extracted is None:
            continue
        prompt_index = index
        prompt_text = extracted
        raw_prompt_line = raw_line

    if prompt_index is None:
        return KimiPromptSnapshot(
            prompt_visible=False,
            prompt_index=None,
            prompt_text=None,
            prompt_style="missing",
            editor_box_visible=False,
            raw_prompt_line=None,
        )
    prompt_style = _classify_prompt_style(
        prompt_text=prompt_text or "", raw_line=raw_prompt_line or ""
    )
    return KimiPromptSnapshot(
        prompt_visible=True,
        prompt_index=prompt_index,
        prompt_text=prompt_text,
        prompt_style=prompt_style,
        editor_box_visible=_editor_box_around(surface=surface, prompt_index=prompt_index),
        raw_prompt_line=raw_prompt_line,
    )


def _extract_prompt_text(stripped_line: str) -> str | None:
    """Return editor text from one stripped Kimi prompt row."""

    stripped = stripped_line.rstrip()
    if stripped.endswith("│") or stripped.endswith("┃"):
        stripped = stripped[:-1].rstrip()
    match = PROMPT_TOKEN_RE.match(stripped)
    if match is None:
        return None
    return match.group("body").rstrip()


def _classify_prompt_style(*, prompt_text: str, raw_line: str) -> str:
    """Classify prompt payload from text plus ANSI styling."""

    if not prompt_text.strip():
        return "empty"
    if "\x1b[2m" in raw_line:
        return "placeholder"
    if prompt_text.lstrip().startswith("/"):
        return "slash"
    return "typed"


def _editor_box_around(*, surface: SurfaceView, prompt_index: int) -> bool:
    """Return whether the prompt row sits inside the source-backed editor box."""

    above = surface.stripped_lines[max(0, prompt_index - 3) : prompt_index]
    below = surface.stripped_lines[prompt_index + 1 : prompt_index + 4]
    has_top = any(line.lstrip().startswith(("╭", "├")) for line in above)
    has_bottom = any(line.lstrip().startswith(("╰", "└")) for line in below)
    return has_top and has_bottom


def _approval_panel_facts(surface: SurfaceView) -> tuple[str | None, int]:
    """Return approval header and choice count when a bounded approval region exists."""

    header_index: int | None = None
    header_text: str | None = None
    for index, line in enumerate(surface.stripped_lines):
        for header in APPROVAL_HEADERS:
            if header in line:
                header_index = index
                header_text = header
                break
        if header_text is not None:
            break
        if "Approve " in line and line.strip().endswith("?"):
            header_index = index
            header_text = line.strip()
            break
    if header_index is None or header_text is None:
        return None, 0

    region = surface.stripped_lines[
        header_index : min(len(surface.stripped_lines), header_index + 24)
    ]
    has_panel_rule = any(_is_horizontal_rule(line) for line in region)
    choice_count = sum(1 for line in region if APPROVAL_CHOICE_RE.search(line) is not None)
    if not has_panel_rule:
        return None, 0
    return header_text, choice_count


def _activity_facts(*, lines: Sequence[str], prompt_visible: bool) -> tuple[list[str], str | None]:
    """Return live-edge activity reasons from the current-turn region."""

    window = [line.strip() for line in lines[-18:] if line.strip()]
    reasons: list[str] = []
    latest_line: str | None = None
    for line in window:
        if _is_footer_line(line) or _is_editor_border_line(line):
            continue
        frame_kind = _spinner_frame_kind(line)
        if frame_kind is None:
            continue
        if frame_kind == "braille" and ACTIVITY_LABEL_RE.search(line) is None:
            continue
        if prompt_visible and "context:" in line:
            continue
        reasons.append(f"{frame_kind}_spinner")
        latest_line = line
    return list(dict.fromkeys(reasons)), latest_line


def _latest_turn_lines(*, surface: SurfaceView, prompt_index: int | None) -> tuple[str, ...]:
    """Return a bounded current-turn/live-edge region."""

    if prompt_index is None:
        stripped = tuple(line for line in surface.stripped_lines if line.strip())
        return stripped[-24:]
    start_index = max(0, prompt_index - 28)
    return tuple(surface.stripped_lines[start_index:prompt_index])


def _interrupted_visible(lines: Sequence[str]) -> bool:
    """Return whether a current-turn interruption notice is visible."""

    recent = " ".join(line.strip() for line in lines[-12:] if line.strip()).lower()
    return "interrupted by user" in recent or "step interrupted" in recent


def _footer_model_thinking(surface: SurfaceView) -> bool:
    """Return whether footer model metadata contains the thinking capability label."""

    for line in surface.footer_lines(count=4):
        lower = line.lower()
        if "context:" in lower:
            continue
        if " thinking" in lower and not any(frame in line for frame in BRAILLE_SPINNER_FRAMES):
            return True
    return False


def _spinner_frame_kind(line: str) -> str | None:
    """Return the spinner family visible at the beginning of one stripped line."""

    stripped = line.lstrip()
    if stripped.startswith(BRAILLE_SPINNER_FRAMES):
        return "braille"
    if stripped.startswith(MOON_SPINNER_FRAMES):
        return "moon"
    return None


def _is_horizontal_rule(line: str) -> bool:
    """Return whether one stripped line is a Kimi panel horizontal rule."""

    stripped = line.strip()
    return len(stripped) >= 8 and set(stripped) <= {"─"}


def _is_editor_border_line(line: str) -> bool:
    """Return whether one stripped line is an editor box border."""

    stripped = line.strip()
    return stripped.startswith(("╭", "╰", "├", "└")) or stripped.endswith(("╮", "╯", "┤", "┘"))


def _is_footer_line(line: str) -> bool:
    """Return whether one stripped line looks like footer metadata."""

    lower = line.lower()
    return "context:" in lower or "shift+tab:" in lower or "/model:" in lower


def _accepting_input_state(
    *,
    prompt_visible: bool,
    approval_visible: bool,
    active_evidence: bool,
) -> Tristate:
    """Return public accepting-input state from Kimi prompt and modal facts."""

    if approval_visible or active_evidence:
        return "no"
    if prompt_visible:
        return "yes"
    return "unknown"


def _editing_input_state(
    *,
    prompt_visible: bool,
    prompt_text: str | None,
    prompt_style: str,
    accepting_input: Tristate,
) -> Tristate:
    """Return public editing-input state from Kimi prompt facts."""

    if accepting_input == "no":
        return "no"
    if not prompt_visible:
        return "unknown"
    if prompt_style in {"empty", "placeholder"}:
        return "no"
    if prompt_text is not None and prompt_text.strip():
        return "yes"
    return "unknown"


def _ready_posture_state(
    *,
    prompt_visible: bool,
    approval_visible: bool,
    active_evidence: bool,
) -> Tristate:
    """Return public ready-posture state from Kimi prompt and current-turn facts."""

    if approval_visible or active_evidence:
        return "no"
    if prompt_visible:
        return "yes"
    return "unknown"


KimiCodeSignalDetector = KimiCodeSignalDetectorV0_11_X
