"""TUI observation service for the passive server.

This module provides per-agent TUI observers and a background polling service
that reconciles observers against the discovery index. Each observer polls a
single agent's tmux pane, parses the TUI surface, and feeds the shared
tracking session.
"""

from __future__ import annotations

import hashlib
import logging
import threading
import time
from collections import deque
from datetime import UTC, datetime, timedelta

from houmao.agents.realm_controller.backends.tmux_runtime import (
    TmuxCommandError,
    tmux_session_exists,
)
from houmao.passive_server.config import PassiveServerConfig
from houmao.passive_server.discovery import DiscoveredAgent, RegistryDiscoveryService
from houmao.passive_server.models import (
    AgentTuiDetailResponse,
    AgentTuiHistoryResponse,
    AgentTuiStateResponse,
)
from houmao.server.models import (
    HoumaoErrorDetail,
    HoumaoParsedSurface,
    HoumaoProbeSnapshot,
    HoumaoRecentTransition,
    HoumaoStabilityMetadata,
    HoumaoTrackedDiagnostics,
    HoumaoTrackedLastTurn,
    HoumaoTrackedSurface,
    HoumaoTrackedTurn,
    ParseStatus,
    ProcessState,
    TrackedDiagnosticsAvailability,
    TransportState,
)
from houmao.server.tui.parser import OfficialTuiParserAdapter
from houmao.server.tui.process import PaneProcessInspector
from houmao.server.tui.transport import TmuxTransportResolver
from houmao.shared_tui_tracking.models import TrackerConfig, TrackedStateSnapshot
from houmao.shared_tui_tracking.registry import DetectorProfileRegistry, app_id_from_tool
from houmao.shared_tui_tracking.session import TuiTrackerSession

logger = logging.getLogger(__name__)

_DEFAULT_SUPPORTED_TUI_PROCESSES: dict[str, tuple[str, ...]] = {
    "claude": ("claude", "claude-code"),
    "codex": ("codex",),
    "gemini": ("gemini",),
}

_DEFAULT_RECENT_TRANSITION_LIMIT = 50
_DEFAULT_SETTLE_SECONDS = 1.0
_DEFAULT_STABILITY_THRESHOLD_SECONDS = 1.0


def _utc_now_iso() -> str:
    """Return the current UTC timestamp in seconds precision."""

    return datetime.now(UTC).isoformat(timespec="seconds")


def _diagnostics_availability(
    *,
    transport_state: TransportState,
    process_state: ProcessState,
    parse_status: ParseStatus,
) -> TrackedDiagnosticsAvailability:
    """Map low-level observation outcomes into tracked diagnostic availability."""

    if transport_state in ("tmux_missing", "probe_error"):
        return "unavailable"
    if process_state in ("tui_down", "unsupported_tool"):
        return "tui_down"
    if process_state == "probe_error":
        return "error"
    if parse_status == "parse_error":
        return "error"
    if parse_status == "parsed":
        return "available"
    return "unknown"


class AgentTuiObserver:
    """Per-agent TUI observer that polls a tmux pane and tracks state.

    Composes ``TuiTrackerSession``, ``TmuxTransportResolver``,
    ``PaneProcessInspector``, and ``OfficialTuiParserAdapter`` to implement
    the full observation pipeline without reusing ``LiveSessionTracker``.
    """

    def __init__(
        self,
        *,
        agent_id: str,
        agent_name: str,
        tool: str,
        session_name: str,
        window_name: str | None = None,
        observed_version: str | None = None,
    ) -> None:
        """Initialize one observer for a discovered agent."""

        self.m_agent_id: str = agent_id
        self.m_agent_name: str = agent_name
        self.m_tool: str = tool
        self.m_session_name: str = session_name
        self.m_window_name: str | None = window_name
        self.m_observed_version: str | None = observed_version

        app_id = app_id_from_tool(tool=tool)
        self.m_tracker_session: TuiTrackerSession = TuiTrackerSession(
            app_id=app_id,
            observed_version=observed_version,
            config=TrackerConfig(
                settle_seconds=_DEFAULT_SETTLE_SECONDS,
                stability_threshold_seconds=_DEFAULT_STABILITY_THRESHOLD_SECONDS,
            ),
            registry=DetectorProfileRegistry.default(),
        )

        self.m_transport_resolver: TmuxTransportResolver = TmuxTransportResolver()
        self.m_process_inspector: PaneProcessInspector = PaneProcessInspector(
            supported_processes=_DEFAULT_SUPPORTED_TUI_PROCESSES
        )
        self.m_parser_adapter: OfficialTuiParserAdapter = OfficialTuiParserAdapter()

        self.m_baseline_pos: int | None = None
        self.m_last_probe_snapshot: HoumaoProbeSnapshot | None = None
        self.m_parsed_surface: HoumaoParsedSurface | None = None
        self.m_transport_state: TransportState = "tmux_missing"
        self.m_process_state: ProcessState = "unknown"
        self.m_parse_status: ParseStatus = "transport_unavailable"
        self.m_probe_error: HoumaoErrorDetail | None = None
        self.m_parse_error: HoumaoErrorDetail | None = None
        self.m_recent_transitions: deque[HoumaoRecentTransition] = deque(
            maxlen=_DEFAULT_RECENT_TRANSITION_LIMIT
        )
        self.m_started_at_utc: datetime = datetime.now(UTC)
        self.m_started_at_monotonic: float = time.monotonic()

    # -- poll cycle -----------------------------------------------------------

    def poll_cycle(self) -> None:
        """Execute the full observation pipeline for one cycle."""

        observed_at_utc = _utc_now_iso()

        # 1. Check tmux session existence
        if not tmux_session_exists(session_name=self.m_session_name):
            self._record_diagnostics(
                transport_state="tmux_missing",
                process_state="unknown",
                parse_status="transport_unavailable",
                probe_error=None,
                parse_error=None,
                parsed_surface=None,
                probe_snapshot=None,
            )
            return

        # 2. Resolve tmux target
        try:
            target = self.m_transport_resolver.resolve_target(
                session_name=self.m_session_name,
                window_name=self.m_window_name,
            )
        except TmuxCommandError as exc:
            self._record_diagnostics(
                transport_state="probe_error",
                process_state="probe_error",
                parse_status="probe_error",
                probe_error=HoumaoErrorDetail(kind="tmux_probe_error", message=str(exc)),
                parse_error=None,
                parsed_surface=None,
                probe_snapshot=None,
            )
            return

        # 3. Inspect process liveness
        process_inspection = self.m_process_inspector.inspect(
            tool=self.m_tool,
            pane_pid=target.pane.pane_pid,
        )
        probe_snapshot = HoumaoProbeSnapshot(
            observed_at_utc=observed_at_utc,
            pane_id=target.pane.pane_id,
            pane_pid=target.pane.pane_pid,
            matched_process_names=list(process_inspection.matched_process_names),
        )

        if process_inspection.process_state == "probe_error":
            self._record_diagnostics(
                transport_state="tmux_up",
                process_state="probe_error",
                parse_status="probe_error",
                probe_error=HoumaoErrorDetail(
                    kind="process_probe_error",
                    message=process_inspection.error_message or "Process inspection failed.",
                ),
                parse_error=None,
                parsed_surface=None,
                probe_snapshot=probe_snapshot,
            )
            return

        if process_inspection.process_state in {"unsupported_tool", "tui_down"}:
            parse_status: ParseStatus = (
                "unsupported_tool"
                if process_inspection.process_state == "unsupported_tool"
                else "skipped_tui_down"
            )
            self._record_diagnostics(
                transport_state="tmux_up",
                process_state=process_inspection.process_state,
                parse_status=parse_status,
                probe_error=None,
                parse_error=None,
                parsed_surface=None,
                probe_snapshot=probe_snapshot,
            )
            return

        # 4. Capture pane text
        try:
            output_text = self.m_transport_resolver.capture_text(target=target)
        except TmuxCommandError as exc:
            self._record_diagnostics(
                transport_state="probe_error",
                process_state="probe_error",
                parse_status="probe_error",
                probe_error=HoumaoErrorDetail(kind="tmux_capture_error", message=str(exc)),
                parse_error=None,
                parsed_surface=None,
                probe_snapshot=probe_snapshot,
            )
            return

        # Update probe snapshot with captured text info
        probe_snapshot = probe_snapshot.model_copy(
            update={
                "captured_text_hash": hashlib.sha1(output_text.encode("utf-8")).hexdigest(),
                "captured_text_length": len(output_text),
                "captured_text_excerpt": output_text[-4000:],
            }
        )

        # 5. Parse TUI surface
        if not self.m_parser_adapter.supports_tool(tool=self.m_tool):
            self._record_diagnostics(
                transport_state="tmux_up",
                process_state="tui_up",
                parse_status="unsupported_tool",
                probe_error=None,
                parse_error=None,
                parsed_surface=None,
                probe_snapshot=probe_snapshot,
            )
            self.m_tracker_session.on_snapshot(output_text)
            self._drain_and_record_transitions()
            return

        if self.m_baseline_pos is None:
            try:
                self.m_baseline_pos = self.m_parser_adapter.capture_baseline(
                    tool=self.m_tool,
                    output_text=output_text,
                )
            except Exception as exc:
                self._record_diagnostics(
                    transport_state="tmux_up",
                    process_state="tui_up",
                    parse_status="parse_error",
                    probe_error=None,
                    parse_error=HoumaoErrorDetail(kind="parse_baseline_error", message=str(exc)),
                    parsed_surface=None,
                    probe_snapshot=probe_snapshot,
                )
                self.m_tracker_session.on_snapshot(output_text)
                self._drain_and_record_transitions()
                return

        parse_result = self.m_parser_adapter.parse(
            tool=self.m_tool,
            output_text=output_text,
            baseline_pos=self.m_baseline_pos,
        )

        final_parse_status: ParseStatus = (
            "parsed" if parse_result.parsed_surface is not None else "parse_error"
        )
        self._record_diagnostics(
            transport_state="tmux_up",
            process_state="tui_up",
            parse_status=final_parse_status,
            probe_error=None,
            parse_error=parse_result.parse_error,
            parsed_surface=parse_result.parsed_surface,
            probe_snapshot=probe_snapshot,
        )

        # 6. Feed tracker session
        self.m_tracker_session.on_snapshot(output_text)
        self._drain_and_record_transitions()

    # -- state accessors ------------------------------------------------------

    def current_state(self) -> AgentTuiStateResponse:
        """Build the compact observation state response."""

        snap = self.m_tracker_session.current_state()
        return AgentTuiStateResponse(
            agent_id=self.m_agent_id,
            agent_name=self.m_agent_name,
            diagnostics=self._build_diagnostics(),
            surface=self._build_surface(snap),
            turn=HoumaoTrackedTurn(phase=snap.turn_phase),
            last_turn=self._build_last_turn(snap),
            stability=self._build_stability(snap),
        )

    def current_detail(self) -> AgentTuiDetailResponse:
        """Build the detailed observation state response."""

        snap = self.m_tracker_session.current_state()
        return AgentTuiDetailResponse(
            agent_id=self.m_agent_id,
            agent_name=self.m_agent_name,
            diagnostics=self._build_diagnostics(),
            probe_snapshot=self.m_last_probe_snapshot,
            parsed_surface=self.m_parsed_surface,
            surface=self._build_surface(snap),
            turn=HoumaoTrackedTurn(phase=snap.turn_phase),
            last_turn=self._build_last_turn(snap),
            stability=self._build_stability(snap),
        )

    def history(self, limit: int = 50) -> AgentTuiHistoryResponse:
        """Build the history response from recent transitions."""

        entries = list(self.m_recent_transitions)
        entries.reverse()  # most-recent-first
        if limit < len(entries):
            entries = entries[:limit]
        return AgentTuiHistoryResponse(
            agent_id=self.m_agent_id,
            agent_name=self.m_agent_name,
            entries=entries,
        )

    def close(self) -> None:
        """Release resources held by the observer."""

        self.m_tracker_session.close()

    # -- internal helpers -----------------------------------------------------

    def _record_diagnostics(
        self,
        *,
        transport_state: TransportState,
        process_state: ProcessState,
        parse_status: ParseStatus,
        probe_error: HoumaoErrorDetail | None,
        parse_error: HoumaoErrorDetail | None,
        parsed_surface: HoumaoParsedSurface | None,
        probe_snapshot: HoumaoProbeSnapshot | None,
    ) -> None:
        """Update the observer's diagnostic state."""

        self.m_transport_state = transport_state
        self.m_process_state = process_state
        self.m_parse_status = parse_status
        self.m_probe_error = probe_error
        self.m_parse_error = parse_error
        if parsed_surface is not None:
            self.m_parsed_surface = parsed_surface
        if probe_snapshot is not None:
            self.m_last_probe_snapshot = probe_snapshot

    def _build_diagnostics(self) -> HoumaoTrackedDiagnostics:
        """Build the diagnostics model from current observer state."""

        return HoumaoTrackedDiagnostics(
            availability=_diagnostics_availability(
                transport_state=self.m_transport_state,
                process_state=self.m_process_state,
                parse_status=self.m_parse_status,
            ),
            transport_state=self.m_transport_state,
            process_state=self.m_process_state,
            parse_status=self.m_parse_status,
            probe_error=self.m_probe_error,
            parse_error=self.m_parse_error,
        )

    @staticmethod
    def _build_surface(snap: TrackedStateSnapshot) -> HoumaoTrackedSurface:
        """Build the surface model from a tracker snapshot."""

        return HoumaoTrackedSurface(
            accepting_input=snap.surface_accepting_input,
            editing_input=snap.surface_editing_input,
            ready_posture=snap.surface_ready_posture,
        )

    @staticmethod
    def _build_last_turn(snap: TrackedStateSnapshot) -> HoumaoTrackedLastTurn:
        """Build the last-turn model from a tracker snapshot."""

        return HoumaoTrackedLastTurn(
            result=snap.last_turn_result,
            source=snap.last_turn_source,
        )

    def _build_stability(self, snap: TrackedStateSnapshot) -> HoumaoStabilityMetadata:
        """Build the stability metadata from a tracker snapshot."""

        stable_since_utc = self.m_started_at_utc + timedelta(seconds=snap.stable_since_seconds)
        return HoumaoStabilityMetadata(
            signature=snap.stability_signature,
            stable=snap.stable,
            stable_for_seconds=snap.stable_for_seconds,
            stable_since_utc=stable_since_utc.isoformat(timespec="seconds"),
        )

    def _drain_and_record_transitions(self) -> None:
        """Drain events from the tracker session and record as recent transitions."""

        events = self.m_tracker_session.drain_events()
        for event in events:
            recorded_at = self.m_started_at_utc + timedelta(seconds=event.at_seconds)
            transition = HoumaoRecentTransition(
                recorded_at_utc=recorded_at.isoformat(timespec="seconds"),
                summary=event.note,
                diagnostics_availability=_diagnostics_availability(
                    transport_state=self.m_transport_state,
                    process_state=self.m_process_state,
                    parse_status=self.m_parse_status,
                ),
                turn_phase=event.turn_phase,
                last_turn_result=event.last_turn_result,
                last_turn_source=event.last_turn_source,
                transport_state=self.m_transport_state,
                process_state=self.m_process_state,
                parse_status=self.m_parse_status,
            )
            self.m_recent_transitions.append(transition)


# ---------------------------------------------------------------------------
# TUI observation service
# ---------------------------------------------------------------------------


class TuiObservationService:
    """Background service that manages per-agent TUI observers.

    Runs a single polling thread that reconciles observers against the
    discovery index and polls each active observer on a configurable interval.
    """

    def __init__(
        self,
        *,
        discovery: RegistryDiscoveryService,
        config: PassiveServerConfig,
    ) -> None:
        """Initialize the observation service."""

        self.m_discovery: RegistryDiscoveryService = discovery
        self.m_config: PassiveServerConfig = config
        self.m_observers: dict[str, AgentTuiObserver] = {}
        self.m_stop_event: threading.Event = threading.Event()
        self.m_thread: threading.Thread | None = None

    # -- lifecycle ------------------------------------------------------------

    def start(self) -> None:
        """Start the background observation polling thread."""

        if self.m_thread is not None:
            return
        self.m_stop_event.clear()
        self.m_thread = threading.Thread(
            target=self._poll_loop, daemon=True, name="observation-poll"
        )
        self.m_thread.start()

    def stop(self) -> None:
        """Stop the background observation polling thread and clean up observers."""

        self.m_stop_event.set()
        if self.m_thread is not None:
            self.m_thread.join(timeout=10.0)
            self.m_thread = None
        for observer in self.m_observers.values():
            try:
                observer.close()
            except Exception:
                logger.debug("Error closing observer for %s", observer.m_agent_id, exc_info=True)
        self.m_observers.clear()

    # -- accessor -------------------------------------------------------------

    def get_observer(self, agent_id: str) -> AgentTuiObserver | None:
        """Return the observer for an agent, or ``None`` if not observed."""

        return self.m_observers.get(agent_id)

    # -- internal -------------------------------------------------------------

    def _poll_loop(self) -> None:
        """Background loop: reconcile, poll, sleep, repeat until stopped."""

        while not self.m_stop_event.is_set():
            try:
                self._run_cycle()
            except Exception:
                logger.exception("Observation cycle failed")
            self.m_stop_event.wait(timeout=self.m_config.observation_poll_interval_seconds)

    def _run_cycle(self) -> None:
        """Execute one full observation cycle."""

        current_agents = self.m_discovery.index.list_all()
        self._reconcile_observers(current_agents)
        self._poll_all_observers()

    def _reconcile_observers(self, current_agents: list[DiscoveredAgent]) -> None:
        """Create new observers and remove stale ones."""

        current_ids = {a.record.agent_id for a in current_agents}

        # Remove observers for agents no longer in the index
        stale_ids = set(self.m_observers.keys()) - current_ids
        for agent_id in stale_ids:
            observer = self.m_observers.pop(agent_id)
            try:
                observer.close()
            except Exception:
                logger.debug("Error closing stale observer for %s", agent_id, exc_info=True)

        # Create observers for newly discovered agents
        for agent in current_agents:
            agent_id = agent.record.agent_id
            if agent_id in self.m_observers:
                continue
            if not agent.record.terminal.session_name:
                continue
            self.m_observers[agent_id] = AgentTuiObserver(
                agent_id=agent_id,
                agent_name=agent.record.agent_name,
                tool=agent.record.identity.tool,
                session_name=agent.record.terminal.session_name,
            )

    def _poll_all_observers(self) -> None:
        """Poll each active observer with exception isolation."""

        for agent_id, observer in list(self.m_observers.items()):
            try:
                observer.poll_cycle()
            except Exception:
                logger.exception("Observer poll failed for agent %s", agent_id)
