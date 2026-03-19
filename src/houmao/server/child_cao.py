"""Child `cao-server` lifecycle management for `houmao-server`."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from houmao.cao.server_launcher import (
    CaoServerLauncherConfig,
    CaoServerLauncherConfigOverrides,
    CaoServerOwnership,
    CaoServerStartResult,
    CaoServerStatusResult,
    CaoServerStopResult,
    ProxyPolicy,
    load_cao_server_launcher_config,
    read_cao_server_ownership,
    resolve_cao_server_runtime_artifacts,
    start_cao_server,
    status_cao_server,
    stop_cao_server,
)

from .config import HoumaoServerConfig


@dataclass(frozen=True)
class ChildCaoInstance:
    """Resolved child-CAO runtime metadata."""

    config: CaoServerLauncherConfig
    ownership: CaoServerOwnership | None
    status: CaoServerStatusResult


class ChildCaoManager:
    """Manage one derived-port child `cao-server` instance."""

    def __init__(self, *, config: HoumaoServerConfig) -> None:
        self.m_config = config

    def ensure_launcher_config(self) -> CaoServerLauncherConfig:
        """Materialize the child launcher config and return the parsed config."""

        config_path = self.m_config.child_launcher_config_path
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            "\n".join(
                (
                    f'base_url = "{self.m_config.child_api_base_url}"',
                    f'runtime_root = "{self.m_config.child_runtime_root}"',
                    'proxy_policy = "clear"',
                    f"startup_timeout_seconds = {self.m_config.child_startup_timeout_seconds}",
                    "",
                )
            ),
            encoding="utf-8",
        )
        return load_cao_server_launcher_config(
            config_path,
            overrides=CaoServerLauncherConfigOverrides(proxy_policy=ProxyPolicy.CLEAR),
        )

    def start(self) -> CaoServerStartResult:
        """Start or reuse the child CAO process."""

        launcher_config = self.ensure_launcher_config()
        return start_cao_server(launcher_config)

    def stop(self) -> CaoServerStopResult:
        """Stop the child CAO process when tracking exists."""

        launcher_config = self.ensure_launcher_config()
        return stop_cao_server(launcher_config)

    def inspect(self) -> ChildCaoInstance:
        """Return current child-CAO status and ownership metadata."""

        launcher_config = self.ensure_launcher_config()
        artifacts = resolve_cao_server_runtime_artifacts(launcher_config)
        ownership = None
        if artifacts.ownership_file.is_file():
            ownership = read_cao_server_ownership(artifacts.ownership_file)
        return ChildCaoInstance(
            config=launcher_config,
            ownership=ownership,
            status=status_cao_server(launcher_config),
        )

    def ownership_file_path(self) -> Path:
        """Return the current child ownership artifact path."""

        launcher_config = self.ensure_launcher_config()
        return resolve_cao_server_runtime_artifacts(launcher_config).ownership_file
