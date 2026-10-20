"""Replay Codex hook streams into merged posture timelines (throwaway E3/E4 arm).

Standalone, stdlib-only normalizer and posture reducer for the 2026-10-20 Codex
hook-observation campaign. It replays ``collector/events.ndjson`` streams with
the archived Claude merge rules adapted to Codex's ``turn_id`` correlation,
deny-aborts-turn blocked settling, compaction windows, and terminal-gap
fallback. It does not import the production reducer and does not write to the
trajectory under test.

Determinism: ordering and virtual time come from the stream's own
``received_at_monotonic`` / ``received_at_utc`` stamps. No wall clock is read.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
RUN_ROOT_BASE = REPO_ROOT / "tmp" / "codex-hook-capture"


@dataclass(frozen=True)
class Envelope:
    """One collector event row."""

    sequence: int | None
    received_at_utc: str
    received_at_monotonic: float
    channel_generation: int
    via: str
    provider_event: dict[str, Any]


@dataclass(frozen=True)
class Observation:
    """Provider event normalized into the reducer vocabulary."""

    kind: str
    event_name: str
    sequence: int | None
    received_at_utc: str
    received_at_monotonic: float
    generation: int
    session_id: str | None = None
    turn_id: str | None = None
    tool_name: str | None = None
    tool_use_id: str | None = None
    source: str | None = None
    trigger: str | None = None
    permission_mode: str | None = None
    stop_hook_active: bool | None = None
    tool_command: str | None = None


@dataclass(frozen=True)
class PendingToolUse:
    """The immediately preceding PreToolUse, used to pair PermissionRequest."""

    turn_id: str | None
    tool_name: str | None
    tool_use_id: str | None
    command: str | None


@dataclass(frozen=True)
class Posture:
    """One merged posture snapshot for the Codex hook channel."""

    presence: str
    turn_phase: str
    work: str
    blocked: bool
    blocked_tool_name: str | None
    maintenance_active: bool
    turn_id: str | None
    session_id: str | None
    resume_started: bool
    last_turn_result: str
    last_turn_source: str
    last_terminal_turn_id: str | None
    generation: int | None
    epochs: int
    steer_count: int
    compaction_boundaries: int
    permission_requests: int
    allow_settles: int
    deny_settles: int
    terminal_gaps: int
    orphan_terminals: int
    diagnostics: tuple[str, ...]
    last_event: str | None
    last_event_at_utc: str | None


@dataclass(frozen=True)
class TimelineRow:
    """One event plus the posture produced immediately after it."""

    sequence: int | None
    event_name: str
    received_at_utc: str
    received_at_monotonic: float
    generation: int
    session_id: str | None
    turn_id: str | None
    presence: str
    turn_phase: str
    blocked: bool
    maintenance_active: bool
    last_turn_result: str
    work: str
    diagnostics: tuple[str, ...]


@dataclass(frozen=True)
class LabelCheck:
    """One label window compared with the replay posture."""

    label_id: str
    expected: str
    start_phase: str
    end_phase: str
    end_last_turn: str
    verdict: str


@dataclass(frozen=True)
class RunSpec:
    """Expected stream shape and final posture for one captured run."""

    name: str
    root: Path
    expected_events: tuple[str, ...]
    expected_presence: str
    expected_phase: str
    expected_last_turn: str
    expected_epochs: int
    expected_steers: int = 0
    expected_compactions: int = 0
    expected_allow: int = 0
    expected_deny: int = 0
    expected_terminal_gaps: int = 0
    expected_diagnostic: str | None = None
    expected_session_ids: int = 1


@dataclass(frozen=True)
class RunResult:
    """Replay output for one captured run."""

    spec: RunSpec
    rows: tuple[TimelineRow, ...]
    final: Posture
    event_names: tuple[str, ...]
    session_ids: tuple[str, ...]
    collector_status: dict[str, Any] | None
    validation: tuple[str, ...]
    label_checks: tuple[LabelCheck, ...]


KIND_BY_EVENT: dict[str, str] = {
    "SessionStart": "session_start",
    "UserPromptSubmit": "prompt_submitted",
    "PreToolUse": "pre_tool_use",
    "PermissionRequest": "permission_requested",
    "PostToolUse": "post_tool_use",
    "Stop": "turn_stopped",
    "Interrupt": "turn_interrupted",
    "PreCompact": "maintenance_started",
    "PostCompact": "maintenance_ended",
    "SessionEnd": "session_ended",
    "PreModelRequest": "model_request_unavailable",
    "PostModelRequest": "model_request_unavailable",
    "SubagentStart": "subagent_event",
    "SubagentStop": "subagent_event",
}


def _optional_str(payload: dict[str, Any], key: str) -> str | None:
    """Return one non-empty string field or ``None``."""

    value = payload.get(key)
    if not isinstance(value, str) or not value:
        return None
    return value


def _optional_bool(payload: dict[str, Any], key: str) -> bool | None:
    """Return one boolean field or ``None`` when absent or mistyped."""

    value = payload.get(key)
    return value if isinstance(value, bool) else None


def _tool_command(payload: dict[str, Any]) -> str | None:
    """Return the shell command from a tool payload, when present."""

    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return None
    return _optional_str(tool_input, "command")


def normalize(envelope: Envelope) -> Observation:
    """Normalize one collector envelope into one observation."""

    payload = envelope.provider_event
    event_name = _optional_str(payload, "hook_event_name") or "<malformed>"
    kind = KIND_BY_EVENT.get(event_name, "unknown")
    return Observation(
        kind=kind,
        event_name=event_name,
        sequence=envelope.sequence,
        received_at_utc=envelope.received_at_utc,
        received_at_monotonic=envelope.received_at_monotonic,
        generation=envelope.channel_generation,
        session_id=_optional_str(payload, "session_id"),
        turn_id=_optional_str(payload, "turn_id"),
        tool_name=_optional_str(payload, "tool_name"),
        tool_use_id=_optional_str(payload, "tool_use_id"),
        source=_optional_str(payload, "source"),
        trigger=_optional_str(payload, "trigger"),
        permission_mode=_optional_str(payload, "permission_mode"),
        stop_hook_active=_optional_bool(payload, "stop_hook_active"),
        tool_command=_tool_command(payload),
    )


class Reducer:
    """Pure Codex posture reducer; one observation per call, arrival order."""

    def __init__(self) -> None:
        """Initialize the empty posture."""

        self.m_presence = "unknown"
        self.m_turn_phase = "unknown"
        self.m_work = "unknown"
        self.m_blocked = False
        self.m_blocked_tool_name: str | None = None
        self.m_blocked_tool_use_id: str | None = None
        self.m_maintenance_active = False
        self.m_pre_maintenance_phase: str | None = None
        self.m_turn_id: str | None = None
        self.m_session_id: str | None = None
        self.m_resume_started = False
        self.m_last_turn_result = "none"
        self.m_last_turn_source = "none"
        self.m_last_terminal_turn_id: str | None = None
        self.m_last_pre_tool_use: PendingToolUse | None = None
        self.m_generation: int | None = None
        self.m_epochs = 0
        self.m_steer_count = 0
        self.m_compaction_boundaries = 0
        self.m_permission_requests = 0
        self.m_allow_settles = 0
        self.m_deny_settles = 0
        self.m_terminal_gaps = 0
        self.m_orphan_terminals = 0
        self.m_work_diagnosed = False
        self.m_events_seen = 0
        self.m_seen_sequences: set[tuple[int, int]] = set()
        self.m_diagnostics: list[str] = []
        self.m_last_event: str | None = None
        self.m_last_event_at_utc: str | None = None

    def posture(self) -> Posture:
        """Return the current immutable posture snapshot."""

        return Posture(
            presence=self.m_presence,
            turn_phase=self.m_turn_phase,
            work=self.m_work,
            blocked=self.m_blocked,
            blocked_tool_name=self.m_blocked_tool_name,
            maintenance_active=self.m_maintenance_active,
            turn_id=self.m_turn_id,
            session_id=self.m_session_id,
            resume_started=self.m_resume_started,
            last_turn_result=self.m_last_turn_result,
            last_turn_source=self.m_last_turn_source,
            last_terminal_turn_id=self.m_last_terminal_turn_id,
            generation=self.m_generation,
            epochs=self.m_epochs,
            steer_count=self.m_steer_count,
            compaction_boundaries=self.m_compaction_boundaries,
            permission_requests=self.m_permission_requests,
            allow_settles=self.m_allow_settles,
            deny_settles=self.m_deny_settles,
            terminal_gaps=self.m_terminal_gaps,
            orphan_terminals=self.m_orphan_terminals,
            diagnostics=tuple(self.m_diagnostics),
            last_event=self.m_last_event,
            last_event_at_utc=self.m_last_event_at_utc,
        )

    def reduce(self, observation: Observation) -> Posture:
        """Consume one observation and return the new posture."""

        self.m_events_seen += 1
        if self.m_generation is None:
            self.m_generation = observation.generation
        elif observation.generation > self.m_generation:
            self._reset_generation(observation.generation)
        if observation.sequence is not None:
            key = (observation.generation, observation.sequence)
            if key in self.m_seen_sequences:
                self._diag("duplicate_event", f"seq={observation.sequence}")
                return self.posture()
            self.m_seen_sequences.add(key)

        self.m_last_event = observation.event_name
        self.m_last_event_at_utc = observation.received_at_utc

        if observation.kind == "session_start":
            self._apply_session_start(observation)
        elif observation.kind == "prompt_submitted":
            self._apply_prompt_submitted(observation)
        elif observation.kind == "pre_tool_use":
            self._apply_pre_tool_use(observation)
        elif observation.kind == "permission_requested":
            self._apply_permission_requested(observation)
        elif observation.kind == "post_tool_use":
            self._apply_post_tool_use(observation)
        elif observation.kind == "turn_stopped":
            self._apply_turn_stopped(observation)
        elif observation.kind == "turn_interrupted":
            self._apply_turn_interrupted(observation)
        elif observation.kind == "maintenance_started":
            self._apply_maintenance_started(observation)
        elif observation.kind == "maintenance_ended":
            self._apply_maintenance_ended(observation)
        elif observation.kind == "session_ended":
            self._apply_session_ended(observation)
        elif observation.kind == "model_request_unavailable":
            self._diag("model_request_event_unavailable", observation.event_name)
        elif observation.kind == "subagent_event":
            self._diag("subagent_event_observed", observation.event_name)
        else:
            self._diag("unknown_event", observation.event_name)
        return self.posture()

    def finish(self, reason: str = "stream_end") -> Posture:
        """Close the stream and apply the terminal-gap fallback."""

        if self.m_events_seen == 0:
            self._diag("empty_stream", reason)
            return self.posture()
        if self.m_turn_phase in ("active", "blocked") or self.m_turn_id is not None:
            self.m_terminal_gaps += 1
            self._diag("terminal_gap", f"{reason}:open_turn")
            if self.m_presence == "present":
                self.m_presence = "lost"
            self.m_turn_phase = "unknown"
            self.m_turn_id = None
            self.m_blocked = False
            self.m_blocked_tool_name = None
            self.m_blocked_tool_use_id = None
            self.m_last_turn_result = "none"
            self.m_last_turn_source = "none"
        elif self.m_presence == "present":
            self.m_presence = "unknown"
            self._diag("stream_end_without_session_end", reason)
        return self.posture()

    def _apply_session_start(self, observation: Observation) -> None:
        """Apply SessionStart: startup/resume reset the turn, compact marks a boundary."""

        self.m_presence = "present"
        if observation.session_id is not None:
            self.m_session_id = observation.session_id
        if observation.source == "resume":
            self.m_resume_started = True
        elif observation.source in ("startup", "clear", "fork"):
            self.m_resume_started = False
        if observation.source in ("startup", "resume"):
            self._reset_turn()
            self.m_turn_phase = "ready"
        elif observation.source == "compact":
            self.m_compaction_boundaries += 1
            self._diag("compaction_boundary", observation.source)
            if self.m_turn_phase == "unknown":
                self.m_turn_phase = "ready"
        elif self.m_turn_phase == "unknown":
            self.m_turn_phase = "ready"

    def _apply_prompt_submitted(self, observation: Observation) -> None:
        """Start a new turn epoch, or record a steer in the running epoch."""

        self.m_presence = "present"
        if self.m_turn_phase in ("active", "blocked") and self.m_turn_id is not None:
            if observation.turn_id == self.m_turn_id:
                self.m_steer_count += 1
                self._diag("steer_same_turn", observation.turn_id)
                if self.m_blocked:
                    self._diag("prompt_during_blocked")
                self.m_blocked = False
                self.m_turn_phase = "active"
                return
            self._diag("turn_epoch_superseded", f"{self.m_turn_id}->{observation.turn_id}")
        if self.m_maintenance_active:
            self._diag("prompt_during_maintenance")
            self.m_maintenance_active = False
        self.m_turn_id = observation.turn_id
        self.m_turn_phase = "active"
        self.m_blocked = False
        self.m_blocked_tool_name = None
        self.m_blocked_tool_use_id = None
        self.m_last_pre_tool_use = None
        self.m_last_turn_result = "none"
        self.m_last_turn_source = "none"
        self.m_last_terminal_turn_id = None
        self.m_epochs += 1

    def _apply_pre_tool_use(self, observation: Observation) -> None:
        """Record the tool call that a following PermissionRequest pairs with."""

        self.m_presence = "present"
        if self.m_turn_phase == "blocked":
            self._diag("blocked_superseded_by_pre_tool_use", observation.tool_use_id)
            self.m_blocked = False
            self.m_blocked_tool_name = None
            self.m_blocked_tool_use_id = None
            self.m_turn_phase = "active"
        if self.m_turn_id is None:
            self._diag("tool_without_turn", observation.tool_name)
        elif observation.turn_id is None or observation.turn_id == self.m_turn_id:
            self.m_turn_phase = "active"
        else:
            self._diag("tool_turn_mismatch", f"{observation.turn_id}!={self.m_turn_id}")
        self.m_last_pre_tool_use = PendingToolUse(
            turn_id=observation.turn_id,
            tool_name=observation.tool_name,
            tool_use_id=observation.tool_use_id,
            command=observation.tool_command,
        )

    def _apply_permission_requested(self, observation: Observation) -> None:
        """Enter blocked and pair back to the immediately preceding PreToolUse."""

        self.m_presence = "present"
        self.m_permission_requests += 1
        paired = self.m_last_pre_tool_use
        matches = (
            paired is not None
            and paired.turn_id == observation.turn_id
            and paired.tool_name == observation.tool_name
            and paired.command == observation.tool_command
        )
        if matches:
            self.m_blocked_tool_use_id = paired.tool_use_id
            self._diag("permission_paired", paired.tool_use_id)
        else:
            self.m_blocked_tool_use_id = None
            self._diag("permission_without_pre_tool_use", observation.tool_name)
        if self.m_turn_id is None:
            self._diag("permission_without_armed_prompt", observation.turn_id)
            self.m_turn_id = observation.turn_id
        self.m_blocked = True
        self.m_blocked_tool_name = observation.tool_name
        self.m_turn_phase = "blocked"

    def _apply_post_tool_use(self, observation: Observation) -> None:
        """Settle blocked on allow, pairing by the PreToolUse tool_use_id."""

        self.m_presence = "present"
        if self.m_blocked:
            if (
                self.m_blocked_tool_use_id is not None
                and observation.tool_use_id == self.m_blocked_tool_use_id
            ):
                self._diag("allow_settled", observation.tool_use_id)
            else:
                self._diag(
                    "blocked_settle_tool_mismatch",
                    f"{self.m_blocked_tool_use_id}!={observation.tool_use_id}",
                )
            self.m_allow_settles += 1
            self.m_blocked = False
            self.m_blocked_tool_name = None
            self.m_blocked_tool_use_id = None
            if self.m_turn_id is not None:
                self.m_turn_phase = "active"
            return
        if self.m_turn_id is not None:
            self.m_turn_phase = "active"

    def _apply_turn_stopped(self, observation: Observation) -> None:
        """Settle success, unless stop_hook_active marks a continuation."""

        if observation.stop_hook_active is True:
            self._diag("stop_hook_active_continuation", observation.turn_id)
            if self.m_turn_id is not None:
                self.m_turn_phase = "active"
            return
        if self.m_turn_id is None or self.m_turn_phase in ("ready", "unknown"):
            self.m_orphan_terminals += 1
            self._diag("orphan_terminal", "Stop")
            return
        if observation.turn_id is not None and observation.turn_id != self.m_turn_id:
            self.m_orphan_terminals += 1
            self._diag("terminal_turn_mismatch", f"{observation.turn_id}!={self.m_turn_id}")
            return
        self._settle_terminal("success", observation.turn_id or self.m_turn_id, "Stop")

    def _apply_turn_interrupted(self, observation: Observation) -> None:
        """Settle interrupted; deny-cancel also clears blocked and aborts the turn."""

        if self.m_turn_id is None:
            if (
                self.m_last_turn_result == "success"
                and observation.turn_id == self.m_last_terminal_turn_id
            ):
                self.m_last_turn_result = "interrupted"
                self._diag("hook_success_interrupt_override", observation.turn_id)
            else:
                self.m_orphan_terminals += 1
                self._diag("orphan_terminal", "Interrupt")
            return
        if observation.turn_id is not None and observation.turn_id != self.m_turn_id:
            self.m_orphan_terminals += 1
            self._diag("interrupt_turn_mismatch", f"{observation.turn_id}!={self.m_turn_id}")
            return
        turn_id = observation.turn_id or self.m_turn_id
        if self.m_blocked:
            self.m_deny_settles += 1
            self._diag("deny_aborted_turn", self.m_blocked_tool_name)
        else:
            self._diag("esc_interrupt", turn_id)
        self._settle_terminal("interrupted", turn_id, "Interrupt")

    def _apply_maintenance_started(self, observation: Observation) -> None:
        """Hold the current posture through a compaction window."""

        self.m_presence = "present"
        if not self.m_maintenance_active:
            self.m_pre_maintenance_phase = self.m_turn_phase
            self.m_maintenance_active = True
            self._diag("maintenance_started", observation.trigger)
        if self.m_turn_phase == "unknown":
            self.m_turn_phase = "ready"

    def _apply_maintenance_ended(self, observation: Observation) -> None:
        """Close the compaction window without minting a turn epoch."""

        self.m_maintenance_active = False
        self._diag("maintenance_ended", observation.trigger)
        if self.m_turn_phase == "unknown":
            self.m_turn_phase = self.m_pre_maintenance_phase or "ready"
        self.m_pre_maintenance_phase = None

    def _apply_session_ended(self, observation: Observation) -> None:
        """Lose presence; an open turn becomes an explicit terminal gap."""

        self.m_presence = "lost"
        if self.m_turn_phase in ("active", "blocked") or self.m_turn_id is not None:
            self.m_terminal_gaps += 1
            self._diag("session_end_with_open_turn", self.m_turn_id)
            self.m_turn_phase = "unknown"
            self.m_turn_id = None
            self.m_blocked = False
            self.m_blocked_tool_name = None
            self.m_blocked_tool_use_id = None
            self.m_last_turn_result = "none"
            self.m_last_turn_source = "none"
        self.m_maintenance_active = False
        self.m_pre_maintenance_phase = None

    def _settle_terminal(self, result: str, turn_id: str | None, event_name: str) -> None:
        """Latch one terminal result and return to ready."""

        self.m_last_turn_result = result
        self.m_last_turn_source = "hook_observation"
        self.m_last_terminal_turn_id = turn_id
        self.m_turn_phase = "ready"
        self.m_turn_id = None
        self.m_blocked = False
        self.m_blocked_tool_name = None
        self.m_blocked_tool_use_id = None
        self.m_last_pre_tool_use = None
        self._diag("terminal_latched", f"{event_name}:{result}")
        if self.m_work == "unknown" and not self.m_work_diagnosed:
            self.m_work_diagnosed = True
            self._diag("work_signal_unavailable", "Stop has no background_tasks field")

    def _reset_turn(self) -> None:
        """Reset turn-scoped state for a new session generation."""

        self.m_turn_id = None
        self.m_turn_phase = "ready"
        self.m_blocked = False
        self.m_blocked_tool_name = None
        self.m_blocked_tool_use_id = None
        self.m_maintenance_active = False
        self.m_pre_maintenance_phase = None
        self.m_last_pre_tool_use = None
        self.m_last_turn_result = "none"
        self.m_last_turn_source = "none"
        self.m_last_terminal_turn_id = None

    def _reset_generation(self, generation: int) -> None:
        """Reset generation-scoped state while retaining campaign counters."""

        self._diag("generation_boundary", str(generation))
        self.m_generation = generation
        self.m_presence = "unknown"
        self.m_session_id = None
        self.m_resume_started = False
        self._reset_turn()
        self.m_turn_phase = "unknown"
        self.m_work = "unknown"

    def _diag(self, kind: str, detail: str | None = None) -> None:
        """Append one bounded diagnostic string."""

        text = kind if detail is None else f"{kind}:{detail}"
        self.m_diagnostics.append(text)


def load_envelopes(path: Path) -> list[Envelope]:
    """Load one events.ndjson file in virtual-time order."""

    if not path.is_file():
        return []
    rows: list[Envelope] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            provider = row.get("provider_event")
            if not isinstance(provider, dict):
                continue
            monotonic = row.get("received_at_monotonic")
            rows.append(
                Envelope(
                    sequence=row.get("sequence") if isinstance(row.get("sequence"), int) else None,
                    received_at_utc=str(row.get("received_at_utc") or ""),
                    received_at_monotonic=float(monotonic)
                    if isinstance(monotonic, (int, float))
                    else 0.0,
                    channel_generation=int(row.get("channel_generation") or 0),
                    via=str(row.get("via") or "unknown"),
                    provider_event=provider,
                )
            )
    rows.sort(key=lambda item: (item.received_at_monotonic, item.sequence or -1))
    return rows


def replay_envelopes(envelopes: list[Envelope]) -> tuple[list[TimelineRow], Posture]:
    """Replay envelopes and return one timeline row per event plus the final posture."""

    reducer = Reducer()
    rows: list[TimelineRow] = []
    for envelope in envelopes:
        before = len(reducer.m_diagnostics)
        observation = normalize(envelope)
        posture = reducer.reduce(observation)
        rows.append(
            TimelineRow(
                sequence=observation.sequence,
                event_name=observation.event_name,
                received_at_utc=observation.received_at_utc,
                received_at_monotonic=observation.received_at_monotonic,
                generation=observation.generation,
                session_id=posture.session_id,
                turn_id=posture.turn_id,
                presence=posture.presence,
                turn_phase=posture.turn_phase,
                blocked=posture.blocked,
                maintenance_active=posture.maintenance_active,
                last_turn_result=posture.last_turn_result,
                work=posture.work,
                diagnostics=posture.diagnostics[before:],
            )
        )
    final = reducer.finish()
    return rows, final


def _parse_ts(value: str) -> datetime:
    """Parse one ISO-8601 timestamp for label-window comparisons."""

    return datetime.fromisoformat(value)


def _load_json(path: Path) -> dict[str, Any] | None:
    """Load one JSON object, returning None when absent or invalid."""

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _pane_samples(run_root: Path, recording: str) -> dict[str, dict[str, Any]]:
    """Map sample id to its pane snapshot metadata for one recorder run."""

    path = run_root / recording / "pane_snapshots.ndjson"
    samples: dict[str, dict[str, Any]] = {}
    if not path.is_file():
        return samples
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            sample_id = row.get("sample_id")
            if isinstance(sample_id, str):
                samples[sample_id] = row
    return samples


def _label_verdict(
    expected: str,
    window_phases: list[str],
    window_maintenance: bool,
    end_row: TimelineRow | None,
    final: Posture,
    steer_count: int,
) -> str:
    """Compare one label's expected phase against the replay window."""

    if expected == "not_reached":
        return "n/a (not reached)"
    if expected in ("blocked_trust_review", "trust_review_to_ready"):
        return "n/a (TUI-only trust surface)"
    if expected == "ready":
        if end_row is None:
            return "n/a (pre-channel)"
        return "OK" if end_row.turn_phase in ("ready", "unknown") else "MISMATCH"
    if expected == "active_then_completed":
        if end_row is None:
            return "n/a (no events)"
        if end_row.turn_phase == "ready" and end_row.last_turn_result in (
            "success",
            "interrupted",
        ):
            return "OK"
        return "MISMATCH"
    if expected == "blocked_then_approved":
        if "blocked" in window_phases and end_row is not None:
            return "OK" if end_row.last_turn_result == "success" else "MISMATCH"
        return "MISMATCH"
    if expected == "blocked_then_canceled":
        if "blocked" in window_phases and end_row is not None:
            return "OK" if end_row.last_turn_result == "interrupted" else "MISMATCH"
        return "MISMATCH"
    if expected == "generating":
        return (
            "OK" if any(phase in ("active", "blocked") for phase in window_phases) else "MISMATCH"
        )
    if expected == "compacting":
        return "OK" if window_maintenance else "MISMATCH"
    if expected == "interrupted":
        return (
            "OK"
            if end_row is not None and end_row.last_turn_result == "interrupted"
            else "MISMATCH"
        )
    if expected in ("killing", "killed"):
        if final.turn_phase == "unknown" and any(
            item.startswith("terminal_gap") for item in final.diagnostics
        ):
            return "OK"
        return "MISMATCH"
    if expected == "steered_same_turn":
        if steer_count >= 1 and end_row is not None and end_row.last_turn_result == "success":
            return "OK"
        return "MISMATCH"
    if expected == "modal_waiting":
        return "OK" if "blocked" in window_phases else "MISMATCH"
    if expected == "resumed_then_completed":
        if (
            final.resume_started
            and end_row is not None
            and end_row.turn_phase == "ready"
            and end_row.last_turn_result == "success"
        ):
            return "OK"
        return "MISMATCH"
    if expected == "exiting":
        if end_row is not None and (
            end_row.presence in ("lost", "unknown") or end_row.turn_phase == "ready"
        ):
            return "OK"
        return "MISMATCH"
    if expected in ("failed_error_402", "provider_error"):
        # The provider error is not a hook terminal; the truthful hook state is
        # only reached at SessionEnd (open turn -> unknown) or stream end.
        if final.presence == "lost" and final.turn_phase == "unknown":
            return "OK"
        return "MISMATCH"
    return "n/a"


def check_labels(run_root: Path, rows: list[TimelineRow], final: Posture) -> list[LabelCheck]:
    """Compare filled label windows with the replay posture timeline."""

    labels_path = run_root / "labels" / "labels-template.json"
    labels_doc = _load_json(labels_path)
    if labels_doc is None:
        return []
    labels = labels_doc.get("labels")
    if not isinstance(labels, list):
        return []
    main_samples = _pane_samples(run_root, "pane-recording")
    resume_samples = _pane_samples(run_root, "pane-recording-resume")
    checks: list[LabelCheck] = []
    for label in labels:
        if not isinstance(label, dict):
            continue
        label_id = str(label.get("label_id") or "?")
        sample_id = label.get("sample_id")
        if not isinstance(sample_id, str):
            continue
        samples = resume_samples if label_id.startswith("s7-resume") else main_samples
        sample = samples.get(sample_id)
        if sample is None:
            sample = main_samples.get(sample_id) or resume_samples.get(sample_id)
        if sample is None:
            continue
        end_id = label.get("sample_end_id")
        end_sample = samples.get(end_id) if isinstance(end_id, str) else None
        if end_sample is None:
            end_sample = sample
        try:
            start_ts = _parse_ts(str(sample.get("ts_utc")))
            end_ts = _parse_ts(str(end_sample.get("ts_utc")))
        except (TypeError, ValueError):
            continue
        timed_rows = [(_parse_ts(row.received_at_utc), row) for row in rows]
        before = [row for ts, row in timed_rows if ts <= start_ts]
        window = [row for ts, row in timed_rows if start_ts <= ts <= end_ts]
        # A hook terminal can land a fraction of a second after the last visible
        # frame; look ahead briefly, but stop at the next prompt (new epoch).
        lookahead: list[TimelineRow] = []
        for ts, row in timed_rows:
            if end_ts < ts <= end_ts + timedelta(seconds=3):
                if row.event_name == "UserPromptSubmit":
                    break
                lookahead.append(row)
        combined = window + lookahead
        end_row = combined[-1] if combined else (before[-1] if before else None)
        # The blocked row can sit just before the 1-second label boundary; keep
        # the pre-window posture for window-phase classification.
        window_phases = ([before[-1].turn_phase] if before else []) + [
            row.turn_phase for row in combined
        ]
        expected = str(label.get("expectations", {}).get("turn_phase") or "unknown")
        verdict = _label_verdict(
            expected,
            window_phases,
            any(row.maintenance_active for row in combined),
            end_row,
            final,
            final.steer_count,
        )
        checks.append(
            LabelCheck(
                label_id=label_id,
                expected=expected,
                start_phase=before[-1].turn_phase if before else "pre-channel",
                end_phase=end_row.turn_phase if end_row is not None else "pre-channel",
                end_last_turn=end_row.last_turn_result if end_row is not None else "none",
                verdict=verdict,
            )
        )
    return checks


RUN_SPECS: tuple[RunSpec, ...] = (
    RunSpec(
        "s0",
        RUN_ROOT_BASE / "s0" / "run-20261020T035949Z",
        ("SessionStart", "UserPromptSubmit", "Stop", "SessionEnd"),
        "lost",
        "ready",
        "success",
        1,
    ),
    RunSpec(
        "s1",
        RUN_ROOT_BASE / "s1" / "run-20261020T041527Z",
        (
            "SessionStart",
            "UserPromptSubmit",
            "Stop",
            "UserPromptSubmit",
            "PreToolUse",
            "PostToolUse",
            "Stop",
            "SessionEnd",
        ),
        "lost",
        "ready",
        "success",
        2,
    ),
    RunSpec(
        "s2-interactive",
        RUN_ROOT_BASE / "s2" / "run-20261020T040510Z",
        ("SessionStart", "UserPromptSubmit", "Stop", "SessionEnd"),
        "lost",
        "ready",
        "success",
        1,
    ),
    RunSpec(
        "s3",
        RUN_ROOT_BASE / "s3" / "run-20261020T043111Z",
        (
            "SessionStart",
            "UserPromptSubmit",
            "PreToolUse",
            "PermissionRequest",
            "PostToolUse",
            "Stop",
            "UserPromptSubmit",
            "PreToolUse",
            "PermissionRequest",
            "Interrupt",
            "SessionEnd",
        ),
        "lost",
        "ready",
        "interrupted",
        2,
        expected_allow=1,
        expected_deny=1,
    ),
    RunSpec(
        "s4",
        RUN_ROOT_BASE / "s4" / "run-20261020T041644Z",
        (
            "SessionStart",
            "UserPromptSubmit",
            "PreToolUse",
            "PostToolUse",
            "Stop",
            "PreCompact",
            "PostCompact",
            "SessionStart",
            "UserPromptSubmit",
            "Stop",
            "SessionEnd",
        ),
        "lost",
        "ready",
        "success",
        2,
        expected_compactions=1,
    ),
    RunSpec(
        "s5",
        RUN_ROOT_BASE / "s5" / "run-20261020T041843Z",
        ("SessionStart", "UserPromptSubmit", "Interrupt", "SessionEnd"),
        "lost",
        "ready",
        "interrupted",
        1,
    ),
    RunSpec(
        "s6",
        RUN_ROOT_BASE / "s6" / "run-20261020T041916Z",
        (
            "SessionStart",
            "UserPromptSubmit",
            "UserPromptSubmit",
            "Stop",
            "SessionEnd",
        ),
        "lost",
        "ready",
        "success",
        1,
        expected_steers=1,
    ),
    RunSpec(
        "s7",
        RUN_ROOT_BASE / "s7" / "run-20261020T042433Z",
        (
            "SessionStart",
            "UserPromptSubmit",
            "Stop",
            "SessionEnd",
            "SessionStart",
            "UserPromptSubmit",
            "Stop",
            "SessionEnd",
        ),
        "lost",
        "ready",
        "success",
        2,
        expected_session_ids=1,
    ),
    RunSpec(
        "f1",
        RUN_ROOT_BASE / "f1" / "run-20261020T042538Z",
        ("SessionStart", "UserPromptSubmit"),
        "lost",
        "unknown",
        "none",
        1,
        expected_terminal_gaps=1,
        expected_diagnostic="terminal_gap",
    ),
    RunSpec(
        "t1",
        RUN_ROOT_BASE / "t1" / "run-20261020T040411Z",
        ("SessionStart", "UserPromptSubmit", "Stop", "SessionEnd"),
        "lost",
        "ready",
        "success",
        1,
    ),
    RunSpec(
        "t2",
        RUN_ROOT_BASE / "t2" / "run-20261020T040614Z",
        ("SessionStart", "UserPromptSubmit", "Stop", "SessionEnd"),
        "lost",
        "ready",
        "success",
        1,
    ),
    RunSpec(
        "s2-control",
        RUN_ROOT_BASE / "s2" / "run-20261020T040447Z",
        (),
        "unknown",
        "unknown",
        "none",
        0,
        expected_session_ids=0,
        expected_diagnostic="empty_stream",
    ),
    RunSpec(
        "s0-gac-402",
        RUN_ROOT_BASE / "s0" / "run-20261020T035053Z",
        ("SessionStart", "UserPromptSubmit", "SessionEnd"),
        "lost",
        "unknown",
        "none",
        1,
        expected_terminal_gaps=1,
        expected_diagnostic="session_end_with_open_turn",
    ),
)


def _validate(
    spec: RunSpec, result_rows: list[TimelineRow], final: Posture, session_ids: list[str]
) -> list[str]:
    """Return expected-vs-actual mismatches for one run."""

    if spec.expected_epochs < 0:
        return []
    issues: list[str] = []
    names = tuple(row.event_name for row in result_rows)
    if names != spec.expected_events:
        issues.append(f"event sequence expected {spec.expected_events}, got {names}")
    if final.presence != spec.expected_presence:
        issues.append(f"presence expected {spec.expected_presence}, got {final.presence}")
    if final.turn_phase != spec.expected_phase:
        issues.append(f"phase expected {spec.expected_phase}, got {final.turn_phase}")
    if final.last_turn_result != spec.expected_last_turn:
        issues.append(f"last_turn expected {spec.expected_last_turn}, got {final.last_turn_result}")
    if final.epochs != spec.expected_epochs:
        issues.append(f"epochs expected {spec.expected_epochs}, got {final.epochs}")
    if final.steer_count != spec.expected_steers:
        issues.append(f"steers expected {spec.expected_steers}, got {final.steer_count}")
    if final.compaction_boundaries != spec.expected_compactions:
        issues.append(
            f"compactions expected {spec.expected_compactions}, got {final.compaction_boundaries}"
        )
    if final.allow_settles != spec.expected_allow:
        issues.append(f"allow settles expected {spec.expected_allow}, got {final.allow_settles}")
    if final.deny_settles != spec.expected_deny:
        issues.append(f"deny settles expected {spec.expected_deny}, got {final.deny_settles}")
    if final.terminal_gaps != spec.expected_terminal_gaps:
        issues.append(
            f"terminal gaps expected {spec.expected_terminal_gaps}, got {final.terminal_gaps}"
        )
    if len(session_ids) != spec.expected_session_ids:
        issues.append(f"session ids expected {spec.expected_session_ids}, got {session_ids}")
    if spec.expected_diagnostic is not None and not any(
        item.startswith(spec.expected_diagnostic) for item in final.diagnostics
    ):
        issues.append(f"diagnostic {spec.expected_diagnostic} missing")
    return issues


def replay_run(spec: RunSpec) -> RunResult:
    """Replay one run root and check it against the spec and labels."""

    envelopes = load_envelopes(spec.root / "collector" / "events.ndjson")
    rows, final = replay_envelopes(envelopes)
    session_ids = sorted(
        {obs.session_id for obs in (normalize(env) for env in envelopes) if obs.session_id}
    )
    collector_status = _load_json(spec.root / "collector" / "collector.json")
    validation = _validate(spec, rows, final, session_ids)
    label_checks = check_labels(spec.root, rows, final)
    return RunResult(
        spec=spec,
        rows=tuple(rows),
        final=final,
        event_names=tuple(row.event_name for row in rows),
        session_ids=tuple(session_ids),
        collector_status=collector_status,
        validation=tuple(validation),
        label_checks=tuple(label_checks),
    )


def _print_timeline(result: RunResult) -> None:
    """Print one row per replayed event."""

    print("  seq event                 turn_id      presence  phase    blocked maint last_turn")
    for row in result.rows:
        turn = (row.turn_id or "-")[:12]
        print(
            f"  {str(row.sequence):>3} {row.event_name:<20} {turn:<12} "
            f"{row.presence:<9} {row.turn_phase:<8} {str(row.blocked):<7} "
            f"{str(row.maintenance_active):<5} {row.last_turn_result}"
        )


def _print_result(result: RunResult, *, timeline: bool) -> None:
    """Print one run summary, validation, and label agreement."""

    final = result.final
    print(f"=== {result.spec.name}  {result.spec.root}")
    print(
        f"  events={len(result.rows)} epochs={final.epochs} steers={final.steer_count} "
        f"compactions={final.compaction_boundaries} allow={final.allow_settles} "
        f"deny={final.deny_settles} gaps={final.terminal_gaps}"
    )
    print(
        f"  final: presence={final.presence} phase={final.turn_phase} "
        f"last_turn={final.last_turn_result} work={final.work} generation={final.generation}"
    )
    if result.collector_status is not None:
        print(
            "  collector: status={} last_heartbeat={}".format(
                result.collector_status.get("status"),
                result.collector_status.get("last_heartbeat_at_utc"),
            )
        )
    if final.diagnostics:
        print("  diagnostics: " + ", ".join(final.diagnostics))
    if timeline:
        _print_timeline(result)
    if result.validation:
        print("  EXPECTATION MISMATCH:")
        for issue in result.validation:
            print(f"    - {issue}")
    else:
        print("  expectation: OK")
    if result.label_checks:
        print("  labels:")
        for check in result.label_checks:
            print(
                f"    {check.label_id:<28} expected={check.expected:<24} "
                f"start={check.start_phase:<10} end={check.end_phase:<10} "
                f"last_turn={check.end_last_turn:<12} {check.verdict}"
            )


def _synthetic_envelope(sequence: int, event_name: str, **fields: Any) -> Envelope:
    """Build one synthetic HTTP envelope for the self-test."""

    payload = {"hook_event_name": event_name, **fields}
    return Envelope(
        sequence=sequence,
        received_at_utc=f"2026-01-01T00:00:00.{sequence:03d}+00:00",
        received_at_monotonic=float(sequence),
        channel_generation=1,
        via="http",
        provider_event=payload,
    )


def self_test() -> int:
    """Run synthetic streams covering the required reducer cases."""

    checks: list[tuple[str, bool, str]] = []

    normal = [
        _synthetic_envelope(1, "SessionStart", source="startup", session_id="s1"),
        _synthetic_envelope(2, "UserPromptSubmit", turn_id="t1"),
        _synthetic_envelope(
            3,
            "PreToolUse",
            turn_id="t1",
            tool_name="Bash",
            tool_use_id="u1",
            tool_input={"command": "echo hi"},
        ),
        _synthetic_envelope(
            4,
            "PostToolUse",
            turn_id="t1",
            tool_name="Bash",
            tool_use_id="u1",
            tool_input={"command": "echo hi"},
        ),
        _synthetic_envelope(5, "Stop", turn_id="t1", stop_hook_active=False),
        _synthetic_envelope(6, "SessionEnd", reason="other"),
    ]
    _, final = replay_envelopes(normal)
    checks.append(
        (
            "normal-turn",
            final.presence == "lost"
            and final.turn_phase == "ready"
            and final.last_turn_result == "success"
            and final.epochs == 1,
            f"presence={final.presence} phase={final.turn_phase} result={final.last_turn_result}",
        )
    )

    blocked_allow = [
        _synthetic_envelope(1, "SessionStart", source="startup", session_id="s1"),
        _synthetic_envelope(2, "UserPromptSubmit", turn_id="t1"),
        _synthetic_envelope(
            3,
            "PreToolUse",
            turn_id="t1",
            tool_name="Bash",
            tool_use_id="u1",
            tool_input={"command": "echo hi"},
        ),
        _synthetic_envelope(
            4,
            "PermissionRequest",
            turn_id="t1",
            tool_name="Bash",
            tool_input={"command": "echo hi", "description": "write"},
        ),
        _synthetic_envelope(
            5,
            "PostToolUse",
            turn_id="t1",
            tool_name="Bash",
            tool_use_id="u1",
            tool_input={"command": "echo hi"},
            tool_response="",
        ),
        _synthetic_envelope(6, "Stop", turn_id="t1", stop_hook_active=False),
    ]
    rows, final = replay_envelopes(blocked_allow)
    checks.append(
        (
            "blocked-allow",
            any(row.blocked for row in rows)
            and final.allow_settles == 1
            and final.last_turn_result == "success",
            f"blocked_seen={any(row.blocked for row in rows)} allow={final.allow_settles}",
        )
    )

    blocked_deny = [
        _synthetic_envelope(1, "SessionStart", source="startup", session_id="s1"),
        _synthetic_envelope(2, "UserPromptSubmit", turn_id="t1"),
        _synthetic_envelope(
            3,
            "PreToolUse",
            turn_id="t1",
            tool_name="Bash",
            tool_use_id="u1",
            tool_input={"command": "echo hi"},
        ),
        _synthetic_envelope(
            4,
            "PermissionRequest",
            turn_id="t1",
            tool_name="Bash",
            tool_input={"command": "echo hi", "description": "write"},
        ),
        _synthetic_envelope(5, "Interrupt", turn_id="t1"),
        _synthetic_envelope(6, "SessionEnd", reason="other"),
    ]
    _, final = replay_envelopes(blocked_deny)
    checks.append(
        (
            "blocked-deny",
            final.deny_settles == 1
            and final.last_turn_result == "interrupted"
            and not any("Stop" in row.event_name for row in replay_envelopes(blocked_deny)[0]),
            f"deny={final.deny_settles} result={final.last_turn_result}",
        )
    )

    compaction = [
        _synthetic_envelope(1, "SessionStart", source="startup", session_id="s1"),
        _synthetic_envelope(2, "UserPromptSubmit", turn_id="t1"),
        _synthetic_envelope(3, "Stop", turn_id="t1", stop_hook_active=False),
        _synthetic_envelope(4, "PreCompact", turn_id="tc", trigger="manual"),
        _synthetic_envelope(5, "PostCompact", turn_id="tc", trigger="manual"),
        _synthetic_envelope(6, "SessionStart", source="compact", session_id="s1"),
        _synthetic_envelope(7, "UserPromptSubmit", turn_id="t2"),
        _synthetic_envelope(8, "Stop", turn_id="t2", stop_hook_active=False),
        _synthetic_envelope(9, "SessionEnd", reason="other"),
    ]
    rows, final = replay_envelopes(compaction)
    checks.append(
        (
            "compaction-window",
            final.compaction_boundaries == 1
            and final.epochs == 2
            and final.last_turn_result == "success"
            and any(row.maintenance_active for row in rows),
            f"compactions={final.compaction_boundaries} epochs={final.epochs}",
        )
    )

    terminal_gap = [
        _synthetic_envelope(1, "SessionStart", source="startup", session_id="s1"),
        _synthetic_envelope(2, "UserPromptSubmit", turn_id="t1"),
    ]
    rows, final = replay_envelopes(terminal_gap)
    checks.append(
        (
            "terminal-gap",
            final.presence == "lost"
            and final.turn_phase == "unknown"
            and final.last_turn_result == "none"
            and final.terminal_gaps == 1
            and any(item.startswith("terminal_gap") for item in final.diagnostics),
            f"presence={final.presence} phase={final.turn_phase} gaps={final.terminal_gaps}",
        )
    )

    steer = [
        _synthetic_envelope(1, "SessionStart", source="startup", session_id="s1"),
        _synthetic_envelope(2, "UserPromptSubmit", turn_id="t1"),
        _synthetic_envelope(3, "UserPromptSubmit", turn_id="t1"),
        _synthetic_envelope(4, "Stop", turn_id="t1", stop_hook_active=False),
        _synthetic_envelope(5, "SessionEnd", reason="other"),
    ]
    _, final = replay_envelopes(steer)
    checks.append(
        (
            "steer-same-turn",
            final.steer_count == 1 and final.epochs == 1 and final.last_turn_result == "success",
            f"steers={final.steer_count} epochs={final.epochs}",
        )
    )

    continuation = [
        _synthetic_envelope(1, "SessionStart", source="startup", session_id="s1"),
        _synthetic_envelope(2, "UserPromptSubmit", turn_id="t1"),
        _synthetic_envelope(3, "Stop", turn_id="t1", stop_hook_active=True),
        _synthetic_envelope(4, "Stop", turn_id="t1", stop_hook_active=False),
    ]
    _, final = replay_envelopes(continuation)
    checks.append(
        (
            "stop-hook-active",
            final.last_turn_result == "success"
            and any("stop_hook_active_continuation" in item for item in final.diagnostics),
            f"result={final.last_turn_result}",
        )
    )

    model_request = [
        _synthetic_envelope(1, "SessionStart", source="startup", session_id="s1"),
        _synthetic_envelope(2, "PreModelRequest", turn_id="t1"),
    ]
    _, final = replay_envelopes(model_request)
    checks.append(
        (
            "model-request-unavailable",
            final.last_turn_result == "none"
            and any("model_request_event_unavailable" in item for item in final.diagnostics),
            ",".join(final.diagnostics),
        )
    )

    failed = 0
    for name, ok, note in checks:
        print(f"{'PASS' if ok else 'FAIL'} {name}" + (f" ({note})" if note else ""))
        if not ok:
            failed += 1
    print(f"REPLAY SELF-TEST {'PASSED' if failed == 0 else f'{failed} CHECK(S) FAILED'}")
    return 0 if failed == 0 else 1


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint: replay the campaign runs or run the synthetic self-test."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, default=None, help="one run root to replay")
    parser.add_argument("--all", action="store_true", help="replay the iteration-1 run matrix")
    parser.add_argument("--timeline", action="store_true", help="print one row per event")
    parser.add_argument("--no-labels", action="store_true", help="skip label checks")
    parser.add_argument("--self-test", action="store_true", help="run synthetic reducer checks")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()

    specs: tuple[RunSpec, ...]
    if args.run_root is not None:
        root = args.run_root.expanduser().resolve()
        specs = (
            RunSpec(
                name=root.name,
                root=root,
                expected_events=(),
                expected_presence="",
                expected_phase="",
                expected_last_turn="",
                expected_epochs=-1,
                expected_session_ids=-1,
            ),
        )
    else:
        specs = RUN_SPECS

    failed = 0
    for spec in specs:
        result = replay_run(spec)
        if args.no_labels:
            result = RunResult(
                spec=result.spec,
                rows=result.rows,
                final=result.final,
                event_names=result.event_names,
                session_ids=result.session_ids,
                collector_status=result.collector_status,
                validation=result.validation,
                label_checks=(),
            )
        _print_result(result, timeline=args.timeline or args.run_root is not None)
        if result.validation:
            failed += 1
        for check in result.label_checks:
            if check.verdict == "MISMATCH":
                failed += 1
    if len(specs) > 1:
        print(f"\nREPLAY RESULT: {'PASS' if failed == 0 else f'{failed} ISSUE(S)'}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
