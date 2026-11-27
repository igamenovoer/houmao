"""Shared managed-agent discovery and direct-control helpers for `houmao-mgr`."""

from __future__ import annotations

from houmao.agents.realm_controller.gateway_access_runtime import (
    GatewayRuntimeAccess,
    gateway_access_for_manifest,
    load_gateway_access_config,
    owner_gateway_client_binding,
)
from houmao.gateway.access import GatewayAccessError, GatewayClientBinding
from houmao.gateway.deployment import (
    GatewayEndpointDescriptor,
    owner_gateway_base_url,
    validate_gateway_access_config_path,
)
from houmao.gateway.terminal_entry_contracts import (
    GatewayTerminalEntryMode,
    GatewayTerminalEntryTicketV1,
)

from houmao.mailbox.online_models import (
    OnlineAttachRequest,
    OnlineControlFailure,
    OnlineControlRequest,
    OnlineBindingStatus,
)
from houmao.mailbox.online_models import OnlineAuthorityContext
from houmao.mailbox.errors import GatewayMailboxMutationError

from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager, nullcontext
from contextvars import ContextVar
from dataclasses import dataclass, replace
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import shlex
from time import monotonic, sleep
from typing import Any, Literal, TypeVar, cast
import uuid

import click
from pydantic import BaseModel, JsonValue, ValidationError

from houmao.execution.context import execution_is_read_only, validate_execution_owner
from houmao.execution.tmux import TmuxObservationError
from houmao.execution.locators import (
    ExecutorAgentLocatorV1,
    ExecutorLocatorError,
    list_executor_locators,
    resolve_executor_locator,
)
from houmao.execution.models import (
    ExecutionBindingV1,
    ExecutionOperation,
    ExecutionResponseV1,
    JsonObject,
)

from houmao.ag_ui.models import AgUiEventPublishRequest, AgUiEventPublishResponse
from houmao.agents.hermes_profile import HERMES_STANDALONE_RELAUNCH_REFUSAL
from houmao.agents.hermes_profile_cleanup import stop_hermes_from_saved_session
from houmao.agents.mailbox_runtime_models import FilesystemMailboxResolvedConfig, MailboxChannel
from houmao.agents.mailbox_runtime_support import (
    LiveGatewayBindingResolution,
    LiveMailboxesBindingResolution,
    resolve_live_mailbox_binding_from_manifest_path,
    mailboxes_resolved_config_from_payload,
)
from houmao.agents.model_selection import ModelConfig, normalize_model_config
from houmao.agents.realm_controller.agent_identity import normalize_agent_identity_name
from houmao.agents.realm_controller.backends.cao_rest import CaoRestSession
from houmao.agents.realm_controller.backends.dispatch_control import HeadlessDispatchControl
from houmao.agents.realm_controller.backends.headless_base import HeadlessInteractiveSession
from houmao.agents.realm_controller.backends.hermes_native import (
    HermesDeadlineExpired,
    HermesRpcRefused,
)
from houmao.agents.realm_controller.backends.hermes_tui import (
    HermesAdmissionUncertain,
    HermesTuiSession,
)
from houmao.agents.realm_controller.backends.kimi_web import KimiWebSession
from houmao.agents.realm_controller.backends.local_interactive import LocalInteractiveSession
from houmao.agents.realm_controller.backends.dsh_web import DshWebSession, DshWebSessionState
from houmao.agents.realm_controller.backends.service_runtime import ManagedServiceSession
from houmao.agents.realm_controller.web_observation import WebObservation
from houmao.agents.realm_controller.gateway_storage import web_attach_metadata_from_state
from houmao.passive_server.compatibility import (
    gateway_summary_from_status,
)
from houmao.agents.realm_controller.backends.headless_output import (
    HeadlessProvider,
    resolve_headless_provider,
)
from houmao.agents.realm_controller.backends.headless_runner import (
    interrupt_owned_headless_attempt,
    load_headless_turn_events,
)
from houmao.agents.realm_controller.headless_snapshots import (
    HeadlessTurnSnapshot,
    headless_turn_artifacts_root,
    read_headless_turn,
)
from houmao.agents.realm_controller.backends.tmux_runtime import (
    HEADLESS_AGENT_WINDOW_NAME,
    TmuxBackedAuthorityHealth,
    TmuxCommandError,
    kill_tmux_session,
    probe_tmux_backed_authority,
)
from houmao.agents.realm_controller.errors import (
    BackendExecutionError,
    BrainLaunchRuntimeError,
    GatewayHttpError,
    MailboxCommandError,
    RetiredJoinedSessionError,
    SessionManifestError,
)
from houmao.agents.realm_controller.terminal_recovery import (
    OwnerTerminalInspectionUnavailable,
    recorded_tmux_binding,
    require_owned_degraded_tmux_session,
    require_same_recovery_manifest,
    require_same_recovery_record,
    terminal_inspection_unavailable,
)
from houmao.mailbox.services import (
    GatewayMailboxError,
    GatewayMailboxAdapter,
    build_scoped_mailbox_adapter,
    build_gateway_mailbox_adapter,
)
from houmao.agents.realm_controller.gateway_client import GatewayClient, GatewayEndpoint
from houmao.agents.realm_controller.owner_admission import (
    OwnerAdmissionError,
    guard_owner_operation,
    observe_owner_prompt,
    owner_operation_guard_exists,
    reserve_owner_prompt,
)
from houmao.agents.realm_controller.native_refresh import (
    inspect_native_home,
    inspect_native_home_from_manifest,
    observe_common_plugins,
    plan_native_refresh,
)
from houmao.agents.realm_controller.native_refresh_models import (
    CommonPluginObservationV1,
    NativeHomeV1,
    NativeRefreshRequestV1,
    NativeRefreshResultV1,
)
from houmao.agents.realm_controller.gateway_models import (
    GatewayAcceptedRequestV1,
    GatewayControlInputRequestV1,
    GatewayControlInputResultV1,
    GatewayCurrentExecutionMode,
    GatewayMailActionResponseV1,
    GatewayMailArchiveRequestV1,
    GatewayMailAttachmentUploadV1,
    GatewayMailLifecycleResponseV1,
    GatewayMailListResponseV1,
    GatewayMailListRequestV1,
    GatewayMailMarkRequestV1,
    GatewayMailMessageResponseV1,
    GatewayMailMessageRequestV1,
    GatewayMailMoveRequestV1,
    GatewayExecutionOverrideV1,
    GatewayMailAnsweredFilter,
    GatewayMailNotifierContextErrorPolicy,
    GatewayMailNotifierMode,
    GatewayMailNotifierPreNotificationContextAction,
    GatewayMailPostRequestV1,
    GatewayMailNotifierPutV1,
    GatewayMailNotifierStatusV1,
    GatewayMailReplyRequestV1,
    GatewayMailSendRequestV1,
    GatewayMailReadFilter,
    GatewayMailStatusV1,
    GatewayPromptControlErrorV1,
    GatewayPromptAdmissionPolicy,
    GatewayPromptControlRequestV1,
    GatewayPromptControlResultV1,
    GatewayReminderCreateBatchV1,
    GatewayReminderCreateResultV1,
    GatewayReminderDeleteResultV1,
    GatewayReminderListV1,
    GatewayReminderPutV1,
    GatewayReminderV1,
    GatewayRequestPayloadInterruptV1,
    GatewayStatusV1,
    GatewayCurrentInstanceV1,
    GatewayTuiTrackingTimingOverridesV1,
    GatewayWebEntryTicketV1,
)
from houmao.agents.realm_controller.gateway_storage import (
    GatewayPaths,
    build_offline_gateway_status,
    gateway_paths_from_manifest_path,
    load_gateway_current_instance,
    load_gateway_status,
    resolve_internal_gateway_attach_contract,
)
from houmao.agents.realm_controller.mail_commands import (
    MailPromptRequest,
    build_verified_mail_command_result,
    ensure_mailbox_command_ready,
    prepare_mail_prompt,
    run_mail_prompt,
)
from houmao.agents.realm_controller.registry_models import (
    ExternalManagedAgentRegistryRecordV1,
    ManagedAgentRegistryRecordV3,
)
from houmao.agents.realm_controller.registry_storage import (
    global_registry_paths,
    is_live_agent_record_fresh,
    list_external_managed_agent_records,
    load_external_managed_agent_record_by_agent_id,
    load_managed_agent_record_by_agent_id,
    new_external_agent_id,
    new_registry_generation_id,
    publish_external_managed_agent_record,
    publish_managed_agent_record,
    remove_managed_agent_record,
    remove_external_managed_agent_record,
    resolve_external_managed_agent_records_by_name,
    resolve_live_agent_record_by_agent_id,
    resolve_live_agent_records_by_name,
    resolve_managed_agent_records_by_name,
    resolve_relaunchable_managed_agent_record_by_agent_id,
    resolve_relaunchable_managed_agent_records_by_name,
)
from houmao.agents.realm_controller.runtime import (
    RuntimeSessionController,
    dsh_web_processes_have_exited,
    resume_runtime_session,
    resume_stopped_runtime_session,
)
from houmao.agents.realm_controller.models import (
    RelaunchChatSessionSelection,
    SessionControlResult,
    SessionEvent,
)
from houmao.agents.realm_controller.managed_control import (
    MANAGED_STRUCTURED_TUI_BACKENDS,
    terminal_prompt_not_ready_reasons,
)
from houmao.agents.realm_controller.run_modes import RunMode
from houmao.agents.realm_controller.manifest import (
    default_manifest_path,
    load_registry_mode_authority,
    require_registry_mode_authority,
    load_session_manifest,
    parse_session_manifest_payload,
)
from houmao.agents.realm_controller.boundary_models import SessionManifestPayloadV4
from houmao.agents.realm_controller.self_manifest import VerifiedSelfManifest, resolve_self_manifest
from houmao.cao.rest_client import CaoApiError
from houmao.cao.no_proxy import normalize_cao_base_url
from houmao.mailbox import MailboxBootstrapError, load_active_mailbox_registration
from houmao.mailbox.managed import ManagedMailboxOperationError
from houmao.mailbox.models import MailboxChannelStatusV1
from houmao.mailbox.scope import MailScope, MailboxScopeError
from houmao.mailbox.protocol import (
    MailboxNotifyAuth,
    MailboxNotifyBlock,
    OperatorOriginReplyPolicy,
)
from houmao.shared_tui_tracking.ownership import SingleSessionTrackingRuntime
from houmao.gateway.plugins import GatewayPluginConfiguration
from houmao.server.models import (
    HoumaoHeadlessTurnAcceptedResponse,
    HoumaoHeadlessTurnEvent,
    HoumaoHeadlessTurnEventsResponse,
    HoumaoHeadlessTurnRequest,
    HoumaoHeadlessTurnStatusResponse,
    HoumaoManagedAgentActionResponse,
    HoumaoManagedAgentGatewayAttachRequest,
    HoumaoManagedAgentDetailResponse,
    HoumaoManagedAgentGatewayPromptControlRequest,
    HoumaoManagedAgentGatewayRequestCreate,
    HoumaoManagedAgentIdentity,
    HoumaoManagedAgentListResponse,
    HoumaoManagedAgentRequestAcceptedResponse,
    HoumaoManagedAgentStateResponse,
    ManagedAgentLifecycleState,
    ManagedAgentTurnStatus,
    HoumaoTerminalSnapshotHistoryResponse,
    HoumaoTerminalStateResponse,
    HoumaoTrackedSessionIdentity,
)
from houmao.server.pair_client import PairAuthorityClientProtocol

from .common import (
    ManagedAgentScopeContext,
    get_managed_agent_scope_context,
    pair_request,
    require_managed_agent_ref,
    require_supported_houmao_pair,
    resolve_managed_agent_selector,
    resolve_managed_agent_identity,
    resolve_server_base_url,
)
from .mail_receipts import submitted_mail_receipt, verified_mail_receipt
from .managed_agent_observation import observe_selected_agent

_HEADLESS_BACKENDS = frozenset(
    {"claude_headless", "codex_headless", "kimi_headless", "dsh_headless"}
)
_SUPPORTED_LOCAL_TUI_PROCESSES: dict[str, tuple[str, ...]] = {
    "claude": ("claude", "claude-code"),
    "codex": ("codex",),
    "kimi": ("kimi-code", "kimi"),
}
ManagedAgentListState = Literal["active", "stopped", "relaunching", "retired", "all"]
_OWNER_LOCAL_TARGET_SCOPE: ContextVar[bool] = ContextVar("houmao_owner_local_target", default=False)
_ExecutorModel = TypeVar("_ExecutorModel", bound=BaseModel)


@dataclass(frozen=True)
class ManagedAgentTarget:
    """Resolved managed-agent control target."""

    mode: str
    agent_ref: str
    identity: HoumaoManagedAgentIdentity
    client: PairAuthorityClientProtocol | None = None
    controller: RuntimeSessionController | None = None
    record: ManagedAgentRegistryRecordV3 | None = None
    external_record: ExternalManagedAgentRegistryRecordV1 | None = None
    executor_locator: ExecutorAgentLocatorV1 | None = None
    self_manifest: VerifiedSelfManifest | None = None


@dataclass(frozen=True)
class VerifiedRegistryManifest:
    """A selected local manifest verified against its registry record."""

    manifest_path: Path
    payload: SessionManifestPayloadV4
    record: ManagedAgentRegistryRecordV3

    @property
    def agent_id(self) -> str:
        """Return the authoritative agent ID."""

        return self.record.agent_id


class ManifestAuthorityUnavailable(click.ClickException):
    """The selected record is visible but its private manifest cannot be read."""


_VerifiedManifest = VerifiedRegistryManifest | VerifiedSelfManifest
_RunningAgentAuthority = RuntimeSessionController | _VerifiedManifest


class ExecutorGatewayStatusV1(GatewayStatusV1):
    """Qualify owner-loopback gateway coordinates in an operator-facing status view."""

    execution_context: ExecutionBindingV1


@contextmanager
def owner_local_target_scope() -> Iterator[None]:
    """Keep admitted owner dispatch on owner-local records without recursive delegation."""

    token = _OWNER_LOCAL_TARGET_SCOPE.set(True)
    try:
        yield
    finally:
        _OWNER_LOCAL_TARGET_SCOPE.reset(token)


def _execute_executor_operation(
    locator: ExecutorAgentLocatorV1,
    operation: ExecutionOperation,
    arguments: JsonObject | None = None,
) -> ExecutionResponseV1:
    """Enter a saved owner route without exposing its private endpoint on this host."""

    from houmao.execution.router import execute_bound_operation

    return execute_bound_operation(locator, operation, arguments)


def _executor_result(
    locator: ExecutorAgentLocatorV1,
    operation: ExecutionOperation,
    arguments: JsonObject | None = None,
) -> JsonObject:
    """Return only confirmed owner results and preserve transport uncertainty as an error."""

    try:
        response = _execute_executor_operation(locator, operation, arguments)
    except (ValueError, OSError):
        raise click.ClickException(
            f"Execution owner {locator.binding.context_id} is unavailable for agent {locator.agent_id}; no local fallback was attempted."
        ) from None
    if response.outcome != "completed":
        raise click.ClickException(
            f"Execution operation {operation} for agent {locator.agent_id} in context {locator.binding.context_id}: "
            f"{response.error_code or response.outcome}; request={response.request_id}. "
            + (
                "Inspect the owner before any deliberate retry."
                if response.outcome == "indeterminate"
                else "The owner did not admit this operation."
            )
        )
    if response.binding != locator.binding:
        raise click.ClickException(
            "Execution owner returned a mismatched binding; no local fallback was attempted."
        )
    return response.result


def _executor_payload(
    target: ManagedAgentTarget, operation: ExecutionOperation, arguments: JsonObject | None = None
) -> JsonObject:
    """Invoke one finite operation through a resolved executor target."""

    assert target.executor_locator is not None
    return _executor_result(target.executor_locator, operation, arguments)


def _executor_model(
    target: ManagedAgentTarget,
    operation: ExecutionOperation,
    model: type[_ExecutorModel],
    arguments: JsonObject | None = None,
) -> _ExecutorModel:
    """Validate owner data through the maintained response model without coercing authority."""

    payload = _executor_payload(target, operation, arguments)
    try:
        return model.model_validate_json(json.dumps(payload))
    except (ValidationError, ValueError):
        raise click.ClickException(
            "Execution owner returned an incompatible operation result."
        ) from None


def _executor_gateway_status(
    target: ManagedAgentTarget, operation: ExecutionOperation, arguments: JsonObject | None = None
) -> GatewayStatusV1:
    """Keep a foreign gateway's loopback endpoint qualified by its execution owner."""

    status = _executor_model(target, operation, GatewayStatusV1, arguments)
    assert target.executor_locator is not None
    return ExecutorGatewayStatusV1.model_validate_json(
        json.dumps(
            {
                **status.model_dump(mode="json"),
                "execution_context": target.executor_locator.binding.model_dump(mode="json"),
            }
        )
    )


def _qualify_executor_identity(
    identity: HoumaoManagedAgentIdentity, locator: ExecutorAgentLocatorV1
) -> HoumaoManagedAgentIdentity:
    """Mark foreign paths/endpoints as owner-context data rather than local authority."""

    if identity.agent_id != locator.agent_id:
        raise click.ClickException("Execution owner returned a different logical agent identity.")
    if (identity.tool, identity.mode, identity.backend) != (
        locator.tool,
        locator.mode,
        locator.backend,
    ):
        raise click.ClickException(
            "Execution owner run mode differs from the locator. Reconcile the owner before retrying."
        )
    return identity.model_copy(
        update={
            "management_kind": "executor_managed",
            "lifecycle_owner": "executor",
            "execution_context": locator.binding,
            "execution_status": "available",
        }
    )


def _executor_identity(locator: ExecutorAgentLocatorV1) -> HoumaoManagedAgentIdentity:
    """Read current owner identity without reconstructing its manifest on the caller host."""

    payload = _executor_result(locator, "describe")
    try:
        identity = HoumaoManagedAgentIdentity.model_validate_json(
            json.dumps(payload.get("identity"))
        )
    except (ValueError, ValidationError):
        raise click.ClickException(
            "Execution owner did not return a valid managed-agent identity."
        ) from None
    return _qualify_executor_identity(identity, locator)


def _resolve_executor_target_for_selector(
    *, agent_id: str | None, agent_name: str | None, mail_discovery: bool = False
) -> ManagedAgentTarget | None:
    """Resolve delegated locators before local probes and reject cross-context ambiguity."""

    if _OWNER_LOCAL_TARGET_SCOPE.get():
        return None
    try:
        locator = resolve_executor_locator(agent_id=agent_id, agent_name=agent_name)
    except (ExecutorLocatorError, OSError) as exc:
        raise click.ClickException(str(exc)) from None
    if locator is None:
        return None
    local_matches = (
        (
            (record,)
            if (record := load_managed_agent_record_by_agent_id(locator.agent_id)) is not None
            else ()
        )
        if agent_id is not None
        else resolve_managed_agent_records_by_name(cast(str, agent_name))
    )
    for record in local_matches:
        if record.agent_id != locator.agent_id or record.execution_binding != locator.binding:
            raise click.ClickException(
                f"Managed-agent selector is ambiguous or has conflicting execution owners: {record.agent_id}, {locator.agent_id}. Select a non-conflicting authoritative agent ID."
            )
    if mail_discovery and local_matches:
        published = local_matches[0]
        identity = _qualify_executor_identity(_identity_from_record(published), locator)
        return ManagedAgentTarget(
            mode="executor",
            agent_ref=locator.agent_id,
            identity=identity.model_copy(update={"execution_status": "unverified"}),
            executor_locator=locator,
            record=published,
        )
    return ManagedAgentTarget(
        mode="executor",
        agent_ref=locator.agent_id,
        identity=_executor_identity(locator),
        executor_locator=locator,
    )


def _qualify_executor_home(home: NativeHomeV1, target: ManagedAgentTarget) -> NativeHomeV1:
    """Add owner context to an existing native-home contract without changing native authority."""

    assert target.executor_locator is not None
    binding = target.executor_locator.binding
    if home.agent_id != target.executor_locator.agent_id:
        raise click.ClickException("Execution owner returned a different agent's native home.")
    return home.model_copy(
        update={
            "identity": {
                **home.identity,
                "execution_context_id": binding.context_id,
                "execution_host_id": binding.host_id,
                "execution_owner": binding.account,
                "execution_uid": str(binding.uid),
                "execution_gid": str(binding.gid),
            }
        }
    )


class GatewayPromptControlCliError(RuntimeError):
    """Structured CLI failure raised by gateway direct prompt control."""

    def __init__(self, payload: GatewayPromptControlErrorV1) -> None:
        self.payload = payload
        super().__init__(payload.detail)


class HermesManagerPromptRefused(click.ClickException):
    """Report a definite native prompt refusal before any accepted handoff."""

    def __init__(self, code: str, detail: str) -> None:
        """Retain the refusal reason across the delegated execution boundary."""

        self.code = code
        super().__init__(detail)


def _target_uses_pair_api(target: ManagedAgentTarget) -> bool:
    """Return whether the target routes communication through a pair API client."""

    return target.mode in {"server", "external"}


def _external_identity_from_record(
    record: ExternalManagedAgentRegistryRecordV1,
) -> HoumaoManagedAgentIdentity:
    """Project one external registry record into the shared identity payload."""

    return record.cached_identity.model_copy(
        update={
            "tracked_agent_id": record.external_agent_id,
            "agent_name": record.local_name,
            "agent_id": record.external_agent_id,
            "session_name": None,
            "tmux_session_name": None,
            "tmux_window_name": None,
            "manifest_path": None,
            "session_root": None,
            "management_kind": "external_communication_only",
            "lifecycle_owner": "remote",
            "external_agent_id": record.external_agent_id,
            "remote_pair_api_base_url": record.pair_api_base_url,
            "remote_agent_ref": record.remote_agent_ref,
        }
    )


def _annotate_external_remote_identity(
    identity: HoumaoManagedAgentIdentity,
    record: ExternalManagedAgentRegistryRecordV1,
) -> HoumaoManagedAgentIdentity:
    """Annotate a remote identity with local external-target locator metadata."""

    return identity.model_copy(
        update={
            "tracked_agent_id": record.external_agent_id,
            "agent_name": record.local_name,
            "agent_id": record.external_agent_id,
            "management_kind": "external_communication_only",
            "lifecycle_owner": "remote",
            "external_agent_id": record.external_agent_id,
            "remote_pair_api_base_url": record.pair_api_base_url,
            "remote_agent_ref": record.remote_agent_ref,
        }
    )


def _external_unsupported_message(
    target: ManagedAgentTarget,
    *,
    operation: str,
    hint: str | None = None,
) -> str:
    """Return one actionable unsupported-operation message for an external target."""

    record = target.external_record
    local_name = record.local_name if record is not None else target.identity.agent_name
    remote_base_url = (
        record.pair_api_base_url if record is not None else target.identity.remote_pair_api_base_url
    )
    remote_ref = record.remote_agent_ref if record is not None else target.identity.remote_agent_ref
    supported = (
        "agents global list, agents single ... state, agents single ... prompt, "
        "agents single ... interrupt, agents single ... gateway status, "
        "agents single ... gateway prompt, agents single ... gateway interrupt, "
        "and supported agents single ... mail commands"
    )
    detail = (
        f"`{operation}` is unsupported for external communication-only managed agent "
        f"`{local_name or target.agent_ref}`. Lifecycle is owned by the remote Houmao "
        f"authority `{remote_base_url or '<unknown>'}` for remote agent "
        f"`{remote_ref or target.agent_ref}`. Supported local operations: {supported}."
    )
    if hint is not None:
        detail = f"{detail} {hint}"
    return detail


def _raise_external_unsupported(
    target: ManagedAgentTarget,
    *,
    operation: str,
    hint: str | None = None,
) -> None:
    """Raise a clear unsupported-operation error for one external target."""

    if target.mode != "external":
        return
    raise click.ClickException(
        _external_unsupported_message(target, operation=operation, hint=hint)
    )


def _require_live_local_controller(
    target: ManagedAgentTarget,
    *,
    operation: str,
    existing_only: bool = False,
) -> RuntimeSessionController:
    """Return the local runtime controller or raise one operator-facing diagnostic."""

    existing_only = existing_only or target.identity.backend in MANAGED_STRUCTURED_TUI_BACKENDS
    if target.mode == "executor":
        raise click.ClickException(
            f"Operation {operation!r} is unsupported through the finite execution transport; no local fallback was attempted."
        )
    if target.controller is not None:
        return target.controller
    if target.self_manifest is not None:
        authority = target.self_manifest
        try:
            if existing_only:
                controller = resume_runtime_session(
                    session_manifest_path=authority.path, existing_only=True
                )
            else:
                controller = resume_runtime_session(
                    session_manifest_path=authority.path, read_only=True
                )
        except (OSError, RuntimeError, ValueError) as exc:
            raise click.ClickException(str(exc)) from exc
        if (
            controller.agent_id != authority.agent_id
            or controller.registry_generation_id != authority.record.generation_id
        ):
            raise click.ClickException("The managed runtime changed during self resolution.")
        return controller
    if target.mode == "local" and target.record is not None:
        selected_authority = read_selected_manifest(target)
        controller = _resume_controller_from_record(target.record, existing_only=existing_only)
        if (
            controller.agent_id != selected_authority.agent_id
            or controller.registry_generation_id != selected_authority.record.generation_id
            or controller.execution_binding != selected_authority.payload.runtime.execution_binding
        ):
            raise click.ClickException(
                f"The managed runtime for `{selected_authority.agent_id}` changed during controller acquisition."
            )
        return controller
    raise click.ClickException(
        _format_unavailable_local_controller_message(target=target, operation=operation)
    )


def read_selected_manifest(target: ManagedAgentTarget) -> _VerifiedManifest:
    """Read and verify one selected owner's manifest without opening a controller."""

    if target.self_manifest is not None:
        return target.self_manifest
    record = target.record
    if target.mode != "local" or record is None:
        raise ManifestAuthorityUnavailable(
            _format_unavailable_local_controller_message(
                target=target, operation="read the saved runtime manifest"
            )
        )
    try:
        validate_execution_owner(record.execution_binding)
    except (RuntimeError, ValueError) as exc:
        raise ManifestAuthorityUnavailable(
            f"Saved runtime authority for `{record.agent_id}` requires its recorded execution owner."
        ) from exc
    path = Path(record.runtime.manifest_path).expanduser()
    try:
        if not path.is_absolute() or path.resolve() != path:
            raise click.ClickException(
                f"Saved manifest path for `{record.agent_id}` is outside its recorded authority."
            )
        if record.runtime.session_root is not None and path.parent != Path(
            record.runtime.session_root
        ):
            raise click.ClickException(
                f"Saved manifest path for `{record.agent_id}` differs from its recorded session root."
            )
        if not path.is_file():
            raise ManifestAuthorityUnavailable(
                f"Saved runtime manifest for `{record.agent_id}` is unavailable."
            )
        payload = load_registry_mode_authority(record)
        tmux = payload.tmux
        if (
            record.lifecycle.state == "active"
            and tmux is not None
            and (
                tmux.session_name != record.terminal.current_session_name
                or (
                    record.terminal.socket_path is not None
                    and tmux.socket_path != record.terminal.socket_path
                )
            )
        ):
            raise SessionManifestError("Registry and manifest terminal bindings differ.")
    except OSError as exc:
        raise ManifestAuthorityUnavailable(
            f"Saved runtime manifest for `{record.agent_id}` is unavailable."
        ) from exc
    except SessionManifestError as exc:
        if isinstance(exc.__cause__, OSError) or not path.is_file():
            raise ManifestAuthorityUnavailable(
                f"Saved runtime manifest for `{record.agent_id}` is unavailable."
            ) from exc
        raise click.ClickException(
            f"Cannot verify saved runtime authority for `{record.agent_id}`: {exc}"
        ) from exc
    return VerifiedRegistryManifest(manifest_path=path, payload=payload, record=record)


def _running_agent_authority(
    target: ManagedAgentTarget, *, operation: str
) -> _RunningAgentAuthority:
    """Select the authorized manifest or honor an already-acquired controller."""

    if target.self_manifest is not None:
        return target.self_manifest
    if target.mode == "local" and target.record is not None and target.controller is None:
        return read_selected_manifest(target)
    return _require_live_local_controller(target, operation=operation)


def _read_running_agent_manifest(authority: _RunningAgentAuthority) -> SessionManifestPayloadV4:
    """Read current bindings while keeping a resolved self command on its generation."""

    if isinstance(authority, VerifiedRegistryManifest):
        return authority.payload
    if isinstance(authority, VerifiedSelfManifest) and authority.path.resolve() != authority.path:
        raise click.ClickException("The managed manifest changed during self resolution.")
    handle = load_session_manifest(authority.manifest_path)
    payload = parse_session_manifest_payload(handle.payload, source=str(handle.path))
    if isinstance(authority, VerifiedSelfManifest) and (
        payload.agent_id != authority.agent_id
        or payload.registry_generation_id != authority.record.generation_id
        or payload.runtime.execution_binding != authority.payload.runtime.execution_binding
    ):
        raise click.ClickException("The managed runtime changed during self resolution.")
    return payload


def _format_unavailable_local_controller_message(
    target: ManagedAgentTarget,
    *,
    operation: str,
) -> str:
    """Format one unavailable local runtime-authority diagnostic."""

    record = target.record
    agent_name = (
        getattr(record, "agent_name", None) or target.identity.agent_name or target.agent_ref
    )
    agent_id = getattr(record, "agent_id", None) or target.identity.agent_id
    lifecycle = getattr(record, "lifecycle", None)
    lifecycle_state = getattr(lifecycle, "state", None) or target.identity.lifecycle_state
    terminal = getattr(record, "terminal", None)
    tmux_session_name = (
        getattr(terminal, "session_name", None)
        or getattr(terminal, "current_session_name", None)
        or target.identity.tmux_session_name
    )
    runtime = getattr(record, "runtime", None)
    manifest_path = getattr(runtime, "manifest_path", None) or target.identity.manifest_path
    session_root = getattr(runtime, "session_root", None) or target.identity.session_root

    if target.mode == "local_stale":
        cause = (
            "The shared registry still says this local managed agent is active, but its "
            "tmux-backed runtime authority is stale or missing."
        )
    elif target.mode == "local_degraded":
        cause = (
            "The shared registry still says this local managed agent is active, but its "
            "tmux-backed runtime authority is degraded and missing the primary window or pane."
        )
    elif target.mode == "local_stopped":
        cause = "This managed agent is stopped and does not have a live local runtime authority."
    elif _target_uses_pair_api(target):
        cause = (
            "This target is resolved through a pair authority and does not provide a local "
            "runtime controller on this host."
        )
    else:
        cause = (
            f"This target resolved as mode `{target.mode}` but does not provide a live local "
            "runtime controller."
        )

    evidence = _format_local_authority_evidence(
        agent_id=agent_id,
        lifecycle_state=lifecycle_state,
        tmux_session_name=tmux_session_name,
        manifest_path=manifest_path,
        session_root=session_root,
    )
    recovery = _format_local_authority_recovery_hint(agent_id=agent_id, agent_name=agent_name)
    return "\n".join(
        part
        for part in (
            f"Cannot {operation} for managed agent `{agent_name}`.",
            cause,
            evidence,
            recovery,
        )
        if part
    )


def _format_local_authority_evidence(
    *,
    agent_id: str | None,
    lifecycle_state: str | None,
    tmux_session_name: str | None,
    manifest_path: str | None,
    session_root: str | None,
) -> str:
    """Return concise evidence for one unavailable local runtime authority."""

    fields = [
        ("agent_id", agent_id),
        ("lifecycle_state", lifecycle_state),
        ("tmux_session", tmux_session_name),
        ("manifest_path", manifest_path),
        ("session_root", session_root),
    ]
    rendered = [f"{name}=`{value}`" for name, value in fields if value]
    return f"Evidence: {'; '.join(rendered)}." if rendered else ""


def _format_local_authority_recovery_hint(
    *,
    agent_id: str | None,
    agent_name: str | None,
) -> str:
    """Return maintained recovery commands for one unavailable local authority."""

    if agent_id:
        selector = f"--agent-id {shlex.quote(agent_id)}"
    elif agent_name:
        selector = f"--agent-name {shlex.quote(agent_name)}"
    else:
        return (
            "Next: run `houmao-mgr agents global list` to inspect managed agents, or "
            "`houmao-mgr admin cleanup registry --dry-run` to inspect stale registry records."
        )
    return (
        f"Next: run `houmao-mgr agents single {selector} stop` to recover or retire the "
        f"broken active record, `houmao-mgr agents single {selector} relaunch` if the agent "
        "is relaunchable, or `houmao-mgr admin cleanup registry --dry-run` to inspect stale "
        "registry records."
    )


@dataclass(frozen=True)
class _LocalManagedAgentSelectorMiss:
    """One preserved local friendly-name selector miss."""

    agent_name: str
    alias_match: ManagedAgentRegistryRecordV3 | None = None


@dataclass(frozen=True)
class _BrokenActiveRecoveryResult:
    """Outcome of reconciling one broken active local lifecycle record."""

    record: ManagedAgentRegistryRecordV3 | None
    manifest_path: str | None
    session_root: str | None
    detail: str
    retired: bool = False


def _resolve_execution_model_override(
    *,
    model: str | None,
    reasoning_level: int | None,
) -> ModelConfig | None:
    """Normalize one request-scoped execution override from CLI flags."""

    if model is not None and not model.strip():
        raise click.ClickException("`--model` must not be empty.")
    try:
        return normalize_model_config(name=model, reasoning_level=reasoning_level)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc


def _execution_override_payload(
    model_config: ModelConfig | None,
) -> GatewayExecutionOverrideV1 | None:
    """Build one request payload from a normalized execution override."""

    return GatewayExecutionOverrideV1.from_model_config(model_config)


def _require_headless_execution_override_target(
    *,
    target: ManagedAgentTarget,
    execution_model: ModelConfig | None,
) -> None:
    """Reject request-scoped execution overrides for non-headless targets."""

    if execution_model is None:
        return
    if target.identity.transport == "headless":
        return
    raise click.ClickException(
        "Execution overrides are only supported for headless managed-agent prompt routes."
    )


def list_managed_agents(
    *,
    port: int | None,
    lifecycle_state: ManagedAgentListState = "active",
) -> HoumaoManagedAgentListResponse:
    """List managed agents from the registry first, with optional server enrichment."""

    if port is not None:
        if lifecycle_state not in {"active", "all"}:
            raise click.ClickException(
                f"`--state {lifecycle_state}` is only supported for local registry-backed listing without `--port`."
            )
        client = require_supported_houmao_pair(base_url=resolve_server_base_url(port=port))
        return pair_request(client.list_managed_agents)

    merged: dict[str, HoumaoManagedAgentIdentity] = {}
    registry_identities = (
        _list_registry_identities()
        if lifecycle_state == "active"
        else _list_registry_identities(lifecycle_state=lifecycle_state)
    )
    for identity in registry_identities:
        merged[_identity_merge_key(identity)] = identity
    if not _OWNER_LOCAL_TARGET_SCOPE.get():
        for locator in list_executor_locators():
            local_record = load_managed_agent_record_by_agent_id(locator.agent_id)
            if local_record is not None and local_record.execution_binding != locator.binding:
                raise click.ClickException(
                    f"Agent ID {locator.agent_id} has conflicting local and executor ownership."
                )
            try:
                identity = _executor_identity(locator)
            except click.ClickException:
                if lifecycle_state != "all":
                    continue
                identity = HoumaoManagedAgentIdentity(
                    tracked_agent_id=locator.agent_id,
                    agent_id=locator.agent_id,
                    agent_name=locator.agent_name,
                    transport="unknown",
                    tool=locator.tool,
                    mode=locator.mode,
                    backend=locator.backend,
                    management_kind="executor_managed",
                    lifecycle_owner="executor",
                    execution_context=locator.binding,
                    execution_status="unavailable",
                )
            if lifecycle_state != "all" and identity.lifecycle_state != lifecycle_state:
                continue
            merged[_identity_merge_key(identity)] = identity
    if lifecycle_state in {"active", "all"}:
        for record in list_external_managed_agent_records():
            identity = _external_identity_from_record(record)
            merged[_identity_merge_key(identity)] = identity

    pair_client: PairAuthorityClientProtocol | None = (
        _optional_pair_client(base_url=resolve_server_base_url())
        if lifecycle_state in {"active", "all"}
        else None
    )
    if pair_client is not None:
        for identity in pair_request(pair_client.list_managed_agents).agents:
            existing_identity = merged.get(_identity_merge_key(identity))
            if (
                existing_identity is not None
                and existing_identity.management_kind == "executor_managed"
            ):
                continue
            merged[_identity_merge_key(identity)] = identity

    identities = sorted(merged.values(), key=lambda item: (item.transport, item.tracked_agent_id))
    return HoumaoManagedAgentListResponse(agents=identities)


def register_external_managed_agent(
    *,
    local_name: str,
    api_base_url: str,
    agent_ref: str,
    gateway_expected: bool = False,
    replace: bool = False,
) -> dict[str, Any]:
    """Register one remote managed agent as a local communication-only target."""

    _, normalized_name = resolve_managed_agent_selector(
        agent_id=None,
        agent_name=local_name,
    )
    assert normalized_name is not None
    normalized_ref = require_managed_agent_ref(agent_ref)
    normalized_base_url = _normalize_external_pair_api_base_url(api_base_url)
    _raise_if_external_registration_collides_with_local(local_name=normalized_name)

    existing_matches = resolve_external_managed_agent_records_by_name(normalized_name)
    if len(existing_matches) > 1:
        raise click.ClickException(
            "External managed-agent registration is ambiguous for local name "
            f"`{normalized_name}`. Remove duplicate external records manually before retrying."
        )
    existing = existing_matches[0] if existing_matches else None
    if existing is not None and not replace:
        raise click.ClickException(
            "External managed-agent "
            f"`{normalized_name}` is already registered as `{existing.external_agent_id}`. "
            "Use `--replace` to update that external import."
        )

    identity, gateway_status = _verify_external_remote_target(
        base_url=normalized_base_url,
        agent_ref=normalized_ref,
        gateway_expected=gateway_expected,
    )
    now = _now_utc_iso()
    record = ExternalManagedAgentRegistryRecordV1(
        local_name=normalized_name,
        external_agent_id=existing.external_agent_id
        if existing is not None
        else new_external_agent_id(),
        generation_id=new_registry_generation_id(),
        pair_api_base_url=normalized_base_url,
        remote_agent_ref=normalized_ref,
        gateway_expected=gateway_expected,
        created_at_utc=existing.created_at_utc if existing is not None else now,
        updated_at_utc=now,
        verified_at_utc=now,
        cached_identity=identity,
    )
    try:
        published = publish_external_managed_agent_record(record)
    except SessionManifestError as exc:
        raise click.ClickException(str(exc)) from exc

    return _external_agent_action_payload(
        action="registered" if existing is None else "replaced",
        record=published,
        gateway_status=gateway_status,
    )


def list_external_managed_agents() -> dict[str, object]:
    """List locally registered external communication-only managed agents."""

    return {
        "external_agents": [
            _external_agent_record_payload(record)
            for record in sorted(
                list_external_managed_agent_records(),
                key=lambda item: (item.local_name, item.external_agent_id),
            )
        ],
    }


def get_external_managed_agent(
    *,
    agent_id: str | None,
    agent_name: str | None,
) -> dict[str, object]:
    """Return one external communication-only managed-agent registry record."""

    record = _resolve_external_record_for_cli(agent_id=agent_id, agent_name=agent_name)
    return {"external_agent": _external_agent_record_payload(record)}


def verify_external_managed_agent(
    *,
    agent_id: str | None,
    agent_name: str | None,
) -> dict[str, object]:
    """Verify one external managed-agent authority and refresh its cached identity."""

    record = _resolve_external_record_for_cli(agent_id=agent_id, agent_name=agent_name)
    identity, gateway_status = _verify_external_remote_target(
        base_url=record.pair_api_base_url,
        agent_ref=record.remote_agent_ref,
        gateway_expected=record.gateway_expected,
    )
    now = _now_utc_iso()
    refreshed = record.model_copy(
        update={
            "generation_id": new_registry_generation_id(),
            "updated_at_utc": now,
            "verified_at_utc": now,
            "cached_identity": identity,
        }
    )
    try:
        published = publish_external_managed_agent_record(refreshed)
    except SessionManifestError as exc:
        raise click.ClickException(str(exc)) from exc
    return _external_agent_action_payload(
        action="verified",
        record=published,
        gateway_status=gateway_status,
    )


def remove_external_managed_agent(
    *,
    agent_id: str | None,
    agent_name: str | None,
) -> dict[str, object]:
    """Remove one local external managed-agent import without remote side effects."""

    record = _resolve_external_record_for_cli(agent_id=agent_id, agent_name=agent_name)
    try:
        removed = remove_external_managed_agent_record(
            record.external_agent_id,
            generation_id=record.generation_id,
        )
    except SessionManifestError as exc:
        raise click.ClickException(str(exc)) from exc
    if not removed:
        raise click.ClickException(
            "External managed-agent "
            f"`{record.local_name}` changed before removal. Reload and retry."
        )
    return {
        "action": "removed",
        "removed": True,
        "remote_lifecycle_untouched": True,
        "external_agent": _external_agent_record_payload(record),
    }


def _normalize_external_pair_api_base_url(value: str) -> str:
    """Normalize an external pair API base URL or raise a Click error."""

    try:
        return normalize_cao_base_url(value)
    except ValueError as exc:
        raise click.ClickException(f"`--api-base-url` {exc}") from exc


def _raise_if_external_registration_collides_with_local(*, local_name: str) -> None:
    """Reject external imports that would shadow local lifecycle registry records."""

    local_matches = resolve_managed_agent_records_by_name(local_name)
    if not local_matches:
        return
    matched_ids = ", ".join(sorted(record.agent_id for record in local_matches))
    raise click.ClickException(
        "External managed-agent local name "
        f"`{local_name}` conflicts with local lifecycle registry record(s): {matched_ids}. "
        "Local lifecycle records take precedence; choose a different external `--name`."
    )


def _verify_external_remote_target(
    *,
    base_url: str,
    agent_ref: str,
    gateway_expected: bool,
) -> tuple[HoumaoManagedAgentIdentity, GatewayStatusV1 | None]:
    """Verify the remote pair authority and resolve the referenced managed agent."""

    client = require_supported_houmao_pair(base_url=base_url)
    identity = resolve_managed_agent_identity(client, agent_ref=agent_ref)
    gateway_status: GatewayStatusV1 | None = None
    if gateway_expected:
        gateway_status = pair_request(client.get_managed_agent_gateway_status, agent_ref)
    return identity, gateway_status


def _resolve_external_record_for_cli(
    *,
    agent_id: str | None,
    agent_name: str | None,
) -> ExternalManagedAgentRegistryRecordV1:
    """Resolve exactly one external record from shared CLI selector options."""

    normalized_agent_id, normalized_agent_name = resolve_managed_agent_selector(
        agent_id=agent_id,
        agent_name=agent_name,
    )
    record = _resolve_external_managed_agent_record_for_selector(
        agent_id=normalized_agent_id,
        agent_name=normalized_agent_name,
    )
    if record is not None:
        return record
    selector_name = "--agent-id" if normalized_agent_id is not None else "--agent-name"
    selector_value = normalized_agent_id or normalized_agent_name
    raise click.ClickException(
        f"No external communication-only managed agent matches {selector_name} `{selector_value}`."
    )


def _resolve_external_managed_agent_record_for_selector(
    *,
    agent_id: str | None,
    agent_name: str | None,
) -> ExternalManagedAgentRegistryRecordV1 | None:
    """Resolve one external record by external id or local external name."""

    if agent_id is not None:
        try:
            return load_external_managed_agent_record_by_agent_id(agent_id)
        except SessionManifestError as exc:
            raise click.ClickException(str(exc)) from exc
    if agent_name is None:
        return None
    matches = resolve_external_managed_agent_records_by_name(agent_name)
    if len(matches) > 1:
        raise click.ClickException(
            f"External managed-agent name `{agent_name}` is ambiguous across "
            f"{len(matches)} records. Use `--agent-id`."
        )
    if len(matches) == 1:
        return matches[0]
    return None


def _external_target_from_record(
    record: ExternalManagedAgentRegistryRecordV1,
) -> ManagedAgentTarget:
    """Build a communication-only target from one external registry record."""

    client = require_supported_houmao_pair(base_url=record.pair_api_base_url)
    return ManagedAgentTarget(
        mode="external",
        agent_ref=record.remote_agent_ref,
        identity=_external_identity_from_record(record),
        client=client,
        external_record=record,
    )


def _external_agent_action_payload(
    *,
    action: str,
    record: ExternalManagedAgentRegistryRecordV1,
    gateway_status: GatewayStatusV1 | None = None,
) -> dict[str, object]:
    """Return one stable external-agent action payload."""

    payload: dict[str, object] = {
        "action": action,
        "external_agent": _external_agent_record_payload(record),
    }
    if gateway_status is not None:
        payload["gateway"] = gateway_status.model_dump(mode="json")
        payload["gateway_available"] = True
    elif record.gateway_expected:
        payload["gateway_available"] = False
    return payload


def _external_agent_record_payload(
    record: ExternalManagedAgentRegistryRecordV1,
) -> dict[str, object]:
    """Return one concise external-agent registry payload for CLI output."""

    return {
        "local_name": record.local_name,
        "external_agent_id": record.external_agent_id,
        "kind": record.kind,
        "lifecycle_owner": record.lifecycle_owner,
        "pair_api_base_url": record.pair_api_base_url,
        "remote_agent_ref": record.remote_agent_ref,
        "gateway_expected": record.gateway_expected,
        "created_at_utc": record.created_at_utc,
        "updated_at_utc": record.updated_at_utc,
        "verified_at_utc": record.verified_at_utc,
        "cached_identity": _external_identity_from_record(record).model_dump(mode="json"),
    }


def _now_utc_iso() -> str:
    """Return a compact UTC timestamp for registry records."""

    return datetime.now(UTC).isoformat(timespec="seconds")


def resolve_managed_agent_target(
    *,
    agent_id: str | None,
    agent_name: str | None,
    port: int | None,
    include_inactive: bool = False,
    mail_discovery: bool = False,
) -> ManagedAgentTarget:
    """Resolve one managed-agent target through registry-first discovery."""

    scoped_target = _resolve_target_from_scope_context(
        agent_id=agent_id,
        agent_name=agent_name,
        port=port,
        operation_family="agents single/self",
    )
    if isinstance(scoped_target, ManagedAgentTarget):
        return scoped_target
    if scoped_target is not None:
        agent_id = scoped_target.agent_id
        agent_name = scoped_target.agent_name

    normalized_agent_id, normalized_agent_name = resolve_managed_agent_selector(
        agent_id=agent_id,
        agent_name=agent_name,
    )
    normalized_ref = normalized_agent_id or normalized_agent_name
    assert normalized_ref is not None
    if port is not None:
        client = require_supported_houmao_pair(base_url=resolve_server_base_url(port=port))
        identity = resolve_managed_agent_identity(client, agent_ref=normalized_ref)
        return ManagedAgentTarget(
            mode="server",
            agent_ref=normalized_ref,
            identity=identity,
            client=client,
        )

    executor_target = _resolve_executor_target_for_selector(
        agent_id=normalized_agent_id,
        agent_name=normalized_agent_name,
        mail_discovery=mail_discovery,
    )
    if executor_target is not None:
        return executor_target

    record, miss_context = _resolve_local_managed_agent_record_with_miss_context(
        agent_id=normalized_agent_id,
        agent_name=normalized_agent_name,
        include_inactive=include_inactive or mail_discovery,
    )
    if record is not None:
        return select_local_managed_agent_record(record, agent_ref=normalized_ref)

    external_record = _resolve_external_managed_agent_record_for_selector(
        agent_id=normalized_agent_id,
        agent_name=normalized_agent_name,
    )
    if external_record is not None:
        return _external_target_from_record(external_record)

    if miss_context is not None:
        return _resolve_default_pair_target_with_local_miss(
            agent_ref=normalized_ref,
            miss_context=miss_context,
        )

    client = require_supported_houmao_pair(base_url=resolve_server_base_url())
    identity = resolve_managed_agent_identity(client, agent_ref=normalized_ref)
    return ManagedAgentTarget(
        mode="server",
        agent_ref=normalized_ref,
        identity=identity,
        client=client,
    )


def resolve_relaunch_managed_agent_target(
    *,
    agent_id: str | None,
    agent_name: str | None,
    port: int | None,
) -> ManagedAgentTarget:
    """Resolve one managed-agent relaunch target, including stopped relaunchable records."""

    scoped_target = _resolve_target_from_scope_context(
        agent_id=agent_id,
        agent_name=agent_name,
        port=port,
        operation_family="agents single relaunch",
    )
    if isinstance(scoped_target, ManagedAgentTarget):
        raise click.ClickException(
            "`agents self relaunch` uses current-session manifest authority only. "
            "Use `houmao-mgr agents self relaunch` for active current-session refresh or "
            "`houmao-mgr agents single --agent-id <id> relaunch` for selected-agent recovery."
        )
    if scoped_target is not None:
        agent_id = scoped_target.agent_id
        agent_name = scoped_target.agent_name

    normalized_agent_id, normalized_agent_name = resolve_managed_agent_selector(
        agent_id=agent_id,
        agent_name=agent_name,
    )
    normalized_ref = normalized_agent_id or normalized_agent_name
    assert normalized_ref is not None
    if port is not None:
        client = require_supported_houmao_pair(base_url=resolve_server_base_url(port=port))
        identity = resolve_managed_agent_identity(client, agent_ref=normalized_ref)
        return ManagedAgentTarget(
            mode="server",
            agent_ref=normalized_ref,
            identity=identity,
            client=client,
        )

    executor_target = _resolve_executor_target_for_selector(
        agent_id=normalized_agent_id, agent_name=normalized_agent_name
    )
    if executor_target is not None:
        return executor_target

    record, miss_context = _resolve_local_relaunch_record_with_miss_context(
        agent_id=normalized_agent_id,
        agent_name=normalized_agent_name,
    )
    if record is not None:
        _require_supported_registry_origin(record)
        if record.lifecycle.state == "stopped":
            return ManagedAgentTarget(
                mode="local",
                agent_ref=normalized_ref,
                identity=_identity_from_record(record),
                record=record,
            )
        if record.identity.backend == "houmao_server_rest":
            raise click.ClickException(
                "This managed agent is registered with retired backend "
                "`houmao_server_rest`. Relaunch it through a maintained local/headless workflow."
            )
        native_tui = record.identity.backend in MANAGED_STRUCTURED_TUI_BACKENDS
        if not native_tui and _is_local_tmux_backed_active_record(record):
            try:
                health = _probe_local_tmux_authority_for_record(record)
            except SessionManifestError as exc:
                raise click.ClickException(str(exc)) from exc
            if health.state == "degraded_missing_primary":
                return ManagedAgentTarget(
                    mode="local_degraded",
                    agent_ref=normalized_ref,
                    identity=_identity_from_record(record),
                    record=record,
                )
            if health.state == "stale_missing_session":
                return ManagedAgentTarget(
                    mode="local_stale",
                    agent_ref=normalized_ref,
                    identity=_identity_from_record(record),
                    record=record,
                )
        controller = _resume_controller_from_record(record, existing_only=native_tui)
        identity = _identity_from_controller(controller)
        return ManagedAgentTarget(
            mode="local",
            agent_ref=normalized_ref,
            identity=identity,
            controller=controller,
            record=record,
        )

    stopped_fallback_target = _resolve_stopped_relaunch_manifest_fallback_target(
        agent_id=normalized_agent_id,
        agent_name=normalized_agent_name,
    )
    if stopped_fallback_target is not None:
        return stopped_fallback_target

    external_record = _resolve_external_managed_agent_record_for_selector(
        agent_id=normalized_agent_id,
        agent_name=normalized_agent_name,
    )
    if external_record is not None:
        return _external_target_from_record(external_record)

    if miss_context is not None:
        return _resolve_default_pair_target_with_local_miss(
            agent_ref=normalized_ref,
            miss_context=miss_context,
        )

    client = require_supported_houmao_pair(base_url=resolve_server_base_url())
    identity = resolve_managed_agent_identity(client, agent_ref=normalized_ref)
    return ManagedAgentTarget(
        mode="server",
        agent_ref=normalized_ref,
        identity=identity,
        client=client,
    )


def resolve_managed_agent_mail_target(
    *,
    agent_id: str | None,
    agent_name: str | None,
    port: int | None,
    mail_discovery: bool = False,
) -> ManagedAgentTarget:
    """Resolve one scoped managed-agent mail target."""

    scoped_target = _resolve_target_from_scope_context(
        agent_id=agent_id,
        agent_name=agent_name,
        port=port,
        operation_family="scoped agents mail",
    )
    if isinstance(scoped_target, ManagedAgentTarget):
        return scoped_target
    if scoped_target is not None:
        agent_id = scoped_target.agent_id
        agent_name = scoped_target.agent_name

    selected_agent_id, selected_agent_name = resolve_managed_agent_selector(
        agent_id=agent_id,
        agent_name=agent_name,
        allow_missing=True,
    )
    if selected_agent_id is not None or selected_agent_name is not None:
        return resolve_managed_agent_target(
            agent_id=selected_agent_id,
            agent_name=selected_agent_name,
            port=port,
            mail_discovery=mail_discovery,
        )

    if port is not None:
        raise click.ClickException(
            "`--port` is only supported with an explicit `--agent-id` or `--agent-name` "
            "`agents single ... mail` target."
        )

    gateway_commands = _gateway_command_helpers()
    session_name = gateway_commands._try_current_tmux_session_name()
    if session_name is None:
        raise click.ClickException(
            "Exactly one of `--agent-id` or `--agent-name` is required unless the command is "
            "run inside the target tmux session."
        )
    resolved_target = gateway_commands._resolve_gateway_current_session_target(
        session_name=session_name
    )
    if resolved_target is None:
        raise click.ClickException(
            "Current tmux session is not registered as a managed agent in the gateway runtime."
        )
    return cast(ManagedAgentTarget, resolved_target)


def resolve_current_session_managed_agent_target() -> ManagedAgentTarget:
    """Resolve one managed self target without constructing its controller."""

    from .agents.self_identity import identity_from_manifest

    try:
        authority = resolve_self_manifest()
    except (OSError, RuntimeError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    if authority.payload.backend == "houmao_server_rest":
        raise click.ClickException(
            "Current-session attach uses retired backend `houmao_server_rest`. "
            "Use `houmao-passive-server` for maintained API-backed management."
        )
    return ManagedAgentTarget(
        mode="local",
        agent_ref=authority.agent_id,
        identity=identity_from_manifest(authority.path, authority.payload),
        record=authority.record,
        self_manifest=authority,
    )


def _resolve_target_from_scope_context(
    *,
    agent_id: str | None,
    agent_name: str | None,
    port: int | None,
    operation_family: str,
) -> ManagedAgentTarget | ManagedAgentScopeContext | None:
    """Apply inherited `agents single` or `agents self` target scope."""

    scope_context = get_managed_agent_scope_context()
    if scope_context is None:
        return None
    if scope_context.scope == "single":
        if agent_id is not None or agent_name is not None:
            return None
        return scope_context

    if agent_id is not None or agent_name is not None:
        raise click.ClickException(
            f"`{operation_family}` is running under `agents self`; explicit `--agent-id` and "
            "`--agent-name` selectors are not supported."
        )
    if port is not None:
        raise click.ClickException(
            f"`{operation_family}` is running under `agents self`; pair-authority port "
            "overrides are not supported because the target is the current managed tmux session."
        )
    return resolve_current_session_managed_agent_target()


def _resolve_local_managed_agent_record(
    *,
    agent_id: str | None,
    agent_name: str | None,
) -> ManagedAgentRegistryRecordV3 | None:
    """Resolve one local registry-backed managed-agent record."""

    record, _ = _resolve_local_managed_agent_record_with_miss_context(
        agent_id=agent_id,
        agent_name=agent_name,
    )
    return record


def resolve_owner_gateway_access(
    *, agent_id: str | None, agent_name: str | None, recovery_manifest: Path | None = None
) -> GatewayRuntimeAccess:
    """Verify detached or stopped owner authority without delegating over HTTP."""

    agent_id, agent_name = resolve_managed_agent_selector(agent_id=agent_id, agent_name=agent_name)
    try:
        if recovery_manifest is not None:
            return _gateway_access_from_recovery_manifest(
                recovery_manifest, agent_id=agent_id, agent_name=agent_name
            )
        record, _ = _resolve_local_managed_agent_record_with_miss_context(
            agent_id=agent_id, agent_name=agent_name, include_inactive=True
        )
        if record is not None:
            require_registry_mode_authority(record)
            access = gateway_access_for_manifest(Path(record.runtime.manifest_path))
            if (
                access.owner.agent_id == record.agent_id
                and access.execution_binding == record.execution_binding
                and access.target.incarnation == record.generation_id
            ):
                return access
    except (OSError, SessionManifestError, ValueError):
        pass
    raise click.ClickException("Gateway access requires verified local execution owner authority.")


def _gateway_access_from_recovery_manifest(
    path: Path, *, agent_id: str | None, agent_name: str | None
) -> GatewayRuntimeAccess:
    """Use a confined owner manifest explicitly for new policy reprovisioning."""

    if (
        not path.is_absolute()
        or path.name != "manifest.json"
        or path.resolve(strict=True) != path
        or not path.is_file()
        or path.stat().st_uid != os.geteuid()
    ):
        raise ValueError("The recovery manifest must be a confined owner file.")
    handle = load_session_manifest(path)
    payload = parse_session_manifest_payload(handle.payload, source="recovery manifest")
    binding = payload.runtime.execution_binding
    if binding is None or path != default_manifest_path(
        Path(binding.runtime_root), payload.backend, path.parent.name
    ):
        raise ValueError("The recovery manifest is outside its bound runtime directory.")
    manifest_name = (
        normalize_agent_identity_name(payload.agent_name).name_portion
        if payload.agent_name
        else None
    )
    if (agent_id is not None and payload.agent_id != agent_id) or (
        agent_name is not None and manifest_name != agent_name
    ):
        raise ValueError("The recovery manifest differs from the selected agent.")
    access = gateway_access_for_manifest(path)
    if (
        access.owner.agent_id != payload.agent_id
        or access.execution_binding != binding
        or access.target.incarnation != payload.registry_generation_id
    ):
        raise ValueError("The recovery manifest changed during owner verification.")
    return access


def _resolve_local_managed_agent_record_with_miss_context(
    *,
    agent_id: str | None,
    agent_name: str | None,
    include_inactive: bool = False,
) -> tuple[ManagedAgentRegistryRecordV3 | None, _LocalManagedAgentSelectorMiss | None]:
    """Resolve one local record and preserve friendly-name miss diagnostics."""

    if agent_id is not None:
        record = load_managed_agent_record_by_agent_id(agent_id)
        if record is None:
            return None, None
        _require_supported_registry_origin(record)
        if not include_inactive and (
            record.lifecycle.state != "active" or not is_live_agent_record_fresh(record)
        ):
            raise click.ClickException(
                _format_inactive_local_registry_match(
                    selector_name="--agent-id",
                    selector_value=agent_id,
                    record=record,
                )
            )
        return record, None

    assert agent_name is not None
    name_matches = (
        resolve_managed_agent_records_by_name(agent_name)
        if include_inactive
        else resolve_live_agent_records_by_name(agent_name)
    )
    if len(name_matches) > 1:
        raise click.ClickException(
            _format_ambiguous_local_registry_matches(
                selector_name="--agent-name",
                selector_value=agent_name,
                resolution_kind="friendly name",
                matches=name_matches,
            )
        )
    if len(name_matches) == 1:
        return name_matches[0], None
    all_matches = () if include_inactive else resolve_managed_agent_records_by_name(agent_name)
    if all_matches:
        if len(all_matches) > 1:
            raise click.ClickException(
                _format_ambiguous_local_registry_matches(
                    selector_name="--agent-name",
                    selector_value=agent_name,
                    resolution_kind="friendly name",
                    matches=all_matches,
                )
            )
        _require_supported_registry_origin(all_matches[0])
        raise click.ClickException(
            _format_inactive_local_registry_match(
                selector_name="--agent-name",
                selector_value=agent_name,
                record=all_matches[0],
            )
        )
    return (
        None,
        _LocalManagedAgentSelectorMiss(
            agent_name=agent_name,
            alias_match=_resolve_local_managed_agent_alias_hint(agent_name),
        ),
    )


def _resolve_local_managed_agent_alias_hint(
    agent_name: str,
) -> ManagedAgentRegistryRecordV3 | None:
    """Return one exact unique tmux/session alias hint for a missed friendly name."""

    alias_matches = [
        record for record in _list_registry_records() if record.terminal.session_name == agent_name
    ]
    if len(alias_matches) == 1:
        return alias_matches[0]
    return None


def _resolve_local_relaunch_record_with_miss_context(
    *,
    agent_id: str | None,
    agent_name: str | None,
) -> tuple[ManagedAgentRegistryRecordV3 | None, _LocalManagedAgentSelectorMiss | None]:
    """Resolve one local registry record for relaunch, including stopped relaunchable state."""

    if agent_id is not None:
        active_record = resolve_live_agent_record_by_agent_id(agent_id)
        if active_record is not None:
            return active_record, None
        relaunchable_record = resolve_relaunchable_managed_agent_record_by_agent_id(agent_id)
        if relaunchable_record is not None:
            return relaunchable_record, None
        record = load_managed_agent_record_by_agent_id(agent_id)
        if record is None:
            return None, None
        _require_supported_registry_origin(record)
        raise click.ClickException(
            _format_unavailable_local_relaunch_record(
                selector_name="--agent-id",
                selector_value=agent_id,
                record=record,
            )
        )

    assert agent_name is not None
    active_matches = resolve_live_agent_records_by_name(agent_name)
    if len(active_matches) > 1:
        raise click.ClickException(
            _format_ambiguous_local_registry_matches(
                selector_name="--agent-name",
                selector_value=agent_name,
                resolution_kind="friendly name",
                matches=active_matches,
            )
        )
    if len(active_matches) == 1:
        return active_matches[0], None

    relaunchable_matches = resolve_relaunchable_managed_agent_records_by_name(agent_name)
    if len(relaunchable_matches) > 1:
        raise click.ClickException(
            _format_ambiguous_local_registry_matches(
                selector_name="--agent-name",
                selector_value=agent_name,
                resolution_kind="friendly name",
                matches=relaunchable_matches,
            )
        )
    if len(relaunchable_matches) == 1:
        return relaunchable_matches[0], None

    all_matches = resolve_managed_agent_records_by_name(agent_name)
    if all_matches:
        if len(all_matches) > 1:
            raise click.ClickException(
                _format_ambiguous_local_registry_matches(
                    selector_name="--agent-name",
                    selector_value=agent_name,
                    resolution_kind="friendly name",
                    matches=all_matches,
                )
            )
        _require_supported_registry_origin(all_matches[0])
        raise click.ClickException(
            _format_unavailable_local_relaunch_record(
                selector_name="--agent-name",
                selector_value=agent_name,
                record=all_matches[0],
            )
        )
    return (
        None,
        _LocalManagedAgentSelectorMiss(
            agent_name=agent_name,
            alias_match=_resolve_local_managed_agent_alias_hint(agent_name),
        ),
    )


def _resolve_default_pair_target_with_local_miss(
    *,
    agent_ref: str,
    miss_context: _LocalManagedAgentSelectorMiss,
) -> ManagedAgentTarget:
    """Resolve default pair fallback while preserving one local friendly-name miss."""

    try:
        client = require_supported_houmao_pair(base_url=resolve_server_base_url())
        identity = resolve_managed_agent_identity(client, agent_ref=agent_ref)
    except click.ClickException as exc:
        raise click.ClickException(
            _format_local_managed_agent_selector_failure(
                miss_context=miss_context,
                remote_detail=str(exc),
            )
        ) from exc
    return ManagedAgentTarget(
        mode="server",
        agent_ref=agent_ref,
        identity=identity,
        client=client,
    )


def _resolve_stopped_relaunch_manifest_fallback_target(
    *,
    agent_id: str | None,
    agent_name: str | None,
) -> ManagedAgentTarget | None:
    """Resolve one pre-registry stopped manifest as a relaunch recovery fallback."""

    from .runtime_cleanup import _resolve_effective_runtime_root, discover_runtime_session_envelopes

    runtime_root = _resolve_effective_runtime_root(None)
    envelopes = discover_runtime_session_envelopes(runtime_root)
    for envelope in envelopes:
        retirement = getattr(envelope, "retirement", None)
        if retirement is None:
            continue
        if (
            retirement.agent_id == agent_id
            if agent_id is not None
            else agent_name is not None and retirement.agent_name == agent_name
        ):
            raise click.ClickException(str(retirement)) from retirement
    matches = [
        envelope
        for envelope in envelopes
        if _stopped_relaunch_envelope_matches_selector(
            envelope=envelope,
            agent_id=agent_id,
            agent_name=agent_name,
        )
    ]
    if not matches:
        return None
    if len(matches) > 1:
        candidates = ", ".join(_format_stopped_relaunch_candidate(match) for match in matches)
        selector_name = "--agent-id" if agent_id is not None else "--agent-name"
        selector_value = agent_id if agent_id is not None else agent_name
        assert selector_value is not None
        raise click.ClickException(
            "Stopped-session relaunch recovery is ambiguous under the effective runtime root "
            f"`{runtime_root}` for {selector_name} `{selector_value}`. Use an explicit "
            f"manifest/session-root recovery path with one candidate: {candidates}"
        )

    match = matches[0]
    assert match.payload is not None
    agent_def_dir_value = match.payload.runtime.agent_def_dir
    if agent_def_dir_value is None or not agent_def_dir_value.strip():
        raise click.ClickException(
            "Stopped-session relaunch recovery matched a persisted manifest, but "
            "`runtime.agent_def_dir` is missing from that manifest."
        )
    try:
        controller = resume_stopped_runtime_session(
            agent_def_dir=Path(agent_def_dir_value).resolve(),
            session_manifest_path=match.manifest_path,
        )
    except BrainLaunchRuntimeError as exc:
        raise click.ClickException(str(exc)) from exc
    return ManagedAgentTarget(
        mode="local_stopped",
        agent_ref=agent_id or agent_name or match.manifest_path.as_posix(),
        identity=_identity_from_controller(controller),
        controller=controller,
    )


def _stopped_relaunch_envelope_matches_selector(
    *,
    envelope: object,
    agent_id: str | None,
    agent_name: str | None,
) -> bool:
    """Return whether one stopped runtime envelope matches a relaunch selector."""

    payload = getattr(envelope, "payload", None)
    if getattr(envelope, "live", True) or payload is None:
        return False
    if agent_id is not None:
        return getattr(payload, "agent_id", None) == agent_id
    assert agent_name is not None
    return getattr(payload, "agent_name", None) == agent_name


def _format_stopped_relaunch_candidate(envelope: object) -> str:
    """Format one stopped-manifest relaunch candidate for ambiguity diagnostics."""

    payload = getattr(envelope, "payload", None)
    parts = [
        f"agent_id={getattr(payload, 'agent_id', None)!r}",
        f"agent_name={getattr(payload, 'agent_name', None)!r}",
        f"manifest_path={getattr(envelope, 'manifest_path', None)!r}",
        f"session_root={getattr(envelope, 'session_root', None)!r}",
        f"tmux_session_name={getattr(envelope, 'tmux_session_name', None)!r}",
    ]
    return "{" + ", ".join(parts) + "}"


def _format_local_managed_agent_selector_failure(
    *,
    miss_context: _LocalManagedAgentSelectorMiss,
    remote_detail: str,
) -> str:
    """Format one local friendly-name miss with one failed default pair fallback."""

    lines = [
        f"No local managed agent matched friendly name `{miss_context.agent_name}`.",
    ]
    if miss_context.alias_match is not None:
        lines.append(
            "`--agent-name` expects the published friendly managed-agent name. "
            f"`{miss_context.agent_name}` matches the live local tmux/session alias for "
            f"agent_name `{miss_context.alias_match.agent_name}` "
            f"(agent_id `{miss_context.alias_match.agent_id}`)."
        )
        retry_guidance = (
            f"Retry with `--agent-name {miss_context.alias_match.agent_name}`, "
            f"`--agent-id {miss_context.alias_match.agent_id}`, "
            "or inspect `houmao-mgr agents global list`."
        )
    else:
        retry_guidance = (
            "Retry with `houmao-mgr agents global list`, the correct friendly managed-agent name, "
            "or `--agent-id <id>`."
        )
    lines.append(f"Fallback lookup through the default pair authority also failed: {remote_detail}")
    lines.append(retry_guidance)
    return "\n".join(lines)


def resolve_live_agent_record(agent_identity: str) -> ManagedAgentRegistryRecordV3 | None:
    """Backward-compatible local record resolution without explicit ambiguity errors."""

    record = resolve_live_agent_record_by_agent_id(agent_identity)
    if record is not None:
        return record
    name_matches = resolve_live_agent_records_by_name(agent_identity)
    if len(name_matches) == 1:
        return name_matches[0]
    return None


def _format_ambiguous_local_registry_matches(
    *,
    selector_name: str,
    selector_value: str,
    resolution_kind: str,
    matches: Sequence[ManagedAgentRegistryRecordV3],
) -> str:
    """Format one explicit local-registry ambiguity error."""

    candidate_lines = "\n".join(
        (
            f"- agent_id={record.agent_id} "
            f"agent_name={record.agent_name} "
            f"lifecycle_state={_record_lifecycle_state(record)} "
            f"tmux_session_name={record.terminal.session_name} "
            f"manifest_path={_record_manifest_path(record)} "
            f"session_root={_record_session_root(record)}"
        )
        for record in matches
    )
    return (
        f"Local managed-agent resolution is ambiguous for {selector_name} `{selector_value}` "
        f"({resolution_kind}).\nCandidates:\n{candidate_lines}\n"
        "Retry with `--agent-id <id>`."
    )


def _format_inactive_local_registry_match(
    *,
    selector_name: str,
    selector_value: str,
    record: ManagedAgentRegistryRecordV3,
) -> str:
    """Format one explicit inactive local-registry match error."""

    lines = [
        f"Local managed-agent resolution for {selector_name} `{selector_value}` matched "
        f"an inactive registry record.",
        (
            f"agent_id={record.agent_id} agent_name={record.agent_name} "
            f"lifecycle_state={_record_lifecycle_state(record)} "
            f"tmux_session_name={record.terminal.session_name} "
            f"manifest_path={_record_manifest_path(record)} "
            f"session_root={_record_session_root(record)}"
        ),
        "Live state/prompt/interrupt/stop/gateway operations require an active managed agent.",
    ]
    lifecycle_state = _record_lifecycle_state(record)
    if lifecycle_state == "stopped":
        lines.append(
            f"Use `houmao-mgr agents single --agent-id {record.agent_id} relaunch` to revive it or "
            f"`houmao-mgr agents single --agent-id {record.agent_id} cleanup session` to remove its stopped artifacts."
        )
    elif lifecycle_state == "retired":
        lines.append(
            "The record is retired and no longer participates in live routing; inspect lifecycle-aware listings instead."
        )
    elif lifecycle_state == "relaunching":
        lines.append(
            "The record is currently relaunching; retry after the relaunch transition completes."
        )
    return "\n".join(lines)


def _format_unavailable_local_relaunch_record(
    *,
    selector_name: str,
    selector_value: str,
    record: ManagedAgentRegistryRecordV3,
) -> str:
    """Format one explicit local-registry relaunch error."""

    lines = [
        f"Managed-agent relaunch for {selector_name} `{selector_value}` matched a registry record "
        "that cannot be relaunched.",
        (
            f"agent_id={record.agent_id} agent_name={record.agent_name} "
            f"lifecycle_state={_record_lifecycle_state(record)} "
            f"relaunchable={record.lifecycle.relaunchable} "
            f"tmux_session_name={record.terminal.session_name} "
            f"manifest_path={_record_manifest_path(record)} "
            f"session_root={_record_session_root(record)}"
        ),
    ]
    lifecycle_state = _record_lifecycle_state(record)
    if lifecycle_state == "stopped":
        lines.append(
            "The stopped record exists, but it does not retain supported local relaunch "
            "authority for stopped-session revival."
        )
        lines.append(
            f"Use `houmao-mgr agents single --agent-id {record.agent_id} cleanup session` to remove "
            "the stopped runtime artifacts, or relaunch from an explicit manifest/session-root "
            "recovery path once the missing authority is repaired."
        )
    elif lifecycle_state == "active":
        lines.append(
            "The record still claims active lifecycle state, but no fresh live tmux authority "
            "was available for active relaunch."
        )
    elif lifecycle_state == "retired":
        lines.append("The record is retired and no longer participates in relaunch routing.")
    elif lifecycle_state == "relaunching":
        lines.append("The record is already in a relaunch transition; retry after it completes.")
    return "\n".join(lines)


def _record_lifecycle_state(record: object) -> ManagedAgentLifecycleState | None:
    """Return one lifecycle-state string when the record exposes it."""

    lifecycle = getattr(record, "lifecycle", None)
    raw_value: object = getattr(lifecycle, "state", None)
    if raw_value == "active":
        return "active"
    if raw_value == "stopped":
        return "stopped"
    if raw_value == "relaunching":
        return "relaunching"
    if raw_value == "retired":
        return "retired"
    return None


def _record_manifest_path(record: object) -> str:
    """Return one manifest-path string for diagnostics when present."""

    runtime = getattr(record, "runtime", None)
    value = getattr(runtime, "manifest_path", None)
    return value if isinstance(value, str) else "-"


def _record_session_root(record: object) -> str:
    """Return one session-root string for diagnostics when present."""

    runtime = getattr(record, "runtime", None)
    value = getattr(runtime, "session_root", None)
    return value if isinstance(value, str) and value.strip() else "-"


def _non_empty_record_manifest_path(record: object) -> str | None:
    """Return one manifest-path string when present and non-empty."""

    value = _record_manifest_path(record)
    return value if value != "-" and value.strip() else None


def _non_empty_record_session_root(record: object) -> str | None:
    """Return one session-root string when present and non-empty."""

    value = _record_session_root(record)
    return value if value != "-" and value.strip() else None


def _format_stop_failure_guidance(
    *,
    base_detail: str,
    target: ManagedAgentTarget,
    completed_phase: str,
    failed_phase: str,
    manifest_path: str | None,
    session_root: str | None,
) -> str:
    """Append actionable stop recovery guidance to one failure detail."""

    context_lines = _stop_failure_context_lines(
        target=target,
        manifest_path=manifest_path,
        session_root=session_root,
    )
    dry_run_command = _stop_cleanup_followup_command(
        target=target,
        manifest_path=manifest_path,
        session_root=session_root,
        dry_run=True,
    )
    cleanup_command = _stop_cleanup_followup_command(
        target=target,
        manifest_path=manifest_path,
        session_root=session_root,
        dry_run=False,
    )
    lines = [
        base_detail,
        "",
        "Recovery guidance:",
        f"  completed_phase: {completed_phase}",
        f"  failed_phase: {failed_phase}",
        "  known_target:",
        *context_lines,
    ]
    if dry_run_command is not None:
        lines.extend(
            [
                "  next_step_dry_run:",
                f"    {dry_run_command}",
            ]
        )
    if cleanup_command is not None:
        lines.extend(
            [
                "  after_review:",
                f"    {cleanup_command}",
            ]
        )
    lines.extend(
        [
            "  retry:",
            f"    houmao-mgr agents single --agent-id {shlex.quote(target.identity.tracked_agent_id)} stop",
        ]
    )
    return "\n".join(lines)


def _stop_failure_context_lines(
    *,
    target: ManagedAgentTarget,
    manifest_path: str | None,
    session_root: str | None,
) -> list[str]:
    """Return indented target context lines for stop failure guidance."""

    record = target.record
    identity = target.identity
    agent_name = getattr(record, "agent_name", None) or identity.agent_name
    agent_id = getattr(record, "agent_id", None) or identity.agent_id or identity.tracked_agent_id
    terminal = getattr(record, "terminal", None)
    tmux_session_name = (
        getattr(terminal, "session_name", None)
        or identity.tmux_session_name
        or identity.session_name
    )
    fields = (
        ("agent_name", agent_name),
        ("agent_id", agent_id),
        ("tmux_session_name", tmux_session_name),
        ("manifest_path", manifest_path),
        ("session_root", session_root),
    )
    return [f"    {name}: {value}" for name, value in fields if isinstance(value, str) and value]


def _stop_cleanup_followup_command(
    *,
    target: ManagedAgentTarget,
    manifest_path: str | None,
    session_root: str | None,
    dry_run: bool,
) -> str | None:
    """Return the most precise supported cleanup command for stop recovery."""

    selector = _stop_cleanup_selector(
        target=target,
        manifest_path=manifest_path,
        session_root=session_root,
    )
    if selector is None:
        return None
    suffix = " --dry-run" if dry_run else ""
    return f"houmao-mgr agents single {selector} cleanup session --purge-registry{suffix}"


def _stop_cleanup_selector(
    *,
    target: ManagedAgentTarget,
    manifest_path: str | None,
    session_root: str | None,
) -> str | None:
    """Return a cleanup selector for one failed stop operation."""

    record = target.record
    agent_id = getattr(record, "agent_id", None) or target.identity.agent_id
    if isinstance(agent_id, str) and agent_id.strip():
        return f"--agent-id {shlex.quote(agent_id)}"
    agent_name = getattr(record, "agent_name", None) or target.identity.agent_name
    if isinstance(agent_name, str) and agent_name.strip():
        return f"--agent-name {shlex.quote(agent_name)}"
    if manifest_path is not None and manifest_path.strip():
        return f"--agent-id {shlex.quote(target.identity.tracked_agent_id)}"
    if session_root is not None and session_root.strip():
        return f"--agent-id {shlex.quote(target.identity.tracked_agent_id)}"
    return None


def _annotate_external_state_response(
    response: HoumaoManagedAgentStateResponse,
    record: ExternalManagedAgentRegistryRecordV1,
) -> HoumaoManagedAgentStateResponse:
    """Attach local external-import metadata to one remote state response."""

    return response.model_copy(
        update={
            "tracked_agent_id": record.external_agent_id,
            "identity": _annotate_external_remote_identity(response.identity, record),
        }
    )


def _annotate_external_detail_response(
    response: HoumaoManagedAgentDetailResponse,
    record: ExternalManagedAgentRegistryRecordV1,
) -> HoumaoManagedAgentDetailResponse:
    """Attach local external-import metadata to one remote detail response."""

    summary_state = _annotate_external_state_response(response.summary_state, record)
    return response.model_copy(
        update={
            "tracked_agent_id": record.external_agent_id,
            "identity": summary_state.identity,
            "summary_state": summary_state,
        }
    )


def managed_agent_identity_payload(target: ManagedAgentTarget) -> HoumaoManagedAgentIdentity:
    """Return the resolved managed-agent identity payload."""

    if _target_uses_pair_api(target):
        assert target.client is not None
        identity = resolve_managed_agent_identity(target.client, agent_ref=target.agent_ref)
        if target.external_record is not None:
            return _annotate_external_remote_identity(identity, target.external_record)
        return identity
    return target.identity


def _observe_recorded_managed_agent(target: ManagedAgentTarget) -> HoumaoManagedAgentDetailResponse:
    """Read one registry selection without a terminal preflight or writable resume."""

    record = target.record
    assert record is not None
    path = Path(record.runtime.manifest_path)
    identity = target.identity
    try:
        authority = read_selected_manifest(target)
        manifest = _read_running_agent_manifest(authority)
    except ManifestAuthorityUnavailable as exc:
        return observe_selected_agent(
            identity=identity,
            record=record,
            manifest_path=path,
            manifest=None,
            authority_error=exc.format_message(),
        )
    tmux = manifest.tmux
    path = authority.manifest_path
    identity = identity.model_copy(
        update={
            "runtime_session_id": manifest.runtime.session_id or identity.runtime_session_id,
            "tmux_window_name": tmux.primary_window_name if tmux is not None else None,
        }
    )
    client = None
    gateway = None
    if record.lifecycle.state == "active":
        try:
            status = _gateway_status_for_controller(authority)
            if status.gateway_health == "healthy":
                client = _live_gateway_client_for_controller(authority, private=True)
            if status.gateway_health != "healthy" or client is not None:
                gateway = gateway_summary_from_status(status)
        except (click.ClickException, GatewayHttpError):
            pass
    result = observe_selected_agent(
        identity=identity,
        record=record,
        manifest_path=path,
        manifest=manifest,
        gateway_client=client,
        gateway_summary=gateway,
    )
    latest = read_selected_manifest(target)
    if _read_running_agent_manifest(latest).tmux != tmux and manifest.mode == "tui":
        raise click.ClickException(
            f"The terminal binding for `{record.agent_id}` changed during observation."
        )
    return result


def managed_agent_state_payload(target: ManagedAgentTarget) -> HoumaoManagedAgentStateResponse:
    """Return a managed-agent state payload for one resolved target."""

    if target.mode == "executor":
        response = _executor_model(target, "state", HoumaoManagedAgentStateResponse)
        assert target.executor_locator is not None
        return response.model_copy(
            update={
                "identity": _qualify_executor_identity(response.identity, target.executor_locator)
            }
        )
    if _target_uses_pair_api(target):
        assert target.client is not None
        response = pair_request(target.client.get_managed_agent_state, target.agent_ref)
        if target.external_record is not None:
            return _annotate_external_state_response(response, target.external_record)
        return response
    if target.mode == "local" and target.record is not None:
        return _observe_recorded_managed_agent(target).summary_state
    raise click.ClickException(
        _format_unavailable_local_controller_message(
            target, operation="inspect managed-agent state"
        )
    )


def managed_agent_state_policy_summary(target: ManagedAgentTarget) -> dict[str, str | int] | None:
    """Read a bounded retained policy summary for the exact selected local owner."""

    record = target.record
    if target.mode != "local" or record is None:
        return None
    try:
        access = resolve_owner_gateway_access(agent_id=record.agent_id, agent_name=None)
        if (
            access.manifest_path != Path(record.runtime.manifest_path)
            or access.target.incarnation != record.generation_id
            or access.execution_binding != record.execution_binding
        ):
            return None
        access.require_current()
        policy = access.store.snapshot(read_only=True)
    except (click.ClickException, GatewayAccessError, SessionManifestError):
        return None
    if policy.default_permission_group is None:
        return {
            "admin_mode": policy.admin_mode,
            "default_permission_effects": ", ".join(
                permission.action for permission in policy.default_permission_effects
            ),
        }
    assert policy.default_permission_group_version is not None
    return {
        "admin_mode": policy.admin_mode,
        "default_permission_group": policy.default_permission_group,
        "default_permission_group_version": policy.default_permission_group_version,
    }


def managed_agent_detail_payload(target: ManagedAgentTarget) -> HoumaoManagedAgentDetailResponse:
    """Return a managed-agent detail payload for one resolved target."""

    if target.mode == "executor":
        response = _executor_model(target, "inspect", HoumaoManagedAgentDetailResponse)
        assert target.executor_locator is not None
        identity = _qualify_executor_identity(response.identity, target.executor_locator)
        return response.model_copy(
            update={
                "identity": identity,
                "summary_state": response.summary_state.model_copy(update={"identity": identity}),
            }
        )
    if _target_uses_pair_api(target):
        assert target.client is not None
        response = pair_request(target.client.get_managed_agent_state_detail, target.agent_ref)
        if target.external_record is not None:
            return _annotate_external_detail_response(response, target.external_record)
        return response
    if target.mode == "local" and target.record is not None:
        return _observe_recorded_managed_agent(target)
    raise click.ClickException(
        _format_unavailable_local_controller_message(
            target, operation="inspect managed-agent detail"
        )
    )


def _require_native_common_target(target: ManagedAgentTarget) -> None:
    """Reject external and inactive authority before native body inspection."""

    if (
        target.mode == "external"
        or target.identity.management_kind == "external_communication_only"
    ):
        raise click.ClickException("Native home and refresh require a locally managed agent.")
    if target.identity.lifecycle_state not in {None, "active"}:
        raise click.ClickException("Native home and refresh require an active managed agent.")
    if target.mode not in {"local", "server", "executor"}:
        raise click.ClickException("Native home and refresh require healthy active authority.")
    if target.mode == "server" and (
        target.client is None or target.client.pair_authority_kind != "houmao-passive-server"
    ):
        raise click.ClickException("Native home and refresh require the maintained passive server.")


def _native_common_gateway_client(controller: RuntimeSessionController) -> GatewayClient | None:
    """Use an attached gateway without falling back after its transport fails."""

    if gateway_paths_from_manifest_path(controller.manifest_path) is None:
        return None
    client = _live_gateway_client_for_controller(controller)
    if (
        client is None
        and _gateway_status_for_controller(controller).gateway_health != "not_attached"
    ):
        raise click.ClickException(
            "The attached gateway is unavailable; native refresh was not run."
        )
    if client is not None:
        try:
            expected = inspect_native_home(controller)
            actual = client.get_native_home()
        except (RuntimeError, OSError, ValueError):
            raise click.ClickException(
                "The attached gateway native authority is unavailable; native refresh was not run."
            ) from None
        if actual != expected:
            raise click.ClickException(
                "The attached gateway belongs to a different native execution; native refresh was not run."
            )
        client.bind_native_home(expected)
    return client


def managed_agent_native_home(target: ManagedAgentTarget) -> NativeHomeV1:
    """Read authoritative native-home selection without materializing inputs."""

    _require_native_common_target(target)
    if target.mode == "executor":
        return _qualify_executor_home(_executor_model(target, "home", NativeHomeV1), target)
    if target.mode == "server":
        assert target.client is not None
        return pair_request(target.client.get_managed_agent_gateway_native_home, target.agent_ref)
    if target.self_manifest is not None:
        try:
            return inspect_native_home_from_manifest(target.self_manifest.path)
        except (OSError, RuntimeError, ValueError) as exc:
            raise click.ClickException(str(exc)) from exc
    controller = _require_live_local_controller(target, operation="inspect the native home")
    client = _native_common_gateway_client(controller)
    return client.get_native_home() if client is not None else inspect_native_home(controller)


def managed_agent_common_plugin_state(target: ManagedAgentTarget) -> CommonPluginObservationV1:
    """Read common evidence without forcing discovery or attaching a gateway."""

    _require_native_common_target(target)
    if target.mode == "executor":
        observation = _executor_model(target, "refresh_check", CommonPluginObservationV1)
        return observation.model_copy(
            update={"home": _qualify_executor_home(observation.home, target)}
        )
    if target.mode == "server":
        assert target.client is not None
        return pair_request(
            target.client.get_managed_agent_gateway_common_plugin_state, target.agent_ref
        )
    controller = _require_live_local_controller(target, operation="inspect common-plugin state")
    client = _native_common_gateway_client(controller)
    return (
        client.get_common_plugin_state()
        if client is not None
        else observe_common_plugins(controller)
    )


def refresh_managed_agent(
    target: ManagedAgentTarget, *, timeout_seconds: float = 30.0
) -> NativeRefreshResultV1:
    """Use the owning gateway or permit only a qualified local mutation-free result."""

    request = NativeRefreshRequestV1(timeout_seconds=timeout_seconds)
    _require_native_common_target(target)
    if target.mode == "executor":
        result = _executor_model(
            target, "refresh", NativeRefreshResultV1, {"timeout_seconds": timeout_seconds}
        )
        observation = result.observation.model_copy(
            update={"home": _qualify_executor_home(result.observation.home, target)}
        )
        before = (
            result.before.model_copy(
                update={"home": _qualify_executor_home(result.before.home, target)}
            )
            if result.before is not None
            else None
        )
        return result.model_copy(update={"observation": observation, "before": before})
    if target.mode == "server":
        assert target.client is not None
        return pair_request(
            target.client.refresh_managed_agent_gateway_native, target.agent_ref, request
        )
    controller = _require_live_local_controller(target, operation="refresh native resources")
    client = _native_common_gateway_client(controller)
    if client is not None:
        return client.refresh_native(request)
    observation = observe_common_plugins(controller)
    planned = plan_native_refresh(observation)
    if planned is not None:
        return planned
    return NativeRefreshResultV1(
        method="none",
        outcome="unsupported",
        observation=observation,
        diagnostics=["gateway_attachment_required"],
    )


def prompt_managed_agent(
    target: ManagedAgentTarget,
    *,
    prompt: str,
    model: str | None = None,
    reasoning_level: int | None = None,
) -> object:
    """Submit the default prompt path for one managed agent."""

    if target.mode == "executor":
        result = _executor_payload(
            target, "prompt", {"prompt": prompt, "model": model, "reasoning_level": reasoning_level}
        )
        assert target.executor_locator is not None
        return {
            **result,
            "execution_context": target.executor_locator.binding.model_dump(mode="json"),
        }
    execution_model = _resolve_execution_model_override(
        model=model,
        reasoning_level=reasoning_level,
    )
    if target.identity.mode != "service":
        _require_headless_execution_override_target(
            target=target,
            execution_model=execution_model,
        )
    if _target_uses_pair_api(target):
        assert target.client is not None
        from houmao.server.models import HoumaoManagedAgentSubmitPromptRequest

        return pair_request(
            target.client.submit_managed_agent_request,
            target.agent_ref,
            HoumaoManagedAgentSubmitPromptRequest(
                prompt=prompt,
                execution=_execution_override_payload(execution_model),
            ),
        )

    if (
        target.identity.mode == "tui"
        and target.identity.backend not in MANAGED_STRUCTURED_TUI_BACKENDS
        and target.record is not None
    ):
        try:
            selected = read_selected_manifest(target)
            health = _probe_recorded_terminal(target.record, selected.payload)
        except OwnerTerminalInspectionUnavailable as exc:
            raise click.ClickException(str(exc)) from exc
        if health.state in {"stale_missing_session", "degraded_missing_primary"}:
            failed = replace(
                target, mode="local_stale" if not health.session_exists else "local_degraded"
            )
            raise click.ClickException(
                _format_unavailable_local_controller_message(
                    target=failed, operation="submit a prompt"
                )
            )
    controller = _require_live_local_controller(
        target, operation="submit a prompt", existing_only=True
    )
    return _dispatch_owned_manager_prompt(
        controller,
        tracked_agent_id=target.identity.tracked_agent_id,
        prompt=prompt,
        execution_model=execution_model,
    )


def _dispatch_owned_manager_prompt(
    controller: RuntimeSessionController,
    *,
    tracked_agent_id: str,
    prompt: str,
    execution_model: ModelConfig | None,
) -> HoumaoManagedAgentRequestAcceptedResponse:
    """Use one owner reservation for both manager prompt entrypoints."""

    if not prompt.strip():
        raise click.ClickException("Prompt must not be empty.")
    generation = controller.registry_generation_id
    if generation is None:
        raise click.ClickException("The selected owner has no current generation.")
    backend = controller.backend_session
    dispatch_attempted = False
    try:
        capabilities = controller.control_capabilities()
        capabilities.require("prompt")
        if isinstance(backend, HermesTuiSession):
            if execution_model is not None:
                raise BackendExecutionError("Hermes requests use the launch-selected model.")
            return _dispatch_hermes_tui_manager_prompt(
                controller,
                backend,
                tracked_agent_id=tracked_agent_id,
                generation=generation,
                prompt=prompt,
            )
        claim = reserve_owner_prompt(
            controller.manifest_path,
            generation,
            origin="manager",
            readiness=_manager_prompt_readiness(controller, mode=capabilities.mode),
        )
    except (BrainLaunchRuntimeError, OSError) as exc:
        if isinstance(backend, HermesTuiSession):
            if isinstance(exc, OwnerAdmissionError):
                raise HermesManagerPromptRefused(exc.code, str(exc)) from None
            if isinstance(exc, HermesDeadlineExpired):
                raise HermesManagerPromptRefused("deadline_exhausted", str(exc)) from None
            if isinstance(exc, HermesRpcRefused):
                raise HermesManagerPromptRefused("native_refusal", str(exc)) from None
        raise click.ClickException(str(exc)) from None

    dispatch = HeadlessDispatchControl.from_callbacks(
        allowed=claim.active,
        confirmed=claim.handoff,
        deadline=monotonic() + 300,
        manifest_path=controller.manifest_path,
        generation_id=generation,
    )
    try:
        if isinstance(
            backend,
            (HeadlessInteractiveSession, DshWebSession, KimiWebSession, ManagedServiceSession),
        ):
            backend.configure_request_dispatch(dispatch)
        dispatch_attempted = True
        events = controller.send_prompt(
            prompt,
            execution_model=execution_model,
            turn_artifact_dir_name=claim.request_id,
        )
    except BackendExecutionError as exc:
        if isinstance(backend, (KimiWebSession, LocalInteractiveSession)) and not (
            dispatch.m_input_started.is_set()
        ):
            claim.finish("failed")
            raise click.ClickException(str(exc)) from None
        claim.finish("uncertain" if dispatch_attempted else "failed")
        raise
    except BaseException:
        # Input may have crossed the native boundary before a process or caller disappeared.
        claim.finish("uncertain" if dispatch_attempted else "failed")
        raise
    finally:
        if isinstance(
            backend,
            (HeadlessInteractiveSession, DshWebSession, KimiWebSession, ManagedServiceSession),
        ):
            backend.configure_request_dispatch(None)

    delivery_state: Literal["handed_off", "completed", "interrupted", "failed", "uncertain"]
    headless_turn_index = None
    if capabilities.mode == "tui" and any(event.kind == "submitted" for event in events):
        claim.handoff()
        delivery_state = "handed_off"
        detail = "Prompt handed off to the terminal. Provider completion is unconfirmed."
    elif (
        terminal := next((event for event in reversed(events) if event.kind == "done"), None)
    ) is not None:
        payload = terminal.payload or {}
        outcome = payload.get("outcome", "completed" if capabilities.mode == "headless" else None)
        if outcome in ("completed", "interrupted", "failed"):
            delivery_state = cast(Literal["completed", "interrupted", "failed"], outcome)
            claim.finish(delivery_state, evidence=capabilities.evidence_source)
            detail = f"Native prompt outcome: {delivery_state}."
            if capabilities.mode == "headless":
                headless_turn_index = terminal.turn_index
        else:
            delivery_state = "uncertain"
            claim.finish(delivery_state)
            detail = "The owner could not verify the native prompt outcome."
    else:
        delivery_state = "uncertain"
        claim.finish(delivery_state)
        detail = "The owner could not verify the native prompt outcome."
    if isinstance(backend, KimiWebSession) and any(
        event.kind == "status"
        and event.payload is not None
        and event.payload.get("phase") == "native_admission"
        and event.payload.get("native_status") == "queued"
        for event in events
    ):
        detail = f"Kimi accepted the prompt as queued. {detail}"
    return HoumaoManagedAgentRequestAcceptedResponse(
        success=delivery_state in {"handed_off", "completed"},
        tracked_agent_id=tracked_agent_id,
        request_id=claim.request_id,
        request_kind="submit_prompt",
        disposition="accepted",
        detail=detail,
        delivery_state=delivery_state,
        evidence_source=capabilities.evidence_source,
        headless_turn_id=claim.request_id if capabilities.mode == "headless" else None,
        headless_turn_index=headless_turn_index,
    )


def _dispatch_hermes_tui_manager_prompt(
    controller: RuntimeSessionController,
    backend: HermesTuiSession,
    *,
    tracked_agent_id: str,
    generation: str,
    prompt: str,
) -> HoumaoManagedAgentRequestAcceptedResponse:
    """Reserve and observe one prompt for the pinned Hermes conversation."""

    if execution_is_read_only():
        raise OwnerAdmissionError("unavailable", "Read-only execution cannot submit a prompt.")
    delivery: Literal["queued", "handed_off", "completed", "failed", "interrupted", "uncertain"]
    with controller.execution_scope():
        # Native observation reconciles the owner ledger and needs its own transaction.
        observed = controller.observe_managed_tui()
        if (
            observed.freshness != "current"
            or observed.owner_available is not True
            or observed.connection_ready is not True
        ):
            raise OwnerAdmissionError(
                "unavailable", "The native Hermes conversation is unavailable."
            )
        if observed.active_request_id is not None:
            raise OwnerAdmissionError("not_ready", "The owner has an unresolved prompt attempt.")
        if observed.can_accept_prompt_now is not True:
            raise OwnerAdmissionError("not_ready", "The native Hermes conversation is busy.")

        claim = reserve_owner_prompt(
            controller.manifest_path,
            generation,
            origin="manager",
            reconcile_tui=backend.reconcile_owner_attempt,
        )
        try:
            admission = backend.submit_native_prompt(
                prompt, request_id=claim.request_id, owner_claim=claim, existing_only=True
            )
        except HermesAdmissionUncertain as exc:
            delivery = "uncertain"
            detail = str(exc)
        else:
            settled = backend.wait_for_native_prompt(claim, admission)
            outcome = settled.terminal_outcome
            if outcome is not None:
                delivery = outcome
                detail = f"Native prompt outcome: {outcome}."
            elif settled.native_admission_id is not None and settled.status == "queued":
                delivery = "queued"
                detail = "Hermes accepted the prompt into its native queue."
            elif settled.native_admission_id is not None and settled.status == "running":
                delivery = "handed_off"
                detail = "Hermes started the prompt. Completion is unconfirmed."
            else:
                delivery = "uncertain"
                detail = "Hermes native prompt admission could not be confirmed."

    return HoumaoManagedAgentRequestAcceptedResponse(
        success=delivery in {"queued", "handed_off", "completed"},
        tracked_agent_id=tracked_agent_id,
        request_id=claim.request_id,
        request_kind="submit_prompt",
        detail=detail,
        delivery_state=delivery,
        evidence_source="tui_native",
    )


def _manager_prompt_readiness(
    controller: RuntimeSessionController, *, mode: RunMode
) -> Callable[[], None] | None:
    """Prepare a native readiness check to run while reserving the input slot."""

    if mode == "web" and isinstance(controller.backend_session, (DshWebSession, KimiWebSession)):
        return lambda: _require_manager_web_ready(controller)
    if mode == "service":
        return lambda: _require_manager_service_ready(controller)
    if mode != "tui":
        return None
    manifest = controller.require_managed_control_owner()
    if manifest.tmux is None or manifest.tmux.socket_path is None:
        raise OwnerAdmissionError("unavailable", "The terminal has no recorded owner socket.")
    tracker = _local_tui_runtime_for_controller(controller, manifest=manifest)
    with controller.execution_scope():
        deadline = monotonic() + 2.0
        state = tracker.refresh_once()
        _require_manager_terminal_ready(state, require_stable=False)
        while not state.stability.stable and monotonic() < deadline:
            sleep(0.25)
            state = tracker.refresh_once()
            _require_manager_terminal_ready(state, require_stable=False)
        _require_manager_terminal_ready(state)

    def recheck() -> None:
        """Close the observation-to-admission window before any terminal mutation."""

        with controller.execution_scope():
            _require_manager_terminal_ready(tracker.refresh_once())

    return recheck


def _require_manager_service_ready(controller: RuntimeSessionController) -> None:
    """Require current idle native service evidence before admitting a prompt."""

    observed = controller.observe_managed_service()
    if observed.owner_available is not True or observed.connection_ready is not True:
        raise OwnerAdmissionError("unavailable", "The native service connection is unavailable.")
    if observed.can_accept_prompt_now is not True:
        raise OwnerAdmissionError("not_ready", "The native service cannot admit a prompt now.")


def _require_manager_web_ready(controller: RuntimeSessionController) -> None:
    """Require ready evidence from the controller's exact native Web identity."""

    backend = controller.backend_session
    if isinstance(backend, (DshWebSession, KimiWebSession)):
        manifest = controller.require_managed_control_owner()
        metadata = web_attach_metadata_from_state(manifest.backend_state)
        with controller.execution_scope():
            observed = WebObservation(
                metadata=metadata,
                state=backend.observe_web_state,
                history=backend.observe_web_history,
            ).refresh()
        if observed.availability != "available":
            raise OwnerAdmissionError("unavailable", "The native Web session is unavailable.")
        if not observed.can_accept_prompt_now:
            raise OwnerAdmissionError("not_ready", "The native Web session is busy.")


def _require_manager_terminal_ready(
    state: HoumaoTerminalStateResponse, *, require_stable: bool = True
) -> None:
    """Require the shared terminal readiness criteria and an empty composer."""

    reasons = terminal_prompt_not_ready_reasons(state, require_stable=require_stable)
    if state.surface.pending_input != "no":
        reasons.append(f"surface.pending_input={state.surface.pending_input!r}")
    if reasons:
        raise OwnerAdmissionError(
            "not_ready", f"The terminal is not ready to accept a prompt ({', '.join(reasons)})."
        )


def open_managed_agent_browser(target: ManagedAgentTarget) -> SessionControlResult:
    """Open the owner's Kimi Web UI through an explicit local manager action."""

    controller = _require_live_local_controller(target, operation="open the native browser")
    backend = controller.backend_session
    if not isinstance(backend, KimiWebSession):
        raise click.ClickException("Browser opening requires an active local Kimi Web agent.")
    try:
        with controller.execution_scope():
            controller.require_managed_control_owner()
            result = backend.open_browser()
    except (OSError, BrainLaunchRuntimeError) as exc:
        raise click.ClickException(str(exc)) from None
    if result.status != "ok":
        raise click.ClickException(result.detail)
    return result


def interrupt_managed_agent(target: ManagedAgentTarget) -> object:
    """Interrupt one managed agent through the resolved control path."""

    if target.mode == "executor":
        executor_result = _executor_payload(target, "interrupt")
        assert target.executor_locator is not None
        return {
            **executor_result,
            "execution_context": target.executor_locator.binding.model_dump(mode="json"),
        }
    if _target_uses_pair_api(target):
        assert target.client is not None
        from houmao.server.models import HoumaoManagedAgentInterruptRequest

        return pair_request(
            target.client.submit_managed_agent_request,
            target.agent_ref,
            HoumaoManagedAgentInterruptRequest(),
        )

    controller = _require_live_local_controller(target, operation="interrupt managed agent")
    try:
        capabilities = controller.control_capabilities()
        capabilities.require("interrupt")
        if capabilities.mode == "headless" and capabilities.backend != "hermes_headless":
            generation = controller.registry_generation_id
            if generation is None:
                raise SessionManifestError("The selected owner has no current generation.")
            manifest_path = controller.manifest_path
            guard = (
                guard_owner_operation(manifest_path, generation)
                if owner_operation_guard_exists(manifest_path)
                else nullcontext()
            )
            with guard:
                attempt = observe_owner_prompt(manifest_path, generation)
                result = (
                    interrupt_owned_headless_attempt(attempt.turn_dir)
                    if attempt is not None
                    else SessionControlResult(
                        status="ok",
                        action="interrupt",
                        detail="No in-flight managed headless request.",
                    )
                )
        else:
            result = controller.interrupt()
    except (BrainLaunchRuntimeError, OSError) as exc:
        raise click.ClickException(str(exc)) from None
    return HoumaoManagedAgentActionResponse(
        success=result.status == "ok",
        tracked_agent_id=target.identity.tracked_agent_id,
        detail=result.detail,
    )


def stop_managed_agent(target: ManagedAgentTarget) -> HoumaoManagedAgentActionResponse:
    """Stop one managed agent through the resolved control path."""

    _raise_external_unsupported(target, operation="agents single ... stop")

    if target.mode == "executor":
        response = _executor_model(target, "stop", HoumaoManagedAgentActionResponse)
        assert target.executor_locator is not None
        return response.model_copy(update={"execution_context": target.executor_locator.binding})

    if target.mode == "server":
        assert target.client is not None
        return pair_request(target.client.stop_managed_agent, target.agent_ref)

    if target.mode in {"local_degraded", "local_stale"}:
        assert target.record is not None
        return _stop_degraded_or_stale_local_managed_agent(target)

    record = target.record
    if (
        target.controller is None
        and target.mode == "local"
        and record is not None
        and record.identity.backend not in MANAGED_STRUCTURED_TUI_BACKENDS
        and _is_local_tmux_backed_active_record(record)
    ):
        try:
            health = _probe_local_tmux_authority_for_record(record)
        except SessionManifestError as exc:
            raise click.ClickException(str(exc)) from exc
        if health.state == "degraded_missing_primary":
            return _stop_degraded_or_stale_local_managed_agent(
                replace(target, mode="local_degraded")
            )
        if health.state == "stale_missing_session":
            return _stop_degraded_or_stale_local_managed_agent(replace(target, mode="local_stale"))

    controller = _require_live_local_controller(target, operation="stop managed agent")
    manifest_path = str(controller.manifest_path)
    session_root = str(controller.manifest_path.parent)
    try:
        result = controller.stop(force_cleanup=True)
    except (OSError, BrainLaunchRuntimeError, SessionManifestError) as exc:
        return HoumaoManagedAgentActionResponse(
            success=False,
            tracked_agent_id=target.identity.tracked_agent_id,
            detail=_format_stop_failure_guidance(
                base_detail=f"Failed to stop managed agent `{target.agent_ref}`: {exc}",
                target=target,
                completed_phase="target resolution",
                failed_phase="local runtime teardown",
                manifest_path=manifest_path,
                session_root=session_root,
            ),
            manifest_path=manifest_path,
            session_root=session_root,
        )
    detail = result.detail
    if result.status != "ok":
        detail = _format_stop_failure_guidance(
            base_detail=result.detail,
            target=target,
            completed_phase="target resolution",
            failed_phase="local runtime teardown",
            manifest_path=manifest_path,
            session_root=session_root,
        )
    return HoumaoManagedAgentActionResponse(
        success=result.status == "ok",
        tracked_agent_id=target.identity.tracked_agent_id,
        detail=detail,
        manifest_path=manifest_path,
        session_root=session_root,
    )


def _recover_broken_active_local_record(
    target: ManagedAgentTarget,
) -> _BrokenActiveRecoveryResult:
    """Transition one verified broken active local record out of active state."""

    assert target.record is not None
    original = target.record
    current = load_managed_agent_record_by_agent_id(original.agent_id)
    if current is None:
        return _BrokenActiveRecoveryResult(
            record=None,
            manifest_path=_non_empty_record_manifest_path(original),
            session_root=_non_empty_record_session_root(original),
            detail=(
                "Broken active managed-agent registry record for "
                f"`{original.agent_name or original.agent_id}` was already gone."
            ),
            retired=True,
        )
    if not _is_local_tmux_backed_active_record(current):
        if (
            current.lifecycle.state == "stopped"
            and current.generation_id == original.generation_id
            and current.execution_binding == original.execution_binding
            and current.runtime == original.runtime
        ):
            return _BrokenActiveRecoveryResult(
                record=current,
                manifest_path=current.runtime.manifest_path,
                session_root=current.runtime.session_root,
                detail=(
                    "Managed agent "
                    f"`{current.agent_name or current.agent_id}` was already recovered to "
                    "stopped lifecycle continuity."
                ),
            )
        raise SessionManifestError(
            "Broken-active recovery expected a local active tmux-backed record for "
            f"`{current.agent_name or current.agent_id}`, found lifecycle state "
            f"`{current.lifecycle.state}`."
        )

    require_same_recovery_record(original, current)
    manifest = _read_recovery_manifest(current)
    manifest_path = Path(current.runtime.manifest_path)
    guard = (
        guard_owner_operation(manifest_path, current.generation_id, recover_lost_maintenance=True)
        if owner_operation_guard_exists(manifest_path)
        else nullcontext()
    )
    with guard as maintenance:
        if maintenance is not None:
            _require_stopped_dsh_maintenance_owner(current, manifest)
        result = _recover_verified_broken_active_record(current, manifest)
        if maintenance is not None:
            maintenance.fence_after_recovery()
        return result


def _require_stopped_dsh_maintenance_owner(
    record: ManagedAgentRegistryRecordV3, manifest: SessionManifestPayloadV4 | None
) -> None:
    """Verify native process exit before broken tmux can retire lost file maintenance."""

    error = "The former native execution has no verified shutdown evidence."
    if manifest is None or manifest.backend != "dsh_web":
        raise OwnerAdmissionError("uncertain", error)
    try:
        state = DshWebSessionState.from_payload(manifest.backend_state)
    except (BrainLaunchRuntimeError, TypeError, ValueError):
        raise OwnerAdmissionError("uncertain", error) from None
    if (
        state.web_identity["agent_id"] != record.agent_id
        or state.web_identity["runtime_session_id"] != manifest.runtime.session_id
        or state.web_identity["generation"] != record.generation_id
        or not dsh_web_processes_have_exited(state)
    ):
        raise OwnerAdmissionError("uncertain", error)


def _recover_verified_broken_active_record(
    current: ManagedAgentRegistryRecordV3, manifest: SessionManifestPayloadV4 | None
) -> _BrokenActiveRecoveryResult:
    """Settle broken terminal authority while owner maintenance cannot start."""

    health = _probe_recorded_terminal(current, manifest)
    if health.state not in {"degraded_missing_primary", "stale_missing_session"}:
        raise SessionManifestError(
            "Broken-active recovery rechecked local tmux authority for "
            f"`{current.agent_name or current.agent_id}` and found state "
            f"`{health.state}` instead of stale or degraded authority. Retry the command."
        )

    binding = recorded_tmux_binding(current, manifest)
    session_id = (
        require_owned_degraded_tmux_session(current, binding, health)
        if health.state == "degraded_missing_primary"
        else None
    )
    require_same_recovery_record(current, load_managed_agent_record_by_agent_id(current.agent_id))
    require_same_recovery_manifest(manifest, _read_recovery_manifest(current))
    if current.identity.tool == "hermes":
        if manifest is None:
            raise SessionManifestError("The recorded Hermes shutdown authority is unavailable.")
        try:
            stop_hermes_from_saved_session(Path(current.runtime.manifest_path), manifest)
        except (OSError, ValueError, RuntimeError) as exc:
            raise SessionManifestError(
                f"Could not retire the recorded Hermes owner: {exc}"
            ) from exc
    if session_id is not None:
        from houmao.execution.tmux import tmux_server_scope

        assert binding.socket_path is not None
        try:
            with tmux_server_scope(binding.socket_path):
                kill_tmux_session(session_name=binding.session_name, session_id=session_id)
        except TmuxCommandError as exc:
            raise SessionManifestError(f"Could not stop the degraded tmux session: {exc}") from exc

    manifest_path = current.runtime.manifest_path
    session_root = current.runtime.session_root
    if not _record_has_relaunchable_manifest_authority(current):
        retired = remove_managed_agent_record(
            current.agent_id,
            generation_id=current.generation_id,
        )
        return _BrokenActiveRecoveryResult(
            record=None,
            manifest_path=manifest_path,
            session_root=session_root,
            detail=(
                "Retired broken active managed-agent registry record without preserved "
                f"relaunch authority for `{current.agent_name or current.agent_id}`; "
                "use `houmao-mgr project agents launch ...` for a project-backed fresh launch."
                if retired
                else (
                    "Broken active managed-agent registry record for "
                    f"`{current.agent_name or current.agent_id}` was already gone; "
                    "use `houmao-mgr project agents launch ...` for a project-backed fresh launch."
                )
            ),
            retired=True,
        )

    stopped_record = _stopped_record_from_broken_active_record(current)
    published = publish_managed_agent_record(
        stopped_record, expected_generation_id=current.generation_id
    )
    return _BrokenActiveRecoveryResult(
        record=published,
        manifest_path=published.runtime.manifest_path,
        session_root=published.runtime.session_root,
        detail=(
            "Recovered stale or degraded active managed agent "
            f"`{published.agent_name or published.agent_id}` into stopped lifecycle "
            "continuity; use `houmao-mgr agents single --agent-id <id> relaunch` to revive."
        ),
    )


def _stopped_record_from_broken_active_record(
    record: ManagedAgentRegistryRecordV3,
) -> ManagedAgentRegistryRecordV3:
    """Build a stopped lifecycle record from one verified broken active record."""

    stopped_at = datetime.now(UTC).isoformat(timespec="seconds")
    payload = record.model_dump(mode="json")
    lifecycle_payload = dict(payload["lifecycle"])
    lifecycle_payload.update(
        {
            "state": "stopped",
            "state_updated_at": stopped_at,
            "stopped_at": stopped_at,
            "stop_reason": "operator_stop",
        }
    )
    terminal_payload = dict(payload["terminal"])
    terminal_payload["current_session_name"] = None
    terminal_payload["last_session_name"] = (
        record.terminal.last_session_name or record.terminal.session_name
    )
    payload["lifecycle"] = lifecycle_payload
    payload["terminal"] = terminal_payload
    payload["liveness"] = None
    payload["gateway"] = None
    return ManagedAgentRegistryRecordV3.model_validate(payload)


def _record_has_relaunchable_manifest_authority(record: ManagedAgentRegistryRecordV3) -> bool:
    """Return whether one record can be preserved as stopped relaunch authority."""

    return record.lifecycle.relaunchable and _record_has_readable_manifest_authority(record)


def _stop_degraded_or_stale_local_managed_agent(
    target: ManagedAgentTarget,
) -> HoumaoManagedAgentActionResponse:
    """Stop a local tmux-backed managed agent whose tmux authority is degraded or stale."""

    assert target.record is not None
    record = target.record
    try:
        recovery = _recover_broken_active_local_record(target)
    except OwnerTerminalInspectionUnavailable as exc:
        return HoumaoManagedAgentActionResponse(
            success=False,
            tracked_agent_id=target.identity.tracked_agent_id,
            detail=str(exc),
            manifest_path=_non_empty_record_manifest_path(record),
            session_root=_non_empty_record_session_root(record),
        )
    except (OSError, OwnerAdmissionError, SessionManifestError) as exc:
        manifest_path = _non_empty_record_manifest_path(record)
        session_root = _non_empty_record_session_root(record)
        return HoumaoManagedAgentActionResponse(
            success=False,
            tracked_agent_id=target.identity.tracked_agent_id,
            detail=_format_stop_failure_guidance(
                base_detail=(
                    f"Failed to recover broken active shared-registry record for "
                    f"`{record.agent_name or record.agent_id}` during stop: {exc}"
                ),
                target=target,
                completed_phase="local stale/degraded authority classification",
                failed_phase="shared-registry lifecycle transition",
                manifest_path=manifest_path,
                session_root=session_root,
            ),
            manifest_path=manifest_path,
            session_root=session_root,
        )
    return HoumaoManagedAgentActionResponse(
        success=True,
        tracked_agent_id=target.identity.tracked_agent_id,
        detail=recovery.detail,
        manifest_path=recovery.manifest_path,
        session_root=recovery.session_root,
    )


def relaunch_managed_agent(
    target: ManagedAgentTarget,
    *,
    relaunch_chat_session: RelaunchChatSessionSelection | None = None,
) -> HoumaoManagedAgentActionResponse:
    """Relaunch one tmux-backed managed agent through the resolved runtime authority."""

    _raise_external_unsupported(target, operation="agents single ... relaunch")

    if target.mode == "executor":
        arguments: JsonObject = {}
        if relaunch_chat_session is not None:
            arguments["chat_session"] = {
                "mode": relaunch_chat_session.mode,
                "session_id": relaunch_chat_session.session_id,
            }
        response = _executor_model(target, "relaunch", HoumaoManagedAgentActionResponse, arguments)
        assert target.executor_locator is not None
        return response.model_copy(update={"execution_context": target.executor_locator.binding})

    if target.record is not None and target.record.identity.tool == "hermes":
        try:
            saved = load_registry_mode_authority(target.record)
        except (OSError, SessionManifestError) as exc:
            raise click.ClickException(str(exc)) from exc
        if saved.launch_plan.hermes_profile is None:
            return HoumaoManagedAgentActionResponse(
                success=False,
                tracked_agent_id=target.identity.tracked_agent_id,
                detail=HERMES_STANDALONE_RELAUNCH_REFUSAL,
            )

    if target.mode in {"local_degraded", "local_stale"}:
        assert target.record is not None
        return _relaunch_degraded_or_stale_local_managed_agent(
            target,
            relaunch_chat_session=relaunch_chat_session,
        )

    if target.mode == "server":
        if target.record is None:
            raise click.ClickException(
                "Managed-agent relaunch requires local manifest authority on the owning host. "
                "This target is only resolvable through pair HTTP metadata."
            )
        if _record_lifecycle_state(target.record) == "stopped":
            controller = _resume_stopped_controller_from_record(target.record)
        else:
            controller = _resume_controller_from_record(target.record)
        tracked_agent_id = target.identity.tracked_agent_id
    elif target.mode == "local_stopped":
        controller = _require_live_local_controller(
            target,
            operation="relaunch managed agent",
        )
        tracked_agent_id = target.identity.tracked_agent_id
    else:
        if target.record is not None and _record_lifecycle_state(target.record) == "stopped":
            controller = _resume_stopped_controller_from_record(target.record)
        else:
            controller = _require_live_local_controller(
                target,
                operation="relaunch managed agent",
            )
        tracked_agent_id = target.identity.tracked_agent_id

    try:
        result = (
            controller.revive_stopped_session(chat_session=relaunch_chat_session)
            if (
                target.mode == "local_stopped"
                or (
                    target.record is not None
                    and _record_lifecycle_state(target.record) == "stopped"
                )
            )
            else (
                controller.relaunch(chat_session=relaunch_chat_session)
                if relaunch_chat_session is not None
                else controller.relaunch()
            )
        )
    except OwnerAdmissionError as exc:
        return HoumaoManagedAgentActionResponse(
            success=False, tracked_agent_id=tracked_agent_id, detail=str(exc)
        )
    return HoumaoManagedAgentActionResponse(
        success=result.status == "ok",
        tracked_agent_id=tracked_agent_id,
        detail=result.detail,
    )


def _relaunch_degraded_or_stale_local_managed_agent(
    target: ManagedAgentTarget,
    *,
    relaunch_chat_session: RelaunchChatSessionSelection | None,
) -> HoumaoManagedAgentActionResponse:
    """Relaunch a local tmux-backed managed agent whose tmux authority is degraded or stale."""

    assert target.record is not None
    record = target.record
    try:
        recovery = _recover_broken_active_local_record(target)
    except OwnerTerminalInspectionUnavailable as exc:
        raise click.ClickException(str(exc)) from exc
    except (OSError, OwnerAdmissionError, SessionManifestError) as exc:
        raise click.ClickException(
            f"Managed agent `{record.agent_name or record.agent_id}` cannot be relaunched: "
            f"failed to reconcile broken active local authority first ({exc}). "
            "Run `houmao-mgr agents single --agent-id <id> stop` to recover or retire the active record before "
            "retrying relaunch."
        ) from exc
    if recovery.record is None:
        raise click.ClickException(
            f"Managed agent `{record.agent_name or record.agent_id}` cannot be relaunched: "
            f"{recovery.detail}"
        )
    try:
        controller = _resume_stopped_controller_from_record(recovery.record)
    except click.ClickException as exc:
        raise click.ClickException(
            f"Managed agent `{record.agent_name or record.agent_id}` cannot be relaunched: "
            f"preserved relaunch authority could not be reconstructed ({exc.message}). "
            "Use `houmao-mgr agents single --agent-id <id> stop` to retire the registry record, then "
            "`houmao-mgr project agents launch ...` for a project-backed fresh launch."
        ) from exc

    result = controller.revive_stopped_session(chat_session=relaunch_chat_session)
    return HoumaoManagedAgentActionResponse(
        success=result.status == "ok",
        tracked_agent_id=target.identity.tracked_agent_id,
        detail=result.detail,
    )


def gateway_status(target: ManagedAgentTarget) -> GatewayStatusV1:
    """Return gateway status for one managed agent."""

    if target.mode == "executor":
        return _executor_gateway_status(target, "gateway_status")
    if _target_uses_pair_api(target):
        assert target.client is not None
        return pair_request(target.client.get_managed_agent_gateway_status, target.agent_ref)

    authority = _running_agent_authority(target, operation="show gateway status")
    client = _live_gateway_client_for_controller(authority, private=True, require_available=True)
    if client is not None:
        try:
            status = client.status()
        except GatewayHttpError as exc:
            raise click.ClickException(exc.detail) from None
        if isinstance(authority, (VerifiedRegistryManifest, VerifiedSelfManifest)):
            paths = gateway_paths_from_manifest_path(authority.manifest_path)
            try:
                assert paths is not None
                current = load_gateway_current_instance(paths.current_instance_path)
                if not _gateway_status_matches_instance(status, current):
                    raise SessionManifestError("Gateway status belongs to a superseded instance.")
            except SessionManifestError as exc:
                raise _gateway_inspection_unavailable(authority, exc) from None
        return status
    return _gateway_status_for_controller(authority)


@dataclass(frozen=True)
class _OwnerLocalBrowserEntry:
    """An existing gateway verified against one current owner and generation."""

    manifest_path: Path
    port: int
    base_url: str
    client: GatewayClient
    descriptor: GatewayEndpointDescriptor


def _verify_owner_local_browser_gateway(
    *, agent_id: str | None, agent_name: str | None, surface: Literal["Web", "terminal"]
) -> _OwnerLocalBrowserEntry:
    """Select one existing direct listener and verify its retained identity."""

    entry = f"{surface.capitalize()} entry"
    changed = f"The managed {surface} execution changed. Select its live gateway and retry."
    agent_id, agent_name = resolve_managed_agent_selector(agent_id=agent_id, agent_name=agent_name)
    try:
        locator = resolve_executor_locator(agent_id=agent_id, agent_name=agent_name)
    except (ExecutorLocatorError, OSError):
        raise click.ClickException(
            f"{entry} could not verify the selected execution owner."
        ) from None
    if locator is not None:
        raise click.ClickException(
            f"{entry} requires running the command in the owner's execution context."
        )

    record = _resolve_local_managed_agent_record(agent_id=agent_id, agent_name=agent_name)
    if record is None:
        raise click.ClickException(
            f"{entry} requires a local managed agent. Run this command in the owner's execution context."
        )
    if surface == "Web" and record.mode != "web":
        raise click.ClickException("Web entry requires a live managed agent in Web mode.")

    manifest_path = Path(record.runtime.manifest_path)
    try:
        if surface == "terminal":
            validate_execution_owner(record.execution_binding)
        require_registry_mode_authority(record)
    except (OSError, SessionManifestError, ValueError):
        raise click.ClickException(changed) from None
    try:
        paths = gateway_paths_from_manifest_path(manifest_path)
        current = load_gateway_current_instance(paths.current_instance_path) if paths else None
    except (OSError, SessionManifestError):
        current = None
    if current is None:
        agent_description = "this Web agent" if surface == "Web" else "this managed agent"
        raise click.ClickException(
            f"No live gateway is attached to {agent_description}. "
            "Use `houmao-mgr agents single --agent-id <id> gateway attach` to attach it explicitly."
        )

    execution = record.execution_binding
    retained = current.endpoint_descriptor
    if execution is None or retained is None:
        raise click.ClickException(changed)
    try:
        base_url = owner_gateway_base_url(current.port)
        client = GatewayClient(base_url=base_url, respect_proxy_env=False)
        descriptor = client.describe_endpoint()
    except (GatewayHttpError, ValueError):
        raise click.ClickException(
            f"{entry} could not verify the live owner-local gateway."
        ) from None
    if (
        descriptor.target.owner.agent_id != record.agent_id
        or descriptor.target.owner.context_id != execution.context_id
        or descriptor.target.incarnation != record.generation_id
        or descriptor.presence_id != retained.presence_id
        or descriptor.protocol != current.protocol_version
        or descriptor.proof_protocol != retained.proof_protocol
    ):
        raise click.ClickException(changed)
    return _OwnerLocalBrowserEntry(manifest_path, current.port, base_url, client, descriptor)


def _signed_browser_gateway_client(
    entry: _OwnerLocalBrowserEntry,
    *,
    signer: Path | None,
    surface: Literal["Web", "terminal"],
) -> GatewayClient:
    """Bind a configured or explicit caller signer to the verified listener."""

    descriptor = entry.descriptor
    requirement = (
        "Web entry requires a signer with `web.enter` permission."
        if surface == "Web"
        else "Terminal interaction requires a currently enrolled admin signer."
    )
    try:
        if signer is None:
            binding, generation = owner_gateway_client_binding(
                entry.manifest_path, port=entry.port, private=False
            )
        else:
            binding = GatewayClientBinding(
                base_url=entry.base_url,
                owner=descriptor.target.owner,
                purpose="caller",
                private_key_path=str(signer),
            )
            generation = descriptor.target.incarnation
    except (GatewayAccessError, SessionManifestError, ValueError):
        diagnostic = (
            "Web entry requires a usable signer with `web.enter` permission."
            if surface == "Web"
            else requirement
        )
        raise click.ClickException(diagnostic) from None
    if (
        binding is None
        or binding.purpose != "caller"
        or (surface == "terminal" and binding.private_key_path is None)
    ):
        raise click.ClickException(f"{requirement} Pass `--signer` or set `admin_signer_path`.")
    if (
        generation != descriptor.target.incarnation
        or binding.owner != descriptor.target.owner
        or binding.base_url != entry.base_url
    ):
        raise click.ClickException(
            f"The managed {surface} execution changed. Select its live gateway and retry."
        )
    return GatewayClient(
        base_url=entry.base_url,
        binding=binding,
        target_incarnation=generation,
        target_presence_id=descriptor.presence_id,
        respect_proxy_env=False,
    )


def gateway_web_entry(
    *, agent_id: str | None, agent_name: str | None, signer: Path | None = None
) -> GatewayWebEntryTicketV1:
    """Request a ticket using the live owner-local gateway's access policy."""

    entry = _verify_owner_local_browser_gateway(
        agent_id=agent_id, agent_name=agent_name, surface="Web"
    )
    if entry.descriptor.admin_mode == "unavailable":
        raise click.ClickException(
            "Web entry access policy is unavailable. Check the live owner-local gateway."
        )
    client = entry.client
    if signer is not None or entry.descriptor.admin_mode == "keyed":
        client = _signed_browser_gateway_client(entry, signer=signer, surface="Web")
    try:
        return client.issue_web_entry_ticket()
    except GatewayHttpError as exc:
        raise click.ClickException(exc.detail) from None


def gateway_terminal_entry(
    *, agent_id: str | None, agent_name: str | None, interact: bool, signer: Path | None = None
) -> GatewayTerminalEntryTicketV1:
    """Request a browser terminal ticket from the already-running owner gateway."""

    if signer is not None and not interact:
        raise click.ClickException(
            "`--signer` requires `--interact`. Terminal viewing is unsigned."
        )
    entry = _verify_owner_local_browser_gateway(
        agent_id=agent_id, agent_name=agent_name, surface="terminal"
    )
    mode: GatewayTerminalEntryMode = "interact" if interact else "view"
    client = entry.client
    if interact:
        if entry.descriptor.admin_mode != "keyed":
            raise click.ClickException(
                "Terminal interaction requires a gateway with a verified enrolled administrator."
            )
        client = _signed_browser_gateway_client(entry, signer=signer, surface="terminal")
    try:
        ticket = client.issue_terminal_entry_ticket(mode=mode)
    except GatewayHttpError as exc:
        raise click.ClickException(exc.detail) from None
    if not interact:
        # An unsigned request has no challenge binding, so check the same listener again.
        changed = "The managed terminal execution changed. Select its live gateway and retry."
        try:
            current = client.describe_endpoint()
        except (GatewayHttpError, ValueError):
            raise click.ClickException(changed) from None
        if (
            current.target != entry.descriptor.target
            or current.presence_id != entry.descriptor.presence_id
            or current.protocol != entry.descriptor.protocol
            or current.proof_protocol != entry.descriptor.proof_protocol
        ):
            raise click.ClickException(changed)
    return ticket


def attach_gateway(
    target: ManagedAgentTarget,
    *,
    background: bool = False,
    tui_tracking_timing_overrides: GatewayTuiTrackingTimingOverridesV1 | None = None,
    plugin_config: GatewayPluginConfiguration | None = None,
    plugin_config_overrides: dict[str, dict[str, JsonValue]] | None = None,
    access_config_path: Path | None = None,
) -> GatewayStatusV1:
    """Attach or reuse a live gateway for one managed agent."""

    _raise_external_unsupported(target, operation="agents single ... gateway attach")
    if target.mode == "executor":
        if plugin_config is not None or plugin_config_overrides:
            raise click.ClickException(
                "Gateway plugin configuration is unsupported through the finite execution transport."
            )
        arguments: JsonObject = {
            "background": background,
            "tui_tracking_timing_overrides": tui_tracking_timing_overrides.model_dump(mode="json")
            if tui_tracking_timing_overrides is not None
            else None,
        }
        if access_config_path is not None:
            try:
                arguments["access_config_path"] = validate_gateway_access_config_path(
                    str(access_config_path)
                )
            except ValueError as exc:
                raise click.ClickException(str(exc)) from None
        return _executor_gateway_status(target, "gateway_attach", arguments)
    if (
        target.identity.transport == "web"
        and tui_tracking_timing_overrides is not None
        and tui_tracking_timing_overrides.has_values()
    ):
        raise click.ClickException(
            "Gateway TUI timing overrides are unsupported for the Web native surface."
        )

    target = _local_gateway_target_for_passive_pair(target, operation="attach")
    execution_mode_override: GatewayCurrentExecutionMode = (
        "detached_process" if background else "tmux_auxiliary_window"
    )
    if target.mode == "server":
        if access_config_path is not None:
            raise click.ClickException("Gateway access configuration requires owner-side attach.")
        if plugin_config is not None or plugin_config_overrides:
            raise click.ClickException(
                "Gateway plugin configuration requires local runtime authority on the owning host."
            )
        assert target.client is not None
        return pair_request(
            target.client.attach_managed_agent_gateway,
            target.agent_ref,
            HoumaoManagedAgentGatewayAttachRequest(
                execution_mode=execution_mode_override,
                tui_tracking_timings=tui_tracking_timing_overrides,
            ),
        )

    controller = _require_live_local_controller(target, operation="attach gateway")
    deployment = None
    if access_config_path is not None:
        try:
            validate_gateway_access_config_path(str(access_config_path))
            deployment = load_gateway_access_config(
                controller.launch_plan.working_directory / access_config_path
            )
        except (ValueError, SessionManifestError) as exc:
            raise click.ClickException(str(exc)) from None
    result = controller.attach_gateway(
        execution_mode_override=execution_mode_override,
        tui_tracking_timing_overrides=tui_tracking_timing_overrides,
        plugin_config=plugin_config,
        plugin_config_overrides=plugin_config_overrides,
        access_config=deployment,
    )
    if result.status != "ok":
        raise click.ClickException(result.detail)
    return _gateway_status_for_controller(controller)


def detach_gateway(target: ManagedAgentTarget) -> GatewayStatusV1:
    """Detach one live gateway for the resolved managed agent."""

    _raise_external_unsupported(target, operation="agents single ... gateway detach")
    if target.mode == "executor":
        return _executor_gateway_status(target, "gateway_detach")

    target = _local_gateway_target_for_passive_pair(target, operation="detach")
    if target.mode == "server":
        assert target.client is not None
        return pair_request(target.client.detach_managed_agent_gateway, target.agent_ref)

    controller = _require_live_local_controller(target, operation="detach gateway")
    result = controller.detach_gateway()
    if result.status != "ok":
        raise click.ClickException(result.detail)
    return _gateway_status_for_controller(controller)


def gateway_prompt(
    target: ManagedAgentTarget,
    *,
    prompt: str,
    admission_policy: GatewayPromptAdmissionPolicy = "ready_only",
    model: str | None = None,
    reasoning_level: int | None = None,
) -> GatewayPromptControlResultV1:
    """Submit one direct gateway prompt for a managed agent."""

    execution_model = _resolve_execution_model_override(
        model=model,
        reasoning_level=reasoning_level,
    )
    _require_headless_execution_override_target(
        target=target,
        execution_model=execution_model,
    )
    if _target_uses_pair_api(target):
        assert target.client is not None
        try:
            return target.client.control_managed_agent_gateway_prompt(
                target.agent_ref,
                HoumaoManagedAgentGatewayPromptControlRequest(
                    prompt=prompt,
                    admission_policy=admission_policy,
                    execution=_execution_override_payload(execution_model),
                ),
            )
        except CaoApiError as exc:
            raise GatewayPromptControlCliError(
                _prompt_control_error_from_cao(
                    exc,
                    admission_policy=admission_policy,
                )
            ) from exc

    authority = _running_agent_authority(target, operation="submit gateway prompt")
    try:
        client = _require_live_gateway_client_for_controller(authority)
        return client.control_prompt(
            GatewayPromptControlRequestV1(
                prompt=prompt,
                admission_policy=admission_policy,
                execution=_execution_override_payload(execution_model),
            )
        )
    except GatewayHttpError as exc:
        raise GatewayPromptControlCliError(
            _prompt_control_error_from_gateway_http(
                exc,
                admission_policy=admission_policy,
            )
        ) from exc
    except click.ClickException as exc:
        raise GatewayPromptControlCliError(
            GatewayPromptControlErrorV1(
                admission_policy=admission_policy,
                error_code="unavailable",
                detail=exc.message or str(exc),
            )
        ) from exc


def _prompt_control_error_from_cao(
    exc: CaoApiError,
    *,
    admission_policy: GatewayPromptAdmissionPolicy,
) -> GatewayPromptControlErrorV1:
    """Normalize one pair-server prompt-control failure into structured JSON."""

    payload = exc.payload if isinstance(exc.payload, dict) else None
    detail_payload = payload.get("detail") if isinstance(payload, dict) else None
    return _coerce_prompt_control_error(
        payload=detail_payload,
        admission_policy=admission_policy,
        status_code=exc.status_code,
        fallback_detail=exc.detail,
    )


def _prompt_control_error_from_gateway_http(
    exc: GatewayHttpError,
    *,
    admission_policy: GatewayPromptAdmissionPolicy,
) -> GatewayPromptControlErrorV1:
    """Normalize one direct gateway HTTP failure into structured JSON."""

    try:
        payload = json.loads(exc.detail)
    except json.JSONDecodeError:
        payload = None
    return _coerce_prompt_control_error(
        payload=payload,
        admission_policy=admission_policy,
        status_code=exc.status_code,
        fallback_detail=exc.detail,
    )


def _coerce_prompt_control_error(
    *,
    payload: object,
    admission_policy: GatewayPromptAdmissionPolicy,
    status_code: int | None,
    fallback_detail: str,
) -> GatewayPromptControlErrorV1:
    """Return one strict prompt-control error payload from a best-effort source payload."""

    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            payload = None
    if isinstance(payload, dict):
        try:
            return GatewayPromptControlErrorV1.model_validate(payload)
        except ValidationError:
            detail_value = payload.get("detail")
            if isinstance(detail_value, str) and detail_value.strip():
                fallback_detail = detail_value
    return GatewayPromptControlErrorV1(
        admission_policy=admission_policy,
        error_code=_prompt_control_error_code_from_status(status_code),
        detail=fallback_detail,
    )


def _prompt_control_error_code_from_status(status_code: int | None) -> str:
    """Map one HTTP status code to a conservative prompt-control error code."""

    if status_code == 409:
        return "not_ready"
    if status_code == 501:
        return "unsupported_backend"
    if status_code == 503:
        return "unavailable"
    if status_code == 422:
        return "dispatch_failed"
    return "dispatch_failed"


def gateway_interrupt(target: ManagedAgentTarget) -> GatewayAcceptedRequestV1:
    """Submit a gateway interrupt for one managed agent."""

    if _target_uses_pair_api(target):
        assert target.client is not None
        return pair_request(
            target.client.submit_managed_agent_gateway_request,
            target.agent_ref,
            HoumaoManagedAgentGatewayRequestCreate(
                kind="interrupt",
                payload=GatewayRequestPayloadInterruptV1(),
            ),
        )

    controller = _require_live_local_controller(target, operation="submit gateway interrupt")
    return controller.interrupt_via_gateway()


def gateway_send_keys(
    target: ManagedAgentTarget,
    *,
    sequence: str,
    escape_special_keys: bool,
) -> GatewayControlInputResultV1:
    """Submit raw gateway control input for one managed agent."""

    _raise_external_unsupported(target, operation="agents single ... gateway send-keys")

    request_model = GatewayControlInputRequestV1(
        sequence=sequence,
        escape_special_keys=escape_special_keys,
    )
    if target.mode == "server":
        assert target.client is not None
        return pair_request(
            target.client.send_managed_agent_gateway_control_input,
            target.agent_ref,
            request_model,
        )

    authority = _running_agent_authority(target, operation="send gateway control input")
    client = _require_live_gateway_client_for_controller(authority)
    try:
        return client.send_control_input(request_model)
    except GatewayHttpError as exc:
        raise click.ClickException(exc.detail) from exc


def gateway_ag_ui_publish(
    target: ManagedAgentTarget,
    *,
    request_model: AgUiEventPublishRequest,
) -> AgUiEventPublishResponse:
    """Publish an already-standard AG-UI event batch to one live Houmao gateway."""

    _raise_external_unsupported(
        target,
        operation="agents single ... gateway ag-ui publish",
        hint="Generate events with `houmao-mgr ag-ui impl render` or `houmao-mgr ag-ui protocol tool-call render` and deliver them with endpoint-specific tooling for third-party endpoints.",
    )
    target = _local_gateway_target_for_passive_pair(target, operation="ag-ui publish")
    if _target_uses_pair_api(target):
        raise click.ClickException(
            "AG-UI publish requires a live local Houmao gateway endpoint. "
            "Remote pair API forwarding is unsupported for this command."
        )

    authority = _running_agent_authority(target, operation="publish AG-UI events")
    client = _require_live_gateway_client_for_controller(authority)
    try:
        return client.publish_ag_ui_events(request_model)
    except GatewayHttpError as exc:
        raise click.ClickException(exc.detail) from exc


def gateway_tui_state(target: ManagedAgentTarget) -> HoumaoTerminalStateResponse:
    """Return raw gateway-owned TUI state for one managed agent."""

    _raise_external_unsupported(target, operation="agents single ... gateway tui state")

    if _target_uses_pair_api(target):
        assert target.client is not None
        return pair_request(target.client.get_managed_agent_gateway_tui_state, target.agent_ref)

    authority = _running_agent_authority(target, operation="show gateway TUI state")
    client = _require_live_gateway_client_for_controller(authority)
    try:
        return client.get_tui_state()
    except GatewayHttpError as exc:
        raise click.ClickException(exc.detail) from exc


def gateway_tui_history(target: ManagedAgentTarget) -> HoumaoTerminalSnapshotHistoryResponse:
    """Return raw gateway-owned TUI snapshot history for one managed agent."""

    _raise_external_unsupported(target, operation="agents single ... gateway tui history")

    if _target_uses_pair_api(target):
        assert target.client is not None
        return pair_request(target.client.get_managed_agent_gateway_tui_history, target.agent_ref)

    authority = _running_agent_authority(target, operation="show gateway TUI history")
    client = _require_live_gateway_client_for_controller(authority)
    try:
        return client.get_tui_history(limit=100)
    except GatewayHttpError as exc:
        raise click.ClickException(exc.detail) from exc


def gateway_tui_note_prompt(
    target: ManagedAgentTarget,
    *,
    prompt: str,
) -> HoumaoTerminalStateResponse:
    """Record prompt-note provenance through the live gateway tracker."""

    _raise_external_unsupported(target, operation="agents single ... gateway tui note-prompt")

    if _target_uses_pair_api(target):
        assert target.client is not None
        return pair_request(
            target.client.note_managed_agent_gateway_tui_prompt,
            target.agent_ref,
            prompt=prompt,
        )

    authority = _running_agent_authority(target, operation="record gateway TUI prompt note")
    client = _require_live_gateway_client_for_controller(authority)
    try:
        return client.note_tui_prompt_submission(prompt=prompt)
    except GatewayHttpError as exc:
        raise click.ClickException(exc.detail) from exc


def gateway_list_reminders(target: ManagedAgentTarget) -> GatewayReminderListV1:
    """Return the live gateway reminder set for one managed agent."""

    _raise_external_unsupported(target, operation="agents single ... gateway reminders list")

    if _target_uses_pair_api(target):
        assert target.client is not None
        return pair_request(target.client.list_managed_agent_gateway_reminders, target.agent_ref)

    authority = _running_agent_authority(target, operation="list gateway reminders")
    client = _require_live_gateway_client_for_controller(authority)
    try:
        return client.list_reminders()
    except GatewayHttpError as exc:
        raise click.ClickException(exc.detail) from exc


def gateway_get_reminder(
    target: ManagedAgentTarget,
    *,
    reminder_id: str,
) -> GatewayReminderV1:
    """Return one live gateway reminder for one managed agent."""

    _raise_external_unsupported(target, operation="agents single ... gateway reminders get")

    if _target_uses_pair_api(target):
        assert target.client is not None
        return pair_request(
            target.client.get_managed_agent_gateway_reminder,
            target.agent_ref,
            reminder_id,
        )

    authority = _running_agent_authority(target, operation="get gateway reminder")
    client = _require_live_gateway_client_for_controller(authority)
    try:
        return client.get_reminder(reminder_id=reminder_id)
    except GatewayHttpError as exc:
        raise click.ClickException(exc.detail) from exc


def gateway_create_reminders(
    target: ManagedAgentTarget,
    *,
    payload: GatewayReminderCreateBatchV1,
) -> GatewayReminderCreateResultV1:
    """Create one or more live gateway reminders for one managed agent."""

    _raise_external_unsupported(target, operation="agents single ... gateway reminders create")

    if _target_uses_pair_api(target):
        assert target.client is not None
        return pair_request(
            target.client.create_managed_agent_gateway_reminders,
            target.agent_ref,
            payload,
        )

    authority = _running_agent_authority(target, operation="create gateway reminders")
    client = _require_live_gateway_client_for_controller(authority)
    try:
        return client.create_reminders(payload)
    except GatewayHttpError as exc:
        raise click.ClickException(exc.detail) from exc


def gateway_put_reminder(
    target: ManagedAgentTarget,
    *,
    reminder_id: str,
    payload: GatewayReminderPutV1,
) -> GatewayReminderV1:
    """Replace one live gateway reminder for one managed agent."""

    _raise_external_unsupported(target, operation="agents single ... gateway reminders put")

    if _target_uses_pair_api(target):
        assert target.client is not None
        return pair_request(
            target.client.put_managed_agent_gateway_reminder,
            target.agent_ref,
            reminder_id,
            payload,
        )

    authority = _running_agent_authority(target, operation="set gateway reminder")
    client = _require_live_gateway_client_for_controller(authority)
    try:
        return client.put_reminder(reminder_id=reminder_id, payload=payload)
    except GatewayHttpError as exc:
        raise click.ClickException(exc.detail) from exc


def gateway_delete_reminder(
    target: ManagedAgentTarget,
    *,
    reminder_id: str,
) -> GatewayReminderDeleteResultV1:
    """Delete one live gateway reminder for one managed agent."""

    _raise_external_unsupported(target, operation="agents single ... gateway reminders delete")

    if _target_uses_pair_api(target):
        assert target.client is not None
        return pair_request(
            target.client.delete_managed_agent_gateway_reminder,
            target.agent_ref,
            reminder_id,
        )

    authority = _running_agent_authority(target, operation="remove gateway reminder")
    client = _require_live_gateway_client_for_controller(authority)
    try:
        return client.delete_reminder(reminder_id=reminder_id)
    except GatewayHttpError as exc:
        raise click.ClickException(exc.detail) from exc


def gateway_mail_notifier_status(
    target: ManagedAgentTarget,
    *,
    channel: MailboxChannel,
) -> GatewayMailNotifierStatusV1:
    """Return gateway mail-notifier status for one managed agent."""

    _raise_external_unsupported(target, operation="agents single ... gateway mail-notifier status")

    if _target_uses_pair_api(target):
        assert target.client is not None
        return pair_request(
            target.client.get_managed_agent_gateway_mail_notifier,
            target.agent_ref,
            channel=channel,
        )

    authority = _running_agent_authority(
        target,
        operation="show gateway mail-notifier status",
    )
    client = _require_live_gateway_client_for_controller(authority)
    try:
        return client.get_mail_notifier(
            channel=channel,
        )
    except GatewayHttpError as exc:
        raise click.ClickException(exc.detail) from exc


def gateway_mail_notifier_enable(
    target: ManagedAgentTarget,
    *,
    channel: MailboxChannel,
    interval_seconds: int,
    mode: GatewayMailNotifierMode = "any_inbox",
    appendix_text: str | None = None,
    context_error_policy: GatewayMailNotifierContextErrorPolicy = "continue_current",
    pre_notification_context_action: GatewayMailNotifierPreNotificationContextAction = "none",
) -> GatewayMailNotifierStatusV1:
    """Enable or update gateway mail-notifier state for one managed agent."""

    _raise_external_unsupported(target, operation="agents single ... gateway mail-notifier enable")

    request_model = (
        GatewayMailNotifierPutV1(
            interval_seconds=interval_seconds,
            mode=mode,
            appendix_text=appendix_text,
            context_error_policy=context_error_policy,
            pre_notification_context_action=pre_notification_context_action,
        )
        if appendix_text is not None
        else GatewayMailNotifierPutV1(
            interval_seconds=interval_seconds,
            mode=mode,
            context_error_policy=context_error_policy,
            pre_notification_context_action=pre_notification_context_action,
        )
    )
    if _target_uses_pair_api(target):
        assert target.client is not None
        return pair_request(
            target.client.put_managed_agent_gateway_mail_notifier,
            target.agent_ref,
            request_model,
            channel=channel,
        )

    authority = _running_agent_authority(
        target,
        operation="enable gateway mail-notifier",
    )
    client = _require_live_gateway_client_for_controller(authority)
    try:
        return client.put_mail_notifier(
            request_model,
            channel=channel,
        )
    except GatewayHttpError as exc:
        raise click.ClickException(exc.detail) from exc


def gateway_mail_notifier_disable(
    target: ManagedAgentTarget,
    *,
    channel: MailboxChannel,
) -> GatewayMailNotifierStatusV1:
    """Disable gateway mail-notifier state for one managed agent."""

    _raise_external_unsupported(target, operation="agents single ... gateway mail-notifier disable")

    if _target_uses_pair_api(target):
        assert target.client is not None
        return pair_request(
            target.client.delete_managed_agent_gateway_mail_notifier,
            target.agent_ref,
            channel=channel,
        )

    authority = _running_agent_authority(
        target,
        operation="disable gateway mail-notifier",
    )
    client = _require_live_gateway_client_for_controller(authority)
    try:
        return client.delete_mail_notifier(
            channel=channel,
        )
    except GatewayHttpError as exc:
        raise click.ClickException(exc.detail) from exc


def mailbox_status(target: ManagedAgentTarget) -> dict[str, object]:
    """Report offline membership for a locally controlled running body."""

    controller = _require_local_filesystem_mailbox_target(target, operation="status")
    binding = controller.launch_plan.mailboxes.offline.binding
    return {
        "schema_version": 2,
        "tracked_agent_id": target.identity.tracked_agent_id,
        "agent_name": controller.agent_identity,
        "agent_id": controller.agent_id,
        "channel": "offline",
        "registered": binding is not None,
        "revision": controller.launch_plan.mailboxes.offline.revision,
        "binding": None
        if binding is None
        else {
            "agent_id": binding.agent_id,
            "binding_id": binding.binding_id,
            "transport": binding.transport,
            "address": binding.address,
        },
        "activation_state": controller.mailbox_activation_state(),
    }


def register_mailbox_binding(
    target: ManagedAgentTarget,
    *,
    mailbox_root: Path | None = None,
    principal_id: str | None = None,
    address: str | None = None,
    registry_url: str | None = None,
    credential_file: Path | None = None,
    admin_credential_file: Path | None = None,
) -> dict[str, object]:
    """Join the selected local or remote offline registry without body relaunch."""

    controller = _require_local_filesystem_mailbox_target(target, operation="join")
    try:
        if registry_url is not None:
            if mailbox_root is not None or principal_id is not None:
                raise click.ClickException(
                    "Remote join cannot select registry-host paths or sender IDs."
                )
            if credential_file is None or admin_credential_file is None or address is None:
                raise click.ClickException(
                    "Remote join requires --address, --credential-file, and --admin-credential-file."
                )
            result = controller.register_remote_offline_mailbox(
                registry_url=registry_url,
                credential_file=credential_file,
                admin_credential_file=admin_credential_file,
                address=address,
            )
        else:
            if credential_file is not None or admin_credential_file is not None:
                raise click.ClickException("Remote credential options require --registry-url.")
            result = controller.register_filesystem_mailbox(
                mailbox_root=mailbox_root,
                principal_id=principal_id,
                address=address,
            )
    except (
        MailboxBootstrapError,
        ManagedMailboxOperationError,
        SessionManifestError,
        ValueError,
        RuntimeError,
    ) as exc:
        raise click.ClickException(str(exc)) from exc
    binding = result.mailbox
    assert binding is not None
    return {
        "schema_version": 2,
        "tracked_agent_id": target.identity.tracked_agent_id,
        "agent_name": controller.agent_identity,
        "agent_id": controller.agent_id,
        "channel": "offline",
        "binding_id": binding.binding_id,
        "transport": binding.transport,
        "address": binding.address,
        "revision": binding.bindings_version,
        "activation_state": result.activation_state,
        "shared_registration": result.shared_lifecycle_result,
        "warnings": list(controller.operation_warnings),
    }


def unregister_mailbox_binding(target: ManagedAgentTarget, *, mode: str) -> dict[str, object]:
    """Release offline membership explicitly, preserving the online binding."""

    controller = _require_local_filesystem_mailbox_target(target, operation="leave")
    previous = controller.launch_plan.mailboxes.offline.binding
    if previous is None:
        raise click.ClickException("Target has no configured offline mailbox.")
    try:
        result = controller.unregister_filesystem_mailbox(mode=cast(Any, mode))
    except (SessionManifestError, ValueError, RuntimeError) as exc:
        raise click.ClickException(str(exc)) from exc
    return {
        "schema_version": 2,
        "tracked_agent_id": target.identity.tracked_agent_id,
        "agent_name": controller.agent_identity,
        "agent_id": controller.agent_id,
        "channel": "offline",
        "binding_id": previous.binding_id,
        "transport": previous.transport,
        "address": previous.address,
        "activation_state": result.activation_state,
        "shared_unregistration": result.shared_lifecycle_result,
        "warnings": list(controller.operation_warnings),
    }


def _local_manager_mail_status(authority: _RunningAgentAuthority) -> GatewayMailStatusV1:
    """Report both configured channels and independent backend availability."""

    payload = _read_running_agent_manifest(authority)
    mailboxes = mailboxes_resolved_config_from_payload(
        payload.launch_plan.mailboxes.model_dump(mode="json"), manifest_path=authority.manifest_path
    )
    summaries: dict[str, MailboxChannelStatusV1 | None] = {}
    for channel in ("offline", "online"):
        slot = mailboxes.slot_for(channel)
        binding = slot.binding
        if binding is None:
            summaries[channel] = None
            continue
        error = None
        supported_operations: list[str] = []
        limitations: list[str] = []
        try:
            backend_status = build_gateway_mailbox_adapter(binding).status()
            supported_operations = [
                action for action in backend_status.supported_operations() if action != "post"
            ]
            if not backend_status.placement_writable:
                limitations.append("Message placement requires separate mailbox owner authority.")
        except (GatewayMailboxError, ValueError, OSError):
            error = "Mailbox backend is unavailable."
        summaries[channel] = MailboxChannelStatusV1(
            agent_id=binding.agent_id,
            channel=channel,
            binding_id=binding.binding_id,
            revision=slot.revision,
            address=binding.address,
            transport=binding.transport,
            available=error is None,
            error=error,
            supported_operations=supported_operations,
            limitations=limitations,
        )
    return GatewayMailStatusV1(
        agent_id=payload.agent_id,
        offline=summaries["offline"],
        online=summaries["online"],
        canonical_mail_identity=mailboxes.canonical_mail_identity,
    )


def _local_manager_mail_list(
    authority: _RunningAgentAuthority,
    *,
    channel: MailboxChannel,
    expected_binding_id: str | None = None,
    box: str,
    read_state: str,
    answered_state: str,
    archived: bool | None,
    limit: int,
    since: str | None,
    cursor: str | None,
) -> GatewayMailListResponseV1:
    """List mailbox contents through manager-owned local execution."""

    adapter = _local_mailbox_adapter(
        authority,
        channel=channel,
        expected_binding_id=expected_binding_id,
    )
    try:
        page = adapter.list_page(
            box=box,
            read_state=read_state,
            answered_state=answered_state,
            archived=archived,
            limit=limit,
            since=since,
            cursor=cursor,
        )
        status = adapter.status()
    except GatewayMailboxMutationError as exc:
        raise click.ClickException(json.dumps(exc.safe_payload(), sort_keys=True)) from exc
    except (GatewayMailboxError, MailboxScopeError) as exc:
        raise click.ClickException(str(exc)) from exc
    from houmao.mailbox.pagination import build_mail_page_response

    return build_mail_page_response(identity=status, box=box, page=page)


def _local_manager_mail_peek(
    authority: _RunningAgentAuthority,
    *,
    channel: MailboxChannel,
    expected_binding_id: str | None = None,
    message_ref: str,
    box: str | None,
) -> GatewayMailMessageResponseV1:
    """Peek at one mailbox message through manager-owned local execution."""

    adapter = _local_mailbox_adapter(
        authority,
        channel=channel,
        expected_binding_id=expected_binding_id,
    )
    try:
        message = adapter.peek(message_ref=message_ref, box=box)
        status = adapter.status()
    except GatewayMailboxMutationError as exc:
        raise click.ClickException(json.dumps(exc.safe_payload(), sort_keys=True)) from exc
    except (GatewayMailboxError, MailboxScopeError) as exc:
        raise click.ClickException(str(exc)) from exc
    return GatewayMailMessageResponseV1(
        operation="peek",
        transport=status.transport,
        principal_id=status.principal_id,
        address=status.address,
        message=message,
    )


def _local_manager_mail_read(
    authority: _RunningAgentAuthority,
    *,
    channel: MailboxChannel,
    expected_binding_id: str | None = None,
    message_ref: str,
    box: str | None,
) -> GatewayMailMessageResponseV1:
    """Read one mailbox message through manager-owned local execution."""

    adapter = _local_mailbox_adapter(
        authority,
        channel=channel,
        expected_binding_id=expected_binding_id,
    )
    try:
        message = adapter.read(message_ref=message_ref, box=box)
        status = adapter.status()
    except GatewayMailboxMutationError as exc:
        raise click.ClickException(json.dumps(exc.safe_payload(), sort_keys=True)) from exc
    except (GatewayMailboxError, MailboxScopeError) as exc:
        raise click.ClickException(str(exc)) from exc
    return GatewayMailMessageResponseV1(
        operation="read",
        transport=status.transport,
        principal_id=status.principal_id,
        address=status.address,
        message=message,
    )


def _local_manager_mail_send(
    authority: _RunningAgentAuthority,
    *,
    channel: MailboxChannel,
    expected_binding_id: str | None = None,
    to_recipients: Sequence[str],
    cc_recipients: Sequence[str],
    subject: str,
    body_content: str,
    attachments: Sequence[GatewayMailAttachmentUploadV1],
    notify_block: MailboxNotifyBlock | None = None,
    notify_auth: MailboxNotifyAuth | None = None,
) -> GatewayMailActionResponseV1:
    """Send mail through manager-owned local execution."""

    adapter = _local_mailbox_adapter(
        authority,
        channel=channel,
        expected_binding_id=expected_binding_id,
    )
    try:
        message = adapter.send(
            to_addresses=to_recipients,
            cc_addresses=cc_recipients,
            subject=subject,
            body_content=body_content,
            attachments=attachments,
            notify_block=notify_block,
            notify_auth=notify_auth,
        )
        status = adapter.status()
    except GatewayMailboxMutationError as exc:
        raise click.ClickException(json.dumps(exc.safe_payload(), sort_keys=True)) from exc
    except (GatewayMailboxError, MailboxScopeError) as exc:
        raise click.ClickException(str(exc)) from exc
    return GatewayMailActionResponseV1(
        operation="send",
        transport=status.transport,
        principal_id=status.principal_id,
        address=status.address,
        message=message,
    )


def _local_manager_mail_reply(
    authority: _RunningAgentAuthority,
    *,
    channel: MailboxChannel,
    expected_binding_id: str | None = None,
    message_ref: str,
    body_content: str,
    attachments: Sequence[GatewayMailAttachmentUploadV1],
    notify_block: MailboxNotifyBlock | None = None,
    notify_auth: MailboxNotifyAuth | None = None,
) -> GatewayMailActionResponseV1:
    """Reply through manager-owned local execution."""

    adapter = _local_mailbox_adapter(
        authority,
        channel=channel,
        expected_binding_id=expected_binding_id,
    )
    try:
        message = adapter.reply(
            message_ref=message_ref,
            body_content=body_content,
            attachments=attachments,
            notify_block=notify_block,
            notify_auth=notify_auth,
        )
        status = adapter.status()
    except GatewayMailboxMutationError as exc:
        raise click.ClickException(json.dumps(exc.safe_payload(), sort_keys=True)) from exc
    except (GatewayMailboxError, MailboxScopeError) as exc:
        raise click.ClickException(str(exc)) from exc
    return GatewayMailActionResponseV1(
        operation="reply",
        transport=status.transport,
        principal_id=status.principal_id,
        address=status.address,
        message=message,
    )


def _local_manager_mail_post(
    authority: _RunningAgentAuthority,
    *,
    channel: MailboxChannel,
    expected_binding_id: str | None = None,
    subject: str,
    body_content: str,
    reply_policy: OperatorOriginReplyPolicy,
    attachments: Sequence[GatewayMailAttachmentUploadV1],
    notify_block: MailboxNotifyBlock | None = None,
    notify_auth: MailboxNotifyAuth | None = None,
) -> GatewayMailActionResponseV1:
    """Post operator-origin mail through manager-owned local execution."""

    adapter = _local_mailbox_adapter(
        authority,
        channel=channel,
        expected_binding_id=expected_binding_id,
    )
    try:
        message = adapter.post(
            subject=subject,
            body_content=body_content,
            reply_policy=reply_policy,
            attachments=attachments,
            notify_block=notify_block,
            notify_auth=notify_auth,
        )
        status = adapter.status()
    except GatewayMailboxMutationError as exc:
        raise click.ClickException(json.dumps(exc.safe_payload(), sort_keys=True)) from exc
    except (GatewayMailboxError, MailboxScopeError) as exc:
        raise click.ClickException(str(exc)) from exc
    return GatewayMailActionResponseV1(
        operation="post",
        transport=status.transport,
        principal_id=status.principal_id,
        address=status.address,
        message=message,
    )


def _local_manager_mail_mark(
    authority: _RunningAgentAuthority,
    *,
    channel: MailboxChannel,
    expected_binding_id: str | None = None,
    message_refs: Sequence[str],
    read: bool | None,
    answered: bool | None,
    archived: bool | None,
) -> GatewayMailLifecycleResponseV1:
    """Mark mailbox state through manager-owned local execution."""

    adapter = _local_mailbox_adapter(
        authority,
        channel=channel,
        expected_binding_id=expected_binding_id,
    )
    try:
        messages = adapter.mark(
            message_refs=message_refs,
            read=read,
            answered=answered,
            archived=archived,
        )
        status = adapter.status()
    except GatewayMailboxMutationError as exc:
        raise click.ClickException(json.dumps(exc.safe_payload(), sort_keys=True)) from exc
    except (GatewayMailboxError, MailboxScopeError) as exc:
        raise click.ClickException(str(exc)) from exc
    return GatewayMailLifecycleResponseV1(
        operation="mark",
        transport=status.transport,
        principal_id=status.principal_id,
        address=status.address,
        message_count=len(messages),
        messages=messages,
    )


def _local_manager_mail_move(
    authority: _RunningAgentAuthority,
    *,
    channel: MailboxChannel,
    expected_binding_id: str | None = None,
    message_refs: Sequence[str],
    destination_box: str,
) -> GatewayMailLifecycleResponseV1:
    """Move mailbox messages through manager-owned local execution."""

    adapter = _local_mailbox_adapter(
        authority,
        channel=channel,
        expected_binding_id=expected_binding_id,
    )
    try:
        messages = adapter.move(message_refs=message_refs, destination_box=destination_box)
        status = adapter.status()
    except GatewayMailboxMutationError as exc:
        raise click.ClickException(json.dumps(exc.safe_payload(), sort_keys=True)) from exc
    except (GatewayMailboxError, MailboxScopeError) as exc:
        raise click.ClickException(str(exc)) from exc
    return GatewayMailLifecycleResponseV1(
        operation="move",
        transport=status.transport,
        principal_id=status.principal_id,
        address=status.address,
        message_count=len(messages),
        messages=messages,
    )


def _local_manager_mail_archive(
    authority: _RunningAgentAuthority,
    *,
    channel: MailboxChannel,
    expected_binding_id: str | None = None,
    message_refs: Sequence[str],
) -> GatewayMailLifecycleResponseV1:
    """Archive mailbox messages through manager-owned local execution."""

    adapter = _local_mailbox_adapter(
        authority,
        channel=channel,
        expected_binding_id=expected_binding_id,
    )
    try:
        messages = adapter.archive(message_refs=message_refs)
        status = adapter.status()
    except GatewayMailboxMutationError as exc:
        raise click.ClickException(json.dumps(exc.safe_payload(), sort_keys=True)) from exc
    except (GatewayMailboxError, MailboxScopeError) as exc:
        raise click.ClickException(str(exc)) from exc
    return GatewayMailLifecycleResponseV1(
        operation="archive",
        transport=status.transport,
        principal_id=status.principal_id,
        address=status.address,
        message_count=len(messages),
        messages=messages,
    )


def online_mailbox_status(target: ManagedAgentTarget) -> OnlineBindingStatus:
    """Read online configuration through the running gateway companion."""

    if _target_uses_pair_api(target):
        assert target.client is not None
        return pair_request(target.client.get_managed_agent_online_binding, target.agent_ref)
    controller = _require_live_local_controller(target, operation="inspect online mailbox status")
    client = _require_live_gateway_client_for_controller(controller)
    try:
        return client.online_binding_status()
    except GatewayHttpError as exc:
        raise click.ClickException(str(exc)) from exc


def control_online_mailbox(
    target: ManagedAgentTarget,
    operation: str,
    request: OnlineAttachRequest | OnlineControlRequest,
) -> OnlineBindingStatus:
    """Forward one explicit revision-pinned operator action without retries."""

    if _target_uses_pair_api(target):
        assert target.client is not None
        method = getattr(target.client, f"{operation}_managed_agent_online_binding")
        try:
            result = method(target.agent_ref, request)
        except CaoApiError as exc:
            detail = exc.payload.get("detail") if isinstance(exc.payload, dict) else None
            try:
                failure = OnlineControlFailure.model_validate(detail)
            except ValidationError:
                raise click.ClickException(exc.detail) from exc
            raise click.ClickException(failure.detail) from exc
        return OnlineBindingStatus.model_validate(result.model_dump(mode="json"))
    controller = _require_live_local_controller(target, operation="control online mailbox binding")
    client = _require_live_gateway_client_for_controller(controller)
    try:
        result = getattr(client, f"{operation}_online_binding")(request)
        return OnlineBindingStatus.model_validate(result.model_dump(mode="json"))
    except GatewayHttpError as exc:
        raise click.ClickException(str(exc)) from exc


def _local_mailbox_adapter(
    authority: _RunningAgentAuthority,
    *,
    channel: MailboxChannel,
    expected_binding_id: str | None = None,
) -> GatewayMailboxAdapter:
    """Resolve one current channel and reject stale targeting before backend I/O."""

    try:
        payload = _read_running_agent_manifest(authority)
        mailboxes = mailboxes_resolved_config_from_payload(
            payload.launch_plan.mailboxes.model_dump(mode="json"),
            manifest_path=authority.manifest_path,
        )
        binding = mailboxes.binding_for(channel)
        if binding is None:
            raise click.ClickException(f"Target has no configured {channel} mailbox.")
        if binding.agent_id != authority.agent_id:
            raise click.ClickException("Mailbox owner differs from the selected agent.")
        scope = MailScope(binding.agent_id, channel, binding.binding_id)
        if expected_binding_id is not None:
            scope.require_binding(expected_binding_id)
        return build_scoped_mailbox_adapter(
            binding,
            authority=OnlineAuthorityContext(
                authority.manifest_path, payload.agent_id, payload.runtime.session_id
            ),
        )
    except (GatewayMailboxError, ValueError, SessionManifestError) as exc:
        raise click.ClickException(str(exc)) from exc


def _resolve_mail_expected_binding(
    target: ManagedAgentTarget,
    channel: MailboxChannel,
    expected_binding_id: str | None,
) -> str:
    """Pin one operation to a selected binding without retrying a replacement."""

    if _target_uses_pair_api(target):
        assert target.client is not None
        summary = pair_request(target.client.get_managed_agent_mail_status, target.agent_ref)
        binding = getattr(summary, channel)
        if binding is None:
            raise click.ClickException(f"Target has no configured {channel} mailbox.")
        current_id = binding.binding_id
    else:
        authority = _running_agent_authority(target, operation=f"resolve {channel} mail")
        payload = _read_running_agent_manifest(authority)
        slot = getattr(payload.launch_plan.mailboxes, channel)
        if slot.binding is None:
            raise click.ClickException(f"Target has no configured {channel} mailbox.")
        current_id = slot.binding.binding_id
    if expected_binding_id is not None and expected_binding_id != current_id:
        raise click.ClickException("Mailbox binding changed; resolve the selected channel again.")
    return str(current_id)


def _gateway_mail_send(
    client: GatewayClient,
    *,
    channel: MailboxChannel,
    expected_binding_id: str,
    to_recipients: Sequence[str],
    cc_recipients: Sequence[str],
    subject: str,
    body_content: str,
    attachments: Sequence[GatewayMailAttachmentUploadV1],
    notify_block: MailboxNotifyBlock | None = None,
    notify_auth: MailboxNotifyAuth | None = None,
) -> GatewayMailActionResponseV1:
    """Send mail through one live loopback gateway client."""

    try:
        return client.send_mail(
            GatewayMailSendRequestV1(
                to=list(to_recipients),
                cc=list(cc_recipients),
                subject=subject,
                body_content=body_content,
                attachments=list(attachments),
                notify_block=notify_block,
                notify_auth=notify_auth,
                expected_binding_id=expected_binding_id,
            ),
            channel=channel,
        )
    except GatewayHttpError as exc:
        raise click.ClickException(exc.detail) from exc


def _gateway_mail_reply(
    client: GatewayClient,
    *,
    channel: MailboxChannel,
    expected_binding_id: str,
    message_ref: str,
    body_content: str,
    attachments: Sequence[GatewayMailAttachmentUploadV1],
    notify_block: MailboxNotifyBlock | None = None,
    notify_auth: MailboxNotifyAuth | None = None,
) -> GatewayMailActionResponseV1:
    """Reply through one live loopback gateway client."""

    try:
        return client.reply_mail(
            GatewayMailReplyRequestV1(
                message_ref=message_ref,
                body_content=body_content,
                attachments=list(attachments),
                notify_block=notify_block,
                notify_auth=notify_auth,
                expected_binding_id=expected_binding_id,
            ),
            channel=channel,
        )
    except GatewayHttpError as exc:
        raise click.ClickException(exc.detail) from exc


def _gateway_mail_post(
    client: GatewayClient,
    *,
    channel: MailboxChannel,
    expected_binding_id: str,
    subject: str,
    body_content: str,
    reply_policy: OperatorOriginReplyPolicy,
    attachments: Sequence[GatewayMailAttachmentUploadV1],
    notify_block: MailboxNotifyBlock | None = None,
    notify_auth: MailboxNotifyAuth | None = None,
) -> GatewayMailActionResponseV1:
    """Post operator-origin mail through one live loopback gateway client."""

    try:
        return client.post_mail(
            GatewayMailPostRequestV1(
                subject=subject,
                body_content=body_content,
                reply_policy=reply_policy,
                attachments=list(attachments),
                notify_block=notify_block,
                notify_auth=notify_auth,
                expected_binding_id=expected_binding_id,
            ),
            channel=channel,
        )
    except GatewayHttpError as exc:
        raise click.ClickException(exc.detail) from exc


def _gateway_mail_mark(
    client: GatewayClient,
    *,
    channel: MailboxChannel,
    expected_binding_id: str,
    message_refs: Sequence[str],
    read: bool | None,
    answered: bool | None,
    archived: bool | None,
) -> GatewayMailLifecycleResponseV1:
    """Mark mailbox state through one live loopback gateway client."""

    try:
        return client.mark_mail(
            GatewayMailMarkRequestV1(
                message_refs=list(message_refs),
                read=read,
                answered=answered,
                archived=archived,
                expected_binding_id=expected_binding_id,
            ),
            channel=channel,
        )
    except GatewayHttpError as exc:
        raise click.ClickException(exc.detail) from exc


def _gateway_mail_move(
    client: GatewayClient,
    *,
    channel: MailboxChannel,
    expected_binding_id: str,
    message_refs: Sequence[str],
    destination_box: str,
) -> GatewayMailLifecycleResponseV1:
    """Move mailbox messages through one live loopback gateway client."""

    try:
        return client.move_mail(
            GatewayMailMoveRequestV1(
                message_refs=list(message_refs),
                destination_box=destination_box,
                expected_binding_id=expected_binding_id,
            ),
            channel=channel,
        )
    except GatewayHttpError as exc:
        raise click.ClickException(exc.detail) from exc


def _gateway_mail_archive(
    client: GatewayClient,
    *,
    channel: MailboxChannel,
    expected_binding_id: str,
    message_refs: Sequence[str],
) -> GatewayMailLifecycleResponseV1:
    """Archive mailbox messages through one live loopback gateway client."""

    try:
        return client.archive_mail(
            GatewayMailArchiveRequestV1(
                message_refs=list(message_refs),
                expected_binding_id=expected_binding_id,
            ),
            channel=channel,
        )
    except GatewayHttpError as exc:
        raise click.ClickException(exc.detail) from exc


def mail_status(target: ManagedAgentTarget) -> object:
    """Return mailbox status for one managed agent."""

    if _target_uses_pair_api(target):
        assert target.client is not None
        return build_verified_mail_command_result(
            operation="status",
            execution_path="gateway_backed",
            payload=pair_request(target.client.get_managed_agent_mail_status, target.agent_ref),
        )

    authority = _running_agent_authority(target, operation="show managed-agent mail status")
    client = _live_gateway_client_for_controller(authority, private=True, require_available=True)
    if client is not None:
        try:
            result = client.mail_status()
        except GatewayHttpError as exc:
            raise click.ClickException(exc.detail) from None
        return build_verified_mail_command_result(
            operation="status", execution_path="gateway_backed", payload=result
        )
    return build_verified_mail_command_result(
        operation="status",
        execution_path="manager_direct",
        payload=_local_manager_mail_status(authority),
    )


def mail_list(
    target: ManagedAgentTarget,
    *,
    channel: MailboxChannel,
    expected_binding_id: str | None = None,
    box: str,
    read_state: str,
    answered_state: str,
    archived: bool | None,
    limit: int,
    since: str | None,
    cursor: str | None,
) -> object:
    """List mailbox contents for one managed agent."""

    expected_binding_id = _resolve_mail_expected_binding(target, channel, expected_binding_id)

    if _target_uses_pair_api(target):
        assert target.client is not None
        from houmao.server.models import HoumaoManagedAgentMailListRequest

        return build_verified_mail_command_result(
            operation="list",
            execution_path="gateway_backed",
            payload=pair_request(
                target.client.list_managed_agent_mail,
                target.agent_ref,
                HoumaoManagedAgentMailListRequest(
                    box=box,
                    read_state=cast(GatewayMailReadFilter, read_state),
                    answered_state=cast(GatewayMailAnsweredFilter, answered_state),
                    archived=archived,
                    limit=limit,
                    since=since,
                    cursor=cursor,
                    expected_binding_id=expected_binding_id,
                ),
                channel=channel,
            ),
        )

    authority = _running_agent_authority(target, operation="list managed-agent mail")
    client = _live_gateway_client_for_controller(authority, private=True, require_available=True)
    if client is not None:
        try:
            result = client.list_mail(
                GatewayMailListRequestV1(
                    box=box,
                    read_state=cast(GatewayMailReadFilter, read_state),
                    answered_state=cast(GatewayMailAnsweredFilter, answered_state),
                    archived=archived,
                    limit=limit,
                    since=since,
                    cursor=cursor,
                    expected_binding_id=expected_binding_id,
                ),
                channel=channel,
            )
        except GatewayHttpError as exc:
            raise click.ClickException(exc.detail) from None
        return build_verified_mail_command_result(
            operation="list", execution_path="gateway_backed", payload=result
        )
    return build_verified_mail_command_result(
        operation="list",
        execution_path="manager_direct",
        payload=_local_manager_mail_list(
            authority,
            box=box,
            read_state=read_state,
            answered_state=answered_state,
            archived=archived,
            limit=limit,
            since=since,
            cursor=cursor,
            channel=channel,
            expected_binding_id=expected_binding_id,
        ),
    )


def mail_peek(
    target: ManagedAgentTarget,
    *,
    channel: MailboxChannel,
    expected_binding_id: str | None = None,
    message_ref: str,
    box: str | None,
) -> object:
    """Peek at one mailbox message for one managed agent."""

    expected_binding_id = _resolve_mail_expected_binding(target, channel, expected_binding_id)

    if _target_uses_pair_api(target):
        assert target.client is not None
        from houmao.server.models import HoumaoManagedAgentMailMessageRequest

        return build_verified_mail_command_result(
            operation="peek",
            execution_path="gateway_backed",
            payload=pair_request(
                target.client.peek_managed_agent_mail,
                target.agent_ref,
                HoumaoManagedAgentMailMessageRequest(
                    message_ref=message_ref,
                    box=box,
                    expected_binding_id=expected_binding_id,
                ),
                channel=channel,
            ),
        )

    authority = _running_agent_authority(target, operation="peek managed-agent mail")
    client = _live_gateway_client_for_controller(authority, private=True, require_available=True)
    if client is not None:
        try:
            result = client.peek_mail(
                GatewayMailMessageRequestV1(
                    message_ref=message_ref,
                    box=box,
                    expected_binding_id=expected_binding_id,
                ),
                channel=channel,
            )
        except GatewayHttpError as exc:
            raise click.ClickException(exc.detail) from None
        return build_verified_mail_command_result(
            operation="peek", execution_path="gateway_backed", payload=result
        )
    return build_verified_mail_command_result(
        operation="peek",
        execution_path="manager_direct",
        payload=_local_manager_mail_peek(
            authority,
            message_ref=message_ref,
            box=box,
            channel=channel,
            expected_binding_id=expected_binding_id,
        ),
    )


def mail_read(
    target: ManagedAgentTarget,
    *,
    channel: MailboxChannel,
    expected_binding_id: str | None = None,
    message_ref: str,
    box: str | None,
) -> object:
    """Read one mailbox message for one managed agent."""

    expected_binding_id = _resolve_mail_expected_binding(target, channel, expected_binding_id)

    if _target_uses_pair_api(target):
        assert target.client is not None
        from houmao.server.models import HoumaoManagedAgentMailMessageRequest

        return build_verified_mail_command_result(
            operation="read",
            execution_path="gateway_backed",
            payload=pair_request(
                target.client.read_managed_agent_mail,
                target.agent_ref,
                HoumaoManagedAgentMailMessageRequest(
                    message_ref=message_ref,
                    box=box,
                    expected_binding_id=expected_binding_id,
                ),
                channel=channel,
            ),
        )

    authority = _running_agent_authority(target, operation="read managed-agent mail")
    client = _live_gateway_client_for_controller(authority, private=True, require_available=True)
    if client is not None:
        try:
            result = client.read_mail(
                GatewayMailMessageRequestV1(
                    message_ref=message_ref,
                    box=box,
                    expected_binding_id=expected_binding_id,
                ),
                channel=channel,
            )
        except GatewayHttpError as exc:
            raise click.ClickException(exc.detail) from None
        return build_verified_mail_command_result(
            operation="read", execution_path="gateway_backed", payload=result
        )
    return build_verified_mail_command_result(
        operation="read",
        execution_path="manager_direct",
        payload=_local_manager_mail_read(
            authority,
            message_ref=message_ref,
            box=box,
            channel=channel,
            expected_binding_id=expected_binding_id,
        ),
    )


def mail_send(
    target: ManagedAgentTarget,
    *,
    channel: MailboxChannel,
    expected_binding_id: str | None = None,
    to_recipients: list[str],
    cc_recipients: list[str],
    subject: str,
    body_content: str,
    attachments: Sequence[GatewayMailAttachmentUploadV1],
    notify_block: MailboxNotifyBlock | None = None,
    notify_auth: MailboxNotifyAuth | None = None,
) -> dict[str, object]:
    """Send a mailbox message for one managed agent."""

    expected_binding_id = _resolve_mail_expected_binding(target, channel, expected_binding_id)

    if _target_uses_pair_api(target):
        assert target.client is not None
        from houmao.server.models import HoumaoManagedAgentMailSendRequest

        return verified_mail_receipt(
            channel=channel,
            binding_id=expected_binding_id,
            execution_path="gateway_backed",
            payload=pair_request(
                target.client.send_managed_agent_mail,
                target.agent_ref,
                HoumaoManagedAgentMailSendRequest(
                    to=to_recipients,
                    cc=cc_recipients,
                    subject=subject,
                    body_content=body_content,
                    attachments=list(attachments),
                    notify_block=notify_block,
                    notify_auth=notify_auth,
                    expected_binding_id=expected_binding_id,
                ),
                channel=channel,
            ),
        )

    authority = _running_agent_authority(target, operation="send managed-agent mail")
    gateway_client = _live_gateway_client_for_controller(
        authority, private=True, require_available=True
    )
    if gateway_client is not None:
        return verified_mail_receipt(
            channel=channel,
            binding_id=expected_binding_id,
            execution_path="gateway_backed",
            payload=_gateway_mail_send(
                gateway_client,
                to_recipients=to_recipients,
                cc_recipients=cc_recipients,
                subject=subject,
                body_content=body_content,
                attachments=attachments,
                notify_block=notify_block,
                notify_auth=notify_auth,
                channel=channel,
                expected_binding_id=expected_binding_id,
            ),
        )

    if (
        target.identity.transport != "tui"
        or _local_manager_mail_authority_error(
            authority, channel=channel, expected_binding_id=expected_binding_id
        )
        is None
    ):
        return verified_mail_receipt(
            channel=channel,
            binding_id=expected_binding_id,
            execution_path="manager_direct",
            payload=_local_manager_mail_send(
                authority,
                to_recipients=to_recipients,
                cc_recipients=cc_recipients,
                subject=subject,
                body_content=body_content,
                attachments=attachments,
                notify_block=notify_block,
                notify_auth=notify_auth,
                channel=channel,
                expected_binding_id=expected_binding_id,
            ),
        )

    # Preserve the submission-only fallback when verified direct or gateway-backed
    # execution is unavailable for a live TUI-managed session. The TUI submission
    # path cannot deliver the typed `notify_block`/`notify_auth` envelope fields
    # because the live agent composes the canonical envelope itself; senders that
    # need that delivery path should encode the block as a `houmao-notify` body
    # fence so the agent's send tooling extracts it at composition time.
    submission = _run_local_mail_prompt(
        controller=_require_live_local_controller(target, operation="submit TUI mail"),
        operation="send",
        args={
            "to": to_recipients,
            "cc": cc_recipients,
            "subject": subject,
            "body_content": body_content,
            "attachments": [attachment.model_dump(mode="json") for attachment in attachments],
        },
        channel=channel,
        expected_binding_id=expected_binding_id,
    )
    receipt = submitted_mail_receipt(submission, channel=channel, binding_id=expected_binding_id)
    receipt.update(to=to_recipients, cc=cc_recipients, subject=subject)
    return receipt


def mail_post(
    target: ManagedAgentTarget,
    *,
    channel: MailboxChannel,
    expected_binding_id: str | None = None,
    subject: str,
    body_content: str,
    reply_policy: OperatorOriginReplyPolicy,
    attachments: Sequence[GatewayMailAttachmentUploadV1],
    notify_block: MailboxNotifyBlock | None = None,
    notify_auth: MailboxNotifyAuth | None = None,
) -> dict[str, object]:
    """Post one operator-origin mailbox note into one managed agent inbox."""

    expected_binding_id = _resolve_mail_expected_binding(target, channel, expected_binding_id)

    if _target_uses_pair_api(target):
        assert target.client is not None
        from houmao.server.models import HoumaoManagedAgentMailPostRequest

        return verified_mail_receipt(
            channel=channel,
            binding_id=expected_binding_id,
            execution_path="gateway_backed",
            payload=pair_request(
                target.client.post_managed_agent_mail,
                target.agent_ref,
                HoumaoManagedAgentMailPostRequest(
                    subject=subject,
                    body_content=body_content,
                    reply_policy=reply_policy,
                    attachments=list(attachments),
                    notify_block=notify_block,
                    notify_auth=notify_auth,
                    expected_binding_id=expected_binding_id,
                ),
                channel=channel,
            ),
        )

    authority = _running_agent_authority(
        target,
        operation="post operator-origin managed-agent mail",
    )
    gateway_client = _live_gateway_client_for_controller(
        authority, private=False, require_available=True
    )
    if gateway_client is not None:
        return verified_mail_receipt(
            channel=channel,
            binding_id=expected_binding_id,
            execution_path="gateway_backed",
            payload=_gateway_mail_post(
                gateway_client,
                subject=subject,
                body_content=body_content,
                reply_policy=reply_policy,
                attachments=attachments,
                notify_block=notify_block,
                notify_auth=notify_auth,
                channel=channel,
                expected_binding_id=expected_binding_id,
            ),
        )

    if (
        target.identity.transport != "tui"
        or _local_manager_mail_authority_error(
            authority, channel=channel, expected_binding_id=expected_binding_id
        )
        is None
    ):
        return verified_mail_receipt(
            channel=channel,
            binding_id=expected_binding_id,
            execution_path="manager_direct",
            payload=_local_manager_mail_post(
                authority,
                subject=subject,
                body_content=body_content,
                reply_policy=reply_policy,
                attachments=attachments,
                notify_block=notify_block,
                notify_auth=notify_auth,
                channel=channel,
                expected_binding_id=expected_binding_id,
            ),
        )

    raise click.ClickException(
        "operator-origin mailbox post requires authoritative manager or gateway mail authority; "
        "live TUI submission fallback is intentionally unsupported"
    )


def mail_reply(
    target: ManagedAgentTarget,
    *,
    channel: MailboxChannel,
    expected_binding_id: str | None = None,
    message_ref: str,
    body_content: str,
    attachments: Sequence[GatewayMailAttachmentUploadV1],
    notify_block: MailboxNotifyBlock | None = None,
    notify_auth: MailboxNotifyAuth | None = None,
) -> dict[str, object]:
    """Reply to a mailbox message for one managed agent."""

    expected_binding_id = _resolve_mail_expected_binding(target, channel, expected_binding_id)

    if _target_uses_pair_api(target):
        assert target.client is not None
        from houmao.server.models import HoumaoManagedAgentMailReplyRequest

        return verified_mail_receipt(
            channel=channel,
            binding_id=expected_binding_id,
            parent_message_ref=message_ref,
            execution_path="gateway_backed",
            payload=pair_request(
                target.client.reply_managed_agent_mail,
                target.agent_ref,
                HoumaoManagedAgentMailReplyRequest(
                    message_ref=message_ref,
                    body_content=body_content,
                    attachments=list(attachments),
                    notify_block=notify_block,
                    notify_auth=notify_auth,
                    expected_binding_id=expected_binding_id,
                ),
                channel=channel,
            ),
        )

    authority = _running_agent_authority(target, operation="reply to managed-agent mail")
    gateway_client = _live_gateway_client_for_controller(
        authority, private=True, require_available=True
    )
    if gateway_client is not None:
        return verified_mail_receipt(
            channel=channel,
            binding_id=expected_binding_id,
            parent_message_ref=message_ref,
            execution_path="gateway_backed",
            payload=_gateway_mail_reply(
                gateway_client,
                message_ref=message_ref,
                body_content=body_content,
                attachments=attachments,
                notify_block=notify_block,
                notify_auth=notify_auth,
                channel=channel,
                expected_binding_id=expected_binding_id,
            ),
        )

    if (
        target.identity.transport != "tui"
        or _local_manager_mail_authority_error(
            authority, channel=channel, expected_binding_id=expected_binding_id
        )
        is None
    ):
        return verified_mail_receipt(
            channel=channel,
            binding_id=expected_binding_id,
            parent_message_ref=message_ref,
            execution_path="manager_direct",
            payload=_local_manager_mail_reply(
                authority,
                message_ref=message_ref,
                body_content=body_content,
                attachments=attachments,
                notify_block=notify_block,
                notify_auth=notify_auth,
                channel=channel,
                expected_binding_id=expected_binding_id,
            ),
        )

    submission = _run_local_mail_prompt(
        controller=_require_live_local_controller(target, operation="submit TUI mail"),
        operation="reply",
        args={
            "message_ref": message_ref,
            "body_content": body_content,
            "attachments": [attachment.model_dump(mode="json") for attachment in attachments],
        },
        channel=channel,
        expected_binding_id=expected_binding_id,
    )
    receipt = submitted_mail_receipt(submission, channel=channel, binding_id=expected_binding_id)
    receipt["parent_message_ref"] = message_ref
    return receipt


def mail_mark(
    target: ManagedAgentTarget,
    *,
    channel: MailboxChannel,
    expected_binding_id: str | None = None,
    message_refs: list[str],
    read: bool | None,
    answered: bool | None,
    archived: bool | None,
) -> object:
    """Mark selected mailbox messages for a managed agent."""

    expected_binding_id = _resolve_mail_expected_binding(target, channel, expected_binding_id)

    if _target_uses_pair_api(target):
        assert target.client is not None
        from houmao.server.models import HoumaoManagedAgentMailMarkRequest

        return build_verified_mail_command_result(
            operation="mark",
            execution_path="gateway_backed",
            payload=pair_request(
                target.client.mark_managed_agent_mail,
                target.agent_ref,
                HoumaoManagedAgentMailMarkRequest(
                    message_refs=message_refs,
                    read=read,
                    answered=answered,
                    archived=archived,
                    expected_binding_id=expected_binding_id,
                ),
                channel=channel,
            ),
        )

    authority = _running_agent_authority(target, operation="mark managed-agent mail")
    gateway_client = _live_gateway_client_for_controller(
        authority, private=True, require_available=True
    )
    if gateway_client is not None:
        return build_verified_mail_command_result(
            operation="mark",
            execution_path="gateway_backed",
            payload=_gateway_mail_mark(
                gateway_client,
                message_refs=message_refs,
                read=read,
                answered=answered,
                archived=archived,
                channel=channel,
                expected_binding_id=expected_binding_id,
            ),
        )

    if target.identity.transport != "tui":
        return build_verified_mail_command_result(
            operation="mark",
            execution_path="manager_direct",
            payload=_local_manager_mail_mark(
                authority,
                message_refs=message_refs,
                read=read,
                answered=answered,
                archived=archived,
                channel=channel,
                expected_binding_id=expected_binding_id,
            ),
        )

    direct_mail_error = _local_manager_mail_authority_error(
        authority,
        channel=channel,
        expected_binding_id=expected_binding_id,
    )
    if direct_mail_error is None:
        return build_verified_mail_command_result(
            operation="mark",
            execution_path="manager_direct",
            payload=_local_manager_mail_mark(
                authority,
                message_refs=message_refs,
                read=read,
                answered=answered,
                archived=archived,
                channel=channel,
                expected_binding_id=expected_binding_id,
            ),
        )

    return _run_local_mail_prompt(
        controller=_require_live_local_controller(target, operation="submit TUI mail"),
        operation="mark",
        args={
            "message_refs": message_refs,
            "read": read,
            "answered": answered,
            "archived": archived,
        },
        channel=channel,
        expected_binding_id=expected_binding_id,
    )


def mail_move(
    target: ManagedAgentTarget,
    *,
    channel: MailboxChannel,
    expected_binding_id: str | None = None,
    message_refs: list[str],
    destination_box: str,
) -> object:
    """Move selected mailbox messages for a managed agent."""

    expected_binding_id = _resolve_mail_expected_binding(target, channel, expected_binding_id)

    if _target_uses_pair_api(target):
        assert target.client is not None
        from houmao.server.models import HoumaoManagedAgentMailMoveRequest

        return build_verified_mail_command_result(
            operation="move",
            execution_path="gateway_backed",
            payload=pair_request(
                target.client.move_managed_agent_mail,
                target.agent_ref,
                HoumaoManagedAgentMailMoveRequest(
                    message_refs=message_refs,
                    destination_box=destination_box,
                    expected_binding_id=expected_binding_id,
                ),
                channel=channel,
            ),
        )

    authority = _running_agent_authority(target, operation="move managed-agent mail")
    client = _live_gateway_client_for_controller(authority, private=True, require_available=True)
    if client is not None:
        try:
            result = _gateway_mail_move(
                client,
                message_refs=message_refs,
                destination_box=destination_box,
                channel=channel,
                expected_binding_id=expected_binding_id,
            )
        except GatewayHttpError as exc:
            raise click.ClickException(exc.detail) from None
        return build_verified_mail_command_result(
            operation="move", execution_path="gateway_backed", payload=result
        )
    return build_verified_mail_command_result(
        operation="move",
        execution_path="manager_direct",
        payload=_local_manager_mail_move(
            authority,
            message_refs=message_refs,
            destination_box=destination_box,
            channel=channel,
            expected_binding_id=expected_binding_id,
        ),
    )


def mail_archive(
    target: ManagedAgentTarget,
    *,
    channel: MailboxChannel,
    expected_binding_id: str | None = None,
    message_refs: list[str],
) -> object:
    """Archive selected mailbox messages for a managed agent."""

    expected_binding_id = _resolve_mail_expected_binding(target, channel, expected_binding_id)

    if _target_uses_pair_api(target):
        assert target.client is not None
        from houmao.server.models import HoumaoManagedAgentMailArchiveRequest

        return build_verified_mail_command_result(
            operation="archive",
            execution_path="gateway_backed",
            payload=pair_request(
                target.client.archive_managed_agent_mail,
                target.agent_ref,
                HoumaoManagedAgentMailArchiveRequest(
                    message_refs=message_refs,
                    expected_binding_id=expected_binding_id,
                ),
                channel=channel,
            ),
        )

    authority = _running_agent_authority(target, operation="archive managed-agent mail")
    client = _live_gateway_client_for_controller(authority, private=True, require_available=True)
    if client is not None:
        try:
            result = _gateway_mail_archive(
                client,
                message_refs=message_refs,
                channel=channel,
                expected_binding_id=expected_binding_id,
            )
        except GatewayHttpError as exc:
            raise click.ClickException(exc.detail) from None
        return build_verified_mail_command_result(
            operation="archive", execution_path="gateway_backed", payload=result
        )
    return build_verified_mail_command_result(
        operation="archive",
        execution_path="manager_direct",
        payload=_local_manager_mail_archive(
            authority,
            message_refs=message_refs,
            channel=channel,
            expected_binding_id=expected_binding_id,
        ),
    )


def mail_resolve_live(target: ManagedAgentTarget) -> dict[str, Any]:
    """Resolve one managed agent's live mailbox bindings and gateway metadata."""

    if _target_uses_pair_api(target):
        assert target.client is not None
        payload = pair_request(target.client.get_managed_agent_mail_resolve_live, target.agent_ref)
        return _normalized_live_mail_payload(
            target=target,
            payload=payload,
            source_override="pair_authority",
        )

    record = target.record
    if record is not None and (target.mode == "executor" or record.lifecycle.state != "active"):
        return _published_mail_payload(target, record)
    try:
        authority = _running_agent_authority(
            target, operation="resolve live managed-agent mail bindings"
        )
    except ManifestAuthorityUnavailable:
        if record is None:
            raise
        return _published_mail_payload(target, record)
    try:
        if isinstance(authority, (VerifiedRegistryManifest, VerifiedSelfManifest)):
            manifest = _read_running_agent_manifest(authority)
            mailboxes = mailboxes_resolved_config_from_payload(
                manifest.launch_plan.mailboxes, manifest_path=authority.manifest_path
            )
            resolution = LiveMailboxesBindingResolution(
                mailboxes=mailboxes, gateway=_mail_discovery_gateway(authority)
            )
        else:
            resolution = resolve_live_mailbox_binding_from_manifest_path(
                manifest_path=authority.manifest_path,
            )
    except (ValueError, OSError, SessionManifestError) as exc:
        raise click.ClickException(str(exc)) from exc
    return _normalized_live_mail_payload(target=target, payload=resolution.payload())


def _published_mail_payload(
    target: ManagedAgentTarget, record: ManagedAgentRegistryRecordV3
) -> dict[str, Any]:
    """Return public recipient contact without claiming current availability."""

    channels: dict[str, Any] = {}
    for channel in ("offline", "online"):
        slot = record.mailboxes.offline if channel == "offline" else record.mailboxes.online
        channels[channel] = {
            "revision": slot.revision,
            "binding": None
            if slot.binding is None
            else slot.binding.model_dump(exclude={"availability"}),
            "availability": "unverified",
        }
    return _normalized_live_mail_payload(
        target=target,
        payload={
            "source": "registry_projection",
            "mailboxes": channels,
            "canonical_mail_identity": record.canonical_mail_identity,
            "gateway": None,
        },
    )


def _mail_discovery_gateway(authority: _VerifiedManifest) -> LiveGatewayBindingResolution | None:
    """Show a live gateway only when its instance identifies this selected owner."""

    paths = gateway_paths_from_manifest_path(authority.manifest_path)
    if paths is None:
        return None
    try:
        instance, endpoint = _verified_current_gateway(authority, paths)
    except (GatewayHttpError, OSError, SessionManifestError):
        return None
    return LiveGatewayBindingResolution(
        host=instance.host,
        port=instance.port,
        base_url=owner_gateway_base_url(endpoint.port),
        state_path=paths.state_path,
        protocol_version=instance.protocol_version,
        source="current_instance_record",
    )


def _local_manager_mail_authority_error(
    authority: _RunningAgentAuthority,
    *,
    channel: MailboxChannel,
    expected_binding_id: str | None = None,
) -> click.ClickException | None:
    """Return one direct-mail authority error, or `None` when direct execution is ready."""

    try:
        _local_mailbox_adapter(
            authority,
            channel=channel,
            expected_binding_id=expected_binding_id,
        )
    except AttributeError:
        return click.ClickException(
            "Manager-owned local mail authority is unavailable for this runtime controller."
        )
    except click.ClickException as exc:
        return exc
    return None


def _normalized_live_mail_payload(
    *,
    target: ManagedAgentTarget,
    payload: dict[str, Any],
    source_override: str | None = None,
) -> dict[str, Any]:
    """Normalize one live mailbox resolution payload for CLI output."""

    normalized = dict(payload)
    if source_override is not None:
        normalized["source"] = source_override
    normalized["schema_version"] = 1
    normalized["managed_agent"] = _managed_agent_live_payload(target)
    normalized["gateway_available"] = isinstance(normalized.get("gateway"), dict)
    return normalized


def _managed_agent_live_payload(target: ManagedAgentTarget) -> dict[str, Any]:
    """Project stable managed-agent identity fields for `resolve-live` payloads."""

    return {
        "mode": target.mode,
        "agent_ref": target.agent_ref,
        "tracked_agent_id": target.identity.tracked_agent_id,
        "agent_name": target.identity.agent_name,
        "agent_id": target.identity.agent_id,
        "tmux_session_name": target.identity.tmux_session_name,
    }


def _gateway_command_helpers() -> Any:
    """Import the gateway command module lazily to reuse current-session helpers."""

    from .agents import gateway as gateway_commands

    return gateway_commands


def submit_headless_turn(
    target: ManagedAgentTarget,
    *,
    prompt: str,
    model: str | None = None,
    reasoning_level: int | None = None,
) -> HoumaoHeadlessTurnAcceptedResponse:
    """Submit one headless turn for a managed agent."""

    _raise_external_unsupported(target, operation="agents single ... turn submit")
    if target.identity.transport != "headless":
        raise click.ClickException("This command requires headless mode.")

    execution_model = _resolve_execution_model_override(
        model=model,
        reasoning_level=reasoning_level,
    )
    _require_headless_execution_override_target(
        target=target,
        execution_model=execution_model,
    )
    if target.mode == "server":
        assert target.client is not None
        return pair_request(
            target.client.submit_headless_turn,
            target.agent_ref,
            HoumaoHeadlessTurnRequest(
                prompt=prompt,
                execution=_execution_override_payload(execution_model),
            ),
        )

    controller = _require_live_local_controller(
        target, operation="submit headless turn", existing_only=True
    )
    outcome = _dispatch_owned_manager_prompt(
        controller,
        tracked_agent_id=target.identity.tracked_agent_id,
        prompt=prompt,
        execution_model=execution_model,
    )
    snapshot = _turn_snapshot_from_id(controller=controller, turn_id=outcome.request_id)
    return HoumaoHeadlessTurnAcceptedResponse(
        success=outcome.success,
        tracked_agent_id=target.identity.tracked_agent_id,
        turn_id=outcome.request_id,
        turn_index=snapshot.turn_index,
        status=_managed_agent_turn_status(snapshot.status),
        detail=outcome.detail,
    )


def headless_turn_status(
    target: ManagedAgentTarget,
    *,
    turn_id: str,
) -> HoumaoHeadlessTurnStatusResponse:
    """Return headless turn status for one managed agent."""

    _raise_external_unsupported(target, operation="agents single ... turn status")

    if target.mode == "server":
        assert target.client is not None
        return pair_request(target.client.get_headless_turn_status, target.agent_ref, turn_id)

    authority = _running_agent_authority(target, operation="show headless turn status")
    snapshot = _turn_snapshot_from_id(controller=authority, turn_id=turn_id)
    return HoumaoHeadlessTurnStatusResponse(
        tracked_agent_id=target.identity.tracked_agent_id,
        turn_id=snapshot.turn_id,
        turn_index=snapshot.turn_index,
        status=_managed_agent_turn_status(snapshot.status),
        started_at_utc=snapshot.started_at_utc,
        completed_at_utc=snapshot.completed_at_utc,
        returncode=snapshot.returncode,
        completion_source=snapshot.completion_source,
        stdout_path=str(snapshot.stdout_path) if snapshot.stdout_path is not None else None,
        stderr_path=str(snapshot.stderr_path) if snapshot.stderr_path is not None else None,
        status_path=str(snapshot.status_path) if snapshot.status_path is not None else None,
        history_summary=snapshot.history_summary,
        error=snapshot.error,
    )


def headless_turn_events(
    target: ManagedAgentTarget,
    *,
    turn_id: str,
) -> HoumaoHeadlessTurnEventsResponse:
    """Return structured events for one headless turn."""

    _raise_external_unsupported(target, operation="agents single ... turn events")

    if target.mode == "server":
        assert target.client is not None
        return pair_request(target.client.get_headless_turn_events, target.agent_ref, turn_id)

    authority = _running_agent_authority(target, operation="show headless turn events")
    snapshot = _turn_snapshot_from_id(controller=authority, turn_id=turn_id)
    events = _load_turn_events(
        snapshot,
        provider=_headless_provider_for_authority(authority),
    )
    return HoumaoHeadlessTurnEventsResponse(
        tracked_agent_id=target.identity.tracked_agent_id,
        turn_id=turn_id,
        entries=events,
    )


def headless_turn_artifact_text(
    target: ManagedAgentTarget,
    *,
    turn_id: str,
    artifact_name: str,
) -> str:
    """Return one raw headless artifact text payload."""

    _raise_external_unsupported(target, operation="agents single ... turn artifact")

    if target.mode == "server":
        assert target.client is not None
        return pair_request(
            target.client.get_headless_turn_artifact_text,
            target.agent_ref,
            turn_id,
            artifact_name=artifact_name,
        )

    authority = _running_agent_authority(target, operation="read headless turn artifact")
    snapshot = _turn_snapshot_from_id(controller=authority, turn_id=turn_id)
    if artifact_name == "stdout":
        artifact_path = snapshot.stdout_path
    elif artifact_name == "stderr":
        artifact_path = snapshot.stderr_path
    else:
        raise click.ClickException(f"Unknown headless artifact `{artifact_name}`.")
    if artifact_path is None or not artifact_path.exists():
        return ""
    return artifact_path.read_text(encoding="utf-8")


def _list_registry_identities(
    *,
    lifecycle_state: ManagedAgentListState = "active",
) -> list[HoumaoManagedAgentIdentity]:
    """Return current fresh registry identities."""

    return [
        _identity_from_record(record)
        for record in _list_registry_records(lifecycle_state=lifecycle_state)
    ]


def _list_registry_records(
    *,
    lifecycle_state: ManagedAgentListState = "active",
) -> list[ManagedAgentRegistryRecordV3]:
    """Return lifecycle-filtered shared-registry records."""

    paths = global_registry_paths()
    if not paths.live_agents_dir.exists():
        return []
    records: list[ManagedAgentRegistryRecordV3] = []
    for candidate in sorted(paths.live_agents_dir.iterdir()):
        if not candidate.is_dir():
            continue
        if lifecycle_state == "active":
            record = resolve_live_agent_record_by_agent_id(candidate.name)
            if record is not None and _retired_registry_origin(record) is None:
                records.append(record)
            continue
        record = load_managed_agent_record_by_agent_id(candidate.name)
        if record is None:
            continue
        if record.lifecycle.state == "active" and not is_live_agent_record_fresh(record):
            continue
        if lifecycle_state != "all" and record.lifecycle.state != lifecycle_state:
            continue
        if _retired_registry_origin(record) is not None:
            continue
        records.append(record)
    return records


def _retired_registry_origin(
    record: ManagedAgentRegistryRecordV3,
) -> RetiredJoinedSessionError | None:
    """Check the manifest for a retired origin without interpreting a missing manifest."""

    path = _non_empty_record_manifest_path(record)
    if path is not None:
        try:
            load_session_manifest(Path(path))
        except RetiredJoinedSessionError as exc:
            return exc
        except SessionManifestError:
            pass
    return None


def _require_supported_registry_origin(record: ManagedAgentRegistryRecordV3) -> None:
    """Refuse a selected retired record before probing or using another authority."""

    retirement = _retired_registry_origin(record)
    if retirement is not None:
        raise click.ClickException(str(retirement)) from retirement


def _identity_merge_key(identity: HoumaoManagedAgentIdentity) -> str:
    """Return one stable merge key for mixed registry/server identity aggregation."""

    for value in (
        identity.agent_id,
        identity.manifest_path,
        identity.session_name,
        identity.tracked_agent_id,
    ):
        if value is not None and value.strip():
            return value
    return identity.tracked_agent_id


def _identity_from_record(
    record: ManagedAgentRegistryRecordV3, *, manifest: SessionManifestPayloadV4 | None = None
) -> HoumaoManagedAgentIdentity:
    """Project one registry record into the shared identity payload."""

    transport = record.mode
    tracked_agent_id = record.agent_id or record.agent_name or record.terminal.session_name
    tmux_window_name = (
        HEADLESS_AGENT_WINDOW_NAME
        if transport == "headless" or record.identity.backend == "local_interactive"
        else None
    )
    if manifest is not None and manifest.tmux is not None:
        tmux_window_name = manifest.tmux.primary_window_name or tmux_window_name
    return HoumaoManagedAgentIdentity(
        tracked_agent_id=tracked_agent_id,
        transport=transport,
        mode=record.mode,
        backend=record.identity.backend,
        native_surface=record.native_surface,
        tool=record.identity.tool,
        session_name=record.terminal.session_name if transport == "tui" else None,
        terminal_id=None,
        runtime_session_id=manifest.runtime.session_id
        if manifest is not None
        else tracked_agent_id,
        tmux_session_name=record.terminal.session_name,
        tmux_window_name=tmux_window_name,
        manifest_path=record.runtime.manifest_path,
        session_root=record.runtime.session_root,
        agent_name=record.agent_name,
        agent_id=record.agent_id,
        lifecycle_state=_record_lifecycle_state(record),
        management_kind="local_lifecycle",
        lifecycle_owner="local",
        execution_context=record.execution_binding,
        execution_status="available" if record.execution_binding is not None else None,
    )


def select_local_managed_agent_record(
    record: ManagedAgentRegistryRecordV3, *, agent_ref: str
) -> ManagedAgentTarget:
    """Select an already-disambiguated local record without opening its runtime."""

    _require_supported_registry_origin(record)
    if record.identity.backend == "houmao_server_rest":
        raise click.ClickException(
            "This managed agent is registered with retired backend "
            "`houmao_server_rest`. Use `houmao-passive-server` for maintained API-backed "
            "management or relaunch the agent through a maintained local/headless workflow."
        )
    return ManagedAgentTarget(
        mode="local", agent_ref=agent_ref, identity=_identity_from_record(record), record=record
    )


def _resume_controller_from_record(
    record: ManagedAgentRegistryRecordV3,
    *,
    existing_only: bool = False,
) -> RuntimeSessionController:
    """Resume one local runtime controller from a registry record."""

    manifest_path = Path(record.runtime.manifest_path).expanduser().resolve()
    try:
        require_registry_mode_authority(record)
        return resume_runtime_session(
            session_manifest_path=manifest_path, existing_only=existing_only
        )
    except (BrainLaunchRuntimeError, TmuxObservationError) as exc:
        cause: BaseException | None = exc
        while cause is not None:
            if isinstance(cause, TmuxObservationError):
                raise click.ClickException(
                    str(terminal_inspection_unavailable(record, cause))
                ) from exc
            cause = cause.__cause__
        tracked_name = record.agent_name or record.agent_id or record.terminal.session_name
        raise click.ClickException(
            f"Managed agent `{tracked_name}` is registered in the shared registry but "
            f"its local tmux-backed runtime authority is no longer live or otherwise "
            f"unusable: {exc}"
        ) from exc


def _probe_local_tmux_authority_for_record(
    record: ManagedAgentRegistryRecordV3,
) -> TmuxBackedAuthorityHealth:
    """Classify one active agent's terminal on its selected owner socket."""

    return _probe_recorded_terminal(record, _read_recovery_manifest(record))


def _read_recovery_manifest(
    record: ManagedAgentRegistryRecordV3,
) -> SessionManifestPayloadV4 | None:
    """Load a usable manifest, retaining registry authority for missing runtimes."""

    try:
        validate_execution_owner(record.execution_binding)
    except (ValueError, OSError) as exc:
        raise terminal_inspection_unavailable(
            record, "The recorded owner route is unavailable"
        ) from exc
    manifest_path = Path(record.runtime.manifest_path)
    try:
        handle = load_session_manifest(manifest_path)
        return parse_session_manifest_payload(handle.payload, source=str(handle.path))
    except RetiredJoinedSessionError:
        raise
    except SessionManifestError:
        return None


def _probe_recorded_terminal(
    record: ManagedAgentRegistryRecordV3, manifest: SessionManifestPayloadV4 | None
) -> TmuxBackedAuthorityHealth:
    """Use saved primary handles when available and surface checked query failures."""

    from houmao.execution.tmux import tmux_server_scope

    binding = recorded_tmux_binding(record, manifest)
    assert binding.socket_path is not None
    try:
        with tmux_server_scope(binding.socket_path):
            if manifest is None:
                return probe_tmux_backed_authority(session_name=binding.session_name)
            return probe_tmux_backed_authority(
                session_name=binding.session_name,
                primary_window_id=binding.primary_window_id,
                primary_pane_id=binding.primary_pane_id,
                primary_window_name=binding.primary_window_name,
            )
    except TmuxCommandError as exc:
        raise terminal_inspection_unavailable(record, exc) from exc


def _record_has_readable_manifest_authority(
    record: ManagedAgentRegistryRecordV3,
) -> bool:
    """Return whether one registry record still exposes readable manifest authority."""

    agent_def_dir_raw = record.runtime.agent_def_dir
    if agent_def_dir_raw is None or not agent_def_dir_raw.strip():
        return False
    manifest_path_raw = record.runtime.manifest_path
    if not manifest_path_raw or not manifest_path_raw.strip():
        return False
    manifest_path = Path(manifest_path_raw).expanduser().resolve()
    if not manifest_path.is_file():
        return False
    agent_def_dir = Path(agent_def_dir_raw).expanduser().resolve()
    if not agent_def_dir.is_dir():
        return False
    return True


def _is_local_tmux_backed_active_record(record: ManagedAgentRegistryRecordV3) -> bool:
    """Return whether one record represents an active local tmux-backed managed agent."""

    if record.lifecycle.state != "active":
        return False
    if record.identity.backend == "houmao_server_rest":
        return False
    return True


def _resume_stopped_controller_from_record(
    record: ManagedAgentRegistryRecordV3,
) -> RuntimeSessionController:
    """Prepare one stopped local runtime controller for stopped-session revival."""

    agent_def_dir_raw = record.runtime.agent_def_dir
    if agent_def_dir_raw is None:
        raise click.ClickException(
            f"Managed agent `{record.agent_name}` cannot be relaunched because "
            "`runtime.agent_def_dir` is missing from the stopped registry record."
        )
    manifest_path = Path(record.runtime.manifest_path).resolve()
    if not manifest_path.is_file():
        raise click.ClickException(
            f"Managed agent `{record.agent_name}` cannot be relaunched because its manifest "
            f"`{manifest_path}` is unavailable."
        )
    agent_def_dir = Path(agent_def_dir_raw).resolve()
    if not agent_def_dir.is_dir():
        raise click.ClickException(
            f"Managed agent `{record.agent_name}` cannot be relaunched because its persisted "
            f"agent-definition directory `{agent_def_dir}` is unavailable."
        )
    try:
        require_registry_mode_authority(record)
        return resume_stopped_runtime_session(
            agent_def_dir=agent_def_dir,
            session_manifest_path=manifest_path,
        )
    except BrainLaunchRuntimeError as exc:
        tracked_name = record.agent_name or record.agent_id or record.terminal.session_name
        raise click.ClickException(
            f"Managed agent `{tracked_name}` is registered as a stopped relaunchable runtime, "
            f"but its preserved local authority could not be reconstructed: {exc}"
        ) from exc


def _identity_from_controller(controller: RuntimeSessionController) -> HoumaoManagedAgentIdentity:
    """Project one resumed controller into the shared identity model."""

    tracked_agent_id = (
        controller.agent_id or controller.agent_identity or controller.manifest_path.parent.name
    )
    transport = controller.launch_plan.mode
    manifest = _managed_manifest_for_identity(controller.manifest_path)
    tmux_window_name = _managed_tmux_window_name_from_manifest_path(
        manifest_path=controller.manifest_path,
        default=(
            HEADLESS_AGENT_WINDOW_NAME
            if transport == "headless" or controller.launch_plan.backend == "local_interactive"
            else None
        ),
    )
    return HoumaoManagedAgentIdentity(
        tracked_agent_id=tracked_agent_id,
        transport=transport,
        mode=controller.launch_plan.mode,
        backend=controller.launch_plan.backend,
        native_surface=manifest.native_surface if manifest is not None else None,
        tool=controller.launch_plan.tool,
        session_name=controller.tmux_session_name if transport == "tui" else None,
        terminal_id=None,
        runtime_session_id=manifest.runtime.session_id
        if transport == "web" and manifest is not None
        else controller.manifest_path.parent.name,
        tmux_session_name=controller.tmux_session_name,
        tmux_window_name=tmux_window_name,
        manifest_path=str(controller.manifest_path),
        session_root=str(controller.manifest_path.parent),
        agent_name=controller.agent_identity,
        agent_id=controller.agent_id,
        management_kind="local_lifecycle",
        lifecycle_owner="local",
        execution_context=manifest.runtime.execution_binding if manifest is not None else None,
        execution_status="available"
        if manifest is not None and manifest.runtime.execution_binding is not None
        else None,
    )


def _optional_pair_client(*, base_url: str) -> PairAuthorityClientProtocol | None:
    """Return one reachable pair client or `None` when unavailable."""

    try:
        return require_supported_houmao_pair(base_url=base_url)
    except click.ClickException:
        return None


def _resolve_server_identity_from_record(
    *,
    client: PairAuthorityClientProtocol,
    record: ManagedAgentRegistryRecordV3,
) -> HoumaoManagedAgentIdentity:
    """Resolve the server-side identity described by one registry record."""

    candidates = (
        record.agent_id,
        record.agent_name,
        record.terminal.session_name,
    )
    for candidate in candidates:
        if candidate is None:
            continue
        try:
            return resolve_managed_agent_identity(client, agent_ref=candidate)
        except click.ClickException:
            continue
        except CaoApiError:
            continue
    raise click.ClickException(
        f"Managed agent `{record.agent_name}` is registered in the shared registry but "
        "could not be resolved from the owning pair authority."
    )


def _local_gateway_target_for_passive_pair(
    target: ManagedAgentTarget,
    *,
    operation: str,
) -> ManagedAgentTarget:
    """Convert passive-server gateway attach and detach onto the local authority path."""

    if target.mode != "server":
        return target
    assert target.client is not None
    if target.client.pair_authority_kind != "houmao-passive-server":
        return target
    record = _resolve_local_gateway_record_for_passive_pair(target)
    if record is None or record.identity.backend == "houmao_server_rest":
        raise click.ClickException(
            f"Passive-server gateway {operation} requires local authority on the owning host; "
            "remote pair HTTP control is unsupported."
        )
    controller = _resume_controller_from_record(record)
    return ManagedAgentTarget(
        mode="local",
        agent_ref=target.agent_ref,
        identity=_identity_from_controller(controller),
        controller=controller,
        record=record,
    )


def _resolve_local_gateway_record_for_passive_pair(
    target: ManagedAgentTarget,
) -> ManagedAgentRegistryRecordV3 | None:
    """Resolve one local registry record for passive-server gateway attach and detach."""

    if target.identity.agent_id is not None:
        return resolve_live_agent_record_by_agent_id(target.identity.agent_id)
    return _resolve_local_managed_agent_record(
        agent_id=None,
        agent_name=target.identity.agent_name or target.agent_ref,
    )


def _gateway_status_for_controller(authority: _RunningAgentAuthority) -> GatewayStatusV1:
    """Return gateway status from the authorized runtime's manifest path."""

    if isinstance(authority, VerifiedSelfManifest):
        _read_running_agent_manifest(authority)
    paths = gateway_paths_from_manifest_path(authority.manifest_path)
    if paths is None:
        raise click.ClickException(
            "Managed agent does not publish manifest-backed gateway capability."
        )
    if paths.state_path.is_file():
        try:
            return load_gateway_status(paths.state_path)
        except SessionManifestError as exc:
            raise click.ClickException(str(exc)) from exc
    try:
        attach_contract = resolve_internal_gateway_attach_contract(paths)
    except SessionManifestError as exc:
        raise click.ClickException(str(exc)) from exc
    return build_offline_gateway_status(
        attach_contract=attach_contract,
        managed_agent_instance_epoch=0,
    )


def _live_gateway_client_for_controller(
    authority: _RunningAgentAuthority,
    *,
    private: bool = False,
    require_available: bool = False,
) -> GatewayClient | None:
    """Return a client preserving the running agent's owner and signer binding."""

    status = _gateway_status_for_controller(authority)
    if status.gateway_health != "healthy":
        return None
    presence_id = None
    if isinstance(authority, (VerifiedRegistryManifest, VerifiedSelfManifest)):
        paths = gateway_paths_from_manifest_path(authority.manifest_path)
        try:
            assert paths is not None
            instance, endpoint = _verified_current_gateway(authority, paths)
            if not _gateway_status_matches_instance(status, instance):
                raise SessionManifestError("Gateway status belongs to a superseded instance.")
            if instance.endpoint_descriptor is not None:
                presence_id = instance.endpoint_descriptor.presence_id
        except (GatewayHttpError, OSError, SessionManifestError) as exc:
            if require_available:
                raise _gateway_inspection_unavailable(authority, exc) from None
            return None
    else:
        if status.gateway_host is None or status.gateway_port is None:
            return None
        endpoint = GatewayEndpoint(host=status.gateway_host, port=status.gateway_port)
        try:
            GatewayClient(endpoint=endpoint).health()
        except GatewayHttpError as exc:
            if require_available:
                raise click.ClickException(exc.detail) from None
            return None
    scope = get_managed_agent_scope_context()
    try:
        binding, incarnation = owner_gateway_client_binding(
            authority.manifest_path,
            port=endpoint.port,
            private=private,
            prefer_self=isinstance(authority, VerifiedSelfManifest)
            or (scope is not None and scope.scope == "self"),
        )
    except (GatewayAccessError, SessionManifestError, ValueError):
        raise click.ClickException("Gateway caller binding is unavailable.") from None
    if (
        isinstance(authority, (VerifiedRegistryManifest, VerifiedSelfManifest))
        and incarnation != authority.record.generation_id
    ):
        raise click.ClickException("The gateway belongs to a different runtime generation.")
    return GatewayClient(
        endpoint=endpoint,
        binding=binding,
        target_incarnation=incarnation,
        target_presence_id=presence_id,
    )


def _verified_current_gateway(
    authority: _VerifiedManifest, paths: GatewayPaths
) -> tuple[GatewayCurrentInstanceV1, GatewayEndpoint]:
    """Match the persisted instance and the responding endpoint to this owner."""

    instance = load_gateway_current_instance(paths.current_instance_path)
    saved = instance.endpoint_descriptor
    binding = authority.payload.runtime.execution_binding
    if (
        saved is None
        or binding is None
        or saved.target.owner.agent_id != authority.agent_id
        or saved.target.owner.context_id != binding.context_id
        or saved.target.incarnation != authority.record.generation_id
    ):
        raise SessionManifestError("Current gateway instance differs from the selected owner.")
    endpoint = GatewayEndpoint(host=instance.host, port=instance.port)
    descriptor = GatewayClient(endpoint=endpoint, timeout_seconds=2.0).describe_endpoint()
    if (
        descriptor.target != saved.target
        or descriptor.presence_id != saved.presence_id
        or descriptor.protocol != saved.protocol
        or descriptor.proof_protocol != saved.proof_protocol
    ):
        raise SessionManifestError("Gateway listener belongs to a different instance.")
    if load_gateway_current_instance(paths.current_instance_path).endpoint_descriptor != saved:
        raise SessionManifestError("Current gateway instance changed during observation.")
    return instance, endpoint


def _gateway_status_matches_instance(
    status: GatewayStatusV1, instance: GatewayCurrentInstanceV1
) -> bool:
    """Compare status evidence with the verified gateway's instance coordinates."""

    return (
        status.gateway_health == "healthy"
        and status.gateway_host == instance.host
        and status.gateway_port == instance.port
        and status.protocol_version == instance.protocol_version
        and status.managed_agent_instance_epoch == instance.managed_agent_instance_epoch
        and status.managed_agent_instance_id == instance.managed_agent_instance_id
    )


def _gateway_inspection_unavailable(
    authority: _VerifiedManifest, cause: Exception
) -> click.ClickException:
    """Report a failed gateway observation without claiming detachment."""

    reason = str(cause) if isinstance(cause, SessionManifestError) else "Endpoint is unavailable."
    return click.ClickException(f"Gateway status unavailable for `{authority.agent_id}`. {reason}")


def _require_live_gateway_client_for_controller(
    authority: _RunningAgentAuthority,
) -> GatewayClient:
    """Return a verified live gateway client or fail with attach guidance."""

    client = _live_gateway_client_for_controller(authority)
    if client is None:
        raise click.ClickException(
            "No live gateway is attached to the managed agent. "
            "Run `houmao-mgr agents single --agent-id <id> gateway attach` or "
            "`houmao-mgr agents self gateway attach` and retry."
        )
    return client


def _local_tui_runtime_for_controller(
    controller: RuntimeSessionController,
    *,
    manifest: SessionManifestPayloadV4 | None = None,
) -> SingleSessionTrackingRuntime:
    """Return one ephemeral single-session tracker for a local TUI controller."""

    if manifest is None:
        manifest = _managed_manifest_for_identity(controller.manifest_path)
    binding = manifest.tmux if manifest is not None else None
    return SingleSessionTrackingRuntime(
        identity=_tracked_tui_identity_for_controller(controller),
        supported_tui_processes=_SUPPORTED_LOCAL_TUI_PROCESSES,
        primary_binding=binding,
    )


def _tracked_tui_identity_for_controller(
    controller: RuntimeSessionController,
) -> HoumaoTrackedSessionIdentity:
    """Build one tracked-session identity for local TUI discovery."""

    tracked_agent_id = (
        controller.agent_id or controller.agent_identity or controller.manifest_path.parent.name
    )
    tmux_session_name = (
        controller.tmux_session_name
        or controller.agent_identity
        or controller.manifest_path.parent.name
    )
    launch_policy = controller.launch_plan.launch_policy_provenance
    return HoumaoTrackedSessionIdentity(
        tracked_session_id=tracked_agent_id,
        session_name=tmux_session_name,
        tool=controller.launch_plan.tool,
        observed_tool_version=launch_policy.detected_tool_version if launch_policy else None,
        tmux_session_name=tmux_session_name,
        tmux_window_name=_managed_tmux_window_name_from_manifest_path(
            manifest_path=controller.manifest_path,
            default=HEADLESS_AGENT_WINDOW_NAME,
        ),
        agent_name=controller.agent_identity,
        agent_id=controller.agent_id,
        manifest_path=str(controller.manifest_path),
        session_root=str(controller.manifest_path.parent),
    )


def _managed_manifest_for_identity(manifest_path: Path) -> SessionManifestPayloadV4 | None:
    """Read current persisted identity without activating or retargeting an agent."""

    try:
        handle = load_session_manifest(manifest_path)
        return parse_session_manifest_payload(handle.payload, source=str(handle.path))
    except SessionManifestError:
        return None


def _managed_tmux_window_name_from_manifest_path(
    *,
    manifest_path: Path,
    default: str | None,
) -> str | None:
    """Return the best persisted tmux window name for one managed session."""

    try:
        handle = load_session_manifest(manifest_path)
        payload = parse_session_manifest_payload(handle.payload, source=str(handle.path))
    except SessionManifestError:
        return default

    if isinstance(payload, SessionManifestPayloadV4):
        if payload.tmux is not None and payload.tmux.primary_window_name is not None:
            return payload.tmux.primary_window_name
        if payload.interactive is not None and payload.interactive.tmux_window_name is not None:
            return payload.interactive.tmux_window_name
    backend_window_name = payload.backend_state.get("tmux_window_name")
    if isinstance(backend_window_name, str) and backend_window_name.strip():
        return backend_window_name.strip()
    return default


def _turn_snapshot_from_id(
    *,
    controller: _RunningAgentAuthority,
    turn_id: str,
) -> HeadlessTurnSnapshot:
    """Return one local turn snapshot or fail clearly."""

    if Path(turn_id).name != turn_id or turn_id in {"", ".", ".."}:
        raise click.ClickException(f"Headless turn `{turn_id}` was not found.")
    provider = _headless_provider_for_authority(controller)
    try:
        root = headless_turn_artifacts_root(controller.manifest_path)
        candidate = root / turn_id
        if candidate.is_symlink() or not candidate.is_dir():
            raise click.ClickException(f"Headless turn `{turn_id}` was not found.")
        return read_headless_turn(candidate, dsh_cli=provider == "dsh", provider=provider)
    except (OSError, BackendExecutionError) as exc:
        raise click.ClickException(str(exc)) from exc


def _headless_provider_for_authority(authority: _RunningAgentAuthority) -> HeadlessProvider:
    """Read the saved provider identity for one running agent's artifacts."""

    if isinstance(authority, (VerifiedRegistryManifest, VerifiedSelfManifest)):
        payload = _read_running_agent_manifest(authority)
        if payload.mode != "headless":
            raise click.ClickException("Saved turn reads require a headless managed agent.")
        return resolve_headless_provider(tool=payload.tool, backend=payload.backend)
    return resolve_headless_provider(
        tool=authority.launch_plan.tool, backend=authority.launch_plan.backend
    )


def _load_turn_events(
    snapshot: HeadlessTurnSnapshot,
    *,
    provider: HeadlessProvider,
) -> list[HoumaoHeadlessTurnEvent]:
    """Load structured events for one persisted local headless turn."""

    if snapshot.stdout_path is None or not snapshot.stdout_path.exists():
        return []
    entries: list[HoumaoHeadlessTurnEvent] = []
    for event in load_headless_turn_events(
        turn_dir=snapshot.stdout_path.parent,
        provider=provider,
        output_format="stream-json",
        turn_index=snapshot.turn_index,
    ):
        entries.append(
            HoumaoHeadlessTurnEvent(
                kind=event.kind,
                message=event.message,
                turn_index=event.turn_index,
                timestamp_utc=snapshot.completed_at_utc or snapshot.started_at_utc,
                payload=event.payload,
            )
        )
    return entries


def _run_local_mail_prompt(
    *,
    channel: MailboxChannel,
    expected_binding_id: str,
    controller: RuntimeSessionController,
    operation: str,
    args: dict[str, Any],
) -> dict[str, Any]:
    """Run one submission-only mailbox fallback through the current owner slot."""

    try:
        mailbox = ensure_mailbox_command_ready(
            controller.launch_plan,
            channel=channel,
            expected_binding_id=expected_binding_id,
            tmux_session_name=controller.tmux_session_name,
        )
    except MailboxCommandError as exc:
        raise click.ClickException(str(exc)) from exc
    prefer_live_gateway = _live_gateway_client_for_controller(controller) is not None
    prompt_args = _enrich_local_mail_prompt_args(
        mailbox=mailbox,
        operation=operation,
        args={**args, "channel": channel, "expected_binding_id": expected_binding_id},
    )
    prompt_request = prepare_mail_prompt(
        launch_plan=controller.launch_plan,
        channel=channel,
        expected_binding_id=expected_binding_id,
        operation=cast(Any, operation),
        args=prompt_args,
        prefer_live_gateway=prefer_live_gateway,
        tmux_session_name=controller.tmux_session_name,
    )

    def send_owned(request: MailPromptRequest) -> list[SessionEvent]:
        """Retain the mailbox-specific event projection after a guarded native send."""

        backend = controller.backend_session
        generation = controller.registry_generation_id
        try:
            capabilities = controller.control_capabilities()
            capabilities.require("prompt")
            if (
                generation is None
                or capabilities.mode != "tui"
                or not isinstance(backend, (LocalInteractiveSession, CaoRestSession))
            ):
                raise BackendExecutionError("The selected owner does not support TUI mail prompts.")
            readiness = _manager_prompt_readiness(controller, mode="tui")
            if readiness is None:
                raise BackendExecutionError("Verified terminal readiness is unavailable.")
            with controller.execution_scope():
                identity = (
                    backend.plugin_execution_identity()
                    if isinstance(backend, LocalInteractiveSession)
                    else None
                )
            claim = reserve_owner_prompt(
                controller.manifest_path,
                generation,
                request_id=request.request_id,
                origin="manager_mail",
                readiness=readiness,
            )
        except OwnerAdmissionError as exc:
            if exc.code in {"not_ready", "uncertain"}:
                raise BackendExecutionError(f"Managed terminal is busy. {exc}") from exc
            raise
        except (OSError, SessionManifestError, TmuxCommandError) as exc:
            raise BackendExecutionError(str(exc)) from exc

        dispatch: HeadlessDispatchControl | None = None
        attempted = False
        try:
            if isinstance(backend, LocalInteractiveSession):

                def allowed() -> bool:
                    """Recheck the exact TUI and its readiness before literal paste."""

                    if not claim.active():
                        return False
                    try:
                        with controller.execution_scope():
                            if dispatch is not None and not dispatch.m_input_started.is_set():
                                readiness()
                            return backend.plugin_execution_identity() == identity
                    except (BrainLaunchRuntimeError, OSError, TmuxCommandError):
                        return False

                dispatch = HeadlessDispatchControl.from_callbacks(
                    allowed=allowed,
                    confirmed=claim.handoff,
                    deadline=monotonic() + 10,
                    manifest_path=claim.manifest_path,
                    generation_id=claim.generation_id,
                )
                backend.configure_request_dispatch(dispatch)
            elif not claim.active():
                raise BackendExecutionError("The managed terminal owner changed before submission.")

            attempted = True
            events = controller.send_mail_prompt(request)
            if dispatch is not None:
                if not dispatch.m_handoff_confirmed.is_set():
                    raise BackendExecutionError("Native terminal handoff could not be verified.")
            elif any(event.kind == "submitted" for event in events) and claim.active():
                claim.handoff()
                if any(
                    event.kind == "done"
                    and (event.payload or {}).get("canonical_runtime_status") == "completed"
                    for event in events
                ):
                    claim.finish("settled", evidence="terminal_tracker")
            else:
                raise BackendExecutionError("Native terminal handoff could not be verified.")
            return events
        except BaseException:
            input_may_have_started = attempted and (
                dispatch is None or dispatch.m_input_started.is_set()
            )
            claim.finish("uncertain" if input_may_have_started else "failed")
            raise
        finally:
            if isinstance(backend, LocalInteractiveSession):
                backend.configure_request_dispatch(None)

    return run_mail_prompt(
        send_prompt=None,
        send_mail_prompt=send_owned,
        prompt_request=prompt_request,
        mailbox=mailbox,
    )


def _enrich_local_mail_prompt_args(
    *,
    mailbox: object,
    operation: str,
    args: dict[str, Any],
) -> dict[str, Any]:
    """Attach runtime-resolved mailbox principal records when available."""

    enriched = dict(args)
    if operation != "send" or not isinstance(mailbox, FilesystemMailboxResolvedConfig):
        return enriched

    enriched["resolved_sender"] = {
        "principal_id": mailbox.principal_id,
        "address": mailbox.address,
    }
    enriched["resolved_to"] = _resolve_registered_mail_principals(
        mailbox_root=mailbox.filesystem_root,
        addresses=_string_sequence(args.get("to")),
        field_name="to",
    )
    enriched["resolved_cc"] = _resolve_registered_mail_principals(
        mailbox_root=mailbox.filesystem_root,
        addresses=_string_sequence(args.get("cc")),
        field_name="cc",
    )
    return enriched


def _resolve_registered_mail_principals(
    *,
    mailbox_root: Path,
    addresses: tuple[str, ...],
    field_name: str,
) -> list[dict[str, str]]:
    """Resolve active mailbox registrations into managed-principal payloads."""

    principals: list[dict[str, str]] = []
    seen_addresses: set[str] = set()
    for address in addresses:
        normalized = address.strip()
        if not normalized or normalized in seen_addresses:
            continue
        seen_addresses.add(normalized)
        try:
            registration = load_active_mailbox_registration(mailbox_root, address=normalized)
        except (FileNotFoundError, MailboxBootstrapError) as exc:
            raise click.ClickException(
                f"Filesystem mailbox send requires an active registration for `{field_name}` "
                f"recipient `{normalized}`: {exc}"
            ) from exc
        principal_payload = {
            "principal_id": registration.owner_principal_id,
            "address": registration.address,
        }
        if registration.display_name:
            principal_payload["display_name"] = registration.display_name
        if registration.manifest_path_hint:
            principal_payload["manifest_path_hint"] = registration.manifest_path_hint
        if registration.role:
            principal_payload["role"] = registration.role
        principals.append(principal_payload)
    return principals


def _string_sequence(value: object) -> tuple[str, ...]:
    """Normalize one optional string sequence payload."""

    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, str) and item.strip())


def _managed_agent_turn_status(status: str) -> ManagedAgentTurnStatus:
    """Normalize one local runtime status into the public managed-agent enum."""

    if status in {"active", "completed", "failed", "interrupted", "unknown"}:
        return cast(ManagedAgentTurnStatus, status)
    return "unknown"


def _new_request_id(*, prefix: str) -> str:
    """Return one stable request id for direct local command responses."""

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}-{timestamp}-{uuid.uuid4().hex[:10]}"


def _require_local_filesystem_mailbox_target(
    target: ManagedAgentTarget,
    *,
    operation: str,
) -> RuntimeSessionController:
    """Return the local controller for one late mailbox workflow target."""

    if _target_uses_pair_api(target):
        raise click.ClickException(
            f"Late local mailbox {operation} is unavailable for server-backed or external "
            "pair-backed managed agents."
        )
    return _require_live_local_controller(
        target,
        operation=f"run late local mailbox {operation}",
    )
