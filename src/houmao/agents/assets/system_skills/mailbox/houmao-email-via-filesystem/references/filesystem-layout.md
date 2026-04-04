# Filesystem Mailbox Layout

Use this reference when you need exact on-disk structure for the filesystem mailbox transport.

The layout below is rooted at the effective mailbox content root. That content root may be relocated through resolved mailbox bindings and defaults to `<runtime_root>/mailbox` when the runtime does not provide an explicit override.

When an agent interacts with a shared mailbox, inspect `rules/` first. That mailbox-local rules area is where the shared mailbox can publish a README, markdown policy guidance, optional compatibility helpers, and helper skills that refine the generic transport guidance.

Mailbox initialization is a runtime-owned bootstrap step. That bootstrap path creates or validates `protocol-version.txt`, the SQLite schema, the `rules/` tree, and any in-root address-based mailbox directories before agents are expected to use the mailbox. Compatibility helper assets may also be published under `rules/scripts/`.

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
      mailbox.sqlite
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

- `rules/`
  Shared mailbox-local rules area for protocol notes, policy guidance, optional compatibility helpers, and helper skills.

- `rules/scripts/`
  Optional compatibility or diagnostic helper scripts.
  Ordinary mailbox work should use gateway `/v1/mail/*` or `houmao-mgr agents mail ...` rather than treating these files as the first-choice public contract.

- `mailboxes/<address>/inbox`
  Recipient-facing mailbox projection for delivered messages.
  The `mailboxes/<address>` entry may be a real directory under `<mailbox_root>` or a symlink to a private mailbox directory outside `<mailbox_root>`.
  Individual inbox entries are symlinks to canonical message files under `messages/`.

- `mailboxes/<address>/mailbox.sqlite`
  Mailbox-local SQLite state for one resolved mailbox directory.
  This database stores mailbox-view state keyed by `message_id` plus mailbox-local thread summary caches keyed by `thread_id`.
  It is the authoritative store for read, starred, archived, deleted, and unread-thread mailbox-view state for that mailbox.

- `mailboxes/<address>/sent`
  Sender-facing mailbox projection for outbound messages.
  Individual sent entries are symlinks to canonical message files under `messages/`.

- `mailboxes/<address>`
  Address-routed mailbox registration entry used by the shared mail group.
  Dynamic join can be implemented by creating this entry as a symlink to a private mailbox directory that already contains `inbox/`, `sent/`, `archive/`, and `drafts/`.
  Historical preserved artifacts may appear as `mailboxes/<address>--<uuid4hex>/` after `stash` replacement flows.

- `messages/`, `locks/`, `attachments/managed/`, and `index.sqlite`
  Shared mail-group artifacts that remain anchored under `<mailbox_root>` even when an address-based mailbox entry is symlinked to a private directory.

- `attachments/managed/<attachment-id>/`
  Optional managed-copy attachment storage.

- `locks/`
  Filesystem lock area used to serialize conflicting mailbox writes.

- `index.sqlite`
  Shared mailbox-root structural catalog for registrations, canonical messages, recipient associations, projections, and attachment metadata.
  Mailbox-view state that can differ per mailbox lives in each mailbox directory's `mailbox.sqlite` instead.

- `staging/`
  Temporary area for composing and validating messages before delivery becomes visible.
