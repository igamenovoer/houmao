"""Typed models and constants for the Houmao-server agent API demo pack."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


CURRENT_RUN_ROOT_FILENAME = "current_run_root.txt"
DEFAULT_DEMO_PACK_DIRNAME = "houmao-server-agent-api-demo-pack"
DEFAULT_OUTPUTS_DIRNAME = "outputs"
DEFAULT_RUNS_DIRNAME = "runs"
DEFAULT_AUTOTEST_OUTPUTS_DIRNAME = "autotest"
DEFAULT_PROMPT_FILENAME = "prompt.txt"
DEFAULT_INTERRUPT_PROMPT_FILENAME = "interrupt_prompt.txt"
DEFAULT_PARAMETERS_FILENAME = "demo_parameters.json"
DEFAULT_EXPECTED_REPORT_RELATIVE_PATH = Path("expected_report") / "report.json"


@dataclass(frozen=True)
class DemoPackPaths:
    """Resolved repository and pack roots for the demo pack."""

    repo_root: Path
    pack_dir: Path
    outputs_dir: Path
    runs_dir: Path
    autotest_outputs_dir: Path
    current_run_root_path: Path


@dataclass
class PersistedDemoState:
    """Persisted JSON-ready lifecycle state for one demo-owned run."""

    active: bool
    repo_root: str
    pack_dir: str
    run_root: str
    selected_lane_ids: list[str]
    started_at_utc: str
    updated_at_utc: str
    steps: dict[str, bool] = field(default_factory=dict)
    config: dict[str, Any] = field(default_factory=dict)
    preflight: dict[str, Any] = field(default_factory=dict)
    server: dict[str, Any] = field(default_factory=dict)
    lanes: dict[str, dict[str, Any]] = field(default_factory=dict)
    failure: str | None = None
    shared_routes: dict[str, Any] | None = None
    last_verify_result: dict[str, Any] | None = None
    last_stop_result: dict[str, Any] | None = None

    def to_payload(self) -> dict[str, Any]:
        """Return one JSON-ready payload."""

        return {
            "active": self.active,
            "repo_root": self.repo_root,
            "pack_dir": self.pack_dir,
            "run_root": self.run_root,
            "selected_lane_ids": list(self.selected_lane_ids),
            "started_at_utc": self.started_at_utc,
            "updated_at_utc": self.updated_at_utc,
            "steps": dict(self.steps),
            "config": dict(self.config),
            "preflight": dict(self.preflight),
            "server": dict(self.server),
            "lanes": {key: dict(value) for key, value in self.lanes.items()},
            "failure": self.failure,
            "shared_routes": None if self.shared_routes is None else dict(self.shared_routes),
            "last_verify_result": (
                None if self.last_verify_result is None else dict(self.last_verify_result)
            ),
            "last_stop_result": (
                None if self.last_stop_result is None else dict(self.last_stop_result)
            ),
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> PersistedDemoState:
        """Build one persisted state model from a JSON object."""

        return cls(
            active=bool(payload.get("active")),
            repo_root=str(payload["repo_root"]),
            pack_dir=str(payload["pack_dir"]),
            run_root=str(payload["run_root"]),
            selected_lane_ids=[str(item) for item in payload.get("selected_lane_ids", [])],
            started_at_utc=str(payload["started_at_utc"]),
            updated_at_utc=str(payload["updated_at_utc"]),
            steps={str(key): bool(value) for key, value in dict(payload.get("steps", {})).items()},
            config=dict(payload.get("config", {})),
            preflight=dict(payload.get("preflight", {})),
            server=dict(payload.get("server", {})),
            lanes={
                str(key): dict(value) for key, value in dict(payload.get("lanes", {})).items()
            },
            failure=payload.get("failure"),
            shared_routes=(
                None
                if payload.get("shared_routes") is None
                else dict(payload.get("shared_routes", {}))
            ),
            last_verify_result=(
                None
                if payload.get("last_verify_result") is None
                else dict(payload.get("last_verify_result", {}))
            ),
            last_stop_result=(
                None
                if payload.get("last_stop_result") is None
                else dict(payload.get("last_stop_result", {}))
            ),
        )
