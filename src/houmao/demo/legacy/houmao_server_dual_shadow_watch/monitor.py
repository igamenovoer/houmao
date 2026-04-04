"""Live Rich dashboard for the Houmao-server dual shadow-watch demo."""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from houmao.server.client import HoumaoServerClient
from houmao.server.models import HoumaoRecentTransition, HoumaoTerminalStateResponse

from houmao.demo.legacy.houmao_server_dual_shadow_watch.models import (
    HoumaoServerDualShadowWatchState,
    load_demo_state,
)

_STATE_STYLE_BY_CATEGORY: dict[str, dict[str, str]] = {
    "turn_phase": {
        "ready": "bold cyan",
        "active": "bold yellow",
        "unknown": "bold bright_black",
    },
    "last_turn_result": {
        "success": "bold green",
        "interrupted": "bold magenta",
        "known_failure": "bold red",
        "none": "bright_black",
    },
    "last_turn_source": {
        "explicit_input": "cyan",
        "surface_inference": "yellow",
        "none": "bright_black",
    },
    "diagnostics_availability": {
        "available": "green",
        "unavailable": "red",
        "tui_down": "red",
        "error": "bold red",
        "unknown": "bright_black",
    },
    "transport_state": {
        "tmux_up": "green",
        "tmux_missing": "red",
        "probe_error": "red",
        "error": "red",
    },
    "process_state": {
        "tui_up": "green",
        "tui_down": "red",
        "unsupported_tool": "magenta",
        "probe_error": "red",
        "unknown": "bright_black",
        "error": "red",
    },
    "parse_status": {
        "parsed": "green",
        "skipped_tui_down": "yellow",
        "unsupported_tool": "magenta",
        "transport_unavailable": "bright_black",
        "probe_error": "red",
        "parse_error": "red",
        "error": "red",
    },
    "tri_state": {
        "yes": "cyan",
        "no": "yellow",
        "unknown": "bright_black",
    },
    "availability": {
        "supported": "green",
        "unsupported": "magenta",
        "disconnected": "red",
        "unknown": "bright_black",
        "error": "red",
        "-": "bright_black",
    },
    "business_state": {
        "idle": "cyan",
        "working": "yellow",
        "awaiting_operator": "magenta",
        "unknown": "bright_black",
        "error": "red",
        "-": "bright_black",
    },
    "input_mode": {
        "freeform": "cyan",
        "modal": "yellow",
        "closed": "yellow",
        "unknown": "bright_black",
        "error": "red",
        "-": "bright_black",
    },
    "ui_context": {
        "normal_prompt": "cyan",
        "selection_menu": "yellow",
        "slash_command": "yellow",
        "unknown": "bright_black",
        "error": "red",
        "-": "bright_black",
    },
    "stability_state": {
        "stable": "green",
        "changing": "yellow",
        "-": "bright_black",
    },
}


@dataclass(frozen=True)
class AgentDisplayState:
    """Current operator-facing state for one monitored agent."""

    slot: str
    tool: str
    terminal_id: str
    tmux_session_name: str
    diagnostics_availability: str
    transport_state: str
    process_state: str
    parse_status: str
    accepting_input: str
    editing_input: str
    ready_posture: str
    parsed_availability: str
    business_state: str
    input_mode: str
    ui_context: str
    turn_phase: str
    last_turn_result: str
    last_turn_source: str
    visible_stable: bool | None
    visible_stable_for_seconds: float | None
    anomaly_codes: tuple[str, ...]
    dialog_tail: str
    detail: str
    last_transition_at_utc: str | None
    last_transition_summary: str | None
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
    """Poll server-owned tracked state, persist consumed evidence, and render the dashboard."""

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
                                diagnostics_availability="error",
                                transport_state="error",
                                process_state="error",
                                parse_status="error",
                                accepting_input="unknown",
                                editing_input="unknown",
                                ready_posture="unknown",
                                parsed_availability="error",
                                business_state="error",
                                input_mode="error",
                                ui_context="error",
                                turn_phase="unknown",
                                last_turn_result="none",
                                last_turn_source="none",
                                visible_stable=None,
                                visible_stable_for_seconds=None,
                                anomaly_codes=(),
                                dialog_tail="",
                                detail="Failed to fetch terminal state from houmao-server.",
                                last_transition_at_utc=None,
                                last_transition_summary=None,
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
        transitions: list[HoumaoRecentTransition],
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
                changed_fields=tuple(transition.changed_fields),
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
    last_transition = state.recent_transitions[-1] if state.recent_transitions else None
    error_detail = state.diagnostics.parse_error or state.diagnostics.probe_error
    return AgentDisplayState(
        slot=slot,
        tool=state.tracked_session.tool,
        terminal_id=state.terminal_id,
        tmux_session_name=state.tracked_session.tmux_session_name,
        diagnostics_availability=state.diagnostics.availability,
        transport_state=state.diagnostics.transport_state,
        process_state=state.diagnostics.process_state,
        parse_status=state.diagnostics.parse_status,
        accepting_input=state.surface.accepting_input,
        editing_input=state.surface.editing_input,
        ready_posture=state.surface.ready_posture,
        parsed_availability=parsed_surface.availability if parsed_surface is not None else "-",
        business_state=parsed_surface.business_state if parsed_surface is not None else "-",
        input_mode=parsed_surface.input_mode if parsed_surface is not None else "-",
        ui_context=parsed_surface.ui_context if parsed_surface is not None else "-",
        turn_phase=state.turn.phase,
        last_turn_result=state.last_turn.result,
        last_turn_source=state.last_turn.source,
        visible_stable=state.stability.stable,
        visible_stable_for_seconds=state.stability.stable_for_seconds,
        anomaly_codes=tuple(parsed_surface.anomaly_codes) if parsed_surface is not None else (),
        dialog_tail=parsed_surface.dialog_tail if parsed_surface is not None else "",
        detail=_detail_from_terminal(state),
        last_transition_at_utc=last_transition.recorded_at_utc
        if last_transition is not None
        else None,
        last_transition_summary=last_transition.summary if last_transition is not None else None,
        error_detail=error_detail.message if error_detail is not None else None,
    )


def _detail_from_terminal(state: HoumaoTerminalStateResponse) -> str:
    """Build one concise operator-facing detail string."""

    if state.diagnostics.probe_error is not None:
        return state.diagnostics.probe_error.message
    if state.diagnostics.parse_error is not None:
        return state.diagnostics.parse_error.message
    if state.diagnostics.availability == "unavailable":
        return "Tracked tmux session is no longer live."
    if state.diagnostics.availability == "tui_down":
        return "Supported TUI process is not running in the tracked tmux pane."
    if state.diagnostics.availability == "error":
        return "The current sample could not be observed or parsed cleanly."
    if state.turn.phase == "active":
        return "Tracker has enough evidence that a turn is currently in flight."
    if state.turn.phase == "ready" and state.last_turn.result == "success":
        return "Latest turn settled successfully and the terminal looks ready again."
    if state.turn.phase == "ready":
        return "Terminal looks ready for the next turn."
    return "Tracker cannot safely classify the current turn posture."


def _render_dashboard(
    *,
    demo_state: HoumaoServerDualShadowWatchState,
    display_states: list[AgentDisplayState],
    transitions: list[ServerTransitionEvent],
) -> Layout:
    """Build the live Rich layout for the current monitor state."""

    layout = Layout()
    layout.split_column(
        Layout(name="header", size=6),
        Layout(name="agents", size=20),
        Layout(name="transitions"),
    )
    layout["header"].update(
        _render_header_panel(demo_state=demo_state, display_states=display_states)
    )
    layout["agents"].update(_render_agents_panel(display_states))
    layout["transitions"].update(
        _render_transition_panel(demo_state=demo_state, transitions=transitions)
    )
    return layout


def _render_header_panel(
    *,
    demo_state: HoumaoServerDualShadowWatchState,
    display_states: list[AgentDisplayState],
) -> Panel:
    """Render a short top-level monitor summary."""

    lines = [
        Text(f"server: {demo_state.server.api_base_url}"),
        Text(_monitor_cadence_summary(demo_state)),
        Text(_server_posture_summary(demo_state)),
        _header_current_states_text(display_states),
    ]
    return Panel(Group(*lines), title="Houmao Server State Watch")


def _render_agent_panel(state: AgentDisplayState) -> Panel:
    """Render one compact per-agent status card."""

    lines = [
        _current_text(state, prefix="current: "),
        _last_turn_text(state, prefix="last turn: "),
        _diagnostics_text(state, prefix="diagnostics: "),
        _surface_observables_text(state, prefix="surface: "),
        _surface_text(state, prefix="parsed surface: "),
        _stability_text(state, prefix="visible stability: "),
        Text(f"detail: {_truncate_text(state.detail, limit=120)}"),
        Text(f"last transition: {_last_transition_summary(state)}"),
        Text(f"tail: {_compact_dialog_excerpt(state.dialog_tail)}"),
    ]
    if state.error_detail:
        lines.append(Text(f"error: {_truncate_text(state.error_detail, limit=120)}"))
    elif _should_show_anomalies(state):
        lines.append(Text(f"anomalies: {','.join(state.anomaly_codes[-3:])}"))
    return Panel(Group(*lines), title=f"{state.slot} ({state.tool})")


def _render_agents_panel(display_states: list[AgentDisplayState]) -> Panel:
    """Render all agents in one stacked status panel for narrow tmux panes."""

    body_lines: list[Text] = []
    for index, state in enumerate(display_states):
        if index > 0:
            body_lines.append(Text(""))
        body_lines.extend(_agent_panel_lines(state))
    return Panel(Group(*body_lines), title="Agent Status")


def _agent_panel_lines(state: AgentDisplayState) -> list[Text]:
    """Build compact status lines for one agent."""

    lines = [
        _agent_heading_text(state),
        _current_health_text(state, prefix="  current: "),
        _last_turn_text(state, prefix="  last turn: "),
        _surface_observables_text(state, prefix="  surface: "),
        _surface_text(state, prefix="  parsed surface: "),
        _stability_text(state, prefix="  visible stability: "),
        Text(f"  detail: {_truncate_text(state.detail, limit=120)}"),
        Text(f"  last: {_last_transition_summary(state)}"),
        Text(f"  tail: {_compact_dialog_excerpt(state.dialog_tail)}"),
    ]
    if state.error_detail:
        lines.append(Text(f"  error: {_truncate_text(state.error_detail, limit=120)}"))
    elif _should_show_anomalies(state):
        lines.append(Text(f"  anomalies: {','.join(state.anomaly_codes[-3:])}"))
    return lines


def _render_transition_panel(
    *,
    demo_state: HoumaoServerDualShadowWatchState,
    transitions: list[ServerTransitionEvent],
) -> Panel:
    """Render the rolling transition log."""

    body_lines = [
        Text(_monitor_cadence_summary(demo_state)),
        Text(_server_posture_summary(demo_state)),
    ]
    if not transitions:
        body_lines.append(Text("No server-authored transitions yet."))
    for event in transitions[-6:]:
        short_ts = _short_timestamp(event.ts_utc)
        line = Text()
        if short_ts:
            line.append(f"{short_ts} ", style="dim")
        line.append(f"{event.slot}:", style="bold")
        line.append(f" {_truncate_text(event.summary, limit=120)}")
        body_lines.append(line)
    return Panel(Group(*body_lines), title="Recent Server Transitions")


def _monitor_cadence_summary(demo_state: HoumaoServerDualShadowWatchState) -> str:
    """Render the monitor-local polling cadence."""

    return f"monitor: poll={demo_state.poll_interval_seconds:.1f}s"


def _server_posture_summary(demo_state: HoumaoServerDualShadowWatchState) -> str:
    """Render the server-owned timing posture for the run."""

    return (
        "server posture: "
        f"completion_debounce={demo_state.completion_stability_seconds:.1f}s  "
        f"unknown->stalled={demo_state.unknown_to_stalled_timeout_seconds:.1f}s"
    )


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


def _header_current_states_text(display_states: list[AgentDisplayState]) -> Text:
    """Render the header summary with colored current state tokens."""

    line = Text("current: ")
    if not display_states:
        line.append("no agents", style="bright_black")
        return line
    for index, state in enumerate(display_states):
        if index > 0:
            line.append(" | ")
        line.append(f"{state.slot}: ", style="bold")
        line.append_text(_styled_token(state.turn_phase, category="turn_phase"))
        line.append(" (last=")
        line.append_text(_styled_token(state.last_turn_result, category="last_turn_result"))
        line.append(", ready=")
        line.append_text(_styled_token(state.ready_posture, category="tri_state"))
        line.append(")")
    return line


def _agent_heading_text(state: AgentDisplayState) -> Text:
    """Render the compact agent heading."""

    heading = Text()
    heading.append(state.slot, style="bold")
    heading.append(f" ({state.tool})")
    return heading


def _current_text(state: AgentDisplayState, *, prefix: str) -> Text:
    """Render the public turn-phase line."""

    line = Text(prefix)
    line.append_text(_styled_token(state.turn_phase, category="turn_phase"))
    return line


def _last_turn_text(state: AgentDisplayState, *, prefix: str) -> Text:
    """Render the sticky last-turn outcome line."""

    line = Text(prefix)
    line.append_text(_styled_token(state.last_turn_result, category="last_turn_result"))
    line.append(" / ")
    line.append_text(_styled_token(state.last_turn_source, category="last_turn_source"))
    return line


def _diagnostics_text(state: AgentDisplayState, *, prefix: str) -> Text:
    """Render diagnostic availability and low-level transport state."""

    line = Text(prefix)
    line.append_text(
        _styled_token(state.diagnostics_availability, category="diagnostics_availability")
    )
    line.append(" | ")
    line.append_text(_styled_token(state.transport_state, category="transport_state"))
    line.append(" / ")
    line.append_text(_styled_token(state.process_state, category="process_state"))
    line.append(" / ")
    line.append_text(_styled_token(state.parse_status, category="parse_status"))
    return line


def _surface_observables_text(state: AgentDisplayState, *, prefix: str) -> Text:
    """Render foundational surface observables."""

    line = Text(prefix)
    line.append("accepting=")
    line.append_text(_styled_token(state.accepting_input, category="tri_state"))
    line.append(" / editing=")
    line.append_text(_styled_token(state.editing_input, category="tri_state"))
    line.append(" / ready=")
    line.append_text(_styled_token(state.ready_posture, category="tri_state"))
    return line


def _surface_text(state: AgentDisplayState, *, prefix: str) -> Text:
    """Render the parsed surface summary with colored state tokens."""

    line = Text(prefix)
    line.append_text(_styled_token(state.parsed_availability, category="availability"))
    line.append(" / ")
    line.append_text(_styled_token(state.business_state, category="business_state"))
    line.append(" / ")
    line.append_text(_styled_token(state.input_mode, category="input_mode"))
    line.append(" / ")
    line.append_text(_styled_token(state.ui_context, category="ui_context"))
    return line


def _stability_text(state: AgentDisplayState, *, prefix: str) -> Text:
    """Render visible stability with color-coded posture."""

    line = Text(prefix)
    if state.visible_stable is None or state.visible_stable_for_seconds is None:
        line.append_text(_styled_token("-", category="stability_state"))
        return line
    posture = "stable" if state.visible_stable else "changing"
    line.append_text(_styled_token(posture, category="stability_state"))
    line.append(f" for {_format_seconds(state.visible_stable_for_seconds)}s")
    return line


def _current_health_text(state: AgentDisplayState, *, prefix: str) -> Text:
    """Render the compact top-line state for one agent."""

    line = Text(prefix)
    line.append_text(_styled_token(state.turn_phase, category="turn_phase"))
    line.append(" | ")
    line.append_text(
        _styled_token(state.diagnostics_availability, category="diagnostics_availability")
    )
    line.append(" | ")
    line.append_text(_styled_token(state.transport_state, category="transport_state"))
    line.append("/")
    line.append_text(_styled_token(state.process_state, category="process_state"))
    line.append("/")
    line.append_text(_styled_token(state.parse_status, category="parse_status"))
    return line


def _styled_token(value: str, *, category: str) -> Text:
    """Return one token wrapped in its configured Rich style."""

    return Text(value, style=_state_style(category=category, value=value))


def _state_style(*, category: str, value: str) -> str:
    """Return the Rich style name for one categorized state value."""

    return _STATE_STYLE_BY_CATEGORY.get(category, {}).get(value, "white")


def _last_transition_summary(state: AgentDisplayState) -> str:
    """Render a compact last-transition summary for one agent."""

    if state.last_transition_summary is None:
        return "none"
    short_ts = _short_timestamp(state.last_transition_at_utc)
    if short_ts is None:
        return _truncate_text(state.last_transition_summary, limit=120)
    return f"{short_ts} {_truncate_text(state.last_transition_summary, limit=120)}"


def _short_timestamp(ts_utc: str | None) -> str | None:
    """Return a compact `HH:MM:SS` timestamp when possible."""

    if ts_utc is None:
        return None
    try:
        return datetime.fromisoformat(ts_utc).astimezone(UTC).strftime("%H:%M:%S")
    except ValueError:
        return ts_utc


def _truncate_text(value: str, *, limit: int) -> str:
    """Truncate one long string for dashboard display."""

    collapsed = " ".join(value.split())
    if len(collapsed) <= limit:
        return collapsed
    return f"{collapsed[: limit - 1]}…"


def _compact_dialog_excerpt(dialog_tail: str) -> str:
    """Collapse one dialog tail into a compact single-line excerpt."""

    fragments: list[str] = []
    for raw_line in dialog_tail.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        if stripped.startswith("│") and stripped.endswith("│"):
            continue
        if set(stripped) <= {"│", "─", "╭", "╮", "╰", "╯", "┌", "┐", "└", "┘", " "}:
            continue
        fragments.append(stripped)
    if not fragments:
        return "-"
    return _truncate_text(" | ".join(fragments[-3:]), limit=140)


def _should_show_anomalies(state: AgentDisplayState) -> bool:
    """Return whether anomalies add value for the current display state."""

    if not state.anomaly_codes:
        return False
    return state.diagnostics_availability in {"unknown", "error"} or state.turn_phase == "unknown"
