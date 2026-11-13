"""Codex rollout and exec JSON accounting with explicit cumulative scope."""

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

CODEX_ALIASES = {
    "input_tokens": ("input_tokens", "prompt_tokens", "input"),
    "output_tokens": ("output_tokens", "completion_tokens", "output"),
    "cached_input_tokens": ("cached_input_tokens", "cache_read_input_tokens", "cached_tokens"),
    "cache_write_input_tokens": ("cache_write_input_tokens", "cache_creation_input_tokens"),
    "reasoning_output_tokens": ("reasoning_output_tokens", "reasoning_tokens"),
    "total_tokens": ("total_tokens",),
}
CODEX_SEMANTICS = UsageTokenSemantics(
    cached_input_included_in_input=True,
    cache_write_included_in_input=True,
    reasoning_included_in_output=True,
)


def parse_codex(
    payload: Mapping[str, Any], state: UsageAdapterState, context: UsageParseContext
) -> list[UsageObservation]:
    """Parse native Codex records and exec events without assuming turn scope."""

    event = str(payload.get("type", ""))
    data = mapping(payload.get("payload"))
    if event == "thread.started":
        state.provider_session_id = text_id(payload.get("thread_id")) or state.provider_session_id
        return []
    if event == "session_meta":
        state.provider_session_id = text_id(data.get("id")) or text_id(data.get("session_id"))
        spawn = mapping(mapping(mapping(data.get("source")).get("subagent")).get("thread_spawn"))
        state.forked_from_id = text_id(data.get("forked_from_id")) or text_id(
            spawn.get("parent_thread_id")
        )
        state.spawned_subagent = bool(spawn)
        state.replay_active = state.forked_from_id is not None
        return []
    if event in {"inter_agent_communication_metadata", "inter_agent_communication"}:
        if data.get("trigger_turn") is True or payload.get("trigger_turn") is True:
            state.replay_active = False
        return []
    if event == "turn_context":
        state.model = text_id(data.get("model")) or state.model
        turn = text_id(data.get("turn_id"))
        if turn and not state.replay_active and turn != state.provider_turn_id:
            state.provider_turn_id = turn
            return [lifecycle_observation(state, context, payload, event, "started")]
        return []
    if event == "compacted":
        response = text_id(data.get("compaction_response_id"))
        if not response:
            return []
        if response not in state.compacted_ids:
            state.compacted_ids.append(response)
        pending = state.pending_compactions.pop(response, None)
        if pending is None or state.replay_active:
            return []
        return _request_record(pending, state, context, accounting_kind="compaction")
    if event == "token_usage_record":
        if state.spawned_subagent:
            state.replay_active = False
        if state.replay_active:
            return []
        if not text_id(data.get("response_id")):
            return []
        if text_id(data.get("turn_id")):
            return _request_record(payload, state, context)
        # Older compaction-only request records must match a compaction marker.
        response = str(data["response_id"])
        if response in state.compacted_ids:
            return _request_record(payload, state, context, accounting_kind="compaction")
        state.pending_compactions[response] = {
            "type": event,
            "timestamp": timestamp(payload),
            "payload": {
                key: data[key]
                for key in ("response_id", "usage", "thread_token_usage", "model")
                if key in data
            },
        }
        state.latest_response_id = response
        state.latest_response_values = counters(mapping(data.get("usage")), CODEX_ALIASES)
        return []
    if event == "event_msg":
        inner = str(data.get("type", ""))
        turn = text_id(data.get("turn_id"))
        if inner in {"task_started", "turn_started"}:
            state.replay_active = False
            state.provider_turn_id = turn or state.provider_turn_id
            state.latest_response_id = None
            state.latest_response_values = {}
            return [lifecycle_observation(state, context, payload, inner, "started")]
        if inner == "token_count":
            return _token_count(payload, state, context)
        if inner in {"task_complete", "turn_complete", "turn_completed"}:
            state.provider_turn_id = turn or state.provider_turn_id
            if not state.replay_active:
                return [lifecycle_observation(state, context, payload, inner, "completed")]
        if inner in {"turn_aborted", "turn_interrupted", "task_aborted"}:
            state.provider_turn_id = turn or state.provider_turn_id
            if not state.replay_active:
                return [lifecycle_observation(state, context, payload, inner, "interrupted")]
        if inner in {"turn_failed", "task_failed"} and not state.replay_active:
            state.provider_turn_id = turn or state.provider_turn_id
            return [lifecycle_observation(state, context, payload, inner, "failed")]
        return []
    if event == "turn.completed":
        usage = mapping(payload.get("usage"))
        return [
            observation(
                state,
                context,
                payload,
                event_type=event,
                kind="cumulative",
                scope="session_cumulative",
                values=counters(usage, CODEX_ALIASES),
                accounting={"usage": dict(usage)},
                semantics=CODEX_SEMANTICS,
            ),
            lifecycle_observation(state, context, payload, event, "completed"),
        ]
    if event in {"turn.started", "turn.failed"}:
        state.provider_turn_id = text_id(payload.get("turn_id")) or state.provider_turn_id
        return [
            lifecycle_observation(
                state, context, payload, event, "started" if event == "turn.started" else "failed"
            )
        ]
    return []


def _request_record(
    payload: Mapping[str, Any],
    state: UsageAdapterState,
    context: UsageParseContext,
    *,
    accounting_kind: str = "request",
) -> list[UsageObservation]:
    """Read a provider response record with identity suitable for deduplication."""

    data = mapping(payload.get("payload"))
    response = text_id(data.get("response_id"))
    state.provider_session_id = text_id(data.get("thread_id")) or state.provider_session_id
    state.provider_turn_id = text_id(data.get("turn_id")) or state.provider_turn_id
    usage = mapping(data.get("usage"))
    if not usage or response is None:
        return []
    values = counters(usage, CODEX_ALIASES)
    state.latest_response_id = response
    state.latest_response_values = values
    result = [
        observation(
            state,
            context,
            payload,
            event_type="token_usage_record",
            values=values,
            request_id=response,
            accounting={"usage": dict(usage)},
            semantics=CODEX_SEMANTICS,
            accounting_kind=accounting_kind,
            metadata={
                "representation": "response_record",
                "thread_total": counters(mapping(data.get("thread_token_usage")), CODEX_ALIASES),
            },
        )
    ]
    if isinstance(data.get("thread_token_usage"), dict):
        total = mapping(data["thread_token_usage"])
        state.previous_totals.update(counters(total, CODEX_ALIASES))
        result.append(
            observation(
                state,
                context,
                payload,
                event_type="token_usage_record.thread_total",
                kind="cumulative",
                scope="session_cumulative",
                values=counters(total, CODEX_ALIASES),
                accounting={"thread_token_usage": dict(total)},
                semantics=CODEX_SEMANTICS,
            )
        )
    return result


def _token_count(
    payload: Mapping[str, Any], state: UsageAdapterState, context: UsageParseContext
) -> list[UsageObservation]:
    """Read legacy snapshots and suppress repeated or request-covered deltas."""

    data = mapping(payload.get("payload"))
    info = mapping(data.get("info"))
    total = counters(mapping(info.get("total_token_usage")), CODEX_ALIASES)
    last = counters(mapping(info.get("last_token_usage")), CODEX_ALIASES)
    previous = state.previous_totals
    advanced = not total or total != previous
    state.previous_totals = total or previous
    if state.replay_active:
        return []
    result: list[UsageObservation] = []
    if total:
        result.append(
            observation(
                state,
                context,
                payload,
                event_type="token_count.total",
                kind="cumulative",
                scope="session_cumulative",
                values=total,
                accounting={"total_token_usage": dict(mapping(info.get("total_token_usage")))},
                semantics=CODEX_SEMANTICS,
            )
        )
    pending = state.pending_compactions.get(state.latest_response_id or "")
    covered_pending = pending is not None and (
        last == state.latest_response_values
        or counters(
            mapping(mapping(pending.get("payload")).get("thread_token_usage")), CODEX_ALIASES
        )
        == total
    )
    if last and advanced and (last != state.latest_response_values or covered_pending):
        fingerprint = stable_key(timestamp(payload), state.provider_turn_id, last)
        ordinal = state.occurrences.get(fingerprint, 0)
        state.occurrences[fingerprint] = ordinal + 1
        result.append(
            observation(
                state,
                context,
                payload,
                event_type="token_count.last",
                values=last,
                request_id=state.latest_response_id
                if covered_pending
                else f"token-count-{fingerprint}-{ordinal}",
                accounting={"last_token_usage": dict(mapping(info.get("last_token_usage")))},
                semantics=CODEX_SEMANTICS,
                metadata={"representation": "legacy_snapshot", "cumulative_total": total},
            )
        )
    if last == state.latest_response_values and state.latest_response_id:
        state.pending_compactions.pop(state.latest_response_id, None)
        # Consume the response/snapshot association. A later independent request
        # can have identical counters and must not inherit this response ID.
        state.latest_response_id = None
        state.latest_response_values = {}
    return result
