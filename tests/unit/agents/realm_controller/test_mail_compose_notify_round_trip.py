"""End-to-end-ish round-trip test for notify-block extraction at gateway compose time.

Composes a canonical mailbox message through the same code path the gateway
adapter uses for its `send()`/`post()` flows, asserts the staged document on
disk preserves both the explicit-flag form and the body-fence form, and
asserts caller-supplied `notify_block` wins over body extraction.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from houmao.agents.realm_controller.gateway_mailbox import (
    FilesystemGatewayMailboxAdapter,
    _generate_filesystem_message_id,
)
from houmao.mailbox.managed import DeliveryRequest, ManagedPrincipal
from houmao.mailbox.protocol import MailboxNotifyAuth, parse_message_document


def _make_request(*, message_id: str, sender: ManagedPrincipal) -> DeliveryRequest:
    staged_message_path = Path("/tmp") / f"notify-roundtrip-{message_id}.md"
    return DeliveryRequest(
        staged_message_path=staged_message_path,
        message_id=message_id,
        thread_id=message_id,
        in_reply_to=None,
        references=(),
        created_at_utc="2026-04-25T12:00:00Z",
        sender=sender,
        to=(
            ManagedPrincipal(
                principal_id="HOUMAO-bob",
                address="bob@houmao.localhost",
            ),
        ),
        cc=(),
        reply_to=(),
        subject="hello",
        attachments=(),
        headers={},
    )


def _adapter() -> FilesystemGatewayMailboxAdapter:
    """Build a bare adapter usable only for `_write_staged_message`."""

    return object.__new__(FilesystemGatewayMailboxAdapter)


def test_write_staged_message_extracts_body_fence_into_notify_block(
    tmp_path: Path,
) -> None:
    sender = ManagedPrincipal(
        principal_id="HOUMAO-alice",
        address="alice@houmao.localhost",
    )
    message_id = _generate_filesystem_message_id(datetime.now(UTC))
    staged = tmp_path / "staged.md"
    body = "Hi bob,\n\n```houmao-notify\nre-run on official path\n```\n\nFull report inline."

    adapter = _adapter()
    adapter._write_staged_message(  # type: ignore[attr-defined]
        staged_message_path=staged,
        request=_make_request(message_id=message_id, sender=sender),
        body_content=body,
    )

    parsed = parse_message_document(staged.read_text(encoding="utf-8"))
    assert parsed.notify_block == "re-run on official path"
    assert parsed.notify_auth is None
    assert "```houmao-notify" in parsed.body_markdown


def test_write_staged_message_caller_value_overrides_body_fence(tmp_path: Path) -> None:
    sender = ManagedPrincipal(
        principal_id="HOUMAO-alice",
        address="alice@houmao.localhost",
    )
    message_id = _generate_filesystem_message_id(datetime.now(UTC))
    staged = tmp_path / "staged.md"
    body = "```houmao-notify\nfrom body fence\n```\n"

    adapter = _adapter()
    adapter._write_staged_message(  # type: ignore[attr-defined]
        staged_message_path=staged,
        request=_make_request(message_id=message_id, sender=sender),
        body_content=body,
        notify_block="explicit caller value",
    )

    parsed = parse_message_document(staged.read_text(encoding="utf-8"))
    assert parsed.notify_block == "explicit caller value"


def test_write_staged_message_preserves_notify_auth(tmp_path: Path) -> None:
    sender = ManagedPrincipal(
        principal_id="HOUMAO-alice",
        address="alice@houmao.localhost",
    )
    message_id = _generate_filesystem_message_id(datetime.now(UTC))
    staged = tmp_path / "staged.md"
    auth = MailboxNotifyAuth(scheme="none", token="bearer-xyz", iss="HOUMAO-alice")

    adapter = _adapter()
    adapter._write_staged_message(  # type: ignore[attr-defined]
        staged_message_path=staged,
        request=_make_request(message_id=message_id, sender=sender),
        body_content="ordinary body",
        notify_block="continue current task",
        notify_auth=auth,
    )

    parsed = parse_message_document(staged.read_text(encoding="utf-8"))
    assert parsed.notify_block == "continue current task"
    assert parsed.notify_auth == auth
