"""Public, versioned data contracts for trusted gateway plugins."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator

PLUGIN_SDK_VERSION = 2
PLUGIN_ENTRY_POINT_GROUP = "houmao.gateway_plugins"
_INSTANCE_ID = re.compile(r"[a-z][a-z0-9-]{0,62}\Z")


class _PluginModel(BaseModel):
    """Reject unknown fields and implicit coercion in public plugin models."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, allow_inf_nan=False)


class PluginCredentialReference(_PluginModel):
    """Select one absolute private credential document without embedding secrets."""

    file: Path

    @field_validator("file", mode="before")
    @classmethod
    def _absolute_file(cls, value: object) -> Path:
        """Accept an explicit path without expanding variables or user homes."""

        if not isinstance(value, (str, Path)):
            raise ValueError("credential reference requires an absolute file path")
        path = Path(value)
        if not path.is_absolute() or ".." in path.parts:
            raise ValueError("credential reference requires an absolute file path")
        return path


class PluginInstanceConfiguration(_PluginModel):
    """Enable one implementation with owner-selected settings and credentials."""

    implementation: str = Field(min_length=1, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
    credential_ref: PluginCredentialReference | None = None
    config: dict[str, JsonValue] = Field(default_factory=dict)


class GatewayPluginConfiguration(_PluginModel):
    """Describe a complete explicitly enabled gateway plugin set.

    Parameters
    ----------
    plugins : dict
        Instance IDs mapped to independently installed implementations.
    max_event_bytes : int
        Maximum UTF-8 JSON event-envelope size.
    dispatch_timeout_seconds : float
        Finite deadline for confirming immediate dispatch.
    startup_timeout_seconds, shutdown_timeout_seconds : float
        Cooperative plugin lifecycle deadlines.
    """

    schema_version: Literal[1] = 1
    plugins: dict[str, PluginInstanceConfiguration] = Field(default_factory=dict)
    max_event_bytes: int = Field(default=65536, gt=0)
    dispatch_timeout_seconds: float = Field(default=10.0, gt=0, allow_inf_nan=False)
    startup_timeout_seconds: float = Field(default=10.0, gt=0, allow_inf_nan=False)
    shutdown_timeout_seconds: float = Field(default=5.0, gt=0, allow_inf_nan=False)

    @field_validator("schema_version", mode="before")
    @classmethod
    def _schema_version(cls, value: object) -> object:
        """Require an integer version rather than boolean equality with one."""

        if type(value) is not int:
            raise ValueError("schema_version must be an integer")
        return value

    @field_validator("plugins")
    @classmethod
    def _instance_ids(
        cls, value: dict[str, PluginInstanceConfiguration]
    ) -> dict[str, PluginInstanceConfiguration]:
        """Validate host-owned instance names before applying any selection."""

        if any(_INSTANCE_ID.fullmatch(name) is None for name in value):
            raise ValueError("plugin instance IDs must match [a-z][a-z0-9-]{0,62}")
        return value

    @classmethod
    def from_file(cls, path: Path) -> GatewayPluginConfiguration:
        """Read a duplicate-safe versioned YAML or JSON configuration file."""

        from houmao.gateway.plugins.configuration import load_plugin_configuration

        return load_plugin_configuration(path)

    @property
    def configuration_digest(self) -> str:
        """Return an opaque canonical identity for complete effective selections."""

        encoded = json.dumps(
            self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


class PluginOwner(_PluginModel):
    """Immutable logical owner identity supplied by the gateway host."""

    agent_id: str = Field(min_length=1)
    runtime_session_id: str = Field(min_length=1)
    agent_name: str | None = None


class PluginListener(_PluginModel):
    """Describe a resolved live listener supplied before plugin activation."""

    host: str
    port: int = Field(ge=1, le=65535)
    base_url: str


class PluginEvent(_PluginModel):
    """Represent one ordinary notification, without a queued delivery authority."""

    source_event_id: str = Field(min_length=1, max_length=512)
    text: str = Field(min_length=1)
    metadata: dict[str, JsonValue] = Field(default_factory=dict)


class PluginDispatchResult(_PluginModel):
    """Confirm dispatch, without promising completed agent work or deduplication."""

    disposition: Literal["dispatched"] = "dispatched"
    source_event_id: str
    native_admission: Literal["queued", "handed_off"] | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    native_prompt_id: str | None = Field(default=None, exclude_if=lambda value: value is None)


PluginLifecycleState = Literal[
    "configured",
    "starting",
    "running",
    "failed",
    "stopping",
    "stopped",
    "disabled_by_listener_policy",
]
PluginConnectionState = Literal[
    "unattached", "connected", "reconnecting", "degraded", "disconnected"
]


class PluginStatus(_PluginModel):
    """Expose a sanitized host snapshot without calling plugin health code."""

    instance_id: str
    implementation: str
    distribution: str | None = None
    distribution_version: str | None = None
    sdk_version: int | None = None
    lifecycle: PluginLifecycleState = "configured"
    connection: PluginConnectionState = "unattached"
    binding_id: str | None = None
    error_code: str | None = None
    error_detail: str | None = None
    conflicts: list[dict[str, str]] = Field(default_factory=list)
    workers: list[str] = Field(default_factory=list)
    worker_failures: list[str] = Field(default_factory=list)
    active_requests: int = Field(default=0, ge=0)
    retry_at: str | None = None


class GatewayPluginStatusResponse(_PluginModel):
    """List configured plugin status with the active configuration digest."""

    schema_version: Literal[1] = 1
    configuration_digest: str
    plugins: list[PluginStatus] = Field(default_factory=list)
