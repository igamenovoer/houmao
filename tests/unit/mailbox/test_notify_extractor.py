"""Tests for the houmao-notify body fence extractor and composition wiring."""

from __future__ import annotations

from houmao.mailbox.protocol import (
    NOTIFY_BLOCK_MAX_CHARS,
    MailboxMessage,
    MailboxPrincipal,
    extract_notify_block_from_body,
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


def _base_payload(body: str, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "message_id": _MID,
        "thread_id": _MID,
        "created_at_utc": "2026-04-25T12:00:00Z",
        "from": _PRINCIPAL_FROM,
        "to": [_PRINCIPAL_TO],
        "subject": "hello",
        "body_markdown": body,
    }
    payload.update(overrides)
    return payload


def test_extract_returns_none_for_body_without_fence() -> None:
    assert extract_notify_block_from_body("plain body, no fence") is None


def test_extract_returns_none_for_empty_string() -> None:
    assert extract_notify_block_from_body("") is None


def test_extract_returns_first_fence_contents_trimmed() -> None:
    body = "intro\n\n```houmao-notify\n  re-run on official timing path  \n```\n\noutro"

    assert extract_notify_block_from_body(body) == "re-run on official timing path"


def test_extract_first_fence_wins_over_second() -> None:
    body = (
        "```houmao-notify\nfirst block\n```\n\nmiddle text\n```houmao-notify\nsecond block\n```\n"
    )

    assert extract_notify_block_from_body(body) == "first block"


def test_extract_returns_none_for_blank_fence() -> None:
    body = "```houmao-notify\n   \n  \n```\n"

    assert extract_notify_block_from_body(body) is None


def test_extract_ignores_unrelated_info_strings() -> None:
    body = "```python\nprint('hi')\n```\n```other-fence\nignored\n```"

    assert extract_notify_block_from_body(body) is None


def test_extract_ignores_unterminated_fence() -> None:
    body = "```houmao-notify\nstart but no close"

    assert extract_notify_block_from_body(body) is None


def test_extract_handles_multi_line_fence_content() -> None:
    body = "```houmao-notify\nline one\nline two\nline three\n```"

    assert extract_notify_block_from_body(body) == "line one\nline two\nline three"


def test_extract_tolerates_trailing_whitespace_on_fence_marker_line() -> None:
    body = "```houmao-notify   \nmessage body\n```   "

    assert extract_notify_block_from_body(body) == "message body"


def test_compose_extracts_when_notify_block_key_absent() -> None:
    body = "intro\n\n```houmao-notify\nfrom body fence\n```\n"
    message = MailboxMessage.compose(_base_payload(body))

    assert message.notify_block == "from body fence"
    assert "```houmao-notify" in message.body_markdown


def test_compose_caller_supplied_value_bypasses_body_extraction() -> None:
    body = "intro\n\n```houmao-notify\nfrom body fence\n```\n"
    message = MailboxMessage.compose(_base_payload(body, notify_block="caller wins"))

    assert message.notify_block == "caller wins"


def test_compose_explicit_none_bypasses_body_extraction() -> None:
    body = "intro\n\n```houmao-notify\nfrom body fence\n```\n"
    message = MailboxMessage.compose(_base_payload(body, notify_block=None))

    assert message.notify_block is None


def test_compose_oversize_caller_value_truncates_visibly() -> None:
    long_value = "x" * (NOTIFY_BLOCK_MAX_CHARS + 50)
    message = MailboxMessage.compose(_base_payload("plain body", notify_block=long_value))

    assert message.notify_block is not None
    assert len(message.notify_block) == NOTIFY_BLOCK_MAX_CHARS
    assert message.notify_block.endswith("…")


def test_compose_oversize_body_fence_truncates_visibly() -> None:
    huge = "y" * (NOTIFY_BLOCK_MAX_CHARS + 50)
    body = f"intro\n\n```houmao-notify\n{huge}\n```\n"
    message = MailboxMessage.compose(_base_payload(body))

    assert message.notify_block is not None
    assert len(message.notify_block) == NOTIFY_BLOCK_MAX_CHARS
    assert message.notify_block.endswith("…")


def test_pure_validate_does_not_extract_from_body() -> None:
    """`MailboxMessage.model_validate` does NOT auto-extract; only `compose` does.

    This protects round-trips of stored canonical envelopes from synthesizing
    a `notify_block` field that the original sender did not author.
    """

    body = "intro\n\n```houmao-notify\nshould stay in body only\n```\n"
    message = MailboxMessage.model_validate(_base_payload(body))

    assert message.notify_block is None
    assert "```houmao-notify" in message.body_markdown
