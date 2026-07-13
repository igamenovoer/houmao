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
_LIST_SELECTION_FOOTER = "Press enter to confirm or esc to go back"
_LIST_SELECTION_TITLES = (
    "Select Model and Effort",
    "Select Reasoning Effort",
    "Select Personality",
    "Select Approval Mode",
)
_LIST_SELECTION_ROW_RE = re.compile(r"(?m)^\s*›\s+\d+\.\s+.+$")


def has_blocking_overlay(surface: SurfaceView) -> bool:
    """Return whether one Codex modal/operator overlay is visible."""

    stripped_text = "\n".join(surface.stripped_lines)
    live_edge_text = "\n".join(line for line in surface.stripped_lines[-28:] if line.strip())
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
    if _LIST_SELECTION_FOOTER in live_edge_text and (
        any(title in live_edge_text for title in _LIST_SELECTION_TITLES)
        or _LIST_SELECTION_ROW_RE.search(live_edge_text) is not None
    ):
        return True
    return False
