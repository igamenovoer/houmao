"""Tests for the canonical envelope notify-block and notify-auth fields."""

from __future__ import annotations

import pytest

from houmao.mailbox.protocol import (
    MAILBOX_PROTOCOL_VERSION,
    NOTIFY_BLOCK_MAX_CHARS,
    MailboxMessage,
    MailboxNotifyAuth,
    MailboxPrincipal,
    parse_message_document,
    serialize_message_document,
)


_MID = "msg-20260425T120000Z-a1b2c3d4e5f64798aabbccddeeff0011"
_PRINCIPAL_FROM = MailboxPrincipal(
    principal_id="HOUMAO-alice",
    address="alice@houmao.localhost",
)
_PRINCIPAL_TO = MailboxPrincipal(
    principal_id="HOUMAO-bob",
    address="bob@houmao.localhost",
)


def _base_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "message_id": _MID,
        "thread_id": _MID,
        "created_at_utc": "2026-04-25T12:00:00Z",
        "from": _PRINCIPAL_FROM,
        "to": [_PRINCIPAL_TO],
        "subject": "hello",
        "body_markdown": "ordinary body content",
    }
    payload.update(overrides)
    return payload


def test_protocol_version_is_two() -> None:
    assert MAILBOX_PROTOCOL_VERSION == 2


def test_notify_auth_scheme_none_is_accepted() -> None:
    auth = MailboxNotifyAuth(scheme="none")

    assert auth.scheme == "none"
    assert auth.token is None


def test_notify_auth_optional_claims_round_trip() -> None:
    auth = MailboxNotifyAuth(
        scheme="none",
        token="opaque-bearer",
        iss="HOUMAO-alice",
        iat="2026-04-25T12:00:00Z",
        exp="2026-04-25T12:30:00Z",
    )

    assert auth.token == "opaque-bearer"
    assert auth.iss == "HOUMAO-alice"
    assert auth.iat == "2026-04-25T12:00:00Z"
    assert auth.exp == "2026-04-25T12:30:00Z"


@pytest.mark.parametrize("scheme", ["shared-token", "hmac-sha256", "jws"])
def test_notify_auth_rejects_non_none_schemes(scheme: str) -> None:
    with pytest.raises(ValueError, match="verifier not yet supported"):
        MailboxNotifyAuth(scheme=scheme)  # type: ignore[arg-type]


def test_notify_auth_rejects_blank_optional_claims() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        MailboxNotifyAuth(scheme="none", token="   ")


def test_message_defaults_have_no_notify_fields() -> None:
    message = MailboxMessage.compose(_base_payload())

    assert message.notify_block is None
    assert message.notify_auth is None


def test_message_round_trip_preserves_notify_block_and_auth() -> None:
    auth = MailboxNotifyAuth(scheme="none", token="opaque")
    message = MailboxMessage.compose(
        _base_payload(notify_block="re-run on official path", notify_auth=auth)
    )

    rendered = serialize_message_document(message)
    parsed = parse_message_document(rendered)

    assert parsed.notify_block == "re-run on official path"
    assert parsed.notify_auth == auth
    assert parsed == message


def test_message_validator_truncates_oversize_notify_block_visibly() -> None:
    payload = _base_payload(notify_block="x" * (NOTIFY_BLOCK_MAX_CHARS + 100))

    message = MailboxMessage.compose(payload)

    assert message.notify_block is not None
    assert len(message.notify_block) == NOTIFY_BLOCK_MAX_CHARS
    assert message.notify_block.endswith("…")
    assert message.notify_block[:-1] == "x" * (NOTIFY_BLOCK_MAX_CHARS - 1)


def test_message_validator_normalizes_blank_notify_block_to_none() -> None:
    message = MailboxMessage.compose(_base_payload(notify_block="   \n  "))

    assert message.notify_block is None


def test_message_rejects_nul_byte_in_notify_block() -> None:
    with pytest.raises(ValueError, match="must not contain NUL bytes"):
        MailboxMessage.compose(_base_payload(notify_block="bad\x00content"))


def test_message_rejects_unsupported_notify_auth_scheme_at_envelope_construction() -> None:
    with pytest.raises(ValueError, match="verifier not yet supported"):
        MailboxMessage.compose(_base_payload(notify_auth={"scheme": "hmac-sha256"}))


def test_legacy_v1_envelope_is_rejected_at_validation() -> None:
    payload = _base_payload(protocol_version=1)

    with pytest.raises(ValueError, match="must be 2"):
        MailboxMessage.compose(payload)


def test_v2_envelope_without_notify_fields_remains_valid() -> None:
    message = MailboxMessage.compose(_base_payload(protocol_version=2))

    assert message.protocol_version == 2
    assert message.notify_block is None
    assert message.notify_auth is None
