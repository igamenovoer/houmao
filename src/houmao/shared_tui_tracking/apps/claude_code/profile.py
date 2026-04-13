"""Claude Code tracked-TUI detector profiles."""

from __future__ import annotations

import hashlib
import re

from houmao.shared_tui_tracking.apps.claude_code.signals.prompt_behavior import (
    ClaudePromptBehaviorVariant,
    ClaudePromptBehaviorVariantV2_1_X,
    FallbackClaudePromptBehaviorVariant,
    build_prompt_area_snapshot,
    prompt_behavior_notes,
)

from houmao.shared_tui_tracking.detectors import BaseVersionedClaudeDetector
from houmao.shared_tui_tracking.models import DetectedTurnSignals, ParsedSurfaceContext, Tristate
from houmao.shared_tui_tracking.surface import SurfaceView


READY_FOOTER_ADVISORY_PATTERNS = (
    "Claude Code has switched from npm to native installer.",
    "Run `claude install`",
)
COMPLETION_MARKER_RE = re.compile(r"Worked for \d+[smh]")
COLOR_RE = re.compile(r"\x1b\[38;5;(\d+)m")
INTERRUPTED_RE = re.compile(r"^⎿\s+Interrupted · What should Claude do instead\?$")
SPINNER_LINE_RE = re.compile(r"^[✢✻✽✶·*]\s+.+…(?:\s+\(.+\))?$")
FOOTER_INTERRUPT_RE = re.compile(r"esc to(?: interrupt|…|\\.\\.\\.)?")


class _BaseClaudeCodeSignalDetector(BaseVersionedClaudeDetector):
    """Tracked-TUI detector for one Claude Code version family."""

    def __init__(
        self,
        *,
        detector_version: str,
        prompt_behavior_variant: ClaudePromptBehaviorVariant,
        profile_notes: tuple[str, ...] = (),
    ) -> None:
        """Initialize one Claude detector profile."""

        self.m_detector_version: str = detector_version
        self.m_prompt_behavior_variant: ClaudePromptBehaviorVariant = prompt_behavior_variant
        self.m_profile_notes: tuple[str, ...] = profile_notes

    @property
    def detector_name(self) -> str:
        """Return the detector family name."""

        return "claude_code"

    @property
    def detector_version(self) -> str:
        """Return the detector selector version."""

        return self.m_detector_version

    def detect(
        self,
        *,
        output_text: str | None,
        parsed_surface: ParsedSurfaceContext | None = None,
    ) -> DetectedTurnSignals:
        """Return normalized tracked signals for one Claude surface."""

        del parsed_surface
        surface = SurfaceView.from_text(output_text or "")
        prompt_snapshot = build_prompt_area_snapshot(surface)
        prompt_classification = self.m_prompt_behavior_variant.classify(prompt_snapshot)
        prompt_text = prompt_classification.prompt_text
        last_prompt_index = prompt_snapshot.prompt_index
        prompt_visible = prompt_snapshot.prompt_visible
        footer_interruptable = any(
            FOOTER_INTERRUPT_RE.search(line) is not None for line in surface.footer_lines()
        )
        footer_has_ready_advisory = any(
            pattern in line
            for line in surface.footer_lines()
            for pattern in READY_FOOTER_ADVISORY_PATTERNS
        )
        latest_turn_anchor_index = _latest_turn_prompt_anchor_index(surface)
        latest_status_index, latest_status_line = _latest_turn_status_line(
            surface=surface,
            prompt_anchor_index=latest_turn_anchor_index,
        )
        activity_region_lines = _latest_turn_activity_line_items(
            surface=surface,
            prompt_anchor_index=latest_turn_anchor_index,
        )
        slash_menu_visible = bool(prompt_text and prompt_text.startswith("/")) and any(
            stripped_line.strip().startswith("/")
            for _, _, stripped_line in surface.iter_lines_with_indices()
            if stripped_line.strip() and not stripped_line.strip().startswith("❯")
        )

        active_reasons: list[str] = []
        notes: list[str] = [
            *self.m_profile_notes,
            *prompt_behavior_notes(
                variant=self.m_prompt_behavior_variant,
                classification=prompt_classification,
            ),
        ]
        if latest_turn_anchor_index is None:
            notes.append("latest_turn_anchor_missing")
        current_error_present = False
        latest_response_index: int | None = None

        interrupted = False
        if latest_status_index is not None and latest_status_line is not None:
            interrupted = bool(
                INTERRUPTED_RE.match(latest_status_line)
                and surface.prompt_visible_after(latest_status_index)
            )

        known_failure = False
        if latest_status_index is not None:
            raw_status = surface.raw_lines[latest_status_index]
            status_colors = {int(item) for item in COLOR_RE.findall(raw_status) if item != "246"}
            if status_colors and surface.prompt_visible_after(latest_status_index):
                lower_colors: set[int] = set()
                for raw_footer in surface.footer_raw_lines():
                    lower_colors.update(int(item) for item in COLOR_RE.findall(raw_footer))
                shared_colors = {
                    item for item in status_colors if item in lower_colors and item != 246
                }
                if shared_colors:
                    known_failure = True
                    current_error_present = True

        for _, _, stripped_line in activity_region_lines:
            if SPINNER_LINE_RE.match(stripped_line.strip()):
                active_reasons.append("thinking_line")
                break

        for index, _, stripped_line in surface.iter_lines_with_indices():
            if last_prompt_index is not None and index >= last_prompt_index:
                continue
            if stripped_line.strip().startswith("● "):
                latest_response_index = index

        if footer_interruptable:
            for _, _, stripped_line in activity_region_lines:
                if stripped_line.strip().startswith("● ") and "Worked for" not in stripped_line:
                    active_reasons.append("active_block")
                    break

        if footer_interruptable and not active_reasons:
            active_reasons.append("interruptable_footer")

        active_evidence = bool(active_reasons) and not interrupted and not known_failure
        completion_marker = None
        for _, _, stripped_line in surface.iter_lines_with_indices():
            match = COMPLETION_MARKER_RE.search(stripped_line)
            if match is not None:
                completion_marker = match.group(0)
                break
        response_candidate_visible = (
            latest_response_index is not None
            and surface.prompt_visible_after(latest_response_index)
        )

        ambiguous_interactive_surface = slash_menu_visible and not active_evidence
        success_blocked = bool(
            footer_interruptable or current_error_present or ambiguous_interactive_surface
        )
        success_candidate = (
            (completion_marker is not None or response_candidate_visible)
            and prompt_visible
            and not success_blocked
            and not interrupted
            and not known_failure
        )
        if success_candidate:
            if completion_marker is not None:
                notes.append("completion_marker_visible")
            if response_candidate_visible and completion_marker is None:
                notes.append("response_block_success_candidate")
        if slash_menu_visible:
            notes.append("slash_menu_visible")
        if footer_has_ready_advisory:
            notes.append("ready_footer_advisory")

        ready_posture: Tristate = (
            "yes"
            if prompt_visible and not footer_interruptable and not slash_menu_visible
            else "unknown"
        )
        accepting_input: Tristate = "yes" if prompt_visible else "unknown"
        editing_input = _editing_input_state(
            prompt_visible=prompt_visible,
            prompt_kind=prompt_classification.kind,
        )
        if ambiguous_interactive_surface:
            ready_posture = "unknown"
        if active_evidence:
            notes.append("active_turn_detected")
        if interrupted:
            notes.append("interrupted_signal_detected")
        if known_failure:
            notes.append("known_failure_signal_detected")
        if ambiguous_interactive_surface:
            notes.append("ambiguous_interactive_surface")

        stripped_text = "\n".join(surface.stripped_lines)
        surface_signature = hashlib.sha256(stripped_text.encode("utf-8")).hexdigest()
        return DetectedTurnSignals(
            detector_name=self.detector_name,
            detector_version=self.detector_version,
            accepting_input=accepting_input,
            editing_input=editing_input,
            ready_posture=ready_posture,
            prompt_visible=prompt_visible,
            prompt_text=prompt_text,
            footer_interruptable=footer_interruptable,
            active_evidence=active_evidence,
            active_reasons=tuple(dict.fromkeys(active_reasons)),
            interrupted=interrupted,
            known_failure=known_failure,
            current_error_present=current_error_present,
            success_candidate=success_candidate,
            completion_marker=completion_marker,
            latest_status_line=latest_status_line,
            ambiguous_interactive_surface=ambiguous_interactive_surface,
            success_blocked=success_blocked,
            surface_signature=surface_signature,
            notes=tuple(notes),
        )


class ClaudeCodeSignalDetectorV2_1_X(_BaseClaudeCodeSignalDetector):
    """Closest-compatible detector for observed Claude Code `2.1.x`."""

    def __init__(self) -> None:
        """Initialize the `2.1.x` Claude detector profile."""

        super().__init__(
            detector_version="2.1.x",
            prompt_behavior_variant=ClaudePromptBehaviorVariantV2_1_X(),
        )

    def compatibility_score(self, *, observed_version: str | None) -> int:
        """Return a closeness score for a Claude version string."""

        if observed_version is None:
            return 50
        if "2.1." in observed_version:
            return 200
        if "2." in observed_version:
            return 120
        return 20


class FallbackClaudeDetector(_BaseClaudeCodeSignalDetector):
    """Conservative fallback detector for unmatched Claude versions."""

    def __init__(self) -> None:
        """Initialize the fallback Claude detector profile."""

        super().__init__(
            detector_version="fallback",
            prompt_behavior_variant=FallbackClaudePromptBehaviorVariant(),
            profile_notes=("fallback_detector",),
        )

    def compatibility_score(self, *, observed_version: str | None) -> int:
        """Return a low but always-available score."""

        return 1


def _editing_input_state(
    *,
    prompt_visible: bool,
    prompt_kind: str,
) -> Tristate:
    """Return the editing-input tristate for one Claude prompt surface."""

    if not prompt_visible:
        return "unknown"
    if prompt_kind == "draft":
        return "yes"
    if prompt_kind in {"placeholder", "empty"}:
        return "no"
    return "unknown"


def _latest_turn_prompt_anchor_index(surface: SurfaceView) -> int | None:
    """Return the latest visible Claude prompt index, including the empty input row."""

    for index in range(len(surface.stripped_lines) - 1, -1, -1):
        stripped_line = surface.stripped_lines[index].strip()
        if not stripped_line.startswith("❯"):
            continue
        return index
    return None


def _latest_turn_status_line(
    *,
    surface: SurfaceView,
    prompt_anchor_index: int | None,
) -> tuple[int | None, str | None]:
    """Return the latest Claude status line scoped to the latest visible prompt anchor."""

    if prompt_anchor_index is None:
        return None, None
    latest_status_index: int | None = None
    latest_status_line: str | None = None
    for index, _, stripped_line in _latest_turn_region_line_items(
        surface=surface,
        prompt_anchor_index=prompt_anchor_index,
    ):
        normalized_line = stripped_line.strip()
        if not normalized_line.startswith("⎿"):
            if latest_status_index is not None and normalized_line.startswith("● "):
                latest_status_index = None
                latest_status_line = None
            continue
        latest_status_index = index
        latest_status_line = normalized_line
    return latest_status_index, latest_status_line


def _latest_turn_region_line_items(
    *,
    surface: SurfaceView,
    prompt_anchor_index: int | None,
) -> tuple[tuple[int, str, str], ...]:
    """Return line items in the latest visible Claude turn region."""

    if prompt_anchor_index is None:
        return tuple(surface.iter_lines_with_indices())
    region_start_index = 0
    for index in range(prompt_anchor_index - 1, -1, -1):
        stripped_line = surface.stripped_lines[index].strip()
        if not stripped_line.startswith("❯"):
            continue
        if not stripped_line[1:].strip():
            continue
        region_start_index = index + 1
        break
    return tuple(
        item
        for item in surface.iter_lines_with_indices()
        if region_start_index <= item[0] < prompt_anchor_index
    )


def _latest_turn_activity_line_items(
    *,
    surface: SurfaceView,
    prompt_anchor_index: int | None,
) -> tuple[tuple[int, str, str], ...]:
    """Return current activity line items, excluding completed-turn history."""

    line_items = _latest_turn_region_line_items(
        surface=surface,
        prompt_anchor_index=prompt_anchor_index,
    )
    if prompt_anchor_index is None:
        return line_items
    latest_completion_offset: int | None = None
    for offset, (_, _, stripped_line) in enumerate(line_items):
        if COMPLETION_MARKER_RE.search(stripped_line) is None:
            continue
        latest_completion_offset = offset
    if latest_completion_offset is None:
        return line_items
    return line_items[latest_completion_offset + 1 :]
