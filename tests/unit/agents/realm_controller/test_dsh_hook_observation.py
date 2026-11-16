"""Keep non-hook native providers outside terminal hook collector cleanup."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from houmao.agents.realm_controller.hook_observation_launch import stop_hook_observation


@pytest.mark.parametrize("tool", ["dsh", "claude", "codex", "kimi"])
def test_stop_only_addresses_a_tool_with_a_hook_adapter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, tool: str
) -> None:
    """Stopping DSH skips hook paths while existing hook-capable tools retain cleanup."""

    collector = Mock()
    monkeypatch.setattr(
        "houmao.agents.realm_controller.hook_observation_launch.stop_collector", collector
    )
    stop_hook_observation(tmp_path, tool=tool)
    if tool == "dsh":
        collector.assert_not_called()
    else:
        collector.assert_called_once_with(tmp_path, tool=tool)
    assert not (tmp_path / "hook-observation").exists()
