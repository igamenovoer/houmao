## Why

The current mailbox implementation achieves integrity by manually maintaining filesystem artifacts such as `rules/`, managed scripts, projection symlinks, lock files, and SQLite indexes. That makes the filesystem transport workable, but it also bakes transport-specific repair machinery into the mailbox contract and blocks Houmao from using a real mail system as the authority for delivery, mailbox state, and threading.

The repository now has a proven local Stalwart bring-up path, and the next step is to make real mail transport first-class. At the same time, Houmao already has an agent gateway sidecar that can act on behalf of managed agents. Today that gateway can wake agents about unread mail, but its notifier path is still hard-wired to filesystem mailbox-local SQLite. That means the gateway cannot yet be the transport abstraction boundary between filesystem mailboxes and real email-backed mailboxes.

This change keeps scope narrow. It introduces a Stalwart-backed transport and revises gateway/mailbox interaction only for the mailbox functions that both the filesystem transport and a real email system can support cleanly.

## What Changes

- Add a Stalwart-backed mailbox transport for Houmao mailbox-enabled sessions.
- Use Stalwart as the mailbox authority for delivery, unread state, reply ancestry, and transport-level integrity instead of re-creating those responsibilities in Houmao.
- Use Stalwart management surfaces to provision required domains, accounts, and mailbox credentials for mailbox-enabled participants.
- Add a gateway-owned mailbox facade for the shared mailbox operations supported by both transports: mailbox availability or status, `check`, `send`, and `reply`.
- Keep `POST /v1/requests` focused on terminal-mutating work, and expose dedicated `/v1/mail/*` routes for shared mailbox operations instead of modeling mailbox transport as queue-driven prompt injection.
- Back the gateway mailbox facade with transport adapters so the same managed-agent HTTP contract can target either filesystem mailbox state or Stalwart-backed mailboxes.
- Change gateway mail notifier behavior to read unread state through the same gateway mailbox facade instead of directly reading filesystem mailbox-local SQLite.
- Revise mailbox protocol and mailbox skill guidance so shared mailbox work uses transport-neutral message references and normalized metadata rather than filesystem-only ids, paths, or repair instructions.
- Keep transport-specific mailbox mechanics outside the shared gateway contract. Filesystem `rules/`, helper scripts, locks, and SQLite layout remain transport-local; Stalwart JMAP and management surfaces remain transport-local.
- **BREAKING**: gateway/mailbox integration will no longer treat mailbox-local SQLite and filesystem-shaped identifiers as the universal mailbox interaction contract.

## Capabilities

### New Capabilities
- `agent-mailbox-stalwart-transport`: Define Stalwart-backed mailbox provisioning and the shared mailbox operations needed for gateway-backed or direct `check`, `send`, and `reply`.

### Modified Capabilities
- `agent-gateway`: Add dedicated shared mailbox routes and keep mailbox operations separate from terminal-mutating request kinds.
- `agent-gateway-mail-notifier`: Make notifier unread detection transport-generic by routing it through the gateway mailbox facade.
- `agent-mailbox-protocol`: Refocus the shared mailbox operation contract on transport-neutral message references and metadata required by both filesystem and real email transports.
- `agent-mailbox-email-compatibility`: Replace the current future-only compatibility story with implemented true-email transport requirements for the shared mailbox operation set.
- `agent-mailbox-system-skills`: Extend runtime-owned mailbox skills and env bindings to prefer the live gateway mailbox facade for shared operations while preserving direct transport fallback when no gateway is attached.
- `brain-launch-runtime`: Extend mailbox config resolution, manifest persistence, session startup, resume, and runtime `mail` flows to support a Stalwart-backed transport while preserving one operator-facing mailbox UX.

## Impact

- Affected code: gateway models, service, client, and notifier logic; mailbox runtime models and support; runtime launch-plan composition; projected mailbox system skills; and new Stalwart transport/client code.
- Affected systems: agent gateway HTTP surface, gateway notifier, mailbox-enabled agent sessions, local Stalwart development environment, and mailbox-focused docs.
- External dependencies: Stalwart local server/runtime, Stalwart management API, and JMAP for shared mailbox operations.
- Testing: new coverage for filesystem and Stalwart gateway mail adapters, notifier behavior through the gateway facade, and retained filesystem transport coverage unless explicitly superseded later.
