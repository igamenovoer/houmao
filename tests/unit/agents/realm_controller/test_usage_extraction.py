"""Scope, duplication, provenance, and missing-value accounting regressions."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from houmao.agents.realm_controller.usage_adapters import UsageAdapter, parse_usage_payload
from houmao.agents.realm_controller.usage_extraction import assemble_usage_record
from houmao.agents.realm_controller.usage_models import (
    UsageObservation,
    UsageTokenSemantics,
    UsageTurnSnapshot,
)


def _snapshot(provider: str = "codex", **changes) -> UsageTurnSnapshot:
    """Construct a fully associated test turn with complete collection coverage."""

    return UsageTurnSnapshot(
        agent_id="agent",
        runtime_session_id="runtime",
        turn_id="managed-turn",
        backend=f"{provider}_headless",
        provider=provider,
        coverage="complete",
        **changes,
    )


def _observation(key: str, values: dict, **changes) -> UsageObservation:
    """Create qualified test evidence without source conversation content."""

    return UsageObservation(
        observation_id=key,
        provider="codex",
        request_id=key,
        values=values,
        source_ref=key,
        measurement_scope="request",
        coverage="complete",
        token_semantics=UsageTokenSemantics(
            cached_input_included_in_input=True,
            cache_write_included_in_input=True,
            reasoning_included_in_output=True,
        ),
        **changes,
    )


def test_request_copies_are_counted_once_and_all_evidence_remains_visible() -> None:
    first = _observation(
        "response",
        {
            "input_tokens": 1000,
            "output_tokens": 100,
            "cached_input_tokens": 700,
            "reasoning_output_tokens": 40,
        },
    )
    copy = first.model_copy(update={"source_kind": "structured_output", "source_ref": "stdout"})
    record = assemble_usage_record(_snapshot(), [first, copy], outcome="completed")
    assert record.token_usage.input_tokens.value == 1000
    assert record.token_usage.total_tokens.value == 1100
    assert record.token_usage.total_tokens.provenance.method == "derived"
    assert len(record.sources) == 2


def test_summary_is_not_added_to_its_constituent_request() -> None:
    request = _observation("request", {"input_tokens": 100, "output_tokens": 20})
    summary = _observation("summary", {"input_tokens": 100, "output_tokens": 20}, kind="summary")
    summary.measurement_scope = "turn"
    record = assemble_usage_record(_snapshot(), [request, summary], outcome="completed")
    assert record.token_usage.input_tokens.value == 100


def test_verified_cumulative_baselines_yield_1000_then_600() -> None:
    records = []
    for baseline, total in ((0, 1000), (1000, 1600)):
        obs = _observation("total", {"total_tokens": total}, kind="cumulative")
        obs.measurement_scope = "session_cumulative"
        records.append(
            assemble_usage_record(
                _snapshot(baseline={"total_tokens": baseline}), [obs], outcome="completed"
            )
        )
    assert [r.token_usage.total_tokens.value for r in records] == [1000, 600]
    assert all(r.token_usage.total_tokens.provenance.method == "derived" for r in records)


def test_incomplete_native_cumulative_endpoint_remains_partial() -> None:
    """A final collection budget cannot promote a prefix endpoint to complete usage."""

    obs = _observation("total", {"total_tokens": 1600}, kind="cumulative").model_copy(
        update={"measurement_scope": "session_cumulative", "coverage": "partial"}
    )
    record = assemble_usage_record(
        _snapshot(baseline={"total_tokens": 1000}), [obs], outcome="completed"
    )
    assert record.token_usage.total_tokens.value == 600
    assert record.token_usage.total_tokens.availability == "partial"


@pytest.mark.parametrize(
    "baseline,total,reason",
    [
        ({}, 100, "missing_cumulative_baseline"),
        ({"total_tokens": 200}, 100, "cumulative_counter_decreased"),
    ],
)
def test_unverified_or_decreasing_cumulative_totals_remain_unavailable(
    baseline, total, reason
) -> None:
    obs = _observation("total", {"total_tokens": total}, kind="cumulative")
    obs.measurement_scope = "session_cumulative"
    record = assemble_usage_record(_snapshot(baseline=baseline), [obs], outcome="completed")
    assert record.token_usage.total_tokens.value is None
    assert reason in record.diagnostics


def test_cross_epoch_baseline_does_not_produce_a_delta() -> None:
    obs = _observation(
        "total", {"total_tokens": 100}, kind="cumulative", metadata={"counter_epoch": "reset"}
    )
    obs.measurement_scope = "session_cumulative"
    record = assemble_usage_record(
        _snapshot(baseline={"total_tokens": 0}, counter_epoch="old"), [obs], outcome="completed"
    )
    assert record.token_usage.total_tokens.value is None
    assert "incomparable_cumulative_epoch" in record.diagnostics


def test_missing_metric_and_reported_zero_are_distinct() -> None:
    obs = _observation(
        "response", {"input_tokens": 10, "output_tokens": 2, "cached_input_tokens": 0}
    )
    record = assemble_usage_record(_snapshot(), [obs], outcome="completed")
    assert record.token_usage.cached_input_tokens.value == 0
    assert record.token_usage.cache_write_input_tokens.value is None
    assert record.cost.amount.value is None


def test_interruption_preserves_reported_partial_usage_and_runtime_timing() -> None:
    obs = _observation("response", {"input_tokens": 10, "output_tokens": 2})
    record = assemble_usage_record(
        _snapshot(),
        [obs],
        outcome="interrupted",
        completed_at_utc="2026-11-13T00:01:00Z",
        wall_time_ms=1000,
    )
    assert record.token_usage.input_tokens.availability == "partial"
    assert record.wall_time_ms.value == 1000
    assert record.completed_at_utc == "2026-11-13T00:01:00Z"


def test_conflicting_complete_variants_do_not_choose_larger_charge() -> None:
    first = _observation("same", {"input_tokens": 10, "output_tokens": 2})
    other = first.model_copy(
        update={"values": {"input_tokens": 100, "output_tokens": 2}, "source_ref": "copy"}
    )
    record = assemble_usage_record(_snapshot(), [first, other], outcome="completed")
    assert record.token_usage.input_tokens.value is None
    assert record.token_usage.output_tokens.value == 2
    assert "conflicting_request_evidence" in record.diagnostics


def test_unknown_token_inclusion_prevents_total_derivation() -> None:
    obs = _observation("response", {"input_tokens": 10, "output_tokens": 2})
    obs.token_semantics = UsageTokenSemantics()
    record = assemble_usage_record(_snapshot(), [obs], outcome="completed")
    assert record.token_usage.total_tokens.value is None


def test_parent_sidechain_copy_does_not_replace_parent_accounting() -> None:
    first = parse_usage_payload(
        "claude",
        {
            "type": "assistant",
            "sessionId": "session",
            "message": {
                "id": "msg_parent",
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 10, "output_tokens": 2},
            },
        },
        source_ref="parent",
    )[0]
    replay = first.model_copy(
        update={
            "is_sidechain": True,
            "values": {"input_tokens": 999, "output_tokens": 2},
            "source_ref": "sidechain",
        }
    )
    record = assemble_usage_record(_snapshot("claude"), [first, replay], outcome="completed")
    assert record.token_usage.input_tokens.value == 10


def test_linked_child_breakdown_does_not_add_included_usage_to_parent() -> None:
    parent = _observation("parent", {"input_tokens": 100, "output_tokens": 20})
    child = _observation(
        "child",
        {"input_tokens": 25, "output_tokens": 5},
        parent_turn_id="managed-turn",
        provider_turn_id="child-turn",
        metadata={"included_in_parent": True},
    )
    record = assemble_usage_record(_snapshot(), [parent, child], outcome="completed")
    assert record.token_usage.input_tokens.value == 100
    assert record.subagent_accounting == "separate"
    assert record.subagent_usage[0].token_usage.input_tokens.value == 25
    assert record.subagent_usage[0].included_in_parent is True


def test_public_sources_exclude_full_provider_event_content() -> None:
    obs = parse_usage_payload(
        "claude",
        {
            "type": "result",
            "result": "PRIVATE RESPONSE",
            "api_key": "PRIVATE KEY",
            "usage": {"input_tokens": 10, "output_tokens": 2},
        },
        source_ref="/private/user/session.jsonl",
    )[0]
    record = assemble_usage_record(_snapshot("claude"), [obs], outcome="completed")
    raw = record.model_dump_json()
    assert "PRIVATE" not in raw
    assert "/private" not in raw


@pytest.mark.parametrize("provider", ["claude", "codex", "kimi"])
def test_real_two_turn_capture_assembles_native_requests_without_replay(provider: str) -> None:
    root = Path(__file__).parents[3] / "fixtures" / "agent-usage-records"
    fixture = json.loads(next(root.glob(f"{provider}-*-qwen.json")).read_text())
    adapter = UsageAdapter.from_provider(provider, fixture["provider_session_id"])
    evidence = [
        item
        for raw in fixture["native_records"]
        for item in adapter.parse(raw, source_ref="native")
    ]
    turn_keys = list(
        dict.fromkeys(item.provider_turn_id for item in evidence if item.lifecycle == "started")
    )
    records = [
        assemble_usage_record(
            _snapshot(
                provider, provider_session_id=fixture["provider_session_id"], provider_turn_id=turn
            ),
            evidence,
            outcome="completed",
        )
        for turn in turn_keys
    ]
    assert len(records) == 2
    assert all(record.token_usage.input_tokens.value > 0 for record in records)
    assert all(record.token_usage.output_tokens.value > 0 for record in records)
    if provider == "codex":
        final = fixture["headless_turns"][-1][-1]["usage"]
        assert (
            sum(record.token_usage.input_tokens.value for record in records)
            == final["input_tokens"]
        )
        assert (
            sum(record.token_usage.output_tokens.value for record in records)
            == final["output_tokens"]
        )
    if provider == "kimi":
        assert all(record.token_usage.cached_input_tokens.value is None for record in records)
        assert all(record.token_usage.total_tokens.value is None for record in records)


def test_claude_resumed_cost_and_api_duration_use_session_baselines() -> None:
    root = Path(__file__).parents[3] / "fixtures" / "agent-usage-records"
    fixture = json.loads(next(root.glob("claude-*-qwen.json")).read_text())
    adapter = UsageAdapter.from_provider("claude", fixture["provider_session_id"])
    first = fixture["headless_turns"][0][-1]
    second = fixture["headless_turns"][1][-1]
    evidence = [
        item
        for payload in fixture["headless_turns"][1]
        for item in adapter.parse(payload, source_ref="stdout", source_kind="structured_output")
    ]
    snapshot = _snapshot(
        "claude",
        baseline={"cost_usd": first["total_cost_usd"], "duration_api_ms": first["duration_api_ms"]},
    )
    record = assemble_usage_record(snapshot, evidence, outcome="completed")
    assert record.cost.amount.value == pytest.approx(
        second["total_cost_usd"] - first["total_cost_usd"]
    )
    assert record.cost.amount.provenance.method == "derived"
    assert (
        record.provider_timing.duration_api_ms.value
        == second["duration_api_ms"] - first["duration_api_ms"]
    )
    assert record.provider_timing.duration_ms.value == second["duration_ms"]


def test_two_requests_with_identical_counters_are_both_counted() -> None:
    first = _observation("response-a", {"input_tokens": 10, "output_tokens": 2})
    second = _observation("response-b", {"input_tokens": 10, "output_tokens": 2})
    record = assemble_usage_record(_snapshot(), [first, second], outcome="completed")
    assert record.token_usage.input_tokens.value == 20
    assert record.token_usage.output_tokens.value == 4


def test_cumulative_provenance_references_both_endpoints() -> None:
    obs = _observation("total", {"total_tokens": 1600}, kind="cumulative")
    obs.measurement_scope = "session_cumulative"
    snapshot = _snapshot(
        baseline={"total_tokens": 1000},
        metadata={"baseline_source_ids": {"total_tokens": ["source-baseline"]}},
    )
    record = assemble_usage_record(snapshot, [obs], outcome="completed")
    sources = record.token_usage.total_tokens.provenance.source_ids
    assert "source-baseline" in sources
    assert len(sources) == 2
