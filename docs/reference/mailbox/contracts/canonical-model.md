# Mailbox Canonical Model

This page defines the message format that the filesystem mailbox transport treats as authoritative content.

## Mental Model

The mailbox system separates durable message content from per-recipient mailbox state.

- The canonical message is an immutable Markdown file with YAML front matter.
- The file captures who sent the message, who received it, how it threads, and what attachments it refers to.
- Read, answered, starred, archived, deleted, and thread summary state do not rewrite that canonical file. They live in `index.sqlite`.

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

Addresses are full-form email-like strings such as `research@houmao.localhost`. Whitespace, blank values, invalid domains, and unsafe literal path-segment values are rejected. Newly derived managed-agent addresses use `<agentname>@houmao.localhost`, while `HOUMAO-*` locals under `houmao.localhost` are reserved for Houmao-owned system mailboxes such as `HOUMAO-operator@houmao.localhost`.

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
- Operator-origin messages use explicit provenance headers such as `x-houmao-origin: operator` plus `x-houmao-reply-policy: none` or `x-houmao-reply-policy: operator_mailbox`.
- New operator-origin messages default to `x-houmao-reply-policy: operator_mailbox`; their `reply_to` targets the reserved system mailbox `HOUMAO-operator@houmao.localhost`. With `none`, replies to that operator-origin message are rejected.

### Notification-prompt block

- Optional `notify_block` is a short, sender-marked string intended for prominent receiver-side rendering by future notification surfaces. Senders may author it inline as a Markdown fenced code block with info-string `houmao-notify`; canonical-message construction extracts the first such fence into `notify_block` and leaves `body_markdown` unchanged. Callers may also supply `notify_block` directly through composition surfaces (`MailboxMessage.compose(...)`, `houmao-mgr agents mail send --notify-block ...`, gateway `/v1/mail/send` request body); explicit values bypass body-fence extraction.
- `notify_block` is capped at 512 characters; longer values are truncated to 511 characters plus a single trailing `…` (U+2026) at composition time.
- Optional `notify_auth` carries sender-supplied authentication metadata associated with `notify_block`. The protocol reserves the schemes `none`, `shared-token`, `hmac-sha256`, and `jws`; in the current protocol version only `scheme="none"` is accepted at validation. Non-`none` schemes are rejected with an explicit "verifier not yet supported" error so the slot can be carried forward without another envelope-level breaking change.
- The gateway notifier prompt does **not** render `notify_block` content in this protocol version. Notifier rendering, verifier plug-ins, and gateway-side trust posture (`permissive-log` versus `required`) land in a follow-on change.

## Representative Canonical Message

This is the shape serialized by `serialize_message_document()` and parsed by `parse_message_document()`.

```markdown
---
protocol_version: 2
message_id: msg-20260313T091530Z-a1b2c3d4e5f64798aabbccddeeff0011
thread_id: msg-20260313T091530Z-a1b2c3d4e5f64798aabbccddeeff0011
in_reply_to: null
references: []
created_at_utc: 2026-03-13T09:15:30Z
from:
  principal_id: HOUMAO-research
  address: research@houmao.localhost
to:
  - principal_id: HOUMAO-orchestrator
    address: orchestrator@houmao.localhost
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
notify_block: re-run on official timing path before reporting
notify_auth:
  scheme: none
---

# Summary

The parser drift appears after the second transform stage.

```houmao-notify
re-run on official timing path before reporting
```
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
