"""Tests for ``PassiveServerConfig``."""

from __future__ import annotations

from pathlib import Path

import pytest

from houmao.passive_server.config import PassiveServerConfig


class TestDefaults:
    """Default configuration values."""

    def test_default_api_base_url(self) -> None:
        config = PassiveServerConfig()
        assert config.api_base_url == "http://127.0.0.1:9891"

    def test_default_runtime_root_is_absolute(self) -> None:
        config = PassiveServerConfig()
        assert config.runtime_root.is_absolute()

    def test_default_port(self) -> None:
        config = PassiveServerConfig()
        assert config.public_port == 9891

    def test_default_host(self) -> None:
        config = PassiveServerConfig()
        assert config.public_host == "127.0.0.1"

    def test_default_discovery_poll_interval(self) -> None:
        config = PassiveServerConfig()
        assert config.discovery_poll_interval_seconds == 5.0


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

    def test_runtime_root_resolved_to_absolute(self, tmp_path: Path) -> None:
        config = PassiveServerConfig(runtime_root=tmp_path / "relative" / "..")
        assert config.runtime_root.is_absolute()
        assert config.runtime_root == tmp_path.resolve()


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
