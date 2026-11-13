"""Kimi wire accounting with qualified request and native turn boundaries."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from houmao.agents.realm_controller.usage_adapters.common import (
    UsageAdapterState,
    UsageParseContext,
    counters,
    lifecycle_observation,
    mapping,
    observation,
    stable_key,
    text_id,
    timestamp,
)
from houmao.agents.realm_controller.usage_models import UsageObservation, UsageTokenSemantics

KIMI_ALIASES = {
    "input_tokens": ("inputOther", "input_other"),
    "output_tokens": ("output",),
    "cached_input_tokens": ("inputCacheRead", "input_cache_read"),
    "cache_write_input_tokens": ("inputCacheCreation", "input_cache_creation"),
    "total_tokens": ("total", "total_tokens"),
}
KIMI_SEMANTICS = UsageTokenSemantics(
    cached_input_included_in_input=False,
    cache_write_included_in_input=False,
    reasoning_included_in_output=True,
)


def parse_kimi(
    payload: Mapping[str, Any], state: UsageAdapterState, context: UsageParseContext
) -> list[UsageObservation]:
    """Read Kimi usage increments separately from status and session totals."""

    event = str(payload.get("type", ""))
    if event == "session.resume_hint":
        state.provider_session_id = text_id(payload.get("session_id")) or state.provider_session_id
        return []
    if event == "turn.prompt":
        state.provider_turn_id = text_id(payload.get("turnId")) or state.provider_turn_id
        return [lifecycle_observation(state, context, payload, event, "started")]
    if event in {"turn.ended", "prompt.completed"}:
        state.provider_turn_id = text_id(payload.get("turnId")) or state.provider_turn_id
        reason = payload.get("reason")
        if reason in {"completed", "success"}:
            outcome = "completed"
        elif reason in {"interrupted", "aborted", "cancelled", "canceled"}:
            outcome = "interrupted"
        elif reason in {"error", "failed", "failure"}:
            outcome = "failed"
        else:
            return []
        return [lifecycle_observation(state, context, payload, event, outcome)]
    if event == "usage.record":
        state.model = text_id(payload.get("model")) or state.model
        usage = mapping(payload.get("usage"))
        values = counters(usage, KIMI_ALIASES)
        if payload.get("usageScope") != "turn":
            # A session-source request is not automatically a cumulative total.
            return [
                observation(
                    state,
                    context,
                    payload,
                    event_type=event,
                    kind="cumulative",
                    scope="unknown",
                    values=values,
                    accounting={"usage": dict(usage), "usageScope": payload.get("usageScope")},
                    semantics=KIMI_SEMANTICS,
                    coverage="unknown",
                    metadata={"limitation": "unverified_session_usage_scope"},
                )
            ]
        # Kimi 2.6.0 UsageAgentModel.record emits one usage.record per request;
        # context.append_loop_event.step.end repeats it and is not added again.
        request_id = text_id(payload.get("requestId")) or text_id(payload.get("id"))
        if request_id is None:
            request_id = "kimi-request-" + stable_key(
                state.provider_session_id, state.provider_turn_id, timestamp(payload), values
            )
        return [
            observation(
                state,
                context,
                payload,
                event_type=event,
                values=values,
                request_id=request_id,
                accounting={"usage": dict(usage), "usageScope": "turn"},
                semantics=KIMI_SEMANTICS,
                coverage="complete" if state.provider_turn_id is not None else "unknown",
            )
        ]
    message = mapping(payload.get("message"))
    data = mapping(message.get("payload"))
    if message.get("type") == "TurnBegin":
        turn = text_id(data.get("turn_id"))
        if turn is not None:
            state.provider_turn_id = turn
            return [lifecycle_observation(state, context, payload, "TurnBegin", "started")]
    if message.get("type") == "StatusUpdate" and isinstance(data.get("token_usage"), dict):
        usage = mapping(data["token_usage"])
        return [
            observation(
                state,
                context,
                payload,
                event_type="StatusUpdate",
                values=counters(usage, KIMI_ALIASES),
                request_id=text_id(data.get("message_id")),
                accounting={"token_usage": dict(usage)},
                semantics=KIMI_SEMANTICS,
                coverage="unknown",
            )
        ]
    return []
