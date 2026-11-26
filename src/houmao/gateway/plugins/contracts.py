"""Public author protocols and factories independent of gateway internals."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from pathlib import Path
from typing import Generic, Protocol, TypeVar

from fastapi import APIRouter
from pydantic import BaseModel, JsonValue

from houmao.gateway.plugins.models import (
    PLUGIN_SDK_VERSION,
    PluginDispatchResult,
    PluginEvent,
    PluginListener,
    PluginOwner,
    PluginPromptReadiness,
)


class PluginCredentialReader(Protocol):
    """Read only the document selected for an active owner binding."""

    def read(self) -> dict[str, JsonValue]:
        """Read current selected credentials without discovering other documents."""


class PluginState(Protocol):
    """Resolve private non-message state inside one service binding."""

    def path(self, relative_path: str) -> Path:
        """Resolve a contained state path, rejecting escapes and symlinks."""


class PluginEventDispatcher(Protocol):
    """Dispatch one notification immediately or report a typed failure."""

    async def wait_until_ready(self, *, timeout_seconds: float) -> PluginPromptReadiness | None:
        """Observe current prompt readiness or report timeout or context loss."""

    def validate(self, event: PluginEvent) -> None:
        """Validate the envelope and visible projection without reserving admission."""

    async def dispatch(
        self, event: PluginEvent, *, readiness: PluginPromptReadiness | None = None
    ) -> PluginDispatchResult:
        """Return only after confirmed handoff; leave every retry to the sender."""


class PluginWorkerSupervisor(Protocol):
    """Own cooperative lifetime and failure reporting for service listeners."""

    def start_soon(self, name: str, worker: Callable[[], Awaitable[None]]) -> None:
        """Start a named listener within the active plugin resource lifespan."""


class PluginContext(Protocol):
    """Expose narrow owner-scoped capabilities to a trusted plugin instance."""

    @property
    def owner(self) -> PluginOwner:
        """Return the immutable logical gateway owner."""

    @property
    def instance_id(self) -> str:
        """Return the configured host-owned instance ID."""

    @property
    def binding_id(self) -> str:
        """Return the opaque stable service/account identity."""

    @property
    def listener(self) -> PluginListener | None:
        """Return resolved listener facts once host activation begins."""

    @property
    def events(self) -> PluginEventDispatcher:
        """Return the immediate ordinary-event dispatch port."""

    @property
    def workers(self) -> PluginWorkerSupervisor:
        """Return this instance's lifecycle-owned worker supervisor."""

    @property
    def credentials(self) -> PluginCredentialReader:
        """Return access only to the selected credential source."""

    @property
    def state(self) -> PluginState:
        """Return contained owner/binding-specific state access."""

    def report_connection(self, state: str, *, retry_at: str | None = None) -> None:
        """Publish safe connection state without invoking a health callback."""

    def log(
        self,
        event_code: str,
        *,
        fields: dict[str, str | int | float | bool | None] | None = None,
    ) -> None:
        """Report allowlisted operational metadata without private content."""


class GatewayPlugin(Protocol):
    """Provide a staged relative router and one asynchronous resource lifespan."""

    @property
    def router(self) -> APIRouter:
        """Return resource-free relative HTTP routes with explicit SDK actions."""

    def lifespan(self) -> AbstractAsyncContextManager[None]:
        """Open and close service resources under the host's supervisor."""


ConfigT = TypeVar("ConfigT", bound=BaseModel)


@dataclass(frozen=True)
class PluginDefinition(Generic[ConfigT]):
    """Advertise an independently installed, versioned implementation.

    Parameters
    ----------
    config_model : type[BaseModel]
        Plugin-owned strict schema for implementation settings.
    binding_identity : callable
        Pure deterministic service/account identity, excluding secret values.
    create : callable
        Resource-free factory accepting host context and validated settings.
    sdk_version : int
        Supported plugin contract version, independent of the package version.
    """

    config_model: type[ConfigT]
    binding_identity: Callable[[ConfigT], str]
    create: Callable[[PluginContext, ConfigT], GatewayPlugin]
    sdk_version: int = PLUGIN_SDK_VERSION
