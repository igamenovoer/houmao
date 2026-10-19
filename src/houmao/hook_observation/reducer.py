"""Pure hook posture reduction and its ReactiveX pipeline.

The reducer owns the normative merge rules from
``openspec/changes/add-cli-hook-observation-channel/design/state-transitions.md``:
a FIFO armed-prompt queue, hook-only blocked state, maintenance windows,
terminal latching, the session-scoped work axis, generation isolation, and
bounded secret-free diagnostics.
"""

from __future__ import annotations

from collections import deque

from reactivex import Observable, abc, operators as ops

from houmao.hook_observation.models import (
    HookArmedPrompt,
    HookObservation,
    HookPosture,
    HookPostureCounters,
    HookPostureDiagnostic,
    HookPostureDiagnosticKind,
    HookTerminalResult,
    HookTurnPhase,
    HookWorkState,
    NormalizedHookKind,
)


_SESSION_RESET_SOURCES = frozenset({"startup", "clear", "fork"})


class HookPostureReducer:
    """Stateful but I/O-free reducer for one hook channel.

    Each call to :meth:`reduce` consumes one observation in arrival order and
    returns the resulting immutable posture. Duplicate re-deliveries are
    idempotent when the envelope carries a sequence number.
    """

    def __init__(
        self,
        *,
        diagnostic_capacity: int = 32,
        duplicate_window: int = 512,
    ) -> None:
        """Initialize an empty posture.

        Parameters
        ----------
        diagnostic_capacity:
            Maximum retained diagnostics. Older entries are discarded.
        duplicate_window:
            Number of recent ``(generation, sequence)`` keys retained for
            duplicate detection.
        """

        if diagnostic_capacity < 1:
            raise ValueError("diagnostic_capacity must be positive")
        if duplicate_window < 1:
            raise ValueError("duplicate_window must be positive")
        self.m_diagnostic_capacity: int = diagnostic_capacity
        self.m_duplicate_window: int = duplicate_window
        self.m_diagnostics: deque[HookPostureDiagnostic] = deque(maxlen=diagnostic_capacity)
        self.m_seen_sequences: deque[tuple[int, int]] = deque(maxlen=duplicate_window)
        self.m_seen_sequence_set: set[tuple[int, int]] = set()
        self.m_recent_terminals: deque[tuple[int, str]] = deque(maxlen=duplicate_window)
        self.m_recent_terminal_set: set[tuple[int, str]] = set()
        self.m_generation: int | None = None
        self.m_generation_has_events: bool = False
        self.m_session_id: str | None = None
        self.m_session_started: bool = False
        self.m_session_start_source: str | None = None
        self.m_armed_prompts: deque[HookArmedPrompt] = deque()
        self.m_terminal_result: HookTerminalResult = "none"
        self.m_terminal_error_class: str | None = None
        self.m_terminal_prompt_id: str | None = None
        self.m_terminal_consumed_prompt_id: str | None = None
        self.m_terminal_stop_hook_active: bool | None = None
        self.m_terminal_message_present: bool | None = None
        self.m_blocked: bool = False
        self.m_blocked_tool_name: str | None = None
        self.m_maintenance_active: bool = False
        self.m_work: HookWorkState = "unknown"
        self.m_last_activity_is_interrupt: bool | None = None
        self.m_events_seen: int = 0
        self.m_normalized_events: int = 0
        self.m_unknown_events: int = 0
        self.m_malformed_events: int = 0
        self.m_orphan_terminals: int = 0
        self.m_orphan_generations: int = 0
        self.m_duplicate_events: int = 0
        self.m_last_event_name: str | None = None
        self.m_last_event_kind: NormalizedHookKind | None = None
        self.m_last_event_at_utc: str | None = None
        self.m_last_sequence: int | None = None

    @property
    def posture(self) -> HookPosture:
        """Return the current immutable posture snapshot."""

        if self.m_armed_prompts:
            turn_phase: HookTurnPhase = "blocked" if self.m_blocked else "active"
        elif self.m_terminal_result != "none":
            turn_phase = "ready"
        else:
            turn_phase = "unknown"
        active_prompt = self.m_armed_prompts[0] if self.m_armed_prompts else None
        counters = HookPostureCounters(
            events_seen=self.m_events_seen,
            normalized_events=self.m_normalized_events,
            unknown_events=self.m_unknown_events,
            malformed_events=self.m_malformed_events,
            orphan_terminals=self.m_orphan_terminals,
            orphan_generations=self.m_orphan_generations,
            duplicate_events=self.m_duplicate_events,
        )
        return HookPosture(
            generation=self.m_generation,
            session_id=self.m_session_id,
            session_started=self.m_session_started,
            session_start_source=self.m_session_start_source,
            turn_phase=turn_phase,
            terminal_result=self.m_terminal_result,
            terminal_error_class=self.m_terminal_error_class,
            terminal_prompt_id=self.m_terminal_prompt_id,
            terminal_consumed_prompt_id=self.m_terminal_consumed_prompt_id,
            terminal_stop_hook_active=self.m_terminal_stop_hook_active,
            terminal_message_present=self.m_terminal_message_present,
            blocked=self.m_blocked,
            blocked_tool_name=self.m_blocked_tool_name,
            maintenance_active=self.m_maintenance_active,
            work=self.m_work,
            active_prompt_id=None if active_prompt is None else active_prompt.prompt_id,
            active_prompt_provider_initiated=(
                None if active_prompt is None else active_prompt.provider_initiated
            ),
            armed_prompt_count=len(self.m_armed_prompts),
            queued_prompt_count=max(0, len(self.m_armed_prompts) - 1),
            armed_prompts=tuple(self.m_armed_prompts),
            last_activity_is_interrupt=self.m_last_activity_is_interrupt,
            counters=counters,
            diagnostics=tuple(self.m_diagnostics),
            last_event_name=self.m_last_event_name,
            last_event_kind=self.m_last_event_kind,
            last_event_at_utc=self.m_last_event_at_utc,
            last_sequence=self.m_last_sequence,
        )

    def reduce(self, observation: HookObservation) -> HookPosture:
        """Consume one observation in arrival order and return the posture."""

        self.m_events_seen += 1
        generation = observation.channel_generation
        if self.m_generation is not None:
            if generation < self.m_generation:
                self.m_orphan_generations += 1
                self._diagnose(
                    "hook_orphan_generation",
                    observation,
                    detail=f"generation {generation} < current {self.m_generation}",
                )
                return self.posture
            if generation > self.m_generation:
                self._reset_generation(generation)

        if observation.kind == "generation_started":
            if self.m_generation is None:
                self.m_generation = generation
            if not self.m_generation_has_events:
                self._reset_generation_state()
            return self.posture

        if self.m_generation is None:
            self.m_generation = generation
        if observation.sequence is not None and self._seen_sequence(
            generation=generation,
            sequence=observation.sequence,
        ):
            self.m_duplicate_events += 1
            self._diagnose(
                "hook_duplicate_event",
                observation,
                detail=f"sequence {observation.sequence}",
            )
            return self.posture

        self.m_generation_has_events = True
        if observation.kind != "unknown":
            self.m_normalized_events += 1
        self.m_last_event_name = observation.event_name
        self.m_last_event_kind = observation.kind
        self.m_last_event_at_utc = observation.received_at_utc
        self.m_last_sequence = observation.sequence

        if observation.kind == "session_started":
            self._apply_session_started(observation)
        elif observation.kind == "prompt_submitted":
            self._apply_prompt_submitted(observation)
        elif observation.kind == "activity":
            self._apply_activity(observation)
        elif observation.kind == "permission_requested":
            self._apply_permission_requested(observation)
        elif observation.kind == "permission_resolved":
            self._clear_blocked()
        elif observation.kind == "turn_completed":
            self._apply_terminal(observation, result="success")
        elif observation.kind == "turn_failed":
            self._apply_terminal(observation, result="known_failure")
        elif observation.kind == "maintenance_started":
            self.m_maintenance_active = True
        elif observation.kind == "maintenance_ended":
            self.m_maintenance_active = False
        else:
            self._count_unknown(observation)
        return self.posture

    def _apply_session_started(self, observation: HookObservation) -> None:
        """Apply one SessionStart with source-specific reset semantics."""

        if observation.source in _SESSION_RESET_SOURCES:
            self._reset_turn_state()
            self.m_session_id = observation.session_id
        elif observation.session_id is not None:
            self.m_session_id = observation.session_id
        self.m_session_started = True
        self.m_session_start_source = observation.source

    def _apply_prompt_submitted(self, observation: HookObservation) -> None:
        """Append one armed prompt behind any already-armed prompts."""

        self.m_armed_prompts.append(
            HookArmedPrompt(
                prompt_id=observation.prompt_id,
                provider_initiated=observation.provider_initiated,
                sequence=observation.sequence,
                armed_at_utc=observation.received_at_utc,
            )
        )
        self._clear_blocked()
        self._clear_terminal()
        if observation.prompt_id is None:
            self._diagnose("prompt_id_missing", observation)

    def _apply_activity(self, observation: HookObservation) -> None:
        """Apply tool activity and resolve any outstanding permission wait."""

        self._clear_blocked()
        self.m_last_activity_is_interrupt = observation.is_interrupt

    def _apply_permission_requested(self, observation: HookObservation) -> None:
        """Enter the hook-only blocked phase for an armed turn."""

        if not self.m_armed_prompts:
            self._diagnose("permission_without_armed_prompt", observation)
            return
        self.m_blocked = True
        self.m_blocked_tool_name = observation.tool_name

    def _apply_terminal(self, observation: HookObservation, *, result: HookTerminalResult) -> None:
        """Consume the oldest armed prompt or record an orphan diagnostic."""

        if observation.stop_hook_active is True:
            self._diagnose(
                "hook_stop_hook_active",
                observation,
                detail=f"terminal={observation.kind}",
            )
            return
        if not self.m_armed_prompts:
            if observation.prompt_id is not None and self._is_recent_terminal(
                generation=observation.channel_generation,
                prompt_id=observation.prompt_id,
            ):
                self.m_duplicate_events += 1
                self._diagnose(
                    "hook_duplicate_event",
                    observation,
                    detail="terminal re-delivery",
                )
                return
            self.m_orphan_terminals += 1
            self._diagnose(
                "hook_orphan_terminal",
                observation,
                detail=f"terminal={observation.kind}",
            )
            return
        consumed = self.m_armed_prompts.popleft()
        self._note_terminal(
            generation=observation.channel_generation,
            prompt_id=observation.prompt_id,
        )
        self.m_terminal_result = result
        self.m_terminal_error_class = observation.error_class if result == "known_failure" else None
        self.m_terminal_prompt_id = observation.prompt_id
        self.m_terminal_consumed_prompt_id = consumed.prompt_id
        self.m_terminal_stop_hook_active = observation.stop_hook_active
        self.m_terminal_message_present = observation.last_assistant_message_present
        self._clear_blocked()
        if result == "success" and observation.background_work_pending is not None:
            self.m_work = "pending" if observation.background_work_pending else "clear"

    def _count_unknown(self, observation: HookObservation) -> None:
        """Count one unknown or malformed observation without posture changes."""

        if observation.malformed:
            self.m_malformed_events += 1
            self._diagnose(
                "hook_malformed_event",
                observation,
                detail=observation.malformed_reason,
            )
            return
        self.m_unknown_events += 1
        self._diagnose("hook_unknown_event", observation)

    def _clear_blocked(self) -> None:
        """Leave the blocked phase."""

        self.m_blocked = False
        self.m_blocked_tool_name = None

    def _clear_terminal(self) -> None:
        """Clear the previous terminal latch for a newly armed turn."""

        self.m_terminal_result = "none"
        self.m_terminal_error_class = None
        self.m_terminal_prompt_id = None
        self.m_terminal_consumed_prompt_id = None
        self.m_terminal_stop_hook_active = None
        self.m_terminal_message_present = None

    def _seen_sequence(self, *, generation: int, sequence: int) -> bool:
        """Return whether a sequence was already consumed, recording new keys."""

        key = (generation, sequence)
        if key in self.m_seen_sequence_set:
            return True
        if len(self.m_seen_sequences) >= self.m_duplicate_window:
            oldest = self.m_seen_sequences.popleft()
            self.m_seen_sequence_set.discard(oldest)
        self.m_seen_sequences.append(key)
        self.m_seen_sequence_set.add(key)
        return False

    def _note_terminal(self, *, generation: int, prompt_id: str | None) -> None:
        """Remember one consumed terminal prompt for re-delivery detection."""

        if prompt_id is None:
            return
        key = (generation, prompt_id)
        if key in self.m_recent_terminal_set:
            return
        if len(self.m_recent_terminals) >= self.m_duplicate_window:
            oldest = self.m_recent_terminals.popleft()
            self.m_recent_terminal_set.discard(oldest)
        self.m_recent_terminals.append(key)
        self.m_recent_terminal_set.add(key)

    def _is_recent_terminal(self, *, generation: int, prompt_id: str) -> bool:
        """Return whether a prompt already produced a terminal in this generation."""

        return (generation, prompt_id) in self.m_recent_terminal_set

    def _reset_generation(self, generation: int) -> None:
        """Start a new generation with a clean posture."""

        self.m_generation = generation
        self._reset_generation_state()

    def _reset_generation_state(self) -> None:
        """Clear generation-scoped posture while retaining counters."""

        self.m_generation_has_events = False
        self.m_session_id = None
        self.m_session_started = False
        self.m_session_start_source = None
        self.m_last_event_name = None
        self.m_last_event_kind = None
        self.m_last_event_at_utc = None
        self.m_last_sequence = None
        self._reset_turn_state()

    def _reset_turn_state(self) -> None:
        """Clear turn-scoped posture without touching identity or counters."""

        self.m_armed_prompts.clear()
        self.m_terminal_result = "none"
        self.m_terminal_error_class = None
        self.m_terminal_prompt_id = None
        self.m_terminal_consumed_prompt_id = None
        self.m_terminal_stop_hook_active = None
        self.m_terminal_message_present = None
        self.m_blocked = False
        self.m_blocked_tool_name = None
        self.m_maintenance_active = False
        self.m_work = "unknown"
        self.m_last_activity_is_interrupt = None
        self.m_recent_terminals.clear()
        self.m_recent_terminal_set.clear()

    def _diagnose(
        self,
        kind: HookPostureDiagnosticKind,
        observation: HookObservation,
        *,
        detail: str | None = None,
    ) -> None:
        """Append one bounded diagnostic with no payload content."""

        self.m_diagnostics.append(
            HookPostureDiagnostic(
                kind=kind,
                event_name=observation.event_name,
                channel_generation=observation.channel_generation,
                received_at_utc=observation.received_at_utc,
                detail=detail,
            )
        )


def build_hook_posture_pipeline(
    source: Observable[HookObservation],
    *,
    scheduler: abc.SchedulerBase,
    reducer: HookPostureReducer | None = None,
) -> Observable[HookPosture]:
    """Build the posture stream as an ``ops.scan`` over normalized observations.

    Parameters
    ----------
    source:
        Normalized observations in store arrival order.
    scheduler:
        Tracker scheduler reserved for timed reductions. The v1 reducer has no
        timed operators, so reduction is synchronous on the source scheduler.
    reducer:
        Optional caller-owned reducer, for consumers that also inspect the
        reducer directly.

    Returns
    -------
    Observable[HookPosture]
        One posture snapshot per consumed observation.
    """

    posture_reducer = reducer if reducer is not None else HookPostureReducer()

    def _accumulate(_previous: HookPosture, observation: HookObservation) -> HookPosture:
        """Fold one observation into the caller-owned reducer."""

        return posture_reducer.reduce(observation)

    del scheduler
    return source.pipe(
        ops.scan(_accumulate, seed=posture_reducer.posture),
        ops.share(),
    )
