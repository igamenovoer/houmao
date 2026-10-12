"""Codex TUI tracked-TUI detector profiles with temporal inference.

The maintained profile targets codex 0.162.x surfaces and is qualified against
the blind-labeled 0.162.1 recordings from the 2026-10-12 debug campaign
(`context/campaigns/debug/2026-10-12-codex-tui-parsing/`). Repairs over the
retired 0.144.x family:

- The status-row label family is checked before the assistant-prose break in
  `detect_activity`, so compaction and other maintained status labels count as
  busy instead of being swallowed as prose.
- The interruption needle is the whitespace-normalized `Conversation
  interrupted` prefix; a visible notice with concurrent activity is stale
  scrollback and does not mark the surface interrupted.
- The completion dock renders as `Worked for Ns • HH:MM` with no box-drawing
  prefix.
- 0.162.x modal surfaces (workspace trust, list-selection pickers, warnings
  screen, send-input dialog) are blocking overlays and report closed input
  admission with active suppressed rather than manufacturing activity.
- Temporal hints are dock-aware: latest-turn growth while the `Worked for`
  dock is absent counts as active (0.162 hides the status row while the final
  answer streams), and a status-row blink of about one second or less carries
  active across the seam.
- Pending input is recognized from the queued-echo surface (`› <text>` above
  the status row); the legacy pending-section headers never render in 0.162.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from collections.abc import Sequence
from dataclasses import dataclass

from houmao.shared_tui_tracking.apps.codex_tui.signals.activity import (
    assistant_response_visible,
    detect_activity,
    latest_turn_region_signature,
    queued_echo_present,
)
from houmao.shared_tui_tracking.apps.codex_tui.signals.error_cells import (
    DEGRADED_CHAT_CONTEXT_NOTE,
    KNOWN_FAILURE_NOTE,
    prompt_adjacent_terminal_signal,
)
from houmao.shared_tui_tracking.apps.codex_tui.signals.interrupted import (
    is_interrupted_surface,
)
from houmao.shared_tui_tracking.apps.codex_tui.signals.overlays import has_blocking_overlay
from houmao.shared_tui_tracking.apps.codex_tui.signals.prompt_behavior import (
    CodexPromptBehaviorVariant,
    CodexPromptBehaviorVariantV0_162_X,
    build_prompt_area_snapshot,
    latest_turn_live_edge_lines,
    latest_turn_lines,
    prompt_behavior_notes,
)
from houmao.shared_tui_tracking.apps.codex_tui.signals.ready import (
    accepting_input_state,
    editing_input_state,
    ready_posture_state,
)
from houmao.shared_tui_tracking.detectors import BaseTrackedTurnSignalDetector
from houmao.shared_tui_tracking.models import (
    DegradedChatContextDiagnostic,
    DetectedTurnSignals,
    ParsedSurfaceContext,
    RecentProfileFrame,
    TemporalHintSignals,
    Tristate,
)
from houmao.shared_tui_tracking.surface import SurfaceView


# 0.162.x dock: `Worked for Ns • HH:MM` with no box-drawing prefix
# (codex-rs/tui/src/history_cell/separators.rs).
_CODEX_WORKED_PREFIX = "Worked for "
_TEMPORAL_WINDOW_SECONDS = 3.0
_MAX_CONTIGUOUS_GAP_SECONDS = 2.0
_STATUS_BLINK_CARRY_SECONDS = 1.0
_MIN_GROWTH_CHARS = 48
_MIN_ADDED_LINES = 2
_MAX_DEGRADED_MESSAGE_PREVIEW_CHARS = 240
_NUMBERED_STREAM_RE = re.compile(r"^\d+\.\s")
# Startup splash: the placeholder composer renders before the footer model
# line (`<model> · /…`) appears.
_FOOTER_MODEL_RE = re.compile(r"^\s*\S.*·\s*/", re.MULTILINE)
LOGGER = logging.getLogger(__name__)
_CODEX_PROVIDER_MARKERS = ("OpenAI Codex",)


@dataclass(frozen=True)
class _CodexTuiFrame:
    """Profile-private Codex frame stored inside the recent temporal window."""

    prompt_visible: bool
    blocking_overlay: bool
    active_status_row_visible: bool
    compaction_status_visible: bool
    active_evidence: bool
    assistant_response_visible: bool
    current_error_present: bool
    interrupted: bool
    ready_posture: str
    draft_visible: bool
    latest_turn_region_signature: str
    latest_turn_region_length: int
    latest_turn_region_line_count: int
    completion_docked: bool
    turn_content_visible: bool


class _BaseCodexTuiSignalDetector(BaseTrackedTurnSignalDetector):
    """Tracked-TUI detector for one Codex version family."""

    def __init__(
        self,
        *,
        detector_version: str,
        prompt_behavior_variant: CodexPromptBehaviorVariant,
        include_collaboration_cells: bool = False,
        profile_notes: tuple[str, ...] = (),
    ) -> None:
        """Initialize one Codex detector profile."""

        self.m_detector_version: str = detector_version
        self.m_prompt_behavior_variant: CodexPromptBehaviorVariant = prompt_behavior_variant
        self.m_include_collaboration_cells: bool = include_collaboration_cells
        self.m_profile_notes: tuple[str, ...] = profile_notes

    @property
    def detector_version(self) -> str:
        """Return the stable detector profile selector."""

        return self.m_detector_version

    @property
    def temporal_window_seconds(self) -> float:
        """Return the recent-window duration used by this profile."""

        return _TEMPORAL_WINDOW_SECONDS

    def detect(
        self,
        *,
        output_text: str | None,
        parsed_surface: ParsedSurfaceContext | None = None,
    ) -> DetectedTurnSignals:
        """Return normalized tracked signals for one Codex TUI surface."""

        del parsed_surface
        surface, surface_fresh = _current_codex_surface(output_text)
        stripped_text = "\n".join(surface.stripped_lines)
        prompt_snapshot = build_prompt_area_snapshot(surface)
        latest_turn_region_lines = latest_turn_lines(
            surface=surface,
            prompt_index=prompt_snapshot.prompt_index,
        )
        live_edge_lines = latest_turn_live_edge_lines(surface=surface)
        prompt_classification = self.m_prompt_behavior_variant.classify(prompt_snapshot)
        blocking_overlay = has_blocking_overlay(surface)
        activity = detect_activity(
            latest_turn_lines=latest_turn_region_lines,
            live_edge_lines=live_edge_lines,
            prompt_visible=prompt_snapshot.prompt_visible,
            include_collaboration_cells=self.m_include_collaboration_cells,
        )
        queued_echo = queued_echo_present(surface=surface)
        active_evidence = activity.active_evidence or queued_echo
        active_reasons = tuple(
            dict.fromkeys((*activity.active_reasons, *(("queued_follow_up",) if queued_echo else ())))
        )
        interrupted = (
            is_interrupted_surface(
                latest_turn_lines=latest_turn_region_lines,
                prompt_visible=prompt_snapshot.prompt_visible,
                active_status_row_visible=activity.active_status_row_visible,
            )
            and not active_evidence
        )
        terminal_signal = prompt_adjacent_terminal_signal(latest_turn_region_lines)
        current_error_present = terminal_signal is not None
        degraded_context = (
            terminal_signal.degraded_context if terminal_signal is not None else False
        )
        degraded_context_diagnostic = (
            DegradedChatContextDiagnostic(
                tool_name="codex",
                detector_name="codex_tui",
                detector_version=self.detector_version,
                degraded_error_type=terminal_signal.degraded_error_type or "unknown",
                message_preview=_message_preview(terminal_signal.block_text),
            )
            if degraded_context and terminal_signal is not None
            else None
        )
        known_failure = (
            terminal_signal.known_failure
            if terminal_signal is not None and not terminal_signal.degraded_context
            else False
        )
        startup_splash = (
            prompt_snapshot.prompt_visible
            and not blocking_overlay
            and _FOOTER_MODEL_RE.search(stripped_text) is None
        )
        completion_marker = next(
            (
                line
                for line in reversed(latest_turn_region_lines)
                if line.strip().startswith(_CODEX_WORKED_PREFIX)
            ),
            None,
        )

        if blocking_overlay or startup_splash:
            # Operator surfaces close input admission without manufacturing
            # activity, interruption, or a terminal result.
            accepting_input: Tristate = "no"
            editing_input: Tristate = "no"
            ready_posture: Tristate = "no"
            pending_input: Tristate = "no"
            active_evidence = False
            active_reasons = ()
            interrupted = False
            success_candidate = False
        else:
            accepting_input = accepting_input_state(
                prompt_visible=prompt_snapshot.prompt_visible,
                blocking_overlay=blocking_overlay,
            )
            editing_input = editing_input_state(
                prompt_visible=prompt_snapshot.prompt_visible,
                prompt_classification=prompt_classification,
            )
            ready_posture = ready_posture_state(
                prompt_visible=prompt_snapshot.prompt_visible,
                blocking_overlay=blocking_overlay,
                active_evidence=active_evidence,
            )
            if not prompt_snapshot.prompt_visible:
                # No composer anywhere: dead/exited surface (for example the
                # resume hint after quit) — blocked, not unknown.
                accepting_input = "no"
                editing_input = "no"
                ready_posture = "no"
            if queued_echo:
                pending_input = "yes"
            elif surface_fresh and prompt_snapshot.prompt_visible:
                pending_input = "no"
            else:
                pending_input = "unknown"
            success_candidate = bool(
                prompt_snapshot.prompt_visible
                and ready_posture == "yes"
                and not active_evidence
                and not current_error_present
                and not interrupted
                and not known_failure
                and prompt_classification.kind in {"empty", "placeholder"}
            )

        success_blocked = bool(
            active_evidence
            or blocking_overlay
            or startup_splash
            or interrupted
            or current_error_present
            or known_failure
        )
        notes: list[str] = [
            *self.m_profile_notes,
            *prompt_behavior_notes(
                variant=self.m_prompt_behavior_variant,
                classification=prompt_classification,
            ),
        ]
        if not surface_fresh:
            notes.append("provider_surface_not_fresh")
        if startup_splash:
            notes.append("startup_splash")
        if interrupted:
            notes.append("interrupted_signal_detected")
        if blocking_overlay:
            notes.append("ambiguous_interactive_surface")
        if current_error_present:
            notes.append("current_error_present")
        if degraded_context:
            notes.append(DEGRADED_CHAT_CONTEXT_NOTE)
        if known_failure:
            notes.append(KNOWN_FAILURE_NOTE)
        if active_evidence:
            notes.append("active_turn_detected")
        if queued_echo:
            notes.append("queued_follow_up_echo")
        if completion_marker is not None:
            notes.append("completion_marker_visible")

        surface_signature = hashlib.sha256(stripped_text.encode("utf-8")).hexdigest()
        return DetectedTurnSignals(
            detector_name="codex_tui",
            detector_version=self.detector_version,
            accepting_input=accepting_input,
            editing_input=editing_input,
            ready_posture=ready_posture,
            pending_input=pending_input,
            prompt_visible=prompt_snapshot.prompt_visible,
            prompt_text=prompt_classification.prompt_text,
            footer_interruptable=activity.active_status_row_visible,
            active_evidence=active_evidence,
            active_reasons=active_reasons,
            interrupted=interrupted,
            known_failure=known_failure,
            current_error_present=current_error_present,
            success_candidate=success_candidate,
            completion_marker=completion_marker,
            latest_status_line=activity.latest_status_line,
            ambiguous_interactive_surface=blocking_overlay,
            success_blocked=success_blocked,
            surface_signature=surface_signature,
            notes=tuple(dict.fromkeys(notes)),
            chat_context="degraded" if degraded_context else "current",
            chat_context_diagnostic=degraded_context_diagnostic,
        )

    def build_temporal_frame(
        self,
        *,
        output_text: str | None,
        signals: DetectedTurnSignals,
        observed_at_seconds: float,
    ) -> object | None:
        """Return one profile-private frame for recent-window inference."""

        del observed_at_seconds
        del signals
        surface, _surface_fresh = _current_codex_surface(output_text)
        prompt_snapshot = build_prompt_area_snapshot(surface)
        latest_turn_region_lines = latest_turn_lines(
            surface=surface,
            prompt_index=prompt_snapshot.prompt_index,
        )
        live_edge_lines = latest_turn_live_edge_lines(surface=surface)
        activity = detect_activity(
            latest_turn_lines=latest_turn_region_lines,
            live_edge_lines=live_edge_lines,
            prompt_visible=prompt_snapshot.prompt_visible,
            include_collaboration_cells=self.m_include_collaboration_cells,
        )
        terminal_signal = prompt_adjacent_terminal_signal(latest_turn_region_lines)
        blocking_overlay = has_blocking_overlay(surface)
        ready_posture = ready_posture_state(
            prompt_visible=prompt_snapshot.prompt_visible,
            blocking_overlay=blocking_overlay,
            active_evidence=activity.active_evidence,
        )
        interrupted = is_interrupted_surface(
            latest_turn_lines=latest_turn_region_lines,
            prompt_visible=prompt_snapshot.prompt_visible,
            active_status_row_visible=activity.active_status_row_visible,
        )
        prompt_classification = self.m_prompt_behavior_variant.classify(prompt_snapshot)
        return _CodexTuiFrame(
            prompt_visible=prompt_snapshot.prompt_visible,
            blocking_overlay=blocking_overlay,
            active_status_row_visible=activity.active_status_row_visible,
            compaction_status_visible="compaction_status" in activity.active_reasons,
            active_evidence=activity.active_evidence,
            assistant_response_visible=assistant_response_visible(latest_turn_region_lines),
            current_error_present=terminal_signal is not None,
            interrupted=interrupted,
            ready_posture=ready_posture,
            draft_visible=prompt_classification.kind == "draft",
            latest_turn_region_signature=latest_turn_region_signature(latest_turn_region_lines),
            latest_turn_region_length=len("\n".join(latest_turn_region_lines)),
            latest_turn_region_line_count=len(latest_turn_region_lines),
            completion_docked=any(
                line.strip().startswith(_CODEX_WORKED_PREFIX) for line in latest_turn_region_lines
            ),
            turn_content_visible=assistant_response_visible(latest_turn_region_lines)
            or any(
                _NUMBERED_STREAM_RE.match(line.strip()) is not None
                for line in latest_turn_region_lines
            ),
        )

    def derive_temporal_hints(
        self,
        *,
        recent_frames: Sequence[RecentProfileFrame],
    ) -> TemporalHintSignals:
        """Return recent-window Codex lifecycle hints.

        Dock-aware: hints die once the `Worked for` dock lands in the
        latest-turn region; growth while undocked with turn content counts as
        active (0.162 hides the status row while the final answer streams); a
        status-row blink of about one second or less with no dock carries
        active across the seam. The turn-content gate keeps startup or editing
        redraws from manufacturing activity.
        """

        codex_frames = [item for item in recent_frames if isinstance(item.payload, _CodexTuiFrame)]
        if len(codex_frames) < 2:
            return TemporalHintSignals()

        contiguous_frames = [codex_frames[-1]]
        for frame in reversed(codex_frames[:-1]):
            next_frame = contiguous_frames[0]
            if (
                next_frame.observed_at_seconds - frame.observed_at_seconds
                > _MAX_CONTIGUOUS_GAP_SECONDS
            ):
                break
            contiguous_frames.insert(0, frame)
        if len(contiguous_frames) < 2:
            return TemporalHintSignals()

        newest = contiguous_frames[-1].payload
        if not isinstance(newest, _CodexTuiFrame):
            return TemporalHintSignals()
        newest_at_seconds = contiguous_frames[-1].observed_at_seconds
        if newest.blocking_overlay or newest.current_error_present or newest.interrupted:
            return TemporalHintSignals()
        if newest.completion_docked:
            return TemporalHintSignals()
        if newest.active_status_row_visible:
            return TemporalHintSignals()

        recent_active = next(
            (
                item
                for item in reversed(contiguous_frames[:-1])
                if isinstance(item.payload, _CodexTuiFrame)
                and item.payload.active_status_row_visible
                and not item.payload.completion_docked
            ),
            None,
        )
        if (
            recent_active is not None
            and isinstance(recent_active.payload, _CodexTuiFrame)
            and newest_at_seconds - recent_active.observed_at_seconds
            <= _STATUS_BLINK_CARRY_SECONDS
            and newest.ready_posture == "yes"
            and not newest.draft_visible
        ):
            carry_reasons: tuple[str, ...] = (
                ("compaction_status",)
                if recent_active.payload.compaction_status_visible
                else ("status_row_blink_carry",)
            )
            return TemporalHintSignals(
                active_evidence=True,
                active_reasons=carry_reasons,
                ready_posture="no",
                notes=("temporal_status_blink",),
            )

        if not newest.turn_content_visible:
            return TemporalHintSignals()
        oldest = contiguous_frames[0].payload
        if not isinstance(oldest, _CodexTuiFrame):
            return TemporalHintSignals()
        if oldest.latest_turn_region_signature == newest.latest_turn_region_signature:
            return TemporalHintSignals()
        growth_chars = newest.latest_turn_region_length - oldest.latest_turn_region_length
        growth_lines = newest.latest_turn_region_line_count - oldest.latest_turn_region_line_count
        if growth_chars < _MIN_GROWTH_CHARS and growth_lines < _MIN_ADDED_LINES:
            return TemporalHintSignals()
        hints = TemporalHintSignals(
            active_evidence=True,
            active_reasons=("transcript_growth_undocked",),
            ready_posture="no",
            notes=("temporal_growth_undocked",),
        )
        if LOGGER.isEnabledFor(logging.DEBUG):
            LOGGER.debug(
                "shared_tui_tracking.codex_profile %s",
                json.dumps(
                    {
                        "event": "temporal_hint_emitted",
                        "frame_count": len(contiguous_frames),
                        "growth_chars": growth_chars,
                        "growth_lines": growth_lines,
                        "oldest_signature": oldest.latest_turn_region_signature[:12],
                        "newest_signature": newest.latest_turn_region_signature[:12],
                        "hints": hints.to_payload(),
                    },
                    sort_keys=True,
                    default=str,
                ),
            )
        return hints


def _current_codex_surface(output_text: str | None) -> tuple[SurfaceView, bool]:
    """Return the current Codex surface and whether it belongs to the latest launch."""

    surface = SurfaceView.from_text(output_text or "")
    if surface.has_unrendered_shell_launch(provider_markers=_CODEX_PROVIDER_MARKERS):
        return SurfaceView.from_text(""), False
    return surface, True


def _message_preview(value: str) -> str:
    """Return a bounded single-line preview suitable for diagnostics."""

    normalized = " ".join(value.split())
    if len(normalized) <= _MAX_DEGRADED_MESSAGE_PREVIEW_CHARS:
        return normalized
    return normalized[: _MAX_DEGRADED_MESSAGE_PREVIEW_CHARS - 1].rstrip() + "..."


class CodexTuiSignalDetectorV0_162_X(_BaseCodexTuiSignalDetector):
    """Tracked-TUI detector for observed Codex `0.162.x` surfaces."""

    qualified_through_version = "0.162.1"

    def __init__(self) -> None:
        """Initialize the maintained `0.162.x` detector family."""

        super().__init__(
            detector_version="0.162.x",
            prompt_behavior_variant=CodexPromptBehaviorVariantV0_162_X(),
            include_collaboration_cells=True,
            profile_notes=(
                "source_profile=codex-0.162.x",
                f"qualified_through_version={self.qualified_through_version}",
            ),
        )


CodexTuiSignalDetector = CodexTuiSignalDetectorV0_162_X


CodexTrackedTurnSignalDetector = CodexTuiSignalDetector
