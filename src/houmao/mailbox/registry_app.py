"""Narrow offline-registry HTTP application with no body lifecycle routes."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, FastAPI, Header, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, SecretStr

from houmao.mailbox.models import (
    GatewayMailArchiveRequestV1,
    GatewayMailListRequestV1,
    GatewayMailListResponseV1,
    GatewayMailMarkRequestV1,
    GatewayMailMessageRequestV1,
    GatewayMailMoveRequestV1,
    GatewayMailReplyRequestV1,
    GatewayMailSendRequestV1,
)
from houmao.mailbox.registry import (
    OfflineRegistryError,
    OfflineRegistryService,
    RegistryEnrollment,
    RegistryMember,
)
from houmao.mailbox.registry_config import OfflineRegistryConfig
from houmao.mailbox.scope import MailboxScopeError
from houmao.mailbox.pagination import MailboxCursorError
from houmao.mailbox.services import GatewayMailboxError, GatewayMailboxUnsupportedError


class _CredentialReplacement(BaseModel):
    """Secret administrative replacement request, excluded from diagnostics."""

    model_config = ConfigDict(extra="forbid")
    member_credential: SecretStr


def create_offline_registry_app(*, config: OfflineRegistryConfig) -> FastAPI:
    """Build only health, administrative membership, and owner-scoped mail APIs."""

    service = OfflineRegistryService.from_config(config)
    app = FastAPI(title="Houmao Offline Registry", docs_url=None, redoc_url=None, openapi_url=None)

    def member_token(authorization: Annotated[str | None, Header()] = None) -> str:
        """Require an explicit bearer credential, never an agent ID."""

        if authorization is None or not authorization.startswith("Bearer "):
            raise OfflineRegistryError("unauthorized", "bearer credential required", 401)
        return authorization.removeprefix("Bearer ")

    def admin_token(credential: str = Depends(member_token)) -> str:
        """Authorize administrative membership mutation separately from member mail."""

        service.require_admin(credential)
        return credential

    @app.exception_handler(OfflineRegistryError)
    async def registry_error(_request: Request, exc: OfflineRegistryError) -> JSONResponse:
        """Return stable public errors without request/credential echo."""

        return JSONResponse(status_code=exc.status, content={"code": exc.code, "detail": str(exc)})

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
        """Remove Pydantic input and context values that may contain a submitted token."""

        return JSONResponse(
            status_code=422,
            content={
                "code": "invalid_request",
                "detail": [
                    {"loc": list(error["loc"]), "type": error["type"], "msg": error["msg"]}
                    for error in exc.errors()
                ],
            },
        )

    @app.exception_handler(MailboxScopeError)
    async def scope_error(_request: Request, _exc: MailboxScopeError) -> JSONResponse:
        """Preserve stale owner/binding conflicts without backend side effects."""

        return JSONResponse(
            status_code=409,
            content={
                "code": _exc.error_code
                if isinstance(_exc, MailboxCursorError)
                else "binding_conflict",
                "detail": str(_exc)
                if isinstance(_exc, MailboxCursorError)
                else "mail scope changed",
            },
        )

    @app.exception_handler(GatewayMailboxError)
    async def mail_error(_request: Request, exc: GatewayMailboxError) -> JSONResponse:
        """Exclude internal filesystem paths from public backend errors."""

        unsupported = isinstance(exc, GatewayMailboxUnsupportedError)
        return JSONResponse(
            status_code=422 if unsupported else 409,
            content={
                "code": "unsupported_operation" if unsupported else "mail_operation_failed",
                "detail": "offline mail operation could not be completed",
            },
        )

    @app.get("/health")
    def health() -> dict[str, str]:
        """Expose service liveness independently of runtime presence."""

        return {"status": "ok", "mode": "offline-registry"}

    @app.post("/houmao/registry/members", response_model=RegistryMember)
    def enroll(
        request: RegistryEnrollment, _credential: str = Depends(admin_token)
    ) -> RegistryMember:
        """Enroll with a pre-created member token; retries preserve confirmed identity."""

        return service.enroll(request)

    @app.get("/houmao/registry/members/{agent_id}", response_model=RegistryMember)
    def member_status(agent_id: str, _credential: str = Depends(admin_token)) -> RegistryMember:
        """Resolve durable owner membership without consulting runtime leases."""

        return service.member_status(agent_id)

    @app.delete("/houmao/registry/members/{agent_id}", response_model=RegistryMember)
    def release(
        agent_id: str,
        purge: bool = False,
        expected_registration_id: str | None = None,
        _credential: str = Depends(admin_token),
    ) -> RegistryMember:
        """Explicitly release an agent without granting any body-control authority."""

        return service.release(
            agent_id, purge=purge, expected_registration_id=expected_registration_id
        )

    @app.put("/houmao/registry/members/{agent_id}/credential", response_model=RegistryMember)
    def replace_credential(
        agent_id: str,
        request: _CredentialReplacement,
        _credential: str = Depends(admin_token),
    ) -> RegistryMember:
        """Deliberately replace credentials instead of rotating them on ordinary rejoin."""

        return service.replace_credential(agent_id, request.member_credential.get_secret_value())

    @app.get("/houmao/registry/self", response_model=RegistryMember)
    def self_status(credential: str = Depends(member_token)) -> RegistryMember:
        """Resolve authorized durable membership while the body is stopped."""

        return service.self_status(credential)

    @app.delete("/houmao/registry/self", response_model=RegistryMember)
    def self_release(
        expected_registration_id: Annotated[str, Query(min_length=1)],
        credential: str = Depends(member_token),
    ) -> RegistryMember:
        """Allow an authenticated owner to release its own registration."""

        return service.release_self(credential, expected_registration_id=expected_registration_id)

    @app.post("/houmao/registry/self/mail/list", response_model=GatewayMailListResponseV1)
    def list_page(
        request: GatewayMailListRequestV1, credential: str = Depends(member_token)
    ) -> GatewayMailListResponseV1:
        """Preserve bounded page completeness and opaque continuation over HTTP."""

        return service.list_page(credential, request)

    def install_mail_route(operation: str, model: type[BaseModel]) -> None:
        """Register one strict model without exposing a generic arbitrary operation surface."""

        def endpoint(request: Any, credential: str = Depends(member_token)) -> dict[str, object]:
            """Run a fixed owner-scoped lifecycle operation."""

            return {
                "messages": [
                    message.model_dump(mode="json")
                    for message in service.mail(credential, operation, request)
                ]
            }

        endpoint.__annotations__["request"] = model
        app.add_api_route("/houmao/registry/self/mail/" + operation, endpoint, methods=["POST"])

    for operation, model in (
        ("peek", GatewayMailMessageRequestV1),
        ("read", GatewayMailMessageRequestV1),
        ("send", GatewayMailSendRequestV1),
        ("reply", GatewayMailReplyRequestV1),
        ("mark", GatewayMailMarkRequestV1),
        ("move", GatewayMailMoveRequestV1),
        ("archive", GatewayMailArchiveRequestV1),
    ):
        install_mail_route(operation, model)

    @app.post("/houmao/registry/self/attachments")
    async def upload_attachment(
        request: Request,
        x_content_sha256: Annotated[str, Header()],
        content_type: Annotated[str, Header()] = "application/octet-stream",
        x_attachment_label: Annotated[str | None, Header()] = None,
        credential: str = Depends(member_token),
    ) -> dict[str, object]:
        """Bound streaming input before allocating or writing an attachment."""

        service.self_status(credential)
        chunks = bytearray()
        async for chunk in request.stream():
            if len(chunks) + len(chunk) > service.max_attachment_bytes:
                raise OfflineRegistryError(
                    "attachment_too_large", "attachment exceeds transfer limit", 413
                )
            chunks.extend(chunk)
        return service.upload(
            credential,
            bytes(chunks),
            sha256=x_content_sha256,
            media_type=content_type,
            label=x_attachment_label,
        ).model_dump(mode="json")

    @app.get("/houmao/registry/self/attachments/{upload_id}")
    def download_attachment(upload_id: str, credential: str = Depends(member_token)) -> Response:
        """Transfer verified bytes only after message or upload ownership checks."""

        attachment, content = service.download(credential, upload_id)
        return Response(
            content=content,
            media_type=attachment.media_type,
            headers={"X-Content-SHA256": attachment.sha256},
        )

    return app
