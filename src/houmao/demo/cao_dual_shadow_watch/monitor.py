"""Live `rich` dashboard for the dual-agent shadow-watch demo."""

from __future__ import annotations

import argparse
import json
import time
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

from houmao.agents.realm_controller.backends.shadow_parser_core import (
    ANOMALY_STALLED_ENTERED,
    ANOMALY_STALLED_RECOVERED,
    ShadowParserError,
)
from houmao.agents.realm_controller.backends.shadow_parser_stack import (
    ShadowParserStack,
    as_shadow_parser_error,
)
from houmao.cao.rest_client import CaoApiError, CaoRestClient

from houmao.demo.cao_dual_shadow_watch.models import (
    AgentDashboardState,
    AgentSessionState,
    MonitorObservation,
    MonitorTransitionEvent,
    DualShadowWatchDemoState,
    load_demo_state,
)


ANOMALY_CAO_FETCH_ERROR = "cao_fetch_error"
ANOMALY_SHADOW_PARSE_ERROR = "shadow_parse_error"
READINESS_STATES = ("ready", "waiting", "blocked", "failed", "unknown", "stalled")
COMPLETION_STATES = (
    "inactive",
    "in_progress",
    "candidate_complete",
    "completed",
    "waiting",
    "blocked",
    "failed",
    "unknown",
    "stalled",
)


class AgentStateTracker:
    """State machine that mirrors shadow-only readiness/completion semantics."""

    def __init__(
        self,
        *,
        session: AgentSessionState,
        completion_stability_seconds: float,
        unknown_to_stalled_timeout_seconds: float,
    ) -> None:
        self.m_session = session
        self.m_completion_stability_seconds = completion_stability_seconds
        self.m_unknown_to_stalled_timeout_seconds = unknown_to_stalled_timeout_seconds
        self.m_previous_state: AgentDashboardState | None = None
        self.m_readiness_unknown_started_at: float | None = None
        self.m_readiness_stalled = False
        self.m_completion_unknown_started_at: float | None = None
        self.m_completion_stalled = False
        self.m_last_ready_projection_key: str | None = None
        self.m_cycle_baseline_projection_key: str | None = None
        self.m_cycle_frozen_projection_key: str | None = None
        self.m_cycle_saw_working = False
        self.m_cycle_saw_projection_change = False
        self.m_candidate_started_at: float | None = None
        self.m_candidate_signature: tuple[object, ...] | None = None
        self.m_last_business_state: str | None = None

    def observe(
        self,
        observation: MonitorObservation,
    ) -> tuple[AgentDashboardState, MonitorTransitionEvent | None]:
        """Consume one monitor observation and emit the current dashboard state."""

        tick_anomalies = list(observation.anomaly_codes)
        readiness_state, readiness_unknown_elapsed = self._reduce_readiness(
            observation=observation,
            tick_anomalies=tick_anomalies,
        )
        completion_state, completion_unknown_elapsed, stable_elapsed, projection_changed = (
            self._reduce_completion(
                observation=observation,
                tick_anomalies=tick_anomalies,
            )
        )
        state = AgentDashboardState(
            slot=observation.slot,
            tool=observation.tool,
            terminal_id=observation.terminal_id,
            tmux_session_name=observation.tmux_session_name,
            cao_status=observation.cao_status,
            parser_family=observation.parser_family,
            parser_preset_id=observation.parser_preset_id,
            parser_preset_version=observation.parser_preset_version,
            availability=observation.availability,
            business_state=observation.business_state,
            input_mode=observation.input_mode,
            ui_context=observation.ui_context,
            readiness_state=readiness_state,
            completion_state=completion_state,
            unknown_elapsed_seconds=readiness_unknown_elapsed or completion_unknown_elapsed,
            stable_elapsed_seconds=stable_elapsed,
            projection_changed=projection_changed,
            baseline_invalidated=observation.baseline_invalidated,
            anomaly_codes=tuple(tick_anomalies),
            dialog_tail=observation.dialog_tail,
            operator_blocked_excerpt=observation.operator_blocked_excerpt,
            error_detail=observation.error_detail,
        )
        transition = self._build_transition(state)
        self.m_previous_state = state
        self.m_last_business_state = observation.business_state
        return state, transition

    def _reduce_readiness(
        self,
        *,
        observation: MonitorObservation,
        tick_anomalies: list[str],
    ) -> tuple[str, float | None]:
        """Update readiness state from one observation."""

        classification = _classify_readiness(observation)
        if classification == "unknown":
            if self.m_readiness_unknown_started_at is None:
                self.m_readiness_unknown_started_at = observation.monotonic_ts
            elapsed = observation.monotonic_ts - self.m_readiness_unknown_started_at
            if elapsed >= self.m_unknown_to_stalled_timeout_seconds:
                if not self.m_readiness_stalled:
                    tick_anomalies.append(ANOMALY_STALLED_ENTERED)
                self.m_readiness_stalled = True
                return "stalled", elapsed
            return "unknown", elapsed

        if self.m_readiness_stalled:
            tick_anomalies.append(ANOMALY_STALLED_RECOVERED)
        self.m_readiness_unknown_started_at = None
        self.m_readiness_stalled = False
        return classification, None

    def _reduce_completion(
        self,
        *,
        observation: MonitorObservation,
        tick_anomalies: list[str],
    ) -> tuple[str, float | None, float | None, bool]:
        """Update completion state from one observation."""

        classification = _classify_completion_surface(observation)
        if classification == "unknown":
            if self.m_completion_unknown_started_at is None:
                self.m_completion_unknown_started_at = observation.monotonic_ts
            elapsed = observation.monotonic_ts - self.m_completion_unknown_started_at
            if elapsed >= self.m_unknown_to_stalled_timeout_seconds:
                if not self.m_completion_stalled:
                    tick_anomalies.append(ANOMALY_STALLED_ENTERED)
                self.m_completion_stalled = True
                return "stalled", elapsed, None, self.m_cycle_saw_projection_change
            return "unknown", elapsed, None, self.m_cycle_saw_projection_change

        if self.m_completion_stalled:
            tick_anomalies.append(ANOMALY_STALLED_RECOVERED)
        self.m_completion_unknown_started_at = None
        self.m_completion_stalled = False

        if _is_submit_ready(observation):
            self.m_last_ready_projection_key = observation.normalized_projection_text

        if classification in {"failed", "blocked"}:
            self.m_candidate_started_at = None
            self.m_candidate_signature = None
            return classification, None, None, self.m_cycle_saw_projection_change

        transitioned_into_working = observation.business_state == "working" and (
            self.m_last_business_state != "working"
        )
        if transitioned_into_working:
            self.m_cycle_baseline_projection_key = (
                self.m_last_ready_projection_key or observation.normalized_projection_text
            )
            self.m_cycle_frozen_projection_key = None
            self.m_cycle_saw_working = False
            self.m_cycle_saw_projection_change = False
            self.m_candidate_started_at = None
            self.m_candidate_signature = None

        effective_projection_key = observation.normalized_projection_text
        if observation.baseline_invalidated:
            if self.m_cycle_frozen_projection_key is None:
                self.m_cycle_frozen_projection_key = effective_projection_key
            effective_projection_key = self.m_cycle_frozen_projection_key
        elif self.m_cycle_frozen_projection_key is not None:
            effective_projection_key = self.m_cycle_frozen_projection_key

        if observation.business_state == "working":
            if self.m_cycle_baseline_projection_key is None:
                self.m_cycle_baseline_projection_key = (
                    self.m_last_ready_projection_key or observation.normalized_projection_text
                )
            self.m_cycle_saw_working = True
            self.m_candidate_started_at = None
            self.m_candidate_signature = None
            return "in_progress", None, None, self.m_cycle_saw_projection_change

        if self.m_cycle_baseline_projection_key is not None:
            self.m_cycle_saw_projection_change = self.m_cycle_saw_projection_change or (
                effective_projection_key != self.m_cycle_baseline_projection_key
            )

        if _is_submit_ready(observation) and (
            self.m_cycle_saw_working or self.m_cycle_saw_projection_change
        ):
            signature = (
                observation.availability,
                observation.business_state,
                observation.input_mode,
                effective_projection_key,
                self.m_cycle_saw_working,
                self.m_cycle_saw_projection_change,
            )
            if signature != self.m_candidate_signature:
                self.m_candidate_signature = signature
                self.m_candidate_started_at = observation.monotonic_ts
            assert self.m_candidate_started_at is not None
            stable_elapsed = observation.monotonic_ts - self.m_candidate_started_at
            if stable_elapsed >= self.m_completion_stability_seconds:
                return "completed", None, stable_elapsed, self.m_cycle_saw_projection_change
            return "candidate_complete", None, stable_elapsed, self.m_cycle_saw_projection_change

        self.m_candidate_started_at = None
        self.m_candidate_signature = None
        if self.m_cycle_baseline_projection_key is None:
            return "inactive", None, None, self.m_cycle_saw_projection_change
        return "waiting", None, None, self.m_cycle_saw_projection_change

    def _build_transition(self, state: AgentDashboardState) -> MonitorTransitionEvent | None:
        """Return one transition event when the visible state signature changes."""

        previous = self.m_previous_state
        if previous is None:
            return MonitorTransitionEvent(
                ts_utc=_now_utc_iso(),
                slot=state.slot,
                tool=state.tool,
                summary=(
                    f"{state.slot}: initialized readiness={state.readiness_state}, "
                    f"completion={state.completion_state}, "
                    f"surface={state.business_state}+{state.input_mode}"
                ),
                changed_fields=("initialized",),
            )
        if previous.transition_signature() == state.transition_signature():
            return None

        changed_fields: list[str] = []
        field_pairs = [
            ("cao_status", previous.cao_status, state.cao_status),
            ("availability", previous.availability, state.availability),
            ("business_state", previous.business_state, state.business_state),
            ("input_mode", previous.input_mode, state.input_mode),
            ("ui_context", previous.ui_context, state.ui_context),
            ("readiness_state", previous.readiness_state, state.readiness_state),
            ("completion_state", previous.completion_state, state.completion_state),
            ("projection_changed", previous.projection_changed, state.projection_changed),
            ("baseline_invalidated", previous.baseline_invalidated, state.baseline_invalidated),
            ("anomaly_codes", previous.anomaly_codes, state.anomaly_codes),
            ("error_detail", previous.error_detail, state.error_detail),
        ]
        for field_name, before, after in field_pairs:
            if before != after:
                changed_fields.append(f"{field_name}: {before!r} -> {after!r}")
        return MonitorTransitionEvent(
            ts_utc=_now_utc_iso(),
            slot=state.slot,
            tool=state.tool,
            summary=f"{state.slot}: " + "; ".join(changed_fields),
            changed_fields=tuple(
                field_name.split(":", maxsplit=1)[0] for field_name in changed_fields
            ),
        )


class AgentSessionMonitor:
    """Bind one parser stack and tracker to one persisted agent session."""

    def __init__(
        self,
        *,
        session: AgentSessionState,
        completion_stability_seconds: float,
        unknown_to_stalled_timeout_seconds: float,
    ) -> None:
        self.m_session = session
        self.m_parser_stack = ShadowParserStack(tool=session.tool)
        self.m_tracker = AgentStateTracker(
            session=session,
            completion_stability_seconds=completion_stability_seconds,
            unknown_to_stalled_timeout_seconds=unknown_to_stalled_timeout_seconds,
        )
        self.m_baseline_pos: int | None = None

    def sample(
        self,
        *,
        client: CaoRestClient,
        monotonic_ts: float,
    ) -> tuple[AgentDashboardState, MonitorTransitionEvent | None, dict[str, Any]]:
        """Fetch, parse, and reduce one live CAO snapshot."""

        try:
            terminal = client.get_terminal(self.m_session.terminal_id)
            output = client.get_terminal_output(self.m_session.terminal_id, mode="full")
        except CaoApiError as exc:
            observation = MonitorObservation(
                slot=self.m_session.slot,
                tool=self.m_session.tool,
                terminal_id=self.m_session.terminal_id,
                tmux_session_name=self.m_session.tmux_session_name,
                cao_status="disconnected",
                parser_family=self.m_parser_stack.parser_family,
                parser_preset_id=None,
                parser_preset_version=None,
                availability="disconnected",
                business_state="unknown",
                input_mode="unknown",
                ui_context="unknown",
                normalized_projection_text="",
                dialog_tail="",
                operator_blocked_excerpt=None,
                anomaly_codes=(ANOMALY_CAO_FETCH_ERROR,),
                baseline_invalidated=False,
                monotonic_ts=monotonic_ts,
                error_detail=str(exc),
            )
        else:
            try:
                if self.m_baseline_pos is None:
                    self.m_baseline_pos = self.m_parser_stack.capture_baseline_pos(output.output)
                snapshot = self.m_parser_stack.parse_snapshot(
                    output.output,
                    baseline_pos=self.m_baseline_pos,
                )
            except ShadowParserError as exc:
                normalized_exc = as_shadow_parser_error(exc)
                observation = MonitorObservation(
                    slot=self.m_session.slot,
                    tool=self.m_session.tool,
                    terminal_id=self.m_session.terminal_id,
                    tmux_session_name=self.m_session.tmux_session_name,
                    cao_status=(
                        terminal.status.value if terminal.status is not None else "unknown"
                    ),
                    parser_family=self.m_parser_stack.parser_family,
                    parser_preset_id=(
                        normalized_exc.metadata.parser_preset_id
                        if normalized_exc.metadata is not None
                        else None
                    ),
                    parser_preset_version=(
                        normalized_exc.metadata.parser_preset_version
                        if normalized_exc.metadata is not None
                        else None
                    ),
                    availability="unknown",
                    business_state="unknown",
                    input_mode="unknown",
                    ui_context="unknown",
                    normalized_projection_text="",
                    dialog_tail=self.m_parser_stack.ansi_stripped_tail_excerpt(output.output),
                    operator_blocked_excerpt=None,
                    anomaly_codes=(ANOMALY_SHADOW_PARSE_ERROR,),
                    baseline_invalidated=False,
                    monotonic_ts=monotonic_ts,
                    error_detail=str(normalized_exc),
                )
            else:
                assessment = snapshot.surface_assessment
                projection = snapshot.dialog_projection
                observation = MonitorObservation(
                    slot=self.m_session.slot,
                    tool=self.m_session.tool,
                    terminal_id=self.m_session.terminal_id,
                    tmux_session_name=self.m_session.tmux_session_name,
                    cao_status=(
                        terminal.status.value if terminal.status is not None else "unknown"
                    ),
                    parser_family=self.m_parser_stack.parser_family,
                    parser_preset_id=assessment.parser_metadata.parser_preset_id,
                    parser_preset_version=assessment.parser_metadata.parser_preset_version,
                    availability=assessment.availability,
                    business_state=assessment.business_state,
                    input_mode=assessment.input_mode,
                    ui_context=assessment.ui_context,
                    normalized_projection_text=projection.normalized_text,
                    dialog_tail=projection.tail,
                    operator_blocked_excerpt=assessment.operator_blocked_excerpt,
                    anomaly_codes=tuple(
                        anomaly.code
                        for anomaly in (
                            *assessment.parser_metadata.anomalies,
                            *assessment.anomalies,
                            *projection.anomalies,
                        )
                    ),
                    baseline_invalidated=assessment.parser_metadata.baseline_invalidated,
                    monotonic_ts=monotonic_ts,
                    error_detail=None,
                )
        state, transition = self.m_tracker.observe(observation)
        sample_payload = {
            "ts_utc": _now_utc_iso(),
            "slot": state.slot,
            "tool": state.tool,
            "terminal_id": state.terminal_id,
            "tmux_session_name": state.tmux_session_name,
            "cao_status": state.cao_status,
            "parser_family": state.parser_family,
            "parser_preset_id": state.parser_preset_id,
            "parser_preset_version": state.parser_preset_version,
            "availability": state.availability,
            "business_state": state.business_state,
            "input_mode": state.input_mode,
            "ui_context": state.ui_context,
            "readiness_state": state.readiness_state,
            "completion_state": state.completion_state,
            "unknown_elapsed_seconds": state.unknown_elapsed_seconds,
            "stable_elapsed_seconds": state.stable_elapsed_seconds,
            "projection_changed": state.projection_changed,
            "baseline_invalidated": state.baseline_invalidated,
            "anomaly_codes": list(state.anomaly_codes),
            "dialog_tail": state.dialog_tail,
            "operator_blocked_excerpt": state.operator_blocked_excerpt,
            "error_detail": state.error_detail,
        }
        return state, transition, sample_payload


class ShadowWatchMonitor:
    """Own the polling loop, NDJSON evidence, and live `rich` dashboard."""

    def __init__(self, *, state_file: Path, dashboard_log_path: Path | None = None) -> None:
        self.m_state_file = state_file.resolve()
        self.m_state = load_demo_state(self.m_state_file)
        self.m_console = Console()
        self.m_dashboard_log_path = (
            dashboard_log_path.resolve() if dashboard_log_path is not None else None
        )
        self.m_client = CaoRestClient(self.m_state.launcher.base_url)
        self.m_agent_monitors = {
            slot: AgentSessionMonitor(
                session=session,
                completion_stability_seconds=self.m_state.completion_stability_seconds,
                unknown_to_stalled_timeout_seconds=self.m_state.unknown_to_stalled_timeout_seconds,
            )
            for slot, session in self.m_state.agents.items()
        }
        self.m_transition_log: list[MonitorTransitionEvent] = []

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
                states: list[AgentDashboardState] = []
                for slot in sorted(self.m_agent_monitors):
                    state, transition, sample_payload = self.m_agent_monitors[slot].sample(
                        client=self.m_client,
                        monotonic_ts=time.monotonic(),
                    )
                    states.append(state)
                    _append_ndjson(samples_path, sample_payload)
                    if transition is not None:
                        self.m_transition_log.append(transition)
                        self.m_transition_log = self.m_transition_log[-12:]
                        _append_ndjson(transitions_path, transition.to_payload())
                renderable = _render_dashboard(
                    demo_state=self.m_state,
                    states=states,
                    transitions=self.m_transition_log,
                )
                live.update(renderable)
                if self.m_dashboard_log_path is not None:
                    self.m_dashboard_log_path.parent.mkdir(parents=True, exist_ok=True)
                    with self.m_dashboard_log_path.open("a", encoding="utf-8") as handle:
                        handle.write(f"[{_now_utc_iso()}] dashboard refreshed\n")
                iteration += 1
                if max_iterations is not None and iteration >= max_iterations:
                    return 0
                elapsed = time.monotonic() - started_at
                time.sleep(max(self.m_state.poll_interval_seconds - elapsed, 0.0))


def main(argv: list[str] | None = None) -> int:
    """Run the standalone monitor entrypoint."""

    parser = argparse.ArgumentParser(description="Live rich dashboard for dual CAO shadow watch.")
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


def _render_dashboard(
    *,
    demo_state: DualShadowWatchDemoState,
    states: list[AgentDashboardState],
    transitions: list[MonitorTransitionEvent],
) -> Layout:
    """Build the live `rich` layout for the current monitor state."""

    layout = Layout()
    layout.split_column(
        Layout(name="summary", size=8),
        Layout(name="details", size=12),
        Layout(name="transitions"),
    )
    layout["summary"].update(_render_summary_table(states=states))
    layout["details"].update(
        Columns([_render_detail_panel(state) for state in states], equal=True, expand=True)
    )
    layout["transitions"].update(
        _render_transition_panel(demo_state=demo_state, transitions=transitions)
    )
    return layout


def _render_summary_table(*, states: list[AgentDashboardState]) -> Panel:
    """Render the compact top-level state table."""

    table = Table(expand=True)
    for column in (
        "slot",
        "cao_status",
        "availability",
        "business_state",
        "input_mode",
        "readiness",
        "completion",
        "unknown_s",
        "stable_s",
        "projection_changed",
        "baseline_invalidated",
        "anomalies",
    ):
        table.add_column(column)
    for state in states:
        table.add_row(
            state.slot,
            state.cao_status,
            state.availability,
            state.business_state,
            state.input_mode,
            state.readiness_state,
            state.completion_state,
            _format_seconds(state.unknown_elapsed_seconds),
            _format_seconds(state.stable_elapsed_seconds),
            str(state.projection_changed),
            str(state.baseline_invalidated),
            ",".join(state.anomaly_codes[-4:]) if state.anomaly_codes else "-",
        )
    return Panel(table, title="Shadow Watch Summary")


def _render_detail_panel(state: AgentDashboardState) -> Panel:
    """Render one per-agent detail panel."""

    lines = [
        Text(f"tmux: {state.tmux_session_name}"),
        Text(f"terminal: {state.terminal_id}"),
        Text(
            "parser: "
            f"{state.parser_family}"
            + (
                f" ({state.parser_preset_id}@{state.parser_preset_version})"
                if state.parser_preset_id and state.parser_preset_version
                else ""
            )
        ),
        Text(f"ui_context: {state.ui_context}"),
        Text(f"tail: {state.dialog_tail or '<empty>'}"),
    ]
    if state.operator_blocked_excerpt:
        lines.append(Text(f"blocked_excerpt: {state.operator_blocked_excerpt}"))
    if state.error_detail:
        lines.append(Text(f"error: {state.error_detail}"))
    return Panel(Group(*lines), title=f"{state.tool} ({state.slot})")


def _render_transition_panel(
    *,
    demo_state: DualShadowWatchDemoState,
    transitions: list[MonitorTransitionEvent],
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
        body_lines.append(Text("No transitions yet."))
    for event in transitions[-10:]:
        body_lines.append(Text(f"{event.ts_utc} {event.summary}"))
    return Panel(Group(*body_lines), title="Transitions")


def _append_ndjson(path: Path, payload: dict[str, Any]) -> None:
    """Append one JSON object as a single NDJSON line."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def _classify_readiness(observation: MonitorObservation) -> str:
    """Return one readiness classification from a parsed observation."""

    if observation.availability in {"unsupported", "disconnected"}:
        return "failed"
    if _is_operator_blocked(observation):
        return "blocked"
    if _is_unknown_for_stall(observation):
        return "unknown"
    if _is_submit_ready(observation):
        return "ready"
    return "waiting"


def _classify_completion_surface(observation: MonitorObservation) -> str:
    """Return the base completion-surface classification before timing logic."""

    if observation.availability in {"unsupported", "disconnected"}:
        return "failed"
    if _is_operator_blocked(observation):
        return "blocked"
    if _is_unknown_for_stall(observation):
        return "unknown"
    if observation.business_state == "working":
        return "in_progress"
    return "waiting"


def _is_submit_ready(observation: MonitorObservation) -> bool:
    """Return whether the observation is prompt-submit ready."""

    return (
        observation.availability == "supported"
        and observation.business_state == "idle"
        and observation.input_mode == "freeform"
    )


def _is_operator_blocked(observation: MonitorObservation) -> bool:
    """Return whether the observation requires operator intervention."""

    return (
        observation.availability == "supported"
        and observation.business_state == "awaiting_operator"
    )


def _is_unknown_for_stall(observation: MonitorObservation) -> bool:
    """Return whether the observation contributes to unknown-to-stalled timing."""

    return observation.availability == "unknown" or (
        observation.availability == "supported" and observation.business_state == "unknown"
    )


def _now_utc_iso() -> str:
    """Return one current UTC timestamp string."""

    return datetime.now(UTC).isoformat(timespec="seconds")


def _format_seconds(value: float | None) -> str:
    """Render one optional duration value for the summary table."""

    if value is None:
        return "-"
    return f"{value:.1f}"
