"""High-level session runtime orchestration."""

from __future__ import annotations

import fcntl
import logging
import os
import shlex
import signal
import socket
import sqlite3
import subprocess
import sys
import time
from dataclasses import dataclass, field, replace
from contextlib import contextmanager
from functools import wraps
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Concatenate, Iterator, Literal, ParamSpec, TypeVar, cast

from houmao.execution.context import (
    current_execution_binding,
    execution_binding_scope,
    execution_is_read_only,
    execution_read_only_scope,
    observed_local_binding,
    validate_execution_owner,
)
from houmao.execution.models import ExecutionBindingV1
from houmao.execution.tmux import (
    capture_tmux_socket_path,
    current_tmux_socket_path,
    tmux_server_scope,
    validate_tmux_socket_path,
)

from houmao.gateway.plugins import GatewayPluginConfiguration

from houmao.agents.agent_workspace import (
    HOUMAO_AGENT_MEMORY_DIR_ENV_VAR,
    HOUMAO_AGENT_MEMO_FILE_ENV_VAR,
    HOUMAO_AGENT_PAGES_DIR_ENV_VAR,
    AgentMemoryPaths,
    ensure_agent_memory,
    memory_env,
    resolve_agent_memory,
)
from houmao.agents.launch_env import owner_launch_baseline, validate_persistent_env_records
from houmao.cao.no_proxy import (
    inject_loopback_no_proxy_env,
    is_supported_loopback_cao_base_url,
    should_preserve_no_proxy_env,
)
from houmao.owned_paths import (
    HOUMAO_GLOBAL_MAILBOX_DIR_ENV_VAR,
    HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR,
    HOUMAO_GLOBAL_RUNTIME_DIR_ENV_VAR,
    resolve_mailbox_root,
    resolve_registry_root,
    resolve_runtime_root,
)
from houmao.project.overlay import (
    PROJECT_OVERLAY_DIR_ENV_VAR,
    ensure_project_aware_local_roots,
    resolve_project_aware_local_roots,
    resolve_project_aware_mailbox_root,
)
from houmao.agents.managed_prompt_header import (
    compose_managed_launch_prompt,
    resolve_managed_prompt_header_decision,
)
from houmao.agents.managed_launch_force import ManagedLaunchForceMode
from houmao.agents.launch_policy.models import LaunchPolicyProvenance
from houmao.agents.dsh_configuration import (
    DshEffectiveToolParams,
    read_dsh_mcp_environment,
)
from houmao.agents.kimi_system_prompt import (
    KimiSystemPromptError,
    validate_kimi_v2_engine_env,
)
from houmao.agents.model_selection import (
    ModelConfig,
    extract_resolved_model_config_from_brain_manifest,
    resolve_execution_model_config,
)
from houmao.agents.realm_controller.runtime_launch_environment import (
    read_runtime_launch_environment,
    write_runtime_launch_environment,
)
from .agent_identity import (
    AGENT_DEF_DIR_ENV_VAR,
    AGENT_NAMESPACE_PREFIX,
    AGENT_ID_ENV_VAR,
    AGENT_MANIFEST_PATH_ENV_VAR,
    AgentIdentityCreation,
    AgentIdMode,
    derive_default_canonical_agent_name,
    derive_tmux_session_name,
    is_path_like_agent_identity,
    normalize_managed_agent_id,
    normalize_managed_agent_name,
    normalize_agent_identity_name,
    normalize_user_managed_agent_name,
)
from .backends.cao_rest import (
    CaoRestSession,
    CaoSessionState,
    cao_backend_state_payload,
)
from .boundary_models import (
    RegistryLaunchAuthorityV1,
    SessionManifestAgentLaunchAuthorityV1,
    SessionManifestPayloadV4,
)
from .backends.claude_headless import ClaudeHeadlessSession
from .backends.codex_headless import CodexHeadlessSession
from .backends.headless_base import (
    HeadlessInteractiveSession,
    HeadlessSessionState,
    headless_backend_state_payload,
)
from .backends.kimi_headless import KimiHeadlessSession
from houmao.agents.realm_controller.backends.dsh_headless import DshHeadlessSession
from houmao.agents.realm_controller.backends.service_runtime import (
    ManagedServiceSession,
    ManagedServiceSessionState,
)
from .backends.dsh_web import DshWebSession, DshWebSessionState
from .backends.kimi_web import KimiWebSession, KimiWebSessionState
from .native_surface import NativeSurfaceV1
from .backends.headless_output import (
    HeadlessDisplayDetail,
    HeadlessDisplayStyle,
    resolve_headless_display_detail,
    resolve_headless_display_style,
)
from .backends.local_interactive import (
    LocalInteractiveSession,
    validate_kimi_tui_chat_selection,
)
from .backends.tmux_runtime import (
    TmuxCommandError,
    TmuxPaneRecord,
    has_tmux_session as has_tmux_session_shared,
    list_tmux_panes as list_tmux_panes_shared,
    list_tmux_sessions as list_tmux_sessions_shared,
    overlay_tmux_rich_color_environment,
    read_tmux_session_environment_value as read_tmux_session_environment_value_shared,
    run_tmux as run_tmux_shared,
    set_tmux_session_environment as set_tmux_session_environment_shared,
    show_tmux_environment as show_tmux_environment_shared,
    tmux_error_detail as tmux_error_detail_shared,
    tmux_config_injection_enabled,
    unset_tmux_session_environment as unset_tmux_session_environment_shared,
)
from .errors import (
    BackendExecutionError,
    GatewayAttachError,
    GatewayDiscoveryError,
    GatewayHttpError,
    GatewayNoLiveInstanceError,
    GatewayProtocolError,
    GatewayUnsupportedBackendError,
    LaunchPlanError,
    LaunchPolicyResolutionError,
    SessionManifestError,
)
from .gateway_client import GatewayClient, GatewayEndpoint
from houmao.agents.realm_controller.gateway_access_runtime import (
    gateway_access_for_manifest,
    load_gateway_deployment,
    owner_gateway_client_binding,
    provision_gateway_generation,
    save_gateway_deployment,
)
from houmao.gateway.access import GatewayAccessError, GatewayLaunchSeed
from houmao.gateway.deployment import GatewayDeployment, owner_gateway_base_url
from .gateway_models import (
    GATEWAY_PROTOCOL_VERSION,
    BlueprintGatewayDefaults,
    GatewayAcceptedRequestV1,
    GatewayAttachContractV1,
    GatewayCurrentExecutionMode,
    GatewayCurrentInstanceV1,
    GatewayDesiredConfigV1,
    GatewayDiagnosticLoggingConfigV1,
    GatewayHost,
    GatewayJsonObject,
    GatewayPromptAdmissionPolicy,
    GatewayPromptControlRequestV1,
    GatewayPromptControlResultV1,
    GatewayRequestCreateV1,
    GatewayRequestPayloadInterruptV1,
    GatewayRequestPayloadSubmitPromptV1,
    GatewayStatusV1,
    GatewayTuiTrackingTimingConfigV1,
    GatewayTuiTrackingTimingOverridesV1,
    default_gateway_execution_mode_for_backend,
    resolve_gateway_tui_tracking_timing_config,
)
from .gateway_storage import (
    AGENT_GATEWAY_ATTACH_PATH_ENV_VAR,
    AGENT_GATEWAY_HOST_ENV_VAR,
    AGENT_GATEWAY_PORT_ENV_VAR,
    AGENT_GATEWAY_PROTOCOL_VERSION_ENV_VAR,
    AGENT_GATEWAY_ROOT_ENV_VAR,
    AGENT_GATEWAY_STATE_PATH_ENV_VAR,
    GatewayCapabilityPublication,
    GatewayPaths,
    build_live_gateway_bindings,
    build_offline_gateway_status,
    delete_gateway_current_instance,
    ensure_gateway_capability,
    gateway_paths_from_manifest_path,
    is_pid_running,
    live_gateway_env_var_names,
    load_gateway_current_instance,
    load_gateway_desired_config,
    load_gateway_status,
    publish_live_gateway_env,
    read_pid_file,
    refresh_gateway_manifest_publication,
    refresh_internal_gateway_publication,
    resolve_internal_gateway_attach_contract,
    write_gateway_desired_config,
    write_gateway_status,
)
from .hook_observation_launch import (
    activate_hook_observation_for_provider_start,
    ensure_hook_observation_on_resume,
    stop_hook_observation,
)
from .launch_plan import (
    LaunchPlanRequest,
    build_launch_plan,
    _bootstrap_message,
    configured_cao_parsing_mode,
    resolve_cao_parsing_mode,
    validate_dsh_launch_version,
    validate_kimi_web_launch_version,
)
from houmao.agents.realm_controller.run_modes import RunMode, mode_for_backend, resolve_run_mode
from houmao.agents.realm_controller.managed_control import (
    ManagedControlCapabilitiesV1,
    ManagedControlObservationV1,
    managed_control_capabilities,
)
from .loaders import RolePackage, load_brain_manifest, load_role_package
from .mail_commands import MailPromptRequest
from houmao.agents.mailbox_runtime_support import (
    bootstrap_resolved_mailbox,
    default_mailbox_address,
    mailbox_bindings_version_now,
    parse_declarative_mailboxes_config,
    safe_registry_mailboxes_projection,
    refresh_filesystem_mailbox_config,
    resolve_effective_mailboxes_config,
    resolve_live_mailbox_binding,
    mailboxes_resolved_config_from_payload,
)
from houmao.agents.mailbox_runtime_models import (
    FilesystemMailboxResolvedConfig,
    MailboxesDeclarativeConfig,
    MailboxesResolvedConfig,
    RemoteRegistryMailboxResolvedConfig,
    MailboxResolvedConfig,
)
from .manifest import (
    SessionManifestRequest,
    build_session_manifest_payload,
    default_manifest_path,
    generate_session_id,
    load_registry_mode_authority,
    load_session_manifest,
    parse_session_manifest_payload,
    runtime_owned_session_root_from_manifest_path,
    write_session_manifest,
    mutate_session_mailbox_binding,
)
from .models import (
    BackendKind,
    CaoParsingMode,
    GatewayControlResult,
    HeadlessTurnSessionSelection,
    InteractiveSession,
    LaunchPlan,
    RelaunchChatSessionSelection,
    RoleInjectionPlan,
    SessionControlResult,
    SessionEvent,
)
from .registry_models import (
    ManagedAgentRegistryRecordV3,
    RegistryGatewayV1,
    RegistryIdentityV1,
    RegistryLifecycleV1,
    RegistryLivenessV1,
    RegistryMailboxesV1,
    RegistryRuntimeV1,
    RegistryTerminalV2,
    canonicalize_registry_agent_name,
)
from .registry_storage import (
    TMUX_BACKED_REGISTRY_SENTINEL_LEASE_TTL,
    is_live_agent_record_fresh,
    load_managed_agent_record_by_agent_id,
    new_registry_generation_id,
    publish_live_agent_record,
    remove_live_agent_record,
    resolve_live_agent_record_by_agent_id,
    resolve_live_agent_records_by_name,
)
from houmao.mailbox import bootstrap_filesystem_mailbox, resolve_filesystem_mailbox_paths
from houmao.mailbox.managed import (
    DeregisterMailboxRequest,
    RegisterMailboxRequest,
    deregister_mailbox,
    register_mailbox,
)

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
        "kimi_web",
        "cao_rest",
    }
)
# Keep this narrow allowlist aligned with `_build_gateway_execution_adapter()`.
_GATEWAY_ATTACH_SUPPORTED_BACKENDS: tuple[BackendKind, ...] = (
    "local_interactive",
    "codex_headless",
    "codex_app_server",
    "claude_headless",
    "kimi_headless",
    "kimi_acp",
    "dsh_headless",
    "dsh_acp",
    "dsh_web",
    "kimi_web",
    "cao_rest",
)
_STOPPED_SESSION_RELAUNCH_BACKENDS: frozenset[BackendKind] = frozenset(
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
        "kimi_web",
    }
)
_PRIMARY_AGENT_WINDOW_INDEX = "0"
_GATEWAY_AUXILIARY_WINDOW_NAME = "gateway"
_GATEWAY_EXECUTION_MODE_ENV_VAR = "HOUMAO_GATEWAY_EXECUTION_MODE"
_GATEWAY_TMUX_WINDOW_ID_ENV_VAR = "HOUMAO_GATEWAY_TMUX_WINDOW_ID"
_GATEWAY_TMUX_WINDOW_INDEX_ENV_VAR = "HOUMAO_GATEWAY_TMUX_WINDOW_INDEX"
_GATEWAY_TMUX_PANE_ID_ENV_VAR = "HOUMAO_GATEWAY_TMUX_PANE_ID"
_BRAIN_ONLY_ROLE_NAME = "brain-only"
_JOINED_SESSION_ORIGIN = "joined_tmux"
_LOGGER = logging.getLogger(__name__)
_RETIRED_MEMORY_ENV_VARS = frozenset(
    {
        "HOUMAO_JOB_DIR",
        "HOUMAO_MEMORY_DIR",
        "HOUMAO_AGENT_STATE_DIR",
        "HOUMAO_AGENT_SCRATCH_DIR",
        "HOUMAO_AGENT_PERSIST_DIR",
    }
)
_MEMORY_ENV_VARS = frozenset(
    {
        HOUMAO_AGENT_MEMORY_DIR_ENV_VAR,
        HOUMAO_AGENT_MEMO_FILE_ENV_VAR,
        HOUMAO_AGENT_PAGES_DIR_ENV_VAR,
    }
)
_RETIRED_MAILBOX_METADATA_KEYS = frozenset(
    {
        "mailbox_live_enabled",
        "mailbox_live_bindings_version",
    }
)

MailboxActivationState = Literal["active"]


class _TmuxLocalDiscoveryUnavailableError(SessionManifestError):
    """Raised when tmux-local discovery pointers are unavailable for fallback."""


@dataclass(frozen=True)
class FilesystemMailboxBindingMutationResult:
    """Structured result for one late filesystem mailbox mutation."""

    mailbox: MailboxResolvedConfig | None
    shared_lifecycle_result: dict[str, object]
    activation_state: MailboxActivationState


@dataclass(frozen=True)
class AgentIdentityResolution:
    """Resolved `--agent-identity` details for session-control commands.

    Parameters
    ----------
    session_manifest_path:
        Resolved session manifest path used to resume/control a runtime session.
    canonical_agent_identity:
        Canonical tmux identity when resolved from a name input.
    agent_def_dir:
        Optional launch provenance for explicit relaunch planning.
    warnings:
        Non-fatal parsing warnings surfaced to CLI callers.
    """

    session_manifest_path: Path
    canonical_agent_identity: str | None = None
    agent_def_dir: Path | None = None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class _TmuxAuxiliaryWindowHandle:
    """Resolved tmux-owned execution handle for one auxiliary gateway window."""

    window_id: str
    window_index: str
    pane_id: str


@dataclass(frozen=True)
class ResolvedRuntimeIdentity:
    """Resolved runtime-owned identity metadata for a started tmux-backed session."""

    agent_name: str
    canonical_agent_name: str
    agent_id: str
    tmux_session_name: str
    warnings: tuple[str, ...] = ()


_ExecutionParams = ParamSpec("_ExecutionParams")
_ExecutionResult = TypeVar("_ExecutionResult")


def _validate_saved_execution_binding(binding: ExecutionBindingV1 | None) -> None:
    """Reject a saved runtime whose admitted owner differs from this operation."""

    try:
        validate_execution_owner(binding)
    except ValueError as exc:
        raise SessionManifestError(str(exc)) from exc


@contextmanager
def _runtime_execution_scope(plan: LaunchPlan) -> Iterator[None]:
    """Restore this runtime's owner and concrete socket for one operation."""

    _validate_saved_execution_binding(plan.execution_binding)
    socket_path = plan.metadata.get("tmux_socket_path")
    binding = plan.execution_binding
    if binding is not None and binding.tmux_socket is not None:
        if socket_path is not None and str(socket_path) != binding.tmux_socket:
            raise SessionManifestError("Saved tmux socket differs from execution binding")
        socket_path = binding.tmux_socket
    with (
        execution_binding_scope(binding),
        tmux_server_scope(str(socket_path) if socket_path is not None else None),
    ):
        yield


def _validate_controller_generation(controller: RuntimeSessionController) -> None:
    """Reject an old controller before it acts on a replacement runtime generation."""

    if (
        controller.execution_binding is None
        or controller.registry_generation_id is None
        or not controller.manifest_path.is_file()
    ):
        return
    payload = load_session_manifest(controller.manifest_path).payload
    expected = {controller.registry_generation_id, controller.m_registry_handoff_generation}
    if (
        payload["registry_generation_id"] not in expected
        or payload["agent_id"] != controller.agent_id
        or payload["runtime"].get("execution_binding")
        != controller.execution_binding.model_dump(mode="json")
    ):
        raise SessionManifestError(
            "Runtime execution generation changed; resolve the current manifest again"
        )


def require_active_managed_control_manifest(
    manifest_path: Path,
    *,
    generation_id: str,
    agent_id: str | None = None,
    execution_binding: ExecutionBindingV1 | None = None,
) -> SessionManifestPayloadV4:
    """Verify the saved path is still owned by this exact active managed generation."""

    if not manifest_path.is_absolute() or manifest_path != manifest_path.resolve():
        raise SessionManifestError("Managed control requires a canonical runtime manifest path")
    if agent_id is None or execution_binding is None:
        handle = load_session_manifest(manifest_path)
        selected = parse_session_manifest_payload(handle.payload, source=str(handle.path))
        if (
            selected.registry_generation_id != generation_id
            or (agent_id is not None and selected.agent_id != agent_id)
            or (
                execution_binding is not None
                and selected.runtime.execution_binding != execution_binding
            )
        ):
            raise SessionManifestError("Managed control generation or owner changed")
        agent_id = selected.agent_id
        execution_binding = selected.runtime.execution_binding
    if execution_binding is None:
        raise SessionManifestError("Managed control requires a saved execution binding")
    _validate_saved_execution_binding(execution_binding)
    record = load_managed_agent_record_by_agent_id(
        agent_id, env={HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR: execution_binding.registry_root}
    )
    if (
        record is None
        or record.agent_id != agent_id
        or record.execution_binding != execution_binding
        or record.generation_id != generation_id
        or Path(record.runtime.manifest_path) != manifest_path
        or record.lifecycle.state != "active"
        or not is_live_agent_record_fresh(record)
    ):
        raise SessionManifestError(
            "Managed control registry no longer names this active generation"
        )
    return load_registry_mode_authority(record)


def _execution_bound_controller(
    operation: Callable[Concatenate[RuntimeSessionController, _ExecutionParams], _ExecutionResult],
) -> Callable[Concatenate[RuntimeSessionController, _ExecutionParams], _ExecutionResult]:
    """Keep every controller operation bound when called by independent workers."""

    @wraps(operation)
    def bound(
        controller: RuntimeSessionController,
        /,
        *args: _ExecutionParams.args,
        **kwargs: _ExecutionParams.kwargs,
    ) -> _ExecutionResult:
        """Run under the controller's saved authority and restore caller scope."""

        if execution_is_read_only() and operation.__name__ not in {
            "gateway_status",
            "build_shared_registry_record",
        }:
            raise SessionManifestError("Read-only execution scope cannot mutate runtime state")
        with _runtime_execution_scope(controller.launch_plan):
            _validate_controller_generation(controller)
            return operation(controller, *args, **kwargs)

    return bound


def _execution_scoped_start(
    operation: Callable[_ExecutionParams, _ExecutionResult],
) -> Callable[_ExecutionParams, _ExecutionResult]:
    """Capture birth-time socket authority before a backend can touch tmux."""

    @wraps(operation)
    def bound(*args: _ExecutionParams.args, **kwargs: _ExecutionParams.kwargs) -> _ExecutionResult:
        """Pin the owner-selected or enclosing socket for the complete birth."""

        if execution_is_read_only():
            raise SessionManifestError("Read-only execution scope cannot launch an agent")
        binding = current_execution_binding()
        selected = binding.tmux_socket if binding is not None else None
        socket_path = selected or capture_tmux_socket_path()
        with tmux_server_scope(socket_path):
            return operation(*args, **kwargs)

    return bound


def _execution_scoped_resume(
    operation: Callable[_ExecutionParams, _ExecutionResult],
) -> Callable[_ExecutionParams, _ExecutionResult]:
    """Load saved socket and owner before backend reconstruction or local probes."""

    @wraps(operation)
    def bound(*args: _ExecutionParams.args, **kwargs: _ExecutionParams.kwargs) -> _ExecutionResult:
        """Read authority without interpreting another runtime's paths as local."""

        path = kwargs.get("session_manifest_path")
        if not isinstance(path, Path):
            raise SessionManifestError("Runtime resume requires an explicit manifest Path")
        handle = load_session_manifest(path)
        payload = parse_session_manifest_payload(handle.payload, source=str(handle.path))
        binding = payload.runtime.execution_binding
        _validate_saved_execution_binding(binding)
        selected_socket = payload.tmux.socket_path if payload.tmux is not None else None
        if binding is not None and binding.tmux_socket is not None:
            if selected_socket != binding.tmux_socket:
                raise SessionManifestError("Persisted tmux socket differs from execution binding")
        read_only = kwargs.get("read_only", False)
        with (
            execution_binding_scope(binding),
            tmux_server_scope(selected_socket),
            execution_read_only_scope(bool(read_only)),
        ):
            return operation(*args, **kwargs)

    return bound


@dataclass
class RuntimeSessionController:
    """Controller that binds a backend session to persisted manifest state."""

    launch_plan: LaunchPlan
    role_name: str
    brain_manifest_path: Path
    manifest_path: Path
    backend_session: InteractiveSession
    agent_def_dir: Path | None = None
    agent_identity: str | None = None
    agent_id: str | None = None
    tmux_session_name: str | None = None
    memory_root: Path | None = None
    memo_file: Path | None = None
    pages_dir: Path | None = None
    agent_identity_warnings: tuple[str, ...] = ()
    startup_warnings: tuple[str, ...] = ()
    parsing_mode: CaoParsingMode | None = None
    gateway_root: Path | None = None
    gateway_attach_path: Path | None = None
    gateway_auto_attach_error: str | None = None
    gateway_host: str | None = None
    gateway_port: int | None = None
    registry_generation_id: str | None = None
    gateway_admin_seed: GatewayLaunchSeed | None = None
    registry_launch_authority: RegistryLaunchAuthorityV1 = "runtime"
    agent_launch_authority: SessionManifestAgentLaunchAuthorityV1 | None = None
    operation_warnings: tuple[str, ...] = ()
    m_web_manifest_identity: dict[str, Any] | None = field(default=None, init=False, repr=False)
    m_registry_handoff_generation: str | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        """Strip retired mailbox-live metadata from persisted launch plans."""

        self.launch_plan = _without_retired_mailbox_metadata(self.launch_plan)
        binding = self.launch_plan.execution_binding or current_execution_binding()
        metadata = dict(self.launch_plan.metadata)
        if self.launch_plan.backend in _TMUX_BACKED_BACKENDS:
            selected = metadata.get("tmux_socket_path")
            metadata["tmux_socket_path"] = validate_tmux_socket_path(
                str(selected) if selected is not None else capture_tmux_socket_path()
            )
        self.launch_plan = replace(self.launch_plan, execution_binding=binding, metadata=metadata)
        if isinstance(self.backend_session, (DshWebSession, KimiWebSession)):
            self.m_web_manifest_identity = dict(self.backend_session.state.web_identity)
            self.backend_session.set_binding_changed_callback(self._persist_web_binding_change)

    @property
    def execution_binding(self) -> ExecutionBindingV1 | None:
        """Return the immutable owner authority associated with this runtime."""

        return self.launch_plan.execution_binding

    @property
    def tmux_socket_path(self) -> str | None:
        """Return the captured concrete owner-side tmux socket selector."""

        selected = self.launch_plan.metadata.get("tmux_socket_path")
        return str(selected) if selected is not None else None

    @contextmanager
    def execution_scope(self) -> Iterator[None]:
        """Restore this controller's authority for services calling its backend directly."""

        with _runtime_execution_scope(self.launch_plan):
            _validate_controller_generation(self)
            yield

    def require_managed_control_owner(self) -> SessionManifestPayloadV4:
        """Resolve owner and surface authority for a current managed control operation."""

        if self.registry_generation_id is None or self.agent_id is None:
            raise SessionManifestError("Managed control needs the selected agent and generation")
        manifest = require_active_managed_control_manifest(
            self.manifest_path,
            generation_id=self.registry_generation_id,
            agent_id=self.agent_id,
            execution_binding=self.execution_binding,
        )
        if (
            manifest.mode != self.launch_plan.mode
            or manifest.backend != self.launch_plan.backend
            or manifest.tool != self.launch_plan.tool
        ):
            raise SessionManifestError("Managed control mode differs from the selected backend")
        return manifest

    def control_capabilities(self) -> ManagedControlCapabilitiesV1:
        """Describe supported operations on this verified managed surface."""

        manifest = self.require_managed_control_owner()
        return managed_control_capabilities(
            tool=manifest.tool,
            mode=manifest.mode,
            backend=manifest.backend,
            native_surface=manifest.native_surface,
        )

    def observe_managed_service(self) -> ManagedControlObservationV1:
        """Read service evidence from the owned adapter without inferring native readiness."""

        with self.execution_scope():
            manifest = self.require_managed_control_owner()
            if manifest.mode != "service":
                raise BackendExecutionError("Native service observation requires service mode")
            observer = getattr(self.backend_session, "observe_managed_service", None)
            if callable(observer):
                observation = observer()
                if (
                    not isinstance(observation, ManagedControlObservationV1)
                    or observation.source != "service_native"
                ):
                    raise BackendExecutionError("Native service returned invalid control evidence")
                self.require_managed_control_owner()
                return observation
            return ManagedControlObservationV1(
                source="owner_registry", freshness="unknown", can_accept_prompt_now=False
            )

    @_execution_bound_controller
    def _persist_web_binding_change(self) -> None:
        """Publish an intentional Web reset before its next native input handoff."""

        self.persist_manifest(refresh_registry=True)
        self.ensure_gateway_capability()

    @_execution_bound_controller
    def send_web_prompt(
        self,
        prompt: str,
        *,
        admission_policy: str = "ready_only",
        operator: bool = True,
        turn_artifact_dir_name: str | None = None,
        session_selection: HeadlessTurnSessionSelection | None = None,
        execution_model: ModelConfig | None = None,
        deadline_epoch_ms: int | None = None,
        timeout_seconds: float = 300,
        refresh_registry: bool = True,
    ) -> list[SessionEvent]:
        """Submit explicitly scoped Web control while preserving native identity authority."""

        if not isinstance(self.backend_session, (DshWebSession, KimiWebSession)):
            raise SessionManifestError("Web prompt control requires a native Web backend")
        self._reset_operation_warnings()
        events = self.backend_session.send_web_prompt(
            prompt,
            admission_policy=admission_policy,
            operator=operator,
            turn_artifact_dir_name=turn_artifact_dir_name,
            session_selection=session_selection,
            execution_model=execution_model,
            deadline_epoch_ms=deadline_epoch_ms,
            timeout_seconds=timeout_seconds,
        )
        self.persist_manifest(refresh_registry=refresh_registry)
        return events

    @_execution_bound_controller
    def send_prompt(
        self,
        prompt: str,
        *,
        session_selection: HeadlessTurnSessionSelection | None = None,
        turn_artifact_dir_name: str | None = None,
        execution_model: ModelConfig | None = None,
        refresh_registry: bool = True,
    ) -> list[SessionEvent]:
        """Send a prompt and persist updated session state."""

        self._reset_operation_warnings()
        if isinstance(self.backend_session, (DshWebSession, KimiWebSession)):
            return self.send_web_prompt(
                prompt,
                session_selection=session_selection,
                turn_artifact_dir_name=turn_artifact_dir_name,
                execution_model=execution_model,
                refresh_registry=refresh_registry,
                operator=self.backend_session.m_dispatch_control is None,
            )
        if isinstance(self.backend_session, ManagedServiceSession):
            if session_selection is not None:
                raise SessionManifestError(
                    "Service requests use the currently bound native session."
                )
            events = self.backend_session.send_prompt(
                prompt,
                turn_artifact_dir_name=turn_artifact_dir_name,
                execution_model=execution_model,
            )
        elif isinstance(self.backend_session, HeadlessInteractiveSession):
            events = self.backend_session.send_prompt(
                prompt,
                turn_artifact_dir_name=turn_artifact_dir_name,
                session_selection=session_selection,
                execution_model=self._resolve_headless_execution_model(execution_model),
            )
        else:
            if execution_model is not None and not execution_model.is_empty():
                raise SessionManifestError(
                    "Execution overrides are only supported for headless runtime sessions."
                )
            events = self.backend_session.send_prompt(prompt)
        if isinstance(self.backend_session, HeadlessInteractiveSession):
            dispatch_control = getattr(self.backend_session, "m_dispatch_control", None)
            if dispatch_control is not None and dispatch_control.m_generation_id is not None:
                try:
                    current_generation = load_session_manifest(self.manifest_path).payload.get(
                        "registry_generation_id"
                    )
                except (OSError, SessionManifestError):
                    raise BackendExecutionError(
                        "Immediate dispatch execution identity is no longer current"
                    ) from None
                if current_generation != dispatch_control.m_generation_id:
                    raise BackendExecutionError(
                        "Immediate dispatch execution identity is no longer current"
                    )
        self.persist_manifest(refresh_registry=refresh_registry)
        return events

    def _resolve_headless_execution_model(
        self,
        execution_model: ModelConfig | None,
    ) -> ModelConfig | None:
        """Use native DSH defaults or resolve another tool's launch-owned defaults."""

        if execution_model is None or execution_model.is_empty():
            return None
        if self.launch_plan.backend in {"dsh_headless", "dsh_acp"}:
            # DSH consumes current materialized native defaults. Filling missing
            # request fields from launch provenance would mask later home edits.
            return execution_model
        try:
            brain_manifest = load_brain_manifest(self.brain_manifest_path)
            launch_model = extract_resolved_model_config_from_brain_manifest(
                brain_manifest,
                source=str(self.brain_manifest_path),
            )
        except ValueError as exc:
            raise SessionManifestError(str(exc)) from exc
        return resolve_execution_model_config(
            launch_model=launch_model,
            request_override=execution_model,
        ).config

    @_execution_bound_controller
    def send_mail_prompt(self, prompt_request: MailPromptRequest) -> list[SessionEvent]:
        """Send one runtime-owned mailbox prompt and persist updated session state."""

        self._reset_operation_warnings()
        from houmao.mailbox.scope import MailScope

        current = load_session_manifest(self.manifest_path)
        parsed = parse_session_manifest_payload(current.payload, source=str(current.path))
        bindings = mailboxes_resolved_config_from_payload(
            parsed.launch_plan.mailboxes, manifest_path=current.path
        )
        binding = bindings.binding_for(prompt_request.channel)
        if binding is None:
            raise SessionManifestError("Selected mail channel is absent")
        MailScope(binding.agent_id, prompt_request.channel, binding.binding_id).require_binding(
            prompt_request.expected_binding_id
        )
        resolve_live_mailbox_binding(durable_mailbox=binding)
        backend_send_mail_prompt = getattr(self.backend_session, "send_mail_prompt", None)
        if callable(backend_send_mail_prompt):
            typed_send_mail_prompt = cast(
                Callable[[MailPromptRequest], list[SessionEvent]],
                backend_send_mail_prompt,
            )
            events = typed_send_mail_prompt(prompt_request)
        else:
            events = self.backend_session.send_prompt(prompt_request.prompt)
        self.persist_manifest()
        return events

    @_execution_bound_controller
    def interrupt(self) -> SessionControlResult:
        """Interrupt in-flight backend work and persist state."""

        self._reset_operation_warnings()
        result = self.backend_session.interrupt()
        self.persist_manifest()
        return result

    @_execution_bound_controller
    def send_input_ex(
        self, sequence: str, *, escape_special_keys: bool = False
    ) -> SessionControlResult:
        """Send raw control input and persist any updated backend state.

        Parameters
        ----------
        sequence:
            Mixed literal/special-key control-input sequence to deliver.
        escape_special_keys:
            When true, disable `<[key-name]>` parsing and send the full
            sequence literally.

        Returns
        -------
        SessionControlResult
            Control-action result describing whether delivery succeeded.
        """

        self._reset_operation_warnings()
        if self.launch_plan.mode != "tui":
            return SessionControlResult(
                status="error",
                action="control_input",
                detail=f"Raw control input is unsupported for backend={self.launch_plan.backend!r}.",
            )
        if self.execution_binding is not None and self.registry_generation_id is not None:
            self.control_capabilities().require("send_keys")
        if isinstance(self.backend_session, CaoRestSession):
            result = self.backend_session.send_input_ex(
                sequence,
                escape_special_keys=escape_special_keys,
            )
            self.persist_manifest()
            return result

        backend_send_input_ex = getattr(self.backend_session, "send_input_ex", None)
        if callable(backend_send_input_ex):
            result = backend_send_input_ex(
                sequence,
                escape_special_keys=escape_special_keys,
            )
            if isinstance(result, SessionControlResult):
                self.persist_manifest()
                return result

        result = SessionControlResult(
            status="error",
            action="control_input",
            detail=(f"Raw control input is unsupported for backend={self.launch_plan.backend!r}."),
        )
        self.persist_manifest()
        return result

    @_execution_bound_controller
    def stop(self, *, force_cleanup: bool = False) -> SessionControlResult:
        """Terminate backend resources and persist state."""

        self._reset_operation_warnings()
        last_tmux_session_name = _tmux_session_name_for_controller(self)
        if self._is_tmux_backed():
            try:
                detach_result = self.detach_gateway()
            except GatewayDiscoveryError:
                detach_result = None
            except (OSError, SessionManifestError) as exc:
                self._record_registry_warning(
                    "Shared-registry refresh failed during pre-stop gateway detach",
                    exc,
                )
                detach_result = None
            if detach_result is not None and detach_result.status == "ok":
                self.gateway_host = None
                self.gateway_port = None
        if isinstance(
            self.backend_session,
            (HeadlessInteractiveSession, DshWebSession, KimiWebSession, ManagedServiceSession),
        ):
            self.backend_session.configure_stop_force_cleanup(force_cleanup=force_cleanup)
        try:
            result = self.backend_session.terminate()
        finally:
            _stop_hook_observation_for_controller(self)
        if result.status == "ok":
            self.tmux_session_name = last_tmux_session_name
            self.persist_manifest(refresh_registry=False)
            try:
                stopped_record = self.publish_stopped_shared_registry_record(
                    last_tmux_session_name=last_tmux_session_name
                )
                if stopped_record is None:
                    self.clear_shared_registry_record()
            except (OSError, SessionManifestError) as exc:
                self._record_registry_warning(
                    "Shared-registry stop transition failed after successful stop-session teardown",
                    exc,
                )
        else:
            self.persist_manifest()
        return result

    @_execution_bound_controller
    def close(self) -> None:
        """Close the backend session."""

        self._reset_operation_warnings()
        try:
            self.backend_session.close()
        finally:
            _stop_hook_observation_for_controller(self)
        self.persist_manifest()

    @_execution_bound_controller
    def refresh_mailbox_bindings(
        self,
        *,
        filesystem_root: Path | None = None,
    ) -> MailboxResolvedConfig:
        """Refresh mailbox env bindings for an active session."""

        self._reset_operation_warnings()
        mailbox = self.launch_plan.mailboxes.offline.binding
        if mailbox is None:
            raise SessionManifestError("Session does not have mailbox support enabled.")
        if not isinstance(mailbox, FilesystemMailboxResolvedConfig):
            raise SessionManifestError(
                f"Mailbox binding refresh is not implemented for transport={mailbox.transport!r}."
            )

        if filesystem_root is not None and filesystem_root.resolve() != mailbox.filesystem_root:
            raise SessionManifestError(
                "Offline refresh cannot select another registry store; leave and join explicitly"
            )
        from houmao.mailbox.registry_config import verify_selected_registry_store

        verify_selected_registry_store(mailbox.filesystem_root, mailbox.registry_root)
        refreshed = refresh_filesystem_mailbox_config(
            mailbox,
            filesystem_root=filesystem_root,
        )
        try:
            bootstrapped = bootstrap_resolved_mailbox(
                refreshed,
                manifest_path_hint=self.manifest_path,
                role_name=self.role_name,
            )
            if not isinstance(bootstrapped, FilesystemMailboxResolvedConfig):
                raise SessionManifestError(
                    "Mailbox binding refresh returned an unexpected non-filesystem mailbox type."
                )
            refreshed = bootstrapped
        except (RuntimeError, ValueError) as exc:
            raise SessionManifestError(f"Failed to refresh mailbox bindings: {exc}") from exc

        resolve_live_mailbox_binding(durable_mailbox=refreshed)
        self._commit_offline_mailbox_binding(refreshed)
        committed_binding = self.launch_plan.mailboxes.offline.binding
        assert committed_binding is not None
        return committed_binding

    def mailbox_activation_state(self) -> MailboxActivationState | None:
        """Return the current local mailbox activation state, when meaningful."""

        mailbox = self.launch_plan.mailboxes.offline.binding
        if mailbox is None:
            return None
        try:
            resolve_live_mailbox_binding(durable_mailbox=mailbox)
        except ValueError:
            return None
        return "active"

    @_execution_bound_controller
    def register_filesystem_mailbox(
        self,
        *,
        mailbox_root: Path | None = None,
        principal_id: str | None = None,
        address: str | None = None,
        mode: Literal["safe"] = "safe",
    ) -> FilesystemMailboxBindingMutationResult:
        """Attach one filesystem mailbox binding to the current session."""

        self._reset_operation_warnings()

        effective_principal_id = self.agent_id
        if effective_principal_id is None:
            raise SessionManifestError("Offline join requires a persisted agent_id")
        if principal_id is not None and principal_id != effective_principal_id:
            raise SessionManifestError("Offline owner must equal the persisted agent_id")
        effective_address = _normalize_optional_mailbox_text(
            address,
            field_name="address",
        ) or default_mailbox_address(
            tool=self.launch_plan.tool,
            role_name=self.role_name,
            agent_identity=self.agent_identity,
        )
        working_directory = self.launch_plan.working_directory.resolve()
        if mailbox_root is None and not os.environ.get(HOUMAO_GLOBAL_MAILBOX_DIR_ENV_VAR):
            ensure_project_aware_local_roots(cwd=working_directory)
        effective_mailbox_root = resolve_project_aware_mailbox_root(
            cwd=working_directory,
            explicit_root=mailbox_root,
        )

        from houmao.mailbox.registry_config import verify_selected_registry_store

        verify_selected_registry_store(effective_mailbox_root)
        previous = self.launch_plan.mailboxes.offline.binding
        if previous is not None and (
            not isinstance(previous, FilesystemMailboxResolvedConfig)
            or previous.address != effective_address
            or previous.filesystem_root != effective_mailbox_root.resolve()
        ):
            raise SessionManifestError(
                "Offline slot is already configured; leave before selecting another registration"
            )
        bootstrap_filesystem_mailbox(effective_mailbox_root)
        mailbox_paths = resolve_filesystem_mailbox_paths(effective_mailbox_root)
        shared_result = register_mailbox(
            effective_mailbox_root,
            RegisterMailboxRequest(
                mode=mode,
                address=effective_address,
                owner_principal_id=effective_principal_id,
                mailbox_kind="in_root",
                mailbox_path=mailbox_paths.mailbox_entry_path(effective_address),
                display_name=self.agent_identity,
                manifest_path_hint=str(self.manifest_path.resolve()),
                role=self.role_name,
            ),
        )

        updated_mailbox = FilesystemMailboxResolvedConfig(
            transport="filesystem",
            agent_id=effective_principal_id,
            binding_id=str(shared_result["active_registration_id"]),
            principal_id=effective_principal_id,
            address=effective_address,
            filesystem_root=effective_mailbox_root.resolve(),
            registry_root=resolve_registry_root(),
            bindings_version=mailbox_bindings_version_now(),
        )
        try:
            resolve_live_mailbox_binding(durable_mailbox=updated_mailbox)
        except ValueError as exc:
            raise SessionManifestError(str(exc)) from exc
        try:
            self._commit_offline_mailbox_binding(updated_mailbox)
        except Exception as exc:
            raise SessionManifestError(
                f"Registry confirmed registration {updated_mailbox.binding_id}; local publication failed. Retry the same join to reconcile."
            ) from exc
        return FilesystemMailboxBindingMutationResult(
            mailbox=self.launch_plan.mailboxes.offline.binding,
            shared_lifecycle_result=shared_result,
            activation_state=_mailbox_mutation_activation_state(
                controller=self,
                updated_mailbox=updated_mailbox,
            ),
        )

    @_execution_bound_controller
    def register_remote_offline_mailbox(
        self,
        *,
        registry_url: str,
        credential_file: Path,
        admin_credential_file: Path,
        address: str,
    ) -> FilesystemMailboxBindingMutationResult:
        """Enroll this owner without sharing host paths or restarting the body."""

        from houmao.mailbox.registry import prepare_member_credential
        from houmao.mailbox.registry_client import OfflineRegistryClient
        from houmao.mailbox.registry_config import read_private_credential

        if self.agent_id is None:
            raise SessionManifestError("Offline join requires a persisted agent_id")
        previous = self.launch_plan.mailboxes.offline.binding
        if previous is not None and (
            not isinstance(previous, RemoteRegistryMailboxResolvedConfig)
            or previous.address != address
            or previous.registry_url.rstrip("/") != registry_url.rstrip("/")
        ):
            raise SessionManifestError(
                "Offline slot is already configured; leave before selecting another registration"
            )
        prepare_member_credential(credential_file)
        administrator = OfflineRegistryClient.from_url(registry_url, admin_credential_file)
        member = administrator.enroll(
            agent_id=self.agent_id,
            address=address,
            member_credential=read_private_credential(credential_file),
            display_name=self.agent_identity,
        )
        binding = RemoteRegistryMailboxResolvedConfig(
            transport="registry",
            agent_id=self.agent_id,
            principal_id=self.agent_id,
            binding_id=member.registration_id,
            address=member.address,
            bindings_version=mailbox_bindings_version_now(),
            registry_url=registry_url,
            credential_ref=str(credential_file.resolve()),
            credential_file=credential_file.resolve(),
        )
        try:
            self._commit_offline_mailbox_binding(binding)
        except Exception as exc:
            raise SessionManifestError(
                f"Registry confirmed registration {member.registration_id}; local publication failed. Retry the same join to reconcile."
            ) from exc
        return FilesystemMailboxBindingMutationResult(
            mailbox=self.launch_plan.mailboxes.offline.binding,
            shared_lifecycle_result=member.model_dump(),
            activation_state="active",
        )

    @_execution_bound_controller
    def unregister_filesystem_mailbox(
        self,
        *,
        mode: Literal["deactivate", "purge"] = "deactivate",
    ) -> FilesystemMailboxBindingMutationResult:
        """Remove one filesystem mailbox binding from the current session."""

        self._reset_operation_warnings()

        mailbox = self.launch_plan.mailboxes.offline.binding
        if mailbox is None:
            raise SessionManifestError("Session does not have a filesystem mailbox binding.")
        if isinstance(mailbox, RemoteRegistryMailboxResolvedConfig):
            from houmao.mailbox.registry_client import OfflineRegistryClient

            if mailbox.credential_file is None:
                raise SessionManifestError(
                    "Remote offline release requires a private credential file"
                )
            member = OfflineRegistryClient.from_url(
                mailbox.registry_url, mailbox.credential_file
            ).release(purge=mode == "purge", expected_registration_id=mailbox.binding_id)
            shared_result = member.model_dump()
        elif isinstance(mailbox, FilesystemMailboxResolvedConfig):
            from houmao.mailbox.registry_config import verify_selected_registry_store
            from houmao.mailbox.authority_lock import offline_authority_lock

            verify_selected_registry_store(mailbox.filesystem_root, mailbox.registry_root)
            with offline_authority_lock(mailbox.filesystem_root):
                with sqlite3.connect(mailbox.filesystem_root / "index.sqlite") as connection:
                    original = connection.execute(
                        "SELECT owner_principal_id, address, status FROM mailbox_registrations WHERE registration_id = ?",
                        (mailbox.binding_id,),
                    ).fetchone()
                if original is not None and original[:2] != (self.agent_id, mailbox.address):
                    raise SessionManifestError("Offline registration belongs to another owner")
                if original is not None and original[2] == "active":
                    resolve_live_mailbox_binding(durable_mailbox=mailbox)
                    shared_result = deregister_mailbox(
                        mailbox.filesystem_root,
                        DeregisterMailboxRequest(mode=mode, address=mailbox.address),
                    )
                else:
                    # A confirmed release may have lost its local publication response.
                    # Retiring this stale slot must never release the next address owner.
                    shared_result = {
                        "ok": True,
                        "address": mailbox.address,
                        "released_registration_id": mailbox.binding_id,
                        "action": "already_released",
                    }
        else:
            raise SessionManifestError("Online bindings cannot be released as offline membership")
        self._commit_offline_mailbox_binding(None)
        return FilesystemMailboxBindingMutationResult(
            mailbox=None,
            shared_lifecycle_result=shared_result,
            activation_state=_mailbox_mutation_activation_state(
                controller=self,
                updated_mailbox=None,
            ),
        )

    @_execution_bound_controller
    def _commit_offline_mailbox_binding(self, binding: MailboxResolvedConfig | None) -> None:
        """Commit a prepared registration without overwriting the online slot."""

        if self.agent_id is None:
            raise SessionManifestError("Mail mutation requires persisted agent_id")
        session_id = _runtime_session_id_from_manifest_path(self.manifest_path)
        if session_id is None:
            raise SessionManifestError("Mail mutation requires a runtime-owned session identity")
        committed = mutate_session_mailbox_binding(
            self.manifest_path,
            channel="offline",
            expected_revision=self.launch_plan.mailboxes.offline.revision,
            binding=binding,
            agent_id=self.agent_id,
            session_id=session_id,
        )
        payload = parse_session_manifest_payload(committed.payload, source=str(committed.path))
        previous = self.launch_plan
        self.launch_plan = replace(
            self.launch_plan,
            mailboxes=mailboxes_resolved_config_from_payload(
                payload.launch_plan.mailboxes, manifest_path=committed.path
            ),
        )
        revision = self.launch_plan.mailboxes.offline.revision
        try:
            _refresh_mailbox_projection_and_backend_launch_plan(
                controller=self, previous_launch_plan=previous, updated_launch_plan=self.launch_plan
            )
        except (OSError, SessionManifestError) as exc:
            self._record_registry_warning(
                f"Offline binding committed at revision {revision}; backend projection refresh "
                "failed; resolve status and reconcile the committed binding",
                exc,
            )
        try:
            self.refresh_shared_registry_record()
        except (OSError, SessionManifestError) as exc:
            reconciliation = (
                "resolve status or retry join to reconcile"
                if binding is not None
                else "resolve status to reconcile the released offline slot"
            )
            self._record_registry_warning(
                f"Offline binding committed at revision {revision}; shared-registry projection "
                f"refresh failed; {reconciliation}",
                exc,
            )

    @_execution_bound_controller
    def relaunch(
        self,
        *,
        chat_session: RelaunchChatSessionSelection | None = None,
    ) -> SessionControlResult:
        """Relaunch the tmux-backed managed-agent surface without rebuilding the home."""

        self._reset_operation_warnings()
        try:
            effective_chat_session = _resolve_relaunch_chat_session_selection(
                controller=self,
                requested=chat_session,
            )
        except ValueError as exc:
            return SessionControlResult(
                status="error",
                action="relaunch",
                detail=str(exc),
            )
        authority = _resolve_manifest_relaunch_authority(self)
        if authority.primary_window_index != _PRIMARY_AGENT_WINDOW_INDEX:
            return SessionControlResult(
                status="error",
                action="relaunch",
                detail=(
                    "Manifest relaunch authority is invalid because the primary window index "
                    f"is `{authority.primary_window_index}` instead of `{_PRIMARY_AGENT_WINDOW_INDEX}`."
                ),
            )

        session_name = _tmux_session_name_for_controller(self)
        if session_name is None or session_name.strip() != authority.tmux_session_name:
            return SessionControlResult(
                status="error",
                action="relaunch",
                detail=(
                    "Manifest relaunch authority is stale because the controller tmux session "
                    f"`{session_name}` does not match the persisted relaunch session "
                    f"`{authority.tmux_session_name}`."
                ),
            )

        if _backend_requires_provider_start_relaunch(self.launch_plan.backend):
            try:
                updated_launch_plan = _build_provider_start_launch_plan_for_relaunch(self)
                validate_kimi_tui_chat_selection(updated_launch_plan, effective_chat_session)
                updated_launch_plan = _activate_hook_observation_for_controller(
                    controller=self,
                    launch_plan=updated_launch_plan,
                )
                _refresh_backend_launch_plan(
                    backend_session=self.backend_session,
                    launch_plan=updated_launch_plan,
                )
            except (
                FileNotFoundError,
                LaunchPlanError,
                LaunchPolicyResolutionError,
                RuntimeError,
                SessionManifestError,
                ValueError,
            ) as exc:
                self.persist_manifest()
                return SessionControlResult(
                    status="error",
                    action="relaunch",
                    detail=str(exc),
                )
            self.launch_plan = updated_launch_plan

        try:
            result = _relaunch_backend_session(self, chat_session=effective_chat_session)
        except (OSError, ValueError, SessionManifestError, GatewayAccessError):
            _stop_hook_observation_for_controller(self)
            return SessionControlResult(
                status="error", action="relaunch", detail="Gateway generation setup failed."
            )
        if result.status != "ok":
            _stop_hook_observation_for_controller(self)
            self.persist_manifest()
            return result

        try:
            _refresh_pair_launch_registration(self)
        except SessionManifestError as exc:
            self.persist_manifest()
            return SessionControlResult(
                status="error",
                action="relaunch",
                detail=str(exc),
            )

        if isinstance(self.backend_session, (DshWebSession, KimiWebSession)):
            try:
                self.persist_manifest(refresh_registry=False)
                self.refresh_shared_registry_record()
                self.ensure_gateway_capability()
            except (OSError, SessionManifestError) as exc:
                return SessionControlResult(status="error", action="relaunch", detail=str(exc))
        else:
            self.persist_manifest()
        return result

    @_execution_bound_controller
    def revive_stopped_session(
        self,
        *,
        chat_session: RelaunchChatSessionSelection | None = None,
    ) -> SessionControlResult:
        """Revive one stopped tmux-backed managed-agent runtime without rebuilding its home."""

        self._reset_operation_warnings()
        if not _backend_supports_stopped_session_relaunch(self.launch_plan.backend):
            return SessionControlResult(
                status="error",
                action="relaunch",
                detail=(
                    "Stopped-session revival is only supported for local tmux-backed backends "
                    f"({sorted(_STOPPED_SESSION_RELAUNCH_BACKENDS)}), got "
                    f"{self.launch_plan.backend!r}."
                ),
            )
        try:
            effective_chat_session = _resolve_relaunch_chat_session_selection(
                controller=self,
                requested=chat_session,
            )
        except ValueError as exc:
            _rollback_stopped_session_revival(self)
            return SessionControlResult(
                status="error",
                action="relaunch",
                detail=str(exc),
            )

        if _backend_requires_provider_start_relaunch(self.launch_plan.backend):
            try:
                updated_launch_plan = _build_provider_start_launch_plan_for_relaunch(self)
                validate_kimi_tui_chat_selection(updated_launch_plan, effective_chat_session)
                updated_launch_plan = _activate_hook_observation_for_controller(
                    controller=self,
                    launch_plan=updated_launch_plan,
                )
                _refresh_backend_launch_plan(
                    backend_session=self.backend_session,
                    launch_plan=updated_launch_plan,
                )
            except (
                FileNotFoundError,
                LaunchPlanError,
                LaunchPolicyResolutionError,
                RuntimeError,
                SessionManifestError,
                ValueError,
            ) as exc:
                _rollback_stopped_session_revival(self)
                return SessionControlResult(
                    status="error",
                    action="relaunch",
                    detail=str(exc),
                )
            self.launch_plan = updated_launch_plan

        if isinstance(self.backend_session, HeadlessInteractiveSession):
            try:
                self.backend_session.prepare_stopped_revival(
                    tmux_session_name=self._require_tmux_session_name()
                )
            except (BackendExecutionError, TmuxCommandError) as exc:
                _stop_hook_observation_for_controller(self)
                _rollback_stopped_session_revival(self)
                return SessionControlResult(status="error", action="relaunch", detail=str(exc))

        try:
            result = _relaunch_backend_session(self, chat_session=effective_chat_session)
        except (OSError, ValueError, SessionManifestError, GatewayAccessError):
            _stop_hook_observation_for_controller(self)
            _rollback_stopped_session_revival(self)
            return SessionControlResult(
                status="error", action="relaunch", detail="Gateway generation setup failed."
            )
        if result.status != "ok":
            _stop_hook_observation_for_controller(self)
            _rollback_stopped_session_revival(self)
            return result

        try:
            self.persist_manifest(refresh_registry=False)
            if isinstance(self.backend_session, (DshWebSession, KimiWebSession)):
                self.refresh_shared_registry_record()
            self.ensure_gateway_capability()
            _refresh_pair_launch_registration(self)
        except (OSError, SessionManifestError) as exc:
            _rollback_stopped_session_revival(self)
            return SessionControlResult(
                status="error",
                action="relaunch",
                detail=str(exc),
            )

        self.persist_manifest()
        return result

    @_execution_bound_controller
    def persist_manifest(self, *, refresh_registry: bool = True) -> None:
        """Persist current backend state to session manifest."""

        backend_state = _backend_state_for_session(self.backend_session)
        self.tmux_session_name = _tmux_session_name_for_controller(self)
        self.agent_launch_authority = _agent_launch_authority_with_primary_handles(
            self.agent_launch_authority,
            backend_state=backend_state,
        )
        payload = build_session_manifest_payload(
            SessionManifestRequest(
                launch_plan=self.launch_plan,
                role_name=self.role_name,
                brain_manifest_path=self.brain_manifest_path,
                backend_state=backend_state,
                agent_name=self.agent_identity,
                agent_id=self.agent_id,
                tmux_session_name=self.tmux_session_name,
                session_id=_runtime_session_id_from_manifest_path(self.manifest_path),
                memory_root=self.memory_root,
                memo_file=self.memo_file,
                pages_dir=self.pages_dir,
                agent_def_dir=self.agent_def_dir,
                registry_generation_id=self.registry_generation_id,
                gateway_admin_seed=self.gateway_admin_seed,
                registry_launch_authority=self.registry_launch_authority,
                agent_launch_authority=self.agent_launch_authority,
            )
        )
        committed = write_session_manifest(
            self.manifest_path,
            payload,
            expected_web_identity=self.m_web_manifest_identity,
            expected_registry_generation_id=self.m_registry_handoff_generation
            or (
                self.m_web_manifest_identity.get("generation")
                if self.m_web_manifest_identity is not None
                else self.registry_generation_id
            ),
        )
        if isinstance(self.backend_session, (DshWebSession, KimiWebSession)):
            self.m_web_manifest_identity = dict(committed.payload["backend_state"]["web_identity"])
        self.launch_plan = replace(
            self.launch_plan,
            mailboxes=mailboxes_resolved_config_from_payload(
                committed.payload["launch_plan"]["mailboxes"], manifest_path=self.manifest_path
            ),
        )
        update_plan = getattr(self.backend_session, "update_launch_plan", None)
        if callable(update_plan):
            update_plan(self.launch_plan)
        if refresh_registry:
            try:
                self.refresh_shared_registry_record()
            except (OSError, SessionManifestError) as exc:
                self._record_registry_warning(
                    "Shared-registry refresh failed after manifest persistence",
                    exc,
                )

    def consume_operation_warnings(self) -> tuple[str, ...]:
        """Return and clear non-fatal warnings captured during the last operation."""

        warnings = self.operation_warnings
        self.operation_warnings = ()
        return warnings

    @_execution_bound_controller
    def ensure_gateway_capability(
        self,
        *,
        blueprint_gateway_defaults: BlueprintGatewayDefaults | None = None,
    ) -> None:
        """Publish gateway capability from current persisted session authority.

        A gateway may have committed newer native conversation state than this
        controller holds. Capability discovery and gateway lifecycle actions do
        not own that state and must never persist the controller's snapshot.
        """

        if not self._is_tmux_backed() or _tmux_session_name_for_controller(self) is None:
            return
        handle = load_session_manifest(self.manifest_path)
        payload = parse_session_manifest_payload(handle.payload, source=str(handle.path))
        self.launch_plan = replace(
            self.launch_plan,
            mailboxes=mailboxes_resolved_config_from_payload(
                payload.launch_plan.mailboxes, manifest_path=handle.path
            ),
        )
        session_name = payload.tmux_session_name
        if session_name is None:
            return
        session_id = _runtime_session_id_from_manifest_path(self.manifest_path)
        if session_id is None:
            return
        paths = ensure_gateway_capability(
            GatewayCapabilityPublication(
                manifest_path=self.manifest_path,
                backend=payload.backend,
                tool=payload.tool,
                session_id=session_id,
                tmux_session_name=session_name,
                working_directory=Path(payload.working_directory),
                backend_state=cast(GatewayJsonObject, payload.backend_state),
                agent_def_dir=Path(payload.runtime.agent_def_dir)
                if payload.runtime.agent_def_dir is not None
                else None,
                blueprint_gateway_defaults=blueprint_gateway_defaults,
            )
        )
        stable_discovery_env = {
            AGENT_MANIFEST_PATH_ENV_VAR: str(self.manifest_path.resolve()),
        }
        stable_discovery_env[AGENT_ID_ENV_VAR] = payload.agent_id
        memory = _memory_from_manifest_payload(payload=payload)
        if memory is not None:
            stable_discovery_env.update(memory_env(memory))
        set_tmux_session_environment_shared(
            session_name=session_name,
            env_vars=stable_discovery_env,
        )
        if has_tmux_session_shared(session_name=session_name).returncode == 0:
            try:
                unset_tmux_session_environment_shared(
                    session_name=session_name,
                    variable_names=(
                        [
                            AGENT_GATEWAY_ATTACH_PATH_ENV_VAR,
                            AGENT_GATEWAY_ROOT_ENV_VAR,
                        ]
                        + sorted(_RETIRED_MEMORY_ENV_VARS)
                    ),
                )
            except TmuxCommandError:
                pass
        self.gateway_root = paths.gateway_root
        self.gateway_attach_path = paths.attach_path
        self.refresh_shared_registry_record()

    @_execution_bound_controller
    def attach_gateway(
        self,
        *,
        host_override: str | None = None,
        port_override: int | None = None,
        execution_mode_override: GatewayCurrentExecutionMode | None = None,
        tui_tracking_timing_overrides: GatewayTuiTrackingTimingOverridesV1 | None = None,
        plugin_config: GatewayPluginConfiguration | None = None,
        access_config: GatewayDeployment | None = None,
    ) -> GatewayControlResult:
        """Start a live gateway instance for the addressed session."""

        with _gateway_lifecycle_lock(self.manifest_path):
            _validate_controller_generation(self)
            result = _attach_gateway_for_controller(
                self,
                host_override=host_override,
                port_override=port_override,
                execution_mode_override=execution_mode_override,
                tui_tracking_timing_overrides=tui_tracking_timing_overrides,
                plugin_config=plugin_config,
                access_config=access_config,
            )
            if result.status == "ok":
                self.refresh_shared_registry_record()
            return result

    @_execution_bound_controller
    def detach_gateway(self) -> GatewayControlResult:
        """Stop a live gateway instance while preserving attachability metadata."""

        with _gateway_lifecycle_lock(self.manifest_path):
            _validate_controller_generation(self)
            result = _detach_gateway_for_controller(self)
            if result.status == "ok":
                self.refresh_shared_registry_record()
            return result

    @_execution_bound_controller
    def gateway_status(self) -> GatewayStatusV1:
        """Return current gateway status from the live gateway or stable state file."""

        return _gateway_status_for_controller(self)

    @_execution_bound_controller
    def send_prompt_via_gateway(self, prompt: str) -> GatewayAcceptedRequestV1:
        """Submit a prompt through the live gateway queue."""

        return _submit_gateway_request_for_controller(
            self,
            GatewayRequestCreateV1(
                kind="submit_prompt",
                payload=GatewayRequestPayloadSubmitPromptV1(prompt=prompt),
            ),
        )

    @_execution_bound_controller
    def control_prompt_via_gateway(
        self,
        prompt: str,
        *,
        admission_policy: GatewayPromptAdmissionPolicy = "ready_only",
    ) -> GatewayPromptControlResultV1:
        """Submit one prompt through the live gateway direct-control path."""

        return _submit_gateway_prompt_control_for_controller(
            self,
            GatewayPromptControlRequestV1(
                prompt=prompt,
                admission_policy=admission_policy,
            ),
        )

    @_execution_bound_controller
    def interrupt_via_gateway(self) -> GatewayAcceptedRequestV1:
        """Submit an interrupt through the live gateway queue."""

        return _submit_gateway_request_for_controller(
            self,
            GatewayRequestCreateV1(
                kind="interrupt",
                payload=GatewayRequestPayloadInterruptV1(),
            ),
        )

    def _is_tmux_backed(self) -> bool:
        """Return whether this controller manages a tmux-backed backend."""

        return self.launch_plan.backend in _TMUX_BACKED_BACKENDS

    def _require_tmux_session_name(self) -> str:
        """Return the controller's tmux session name."""

        session_name = _tmux_session_name_for_controller(self)
        if session_name is None:
            raise SessionManifestError(
                f"backend={self.launch_plan.backend!r} is missing a tmux session binding."
            )
        return session_name

    @_execution_bound_controller
    def refresh_shared_registry_record(self) -> ManagedAgentRegistryRecordV3 | None:
        """Publish or refresh the shared-registry record for this live session."""

        if not self.should_publish_shared_registry_record():
            return None
        record = self.build_shared_registry_record()
        if record is None:
            return None
        existing_record = resolve_live_agent_record_by_agent_id(record.agent_id)
        if existing_record is not None and existing_record.agent_name != record.agent_name:
            self._record_registry_warning(
                "Shared-registry agent-id reuse warning",
                SessionManifestError(
                    "authoritative agent_id "
                    f"`{record.agent_id}` is being reused with canonical agent name "
                    f"`{record.agent_name}` after previously publishing "
                    f"`{existing_record.agent_name}`"
                ),
            )
        if self.m_registry_handoff_generation is not None:
            published = publish_live_agent_record(
                record, expected_generation_id=self.m_registry_handoff_generation
            )
            self.m_registry_handoff_generation = None
            return published
        return publish_live_agent_record(record)

    def should_publish_shared_registry_record(self) -> bool:
        """Return whether runtime is the launch authority for registry publication."""

        return self.registry_launch_authority == "runtime"

    @_execution_bound_controller
    def build_shared_registry_record(self) -> ManagedAgentRegistryRecordV3 | None:
        """Build the current pointer-oriented shared-registry record for this session."""

        return _build_shared_registry_record_for_controller(self)

    @_execution_bound_controller
    def publish_stopped_shared_registry_record(
        self,
        *,
        last_tmux_session_name: str | None,
    ) -> ManagedAgentRegistryRecordV3 | None:
        """Publish one stopped lifecycle record after successful local teardown."""

        record = _build_stopped_shared_registry_record_for_controller(
            self,
            last_tmux_session_name=last_tmux_session_name,
        )
        if record is None:
            return None
        return publish_live_agent_record(record)

    @_execution_bound_controller
    def clear_shared_registry_record(self) -> bool:
        """Remove this session's shared-registry record during authoritative teardown."""

        if not self._is_tmux_backed() or self.agent_id is None:
            return False
        return remove_live_agent_record(
            self.agent_id,
            generation_id=self.registry_generation_id,
        )

    def _reset_operation_warnings(self) -> None:
        """Clear non-fatal warnings before starting a new controller operation."""

        self.operation_warnings = ()

    def _record_registry_warning(self, prefix: str, exc: Exception) -> None:
        """Capture one non-fatal shared-registry warning for the current operation."""

        message = f"{prefix}: {exc}"
        self.operation_warnings = (*self.operation_warnings, message)
        _LOGGER.warning(message)


def _effective_role_prompt_from_brain_manifest(
    manifest: dict[str, Any],
    *,
    fallback: str,
) -> str:
    """Return the effective role prompt recorded in one brain manifest."""

    stored_role_prompt = _stored_role_prompt_from_brain_manifest(manifest)
    if stored_role_prompt is None:
        return fallback
    return stored_role_prompt


def _stored_role_prompt_from_brain_manifest(manifest: dict[str, Any]) -> str | None:
    """Return one stored effective role prompt from a brain manifest when present."""

    inputs = manifest.get("inputs")
    if not isinstance(inputs, dict):
        return None
    raw_value = inputs.get("role_prompt_text")
    if raw_value is None:
        return None
    if not isinstance(raw_value, str):
        raise SessionManifestError("Brain manifest inputs.role_prompt_text must be a string.")
    return raw_value


def _managed_prompt_header_payload_from_brain_manifest(
    manifest: dict[str, Any],
) -> dict[str, Any] | None:
    """Return one stored managed-header metadata payload when present."""

    inputs = manifest.get("inputs")
    if not isinstance(inputs, dict):
        return None
    raw_value = inputs.get("managed_prompt_header")
    if raw_value is None:
        return None
    if not isinstance(raw_value, dict):
        raise SessionManifestError("Brain manifest inputs.managed_prompt_header must be a mapping.")
    return cast(dict[str, Any], raw_value)


def _managed_prompt_header_enabled_from_brain_manifest(manifest: dict[str, Any]) -> bool | None:
    """Return one persisted managed-header enabled flag when present."""

    payload = _managed_prompt_header_payload_from_brain_manifest(manifest)
    if payload is None:
        return None
    raw_enabled = payload.get("enabled")
    if raw_enabled is None:
        return None
    if not isinstance(raw_enabled, bool):
        raise SessionManifestError(
            "Brain manifest inputs.managed_prompt_header.enabled must be a boolean."
        )
    return raw_enabled


@_execution_scoped_start
def start_runtime_session(
    *,
    agent_def_dir: Path,
    brain_manifest_path: Path,
    role_name: str | None,
    runtime_root: Path | None = None,
    project_overlay_dir: Path | None = None,
    shared_runtime_root: Path | None = None,
    shared_mailbox_root: Path | None = None,
    private_workspace_root: Path | None = None,
    jobs_root: Path | None = None,
    memory_paths: AgentMemoryPaths | None = None,
    backend: BackendKind | None = None,
    mode: RunMode | None = None,
    working_directory: Path | None = None,
    api_base_url: str = "http://localhost:9889",
    cao_profile_store_dir: Path | None = None,
    agent_identity: str | None = None,
    agent_name: str | None = None,
    agent_id: str | None = None,
    agent_id_mode: AgentIdMode | None = None,
    cao_parsing_mode: CaoParsingMode | None = None,
    mailboxes: MailboxesDeclarativeConfig | None = None,
    mailbox_transport: str | None = None,
    mailbox_root: Path | None = None,
    mailbox_account_dir: Path | None = None,
    mailbox_principal_id: str | None = None,
    mailbox_address: str | None = None,
    mailbox_stalwart_base_url: str | None = None,
    mailbox_stalwart_jmap_url: str | None = None,
    mailbox_stalwart_management_url: str | None = None,
    mailbox_stalwart_login_identity: str | None = None,
    headless_display_style: HeadlessDisplayStyle | None = None,
    headless_display_detail: HeadlessDisplayDetail | None = None,
    blueprint_gateway_defaults: BlueprintGatewayDefaults | None = None,
    gateway_auto_attach: bool = False,
    gateway_host: str | None = None,
    gateway_port: int | None = None,
    gateway_execution_mode_override: GatewayCurrentExecutionMode | None = None,
    gateway_tui_tracking_timing_overrides: GatewayTuiTrackingTimingOverridesV1 | None = None,
    gateway_plugins: GatewayPluginConfiguration | None = None,
    gateway_admin_seed: GatewayLaunchSeed | None = None,
    gateway_access_config: GatewayDeployment | None = None,
    tmux_session_name: str | None = None,
    default_tmux_session_name: str | None = None,
    launch_env_overrides: dict[str, str] | None = None,
    managed_force_mode: ManagedLaunchForceMode | None = None,
    registry_launch_authority: RegistryLaunchAuthorityV1 = "runtime",
) -> RuntimeSessionController:
    """Start a new runtime session and persist its session manifest."""

    if backend == "houmao_server_rest":
        raise SessionManifestError(
            "backend='houmao_server_rest' is retired. Use maintained local/headless "
            "manager workflows or `houmao-passive-server` API-managed launches instead."
        )
    if (gateway_host is not None or gateway_port is not None) and not gateway_auto_attach:
        raise SessionManifestError(
            "Gateway host or port overrides require launch-time gateway attach."
        )
    if gateway_execution_mode_override is not None and not gateway_auto_attach:
        raise SessionManifestError(
            "Gateway execution-mode overrides require launch-time gateway attach."
        )
    if gateway_plugins is not None and not gateway_auto_attach:
        raise SessionManifestError("Gateway plugin selections require launch-time gateway attach.")
    if gateway_access_config is not None and not gateway_auto_attach:
        raise SessionManifestError(
            "Gateway deployment settings require launch-time gateway attach."
        )
    if (
        gateway_tui_tracking_timing_overrides is not None
        and gateway_tui_tracking_timing_overrides.has_values()
        and not gateway_auto_attach
    ):
        raise SessionManifestError(
            "Gateway TUI tracking timing overrides require launch-time gateway attach."
        )

    manifest = load_brain_manifest(brain_manifest_path)
    tool = str(manifest.get("inputs", {}).get("tool", ""))
    selected_backend = resolve_run_mode(tool, mode=mode, backend=backend).backend
    if selected_backend == "kimi_web":
        executable = manifest.get("runtime", {}).get("launch_executable")
        if not isinstance(executable, str) or not executable.strip():
            raise LaunchPlanError("Kimi Web brain manifest is missing runtime.launch_executable.")
        validate_kimi_web_launch_version(executable=executable)
    resolved_gateway_defaults = blueprint_gateway_defaults or _gateway_defaults_from_brain_manifest(
        manifest,
        source=str(brain_manifest_path),
    )
    resolved_role_name = role_name.strip() if role_name is not None and role_name.strip() else None
    if resolved_role_name is None:
        role_package = RolePackage(
            role_name=_BRAIN_ONLY_ROLE_NAME,
            system_prompt="",
            path=(agent_def_dir / "roles" / _BRAIN_ONLY_ROLE_NAME / "system-prompt.md").resolve(),
        )
    else:
        role_package = load_role_package(agent_def_dir, resolved_role_name)
    role_package = replace(
        role_package,
        system_prompt=_effective_role_prompt_from_brain_manifest(
            manifest,
            fallback=role_package.system_prompt,
        ),
    )

    try:
        effective_runtime_root = resolve_runtime_root(explicit_root=runtime_root)
    except ValueError as exc:
        raise SessionManifestError(str(exc)) from exc
    if mode_for_backend(selected_backend) in {"web", "service"} and (
        cao_parsing_mode is not None
        or headless_display_style is not None
        or headless_display_detail is not None
        or (
            gateway_tui_tracking_timing_overrides is not None
            and gateway_tui_tracking_timing_overrides.has_values()
        )
    ):
        if mode_for_backend(selected_backend) == "web":
            raise SessionManifestError(
                "Web mode does not support terminal parser, display, or timing controls."
            )
        raise SessionManifestError(
            "Managed service mode does not support terminal parser, display, or timing controls."
        )
    if selected_backend in {"dsh_headless", "dsh_acp", "dsh_web"}:
        executable = manifest["runtime"].get("launch_executable")
        if not isinstance(executable, str) or not executable.strip():
            raise LaunchPlanError("DSH brain manifest is missing runtime.launch_executable.")
        validate_dsh_launch_version(executable=executable, backend=selected_backend)
    if gateway_auto_attach and selected_backend not in _TMUX_BACKED_BACKENDS:
        raise SessionManifestError(
            "Launch-time gateway attach is only supported for tmux-backed backends."
        )
    selected_workdir = (working_directory or Path.cwd()).resolve()
    session_id = generate_session_id(prefix=selected_backend)

    resolved_runtime_identity: ResolvedRuntimeIdentity | None = None
    non_tmux_agent_id: str | None = None
    agent_identity_warnings: tuple[str, ...] = ()
    startup_warnings: tuple[str, ...] = ()
    if selected_backend in _TMUX_BACKED_BACKENDS:
        resolved_runtime_identity = _resolve_start_session_identity(
            manifest=manifest,
            tool=tool,
            role_name=role_package.role_name,
            requested_agent_name=agent_name,
            requested_agent_identity=agent_identity,
            requested_agent_id=agent_id,
            requested_agent_id_mode=agent_id_mode,
            requested_tmux_session_name=tmux_session_name,
            default_tmux_session_name=default_tmux_session_name,
        )
        agent_identity_warnings = resolved_runtime_identity.warnings
        existing_record = resolve_live_agent_record_by_agent_id(resolved_runtime_identity.agent_id)
        if (
            existing_record is not None
            and existing_record.agent_name != resolved_runtime_identity.agent_name
        ):
            startup_warnings = (
                "authoritative agent_id "
                f"`{resolved_runtime_identity.agent_id}` was previously published as "
                f"`{existing_record.agent_name}` and is now starting as "
                f"`{resolved_runtime_identity.agent_name}`",
            )
    else:
        if agent_identity is not None:
            raise SessionManifestError(
                "start-session --agent-identity requires a tmux-backed backend."
            )
        stored_agent_id = _built_manifest_identity(manifest)[1]
        if stored_agent_id is not None:
            if agent_id_mode is not None or (
                agent_id is not None and normalize_managed_agent_id(agent_id) != stored_agent_id
            ):
                raise SessionManifestError("An existing-agent brain cannot change its agent_id.")
            non_tmux_agent_id = stored_agent_id
        else:
            non_tmux_agent_id = (
                AgentIdentityCreation(
                    agent_name=agent_name, agent_id=agent_id, agent_id_mode=agent_id_mode
                )
                .resolve()
                .agent_id
            )

    _ = jobs_root
    resolved_memory = memory_paths
    if selected_backend in _TMUX_BACKED_BACKENDS and resolved_runtime_identity is not None:
        if resolved_memory is None:
            source_roots = resolve_project_aware_local_roots(cwd=selected_workdir)
            resolved_memory = resolve_agent_memory(
                overlay_root=source_roots.overlay_root,
                agent_id=resolved_runtime_identity.agent_id,
            )
        ensure_agent_memory(resolved_memory)

    declared_mailboxes = mailboxes or _declared_mailbox_from_manifest(
        manifest, source=str(brain_manifest_path)
    )
    manifest_path = default_manifest_path(
        effective_runtime_root, selected_backend, session_id
    ).resolve()
    overrides = {
        "transport_override": mailbox_transport,
        "filesystem_root_override": mailbox_root,
        "filesystem_account_dir_override": mailbox_account_dir,
        "principal_id_override": mailbox_principal_id,
        "address_override": mailbox_address,
        "stalwart_base_url_override": mailbox_stalwart_base_url,
        "stalwart_jmap_url_override": mailbox_stalwart_jmap_url,
        "stalwart_management_url_override": mailbox_stalwart_management_url,
        "stalwart_login_identity_override": mailbox_stalwart_login_identity,
    }
    use_online = mailbox_transport == "stalwart" or any(
        (
            mailbox_stalwart_base_url,
            mailbox_stalwart_jmap_url,
            mailbox_stalwart_management_url,
            mailbox_stalwart_login_identity,
        )
    )
    try:
        resolved_agent_id = (
            resolved_runtime_identity.agent_id if resolved_runtime_identity else non_tmux_agent_id
        )
        if resolved_agent_id is None:
            raise SessionManifestError("New agent creation did not resolve its required identity")
        resolved_mailboxes = resolve_effective_mailboxes_config(
            declared_config=declared_mailboxes,
            agent_id=resolved_agent_id,
            runtime_root=effective_runtime_root,
            tool=tool,
            role_name=role_package.role_name,
            agent_identity=resolved_runtime_identity.canonical_agent_name
            if resolved_runtime_identity
            else agent_name,
            manifest_path_hint=manifest_path,
            offline_overrides=None if use_online else overrides,
            online_overrides=overrides if use_online else None,
        )
    except (RuntimeError, ValueError) as exc:
        raise SessionManifestError(f"Failed to prepare mail bindings: {exc}") from exc

    launch_plan = build_launch_plan(
        LaunchPlanRequest(
            brain_manifest=manifest,
            role_package=role_package,
            backend=selected_backend,
            working_directory=selected_workdir,
            mailboxes=resolved_mailboxes,
            session_root=manifest_path.parent,
        )
    )
    launch_plan = replace(
        launch_plan,
        execution_binding=current_execution_binding()
        or observed_local_binding(
            working_directory=selected_workdir,
            runtime_root=effective_runtime_root,
            registry_root=resolve_registry_root(),
            tmux_socket=current_tmux_socket_path()
            if selected_backend in _TMUX_BACKED_BACKENDS
            else None,
        ),
        metadata={
            **launch_plan.metadata,
            "tmux_socket_path": current_tmux_socket_path(),
        }
        if selected_backend in _TMUX_BACKED_BACKENDS
        else launch_plan.metadata,
    )
    launch_plan = _launch_plan_with_memory(
        launch_plan,
        memory=resolved_memory,
    )
    launch_plan = _launch_plan_with_transient_env_overrides(
        launch_plan,
        env_overrides=launch_env_overrides,
    )
    if project_overlay_dir is None:
        if shared_runtime_root is None and (
            os.environ.get(HOUMAO_GLOBAL_RUNTIME_DIR_ENV_VAR)
            or current_execution_binding() is not None
        ):
            shared_runtime_root = effective_runtime_root
        if shared_mailbox_root is None and (
            mailbox_root is not None or os.environ.get(HOUMAO_GLOBAL_MAILBOX_DIR_ENV_VAR)
        ):
            shared_mailbox_root = resolve_mailbox_root(explicit_root=mailbox_root)
        if os.environ.get(PROJECT_OVERLAY_DIR_ENV_VAR):
            project_overlay_dir = resolve_project_aware_local_roots(
                cwd=selected_workdir
            ).overlay_root
    root_context = {
        name: str(path.resolve())
        for name, path in (
            (HOUMAO_GLOBAL_RUNTIME_DIR_ENV_VAR, shared_runtime_root),
            (HOUMAO_GLOBAL_MAILBOX_DIR_ENV_VAR, shared_mailbox_root),
            (PROJECT_OVERLAY_DIR_ENV_VAR, project_overlay_dir),
            ("HOUMAO_AGENT_PRIVATE_WORKSPACE_ROOT", private_workspace_root),
        )
        if path is not None
    }
    launch_plan = _resolve_managed_launch_environment(
        launch_plan,
        root_context=root_context,
        agent_id=resolved_agent_id,
        manifest_path=manifest_path,
        agent_def_dir=agent_def_dir,
        api_base_url=api_base_url,
    )
    launch_plan = _launch_plan_with_headless_display_controls(
        launch_plan,
        style=headless_display_style,
        detail=headless_display_detail,
    )
    if managed_force_mode is not None:
        launch_plan = replace(
            launch_plan,
            metadata={
                **launch_plan.metadata,
                "managed_force_mode": managed_force_mode,
            },
        )

    registry_generation_id = (
        new_registry_generation_id() if selected_backend in _TMUX_BACKED_BACKENDS else None
    )
    if registry_generation_id is not None:
        assert launch_plan.execution_binding is not None
        gateway_admin_seed = gateway_admin_seed or GatewayLaunchSeed()
        provision_gateway_generation(
            binding=launch_plan.execution_binding,
            agent_id=resolved_agent_id,
            generation_id=registry_generation_id,
            seed=gateway_admin_seed,
        )
    elif gateway_admin_seed is not None:
        raise SessionManifestError(
            "Gateway admin seeding requires a managed gateway-capable backend."
        )
    if mode_for_backend(selected_backend) == "web":
        launch_plan = replace(
            launch_plan,
            metadata={
                **launch_plan.metadata,
                "managed_web_identity": {
                    "agent_id": resolved_agent_id,
                    "runtime_session_id": session_id,
                    "generation": registry_generation_id,
                },
            },
        )
    elif launch_plan.mode == "service":
        launch_plan = _launch_plan_with_service_identity(
            launch_plan,
            agent_id=resolved_agent_id,
            session_id=session_id,
            generation=registry_generation_id,
        )
    hook_observation_root = manifest_path.parent
    launch_plan = persist_runtime_launch_inputs(launch_plan, session_root=hook_observation_root)
    launch_plan = activate_hook_observation_for_provider_start(
        launch_plan,
        session_root=hook_observation_root,
    )
    try:
        backend_session = _create_backend_session(
            launch_plan=launch_plan,
            role_name=role_package.role_name,
            role_prompt=role_package.system_prompt,
            agent_def_dir=agent_def_dir,
            api_base_url=api_base_url,
            cao_profile_store_dir=cao_profile_store_dir,
            session_manifest_path=manifest_path,
            agent_identity=(
                resolved_runtime_identity.tmux_session_name
                if resolved_runtime_identity is not None
                else None
            ),
            cao_parsing_mode=cao_parsing_mode,
        )
    except BaseException:
        stop_hook_observation(hook_observation_root, tool=launch_plan.tool)
        raise

    resolved_tmux_session_name: str | None = None
    resolved_parsing_mode: CaoParsingMode | None = None
    if isinstance(backend_session, CaoRestSession):
        resolved_tmux_session_name = backend_session.state.session_name
        resolved_parsing_mode = backend_session.state.parsing_mode
        startup_warnings = (*startup_warnings, *backend_session.startup_warnings)
    elif isinstance(backend_session, HeadlessInteractiveSession):
        resolved_tmux_session_name = backend_session.state.tmux_session_name
    elif isinstance(backend_session, (DshWebSession, KimiWebSession)):
        resolved_tmux_session_name = backend_session.state.tmux_session_name
    elif isinstance(backend_session, ManagedServiceSession):
        resolved_tmux_session_name = backend_session.state.tmux_session_name

    controller = RuntimeSessionController(
        launch_plan=launch_plan,
        role_name=role_package.role_name,
        brain_manifest_path=brain_manifest_path.resolve(),
        manifest_path=manifest_path,
        agent_def_dir=agent_def_dir.resolve(),
        backend_session=backend_session,
        agent_identity=(
            resolved_runtime_identity.agent_name if resolved_runtime_identity is not None else None
        ),
        agent_id=resolved_runtime_identity.agent_id
        if resolved_runtime_identity is not None
        else non_tmux_agent_id,
        tmux_session_name=resolved_tmux_session_name,
        memory_root=resolved_memory.memory_root if resolved_memory is not None else None,
        memo_file=resolved_memory.memo_file if resolved_memory is not None else None,
        pages_dir=resolved_memory.pages_dir if resolved_memory is not None else None,
        agent_identity_warnings=agent_identity_warnings,
        startup_warnings=startup_warnings,
        parsing_mode=resolved_parsing_mode,
        registry_generation_id=registry_generation_id,
        gateway_admin_seed=gateway_admin_seed,
        registry_launch_authority=registry_launch_authority,
        agent_launch_authority=None,
    )
    controller.persist_manifest(refresh_registry=False)
    controller.ensure_gateway_capability(
        blueprint_gateway_defaults=resolved_gateway_defaults,
    )
    if gateway_auto_attach:
        attach_result = controller.attach_gateway(
            host_override=gateway_host,
            port_override=gateway_port,
            execution_mode_override=gateway_execution_mode_override,
            tui_tracking_timing_overrides=gateway_tui_tracking_timing_overrides,
            plugin_config=gateway_plugins,
            access_config=gateway_access_config,
        )
        if attach_result.status == "error":
            controller.gateway_auto_attach_error = attach_result.detail
        else:
            controller.gateway_host = attach_result.gateway_host
            controller.gateway_port = attach_result.gateway_port
    return controller


def resolve_agent_identity(
    *,
    agent_identity: str,
    base: Path,
    explicit_agent_def_dir: Path | None = None,
) -> AgentIdentityResolution:
    """Resolve an `--agent-identity` into a concrete session manifest path.

    Parameters
    ----------
    agent_identity:
        Raw CLI identity value (manifest path or agent name).
    base:
        Base path used for resolving relative manifest paths.
    explicit_agent_def_dir:
        Optional override for subsequent explicit relaunch planning.

    Returns
    -------
    AgentIdentityResolution
        Resolved manifest path and optional canonical name metadata.
    """

    if is_path_like_agent_identity(agent_identity):
        manifest_path = _resolve_manifest_path(agent_identity, base=base)
        if not manifest_path.is_file():
            raise SessionManifestError(f"Session manifest not found: {manifest_path}")
        return AgentIdentityResolution(
            session_manifest_path=manifest_path.resolve(), agent_def_dir=explicit_agent_def_dir
        )

    registry_id_resolution = _resolve_agent_identity_from_shared_registry_agent_id(
        agent_id=agent_identity,
        explicit_agent_def_dir=explicit_agent_def_dir,
    )
    if registry_id_resolution is not None:
        return registry_id_resolution

    normalized = normalize_agent_identity_name(agent_identity)
    tmux_resolution_error: SessionManifestError | None = None
    try:
        return _resolve_agent_identity_from_tmux_local(
            canonical_agent_identity=normalized.canonical_name,
            explicit_agent_def_dir=explicit_agent_def_dir,
            warnings=normalized.warnings,
        )
    except SessionManifestError as exc:
        tmux_resolution_error = exc

    registry_resolution = _resolve_agent_identity_from_shared_registry(
        canonical_agent_identity=normalized.canonical_name,
        explicit_agent_def_dir=explicit_agent_def_dir,
        warnings=normalized.warnings,
    )
    if registry_resolution is not None:
        return registry_resolution

    if tmux_resolution_error is not None:
        raise SessionManifestError(
            f"{tmux_resolution_error} Shared-registry fallback did not find a fresh record for "
            f"`{normalized.canonical_name}`."
        ) from tmux_resolution_error

    raise SessionManifestError(
        f"Agent not found: no live tmux session or shared-registry record matched "
        f"`{normalized.canonical_name}`."
    )


def resume_runtime_session(
    *,
    session_manifest_path: Path,
    agent_def_dir: Path | None = None,
    cao_profile_store_dir: Path | None = None,
    cao_parsing_mode: CaoParsingMode | None = None,
    read_only: bool = False,
) -> RuntimeSessionController:
    """Open a running session from committed runtime inputs.

    A supplied definition directory is retained as launch provenance for an
    explicit relaunch. Reconstructing the already-running session uses its
    manifest and private runtime artifacts.
    """

    return _resume_runtime_session_controller(
        agent_def_dir=agent_def_dir,
        session_manifest_path=session_manifest_path,
        cao_profile_store_dir=cao_profile_store_dir,
        cao_parsing_mode=cao_parsing_mode,
        stopped_revival=False,
        read_only=read_only,
    )


def resume_stopped_runtime_session(
    *,
    agent_def_dir: Path,
    session_manifest_path: Path,
    cao_profile_store_dir: Path | None = None,
    cao_parsing_mode: CaoParsingMode | None = None,
) -> RuntimeSessionController:
    """Prepare a controller that can revive one stopped tmux-backed runtime session."""

    return _resume_runtime_session_controller(
        agent_def_dir=agent_def_dir,
        session_manifest_path=session_manifest_path,
        cao_profile_store_dir=cao_profile_store_dir,
        cao_parsing_mode=cao_parsing_mode,
        stopped_revival=True,
    )


@_execution_scoped_resume
def _resume_runtime_session_controller(
    *,
    agent_def_dir: Path | None,
    session_manifest_path: Path,
    cao_profile_store_dir: Path | None,
    cao_parsing_mode: CaoParsingMode | None,
    stopped_revival: bool,
    read_only: bool = False,
) -> RuntimeSessionController:
    """Build one runtime controller from a persisted manifest with optional stopped revival."""

    handle = load_session_manifest(session_manifest_path)
    manifest_payload = parse_session_manifest_payload(
        handle.payload,
        source=str(handle.path),
    )
    _validate_saved_execution_binding(manifest_payload.runtime.execution_binding)
    read_only = execution_is_read_only()

    backend = manifest_payload.backend
    if backend in _TMUX_BACKED_BACKENDS and manifest_payload.agent_id is None:
        raise SessionManifestError("Existing agent manifest is missing required agent_id.")
    role_name = manifest_payload.role_name
    brain_manifest_path = Path(manifest_payload.brain_manifest_path).resolve()
    if stopped_revival and not _backend_supports_stopped_session_relaunch(backend):
        raise SessionManifestError(
            "Stopped-session revival is only supported for local tmux-backed backends "
            f"({sorted(_STOPPED_SESSION_RELAUNCH_BACKENDS)}), got {backend!r}."
        )
    agent_def_dir = _launch_definition_path(manifest_payload, agent_def_dir)
    memory = _memory_from_manifest_payload(payload=manifest_payload)
    if memory is not None and not read_only:
        ensure_agent_memory(memory)

    resolved_mailboxes = _resolved_mailbox_from_manifest_payload(
        manifest_payload,
        session_manifest_path=session_manifest_path,
    )
    launch_plan = _restore_runtime_launch_plan(
        payload=manifest_payload,
        session_root=handle.path.parent,
        mailboxes=resolved_mailboxes,
    )
    launch_plan = replace(
        launch_plan,
        execution_binding=manifest_payload.runtime.execution_binding,
        metadata={
            **launch_plan.metadata,
            "tmux_socket_path": manifest_payload.tmux.socket_path,
        }
        if manifest_payload.tmux is not None and manifest_payload.tmux.socket_path is not None
        else launch_plan.metadata,
    )
    launch_plan = _launch_plan_with_memory(launch_plan, memory=memory)
    if (
        launch_plan.public_env is None
        and launch_plan.execution_binding is not None
        and not _is_joined_tmux_manifest(manifest_payload)
    ):
        # Older private records lack visibility provenance. Keep their values in the
        # native process environment and rebuild only the verified discovery bindings.
        private_names = frozenset(launch_plan.env).difference(
            _MEMORY_ENV_VARS, {launch_plan.home_env_var}
        )
        launch_plan = _resolve_managed_launch_environment(
            replace(launch_plan, private_env_var_names=private_names),
            root_context={},
            agent_id=manifest_payload.agent_id,
            manifest_path=handle.path,
            agent_def_dir=agent_def_dir,
        )
    if not stopped_revival and not read_only:
        launch_plan = ensure_hook_observation_on_resume(
            launch_plan,
            session_root=session_manifest_path.resolve().parent,
        )

    requested_tmux_session_name = manifest_payload.tmux_session_name
    if stopped_revival:
        requested_tmux_session_name = _resolve_start_session_identity(
            manifest=load_brain_manifest(brain_manifest_path),
            tool=manifest_payload.tool,
            role_name=role_name,
            requested_agent_name=manifest_payload.agent_name,
            requested_agent_identity=None,
            requested_agent_id=manifest_payload.agent_id,
        ).tmux_session_name

    registry_generation_id = manifest_payload.registry_generation_id
    if backend in _TMUX_BACKED_BACKENDS and registry_generation_id is None and not read_only:
        registry_generation_id = new_registry_generation_id()
    if mode_for_backend(backend) == "web":
        launch_plan = replace(
            launch_plan,
            metadata={
                **launch_plan.metadata,
                "managed_web_identity": {
                    "agent_id": manifest_payload.agent_id,
                    "runtime_session_id": manifest_payload.runtime.session_id,
                    "generation": registry_generation_id,
                },
            },
        )
    elif launch_plan.mode == "service":
        launch_plan = _launch_plan_with_service_identity(
            launch_plan,
            agent_id=manifest_payload.agent_id,
            session_id=manifest_payload.runtime.session_id,
            generation=registry_generation_id,
        )

    backend_session = _create_backend_session(
        launch_plan=launch_plan,
        role_name=role_name,
        role_prompt=launch_plan.role_injection.prompt,
        agent_def_dir=None,
        cao_profile_store_dir=cao_profile_store_dir,
        resume_state=manifest_payload,
        session_manifest_path=session_manifest_path.resolve(),
        agent_identity=requested_tmux_session_name,
        cao_parsing_mode=cao_parsing_mode,
        stopped_revival=stopped_revival,
    )

    resolved_tmux_session_name: str | None = None
    if isinstance(backend_session, CaoRestSession):
        resolved_tmux_session_name = backend_session.state.session_name
    elif isinstance(backend_session, HeadlessInteractiveSession):
        resolved_tmux_session_name = backend_session.state.tmux_session_name
    elif isinstance(backend_session, (DshWebSession, KimiWebSession)):
        resolved_tmux_session_name = backend_session.state.tmux_session_name
    elif isinstance(backend_session, ManagedServiceSession):
        resolved_tmux_session_name = backend_session.state.tmux_session_name

    controller = RuntimeSessionController(
        launch_plan=launch_plan,
        role_name=role_name,
        brain_manifest_path=brain_manifest_path,
        manifest_path=session_manifest_path.resolve(),
        agent_def_dir=agent_def_dir,
        backend_session=backend_session,
        agent_identity=manifest_payload.agent_name,
        agent_id=manifest_payload.agent_id,
        tmux_session_name=resolved_tmux_session_name or requested_tmux_session_name,
        memory_root=memory.memory_root if memory is not None else None,
        memo_file=memory.memo_file if memory is not None else None,
        pages_dir=memory.pages_dir if memory is not None else None,
        parsing_mode=(
            backend_session.state.parsing_mode
            if isinstance(backend_session, CaoRestSession)
            else None
        ),
        registry_generation_id=registry_generation_id,
        gateway_admin_seed=manifest_payload.gateway_admin_seed,
        registry_launch_authority=manifest_payload.registry_launch_authority,
        agent_launch_authority=manifest_payload.agent_launch_authority,
    )
    if not stopped_revival and not read_only:
        controller.ensure_gateway_capability()
    return controller


def _create_backend_session(
    *,
    launch_plan: LaunchPlan,
    role_name: str,
    role_prompt: str,
    agent_def_dir: Path | None,
    api_base_url: str | None = None,
    cao_profile_store_dir: Path | None,
    resume_state: SessionManifestPayloadV4 | None = None,
    session_manifest_path: Path | None = None,
    agent_identity: str | None = None,
    cao_parsing_mode: CaoParsingMode | None = None,
    stopped_revival: bool = False,
) -> InteractiveSession:
    """Create a concrete backend session for start/resume flows."""

    if launch_plan.backend == "dsh_web":
        web_state = (
            DshWebSessionState.from_payload(resume_state.backend_state)
            if resume_state is not None
            else None
        )
        return cast(
            InteractiveSession,
            DshWebSession.from_launch_plan(
                launch_plan=launch_plan,
                role_name=role_name,
                session_manifest_path=_require_session_manifest_path(
                    session_manifest_path, backend=launch_plan.backend
                ),
                agent_def_dir=agent_def_dir,
                state=web_state,
                tmux_session_name=agent_identity,
                provider_start=resume_state is None,
            ),
        )

    if launch_plan.backend == "kimi_web":
        kimi_web_state = (
            KimiWebSessionState.from_payload(resume_state.backend_state)
            if resume_state is not None
            else None
        )
        return cast(
            InteractiveSession,
            KimiWebSession.from_launch_plan(
                launch_plan=launch_plan,
                role_name=role_name,
                session_manifest_path=_require_session_manifest_path(
                    session_manifest_path, backend=launch_plan.backend
                ),
                agent_def_dir=agent_def_dir,
                state=kimi_web_state,
                tmux_session_name=agent_identity,
                provider_start=resume_state is None,
            ),
        )

    if launch_plan.mode == "service":
        service_state = (
            ManagedServiceSessionState.from_payload(resume_state.backend_state)
            if resume_state is not None
            else None
        )
        return cast(
            InteractiveSession,
            ManagedServiceSession.from_launch_plan(
                launch_plan=launch_plan,
                session_manifest_path=_require_session_manifest_path(
                    session_manifest_path, backend=launch_plan.backend
                ),
                tmux_session_name=agent_identity,
                state=service_state,
                provider_start=resume_state is None,
            ),
        )

    if launch_plan.backend == "codex_headless":
        state = _resume_headless_state(
            resume_state,
            launch_plan=launch_plan,
            stopped_revival=stopped_revival,
        )
        return cast(
            InteractiveSession,
            CodexHeadlessSession(
                launch_plan=launch_plan,
                role_name=role_name,
                session_manifest_path=_require_session_manifest_path(
                    session_manifest_path,
                    backend=launch_plan.backend,
                ),
                agent_def_dir=agent_def_dir,
                state=state,
                tmux_session_name=agent_identity,
            ),
        )

    if launch_plan.backend == "local_interactive":
        state = _resume_local_interactive_state(
            resume_state,
            launch_plan=launch_plan,
            stopped_revival=stopped_revival,
        )
        return cast(
            InteractiveSession,
            LocalInteractiveSession(
                launch_plan=launch_plan,
                role_name=role_name,
                session_manifest_path=_require_session_manifest_path(
                    session_manifest_path,
                    backend=launch_plan.backend,
                ),
                agent_def_dir=agent_def_dir,
                state=state,
                tmux_session_name=agent_identity,
            ),
        )

    if launch_plan.backend == "claude_headless":
        state = _resume_headless_state(
            resume_state,
            launch_plan=launch_plan,
            stopped_revival=stopped_revival,
        )
        return cast(
            InteractiveSession,
            ClaudeHeadlessSession(
                launch_plan=launch_plan,
                role_name=role_name,
                session_manifest_path=_require_session_manifest_path(
                    session_manifest_path,
                    backend=launch_plan.backend,
                ),
                agent_def_dir=agent_def_dir,
                state=state,
                tmux_session_name=agent_identity,
            ),
        )

    if launch_plan.backend == "dsh_headless":
        state = _resume_headless_state(
            resume_state, launch_plan=launch_plan, stopped_revival=stopped_revival
        )
        if (
            state is not None
            and Path(state.working_directory).resolve() != launch_plan.working_directory
        ):
            raise SessionManifestError("DSH resume requires the recorded working directory")
        return cast(
            InteractiveSession,
            DshHeadlessSession(
                launch_plan=launch_plan,
                role_name=role_name,
                session_manifest_path=_require_session_manifest_path(
                    session_manifest_path, backend=launch_plan.backend
                ),
                agent_def_dir=agent_def_dir,
                state=state,
                tmux_session_name=agent_identity,
            ),
        )

    if launch_plan.backend == "kimi_headless":
        state = _resume_headless_state(
            resume_state,
            launch_plan=launch_plan,
            stopped_revival=stopped_revival,
        )
        if (
            state is not None
            and Path(state.working_directory).resolve() != launch_plan.working_directory
        ):
            raise SessionManifestError(
                "Kimi resume requires the same working directory as the persisted session"
            )
        return cast(
            InteractiveSession,
            KimiHeadlessSession(
                launch_plan=launch_plan,
                role_name=role_name,
                session_manifest_path=_require_session_manifest_path(
                    session_manifest_path,
                    backend=launch_plan.backend,
                ),
                agent_def_dir=agent_def_dir,
                state=state,
                tmux_session_name=agent_identity,
            ),
        )

    if launch_plan.backend == "cao_rest":
        existing_state = _resume_cao_state(resume_state)
        configured_mode = configured_cao_parsing_mode(launch_plan)
        resolved_parsing_mode = resolve_cao_parsing_mode(
            tool=launch_plan.tool,
            requested_mode=cao_parsing_mode,
            configured_mode=configured_mode,
        )
        if existing_state is not None and existing_state.parsing_mode != resolved_parsing_mode:
            raise SessionManifestError(
                "CAO parsing mode mismatch on resume: "
                f"manifest requires {existing_state.parsing_mode!r}, "
                f"but current configuration resolves to {resolved_parsing_mode!r}."
            )
        resolved_api_base_url = (
            existing_state.api_base_url if existing_state is not None else api_base_url
        )
        if resolved_api_base_url is None or not resolved_api_base_url.strip():
            raise SessionManifestError(
                "CAO start requires a non-empty api_base_url for backend=cao_rest"
            )
        return cast(
            InteractiveSession,
            CaoRestSession(
                launch_plan=launch_plan,
                api_base_url=resolved_api_base_url.strip(),
                role_name=role_name,
                role_prompt=role_prompt,
                agent_def_dir=agent_def_dir,
                profile_store_dir=cao_profile_store_dir,
                existing_state=existing_state,
                session_manifest_path=session_manifest_path,
                tmux_session_name=agent_identity,
                parsing_mode=resolved_parsing_mode,
            ),
        )

    if launch_plan.backend == "houmao_server_rest":
        raise SessionManifestError(
            "backend='houmao_server_rest' is retired. Use maintained local/headless "
            "manager workflows or `houmao-passive-server` API-managed launches instead."
        )

    raise SessionManifestError(f"Unsupported backend: {launch_plan.backend}")


def _resume_headless_state(
    payload: SessionManifestPayloadV4 | None,
    *,
    launch_plan: LaunchPlan,
    stopped_revival: bool = False,
) -> HeadlessSessionState | None:
    if payload is None:
        return None

    headless = payload.headless
    if headless is None:
        raise SessionManifestError("Headless session manifest missing `headless` state")

    session_id = headless.session_id
    turn_index = headless.turn_index
    if (
        (session_id is None or not session_id.strip())
        and turn_index > 0
        and headless.resume_selection_kind == "none"
    ):
        raise SessionManifestError(
            "Headless resume requires a non-empty headless.session_id after turn 0"
        )
    tmux_session_name = _manifest_tmux_session_name(payload)
    if not stopped_revival and (tmux_session_name is None or not tmux_session_name.strip()):
        raise SessionManifestError("Headless resume requires a non-empty tmux session authority.")
    tmux_window_name = _resolved_resumed_tmux_window_name(payload=payload, launch_plan=launch_plan)

    return HeadlessSessionState(
        session_id=session_id.strip() if session_id else None,
        turn_index=_manifest_interactive_turn_index(payload, fallback=turn_index),
        role_bootstrap_applied=_manifest_interactive_role_bootstrap_applied(
            payload,
            fallback=headless.role_bootstrap_applied,
        ),
        working_directory=_manifest_interactive_working_directory(
            payload,
            fallback=headless.working_directory or str(launch_plan.working_directory),
        ),
        tmux_session_name=(
            None
            if stopped_revival
            else (tmux_session_name.strip() if tmux_session_name is not None else None)
        ),
        tmux_window_name=tmux_window_name,
        tmux_window_id=None if stopped_revival else _manifest_primary_tmux_window_id(payload),
        tmux_pane_id=None if stopped_revival else _manifest_primary_tmux_pane_id(payload),
        resume_selection_kind=headless.resume_selection_kind,
        resume_selection_value=headless.resume_selection_value,
        joined_session=_is_joined_tmux_manifest(payload),
    )


def _resume_local_interactive_state(
    payload: SessionManifestPayloadV4 | None,
    *,
    launch_plan: LaunchPlan,
    stopped_revival: bool = False,
) -> HeadlessSessionState | None:
    if payload is None:
        return None

    local_interactive = payload.local_interactive
    if local_interactive is None:
        raise SessionManifestError(
            "Local interactive session manifest missing `local_interactive` state"
        )

    tmux_session_name = _manifest_tmux_session_name(payload)
    if not stopped_revival and (tmux_session_name is None or not tmux_session_name.strip()):
        raise SessionManifestError(
            "Local interactive resume requires a non-empty tmux session authority."
        )
    tmux_window_name = _resolved_resumed_tmux_window_name(payload=payload, launch_plan=launch_plan)

    return HeadlessSessionState(
        session_id=None,
        turn_index=_manifest_interactive_turn_index(payload, fallback=local_interactive.turn_index),
        role_bootstrap_applied=_manifest_interactive_role_bootstrap_applied(
            payload,
            fallback=local_interactive.role_bootstrap_applied,
        ),
        working_directory=_manifest_interactive_working_directory(
            payload,
            fallback=local_interactive.working_directory or str(launch_plan.working_directory),
        ),
        tmux_session_name=(
            None
            if stopped_revival
            else (tmux_session_name.strip() if tmux_session_name is not None else None)
        ),
        tmux_window_name=tmux_window_name,
        tmux_window_id=None if stopped_revival else _manifest_primary_tmux_window_id(payload),
        tmux_pane_id=None if stopped_revival else _manifest_primary_tmux_pane_id(payload),
        joined_session=_is_joined_tmux_manifest(payload),
    )


def _require_session_manifest_path(
    session_manifest_path: Path | None, *, backend: BackendKind
) -> Path:
    if session_manifest_path is None:
        raise SessionManifestError(f"backend={backend} requires a resolved session manifest path.")
    return session_manifest_path.resolve()


def _manifest_tmux_session_name(
    payload: SessionManifestPayloadV4,
) -> str | None:
    """Return the normalized tmux session name from one parsed manifest payload."""

    if payload.tmux is not None:
        return payload.tmux.session_name
    return payload.tmux_session_name


def _manifest_interactive_turn_index(
    payload: SessionManifestPayloadV4,
    *,
    fallback: int,
) -> int:
    """Return the normalized interactive turn index for one manifest payload."""

    if payload.interactive is not None:
        return payload.interactive.turn_index
    return fallback


def _manifest_interactive_working_directory(
    payload: SessionManifestPayloadV4,
    *,
    fallback: str,
) -> str:
    """Return the normalized interactive working directory for one manifest payload."""

    if payload.interactive is not None:
        value = payload.interactive.working_directory
        if value is not None and value.strip():
            return value
    return fallback


def _manifest_interactive_role_bootstrap_applied(
    payload: SessionManifestPayloadV4,
    *,
    fallback: bool,
) -> bool:
    """Return the normalized role-bootstrap flag for one manifest payload."""

    if payload.interactive is not None:
        value = payload.interactive.role_bootstrap_applied
        if value is not None:
            return value
    return fallback


def _manifest_interactive_terminal_id(
    payload: SessionManifestPayloadV4,
) -> str | None:
    """Return the normalized interactive terminal id for one manifest payload."""

    if payload.interactive is not None:
        return payload.interactive.terminal_id
    return None


def _manifest_interactive_parsing_mode(
    payload: SessionManifestPayloadV4,
) -> CaoParsingMode | None:
    """Return the normalized interactive parsing mode for one manifest payload."""

    if payload.interactive is not None:
        return payload.interactive.parsing_mode
    return None


def _manifest_interactive_tmux_window_name(
    payload: SessionManifestPayloadV4,
) -> str | None:
    """Return the normalized interactive tmux window name for one manifest payload."""

    if payload.interactive is not None:
        return payload.interactive.tmux_window_name
    return None


def _manifest_primary_tmux_window_name(
    payload: SessionManifestPayloadV4,
) -> str | None:
    """Return the best persisted tmux window name from one manifest payload."""

    if payload.tmux is not None:
        value = payload.tmux.primary_window_name
        if value is not None and value.strip():
            return value.strip()
    interactive_value = _manifest_interactive_tmux_window_name(payload)
    if interactive_value is not None and interactive_value.strip():
        return interactive_value.strip()
    backend_window_name = payload.backend_state.get("tmux_window_name")
    if isinstance(backend_window_name, str) and backend_window_name.strip():
        return backend_window_name.strip()
    return None


def _manifest_primary_tmux_window_id(
    payload: SessionManifestPayloadV4,
) -> str | None:
    """Return the best persisted primary tmux window id from one manifest payload."""

    if payload.tmux is not None and payload.tmux.primary_window_id is not None:
        return payload.tmux.primary_window_id
    if (
        payload.agent_launch_authority is not None
        and payload.agent_launch_authority.primary_window_id is not None
    ):
        return payload.agent_launch_authority.primary_window_id
    return _optional_backend_state_str(payload, "tmux_window_id")


def _manifest_primary_tmux_pane_id(
    payload: SessionManifestPayloadV4,
) -> str | None:
    """Return the best persisted primary tmux pane id from one manifest payload."""

    if payload.tmux is not None and payload.tmux.primary_pane_id is not None:
        return payload.tmux.primary_pane_id
    if (
        payload.agent_launch_authority is not None
        and payload.agent_launch_authority.primary_pane_id is not None
    ):
        return payload.agent_launch_authority.primary_pane_id
    return _optional_backend_state_str(payload, "tmux_pane_id")


def _joined_launch_plan_tmux_window_name(launch_plan: LaunchPlan) -> str | None:
    """Return the joined launch-plan tmux window name when one was persisted."""

    value = launch_plan.metadata.get("tmux_window_name")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _resolved_resumed_tmux_window_name(
    *,
    payload: SessionManifestPayloadV4,
    launch_plan: LaunchPlan,
) -> str | None:
    """Resolve the tmux window name to keep during resume-time manifest persistence."""

    persisted_window_name = _manifest_primary_tmux_window_name(payload)
    if persisted_window_name is not None:
        return persisted_window_name
    if _is_joined_tmux_manifest(payload):
        return _joined_launch_plan_tmux_window_name(launch_plan)
    return None


def _manifest_pair_managed_agent_ref(
    payload: SessionManifestPayloadV4,
) -> str | None:
    """Return the normalized pair-managed session alias for one manifest payload."""

    if payload.gateway_authority is not None:
        return payload.gateway_authority.attach.managed_agent_ref
    if payload.houmao_server is not None:
        return payload.houmao_server.session_name
    return None


def _is_joined_tmux_manifest(
    payload: SessionManifestPayloadV4,
) -> bool:
    """Return whether one manifest payload describes a joined tmux session."""

    return (
        payload.agent_launch_authority is not None
        and payload.agent_launch_authority.session_origin == _JOINED_SESSION_ORIGIN
    )


def persist_runtime_launch_inputs(launch_plan: LaunchPlan, *, session_root: Path) -> LaunchPlan:
    """Capture the selected private environment for the new live runtime."""

    metadata = dict(launch_plan.metadata)
    mcp_environment: dict[str, str] = {}
    dsh = metadata.get("dsh")
    source = metadata.get("env_source_file")
    if launch_plan.tool == "dsh" and isinstance(dsh, dict) and dsh.get("mcp_server_names"):
        setup = DshEffectiveToolParams.from_file(Path(dsh["setup_path"]))
        mcp_environment = read_dsh_mcp_environment(setup, source)
    name = write_runtime_launch_environment(
        session_root,
        environment=launch_plan.env,
        transient_names=launch_plan.transient_env_var_names,
        mcp_environment=mcp_environment,
        public_names=(
            frozenset(launch_plan.public_env) if launch_plan.public_env is not None else None
        ),
        private_names=launch_plan.private_env_var_names,
        masked_names=launch_plan.previous_public_env_var_names,
    )
    if launch_plan.tool == "dsh":
        metadata["env_source_file"] = str(session_root / name)
    return replace(launch_plan, runtime_launch_environment_file=name, metadata=metadata)


def _restore_runtime_launch_plan(
    *,
    payload: SessionManifestPayloadV4,
    session_root: Path,
    mailboxes: MailboxesResolvedConfig,
) -> LaunchPlan:
    """Restore prepared launch inputs without compiling a provider-start plan."""

    saved = payload.launch_plan
    metadata = dict(saved.metadata)
    metadata.pop("env_source_file", None)
    if _is_joined_tmux_manifest(payload):
        metadata.setdefault("session_origin", _JOINED_SESSION_ORIGIN)
    environment = {saved.home_selector.env_var: saved.home_selector.home_path}
    transient_names: frozenset[str] = frozenset()
    public_env: dict[str, str] | None = None
    private_names: frozenset[str] = frozenset()
    masked_names: frozenset[str] = frozenset()
    name = payload.runtime.launch_environment_file
    if name is not None:
        source = session_root / name
        private = read_runtime_launch_environment(source)
        environment.update(private.environment)
        transient_names = frozenset(private.transient_names)
        private_names = frozenset(private.private_names)
        masked_names = frozenset(private.masked_names)
        if private.public_names is not None:
            public_env = {
                key: environment[key] for key in private.public_names if key in environment
            }
        if saved.tool == "dsh":
            metadata["env_source_file"] = str(source)
    prompt = payload.system_prompt.text if payload.system_prompt is not None else ""
    provenance = saved.launch_policy_provenance
    return LaunchPlan(
        backend=saved.backend,
        native_surface_kind=saved.native_surface_kind,
        tool=saved.tool,
        executable=saved.executable,
        args=list(saved.args),
        working_directory=Path(saved.working_directory),
        home_env_var=saved.home_selector.env_var,
        home_path=Path(saved.home_selector.home_path),
        env=environment,
        env_var_names=list(saved.env_var_names),
        role_injection=RoleInjectionPlan(
            method=saved.role_injection.method,
            role_name=saved.role_injection.role_name,
            prompt=prompt,
            bootstrap_message=_bootstrap_message(saved.role_injection.role_name, prompt)
            if saved.role_injection.method in {"bootstrap_message", "native_append_system_prompt"}
            else None,
        ),
        metadata=metadata,
        mailboxes=mailboxes,
        transient_env_var_names=transient_names,
        execution_binding=payload.runtime.execution_binding,
        runtime_launch_environment_file=name,
        public_env=public_env,
        private_env_var_names=private_names,
        previous_public_env_var_names=masked_names,
        launch_policy_provenance=LaunchPolicyProvenance(**provenance.model_dump())
        if provenance is not None
        else None,
    )


def _build_joined_launch_plan_from_manifest_payload(
    *,
    payload: SessionManifestPayloadV4,
    role_package: RolePackage,
    mailboxes: MailboxesResolvedConfig,
) -> LaunchPlan:
    """Rebuild a join-derived launch plan from the persisted session manifest."""

    if payload.agent_launch_authority is None:
        raise SessionManifestError("Joined-session resume requires v4 agent_launch_authority data.")
    authority = payload.agent_launch_authority
    if authority.session_origin != _JOINED_SESSION_ORIGIN:
        raise SessionManifestError("Joined-session resume requires session_origin=joined_tmux.")

    launch_payload = payload.launch_plan
    tmux_session_name = authority.tmux_session_name or _manifest_tmux_session_name(payload)
    env = _resolve_joined_launch_env_values(
        authority=authority,
        tmux_session_name=tmux_session_name,
    )
    metadata = dict(launch_payload.metadata)
    metadata.setdefault("session_origin", _JOINED_SESSION_ORIGIN)
    return LaunchPlan(
        backend=launch_payload.backend,
        native_surface_kind=launch_payload.native_surface_kind,
        tool=launch_payload.tool,
        executable=launch_payload.executable,
        args=list(launch_payload.args),
        working_directory=Path(launch_payload.working_directory).resolve(),
        home_env_var=launch_payload.home_selector.env_var,
        home_path=Path(launch_payload.home_selector.home_path).resolve(),
        env=env,
        env_var_names=list(launch_payload.env_var_names),
        role_injection=RoleInjectionPlan(
            method=launch_payload.role_injection.method,
            role_name=launch_payload.role_injection.role_name,
            prompt=role_package.system_prompt,
            bootstrap_message=(
                role_package.system_prompt
                if launch_payload.role_injection.method == "bootstrap_message"
                else None
            ),
        ),
        metadata=metadata,
        mailboxes=mailboxes,
        launch_policy_provenance=None,
    )


def _resolve_joined_launch_env_values(
    *,
    authority: SessionManifestAgentLaunchAuthorityV1,
    tmux_session_name: str | None,
) -> dict[str, str]:
    """Resolve persisted joined-session launch env bindings into concrete values."""

    resolved: dict[str, str] = {}
    for binding in authority.launch_env or ():
        if binding.mode == "literal":
            resolved[binding.name] = binding.value
            continue
        if tmux_session_name is None or not tmux_session_name.strip():
            raise SessionManifestError(
                f"Joined relaunch requires tmux session authority to resolve `{binding.name}`."
            )
        value = read_tmux_session_environment_value_shared(
            session_name=tmux_session_name,
            variable_name=binding.name,
        )
        if value is None or not value.strip():
            raise SessionManifestError(
                "Joined relaunch could not resolve inherited launch env "
                f"`{binding.name}` from tmux session `{tmux_session_name}`."
            )
        resolved[binding.name] = value
    return resolved


def _optional_backend_state_str(
    payload: SessionManifestPayloadV4,
    key: str,
) -> str | None:
    """Return one normalized optional backend_state string."""

    value = payload.backend_state.get(key)
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _agent_launch_authority_with_primary_handles(
    authority: SessionManifestAgentLaunchAuthorityV1 | None,
    *,
    backend_state: dict[str, Any],
) -> SessionManifestAgentLaunchAuthorityV1 | None:
    """Refresh optional primary tmux handles on a persisted launch authority."""

    if authority is None:
        return None
    updates: dict[str, str | None] = {}
    window_id = _optional_non_empty_backend_value(backend_state.get("tmux_window_id"))
    pane_id = _optional_non_empty_backend_value(backend_state.get("tmux_pane_id"))
    if window_id is not None or authority.primary_window_id is not None:
        updates["primary_window_id"] = window_id
    if pane_id is not None or authority.primary_pane_id is not None:
        updates["primary_pane_id"] = pane_id
    if not updates:
        return authority
    return authority.model_copy(update=updates)


def _optional_non_empty_backend_value(value: object) -> str | None:
    """Return a stripped backend-state string when present."""

    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _resolve_manifest_relaunch_authority(
    controller: RuntimeSessionController,
) -> SessionManifestAgentLaunchAuthorityV1:
    """Load and validate the relaunch authority for one tmux-backed controller."""

    handle = load_session_manifest(controller.manifest_path)
    payload = parse_session_manifest_payload(handle.payload, source=str(handle.path))
    if isinstance(payload, SessionManifestPayloadV4) and payload.agent_launch_authority is not None:
        return payload.agent_launch_authority

    tmux_session_name = _manifest_tmux_session_name(payload)
    if tmux_session_name is None or not tmux_session_name.strip():
        raise SessionManifestError(
            f"Manifest `{handle.path}` is missing tmux-backed relaunch authority."
        )
    return SessionManifestAgentLaunchAuthorityV1(
        backend=payload.backend,
        tool=payload.tool,
        tmux_session_name=tmux_session_name,
        primary_window_index=_PRIMARY_AGENT_WINDOW_INDEX,
        primary_window_id=_manifest_primary_tmux_window_id(payload),
        primary_pane_id=_manifest_primary_tmux_pane_id(payload),
        working_directory=payload.working_directory,
        posture_kind="runtime_launch_plan",
        session_id=(
            payload.runtime.session_id
            if isinstance(payload, SessionManifestPayloadV4)
            else _runtime_session_id_from_manifest_path(handle.path)
        ),
        profile_name=(
            payload.cao.profile_name
            if payload.cao is not None
            else _optional_backend_state_str(payload, "profile_name")
        ),
        profile_path=(
            payload.cao.profile_path
            if payload.cao is not None
            else _optional_backend_state_str(payload, "profile_path")
        ),
    )


def _resolve_relaunch_chat_session_selection(
    *,
    controller: RuntimeSessionController,
    requested: RelaunchChatSessionSelection | None,
) -> RelaunchChatSessionSelection:
    """Resolve relaunch chat-session policy from CLI override, profile provenance, or default."""

    if requested is not None:
        return requested
    profile_selection = _launch_profile_relaunch_chat_session_selection(controller.launch_plan)
    if profile_selection is not None:
        return profile_selection
    return RelaunchChatSessionSelection(mode="new")


def _launch_profile_relaunch_chat_session_selection(
    launch_plan: LaunchPlan,
) -> RelaunchChatSessionSelection | None:
    """Return stored launch-profile relaunch policy from launch-plan metadata when present."""

    launch_overrides = launch_plan.metadata.get("launch_overrides")
    if not isinstance(launch_overrides, dict):
        return None
    construction_provenance = launch_overrides.get("construction_provenance")
    if not isinstance(construction_provenance, dict):
        return None
    launch_profile = construction_provenance.get("launch_profile")
    if not isinstance(launch_profile, dict):
        return None
    relaunch = launch_profile.get("relaunch")
    if isinstance(relaunch, dict):
        chat_session = relaunch.get("chat_session")
        if isinstance(chat_session, dict):
            return _relaunch_chat_session_selection_from_payload(chat_session)
    chat_session = launch_profile.get("relaunch_chat_session")
    if isinstance(chat_session, dict):
        return _relaunch_chat_session_selection_from_payload(chat_session)
    return None


def _launch_plan_with_service_identity(
    launch_plan: LaunchPlan, *, agent_id: str, session_id: str | None, generation: str | None
) -> LaunchPlan:
    """Give the private supervisor the same identity as the saved execution route."""

    if generation is None or session_id is None:
        raise SessionManifestError(
            "Managed service requires a recorded runtime and owner generation."
        )
    return replace(
        launch_plan,
        metadata={
            **launch_plan.metadata,
            "managed_service_identity": {
                "agent_id": agent_id,
                "runtime_session_id": session_id,
                "generation": generation,
            },
        },
    )


def _relaunch_chat_session_selection_from_payload(
    payload: dict[str, object],
) -> RelaunchChatSessionSelection:
    """Parse one persisted relaunch chat-session selector payload."""

    raw_mode = payload.get("mode")
    if raw_mode not in {"new", "tool_last_or_new", "exact"}:
        raise ValueError(
            "Launch-profile relaunch chat-session policy must use mode "
            "`new`, `tool_last_or_new`, or `exact`."
        )
    mode = cast(Literal["new", "tool_last_or_new", "exact"], raw_mode)
    session_id = payload.get("id", payload.get("session_id"))
    if session_id is not None and not isinstance(session_id, str):
        raise ValueError("Launch-profile relaunch chat-session id must be a string.")
    return RelaunchChatSessionSelection(mode=mode, session_id=session_id)


def _relaunch_backend_session(
    controller: RuntimeSessionController,
    *,
    chat_session: RelaunchChatSessionSelection,
) -> SessionControlResult:
    """Dispatch the shared relaunch primitive across supported tmux-backed backends."""

    backend_session = controller.backend_session
    if isinstance(backend_session, ManagedServiceSession):
        if controller.agent_id is None:
            raise SessionManifestError("Managed service relaunch requires an agent identity.")
        generation = new_registry_generation_id()
        _provision_relaunch_gateway_generation(controller, generation)
        current_plan = controller.launch_plan
        launch_plan = _launch_plan_with_service_identity(
            current_plan,
            agent_id=controller.agent_id,
            session_id=backend_session.state.runtime_session_id,
            generation=generation,
        )
        backend_session.update_launch_plan(launch_plan)
        try:
            result = backend_session.relaunch(chat_session=chat_session)
        except BaseException:
            backend_session.update_launch_plan(current_plan)
            raise
        if result.status == "ok":
            controller.launch_plan = launch_plan
            controller.m_registry_handoff_generation = controller.registry_generation_id
            controller.registry_generation_id = generation
        else:
            backend_session.update_launch_plan(current_plan)
        return result
    if isinstance(backend_session, (DshWebSession, KimiWebSession)):
        handle = load_session_manifest(controller.manifest_path)
        expected_identity = controller.m_web_manifest_identity
        if handle.payload["backend_state"].get("web_identity") != expected_identity:
            return SessionControlResult(
                status="error", action="relaunch", detail="Web relaunch authority is stale"
            )
        previous_generation = str(backend_session.state.web_identity["generation"])
        existing_record = (
            load_managed_agent_record_by_agent_id(controller.agent_id)
            if controller.agent_id is not None
            else None
        )
        if existing_record is not None and (
            existing_record.generation_id != previous_generation
            or Path(existing_record.runtime.manifest_path).resolve()
            != controller.manifest_path.resolve()
        ):
            return SessionControlResult(
                status="error", action="relaunch", detail="Web registry owner changed"
            )
        generation = new_registry_generation_id()
        _provision_relaunch_gateway_generation(controller, generation)
        previous_plan = controller.launch_plan
        launch_plan = replace(
            previous_plan,
            metadata={
                **previous_plan.metadata,
                "managed_web_identity": {
                    "agent_id": backend_session.state.web_identity["agent_id"],
                    "runtime_session_id": backend_session.state.web_identity["runtime_session_id"],
                    "generation": generation,
                },
            },
        )
        backend_session.update_launch_plan(launch_plan)
        result = backend_session.relaunch(chat_session=chat_session)
        if result.status == "ok":
            controller.launch_plan = launch_plan
            controller.registry_generation_id = generation
            if existing_record is not None:
                controller.m_registry_handoff_generation = previous_generation
        else:
            backend_session.update_launch_plan(previous_plan)
        return result
    if not isinstance(
        backend_session, (LocalInteractiveSession, HeadlessInteractiveSession, CaoRestSession)
    ):
        return SessionControlResult(
            status="error",
            action="relaunch",
            detail=f"backend={controller.launch_plan.backend!r} does not support tmux-backed relaunch.",
        )
    if isinstance(backend_session, CaoRestSession) and chat_session.mode != "new":
        return SessionControlResult(
            status="error",
            action="relaunch",
            detail="Chat-session continuation is not supported for backend='cao_rest'.",
        )
    generation = new_registry_generation_id()
    _provision_relaunch_gateway_generation(controller, generation)
    result = (
        backend_session.relaunch()
        if isinstance(backend_session, CaoRestSession)
        else backend_session.relaunch(chat_session=chat_session)
    )
    if result.status == "ok":
        controller.m_registry_handoff_generation = controller.registry_generation_id
        controller.registry_generation_id = generation
    return result


def _provision_relaunch_gateway_generation(
    controller: RuntimeSessionController, generation: str
) -> None:
    """Prepare a new managed self key using the existing owner roster."""

    binding = controller.execution_binding
    if binding is None or controller.agent_id is None:
        raise SessionManifestError("Gateway generation requires managed execution authority.")
    provision_gateway_generation(
        binding=binding, agent_id=controller.agent_id, generation_id=generation
    )


def _refresh_pair_launch_registration(controller: RuntimeSessionController) -> None:
    """Refresh the pair launch registration after a successful local relaunch."""

    if controller.launch_plan.backend != "houmao_server_rest":
        return
    raise SessionManifestError("backend='houmao_server_rest' relaunch is retired.")


def _resume_cao_state(
    payload: SessionManifestPayloadV4 | None,
) -> CaoSessionState | None:
    if payload is None:
        return None

    cao = payload.cao
    if cao is None:
        raise SessionManifestError("CAO session manifest missing `cao` state")

    persisted_api_base_url = cao.api_base_url.strip()
    if not persisted_api_base_url:
        raise SessionManifestError("CAO session manifest missing or blank cao.api_base_url")

    terminal_id = cao.terminal_id.strip()
    normalized_terminal_id = _manifest_interactive_terminal_id(payload)
    if normalized_terminal_id is not None:
        normalized_terminal_id = normalized_terminal_id.strip()
    if not terminal_id:
        raise SessionManifestError("CAO session manifest missing or blank cao.terminal_id")
    if normalized_terminal_id is not None and terminal_id != normalized_terminal_id:
        raise SessionManifestError(
            "CAO session manifest terminal_id mismatch: "
            "cao.terminal_id must equal interactive.terminal_id"
        )

    session_name = cao.session_name.strip()
    if not session_name:
        raise SessionManifestError("CAO session manifest missing or blank cao.session_name")

    profile_name = cao.profile_name.strip()
    if not profile_name:
        raise SessionManifestError("CAO session manifest missing or blank cao.profile_name")

    profile_path = cao.profile_path.strip()
    if not profile_path:
        raise SessionManifestError("CAO session manifest missing or blank cao.profile_path")

    parsing_mode = cao.parsing_mode
    normalized_parsing_mode = _manifest_interactive_parsing_mode(payload)
    if normalized_parsing_mode is not None and parsing_mode != normalized_parsing_mode:
        raise SessionManifestError(
            "CAO session manifest parsing_mode mismatch: "
            "cao.parsing_mode must equal interactive.parsing_mode"
        )

    backend_api_base_url = payload.backend_state.get("api_base_url")
    if not isinstance(backend_api_base_url, str) or not backend_api_base_url.strip():
        raise SessionManifestError(
            "CAO session manifest missing or blank backend_state.api_base_url"
        )
    if persisted_api_base_url != backend_api_base_url.strip():
        raise SessionManifestError(
            "CAO session manifest api_base_url mismatch: "
            "cao.api_base_url must equal backend_state.api_base_url"
        )
    backend_parsing_mode = payload.backend_state.get("parsing_mode")
    if normalized_parsing_mode is None:
        if not isinstance(backend_parsing_mode, str) or not backend_parsing_mode.strip():
            raise SessionManifestError(
                "CAO session manifest missing or blank backend_state.parsing_mode"
            )
        normalized_parsing_mode = cast(CaoParsingMode, backend_parsing_mode.strip())
    if parsing_mode != normalized_parsing_mode:
        raise SessionManifestError(
            "CAO session manifest parsing_mode mismatch: "
            "cao.parsing_mode must equal normalized interactive parsing mode"
        )

    tmux_window_name = cao.tmux_window_name.strip() if cao.tmux_window_name is not None else None
    normalized_tmux_window_name = _manifest_interactive_tmux_window_name(payload)
    if normalized_tmux_window_name is not None:
        normalized_tmux_window_name = normalized_tmux_window_name.strip()
        if tmux_window_name is None:
            tmux_window_name = normalized_tmux_window_name
        elif tmux_window_name != normalized_tmux_window_name:
            raise SessionManifestError(
                "CAO session manifest tmux_window_name mismatch: "
                "cao.tmux_window_name must equal interactive.tmux_window_name"
            )
    else:
        backend_tmux_window_name = payload.backend_state.get("tmux_window_name")
        if backend_tmux_window_name is not None:
            if (
                not isinstance(backend_tmux_window_name, str)
                or not backend_tmux_window_name.strip()
            ):
                raise SessionManifestError(
                    "CAO session manifest backend_state.tmux_window_name must be a "
                    "non-empty string when present"
                )
            resolved_backend_tmux_window_name = backend_tmux_window_name.strip()
            if tmux_window_name is None:
                tmux_window_name = resolved_backend_tmux_window_name
            elif tmux_window_name != resolved_backend_tmux_window_name:
                raise SessionManifestError(
                    "CAO session manifest tmux_window_name mismatch: "
                    "cao.tmux_window_name must equal backend_state.tmux_window_name"
                )

    return CaoSessionState(
        api_base_url=persisted_api_base_url,
        session_name=session_name,
        terminal_id=terminal_id,
        profile_name=profile_name,
        profile_path=profile_path,
        tmux_window_name=tmux_window_name,
        parsing_mode=parsing_mode,
        turn_index=cao.turn_index,
    )


def _resume_houmao_server_state(
    payload: SessionManifestPayloadV4 | None,
) -> CaoSessionState | None:
    if payload is None:
        return None

    houmao_server = payload.houmao_server
    if houmao_server is None:
        raise SessionManifestError("houmao-server session manifest missing `houmao_server` state")

    persisted_api_base_url = houmao_server.api_base_url.strip()
    if not persisted_api_base_url:
        raise SessionManifestError(
            "houmao-server session manifest missing or blank houmao_server.api_base_url"
        )

    terminal_id = houmao_server.terminal_id.strip()
    normalized_terminal_id = _manifest_interactive_terminal_id(payload)
    if normalized_terminal_id is not None:
        normalized_terminal_id = normalized_terminal_id.strip()
    if not terminal_id:
        raise SessionManifestError(
            "houmao-server session manifest missing or blank houmao_server.terminal_id"
        )
    if normalized_terminal_id is not None and terminal_id != normalized_terminal_id:
        raise SessionManifestError(
            "houmao-server session manifest terminal_id mismatch: "
            "houmao_server.terminal_id must equal interactive.terminal_id"
        )

    session_name = houmao_server.session_name.strip()
    normalized_session_name = _manifest_pair_managed_agent_ref(payload)
    if normalized_session_name is not None:
        normalized_session_name = normalized_session_name.strip()
    if not session_name:
        raise SessionManifestError(
            "houmao-server session manifest missing or blank houmao_server.session_name"
        )
    if normalized_session_name is not None and session_name != normalized_session_name:
        raise SessionManifestError(
            "houmao-server session manifest session_name mismatch: "
            "houmao_server.session_name must equal gateway_authority.attach.managed_agent_ref"
        )

    backend_api_base_url = payload.backend_state.get("api_base_url")
    if not isinstance(backend_api_base_url, str) or not backend_api_base_url.strip():
        raise SessionManifestError(
            "houmao-server session manifest missing or blank backend_state.api_base_url"
        )
    if persisted_api_base_url != backend_api_base_url.strip():
        raise SessionManifestError(
            "houmao-server session manifest api_base_url mismatch: "
            "houmao_server.api_base_url must equal backend_state.api_base_url"
        )

    normalized_parsing_mode = _manifest_interactive_parsing_mode(payload)
    if normalized_parsing_mode is None:
        backend_parsing_mode = payload.backend_state.get("parsing_mode")
        if not isinstance(backend_parsing_mode, str) or not backend_parsing_mode.strip():
            raise SessionManifestError(
                "houmao-server session manifest missing or blank backend_state.parsing_mode"
            )
        normalized_parsing_mode = cast(CaoParsingMode, backend_parsing_mode.strip())
    if houmao_server.parsing_mode != normalized_parsing_mode:
        raise SessionManifestError(
            "houmao-server session manifest parsing_mode mismatch: "
            "houmao_server.parsing_mode must equal normalized interactive parsing mode"
        )

    profile_name = str(payload.backend_state.get("profile_name", "houmao-server")).strip()
    profile_path = str(payload.backend_state.get("profile_path", "houmao-server")).strip()
    if not profile_name:
        profile_name = "houmao-server"
    if not profile_path:
        profile_path = "houmao-server"

    return CaoSessionState(
        api_base_url=persisted_api_base_url,
        session_name=session_name,
        terminal_id=terminal_id,
        profile_name=profile_name,
        profile_path=profile_path,
        tmux_window_name=(
            _manifest_interactive_tmux_window_name(payload) or houmao_server.tmux_window_name
        ),
        parsing_mode=houmao_server.parsing_mode,
        turn_index=_manifest_interactive_turn_index(payload, fallback=houmao_server.turn_index),
    )


def _backend_state_for_session(session: InteractiveSession) -> GatewayJsonObject:
    """Build JSON-serializable backend state for one runtime session.

    Parameters
    ----------
    session:
        Concrete runtime session implementation.

    Returns
    -------
    GatewayJsonObject
        Backend-specific state persisted into the manifest and gateway
        capability artifacts.
    """

    if isinstance(session, (DshWebSession, KimiWebSession)):
        return cast(GatewayJsonObject, session.state.to_payload())
    if isinstance(session, ManagedServiceSession):
        return cast(GatewayJsonObject, session.runtime_state_payload())
    if isinstance(session, HeadlessInteractiveSession):
        return cast(GatewayJsonObject, headless_backend_state_payload(session.state))
    if isinstance(session, CaoRestSession):
        return cast(GatewayJsonObject, cao_backend_state_payload(session.state))
    return {}


def _declared_mailbox_from_manifest(
    manifest: dict[str, object],
    *,
    source: str,
) -> MailboxesDeclarativeConfig:
    try:
        if "mailbox" in manifest:
            raise ValueError("Unsupported single mailbox declaration; use mailboxes.offline/online")
        return parse_declarative_mailboxes_config(
            manifest.get("mailboxes"),
            source=source,
        )
    except ValueError as exc:
        raise SessionManifestError(str(exc)) from exc


def _gateway_defaults_from_brain_manifest(
    manifest: dict[str, object],
    *,
    source: str,
) -> BlueprintGatewayDefaults | None:
    """Return optional gateway defaults from manifest `inputs.extra.gateway`."""

    inputs = manifest.get("inputs")
    if inputs is None:
        return None
    if not isinstance(inputs, dict):
        raise SessionManifestError(f"{source}: brain manifest `inputs` must be a mapping")

    extra = inputs.get("extra")
    if extra is None:
        return None
    if not isinstance(extra, dict):
        raise SessionManifestError(f"{source}: brain manifest `inputs.extra` must be a mapping")

    raw_gateway = extra.get("gateway")
    if raw_gateway is None:
        return None
    if not isinstance(raw_gateway, dict):
        raise SessionManifestError(
            f"{source}: brain manifest `inputs.extra.gateway` must be a mapping"
        )

    try:
        return BlueprintGatewayDefaults.model_validate(raw_gateway)
    except Exception as exc:
        raise SessionManifestError(
            f"{source}: invalid brain manifest `inputs.extra.gateway`: {exc}"
        ) from exc


def _resolved_mailbox_from_manifest_payload(
    payload: SessionManifestPayloadV4,
    *,
    session_manifest_path: Path,
) -> MailboxesResolvedConfig:
    try:
        return mailboxes_resolved_config_from_payload(
            payload.launch_plan.mailboxes,
            manifest_path=session_manifest_path.resolve(),
        )
    except ValueError as exc:
        raise SessionManifestError(str(exc)) from exc


def _mailbox_mutation_activation_state(
    *,
    controller: RuntimeSessionController,
    updated_mailbox: FilesystemMailboxResolvedConfig | None,
) -> MailboxActivationState:
    """Return the activation state for one completed mailbox mutation."""

    del controller, updated_mailbox
    return "active"


def _refresh_mailbox_projection_and_backend_launch_plan(
    *,
    controller: RuntimeSessionController,
    previous_launch_plan: LaunchPlan,
    updated_launch_plan: LaunchPlan,
) -> None:
    """Refresh backend launch-plan state after one mailbox mutation."""

    del previous_launch_plan
    _refresh_backend_launch_plan(
        backend_session=controller.backend_session,
        launch_plan=updated_launch_plan,
    )


def _without_retired_mailbox_metadata(launch_plan: LaunchPlan) -> LaunchPlan:
    """Return one launch plan with retired mailbox-live metadata removed."""

    if not any(key in launch_plan.metadata for key in _RETIRED_MAILBOX_METADATA_KEYS):
        return launch_plan
    return replace(
        launch_plan,
        metadata={
            key: value
            for key, value in launch_plan.metadata.items()
            if key not in _RETIRED_MAILBOX_METADATA_KEYS
        },
    )


def _normalize_optional_mailbox_text(value: str | None, *, field_name: str) -> str | None:
    """Normalize one optional mailbox command field."""

    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        raise SessionManifestError(f"`{field_name}` must not be blank.")
    return stripped


def _launch_plan_with_memory(
    launch_plan: LaunchPlan,
    *,
    memory: AgentMemoryPaths | None,
) -> LaunchPlan:
    """Return a launch plan with the effective memory env binding injected."""

    updated_env = dict(launch_plan.env)
    for env_var_name in _MEMORY_ENV_VARS | _RETIRED_MEMORY_ENV_VARS:
        updated_env.pop(env_var_name, None)
    updated_env_var_names = set(launch_plan.env_var_names)
    updated_env_var_names.difference_update(_MEMORY_ENV_VARS)
    updated_env_var_names.difference_update(_RETIRED_MEMORY_ENV_VARS)
    if memory is not None:
        memory_values = memory_env(memory)
        updated_env.update(memory_values)
        updated_env_var_names.update(memory_values)
    return replace(
        launch_plan,
        env=updated_env,
        env_var_names=sorted(updated_env_var_names),
    )


def _launch_plan_with_transient_env_overrides(
    launch_plan: LaunchPlan,
    *,
    env_overrides: dict[str, str] | None,
) -> LaunchPlan:
    """Apply validated one-off values for this generation only."""

    if not env_overrides:
        return launch_plan

    protected = {*launch_plan.private_env_var_names, launch_plan.home_env_var}
    if launch_plan.tool == "dsh":
        protected.update(("DSH_AGENTS_HOME", "DSH_PERMISSION_MODE", "DSH_BUNDLED_SKILL_DIR"))
    try:
        overrides = validate_persistent_env_records(
            env_overrides,
            auth_env_allowlist=sorted(protected),
            source="One-shot launch environment",
        )
    except ValueError as exc:
        raise SessionManifestError(str(exc)) from exc
    updated_env = {**launch_plan.env, **overrides}
    if launch_plan.tool == "kimi":
        try:
            validate_kimi_v2_engine_env(updated_env)
        except KimiSystemPromptError as exc:
            raise SessionManifestError(str(exc)) from exc
    return replace(
        launch_plan,
        env=updated_env,
        transient_env_var_names=launch_plan.transient_env_var_names.union(overrides),
    )


def _resolve_managed_launch_environment(
    plan: LaunchPlan,
    *,
    root_context: dict[str, str],
    agent_id: str | None,
    manifest_path: Path,
    agent_def_dir: Path | None,
    api_base_url: str = "",
    previous_keys: frozenset[str] = frozenset(),
) -> LaunchPlan:
    """Resolve the explicit provider environment and its safe tmux projection."""

    context_vars = {
        HOUMAO_GLOBAL_RUNTIME_DIR_ENV_VAR,
        HOUMAO_GLOBAL_MAILBOX_DIR_ENV_VAR,
        PROJECT_OVERLAY_DIR_ENV_VAR,
        "HOUMAO_AGENT_PRIVATE_WORKSPACE_ROOT",
    }
    selected_context = {
        key: value
        for key, value in root_context.items()
        if key in context_vars and isinstance(value, str) and Path(value).is_absolute()
    }
    environment = {
        **owner_launch_baseline(os.environ),
        **plan.env,
        **selected_context,
        plan.home_env_var: str(plan.home_path),
        AGENT_MANIFEST_PATH_ENV_VAR: str(manifest_path.resolve()),
        "HOUMAO_TOOL": plan.tool,
    }
    if plan.execution_binding is not None:
        environment[HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR] = plan.execution_binding.registry_root
    if agent_id is not None:
        environment[AGENT_ID_ENV_VAR] = agent_id
    masked_keys = previous_keys | (context_vars - selected_context.keys())
    if plan.mode in {"headless", "tui"} and agent_def_dir is not None:
        environment[AGENT_DEF_DIR_ENV_VAR] = str(agent_def_dir.resolve())
    else:
        masked_keys = masked_keys | {AGENT_DEF_DIR_ENV_VAR}
    if plan.backend in _TMUX_BACKED_BACKENDS and tmux_config_injection_enabled():
        overlay_tmux_rich_color_environment(environment)
        masked_keys = masked_keys | {"NO_COLOR"}
    if not should_preserve_no_proxy_env(os.environ) and (
        plan.backend != "cao_rest" or is_supported_loopback_cao_base_url(api_base_url)
    ):
        inject_loopback_no_proxy_env(environment)
    public_env = {
        name: value for name, value in environment.items() if name not in plan.private_env_var_names
    }
    return replace(
        plan,
        env=environment,
        public_env=public_env,
        previous_public_env_var_names=frozenset(masked_keys - public_env.keys()),
        metadata={**plan.metadata, "launch_root_context": selected_context},
    )


def _launch_plan_with_headless_display_controls(
    launch_plan: LaunchPlan,
    *,
    style: HeadlessDisplayStyle | None,
    detail: HeadlessDisplayDetail | None,
) -> LaunchPlan:
    """Return a launch plan with normalized headless display metadata."""

    if launch_plan.mode != "headless":
        return launch_plan

    updated_metadata = dict(launch_plan.metadata)
    updated_metadata["headless_display_style"] = resolve_headless_display_style(
        style if style is not None else updated_metadata.get("headless_display_style")
    )
    updated_metadata["headless_display_detail"] = resolve_headless_display_detail(
        detail if detail is not None else updated_metadata.get("headless_display_detail")
    )
    return replace(launch_plan, metadata=updated_metadata)


def _backend_requires_provider_start_relaunch(backend: BackendKind) -> bool:
    """Return whether one backend relaunch must rebuild provider-start state."""

    return backend in {
        "local_interactive",
        "codex_headless",
        "codex_app_server",
        "claude_headless",
        "kimi_headless",
        "kimi_acp",
        "dsh_headless",
        "dsh_acp",
        "dsh_web",
        "kimi_web",
    }


def _backend_supports_stopped_session_relaunch(backend: BackendKind) -> bool:
    """Return whether one backend supports reviving a stopped tmux-backed runtime home."""

    return backend in _STOPPED_SESSION_RELAUNCH_BACKENDS


def _build_provider_start_launch_plan_for_relaunch(
    controller: RuntimeSessionController,
) -> LaunchPlan:
    """Rebuild a provider-start launch plan for one local tmux-backed relaunch."""

    if controller.agent_launch_authority is not None:
        authority = controller.agent_launch_authority
        if authority.session_origin == _JOINED_SESSION_ORIGIN:
            if authority.posture_kind == "unavailable":
                raise SessionManifestError(
                    "Joined-session relaunch is unavailable because no launch options were recorded."
                )
            if controller.agent_def_dir is None:
                raise SessionManifestError(
                    "Joined-session relaunch requires a persisted agent-definition directory."
                )
            handle = load_session_manifest(controller.manifest_path)
            payload = parse_session_manifest_payload(handle.payload, source=str(handle.path))
            role_package = load_role_package(controller.agent_def_dir, controller.role_name)
            updated_launch_plan = _build_joined_launch_plan_from_manifest_payload(
                payload=payload,
                role_package=role_package,
                mailboxes=_resolved_mailbox_from_manifest_payload(
                    payload,
                    session_manifest_path=controller.manifest_path,
                ),
            )
            updated_launch_plan = _launch_plan_with_memory(
                updated_launch_plan,
                memory=_memory_from_controller(controller),
            )
            return persist_runtime_launch_inputs(
                _preserve_controller_execution_authority(controller, updated_launch_plan),
                session_root=controller.manifest_path.parent,
            )

    if controller.agent_def_dir is None:
        raise SessionManifestError(
            "Local provider relaunch requires a persisted agent-definition directory."
        )

    manifest = load_brain_manifest(controller.brain_manifest_path)
    role_package = load_role_package(controller.agent_def_dir, controller.role_name)
    stored_role_prompt = _stored_role_prompt_from_brain_manifest(manifest)
    controller_memory = _memory_from_controller(controller)
    if stored_role_prompt is not None:
        role_package = replace(role_package, system_prompt=stored_role_prompt)
    else:
        persisted_managed_header_enabled = _managed_prompt_header_enabled_from_brain_manifest(
            manifest
        )
        managed_header_decision = resolve_managed_prompt_header_decision(
            launch_override=None,
            stored_policy=None,
            default_enabled=(
                persisted_managed_header_enabled
                if persisted_managed_header_enabled is not None
                else True
            ),
        )
        built_agent_name, built_agent_id = _built_manifest_identity(manifest)
        resolved_agent_name = controller.agent_identity or built_agent_name
        if resolved_agent_name is None:
            resolved_agent_name = derive_default_canonical_agent_name(
                tool=controller.launch_plan.tool,
                role_name=controller.role_name,
            )
        else:
            resolved_agent_name = normalize_managed_agent_name(resolved_agent_name)
        resolved_agent_id = controller.agent_id or built_agent_id
        if resolved_agent_id is not None:
            resolved_agent_id = normalize_managed_agent_id(resolved_agent_id)
        else:
            raise SessionManifestError("Existing agent is missing required persisted agent_id.")
        role_package = replace(
            role_package,
            system_prompt=compose_managed_launch_prompt(
                base_prompt=role_package.system_prompt,
                overlay_mode=None,
                overlay_text=None,
                managed_header_enabled=managed_header_decision.enabled,
                agent_name=resolved_agent_name,
                agent_id=resolved_agent_id,
                memo_file=(
                    str(controller_memory.memo_file) if controller_memory is not None else None
                ),
            ),
        )
    updated_launch_plan = build_launch_plan(
        LaunchPlanRequest(
            brain_manifest=manifest,
            role_package=role_package,
            backend=controller.launch_plan.backend,
            working_directory=controller.launch_plan.working_directory,
            mailboxes=controller.launch_plan.mailboxes,
            intent="provider_start",
            session_root=controller.manifest_path.parent,
        )
    )
    updated_launch_plan = _launch_plan_with_memory(
        updated_launch_plan,
        memory=controller_memory,
    )
    updated_launch_plan = _launch_plan_with_headless_display_controls(
        updated_launch_plan,
        style=resolve_headless_display_style(
            controller.launch_plan.metadata.get("headless_display_style")
        ),
        detail=resolve_headless_display_detail(
            controller.launch_plan.metadata.get("headless_display_detail")
        ),
    )
    old_plan = controller.launch_plan
    recorded_context = old_plan.metadata.get("launch_root_context", {})
    updated_launch_plan = _resolve_managed_launch_environment(
        _preserve_controller_execution_authority(controller, updated_launch_plan),
        root_context=recorded_context if isinstance(recorded_context, dict) else {},
        agent_id=controller.agent_id,
        manifest_path=controller.manifest_path,
        agent_def_dir=controller.agent_def_dir,
        previous_keys=old_plan.previous_public_env_var_names
        | frozenset(old_plan.public_env if old_plan.public_env is not None else old_plan.env),
    )
    return persist_runtime_launch_inputs(
        updated_launch_plan,
        session_root=controller.manifest_path.parent,
    )


def _preserve_controller_execution_authority(
    controller: RuntimeSessionController, launch_plan: LaunchPlan
) -> LaunchPlan:
    """Keep relaunch plan reconstruction within the original owner and server."""

    return replace(
        launch_plan,
        execution_binding=controller.launch_plan.execution_binding,
        metadata={
            **launch_plan.metadata,
            "tmux_socket_path": controller.launch_plan.metadata.get("tmux_socket_path"),
        },
    )


def _hook_observation_session_root(controller: RuntimeSessionController) -> Path | None:
    """Return the runtime-owned session root that owns hook artifacts."""

    return runtime_owned_session_root_from_manifest_path(controller.manifest_path)


def _activate_hook_observation_for_controller(
    *,
    controller: RuntimeSessionController,
    launch_plan: LaunchPlan,
) -> LaunchPlan:
    """Start the collector and install observer settings before a provider start."""

    session_root = _hook_observation_session_root(controller)
    if session_root is None:
        return launch_plan
    return activate_hook_observation_for_provider_start(
        launch_plan,
        session_root=session_root,
    )


def _stop_hook_observation_for_controller(controller: RuntimeSessionController) -> None:
    """Stop the controller session's collector, tolerating a missing record."""

    stop_hook_observation(
        _hook_observation_session_root(controller),
        tool=controller.launch_plan.tool,
    )


def _memory_from_controller(
    controller: RuntimeSessionController,
) -> AgentMemoryPaths | None:
    """Return the controller's resolved memory paths when they exist."""

    if (
        controller.memory_root is None
        or controller.memo_file is None
        or controller.pages_dir is None
    ):
        return None
    return AgentMemoryPaths(
        memory_root=controller.memory_root,
        memo_file=controller.memo_file,
        pages_dir=controller.pages_dir,
    )


def _memory_from_manifest_payload(
    *,
    payload: SessionManifestPayloadV4,
) -> AgentMemoryPaths | None:
    """Return the resolved memory paths stored in one session manifest."""

    if (
        payload.runtime.memory_root is None
        or payload.runtime.memo_file is None
        or payload.runtime.pages_dir is None
    ):
        return None
    return AgentMemoryPaths(
        memory_root=Path(payload.runtime.memory_root).resolve(),
        memo_file=Path(payload.runtime.memo_file).resolve(),
        pages_dir=Path(payload.runtime.pages_dir).resolve(),
    )


def _resolve_start_session_identity(
    *,
    manifest: dict[str, object],
    tool: str,
    role_name: str,
    requested_agent_name: str | None = None,
    requested_agent_identity: str | None,
    requested_agent_id: str | None,
    requested_agent_id_mode: AgentIdMode | None = None,
    requested_tmux_session_name: str | None = None,
    default_tmux_session_name: str | None = None,
) -> ResolvedRuntimeIdentity:
    """Resolve canonical name, authoritative id, and tmux handle for session start."""

    built_identity = _built_manifest_identity(manifest)
    warnings: list[str] = []

    if requested_agent_name is not None and requested_agent_identity is not None:
        raise SessionManifestError(
            "start-session does not allow both --agent-name and --agent-identity."
        )
    if requested_agent_identity is not None and is_path_like_agent_identity(
        requested_agent_identity
    ):
        raise SessionManifestError(
            "start-session --agent-identity must be a canonical agent name, not a manifest path."
        )

    if requested_agent_name is not None:
        agent_name = normalize_user_managed_agent_name(requested_agent_name)
        canonical_agent_name = f"{AGENT_NAMESPACE_PREFIX}{agent_name}"
    elif requested_agent_identity is not None:
        normalized = normalize_agent_identity_name(requested_agent_identity)
        agent_name = normalized.canonical_name
        canonical_agent_name = normalized.canonical_name
        warnings.extend(normalized.warnings)
    elif built_identity[0] is not None:
        agent_name = built_identity[0]
        canonical_agent_name = _canonical_runtime_agent_name(agent_name)
    else:
        canonical_agent_name = _default_canonical_agent_name(tool=tool, role_name=role_name)
        agent_name = canonical_agent_name

    persisted_agent_id = built_identity[1]
    if persisted_agent_id is not None:
        if requested_agent_id_mode is not None:
            raise SessionManifestError(
                "An existing-agent brain cannot generate another agent_id. "
                "Build an identity-free template to create another agent."
            )
        if (
            requested_agent_id is not None
            and normalize_managed_agent_id(requested_agent_id) != persisted_agent_id
        ):
            raise SessionManifestError("An existing-agent brain cannot change its agent_id.")
        agent_id = persisted_agent_id
    else:
        agent_id = (
            AgentIdentityCreation(
                agent_name=agent_name,
                agent_id=requested_agent_id,
                agent_id_mode=requested_agent_id_mode,
            )
            .resolve()
            .agent_id
        )

    persisted_agent_name = built_identity[0]
    if (
        persisted_agent_id is not None
        and persisted_agent_name is not None
        and persisted_agent_name != agent_name
    ):
        warnings.append(
            "reusing persisted authoritative agent_id "
            f"`{persisted_agent_id}` for agent name "
            f"`{agent_name}` after build metadata previously named "
            f"`{persisted_agent_name}`"
        )

    stripped_requested_tmux_session_name = (
        requested_tmux_session_name.strip()
        if requested_tmux_session_name is not None and requested_tmux_session_name.strip()
        else None
    )
    stripped_default_tmux_session_name = (
        default_tmux_session_name.strip()
        if default_tmux_session_name is not None and default_tmux_session_name.strip()
        else None
    )
    if stripped_requested_tmux_session_name is not None:
        resolved_tmux_session_name = stripped_requested_tmux_session_name
    elif stripped_default_tmux_session_name is not None:
        try:
            occupied_session_names = list_tmux_sessions_shared()
        except TmuxCommandError as exc:
            raise SessionManifestError(
                "start-session requires `tmux` on PATH for tmux-backed backends."
            ) from exc
        if stripped_default_tmux_session_name in occupied_session_names:
            raise SessionManifestError(
                "Managed reused-home restart cannot restore preserved tmux session name "
                f"`{stripped_default_tmux_session_name}` because a live tmux session already "
                "uses it. Stop that session or pass an explicit `--session-name` override."
            )
        resolved_tmux_session_name = stripped_default_tmux_session_name
    else:
        try:
            occupied_session_names = list_tmux_sessions_shared()
        except TmuxCommandError as exc:
            raise SessionManifestError(
                "start-session requires `tmux` on PATH for tmux-backed backends."
            ) from exc

        resolved_tmux_session_name = derive_tmux_session_name(
            canonical_agent_name=canonical_agent_name,
            launch_epoch_ms=time.time_ns() // 1_000_000,
            occupied_session_names=occupied_session_names,
        )

    return ResolvedRuntimeIdentity(
        agent_name=agent_name,
        canonical_agent_name=canonical_agent_name,
        agent_id=agent_id,
        tmux_session_name=resolved_tmux_session_name,
        warnings=tuple(warnings),
    )


def _built_manifest_identity(manifest: dict[str, object]) -> tuple[str | None, str | None]:
    """Read optional persisted identity metadata from a built brain manifest."""

    raw_identity = manifest.get("identity")
    if raw_identity is None:
        return None, None
    if not isinstance(raw_identity, dict):
        raise SessionManifestError("Brain identity must be an object with required agent_id.")

    raw_agent_name = raw_identity.get("canonical_agent_name")
    agent_name = None
    if isinstance(raw_agent_name, str) and raw_agent_name.strip():
        agent_name = normalize_managed_agent_name(raw_agent_name)

    raw_agent_id = raw_identity.get("agent_id")
    if not isinstance(raw_agent_id, str) or not raw_agent_id.strip():
        raise SessionManifestError("Existing brain identity is missing required agent_id.")
    agent_id = normalize_managed_agent_id(raw_agent_id)
    return agent_name, agent_id


def _default_canonical_agent_name(*, tool: str, role_name: str) -> str:
    """Return the default canonical agent name for a tmux-backed session."""

    return derive_default_canonical_agent_name(tool=tool, role_name=role_name)


def _canonical_runtime_agent_name(agent_name: str) -> str:
    """Return the runtime-owned canonical tmux name for one persisted agent name."""

    normalized_name = normalize_managed_agent_name(agent_name)
    if normalized_name.startswith(AGENT_NAMESPACE_PREFIX):
        return normalized_name
    return f"{AGENT_NAMESPACE_PREFIX}{normalized_name}"


def _refresh_backend_launch_plan(
    *,
    backend_session: InteractiveSession,
    launch_plan: LaunchPlan,
) -> None:
    update_method = getattr(backend_session, "update_launch_plan", None)
    if callable(update_method):
        update_method(launch_plan)
        return
    raise SessionManifestError(
        f"backend={launch_plan.backend!r} does not support mailbox binding refresh."
    )


def _resolve_manifest_path(value: str, *, base: Path) -> Path:
    """Resolve a manifest path relative to the provided base directory."""

    candidate = Path(value)
    if candidate.is_absolute():
        return candidate
    return (base / candidate).resolve()


def _ensure_tmux_session_exists(*, session_name: str) -> None:
    """Validate that a tmux session exists before reading its environment."""

    try:
        has_result = has_tmux_session_shared(session_name=session_name)
    except TmuxCommandError as exc:
        raise SessionManifestError(
            f"Agent-name resolution requires `tmux` on PATH for session `{session_name}`."
        ) from exc
    if has_result.returncode == 0:
        return
    if has_result.returncode == 1:
        raise SessionManifestError(
            f"Agent not found: tmux session `{session_name}` does not exist. "
            "Run `tmux ls` to discover active agents or pass a manifest path."
        )
    detail = tmux_error_detail_shared(has_result)
    raise SessionManifestError(
        f"Failed to query tmux session `{session_name}`: {detail or 'unknown tmux error'}"
    )


def _read_tmux_session_env_var(
    *,
    session_name: str,
    variable_name: str,
    missing_message: str,
) -> str:
    """Read one tmux session environment value and reject missing/blank output."""

    try:
        env_result = show_tmux_environment_shared(
            session_name=session_name,
            variable_name=variable_name,
        )
    except TmuxCommandError as exc:
        raise SessionManifestError(
            f"Agent-name resolution requires `tmux` on PATH for session `{session_name}`."
        ) from exc

    env_detail = tmux_error_detail_shared(env_result)
    if env_result.returncode != 0:
        if "unknown variable" in env_detail.lower():
            raise _TmuxLocalDiscoveryUnavailableError(
                f"{missing_message}: tmux session `{session_name}` has no `{variable_name}` value."
            )
        raise SessionManifestError(
            f"Failed reading `{variable_name}` from tmux session "
            f"`{session_name}`: {env_detail or 'unknown tmux error'}"
        )

    line = ""
    for raw_line in env_result.stdout.splitlines():
        stripped = raw_line.strip()
        if stripped:
            line = stripped
            break

    if not line or line == f"-{variable_name}":
        raise _TmuxLocalDiscoveryUnavailableError(
            f"{missing_message}: tmux session `{session_name}` has blank `{variable_name}`."
        )

    prefix = f"{variable_name}="
    if not line.startswith(prefix):
        raise SessionManifestError(
            f"Unexpected tmux environment output for `{session_name}`: {line}"
        )

    value = line[len(prefix) :].strip()
    if not value:
        raise _TmuxLocalDiscoveryUnavailableError(
            f"{missing_message}: tmux session `{session_name}` has blank `{variable_name}`."
        )
    return value


def _resolve_manifest_path_from_tmux_session(*, session_name: str) -> Path:
    """Resolve a session manifest path from tmux session environment state."""

    manifest_path = Path(
        _read_tmux_session_env_var(
            session_name=session_name,
            variable_name=AGENT_MANIFEST_PATH_ENV_VAR,
            missing_message="Manifest pointer missing",
        )
    )
    if not manifest_path.is_absolute():
        raise SessionManifestError(
            f"Invalid manifest pointer in tmux session `{session_name}`: "
            f"`{AGENT_MANIFEST_PATH_ENV_VAR}` must be an absolute path."
        )
    manifest_path = manifest_path.resolve()
    if not manifest_path.is_file():
        raise _TmuxLocalDiscoveryUnavailableError(
            f"Manifest pointer stale: `{AGENT_MANIFEST_PATH_ENV_VAR}` in tmux "
            f"session `{session_name}` points to missing file `{manifest_path}`."
        )
    return manifest_path


def _resolve_agent_identity_from_shared_registry_agent_id(
    *,
    agent_id: str,
    explicit_agent_def_dir: Path | None,
) -> AgentIdentityResolution | None:
    """Resolve a control target directly from the shared registry by agent id."""

    record = resolve_live_agent_record_by_agent_id(agent_id)
    if record is None:
        return None
    return _agent_identity_resolution_from_registry_record(
        record=record,
        explicit_agent_def_dir=explicit_agent_def_dir,
        warnings=(),
    )


def _resolve_agent_identity_from_tmux_local(
    *,
    canonical_agent_identity: str,
    explicit_agent_def_dir: Path | None,
    warnings: tuple[str, ...],
) -> AgentIdentityResolution:
    """Resolve a control target from tmux-local discovery pointers."""

    direct_error: SessionManifestError | _TmuxLocalDiscoveryUnavailableError | None = None
    try:
        return _resolve_agent_identity_from_addressed_tmux_session(
            canonical_agent_identity=canonical_agent_identity,
            explicit_agent_def_dir=explicit_agent_def_dir,
            warnings=warnings,
        )
    except (SessionManifestError, _TmuxLocalDiscoveryUnavailableError) as exc:
        direct_error = exc

    try:
        session_names = sorted(list_tmux_sessions_shared())
    except TmuxCommandError as exc:
        if direct_error is not None:
            raise direct_error
        raise SessionManifestError("Agent-name resolution requires `tmux` on PATH.") from exc

    matches: list[tuple[str, Path, SessionManifestPayloadV4]] = []
    for session_name in session_names:
        try:
            manifest_path = _resolve_manifest_path_from_tmux_session(session_name=session_name)
            payload = parse_session_manifest_payload(
                load_session_manifest(manifest_path).payload,
                source=str(manifest_path),
            )
        except (SessionManifestError, _TmuxLocalDiscoveryUnavailableError):
            continue
        if payload.backend not in _TMUX_BACKED_BACKENDS:
            continue
        if payload.tmux_session_name != session_name:
            continue
        if payload.agent_name != canonical_agent_identity:
            continue
        matches.append((session_name, manifest_path, payload))

    if not matches:
        if direct_error is not None:
            raise direct_error
        raise _TmuxLocalDiscoveryUnavailableError(
            f"No local tmux session metadata matched canonical agent name "
            f"`{canonical_agent_identity}`."
        )
    if len(matches) > 1:
        matched_sessions = ", ".join(sorted(session_name for session_name, _, _ in matches))
        raise SessionManifestError(
            "Agent-name resolution is ambiguous: canonical agent name "
            f"`{canonical_agent_identity}` matched multiple tmux sessions: {matched_sessions}."
        )

    _, manifest_path, payload = matches[0]
    return AgentIdentityResolution(
        session_manifest_path=manifest_path,
        canonical_agent_identity=canonical_agent_identity,
        agent_def_dir=_launch_definition_path(payload, explicit_agent_def_dir),
        warnings=warnings,
    )


def _resolve_agent_identity_from_addressed_tmux_session(
    *,
    canonical_agent_identity: str,
    explicit_agent_def_dir: Path | None,
    warnings: tuple[str, ...],
) -> AgentIdentityResolution:
    """Resolve a control target from the addressed canonical tmux session."""

    _ensure_tmux_session_exists(session_name=canonical_agent_identity)
    manifest_path = _resolve_manifest_path_from_tmux_session(session_name=canonical_agent_identity)
    payload = parse_session_manifest_payload(
        load_session_manifest(manifest_path).payload,
        source=str(manifest_path),
    )
    if payload.backend not in _TMUX_BACKED_BACKENDS:
        raise SessionManifestError(
            "Resolved manifest mismatch: name-based resolution requires a tmux-backed "
            f"manifest, got backend={payload.backend!r} from `{manifest_path}`."
        )
    if payload.agent_name != canonical_agent_identity:
        raise _TmuxLocalDiscoveryUnavailableError(
            "Resolved manifest mismatch: canonical agent name "
            f"`{payload.agent_name}` does not match addressed tmux session "
            f"`{canonical_agent_identity}`."
        )
    _validate_resolved_manifest_matches_tmux_session(
        manifest_path=manifest_path,
        session_name=canonical_agent_identity,
    )
    return AgentIdentityResolution(
        session_manifest_path=manifest_path,
        canonical_agent_identity=canonical_agent_identity,
        agent_def_dir=_launch_definition_path(payload, explicit_agent_def_dir),
        warnings=warnings,
    )


def _resolve_agent_identity_from_shared_registry(
    *,
    canonical_agent_identity: str,
    explicit_agent_def_dir: Path | None,
    warnings: tuple[str, ...],
) -> AgentIdentityResolution | None:
    """Resolve a control target from the shared live-agent registry."""

    matches = resolve_live_agent_records_by_name(canonical_agent_identity)
    if not matches:
        return None
    if len(matches) > 1:
        matched_agent_ids = ", ".join(sorted(record.agent_id for record in matches))
        raise SessionManifestError(
            "Shared-registry resolution is ambiguous: canonical agent name "
            f"`{canonical_agent_identity}` matched multiple authoritative ids: "
            f"{matched_agent_ids}."
        )

    return _agent_identity_resolution_from_registry_record(
        record=matches[0],
        explicit_agent_def_dir=explicit_agent_def_dir,
        warnings=warnings,
    )


def _agent_identity_resolution_from_registry_record(
    *,
    record: ManagedAgentRegistryRecordV3,
    explicit_agent_def_dir: Path | None,
    warnings: tuple[str, ...],
) -> AgentIdentityResolution:
    """Build one control-target resolution from a shared-registry record."""

    manifest_path = Path(record.runtime.manifest_path)
    if not manifest_path.is_absolute():
        raise SessionManifestError(
            "Shared-registry record has invalid manifest_path: expected an absolute path, "
            f"got `{manifest_path}`."
        )
    manifest_path = manifest_path.resolve()
    if not manifest_path.is_file():
        raise SessionManifestError(
            f"Shared-registry manifest pointer is stale: `{manifest_path}` does not exist."
        )

    payload = _validate_resolved_manifest_matches_tmux_session(
        manifest_path=manifest_path,
        session_name=record.terminal.session_name,
    )

    return AgentIdentityResolution(
        session_manifest_path=manifest_path,
        canonical_agent_identity=record.agent_name,
        agent_def_dir=_launch_definition_path(payload, explicit_agent_def_dir),
        warnings=warnings,
    )


def _launch_definition_path(
    payload: SessionManifestPayloadV4, override: Path | None
) -> Path | None:
    """Return definition provenance for a future explicit relaunch."""

    if override is not None:
        return override
    saved = payload.runtime.agent_def_dir
    return Path(saved) if saved is not None and Path(saved).is_absolute() else None


def _validate_resolved_manifest_matches_tmux_session(
    *, manifest_path: Path, session_name: str
) -> SessionManifestPayloadV4:
    """Validate tmux-resolved manifest backend and session-name invariants."""

    handle = load_session_manifest(manifest_path)
    payload = parse_session_manifest_payload(handle.payload, source=str(handle.path))
    if payload.backend not in _TMUX_BACKED_BACKENDS:
        raise SessionManifestError(
            "Resolved manifest mismatch: name-based resolution requires a tmux-backed "
            f"manifest, got backend={payload.backend!r} from `{manifest_path}`."
        )

    persisted_session_name = _persisted_tmux_session_name(
        payload=payload,
        manifest_path=manifest_path,
    )
    if persisted_session_name != session_name:
        raise SessionManifestError(
            "Resolved manifest mismatch: persisted tmux session name "
            f"({persisted_session_name!r}) does not match addressed tmux session "
            f"{session_name!r}."
        )
    return payload


def _persisted_tmux_session_name(
    *,
    payload: SessionManifestPayloadV4,
    manifest_path: Path,
) -> str:
    persisted = payload.tmux_session_name
    if persisted is None or not persisted.strip():
        raise SessionManifestError(
            f"Resolved manifest mismatch: `{manifest_path}` is missing non-empty "
            "`payload.tmux_session_name`."
        )
    return persisted.strip()


def _runtime_session_id_from_manifest_path(manifest_path: Path) -> str | None:
    """Return the runtime-owned session id derived from the nested manifest layout."""

    paths = gateway_paths_from_manifest_path(manifest_path)
    if paths is None:
        return None
    return paths.session_root.name


def _build_shared_registry_record_for_controller(
    controller: RuntimeSessionController,
) -> ManagedAgentRegistryRecordV3 | None:
    """Build one shared-registry record from current runtime-owned session state."""

    if not controller._is_tmux_backed():
        return None

    tmux_session_name = _tmux_session_name_for_controller(controller)
    if tmux_session_name is None:
        return None

    canonical_agent_name = controller.agent_identity
    agent_id = controller.agent_id
    generation_id = controller.registry_generation_id
    if generation_id is None or canonical_agent_name is None or agent_id is None:
        return None

    published_at = datetime.now(UTC)
    session_root = runtime_owned_session_root_from_manifest_path(controller.manifest_path)
    return ManagedAgentRegistryRecordV3(
        mode=controller.launch_plan.mode,
        agent_name=canonicalize_registry_agent_name(canonical_agent_name),
        execution_binding=controller.launch_plan.execution_binding,
        agent_id=agent_id,
        generation_id=generation_id,
        lifecycle=RegistryLifecycleV1(
            state="active",
            relaunchable=_shared_registry_record_is_relaunchable(
                controller=controller,
                session_root=session_root,
            ),
            state_updated_at=published_at.isoformat(timespec="seconds"),
        ),
        identity=RegistryIdentityV1(
            backend=controller.launch_plan.backend,
            tool=controller.launch_plan.tool,
        ),
        runtime=_shared_registry_runtime_payload(
            controller=controller,
            session_root=session_root,
        ),
        terminal=RegistryTerminalV2(
            kind="tmux",
            socket_path=controller.launch_plan.metadata.get("tmux_socket_path"),
            current_session_name=tmux_session_name,
            last_session_name=tmux_session_name,
        ),
        liveness=RegistryLivenessV1(
            published_at=published_at.isoformat(timespec="seconds"),
            lease_expires_at=(published_at + TMUX_BACKED_REGISTRY_SENTINEL_LEASE_TTL).isoformat(
                timespec="seconds"
            ),
        ),
        gateway=_shared_registry_gateway_payload(controller),
        mailboxes=_shared_registry_mailbox_payload(controller),
        canonical_mail_identity=controller.launch_plan.mailboxes.canonical_mail_identity,
        native_surface=_registry_native_surface(controller),
    )


def _build_stopped_shared_registry_record_for_controller(
    controller: RuntimeSessionController,
    *,
    last_tmux_session_name: str | None,
) -> ManagedAgentRegistryRecordV3 | None:
    """Build one stopped lifecycle registry record after successful runtime teardown."""

    if not controller._is_tmux_backed():
        return None

    canonical_agent_name = controller.agent_identity
    agent_id = controller.agent_id
    generation_id = controller.registry_generation_id
    if generation_id is None or canonical_agent_name is None or agent_id is None:
        return None
    if (
        not controller.should_publish_shared_registry_record()
        and load_managed_agent_record_by_agent_id(agent_id) is None
    ):
        return None

    session_root = runtime_owned_session_root_from_manifest_path(controller.manifest_path)
    stopped_at = datetime.now(UTC)
    last_session_name = (
        last_tmux_session_name or controller.tmux_session_name or canonical_agent_name
    )
    return ManagedAgentRegistryRecordV3(
        mode=controller.launch_plan.mode,
        agent_name=canonicalize_registry_agent_name(canonical_agent_name),
        execution_binding=controller.launch_plan.execution_binding,
        agent_id=agent_id,
        generation_id=generation_id,
        lifecycle=RegistryLifecycleV1(
            state="stopped",
            relaunchable=_shared_registry_record_is_relaunchable(
                controller=controller,
                session_root=session_root,
            ),
            state_updated_at=stopped_at.isoformat(timespec="seconds"),
            stopped_at=stopped_at.isoformat(timespec="seconds"),
            stop_reason="operator_stop",
        ),
        identity=RegistryIdentityV1(
            backend=controller.launch_plan.backend,
            tool=controller.launch_plan.tool,
        ),
        runtime=_shared_registry_runtime_payload(
            controller=controller,
            session_root=session_root,
        ),
        terminal=RegistryTerminalV2(
            kind="tmux",
            socket_path=controller.launch_plan.metadata.get("tmux_socket_path"),
            current_session_name=None,
            last_session_name=last_session_name,
        ),
        liveness=None,
        gateway=None,
        mailboxes=_shared_registry_mailbox_payload(controller),
        canonical_mail_identity=controller.launch_plan.mailboxes.canonical_mail_identity,
        native_surface=_registry_native_surface(controller),
    )


def _registry_native_surface(controller: RuntimeSessionController) -> NativeSurfaceV1 | None:
    """Read the latest persisted surface rather than a stale controller snapshot."""

    if not controller.manifest_path.is_file():
        return None
    manifest = load_session_manifest(controller.manifest_path)
    return parse_session_manifest_payload(
        manifest.payload, source=str(manifest.path)
    ).native_surface


def _shared_registry_runtime_payload(
    *,
    controller: RuntimeSessionController,
    session_root: Path | None,
) -> RegistryRuntimeV1:
    """Build the shared-registry runtime locator payload for one controller."""

    return RegistryRuntimeV1(
        manifest_path=str(controller.manifest_path.resolve()),
        session_root=str(session_root.resolve()) if session_root is not None else None,
        agent_def_dir=(
            str(controller.agent_def_dir) if controller.agent_def_dir is not None else None
        ),
    )


def _shared_registry_mailbox_payload(controller: RuntimeSessionController) -> RegistryMailboxesV1:
    """Publish only the secret-free projection of both channel authorities."""

    return RegistryMailboxesV1.model_validate(
        safe_registry_mailboxes_projection(controller.launch_plan.mailboxes)
    )


def _shared_registry_record_is_relaunchable(
    *,
    controller: RuntimeSessionController,
    session_root: Path | None,
) -> bool:
    """Return whether the controller retains supported stopped-session relaunch authority."""

    if session_root is None or controller.agent_def_dir is None:
        return False
    return _backend_supports_stopped_session_relaunch(controller.launch_plan.backend)


def _rollback_stopped_session_revival(controller: RuntimeSessionController) -> None:
    """Best-effort cleanup for a failed stopped-session revival attempt."""

    if not isinstance(
        controller.backend_session,
        (HeadlessInteractiveSession, DshWebSession, KimiWebSession, ManagedServiceSession),
    ):
        controller.tmux_session_name = None
        return
    controller.backend_session.configure_stop_force_cleanup(force_cleanup=True)
    result = controller.backend_session.terminate()
    controller.tmux_session_name = None
    if result.status == "ok":
        return
    message = f"Stopped-session revival cleanup failed: {result.detail}"
    controller.operation_warnings = (*controller.operation_warnings, message)
    _LOGGER.warning(message)


def _shared_registry_gateway_payload(
    controller: RuntimeSessionController,
) -> RegistryGatewayV1 | None:
    """Build optional live gateway connect metadata for registry publication."""

    paths = gateway_paths_from_manifest_path(controller.manifest_path)
    if paths is None:
        return None

    if paths.current_instance_path.is_file():
        try:
            current_instance = load_gateway_current_instance(paths.current_instance_path)
        except SessionManifestError:
            current_instance = None
    else:
        current_instance = None

    if current_instance is None:
        return None

    return RegistryGatewayV1(
        host=current_instance.host,
        port=current_instance.port,
        state_path=str(paths.state_path.resolve()),
        protocol_version=current_instance.protocol_version,
        owner_connect_url=owner_gateway_base_url(current_instance.port),
        endpoint_descriptor=current_instance.endpoint_descriptor,
    )


def _tmux_session_name_for_controller(controller: RuntimeSessionController) -> str | None:
    """Return the tmux session name for a runtime controller."""

    if controller.tmux_session_name is not None:
        return controller.tmux_session_name
    if isinstance(controller.backend_session, CaoRestSession):
        return controller.backend_session.state.session_name
    if isinstance(controller.backend_session, HeadlessInteractiveSession):
        return controller.backend_session.state.tmux_session_name
    if isinstance(controller.backend_session, ManagedServiceSession):
        return controller.backend_session.state.tmux_session_name
    return None


def _require_gateway_paths_for_controller(controller: RuntimeSessionController) -> GatewayPaths:
    """Return runtime-owned gateway paths for one controller.

    Parameters
    ----------
    controller:
        Runtime controller whose gateway assets should exist.

    Returns
    -------
    GatewayPaths
        Resolved gateway filesystem layout for the controller.
    """

    paths = gateway_paths_from_manifest_path(controller.manifest_path)
    if paths is None:
        raise GatewayDiscoveryError(
            "Gateway operations require a runtime-owned session manifest rooted at "
            "`<session-root>/manifest.json`."
        )
    controller.ensure_gateway_capability()
    return paths


@contextmanager
def _gateway_lifecycle_lock(manifest_path: Path) -> Iterator[None]:
    """Serialize live deployment selection with the owner's attach and detach."""

    lock_path = manifest_path.parent / ".gateway-lifecycle.lock"
    descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        os.close(descriptor)


def _attach_gateway_for_controller(
    controller: RuntimeSessionController,
    *,
    host_override: str | None,
    port_override: int | None,
    execution_mode_override: GatewayCurrentExecutionMode | None,
    tui_tracking_timing_overrides: GatewayTuiTrackingTimingOverridesV1 | None,
    plugin_config: GatewayPluginConfiguration | None = None,
    access_config: GatewayDeployment | None = None,
) -> GatewayControlResult:
    """Start a live gateway process for one runtime-owned controller.

    Parameters
    ----------
    controller:
        Runtime controller whose gateway should be attached.
    host_override:
        Optional CLI host override for the attach action.
    port_override:
        Optional CLI port override for the attach action.
    execution_mode_override:
        Optional CLI execution-mode override for the attach action.
    tui_tracking_timing_overrides:
        Optional CLI/API timing override for gateway-owned TUI tracking.
    plugin_config:
        Complete plugin selection. Omission preserves the persisted selection;
        an explicitly empty selection clears it after the gateway is stopped.

    Returns
    -------
    GatewayControlResult
        Structured attach outcome for CLI and API callers.
    """

    if controller.launch_plan.backend not in _GATEWAY_ATTACH_SUPPORTED_BACKENDS:
        paths = _require_gateway_paths_for_controller(controller)
        supported_backends = ", ".join(
            repr(backend) for backend in _GATEWAY_ATTACH_SUPPORTED_BACKENDS
        )
        detail = (
            "Gateway attach is only implemented for runtime-owned tmux-backed backends "
            f"{{{supported_backends}}} in v1, got "
            f"backend={controller.launch_plan.backend!r}."
        )
        return GatewayControlResult(
            status="error",
            action="gateway_attach",
            detail=detail,
            gateway_root=str(paths.gateway_root),
        )

    paths = _require_gateway_paths_for_controller(controller)
    if (
        mode_for_backend(controller.launch_plan.backend) == "web"
        and tui_tracking_timing_overrides is not None
        and tui_tracking_timing_overrides.has_values()
    ):
        return GatewayControlResult(
            status="error",
            action="gateway_attach",
            detail="DSH Web does not support terminal tracking timing controls.",
            gateway_root=str(paths.gateway_root),
        )
    attach_contract = resolve_internal_gateway_attach_contract(paths)
    try:
        access = gateway_access_for_manifest(controller.manifest_path)
        access.store.load()
        access.store.load_self(access.target.incarnation)
        retained_deployment = load_gateway_deployment(controller.manifest_path)
    except (GatewayAccessError, OSError, ValueError, SessionManifestError):
        return GatewayControlResult(
            status="error",
            action="gateway_attach",
            detail="Gateway owner access policy is unavailable.",
            gateway_root=str(paths.gateway_root),
        )
    deployment = access_config if access_config is not None else retained_deployment
    deployment_changed = deployment != retained_deployment
    if deployment is not None and (
        (host_override is not None and host_override != deployment.bind_host)
        or (port_override is not None and port_override != deployment.bind_port)
    ):
        return GatewayControlResult(
            status="error",
            action="gateway_attach",
            detail="Gateway listener overrides conflict with the selected access configuration.",
            gateway_root=str(paths.gateway_root),
        )
    starting = False
    try:
        host, requested_port = _resolve_gateway_listener(
            paths=paths,
            attach_contract=attach_contract,
            host_override=deployment.bind_host if deployment is not None else host_override,
            port_override=(
                deployment.bind_port or (0 if deployment_changed else None)
                if deployment is not None
                else port_override
            ),
        )
        if host == "0.0.0.0" and deployment is None:
            raise GatewayAttachError(
                "An all-interface gateway requires explicit access configuration."
            )
        execution_mode = _resolve_gateway_execution_mode(
            controller=controller,
            paths=paths,
            execution_mode_override=execution_mode_override,
        )
        tui_tracking_timings = _resolve_gateway_tui_tracking_timings(
            paths=paths,
            explicit=tui_tracking_timing_overrides,
        )
        desired_config = _load_optional_desired_config(paths) or GatewayDesiredConfigV1()
        selection = plugin_config if plugin_config is not None else desired_config.desired_plugins
        live_instance = _live_gateway_for_plugin_attach(controller=controller, paths=paths)
        if live_instance is not None:
            if (
                deployment_changed
                or live_instance.host != host
                or requested_port not in {0, live_instance.port}
                or live_instance.execution_mode != execution_mode
                or (
                    desired_config.desired_tui_tracking_timings
                    or GatewayTuiTrackingTimingConfigV1()
                )
                != tui_tracking_timings
            ):
                return GatewayControlResult(
                    status="error",
                    action="gateway_attach",
                    detail="Gateway deployment changed. Detach and attach to apply the new settings.",
                    gateway_root=str(paths.gateway_root),
                )
            if selection is not None:
                try:
                    snapshot = owner_gateway_client_for_controller(
                        controller,
                        endpoint=GatewayEndpoint(host=live_instance.host, port=live_instance.port),
                        private=True,
                    ).get_plugins()
                except (GatewayHttpError, GatewayAccessError, SessionManifestError, ValueError):
                    return GatewayControlResult(
                        status="error",
                        action="gateway_attach",
                        detail="Cannot verify the live gateway plugin configuration.",
                        gateway_root=str(paths.gateway_root),
                    )
                if snapshot.configuration_digest != selection.configuration_digest:
                    return GatewayControlResult(
                        status="error",
                        action="gateway_attach",
                        detail="Gateway plugin selection changed. Detach and attach to apply it.",
                        gateway_root=str(paths.gateway_root),
                    )
            controller.gateway_root = paths.gateway_root
            controller.gateway_attach_path = paths.attach_path
            controller.gateway_host = live_instance.host
            controller.gateway_port = live_instance.port
            return GatewayControlResult(
                status="ok",
                action="gateway_attach",
                detail="Reused the live gateway with the equivalent configuration.",
                gateway_root=str(paths.gateway_root),
                gateway_host=live_instance.host,
                gateway_port=live_instance.port,
            )
        if deployment_changed and deployment is not None:
            save_gateway_deployment(controller.manifest_path, deployment)
        if plugin_config is not None:
            write_gateway_desired_config(
                paths.desired_config_path,
                desired_config.model_copy(update={"desired_plugins": plugin_config}),
            )
        starting = True
        resolved_port = _start_gateway_process(
            controller=controller,
            paths=paths,
            host=host,
            port=requested_port,
            execution_mode=execution_mode,
            tui_tracking_timings=tui_tracking_timings,
        )
    except (
        GatewayAttachError,
        GatewayDiscoveryError,
        GatewayProtocolError,
        GatewayUnsupportedBackendError,
        GatewayAccessError,
        OSError,
        SessionManifestError,
        TmuxCommandError,
    ) as exc:
        if starting:
            _clear_stale_gateway_runtime_state(
                controller=controller,
                paths=paths,
                attach_contract=attach_contract,
            )
        return GatewayControlResult(
            status="error",
            action="gateway_attach",
            detail=str(exc),
            gateway_root=str(paths.gateway_root),
        )

    controller.gateway_root = paths.gateway_root
    controller.gateway_attach_path = paths.attach_path
    controller.gateway_host = host
    controller.gateway_port = resolved_port
    return GatewayControlResult(
        status="ok",
        action="gateway_attach",
        detail=(
            f"Attached gateway for session `{controller._require_tmux_session_name()}` on "
            f"{host}:{resolved_port}."
        ),
        gateway_root=str(paths.gateway_root),
        gateway_host=host,
        gateway_port=resolved_port,
    )


def _detach_gateway_for_controller(controller: RuntimeSessionController) -> GatewayControlResult:
    """Detach a live gateway instance while preserving attachability metadata.

    Parameters
    ----------
    controller:
        Runtime controller whose live gateway should be detached.

    Returns
    -------
    GatewayControlResult
        Structured detach outcome for CLI and API callers.
    """

    paths = _require_gateway_paths_for_controller(controller)
    attach_contract = resolve_internal_gateway_attach_contract(paths)
    try:
        current_instance = load_gateway_current_instance(paths.current_instance_path)
    except SessionManifestError:
        current_instance = None
    session_name = controller._require_tmux_session_name()
    if current_instance is not None and current_instance.execution_mode == "tmux_auxiliary_window":
        try:
            was_running = _same_session_gateway_is_alive(
                session_name=session_name,
                current_instance=current_instance,
            )
        except TmuxCommandError as exc:
            return GatewayControlResult(
                status="error",
                action="gateway_detach",
                detail=f"Failed to inspect gateway tmux pane state: {exc}",
                gateway_root=str(paths.gateway_root),
            )
        try:
            _stop_same_session_gateway_surface(
                session_name=session_name,
                current_instance=current_instance,
                strict=True,
            )
        except GatewayAttachError as exc:
            return GatewayControlResult(
                status="error",
                action="gateway_detach",
                detail=str(exc),
                gateway_root=str(paths.gateway_root),
            )
        delete_gateway_current_instance(paths)
        _clear_stale_gateway_runtime_state(
            controller=controller,
            paths=paths,
            attach_contract=attach_contract,
        )
        controller.gateway_host = None
        controller.gateway_port = None
        return GatewayControlResult(
            status="ok",
            action="gateway_detach",
            detail=(
                "Detached live gateway instance."
                if was_running
                else "Cleared stale or absent live gateway bindings."
            ),
            gateway_root=str(paths.gateway_root),
        )

    listener = _live_gateway_listener_from_status(paths)
    pid = read_pid_file(paths.pid_path)
    was_running = pid is not None and is_pid_running(pid)
    if was_running and pid is not None:
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError as exc:
            return GatewayControlResult(
                status="error",
                action="gateway_detach",
                detail=f"Failed to terminate gateway process {pid}: {exc}",
                gateway_root=str(paths.gateway_root),
            )
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            if _gateway_process_stopped(pid=pid, listener=listener):
                break
            time.sleep(0.1)
        if not _gateway_process_stopped(pid=pid, listener=listener):
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError as exc:
                return GatewayControlResult(
                    status="error",
                    action="gateway_detach",
                    detail=f"Failed to terminate gateway process {pid}: {exc}",
                    gateway_root=str(paths.gateway_root),
                )
            deadline = time.monotonic() + 1.0
            while time.monotonic() < deadline:
                if _gateway_process_stopped(pid=pid, listener=listener):
                    break
                time.sleep(0.1)
            if not _gateway_process_stopped(pid=pid, listener=listener):
                return GatewayControlResult(
                    status="error",
                    action="gateway_detach",
                    detail=f"Gateway listener did not stop cleanly for process {pid}.",
                    gateway_root=str(paths.gateway_root),
                )

    _clear_stale_gateway_runtime_state(
        controller=controller,
        paths=paths,
        attach_contract=attach_contract,
    )
    controller.gateway_host = None
    controller.gateway_port = None
    return GatewayControlResult(
        status="ok",
        action="gateway_detach",
        detail=(
            "Detached live gateway instance."
            if was_running
            else "Cleared stale or absent live gateway bindings."
        ),
        gateway_root=str(paths.gateway_root),
    )


def _gateway_status_for_controller(controller: RuntimeSessionController) -> GatewayStatusV1:
    """Return gateway status for one runtime controller.

    Parameters
    ----------
    controller:
        Runtime controller whose gateway status is being queried.

    Returns
    -------
    GatewayStatusV1
        Live gateway status when attached, otherwise the persisted offline
        status artifact.
    """

    paths = _require_gateway_paths_for_controller(controller)
    try:
        client = _validated_gateway_client_for_controller(controller, paths=paths, private=True)
    except GatewayNoLiveInstanceError:
        return load_gateway_status(paths.state_path)
    return client.status()


def _submit_gateway_request_for_controller(
    controller: RuntimeSessionController,
    request_payload: GatewayRequestCreateV1,
) -> GatewayAcceptedRequestV1:
    """Submit one gateway-managed request through the live gateway client.

    Parameters
    ----------
    controller:
        Runtime controller owning the live gateway.
    request_payload:
        Validated gateway request payload to submit.

    Returns
    -------
    GatewayAcceptedRequestV1
        Accepted durable queue record returned by the gateway.
    """

    paths = _require_gateway_paths_for_controller(controller)
    client = _validated_gateway_client_for_controller(controller, paths=paths)
    return client.create_request(request_payload)


def _submit_gateway_prompt_control_for_controller(
    controller: RuntimeSessionController,
    request_payload: GatewayPromptControlRequestV1,
) -> GatewayPromptControlResultV1:
    """Submit one direct prompt-control request through the live gateway client."""

    paths = _require_gateway_paths_for_controller(controller)
    client = _validated_gateway_client_for_controller(controller, paths=paths)
    return client.control_prompt(request_payload)


def _validated_gateway_client_for_controller(
    controller: RuntimeSessionController,
    *,
    paths: GatewayPaths,
    private: bool = False,
) -> GatewayClient:
    """Validate live gateway bindings and return a connected client.

    Parameters
    ----------
    controller:
        Runtime controller used for stale-state cleanup if discovery fails.
    paths:
        Gateway filesystem layout for the controller.

    Returns
    -------
    GatewayClient
        Live gateway client validated structurally and via `GET /health`.
    """

    session_name = controller._require_tmux_session_name()
    attach_contract = resolve_internal_gateway_attach_contract(paths)
    try:
        current_instance = load_gateway_current_instance(paths.current_instance_path)
    except SessionManifestError:
        current_instance = None
    if current_instance is not None and current_instance.execution_mode == "tmux_auxiliary_window":
        try:
            live_same_session = _same_session_gateway_is_alive(
                session_name=session_name,
                current_instance=current_instance,
            )
        except TmuxCommandError as exc:
            raise GatewayDiscoveryError(
                f"Failed to inspect same-session gateway tmux pane state: {exc}"
            ) from exc
        if not live_same_session:
            _clear_stale_gateway_runtime_state(
                controller=controller,
                paths=paths,
                attach_contract=attach_contract,
            )
            raise GatewayNoLiveInstanceError(
                f"No live gateway is attached for session `{session_name}`."
            )
    host_value = _read_optional_tmux_session_env_var(
        session_name=session_name,
        variable_name=AGENT_GATEWAY_HOST_ENV_VAR,
    )
    port_value = _read_optional_tmux_session_env_var(
        session_name=session_name,
        variable_name=AGENT_GATEWAY_PORT_ENV_VAR,
    )
    state_path_value = _read_optional_tmux_session_env_var(
        session_name=session_name,
        variable_name=AGENT_GATEWAY_STATE_PATH_ENV_VAR,
    )
    protocol_value = _read_optional_tmux_session_env_var(
        session_name=session_name,
        variable_name=AGENT_GATEWAY_PROTOCOL_VERSION_ENV_VAR,
    )
    if (
        host_value is None
        or port_value is None
        or state_path_value is None
        or protocol_value is None
    ):
        raise GatewayNoLiveInstanceError(
            f"No live gateway is attached for session `{session_name}`."
        )
    if host_value not in {"127.0.0.1", "0.0.0.0"}:
        raise GatewayDiscoveryError(
            f"Invalid `{AGENT_GATEWAY_HOST_ENV_VAR}` value {host_value!r} in tmux session "
            f"`{session_name}`."
        )
    try:
        port = int(port_value)
    except ValueError as exc:
        raise GatewayDiscoveryError(
            f"Invalid `{AGENT_GATEWAY_PORT_ENV_VAR}` value {port_value!r} in tmux session "
            f"`{session_name}`."
        ) from exc
    if port < 1 or port > 65535:
        raise GatewayDiscoveryError(
            f"Invalid `{AGENT_GATEWAY_PORT_ENV_VAR}` value {port!r} in tmux session "
            f"`{session_name}`."
        )
    state_path = Path(state_path_value)
    if not state_path.is_absolute() or state_path.resolve() != paths.state_path:
        raise GatewayDiscoveryError(
            f"Invalid `{AGENT_GATEWAY_STATE_PATH_ENV_VAR}` value {state_path_value!r} in tmux "
            f"session `{session_name}`."
        )
    if protocol_value != GATEWAY_PROTOCOL_VERSION:
        raise GatewayProtocolError(
            f"Unsupported gateway protocol version {protocol_value!r}; expected "
            f"{GATEWAY_PROTOCOL_VERSION!r}."
        )
    endpoint = GatewayEndpoint(
        host=cast(GatewayHost, host_value),
        port=port,
    )
    client = GatewayClient(endpoint=endpoint)
    try:
        health = client.health()
    except GatewayHttpError as exc:
        _clear_stale_gateway_runtime_state(
            controller=controller,
            paths=paths,
            attach_contract=attach_contract,
        )
        raise GatewayNoLiveInstanceError(
            f"No live gateway is attached for session `{session_name}`."
        ) from exc
    if health.protocol_version != GATEWAY_PROTOCOL_VERSION:
        raise GatewayProtocolError(
            f"Gateway health reported incompatible protocol version {health.protocol_version!r}."
        )
    return owner_gateway_client_for_controller(controller, endpoint=endpoint, private=private)


def owner_gateway_client_for_controller(
    controller: RuntimeSessionController,
    *,
    endpoint: GatewayEndpoint,
    private: bool = False,
    prefer_self: bool = False,
) -> GatewayClient:
    """Bind one owner-local HTTP caller to its selected execution and signer."""

    binding, incarnation = owner_gateway_client_binding(
        controller.manifest_path,
        port=endpoint.port,
        private=private,
        prefer_self=prefer_self,
    )
    return GatewayClient(endpoint=endpoint, binding=binding, target_incarnation=incarnation)


def _resolve_gateway_listener(
    *,
    paths: GatewayPaths,
    attach_contract: GatewayAttachContractV1,
    host_override: str | None,
    port_override: int | None,
) -> tuple[GatewayHost, int]:
    """Resolve the listener request for one gateway attach action.

    Parameters
    ----------
    paths:
        Gateway filesystem layout for the controller.
    attach_contract:
        Stable attach contract used to source persisted defaults.
    host_override:
        Optional CLI host override.
    port_override:
        Optional CLI port override.

    Returns
    -------
    tuple[GatewayHost, int]
        Resolved host and requested port. A returned port of `0` delegates
        automatic port assignment to the gateway bind step.

    """

    desired_config = _load_optional_desired_config(paths)
    host_candidate = (
        host_override
        or os.environ.get(AGENT_GATEWAY_HOST_ENV_VAR)
        or (desired_config.desired_host if desired_config is not None else None)
        or attach_contract.desired_host
        or "127.0.0.1"
    )
    if host_candidate not in {"127.0.0.1", "0.0.0.0"}:
        raise GatewayAttachError("Gateway host must resolve to exactly '127.0.0.1' or '0.0.0.0'.")
    env_port = os.environ.get(AGENT_GATEWAY_PORT_ENV_VAR)
    port_candidate: int | None = port_override
    if port_candidate is None and env_port:
        try:
            port_candidate = int(env_port)
        except ValueError as exc:
            raise GatewayAttachError(
                f"Invalid `{AGENT_GATEWAY_PORT_ENV_VAR}` value {env_port!r}."
            ) from exc
    if port_candidate is None and desired_config is not None:
        port_candidate = desired_config.desired_port
    if port_candidate is None:
        port_candidate = attach_contract.desired_port
    if port_candidate is None:
        port_candidate = 0
    if port_candidate < 1 or port_candidate > 65535:
        if port_candidate != 0:
            raise GatewayAttachError("Gateway port must be between 1 and 65535.")
    return cast(GatewayHost, host_candidate), port_candidate


def _resolve_gateway_execution_mode(
    *,
    controller: RuntimeSessionController,
    paths: GatewayPaths,
    execution_mode_override: GatewayCurrentExecutionMode | None,
) -> GatewayCurrentExecutionMode:
    """Resolve the requested gateway execution mode for one attach action."""

    if execution_mode_override is not None:
        return execution_mode_override
    desired_config = _load_optional_desired_config(paths)
    if desired_config is not None:
        return desired_config.desired_execution_mode
    return default_gateway_execution_mode_for_backend(controller.launch_plan.backend)


def _resolve_gateway_tui_tracking_timings(
    *,
    paths: GatewayPaths,
    explicit: GatewayTuiTrackingTimingOverridesV1 | None,
) -> GatewayTuiTrackingTimingConfigV1:
    """Resolve effective gateway-owned TUI tracking timings for one attach action."""

    desired_config = _load_optional_desired_config(paths)
    return resolve_gateway_tui_tracking_timing_config(
        explicit=explicit,
        desired=(
            desired_config.desired_tui_tracking_timings if desired_config is not None else None
        ),
    )


def _find_tmux_pane(
    *,
    session_name: str,
    pane_id: str,
) -> TmuxPaneRecord | None:
    """Return one tmux pane record by id when present."""

    try:
        panes = list_tmux_panes_shared(session_name=session_name)
    except TmuxCommandError:
        if has_tmux_session_shared(session_name=session_name).returncode == 1:
            return None
        raise
    for pane in panes:
        if pane.pane_id == pane_id:
            return pane
    return None


def _same_session_gateway_is_alive(
    *,
    session_name: str,
    current_instance: GatewayCurrentInstanceV1,
) -> bool:
    """Return whether the recorded same-session gateway pane is still alive."""

    if current_instance.execution_mode != "tmux_auxiliary_window":
        return True
    pane_id = current_instance.tmux_pane_id
    if pane_id is None:
        return False
    pane = _find_tmux_pane(session_name=session_name, pane_id=pane_id)
    if pane is None:
        return False
    return not pane.pane_dead


def _stop_same_session_gateway_surface(
    *,
    session_name: str,
    current_instance: GatewayCurrentInstanceV1,
    strict: bool,
) -> bool:
    """Stop one recorded same-session gateway tmux surface."""

    if current_instance.execution_mode != "tmux_auxiliary_window":
        return False
    window_id = current_instance.tmux_window_id
    window_index = current_instance.tmux_window_index
    pane_id = current_instance.tmux_pane_id
    if window_id is None or pane_id is None:
        return False
    if window_index == _PRIMARY_AGENT_WINDOW_INDEX:
        if strict:
            raise GatewayAttachError("Refusing to stop the reserved agent window `0`.")
        return False
    try:
        result = run_tmux_shared(["kill-window", "-t", window_id])
    except TmuxCommandError as exc:
        if strict:
            raise GatewayAttachError(
                f"Failed to stop gateway tmux window `{window_id}`: {exc}"
            ) from exc
        return False
    if result.returncode != 0:
        detail = tmux_error_detail_shared(result).lower()
        if (
            "can't find window" in detail
            or "can't find pane" in detail
            or "can't find session" in detail
            or "no server running" in detail
        ):
            return False
        if strict:
            raise GatewayAttachError(
                f"Failed to stop gateway tmux window `{window_id}`: "
                f"{tmux_error_detail_shared(result) or 'unknown tmux error'}"
            )
        return False

    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        if _find_tmux_pane(session_name=session_name, pane_id=pane_id) is None:
            return True
        time.sleep(0.1)
    if strict:
        raise GatewayAttachError(
            f"Timed out waiting for gateway tmux pane `{pane_id}` to stop after killing "
            f"window `{window_id}`."
        )
    return False


def _same_session_gateway_shell_command(
    *,
    paths: GatewayPaths,
    host: GatewayHost,
    port: int,
    tui_tracking_timings: GatewayTuiTrackingTimingConfigV1 | None,
) -> str:
    """Return the shell command used to launch a gateway in an auxiliary tmux window."""

    gateway_module = "houmao.agents.realm_controller.gateway_service"
    exports = (
        f"export {_GATEWAY_EXECUTION_MODE_ENV_VAR}=tmux_auxiliary_window; "
        f'export {_GATEWAY_TMUX_PANE_ID_ENV_VAR}="$TMUX_PANE"; '
        f'export {_GATEWAY_TMUX_WINDOW_ID_ENV_VAR}="$(tmux display-message -p -t '
        f'"$TMUX_PANE" \'#{{window_id}}\')"; '
        f'export {_GATEWAY_TMUX_WINDOW_INDEX_ENV_VAR}="$(tmux display-message -p -t '
        f'"$TMUX_PANE" \'#{{window_index}}\')"; '
        "export PYTHONUNBUFFERED=1; "
        "set -o pipefail; "
    )
    gateway_command = " ".join(
        shlex.quote(value)
        for value in (
            sys.executable,
            "-m",
            gateway_module,
            "--gateway-root",
            str(paths.gateway_root),
            "--host",
            host,
            "--port",
            str(port),
            *(
                _gateway_tui_tracking_timing_cli_args(tui_tracking_timings)
                if tui_tracking_timings is not None
                else ()
            ),
        )
    )
    log_target = shlex.quote(str(paths.log_path))
    return f"{exports}{gateway_command} 2>&1 | tee -a {log_target}; exit ${{PIPESTATUS[0]}}"


def _gateway_tui_tracking_timing_cli_args(
    timings: GatewayTuiTrackingTimingConfigV1,
) -> tuple[str, ...]:
    """Return internal gateway-service CLI args for resolved TUI tracking timings."""

    return (
        "--tui-watch-poll-interval-seconds",
        str(timings.watch_poll_interval_seconds),
        "--tui-stability-threshold-seconds",
        str(timings.stability_threshold_seconds),
        "--tui-completion-stability-seconds",
        str(timings.completion_stability_seconds),
        "--tui-unknown-to-stalled-timeout-seconds",
        str(timings.unknown_to_stalled_timeout_seconds),
        "--tui-stale-active-recovery-seconds",
        str(timings.stale_active_recovery_seconds),
        "--tui-final-stable-active-recovery-seconds",
        str(timings.final_stable_active_recovery_seconds),
    )


def _launch_same_session_gateway_window(
    *,
    controller: RuntimeSessionController,
    session_name: str,
    paths: GatewayPaths,
    host: GatewayHost,
    port: int,
    tui_tracking_timings: GatewayTuiTrackingTimingConfigV1,
) -> _TmuxAuxiliaryWindowHandle:
    """Launch one same-session gateway window and return its tmux execution handle."""

    command = _same_session_gateway_shell_command(
        paths=paths,
        host=host,
        port=port,
        tui_tracking_timings=(
            None
            if mode_for_backend(controller.launch_plan.backend) == "web"
            else tui_tracking_timings
        ),
    )
    try:
        result = run_tmux_shared(
            [
                "new-window",
                "-d",
                "-P",
                "-F",
                "#{window_id}\t#{window_index}\t#{pane_id}",
                "-t",
                session_name,
                "-n",
                _GATEWAY_AUXILIARY_WINDOW_NAME,
                "-c",
                str(controller.launch_plan.working_directory),
                "bash",
                "-lc",
                command,
            ]
        )
    except TmuxCommandError as exc:
        raise GatewayAttachError(f"Failed to create gateway tmux window: {exc}") from exc
    if result.returncode != 0:
        raise GatewayAttachError(
            "Failed to create gateway tmux window: "
            f"{tmux_error_detail_shared(result) or 'unknown tmux error'}"
        )
    parts = (result.stdout or "").strip().split("\t")
    if len(parts) != 3:
        raise GatewayAttachError(
            f"Unexpected tmux new-window output while launching gateway: {result.stdout!r}"
        )
    handle = _TmuxAuxiliaryWindowHandle(
        window_id=parts[0],
        window_index=parts[1],
        pane_id=parts[2],
    )
    if handle.window_index == _PRIMARY_AGENT_WINDOW_INDEX:
        raise GatewayAttachError("Gateway auxiliary window unexpectedly used reserved window `0`.")
    return handle


def _wait_for_same_session_gateway_endpoint(
    *,
    session_name: str,
    handle: _TmuxAuxiliaryWindowHandle,
    paths: GatewayPaths,
    host: GatewayHost,
    requested_port: int,
    deadline: float,
) -> GatewayEndpoint:
    """Wait until the tmux-hosted gateway publishes its live execution state."""

    observed_pane = False
    while time.monotonic() < deadline:
        pane = _find_tmux_pane(session_name=session_name, pane_id=handle.pane_id)
        if pane is None:
            if observed_pane:
                raise GatewayAttachError(
                    _gateway_process_start_failure_detail(
                        log_path=paths.log_path,
                        host=host,
                        port=requested_port,
                    )
                )
        elif pane.pane_dead:
            raise GatewayAttachError(
                _gateway_process_start_failure_detail(
                    log_path=paths.log_path,
                    host=host,
                    port=requested_port,
                )
            )
        else:
            observed_pane = True
        try:
            current_instance = load_gateway_current_instance(paths.current_instance_path)
        except SessionManifestError:
            time.sleep(0.1)
            continue
        if current_instance.execution_mode != "tmux_auxiliary_window":
            time.sleep(0.1)
            continue
        if current_instance.tmux_window_id != handle.window_id:
            time.sleep(0.1)
            continue
        if current_instance.tmux_window_index != handle.window_index:
            time.sleep(0.1)
            continue
        if current_instance.tmux_pane_id != handle.pane_id:
            time.sleep(0.1)
            continue
        if requested_port not in {0, current_instance.port}:
            raise GatewayAttachError(
                "Gateway startup published a listener port that does not match the "
                f"requested port {requested_port}."
            )
        return GatewayEndpoint(host=host, port=current_instance.port)
    if requested_port == 0:
        raise GatewayAttachError("Timed out waiting for gateway startup to publish its bound port.")
    raise GatewayAttachError(
        f"Timed out waiting for gateway startup to publish listener {host}:{requested_port}."
    )


def _start_gateway_process(
    *,
    controller: RuntimeSessionController,
    paths: GatewayPaths,
    host: GatewayHost,
    port: int,
    execution_mode: GatewayCurrentExecutionMode,
    tui_tracking_timings: GatewayTuiTrackingTimingConfigV1,
) -> int:
    """Launch the gateway subprocess and wait for health readiness.

    Parameters
    ----------
    controller:
        Runtime controller owning the gateway.
    paths:
        Gateway filesystem layout for the controller.
    host:
        Requested listener host.
    port:
        Requested listener port. A value of `0` delegates port assignment to
        the gateway bind step.
    execution_mode:
        Execution mode requested for the live gateway instance.
    tui_tracking_timings:
        Resolved TUI tracking timings for the gateway-owned tracker.

    Returns
    -------
    int
        Resolved live gateway port published by the child process.
    """

    session_name = controller._require_tmux_session_name()
    if execution_mode == "tmux_auxiliary_window":
        try:
            current_instance = load_gateway_current_instance(paths.current_instance_path)
        except SessionManifestError:
            current_instance = None
        if current_instance is not None:
            _stop_same_session_gateway_surface(
                session_name=session_name,
                current_instance=current_instance,
                strict=False,
            )
        handle = _launch_same_session_gateway_window(
            controller=controller,
            session_name=session_name,
            paths=paths,
            host=host,
            port=port,
            tui_tracking_timings=tui_tracking_timings,
        )
        deadline = time.monotonic() + 10.0
        observed_pane = False
        try:
            endpoint = _wait_for_same_session_gateway_endpoint(
                session_name=session_name,
                handle=handle,
                paths=paths,
                host=host,
                requested_port=port,
                deadline=deadline,
            )
            client = GatewayClient(endpoint=endpoint)
            same_session_last_health_error: GatewayHttpError | None = None
            while time.monotonic() < deadline:
                pane = _find_tmux_pane(session_name=session_name, pane_id=handle.pane_id)
                if pane is None:
                    if observed_pane:
                        raise GatewayAttachError(
                            _gateway_process_start_failure_detail(
                                log_path=paths.log_path,
                                host=host,
                                port=port,
                            )
                        )
                elif pane.pane_dead:
                    raise GatewayAttachError(
                        _gateway_process_start_failure_detail(
                            log_path=paths.log_path,
                            host=host,
                            port=port,
                        )
                    )
                else:
                    observed_pane = True
                try:
                    health = client.health()
                except GatewayHttpError as exc:
                    same_session_last_health_error = exc
                    time.sleep(0.1)
                    continue
                if health.protocol_version != GATEWAY_PROTOCOL_VERSION:
                    raise GatewayProtocolError(
                        f"Gateway health returned incompatible protocol version "
                        f"{health.protocol_version!r}."
                    )
                write_gateway_desired_config(
                    paths.desired_config_path,
                    GatewayDesiredConfigV1(
                        desired_host=host,
                        desired_port=endpoint.port,
                        desired_execution_mode=execution_mode,
                        desired_tui_tracking_timings=tui_tracking_timings,
                        desired_diagnostic_logging=_load_desired_diagnostic_logging(paths),
                        desired_plugins=_load_desired_plugins(paths),
                    ),
                )
                refresh_internal_gateway_publication(paths)
                publish_live_gateway_env(
                    session_name=session_name,
                    live_bindings=build_live_gateway_bindings(
                        host=host,
                        port=endpoint.port,
                        state_path=paths.state_path,
                    ),
                    set_env=set_tmux_session_environment_shared,
                )
                return endpoint.port
            raise GatewayAttachError(
                _gateway_health_readiness_timeout_detail(
                    host=host,
                    port=endpoint.port,
                    last_error=same_session_last_health_error,
                )
            )
        except Exception:
            try:
                _stop_same_session_gateway_surface(
                    session_name=session_name,
                    current_instance=load_gateway_current_instance(paths.current_instance_path),
                    strict=False,
                )
            except SessionManifestError:
                pass
            raise

    log_stream = paths.log_path.open("a", encoding="utf-8")
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "houmao.agents.realm_controller.gateway_service",
            "--gateway-root",
            str(paths.gateway_root),
            "--host",
            host,
            "--port",
            str(port),
            *(
                _gateway_tui_tracking_timing_cli_args(tui_tracking_timings)
                if mode_for_backend(controller.launch_plan.backend) != "web"
                else ()
            ),
        ],
        stdout=log_stream,
        stderr=subprocess.STDOUT,
        cwd=str(controller.launch_plan.working_directory),
        start_new_session=True,
        text=True,
    )
    log_stream.close()
    deadline = time.monotonic() + 10.0
    try:
        endpoint = _wait_for_gateway_endpoint(
            process=process,
            paths=paths,
            host=host,
            requested_port=port,
            deadline=deadline,
        )
        client = GatewayClient(endpoint=endpoint)
        detached_last_health_error: GatewayHttpError | None = None
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise GatewayAttachError(
                    _gateway_process_start_failure_detail(
                        log_path=paths.log_path,
                        host=host,
                        port=port,
                    )
                )
            try:
                health = client.health()
            except GatewayHttpError as exc:
                detached_last_health_error = exc
                time.sleep(0.1)
                continue
            if health.protocol_version != GATEWAY_PROTOCOL_VERSION:
                raise GatewayProtocolError(
                    f"Gateway health returned incompatible protocol version "
                    f"{health.protocol_version!r}."
                )
            write_gateway_desired_config(
                paths.desired_config_path,
                GatewayDesiredConfigV1(
                    desired_host=host,
                    desired_port=endpoint.port,
                    desired_execution_mode=execution_mode,
                    desired_tui_tracking_timings=tui_tracking_timings,
                    desired_diagnostic_logging=_load_desired_diagnostic_logging(paths),
                    desired_plugins=_load_desired_plugins(paths),
                ),
            )
            refresh_internal_gateway_publication(paths)
            publish_live_gateway_env(
                session_name=session_name,
                live_bindings=build_live_gateway_bindings(
                    host=host,
                    port=endpoint.port,
                    state_path=paths.state_path,
                ),
                set_env=set_tmux_session_environment_shared,
            )
            return endpoint.port
        raise GatewayAttachError(
            _gateway_health_readiness_timeout_detail(
                host=host,
                port=endpoint.port,
                last_error=detached_last_health_error,
            )
        )
    except Exception:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=2.0)
        raise


def _wait_for_gateway_endpoint(
    *,
    process: subprocess.Popen[str],
    paths: GatewayPaths,
    host: GatewayHost,
    requested_port: int,
    deadline: float,
) -> GatewayEndpoint:
    """Wait until the child gateway process publishes its bound listener.

    Parameters
    ----------
    process:
        Gateway subprocess started by the runtime.
    paths:
        Gateway filesystem layout for the controller.
    host:
        Requested listener host.
    requested_port:
        Requested listener port, or `0` for system-assigned port selection.
    deadline:
        Absolute monotonic deadline for endpoint publication.

    Returns
    -------
    GatewayEndpoint
        Published gateway endpoint for the child process.
    """

    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise GatewayAttachError(
                _gateway_process_start_failure_detail(
                    log_path=paths.log_path,
                    host=host,
                    port=requested_port,
                )
            )
        try:
            current_instance = load_gateway_current_instance(paths.current_instance_path)
        except SessionManifestError:
            time.sleep(0.1)
            continue
        if current_instance.pid != process.pid:
            time.sleep(0.1)
            continue
        if requested_port not in {0, current_instance.port}:
            raise GatewayAttachError(
                "Gateway startup published a listener port that does not match the "
                f"requested port {requested_port}."
            )
        return GatewayEndpoint(
            host=host,
            port=current_instance.port,
        )
    if requested_port == 0:
        raise GatewayAttachError("Timed out waiting for gateway startup to publish its bound port.")
    raise GatewayAttachError(
        f"Timed out waiting for gateway startup to publish listener {host}:{requested_port}."
    )


def _clear_stale_gateway_runtime_state(
    *,
    controller: RuntimeSessionController,
    paths: GatewayPaths,
    attach_contract: GatewayAttachContractV1,
) -> None:
    """Clear live bindings and restore offline seeded gateway state.

    Parameters
    ----------
    controller:
        Runtime controller whose live bindings should be cleared.
    paths:
        Gateway filesystem layout for the controller.
    attach_contract:
        Stable attach contract used to rebuild offline status.
    """

    session_name = _tmux_session_name_for_controller(controller)
    if session_name is not None:
        try:
            unset_tmux_session_environment_shared(
                session_name=session_name,
                variable_names=list(live_gateway_env_var_names()),
            )
        except TmuxCommandError:
            pass
        try:
            current_instance = load_gateway_current_instance(paths.current_instance_path)
        except SessionManifestError:
            current_instance = None
        if current_instance is not None:
            _stop_same_session_gateway_surface(
                session_name=session_name,
                current_instance=current_instance,
                strict=False,
            )
    delete_gateway_current_instance(paths)
    existing_epoch = 0
    try:
        existing_status = load_gateway_status(paths.state_path)
    except SessionManifestError:
        existing_status = None
    desired_config = _load_optional_desired_config(paths)
    if existing_status is not None:
        existing_epoch = existing_status.managed_agent_instance_epoch
    write_gateway_status(
        paths.state_path,
        build_offline_gateway_status(
            attach_contract=attach_contract,
            managed_agent_instance_epoch=existing_epoch,
            desired_config=desired_config,
        ),
    )
    refresh_gateway_manifest_publication(paths)


def _load_optional_desired_config(paths: GatewayPaths) -> GatewayDesiredConfigV1 | None:
    """Load desired gateway listener config when present.

    Parameters
    ----------
    paths:
        Gateway filesystem layout to inspect.

    Returns
    -------
    GatewayDesiredConfigV1 | None
        Persisted desired listener configuration, if it exists.
    """

    if not paths.desired_config_path.is_file():
        return None
    return load_gateway_desired_config(paths.desired_config_path)


def _load_desired_diagnostic_logging(
    paths: GatewayPaths,
) -> GatewayDiagnosticLoggingConfigV1 | None:
    """Load persisted gateway diagnostic logging config when present."""

    desired_config = _load_optional_desired_config(paths)
    if desired_config is None:
        return None
    return desired_config.desired_diagnostic_logging


def _load_desired_plugins(paths: GatewayPaths) -> GatewayPluginConfiguration | None:
    """Read persisted selections without resolving implementations or credentials."""

    desired_config = _load_optional_desired_config(paths)
    return desired_config.desired_plugins if desired_config is not None else None


def _live_gateway_for_plugin_attach(
    *, controller: RuntimeSessionController, paths: GatewayPaths
) -> GatewayCurrentInstanceV1 | None:
    """Find an existing process before considering a plugin selection change."""

    try:
        current = load_gateway_current_instance(paths.current_instance_path)
    except SessionManifestError:
        return None
    if not is_pid_running(current.pid):
        return None
    if not _same_session_gateway_is_alive(
        session_name=controller._require_tmux_session_name(), current_instance=current
    ):
        return None
    return current


def _gateway_process_start_failure_detail(*, log_path: Path, host: GatewayHost, port: int) -> str:
    """Return a user-facing startup failure detail for an exited gateway process.

    Parameters
    ----------
    log_path:
        Gateway log path written by the child process.
    host:
        Requested listener host.
    port:
        Requested listener port.

    Returns
    -------
    str
        Operator-facing failure detail.
    """

    try:
        log_text = log_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        log_text = ""
    lowered = log_text.lower()
    if "address already in use" in lowered or "errno 98" in lowered:
        return f"Gateway attach failed because listener {host}:{port} is already in use."
    return f"Gateway attach failed before health readiness; see `{log_path}`."


def _gateway_health_readiness_timeout_detail(
    *,
    host: GatewayHost,
    port: int,
    last_error: GatewayHttpError | None,
) -> str:
    """Return an attach-timeout detail with the last observed health probe error."""

    detail = f"Timed out waiting for gateway health readiness on {host}:{port}."
    if last_error is not None:
        detail = f"{detail} Last health probe error: {last_error.detail}"
    return detail


def _live_gateway_listener_from_status(paths: GatewayPaths) -> tuple[GatewayHost, int] | None:
    """Return the last live gateway listener from persisted status.

    Parameters
    ----------
    paths:
        Gateway filesystem layout to inspect.

    Returns
    -------
    tuple[GatewayHost, int] | None
        Last published live listener, if the status snapshot still contains one.
    """

    try:
        status = load_gateway_status(paths.state_path)
    except SessionManifestError:
        return None
    if status.gateway_host is None or status.gateway_port is None:
        return None
    return status.gateway_host, status.gateway_port


def _gateway_process_stopped(
    *,
    pid: int,
    listener: tuple[GatewayHost, int] | None,
) -> bool:
    """Return whether a gateway process has stopped serving its listener.

    Parameters
    ----------
    pid:
        Gateway process identifier.
    listener:
        Last known live gateway listener, if available.

    Returns
    -------
    bool
        `True` when the process is gone or the listener can be rebound locally.
    """

    if listener is not None:
        return _gateway_listener_available_for_bind(
            host=listener[0],
            port=listener[1],
        )
    return not is_pid_running(pid)


def _gateway_listener_available_for_bind(*, host: GatewayHost, port: int) -> bool:
    """Return whether the addressed gateway listener can be rebound locally.

    Parameters
    ----------
    host:
        Listener host to probe.
    port:
        Listener port to probe.

    Returns
    -------
    bool
        `True` when a local bind succeeds for the requested listener.
    """

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def _read_optional_tmux_session_env_var(*, session_name: str, variable_name: str) -> str | None:
    """Read one tmux env var and return `None` when it is unset or unknown.

    Parameters
    ----------
    session_name:
        Tmux session name to inspect.
    variable_name:
        Environment variable name to read.

    Returns
    -------
    str | None
        Published value when present, otherwise `None`.
    """

    try:
        env_result = show_tmux_environment_shared(
            session_name=session_name,
            variable_name=variable_name,
        )
    except TmuxCommandError:
        return None

    if env_result.returncode != 0:
        detail = tmux_error_detail_shared(env_result).lower()
        if "unknown variable" in detail:
            return None
        return None

    line = ""
    for raw_line in env_result.stdout.splitlines():
        stripped = raw_line.strip()
        if stripped:
            line = stripped
            break
    if not line or line == f"-{variable_name}":
        return None
    prefix = f"{variable_name}="
    if not line.startswith(prefix):
        return None
    value = line[len(prefix) :].strip()
    return value or None
