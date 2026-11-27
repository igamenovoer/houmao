"""Issue and redeem owner-local browser access for one live Web execution."""

from __future__ import annotations

import asyncio
import hashlib
import ipaddress
import re
import secrets
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TypeVar

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from starlette.concurrency import run_in_threadpool

from houmao.agents.realm_controller.gateway_models import (
    GatewayWebEntryTicketV1,
    GatewayWebExecutionIdentityV1,
)
from houmao.gateway._browser_login_attempts import BrowserLoginStore
from houmao.gateway._web_login import (
    WEB_LOGIN_NAMESPACE,
    WEB_LOGIN_PROOF_MAX_BYTES,
    render_web_login_page,
    verify_web_login,
)
from houmao.gateway.access import (
    GatewayAccessError,
    GatewayAccessPolicy,
    GatewayGrant,
    GatewayTarget,
)
from houmao.gateway.authorization_models import AuthorizationActor
from houmao.gateway.operations import WEB_ENTRY

WEB_TICKET_PATH = "/v1/web/entry-ticket"
WEB_ENTER_PATH = "/v1/web/enter"
WEB_LOGIN_PATH = "/v1/web/login"
WEB_PROVE_PATH = WEB_LOGIN_PATH + "/{attempt_id}/prove"
WEB_CLAIM_PATH = WEB_LOGIN_PATH + "/{attempt_id}/claim"
WEB_RESPONSE_HEADERS = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"}
_TICKET_LIFETIME = 60
_CAPACITY = 128
_TICKET_QUERY = re.compile(rb"ticket=([A-Za-z0-9_-]{43})")
_CLAIM_HEADER = "X-Houmao-Web-Claim"
_ENTRY_ENDED = "Web entry expired or is unavailable. Start again from the owner-local entry URL."
_OWNER_LOCAL_ONLY = "Use the owner-local gateway address directly or through a private TCP forward."
_BAD_PROOF = "Choose an enrolled admin key or start again from the login page."
_Result = TypeVar("_Result")


def is_web_entry_path(path: str) -> bool:
    """Recognize the reserved Web entry and login HTTP path families."""

    return (
        path == WEB_TICKET_PATH
        or path == WEB_ENTER_PATH
        or path.startswith((WEB_TICKET_PATH + "/", WEB_ENTER_PATH + "/", WEB_LOGIN_PATH + "/"))
        or path == WEB_LOGIN_PATH
    )


def require_web_entry_origin(request: Request, issuer: str, *, browser_post: bool = False) -> None:
    """Require the exact owner-local authority and a direct loopback connection."""

    origins = request.headers.getlist("origin")
    try:
        loopback = (
            request.client is not None and ipaddress.ip_address(request.client.host).is_loopback
        )
    except ValueError:
        loopback = False
    if (
        not loopback
        or request.scope["scheme"] != "http"
        or request.headers.getlist("host") != [issuer.removeprefix("http://")]
        or any(
            name in {"forwarded", "via", "x-real-ip"} or name.startswith("x-forwarded-")
            for name in request.headers
        )
        or (browser_post and origins != [issuer])
        or (origins and origins != [issuer])
    ):
        raise HTTPException(403, _OWNER_LOCAL_ONLY)


@dataclass(frozen=True)
class WebEntryBinding:
    """Pin a Web execution to one retained gateway owner and native origin."""

    target: GatewayTarget
    execution: GatewayWebExecutionIdentityV1
    origin: str


@dataclass(frozen=True)
class _Ticket:
    """Retain redirect authority without storing the bearer or native credentials."""

    binding: WebEntryBinding
    grant: GatewayGrant
    deadline: float


def _bearer_digest(value: str) -> bytes:
    """Hash an opaque bearer for in-memory comparison."""

    return hashlib.sha256(value.encode("ascii")).digest()


def _utc_expiry(lifetime: int) -> str:
    """Return the display expiry for a grant with a separate monotonic deadline."""

    return (datetime.now(UTC) + timedelta(seconds=lifetime)).isoformat()


class _WebEntryStore:
    """Serialize native Web redirect tickets for one gateway listener."""

    def __init__(self) -> None:
        """Initialize the bounded, ephemeral ticket collection."""

        self.m_lock: threading.Lock = threading.Lock()
        self.m_tickets: dict[bytes, _Ticket] = {}

    def _mint_locked(
        self, issuer: str, binding: WebEntryBinding, grant: GatewayGrant, *, now: float
    ) -> GatewayWebEntryTicketV1:
        """Allocate a normal ticket while holding the transition lock."""

        self.m_tickets = {
            digest: ticket for digest, ticket in self.m_tickets.items() if ticket.deadline > now
        }
        if len(self.m_tickets) >= _CAPACITY:
            raise HTTPException(429, "Web entry capacity reached. Try again shortly.")
        bearer = secrets.token_urlsafe(32)
        self.m_tickets[_bearer_digest(bearer)] = _Ticket(binding, grant, now + _TICKET_LIFETIME)
        return GatewayWebEntryTicketV1(
            url=f"{issuer}{WEB_ENTER_PATH}?ticket={bearer}",
            expires_at_utc=_utc_expiry(_TICKET_LIFETIME),
        )

    def mint(
        self, issuer: str, binding: WebEntryBinding, grant: GatewayGrant
    ) -> GatewayWebEntryTicketV1:
        """Allocate an admitted client's ticket."""

        with self.m_lock:
            return self._mint_locked(issuer, binding, grant, now=time.monotonic())

    def take(self, bearer: str) -> _Ticket | None:
        """Consume exactly once before any live I/O."""

        with self.m_lock:
            ticket = self.m_tickets.pop(_bearer_digest(bearer), None)
            return ticket if ticket is not None and ticket.deadline > time.monotonic() else None


async def _bounded_request(
    request: Request, limit: int, *, subject: str = "Web entry", login: str = "Web login"
) -> bytes:
    """Read a request without buffering beyond the operation's allowed body."""

    data = bytearray()
    async for chunk in request.stream():
        if len(chunk) > limit - len(data):
            if not limit:
                raise HTTPException(422, f"{subject} requests must have an empty body.")
            raise HTTPException(413, f"{login} proof exceeds the size limit.")
        data.extend(chunk)
    return bytes(data)


async def _within_deadline(
    deadline: float, operation: Callable[[], _Result], *, expired_detail: str = _ENTRY_ENDED
) -> _Result:
    """Bound native or proof I/O by the grant's original monotonic deadline."""

    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise HTTPException(410, expired_detail)
    try:
        result = await asyncio.wait_for(run_in_threadpool(operation), timeout=remaining)
    except TimeoutError:
        raise HTTPException(410, expired_detail) from None
    if time.monotonic() >= deadline:
        raise HTTPException(410, expired_detail)
    return result


def _require_no_query(request: Request, *, login: str = "Web login") -> None:
    """Reject caller-supplied options before handling the operation."""

    if request.scope["query_string"]:
        raise HTTPException(422, f"{login} requests do not accept query parameters.")


def _retry_page() -> HTMLResponse:
    """Explain a dead grant and link back to the ticket-free page."""

    return HTMLResponse(
        '<!doctype html><meta charset="utf-8"><title>Web entry expired</title>'
        "<p>Web entry expired or is unavailable.</p>"
        f'<p><a href="{WEB_ENTER_PATH}">Start again</a></p>',
        status_code=410,
        headers={"Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'"},
    )


def register_web_entry_routes(
    app: FastAPI,
    *,
    issuer: Callable[[], str],
    listener: Callable[[], str],
    agent_id: str,
    resolve: Callable[[WebEntryBinding | None], tuple[WebEntryBinding, str]],
    access_policy: Callable[[], GatewayAccessPolicy],
) -> None:
    """Publish both ways to enter the verified native Web application."""

    store = _WebEntryStore()
    logins = BrowserLoginStore[WebEntryBinding](
        clock=lambda: time.monotonic(),
        capacity=lambda: _CAPACITY,
        expired_detail=_ENTRY_ENDED,
        capacity_detail="Web login capacity reached. Try again shortly.",
    )

    def require_current_grant(grant: GatewayGrant, target: GatewayTarget, *, status: int) -> None:
        """Recheck Web permission and the exact admitted authority."""

        if (
            WEB_ENTRY in grant.permissions
            and grant.target == target
            and access_policy().revalidate(grant)
        ):
            return
        raise HTTPException(
            status,
            "Web entry access changed. Check the current gateway policy and retry."
            if status == 403
            else _ENTRY_ENDED,
        )

    def resolve_authorized(
        grant: GatewayGrant, expected: WebEntryBinding | None = None, *, stale_status: int = 410
    ) -> tuple[WebEntryBinding, str]:
        """Verify the caller before and after resolving the same live Web execution."""

        target = expected.target if expected is not None else grant.target
        require_current_grant(grant, target, status=stale_status)
        binding, destination = resolve(expected)
        require_current_grant(grant, binding.target, status=stale_status)
        return binding, destination

    def redirect_destination(grant: GatewayGrant, expected: WebEntryBinding | None = None) -> str:
        """Fence native entry immediately before disclosing the redirect."""

        _, destination = resolve_authorized(grant, expected)
        try:
            access_policy().handoff(grant)
        except GatewayAccessError as error:
            if error.status_code == 503:
                raise
            raise HTTPException(410, _ENTRY_ENDED) from None
        return destination

    def open_destination() -> str | None:
        """Resolve an anonymous handoff or signal that the login page is required."""

        try:
            grant = access_policy().authorize(AuthorizationActor(kind="anonymous"), (WEB_ENTRY,))
        except GatewayAccessError as error:
            if error.code == "proof_required":
                return None
            raise
        return redirect_destination(grant)

    @app.post(WEB_TICKET_PATH, response_model=GatewayWebEntryTicketV1)
    async def _issue(request: Request) -> GatewayWebEntryTicketV1:
        """Mint a ticket after direct Web entry admission."""

        base = issuer()
        require_web_entry_origin(request, base)
        _require_no_query(request)
        grant = getattr(request.state, "gateway_grant", None)
        if not isinstance(grant, GatewayGrant) or WEB_ENTRY not in grant.permissions:
            raise HTTPException(403, "Current gateway Web entry permission is required.")
        await _bounded_request(request, 0)

        def issue() -> GatewayWebEntryTicketV1:
            """Keep retained authority and native observation outside the event loop."""

            binding, _ = resolve_authorized(grant, stale_status=403)
            return store.mint(base, binding, grant)

        return await run_in_threadpool(issue)

    @app.get(WEB_ENTER_PATH)
    async def _enter(request: Request) -> Response:
        """Open a live Web agent anonymously, through login, or by ticket."""

        base = issuer()
        require_web_entry_origin(request, base)
        query = request.scope["query_string"]
        if not query:
            open_url = await run_in_threadpool(open_destination)
            if open_url is not None:
                return RedirectResponse(open_url, status_code=302)
            nonce = secrets.token_urlsafe(24)
            return HTMLResponse(
                render_web_login_page(nonce, agent_id=agent_id),
                headers={
                    "X-Frame-Options": "DENY",
                    "Content-Security-Policy": (
                        f"default-src 'none'; script-src 'nonce-{nonce}'; style-src 'nonce-{nonce}'; "
                        "connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
                    ),
                },
            )
        match = _TICKET_QUERY.fullmatch(query)
        ticket = store.take(match[1].decode("ascii")) if match is not None else None
        if ticket is None:
            return _retry_page()
        try:
            destination = await _within_deadline(
                ticket.deadline, lambda: redirect_destination(ticket.grant, ticket.binding)
            )
        except HTTPException:
            return _retry_page()
        return RedirectResponse(destination, status_code=302)

    @app.post(WEB_LOGIN_PATH)
    async def _start(request: Request) -> dict[str, str]:
        """Start a pending login only when the browser asks."""

        base = issuer()
        require_web_entry_origin(request, base, browser_post=True)
        _require_no_query(request)
        await _bounded_request(request, 0)
        binding, _ = await run_in_threadpool(resolve, None)
        return logins.start(
            binding,
            issuer=base,
            listener=listener(),
            namespace=WEB_LOGIN_NAMESPACE,
            prove_path=WEB_PROVE_PATH,
            evidence={
                "target": binding.target.model_dump(mode="json"),
                "execution": binding.execution.model_dump(mode="json"),
                "native_origin": binding.origin,
            },
        )

    @app.post(WEB_PROVE_PATH)
    async def _prove(request: Request, attempt_id: str) -> dict[str, str]:
        """Approve the pending attempt using a current signer with Web entry permission."""

        require_web_entry_origin(request, issuer())
        _require_no_query(request)
        login = logins.get(attempt_id)
        if login.approval is not None:
            raise HTTPException(410, _ENTRY_ENDED)

        def approve(proofs: bytes) -> GatewayGrant:
            """Verify the terminal signature and the currently owned Web target."""

            try:
                grant = verify_web_login(access_policy(), proofs, login.challenge)
            except GatewayAccessError as error:
                raise HTTPException(error.status_code, _BAD_PROOF) from None
            resolve_authorized(grant, login.binding)
            return grant

        proofs = await _bounded_request(request, WEB_LOGIN_PROOF_MAX_BYTES)
        grant = await _within_deadline(login.deadline, lambda: approve(proofs))
        logins.approve(attempt_id, login, grant)
        return {"status": "approved"}

    @app.post(WEB_CLAIM_PATH)
    async def _claim(request: Request, attempt_id: str) -> Response:
        """Claim an approval using the secret issued only to the waiting tab."""

        base = issuer()
        require_web_entry_origin(request, base, browser_post=True)
        _require_no_query(request)
        await _bounded_request(request, 0)
        login = logins.get(attempt_id)
        if not login.matches_claim(request.headers.getlist(_CLAIM_HEADER)):
            raise HTTPException(403, "Web login belongs to another browser tab.")
        grant = login.approval
        if grant is None:
            return JSONResponse({"status": "pending"}, status_code=202)
        await _within_deadline(login.deadline, lambda: resolve_authorized(grant, login.binding))
        ticket = logins.claim(
            attempt_id, login, lambda binding, grant: store.mint(base, binding, grant)
        )
        return JSONResponse(ticket.model_dump(mode="json"))
