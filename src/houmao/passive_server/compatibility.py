"""Compatibility projections from passive-server state into pair-managed models."""

from __future__ import annotations

from typing import Literal, cast

from houmao.agents.mailbox_runtime_models import MailboxTransport
from houmao.agents.realm_controller.backends.tmux_runtime import HEADLESS_AGENT_WINDOW_NAME
from houmao.agents.realm_controller.gateway_models import GatewayStatusV1
from houmao.agents.realm_controller.registry_models import ManagedAgentRegistryRecordV3
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
    HoumaoManagedAgentStateResponse,
    HoumaoManagedAgentTurnView,
    HoumaoManagedAgentTuiDetailView,
    ManagedAgentAvailability,
    ManagedAgentLastTurnResult,
)

_HEADLESS_BACKENDS = frozenset({"claude_headless", "codex_headless", "gemini_headless"})


def is_headless_backend(backend: str) -> bool:
    """Return whether one backend maps to the headless managed-agent transport."""

    return backend in _HEADLESS_BACKENDS


def managed_identity_from_discovered_summary(
    summary: DiscoveredAgentSummary,
) -> HoumaoManagedAgentIdentity:
    """Project one discovery summary into the shared managed-agent identity model."""

    transport: Literal["headless", "tui"] = (
        "headless" if is_headless_backend(summary.backend) else "tui"
    )
    tmux_window_name = (
        HEADLESS_AGENT_WINDOW_NAME
        if transport == "headless" or summary.backend == "local_interactive"
        else None
    )
    return HoumaoManagedAgentIdentity(
        tracked_agent_id=summary.agent_id,
        transport=transport,
        tool=summary.tool,
        session_name=summary.tmux_session_name if transport == "tui" else None,
        terminal_id=summary.agent_id if transport == "tui" else None,
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


def mailbox_summary_from_registry_record(
    record: ManagedAgentRegistryRecordV3,
) -> HoumaoManagedAgentMailboxSummaryView | None:
    """Return optional redacted mailbox posture from one registry record."""

    mailbox = record.mailbox
    if mailbox is None:
        return None
    transport = getattr(mailbox, "transport", None)
    if transport not in {"filesystem", "stalwart"}:
        return None
    return HoumaoManagedAgentMailboxSummaryView(
        transport=cast(MailboxTransport, transport),
        principal_id=getattr(mailbox, "principal_id", None),
        address=getattr(mailbox, "address", None),
    )


def mailbox_summary_from_headless_control_state(
    control_state: PassiveManagedHeadlessControlState,
) -> HoumaoManagedAgentMailboxSummaryView | None:
    """Return optional mailbox posture from one live headless control state."""

    controller = control_state.controller
    if controller is None:
        return None
    mailbox = controller.launch_plan.mailbox
    if mailbox is None:
        return None
    return HoumaoManagedAgentMailboxSummaryView(
        transport=mailbox.transport,
        principal_id=mailbox.principal_id,
        address=mailbox.address,
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
) -> HoumaoManagedAgentStateResponse:
    """Project one passive TUI observation sample into managed-agent summary state."""

    identity = managed_identity_from_discovered_agent(agent)
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
        diagnostics=_tracked_errors_from_tui_state(state),
        mailbox=mailbox_summary,
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
        canonical_terminal_state_route=f"/houmao/agents/{agent.record.agent_id}/state",
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

    if active_turn is not None:
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
        last_turn_result = _last_turn_result_from_headless_status(latest_turn.status)
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
        diagnostics=diagnostics,
        mailbox=mailbox_summary,
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
        mailbox=summary_state.mailbox,
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
