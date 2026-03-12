## Why

`add-agent-mailbox-protocol` established a workable filesystem mailbox transport, but before the system is put into real use we have already identified four contract gaps: recipient addressing is too ambiguous, the runtime `mail` CLI still overlaps with generic prompting, mailbox join conflicts are only partly modeled, and leave-group cleanup is undefined. Those gaps all come from the same underlying issue: the current `v1` model treats `principal_id` as both the mailbox owner and the concrete mailbox registration.

This is the right time to refactor because the mailbox system is still pre-adoption and we can improve the protocol directly without carrying migration baggage. Tightening the design now will make mailbox lifecycle, addressing, runtime bindings, and runtime commands much easier to reason about before they become operator habits or external contracts.

## What Changes

- Refactor the mailbox model so full mailbox addresses become the routing identity for delivery and runtime CLI usage, while `principal_id` remains ownership metadata rather than the sole registry key.
- Refactor the filesystem mailbox registry from one-row-per-principal into lifecycle-managed mailbox registrations with one active registration per address, historical inactive or stashed registrations, registration-scoped mutable state, and canonical recipient history that is decoupled from live registration rows.
- Add explicit managed mailbox lifecycle operations for join and leave flows, including `safe`, `force`, and `stash` join handling plus `deactivate` and `purge` cleanup modes, all exposed through the existing mailbox-local `--mailbox-root` plus `--payload-file` JSON script pattern.
- Keep the mailbox protocol at the intended `v1` contract, but treat old principal-keyed mailbox roots as unsupported hard-reset artifacts that must be deleted and re-bootstrapped rather than migrated in place.
- **BREAKING** Tighten runtime `mail send` recipient handling so `--to` and `--cc` require full-form mailbox addresses instead of accepting ambiguous short names.
- **BREAKING** Remove prompt-style `--instruction` usage from runtime `mail send` and `mail reply`, and require explicit mail body inputs such as `--body-file` or `--body-content`.
- Update runtime mailbox env bindings, mailbox-local filesystem layout, and operator documentation so address-routed mailbox registrations become the basis for `mailboxes/<address>/`, `locks/addresses/<address>.lock`, and `AGENTSYS_MAILBOX_FS_INBOX_DIR`.

## Capabilities

### New Capabilities

- `agent-mailbox-registration-lifecycle`: Address-routed mailbox registration semantics for the filesystem mailbox transport, including active versus inactive versus stashed mailbox entries, explicit join conflict handling, address-scoped locking, hard-reset handling for stale roots, and defined leave-group cleanup behavior.

### Modified Capabilities

- `brain-launch-runtime`: The runtime `mail` command surface changes to validate full-form recipient addresses, accept explicit mail body inputs instead of `--instruction`, and publish mailbox filesystem bindings based on the active mailbox registration path.

## Impact

This refactor will affect the filesystem mailbox SQLite schema and bootstrap contract, mailbox-local directory and lock naming, managed mailbox helper scripts under `rules/scripts/`, runtime mail command parsing and prompt payload construction, runtime mailbox env bindings, mailbox skill assets, mailbox-focused tests, and mailbox Q&A or operator documentation that currently describe the looser behavior. It intentionally changes the operator-facing mailbox contract before adoption, so old principal-keyed mailbox roots become unsupported and current examples and fixtures will need to move to full mailbox addresses, explicit message-body inputs, and address-based mailbox layout expectations.
