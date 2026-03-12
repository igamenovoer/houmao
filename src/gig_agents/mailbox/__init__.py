"""Mailbox protocol and filesystem bootstrap helpers."""

from gig_agents.mailbox.errors import MailboxBootstrapError, MailboxError, MailboxProtocolError
from gig_agents.mailbox.filesystem import (
    FilesystemMailboxPaths,
    bootstrap_filesystem_mailbox,
    read_protocol_version,
    resolve_filesystem_mailbox_paths,
)
from gig_agents.mailbox.protocol import (
    MAILBOX_PROTOCOL_VERSION,
    MESSAGE_ID_PATTERN,
    MailboxAttachment,
    MailboxMessage,
    MailboxPrincipal,
    generate_message_id,
    parse_message_document,
    serialize_message_document,
    validate_message_id,
)

__all__ = [
    "FilesystemMailboxPaths",
    "MAILBOX_PROTOCOL_VERSION",
    "MESSAGE_ID_PATTERN",
    "MailboxAttachment",
    "MailboxBootstrapError",
    "MailboxError",
    "MailboxMessage",
    "MailboxPrincipal",
    "MailboxProtocolError",
    "bootstrap_filesystem_mailbox",
    "generate_message_id",
    "parse_message_document",
    "read_protocol_version",
    "resolve_filesystem_mailbox_paths",
    "serialize_message_document",
    "validate_message_id",
]
