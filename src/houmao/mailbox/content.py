"""Bound canonical metadata and selected content reads independently."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from houmao.mailbox.errors import MailboxProtocolError
from houmao.mailbox.protocol import MailboxMessage, parse_message_document

MAX_CANONICAL_METADATA_BYTES = 65536
DEFAULT_CONTENT_BYTES = 65536
METADATA_PREVIEW_BYTES = 512


@dataclass(frozen=True)
class CanonicalContent:
    """A validated envelope with explicitly bounded body content."""

    message: MailboxMessage
    complete: bool
    limit_bytes: int


def read_canonical_content(path: Path, *, metadata_only: bool = False) -> CanonicalContent:
    """Read bounded front matter and either a preview or selected content.

    Parameters
    ----------
    path:
        Actor-authorized canonical document path.
    metadata_only:
        Limit body access to the short metadata preview instead of a content read.

    Returns
    -------
    CanonicalContent
        Envelope, returned-content completeness, and the applied byte limit.
    """

    limit = METADATA_PREVIEW_BYTES if metadata_only else DEFAULT_CONTENT_BYTES
    with path.open("rb") as stream:
        header = bytearray(stream.readline(5))
        if header != b"---\n":
            raise MailboxProtocolError("canonical metadata must start with YAML front matter")
        while True:
            line = stream.readline(MAX_CANONICAL_METADATA_BYTES - len(header) + 1)
            if not line or len(header) + len(line) > MAX_CANONICAL_METADATA_BYTES:
                raise MailboxProtocolError(
                    "canonical metadata exceeds the supported 65536-byte limit"
                )
            header.extend(line)
            if line == b"---\n":
                break
        body = stream.read(limit + 1)
    complete = len(body) <= limit
    preview = body[:limit].decode("utf-8", errors="replace")
    try:
        document = header.decode("utf-8") + preview
        message = parse_message_document(document)
    except UnicodeError as exc:
        raise MailboxProtocolError("canonical metadata is not valid UTF-8") from exc
    return CanonicalContent(message=message, complete=complete, limit_bytes=limit)
