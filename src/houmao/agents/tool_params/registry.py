"""Registry and IO boundary for per-tool launch settings."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, cast

import yaml

from houmao.agents.tool_params.base import StrictToolParams, ToolParamsAdapter
from houmao.agents.tool_params.claude import ClaudeToolParamsAdapter
from houmao.agents.tool_params.codex import CodexToolParamsAdapter
from houmao.agents.tool_params.hermes import HermesToolParamsAdapter
from houmao.agents.tool_params.kimi import KimiToolParamsAdapter

_ADAPTERS = {
    "claude": ClaudeToolParamsAdapter(),
    "codex": CodexToolParamsAdapter(),
    "hermes": HermesToolParamsAdapter(),
    "kimi": KimiToolParamsAdapter(),
}


def get_tool_params_adapter(tool: str) -> ToolParamsAdapter[StrictToolParams, StrictToolParams]:
    """Select the adapter for one supported tool."""

    if tool == "dsh":
        from houmao.agents.tool_params.dsh import DshToolParamsAdapter

        return cast(ToolParamsAdapter[StrictToolParams, StrictToolParams], DshToolParamsAdapter())
    adapter = _ADAPTERS.get(tool)
    if adapter is None:
        raise ValueError(f"Tool `{tool}` has no tool_params schema")
    return cast(ToolParamsAdapter[StrictToolParams, StrictToolParams], adapter)


def validate_tool_params(tool: str, payload: object, *, source: str) -> dict[str, Any]:
    """Validate one partial layer and serialize only explicitly supplied fields."""

    adapter = get_tool_params_adapter(tool)
    return adapter.parse_partial(
        _require_mapping(payload, source=source), source=source
    ).model_dump(mode="json", exclude_unset=True)


def merge_partial_tool_params(
    tool: str, layers: Sequence[tuple[str, Mapping[str, Any]]]
) -> dict[str, Any]:
    """Merge authored layers while retaining optionality for future launches."""

    adapter = get_tool_params_adapter(tool)
    partials = [(source, adapter.parse_partial(raw, source=source)) for source, raw in layers]
    return adapter.merge_partial(partials).model_dump(mode="json", exclude_unset=True)


def resolve_tool_params(
    tool: str, layers: Sequence[tuple[str, Mapping[str, Any]]]
) -> dict[str, Any]:
    """Apply precedence and validate the resulting effective parameters."""

    adapter = get_tool_params_adapter(tool)
    partials = [(source, adapter.parse_partial(raw, source=source)) for source, raw in layers]
    return adapter.merge_layers(partials).model_dump(mode="json")


def parse_tool_params_cli_input(value: str) -> dict[str, Any]:
    """Read inline JSON or load a YAML or JSON mapping from an owner-side path."""

    if value.startswith("@"):
        try:
            path = Path(value[1:]).expanduser()
        except RuntimeError:
            raise ValueError("tool_params file: cannot resolve the home directory") from None
        source = f"tool_params file {path}"
        suffix = path.suffix.lower()
        if suffix not in {".yaml", ".yml", ".json"}:
            raise ValueError(f"{source}: use a .yaml, .yml, or .json file")
        try:
            raw = path.read_text(encoding="utf-8")
            loaded = json.loads(raw) if suffix == ".json" else yaml.safe_load(raw)
        except (OSError, UnicodeError, ValueError, yaml.YAMLError, RecursionError):
            raise ValueError(f"{source}: cannot read a valid {suffix[1:]} document") from None
    else:
        source = "tool_params"
        try:
            loaded = json.loads(value)
        except (ValueError, RecursionError):
            raise ValueError(f"{source}: expected inline JSON or @<path>") from None
    return _require_mapping(loaded, source=source)


def _require_mapping(payload: object, *, source: str) -> dict[str, Any]:
    """Check the mapping boundary without exposing unvalidated values."""

    if not isinstance(payload, Mapping) or any(not isinstance(key, str) for key in payload):
        raise ValueError(f"{source}: expected a mapping with string keys")
    return dict(payload)
