"""Codex TUI generic error-cell helpers."""

from __future__ import annotations

import re


_CODEX_ERROR_CELL_RE = re.compile(r"^\s*■ .+")


def latest_error_cell(latest_turn_lines: tuple[str, ...]) -> str | None:
    """Return the latest relevant generic error-cell line if present."""

    for line in reversed(latest_turn_lines):
        if _CODEX_ERROR_CELL_RE.match(line) is not None:
            return line.strip()
    return None
