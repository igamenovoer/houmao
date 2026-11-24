"""Host trusted installed gateway extensions without exposing runtime internals.

Route staging is resource-free. Each surviving instance owns an independently
supervised asynchronous lifespan and a request-scoped immediate dispatch port.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass, field
import hashlib
import json
import logging
import math
import os
from pathlib import Path
import re
import stat
import threading
from typing import Protocol, cast

from fastapi import FastAPI, HTTPException, Request
from pydantic import JsonValue, TypeAdapter, ValidationError
from starlette.responses import JSONResponse, Response
from starlette.routing import Match, Route
from starlette.types import Scope

from houmao.agents.realm_controller.gateway_plugin_routes import (
    PluginRouteError,
    PluginRoutePermission,
    core_route_declarations,
    plugin_route_declarations,
    route_conflicts,
)
from houmao.gateway.plugins import (
    GatewayPlugin,
    GatewayPluginConfiguration,
    GatewayPluginStatusResponse,
    PluginDispatchError,
    PluginDispatchResult,
    PluginEvent,
    PluginInstanceConfiguration,
    PluginListener,
    PluginOwner,
    PluginStatus,
)
from houmao.gateway.plugins.discovery import PluginLoadError, load_plugin_definition
from houmao.gateway.plugins.models import PluginConnectionState


_LOGGER = logging.getLogger("houmao.gateway.plugins")
_SAFE_CODE = re.compile(r"[A-Za-z0-9_.-]{1,80}\Z")
_CONNECTION_STATES = {"unattached", "connected", "reconnecting", "degraded", "disconnected"}
_CREDENTIAL_DOCUMENT = TypeAdapter(dict[str, JsonValue])


class PluginDispatchCallback(Protocol):
    """Internal synchronous immediate-dispatch seam supplied by the runtime."""

    def __call__(
        self,
        event: PluginEvent,
        *,
        instance_id: str,
        binding_id: str,
        timeout_seconds: float,
        is_active: Callable[[], bool],
    ) -> PluginDispatchResult:
        """Confirm handoff or raise a typed failure, honoring cancellation fencing."""


@dataclass
class _Instance:
    """Passive host bookkeeping for a single selected implementation instance."""

    selection: PluginInstanceConfiguration
    status: PluginStatus
    plugin: GatewayPlugin | None = None
    context: _PluginContext | None = None
    lifetime: asyncio.Task[None] | None = None
    stop_event: asyncio.Event = field(default_factory=asyncio.Event)
    entered: bool = False


class GatewayPluginHost:
    """Stage namespaced routes and supervise independent plugin instances."""

    def __init__(self) -> None:
        """Create an unconfigured host for initialization through its factory."""

        self.m_configuration: GatewayPluginConfiguration = GatewayPluginConfiguration()
        self.m_owner: PluginOwner | None = None
        self.m_gateway_root: Path = Path()
        self.m_project_root: Path = Path()
        self.m_listener_host: str = "127.0.0.1"
        self.m_deployment_validated: bool = False
        self.m_listener_port: int | None = None
        self.m_dispatch: PluginDispatchCallback | None = None
        self.m_instances: dict[str, _Instance] = {}
        self.m_started: bool = False
        self.m_staged: bool = False
        self.m_lock: threading.RLock = threading.RLock()
        self.m_admission_routes: list[tuple[Route, PluginRoutePermission]] = []

    @classmethod
    def from_config(
        cls,
        *,
        configuration: GatewayPluginConfiguration,
        owner: PluginOwner,
        gateway_root: Path,
        project_root: Path,
        listener_host: str,
        dispatch: PluginDispatchCallback,
        deployment_validated: bool = False,
    ) -> GatewayPluginHost:
        """Bind explicit configuration and the owner without loading plugin code.

        Parameters
        ----------
        configuration:
            Complete selected instance set and finite lifecycle/request bounds.
        owner:
            Manifest-backed logical agent and runtime identity.
        gateway_root, project_root:
            Private host storage and the project boundary for credential checks.
        listener_host:
            Actual configured listener policy, checked before code loading.
        dispatch:
            Runtime-owned immediate dispatch function.
        deployment_validated:
            Whether the owner runtime validated explicit access for a broader bind.
        """

        result = cls()
        result.m_configuration = configuration.model_copy(deep=True)
        result.m_owner = owner.model_copy(deep=True)
        result.m_gateway_root = gateway_root.resolve()
        result.m_project_root = _checkout_root(project_root)
        result.m_listener_host = listener_host
        result.m_deployment_validated = deployment_validated
        result.m_dispatch = dispatch
        result.m_instances = {
            name: _Instance(
                selection=selection,
                status=PluginStatus(instance_id=name, implementation=selection.implementation),
            )
            for name, selection in sorted(configuration.plugins.items())
        }
        return result

    @property
    def config_digest(self) -> str:
        """Return the canonical identity of the active selected configuration."""

        return self.m_configuration.configuration_digest

    def status(self) -> list[PluginStatus]:
        """Return independent safe snapshots without invoking external code."""

        with self.m_lock:
            return [self._declared_status(entry.status) for entry in self.m_instances.values()]

    def status_for(self, instance_id: str) -> PluginStatus | None:
        """Return a snapshot for a selected instance, or absence."""

        with self.m_lock:
            entry = self.m_instances.get(instance_id)
            return self._declared_status(entry.status) if entry is not None else None

    def _declared_status(self, status: PluginStatus) -> PluginStatus:
        """Report only host-qualified actions on the represented binding."""

        resource = f"plugin:{status.instance_id}:{status.binding_id}"
        actions = sorted(
            {row.action for row in self.route_permissions() if row.resource == resource}
        )
        return status.model_copy(deep=True, update={"declared_actions": actions})

    def instance_resource(self, instance_id: str) -> str | None:
        """Return a selected instance's policy resource without resolving service credentials."""

        with self.m_lock:
            entry = self.m_instances.get(instance_id)
            if entry is None:
                return None
            binding = entry.status.binding_id
        if binding is None:
            return f"plugin:{instance_id}"
        return f"plugin:{instance_id}:{binding}"

    def route_permission(self, scope: Scope) -> PluginRoutePermission | None:
        """Resolve the action even when a selected route could not be published."""

        instance_id = self._custom_instance(scope["path"])
        if instance_id is None:
            return None
        matches = {
            permission
            for route, permission in self.m_admission_routes
            if route.matches(scope)[0] is Match.FULL
        }
        if len(matches) == 1:
            return matches.pop()
        resource = self.instance_resource(instance_id)
        assert resource is not None
        return PluginRoutePermission(action="plugin.status.read", resource=resource)

    def route_permissions(self) -> frozenset[PluginRoutePermission]:
        """Return exact declared actions for the supported selected plugin instances."""

        return frozenset(permission for _, permission in self.m_admission_routes)

    def _custom_instance(self, path: str) -> str | None:
        """Identify a selected custom namespace independently of its lifecycle."""

        prefix = "/v1/plugins/"
        if not path.startswith(prefix):
            return None
        instance_id, _, relative = path[len(prefix) :].partition("/")
        if instance_id not in self.m_instances or relative.rstrip("/") == "_status":
            return None
        return instance_id

    def stage(self, app: FastAPI) -> None:
        """Register host status and only validated, nonconflicting plugin routers."""

        if self.m_staged:
            return
        self.m_staged = True

        @app.get("/v1/plugins", response_model=GatewayPluginStatusResponse)
        def _plugin_status_list() -> GatewayPluginStatusResponse:
            """Read all configured extension state without service calls."""

            return self._status_response()

        @app.get("/v1/plugins/{instance_id}/_status", response_model=PluginStatus)
        def _plugin_status(instance_id: str) -> PluginStatus:
            """Read one host-owned extension snapshot."""

            status = self.status_for(instance_id)
            if status is None:
                raise HTTPException(status_code=404, detail="Unknown plugin instance")
            return status

        @app.exception_handler(PluginDispatchError)
        async def _dispatch_error(_request: Request, error: PluginDispatchError) -> JSONResponse:
            """Render only the public typed failure fields."""

            return JSONResponse(
                status_code=error.status_code, content={"detail": error.to_detail()}
            )

        @app.middleware("http")
        async def _plugin_guard(
            request: Request, call_next: Callable[[Request], Awaitable[Response]]
        ) -> Response:
            """Gate custom namespaces independently of core/status routes."""

            custom_instance = self._custom_instance(request.scope["path"])
            if custom_instance is not None:
                status = self.status_for(custom_instance)
                if status is not None and status.lifecycle != "running":
                    error = PluginDispatchError(
                        error_code=status.error_code or "plugin_unavailable",
                        status_code=503,
                        retryable=status.lifecycle
                        in {"configured", "starting", "stopping", "stopped"},
                        message="Plugin instance is unavailable.",
                    )
                    return JSONResponse(status_code=503, content={"detail": error.to_detail()})
            try:
                return await call_next(request)
            except Exception:
                if custom_instance is None:
                    raise
                _LOGGER.warning("plugin_request_failed instance=%s", custom_instance)
                error = PluginDispatchError(
                    error_code="plugin_request_failed",
                    status_code=503,
                    retryable=True,
                    dispatch_outcome="unknown",
                    message="Plugin request failed.",
                )
                return JSONResponse(status_code=503, content={"detail": error.to_detail()})

        if self.m_listener_host != "127.0.0.1" and not self.m_deployment_validated:
            for entry in self.m_instances.values():
                self._update(
                    entry,
                    lifecycle="disabled_by_listener_policy",
                    error_code="disabled_by_listener_policy",
                    error_detail="Gateway deployment access is unavailable.",
                )
            self._write_snapshot()
            return

        declarations = list(core_route_declarations(app.routes))
        for instance_id, entry in self.m_instances.items():
            safe_fields: set[str] = set()
            try:
                loaded = load_plugin_definition(entry.selection.implementation)
                self._update(
                    entry,
                    distribution=loaded.distribution,
                    distribution_version=loaded.distribution_version,
                    sdk_version=loaded.definition.sdk_version,
                )
                safe_fields = set(loaded.definition.config_model.model_fields)
                settings = loaded.definition.config_model.model_validate(
                    entry.selection.config, strict=True
                )
                identity = loaded.definition.binding_identity(settings.model_copy(deep=True))
                repeated_identity = loaded.definition.binding_identity(
                    settings.model_copy(deep=True)
                )
                if (
                    not isinstance(identity, str)
                    or not identity.strip()
                    or len(identity) > 4096
                    or identity != repeated_identity
                ):
                    raise PluginRouteError(
                        "invalid_binding_identity", "Invalid or unstable service binding identity"
                    )
                owner = self._owner()
                digest = hashlib.sha256(
                    json.dumps(
                        [
                            owner.agent_id,
                            owner.runtime_session_id,
                            instance_id,
                            entry.selection.implementation,
                            identity,
                        ],
                        ensure_ascii=True,
                        separators=(",", ":"),
                    ).encode("utf-8")
                ).hexdigest()
                self._update(entry, binding_id=digest)
                context = _PluginContext.from_instance(self, instance_id, entry)
                entry.context = context
                plugin = loaded.definition.create(context, settings)
                if not callable(getattr(plugin, "lifespan", None)):
                    raise PluginRouteError(
                        "invalid_plugin", "Plugin must supply a supervised lifespan"
                    )
                resource = self.instance_resource(instance_id)
                assert resource is not None
                staged = plugin_route_declarations(
                    instance_id,
                    plugin.router,
                    implementation=entry.selection.implementation,
                    resource=resource,
                )
                declarations.extend(staged)
                for declaration in staged:
                    permission = declaration.permission
                    assert permission is not None
                    route = Route(declaration.path, _unpublished_route, methods=declaration.methods)
                    route.methods = set(declaration.methods)
                    self.m_admission_routes.append((route, permission))
                entry.plugin = plugin
            except PluginLoadError as error:
                detail = error.message
                if error.distributions:
                    detail += " Distributions: " + ", ".join(error.distributions)
                self._fail(entry, error.error_code, detail)
            except ValidationError as error:
                locations = sorted(
                    {
                        _safe_validation_location(item["loc"], safe_fields)
                        for item in error.errors(include_input=False, include_context=False)
                    }
                )
                self._fail(
                    entry,
                    "invalid_plugin_configuration",
                    "Invalid settings at: " + ", ".join(locations),
                )
            except PluginRouteError as error:
                self._fail(entry, error.error_code, error.message)
            except Exception:
                self._fail(entry, "plugin_factory_failed", "Plugin preparation failed.")

        conflicts = route_conflicts(tuple(declarations))
        for instance_id, evidence in conflicts.items():
            entry = self.m_instances[instance_id]
            self._fail(entry, "route_conflict", "Plugin HTTP route declarations overlap.")
            self._update(entry, conflicts=evidence)
        for instance_id, entry in self.m_instances.items():
            if entry.plugin is not None and entry.status.lifecycle == "configured":
                app.include_router(entry.plugin.router, prefix=f"/v1/plugins/{instance_id}")
        self._write_snapshot()

    async def start(self, *, host: str | None = None, port: int | None = None) -> None:
        """Schedule isolated resource activation after core listener initialization."""

        if self.m_started:
            return
        if not self.m_staged:
            raise RuntimeError("Plugin routes must be staged before activation")
        if host is not None and host != self.m_listener_host:
            raise ValueError("Plugin listener policy cannot change after route staging")
        self.m_listener_port = port
        self.m_started = True
        for instance_id, entry in self.m_instances.items():
            if entry.plugin is not None and entry.status.lifecycle == "configured":
                self._update(entry, lifecycle="starting")
                entry.lifetime = asyncio.create_task(
                    self._run_instance(entry), name=f"gateway-plugin-{instance_id}"
                )
        self._write_snapshot()

    async def stop(self) -> None:
        """Revoke dispatch access and clean up each independent plugin lifespan."""

        if not self.m_started:
            return
        self.m_started = False
        tasks: list[asyncio.Task[None]] = []
        for entry in self.m_instances.values():
            if entry.context is not None:
                entry.context.revoke()
            entry.stop_event.set()
            task = entry.lifetime
            if task is not None and not task.done():
                if not entry.entered:
                    task.cancel()
                if entry.status.lifecycle != "failed":
                    self._update(entry, lifecycle="stopping")
                tasks.append(task)
        if tasks:
            _, pending = await asyncio.wait(
                tasks, timeout=self.m_configuration.shutdown_timeout_seconds + 0.1
            )
            for entry in self.m_instances.values():
                if entry.lifetime in pending:
                    self._fail(entry, "cleanup_timeout", "Plugin cleanup exceeded its deadline.")
                    if entry.lifetime is not None:
                        entry.lifetime.cancel()
                elif entry.status.lifecycle == "stopping":
                    self._update(entry, lifecycle="stopped", connection="disconnected")
        self._write_snapshot()

    async def _run_instance(self, entry: _Instance) -> None:
        """Own startup, active waiting, and bounded cleanup for one instance."""

        context = entry.context
        plugin = entry.plugin
        if context is None or plugin is None:
            return
        manager: AbstractAsyncContextManager[None] | None = None
        try:
            _ensure_private_directory(context.state_root, self.m_gateway_root)
            context.activate()
            manager = plugin.lifespan()
            async with asyncio.timeout(self.m_configuration.startup_timeout_seconds):
                await manager.__aenter__()
            entry.entered = True
            if entry.status.lifecycle == "starting":
                self._update(entry, lifecycle="running")
            self._write_snapshot()
            await entry.stop_event.wait()
        except asyncio.CancelledError:
            if self.m_started and entry.status.lifecycle != "failed":
                self._fail(entry, "startup_canceled", "Plugin startup was canceled.")
        except TimeoutError:
            self._fail(entry, "startup_timeout", "Plugin startup exceeded its deadline.")
        except PluginDispatchError as error:
            self._fail(entry, error.error_code, "Plugin resource initialization failed.")
        except Exception:
            self._fail(entry, "startup_failed", "Plugin resource initialization failed.")
        finally:
            context.revoke()
            try:
                async with asyncio.timeout(self.m_configuration.shutdown_timeout_seconds):
                    await context.stop_workers()
                    if entry.entered and manager is not None:
                        await manager.__aexit__(None, None, None)
            except (TimeoutError, asyncio.CancelledError):
                self._fail(entry, "cleanup_timeout", "Plugin cleanup exceeded its deadline.")
            except Exception:
                self._fail(entry, "cleanup_failed", "Plugin cleanup failed.")
            self._update(entry, connection="disconnected", retry_at=None)
            if entry.status.lifecycle != "failed":
                self._update(entry, lifecycle="stopped")
            self._write_snapshot()

    def _owner(self) -> PluginOwner:
        """Require configured manifest-derived ownership."""

        if self.m_owner is None:
            raise RuntimeError("Plugin host has no owner")
        return self.m_owner

    def _status_response(self) -> GatewayPluginStatusResponse:
        """Build the public safe status envelope."""

        return GatewayPluginStatusResponse(
            configuration_digest=self.config_digest, plugins=self.status()
        )

    def _update(self, entry: _Instance, **fields: object) -> None:
        """Replace one immutable snapshot without invoking a plugin callback."""

        with self.m_lock:
            entry.status = entry.status.model_copy(update=fields)

    def _fail(self, entry: _Instance, code: str, message: str) -> None:
        """Revoke one failed instance and retain a safe diagnostic."""

        if entry.context is not None:
            entry.context.revoke()
        entry.stop_event.set()
        self._update(entry, lifecycle="failed", error_code=code, error_detail=message)

    def _write_snapshot(self) -> None:
        """Persist only safe host metadata, never credentials or event bodies."""

        if not self.m_instances:
            return
        directory = self.m_gateway_root / "plugins"
        try:
            _ensure_private_directory(directory, self.m_gateway_root)
            destination = directory / "status.json"
            if destination.is_symlink():
                return
            temporary = directory / f".status-{os.getpid()}-{threading.get_ident()}.tmp"
            descriptor = os.open(
                temporary,
                os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0),
                0o600,
            )
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                stream.write(self._status_response().model_dump_json())
            os.replace(temporary, destination)
        except OSError:
            _LOGGER.warning("plugin_status_snapshot_unavailable")


class _PluginContext:
    """Concrete narrow ports bound to one host instance and active generation."""

    def __init__(self) -> None:
        """Initialize empty internal context state."""

        self.m_host: GatewayPluginHost | None = None
        self.m_entry: _Instance | None = None
        self.m_instance_id: str = ""
        self.m_active: threading.Event = threading.Event()
        self.m_revoked: asyncio.Event = asyncio.Event()
        self.m_workers: dict[str, asyncio.Task[None]] = {}
        self.m_state_root: Path = Path()
        self.m_credentials: _CredentialReader | None = None
        self.m_state: _ScopedState | None = None

    @classmethod
    def from_instance(
        cls, host: GatewayPluginHost, instance_id: str, entry: _Instance
    ) -> _PluginContext:
        """Prepare inactive scoped ports without reading credentials or state."""

        result = cls()
        result.m_host = host
        result.m_entry = entry
        result.m_instance_id = instance_id
        result.m_state_root = (
            host.m_gateway_root
            / "plugins"
            / instance_id
            / "bindings"
            / (entry.status.binding_id or "")
        )
        result.m_state = _ScopedState.from_root(result.m_state_root)
        reference = entry.selection.credential_ref
        result.m_credentials = _CredentialReader.from_reference(
            reference.file if reference is not None else None,
            project_root=host.m_project_root,
            is_active=result.m_active.is_set,
        )
        return result

    @property
    def owner(self) -> PluginOwner:
        """Return immutable manifest-backed logical ownership."""

        return self._host()._owner()

    @property
    def instance_id(self) -> str:
        """Return the configured namespace identity."""

        return self.m_instance_id

    @property
    def binding_id(self) -> str:
        """Return the deterministic opaque account binding identity."""

        return self._entry().status.binding_id or ""

    @property
    def listener(self) -> PluginListener | None:
        """Return resolved listener metadata after production bind, when present."""

        host = self._host()
        if host.m_listener_port is None:
            return None
        return PluginListener(
            host=host.m_listener_host,
            port=host.m_listener_port,
            base_url=f"http://127.0.0.1:{host.m_listener_port}",
        )

    @property
    def events(self) -> _PluginContext:
        """Return the request-scoped immediate event port."""

        return self

    @property
    def workers(self) -> _PluginContext:
        """Return this instance's cooperative worker supervisor."""

        return self

    @property
    def credentials(self) -> _CredentialReader:
        """Return access only to the selected private credential document."""

        if self.m_credentials is None:
            raise RuntimeError("Plugin context is unconfigured")
        return self.m_credentials

    @property
    def state(self) -> _ScopedState:
        """Return contained non-message service state access."""

        if self.m_state is None:
            raise RuntimeError("Plugin context is unconfigured")
        return self.m_state

    @property
    def state_root(self) -> Path:
        """Return the private scope root for host resource activation."""

        return self.m_state_root

    def activate(self) -> None:
        """Enable resource reads during the host-owned lifespan."""

        self.m_active.set()
        self.m_revoked.clear()

    def revoke(self) -> None:
        """Prevent all old requests and callbacks from acquiring dispatch authority."""

        self.m_active.clear()
        self.m_revoked.set()

    async def dispatch(self, event: PluginEvent) -> PluginDispatchResult:
        """Dispatch only while active and fence a timed-out or canceled attempt."""

        host = self._host()
        entry = self._entry()
        source_event_id = getattr(event, "source_event_id", None)
        if not self.m_active.is_set() or entry.status.lifecycle != "running":
            raise PluginDispatchError(
                error_code="plugin_unavailable",
                status_code=503,
                retryable=True,
                source_event_id=source_event_id,
            )
        try:
            validated = PluginEvent.model_validate(event.model_dump(mode="json"))
            encoded = json.dumps(validated.model_dump(mode="json"), allow_nan=False).encode("utf-8")
        except (AttributeError, TypeError, ValueError):
            raise PluginDispatchError(
                error_code="invalid_event", status_code=422, retryable=False
            ) from None
        if len(encoded) > host.m_configuration.max_event_bytes:
            raise PluginDispatchError(
                error_code="event_too_large",
                status_code=422,
                retryable=False,
                source_event_id=validated.source_event_id,
            )
        callback = host.m_dispatch
        if callback is None:
            raise RuntimeError("Plugin dispatcher is unconfigured")
        attempt = threading.Event()
        attempt.set()

        def _is_active() -> bool:
            """Keep request cancellation separate from reusable context activation."""

            return (
                attempt.is_set() and self.m_active.is_set() and entry.status.lifecycle == "running"
            )

        host._update(entry, active_requests=entry.status.active_requests + 1)
        dispatch_task = asyncio.create_task(
            asyncio.to_thread(
                callback,
                validated,
                instance_id=self.instance_id,
                binding_id=self.binding_id,
                timeout_seconds=host.m_configuration.dispatch_timeout_seconds,
                is_active=_is_active,
            )
        )
        revocation_task = asyncio.create_task(self.m_revoked.wait())
        try:
            async with asyncio.timeout(host.m_configuration.dispatch_timeout_seconds):
                await asyncio.wait(
                    (dispatch_task, revocation_task), return_when=asyncio.FIRST_COMPLETED
                )
            if not _is_active():
                raise PluginDispatchError(
                    error_code="plugin_unavailable",
                    status_code=503,
                    retryable=True,
                    dispatch_outcome="unknown",
                    source_event_id=validated.source_event_id,
                )
            result = dispatch_task.result()
            if not isinstance(result, PluginDispatchResult) or (
                result.source_event_id != validated.source_event_id
            ):
                raise PluginDispatchError(
                    error_code="dispatch_unconfirmed",
                    status_code=503,
                    retryable=True,
                    dispatch_outcome="unknown",
                    source_event_id=validated.source_event_id,
                )
            return result
        except TimeoutError:
            raise PluginDispatchError(
                error_code="dispatch_timeout",
                status_code=503,
                retryable=True,
                dispatch_outcome="unknown",
                source_event_id=validated.source_event_id,
            ) from None
        except PluginDispatchError:
            raise
        except asyncio.CancelledError:
            raise
        except Exception:
            raise PluginDispatchError(
                error_code="dispatch_failed",
                status_code=503,
                retryable=True,
                dispatch_outcome="unknown",
                source_event_id=validated.source_event_id,
            ) from None
        finally:
            attempt.clear()
            dispatch_task.cancel()
            revocation_task.cancel()
            await asyncio.gather(dispatch_task, revocation_task, return_exceptions=True)
            host._update(entry, active_requests=max(0, entry.status.active_requests - 1))

    def start_soon(self, name: str, worker: Callable[[], Awaitable[None]]) -> None:
        """Start a listener only during this instance's active resource lifespan."""

        if not self.m_active.is_set() or not _SAFE_CODE.fullmatch(name) or name in self.m_workers:
            raise RuntimeError("Plugin worker registration is unavailable or invalid")
        task = asyncio.create_task(
            self._run_worker(name, worker), name=f"plugin-{self.instance_id}-{name}"
        )
        self.m_workers[name] = task
        self._host()._update(self._entry(), workers=sorted(self.m_workers))

    async def _run_worker(self, name: str, worker: Callable[[], Awaitable[None]]) -> None:
        """Isolate one listener's unexpected exit or exception to its owner."""

        try:
            await worker()
        except asyncio.CancelledError:
            if not self.m_active.is_set():
                return
        except Exception:
            pass
        if self.m_active.is_set():
            host = self._host()
            entry = self._entry()
            host._update(entry, worker_failures=sorted({*entry.status.worker_failures, name}))
            host._fail(entry, "worker_failed", "A supervised plugin worker stopped unexpectedly.")

    async def stop_workers(self) -> None:
        """Cancel and await this instance's cooperative listeners."""

        tasks = list(self.m_workers.values())
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self.m_workers.clear()
        self._host()._update(self._entry(), workers=[])

    def report_connection(self, state: str, *, retry_at: str | None = None) -> None:
        """Publish a safe finite connection state without external health probes."""

        if state not in _CONNECTION_STATES:
            raise ValueError("Unsupported plugin connection state")
        if not self.m_active.is_set():
            raise RuntimeError("Plugin connection reporting requires an active lifespan")
        if retry_at is not None and (
            len(retry_at) > 64 or not re.fullmatch(r"[0-9T:Z+ .-]+", retry_at)
        ):
            raise ValueError("Invalid connection retry timestamp")
        self._host()._update(
            self._entry(), connection=cast(PluginConnectionState, state), retry_at=retry_at
        )
        self._host()._write_snapshot()

    def log(
        self, event_code: str, *, fields: dict[str, str | int | float | bool | None] | None = None
    ) -> None:
        """Log static event codes with bounded numerical or enum-only metadata."""

        if not _SAFE_CODE.fullmatch(event_code):
            raise ValueError("Invalid plugin diagnostic event code")
        safe: dict[str, str | int | float | bool | None] = {}
        for key, value in (fields or {}).items():
            if not _SAFE_CODE.fullmatch(key):
                continue
            if value is None or isinstance(value, (int, bool)):
                safe[key] = value
            elif isinstance(value, float) and math.isfinite(value):
                safe[key] = value
            elif key == "state" and value in _CONNECTION_STATES:
                safe[key] = value
            elif key == "method" and value in {
                "GET",
                "POST",
                "PUT",
                "PATCH",
                "DELETE",
                "HEAD",
                "OPTIONS",
            }:
                safe[key] = value
        _LOGGER.info("%s instance=%s fields=%s", event_code, self.instance_id, json.dumps(safe))

    def _host(self) -> GatewayPluginHost:
        """Require the owning host without exposing it through the SDK."""

        if self.m_host is None:
            raise RuntimeError("Plugin context is unconfigured")
        return self.m_host

    def _entry(self) -> _Instance:
        """Require private host bookkeeping for this context."""

        if self.m_entry is None:
            raise RuntimeError("Plugin context is unconfigured")
        return self.m_entry


class _ScopedState:
    """Resolve paths without granting access outside the service binding."""

    def __init__(self) -> None:
        """Create an unbound state resolver."""

        self.m_root: Path = Path()

    @classmethod
    def from_root(cls, root: Path) -> _ScopedState:
        """Bind a host-derived state directory without creating it."""

        result = cls()
        result.m_root = root
        return result

    def path(self, relative_path: str) -> Path:
        """Return a contained path, rejecting parent traversal and symlinks."""

        relative = Path(relative_path)
        if (
            not relative_path
            or relative.is_absolute()
            or ".." in relative.parts
            or "\\" in relative_path
            or "\x00" in relative_path
        ):
            raise ValueError("Plugin state path must remain within its binding")
        candidate = self.m_root / relative
        for item in (candidate, *candidate.parents):
            if item.is_symlink():
                raise ValueError("Plugin state symlinks are unsupported")
        if not candidate.resolve().is_relative_to(self.m_root.resolve()):
            raise ValueError("Plugin state path escapes its binding")
        return candidate


class _CredentialReader:
    """Read only the explicitly selected safe private file while active."""

    def __init__(self) -> None:
        """Create an inactive credential port."""

        self.m_path: Path | None = None
        self.m_project_root: Path = Path()
        self.m_is_active: Callable[[], bool] = lambda: False

    @classmethod
    def from_reference(
        cls, path: Path | None, *, project_root: Path, is_active: Callable[[], bool]
    ) -> _CredentialReader:
        """Bind the selected source without opening or discovering a document."""

        result = cls()
        result.m_path = path
        result.m_project_root = project_root
        result.m_is_active = is_active
        return result

    def read(self) -> dict[str, JsonValue]:
        """Read current selected credentials with safe failures and no fallback."""

        try:
            path = self.m_path
            if not self.m_is_active() or path is None or not path.is_absolute():
                raise ValueError
            if any(item.is_symlink() for item in (path, *path.parents)):
                raise ValueError
            if path.resolve().is_relative_to(self.m_project_root):
                raise ValueError
            descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
            with os.fdopen(descriptor, "r", encoding="utf-8") as stream:
                details = os.fstat(stream.fileno())
                if (
                    not stat.S_ISREG(details.st_mode)
                    or details.st_uid != os.getuid()
                    or details.st_mode & 0o077
                ):
                    raise ValueError
                text = stream.read(1024 * 1024 + 1)
                if len(text) > 1024 * 1024:
                    raise ValueError
                return _CREDENTIAL_DOCUMENT.validate_json(text, strict=True)
        except (OSError, ValueError, UnicodeError):
            raise PluginDispatchError(
                error_code="credential_unavailable",
                status_code=503,
                retryable=False,
                message="Selected plugin credentials are unavailable.",
            ) from None


def _unpublished_route() -> None:
    """Inert endpoint used only to match validated unavailable routes."""


def _checkout_root(project_root: Path) -> Path:
    """Resolve the nearest declared checkout without scanning credential locations."""

    resolved = project_root.resolve()
    for candidate in (resolved, *resolved.parents):
        if (candidate / ".git").exists():
            return candidate
    return resolved


def _safe_validation_location(location: tuple[str | int, ...], fields: set[str]) -> str:
    """Name declared top-level fields without leaking dynamic input mapping keys."""

    if not location:
        return "<root>"
    first = location[0]
    label = first if isinstance(first, str) and first in fields else "<field>"
    return label + (".*" if len(location) > 1 else "")


def _ensure_private_directory(directory: Path, boundary: Path) -> None:
    """Create private contained directories while rejecting symlink escapes."""

    relative = directory.relative_to(boundary)
    if boundary.is_symlink():
        raise OSError("Private plugin state boundary contains a symlink")
    current = boundary
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise OSError("Private plugin state contains a symlink")
        current.mkdir(mode=0o700, exist_ok=True)
        details = current.stat()
        if (
            not stat.S_ISDIR(details.st_mode)
            or details.st_uid != os.getuid()
            or details.st_mode & 0o077
        ):
            raise OSError("Plugin state directory is not owner-private")
