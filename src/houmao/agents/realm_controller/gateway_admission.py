"""Apply gateway caller admission before protected routing and request parsing."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, Protocol

from fastapi import FastAPI, Request
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import MutableHeaders
from starlette.requests import ClientDisconnect
from starlette.responses import JSONResponse
from starlette.routing import Match, Route
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from houmao.agents.realm_controller.errors import GatewayError
from houmao.agents.realm_controller.gateway_plugin_host import GatewayPluginHost
from houmao.agents.realm_controller.gateway_plugin_routes import declared_plugin_access
from houmao.agents.realm_controller.gateway_web_entry import (
    WEB_CLAIM_PATH,
    WEB_ENTER_PATH,
    WEB_LOGIN_PATH,
    WEB_PROVE_PATH,
    WEB_RESPONSE_HEADERS,
    WEB_TICKET_PATH,
    is_web_entry_path,
)
from houmao.gateway.access import (
    CHALLENGE_HEADER,
    SIGNATURE_HEADER,
    AccessClass,
    GatewayAccessError,
    GatewayGrant,
    GatewayRequestBinding,
)
from houmao.gateway.owner_authority import BACKING_HEADER, RELAY_HEADER

PUBLIC_INPUT_LIMIT = 64 * 1024
CHALLENGE_INPUT_LIMIT = 16 * 1024
_SIGNED_BODY_LIMIT = 16 * 1024 * 1024
_PROOF_HEADERS = (CHALLENGE_HEADER, SIGNATURE_HEADER, RELAY_HEADER, BACKING_HEADER)
_CREDENTIAL_HEADERS = frozenset(header.lower().encode("ascii") for header in _PROOF_HEADERS)
_PUBLIC_INPUT_PATHS = frozenset({"/v1/messages", "/v1/public/prompt"})
_PUBLIC_GET = ("/health", "/v1/endpoint", WEB_ENTER_PATH)
_PUBLIC_POST = (
    "/v1/auth/challenge",
    *_PUBLIC_INPUT_PATHS,
    WEB_LOGIN_PATH,
    WEB_PROVE_PATH,
    WEB_CLAIM_PATH,
)
_PRIVATE_GET = (
    "/v1/status",
    "/v1/usage",
    "/v1/memory",
    "/v1/memory/memo",
    "/v1/mail/status",
    "/v1/plugins",
    "/v1/plugins/{instance_id}/_status",
)
_PRIVATE_POST = (
    WEB_TICKET_PATH,
    "/v1/memory/memo/append",
    *(f"/v1/memory/pages/{op}" for op in ("tree", "resolve", "read", "write", "append", "delete")),
    *(
        f"/v1/mail/{{channel}}/{op}"
        for op in ("list", "peek", "read", "send", "reply", "mark", "move", "archive")
    ),
)
_ADMIN_GET = (
    "/v1/native-home",
    "/v1/control/refresh",
    "/v1/control/tui/state",
    "/v1/control/tui/history",
    "/v1/control/web/state",
    "/v1/control/web/history",
    "/v1/control/service/state",
    "/v1/control/service/requests/{request_id}",
    "/v1/control/headless/state",
    "/v1/reminders",
    "/v1/reminders/{reminder_id}",
    "/v1/mail/online/binding",
    "/v1/mail-notifier/{channel}",
    "/v1/ag-ui/capabilities",
    "/v1/ag-ui/destination",
    "/v1/ag-ui/active-thread",
)
_ADMIN_POST = (
    "/v1/admin/keys",
    "/v1/control/refresh",
    "/v1/control/tui/note-prompt",
    "/v1/control/send-keys",
    "/v1/control/prompt",
    "/v1/control/headless/next-prompt-session",
    "/v1/requests",
    "/v1/reminders",
    "/v1/mail/online/binding/refresh",
    "/v1/mail/online/binding/reconnect",
    "/v1/mail/{channel}/post",
    "/v1/ag-ui/connect",
    "/v1/ag-ui/runs",
    "/v1/ag-ui/events",
)
_ADMIN_PUT = (
    "/v1/reminders/{reminder_id}",
    "/v1/mail/online/binding",
    "/v1/mail-notifier/{channel}",
    "/v1/ag-ui/active-thread",
)
_ADMIN_DELETE = (
    "/v1/admin/keys/{key_id}",
    "/v1/reminders/{reminder_id}",
    "/v1/mail/online/binding",
    "/v1/mail-notifier/{channel}",
    "/v1/ag-ui/connections/{connection_id}",
    "/v1/ag-ui/active-thread",
)
_CORE_CLASSIFICATIONS: tuple[tuple[AccessClass, str, tuple[str, ...]], ...] = (
    ("public", "GET", _PUBLIC_GET),
    ("public", "POST", _PUBLIC_POST),
    ("private", "GET", _PRIVATE_GET),
    ("private", "POST", _PRIVATE_POST),
    ("private", "PUT", ("/v1/memory/memo",)),
    ("admin", "GET", _ADMIN_GET),
    ("admin", "POST", _ADMIN_POST),
    ("admin", "PUT", _ADMIN_PUT),
    ("admin", "DELETE", _ADMIN_DELETE),
)
_CORE_ACCESS: dict[tuple[str, str], AccessClass] = {
    (method, path): access for access, method, paths in _CORE_CLASSIFICATIONS for path in paths
}


@dataclass(frozen=True)
class GatewayOperation:
    """A matched route and the access class applied before handling it."""

    path: str
    access: AccessClass

    @property
    def direct_admin(self) -> bool:
        """Whether only a direct enrolled administrator may use this operation."""

        return self.path == WEB_TICKET_PATH

    @property
    def registration(self) -> bool:
        """Whether the operation accepts first-key proof."""

        return self.path == "/v1/admin/keys"


class GatewayAdmission(Protocol):
    """Verify the exact operation against the gateway's current owner policy."""

    def __call__(
        self,
        *,
        request: Request,
        operation: GatewayOperation,
        binding: GatewayRequestBinding,
        proof: dict[str, str],
    ) -> GatewayGrant:
        """Return authoritative caller provenance for the matched operation."""


def _classified_routes(
    routes: list[object], *, plugin_routes: bool
) -> list[tuple[Route, dict[str, GatewayOperation]]]:
    """Validate every published HTTP operation before the application can listen."""

    result: list[tuple[Route, dict[str, GatewayOperation]]] = []
    for route in routes:
        if not isinstance(route, Route) or not route.methods:
            raise GatewayError("Gateway contains an unsupported or unclassified route.")
        operations: dict[str, GatewayOperation] = {}
        for method in route.methods:
            access = _CORE_ACCESS.get((method, route.path))
            if access is None:
                if not plugin_routes or not route.path.startswith("/v1/plugins/"):
                    raise GatewayError(
                        f"Gateway route has no access classification: {method} {route.path}."
                    )
                access = declared_plugin_access(route)
            operations[method] = GatewayOperation(route.path, access)
        result.append((route, operations))
    return result


def validate_core_gateway_routes(routes: list[object]) -> None:
    """Reject unclassified core routes before importing plugin implementations."""

    _classified_routes(routes, plugin_routes=False)


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
        self.m_routes = _classified_routes(list(gateway.routes), plugin_routes=True)
        self.m_admit: GatewayAdmission = admit
        self.m_reserve_public_input: Callable[[], None] = reserve_public_input
        self.m_log_denial: Callable[[GatewayOperation, int], None] = log_denial

    def _operation(self, scope: Scope) -> GatewayOperation | None:
        """Match actual routes in the same order as the app's router."""

        for route, operations in self.m_routes:
            if route.matches(scope)[0] is Match.FULL:
                return operations[scope["method"]]
        unavailable_access = self.m_plugin_host.unavailable_route_access(scope)
        if unavailable_access is not None:
            return GatewayOperation("/v1/plugins/{instance_id}/{operation}", unavailable_access)
        return None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Check the access rule, replaying bounded raw bytes only after admission."""

        if scope["type"] != "http":
            await self.m_app(scope, receive, send)
            return
        if is_web_entry_path(scope["path"]):
            downstream = send

            async def send_web_response(message: Message) -> None:
                """Protect both admission denials and Web handler responses."""

                if message["type"] == "http.response.start":
                    headers = MutableHeaders(scope=message)
                    for key, value in WEB_RESPONSE_HEADERS.items():
                        headers[key] = value
                await downstream(message)

            send = send_web_response
        operation = self._operation(scope)
        if operation is None:
            await self.m_app(scope, receive, send)
            return
        request = Request(scope, receive)
        request.state.gateway_operation = operation.path
        headers = {name: request.headers.getlist(name) for name in _PROOF_HEADERS}
        signed = any(headers.values())
        try:
            if operation.direct_admin and (headers[RELAY_HEADER] or headers[BACKING_HEADER]):
                raise GatewayAccessError(403, "direct_admin_required")
            if operation.access == "public" and is_web_entry_path(operation.path) and signed:
                raise GatewayAccessError(403, "interactive_web_proof_required")
            if headers[BACKING_HEADER] or any(len(values) > 1 for values in headers.values()):
                raise GatewayAccessError(401, "invalid_proof")
            if operation.path in _PUBLIC_INPUT_PATHS:
                self.m_reserve_public_input()
            limit = self._body_limit(operation.path, signed=signed)
            body = await _bounded_body(request, limit) if limit is not None else b""
            proof = {name: values[0] for name, values in headers.items() if values}
            if operation.access != "public" or signed:
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

    @staticmethod
    def _body_limit(path: str, *, signed: bool) -> int | None:
        """Select the request envelope ceiling before reading any bytes."""

        if path in _PUBLIC_INPUT_PATHS:
            return PUBLIC_INPUT_LIMIT
        if path == "/v1/auth/challenge":
            return CHALLENGE_INPUT_LIMIT
        if path == WEB_TICKET_PATH:
            return 4096 if signed else None
        return _SIGNED_BODY_LIMIT if signed else None

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
    if error.code == "owner_local_web_entry_required":
        detail["message"] = "Use the owner-local gateway directly or through a private TCP forward."
    if error.status_code == 401:
        challenge_path = "/v1/auth/challenge"
        purposes: tuple[Literal["self", "admin", "register"], ...] = (
            ("admin", "register")
            if operation.registration
            else ("admin",)
            if operation.access == "admin" or operation.direct_admin
            else ("self", "admin")
        )
        detail.update(challenge_path=challenge_path, purposes=purposes)
        headers["WWW-Authenticate"] = f'Houmao-SSHSIG challenge="{challenge_path}"'
    return JSONResponse(status_code=error.status_code, content={"detail": detail}, headers=headers)
