# Filesystem Mailbox Protocol v1

This protocol note is materialized by the runtime during filesystem mailbox bootstrap.

## Required layout

- Canonical messages live under `messages/<YYYY-MM-DD>/<message-id>.md`.
- `index.sqlite` stores mailbox registrations, canonical delivery history, projection catalog data, and other shared structural indexes.
- Each resolved mailbox directory stores mailbox-view state in a stable `mailbox.sqlite`.
- `mailboxes/<address>/inbox` and `mailboxes/<address>/sent` contain symlink projections back to canonical message files for the active registration of that full mailbox address.
- `archive/` and `drafts/` are reserved placeholder directories in v1.
- `locks/addresses/<address>.lock` is the address-scoped serialization key for delivery, mailbox-state mutation, register, deregister, and repair flows.
- Ordinary mailbox work should flow through Houmao-owned surfaces such as gateway `/v1/mail/*` or `houmao-mgr agents mail ...`, not through mailbox-owned scripts as the public execution contract.
- `rules/` remains the mailbox-local source of policy guidance such as formatting, etiquette, and workflow hints.
- `rules/scripts/`, when published, is compatibility or implementation detail rather than the primary ordinary workflow surface.
- Published compatibility helpers keep the stable `--mailbox-root` plus `--payload-file` contract, validate payloads through strict shared schemas before mutation, and emit exactly one JSON object to stdout for both success and failure outcomes.

## Current implementation state

This is the intended address-routed v1 contract. Mailbox roots from the earlier principal-keyed layout are unsupported stale roots and should be deleted and re-bootstrapped instead of migrated in place.
