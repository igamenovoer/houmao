"""Unified runtime shadow parser stack for CAO-backed tools."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from .claude_code_shadow import (
    ClaudeDialogProjector,
    ClaudeCodeShadowParseError,
    ClaudeCodeShadowParser,
)
from .codex_shadow import (
    CodexDialogProjector,
    CodexShadowParseError,
    CodexShadowParser,
)
from .shadow_parser_core import (
    ParsedShadowSnapshot,
    ShadowParserError,
)

_PARSER_FAMILY_CLAUDE_SHADOW = "claude_shadow"
_PARSER_FAMILY_CODEX_SHADOW = "codex_shadow"


@dataclass(frozen=True)
class ShadowParserStackSelection:
    """Selected parser stack and parser-family identifier."""

    parser: "ShadowParser"
    parser_family: str


ShadowParser = ClaudeCodeShadowParser | CodexShadowParser


class ShadowParserStack:
    """Provider-aware adapter for runtime-owned shadow parsers."""

    def __init__(
        self,
        *,
        tool: str,
        projector_override: ClaudeDialogProjector | CodexDialogProjector | None = None,
    ) -> None:
        self._tool = tool
        self._parser: ShadowParser
        if tool == "claude":
            self._parser = ClaudeCodeShadowParser(
                projector_override=cast(ClaudeDialogProjector | None, projector_override)
            )
            self._parser_family = _PARSER_FAMILY_CLAUDE_SHADOW
            return
        if tool == "codex":
            self._parser = CodexShadowParser(
                projector_override=cast(CodexDialogProjector | None, projector_override)
            )
            self._parser_family = _PARSER_FAMILY_CODEX_SHADOW
            return
        raise ValueError(f"Shadow parsing is unsupported for tool {tool!r}")

    @property
    def parser_family(self) -> str:
        """Return selected parser-family identifier."""

        return self._parser_family

    @property
    def parser(self) -> ShadowParser:
        """Return selected provider parser instance."""

        return self._parser

    def selection(self) -> ShadowParserStackSelection:
        """Return parser selection details for diagnostics."""

        return ShadowParserStackSelection(
            parser=self._parser,
            parser_family=self._parser_family,
        )

    def capture_baseline_pos(self, scrollback: str) -> int:
        """Capture parser-specific baseline offset."""

        return self._parser.capture_baseline_pos(scrollback)

    def parse_snapshot(
        self,
        scrollback: str,
        *,
        baseline_pos: int,
    ) -> ParsedShadowSnapshot:
        """Return provider surface assessment and dialog projection together."""

        return self._parser.parse_snapshot(scrollback, baseline_pos=baseline_pos)

    def ansi_stripped_tail_excerpt(self, scrollback: str, *, max_lines: int = 12) -> str:
        """Return ANSI-stripped tail excerpt via selected parser."""

        return self._parser.ansi_stripped_tail_excerpt(scrollback, max_lines=max_lines)


def as_shadow_parser_error(exc: Exception) -> ShadowParserError:
    """Normalize provider-specific parse errors into shared error type."""

    if isinstance(exc, ShadowParserError):
        return exc
    if isinstance(exc, (CodexShadowParseError, ClaudeCodeShadowParseError)):
        return ShadowParserError(str(exc))
    return ShadowParserError(str(exc))
