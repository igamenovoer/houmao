"""Strict, immutable CCCC connection and selected-credential configuration."""

from __future__ import annotations

import ipaddress
import json
from urllib.parse import urlsplit, urlunsplit

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator

from houmao_cccc.delivery import DeliverySettings

MAIL_DEFAULT_LIMIT = 50
MAIL_MAX_LIMIT = 200
MAIL_DEFAULT_BYTES = 262144
MAIL_MAX_BYTES = 1048576


def normalize_endpoint(value: str, *, loopback_only: bool = False) -> str:
    """Normalize a credential-free endpoint and enforce its transport boundary."""

    try:
        parsed = urlsplit(value)
        host = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Invalid service endpoint") from exc
    if (
        parsed.scheme not in {"http", "https"}
        or not host
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or "\\" in value
        or any(part in {".", ".."} for part in parsed.path.split("/"))
        or "%" in parsed.path
    ):
        raise ValueError("Endpoint must be an absolute credential-free HTTP(S) URL")
    try:
        local = ipaddress.ip_address(host).is_loopback
    except ValueError:
        local = host.lower() == "localhost"
    if loopback_only and not local:
        raise ValueError("Gateway URL must use a loopback address")
    if not local and parsed.scheme != "https":
        raise ValueError("Remote CCCC endpoints require HTTPS")
    authority = f"[{host.lower()}]" if ":" in host else host.lower()
    if port is not None:
        authority += f":{port}"
    return urlunsplit((parsed.scheme, authority, parsed.path.rstrip("/"), "", ""))


class CcccConfiguration(BaseModel):
    """Select one provisioned Actor registration and finite transport budgets."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, allow_inf_nan=False)

    endpoint: str = Field(min_length=1, max_length=2048)
    group_id: str = Field(min_length=1, max_length=256)
    actor_id: str = Field(min_length=1, max_length=256)
    actor_generation: str = Field(min_length=1, max_length=256)
    request_timeout_seconds: float = Field(default=10.0, gt=0, le=60)
    poll_timeout_seconds: float = Field(default=20.0, gt=0, le=20)
    reconnect_delay_seconds: float = Field(default=1.0, gt=0, le=30)
    renew_interval_seconds: float = Field(default=10.0, gt=0, le=20)
    max_response_bytes: int = Field(default=262144, ge=1024, le=1048576)
    max_event_bytes: int = Field(default=65536, ge=1024, le=65536)
    history_limit: int = Field(default=50, ge=1, le=100)
    mail_limit: int = Field(default=MAIL_DEFAULT_LIMIT, ge=1, le=MAIL_MAX_LIMIT)
    mail_max_bytes: int = Field(default=MAIL_DEFAULT_BYTES, ge=1024, le=MAIL_MAX_BYTES)
    delivery: DeliverySettings = Field(default_factory=DeliverySettings)

    @field_validator("endpoint")
    @classmethod
    def _endpoint(cls, value: str) -> str:
        """Reject credentials, redirects, and insecure remote endpoints."""

        return normalize_endpoint(value)

    @field_validator("group_id", "actor_id", "actor_generation")
    @classmethod
    def _identity(cls, value: str) -> str:
        """Keep selected routing descriptors nonempty and free of controls."""

        if value != value.strip() or any(ord(char) < 32 or ord(char) == 127 for char in value):
            raise ValueError("Actor descriptors must not contain whitespace or controls")
        return value


def binding_identity(configuration: CcccConfiguration) -> str:
    """Return a deterministic public Actor identity without credential values."""

    return json.dumps(
        [
            "cccc-v2",
            configuration.endpoint,
            configuration.group_id,
            configuration.actor_id,
            configuration.actor_generation,
        ],
        ensure_ascii=True,
        separators=(",", ":"),
    )


def validate_credentials(
    configuration: CcccConfiguration, owner_agent_id: str, document: dict[str, JsonValue]
) -> str:
    """Validate the SDK-selected private document against the fixed owner binding."""

    required: dict[str, str] = {
        "agent_id": owner_agent_id,
        "endpoint": configuration.endpoint,
        "group_id": configuration.group_id,
        "actor_id": configuration.actor_id,
        "actor_generation": configuration.actor_generation,
    }
    if any(document.get(key) != value for key, value in required.items()):
        raise ValueError("Selected CCCC credentials do not match the owner binding")
    token = document.get("token")
    if not isinstance(token, str) or not token or len(token) > 8192:
        raise ValueError("Selected CCCC credential token is invalid")
    if any(char.isspace() or ord(char) < 33 or ord(char) > 126 for char in token):
        raise ValueError("Selected CCCC credential token is invalid")
    return token
