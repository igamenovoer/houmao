"""High-level session runtime orchestration."""

from __future__ import annotations

import logging
import os
import signal
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from .agent_identity import (
    AGENT_DEF_DIR_ENV_VAR,
    AGENT_MANIFEST_PATH_ENV_VAR,
    is_path_like_agent_identity,
    normalize_agent_identity_name,
)
from .backends.cao_rest import (
    CaoRestSession,
    CaoSessionState,
    cao_backend_state_payload,
)
from .boundary_models import SessionManifestPayloadV2
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
from .backends.tmux_runtime import (
    TmuxCommandError,
    has_tmux_session as has_tmux_session_shared,
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
    SessionManifestError,
)
from .gateway_client import GatewayClient, GatewayEndpoint
from .gateway_models import (
    GATEWAY_PROTOCOL_VERSION,
    BlueprintGatewayDefaults,
    GatewayAcceptedRequestV1,
    GatewayAttachContractV1,
    GatewayDesiredConfigV1,
    GatewayHost,
    GatewayJsonObject,
    GatewayProtocolVersion,
    GatewayRequestCreateV1,
    GatewayRequestPayloadInterruptV1,
    GatewayRequestPayloadSubmitPromptV1,
    GatewayStatusV1,
)
from .gateway_storage import (
    AGENT_GATEWAY_HOST_ENV_VAR,
    AGENT_GATEWAY_PORT_ENV_VAR,
    AGENT_GATEWAY_PROTOCOL_VERSION_ENV_VAR,
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
    load_attach_contract,
    load_gateway_current_instance,
    load_gateway_desired_config,
    load_gateway_status,
    publish_live_gateway_env,
    publish_stable_gateway_env,
    read_pid_file,
    write_attach_contract,
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
from .loaders import load_brain_manifest, load_role_package
from houmao.agents.mailbox_runtime_support import (
    MAILBOX_TRANSPORT_FILESYSTEM,
    bootstrap_resolved_mailbox,
    mailbox_env_bindings,
    parse_declarative_mailbox_config,
    refresh_filesystem_mailbox_config,
    resolve_effective_mailbox_config,
    resolved_mailbox_config_from_payload,
)
from houmao.agents.mailbox_runtime_models import (
    MailboxDeclarativeConfig,
    MailboxResolvedConfig,
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
    SessionControlResult,
    SessionEvent,
)
from .registry_models import (
    LiveAgentRegistryRecordV1,
    RegistryGatewayV1,
    RegistryIdentityV1,
    RegistryMailboxV1,
    RegistryRuntimeV1,
    RegistryTerminalV1,
    canonicalize_registry_agent_name,
    derive_agent_key,
)
from .registry_storage import (
    DEFAULT_REGISTRY_LEASE_TTL,
    new_registry_generation_id,
    publish_live_agent_record,
    remove_live_agent_record,
    resolve_live_agent_record,
)

_TMUX_BACKED_BACKENDS: frozenset[BackendKind] = frozenset(
    {"codex_headless", "claude_headless", "gemini_headless", "cao_rest"}
)
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
    agent_identity_warnings: tuple[str, ...] = ()
    startup_warnings: tuple[str, ...] = ()
    parsing_mode: CaoParsingMode | None = None
    gateway_root: Path | None = None
    gateway_attach_path: Path | None = None
    gateway_auto_attach_error: str | None = None
    gateway_host: str | None = None
    gateway_port: int | None = None
    registry_generation_id: str | None = None
    operation_warnings: tuple[str, ...] = ()

    def send_prompt(self, prompt: str) -> list[SessionEvent]:
        """Send a prompt and persist updated session state."""

        self._reset_operation_warnings()
        events = self.backend_session.send_prompt(prompt)
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

        result = SessionControlResult(
            status="error",
            action="control_input",
            detail=(
                "Raw control input is only supported for resumed "
                f"backend=cao_rest sessions, got backend={self.launch_plan.backend!r}."
            ),
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
        if mailbox.transport != MAILBOX_TRANSPORT_FILESYSTEM:
            raise SessionManifestError(
                f"Mailbox binding refresh is not implemented for transport={mailbox.transport!r}."
            )

        refreshed = refresh_filesystem_mailbox_config(
            mailbox,
            filesystem_root=filesystem_root,
        )
        try:
            bootstrap_resolved_mailbox(
                refreshed,
                manifest_path_hint=self.manifest_path,
                role_name=self.role_name,
            )
        except RuntimeError as exc:
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

    def persist_manifest(self, *, refresh_registry: bool = True) -> None:
        """Persist current backend state to session manifest."""

        backend_state = _backend_state_for_session(self.backend_session)
        payload = build_session_manifest_payload(
            SessionManifestRequest(
                launch_plan=self.launch_plan,
                role_name=self.role_name,
                brain_manifest_path=self.brain_manifest_path,
                backend_state=backend_state,
                registry_generation_id=self.registry_generation_id,
            )
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
        publish_stable_gateway_env(
            session_name=session_name,
            attach_path=paths.attach_path,
            gateway_root=paths.gateway_root,
            set_env=set_tmux_session_environment_shared,
        )
        self.gateway_root = paths.gateway_root
        self.gateway_attach_path = paths.attach_path
        self.refresh_shared_registry_record()

    def attach_gateway(
        self,
        *,
        host_override: str | None = None,
        port_override: int | None = None,
    ) -> GatewayControlResult:
        """Start a live gateway instance for the addressed session."""

        result = _attach_gateway_for_controller(
            self,
            host_override=host_override,
            port_override=port_override,
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

    def refresh_shared_registry_record(self) -> LiveAgentRegistryRecordV1 | None:
        """Publish or refresh the shared-registry record for this live session."""

        record = _build_shared_registry_record_for_controller(self)
        if record is None:
            return None
        return publish_live_agent_record(record)

    def clear_shared_registry_record(self) -> bool:
        """Remove this session's shared-registry record during authoritative teardown."""

        session_name = _tmux_session_name_for_controller(self)
        if not self._is_tmux_backed() or session_name is None:
            return False
        return remove_live_agent_record(
            session_name,
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
    role_name: str,
    runtime_root: Path,
    backend: BackendKind | None = None,
    working_directory: Path | None = None,
    api_base_url: str = "http://localhost:9889",
    cao_profile_store_dir: Path | None = None,
    agent_identity: str | None = None,
    cao_parsing_mode: CaoParsingMode | None = None,
    mailbox_transport: str | None = None,
    mailbox_root: Path | None = None,
    mailbox_principal_id: str | None = None,
    mailbox_address: str | None = None,
    blueprint_gateway_defaults: BlueprintGatewayDefaults | None = None,
    gateway_auto_attach: bool = False,
    gateway_host: str | None = None,
    gateway_port: int | None = None,
) -> RuntimeSessionController:
    """Start a new runtime session and persist its session manifest."""

    if (gateway_host is not None or gateway_port is not None) and not gateway_auto_attach:
        raise SessionManifestError(
            "Gateway host or port overrides require launch-time gateway attach."
        )

    manifest = load_brain_manifest(brain_manifest_path)
    role_package = load_role_package(agent_def_dir, role_name)

    tool = str(manifest.get("inputs", {}).get("tool", ""))
    selected_backend = backend or backend_for_tool(tool)
    if gateway_auto_attach and selected_backend not in _TMUX_BACKED_BACKENDS:
        raise SessionManifestError(
            "Launch-time gateway attach is only supported for tmux-backed backends."
        )
    selected_workdir = (working_directory or Path.cwd()).resolve()
    declared_mailbox = _declared_mailbox_from_manifest(
        manifest,
        source=str(brain_manifest_path),
    )
    try:
        resolved_mailbox = resolve_effective_mailbox_config(
            declared_config=declared_mailbox,
            runtime_root=runtime_root.resolve(),
            tool=tool,
            role_name=role_name,
            agent_identity=agent_identity,
            transport_override=mailbox_transport,
            filesystem_root_override=mailbox_root,
            principal_id_override=mailbox_principal_id,
            address_override=mailbox_address,
        )
    except ValueError as exc:
        raise SessionManifestError(str(exc)) from exc

    launch_plan = build_launch_plan(
        LaunchPlanRequest(
            brain_manifest=manifest,
            role_package=role_package,
            backend=selected_backend,
            working_directory=selected_workdir,
            mailbox=resolved_mailbox,
        )
    )

    session_id = generate_session_id(prefix=selected_backend)
    manifest_path = default_manifest_path(runtime_root, selected_backend, session_id)
    manifest_path = manifest_path.resolve()
    if resolved_mailbox is not None:
        try:
            bootstrap_resolved_mailbox(
                resolved_mailbox,
                manifest_path_hint=manifest_path,
                role_name=role_name,
            )
        except RuntimeError as exc:
            raise SessionManifestError(f"Failed to bootstrap mailbox support: {exc}") from exc

    canonical_agent_identity: str | None = None
    agent_identity_warnings: tuple[str, ...] = ()
    if selected_backend in _TMUX_BACKED_BACKENDS:
        if agent_identity is not None:
            if is_path_like_agent_identity(agent_identity):
                raise SessionManifestError(
                    "start-session --agent-identity must be a name for "
                    f"backend={selected_backend}, not a manifest path."
                )
            normalized = normalize_agent_identity_name(agent_identity)
            canonical_agent_identity = normalized.canonical_name
            agent_identity_warnings = normalized.warnings
    elif agent_identity is not None:
        raise SessionManifestError(
            "start-session --agent-identity is only supported for tmux-backed "
            f"backends: {sorted(_TMUX_BACKED_BACKENDS)}."
        )

    backend_session = _create_backend_session(
        launch_plan=launch_plan,
        role_name=role_name,
        role_prompt=role_package.system_prompt,
        agent_def_dir=agent_def_dir,
        api_base_url=api_base_url,
        cao_profile_store_dir=cao_profile_store_dir,
        session_manifest_path=manifest_path,
        agent_identity=canonical_agent_identity,
        cao_parsing_mode=cao_parsing_mode,
    )

    resolved_agent_identity: str | None = None
    resolved_parsing_mode: CaoParsingMode | None = None
    startup_warnings: tuple[str, ...] = ()
    if isinstance(backend_session, CaoRestSession):
        resolved_agent_identity = backend_session.state.session_name
        resolved_parsing_mode = backend_session.state.parsing_mode
        startup_warnings = backend_session.startup_warnings
    elif isinstance(backend_session, HeadlessInteractiveSession):
        resolved_agent_identity = backend_session.state.tmux_session_name

    controller = RuntimeSessionController(
        launch_plan=launch_plan,
        role_name=role_name,
        brain_manifest_path=brain_manifest_path.resolve(),
        manifest_path=manifest_path,
        agent_def_dir=agent_def_dir.resolve(),
        backend_session=backend_session,
        agent_identity=resolved_agent_identity,
        agent_identity_warnings=agent_identity_warnings,
        startup_warnings=startup_warnings,
        parsing_mode=resolved_parsing_mode,
        registry_generation_id=(
            new_registry_generation_id() if selected_backend in _TMUX_BACKED_BACKENDS else None
        ),
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

    normalized = normalize_agent_identity_name(agent_identity)
    try:
        _ensure_tmux_session_exists(session_name=normalized.canonical_name)
    except SessionManifestError as tmux_error:
        registry_resolution = _resolve_agent_identity_from_shared_registry(
            canonical_agent_identity=normalized.canonical_name,
            explicit_agent_def_dir=explicit_agent_def_dir,
            warnings=normalized.warnings,
        )
        if registry_resolution is not None:
            return registry_resolution
        raise SessionManifestError(
            f"{tmux_error} Shared-registry fallback did not find a fresh record for "
            f"`{normalized.canonical_name}`."
        ) from tmux_error

    try:
        return _resolve_agent_identity_from_tmux_local(
            canonical_agent_identity=normalized.canonical_name,
            explicit_agent_def_dir=explicit_agent_def_dir,
            warnings=normalized.warnings,
        )
    except _TmuxLocalDiscoveryUnavailableError as discovery_error:
        registry_resolution = _resolve_agent_identity_from_shared_registry(
            canonical_agent_identity=normalized.canonical_name,
            explicit_agent_def_dir=explicit_agent_def_dir,
            warnings=normalized.warnings,
        )
        if registry_resolution is not None:
            return registry_resolution
        raise SessionManifestError(
            f"{discovery_error} Shared-registry fallback did not find a fresh record for "
            f"`{normalized.canonical_name}`."
        ) from discovery_error


def resume_runtime_session(
    *,
    agent_def_dir: Path,
    session_manifest_path: Path,
    cao_profile_store_dir: Path | None = None,
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
    manifest = load_brain_manifest(brain_manifest_path)
    role_package = load_role_package(agent_def_dir, role_name)

    launch_plan = build_launch_plan(
        LaunchPlanRequest(
            brain_manifest=manifest,
            role_package=role_package,
            backend=backend,
            working_directory=Path(manifest_payload.working_directory),
            mailbox=_resolved_mailbox_from_manifest_payload(manifest_payload),
        )
    )

    backend_session = _create_backend_session(
        launch_plan=launch_plan,
        role_name=role_name,
        role_prompt=role_package.system_prompt,
        agent_def_dir=agent_def_dir,
        cao_profile_store_dir=cao_profile_store_dir,
        resume_state=manifest_payload,
        session_manifest_path=session_manifest_path.resolve(),
    )

    resolved_agent_identity: str | None = None
    if isinstance(backend_session, CaoRestSession):
        resolved_agent_identity = backend_session.state.session_name
    elif isinstance(backend_session, HeadlessInteractiveSession):
        resolved_agent_identity = backend_session.state.tmux_session_name

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
        agent_identity=resolved_agent_identity,
        parsing_mode=(
            backend_session.state.parsing_mode
            if isinstance(backend_session, CaoRestSession)
            else None
        ),
        registry_generation_id=registry_generation_id,
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
    resume_state: SessionManifestPayloadV2 | None = None,
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
                agent_identity=agent_identity,
                parsing_mode=resolved_parsing_mode,
            ),
        )

    raise SessionManifestError(f"Unsupported backend: {launch_plan.backend}")


def _resume_headless_state(
    payload: SessionManifestPayloadV2 | None,
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
    tmux_session_name = payload.backend_state.get("tmux_session_name")
    if not isinstance(tmux_session_name, str) or not tmux_session_name.strip():
        raise SessionManifestError(
            "Headless resume requires non-empty backend_state.tmux_session_name"
        )

    return HeadlessSessionState(
        session_id=session_id.strip() if session_id else None,
        turn_index=turn_index,
        role_bootstrap_applied=headless.role_bootstrap_applied,
        working_directory=headless.working_directory or str(launch_plan.working_directory),
        tmux_session_name=tmux_session_name.strip(),
    )


def _require_session_manifest_path(
    session_manifest_path: Path | None, *, backend: BackendKind
) -> Path:
    if session_manifest_path is None:
        raise SessionManifestError(f"backend={backend} requires a resolved session manifest path.")
    return session_manifest_path.resolve()


def _resume_cao_state(
    payload: SessionManifestPayloadV2 | None,
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
    if not terminal_id:
        raise SessionManifestError("CAO session manifest missing or blank cao.terminal_id")

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
    if not isinstance(backend_parsing_mode, str) or not backend_parsing_mode.strip():
        raise SessionManifestError(
            "CAO session manifest missing or blank backend_state.parsing_mode"
        )
    if parsing_mode != backend_parsing_mode.strip():
        raise SessionManifestError(
            "CAO session manifest parsing_mode mismatch: "
            "cao.parsing_mode must equal backend_state.parsing_mode"
        )

    tmux_window_name: str | None = None
    if cao.tmux_window_name is not None:
        tmux_window_name = cao.tmux_window_name.strip()

    backend_tmux_window_name = payload.backend_state.get("tmux_window_name")
    if backend_tmux_window_name is not None:
        if not isinstance(backend_tmux_window_name, str) or not backend_tmux_window_name.strip():
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
    payload: SessionManifestPayloadV2,
) -> MailboxResolvedConfig | None:
    try:
        return resolved_mailbox_config_from_payload(payload.launch_plan.mailbox)
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


def _resolve_agent_identity_from_tmux_local(
    *,
    canonical_agent_identity: str,
    explicit_agent_def_dir: Path | None,
    warnings: tuple[str, ...],
) -> AgentIdentityResolution:
    """Resolve a control target from tmux-local discovery pointers."""

    manifest_path = _resolve_manifest_path_from_tmux_session(session_name=canonical_agent_identity)
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

    record = resolve_live_agent_record(canonical_agent_identity)
    if record is None:
        return None

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
        session_name=canonical_agent_identity,
    )

    return AgentIdentityResolution(
        session_manifest_path=manifest_path,
        canonical_agent_identity=canonical_agent_identity,
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
    record: LiveAgentRegistryRecordV1,
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


def _persisted_tmux_session_name(*, payload: SessionManifestPayloadV2, manifest_path: Path) -> str:
    if payload.backend == "cao_rest":
        cao = payload.cao
        if cao is None:
            raise SessionManifestError(
                f"Resolved manifest mismatch: `{manifest_path}` is missing `cao` payload."
            )
        persisted = cao.session_name.strip()
        if not persisted:
            raise SessionManifestError(
                f"Resolved manifest mismatch: `{manifest_path}` has blank "
                "`payload.cao.session_name`."
            )
        return persisted

    persisted_backend = payload.backend_state.get("tmux_session_name")
    if not isinstance(persisted_backend, str) or not persisted_backend.strip():
        raise SessionManifestError(
            f"Resolved manifest mismatch: `{manifest_path}` is missing non-empty "
            "`payload.backend_state.tmux_session_name`."
        )
    return persisted_backend.strip()


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
) -> LiveAgentRegistryRecordV1 | None:
    """Build one shared-registry record from current runtime-owned session state."""

    if not controller._is_tmux_backed():
        return None

    session_name = _tmux_session_name_for_controller(controller)
    if session_name is None:
        return None

    canonical_agent_name = canonicalize_registry_agent_name(session_name)
    generation_id = controller.registry_generation_id
    if generation_id is None:
        return None

    published_at = datetime.now(UTC)
    session_root = runtime_owned_session_root_from_manifest_path(controller.manifest_path)
    mailbox = controller.launch_plan.mailbox

    gateway_payload = _shared_registry_gateway_payload(controller)
    mailbox_payload = (
        RegistryMailboxV1(
            transport=mailbox.transport,
            principal_id=mailbox.principal_id,
            address=mailbox.address,
            filesystem_root=str(mailbox.filesystem_root.resolve()),
            bindings_version=mailbox.bindings_version,
        )
        if mailbox is not None
        else None
    )

    return LiveAgentRegistryRecordV1(
        agent_name=canonical_agent_name,
        agent_key=derive_agent_key(canonical_agent_name),
        generation_id=generation_id,
        published_at=published_at.isoformat(timespec="seconds"),
        lease_expires_at=(published_at + DEFAULT_REGISTRY_LEASE_TTL).isoformat(timespec="seconds"),
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
            session_name=canonical_agent_name,
        ),
        gateway=gateway_payload,
        mailbox=mailbox_payload,
    )


def _shared_registry_gateway_payload(
    controller: RuntimeSessionController,
) -> RegistryGatewayV1 | None:
    """Build stable and live gateway metadata for registry publication."""

    paths = gateway_paths_from_manifest_path(controller.manifest_path)
    if paths is None or not paths.attach_path.is_file():
        return None

    host: str | None = None
    port: int | None = None
    state_path: str | None = None
    protocol_version: GatewayProtocolVersion | None = None

    if paths.current_instance_path.is_file():
        try:
            current_instance = load_gateway_current_instance(paths.current_instance_path)
        except SessionManifestError:
            current_instance = None
        if current_instance is not None:
            host = current_instance.host
            port = current_instance.port
            state_path = str(paths.state_path.resolve())
            protocol_version = current_instance.protocol_version

    return RegistryGatewayV1(
        gateway_root=str(paths.gateway_root.resolve()),
        attach_path=str(paths.attach_path.resolve()),
        host=cast(GatewayHost | None, host),
        port=port,
        state_path=state_path,
        protocol_version=protocol_version,
    )


def _tmux_session_name_for_controller(controller: RuntimeSessionController) -> str | None:
    """Return the tmux session name for a runtime controller."""

    if isinstance(controller.backend_session, CaoRestSession):
        return controller.backend_session.state.session_name
    if isinstance(controller.backend_session, HeadlessInteractiveSession):
        return controller.backend_session.state.tmux_session_name
    return controller.agent_identity


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

    Returns
    -------
    GatewayControlResult
        Structured attach outcome for CLI and API callers.
    """

    paths = _require_gateway_paths_for_controller(controller)
    attach_contract = load_attach_contract(paths.attach_path)
    if controller.launch_plan.backend != "cao_rest":
        detail = (
            "Gateway attach is only implemented for runtime-owned backend='cao_rest' "
            f"sessions in v1, got backend={controller.launch_plan.backend!r}."
        )
        return GatewayControlResult(
            status="error",
            action="gateway_attach",
            detail=detail,
            gateway_root=str(paths.gateway_root),
        )

    try:
        host, requested_port = _resolve_gateway_listener(
            paths=paths,
            attach_contract=attach_contract,
            host_override=host_override,
            port_override=port_override,
        )
        resolved_port = _start_gateway_process(
            controller=controller,
            paths=paths,
            host=host,
            port=requested_port,
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
    attach_contract = load_attach_contract(paths.attach_path)
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
    attach_contract = load_attach_contract(paths.attach_path)
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


def _start_gateway_process(
    *,
    controller: RuntimeSessionController,
    paths: GatewayPaths,
    host: GatewayHost,
    port: int,
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

    Returns
    -------
    int
        Resolved live gateway port published by the child process.
    """

    session_name = controller._require_tmux_session_name()
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
                ),
            )
            write_attach_contract(
                paths.attach_path,
                load_attach_contract(paths.attach_path).model_copy(
                    update={"desired_host": host, "desired_port": endpoint.port}
                ),
            )
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
    delete_gateway_current_instance(paths)
    existing_epoch = 0
    try:
        existing_status = load_gateway_status(paths.state_path)
    except SessionManifestError:
        existing_status = None
    if existing_status is not None:
        existing_epoch = existing_status.managed_agent_instance_epoch
    write_gateway_status(
        paths.state_path,
        build_offline_gateway_status(
            attach_contract=attach_contract,
            managed_agent_instance_epoch=existing_epoch,
        ),
    )


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
