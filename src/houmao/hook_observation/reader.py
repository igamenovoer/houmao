"""Per-consumer tailing reader for the session hook event store.

Every tracking consumer owns one reader over the session-local
``hook-observation/claude/events.ndjson`` file. The reader resumes from its
in-memory byte offset, refuses to consume an unterminated final line (the
collector may still be writing it), drops records from older channel
generations, and counts malformed or garbage lines instead of failing.

The module also composes the consumer-side channel input: reader, posture
reducer, and health monitor. The tracker supplies the scheduler and drives one
``read_cycle`` per poll cycle.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from houmao.hook_observation.health import (
    STARTUP_GRACE_SECONDS,
    STALENESS_THRESHOLD_SECONDS,
    HookChannelHealthMonitor,
    HookChannelHealthSnapshot,
    HookChannelState,
    coerce_channel_state,
)
from houmao.hook_observation.models import HookEventEnvelope, HookObservation
from houmao.hook_observation.normalizer import normalize_envelope
from houmao.hook_observation.reducer import HookPostureReducer
from houmao.hook_observation.store import (
    CHANNEL_FILENAME,
    CLAUDE_ADAPTER_DIRNAME,
    EVENTS_FILENAME,
    HOOK_OBSERVATION_DIRNAME,
    MAX_ENVELOPE_LINE_BYTES,
    parse_envelope_line,
)


READ_CHUNK_BYTES = MAX_ENVELOPE_LINE_BYTES + 1
COLLECTOR_RECORD_FILENAME = "collector.json"
_FORCED_HEALTH_STATES = frozenset({"disabled_by_policy", "untrusted_workspace", "error", "stopped"})
_EXPLICIT_STATE_PRECEDES_COLLECTOR = frozenset(
    {"unavailable", "installing", "disabled_by_policy", "untrusted_workspace", "error", "stopped"}
)


@dataclass(frozen=True)
class HookReadBatch:
    """One incremental read from the hook event store."""

    observations: tuple[HookObservation, ...] = ()
    current_generation: int | None = None
    skipped_blank_lines: int = 0
    skipped_garbage_lines: int = 0
    skipped_invalid_lines: int = 0
    skipped_oversized_lines: int = 0
    dropped_old_generation_lines: int = 0
    retried_partial_line: bool = False
    read_error: str | None = None

    @property
    def skipped_lines(self) -> int:
        """Return the total number of skipped non-envelope lines."""

        return (
            self.skipped_blank_lines
            + self.skipped_garbage_lines
            + self.skipped_invalid_lines
            + self.skipped_oversized_lines
        )


@dataclass(frozen=True)
class HookReadChunk:
    """Parsed envelopes and skip counters from one byte range."""

    envelopes: tuple[HookEventEnvelope, ...]
    skipped_blank_lines: int
    skipped_garbage_lines: int
    skipped_invalid_lines: int
    skipped_oversized_lines: int


@dataclass(frozen=True)
class HookChannelCycle:
    """One poll-cycle read of the hook observation channel."""

    observations: tuple[HookObservation, ...]
    health: HookChannelHealthSnapshot
    current_generation: int | None = None
    read_error: str | None = None
    retried_partial_line: bool = False
    skipped_blank_lines: int = 0
    skipped_garbage_lines: int = 0
    skipped_invalid_lines: int = 0
    skipped_oversized_lines: int = 0
    dropped_old_generation_lines: int = 0


class HookObservationReader:
    """Byte-offset reader over one session's append-only hook event store.

    A new reader scans the store from the first line, keeps only records from
    the newest generation it finds, and leaves any unterminated final line for
    the next read. Later reads resume from the retained offset.
    """

    def __init__(self, events_path: Path | str) -> None:
        """Initialize one reader bound to an events file.

        Parameters
        ----------
        events_path:
            Path to the session-local ``events.ndjson`` file. The file may not
            exist yet.
        """

        self.m_events_path: Path = Path(events_path)
        self.m_offset: int = 0
        self.m_current_generation: int | None = None
        self.m_initialized: bool = False

    @property
    def events_path(self) -> Path:
        """Return the watched events file path."""

        return self.m_events_path

    @property
    def offset(self) -> int:
        """Return the byte offset of the next unread complete line."""

        return self.m_offset

    @property
    def current_generation(self) -> int | None:
        """Return the newest channel generation observed by this reader."""

        return self.m_current_generation

    def read_new(self) -> HookReadBatch:
        """Read records appended since the previous call.

        Returns
        -------
        HookReadBatch
            Current-generation observations plus skip and retry counters.
        """

        try:
            size = self.m_events_path.stat().st_size
        except FileNotFoundError:
            return HookReadBatch(current_generation=self.m_current_generation)
        except OSError:
            return HookReadBatch(
                current_generation=self.m_current_generation,
                read_error="Hook event store is not readable.",
            )

        if not self.m_initialized or size < self.m_offset:
            self._reset()
            return self._read_initial(size)
        if size == self.m_offset:
            if self.m_offset > 0 and not self._offset_is_line_boundary():
                self._reset()
                return self._read_initial(size)
            return HookReadBatch(current_generation=self.m_current_generation)
        if self.m_offset > 0 and not self._offset_is_line_boundary():
            self._reset()
            return self._read_initial(size)
        return self._read_incremental(size)

    def _reset(self) -> None:
        """Forget offsets and generation after a fresh start or truncation."""

        self.m_offset = 0
        self.m_current_generation = None
        self.m_initialized = False

    def _offset_is_line_boundary(self) -> bool:
        """Return whether the retained offset still follows a complete line."""

        try:
            with self.m_events_path.open("rb") as handle:
                handle.seek(self.m_offset - 1)
                return handle.read(1) == b"\n"
        except OSError:
            return True

    def _read_initial(self, size: int) -> HookReadBatch:
        """Scan a fresh store and keep only the newest generation."""

        try:
            data = self.m_events_path.read_bytes()
        except OSError:
            return HookReadBatch(read_error="Hook event store is not readable.")
        self.m_initialized = True
        if not data:
            self.m_offset = 0
            return HookReadBatch()
        last_newline = data.rfind(b"\n")
        if last_newline < 0:
            self.m_offset = 0
            return HookReadBatch(retried_partial_line=True)
        complete = data[: last_newline + 1]
        self.m_offset = last_newline + 1
        chunk = _parse_chunk(complete)
        generation = max(
            (envelope.channel_generation for envelope in chunk.envelopes),
            default=None,
        )
        self.m_current_generation = generation
        observations, dropped = _current_generation_observations(
            envelopes=chunk.envelopes,
            generation=generation,
        )
        return HookReadBatch(
            observations=observations,
            current_generation=generation,
            skipped_blank_lines=chunk.skipped_blank_lines,
            skipped_garbage_lines=chunk.skipped_garbage_lines,
            skipped_invalid_lines=chunk.skipped_invalid_lines,
            skipped_oversized_lines=chunk.skipped_oversized_lines,
            dropped_old_generation_lines=dropped,
            retried_partial_line=self.m_offset < size,
        )

    def _read_incremental(self, size: int) -> HookReadBatch:
        """Read complete lines appended after the retained offset."""

        envelopes: list[HookEventEnvelope] = []
        skipped_blank_lines = 0
        skipped_garbage_lines = 0
        skipped_invalid_lines = 0
        skipped_oversized_lines = 0
        position = self.m_offset
        read_error: str | None = None
        while position < size:
            try:
                with self.m_events_path.open("rb") as handle:
                    handle.seek(position)
                    data = handle.read(READ_CHUNK_BYTES)
            except OSError:
                read_error = "Hook event store is not readable."
                break
            if not data:
                break
            last_newline = data.rfind(b"\n")
            if last_newline < 0:
                if len(data) < READ_CHUNK_BYTES:
                    break
                line_end = self._find_line_end(start=position + len(data), size=size)
                if line_end is None:
                    break
                skipped_oversized_lines += 1
                position = line_end
                continue
            complete = data[: last_newline + 1]
            chunk = _parse_chunk(complete)
            envelopes.extend(chunk.envelopes)
            skipped_blank_lines += chunk.skipped_blank_lines
            skipped_garbage_lines += chunk.skipped_garbage_lines
            skipped_invalid_lines += chunk.skipped_invalid_lines
            skipped_oversized_lines += chunk.skipped_oversized_lines
            position += last_newline + 1
        self.m_offset = position
        generation = max(
            (
                candidate
                for candidate in (
                    self.m_current_generation,
                    *(envelope.channel_generation for envelope in envelopes),
                )
                if candidate is not None
            ),
            default=None,
        )
        self.m_current_generation = generation
        observations, dropped = _current_generation_observations(
            envelopes=tuple(envelopes),
            generation=generation,
        )
        return HookReadBatch(
            observations=observations,
            current_generation=generation,
            skipped_blank_lines=skipped_blank_lines,
            skipped_garbage_lines=skipped_garbage_lines,
            skipped_invalid_lines=skipped_invalid_lines,
            skipped_oversized_lines=skipped_oversized_lines,
            dropped_old_generation_lines=dropped,
            retried_partial_line=self.m_offset < size,
            read_error=read_error,
        )

    def _find_line_end(self, *, start: int, size: int) -> int | None:
        """Return the offset after the next newline at or after ``start``."""

        position = start
        try:
            with self.m_events_path.open("rb") as handle:
                handle.seek(position)
                while position < size:
                    chunk = handle.read(READ_CHUNK_BYTES)
                    if not chunk:
                        return None
                    index = chunk.find(b"\n")
                    if index >= 0:
                        return position + index + 1
                    position += len(chunk)
        except OSError:
            return None
        return None


class HookObservationChannel:
    """Consumer-side hook channel input: reader, reducer, and health."""

    def __init__(
        self,
        *,
        events_path: Path | str,
        channel_path: Path | str,
        channel_status: dict[str, Any] | None = None,
        startup_grace_seconds: float = STARTUP_GRACE_SECONDS,
        staleness_threshold_seconds: float = STALENESS_THRESHOLD_SECONDS,
        reducer: HookPostureReducer | None = None,
    ) -> None:
        """Initialize one channel input for a consumer.

        Parameters
        ----------
        events_path:
            Session-local events file.
        channel_path:
            Session-local ``channel.json`` status file.
        channel_status:
            Already-read status document; re-read per cycle when omitted.
        startup_grace_seconds:
            Startup silence window for the health machine.
        staleness_threshold_seconds:
            Event-gap threshold for the stale state.
        reducer:
            Optional caller-owned posture reducer.
        """

        self.m_reader = HookObservationReader(events_path)
        self.m_channel_path = Path(channel_path)
        self.m_collector_path = self.m_channel_path.with_name(COLLECTOR_RECORD_FILENAME)
        self.m_reducer = reducer if reducer is not None else HookPostureReducer()
        self.m_status: dict[str, Any] | None = channel_status
        forced_state = _forced_health_state(self.m_status)
        explicit_state = _explicit_channel_state(self.m_status)
        self.m_health = HookChannelHealthMonitor(
            startup_grace_seconds=startup_grace_seconds,
            staleness_threshold_seconds=staleness_threshold_seconds,
            forced_state=forced_state,
            since_utc=_status_timestamp(self.m_status),
            initial_detail=(
                _install_detail(self.m_status)
                if explicit_state in {"unavailable", "installing"}
                else None
            ),
        )

    @classmethod
    def from_session_root(
        cls,
        session_root: str | Path | None,
        *,
        startup_grace_seconds: float = STARTUP_GRACE_SECONDS,
        staleness_threshold_seconds: float = STALENESS_THRESHOLD_SECONDS,
        reducer: HookPostureReducer | None = None,
    ) -> HookObservationChannel | None:
        """Build the channel when the session store advertises one.

        Parameters
        ----------
        session_root:
            Session root that owns the hook subtree. ``None`` disables the
            channel.
        startup_grace_seconds:
            Startup silence window for the health machine.
        staleness_threshold_seconds:
            Event-gap threshold for the stale state.
        reducer:
            Optional caller-owned posture reducer.

        Returns
        -------
        HookObservationChannel | None
            A channel when ``hook-observation/claude/channel.json`` exists and
            parses as a JSON object; ``None`` otherwise.
        """

        if session_root is None or not str(session_root).strip():
            return None
        channel_dir = Path(session_root).expanduser() / HOOK_OBSERVATION_DIRNAME
        channel_dir = channel_dir / CLAUDE_ADAPTER_DIRNAME
        channel_path = channel_dir / CHANNEL_FILENAME
        status = read_channel_status(channel_path)
        if status is None:
            return None
        return cls(
            events_path=channel_dir / EVENTS_FILENAME,
            channel_path=channel_path,
            channel_status=status,
            startup_grace_seconds=startup_grace_seconds,
            staleness_threshold_seconds=staleness_threshold_seconds,
            reducer=reducer,
        )

    @property
    def reader(self) -> HookObservationReader:
        """Return the byte-offset event reader."""

        return self.m_reader

    @property
    def reducer(self) -> HookPostureReducer:
        """Return the posture reducer owned by this channel."""

        return self.m_reducer

    @property
    def health(self) -> HookChannelHealthMonitor:
        """Return the health monitor owned by this channel."""

        return self.m_health

    @property
    def events_path(self) -> Path:
        """Return the watched events file path."""

        return self.m_reader.events_path

    @property
    def channel_path(self) -> Path:
        """Return the status file path."""

        return self.m_channel_path

    @property
    def collector_path(self) -> Path:
        """Return the collector liveness record path."""

        return self.m_collector_path

    def read_cycle(
        self,
        *,
        now_monotonic: float,
        now_utc: str,
        tui_changed: bool,
    ) -> HookChannelCycle:
        """Read new observations and update channel health for one cycle.

        Parameters
        ----------
        now_monotonic:
            Tracker monotonic clock value for this cycle.
        now_utc:
            Wall-clock timestamp for this cycle.
        tui_changed:
            Whether the visible TUI surface changed since the previous cycle.

        Returns
        -------
        HookChannelCycle
            New observations plus the post-transition health snapshot.
        """

        status = read_channel_status(self.m_channel_path)
        if status is not None:
            self.m_status = status
        collector_status = _collector_status(status)
        forced_state = _forced_health_state(status)
        explicit_state = _explicit_channel_state(status)
        if explicit_state not in _EXPLICIT_STATE_PRECEDES_COLLECTOR:
            channel_generation = self.m_reader.current_generation
            if channel_generation is None:
                channel_generation = _status_generation(status)
            if _collector_record_stopped(
                self.m_collector_path,
                channel_generation=channel_generation,
            ):
                collector_status = "stopped"
        if forced_state is not None and forced_state != self.m_health.forced_state:
            self.m_health = HookChannelHealthMonitor(
                startup_grace_seconds=self.m_health.startup_grace_seconds,
                staleness_threshold_seconds=self.m_health.staleness_threshold_seconds,
                forced_state=forced_state,
                since_utc=_status_timestamp(status),
            )
        elif (
            explicit_state in {"unavailable", "installing"} and self.m_health.state != "unavailable"
        ):
            self.m_health = HookChannelHealthMonitor(
                startup_grace_seconds=self.m_health.startup_grace_seconds,
                staleness_threshold_seconds=self.m_health.staleness_threshold_seconds,
                since_utc=_status_timestamp(status),
                initial_detail=_install_detail(status),
            )
        if self.m_health.forced_state is not None:
            health = self.m_health.observe(
                now_monotonic=now_monotonic,
                now_utc=now_utc,
                events_this_cycle=0,
                tui_changed=tui_changed,
                collector_status=collector_status,
            )
            return HookChannelCycle(observations=(), health=health)
        if explicit_state in {"unavailable", "installing"}:
            health = self.m_health.observe(
                now_monotonic=now_monotonic,
                now_utc=now_utc,
                events_this_cycle=0,
                tui_changed=tui_changed,
                collector_status=None,
            )
            return HookChannelCycle(observations=(), health=health)

        batch = self.m_reader.read_new()
        health = self.m_health.observe(
            now_monotonic=now_monotonic,
            now_utc=now_utc,
            events_this_cycle=len(batch.observations),
            tui_changed=tui_changed,
            collector_status=collector_status,
            read_error=batch.read_error,
        )
        return HookChannelCycle(
            observations=batch.observations,
            health=health,
            current_generation=batch.current_generation,
            read_error=batch.read_error,
            retried_partial_line=batch.retried_partial_line,
            skipped_blank_lines=batch.skipped_blank_lines,
            skipped_garbage_lines=batch.skipped_garbage_lines,
            skipped_invalid_lines=batch.skipped_invalid_lines,
            skipped_oversized_lines=batch.skipped_oversized_lines,
            dropped_old_generation_lines=batch.dropped_old_generation_lines,
        )


def read_channel_status(channel_path: Path | str) -> dict[str, Any] | None:
    """Read one ``channel.json`` document, returning ``None`` when unusable."""

    try:
        raw = Path(channel_path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _parse_chunk(data: bytes) -> HookReadChunk:
    """Parse one block of newline-terminated store lines."""

    envelopes: list[HookEventEnvelope] = []
    blank_lines = 0
    garbage_lines = 0
    invalid_lines = 0
    oversized_lines = 0
    for chunk in data.split(b"\n")[:-1]:
        if not chunk.strip():
            blank_lines += 1
            continue
        if len(chunk) > MAX_ENVELOPE_LINE_BYTES:
            oversized_lines += 1
            continue
        try:
            text = chunk.decode("utf-8").rstrip("\r")
        except UnicodeDecodeError:
            garbage_lines += 1
            continue
        parsed = parse_envelope_line(text)
        if parsed.ok and parsed.envelope is not None:
            envelopes.append(parsed.envelope)
        elif parsed.outcome == "oversized":
            oversized_lines += 1
        elif parsed.outcome == "invalid_shape":
            invalid_lines += 1
        elif parsed.outcome == "blank":
            blank_lines += 1
        else:
            garbage_lines += 1
    return HookReadChunk(
        envelopes=tuple(envelopes),
        skipped_blank_lines=blank_lines,
        skipped_garbage_lines=garbage_lines,
        skipped_invalid_lines=invalid_lines,
        skipped_oversized_lines=oversized_lines,
    )


def _current_generation_observations(
    *,
    envelopes: tuple[HookEventEnvelope, ...],
    generation: int | None,
) -> tuple[tuple[HookObservation, ...], int]:
    """Normalize current-generation envelopes and count dropped older rows."""

    if generation is None:
        return (), 0
    observations: list[HookObservation] = []
    dropped = 0
    for envelope in envelopes:
        if envelope.channel_generation < generation:
            dropped += 1
            continue
        observations.append(normalize_envelope(envelope))
    return tuple(observations), dropped


def _explicit_channel_state(status: dict[str, Any] | None) -> HookChannelState | None:
    """Return the explicit channel state from install or health metadata."""

    if status is None:
        return None
    for key in ("channel_state", "state", "health_state"):
        value = status.get(key)
        if value == "installing":
            return "unavailable"
        candidate = coerce_channel_state(value)
        if candidate is not None:
            return candidate
    if status.get("status") == "installing":
        return "unavailable"
    return coerce_channel_state(status.get("status"))


def _forced_health_state(status: dict[str, Any] | None) -> HookChannelState | None:
    """Return a forced terminal health state from channel metadata."""

    explicit_state = _explicit_channel_state(status)
    if explicit_state in _FORCED_HEALTH_STATES:
        return explicit_state
    return None


def _collector_status(status: dict[str, Any] | None) -> str | None:
    """Return the collector status label from channel metadata."""

    if status is None:
        return None
    if _explicit_channel_state(status) in {"unavailable", "installing"}:
        return None
    value = status.get("status")
    return value if isinstance(value, str) else None


def _install_detail(status: dict[str, Any] | None) -> str | None:
    """Return the bounded install-time detail reason when one is published."""

    if status is None:
        return None
    install = status.get("install")
    if not isinstance(install, dict):
        return None
    detail = install.get("detail")
    if not isinstance(detail, str) or not detail.strip():
        return None
    return detail


def _status_generation(status: dict[str, Any] | None) -> int | None:
    """Return one integer generation stamp from a status document."""

    if status is None:
        return None
    value = status.get("generation")
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _collector_record_stopped(
    collector_path: Path,
    *,
    channel_generation: int | None,
) -> bool:
    """Return whether the collector liveness record reports a stopped collector.

    A record from a different channel generation is ignored so a stale record
    from a previous launch cannot stop the current generation.
    """

    record = read_channel_status(collector_path)
    if record is None or record.get("status") != "stopped":
        return False
    record_generation = _status_generation(record)
    if (
        record_generation is not None
        and channel_generation is not None
        and record_generation != channel_generation
    ):
        return False
    return True


def _status_timestamp(status: dict[str, Any] | None) -> str | None:
    """Return a status timestamp for initial health bookkeeping."""

    if status is None:
        return None
    for key in ("started_at_utc", "updated_at_utc"):
        value = status.get(key)
        if isinstance(value, str) and value:
            return value
    return None
