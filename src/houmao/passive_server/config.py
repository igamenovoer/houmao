"""Configuration model for the passive server."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator

from houmao.project import resolve_project_aware_runtime_root

_DEFAULT_API_BASE_URL = "http://127.0.0.1:9891"


def _normalize_base_url(url: str) -> str:
    """Strip trailing slash and validate scheme."""

    url = url.rstrip("/")
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https"):
        raise ValueError(f"api_base_url scheme must be http or https, got {parts.scheme!r}")
    if not parts.hostname:
        raise ValueError("api_base_url must include a hostname")
    return url


class PassiveServerConfig(BaseModel):
    """Resolved passive-server configuration."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    api_base_url: str = Field(default=_DEFAULT_API_BASE_URL)
    runtime_root: Path = Field(
        default_factory=lambda: resolve_project_aware_runtime_root(cwd=Path.cwd().resolve())
    )
    discovery_poll_interval_seconds: float = Field(default=5.0, gt=0.0)
    observation_poll_interval_seconds: float = Field(default=2.0, ge=0.5)

    @field_validator("api_base_url")
    @classmethod
    def _validate_api_base_url(cls, value: str) -> str:
        return _normalize_base_url(value)

    @field_validator("runtime_root")
    @classmethod
    def _validate_runtime_root(cls, value: Path) -> Path:
        return value.expanduser().resolve()

    # -- derived properties --------------------------------------------------

    @property
    def public_host(self) -> str:
        """Return the normalized public listener host."""

        return urlsplit(self.api_base_url).hostname or "127.0.0.1"

    @property
    def public_port(self) -> int:
        """Return the normalized public listener port."""

        port = urlsplit(self.api_base_url).port
        return port if port is not None else 80

    @property
    def server_root(self) -> Path:
        """Return the server-specific root directory."""

        return (
            self.runtime_root / "houmao_servers" / f"{self.public_host}-{self.public_port}"
        ).resolve()

    @property
    def run_dir(self) -> Path:
        """Return the server run-state directory."""

        return (self.server_root / "run").resolve()

    @property
    def current_instance_path(self) -> Path:
        """Return the on-disk current-instance metadata path."""

        return (self.run_dir / "current-instance.json").resolve()

    @property
    def managed_agents_root(self) -> Path:
        """Return the root directory for managed headless agent persistence."""

        return (self.server_root / "managed_agents").resolve()
