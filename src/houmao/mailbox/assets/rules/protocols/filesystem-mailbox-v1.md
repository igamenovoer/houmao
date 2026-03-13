# Filesystem Mailbox Protocol v1

This protocol note is materialized by the runtime during filesystem mailbox bootstrap.

## Required layout

- Canonical messages live under `messages/<YYYY-MM-DD>/<message-id>.md`.
- `index.sqlite` stores mailbox registrations, canonical delivery history, mutable mailbox state, and structural indexes.
- `mailboxes/<address>/inbox` and `mailboxes/<address>/sent` contain symlink projections back to canonical message files for the active registration of that full mailbox address.
- `archive/` and `drafts/` are reserved placeholder directories in v1.
- `locks/addresses/<address>.lock` is the address-scoped serialization key for delivery, mailbox-state mutation, register, deregister, and repair flows.
- Sensitive operations that touch `index.sqlite` or `locks/` should use the managed scripts under `rules/scripts/`.
- `rules/scripts/requirements.txt` declares the third-party Python dependencies needed by those managed Python helpers and uses minimum-version requirements for the managed validation stack.
- The managed lifecycle surface includes `register_mailbox.py` for `safe|force|stash` joins and `deregister_mailbox.py` for `deactivate|purge` leave flows.
- The managed Python helpers keep the stable `--mailbox-root` plus `--payload-file` contract, validate payloads through strict shared schemas before mutation, and emit exactly one JSON object to stdout for both success and failure outcomes.

## Current implementation state

This is the intended address-routed v1 contract. Mailbox roots from the earlier principal-keyed layout are unsupported stale roots and should be deleted and re-bootstrapped instead of migrated in place.
