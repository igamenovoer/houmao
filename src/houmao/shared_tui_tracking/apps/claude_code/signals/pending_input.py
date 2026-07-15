"""Claude pending-input detection from the bounded composer structure."""

from __future__ import annotations

import re

from houmao.shared_tui_tracking.apps.claude_code.signals.prompt_behavior import (
    PromptAreaSnapshot,
    payload_uses_ghost_render_style,
)
from houmao.shared_tui_tracking.models import Tristate
from houmao.shared_tui_tracking.surface import SurfaceView


_PROMPT_RE = re.compile(r"^(?P<indent>\s*)❯(?P<payload>.*)$")


def pending_input_state(
    *,
    surface: SurfaceView,
    composer: PromptAreaSnapshot,
) -> Tristate:
    """Return whether Claude renders a submitted instruction behind the active turn.

    A positive match requires the complete bottom composer frame and a non-empty,
    indented, semantically styled user cell directly above its upper rule.  This
    deliberately ignores composer suggestion wording.  Cropped or prompt-like but
    unclassifiable structures stay unknown.
    """

    composer_index = composer.prompt_index
    if composer_index is None:
        return "unknown"
    if composer_index < 2 or composer_index + 1 >= len(surface.stripped_lines):
        return "unknown"
    if not _is_composer_rule(surface.stripped_lines[composer_index - 1]):
        return "unknown"
    if not _is_composer_rule(surface.stripped_lines[composer_index + 1]):
        return "unknown"

    candidate_end_index = composer_index - 2
    if not surface.stripped_lines[candidate_end_index].strip():
        candidate_end_index -= 1
        if candidate_end_index < 0 or not surface.stripped_lines[candidate_end_index].strip():
            return "no"

    region_start_index = max(0, candidate_end_index - 7)
    candidate_index: int | None = None
    candidate_match: re.Match[str] | None = None
    for index in range(candidate_end_index, region_start_index - 1, -1):
        line = surface.stripped_lines[index]
        if not line.strip():
            break
        match = _PROMPT_RE.match(line)
        if match is not None:
            candidate_index = index
            candidate_match = match
            break
        if _is_intervening_cell(line):
            return "no"
    if candidate_index is None or candidate_match is None:
        immediate_line = surface.stripped_lines[candidate_end_index]
        return "unknown" if len(immediate_line) - len(immediate_line.lstrip()) >= 2 else "no"
    if len(candidate_match.group("indent")) < 2:
        return "unknown"

    if any(
        _is_intervening_cell(line)
        for line in surface.stripped_lines[candidate_index + 1 : candidate_end_index + 1]
    ):
        return "no"

    payload = candidate_match.group("payload").strip()
    if not payload:
        return "unknown"
    candidate_line = surface.stripped_lines[candidate_index]
    candidate = PromptAreaSnapshot(
        prompt_visible=True,
        prompt_index=candidate_index,
        raw_prompt_line=surface.raw_lines[candidate_index],
        stripped_prompt_line=candidate_line,
        payload_text=payload,
        raw_prompt_region_lines=(surface.raw_lines[candidate_index],),
        stripped_prompt_region_lines=(candidate_line,),
    )
    ghost_style = payload_uses_ghost_render_style(candidate)
    if ghost_style is None:
        return "unknown"
    return "yes" if ghost_style else "unknown"


def _is_composer_rule(line: str) -> bool:
    """Return whether one line is a complete Claude composer boundary."""

    stripped = line.strip()
    return len(stripped) >= 8 and set(stripped) == {"─"}


def _is_intervening_cell(line: str) -> bool:
    """Return whether a line is provider output rather than queued-row wrapping."""

    stripped = line.strip()
    return stripped.startswith(("●", "⎿", "✢", "✻", "✽", "✶", "·", "*")) or stripped.startswith(
        ("Bash(", "Read(", "Write(", "Edit(", "Task(")
    )
