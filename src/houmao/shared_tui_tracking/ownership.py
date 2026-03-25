"""Neutral single-session TUI tracking helpers.

This module provides a shared single-session tracking runtime that can be used
by both the direct `houmao-server` fallback and the per-agent gateway control
plane without requiring the gateway to import the `houmao.server.tui` package
directly as its runtime boundary.
"""

from __future__ import annotations

import hashlib
import threading
import time

from houmao.agents.realm_controller.backends.tmux_runtime import (
    TmuxCommandError,
    tmux_session_exists,
)
from houmao.server.models import (
    HoumaoErrorDetail,
    HoumaoProbeSnapshot,
    HoumaoTerminalHistoryResponse,
    HoumaoTerminalStateResponse,
    HoumaoTrackedSessionIdentity,
)
from houmao.server.tui.parser import OfficialTuiParserAdapter
from houmao.server.tui.process import PaneProcessInspector
from houmao.server.tui.transport import TmuxTransportResolver
from houmao.server.tui.tracking import LiveSessionTracker, utc_now_iso

_DEFAULT_SUPPORTED_TUI_PROCESSES: dict[str, tuple[str, ...]] = {
    "claude": ("claude", "claude-code"),
    "codex": ("codex",),
    "gemini": ("gemini",),
}


class SingleSessionTrackingRuntime:
    """Continuously track one tmux-backed TUI session in-process."""

    def __init__(
        self,
        *,
        identity: HoumaoTrackedSessionIdentity,
        watch_poll_interval_seconds: float = 0.5,
        recent_transition_limit: int = 24,
        stability_threshold_seconds: float = 1.0,
        completion_stability_seconds: float = 1.0,
        unknown_to_stalled_timeout_seconds: float = 30.0,
        supported_tui_processes: dict[str, tuple[str, ...]] | None = None,
    ) -> None:
        """Initialize the single-session tracking runtime."""

        self.m_watch_poll_interval_seconds = watch_poll_interval_seconds
        self.m_transport_resolver = TmuxTransportResolver()
        self.m_process_inspector = PaneProcessInspector(
            supported_processes=supported_tui_processes or _DEFAULT_SUPPORTED_TUI_PROCESSES
        )
        self.m_parser_adapter = OfficialTuiParserAdapter()
        self.m_tracker = LiveSessionTracker(
            identity=identity,
            recent_transition_limit=recent_transition_limit,
            stability_threshold_seconds=stability_threshold_seconds,
            completion_stability_seconds=completion_stability_seconds,
            unknown_to_stalled_timeout_seconds=unknown_to_stalled_timeout_seconds,
        )
        self.m_stop_event = threading.Event()
        self.m_thread = threading.Thread(
            target=self._run,
            name=f"houmao-shared-track-{identity.tracked_session_id}",
            daemon=True,
        )
        self.m_started = False

    @property
    def identity(self) -> HoumaoTrackedSessionIdentity:
        """Return the current tracked session identity."""

        return self.m_tracker.current_state().tracked_session

    def start(self) -> None:
        """Start the background tracking loop."""

        if self.m_started:
            return
        self.m_started = True
        self.m_thread.start()

    def stop(self) -> None:
        """Stop the background tracking loop."""

        self.m_stop_event.set()
        if self.m_started:
            self.m_thread.join(timeout=2.0)

    def current_state(self) -> HoumaoTerminalStateResponse:
        """Return the latest tracked terminal state."""

        return self.m_tracker.current_state()

    def history(self, *, limit: int) -> HoumaoTerminalHistoryResponse:
        """Return bounded recent tracked history."""

        return self.m_tracker.history(limit=limit)

    def note_prompt_submission(self, *, message: str) -> HoumaoTerminalStateResponse:
        """Arm explicit-input tracking for one prompt submission."""

        return self.m_tracker.note_prompt_submission(
            message=message,
            observed_at_utc=utc_now_iso(),
            monotonic_ts=time.monotonic(),
        )

    def refresh_once(self) -> HoumaoTerminalStateResponse:
        """Run one immediate poll cycle and return the updated state."""

        self._poll_once()
        return self.m_tracker.current_state()

    def _run(self) -> None:
        """Poll continuously until shutdown."""

        while not self.m_stop_event.is_set():
            self._poll_once()
            self.m_stop_event.wait(self.m_watch_poll_interval_seconds)

    def _poll_once(self) -> None:
        """Poll the tracked tmux session once."""

        identity = self.m_tracker.current_state().tracked_session
        observed_at_utc = utc_now_iso()
        monotonic_ts = time.monotonic()

        if not tmux_session_exists(session_name=identity.tmux_session_name):
            self.m_tracker.record_cycle(
                identity=identity,
                observed_at_utc=observed_at_utc,
                monotonic_ts=monotonic_ts,
                transport_state="tmux_missing",
                process_state="unknown",
                parse_status="transport_unavailable",
                probe_snapshot=None,
                probe_error=None,
                parse_error=None,
                parsed_surface=None,
                output_text=None,
            )
            return

        try:
            target = self.m_transport_resolver.resolve_target(
                session_name=identity.tmux_session_name,
                window_name=identity.tmux_window_name,
            )
        except TmuxCommandError as exc:
            self.m_tracker.record_cycle(
                identity=identity,
                observed_at_utc=observed_at_utc,
                monotonic_ts=monotonic_ts,
                transport_state="probe_error",
                process_state="probe_error",
                parse_status="probe_error",
                probe_snapshot=None,
                probe_error=HoumaoErrorDetail(kind="tmux_probe_error", message=str(exc)),
                parse_error=None,
                parsed_surface=None,
                output_text=None,
            )
            return

        process_inspection = self.m_process_inspector.inspect(
            tool=identity.tool,
            pane_pid=target.pane.pane_pid,
        )
        probe_snapshot = HoumaoProbeSnapshot(
            observed_at_utc=observed_at_utc,
            pane_id=target.pane.pane_id,
            pane_pid=target.pane.pane_pid,
            matched_process_names=list(process_inspection.matched_process_names),
        )
        if process_inspection.process_state == "probe_error":
            self.m_tracker.record_cycle(
                identity=identity,
                observed_at_utc=observed_at_utc,
                monotonic_ts=monotonic_ts,
                transport_state="tmux_up",
                process_state="probe_error",
                parse_status="probe_error",
                probe_snapshot=probe_snapshot,
                probe_error=HoumaoErrorDetail(
                    kind="process_probe_error",
                    message=process_inspection.error_message or "Process inspection failed.",
                ),
                parse_error=None,
                parsed_surface=None,
                output_text=None,
            )
            return

        if process_inspection.process_state in {"unsupported_tool", "tui_down"}:
            self.m_tracker.record_cycle(
                identity=identity,
                observed_at_utc=observed_at_utc,
                monotonic_ts=monotonic_ts,
                transport_state="tmux_up",
                process_state=process_inspection.process_state,
                parse_status=(
                    "unsupported_tool"
                    if process_inspection.process_state == "unsupported_tool"
                    else "skipped_tui_down"
                ),
                probe_snapshot=probe_snapshot,
                probe_error=None,
                parse_error=None,
                parsed_surface=None,
                output_text=None,
            )
            return

        try:
            output_text = self.m_transport_resolver.capture_text(target=target)
        except TmuxCommandError as exc:
            self.m_tracker.record_cycle(
                identity=identity,
                observed_at_utc=observed_at_utc,
                monotonic_ts=monotonic_ts,
                transport_state="probe_error",
                process_state="probe_error",
                parse_status="probe_error",
                probe_snapshot=probe_snapshot,
                probe_error=HoumaoErrorDetail(kind="tmux_capture_error", message=str(exc)),
                parse_error=None,
                parsed_surface=None,
                output_text=None,
            )
            return

        probe_snapshot = probe_snapshot.model_copy(
            update={
                "captured_text_hash": hashlib.sha1(output_text.encode("utf-8")).hexdigest(),
                "captured_text_length": len(output_text),
                "captured_text_excerpt": output_text[-4000:],
            }
        )

        if not self.m_parser_adapter.supports_tool(tool=identity.tool):
            self.m_tracker.record_cycle(
                identity=identity,
                observed_at_utc=observed_at_utc,
                monotonic_ts=monotonic_ts,
                transport_state="tmux_up",
                process_state="unsupported_tool",
                parse_status="unsupported_tool",
                probe_snapshot=probe_snapshot,
                probe_error=None,
                parse_error=None,
                parsed_surface=None,
                output_text=output_text,
            )
            return

        baseline_pos = self.m_tracker.baseline_pos
        if baseline_pos is None:
            try:
                baseline_pos = self.m_parser_adapter.capture_baseline(
                    tool=identity.tool,
                    output_text=output_text,
                )
            except Exception as exc:
                self.m_tracker.record_cycle(
                    identity=identity,
                    observed_at_utc=observed_at_utc,
                    monotonic_ts=monotonic_ts,
                    transport_state="tmux_up",
                    process_state="tui_up",
                    parse_status="parse_error",
                    probe_snapshot=probe_snapshot,
                    probe_error=None,
                    parse_error=HoumaoErrorDetail(
                        kind="parse_baseline_error",
                        message=str(exc),
                    ),
                    parsed_surface=None,
                    output_text=output_text,
                )
                return
            self.m_tracker.set_baseline_pos(baseline_pos)

        parse_result = self.m_parser_adapter.parse(
            tool=identity.tool,
            output_text=output_text,
            baseline_pos=baseline_pos,
        )
        self.m_tracker.record_cycle(
            identity=identity,
            observed_at_utc=observed_at_utc,
            monotonic_ts=monotonic_ts,
            transport_state="tmux_up",
            process_state="tui_up",
            parse_status="parsed" if parse_result.parsed_surface is not None else "parse_error",
            probe_snapshot=probe_snapshot,
            probe_error=None,
            parse_error=parse_result.parse_error,
            parsed_surface=parse_result.parsed_surface,
            output_text=output_text,
        )
