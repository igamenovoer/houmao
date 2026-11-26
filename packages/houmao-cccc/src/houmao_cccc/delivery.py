"""Per-instance CCCC delivery settings and lease-local chat batching."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DeliverySettings(BaseModel):
    """Select the intake transport and its finite timing policy."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, allow_inf_nan=False)

    transport: Literal["pull", "push"] = "pull"
    pull_interval: float = Field(default=1.0, gt=0)
    push_policy: Literal["asap", "batch"] | None = None
    quiet_interval: float | None = Field(default=None, gt=0)
    max_wait: float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def _validate_policy(self) -> DeliverySettings:
        """Require a push policy and use timers only for timed push."""

        if (self.transport == "pull") != (self.push_policy is None):
            raise ValueError("Only push transport requires a push policy")
        if self.push_policy == "batch":
            if self.quiet_interval is None or self.max_wait is None:
                raise ValueError("Timed push requires quiet_interval and max_wait")
            if self.quiet_interval > self.max_wait:
                raise ValueError("quiet_interval must be at most max_wait")
        elif self.quiet_interval is not None or self.max_wait is not None:
            raise ValueError("Batch timers require the batch push policy")
        return self


@dataclass(frozen=True)
class ChatOffer:
    """One validated provider claim under the current receiver lease."""

    attempt_id: str
    event_id: str
    sequence: int
    sender: str
    timestamp: str
    mode: Literal["send", "request_reply"]
    text: str
    expires_at: float
    size: int


ChatBatch = tuple[ChatOffer, ...]
ChatSelection = tuple[ChatBatch, ...]


class DeliveryBuffer:
    """Stage bounded provider work and preserve sealed batch membership in FIFO order."""

    def __init__(self) -> None:
        """Start with an empty buffer and no intake credit."""

        self.m_settings: DeliverySettings = DeliverySettings()
        self.m_max_count: int = 0
        self.m_max_bytes: int = 0
        self.m_count: int = 0
        self.m_bytes: int = 0
        self.m_highest_sequence: int = 0
        self.m_open: list[ChatOffer] = []
        self.m_sealed: deque[ChatBatch] = deque()
        self.m_reservation: ChatSelection | None = None
        self.m_first: float = 0.0
        self.m_last: float = 0.0

    @classmethod
    def from_settings(
        cls, settings: DeliverySettings, *, max_count: int, max_bytes: int
    ) -> DeliveryBuffer:
        """Start a buffer for a lease with negotiated count and byte budgets."""

        buffer = cls()
        buffer.m_settings = settings
        buffer.m_max_count = max_count
        buffer.m_max_bytes = max_bytes
        return buffer

    @property
    def credit(self) -> tuple[int, int]:
        """Return remaining staged capacity, including work in dispatch."""

        return self.m_max_count - self.m_count, self.m_max_bytes - self.m_bytes

    @property
    def highest_sequence(self) -> int:
        """Return the last staged sequence for a replacement connection on this lease."""

        return self.m_highest_sequence

    @property
    def deadline(self) -> float | None:
        """Return the deadline of the current timed batch on the monotonic clock."""

        if not self.m_open:
            return None
        quiet = self.m_settings.quiet_interval
        maximum = self.m_settings.max_wait
        assert quiet is not None and maximum is not None
        return min(self.m_last + quiet, self.m_first + maximum)

    @property
    def head(self) -> ChatBatch | None:
        """Read the oldest sealed batch without freeing its capacity."""

        return self.m_sealed[0] if self.m_sealed else None

    @property
    def sealed(self) -> ChatSelection:
        """Read the sealed batches in delivery order."""

        return tuple(self.m_sealed)

    @property
    def open_count(self) -> int:
        """Return the number of messages still collecting in the timed batch."""

        return len(self.m_open)

    @property
    def reserved(self) -> bool:
        """Report whether a prompt or tool read currently owns the queue head."""

        return self.m_reservation is not None

    def reserve(self, selection: ChatSelection) -> bool:
        """Reserve an unchanged prefix without waiting or releasing staging credit."""

        if (
            self.reserved
            or not selection
            or len(selection) > len(self.m_sealed)
            or any(batch is not self.m_sealed[index] for index, batch in enumerate(selection))
        ):
            return False
        self.m_reservation = selection
        return True

    def release(self, selection: ChatSelection, *, consume: bool) -> None:
        """Release one head owner after its authoritative decision."""

        if self.m_reservation is not selection:
            raise ValueError("Only the reservation owner may release the current delivery head")
        if consume:
            for batch in selection:
                self.finish(batch)
        self.m_reservation = None

    def _seal(self) -> None:
        """Close the current open batch without altering its members."""

        if self.m_open:
            self.m_sealed.append(tuple(self.m_open))
            self.m_open.clear()

    def configure(self, settings: DeliverySettings) -> None:
        """Apply a same-transport edit after sealing previous timed work."""

        if settings != self.m_settings:
            self._seal()
            self.m_settings = settings

    def close_due(self, now: float) -> None:
        """Close a timed batch at the deadline, including an exact boundary."""

        deadline = self.deadline
        if deadline is not None and now >= deadline:
            self._seal()

    def stage(self, offers: list[ChatOffer], now: float) -> None:
        """Accept one pull snapshot or push frame without extending timers for repeats."""

        self.close_due(now)
        sequence = self.m_highest_sequence
        fresh = []
        for offer in offers:
            if offer.sequence > sequence:
                fresh.append(offer)
                sequence = offer.sequence
        count, capacity = self.credit
        size = sum(offer.size for offer in fresh)
        if len(fresh) > count or size > capacity:
            raise ValueError("Provider offers exceed staging credit")
        if not fresh:
            return
        self.m_highest_sequence = sequence
        self.m_count += len(fresh)
        self.m_bytes += size
        if self.m_settings.transport == "pull":
            self.m_sealed.append(tuple(fresh))
        elif self.m_settings.push_policy == "asap":
            self.m_sealed.extend((offer,) for offer in fresh)
        else:
            if not self.m_open:
                self.m_first = now
            self.m_open.extend(fresh)
            self.m_last = now

    def finish(self, batch: ChatBatch) -> None:
        """Release credit only after the head batch is settled or expired."""

        if self.head is not batch:
            raise ValueError("Only the current delivery batch may finish")
        self.m_sealed.popleft()
        self.m_count -= len(batch)
        self.m_bytes -= sum(offer.size for offer in batch)
