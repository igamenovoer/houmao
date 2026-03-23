"""Codex TUI prompt and ready-posture helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass

from houmao.shared_tui_tracking.models import Tristate
from houmao.shared_tui_tracking.surface import SurfaceView


_CODEX_PROMPT_RE = re.compile(r"^\s*›(.*)$")
_CODEX_DIM_SGR_RE = re.compile(r"\x1b\[(?:0;)?2m")
_CODEX_PLACEHOLDER_TEXTS = frozenset(
    {
        "Ask Codex to do anything",
        "Explain this codebase",
        "Summarize recent commits",
        "Implement {feature}",
        "Find and fix a bug in @filename",
        "Write tests for @filename",
        "Improve documentation in @filename",
        "Run /review on my current changes",
        "Use /skills to list available skills",
    }
)


@dataclass(frozen=True)
class CodexPromptContext:
    """Current prompt and latest-turn context for one Codex surface."""

    prompt_index: int | None
    prompt_visible: bool
    prompt_text: str | None
    latest_turn_lines: tuple[str, ...]


def build_prompt_context(surface: SurfaceView) -> CodexPromptContext:
    """Return current prompt metadata and a bounded latest-turn text region."""

    prompt_index: int | None = None
    prompt_text: str | None = None
    for index, (raw_line, line) in enumerate(
        zip(surface.raw_lines, surface.stripped_lines, strict=True)
    ):
        match = _CODEX_PROMPT_RE.match(line)
        if match is not None:
            prompt_index = index
            prompt_text = _normalize_prompt_text(
                prompt_text=match.group(1).strip() or None,
                raw_line=raw_line,
            )

    non_empty_lines = [line.strip() for line in surface.stripped_lines if line.strip()]
    if prompt_index is None:
        latest_turn_lines = tuple(non_empty_lines[-24:])
    else:
        start_index = max(prompt_index - 24, 0)
        latest_turn_lines = tuple(
            line.strip()
            for line in surface.stripped_lines[start_index:prompt_index]
            if line.strip()
        )

    return CodexPromptContext(
        prompt_index=prompt_index,
        prompt_visible=prompt_index is not None,
        prompt_text=prompt_text,
        latest_turn_lines=latest_turn_lines,
    )


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
    prompt_text: str | None,
) -> Tristate:
    """Return the editing-input tristate for one Codex surface."""

    if prompt_visible and prompt_text:
        return "yes"
    if prompt_visible:
        return "no"
    return "unknown"


def _normalize_prompt_text(*, prompt_text: str | None, raw_line: str) -> str | None:
    """Treat dim-rendered Codex placeholders as empty draft input."""

    if prompt_text is None:
        return None
    if prompt_text not in _CODEX_PLACEHOLDER_TEXTS:
        return prompt_text
    if _CODEX_DIM_SGR_RE.search(raw_line) is None:
        return prompt_text
    return None


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
