"""Claude Code tracked-TUI detector profiles."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Sequence
from dataclasses import dataclass

from houmao.shared_tui_tracking.apps.claude_code.signals.prompt_behavior import (
    _CLAUDE_PROMPT_RE,
    ClaudePromptBehaviorVariantV2_1_X,
    build_prompt_area_snapshot,
    prompt_behavior_notes,
)
from houmao.shared_tui_tracking.apps.claude_code.signals.pending_input import (
    pending_input_state,
)

from houmao.shared_tui_tracking.detectors import BaseVersionedClaudeDetector
from houmao.shared_tui_tracking.models import (
    DetectedTurnSignals,
    ParsedSurfaceContext,
    RecentProfileFrame,
    TemporalHintSignals,
    Tristate,
)
from houmao.shared_tui_tracking.surface import SurfaceView


READY_FOOTER_ADVISORY_PATTERNS = (
    "Claude Code has switched from npm to native installer.",
    "Run `claude install`",
)
COMPLETION_MARKER_RE = re.compile(
    r"^✻\s+(?:Baked|Brewed|Churned|Cogitated|Cooked|Crunched|Sautéed|Worked)"
    r"\s+for\s+(?:(?:\d+h)\s+)?(?:(?:\d+m)\s+)?\d+s\b"
)
COLOR_RE = re.compile(r"\x1b\[38;5;(\d+)m")
INTERRUPTED_RE = re.compile(r"^⎿\s+(?:Interrupted|User rejected)\b")
SPINNER_LINE_RE = re.compile(r"^[✢✻✽✶·*]\s+\S.*(?:…|\.{3})(?:\s+\([^)]*\))?\s*$")
FOOTER_INTERRUPT_RE = re.compile(r"esc to(?: interrupt|…|\.\.\.)?")

_TEMPORAL_WINDOW_SECONDS = 600.0
_CONTIGUOUS_GAP_SECONDS = 2.0
_BLINK_CARRY_SECONDS = 1.0

_BUSY_FOOTER = "esc to interrupt"
_STATE_BEARING_LINE_RE = re.compile(r"^(?:❯|●|⎿|✻|⏵|─{8,}|╌{8,}|▔{4,})")

_TRUST_TITLE = "quick safety check"
_TRUST_OPTION = "trust this folder"
_APPROVAL_QUESTION = "do you want to "
_APPROVAL_FOOTER = "esc to cancel"
_PICKER_TITLE_RE = re.compile(r"^\s*select model\s*$", re.IGNORECASE)
_PICKER_OPTION_RE = re.compile(r"❯\s*\d+\.")
_PICKER_BORDER_RE = re.compile(r"▔{4,}")


class ClaudeCodeSignalDetectorV2_1_X(BaseVersionedClaudeDetector):
    """Tracked-TUI detector for Claude Code 2.1.296 and later.

    Qualified against the frozen 2026-10-12 campaign recordings of claude
    2.1.296 (zero false-ready across three blind-labeled sessions; see
    ``context/campaigns/debug/2026-10-12-claude-code-tui-parsing/``). Surface
    contract for the qualified family:

    - Modal surfaces (the workspace trust dialog, ``Do you want to …``
      approval panels with their cancel footer, and the ``Select model``
      picker) hold the whole surface: all four booleans are ``no`` and turn
      activity is suppressed while they are mounted.
    - Completion reads from the ``✻ <Verb> for <Nm Ns>`` dock scoped to the
      latest-turn region; persisted docks in scrollback do not complete a
      newer turn.
    - Busy evidence uses the ``esc to interrupt`` footer as primary, with a
      suffix-tolerant spinner line as secondary; while busy, readiness
      asserts ``no`` instead of degrading to ``unknown``.
    - Interruption matches ``⎿ Interrupted`` and ``⎿ User rejected`` status
      lines on the latest region status line.
    - Queued input reads from the composer placeholder payload (see
      ``signals/pending_input.py``).
    - Success candidacy is refused while the composer carries a draft, and
      the settle-identity ``surface_signature`` hashes state-bearing lines
      only so volatile furniture (tip lines, transient hints, the effort
      indicator) cannot invalidate a settled success.
    - The temporal channel (600 s window) infers silent Esc aborts (active →
      idle with no modal, no interrupt line, and no fresh region dock),
      carries busy evidence across the slash-autocomplete blink, and
      restores a pre-modal interrupted outcome when a modal opened from an
      idle interrupted surface dismisses.
    """

    qualified_through_version = "2.1.296"

    def __init__(self) -> None:
        """Initialize the maintained Claude 2.1.x detector profile."""

        self.m_detector_version: str = "2.1.x"
        self.m_prompt_behavior_variant: ClaudePromptBehaviorVariantV2_1_X = (
            ClaudePromptBehaviorVariantV2_1_X()
        )
        self.m_profile_notes: tuple[str, ...] = (
            "source_profile=claude-2.1.x",
            f"qualified_through_version={self.qualified_through_version}",
        )

    @property
    def detector_name(self) -> str:
        """Return the detector family name."""

        return "claude_code"

    @property
    def detector_version(self) -> str:
        """Return the detector selector version."""

        return self.m_detector_version

    @property
    def temporal_window_seconds(self) -> float:
        """Return the recent-window duration; the abort chain needs the whole turn."""

        return _TEMPORAL_WINDOW_SECONDS

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

        del parsed_surface
        surface = SurfaceView.from_text(output_text or "")
        prompt_snapshot = build_prompt_area_snapshot(surface)
        prompt_classification = self.m_prompt_behavior_variant.classify(prompt_snapshot)
        prompt_text = prompt_classification.prompt_text
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
        region_lines = _latest_turn_region_lines(surface)
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

        if footer_interruptable:
            for _, _, stripped_line in activity_region_lines:
                if stripped_line.strip().startswith("● ") and "Worked for" not in stripped_line:
                    active_reasons.append("active_block")
                    break

        if footer_interruptable and not active_reasons:
            active_reasons.append("interruptable_footer")

        active_evidence = bool(active_reasons) and not interrupted and not known_failure
        completion_marker = _scoped_completion_marker(region_lines)
        response_candidate_visible = prompt_visible and any(
            line.strip().startswith("● ") for line in region_lines
        )

        ambiguous_interactive_surface = slash_menu_visible and not active_evidence
        success_blocked = bool(
            footer_interruptable or current_error_present or ambiguous_interactive_surface
        )

        accepting_input: Tristate = "yes" if prompt_visible else "unknown"
        editing_input = _editing_input_state(
            prompt_visible=prompt_visible,
            prompt_kind=prompt_classification.kind,
        )
        pending_input = pending_input_state(surface=surface, composer=prompt_snapshot)
        ready_posture: Tristate = (
            "yes"
            if prompt_visible and not footer_interruptable and not slash_menu_visible
            else "unknown"
        )
        if ambiguous_interactive_surface:
            ready_posture = "unknown"

        if _modal_surface(surface):
            # Modal shield: trust dialog, approval panels, and pickers render
            # `❯`-option rows that false-fire the composer anchor; all four
            # booleans are no and turn activity is suppressed while they hold.
            notes.append("modal_2_1_296")
            return DetectedTurnSignals(
                detector_name=self.detector_name,
                detector_version=self.detector_version,
                accepting_input="no",
                editing_input="no",
                ready_posture="no",
                pending_input="no",
                prompt_visible=prompt_visible,
                prompt_text=prompt_text,
                footer_interruptable=footer_interruptable,
                active_evidence=False,
                active_reasons=(),
                interrupted=False,
                known_failure=known_failure,
                current_error_present=current_error_present,
                success_candidate=False,
                completion_marker=completion_marker,
                latest_status_line=latest_status_line,
                ambiguous_interactive_surface=True,
                success_blocked=True,
                surface_signature=_state_bearing_signature(surface),
                notes=tuple(dict.fromkeys(notes)),
            )

        # Assert-no readiness while busy: degrading to unknown during active
        # turns reads as ready-adjacent downstream.
        if active_evidence:
            ready_posture = "no"
        if not prompt_visible:
            # No composer anywhere: blank/dead surface (e.g. the trust-dialog
            # dismissal frame) — blocked, not unknown.
            accepting_input = "no"
            editing_input = "no"
            ready_posture = "no"
            pending_input = "no"
            notes.append("prompt_missing_blocked")

        success_candidate = bool(
            (completion_marker is not None or response_candidate_visible)
            and prompt_visible
            and not success_blocked
            and not interrupted
            and not known_failure
            # Typing is not a settle surface: the dock persists in the region
            # while the operator composes the next prompt.
            and editing_input != "yes"
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
        if active_evidence:
            notes.append("active_turn_detected")
        if interrupted:
            notes.append("interrupted_signal_detected")
        if known_failure:
            notes.append("known_failure_signal_detected")
        if ambiguous_interactive_surface:
            notes.append("ambiguous_interactive_surface")

        return DetectedTurnSignals(
            detector_name=self.detector_name,
            detector_version=self.detector_version,
            accepting_input=accepting_input,
            editing_input=editing_input,
            ready_posture=ready_posture,
            pending_input=pending_input,
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
            surface_signature=_state_bearing_signature(surface),
            notes=tuple(dict.fromkeys(notes)),
        )

    def build_temporal_frame(
        self,
        *,
        output_text: str | None,
        signals: DetectedTurnSignals,
        observed_at_seconds: float,
    ) -> object | None:
        """Return one Claude frame carrying busy/modal/dock surface facts."""

        del signals
        del observed_at_seconds
        if output_text is None:
            return None
        surface = SurfaceView.from_text(output_text)
        region_lines = _latest_turn_region_lines(surface)
        busy_footer = any(_BUSY_FOOTER in line for line in surface.footer_lines())
        spinner_visible = any(
            SPINNER_LINE_RE.match(line.strip()) for line in surface.stripped_lines
        )
        return _ClaudeTuiFrame296(
            active=busy_footer or spinner_visible,
            busy_footer=busy_footer,
            spinner_visible=spinner_visible,
            modal=_modal_surface(surface),
            slash_menu_open=_slash_menu_visible(surface),
            prompt_visible=surface.last_prompt_index() is not None,
            interrupt_line=any(
                INTERRUPTED_RE.match(line.strip()) is not None for line in region_lines
            ),
            region_dock_lines=tuple(
                line.strip()
                for line in region_lines
                if COMPLETION_MARKER_RE.match(line.strip()) is not None
            ),
            surface_dock_lines=tuple(
                line.strip()
                for line in surface.stripped_lines
                if COMPLETION_MARKER_RE.match(line.strip()) is not None
            ),
        )

    def derive_temporal_hints(
        self,
        *,
        recent_frames: Sequence[RecentProfileFrame],
    ) -> TemporalHintSignals:
        """Return silent-abort, slash-menu-blink, and modal-restore hints.

        Silent abort: claude 2.1.296's Esc mid-turn stops the turn with no
        transcript line and restores the prompt into the composer as a draft.
        The rule fires on idle frames whose contiguous history shows an active
        frame followed by no modal, no interrupt status line, and no fresh
        region dock (a dock is fresh only if it was not visible during the
        active frames — stale in-region docks survive aborts via scroll-off).

        Slash-menu blink: opening the slash autocomplete while busy hides the
        busy footer and the spinner; with the menu open and activity within
        1 s, the turn is still active.

        Modal restore: a modal opened from an idle surface whose pre-modal
        frames carried an interrupt line returns to that interrupted outcome
        on dismissal (the ``/model`` echo re-anchors the region, hiding the
        pre-modal line from the static needle).
        """

        frames = [item for item in recent_frames if isinstance(item.payload, _ClaudeTuiFrame296)]
        if len(frames) < 2:
            return TemporalHintSignals()
        contiguous = [frames[-1]]
        for frame in reversed(frames[:-1]):
            if (
                contiguous[0].observed_at_seconds - frame.observed_at_seconds
                > _CONTIGUOUS_GAP_SECONDS
            ):
                break
            contiguous.insert(0, frame)
        newest_frame = contiguous[-1]
        newest = newest_frame.payload
        assert isinstance(newest, _ClaudeTuiFrame296)
        if newest.modal or newest.active or not newest.prompt_visible:
            return TemporalHintSignals()

        if newest.slash_menu_open:
            recent_active = next(
                (
                    item
                    for item in reversed(contiguous[:-1])
                    if isinstance(item.payload, _ClaudeTuiFrame296) and item.payload.active
                ),
                None,
            )
            if (
                recent_active is not None
                and newest_frame.observed_at_seconds - recent_active.observed_at_seconds
                <= _BLINK_CARRY_SECONDS
            ):
                return TemporalHintSignals(
                    active_evidence=True,
                    active_reasons=("busy_evidence_blink_carry",),
                    ready_posture="no",
                    notes=("slash_menu_blink_carry",),
                )
            return TemporalHintSignals()

        if newest.interrupt_line:
            # The static needle already carries this surface.
            return TemporalHintSignals()

        last_modal_index = next(
            (
                index
                for index in range(len(contiguous) - 1, -1, -1)
                if _frame_payload(contiguous[index]).modal
            ),
            None,
        )
        last_active_index = next(
            (
                index
                for index in range(len(contiguous) - 1, -1, -1)
                if _frame_payload(contiguous[index]).active
            ),
            None,
        )

        if last_modal_index is not None and (
            last_active_index is None or last_modal_index > last_active_index
        ):
            modal_run_start = last_modal_index
            while modal_run_start > 0 and _frame_payload(contiguous[modal_run_start - 1]).modal:
                modal_run_start -= 1
            pre_modal_idle: list[RecentProfileFrame] = []
            for item in reversed(contiguous[:modal_run_start]):
                payload = _frame_payload(item)
                if payload.modal or payload.active:
                    break
                pre_modal_idle.append(item)
            # Any interrupt line in the pre-modal idle run marks the outcome the
            # modal was opened from; a slash-menu frame captured while typing the
            # modal command re-anchors the region and can hide it on the last
            # frame, so scan the whole run.
            if any(_frame_payload(item).interrupt_line for item in pre_modal_idle):
                return TemporalHintSignals(
                    interrupted=True,
                    notes=("modal_dismissed_interrupt_restore",),
                )
            return TemporalHintSignals()

        if last_active_index is None:
            return TemporalHintSignals()
        tail = contiguous[last_active_index + 1 :]
        if any(_frame_payload(item).modal or _frame_payload(item).interrupt_line for item in tail):
            return TemporalHintSignals()
        active_surface_docks: set[str] = set()
        for item in contiguous[: last_active_index + 1]:
            active_surface_docks.update(_frame_payload(item).surface_dock_lines)
        if any(dock_line not in active_surface_docks for dock_line in newest.region_dock_lines):
            # A dock line appeared that was not visible during the active
            # frames: this is a completed turn, not an abort.
            return TemporalHintSignals()
        return TemporalHintSignals(
            interrupted=True,
            notes=("silent_abort_idle",),
        )


@dataclass(frozen=True)
class _ClaudeTuiFrame296:
    """Temporal frame: busy/modal/menu facts plus dock visibility."""

    active: bool
    busy_footer: bool
    spinner_visible: bool
    modal: bool
    slash_menu_open: bool
    prompt_visible: bool
    interrupt_line: bool
    region_dock_lines: tuple[str, ...]
    surface_dock_lines: tuple[str, ...]


def _frame_payload(frame: RecentProfileFrame) -> _ClaudeTuiFrame296:
    """Return the typed Claude temporal frame payload."""

    payload = frame.payload
    assert isinstance(payload, _ClaudeTuiFrame296)
    return payload


def _modal_surface(surface: SurfaceView) -> bool:
    """Return whether the surface holds a 2.1.296 modal (trust/approval/picker)."""

    stripped_text = "\n".join(surface.stripped_lines)
    lowered = stripped_text.lower()
    if _TRUST_TITLE in lowered and _TRUST_OPTION in lowered:
        return True
    if _APPROVAL_QUESTION in lowered and _APPROVAL_FOOTER in lowered:
        return True
    lines = [line for line in surface.stripped_lines if line.strip()]
    if any(_PICKER_TITLE_RE.match(line) is not None for line in lines):
        return True
    return any(_PICKER_OPTION_RE.search(line) is not None for line in lines) and any(
        _PICKER_BORDER_RE.search(line) is not None for line in lines
    )


def _slash_menu_visible(surface: SurfaceView) -> bool:
    """Return whether the slash autocomplete menu is open above the composer."""

    prompt_index = surface.last_prompt_index()
    if prompt_index is None:
        return False
    prompt_line = surface.stripped_lines[prompt_index]
    match = _CLAUDE_PROMPT_RE.match(prompt_line)
    payload = match.group(1).strip() if match is not None else ""
    if not payload.startswith("/"):
        return False
    return any(
        line.strip().startswith("/") and not line.strip().startswith("❯")
        for line in surface.stripped_lines
        if line.strip()
    )


def _latest_turn_region_lines(surface: SurfaceView) -> tuple[str, ...]:
    """Return the latest-turn region lines (stripped) for one surface."""

    anchor_index = _latest_turn_prompt_anchor_index(surface)
    return tuple(
        stripped_line
        for _, _, stripped_line in _latest_turn_region_line_items(
            surface=surface,
            prompt_anchor_index=anchor_index,
        )
    )


def _scoped_completion_marker(region_lines: Sequence[str]) -> str | None:
    """Return the latest-turn-region completion dock, never full-scrollback."""

    marker: str | None = None
    for line in region_lines:
        match = COMPLETION_MARKER_RE.match(line.strip())
        if match is not None:
            marker = match.group(0)
    return marker


def _state_bearing_signature(surface: SurfaceView) -> str:
    """Return the settle-identity signature over state-bearing lines only.

    The projection keeps transcript anchors (``❯`` echoes, ``●`` blocks, ``⎿``
    status lines, ``✻`` docks), box rules, and the mode footer, and drops
    volatile furniture (tip lines, transient hints, the effort indicator,
    spinner animation) whose churn must not invalidate a settled success.
    """

    projection = [
        line
        for line in (raw.strip() for raw in surface.stripped_lines)
        if line and _STATE_BEARING_LINE_RE.match(line) is not None
    ]
    return hashlib.sha256("\n".join(projection).encode("utf-8")).hexdigest()


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
        if COMPLETION_MARKER_RE.match(stripped_line.strip()) is None:
            continue
        latest_completion_offset = offset
    if latest_completion_offset is None:
        return line_items
    return line_items[latest_completion_offset + 1 :]
