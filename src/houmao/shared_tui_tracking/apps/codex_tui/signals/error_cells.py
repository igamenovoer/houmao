"""Codex TUI terminal failure-surface helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass


_CODEX_ERROR_CELL_RE = re.compile(r"^\s*■ .+")
_CODEX_WARNING_CELL_RE = re.compile(r"^\s*⚠ .+")
_PROMPT_LINE_RE = re.compile(r"^\s*›")
_MAX_PROMPT_ADJACENT_ERROR_CONTINUATION_LINES = 4
_DEGRADED_COMPACT_RE = re.compile(
    r"\b(remote\s+compact|compact\s+task|compact(?:ion)?\b.*"
    r"(?:fail|error|disconnect|server|stream)|(?:server|stream|remote)\b.*\bcompact)\b",
    re.IGNORECASE,
)
_CODEX_REMOTE_COMPACT_STREAM_DISCONNECTED_RE = re.compile(
    r"\b(stream|connection|response\s+body|socket)\b.*\b(disconnect|closed|lost|ended)|"
    r"\b(disconnect|closed|lost|ended)\b.*\b(stream|connection|response\s+body|socket)\b",
    re.IGNORECASE,
)
_CODEX_REMOTE_COMPACT_CONTEXT_LENGTH_RE = re.compile(
    r"\b(context_length_exceeded|context\s+length|context\s+window|ran\s+out\s+of\s+room)\b",
    re.IGNORECASE,
)
_CODEX_REMOTE_COMPACT_UNKNOWN_PARAMETER_RE = re.compile(
    r"\b(unknown|unrecognized|unsupported)\s+(?:parameter|param|argument|field)\b",
    re.IGNORECASE,
)
_CODEX_REMOTE_COMPACT_SERVER_ERROR_RE = re.compile(
    r"\b(server\s+error|internal\s+server\s+error|bad\s+gateway|gateway\s+timeout|"
    r"service\s+unavailable|5\d\d)\b",
    re.IGNORECASE,
)
_KNOWN_TERMINAL_FAILURE_RE = re.compile(
    r"\b("
    r"server\s+overload(?:ed)?|"
    r"overload(?:ed)?|"
    r"high\s+(?:load|demand)|"
    r"at\s+capacity|"
    r"context\s+window|"
    r"ran\s+out\s+of\s+room|"
    r"quota\s+exceed(?:ed)?|"
    r"invalid\s+prompt"
    r")\b",
    re.IGNORECASE,
)
DEGRADED_CHAT_CONTEXT_NOTE = "chat_context=degraded"
KNOWN_FAILURE_NOTE = "known_failure_signal_detected"
CODEX_REMOTE_COMPACT_STREAM_DISCONNECTED = "codex_remote_compact_stream_disconnected"
CODEX_REMOTE_COMPACT_CONTEXT_LENGTH_EXCEEDED = "codex_remote_compact_context_length_exceeded"
CODEX_REMOTE_COMPACT_UNKNOWN_PARAMETER = "codex_remote_compact_unknown_parameter"
CODEX_REMOTE_COMPACT_SERVER_ERROR = "codex_remote_compact_server_error"


@dataclass(frozen=True)
class PromptAdjacentTerminalSignal:
    """Profile-private prompt-adjacent terminal signal classification."""

    block_text: str
    marker: str
    degraded_context: bool
    degraded_error_type: str | None
    known_failure: bool

    @property
    def current_error_present(self) -> bool:
        """Return whether this terminal surface is current-error evidence."""

        return True


def latest_error_cell(latest_turn_lines: tuple[str, ...]) -> str | None:
    """Return the latest relevant generic error-cell line if present."""

    for line in reversed(latest_turn_lines):
        if _CODEX_ERROR_CELL_RE.match(line) is not None:
            return line.strip()
    return None


def prompt_adjacent_error_cell(latest_turn_lines: tuple[str, ...]) -> str | None:
    """Return a red error cell directly adjacent to the current prompt edge."""

    signal = prompt_adjacent_terminal_signal(latest_turn_lines)
    if signal is None or signal.marker != "error":
        return None
    return signal.block_text


def prompt_adjacent_terminal_signal(
    latest_turn_lines: tuple[str, ...],
) -> PromptAdjacentTerminalSignal | None:
    """Return the prompt-adjacent terminal failure signal, if one is current."""

    continuation_lines = 0
    continuation_block: list[str] = []
    for raw_line in reversed(latest_turn_lines):
        line = raw_line.strip()
        if not line:
            continue
        if _CODEX_ERROR_CELL_RE.match(line) is not None:
            block_text = _terminal_block_text(line, continuation_block)
            return PromptAdjacentTerminalSignal(
                block_text=block_text,
                marker="error",
                degraded_context=is_degraded_error_cell(block_text),
                degraded_error_type=degraded_error_type(block_text),
                known_failure=_is_known_terminal_failure(block_text),
            )
        if _CODEX_WARNING_CELL_RE.match(line) is not None:
            block_text = _terminal_block_text(line, continuation_block)
            if not _is_known_terminal_failure(block_text):
                return None
            return PromptAdjacentTerminalSignal(
                block_text=block_text,
                marker="warning",
                degraded_context=is_degraded_error_cell(block_text),
                degraded_error_type=degraded_error_type(block_text),
                known_failure=True,
            )
        if not _can_belong_to_prompt_adjacent_error_block(line):
            return None
        continuation_lines += 1
        if continuation_lines > _MAX_PROMPT_ADJACENT_ERROR_CONTINUATION_LINES:
            return None
        continuation_block.append(line)
    return None


def is_degraded_error_cell(error_line: str | None) -> bool:
    """Return whether a prompt-adjacent error marks recoverable degraded context."""

    if error_line is None:
        return False
    return _DEGRADED_COMPACT_RE.search(error_line) is not None


def degraded_error_type(error_line: str | None) -> str | None:
    """Return the Codex-scoped degraded error type for one prompt-adjacent error."""

    if error_line is None or not is_degraded_error_cell(error_line):
        return None
    if _CODEX_REMOTE_COMPACT_STREAM_DISCONNECTED_RE.search(error_line) is not None:
        return CODEX_REMOTE_COMPACT_STREAM_DISCONNECTED
    if _CODEX_REMOTE_COMPACT_CONTEXT_LENGTH_RE.search(error_line) is not None:
        return CODEX_REMOTE_COMPACT_CONTEXT_LENGTH_EXCEEDED
    if _CODEX_REMOTE_COMPACT_UNKNOWN_PARAMETER_RE.search(error_line) is not None:
        return CODEX_REMOTE_COMPACT_UNKNOWN_PARAMETER
    if _CODEX_REMOTE_COMPACT_SERVER_ERROR_RE.search(error_line) is not None:
        return CODEX_REMOTE_COMPACT_SERVER_ERROR
    return "unknown"


def _can_belong_to_prompt_adjacent_error_block(line: str) -> bool:
    """Return whether one line can be wrapped text from a prompt-edge error."""

    if _PROMPT_LINE_RE.match(line) is not None:
        return False
    if line.startswith(("•", "⚠", "╭", "│", "╰")):
        return False
    if line.startswith("Tip:") or line.startswith("model:"):
        return False
    return True


def _terminal_block_text(head_line: str, continuation_block: list[str]) -> str:
    """Return normalized prompt-adjacent terminal block text."""

    return " ".join((head_line.strip(), *(line.strip() for line in reversed(continuation_block))))


def _is_known_terminal_failure(block_text: str) -> bool:
    """Return whether one bounded terminal block is a recognized terminal failure."""

    return _KNOWN_TERMINAL_FAILURE_RE.search(block_text) is not None
