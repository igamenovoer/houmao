"""Mailbox-specific exception types."""

from __future__ import annotations


class MailboxError(RuntimeError):
    """Base error raised by mailbox helpers."""


class MailboxProtocolError(MailboxError):
    """Raised when canonical mailbox data is invalid or malformed."""


class MailboxBootstrapError(MailboxError):
    """Raised when filesystem mailbox bootstrap cannot complete safely."""
