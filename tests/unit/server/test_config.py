from __future__ import annotations

from pathlib import Path

from houmao.server.config import HoumaoServerConfig


def test_houmao_server_config_derives_child_url_and_roots(tmp_path: Path) -> None:
    config = HoumaoServerConfig(
        api_base_url="http://127.0.0.1:9889",
        runtime_root=tmp_path,
    )

    assert config.public_host == "127.0.0.1"
    assert config.public_port == 9889
    assert config.child_api_base_url == "http://127.0.0.1:9890"
    assert config.server_root == tmp_path / "houmao_servers" / "127.0.0.1-9889"
    assert config.child_root == config.server_root / "child_cao"
    assert config.current_instance_path == config.server_root / "run" / "current-instance.json"
    assert config.terminal_state_root == config.server_root / "state" / "terminals"
    assert config.terminal_history_root == config.server_root / "history" / "terminals"
