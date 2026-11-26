"""Relay signed online mail rules to an independent Stalwart policy authority."""

from __future__ import annotations

from urllib.parse import urlsplit

import httpx
from pydantic import ValidationError

from houmao.mailbox.policy import MailPolicyReceipt, SignedMailPolicyUpdate

_CONNECTOR_ROUTE = "/v1/mail-policy/apply"
_MAX_RECEIPT_BYTES = 16 * 1024


class StalwartPolicyConnector:
    """Forward signed requests without mailbox or provider management credentials."""

    def __init__(self, base_url: str) -> None:
        """Pin the explicitly configured HTTPS endpoint."""

        url = urlsplit(base_url)
        if (
            url.scheme != "https"
            or not url.hostname
            or url.username is not None
            or url.password is not None
            or url.query
            or url.fragment
            or url.path.rstrip("/")
        ):
            raise ValueError("Stalwart policy connector must be an HTTPS origin.")
        self.m_url: str = base_url.rstrip("/") + _CONNECTOR_ROUTE

    def apply(self, request: SignedMailPolicyUpdate) -> MailPolicyReceipt:
        """Return a scoped connector result without retrying a possible mutation."""

        operation_id = request.update.operation_id
        try:
            with httpx.stream(
                "POST",
                self.m_url,
                content=request.model_dump_json().encode(),
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                timeout=10,
                follow_redirects=False,
                trust_env=False,
            ) as response:
                if response.status_code in {404, 405, 501}:
                    return MailPolicyReceipt(status="unsupported", operation_id=operation_id)
                if not response.is_success:
                    detail = "Stalwart policy connector did not confirm the update."
                    return MailPolicyReceipt(
                        status="uncertain", operation_id=operation_id, detail=detail
                    )
                payload = bytearray()
                for chunk in response.iter_bytes(chunk_size=4096):
                    payload.extend(chunk)
                    if len(payload) > _MAX_RECEIPT_BYTES:
                        raise ValueError("Stalwart policy receipt exceeded its transfer limit.")
            receipt = MailPolicyReceipt.model_validate_json(payload)
            if receipt.operation_id != operation_id or (
                receipt.status == "applied"
                and receipt.revision != request.update.expected_revision + 1
            ):
                raise ValueError("Stalwart policy receipt named another operation or revision.")
        except (httpx.HTTPError, ValidationError, ValueError):
            return MailPolicyReceipt(
                status="uncertain",
                operation_id=operation_id,
                detail="Stalwart policy connector did not confirm the update.",
            )
        return receipt
