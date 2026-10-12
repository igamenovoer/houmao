"""Codex TUI modal overlay detection helpers.

Needle provenance: codex 0.162.x source (`extern/orphan/codex`, codex-rs/tui).
Every needle is bounded structure plus essential semantic tokens rather than
an exact full-sentence literal, so minor upstream rewording does not silently
break detection. Capture-unverified surfaces (edits-form approval,
permissions-grant, send-input dialog) ship source-backed and marked
qualification-pending.
"""

from __future__ import annotations

import re

from houmao.shared_tui_tracking.surface import SurfaceView


# Approval modals (bottom_pane/approval_overlay.rs): titles and the
# confirm/cancel footer survive in 0.162.x. The edits-form and
# permissions-grant variants are qualification-pending (never captured live).
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
# Send-input-to-terminal dialog (approval_overlay.rs): `Would you like to send
# input to terminal <pid>?` / `... to the existing terminal?`.
# Qualification-pending (source-backed, not yet captured).
_SEND_INPUT_TITLE_TOKEN = "would you like to send input to"
_REQUEST_USER_INPUT_RE = re.compile(r"Question \d+/\d+")
_FIELD_FORM_RE = re.compile(r"Field \d+/\d+")
_APP_LINK_HINTS = (
    "Install on ChatGPT",
    "Use tab / ↑ ↓ to move, enter to select, esc to close",
    "Newly installed apps can take a few minutes to appear in /apps.",
)
_LIST_SELECTION_FOOTER = "Press enter to confirm or esc to go back"
# 0.162.x list-selection picker footer (bottom_pane/selection_picker_tests.rs,
# chatwidget/tests/permission_picker_tests.rs). Renders only for bottom-pane
# selection pickers, so the footer alone is a blocking signal.
_LIST_SELECTION_FOOTER_0_162_RE = re.compile(
    r"enter\s+(?:select|continue)\s*·\s*esc\s+back",
    re.IGNORECASE,
)
_LIST_SELECTION_TITLES = (
    "Select Model and Effort",
    "Select Reasoning Effort",
    "Select Personality",
    "Select Approval Mode",
)
_LIST_SELECTION_ROW_RE = re.compile(r"(?m)^\s*›\s+\d+\.\s+.+$")
# Workspace-trust screen (onboarding/trust_directory.rs): `Trust this folder?`
# title plus the `Trust and continue` option.
_TRUST_TITLE_TOKEN = "trust this folder?"
_TRUST_OPTION_TOKEN = "trust and continue"
# Warnings viewer (bottom_pane/warnings_view_render.rs): title
# `Warnings · N of M · <source>` with a dismiss affordance in the footer.
_WARNINGS_TITLE_RE = re.compile(r"Warnings\s*·\s*\d+\s*of\s*\d+\s*·")
_WARNINGS_FOOTER_TOKEN = "dismiss"


def has_blocking_overlay(surface: SurfaceView) -> bool:
    """Return whether one Codex modal/operator overlay is visible."""

    stripped_text = "\n".join(surface.stripped_lines)
    lowered = stripped_text.lower()
    live_edge_text = "\n".join(line for line in surface.stripped_lines[-28:] if line.strip())
    live_edge_lowered = live_edge_text.lower()
    if any(title in stripped_text for title in _APPROVAL_TITLES) and any(
        footer in stripped_text for footer in _APPROVAL_FOOTERS
    ):
        return True
    if _SEND_INPUT_TITLE_TOKEN in lowered:
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
    if _TRUST_TITLE_TOKEN in lowered and _TRUST_OPTION_TOKEN in lowered:
        return True
    if _WARNINGS_TITLE_RE.search(stripped_text) is not None and (
        _WARNINGS_FOOTER_TOKEN in live_edge_lowered
    ):
        return True
    if _LIST_SELECTION_FOOTER_0_162_RE.search(live_edge_text) is not None:
        return True
    if _LIST_SELECTION_FOOTER in live_edge_text and (
        any(title in live_edge_text for title in _LIST_SELECTION_TITLES)
        or _LIST_SELECTION_ROW_RE.search(live_edge_text) is not None
    ):
        return True
    return False
