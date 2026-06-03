"""Formatting helpers for CLI JSON input fix guides."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import json
from typing import Any


@dataclass(frozen=True)
class JsonInputFixGuide:
    """One human-facing JSON input repair guide."""

    problem: str
    command: str
    input_name: str
    input_source: str
    schema: Mapping[str, Any]
    example_payload: Mapping[str, Any]
    required_paths: tuple[str, ...] = ()
    command_example: str | None = None

    def render(self) -> str:
        """Return a terminal-safe fix guide."""

        lines = [
            self.problem.strip(),
            "",
            "Fix guide:",
            f"- command: {self.command}",
            f"- input: {self.input_name}",
            f"- input source: {self.input_source}",
        ]
        if self.required_paths:
            lines.append(f"- required field paths: {', '.join(self.required_paths)}")
        lines.extend(
            [
                "- expected JSON shape:",
                _pretty_json(self.schema),
                "- example payload:",
                _compact_json(self.example_payload),
            ]
        )
        if self.command_example is not None:
            lines.extend(["- example command:", self.command_example])
        return "\n".join(lines)


def _pretty_json(payload: Mapping[str, Any]) -> str:
    """Return deterministic pretty JSON for schema display."""

    return json.dumps(payload, indent=2, sort_keys=False)


def _compact_json(payload: Mapping[str, Any]) -> str:
    """Return deterministic compact JSON for command examples."""

    return json.dumps(payload, sort_keys=False, separators=(",", ":"))


def compact_json_object(payload: Mapping[str, Any]) -> str:
    """Return one compact JSON object string."""

    return _compact_json(payload)


def required_field_paths(prefix: str, names: Sequence[str]) -> tuple[str, ...]:
    """Return dot-path labels for required JSON fields."""

    return tuple(f"{prefix}.{name}" for name in names)
