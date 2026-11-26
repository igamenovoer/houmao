"""Managed Hermes route configuration."""

from __future__ import annotations

from typing import Literal, get_args
from urllib.parse import urlsplit

from pydantic import field_validator

from houmao.agents.tool_params.base import StrictToolParams, ToolParamsAdapter


HermesReasoningEffort = Literal["none", "minimal", "low", "medium", "high", "xhigh", "max"]
HERMES_REASONING_EFFORTS: tuple[HermesReasoningEffort, ...] = get_args(HermesReasoningEffort)


def validate_hermes_reasoning_effort(value: object) -> HermesReasoningEffort:
    """Validate an exact effort label for Hermes custom Chat Completions."""

    if isinstance(value, str) and value in HERMES_REASONING_EFFORTS:
        return value
    raise ValueError(f"reasoning_effort must be one of {', '.join(HERMES_REASONING_EFFORTS)}.")


class HermesPartialToolParams(StrictToolParams):
    """An authored route layer for the managed Hermes provider."""

    base_url: str | None = None
    reasoning_effort: HermesReasoningEffort | None = None

    @field_validator("reasoning_effort", mode="before")
    @classmethod
    def _validate_reasoning_effort(cls, value: object) -> HermesReasoningEffort | None:
        """Validate an authored Hermes effort when supplied."""

        return None if value is None else validate_hermes_reasoning_effort(value)

    @field_validator("base_url")
    @classmethod
    def _validate_base_url(cls, value: str | None) -> str | None:
        """Accept an explicit HTTP endpoint with separate credential binding."""

        if value is None:
            return None
        url = value.strip()
        invalid_url = "Expected an HTTP(S) provider URL with credentials supplied separately."
        try:
            parsed = urlsplit(url)
            port = parsed.port
        except ValueError:
            raise ValueError(invalid_url) from None
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or any(char.isspace() for char in url)
        ):
            raise ValueError(invalid_url)
        if port == 0:
            raise ValueError("A provider port must be positive.")
        return url


class HermesToolParams(HermesPartialToolParams):
    """The complete managed Hermes Chat Completions route."""

    base_url: str


class HermesToolParamsAdapter(ToolParamsAdapter[HermesPartialToolParams, HermesToolParams]):
    """Select the endpoint using the common layered launch settings."""

    partial_model = HermesPartialToolParams
    effective_model = HermesToolParams
