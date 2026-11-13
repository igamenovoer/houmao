"""Claude Code accounting from native messages and structured completion output."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from houmao.agents.realm_controller.usage_adapters.common import (
    UsageAdapterState,
    UsageParseContext,
    counters,
    lifecycle_observation,
    mapping,
    number,
    observation,
    text_id,
)
from houmao.agents.realm_controller.usage_models import UsageObservation, UsageTokenSemantics

CLAUDE_ALIASES = {
    "input_tokens": ("input_tokens",),
    "output_tokens": ("output_tokens",),
    "cached_input_tokens": ("cache_read_input_tokens", "cached_input_tokens"),
    "cache_write_input_tokens": ("cache_creation_input_tokens", "cache_write_input_tokens"),
    "reasoning_output_tokens": ("reasoning_output_tokens", "reasoning_tokens"),
    "total_tokens": ("total_tokens",),
}
CLAUDE_SEMANTICS = UsageTokenSemantics(
    cached_input_included_in_input=False,
    cache_write_included_in_input=False,
    reasoning_included_in_output=True,
)


def parse_claude(
    payload: Mapping[str, Any], state: UsageAdapterState, context: UsageParseContext
) -> list[UsageObservation]:
    """Read recognized Claude accounting and lifecycle fields for one JSON record."""

    session = text_id(payload.get("sessionId")) or text_id(payload.get("session_id"))
    if session:
        state.provider_session_id = session
    event = str(payload.get("type", ""))
    message = mapping(payload.get("message"))
    state.model = text_id(message.get("model")) or text_id(payload.get("model")) or state.model
    if event == "user" and not payload.get("isMeta") and _is_prompt(message):
        turn = text_id(payload.get("uuid")) or text_id(payload.get("prompt_id"))
        if turn:
            state.provider_turn_id = turn
            return [lifecycle_observation(state, context, payload, event, "started")]
    if event == "assistant" and isinstance(message.get("usage"), dict):
        usage = mapping(message["usage"])
        values = counters(usage, CLAUDE_ALIASES)
        thinking = mapping(usage.get("output_tokens_details")).get("thinking_tokens")
        if "reasoning_output_tokens" not in values and number(thinking) is not None:
            values["reasoning_output_tokens"] = number(thinking)
        message_id = text_id(message.get("id"))
        request_id = text_id(payload.get("requestId")) or text_id(payload.get("request_id"))
        # Message IDs are stable across native/stdout copies and content blocks.
        logical_id = message_id or request_id
        complete = message.get("stop_reason") is not None
        result = [
            observation(
                state,
                context,
                payload,
                event_type=event,
                values=values,
                request_id=logical_id,
                accounting={"usage": dict(usage)},
                semantics=CLAUDE_SEMANTICS,
                coverage="complete" if complete else "partial",
                metadata={"request_id": request_id, "message_id": message_id},
            )
        ]
        if message.get("stop_reason") in {"end_turn", "stop_sequence"}:
            result.append(lifecycle_observation(state, context, payload, event, "completed"))
        return result
    if event == "result":
        usage = mapping(payload.get("usage"))
        values = counters(usage, CLAUDE_ALIASES)
        duration = number(payload.get("duration_ms"))
        if duration is not None:
            values["duration_ms"] = duration
        result = [
            observation(
                state,
                context,
                payload,
                event_type=event,
                kind="summary",
                scope="turn",
                values=values,
                accounting={"usage": dict(usage), "duration_ms": duration},
                semantics=CLAUDE_SEMANTICS,
                metadata={"summary_complete": True},
            )
        ]
        # Qualified 2.1.323 resumed captures report these as session totals.
        cumulative = {
            key: number(payload[raw])
            for key, raw in {
                "cost_usd": "total_cost_usd",
                "duration_api_ms": "duration_api_ms",
            }.items()
            if raw in payload
        }
        if cumulative:
            state.previous_totals.update(cumulative)
            result.append(
                observation(
                    state,
                    context,
                    payload,
                    event_type="result.session_totals",
                    kind="cumulative",
                    scope="session_cumulative",
                    values=cumulative,
                    accounting={
                        key: payload[key]
                        for key in ("total_cost_usd", "duration_api_ms")
                        if key in payload
                    },
                    semantics=CLAUDE_SEMANTICS,
                )
            )
        failed = payload.get("is_error") is True or str(payload.get("subtype", "")).startswith(
            "error"
        )
        result.append(
            lifecycle_observation(
                state, context, payload, event, "failed" if failed else "completed"
            )
        )
        return result
    if event == "cost-state":
        values = {
            key: number(payload[raw])
            for key, raw in {
                "cost_usd": "totalCostUSD",
                "duration_api_ms": "totalAPIDuration",
            }.items()
            if raw in payload
        }
        state.previous_totals.update(values)
        return [
            observation(
                state,
                context,
                payload,
                event_type=event,
                kind="cumulative",
                scope="session_cumulative",
                values=values,
                accounting={
                    "cost_usd": values.get("cost_usd"),
                    "duration_api_ms": values.get("duration_api_ms"),
                },
            )
        ]
    return []


def _is_prompt(message: Mapping[str, Any]) -> bool:
    """Distinguish external user prompts from continuing tool-result messages."""

    content = message.get("content")
    if isinstance(content, str):
        return True
    return (
        isinstance(content, list)
        and any(
            isinstance(part, dict) and part.get("type") in {"text", "image"} for part in content
        )
        and not any(
            isinstance(part, dict) and part.get("type") == "tool_result" for part in content
        )
    )
