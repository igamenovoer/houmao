"""Base signal-detector interfaces and shared surface helpers."""

from __future__ import annotations

import abc
import re
from dataclasses import dataclass
from typing import Iterable

from houmao.explore.claude_code_state_tracking.models import DetectedSignals


ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")


@dataclass(frozen=True)
class SurfaceView:
    """Structured current-surface view derived from raw ANSI text."""

    raw_text: str
    raw_lines: tuple[str, ...]
    stripped_lines: tuple[str, ...]

    @classmethod
    def from_text(cls, raw_text: str) -> "SurfaceView":
        """Build one view from raw ANSI pane text."""

        raw_lines = tuple(raw_text.splitlines())
        stripped_lines = tuple(strip_ansi(line) for line in raw_lines)
        return cls(raw_text=raw_text, raw_lines=raw_lines, stripped_lines=stripped_lines)

    def last_prompt_index(self) -> int | None:
        """Return the last visible prompt-line index if present."""

        indices = [
            index for index, line in enumerate(self.stripped_lines) if line.strip().startswith("❯")
        ]
        return indices[-1] if indices else None

    def last_status_index(self) -> int | None:
        """Return the last visible Claude status-line index if present."""

        indices = [
            index for index, line in enumerate(self.stripped_lines) if line.strip().startswith("⎿")
        ]
        return indices[-1] if indices else None

    def latest_status_line(self) -> str | None:
        """Return the last visible stripped status line."""

        index = self.last_status_index()
        if index is None:
            return None
        return self.stripped_lines[index].strip()

    def prompt_visible_after(self, index: int) -> bool:
        """Return whether a fresh prompt is visible below one line index."""

        last_prompt_index = self.last_prompt_index()
        return last_prompt_index is not None and last_prompt_index > index

    def prompt_text(self) -> str | None:
        """Return stripped text from the latest visible prompt line."""

        index = self.last_prompt_index()
        if index is None:
            return None
        line = self.stripped_lines[index].strip()
        if not line.startswith("❯"):
            return None
        return line[1:].strip()

    def footer_lines(self, count: int = 4) -> tuple[str, ...]:
        """Return the last few non-empty stripped lines for footer inspection."""

        if count <= 0:
            return ()
        lines = [line for line in self.stripped_lines if line.strip()]
        return tuple(lines[-count:])

    def footer_raw_lines(self, count: int = 4) -> tuple[str, ...]:
        """Return the last few non-empty raw lines for footer inspection."""

        if count <= 0:
            return ()
        lines = [
            raw_line
            for raw_line, stripped_line in zip(self.raw_lines, self.stripped_lines, strict=True)
            if stripped_line.strip()
        ]
        return tuple(lines[-count:])

    def iter_lines_with_indices(self) -> Iterable[tuple[int, str, str]]:
        """Yield `(index, raw_line, stripped_line)` tuples."""

        for index, (raw_line, stripped_line) in enumerate(
            zip(self.raw_lines, self.stripped_lines, strict=True)
        ):
            yield index, raw_line, stripped_line


class BaseTurnSignalDetector(abc.ABC):
    """Abstract interface for tool/version-specific signal detectors."""

    @property
    @abc.abstractmethod
    def detector_name(self) -> str:
        """Return the detector family name."""

    @property
    @abc.abstractmethod
    def detector_version(self) -> str:
        """Return the detector version selector."""

    @abc.abstractmethod
    def compatibility_score(self, *, observed_version: str | None) -> int:
        """Return a higher score for a closer-compatible version match."""

    @abc.abstractmethod
    def detect(self, *, output_text: str) -> DetectedSignals:
        """Return normalized signals for one raw pane surface."""


def select_claude_detector(*, observed_version: str | None) -> BaseTurnSignalDetector:
    """Return the closest-compatible Claude detector.

    Parameters
    ----------
    observed_version:
        Observed Claude Code version string, when available.
    """

    from houmao.explore.claude_code_state_tracking.detectors.claude_code_v2_1_x import (
        ClaudeCodeSignalDetectorV2_1_X,
        FallbackClaudeDetector,
    )

    candidates: list[BaseTurnSignalDetector] = [
        ClaudeCodeSignalDetectorV2_1_X(),
        FallbackClaudeDetector(),
    ]
    return max(
        candidates, key=lambda item: item.compatibility_score(observed_version=observed_version)
    )


def strip_ansi(text: str) -> str:
    """Return one ANSI-stripped string."""

    return ANSI_ESCAPE_RE.sub("", text).replace("\u00a0", " ")
