# Mailbox Canonical Model

This page defines the message format that the filesystem mailbox transport treats as authoritative content.

## Mental Model

The mailbox system separates durable message content from per-recipient mailbox state.

- The canonical message is an immutable Markdown file with YAML front matter.
- The file captures who sent the message, who received it, how it threads, and what attachments it refers to.
- Read, starred, archived, deleted, and thread summary state do not rewrite that canonical file. They live in `index.sqlite`.

That split matters because repair can rebuild projections and mutable state around canonical messages, but it cannot invent missing canonical content.

## Exact Contract

### Protocol version and identity fields

- `protocol_version` must be `1`.
- `message_id` and `thread_id` must match `msg-{YYYYMMDDTHHMMSSZ}-{uuid4-no-dashes}`.
- `created_at_utc` must be an RFC3339 UTC timestamp ending in `Z`.
- The YAML front matter uses `from` as the serialized field name for the sender, even though the Python model field is `sender`.

### Addressing

Each participant is a `MailboxPrincipal` with:

- `principal_id`
- `address`
- optional `display_name`
- optional `manifest_path_hint`
- optional `role`

Addresses are full-form email-like strings such as `AGENTSYS-research@agents.localhost`. Whitespace, blank values, invalid domains, and unsafe literal path-segment values are rejected.

### Threading

- A root message uses its own `message_id` as `thread_id`.
- A root message must not include `references`.
- A reply keeps the existing `thread_id`.
- A reply must set `in_reply_to`.
- A reply must include `references`, and the last element of `references` must equal `in_reply_to`.
- Subject changes do not create a new thread by themselves.

### Recipients and attachments

- `to` must contain at least one recipient.
- `cc` and `reply_to` are optional lists.
- Attachments are structured metadata, not free-form blobs embedded into the canonical message model.
- Attachment `kind` is either `path_ref` or `managed_copy`.
- `path_ref` attachments must use absolute paths.
- Optional `sha256` values must be 64-character lowercase hex digests.

### Headers and body

- `subject` must be non-blank.
- `body_markdown` may be empty, but it must not contain NUL bytes.
- `headers` is an extensible mapping, but header keys must be non-blank.

## Representative Canonical Message

This is the shape serialized by `serialize_message_document()` and parsed by `parse_message_document()`.

```markdown
---
protocol_version: 1
message_id: msg-20260313T091530Z-a1b2c3d4e5f64798aabbccddeeff0011
thread_id: msg-20260313T091530Z-a1b2c3d4e5f64798aabbccddeeff0011
in_reply_to: null
references: []
created_at_utc: 2026-03-13T09:15:30Z
from:
  principal_id: AGENTSYS-research
  address: AGENTSYS-research@agents.localhost
to:
  - principal_id: AGENTSYS-orchestrator
    address: AGENTSYS-orchestrator@agents.localhost
cc: []
reply_to: []
subject: Investigate parser drift
attachments:
  - attachment_id: att-1
    kind: path_ref
    path: /abs/path/notes.txt
    media_type: text/plain
headers:
  tags:
    - parser
---

# Summary

The parser drift appears after the second transform stage.
```

## Immutable Versus Mutable Boundaries

Authoritative immutable content:

- `messages/<YYYY-MM-DD>/<message-id>.md`
- front matter values such as sender, recipients, thread metadata, and attachments
- Markdown body text

Authoritative mutable state:

- `mailbox_state` rows for read, starred, archived, and deleted flags
- `thread_summaries` rows for normalized subject, latest message, and unread counts
- `mailbox_projections` rows and the corresponding symlinks in `inbox/` and `sent/`

Practical rule: if you are changing recipient-visible status, you should be touching SQLite-backed state, not rewriting a delivered Markdown file.

## Source References

- [`src/houmao/mailbox/protocol.py`](../../../../src/houmao/mailbox/protocol.py)
- [`src/houmao/mailbox/filesystem.py`](../../../../src/houmao/mailbox/filesystem.py)
- [`src/houmao/mailbox/managed.py`](../../../../src/houmao/mailbox/managed.py)
