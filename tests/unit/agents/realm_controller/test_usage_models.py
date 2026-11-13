"""Contract tests for strict provider-faithful accounting models."""

from __future__ import annotations

import math

import pytest
from pydantic import ValidationError

from houmao.agents.realm_controller.usage_models import (
    UsageCapability,
    UsageIdentity,
    UsageMetric,
    UsageObservation,
    UsagePage,
    UsageRecord,
    UsageSource,
    UsageTokenSemantics,
    UsageTokenUsage,
    opaque_usage_reference,
)


def _identity() -> UsageIdentity:
    """Build a stable example identity without provider credentials."""

    return UsageIdentity(
        agent_id="agent-a",
        runtime_session_id="runtime-a",
        turn_id="turn-a",
        backend="codex_headless",
        provider="codex",
        generation_id="generation-a",
    )


def test_missing_measurement_is_not_reported_zero() -> None:
    """Preserve explicit zero independently of omitted fields."""

    usage = UsageTokenUsage(cached_input_tokens=UsageMetric.reported(0))
    assert usage.cached_input_tokens.value == 0
    assert usage.cached_input_tokens.availability == "available"
    assert usage.cached_input_tokens.provenance is not None
    assert usage.cached_input_tokens.provenance.method == "reported"
    assert usage.output_tokens.value is None
    assert usage.output_tokens.availability == "unavailable"
    assert usage.output_tokens.provenance is None


@pytest.mark.parametrize("value", [True, -1, math.inf, math.nan, "100"])
def test_invalid_values_are_rejected(value: object) -> None:
    """Reject coercion and invalid counter values rather than replacing them."""

    with pytest.raises(ValidationError):
        UsageMetric.model_validate(
            {"value": value, "availability": "available", "provenance": {"method": "reported"}}
        )


def test_measured_value_requires_valid_availability_and_provenance() -> None:
    """Require a measurement's value and provenance to agree with its status."""

    with pytest.raises(ValidationError):
        UsageMetric(value=1)
    with pytest.raises(ValidationError):
        UsageMetric(availability="available")
    with pytest.raises(ValidationError):
        UsageMetric(value=1, availability="available")


def test_derived_delta_keeps_rule_and_endpoints() -> None:
    """A derived value remains distinguishable from a provider report."""

    metric = UsageMetric.derived(
        600, rule="same-epoch-cumulative-delta", source_ids=["before", "after"]
    )
    assert metric.value == 600
    assert metric.provenance is not None
    assert metric.provenance.method == "derived"
    assert metric.provenance.rule == "same-epoch-cumulative-delta"
    assert metric.provenance.source_ids == ["before", "after"]


def test_token_overlap_remains_explicit_without_automatic_summing() -> None:
    """Subset measurements do not silently become an invented total."""

    usage = UsageTokenUsage(
        input_tokens=UsageMetric.reported(1000),
        cached_input_tokens=UsageMetric.reported(700),
        output_tokens=UsageMetric.reported(100),
        reasoning_output_tokens=UsageMetric.reported(40),
    )
    semantics = UsageTokenSemantics(
        cached_input_included_in_input=True, reasoning_included_in_output=True
    )
    assert usage.total_tokens.value is None
    assert semantics.cached_input_included_in_input is True
    assert semantics.cache_write_included_in_input is None


def test_records_have_stable_versioned_identity_and_origin() -> None:
    """Managed and observed origins share deterministic record identities."""

    identity = _identity()
    record = UsageRecord(**identity.model_dump(), outcome="completed")
    assert record.record_id == "usage-v1:runtime-a:turn-a"
    observed = UsageRecord(
        **{**identity.model_dump(), "turn_origin": "native_observed"}, outcome="interrupted"
    )
    assert observed.turn_origin == "native_observed"
    with pytest.raises(ValidationError):
        UsageRecord(**identity.model_dump(), outcome="completed", record_id="another-turn")
    with pytest.raises(ValidationError):
        UsageIdentity(**{**identity.model_dump(), "turn_id": " "})


def test_public_source_evidence_is_allowlisted() -> None:
    """Nested prompt, tool, path, and credential fields never pass through."""

    source = UsageSource(
        source_id="source-a",
        source_kind="structured_output",
        source_ref="canonical:7",
        accounting={
            "usage": {
                "input_tokens": 20,
                "output_tokens": 4,
                "api_key": "private",
                "prompt": "private",
                "tool": {"content": "private"},
            },
            "total_cost_usd": 0.1,
            "credential": "private",
            "path": "/private/source",
            "response": "private",
        },
    )
    assert source.accounting == {
        "usage": {"input_tokens": 20, "output_tokens": 4},
        "total_cost_usd": 0.1,
    }
    assert "private" not in source.model_dump_json()
    with pytest.raises(ValidationError):
        UsageSource(
            source_id="source-a",
            source_kind="native_session_log",
            source_ref="/private/source.jsonl",
        )
    assert opaque_usage_reference("/private/source.jsonl").startswith("source-")


def test_invalid_numeric_evidence_cannot_leak_private_strings() -> None:
    """Allowlisted names do not make arbitrary counter strings public evidence."""

    source = UsageSource(
        source_id="source-a",
        source_kind="structured_output",
        source_ref="canonical:1",
        accounting={
            "usage": {
                "input_tokens": 20,
                "cached_input_tokens": "private prompt",
                "output_tokens": {"currency": "private"},
            },
            "model": "Qwen/Qwen3.8-27B-FP8",
            "duration_ms": "private response",
            "currency": "USD",
            "service_tier": "standard",
        },
    )
    assert source.accounting["usage"]["input_tokens"] == 20
    assert source.accounting["usage"]["cached_input_tokens"] is None
    assert source.accounting["usage"]["output_tokens"] is None
    assert source.accounting["model"] == "Qwen/Qwen3.8-27B-FP8"
    assert "private" not in source.model_dump_json()


def test_observation_keeps_lifecycle_and_scope_separate() -> None:
    """An empty lifecycle observation does not imply zero token usage."""

    observation = UsageObservation(
        observation_id="event-a",
        provider="codex",
        provider_turn_id="native-turn",
        kind="lifecycle",
        accounting_kind="turn_completed",
        lifecycle="completed",
    )
    assert observation.values == {}
    assert observation.measurement_scope == "unknown"


def test_session_evidence_does_not_enable_turn_recording() -> None:
    """Capability describes source scope independently of finalized rows."""

    page = UsagePage(
        capability=UsageCapability(
            status="partial",
            observed_scopes=["session_cumulative"],
            reasons=["turn_association_unavailable"],
        )
    )
    assert page.capability.turn_recording is False
    assert page.records == []
    with pytest.raises(ValidationError):
        UsageCapability.model_validate({"status": "available", "invented": True})
