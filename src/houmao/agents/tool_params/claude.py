"""Typed Claude launch settings."""

from typing import Literal

from pydantic import Field, field_validator

from houmao.agents.tool_params.base import StrictToolParams, ToolParamsAdapter


class ClaudeToolParams(StrictToolParams):
    """Authored Claude permission and headless output preferences."""

    include_partial_messages: bool = False
    permission_mode: (
        Literal["default", "acceptEdits", "plan", "dontAsk", "auto", "bypassPermissions"] | None
    ) = Field(default=None, exclude_if=lambda value: value is None)

    @field_validator("permission_mode", mode="before")
    @classmethod
    def _normalize_permission_mode(cls, value: object) -> object:
        """Treat Claude's Manual label as its native default mode."""

        if value is None:
            raise ValueError("Claude permission_mode requires a native mode")
        return "default" if value == "manual" else value


class ClaudeToolParamsAdapter(ToolParamsAdapter[ClaudeToolParams, ClaudeToolParams]):
    """Project Claude's partial-message flag for its headless backend."""

    partial_model = ClaudeToolParams
    effective_model = ClaudeToolParams

    def prepare_launch(self, effective: ClaudeToolParams, *, backend: str) -> tuple[str, ...]:
        """Project partial-message delivery when the selected backend supports it."""

        if not effective.include_partial_messages:
            return ()
        if backend != "claude_headless":
            raise ValueError(
                f"`tool_params.include_partial_messages` is unsupported for backend={backend!r}"
            )
        return ("--include-partial-messages",)
