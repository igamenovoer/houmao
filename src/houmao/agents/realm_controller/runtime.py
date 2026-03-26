"""High-level session runtime orchestration."""

from __future__ import annotations

import logging
import os
import shlex
import signal
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable, cast

from houmao.owned_paths import (
    AGENTSYS_JOB_DIR_ENV_VAR,
    resolve_runtime_root,
    resolve_session_job_dir,
)
from .agent_identity import (
    AGENT_NAMESPACE_PREFIX,
    AGENT_DEF_DIR_ENV_VAR,
    AGENT_ID_ENV_VAR,
    AGENT_MANIFEST_PATH_ENV_VAR,
    derive_auto_agent_name_base,
    derive_agent_id_from_name,
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
from .backends.houmao_server_rest import HoumaoServerRestSession
from .boundary_models import (
    RegistryLaunchAuthorityV1,
    SessionManifestAgentLaunchAuthorityV1,
    SessionManifestPayloadV3,
    SessionManifestPayloadV4,
)
from .backends.claude_headless import ClaudeHeadlessSession
from .backends.codex_headless import CodexHeadlessSession
from .backends.codex_app_server import (
    CodexAppServerSession,
    codex_backend_state_payload,
)
from .backends.gemini_headless import GeminiHeadlessSession
from .backends.headless_base import (
    HeadlessInteractiveSession,
    HeadlessSessionState,
    headless_backend_state_payload,
)
from .backends.local_interactive import LocalInteractiveSession
from .backends.tmux_runtime import (
    TmuxCommandError,
    TmuxPaneRecord,
    has_tmux_session as has_tmux_session_shared,
    list_tmux_panes as list_tmux_panes_shared,
    list_tmux_sessions as list_tmux_sessions_shared,
    read_tmux_session_environment_value as read_tmux_session_environment_value_shared,
    run_tmux as run_tmux_shared,
    set_tmux_session_environment as set_tmux_session_environment_shared,
    show_tmux_environment as show_tmux_environment_shared,
    tmux_error_detail as tmux_error_detail_shared,
    unset_tmux_session_environment as unset_tmux_session_environment_shared,
)
from .errors import (
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
from .gateway_models import (
    GATEWAY_PROTOCOL_VERSION,
    BlueprintGatewayDefaults,
    GatewayAcceptedRequestV1,
    GatewayAttachContractV1,
    GatewayCurrentExecutionMode,
    GatewayCurrentInstanceV1,
    GatewayDesiredConfigV1,
    GatewayHost,
    GatewayJsonObject,
    GatewayRequestCreateV1,
    GatewayRequestPayloadInterruptV1,
    GatewayRequestPayloadSubmitPromptV1,
    GatewayStatusV1,
    default_gateway_execution_mode_for_backend,
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
from .launch_plan import (
    LaunchPlanRequest,
    backend_for_tool,
    build_launch_plan,
    configured_cao_parsing_mode,
    resolve_cao_parsing_mode,
)
from .loaders import RolePackage, load_brain_manifest, load_role_package
from .mail_commands import MailPromptRequest
from houmao.agents.mailbox_runtime_support import (
    bootstrap_resolved_mailbox,
    mailbox_env_bindings,
    parse_declarative_mailbox_config,
    refresh_filesystem_mailbox_config,
    resolve_effective_mailbox_config,
    resolved_mailbox_config_from_payload,
)
from houmao.agents.mailbox_runtime_models import (
    FilesystemMailboxResolvedConfig,
    MailboxDeclarativeConfig,
    MailboxResolvedConfig,
    StalwartMailboxResolvedConfig,
)
from .manifest import (
    SessionManifestRequest,
    build_session_manifest_payload,
    default_manifest_path,
    generate_session_id,
    load_session_manifest,
    parse_session_manifest_payload,
    runtime_owned_session_root_from_manifest_path,
    write_session_manifest,
)
from .models import (
    BackendKind,
    CaoParsingMode,
    GatewayControlResult,
    InteractiveSession,
    LaunchPlan,
    RoleInjectionPlan,
    SessionControlResult,
    SessionEvent,
)
from .registry_models import (
    LiveAgentRegistryRecordV2,
    RegistryGatewayV1,
    RegistryIdentityV1,
    RegistryMailboxFilesystemV1,
    RegistryMailboxStalwartV1,
    RegistryMailboxV1,
    RegistryRuntimeV1,
    RegistryTerminalV1,
    canonicalize_registry_agent_name,
)
from .registry_storage import (
    DEFAULT_REGISTRY_LEASE_TTL,
    JOINED_REGISTRY_SENTINEL_LEASE_TTL,
    new_registry_generation_id,
    publish_live_agent_record,
    remove_live_agent_record,
    resolve_live_agent_record_by_agent_id,
    resolve_live_agent_records_by_name,
)
from houmao.server.client import HoumaoServerClient
from houmao.server.models import HoumaoRegisterLaunchRequest

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
# Keep this narrow allowlist aligned with `_build_gateway_execution_adapter()`.
_GATEWAY_ATTACH_SUPPORTED_BACKENDS: tuple[BackendKind, ...] = (
    "local_interactive",
    "codex_headless",
    "claude_headless",
    "gemini_headless",
    "cao_rest",
    "houmao_server_rest",
)
_PRIMARY_AGENT_WINDOW_INDEX = "0"
_GATEWAY_AUXILIARY_WINDOW_NAME = "gateway"
_GATEWAY_EXECUTION_MODE_ENV_VAR = "AGENTSYS_GATEWAY_EXECUTION_MODE"
_GATEWAY_TMUX_WINDOW_ID_ENV_VAR = "AGENTSYS_GATEWAY_TMUX_WINDOW_ID"
_GATEWAY_TMUX_WINDOW_INDEX_ENV_VAR = "AGENTSYS_GATEWAY_TMUX_WINDOW_INDEX"
_GATEWAY_TMUX_PANE_ID_ENV_VAR = "AGENTSYS_GATEWAY_TMUX_PANE_ID"
_BRAIN_ONLY_ROLE_NAME = "brain-only"
_JOINED_SESSION_ORIGIN = "joined_tmux"
_LOGGER = logging.getLogger(__name__)


class _TmuxLocalDiscoveryUnavailableError(SessionManifestError):
    """Raised when tmux-local discovery pointers are unavailable for fallback."""


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
        Effective agent-definition root for name-based tmux resolution.
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
    job_dir: Path | None = None
    agent_identity_warnings: tuple[str, ...] = ()
    startup_warnings: tuple[str, ...] = ()
    parsing_mode: CaoParsingMode | None = None
    gateway_root: Path | None = None
    gateway_attach_path: Path | None = None
    gateway_auto_attach_error: str | None = None
    gateway_host: str | None = None
    gateway_port: int | None = None
    registry_generation_id: str | None = None
    registry_launch_authority: RegistryLaunchAuthorityV1 = "runtime"
    agent_launch_authority: SessionManifestAgentLaunchAuthorityV1 | None = None
    operation_warnings: tuple[str, ...] = ()

    def send_prompt(self, prompt: str) -> list[SessionEvent]:
        """Send a prompt and persist updated session state."""

        self._reset_operation_warnings()
        events = self.backend_session.send_prompt(prompt)
        self.persist_manifest()
        return events

    def send_mail_prompt(self, prompt_request: MailPromptRequest) -> list[SessionEvent]:
        """Send one runtime-owned mailbox prompt and persist updated session state."""

        self._reset_operation_warnings()
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

    def interrupt(self) -> SessionControlResult:
        """Interrupt in-flight backend work and persist state."""

        self._reset_operation_warnings()
        result = self.backend_session.interrupt()
        self.persist_manifest()
        return result

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

    def stop(self, *, force_cleanup: bool = False) -> SessionControlResult:
        """Terminate backend resources and persist state."""

        self._reset_operation_warnings()
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
        if isinstance(self.backend_session, HeadlessInteractiveSession):
            self.backend_session.configure_stop_force_cleanup(force_cleanup=force_cleanup)
        result = self.backend_session.terminate()
        if result.status == "ok":
            self.persist_manifest(refresh_registry=False)
            try:
                self.clear_shared_registry_record()
            except (OSError, SessionManifestError) as exc:
                self._record_registry_warning(
                    "Shared-registry cleanup failed after successful stop-session teardown",
                    exc,
                )
        else:
            self.persist_manifest()
        return result

    def close(self) -> None:
        """Close the backend session."""

        self._reset_operation_warnings()
        self.backend_session.close()
        self.persist_manifest()

    def refresh_mailbox_bindings(
        self,
        *,
        filesystem_root: Path | None = None,
    ) -> MailboxResolvedConfig:
        """Refresh mailbox env bindings for an active session."""

        self._reset_operation_warnings()
        mailbox = self.launch_plan.mailbox
        if mailbox is None:
            raise SessionManifestError("Session does not have mailbox support enabled.")
        if not isinstance(mailbox, FilesystemMailboxResolvedConfig):
            raise SessionManifestError(
                f"Mailbox binding refresh is not implemented for transport={mailbox.transport!r}."
            )

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

        updated_launch_plan = _launch_plan_with_mailbox(
            self.launch_plan,
            refreshed,
        )
        _refresh_backend_launch_plan(
            backend_session=self.backend_session,
            launch_plan=updated_launch_plan,
        )
        self.launch_plan = updated_launch_plan
        self.persist_manifest()
        return refreshed

    def relaunch(self) -> SessionControlResult:
        """Relaunch the tmux-backed managed-agent surface without rebuilding the home."""

        self._reset_operation_warnings()
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

        result = _relaunch_backend_session(self)
        if result.status != "ok":
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

        self.persist_manifest()
        return result

    def persist_manifest(self, *, refresh_registry: bool = True) -> None:
        """Persist current backend state to session manifest."""

        backend_state = _backend_state_for_session(self.backend_session)
        self.tmux_session_name = _tmux_session_name_for_controller(self)
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
                job_dir=self.job_dir,
                agent_def_dir=self.agent_def_dir,
                registry_generation_id=self.registry_generation_id,
                registry_launch_authority=self.registry_launch_authority,
                agent_launch_authority=self.agent_launch_authority,
            )
        )
        payload = _preserve_server_managed_headless_gateway_authority(
            manifest_path=self.manifest_path,
            backend=self.launch_plan.backend,
            payload=payload,
        )
        write_session_manifest(self.manifest_path, payload)
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

    def ensure_gateway_capability(
        self,
        *,
        blueprint_gateway_defaults: BlueprintGatewayDefaults | None = None,
    ) -> None:
        """Publish stable gateway capability for runtime-owned tmux-backed sessions."""

        if not self._is_tmux_backed():
            return
        self.persist_manifest(refresh_registry=False)
        session_name = _tmux_session_name_for_controller(self)
        if session_name is None:
            return
        session_id = _runtime_session_id_from_manifest_path(self.manifest_path)
        if session_id is None:
            return
        paths = ensure_gateway_capability(
            GatewayCapabilityPublication(
                manifest_path=self.manifest_path,
                backend=self.launch_plan.backend,
                tool=self.launch_plan.tool,
                session_id=session_id,
                tmux_session_name=session_name,
                working_directory=self.launch_plan.working_directory,
                backend_state=_backend_state_for_session(self.backend_session),
                agent_def_dir=_runtime_agent_def_dir(self),
                blueprint_gateway_defaults=blueprint_gateway_defaults,
            )
        )
        stable_discovery_env = {
            AGENT_MANIFEST_PATH_ENV_VAR: str(self.manifest_path.resolve()),
        }
        if self.agent_id is not None:
            stable_discovery_env[AGENT_ID_ENV_VAR] = self.agent_id
        set_tmux_session_environment_shared(
            session_name=session_name,
            env_vars=stable_discovery_env,
        )
        if has_tmux_session_shared(session_name=session_name).returncode == 0:
            try:
                unset_tmux_session_environment_shared(
                    session_name=session_name,
                    variable_names=[
                        AGENT_GATEWAY_ATTACH_PATH_ENV_VAR,
                        AGENT_GATEWAY_ROOT_ENV_VAR,
                    ],
                )
            except TmuxCommandError:
                pass
        self.gateway_root = paths.gateway_root
        self.gateway_attach_path = paths.attach_path
        self.refresh_shared_registry_record()

    def attach_gateway(
        self,
        *,
        host_override: str | None = None,
        port_override: int | None = None,
        execution_mode_override: GatewayCurrentExecutionMode | None = None,
    ) -> GatewayControlResult:
        """Start a live gateway instance for the addressed session."""

        result = _attach_gateway_for_controller(
            self,
            host_override=host_override,
            port_override=port_override,
            execution_mode_override=execution_mode_override,
        )
        if result.status == "ok":
            self.refresh_shared_registry_record()
        return result

    def detach_gateway(self) -> GatewayControlResult:
        """Stop a live gateway instance while preserving attachability metadata."""

        result = _detach_gateway_for_controller(self)
        if result.status == "ok":
            self.refresh_shared_registry_record()
        return result

    def gateway_status(self) -> GatewayStatusV1:
        """Return current gateway status from the live gateway or stable state file."""

        return _gateway_status_for_controller(self)

    def send_prompt_via_gateway(self, prompt: str) -> GatewayAcceptedRequestV1:
        """Submit a prompt through the live gateway queue."""

        return _submit_gateway_request_for_controller(
            self,
            GatewayRequestCreateV1(
                kind="submit_prompt",
                payload=GatewayRequestPayloadSubmitPromptV1(prompt=prompt),
            ),
        )

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

    def refresh_shared_registry_record(self) -> LiveAgentRegistryRecordV2 | None:
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
        return publish_live_agent_record(record)

    def should_publish_shared_registry_record(self) -> bool:
        """Return whether runtime is the launch authority for registry publication."""

        return self.registry_launch_authority == "runtime"

    def build_shared_registry_record(self) -> LiveAgentRegistryRecordV2 | None:
        """Build the current pointer-oriented shared-registry record for this session."""

        return _build_shared_registry_record_for_controller(self)

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


def start_runtime_session(
    *,
    agent_def_dir: Path,
    brain_manifest_path: Path,
    role_name: str | None,
    runtime_root: Path | None = None,
    backend: BackendKind | None = None,
    working_directory: Path | None = None,
    api_base_url: str = "http://localhost:9889",
    cao_profile_store_dir: Path | None = None,
    agent_identity: str | None = None,
    agent_name: str | None = None,
    agent_id: str | None = None,
    cao_parsing_mode: CaoParsingMode | None = None,
    mailbox_transport: str | None = None,
    mailbox_root: Path | None = None,
    mailbox_principal_id: str | None = None,
    mailbox_address: str | None = None,
    mailbox_stalwart_base_url: str | None = None,
    mailbox_stalwart_jmap_url: str | None = None,
    mailbox_stalwart_management_url: str | None = None,
    mailbox_stalwart_login_identity: str | None = None,
    blueprint_gateway_defaults: BlueprintGatewayDefaults | None = None,
    gateway_auto_attach: bool = False,
    gateway_host: str | None = None,
    gateway_port: int | None = None,
    tmux_session_name: str | None = None,
    registry_launch_authority: RegistryLaunchAuthorityV1 = "runtime",
) -> RuntimeSessionController:
    """Start a new runtime session and persist its session manifest."""

    if (gateway_host is not None or gateway_port is not None) and not gateway_auto_attach:
        raise SessionManifestError(
            "Gateway host or port overrides require launch-time gateway attach."
        )

    manifest = load_brain_manifest(brain_manifest_path)
    resolved_role_name = role_name.strip() if role_name is not None and role_name.strip() else None
    if resolved_role_name is None:
        role_package = RolePackage(
            role_name=_BRAIN_ONLY_ROLE_NAME,
            system_prompt="",
            path=(agent_def_dir / "roles" / _BRAIN_ONLY_ROLE_NAME / "system-prompt.md").resolve(),
        )
    else:
        role_package = load_role_package(agent_def_dir, resolved_role_name)

    try:
        effective_runtime_root = resolve_runtime_root(explicit_root=runtime_root)
    except ValueError as exc:
        raise SessionManifestError(str(exc)) from exc
    tool = str(manifest.get("inputs", {}).get("tool", ""))
    selected_backend = backend or backend_for_tool(tool)
    if gateway_auto_attach and selected_backend not in _TMUX_BACKED_BACKENDS:
        raise SessionManifestError(
            "Launch-time gateway attach is only supported for tmux-backed backends."
        )
    selected_workdir = (working_directory or Path.cwd()).resolve()
    session_id = generate_session_id(prefix=selected_backend)

    resolved_runtime_identity: ResolvedRuntimeIdentity | None = None
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
            requested_tmux_session_name=tmux_session_name,
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
    elif agent_identity is not None or agent_name is not None or agent_id is not None:
        raise SessionManifestError(
            "start-session --agent-identity/--agent-name/--agent-id are only supported for "
            f"tmux-backed backends: {sorted(_TMUX_BACKED_BACKENDS)}."
        )

    try:
        job_dir = resolve_session_job_dir(
            session_id=session_id,
            working_directory=selected_workdir,
        )
    except ValueError as exc:
        raise SessionManifestError(str(exc)) from exc
    job_dir.mkdir(parents=True, exist_ok=True)

    declared_mailbox = _declared_mailbox_from_manifest(
        manifest,
        source=str(brain_manifest_path),
    )
    try:
        resolved_mailbox = resolve_effective_mailbox_config(
            declared_config=declared_mailbox,
            runtime_root=effective_runtime_root,
            tool=tool,
            role_name=role_package.role_name,
            agent_identity=(
                resolved_runtime_identity.canonical_agent_name
                if resolved_runtime_identity is not None
                else None
            ),
            transport_override=mailbox_transport,
            filesystem_root_override=mailbox_root,
            principal_id_override=mailbox_principal_id,
            address_override=mailbox_address,
            stalwart_base_url_override=mailbox_stalwart_base_url,
            stalwart_jmap_url_override=mailbox_stalwart_jmap_url,
            stalwart_management_url_override=mailbox_stalwart_management_url,
            stalwart_login_identity_override=mailbox_stalwart_login_identity,
        )
    except ValueError as exc:
        raise SessionManifestError(str(exc)) from exc

    manifest_path = default_manifest_path(effective_runtime_root, selected_backend, session_id)
    manifest_path = manifest_path.resolve()
    if resolved_mailbox is not None:
        try:
            resolved_mailbox = bootstrap_resolved_mailbox(
                resolved_mailbox,
                manifest_path_hint=manifest_path,
                role_name=role_package.role_name,
            )
        except (RuntimeError, ValueError) as exc:
            raise SessionManifestError(f"Failed to bootstrap mailbox support: {exc}") from exc

    launch_plan = build_launch_plan(
        LaunchPlanRequest(
            brain_manifest=manifest,
            role_package=role_package,
            backend=selected_backend,
            working_directory=selected_workdir,
            mailbox=resolved_mailbox,
        )
    )
    launch_plan = _launch_plan_with_job_dir(launch_plan, job_dir=job_dir)

    backend_session = _create_backend_session(
        launch_plan=launch_plan,
        role_name=role_package.role_name,
        role_prompt=role_package.system_prompt,
        agent_def_dir=agent_def_dir,
        api_base_url=api_base_url,
        cao_profile_store_dir=cao_profile_store_dir,
        session_manifest_path=manifest_path,
        agent_identity=(
            tmux_session_name or resolved_runtime_identity.tmux_session_name
            if resolved_runtime_identity is not None
            else None
        ),
        cao_parsing_mode=cao_parsing_mode,
    )

    resolved_tmux_session_name: str | None = None
    resolved_parsing_mode: CaoParsingMode | None = None
    if isinstance(backend_session, CaoRestSession):
        resolved_tmux_session_name = backend_session.state.session_name
        resolved_parsing_mode = backend_session.state.parsing_mode
        startup_warnings = (*startup_warnings, *backend_session.startup_warnings)
    elif isinstance(backend_session, HeadlessInteractiveSession):
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
        else None,
        tmux_session_name=resolved_tmux_session_name,
        job_dir=job_dir,
        agent_identity_warnings=agent_identity_warnings,
        startup_warnings=startup_warnings,
        parsing_mode=resolved_parsing_mode,
        registry_generation_id=(
            new_registry_generation_id() if selected_backend in _TMUX_BACKED_BACKENDS else None
        ),
        registry_launch_authority=registry_launch_authority,
        agent_launch_authority=None,
    )
    controller.persist_manifest(refresh_registry=False)
    controller.ensure_gateway_capability(
        blueprint_gateway_defaults=blueprint_gateway_defaults,
    )
    if gateway_auto_attach:
        attach_result = controller.attach_gateway(
            host_override=gateway_host,
            port_override=gateway_port,
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
        Optional explicit CLI override for the effective agent-definition root
        when resolving a name-based tmux session.

    Returns
    -------
    AgentIdentityResolution
        Resolved manifest path and optional canonical name metadata.
    """

    if is_path_like_agent_identity(agent_identity):
        manifest_path = _resolve_manifest_path(agent_identity, base=base)
        if not manifest_path.is_file():
            raise SessionManifestError(f"Session manifest not found: {manifest_path}")
        return AgentIdentityResolution(session_manifest_path=manifest_path.resolve())

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
    agent_def_dir: Path,
    session_manifest_path: Path,
    cao_profile_store_dir: Path | None = None,
    cao_parsing_mode: CaoParsingMode | None = None,
) -> RuntimeSessionController:
    """Resume a runtime session from a persisted manifest."""

    handle = load_session_manifest(session_manifest_path)
    manifest_payload = parse_session_manifest_payload(
        handle.payload,
        source=str(handle.path),
    )

    backend = manifest_payload.backend
    role_name = manifest_payload.role_name
    brain_manifest_path = Path(manifest_payload.brain_manifest_path).resolve()
    role_package = load_role_package(agent_def_dir, role_name)
    job_dir = _job_dir_from_manifest_payload(
        payload=manifest_payload,
        session_manifest_path=session_manifest_path.resolve(),
    )
    job_dir.mkdir(parents=True, exist_ok=True)

    resolved_mailbox = _resolved_mailbox_from_manifest_payload(
        manifest_payload,
        session_manifest_path=session_manifest_path,
    )
    if _is_joined_tmux_manifest(manifest_payload):
        launch_plan = _build_joined_launch_plan_from_manifest_payload(
            payload=manifest_payload,
            role_package=role_package,
            mailbox=resolved_mailbox,
        )
    else:
        manifest = load_brain_manifest(brain_manifest_path)
        launch_plan = build_launch_plan(
            LaunchPlanRequest(
                brain_manifest=manifest,
                role_package=role_package,
                backend=backend,
                working_directory=Path(manifest_payload.working_directory),
                mailbox=resolved_mailbox,
                intent="resume_control",
            )
        )
    launch_plan = _launch_plan_with_job_dir(launch_plan, job_dir=job_dir)

    backend_session = _create_backend_session(
        launch_plan=launch_plan,
        role_name=role_name,
        role_prompt=role_package.system_prompt,
        agent_def_dir=agent_def_dir,
        cao_profile_store_dir=cao_profile_store_dir,
        resume_state=manifest_payload,
        session_manifest_path=session_manifest_path.resolve(),
        agent_identity=manifest_payload.tmux_session_name,
        cao_parsing_mode=cao_parsing_mode,
    )

    resolved_tmux_session_name: str | None = None
    if isinstance(backend_session, CaoRestSession):
        resolved_tmux_session_name = backend_session.state.session_name
    elif isinstance(backend_session, HeadlessInteractiveSession):
        resolved_tmux_session_name = backend_session.state.tmux_session_name

    registry_generation_id = manifest_payload.registry_generation_id
    if backend in _TMUX_BACKED_BACKENDS and registry_generation_id is None:
        registry_generation_id = new_registry_generation_id()

    controller = RuntimeSessionController(
        launch_plan=launch_plan,
        role_name=role_name,
        brain_manifest_path=brain_manifest_path,
        manifest_path=session_manifest_path.resolve(),
        agent_def_dir=agent_def_dir.resolve(),
        backend_session=backend_session,
        agent_identity=manifest_payload.agent_name,
        agent_id=manifest_payload.agent_id,
        tmux_session_name=resolved_tmux_session_name or manifest_payload.tmux_session_name,
        job_dir=job_dir,
        parsing_mode=(
            backend_session.state.parsing_mode
            if isinstance(backend_session, CaoRestSession)
            else None
        ),
        registry_generation_id=registry_generation_id,
        registry_launch_authority=manifest_payload.registry_launch_authority,
        agent_launch_authority=manifest_payload.agent_launch_authority,
    )
    controller.ensure_gateway_capability()
    return controller


def _create_backend_session(
    *,
    launch_plan: LaunchPlan,
    role_name: str,
    role_prompt: str,
    agent_def_dir: Path,
    api_base_url: str | None = None,
    cao_profile_store_dir: Path | None,
    resume_state: SessionManifestPayloadV3 | SessionManifestPayloadV4 | None = None,
    session_manifest_path: Path | None = None,
    agent_identity: str | None = None,
    cao_parsing_mode: CaoParsingMode | None = None,
) -> InteractiveSession:
    """Create a concrete backend session for start/resume flows."""

    if launch_plan.backend == "codex_app_server":
        if resume_state is not None:
            raise SessionManifestError(
                "Resuming codex_app_server from persisted manifest is not supported "
                "because stdio channel state is not recoverable."
            )
        return cast(InteractiveSession, CodexAppServerSession(launch_plan=launch_plan))

    if launch_plan.backend == "codex_headless":
        state = _resume_headless_state(resume_state, launch_plan=launch_plan)
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
        state = _resume_local_interactive_state(resume_state, launch_plan=launch_plan)
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
        state = _resume_headless_state(resume_state, launch_plan=launch_plan)
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

    if launch_plan.backend == "gemini_headless":
        state = _resume_headless_state(resume_state, launch_plan=launch_plan)
        if (
            state is not None
            and Path(state.working_directory).resolve() != launch_plan.working_directory
        ):
            raise SessionManifestError(
                "Gemini resume requires the same working directory as the persisted session"
            )
        return cast(
            InteractiveSession,
            GeminiHeadlessSession(
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
        existing_state = _resume_houmao_server_state(resume_state)
        configured_mode = configured_cao_parsing_mode(launch_plan)
        resolved_parsing_mode = resolve_cao_parsing_mode(
            tool=launch_plan.tool,
            requested_mode=cao_parsing_mode,
            configured_mode=configured_mode,
        )
        if existing_state is not None and existing_state.parsing_mode != resolved_parsing_mode:
            raise SessionManifestError(
                "houmao-server parsing mode mismatch on resume: "
                f"manifest requires {existing_state.parsing_mode!r}, "
                f"but current configuration resolves to {resolved_parsing_mode!r}."
            )
        resolved_api_base_url = (
            existing_state.api_base_url if existing_state is not None else api_base_url
        )
        if resolved_api_base_url is None or not resolved_api_base_url.strip():
            raise SessionManifestError(
                "houmao-server start requires a non-empty api_base_url for "
                "backend=houmao_server_rest"
            )
        return cast(
            InteractiveSession,
            HoumaoServerRestSession(
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

    raise SessionManifestError(f"Unsupported backend: {launch_plan.backend}")


def _resume_headless_state(
    payload: SessionManifestPayloadV3 | SessionManifestPayloadV4 | None,
    *,
    launch_plan: LaunchPlan,
) -> HeadlessSessionState | None:
    if payload is None:
        return None

    headless = payload.headless
    if headless is None:
        raise SessionManifestError("Headless session manifest missing `headless` state")

    session_id = headless.session_id
    turn_index = headless.turn_index
    if (session_id is None or not session_id.strip()) and turn_index > 0:
        raise SessionManifestError(
            "Headless resume requires a non-empty headless.session_id after turn 0"
        )
    tmux_session_name = _manifest_tmux_session_name(payload)
    if tmux_session_name is None or not tmux_session_name.strip():
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
        tmux_session_name=tmux_session_name.strip(),
        tmux_window_name=tmux_window_name,
        resume_selection_kind=headless.resume_selection_kind,
        resume_selection_value=headless.resume_selection_value,
        joined_session=_is_joined_tmux_manifest(payload),
    )


def _resume_local_interactive_state(
    payload: SessionManifestPayloadV3 | SessionManifestPayloadV4 | None,
    *,
    launch_plan: LaunchPlan,
) -> HeadlessSessionState | None:
    if payload is None:
        return None

    local_interactive = payload.local_interactive
    if local_interactive is None:
        raise SessionManifestError(
            "Local interactive session manifest missing `local_interactive` state"
        )

    tmux_session_name = _manifest_tmux_session_name(payload)
    if tmux_session_name is None or not tmux_session_name.strip():
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
        tmux_session_name=tmux_session_name.strip(),
        tmux_window_name=tmux_window_name,
        joined_session=_is_joined_tmux_manifest(payload),
    )


def _require_session_manifest_path(
    session_manifest_path: Path | None, *, backend: BackendKind
) -> Path:
    if session_manifest_path is None:
        raise SessionManifestError(f"backend={backend} requires a resolved session manifest path.")
    return session_manifest_path.resolve()


def _manifest_tmux_session_name(
    payload: SessionManifestPayloadV3 | SessionManifestPayloadV4,
) -> str | None:
    """Return the normalized tmux session name from one parsed manifest payload."""

    if isinstance(payload, SessionManifestPayloadV4) and payload.tmux is not None:
        return payload.tmux.session_name
    return payload.tmux_session_name


def _manifest_interactive_turn_index(
    payload: SessionManifestPayloadV3 | SessionManifestPayloadV4,
    *,
    fallback: int,
) -> int:
    """Return the normalized interactive turn index for one manifest payload."""

    if isinstance(payload, SessionManifestPayloadV4) and payload.interactive is not None:
        return payload.interactive.turn_index
    return fallback


def _manifest_interactive_working_directory(
    payload: SessionManifestPayloadV3 | SessionManifestPayloadV4,
    *,
    fallback: str,
) -> str:
    """Return the normalized interactive working directory for one manifest payload."""

    if isinstance(payload, SessionManifestPayloadV4) and payload.interactive is not None:
        value = payload.interactive.working_directory
        if value is not None and value.strip():
            return value
    return fallback


def _manifest_interactive_role_bootstrap_applied(
    payload: SessionManifestPayloadV3 | SessionManifestPayloadV4,
    *,
    fallback: bool,
) -> bool:
    """Return the normalized role-bootstrap flag for one manifest payload."""

    if isinstance(payload, SessionManifestPayloadV4) and payload.interactive is not None:
        value = payload.interactive.role_bootstrap_applied
        if value is not None:
            return value
    return fallback


def _manifest_interactive_terminal_id(
    payload: SessionManifestPayloadV3 | SessionManifestPayloadV4,
) -> str | None:
    """Return the normalized interactive terminal id for one manifest payload."""

    if isinstance(payload, SessionManifestPayloadV4) and payload.interactive is not None:
        return payload.interactive.terminal_id
    return None


def _manifest_interactive_parsing_mode(
    payload: SessionManifestPayloadV3 | SessionManifestPayloadV4,
) -> CaoParsingMode | None:
    """Return the normalized interactive parsing mode for one manifest payload."""

    if isinstance(payload, SessionManifestPayloadV4) and payload.interactive is not None:
        return payload.interactive.parsing_mode
    return None


def _manifest_interactive_tmux_window_name(
    payload: SessionManifestPayloadV3 | SessionManifestPayloadV4,
) -> str | None:
    """Return the normalized interactive tmux window name for one manifest payload."""

    if isinstance(payload, SessionManifestPayloadV4) and payload.interactive is not None:
        return payload.interactive.tmux_window_name
    return None


def _manifest_primary_tmux_window_name(
    payload: SessionManifestPayloadV3 | SessionManifestPayloadV4,
) -> str | None:
    """Return the best persisted tmux window name from one manifest payload."""

    if isinstance(payload, SessionManifestPayloadV4) and payload.tmux is not None:
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


def _joined_launch_plan_tmux_window_name(launch_plan: LaunchPlan) -> str | None:
    """Return the joined launch-plan tmux window name when one was persisted."""

    value = launch_plan.metadata.get("tmux_window_name")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _resolved_resumed_tmux_window_name(
    *,
    payload: SessionManifestPayloadV3 | SessionManifestPayloadV4,
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
    payload: SessionManifestPayloadV3 | SessionManifestPayloadV4,
) -> str | None:
    """Return the normalized pair-managed session alias for one manifest payload."""

    if isinstance(payload, SessionManifestPayloadV4) and payload.gateway_authority is not None:
        return payload.gateway_authority.attach.managed_agent_ref
    if payload.houmao_server is not None:
        return payload.houmao_server.session_name
    return None


def _is_joined_tmux_manifest(
    payload: SessionManifestPayloadV3 | SessionManifestPayloadV4,
) -> bool:
    """Return whether one manifest payload describes a joined tmux session."""

    return (
        isinstance(payload, SessionManifestPayloadV4)
        and payload.agent_launch_authority is not None
        and payload.agent_launch_authority.session_origin == _JOINED_SESSION_ORIGIN
    )


def _build_joined_launch_plan_from_manifest_payload(
    *,
    payload: SessionManifestPayloadV3 | SessionManifestPayloadV4,
    role_package: RolePackage,
    mailbox: MailboxResolvedConfig | None,
) -> LaunchPlan:
    """Rebuild a join-derived launch plan from the persisted session manifest."""

    if not isinstance(payload, SessionManifestPayloadV4) or payload.agent_launch_authority is None:
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
        mailbox=mailbox,
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
    payload: SessionManifestPayloadV3 | SessionManifestPayloadV4,
    key: str,
) -> str | None:
    """Return one normalized optional backend_state string."""

    value = payload.backend_state.get(key)
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


def _relaunch_backend_session(controller: RuntimeSessionController) -> SessionControlResult:
    """Dispatch the shared relaunch primitive across supported tmux-backed backends."""

    backend_session = controller.backend_session
    if isinstance(backend_session, HoumaoServerRestSession):
        return backend_session.relaunch()
    if isinstance(backend_session, LocalInteractiveSession):
        return backend_session.relaunch()
    if isinstance(backend_session, HeadlessInteractiveSession):
        return backend_session.relaunch()
    if isinstance(backend_session, CaoRestSession):
        return backend_session.relaunch()
    return SessionControlResult(
        status="error",
        action="relaunch",
        detail=(
            f"backend={controller.launch_plan.backend!r} does not support tmux-backed relaunch."
        ),
    )


def _refresh_pair_launch_registration(controller: RuntimeSessionController) -> None:
    """Refresh the pair launch registration after a successful local relaunch."""

    if controller.launch_plan.backend != "houmao_server_rest":
        return
    backend_session = controller.backend_session
    if not isinstance(backend_session, HoumaoServerRestSession):
        raise SessionManifestError(
            "Pair-backed relaunch completed without a houmao_server_rest backend session."
        )

    state = backend_session.state
    client = HoumaoServerClient(state.api_base_url)
    try:
        client.register_launch(
            HoumaoRegisterLaunchRequest(
                session_name=state.session_name,
                terminal_id=state.terminal_id,
                tool=controller.launch_plan.tool,
                manifest_path=str(controller.manifest_path),
                session_root=str(controller.manifest_path.parent),
                agent_name=controller.agent_identity,
                agent_id=controller.agent_id,
                tmux_session_name=controller.tmux_session_name or state.session_name,
                tmux_window_name=state.tmux_window_name,
            )
        )
    except Exception as exc:
        raise SessionManifestError(
            "Pair-managed relaunch succeeded locally, but failed to refresh the owning "
            f"`houmao-server` registration: {exc}"
        ) from exc


def _resume_cao_state(
    payload: SessionManifestPayloadV3 | SessionManifestPayloadV4 | None,
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
    payload: SessionManifestPayloadV3 | SessionManifestPayloadV4 | None,
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

    if isinstance(session, CodexAppServerSession):
        return cast(GatewayJsonObject, codex_backend_state_payload(session.state))
    if isinstance(session, HeadlessInteractiveSession):
        return cast(GatewayJsonObject, headless_backend_state_payload(session.state))
    if isinstance(session, HoumaoServerRestSession):
        return cast(GatewayJsonObject, cao_backend_state_payload(session.state))
    if isinstance(session, CaoRestSession):
        return cast(GatewayJsonObject, cao_backend_state_payload(session.state))
    return {}


def _declared_mailbox_from_manifest(
    manifest: dict[str, object],
    *,
    source: str,
) -> MailboxDeclarativeConfig | None:
    try:
        return parse_declarative_mailbox_config(
            manifest.get("mailbox"),
            source=source,
        )
    except ValueError as exc:
        raise SessionManifestError(str(exc)) from exc


def _resolved_mailbox_from_manifest_payload(
    payload: SessionManifestPayloadV3 | SessionManifestPayloadV4,
    *,
    session_manifest_path: Path,
) -> MailboxResolvedConfig | None:
    try:
        return resolved_mailbox_config_from_payload(
            payload.launch_plan.mailbox,
            manifest_path=session_manifest_path.resolve(),
        )
    except ValueError as exc:
        raise SessionManifestError(str(exc)) from exc


def _launch_plan_with_mailbox(
    launch_plan: LaunchPlan,
    mailbox: MailboxResolvedConfig,
) -> LaunchPlan:
    mailbox_env = mailbox_env_bindings(mailbox)
    updated_env = dict(launch_plan.env)
    updated_env.update(mailbox_env)
    return replace(
        launch_plan,
        env=updated_env,
        env_var_names=sorted({*launch_plan.env_var_names, *mailbox_env.keys()}),
        mailbox=mailbox,
    )


def _launch_plan_with_job_dir(launch_plan: LaunchPlan, *, job_dir: Path) -> LaunchPlan:
    """Return a launch plan with the runtime-owned job-dir binding injected."""

    updated_env = dict(launch_plan.env)
    updated_env[AGENTSYS_JOB_DIR_ENV_VAR] = str(job_dir.resolve())
    return replace(
        launch_plan,
        env=updated_env,
        env_var_names=sorted({*launch_plan.env_var_names, AGENTSYS_JOB_DIR_ENV_VAR}),
    )


def _backend_requires_provider_start_relaunch(backend: BackendKind) -> bool:
    """Return whether one backend relaunch must rebuild provider-start state."""

    return backend in {
        "local_interactive",
        "codex_headless",
        "claude_headless",
        "gemini_headless",
    }


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
                mailbox=_resolved_mailbox_from_manifest_payload(
                    payload,
                    session_manifest_path=controller.manifest_path,
                ),
            )
            if controller.job_dir is not None:
                updated_launch_plan = _launch_plan_with_job_dir(
                    updated_launch_plan,
                    job_dir=controller.job_dir,
                )
            return updated_launch_plan

    if controller.agent_def_dir is None:
        raise SessionManifestError(
            "Local provider relaunch requires a persisted agent-definition directory."
        )

    manifest = load_brain_manifest(controller.brain_manifest_path)
    role_package = load_role_package(controller.agent_def_dir, controller.role_name)
    updated_launch_plan = build_launch_plan(
        LaunchPlanRequest(
            brain_manifest=manifest,
            role_package=role_package,
            backend=controller.launch_plan.backend,
            working_directory=controller.launch_plan.working_directory,
            mailbox=controller.launch_plan.mailbox,
            intent="provider_start",
        )
    )
    if controller.job_dir is not None:
        updated_launch_plan = _launch_plan_with_job_dir(
            updated_launch_plan,
            job_dir=controller.job_dir,
        )
    return updated_launch_plan


def _job_dir_from_manifest_payload(
    *,
    payload: SessionManifestPayloadV3 | SessionManifestPayloadV4,
    session_manifest_path: Path,
) -> Path:
    """Resolve the persisted or fallback job dir for one manifest payload."""

    if payload.job_dir is not None:
        return Path(payload.job_dir).resolve()

    session_id = _runtime_session_id_from_manifest_path(session_manifest_path)
    if session_id is None:
        raise SessionManifestError(
            "Session manifest is missing `job_dir` and does not use the runtime-owned "
            "`<session-root>/manifest.json` layout required for fallback derivation."
        )
    try:
        return resolve_session_job_dir(
            session_id=session_id,
            working_directory=Path(payload.working_directory).resolve(),
        )
    except ValueError as exc:
        raise SessionManifestError(str(exc)) from exc


def _resolve_start_session_identity(
    *,
    manifest: dict[str, object],
    tool: str,
    role_name: str,
    requested_agent_name: str | None = None,
    requested_agent_identity: str | None,
    requested_agent_id: str | None,
    requested_tmux_session_name: str | None = None,
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

    stripped_requested_agent_id = None
    if requested_agent_id is not None:
        stripped_requested_agent_id = normalize_managed_agent_id(requested_agent_id)

    persisted_agent_id = built_identity[1]
    agent_id = (
        stripped_requested_agent_id or persisted_agent_id or derive_agent_id_from_name(agent_name)
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
    if stripped_requested_tmux_session_name is not None:
        resolved_tmux_session_name = stripped_requested_tmux_session_name
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
    if not isinstance(raw_identity, dict):
        return None, None

    raw_agent_name = raw_identity.get("canonical_agent_name")
    agent_name = None
    if isinstance(raw_agent_name, str) and raw_agent_name.strip():
        agent_name = normalize_managed_agent_name(raw_agent_name)

    raw_agent_id = raw_identity.get("agent_id")
    agent_id = None
    if isinstance(raw_agent_id, str) and raw_agent_id.strip():
        agent_id = normalize_managed_agent_id(raw_agent_id)
    return agent_name, agent_id


def _default_canonical_agent_name(*, tool: str, role_name: str) -> str:
    """Return the default canonical agent name for a tmux-backed session."""

    normalized = normalize_agent_identity_name(
        derive_auto_agent_name_base(tool=tool, role_name=role_name)
    )
    return normalized.canonical_name


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


def _preserve_server_managed_headless_gateway_authority(
    *,
    manifest_path: Path,
    backend: str,
    payload: dict[str, object],
) -> dict[str, object]:
    """Preserve server-managed headless pair routing when runtime state omits it."""

    if backend not in {"codex_headless", "claude_headless", "gemini_headless"}:
        return payload

    raw_gateway_authority = payload.get("gateway_authority")
    if not isinstance(raw_gateway_authority, dict):
        return payload

    try:
        existing_handle = load_session_manifest(manifest_path)
        existing_payload = parse_session_manifest_payload(
            existing_handle.payload,
            source=str(existing_handle.path),
        )
    except SessionManifestError:
        return payload

    existing_gateway_authority = existing_payload.gateway_authority
    if existing_gateway_authority is None:
        return payload

    merged_gateway_authority = dict(raw_gateway_authority)
    for endpoint_name in ("attach", "control"):
        raw_endpoint = merged_gateway_authority.get(endpoint_name)
        merged_endpoint = dict(raw_endpoint) if isinstance(raw_endpoint, dict) else {}
        existing_endpoint = getattr(existing_gateway_authority, endpoint_name).model_dump(
            mode="json"
        )
        for field_name in ("api_base_url", "managed_agent_ref"):
            if (
                merged_endpoint.get(field_name) is None
                and existing_endpoint.get(field_name) is not None
            ):
                merged_endpoint[field_name] = existing_endpoint[field_name]
        merged_gateway_authority[endpoint_name] = merged_endpoint

    updated_payload = dict(payload)
    updated_payload["gateway_authority"] = merged_gateway_authority
    return updated_payload


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

    matches: list[tuple[str, Path]] = []
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
        matches.append((session_name, manifest_path))

    if not matches:
        if direct_error is not None:
            raise direct_error
        raise _TmuxLocalDiscoveryUnavailableError(
            f"No local tmux session metadata matched canonical agent name "
            f"`{canonical_agent_identity}`."
        )
    if len(matches) > 1:
        matched_sessions = ", ".join(sorted(session_name for session_name, _ in matches))
        raise SessionManifestError(
            "Agent-name resolution is ambiguous: canonical agent name "
            f"`{canonical_agent_identity}` matched multiple tmux sessions: {matched_sessions}."
        )

    session_name, manifest_path = matches[0]
    return AgentIdentityResolution(
        session_manifest_path=manifest_path,
        canonical_agent_identity=canonical_agent_identity,
        agent_def_dir=_resolve_agent_def_dir_for_name_resolution(
            session_name=session_name,
            explicit_agent_def_dir=explicit_agent_def_dir,
        ),
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
        agent_def_dir=_resolve_agent_def_dir_for_name_resolution(
            session_name=canonical_agent_identity,
            explicit_agent_def_dir=explicit_agent_def_dir,
        ),
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
    record: LiveAgentRegistryRecordV2,
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

    _validate_resolved_manifest_matches_tmux_session(
        manifest_path=manifest_path,
        session_name=record.terminal.session_name,
    )

    return AgentIdentityResolution(
        session_manifest_path=manifest_path,
        canonical_agent_identity=record.agent_name,
        agent_def_dir=_resolve_agent_def_dir_for_registry_resolution(
            record=record,
            explicit_agent_def_dir=explicit_agent_def_dir,
        ),
        warnings=warnings,
    )


def _resolve_agent_def_dir_for_name_resolution(
    *,
    session_name: str,
    explicit_agent_def_dir: Path | None,
) -> Path:
    """Resolve the effective agent-definition root for name-based control."""

    if explicit_agent_def_dir is not None:
        resolved_override = explicit_agent_def_dir.resolve()
        if not resolved_override.is_dir():
            raise SessionManifestError(
                "Explicit `--agent-def-dir` override must point to an existing directory, "
                f"got `{resolved_override}`."
            )
        return resolved_override

    resolved_agent_def_dir = Path(
        _read_tmux_session_env_var(
            session_name=session_name,
            variable_name=AGENT_DEF_DIR_ENV_VAR,
            missing_message="Agent definition pointer missing",
        )
    )
    if not resolved_agent_def_dir.is_absolute():
        raise SessionManifestError(
            f"Invalid agent definition pointer in tmux session `{session_name}`: "
            f"`{AGENT_DEF_DIR_ENV_VAR}` must be an absolute path."
        )
    resolved_agent_def_dir = resolved_agent_def_dir.resolve()
    if not resolved_agent_def_dir.is_dir():
        raise _TmuxLocalDiscoveryUnavailableError(
            f"Agent definition pointer stale: `{AGENT_DEF_DIR_ENV_VAR}` in tmux "
            f"session `{session_name}` points to missing directory `{resolved_agent_def_dir}`."
        )
    return resolved_agent_def_dir


def _resolve_agent_def_dir_for_registry_resolution(
    *,
    record: LiveAgentRegistryRecordV2,
    explicit_agent_def_dir: Path | None,
) -> Path:
    """Resolve the effective agent-definition root for registry-based control."""

    if explicit_agent_def_dir is not None:
        resolved_override = explicit_agent_def_dir.resolve()
        if not resolved_override.is_dir():
            raise SessionManifestError(
                "Explicit `--agent-def-dir` override must point to an existing directory, "
                f"got `{resolved_override}`."
            )
        return resolved_override

    agent_def_dir_value = record.runtime.agent_def_dir
    if agent_def_dir_value is None:
        raise SessionManifestError(
            "Shared-registry record is missing `runtime.agent_def_dir`, so name-based "
            "control requires an explicit `--agent-def-dir` override."
        )

    resolved_agent_def_dir = Path(agent_def_dir_value)
    if not resolved_agent_def_dir.is_absolute():
        raise SessionManifestError(
            "Shared-registry record has invalid runtime.agent_def_dir: "
            f"expected an absolute path, got `{resolved_agent_def_dir}`."
        )

    resolved_agent_def_dir = resolved_agent_def_dir.resolve()
    if not resolved_agent_def_dir.is_dir():
        raise SessionManifestError(
            "Shared-registry agent-definition pointer is stale: "
            f"`{resolved_agent_def_dir}` does not exist."
        )
    return resolved_agent_def_dir


def _validate_resolved_manifest_matches_tmux_session(
    *, manifest_path: Path, session_name: str
) -> None:
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


def _persisted_tmux_session_name(
    *,
    payload: SessionManifestPayloadV3 | SessionManifestPayloadV4,
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


def _runtime_agent_def_dir(controller: RuntimeSessionController) -> Path | None:
    """Return the runtime-owned agent-definition directory when available."""

    if controller.agent_def_dir is None:
        return None
    return controller.agent_def_dir.resolve()


def _build_shared_registry_record_for_controller(
    controller: RuntimeSessionController,
) -> LiveAgentRegistryRecordV2 | None:
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
    mailbox = controller.launch_plan.mailbox
    lease_ttl = (
        JOINED_REGISTRY_SENTINEL_LEASE_TTL
        if (
            controller.agent_launch_authority is not None
            and controller.agent_launch_authority.session_origin == _JOINED_SESSION_ORIGIN
        )
        else DEFAULT_REGISTRY_LEASE_TTL
    )

    gateway_payload = _shared_registry_gateway_payload(controller)
    if isinstance(mailbox, FilesystemMailboxResolvedConfig):
        mailbox_payload: RegistryMailboxV1 | None = RegistryMailboxFilesystemV1(
            transport="filesystem",
            principal_id=mailbox.principal_id,
            address=mailbox.address,
            filesystem_root=str(mailbox.filesystem_root.resolve()),
            bindings_version=mailbox.bindings_version,
        )
    elif isinstance(mailbox, StalwartMailboxResolvedConfig):
        mailbox_payload = RegistryMailboxStalwartV1(
            transport="stalwart",
            principal_id=mailbox.principal_id,
            address=mailbox.address,
            bindings_version=mailbox.bindings_version,
            jmap_url=mailbox.jmap_url,
            management_url=mailbox.management_url,
            login_identity=mailbox.login_identity,
            credential_ref=mailbox.credential_ref,
        )
    else:
        mailbox_payload = None

    return LiveAgentRegistryRecordV2(
        agent_name=canonicalize_registry_agent_name(canonical_agent_name),
        agent_id=agent_id,
        generation_id=generation_id,
        published_at=published_at.isoformat(timespec="seconds"),
        lease_expires_at=(published_at + lease_ttl).isoformat(timespec="seconds"),
        identity=RegistryIdentityV1(
            backend=controller.launch_plan.backend,
            tool=controller.launch_plan.tool,
        ),
        runtime=RegistryRuntimeV1(
            manifest_path=str(controller.manifest_path.resolve()),
            session_root=str(session_root.resolve()) if session_root is not None else None,
            agent_def_dir=(
                str(controller.agent_def_dir.resolve())
                if controller.agent_def_dir is not None
                else None
            ),
        ),
        terminal=RegistryTerminalV1(
            kind="tmux",
            session_name=tmux_session_name,
        ),
        gateway=gateway_payload,
        mailbox=mailbox_payload,
    )


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
        host=cast(GatewayHost, current_instance.host),
        port=current_instance.port,
        state_path=str(paths.state_path.resolve()),
        protocol_version=current_instance.protocol_version,
    )


def _tmux_session_name_for_controller(controller: RuntimeSessionController) -> str | None:
    """Return the tmux session name for a runtime controller."""

    if controller.tmux_session_name is not None:
        return controller.tmux_session_name
    if isinstance(controller.backend_session, CaoRestSession):
        return controller.backend_session.state.session_name
    if isinstance(controller.backend_session, HeadlessInteractiveSession):
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

    controller.ensure_gateway_capability()
    paths = gateway_paths_from_manifest_path(controller.manifest_path)
    if paths is None:
        raise GatewayDiscoveryError(
            "Gateway operations require a runtime-owned session manifest rooted at "
            "`<session-root>/manifest.json`."
        )
    return paths


def _attach_gateway_for_controller(
    controller: RuntimeSessionController,
    *,
    host_override: str | None,
    port_override: int | None,
    execution_mode_override: GatewayCurrentExecutionMode | None,
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
    attach_contract = resolve_internal_gateway_attach_contract(paths)
    try:
        host, requested_port = _resolve_gateway_listener(
            paths=paths,
            attach_contract=attach_contract,
            host_override=host_override,
            port_override=port_override,
        )
        execution_mode = _resolve_gateway_execution_mode(
            controller=controller,
            paths=paths,
            execution_mode_override=execution_mode_override,
        )
        resolved_port = _start_gateway_process(
            controller=controller,
            paths=paths,
            host=host,
            port=requested_port,
            execution_mode=execution_mode,
        )
    except (
        GatewayAttachError,
        GatewayDiscoveryError,
        GatewayProtocolError,
        GatewayUnsupportedBackendError,
        TmuxCommandError,
    ) as exc:
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
        client = _validated_gateway_client_for_controller(controller, paths=paths)
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


def _validated_gateway_client_for_controller(
    controller: RuntimeSessionController,
    *,
    paths: GatewayPaths,
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
    return client


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


def _find_tmux_pane(
    *,
    session_name: str,
    pane_id: str,
) -> TmuxPaneRecord | None:
    """Return one tmux pane record by id when present."""

    for pane in list_tmux_panes_shared(session_name=session_name):
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
        )
    )
    log_target = shlex.quote(str(paths.log_path))
    return f"{exports}{gateway_command} 2>&1 | tee -a {log_target}; exit ${{PIPESTATUS[0]}}"


def _launch_same_session_gateway_window(
    *,
    controller: RuntimeSessionController,
    session_name: str,
    paths: GatewayPaths,
    host: GatewayHost,
    port: int,
) -> _TmuxAuxiliaryWindowHandle:
    """Launch one same-session gateway window and return its tmux execution handle."""

    command = _same_session_gateway_shell_command(paths=paths, host=host, port=port)
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
                except GatewayHttpError:
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
                f"Timed out waiting for gateway health readiness on {host}:{endpoint.port}."
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
            except GatewayHttpError:
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
            f"Timed out waiting for gateway health readiness on {host}:{endpoint.port}."
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
