"""Codex TUI activity and transcript-growth helpers."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from houmao.shared_tui_tracking.apps.codex_tui.signals.interrupted import (
    steer_interruption_text_visible,
)


_BOOTSTRAP_STATUS_PREFIXES = (
    "Booting MCP server:",
    "Starting MCP servers",
)
_AGENT_TURN_STATUS_RE = re.compile(r"^\s*• (.+?) \((.+esc to interrupt.*)\)\s*$")
_TOOL_CELL_RE = re.compile(r"^\s*• (Calling |Running |Waited for background terminal · ).+")
_PENDING_STEER_PREFIX = "• Messages to be submitted after next tool call"
_REJECTED_STEER_PREFIX = "• Messages to be submitted at end of turn"
_QUEUED_FOLLOW_UP_PREFIX = "• Queued follow-up inputs"
_PENDING_INPUT_PREFIXES = (
    _PENDING_STEER_PREFIX,
    _REJECTED_STEER_PREFIX,
    _QUEUED_FOLLOW_UP_PREFIX,
)
_NON_RESPONSE_BULLET_PREFIXES = (
    *_PENDING_INPUT_PREFIXES,
    "• You have ",
    "• Working ",
    "• Calling ",
    "• Running ",
    "• Waited for background terminal · ",
    "• Waiting for ",
    "• Finished waiting",
)
_COLLAB_CELL_RE = re.compile(
    r"^\s*• (?P<kind>Waiting for .+|Finished waiting|Resumed .+|Failed to resume .+)\s*$"
)
_RETRY_STATUS_RE = re.compile(
    r"^(?:•\s+)?Reconnecting(?:\.\.\.|\s+to\s+model\s+stream)\s*"
    r"(?:\(\d+/\d+\)|\d+/\d+)(?:\s+\([^\n]*esc to interrupt[^\n]*\))?$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CodexActivitySignals:
    """Single-snapshot Codex activity evidence."""

    active_evidence: bool
    active_status_row_visible: bool
    latest_status_line: str | None
    active_reasons: tuple[str, ...]
    steer_handoff: bool
    in_flight_tool_cell: bool
    pending_input_visible: bool


def detect_activity(
    *,
    latest_turn_lines: tuple[str, ...],
    live_edge_lines: tuple[str, ...],
    prompt_visible: bool,
    steer_interruption_text: str,
    include_collaboration_cells: bool = False,
    include_queued_follow_up: bool = False,
) -> CodexActivitySignals:
    """Return current Codex activity evidence from one surface."""

    del steer_interruption_text
    active_reasons: list[str] = []
    active_status_line: str | None = None
    for line in reversed(live_edge_lines):
        stripped = line.strip()
        if _is_assistant_response_line(stripped):
            break
        if stripped.startswith(_PENDING_INPUT_PREFIXES):
            continue
        match = _AGENT_TURN_STATUS_RE.match(stripped)
        if match is None:
            continue
        header = match.group(1).strip()
        if any(header.startswith(prefix) for prefix in _BOOTSTRAP_STATUS_PREFIXES):
            continue
        active_status_line = stripped
        active_reasons.append("status_row")
        break

    in_flight_tool_cell = any(_TOOL_CELL_RE.match(line) is not None for line in live_edge_lines)
    if in_flight_tool_cell:
        active_reasons.append("tool_cell")

    if include_collaboration_cells and _latest_collaboration_cell_is_in_flight(live_edge_lines):
        active_reasons.append("collaboration_cell")

    pending_input_prefix = (
        _current_pending_input_prefix(live_edge_lines) if include_queued_follow_up else None
    )
    if pending_input_prefix == _QUEUED_FOLLOW_UP_PREFIX:
        active_reasons.append("queued_follow_up")
    elif pending_input_prefix is not None:
        active_reasons.append("pending_input")

    retry_status_line = _latest_retry_status_line(live_edge_lines)
    if retry_status_line is not None:
        active_reasons.append("stream_retry_status")

    steer_handoff = (
        steer_interruption_text_visible(lines=latest_turn_lines)
        and prompt_visible
        and active_status_line is not None
    )
    if steer_handoff:
        active_reasons.append("steer_handoff")

    return CodexActivitySignals(
        active_evidence=bool(active_reasons),
        active_status_row_visible=active_status_line is not None,
        latest_status_line=active_status_line or retry_status_line,
        active_reasons=tuple(dict.fromkeys(active_reasons)),
        steer_handoff=steer_handoff,
        in_flight_tool_cell=in_flight_tool_cell,
        pending_input_visible=pending_input_prefix is not None,
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


def _is_assistant_response_line(stripped: str) -> bool:
    """Return whether one normalized line begins an assistant response cell."""

    return stripped.startswith("• ") and not stripped.startswith(_NON_RESPONSE_BULLET_PREFIXES)


def _latest_retry_status_line(live_edge_lines: tuple[str, ...]) -> str | None:
    """Return the latest live-edge retry/reconnect status line, if present."""

    for line in reversed(live_edge_lines):
        stripped = line.strip()
        if not stripped or stripped.startswith(("■", "⚠")):
            continue
        if _RETRY_STATUS_RE.search(stripped) is not None:
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


def _current_pending_input_prefix(live_edge_lines: tuple[str, ...]) -> str | None:
    """Return the current pending-input section with no later assistant response."""

    queue_index: int | None = None
    queue_prefix: str | None = None
    for index, line in enumerate(live_edge_lines):
        stripped = line.strip()
        for prefix in _PENDING_INPUT_PREFIXES:
            if stripped.startswith(prefix):
                queue_index = index
                queue_prefix = prefix
                break
    if queue_index is None:
        return None
    for line in live_edge_lines[queue_index + 1 :]:
        stripped = line.strip()
        if not stripped.startswith("• "):
            continue
        if stripped.startswith(_NON_RESPONSE_BULLET_PREFIXES):
            continue
        return None
    return queue_prefix
