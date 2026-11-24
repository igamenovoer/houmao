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
from houmao.agents.realm_controller.gateway_models import (
    GatewayRequestCreateV1,
    GatewayRequestPayloadSubmitPromptV1,
)
from houmao.gateway.access import (
    CHALLENGE_HEADER,
    SIGNATURE_HEADER,
    GatewayAccessError,
    GatewayAccessPolicy,
    GatewayChallengeRequest,
    GatewayGrant,
    GatewayRequestBinding,
    parse_access_document,
)
from houmao.gateway.authorization_models import AuthorizationDecision, Permission
from houmao.gateway.operations import (
    CORE_OPERATIONS,
    INTERRUPT,
    MAIL_ACTIONS,
    STATUS,
    WORK_REQUEST,
    GatewayOperation,
    prompt_permissions,
)
from houmao.gateway.owner_authority import (
    BACKING_HEADER,
    RELAY_HEADER,
    PassiveBackingBinding,
    consume_passive_backing,
)

from houmao.passive_server.models import (
    PassiveHeadlessTurnRequest,
    PassivePromptRequest,
    PassiveProofEndpoint,
)

if TYPE_CHECKING:
    from houmao.passive_server.service import PassiveServerService


_PREFIX = "/houmao/agents/{agent_ref}"
_MAX_PROTECTED_BYTES = 16 * 1024 * 1024
_PUBLIC = {
    ("GET", ""),
    ("GET", "/resolve"),
    ("GET", "/auth/endpoint"),
    ("POST", "/auth/challenge"),
}
_BACKING = {
    ("GET", "/gateway/internal/inspect"),
    ("POST", "/gateway/internal/headless-prompt"),
    ("POST", "/gateway/internal/interrupt"),
}
_PROOF_HEADERS = (CHALLENGE_HEADER, SIGNATURE_HEADER, RELAY_HEADER, BACKING_HEADER)


@dataclass(frozen=True)
class PassiveOperation:
    """Declare a matched passive effect and the exact gateway routes it may use."""

    permission: Permission | None = None
    downstream: tuple[tuple[str, GatewayOperation], ...] = ()
    selector: Literal["turn", "prompt", "work-request"] | None = None
    additional_permissions: tuple[Permission, ...] = ()

    def permissions(self, body: bytes, *, channel: str | None) -> tuple[Permission, ...]:
        """Check local intent or evaluate the explicit set of proxy operations."""

        if self.selector == "work-request":
            try:
                work_request = parse_access_document(GatewayRequestCreateV1, body)
            except ValueError:
                raise GatewayAccessError(422, "invalid_operation") from None
            if work_request.kind != "submit_work_request":
                raise GatewayAccessError(422, "invalid_operation")
            return (WORK_REQUEST,)
        if self.selector == "prompt":
            try:
                prompt = parse_access_document(PassivePromptRequest, body)
                return prompt_permissions(GatewayRequestPayloadSubmitPromptV1(prompt=prompt.prompt))
            except ValueError:
                raise GatewayAccessError(422, "invalid_operation") from None
        if self.selector == "turn":
            try:
                payload = parse_access_document(PassiveHeadlessTurnRequest, body)
            except ValueError:
                raise GatewayAccessError(422, "invalid_operation") from None
            return prompt_permissions(
                GatewayRequestPayloadSubmitPromptV1(
                    prompt=payload.prompt,
                    chat_session=payload.chat_session,
                    execution=payload.execution,
                )
            )
        if self.permission is not None:
            return (self.permission, *self.additional_permissions)
        return tuple(
            permission
            for _method, operation in self.downstream
            for permission in operation.bind_channel(channel).permissions(body)
        )


def _gateway_operation(method: str, path: str) -> tuple[str, GatewayOperation]:
    """Resolve a declared core route before running the passive HTTP listener."""

    return method, CORE_OPERATIONS[method, path]


def _proxy(method: str, path: str) -> PassiveOperation:
    """Declare one passive proxy forwarding a core gateway operation."""

    return PassiveOperation(downstream=(_gateway_operation(method, path),))


def _local(resource: str, action: str) -> PassiveOperation:
    """Declare an effect performed directly in the passive server."""

    return PassiveOperation(permission=Permission(resource=resource, action=action))


_OPERATIONS = {
    ("PUT", "/admin/default-permission-group"): _local("policy", "admin.default-group.set"),
    ("GET", "/usage"): _proxy("GET", "/v1/usage"),
    ("GET", "/gateway"): _proxy("GET", "/v1/status"),
    **{
        (method, f"/gateway{path}"): _proxy(method, f"/v1{path}")
        for method, path in (
            ("GET", "/memory"),
            ("GET", "/memory/memo"),
            ("PUT", "/memory/memo"),
            ("POST", "/memory/memo/append"),
            *(
                ("POST", f"/memory/pages/{action}")
                for action in (
                    "tree",
                    "resolve",
                    "read",
                    "write",
                    "append",
                    "delete",
                )
            ),
            ("GET", "/native-home"),
            ("GET", "/control/headless/state"),
            ("POST", "/control/headless/next-prompt-session"),
            ("POST", "/requests"),
            ("POST", "/control/prompt"),
            ("POST", "/control/send-keys"),
            *((method, "/mail-notifier/{channel}") for method in ("GET", "PUT", "DELETE")),
            ("GET", "/reminders"),
            ("POST", "/reminders"),
            *((method, "/reminders/{reminder_id}") for method in ("GET", "PUT", "DELETE")),
        )
    },
    **{
        (method, "/gateway/control/refresh"): PassiveOperation(
            downstream=(
                _gateway_operation("GET", "/v1/native-home"),
                _gateway_operation(method, "/v1/control/refresh"),
            ),
        )
        for method in ("GET", "POST")
    },
    **{
        (method, f"/gateway{path}"): _proxy(method, f"/v1/control{path}")
        for method, path in (
            ("GET", "/tui/state"),
            ("GET", "/tui/history"),
            ("GET", "/web/state"),
            ("GET", "/web/history"),
            ("POST", "/tui/note-prompt"),
        )
    },
    ("POST", "/gateway/attach"): _local("gateway", "gateway.attach"),
    ("POST", "/gateway/detach"): _local("gateway", "gateway.detach"),
    **{
        (method, path): _proxy(method, f"/v1{path}")
        for method, path in (
            ("GET", "/mail/status"),
            *(("POST", f"/mail/{{channel}}/{action}") for action in MAIL_ACTIONS),
            *((method, "/mail/online/binding") for method in ("GET", "PUT", "DELETE")),
            ("POST", "/mail/online/binding/refresh"),
            ("POST", "/mail/online/binding/reconnect"),
        )
    },
    **{
        ("GET", path): PassiveOperation(
            STATUS, downstream=(_gateway_operation("GET", "/v1/status"),)
        )
        for path in ("/state", "/managed-state")
    },
    **{
        ("GET", path): PassiveOperation(
            Permission(resource="agent", action="agent.state.detail.read"),
            downstream=(_gateway_operation("GET", "/v1/status"),),
            additional_permissions=(STATUS,),
        )
        for path in ("/state/detail", "/managed-state/detail")
    },
    **{
        ("GET", path): _local("agent", "agent.history.read")
        for path in ("/history", "/managed-history")
    },
    ("POST", "/requests"): PassiveOperation(
        selector="prompt", downstream=(_gateway_operation("POST", "/v1/requests"),)
    ),
    ("POST", "/work-requests"): PassiveOperation(WORK_REQUEST, selector="work-request"),
    ("POST", "/interrupt"): PassiveOperation(
        INTERRUPT, downstream=(_gateway_operation("POST", "/v1/requests"),)
    ),
    ("POST", "/stop"): _local("agent", "agent.stop"),
    ("POST", "/turns"): PassiveOperation(selector="turn"),
    ("GET", "/turns/{turn_id}"): _local("agent", "agent.turn.read"),
    ("GET", "/turns/{turn_id}/events"): _local("agent", "agent.turn.events.read"),
    ("GET", "/turns/{turn_id}/artifacts/{name}"): _local("agent", "agent.turn.artifact.read"),
}
PASSIVE_PERMISSIONS = frozenset(
    operation.permission for operation in _OPERATIONS.values() if operation.permission is not None
)
_CLIENT_ROUTE_PATTERNS = tuple((method, compile_path(path)[0]) for method, path in _OPERATIONS)


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
    relay_operations: tuple[tuple[str, str, GatewayOperation], ...] = ()


CURRENT_ADMISSION: ContextVar[PassiveAdmission | None] = ContextVar(
    "houmao_passive_admission", default=None
)


def passive_route_operation(
    method: str, path: str
) -> PassiveOperation | Literal["public", "backing"]:
    """Select the declared effect for every selected-agent route."""

    key = method, path.removeprefix(_PREFIX)
    if not path.startswith(_PREFIX) or key in _PUBLIC:
        return "public"
    if key in _BACKING:
        return "backing"
    if key not in _OPERATIONS:
        raise RuntimeError(f"Missing passive target operation for {method} {path}")
    return _OPERATIONS[key]


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


def _relay_operations(
    operation: PassiveOperation, request: Request
) -> tuple[tuple[str, str, GatewayOperation], ...]:
    """Resolve the matched route's allowed downstream paths and operations."""

    routes = []
    for method, declaration in operation.downstream:
        path = declaration.path
        for name, value in request.path_params.items():
            path = path.replace("{" + name + "}", quote(str(value), safe=""))
        downstream = declaration.bind_channel(request.path_params.get("channel"))
        routes.append((method, path, downstream))
    return tuple(routes)


def proof_failure(
    agent_ref: str | None, exc: GatewayAccessError, *, offer_challenge: bool = True
) -> JSONResponse:
    """Return a safe admission result applicable to this ingress."""

    status = exc.status_code
    detail = {
        401: "Caller proof is required or invalid",
        403: "Caller has insufficient authority",
        409: "Target authorization changed",
        413: "Protected request is too large",
        422: "Invalid protected request",
        503: "Target access policy is unavailable",
    }.get(status, "Target access denied")
    headers = {"Cache-Control": "no-store"}
    if status == 401 and offer_challenge and agent_ref is not None:
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


def describe_passive_endpoint(service: PassiveServerService, agent_ref: str) -> Response:
    """Expose the selected target and current passive proof listener."""

    selected = service.resolve_access_target(agent_ref)
    if isinstance(selected, tuple):
        return JSONResponse(status_code=selected[0], content=selected[1])
    try:
        service.require_access_target_current(selected)
        state = selected.policy.store.snapshot()
    except GatewayAccessError as exc:
        return proof_failure(agent_ref, exc, offer_challenge=False)
    descriptor = PassiveProofEndpoint(
        target=selected.runtime.target,
        presence_id=selected.policy.listener_id,
        admin_mode=state.admin_mode,
        challenge_path=f"/houmao/agents/{quote(agent_ref, safe='')}/auth/challenge",
    )
    return JSONResponse(
        content=descriptor.model_dump(mode="json"), headers={"Cache-Control": "no-store"}
    )


async def issue_passive_challenge(
    service: PassiveServerService, request: Request, agent_ref: str
) -> Response:
    """Issue a caller challenge for the current selected target."""

    try:
        issuer = ingress_issuer(request, service.m_config.api_base_url)
        encoded = await read_bound_body(request, limit=64 * 1024)
        challenge = parse_access_document(GatewayChallengeRequest, encoded)
        if challenge.purpose == "register":
            raise GatewayAccessError(403, "insufficient_authority")
        challenge_path = passive_client_challenge_path(
            challenge.request.method, challenge.request.path
        )
        if challenge_path != f"/houmao/agents/{quote(agent_ref, safe='')}/auth/challenge":
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
        operations = {
            method: passive_route_operation(method, self.path) for method in self.methods or ()
        }

        async def admitted_handler(request: Request) -> Response:
            """Resolve the target, admit the caller, then run the matched operation."""

            operation = operations[request.method]
            if operation == "public":
                if any(name in request.headers for name in _PROOF_HEADERS):
                    return proof_failure(None, GatewayAccessError(401, "invalid_proof"))
                return await handler(request)
            agent_ref = str(request.path_params["agent_ref"])
            service: PassiveServerService = request.app.state.passive_service
            target = await run_in_threadpool(service.resolve_access_target, agent_ref)
            if isinstance(target, tuple):
                return JSONResponse(status_code=target[0], content=target[1])
            try:
                admission, admitted_request = await _admit_request(
                    service, request, target, operation
                )
                await run_in_threadpool(service.require_access_target_current, target)
            except GatewayAccessError as exc:
                return proof_failure(agent_ref, exc, offer_challenge=operation != "backing")
            except ClientDisconnect:
                return JSONResponse(status_code=400, content={"detail": "Incomplete request"})
            except (OSError, RuntimeError, ValueError):
                return proof_failure(agent_ref, GatewayAccessError(503, "policy_unavailable"))
            token = CURRENT_ADMISSION.set(admission)
            try:
                response = await handler(admitted_request)
                if response.status_code == 401 and operation != "backing":
                    response.headers.update(challenge_headers(agent_ref))
                    response.headers["Cache-Control"] = "no-store"
                return response
            except GatewayAccessError as exc:
                return proof_failure(agent_ref, exc, offer_challenge=operation != "backing")
            finally:
                CURRENT_ADMISSION.reset(token)

        return admitted_handler


async def _admit_request(
    service: PassiveServerService,
    request: Request,
    target: PassiveAccessTarget,
    operation: PassiveOperation | Literal["backing"],
) -> tuple[PassiveAdmission, Request]:
    """Admit only a current selected credential through its matching mechanism."""

    proof = {name: request.headers.getlist(name) for name in _PROOF_HEADERS}
    if any(len(values) > 1 for values in proof.values()) or proof[RELAY_HEADER]:
        raise GatewayAccessError(401, "invalid_proof")
    challenge_id = next(iter(proof[CHALLENGE_HEADER]), None)
    signature = next(iter(proof[SIGNATURE_HEADER]), None)
    backing_token = next(iter(proof[BACKING_HEADER]), None)
    base_url = service.m_config.api_base_url
    if operation == "backing":
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
    issuer = ingress_issuer(request, base_url) if challenge_id is not None else base_url
    body = await read_bound_body(request)
    grant = await run_in_threadpool(
        target.policy.admit,
        lambda: operation.permissions(body, channel=request.path_params.get("channel")),
        issuer=issuer,
        request=bind_request(request, body),
        challenge_id=challenge_id,
        signature=signature,
    )
    if not isinstance(grant, AuthorizationDecision):
        raise GatewayAccessError(403, "insufficient_authority")
    return PassiveAdmission(target, grant, _relay_operations(operation, request)), (
        _request_with_body(request, body)
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
