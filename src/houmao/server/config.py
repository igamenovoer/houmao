"""Configuration models for the Houmao HTTP server."""

from __future__ import annotations

from pathlib import Path
from urllib import parse

from pydantic import BaseModel, ConfigDict, Field, field_validator

from houmao.cao.no_proxy import extract_cao_base_url_host_port, normalize_cao_base_url
from houmao.owned_paths import resolve_runtime_root

_DEFAULT_SUPPORTED_TUI_PROCESSES: dict[str, tuple[str, ...]] = {
    "claude": ("claude", "claude-code"),
    "codex": ("codex",),
}


class HoumaoServerConfig(BaseModel):
    """Resolved server configuration."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    api_base_url: str = Field(default="http://127.0.0.1:9889")
    runtime_root: Path = Field(default_factory=resolve_runtime_root)
    watch_poll_interval_seconds: float = 1.0
    recent_transition_limit: int = 24
    stability_threshold_seconds: float = 1.0
    completion_stability_seconds: float = 1.0
    unknown_to_stalled_timeout_seconds: float = 30.0
    supported_tui_processes: dict[str, tuple[str, ...]] = Field(
        default_factory=lambda: dict(_DEFAULT_SUPPORTED_TUI_PROCESSES)
    )
    child_startup_timeout_seconds: float = 15.0
    startup_child: bool = True

    @field_validator("api_base_url")
    @classmethod
    def _validate_api_base_url(cls, value: str) -> str:
        return normalize_cao_base_url(value)

    @field_validator("runtime_root")
    @classmethod
    def _validate_runtime_root(cls, value: Path) -> Path:
        return value.expanduser().resolve()

    @field_validator(
        "watch_poll_interval_seconds",
        "stability_threshold_seconds",
        "completion_stability_seconds",
        "unknown_to_stalled_timeout_seconds",
        "child_startup_timeout_seconds",
    )
    @classmethod
    def _validate_positive_float(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("must be > 0")
        return value

    @field_validator("recent_transition_limit")
    @classmethod
    def _validate_recent_transition_limit(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("must be > 0")
        return value

    @field_validator("supported_tui_processes")
    @classmethod
    def _validate_supported_tui_processes(
        cls, value: dict[str, tuple[str, ...]]
    ) -> dict[str, tuple[str, ...]]:
        normalized: dict[str, tuple[str, ...]] = {}
        for tool, names in value.items():
            normalized_tool = tool.strip()
            if not normalized_tool:
                raise ValueError("supported_tui_processes keys must not be empty")
            normalized_names = tuple(name.strip() for name in names if name.strip())
            if not normalized_names:
                raise ValueError(
                    f"supported_tui_processes[{normalized_tool!r}] must define at least one process name"
                )
            normalized[normalized_tool] = normalized_names
        return normalized

    @property
    def public_host(self) -> str:
        """Return the normalized public listener host."""

        host, _ = extract_cao_base_url_host_port(self.api_base_url)
        return host

    @property
    def public_port(self) -> int:
        """Return the normalized public listener port."""

        _, port = extract_cao_base_url_host_port(self.api_base_url)
        return port

    @property
    def child_api_base_url(self) -> str:
        """Return the derived child CAO base URL."""

        child_port = self.public_port + 1
        return f"http://127.0.0.1:{child_port}"

    @property
    def server_root(self) -> Path:
        """Return the Houmao-owned server root for this listener."""

        return (
            self.runtime_root / "houmao_servers" / f"{self.public_host}-{self.public_port}"
        ).resolve()

    @property
    def logs_dir(self) -> Path:
        """Return the server log directory."""

        return (self.server_root / "logs").resolve()

    @property
    def run_dir(self) -> Path:
        """Return the server run-state directory."""

        return (self.server_root / "run").resolve()

    @property
    def state_dir(self) -> Path:
        """Return the server state directory."""

        return (self.server_root / "state").resolve()

    @property
    def history_dir(self) -> Path:
        """Return the server history directory."""

        return (self.server_root / "history").resolve()

    @property
    def sessions_dir(self) -> Path:
        """Return the session-registration directory."""

        return (self.server_root / "sessions").resolve()

    @property
    def child_root(self) -> Path:
        """Return the child-CAO ownership root."""

        return (self.server_root / "child_cao").resolve()

    @property
    def child_runtime_root(self) -> Path:
        """Return the child launcher runtime root."""

        return (self.child_root / "runtime").resolve()

    @property
    def child_launcher_config_path(self) -> Path:
        """Return the generated child-launcher TOML path."""

        return (self.child_root / "launcher.toml").resolve()

    @property
    def current_instance_path(self) -> Path:
        """Return the server current-instance path."""

        return (self.run_dir / "current-instance.json").resolve()

    @property
    def pid_path(self) -> Path:
        """Return the server pid path."""

        return (self.run_dir / "houmao-server.pid").resolve()

    @property
    def terminal_state_root(self) -> Path:
        """Return the compatibility state root for per-terminal views."""

        return (self.state_dir / "terminals").resolve()

    @property
    def terminal_history_root(self) -> Path:
        """Return the append-only history root for per-terminal views."""

        return (self.history_dir / "terminals").resolve()

    def child_bind_host(self) -> str:
        """Return the loopback host used for the child CAO listener."""

        return parse.urlsplit(self.child_api_base_url).hostname or "127.0.0.1"
