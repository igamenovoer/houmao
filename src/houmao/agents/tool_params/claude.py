"""Typed Claude launch settings."""

from houmao.agents.tool_params.base import StrictToolParams, ToolParamsAdapter


class ClaudeToolParams(StrictToolParams):
    """Claude settings owned by Houmao's launch pipeline."""

    include_partial_messages: bool = False


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
