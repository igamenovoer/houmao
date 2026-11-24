"""Tests for the packaged starter Kimi tool adapter."""

from pathlib import Path

import yaml

from houmao.agents.kimi_launch_env import KIMI_CONFIG_ENV_NAMES, KIMI_PRIVATE_ENV_NAMES


_WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
_ADAPTER_PATH = _WORKSPACE_ROOT / "src/houmao/project/assets/starter_agents/tools/kimi/adapter.yaml"


def test_starter_kimi_adapter_allows_only_private_environment_inputs() -> None:
    """Keep config-owned settings outside the adapter credential allowlist."""

    payload = yaml.safe_load(_ADAPTER_PATH.read_text(encoding="utf-8"))
    allowlist = set(payload["auth_projection"]["env"]["allowlist"])

    assert allowlist == KIMI_PRIVATE_ENV_NAMES
    assert allowlist.isdisjoint(KIMI_CONFIG_ENV_NAMES)
