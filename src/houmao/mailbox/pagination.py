"""Bounded metadata page contracts and scope-independent backend cursors."""

from __future__ import annotations

import base64
from dataclasses import dataclass
import hashlib
import json
from typing import Mapping

from houmao.mailbox.models import (
    GatewayMailListResponseV1,
    GatewayMailboxMessageV1,
    MailboxBackendStatusV1,
)
from houmao.mailbox.scope import MailboxScopeError

DEFAULT_MAIL_PAGE_SIZE = 50
MAX_MAIL_PAGE_SIZE = 200


class MailboxCursorError(MailboxScopeError):
    """A continuation cannot safely target this query snapshot."""

    def __init__(self, message: str, *, stale: bool = False) -> None:
        """Expose a structured distinction between drift and invalid targeting."""

        super().__init__(message)
        self.m_error_code: str = "stale_mail_cursor" if stale else "invalid_mail_cursor"

    @property
    def error_code(self) -> str:
        """Return the public pagination refusal category."""

        return self.m_error_code


@dataclass(frozen=True)
class BackendMailPage:
    """One finite backend page; its continuation receives outer owner scope."""

    messages: list[GatewayMailboxMessageV1]
    next_cursor: str | None
    has_more: bool
    complete: bool
    total_count: int | None = None


def validate_page_size(limit: int) -> int:
    """Reject absent/unbounded or oversized page requests at service boundaries."""

    if (
        isinstance(limit, bool)
        or not isinstance(limit, int)
        or not 1 <= limit <= MAX_MAIL_PAGE_SIZE
    ):
        raise ValueError(f"mail page limit must be between 1 and {MAX_MAIL_PAGE_SIZE}")
    return limit


def query_fingerprint(query: Mapping[str, object]) -> str:
    """Identify normalized filters and deterministic ordering without credentials."""

    payload = json.dumps(dict(query), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def encode_backend_cursor(*, fingerprint: str, state: str, position: int, account: str) -> str:
    """Encode bounded continuation data; this is not an authorization token."""

    payload = {
        "v": 1,
        "filter": fingerprint,
        "state": state,
        "position": position,
        "account": account,
    }
    return (
        base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode())
        .decode()
        .rstrip("=")
    )


def decode_backend_cursor(cursor: str, *, fingerprint: str, account: str) -> tuple[str, int]:
    """Reject malformed, foreign-account, or changed-filter continuations."""

    try:
        if len(cursor) > 8192:
            raise ValueError("oversized continuation")
        value = json.loads(
            base64.b64decode(cursor + "=" * (-len(cursor) % 4), altchars=b"-_", validate=True)
        )
        if not isinstance(value, dict) or set(value) != {
            "v",
            "filter",
            "state",
            "position",
            "account",
        }:
            raise ValueError("invalid continuation fields")
        if value["v"] != 1 or value["filter"] != fingerprint or value["account"] != account:
            raise ValueError("continuation belongs to another query or account")
        if not isinstance(value["state"], str) or not value["state"]:
            raise ValueError("invalid query state")
        position = value["position"]
        if type(position) is not int or not 0 <= position <= 9223372036854775807:
            raise ValueError("invalid position")
        return value["state"], position
    except (ValueError, TypeError, UnicodeError) as exc:
        raise MailboxCursorError(
            "Invalid continuation for this account/filter; start a fresh page"
        ) from exc


def build_mail_page_response(
    *,
    identity: MailboxBackendStatusV1,
    box: str,
    page: BackendMailPage,
) -> GatewayMailListResponseV1:
    """Describe page counts without presenting a sample as the whole mailbox."""

    return GatewayMailListResponseV1(
        transport=identity.transport,
        principal_id=identity.principal_id,
        address=identity.address,
        box=box,
        message_count=len(page.messages),
        open_count=sum(message.archived is not True for message in page.messages),
        unread_count=sum(message.unread is True for message in page.messages),
        messages=page.messages,
        next_cursor=page.next_cursor,
        has_more=page.has_more,
        complete=page.complete,
        total_count=page.total_count,
    )
