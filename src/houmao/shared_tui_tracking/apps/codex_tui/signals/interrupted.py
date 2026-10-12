"""Codex TUI interruption detection helpers."""

from __future__ import annotations

import re
from collections.abc import Sequence


# Codex 0.162.x renders the interruption notice as
# `■ Conversation interrupted - use /feedback if something went wrong`
# (extern/orphan/codex codex-rs/tui/src/chatwidget/input_restore.rs). The needle
# is the whitespace-normalized, case-insensitive `Conversation interrupted`
# prefix so suffix rewording does not silently break detection.
CODEX_INTERRUPTED_PREFIX = "conversation interrupted"
_WHITESPACE_RE = re.compile(r"\s+")


def _normalize_wrapped_text(value: str) -> str:
    """Return one whitespace-normalized, case-folded surface string."""

    return _WHITESPACE_RE.sub(" ", value).strip().lower()


def interrupted_text_visible_in_lines(*, lines: Sequence[str]) -> bool:
    """Return whether the interruption notice prefix shows in one scoped region."""

    return CODEX_INTERRUPTED_PREFIX in _normalize_wrapped_text("\n".join(lines))


def is_interrupted_surface(
    *,
    latest_turn_lines: Sequence[str],
    prompt_visible: bool,
    active_status_row_visible: bool,
) -> bool:
    """Return whether the current Codex surface matches the interruption rule.

    The notice counts only with an idle live edge: while a status row shows a
    turn still running, a visible notice is stale scrollback and does not mark
    the surface interrupted.
    """

    return (
        interrupted_text_visible_in_lines(lines=latest_turn_lines)
        and prompt_visible
        and not active_status_row_visible
    )
