"""Pydantic models for persisted runtime boundary payloads."""

from __future__ import annotations

from houmao.gateway.access import GatewayLaunchSeed

from typing import Annotated, Literal, TypeAlias

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from houmao.execution.context import parse_execution_binding
from houmao.execution.models import ExecutionBindingV1

from .agent_identity import normalize_managed_agent_id, normalize_managed_agent_name
from .errors import SessionManifestError
from .models import BackendKind, CaoParsingMode, RoleInjectionMethod
from houmao.agents.realm_controller.run_modes import (
    RunMode,
    human_surface_for_mode,
    validate_mode_binding,
)
from houmao.agents.realm_controller.native_surface import (
    NativeSurfaceKind,
    NativeSurfaceV1,
    TerminalNativeSurfaceV1,
    WebNativeSurfaceV1,
)

OperatorPromptModeV1: TypeAlias = Literal["as_is", "unattended"]
LaunchPolicySelectionSourceV1: TypeAlias = Literal["registry", "env_override"]
RegistryLaunchAuthorityV1: TypeAlias = Literal["runtime", "external"]
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
        "codex_app_server",
        "claude_headless",
        "kimi_headless",
        "kimi_acp",
        "dsh_headless",
        "dsh_acp",
        "dsh_web",
        "hermes_tui",
        "hermes_service",
        "hermes_headless",
        "kimi_web",
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
    channel: Literal["offline"]
    agent_id: str
    binding_id: str
    registry_root: str | None = None
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
    channel: Literal["online"]
    provider: Literal["stalwart"]
    agent_id: str
    binding_id: str
    principal_id: str
    address: str
    bindings_version: str
    jmap_url: str
    management_url: str | None = None
    account_id: str | None = None
    identity_id: str | None = None
    trusted_jmap_origins: list[str] = Field(default_factory=list)
    api_origin: str | None = None
    credential_source_ref: str | None = None
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
    def _not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("must not be empty")
        return value


class LaunchPlanMailboxRegistryV1(_StrictBoundaryModel):
    """Protected remote offline binding; no registry-local paths are accepted."""

    transport: Literal["registry"]
    channel: Literal["offline"]
    agent_id: str
    binding_id: str
    principal_id: str
    address: str
    bindings_version: str
    registry_url: str
    credential_ref: str


LaunchPlanMailboxV1: TypeAlias = Annotated[
    LaunchPlanMailboxFilesystemV1 | LaunchPlanMailboxStalwartV1 | LaunchPlanMailboxRegistryV1,
    Field(discriminator="transport"),
]


class MailboxSlotPayloadV1(_StrictBoundaryModel):
    """Persisted slot authority, including empty-slot tombstone revisions."""

    revision: str = Field(min_length=1)
    binding: LaunchPlanMailboxV1 | None

    @model_validator(mode="after")
    def _validate_revision(self) -> "MailboxSlotPayloadV1":
        """Require matching binding and envelope revisions."""

        if not self.revision.strip():
            raise ValueError("revision must not be blank")
        if self.binding is not None and self.binding.bindings_version != self.revision:
            raise ValueError("binding revision differs from its slot authority")
        return self


class MailboxesPayloadV1(_StrictBoundaryModel):
    """Both mailbox channels, each with independent revision authority."""

    offline: MailboxSlotPayloadV1
    online: MailboxSlotPayloadV1

    @model_validator(mode="after")
    def _validate_scope(self) -> "MailboxesPayloadV1":
        """Reject swapped channels, blank scope, or mixed agent owners."""

        owners: set[str] = set()
        for channel, slot in (("offline", self.offline), ("online", self.online)):
            if slot.binding is None:
                continue
            if slot.binding.channel != channel:
                raise ValueError("mailbox binding does not match its selected channel")
            if not slot.binding.agent_id.strip() or not slot.binding.binding_id.strip():
                raise ValueError("mailbox binding requires agent_id and binding_id")
            if slot.binding.principal_id != slot.binding.agent_id:
                raise ValueError("mailbox principal_id must equal owning agent_id")
            owners.add(slot.binding.agent_id)
        if len(owners) > 1:
            raise ValueError("mailbox bindings must have the same agent owner")
        return self


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
    """Persisted `launch_plan.v3` payload."""

    schema_version: Literal[3]
    backend: BackendKind
    mode: RunMode
    native_surface_kind: NativeSurfaceKind | None = None
    execution_binding: ExecutionBindingV1 | None = None

    _execution_binding = field_validator("execution_binding", mode="before")(
        parse_execution_binding
    )
    tool: str
    executable: str
    args: list[str]
    working_directory: str
    home_selector: LaunchPlanHomeSelectorV1
    env_var_names: list[str]
    role_injection: LaunchPlanRoleInjectionV1
    metadata: JsonObject
    mailboxes: MailboxesPayloadV1
    launch_policy_provenance: LaunchPolicyProvenanceV1 | None = None

    @field_validator("tool", "executable", "working_directory")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @model_validator(mode="after")
    def _validate_native_surface(self) -> "LaunchPlanPayloadV1":
        """Keep the native surface consistent with the selected launch mode."""

        validate_mode_binding(self.tool, self.mode, self.backend)
        expected_surface = human_surface_for_mode(self.mode)
        if self.native_surface_kind is not None and self.native_surface_kind != expected_surface:
            raise ValueError("launch plan native surface differs from the selected mode")
        if self.mode == "web" and self.native_surface_kind != "web":
            raise ValueError("web mode requires a native Web surface")
        return self


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
    launch_environment_file: str | None = Field(
        default=None, pattern=r"^launch-environment-[a-f0-9]{32}\.json$"
    )
    execution_binding: ExecutionBindingV1 | None = None

    _execution_binding = field_validator("execution_binding", mode="before")(
        parse_execution_binding
    )
    memory_root: str | None = None
    memo_file: str | None = None
    pages_dir: str | None = None
    agent_def_dir: str | None = None
    agent_pid: int | None = None
    registry_generation_id: str | None = None
    registry_launch_authority: RegistryLaunchAuthorityV1 = "runtime"

    @field_validator(
        "session_id",
        "memory_root",
        "memo_file",
        "pages_dir",
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
        memory_fields = (self.memory_root, self.memo_file, self.pages_dir)
        if any(value is not None for value in memory_fields) and not all(
            value is not None for value in memory_fields
        ):
            raise ValueError(
                "runtime.memory_root, runtime.memo_file, and runtime.pages_dir must be "
                "stored together"
            )
        return self


class SessionManifestTmuxSectionV1(_StrictBoundaryModel):
    """Normalized tmux session authority for one managed surface."""

    model_config = ConfigDict(frozen=True)

    session_name: str
    socket_path: str | None = None
    server_allow_start: bool | None = None
    primary_window_index: str = "0"
    primary_window_role: Literal["managed_agent_surface", "supervisor_logs"] = (
        "managed_agent_surface"
    )
    primary_window_name: str | None = None
    primary_window_id: str | None = None
    primary_pane_id: str | None = None

    @field_validator("socket_path")
    @classmethod
    def _socket_path_absolute(cls, value: str | None) -> str | None:
        """Validate an owner-local selector without resolving a foreign path."""

        if value is None:
            return None
        from houmao.execution.tmux import validate_tmux_socket_path

        return validate_tmux_socket_path(value)

    @field_validator(
        "session_name",
        "primary_window_index",
        "primary_window_name",
        "primary_window_id",
        "primary_pane_id",
    )
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


class SessionManifestSystemPromptSectionV1(_StrictBoundaryModel):
    """Read-only effective Houmao system prompt persisted for self retrieval."""

    format: Literal["text"] = "text"
    role_name: str
    text: str
    sha256: str
    source: str

    @field_validator("role_name", "sha256", "source")
    @classmethod
    def _not_blank(cls, value: str) -> str:
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
    primary_window_id: str | None = None
    primary_pane_id: str | None = None
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
        "primary_window_id",
        "primary_pane_id",
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


class SessionManifestPayloadV4(_StrictBoundaryModel):
    """Persisted ``session_manifest.v6`` payload."""

    schema_version: Literal[6]
    backend: BackendKind
    mode: RunMode
    tool: str
    role_name: str
    created_at_utc: str
    working_directory: str
    brain_manifest_path: str
    agent_name: str | None = None
    agent_id: str
    tmux_session_name: str | None = None
    native_surface: NativeSurfaceV1 | None = None
    registry_generation_id: str | None = None
    registry_launch_authority: RegistryLaunchAuthorityV1 = "runtime"
    runtime: SessionManifestRuntimeSectionV1
    tmux: SessionManifestTmuxSectionV1 | None = None
    interactive: SessionManifestInteractiveSectionV1 | None = None
    agent_launch_authority: SessionManifestAgentLaunchAuthorityV1 | None = None
    gateway_authority: SessionManifestGatewayAuthorityV1 | None = None
    gateway_admin_seed: GatewayLaunchSeed | None = None
    launch_plan: LaunchPlanPayloadV1
    launch_policy_provenance: LaunchPolicyProvenanceV1 | None = None
    system_prompt: SessionManifestSystemPromptSectionV1 | None = None
    backend_state: JsonObject
    codex: None = None
    headless: HeadlessSectionV1 | None = None
    local_interactive: LocalInteractiveSectionV1 | None = None
    cao: CaoSectionV2 | None = None
    houmao_server: HoumaoServerSectionV1 | None = None

    @field_validator("gateway_admin_seed", mode="before")
    @classmethod
    def _parse_gateway_admin_seed(cls, value: object) -> object:
        """Allow a strict seed's tuple to be read from the manifest JSON array."""

        if isinstance(value, dict) and isinstance(value.get("admin_keys"), list):
            return {**value, "admin_keys": tuple(value["admin_keys"])}
        return value

    @field_validator(
        "tool",
        "role_name",
        "created_at_utc",
        "working_directory",
        "brain_manifest_path",
        "agent_name",
        "agent_id",
        "tmux_session_name",
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
        for slot in (self.launch_plan.mailboxes.offline, self.launch_plan.mailboxes.online):
            if slot.binding is not None and slot.binding.agent_id != self.agent_id:
                raise ValueError("mailbox binding agent_id differs from manifest owner")
        if self.launch_plan.backend != self.backend:
            raise ValueError("launch_plan.backend must match manifest backend")
        if self.launch_plan.tool != self.tool:
            raise ValueError("launch_plan.tool must match manifest tool")
        if self.launch_plan.mode != self.mode:
            raise ValueError("launch_plan.mode must match manifest mode")
        if self.native_surface is not None and self.native_surface.kind != human_surface_for_mode(
            self.mode
        ):
            raise ValueError("manifest native surface differs from the selected mode")
        if self.mode == "web":
            surface = self.native_surface
            identity = self.backend_state.get("web_identity")
            if not isinstance(surface, WebNativeSurfaceV1) or not isinstance(identity, dict):
                raise ValueError(
                    "Web mode requires a verified native Web surface and execution identity"
                )
            required = (
                "agent_id",
                "runtime_session_id",
                "generation",
                "host_incarnation",
                "native_session_id",
                "agent_incarnation",
            )
            if (
                type(identity.get("protocol_version")) is not int
                or identity.get("protocol_version") != 1
                or any(
                    not isinstance(identity.get(key), str) or not identity[key] for key in required
                )
            ):
                raise ValueError("Web mode requires a complete versioned execution identity")
            if (
                self.backend_state.get("origin") != surface.origin
                or self.backend_state.get("browser_url") != surface.origin
                or identity["native_session_id"] != surface.native_session_id
                or identity["agent_id"] != self.agent_id
                or identity["runtime_session_id"] != self.runtime.session_id
                or identity["generation"] != self.registry_generation_id
            ):
                raise ValueError("native Web identity differs from manifest execution authority")
            if self.interactive is not None and (
                self.interactive.terminal_id is not None
                or self.interactive.parsing_mode is not None
            ):
                raise ValueError("Web supervision cannot publish terminal parser authority")
            if self.tmux is not None and self.tmux.primary_window_role != "supervisor_logs":
                raise ValueError("Web tmux metadata must identify supervisory logs")
        elif isinstance(self.native_surface, WebNativeSurfaceV1):
            raise ValueError("a Web native surface requires Web mode")
        if (
            isinstance(self.native_surface, TerminalNativeSurfaceV1)
            and self.native_surface.tmux_session_name != self.tmux_session_name
        ):
            raise ValueError("terminal native surface differs from tmux session authority")
        if isinstance(self.native_surface, TerminalNativeSurfaceV1) and self.backend not in {
            "local_interactive",
            "hermes_tui",
            "cao_rest",
            "houmao_server_rest",
        }:
            raise ValueError("headless process supervision is not a native terminal surface")

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
        if not expects_tmux_identity and self.tmux_session_name is not None:
            raise ValueError("tmux_session_name must be omitted for non-tmux backends")

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
        if self.runtime.execution_binding != self.launch_plan.execution_binding:
            raise ValueError("runtime.execution_binding must match launch_plan.execution_binding")
        binding = self.runtime.execution_binding
        if (
            binding is not None
            and binding.tmux_socket is not None
            and self.backend in _TMUX_BACKED_BACKENDS
        ):
            if self.tmux is None or self.tmux.socket_path != binding.tmux_socket:
                raise ValueError("tmux.socket_path must match the admitted execution binding")

        if self.mode == "web" or self.backend == "codex_app_server":
            if any(
                section is not None
                for section in (
                    self.headless,
                    self.local_interactive,
                    self.cao,
                    self.houmao_server,
                )
            ):
                raise ValueError(
                    "Web and service manifests omit terminal/headless backend sections"
                )
            if self.backend == "codex_app_server":
                self._validate_codex_service_state()
        elif self.backend in {
            "codex_headless",
            "claude_headless",
            "kimi_headless",
            "dsh_headless",
        }:
            if self.headless is None:
                raise ValueError(
                    "headless is required for backend=codex_headless/claude_headless/kimi_headless"
                )
            if (
                self.local_interactive is not None
                or self.cao is not None
                or self.houmao_server is not None
            ):
                raise ValueError(
                    "local_interactive/cao/houmao_server must be omitted for "
                    "backend=codex_headless/"
                    "claude_headless/kimi_headless"
                )
        elif self.backend == "local_interactive":
            if self.local_interactive is None:
                raise ValueError("local_interactive is required for backend=local_interactive")
            if self.headless is not None or self.cao is not None or self.houmao_server is not None:
                raise ValueError(
                    "headless/cao/houmao_server must be omitted for backend=local_interactive"
                )
        elif self.backend == "cao_rest":
            if self.cao is None:
                raise ValueError("cao is required for backend=cao_rest")
            if (
                self.headless is not None
                or self.local_interactive is not None
                or self.houmao_server is not None
            ):
                raise ValueError(
                    "headless/local_interactive/houmao_server must be omitted for backend=cao_rest"
                )
        elif self.backend == "houmao_server_rest":
            if self.houmao_server is None:
                raise ValueError("houmao_server is required for backend=houmao_server_rest")
            if (
                self.headless is not None
                or self.local_interactive is not None
                or self.cao is not None
            ):
                raise ValueError(
                    "headless/local_interactive/cao must be omitted for backend=houmao_server_rest"
                )
        return self

    def _validate_codex_service_state(self) -> None:
        """Require an exact current service binding for a saved Codex thread."""

        from houmao.agents.realm_controller.backends.service_runtime import (
            ManagedServiceSessionState,
        )

        try:
            state = ManagedServiceSessionState.from_payload(self.backend_state)
        except ValidationError as exc:
            raise ValueError(
                "Codex app-server authority requires current service state. Start a fresh runtime session."
            ) from exc
        if (
            self.tmux is None
            or self.tmux.primary_window_role != "supervisor_logs"
            or state.tmux_session_name != self.tmux.session_name
            or not state.tmux_window_id
            or state.tmux_window_id != self.tmux.primary_window_id
            or state.tmux_pane_id != self.tmux.primary_pane_id
            or state.working_directory != self.working_directory
            or state.working_directory != self.launch_plan.working_directory
            or state.generation_id != self.registry_generation_id
            or state.runtime_session_id != self.runtime.session_id
            or not state.native_session_id.strip()
            or not state.service_incarnation.strip()
            or not state.generation_id.strip()
            or not state.runtime_session_id.strip()
            or self.registry_launch_authority != "runtime"
            or self.runtime.execution_binding is None
        ):
            raise ValueError(
                "Codex app-server current service identity differs from manifest authority"
            )


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
SessionManifestPayloadV4.model_rebuild()
