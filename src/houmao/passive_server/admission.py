"""Selected-agent route admission for the passive HTTP ingress."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal
from urllib.parse import quote, urlsplit

from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from starlette.concurrency import run_in_threadpool
from starlette.requests import ClientDisconnect
from starlette.responses import Response
from starlette.routing import compile_path
from starlette.types import Message

from houmao.agents.realm_controller.gateway_access_runtime import GatewayRuntimeAccess
from houmao.gateway.access import (
    AccessClass,
    CHALLENGE_HEADER,
    SIGNATURE_HEADER,
    GatewayAccessError,
    GatewayAccessPolicy,
    GatewayChallengeRequest,
    GatewayGrant,
    GatewayRequestBinding,
    parse_access_document,
)
from houmao.gateway.owner_authority import (
    BACKING_HEADER,
    RELAY_HEADER,
    PassiveBackingBinding,
    consume_passive_backing,
)

if TYPE_CHECKING:
    from houmao.passive_server.service import PassiveServerService


_PREFIX = "/houmao/agents/{agent_ref}"
_MAX_PROTECTED_BYTES = 16 * 1024 * 1024
_PUBLIC = {("GET", ""), ("GET", "/resolve"), ("POST", "/auth/challenge")}
_PRIVATE = {
    ("GET", "/usage"),
    ("GET", "/gateway"),
    ("GET", "/gateway/memory"),
    ("GET", "/gateway/memory/memo"),
    ("PUT", "/gateway/memory/memo"),
    ("POST", "/gateway/memory/memo/append"),
    *(
        ("POST", f"/gateway/memory/pages/{name}")
        for name in ("tree", "resolve", "read", "write", "append", "delete")
    ),
    ("GET", "/mail/status"),
    *(
        ("POST", f"/mail/{{channel}}/{name}")
        for name in ("list", "peek", "read", "send", "reply", "mark", "move", "archive")
    ),
    ("GET", "/managed-state"),
}
_ADMIN = {
    ("GET", "/gateway/native-home"),
    ("GET", "/gateway/control/refresh"),
    ("POST", "/gateway/control/refresh"),
    ("GET", "/gateway/tui/state"),
    ("GET", "/gateway/tui/history"),
    ("GET", "/gateway/web/state"),
    ("GET", "/gateway/web/history"),
    ("POST", "/gateway/tui/note-prompt"),
    ("GET", "/gateway/control/headless/state"),
    ("POST", "/gateway/control/headless/next-prompt-session"),
    ("POST", "/gateway/requests"),
    ("POST", "/gateway/control/prompt"),
    ("POST", "/gateway/control/send-keys"),
    ("POST", "/gateway/attach"),
    ("POST", "/gateway/detach"),
    *((method, "/gateway/mail-notifier/{channel}") for method in ("GET", "PUT", "DELETE")),
    ("GET", "/gateway/reminders"),
    ("POST", "/gateway/reminders"),
    *((method, "/gateway/reminders/{reminder_id}") for method in ("GET", "PUT", "DELETE")),
    *((method, "/mail/online/binding") for method in ("GET", "PUT", "DELETE")),
    ("POST", "/mail/online/binding/refresh"),
    ("POST", "/mail/online/binding/reconnect"),
    ("POST", "/mail/{channel}/post"),
    ("GET", "/state"),
    ("GET", "/state/detail"),
    ("GET", "/history"),
    ("GET", "/managed-state/detail"),
    ("GET", "/managed-history"),
    ("POST", "/requests"),
    ("POST", "/interrupt"),
    ("POST", "/stop"),
    ("POST", "/turns"),
    ("GET", "/turns/{turn_id}"),
    ("GET", "/turns/{turn_id}/events"),
    ("GET", "/turns/{turn_id}/artifacts/{name}"),
}
_BACKING = {
    ("GET", "/gateway/internal/inspect"),
    ("POST", "/gateway/internal/headless-prompt"),
    ("POST", "/gateway/internal/interrupt"),
}
_PROOF_HEADERS = (CHALLENGE_HEADER, SIGNATURE_HEADER, RELAY_HEADER, BACKING_HEADER)
_CLIENT_ROUTE_PATTERNS = tuple(
    (method, compile_path(path)[0]) for method, path in _PRIVATE | _ADMIN
)


@dataclass(frozen=True)
class PassiveAccessTarget:
    """The independently selected owner state for a passive target."""

    runtime: GatewayRuntimeAccess
    policy: GatewayAccessPolicy
    tracked_agent_id: str | None
    manifest_path: Path


@dataclass(frozen=True)
class PassiveAdmission:
    """The selected target and caller grant scoped to the current request."""

    target: PassiveAccessTarget
    grant: GatewayGrant | None
    relay_operations: frozenset[tuple[str, str]] = frozenset()


CURRENT_ADMISSION: ContextVar[PassiveAdmission | None] = ContextVar(
    "houmao_passive_admission", default=None
)


def passive_route_access(method: str, path: str) -> AccessClass | Literal["backing"]:
    """Require an explicit classification for every selected-agent operation."""

    if not path.startswith(_PREFIX):
        return "public"
    key = (method, path.removeprefix(_PREFIX))
    if key in _PUBLIC:
        return "public"
    if key in _PRIVATE:
        return "private"
    if key in _ADMIN:
        return "admin"
    if key in _BACKING:
        return "backing"
    raise RuntimeError(f"Missing passive target access classification for {method} {path}")


def challenge_headers(agent_ref: str) -> dict[str, str]:
    """Return the passive challenge path without exposing proof material."""

    path = f"/houmao/agents/{quote(agent_ref, safe='')}/auth/challenge"
    return {"WWW-Authenticate": f'Houmao-SSHSIG challenge="{path}"'}


def passive_client_challenge_path(method: str, path: str) -> str | None:
    """Select proof only for a known protected operation of a selected agent."""

    if not path.startswith("/houmao/agents/"):
        return None
    ref, slash, rest = path.removeprefix("/houmao/agents/").partition("/")
    if not ref or not slash:
        return None
    if any(
        method == verb and pattern.fullmatch(f"/{rest}") for verb, pattern in _CLIENT_ROUTE_PATTERNS
    ):
        return f"/houmao/agents/{ref}/auth/challenge"
    return None


def _relay_operations(http_request: Request) -> frozenset[tuple[str, str]]:
    """Restrict relays to the matched proxy's existing downstream operations."""

    path = http_request.scope["route"].path.removeprefix(_PREFIX)
    method = http_request.method
    for key in ("channel", "reminder_id"):
        if key in http_request.path_params:
            path = path.replace("{" + key + "}", quote(str(http_request.path_params[key]), safe=""))
    if path in {"/gateway", "/state", "/state/detail", "/managed-state", "/managed-state/detail"}:
        return frozenset({("GET", "/v1/status")})
    if path in {"/requests", "/interrupt"}:
        return frozenset({("POST", "/v1/requests")})
    if path == "/gateway/control/refresh":
        return frozenset({("GET", "/v1/native-home"), (method, "/v1/control/refresh")})
    if path.startswith(("/gateway/tui/", "/gateway/web/")):
        return frozenset({(method, f"/v1/control{path.removeprefix('/gateway')}")})
    if path.startswith("/gateway/"):
        return frozenset({(method, f"/v1{path.removeprefix('/gateway')}")})
    if path == "/usage" or path.startswith("/mail/"):
        return frozenset({(method, f"/v1{path}")})
    return frozenset()


def proof_failure(
    agent_ref: str, exc: GatewayAccessError, *, offer_challenge: bool = True
) -> JSONResponse:
    """Return a safe admission result applicable to this ingress."""

    status = exc.status_code
    detail = {
        401: "Caller proof is required or invalid",
        403: "Caller has insufficient authority",
        503: "Target access policy is unavailable",
    }.get(status, "Target access denied")
    headers = {"Cache-Control": "no-store"}
    if status == 401 and offer_challenge:
        headers.update(challenge_headers(agent_ref))
    return JSONResponse(
        status_code=status,
        content={"detail": detail, "code": exc.code},
        headers=headers,
    )


def ingress_issuer(request: Request, base_url: str) -> str:
    """Use the configured passive origin and verify the request arrived on it."""

    actual = urlsplit(str(request.base_url))
    configured = urlsplit(base_url)
    try:
        actual_port = actual.port or (443 if actual.scheme == "https" else 80)
        configured_port = configured.port or (443 if configured.scheme == "https" else 80)
    except ValueError:
        raise GatewayAccessError(401, "invalid_proof") from None
    if (actual.scheme, actual.hostname, actual_port) != (
        configured.scheme,
        configured.hostname,
        configured_port,
    ):
        raise GatewayAccessError(401, "invalid_proof")
    return base_url


async def read_bound_body(request: Request, *, limit: int = _MAX_PROTECTED_BYTES) -> bytes:
    """Read bounded raw HTTP bytes before parsing protected content."""

    chunks = bytearray()
    async for chunk in request.stream():
        if len(chunks) + len(chunk) > limit:
            raise GatewayAccessError(413, "request_too_large")
        chunks.extend(chunk)
    return bytes(chunks)


def bind_request(request: Request, body: bytes) -> GatewayRequestBinding:
    """Bind proof to the exact escaped path and raw query used at passive ingress."""

    try:
        raw_path: bytes = request.scope["raw_path"]
        return GatewayRequestBinding.from_request(
            request.method,
            raw_path.decode("ascii"),
            request.scope["query_string"].decode("ascii"),
            body,
        )
    except (KeyError, UnicodeError, ValueError):
        raise GatewayAccessError(401, "invalid_proof") from None


async def issue_passive_challenge(
    service: PassiveServerService, request: Request, agent_ref: str
) -> Response:
    """Issue a self or admin challenge for the current selected target."""

    try:
        issuer = ingress_issuer(request, service.m_config.api_base_url)
        encoded = await read_bound_body(request, limit=64 * 1024)
        challenge = parse_access_document(GatewayChallengeRequest, encoded)
        if challenge.purpose == "register" or any(
            name in request.headers for name in _PROOF_HEADERS
        ):
            raise GatewayAccessError(403, "insufficient_authority")
        path_parts = challenge.request.path.split("/")
        if len(path_parts) < 5 or path_parts[1:4] != [
            "houmao",
            "agents",
            quote(agent_ref, safe=""),
        ]:
            raise GatewayAccessError(403, "insufficient_authority")
        target = await run_in_threadpool(service.resolve_access_target, agent_ref)
        if isinstance(target, tuple):
            return JSONResponse(status_code=target[0], content=target[1])
        value = await run_in_threadpool(target.policy.issue, issuer, challenge)
        return JSONResponse(
            content=value.model_dump(mode="json"), headers={"Cache-Control": "no-store"}
        )
    except GatewayAccessError as exc:
        return proof_failure(agent_ref, exc)
    except (ValueError, ClientDisconnect):
        return JSONResponse(status_code=422, content={"detail": "Invalid challenge request"})


class PassiveTargetRoute(APIRoute):
    """Check selected-agent proof before FastAPI parses the operation body."""

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        """Wrap the matched route with selected-agent admission."""

        handler = super().get_route_handler()
        classes = {method: passive_route_access(method, self.path) for method in self.methods or ()}

        async def admitted_handler(request: Request) -> Response:
            """Resolve the target, admit the caller, then run the matched operation."""

            access = classes[request.method]
            if access == "public":
                return await handler(request)
            agent_ref = str(request.path_params["agent_ref"])
            service: PassiveServerService = request.app.state.passive_service
            target = await run_in_threadpool(service.resolve_access_target, agent_ref)
            if isinstance(target, tuple):
                return JSONResponse(status_code=target[0], content=target[1])
            try:
                admission, admitted_request = await _admit_request(service, request, target, access)
                await run_in_threadpool(service.require_access_target_current, target)
            except GatewayAccessError as exc:
                return proof_failure(agent_ref, exc, offer_challenge=access != "backing")
            except ClientDisconnect:
                return JSONResponse(status_code=400, content={"detail": "Incomplete request"})
            except (OSError, RuntimeError, ValueError):
                return proof_failure(agent_ref, GatewayAccessError(503, "policy_unavailable"))
            token = CURRENT_ADMISSION.set(admission)
            try:
                response = await handler(admitted_request)
                if response.status_code == 401 and access != "backing":
                    response.headers.update(challenge_headers(agent_ref))
                    response.headers["Cache-Control"] = "no-store"
                return response
            except GatewayAccessError as exc:
                return proof_failure(agent_ref, exc, offer_challenge=access != "backing")
            finally:
                CURRENT_ADMISSION.reset(token)

        return admitted_handler


async def _admit_request(
    service: PassiveServerService,
    request: Request,
    target: PassiveAccessTarget,
    access: AccessClass | Literal["backing"],
) -> tuple[PassiveAdmission, Request]:
    """Admit only a current selected credential through its matching mechanism."""

    proof = {name: request.headers.getlist(name) for name in _PROOF_HEADERS}
    if any(len(values) > 1 for values in proof.values()) or proof[RELAY_HEADER]:
        raise GatewayAccessError(401, "invalid_proof")
    challenge_id = next(iter(proof[CHALLENGE_HEADER]), None)
    signature = next(iter(proof[SIGNATURE_HEADER]), None)
    backing_token = next(iter(proof[BACKING_HEADER]), None)
    base_url = service.m_config.api_base_url
    if access == "backing":
        if not backing_token or challenge_id is not None or signature is not None:
            raise GatewayAccessError(403, "insufficient_authority")
        if target.tracked_agent_id is None:
            raise GatewayAccessError(403, "insufficient_authority")
        issuer = ingress_issuer(request, base_url)
        body = await read_bound_body(request)
        await run_in_threadpool(
            consume_passive_backing,
            target.runtime.private_root,
            binding=PassiveBackingBinding(
                target=target.runtime.target,
                api_base_url=issuer,
                tracked_agent_id=target.tracked_agent_id,
            ),
            request=bind_request(request, body),
            token=backing_token,
        )
        return PassiveAdmission(target, None), _request_with_body(request, body)
    if backing_token is not None:
        raise GatewayAccessError(403, "insufficient_authority")
    if bool(challenge_id) != bool(signature) or challenge_id == "" or signature == "":
        raise GatewayAccessError(401, "invalid_proof")
    if challenge_id is None:
        grant = await run_in_threadpool(
            target.policy.admit, access, issuer=base_url, request=bind_request(request, b"")
        )
        return PassiveAdmission(target, grant, _relay_operations(request)), request
    issuer = ingress_issuer(request, base_url)
    body = await read_bound_body(request)
    grant = await run_in_threadpool(
        target.policy.admit,
        access,
        issuer=issuer,
        request=bind_request(request, body),
        challenge_id=challenge_id,
        signature=signature,
    )
    return PassiveAdmission(target, grant, _relay_operations(request)), _request_with_body(
        request, body
    )


def _request_with_body(request: Request, body: bytes) -> Request:
    """Provide FastAPI the same bytes the ingress already verified."""

    sent = False

    async def receive() -> Message:
        """Replay the bounded HTTP body to the operation parser."""

        nonlocal sent
        if not sent:
            sent = True
            return {"type": "http.request", "body": body, "more_body": False}
        return await request.receive()

    credential_names = {name.lower().encode("ascii") for name in _PROOF_HEADERS}
    scope = dict(request.scope)
    scope["headers"] = [
        (name, value) for name, value in scope["headers"] if name not in credential_names
    ]
    return Request(scope, receive=receive)
