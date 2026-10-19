"""Channel health for one consumer's hook observation store.

The health state machine is driven by the tracking consumer's poll-cycle clock:
every cycle reports how many new observations were folded, whether the visible
TUI surface changed, and the collector's published status. The monitor owns no
clock and performs no I/O, which keeps the transition table deterministic and
directly testable.

State transitions
-----------------
``unavailable`` is the startup state. An event at any time moves the channel to
``active``. If no event arrives within the startup grace period the channel
stays ``unavailable``. Once active, a gap longer than the staleness threshold
combined with a changing TUI surface moves the channel to ``stale``; the next
current-generation event restores ``active``. Read failures move the channel to
``error`` until a healthy read arrives. A stopped collector is terminal, as are
the policy states ``disabled_by_policy`` and ``untrusted_workspace``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, cast, get_args


HookChannelState = Literal[
    "active",
    "unavailable",
    "stale",
    "disabled_by_policy",
    "untrusted_workspace",
    "error",
    "stopped",
]

STARTUP_GRACE_SECONDS = 15.0
STALENESS_THRESHOLD_SECONDS = 30.0
_TERMINAL_STATES = frozenset({"disabled_by_policy", "untrusted_workspace", "error", "stopped"})
_FORCED_STATES = frozenset({"disabled_by_policy", "untrusted_workspace", "error"})
_KNOWN_STATES = frozenset(get_args(HookChannelState))
_DEFAULT_DETAILS: dict[HookChannelState, str | None] = {
    "active": None,
    "unavailable": "No hook event has arrived yet.",
    "stale": "No hook event arrived within the staleness threshold while the TUI kept changing.",
    "disabled_by_policy": "Hook observation is disabled by policy for this session.",
    "untrusted_workspace": "Workspace trust is not established for hook observation.",
    "error": "The hook observation store could not be read.",
    "stopped": "The hook observation collector is stopped.",
}


@dataclass(frozen=True)
class HookChannelHealthSnapshot:
    """One health snapshot for a hook observation channel."""

    state: HookChannelState
    detail: str | None
    since_utc: str | None
    last_event_at_utc: str | None

    @property
    def degraded(self) -> bool:
        """Return whether the channel has no lifecycle authority."""

        return self.state != "active"


class HookChannelHealthMonitor:
    """Poll-cycle-driven health state machine for one hook channel."""

    def __init__(
        self,
        *,
        startup_grace_seconds: float = STARTUP_GRACE_SECONDS,
        staleness_threshold_seconds: float = STALENESS_THRESHOLD_SECONDS,
        forced_state: HookChannelState | None = None,
        since_utc: str | None = None,
        initial_detail: str | None = None,
    ) -> None:
        """Initialize the monitor in ``unavailable`` or a forced terminal state.

        Parameters
        ----------
        startup_grace_seconds:
            Window after the first observed cycle before a silent channel is
            reported as unavailable.
        staleness_threshold_seconds:
            Maximum event gap while the TUI keeps changing before an active
            channel is reported as stale.
        forced_state:
            Terminal state supplied by channel metadata (policy refusal or
            collector stop).
        since_utc:
            Optional wall-clock timestamp for the initial state.
        initial_detail:
            Optional bounded detail reason for the initial state, used for
            launch-time degradation reasons such as a settings conflict.
        """

        if startup_grace_seconds < 0:
            raise ValueError("startup_grace_seconds must not be negative")
        if staleness_threshold_seconds < 0:
            raise ValueError("staleness_threshold_seconds must not be negative")
        if forced_state is not None and forced_state not in _TERMINAL_STATES:
            raise ValueError(f"forced_state {forced_state!r} is not terminal")
        self.m_startup_grace_seconds: float = startup_grace_seconds
        self.m_staleness_threshold_seconds: float = staleness_threshold_seconds
        self.m_forced_state: HookChannelState | None = (
            forced_state if forced_state in _FORCED_STATES else None
        )
        self.m_collector_stopped: bool = forced_state == "stopped"
        self.m_state: HookChannelState = forced_state or "unavailable"
        self.m_detail: str | None = (
            bounded_health_detail(initial_detail)
            if self.m_state == "unavailable" and initial_detail
            else _DEFAULT_DETAILS[self.m_state]
        )
        self.m_detail_pinned: bool = bool(initial_detail) and self.m_state == "unavailable"
        self.m_since_utc: str | None = since_utc
        self.m_last_event_at_utc: str | None = None
        self.m_last_event_monotonic: float | None = None
        self.m_started_monotonic: float | None = None
        self.m_ever_event: bool = False

    @property
    def state(self) -> HookChannelState:
        """Return the current health state."""

        return self.m_state

    @property
    def startup_grace_seconds(self) -> float:
        """Return the configured startup silence window."""

        return self.m_startup_grace_seconds

    @property
    def staleness_threshold_seconds(self) -> float:
        """Return the configured event-gap staleness threshold."""

        return self.m_staleness_threshold_seconds

    @property
    def forced_state(self) -> HookChannelState | None:
        """Return the terminal state supplied by channel metadata, if any."""

        return self.m_forced_state

    def snapshot(self) -> HookChannelHealthSnapshot:
        """Return an immutable health snapshot."""

        return HookChannelHealthSnapshot(
            state=self.m_state,
            detail=self.m_detail,
            since_utc=self.m_since_utc,
            last_event_at_utc=self.m_last_event_at_utc,
        )

    def observe(
        self,
        *,
        now_monotonic: float,
        now_utc: str,
        events_this_cycle: int,
        tui_changed: bool,
        collector_status: str | None = None,
        read_error: str | None = None,
    ) -> HookChannelHealthSnapshot:
        """Apply one poll-cycle observation and return the new snapshot.

        Parameters
        ----------
        now_monotonic:
            Tracker monotonic clock for the current poll cycle.
        now_utc:
            Wall-clock timestamp for the current poll cycle.
        events_this_cycle:
            Number of current-generation observations folded this cycle.
        tui_changed:
            Whether the visible TUI surface changed since the previous cycle.
        collector_status:
            Collector status label read from ``channel.json``.
        read_error:
            Store read failure message, when the read failed.

        Returns
        -------
        HookChannelHealthSnapshot
            Health after applying the transition table.
        """

        if self.m_started_monotonic is None:
            self.m_started_monotonic = now_monotonic
        if events_this_cycle > 0:
            self.m_ever_event = True
            self.m_last_event_monotonic = now_monotonic
            self.m_last_event_at_utc = now_utc

        if collector_status == "stopped":
            self.m_collector_stopped = True

        if self.m_forced_state is not None:
            self._transition(self.m_forced_state, now_utc=now_utc)
        elif self.m_collector_stopped:
            self._transition("stopped", now_utc=now_utc)
        elif read_error is not None:
            self._transition("error", now_utc=now_utc, detail=read_error)
        elif events_this_cycle > 0:
            self._transition("active", now_utc=now_utc)
        elif self.m_state == "error":
            self._transition("active" if self.m_ever_event else "unavailable", now_utc=now_utc)
        elif self.m_state == "active":
            if self._staleness_elapsed(now_monotonic=now_monotonic, tui_changed=tui_changed):
                self._transition("stale", now_utc=now_utc)
        elif self.m_state == "unavailable":
            self._startup_grace_detail(now_monotonic=now_monotonic)
        return self.snapshot()

    def _staleness_elapsed(self, *, now_monotonic: float, tui_changed: bool) -> bool:
        """Return whether an active channel is stale for this cycle."""

        if not tui_changed or self.m_last_event_monotonic is None:
            return False
        elapsed = now_monotonic - self.m_last_event_monotonic
        return elapsed > self.m_staleness_threshold_seconds

    def _startup_grace_detail(self, *, now_monotonic: float) -> None:
        """Update the unavailable detail once the startup grace period elapses."""

        if self.m_detail_pinned:
            return
        if self.m_ever_event or self.m_started_monotonic is None:
            return
        if now_monotonic - self.m_started_monotonic < self.m_startup_grace_seconds:
            return
        self.m_detail = "No hook event arrived within the startup grace period."

    def _transition(
        self,
        state: HookChannelState,
        *,
        now_utc: str,
        detail: str | None = None,
    ) -> None:
        """Move to one state, keeping the original detail unless overridden."""

        if state == self.m_state:
            if detail is not None:
                self.m_detail = bounded_health_detail(detail)
            return
        self.m_state = state
        self.m_since_utc = now_utc
        self.m_detail = (
            bounded_health_detail(detail) if detail is not None else _DEFAULT_DETAILS[state]
        )


def bounded_health_detail(detail: str | None) -> str | None:
    """Return a bounded, single-line detail reason."""

    if detail is None:
        return None
    collapsed = " ".join(detail.split())
    if not collapsed:
        return None
    if len(collapsed) <= 160:
        return collapsed
    return collapsed[:159] + "…"


def coerce_channel_state(value: object) -> HookChannelState | None:
    """Return a known channel state for one metadata value, else ``None``."""

    if not isinstance(value, str) or value not in _KNOWN_STATES:
        return None
    return cast(HookChannelState, value)
