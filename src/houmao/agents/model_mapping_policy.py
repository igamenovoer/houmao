"""Native reasoning-mapping policy for unified model selection."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
import json
from pathlib import Path
from typing import Any, TypeVar

from houmao.agents.launch_policy.provider_hooks import (
    provider_state_mutation_lock,
    set_json_key,
    set_toml_key,
)
from houmao.agents.model_selection import ModelConfig

_CLAUDE_SETTINGS_FILENAME = "settings.json"
_CODEX_CONFIG_FILENAME = "config.toml"
_GEMINI_SETTINGS_PATH = Path(".gemini") / "settings.json"
_NativeBucketT = TypeVar("_NativeBucketT")


def resolve_reasoning_mapping(
    *,
    tool: str,
    requested_level: int,
    model_name: str | None,
    tool_version: str | None = None,
) -> dict[str, Any]:
    """Resolve one normalized reasoning level into native tool state."""

    if tool == "claude":
        native_value = _map_claude_effort(requested_level=requested_level, model_name=model_name)
        clamped = requested_level == 10 and native_value != "max"
        return {
            "tool": tool,
            "tool_version": tool_version,
            "requested_level": requested_level,
            "model_name": model_name,
            "native_scale": "effortLevel",
            "native_value": native_value,
            "clamped": clamped,
            "projection_target": {
                "surface": "json",
                "path": _CLAUDE_SETTINGS_FILENAME,
                "key_path": ["effortLevel"],
            },
        }

    if tool == "codex":
        native_value = _bucket_by_level(
            requested_level=requested_level,
            native_values=("none", "minimal", "low", "medium", "high", "xhigh"),
        )
        return {
            "tool": tool,
            "tool_version": tool_version,
            "requested_level": requested_level,
            "model_name": model_name,
            "native_scale": "model_reasoning_effort",
            "native_value": native_value,
            "clamped": True,
            "projection_target": {
                "surface": "toml",
                "path": _CODEX_CONFIG_FILENAME,
                "key_path": ["model_reasoning_effort"],
            },
        }

    if tool == "gemini":
        return _resolve_gemini_reasoning_mapping(
            requested_level=requested_level,
            model_name=model_name,
            tool_version=tool_version,
        )

    raise ValueError(f"Unsupported model-mapping tool {tool!r}")


def project_reasoning_level(
    *,
    home_path: Path,
    tool: str,
    requested_level: int,
    model_name: str | None,
    tool_version: str | None = None,
) -> dict[str, Any]:
    """Project one normalized reasoning level into the runtime home."""

    mapping = resolve_reasoning_mapping(
        tool=tool,
        requested_level=requested_level,
        model_name=model_name,
        tool_version=tool_version,
    )
    if tool == "claude":
        set_json_key(
            path=home_path / _CLAUDE_SETTINGS_FILENAME,
            key_path=("effortLevel",),
            value=str(mapping["native_value"]),
            repair_invalid=True,
        )
        return mapping

    if tool == "codex":
        set_toml_key(
            path=home_path / _CODEX_CONFIG_FILENAME,
            key_path=("model_reasoning_effort",),
            value=str(mapping["native_value"]),
            repair_invalid=True,
        )
        return mapping

    if tool == "gemini":
        settings_path = home_path / _GEMINI_SETTINGS_PATH
        _project_gemini_reasoning(
            settings_path=settings_path,
            requested_model_name=model_name,
            mapping=mapping,
        )
        return mapping

    raise ValueError(f"Unsupported model-mapping tool {tool!r}")


def project_model_name(
    *,
    home_path: Path,
    tool: str,
    model_name: str,
    env_exports: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Project one normalized model name into the runtime home or launch env."""

    stripped_model_name = model_name.strip()
    if not stripped_model_name:
        raise ValueError("model_name must not be empty")

    if tool == "claude":
        if env_exports is not None:
            env_exports["ANTHROPIC_MODEL"] = stripped_model_name
        return {
            "surface": "env",
            "env_var": "ANTHROPIC_MODEL",
            "value": stripped_model_name,
        }

    if tool == "codex":
        set_toml_key(
            path=home_path / _CODEX_CONFIG_FILENAME,
            key_path=("model",),
            value=stripped_model_name,
            repair_invalid=True,
        )
        return {
            "surface": "toml",
            "path": _CODEX_CONFIG_FILENAME,
            "key_path": ["model"],
            "value": stripped_model_name,
        }

    if tool == "gemini":
        set_json_key(
            path=home_path / _GEMINI_SETTINGS_PATH,
            key_path=("model", "name"),
            value=stripped_model_name,
            repair_invalid=True,
        )
        return {
            "surface": "json",
            "path": str(_GEMINI_SETTINGS_PATH),
            "key_path": ["model", "name"],
            "value": stripped_model_name,
        }

    raise ValueError(f"Unsupported model-mapping tool {tool!r}")


@contextmanager
def temporary_project_model_config(
    *,
    home_path: Path,
    tool: str,
    model_config: ModelConfig | None,
) -> Iterator[dict[str, str]]:
    """Apply one effective model config for a single headless turn and then restore state."""

    if model_config is None or model_config.is_empty():
        yield {}
        return

    env_exports: dict[str, str] = {}
    mutated_paths = _mutated_model_config_paths(
        home_path=home_path,
        tool=tool,
        model_config=model_config,
    )
    with provider_state_mutation_lock(home_path):
        snapshots = {
            path: path.read_text(encoding="utf-8") if path.exists() else None for path in mutated_paths
        }
        try:
            if model_config.name is not None:
                project_model_name(
                    home_path=home_path,
                    tool=tool,
                    model_name=model_config.name,
                    env_exports=env_exports,
                )
            if model_config.reasoning is not None:
                project_reasoning_level(
                    home_path=home_path,
                    tool=tool,
                    requested_level=model_config.reasoning.level,
                    model_name=model_config.name,
                )
            yield env_exports
        finally:
            _restore_model_config_paths(snapshots)


def _resolve_gemini_reasoning_mapping(
    *,
    requested_level: int,
    model_name: str | None,
    tool_version: str | None,
) -> dict[str, Any]:
    """Resolve one Gemini-native reasoning projection."""

    if _is_gemini_3_model(model_name):
        native_value = _map_gemini_3_thinking_level(requested_level=requested_level)
        return {
            "tool": "gemini",
            "tool_version": tool_version,
            "requested_level": requested_level,
            "model_name": model_name,
            "native_scale": "thinkingLevel",
            "native_value": native_value,
            "clamped": True,
            "projection_target": {
                "surface": "json",
                "path": str(_GEMINI_SETTINGS_PATH),
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
        }

    budget_value = _bucket_by_level(
        requested_level=requested_level,
        native_values=(0, 512, 2048, 4096, 8192, 16384),
    )
    return {
        "tool": "gemini",
        "tool_version": tool_version,
        "requested_level": requested_level,
        "model_name": model_name,
        "native_scale": "thinkingBudget",
        "native_value": budget_value,
        "clamped": True,
        "projection_target": {
            "surface": "json",
            "path": str(_GEMINI_SETTINGS_PATH),
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
    }


def _map_claude_effort(*, requested_level: int, model_name: str | None) -> str:
    """Map one normalized level to a Claude-native effort bucket."""

    if requested_level <= 3:
        return "low"
    if requested_level <= 6:
        return "medium"
    if requested_level <= 9:
        return "high"
    if _claude_model_supports_max(model_name):
        return "max"
    return "high"


def _map_gemini_3_thinking_level(*, requested_level: int) -> str:
    """Map one normalized level to a Gemini 3 thinking level."""

    if requested_level <= 3:
        return "LOW"
    if requested_level <= 7:
        return "MEDIUM"
    return "HIGH"


def _bucket_by_level(
    requested_level: int,
    native_values: tuple[_NativeBucketT, ...],
) -> _NativeBucketT:
    """Resolve one normalized level to the nearest supported native bucket."""

    if len(native_values) == 1:
        return native_values[0]
    scaled_index = round(((requested_level - 1) / 9) * (len(native_values) - 1))
    return native_values[max(0, min(len(native_values) - 1, scaled_index))]


def _claude_model_supports_max(model_name: str | None) -> bool:
    """Return whether one Claude model likely supports `max` effort."""

    if model_name is None:
        return False
    lowered = model_name.lower()
    return "opus-4-6" in lowered


def _is_gemini_3_model(model_name: str | None) -> bool:
    """Return whether one Gemini model uses Gemini 3 thinking-level semantics."""

    if model_name is None:
        return False
    lowered = model_name.lower()
    return lowered.startswith("gemini-3")


def _project_gemini_reasoning(
    *,
    settings_path: Path,
    requested_model_name: str | None,
    mapping: dict[str, Any],
) -> None:
    """Persist one Gemini reasoning override under `modelConfigs.customOverrides`."""

    payload = _load_json_mapping(settings_path)
    effective_model_name = requested_model_name or _extract_model_name(payload) or "auto"
    model_configs = payload.get("modelConfigs")
    if not isinstance(model_configs, dict):
        model_configs = {}
        payload["modelConfigs"] = model_configs

    custom_overrides = model_configs.get("customOverrides")
    if not isinstance(custom_overrides, list):
        custom_overrides = []

    preserved_overrides: list[dict[str, Any]] = []
    for override in custom_overrides:
        if not isinstance(override, dict):
            continue
        match_payload = override.get("match")
        if isinstance(match_payload, dict) and match_payload.get("model") == effective_model_name:
            continue
        preserved_overrides.append(override)

    custom_override = {
        "match": {"model": effective_model_name},
        "modelConfig": {
            "generateContentConfig": {
                "thinkingConfig": {
                    str(mapping["native_scale"]): mapping["native_value"],
                }
            }
        },
    }
    model_configs["customOverrides"] = [custom_override, *preserved_overrides]
    _write_json_mapping(settings_path, payload)


def _extract_model_name(payload: dict[str, Any]) -> str | None:
    """Extract one Gemini model name from a settings payload when present."""

    model_payload = payload.get("model")
    if not isinstance(model_payload, dict):
        return None
    name = model_payload.get("name")
    if not isinstance(name, str) or not name.strip():
        return None
    return name.strip()


def _load_json_mapping(path: Path) -> dict[str, Any]:
    """Load one JSON object from disk, tolerating missing or invalid state."""

    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_json_mapping(path: Path, payload: dict[str, Any]) -> None:
    """Persist one JSON object with stable formatting."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _mutated_model_config_paths(
    *,
    home_path: Path,
    tool: str,
    model_config: ModelConfig,
) -> tuple[Path, ...]:
    """Return the runtime-home files mutated by one effective model projection."""

    if tool == "claude":
        if model_config.reasoning is None:
            return ()
        return (home_path / _CLAUDE_SETTINGS_FILENAME,)
    if tool == "codex":
        return (home_path / _CODEX_CONFIG_FILENAME,)
    if tool == "gemini":
        return (home_path / _GEMINI_SETTINGS_PATH,)
    raise ValueError(f"Unsupported model-mapping tool {tool!r}")


def _restore_model_config_paths(snapshots: dict[Path, str | None]) -> None:
    """Restore previously captured runtime-home file contents."""

    for path, prior_content in snapshots.items():
        if prior_content is None:
            if path.exists():
                path.unlink()
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(prior_content, encoding="utf-8")
