"""Apply gateway caller admission before protected routing and request parsing."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from fastapi import FastAPI, Request
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import Headers, MutableHeaders
from starlette.requests import ClientDisconnect
from starlette.responses import JSONResponse
from starlette.routing import Match, Route, WebSocketRoute
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from houmao.agents.realm_controller.errors import GatewayError
from houmao.agents.realm_controller.gateway_plugin_host import GatewayPluginHost
from houmao.agents.realm_controller.gateway_plugin_routes import declared_plugin_action
from houmao.agents.realm_controller.gateway_web_entry import (
    WEB_RESPONSE_HEADERS,
    WEB_TICKET_PATH,
    is_web_entry_path,
)
from houmao.gateway.access import (
    CHALLENGE_HEADER,
    SIGNATURE_HEADER,
    GatewayAccessError,
    FirstEnrollment,
    GatewayGrant,
    GatewayRequestBinding,
)
from houmao.gateway.authorization_models import Permission
from houmao.gateway.file_edits.contracts import MAX_FILE_REQUEST_BYTES
from houmao.gateway.operations import CORE_OPERATIONS, CORE_TERMINAL_WEBSOCKETS, GatewayOperation
from houmao.gateway.owner_authority import BACKING_HEADER, RELAY_HEADER
from houmao.gateway.terminal_entry_contracts import (
    TERMINAL_INTERACT_TICKET_PATH,
    TERMINAL_VIEW_TICKET_PATH,
    is_terminal_entry_path,
)

PUBLIC_INPUT_LIMIT = 64 * 1024
CHALLENGE_INPUT_LIMIT = 16 * 1024
_SIGNED_BODY_LIMIT = 16 * 1024 * 1024
_PROOF_HEADERS = (CHALLENGE_HEADER, SIGNATURE_HEADER, RELAY_HEADER, BACKING_HEADER)
_CREDENTIAL_HEADERS = frozenset(header.lower().encode("ascii") for header in _PROOF_HEADERS)
_PUBLIC_INPUT_PATHS = frozenset({"/v1/messages", "/v1/public/prompt"})


class GatewayAdmission(Protocol):
    """Verify the exact operation against the gateway's current owner policy."""

    def __call__(
        self,
        *,
        request: Request,
        operation: GatewayOperation,
        binding: GatewayRequestBinding,
        proof: dict[str, str],
        body: bytes,
    ) -> GatewayGrant | FirstEnrollment | None:
        """Return authoritative caller provenance for the matched operation."""


def _classified_routes(
    routes: list[object], *, plugin_routes: bool
) -> tuple[
    list[tuple[Route, dict[str, GatewayOperation]]], dict[str, tuple[WebSocketRoute, Permission]]
]:
    """Validate HTTP operations and the fixed terminal WebSockets before listening."""

    http_routes: list[tuple[Route, dict[str, GatewayOperation]]] = []
    terminal_websockets: dict[str, tuple[WebSocketRoute, Permission]] = {}
    for route in routes:
        if isinstance(route, WebSocketRoute):
            permission = CORE_TERMINAL_WEBSOCKETS.get(route.path)
            if permission is None or route.path in terminal_websockets:
                raise GatewayError(
                    "Gateway contains an unsupported or unclassified WebSocket route."
                )
            terminal_websockets[route.path] = (route, permission)
            continue
        if not isinstance(route, Route) or not route.methods:
            raise GatewayError("Gateway contains an unsupported or unclassified route.")
        operations: dict[str, GatewayOperation] = {}
        for method in route.methods:
            operation = CORE_OPERATIONS.get((method, route.path))
            if operation is None and route.path == "/v1/plugins/{instance_id}/_status":
                operation = GatewayOperation(route.path, None, selector="plugin-status")
            if operation is None:
                if not plugin_routes or not route.path.startswith("/v1/plugins/"):
                    raise GatewayError(
                        f"Gateway route has no access classification: {method} {route.path}."
                    )
                action = declared_plugin_action(route)
                operation = GatewayOperation(route.path, None, selector=action)
            operations[method] = operation
        http_routes.append((route, operations))
    return http_routes, terminal_websockets


def validate_core_gateway_routes(routes: list[object]) -> None:
    """Reject unclassified core routes before importing plugin implementations."""

    _classified_routes(routes, plugin_routes=False)


def _plugin_operation(path: str, resource: str, action: str) -> GatewayOperation:
    """Preserve the host's exact instance and action in middleware admission."""

    return GatewayOperation(path, Permission(resource=resource, action=action))


class GatewayAdmissionMiddleware:
    """Resolve the matched access class and establish caller state before FastAPI."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        gateway: FastAPI,
        plugin_host: GatewayPluginHost,
        admit: GatewayAdmission,
        reserve_public_input: Callable[[], None],
        log_denial: Callable[[GatewayOperation, int], None],
    ) -> None:
        """Capture the validated route inventory and policy callbacks."""

        self.m_app: ASGIApp = app
        self.m_plugin_host: GatewayPluginHost = plugin_host
        self.m_routes, self.m_terminal_websockets = _classified_routes(
            list(gateway.routes), plugin_routes=True
        )
        self.m_admit: GatewayAdmission = admit
        self.m_reserve_public_input: Callable[[], None] = reserve_public_input
        self.m_log_denial: Callable[[GatewayOperation, int], None] = log_denial

    def _operation(self, scope: Scope) -> GatewayOperation | None:
        """Match actual routes in the same order as the app's router."""

        for route, operations in self.m_routes:
            match, child = route.matches(scope)
            if match is not Match.FULL:
                continue
            operation = operations[scope["method"]]
            params = child.get("path_params", {})
            if operation.selector == "plugin-status":
                instance = params["instance_id"]
                resource = self.m_plugin_host.instance_resource(instance)
                return _plugin_operation(
                    operation.path, resource or "plugins", "plugin.status.read"
                )
            if operation.selector is not None and operation.selector.startswith("plugin."):
                selected = self.m_plugin_host.route_permission(scope)
                if selected is None or selected.action != operation.selector:
                    raise GatewayError("Published plugin route lost its authorization declaration.")
                return _plugin_operation(operation.path, selected.resource, selected.action)
            return operation.bind_channel(params.get("channel"))
        unavailable = self.m_plugin_host.route_permission(scope)
        if unavailable is not None:
            return _plugin_operation(
                "/v1/plugins/{instance_id}/{operation}", unavailable.resource, unavailable.action
            )
        return None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Check the access rule, replaying bounded raw bytes only after admission."""

        if scope["type"] == "websocket":
            await self._terminal_websocket(scope, receive, send)
            return
        if scope["type"] != "http":
            await self.m_app(scope, receive, send)
            return
        operation = self._operation(scope)
        terminal_path = is_terminal_entry_path(scope["path"]) or (
            operation is not None and is_terminal_entry_path(operation.path)
        )
        if terminal_path or is_web_entry_path(scope["path"]):
            downstream = send

            async def send_web_response(message: Message) -> None:
                """Protect browser entry responses and admission denials."""

                if message["type"] == "http.response.start":
                    headers = MutableHeaders(scope=message)
                    for key, value in WEB_RESPONSE_HEADERS.items():
                        headers[key] = value
                await downstream(message)

            send = send_web_response
        if operation is None:
            await self.m_app(scope, receive, send)
            return
        request = Request(scope, receive)
        request.state.gateway_operation = operation.path
        request.state.gateway_admitted_operation = operation
        headers = {name: request.headers.getlist(name) for name in _PROOF_HEADERS}
        signed = any(headers.values())
        try:
            if (terminal_path or operation.direct_web_entry) and (
                headers[RELAY_HEADER] or headers[BACKING_HEADER]
            ):
                code = (
                    "direct_terminal_access_required" if terminal_path else "direct_admin_required"
                )
                raise GatewayAccessError(403, code)
            if operation.transport_public and signed:
                if terminal_path:
                    raise GatewayAccessError(403, "terminal_browser_ticket_required")
                if is_web_entry_path(operation.path):
                    raise GatewayAccessError(403, "interactive_web_proof_required")
            if headers[BACKING_HEADER] or any(len(values) > 1 for values in headers.values()):
                raise GatewayAccessError(401, "invalid_proof")
            if operation.path in _PUBLIC_INPUT_PATHS:
                self.m_reserve_public_input()
            limit = self._body_limit(operation, signed=signed)
            body = await _bounded_body(request, limit) if limit is not None else b""
            proof = {name: values[0] for name, values in headers.items() if values}
            if not operation.transport_public or signed:
                request_binding = GatewayRequestBinding.from_request(
                    method=request.method,
                    path=scope.get("raw_path", scope["path"].encode("utf-8")).decode("ascii"),
                    query=scope["query_string"].decode("ascii"),
                    body=body,
                )
                request.state.gateway_grant = await run_in_threadpool(
                    self.m_admit,
                    request=request,
                    operation=operation,
                    binding=request_binding,
                    proof=proof,
                    body=body,
                )
        except GatewayAccessError as error:
            await self._reject(operation, error, scope, receive, send)
            return
        except (UnicodeError, ValueError):
            await self._reject(
                operation, GatewayAccessError(401, "invalid_proof"), scope, receive, send
            )
            return
        except ClientDisconnect:
            return
        if limit is not None:
            receive = _replaying_receive(body, receive)
        if signed:
            scope["headers"] = [
                (name, value) for name, value in scope["headers"] if name not in _CREDENTIAL_HEADERS
            ]
        await self.m_app(scope, receive, send)

    async def _terminal_websocket(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Pass only classified terminals to the handler that authorizes the stream."""

        path = scope["path"]
        classified = self.m_terminal_websockets.get(path)
        headers = Headers(scope=scope)
        if (
            classified is None
            or scope.get("raw_path", path.encode("utf-8")) != path.encode("utf-8")
            or classified[0].matches(scope)[0] is not Match.FULL
            or RELAY_HEADER in headers
            or BACKING_HEADER in headers
        ):
            await send({"type": "websocket.close", "code": 1008})
            return
        scope.setdefault("state", {})["gateway_terminal_permission"] = classified[1]
        await self.m_app(scope, receive, send)

    @staticmethod
    def _body_limit(operation: GatewayOperation, *, signed: bool) -> int | None:
        """Select the request envelope ceiling before reading any bytes."""

        path = operation.path
        if path in _PUBLIC_INPUT_PATHS:
            return PUBLIC_INPUT_LIMIT
        if path == "/v1/auth/challenge":
            return CHALLENGE_INPUT_LIMIT
        if path == WEB_TICKET_PATH:
            return 4096 if signed else None
        if path in {TERMINAL_VIEW_TICKET_PATH, TERMINAL_INTERACT_TICKET_PATH}:
            return 0
        if operation.selector == "files-resolved":
            return MAX_FILE_REQUEST_BYTES
        return _SIGNED_BODY_LIMIT if signed or operation.selector is not None else None

    async def _reject(
        self,
        operation: GatewayOperation,
        error: GatewayAccessError,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        """Send safe denial details without reflecting headers or request input."""

        self.m_log_denial(operation, error.status_code)
        response = gateway_access_error_response(error, operation)
        await response(scope, receive, send)


async def _bounded_body(request: Request, limit: int) -> bytes:
    """Read the exact signed or public body while bounding buffering."""

    body = bytearray()
    async for chunk in request.stream():
        if len(chunk) > limit - len(body):
            raise GatewayAccessError(413, "request_body_too_large")
        body.extend(chunk)
    return bytes(body)


def _replaying_receive(body: bytes, receive: Receive) -> Receive:
    """Provide admitted bytes once and preserve downstream disconnect handling."""

    sent = False

    async def replay() -> Message:
        """Return the admitted bytes as a single ASGI frame."""

        nonlocal sent
        if not sent:
            sent = True
            return {"type": "http.request", "body": body, "more_body": False}
        return await receive()

    return replay


def gateway_access_error_response(
    error: GatewayAccessError, operation: GatewayOperation
) -> JSONResponse:
    """Return an access error with a safe challenge locator for HTTP 401."""

    detail: dict[str, object] = {"error_code": error.code}
    headers = {"Cache-Control": "no-store"}
    if error.code in {"owner_local_web_entry_required", "direct_terminal_access_required"}:
        detail["message"] = "Use the owner-local gateway directly or through a private TCP forward."
    if error.status_code == 401:
        challenge_path = "/v1/auth/challenge"
        purposes = ("caller", "register") if operation.registration else ("caller",)
        detail.update(challenge_path=challenge_path, purposes=purposes)
        headers["WWW-Authenticate"] = f'Houmao-SSHSIG challenge="{challenge_path}"'
    return JSONResponse(status_code=error.status_code, content={"detail": detail}, headers=headers)
