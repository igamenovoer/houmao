"""Tests for the packaged starter Kimi tool adapter."""

from pathlib import Path

import yaml


_WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
_ADAPTER_PATH = _WORKSPACE_ROOT / "src/houmao/project/assets/starter_agents/tools/kimi/adapter.yaml"


def test_starter_kimi_adapter_uses_current_model_environment_allowlist() -> None:
    payload = yaml.safe_load(_ADAPTER_PATH.read_text(encoding="utf-8"))
    allowlist = set(payload["auth_projection"]["env"]["allowlist"])

    assert {
        "KIMI_MODEL_THINKING_KEEP",
        "KIMI_MODEL_TEMPERATURE",
        "KIMI_MODEL_TOP_P",
        "KIMI_MODEL_MAX_TOKENS",
        "KIMI_MODEL_MAX_COMPLETION_TOKENS",
    } <= allowlist
    assert "KIMI_MODEL_DEFAULT_THINKING" not in allowlist
    assert "KIMI_MODEL_THINKING_MODE" not in allowlist
