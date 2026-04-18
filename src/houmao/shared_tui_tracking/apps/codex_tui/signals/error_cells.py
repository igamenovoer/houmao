"""Codex TUI generic error-cell helpers."""

from __future__ import annotations

import re


_CODEX_ERROR_CELL_RE = re.compile(r"^\s*■ .+")
_PROMPT_LINE_RE = re.compile(r"^\s*›")
_MAX_PROMPT_ADJACENT_ERROR_CONTINUATION_LINES = 4
_DEGRADED_COMPACT_RE = re.compile(
    r"\b(remote\s+compact|compact\s+task|compact(?:ion)?\b.*"
    r"(?:fail|error|disconnect|server|stream)|(?:server|stream|remote)\b.*\bcompact)\b",
    re.IGNORECASE,
)
DEGRADED_CHAT_CONTEXT_NOTE = "chat_context=degraded"


def latest_error_cell(latest_turn_lines: tuple[str, ...]) -> str | None:
    """Return the latest relevant generic error-cell line if present."""

    for line in reversed(latest_turn_lines):
        if _CODEX_ERROR_CELL_RE.match(line) is not None:
            return line.strip()
    return None


def prompt_adjacent_error_cell(latest_turn_lines: tuple[str, ...]) -> str | None:
    """Return a red error cell directly adjacent to the current prompt edge."""

    continuation_lines = 0
    for raw_line in reversed(latest_turn_lines):
        line = raw_line.strip()
        if not line:
            continue
        if _CODEX_ERROR_CELL_RE.match(line) is not None:
            return line
        if not _can_belong_to_prompt_adjacent_error_block(line):
            return None
        continuation_lines += 1
        if continuation_lines > _MAX_PROMPT_ADJACENT_ERROR_CONTINUATION_LINES:
            return None
    return None


def is_degraded_error_cell(error_line: str | None) -> bool:
    """Return whether a prompt-adjacent error marks recoverable degraded context."""

    if error_line is None:
        return False
    return _DEGRADED_COMPACT_RE.search(error_line) is not None


def _can_belong_to_prompt_adjacent_error_block(line: str) -> bool:
    """Return whether one line can be wrapped text from a prompt-edge error."""

    if _PROMPT_LINE_RE.match(line) is not None:
        return False
    if line.startswith(("•", "⚠", "╭", "│", "╰")):
        return False
    if line.startswith("Tip:") or line.startswith("model:"):
        return False
    return True
