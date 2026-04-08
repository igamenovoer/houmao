"""Pydantic models for persisted runtime boundary payloads."""

from __future__ import annotations

from typing import Annotated, Literal, TypeAlias

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from .agent_identity import normalize_managed_agent_id, normalize_managed_agent_name
from .errors import SessionManifestError
from .models import BackendKind, CaoParsingMode, RoleInjectionMethod

OperatorPromptModeV1: TypeAlias = Literal["as_is", "unattended"]
LaunchPolicySelectionSourceV1: TypeAlias = Literal["registry", "env_override"]
RegistryLaunchAuthorityV1: TypeAlias = Literal["runtime", "external"]
RuntimeMemoryBindingKindV1: TypeAlias = Literal["auto", "exact", "disabled"]
SessionOriginV1: TypeAlias = Literal["joined_tmux"]
AgentLaunchPostureKindV1: TypeAlias = Literal[
    "runtime_launch_plan",
    "tui_launch_options",
    "headless_launch_options",
    "unavailable",
]
HeadlessResumeSelectionKindV1: TypeAlias = Literal["none", "last", "exact"]

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list[object] | dict[str, object]
JsonObject: TypeAlias = dict[str, JsonValue]
_TMUX_BACKED_BACKENDS: frozenset[BackendKind] = frozenset(
    {
        "local_interactive",
        "codex_headless",
        "claude_headless",
        "gemini_headless",
        "cao_rest",
        "houmao_server_rest",
    }
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


class LaunchPlanMailboxFilesystemV1(_StrictBoundaryModel):
    """Persisted filesystem mailbox binding for `launch_plan.v1`."""

    transport: Literal["filesystem"]
    principal_id: str
    address: str
    bindings_version: str
    filesystem_root: str
    mailbox_kind: Literal["in_root", "symlink"] = "in_root"
    mailbox_path: str | None = None

    @field_validator(
        "principal_id",
        "address",
        "bindings_version",
        "filesystem_root",
        "mailbox_path",
    )
    @classmethod
    def _not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @model_validator(mode="after")
    def _require_path_for_symlink(self) -> "LaunchPlanMailboxFilesystemV1":
        if self.mailbox_kind == "symlink" and self.mailbox_path is None:
            raise ValueError("mailbox_path is required when mailbox_kind is `symlink`")
        return self


class LaunchPlanMailboxStalwartV1(_StrictBoundaryModel):
    """Persisted Stalwart mailbox binding for `launch_plan.v1`."""

    transport: Literal["stalwart"]
    principal_id: str
    address: str
    bindings_version: str
    jmap_url: str
    management_url: str
    login_identity: str
    credential_ref: str

    @field_validator(
        "principal_id",
        "address",
        "bindings_version",
        "jmap_url",
        "management_url",
        "login_identity",
        "credential_ref",
    )
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value


LaunchPlanMailboxV1: TypeAlias = Annotated[
    LaunchPlanMailboxFilesystemV1 | LaunchPlanMailboxStalwartV1,
    Field(discriminator="transport"),
]


class LaunchPolicyProvenanceV1(_StrictBoundaryModel):
    """Typed launch-policy provenance persisted in launch/session payloads."""

    requested_operator_prompt_mode: OperatorPromptModeV1
    detected_tool_version: str
    selected_strategy_id: str
    selection_source: LaunchPolicySelectionSourceV1
    override_env_var_name: str | None = None

    @field_validator(
        "detected_tool_version",
        "selected_strategy_id",
        "override_env_var_name",
    )
    @classmethod
    def _not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
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
    launch_policy_provenance: LaunchPolicyProvenanceV1 | None = None

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
    resume_selection_kind: HeadlessResumeSelectionKindV1 = "none"
    resume_selection_value: str | None = None

    @field_validator("working_directory", "resume_selection_value")
    @classmethod
    def _optional_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @model_validator(mode="after")
    def _validate_resume_selection(self) -> HeadlessSectionV1:
        if self.resume_selection_kind == "exact":
            if self.resume_selection_value is None:
                raise ValueError(
                    "resume_selection_value is required for resume_selection_kind=exact"
                )
            return self
        if self.resume_selection_value is not None:
            raise ValueError(
                "resume_selection_value must be omitted unless resume_selection_kind=exact"
            )
        return self


class LocalInteractiveSectionV1(_StrictBoundaryModel):
    """Persisted local interactive backend section."""

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


class HoumaoServerSectionV1(_StrictBoundaryModel):
    """Persisted `houmao_server_rest` backend section."""

    api_base_url: str
    session_name: str
    terminal_id: str
    parsing_mode: CaoParsingMode
    tmux_window_name: str | None = None
    turn_index: int = 0

    @field_validator("api_base_url", "session_name", "terminal_id")
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


class SessionManifestRuntimeSectionV1(_StrictBoundaryModel):
    """Normalized runtime-owned manifest authority for one tmux-backed session."""

    session_id: str | None = None
    job_dir: str | None = None
    memory_binding: RuntimeMemoryBindingKindV1 | None = None
    memory_dir: str | None = None
    agent_def_dir: str | None = None
    agent_pid: int | None = None
    registry_generation_id: str | None = None
    registry_launch_authority: RegistryLaunchAuthorityV1 = "runtime"

    @field_validator(
        "session_id",
        "job_dir",
        "memory_binding",
        "memory_dir",
        "agent_def_dir",
        "registry_generation_id",
        "registry_launch_authority",
    )
    @classmethod
    def _optional_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @field_validator("agent_pid")
    @classmethod
    def _optional_positive_int(cls, value: int | None) -> int | None:
        if value is None:
            return None
        if value <= 0:
            raise ValueError("must be > 0")
        return value

    @model_validator(mode="after")
    def _validate_memory_binding(self) -> "SessionManifestRuntimeSectionV1":
        if self.memory_binding in {"auto", "exact"} and self.memory_dir is None:
            raise ValueError("memory_dir is required when runtime.memory_binding enables memory")
        if self.memory_binding == "disabled" and self.memory_dir is not None:
            raise ValueError(
                "runtime.memory_dir must be omitted when runtime.memory_binding is disabled"
            )
        if self.memory_binding is None and self.memory_dir is not None:
            raise ValueError("runtime.memory_binding is required when runtime.memory_dir is set")
        return self


class SessionManifestTmuxSectionV1(_StrictBoundaryModel):
    """Normalized tmux session authority for one managed surface."""

    session_name: str
    primary_window_index: str = "0"
    primary_window_role: Literal["managed_agent_surface"] = "managed_agent_surface"
    primary_window_name: str | None = None

    @field_validator("session_name", "primary_window_index", "primary_window_name")
    @classmethod
    def _optional_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("must not be empty")
        return value


class SessionManifestInteractiveSectionV1(_StrictBoundaryModel):
    """Shared interactive/runtime control state persisted in v4 manifests."""

    turn_index: int = 0
    working_directory: str | None = None
    role_bootstrap_applied: bool | None = None
    terminal_id: str | None = None
    parsing_mode: CaoParsingMode | None = None
    tmux_window_name: str | None = None

    @field_validator("working_directory", "terminal_id", "tmux_window_name")
    @classmethod
    def _optional_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("must not be empty")
        return value


class JoinedLaunchEnvBindingLiteralV1(_StrictBoundaryModel):
    """Literal joined-session launch env binding."""

    mode: Literal["literal"]
    name: str
    value: str

    @field_validator("name", "value")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value


class JoinedLaunchEnvBindingInheritedV1(_StrictBoundaryModel):
    """Inherited joined-session launch env binding."""

    mode: Literal["inherit"]
    name: str

    @field_validator("name")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value


JoinedLaunchEnvBindingV1: TypeAlias = Annotated[
    JoinedLaunchEnvBindingLiteralV1 | JoinedLaunchEnvBindingInheritedV1,
    Field(discriminator="mode"),
]


class SessionManifestAgentLaunchAuthorityV1(_StrictBoundaryModel):
    """Secret-free relaunch posture persisted in v4 manifests."""

    backend: BackendKind
    tool: str
    tmux_session_name: str | None = None
    primary_window_index: str = "0"
    working_directory: str
    session_id: str | None = None
    profile_name: str | None = None
    profile_path: str | None = None
    session_origin: SessionOriginV1 | None = None
    posture_kind: AgentLaunchPostureKindV1 | None = None
    launch_args: list[str] | None = None
    launch_env: list[JoinedLaunchEnvBindingV1] | None = None

    @field_validator(
        "tool",
        "tmux_session_name",
        "primary_window_index",
        "working_directory",
        "session_id",
        "profile_name",
        "profile_path",
    )
    @classmethod
    def _optional_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @field_validator("launch_args")
    @classmethod
    def _launch_args_not_blank(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        normalized: list[str] = []
        for entry in value:
            if not entry.strip():
                raise ValueError("launch_args entries must not be empty")
            normalized.append(entry)
        return normalized

    @model_validator(mode="after")
    def _validate_posture(self) -> SessionManifestAgentLaunchAuthorityV1:
        if self.posture_kind is None:
            return self
        if self.posture_kind in {"runtime_launch_plan", "unavailable"}:
            if self.launch_args is not None or self.launch_env is not None:
                raise ValueError(
                    "launch_args/launch_env must be omitted for runtime_launch_plan/unavailable"
                )
            return self
        if not self.launch_args and not self.launch_env:
            raise ValueError(
                "tui/headless launch-option postures require launch_args or launch_env"
            )
        return self


class SessionManifestGatewayEndpointAuthorityV1(_StrictBoundaryModel):
    """Normalized attach or control authority endpoint metadata."""

    api_base_url: str | None = None
    managed_agent_ref: str | None = None
    terminal_id: str | None = None
    profile_name: str | None = None
    profile_path: str | None = None
    parsing_mode: CaoParsingMode | None = None
    tmux_window_name: str | None = None

    @field_validator(
        "api_base_url",
        "managed_agent_ref",
        "terminal_id",
        "profile_name",
        "profile_path",
        "tmux_window_name",
    )
    @classmethod
    def _optional_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("must not be empty")
        return value


class SessionManifestGatewayAuthorityV1(_StrictBoundaryModel):
    """Normalized attach and control authority persisted in v4 manifests."""

    attach: SessionManifestGatewayEndpointAuthorityV1
    control: SessionManifestGatewayEndpointAuthorityV1


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
    launch_policy_provenance: LaunchPolicyProvenanceV1 | None = None
    backend_state: JsonObject
    codex: CodexSectionV1 | None = None
    headless: HeadlessSectionV1 | None = None
    local_interactive: LocalInteractiveSectionV1 | None = None
    cao: CaoSectionV2 | None = None
    houmao_server: HoumaoServerSectionV1 | None = None

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
            if (
                self.headless is not None
                or self.local_interactive is not None
                or self.cao is not None
                or self.houmao_server is not None
            ):
                raise ValueError(
                    "headless/local_interactive/cao/houmao_server must be omitted for "
                    "backend=codex_app_server"
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
            if (
                self.codex is not None
                or self.local_interactive is not None
                or self.cao is not None
                or self.houmao_server is not None
            ):
                raise ValueError(
                    "codex/local_interactive/cao/houmao_server must be omitted for "
                    "backend=codex_headless/"
                    "claude_headless/gemini_headless"
                )
        elif self.backend == "local_interactive":
            if self.local_interactive is None:
                raise ValueError("local_interactive is required for backend=local_interactive")
            if (
                self.codex is not None
                or self.headless is not None
                or self.cao is not None
                or self.houmao_server is not None
            ):
                raise ValueError(
                    "codex/headless/cao/houmao_server must be omitted for backend=local_interactive"
                )
        elif self.backend == "cao_rest":
            if self.cao is None:
                raise ValueError("cao is required for backend=cao_rest")
            if (
                self.codex is not None
                or self.headless is not None
                or self.local_interactive is not None
                or self.houmao_server is not None
            ):
                raise ValueError(
                    "codex/headless/local_interactive/houmao_server must be omitted for "
                    "backend=cao_rest"
                )
        elif self.backend == "houmao_server_rest":
            if self.houmao_server is None:
                raise ValueError("houmao_server is required for backend=houmao_server_rest")
            if (
                self.codex is not None
                or self.headless is not None
                or self.local_interactive is not None
                or self.cao is not None
            ):
                raise ValueError(
                    "codex/headless/local_interactive/cao must be omitted for "
                    "backend=houmao_server_rest"
                )
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
    registry_launch_authority: RegistryLaunchAuthorityV1 = "runtime"
    launch_plan: LaunchPlanPayloadV1
    launch_policy_provenance: LaunchPolicyProvenanceV1 | None = None
    backend_state: JsonObject
    codex: CodexSectionV1 | None = None
    headless: HeadlessSectionV1 | None = None
    local_interactive: LocalInteractiveSectionV1 | None = None
    cao: CaoSectionV2 | None = None
    houmao_server: HoumaoServerSectionV1 | None = None

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
        "registry_launch_authority",
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
                normalized_agent_name = normalize_managed_agent_name(self.agent_name)
            except SessionManifestError as exc:
                raise ValueError(str(exc)) from exc
            if normalized_agent_name != self.agent_name:
                raise ValueError("agent_name must not include leading or trailing whitespace")

        if self.agent_id is not None:
            try:
                normalized_agent_id = normalize_managed_agent_id(self.agent_id)
            except SessionManifestError as exc:
                raise ValueError(str(exc)) from exc
            if normalized_agent_id != self.agent_id:
                raise ValueError("agent_id must not include leading or trailing whitespace")

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
            if (
                self.headless is not None
                or self.local_interactive is not None
                or self.cao is not None
                or self.houmao_server is not None
            ):
                raise ValueError(
                    "headless/local_interactive/cao/houmao_server must be omitted for "
                    "backend=codex_app_server"
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
            if (
                self.codex is not None
                or self.local_interactive is not None
                or self.cao is not None
                or self.houmao_server is not None
            ):
                raise ValueError(
                    "codex/local_interactive/cao/houmao_server must be omitted for "
                    "backend=codex_headless/"
                    "claude_headless/gemini_headless"
                )
        elif self.backend == "local_interactive":
            if self.local_interactive is None:
                raise ValueError("local_interactive is required for backend=local_interactive")
            if (
                self.codex is not None
                or self.headless is not None
                or self.cao is not None
                or self.houmao_server is not None
            ):
                raise ValueError(
                    "codex/headless/cao/houmao_server must be omitted for backend=local_interactive"
                )
        elif self.backend == "cao_rest":
            if self.cao is None:
                raise ValueError("cao is required for backend=cao_rest")
            if (
                self.codex is not None
                or self.headless is not None
                or self.local_interactive is not None
                or self.houmao_server is not None
            ):
                raise ValueError(
                    "codex/headless/local_interactive/houmao_server must be omitted for "
                    "backend=cao_rest"
                )
        elif self.backend == "houmao_server_rest":
            if self.houmao_server is None:
                raise ValueError("houmao_server is required for backend=houmao_server_rest")
            if (
                self.codex is not None
                or self.headless is not None
                or self.local_interactive is not None
                or self.cao is not None
            ):
                raise ValueError(
                    "codex/headless/local_interactive/cao must be omitted for "
                    "backend=houmao_server_rest"
                )
        return self


class SessionManifestPayloadV4(_StrictBoundaryModel):
    """Persisted ``session_manifest.v4`` payload."""

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
    registry_launch_authority: RegistryLaunchAuthorityV1 = "runtime"
    runtime: SessionManifestRuntimeSectionV1
    tmux: SessionManifestTmuxSectionV1 | None = None
    interactive: SessionManifestInteractiveSectionV1 | None = None
    agent_launch_authority: SessionManifestAgentLaunchAuthorityV1 | None = None
    gateway_authority: SessionManifestGatewayAuthorityV1 | None = None
    launch_plan: LaunchPlanPayloadV1
    launch_policy_provenance: LaunchPolicyProvenanceV1 | None = None
    backend_state: JsonObject
    codex: CodexSectionV1 | None = None
    headless: HeadlessSectionV1 | None = None
    local_interactive: LocalInteractiveSectionV1 | None = None
    cao: CaoSectionV2 | None = None
    houmao_server: HoumaoServerSectionV1 | None = None

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
        "registry_launch_authority",
    )
    @classmethod
    def _not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @model_validator(mode="after")
    def _validate_backend_sections_and_authority(self) -> "SessionManifestPayloadV4":
        if self.schema_version != 4:
            raise ValueError("schema_version must be 4")
        if self.launch_plan.backend != self.backend:
            raise ValueError("launch_plan.backend must match manifest backend")
        if self.launch_plan.tool != self.tool:
            raise ValueError("launch_plan.tool must match manifest tool")

        if self.agent_name is not None:
            try:
                normalized_agent_name = normalize_managed_agent_name(self.agent_name)
            except SessionManifestError as exc:
                raise ValueError(str(exc)) from exc
            if normalized_agent_name != self.agent_name:
                raise ValueError("agent_name must not include leading or trailing whitespace")

        if self.agent_id is not None:
            try:
                normalized_agent_id = normalize_managed_agent_id(self.agent_id)
            except SessionManifestError as exc:
                raise ValueError(str(exc)) from exc
            if normalized_agent_id != self.agent_id:
                raise ValueError("agent_id must not include leading or trailing whitespace")

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

        if expects_tmux_identity:
            if self.tmux is None:
                raise ValueError("tmux is required for tmux-backed backends")
            if self.interactive is None:
                raise ValueError("interactive is required for tmux-backed backends")
            if self.agent_launch_authority is None:
                raise ValueError("agent_launch_authority is required for tmux-backed backends")
            if self.gateway_authority is None:
                raise ValueError("gateway_authority is required for tmux-backed backends")
            if self.tmux_session_name != self.tmux.session_name:
                raise ValueError("tmux.session_name must match top-level tmux_session_name")

        if self.job_dir is not None and self.runtime.job_dir != self.job_dir:
            raise ValueError("runtime.job_dir must match top-level job_dir when both are set")
        if (
            self.registry_generation_id is not None
            and self.runtime.registry_generation_id != self.registry_generation_id
        ):
            raise ValueError(
                "runtime.registry_generation_id must match top-level registry_generation_id"
            )
        if self.runtime.registry_launch_authority != self.registry_launch_authority:
            raise ValueError(
                "runtime.registry_launch_authority must match top-level registry_launch_authority"
            )

        if self.backend == "codex_app_server":
            if self.codex is None:
                raise ValueError("codex is required for backend=codex_app_server")
            if (
                self.headless is not None
                or self.local_interactive is not None
                or self.cao is not None
                or self.houmao_server is not None
            ):
                raise ValueError(
                    "headless/local_interactive/cao/houmao_server must be omitted for "
                    "backend=codex_app_server"
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
            if (
                self.codex is not None
                or self.local_interactive is not None
                or self.cao is not None
                or self.houmao_server is not None
            ):
                raise ValueError(
                    "codex/local_interactive/cao/houmao_server must be omitted for "
                    "backend=codex_headless/"
                    "claude_headless/gemini_headless"
                )
        elif self.backend == "local_interactive":
            if self.local_interactive is None:
                raise ValueError("local_interactive is required for backend=local_interactive")
            if (
                self.codex is not None
                or self.headless is not None
                or self.cao is not None
                or self.houmao_server is not None
            ):
                raise ValueError(
                    "codex/headless/cao/houmao_server must be omitted for backend=local_interactive"
                )
        elif self.backend == "cao_rest":
            if self.cao is None:
                raise ValueError("cao is required for backend=cao_rest")
            if (
                self.codex is not None
                or self.headless is not None
                or self.local_interactive is not None
                or self.houmao_server is not None
            ):
                raise ValueError(
                    "codex/headless/local_interactive/houmao_server must be omitted for "
                    "backend=cao_rest"
                )
        elif self.backend == "houmao_server_rest":
            if self.houmao_server is None:
                raise ValueError("houmao_server is required for backend=houmao_server_rest")
            if (
                self.codex is not None
                or self.headless is not None
                or self.local_interactive is not None
                or self.cao is not None
            ):
                raise ValueError(
                    "codex/headless/local_interactive/cao must be omitted for "
                    "backend=houmao_server_rest"
                )
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


LaunchPlanPayloadV1.model_rebuild()
SessionManifestPayloadV2.model_rebuild()
SessionManifestPayloadV3.model_rebuild()
SessionManifestPayloadV4.model_rebuild()
