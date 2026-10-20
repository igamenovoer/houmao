"""Data models for the provider-neutral hook observation channel.

The models in this module are the stable vocabulary shared by the session
store, the per-adapter event normalizers, and the posture reducer. They are
plain frozen dataclasses so they can be compared, logged by field, and
serialized without provider-specific imports.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal


HookAdapter = Literal["claude", "codex", "kimi"]
HookDeliveryVia = Literal["http", "command", "command_fallback", "unknown"]
HookRecordType = Literal["event", "generation_boundary"]
HookStoreStatus = Literal["running", "stopped"]
HookPresence = Literal["unknown", "present", "lost"]
EnvelopeParseOutcome = Literal[
    "ok",
    "blank",
    "garbage",
    "oversized",
    "invalid_shape",
    "incomplete",
]
NormalizedHookKind = Literal[
    "session_started",
    "prompt_submitted",
    "prompt_queued",
    "activity",
    "tool_started",
    "tool_completed",
    "tool_failed",
    "permission_requested",
    "permission_resolved",
    "turn_started",
    "turn_completed",
    "turn_interrupted",
    "turn_failed",
    "maintenance_started",
    "maintenance_ended",
    "session_heartbeat",
    "session_ended",
    "subagent_started",
    "subagent_stopped",
    "generation_started",
    "unknown",
]
HookTurnStateHint = Literal["none", "active", "blocked", "maintenance", "ended"]
HookTerminalHint = Literal["none", "success", "interrupted", "known_failure"]
HookTurnPhase = Literal["ready", "active", "blocked", "unknown"]
HookWorkState = Literal["pending", "clear", "unknown"]
HookTerminalResult = Literal["success", "interrupted", "known_failure", "none"]
HookPostureDiagnosticKind = Literal[
    "hook_unknown_event",
    "hook_malformed_event",
    "hook_orphan_terminal",
    "hook_orphan_generation",
    "hook_duplicate_event",
    "hook_stop_hook_active",
    "prompt_id_missing",
    "permission_without_armed_prompt",
    "hook_steer_same_turn",
    "hook_turn_epoch_superseded",
    "hook_prompt_during_blocked",
    "hook_prompt_during_maintenance",
    "hook_permission_pair_unresolved",
    "hook_blocked_tool_mismatch",
    "hook_deny_aborted_turn",
    "hook_compaction_boundary",
    "hook_terminal_gap",
    "hook_session_end_with_open_turn",
    "hook_unavailable_event_family",
    "hook_prompt_queued",
    "hook_nested_scope_opened",
    "hook_nested_scope_closed",
    "hook_turn_started_without_prompt",
    "hook_turn_started_without_turn_id",
    "hook_tool_without_turn",
    "hook_permission_turn_mismatch",
    "hook_permission_result_without_blocked",
    "hook_permission_result_unexercised_decision",
    "hook_headless_session_end_gap",
    "hook_heartbeat_liveness_unavailable",
]


@dataclass(frozen=True)
class HookEventEnvelope:
    """One line of the append-only hook event store.

    Parameters
    ----------
    received_at_utc:
        Collector-stamped UTC receive time in ISO-8601 form.
    channel_generation:
        Provider launch generation that produced the record.
    via:
        Delivery path used to reach the collector.
    provider_event:
        Raw provider payload. Empty for a generation boundary record.
    sequence:
        Collector-assigned receive order, or ``None`` for command fallback
        rows and generation boundary records.
    record_type:
        ``event`` for provider deliveries, ``generation_boundary`` for the
        store-control record that opens a generation.
    """

    received_at_utc: str
    channel_generation: int
    via: HookDeliveryVia
    provider_event: dict[str, Any]
    sequence: int | None = None
    record_type: HookRecordType = "event"

    @property
    def is_generation_boundary(self) -> bool:
        """Return whether this record opens a new channel generation."""

        return self.record_type == "generation_boundary"

    @property
    def event_name(self) -> str | None:
        """Return the provider event name when the record carries one."""

        name = self.provider_event.get("hook_event_name")
        return name if isinstance(name, str) and name else None

    def to_payload(self) -> dict[str, Any]:
        """Return the canonical JSON-serializable line payload."""

        payload: dict[str, Any] = {
            "sequence": self.sequence,
            "received_at_utc": self.received_at_utc,
            "channel_generation": self.channel_generation,
            "via": self.via,
            "provider_event": self.provider_event,
        }
        if self.record_type != "event":
            payload["record_type"] = self.record_type
        return payload


@dataclass(frozen=True)
class EnvelopeParseResult:
    """Outcome of parsing one raw store line."""

    envelope: HookEventEnvelope | None
    outcome: EnvelopeParseOutcome

    @property
    def ok(self) -> bool:
        """Return whether the line produced an envelope."""

        return self.outcome == "ok" and self.envelope is not None


@dataclass(frozen=True)
class StoreReadResult:
    """Snapshot of one append-only store read."""

    envelopes: tuple[HookEventEnvelope, ...]
    skipped_blank_lines: int = 0
    skipped_garbage_lines: int = 0
    skipped_oversized_lines: int = 0
    skipped_invalid_lines: int = 0
    skipped_incomplete_lines: int = 0

    @property
    def skipped_lines(self) -> int:
        """Return the total number of non-envelope lines."""

        return (
            self.skipped_blank_lines
            + self.skipped_garbage_lines
            + self.skipped_oversized_lines
            + self.skipped_invalid_lines
            + self.skipped_incomplete_lines
        )


@dataclass(frozen=True)
class HookBackgroundTask:
    """Inspection-safe summary of one provider background task."""

    task_id: str | None
    status: str | None
    task_type: str | None

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-serializable payload."""

        return asdict(self)


@dataclass(frozen=True)
class HookObservation:
    """One provider event normalized into the provider-neutral vocabulary.

    The observation never carries tool input, tool output, or assistant
    message text. Text-bearing provider fields are reduced to flags or bounded
    class names before they reach this model. ``prompt_text`` is the one
    deliberate exception: the Kimi adapter collapses a structured
    ``ContentPart[]`` prompt to its joined text at the provider contract's
    request, and ``prompt_part_count`` keeps the collapsed shape visible.

    ``turn_id`` is the provider's turn-epoch key when the provider exposes one
    (Codex and Kimi do; Claude correlates by ``prompt_id``). Kimi's integer
    turn identifiers are carried as their decimal string form. ``steer`` marks
    a second prompt submission that belongs to the running turn rather than
    minting a new epoch.
    """

    kind: NormalizedHookKind
    event_name: str
    channel_generation: int
    received_at_utc: str
    sequence: int | None = None
    session_id: str | None = None
    prompt_id: str | None = None
    turn_id: str | None = None
    steer: bool = False
    tool_name: str | None = None
    tool_use_id: str | None = None
    agent_id: str | None = None
    agent_name: str | None = None
    turn_state_hint: HookTurnStateHint = "none"
    terminal_hint: HookTerminalHint = "none"
    maintenance_trigger: str | None = None
    source: str | None = None
    reason: str | None = None
    origin_kind: str | None = None
    origin_name: str | None = None
    permission_decision: str | None = None
    prompt_text: str | None = None
    prompt_part_count: int | None = None
    queue_length: int | None = None
    background_tasks: tuple[HookBackgroundTask, ...] = ()
    background_work_pending: bool | None = None
    stop_hook_active: bool | None = None
    last_assistant_message_present: bool | None = None
    error_class: str | None = None
    is_interrupt: bool | None = None
    provider_initiated: bool = False
    malformed: bool = False
    malformed_reason: str | None = None

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-serializable payload."""

        return asdict(self)


@dataclass(frozen=True)
class HookArmedPrompt:
    """One prompt waiting for its terminal event in arrival order."""

    prompt_id: str | None
    provider_initiated: bool
    sequence: int | None
    armed_at_utc: str

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-serializable payload."""

        return asdict(self)


@dataclass(frozen=True)
class HookPostureDiagnostic:
    """One bounded, secret-free posture diagnostic."""

    kind: HookPostureDiagnosticKind
    event_name: str
    channel_generation: int
    received_at_utc: str
    detail: str | None = None

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-serializable payload."""

        return asdict(self)


@dataclass(frozen=True)
class HookPostureCounters:
    """Monotonic counters accumulated across channel generations."""

    events_seen: int = 0
    normalized_events: int = 0
    unknown_events: int = 0
    malformed_events: int = 0
    orphan_terminals: int = 0
    orphan_generations: int = 0
    duplicate_events: int = 0
    steer_events: int = 0
    turn_epochs: int = 0
    compaction_boundaries: int = 0
    allow_settles: int = 0
    deny_settles: int = 0
    terminal_gaps: int = 0
    permission_requests: int = 0
    blocked_windows: int = 0
    queued_prompts: int = 0
    interrupts: int = 0
    subagent_starts: int = 0
    subagent_stops: int = 0
    heartbeats: int = 0

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-serializable payload."""

        return asdict(self)


@dataclass(frozen=True)
class HookPosture:
    """Merged posture facts derived from one hook channel generation."""

    generation: int | None
    session_id: str | None
    session_started: bool
    session_start_source: str | None
    turn_phase: HookTurnPhase
    terminal_result: HookTerminalResult
    terminal_error_class: str | None
    terminal_prompt_id: str | None
    terminal_consumed_prompt_id: str | None
    terminal_stop_hook_active: bool | None
    terminal_message_present: bool | None
    blocked: bool
    blocked_tool_name: str | None
    maintenance_active: bool
    work: HookWorkState
    active_prompt_id: str | None
    active_prompt_provider_initiated: bool | None
    armed_prompt_count: int
    queued_prompt_count: int
    armed_prompts: tuple[HookArmedPrompt, ...]
    last_activity_is_interrupt: bool | None
    counters: HookPostureCounters
    diagnostics: tuple[HookPostureDiagnostic, ...]
    last_event_name: str | None
    last_event_kind: NormalizedHookKind | None
    last_event_at_utc: str | None
    last_sequence: int | None
    presence: HookPresence = "unknown"
    turn_id: str | None = None
    blocked_tool_use_id: str | None = None
    terminal_source: str | None = None

    @property
    def prompt_active(self) -> bool:
        """Return whether at least one prompt is armed."""

        return self.armed_prompt_count > 0

    @property
    def settled(self) -> bool:
        """Return whether the turn is ready with no outstanding background work."""

        return self.turn_phase == "ready" and self.work == "clear"

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-serializable payload."""

        return asdict(self)
