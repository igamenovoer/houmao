"""Replay Kimi hook streams into merged posture timelines (throwaway E3/E4 arm).

Standalone, stdlib-only normalizer and posture reducer for the 2026-10-20 Kimi
Code hook-observation campaign. It replays ``collector/events.ndjson`` streams
with the archived Claude merge rules adapted to Kimi's event shapes: no
``turn_id`` on tool events, a ``PermissionResult``-settled blocked window, a
turn-preserving deny path, lazy ``SessionStart`` creation, per-generation
``turn_id`` restart, real ``PreCompact``/``PostCompact``, a hook-settled
``Interrupt``, and terminal-gap plus headless-no-``SessionEnd`` fallbacks.

It does not import the production reducer and does not write to the run roots.
Determinism: ordering and virtual time come from the stream's own
``received_at_monotonic`` / ``received_at_utc`` stamps (fallback envelopes have
``sequence: null`` and are ordered by ``emitter_seq``). No wall clock is read.

Run roots are discovered under ``tmp/kimi-hook-capture/``; campaign capture
roots are replayed with their expected stream shape, harness G0 self-test roots
are named and skipped.
"""

from __future__ import annotations

import argparse
import json
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
RUN_ROOT_BASE = REPO_ROOT / "tmp" / "kimi-hook-capture"

HEARTBEAT_INTERVAL_SECONDS = 60.0
LABEL_LOOKAROUND_SECONDS = 3.0
LABEL_LOOKBEHIND_SECONDS = 3.0

KIMI_EVENTS: frozenset[str] = frozenset(
    {
        "PreToolUse",
        "PostToolUse",
        "PostToolUseFailure",
        "PermissionRequest",
        "PermissionResult",
        "UserPromptSubmit",
        "UserPromptQueued",
        "TurnStarted",
        "Stop",
        "StopFailure",
        "Interrupt",
        "SessionStart",
        "SessionEnd",
        "SessionHeartbeat",
        "SubagentStart",
        "SubagentStop",
        "TaskStarted",
        "PreCompact",
        "PostCompact",
        "Notification",
    }
)


@dataclass(frozen=True)
class Envelope:
    """One collector event row, including file-fallback rows."""

    sequence: int | None
    emitter_seq: int | None
    received_at_utc: str
    received_at_monotonic: float
    channel_generation: int
    via: str
    provider_event: dict[str, Any]

    def effective_sequence(self) -> int:
        """Return the ordering sequence: collector sequence or emitter sequence."""

        if self.sequence is not None:
            return self.sequence
        if self.emitter_seq is not None:
            return self.emitter_seq
        return -1

    def duplicate_key(self) -> tuple[int, str, int]:
        """Return the dedup key; HTTP and fallback counters are independent."""

        channel = "fallback" if self.sequence is None else "http"
        return (self.channel_generation, channel, self.effective_sequence())


@dataclass(frozen=True)
class RunMeta:
    """Run-level metadata used by the terminal fallbacks."""

    scenario: str
    headless: bool
    process_returncode: int | None
    finished_at_utc: str | None


@dataclass(frozen=True)
class Observation:
    """Provider event normalized into the reducer vocabulary."""

    kind: str
    event_name: str
    sequence: int | None
    emitter_seq: int | None
    received_at_utc: str
    received_at_monotonic: float
    generation: int
    via: str
    session_id: str | None = None
    turn_id: int | None = None
    tool_name: str | None = None
    tool_call_id: str | None = None
    tool_command: str | None = None
    source: str | None = None
    reason: str | None = None
    trigger: str | None = None
    decision: str | None = None
    origin_kind: str | None = None
    origin_name: str | None = None
    is_steer: bool | None = None
    stop_hook_active: bool | None = None
    prompt_text: str | None = None
    queue_length: int | None = None
    error_code: str | None = None


@dataclass(frozen=True)
class Posture:
    """One merged posture snapshot for the Kimi hook channel."""

    presence: str
    turn_phase: str
    work: str
    blocked: bool
    blocked_tool_name: str | None
    blocked_tool_call_id: str | None
    maintenance_active: bool
    turn_id: int | None
    session_id: str | None
    generation: int | None
    resume_started: bool
    last_turn_result: str
    last_turn_source: str
    last_terminal_turn_id: int | None
    epochs: int
    epoch_turn_ids: tuple[int | None, ...]
    steers: int
    queued_prompts: int
    compaction_boundaries: int
    permission_requests: int
    blocked_windows: int
    allow_settles: int
    deny_settles: int
    interrupts: int
    subagent_starts: int
    subagent_stops: int
    nested_scopes: int
    pre_tool_uses: int
    post_tool_uses: int
    tool_failures: int
    tool_pairs: int
    unpaired_post_tool_uses: int
    heartbeats: int
    last_heartbeat_at_utc: str | None
    terminal_gaps: int
    orphan_terminals: int
    events_seen: int
    fallback_events: int
    gap_silence_seconds: float | None
    diagnostics: tuple[str, ...]
    last_event: str | None
    last_event_at_utc: str | None


@dataclass(frozen=True)
class TimelineRow:
    """One event plus the posture produced immediately after it."""

    sequence: int | None
    emitter_seq: int | None
    event_name: str
    received_at_utc: str
    received_at_monotonic: float
    generation: int
    turn_id: int | None
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
    expected_turn_ids: tuple[int | None, ...] | None = None
    expected_steers: int = 0
    expected_queued: int = 0
    expected_compactions: int = 0
    expected_allow: int = 0
    expected_deny: int = 0
    expected_interrupts: int = 0
    expected_subagents: tuple[int, int] = (0, 0)
    expected_heartbeats: int = 0
    expected_terminal_gaps: int = 0
    expected_fallback: int = 0
    expected_generations: int = 1
    expected_resumes: int = 0
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
    generations: tuple[int, ...]
    meta: RunMeta
    collector_status: dict[str, Any] | None
    validation: tuple[str, ...]
    label_checks: tuple[LabelCheck, ...]


KIND_BY_EVENT: dict[str, str] = {
    "SessionStart": "session_start",
    "UserPromptSubmit": "prompt_submitted",
    "UserPromptQueued": "prompt_queued",
    "TurnStarted": "turn_started",
    "Stop": "turn_stopped",
    "StopFailure": "turn_failed",
    "Interrupt": "turn_interrupted",
    "SessionEnd": "session_ended",
    "SessionHeartbeat": "session_heartbeat",
    "PreToolUse": "pre_tool_use",
    "PostToolUse": "post_tool_use",
    "PostToolUseFailure": "post_tool_use_failure",
    "PermissionRequest": "permission_requested",
    "PermissionResult": "permission_resolved",
    "PreCompact": "maintenance_started",
    "PostCompact": "maintenance_ended",
    "SubagentStart": "subagent_started",
    "SubagentStop": "subagent_stopped",
    "TaskStarted": "task_started_unavailable",
    "Notification": "notification_unavailable",
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


def _optional_int(payload: dict[str, Any], key: str) -> int | None:
    """Return one integer field, accepting a numeric string defensively."""

    value = payload.get(key)
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _tool_command(payload: dict[str, Any]) -> str | None:
    """Return the shell command from a tool payload, when present."""

    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return None
    return _optional_str(tool_input, "command")


def _prompt_text(payload: dict[str, Any]) -> str | None:
    """Collapse a ContentPart[] prompt or a plain string prompt to text."""

    value = payload.get("prompt")
    if isinstance(value, str):
        return value or None
    if not isinstance(value, list):
        return None
    parts: list[str] = []
    for part in value:
        if not isinstance(part, dict):
            continue
        text = part.get("text")
        if isinstance(text, str):
            parts.append(text)
    joined = "".join(parts)
    return joined or None


def _error_code(payload: dict[str, Any]) -> str | None:
    """Return ``error.code`` from a PostToolUseFailure payload."""

    error = payload.get("error")
    if not isinstance(error, dict):
        return None
    return _optional_str(error, "code")


def normalize(envelope: Envelope) -> Observation:
    """Normalize one collector envelope into one observation."""

    payload = envelope.provider_event
    event_name = _optional_str(payload, "hook_event_name") or "<malformed>"
    kind = KIND_BY_EVENT.get(event_name, "unknown")
    return Observation(
        kind=kind,
        event_name=event_name,
        sequence=envelope.sequence,
        emitter_seq=envelope.emitter_seq,
        received_at_utc=envelope.received_at_utc,
        received_at_monotonic=envelope.received_at_monotonic,
        generation=envelope.channel_generation,
        via=envelope.via,
        session_id=_optional_str(payload, "session_id"),
        turn_id=_optional_int(payload, "turn_id"),
        tool_name=_optional_str(payload, "tool_name"),
        tool_call_id=_optional_str(payload, "tool_call_id"),
        tool_command=_tool_command(payload),
        source=_optional_str(payload, "source"),
        reason=_optional_str(payload, "reason"),
        trigger=_optional_str(payload, "trigger"),
        decision=_optional_str(payload, "decision"),
        origin_kind=_optional_str(payload, "origin_kind"),
        origin_name=_optional_str(payload, "origin_name"),
        is_steer=_optional_bool(payload, "is_steer"),
        stop_hook_active=_optional_bool(payload, "stop_hook_active"),
        prompt_text=_prompt_text(payload),
        queue_length=_optional_int(payload, "queue_length"),
        error_code=_error_code(payload),
    )


class Reducer:
    """Pure Kimi posture reducer; one observation per call, arrival order."""

    def __init__(self) -> None:
        """Initialize the empty posture."""

        self.m_presence = "unknown"
        self.m_turn_phase = "unknown"
        self.m_work = "unknown"
        self.m_blocked = False
        self.m_blocked_tool_name: str | None = None
        self.m_blocked_tool_call_id: str | None = None
        self.m_maintenance_active = False
        self.m_pre_maintenance_phase: str | None = None
        self.m_turn_id: int | None = None
        self.m_session_id: str | None = None
        self.m_generation: int | None = None
        self.m_resume_started = False
        self.m_last_turn_result = "none"
        self.m_last_turn_source = "none"
        self.m_last_terminal_turn_id: int | None = None
        self.m_epochs = 0
        self.m_epoch_turn_ids: list[int | None] = []
        self.m_pending_epoch = False
        self.m_pending_prompts = 0
        self.m_steers = 0
        self.m_queued_prompts = 0
        self.m_compaction_boundaries = 0
        self.m_compaction_freshness_pending: int | None = None
        self.m_permission_requests = 0
        self.m_blocked_windows = 0
        self.m_allow_settles = 0
        self.m_deny_settles = 0
        self.m_interrupts = 0
        self.m_subagent_starts = 0
        self.m_subagent_stops = 0
        self.m_nested_scopes = 0
        self.m_heartbeats = 0
        self.m_last_heartbeat_at_utc: str | None = None
        self.m_terminal_gaps = 0
        self.m_orphan_terminals = 0
        self.m_pre_tool_uses = 0
        self.m_post_tool_uses = 0
        self.m_tool_failures = 0
        self.m_tool_pairs = 0
        self.m_unpaired_post_tool_uses = 0
        self.m_pending_tool_calls: dict[str, str] = {}
        self.m_work_diagnosed = False
        self.m_events_seen = 0
        self.m_fallback_events = 0
        self.m_seen_keys: set[tuple[int, str, int]] = set()
        self.m_diagnostics: list[str] = []
        self.m_last_event: str | None = None
        self.m_last_event_at_utc: str | None = None
        self.m_last_event_monotonic: float | None = None
        self.m_gap_silence_seconds: float | None = None

    def posture(self) -> Posture:
        """Return the current immutable posture snapshot."""

        return Posture(
            presence=self.m_presence,
            turn_phase=self.m_turn_phase,
            work=self.m_work,
            blocked=self.m_blocked,
            blocked_tool_name=self.m_blocked_tool_name,
            blocked_tool_call_id=self.m_blocked_tool_call_id,
            maintenance_active=self.m_maintenance_active,
            turn_id=self.m_turn_id,
            session_id=self.m_session_id,
            generation=self.m_generation,
            resume_started=self.m_resume_started,
            last_turn_result=self.m_last_turn_result,
            last_turn_source=self.m_last_turn_source,
            last_terminal_turn_id=self.m_last_terminal_turn_id,
            epochs=self.m_epochs,
            epoch_turn_ids=tuple(self.m_epoch_turn_ids),
            steers=self.m_steers,
            queued_prompts=self.m_queued_prompts,
            compaction_boundaries=self.m_compaction_boundaries,
            permission_requests=self.m_permission_requests,
            blocked_windows=self.m_blocked_windows,
            allow_settles=self.m_allow_settles,
            deny_settles=self.m_deny_settles,
            interrupts=self.m_interrupts,
            subagent_starts=self.m_subagent_starts,
            subagent_stops=self.m_subagent_stops,
            nested_scopes=self.m_nested_scopes,
            pre_tool_uses=self.m_pre_tool_uses,
            post_tool_uses=self.m_post_tool_uses,
            tool_failures=self.m_tool_failures,
            tool_pairs=self.m_tool_pairs,
            unpaired_post_tool_uses=self.m_unpaired_post_tool_uses,
            heartbeats=self.m_heartbeats,
            last_heartbeat_at_utc=self.m_last_heartbeat_at_utc,
            terminal_gaps=self.m_terminal_gaps,
            orphan_terminals=self.m_orphan_terminals,
            events_seen=self.m_events_seen,
            fallback_events=self.m_fallback_events,
            gap_silence_seconds=self.m_gap_silence_seconds,
            diagnostics=tuple(self.m_diagnostics),
            last_event=self.m_last_event,
            last_event_at_utc=self.m_last_event_at_utc,
        )

    def reduce(self, observation: Observation) -> Posture:
        """Consume one observation and return the new posture."""

        self.m_events_seen += 1
        if self.m_generation is None:
            self.m_generation = observation.generation
        elif observation.generation < self.m_generation:
            self._diag("hook_orphan_generation", str(observation.generation))
            return self.posture()
        elif observation.generation > self.m_generation:
            self._reset_generation(observation.generation)

        key = observation_key(observation)
        if key in self.m_seen_keys:
            self._diag("duplicate_event", observation.event_name)
            return self.posture()
        self.m_seen_keys.add(key)

        self.m_last_event = observation.event_name
        self.m_last_event_at_utc = observation.received_at_utc
        self.m_last_event_monotonic = observation.received_at_monotonic
        if observation.via == "command_fallback":
            self.m_fallback_events += 1
            self._diag("fallback_delivery", observation.event_name)

        if observation.kind == "session_start":
            self._apply_session_start(observation)
        elif observation.kind == "prompt_submitted":
            self._apply_prompt_submitted(observation)
        elif observation.kind == "prompt_queued":
            self._apply_prompt_queued(observation)
        elif observation.kind == "turn_started":
            self._apply_turn_started(observation)
        elif observation.kind == "pre_tool_use":
            self._apply_pre_tool_use(observation)
        elif observation.kind == "post_tool_use":
            self._apply_post_tool_use(observation)
        elif observation.kind == "post_tool_use_failure":
            self._apply_post_tool_use_failure(observation)
        elif observation.kind == "permission_requested":
            self._apply_permission_requested(observation)
        elif observation.kind == "permission_resolved":
            self._apply_permission_resolved(observation)
        elif observation.kind == "turn_stopped":
            self._apply_turn_stopped(observation)
        elif observation.kind == "turn_failed":
            self._apply_turn_failed(observation)
        elif observation.kind == "turn_interrupted":
            self._apply_turn_interrupted(observation)
        elif observation.kind == "maintenance_started":
            self._apply_maintenance_started(observation)
        elif observation.kind == "maintenance_ended":
            self._apply_maintenance_ended(observation)
        elif observation.kind == "session_ended":
            self._apply_session_ended(observation)
        elif observation.kind == "session_heartbeat":
            self._apply_session_heartbeat(observation)
        elif observation.kind == "subagent_started":
            self._apply_subagent_started(observation)
        elif observation.kind == "subagent_stopped":
            self._apply_subagent_stopped(observation)
        elif observation.kind == "task_started_unavailable":
            self._diag("task_started_unobserved", observation.event_name)
        elif observation.kind == "notification_unavailable":
            self._diag("notification_unobserved", observation.event_name)
        else:
            self._diag("unknown_event", observation.event_name)
        return self.posture()

    def finish(
        self,
        *,
        reason: str = "stream_end",
        headless: bool = False,
        process_returncode: int | None = None,
        finished_at_utc: str | None = None,
    ) -> Posture:
        """Close the stream and apply the terminal-gap / headless fallbacks."""

        self.m_gap_silence_seconds = _silence_seconds(self.m_last_event_at_utc, finished_at_utc)
        if self.m_events_seen == 0:
            self._diag("empty_stream", reason)
            return self.posture()
        open_turn = (
            self.m_turn_phase in ("active", "blocked")
            or self.m_turn_id is not None
            or self.m_pending_epoch
        )
        if open_turn:
            self.m_terminal_gaps += 1
            self._diag("terminal_gap", f"{reason}:open_turn")
            if self.m_heartbeats == 0:
                self._diag("heartbeat_liveness_unavailable", "no first 60 s tick")
            if self.m_presence == "present":
                self.m_presence = "lost"
            self.m_turn_phase = "unknown"
            self.m_turn_id = None
            self.m_blocked = False
            self.m_blocked_tool_name = None
            self.m_blocked_tool_call_id = None
            self.m_pending_epoch = False
            self.m_nested_scopes = 0
            self.m_last_turn_result = "none"
            self.m_last_turn_source = "none"
        elif self.m_presence == "present":
            if headless and process_returncode == 0:
                self.m_presence = "lost"
                self._diag("headless_session_end_gap", "clean process exit, no SessionEnd")
                if self.m_last_turn_result == "success":
                    self._diag("headless_terminal_settled", "Stop latched before exit")
            else:
                self.m_presence = "unknown"
                self._diag("stream_end_without_session_end", reason)
        return self.posture()

    def _apply_session_start(self, observation: Observation) -> None:
        """Establish presence and reset turn state for a fresh generation."""

        self.m_presence = "present"
        if observation.session_id is not None:
            self.m_session_id = observation.session_id
        if observation.source == "resume":
            self.m_resume_started = True
        elif observation.source in ("startup", "clear", "fork"):
            self.m_resume_started = False

        if observation.source in ("startup", "resume", "clear", "fork"):
            if self.m_turn_phase in ("active", "blocked"):
                self._diag("session_start_during_active_turn", observation.source)
                return
            self._reset_turn()
            self.m_turn_phase = "ready"
        elif observation.source == "compact":
            self.m_compaction_boundaries += 1
            self._diag("compaction_boundary", observation.source)
            if self.m_turn_phase == "unknown":
                self.m_turn_phase = "ready"
        else:
            if self.m_turn_phase == "unknown":
                self.m_turn_phase = "ready"
            if observation.source is not None:
                self._diag("session_start_source_unexercised", observation.source)

    def _apply_prompt_submitted(self, observation: Observation) -> None:
        """Arm a turn at submission; bind the epoch when ``TurnStarted`` arrives."""

        self.m_presence = "present"
        if observation.is_steer is True and self.m_turn_phase in ("active", "blocked"):
            self.m_steers += 1
            self._diag("steer_same_turn", "is_steer=true")
            if self.m_blocked:
                self._diag("steer_during_blocked")
                self.m_blocked = False
                self.m_blocked_tool_name = None
                self.m_blocked_tool_call_id = None
            self.m_turn_phase = "active"
            return
        if observation.is_steer is True:
            self._diag("steer_without_active_turn")
        if self.m_turn_phase in ("active", "blocked"):
            self.m_pending_prompts += 1
            self._diag("prompt_queued_behind_active", str(self.m_pending_prompts))
            return
        if self.m_maintenance_active:
            self._diag("prompt_during_maintenance")
            self.m_maintenance_active = False
            self.m_pre_maintenance_phase = None
        self._arm_prompt(observation.turn_id)

    def _apply_prompt_queued(self, observation: Observation) -> None:
        """Record the queue signal; a steered message stays in the running turn."""

        self.m_presence = "present"
        self.m_queued_prompts += 1
        length = observation.queue_length if observation.queue_length is not None else 0
        if self.m_turn_phase in ("active", "blocked"):
            self._diag("steer_into_active_turn", f"queue_length={length}")
        else:
            self._diag("queue_without_active_turn", f"queue_length={length}")

    def _apply_turn_started(self, observation: Observation) -> None:
        """Bind the operator epoch's ``turn_id``; nested turns stay non-terminal."""

        self.m_presence = "present"
        nested = (
            observation.origin_kind == "system_trigger" or observation.origin_name == "subagent"
        )
        if nested:
            self.m_nested_scopes += 1
            self._diag("subagent_turn_started", observation.origin_name or "system_trigger")
            return
        if observation.turn_id is None:
            self._diag("turn_started_without_turn_id")
            return
        if self.m_pending_epoch or (
            self.m_turn_phase in ("active", "blocked") and self.m_turn_id is None
        ):
            self.m_turn_id = observation.turn_id
            self.m_pending_epoch = False
            if self.m_epoch_turn_ids:
                self.m_epoch_turn_ids[-1] = observation.turn_id
            self._diag("turn_id_bound", str(observation.turn_id))
            self._check_compaction_freshness(observation.turn_id)
            if self.m_turn_phase == "unknown":
                self.m_turn_phase = "active"
            return
        if self.m_turn_phase in ("active", "blocked") and self.m_turn_id is not None:
            if observation.turn_id == self.m_turn_id:
                self._diag("duplicate_turn_started", str(observation.turn_id))
                return
            self._diag(
                "turn_started_new_epoch_without_prompt",
                f"{self.m_turn_id}->{observation.turn_id}",
            )
        else:
            self._diag("turn_started_without_prompt", str(observation.turn_id))
        self._arm_prompt(observation.turn_id)
        self.m_pending_epoch = False
        if self.m_epoch_turn_ids:
            self.m_epoch_turn_ids[-1] = observation.turn_id
        self._check_compaction_freshness(observation.turn_id)

    def _apply_pre_tool_use(self, observation: Observation) -> None:
        """Record a tool call; tool events have no ``turn_id`` at 2.2.0."""

        self.m_presence = "present"
        self.m_pre_tool_uses += 1
        if observation.turn_id is not None:
            self._diag("tool_event_turn_id_present", observation.event_name)
        if self.m_turn_phase == "blocked":
            self._diag("pre_tool_use_during_blocked", observation.tool_name or "?")
        elif self.m_turn_id is not None or self.m_pending_epoch:
            self.m_turn_phase = "active"
        else:
            self._diag("tool_without_turn", observation.tool_name or "?")
        if observation.tool_call_id is not None:
            self.m_pending_tool_calls[observation.tool_call_id] = observation.tool_name or "?"

    def _apply_post_tool_use(self, observation: Observation) -> None:
        """Pair the tool call; a blocked window is held until PermissionResult."""

        self.m_presence = "present"
        self.m_post_tool_uses += 1
        self._consume_tool_call(observation)
        if self.m_turn_phase == "blocked":
            self._diag("post_tool_use_during_blocked", observation.tool_name or "?")
            return
        if self.m_turn_id is not None or self.m_pending_epoch:
            self.m_turn_phase = "active"

    def _apply_post_tool_use_failure(self, observation: Observation) -> None:
        """Record a tool failure; the deny path continues to ``Stop``."""

        self.m_presence = "present"
        self.m_tool_failures += 1
        self._consume_tool_call(observation)
        detail = observation.error_code or "unknown"
        self._diag("tool_failure_nonterminal", detail)
        if self.m_turn_phase == "blocked":
            self._diag("blocked_settled_by_tool_failure", observation.tool_name or "?")
            self.m_blocked = False
            self.m_blocked_tool_name = None
            self.m_blocked_tool_call_id = None
        if self.m_turn_id is not None or self.m_pending_epoch:
            self.m_turn_phase = "active"

    def _apply_permission_requested(self, observation: Observation) -> None:
        """Enter the hooks-only blocked posture and pair by ``tool_call_id``."""

        self.m_presence = "present"
        self.m_permission_requests += 1
        self.m_blocked_windows += 1
        if observation.turn_id is not None:
            if self.m_turn_id is None and (self.m_pending_epoch or self.m_turn_phase != "ready"):
                self.m_turn_id = observation.turn_id
                self.m_pending_epoch = False
                if self.m_epoch_turn_ids:
                    self.m_epoch_turn_ids[-1] = observation.turn_id
                self._diag("permission_armed_turn", str(observation.turn_id))
            elif self.m_turn_id is None and not self.m_pending_epoch:
                self._diag("permission_without_armed_prompt", str(observation.turn_id))
                self.m_turn_id = observation.turn_id
                self.m_pending_epoch = False
            elif self.m_turn_id is not None and observation.turn_id != self.m_turn_id:
                self._diag(
                    "permission_turn_mismatch",
                    f"{observation.turn_id}!={self.m_turn_id}",
                )
        if (
            observation.tool_call_id is not None
            and observation.tool_call_id in self.m_pending_tool_calls
        ):
            self._diag("permission_paired", observation.tool_call_id)
        else:
            self._diag("permission_without_pre_tool_use", observation.tool_name or "?")
        self.m_blocked = True
        self.m_blocked_tool_name = observation.tool_name
        self.m_blocked_tool_call_id = observation.tool_call_id
        self.m_turn_phase = "blocked"

    def _apply_permission_resolved(self, observation: Observation) -> None:
        """Settle the blocked window; the turn stays armed until ``Stop``."""

        self.m_presence = "present"
        decision = observation.decision or "unknown"
        if not self.m_blocked:
            self._diag("permission_result_without_blocked", decision)
            return
        self.m_blocked = False
        self.m_blocked_tool_name = None
        self.m_blocked_tool_call_id = None
        if self.m_turn_id is not None or self.m_pending_epoch:
            self.m_turn_phase = "active"
        if decision == "approved":
            self.m_allow_settles += 1
        elif decision == "rejected":
            self.m_deny_settles += 1
        else:
            self._diag("permission_result_unexercised_decision", decision)
        self._diag("blocked_settled", decision)

    def _apply_turn_stopped(self, observation: Observation) -> None:
        """Settle success; a nested or continuation stop is non-terminal."""

        self.m_presence = "present"
        if observation.stop_hook_active is True:
            self._diag("stop_hook_active_continuation", "non-terminal Stop")
            if self.m_turn_id is not None:
                self.m_turn_phase = "active"
            return
        if self.m_nested_scopes > 0:
            self.m_nested_scopes -= 1
            self._diag("nested_turn_stopped", str(self.m_nested_scopes))
            return
        if self.m_turn_phase not in ("active", "blocked"):
            self.m_orphan_terminals += 1
            self._diag("orphan_terminal", "Stop")
            return
        self._settle_terminal("success", self.m_turn_id, "Stop")

    def _apply_turn_failed(self, observation: Observation) -> None:
        """Settle ``known_failure`` when a StopFailure is ever delivered."""

        self.m_presence = "present"
        if self.m_turn_phase not in ("active", "blocked"):
            self.m_orphan_terminals += 1
            self._diag("orphan_terminal", "StopFailure")
            return
        self._diag("stop_failure_unexercised", "StopFailure")
        self._settle_terminal("known_failure", self.m_turn_id, "StopFailure")

    def _apply_turn_interrupted(self, observation: Observation) -> None:
        """Settle interrupted from the hook event; Kimi emits it in place of Stop."""

        self.m_presence = "present"
        self.m_interrupts += 1
        if self.m_turn_id is None and not self.m_pending_epoch:
            if (
                self.m_last_turn_result == "success"
                and observation.turn_id == self.m_last_terminal_turn_id
            ):
                self.m_last_turn_result = "interrupted"
                self.m_last_turn_source = "hook_observation"
                self._diag("hook_success_interrupt_override", str(observation.turn_id))
            else:
                self.m_orphan_terminals += 1
                self._diag("orphan_terminal", "Interrupt")
            return
        if (
            observation.turn_id is not None
            and self.m_turn_id is not None
            and observation.turn_id != self.m_turn_id
        ):
            self.m_orphan_terminals += 1
            self._diag("interrupt_turn_mismatch", f"{observation.turn_id}!={self.m_turn_id}")
            return
        if self.m_blocked:
            self.m_deny_settles += 1
            self._diag("deny_aborted_turn", self.m_blocked_tool_name or "?")
        else:
            self._diag("esc_interrupt", observation.reason or "?")
        self._settle_terminal("interrupted", observation.turn_id or self.m_turn_id, "Interrupt")

    def _apply_maintenance_started(self, observation: Observation) -> None:
        """Hold the current posture through a real PreCompact window."""

        self.m_presence = "present"
        if not self.m_maintenance_active:
            self.m_pre_maintenance_phase = self.m_turn_phase
            self.m_maintenance_active = True
            self.m_compaction_boundaries += 1
            self._diag("maintenance_started", observation.trigger or "unknown")
        if self.m_epoch_turn_ids:
            self.m_compaction_freshness_pending = self.m_epoch_turn_ids[-1]
        if self.m_turn_phase == "unknown":
            self.m_turn_phase = "ready"

    def _apply_maintenance_ended(self, observation: Observation) -> None:
        """Close the compaction window without minting a turn epoch."""

        self.m_maintenance_active = False
        self._diag("maintenance_ended", observation.trigger or "unknown")
        if self.m_turn_phase == "unknown":
            self.m_turn_phase = self.m_pre_maintenance_phase or "ready"
        self.m_pre_maintenance_phase = None

    def _apply_session_ended(self, observation: Observation) -> None:
        """Lose presence; an open turn is an explicit terminal gap."""

        self.m_presence = "lost"
        self._diag("session_end", observation.reason or "unknown")
        if (
            self.m_turn_phase in ("active", "blocked")
            or self.m_turn_id is not None
            or self.m_pending_epoch
        ):
            self.m_terminal_gaps += 1
            self._diag("session_end_with_open_turn", str(self.m_turn_id))
            self.m_turn_phase = "unknown"
            self.m_turn_id = None
            self.m_blocked = False
            self.m_blocked_tool_name = None
            self.m_blocked_tool_call_id = None
            self.m_pending_epoch = False
            self.m_nested_scopes = 0
            self.m_last_turn_result = "none"
            self.m_last_turn_source = "none"
        self.m_maintenance_active = False
        self.m_pre_maintenance_phase = None

    def _apply_session_heartbeat(self, observation: Observation) -> None:
        """Record liveness; the payload's ``uptime_ms`` is diagnostic only."""

        self.m_presence = "present"
        self.m_heartbeats += 1
        self.m_last_heartbeat_at_utc = observation.received_at_utc
        if self.m_heartbeats == 1:
            self._diag("heartbeat_observed", "60 s cadence")

    def _apply_subagent_started(self, observation: Observation) -> None:
        """Open a nested scope for a subagent run."""

        self.m_presence = "present"
        self.m_subagent_starts += 1
        self._diag("subagent_started", observation.tool_name or "agent")
        self.m_nested_scopes += 1

    def _apply_subagent_stopped(self, observation: Observation) -> None:
        """Close the nested scope; the parent turn stays active."""

        self.m_presence = "present"
        self.m_subagent_stops += 1
        self._diag("subagent_stopped", observation.tool_name or "agent")
        if self.m_nested_scopes > 0:
            self.m_nested_scopes -= 1
        else:
            self._diag("subagent_stop_without_scope")

    def _arm_prompt(self, turn_id: int | None) -> None:
        """Start a new operator epoch and clear the previous terminal latch."""

        self.m_turn_id = turn_id
        self.m_pending_epoch = turn_id is None
        self.m_turn_phase = "active"
        self.m_blocked = False
        self.m_blocked_tool_name = None
        self.m_blocked_tool_call_id = None
        self.m_last_turn_result = "none"
        self.m_last_turn_source = "none"
        self.m_last_terminal_turn_id = None
        self.m_pending_tool_calls.clear()
        self.m_epochs += 1
        self.m_epoch_turn_ids.append(turn_id)

    def _settle_terminal(self, result: str, turn_id: int | None, event_name: str) -> None:
        """Latch one terminal result and return to ready."""

        self.m_last_turn_result = result
        self.m_last_turn_source = "hook_observation"
        self.m_last_terminal_turn_id = turn_id
        self.m_turn_phase = "ready"
        self.m_turn_id = None
        self.m_pending_epoch = False
        self.m_blocked = False
        self.m_blocked_tool_name = None
        self.m_blocked_tool_call_id = None
        self.m_pending_tool_calls.clear()
        self._diag("terminal_latched", f"{event_name}:{result}")
        if self.m_work == "unknown" and not self.m_work_diagnosed:
            self.m_work_diagnosed = True
            self._diag("work_signal_unavailable", "Stop has no background_tasks field")
        if self.m_pending_prompts > 0:
            self.m_pending_prompts -= 1
            self._diag("queued_prompt_drained", str(self.m_pending_prompts))
            self._arm_prompt(None)

    def _consume_tool_call(self, observation: Observation) -> None:
        """Pair a post-tool event with its pending ``PreToolUse`` by id."""

        if observation.tool_call_id is None:
            self.m_unpaired_post_tool_uses += 1
            self._diag("tool_event_without_tool_call_id", observation.event_name)
            return
        if observation.tool_call_id in self.m_pending_tool_calls:
            self.m_tool_pairs += 1
            del self.m_pending_tool_calls[observation.tool_call_id]
            return
        self.m_unpaired_post_tool_uses += 1
        self._diag("post_tool_use_without_pre_tool_use", observation.tool_call_id)

    def _check_compaction_freshness(self, turn_id: int) -> None:
        """Name whether the post-compact turn reused or minted a ``turn_id``."""

        if self.m_compaction_freshness_pending is None:
            return
        previous = self.m_compaction_freshness_pending
        self.m_compaction_freshness_pending = None
        if turn_id != previous:
            self._diag("post_compaction_fresh_turn_id", f"{previous}->{turn_id}")
        else:
            self._diag("post_compaction_turn_id_reused", str(turn_id))

    def _reset_turn(self) -> None:
        """Reset turn-scoped state for a new session generation."""

        self.m_turn_id = None
        self.m_turn_phase = "ready"
        self.m_pending_epoch = False
        self.m_pending_prompts = 0
        self.m_blocked = False
        self.m_blocked_tool_name = None
        self.m_blocked_tool_call_id = None
        self.m_maintenance_active = False
        self.m_pre_maintenance_phase = None
        self.m_compaction_freshness_pending = None
        self.m_pending_tool_calls.clear()
        self.m_last_turn_result = "none"
        self.m_last_turn_source = "none"
        self.m_last_terminal_turn_id = None
        self.m_nested_scopes = 0

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


def observation_key(observation: Observation) -> tuple[int, str, int]:
    """Return the dedup key for one normalized observation."""

    sequence = observation.sequence
    if sequence is None:
        sequence = observation.emitter_seq if observation.emitter_seq is not None else -1
        channel = "fallback"
    else:
        channel = "http"
    return (observation.generation, channel, sequence)


def load_envelopes(path: Path) -> list[Envelope]:
    """Load one events.ndjson file in virtual-time order.

    Fallback envelopes carry ``sequence: null`` and are ordered by
    ``emitter_seq`` within the same receive stamp.
    """

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
                    sequence=_optional_int(row, "sequence"),
                    emitter_seq=_optional_int(row, "emitter_seq"),
                    received_at_utc=str(row.get("received_at_utc") or ""),
                    received_at_monotonic=float(monotonic)
                    if isinstance(monotonic, (int, float))
                    else 0.0,
                    channel_generation=int(row.get("channel_generation") or 0),
                    via=str(row.get("via") or "unknown"),
                    provider_event=provider,
                )
            )
    rows.sort(key=lambda item: (item.received_at_monotonic, item.effective_sequence()))
    return rows


def replay_envelopes(
    envelopes: list[Envelope],
    *,
    meta: RunMeta | None = None,
) -> tuple[list[TimelineRow], Posture]:
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
                emitter_seq=observation.emitter_seq,
                event_name=observation.event_name,
                received_at_utc=observation.received_at_utc,
                received_at_monotonic=observation.received_at_monotonic,
                generation=observation.generation,
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
    if meta is None:
        final = reducer.finish()
    else:
        final = reducer.finish(
            headless=meta.headless,
            process_returncode=meta.process_returncode,
            finished_at_utc=meta.finished_at_utc,
        )
    return rows, final


def _parse_ts(value: str) -> datetime:
    """Parse one ISO-8601 timestamp for label-window comparisons."""

    return datetime.fromisoformat(value)


def _silence_seconds(start_utc: str | None, end_utc: str | None) -> float | None:
    """Return seconds between two UTC stamps, or ``None`` when unusable."""

    if start_utc is None or end_utc is None:
        return None
    try:
        return (_parse_ts(end_utc) - _parse_ts(start_utc)).total_seconds()
    except (TypeError, ValueError):
        return None


def _load_json(path: Path) -> dict[str, Any] | None:
    """Load one JSON object, returning None when absent or invalid."""

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def load_run_meta(run_root: Path) -> RunMeta:
    """Read the launch/summary metadata used by the terminal fallbacks."""

    launch = _load_json(run_root / "launch.json") or {}
    summary = _load_json(run_root / "run-summary.json") or {}
    launch_block = launch.get("launch")
    headless = False
    if isinstance(launch_block, dict):
        headless = launch_block.get("headless") is True
    time_block = launch.get("time")
    finished = None
    if isinstance(time_block, dict):
        finished = time_block.get("finished_at_utc")
    if not isinstance(finished, str):
        candidate = summary.get("finished_at_utc")
        finished = candidate if isinstance(candidate, str) else None
    returncode: int | None = None
    extra = summary.get("extra")
    if isinstance(extra, dict):
        for value in extra.values():
            if isinstance(value, dict) and isinstance(value.get("returncode"), int):
                if not isinstance(value.get("returncode"), bool):
                    returncode = value["returncode"]
    scenario = launch.get("scenario")
    return RunMeta(
        scenario=scenario if isinstance(scenario, str) else run_root.parent.name,
        headless=headless,
        process_returncode=returncode,
        finished_at_utc=finished,
    )


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
    window_events: list[str],
    window_maintenance: bool,
    end_row: TimelineRow | None,
    final: Posture,
) -> str:
    """Compare one label's expected posture against the replay window."""

    if expected == "not_reached":
        return "n/a (not reached)"
    if expected == "idle_ready":
        if end_row is None:
            return "n/a (pre-channel)"
        return "OK" if end_row.turn_phase in ("ready", "unknown") else "MISMATCH"
    if expected == "session_created":
        if "SessionStart" not in window_events:
            return "MISMATCH"
        return "OK" if end_row is None or end_row.turn_phase != "unknown" else "MISMATCH"
    if expected == "active_then_settled":
        if "active" not in window_phases:
            return "MISMATCH"
        settled = (
            end_row is not None
            and end_row.last_turn_result in ("success", "interrupted", "known_failure")
        ) or final.last_turn_result in ("success", "interrupted", "known_failure")
        return "OK" if settled else "MISMATCH"
    if expected == "active":
        if "active" in window_phases:
            return "OK"
        return "OK" if end_row is not None and end_row.turn_phase == "active" else "MISMATCH"
    if expected == "terminal_gap":
        if (
            final.terminal_gaps >= 1
            and final.turn_phase == "unknown"
            and any(item.startswith("terminal_gap") for item in final.diagnostics)
        ):
            return "OK"
        return "MISMATCH"
    if expected == "blocked_then_completed":
        if "blocked" not in window_phases:
            return "MISMATCH"
        settled = (end_row is not None and end_row.last_turn_result == "success") or (
            final.last_turn_result == "success"
        )
        return "OK" if settled and final.allow_settles >= 1 else "MISMATCH"
    if expected == "blocked_then_rejected":
        if "blocked" not in window_phases:
            return "MISMATCH"
        return (
            "OK"
            if final.deny_settles >= 1 and final.last_turn_result == "success"
            else ("MISMATCH")
        )
    if expected == "maintenance":
        return "OK" if window_maintenance else "MISMATCH"
    if expected == "interrupted":
        if end_row is not None and end_row.last_turn_result == "interrupted":
            return "OK"
        return "OK" if final.last_turn_result == "interrupted" else "MISMATCH"
    if expected == "steered_into_active_turn":
        drained = final.queued_prompts >= 1 and final.epochs == 1
        settled = (end_row is not None and end_row.last_turn_result == "success") or (
            final.last_turn_result == "success"
        )
        return "OK" if drained and settled else "MISMATCH"
    if expected == "exiting":
        if end_row is not None and (
            end_row.presence in ("lost", "unknown") or end_row.turn_phase == "ready"
        ):
            return "OK"
        return "MISMATCH"
    if expected == "resumed_then_active":
        if not final.resume_started:
            return "MISMATCH"
        return "OK" if "active" in window_phases or final.epochs >= 2 else "MISMATCH"
    if expected == "subagent_running":
        return (
            "OK"
            if final.subagent_starts >= 1
            and ("SubagentStart" in window_events or "TurnStarted" in window_events)
            else "MISMATCH"
        )
    if expected == "subagent_done":
        return (
            "OK" if final.subagent_stops >= 1 and "SubagentStop" in window_events else ("MISMATCH")
        )
    if expected in ("headless", "process_exit"):
        return "n/a (headless, no pane)"
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
    recording_cache: dict[str, dict[str, dict[str, Any]]] = {}

    def samples_for(recording: str) -> dict[str, dict[str, Any]]:
        if recording not in recording_cache:
            recording_cache[recording] = _pane_samples(run_root, recording)
        return recording_cache[recording]

    checks: list[LabelCheck] = []
    timed_rows = [(_parse_ts(row.received_at_utc), row) for row in rows if row.received_at_utc]
    for label in labels:
        if not isinstance(label, dict):
            continue
        label_id = str(label.get("label_id") or "?")
        expected = str(label.get("expectations", {}).get("turn_phase") or "unknown")
        sample_id = label.get("sample_id")
        evidence = label.get("evidence")
        recording = "pane-recording"
        if isinstance(evidence, dict) and isinstance(evidence.get("recording"), str):
            recording = evidence["recording"]
        elif label_id.startswith("s7-resume"):
            recording = "pane-recording-resume"
        samples = samples_for(recording)
        if not isinstance(sample_id, str) or sample_id not in samples:
            checks.append(
                LabelCheck(
                    label_id=label_id,
                    expected=expected,
                    start_phase="no-sample",
                    end_phase="no-sample",
                    end_last_turn="none",
                    verdict="n/a (no pane sample)",
                )
            )
            continue
        sample = samples[sample_id]
        end_id = label.get("sample_end_id")
        end_sample = samples.get(end_id) if isinstance(end_id, str) else None
        if end_sample is None:
            end_sample = sample
        try:
            start_ts = _parse_ts(str(sample.get("ts_utc")))
            end_ts = _parse_ts(str(end_sample.get("ts_utc")))
        except (TypeError, ValueError):
            continue
        lookbehind = [
            row
            for ts, row in timed_rows
            if start_ts - timedelta(seconds=LABEL_LOOKBEHIND_SECONDS) <= ts < start_ts
        ]
        window = [row for ts, row in timed_rows if start_ts <= ts <= end_ts]
        before = [row for ts, row in timed_rows if ts < start_ts]
        base_generation: int | None = None
        if window:
            base_generation = window[-1].generation
        elif lookbehind:
            base_generation = lookbehind[-1].generation
        elif before:
            base_generation = before[-1].generation
        lookahead: list[TimelineRow] = []
        for ts, row in timed_rows:
            if end_ts < ts <= end_ts + timedelta(seconds=LABEL_LOOKAROUND_SECONDS):
                if row.event_name == "UserPromptSubmit":
                    break
                if row.event_name == "SessionStart":
                    if base_generation is None:
                        lookahead.append(row)
                    break
                lookahead.append(row)
        combined = lookbehind + window + lookahead
        end_row = combined[-1] if combined else (before[-1] if before else None)
        window_phases = [row.turn_phase for row in combined]
        if before and lookbehind:
            window_phases = [lookbehind[0].turn_phase] + window_phases
        window_events = [row.event_name for row in combined]
        verdict = _label_verdict(
            expected,
            window_phases,
            window_events,
            any(row.maintenance_active for row in combined),
            end_row,
            final,
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


def _spec(name: str, relative: str, *args: Any, **kwargs: Any) -> RunSpec:
    """Build one run spec with a path relative to the capture base."""

    return RunSpec(name, RUN_ROOT_BASE / relative, *args, **kwargs)


RUN_SPECS: tuple[RunSpec, ...] = (
    _spec(
        "s0-earlier-1",
        "s0/run-20261020T131852Z",
        (),
        "unknown",
        "unknown",
        "none",
        0,
        expected_session_ids=0,
        expected_generations=0,
        expected_diagnostic="empty_stream",
    ),
    _spec(
        "s0-earlier-2",
        "s0/run-20261020T132224Z",
        (),
        "unknown",
        "unknown",
        "none",
        0,
        expected_session_ids=0,
        expected_generations=0,
        expected_diagnostic="empty_stream",
    ),
    _spec(
        "s0-gate-refuted",
        "s0/run-20261020T132548Z",
        (),
        "unknown",
        "unknown",
        "none",
        0,
        expected_session_ids=0,
        expected_generations=0,
        expected_diagnostic="empty_stream",
    ),
    _spec(
        "s0-gate",
        "s0/run-20261020T133111Z",
        ("SessionStart", "UserPromptSubmit", "TurnStarted", "Stop", "SessionEnd"),
        "lost",
        "ready",
        "success",
        1,
        expected_turn_ids=(0,),
    ),
    _spec(
        "s1",
        "s1/run-20261020T133343Z",
        (
            "SessionStart",
            "UserPromptSubmit",
            "TurnStarted",
            "Stop",
            "UserPromptSubmit",
            "TurnStarted",
            "PreToolUse",
            "PostToolUse",
            "Stop",
            "SessionHeartbeat",
            "UserPromptSubmit",
            "TurnStarted",
            "Stop",
            "SessionEnd",
        ),
        "lost",
        "ready",
        "success",
        3,
        expected_turn_ids=(0, 1, 2),
        expected_heartbeats=1,
    ),
    _spec(
        "s2-control",
        "s2/run-20261020T133534Z",
        (),
        "unknown",
        "unknown",
        "none",
        0,
        expected_session_ids=0,
        expected_generations=0,
        expected_diagnostic="empty_stream",
    ),
    _spec(
        "s3",
        "s3/run-20261020T133622Z",
        (
            "SessionStart",
            "UserPromptSubmit",
            "TurnStarted",
            "PreToolUse",
            "PermissionRequest",
            "PostToolUse",
            "PermissionResult",
            "Stop",
            "UserPromptSubmit",
            "TurnStarted",
            "PreToolUse",
            "PermissionRequest",
            "PermissionResult",
            "PostToolUseFailure",
            "Stop",
            "SessionEnd",
        ),
        "lost",
        "ready",
        "success",
        2,
        expected_turn_ids=(0, 1),
        expected_allow=1,
        expected_deny=1,
    ),
    _spec(
        "s4",
        "s4/run-20261020T133716Z",
        (
            "SessionStart",
            "UserPromptSubmit",
            "TurnStarted",
            "PreToolUse",
            "PostToolUse",
            "Stop",
            "PreCompact",
            "PostCompact",
            "UserPromptSubmit",
            "TurnStarted",
            "Stop",
            "SessionEnd",
        ),
        "lost",
        "ready",
        "success",
        2,
        expected_turn_ids=(0, 1),
        expected_compactions=1,
        expected_diagnostic="post_compaction_fresh_turn_id",
    ),
    _spec(
        "s5",
        "s5/run-20261020T133804Z",
        ("SessionStart", "UserPromptSubmit", "TurnStarted", "Interrupt", "SessionEnd"),
        "lost",
        "ready",
        "interrupted",
        1,
        expected_turn_ids=(0,),
        expected_interrupts=1,
    ),
    _spec(
        "s6-deviation",
        "s6/run-20261020T133838Z",
        (
            "SessionStart",
            "UserPromptSubmit",
            "TurnStarted",
            "SessionHeartbeat",
            "Stop",
            "UserPromptSubmit",
            "TurnStarted",
            "Stop",
            "SessionEnd",
        ),
        "lost",
        "ready",
        "success",
        2,
        expected_turn_ids=(0, 1),
        expected_heartbeats=1,
    ),
    _spec(
        "s6",
        "s6/run-20261020T134110Z",
        (
            "SessionStart",
            "UserPromptSubmit",
            "TurnStarted",
            "UserPromptQueued",
            "SessionHeartbeat",
            "Stop",
            "SessionHeartbeat",
            "SessionHeartbeat",
            "SessionHeartbeat",
            "SessionHeartbeat",
            "SessionEnd",
        ),
        "lost",
        "ready",
        "success",
        1,
        expected_turn_ids=(0,),
        expected_queued=1,
        expected_heartbeats=5,
        expected_diagnostic="steer_into_active_turn",
    ),
    _spec(
        "s7",
        "s7/run-20261020T134720Z",
        (
            "SessionStart",
            "UserPromptSubmit",
            "TurnStarted",
            "Stop",
            "SessionEnd",
            "SessionStart",
            "UserPromptSubmit",
            "TurnStarted",
            "Stop",
            "SessionEnd",
        ),
        "lost",
        "ready",
        "success",
        2,
        expected_turn_ids=(0, 1),
        expected_generations=2,
        expected_resumes=1,
    ),
    _spec(
        "s8",
        "s8/run-20261020T134807Z",
        ("SessionStart", "UserPromptSubmit", "TurnStarted", "Stop"),
        "lost",
        "ready",
        "success",
        1,
        expected_turn_ids=(0,),
        expected_diagnostic="headless_session_end_gap",
    ),
    _spec(
        "s9",
        "s9/run-20261020T135227Z",
        (
            "SessionStart",
            "UserPromptSubmit",
            "TurnStarted",
            "PreToolUse",
            "TurnStarted",
            "SubagentStart",
            "Stop",
            "SubagentStop",
            "PostToolUse",
            "Stop",
            "SessionEnd",
        ),
        "lost",
        "ready",
        "success",
        1,
        expected_turn_ids=(0,),
        expected_subagents=(1, 1),
        expected_diagnostic="subagent_turn_started",
    ),
    _spec(
        "f1-prior",
        "f1/run-20261020T134906Z",
        ("SessionStart", "UserPromptSubmit", "TurnStarted"),
        "lost",
        "unknown",
        "none",
        1,
        expected_turn_ids=(0,),
        expected_terminal_gaps=1,
        expected_diagnostic="terminal_gap",
    ),
    _spec(
        "f1",
        "f1/run-20261020T134947Z",
        ("SessionStart", "UserPromptSubmit", "TurnStarted"),
        "lost",
        "unknown",
        "none",
        1,
        expected_turn_ids=(0,),
        expected_terminal_gaps=1,
        expected_diagnostic="terminal_gap",
    ),
    _spec(
        "d1",
        "d1/run-20261020T135119Z",
        (
            "SessionStart",
            "UserPromptSubmit",
            "TurnStarted",
            "Stop",
            "SessionEnd",
        ),
        "lost",
        "ready",
        "success",
        1,
        expected_turn_ids=(0,),
        expected_fallback=4,
        expected_diagnostic="fallback_delivery",
    ),
    _spec(
        "t1",
        "t1/run-20261020T135150Z",
        ("SessionStart", "UserPromptSubmit", "TurnStarted", "Stop", "SessionEnd"),
        "lost",
        "ready",
        "success",
        1,
        expected_turn_ids=(0,),
    ),
)


def _discover_campaign_roots() -> tuple[list[Path], list[Path]]:
    """Split run roots into campaign captures and harness G0 artifacts."""

    campaign: list[Path] = []
    skipped: list[Path] = []
    if not RUN_ROOT_BASE.is_dir():
        return campaign, skipped
    for root in sorted(RUN_ROOT_BASE.glob("*/run-*")):
        if not root.is_dir():
            continue
        events = load_envelopes(root / "collector" / "events.ndjson")
        has_kimi = any(normalize(envelope).event_name in KIMI_EVENTS for envelope in events)
        has_labels = (root / "labels" / "labels-template.json").is_file()
        if has_kimi or has_labels:
            campaign.append(root)
        else:
            skipped.append(root)
    return campaign, skipped


def _spec_for(root: Path) -> RunSpec:
    """Return the declared spec for a known root, else a permissive spec."""

    resolved = root.resolve()
    for spec in RUN_SPECS:
        if spec.root.resolve() == resolved:
            return spec
    return RunSpec(
        name=f"{root.parent.name}/{root.name}",
        root=root,
        expected_events=(),
        expected_presence="",
        expected_phase="",
        expected_last_turn="",
        expected_epochs=-1,
        expected_turn_ids=None,
        expected_session_ids=-1,
    )


def _validate(
    spec: RunSpec,
    result_rows: list[TimelineRow],
    final: Posture,
    session_ids: list[str],
    generations: list[int],
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
    if spec.expected_turn_ids is not None and final.epoch_turn_ids != spec.expected_turn_ids:
        issues.append(f"turn ids expected {spec.expected_turn_ids}, got {final.epoch_turn_ids}")
    if final.steers != spec.expected_steers:
        issues.append(f"steers expected {spec.expected_steers}, got {final.steers}")
    if final.queued_prompts != spec.expected_queued:
        issues.append(f"queued expected {spec.expected_queued}, got {final.queued_prompts}")
    if final.compaction_boundaries != spec.expected_compactions:
        issues.append(
            f"compactions expected {spec.expected_compactions}, got {final.compaction_boundaries}"
        )
    if final.allow_settles != spec.expected_allow:
        issues.append(f"allow settles expected {spec.expected_allow}, got {final.allow_settles}")
    if final.deny_settles != spec.expected_deny:
        issues.append(f"deny settles expected {spec.expected_deny}, got {final.deny_settles}")
    if final.interrupts != spec.expected_interrupts:
        issues.append(f"interrupts expected {spec.expected_interrupts}, got {final.interrupts}")
    subagents = (final.subagent_starts, final.subagent_stops)
    if subagents != spec.expected_subagents:
        issues.append(f"subagents expected {spec.expected_subagents}, got {subagents}")
    if final.heartbeats != spec.expected_heartbeats:
        issues.append(f"heartbeats expected {spec.expected_heartbeats}, got {final.heartbeats}")
    if final.terminal_gaps != spec.expected_terminal_gaps:
        issues.append(
            f"terminal gaps expected {spec.expected_terminal_gaps}, got {final.terminal_gaps}"
        )
    if final.fallback_events != spec.expected_fallback:
        issues.append(
            f"fallback events expected {spec.expected_fallback}, got {final.fallback_events}"
        )
    if len(generations) != spec.expected_generations:
        issues.append(f"generations expected {spec.expected_generations}, got {generations}")
    if spec.expected_resumes != int(final.resume_started):
        issues.append(f"resumes expected {spec.expected_resumes}, got {final.resume_started}")
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
    meta = load_run_meta(spec.root)
    rows, final = replay_envelopes(envelopes, meta=meta)
    session_ids = sorted(
        {obs.session_id for obs in (normalize(env) for env in envelopes) if obs.session_id}
    )
    generations = sorted({envelope.channel_generation for envelope in envelopes})
    collector_status = _load_json(spec.root / "collector" / "collector.json")
    validation = _validate(spec, rows, final, session_ids, generations)
    label_checks = check_labels(spec.root, rows, final)
    return RunResult(
        spec=spec,
        rows=tuple(rows),
        final=final,
        event_names=tuple(row.event_name for row in rows),
        session_ids=tuple(session_ids),
        generations=tuple(generations),
        meta=meta,
        collector_status=collector_status,
        validation=tuple(validation),
        label_checks=tuple(label_checks),
    )


def _print_timeline(result: RunResult) -> None:
    """Print one row per replayed event."""

    print("  seq   event                 turn  presence  phase    blocked maint last_turn")
    for row in result.rows:
        seq = str(row.sequence) if row.sequence is not None else f"f{row.emitter_seq}"
        turn = "-" if row.turn_id is None else str(row.turn_id)
        print(
            f"  {seq:<5} {row.event_name:<21} {turn:<5} {row.presence:<9} "
            f"{row.turn_phase:<8} {str(row.blocked):<7} {str(row.maintenance_active):<5} "
            f"{row.last_turn_result}"
        )


def _print_result(result: RunResult, *, timeline: bool) -> None:
    """Print one run summary, validation, and label agreement."""

    final = result.final
    print(f"=== {result.spec.name}  {result.spec.root}")
    print(
        f"  events={len(result.rows)} generations={len(result.generations)} "
        f"epochs={final.epochs} turns={final.epoch_turn_ids} "
        f"queued={final.queued_prompts} steers={final.steers} "
        f"compactions={final.compaction_boundaries} allow={final.allow_settles} "
        f"deny={final.deny_settles} interrupts={final.interrupts} "
        f"permissions={final.permission_requests}/{final.blocked_windows} "
        f"tools={final.pre_tool_uses}/{final.post_tool_uses}/{final.tool_failures} "
        f"pairs={final.tool_pairs} subagents={final.subagent_starts}/{final.subagent_stops} "
        f"gaps={final.terminal_gaps} fallback={final.fallback_events}"
    )
    print(
        f"  final: presence={final.presence} phase={final.turn_phase} "
        f"last_turn={final.last_turn_result} work={final.work} "
        f"session_id={final.session_id or '-'} generation={final.generation}"
    )
    print(
        f"  liveness: heartbeats={final.heartbeats} "
        f"last_heartbeat={final.last_heartbeat_at_utc or '-'} "
        f"silence={_fmt_seconds(final.gap_silence_seconds)}"
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
    if not result.spec.expected_events and result.spec.expected_epochs >= 0:
        print("  expectation: OK (empty control stream)")
    elif result.validation:
        print("  EXPECTATION MISMATCH:")
        for issue in result.validation:
            print(f"    - {issue}")
    else:
        print("  expectation: OK")
    if result.label_checks:
        print("  labels:")
        for check in result.label_checks:
            print(
                f"    {check.label_id:<26} expected={check.expected:<26} "
                f"start={check.start_phase:<10} end={check.end_phase:<10} "
                f"last_turn={check.end_last_turn:<12} {check.verdict}"
            )


def _fmt_seconds(value: float | None) -> str:
    """Format one optional duration for the summary line."""

    if value is None:
        return "-"
    return f"{value:.3f}s"


def _synthetic_envelope(
    sequence: int,
    event_name: str,
    *,
    generation: int = 1,
    via: str = "http",
    received_at_monotonic: float | None = None,
    **fields: Any,
) -> Envelope:
    """Build one synthetic envelope for the self-test."""

    payload = {"hook_event_name": event_name, **fields}
    monotonic = float(sequence) if received_at_monotonic is None else received_at_monotonic
    return Envelope(
        sequence=sequence,
        emitter_seq=None,
        received_at_utc=f"2026-01-01T00:00:{sequence:02d}.000+00:00",
        received_at_monotonic=monotonic,
        channel_generation=generation,
        via=via,
        provider_event=payload,
    )


def _fallback_envelope(emitter_seq: int, event_name: str, **fields: Any) -> Envelope:
    """Build one synthetic file-fallback envelope for the self-test."""

    payload = {"hook_event_name": event_name, **fields}
    return Envelope(
        sequence=None,
        emitter_seq=emitter_seq,
        received_at_utc=f"2026-01-01T00:00:{emitter_seq:02d}.000+00:00",
        received_at_monotonic=float(emitter_seq),
        channel_generation=1,
        via="command_fallback",
        provider_event=payload,
    )


def _check(name: str, ok: bool, note: str, checks: list[tuple[str, bool, str]]) -> None:
    """Append one named self-test check."""

    checks.append((name, ok, note))


def self_test() -> int:
    """Run synthetic streams covering the required reducer cases."""

    checks: list[tuple[str, bool, str]] = []

    normal = [
        _synthetic_envelope(1, "SessionStart", source="startup", session_id="s1"),
        _synthetic_envelope(2, "UserPromptSubmit", prompt=[{"type": "text", "text": "OK"}]),
        _synthetic_envelope(3, "TurnStarted", turn_id=0, origin_kind="user"),
        _synthetic_envelope(
            4, "PreToolUse", tool_name="Bash", tool_call_id="tc1", tool_input={"command": "echo"}
        ),
        _synthetic_envelope(
            5, "PostToolUse", tool_name="Bash", tool_call_id="tc1", tool_input={"command": "echo"}
        ),
        _synthetic_envelope(6, "Stop", stop_hook_active=False),
        _synthetic_envelope(7, "SessionEnd", reason="exit"),
    ]
    rows, final = replay_envelopes(normal)
    _check(
        "normal-turn",
        final.presence == "lost"
        and final.turn_phase == "ready"
        and final.last_turn_result == "success"
        and final.epochs == 1
        and final.epoch_turn_ids == (0,)
        and final.tool_pairs == 1
        and final.tool_failures == 0,
        f"presence={final.presence} phase={final.turn_phase} result={final.last_turn_result} "
        f"pairs={final.tool_pairs}",
        checks,
    )

    blocked_allow = [
        _synthetic_envelope(1, "SessionStart", source="startup", session_id="s1"),
        _synthetic_envelope(2, "UserPromptSubmit"),
        _synthetic_envelope(3, "TurnStarted", turn_id=0, origin_kind="user"),
        _synthetic_envelope(4, "PreToolUse", tool_name="Write", tool_call_id="tc1"),
        _synthetic_envelope(
            5, "PermissionRequest", turn_id=0, tool_name="Write", tool_call_id="tc1"
        ),
        _synthetic_envelope(6, "PostToolUse", tool_name="Write", tool_call_id="tc1"),
        _synthetic_envelope(
            7,
            "PermissionResult",
            turn_id=0,
            tool_name="Write",
            tool_call_id="tc1",
            decision="approved",
        ),
        _synthetic_envelope(8, "Stop", stop_hook_active=False),
    ]
    rows, final = replay_envelopes(blocked_allow)
    held_after_post = rows[5].turn_phase == "blocked"
    _check(
        "blocked-allow",
        any(row.blocked for row in rows)
        and held_after_post
        and final.allow_settles == 1
        and final.last_turn_result == "success",
        f"blocked_seen={any(row.blocked for row in rows)} held_after_post={held_after_post} "
        f"allow={final.allow_settles}",
        checks,
    )

    blocked_deny = [
        _synthetic_envelope(1, "SessionStart", source="startup", session_id="s1"),
        _synthetic_envelope(2, "UserPromptSubmit"),
        _synthetic_envelope(3, "TurnStarted", turn_id=0, origin_kind="user"),
        _synthetic_envelope(4, "PreToolUse", tool_name="Write", tool_call_id="tc1"),
        _synthetic_envelope(
            5, "PermissionRequest", turn_id=0, tool_name="Write", tool_call_id="tc1"
        ),
        _synthetic_envelope(
            6,
            "PermissionResult",
            turn_id=0,
            tool_name="Write",
            tool_call_id="tc1",
            decision="rejected",
        ),
        _synthetic_envelope(7, "PostToolUseFailure", tool_name="Write", tool_call_id="tc1"),
        _synthetic_envelope(8, "Stop", stop_hook_active=False),
    ]
    rows, final = replay_envelopes(blocked_deny)
    _check(
        "blocked-deny",
        final.deny_settles == 1
        and final.last_turn_result == "success"
        and final.interrupts == 0
        and any(row.blocked for row in rows)
        and rows[-1].last_turn_result == "success",
        f"deny={final.deny_settles} result={final.last_turn_result} interrupts={final.interrupts}",
        checks,
    )

    compaction = [
        _synthetic_envelope(1, "SessionStart", source="startup", session_id="s1"),
        _synthetic_envelope(2, "UserPromptSubmit"),
        _synthetic_envelope(3, "TurnStarted", turn_id=0, origin_kind="user"),
        _synthetic_envelope(4, "Stop", stop_hook_active=False),
        _synthetic_envelope(5, "PreCompact", trigger="manual", token_count=100),
        _synthetic_envelope(6, "PostCompact", trigger="manual", estimated_token_count=90),
        _synthetic_envelope(7, "UserPromptSubmit"),
        _synthetic_envelope(8, "TurnStarted", turn_id=1, origin_kind="user"),
        _synthetic_envelope(9, "Stop", stop_hook_active=False),
        _synthetic_envelope(10, "SessionEnd", reason="exit"),
    ]
    rows, final = replay_envelopes(compaction)
    _check(
        "compaction-window",
        final.compaction_boundaries == 1
        and final.epochs == 2
        and final.epoch_turn_ids == (0, 1)
        and final.last_turn_result == "success"
        and any(row.maintenance_active for row in rows)
        and any(item.startswith("post_compaction_fresh_turn_id") for item in final.diagnostics),
        f"compactions={final.compaction_boundaries} epochs={final.epochs} "
        f"turns={final.epoch_turn_ids}",
        checks,
    )

    interrupt = [
        _synthetic_envelope(1, "SessionStart", source="startup", session_id="s1"),
        _synthetic_envelope(2, "UserPromptSubmit"),
        _synthetic_envelope(3, "TurnStarted", turn_id=0, origin_kind="user"),
        _synthetic_envelope(4, "Interrupt", turn_id=0, reason="cancelled"),
        _synthetic_envelope(5, "SessionEnd", reason="exit"),
    ]
    rows, final = replay_envelopes(interrupt)
    _check(
        "interrupt",
        final.last_turn_result == "interrupted"
        and final.interrupts == 1
        and not any(row.event_name == "Stop" for row in rows),
        f"result={final.last_turn_result} interrupts={final.interrupts}",
        checks,
    )

    terminal_gap = [
        _synthetic_envelope(1, "SessionStart", source="startup", session_id="s1"),
        _synthetic_envelope(2, "UserPromptSubmit"),
        _synthetic_envelope(3, "TurnStarted", turn_id=0, origin_kind="user"),
    ]
    _, final = replay_envelopes(
        terminal_gap,
        meta=RunMeta(
            scenario="f1",
            headless=False,
            process_returncode=None,
            finished_at_utc="2026-01-01T00:01:13.000+00:00",
        ),
    )
    _check(
        "terminal-gap",
        final.presence == "lost"
        and final.turn_phase == "unknown"
        and final.last_turn_result == "none"
        and final.terminal_gaps == 1
        and any(item.startswith("terminal_gap") for item in final.diagnostics)
        and any(item.startswith("heartbeat_liveness_unavailable") for item in final.diagnostics)
        and final.gap_silence_seconds is not None
        and final.gap_silence_seconds > 60.0,
        f"presence={final.presence} phase={final.turn_phase} gaps={final.terminal_gaps} "
        f"silence={_fmt_seconds(final.gap_silence_seconds)}",
        checks,
    )

    resume = [
        _synthetic_envelope(1, "SessionStart", source="startup", session_id="s1"),
        _synthetic_envelope(2, "UserPromptSubmit"),
        _synthetic_envelope(3, "TurnStarted", turn_id=0, origin_kind="user"),
        _synthetic_envelope(4, "Stop", stop_hook_active=False),
        _synthetic_envelope(5, "SessionEnd", reason="exit"),
        _synthetic_envelope(6, "SessionStart", generation=2, source="resume", session_id="s1"),
        _synthetic_envelope(7, "UserPromptSubmit", generation=2),
        _synthetic_envelope(8, "TurnStarted", generation=2, turn_id=1, origin_kind="user"),
        _synthetic_envelope(9, "Stop", generation=2, stop_hook_active=False),
        _synthetic_envelope(10, "SessionEnd", generation=2, reason="exit"),
    ]
    _, final = replay_envelopes(resume)
    _check(
        "resume-generation",
        final.resume_started
        and final.generation == 2
        and final.epochs == 2
        and final.epoch_turn_ids == (0, 1)
        and final.session_id == "s1"
        and final.presence == "lost"
        and final.last_turn_result == "success",
        f"generation={final.generation} epochs={final.epochs} turns={final.epoch_turn_ids}",
        checks,
    )

    headless = [
        _synthetic_envelope(1, "SessionStart", source="startup", session_id="s1"),
        _synthetic_envelope(2, "UserPromptSubmit"),
        _synthetic_envelope(3, "TurnStarted", turn_id=0, origin_kind="user"),
        _synthetic_envelope(4, "Stop", stop_hook_active=False),
    ]
    _, final = replay_envelopes(
        headless,
        meta=RunMeta(
            scenario="s8",
            headless=True,
            process_returncode=0,
            finished_at_utc="2026-01-01T00:00:34.000+00:00",
        ),
    )
    _check(
        "headless-no-session-end",
        final.presence == "lost"
        and final.turn_phase == "ready"
        and final.last_turn_result == "success"
        and any(item.startswith("headless_session_end_gap") for item in final.diagnostics)
        and any(item.startswith("headless_terminal_settled") for item in final.diagnostics),
        f"presence={final.presence} phase={final.turn_phase} result={final.last_turn_result}",
        checks,
    )

    queue = [
        _synthetic_envelope(1, "SessionStart", source="startup", session_id="s1"),
        _synthetic_envelope(2, "UserPromptSubmit"),
        _synthetic_envelope(3, "TurnStarted", turn_id=0, origin_kind="user"),
        _synthetic_envelope(4, "UserPromptQueued", prompt_id="msg_1", queue_length=1),
        _synthetic_envelope(5, "Stop", stop_hook_active=False),
        _synthetic_envelope(6, "SessionEnd", reason="exit"),
    ]
    _, final = replay_envelopes(queue)
    _check(
        "queue-steer-into-turn",
        final.queued_prompts == 1
        and final.epochs == 1
        and final.last_turn_result == "success"
        and any(item.startswith("steer_into_active_turn") for item in final.diagnostics),
        f"queued={final.queued_prompts} epochs={final.epochs}",
        checks,
    )

    subagent = [
        _synthetic_envelope(1, "SessionStart", source="startup", session_id="s1"),
        _synthetic_envelope(2, "UserPromptSubmit"),
        _synthetic_envelope(3, "TurnStarted", turn_id=0, origin_kind="user"),
        _synthetic_envelope(4, "PreToolUse", tool_name="Agent", tool_call_id="tc1"),
        _synthetic_envelope(
            5, "TurnStarted", turn_id=0, origin_kind="system_trigger", origin_name="subagent"
        ),
        _synthetic_envelope(6, "SubagentStart", agent_name="explore"),
        _synthetic_envelope(7, "Stop", stop_hook_active=False),
        _synthetic_envelope(8, "SubagentStop", agent_name="explore"),
        _synthetic_envelope(9, "PostToolUse", tool_name="Agent", tool_call_id="tc1"),
        _synthetic_envelope(10, "Stop", stop_hook_active=False),
        _synthetic_envelope(11, "SessionEnd", reason="exit"),
    ]
    rows, final = replay_envelopes(subagent)
    _check(
        "subagent-scope",
        final.epochs == 1
        and final.epoch_turn_ids == (0,)
        and final.subagent_starts == 1
        and final.subagent_stops == 1
        and final.last_turn_result == "success"
        and rows[6].last_turn_result == "none",
        f"epochs={final.epochs} starts={final.subagent_starts} stops={final.subagent_stops} "
        f"nested_stop_last_turn={rows[6].last_turn_result}",
        checks,
    )

    fallback = [
        _fallback_envelope(3, "Stop", stop_hook_active=False),
        _fallback_envelope(1, "SessionStart", source="startup", session_id="s1"),
        _fallback_envelope(2, "UserPromptSubmit"),
        _synthetic_envelope(4, "SessionEnd", reason="exit", received_at_monotonic=4.0),
    ]
    fallback.sort(key=lambda item: (item.received_at_monotonic, item.effective_sequence()))
    _, final = replay_envelopes(fallback)
    _check(
        "fallback-ordering",
        final.fallback_events == 3
        and final.last_turn_result == "success"
        and sum(item.startswith("fallback_delivery") for item in final.diagnostics) == 3,
        f"fallback={final.fallback_events} result={final.last_turn_result}",
        checks,
    )

    loader_lines = [
        json.dumps(
            {
                "sequence": None,
                "emitter_seq": 4,
                "received_at_utc": "2026-01-01T00:00:04.000+00:00",
                "received_at_monotonic": 4.0,
                "channel_generation": 1,
                "via": "command_fallback",
                "provider_event": {"hook_event_name": "Stop", "stop_hook_active": False},
            }
        ),
        json.dumps(
            {
                "sequence": None,
                "emitter_seq": 2,
                "received_at_utc": "2026-01-01T00:00:02.000+00:00",
                "received_at_monotonic": 2.0,
                "channel_generation": 1,
                "via": "command_fallback",
                "provider_event": {"hook_event_name": "UserPromptSubmit"},
            }
        ),
        json.dumps(
            {
                "sequence": 1,
                "received_at_utc": "2026-01-01T00:00:01.000+00:00",
                "received_at_monotonic": 1.0,
                "channel_generation": 1,
                "via": "http",
                "provider_event": {"hook_event_name": "SessionStart", "source": "startup"},
            }
        ),
    ]
    with tempfile.TemporaryDirectory() as temp_dir:
        events_path = Path(temp_dir) / "events.ndjson"
        events_path.write_text("\n".join(loader_lines) + "\n", encoding="utf-8")
        loaded = load_envelopes(events_path)
    _check(
        "fallback-loader-order",
        [item.provider_event["hook_event_name"] for item in loaded]
        == ["SessionStart", "UserPromptSubmit", "Stop"]
        and loaded[1].sequence is None
        and loaded[1].emitter_seq == 2,
        f"order={[item.effective_sequence() for item in loaded]}",
        checks,
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
    parser.add_argument("--all", action="store_true", help="replay every capture run root")
    parser.add_argument("--timeline", action="store_true", help="print one row per event")
    parser.add_argument("--no-labels", action="store_true", help="skip label checks")
    parser.add_argument("--self-test", action="store_true", help="run synthetic reducer checks")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()

    specs: tuple[RunSpec, ...]
    skipped: list[Path] = []
    if args.run_root is not None:
        root = args.run_root.expanduser().resolve()
        if not root.is_dir():
            parser.error(f"run root does not exist: {root}")
        specs = (_spec_for(root),)
    else:
        roots, skipped = _discover_campaign_roots()
        if not roots:
            print(f"no campaign run roots found under {RUN_ROOT_BASE}")
            return 1
        specs = tuple(_spec_for(root) for root in roots)

    failed = 0
    label_ok = 0
    label_na = 0
    label_bad = 0
    total_events = 0
    for spec in specs:
        result = replay_run(spec)
        if args.no_labels:
            result = RunResult(
                spec=result.spec,
                rows=result.rows,
                final=result.final,
                event_names=result.event_names,
                session_ids=result.session_ids,
                generations=result.generations,
                meta=result.meta,
                collector_status=result.collector_status,
                validation=result.validation,
                label_checks=(),
            )
        _print_result(result, timeline=args.timeline or args.run_root is not None)
        total_events += len(result.rows)
        if result.validation:
            failed += 1
        for check in result.label_checks:
            if check.verdict == "MISMATCH":
                failed += 1
                label_bad += 1
            elif check.verdict == "OK":
                label_ok += 1
            else:
                label_na += 1
    if skipped:
        print(
            f"\nSKIPPED {len(skipped)} harness self-test root(s): "
            + ", ".join(str(path.relative_to(RUN_ROOT_BASE)) for path in skipped)
        )
    if len(specs) > 1:
        print(
            f"\nLABELS: ok={label_ok} n/a={label_na} mismatch={label_bad}; "
            f"roots={len(specs)} events={total_events}"
        )
        print(f"REPLAY RESULT: {'PASS' if failed == 0 else f'{failed} ISSUE(S)'}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
