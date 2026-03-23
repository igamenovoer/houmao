"""Fallback tracker profile for unsupported or unknown tools."""

from __future__ import annotations

import hashlib

from houmao.shared_tui_tracking.detectors import BaseTrackedTurnSignalDetector
from houmao.shared_tui_tracking.models import DetectedTurnSignals, ParsedSurfaceContext, Tristate


class FallbackTrackedTurnSignalDetector(BaseTrackedTurnSignalDetector):
    """Conservative detector for unsupported or unknown tools."""

    def detect(
        self,
        *,
        output_text: str | None,
        parsed_surface: ParsedSurfaceContext | None = None,
    ) -> DetectedTurnSignals:
        """Return normalized tracked signals for one unsupported surface."""

        del parsed_surface
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
