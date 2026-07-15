"""UC-03 prompt-admission classification test utilities."""

from __future__ import annotations

from enum import Enum


class Uc03ReadinessLabel(str, Enum):
    """Independent behavioral ground-truth labels used by UC-03.

    See ``context/features/2026-07-11-tui-state-tracking-test-plan/usecases/
    uc-03-qualify-prompt-admission-readiness.md`` for definitions.
    """

    READY_IMMEDIATE = "ready_immediate"
    BUSY_ACTIVE = "busy_active"
    BUSY_DRAFT = "busy_draft"
    BUSY_OVERLAY = "busy_overlay"
    INDETERMINATE = "indeterminate"


def map_public_state_to_uc03_label(
    turn_phase: str | None,
    surface_ready_posture: str | None,
    surface_editing_input: str | None,
    surface_accepting_input: str | None,
    diagnostics_availability: str | None,
    active_reasons: list[str] | None,
    ambiguous_interactive_surface: bool = False,
) -> Uc03ReadinessLabel:
    """Map a public tracked-state sample to a UC-03 readiness label.

    The mapping follows UC-03's independent behavioral ground truth:

    - ``ready_immediate``: the provider surface is empty, stable, and able to
      start a new independent turn immediately.
    - ``busy_active``: the provider is currently processing a turn.
    - ``busy_draft``: a user-authored draft is present in the prompt editor.
    - ``busy_overlay``: a non-submit-ready overlay (slash menu, selector, etc.)
      is visible.
    - ``indeterminate``: evidence is missing or ambiguous.

    Parameters
    ----------
    turn_phase
        Tracker ``turn.phase`` value.
    surface_ready_posture
        Tracker ``surface.ready_posture`` value.
    surface_editing_input
        Tracker ``surface.editing_input`` value.
    surface_accepting_input
        Tracker ``surface.accepting_input`` value.
    diagnostics_availability
        Tracker ``diagnostics.availability`` value.
    active_reasons
        Tracker ``active_reasons`` list.
    ambiguous_interactive_surface
        Explicit detector evidence that a selector, menu, or approval surface is visible.

    Returns
    -------
    Uc03ReadinessLabel
        The UC-03 readiness label for the sample.
    """
    active_reasons = active_reasons or []

    # Diagnostics take precedence over visible rows retained in a dead or missing pane.
    if diagnostics_availability not in ("available", None):
        return Uc03ReadinessLabel.INDETERMINATE

    if turn_phase is None or surface_ready_posture is None:
        return Uc03ReadinessLabel.INDETERMINATE

    # Active processing takes precedence over draft/overlay classification.
    if turn_phase == "active" or active_reasons:
        return Uc03ReadinessLabel.BUSY_ACTIVE

    # A visible draft means the editor is occupied.
    if surface_editing_input == "yes":
        return Uc03ReadinessLabel.BUSY_DRAFT

    # Overlay classification requires affirmative detector evidence. Unknown readiness
    # alone does not identify what kind of surface is blocking prompt admission.
    if ambiguous_interactive_surface:
        return Uc03ReadinessLabel.BUSY_OVERLAY

    if surface_ready_posture == "unknown" or surface_accepting_input in ("no", "unknown"):
        return Uc03ReadinessLabel.INDETERMINATE

    if (
        turn_phase == "ready"
        and surface_ready_posture == "yes"
        and surface_editing_input in ("no", None)
        and surface_accepting_input == "yes"
    ):
        return Uc03ReadinessLabel.READY_IMMEDIATE

    return Uc03ReadinessLabel.INDETERMINATE
