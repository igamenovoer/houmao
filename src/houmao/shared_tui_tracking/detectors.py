"""Official/runtime detector boundary for tracked TUI state."""

from __future__ import annotations

import abc
import hashlib
import re
from dataclasses import dataclass
from typing import Iterable

from houmao.shared_tui_tracking.models import DetectedTurnSignals, ParsedSurfaceContext, Tristate


ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
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
READY_FOOTER_ADVISORY_PATTERNS = (
    "Claude Code has switched from npm to native installer.",
    "Run `claude install`",
)
COMPLETION_MARKER_RE = re.compile(r"Worked for \d+[smh]")
COLOR_RE = re.compile(r"\x1b\[38;5;(\d+)m")
INTERRUPTED_RE = re.compile(r"^⎿\s+Interrupted · What should Claude do instead\?$")
SPINNER_LINE_RE = re.compile(r"^[✢✻✽✶·*]\s+.+…(?:\s+\(.+\))?$")
FOOTER_INTERRUPT_RE = re.compile(r"esc to(?: interrupt|…|\\.\\.\\.)?")
_CODEX_PROMPT_RE = re.compile(r"^\s*›(.*)$")
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
class SurfaceView:
    """Structured current-surface view derived from raw ANSI text."""

    raw_text: str
    raw_lines: tuple[str, ...]
    stripped_lines: tuple[str, ...]

    @classmethod
    def from_text(cls, raw_text: str) -> "SurfaceView":
        """Build one view from raw ANSI pane text."""

        raw_lines = tuple(raw_text.splitlines())
        stripped_lines = tuple(strip_ansi(line) for line in raw_lines)
        return cls(raw_text=raw_text, raw_lines=raw_lines, stripped_lines=stripped_lines)

    def last_prompt_index(self) -> int | None:
        """Return the last visible prompt-line index if present."""

        indices = [
            index for index, line in enumerate(self.stripped_lines) if line.strip().startswith("❯")
        ]
        return indices[-1] if indices else None

    def last_status_index(self) -> int | None:
        """Return the last visible Claude status-line index if present."""

        indices = [
            index for index, line in enumerate(self.stripped_lines) if line.strip().startswith("⎿")
        ]
        return indices[-1] if indices else None

    def latest_status_line(self) -> str | None:
        """Return the last visible stripped status line."""

        index = self.last_status_index()
        if index is None:
            return None
        return self.stripped_lines[index].strip()

    def prompt_visible_after(self, index: int) -> bool:
        """Return whether a fresh prompt is visible below one line index."""

        last_prompt_index = self.last_prompt_index()
        return last_prompt_index is not None and last_prompt_index > index

    def prompt_text(self) -> str | None:
        """Return stripped text from the latest visible prompt line."""

        index = self.last_prompt_index()
        if index is None:
            return None
        line = self.stripped_lines[index].strip()
        if not line.startswith("❯"):
            return None
        return line[1:].strip()

    def footer_lines(self, count: int = 4) -> tuple[str, ...]:
        """Return the last few non-empty stripped lines for footer inspection."""

        if count <= 0:
            return ()
        lines = [line for line in self.stripped_lines if line.strip()]
        return tuple(lines[-count:])

    def footer_raw_lines(self, count: int = 4) -> tuple[str, ...]:
        """Return the last few non-empty raw lines for footer inspection."""

        if count <= 0:
            return ()
        lines = [
            raw_line
            for raw_line, stripped_line in zip(self.raw_lines, self.stripped_lines, strict=True)
            if stripped_line.strip()
        ]
        return tuple(lines[-count:])

    def iter_lines_with_indices(self) -> Iterable[tuple[int, str, str]]:
        """Yield `(index, raw_line, stripped_line)` tuples."""

        for index, (raw_line, stripped_line) in enumerate(
            zip(self.raw_lines, self.stripped_lines, strict=True)
        ):
            yield index, raw_line, stripped_line


class BaseTrackedTurnSignalDetector(abc.ABC):
    """Abstract detector for one tool family."""

    @abc.abstractmethod
    def detect(
        self,
        *,
        output_text: str | None,
        parsed_surface: ParsedSurfaceContext | None = None,
    ) -> DetectedTurnSignals:
        """Return normalized tracked turn signals."""


class BaseVersionedClaudeDetector(BaseTrackedTurnSignalDetector, abc.ABC):
    """Abstract Claude detector with version scoring."""

    @property
    @abc.abstractmethod
    def detector_name(self) -> str:
        """Return the detector family name."""

    @property
    @abc.abstractmethod
    def detector_version(self) -> str:
        """Return the detector version selector."""

    @abc.abstractmethod
    def compatibility_score(self, *, observed_version: str | None) -> int:
        """Return a higher score for a closer-compatible version match."""


class ClaudeCodeSignalDetectorV2_1_X(BaseVersionedClaudeDetector):
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

    def detect(
        self,
        *,
        output_text: str | None,
        parsed_surface: ParsedSurfaceContext | None = None,
    ) -> DetectedTurnSignals:
        """Return normalized tracked signals for one Claude surface."""

        surface = SurfaceView.from_text(output_text or "")
        prompt_text = surface.prompt_text()
        last_prompt_index = surface.last_prompt_index()
        prompt_visible = last_prompt_index is not None
        footer_interruptable = any(
            FOOTER_INTERRUPT_RE.search(line) is not None for line in surface.footer_lines()
        )
        footer_has_ready_advisory = any(
            pattern in line
            for line in surface.footer_lines()
            for pattern in READY_FOOTER_ADVISORY_PATTERNS
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

        ambiguous_interactive_surface = slash_menu_visible and not active_evidence
        success_blocked = bool(
            footer_interruptable
            or footer_has_ready_advisory
            or current_error_present
            or ambiguous_interactive_surface
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
        editing_input: Tristate = "yes" if prompt_text else "no" if prompt_visible else "unknown"
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


class FallbackClaudeDetector(BaseVersionedClaudeDetector):
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

    def detect(
        self,
        *,
        output_text: str | None,
        parsed_surface: ParsedSurfaceContext | None = None,
    ) -> DetectedTurnSignals:
        """Return a conservative detector result."""

        surface = SurfaceView.from_text(output_text or "")
        prompt_visible = surface.last_prompt_index() is not None
        prompt_text = surface.prompt_text()
        stripped_text = "\n".join(surface.stripped_lines)
        surface_signature = hashlib.sha256(stripped_text.encode("utf-8")).hexdigest()
        return DetectedTurnSignals(
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
            ambiguous_interactive_surface=False,
            success_blocked=False,
            surface_signature=surface_signature,
            notes=("fallback_detector",),
        )


class CodexTrackedTurnSignalDetector(BaseTrackedTurnSignalDetector):
    """Conservative raw-surface detector for Codex app-server TUIs."""

    def detect(
        self,
        *,
        output_text: str | None,
        parsed_surface: ParsedSurfaceContext | None = None,
    ) -> DetectedTurnSignals:
        """Return normalized tracked signals for one Codex surface."""

        text = output_text or ""
        lines = tuple(text.splitlines())
        prompt_index: int | None = None
        prompt_text = ""
        for index, line in enumerate(lines):
            match = _CODEX_PROMPT_RE.match(line)
            if match is not None:
                prompt_index = index
                prompt_text = match.group(1).strip()
        prompt_visible = prompt_index is not None
        active_status_row = any(_CODEX_WORKING_RE.match(line) is not None for line in lines)
        steer_handoff = (
            _CODEX_STEER_INTERRUPTION_TEXT in text and active_status_row and prompt_visible
        )
        interrupted = _CODEX_INTERRUPTED_TEXT in text and prompt_visible and not active_status_row
        current_error_present = any(_CODEX_ERROR_CELL_RE.match(line) is not None for line in lines)
        ambiguous_interactive_surface = any(hint in text for hint in _CODEX_APPROVAL_HINTS)
        active_evidence = bool(steer_handoff or active_status_row)
        ready_posture: Tristate
        if ambiguous_interactive_surface and not active_evidence:
            ready_posture = "unknown"
        elif prompt_visible and not active_evidence and not ambiguous_interactive_surface:
            ready_posture = "yes"
        elif active_evidence:
            ready_posture = "no"
        else:
            ready_posture = "unknown"
        accepting_input: Tristate
        if prompt_visible and not ambiguous_interactive_surface:
            accepting_input = "yes"
        elif ambiguous_interactive_surface:
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
                for line in lines[:prompt_index]
                if prompt_index is not None
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
            detector_name="codex_app_server",
            detector_version="builtin",
            accepting_input=accepting_input,
            editing_input=editing_input,
            ready_posture=ready_posture,
            prompt_visible=prompt_visible,
            prompt_text=prompt_text or None,
            footer_interruptable=active_status_row,
            active_evidence=active_evidence,
            active_reasons=("codex_activity",) if active_evidence else (),
            interrupted=interrupted,
            known_failure=False,
            current_error_present=current_error_present,
            success_candidate=success_candidate,
            completion_marker=None,
            latest_status_line=None,
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
        parsed_surface: ParsedSurfaceContext | None = None,
    ) -> DetectedTurnSignals:
        """Return normalized tracked signals for one unsupported surface."""

        text = output_text or ""
        ready_posture: Tristate = "unknown"
        accepting_input: Tristate = "unknown"
        editing_input: Tristate = "unknown"
        ambiguous_interactive_surface = False
        active_evidence = False
        surface_signature = hashlib.sha256(text.encode("utf-8")).hexdigest()
        notes: tuple[str, ...] = ("fallback_detector",)
        if ambiguous_interactive_surface:
            notes = ("fallback_detector", "ambiguous_interactive_surface")
        return DetectedTurnSignals(
            detector_name="unsupported_tool",
            detector_version="builtin",
            accepting_input=accepting_input,
            editing_input=editing_input,
            ready_posture=ready_posture,
            prompt_visible=False,
            prompt_text=None,
            footer_interruptable=False,
            active_evidence=active_evidence,
            active_reasons=("background_working",) if active_evidence else (),
            interrupted=False,
            known_failure=False,
            current_error_present=False,
            success_candidate=False,
            completion_marker=None,
            latest_status_line=None,
            ambiguous_interactive_surface=ambiguous_interactive_surface,
            success_blocked=ambiguous_interactive_surface or active_evidence,
            surface_signature=surface_signature,
            notes=notes,
        )


def select_claude_detector(*, observed_version: str | None) -> BaseTrackedTurnSignalDetector:
    """Return the closest-compatible Claude detector for one observed version."""

    from houmao.shared_tui_tracking.registry import DetectorProfileRegistry

    resolved = DetectorProfileRegistry.default().resolve(
        app_id="claude_code",
        observed_version=observed_version,
    )
    return resolved.detector


def select_tracked_turn_signal_detector(
    *,
    tool: str,
    observed_version: str | None = None,
) -> BaseTrackedTurnSignalDetector:
    """Return the best available detector for one official/runtime tool."""

    from houmao.shared_tui_tracking.registry import DetectorProfileRegistry, app_id_from_tool

    resolved = DetectorProfileRegistry.default().resolve(
        app_id=app_id_from_tool(tool=tool),
        observed_version=observed_version,
    )
    return resolved.detector


def strip_ansi(text: str) -> str:
    """Return one ANSI-stripped string."""

    return ANSI_ESCAPE_RE.sub("", text).replace("\u00a0", " ")
