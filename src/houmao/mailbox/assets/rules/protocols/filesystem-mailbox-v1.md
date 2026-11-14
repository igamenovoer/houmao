# Filesystem Mailbox Protocol Version 4

This protocol note is materialized by the runtime during filesystem mailbox bootstrap.

## Required layout

- Canonical messages live under `messages/<YYYY-MM-DD>/<message-id>.md`.
- `index.sqlite` stores mailbox registrations, canonical delivery history, projection catalog data, and other shared structural indexes.
- Each resolved mailbox directory stores mailbox-view state in a stable `mailbox.sqlite`.
- `mailboxes/<address>/inbox` and `mailboxes/<address>/sent` contain symlink projections back to canonical message files for the active registration of that full mailbox address.
- `archive/` and `drafts/` are reserved placeholder directories in this version.
- `locks/addresses/<address>.lock` is the address-scoped serialization key for delivery, mailbox-state mutation, register, deregister, and repair flows.
- Ordinary mailbox work should flow through Houmao-owned surfaces such as gateway `/v1/mail/*` or scoped `houmao-mgr agents single/self ... mail ...`, not through mailbox-owned scripts as the public execution contract.
- `rules/` remains the mailbox-local source of policy guidance such as formatting, etiquette, and workflow hints.
- `rules/scripts/`, when published, is compatibility or implementation detail rather than the primary ordinary workflow surface.
- Published compatibility helpers keep the stable `--mailbox-root` plus `--payload-file` contract, validate payloads through strict shared schemas before mutation, and emit exactly one JSON object to stdout for both success and failure outcomes.

## Current implementation state

This is the intended address-routed version 4 contract. Mailbox roots from the earlier principal-keyed layout are unsupported stale roots and require an explicit operator backup restore or rebootstrap; they are never silently migrated or reset.

## Exclusive Ownership and Remote Access

An agent owner is its persisted `agent_id`. Only safe, conflict-rejecting joins are supported. A durable preparing reservation precedes mailbox preparation, and only a ready registration becomes active. Rejoin by the same owner/address/path is idempotent. Force/stash modes and confirmation cannot take another owner's address.

Membership outlives runtime presence and gateway availability. Explicit release isolates in-root private history under `history/<registration-id>/`; symlink release preserves external targets. A later different owner receives a new registration and private view. Runtime liveness cleanup cannot release addresses.

The selected registry's host owns this store. Authenticated remote members use the narrow registry API and managed content transfers without choosing host paths. Credentials and verifier digests are private and never appear in discovery. Offline and online operations have explicit channel and binding scope and never forward or fall back between channels.

OS-owned locks release on process exit. Repair preserves readable ownership and private member data while rebuilding derived message indexes. Missing/unreadable ownership requires an explicit backup restore or rebootstrap.
