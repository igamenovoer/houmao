"""Compatibility projections from passive-server state into pair-managed models."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal

from houmao.agents.mailbox_runtime_support import safe_registry_mailboxes_projection
from houmao.agents.realm_controller.backends.tmux_runtime import HEADLESS_AGENT_WINDOW_NAME
from houmao.agents.realm_controller.gateway_models import GatewayStatusV1
from houmao.agents.realm_controller.gateway_models import (
    GatewayWebControlStateV1,
    GatewayWebHistoryV1,
)
from houmao.agents.realm_controller.headless_snapshots import headless_control_observation
from houmao.agents.realm_controller.managed_control import (
    ManagedControlCapabilitiesV1,
    ManagedControlObservationV1,
    ManagedControlOutcome,
    managed_control_capabilities,
)
from houmao.agents.realm_controller.registry_models import ManagedAgentRegistryRecordV3
from houmao.agents.realm_controller.native_surface import (
    TerminalNativeSurfaceV1,
    WebNativeSurfaceV1,
)
from houmao.agents.realm_controller.web_observation import web_state_is_fresh
from houmao.passive_server.discovery import DiscoveredAgent
from houmao.passive_server.headless import PassiveManagedHeadlessControlState
from houmao.passive_server.models import (
    AgentTuiDetailResponse,
    AgentTuiHistoryResponse,
    AgentTuiStateResponse,
    DiscoveredAgentSummary,
)
from houmao.server.managed_agents import ManagedHeadlessTurnRecord
from houmao.server.models import (
    HoumaoErrorDetail,
    HoumaoManagedAgentDetailResponse,
    HoumaoManagedAgentGatewaySummaryView,
    HoumaoManagedAgentHeadlessDetailView,
    HoumaoManagedAgentHistoryEntry,
    HoumaoManagedAgentHistoryResponse,
    HoumaoManagedAgentIdentity,
    HoumaoManagedAgentLastTurnView,
    HoumaoManagedAgentMailboxSummaryView,
    HoumaoManagedAgentNativeTuiDetailView,
    HoumaoManagedAgentServiceDetailView,
    HoumaoManagedAgentStateResponse,
    HoumaoManagedAgentTurnView,
    HoumaoManagedAgentTuiDetailView,
    HoumaoManagedAgentWebDetailView,
    ManagedAgentAvailability,
    ManagedAgentLastTurnResult,
)
from houmao.shared_tui_tracking.models import TurnPhase

if TYPE_CHECKING:
    from houmao.agents.realm_controller.headless_snapshots import HeadlessTurnSnapshot

_RESULT_FROM_NATIVE_OUTCOME: dict[ManagedControlOutcome, ManagedAgentLastTurnResult] = {
    "completed": "success",
    "failed": "known_failure",
    "interrupted": "interrupted",
    "uncertain": "unknown",
}
_OUTCOME_FROM_PASSIVE_STATUS: dict[str, ManagedControlOutcome] = {
    "completed": "completed",
    "failed": "failed",
    "interrupted": "interrupted",
    "unknown": "uncertain",
}


def managed_identity_from_discovered_summary(
    summary: DiscoveredAgentSummary,
) -> HoumaoManagedAgentIdentity:
    """Project one discovery summary into the shared managed-agent identity model."""

    transport = summary.mode
    terminal = isinstance(summary.native_surface, TerminalNativeSurfaceV1)
    tmux_window_name = (
        HEADLESS_AGENT_WINDOW_NAME
        if transport == "headless" or summary.backend == "local_interactive"
        else None
    )
    return HoumaoManagedAgentIdentity(
        tracked_agent_id=summary.agent_id,
        transport=transport,
        native_surface=summary.native_surface,
        mode=summary.mode,
        backend=summary.backend,
        tool=summary.tool,
        session_name=summary.tmux_session_name if terminal else None,
        terminal_id=summary.agent_id if terminal else None,
        runtime_session_id=summary.agent_id,
        tmux_session_name=summary.tmux_session_name,
        tmux_window_name=tmux_window_name,
        manifest_path=summary.manifest_path,
        session_root=summary.session_root,
        agent_name=summary.agent_name,
        agent_id=summary.agent_id,
    )


def managed_identity_from_discovered_agent(agent: DiscoveredAgent) -> HoumaoManagedAgentIdentity:
    """Project one full discovered agent into the shared managed-agent identity model."""

    return managed_identity_from_discovered_summary(agent.summary)


def _capabilities(
    identity: HoumaoManagedAgentIdentity,
) -> ManagedControlCapabilitiesV1 | None:
    """Report capabilities only for a recorded owner mode and backend."""

    if identity.mode is None or identity.backend is None:
        return None
    return managed_control_capabilities(
        tool=identity.tool,
        mode=identity.mode,
        backend=identity.backend,
        native_surface=identity.native_surface,
    )


def managed_service_state_from_observation(
    *,
    identity: HoumaoManagedAgentIdentity,
    observation: ManagedControlObservationV1,
    mailbox_summary: HoumaoManagedAgentMailboxSummaryView | None = None,
    gateway_summary: HoumaoManagedAgentGatewaySummaryView | None = None,
) -> HoumaoManagedAgentStateResponse:
    """Project attributed service evidence without interpreting its supervisor pane."""

    available = (
        observation.freshness == "current"
        and observation.owner_available is True
        and observation.connection_ready is True
    )
    phase: TurnPhase = "unknown"
    if available:
        if observation.active_request_id is not None or observation.active_turn_id is not None:
            phase = "active"
        elif observation.can_accept_prompt_now is True:
            phase = "ready"
    diagnostics = []
    if not available:
        diagnostics.append(
            HoumaoErrorDetail(
                kind="service_connection_unavailable",
                message="Verified native service connection is unavailable.",
            )
        )
    return HoumaoManagedAgentStateResponse(
        tracked_agent_id=identity.tracked_agent_id,
        identity=identity,
        availability="available" if available else "unavailable",
        turn=HoumaoManagedAgentTurnView(
            phase=phase, active_turn_id=observation.active_turn_id if available else None
        ),
        last_turn=HoumaoManagedAgentLastTurnView(
            result=_RESULT_FROM_NATIVE_OUTCOME.get(observation.last_outcome, "unknown")
            if observation.last_outcome is not None
            else "unknown",
            turn_id=observation.last_turn_id,
        ),
        capabilities=_capabilities(identity),
        control=observation,
        diagnostics=diagnostics,
        mailboxes=mailbox_summary,
        gateway=gateway_summary,
    )


def managed_service_detail_response(
    summary_state: HoumaoManagedAgentStateResponse,
) -> HoumaoManagedAgentDetailResponse:
    """Return the service-specific detail with its verified evidence."""

    assert summary_state.control is not None
    return HoumaoManagedAgentDetailResponse(
        tracked_agent_id=summary_state.tracked_agent_id,
        identity=summary_state.identity,
        summary_state=summary_state,
        detail=HoumaoManagedAgentServiceDetailView(state=summary_state.control),
    )


def managed_native_tui_detail_response(
    *,
    identity: HoumaoManagedAgentIdentity,
    observation: ManagedControlObservationV1,
    mailbox_summary: HoumaoManagedAgentMailboxSummaryView | None = None,
    gateway_summary: HoumaoManagedAgentGatewaySummaryView | None = None,
) -> HoumaoManagedAgentDetailResponse:
    """Project structured readiness and keep the terminal handoff under the saved identity."""

    available = (
        observation.freshness == "current"
        and observation.owner_available is True
        and observation.connection_ready is True
    )
    phase: TurnPhase = "unknown"
    if available:
        if (
            observation.active_turn_id is not None
            or observation.native_admission_state == "running"
        ):
            phase = "active"
        elif observation.can_accept_prompt_now is True:
            phase = "ready"
    summary = HoumaoManagedAgentStateResponse(
        tracked_agent_id=identity.tracked_agent_id,
        identity=identity,
        availability="available" if available else "unavailable",
        turn=HoumaoManagedAgentTurnView(
            phase=phase, active_turn_id=observation.active_turn_id if available else None
        ),
        last_turn=HoumaoManagedAgentLastTurnView(
            result=_RESULT_FROM_NATIVE_OUTCOME.get(observation.last_outcome, "unknown")
            if observation.last_outcome is not None
            else "unknown",
            turn_id=observation.last_turn_id,
        ),
        capabilities=_capabilities(identity),
        control=observation,
        diagnostics=[]
        if available
        else [
            HoumaoErrorDetail(
                kind="native_tui_unavailable",
                message="Verified native terminal control is unavailable.",
            )
        ],
        mailboxes=mailbox_summary,
        gateway=gateway_summary,
    )
    return HoumaoManagedAgentDetailResponse(
        tracked_agent_id=identity.tracked_agent_id,
        identity=identity,
        summary_state=summary,
        detail=HoumaoManagedAgentNativeTuiDetailView(state=observation),
    )


def managed_runtime_headless_state_from_observation(
    *,
    identity: HoumaoManagedAgentIdentity,
    latest_turn: HeadlessTurnSnapshot | None,
    owner_available: bool | None,
    native_session_id: str | None = None,
    mailbox_summary: HoumaoManagedAgentMailboxSummaryView | None = None,
    gateway_summary: HoumaoManagedAgentGatewaySummaryView | None = None,
) -> HoumaoManagedAgentStateResponse:
    """Project one-shot work from native attempt state and durable exit evidence."""

    control = headless_control_observation(
        latest_turn, owner_available=owner_available, native_session_id=native_session_id
    )
    active_id = control.active_turn_id
    outcome = control.last_outcome
    settled_turn = latest_turn if outcome is not None else None
    diagnostics = []
    if outcome == "uncertain":
        diagnostics.append(
            HoumaoErrorDetail(
                kind="headless_outcome_uncertain",
                message="The last recorded worker has no verified terminal evidence.",
            )
        )
    return HoumaoManagedAgentStateResponse(
        tracked_agent_id=identity.tracked_agent_id,
        identity=identity,
        availability="available" if owner_available else "unavailable",
        turn=HoumaoManagedAgentTurnView(
            phase="active"
            if active_id is not None
            else "ready"
            if control.can_accept_prompt_now
            else "unknown",
            active_turn_id=active_id,
        ),
        last_turn=HoumaoManagedAgentLastTurnView(
            result=_RESULT_FROM_NATIVE_OUTCOME[outcome] if outcome is not None else "none",
            turn_id=control.last_turn_id,
            turn_index=settled_turn.turn_index if settled_turn is not None else None,
            updated_at_utc=settled_turn.completed_at_utc if settled_turn is not None else None,
        ),
        capabilities=_capabilities(identity),
        control=control,
        diagnostics=diagnostics,
        mailboxes=mailbox_summary,
        gateway=gateway_summary,
    )


def managed_runtime_headless_detail_response(
    *,
    summary_state: HoumaoManagedAgentStateResponse,
    latest_turn: HeadlessTurnSnapshot | None,
) -> HoumaoManagedAgentDetailResponse:
    """Preserve the relevant owner-native evidence for richer one-shot detail."""

    control = summary_state.control
    assert control is not None
    active = control.active_turn_id is not None
    settled_turn = latest_turn if not active else None
    last_status = "unknown" if control.last_outcome == "uncertain" else control.last_outcome
    detail = HoumaoManagedAgentHeadlessDetailView(
        runtime_resumable=True,
        tmux_session_live=control.owner_available,
        can_accept_prompt_now=control.can_accept_prompt_now,
        interruptible=active,
        turn=summary_state.turn,
        last_turn=summary_state.last_turn,
        active_turn_started_at_utc=latest_turn.started_at_utc
        if active and latest_turn is not None
        else None,
        last_turn_status=last_status,
        last_turn_started_at_utc=settled_turn.started_at_utc if settled_turn is not None else None,
        last_turn_completed_at_utc=settled_turn.completed_at_utc
        if settled_turn is not None
        else None,
        last_turn_returncode=settled_turn.returncode if settled_turn is not None else None,
        last_turn_history_summary=settled_turn.history_summary
        if settled_turn is not None
        else None,
        last_turn_error=settled_turn.error if settled_turn is not None else None,
        last_turn_completion_source=settled_turn.completion_source
        if settled_turn is not None
        else None,
        mailboxes=summary_state.mailboxes,
        gateway=summary_state.gateway,
        diagnostics=summary_state.diagnostics,
    )
    return HoumaoManagedAgentDetailResponse(
        tracked_agent_id=summary_state.tracked_agent_id,
        identity=summary_state.identity,
        summary_state=summary_state,
        detail=detail,
    )


def managed_web_state_from_observation(
    *,
    agent: DiscoveredAgent,
    state: GatewayWebControlStateV1,
    gateway_summary: HoumaoManagedAgentGatewaySummaryView | None = None,
) -> HoumaoManagedAgentStateResponse:
    """Project native facts without terminal readiness or caller ownership guesses."""

    return managed_web_state_from_native(
        identity=managed_identity_from_discovered_agent(agent),
        state=state,
        mailbox_summary=mailbox_summary_from_registry_record(agent.record),
        gateway_summary=gateway_summary,
    )


def managed_web_state_from_native(
    *,
    identity: HoumaoManagedAgentIdentity,
    state: GatewayWebControlStateV1,
    mailbox_summary: HoumaoManagedAgentMailboxSummaryView | None = None,
    gateway_summary: HoumaoManagedAgentGatewaySummaryView | None = None,
) -> HoumaoManagedAgentStateResponse:
    """Share native Web projection between direct manager and passive inspection."""

    identity = identity.model_copy(
        update={
            "runtime_session_id": state.identity.runtime_session_id,
            "native_surface": WebNativeSurfaceV1(
                origin=state.origin, native_session_id=state.identity.native_session_id
            ),
        }
    )
    phase: TurnPhase = "unknown"
    if state.availability == "available":
        phase = "blocked" if state.interaction_waits else "active" if state.active_turn else "ready"
    result: ManagedAgentLastTurnResult = "none"
    if state.last_turn is not None:
        results: dict[str, ManagedAgentLastTurnResult] = {
            "success": "success",
            "completed": "success",
            "end_turn": "success",
            "interrupted": "interrupted",
            "cancelled": "interrupted",
            "failed": "known_failure",
            "error": "known_failure",
        }
        result = results.get(state.last_turn.result, "unknown")
    available = state.availability == "available"
    fresh = available and web_state_is_fresh(state)
    active_turn_id = (
        f"native-turn:{state.identity.native_session_id}:{state.active_turn.turn}"
        if state.active_turn is not None
        else None
    )
    last_turn_id = (
        f"native-turn:{state.identity.native_session_id}:{state.last_turn.turn}"
        if state.last_turn is not None
        else None
    )
    outcome: ManagedControlOutcome | None = None
    if state.last_turn is not None:
        outcome_by_result: dict[ManagedAgentLastTurnResult, ManagedControlOutcome] = {
            "success": "completed",
            "interrupted": "interrupted",
            "known_failure": "failed",
        }
        outcome = outcome_by_result.get(result, "uncertain")
    return HoumaoManagedAgentStateResponse(
        tracked_agent_id=identity.tracked_agent_id,
        identity=identity,
        availability="available" if available else "unavailable",
        turn=HoumaoManagedAgentTurnView(
            phase=phase,
            active_turn_id=active_turn_id,
        ),
        last_turn=HoumaoManagedAgentLastTurnView(
            result=result,
            turn_id=last_turn_id,
            turn_index=state.last_turn.turn if state.last_turn else None,
            updated_at_utc=state.observed_at_utc if state.last_turn else None,
        ),
        capabilities=_capabilities(identity),
        control=ManagedControlObservationV1(
            source="web_native",
            freshness="current" if fresh else "stale" if available else "unknown",
            observed_at_utc=state.observed_at_utc if available else None,
            owner_available=state.host_process_alive,
            connection_ready=state.control_available,
            can_accept_prompt_now=fresh and state.control_available and state.can_accept_prompt_now,
            native_session_id=state.identity.native_session_id,
            active_turn_id=active_turn_id,
            last_turn_id=last_turn_id,
            last_outcome=outcome,
        ),
        diagnostics=[
            HoumaoErrorDetail(kind="web_unavailable", message=message)
            for message in state.diagnostics
        ],
        mailboxes=mailbox_summary,
        gateway=gateway_summary,
        web=state,
    )


def managed_web_detail_response(
    *,
    agent: DiscoveredAgent,
    state: GatewayWebControlStateV1,
    gateway_summary: HoumaoManagedAgentGatewaySummaryView | None = None,
) -> HoumaoManagedAgentDetailResponse:
    """Return the canonical native Web detail with shared identity and bindings."""

    summary = managed_web_state_from_observation(
        agent=agent, state=state, gateway_summary=gateway_summary
    )
    return HoumaoManagedAgentDetailResponse(
        tracked_agent_id=summary.tracked_agent_id,
        identity=summary.identity,
        summary_state=summary,
        detail=HoumaoManagedAgentWebDetailView(state=state),
    )


def managed_web_history_response(
    *,
    agent: DiscoveredAgent,
    history: GatewayWebHistoryV1,
) -> HoumaoManagedAgentHistoryResponse:
    """Preserve native turn/input and incarnation metadata in bounded history."""

    return HoumaoManagedAgentHistoryResponse(tracked_agent_id=agent.record.agent_id, web=history)


def mailbox_summary_from_registry_record(
    record: ManagedAgentRegistryRecordV3,
) -> HoumaoManagedAgentMailboxSummaryView | None:
    """Return optional redacted mailbox posture from one registry record."""

    return HoumaoManagedAgentMailboxSummaryView(
        **record.mailboxes.model_dump(mode="json"),
        canonical_mail_identity=record.canonical_mail_identity,
    )


def mailbox_summary_from_headless_control_state(
    control_state: PassiveManagedHeadlessControlState,
) -> HoumaoManagedAgentMailboxSummaryView | None:
    """Return optional mailbox posture from one live headless control state."""

    controller = control_state.controller
    if controller is None:
        return None
    mailboxes = controller.launch_plan.mailboxes
    return HoumaoManagedAgentMailboxSummaryView(
        **safe_registry_mailboxes_projection(mailboxes),
        canonical_mail_identity=mailboxes.canonical_mail_identity,
    )


def gateway_summary_from_status(status: GatewayStatusV1) -> HoumaoManagedAgentGatewaySummaryView:
    """Project one gateway status payload into the shared managed-agent summary view."""

    return HoumaoManagedAgentGatewaySummaryView(
        gateway_health=status.gateway_health,
        managed_agent_connectivity=status.managed_agent_connectivity,
        managed_agent_recovery=status.managed_agent_recovery,
        request_admission=status.request_admission,
        active_execution=status.active_execution,
        queue_depth=status.queue_depth,
        gateway_host=status.gateway_host,
        gateway_port=status.gateway_port,
    )


def managed_tui_state_from_observation(
    *,
    agent: DiscoveredAgent,
    state: AgentTuiStateResponse,
    gateway_summary: HoumaoManagedAgentGatewaySummaryView | None,
    mailbox_summary: HoumaoManagedAgentMailboxSummaryView | None,
    observed_at_utc: datetime | None,
    max_age_seconds: float,
) -> HoumaoManagedAgentStateResponse:
    """Project one passive TUI observation sample into managed-agent summary state."""

    identity = managed_identity_from_discovered_agent(agent)
    freshness: Literal["current", "stale", "unknown"] = "unknown"
    if observed_at_utc is not None:
        age_seconds = (datetime.now(UTC) - observed_at_utc).total_seconds()
        freshness = "current" if 0 <= age_seconds <= max_age_seconds else "stale"
    return HoumaoManagedAgentStateResponse(
        tracked_agent_id=identity.tracked_agent_id,
        identity=identity,
        availability=_availability_from_tui_state(state),
        turn=HoumaoManagedAgentTurnView(
            phase=state.turn.phase,
            active_turn_id=(
                f"tui-anchor:{identity.tracked_agent_id}" if state.turn.phase == "active" else None
            ),
        ),
        last_turn=HoumaoManagedAgentLastTurnView(
            result=state.last_turn.result,
            turn_id=None,
            turn_index=None,
            updated_at_utc=state.last_turn.updated_at_utc,
        ),
        capabilities=_capabilities(identity),
        control=ManagedControlObservationV1(
            source="terminal_tracker",
            freshness=freshness,
            observed_at_utc=observed_at_utc.isoformat() if observed_at_utc is not None else None,
            owner_available=state.diagnostics.transport_state == "tmux_up",
            connection_ready=state.diagnostics.availability == "available",
            can_accept_prompt_now=(
                freshness == "current"
                and state.diagnostics.availability == "available"
                and state.turn.phase == "ready"
                and state.surface.accepting_input == "yes"
                and state.surface.editing_input == "no"
                and state.surface.ready_posture == "yes"
                and state.surface.pending_input == "no"
                and state.stability.stable
            ),
        ),
        diagnostics=_tracked_errors_from_tui_state(state),
        mailboxes=mailbox_summary,
        gateway=gateway_summary,
    )


def managed_tui_detail_response(
    *,
    agent: DiscoveredAgent,
    detail_state: AgentTuiDetailResponse,
    summary_state: HoumaoManagedAgentStateResponse,
) -> HoumaoManagedAgentDetailResponse:
    """Project one passive TUI detail sample into managed-agent detail payload."""

    terminal_ref = summary_state.identity.terminal_id or agent.record.agent_id
    detail = HoumaoManagedAgentTuiDetailView(
        terminal_id=terminal_ref,
        canonical_terminal_state_route=f"/houmao/agents/{agent.record.agent_id}/state/detail",
        canonical_terminal_history_route=f"/houmao/agents/{agent.record.agent_id}/history",
        diagnostics=detail_state.diagnostics,
        probe_snapshot=detail_state.probe_snapshot,
        parsed_surface=detail_state.parsed_surface,
        surface=detail_state.surface,
        stability=detail_state.stability,
    )
    return HoumaoManagedAgentDetailResponse(
        tracked_agent_id=summary_state.tracked_agent_id,
        identity=summary_state.identity,
        summary_state=summary_state,
        detail=detail,
    )


def managed_tui_history_from_observation(
    *,
    agent: DiscoveredAgent,
    history: AgentTuiHistoryResponse,
) -> HoumaoManagedAgentHistoryResponse:
    """Project passive TUI history entries into the shared managed-agent history model."""

    identity = managed_identity_from_discovered_agent(agent)
    return HoumaoManagedAgentHistoryResponse(
        tracked_agent_id=identity.tracked_agent_id,
        entries=[
            HoumaoManagedAgentHistoryEntry(
                recorded_at_utc=entry.recorded_at_utc,
                summary=entry.summary,
                availability=_availability_from_tui_transition(entry),
                turn_phase=entry.turn_phase,
                last_turn_result=entry.last_turn_result,
                turn_id=None,
            )
            for entry in history.entries
        ],
    )


def managed_identity_from_headless_control_state(
    control_state: PassiveManagedHeadlessControlState,
) -> HoumaoManagedAgentIdentity:
    """Project one passive managed-headless control state into the shared identity model."""

    authority = control_state.authority
    return HoumaoManagedAgentIdentity(
        tracked_agent_id=authority.tracked_agent_id,
        transport="headless",
        mode="headless",
        backend=authority.backend,
        tool=authority.tool,
        session_name=None,
        terminal_id=None,
        runtime_session_id=authority.tracked_agent_id,
        tmux_session_name=authority.tmux_session_name,
        tmux_window_name=HEADLESS_AGENT_WINDOW_NAME,
        manifest_path=authority.manifest_path,
        session_root=authority.session_root,
        agent_name=authority.agent_name,
        agent_id=authority.agent_id,
    )


def managed_headless_state_from_control_state(
    *,
    control_state: PassiveManagedHeadlessControlState,
    gateway_summary: HoumaoManagedAgentGatewaySummaryView | None,
    mailbox_summary: HoumaoManagedAgentMailboxSummaryView | None,
) -> HoumaoManagedAgentStateResponse:
    """Project passive managed-headless live state into the shared summary model."""

    identity = managed_identity_from_headless_control_state(control_state)
    diagnostics = _headless_diagnostics_from_control_state(control_state)
    availability = _headless_availability_from_control_state(control_state)
    active_turn = control_state.active_turn
    latest_turn = control_state.latest_turn

    unresolved = latest_turn is not None and latest_turn.status == "unknown"
    if unresolved:
        turn = HoumaoManagedAgentTurnView(phase="unknown")
    elif active_turn is not None:
        turn = HoumaoManagedAgentTurnView(phase="active", active_turn_id=active_turn.turn_id)
    else:
        turn = HoumaoManagedAgentTurnView(
            phase="ready" if availability == "available" else "unknown",
            active_turn_id=None,
        )

    last_turn_result: ManagedAgentLastTurnResult = "none"
    last_turn_id: str | None = None
    last_turn_index: int | None = None
    updated_at_utc: str | None = None
    if latest_turn is not None:
        last_turn_result = (
            "unknown" if unresolved else _last_turn_result_from_headless_status(latest_turn.status)
        )
        last_turn_id = latest_turn.turn_id
        last_turn_index = latest_turn.turn_index
        updated_at_utc = latest_turn.completed_at_utc or latest_turn.started_at_utc
    elif active_turn is not None:
        updated_at_utc = active_turn.started_at_utc

    return HoumaoManagedAgentStateResponse(
        tracked_agent_id=identity.tracked_agent_id,
        identity=identity,
        availability=availability,
        turn=turn,
        last_turn=HoumaoManagedAgentLastTurnView(
            result=last_turn_result,
            turn_id=last_turn_id,
            turn_index=last_turn_index,
            updated_at_utc=updated_at_utc,
        ),
        capabilities=_capabilities(identity),
        control=ManagedControlObservationV1(
            source="headless_artifacts",
            freshness="unknown" if unresolved else "current",
            observed_at_utc=datetime.now(UTC).isoformat(),
            owner_available=control_state.tmux_session_live,
            connection_ready=control_state.runtime_resumable,
            can_accept_prompt_now=control_state.can_accept_prompt_now,
            active_request_id=active_turn.turn_id if active_turn is not None else None,
            active_turn_id=(
                active_turn.turn_id if active_turn is not None and not unresolved else None
            ),
            last_turn_id=last_turn_id,
            last_outcome=(
                _OUTCOME_FROM_PASSIVE_STATUS.get(latest_turn.status)
                if latest_turn is not None
                else None
            ),
        ),
        diagnostics=diagnostics,
        mailboxes=mailbox_summary,
        gateway=gateway_summary,
    )


def managed_headless_detail_response(
    *,
    control_state: PassiveManagedHeadlessControlState,
    summary_state: HoumaoManagedAgentStateResponse,
) -> HoumaoManagedAgentDetailResponse:
    """Project passive managed-headless live detail into the shared detail response."""

    active_turn = control_state.active_turn
    latest_turn = control_state.latest_turn
    detail = HoumaoManagedAgentHeadlessDetailView(
        runtime_resumable=control_state.runtime_resumable,
        tmux_session_live=control_state.tmux_session_live,
        can_accept_prompt_now=control_state.can_accept_prompt_now,
        interruptible=control_state.interruptible,
        turn=summary_state.turn,
        last_turn=summary_state.last_turn,
        active_turn_started_at_utc=active_turn.started_at_utc if active_turn is not None else None,
        active_turn_interrupt_requested_at_utc=(
            active_turn.interrupt_requested_at_utc if active_turn is not None else None
        ),
        last_turn_status=latest_turn.status if latest_turn is not None else None,
        last_turn_started_at_utc=latest_turn.started_at_utc if latest_turn is not None else None,
        last_turn_completed_at_utc=(
            latest_turn.completed_at_utc if latest_turn is not None else None
        ),
        last_turn_completion_source=(
            latest_turn.completion_source if latest_turn is not None else None
        ),
        last_turn_returncode=latest_turn.returncode if latest_turn is not None else None,
        last_turn_history_summary=(
            latest_turn.history_summary if latest_turn is not None else None
        ),
        last_turn_error=latest_turn.error if latest_turn is not None else None,
        mailboxes=summary_state.mailboxes,
        gateway=summary_state.gateway,
        diagnostics=list(summary_state.diagnostics),
    )
    return HoumaoManagedAgentDetailResponse(
        tracked_agent_id=summary_state.tracked_agent_id,
        identity=summary_state.identity,
        summary_state=summary_state,
        detail=detail,
    )


def managed_headless_history_from_turn_records(
    *,
    tracked_agent_id: str,
    turn_records: list[ManagedHeadlessTurnRecord],
    limit: int,
) -> HoumaoManagedAgentHistoryResponse:
    """Project passive managed-headless turn records into shared history entries."""

    ordered = sorted(
        turn_records,
        key=lambda record: (record.started_at_utc, record.turn_id),
        reverse=True,
    )
    entries = [
        HoumaoManagedAgentHistoryEntry(
            recorded_at_utc=record.completed_at_utc or record.started_at_utc,
            summary=record.history_summary or f"Turn {record.turn_id} status={record.status}.",
            availability="available" if record.status == "active" else "unavailable",
            turn_phase="active" if record.status == "active" else "ready",
            last_turn_result=_last_turn_result_from_headless_status(record.status),
            turn_id=record.turn_id,
        )
        for record in ordered[:limit]
    ]
    return HoumaoManagedAgentHistoryResponse(
        tracked_agent_id=tracked_agent_id,
        entries=entries,
    )


def _availability_from_tui_state(state: AgentTuiStateResponse) -> ManagedAgentAvailability:
    """Map passive TUI observation posture into the shared availability enum."""

    if state.diagnostics.availability == "error":
        return "error"
    if state.diagnostics.availability in {"unavailable", "tui_down"}:
        return "unavailable"
    return "available"


def _tracked_errors_from_tui_state(state: AgentTuiStateResponse) -> list[HoumaoErrorDetail]:
    """Return surfaced probe and parse errors from one passive TUI state sample."""

    diagnostics: list[HoumaoErrorDetail] = []
    if state.diagnostics.probe_error is not None:
        diagnostics.append(state.diagnostics.probe_error)
    if state.diagnostics.parse_error is not None:
        diagnostics.append(state.diagnostics.parse_error)
    return diagnostics


def _availability_from_tui_transition(entry: object) -> ManagedAgentAvailability:
    """Map one passive TUI history entry into shared coarse availability."""

    diagnostics_availability = getattr(entry, "diagnostics_availability", "unknown")
    if diagnostics_availability == "error":
        return "error"
    if diagnostics_availability in {"unavailable", "tui_down"}:
        return "unavailable"
    return "available"


def _headless_availability_from_control_state(
    control_state: PassiveManagedHeadlessControlState,
) -> ManagedAgentAvailability:
    """Return shared managed-agent availability for one passive headless control state."""

    if not control_state.runtime_resumable:
        return "unavailable"
    if control_state.tmux_session_live:
        return "available"
    return "unavailable"


def _headless_diagnostics_from_control_state(
    control_state: PassiveManagedHeadlessControlState,
) -> list[HoumaoErrorDetail]:
    """Return surfaced diagnostics for one passive headless control state."""

    diagnostics: list[HoumaoErrorDetail] = []
    if not control_state.runtime_resumable:
        diagnostics.append(
            HoumaoErrorDetail(
                kind="runtime_resume_unavailable",
                message=(
                    "Managed headless authority exists, but the passive server could not "
                    "resume live runtime control from persisted state."
                ),
            )
        )
    elif not control_state.tmux_session_live:
        diagnostics.append(
            HoumaoErrorDetail(
                kind="tmux_session_missing",
                message=(
                    f"Native headless tmux session `{control_state.authority.tmux_session_name}` "
                    "is not live."
                ),
            )
        )
    return diagnostics


def _last_turn_result_from_headless_status(status: str) -> ManagedAgentLastTurnResult:
    """Map one headless turn status into the shared coarse last-turn result."""

    if status == "completed":
        return "success"
    if status == "interrupted":
        return "interrupted"
    if status in {"failed", "unknown"}:
        return "known_failure"
    return "none"
