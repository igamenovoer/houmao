"""Serve owner-local browser tmux attachments on the existing gateway."""

from __future__ import annotations

import asyncio
import hashlib
import ipaddress
import json
import re
import secrets
import threading
import time
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, Response
from starlette.concurrency import run_in_threadpool
from starlette.websockets import WebSocketState

from houmao.agents.realm_controller.gateway_terminal_login import register_terminal_login_routes
from houmao.agents.realm_controller.gateway_terminal_pty import (
    TerminalTarget,
    TerminalUnavailable,
    run_terminal_stream,
)
from houmao.agents.realm_controller.gateway_web_entry import (
    _bounded_request,
    require_web_entry_origin,
)
from houmao.gateway._tmux_terminal import read_terminal_asset, render_terminal_page
from houmao.gateway.access import GatewayAccessError, GatewayAccessPolicy, GatewayGrant
from houmao.gateway.operations import TERMINAL_INTERACT, TERMINAL_VIEW
from houmao.gateway.owner_authority import BACKING_HEADER, RELAY_HEADER
from houmao.gateway.terminal_entry_contracts import (
    TERMINAL_ASSET_PATH,
    TERMINAL_INTERACT_PATH,
    TERMINAL_INTERACT_STREAM_PATH,
    TERMINAL_INTERACT_TICKET_PATH,
    TERMINAL_VIEW_PATH,
    TERMINAL_VIEW_STREAM_PATH,
    TERMINAL_VIEW_TICKET_PATH,
    GatewayTerminalEntryMode,
    GatewayTerminalEntryTicketV1,
)

_TOKEN = re.compile(r"[A-Za-z0-9_-]{43}")
_TICKET_SECONDS = 60
_MAX_TICKETS = 128
_MAX_STREAMS = 16
_GRANT_TIMEOUT = 10
_GRANT_MESSAGE_BYTES = 128
_PAGE_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        "connect-src 'self'; img-src data:; frame-ancestors 'none'; base-uri 'none'; "
        "form-action 'none'"
    ),
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
}


@dataclass(frozen=True)
class _TerminalTicket:
    """Retain the selected terminal and original authority without the bearer."""

    target: TerminalTarget
    mode: GatewayTerminalEntryMode
    listener: str
    deadline: float
    admin: GatewayGrant | None


def _digest(token: str) -> bytes:
    """Return the in-memory lookup key for a validated opaque token."""

    return hashlib.sha256(token.encode("ascii")).digest()


class _TerminalTickets:
    """Bound and serialize single-use connection grants for one gateway app."""

    def __init__(self) -> None:
        """Initialize the private ticket store."""

        self.m_lock: threading.Lock = threading.Lock()
        self.m_tickets: dict[bytes, _TerminalTicket] = {}

    def issue(
        self,
        *,
        issuer: str,
        listener: str,
        target: TerminalTarget,
        mode: GatewayTerminalEntryMode,
        admin: GatewayGrant | None,
    ) -> GatewayTerminalEntryTicketV1:
        """Issue one fragment link bound to the live target and access mode."""

        with self.m_lock:
            now = time.monotonic()
            self.m_tickets = {
                key: entry for key, entry in self.m_tickets.items() if entry.deadline > now
            }
            if sum(entry.mode == mode for entry in self.m_tickets.values()) >= _MAX_TICKETS:
                raise HTTPException(429, "Terminal entry capacity reached. Try again shortly.")
            token = secrets.token_urlsafe(32)
            self.m_tickets[_digest(token)] = _TerminalTicket(
                target, mode, listener, now + _TICKET_SECONDS, admin
            )
        path = TERMINAL_VIEW_PATH if mode == "view" else TERMINAL_INTERACT_PATH
        return GatewayTerminalEntryTicketV1(
            url=f"{issuer}{path}#ticket={token}",
            expires_at_utc=(datetime.now(UTC) + timedelta(seconds=_TICKET_SECONDS)).isoformat(),
            mode=mode,
        )

    def take(self, token: str, mode: GatewayTerminalEntryMode) -> _TerminalTicket | None:
        """Consume an unexpired token through its own stream route once."""

        key = _digest(token)
        with self.m_lock:
            entry = self.m_tickets.get(key)
            if entry is None or entry.mode != mode:
                return None
            del self.m_tickets[key]
            return entry if entry.deadline > time.monotonic() else None


def _require_http_origin(request: Request, issuer: str) -> None:
    """Check owner-local transport and reject options carried in the URL."""

    require_web_entry_origin(request, issuer)
    if request.scope["query_string"]:
        raise HTTPException(422, "Terminal entry does not accept a query string.")


def _is_owner_websocket(websocket: WebSocket, issuer: str) -> bool:
    """Check the exact browser origin and require a direct loopback peer."""

    try:
        client = websocket.client
        loopback = client is not None and ipaddress.ip_address(client.host).is_loopback
    except ValueError:
        return False
    return (
        loopback
        and websocket.scope["scheme"] == "ws"
        and websocket.headers.getlist("host") == [issuer.removeprefix("http://")]
        and websocket.headers.getlist("origin") == [issuer]
        and not websocket.scope["query_string"]
        and not any(
            name in {"forwarded", "via", "x-real-ip", RELAY_HEADER.lower(), BACKING_HEADER.lower()}
            or name.startswith("x-forwarded-")
            for name in websocket.headers
        )
    )


async def _initial_ticket(websocket: WebSocket) -> str | None:
    """Read a bounded first frame that carries only the connection bearer."""

    message = await asyncio.wait_for(websocket.receive(), timeout=_GRANT_TIMEOUT)
    text = message.get("text")
    if not isinstance(text, str) or len(text) > _GRANT_MESSAGE_BYTES:
        return None
    try:
        value = json.loads(text)
    except (ValueError, RecursionError):
        return None
    if not isinstance(value, dict) or set(value) != {"type", "ticket"}:
        return None
    ticket = value["ticket"]
    if value["type"] != "grant" or not isinstance(ticket, str) or not _TOKEN.fullmatch(ticket):
        return None
    return ticket


async def _close_stream(websocket: WebSocket, code: int, reason: str = "") -> None:
    """Close a live stream while tolerating a concurrent network disconnect."""

    if WebSocketState.DISCONNECTED in (websocket.client_state, websocket.application_state):
        return
    with suppress(WebSocketDisconnect, RuntimeError):
        # The server may know of transport loss before the ASGI disconnect is received.
        await websocket.close(code, reason)


def register_terminal_entry_routes(
    app: FastAPI,
    *,
    issuer: Callable[[], str],
    listener: Callable[[], str],
    agent_id: str,
    resolve_target: Callable[[], TerminalTarget],
    policy: Callable[[], GatewayAccessPolicy],
) -> None:
    """Register the viewer, interactive terminal, and shared browser assets."""

    tickets = _TerminalTickets()
    streams: dict[GatewayTerminalEntryMode, set[WebSocket]] = {"view": set(), "interact": set()}

    def mint_admin(target: TerminalTarget, grant: GatewayGrant) -> GatewayTerminalEntryTicketV1:
        """Mint a current administrator's ticket after caller and target validation."""

        active_listener = listener()
        if (
            grant.target.owner.agent_id != target.agent_id
            or grant.target.incarnation != target.generation
            or grant.listener_id != active_listener
        ):
            raise HTTPException(409, "The managed terminal changed. Start again.")
        return tickets.issue(
            issuer=issuer(), listener=active_listener, target=target, mode="interact", admin=grant
        )

    def current_target() -> TerminalTarget:
        """Translate terminal authority failures into a safe owner-local error."""

        try:
            return resolve_target()
        except TerminalUnavailable as error:
            raise HTTPException(409, str(error)) from None

    async def page(request: Request, mode: GatewayTerminalEntryMode) -> Response:
        """Serve the fixed page without minting a grant or allocating a PTY."""

        _require_http_origin(request, issuer())
        await run_in_threadpool(current_target)
        return HTMLResponse(render_terminal_page(mode), headers=_PAGE_HEADERS)

    @app.get(TERMINAL_VIEW_PATH)
    async def view_page(request: Request) -> Response:
        """Serve the anonymous viewer page."""

        return await page(request, "view")

    @app.get(TERMINAL_INTERACT_PATH)
    async def admin_page(request: Request) -> Response:
        """Serve the interactive page with its administrator sign-in action."""

        return await page(request, "interact")

    @app.get(TERMINAL_ASSET_PATH)
    def asset(request: Request, name: str) -> Response:
        """Serve only bundled named resources from the owner-local gateway."""

        _require_http_origin(request, issuer())
        resource = read_terminal_asset(name)
        if resource is None:
            raise HTTPException(404, "Terminal asset not found.")
        data, media_type = resource
        return Response(data, media_type=media_type, headers=_PAGE_HEADERS)

    @app.post(TERMINAL_VIEW_TICKET_PATH)
    async def view_ticket(request: Request) -> GatewayTerminalEntryTicketV1:
        """Issue a view grant independently of roster and default permissions."""

        base = issuer()
        _require_http_origin(request, base)
        await _bounded_request(request, 0)
        target = await run_in_threadpool(current_target)
        return tickets.issue(
            issuer=base, listener=listener(), target=target, mode="view", admin=None
        )

    @app.post(TERMINAL_INTERACT_TICKET_PATH)
    async def admin_ticket(request: Request) -> GatewayTerminalEntryTicketV1:
        """Issue a ticket under current open or enrolled-key administrator authority."""

        _require_http_origin(request, issuer())
        await _bounded_request(request, 0)
        grant = getattr(request.state, "gateway_grant", None)
        if not isinstance(grant, GatewayGrant):
            raise HTTPException(403, "Gateway administrator authority is required.")

        def issue() -> GatewayTerminalEntryTicketV1:
            """Validate privilege before and after live target resolution."""

            policy().require_terminal_interaction(grant)
            target = current_target()
            policy().require_terminal_interaction(grant)
            return mint_admin(target, grant)

        return await run_in_threadpool(issue)

    async def stream(websocket: WebSocket, mode: GatewayTerminalEntryMode) -> None:
        """Redeem the mode-specific ticket before starting the tmux attachment."""

        permission = TERMINAL_VIEW if mode == "view" else TERMINAL_INTERACT
        if getattr(
            websocket.state, "gateway_terminal_permission", None
        ) != permission or not _is_owner_websocket(websocket, issuer()):
            await websocket.close(1008, "Use the direct owner-local gateway origin.")
            return
        active = streams[mode]
        if len(active) >= _MAX_STREAMS:
            await websocket.close(1013, "Terminal attachment capacity reached.")
            return
        active.add(websocket)
        try:
            await websocket.accept()
            token = await _initial_ticket(websocket)
            entry = tickets.take(token, mode) if token is not None else None
            if entry is None:
                await _close_stream(websocket, 1008, "Terminal link expired or is invalid.")
                return

            def check_current() -> None:
                """Keep the original grant bound to the live listener and target."""

                if listener() != entry.listener:
                    raise TerminalUnavailable("The gateway instance changed.")
                if resolve_target() != entry.target:
                    raise TerminalUnavailable("The managed terminal changed.")
                if entry.admin is not None:
                    policy().require_terminal_interaction(entry.admin)

            await run_in_threadpool(check_current)
            if time.monotonic() >= entry.deadline:
                await _close_stream(websocket, 1008, "Terminal link expired or is invalid.")
                return
            await run_terminal_stream(
                websocket, entry.target, interact=mode == "interact", check_current=check_current
            )
            await _close_stream(websocket, 1000)
        except WebSocketDisconnect:
            return
        except (GatewayAccessError, TerminalUnavailable, TimeoutError):
            await _close_stream(websocket, 1008, "Terminal access ended. Open a fresh link.")
        finally:
            active.discard(websocket)

    @app.websocket(TERMINAL_VIEW_STREAM_PATH)
    async def view_stream(websocket: WebSocket) -> None:
        """Attach a read-only browser terminal."""

        await stream(websocket, "view")

    @app.websocket(TERMINAL_INTERACT_STREAM_PATH)
    async def admin_stream(websocket: WebSocket) -> None:
        """Attach an administrator's interactive browser terminal."""

        await stream(websocket, "interact")

    register_terminal_login_routes(
        app,
        issuer=issuer,
        listener=listener,
        agent_id=agent_id,
        resolve_target=resolve_target,
        policy=policy,
        mint_ticket=mint_admin,
    )
