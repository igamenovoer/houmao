"""Typed Codex launch settings."""

from typing import Literal

from pydantic import Field, field_validator

from houmao.agents.tool_params.base import StrictToolParams, ToolParamsAdapter


class CodexToolParams(StrictToolParams):
    """Codex approval and sandbox preferences shared by CLI and service launches."""

    approval_policy: Literal["never", "on-request", "untrusted"] | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    sandbox_mode: Literal["danger-full-access", "workspace-write", "read-only"] | None = Field(
        default=None, exclude_if=lambda value: value is None
    )

    @field_validator("approval_policy", "sandbox_mode", mode="before")
    @classmethod
    def _require_native_policy(cls, value: object) -> object:
        """Require a supported value when a policy field is present."""

        if value is None:
            raise ValueError("Codex permission fields require a native policy value")
        return value

    @field_validator("approval_policy", mode="before")
    @classmethod
    def _normalize_legacy_approval(cls, value: object) -> object:
        """Use the policy Codex applies for its legacy OnFailure spelling."""

        return "on-request" if value == "on-failure" else value


class CodexToolParamsAdapter(ToolParamsAdapter[CodexToolParams, CodexToolParams]):
    """Validate authored Codex permission preferences."""

    partial_model = CodexToolParams
    effective_model = CodexToolParams
