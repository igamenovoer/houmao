# Filesystem Mailbox Layout

This page explains the durable on-disk structure of the version 4 filesystem mailbox transport.

## Mental Model

The mailbox root mixes shared artifacts with per-address projections.

- Shared artifacts such as `messages/`, `locks/`, `index.sqlite`, `attachments/managed/`, and `rules/` stay under the mailbox root.
- `mailboxes/<address>` is the registration entry for one full mailbox address.
- That mailbox entry may be a real directory under the root or a symlink to a private mailbox directory elsewhere.
- The canonical message store remains shared even when a mailbox entry points outside the root.

## Annotated Tree

```text
<mailbox_root>/
  protocol-version.txt              # On-disk protocol marker; must match version 4
  index.sqlite                      # Private ownership/member verifiers, uploads, delivery catalog, and projections
  rules/
    README.md                       # Mailbox-local operating notes
    protocols/
      filesystem-mailbox-v1.md      # Shipped protocol note for this build
    scripts/
      requirements.txt              # Third-party Python deps for optional compatibility helpers
      register_mailbox.py
      deregister_mailbox.py
      deliver_message.py
      insert_standard_headers.py
      update_mailbox_state.py
      repair_index.py
    skills/                         # Mailbox-local helper skills, if present
  locks/
    index.lock
    addresses/
      <address>.lock                # Address-scoped serialization key
  messages/
    YYYY-MM-DD/
      <message-id>.md               # Canonical immutable Markdown message
  attachments/
    managed/
      <attachment-id>/
        <filename>                  # Optional managed-copy attachment storage
  mailboxes/
    <address>/
      inbox/
      sent/
      archive/
      drafts/
      mailbox.sqlite                # Mailbox-view state keyed by message_id and thread_id
    <other-address> -> /abs/path/private-mailboxes/<other-address>
  history/<registration-id>/        # Retained private state of released in-root registrations
  .authority.lock                   # OS-owned membership/read/reassignment exclusion
  staging/                          # Pre-delivery temporary work area
```

## Exact Layout Rules

### Canonical Content and Projections

- Canonical messages live under `messages/<YYYY-MM-DD>/<message-id>.md`.
- Recipient inbox and sender sent entries are symlink projections back to the canonical file.
- `archive/` stores projections moved by the explicit archive workflow; `drafts/` remains available for composition.

### Rules Tree

- `rules/` is the mailbox-local policy and helper area.
- `rules/README.md` explains the mailbox-local expectations.
- `rules/protocols/filesystem-mailbox-v1.md` retains its historical filename and documents the current version 4 contract.
- `rules/scripts/`, when published, contains compatibility or implementation-detail helpers for repair, debugging, or deep direct filesystem workflows. It is not the ordinary attached-session workflow surface.

### Shared State

- `index.sqlite` stores registrations, delivery history, attachment metadata, projections, and shared structural metadata for the mailbox root.
- The private index also contains durable `offline_members` and `offline_uploads` when registry service access is configured. These contain authorization verifiers and attachment ownership, not public discovery payloads.
- The current transport intentionally uses SQLite `DELETE` journal mode rather than WAL sidecar files.
- `locks/index.lock` and `locks/addresses/<address>.lock` serialize sensitive writes.
- Shared-root unread counters and other mailbox-view state are not authoritative once mailbox-local SQLite is available.

### Mailbox-Local State

- Each resolved mailbox directory owns one stable `mailbox.sqlite`.
- That mailbox-local database stores mailbox-view state that can vary by mailbox, including read or unread, starred, archived, deleted, and mailbox-local thread summaries.
- `message_state` rows are keyed by `message_id`.
- `thread_summaries` rows are keyed by `thread_id`.
- Because the database already scopes to one mailbox directory, mailbox-local tables do not need `registration_id` in their row identity.

### Registration Entries

- `mailboxes/<address>` is keyed by the full mailbox address, not by principal id.
- An active registration may be `in_root` or `symlink`.
- Released in-root private views move to `history/<registration-id>/`; a new address owner receives a fresh view.

## Relationship Between The Tree And The Message Model

- The Markdown file under `messages/` is the immutable content authority.
- The symlink under `inbox/` or `sent/` is a mailbox view of that authority.
- The shared `index.sqlite` is the mutable structural catalog for the mailbox root.
- The mailbox-local `mailbox.sqlite` is the mutable mailbox-view store for read flags, archive flags, deleted or starred state, and thread unread summaries.

If you need the exact message schema, pair this page with [Canonical Model](canonical-model.md). If you need the compatibility-helper mutation boundary, pair it with [Managed Scripts](managed-scripts.md).

## Source References

- [`src/houmao/mailbox/filesystem.py`](../../../../src/houmao/mailbox/filesystem.py)
- [`src/houmao/mailbox/assets/rules/protocols/filesystem-mailbox-v1.md`](../../../../src/houmao/mailbox/assets/rules/protocols/filesystem-mailbox-v1.md)
- [`src/houmao/mailbox/assets/rules/README.md`](../../../../src/houmao/mailbox/assets/rules/README.md)
- [`src/houmao/agents/assets/system_skills/public/houmao-shared-routines/subskills/houmao-agent-email-comms/references/filesystem-layout.md`](../../../../src/houmao/agents/assets/system_skills/public/houmao-shared-routines/subskills/houmao-agent-email-comms/references/filesystem-layout.md)
