"""Codex TUI tracked-TUI detector profiles with temporal inference."""

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Sequence
from dataclasses import dataclass

from houmao.shared_tui_tracking.apps.codex_tui.signals.activity import (
    detect_activity,
    latest_turn_region_signature,
)
from houmao.shared_tui_tracking.apps.codex_tui.signals.error_cells import (
    DEGRADED_CHAT_CONTEXT_NOTE,
    KNOWN_FAILURE_NOTE,
    prompt_adjacent_terminal_signal,
)
from houmao.shared_tui_tracking.apps.codex_tui.signals.interrupted import (
    CODEX_STEER_INTERRUPTION_TEXT,
    is_interrupted_surface,
)
from houmao.shared_tui_tracking.apps.codex_tui.signals.overlays import has_blocking_overlay
from houmao.shared_tui_tracking.apps.codex_tui.signals.prompt_behavior import (
    CodexPromptBehaviorVariant,
    CodexPromptBehaviorVariantV0_116_X,
    FallbackCodexPromptBehaviorVariant,
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
    DetectedTurnSignals,
    ParsedSurfaceContext,
    RecentProfileFrame,
    TemporalHintSignals,
)
from houmao.shared_tui_tracking.surface import SurfaceView


_CODEX_WORKED_PREFIX = "─ Worked for "
_TEMPORAL_WINDOW_SECONDS = 3.0
_MAX_CONTIGUOUS_GAP_SECONDS = 2.0
_MIN_GROWTH_CHARS = 48
_MIN_ADDED_LINES = 2
LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class _CodexTuiFrame:
    """Profile-private Codex frame stored inside the recent temporal window."""

    prompt_visible: bool
    blocking_overlay: bool
    active_status_row_visible: bool
    current_error_present: bool
    interrupted: bool
    ready_posture: str
    latest_turn_region_signature: str
    latest_turn_region_length: int
    latest_turn_region_line_count: int


class _BaseCodexTuiSignalDetector(BaseTrackedTurnSignalDetector):
    """Tracked-TUI detector for one Codex version family."""

    def __init__(
        self,
        *,
        detector_version: str,
        prompt_behavior_variant: CodexPromptBehaviorVariant,
        profile_notes: tuple[str, ...] = (),
    ) -> None:
        """Initialize one Codex detector profile."""

        self.m_detector_version: str = detector_version
        self.m_prompt_behavior_variant: CodexPromptBehaviorVariant = prompt_behavior_variant
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
        surface = SurfaceView.from_text(output_text or "")
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
            steer_interruption_text=CODEX_STEER_INTERRUPTION_TEXT,
        )
        interrupted = is_interrupted_surface(
            latest_turn_lines=latest_turn_region_lines,
            prompt_visible=prompt_snapshot.prompt_visible,
            active_status_row_visible=activity.active_status_row_visible,
        )
        terminal_signal = prompt_adjacent_terminal_signal(latest_turn_region_lines)
        current_error_present = terminal_signal is not None
        degraded_context = (
            terminal_signal.degraded_context if terminal_signal is not None else False
        )
        known_failure = (
            terminal_signal.known_failure
            if terminal_signal is not None and not terminal_signal.degraded_context
            else False
        )
        ready_posture = ready_posture_state(
            prompt_visible=prompt_snapshot.prompt_visible,
            blocking_overlay=blocking_overlay,
            active_evidence=activity.active_evidence,
        )
        accepting_input = accepting_input_state(
            prompt_visible=prompt_snapshot.prompt_visible,
            blocking_overlay=blocking_overlay,
        )
        editing_input = editing_input_state(
            prompt_visible=prompt_snapshot.prompt_visible,
            prompt_classification=prompt_classification,
        )
        completion_marker = next(
            (
                line
                for line in reversed(latest_turn_region_lines)
                if line.strip().startswith(_CODEX_WORKED_PREFIX)
            ),
            None,
        )
        success_candidate = bool(
            prompt_snapshot.prompt_visible
            and ready_posture == "yes"
            and not activity.active_evidence
            and not current_error_present
            and not interrupted
            and not known_failure
            and not blocking_overlay
            and prompt_classification.kind in {"empty", "placeholder"}
        )
        notes: list[str] = [
            *self.m_profile_notes,
            *prompt_behavior_notes(
                variant=self.m_prompt_behavior_variant,
                classification=prompt_classification,
            ),
        ]
        if activity.steer_handoff:
            notes.append("steer_handoff_active")
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
        if activity.active_evidence:
            notes.append("active_turn_detected")
        if completion_marker is not None:
            notes.append("completion_marker_visible")

        stripped_text = "\n".join(surface.stripped_lines)
        surface_signature = hashlib.sha256(stripped_text.encode("utf-8")).hexdigest()
        success_blocked = bool(
            current_error_present
            or known_failure
            or blocking_overlay
            or activity.active_evidence
            or interrupted
        )
        return DetectedTurnSignals(
            detector_name="codex_tui",
            detector_version=self.detector_version,
            accepting_input=accepting_input,
            editing_input=editing_input,
            ready_posture=ready_posture,
            prompt_visible=prompt_snapshot.prompt_visible,
            prompt_text=prompt_classification.prompt_text,
            footer_interruptable=activity.active_status_row_visible,
            active_evidence=activity.active_evidence,
            active_reasons=activity.active_reasons,
            interrupted=interrupted,
            known_failure=known_failure,
            current_error_present=current_error_present,
            success_candidate=success_candidate,
            completion_marker=completion_marker,
            latest_status_line=activity.latest_status_line,
            ambiguous_interactive_surface=blocking_overlay,
            success_blocked=success_blocked,
            surface_signature=surface_signature,
            notes=tuple(notes),
            chat_context="degraded" if degraded_context else "current",
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
        surface = SurfaceView.from_text(output_text or "")
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
            steer_interruption_text=CODEX_STEER_INTERRUPTION_TEXT,
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
        return _CodexTuiFrame(
            prompt_visible=prompt_snapshot.prompt_visible,
            blocking_overlay=blocking_overlay,
            active_status_row_visible=activity.active_status_row_visible,
            current_error_present=terminal_signal is not None,
            interrupted=interrupted,
            ready_posture=ready_posture,
            latest_turn_region_signature=latest_turn_region_signature(latest_turn_region_lines),
            latest_turn_region_length=len("\n".join(latest_turn_region_lines)),
            latest_turn_region_line_count=len(latest_turn_region_lines),
        )

    def derive_temporal_hints(
        self,
        *,
        recent_frames: Sequence[RecentProfileFrame],
    ) -> TemporalHintSignals:
        """Return recent-window Codex lifecycle hints."""

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

        oldest = contiguous_frames[0].payload
        newest = contiguous_frames[-1].payload
        if not isinstance(oldest, _CodexTuiFrame) or not isinstance(newest, _CodexTuiFrame):
            return TemporalHintSignals()
        if newest.blocking_overlay or newest.current_error_present or newest.interrupted:
            return TemporalHintSignals()
        if newest.active_status_row_visible:
            return TemporalHintSignals()
        growth_chars = newest.latest_turn_region_length - oldest.latest_turn_region_length
        growth_lines = newest.latest_turn_region_line_count - oldest.latest_turn_region_line_count
        if newest.latest_turn_region_signature == oldest.latest_turn_region_signature:
            return TemporalHintSignals()
        if growth_chars < _MIN_GROWTH_CHARS and growth_lines < _MIN_ADDED_LINES:
            return TemporalHintSignals()
        hints = TemporalHintSignals(
            active_evidence=True,
            active_reasons=("transcript_growth",),
            ready_posture="no",
            notes=("temporal_transcript_growth",),
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


class CodexTuiSignalDetectorV0_116_X(_BaseCodexTuiSignalDetector):
    """Tracked-TUI detector for observed Codex `0.116.x` surfaces."""

    def __init__(self) -> None:
        """Initialize the `0.116.x` detector family."""

        super().__init__(
            detector_version="0.116.x",
            prompt_behavior_variant=CodexPromptBehaviorVariantV0_116_X(),
        )


class FallbackCodexTuiSignalDetector(_BaseCodexTuiSignalDetector):
    """Conservative tracked-TUI detector for unmatched Codex versions."""

    def __init__(self) -> None:
        """Initialize the fallback Codex detector family."""

        super().__init__(
            detector_version="fallback",
            prompt_behavior_variant=FallbackCodexPromptBehaviorVariant(),
            profile_notes=("fallback_detector",),
        )


CodexTuiSignalDetector = CodexTuiSignalDetectorV0_116_X


CodexTrackedTurnSignalDetector = CodexTuiSignalDetector
