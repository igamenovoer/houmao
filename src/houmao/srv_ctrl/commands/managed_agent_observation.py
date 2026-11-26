"""Observe a selected managed runtime from its recorded mode and verified binding."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from houmao.agents.mailbox_runtime_support import (
    mailboxes_resolved_config_from_payload,
    safe_registry_mailboxes_projection,
)
from houmao.agents.realm_controller.backends.dsh_web import DshWebSession
from houmao.agents.realm_controller.backends.kimi_web import KimiWebSession
from houmao.agents.realm_controller.boundary_models import SessionManifestPayloadV4
from houmao.agents.realm_controller.errors import GatewayHttpError, SessionManifestError
from houmao.agents.realm_controller.gateway_client import GatewayClient
from houmao.agents.realm_controller.gateway_models import GatewayWebControlStateV1
from houmao.agents.realm_controller.gateway_storage import web_attach_metadata_from_state
from houmao.agents.realm_controller.headless_snapshots import latest_headless_turn
from houmao.agents.realm_controller.managed_control import (
    MANAGED_STRUCTURED_TUI_BACKENDS,
    ManagedControlCapabilitiesV1,
    ManagedControlObservationV1,
    managed_control_capabilities,
    terminal_prompt_not_ready_reasons,
)
from houmao.agents.realm_controller.registry_models import ManagedAgentRegistryRecordV3
from houmao.agents.realm_controller.registry_storage import is_live_agent_record_fresh
from houmao.agents.realm_controller.runtime import RuntimeSessionController, resume_runtime_session
from houmao.agents.realm_controller.web_observation import (
    WebObservation,
    web_observation_is_fresh,
    web_state_is_fresh,
)
from houmao.passive_server.compatibility import (
    mailbox_summary_from_registry_record,
    managed_native_tui_detail_response,
    managed_runtime_headless_detail_response,
    managed_runtime_headless_state_from_observation,
    managed_service_detail_response,
    managed_service_state_from_observation,
    managed_web_state_from_native,
)
from houmao.server.models import (
    HoumaoErrorDetail,
    HoumaoManagedAgentDetailResponse,
    HoumaoManagedAgentGatewaySummaryView,
    HoumaoManagedAgentHeadlessDetailView,
    HoumaoManagedAgentIdentity,
    HoumaoManagedAgentLastTurnView,
    HoumaoManagedAgentMailboxSummaryView,
    HoumaoManagedAgentNativeTuiDetailView,
    HoumaoManagedAgentPublicationView,
    HoumaoManagedAgentServiceDetailView,
    HoumaoManagedAgentStateResponse,
    HoumaoManagedAgentTuiDetailView,
    HoumaoManagedAgentTurnView,
    HoumaoManagedAgentWebDetailView,
    HoumaoTerminalStateResponse,
    HoumaoTrackedDiagnostics,
    HoumaoTrackedSessionIdentity,
    HoumaoTrackedSurface,
    ManagedAgentDetailPayload,
)
from houmao.shared_tui_tracking.ownership import SingleSessionTrackingRuntime


def observe_selected_agent(
    *,
    identity: HoumaoManagedAgentIdentity,
    record: ManagedAgentRegistryRecordV3,
    manifest_path: Path,
    manifest: SessionManifestPayloadV4 | None,
    gateway_client: GatewayClient | None = None,
    gateway_summary: HoumaoManagedAgentGatewaySummaryView | None = None,
    authority_error: str | None = None,
) -> HoumaoManagedAgentDetailResponse:
    """Compose summary and detail from the same mode-specific observation."""

    mailboxes = mailbox_summary_from_registry_record(record)
    if manifest is not None:
        try:
            resolved = mailboxes_resolved_config_from_payload(
                manifest.launch_plan.mailboxes, manifest_path=manifest_path
            )
            mailboxes = HoumaoManagedAgentMailboxSummaryView.model_validate(
                {
                    **safe_registry_mailboxes_projection(resolved),
                    "canonical_mail_identity": resolved.canonical_mail_identity,
                }
            )
        except (OSError, ValueError):
            # A protected binding that cannot be decoded leaves the published summary visible.
            pass

    live_candidate = record.lifecycle.state == "active"
    detail: HoumaoManagedAgentDetailResponse | None = None
    if manifest is not None:
        try:
            if manifest.mode == "headless":
                detail = _headless_detail(
                    identity=identity,
                    path=manifest_path,
                    manifest=manifest,
                    client=gateway_client,
                    mailboxes=mailboxes,
                    gateway=gateway_summary,
                )
            elif live_candidate and manifest.mode == "service":
                summary = managed_service_state_from_observation(
                    identity=identity,
                    mailbox_summary=mailboxes,
                    gateway_summary=gateway_summary,
                    observation=_native_controller(
                        manifest_path, manifest
                    ).observe_managed_service(),
                )
                detail = managed_service_detail_response(summary)
            elif live_candidate and manifest.mode == "web":
                summary = managed_web_state_from_native(
                    identity=identity,
                    mailbox_summary=mailboxes,
                    gateway_summary=gateway_summary,
                    state=_observe_web(manifest_path, manifest, gateway_client),
                )
                detail = _detail(summary, HoumaoManagedAgentWebDetailView(state=summary.web))
            elif live_candidate and manifest.backend in MANAGED_STRUCTURED_TUI_BACKENDS:
                detail = managed_native_tui_detail_response(
                    identity=identity,
                    mailbox_summary=mailboxes,
                    gateway_summary=gateway_summary,
                    observation=_native_controller(manifest_path, manifest).observe_managed_tui(),
                )
            elif live_candidate and manifest.mode == "tui":
                detail = _tui_detail(
                    identity=identity,
                    path=manifest_path,
                    manifest=manifest,
                    client=gateway_client,
                    mailboxes=mailboxes,
                    gateway=gateway_summary,
                )
        except (RuntimeError, OSError, ValueError):
            authority_error = f"Evidence for the selected {record.mode} runtime is unavailable."

    if detail is None:
        detail = _unavailable_detail(
            identity=identity,
            record=record,
            mailboxes=mailboxes,
            gateway=gateway_summary,
            reason=authority_error
            or f"The registry records this runtime as {record.lifecycle.state}.",
        )
    liveness = record.liveness
    memory = manifest.runtime if manifest is not None else None
    summary = detail.summary_state.model_copy(
        update={
            "publication": HoumaoManagedAgentPublicationView(
                state_updated_at=record.lifecycle.state_updated_at,
                published_at=liveness.published_at if liveness is not None else None,
                lease_expires_at=liveness.lease_expires_at if liveness is not None else None,
                lease_freshness=(
                    ("current" if is_live_agent_record_fresh(record) else "expired")
                    if liveness is not None
                    else None
                ),
            ),
            "memory_root": memory.memory_root if memory is not None else None,
            "memo_file": memory.memo_file if memory is not None else None,
            "pages_dir": memory.pages_dir if memory is not None else None,
        }
    )
    return detail.model_copy(update={"summary_state": summary})


def _detail(
    summary: HoumaoManagedAgentStateResponse, detail: ManagedAgentDetailPayload
) -> HoumaoManagedAgentDetailResponse:
    """Wrap one mode-specific result using the summary's selected identity."""

    return HoumaoManagedAgentDetailResponse(
        tracked_agent_id=summary.tracked_agent_id,
        identity=summary.identity,
        summary_state=summary,
        detail=detail,
    )


def _capabilities(identity: HoumaoManagedAgentIdentity) -> ManagedControlCapabilitiesV1 | None:
    """Return mode-bound capability fields for a registry-backed summary."""

    if identity.mode is None or identity.backend is None:
        return None
    return managed_control_capabilities(
        tool=identity.tool,
        mode=identity.mode,
        backend=identity.backend,
        native_surface=identity.native_surface,
    )


def _unavailable_detail(
    *,
    identity: HoumaoManagedAgentIdentity,
    record: ManagedAgentRegistryRecordV3,
    mailboxes: HoumaoManagedAgentMailboxSummaryView | None,
    gateway: HoumaoManagedAgentGatewaySummaryView | None,
    reason: str,
) -> HoumaoManagedAgentDetailResponse:
    """Preserve authorized publication when observation or manifest access is unavailable."""

    diagnostic = HoumaoErrorDetail(kind="managed_observation_unavailable", message=reason)
    native_tui = record.identity.backend in MANAGED_STRUCTURED_TUI_BACKENDS
    control = ManagedControlObservationV1(
        source="tui_native" if native_tui else "owner_registry",
        freshness="unknown",
        terminal_attachment="unverified" if native_tui else None,
    )
    summary = HoumaoManagedAgentStateResponse(
        tracked_agent_id=identity.tracked_agent_id,
        identity=identity,
        availability="unavailable",
        turn=HoumaoManagedAgentTurnView(phase="unknown"),
        last_turn=HoumaoManagedAgentLastTurnView(result="unknown"),
        control=control,
        diagnostics=[diagnostic],
        mailboxes=mailboxes,
        gateway=gateway,
        capabilities=_capabilities(identity),
    )
    mode = record.mode
    if mode == "service":
        return _detail(summary, HoumaoManagedAgentServiceDetailView(state=control))
    if mode == "web":
        return _detail(summary, HoumaoManagedAgentWebDetailView(state=None))
    if native_tui:
        return _detail(summary, HoumaoManagedAgentNativeTuiDetailView(state=control))
    if mode == "tui":
        return _detail(
            summary,
            HoumaoManagedAgentTuiDetailView(
                terminal_id=None,
                canonical_terminal_state_route=None,
                canonical_terminal_history_route=None,
                diagnostics=HoumaoTrackedDiagnostics(
                    availability="unavailable",
                    transport_state="probe_error",
                    process_state="unknown",
                    parse_status="transport_unavailable",
                    probe_error=diagnostic,
                ),
                surface=HoumaoTrackedSurface(
                    accepting_input="unknown",
                    editing_input="unknown",
                    ready_posture="unknown",
                    pending_input="unknown",
                ),
                stability=None,
            ),
        )
    return _detail(
        summary,
        HoumaoManagedAgentHeadlessDetailView(
            runtime_resumable=False,
            tmux_session_live=None,
            can_accept_prompt_now=None,
            interruptible=False,
            turn=summary.turn,
            last_turn=summary.last_turn,
            mailboxes=mailboxes,
            gateway=gateway,
            diagnostics=summary.diagnostics,
        ),
    )


def _native_controller(path: Path, manifest: SessionManifestPayloadV4) -> RuntimeSessionController:
    """Reopen only the selected native observation adapter without lifecycle effects."""

    controller = resume_runtime_session(session_manifest_path=path, read_only=True)
    if (
        controller.agent_id != manifest.agent_id
        or controller.registry_generation_id != manifest.registry_generation_id
        or controller.execution_binding != manifest.runtime.execution_binding
        or controller.launch_plan.mode != manifest.mode
        or controller.launch_plan.backend != manifest.backend
    ):
        raise SessionManifestError("The managed runtime changed during adapter acquisition.")
    return controller


def _observe_web(
    path: Path, manifest: SessionManifestPayloadV4, client: GatewayClient | None
) -> GatewayWebControlStateV1:
    """Try an attributable gateway sample, then inspect the exact native binding."""

    metadata = web_attach_metadata_from_state(manifest.backend_state, backend=manifest.backend)
    if (
        metadata.identity.agent_id != manifest.agent_id
        or metadata.identity.generation != manifest.registry_generation_id
        or metadata.identity.runtime_session_id != manifest.runtime.session_id
    ):
        raise SessionManifestError("Native Web metadata differs from the selected runtime.")
    if client is not None:
        try:
            state = client.get_web_state()
            if (
                state.identity == metadata.identity
                and state.origin == metadata.origin
                and state.browser_url == metadata.browser_url
                and state.availability == "available"
                and web_state_is_fresh(state)
            ):
                return state.model_copy(update={"source": "gateway"})
        except GatewayHttpError:
            pass
    try:
        controller = _native_controller(path, manifest)
        backend = controller.backend_session
        if isinstance(backend, DshWebSession):
            state_reader = backend.observe_web_state_read_only
            history_reader = backend.observe_web_history_read_only
        elif isinstance(backend, KimiWebSession):
            state_reader = backend.observe_web_state
            history_reader = backend.observe_web_history
        else:
            raise SessionManifestError("The selected Web observer is unavailable.")
        with controller.execution_scope():
            return WebObservation(
                metadata=metadata,
                state=state_reader,
                history=history_reader,
                sparse_history=manifest.backend == "kimi_web",
            ).refresh()
    except (OSError, RuntimeError, ValueError):
        return WebObservation(
            metadata=metadata, state=lambda: {}, history=lambda **_: {}
        ).unavailable()


def _headless_detail(
    *,
    identity: HoumaoManagedAgentIdentity,
    path: Path,
    manifest: SessionManifestPayloadV4,
    client: GatewayClient | None,
    mailboxes: HoumaoManagedAgentMailboxSummaryView | None,
    gateway: HoumaoManagedAgentGatewaySummaryView | None,
) -> HoumaoManagedAgentDetailResponse:
    """Read saved outcomes and qualify admission separately when a gateway can report it."""

    latest_turn = latest_headless_turn(
        manifest_path=path, tool=manifest.tool, backend=manifest.backend
    )
    live = None
    if client is not None:
        try:
            live = client.get_headless_control_state()
        except GatewayHttpError:
            pass
    summary = managed_runtime_headless_state_from_observation(
        identity=identity,
        latest_turn=latest_turn,
        owner_available=live.tmux_session_live if live is not None else None,
        native_session_id=manifest.headless.session_id if manifest.headless is not None else None,
        mailbox_summary=mailboxes,
        gateway_summary=gateway,
    )
    control = summary.control
    assert control is not None
    if live is None:
        summary.diagnostics.append(
            HoumaoErrorDetail(
                kind="headless_admission_unverified",
                message="Saved turn evidence is available independently of live prompt admission.",
            )
        )
    else:
        active_turn_id = live.active_turn_id or control.active_turn_id
        ready = live.can_accept_prompt_now and active_turn_id is None
        summary = summary.model_copy(
            update={
                "turn": HoumaoManagedAgentTurnView(
                    phase="active" if active_turn_id else "ready" if ready else "unknown",
                    active_turn_id=active_turn_id,
                ),
                "control": control.model_copy(
                    update={
                        "freshness": "current",
                        "observed_at_utc": datetime.now(UTC).isoformat(),
                        "can_accept_prompt_now": ready,
                        "active_turn_id": active_turn_id,
                    }
                ),
            }
        )
    result = managed_runtime_headless_detail_response(
        summary_state=summary, latest_turn=latest_turn
    )
    if live is not None:
        result = result.model_copy(
            update={
                "detail": result.detail.model_copy(
                    update={
                        "runtime_resumable": live.runtime_resumable,
                        "interruptible": live.interruptible,
                        "chat_session": live.chat_session,
                    }
                )
            }
        )
    return result


def _observe_tui(
    *,
    identity: HoumaoManagedAgentIdentity,
    path: Path,
    manifest: SessionManifestPayloadV4,
    client: GatewayClient | None,
) -> HoumaoTerminalStateResponse:
    """Obtain fresh tracker evidence from the gateway or the saved exact pane."""

    binding = manifest.tmux
    if binding is None or binding.socket_path is None:
        raise SessionManifestError("The selected runtime has no saved primary terminal binding.")
    if client is not None:
        try:
            tracked = client.get_tui_state()
            probe = tracked.probe_snapshot
            if (
                tracked.tracked_session.agent_id == manifest.agent_id
                and tracked.tracked_session.tmux_session_name == binding.session_name
                and tracked.tracked_session.tool == manifest.tool
                and tracked.diagnostics.availability == "available"
                and probe is not None
                and probe.pane_id == binding.primary_pane_id
                and web_observation_is_fresh(probe.observed_at_utc)
            ):
                return tracked
        except GatewayHttpError:
            pass
    policy = manifest.launch_policy_provenance
    tracker = SingleSessionTrackingRuntime(
        identity=HoumaoTrackedSessionIdentity(
            tracked_session_id=identity.tracked_agent_id,
            session_name=binding.session_name,
            tool=manifest.tool,
            observed_tool_version=policy.detected_tool_version if policy is not None else None,
            tmux_session_name=binding.session_name,
            tmux_window_name=binding.primary_window_name,
            agent_name=manifest.agent_name,
            agent_id=manifest.agent_id,
            manifest_path=str(path),
            session_root=str(path.parent),
        ),
        primary_binding=binding,
        joined=(
            manifest.agent_launch_authority is not None
            and manifest.agent_launch_authority.session_origin == "joined_tmux"
        ),
    )
    return tracker.refresh_once()


def _tui_detail(
    *,
    identity: HoumaoManagedAgentIdentity,
    path: Path,
    manifest: SessionManifestPayloadV4,
    client: GatewayClient | None,
    mailboxes: HoumaoManagedAgentMailboxSummaryView | None,
    gateway: HoumaoManagedAgentGatewaySummaryView | None,
) -> HoumaoManagedAgentDetailResponse:
    """Report terminal posture only from the selected owner's observed primary pane."""

    state = _observe_tui(identity=identity, path=path, manifest=manifest, client=client)
    probe = state.probe_snapshot
    known = probe is not None and state.diagnostics.availability == "available"
    diagnostics = [
        error
        for error in (state.diagnostics.probe_error, state.diagnostics.parse_error)
        if error is not None
    ]
    if not known and not diagnostics:
        diagnostics.append(
            HoumaoErrorDetail(
                kind="terminal_observation_unavailable",
                message="Current observation of the selected primary terminal is unavailable.",
            )
        )
    terminal_id = state.terminal_id if known else None
    identity = identity.model_copy(
        update={
            "terminal_id": terminal_id,
            "tmux_window_name": state.tracked_session.tmux_window_name,
        }
    )
    summary = HoumaoManagedAgentStateResponse(
        tracked_agent_id=identity.tracked_agent_id,
        identity=identity,
        control=ManagedControlObservationV1(
            source="terminal_tracker",
            freshness="current" if known else "unknown",
            observed_at_utc=probe.observed_at_utc if probe is not None else None,
            owner_available=True if known else None,
            can_accept_prompt_now=(
                state.surface.pending_input == "no" and not terminal_prompt_not_ready_reasons(state)
                if known
                else None
            ),
        ),
        availability="available" if known else "unavailable",
        turn=HoumaoManagedAgentTurnView(
            phase=state.turn.phase if known else "unknown",
            active_turn_id=f"tui-anchor:{identity.tracked_agent_id}"
            if known and state.turn.phase == "active"
            else None,
        ),
        last_turn=HoumaoManagedAgentLastTurnView(
            result=state.last_turn.result if known else "unknown",
            updated_at_utc=state.last_turn.updated_at_utc if known else None,
        ),
        diagnostics=diagnostics,
        mailboxes=mailboxes,
        gateway=gateway,
        capabilities=_capabilities(identity),
    )
    return _detail(
        summary,
        HoumaoManagedAgentTuiDetailView(
            terminal_id=terminal_id,
            canonical_terminal_state_route=(
                f"/houmao/terminals/{terminal_id}/state" if terminal_id is not None else None
            ),
            canonical_terminal_history_route=(
                f"/houmao/terminals/{terminal_id}/history" if terminal_id is not None else None
            ),
            diagnostics=state.diagnostics,
            probe_snapshot=state.probe_snapshot,
            parsed_surface=state.parsed_surface if known else None,
            surface=state.surface,
            stability=state.stability,
        ),
    )
