"""Append-only per-session store for raw Claude hook envelopes.

The store is the neutral fan-out primitive for the observation channel. One
writer appends one JSON envelope per line under an exclusive file lock and
maintains a secret-free ``channel.json`` status document with an atomic
write-tmp-then-rename update.
"""

from __future__ import annotations

import fcntl
import json
import os
import threading
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, cast

from houmao.hook_observation.models import (
    EnvelopeParseResult,
    HookDeliveryVia,
    HookEventEnvelope,
    HookStoreStatus,
    StoreReadResult,
)


HOOK_OBSERVATION_DIRNAME = "hook-observation"
CLAUDE_ADAPTER_DIRNAME = "claude"
EVENTS_FILENAME = "events.ndjson"
CHANNEL_FILENAME = "channel.json"
CHANNEL_TMP_FILENAME = "channel.json.tmp"
MAX_ENVELOPE_LINE_BYTES = 2 << 20
PRIVATE_DIR_MODE = 0o700
PRIVATE_FILE_MODE = 0o600
GENERATION_BOUNDARY_EVENT_NAMES = frozenset({"GenerationBoundary"})
_VIA_VALUES = frozenset({"http", "command", "command_fallback"})


def _utc_now_iso() -> str:
    """Return the current UTC time in ISO-8601 form."""

    return datetime.now(UTC).isoformat(timespec="seconds")


class HookObservationStore:
    """Single-writer append-only store for one session's hook envelopes."""

    def __init__(self, session_root: Path | str, *, generation: int = 1) -> None:
        """Open or create the session store for one channel generation.

        Parameters
        ----------
        session_root:
            Session root directory that owns the hook subtree.
        generation:
            Requested channel generation. A generation newer than every
            existing record appends a generation boundary; the newest existing
            generation is resumed; an older request is rejected.

        Raises
        ------
        ValueError
            If ``generation`` is not positive or is older than the store.
        """

        if generation < 1:
            raise ValueError("generation must be positive")
        self.m_session_root: Path = Path(session_root)
        self.m_observation_root: Path = self.m_session_root / HOOK_OBSERVATION_DIRNAME
        self.m_directory: Path = self.m_observation_root / CLAUDE_ADAPTER_DIRNAME
        self.m_events_path: Path = self.m_directory / EVENTS_FILENAME
        self.m_channel_path: Path = self.m_directory / CHANNEL_FILENAME
        self.m_write_lock: threading.Lock = threading.Lock()
        self.m_status: HookStoreStatus = "running"
        self.m_port: int | None = None
        self.m_started_at_utc: str = _utc_now_iso()
        self.m_updated_at_utc: str = self.m_started_at_utc
        self.m_stopped_at_utc: str | None = None
        _ensure_private_dir(self.m_observation_root)
        _ensure_private_dir(self.m_directory)
        if self.m_events_path.is_file():
            os.chmod(self.m_events_path, PRIVATE_FILE_MODE)

        existing = read_store(self.m_events_path)
        existing_generations = [item.channel_generation for item in existing.envelopes]
        newest_generation = max(existing_generations, default=None)
        if newest_generation is not None and generation < newest_generation:
            raise ValueError(
                f"generation {generation} is older than store generation {newest_generation}"
            )
        self.m_generation: int = (
            generation if newest_generation is None else max(newest_generation, generation)
        )
        self.m_next_sequence: int = (
            max(
                (item.sequence for item in existing.envelopes if item.sequence is not None),
                default=0,
            )
            + 1
        )
        self.m_accepted_events: int = sum(
            1 for item in existing.envelopes if not item.is_generation_boundary
        )
        self.m_generation_boundaries: int = sum(
            1 for item in existing.envelopes if item.is_generation_boundary
        )
        self.m_skipped_lines: int = existing.skipped_lines
        self.m_events_by_name: Counter[str] = Counter()
        for item in existing.envelopes:
            if item.is_generation_boundary:
                continue
            self.m_events_by_name[item.event_name or "unknown"] += 1
        if newest_generation is None or generation > newest_generation:
            self._append_generation_boundary()
        self.write_channel_status()

    @property
    def session_root(self) -> Path:
        """Return the session root that owns this store."""

        return self.m_session_root

    @property
    def directory(self) -> Path:
        """Return the hook observation directory."""

        return self.m_directory

    @property
    def events_path(self) -> Path:
        """Return the append-only events file path."""

        return self.m_events_path

    @property
    def channel_path(self) -> Path:
        """Return the secret-free status file path."""

        return self.m_channel_path

    @property
    def generation(self) -> int:
        """Return the current channel generation."""

        return self.m_generation

    @property
    def next_sequence(self) -> int:
        """Return the next sequence number that will be assigned."""

        return self.m_next_sequence

    @property
    def status(self) -> HookStoreStatus:
        """Return the current collector status label."""

        return self.m_status

    def begin_generation(self, generation: int) -> HookEventEnvelope | None:
        """Open a new generation and append its boundary record.

        Parameters
        ----------
        generation:
            New generation number. Equal generations are a no-op resume;
            older generations raise.

        Returns
        -------
        HookEventEnvelope | None
            The appended boundary envelope, or ``None`` for an equal resume.

        Raises
        ------
        ValueError
            If ``generation`` is not positive or is older than the store.
        """

        if generation < 1:
            raise ValueError("generation must be positive")
        with self.m_write_lock:
            if generation < self.m_generation:
                raise ValueError(
                    f"generation {generation} is older than current {self.m_generation}"
                )
            if generation == self.m_generation:
                return None
            self.m_generation = generation
            envelope = self._append_generation_boundary()
        self.write_channel_status()
        return envelope

    def append_event(
        self,
        provider_event: dict[str, Any],
        *,
        via: HookDeliveryVia = "http",
        received_at_utc: str | None = None,
    ) -> HookEventEnvelope:
        """Append one provider event and assign its sequence.

        Parameters
        ----------
        provider_event:
            Raw provider payload object.
        via:
            Delivery path that produced the event.
        received_at_utc:
            Optional receive-time override for deterministic tests.

        Returns
        -------
        HookEventEnvelope
            The appended envelope.

        Raises
        ------
        TypeError
            If ``provider_event`` is not a JSON object.
        """

        if not isinstance(provider_event, dict):
            raise TypeError("provider_event must be a dict")
        with self.m_write_lock:
            envelope = HookEventEnvelope(
                sequence=self.m_next_sequence,
                received_at_utc=received_at_utc or _utc_now_iso(),
                channel_generation=self.m_generation,
                via=via,
                provider_event=provider_event,
            )
            self._append_envelope(envelope)
            self.m_next_sequence += 1
            self.m_accepted_events += 1
            self.m_events_by_name[envelope.event_name or "unknown"] += 1
        self.write_channel_status()
        return envelope

    def mark_running(self, *, port: int | None = None) -> None:
        """Mark the collector running and publish an optional port."""

        with self.m_write_lock:
            self.m_status = "running"
            self.m_port = port
            self.m_stopped_at_utc = None
        self.write_channel_status()

    def mark_stopped(self) -> None:
        """Mark the collector stopped."""

        with self.m_write_lock:
            self.m_status = "stopped"
            self.m_stopped_at_utc = _utc_now_iso()
        self.write_channel_status()

    def channel_status(self) -> dict[str, Any]:
        """Return the secret-free status document."""

        return {
            "schema_version": 1,
            "status": self.m_status,
            "generation": self.m_generation,
            "pid": os.getpid(),
            "port": self.m_port,
            "started_at_utc": self.m_started_at_utc,
            "updated_at_utc": self.m_updated_at_utc,
            "stopped_at_utc": self.m_stopped_at_utc,
            "last_sequence": self.m_next_sequence - 1,
            "counts": {
                "accepted": self.m_accepted_events,
                "generation_boundaries": self.m_generation_boundaries,
                "skipped_lines": self.m_skipped_lines,
            },
            "events_by_name": dict(sorted(self.m_events_by_name.items())),
        }

    def write_channel_status(self, *, extra: Mapping[str, Any] | None = None) -> None:
        """Atomically replace ``channel.json`` with the current status.

        Parameters
        ----------
        extra:
            Optional caller-owned status fields. Fields named ``token``,
            ``raw_payload``, ``prompt``, ``tool_input``, or ``tool_response``
            are rejected to keep the status document secret-free.
        """

        with self.m_write_lock:
            self.m_updated_at_utc = _utc_now_iso()
            payload = self.channel_status()
            if extra is not None:
                payload.update(_validated_extra_status(extra))
            tmp_path = self.m_directory / CHANNEL_TMP_FILENAME
            descriptor = os.open(
                tmp_path,
                os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
                PRIVATE_FILE_MODE,
            )
            try:
                with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                    json.dump(payload, handle, indent=2, sort_keys=True)
                    handle.write("\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                os.chmod(tmp_path, PRIVATE_FILE_MODE)
                os.replace(tmp_path, self.m_channel_path)
            except BaseException:
                try:
                    tmp_path.unlink()
                except FileNotFoundError:
                    pass
                raise

    def _append_generation_boundary(self) -> HookEventEnvelope:
        """Append the boundary record for the current generation."""

        envelope = HookEventEnvelope(
            sequence=None,
            received_at_utc=_utc_now_iso(),
            channel_generation=self.m_generation,
            via="http",
            provider_event={},
            record_type="generation_boundary",
        )
        self._append_envelope(envelope)
        self.m_generation_boundaries += 1
        return envelope

    def _append_envelope(self, envelope: HookEventEnvelope) -> None:
        """Append one serialized envelope under the inter-process lock."""

        line = json.dumps(envelope.to_payload(), sort_keys=True) + "\n"
        descriptor = os.open(
            self.m_events_path,
            os.O_WRONLY | os.O_CREAT | os.O_APPEND,
            PRIVATE_FILE_MODE,
        )
        try:
            os.chmod(self.m_events_path, PRIVATE_FILE_MODE)
            with os.fdopen(descriptor, "a", encoding="utf-8") as handle:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                try:
                    handle.write(self._trailing_newline_repair())
                    handle.write(line)
                    handle.flush()
                    os.fsync(handle.fileno())
                finally:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        except BaseException:
            try:
                os.close(descriptor)
            except OSError:
                pass
            raise

    def _trailing_newline_repair(self) -> str:
        """Return a newline when a crashed writer left an unterminated last line."""

        try:
            with self.m_events_path.open("rb") as handle:
                handle.seek(0, os.SEEK_END)
                if handle.tell() == 0:
                    return ""
                handle.seek(-1, os.SEEK_END)
                return "" if handle.read(1) == b"\n" else "\n"
        except OSError:
            return ""


def read_store(events_path: Path | str) -> StoreReadResult:
    """Read one append-only store file as a tolerant snapshot.

    Blank, garbage, oversized, invalid-shape, and unterminated final lines are
    counted and skipped. Any parsed envelope, including generation boundary
    records, is returned in file order.

    Parameters
    ----------
    events_path:
        Path to ``events.ndjson``.

    Returns
    -------
    StoreReadResult
        Parsed envelopes plus skip counters.
    """

    path = Path(events_path)
    if not path.is_file():
        return StoreReadResult(envelopes=())
    data = path.read_bytes()
    if not data:
        return StoreReadResult(envelopes=())
    chunks = data.split(b"\n")
    incomplete_lines = 0
    if chunks[-1]:
        incomplete_lines = 1
        complete_chunks = chunks[:-1]
    else:
        complete_chunks = chunks[:-1]
    envelopes: list[HookEventEnvelope] = []
    blank_lines = 0
    garbage_lines = 0
    oversized_lines = 0
    invalid_lines = 0
    for chunk in complete_chunks:
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
        if parsed.outcome == "ok" and parsed.envelope is not None:
            envelopes.append(parsed.envelope)
        elif parsed.outcome == "oversized":
            oversized_lines += 1
        elif parsed.outcome == "invalid_shape":
            invalid_lines += 1
        elif parsed.outcome == "garbage":
            garbage_lines += 1
        else:
            blank_lines += 1
    return StoreReadResult(
        envelopes=tuple(envelopes),
        skipped_blank_lines=blank_lines,
        skipped_garbage_lines=garbage_lines,
        skipped_oversized_lines=oversized_lines,
        skipped_invalid_lines=invalid_lines,
        skipped_incomplete_lines=incomplete_lines,
    )


def parse_envelope_line(line: str) -> EnvelopeParseResult:
    """Parse one raw store line into an envelope or a skip outcome."""

    text = line.strip()
    if not text:
        return EnvelopeParseResult(envelope=None, outcome="blank")
    if len(line.encode("utf-8")) > MAX_ENVELOPE_LINE_BYTES:
        return EnvelopeParseResult(envelope=None, outcome="oversized")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return EnvelopeParseResult(envelope=None, outcome="garbage")
    if not isinstance(payload, dict):
        return EnvelopeParseResult(envelope=None, outcome="invalid_shape")
    envelope = _envelope_from_payload(payload)
    if envelope is None:
        return EnvelopeParseResult(envelope=None, outcome="invalid_shape")
    return EnvelopeParseResult(envelope=envelope, outcome="ok")


def _envelope_from_payload(payload: dict[str, Any]) -> HookEventEnvelope | None:
    """Build one envelope from a decoded JSON object."""

    generation = payload.get("channel_generation")
    if isinstance(generation, bool) or not isinstance(generation, int):
        return None
    received_at_utc_value = payload.get("received_at_utc")
    if not isinstance(received_at_utc_value, str):
        received_at_utc_value = payload.get("recorded_at_utc")
    received_at_utc = received_at_utc_value if isinstance(received_at_utc_value, str) else ""
    record_type_value = payload.get("record_type")
    if record_type_value is not None and not isinstance(record_type_value, str):
        return None
    if isinstance(record_type_value, str) and record_type_value not in {
        "event",
        "generation_boundary",
    }:
        return None
    provider_value = payload.get("provider_event")
    provider_event = provider_value if isinstance(provider_value, dict) else None
    is_boundary = record_type_value == "generation_boundary"
    record_value = payload.get("record")
    if isinstance(record_value, str) and record_value in {"generation_boundary", "boundary"}:
        is_boundary = True
    if provider_event is not None:
        boundary_name = provider_event.get("hook_event_name")
        if boundary_name in GENERATION_BOUNDARY_EVENT_NAMES:
            is_boundary = True
    sequence = _optional_sequence(payload.get("sequence"))
    via = _normalized_via(payload.get("via"))
    if is_boundary:
        return HookEventEnvelope(
            received_at_utc=received_at_utc,
            channel_generation=generation,
            via=via,
            provider_event={},
            sequence=sequence,
            record_type="generation_boundary",
        )
    if provider_event is None:
        return None
    return HookEventEnvelope(
        received_at_utc=received_at_utc,
        channel_generation=generation,
        via=via,
        provider_event=provider_event,
        sequence=sequence,
        record_type="event",
    )


def _optional_sequence(value: object) -> int | None:
    """Return one optional integer sequence value."""

    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _normalized_via(value: object) -> HookDeliveryVia:
    """Return one known delivery path label."""

    if isinstance(value, str) and value in _VIA_VALUES:
        return cast(HookDeliveryVia, value)
    return "unknown"


def _validated_extra_status(extra: Mapping[str, Any]) -> dict[str, Any]:
    """Validate caller-owned status fields against the secret-free contract."""

    forbidden = {"token", "raw_payload", "prompt", "tool_input", "tool_response"}
    for key in extra:
        if key.lower() in forbidden:
            raise ValueError(f"channel status field {key!r} is not secret-free")
    return dict(extra)


def _ensure_private_dir(path: Path) -> None:
    """Create a directory when needed and force owner-only permissions."""

    path.mkdir(parents=True, exist_ok=True, mode=PRIVATE_DIR_MODE)
    os.chmod(path, PRIVATE_DIR_MODE)
