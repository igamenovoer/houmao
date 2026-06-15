"""Tests for ``PassiveServerConfig``."""

from __future__ import annotations

from pathlib import Path

import pytest

from houmao.owned_paths import (
    HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR,
    HOUMAO_GLOBAL_RUNTIME_DIR_ENV_VAR,
)
from houmao.passive_server.config import PassiveServerConfig


class TestDefaults:
    """Default configuration values."""

    def test_default_api_base_url(self) -> None:
        config = PassiveServerConfig()
        assert config.api_base_url == "http://127.0.0.1:9891"

    def test_default_runtime_root_is_absolute(self) -> None:
        config = PassiveServerConfig()
        assert config.runtime_root.is_absolute()

    def test_default_registry_root_is_absolute(self) -> None:
        config = PassiveServerConfig()
        assert config.registry_root.is_absolute()

    def test_default_port(self) -> None:
        config = PassiveServerConfig()
        assert config.public_port == 9891

    def test_default_host(self) -> None:
        config = PassiveServerConfig()
        assert config.public_host == "127.0.0.1"

    def test_default_discovery_poll_interval(self) -> None:
        config = PassiveServerConfig()
        assert config.discovery_poll_interval_seconds == 5.0

    def test_default_observation_poll_interval(self) -> None:
        config = PassiveServerConfig()
        assert config.observation_poll_interval_seconds == 2.0


class TestNormalization:
    """URL normalization and path resolution."""

    def test_trailing_slash_stripped(self) -> None:
        config = PassiveServerConfig(api_base_url="http://127.0.0.1:9891/")
        assert config.api_base_url == "http://127.0.0.1:9891"

    def test_invalid_scheme_rejected(self) -> None:
        with pytest.raises(ValueError, match="scheme"):
            PassiveServerConfig(api_base_url="ftp://localhost:9891")

    def test_custom_discovery_poll_interval(self) -> None:
        config = PassiveServerConfig(discovery_poll_interval_seconds=2.0)
        assert config.discovery_poll_interval_seconds == 2.0

    def test_non_positive_discovery_poll_interval_rejected(self) -> None:
        with pytest.raises(ValueError):
            PassiveServerConfig(discovery_poll_interval_seconds=0.0)

    def test_negative_discovery_poll_interval_rejected(self) -> None:
        with pytest.raises(ValueError):
            PassiveServerConfig(discovery_poll_interval_seconds=-1.0)

    def test_custom_observation_poll_interval(self) -> None:
        config = PassiveServerConfig(observation_poll_interval_seconds=3.0)
        assert config.observation_poll_interval_seconds == 3.0

    def test_observation_poll_interval_below_minimum_rejected(self) -> None:
        with pytest.raises(ValueError):
            PassiveServerConfig(observation_poll_interval_seconds=0.1)

    def test_observation_poll_interval_at_minimum(self) -> None:
        config = PassiveServerConfig(observation_poll_interval_seconds=0.5)
        assert config.observation_poll_interval_seconds == 0.5

    def test_runtime_root_resolved_to_absolute(self, tmp_path: Path) -> None:
        config = PassiveServerConfig(runtime_root=tmp_path / "relative" / "..")
        assert config.runtime_root.is_absolute()
        assert config.runtime_root == tmp_path.resolve()

    def test_registry_root_resolved_to_absolute(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.chdir(tmp_path)

        config = PassiveServerConfig(registry_root=Path("registry") / ".." / "custom-registry")

        assert config.registry_root.is_absolute()
        assert config.registry_root == (tmp_path / "custom-registry").resolve()

    def test_default_roots_follow_global_env_without_project_overlay(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        cwd = tmp_path / "plain-workdir"
        runtime_root = tmp_path / "global-runtime"
        registry_root = tmp_path / "global-registry"
        cwd.mkdir()
        monkeypatch.chdir(cwd)
        monkeypatch.setenv(HOUMAO_GLOBAL_RUNTIME_DIR_ENV_VAR, str(runtime_root))
        monkeypatch.setenv(HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR, str(registry_root))

        config = PassiveServerConfig()

        assert not (cwd / ".houmao").exists()
        assert config.runtime_root == runtime_root.resolve()
        assert config.registry_root == registry_root.resolve()

    def test_default_roots_use_global_defaults_without_project_overlay(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        cwd = tmp_path / "plain-workdir"
        fake_config_path = tmp_path / "config" / "houmao"
        cwd.mkdir()
        monkeypatch.chdir(cwd)
        monkeypatch.delenv(HOUMAO_GLOBAL_RUNTIME_DIR_ENV_VAR, raising=False)
        monkeypatch.delenv(HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR, raising=False)
        monkeypatch.setattr(
            "houmao.owned_paths.platformdirs.user_config_path",
            lambda **_kwargs: fake_config_path,
        )

        config = PassiveServerConfig()

        assert not (cwd / ".houmao").exists()
        assert config.runtime_root == (fake_config_path / "runtime").resolve()
        assert config.registry_root == (fake_config_path / "registry").resolve()

    def test_registry_helper_env_uses_configured_registry_root(self, tmp_path: Path) -> None:
        config = PassiveServerConfig(registry_root=tmp_path / "registry")

        assert config.registry_helper_env() == {
            HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR: str((tmp_path / "registry").resolve())
        }


class TestDerivedProperties:
    """Derived property computation."""

    def test_server_root_follows_convention(self, tmp_path: Path) -> None:
        config = PassiveServerConfig(
            api_base_url="http://0.0.0.0:9895",
            runtime_root=tmp_path,
        )
        expected = (tmp_path / "houmao_servers" / "0.0.0.0-9895").resolve()
        assert config.server_root == expected

    def test_run_dir_under_server_root(self, tmp_path: Path) -> None:
        config = PassiveServerConfig(runtime_root=tmp_path)
        assert config.run_dir == (config.server_root / "run").resolve()

    def test_current_instance_path_under_run_dir(self, tmp_path: Path) -> None:
        config = PassiveServerConfig(runtime_root=tmp_path)
        assert config.current_instance_path == (config.run_dir / "current-instance.json").resolve()

    def test_host_port_extraction(self) -> None:
        config = PassiveServerConfig(api_base_url="http://10.0.0.5:8080")
        assert config.public_host == "10.0.0.5"
        assert config.public_port == 8080
