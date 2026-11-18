"""Typed Codex launch settings."""

from houmao.agents.tool_params.base import StrictToolParams, ToolParamsAdapter


class CodexToolParams(StrictToolParams):
    """Codex currently uses its native setup files for tool-specific settings."""


class CodexToolParamsAdapter(ToolParamsAdapter[CodexToolParams, CodexToolParams]):
    """Enforce the empty Codex parameters schema."""

    partial_model = CodexToolParams
    effective_model = CodexToolParams
