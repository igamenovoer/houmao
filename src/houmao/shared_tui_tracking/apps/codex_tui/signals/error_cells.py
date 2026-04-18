"""Codex TUI generic error-cell helpers."""

from __future__ import annotations

import re


_CODEX_ERROR_CELL_RE = re.compile(r"^\s*■ .+")
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


def is_degraded_error_cell(error_line: str | None) -> bool:
    """Return whether a prompt-adjacent error marks recoverable degraded context."""

    if error_line is None:
        return False
    return _DEGRADED_COMPACT_RE.search(error_line) is not None
