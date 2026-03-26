"""Typed models and constants for the passive-server parallel validation demo pack."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal


CURRENT_RUN_ROOT_FILENAME = "current_run_root.txt"
DEFAULT_DEMO_PACK_DIRNAME = "passive-server-parallel-validation-demo-pack"
DEFAULT_OUTPUTS_DIRNAME = "outputs"
DEFAULT_RUNS_DIRNAME = "runs"
DEFAULT_AUTOTEST_OUTPUTS_DIRNAME = "autotest"
DEFAULT_PARAMETERS_FILENAME = "demo_parameters.json"
DEFAULT_SHARED_PROMPT_FILENAME = "shared_prompt.txt"
DEFAULT_GATEWAY_PROMPT_FILENAME = "gateway_prompt.txt"
DEFAULT_HEADLESS_PROMPT_FILENAME = "headless_prompt.txt"
DEFAULT_EXPECTED_REPORT_RELATIVE_PATH = Path("expected_report") / "report.json"
DEFAULT_AGENT_PROFILE = "server-api-smoke"
DEFAULT_ROLE_NAME = "server-api-smoke"
DEFAULT_PROVIDER = "claude_code"
DEFAULT_OLD_SERVER_PORT = 9889
DEFAULT_PASSIVE_SERVER_PORT = 9891
DEFAULT_HISTORY_LIMIT = 20
DEFAULT_DISCOVERY_TIMEOUT_SECONDS = 30.0
DEFAULT_REQUEST_TIMEOUT_SECONDS = 120.0
DEFAULT_REQUEST_POLL_INTERVAL_SECONDS = 0.5
DEFAULT_HEALTH_TIMEOUT_SECONDS = 30.0
DEFAULT_COMPAT_SHELL_READY_TIMEOUT_SECONDS = 20.0
DEFAULT_COMPAT_PROVIDER_READY_TIMEOUT_SECONDS = 120.0
DEFAULT_COMPAT_CODEX_WARMUP_SECONDS = 10.0

ProviderName = Literal["claude_code", "codex"]
PROVIDER_CHOICES: tuple[ProviderName, ...] = ("claude_code", "codex")


def tool_for_provider(provider: str) -> str:
    """Return the Houmao tool name for one selected provider."""

    if provider == "claude_code":
        return "claude"
    if provider == "codex":
        return "codex"
    raise ValueError(f"Unsupported provider: {provider!r}")


def executable_for_provider(provider: str) -> str:
    """Return the provider executable that must exist on PATH."""

    if provider == "claude_code":
        return "claude"
    if provider == "codex":
        return "codex"
    raise ValueError(f"Unsupported provider: {provider!r}")


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
    """Persisted JSON-ready lifecycle state for one dual-authority validation run."""

    active: bool
    repo_root: str
    pack_dir: str
    run_root: str
    provider: str
    tool: str
    agent_profile: str
    agent_def_dir: str
    started_at_utc: str
    updated_at_utc: str
    steps: dict[str, bool] = field(default_factory=dict)
    config: dict[str, Any] = field(default_factory=dict)
    preflight: dict[str, Any] = field(default_factory=dict)
    authorities: dict[str, Any] = field(default_factory=dict)
    shared_agent: dict[str, Any] = field(default_factory=dict)
    headless_agent: dict[str, Any] | None = None
    inspect_result: dict[str, Any] | None = None
    gateway_result: dict[str, Any] | None = None
    headless_result: dict[str, Any] | None = None
    stop_result: dict[str, Any] | None = None
    last_verify_result: dict[str, Any] | None = None
    failure: str | None = None

    def to_payload(self) -> dict[str, Any]:
        """Return one JSON-ready payload."""

        return {
            "active": self.active,
            "repo_root": self.repo_root,
            "pack_dir": self.pack_dir,
            "run_root": self.run_root,
            "provider": self.provider,
            "tool": self.tool,
            "agent_profile": self.agent_profile,
            "agent_def_dir": self.agent_def_dir,
            "started_at_utc": self.started_at_utc,
            "updated_at_utc": self.updated_at_utc,
            "steps": dict(self.steps),
            "config": dict(self.config),
            "preflight": dict(self.preflight),
            "authorities": dict(self.authorities),
            "shared_agent": dict(self.shared_agent),
            "headless_agent": None if self.headless_agent is None else dict(self.headless_agent),
            "inspect_result": None if self.inspect_result is None else dict(self.inspect_result),
            "gateway_result": None if self.gateway_result is None else dict(self.gateway_result),
            "headless_result": None if self.headless_result is None else dict(self.headless_result),
            "stop_result": None if self.stop_result is None else dict(self.stop_result),
            "last_verify_result": (
                None if self.last_verify_result is None else dict(self.last_verify_result)
            ),
            "failure": self.failure,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> PersistedDemoState:
        """Build one persisted state model from a JSON object."""

        return cls(
            active=bool(payload.get("active")),
            repo_root=str(payload["repo_root"]),
            pack_dir=str(payload["pack_dir"]),
            run_root=str(payload["run_root"]),
            provider=str(payload["provider"]),
            tool=str(payload["tool"]),
            agent_profile=str(payload["agent_profile"]),
            agent_def_dir=str(payload["agent_def_dir"]),
            started_at_utc=str(payload["started_at_utc"]),
            updated_at_utc=str(payload["updated_at_utc"]),
            steps={str(key): bool(value) for key, value in dict(payload.get("steps", {})).items()},
            config=dict(payload.get("config", {})),
            preflight=dict(payload.get("preflight", {})),
            authorities=dict(payload.get("authorities", {})),
            shared_agent=dict(payload.get("shared_agent", {})),
            headless_agent=(
                None
                if payload.get("headless_agent") is None
                else dict(payload.get("headless_agent", {}))
            ),
            inspect_result=(
                None
                if payload.get("inspect_result") is None
                else dict(payload.get("inspect_result", {}))
            ),
            gateway_result=(
                None
                if payload.get("gateway_result") is None
                else dict(payload.get("gateway_result", {}))
            ),
            headless_result=(
                None
                if payload.get("headless_result") is None
                else dict(payload.get("headless_result", {}))
            ),
            stop_result=(
                None
                if payload.get("stop_result") is None
                else dict(payload.get("stop_result", {}))
            ),
            last_verify_result=(
                None
                if payload.get("last_verify_result") is None
                else dict(payload.get("last_verify_result", {}))
            ),
            failure=payload.get("failure"),
        )

