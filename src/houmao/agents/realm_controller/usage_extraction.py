"""Assemble immutable turn accounting from provider-faithful observations.

Measurements are selected per metric. Verified turn summaries take precedence
over their constituent requests, and cumulative snapshots require an explicit
comparable baseline. Source variants retain provenance without repeated charges.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence

from houmao.agents.realm_controller.usage_adapters.common import TOKEN_KEYS, stable_key
from houmao.agents.realm_controller.usage_models import (
    UsageCost,
    UsageMetric,
    UsageNumber,
    UsageObservation,
    UsageOutcome,
    UsageProviderTiming,
    UsageRecord,
    UsageSource,
    UsageSubagentUsage,
    UsageTokenSemantics,
    UsageTokenUsage,
    UsageTurnSnapshot,
    opaque_usage_reference,
)


def assemble_usage_record(
    snapshot: UsageTurnSnapshot,
    observations: Sequence[UsageObservation],
    *,
    outcome: UsageOutcome,
    completed_at_utc: str | None = None,
    wall_time_ms: UsageNumber | None = None,
    baseline: Mapping[str, UsageNumber | None] | None = None,
) -> UsageRecord:
    """Project a finalized turn, keeping ambiguous measurements unavailable.

    Parameters
    ----------
    snapshot:
        Durable turn-start identity and verified collection boundaries.
    observations:
        Evidence within the final cutoff, including repeated source variants.
    outcome:
        Terminal outcome established by the execution or native lifecycle.
    completed_at_utc:
        Original terminal timestamp, never recovery's current time.
    wall_time_ms:
        Houmao-measured wall time when the managed execution measured it.
    baseline:
        Optional explicit comparable cumulative baseline; otherwise the saved
        turn-start baseline is used.
    """

    selected = [item for item in observations if _belongs_to_turn(item, snapshot)]
    children = [item for item in selected if item.parent_turn_id is not None]
    parent = [item for item in selected if item.parent_turn_id is None]
    diagnostics: list[str] = []
    requests = _deduplicate_requests(parent, diagnostics)
    summaries = [
        item for item in parent if item.kind == "summary" and item.measurement_scope == "turn"
    ]
    cumulative = [
        item
        for item in parent
        if item.kind == "cumulative" and item.measurement_scope == "session_cumulative"
    ]
    saved_baseline = dict(snapshot.baseline if baseline is None else baseline)
    partial = snapshot.coverage == "partial" or outcome != "completed"
    metrics = {
        key: _select_metric(
            key, summaries, requests, cumulative, saved_baseline, snapshot, partial, diagnostics
        )
        for key in (*TOKEN_KEYS, "cost_usd", "duration_ms", "duration_api_ms")
    }
    semantics = _select_semantics(parent)
    _derive_total(metrics, semantics)
    sources = [_public_source(item) for item in _unique_observations(selected)]
    wall = UsageMetric(unit="milliseconds")
    if wall_time_ms is not None:
        runtime_id = opaque_usage_reference(
            f"runtime:{snapshot.runtime_session_id}:{snapshot.turn_id}"
        )
        sources.append(
            UsageSource(
                source_id=runtime_id,
                source_kind="houmao_runtime",
                source_ref=runtime_id,
                profile_id="houmao-wall-time-v1",
                measurement_scope="turn",
                accounting={"duration_ms": wall_time_ms},
            )
        )
        wall = UsageMetric.reported(wall_time_ms, unit="milliseconds", source_ids=[runtime_id])
    identity = snapshot.model_dump(
        include=set(UsageTurnSnapshot.model_fields)
        - {
            "started_at_utc",
            "binding_id",
            "source_positions",
            "baseline",
            "counter_epoch",
            "coverage",
            "metadata",
        }
    )
    sessions = {item.provider_session_id for item in selected if item.provider_session_id}
    native_turns = {item.provider_turn_id for item in selected if item.provider_turn_id}
    if not identity.get("provider_session_id") and len(sessions) == 1:
        identity["provider_session_id"] = sessions.pop()
    if not identity.get("provider_turn_id") and len(native_turns) == 1:
        identity["provider_turn_id"] = native_turns.pop()
    child_breakdown = _subagent_breakdown(snapshot, children, partial)
    return UsageRecord(
        **identity,
        outcome=outcome,
        started_at_utc=snapshot.started_at_utc,
        completed_at_utc=completed_at_utc,
        token_usage=UsageTokenUsage(**{key: metrics[key] for key in TOKEN_KEYS}),
        token_semantics=semantics,
        wall_time_ms=wall,
        provider_timing=UsageProviderTiming(
            duration_ms=metrics["duration_ms"], duration_api_ms=metrics["duration_api_ms"]
        ),
        cost=UsageCost(
            amount=metrics["cost_usd"],
            currency="USD" if metrics["cost_usd"].value is not None else None,
        ),
        sources=sources,
        subagent_accounting="separate" if child_breakdown else "unknown",
        subagent_usage=child_breakdown,
        diagnostics=list(dict.fromkeys(diagnostics)),
    )


def _belongs_to_turn(item: UsageObservation, snapshot: UsageTurnSnapshot) -> bool:
    """Reject explicit identity mismatches while allowing associated output evidence."""

    if item.provider != snapshot.provider:
        return False
    if item.turn_id is not None and item.turn_id != snapshot.turn_id:
        return False
    if (
        snapshot.provider_session_id
        and item.provider_session_id
        and item.provider_session_id != snapshot.provider_session_id
        and item.parent_turn_id is None
    ):
        return False
    if (
        snapshot.provider_turn_id
        and item.provider_turn_id
        and item.provider_turn_id != snapshot.provider_turn_id
        and item.parent_turn_id is None
    ):
        return False
    return True


def _unique_observations(items: Sequence[UsageObservation]) -> list[UsageObservation]:
    """Collapse equivalent replays while retaining distinct provisional variants."""

    seen: set[str] = set()
    unique: list[UsageObservation] = []
    for item in items:
        key = stable_key(item.model_dump(mode="json"))
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def _request_key(item: UsageObservation) -> str:
    """Resolve one provider request without treating equal counters as identity."""

    if item.request_id is None:
        return item.observation_id
    scope = item.provider_session_id
    # An actual Claude request ID establishes copied-transcript identity across
    # sessions. Requestless gateway placeholders remain scoped to their session.
    if item.provider == "claude" and item.metadata.get("request_id"):
        scope = None
    elif item.provider == "claude" and not item.request_id.startswith(("msg_", "resp_")):
        # Gateway placeholders can repeat across independent requests.
        return stable_key(
            item.provider,
            scope,
            item.request_id,
            item.provider_turn_id,
            item.timestamp_utc or item.observation_id,
        )
    return stable_key(item.provider, scope, item.request_id)


def _deduplicate_requests(
    observations: Sequence[UsageObservation], diagnostics: list[str]
) -> list[UsageObservation]:
    """Select complete request snapshots and surface incompatible duplicates."""

    groups: dict[str, list[UsageObservation]] = defaultdict(list)
    for item in observations:
        if item.kind == "request" and item.measurement_scope == "request":
            if item.metadata.get("representation") == "legacy_snapshot" and any(
                other.metadata.get("representation") == "response_record"
                and other.provider_turn_id == item.provider_turn_id
                and bool(item.metadata.get("cumulative_total"))
                and other.metadata.get("thread_total") == item.metadata.get("cumulative_total")
                for other in observations
            ):
                continue
            groups[_request_key(item)].append(item)
    result: list[UsageObservation] = []
    for variants in groups.values():
        non_sidechain = [item for item in variants if not item.is_sidechain]
        eligible = non_sidechain or variants
        complete = [item for item in eligible if item.coverage == "complete"]
        eligible = complete or eligible
        chosen = max(
            eligible,
            key=lambda item: (
                sum(value is not None for value in item.values.values()),
                item.source_kind == "native_session_log",
                item.timestamp_utc or "",
            ),
        )
        conflicts = {
            key
            for key in chosen.values
            if len({item.values[key] for item in eligible if item.values.get(key) is not None}) > 1
        }
        if conflicts:
            diagnostics.append("conflicting_request_evidence")
            chosen = chosen.model_copy(
                update={
                    "values": {
                        key: None if key in conflicts else value
                        for key, value in chosen.values.items()
                    },
                    "coverage": "partial",
                }
            )
        result.append(chosen)
    return result


def _select_metric(
    key: str,
    summaries: Sequence[UsageObservation],
    requests: Sequence[UsageObservation],
    cumulative: Sequence[UsageObservation],
    baseline: Mapping[str, UsageNumber | None],
    snapshot: UsageTurnSnapshot,
    partial: bool,
    diagnostics: list[str],
) -> UsageMetric:
    """Choose one compatible representation for an individual measurement."""

    unit = (
        "currency"
        if key == "cost_usd"
        else "milliseconds"
        if key.startswith("duration")
        else "tokens"
    )
    usable_summaries = [item for item in summaries if item.values.get(key) is not None]
    if usable_summaries:
        chosen = usable_summaries[-1]
        return UsageMetric.reported(
            chosen.values[key],
            unit=unit,
            source_ids=[_source_id(chosen)],
            partial=partial or chosen.coverage != "complete",
        )
    available = [item for item in requests if item.values.get(key) is not None]
    if available:
        total = sum(item.values[key] or 0 for item in available)
        incomplete = (
            partial
            or len(available) != len(requests)
            or any(item.coverage != "complete" for item in available)
        )
        source_ids = [_source_id(item) for item in available]
        if len(available) == 1:
            return UsageMetric.reported(total, unit=unit, source_ids=source_ids, partial=incomplete)
        return UsageMetric.derived(
            total,
            rule="sum_distinct_provider_requests",
            unit=unit,
            source_ids=source_ids,
            partial=incomplete,
        )
    snapshots = [item for item in cumulative if item.values.get(key) is not None]
    if snapshots:
        chosen = snapshots[-1]
        previous = baseline.get(key)
        epoch = chosen.metadata.get("counter_epoch")
        if (
            epoch is not None
            and snapshot.counter_epoch is not None
            and epoch != snapshot.counter_epoch
        ):
            diagnostics.append("incomparable_cumulative_epoch")
        elif previous is not None:
            current = chosen.values[key]
            assert current is not None
            if current >= previous:
                baseline_sources = snapshot.metadata.get("baseline_source_ids", [])
                if isinstance(baseline_sources, dict):
                    baseline_sources = baseline_sources.get(key, [])
                endpoint_ids = (
                    [
                        source if source.startswith("source-") else opaque_usage_reference(source)
                        for source in baseline_sources
                        if isinstance(source, str)
                    ]
                    if isinstance(baseline_sources, list)
                    else []
                )
                return UsageMetric.derived(
                    current - previous,
                    rule="same_session_cumulative_delta",
                    unit=unit,
                    source_ids=list(dict.fromkeys([*endpoint_ids, _source_id(chosen)])),
                    partial=partial or chosen.coverage != "complete",
                )
            diagnostics.append("cumulative_counter_decreased")
        else:
            diagnostics.append("missing_cumulative_baseline")
    return UsageMetric(unit=unit)


def _select_semantics(items: Sequence[UsageObservation]) -> UsageTokenSemantics:
    """Retain only inclusion relationships established consistently by evidence."""

    values: dict[str, bool | None] = {}
    for key in UsageTokenSemantics.model_fields:
        reported = {
            getattr(item.token_semantics, key)
            for item in items
            if getattr(item.token_semantics, key) is not None
        }
        values[key] = reported.pop() if len(reported) == 1 else None
    return UsageTokenSemantics(**values)


def _derive_total(metrics: dict[str, UsageMetric], semantics: UsageTokenSemantics) -> None:
    """Derive totals only from a fully specified inclusion relationship."""

    if metrics["total_tokens"].value is not None:
        return
    required = ["input_tokens", "output_tokens"]
    for included, key in (
        (semantics.cached_input_included_in_input, "cached_input_tokens"),
        (semantics.cache_write_included_in_input, "cache_write_input_tokens"),
        (semantics.reasoning_included_in_output, "reasoning_output_tokens"),
    ):
        if included is None:
            return
        if not included:
            required.append(key)
    if any(metrics[key].value is None for key in required):
        return
    total = sum(metrics[key].value or 0 for key in required)
    source_ids: list[str] = []
    for key in required:
        provenance = metrics[key].provenance
        if provenance is not None:
            source_ids.extend(provenance.source_ids)
    sources = list(dict.fromkeys(source_ids))
    metrics["total_tokens"] = UsageMetric.derived(
        total,
        rule="provider_disjoint_token_buckets",
        source_ids=sources,
        partial=any(metrics[key].availability == "partial" for key in required),
    )


def _source_id(item: UsageObservation) -> str:
    """Identify an accounting source variant without exposing its private locator."""

    return opaque_usage_reference(stable_key(item.model_dump(mode="json")))


def _public_source(item: UsageObservation) -> UsageSource:
    """Project one observation through the accounting-only public boundary."""

    return UsageSource(
        source_id=_source_id(item),
        observation_id=item.observation_id,
        source_kind=item.source_kind,
        source_ref=opaque_usage_reference(item.source_ref),
        profile_id=item.profile_id,
        provider_event_type=item.provider_event_type,
        provider_version=item.provider_version,
        measurement_scope=item.measurement_scope,
        accounting=item.accounting,
    )


def _subagent_breakdown(
    snapshot: UsageTurnSnapshot, items: Sequence[UsageObservation], partial: bool
) -> list[UsageSubagentUsage]:
    """Keep explicitly linked child measurements separate from parent totals."""

    grouped: dict[str, list[UsageObservation]] = defaultdict(list)
    for item in items:
        child_id = item.provider_turn_id or item.metadata.get("child_id")
        if isinstance(child_id, str):
            grouped[child_id].append(item)
    result: list[UsageSubagentUsage] = []
    for child_id, evidence in grouped.items():
        diagnostic: list[str] = []
        requests = _deduplicate_requests(evidence, diagnostic)
        metrics = {
            key: _select_metric(key, [], requests, [], {}, snapshot, partial, diagnostic)
            for key in TOKEN_KEYS
        }
        _derive_total(metrics, _select_semantics(evidence))
        included = {
            item.metadata.get("included_in_parent")
            for item in evidence
            if isinstance(item.metadata.get("included_in_parent"), bool)
        }
        result.append(
            UsageSubagentUsage(
                parent_turn_id=snapshot.turn_id,
                child_id=child_id,
                included_in_parent=included.pop() if len(included) == 1 else None,
                token_usage=UsageTokenUsage(**metrics),
                sources=[_public_source(item) for item in evidence],
            )
        )
    return result
