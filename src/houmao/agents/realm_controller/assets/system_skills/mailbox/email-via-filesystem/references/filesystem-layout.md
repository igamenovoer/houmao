# Filesystem Mailbox Layout

Use this reference when you need exact on-disk structure for the filesystem mailbox transport.

The layout below is rooted at the effective mailbox content root. That content root may be relocated through env bindings and defaults to `<runtime_root>/mailbox` when the runtime does not provide an explicit override.

When an agent interacts with a shared mailbox, inspect `rules/` first. That mailbox-local rules area is where the shared mailbox can publish a README, standardized helper scripts, and mailbox-operation helper skills that refine the generic transport guidance.

Mailbox initialization is a runtime-owned bootstrap step. That bootstrap path creates or validates `protocol-version.txt`, the SQLite schema, the `rules/` tree, the managed scripts under `rules/scripts/`, and any in-root address-based mailbox directories before agents are expected to use the mailbox.

```text
<mailbox_root>/
  protocol-version.txt
  index.sqlite
  rules/
    README.md
    protocols/
    scripts/
      requirements.txt
      register_mailbox.py
      deregister_mailbox.py
      deliver_message.py
      insert_standard_headers.py
      update_mailbox_state.py
      repair_index.py
    skills/
  locks/
    index.lock
    addresses/
      <address>.lock
  messages/
    YYYY-MM-DD/
      <message-id>.md
  attachments/
    managed/
      <attachment-id>/
        <filename>
  mailboxes/
    <address>/
      inbox/
      sent/
      archive/
      drafts/
    <other-address> -> /abs/path/private-mailboxes/<other-address>
  staging/
```

## Structure meaning

- `messages/`
  Canonical immutable Markdown message store.
  Messages are grouped by delivery date as `messages/<YYYY-MM-DD>/<message-id>.md`.

- `rules/`
  Shared mailbox-local rules area.
  This is where the shared mailbox publishes protocol notes, helper scripts, and helper skills for standardized mailbox operations.

- `rules/scripts/`
  Shared helper scripts for sensitive mailbox operations.
  Operations that touch `index.sqlite` or `locks/` should use these scripts instead of ad hoc direct mutations.
  Scripts may be `.py` or `.sh`; Python scripts may depend on standard-library modules and additional Python packages when the shared mailbox declares those dependencies in `rules/scripts/requirements.txt`.
  In v1, the runtime-managed asset set includes `requirements.txt`, `register_mailbox.py`, `deregister_mailbox.py`, `deliver_message.py`, `insert_standard_headers.py`, `update_mailbox_state.py`, and `repair_index.py`.
  These filenames are stable within a given `protocol-version.txt` value.
  `insert_standard_headers.py` remains optional at use time, but it is still part of the managed bootstrap material.

- `mailboxes/<address>/inbox`
  Recipient-facing mailbox projection for delivered messages.
  The `mailboxes/<address>` entry may be a real directory under `<mailbox_root>` or a symlink to a private mailbox directory outside `<mailbox_root>`.
  Individual inbox entries are symlinks to canonical message files under `messages/`.

- `mailboxes/<address>/sent`
  Sender-facing mailbox projection for outbound messages.
  Individual sent entries are symlinks to canonical message files under `messages/`.

- `mailboxes/<address>`
  Address-routed mailbox registration entry used by the shared mail group.
  Dynamic join can be implemented by creating this entry as a symlink to a private mailbox directory that already contains `inbox/`, `sent/`, `archive/`, and `drafts/`.
  Historical preserved artifacts may appear as `mailboxes/<address>--<uuid4hex>/` after `stash` replacement flows.
  In v1, `archive/` and `drafts/` are reserved placeholder directories for forward compatibility rather than defined archive or draft workflows.

- `messages/`, `locks/`, `attachments/managed/`, and `index.sqlite`
  Shared mail-group artifacts that remain anchored under `<mailbox_root>` even when an address-based mailbox entry is symlinked to a private directory.

- `attachments/managed/<attachment-id>/`
  Optional managed-copy attachment storage.
  The path is keyed by `attachment_id` for simplicity.
  Message-to-attachment association is tracked in `index.sqlite`, not encoded in the filesystem path.

- `locks/`
  Filesystem lock area used to serialize conflicting mailbox writes.
  Lock names are derived from the literal full mailbox address, not from `principal_id`.

- `index.sqlite`
  Query and mutable-state store for unread or read, starred, archived, and thread summary state.
  It also tracks attachment metadata and message-to-attachment associations for managed or referenced attachments.
  This transport does not rely on `index.sqlite-wal` or `index.sqlite-shm` sidecar files.

- `staging/`
  Temporary area for composing and validating messages before delivery becomes visible.

## Message file shape

Expect Markdown files with structured front matter describing:

- `message_id`
- `thread_id`
- `in_reply_to`
- `references`
- sender and recipient mailbox principals, routed by full address
- attachment metadata

Treat the Markdown file as immutable after delivery. Update read or unread and related mailbox state in SQLite instead of rewriting the delivered message body.
