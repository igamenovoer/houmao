"""Mailbox protocol and filesystem bootstrap helpers."""

from gig_agents.mailbox.errors import MailboxBootstrapError, MailboxError, MailboxProtocolError
from gig_agents.mailbox.filesystem import (
    FilesystemMailboxPaths,
    MailboxRegistration,
    bootstrap_filesystem_mailbox,
    load_active_mailbox_registration,
    read_protocol_version,
    resolve_active_mailbox_inbox_dir,
    resolve_filesystem_mailbox_paths,
)
from gig_agents.mailbox.protocol import (
    MAILBOX_PROTOCOL_VERSION,
    MESSAGE_ID_PATTERN,
    MailboxAttachment,
    MailboxMessage,
    MailboxPrincipal,
    generate_message_id,
    mailbox_address_path_segment,
    parse_message_document,
    serialize_message_document,
    validate_mailbox_address,
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
    "MailboxRegistration",
    "MailboxProtocolError",
    "bootstrap_filesystem_mailbox",
    "generate_message_id",
    "load_active_mailbox_registration",
    "mailbox_address_path_segment",
    "parse_message_document",
    "read_protocol_version",
    "resolve_active_mailbox_inbox_dir",
    "resolve_filesystem_mailbox_paths",
    "serialize_message_document",
    "validate_mailbox_address",
    "validate_message_id",
]
