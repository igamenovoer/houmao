"""Candidate codex 0.162.x detector applied by monkey patch.

The campaign's no-product-change declaration keeps ``src/houmao/`` read-only,
so the proposed 0.162.x repairs live here and are applied at replay time by
patching four seams inside ``apps/codex_tui/profile.py``'s imported helper
namespace:

1. ``profile.detect_activity`` — ordering fix and queue needle. The shipped
   version checks ``_is_assistant_response_line`` before the status-row regex,
   so any status label outside the hardcoded bullet prefixes (``• Compacting
   context (Ns • esc to interrupt)`` in 0.162.x) is misclassified as assistant
   prose and the row never matches. The candidate tests the status row first.
   It also detects 0.162.x queued-follow-up rendering: a second ``› <payload>``
   line inside the latest-turn region above the status row (the shipped
   ``• Messages to be submitted …`` cell needles never fire on 0.162.x).
2. ``profile.has_blocking_overlay`` — adds the 0.162.x modal needles: the
   trust screen (``Trust this folder?`` / ``Trust and continue``), list-selection
   popups with the new footer (``enter select · esc back``; the shipped footer
   needle ``Press enter to confirm or esc to go back`` is dead), the warnings
   screen (``Warnings · … · Startup`` / ``esc dismiss``), and the send-input
   approval title.
3. ``profile.is_interrupted_surface`` — the shipped needle is the legacy
   two-sentence ``Conversation interrupted - tell the model…`` text; 0.162.x
   renders ``■ Conversation interrupted - use /feedback if something went
   wrong``. The candidate matches the ``conversation interrupted`` prefix.
4. ``profile._CODEX_WORKED_PREFIX`` — 0.162.x renders ``Worked for Ns • <time>``
   with no ``─ `` prefix.

On top of the patched base behavior, the candidate's ``detect`` applies the
labeling-rubric modal semantics (modal/startup surfaces: accepting/editing/
ready/pending ``no``, active suppressed — mirroring the kimi 2.1.x candidate)
and suppresses stale interrupt notices while a later turn is active.
"""

from __future__ import annotations

import dataclasses
import re
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from typing import Any

from houmao.shared_tui_tracking.apps.codex_tui import profile as codex_profile
from houmao.shared_tui_tracking.apps.codex_tui.signals.activity import (
    _AGENT_TURN_STATUS_RE,
    _BOOTSTRAP_STATUS_PREFIXES,
    _is_assistant_response_line,
    _latest_retry_status_line,
    _latest_collaboration_cell_is_in_flight,
    CodexActivitySignals,
)
from houmao.shared_tui_tracking.apps.codex_tui.signals.prompt_behavior import (
    CodexPromptBehaviorVariantV0_144_X,
)
from houmao.shared_tui_tracking.models import DetectedTurnSignals, ParsedSurfaceContext
from houmao.shared_tui_tracking.registry import (
    DetectorProfileRegistration,
    DetectorProfileRegistry,
)
from houmao.shared_tui_tracking.surface import SurfaceView

CANDIDATE_DETECTOR_VERSION = "0.162.x-candidate"

_TRUST_TITLE = "trust this folder?"
_TRUST_OPTION = "trust and continue"
_PICKER_FOOTER_0162 = "enter select · esc back"
_PICKER_FOOTER_0162_ALT = "esc back"
_WARNINGS_TITLE_RE = re.compile(r"^\s*Warnings\b.*\bStartup\b", re.MULTILINE)
_WARNINGS_FOOTER = "esc dismiss"
_SEND_INPUT_TITLE = "Would you like to send input to the"
_INTERRUPT_0162 = "conversation interrupted"
_WORKED_PREFIX_0162 = "Worked for "
_QUEUED_ECHO_RE = re.compile(r"^\s*›\s+\S")
_NUMBERED_STREAM_RE = re.compile(r"^\d+\.\s")
_FOOTER_MODEL_RE = re.compile(r"^\s*\S.*·\s*/", re.MULTILINE)
_WHITESPACE_RE = re.compile(r"\s+")


class CodexTuiSignalDetectorV0_162_XCandidate(codex_profile._BaseCodexTuiSignalDetector):
    """Candidate detector for observed codex-cli 0.162.x surfaces."""

    def __init__(self) -> None:
        """Initialize the candidate on the 0.144.x family's knobs."""

        super().__init__(
            detector_version=CANDIDATE_DETECTOR_VERSION,
            prompt_behavior_variant=CodexPromptBehaviorVariantV0_144_X(),
            include_collaboration_cells=True,
            include_queued_follow_up=True,
            temporal_growth_requires_prior_activity=True,
            infer_silent_interruption=True,
            profile_notes=("source_profile=codex-0.162.x-candidate",),
        )

    def detect(
        self,
        *,
        output_text: str | None,
        parsed_surface: ParsedSurfaceContext | None = None,
    ) -> DetectedTurnSignals:
        """Return base signals repaired for codex 0.162.x surfaces."""

        base = super().detect(output_text=output_text, parsed_surface=parsed_surface)
        surface, _fresh = codex_profile._current_codex_surface(output_text)
        stripped_text = "\n".join(surface.stripped_lines)

        modal = base.ambiguous_interactive_surface  # patched overlay fn already applied
        startup_splash = (
            base.prompt_visible and not modal and _FOOTER_MODEL_RE.search(stripped_text) is None
        )

        notes = list(base.notes)
        active = base.active_evidence
        interrupted = base.interrupted and not active  # stale-interrupt suppression

        pending_input = base.pending_input
        if not modal and active and _queued_echo_present(output_text or ""):
            pending_input = "yes"
            notes.append("queued_follow_up_0_162")

        if startup_splash:
            notes.append("startup_splash")
        if modal and base.ambiguous_interactive_surface:
            notes.append("modal_0_162")

        if modal or startup_splash:
            accepting_input = "no"
            editing_input = "no"
            ready_posture = "no"
            pending_input = "no"
            active = False
            interrupted = False
        else:
            accepting_input = base.accepting_input
            editing_input = base.editing_input
            ready_posture = "no" if active else base.ready_posture
            if not base.prompt_visible:
                # No composer anywhere: dead/exited surface (e.g. the resume
                # hint after quit) — blocked, not unknown.
                accepting_input = "no"
                editing_input = "no"
                ready_posture = "no"

        return dataclasses.replace(
            base,
            accepting_input=accepting_input,
            editing_input=editing_input,
            ready_posture=ready_posture,
            pending_input=pending_input,
            active_evidence=active,
            interrupted=interrupted,
            ambiguous_interactive_surface=modal or base.ambiguous_interactive_surface,
            success_candidate=bool(
                base.prompt_visible
                and ready_posture == "yes"
                and not (base.prompt_text or "").strip()
                and not interrupted
            ),
            success_blocked=bool(active or modal or startup_splash or interrupted),
            notes=tuple(dict.fromkeys(notes)),
        )

    def build_temporal_frame(
        self,
        *,
        output_text: str | None,
        signals: DetectedTurnSignals,
        observed_at_seconds: float,
    ) -> object | None:
        """Return the candidate frame, extending the base frame with dock state."""

        frame = super().build_temporal_frame(
            output_text=output_text, signals=signals, observed_at_seconds=observed_at_seconds
        )
        if frame is None:
            return None
        surface, _fresh = codex_profile._current_codex_surface(output_text)
        prompt_snapshot = codex_profile.build_prompt_area_snapshot(surface)
        region = codex_profile.latest_turn_lines(
            surface=surface, prompt_index=prompt_snapshot.prompt_index
        )
        docked = any(line.strip().startswith(_WORKED_PREFIX_0162) for line in region)
        turn_content = any(
            _is_assistant_response_line(line.strip()) or _NUMBERED_STREAM_RE.match(line.strip())
            for line in region
        )
        return _CodexTuiFrame162(
            base=frame, completion_docked=docked, turn_content_visible=turn_content
        )

    def derive_temporal_hints(self, *, recent_frames: Sequence) -> Any:
        """0.144.x temporal inference minus the response-visible veto, dock-aware.

        The shipped veto (``assistant_response_visible`` ⇒ no hints) read answer
        streaming as turn-over. In 0.162.x the status row hides while the final
        answer streams; the turn is over only when ``Worked for …`` docks in the
        latest-turn region. Growth while undocked with turn content in the
        region ⇒ active; a 1-2 sample status blink with no dock ⇒ active carry.
        The turn-content gate keeps startup/editing transitions (splash redraws,
        draft clears) from manufacturing growth-driven false activity.
        """

        from houmao.shared_tui_tracking.models import TemporalHintSignals

        frames = [item for item in recent_frames if isinstance(item.payload, _CodexTuiFrame162)]
        if len(frames) < 2:
            return TemporalHintSignals()
        contiguous = [frames[-1]]
        for frame in reversed(frames[:-1]):
            if contiguous[0].observed_at_seconds - frame.observed_at_seconds > 2.0:
                break
            contiguous.insert(0, frame)
        newest = contiguous[-1].payload
        assert isinstance(newest, _CodexTuiFrame162)
        newest_ts = contiguous[-1].observed_at_seconds
        base = newest.base
        if base.blocking_overlay or base.current_error_present or base.interrupted:
            return TemporalHintSignals()
        if newest.completion_docked:
            return TemporalHintSignals()
        if base.active_status_row_visible:
            return TemporalHintSignals()
        # Blink carry: status row gone for under a second, no dock, still busy.
        recent_active = next(
            (
                item
                for item in reversed(contiguous[:-1])
                if isinstance(item.payload, _CodexTuiFrame162)
                and item.payload.base.active_status_row_visible
                and not item.payload.completion_docked
            ),
            None,
        )
        if (
            recent_active is not None
            and newest_ts - recent_active.observed_at_seconds <= 1.0
            and base.ready_posture == "yes"
        ):
            return TemporalHintSignals(
                active_evidence=True,
                active_reasons=("status_row_blink_carry",),
                ready_posture="no",
                notes=("temporal_status_blink",),
            )
        # Streaming growth while undocked: transcript grew across the window and
        # the region carries turn content (assistant prose or numbered stream).
        if not newest.turn_content_visible:
            return TemporalHintSignals()
        oldest = contiguous[0].payload
        assert isinstance(oldest, _CodexTuiFrame162)
        if oldest.base.latest_turn_region_signature == base.latest_turn_region_signature:
            return TemporalHintSignals()
        growth_chars = base.latest_turn_region_length - oldest.base.latest_turn_region_length
        growth_lines = (
            base.latest_turn_region_line_count - oldest.base.latest_turn_region_line_count
        )
        if growth_chars < 48 and growth_lines < 2:
            return TemporalHintSignals()
        return TemporalHintSignals(
            active_evidence=True,
            active_reasons=("transcript_growth_undocked",),
            ready_posture="no",
            notes=("temporal_growth_undocked",),
        )


@dataclasses.dataclass(frozen=True)
class _CodexTuiFrame162:
    """Candidate frame: base codex frame plus dock state and turn-content flag."""

    base: object
    completion_docked: bool
    turn_content_visible: bool


def _queued_echo_present(output_text: str) -> bool:
    """Return whether a queued follow-up echo renders inside the live surface.

    0.162.x renders a mid-busy submitted follow-up as a ``› <text>`` line just
    above the ``• Working`` status row (later collapsing into ``+ N lines``,
    which carries no queue signal — a documented v1 limitation). The queued
    echo anchors the latest-turn region, so it looks exactly like the current
    turn's own echo in isolation. The disambiguator is what sits above it: a
    queued echo follows in-flight assistant prose of the current turn, while a
    turn-starting echo follows the previous turn's ``Worked for`` dock (or
    startup content). Single-snapshot, no tracker state needed.
    """

    surface = SurfaceView.from_text(output_text)
    lines = [line.strip() for line in surface.stripped_lines if line.strip()]
    prompt_indices = [index for index, line in enumerate(lines) if _QUEUED_ECHO_RE.match(line)]
    if len(prompt_indices) < 2:
        return False
    anchor = prompt_indices[-2]  # nearest › payload line above the composer
    for line in reversed(lines[:anchor]):
        if _is_assistant_response_line(line):
            return True
        if line.startswith(_WORKED_PREFIX_0162):
            return False
        if "conversation interrupted" in line.lower():
            return False
        if _AGENT_TURN_STATUS_RE.match(line):
            return False
        if line.startswith("›"):
            return False
    return False


def _detect_activity_0_162_x(
    *,
    latest_turn_lines: tuple[str, ...],
    live_edge_lines: tuple[str, ...],
    prompt_visible: bool,
    steer_interruption_text: str,
    include_collaboration_cells: bool = False,
    include_queued_follow_up: bool = False,
) -> CodexActivitySignals:
    """detect_activity with the status-row check ahead of the response-line break."""

    active_reasons: list[str] = []
    active_status_line: str | None = None
    for line in reversed(live_edge_lines):
        stripped = line.strip()
        match = _AGENT_TURN_STATUS_RE.match(stripped)
        if match is not None:
            header = match.group(1).strip()
            if any(header.startswith(prefix) for prefix in _BOOTSTRAP_STATUS_PREFIXES):
                continue
            active_status_line = stripped
            active_reasons.append("status_row")
            break
        if _is_assistant_response_line(stripped):
            break

    if any(
        line.strip().startswith(("• Calling ", "• Running ", "• Waited for background terminal · "))
        for line in live_edge_lines
    ):
        active_reasons.append("tool_cell")

    if include_collaboration_cells and _latest_collaboration_cell_is_in_flight(live_edge_lines):
        active_reasons.append("collaboration_cell")

    retry_status_line = _latest_retry_status_line(live_edge_lines)
    if retry_status_line is not None:
        active_reasons.append("stream_retry_status")

    return CodexActivitySignals(
        active_evidence=bool(active_reasons),
        active_status_row_visible=active_status_line is not None,
        latest_status_line=active_status_line or retry_status_line,
        active_reasons=tuple(dict.fromkeys(active_reasons)),
        steer_handoff=False,
        in_flight_tool_cell=False,
        pending_input_visible=False,
    )


def _has_blocking_overlay_0_162_x(surface: SurfaceView) -> bool:
    """Shipped overlay needles plus the 0.162.x modal surfaces."""

    if _original_overlay is not None and _original_overlay(surface):
        return True
    stripped_text = "\n".join(surface.stripped_lines)
    lowered = stripped_text.lower()
    if _TRUST_TITLE in lowered and _TRUST_OPTION in lowered:
        return True
    if _WARNINGS_TITLE_RE.search(stripped_text) is not None and _WARNINGS_FOOTER in lowered:
        return True
    if _SEND_INPUT_TITLE in stripped_text:
        return True
    if (
        _PICKER_FOOTER_0162 in lowered or _PICKER_FOOTER_0162_ALT in lowered
    ) and "select" in lowered:
        return True
    return False


def _is_interrupted_surface_0_162_x(
    *,
    latest_turn_lines: Sequence[str],
    prompt_visible: bool,
    active_status_row_visible: bool,
) -> bool:
    """Interruption rule with the 0.162.x notice text (prefix, wrap-normalized)."""

    normalized = _WHITESPACE_RE.sub(" ", "\n".join(latest_turn_lines)).lower()
    return _INTERRUPT_0162 in normalized and prompt_visible and not active_status_row_visible


_original_overlay = None


@contextmanager
def codex_0_162_x_patch() -> Iterator[None]:
    """Apply the candidate detector and helper patches for one replay."""

    global _original_overlay

    original_default = DetectorProfileRegistry.__dict__["default"].__func__
    original_detect_activity = codex_profile.detect_activity
    original_overlay = codex_profile.has_blocking_overlay
    _original_overlay = original_overlay
    original_is_interrupted = codex_profile.is_interrupted_surface
    original_worked_prefix = codex_profile._CODEX_WORKED_PREFIX

    def patched_default(cls: type[DetectorProfileRegistry]) -> DetectorProfileRegistry:
        """Return the default registry plus the 0.162.x candidate registration."""

        registry = original_default(cls)
        registrations = list(registry.m_registrations)
        candidate = DetectorProfileRegistration(
            app_id="codex_tui",
            detector_name="codex_tui",
            detector_version=CANDIDATE_DETECTOR_VERSION,
            minimum_supported_version=(0, 162, 0),
            maximum_supported_version=(0, 163, 0),
            profile_factory=CodexTuiSignalDetectorV0_162_XCandidate,
        )
        fallback_index = next(
            index
            for index, item in enumerate(registrations)
            if item.app_id == "codex_tui" and item.minimum_supported_version is None
        )
        registrations.insert(fallback_index, candidate)
        return DetectorProfileRegistry(registrations=tuple(registrations))

    DetectorProfileRegistry.default = classmethod(patched_default)  # type: ignore[assignment]
    codex_profile.detect_activity = _detect_activity_0_162_x
    codex_profile.has_blocking_overlay = _has_blocking_overlay_0_162_x
    codex_profile.is_interrupted_surface = _is_interrupted_surface_0_162_x
    codex_profile._CODEX_WORKED_PREFIX = _WORKED_PREFIX_0162
    try:
        yield
    finally:
        DetectorProfileRegistry.default = classmethod(original_default)  # type: ignore[assignment]
        codex_profile.detect_activity = original_detect_activity
        codex_profile.has_blocking_overlay = original_overlay
        codex_profile.is_interrupted_surface = original_is_interrupted
        codex_profile._CODEX_WORKED_PREFIX = original_worked_prefix
        _original_overlay = None
