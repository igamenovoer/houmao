"""Pydantic models for persisted runtime boundary payloads."""

from __future__ import annotations

import re
from typing import TypeAlias

from pydantic import (
    BaseModel,
    ConfigDict,
    ValidationError,
    field_validator,
    model_validator,
)

from houmao.agents.mailbox_runtime_models import MailboxTransport

from .agent_identity import normalize_agent_identity_name
from .errors import SessionManifestError
from .models import BackendKind, CaoParsingMode, RoleInjectionMethod

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list[object] | dict[str, object]
JsonObject: TypeAlias = dict[str, JsonValue]
_SAFE_AGENT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_TMUX_BACKED_BACKENDS: frozenset[BackendKind] = frozenset(
    {"codex_headless", "claude_headless", "gemini_headless", "cao_rest"}
)


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


class LaunchPlanMailboxV1(_StrictBoundaryModel):
    """Persisted resolved mailbox binding for `launch_plan.v1`."""

    transport: MailboxTransport
    principal_id: str
    address: str
    bindings_version: str
    filesystem_root: str

    @field_validator(
        "principal_id",
        "address",
        "bindings_version",
        "filesystem_root",
    )
    @classmethod
    def _not_blank(cls, value: str) -> str:
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
    mailbox: LaunchPlanMailboxV1 | None = None

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
    tmux_window_name: str | None = None
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

    @field_validator("tmux_window_name")
    @classmethod
    def _optional_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
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
    registry_generation_id: str | None = None
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
        "registry_generation_id",
    )
    @classmethod
    def _not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
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
                raise ValueError("headless/cao must be omitted for backend=codex_app_server")
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


class SessionManifestPayloadV3(_StrictBoundaryModel):
    """Persisted ``session_manifest.v3`` payload."""

    schema_version: int
    backend: BackendKind
    tool: str
    role_name: str
    created_at_utc: str
    working_directory: str
    brain_manifest_path: str
    agent_name: str | None = None
    agent_id: str | None = None
    tmux_session_name: str | None = None
    job_dir: str | None = None
    registry_generation_id: str | None = None
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
        "agent_name",
        "agent_id",
        "tmux_session_name",
        "job_dir",
        "registry_generation_id",
    )
    @classmethod
    def _not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @model_validator(mode="after")
    def _validate_backend_sections_and_identity(self) -> "SessionManifestPayloadV3":
        if self.schema_version != 3:
            raise ValueError("schema_version must be 3")
        if self.launch_plan.backend != self.backend:
            raise ValueError("launch_plan.backend must match manifest backend")
        if self.launch_plan.tool != self.tool:
            raise ValueError("launch_plan.tool must match manifest tool")

        if self.agent_name is not None:
            try:
                canonical_agent_name = normalize_agent_identity_name(self.agent_name).canonical_name
            except SessionManifestError as exc:
                raise ValueError(str(exc)) from exc
            if canonical_agent_name != self.agent_name:
                raise ValueError("agent_name must use canonical `AGENTSYS-...` form")

        if self.agent_id is not None and not _SAFE_AGENT_ID_RE.fullmatch(self.agent_id):
            raise ValueError(
                "agent_id must use a safe filesystem component form ([A-Za-z0-9][A-Za-z0-9._-]*)"
            )

        expects_tmux_identity = self.backend in _TMUX_BACKED_BACKENDS
        identity_fields = (
            self.agent_name is not None,
            self.agent_id is not None,
            self.tmux_session_name is not None,
        )
        if expects_tmux_identity and not all(identity_fields):
            raise ValueError(
                "agent_name, agent_id, and tmux_session_name are required for tmux-backed backends"
            )
        if not expects_tmux_identity and any(identity_fields):
            raise ValueError(
                "agent_name, agent_id, and tmux_session_name must be omitted for non-tmux backends"
            )

        if self.backend == "codex_app_server":
            if self.codex is None:
                raise ValueError("codex is required for backend=codex_app_server")
            if self.headless is not None or self.cao is not None:
                raise ValueError("headless/cao must be omitted for backend=codex_app_server")
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
