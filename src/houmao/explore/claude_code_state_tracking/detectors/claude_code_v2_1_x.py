"""Claude Code detector implementation for nearby `2.1.x` surfaces."""

from __future__ import annotations

import hashlib
import re

from houmao.explore.claude_code_state_tracking.detectors.base import (
    BaseTurnSignalDetector,
    SurfaceView,
)
from houmao.explore.claude_code_state_tracking.models import DetectedSignals, Tristate


THINKING_PATTERNS = (
    "Cerebrating…",
    "Nebulizing…",
    "Unfurling…",
    "Slithering…",
    "Musing…",
    "Pouncing…",
    "Bloviating…",
    "thinking with high effort",
)
ACTIVE_TOOL_PATTERNS = (
    "Fetching…",
    "Running…",
    "Searching…",
    "Reading…",
)
COMPLETION_MARKER_RE = re.compile(r"Worked for \d+[smh]")
COLOR_RE = re.compile(r"\x1b\[38;5;(\d+)m")
INTERRUPTED_RE = re.compile(r"^⎿\s+Interrupted · What should Claude do instead\?$")
SPINNER_LINE_RE = re.compile(r"^[✢✻✽✶·*]\s+.+…(?:\s+\(.+\))?$")
FOOTER_INTERRUPT_RE = re.compile(r"esc to(?: interrupt|…|\\.\\.\\.)?")


class ClaudeCodeSignalDetectorV2_1_X(BaseTurnSignalDetector):
    """Closest-compatible detector for observed Claude Code `2.1.x`."""

    @property
    def detector_name(self) -> str:
        """Return the detector family name."""

        return "claude_code"

    @property
    def detector_version(self) -> str:
        """Return the detector selector version."""

        return "2.1.x"

    def compatibility_score(self, *, observed_version: str | None) -> int:
        """Return a closeness score for a Claude version string."""

        if observed_version is None:
            return 50
        if "2.1." in observed_version:
            return 200
        if "2." in observed_version:
            return 120
        return 20

    def detect(self, *, output_text: str) -> DetectedSignals:
        """Return normalized signals for one raw Claude surface."""

        surface = SurfaceView.from_text(output_text)
        prompt_text = surface.prompt_text()
        last_prompt_index = surface.last_prompt_index()
        prompt_visible = last_prompt_index is not None
        footer_interruptable = any(
            FOOTER_INTERRUPT_RE.search(line) is not None for line in surface.footer_lines()
        )
        latest_status_index = surface.last_status_index()
        latest_status_line = surface.latest_status_line()
        slash_menu_visible = bool(prompt_text and prompt_text.startswith("/")) and any(
            stripped_line.strip().startswith("/")
            for _, _, stripped_line in surface.iter_lines_with_indices()
            if stripped_line.strip() and not stripped_line.strip().startswith("❯")
        )

        active_reasons: list[str] = []
        notes: list[str] = []
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

        for _, _, stripped_line in surface.iter_lines_with_indices():
            if any(
                pattern in stripped_line for pattern in THINKING_PATTERNS
            ) or SPINNER_LINE_RE.match(stripped_line.strip()):
                active_reasons.append("thinking_line")
                break

        for index, _, stripped_line in surface.iter_lines_with_indices():
            if last_prompt_index is not None and index >= last_prompt_index:
                continue
            if stripped_line.strip().startswith("● "):
                latest_response_index = index

        if footer_interruptable:
            for _, _, stripped_line in surface.iter_lines_with_indices():
                if stripped_line.strip().startswith("● ") and "Worked for" not in stripped_line:
                    active_reasons.append("active_block")
                    break

        if footer_interruptable:
            for _, _, stripped_line in surface.iter_lines_with_indices():
                if any(pattern in stripped_line for pattern in ACTIVE_TOOL_PATTERNS):
                    active_reasons.append("tool_activity")
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

        success_candidate = (
            (completion_marker is not None or response_candidate_visible)
            and prompt_visible
            and not footer_interruptable
            and not current_error_present
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

        ready_posture: Tristate = (
            "yes"
            if prompt_visible and not footer_interruptable and not slash_menu_visible
            else "unknown"
        )
        accepting_input: Tristate = "yes" if prompt_visible else "unknown"
        editing_input: Tristate = "yes" if prompt_text else "no" if prompt_visible else "unknown"
        if active_evidence:
            notes.append("active_turn_detected")
        if interrupted:
            notes.append("interrupted_signal_detected")
        if known_failure:
            notes.append("known_failure_signal_detected")

        stripped_text = "\n".join(surface.stripped_lines)
        surface_signature = hashlib.sha256(stripped_text.encode("utf-8")).hexdigest()
        return DetectedSignals(
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
            surface_signature=surface_signature,
            notes=tuple(notes),
        )


class FallbackClaudeDetector(BaseTurnSignalDetector):
    """Conservative fallback detector for unmatched Claude versions."""

    @property
    def detector_name(self) -> str:
        """Return the detector family name."""

        return "claude_code"

    @property
    def detector_version(self) -> str:
        """Return the conservative fallback version selector."""

        return "fallback"

    def compatibility_score(self, *, observed_version: str | None) -> int:
        """Return a low but always-available score."""

        return 1

    def detect(self, *, output_text: str) -> DetectedSignals:
        """Return a conservative detector result."""

        surface = SurfaceView.from_text(output_text)
        prompt_visible = surface.last_prompt_index() is not None
        prompt_text = surface.prompt_text()
        stripped_text = "\n".join(surface.stripped_lines)
        surface_signature = hashlib.sha256(stripped_text.encode("utf-8")).hexdigest()
        return DetectedSignals(
            detector_name=self.detector_name,
            detector_version=self.detector_version,
            accepting_input="yes" if prompt_visible else "unknown",
            editing_input="yes" if prompt_text else "no" if prompt_visible else "unknown",
            ready_posture="yes" if prompt_visible else "unknown",
            prompt_visible=prompt_visible,
            prompt_text=prompt_text,
            footer_interruptable=False,
            active_evidence=False,
            active_reasons=(),
            interrupted=False,
            known_failure=False,
            current_error_present=False,
            success_candidate=False,
            completion_marker=None,
            latest_status_line=surface.latest_status_line(),
            surface_signature=surface_signature,
            notes=("fallback_detector",),
        )
