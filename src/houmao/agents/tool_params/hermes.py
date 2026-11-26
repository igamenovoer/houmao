"""Managed Hermes route configuration."""

from __future__ import annotations

from urllib.parse import urlsplit

from pydantic import field_validator

from houmao.agents.tool_params.base import StrictToolParams, ToolParamsAdapter


class HermesPartialToolParams(StrictToolParams):
    """An authored route layer for the managed Hermes provider."""

    base_url: str | None = None

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
