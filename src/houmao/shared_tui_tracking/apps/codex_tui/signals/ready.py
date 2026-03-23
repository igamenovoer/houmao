"""Codex TUI prompt and ready-posture helpers."""

from __future__ import annotations

from houmao.shared_tui_tracking.models import Tristate
from houmao.shared_tui_tracking.apps.codex_tui.signals.prompt_behavior import PromptClassification


def accepting_input_state(
    *,
    prompt_visible: bool,
    blocking_overlay: bool,
) -> Tristate:
    """Return the accepting-input tristate for one Codex surface."""

    if blocking_overlay:
        return "no"
    if prompt_visible:
        return "yes"
    return "unknown"


def editing_input_state(
    *,
    prompt_visible: bool,
    prompt_classification: PromptClassification,
) -> Tristate:
    """Return the editing-input tristate for one Codex surface."""

    if not prompt_visible:
        return "unknown"
    if prompt_classification.kind == "draft":
        return "yes"
    if prompt_classification.kind in {"placeholder", "empty"}:
        return "no"
    return "unknown"


def ready_posture_state(
    *,
    prompt_visible: bool,
    blocking_overlay: bool,
    active_evidence: bool,
) -> Tristate:
    """Return the ready-posture tristate for one Codex surface."""

    if blocking_overlay and not active_evidence:
        return "unknown"
    if active_evidence:
        return "no"
    if prompt_visible:
        return "yes"
    return "unknown"
