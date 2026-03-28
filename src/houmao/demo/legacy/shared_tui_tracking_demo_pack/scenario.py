"""Scenario definitions for recorder-backed tracked-TUI capture."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal, cast

from .models import ToolName


ScenarioAction = Literal[
    "wait_for_ready",
    "wait_for_active",
    "wait_for_interrupted_signal",
    "wait_for_interrupted_ready",
    "wait_seconds",
    "wait_for_pattern",
    "send_text",
    "send_key",
    "interrupt_turn",
    "close_tool",
    "kill_supported_process",
    "kill_session",
]


@dataclass(frozen=True)
class ScenarioStep:
    """One recorder-capture driver step."""

    action: ScenarioAction
    name: str
    text: str | None = None
    key: str | None = None
    seconds: float | None = None
    timeout_seconds: float | None = None
    pattern: str | None = None
    submit: bool = False

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "ScenarioStep":
        """Parse one scenario-step payload."""

        return cls(
            action=cast(ScenarioAction, str(payload["action"])),
            name=str(payload.get("name", payload["action"])),
            text=_optional_string(payload.get("text")),
            key=_optional_string(payload.get("key")),
            seconds=_optional_float(payload.get("seconds")),
            timeout_seconds=_optional_float(payload.get("timeout_seconds")),
            pattern=_optional_string(payload.get("pattern")),
            submit=bool(payload.get("submit", False)),
        )

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-serializable payload."""

        return asdict(self)


@dataclass(frozen=True)
class ScenarioLaunchSpec:
    """Launch settings for one capture scenario."""

    settle_seconds: float | None = None
    sample_interval_seconds: float | None = None
    runtime_observer_interval_seconds: float | None = None
    ready_timeout_seconds: float | None = None
    recipe_path: str | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, Any] | None) -> "ScenarioLaunchSpec":
        """Parse one optional launch payload."""

        if payload is None:
            return cls()
        return cls(
            settle_seconds=_optional_float(payload.get("settle_seconds")),
            sample_interval_seconds=_optional_float(payload.get("sample_interval_seconds")),
            runtime_observer_interval_seconds=_optional_float(
                payload.get("runtime_observer_interval_seconds")
            ),
            ready_timeout_seconds=_optional_float(payload.get("ready_timeout_seconds")),
            recipe_path=_optional_string(payload.get("recipe_path")),
        )

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-serializable payload."""

        return asdict(self)


@dataclass(frozen=True)
class ScenarioDefinition:
    """One recorded-capture scenario loaded from JSON."""

    scenario_id: str
    tool: ToolName
    description: str
    launch: ScenarioLaunchSpec
    steps: tuple[ScenarioStep, ...]

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "ScenarioDefinition":
        """Parse one scenario-definition payload."""

        return cls(
            scenario_id=str(payload["id"]),
            tool=cast(ToolName, str(payload["tool"])),
            description=str(payload["description"]),
            launch=ScenarioLaunchSpec.from_payload(
                cast(dict[str, Any] | None, payload.get("launch"))
            ),
            steps=tuple(
                ScenarioStep.from_payload(item)
                for item in _require_list(payload.get("steps"), context="steps")
            ),
        )

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-serializable payload."""

        return {
            "id": self.scenario_id,
            "tool": self.tool,
            "description": self.description,
            "launch": self.launch.to_payload(),
            "steps": [item.to_payload() for item in self.steps],
        }


def load_scenario(path: Path) -> ScenarioDefinition:
    """Load one scenario definition from disk."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    return ScenarioDefinition.from_payload(payload)


def _require_list(value: object, *, context: str) -> list[dict[str, Any]]:
    """Return a validated list of mapping items."""

    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError(f"{context} must be a list[dict]")
    return value


def _optional_float(value: object) -> float | None:
    """Return one optional float value."""

    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (float, int, str)):
        return float(value)
    return None


def _optional_string(value: object) -> str | None:
    """Return one optional string value."""

    if value is None:
        return None
    return str(value)
