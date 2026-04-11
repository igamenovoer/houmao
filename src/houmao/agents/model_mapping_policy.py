"""Native reasoning-mapping policy for unified model selection."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
import json
from pathlib import Path
from typing import Any

from houmao.agents.launch_policy.provider_hooks import (
    provider_state_mutation_lock,
    set_json_key,
    set_toml_key,
)
from houmao.agents.model_selection import ModelConfig

_CLAUDE_SETTINGS_FILENAME = "settings.json"
_CODEX_CONFIG_FILENAME = "config.toml"
_GEMINI_SETTINGS_PATH = Path(".gemini") / "settings.json"


def resolve_reasoning_mapping(
    *,
    tool: str,
    requested_level: int,
    model_name: str | None,
    tool_version: str | None = None,
) -> dict[str, Any]:
    """Resolve one tool/model-relative reasoning preset index into native tool state."""

    if requested_level < 0:
        raise ValueError("requested_level must be a non-negative integer")

    ladder = _resolve_reasoning_ladder(
        tool=tool,
        model_name=model_name,
        tool_version=tool_version,
    )
    off_preset = ladder["off_preset"]
    positive_presets = ladder["positive_presets"]

    if requested_level == 0:
        if off_preset is None:
            rendered_model = model_name or "default"
            raise ValueError(f"{tool} model `{rendered_model}` does not support reasoning level 0.")
        return _build_reasoning_mapping(
            tool=tool,
            tool_version=tool_version,
            requested_level=requested_level,
            effective_level=0,
            model_name=model_name,
            native_settings=off_preset,
            saturated=False,
            off_requested=True,
        )

    if not positive_presets:
        rendered_model = model_name or "default"
        raise ValueError(f"{tool} model `{rendered_model}` exposes no positive reasoning presets.")

    effective_level = min(requested_level, len(positive_presets))
    native_settings = positive_presets[effective_level - 1]
    return _build_reasoning_mapping(
        tool=tool,
        tool_version=tool_version,
        requested_level=requested_level,
        effective_level=effective_level,
        model_name=model_name,
        native_settings=native_settings,
        saturated=requested_level > len(positive_presets),
        off_requested=False,
    )


def project_reasoning_level(
    *,
    home_path: Path,
    tool: str,
    requested_level: int,
    model_name: str | None,
    tool_version: str | None = None,
) -> dict[str, Any]:
    """Project one reasoning preset index into the runtime home."""

    mapping = resolve_reasoning_mapping(
        tool=tool,
        requested_level=requested_level,
        model_name=model_name,
        tool_version=tool_version,
    )
    if tool == "claude":
        native_setting = _require_single_native_setting(mapping)
        set_json_key(
            path=home_path / _CLAUDE_SETTINGS_FILENAME,
            key_path=("effortLevel",),
            value=str(native_setting["native_value"]),
            repair_invalid=True,
        )
        return mapping

    if tool == "codex":
        native_setting = _require_single_native_setting(mapping)
        set_toml_key(
            path=home_path / _CODEX_CONFIG_FILENAME,
            key_path=("model_reasoning_effort",),
            value=str(native_setting["native_value"]),
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
            path: path.read_text(encoding="utf-8") if path.exists() else None
            for path in mutated_paths
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

    return resolve_reasoning_mapping(
        tool="gemini",
        requested_level=requested_level,
        model_name=model_name,
        tool_version=tool_version,
    )


def _build_reasoning_mapping(
    *,
    tool: str,
    tool_version: str | None,
    requested_level: int,
    effective_level: int,
    model_name: str | None,
    native_settings: tuple[dict[str, Any], ...],
    saturated: bool,
    off_requested: bool,
) -> dict[str, Any]:
    """Build one operator-facing reasoning mapping payload."""

    mapping: dict[str, Any] = {
        "tool": tool,
        "tool_version": tool_version,
        "requested_level": requested_level,
        "effective_level": effective_level,
        "model_name": model_name,
        "saturated": saturated,
        "off_requested": off_requested,
        "native_settings": [dict(setting) for setting in native_settings],
    }
    if len(native_settings) == 1:
        mapping.update(native_settings[0])
    return mapping


def _resolve_reasoning_ladder(
    *,
    tool: str,
    model_name: str | None,
    tool_version: str | None,
) -> dict[str, Any]:
    """Resolve one maintained reasoning ladder for the resolved tool/model."""

    del tool_version

    if tool == "claude":
        positive_presets: list[tuple[dict[str, Any], ...]] = [
            (
                _native_setting(
                    "effortLevel", "low", surface="json", path=_CLAUDE_SETTINGS_FILENAME
                ),
            ),
            (
                _native_setting(
                    "effortLevel",
                    "medium",
                    surface="json",
                    path=_CLAUDE_SETTINGS_FILENAME,
                ),
            ),
            (
                _native_setting(
                    "effortLevel",
                    "high",
                    surface="json",
                    path=_CLAUDE_SETTINGS_FILENAME,
                ),
            ),
        ]
        if _claude_model_supports_max(model_name):
            positive_presets.append(
                (
                    _native_setting(
                        "effortLevel",
                        "max",
                        surface="json",
                        path=_CLAUDE_SETTINGS_FILENAME,
                    ),
                )
            )
        return {
            "off_preset": None,
            "positive_presets": tuple(positive_presets),
        }

    if tool == "codex":
        return {
            "off_preset": (
                _native_setting(
                    "model_reasoning_effort",
                    "none",
                    surface="toml",
                    path=_CODEX_CONFIG_FILENAME,
                ),
            ),
            "positive_presets": (
                (
                    _native_setting(
                        "model_reasoning_effort",
                        "minimal",
                        surface="toml",
                        path=_CODEX_CONFIG_FILENAME,
                    ),
                ),
                (
                    _native_setting(
                        "model_reasoning_effort",
                        "low",
                        surface="toml",
                        path=_CODEX_CONFIG_FILENAME,
                    ),
                ),
                (
                    _native_setting(
                        "model_reasoning_effort",
                        "medium",
                        surface="toml",
                        path=_CODEX_CONFIG_FILENAME,
                    ),
                ),
                (
                    _native_setting(
                        "model_reasoning_effort",
                        "high",
                        surface="toml",
                        path=_CODEX_CONFIG_FILENAME,
                    ),
                ),
                (
                    _native_setting(
                        "model_reasoning_effort",
                        "xhigh",
                        surface="toml",
                        path=_CODEX_CONFIG_FILENAME,
                    ),
                ),
            ),
        }

    if tool == "gemini":
        return _resolve_gemini_reasoning_ladder(model_name=model_name)

    raise ValueError(f"Unsupported model-mapping tool {tool!r}")


def _resolve_gemini_reasoning_ladder(
    *,
    model_name: str | None,
) -> dict[str, Any]:
    """Resolve one maintained Gemini reasoning preset ladder."""

    if _is_gemini_3_model(model_name):
        return {
            "off_preset": None,
            "positive_presets": (
                (
                    _native_setting(
                        "thinkingLevel", "LOW", surface="json", path=str(_GEMINI_SETTINGS_PATH)
                    ),
                    _native_setting(
                        "thinkingBudget", 1024, surface="json", path=str(_GEMINI_SETTINGS_PATH)
                    ),
                ),
                (
                    _native_setting(
                        "thinkingLevel", "MEDIUM", surface="json", path=str(_GEMINI_SETTINGS_PATH)
                    ),
                    _native_setting(
                        "thinkingBudget", 4096, surface="json", path=str(_GEMINI_SETTINGS_PATH)
                    ),
                ),
                (
                    _native_setting(
                        "thinkingLevel", "HIGH", surface="json", path=str(_GEMINI_SETTINGS_PATH)
                    ),
                    _native_setting(
                        "thinkingBudget", 16384, surface="json", path=str(_GEMINI_SETTINGS_PATH)
                    ),
                ),
            ),
        }

    return {
        "off_preset": (
            _native_setting("thinkingBudget", 0, surface="json", path=str(_GEMINI_SETTINGS_PATH)),
        ),
        "positive_presets": (
            (
                _native_setting(
                    "thinkingBudget",
                    512,
                    surface="json",
                    path=str(_GEMINI_SETTINGS_PATH),
                ),
            ),
            (
                _native_setting(
                    "thinkingBudget",
                    2048,
                    surface="json",
                    path=str(_GEMINI_SETTINGS_PATH),
                ),
            ),
            (
                _native_setting(
                    "thinkingBudget",
                    4096,
                    surface="json",
                    path=str(_GEMINI_SETTINGS_PATH),
                ),
            ),
            (
                _native_setting(
                    "thinkingBudget",
                    8192,
                    surface="json",
                    path=str(_GEMINI_SETTINGS_PATH),
                ),
            ),
            (
                _native_setting(
                    "thinkingBudget",
                    16384,
                    surface="json",
                    path=str(_GEMINI_SETTINGS_PATH),
                ),
            ),
        ),
    }


def _native_setting(
    native_scale: str,
    native_value: Any,
    *,
    surface: str,
    path: str,
) -> dict[str, Any]:
    """Build one native reasoning setting payload."""

    return {
        "native_scale": native_scale,
        "native_value": native_value,
        "projection_target": {
            "surface": surface,
            "path": path,
            "key_path": _projection_key_path_for_scale(native_scale),
        },
    }


def _projection_key_path_for_scale(native_scale: str) -> list[object]:
    """Return the projection key path for one maintained native reasoning scale."""

    if native_scale == "effortLevel":
        return ["effortLevel"]
    if native_scale == "model_reasoning_effort":
        return ["model_reasoning_effort"]
    if native_scale in {"thinkingLevel", "thinkingBudget"}:
        return [
            "modelConfigs",
            "customOverrides",
            0,
            "modelConfig",
            "generateContentConfig",
            "thinkingConfig",
            native_scale,
        ]
    raise ValueError(f"Unsupported native reasoning scale {native_scale!r}")


def _require_single_native_setting(mapping: dict[str, Any]) -> dict[str, Any]:
    """Require one single-setting mapping for tools with scalar reasoning state."""

    native_settings = mapping.get("native_settings")
    if not isinstance(native_settings, list) or len(native_settings) != 1:
        raise ValueError("Expected exactly one native setting for this tool mapping.")
    native_setting = native_settings[0]
    if not isinstance(native_setting, dict):
        raise ValueError("Invalid native setting payload.")
    return native_setting


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
                    str(native_setting["native_scale"]): native_setting["native_value"]
                    for native_setting in mapping["native_settings"]
                    if isinstance(native_setting, dict)
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
