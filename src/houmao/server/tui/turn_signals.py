"""Tool-specific simplified turn-signal detection for tracked TUI state."""

from __future__ import annotations

import abc
import hashlib
import re
from dataclasses import dataclass

from houmao.explore.claude_code_state_tracking.detectors import select_claude_detector
from houmao.server.models import HoumaoParsedSurface, Tristate


_CODEx_PROMPT_RE = re.compile(r"^\s*›(.*)$")
_CODEX_WORKING_RE = re.compile(
    r"^\s*• (Working \(|Calling |Running |Waiting for background terminal|Reviewing approval request|Reviewing \d+ approval requests)"
)
_CODEX_INTERRUPTED_TEXT = (
    "Conversation interrupted - tell the model what to do differently. "
    "Something went wrong? Hit `/feedback` to report the issue."
)
_CODEX_STEER_INTERRUPTION_TEXT = "Model interrupted to submit steer instructions."
_CODEX_WORKED_RE = re.compile(r"^\s*─ Worked for .+ ─\s*$")
_CODEX_ERROR_CELL_RE = re.compile(r"^\s*■ .+")
_CODEX_APPROVAL_HINTS = (
    "Would you like to run the following command?",
    "Would you like to grant these permissions?",
    "Would you like to make the following edits?",
    "needs your approval.",
    "Question 1/",
    "Field 1/",
    "Press enter to confirm or esc to cancel",
    "enter to submit | esc to cancel",
)


@dataclass(frozen=True)
class DetectedTurnSignals:
    """Normalized simplified turn signals for one raw surface."""

    accepting_input: Tristate
    editing_input: Tristate
    ready_posture: Tristate
    active_evidence: bool
    interrupted: bool
    known_failure: bool
    current_error_present: bool
    success_candidate: bool
    ambiguous_interactive_surface: bool
    success_blocked: bool
    surface_signature: str
    notes: tuple[str, ...]


class BaseTrackedTurnSignalDetector(abc.ABC):
    """Abstract detector for one tool family."""

    @abc.abstractmethod
    def detect(
        self,
        *,
        output_text: str | None,
        parsed_surface: HoumaoParsedSurface | None,
    ) -> DetectedTurnSignals:
        """Return normalized simplified turn signals."""


class ClaudeTrackedTurnSignalDetector(BaseTrackedTurnSignalDetector):
    """Server-side wrapper over the proven Claude explore detector."""

    def detect(
        self,
        *,
        output_text: str | None,
        parsed_surface: HoumaoParsedSurface | None,
    ) -> DetectedTurnSignals:
        detector = select_claude_detector(observed_version=None)
        detected = detector.detect(output_text=output_text or "")
        ambiguous_interactive_surface = bool(
            parsed_surface is not None
            and (
                parsed_surface.input_mode == "modal"
                or parsed_surface.ui_context in {"selection_menu", "slash_command"}
                or parsed_surface.business_state == "awaiting_operator"
            )
            and not detected.active_evidence
        )
        success_blocked = bool(
            detected.footer_interruptable
            or detected.current_error_present
            or "ready_footer_advisory" in detected.notes
            or ambiguous_interactive_surface
        )
        return DetectedTurnSignals(
            accepting_input="no"
            if parsed_surface is not None and parsed_surface.input_mode in {"modal", "closed"}
            else detected.accepting_input,
            editing_input="unknown"
            if parsed_surface is not None and parsed_surface.input_mode == "modal"
            else detected.editing_input,
            ready_posture="unknown" if ambiguous_interactive_surface else detected.ready_posture,
            active_evidence=detected.active_evidence,
            interrupted=detected.interrupted,
            known_failure=detected.known_failure,
            current_error_present=detected.current_error_present,
            success_candidate=detected.success_candidate,
            ambiguous_interactive_surface=ambiguous_interactive_surface,
            success_blocked=success_blocked,
            surface_signature=detected.surface_signature,
            notes=detected.notes,
        )


class CodexTrackedTurnSignalDetector(BaseTrackedTurnSignalDetector):
    """Conservative raw-surface detector for Codex app-server TUIs."""

    def detect(
        self,
        *,
        output_text: str | None,
        parsed_surface: HoumaoParsedSurface | None,
    ) -> DetectedTurnSignals:
        text = output_text or ""
        lines = tuple(text.splitlines())
        prompt_index: int | None = None
        prompt_text = ""
        for index, line in enumerate(lines):
            match = _CODEx_PROMPT_RE.match(line)
            if match is not None:
                prompt_index = index
                prompt_text = match.group(1).strip()
        prompt_visible = prompt_index is not None
        active_status_row = any(_CODEX_WORKING_RE.match(line) is not None for line in lines)
        steer_handoff = _CODEX_STEER_INTERRUPTION_TEXT in text and active_status_row and prompt_visible
        interrupted = (
            _CODEX_INTERRUPTED_TEXT in text
            and prompt_visible
            and not active_status_row
        )
        current_error_present = any(
            _CODEX_ERROR_CELL_RE.match(line) is not None for line in lines
        )
        ambiguous_interactive_surface = bool(
            (parsed_surface is not None and parsed_surface.input_mode == "modal")
            or (
                parsed_surface is not None
                and parsed_surface.ui_context in {"selection_menu", "slash_command"}
            )
            or any(hint in text for hint in _CODEX_APPROVAL_HINTS)
        )
        active_evidence = bool(
            steer_handoff
            or active_status_row
            or (parsed_surface is not None and parsed_surface.business_state == "working")
        )
        ready_posture: Tristate
        if ambiguous_interactive_surface and not active_evidence:
            ready_posture = "unknown"
        elif (
            parsed_surface is not None
            and parsed_surface.input_mode == "freeform"
            and parsed_surface.business_state == "idle"
            and not active_evidence
        ):
            ready_posture = "yes"
        elif parsed_surface is not None and (
            parsed_surface.input_mode == "closed" or parsed_surface.business_state == "working"
        ):
            ready_posture = "no"
        else:
            ready_posture = "unknown"
        accepting_input: Tristate
        if parsed_surface is not None and parsed_surface.input_mode == "freeform":
            accepting_input = "yes"
        elif parsed_surface is not None and parsed_surface.input_mode in {"modal", "closed"}:
            accepting_input = "no"
        else:
            accepting_input = "unknown"
        editing_input: Tristate
        if prompt_visible and prompt_text:
            editing_input = "yes"
        elif prompt_visible:
            editing_input = "no"
        else:
            editing_input = "unknown"
        success_candidate = bool(
            prompt_visible
            and ready_posture == "yes"
            and not active_evidence
            and not current_error_present
            and any(
                _CODEX_WORKED_RE.match(line) is not None
                for line in lines[:prompt_index] if prompt_index is not None
            )
        )
        notes: list[str] = []
        if steer_handoff:
            notes.append("steer_handoff_active")
        if interrupted:
            notes.append("interrupted_signal_detected")
        if ambiguous_interactive_surface:
            notes.append("ambiguous_interactive_surface")
        if current_error_present:
            notes.append("current_error_present")
        if active_evidence:
            notes.append("active_turn_detected")
        surface_signature = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return DetectedTurnSignals(
            accepting_input=accepting_input,
            editing_input=editing_input,
            ready_posture=ready_posture,
            active_evidence=active_evidence,
            interrupted=interrupted,
            known_failure=False,
            current_error_present=current_error_present,
            success_candidate=success_candidate,
            ambiguous_interactive_surface=ambiguous_interactive_surface,
            success_blocked=bool(
                current_error_present or ambiguous_interactive_surface or active_evidence
            ),
            surface_signature=surface_signature,
            notes=tuple(notes),
        )


class FallbackTrackedTurnSignalDetector(BaseTrackedTurnSignalDetector):
    """Conservative detector for unsupported or unknown tools."""

    def detect(
        self,
        *,
        output_text: str | None,
        parsed_surface: HoumaoParsedSurface | None,
    ) -> DetectedTurnSignals:
        text = output_text or ""
        ready_posture: Tristate = "unknown"
        accepting_input: Tristate = "unknown"
        editing_input: Tristate = "unknown"
        ambiguous_interactive_surface = False
        active_evidence = False
        if parsed_surface is not None:
            if parsed_surface.input_mode == "freeform":
                accepting_input = "yes"
                editing_input = "no"
            elif parsed_surface.input_mode in {"modal", "closed"}:
                accepting_input = "no"
            if (
                parsed_surface.business_state == "idle"
                and parsed_surface.input_mode == "freeform"
                and parsed_surface.ui_context == "normal_prompt"
            ):
                ready_posture = "yes"
            elif parsed_surface.business_state == "working":
                active_evidence = True
                ready_posture = "no"
            elif parsed_surface.input_mode == "modal" or parsed_surface.ui_context in {
                "selection_menu",
                "slash_command",
            }:
                ambiguous_interactive_surface = True
        surface_signature = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return DetectedTurnSignals(
            accepting_input=accepting_input,
            editing_input=editing_input,
            ready_posture="unknown" if ambiguous_interactive_surface else ready_posture,
            active_evidence=active_evidence,
            interrupted=False,
            known_failure=False,
            current_error_present=False,
            success_candidate=False,
            ambiguous_interactive_surface=ambiguous_interactive_surface,
            success_blocked=ambiguous_interactive_surface,
            surface_signature=surface_signature,
            notes=(),
        )


def select_tracked_turn_signal_detector(*, tool: str) -> BaseTrackedTurnSignalDetector:
    """Return the best available detector for one tool."""

    normalized = tool.strip().lower()
    if normalized == "claude":
        return ClaudeTrackedTurnSignalDetector()
    if normalized == "codex":
        return CodexTrackedTurnSignalDetector()
    return FallbackTrackedTurnSignalDetector()
