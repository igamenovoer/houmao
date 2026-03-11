# Filesystem Mailbox Layout

Use this reference when you need exact on-disk structure for the filesystem mailbox transport.

The layout below is rooted at the effective mailbox content root. That content root may be relocated through env bindings and defaults to `<runtime_root>/mailbox` when the runtime does not provide an explicit override.

```text
<mailbox_root>/
  protocol-version.txt
  index.sqlite
  locks/
    index.lock
    principals/
      <principal>.lock
  messages/
    YYYY/
      MM/
        DD/
          <message-id>.md
  attachments/
    managed/
      sha256/
        <digest-prefix>/
          <digest>/
            <filename>
  mailboxes/
    <principal>/
      inbox/
      sent/
      archive/
      drafts/
  staging/
```

## Structure meaning

- `messages/`
  Canonical immutable Markdown message store.

- `mailboxes/<principal>/inbox`
  Recipient-facing mailbox projection for delivered messages.

- `mailboxes/<principal>/sent`
  Sender-facing mailbox projection for outbound messages.

- `locks/`
  Filesystem lock area used to serialize conflicting mailbox writes.

- `index.sqlite`
  Query and mutable-state store for unread or read, starred, archived, and thread summary state.
  This transport does not rely on `index.sqlite-wal` or `index.sqlite-shm` sidecar files.

- `staging/`
  Temporary area for composing and validating messages before delivery becomes visible.

## Message file shape

Expect Markdown files with structured front matter describing:

- `message_id`
- `thread_id`
- `in_reply_to`
- `references`
- sender and recipient principals
- attachment metadata

Treat the Markdown file as immutable after delivery. Update read or unread and related mailbox state in SQLite instead of rewriting the delivered message body.
