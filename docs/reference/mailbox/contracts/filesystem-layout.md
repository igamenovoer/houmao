# Filesystem Mailbox Layout

This page explains the durable on-disk structure of the v1 filesystem mailbox transport.

## Mental Model

The mailbox root mixes shared artifacts with per-address projections.

- Shared artifacts such as `messages/`, `locks/`, `index.sqlite`, `attachments/managed/`, and `rules/` stay under the mailbox root.
- `mailboxes/<address>` is the registration entry for one full mailbox address.
- That mailbox entry may be a real directory under the root or a symlink to a private mailbox directory elsewhere.
- The canonical message store remains shared even when a mailbox entry points outside the root.

## Annotated Tree

```text
<mailbox_root>/
  protocol-version.txt              # On-disk protocol marker; must match v1
  index.sqlite                      # Registrations, mutable state, projections, summaries
  rules/
    README.md                       # Mailbox-local operating notes
    protocols/
      filesystem-mailbox-v1.md      # Shipped protocol note for this build
    scripts/
      requirements.txt              # Third-party Python deps for managed helpers
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
    <other-address> -> /abs/path/private-mailboxes/<other-address>
  staging/                          # Pre-delivery temporary work area
```

## Exact Layout Rules

### Canonical content and projections

- Canonical messages live under `messages/<YYYY-MM-DD>/<message-id>.md`.
- Recipient inbox and sender sent entries are symlink projections back to the canonical file.
- `archive/` and `drafts/` exist as placeholder directories in v1; they do not define a full archive or draft workflow yet.

### Rules tree

- `rules/` is the mailbox-local policy and helper area.
- `rules/README.md` explains the mailbox-local expectations.
- `rules/protocols/filesystem-mailbox-v1.md` documents the shipped v1 contract.
- `rules/scripts/` contains the managed helper entrypoints for sensitive operations.

### Shared state

- `index.sqlite` stores registrations, delivery history, attachment metadata, projections, mailbox state, and thread summaries.
- The current transport intentionally uses SQLite `DELETE` journal mode rather than WAL sidecar files.
- `locks/index.lock` and `locks/addresses/<address>.lock` serialize sensitive writes.

### Registration entries

- `mailboxes/<address>` is keyed by the full mailbox address, not by principal id.
- An active registration may be `in_root` or `symlink`.
- Stashed preserved artifacts appear as `mailboxes/<address>--<uuid4hex>`.

## Relationship Between The Tree And The Message Model

- The Markdown file under `messages/` is the immutable content authority.
- The symlink under `inbox/` or `sent/` is a mailbox view of that authority.
- SQLite is the mutable view: read flags, archive flags, thread summaries, and projection catalog data.

If you need the exact message schema, pair this page with [Canonical Model](canonical-model.md). If you need the mutation boundary, pair it with [Managed Scripts](managed-scripts.md).

## Source References

- [`src/houmao/mailbox/filesystem.py`](../../../../src/houmao/mailbox/filesystem.py)
- [`src/houmao/mailbox/assets/rules/protocols/filesystem-mailbox-v1.md`](../../../../src/houmao/mailbox/assets/rules/protocols/filesystem-mailbox-v1.md)
- [`src/houmao/mailbox/assets/rules/README.md`](../../../../src/houmao/mailbox/assets/rules/README.md)
- [`src/houmao/agents/realm_controller/assets/system_skills/mailbox/email-via-filesystem/references/filesystem-layout.md`](../../../../src/houmao/agents/realm_controller/assets/system_skills/mailbox/email-via-filesystem/references/filesystem-layout.md)
