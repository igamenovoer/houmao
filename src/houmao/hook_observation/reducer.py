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

from houmao.hook_observation.codex_normalizer import CODEX_UNAVAILABLE_FLOOR_FAMILIES
from houmao.hook_observation.kimi_normalizer import KIMI_SILENT_FLOOR_FAMILIES
from houmao.hook_observation.models import (
    HookAdapter,
    HookArmedPrompt,
    HookObservation,
    HookPosture,
    HookPostureCounters,
    HookPostureDiagnostic,
    HookPostureDiagnosticKind,
    HookPresence,
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

    ``adapter="claude"`` (the default) keeps the provider-neutral FIFO
    armed-prompt rules. ``adapter="codex"`` selects the Codex turn-epoch rules
    from the Codex hook-observation state-transition design: ``turn_id``
    correlation, steer-within-epoch, ``Interrupt`` settlement, deny-aborts-turn
    blocked settling, compaction windows, and truthful terminal gaps.
    ``adapter="kimi"`` selects the Kimi rules from
    ``openspec/changes/add-kimi-hook-observation/design/state-transitions.md``:
    two-phase arm/bind turn correlation, ``PermissionResult``-settled blocked
    windows with a non-terminal deny path, hook-settled ``Interrupt``,
    compaction windows with a fresh post-compact epoch, nested subagent
    scopes, queue evidence, and truthful terminal gaps including the headless
    clean-exit case.
    """

    def __init__(
        self,
        *,
        adapter: HookAdapter = "claude",
        diagnostic_capacity: int = 32,
        duplicate_window: int = 512,
    ) -> None:
        """Initialize an empty posture.

        Parameters
        ----------
        adapter:
            Provider posture-rule set. Defaults to ``"claude"`` so existing
            callers keep the FIFO armed-prompt semantics.
        diagnostic_capacity:
            Maximum retained diagnostics. Older entries are discarded.
        duplicate_window:
            Number of recent ``(generation, sequence)`` keys retained for
            duplicate detection.
        """

        if adapter not in ("claude", "codex", "kimi"):
            raise ValueError(f"unknown adapter {adapter!r}")
        if diagnostic_capacity < 1:
            raise ValueError("diagnostic_capacity must be positive")
        if duplicate_window < 1:
            raise ValueError("duplicate_window must be positive")
        self.m_adapter: HookAdapter = adapter
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
        self.m_terminal_source: str | None = None
        self.m_blocked: bool = False
        self.m_blocked_tool_name: str | None = None
        self.m_blocked_tool_use_id: str | None = None
        self.m_maintenance_active: bool = False
        self.m_work: HookWorkState = "unknown"
        self.m_last_activity_is_interrupt: bool | None = None
        self.m_presence: HookPresence = "unknown"
        self.m_turn_id: str | None = None
        self.m_turn_phase: HookTurnPhase = "unknown"
        self.m_pre_maintenance_phase: HookTurnPhase | None = None
        self.m_pending_epoch: bool = False
        self.m_nested_scope_depth: int = 0
        self.m_seen_event_names: set[str] = set()
        self.m_finished: bool = False
        self.m_events_seen: int = 0
        self.m_normalized_events: int = 0
        self.m_unknown_events: int = 0
        self.m_malformed_events: int = 0
        self.m_orphan_terminals: int = 0
        self.m_orphan_generations: int = 0
        self.m_duplicate_events: int = 0
        self.m_steer_events: int = 0
        self.m_turn_epochs: int = 0
        self.m_compaction_boundaries: int = 0
        self.m_allow_settles: int = 0
        self.m_deny_settles: int = 0
        self.m_terminal_gaps: int = 0
        self.m_permission_requests: int = 0
        self.m_blocked_windows: int = 0
        self.m_queued_prompts: int = 0
        self.m_interrupts: int = 0
        self.m_subagent_starts: int = 0
        self.m_subagent_stops: int = 0
        self.m_heartbeats: int = 0
        self.m_last_event_name: str | None = None
        self.m_last_event_kind: NormalizedHookKind | None = None
        self.m_last_event_at_utc: str | None = None
        self.m_last_sequence: int | None = None

    @property
    def posture(self) -> HookPosture:
        """Return the current immutable posture snapshot."""

        if self.m_adapter in ("codex", "kimi"):
            turn_phase: HookTurnPhase = self.m_turn_phase
        elif self.m_armed_prompts:
            turn_phase = "blocked" if self.m_blocked else "active"
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
            steer_events=self.m_steer_events,
            turn_epochs=self.m_turn_epochs,
            compaction_boundaries=self.m_compaction_boundaries,
            allow_settles=self.m_allow_settles,
            deny_settles=self.m_deny_settles,
            terminal_gaps=self.m_terminal_gaps,
            permission_requests=self.m_permission_requests,
            blocked_windows=self.m_blocked_windows,
            queued_prompts=self.m_queued_prompts,
            interrupts=self.m_interrupts,
            subagent_starts=self.m_subagent_starts,
            subagent_stops=self.m_subagent_stops,
            heartbeats=self.m_heartbeats,
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
            presence=self.m_presence,
            turn_id=self.m_turn_id,
            blocked_tool_use_id=self.m_blocked_tool_use_id,
            terminal_source=self.m_terminal_source,
        )

    def reduce(self, observation: HookObservation) -> HookPosture:
        """Consume one observation in arrival order and return the posture."""

        self.m_events_seen += 1
        self.m_finished = False
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

        if self.m_adapter == "codex":
            self._apply_codex_observation(observation)
            return self.posture
        if self.m_adapter == "kimi":
            self._apply_kimi_observation(observation)
            return self.posture

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

    def finish(
        self,
        *,
        reason: str = "stream_end",
        headless: bool = False,
        process_returncode: int | None = None,
    ) -> HookPosture:
        """Close the observation stream and return the final posture.

        The Codex and Kimi adapters define a stream-end transition: an open
        turn without ``Stop``/``Interrupt``/``SessionEnd`` is a terminal gap
        with truthful ``unknown`` turn state. Kimi additionally settles a
        headless run that exited cleanly after a latched ``Stop`` without a
        ``SessionEnd`` and names the missing session end as a diagnostic. The
        Claude adapter has no stream-end rule, so this is a no-op there.

        Parameters
        ----------
        reason:
            Bounded reason label recorded in the terminal-gap diagnostic.
        headless:
            Whether the provider ran in print/headless mode. Ignored by the
            Claude and Codex adapters.
        process_returncode:
            Provider process exit code when known. A clean (``0``) headless
            exit after a latched terminal is terminal-settled.

        Returns
        -------
        HookPosture
            Final posture after the stream-end fallback.
        """

        if self.m_adapter == "kimi":
            return self._finish_kimi(
                reason=reason,
                headless=headless,
                process_returncode=process_returncode,
            )
        if self.m_adapter != "codex":
            return self.posture
        if self.m_finished:
            return self.posture
        self.m_finished = True
        open_turn = (
            self.m_turn_id is not None
            or self.m_turn_phase in ("active", "blocked")
            or bool(self.m_armed_prompts)
        )
        if open_turn:
            self.m_terminal_gaps += 1
            self._diagnose_at(
                "hook_terminal_gap",
                event_name=self.m_last_event_name or "<stream>",
                received_at_utc=self.m_last_event_at_utc or "",
                detail=f"{reason}:open_turn",
            )
            self.m_presence = "lost" if self.m_presence == "present" else self.m_presence
            self.m_turn_phase = "unknown"
            self.m_turn_id = None
            self.m_armed_prompts.clear()
            self._clear_blocked()
            self._clear_terminal()
        elif self.m_presence == "present":
            self.m_presence = "unknown"
        seen = self.m_seen_event_names
        for family in CODEX_UNAVAILABLE_FLOOR_FAMILIES:
            if family in seen:
                continue
            self._diagnose_at(
                "hook_unavailable_event_family",
                event_name=family,
                received_at_utc=self.m_last_event_at_utc or "",
                detail="not dispatched at the supported floor",
            )
        return self.posture

    def _apply_codex_observation(self, observation: HookObservation) -> None:
        """Dispatch one observation through the Codex turn-epoch rules."""

        self.m_seen_event_names.add(observation.event_name)
        if observation.kind == "session_started":
            self._apply_codex_session_started(observation)
        elif observation.kind == "prompt_submitted":
            self._apply_codex_prompt_submitted(observation)
        elif observation.kind in ("tool_started", "tool_completed", "activity"):
            self._apply_codex_tool_activity(observation)
        elif observation.kind == "permission_requested":
            self._apply_codex_permission_requested(observation)
        elif observation.kind == "permission_resolved":
            self._clear_blocked()
            if self.m_turn_id is not None:
                self.m_turn_phase = "active"
        elif observation.kind == "turn_completed":
            self._apply_codex_terminal(observation, result="success")
        elif observation.kind == "turn_interrupted":
            self._apply_codex_terminal(observation, result="interrupted")
        elif observation.kind == "turn_failed":
            self._apply_codex_terminal(observation, result="known_failure")
        elif observation.kind == "maintenance_started":
            self._apply_codex_maintenance_started(observation)
        elif observation.kind == "maintenance_ended":
            self._apply_codex_maintenance_ended(observation)
        elif observation.kind == "session_ended":
            self._apply_codex_session_ended(observation)
        else:
            self._count_unknown(observation)

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

    def _apply_codex_session_started(self, observation: HookObservation) -> None:
        """Apply SessionStart: reset on start/resume, mark compact boundaries."""

        self.m_presence = "present"
        if observation.session_id is not None:
            self.m_session_id = observation.session_id
        self.m_session_started = True
        self.m_session_start_source = observation.source
        if observation.source == "compact":
            self.m_compaction_boundaries += 1
            self._diagnose(
                "hook_compaction_boundary",
                observation,
                detail=observation.source,
            )
            if self.m_turn_phase == "unknown":
                self.m_turn_phase = self.m_pre_maintenance_phase or "ready"
            return
        self._reset_turn_state()
        self.m_turn_phase = "ready"

    def _apply_codex_prompt_submitted(self, observation: HookObservation) -> None:
        """Start a turn epoch, or keep a same-turn repeat as steered input."""

        self.m_presence = "present"
        same_turn = (
            observation.turn_id is not None
            and observation.turn_id == self.m_turn_id
            and self.m_turn_phase in ("active", "blocked")
        )
        if observation.steer or same_turn:
            self.m_steer_events += 1
            self._diagnose(
                "hook_steer_same_turn",
                observation,
                detail=observation.turn_id,
            )
            if self.m_turn_phase == "blocked":
                self._diagnose("hook_prompt_during_blocked", observation)
            else:
                self.m_turn_phase = "active"
            return
        if self.m_turn_id is not None or self.m_armed_prompts:
            self._diagnose(
                "hook_turn_epoch_superseded",
                observation,
                detail=f"{self.m_turn_id}->{observation.turn_id}",
            )
        if self.m_maintenance_active:
            self._diagnose("hook_prompt_during_maintenance", observation)
            self.m_maintenance_active = False
            self.m_pre_maintenance_phase = None
        self.m_turn_id = observation.turn_id
        self.m_turn_phase = "active"
        self.m_armed_prompts.clear()
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
        self.m_work = "unknown"
        self.m_turn_epochs += 1

    def _apply_codex_tool_activity(self, observation: HookObservation) -> None:
        """Apply tool activity, settling blocked only on the paired completion."""

        self.m_presence = "present"
        self.m_last_activity_is_interrupt = observation.is_interrupt
        if self.m_turn_id is None:
            return
        if observation.turn_id is not None and observation.turn_id != self.m_turn_id:
            return
        if observation.kind != "tool_completed":
            if self.m_turn_phase != "blocked":
                self.m_turn_phase = "active"
            return
        if self.m_blocked:
            if self.m_blocked_tool_use_id is None or (
                observation.tool_use_id == self.m_blocked_tool_use_id
            ):
                self.m_allow_settles += 1
                self._clear_blocked()
                self.m_turn_phase = "active"
            else:
                self._diagnose(
                    "hook_blocked_tool_mismatch",
                    observation,
                    detail=f"{self.m_blocked_tool_use_id}!={observation.tool_use_id}",
                )
            return
        self.m_turn_phase = "active"

    def _apply_codex_permission_requested(self, observation: HookObservation) -> None:
        """Enter blocked with the paired PreToolUse attribution when available."""

        self.m_presence = "present"
        if self.m_turn_id is None or (
            observation.turn_id is not None and observation.turn_id != self.m_turn_id
        ):
            self._diagnose("permission_without_armed_prompt", observation)
            return
        self.m_blocked = True
        self.m_blocked_tool_name = observation.tool_name
        self.m_blocked_tool_use_id = observation.tool_use_id
        self.m_turn_phase = "blocked"
        if observation.tool_use_id is None:
            self._diagnose(
                "hook_permission_pair_unresolved",
                observation,
                detail=observation.tool_name,
            )

    def _apply_codex_terminal(
        self,
        observation: HookObservation,
        *,
        result: HookTerminalResult,
    ) -> None:
        """Latch success, interrupted, or known_failure for the open epoch."""

        if observation.kind == "turn_completed" and observation.stop_hook_active is True:
            self._diagnose(
                "hook_stop_hook_active",
                observation,
                detail=f"terminal={observation.kind}",
            )
            if self.m_turn_id is not None:
                self.m_turn_phase = "active"
            return
        if self.m_turn_id is None:
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
        if observation.turn_id is not None and observation.turn_id != self.m_turn_id:
            self.m_orphan_terminals += 1
            self._diagnose(
                "hook_orphan_terminal",
                observation,
                detail=(
                    f"terminal={observation.kind}:turn_mismatch "
                    f"{observation.turn_id}!={self.m_turn_id}"
                ),
            )
            return
        if result == "interrupted" and self.m_blocked:
            self.m_deny_settles += 1
            self._diagnose(
                "hook_deny_aborted_turn",
                observation,
                detail=self.m_blocked_tool_name,
            )
        consumed = self.m_armed_prompts.popleft() if self.m_armed_prompts else None
        self._note_terminal(
            generation=observation.channel_generation,
            prompt_id=observation.prompt_id or self.m_turn_id,
        )
        self.m_terminal_result = result
        self.m_terminal_error_class = observation.error_class if result == "known_failure" else None
        self.m_terminal_prompt_id = observation.prompt_id
        self.m_terminal_consumed_prompt_id = (
            consumed.prompt_id if consumed is not None else self.m_turn_id
        )
        self.m_terminal_stop_hook_active = observation.stop_hook_active
        self.m_terminal_message_present = observation.last_assistant_message_present
        self.m_turn_id = None
        self.m_turn_phase = "ready"
        self.m_armed_prompts.clear()
        self._clear_blocked()

    def _apply_codex_maintenance_started(self, observation: HookObservation) -> None:
        """Open a compaction window and hold the current posture across it."""

        self.m_presence = "present"
        if not self.m_maintenance_active:
            self.m_pre_maintenance_phase = self.m_turn_phase
            self.m_maintenance_active = True
        if self.m_turn_phase == "unknown":
            self.m_turn_phase = "ready"

    def _apply_codex_maintenance_ended(self, observation: HookObservation) -> None:
        """Close the compaction window without minting a turn epoch."""

        del observation
        self.m_maintenance_active = False
        if self.m_turn_phase == "unknown":
            self.m_turn_phase = self.m_pre_maintenance_phase or "ready"
        self.m_pre_maintenance_phase = None

    def _apply_codex_session_ended(self, observation: HookObservation) -> None:
        """Lose presence; an open turn becomes a truthful terminal gap."""

        self.m_presence = "lost"
        open_turn = (
            self.m_turn_id is not None
            or self.m_turn_phase in ("active", "blocked")
            or bool(self.m_armed_prompts)
        )
        if open_turn:
            self.m_terminal_gaps += 1
            self._diagnose(
                "hook_session_end_with_open_turn",
                observation,
                detail=self.m_turn_id,
            )
            self.m_turn_phase = "unknown"
            self.m_turn_id = None
            self.m_armed_prompts.clear()
            self._clear_blocked()
            self._clear_terminal()
        self.m_maintenance_active = False
        self.m_pre_maintenance_phase = None

    def _apply_kimi_observation(self, observation: HookObservation) -> None:
        """Dispatch one observation through the Kimi arm/bind rules."""

        self.m_seen_event_names.add(observation.event_name)
        if observation.kind == "session_started":
            self._apply_kimi_session_started(observation)
        elif observation.kind == "session_ended":
            self._apply_kimi_session_ended(observation)
        elif observation.kind == "session_heartbeat":
            self._apply_kimi_session_heartbeat(observation)
        elif observation.kind == "prompt_submitted":
            self._apply_kimi_prompt_submitted(observation)
        elif observation.kind == "prompt_queued":
            self._apply_kimi_prompt_queued(observation)
        elif observation.kind == "turn_started":
            self._apply_kimi_turn_started(observation)
        elif observation.kind in ("tool_started", "tool_completed", "tool_failed"):
            self._apply_kimi_tool_activity(observation)
        elif observation.kind == "permission_requested":
            self._apply_kimi_permission_requested(observation)
        elif observation.kind == "permission_resolved":
            self._apply_kimi_permission_resolved(observation)
        elif observation.kind == "turn_completed":
            self._apply_kimi_terminal(observation, result="success")
        elif observation.kind == "turn_failed":
            self._apply_kimi_terminal(observation, result="known_failure")
        elif observation.kind == "turn_interrupted":
            self._apply_kimi_terminal(observation, result="interrupted")
        elif observation.kind == "maintenance_started":
            self._apply_kimi_maintenance_started(observation)
        elif observation.kind == "maintenance_ended":
            self._apply_kimi_maintenance_ended(observation)
        elif observation.kind == "subagent_started":
            self._apply_kimi_subagent_started(observation)
        elif observation.kind == "subagent_stopped":
            self._apply_kimi_subagent_stopped(observation)
        else:
            self._count_unknown(observation)

    def _apply_kimi_session_started(self, observation: HookObservation) -> None:
        """Establish presence; a provider start resets turn state."""

        self.m_presence = "present"
        if observation.session_id is not None:
            self.m_session_id = observation.session_id
        self.m_session_started = True
        self.m_session_start_source = observation.source
        if observation.source == "compact":
            self.m_compaction_boundaries += 1
            self._diagnose(
                "hook_compaction_boundary",
                observation,
                detail=observation.source,
            )
            if self.m_turn_phase == "unknown":
                self.m_turn_phase = self.m_pre_maintenance_phase or "ready"
            return
        self._reset_turn_state()
        self.m_turn_phase = "ready"

    def _apply_kimi_prompt_submitted(self, observation: HookObservation) -> None:
        """Arm a new turn epoch; steered input stays in the running epoch."""

        self.m_presence = "present"
        if observation.steer and self._kimi_epoch_open():
            self.m_steer_events += 1
            self._diagnose(
                "hook_steer_same_turn",
                observation,
                detail="steered input",
            )
            if self.m_turn_phase == "blocked":
                self._diagnose("hook_prompt_during_blocked", observation)
                self._clear_blocked()
            self.m_turn_phase = "active"
            return
        if observation.steer:
            self.m_steer_events += 1
            self._diagnose(
                "hook_steer_same_turn",
                observation,
                detail="without open turn",
            )
        if self._kimi_epoch_open():
            self._diagnose(
                "hook_turn_epoch_superseded",
                observation,
                detail=f"{self.m_turn_id or 'pending'}->pending",
            )
        if self.m_maintenance_active:
            self._diagnose("hook_prompt_during_maintenance", observation)
            self.m_maintenance_active = False
            self.m_pre_maintenance_phase = None
        self._kimi_arm_epoch(observation)

    def _apply_kimi_prompt_queued(self, observation: HookObservation) -> None:
        """Record queue evidence without arming a second prompt submission."""

        self.m_presence = "present"
        self.m_queued_prompts += 1
        queue_length = observation.queue_length
        self._diagnose(
            "hook_prompt_queued",
            observation,
            detail=(
                f"prompt_id={observation.prompt_id or '-'},"
                f"queue_length={queue_length if queue_length is not None else '-'}"
            ),
        )

    def _apply_kimi_turn_started(self, observation: HookObservation) -> None:
        """Bind the armed epoch; nested turns open a scope instead."""

        self.m_presence = "present"
        if observation.origin_kind == "system_trigger" or observation.origin_name == "subagent":
            self.m_nested_scope_depth += 1
            self._diagnose(
                "hook_nested_scope_opened",
                observation,
                detail=observation.origin_name or observation.origin_kind,
            )
            return
        if observation.turn_id is None:
            self._diagnose("hook_turn_started_without_turn_id", observation)
            return
        if self.m_pending_epoch or (
            self.m_turn_phase in ("active", "blocked") and self.m_turn_id is None
        ):
            self._kimi_bind_turn_id(observation)
            return
        if self.m_turn_phase in ("active", "blocked") and self.m_turn_id is not None:
            if observation.turn_id == self.m_turn_id:
                self.m_duplicate_events += 1
                self._diagnose(
                    "hook_duplicate_event",
                    observation,
                    detail=f"TurnStarted {observation.turn_id}",
                )
                return
            self._diagnose(
                "hook_turn_epoch_superseded",
                observation,
                detail=f"{self.m_turn_id}->{observation.turn_id}",
            )
        else:
            self._diagnose(
                "hook_turn_started_without_prompt",
                observation,
                detail=observation.turn_id,
            )
        self._kimi_arm_epoch(observation)
        self._kimi_bind_turn_id(observation)

    def _apply_kimi_tool_activity(self, observation: HookObservation) -> None:
        """Apply tool activity; the blocked window settles only at its result."""

        self.m_presence = "present"
        if self.m_turn_phase == "blocked":
            return
        if self._kimi_epoch_open():
            self.m_turn_phase = "active"
            return
        self._diagnose("hook_tool_without_turn", observation, detail=observation.tool_name)

    def _apply_kimi_permission_requested(self, observation: HookObservation) -> None:
        """Enter the hooks-only blocked phase for the open epoch."""

        self.m_presence = "present"
        if not self._kimi_epoch_open():
            self._diagnose("permission_without_armed_prompt", observation)
            return
        if observation.turn_id is not None:
            if self.m_turn_id is None:
                self.m_turn_id = observation.turn_id
                self.m_pending_epoch = False
            elif observation.turn_id != self.m_turn_id:
                self._diagnose(
                    "hook_permission_turn_mismatch",
                    observation,
                    detail=f"{observation.turn_id}!={self.m_turn_id}",
                )
        self.m_permission_requests += 1
        self.m_blocked_windows += 1
        self.m_blocked = True
        self.m_blocked_tool_name = observation.tool_name
        self.m_blocked_tool_use_id = observation.tool_use_id
        self.m_turn_phase = "blocked"
        if observation.tool_use_id is None:
            self._diagnose(
                "hook_permission_pair_unresolved",
                observation,
                detail=observation.tool_name,
            )

    def _apply_kimi_permission_resolved(self, observation: HookObservation) -> None:
        """Settle the blocked window for both approval and rejection."""

        self.m_presence = "present"
        if not self.m_blocked:
            self._diagnose("hook_permission_result_without_blocked", observation)
            return
        if (
            observation.tool_use_id is not None
            and self.m_blocked_tool_use_id is not None
            and observation.tool_use_id != self.m_blocked_tool_use_id
        ):
            self._diagnose(
                "hook_blocked_tool_mismatch",
                observation,
                detail=f"{self.m_blocked_tool_use_id}!={observation.tool_use_id}",
            )
        self._clear_blocked()
        if self._kimi_epoch_open():
            self.m_turn_phase = "active"
        decision = observation.permission_decision
        if decision == "approved":
            self.m_allow_settles += 1
        elif decision == "rejected":
            self.m_deny_settles += 1
        else:
            self._diagnose(
                "hook_permission_result_unexercised_decision",
                observation,
                detail=decision,
            )

    def _apply_kimi_terminal(
        self,
        observation: HookObservation,
        *,
        result: HookTerminalResult,
    ) -> None:
        """Latch success, interrupted, or known_failure for the open epoch."""

        self.m_presence = "present"
        if observation.kind == "turn_completed" and observation.stop_hook_active is True:
            self._diagnose(
                "hook_stop_hook_active",
                observation,
                detail="turn_completed",
            )
            if self._kimi_epoch_open():
                self.m_turn_phase = "active"
            return
        if result == "interrupted":
            self.m_interrupts += 1
        if observation.kind == "turn_completed" and self.m_nested_scope_depth > 0:
            self.m_nested_scope_depth -= 1
            self._diagnose(
                "hook_nested_scope_closed",
                observation,
                detail="Stop",
            )
            return
        if not self._kimi_epoch_open():
            self.m_orphan_terminals += 1
            self._diagnose(
                "hook_orphan_terminal",
                observation,
                detail=f"terminal={observation.kind}",
            )
            return
        if (
            observation.turn_id is not None
            and self.m_turn_id is not None
            and observation.turn_id != self.m_turn_id
        ):
            self.m_orphan_terminals += 1
            self._diagnose(
                "hook_orphan_terminal",
                observation,
                detail=(
                    f"terminal={observation.kind}:turn_mismatch "
                    f"{observation.turn_id}!={self.m_turn_id}"
                ),
            )
            return
        consumed = self.m_armed_prompts.popleft() if self.m_armed_prompts else None
        self.m_terminal_result = result
        self.m_terminal_source = "hook_observation"
        self.m_terminal_error_class = observation.error_class if result == "known_failure" else None
        self.m_terminal_prompt_id = observation.prompt_id
        self.m_terminal_consumed_prompt_id = (
            self.m_turn_id or observation.turn_id or (consumed.prompt_id if consumed else None)
        )
        self.m_terminal_stop_hook_active = observation.stop_hook_active
        self.m_terminal_message_present = observation.last_assistant_message_present
        self.m_turn_id = None
        self.m_pending_epoch = False
        self.m_turn_phase = "ready"
        self.m_armed_prompts.clear()
        self.m_nested_scope_depth = 0
        self._clear_blocked()

    def _apply_kimi_maintenance_started(self, observation: HookObservation) -> None:
        """Open a compaction window and hold the current posture across it."""

        self.m_presence = "present"
        if not self.m_maintenance_active:
            self.m_pre_maintenance_phase = self.m_turn_phase
            self.m_maintenance_active = True
            self.m_compaction_boundaries += 1
            self._diagnose(
                "hook_compaction_boundary",
                observation,
                detail=observation.maintenance_trigger,
            )
        if self.m_turn_phase == "unknown":
            self.m_turn_phase = "ready"

    def _apply_kimi_maintenance_ended(self, observation: HookObservation) -> None:
        """Close the compaction window without minting a turn epoch."""

        del observation
        self.m_maintenance_active = False
        if self.m_turn_phase == "unknown":
            self.m_turn_phase = self.m_pre_maintenance_phase or "ready"
        self.m_pre_maintenance_phase = None

    def _apply_kimi_session_heartbeat(self, observation: HookObservation) -> None:
        """Record liveness evidence; the heartbeat never shapes turn posture."""

        del observation
        self.m_presence = "present"
        self.m_heartbeats += 1

    def _apply_kimi_subagent_started(self, observation: HookObservation) -> None:
        """Open a nested subagent scope under the parent turn."""

        self.m_presence = "present"
        self.m_subagent_starts += 1
        self.m_nested_scope_depth += 1
        self._diagnose(
            "hook_nested_scope_opened",
            observation,
            detail=observation.agent_name or "subagent",
        )

    def _apply_kimi_subagent_stopped(self, observation: HookObservation) -> None:
        """Close the nested subagent scope; the parent turn stays open."""

        self.m_presence = "present"
        self.m_subagent_stops += 1
        if self.m_nested_scope_depth > 0:
            self.m_nested_scope_depth -= 1
            detail = observation.agent_name or "subagent"
        else:
            detail = "unmatched"
        self._diagnose("hook_nested_scope_closed", observation, detail=detail)

    def _apply_kimi_session_ended(self, observation: HookObservation) -> None:
        """Lose presence; an open turn becomes a truthful terminal gap."""

        self.m_presence = "lost"
        if self._kimi_epoch_open():
            self.m_terminal_gaps += 1
            self._diagnose(
                "hook_session_end_with_open_turn",
                observation,
                detail=self.m_turn_id or ("pending" if self.m_pending_epoch else None),
            )
            self.m_turn_phase = "unknown"
            self.m_turn_id = None
            self.m_pending_epoch = False
            self.m_armed_prompts.clear()
            self.m_nested_scope_depth = 0
            self._clear_blocked()
            self._clear_terminal()
        self.m_maintenance_active = False
        self.m_pre_maintenance_phase = None

    def _finish_kimi(
        self,
        *,
        reason: str,
        headless: bool,
        process_returncode: int | None,
    ) -> HookPosture:
        """Apply the Kimi stream-end terminal fallbacks."""

        if self.m_finished:
            return self.posture
        self.m_finished = True
        if self._kimi_epoch_open():
            self.m_terminal_gaps += 1
            self._diagnose_at(
                "hook_terminal_gap",
                event_name=self.m_last_event_name or "<stream>",
                received_at_utc=self.m_last_event_at_utc or "",
                detail=f"{reason}:open_turn",
            )
            if self.m_heartbeats == 0:
                self._diagnose_at(
                    "hook_heartbeat_liveness_unavailable",
                    event_name=self.m_last_event_name or "<stream>",
                    received_at_utc=self.m_last_event_at_utc or "",
                    detail="no heartbeat before the gap",
                )
            self.m_presence = "lost" if self.m_presence == "present" else self.m_presence
            self.m_turn_phase = "unknown"
            self.m_turn_id = None
            self.m_pending_epoch = False
            self.m_armed_prompts.clear()
            self.m_nested_scope_depth = 0
            self._clear_blocked()
            self._clear_terminal()
        elif self.m_presence == "present":
            if headless and process_returncode == 0:
                self.m_presence = "lost"
                self._diagnose_at(
                    "hook_headless_session_end_gap",
                    event_name=self.m_last_event_name or "<stream>",
                    received_at_utc=self.m_last_event_at_utc or "",
                    detail="clean process exit, no SessionEnd",
                )
            else:
                self.m_presence = "unknown"
        for family in KIMI_SILENT_FLOOR_FAMILIES:
            if family in self.m_seen_event_names:
                continue
            self._diagnose_at(
                "hook_unavailable_event_family",
                event_name=family,
                received_at_utc=self.m_last_event_at_utc or "",
                detail="not dispatched at the supported floor",
            )
        return self.posture

    def _kimi_epoch_open(self) -> bool:
        """Return whether an armed or bound Kimi turn epoch is open."""

        return (
            self.m_pending_epoch
            or self.m_turn_id is not None
            or self.m_turn_phase in ("active", "blocked")
        )

    def _kimi_arm_epoch(self, observation: HookObservation) -> None:
        """Arm a new epoch; the following TurnStarted binds its turn_id."""

        self.m_turn_id = None
        self.m_pending_epoch = True
        self.m_turn_phase = "active"
        self._clear_blocked()
        self._clear_terminal()
        self.m_armed_prompts.clear()
        self.m_armed_prompts.append(
            HookArmedPrompt(
                prompt_id=observation.prompt_id,
                provider_initiated=observation.provider_initiated,
                sequence=observation.sequence,
                armed_at_utc=observation.received_at_utc,
            )
        )
        self.m_work = "unknown"
        self.m_turn_epochs += 1

    def _kimi_bind_turn_id(self, observation: HookObservation) -> None:
        """Bind the armed epoch to the provider's turn identifier."""

        self.m_turn_id = observation.turn_id
        self.m_pending_epoch = False
        if not self.m_armed_prompts:
            self.m_armed_prompts.append(
                HookArmedPrompt(
                    prompt_id=observation.prompt_id,
                    provider_initiated=observation.provider_initiated,
                    sequence=observation.sequence,
                    armed_at_utc=observation.received_at_utc,
                )
            )
        if self.m_turn_phase == "unknown":
            self.m_turn_phase = "active"

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
        self.m_blocked_tool_use_id = None

    def _clear_terminal(self) -> None:
        """Clear the previous terminal latch for a newly armed turn."""

        self.m_terminal_result = "none"
        self.m_terminal_error_class = None
        self.m_terminal_prompt_id = None
        self.m_terminal_consumed_prompt_id = None
        self.m_terminal_stop_hook_active = None
        self.m_terminal_message_present = None
        self.m_terminal_source = None

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
        self.m_presence = "unknown"
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
        self.m_terminal_source = None
        self.m_blocked = False
        self.m_blocked_tool_name = None
        self.m_blocked_tool_use_id = None
        self.m_maintenance_active = False
        self.m_pre_maintenance_phase = None
        self.m_turn_id = None
        self.m_turn_phase = "unknown"
        self.m_pending_epoch = False
        self.m_nested_scope_depth = 0
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

    def _diagnose_at(
        self,
        kind: HookPostureDiagnosticKind,
        *,
        event_name: str,
        received_at_utc: str,
        detail: str | None = None,
    ) -> None:
        """Append one diagnostic that is not tied to a single observation."""

        self.m_diagnostics.append(
            HookPostureDiagnostic(
                kind=kind,
                event_name=event_name,
                channel_generation=self.m_generation or 0,
                received_at_utc=received_at_utc,
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
