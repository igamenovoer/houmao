"""Scenario definitions for the Claude Code state-tracking explore harness."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal, cast


ScenarioAction = Literal[
    "wait_for_ready",
    "wait_seconds",
    "wait_for_pattern",
    "send_text",
    "send_key",
    "attach_fault_injection",
    "kill_launch_process",
    "kill_session",
]


@dataclass(frozen=True)
class FaultInjectionSpec:
    """One subprocess-owned fault injection configuration."""

    mode: Literal["launch_strace_inject", "attach_strace_inject"]
    syscall: str
    error: str
    when: str

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-serializable payload."""

        return asdict(self)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "FaultInjectionSpec":
        """Parse one fault injection payload."""

        return cls(
            mode=cast(
                Literal["launch_strace_inject", "attach_strace_inject"], str(payload["mode"])
            ),
            syscall=str(payload["syscall"]),
            error=str(payload["error"]),
            when=str(payload["when"]),
        )


@dataclass(frozen=True)
class ScenarioStep:
    """One scenario driver step."""

    action: ScenarioAction
    name: str
    text: str | None = None
    key: str | None = None
    seconds: float | None = None
    timeout_seconds: float | None = None
    pattern: str | None = None
    submit: bool = False
    fault_injection: FaultInjectionSpec | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "ScenarioStep":
        """Parse one scenario step payload."""

        fault_injection = None
        if isinstance(payload.get("fault_injection"), dict):
            fault_injection = FaultInjectionSpec.from_payload(payload["fault_injection"])
        return cls(
            action=cast(ScenarioAction, str(payload["action"])),
            name=str(payload.get("name", payload["action"])),
            text=_optional_string(payload.get("text")),
            key=_optional_string(payload.get("key")),
            seconds=_optional_float(payload.get("seconds")),
            timeout_seconds=_optional_float(payload.get("timeout_seconds")),
            pattern=_optional_string(payload.get("pattern")),
            submit=bool(payload.get("submit", False)),
            fault_injection=fault_injection,
        )

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-serializable payload."""

        payload = asdict(self)
        if self.fault_injection is None:
            payload["fault_injection"] = None
        return payload


@dataclass(frozen=True)
class ScenarioLaunchSpec:
    """Launch-time settings for one scenario."""

    fault_injection: FaultInjectionSpec | None = None
    ready_timeout_seconds: float = 45.0
    settle_seconds: float = 1.0
    sample_interval_seconds: float = 0.2

    @classmethod
    def from_payload(cls, payload: dict[str, Any] | None) -> "ScenarioLaunchSpec":
        """Parse one optional launch payload."""

        if payload is None:
            return cls()
        fault_injection = None
        if isinstance(payload.get("fault_injection"), dict):
            fault_injection = FaultInjectionSpec.from_payload(payload["fault_injection"])
        return cls(
            fault_injection=fault_injection,
            ready_timeout_seconds=float(payload.get("ready_timeout_seconds", 45.0)),
            settle_seconds=float(payload.get("settle_seconds", 1.0)),
            sample_interval_seconds=float(payload.get("sample_interval_seconds", 0.2)),
        )

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-serializable payload."""

        return asdict(self)


@dataclass(frozen=True)
class ScenarioDefinition:
    """One scenario definition loaded from JSON."""

    scenario_id: str
    description: str
    launch: ScenarioLaunchSpec
    steps: tuple[ScenarioStep, ...]

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "ScenarioDefinition":
        """Parse one scenario definition."""

        return cls(
            scenario_id=str(payload["id"]),
            description=str(payload["description"]),
            launch=ScenarioLaunchSpec.from_payload(payload.get("launch")),
            steps=tuple(
                ScenarioStep.from_payload(item)
                for item in _require_list(payload.get("steps"), context="steps")
            ),
        )

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-serializable payload."""

        return {
            "id": self.scenario_id,
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

    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (float, int, str)):
        return float(value)
    return None


def _optional_string(value: object) -> str | None:
    """Return one optional string value."""

    if value is None:
        return None
    return str(value)
