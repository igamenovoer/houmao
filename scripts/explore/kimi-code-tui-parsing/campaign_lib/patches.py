"""Candidate kimi-code 2.1.x detector applied by monkey patch.

The campaign's no-product-change declaration keeps ``src/houmao/`` read-only,
so the proposed 2.1.x repairs live here and are applied at replay time by
patching three seams:

1. ``DetectorProfileRegistry.default`` — registers the candidate detector for
   kimi_code versions [2.1.0, 2.2.0) so ``resolve(observed_version="2.1.1")``
   selects it (the selector picks the compatible registration with the
   greatest minimum version).
2. ``houmao.terminal_record.service._parse_kimi_snapshot_payload`` — extends
   the recorder analyze parser mapping with the trust startup modal, the
   AskUserQuestion dialog, and the goal-start prompt.
3. ``houmao.server.tui.parser._kimi_startup_modal_visible`` — adds the 2.1
   trust dialog needle for the live server parser path.

Repairs relative to the shared 0.11-era base behavior:

- Activity labels: kimi 2.1 renders ``Thinking…`` / ``Working…`` capitalized
  with U+2026; the base ``ACTIVITY_LABEL_RE`` (lowercase, ASCII dots) matches
  nothing, so braille-frame phases are invisible. The candidate rescan accepts
  both spellings plus ``Retrying (N/M)``, ``Compacting context…``, and
  ``Orchestrating…`` live-edge lines.
- Compaction renders a ``●`` bullet, not a spinner frame; the candidate
  detects it as text.
- AskUserQuestion (`` question`` title + ``[N]`` options) and the goal-start
  prompt (``Approve CreateGoal?``) are modal surfaces: they force
  ``ambiguous_interactive_surface`` and non-ready/non-accepting posture.
- ``accepting_input`` follows the labeling rubric: a visible composer accepts
  typing even while a turn is active (the TUI queues the submission), so only
  modal surfaces close acceptance.
"""

from __future__ import annotations

import dataclasses
import re
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from houmao.shared_tui_tracking.apps.kimi_code.profile import (
    BRAILLE_SPINNER_FRAMES,
    MOON_SPINNER_FRAMES,
    _BaseKimiCodeSignalDetector,
)
from houmao.shared_tui_tracking.models import DetectedTurnSignals, ParsedSurfaceContext
from houmao.shared_tui_tracking.registry import (
    DetectorProfileRegistration,
    DetectorProfileRegistry,
)
from houmao.shared_tui_tracking.surface import SurfaceView

CANDIDATE_DETECTOR_VERSION = "2.1.x-candidate"

_ACTIVITY_LABEL_2_1_RE = re.compile(
    r"(?:working|thinking)(?:\.\.\.|…)|Retrying \(\d+/\d+\)|Compacting context…|Orchestrating…",
    re.IGNORECASE,
)
_COMPACTION_RE = re.compile(r"●\s*Compacting context…")
_QUESTION_TITLE_RE = re.compile(r"^\s*question\s*$", re.IGNORECASE | re.MULTILINE)
_QUESTION_OPTION_RE = re.compile(r"^\s*\[\d+\]", re.MULTILINE)
_GOAL_PROMPT_NEEDLE = "Approve CreateGoal?"
_TRUST_MODAL_NEEDLE = "trust this folder"
_ACTIVITY_WINDOW_LINES_2_1 = 12


class KimiCodeSignalDetectorV2_1_XCandidate(_BaseKimiCodeSignalDetector):
    """Candidate detector for observed kimi-code 2.1.x surfaces."""

    def __init__(self) -> None:
        """Initialize the candidate with the 0.34+ profile's pacing."""

        super().__init__(
            detector_version=CANDIDATE_DETECTOR_VERSION,
            activity_window_lines=4,
            temporal_window_seconds=0.0,
            enable_temporal_growth=False,
            profile_notes=("source_profile=kimi-code-2.1.x-candidate",),
        )

    def detect(
        self,
        *,
        output_text: str | None,
        parsed_surface: ParsedSurfaceContext | None = None,
    ) -> DetectedTurnSignals:
        """Return base signals repaired for kimi-code 2.1.x surfaces."""

        base = super().detect(output_text=output_text, parsed_surface=parsed_surface)
        # Detector semantics operate on the stripped surface (SurfaceView); raw
        # escapes would break dialog and bullet matching.
        stripped_text = "\n".join(SurfaceView.from_text(output_text or "").stripped_lines)
        live_lines = _live_edge_lines(output_text or "")

        reasons = list(base.active_reasons)
        active = base.active_evidence
        spinner_hits = _spinner_activity_2_1(live_lines)
        if spinner_hits and "activity_2_1_label" not in reasons:
            reasons.append("activity_2_1_label")
            active = True
        if any(_COMPACTION_RE.search(line) for line in live_lines):
            if "compaction" not in reasons:
                reasons.append("compaction")
            active = True

        question_dialog = _question_dialog_present(stripped_text)
        goal_prompt = _GOAL_PROMPT_NEEDLE in stripped_text
        modal = base.ambiguous_interactive_surface or question_dialog or goal_prompt
        if question_dialog:
            reasons.append("question_dialog")
        if goal_prompt:
            reasons.append("goal_start_prompt")

        # Interrupt notices persist in scrollback while later turns run; only a
        # notice with no concurrent activity marks an interrupted surface.
        interrupted = base.interrupted and not active
        active_evidence = active and not interrupted
        prompt_visible = base.prompt_visible
        prompt_empty = not (base.prompt_text or "").strip()

        if modal:
            accepting_input = "no"
            ready_posture = "no"
        else:
            accepting_input = "yes" if prompt_visible else "unknown"
            ready_posture = "no" if active_evidence else ("yes" if prompt_visible else "unknown")

        notes = list(base.notes)
        for note, flag in (
            ("question_dialog_visible", question_dialog),
            ("goal_start_prompt_visible", goal_prompt),
        ):
            if flag:
                notes.append(note)

        return dataclasses.replace(
            base,
            accepting_input=accepting_input,
            ready_posture=ready_posture,
            active_evidence=active_evidence,
            active_reasons=tuple(dict.fromkeys(reasons)),
            interrupted=interrupted,
            ambiguous_interactive_surface=modal,
            success_candidate=bool(
                prompt_visible and ready_posture == "yes" and prompt_empty and not interrupted
            ),
            success_blocked=bool(active_evidence or modal or interrupted),
            notes=tuple(dict.fromkeys(notes)),
        )


@contextmanager
def kimi_2_1_x_patch() -> Iterator[None]:
    """Apply the candidate detector and parser patches for one replay."""

    import houmao.server.tui.parser as server_parser
    import houmao.terminal_record.service as record_service

    original_default = DetectorProfileRegistry.__dict__["default"].__func__
    original_payload_parser = record_service._parse_kimi_snapshot_payload
    original_startup_modal = server_parser._kimi_startup_modal_visible

    def patched_default(cls: type[DetectorProfileRegistry]) -> DetectorProfileRegistry:
        """Return the default registry plus the 2.1.x candidate registration."""

        registry = original_default(cls)
        registrations = list(registry.m_registrations)
        candidate = DetectorProfileRegistration(
            app_id="kimi_code",
            detector_name="kimi_code",
            detector_version=CANDIDATE_DETECTOR_VERSION,
            minimum_supported_version=(2, 1, 0),
            maximum_supported_version=(2, 2, 0),
            profile_factory=KimiCodeSignalDetectorV2_1_XCandidate,
        )
        fallback_index = next(
            index
            for index, item in enumerate(registrations)
            if item.app_id == "kimi_code" and item.minimum_supported_version is None
        )
        registrations.insert(fallback_index, candidate)
        return DetectorProfileRegistry(registrations=tuple(registrations))

    def patched_payload_parser(snapshot: Any) -> dict[str, Any]:
        """Extend the recorder kimi parser mapping with 2.1 modal surfaces."""

        payload = original_payload_parser(snapshot)
        text = "\n".join(SurfaceView.from_text(snapshot.output_text or "").stripped_lines)
        if payload["business_state"] in {"unknown", "idle"}:
            if _TRUST_MODAL_NEEDLE in text.lower():
                payload.update(
                    business_state="awaiting_operator",
                    input_mode="modal",
                    ui_context="startup_modal",
                )
            elif _question_dialog_present(text):
                payload.update(
                    business_state="awaiting_operator",
                    input_mode="modal",
                    ui_context="question_dialog",
                )
            elif _GOAL_PROMPT_NEEDLE in text:
                payload.update(
                    business_state="awaiting_operator",
                    input_mode="modal",
                    ui_context="goal_start_prompt",
                )
        return payload

    def patched_startup_modal(normalized_text: str) -> bool:
        """Add the 2.1 trust dialog to the server parser's startup needles."""

        return original_startup_modal(normalized_text) or (
            _TRUST_MODAL_NEEDLE in normalized_text.lower()
        )

    DetectorProfileRegistry.default = classmethod(patched_default)  # type: ignore[assignment]
    record_service._parse_kimi_snapshot_payload = patched_payload_parser
    server_parser._kimi_startup_modal_visible = patched_startup_modal
    try:
        yield
    finally:
        DetectorProfileRegistry.default = classmethod(original_default)  # type: ignore[assignment]
        record_service._parse_kimi_snapshot_payload = original_payload_parser
        server_parser._kimi_startup_modal_visible = original_startup_modal


def _live_edge_lines(text: str) -> list[str]:
    """Return the trailing non-empty stripped lines of one surface."""

    lines = [line.strip() for line in SurfaceView.from_text(text).stripped_lines if line.strip()]
    return lines[-_ACTIVITY_WINDOW_LINES_2_1:]


def _spinner_activity_2_1(live_lines: list[str]) -> list[str]:
    """Return 2.1-aware spinner-activity hits over live-edge lines."""

    hits: list[str] = []
    for line in live_lines:
        if "context:" in line.lower():
            continue
        if line.startswith(BRAILLE_SPINNER_FRAMES):
            if _ACTIVITY_LABEL_2_1_RE.search(line) is not None:
                hits.append(line)
        elif line.startswith(MOON_SPINNER_FRAMES):
            hits.append(line)
    return hits


def _question_dialog_present(text: str) -> bool:
    """Return whether the AskUserQuestion dialog surface is visible."""

    return _QUESTION_TITLE_RE.search(text) is not None and (
        _QUESTION_OPTION_RE.search(text) is not None or "esc cancel" in text.lower()
    )
