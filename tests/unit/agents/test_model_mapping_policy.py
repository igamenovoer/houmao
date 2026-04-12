from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest

from houmao.agents.model_mapping_policy import project_reasoning_level, resolve_reasoning_mapping


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


def test_resolve_reasoning_mapping_claude_rejects_off_when_ladder_lacks_zero() -> None:
    with pytest.raises(ValueError, match="does not support reasoning level 0"):
        resolve_reasoning_mapping(
            tool="claude",
            requested_level=0,
            model_name="claude-sonnet-4-5",
        )


def test_project_reasoning_level_writes_gemini_3_thinking_level(tmp_path: Path) -> None:
    home_path = (tmp_path / "gemini-home").resolve()

    mapping = project_reasoning_level(
        home_path=home_path,
        tool="gemini",
        requested_level=8,
        model_name="gemini-3-pro-preview",
    )

    settings_path = home_path / ".gemini" / "settings.json"
    payload = json.loads(settings_path.read_text(encoding="utf-8"))

    assert mapping["effective_level"] == 3
    assert mapping["saturated"] is True
    assert mapping["native_settings"] == [
        {
            "native_scale": "thinkingLevel",
            "native_value": "HIGH",
            "projection_target": {
                "surface": "json",
                "path": ".gemini/settings.json",
                "key_path": [
                    "modelConfigs",
                    "customOverrides",
                    0,
                    "modelConfig",
                    "generateContentConfig",
                    "thinkingConfig",
                    "thinkingLevel",
                ],
            },
        },
        {
            "native_scale": "thinkingBudget",
            "native_value": 16384,
            "projection_target": {
                "surface": "json",
                "path": ".gemini/settings.json",
                "key_path": [
                    "modelConfigs",
                    "customOverrides",
                    0,
                    "modelConfig",
                    "generateContentConfig",
                    "thinkingConfig",
                    "thinkingBudget",
                ],
            },
        },
    ]
    assert payload["modelConfigs"]["customOverrides"][0] == {
        "match": {"model": "gemini-3-pro-preview"},
        "modelConfig": {
            "generateContentConfig": {
                "thinkingConfig": {
                    "thinkingLevel": "HIGH",
                    "thinkingBudget": 16384,
                }
            }
        },
    }


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
