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


@dataclass(frozen=True)
class CodexActivitySignals:
    """Single-snapshot Codex activity evidence."""

    active_evidence: bool
    active_status_row_visible: bool
    latest_status_line: str | None
    active_reasons: tuple[str, ...]
    steer_handoff: bool
    in_flight_tool_cell: bool


def detect_activity(
    *,
    latest_turn_lines: tuple[str, ...],
    live_edge_lines: tuple[str, ...],
    prompt_visible: bool,
    steer_interruption_text: str,
) -> CodexActivitySignals:
    """Return current Codex activity evidence from one surface."""

    del steer_interruption_text
    active_reasons: list[str] = []
    active_status_line: str | None = None
    for line in reversed(live_edge_lines):
        stripped = line.strip()
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
        latest_status_line=active_status_line,
        active_reasons=tuple(dict.fromkeys(active_reasons)),
        steer_handoff=steer_handoff,
        in_flight_tool_cell=in_flight_tool_cell,
    )


def latest_turn_region_signature(latest_turn_lines: tuple[str, ...]) -> str:
    """Return a private signature for the latest-turn region."""

    payload = "\n".join(latest_turn_lines)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
