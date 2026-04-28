"""Tests for the notify-auth verifier interface and built-in implementations."""

from __future__ import annotations

import pytest

from houmao.agents.realm_controller.notify_auth_verifier import (
    NotifyAuthVerifier,
    PermissiveVerifier,
    SharedTokenVerifier,
    VerifyResult,
    build_notify_auth_verifier,
)
from houmao.mailbox.protocol import MailboxNotifyAuth, MailboxNotifyBlock


_NOTIFY_BLOCK = MailboxNotifyBlock(text="hello")


def test_permissive_verifier_passes_with_no_notify_auth() -> None:
    verifier = PermissiveVerifier()

    result = verifier.verify(notify_block=_NOTIFY_BLOCK, notify_auth=None)

    assert result.passed is True
    assert result.scheme == "none"
    assert result.outcome == "skipped"
    assert result.detail == "no verifier configured"


def test_permissive_verifier_passes_with_notify_auth_present() -> None:
    verifier = PermissiveVerifier()
    auth = MailboxNotifyAuth(scheme="none", token="ignored")

    result = verifier.verify(notify_block=_NOTIFY_BLOCK, notify_auth=auth)

    assert result.passed is True
    assert result.scheme == "none"
    assert result.outcome == "skipped"


def test_shared_token_verifier_accepts_allowlisted_token() -> None:
    verifier = SharedTokenVerifier(frozenset({"bearer-good", "bearer-also-good"}))
    auth = MailboxNotifyAuth(scheme="none", token="bearer-good")

    result = verifier.verify(notify_block=_NOTIFY_BLOCK, notify_auth=auth)

    assert result.passed is True
    assert result.scheme == "shared-token"
    assert result.outcome == "passed"
    assert result.detail == "token matched allowlist"


def test_shared_token_verifier_rejects_unrecognized_token_without_echoing_value() -> None:
    verifier = SharedTokenVerifier(frozenset({"bearer-allowed"}))
    auth = MailboxNotifyAuth(scheme="none", token="super-secret-attacker-token")

    result = verifier.verify(notify_block=_NOTIFY_BLOCK, notify_auth=auth)

    assert result.passed is False
    assert result.scheme == "shared-token"
    assert result.outcome == "failed"
    assert result.detail is not None
    # Critical: the rejection detail must NOT echo the supplied token value.
    assert "super-secret-attacker-token" not in result.detail


def test_shared_token_verifier_rejects_missing_token() -> None:
    verifier = SharedTokenVerifier(frozenset({"bearer-allowed"}))
    auth = MailboxNotifyAuth(scheme="none", token=None)

    result = verifier.verify(notify_block=_NOTIFY_BLOCK, notify_auth=auth)

    assert result.passed is False
    assert result.scheme == "shared-token"
    assert result.outcome == "failed"
    assert result.detail == "missing notify_auth.token"


def test_shared_token_verifier_rejects_when_notify_auth_is_none() -> None:
    verifier = SharedTokenVerifier(frozenset({"bearer-allowed"}))

    result = verifier.verify(notify_block=_NOTIFY_BLOCK, notify_auth=None)

    assert result.passed is False
    assert result.scheme == "shared-token"
    assert result.outcome == "failed"
    assert result.detail == "missing notify_auth.token"


def test_shared_token_verifier_rejects_with_empty_allowlist() -> None:
    verifier = SharedTokenVerifier(frozenset())
    auth = MailboxNotifyAuth(scheme="none", token="any-token-at-all")

    result = verifier.verify(notify_block=_NOTIFY_BLOCK, notify_auth=auth)

    assert result.passed is False
    assert result.outcome == "failed"


def test_factory_builds_permissive_verifier_for_none_kind() -> None:
    verifier = build_notify_auth_verifier(verifier_kind="none")

    assert isinstance(verifier, PermissiveVerifier)


def test_factory_builds_shared_token_verifier_with_allowlist() -> None:
    verifier = build_notify_auth_verifier(
        verifier_kind="shared-token",
        shared_tokens=("bearer-a", "bearer-b"),
    )

    assert isinstance(verifier, SharedTokenVerifier)
    # Probe the resulting verifier behavior so the test does not depend on
    # private attribute names.
    auth_ok = MailboxNotifyAuth(scheme="none", token="bearer-a")
    auth_bad = MailboxNotifyAuth(scheme="none", token="bearer-c")
    assert verifier.verify(notify_block=_NOTIFY_BLOCK, notify_auth=auth_ok).passed is True
    assert verifier.verify(notify_block=_NOTIFY_BLOCK, notify_auth=auth_bad).passed is False


def test_factory_rejects_unknown_verifier_kind() -> None:
    with pytest.raises(ValueError, match="unsupported notify_block_auth_verifier kind"):
        build_notify_auth_verifier(verifier_kind="hmac-sha256")


def test_verify_result_is_a_frozen_dataclass() -> None:
    result = VerifyResult(passed=True, scheme="none", detail=None, outcome="skipped")

    with pytest.raises(Exception):
        result.passed = False  # type: ignore[misc]


def test_verifier_protocol_runtime_checkable_recognizes_built_ins() -> None:
    assert isinstance(PermissiveVerifier(), NotifyAuthVerifier)
    assert isinstance(SharedTokenVerifier(frozenset()), NotifyAuthVerifier)
