"""Canonical headless event parsing, storage, and rendering helpers.

This module separates provider-owned headless JSON protocols from Houmao's
canonical event, artifact, and rendering contracts. Managed headless runtime
execution writes raw provider stdout/stderr artifacts unchanged, then derives a
second canonical JSONL artifact for later replay and inspection.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any, Literal

from houmao.agents.realm_controller.backends.dsh_diagnostics import sanitize_dsh_diagnostic
from houmao.agents.realm_controller.models import SessionEvent

HeadlessDisplayStyle = Literal["plain", "json", "fancy"]
HeadlessDisplayDetail = Literal["concise", "detail"]
HeadlessProvider = Literal["claude", "codex", "kimi", "dsh"]

CANONICAL_HEADLESS_EVENTS_ARTIFACT = "canonical-events.jsonl"
"""Artifact name for canonical normalized headless events."""

_VALID_DISPLAY_STYLES: frozenset[str] = frozenset({"plain", "json", "fancy"})
_VALID_DISPLAY_DETAILS: frozenset[str] = frozenset({"concise", "detail"})
_DSH_CLI_RECORD_TYPES = frozenset(
    {"session", "status", "text", "thinking", "tool_call", "tool_result", "final", "error"}
)
_DSH_CLI_STATUS_PHASES = frozenset({"turn_start", "step_start", "step_end", "turn_end"})
_DSH_CLI_REASONS = frozenset(
    {"completed", "aborted", "blocked", "error", "max-tokens", "interrupted", "forked"}
)


@dataclass(frozen=True)
class CanonicalHeadlessEvent:
    """One provider-normalized semantic headless event.

    Parameters
    ----------
    kind:
        Canonical semantic event category.
    message:
        Short semantic summary for human and machine consumers.
    turn_index:
        Managed headless turn index.
    provider:
        Upstream provider identity.
    provider_event_type:
        Upstream provider event discriminator for provenance.
    timestamp_utc:
        Event timestamp in UTC ISO-8601 format.
    session_id:
        Canonical session or thread identity when known.
    data:
        Provider-normalized semantic event content.
    raw_payload:
        Original provider payload or raw diagnostic surface.
    """

    kind: str
    message: str
    turn_index: int
    provider: HeadlessProvider
    provider_event_type: str
    timestamp_utc: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds")
    )
    session_id: str | None = None
    data: dict[str, Any] | None = None
    raw_payload: dict[str, Any] | None = None

    def to_artifact_record(self) -> dict[str, Any]:
        """Return one durable JSON-compatible artifact record.

        Returns
        -------
        dict[str, Any]
            Canonical artifact payload for JSONL persistence.
        """

        return {
            "kind": self.kind,
            "message": self.message,
            "turn_index": self.turn_index,
            "provider": self.provider,
            "provider_event_type": self.provider_event_type,
            "timestamp_utc": self.timestamp_utc,
            "session_id": self.session_id,
            "data": dict(self.data) if self.data is not None else None,
            "raw_payload": dict(self.raw_payload) if self.raw_payload is not None else None,
        }

    def to_public_payload(self, *, detail: HeadlessDisplayDetail) -> dict[str, Any]:
        """Return one public payload view for inspection surfaces.

        Parameters
        ----------
        detail:
            Requested projection detail.

        Returns
        -------
        dict[str, Any]
            Public event payload with concise or detailed fields.
        """

        payload: dict[str, Any] = {
            "provider": self.provider,
            "session_id": self.session_id,
            "data": dict(self.data) if self.data is not None else None,
        }
        if detail == "detail":
            payload["provider_event_type"] = self.provider_event_type
            payload["raw"] = dict(self.raw_payload) if self.raw_payload is not None else None
        return payload

    @classmethod
    def from_artifact_record(cls, payload: Mapping[str, Any]) -> CanonicalHeadlessEvent:
        """Rebuild one canonical event from a stored artifact record.

        Parameters
        ----------
        payload:
            Stored JSON object.

        Returns
        -------
        CanonicalHeadlessEvent
            Reconstructed canonical event.
        """

        provider_value = str(payload.get("provider", "claude")).strip().lower()
        provider: HeadlessProvider = _coerce_provider(provider_value)
        return cls(
            kind=str(payload.get("kind", "diagnostic")),
            message=str(payload.get("message", "")),
            turn_index=int(payload.get("turn_index", 0)),
            provider=provider,
            provider_event_type=str(payload.get("provider_event_type", "unknown")),
            timestamp_utc=str(payload.get("timestamp_utc", ""))
            or datetime.now(UTC).isoformat(timespec="seconds"),
            session_id=_optional_text(payload.get("session_id")),
            data=_optional_mapping(payload.get("data")),
            raw_payload=_optional_mapping(payload.get("raw_payload")),
        )

    @classmethod
    def from_public_event(cls, payload: Mapping[str, Any]) -> CanonicalHeadlessEvent:
        """Rebuild one canonical event from a public event projection.

        Parameters
        ----------
        payload:
            Public event projection such as one API or CLI event row.

        Returns
        -------
        CanonicalHeadlessEvent
            Reconstructed canonical event.
        """

        event_payload = _optional_mapping(payload.get("payload")) or {}
        provider_value = str(event_payload.get("provider", "claude")).strip().lower()
        provider: HeadlessProvider = _coerce_provider(provider_value)
        provider_event_type = str(event_payload.get("provider_event_type", payload.get("kind", "")))
        raw_payload = _optional_mapping(event_payload.get("raw"))
        return cls(
            kind=str(payload.get("kind", "diagnostic")),
            message=str(payload.get("message", "")),
            turn_index=int(payload.get("turn_index", 0)),
            provider=provider,
            provider_event_type=provider_event_type,
            timestamp_utc=str(payload.get("timestamp_utc", ""))
            or datetime.now(UTC).isoformat(timespec="seconds"),
            session_id=_optional_text(event_payload.get("session_id")),
            data=_optional_mapping(event_payload.get("data")),
            raw_payload=raw_payload,
        )


class CanonicalHeadlessEventParser:
    """Incremental provider-aware canonical event parser."""

    def __init__(
        self,
        *,
        provider: HeadlessProvider,
        turn_index: int,
        output_format: str = "stream-json",
        diagnostic_secrets: tuple[str, ...] | None = None,
    ) -> None:
        """Initialize one parser state.

        Parameters
        ----------
        provider:
            Upstream provider identity.
        turn_index:
            Managed turn index.
        output_format:
            Protocol selected by the backend before reading output.
        diagnostic_secrets:
            Credentials to redact in native diagnostics. None omits diagnostic contents.
        """

        self.m_provider: HeadlessProvider = provider
        self.m_turn_index: int = turn_index
        self.m_session_id: str | None = None
        self.m_seen_action_requests: set[str] = set()
        self.m_dsh_cli: bool = provider == "dsh" and output_format == "dsh-cli"
        self.m_diagnostic_secrets: tuple[str, ...] | None = diagnostic_secrets

    @property
    def session_id(self) -> str | None:
        """Return the latest canonical session identity."""

        return self.m_session_id

    def consume_stream_line(self, line: str) -> list[CanonicalHeadlessEvent]:
        """Parse one streamed JSONL line.

        Parameters
        ----------
        line:
            One raw provider stdout line without trailing newline.

        Returns
        -------
        list[CanonicalHeadlessEvent]
            Zero or more canonical semantic events.
        """

        try:
            payload = json.loads(line)
        except (json.JSONDecodeError, RecursionError):
            if self.m_provider == "dsh":
                return [self._dsh_cli_invalid_record("raw_text")]
            return [self._diagnostic_event(text=line, provider_event_type="raw_text")]
        if not isinstance(payload, dict):
            if self.m_provider == "dsh":
                return [self._dsh_cli_invalid_record("non_mapping")]
            return [
                self._diagnostic_event(
                    text=str(payload),
                    provider_event_type="non_mapping",
                    raw_payload={"value": payload},
                )
            ]
        return self.consume_json_object(payload)

    def consume_json_object(self, payload: Mapping[str, Any]) -> list[CanonicalHeadlessEvent]:
        """Parse one already-decoded provider JSON object.

        Parameters
        ----------
        payload:
            One provider JSON mapping.

        Returns
        -------
        list[CanonicalHeadlessEvent]
            Canonical semantic events derived from the mapping.
        """

        if self.m_provider == "dsh" and (
            self.m_dsh_cli or _optional_text(payload.get("type")) in _DSH_CLI_RECORD_TYPES
        ):
            self.m_dsh_cli = True
            return [self._consume_dsh_cli_payload(payload)]

        candidate_session_id = _extract_session_id_from_payload(payload)
        if candidate_session_id is not None and self.m_session_id is None:
            self.m_session_id = candidate_session_id

        if self.m_provider == "claude":
            return self._consume_claude_payload(payload)
        if self.m_provider == "codex":
            return self._consume_codex_payload(payload)
        if self.m_provider == "dsh":
            return self._consume_dsh_payload(payload)
        return self._consume_kimi_payload(payload)

    def _dsh_cli_invalid_record(self, event_type: str) -> CanonicalHeadlessEvent:
        """Keep malformed DSH records out of public diagnostics and session state."""

        return self._diagnostic_event(
            text="Invalid DSH output record. See the private turn artifact.",
            provider_event_type=event_type,
        )

    def _dsh_cli_diagnostic(self, message: object) -> str:
        """Redact native diagnostics when the worker supplied its credential context."""

        if self.m_diagnostic_secrets is not None and isinstance(message, str):
            safe = sanitize_dsh_diagnostic(message, secret_values=self.m_diagnostic_secrets)
            if safe:
                return safe
        return "DSH native error. See the private turn artifact."

    def _consume_dsh_cli_payload(self, payload: Mapping[str, Any]) -> CanonicalHeadlessEvent:
        """Normalize the native one-shot stream without promoting its final frame to success."""

        event_type = _optional_text(payload.get("type")) or "unknown"
        raw_session_id = payload.get("sessionId")
        session_id = _optional_text(raw_session_id)
        if raw_session_id is not None and raw_session_id != session_id:
            return self._dsh_cli_invalid_record("dsh_cli_session_mismatch")
        data: dict[str, Any]
        if event_type == "error":
            kind, message = "error", self._dsh_cli_diagnostic(payload.get("message"))
            data = {"severity": "error", "text": message}
        elif event_type == "session" and session_id and self.m_session_id is None:
            kind, message = "session", "DSH native session selected"
            data = {"cwd": _optional_text(payload.get("cwd"))}
        elif self.m_session_id is None or (
            session_id is not None and session_id != self.m_session_id
        ):
            return self._dsh_cli_invalid_record("dsh_cli_session_mismatch")
        elif (
            event_type == "status"
            and (phase := _optional_text(payload.get("phase"))) in _DSH_CLI_STATUS_PHASES
        ):
            kind, message = "progress", str(phase)
            data = {"phase": phase}
            for field_name in ("turn", "step"):
                value = payload.get(field_name)
                if type(value) is int and value >= 0:
                    data[field_name] = value
            if phase == "turn_end":
                data.update(self._dsh_cli_reason(payload.get("reason")))
            if phase == "step_end" and isinstance(payload.get("usage"), dict):
                data["reported_step_usage"] = {
                    key: value
                    for key, value in payload["usage"].items()
                    if key
                    in {
                        "inputTokens",
                        "outputTokens",
                        "totalTokens",
                        "cacheReadTokens",
                        "cacheWriteTokens",
                        "reasoningTokens",
                    }
                    and type(value) is int
                    and value >= 0
                }
        elif event_type in {"text", "thinking"} and isinstance(payload.get("text"), str):
            kind = "assistant" if event_type == "text" else "reasoning"
            message = payload["text"]
            data = {"text": message}
        elif event_type in {"tool_call", "tool_result"} and (
            call_id := _optional_text(payload.get("callId"))
        ):
            data = {"action_id": call_id, "action_kind": "tool_use"}
            if event_type == "tool_call":
                name = _optional_text(payload.get("tool")) or "tool"
                arguments = payload.get("input")
                kind, message = "action_request", name
                data.update(
                    name=name,
                    arguments=arguments,
                    arguments_summary=_summarize_arguments(arguments),
                )
            else:
                status = _optional_text(payload.get("status"))
                if status not in {"completed", "error"}:
                    return self._dsh_cli_invalid_record("dsh_cli_invalid_record")
                failed = status == "error"
                kind = "action_result"
                message = (
                    self._dsh_cli_diagnostic(payload.get("result"))
                    if failed
                    else _single_line_summary(
                        _optional_text(payload.get("result")), fallback="tool result"
                    )
                )
                data.update(status=status, result_summary=message, is_error=failed)
        elif (
            event_type == "final"
            and session_id == self.m_session_id
            and isinstance(payload.get("text"), str)
        ):
            kind, message = "completion", "DSH native result observed"
            data = self._dsh_cli_reason(payload.get("reason"))
            data.update(
                status=f"native_{data['stop_reason'] or 'unknown'}", result_text=payload["text"]
            )
        else:
            return self._dsh_cli_invalid_record("dsh_cli_invalid_record")
        return self._event(
            kind=kind,
            message=message,
            provider_event_type=event_type,
            session_id=self.m_session_id if event_type == "error" else session_id,
            data=data,
        )

    def _dsh_cli_reason(self, raw_reason: object) -> dict[str, Any]:
        """Expose only structured reason labels and sanitized native failure detail."""

        reason = _optional_mapping(raw_reason) or {}
        reason_kind = _optional_text(reason.get("kind"))
        data: dict[str, Any] = {
            "stop_reason": reason_kind if reason_kind in _DSH_CLI_REASONS else None
        }
        error = _optional_mapping(reason.get("error"))
        if reason_kind == "error" and error is not None:
            data["error"] = self._dsh_cli_diagnostic(error.get("message"))
            if self.m_diagnostic_secrets is not None and (
                code := _optional_text(error.get("code"))
            ):
                data["error_code"] = sanitize_dsh_diagnostic(
                    code, secret_values=self.m_diagnostic_secrets, max_length=96
                )
        return data

    def _consume_dsh_payload(self, payload: Mapping[str, Any]) -> list[CanonicalHeadlessEvent]:
        """Project driver messages while preserving native ACP outcome distinctions."""

        event_type = str(payload.get("type", "unknown"))
        kind = "diagnostic"
        message = event_type
        data = dict(payload)
        if event_type == "session_init":
            kind, message = "session", "DSH native session selected"
        elif event_type == "session_update":
            update = payload.get("update")
            if not isinstance(update, dict):
                return []
            native_kind = update.get("sessionUpdate")
            content = update.get("content", {})
            if native_kind in {"agent_message_chunk", "agent_thought_chunk"}:
                kind = "assistant" if native_kind == "agent_message_chunk" else "reasoning"
                message = content.get("text", "") if isinstance(content, dict) else ""
                data = {"text": message}
            elif native_kind in {"tool_call", "tool_call_update"}:
                kind, message = "tool_call", str(update.get("title", "DSH tool activity"))
                data = dict(update)
            elif native_kind == "usage_update":
                kind, message = "context_usage", "DSH context occupancy"
                data = dict(update)
            else:
                kind, message = "configuration", str(native_kind)
        elif event_type == "native_result":
            reason = payload.get("stop_reason")
            kind = "completion"
            message = str(reason)
            data = {
                "status": "completed" if reason == "end_turn" else str(reason),
                "completed": reason == "end_turn",
                "interrupted": reason == "cancelled",
                "stop_reason": reason,
            }
        elif event_type in {"driver_error", "driver_cleanup_error"}:
            kind, message = "error", str(payload.get("message", "DSH driver failed"))
        return [
            self._event(
                kind=kind,
                message=message,
                provider_event_type=event_type,
                session_id=self.m_session_id,
                data=data,
                raw_payload=dict(payload),
            )
        ]

    def _consume_claude_payload(self, payload: Mapping[str, Any]) -> list[CanonicalHeadlessEvent]:
        """Parse one Claude stream-json payload."""

        record_type = str(payload.get("type", "event"))
        session_id = _extract_session_id_from_payload(payload) or self.m_session_id
        if session_id is not None and self.m_session_id is None:
            self.m_session_id = session_id

        if record_type == "assistant":
            return self._consume_claude_assistant(payload, session_id=session_id)
        if record_type == "result":
            result_text = _optional_text(payload.get("result"))
            status = "error" if bool(payload.get("is_error")) else "success"
            if isinstance(payload.get("subtype"), str) and status == "success":
                status = str(payload["subtype"]).strip() or "success"
            completion_data: dict[str, Any] = {
                "status": status,
                "result_text": result_text,
                "stop_reason": _optional_text(payload.get("stop_reason")),
                "duration_ms": _coerce_optional_int(payload.get("duration_ms")),
                "duration_api_ms": _coerce_optional_int(payload.get("duration_api_ms")),
                "total_cost_usd": _coerce_optional_number(payload.get("total_cost_usd")),
                "num_turns": _coerce_optional_int(payload.get("num_turns")),
                "usage": _normalize_usage_mapping(
                    _optional_mapping(payload.get("usage"))
                    or _optional_mapping(payload.get("model_usage"))
                ),
                "permission_denials": payload.get("permission_denials"),
                "errors": payload.get("errors"),
            }
            return [
                self._event(
                    kind="completion",
                    message=_completion_message(
                        status=status,
                        usage=completion_data.get("usage"),
                        result_text=result_text,
                    ),
                    provider_event_type="result",
                    session_id=session_id,
                    data=completion_data,
                    raw_payload=dict(payload),
                )
            ]
        if record_type == "system":
            subtype = _optional_text(payload.get("subtype")) or "system"
            summary = (
                _optional_text(payload.get("summary"))
                or _optional_text(payload.get("description"))
                or _optional_text(payload.get("status"))
                or subtype
            )
            return [
                self._event(
                    kind="progress",
                    message=summary,
                    provider_event_type=f"system.{subtype}",
                    session_id=session_id,
                    data={
                        "subtype": subtype,
                        "task_id": _optional_text(payload.get("task_id")),
                        "status": _optional_text(payload.get("status")),
                        "summary": summary,
                        "last_tool_name": _optional_text(payload.get("last_tool_name")),
                        "usage": _normalize_usage_mapping(_optional_mapping(payload.get("usage"))),
                    },
                    raw_payload=dict(payload),
                )
            ]
        return [
            self._event(
                kind="passthrough",
                message=record_type,
                provider_event_type=record_type,
                session_id=session_id,
                data={"summary": record_type},
                raw_payload=dict(payload),
            )
        ]

    def _consume_claude_assistant(
        self,
        payload: Mapping[str, Any],
        *,
        session_id: str | None,
    ) -> list[CanonicalHeadlessEvent]:
        """Parse one Claude assistant payload."""

        message_payload = _optional_mapping(payload.get("message")) or {}
        parent_tool_use_id = _optional_text(payload.get("parent_tool_use_id"))
        model_name = _optional_text(message_payload.get("model"))
        content = message_payload.get("content")
        if not isinstance(content, list):
            return [
                self._event(
                    kind="passthrough",
                    message="assistant",
                    provider_event_type="assistant",
                    session_id=session_id,
                    data={"summary": "assistant without content"},
                    raw_payload=dict(payload),
                )
            ]
        events: list[CanonicalHeadlessEvent] = []
        for block in content:
            if not isinstance(block, dict):
                continue
            block_type = str(block.get("type", "unknown"))
            if block_type == "text":
                text = _optional_text(block.get("text"))
                if text is None:
                    continue
                events.append(
                    self._event(
                        kind="assistant",
                        message=text,
                        provider_event_type="assistant.text",
                        session_id=session_id,
                        data={
                            "text": text,
                            "parent_tool_use_id": parent_tool_use_id,
                            "model": model_name,
                        },
                        raw_payload=dict(block),
                    )
                )
                continue
            if block_type == "thinking":
                text = _optional_text(block.get("thinking"))
                if text is None:
                    continue
                events.append(
                    self._event(
                        kind="reasoning",
                        message=_single_line_summary(text, fallback="reasoning"),
                        provider_event_type="assistant.thinking",
                        session_id=session_id,
                        data={
                            "text": text,
                            "signature": _optional_text(block.get("signature")),
                            "parent_tool_use_id": parent_tool_use_id,
                        },
                        raw_payload=dict(block),
                    )
                )
                continue
            if block_type == "tool_use":
                action_id = _optional_text(block.get("id"))
                if action_id is not None:
                    self.m_seen_action_requests.add(action_id)
                tool_name = _optional_text(block.get("name")) or "tool"
                args = block.get("input")
                events.append(
                    self._event(
                        kind="action_request",
                        message=f"{tool_name} {_summarize_arguments(args)}".strip(),
                        provider_event_type="assistant.tool_use",
                        session_id=session_id,
                        data={
                            "action_id": action_id,
                            "action_kind": "tool_use",
                            "name": tool_name,
                            "arguments": args,
                            "arguments_summary": _summarize_arguments(args),
                            "parent_tool_use_id": parent_tool_use_id,
                        },
                        raw_payload=dict(block),
                    )
                )
                continue
            if block_type == "tool_result":
                tool_use_id = _optional_text(block.get("tool_use_id"))
                status = "error" if bool(block.get("is_error")) else "success"
                result_summary = _summarize_claude_tool_result(block.get("content"))
                events.append(
                    self._event(
                        kind="action_result",
                        message=result_summary,
                        provider_event_type="assistant.tool_result",
                        session_id=session_id,
                        data={
                            "action_id": tool_use_id,
                            "action_kind": "tool_use",
                            "status": status,
                            "result_summary": result_summary,
                            "is_error": bool(block.get("is_error")),
                            "parent_tool_use_id": parent_tool_use_id,
                        },
                        raw_payload=dict(block),
                    )
                )
                continue
            events.append(
                self._event(
                    kind="passthrough",
                    message=f"assistant.{block_type}",
                    provider_event_type=f"assistant.{block_type}",
                    session_id=session_id,
                    data={"summary": f"assistant block {block_type}"},
                    raw_payload=dict(block),
                )
            )
        return events

    def _consume_codex_payload(self, payload: Mapping[str, Any]) -> list[CanonicalHeadlessEvent]:
        """Parse one Codex experimental-json payload."""

        record_type = str(payload.get("type", "event"))
        session_id = _extract_session_id_from_payload(payload) or self.m_session_id
        if record_type == "thread.started":
            thread_id = _optional_text(payload.get("thread_id"))
            if thread_id is not None:
                self.m_session_id = thread_id
            return [
                self._event(
                    kind="session",
                    message=thread_id or "thread started",
                    provider_event_type=record_type,
                    session_id=thread_id,
                    data={"session_id": thread_id},
                    raw_payload=dict(payload),
                )
            ]
        if record_type == "turn.started":
            return [
                self._event(
                    kind="progress",
                    message="turn started",
                    provider_event_type=record_type,
                    session_id=session_id,
                    data={"summary": "turn started"},
                    raw_payload=dict(payload),
                )
            ]
        if record_type == "turn.completed":
            usage = _normalize_usage_mapping(_optional_mapping(payload.get("usage")))
            return [
                self._event(
                    kind="completion",
                    message=_completion_message(status="success", usage=usage),
                    provider_event_type=record_type,
                    session_id=session_id,
                    data={"status": "success", "usage": usage},
                    raw_payload=dict(payload),
                )
            ]
        if record_type == "turn.failed":
            error_payload = _optional_mapping(payload.get("error"))
            error_message = _optional_text((error_payload or {}).get("message"))
            return [
                self._event(
                    kind="completion",
                    message=_completion_message(status="error", error_message=error_message),
                    provider_event_type=record_type,
                    session_id=session_id,
                    data={"status": "error", "error": error_payload},
                    raw_payload=dict(payload),
                )
            ]
        if record_type == "error":
            return [
                self._event(
                    kind="diagnostic",
                    message=_optional_text(payload.get("message")) or "error",
                    provider_event_type=record_type,
                    session_id=session_id,
                    data={
                        "severity": "error",
                        "text": _optional_text(payload.get("message")),
                    },
                    raw_payload=dict(payload),
                )
            ]
        if record_type not in {"item.started", "item.updated", "item.completed"}:
            return [
                self._event(
                    kind="passthrough",
                    message=record_type,
                    provider_event_type=record_type,
                    session_id=session_id,
                    data={"summary": record_type},
                    raw_payload=dict(payload),
                )
            ]

        item = _optional_mapping(payload.get("item"))
        if item is None:
            return [
                self._diagnostic_event(
                    text="missing item payload",
                    provider_event_type=record_type,
                    raw_payload=dict(payload),
                )
            ]

        item_type = str(item.get("type", "item"))
        if item_type == "agent_message":
            text = _optional_text(item.get("text"))
            if text is None or record_type == "item.started":
                return []
            return [
                self._event(
                    kind="assistant",
                    message=text,
                    provider_event_type=f"{record_type}.{item_type}",
                    session_id=session_id,
                    data={"text": text, "item_id": _optional_text(item.get("id"))},
                    raw_payload=dict(payload),
                )
            ]
        if item_type == "reasoning":
            text = _optional_text(item.get("text"))
            if text is None or record_type == "item.started":
                return []
            return [
                self._event(
                    kind="reasoning",
                    message=_single_line_summary(text, fallback="reasoning"),
                    provider_event_type=f"{record_type}.{item_type}",
                    session_id=session_id,
                    data={"text": text, "item_id": _optional_text(item.get("id"))},
                    raw_payload=dict(payload),
                )
            ]
        if item_type == "todo_list":
            if record_type == "item.started":
                return []
            return [
                self._event(
                    kind="progress",
                    message="todo list updated",
                    provider_event_type=f"{record_type}.{item_type}",
                    session_id=session_id,
                    data={
                        "summary": "todo list updated",
                        "item_id": _optional_text(item.get("id")),
                        "items": item.get("items"),
                    },
                    raw_payload=dict(payload),
                )
            ]
        if item_type == "error":
            return [
                self._event(
                    kind="diagnostic",
                    message=_optional_text(item.get("message")) or "item error",
                    provider_event_type=f"{record_type}.{item_type}",
                    session_id=session_id,
                    data={
                        "severity": "error",
                        "item_id": _optional_text(item.get("id")),
                        "text": _optional_text(item.get("message")),
                    },
                    raw_payload=dict(payload),
                )
            ]
        if item_type in {
            "command_execution",
            "mcp_tool_call",
            "collab_tool_call",
            "web_search",
            "file_change",
        }:
            return self._consume_codex_action_item(
                record_type=record_type,
                item=item,
                session_id=session_id,
                raw_payload=dict(payload),
            )

        return [
            self._event(
                kind="passthrough",
                message=f"{record_type}.{item_type}",
                provider_event_type=f"{record_type}.{item_type}",
                session_id=session_id,
                data={"summary": f"item {item_type}"},
                raw_payload=dict(payload),
            )
        ]

    def _consume_codex_action_item(
        self,
        *,
        record_type: str,
        item: Mapping[str, Any],
        session_id: str | None,
        raw_payload: dict[str, Any],
    ) -> list[CanonicalHeadlessEvent]:
        """Parse one Codex action item lifecycle payload."""

        item_type = str(item.get("type", "item"))
        item_id = _optional_text(item.get("id"))
        if record_type == "item.started":
            if item_id is not None:
                self.m_seen_action_requests.add(item_id)
            return [
                self._event(
                    kind="action_request",
                    message=_codex_action_request_message(item),
                    provider_event_type=f"{record_type}.{item_type}",
                    session_id=session_id,
                    data=_codex_action_request_data(item),
                    raw_payload=raw_payload,
                )
            ]
        if record_type == "item.updated" and item_type != "todo_list":
            status = _optional_text(item.get("status"))
            if status == "in_progress":
                if item_type == "collab_tool_call":
                    progress_data = _codex_action_request_data(item)
                    progress_data["status"] = status
                    return [
                        self._event(
                            kind="progress",
                            message=f"{_codex_action_request_message(item)} in progress",
                            provider_event_type=f"{record_type}.{item_type}",
                            session_id=session_id,
                            data=progress_data,
                            raw_payload=raw_payload,
                        )
                    ]
                return []
        return [
            self._event(
                kind="action_result",
                message=_codex_action_result_message(item),
                provider_event_type=f"{record_type}.{item_type}",
                session_id=session_id,
                data=_codex_action_result_data(item),
                raw_payload=raw_payload,
            )
        ]

    def _consume_kimi_payload(self, payload: Mapping[str, Any]) -> list[CanonicalHeadlessEvent]:
        """Parse one Kimi Code stream-json payload."""

        role = _optional_text(payload.get("role"))
        payload_type = _optional_text(payload.get("type"))
        session_id = _extract_session_id_from_payload(payload) or self.m_session_id

        if role == "meta" and payload_type == "session.resume_hint":
            resume_session_id = _optional_text(payload.get("session_id"))
            if resume_session_id is not None:
                self.m_session_id = resume_session_id
            return [
                self._event(
                    kind="session",
                    message=resume_session_id or "session resume hint",
                    provider_event_type="session.resume_hint",
                    session_id=resume_session_id,
                    data={
                        "session_id": resume_session_id,
                        "command": _optional_text(payload.get("command")),
                        "content": _optional_text(payload.get("content")),
                    },
                    raw_payload=dict(payload),
                )
            ]

        if role == "meta" and payload_type == "turn.step.retrying":
            failed_attempt = _coerce_optional_int(payload.get("failed_attempt"))
            next_attempt = _coerce_optional_int(payload.get("next_attempt"))
            max_attempts = _coerce_optional_int(payload.get("max_attempts"))
            delay_ms = _coerce_optional_int(payload.get("delay_ms"))
            error_message = _optional_text(payload.get("error_message"))
            raw_error_message = error_message
            if error_message is not None and self.m_diagnostic_secrets is not None:
                error_message = sanitize_dsh_diagnostic(
                    error_message, secret_values=self.m_diagnostic_secrets
                )
            attempt_summary = (
                f"attempt {next_attempt}/{max_attempts}"
                if next_attempt is not None and max_attempts is not None
                else "retrying"
            )
            delay_summary = f" after {delay_ms}ms" if delay_ms is not None else ""
            message = f"{attempt_summary}{delay_summary}"
            if error_message is not None:
                message += f": {error_message}"
            return [
                self._event(
                    kind="progress",
                    message=message,
                    provider_event_type=payload_type,
                    session_id=session_id,
                    data={
                        "summary": message,
                        "status": "retrying",
                        "failed_attempt": failed_attempt,
                        "next_attempt": next_attempt,
                        "max_attempts": max_attempts,
                        "delay_ms": delay_ms,
                        "error_name": _optional_text(payload.get("error_name")),
                        "error_message": error_message,
                        "status_code": _coerce_optional_int(payload.get("status_code")),
                    },
                    raw_payload=(
                        dict(payload)
                        if not self.m_diagnostic_secrets and error_message == raw_error_message
                        else None
                    ),
                )
            ]

        if role == "assistant":
            return self._consume_kimi_assistant(payload, session_id=session_id)

        if role == "tool":
            content = _optional_text(payload.get("content"))
            result_summary = _single_line_summary(content, fallback="tool result")
            return [
                self._event(
                    kind="action_result",
                    message=result_summary,
                    provider_event_type="tool",
                    session_id=session_id,
                    data={
                        "action_id": _optional_text(payload.get("tool_call_id")),
                        "action_kind": "tool_use",
                        "status": "success",
                        "result_summary": result_summary,
                        "result_text": content,
                    },
                    raw_payload=dict(payload),
                )
            ]

        provider_event_type = payload_type or role or "event"
        if provider_event_type == "error":
            raw_message = _optional_text(payload.get("message"))
            diagnostic_message = raw_message
            if raw_message is not None and self.m_diagnostic_secrets is not None:
                diagnostic_message = sanitize_dsh_diagnostic(
                    raw_message, secret_values=self.m_diagnostic_secrets
                )
            return [
                self._event(
                    kind="diagnostic",
                    message=diagnostic_message or "error",
                    provider_event_type=provider_event_type,
                    session_id=session_id,
                    data={
                        "severity": "error",
                        "text": diagnostic_message,
                    },
                    raw_payload=(
                        dict(payload)
                        if not self.m_diagnostic_secrets and diagnostic_message == raw_message
                        else None
                    ),
                )
            ]
        return [
            self._event(
                kind="passthrough",
                message=provider_event_type,
                provider_event_type=provider_event_type,
                session_id=session_id,
                data={"summary": provider_event_type},
                raw_payload=dict(payload),
            )
        ]

    def _consume_kimi_assistant(
        self,
        payload: Mapping[str, Any],
        *,
        session_id: str | None,
    ) -> list[CanonicalHeadlessEvent]:
        """Parse one Kimi assistant payload."""

        events: list[CanonicalHeadlessEvent] = []
        content = _optional_text(payload.get("content"))
        if content is not None:
            events.append(
                self._event(
                    kind="assistant",
                    message=content,
                    provider_event_type="assistant.content",
                    session_id=session_id,
                    data={"text": content, "role": "assistant"},
                    raw_payload=dict(payload),
                )
            )

        tool_calls = payload.get("tool_calls")
        if not isinstance(tool_calls, list):
            if events:
                return events
            return [
                self._event(
                    kind="passthrough",
                    message="assistant",
                    provider_event_type="assistant",
                    session_id=session_id,
                    data={"summary": "assistant without content"},
                    raw_payload=dict(payload),
                )
            ]

        for tool_call in tool_calls:
            if not isinstance(tool_call, Mapping):
                continue
            function_payload = _optional_mapping(tool_call.get("function")) or {}
            action_id = _optional_text(tool_call.get("id"))
            if action_id is not None:
                self.m_seen_action_requests.add(action_id)
            tool_name = _optional_text(function_payload.get("name")) or "tool"
            arguments = _parse_json_string_or_value(function_payload.get("arguments"))
            events.append(
                self._event(
                    kind="action_request",
                    message=f"{tool_name} {_summarize_arguments(arguments)}".strip(),
                    provider_event_type="assistant.tool_call",
                    session_id=session_id,
                    data={
                        "action_id": action_id,
                        "action_kind": "tool_use",
                        "name": tool_name,
                        "arguments": arguments,
                        "arguments_summary": _summarize_arguments(arguments),
                        "tool_call_type": _optional_text(tool_call.get("type")),
                    },
                    raw_payload=dict(tool_call),
                )
            )
        return events

    def _event(
        self,
        *,
        kind: str,
        message: str,
        provider_event_type: str,
        session_id: str | None,
        data: dict[str, Any] | None = None,
        raw_payload: dict[str, Any] | None = None,
    ) -> CanonicalHeadlessEvent:
        """Build one canonical event with parser defaults."""

        effective_session_id = session_id or self.m_session_id
        if effective_session_id is not None and self.m_session_id is None:
            self.m_session_id = effective_session_id
        return CanonicalHeadlessEvent(
            kind=kind,
            message=message,
            turn_index=self.m_turn_index,
            provider=self.m_provider,
            provider_event_type=provider_event_type,
            session_id=effective_session_id,
            data=data,
            raw_payload=raw_payload,
        )

    def _diagnostic_event(
        self,
        *,
        text: str,
        provider_event_type: str,
        raw_payload: dict[str, Any] | None = None,
    ) -> CanonicalHeadlessEvent:
        """Build one canonical diagnostic event."""

        return self._event(
            kind="diagnostic",
            message=text,
            provider_event_type=provider_event_type,
            session_id=self.m_session_id,
            data={"severity": "warning", "text": text},
            raw_payload=raw_payload,
        )


class CanonicalHeadlessRenderer:
    """Incremental append-only renderer for canonical headless events."""

    def __init__(
        self,
        *,
        style: HeadlessDisplayStyle,
        detail: HeadlessDisplayDetail,
        sink: Callable[[str], None],
    ) -> None:
        """Initialize one renderer.

        Parameters
        ----------
        style:
            Requested output style.
        detail:
            Requested output detail.
        sink:
            Text sink that receives already-formatted chunks.
        """

        self.m_style: HeadlessDisplayStyle = style
        self.m_detail: HeadlessDisplayDetail = detail
        self.m_sink: Callable[[str], None] = sink
        self.m_assistant_open: bool = False
        self.m_last_chunk_had_newline: bool = True

    def render_event(self, event: CanonicalHeadlessEvent) -> None:
        """Render one canonical event incrementally.

        Parameters
        ----------
        event:
            Canonical event to render.
        """

        if self.m_style == "json":
            self._flush_assistant_boundary()
            self.m_sink(
                json.dumps(
                    _renderable_event_record(event=event, detail=self.m_detail), sort_keys=True
                )
                + "\n"
            )
            self.m_last_chunk_had_newline = True
            return

        if event.kind == "assistant":
            self._render_assistant_event(event)
            return

        self._flush_assistant_boundary()
        for line in _human_lines_for_event(event=event, style=self.m_style, detail=self.m_detail):
            self.m_sink(f"{line}\n")
            self.m_last_chunk_had_newline = True

    def finish(self) -> None:
        """Flush any deferred assistant block boundary."""

        self._flush_assistant_boundary()

    def _render_assistant_event(self, event: CanonicalHeadlessEvent) -> None:
        """Render one assistant text event."""

        text = _optional_text((event.data or {}).get("text")) or event.message
        if not text:
            return
        if not self.m_last_chunk_had_newline and not self.m_assistant_open:
            self.m_sink("\n")
            self.m_last_chunk_had_newline = True
        self.m_sink(text)
        self.m_assistant_open = True
        self.m_last_chunk_had_newline = text.endswith("\n")

    def _flush_assistant_boundary(self) -> None:
        """Terminate one open assistant block before structured output."""

        if not self.m_assistant_open:
            return
        if not self.m_last_chunk_had_newline:
            self.m_sink("\n")
        self.m_assistant_open = False
        self.m_last_chunk_had_newline = True


def canonical_headless_event_artifact_path(*, turn_dir: Path) -> Path:
    """Return the canonical event artifact path for one turn directory.

    Parameters
    ----------
    turn_dir:
        Turn artifact directory.

    Returns
    -------
    Path
        Canonical event artifact path.
    """

    return (turn_dir / CANONICAL_HEADLESS_EVENTS_ARTIFACT).resolve()


def resolve_headless_display_style(value: object) -> HeadlessDisplayStyle:
    """Normalize one configured headless display style.

    Parameters
    ----------
    value:
        Candidate configured value.

    Returns
    -------
    HeadlessDisplayStyle
        Valid display style with default fallback.
    """

    if isinstance(value, str):
        candidate = value.strip().lower()
        if candidate in _VALID_DISPLAY_STYLES:
            return candidate  # type: ignore[return-value]
    return "plain"


def resolve_headless_display_detail(value: object) -> HeadlessDisplayDetail:
    """Normalize one configured headless display detail.

    Parameters
    ----------
    value:
        Candidate configured value.

    Returns
    -------
    HeadlessDisplayDetail
        Valid display detail with default fallback.
    """

    if isinstance(value, str):
        candidate = value.strip().lower()
        if candidate in _VALID_DISPLAY_DETAILS:
            return candidate  # type: ignore[return-value]
    return "concise"


def resolve_headless_provider(
    *, tool: str | None = None, backend: str | None = None
) -> HeadlessProvider:
    """Resolve one canonical provider identity.

    Parameters
    ----------
    tool:
        Optional tool identity.
    backend:
        Optional backend identity.

    Returns
    -------
    HeadlessProvider
        Canonical provider name.
    """

    for candidate in (tool, backend):
        if candidate is None:
            continue
        lowered = candidate.strip().lower()
        if lowered.startswith("claude"):
            return "claude"
        if lowered.startswith("codex"):
            return "codex"
        if lowered.startswith("kimi"):
            return "kimi"
        if lowered.startswith("dsh"):
            return "dsh"
    raise ValueError(
        f"Unsupported headless provider tool/backend: tool={tool!r}, backend={backend!r}"
    )


def canonical_headless_events_from_provider_output(
    *,
    provider: HeadlessProvider,
    output_format: str,
    stdout_text: str,
    turn_index: int,
    diagnostic_secrets: tuple[str, ...] | None = None,
) -> list[CanonicalHeadlessEvent]:
    """Canonicalize one raw provider stdout payload.

    Parameters
    ----------
    provider:
        Upstream provider identity.
    output_format:
        Provider output format (`json`, `stream-json`, or `dsh-cli`).
    stdout_text:
        Raw provider stdout text.
    turn_index:
        Managed turn index.
    diagnostic_secrets:
        Optional launch credential context for sanitized native failure detail.

    Returns
    -------
    list[CanonicalHeadlessEvent]
        Canonical semantic events.
    """

    parser = CanonicalHeadlessEventParser(
        provider=provider,
        turn_index=turn_index,
        output_format=output_format,
        diagnostic_secrets=diagnostic_secrets,
    )
    if provider == "dsh" and output_format in {"dsh-cli", "stream-json"}:
        complete_lines, _, unfinished_line = stdout_text.rpartition("\n")
        records: list[CanonicalHeadlessEvent] = []
        for line in complete_lines.split("\n"):
            if line.strip():
                records.extend(parser.consume_stream_line(line))
        if unfinished_line:
            records.append(parser._dsh_cli_invalid_record("dsh_cli_incomplete_record"))  # noqa: SLF001
        return records
    if output_format == "stream-json":
        events: list[CanonicalHeadlessEvent] = []
        for raw_line in stdout_text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            events.extend(parser.consume_stream_line(line))
        return events

    stripped = stdout_text.strip()
    if not stripped:
        return []
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        return [parser._diagnostic_event(text=stripped, provider_event_type="raw_json_text")]  # noqa: SLF001

    if isinstance(payload, list):
        events = []
        for item in payload:
            if isinstance(item, dict):
                events.extend(parser.consume_json_object(item))
            else:
                events.append(
                    parser._diagnostic_event(  # noqa: SLF001
                        text=str(item),
                        provider_event_type="non_mapping",
                        raw_payload={"value": item},
                    )
                )
        return events
    if isinstance(payload, dict):
        return parser.consume_json_object(payload)
    return [
        parser._diagnostic_event(  # noqa: SLF001
            text=str(payload),
            provider_event_type="scalar",
            raw_payload={"value": payload},
        )
    ]


def load_canonical_headless_events(*, canonical_path: Path) -> list[CanonicalHeadlessEvent]:
    """Load canonical events from the durable canonical artifact.

    Parameters
    ----------
    canonical_path:
        Canonical artifact path.

    Returns
    -------
    list[CanonicalHeadlessEvent]
        Parsed canonical events.
    """

    events: list[CanonicalHeadlessEvent] = []
    if not canonical_path.exists():
        return events
    for raw_line in canonical_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            continue
        events.append(CanonicalHeadlessEvent.from_artifact_record(payload))
    return events


def load_preferred_canonical_headless_events(
    *,
    turn_dir: Path,
    provider: HeadlessProvider,
    output_format: str,
    turn_index: int,
) -> list[CanonicalHeadlessEvent]:
    """Load canonical events, preferring the canonical artifact with raw fallback.

    Parameters
    ----------
    turn_dir:
        Turn artifact directory.
    provider:
        Upstream provider identity.
    output_format:
        Provider output format.
    turn_index:
        Managed turn index.

    Returns
    -------
    list[CanonicalHeadlessEvent]
        Canonical semantic events from durable or compatibility sources.
    """

    canonical_path = canonical_headless_event_artifact_path(turn_dir=turn_dir)
    if canonical_path.exists():
        return load_canonical_headless_events(canonical_path=canonical_path)
    stdout_path = (turn_dir / "stdout.jsonl").resolve()
    stdout_text = stdout_path.read_text(encoding="utf-8") if stdout_path.exists() else ""
    return canonical_headless_events_from_provider_output(
        provider=provider,
        output_format=output_format,
        stdout_text=stdout_text,
        turn_index=turn_index,
    )


def canonical_headless_events_to_session_events(
    events: Sequence[CanonicalHeadlessEvent],
) -> list[SessionEvent]:
    """Project canonical events into runtime `SessionEvent` rows.

    Parameters
    ----------
    events:
        Canonical events.

    Returns
    -------
    list[SessionEvent]
        Runtime session events with detailed canonical payloads.
    """

    session_events: list[SessionEvent] = []
    for event in events:
        session_events.append(
            SessionEvent(
                kind=event.kind,
                message=event.message,
                turn_index=event.turn_index,
                payload=event.to_public_payload(detail="detail"),
                timestamp_utc=event.timestamp_utc,
            )
        )
    return session_events


def render_canonical_headless_events(
    *,
    events: Sequence[CanonicalHeadlessEvent],
    style: HeadlessDisplayStyle,
    detail: HeadlessDisplayDetail,
    sink: Callable[[str], None],
) -> None:
    """Render one canonical event stream with the shared headless renderer.

    Parameters
    ----------
    events:
        Canonical events in semantic order.
    style:
        Requested render style.
    detail:
        Requested render detail.
    sink:
        Text sink for rendered output.
    """

    renderer = CanonicalHeadlessRenderer(style=style, detail=detail, sink=sink)
    for event in events:
        renderer.render_event(event)
    renderer.finish()


def renderable_public_headless_event_records(
    *,
    events: Sequence[CanonicalHeadlessEvent],
    detail: HeadlessDisplayDetail,
) -> list[dict[str, Any]]:
    """Build JSON-ready event rows for CLI or API output.

    Parameters
    ----------
    events:
        Canonical events in order.
    detail:
        Requested event detail.

    Returns
    -------
    list[dict[str, Any]]
        JSON-ready event rows.
    """

    return [_renderable_event_record(event=event, detail=detail) for event in events]


def append_canonical_headless_event(
    *,
    canonical_path: Path,
    event: CanonicalHeadlessEvent,
) -> None:
    """Append one canonical event to the durable artifact.

    Parameters
    ----------
    canonical_path:
        Canonical artifact path.
    event:
        Canonical event to append.
    """

    with canonical_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event.to_artifact_record(), sort_keys=True))
        handle.write("\n")


def append_stderr_diagnostic_event(
    *,
    canonical_path: Path,
    provider: HeadlessProvider,
    turn_index: int,
    text: str,
    session_id: str | None,
) -> CanonicalHeadlessEvent:
    """Build and append one stderr-derived diagnostic canonical event.

    Parameters
    ----------
    canonical_path:
        Canonical event artifact path.
    provider:
        Upstream provider identity.
    turn_index:
        Managed turn index.
    text:
        Raw stderr line without trailing newline.
    session_id:
        Current canonical session identity when known.

    Returns
    -------
    CanonicalHeadlessEvent
        Persisted diagnostic event.
    """

    event = CanonicalHeadlessEvent(
        kind="diagnostic",
        message=text,
        turn_index=turn_index,
        provider=provider,
        provider_event_type="stderr",
        session_id=session_id,
        data={"severity": "warning", "stream": "stderr", "text": text},
        raw_payload={"line": text},
    )
    append_canonical_headless_event(canonical_path=canonical_path, event=event)
    return event


def _renderable_event_record(
    *,
    event: CanonicalHeadlessEvent,
    detail: HeadlessDisplayDetail,
) -> dict[str, Any]:
    """Return one JSON-ready renderable event record."""

    return {
        "kind": event.kind,
        "message": event.message,
        "turn_index": event.turn_index,
        "timestamp_utc": event.timestamp_utc,
        "payload": event.to_public_payload(detail=detail),
    }


def _human_lines_for_event(
    *,
    event: CanonicalHeadlessEvent,
    style: HeadlessDisplayStyle,
    detail: HeadlessDisplayDetail,
) -> list[str]:
    """Render one canonical event into human-readable lines."""

    if event.kind == "session":
        if detail == "concise":
            return []
        provider_bits: list[str] = [event.provider]
        if event.session_id is not None:
            provider_bits.append(f"session={event.session_id}")
        return [f"{_human_prefix(style=style, kind=event.kind)} {' '.join(provider_bits)}"]

    if event.kind == "reasoning":
        if detail == "concise":
            return []
        return [f"{_human_prefix(style=style, kind=event.kind)} {event.message}"]

    if event.kind == "action_request":
        return [_human_action_request_line(event=event, style=style, detail=detail)]

    if event.kind == "action_result":
        return [_human_action_result_line(event=event, style=style, detail=detail)]

    if event.kind == "completion":
        return [_human_completion_line(event=event, style=style, detail=detail)]

    if event.kind == "progress":
        if detail == "concise":
            return []
        return [f"{_human_prefix(style=style, kind=event.kind)} {event.message}"]

    if event.kind == "diagnostic":
        severity = _optional_text((event.data or {}).get("severity")) or "warning"
        return [f"{_human_prefix(style=style, kind=event.kind)} [{severity}] {event.message}"]

    if detail == "detail":
        return [f"{_human_prefix(style=style, kind=event.kind)} {event.message}"]
    return []


def _human_action_request_line(
    *,
    event: CanonicalHeadlessEvent,
    style: HeadlessDisplayStyle,
    detail: HeadlessDisplayDetail,
) -> str:
    """Render one action-request event line."""

    data = event.data or {}
    parts = [f"{_human_prefix(style=style, kind=event.kind)} {event.message}"]
    if detail == "detail":
        extras: list[str] = []
        if isinstance(data.get("action_id"), str):
            extras.append(f"id={data['action_id']}")
        if event.session_id is not None:
            extras.append(f"session={event.session_id}")
        extras.append(f"provider_event={event.provider_event_type}")
        if extras:
            parts.append(f" ({', '.join(extras)})")
    return "".join(parts)


def _human_action_result_line(
    *,
    event: CanonicalHeadlessEvent,
    style: HeadlessDisplayStyle,
    detail: HeadlessDisplayDetail,
) -> str:
    """Render one action-result event line."""

    data = event.data or {}
    line = f"{_human_prefix(style=style, kind=event.kind)} {event.message}"
    if detail == "detail":
        extras: list[str] = []
        if isinstance(data.get("status"), str):
            extras.append(f"status={data['status']}")
        if isinstance(data.get("action_id"), str):
            extras.append(f"id={data['action_id']}")
        extras.append(f"provider_event={event.provider_event_type}")
        if extras:
            line += f" ({', '.join(extras)})"
    return line


def _human_completion_line(
    *,
    event: CanonicalHeadlessEvent,
    style: HeadlessDisplayStyle,
    detail: HeadlessDisplayDetail,
) -> str:
    """Render one completion event line."""

    data = event.data or {}
    status = _optional_text(data.get("status")) or "completed"
    parts = [f"{_human_prefix(style=style, kind=event.kind)} {status}"]
    usage_parts = _format_usage_parts(_optional_mapping(data.get("usage")))
    if usage_parts:
        parts.append(" | ")
        parts.append(", ".join(usage_parts))
    if isinstance(data.get("result_text"), str) and detail == "detail":
        result_text = _single_line_summary(str(data["result_text"]), fallback="")
        if result_text:
            parts.append(f" | result={result_text}")
    if detail == "detail":
        if isinstance(data.get("stop_reason"), str):
            parts.append(f" | stop_reason={data['stop_reason']}")
        parts.append(f" | provider_event={event.provider_event_type}")
    return "".join(parts)


def _human_prefix(*, style: HeadlessDisplayStyle, kind: str) -> str:
    """Return the human-readable prefix for one semantic event kind."""

    if style == "fancy":
        return {
            "action_request": "Action:",
            "action_result": "Result:",
            "completion": "Complete:",
            "reasoning": "Reasoning:",
            "progress": "Progress:",
            "diagnostic": "Diagnostic:",
            "session": "Session:",
        }.get(kind, "Event:")
    return {
        "action_request": "[action]",
        "action_result": "[result]",
        "completion": "[complete]",
        "reasoning": "[reasoning]",
        "progress": "[progress]",
        "diagnostic": "[diagnostic]",
        "session": "[session]",
    }.get(kind, "[event]")


def _format_usage_parts(usage: Mapping[str, Any] | None) -> list[str]:
    """Format one normalized usage mapping into concise footer parts."""

    if usage is None:
        return []
    parts: list[str] = []
    for key in (
        "input_tokens",
        "cached_input_tokens",
        "output_tokens",
        "total_tokens",
        "tool_calls",
        "reasoning_tokens",
        "thoughts_token_count",
    ):
        value = usage.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            parts.append(f"{key}={value}")
    duration_ms = usage.get("duration_ms")
    if isinstance(duration_ms, (int, float)) and not isinstance(duration_ms, bool):
        parts.append(f"duration_ms={int(duration_ms)}")
    total_cost_usd = usage.get("total_cost_usd")
    if isinstance(total_cost_usd, (int, float)) and not isinstance(total_cost_usd, bool):
        parts.append(f"cost_usd={total_cost_usd}")
    return parts


def _completion_message(
    *,
    status: str,
    usage: Mapping[str, Any] | None = None,
    result_text: str | None = None,
    error_message: str | None = None,
) -> str:
    """Build one concise completion message."""

    if error_message:
        return error_message
    if result_text:
        return _single_line_summary(result_text, fallback=status)
    usage_parts = _format_usage_parts(usage)
    if usage_parts:
        return f"{status}: {', '.join(usage_parts)}"
    return status


def _normalize_usage_mapping(usage: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """Normalize provider-specific usage fields into one shared mapping."""

    if usage is None:
        return None
    normalized: dict[str, Any] = {}
    key_aliases = {
        "input_tokens": "input_tokens",
        "cached_input_tokens": "cached_input_tokens",
        "output_tokens": "output_tokens",
        "total_tokens": "total_tokens",
        "tool_calls": "tool_calls",
        "duration_ms": "duration_ms",
        "total_cost_usd": "total_cost_usd",
        "cached": "cached_input_tokens",
        "thoughtsTokenCount": "thoughts_token_count",
        "reasoning_tokens": "reasoning_tokens",
    }
    for raw_key, normalized_key in key_aliases.items():
        if raw_key not in usage:
            continue
        value = usage.get(raw_key)
        if isinstance(value, (int, float, str)) and not isinstance(value, bool):
            normalized[normalized_key] = value
    return normalized or dict(usage)


def _codex_action_request_data(item: Mapping[str, Any]) -> dict[str, Any]:
    """Build one canonical Codex action-request payload."""

    item_type = str(item.get("type", "action"))
    if item_type == "command_execution":
        return {
            "action_id": _optional_text(item.get("id")),
            "action_kind": item_type,
            "name": "command",
            "arguments_summary": _optional_text(item.get("command")) or "command",
            "command": _optional_text(item.get("command")),
        }
    if item_type == "mcp_tool_call":
        tool_name = ".".join(
            part
            for part in (
                _optional_text(item.get("server")),
                _optional_text(item.get("tool")),
            )
            if part is not None
        )
        return {
            "action_id": _optional_text(item.get("id")),
            "action_kind": item_type,
            "name": tool_name or "mcp_tool_call",
            "arguments_summary": _summarize_arguments(item.get("arguments")),
            "arguments": item.get("arguments"),
        }
    if item_type == "collab_tool_call":
        tool_name = _optional_text(item.get("tool")) or "collab_tool"
        prompt = _optional_text(item.get("prompt"))
        receiver_thread_ids = item.get("receiver_thread_ids")
        receivers = (
            [value for value in receiver_thread_ids if isinstance(value, str)]
            if isinstance(receiver_thread_ids, list)
            else []
        )
        arguments_summary = prompt or (
            f"receivers={','.join(receivers)}" if receivers else tool_name
        )
        return {
            "action_id": _optional_text(item.get("id")),
            "action_kind": item_type,
            "name": tool_name,
            "arguments_summary": arguments_summary,
            "tool": tool_name,
            "sender_thread_id": _optional_text(item.get("sender_thread_id")),
            "receiver_thread_ids": receivers,
            "prompt": prompt,
            "agents_states": item.get("agents_states"),
        }
    if item_type == "web_search":
        query = _optional_text(item.get("query"))
        return {
            "action_id": _optional_text(item.get("id")),
            "action_kind": item_type,
            "name": "web_search",
            "arguments_summary": query or "web search",
            "query": query,
        }
    changes = item.get("changes")
    return {
        "action_id": _optional_text(item.get("id")),
        "action_kind": item_type,
        "name": "file_change",
        "arguments_summary": _summarize_file_changes(changes),
        "changes": changes,
    }


def _codex_action_request_message(item: Mapping[str, Any]) -> str:
    """Build one concise Codex action-request message."""

    data = _codex_action_request_data(item)
    name = _optional_text(data.get("name")) or "action"
    summary = _optional_text(data.get("arguments_summary"))
    if summary is None:
        return name
    return f"{name} {summary}".strip()


def _codex_action_result_data(item: Mapping[str, Any]) -> dict[str, Any]:
    """Build one canonical Codex action-result payload."""

    item_type = str(item.get("type", "action"))
    result_data = _codex_action_request_data(item)
    status = _optional_text(item.get("status")) or "completed"
    result_data["status"] = status
    if item_type == "command_execution":
        result_data["exit_code"] = _coerce_optional_int(item.get("exit_code"))
        result_data["result_summary"] = _single_line_summary(
            _optional_text(item.get("aggregated_output")),
            fallback=status,
        )
        return result_data
    if item_type == "mcp_tool_call":
        result_data["result_summary"] = _single_line_summary(
            _summarize_result_payload(item.get("result")),
            fallback=(_optional_text((item.get("error") or {}).get("message")) or status)
            if isinstance(item.get("error"), dict)
            else status,
        )
        result_data["error"] = item.get("error")
        return result_data
    if item_type == "collab_tool_call":
        result_data["result_summary"] = _summarize_collab_agent_states(
            item.get("agents_states"),
            fallback=status,
        )
        return result_data
    if item_type == "web_search":
        result_data["result_summary"] = _optional_text(item.get("query")) or status
        return result_data
    result_data["result_summary"] = _summarize_file_changes(item.get("changes"))
    return result_data


def _codex_action_result_message(item: Mapping[str, Any]) -> str:
    """Build one concise Codex action-result message."""

    result_data = _codex_action_result_data(item)
    status = _optional_text(result_data.get("status")) or "completed"
    name = _optional_text(result_data.get("name")) or "action"
    summary = _optional_text(result_data.get("result_summary"))
    if summary:
        return f"{name} {status}: {summary}"
    return f"{name} {status}"


def _summarize_collab_agent_states(value: object, *, fallback: str) -> str:
    """Return one concise summary of Codex collaboration agent states."""

    if not isinstance(value, dict) or not value:
        return fallback
    summaries: list[str] = []
    for thread_id, state in value.items():
        if not isinstance(thread_id, str) or not isinstance(state, dict):
            continue
        status = _optional_text(state.get("status")) or "unknown"
        message = _optional_text(state.get("message"))
        summary = f"{thread_id}={status}"
        if message is not None:
            summary += f" ({_single_line_summary(message, fallback=status)})"
        summaries.append(summary)
    return ", ".join(summaries) if summaries else fallback


def _summarize_arguments(value: object) -> str:
    """Return one concise argument summary string."""

    if value is None:
        return ""
    if isinstance(value, str):
        return _single_line_summary(value, fallback="")
    if isinstance(value, dict):
        if not value:
            return "{}"
        items = [f"{key}={_summarize_scalar_or_json(item)}" for key, item in value.items()]
        return f"({', '.join(items[:4])}{'...' if len(items) > 4 else ''})"
    if isinstance(value, list):
        if not value:
            return "[]"
        rendered = ", ".join(_summarize_scalar_or_json(item) for item in value[:4])
        suffix = ", ..." if len(value) > 4 else ""
        return f"[{rendered}{suffix}]"
    return _summarize_scalar_or_json(value)


def _summarize_claude_tool_result(value: object) -> str:
    """Return one concise Claude tool-result summary."""

    if isinstance(value, str):
        return _single_line_summary(value, fallback="tool result")
    if isinstance(value, list):
        chunks: list[str] = []
        for item in value:
            if isinstance(item, str):
                chunks.append(item)
                continue
            if isinstance(item, dict):
                text_value = _optional_text(item.get("text"))
                if text_value is not None:
                    chunks.append(text_value)
                    continue
                chunks.append(json.dumps(item, sort_keys=True))
        if not chunks:
            return "tool result"
        return _single_line_summary(" ".join(chunks), fallback="tool result")
    return _single_line_summary(_summarize_result_payload(value), fallback="tool result")


def _summarize_result_payload(value: object) -> str:
    """Return one concise result-payload summary."""

    if value is None:
        return ""
    if isinstance(value, str):
        return _single_line_summary(value, fallback="")
    try:
        rendered = json.dumps(value, sort_keys=True)
    except TypeError:
        rendered = str(value)
    return _single_line_summary(rendered, fallback="")


def _summarize_file_changes(value: object) -> str:
    """Return one concise file-change summary."""

    if not isinstance(value, list) or not value:
        return "file change"
    chunks: list[str] = []
    for item in value[:4]:
        if not isinstance(item, dict):
            continue
        kind = _optional_text(item.get("kind")) or "update"
        path = _optional_text(item.get("path")) or "unknown"
        chunks.append(f"{kind} {path}")
    suffix = " ..." if len(value) > 4 else ""
    return ", ".join(chunks) + suffix


def _summarize_scalar_or_json(value: object) -> str:
    """Render one scalar or JSON-ish object into a short string."""

    if isinstance(value, str):
        return _single_line_summary(value, fallback="")
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    try:
        rendered = json.dumps(value, sort_keys=True)
    except TypeError:
        rendered = str(value)
    return _single_line_summary(rendered, fallback="")


def _single_line_summary(text: str | None, *, fallback: str) -> str:
    """Collapse one text blob into a short single-line summary."""

    if text is None:
        return fallback
    compact = " ".join(part for part in text.splitlines() if part.strip())
    compact = " ".join(compact.split())
    if not compact:
        return fallback
    if len(compact) <= 160:
        return compact
    return f"{compact[:157]}..."


def _extract_session_id_from_payload(payload: Mapping[str, Any]) -> str | None:
    """Extract one canonical session identity from a provider payload."""

    for key in ("session_id", "sessionId", "thread_id", "threadId"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    session_payload = payload.get("session")
    if isinstance(session_payload, Mapping):
        nested = session_payload.get("id")
        if isinstance(nested, str) and nested.strip():
            return nested.strip()
    thread_payload = payload.get("thread")
    if isinstance(thread_payload, Mapping):
        nested = thread_payload.get("id")
        if isinstance(nested, str) and nested.strip():
            return nested.strip()
    return None


def _optional_text(value: object) -> str | None:
    """Return one stripped optional string."""

    if not isinstance(value, str):
        return None
    stripped = value.strip()
    if not stripped:
        return None
    return stripped


def _optional_mapping(value: object) -> dict[str, Any] | None:
    """Return one plain dict when the value is mapping-like."""

    if not isinstance(value, Mapping):
        return None
    return {str(key): item for key, item in value.items()}


def _coerce_optional_int(value: object) -> int | None:
    """Return one optional integer."""

    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.strip():
        try:
            return int(value.strip())
        except ValueError:
            return None
    return None


def _coerce_optional_number(value: object) -> int | float | None:
    """Return one optional numeric value."""

    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = float(value.strip())
        except ValueError:
            return None
        if parsed.is_integer():
            return int(parsed)
        return parsed
    return None


def _coerce_provider(value: str) -> HeadlessProvider:
    """Coerce one provider string into the literal union."""

    if value == "claude":
        return "claude"
    if value == "codex":
        return "codex"
    if value == "kimi":
        return "kimi"
    if value == "dsh":
        return "dsh"
    raise ValueError(f"Unsupported canonical headless provider `{value}`.")


def _parse_json_string_or_value(value: object) -> object:
    """Parse a JSON-encoded string when possible and preserve raw value otherwise."""

    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if not stripped:
        return value
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return value
