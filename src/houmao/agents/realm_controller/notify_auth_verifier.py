"""Pluggable verifier interface for canonical mailbox notify-block authentication.

The gateway notifier renderer consults a configured verifier to decide whether
a given mailbox message's ``notify_auth`` metadata authorizes its
``notify_block`` content for receiver-prompt rendering. This module defines
the verifier protocol plus two built-in implementations:

- ``PermissiveVerifier`` always passes; used when the gateway is configured
  with ``notify_block_auth_verifier="none"``.
- ``SharedTokenVerifier`` checks ``notify_auth.token`` against a configured
  shared-secret allowlist; used when ``notify_block_auth_verifier="shared-token"``.

Other reserved schemes (``hmac-sha256``, ``jws``) are not yet shipped; the
canonical envelope rejects them at validation. This module's interface is
forward-compatible so future verifier implementations can be added without
re-touching the dispatch surface.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable

from houmao.mailbox.protocol import MailboxNotifyAuth, MailboxNotifyBlock

VerifyOutcome = Literal["skipped", "passed", "failed"]


@dataclass(frozen=True)
class VerifyResult:
    """Outcome of one verifier dispatch.

    Attributes
    ----------
    passed:
        Whether rendering the notify-block is authorized under the current
        verifier. ``True`` for permissive verifiers regardless of input.
    scheme:
        Verifier scheme name reported for audit (``"none"``, ``"shared-token"``,
        ``"hmac-sha256"``, ``"jws"``).
    detail:
        Non-secret diagnostic explaining the outcome. SHOULD NOT echo
        sender-supplied credential material such as raw token values.
    outcome:
        Audit-facing outcome label; ``"skipped"`` when the verifier did not
        actually verify (e.g. permissive default with no notify_auth supplied),
        ``"passed"`` when verification succeeded, ``"failed"`` when it did not.
    """

    passed: bool
    scheme: str
    detail: str | None
    outcome: VerifyOutcome


@runtime_checkable
class NotifyAuthVerifier(Protocol):
    """Verifier interface consulted by the notifier renderer."""

    def verify(
        self,
        notify_block: MailboxNotifyBlock,
        notify_auth: MailboxNotifyAuth | None,
    ) -> VerifyResult:
        """Return the verifier outcome for one notify-block."""


class PermissiveVerifier:
    """Always-pass verifier used when no real verifier is configured."""

    def verify(
        self,
        notify_block: MailboxNotifyBlock,
        notify_auth: MailboxNotifyAuth | None,
    ) -> VerifyResult:
        del notify_block, notify_auth
        return VerifyResult(
            passed=True,
            scheme="none",
            detail="no verifier configured",
            outcome="skipped",
        )


class SharedTokenVerifier:
    """Compare notify_auth.token against a configured allowlist of shared secrets."""

    def __init__(self, token_allowlist: frozenset[str]) -> None:
        self.m_token_allowlist: frozenset[str] = token_allowlist

    def verify(
        self,
        notify_block: MailboxNotifyBlock,
        notify_auth: MailboxNotifyAuth | None,
    ) -> VerifyResult:
        del notify_block
        scheme = "shared-token"
        if notify_auth is None or notify_auth.token is None:
            return VerifyResult(
                passed=False,
                scheme=scheme,
                detail="missing notify_auth.token",
                outcome="failed",
            )
        if notify_auth.token in self.m_token_allowlist:
            return VerifyResult(
                passed=True,
                scheme=scheme,
                detail="token matched allowlist",
                outcome="passed",
            )
        return VerifyResult(
            passed=False,
            scheme=scheme,
            detail="notify_auth.token did not match any allowlisted shared secret",
            outcome="failed",
        )


def build_notify_auth_verifier(
    *,
    verifier_kind: str,
    shared_tokens: list[str] | tuple[str, ...] | None = None,
) -> NotifyAuthVerifier:
    """Build a verifier instance from gateway notifier configuration values.

    Parameters
    ----------
    verifier_kind:
        Either ``"none"`` (returns :class:`PermissiveVerifier`) or
        ``"shared-token"`` (returns :class:`SharedTokenVerifier` with the
        supplied allowlist). Other values raise ``ValueError``.
    shared_tokens:
        Allowlist of accepted shared-secret tokens for the
        ``"shared-token"`` verifier. Ignored for other verifier kinds.

    Returns
    -------
    NotifyAuthVerifier
        The constructed verifier instance.
    """

    if verifier_kind == "none":
        return PermissiveVerifier()
    if verifier_kind == "shared-token":
        return SharedTokenVerifier(frozenset(shared_tokens or ()))
    raise ValueError(f"unsupported notify_block_auth_verifier kind: {verifier_kind!r}")
