"""Typed Kimi launch settings."""

from typing import Literal

from pydantic import Field, field_validator

from houmao.agents.tool_params.base import StrictToolParams, ToolParamsAdapter

KimiPermissionMode = Literal["manual", "yolo", "auto"]
KIMI_PERMISSION_MODES = ("manual", "yolo", "auto")


class KimiToolParams(StrictToolParams):
    """Support the native Kimi startup permission mode."""

    permission_mode: KimiPermissionMode | None = Field(
        default=None, exclude_if=lambda value: value is None
    )

    @field_validator("permission_mode", mode="before")
    @classmethod
    def _validate_permission_mode(cls, value: object) -> object:
        """Require a native mode when the author supplies a value."""

        if value is None:
            raise ValueError("Kimi permission_mode requires a native mode")
        return value


class KimiToolParamsAdapter(ToolParamsAdapter[KimiToolParams, KimiToolParams]):
    """Validate authored mode and reject modes native prompt entry cannot honor."""

    partial_model = KimiToolParams
    effective_model = KimiToolParams

    def prepare_launch(self, effective: KimiToolParams, *, backend: str) -> tuple[str, ...]:
        """Reject a mode that Kimi would replace while executing a native prompt."""

        if backend == "kimi_headless" and effective.permission_mode in {"manual", "yolo"}:
            raise ValueError(
                f"`tool_params.permission_mode={effective.permission_mode}` is unsupported for "
                "backend='kimi_headless'. Native Kimi `-p` always uses `auto`. "
                "Select TUI, service, or Web to use this permission mode."
            )
        return ()
