"""Opt-in structured diagnostic logging for the live gateway."""

from __future__ import annotations

import json
import math
import threading
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from houmao.agents.realm_controller.gateway_models import (
    GatewayDiagnosticLoggingConfigV1,
    GatewayJsonValue,
)

GatewayDiagnosticLevel = Literal["info", "warning", "error"]

_SENSITIVE_FIELD_NAMES = frozenset(
    {
        "attachment",
        "attachment_contents",
        "attachments",
        "authorization",
        "bearer",
        "body",
        "body_content",
        "cookie",
        "cookies",
        "credential",
        "credential_file",
        "credential_ref",
        "env",
        "environment",
        "password",
        "prompt",
        "raw_body",
        "raw_prompt",
        "refresh_token",
        "secret",
        "token",
    }
)
_SENSITIVE_FIELD_SUFFIXES = (
    "_authorization",
    "_body",
    "_cookie",
    "_credential",
    "_env",
    "_password",
    "_prompt",
    "_secret",
    "_token",
)
_VOLATILE_DEDUP_FIELDS = frozenset(
    {
        "accepted_at_utc",
        "duration_ms",
        "finished_at_utc",
        "last_timestamp_utc",
        "message_id",
        "message_ref",
        "request_id",
        "timestamp_utc",
    }
)


class GatewayDiagnosticLogger:
    """Write bounded structured gateway diagnostics when explicitly enabled."""

    def __init__(self, *, config: GatewayDiagnosticLoggingConfigV1, log_path: Path) -> None:
        """Initialize the logger with one resolved config and active log path."""

        self.m_config: GatewayDiagnosticLoggingConfigV1 = config
        self.m_log_path: Path = log_path
        self.m_lock = threading.RLock()
        self.m_pending_key: str | None = None
        self.m_pending_level: GatewayDiagnosticLevel | None = None
        self.m_pending_event: str | None = None
        self.m_pending_count: int = 0
        self.m_pending_first_timestamp_utc: str | None = None
        self.m_pending_last_timestamp_utc: str | None = None

    @property
    def enabled(self) -> bool:
        """Return whether diagnostic logging is enabled."""

        return self.m_config.enabled

    def emit(
        self,
        *,
        level: GatewayDiagnosticLevel,
        event: str,
        fields: Mapping[str, object] | None = None,
        dedup_key: str | None = None,
    ) -> None:
        """Write one diagnostic entry, suppressing logger failures."""

        if not self.enabled:
            return
        try:
            with self.m_lock:
                self._emit_locked(
                    level=level,
                    event=event,
                    fields=fields or {},
                    dedup_key=dedup_key,
                )
        except Exception:
            return

    def flush(self) -> None:
        """Flush any pending deduplication summary, suppressing logger failures."""

        if not self.enabled:
            return
        try:
            with self.m_lock:
                self._flush_pending_locked()
        except Exception:
            return

    def close(self) -> None:
        """Close the diagnostic logger."""

        self.flush()

    def _emit_locked(
        self,
        *,
        level: GatewayDiagnosticLevel,
        event: str,
        fields: Mapping[str, object],
        dedup_key: str | None,
    ) -> None:
        """Write one diagnostic entry while holding the logger lock."""

        safe_fields = _safe_fields(fields)
        timestamp_utc = _now_utc_iso()
        entry = _build_entry(
            timestamp_utc=timestamp_utc,
            level=level,
            event=event,
            fields=safe_fields,
        )
        if level in {"warning", "error"}:
            semantic_key = dedup_key or _default_dedup_key(
                level=level,
                event=event,
                fields=safe_fields,
            )
            if self.m_pending_key == semantic_key:
                self.m_pending_count += 1
                self.m_pending_last_timestamp_utc = timestamp_utc
                return
            self._flush_pending_locked()
            entry["dedup_key"] = semantic_key
            self._write_entry_locked(entry)
            self.m_pending_key = semantic_key
            self.m_pending_level = level
            self.m_pending_event = event
            self.m_pending_count = 0
            self.m_pending_first_timestamp_utc = timestamp_utc
            self.m_pending_last_timestamp_utc = timestamp_utc
            return

        self._flush_pending_locked()
        self._write_entry_locked(entry)

    def _flush_pending_locked(self) -> None:
        """Flush the pending duplicate summary while holding the logger lock."""

        if self.m_pending_key is None:
            return
        pending_key = self.m_pending_key
        pending_level = self.m_pending_level or "warning"
        pending_event = self.m_pending_event
        suppressed_count = self.m_pending_count
        first_timestamp_utc = self.m_pending_first_timestamp_utc
        last_timestamp_utc = self.m_pending_last_timestamp_utc
        self._clear_pending_locked()
        if suppressed_count <= 0:
            return
        self._write_entry_locked(
            _build_entry(
                timestamp_utc=_now_utc_iso(),
                level=pending_level,
                event="diagnostic.dedup_summary",
                fields={
                    "dedup_key": pending_key,
                    "first_event": pending_event,
                    "first_timestamp_utc": first_timestamp_utc,
                    "last_timestamp_utc": last_timestamp_utc,
                    "suppressed_count": suppressed_count,
                },
            )
        )

    def _clear_pending_locked(self) -> None:
        """Clear the active duplicate run while holding the logger lock."""

        self.m_pending_key = None
        self.m_pending_level = None
        self.m_pending_event = None
        self.m_pending_count = 0
        self.m_pending_first_timestamp_utc = None
        self.m_pending_last_timestamp_utc = None

    def _write_entry_locked(self, entry: dict[str, GatewayJsonValue]) -> None:
        """Append one encoded line, rotating the active log first if needed."""

        line = json.dumps(entry, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        encoded_length = len(line.encode("utf-8")) + 1
        self._rotate_if_needed_locked(incoming_bytes=encoded_length)
        self.m_log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.m_log_path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def _rotate_if_needed_locked(self, *, incoming_bytes: int) -> None:
        """Rotate the active diagnostic log when appending would exceed max_bytes."""

        if not self.m_log_path.exists():
            return
        if self.m_log_path.stat().st_size + incoming_bytes <= self.m_config.max_bytes:
            return
        if self.m_config.backup_count <= 0:
            self.m_log_path.unlink(missing_ok=True)
            return

        self.m_log_path.parent.mkdir(parents=True, exist_ok=True)
        oldest = _rotated_path(self.m_log_path, self.m_config.backup_count)
        oldest.unlink(missing_ok=True)
        for index in range(self.m_config.backup_count - 1, 0, -1):
            source = _rotated_path(self.m_log_path, index)
            destination = _rotated_path(self.m_log_path, index + 1)
            if source.exists():
                source.replace(destination)
        self.m_log_path.replace(_rotated_path(self.m_log_path, 1))


def _build_entry(
    *,
    timestamp_utc: str,
    level: GatewayDiagnosticLevel,
    event: str,
    fields: Mapping[str, GatewayJsonValue],
) -> dict[str, GatewayJsonValue]:
    """Build one diagnostic entry from explicit safe fields."""

    entry: dict[str, GatewayJsonValue] = {
        "schema_version": 1,
        "timestamp_utc": timestamp_utc,
        "level": level,
        "event": event,
    }
    entry.update(fields)
    return entry


def _safe_fields(fields: Mapping[str, object]) -> dict[str, GatewayJsonValue]:
    """Return a JSON-safe diagnostic field mapping without sensitive keys."""

    safe: dict[str, GatewayJsonValue] = {}
    for key, value in fields.items():
        normalized_key = str(key)
        if _is_sensitive_field(normalized_key):
            continue
        safe[normalized_key] = _safe_value(value)
    return safe


def _safe_value(value: object) -> GatewayJsonValue:
    """Convert one explicitly selected diagnostic value to a JSON-safe value."""

    if value is None or isinstance(value, str | int | bool):
        return value
    if isinstance(value, float):
        if math.isfinite(value):
            return value
        return str(value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return _safe_fields({str(key): item for key, item in value.items()})
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return [_safe_value(item) for item in value]
    return str(value)


def _is_sensitive_field(key: str) -> bool:
    """Return whether a diagnostic field name is sensitive by construction."""

    normalized = key.lower().replace("-", "_")
    return normalized in _SENSITIVE_FIELD_NAMES or normalized.endswith(_SENSITIVE_FIELD_SUFFIXES)


def _default_dedup_key(
    *,
    level: GatewayDiagnosticLevel,
    event: str,
    fields: Mapping[str, GatewayJsonValue],
) -> str:
    """Build a semantic deduplication key from non-volatile fields."""

    stable_fields = {
        key: value for key, value in fields.items() if key.lower() not in _VOLATILE_DEDUP_FIELDS
    }
    return json.dumps(
        {"event": event, "fields": stable_fields, "level": level},
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )


def _rotated_path(path: Path, index: int) -> Path:
    """Return the path for one diagnostic backup index."""

    return path.with_name(f"{path.name}.{index}")


def _now_utc_iso() -> str:
    """Return the current UTC timestamp in gateway JSON format."""

    return datetime.now(UTC).isoformat()
