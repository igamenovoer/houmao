"""Strict accounting records and private collection state for managed agents.

The public models preserve unknown metrics and source provenance. Private
observations and checkpoints retain collection evidence without exposing source
paths or provider conversation content in an HTTP response.
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

UsageAvailability = Literal["available", "partial", "unavailable"]
UsageScope = Literal["request", "turn", "session_cumulative", "unknown"]
UsageSourceKind = Literal["structured_output", "native_session_log", "houmao_runtime"]
UsageOutcome = Literal["completed", "failed", "interrupted"]
UsageCoverage = Literal["complete", "partial", "unknown"]
UsageNumber = int | float

USAGE_SCHEMA_VERSION = 1
DEFAULT_USAGE_PAGE_LIMIT = 100
MAX_USAGE_PAGE_LIMIT = 500

_ACCOUNTING_FIELDS = frozenset(
    {
        "usage",
        "model_usage",
        "modelUsage",
        "token_usage",
        "tokenUsage",
        "cost",
        "input_tokens",
        "output_tokens",
        "cached_input_tokens",
        "cache_write_input_tokens",
        "cache_creation_input_tokens",
        "cache_read_input_tokens",
        "reasoning_output_tokens",
        "reasoning_tokens",
        "total_tokens",
        "prompt_tokens",
        "completion_tokens",
        "prompt_tokens_details",
        "completion_tokens_details",
        "cached_tokens",
        "input",
        "output",
        "cached",
        "cacheRead",
        "cacheWrite",
        "totalTokens",
        "input_other",
        "input_cache_creation",
        "input_cache_read",
        "total",
        "inputOther",
        "inputCacheCreation",
        "inputCacheRead",
        "inputTokens",
        "outputTokens",
        "cacheCreationInputTokens",
        "cacheReadInputTokens",
        "reasoningOutputTokens",
        "cache_creation",
        "ephemeral_5m_input_tokens",
        "ephemeral_1h_input_tokens",
        "total_cost_usd",
        "cost_usd",
        "costUSD",
        "amount",
        "currency",
        "duration_ms",
        "duration_api_ms",
        "duration",
        "api_duration_ms",
        "usageScope",
        "service_tier",
        "speed",
        "model",
        "model_id",
        "provider",
        "total_token_usage",
        "last_token_usage",
        "turn_token_usage",
        "thread_token_usage",
    }
)
_OPAQUE_REFERENCE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_CATEGORICAL_ACCOUNTING_FIELDS = frozenset(
    {"currency", "model", "model_id", "provider", "usageScope", "service_tier", "speed"}
)
_ACCOUNTING_CONTAINERS = frozenset(
    {
        "usage",
        "model_usage",
        "modelUsage",
        "token_usage",
        "tokenUsage",
        "cost",
        "prompt_tokens_details",
        "completion_tokens_details",
        "cache_creation",
        "total_token_usage",
        "last_token_usage",
        "turn_token_usage",
        "thread_token_usage",
    }
)


def sanitize_accounting_evidence(value: dict[str, Any]) -> dict[str, Any]:
    """Project recognized accounting fields, excluding conversation and secrets."""

    def project(item: Any, field: str | None = None) -> Any:
        """Keep finite JSON scalars and allowlisted nested accounting objects."""

        if isinstance(item, dict):
            if field is not None and field not in _ACCOUNTING_CONTAINERS:
                return None
            return {
                key: project(child, key)
                for key, child in item.items()
                if isinstance(key, str) and key in _ACCOUNTING_FIELDS
            }
        if isinstance(item, list):
            return None
        if isinstance(item, str):
            if field not in _CATEGORICAL_ACCOUNTING_FIELDS:
                return None
            if field == "currency":
                return item if re.fullmatch(r"[A-Z]{3}", item) else None
            return item if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}", item) else None
        if isinstance(item, bool):
            return None
        if isinstance(item, float) and not math.isfinite(item):
            return None
        if item is None or isinstance(item, (str, int, float, bool)):
            return item
        return None

    result = project(value)
    assert isinstance(result, dict)
    return result


def opaque_usage_reference(value: str) -> str:
    """Return a stable public reference without revealing a private locator."""

    return "source-" + hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


class _UsageModel(BaseModel):
    """Common strict validation for usage boundary and persistence objects."""

    model_config = ConfigDict(extra="forbid", strict=True, validate_assignment=True)


class UsageProvenance(_UsageModel):
    """Origin and evidence supporting one reported or derived measurement."""

    method: Literal["reported", "derived"] = "reported"
    rule: str | None = None
    source_ids: list[str] = Field(default_factory=list)


class UsageMetric(_UsageModel):
    """One measurement with explicit units and availability."""

    value: UsageNumber | None = None
    unit: str = "tokens"
    availability: UsageAvailability = "unavailable"
    measurement_scope: UsageScope = "turn"
    provenance: UsageProvenance | None = None

    @field_validator("value")
    @classmethod
    def _validate_value(cls, value: UsageNumber | None) -> UsageNumber | None:
        """Reject negative and non-finite measurements."""

        if value is not None and (value < 0 or not math.isfinite(value)):
            raise ValueError("Usage measurements must be finite and nonnegative")
        return value

    @model_validator(mode="after")
    def _validate_availability(self) -> Self:
        """Keep missing measurements distinct from measured zero."""

        if self.availability == "unavailable" and self.value is not None:
            raise ValueError("Unavailable usage must have a null value")
        if self.availability != "unavailable" and self.value is None:
            raise ValueError("Available or partial usage requires a value")
        if self.value is not None and self.provenance is None:
            raise ValueError("Measured usage requires provenance")
        return self

    @classmethod
    def reported(
        cls,
        value: UsageNumber | None,
        *,
        unit: str = "tokens",
        source_ids: list[str] | None = None,
        measurement_scope: UsageScope = "turn",
        partial: bool = False,
    ) -> Self:
        """Build a reported measurement, preserving absent values as unavailable."""

        return cls(
            value=value,
            unit=unit,
            availability="unavailable" if value is None else "partial" if partial else "available",
            measurement_scope=measurement_scope,
            provenance=None
            if value is None
            else UsageProvenance(method="reported", source_ids=source_ids or []),
        )

    @classmethod
    def derived(
        cls,
        value: UsageNumber,
        *,
        rule: str,
        unit: str = "tokens",
        source_ids: list[str] | None = None,
        measurement_scope: UsageScope = "turn",
        partial: bool = False,
    ) -> Self:
        """Build a measurement with an explicit derivation rule."""

        return cls(
            value=value,
            unit=unit,
            availability="partial" if partial else "available",
            measurement_scope=measurement_scope,
            provenance=UsageProvenance(method="derived", rule=rule, source_ids=source_ids or []),
        )


class UsageTokenUsage(_UsageModel):
    """Turn counters whose unavailable defaults never imply zero usage."""

    input_tokens: UsageMetric = Field(default_factory=UsageMetric)
    output_tokens: UsageMetric = Field(default_factory=UsageMetric)
    cached_input_tokens: UsageMetric = Field(default_factory=UsageMetric)
    cache_write_input_tokens: UsageMetric = Field(default_factory=UsageMetric)
    reasoning_output_tokens: UsageMetric = Field(default_factory=UsageMetric)
    total_tokens: UsageMetric = Field(default_factory=UsageMetric)


class UsageTokenSemantics(_UsageModel):
    """Provider-established inclusion relationships between token counters."""

    cached_input_included_in_input: bool | None = None
    cache_write_included_in_input: bool | None = None
    reasoning_included_in_output: bool | None = None


class UsageProviderTiming(_UsageModel):
    """Provider-reported timing, separate from runtime wall time."""

    duration_ms: UsageMetric = Field(default_factory=lambda: UsageMetric(unit="milliseconds"))
    duration_api_ms: UsageMetric = Field(default_factory=lambda: UsageMetric(unit="milliseconds"))


class UsageCost(_UsageModel):
    """A provider-reported monetary measurement with explicit currency."""

    amount: UsageMetric = Field(default_factory=lambda: UsageMetric(unit="currency"))
    currency: str | None = None

    @model_validator(mode="after")
    def _validate_currency(self) -> Self:
        """Require a currency when an amount is available."""

        if self.amount.value is not None and not self.currency:
            raise ValueError("A measured cost requires an explicit currency")
        return self


class UsageSource(_UsageModel):
    """Public accounting-only source evidence and opaque provenance."""

    source_id: str
    observation_id: str | None = None
    source_kind: UsageSourceKind
    source_ref: str
    profile_id: str = "unknown"
    provider_event_type: str | None = None
    provider_version: str | None = None
    measurement_scope: UsageScope = "unknown"
    accounting: dict[str, Any] = Field(default_factory=dict)

    @field_validator("source_ref")
    @classmethod
    def _validate_reference(cls, value: str) -> str:
        """Keep paths, URLs, and credential-bearing locators out of public data."""

        if not _OPAQUE_REFERENCE.fullmatch(value):
            raise ValueError("Usage source references must be opaque identifiers")
        return value

    @field_validator("accounting")
    @classmethod
    def _sanitize_accounting(cls, value: dict[str, Any]) -> dict[str, Any]:
        """Allow only explicitly recognized accounting evidence."""

        return sanitize_accounting_evidence(value)


class UsageObservation(_UsageModel):
    """Private scoped evidence staged before immutable turn assembly."""

    observation_id: str
    provider: str
    provider_session_id: str | None = None
    provider_turn_id: str | None = None
    request_id: str | None = None
    turn_id: str | None = None
    binding_id: str | None = None
    source_kind: UsageSourceKind = "native_session_log"
    source_ref: str = "unknown"
    profile_id: str = "unknown"
    provider_event_type: str | None = None
    provider_version: str | None = None
    kind: Literal["request", "summary", "cumulative", "lifecycle"] = "request"
    accounting_kind: str | None = None
    measurement_scope: UsageScope = "unknown"
    values: dict[str, UsageNumber | None] = Field(default_factory=dict)
    token_semantics: UsageTokenSemantics = Field(default_factory=UsageTokenSemantics)
    accounting: dict[str, Any] = Field(default_factory=dict)
    lifecycle: Literal["started", "completed", "failed", "interrupted"] | None = None
    timestamp_utc: str | None = None
    model: str | None = None
    parent_turn_id: str | None = None
    is_sidechain: bool = False
    coverage: UsageCoverage = "unknown"
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("values")
    @classmethod
    def _validate_values(
        cls, values: dict[str, UsageNumber | None]
    ) -> dict[str, UsageNumber | None]:
        """Reject invalid counters without inventing replacements."""

        if any(
            value is not None and (value < 0 or not math.isfinite(value))
            for value in values.values()
        ):
            raise ValueError("Observed measurements must be finite and nonnegative")
        return values

    @field_validator("accounting")
    @classmethod
    def _sanitize_accounting(cls, value: dict[str, Any]) -> dict[str, Any]:
        """Avoid staging conversation content alongside accounting observations."""

        return sanitize_accounting_evidence(value)


class UsageIdentity(_UsageModel):
    """Stable agent, runtime, and accounting-turn identity."""

    agent_id: str
    runtime_session_id: str
    turn_id: str
    backend: str
    provider: str
    generation_id: str | None = None
    provider_session_id: str | None = None
    provider_turn_id: str | None = None
    turn_origin: Literal["managed", "native_observed"] = "managed"
    turn_index: int | None = Field(default=None, ge=0)

    @field_validator("agent_id", "runtime_session_id", "turn_id", "backend", "provider")
    @classmethod
    def _validate_identity(cls, value: str) -> str:
        """Reject empty accounting identities."""

        if not value.strip():
            raise ValueError("Usage identities must not be empty")
        return value


class UsageSourceBinding(_UsageModel):
    """Private durable ownership and attachment boundary for one source family."""

    binding_id: str
    agent_id: str
    runtime_session_id: str
    provider: str
    home_path: str
    provider_session_id: str | None = None
    generation_id: str | None = None
    profile_id: str = "unknown"
    counter_epoch: str = "initial"
    started_at_utc: str | None = None
    collection_boundary: dict[str, int] = Field(default_factory=dict)
    baseline: dict[str, UsageNumber | None] = Field(default_factory=dict)
    provisional: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class UsageCheckpoint(_UsageModel):
    """Private complete-record source position used for transactional ingestion."""

    binding_id: str
    source_id: str
    file_identity: str
    offset: int = Field(default=0, ge=0)
    version: int = Field(default=0, ge=0)
    counter_epoch: str = "initial"
    baseline: dict[str, UsageNumber | None] = Field(default_factory=dict)
    diagnostics: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class UsageTurnSnapshot(UsageIdentity):
    """Private turn-start identity and source boundaries used during recovery."""

    started_at_utc: str | None = None
    binding_id: str | None = None
    source_positions: dict[str, int] = Field(default_factory=dict)
    baseline: dict[str, UsageNumber | None] = Field(default_factory=dict)
    counter_epoch: str | None = None
    coverage: UsageCoverage = "unknown"
    metadata: dict[str, Any] = Field(default_factory=dict)


class UsageFinalization(_UsageModel):
    """Durable terminal facts and evidence cutoff for one pending turn."""

    turn_id: str
    outcome: UsageOutcome
    completed_at_utc: str | None = None
    wall_time_ms: UsageNumber | None = Field(default=None, ge=0)
    returncode: int | None = None
    interrupted: bool = False
    source_positions: dict[str, int] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class UsagePendingTurn(_UsageModel):
    """Private staged turn state, retained after its final row is committed."""

    snapshot: UsageTurnSnapshot
    finalization: UsageFinalization | None = None
    finalized: bool = False


class UsageSubagentUsage(_UsageModel):
    """Provider-associated child measurements that retain overlap semantics."""

    parent_turn_id: str
    child_id: str
    included_in_parent: bool | None = None
    token_usage: UsageTokenUsage = Field(default_factory=UsageTokenUsage)
    sources: list[UsageSource] = Field(default_factory=list)


class UsageRecord(UsageIdentity):
    """One immutable finalized accounting turn in the public usage stream."""

    schema_version: Literal[1] = 1
    record_id: str = ""
    outcome: UsageOutcome
    started_at_utc: str | None = None
    completed_at_utc: str | None = None
    token_usage: UsageTokenUsage = Field(default_factory=UsageTokenUsage)
    token_semantics: UsageTokenSemantics = Field(default_factory=UsageTokenSemantics)
    wall_time_ms: UsageMetric = Field(default_factory=lambda: UsageMetric(unit="milliseconds"))
    provider_timing: UsageProviderTiming = Field(default_factory=UsageProviderTiming)
    cost: UsageCost = Field(default_factory=UsageCost)
    subagent_accounting: Literal["included", "separate", "excluded", "unknown"] = "unknown"
    subagent_usage: list[UsageSubagentUsage] = Field(default_factory=list)
    sources: list[UsageSource] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_record_id(self) -> Self:
        """Use deterministic record identity during normal and recovery writes."""

        expected = f"usage-v1:{self.runtime_session_id}:{self.turn_id}"
        if self.record_id and self.record_id != expected:
            raise ValueError("Usage record ID does not match its turn identity")
        object.__setattr__(self, "record_id", expected)
        return self


class UsageCapability(_UsageModel):
    """Evidence-based current collection capability, independent of history."""

    status: UsageAvailability = "unavailable"
    turn_recording: bool = False
    source_kinds: list[UsageSourceKind] = Field(default_factory=list)
    observed_scopes: list[UsageScope] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class UsageCollectionHealth(_UsageModel):
    """Safe collection health and freshness information returned with pages."""

    status: Literal["healthy", "degraded", "unavailable"] = "healthy"
    updated_at_utc: str | None = None
    diagnostics: list[str] = Field(default_factory=list)


class UsagePage(_UsageModel):
    """Bounded finalized history with an end cursor suitable for later polling."""

    schema_version: Literal[1] = 1
    runtime_session_id: str | None = None
    stream_id: str | None = None
    capability: UsageCapability = Field(default_factory=UsageCapability)
    collection: UsageCollectionHealth = Field(default_factory=UsageCollectionHealth)
    records: list[UsageRecord] = Field(default_factory=list)
    next_cursor: str | None = None
    has_more: bool = False


class UsageCursor(_UsageModel):
    """Validated internal representation of an opaque finalization cursor."""

    version: Literal[1] = 1
    stream_id: str
    sequence: int = Field(ge=0)
