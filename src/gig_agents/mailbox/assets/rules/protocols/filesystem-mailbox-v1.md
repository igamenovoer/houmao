# Filesystem Mailbox Protocol v1

This protocol note is materialized by the runtime during filesystem mailbox bootstrap.

## Required layout

- Canonical messages live under `messages/<YYYY-MM-DD>/<message-id>.md`.
- `index.sqlite` stores mutable mailbox state and structural indexes.
- `mailboxes/<principal>/inbox` and `mailboxes/<principal>/sent` contain symlink projections back to canonical message files.
- `archive/` and `drafts/` are reserved placeholder directories in v1.
- Sensitive operations that touch `index.sqlite` or `locks/` should use the managed scripts under `rules/scripts/`.
- `rules/scripts/requirements.txt` declares the third-party Python dependencies needed by those managed Python helpers.

## Current implementation state

The managed scripts shipped with this build are present and materialized during bootstrap. Their full delivery, mailbox-state mutation, and repair behavior is implemented incrementally across later mailbox tasks, so operators should treat these scripts as the canonical managed entrypoints even while behavior is still expanding.
