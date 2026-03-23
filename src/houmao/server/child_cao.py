"""Child `cao-server` lifecycle management for `houmao-server`."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess

from houmao.cao.server_launcher import (
    CaoServerLauncherConfig,
    CaoServerLauncherConfigOverrides,
    CaoServerOwnership,
    CaoServerStartResult,
    CaoServerStatusResult,
    CaoServerStopResult,
    ProxyPolicy,
    build_cao_server_environment,
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


@dataclass(frozen=True)
class ChildCaoInstallResult:
    """Outcome of a pair-owned agent-profile install command."""

    agent_source: str
    provider: str
    working_directory: Path | None
    returncode: int
    stdout: str
    stderr: str


class ChildCaoInstallError(RuntimeError):
    """Raised when pair-owned install cannot be attempted safely."""


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

    def install_agent_profile(
        self,
        *,
        agent_source: str,
        provider: str,
        working_directory: Path | None = None,
    ) -> ChildCaoInstallResult:
        """Install one agent profile into the managed child-CAO home."""

        launcher_config = self.ensure_launcher_config()
        executable = shutil.which("cao")
        if executable is None:
            raise ChildCaoInstallError("`cao` is not available on PATH for pair-owned install.")

        resolved_working_directory: Path | None = None
        if working_directory is not None:
            resolved_working_directory = working_directory.expanduser().resolve()
            if not resolved_working_directory.exists() or not resolved_working_directory.is_dir():
                raise ChildCaoInstallError(
                    "Pair-owned install requires an existing working directory when one is "
                    f"provided: `{resolved_working_directory}`."
                )

        completed = subprocess.run(
            [executable, "install", agent_source, "--provider", provider],
            check=False,
            capture_output=True,
            cwd=str(resolved_working_directory) if resolved_working_directory is not None else None,
            env=build_cao_server_environment(
                proxy_policy=launcher_config.proxy_policy,
                home_dir=launcher_config.home_dir,
                base_url=launcher_config.base_url,
            ),
            text=True,
        )
        return ChildCaoInstallResult(
            agent_source=agent_source,
            provider=provider,
            working_directory=resolved_working_directory,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
