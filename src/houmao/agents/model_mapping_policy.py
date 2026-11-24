"""Native reasoning-mapping policy for unified model selection."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from houmao.agents.codex_cli_config import (
    CodexCliConfigOverride,
    codex_config_override_args,
    codex_config_override_payload,
)
from houmao.agents.kimi_configuration import (
    KIMI_CONFIG_FILENAME,
    load_kimi_config,
    select_kimi_model_alias,
)
from houmao.agents.launch_policy.provider_hooks import (
    provider_state_mutation_lock,
    set_json_key,
    set_toml_key,
    write_toml_state,
)
from houmao.agents.model_selection import ModelConfig
from houmao.agents.tool_params.dsh import MATERIALIZED_DSH_TOOL_PARAMS, DshEffectiveToolParams

_CLAUDE_SETTINGS_FILENAME = "settings.json"
_CODEX_CONFIG_FILENAME = "config.toml"
_CODEX_GPT_5_6_LUNA_MODEL_PREFIXES = ("gpt-5.6-luna",)
_CODEX_GPT_5_6_SOL_TERRA_MODEL_PREFIXES = ("gpt-5.6-sol", "gpt-5.6-terra")
_CODEX_GPT_5_6_SOL_TERRA_POSITIVE_VALUES = (
    "low",
    "medium",
    "high",
    "xhigh",
    "max",
    "ultra",
)
_CODEX_GPT_5_6_LUNA_POSITIVE_VALUES = ("low", "medium", "high", "xhigh", "max")
_CODEX_CURRENT_CODING_MODEL_PREFIXES = (
    "gpt-5.4",
    "gpt-5.3-codex",
    "gpt-5.2-codex",
)
_CODEX_CURRENT_CODING_MODEL_POSITIVE_VALUES = ("low", "medium", "high", "xhigh")
_CODEX_REASONING_LADDERS_BY_MODEL_PREFIX = (
    (
        _CODEX_GPT_5_6_LUNA_MODEL_PREFIXES,
        None,
        _CODEX_GPT_5_6_LUNA_POSITIVE_VALUES,
    ),
    (
        _CODEX_GPT_5_6_SOL_TERRA_MODEL_PREFIXES,
        None,
        _CODEX_GPT_5_6_SOL_TERRA_POSITIVE_VALUES,
    ),
    (
        _CODEX_CURRENT_CODING_MODEL_PREFIXES,
        None,
        _CODEX_CURRENT_CODING_MODEL_POSITIVE_VALUES,
    ),
)
_CODEX_FALLBACK_REASONING_LADDER = (
    None,
    _CODEX_CURRENT_CODING_MODEL_POSITIVE_VALUES,
)


@dataclass(frozen=True)
class TemporaryModelProjection:
    """Temporary per-turn model projection for headless execution."""

    env: dict[str, str]
    args: list[str]


def resolve_reasoning_mapping(
    *,
    tool: str,
    requested_level: int,
    model_name: str | None,
    tool_version: str | None = None,
    home_path: Path | None = None,
    kimi_config: Mapping[str, Any] | None = None,
    dsh_tool_params: DshEffectiveToolParams | None = None,
) -> dict[str, Any]:
    """Resolve one tool/model-relative reasoning preset index into native tool state."""

    if requested_level < 0:
        raise ValueError("requested_level must be a non-negative integer")

    if tool == "kimi":
        kimi_config = kimi_config if kimi_config is not None else _runtime_kimi_config(home_path)
        model_name = select_kimi_model_alias(kimi_config, model_name)

    ladder = _resolve_reasoning_ladder(
        tool=tool,
        requested_level=requested_level,
        model_name=model_name,
        tool_version=tool_version,
        home_path=home_path,
        kimi_config=kimi_config,
        dsh_tool_params=dsh_tool_params,
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
    dsh_tool_params: DshEffectiveToolParams | None = None,
) -> dict[str, Any]:
    """Project one reasoning preset index into the runtime home."""

    kimi_config = _runtime_kimi_config(home_path) if tool == "kimi" else None
    mapping = resolve_reasoning_mapping(
        tool=tool,
        requested_level=requested_level,
        model_name=model_name,
        tool_version=tool_version,
        home_path=home_path,
        kimi_config=kimi_config,
        dsh_tool_params=dsh_tool_params,
    )
    if tool == "dsh":
        return mapping
    if tool == "claude":
        native_setting = _require_single_native_setting(mapping)
        set_json_key(
            path=home_path / _CLAUDE_SETTINGS_FILENAME,
            key_path=("effortLevel",),
            value=str(native_setting["native_value"]),
            repair_invalid=True,
        )
        _attach_provider_cli_args_metadata(
            mapping,
            ["--effort", str(native_setting["native_value"])],
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
        _attach_codex_cli_override_metadata(
            mapping,
            key_path=("model_reasoning_effort",),
            value=str(native_setting["native_value"]),
        )
        return mapping

    if kimi_config is not None:
        thinking = kimi_config.setdefault("thinking", {})
        if not isinstance(thinking, dict):
            raise ValueError("Kimi config.toml requires a table for `thinking`.")
        thinking.pop("forced_effort", None)
        for native_setting in _require_native_settings(mapping):
            key_path = native_setting["projection_target"]["key_path"]
            thinking[key_path[-1]] = native_setting["native_value"]
        write_toml_state(home_path / KIMI_CONFIG_FILENAME, kimi_config)
        return mapping

    raise ValueError(f"Unsupported model-mapping tool {tool!r}")


def project_model_name(
    *,
    home_path: Path,
    tool: str,
    model_name: str,
) -> dict[str, Any]:
    """Project one normalized model name into the runtime home or CLI arguments."""

    stripped_model_name = model_name.strip()
    if tool == "dsh":
        model, _ = DshEffectiveToolParams.from_file(
            home_path / MATERIALIZED_DSH_TOOL_PARAMS
        ).select_model(stripped_model_name)
        return {"surface": "native_configuration", "value": model.id}
    if not stripped_model_name:
        raise ValueError("model_name must not be empty")

    if tool == "claude":
        projection: dict[str, Any] = {
            "surface": "cli_arg",
            "arg": "--model",
            "value": stripped_model_name,
        }
        _attach_provider_cli_args_metadata(projection, ["--model", stripped_model_name])
        return projection

    if tool == "codex":
        set_toml_key(
            path=home_path / _CODEX_CONFIG_FILENAME,
            key_path=("model",),
            value=stripped_model_name,
            repair_invalid=True,
        )
        projection = {
            "surface": "toml",
            "path": _CODEX_CONFIG_FILENAME,
            "key_path": ["model"],
            "value": stripped_model_name,
        }
        _attach_codex_cli_override_metadata(
            projection,
            key_path=("model",),
            value=stripped_model_name,
        )
        return projection

    if tool == "kimi":
        select_kimi_model_alias(_runtime_kimi_config(home_path), stripped_model_name)
        projection = {
            "surface": "cli_arg",
            "arg": "--model",
            "value": stripped_model_name,
        }
        _attach_provider_cli_args_metadata(projection, ["--model", stripped_model_name])
        return projection

    raise ValueError(f"Unsupported model-mapping tool {tool!r}")


@contextmanager
def temporary_project_model_config(
    *,
    home_path: Path,
    tool: str,
    model_config: ModelConfig | None,
) -> Iterator[TemporaryModelProjection]:
    """Apply one effective model config for a single headless turn and then restore state."""

    if model_config is None or model_config.is_empty():
        yield TemporaryModelProjection(env={}, args=[])
        return

    cli_args: list[str] = []
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
                model_projection = project_model_name(
                    home_path=home_path,
                    tool=tool,
                    model_name=model_config.name,
                )
                cli_args.extend(_cli_args_from_projection(model_projection))
            if model_config.reasoning is not None:
                reasoning_projection = project_reasoning_level(
                    home_path=home_path,
                    tool=tool,
                    requested_level=model_config.reasoning.level,
                    model_name=model_config.name,
                )
                cli_args.extend(_cli_args_from_projection(reasoning_projection))
            yield TemporaryModelProjection(env={}, args=cli_args)
        finally:
            _restore_model_config_paths(snapshots)


def _attach_provider_cli_args_metadata(payload: dict[str, Any], args: list[str]) -> None:
    """Attach provider CLI args metadata to one native projection payload."""

    payload["cli_args"] = list(args)


def _attach_codex_cli_override_metadata(
    payload: dict[str, Any],
    *,
    key_path: tuple[str, ...],
    value: str | bool | int,
) -> None:
    """Attach Codex CLI override metadata to one native projection payload."""

    override = CodexCliConfigOverride(key_path, value)
    payload["cli_overrides"] = codex_config_override_payload((override,))
    payload["cli_args"] = codex_config_override_args((override,))


def _cli_args_from_projection(projection: dict[str, Any]) -> list[str]:
    """Extract provider CLI args from one projection payload when present."""

    cli_args = projection.get("cli_args")
    if not isinstance(cli_args, list) or not all(isinstance(item, str) for item in cli_args):
        return []
    return list(cli_args)


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
    requested_level: int,
    model_name: str | None,
    tool_version: str | None,
    home_path: Path | None,
    kimi_config: Mapping[str, Any] | None,
    dsh_tool_params: DshEffectiveToolParams | None,
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
        return _resolve_codex_reasoning_ladder(model_name=model_name)

    if tool == "kimi":
        assert kimi_config is not None
        return _resolve_kimi_reasoning_ladder(
            config=kimi_config,
            model_name=model_name,
            requested_level=requested_level,
        )

    if tool == "dsh":
        return _resolve_dsh_reasoning_ladder(
            home_path=home_path, model_name=model_name, dsh_tool_params=dsh_tool_params
        )

    raise ValueError(f"Unsupported model-mapping tool {tool!r}")


def _resolve_dsh_reasoning_ladder(
    *,
    home_path: Path | None,
    model_name: str | None,
    dsh_tool_params: DshEffectiveToolParams | None,
) -> dict[str, Any]:
    """Resolve the model's declared DSH thinking slots in native escalation order."""

    if dsh_tool_params is None:
        if home_path is None:
            raise ValueError(
                "DSH reasoning mapping requires effective tool_params or a runtime home."
            )
        dsh_tool_params = DshEffectiveToolParams.from_file(home_path / MATERIALIZED_DSH_TOOL_PARAMS)
    model, _ = dsh_tool_params.select_model(model_name)
    slots = model.reasoning_slots
    if model.reasoning_efforts is False:
        return {
            "off_preset": (
                _native_setting(
                    "reasoning_effort",
                    "off",
                    surface="native_configuration",
                    path=MATERIALIZED_DSH_TOOL_PARAMS,
                ),
            ),
            "positive_presets": (),
        }

    def setting(slot: str) -> tuple[dict[str, Any], ...]:
        """Project the native selector slot, which DSH maps to its wire value."""

        value = _native_setting(
            "reasoning_effort",
            slot,
            surface="native_configuration",
            path=MATERIALIZED_DSH_TOOL_PARAMS,
        )
        value["profile_key"] = slot
        return (value,)

    return {
        "off_preset": setting("off") if "off" in slots else None,
        "positive_presets": tuple(setting(slot) for slot in slots if slot != "off"),
    }


def _resolve_codex_reasoning_ladder(
    *,
    model_name: str | None,
) -> dict[str, Any]:
    """Resolve one maintained Codex reasoning preset ladder."""

    if model_name is not None and model_name.lower() == "gpt-5.6":
        return _codex_reasoning_ladder(
            off_value=None,
            positive_values=_CODEX_GPT_5_6_SOL_TERRA_POSITIVE_VALUES,
        )

    for prefixes, off_value, positive_values in _CODEX_REASONING_LADDERS_BY_MODEL_PREFIX:
        if _model_name_matches_prefix(model_name, prefixes):
            return _codex_reasoning_ladder(
                off_value=off_value,
                positive_values=positive_values,
            )

    off_value, positive_values = _CODEX_FALLBACK_REASONING_LADDER
    return _codex_reasoning_ladder(
        off_value=off_value,
        positive_values=positive_values,
    )


def _resolve_kimi_reasoning_ladder(
    *,
    config: Mapping[str, Any],
    model_name: str | None,
    requested_level: int,
) -> dict[str, Any]:
    """Resolve one declared Kimi model's native thinking settings."""

    if model_name is None:
        raise ValueError("Kimi reasoning requires a selected model alias in config.toml.")
    effective_alias = dict(config["models"][model_name])
    overrides = effective_alias.get("overrides")
    if isinstance(overrides, dict):
        effective_alias.update(overrides)
    positive_values: tuple[str, ...] = ()
    if requested_level > 0:
        effort_values = effective_alias.get("support_efforts")
        if (
            not isinstance(effort_values, list)
            or not effort_values
            or any(not isinstance(value, str) or not value.strip() for value in effort_values)
            or len(set(effort_values)) != len(effort_values)
        ):
            raise ValueError(
                f"Kimi model alias `{model_name}` requires an ordered list of unique, non-empty "
                "labels in config.toml `support_efforts` for positive reasoning levels."
            )
        positive_values = tuple(cast(list[str], effort_values))
    capabilities = {
        value.lower() for value in _nonempty_string_tuple(effective_alias.get("capabilities"))
    }
    off_preset = None
    if "always_thinking" not in capabilities:
        off_preset = (
            _native_setting(
                "thinking_enabled",
                False,
                surface="toml",
                path=KIMI_CONFIG_FILENAME,
            ),
        )
    return {
        "off_preset": off_preset,
        "positive_presets": tuple(
            (
                _native_setting(
                    "thinking_enabled",
                    True,
                    surface="toml",
                    path=KIMI_CONFIG_FILENAME,
                ),
                _native_setting(
                    "thinking_effort",
                    value,
                    surface="toml",
                    path=KIMI_CONFIG_FILENAME,
                ),
            )
            for value in positive_values
        ),
    }


def _runtime_kimi_config(home_path: Path | None) -> dict[str, Any]:
    """Read the native config used by the current runtime generation."""

    if home_path is None:
        raise ValueError("Kimi reasoning requires a resolved config.toml.")
    return load_kimi_config(home_path / KIMI_CONFIG_FILENAME)


def _codex_reasoning_ladder(
    *,
    off_value: str | None,
    positive_values: tuple[str, ...],
) -> dict[str, Any]:
    """Build one Codex reasoning ladder from native effort values."""

    off_preset = (
        (
            _native_setting(
                "model_reasoning_effort",
                off_value,
                surface="toml",
                path=_CODEX_CONFIG_FILENAME,
            ),
        )
        if off_value is not None
        else None
    )
    return {
        "off_preset": off_preset,
        "positive_presets": tuple(
            (
                _native_setting(
                    "model_reasoning_effort",
                    value,
                    surface="toml",
                    path=_CODEX_CONFIG_FILENAME,
                ),
            )
            for value in positive_values
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
    if native_scale == "reasoning_effort":
        return ["reasoning_effort"]
    if native_scale == "thinking_enabled":
        return ["thinking", "enabled"]
    if native_scale == "thinking_effort":
        return ["thinking", "effort"]
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


def _require_native_settings(mapping: dict[str, Any]) -> list[dict[str, Any]]:
    """Require a non-empty list of native reasoning settings."""

    native_settings = mapping.get("native_settings")
    if not isinstance(native_settings, list) or not native_settings:
        raise ValueError("Expected at least one native setting for this tool mapping.")
    if not all(isinstance(setting, dict) for setting in native_settings):
        raise ValueError("Invalid native setting payload.")
    return native_settings


def _nonempty_string_tuple(value: object) -> tuple[str, ...]:
    """Return stripped non-empty strings from one list-like config value."""

    if not isinstance(value, list):
        return ()
    return tuple(item.strip() for item in value if isinstance(item, str) and item.strip())


def _claude_model_supports_max(model_name: str | None) -> bool:
    """Return whether one Claude model likely supports `max` effort."""

    if model_name is None:
        return False
    lowered = model_name.lower()
    return "opus-4-6" in lowered


def _model_name_matches_prefix(model_name: str | None, prefixes: tuple[str, ...]) -> bool:
    """Return whether one model name matches any maintained model-family prefix."""

    if model_name is None:
        return False
    lowered = model_name.lower()
    return any(lowered.startswith(prefix) for prefix in prefixes)


def _mutated_model_config_paths(
    *,
    home_path: Path,
    tool: str,
    model_config: ModelConfig,
) -> tuple[Path, ...]:
    """Return the runtime-home files mutated by one effective model projection."""

    if tool == "dsh":
        return ()
    if tool == "claude":
        if model_config.reasoning is None:
            return ()
        return (home_path / _CLAUDE_SETTINGS_FILENAME,)
    if tool == "codex":
        return (home_path / _CODEX_CONFIG_FILENAME,)
    if tool == "kimi":
        if model_config.reasoning is None:
            return ()
        return (home_path / KIMI_CONFIG_FILENAME,)
    raise ValueError(f"Unsupported model-mapping tool {tool!r}")


def _restore_model_config_paths(snapshots: dict[Path, str | None]) -> None:
    """Restore previously captured runtime-home file contents."""

    for path, prior_content in snapshots.items():
        if prior_content is None:
            if path.exists():
                path.unlink()
            continue
        if not path.exists() or path.read_text(encoding="utf-8") != prior_content:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(prior_content, encoding="utf-8")
