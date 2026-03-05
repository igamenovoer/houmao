"""Pydantic models for persisted runtime boundary payloads."""

from __future__ import annotations

from typing import TypeAlias

from pydantic import (
    BaseModel,
    ConfigDict,
    ValidationError,
    field_validator,
    model_validator,
)

from .models import BackendKind, CaoParsingMode, RoleInjectionMethod

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list[object] | dict[str, object]
JsonObject: TypeAlias = dict[str, JsonValue]


class _StrictBoundaryModel(BaseModel):
    """Shared config for strict boundary parsing."""

    model_config = ConfigDict(extra="forbid", strict=True)


class LaunchPlanHomeSelectorV1(_StrictBoundaryModel):
    """`home_selector` payload for `launch_plan.v1`."""

    env_var: str
    home_path: str

    @field_validator("env_var", "home_path")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value


class LaunchPlanRoleInjectionV1(_StrictBoundaryModel):
    """`role_injection` payload for `launch_plan.v1`."""

    method: RoleInjectionMethod
    role_name: str

    @field_validator("role_name")
    @classmethod
    def _role_name_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value


class LaunchPlanPayloadV1(_StrictBoundaryModel):
    """Persisted `launch_plan.v1` payload."""

    backend: BackendKind
    tool: str
    executable: str
    args: list[str]
    working_directory: str
    home_selector: LaunchPlanHomeSelectorV1
    env_var_names: list[str]
    role_injection: LaunchPlanRoleInjectionV1
    metadata: JsonObject

    @field_validator("tool", "executable", "working_directory")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value


class CodexSectionV1(_StrictBoundaryModel):
    """Persisted codex backend section."""

    thread_id: str | None
    turn_index: int
    pid: int | None = None
    process_started_at_utc: str | None = None


class HeadlessSectionV1(_StrictBoundaryModel):
    """Persisted headless backend section."""

    session_id: str | None
    turn_index: int
    role_bootstrap_applied: bool
    working_directory: str

    @field_validator("working_directory")
    @classmethod
    def _workdir_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value


class CaoSectionV2(_StrictBoundaryModel):
    """Persisted CAO backend section."""

    api_base_url: str
    session_name: str
    terminal_id: str
    profile_name: str
    profile_path: str
    parsing_mode: CaoParsingMode
    turn_index: int = 0

    @field_validator(
        "api_base_url",
        "session_name",
        "terminal_id",
        "profile_name",
        "profile_path",
    )
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value


class SessionManifestPayloadV2(_StrictBoundaryModel):
    """Persisted `session_manifest.v2` payload."""

    schema_version: int
    backend: BackendKind
    tool: str
    role_name: str
    created_at_utc: str
    working_directory: str
    brain_manifest_path: str
    launch_plan: LaunchPlanPayloadV1
    backend_state: JsonObject
    codex: CodexSectionV1 | None = None
    headless: HeadlessSectionV1 | None = None
    cao: CaoSectionV2 | None = None

    @field_validator(
        "tool",
        "role_name",
        "created_at_utc",
        "working_directory",
        "brain_manifest_path",
    )
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @model_validator(mode="after")
    def _validate_backend_sections(self) -> "SessionManifestPayloadV2":
        if self.schema_version != 2:
            raise ValueError("schema_version must be 2")
        if self.launch_plan.backend != self.backend:
            raise ValueError("launch_plan.backend must match manifest backend")
        if self.launch_plan.tool != self.tool:
            raise ValueError("launch_plan.tool must match manifest tool")

        if self.backend == "codex_app_server":
            if self.codex is None:
                raise ValueError("codex is required for backend=codex_app_server")
            if self.headless is not None or self.cao is not None:
                raise ValueError(
                    "headless/cao must be omitted for backend=codex_app_server"
                )
        elif self.backend in {
            "codex_headless",
            "claude_headless",
            "gemini_headless",
        }:
            if self.headless is None:
                raise ValueError(
                    "headless is required for backend=codex_headless/"
                    "claude_headless/gemini_headless"
                )
            if self.codex is not None or self.cao is not None:
                raise ValueError(
                    "codex/cao must be omitted for backend=codex_headless/"
                    "claude_headless/gemini_headless"
                )
        elif self.backend == "cao_rest":
            if self.cao is None:
                raise ValueError("cao is required for backend=cao_rest")
            if self.codex is not None or self.headless is not None:
                raise ValueError("codex/headless must be omitted for backend=cao_rest")
        return self


def format_pydantic_error(prefix: str, exc: ValidationError) -> str:
    """Return an actionable field-path error message."""

    details: list[str] = []
    for issue in exc.errors(include_url=False):
        location = _format_error_location(issue.get("loc", ()))
        message = str(issue.get("msg", "validation failed"))
        details.append(f"{location}: {message}")
        if len(details) >= 3:
            break
    joined = "; ".join(details) if details else "validation failed"
    return f"{prefix}: {joined}"


def _format_error_location(location: object) -> str:
    if not isinstance(location, tuple) or not location:
        return "$"

    path = "$"
    for item in location:
        if isinstance(item, int):
            path += f"[{item}]"
            continue
        path += f".{item}"
    return path
