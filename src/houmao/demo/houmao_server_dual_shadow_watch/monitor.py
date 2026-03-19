"""Live Rich dashboard for the Houmao-server dual shadow-watch demo."""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rich.columns import Columns
from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from houmao.server.client import HoumaoServerClient
from houmao.server.models import HoumaoRecentTransition, HoumaoTerminalStateResponse

from houmao.demo.houmao_server_dual_shadow_watch.models import (
    HoumaoServerDualShadowWatchState,
    load_demo_state,
)


@dataclass(frozen=True)
class AgentDisplayState:
    """Current operator-facing state for one monitored agent."""

    slot: str
    tool: str
    terminal_id: str
    tmux_session_name: str
    transport_state: str
    process_state: str
    parse_status: str
    availability: str
    business_state: str
    input_mode: str
    ui_context: str
    readiness_state: str
    completion_state: str
    readiness_unknown_elapsed_seconds: float | None
    completion_unknown_elapsed_seconds: float | None
    completion_candidate_elapsed_seconds: float | None
    projection_changed: bool
    anomaly_codes: tuple[str, ...]
    dialog_tail: str
    detail: str
    error_detail: str | None = None


@dataclass(frozen=True)
class ServerTransitionEvent:
    """Thin demo wrapper around one server-authored transition."""

    ts_utc: str
    slot: str
    tool: str
    terminal_id: str
    summary: str
    changed_fields: tuple[str, ...]

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-serializable transition payload."""

        return {
            "ts_utc": self.ts_utc,
            "slot": self.slot,
            "tool": self.tool,
            "terminal_id": self.terminal_id,
            "summary": self.summary,
            "changed_fields": list(self.changed_fields),
        }


class ShadowWatchMonitor:
    """Own the polling loop, NDJSON evidence, and live Rich dashboard."""

    def __init__(self, *, state_file: Path, dashboard_log_path: Path | None = None) -> None:
        self.m_state_file = state_file.resolve()
        self.m_state = load_demo_state(self.m_state_file)
        self.m_console = Console()
        self.m_dashboard_log_path = (
            dashboard_log_path.resolve() if dashboard_log_path is not None else None
        )
        self.m_client = HoumaoServerClient(self.m_state.server.api_base_url, timeout_seconds=2.0)
        self.m_transition_log: list[ServerTransitionEvent] = []
        self.m_seen_transition_keys: set[tuple[str, str, str]] = set()

    def run(self, *, max_iterations: int | None = None) -> int:
        """Run the live dashboard until interrupted or max iterations elapse."""

        samples_path = Path(self.m_state.monitor.samples_path)
        transitions_path = Path(self.m_state.monitor.transitions_path)
        samples_path.parent.mkdir(parents=True, exist_ok=True)
        transitions_path.parent.mkdir(parents=True, exist_ok=True)

        iteration = 0
        with Live(console=self.m_console, refresh_per_second=4, screen=False) as live:
            while True:
                started_at = time.monotonic()
                display_states: list[AgentDisplayState] = []
                for slot in sorted(self.m_state.agents):
                    session = self.m_state.agents[slot]
                    ts_utc = _now_utc_iso()
                    try:
                        terminal_state = self.m_client.terminal_state(session.terminal_id)
                    except Exception as exc:
                        _append_ndjson(
                            samples_path,
                            {
                                "ts_utc": ts_utc,
                                "slot": slot,
                                "terminal_id": session.terminal_id,
                                "error": str(exc),
                            },
                        )
                        display_states.append(
                            AgentDisplayState(
                                slot=slot,
                                tool=session.tool,
                                terminal_id=session.terminal_id,
                                tmux_session_name=session.tmux_session_name,
                                transport_state="error",
                                process_state="error",
                                parse_status="error",
                                availability="error",
                                business_state="error",
                                input_mode="error",
                                ui_context="error",
                                readiness_state="error",
                                completion_state="error",
                                readiness_unknown_elapsed_seconds=None,
                                completion_unknown_elapsed_seconds=None,
                                completion_candidate_elapsed_seconds=None,
                                projection_changed=False,
                                anomaly_codes=(),
                                dialog_tail="",
                                detail="Failed to fetch terminal state from houmao-server.",
                                error_detail=str(exc),
                            )
                        )
                        continue

                    _append_ndjson(
                        samples_path,
                        {
                            "ts_utc": ts_utc,
                            "slot": slot,
                            "terminal_id": session.terminal_id,
                            "terminal_state": terminal_state.model_dump(mode="json"),
                        },
                    )
                    self._record_transitions(
                        slot=slot,
                        terminal_id=session.terminal_id,
                        tool=session.tool,
                        transitions=terminal_state.recent_transitions,
                        transitions_path=transitions_path,
                    )
                    display_states.append(
                        _display_state_from_terminal(slot=slot, state=terminal_state)
                    )

                live.update(
                    _render_dashboard(
                        demo_state=self.m_state,
                        display_states=display_states,
                        transitions=self.m_transition_log,
                    )
                )
                if self.m_dashboard_log_path is not None:
                    self.m_dashboard_log_path.parent.mkdir(parents=True, exist_ok=True)
                    with self.m_dashboard_log_path.open("a", encoding="utf-8") as handle:
                        handle.write(f"[{_now_utc_iso()}] dashboard refreshed\n")

                iteration += 1
                if max_iterations is not None and iteration >= max_iterations:
                    return 0
                elapsed = time.monotonic() - started_at
                time.sleep(max(self.m_state.poll_interval_seconds - elapsed, 0.0))

    def _record_transitions(
        self,
        *,
        slot: str,
        terminal_id: str,
        tool: str,
        transitions: tuple[HoumaoRecentTransition, ...],
        transitions_path: Path,
    ) -> None:
        """Record unseen server-authored transitions."""

        for transition in transitions:
            key = (slot, transition.recorded_at_utc, transition.summary)
            if key in self.m_seen_transition_keys:
                continue
            self.m_seen_transition_keys.add(key)
            event = ServerTransitionEvent(
                ts_utc=transition.recorded_at_utc,
                slot=slot,
                tool=tool,
                terminal_id=terminal_id,
                summary=transition.summary,
                changed_fields=transition.changed_fields,
            )
            self.m_transition_log.append(event)
            self.m_transition_log = self.m_transition_log[-20:]
            _append_ndjson(transitions_path, event.to_payload())


def main(argv: list[str] | None = None) -> int:
    """Run the standalone monitor entrypoint."""

    parser = argparse.ArgumentParser(
        description="Live Rich dashboard for Houmao-server dual shadow watch."
    )
    parser.add_argument("--state-file", type=Path, required=True)
    parser.add_argument("--dashboard-log-path", type=Path)
    parser.add_argument("--max-iterations", type=int)
    args = parser.parse_args(argv)
    monitor = ShadowWatchMonitor(
        state_file=args.state_file,
        dashboard_log_path=args.dashboard_log_path,
    )
    try:
        return monitor.run(max_iterations=args.max_iterations)
    except KeyboardInterrupt:
        return 0


def _display_state_from_terminal(
    *, slot: str, state: HoumaoTerminalStateResponse
) -> AgentDisplayState:
    """Convert one terminal-state payload into display-friendly fields."""

    parsed_surface = state.parsed_surface
    return AgentDisplayState(
        slot=slot,
        tool=state.tracked_session.tool,
        terminal_id=state.terminal_id,
        tmux_session_name=state.tracked_session.tmux_session_name,
        transport_state=state.transport_state,
        process_state=state.process_state,
        parse_status=state.parse_status,
        availability=parsed_surface.availability if parsed_surface is not None else "-",
        business_state=parsed_surface.business_state if parsed_surface is not None else "-",
        input_mode=parsed_surface.input_mode if parsed_surface is not None else "-",
        ui_context=parsed_surface.ui_context if parsed_surface is not None else "-",
        readiness_state=state.operator_state.readiness_state,
        completion_state=state.operator_state.completion_state,
        readiness_unknown_elapsed_seconds=state.lifecycle_timing.readiness_unknown_elapsed_seconds,
        completion_unknown_elapsed_seconds=state.lifecycle_timing.completion_unknown_elapsed_seconds,
        completion_candidate_elapsed_seconds=state.lifecycle_timing.completion_candidate_elapsed_seconds,
        projection_changed=state.operator_state.projection_changed,
        anomaly_codes=parsed_surface.anomaly_codes if parsed_surface is not None else (),
        dialog_tail=parsed_surface.dialog_tail if parsed_surface is not None else "",
        detail=state.operator_state.detail,
        error_detail=(state.parse_error or state.probe_error).message
        if (state.parse_error or state.probe_error) is not None
        else None,
    )


def _render_dashboard(
    *,
    demo_state: HoumaoServerDualShadowWatchState,
    display_states: list[AgentDisplayState],
    transitions: list[ServerTransitionEvent],
) -> Layout:
    """Build the live Rich layout for the current monitor state."""

    layout = Layout()
    layout.split_column(
        Layout(name="summary", size=10),
        Layout(name="details", size=16),
        Layout(name="transitions"),
    )
    layout["summary"].update(_render_summary_table(display_states=display_states))
    layout["details"].update(
        Columns(
            [_render_detail_panel(state) for state in display_states],
            equal=True,
            expand=True,
        )
    )
    layout["transitions"].update(
        _render_transition_panel(demo_state=demo_state, transitions=transitions)
    )
    return layout


def _render_summary_table(*, display_states: list[AgentDisplayState]) -> Panel:
    """Render the compact top-level state table."""

    table = Table(expand=True)
    for column in (
        "slot",
        "transport",
        "process",
        "parse",
        "availability",
        "business",
        "input",
        "readiness",
        "completion",
        "unknown_s",
        "candidate_s",
        "projection_changed",
        "anomalies",
    ):
        table.add_column(column)
    for state in display_states:
        unknown_seconds = state.readiness_unknown_elapsed_seconds
        if unknown_seconds is None:
            unknown_seconds = state.completion_unknown_elapsed_seconds
        table.add_row(
            state.slot,
            state.transport_state,
            state.process_state,
            state.parse_status,
            state.availability,
            state.business_state,
            state.input_mode,
            state.readiness_state,
            state.completion_state,
            _format_seconds(unknown_seconds),
            _format_seconds(state.completion_candidate_elapsed_seconds),
            str(state.projection_changed),
            ",".join(state.anomaly_codes[-4:]) if state.anomaly_codes else "-",
        )
    return Panel(table, title="Houmao Server Shadow Watch Summary")


def _render_detail_panel(state: AgentDisplayState) -> Panel:
    """Render one per-agent detail panel."""

    lines = [
        Text(f"tmux: {state.tmux_session_name}"),
        Text(f"terminal: {state.terminal_id}"),
        Text(
            "transport/process/parse: "
            f"{state.transport_state} / {state.process_state} / {state.parse_status}"
        ),
        Text(
            "parser surface: "
            f"{state.availability} / {state.business_state} / {state.input_mode} / {state.ui_context}"
        ),
        Text(
            "lifecycle: "
            f"{state.readiness_state} / {state.completion_state} "
            f"(unknown={_format_seconds(state.readiness_unknown_elapsed_seconds or state.completion_unknown_elapsed_seconds)}, "
            f"candidate={_format_seconds(state.completion_candidate_elapsed_seconds)})"
        ),
        Text(f"detail: {state.detail}"),
        Text(f"tail: {state.dialog_tail or '<empty>'}"),
    ]
    if state.error_detail:
        lines.append(Text(f"error: {state.error_detail}"))
    return Panel(Group(*lines), title=f"{state.tool} ({state.slot})")


def _render_transition_panel(
    *,
    demo_state: HoumaoServerDualShadowWatchState,
    transitions: list[ServerTransitionEvent],
) -> Panel:
    """Render the rolling transition log."""

    header = Text(
        "poll="
        f"{demo_state.poll_interval_seconds:.1f}s "
        f"stable={demo_state.completion_stability_seconds:.1f}s "
        f"unknown->stalled={demo_state.unknown_to_stalled_timeout_seconds:.1f}s"
    )
    body_lines = [header, Text("")]
    if not transitions:
        body_lines.append(Text("No server-authored transitions yet."))
    for event in transitions[-10:]:
        body_lines.append(Text(f"{event.ts_utc} [{event.slot}] {event.summary}"))
    return Panel(Group(*body_lines), title="Server Transitions")


def _append_ndjson(path: Path, payload: dict[str, Any]) -> None:
    """Append one JSON object as a single NDJSON line."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def _now_utc_iso() -> str:
    """Return one current UTC timestamp string."""

    return datetime.now(UTC).isoformat(timespec="seconds")


def _format_seconds(value: float | None) -> str:
    """Render one optional duration value for the summary table."""

    if value is None:
        return "-"
    return f"{value:.1f}"
