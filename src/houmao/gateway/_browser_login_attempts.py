"""Bound one-time browser claim transitions for a gateway login purpose."""

from __future__ import annotations

import base64
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import json
import re
import secrets
import threading
from typing import Generic, TypeVar

from fastapi import HTTPException

from houmao.gateway.access import GatewayGrant

_Binding = TypeVar("_Binding")
_Ticket = TypeVar("_Ticket")
_LOGIN_LIFETIME = 120
_CLAIM_SECRET = re.compile(r"[A-Za-z0-9_-]{43}")


def _digest(secret: str) -> bytes:
    """Keep claim secrets out of the retained login state."""

    return hashlib.sha256(secret.encode("ascii")).digest()


@dataclass(frozen=True)
class BrowserLoginAttempt(Generic[_Binding]):
    """Pin one signed challenge, initiating browser, and verified target."""

    binding: _Binding
    challenge: bytes = field(repr=False)
    claim_digest: bytes = field(repr=False)
    deadline: float
    approval: GatewayGrant | None = None

    def matches_claim(self, values: Sequence[str]) -> bool:
        """Check the initiating browser's single claim secret."""

        return (
            len(values) == 1
            and _CLAIM_SECRET.fullmatch(values[0]) is not None
            and hmac.compare_digest(self.claim_digest, _digest(values[0]))
        )


class BrowserLoginStore(Generic[_Binding]):
    """Serialize pending challenges, approvals, and claims for a gateway listener."""

    def __init__(
        self,
        *,
        clock: Callable[[], float],
        capacity: Callable[[], int],
        expired_detail: str,
        capacity_detail: str,
    ) -> None:
        """Initialize one bounded collection of attempts for this login purpose."""

        self.m_clock: Callable[[], float] = clock
        self.m_capacity: Callable[[], int] = capacity
        self.m_expired_detail: str = expired_detail
        self.m_capacity_detail: str = capacity_detail
        self.m_lock: threading.Lock = threading.Lock()
        self.m_logins: dict[str, BrowserLoginAttempt[_Binding]] = {}

    def start(
        self,
        binding: _Binding,
        *,
        issuer: str,
        listener: str,
        namespace: str,
        prove_path: str,
        evidence: Mapping[str, object],
    ) -> dict[str, str]:
        """Create an attempt and a purpose-bound SSHSIG challenge."""

        with self.m_lock:
            now = self.m_clock()
            self.m_logins = {
                key: login for key, login in self.m_logins.items() if login.deadline > now
            }
            if len(self.m_logins) >= self.m_capacity():
                raise HTTPException(429, self.m_capacity_detail)
            attempt_id = secrets.token_urlsafe(32)
            secret = secrets.token_urlsafe(32)
            expires_at = (datetime.now(UTC) + timedelta(seconds=_LOGIN_LIFETIME)).isoformat()
            challenge = json.dumps(
                {
                    **evidence,
                    "purpose": namespace,
                    "nonce": secrets.token_urlsafe(32),
                    "issuer": issuer,
                    "listener": listener,
                    "method": "POST",
                    "path": prove_path.format(attempt_id=attempt_id),
                    "expires_at_utc": expires_at,
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode("ascii")
            self.m_logins[attempt_id] = BrowserLoginAttempt(
                binding, challenge, _digest(secret), now + _LOGIN_LIFETIME
            )
            return {
                "attempt_id": attempt_id,
                "challenge": base64.urlsafe_b64encode(challenge).decode("ascii").rstrip("="),
                "claim_secret": secret,
                "expires_at_utc": expires_at,
            }

    def get(self, attempt_id: str) -> BrowserLoginAttempt[_Binding]:
        """Read one live attempt snapshot before revalidating it."""

        with self.m_lock:
            login = self.m_logins.get(attempt_id)
            if login is None or login.deadline <= self.m_clock():
                raise HTTPException(410, self.m_expired_detail)
            return login

    def approve(
        self, attempt_id: str, login: BrowserLoginAttempt[_Binding], grant: GatewayGrant
    ) -> None:
        """Record at most one terminal approval of the verified challenge."""

        with self.m_lock:
            self._require_current(attempt_id, login)
            if login.approval is not None:
                raise HTTPException(410, self.m_expired_detail)
            self.m_logins[attempt_id] = replace(login, approval=grant)

    def claim(
        self,
        attempt_id: str,
        login: BrowserLoginAttempt[_Binding],
        issue: Callable[[_Binding, GatewayGrant], _Ticket],
    ) -> _Ticket:
        """Issue one ticket and consume its approval in the same transition."""

        with self.m_lock:
            self._require_current(attempt_id, login)
            if login.approval is None:
                raise HTTPException(410, self.m_expired_detail)
            ticket = issue(login.binding, login.approval)
            del self.m_logins[attempt_id]
            return ticket

    def _require_current(self, attempt_id: str, login: BrowserLoginAttempt[_Binding]) -> None:
        """Check an attempt by snapshot identity with the transition lock held."""

        if self.m_logins.get(attempt_id) is not login or login.deadline <= self.m_clock():
            raise HTTPException(410, self.m_expired_detail)
