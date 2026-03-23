"""Codex TUI modal overlay detection helpers."""

from __future__ import annotations

import re

from houmao.shared_tui_tracking.surface import SurfaceView


_APPROVAL_TITLES = (
    "Would you like to run the following command?",
    "Would you like to grant these permissions?",
    "Would you like to make the following edits?",
    "needs your approval.",
)
_APPROVAL_FOOTERS = (
    "Press enter to confirm or esc to cancel",
    "or o to open thread",
)
_REQUEST_USER_INPUT_RE = re.compile(r"Question \d+/\d+")
_FIELD_FORM_RE = re.compile(r"Field \d+/\d+")
_APP_LINK_HINTS = (
    "Install on ChatGPT",
    "Use tab / ↑ ↓ to move, enter to select, esc to close",
    "Newly installed apps can take a few minutes to appear in /apps.",
)


def has_blocking_overlay(surface: SurfaceView) -> bool:
    """Return whether one Codex modal/operator overlay is visible."""

    stripped_text = "\n".join(surface.stripped_lines)
    if any(title in stripped_text for title in _APPROVAL_TITLES) and any(
        footer in stripped_text for footer in _APPROVAL_FOOTERS
    ):
        return True
    if _REQUEST_USER_INPUT_RE.search(stripped_text) and (
        "enter to submit answer" in stripped_text
        or "enter to submit all" in stripped_text
        or "Press enter to confirm or esc to go back" in stripped_text
    ):
        return True
    if _FIELD_FORM_RE.search(stripped_text) and "enter to submit | esc to cancel" in stripped_text:
        return True
    if any(hint in stripped_text for hint in _APP_LINK_HINTS):
        return True
    return False
