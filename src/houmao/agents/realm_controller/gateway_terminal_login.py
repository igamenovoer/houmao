"""Approve an owner-local terminal browser using the current enrolled admin key."""

from __future__ import annotations

import secrets
import time
from collections.abc import Callable

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.concurrency import run_in_threadpool

from houmao.agents.realm_controller.gateway_terminal_pty import TerminalTarget, TerminalUnavailable
from houmao.agents.realm_controller.gateway_web_entry import (
    WEB_RESPONSE_HEADERS,
    _bounded_request,
    _require_no_query,
    _within_deadline,
    require_web_entry_origin,
)
from houmao.gateway._browser_login_attempts import BrowserLoginStore
from houmao.gateway._web_login import (
    TERMINAL_LOGIN_NAMESPACE,
    WEB_LOGIN_PROOF_MAX_BYTES,
    render_terminal_login_page,
    verify_terminal_login,
)
from houmao.gateway.access import (
    CHALLENGE_HEADER,
    SIGNATURE_HEADER,
    GatewayAccessError,
    GatewayAccessPolicy,
    GatewayGrant,
)
from houmao.gateway.owner_authority import BACKING_HEADER, RELAY_HEADER
from houmao.gateway.terminal_entry_contracts import (
    TERMINAL_LOGIN_CLAIM_PATH,
    TERMINAL_LOGIN_PATH,
    TERMINAL_LOGIN_PROVE_PATH,
    GatewayTerminalEntryTicketV1,
)

_CLAIM_HEADER = "X-Houmao-Terminal-Claim"
_CAPACITY = 128
_LOGIN_ENDED = "Terminal login expired or is unavailable. Open a new terminal login."
_BAD_PROOF = "Choose a current enrolled administrator key and retry."


def _check_request(request: Request, issuer: str, *, browser_post: bool = False) -> None:
    """Keep terminal browser approval on the direct gateway origin."""

    require_web_entry_origin(request, issuer, browser_post=browser_post)
    if any(
        header in request.headers
        for header in (CHALLENGE_HEADER, SIGNATURE_HEADER, BACKING_HEADER, RELAY_HEADER)
    ):
        raise HTTPException(403, "Use the terminal login's direct browser approval flow.")
    _require_no_query(request, login="Terminal login")


def register_terminal_login_routes(
    app: FastAPI,
    *,
    issuer: Callable[[], str],
    listener: Callable[[], str],
    agent_id: str,
    resolve_target: Callable[[], TerminalTarget],
    policy: Callable[[], GatewayAccessPolicy],
    mint_ticket: Callable[[TerminalTarget, GatewayGrant], GatewayTerminalEntryTicketV1],
) -> None:
    """Publish the browser-and-shell approval flow for the admin terminal page."""

    logins = BrowserLoginStore[TerminalTarget](
        clock=lambda: time.monotonic(),
        capacity=lambda: _CAPACITY,
        expired_detail=_LOGIN_ENDED,
        capacity_detail="Terminal login capacity reached. Try again shortly.",
    )

    def current(expected: TerminalTarget | None = None) -> TerminalTarget:
        """Resolve this owner's live target within the original attempt's authority."""

        try:
            target = resolve_target()
        except TerminalUnavailable:
            raise HTTPException(410, _LOGIN_ENDED) from None
        if target.agent_id != agent_id or (expected is not None and target != expected):
            raise HTTPException(410, _LOGIN_ENDED)
        return target

    def require_admin(grant: GatewayGrant, target: TerminalTarget, *, status: int) -> None:
        """Keep the exact enrolled signer and gateway identity through each transition."""

        if (
            grant.target.owner.agent_id != target.agent_id
            or grant.target.incarnation != target.generation
            or grant.listener_id != listener()
        ):
            raise HTTPException(status, _LOGIN_ENDED)
        try:
            policy().require_terminal_admin(grant)
        except GatewayAccessError as error:
            if error.status_code == 503:
                raise HTTPException(503, _LOGIN_ENDED) from None
            raise HTTPException(status, _LOGIN_ENDED) from None

    @app.get(TERMINAL_LOGIN_PATH)
    async def _page(request: Request) -> HTMLResponse:
        """Return a login form with a CSP nonce on the direct owner origin."""

        _check_request(request, issuer())
        await run_in_threadpool(current)
        nonce = secrets.token_urlsafe(24)
        return HTMLResponse(
            render_terminal_login_page(nonce, agent_id=agent_id),
            headers={
                **WEB_RESPONSE_HEADERS,
                "X-Frame-Options": "DENY",
                "Content-Security-Policy": (
                    f"default-src 'none'; script-src 'nonce-{nonce}'; style-src 'nonce-{nonce}'; "
                    "connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
                ),
            },
        )

    @app.post(TERMINAL_LOGIN_PATH)
    async def _start(request: Request) -> JSONResponse:
        """Issue one bound challenge and an opaque browser claim."""

        base = issuer()
        _check_request(request, base, browser_post=True)
        await _bounded_request(request, 0, subject="Terminal login")
        target = await run_in_threadpool(current)
        attempt = logins.start(
            target,
            issuer=base,
            listener=listener(),
            namespace=TERMINAL_LOGIN_NAMESPACE,
            prove_path=TERMINAL_LOGIN_PROVE_PATH,
            evidence={
                "mode": "interact",
                "agent_id": target.agent_id,
                "generation": target.generation,
                "runtime_session_id": target.runtime_session_id,
                "tmux_session_id": target.session_id,
                "tmux_server_started": target.server_started,
            },
        )
        return JSONResponse(attempt, headers=WEB_RESPONSE_HEADERS)

    @app.post(TERMINAL_LOGIN_PROVE_PATH)
    async def _prove(request: Request, attempt_id: str) -> JSONResponse:
        """Approve a challenge using one current retained administrator signature."""

        _check_request(request, issuer())
        login = logins.get(attempt_id)
        if login.approval is not None:
            raise HTTPException(410, _LOGIN_ENDED)
        proofs = await _bounded_request(request, WEB_LOGIN_PROOF_MAX_BYTES, login="Terminal login")

        def approve() -> GatewayGrant:
            """Verify the signer, then resolve and revalidate the original target."""

            try:
                grant = verify_terminal_login(policy(), proofs, login.challenge)
            except GatewayAccessError as error:
                raise HTTPException(error.status_code, _BAD_PROOF) from None
            target = current(login.binding)
            require_admin(grant, target, status=403)
            return grant

        grant = await _within_deadline(login.deadline, approve, expired_detail=_LOGIN_ENDED)
        logins.approve(attempt_id, login, grant)
        return JSONResponse({"status": "approved"}, headers=WEB_RESPONSE_HEADERS)

    @app.post(TERMINAL_LOGIN_CLAIM_PATH)
    async def _claim(request: Request, attempt_id: str) -> JSONResponse:
        """Return a single-use gateway fragment link to only the initiating tab."""

        _check_request(request, issuer(), browser_post=True)
        await _bounded_request(request, 0, subject="Terminal login")
        login = logins.get(attempt_id)
        if not login.matches_claim(request.headers.getlist(_CLAIM_HEADER)):
            raise HTTPException(403, "Terminal login belongs to another browser tab.")
        grant = login.approval
        if grant is None:
            return JSONResponse(
                {"status": "pending"}, status_code=202, headers=WEB_RESPONSE_HEADERS
            )

        def revalidate() -> None:
            """Recheck live authority before issuing a terminal connection grant."""

            require_admin(grant, current(login.binding), status=410)

        await _within_deadline(login.deadline, revalidate, expired_detail=_LOGIN_ENDED)
        ticket = await run_in_threadpool(logins.claim, attempt_id, login, mint_ticket)
        return JSONResponse(ticket.model_dump(mode="json"), headers=WEB_RESPONSE_HEADERS)
