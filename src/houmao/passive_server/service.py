"""Core service for the passive server."""

from __future__ import annotations

from houmao.execution.tmux import tmux_server_scope

from houmao.mailbox.online_models import (
    OnlineAttachRequest,
    OnlineControlFailure,
    OnlineControlRequest,
    OnlineBindingStatus,
)

import json
import logging
import os
import threading
from collections import OrderedDict
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, TypeVar
from urllib.parse import urlsplit
from uuid import uuid4

from houmao.agents.realm_controller.backends.tmux_runtime import (
    kill_tmux_session,
    tmux_session_exists,
)
from houmao.agents.realm_controller.errors import (
    GatewayHttpError,
    RetiredJoinedSessionError,
    SessionManifestError,
)
from houmao.agents.realm_controller.gateway_access_runtime import gateway_access_for_manifest
from houmao.agents.realm_controller.gateway_client import (
    GatewayClient,
    GatewayEndpoint,
)
from houmao.agents.realm_controller.native_refresh_models import (
    CommonPluginObservationV1,
    NativeHomeV1,
    NativeRefreshRequestV1,
    NativeRefreshResultV1,
)
from houmao.agents.realm_controller.headless_snapshots import latest_headless_turn
from houmao.agents.realm_controller.managed_control import (
    MANAGED_STRUCTURED_TUI_BACKENDS,
    ManagedControlObservationV1,
)
from houmao.agents.realm_controller.manifest import (
    load_session_manifest,
    require_registry_mode_authority,
)
from houmao.agents.realm_controller.native_surface import TerminalNativeSurfaceV1
from houmao.agents.realm_controller.runtime import _gateway_lifecycle_lock, resume_runtime_session
from houmao.mailbox.models import MailChannel
from houmao.agents.realm_controller.gateway_models import (
    GatewayAcceptedRequestV1,
    GatewayControlInputRequestV1,
    GatewayControlInputResultV1,
    GatewayHeadlessControlStateV1,
    GatewayMailActionResponseV1,
    GatewayMailArchiveRequestV1,
    GatewayMailLifecycleResponseV1,
    GatewayMailListRequestV1,
    GatewayMailListResponseV1,
    GatewayMailMarkRequestV1,
    GatewayMailMessageRequestV1,
    GatewayMailMessageResponseV1,
    GatewayMailMoveRequestV1,
    GatewayMailNotifierPutV1,
    GatewayMailNotifierStatusV1,
    GatewayMailPostRequestV1,
    GatewayMailReplyRequestV1,
    GatewayMailSendRequestV1,
    GatewayMailStatusV1,
    GatewayReminderCreateBatchV1,
    GatewayReminderCreateResultV1,
    GatewayReminderDeleteResultV1,
    GatewayReminderListV1,
    GatewayReminderPutV1,
    GatewayReminderV1,
    GatewayRequestCreateV1,
    GatewayRequestPayloadInterruptV1,
    GatewayRequestPayloadSubmitPromptV1,
    GatewayRequestPayloadSubmitWorkRequestV1,
    GatewayStatusV1,
    GatewayWebControlStateV1,
    GatewayWebHistoryV1,
    GatewayMemoryActionResponseV1,
    GatewayMemoryMemoResponseV1,
    GatewayMemoryMemoWriteRequestV1,
    GatewayMemoryPagePathRequestV1,
    GatewayMemoryPagePathResolutionV1,
    GatewayMemoryPageResponseV1,
    GatewayMemoryPageTreeRequestV1,
    GatewayMemoryPageTreeResponseV1,
    GatewayMemoryPageWriteRequestV1,
    GatewayMemorySummaryV1,
)
from houmao.agents.realm_controller.gateway_storage import gateway_paths_from_manifest_path
from houmao.agents.realm_controller.registry_storage import (
    remove_live_agent_record,
    resolve_known_managed_agent_records,
)
from houmao.agents.realm_controller.usage_models import UsagePage
from houmao.cao.models import CaoSuccessResponse
from houmao.gateway.access import (
    GatewayAccessError,
    GatewayAccessPolicy,
    GatewayRequestBinding,
    GatewaySelfKey,
    GatewayTarget,
)
from houmao.gateway.authorization_models import (
    DefaultFallbackReceipt,
    DefaultFallbackRequest,
    DefaultPermissionGroupReceipt,
    DefaultPermissionGroupRequest,
)
from houmao.gateway.owner_authority import RELAY_HEADER, issue_gateway_relay
from houmao.gateway.operations import WORK_REQUEST, native_command_candidate
from houmao.gateway.work_requests import render_work_request
from houmao.passive_server.admission import (
    CURRENT_ADMISSION,
    PASSIVE_PERMISSIONS,
    PassiveAccessTarget,
    PassiveAdmission,
)
from houmao.agents.realm_controller.registry_models import (
    LiveAgentRegistryRecordV2,
    ManagedAgentRegistryRecordV3,
)
from houmao.passive_server.compatibility import (
    gateway_summary_from_status,
    mailbox_summary_from_headless_control_state,
    mailbox_summary_from_registry_record,
    managed_headless_detail_response,
    managed_headless_history_from_turn_records,
    managed_headless_state_from_control_state,
    managed_identity_from_discovered_agent,
    managed_native_tui_detail_response,
    managed_runtime_headless_detail_response,
    managed_runtime_headless_state_from_observation,
    managed_service_detail_response,
    managed_service_state_from_observation,
    managed_web_state_from_observation,
    managed_web_detail_response,
    managed_web_history_response,
    managed_tui_detail_response,
    managed_tui_history_from_observation,
    managed_tui_state_from_observation,
)
from houmao.passive_server.config import PassiveServerConfig
from houmao.passive_server.discovery import DiscoveredAgent, RegistryDiscoveryService
from houmao.passive_server.headless import HeadlessAgentService
from houmao.passive_server.models import (
    AgentTuiDetailResponse,
    AgentTuiHistoryResponse,
    AgentWebStateResponse,
    AgentWebHistoryResponse,
    AgentTuiStateResponse,
    DiscoveredAgentConflictResponse,
    DiscoveredAgentListResponse,
    DiscoveredAgentSummary,
    PassiveAgentAddressCandidate,
    PassiveAgentAddressResolveResponse,
    PassiveAgentGatewayAddress,
    PassiveAgentActionResponse,
    PassiveCurrentInstance,
    PassiveHeadlessLaunchRequest,
    PassiveHeadlessLaunchResponse,
    PassiveHeadlessTurnAcceptedResponse,
    PassiveHeadlessTurnEventsResponse,
    PassiveHeadlessTurnRequest,
    PassiveHeadlessTurnStatusResponse,
    PassiveHealthResponse,
    PassivePromptRequest,
    PassiveRequestAcceptedResponse,
    PassiveWorkRequestReceipt,
)
from houmao.passive_server.observation import AgentTuiObserver, TuiObservationService
from houmao.server.models import (
    HoumaoManagedAgentGatewayInternalHeadlessPromptRequest,
    HoumaoManagedAgentDetailResponse,
    HoumaoManagedAgentGatewayNextPromptSessionRequest,
    HoumaoManagedAgentGatewayPromptControlRequest,
    HoumaoManagedAgentGatewayPromptControlResponse,
    HoumaoManagedAgentGatewaySummaryView,
    HoumaoManagedAgentHistoryResponse,
    HoumaoManagedAgentStateResponse,
    HoumaoTerminalSnapshotHistoryResponse,
    HoumaoTerminalStateResponse,
)

log = logging.getLogger(__name__)

_GatewayProxyT = TypeVar("_GatewayProxyT")
_AgentAddressStatus = Literal[
    "offline",
    "live_without_gateway",
    "live_with_gateway",
]


def _address_candidate_from_record(
    record: LiveAgentRegistryRecordV2 | ManagedAgentRegistryRecordV3,
    *,
    retired: bool,
) -> PassiveAgentAddressCandidate:
    """Build safe known-agent identity metadata from one registry record."""

    lifecycle = getattr(record, "lifecycle", None)
    lifecycle_state = "retired" if retired else (str(lifecycle.state) if lifecycle else "active")
    relaunchable = not retired and lifecycle is not None and lifecycle.relaunchable
    return PassiveAgentAddressCandidate(
        agent_id=record.agent_id,
        agent_name=record.agent_name,
        lifecycle_state=lifecycle_state,
        relaunchable=relaunchable,
        tool=record.identity.tool,
        backend=str(record.identity.backend),
        manifest_path=record.runtime.manifest_path,
        session_root=record.runtime.session_root,
    )


def _retired_manifest_error(
    record: LiveAgentRegistryRecordV2 | ManagedAgentRegistryRecordV3,
) -> RetiredJoinedSessionError | None:
    """Recognize retirement even when a reader holds a cached discovery row."""

    try:
        load_session_manifest(Path(record.runtime.manifest_path))
    except RetiredJoinedSessionError as exc:
        return exc
    except SessionManifestError:
        pass
    return None


def _current_gateway_address(
    record: LiveAgentRegistryRecordV2 | ManagedAgentRegistryRecordV3 | None,
) -> PassiveAgentGatewayAddress | None:
    """Return current gateway coordinates from a live record, if present."""

    if record is None or record.gateway is None:
        return None
    return PassiveAgentGatewayAddress(
        host=str(record.gateway.host),
        port=record.gateway.port,
        protocol_version=str(record.gateway.protocol_version),
    )


class PassiveServerService:
    """Passive-server lifecycle and request handling.

    This service owns startup/shutdown bookkeeping, discovery integration,
    and the methods backing the server's HTTP endpoints.
    """

    def __init__(self, config: PassiveServerConfig) -> None:
        self.m_config = config
        self.m_started_at_utc: str = ""
        self.m_discovery = RegistryDiscoveryService(config)
        self.m_observation = TuiObservationService(discovery=self.m_discovery, config=config)
        self.m_headless = HeadlessAgentService(config)
        self.m_access_lock: threading.Lock = threading.Lock()
        self.m_access_listener_id: str = uuid4().hex
        self.m_access_policies: OrderedDict[
            tuple[str, str, str, Path, str | None], GatewayAccessPolicy
        ] = OrderedDict()

    # -- lifecycle ------------------------------------------------------------

    def startup(self) -> None:
        """Create directories, write the on-disk marker, and start services."""

        self.m_started_at_utc = datetime.now(UTC).isoformat(timespec="seconds")
        self.m_config.run_dir.mkdir(parents=True, exist_ok=True)
        self._write_current_instance()
        self.m_discovery.start()
        self.m_observation.start()
        self.m_headless.start()

    def shutdown(self) -> None:
        """Stop services and remove the on-disk current-instance marker."""

        self.m_headless.stop()
        self.m_observation.stop()
        self.m_discovery.stop()
        try:
            self.m_config.current_instance_path.unlink(missing_ok=True)
        except OSError:
            pass

    # -- endpoint helpers -----------------------------------------------------

    def health(self) -> PassiveHealthResponse:
        """Build the health response payload."""

        return PassiveHealthResponse()

    def current_instance(self) -> PassiveCurrentInstance:
        """Build the current-instance response payload."""

        return PassiveCurrentInstance(
            pid=os.getpid(),
            api_base_url=self.m_config.api_base_url,
            server_root=str(self.m_config.server_root),
            started_at_utc=self.m_started_at_utc,
        )

    def list_agents(self) -> DiscoveredAgentListResponse:
        """Return all discovered agents."""

        agents = self.m_discovery.index.list_all()
        return DiscoveredAgentListResponse(
            agents=[a.summary for a in agents if _retired_manifest_error(a.record) is None]
        )

    def resolve_agent(
        self, agent_ref: str
    ) -> DiscoveredAgentSummary | DiscoveredAgentConflictResponse | None:
        """Resolve one agent by id or name.

        Returns:
            ``DiscoveredAgentSummary`` on unique match,
            ``DiscoveredAgentConflictResponse`` on ambiguous name,
            ``None`` on not-found.
        """

        by_id = self.m_discovery.index.get_by_id(agent_ref)
        if by_id is not None:
            return by_id.summary if _retired_manifest_error(by_id.record) is None else None

        by_name = [
            agent
            for agent in self.m_discovery.index.get_by_name(agent_ref)
            if _retired_manifest_error(agent.record) is None
        ]
        if len(by_name) == 1:
            return by_name[0].summary
        if len(by_name) > 1:
            ids = [a.record.agent_id for a in by_name]
            return DiscoveredAgentConflictResponse(
                detail=f"Ambiguous agent name: {len(by_name)} agents share this name. "
                f"Disambiguate by agent_id.",
                agent_ids=ids,
            )
        return None

    def resolve_agent_address(self, agent_ref: str) -> PassiveAgentAddressResolveResponse:
        """Resolve one durable agent address for AG-UI GUI attachment."""

        known_records = list(
            resolve_known_managed_agent_records(
                agent_ref,
                env=self.m_config.registry_helper_env(),
            )
        )
        if not known_records:
            live_by_id = self.m_discovery.index.get_by_id(agent_ref)
            if live_by_id is not None:
                known_records = [live_by_id.record]
            else:
                live_by_name = self.m_discovery.index.get_by_name(agent_ref)
                if len(live_by_name) > 1:
                    return PassiveAgentAddressResolveResponse(
                        status="ambiguous",
                        detail=(
                            f"Ambiguous agent name: {len(live_by_name)} agents share this "
                            "name. Disambiguate by agent_id."
                        ),
                        agent_ref=agent_ref,
                        candidates=[
                            _address_candidate_from_record(
                                agent.record,
                                retired=_retired_manifest_error(agent.record) is not None,
                            )
                            for agent in live_by_name
                        ],
                    )
                if len(live_by_name) == 1:
                    known_records = [live_by_name[0].record]

        if not known_records:
            return PassiveAgentAddressResolveResponse(
                status="unknown",
                detail=f"Agent not found: {agent_ref}",
                agent_ref=agent_ref,
            )
        if len(known_records) > 1:
            return PassiveAgentAddressResolveResponse(
                status="ambiguous",
                detail=(
                    f"Ambiguous agent name: {len(known_records)} known agents share this "
                    "name. Disambiguate by agent_id."
                ),
                agent_ref=agent_ref,
                candidates=[
                    _address_candidate_from_record(
                        record, retired=_retired_manifest_error(record) is not None
                    )
                    for record in known_records
                ],
            )

        record = known_records[0]
        retirement = _retired_manifest_error(record)
        live_agent = self.m_discovery.index.get_by_id(record.agent_id)
        if (
            live_agent is not None
            and live_agent.record.runtime.manifest_path != record.runtime.manifest_path
            and _retired_manifest_error(live_agent.record) is not None
        ):
            live_agent = None
        gateway = _current_gateway_address(live_agent.record if live_agent is not None else None)
        if retirement is not None:
            status: _AgentAddressStatus = "offline"
            detail = str(retirement)
            gateway = None
        elif live_agent is None:
            status = "offline"
            detail = "Agent is known but no live gateway-capable session is currently discovered."
        elif gateway is None:
            status = "live_without_gateway"
            detail = "Agent is live but has no current gateway coordinates."
        else:
            status = "live_with_gateway"
            detail = "Agent is live and current gateway coordinates are available."

        candidate = _address_candidate_from_record(record, retired=retirement is not None)
        return PassiveAgentAddressResolveResponse(
            status=status,
            detail=detail,
            agent_ref=agent_ref,
            agent_id=candidate.agent_id,
            agent_name=candidate.agent_name,
            generation_id=record.generation_id if retirement is None else None,
            lifecycle_state=candidate.lifecycle_state,
            relaunchable=candidate.relaunchable,
            tool=candidate.tool,
            backend=candidate.backend,
            manifest_path=candidate.manifest_path,
            session_root=candidate.session_root,
            gateway=gateway,
        )

    def resolve_access_target(
        self, agent_ref: str
    ) -> PassiveAccessTarget | tuple[int, dict[str, Any]]:
        """Resolve an owner-local policy independently of current gateway presence."""

        tracked = self.m_headless.resolve_usage_matches(agent_ref)
        discovered = self._resolve_agent_or_error(agent_ref)
        if isinstance(discovered, tuple) and discovered[0] == 409:
            return discovered
        if len(tracked) > 1:
            return (409, {"detail": "Ambiguous managed agent reference"})
        if not tracked and not isinstance(discovered, tuple):
            tracked = self.m_headless.resolve_usage_matches(discovered.record.agent_id)
            if len(tracked) > 1:
                return (409, {"detail": "Ambiguous managed agent reference"})
        tracked_id = tracked[0] if tracked else None
        tracked_authority = (
            self.m_headless.access_authority(tracked_id) if tracked_id is not None else None
        )
        if tracked_id is not None and tracked_authority is None:
            return (503, {"detail": "Target access policy is unavailable"})

        record = discovered.record if not isinstance(discovered, tuple) else None
        canonical = tracked_authority.agent_id if tracked_authority is not None else None
        if record is not None and canonical is not None and record.agent_id != canonical:
            return (409, {"detail": "Ambiguous managed agent reference"})
        known_records = resolve_known_managed_agent_records(
            canonical or (record.agent_id if record is not None else agent_ref),
            env=self.m_config.registry_helper_env(),
        )
        if len(known_records) > 1:
            return (409, {"detail": "Ambiguous managed agent reference"})
        if known_records:
            record = known_records[0]
        elif isinstance(discovered, tuple) and discovered[0] == 410:
            return discovered

        if tracked_authority is not None:
            manifest_path = Path(tracked_authority.manifest_path)
        elif record is not None:
            manifest_path = Path(record.runtime.manifest_path)
        else:
            return (404, {"detail": "Agent not found"})

        try:
            runtime = gateway_access_for_manifest(manifest_path)
            runtime.require_current()
            target = runtime.target
            if canonical is not None and canonical != target.owner.agent_id:
                raise GatewayAccessError(503, "policy_unavailable")
            if record is not None and (
                record.agent_id != target.owner.agent_id
                or record.execution_binding is None
                or record.execution_binding.context_id != target.owner.context_id
                or record.generation_id != target.incarnation
                or Path(record.runtime.manifest_path) != manifest_path
            ):
                raise GatewayAccessError(503, "policy_unavailable")

            def current_target() -> GatewayTarget:
                """Verify that the selected manifest still owns this incarnation."""

                runtime.require_current()
                return runtime.target

            def current_self() -> GatewaySelfKey | None:
                """Use registry self authority or the live managed-headless controller."""

                if tracked_id is not None and self.m_headless.access_body_is_live(
                    tracked_id, manifest_path=manifest_path
                ):
                    runtime.require_current()
                    return runtime.store.load_self(target.incarnation)
                return runtime.current_self()

            cache_key = (
                target.owner.agent_id,
                target.owner.context_id,
                target.incarnation,
                manifest_path,
                tracked_id,
            )
            with self.m_access_lock:
                policy = self.m_access_policies.get(cache_key)
                if policy is None:
                    policy = GatewayAccessPolicy(
                        store=runtime.store,
                        target=current_target,
                        current_self=current_self,
                        listener_id=self.m_access_listener_id,
                        catalog=lambda: PASSIVE_PERMISSIONS,
                    )
                    self.m_access_policies[cache_key] = policy
                    if len(self.m_access_policies) > 256:
                        self.m_access_policies.popitem(last=False)
                else:
                    self.m_access_policies.move_to_end(cache_key)
        except RetiredJoinedSessionError as exc:
            return (410, {"detail": str(exc)})
        except (GatewayAccessError, RuntimeError, OSError, ValueError):
            return (503, {"detail": "Target access policy is unavailable"})
        return PassiveAccessTarget(runtime, policy, tracked_id, manifest_path)

    def require_access_target_current(self, selected: PassiveAccessTarget) -> None:
        """Reject a generation replacement that occurred during request admission."""

        try:
            selected.runtime.require_current()
        except RetiredJoinedSessionError:
            raise GatewayAccessError(503, "policy_unavailable") from None
        target = selected.runtime.target
        current = resolve_known_managed_agent_records(
            target.owner.agent_id, env=self.m_config.registry_helper_env()
        )
        if current and (
            len(current) != 1
            or current[0].agent_id != target.owner.agent_id
            or current[0].generation_id != target.incarnation
            or current[0].execution_binding != selected.runtime.execution_binding
            or Path(current[0].runtime.manifest_path) != selected.manifest_path
        ):
            raise GatewayAccessError(503, "policy_unavailable")

    def _require_direct_access(
        self, *, handoff: bool = False, admission: PassiveAdmission | None = None
    ) -> None:
        """Recheck the caller before disclosure or claim one admitted direct effect."""

        admission = admission if admission is not None else CURRENT_ADMISSION.get()
        if admission is None or admission.grant is None:
            return
        selected = admission.target
        try:
            self.require_access_target_current(selected)
            if selected.tracked_agent_id is not None:
                authority = self.m_headless.access_authority(selected.tracked_agent_id)
                if (
                    authority is None
                    or Path(authority.manifest_path) != selected.manifest_path
                    or authority.agent_id not in {None, selected.runtime.target.owner.agent_id}
                ):
                    raise GatewayAccessError(503, "policy_unavailable")
            if handoff:
                selected.policy.handoff(admission.grant)
            elif not selected.policy.revalidate(admission.grant):
                raise GatewayAccessError(401, "invalid_proof")
        except GatewayAccessError:
            raise
        except (OSError, RuntimeError, ValueError):
            raise GatewayAccessError(503, "policy_unavailable") from None

    def set_default_permission_group(
        self, payload: DefaultPermissionGroupRequest
    ) -> DefaultPermissionGroupReceipt:
        """Commit the passive listener's admitted default-group mutation."""

        admission = CURRENT_ADMISSION.get()
        if admission is None or admission.grant is None:
            raise GatewayAccessError(403, "insufficient_authority")
        payload.require_expected(admission.grant)
        return admission.target.policy.set_default_permission_group(
            admission.grant,
            payload.group,
            require_current_target=lambda: self.require_access_target_current(admission.target),
        )

    def set_default_fallback(
        self, principal_id: str, payload: DefaultFallbackRequest
    ) -> DefaultFallbackReceipt:
        """Commit the passive listener's admitted principal fallback mutation."""

        admission = CURRENT_ADMISSION.get()
        if admission is None or admission.grant is None:
            raise GatewayAccessError(403, "insufficient_authority")
        payload.require_expected(admission.grant)
        return admission.target.policy.set_default_fallback(
            admission.grant,
            principal_id,
            payload.enabled,
            require_current_target=lambda: self.require_access_target_current(admission.target),
        )

    def _claim_direct_effect(self) -> None:
        """Claim the admitted decision at the direct mutation boundary."""

        self._require_direct_access(handoff=True)

    def get_usage(
        self, agent_ref: str, *, after: str | None = None, limit: int = 100
    ) -> UsagePage | tuple[int, dict[str, Any]]:
        """Read managed-headless authority first, otherwise proxy a live gateway."""

        admitted = CURRENT_ADMISSION.get()
        if admitted is not None and admitted.target.tracked_agent_id is not None:
            self._require_direct_access()
            return self.m_headless.get_usage(
                admitted.target.tracked_agent_id, after=after, limit=limit
            )

        matches = self.m_headless.resolve_usage_matches(agent_ref) if admitted is None else ()
        if len(matches) > 1:
            return (409, {"detail": "Ambiguous managed headless agent reference"})
        if len(matches) == 1:
            by_id = self.m_discovery.index.get_by_id(agent_ref)
            discovered = (
                [by_id] if by_id is not None else self.m_discovery.index.get_by_name(agent_ref)
            )
            if any(
                matches[0] not in self.m_headless.resolve_usage_matches(agent.record.agent_id)
                for agent in discovered
            ):
                return (409, {"detail": "Ambiguous managed agent reference"})
            return self.m_headless.get_usage(matches[0], after=after, limit=limit)

        resolved = self._resolve_agent_or_error(agent_ref)
        if isinstance(resolved, tuple):
            return resolved
        if admitted is None:
            matches = self.m_headless.resolve_usage_matches(resolved.record.agent_id)
            if len(matches) > 1:
                return (409, {"detail": "Ambiguous managed headless agent reference"})
            if len(matches) == 1:
                return self.m_headless.get_usage(matches[0], after=after, limit=limit)
        client = self._gateway_client_for_agent(resolved)
        if client is None:
            return (502, {"detail": "Usage projection requires an attached gateway"})
        try:
            return client.get_usage(after=after, limit=limit)
        except GatewayHttpError as exc:
            return self._gateway_http_error_tuple(exc)

    # -- gateway proxy --------------------------------------------------------

    def _resolve_agent_or_error(
        self, agent_ref: str
    ) -> DiscoveredAgent | tuple[int, dict[str, Any]]:
        """Resolve an agent by id or name, returning an error tuple on failure."""

        admitted = CURRENT_ADMISSION.get()
        if admitted is not None:
            target = admitted.target.runtime.target
            by_id = self.m_discovery.index.get_by_id(target.owner.agent_id)
            if by_id is None:
                return (502, {"detail": "No gateway attached to agent"})
            retirement = _retired_manifest_error(by_id.record)
            if retirement is not None:
                return (410, {"detail": str(retirement)})
            if by_id.record.generation_id != target.incarnation:
                return (503, {"detail": "Target access policy is unavailable"})
            known = resolve_known_managed_agent_records(
                target.owner.agent_id, env=self.m_config.registry_helper_env()
            )
            if known:
                self.require_access_target_current(admitted.target)
                if known[0].lifecycle.state != "active":
                    return (502, {"detail": "No active gateway attached to agent"})
                return DiscoveredAgent(record=known[0], summary=by_id.summary)
            return by_id

        by_id = self.m_discovery.index.get_by_id(agent_ref)
        if by_id is not None:
            retirement = _retired_manifest_error(by_id.record)
            if retirement is not None:
                return (410, {"detail": str(retirement)})
            return by_id

        by_name = self.m_discovery.index.get_by_name(agent_ref)
        if len(by_name) == 1:
            retirement = _retired_manifest_error(by_name[0].record)
            if retirement is not None:
                return (410, {"detail": str(retirement)})
            return by_name[0]
        if len(by_name) > 1:
            ids = [a.record.agent_id for a in by_name]
            return (
                409,
                DiscoveredAgentConflictResponse(
                    detail=f"Ambiguous agent name: {len(by_name)} agents share this name. "
                    f"Disambiguate by agent_id.",
                    agent_ids=ids,
                ).model_dump(mode="json"),
            )
        return (404, {"detail": f"Agent not found: {agent_ref}"})

    def _gateway_client_for_agent(self, agent: DiscoveredAgent) -> GatewayClient | None:
        """Build a ``GatewayClient`` from the agent's registry record, or ``None``."""

        gw = agent.record.gateway
        if gw is None or gw.host is None or gw.port is None:
            return None
        endpoint = GatewayEndpoint(host="127.0.0.1", port=gw.port)
        admitted = CURRENT_ADMISSION.get()
        if admitted is None or admitted.grant is None:
            return GatewayClient(endpoint=endpoint, respect_proxy_env=False)

        grant = admitted.grant
        receiver_id: str | None = None

        def request_proof(method: str, path: str, body: bytes) -> dict[str, str]:
            """Mint exact one-use evidence for the selected live gateway instance."""

            nonlocal receiver_id
            parts = urlsplit(path)
            target = admitted.target.runtime.target
            record = agent.record
            operation = next(
                (
                    operation
                    for verb, route, operation in admitted.relay_operations
                    if (verb, route) == (method, parts.path)
                ),
                None,
            )
            if (
                operation is None
                or record.agent_id != target.owner.agent_id
                or record.execution_binding != admitted.target.runtime.execution_binding
                or record.generation_id != target.incarnation
            ):
                raise GatewayHttpError(
                    method=method, url="", status_code=403, detail="Gateway relay scope denied"
                )
            try:
                self.require_access_target_current(admitted.target)
                if not admitted.target.policy.revalidate(grant):
                    raise GatewayAccessError(401, "invalid_proof")
                permissions = operation.permissions(body)
                if not set(permissions).issubset(grant.permissions):
                    raise GatewayAccessError(403, "insufficient_authority")
                if receiver_id is None:
                    descriptor = GatewayClient(
                        endpoint=endpoint, respect_proxy_env=False
                    ).describe_endpoint()
                    if descriptor.target != target or not descriptor.presence_id:
                        raise GatewayAccessError(503, "policy_unavailable")
                    receiver_id = descriptor.presence_id
                request_binding = GatewayRequestBinding.from_request(
                    method, parts.path, parts.query, body
                )
                token = issue_gateway_relay(
                    admitted.target.runtime.private_root,
                    grant=grant,
                    request=request_binding,
                    receiver_id=receiver_id,
                    permissions=permissions,
                )
            except GatewayAccessError as exc:
                raise GatewayHttpError(
                    method=method,
                    url="",
                    status_code=exc.status_code,
                    detail=json.dumps({"error_code": exc.code}),
                ) from None
            return {RELAY_HEADER: token}

        return GatewayClient(
            endpoint=endpoint, request_proof=request_proof, respect_proxy_env=False
        )

    def gateway_status(self, agent_ref: str) -> GatewayStatusV1 | tuple[int, dict[str, Any]]:
        """Proxy ``GET /v1/status`` to the agent's gateway."""

        resolved = self._resolve_agent_or_error(agent_ref)
        if isinstance(resolved, tuple):
            return resolved
        client = self._gateway_client_for_agent(resolved)
        if client is None:
            return (502, {"detail": "No gateway attached to agent"})
        try:
            return client.status()
        except GatewayHttpError as exc:
            return self._gateway_http_error_tuple(exc)

    def gateway_native_home(self, agent_ref: str) -> NativeHomeV1 | tuple[int, dict[str, Any]]:
        """Proxy authoritative native-home inspection without reading local home material."""

        return self._native_refresh_gateway_proxy(agent_ref, lambda _client, home: home)

    def gateway_common_plugin_state(
        self, agent_ref: str
    ) -> CommonPluginObservationV1 | tuple[int, dict[str, Any]]:
        """Preserve passive common-plugin evidence without making a freshness decision."""

        return self._native_refresh_gateway_proxy(
            agent_ref, lambda client, _home: client.get_common_plugin_state()
        )

    def gateway_refresh_native(
        self, agent_ref: str, payload: NativeRefreshRequestV1
    ) -> NativeRefreshResultV1 | tuple[int, dict[str, Any]]:
        """Forward exactly one refresh, including typed refusal and partial-effect results."""

        return self._native_refresh_gateway_proxy(
            agent_ref, lambda client, _home: client.refresh_native(payload)
        )

    def _native_refresh_gateway_proxy(
        self,
        agent_ref: str,
        callback: Callable[[GatewayClient, NativeHomeV1], _GatewayProxyT],
    ) -> _GatewayProxyT | tuple[int, dict[str, Any]]:
        """Resolve one gateway and suppress private transport or invalid-response details."""

        resolved = self._resolve_agent_or_error(agent_ref)
        if isinstance(resolved, tuple):
            return resolved
        client = self._gateway_client_for_agent(resolved)
        if client is None:
            return (502, {"detail": "Native refresh projection requires an attached gateway"})
        try:
            home = client.get_native_home()
            record = resolved.record
            surface = record.native_surface
            if (
                home.agent_id != record.agent_id
                or home.identity.get("agent_id") != record.agent_id
                or home.backend != record.identity.backend
                or home.tool != record.identity.tool
                or home.identity.get("generation") != record.generation_id
                or (
                    surface is not None
                    and surface.kind == "web"
                    and home.identity.get("native_session_id") != surface.native_session_id
                )
            ):
                return (502, {"detail": "Agent gateway native authority does not match selection"})
            client.bind_native_home(home)
            result = callback(client, home)
            returned_home: NativeHomeV1 | None = None
            if isinstance(result, NativeHomeV1):
                returned_home = result
            elif isinstance(result, CommonPluginObservationV1):
                returned_home = result.home
            elif isinstance(result, NativeRefreshResultV1):
                returned_home = result.observation.home
            if returned_home != home or (
                isinstance(result, NativeRefreshResultV1)
                and result.before is not None
                and result.before.home != home
            ):
                return (502, {"detail": "Agent gateway native authority changed during request"})
            return result
        except GatewayHttpError as exc:
            if exc.status_code in {401, 403}:
                return self._gateway_http_error_tuple(exc)
            return (
                exc.status_code or 502,
                {"detail": "Agent gateway native refresh response is unavailable"},
            )

    def gateway_memory(
        self,
        agent_ref: str,
    ) -> GatewayMemorySummaryV1 | tuple[int, dict[str, Any]]:
        """Proxy `GET /v1/memory` to the agent's gateway."""

        return self._gateway_proxy(agent_ref, lambda client: client.memory())

    def gateway_memory_memo(
        self,
        agent_ref: str,
    ) -> GatewayMemoryMemoResponseV1 | tuple[int, dict[str, Any]]:
        """Proxy `GET /v1/memory/memo` to the agent's gateway."""

        return self._gateway_proxy(agent_ref, lambda client: client.read_memory_memo())

    def gateway_memory_memo_put(
        self,
        agent_ref: str,
        payload: GatewayMemoryMemoWriteRequestV1,
    ) -> GatewayMemoryMemoResponseV1 | tuple[int, dict[str, Any]]:
        """Proxy `PUT /v1/memory/memo` to the agent's gateway."""

        return self._gateway_proxy(
            agent_ref,
            lambda client: client.write_memory_memo(payload),
        )

    def gateway_memory_memo_append(
        self,
        agent_ref: str,
        payload: GatewayMemoryMemoWriteRequestV1,
    ) -> GatewayMemoryMemoResponseV1 | tuple[int, dict[str, Any]]:
        """Proxy `POST /v1/memory/memo/append` to the agent's gateway."""

        return self._gateway_proxy(
            agent_ref,
            lambda client: client.append_memory_memo(payload),
        )

    def gateway_memory_pages(
        self,
        agent_ref: str,
        payload: GatewayMemoryPageTreeRequestV1,
    ) -> GatewayMemoryPageTreeResponseV1 | tuple[int, dict[str, Any]]:
        """Proxy `POST /v1/memory/pages/tree` to the agent's gateway."""

        return self._gateway_proxy(
            agent_ref,
            lambda client: client.list_memory_pages(payload),
        )

    def gateway_memory_page_resolve(
        self,
        agent_ref: str,
        payload: GatewayMemoryPagePathRequestV1,
    ) -> GatewayMemoryPagePathResolutionV1 | tuple[int, dict[str, Any]]:
        """Proxy `POST /v1/memory/pages/resolve` to the agent's gateway."""

        return self._gateway_proxy(
            agent_ref,
            lambda client: client.resolve_memory_page_path(payload),
        )

    def gateway_memory_page_read(
        self,
        agent_ref: str,
        payload: GatewayMemoryPagePathRequestV1,
    ) -> GatewayMemoryPageResponseV1 | tuple[int, dict[str, Any]]:
        """Proxy `POST /v1/memory/pages/read` to the agent's gateway."""

        return self._gateway_proxy(
            agent_ref,
            lambda client: client.read_memory_page(payload),
        )

    def gateway_memory_page_write(
        self,
        agent_ref: str,
        payload: GatewayMemoryPageWriteRequestV1,
    ) -> GatewayMemoryActionResponseV1 | tuple[int, dict[str, Any]]:
        """Proxy `POST /v1/memory/pages/write` to the agent's gateway."""

        return self._gateway_proxy(
            agent_ref,
            lambda client: client.write_memory_page(payload),
        )

    def gateway_memory_page_append(
        self,
        agent_ref: str,
        payload: GatewayMemoryPageWriteRequestV1,
    ) -> GatewayMemoryActionResponseV1 | tuple[int, dict[str, Any]]:
        """Proxy `POST /v1/memory/pages/append` to the agent's gateway."""

        return self._gateway_proxy(
            agent_ref,
            lambda client: client.append_memory_page(payload),
        )

    def gateway_memory_page_delete(
        self,
        agent_ref: str,
        payload: GatewayMemoryPagePathRequestV1,
    ) -> GatewayMemoryActionResponseV1 | tuple[int, dict[str, Any]]:
        """Proxy `POST /v1/memory/pages/delete` to the agent's gateway."""

        return self._gateway_proxy(
            agent_ref,
            lambda client: client.delete_memory_page(payload),
        )

    def gateway_tui_state(
        self,
        agent_ref: str,
    ) -> HoumaoTerminalStateResponse | tuple[int, dict[str, Any]]:
        """Proxy `GET /v1/control/tui/state` to the agent's gateway."""

        resolved = self._resolve_agent_or_error(agent_ref)
        if isinstance(resolved, tuple):
            return resolved
        if resolved.record.identity.backend in MANAGED_STRUCTURED_TUI_BACKENDS:
            return (501, {"detail": "Terminal parser state is unsupported for Hermes TUI"})
        client = self._gateway_client_for_agent(resolved)
        if client is None:
            return (502, {"detail": "No gateway attached to agent"})
        try:
            return client.get_tui_state()
        except GatewayHttpError as exc:
            return self._gateway_http_error_tuple(exc)

    def gateway_web_state(
        self, agent_ref: str
    ) -> GatewayWebControlStateV1 | tuple[int, dict[str, Any]]:
        """Proxy the gateway's structured native Web state without cold activation."""

        return self._gateway_proxy(agent_ref, lambda client: client.get_web_state())

    def gateway_web_history(
        self, agent_ref: str, *, limit: int = 100
    ) -> GatewayWebHistoryV1 | tuple[int, dict[str, Any]]:
        """Proxy bounded native Web transition metadata."""

        return self._gateway_proxy(agent_ref, lambda client: client.get_web_history(limit=limit))

    def gateway_tui_history(
        self,
        agent_ref: str,
        *,
        limit: int = 100,
    ) -> HoumaoTerminalSnapshotHistoryResponse | tuple[int, dict[str, Any]]:
        """Proxy `GET /v1/control/tui/history` to the agent's gateway."""

        resolved = self._resolve_agent_or_error(agent_ref)
        if isinstance(resolved, tuple):
            return resolved
        if resolved.record.identity.backend in MANAGED_STRUCTURED_TUI_BACKENDS:
            return (501, {"detail": "Terminal tracker history is unsupported for Hermes TUI"})
        client = self._gateway_client_for_agent(resolved)
        if client is None:
            return (502, {"detail": "No gateway attached to agent"})
        try:
            return client.get_tui_history(limit=limit)
        except GatewayHttpError as exc:
            return self._gateway_http_error_tuple(exc)

    def gateway_tui_note_prompt(
        self,
        agent_ref: str,
        *,
        prompt: str,
    ) -> HoumaoTerminalStateResponse | tuple[int, dict[str, Any]]:
        """Proxy `POST /v1/control/tui/note-prompt` to the agent's gateway."""

        resolved = self._resolve_agent_or_error(agent_ref)
        if isinstance(resolved, tuple):
            return resolved
        if resolved.record.identity.backend in MANAGED_STRUCTURED_TUI_BACKENDS:
            return (501, {"detail": "Terminal tracker prompt notes are unsupported for Hermes TUI"})
        client = self._gateway_client_for_agent(resolved)
        if client is None:
            return (502, {"detail": "No gateway attached to agent"})
        try:
            return client.note_tui_prompt_submission(prompt=prompt)
        except GatewayHttpError as exc:
            return self._gateway_http_error_tuple(exc)

    def gateway_headless_control_state(
        self,
        agent_ref: str,
    ) -> GatewayHeadlessControlStateV1 | tuple[int, dict[str, Any]]:
        """Proxy `GET /v1/control/headless/state` to the agent's gateway."""

        resolved = self._resolve_agent_or_error(agent_ref)
        if isinstance(resolved, tuple):
            return resolved
        client = self._gateway_client_for_agent(resolved)
        if client is None:
            return (502, {"detail": "No gateway attached to agent"})
        try:
            return client.get_headless_control_state()
        except GatewayHttpError as exc:
            return self._gateway_http_error_tuple(exc)

    def gateway_headless_next_prompt_session(
        self,
        agent_ref: str,
        payload: HoumaoManagedAgentGatewayNextPromptSessionRequest,
    ) -> GatewayHeadlessControlStateV1 | tuple[int, dict[str, Any]]:
        """Proxy `POST /v1/control/headless/next-prompt-session` to the agent's gateway."""

        resolved = self._resolve_agent_or_error(agent_ref)
        if isinstance(resolved, tuple):
            return resolved
        client = self._gateway_client_for_agent(resolved)
        if client is None:
            return (502, {"detail": "No gateway attached to agent"})
        try:
            return client.set_headless_next_prompt_session(payload)
        except GatewayHttpError as exc:
            return self._gateway_http_error_tuple(exc)

    def gateway_create_request(
        self, agent_ref: str, payload: GatewayRequestCreateV1
    ) -> GatewayAcceptedRequestV1 | tuple[int, dict[str, Any]]:
        """Proxy ``POST /v1/requests`` to the agent's gateway."""

        resolved = self._resolve_agent_or_error(agent_ref)
        if isinstance(resolved, tuple):
            return resolved
        client = self._gateway_client_for_agent(resolved)
        if client is None:
            return (502, {"detail": "No gateway attached to agent"})
        try:
            return client.create_request(payload)
        except GatewayHttpError as exc:
            return self._gateway_http_error_tuple(exc)

    def gateway_control_prompt(
        self,
        agent_ref: str,
        payload: HoumaoManagedAgentGatewayPromptControlRequest,
    ) -> HoumaoManagedAgentGatewayPromptControlResponse | tuple[int, dict[str, Any]]:
        """Proxy `POST /v1/control/prompt` to the agent's gateway."""

        resolved = self._resolve_agent_or_error(agent_ref)
        if isinstance(resolved, tuple):
            return resolved
        client = self._gateway_client_for_agent(resolved)
        if client is None:
            return (502, {"detail": "No gateway attached to agent"})
        try:
            response = client.control_prompt(payload)
        except GatewayHttpError as exc:
            return self._gateway_http_error_tuple(exc)
        return HoumaoManagedAgentGatewayPromptControlResponse.model_validate(
            response.model_dump(mode="json")
        )

    def gateway_send_control_input(
        self,
        agent_ref: str,
        payload: GatewayControlInputRequestV1,
    ) -> GatewayControlInputResultV1 | tuple[int, dict[str, Any]]:
        """Proxy `POST /v1/control/send-keys` to the agent's gateway."""

        resolved = self._resolve_agent_or_error(agent_ref)
        if isinstance(resolved, tuple):
            return resolved
        client = self._gateway_client_for_agent(resolved)
        if client is None:
            return (502, {"detail": "No gateway attached to agent"})
        try:
            return client.send_control_input(payload)
        except GatewayHttpError as exc:
            return self._gateway_http_error_tuple(exc)

    def gateway_mail_notifier_status(
        self,
        agent_ref: str,
        *,
        channel: MailChannel,
    ) -> GatewayMailNotifierStatusV1 | tuple[int, dict[str, Any]]:
        """Proxy `GET /v1/mail-notifier` to the agent's gateway."""

        resolved = self._resolve_agent_or_error(agent_ref)
        if isinstance(resolved, tuple):
            return resolved
        client = self._gateway_client_for_agent(resolved)
        if client is None:
            return (502, {"detail": "No gateway attached to agent"})
        try:
            return client.get_mail_notifier(channel=channel)
        except GatewayHttpError as exc:
            return self._gateway_http_error_tuple(exc)

    def gateway_mail_notifier_enable(
        self,
        agent_ref: str,
        payload: GatewayMailNotifierPutV1,
        *,
        channel: MailChannel,
    ) -> GatewayMailNotifierStatusV1 | tuple[int, dict[str, Any]]:
        """Proxy `PUT /v1/mail-notifier` to the agent's gateway."""

        resolved = self._resolve_agent_or_error(agent_ref)
        if isinstance(resolved, tuple):
            return resolved
        client = self._gateway_client_for_agent(resolved)
        if client is None:
            return (502, {"detail": "No gateway attached to agent"})
        try:
            return client.put_mail_notifier(payload, channel=channel)
        except GatewayHttpError as exc:
            return self._gateway_http_error_tuple(exc)

    def gateway_mail_notifier_disable(
        self,
        agent_ref: str,
        *,
        channel: MailChannel,
    ) -> GatewayMailNotifierStatusV1 | tuple[int, dict[str, Any]]:
        """Proxy `DELETE /v1/mail-notifier` to the agent's gateway."""

        resolved = self._resolve_agent_or_error(agent_ref)
        if isinstance(resolved, tuple):
            return resolved
        client = self._gateway_client_for_agent(resolved)
        if client is None:
            return (502, {"detail": "No gateway attached to agent"})
        try:
            return client.delete_mail_notifier(channel=channel)
        except GatewayHttpError as exc:
            return self._gateway_http_error_tuple(exc)

    def gateway_reminders(
        self,
        agent_ref: str,
    ) -> GatewayReminderListV1 | tuple[int, dict[str, Any]]:
        """Proxy `GET /v1/reminders` to the agent's gateway."""

        resolved = self._resolve_agent_or_error(agent_ref)
        if isinstance(resolved, tuple):
            return resolved
        client = self._gateway_client_for_agent(resolved)
        if client is None:
            return (502, {"detail": "No gateway attached to agent"})
        try:
            return client.list_reminders()
        except GatewayHttpError as exc:
            return self._gateway_http_error_tuple(exc)

    def gateway_create_reminders(
        self,
        agent_ref: str,
        payload: GatewayReminderCreateBatchV1,
    ) -> GatewayReminderCreateResultV1 | tuple[int, dict[str, Any]]:
        """Proxy `POST /v1/reminders` to the agent's gateway."""

        resolved = self._resolve_agent_or_error(agent_ref)
        if isinstance(resolved, tuple):
            return resolved
        client = self._gateway_client_for_agent(resolved)
        if client is None:
            return (502, {"detail": "No gateway attached to agent"})
        try:
            return client.create_reminders(payload)
        except GatewayHttpError as exc:
            return self._gateway_http_error_tuple(exc)

    def gateway_get_reminder(
        self,
        agent_ref: str,
        reminder_id: str,
    ) -> GatewayReminderV1 | tuple[int, dict[str, Any]]:
        """Proxy `GET /v1/reminders/{reminder_id}` to the agent's gateway."""

        resolved = self._resolve_agent_or_error(agent_ref)
        if isinstance(resolved, tuple):
            return resolved
        client = self._gateway_client_for_agent(resolved)
        if client is None:
            return (502, {"detail": "No gateway attached to agent"})
        try:
            return client.get_reminder(reminder_id=reminder_id)
        except GatewayHttpError as exc:
            return self._gateway_http_error_tuple(exc)

    def gateway_put_reminder(
        self,
        agent_ref: str,
        reminder_id: str,
        payload: GatewayReminderPutV1,
    ) -> GatewayReminderV1 | tuple[int, dict[str, Any]]:
        """Proxy `PUT /v1/reminders/{reminder_id}` to the agent's gateway."""

        resolved = self._resolve_agent_or_error(agent_ref)
        if isinstance(resolved, tuple):
            return resolved
        client = self._gateway_client_for_agent(resolved)
        if client is None:
            return (502, {"detail": "No gateway attached to agent"})
        try:
            return client.put_reminder(reminder_id=reminder_id, payload=payload)
        except GatewayHttpError as exc:
            return self._gateway_http_error_tuple(exc)

    def gateway_delete_reminder(
        self,
        agent_ref: str,
        reminder_id: str,
    ) -> GatewayReminderDeleteResultV1 | tuple[int, dict[str, Any]]:
        """Proxy `DELETE /v1/reminders/{reminder_id}` to the agent's gateway."""

        resolved = self._resolve_agent_or_error(agent_ref)
        if isinstance(resolved, tuple):
            return resolved
        client = self._gateway_client_for_agent(resolved)
        if client is None:
            return (502, {"detail": "No gateway attached to agent"})
        try:
            return client.delete_reminder(reminder_id=reminder_id)
        except GatewayHttpError as exc:
            return self._gateway_http_error_tuple(exc)

    def online_binding_status(
        self, agent_ref: str
    ) -> OnlineBindingStatus | tuple[int, dict[str, Any]]:
        """Proxy authorized online binding status."""

        resolved = self._resolve_agent_or_error(agent_ref)
        if isinstance(resolved, tuple):
            return resolved
        client = self._gateway_client_for_agent(resolved)
        if client is None:
            return (502, {"detail": "No gateway attached to agent"})
        try:
            return client.online_binding_status()
        except GatewayHttpError as exc:
            return self._gateway_http_error_tuple(exc)

    def online_binding_attach(
        self, agent_ref: str, request: OnlineAttachRequest
    ) -> OnlineBindingStatus | tuple[int, dict[str, Any]]:
        """Proxy authorized online binding attach."""

        resolved = self._resolve_agent_or_error(agent_ref)
        if isinstance(resolved, tuple):
            return resolved
        client = self._gateway_client_for_agent(resolved)
        if client is None:
            return (502, {"detail": "No gateway attached to agent"})
        try:
            return client.attach_online_binding(request)
        except GatewayHttpError as exc:
            return self._online_control_error_tuple(exc)

    def online_binding_refresh(
        self, agent_ref: str, request: OnlineControlRequest
    ) -> OnlineBindingStatus | tuple[int, dict[str, Any]]:
        """Proxy authorized online binding refresh."""

        resolved = self._resolve_agent_or_error(agent_ref)
        if isinstance(resolved, tuple):
            return resolved
        client = self._gateway_client_for_agent(resolved)
        if client is None:
            return (502, {"detail": "No gateway attached to agent"})
        try:
            return client.refresh_online_binding(request)
        except GatewayHttpError as exc:
            return self._online_control_error_tuple(exc)

    def online_binding_reconnect(
        self, agent_ref: str, request: OnlineControlRequest
    ) -> OnlineBindingStatus | tuple[int, dict[str, Any]]:
        """Proxy authorized online binding reconnect."""

        resolved = self._resolve_agent_or_error(agent_ref)
        if isinstance(resolved, tuple):
            return resolved
        client = self._gateway_client_for_agent(resolved)
        if client is None:
            return (502, {"detail": "No gateway attached to agent"})
        try:
            return client.reconnect_online_binding(request)
        except GatewayHttpError as exc:
            return self._online_control_error_tuple(exc)

    def online_binding_detach(
        self, agent_ref: str, request: OnlineControlRequest
    ) -> OnlineBindingStatus | tuple[int, dict[str, Any]]:
        """Proxy authorized online binding detach."""

        resolved = self._resolve_agent_or_error(agent_ref)
        if isinstance(resolved, tuple):
            return resolved
        client = self._gateway_client_for_agent(resolved)
        if client is None:
            return (502, {"detail": "No gateway attached to agent"})
        try:
            return client.detach_online_binding(request)
        except GatewayHttpError as exc:
            return self._online_control_error_tuple(exc)

    def gateway_mail_status(
        self, agent_ref: str
    ) -> GatewayMailStatusV1 | tuple[int, dict[str, Any]]:
        """Proxy ``GET /v1/mail/status`` to the agent's gateway."""

        resolved = self._resolve_agent_or_error(agent_ref)
        if isinstance(resolved, tuple):
            return resolved
        client = self._gateway_client_for_agent(resolved)
        if client is None:
            return (502, {"detail": "No gateway attached to agent"})
        try:
            return client.mail_status()
        except GatewayHttpError as exc:
            return self._gateway_http_error_tuple(exc)

    def gateway_mail_list(
        self,
        agent_ref: str,
        payload: GatewayMailListRequestV1,
        *,
        channel: MailChannel,
    ) -> GatewayMailListResponseV1 | tuple[int, dict[str, Any]]:
        """Proxy ``POST /v1/mail/list`` to the agent's gateway."""

        resolved = self._resolve_agent_or_error(agent_ref)
        if isinstance(resolved, tuple):
            return resolved
        client = self._gateway_client_for_agent(resolved)
        if client is None:
            return (502, {"detail": "No gateway attached to agent"})
        try:
            return client.list_mail(payload, channel=channel)
        except GatewayHttpError as exc:
            return self._gateway_http_error_tuple(exc)

    def gateway_mail_peek(
        self,
        agent_ref: str,
        payload: GatewayMailMessageRequestV1,
        *,
        channel: MailChannel,
    ) -> GatewayMailMessageResponseV1 | tuple[int, dict[str, Any]]:
        """Proxy ``POST /v1/mail/peek`` to the agent's gateway."""

        resolved = self._resolve_agent_or_error(agent_ref)
        if isinstance(resolved, tuple):
            return resolved
        client = self._gateway_client_for_agent(resolved)
        if client is None:
            return (502, {"detail": "No gateway attached to agent"})
        try:
            return client.peek_mail(payload, channel=channel)
        except GatewayHttpError as exc:
            return self._gateway_http_error_tuple(exc)

    def gateway_mail_read(
        self,
        agent_ref: str,
        payload: GatewayMailMessageRequestV1,
        *,
        channel: MailChannel,
    ) -> GatewayMailMessageResponseV1 | tuple[int, dict[str, Any]]:
        """Proxy ``POST /v1/mail/read`` to the agent's gateway."""

        resolved = self._resolve_agent_or_error(agent_ref)
        if isinstance(resolved, tuple):
            return resolved
        client = self._gateway_client_for_agent(resolved)
        if client is None:
            return (502, {"detail": "No gateway attached to agent"})
        try:
            return client.read_mail(payload, channel=channel)
        except GatewayHttpError as exc:
            return self._gateway_http_error_tuple(exc)

    def gateway_mail_send(
        self,
        agent_ref: str,
        payload: GatewayMailSendRequestV1,
        *,
        channel: MailChannel,
    ) -> GatewayMailActionResponseV1 | tuple[int, dict[str, Any]]:
        """Proxy ``POST /v1/mail/send`` to the agent's gateway."""

        resolved = self._resolve_agent_or_error(agent_ref)
        if isinstance(resolved, tuple):
            return resolved
        client = self._gateway_client_for_agent(resolved)
        if client is None:
            return (502, {"detail": "No gateway attached to agent"})
        try:
            return client.send_mail(payload, channel=channel)
        except GatewayHttpError as exc:
            return self._gateway_http_error_tuple(exc)

    def gateway_mail_post(
        self,
        agent_ref: str,
        payload: GatewayMailPostRequestV1,
        *,
        channel: MailChannel,
    ) -> GatewayMailActionResponseV1 | tuple[int, dict[str, Any]]:
        """Proxy ``POST /v1/mail/post`` to the agent's gateway."""

        resolved = self._resolve_agent_or_error(agent_ref)
        if isinstance(resolved, tuple):
            return resolved
        client = self._gateway_client_for_agent(resolved)
        if client is None:
            return (502, {"detail": "No gateway attached to agent"})
        try:
            return client.post_mail(payload, channel=channel)
        except GatewayHttpError as exc:
            return self._gateway_http_error_tuple(exc)

    def gateway_mail_reply(
        self,
        agent_ref: str,
        payload: GatewayMailReplyRequestV1,
        *,
        channel: MailChannel,
    ) -> GatewayMailActionResponseV1 | tuple[int, dict[str, Any]]:
        """Proxy ``POST /v1/mail/reply`` to the agent's gateway."""

        resolved = self._resolve_agent_or_error(agent_ref)
        if isinstance(resolved, tuple):
            return resolved
        client = self._gateway_client_for_agent(resolved)
        if client is None:
            return (502, {"detail": "No gateway attached to agent"})
        try:
            return client.reply_mail(payload, channel=channel)
        except GatewayHttpError as exc:
            return self._gateway_http_error_tuple(exc)

    def gateway_mail_mark(
        self,
        agent_ref: str,
        payload: GatewayMailMarkRequestV1,
        *,
        channel: MailChannel,
    ) -> GatewayMailLifecycleResponseV1 | tuple[int, dict[str, Any]]:
        """Proxy ``POST /v1/mail/mark`` to the agent's gateway."""

        resolved = self._resolve_agent_or_error(agent_ref)
        if isinstance(resolved, tuple):
            return resolved
        client = self._gateway_client_for_agent(resolved)
        if client is None:
            return (502, {"detail": "No gateway attached to agent"})
        try:
            return client.mark_mail(payload, channel=channel)
        except GatewayHttpError as exc:
            return self._gateway_http_error_tuple(exc)

    def gateway_mail_move(
        self,
        agent_ref: str,
        payload: GatewayMailMoveRequestV1,
        *,
        channel: MailChannel,
    ) -> GatewayMailLifecycleResponseV1 | tuple[int, dict[str, Any]]:
        """Proxy ``POST /v1/mail/move`` to the agent's gateway."""

        resolved = self._resolve_agent_or_error(agent_ref)
        if isinstance(resolved, tuple):
            return resolved
        client = self._gateway_client_for_agent(resolved)
        if client is None:
            return (502, {"detail": "No gateway attached to agent"})
        try:
            return client.move_mail(payload, channel=channel)
        except GatewayHttpError as exc:
            return self._gateway_http_error_tuple(exc)

    def gateway_mail_archive(
        self,
        agent_ref: str,
        payload: GatewayMailArchiveRequestV1,
        *,
        channel: MailChannel,
    ) -> GatewayMailLifecycleResponseV1 | tuple[int, dict[str, Any]]:
        """Proxy ``POST /v1/mail/archive`` to the agent's gateway."""

        resolved = self._resolve_agent_or_error(agent_ref)
        if isinstance(resolved, tuple):
            return resolved
        client = self._gateway_client_for_agent(resolved)
        if client is None:
            return (502, {"detail": "No gateway attached to agent"})
        try:
            return client.archive_mail(payload, channel=channel)
        except GatewayHttpError as exc:
            return self._gateway_http_error_tuple(exc)

    # -- request submission (Tier 6) -------------------------------------------

    def submit_work_request(
        self, payload: GatewayRequestCreateV1
    ) -> PassiveWorkRequestReceipt | tuple[int, dict[str, Any]]:
        """Deliver an admitted work request on the verified detached owner route."""

        admission = CURRENT_ADMISSION.get()
        if (
            admission is None
            or admission.grant is None
            or WORK_REQUEST not in admission.grant.permissions
        ):
            raise GatewayAccessError(403, "insufficient_authority")
        if not isinstance(payload.payload, GatewayRequestPayloadSubmitWorkRequestV1):
            return (422, {"error_code": "invalid_operation"})
        target = admission.target
        tracked_id = target.tracked_agent_id
        if tracked_id is None:
            return (501, {"error_code": "unsupported_backend"})
        grant = admission.grant

        def fence(operation_id: str | None = None) -> None:
            """Verify detached selection, live generation, and current caller authority."""

            try:
                self.require_access_target_current(target)
                paths = gateway_paths_from_manifest_path(target.manifest_path)
                if paths is None:
                    raise GatewayAccessError(503, "policy_unavailable")
                try:
                    paths.current_instance_path.stat()
                except FileNotFoundError:
                    pass
                else:
                    raise GatewayAccessError(409, "gateway_attached")
                if not self.m_headless.access_body_is_live(
                    tracked_id, manifest_path=target.manifest_path
                ):
                    raise GatewayAccessError(503, "target_unavailable")
                if operation_id is not None:
                    target.policy.handoff(grant, operation_id=operation_id)
                elif not target.policy.revalidate(grant):
                    raise GatewayAccessError(409, "authorization_retired")
            except GatewayAccessError:
                raise
            except (OSError, RuntimeError, ValueError):
                raise GatewayAccessError(503, "policy_unavailable") from None

        try:
            with _gateway_lifecycle_lock(target.manifest_path, wait=False):
                fence()
                return self.m_headless.submit_work_request(
                    tracked_id,
                    render_work_request(payload.payload.text, actor=grant.actor),
                    authorize_handoff=fence,
                )
        except BlockingIOError:
            return (409, {"error_code": "gateway_transition"})
        except OSError:
            raise GatewayAccessError(503, "policy_unavailable") from None

    def submit_request(
        self, agent_ref: str, payload: PassivePromptRequest
    ) -> PassiveRequestAcceptedResponse | tuple[int, dict[str, Any]]:
        """Forward a prompt request to the agent's gateway.

        The passive server never does ``tmux send-keys`` directly; requests
        are always mediated by the gateway.  Returns 502 when no gateway is
        attached.
        """

        resolved = self._resolve_agent_or_error(agent_ref)
        if isinstance(resolved, tuple):
            return resolved
        client = self._gateway_client_for_agent(resolved)
        if client is None:
            return (502, {"detail": "No gateway attached to agent — cannot deliver request"})
        try:
            gw_payload = GatewayRequestCreateV1(
                kind="submit_prompt",
                payload=GatewayRequestPayloadSubmitPromptV1(prompt=payload.prompt),
            )
            gw_result = client.create_request(gw_payload)
            return PassiveRequestAcceptedResponse(
                request_id=gw_result.request_id,
                detail="Request forwarded to gateway",
            )
        except GatewayHttpError as exc:
            return self._gateway_http_error_tuple(exc)

    def interrupt_agent(
        self, agent_ref: str
    ) -> PassiveAgentActionResponse | tuple[int, dict[str, Any]]:
        """Interrupt an agent via gateway or, for managed headless, directly."""

        managed_tracked_agent_id, resolved, error = self._resolve_managed_headless_target(agent_ref)
        if error is not None:
            return error
        if managed_tracked_agent_id is not None:
            return self.m_headless.interrupt_managed(
                managed_tracked_agent_id, authorize_effect=self._claim_direct_effect
            )
        if resolved is None:
            return (404, {"detail": f"Agent not found: {agent_ref}"})

        agent_id = resolved.record.agent_id

        # Otherwise try gateway
        client = self._gateway_client_for_agent(resolved)
        if client is None:
            return (
                502,
                {
                    "detail": "No gateway attached and agent is not managed headless — cannot interrupt"
                },
            )
        try:
            gw_payload = GatewayRequestCreateV1(
                kind="interrupt",
                payload=GatewayRequestPayloadInterruptV1(),
            )
            client.create_request(gw_payload)
            return PassiveAgentActionResponse(
                agent_id=agent_id,
                detail="Interrupt forwarded to gateway",
            )
        except GatewayHttpError as exc:
            return self._gateway_http_error_tuple(exc)

    def stop_agent(self, agent_ref: str) -> PassiveAgentActionResponse | tuple[int, dict[str, Any]]:
        """Stop an agent by killing its tmux session and cleaning up.

        For managed headless agents, delegates full cleanup to
        ``HeadlessAgentService``.  For discovered-only agents, performs
        direct tmux kill and registry cleanup.
        """

        managed_tracked_agent_id, resolved, error = self._resolve_managed_headless_target(agent_ref)
        if error is not None:
            return error
        if managed_tracked_agent_id is not None:
            return self.m_headless.stop_managed(
                managed_tracked_agent_id, authorize_effect=self._claim_direct_effect
            )
        if resolved is None:
            return (404, {"detail": f"Agent not found: {agent_ref}"})

        agent_id = resolved.record.agent_id

        self._claim_direct_effect()

        # Discovered-only agent: kill tmux + clear registry
        tmux_session = resolved.record.terminal.session_name if resolved.record.terminal else None
        if tmux_session:
            try:
                with tmux_server_scope(resolved.record.terminal.socket_path):
                    kill_tmux_session(session_name=tmux_session)
            except Exception as exc:
                log.warning("Error killing tmux session %s: %s", tmux_session, exc)

        try:
            remove_live_agent_record(
                agent_id,
                generation_id=resolved.record.generation_id,
                env=self.m_config.registry_helper_env(),
            )
        except Exception as exc:
            log.warning("Error clearing registry for %s: %s", agent_id, exc)

        return PassiveAgentActionResponse(
            agent_id=agent_id,
            detail=f"Agent {agent_id} stopped",
        )

    # -- headless management (Tier 7) -----------------------------------------

    def launch_headless(
        self, payload: PassiveHeadlessLaunchRequest
    ) -> PassiveHeadlessLaunchResponse | tuple[int, dict[str, Any]]:
        """Delegate headless launch to ``HeadlessAgentService``."""

        return self.m_headless.launch(payload)

    def submit_turn(
        self, agent_ref: str, payload: PassiveHeadlessTurnRequest
    ) -> PassiveHeadlessTurnAcceptedResponse | tuple[int, dict[str, Any]]:
        """Submit a turn to a managed headless agent."""

        if native_command_candidate(payload.prompt) is not None:
            return (422, {"error_code": "unsupported_command"})
        managed_tracked_agent_id, _resolved, error = self._resolve_managed_headless_target(
            agent_ref
        )
        if error is not None:
            return error
        if managed_tracked_agent_id is None:
            return (400, {"detail": f"Agent {agent_ref} is not a managed headless agent"})

        admitted = CURRENT_ADMISSION.get()

        def authorize_effect() -> None:
            """Carry the original direct prompt decision into the native worker."""

            self._require_direct_access(handoff=True, admission=admitted)

        return self.m_headless.submit_turn(
            managed_tracked_agent_id,
            payload.prompt,
            chat_session=payload.chat_session,
            execution=payload.execution.to_model_config() if payload.execution else None,
            authorize_effect=authorize_effect,
        )

    def inspect_backing(
        self, agent_ref: str
    ) -> HoumaoManagedAgentDetailResponse | tuple[int, dict[str, Any]]:
        """Inspect the admitted backing controller without a gateway round-trip."""

        tracked_id = self._backing_tracked_id(agent_ref)
        if tracked_id is None:
            return (403, {"detail": "Backing service authority is required"})
        return self._managed_headless_detail_response(
            managed_tracked_agent_id=tracked_id, resolved=None
        )

    def dispatch_backing(
        self, agent_ref: str, payload: HoumaoManagedAgentGatewayInternalHeadlessPromptRequest
    ) -> CaoSuccessResponse | tuple[int, dict[str, Any]]:
        """Dispatch one operation through separate admitted backing authority."""

        tracked_id = self._backing_tracked_id(agent_ref)
        if tracked_id is None:
            return (403, {"detail": "Backing service authority is required"})
        return self.m_headless.dispatch_backing(tracked_id, payload)

    def interrupt_backing(
        self, agent_ref: str
    ) -> PassiveAgentActionResponse | tuple[int, dict[str, Any]]:
        """Interrupt through the exact controller admitted for backing service."""

        tracked_id = self._backing_tracked_id(agent_ref)
        if tracked_id is None:
            return (403, {"detail": "Backing service authority is required"})
        return self.m_headless.interrupt_managed(tracked_id)

    @staticmethod
    def _backing_tracked_id(agent_ref: str) -> str | None:
        """Select the managed id established by the service credential."""

        admission = CURRENT_ADMISSION.get()
        if (
            admission is not None
            and admission.grant is None
            and admission.target.tracked_agent_id == agent_ref
        ):
            return agent_ref
        return None

    def turn_status(
        self, agent_ref: str, turn_id: str
    ) -> PassiveHeadlessTurnStatusResponse | tuple[int, dict[str, Any]]:
        """Return status of a headless turn."""

        managed_tracked_agent_id, _resolved, error = self._resolve_managed_headless_target(
            agent_ref
        )
        if error is not None:
            return error
        if managed_tracked_agent_id is None:
            return (400, {"detail": f"Agent {agent_ref} is not a managed headless agent"})

        return self.m_headless.turn_status(managed_tracked_agent_id, turn_id)

    def turn_events(
        self, agent_ref: str, turn_id: str
    ) -> PassiveHeadlessTurnEventsResponse | tuple[int, dict[str, Any]]:
        """Return structured events from a headless turn."""

        managed_tracked_agent_id, _resolved, error = self._resolve_managed_headless_target(
            agent_ref
        )
        if error is not None:
            return error
        if managed_tracked_agent_id is None:
            return (400, {"detail": f"Agent {agent_ref} is not a managed headless agent"})

        return self.m_headless.turn_events(managed_tracked_agent_id, turn_id)

    def turn_artifact_text(
        self, agent_ref: str, turn_id: str, name: str
    ) -> str | tuple[int, dict[str, Any]]:
        """Return text content of a turn artifact (stdout / stderr)."""

        managed_tracked_agent_id, _resolved, error = self._resolve_managed_headless_target(
            agent_ref
        )
        if error is not None:
            return error
        if managed_tracked_agent_id is None:
            return (400, {"detail": f"Agent {agent_ref} is not a managed headless agent"})

        return self.m_headless.turn_artifact_text(managed_tracked_agent_id, turn_id, name)

    def managed_agent_state(
        self, agent_ref: str
    ) -> HoumaoManagedAgentStateResponse | tuple[int, dict[str, Any]]:
        """Return passive managed-agent summary state for pair consumers."""

        managed_tracked_agent_id, resolved, error = self._resolve_managed_headless_target(agent_ref)
        if error is not None:
            return error
        if managed_tracked_agent_id is not None:
            return self._managed_headless_state_response(
                managed_tracked_agent_id=managed_tracked_agent_id,
                resolved=resolved,
            )
        if resolved is None:
            return (404, {"detail": f"Agent not found: {agent_ref}"})
        if (
            resolved.record.mode in {"headless", "service"}
            or resolved.record.identity.backend in MANAGED_STRUCTURED_TUI_BACKENDS
        ):
            detail = self._managed_runtime_detail_response(resolved)
            return detail if isinstance(detail, tuple) else detail.summary_state
        if resolved.record.mode == "web":
            web_observer = self.m_observation.get_web_observer(resolved.record.agent_id)
            if web_observer is None:
                return (503, {"detail": "Native Web observation is not initialized"})
            try:
                return managed_web_state_from_observation(
                    agent=resolved,
                    state=web_observer.current_state().web,
                    gateway_summary=self._managed_gateway_summary(resolved),
                )
            except (RuntimeError, ValueError, OSError):
                return (503, {"detail": "Verified native Web authority is unavailable"})
        observer = self._verified_terminal_observer(resolved)
        if observer is None:
            return (503, {"detail": "Observer not yet initialized for this agent"})
        return self._managed_tui_summary(resolved, observer)

    def managed_agent_state_detail(
        self, agent_ref: str
    ) -> HoumaoManagedAgentDetailResponse | tuple[int, dict[str, Any]]:
        """Return passive managed-agent transport-specific detail for pair consumers."""

        managed_tracked_agent_id, resolved, error = self._resolve_managed_headless_target(agent_ref)
        if error is not None:
            return error
        if managed_tracked_agent_id is not None:
            return self._managed_headless_detail_response(
                managed_tracked_agent_id=managed_tracked_agent_id,
                resolved=resolved,
            )
        if resolved is None:
            return (404, {"detail": f"Agent not found: {agent_ref}"})
        if (
            resolved.record.mode in {"headless", "service"}
            or resolved.record.identity.backend in MANAGED_STRUCTURED_TUI_BACKENDS
        ):
            return self._managed_runtime_detail_response(resolved)
        if resolved.record.mode == "web":
            web_observer = self.m_observation.get_web_observer(resolved.record.agent_id)
            if web_observer is None:
                return (503, {"detail": "Native Web observation is not initialized"})
            try:
                return managed_web_detail_response(
                    agent=resolved,
                    state=web_observer.current_state().web,
                    gateway_summary=self._managed_gateway_summary(resolved),
                )
            except (RuntimeError, ValueError, OSError):
                return (503, {"detail": "Verified native Web authority is unavailable"})
        observer = self._verified_terminal_observer(resolved)
        if observer is None:
            return (503, {"detail": "Observer not yet initialized for this agent"})
        return managed_tui_detail_response(
            agent=resolved,
            detail_state=observer.current_detail(),
            summary_state=self._managed_tui_summary(resolved, observer),
        )

    def _verified_terminal_observer(self, agent: DiscoveredAgent) -> AgentTuiObserver | None:
        """Return the tracker only for the selected generation's actual TUI."""

        record = agent.record
        if (
            record.mode != "tui"
            or record.identity.backend in MANAGED_STRUCTURED_TUI_BACKENDS
            or not isinstance(record.native_surface, TerminalNativeSurfaceV1)
        ):
            return None
        return self.m_observation.get_observer(record.agent_id, generation_id=record.generation_id)

    def _managed_tui_summary(
        self, agent: DiscoveredAgent, observer: AgentTuiObserver
    ) -> HoumaoManagedAgentStateResponse:
        """Project a tracked sample with its real observation age."""

        return managed_tui_state_from_observation(
            agent=agent,
            state=observer.current_state(),
            gateway_summary=self._managed_gateway_summary(agent),
            mailbox_summary=mailbox_summary_from_registry_record(agent.record),
            observed_at_utc=observer.observed_at_utc,
            max_age_seconds=self.m_config.observation_poll_interval_seconds * 2,
        )

    def _managed_runtime_detail_response(
        self, agent: DiscoveredAgent
    ) -> HoumaoManagedAgentDetailResponse | tuple[int, dict[str, Any]]:
        """Read structured state from the same verified runtime as the manager."""

        record = agent.record
        try:
            require_registry_mode_authority(record)
            controller = resume_runtime_session(
                session_manifest_path=Path(record.runtime.manifest_path),
                read_only=True,
            )
            with controller.execution_scope():
                manifest = controller.require_managed_control_owner()
                if (
                    manifest.agent_id != record.agent_id
                    or manifest.registry_generation_id != record.generation_id
                    or manifest.runtime.execution_binding != record.execution_binding
                ):
                    raise SessionManifestError("Observation belongs to a different managed owner")
                identity = managed_identity_from_discovered_agent(agent).model_copy(
                    update={"runtime_session_id": manifest.runtime.session_id}
                )
                mailbox = mailbox_summary_from_registry_record(record)
                gateway = self._managed_gateway_summary(agent)
                if record.identity.backend in MANAGED_STRUCTURED_TUI_BACKENDS:
                    return managed_native_tui_detail_response(
                        identity=identity,
                        observation=controller.observe_managed_tui(),
                        mailbox_summary=mailbox,
                        gateway_summary=gateway,
                    )
                if record.mode == "service":
                    return managed_service_detail_response(
                        managed_service_state_from_observation(
                            identity=identity,
                            observation=controller.observe_managed_service(),
                            mailbox_summary=mailbox,
                            gateway_summary=gateway,
                        )
                    )
                latest = latest_headless_turn(
                    manifest_path=controller.manifest_path,
                    tool=manifest.tool,
                    backend=manifest.backend,
                )
                owner_available = tmux_session_exists(session_name=record.terminal.session_name)
                controller.require_managed_control_owner()
            summary = managed_runtime_headless_state_from_observation(
                identity=identity,
                latest_turn=latest,
                owner_available=owner_available,
                native_session_id=manifest.headless.session_id if manifest.headless else None,
                mailbox_summary=mailbox,
                gateway_summary=gateway,
            )
            return managed_runtime_headless_detail_response(
                summary_state=summary, latest_turn=latest
            )
        except (OSError, RuntimeError, ValueError):
            if record.identity.backend in MANAGED_STRUCTURED_TUI_BACKENDS:
                return managed_native_tui_detail_response(
                    identity=managed_identity_from_discovered_agent(agent).model_copy(
                        update={"runtime_session_id": None}
                    ),
                    observation=ManagedControlObservationV1(
                        source="tui_native",
                        freshness="unknown",
                        owner_available=False,
                        connection_ready=False,
                        can_accept_prompt_now=False,
                        terminal_attachment="unverified",
                    ),
                    mailbox_summary=mailbox_summary_from_registry_record(record),
                )
            return (503, {"detail": "Verified native runtime observation is unavailable"})

    def managed_agent_history(
        self, agent_ref: str, *, limit: int = 50
    ) -> HoumaoManagedAgentHistoryResponse | tuple[int, dict[str, Any]]:
        """Return passive managed-agent coarse history for pair consumers."""

        managed_tracked_agent_id, resolved, error = self._resolve_managed_headless_target(agent_ref)
        if error is not None:
            return error
        if managed_tracked_agent_id is not None:
            return self._managed_headless_history_response(
                managed_tracked_agent_id=managed_tracked_agent_id,
                limit=limit,
            )
        if resolved is None:
            return (404, {"detail": f"Agent not found: {agent_ref}"})
        if resolved.record.mode == "headless":
            return self._managed_headless_unavailable_error(agent_ref)
        if resolved.record.mode == "service":
            return (501, {"detail": "Native service history is unavailable"})
        if resolved.record.identity.backend in MANAGED_STRUCTURED_TUI_BACKENDS:
            return (501, {"detail": "Terminal tracker history is unsupported for Hermes TUI"})
        if resolved.record.mode == "web":
            web_observer = self.m_observation.get_web_observer(resolved.record.agent_id)
            if web_observer is None:
                return (503, {"detail": "Native Web observation is not initialized"})
            try:
                return managed_web_history_response(
                    agent=resolved,
                    history=web_observer.history(limit=limit).web,
                )
            except (RuntimeError, ValueError, OSError):
                return (503, {"detail": "Verified native Web authority is unavailable"})
        observer = self._verified_terminal_observer(resolved)
        if observer is None:
            return (503, {"detail": "Observer not yet initialized for this agent"})
        return managed_tui_history_from_observation(
            agent=resolved,
            history=observer.history(limit=limit),
        )

    def _resolve_managed_headless_target(
        self, agent_ref: str
    ) -> tuple[str | None, DiscoveredAgent | None, tuple[int, dict[str, Any]] | None]:
        """Resolve one agent reference onto the authoritative managed headless id."""

        admitted = CURRENT_ADMISSION.get()
        if admitted is not None:
            resolved = self._resolve_agent_or_error(agent_ref)
            self._require_direct_access()
            if admitted.target.tracked_agent_id is not None:
                return (
                    admitted.target.tracked_agent_id,
                    resolved if isinstance(resolved, DiscoveredAgent) else None,
                    None,
                )
            if isinstance(resolved, tuple):
                return (None, None, resolved)
            return (None, resolved, None)

        direct_matches = self.m_headless.resolve_managed_matches(agent_ref)
        if len(direct_matches) > 1:
            return (
                None,
                None,
                (409, {"detail": f"Ambiguous managed headless agent reference: {agent_ref}"}),
            )
        if len(direct_matches) == 1:
            return (direct_matches[0], None, None)

        resolved = self._resolve_agent_or_error(agent_ref)
        if isinstance(resolved, tuple):
            return (None, None, resolved)

        discovered_matches = self.m_headless.resolve_managed_matches(resolved.record.agent_id)
        if len(discovered_matches) > 1:
            return (
                None,
                None,
                (
                    409,
                    {
                        "detail": (
                            "Ambiguous managed headless agent reference after discovery "
                            f"resolution: {resolved.record.agent_id}"
                        )
                    },
                ),
            )
        if len(discovered_matches) == 1:
            return (discovered_matches[0], resolved, None)
        return (None, resolved, None)

    def _managed_headless_state_response(
        self,
        *,
        managed_tracked_agent_id: str,
        resolved: DiscoveredAgent | None,
    ) -> HoumaoManagedAgentStateResponse | tuple[int, dict[str, Any]]:
        """Return passive managed-headless summary state for one resolved tracked id."""

        control_state = self.m_headless.get_managed_control_state(managed_tracked_agent_id)
        if control_state is None:
            return (
                503,
                {
                    "detail": (
                        "Managed headless compatibility state is unavailable because the "
                        f"passive server has no live authority for `{managed_tracked_agent_id}`."
                    )
                },
            )
        mailbox_summary = (
            mailbox_summary_from_registry_record(resolved.record)
            if resolved is not None
            else mailbox_summary_from_headless_control_state(control_state)
        )
        return managed_headless_state_from_control_state(
            control_state=control_state,
            gateway_summary=self._managed_gateway_summary(resolved),
            mailbox_summary=mailbox_summary,
        )

    def _managed_headless_detail_response(
        self,
        *,
        managed_tracked_agent_id: str,
        resolved: DiscoveredAgent | None,
    ) -> HoumaoManagedAgentDetailResponse | tuple[int, dict[str, Any]]:
        """Return passive managed-headless detail for one resolved tracked id."""

        control_state = self.m_headless.get_managed_control_state(managed_tracked_agent_id)
        if control_state is None:
            return (
                503,
                {
                    "detail": (
                        "Managed headless compatibility detail is unavailable because the "
                        f"passive server has no live authority for `{managed_tracked_agent_id}`."
                    )
                },
            )
        mailbox_summary = (
            mailbox_summary_from_registry_record(resolved.record)
            if resolved is not None
            else mailbox_summary_from_headless_control_state(control_state)
        )
        summary_state = managed_headless_state_from_control_state(
            control_state=control_state,
            gateway_summary=self._managed_gateway_summary(resolved),
            mailbox_summary=mailbox_summary,
        )
        return managed_headless_detail_response(
            control_state=control_state,
            summary_state=summary_state,
        )

    def _managed_headless_history_response(
        self,
        *,
        managed_tracked_agent_id: str,
        limit: int,
    ) -> HoumaoManagedAgentHistoryResponse | tuple[int, dict[str, Any]]:
        """Return passive managed-headless coarse history for one resolved tracked id."""

        control_state = self.m_headless.get_managed_control_state(managed_tracked_agent_id)
        if control_state is None:
            return (
                503,
                {
                    "detail": (
                        "Managed headless compatibility history is unavailable because the "
                        f"passive server has no live authority for `{managed_tracked_agent_id}`."
                    )
                },
            )
        return managed_headless_history_from_turn_records(
            tracked_agent_id=managed_tracked_agent_id,
            turn_records=self.m_headless.m_store.list_turn_records(
                tracked_agent_id=managed_tracked_agent_id
            ),
            limit=limit,
        )

    def _managed_gateway_summary(
        self,
        agent: DiscoveredAgent | None,
    ) -> HoumaoManagedAgentGatewaySummaryView | None:
        """Return optional managed-agent gateway summary when a live gateway is reachable."""

        if agent is None:
            return None
        client = self._gateway_client_for_agent(agent)
        if client is None:
            return None
        try:
            return gateway_summary_from_status(client.status())
        except GatewayHttpError:
            return None

    @staticmethod
    def _managed_headless_unavailable_error(agent_ref: str) -> tuple[int, dict[str, Any]]:
        """Return one explicit error for headless agents not owned by this passive server."""

        return (
            503,
            {
                "detail": (
                    "Managed headless compatibility is unavailable because this headless agent "
                    "is not owned by the current passive server instance: "
                    f"{agent_ref}"
                )
            },
        )

    # -- agent TUI observation --------------------------------------------------

    def agent_state(
        self, agent_ref: str
    ) -> (
        AgentTuiStateResponse
        | AgentWebStateResponse
        | HoumaoManagedAgentStateResponse
        | tuple[int, dict[str, Any]]
    ):
        """Return compact observation from the recorded agent mode."""

        tracked_id, resolved, error = self._resolve_managed_headless_target(agent_ref)
        if error is not None:
            return error
        if tracked_id is not None:
            return self._managed_headless_state_response(
                managed_tracked_agent_id=tracked_id, resolved=resolved
            )
        if resolved is None:
            return (404, {"detail": f"Agent not found: {agent_ref}"})
        if (
            resolved.record.mode in {"headless", "service"}
            or resolved.record.identity.backend in MANAGED_STRUCTURED_TUI_BACKENDS
        ):
            detail = self._managed_runtime_detail_response(resolved)
            return detail if isinstance(detail, tuple) else detail.summary_state
        if resolved.record.mode == "web":
            web_observer = self.m_observation.get_web_observer(resolved.record.agent_id)
            if web_observer is None:
                return (503, {"detail": "Native Web observation is not initialized"})
            try:
                return web_observer.current_state()
            except (RuntimeError, ValueError, OSError):
                return (503, {"detail": "Verified native Web authority is unavailable"})
        observer = self._verified_terminal_observer(resolved)
        if observer is None:
            return (503, {"detail": "Observer not yet initialized for this agent"})
        return observer.current_state()

    def agent_state_detail(
        self, agent_ref: str
    ) -> AgentTuiDetailResponse | HoumaoManagedAgentDetailResponse | tuple[int, dict[str, Any]]:
        """Return mode-specific detail, preserving raw terminal diagnostics for TUI."""

        tracked_id, resolved, error = self._resolve_managed_headless_target(agent_ref)
        if error is not None:
            return error
        if tracked_id is not None:
            return self._managed_headless_detail_response(
                managed_tracked_agent_id=tracked_id, resolved=resolved
            )
        if resolved is None:
            return (404, {"detail": f"Agent not found: {agent_ref}"})
        if (
            resolved.record.mode in {"headless", "service"}
            or resolved.record.identity.backend in MANAGED_STRUCTURED_TUI_BACKENDS
        ):
            return self._managed_runtime_detail_response(resolved)
        if resolved.record.mode == "web":
            return self.managed_agent_state_detail(agent_ref)
        observer = self._verified_terminal_observer(resolved)
        if observer is None:
            return (503, {"detail": "Observer not yet initialized for this agent"})
        return observer.current_detail()

    def agent_history(
        self, agent_ref: str, limit: int = 50
    ) -> AgentTuiHistoryResponse | AgentWebHistoryResponse | tuple[int, dict[str, Any]]:
        """Return recent state transitions for an agent."""

        resolved = self._resolve_agent_or_error(agent_ref)
        if isinstance(resolved, tuple):
            return resolved
        self._require_direct_access()
        if resolved.record.identity.backend in MANAGED_STRUCTURED_TUI_BACKENDS:
            return (501, {"detail": "Terminal tracker history is unsupported for Hermes TUI"})
        if resolved.record.mode == "web":
            web_observer = self.m_observation.get_web_observer(resolved.record.agent_id)
            if web_observer is None:
                return (503, {"detail": "Native Web observation is not initialized"})
            try:
                return web_observer.history(limit=limit)
            except (RuntimeError, ValueError, OSError):
                return (503, {"detail": "Verified native Web authority is unavailable"})
        observer = self._verified_terminal_observer(resolved)
        if observer is None:
            return (503, {"detail": "Observer not yet initialized for this agent"})
        return observer.history(limit=limit)

    def request_shutdown(self) -> None:
        """Schedule a deferred SIGTERM to allow the response to flush."""

        import signal
        import threading

        def _deferred() -> None:
            import time

            time.sleep(0.1)
            os.kill(os.getpid(), signal.SIGTERM)

        threading.Thread(target=_deferred, daemon=True).start()

    # -- internal -------------------------------------------------------------

    def _online_control_error_tuple(self, exc: GatewayHttpError) -> tuple[int, dict[str, Any]]:
        """Relay recognized online control errors from the selected agent gateway."""
        status = exc.status_code
        if status is not None and status in {400, 409, 502}:
            try:
                detail = OnlineControlFailure.model_validate_json(exc.detail)
            except ValueError:
                pass
            else:
                return status, {"detail": detail.model_dump(mode="json")}
        return self._gateway_http_error_tuple(exc)

    def _gateway_http_error_tuple(self, exc: GatewayHttpError) -> tuple[int, dict[str, Any]]:
        """Project one gateway HTTP error into a passive proxy response tuple."""

        if exc.status_code == 401:
            return (401, {"detail": "Caller proof is required or invalid"})
        if exc.status_code == 403:
            return (403, {"detail": "Caller has insufficient authority"})
        if exc.status_code == 503:
            try:
                detail = json.loads(exc.detail)
            except json.JSONDecodeError:
                detail = None
            if isinstance(detail, dict) and detail.get("error_code") == "policy_unavailable":
                return (503, {"detail": "Target access policy is unavailable"})
        return (502, {"detail": "Agent gateway request failed"})

    def _gateway_proxy(
        self,
        agent_ref: str,
        callback: Callable[[GatewayClient], _GatewayProxyT],
    ) -> _GatewayProxyT | tuple[int, dict[str, Any]]:
        """Invoke one gateway client call for a resolved passive-server agent."""

        resolved = self._resolve_agent_or_error(agent_ref)
        if isinstance(resolved, tuple):
            return resolved
        client = self._gateway_client_for_agent(resolved)
        if client is None:
            return (502, {"detail": "No gateway attached to agent"})
        try:
            return callback(client)
        except GatewayHttpError as exc:
            return self._gateway_http_error_tuple(exc)

    def _write_current_instance(self) -> None:
        """Persist the current-instance payload to disk."""

        payload = self.current_instance().model_dump(mode="json")
        self.m_config.current_instance_path.write_text(
            json.dumps(payload, indent=2) + "\n", encoding="utf-8"
        )
