"""Validated gateway deployment settings and public endpoint metadata."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from houmao.gateway.access import (
    GatewayTarget,
    validate_gateway_base_url as validate_gateway_base_url,
)


def validate_gateway_access_config_path(value: object) -> str:
    """Validate the lexical owner path without opening it in the caller context."""

    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > 4096
        or ".." in Path(value).parts
        or any(ord(c) < 32 for c in value)
    ):
        raise ValueError("Invalid gateway access configuration path.")
    return value


def owner_gateway_base_url(port: int) -> str:
    """Build the owner-local connect URL independently of the bind host."""

    if not 1 <= port <= 65535:
        raise ValueError("Gateway port must be resolved before use.")
    return f"http://127.0.0.1:{port}"


class GatewayDeployment(BaseModel):
    """Owner-selected bind, public-input and advertisement settings."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, hide_input_in_errors=True)

    schema_version: Literal[1] = 1
    bind_host: Literal["127.0.0.1", "0.0.0.0"] = "127.0.0.1"
    bind_port: int | None = Field(default=None, ge=1, le=65535)
    public_input_enabled: bool = False
    advertised_url: str | None = None
    admin_signer_path: str | None = Field(default=None, repr=False)

    @field_validator("advertised_url")
    @classmethod
    def _validate_advertised_url(cls, value: str | None) -> str | None:
        """Require a deployable, exact advertised base URL."""

        return None if value is None else validate_gateway_base_url(value)

    @field_validator("admin_signer_path")
    @classmethod
    def _validate_admin_signer_path(cls, value: str | None) -> str | None:
        """Require an explicit owner-local path for the selected signer."""

        if value is not None and (not Path(value).is_absolute() or any(ord(c) < 32 for c in value)):
            raise ValueError("Gateway admin signer path must be absolute.")
        return value


class GatewayEndpointDescriptor(BaseModel):
    """Publish a live endpoint and its access requirements without credentials."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, hide_input_in_errors=True)

    protocol: str
    target: GatewayTarget
    presence_id: str
    advertised_url: str | None
    admin_access: Literal["open", "key_required", "unavailable"]
    private_proof: Literal["none", "self_or_admin", "unavailable"] = "self_or_admin"
    public_operations: tuple[Literal["messages", "public_prompt"], ...] = ()

    _validate_advertised_url = field_validator("advertised_url")(
        GatewayDeployment._validate_advertised_url
    )

    @field_validator("public_operations", mode="before")
    @classmethod
    def _operations_tuple(cls, value: object) -> object:
        """Accept JSON arrays through dictionary-based boundary loaders."""

        return tuple(value) if isinstance(value, list) else value
