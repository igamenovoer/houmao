from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest

from houmao.agents.model_mapping_policy import (
    project_reasoning_level,
    resolve_reasoning_mapping,
    temporary_project_model_config,
)
from houmao.agents.model_selection import ModelConfig, ModelReasoningConfig


def test_resolve_reasoning_mapping_claude_clamps_max_when_model_does_not_support_it() -> None:
    mapping = resolve_reasoning_mapping(
        tool="claude",
        requested_level=10,
        model_name="claude-sonnet-4-5",
    )

    assert mapping["requested_level"] == 10
    assert mapping["effective_level"] == 3
    assert mapping["native_scale"] == "effortLevel"
    assert mapping["native_value"] == "high"
    assert mapping["saturated"] is True
    assert mapping["off_requested"] is False


@pytest.mark.parametrize(
    "model_name",
    ("gpt-5.4", "gpt-5.4-mini", "gpt-5.3-codex", "gpt-5.2-codex"),
)
def test_resolve_reasoning_mapping_codex_uses_model_aware_supported_buckets(
    model_name: str,
) -> None:
    lowest = resolve_reasoning_mapping(
        tool="codex",
        requested_level=1,
        model_name=model_name,
    )
    highest = resolve_reasoning_mapping(
        tool="codex",
        requested_level=10,
        model_name=model_name,
    )
    intermediate = resolve_reasoning_mapping(
        tool="codex",
        requested_level=7,
        model_name=model_name,
    )

    assert lowest["native_value"] == "low"
    assert lowest["effective_level"] == 1
    assert highest["native_value"] == "xhigh"
    assert highest["effective_level"] == 4
    assert highest["saturated"] is True
    assert intermediate["native_value"] == "xhigh"
    assert intermediate["effective_level"] == 4
    assert intermediate["saturated"] is True


def test_resolve_reasoning_mapping_codex_rejects_off_when_model_ladder_lacks_zero() -> None:
    with pytest.raises(ValueError, match="does not support reasoning level 0"):
        resolve_reasoning_mapping(
            tool="codex",
            requested_level=0,
            model_name="gpt-5.4",
        )


@pytest.mark.parametrize(
    ("model_name", "requested_level", "expected_value", "expected_saturated"),
    (
        ("gpt-5.6", 1, "low", False),
        ("gpt-5.6", 6, "ultra", False),
        ("gpt-5.6-sol", 2, "medium", False),
        ("gpt-5.6-sol-2026-07-11", 3, "high", False),
        ("gpt-5.6-terra", 4, "xhigh", False),
        ("gpt-5.6-terra", 5, "max", False),
        ("gpt-5.6-terra", 6, "ultra", False),
        ("gpt-5.6-sol", 12, "ultra", True),
        ("gpt-5.6-luna", 1, "low", False),
        ("gpt-5.6-luna", 5, "max", False),
        ("gpt-5.6-luna", 6, "max", True),
    ),
)
def test_resolve_reasoning_mapping_codex_gpt_5_6_catalog_ladders(
    model_name: str,
    requested_level: int,
    expected_value: str,
    expected_saturated: bool,
) -> None:
    mapping = resolve_reasoning_mapping(
        tool="codex",
        requested_level=requested_level,
        model_name=model_name,
    )

    assert mapping["native_value"] == expected_value
    assert mapping["saturated"] is expected_saturated


@pytest.mark.parametrize("model_name", ("gpt-5.6", "gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna"))
def test_resolve_reasoning_mapping_codex_gpt_5_6_rejects_off(model_name: str) -> None:
    with pytest.raises(ValueError, match="does not support reasoning level 0"):
        resolve_reasoning_mapping(
            tool="codex",
            requested_level=0,
            model_name=model_name,
        )


def test_resolve_reasoning_mapping_claude_rejects_off_when_ladder_lacks_zero() -> None:
    with pytest.raises(ValueError, match="does not support reasoning level 0"):
        resolve_reasoning_mapping(
            tool="claude",
            requested_level=0,
            model_name="claude-sonnet-4-5",
        )


def test_project_reasoning_level_writes_claude_effort_cli_metadata(tmp_path: Path) -> None:
    home_path = (tmp_path / "claude-home").resolve()

    mapping = project_reasoning_level(
        home_path=home_path,
        tool="claude",
        requested_level=3,
        model_name="claude-sonnet-4-5",
    )

    payload = json.loads((home_path / "settings.json").read_text(encoding="utf-8"))

    assert mapping["native_scale"] == "effortLevel"
    assert mapping["native_value"] == "high"
    assert mapping["cli_args"] == ["--effort", "high"]
    assert payload["effortLevel"] == "high"


def test_project_reasoning_level_writes_codex_model_aware_reasoning_effort(
    tmp_path: Path,
) -> None:
    home_path = (tmp_path / "codex-home").resolve()

    mapping = project_reasoning_level(
        home_path=home_path,
        tool="codex",
        requested_level=1,
        model_name="gpt-5.4",
    )

    payload = tomllib.loads((home_path / "config.toml").read_text(encoding="utf-8"))

    assert mapping["native_scale"] == "model_reasoning_effort"
    assert mapping["native_value"] == "low"
    assert mapping["cli_args"] == ['--config=model_reasoning_effort="low"']
    assert payload["model_reasoning_effort"] == "low"


def test_temporary_project_model_config_claude_uses_cli_args_without_persisting(
    tmp_path: Path,
) -> None:
    home_path = (tmp_path / "claude-home").resolve()
    settings_path = home_path / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text('{"effortLevel":"low"}\n', encoding="utf-8")

    with temporary_project_model_config(
        home_path=home_path,
        tool="claude",
        model_config=ModelConfig(
            name="sonnet",
            reasoning=ModelReasoningConfig(level=3),
        ),
    ) as projection:
        assert projection.env == {}
        assert projection.args == ["--model", "sonnet", "--effort", "high"]
        assert json.loads(settings_path.read_text(encoding="utf-8"))["effortLevel"] == "high"

    assert json.loads(settings_path.read_text(encoding="utf-8"))["effortLevel"] == "low"


def test_project_reasoning_level_kimi_uses_effective_alias_efforts(tmp_path: Path) -> None:
    home_path = (tmp_path / "kimi-home").resolve()
    config_path = home_path / "config.toml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        """default_model = "kimi-code/kimi-for-coding"

[models."kimi-code/kimi-for-coding"]
provider = "managed:kimi-code"
model = "kimi-for-coding"
max_context_size = 262144
capabilities = ["thinking"]
support_efforts = ["low", "medium", "high"]

[models."kimi-code/kimi-for-coding".overrides]
support_efforts = ["low", "high", "max"]
""",
        encoding="utf-8",
    )

    mapping = project_reasoning_level(
        home_path=home_path,
        tool="kimi",
        requested_level=2,
        model_name="kimi-code/kimi-for-coding",
    )
    payload = tomllib.loads(config_path.read_text(encoding="utf-8"))

    assert mapping["effective_level"] == 2
    assert mapping["saturated"] is False
    assert [item["native_value"] for item in mapping["native_settings"]] == [True, "high"]
    assert payload["thinking"] == {"enabled": True, "effort": "high"}


def test_project_reasoning_level_kimi_saturates_to_alias_max(tmp_path: Path) -> None:
    home_path = (tmp_path / "kimi-home").resolve()
    config_path = home_path / "config.toml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        """default_model = "custom"

[models.custom]
provider = "custom"
model = "custom"
max_context_size = 1000
capabilities = ["thinking"]
support_efforts = ["low", "max"]
""",
        encoding="utf-8",
    )

    mapping = project_reasoning_level(
        home_path=home_path,
        tool="kimi",
        requested_level=9,
        model_name=None,
    )

    assert mapping["effective_level"] == 2
    assert mapping["saturated"] is True
    assert mapping["native_settings"][1]["native_value"] == "max"


def test_project_reasoning_level_kimi_zero_disables_optional_thinking(tmp_path: Path) -> None:
    home_path = (tmp_path / "kimi-home").resolve()
    config_path = home_path / "config.toml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        """default_model = "custom"

[models.custom]
provider = "custom"
model = "custom"
max_context_size = 1000
capabilities = ["thinking"]
support_efforts = ["low"]

[thinking]
enabled = true
effort = "low"
""",
        encoding="utf-8",
    )

    mapping = project_reasoning_level(
        home_path=home_path,
        tool="kimi",
        requested_level=0,
        model_name=None,
    )
    payload = tomllib.loads(config_path.read_text(encoding="utf-8"))

    assert mapping["off_requested"] is True
    assert payload["thinking"]["enabled"] is False
    assert payload["thinking"]["effort"] == "low"


def test_resolve_reasoning_mapping_kimi_always_thinking_rejects_zero(tmp_path: Path) -> None:
    home_path = (tmp_path / "kimi-home").resolve()
    config_path = home_path / "config.toml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        """default_model = "custom"

[models.custom]
provider = "custom"
model = "custom"
max_context_size = 1000
capabilities = ["thinking", "always_thinking"]
support_efforts = ["low", "high"]
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="does not support reasoning level 0"):
        resolve_reasoning_mapping(
            tool="kimi",
            requested_level=0,
            model_name=None,
            home_path=home_path,
        )


def test_resolve_reasoning_mapping_kimi_missing_efforts_rejects_positive(
    tmp_path: Path,
) -> None:
    home_path = (tmp_path / "kimi-home").resolve()
    config_path = home_path / "config.toml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        """default_model = "custom"

[models.custom]
provider = "custom"
model = "custom"
max_context_size = 1000
capabilities = ["thinking"]
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="exposes no positive reasoning presets"):
        resolve_reasoning_mapping(
            tool="kimi",
            requested_level=1,
            model_name=None,
            home_path=home_path,
        )


def test_resolve_reasoning_mapping_kimi_env_model_rejects_normalized_level(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="exposes no ordered effort catalog"):
        resolve_reasoning_mapping(
            tool="kimi",
            requested_level=1,
            model_name="kimi-env",
            home_path=tmp_path,
            env_model_values={
                "KIMI_MODEL_NAME": "kimi-env",
                "KIMI_MODEL_THINKING_EFFORT": "high",
            },
        )


def test_temporary_project_model_config_kimi_restores_thinking_state(tmp_path: Path) -> None:
    home_path = (tmp_path / "kimi-home").resolve()
    config_path = home_path / "config.toml"
    config_path.parent.mkdir(parents=True)
    original = """default_model = "custom"

[models.custom]
provider = "custom"
model = "custom"
max_context_size = 1000
capabilities = ["thinking"]
support_efforts = ["low", "high"]

[thinking]
enabled = true
effort = "low"
"""
    config_path.write_text(original, encoding="utf-8")

    with temporary_project_model_config(
        home_path=home_path,
        tool="kimi",
        model_config=ModelConfig(reasoning=ModelReasoningConfig(level=2)),
    ) as projection:
        assert projection.env == {}
        assert projection.args == []
        assert (
            tomllib.loads(config_path.read_text(encoding="utf-8"))["thinking"]["effort"] == "high"
        )

    assert config_path.read_text(encoding="utf-8") == original
