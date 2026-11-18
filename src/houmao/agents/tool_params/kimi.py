"""Typed Kimi launch settings."""

from houmao.agents.tool_params.base import StrictToolParams, ToolParamsAdapter


class KimiToolParams(StrictToolParams):
    """Kimi currently uses its native setup files for tool-specific settings."""


class KimiToolParamsAdapter(ToolParamsAdapter[KimiToolParams, KimiToolParams]):
    """Enforce the empty Kimi parameters schema."""

    partial_model = KimiToolParams
    effective_model = KimiToolParams
