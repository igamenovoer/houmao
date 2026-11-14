"""Typed finite-timeout client for the authenticated offline registry API."""

from __future__ import annotations

import hashlib
import hmac
import json
import math
from pathlib import Path
from typing import Literal
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import HTTPRedirectHandler, OpenerDirector, Request, build_opener

from pydantic import BaseModel, SecretStr

from houmao.mailbox.models import (
    GatewayMailboxMessageV1,
    GatewayMailListRequestV1,
    GatewayMailListResponseV1,
)
from houmao.mailbox.registry import (
    OfflineRegistryError,
    RegistryAttachment,
    RegistryEnrollment,
    RegistryMember,
)
from houmao.mailbox.registry_config import read_private_credential, validate_registry_url


class _RejectRedirects(HTTPRedirectHandler):
    """Never forward a private bearer credential to a redirected endpoint."""

    def redirect_request(
        self,
        req: Request,
        fp: object,
        code: int,
        msg: str,
        headers: object,
        newurl: str,
    ) -> None:
        """Let urllib return the original redirect as a structured HTTP failure."""

        return None


class OfflineRegistryClient:
    """Access one explicitly selected registry with one private bearer credential."""

    def __init__(self) -> None:
        """Initialize an unconfigured client; use ``from_url``."""

        self.m_opener: OpenerDirector = build_opener(_RejectRedirects())
        self.m_url: str
        self.m_credential_file: Path
        self.m_timeout_seconds: float
        self.m_max_transfer_bytes: int

    @classmethod
    def from_url(
        cls,
        url: str,
        credential_file: Path,
        *,
        timeout_seconds: float = 10.0,
        max_transfer_bytes: int = 10 * 1024 * 1024,
    ) -> OfflineRegistryClient:
        """Select a protected endpoint with bounded network and transfer resources."""

        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("registry timeout must be finite and positive")
        if max_transfer_bytes < 1:
            raise ValueError("attachment transfer limit must be positive")
        instance = cls()
        instance.m_url = validate_registry_url(url)
        instance.m_credential_file = credential_file.expanduser().resolve()
        read_private_credential(instance.m_credential_file)
        instance.m_timeout_seconds = timeout_seconds
        instance.m_max_transfer_bytes = max_transfer_bytes
        return instance

    def self_status(self) -> RegistryMember:
        """Resolve the credential's durable member, independently of runtime presence."""

        return RegistryMember.model_validate(self._json("GET", "/houmao/registry/self"))

    def member_status(self, agent_id: str) -> RegistryMember:
        """Resolve an agent's durable ownership with administrative authorization."""

        return RegistryMember.model_validate(
            self._json(
                "GET",
                "/houmao/registry/members/" + quote(agent_id, safe=""),
            )
        )

    def enroll(
        self,
        *,
        agent_id: str,
        address: str,
        member_credential: str,
        display_name: str | None = None,
    ) -> RegistryMember:
        """Enroll using this client's admin credential and a caller-prepared member token."""

        request = RegistryEnrollment(
            agent_id=agent_id,
            address=address,
            member_credential=SecretStr(member_credential),
            display_name=display_name,
        )
        payload = request.model_dump(mode="json")
        payload["member_credential"] = request.member_credential.get_secret_value()
        return RegistryMember.model_validate(
            self._json("POST", "/houmao/registry/members", payload)
        )

    def release(
        self,
        agent_id: str | None = None,
        *,
        purge: bool = False,
        expected_registration_id: str | None = None,
    ) -> RegistryMember:
        """Release own membership or an explicitly selected administrative member."""

        if agent_id is None:
            if not expected_registration_id:
                raise ValueError("member release requires its expected registration ID")
            if purge:
                raise ValueError(
                    "member self release is non-destructive; purge requires administration"
                )
            path = "/houmao/registry/self"
        else:
            path = "/houmao/registry/members/" + quote(agent_id, safe="")
        query: dict[str, str] = {}
        if purge:
            query["purge"] = "true"
        if expected_registration_id is not None:
            query["expected_registration_id"] = expected_registration_id
        if query:
            path += "?" + urlencode(query)
        return RegistryMember.model_validate(self._json("DELETE", path))

    def replace_credential(self, agent_id: str, member_credential: str) -> RegistryMember:
        """Perform explicit administrative credential replacement."""

        return RegistryMember.model_validate(
            self._json(
                "PUT",
                "/houmao/registry/members/" + quote(agent_id, safe="") + "/credential",
                {"member_credential": member_credential},
            )
        )

    def list_page(self, request: GatewayMailListRequestV1) -> GatewayMailListResponseV1:
        """Preserve continuation and page counts from one authenticated registry."""

        return GatewayMailListResponseV1.model_validate(
            self._json("POST", "/houmao/registry/self/mail/list", request.model_dump(mode="json"))
        )

    def mail(
        self,
        operation: Literal["peek", "read", "send", "reply", "mark", "move", "archive"],
        request: BaseModel,
    ) -> list[GatewayMailboxMessageV1]:
        """Execute one explicit channel operation without changing bindings on conflict."""

        payload = self._json(
            "POST", "/houmao/registry/self/mail/" + operation, request.model_dump(mode="json")
        )
        if not isinstance(payload, dict) or not isinstance(payload.get("messages"), list):
            raise OfflineRegistryError(
                "invalid_response", "registry returned an invalid mail response", 502
            )
        return [GatewayMailboxMessageV1.model_validate(item) for item in payload["messages"]]

    def upload(
        self,
        content: bytes,
        *,
        media_type: str = "application/octet-stream",
        label: str | None = None,
    ) -> RegistryAttachment:
        """Upload bytes without interpreting a remote path as a registry-host path."""

        if len(content) > self.m_max_transfer_bytes:
            raise OfflineRegistryError(
                "attachment_too_large", "attachment exceeds transfer limit", 413
            )
        headers = {
            "Content-Type": media_type,
            "X-Content-SHA256": hashlib.sha256(content).hexdigest(),
        }
        if label is not None:
            headers["X-Attachment-Label"] = label
        body, _ = self._request("POST", "/houmao/registry/self/attachments", content, headers)
        return RegistryAttachment.model_validate_json(body)

    def download(self, attachment_id: str) -> bytes:
        """Retrieve bounded content and verify its SHA-256 response digest."""

        content, headers = self._request(
            "GET",
            "/houmao/registry/self/attachments/" + quote(attachment_id, safe=""),
            max_bytes=self.m_max_transfer_bytes,
        )
        digest = headers.get("x-content-sha256", "")
        if not hmac.compare_digest(hashlib.sha256(content).hexdigest(), digest):
            raise OfflineRegistryError(
                "digest_mismatch", "downloaded attachment failed verification", 502
            )
        return content

    def _json(self, method: str, path: str, payload: object | None = None) -> object:
        """Decode a bounded structured response without retaining request payloads."""

        body = None if payload is None else json.dumps(payload).encode("utf-8")
        content, _ = self._request(method, path, body, {"Content-Type": "application/json"})
        try:
            return json.loads(content)
        except (ValueError, UnicodeError) as exc:
            raise OfflineRegistryError(
                "invalid_response", "registry returned invalid JSON", 502
            ) from exc

    def _request(
        self,
        method: str,
        path: str,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
        *,
        max_bytes: int = 16 * 1024 * 1024,
    ) -> tuple[bytes, dict[str, str]]:
        """Perform one finite-timeout request; failed mutations are never auto-retried."""

        request_headers = dict(headers or {})
        request_headers["Authorization"] = "Bearer " + read_private_credential(
            self.m_credential_file
        )
        request = Request(self.m_url + path, data=body, headers=request_headers, method=method)
        try:
            with self.m_opener.open(request, timeout=self.m_timeout_seconds) as response:
                content = response.read(max_bytes + 1)
                response_headers = {key.lower(): value for key, value in response.headers.items()}
        except HTTPError as exc:
            code = "registry_error"
            try:
                error = json.loads(exc.read(16384))
                if isinstance(error, dict) and isinstance(error.get("code"), str):
                    code = error["code"]
            except (ValueError, UnicodeError):
                pass
            raise OfflineRegistryError(code, "registry rejected the operation", exc.code) from None
        except (URLError, TimeoutError, OSError) as exc:
            raise OfflineRegistryError(
                "registry_unavailable",
                "registry request failed; mutation outcome may be uncertain",
                503,
            ) from exc
        if len(content) > max_bytes:
            raise OfflineRegistryError(
                "response_too_large", "registry response exceeded transfer limit", 502
            )
        return content, response_headers
