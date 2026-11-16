"""Typed data boundaries used by the independent CCCC protocol client."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, JsonValue, TypeAdapter

JSON_OBJECT = TypeAdapter(dict[str, JsonValue])


class ProviderBinding(BaseModel):
    """Describe the provider-authenticated Actor registration."""

    model_config = ConfigDict(extra="ignore", strict=True, frozen=True)

    protocol_version: int
    group_id: str
    actor_id: str
    actor_generation: str


class ReceiverLease(BaseModel):
    """Describe an ephemeral intake lease, without persisted resume authority."""

    model_config = ConfigDict(extra="ignore", strict=True, frozen=True)

    lease_id: str = Field(min_length=1)
    lease_generation: int | str
    expires_in_seconds: float | int = Field(gt=0)
