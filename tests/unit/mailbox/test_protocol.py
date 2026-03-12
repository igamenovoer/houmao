from __future__ import annotations

from datetime import UTC, datetime
import re

import pytest

from gig_agents.mailbox.errors import MailboxProtocolError
from gig_agents.mailbox.protocol import (
    MESSAGE_ID_PATTERN,
    MailboxAttachment,
    MailboxMessage,
    MailboxPrincipal,
    generate_message_id,
    parse_message_document,
    serialize_message_document,
)


def test_generate_message_id_uses_timestamp_plus_uuid4_suffix() -> None:
    message_id = generate_message_id(datetime(2026, 3, 11, 4, 15, tzinfo=UTC))

    assert message_id == "msg-20260311T041500Z-" + message_id.rsplit("-", 1)[-1]
    assert MESSAGE_ID_PATTERN.fullmatch(message_id)
    assert re.fullmatch(r"[0-9a-f]{32}", message_id.rsplit("-", 1)[-1])


def test_canonical_message_serialization_round_trips() -> None:
    message = MailboxMessage(
        message_id="msg-20260311T041500Z-a1b2c3d4e5f64798aabbccddeeff0011",
        thread_id="msg-20260311T041500Z-a1b2c3d4e5f64798aabbccddeeff0011",
        created_at_utc="2026-03-11T04:15:00Z",
        sender=MailboxPrincipal(
            principal_id="AGENTSYS-orchestrator",
            address="AGENTSYS-orchestrator@agents.localhost",
        ),
        to=[
            MailboxPrincipal(
                principal_id="AGENTSYS-research",
                address="AGENTSYS-research@agents.localhost",
            )
        ],
        subject="Investigate parser drift",
        body_markdown="Message body in Markdown.\n\nWith a second paragraph.",
        attachments=[
            MailboxAttachment(
                attachment_id="att-20260311T041500Z-a1b2c3d4e5f64798aabbccddeeff0011-01",
                kind="path_ref",
                path="/abs/path/to/report.json",
                media_type="application/json",
                sha256="0" * 64,
                size_bytes=1234,
                label="report.json",
            )
        ],
        headers={"tags": ["parser", "investigation"]},
    )

    rendered = serialize_message_document(message)
    parsed = parse_message_document(rendered)

    assert rendered.startswith("---\nprotocol_version: 1\n")
    assert "from:" in rendered
    assert parsed == message


def test_reply_messages_require_references_ending_with_parent() -> None:
    with pytest.raises(MailboxProtocolError, match="invalid mailbox message document|references"):
        MailboxMessage(
            message_id="msg-20260311T041600Z-a1b2c3d4e5f64798aabbccddeeff0012",
            thread_id="msg-20260311T041500Z-a1b2c3d4e5f64798aabbccddeeff0011",
            in_reply_to="msg-20260311T041500Z-a1b2c3d4e5f64798aabbccddeeff0011",
            references=[],
            created_at_utc="2026-03-11T04:16:00Z",
            sender=MailboxPrincipal(
                principal_id="AGENTSYS-research",
                address="AGENTSYS-research@agents.localhost",
            ),
            to=[
                MailboxPrincipal(
                    principal_id="AGENTSYS-orchestrator",
                    address="AGENTSYS-orchestrator@agents.localhost",
                )
            ],
            subject="Re: Investigate parser drift",
            body_markdown="Acknowledged.",
        )


def test_parse_message_document_rejects_missing_front_matter() -> None:
    with pytest.raises(MailboxProtocolError, match="YAML front matter"):
        parse_message_document("# Not a mailbox document\n")
