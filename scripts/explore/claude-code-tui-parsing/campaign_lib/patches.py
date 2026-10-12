"""Candidate claude 2.1.296 detector applied by monkey patch.

The campaign's no-product-change declaration keeps ``src/houmao/`` read-only,
so the proposed 2.1.296 repairs live here and are applied at replay time by
patching seams inside ``apps/claude_code/profile.py`` and
``shared_tui_tracking/session.py``:

1. ``profile.COMPLETION_MARKER_RE`` — the shipped ``Worked for \\d+[smh]``
   needle is dead: 2.1.296 docks with a per-turn verb from an eight-verb set
   (``✻ <Verb> for <dur> · done <time>``) and ``Nm Ns`` durations. The
   candidate matches the ``✻``-anchored verb-set structure. The patched regex
   also repairs ``_latest_turn_activity_line_items`` slicing.
2. ``profile.SPINNER_LINE_RE`` — the shipped regex misses the suffix-less
   spinner variant (``✻ Cerebrating… `` with trailing whitespace). The
   candidate tolerates a missing ``(Ns · ↓ N tokens)`` suffix and trailing
   whitespace.
3. ``profile.pending_input_state`` — the shipped ghost-cell structure is dead:
   2.1.296 renders the queued state as the composer placeholder ``Press up to
   edit queued messages`` (dim-styled payload). The candidate matches that
   bounded label on the composer payload.
4. ``profile.INTERRUPTED_RE`` — denial paths render ``⎿ User rejected …``
   instead of ``⎿ Interrupted · What should Claude do instead?``; the
   candidate matches either essential token on the latest region status line
   and drops the full-sentence anchor.
5. ``TuiTrackerSession._invalidate_stale_terminal_outcome_for_newer_turn_locked``
   — visible-draft invalidation assumes a composer draft means a newer turn is
   being typed, so it clears the latched terminal outcome. 2.1.296 restores
   the aborted prompt into the composer on a silent Esc abort, and labels hold
   the latched outcome while the operator types (``editing_interrupted`` /
   ``editing_success`` spans). The candidate skips invalidation for
   ``reason="visible_draft"``; real turn activity (``active_signal``) and
   submissions (``input_submitted``) still clear stale outcomes.

On top of the patched base behavior, the candidate's ``detect`` applies the
modal shield (trust dialog, approval panels, model picker) before prompt
classification — modals force accepting/editing/ready/pending ``no`` with
activity suppressed, mirroring the kimi/codex candidates — re-scopes the
completion marker to the latest-turn region (the shipped full-scrollback
search false-fires on persisted docks), asserts ``ready_posture=no`` while
busy (the shipped profile returns ``unknown``, which is why baseline
ready_posture agreement is 0.49), refuses success candidacy while the
composer carries a draft, and replaces the settle-identity
``surface_signature`` with a projection over state-bearing lines (transcript
anchors, box rules, mode footer) so volatile furniture — tip lines below the
dock, transient hints, the effort indicator — cannot invalidate a settled
success (the shipped full-surface hash invalidated on a tip-line change and
the consumed turn authority blocked re-settling).

The candidate's temporal channel (600 s window) adds three rules:

- **Silent-abort inference**: an idle frame (no ``esc to interrupt`` footer,
  no spinner) following an active frame with no modal, no interrupt status
  line, and no *fresh* region dock since the last activity is a silent Esc
  abort (2.1.296 restores the draft and renders no transcript line). A dock
  line counts as fresh only when it was not visible during the active frames;
  this keeps stale in-region docks (visible after the aborted turn's echo
  scrolls off) from reading as completions. Emits ``interrupted=True`` so the
  terminal outcome latches and persists through the restored-draft span.
- **Slash-menu blink carry**: opening the slash autocomplete while busy hides
  the busy footer and the spinner for a frame; with a slash menu open and
  activity observed within 1 s, the turn is still active.
- **Modal-dismissal restore**: a modal opened from an idle surface showing a
  terminal interrupt line (e.g. the model picker after a denial) returns to
  that outcome on dismissal; the ``/model`` echo re-anchors the latest-turn
  region, hiding the pre-modal interrupt line from the static needle.
"""

from __future__ import annotations

import dataclasses
import hashlib
import re
from collections.abc import Iterator, Sequence
from contextlib import contextmanager

from houmao.shared_tui_tracking.apps.claude_code import profile as claude_profile
from houmao.shared_tui_tracking.apps.claude_code.signals.prompt_behavior import (
    _CLAUDE_PROMPT_RE,
    ClaudePromptBehaviorVariantV2_1_X,
)
from houmao.shared_tui_tracking.models import (
    DetectedTurnSignals,
    ParsedSurfaceContext,
    TemporalHintSignals,
)
from houmao.shared_tui_tracking.registry import (
    DetectorProfileRegistration,
    DetectorProfileRegistry,
)
from houmao.shared_tui_tracking.session import TuiTrackerSession
from houmao.shared_tui_tracking.surface import SurfaceView

CANDIDATE_DETECTOR_VERSION = "2.1.296-candidate"
CANDIDATE_REPLAY_TAG = "candidate-2.1.296"
_TEMPORAL_WINDOW_SECONDS = 600.0
_BLINK_CARRY_SECONDS = 1.0

_COMPLETION_DOCK_RE = re.compile(
    r"^✻\s+(?:Baked|Brewed|Churned|Cogitated|Cooked|Crunched|Sautéed|Worked)"
    r"\s+for\s+(?:(?:\d+h)\s+)?(?:(?:\d+m)\s+)?\d+s\b"
)
_SPINNER_LINE_296_RE = re.compile(r"^[✢✻✽✶·*]\s+\S.*(?:…|\.{3})(?:\s+\([^)]*\))?\s*$")
_INTERRUPT_STATUS_RE = re.compile(r"^⎿\s+(?:Interrupted|User rejected)\b")
_QUEUE_PLACEHOLDER = "press up to edit queued messages"
_BUSY_FOOTER = "esc to interrupt"
_STATE_BEARING_LINE_RE = re.compile(r"^(?:❯|●|⎿|✻|⏵|─{8,}|╌{8,}|▔{4,})")

_TRUST_TITLE = "quick safety check"
_TRUST_OPTION = "trust this folder"
_APPROVAL_QUESTION = "do you want to "
_APPROVAL_FOOTER = "esc to cancel"
_PICKER_TITLE_RE = re.compile(r"^\s*select model\s*$", re.IGNORECASE)
_PICKER_OPTION_RE = re.compile(r"❯\s*\d+\.")
_PICKER_BORDER_RE = re.compile(r"▔{4,}")


class ClaudeCodeSignalDetectorV2_1_296Candidate(claude_profile._BaseClaudeCodeSignalDetector):
    """Candidate detector for observed claude-code 2.1.296 surfaces."""

    def __init__(self) -> None:
        """Initialize the candidate on the 2.1.x family's knobs."""

        super().__init__(
            detector_version=CANDIDATE_DETECTOR_VERSION,
            prompt_behavior_variant=ClaudePromptBehaviorVariantV2_1_X(),
            profile_notes=("source_profile=claude-2.1.296-candidate",),
        )

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
        """Return base signals repaired for claude 2.1.296 surfaces."""

        base = super().detect(output_text=output_text, parsed_surface=parsed_surface)
        surface = SurfaceView.from_text(output_text or "")
        notes = list(base.notes)

        if _modal_surface(surface):
            # Modal shield: trust dialog, approval panels, and pickers render
            # `❯`-option rows that false-fire the composer anchor; all four
            # booleans are no and turn activity is suppressed while they hold.
            notes.append("modal_2_1_296")
            return dataclasses.replace(
                base,
                accepting_input="no",
                editing_input="no",
                ready_posture="no",
                pending_input="no",
                active_evidence=False,
                active_reasons=(),
                interrupted=False,
                success_candidate=False,
                success_blocked=True,
                ambiguous_interactive_surface=True,
                notes=tuple(dict.fromkeys(notes)),
            )

        prompt_visible = base.prompt_visible
        region_lines = _latest_turn_region_lines(surface)
        completion_marker = _scoped_completion_marker(region_lines)
        response_candidate_visible = prompt_visible and any(
            line.strip().startswith("● ") for line in region_lines
        )

        active = base.active_evidence
        accepting_input = base.accepting_input
        editing_input = base.editing_input
        pending_input = base.pending_input
        # Assert-no readiness while busy: the shipped profile returns unknown
        # during active turns, which reads as ready-adjacent downstream.
        ready_posture = "no" if active else base.ready_posture
        if not prompt_visible:
            # No composer anywhere: blank/dead surface (e.g. the trust-dialog
            # dismissal frame) — blocked, not unknown.
            accepting_input = "no"
            editing_input = "no"
            ready_posture = "no"
            pending_input = "no"
            notes.append("prompt_missing_blocked")

        success_blocked = bool(
            base.footer_interruptable
            or base.current_error_present
            or base.ambiguous_interactive_surface
        )
        success_candidate = bool(
            (completion_marker is not None or response_candidate_visible)
            and prompt_visible
            and not success_blocked
            and not base.interrupted
            and not base.known_failure
            # Typing is not a settle surface: the dock persists in the region
            # while the operator composes the next prompt.
            and editing_input != "yes"
        )

        return dataclasses.replace(
            base,
            accepting_input=accepting_input,
            editing_input=editing_input,
            ready_posture=ready_posture,
            pending_input=pending_input,
            completion_marker=completion_marker,
            success_candidate=success_candidate,
            success_blocked=success_blocked,
            # Settle-identity signature over state-bearing lines only: the
            # 2.1.296 idle surface churns volatile furniture (tip lines below
            # the dock, transient hints, the /effort indicator), and the
            # shipped full-surface hash lets that noise invalidate a settled
            # success with no path back (turn authority is already consumed).
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
        """Return the candidate frame carrying busy/modal/dock surface facts."""

        del signals
        if output_text is None:
            return None
        surface = SurfaceView.from_text(output_text)
        region_lines = _latest_turn_region_lines(surface)
        busy_footer = any(_BUSY_FOOTER in line for line in surface.footer_lines())
        spinner_visible = any(
            _SPINNER_LINE_296_RE.match(line.strip()) for line in surface.stripped_lines
        )
        return _ClaudeTuiFrame296(
            active=busy_footer or spinner_visible,
            busy_footer=busy_footer,
            spinner_visible=spinner_visible,
            modal=_modal_surface(surface),
            slash_menu_open=_slash_menu_visible(surface),
            prompt_visible=surface.last_prompt_index() is not None,
            interrupt_line=any(
                _INTERRUPT_STATUS_RE.match(line.strip()) is not None for line in region_lines
            ),
            region_dock_lines=tuple(
                line.strip()
                for line in region_lines
                if _COMPLETION_DOCK_RE.match(line.strip()) is not None
            ),
            surface_dock_lines=tuple(
                line.strip()
                for line in surface.stripped_lines
                if _COMPLETION_DOCK_RE.match(line.strip()) is not None
            ),
        )

    def derive_temporal_hints(self, *, recent_frames: Sequence) -> TemporalHintSignals:
        """Return silent-abort, slash-menu-blink, and modal-restore hints.

        Silent abort: 2.1.296's Esc mid-turn stops the turn with no transcript
        line and restores the prompt into the composer as a draft. The rule
        fires on idle frames whose contiguous history shows an active frame
        followed by no modal, no interrupt status line, and no fresh region
        dock (a dock is fresh only if it was not visible during the active
        frames — stale in-region docks survive aborts via scroll-off).

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
            if contiguous[0].observed_at_seconds - frame.observed_at_seconds > 2.0:
                break
            contiguous.insert(0, frame)
        newest_frame = contiguous[-1]
        newest = newest_frame.payload
        assert isinstance(newest, _ClaudeTuiFrame296)
        if newest.modal or newest.active or not newest.prompt_visible:
            return TemporalHintSignals()

        if newest.slash_menu_open:
            recent_active = next(
                (item for item in reversed(contiguous[:-1]) if item.payload.active),
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
                if contiguous[index].payload.modal
            ),
            None,
        )
        last_active_index = next(
            (
                index
                for index in range(len(contiguous) - 1, -1, -1)
                if contiguous[index].payload.active
            ),
            None,
        )

        if last_modal_index is not None and (
            last_active_index is None or last_modal_index > last_active_index
        ):
            modal_run_start = last_modal_index
            while modal_run_start > 0 and contiguous[modal_run_start - 1].payload.modal:
                modal_run_start -= 1
            pre_modal_idle: list = []
            for item in reversed(contiguous[:modal_run_start]):
                if item.payload.modal or item.payload.active:
                    break
                pre_modal_idle.append(item)
            # Any interrupt line in the pre-modal idle run marks the outcome the
            # modal was opened from; a slash-menu frame captured while typing the
            # modal command re-anchors the region and can hide it on the last
            # frame, so scan the whole run.
            if any(item.payload.interrupt_line for item in pre_modal_idle):
                return TemporalHintSignals(
                    interrupted=True,
                    notes=("modal_dismissed_interrupt_restore",),
                )
            return TemporalHintSignals()

        if last_active_index is None:
            return TemporalHintSignals()
        tail = contiguous[last_active_index + 1 :]
        if any(item.payload.modal or item.payload.interrupt_line for item in tail):
            return TemporalHintSignals()
        active_surface_docks: set[str] = set()
        for item in contiguous[: last_active_index + 1]:
            active_surface_docks.update(item.payload.surface_dock_lines)
        if any(dock_line not in active_surface_docks for dock_line in newest.region_dock_lines):
            # A dock line appeared that was not visible during the active
            # frames: this is a completed turn, not an abort.
            return TemporalHintSignals()
        return TemporalHintSignals(
            interrupted=True,
            notes=("silent_abort_idle",),
        )


@dataclasses.dataclass(frozen=True)
class _ClaudeTuiFrame296:
    """Candidate temporal frame: busy/modal/menu facts plus dock visibility."""

    active: bool
    busy_footer: bool
    spinner_visible: bool
    modal: bool
    slash_menu_open: bool
    prompt_visible: bool
    interrupt_line: bool
    region_dock_lines: tuple[str, ...]
    surface_dock_lines: tuple[str, ...]


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

    anchor_index = claude_profile._latest_turn_prompt_anchor_index(surface)
    return tuple(
        stripped_line
        for _, _, stripped_line in claude_profile._latest_turn_region_line_items(
            surface=surface,
            prompt_anchor_index=anchor_index,
        )
    )


def _scoped_completion_marker(region_lines: Sequence[str]) -> str | None:
    """Return the latest-turn-region completion dock, never full-scrollback."""

    marker = None
    for line in region_lines:
        match = _COMPLETION_DOCK_RE.match(line.strip())
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


def _pending_input_state_2_1_296(*, surface: SurfaceView, composer) -> str:
    """pending_input_state via the queued-composer placeholder needle."""

    del surface
    if not composer.prompt_visible:
        return "unknown"
    payload = (composer.payload_text or "").strip().lower()
    if _QUEUE_PLACEHOLDER in payload:
        return "yes"
    return "no"


@contextmanager
def claude_2_1_296_patch() -> Iterator[None]:
    """Apply the candidate detector and helper patches for one replay."""

    original_default = DetectorProfileRegistry.__dict__["default"].__func__
    original_completion_re = claude_profile.COMPLETION_MARKER_RE
    original_spinner_re = claude_profile.SPINNER_LINE_RE
    original_interrupted_re = claude_profile.INTERRUPTED_RE
    original_pending_input_state = claude_profile.pending_input_state
    original_invalidate = TuiTrackerSession._invalidate_stale_terminal_outcome_for_newer_turn_locked

    def patched_default(cls: type[DetectorProfileRegistry]) -> DetectorProfileRegistry:
        """Return the default registry plus the 2.1.296 candidate registration."""

        registry = original_default(cls)
        candidate = DetectorProfileRegistration(
            app_id="claude_code",
            detector_name="claude_code",
            detector_version=CANDIDATE_DETECTOR_VERSION,
            minimum_supported_version=(2, 1, 296),
            maximum_supported_version=(2, 2, 0),
            profile_factory=ClaudeCodeSignalDetectorV2_1_296Candidate,
            qualified_through_version="2.1.296",
        )
        return DetectorProfileRegistry(registrations=(*registry.m_registrations, candidate))

    def patched_invalidate(self, *, reason: str):
        """Skip visible-draft invalidation; typing does not clear an outcome."""

        if reason == "visible_draft":
            return self.m_state.last_turn_result, self.m_state.last_turn_source
        return original_invalidate(self, reason=reason)

    DetectorProfileRegistry.default = classmethod(patched_default)  # type: ignore[assignment]
    claude_profile.COMPLETION_MARKER_RE = _COMPLETION_DOCK_RE
    claude_profile.SPINNER_LINE_RE = _SPINNER_LINE_296_RE
    claude_profile.INTERRUPTED_RE = _INTERRUPT_STATUS_RE
    claude_profile.pending_input_state = _pending_input_state_2_1_296
    TuiTrackerSession._invalidate_stale_terminal_outcome_for_newer_turn_locked = patched_invalidate
    try:
        yield
    finally:
        DetectorProfileRegistry.default = classmethod(original_default)  # type: ignore[assignment]
        claude_profile.COMPLETION_MARKER_RE = original_completion_re
        claude_profile.SPINNER_LINE_RE = original_spinner_re
        claude_profile.INTERRUPTED_RE = original_interrupted_re
        claude_profile.pending_input_state = original_pending_input_state
        TuiTrackerSession._invalidate_stale_terminal_outcome_for_newer_turn_locked = (
            original_invalidate
        )
