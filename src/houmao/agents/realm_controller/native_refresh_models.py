"""Versioned public contracts for native-home and common-plugin refresh.

Freshness describes the stated resource scope and boundary. It remains separate
from connection health and from settlement of the native operation.
"""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

Freshness = Literal["current", "pending", "unknown"]
NativeBoundary = Literal["now", "next_step", "next_turn", "next_load", "unknown"]
RefreshOutcome = Literal[
    "already_current",
    "refreshed",
    "automatic",
    "partial",
    "restart_required",
    "busy",
    "unsupported",
    "failed",
    "outcome_unknown",
    "unavailable",
]


def observation_time() -> str:
    """Return an explicit UTC observation timestamp."""

    return datetime.now(UTC).isoformat()


class _StrictModel(BaseModel):
    """Reject unrecognized fields without coercing native authority."""

    model_config = ConfigDict(extra="forbid", strict=True)


class NativeHomeV1(_StrictModel):
    """Describe the native home selected by one active managed runtime."""

    schema_version: Literal[1] = 1
    agent_id: str = Field(min_length=1)
    backend: str = Field(min_length=1)
    tool: str = Field(min_length=1)
    home_dir: str = Field(min_length=1)
    home_env_var: str | None = None
    identity: dict[str, str] = Field(default_factory=dict)


class NativeHomeChangedError(ValueError):
    """Refuse a conditional request whose captured native authority has changed."""


def native_home_etag(home: NativeHomeV1) -> str:
    """Identify public native authority for an HTTP precondition without private material."""

    encoded = json.dumps(home.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return '"houmao-native-' + hashlib.sha256(encoded.encode("utf-8")).hexdigest() + '"'


class CommonPluginResourceV1(_StrictModel):
    """Report one explicit skill/MCP evidence component without private inputs."""

    kind: Literal["skills", "mcp"]
    component: str = Field(min_length=1, max_length=64)
    freshness: Freshness = "unknown"
    boundary: NativeBoundary = "unknown"
    inventory: list[str] = Field(default_factory=list)
    complete: bool = False
    supported: bool = False
    required: bool = True
    health: str = Field(default="unknown", max_length=80)
    reason: str = Field(default="evidence_unavailable", max_length=500)
    evidence: list[str] = Field(default_factory=list)


class CommonPluginObservationV1(_StrictModel):
    """Observe common resources independently of who triggered their update."""

    schema_version: Literal[1] = 1
    home: NativeHomeV1
    observed_at_utc: str = Field(default_factory=observation_time)
    native_version: str | None = None
    profile: str | None = None
    scope: Literal["common-plugin"] = "common-plugin"
    resources: list[CommonPluginResourceV1]
    coverage_complete: bool = False
    freshness: Freshness = "unknown"
    native_reload: bool = False
    automatic: bool = False
    native_settled: bool = True
    native_ready: bool = True

    @model_validator(mode="after")
    def validate_current_coverage(self) -> Self:
        """Prevent partial or unsupported evidence from claiming current scope."""

        required = [resource for resource in self.resources if resource.required]
        if self.freshness == "current" and (
            not self.coverage_complete
            or {resource.kind for resource in required} != {"skills", "mcp"}
            or any(
                resource.freshness != "current" or not resource.complete or not resource.supported
                for resource in required
            )
        ):
            raise ValueError("Current common scope requires complete evidence for skills and MCP")
        return self

    @property
    def automatic_qualified(self) -> bool:
        """Require a supported native future boundary for each remaining kind."""

        required = [resource for resource in self.resources if resource.required]
        return (
            self.automatic
            and {resource.kind for resource in required} == {"skills", "mcp"}
            and all(
                (resource.freshness == "current" and resource.complete and resource.supported)
                or (
                    resource.supported
                    and resource.boundary in {"next_step", "next_turn", "next_load"}
                )
                for resource in required
            )
        )


class NativeRefreshRequestV1(_StrictModel):
    """Request one bounded refresh without installation or restart authority."""

    schema_version: Literal[1] = 1
    timeout_seconds: float = Field(default=30.0, gt=0, le=120, allow_inf_nan=False)


class NativeRefreshResultV1(_StrictModel):
    """Preserve common observations separately from broader native effects."""

    schema_version: Literal[1] = 1
    method: Literal["noop", "automatic", "native_reload", "none"]
    outcome: RefreshOutcome
    observation: CommonPluginObservationV1
    before: CommonPluginObservationV1 | None = None
    effects: Literal["absent", "confirmed", "partial", "unknown"] = "absent"
    native_settled: bool = True
    native_ready: bool = True
    diagnostics: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_success_evidence(self) -> Self:
        """Reject success shaped results with missing freshness or readiness."""

        if self.outcome in {"already_current", "refreshed"} and (
            self.observation.freshness != "current"
            or not self.native_ready
            or not self.native_settled
            or not self.observation.native_ready
            or not self.observation.native_settled
        ):
            raise ValueError("Confirmed refresh requires current evidence and settled readiness")
        if self.outcome == "already_current" and (
            self.method != "noop" or self.effects != "absent"
        ):
            raise ValueError("Already current must be a mutation-free no-op")
        if self.outcome == "automatic" and (
            self.method != "automatic"
            or not self.observation.automatic_qualified
            or self.effects != "absent"
            or not self.native_ready
            or not self.native_settled
            or not self.observation.native_ready
            or not self.observation.native_settled
        ):
            raise ValueError("Automatic results require qualified automatic coverage")
        return self


def native_refresh_status_code(result: NativeRefreshResultV1) -> int:
    """Map a typed common outcome to its HTTP status without dropping evidence."""

    if result.outcome in {"already_current", "refreshed", "automatic"}:
        return 200
    if result.outcome in {"busy", "restart_required"}:
        return 409
    if result.outcome == "unsupported":
        return 501
    return 503


def refresh_guard_can_release(observation: CommonPluginObservationV1) -> bool:
    """Release admission only after native settlement and readiness are known."""

    return observation.native_settled and observation.native_ready
