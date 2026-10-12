"""Codex TUI activity and transcript-growth helpers.

Needle provenance: codex 0.162.x source (`extern/orphan/codex`, codex-rs/tui).
Source-backed needles use bounded structure plus essential semantic tokens
rather than exact full-sentence literals; capture-unverified families are
marked qualification-pending at their definition sites.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from houmao.shared_tui_tracking.surface import SurfaceView


_BOOTSTRAP_STATUS_PREFIXES = (
    "Booting MCP server:",
    "Starting MCP servers",
)
# Status row structure `• <label> (<elapsed> • esc to interrupt)`: confirmed
# against 0.162.x (chatwidget status row; tests/suite snapshots). The label is
# matched generically so maintained labels outside the historical hardcoded
# bullet prefixes (for example `Compacting context`) still count as busy.
_AGENT_TURN_STATUS_RE = re.compile(r"^\s*• (.+?) \((.+esc to interrupt.*)\)\s*$")
# Compaction status label family: 0.162.x renders `Compacting context`
# (codex-rs/tui/src/chatwidget/compaction.rs COMPACTION_HEADER). Token match so
# minor label rewording stays recognized. The reducer treats this reason as
# provider-maintenance activity, not operator prompt work.
_COMPACTION_STATUS_TOKEN_RE = re.compile(r"\bcompact", re.IGNORECASE)
_TOOL_CELL_RE = re.compile(r"^\s*• (Calling |Running |Waited for background terminal · ).+")
_COLLAB_CELL_RE = re.compile(
    r"^\s*• (?P<kind>Waiting for .+|Finished waiting|Resumed .+|Failed to resume .+)\s*$"
)
# Reconnect/retry status family, source-backed against 0.162.x:
# - `Reconnecting... 2/5` (chatwidget/tests/status_and_layout.rs)
# - `• Reconnecting to server… (0s)` (chatwidget/reconnect.rs `set_status_header`)
# Retry-counter log lines (`stream disconnected - retrying sampling request`)
# are tracing-only and never render on the TUI, so they are not needles.
# Qualification-pending until the fault-injection capture iteration lands.
_RETRY_STATUS_RE = re.compile(
    r"^(?:•\s+)?Reconnecting(?:\.{3}|…)?(?:\s+to\s+.+?)?"
    r"(?:\s+\(\d+/\d+\)|\s+\d+/\d+|\s+\(\d+(?:\.\d+)?s\))?"
    r"(?:\s+\([^)]*esc to interrupt[^)]*\))?\s*$",
    re.IGNORECASE,
)
# Queued-echo surface: while a turn is busy, a submitted follow-up renders as a
# composer-style `› <text>` row above the status row. It later collapses into
# `+ N lines (^t to expand)`, which carries no queue signal (documented
# single-snapshot blind spot).
_QUEUED_ECHO_RE = re.compile(r"^\s*›\s+\S")
_WORKED_DOCK_PREFIX = "Worked for "
_INTERRUPT_NOTICE_TOKEN = "conversation interrupted"
_NON_RESPONSE_BULLET_PREFIXES = (
    "• You have ",
    "• Working ",
    "• Calling ",
    "• Running ",
    "• Waited for background terminal · ",
    "• Waiting for ",
    "• Finished waiting",
)


@dataclass(frozen=True)
class CodexActivitySignals:
    """Single-snapshot Codex activity evidence."""

    active_evidence: bool
    active_status_row_visible: bool
    latest_status_line: str | None
    active_reasons: tuple[str, ...]
    in_flight_tool_cell: bool


def detect_activity(
    *,
    latest_turn_lines: tuple[str, ...],
    live_edge_lines: tuple[str, ...],
    prompt_visible: bool,
    include_collaboration_cells: bool = False,
) -> CodexActivitySignals:
    """Return current Codex activity evidence from one surface.

    The status-row check runs before the assistant-prose break: a status label
    outside the legacy bullet prefixes (compaction in 0.162.x) is busy
    evidence, not assistant prose that terminates the scan.
    """

    del latest_turn_lines, prompt_visible
    active_reasons: list[str] = []
    active_status_line: str | None = None
    for line in reversed(live_edge_lines):
        stripped = line.strip()
        match = _AGENT_TURN_STATUS_RE.match(stripped)
        if match is not None:
            header = match.group(1).strip()
            if any(header.startswith(prefix) for prefix in _BOOTSTRAP_STATUS_PREFIXES):
                continue
            active_status_line = stripped
            if _COMPACTION_STATUS_TOKEN_RE.search(header) is not None:
                # Compaction is provider maintenance, not operator prompt work;
                # it carries its own reason instead of the generic status_row
                # reason so the reducer can scope its carve-out to maintenance.
                active_reasons.append("compaction_status")
            else:
                active_reasons.append("status_row")
            break
        if _is_assistant_response_line(stripped):
            break

    in_flight_tool_cell = any(_TOOL_CELL_RE.match(line) is not None for line in live_edge_lines)
    if in_flight_tool_cell:
        active_reasons.append("tool_cell")

    if include_collaboration_cells and _latest_collaboration_cell_is_in_flight(live_edge_lines):
        active_reasons.append("collaboration_cell")

    retry_status_line = _latest_retry_status_line(live_edge_lines)
    if retry_status_line is not None:
        active_reasons.append("stream_retry_status")

    return CodexActivitySignals(
        active_evidence=bool(active_reasons),
        active_status_row_visible=active_status_line is not None,
        latest_status_line=active_status_line or retry_status_line,
        active_reasons=tuple(dict.fromkeys(active_reasons)),
        in_flight_tool_cell=in_flight_tool_cell,
    )


def latest_turn_region_signature(latest_turn_lines: tuple[str, ...]) -> str:
    """Return a private signature for the latest-turn region."""

    payload = "\n".join(latest_turn_lines)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def assistant_response_visible(latest_turn_lines: tuple[str, ...]) -> bool:
    """Return whether the current turn contains a visible assistant response cell."""

    for line in latest_turn_lines:
        stripped = line.strip()
        if _is_assistant_response_line(stripped):
            return True
    return False


def queued_echo_present(*, surface: SurfaceView) -> bool:
    """Return whether a queued follow-up echo renders inside the live surface.

    Codex 0.162.x renders a follow-up submitted mid-turn as a composer-style
    `› <text>` row above the status row. The echo anchors the latest-turn
    region, so in isolation it looks exactly like a turn-starting echo. The
    disambiguation is structural: a queued echo sits between in-flight turn
    content above it and the live status row below it, while a turn-starting
    echo follows the previous turn's `Worked for` dock or interruption notice
    and a historical echo has the settled turn's dock below it. Once the echo
    collapses into `+ N lines (^t to expand)` no single-snapshot signal
    remains; that window is a documented blind spot.
    """

    lines = [line.strip() for line in surface.stripped_lines if line.strip()]
    echo_indices = [index for index, line in enumerate(lines) if _QUEUED_ECHO_RE.match(line)]
    if len(echo_indices) < 2:
        return False
    anchor = echo_indices[-2]  # nearest › payload line above the composer
    composer = echo_indices[-1]
    for line in lines[anchor + 1 : composer]:
        if line.startswith(_WORKED_DOCK_PREFIX) or _INTERRUPT_NOTICE_TOKEN in line.lower():
            return False
    for line in reversed(lines[:anchor]):
        if _is_assistant_response_line(line):
            return True
        if line.startswith(_WORKED_DOCK_PREFIX):
            return False
        if _INTERRUPT_NOTICE_TOKEN in line.lower():
            return False
        if _AGENT_TURN_STATUS_RE.match(line) is not None:
            return False
        if line.startswith("›"):
            return False
    return False


def _is_assistant_response_line(stripped: str) -> bool:
    """Return whether one normalized line begins an assistant response cell."""

    return stripped.startswith("• ") and not stripped.startswith(_NON_RESPONSE_BULLET_PREFIXES)


def _latest_retry_status_line(live_edge_lines: tuple[str, ...]) -> str | None:
    """Return the latest live-edge retry/reconnect status line, if present."""

    for line in reversed(live_edge_lines):
        stripped = line.strip()
        if not stripped or stripped.startswith(("■", "⚠")):
            continue
        if _RETRY_STATUS_RE.match(stripped) is not None:
            return stripped
    return None


def _latest_collaboration_cell_is_in_flight(live_edge_lines: tuple[str, ...]) -> bool:
    """Return whether the latest current Codex collaboration cell is still in flight."""

    for line in reversed(live_edge_lines):
        match = _COLLAB_CELL_RE.match(line)
        if match is None:
            continue
        kind = match.group("kind")
        return kind.startswith(("Waiting for", "Resumed "))
    return False
