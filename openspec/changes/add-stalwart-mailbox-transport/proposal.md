## Why

The current mailbox implementation achieves integrity by manually maintaining filesystem artifacts such as `rules/`, managed scripts, projection symlinks, lock files, and SQLite indexes. That makes the filesystem transport workable, but it also bakes transport-specific repair machinery into the mailbox contract and blocks Houmao from using a real mail system as the authority for delivery, mailbox state, and threading.

The repository now has a proven local Stalwart bring-up path, and the next step is to make real mail transport first-class. This change moves mailbox behavior toward an email-native model where Stalwart owns delivery and mailbox consistency, while Houmao keeps only the runtime binding, operator UX, and agent-facing conventions it actually needs.

## What Changes

- Add a Stalwart-backed mailbox transport for Houmao mailbox-enabled sessions.
- Use Stalwart as the mailbox authority for delivery, mailbox folders, mailbox state, and transport-level integrity instead of re-creating those responsibilities in Houmao.
- Use Stalwart management surfaces to provision required domains, accounts, and mailbox credentials for mailbox-enabled participants.
- Use an email-native mailbox operation model for `mail check`, `mail send`, and `mail reply`, with JMAP as the primary automation surface and SMTP/IMAP kept as compatibility or debugging surfaces where appropriate.
- Revise the mailbox protocol contract so filesystem-specific machinery such as `rules/`, managed scripts, symlink projections, lock files, and mailbox-local SQLite are treated as filesystem transport details rather than universal mailbox requirements.
- Revise runtime mailbox bindings and projected mailbox system-skill behavior so non-filesystem transports do not inherit filesystem-only env vars or `rules/scripts` expectations.
- Introduce a bootstrap welcome-thread convention that can carry shared agent mailbox guidance and structured usage contracts inside the real mail system instead of storing those conventions in a filesystem mailbox root.
- **BREAKING**: the mailbox contract will no longer treat the current filesystem transport’s integrity mechanisms and ID conventions as the normative mailbox protocol for all transports.

## Capabilities

### New Capabilities
- `agent-mailbox-stalwart-transport`: Define Stalwart-backed mailbox provisioning, binding, send/check/reply behavior, and welcome-thread bootstrap conventions for real email-backed agent mailboxes.

### Modified Capabilities
- `agent-mailbox-protocol`: Refocus the mailbox protocol on transport-neutral mailbox semantics and relax filesystem-derived ID, attachment, and state assumptions that do not belong in a real email transport.
- `agent-mailbox-email-compatibility`: Replace the current future-only compatibility story with implemented true-email transport requirements and explicit Stalwart mapping rules.
- `agent-mailbox-system-skills`: Extend runtime-owned mailbox skills and env bindings to support Stalwart-backed sessions without inheriting filesystem-only `rules/` and managed-script behavior.
- `brain-launch-runtime`: Extend mailbox config resolution, manifest persistence, session startup, resume, and runtime `mail` operations to support a Stalwart-backed transport alongside the existing filesystem transport.

## Impact

- Affected code: mailbox runtime models and support, runtime launch-plan composition, runtime `mail` commands, projected mailbox system skills, gateway/mailbox integration seams, and new Stalwart transport/client code.
- Affected systems: Houmao mailbox contract, local Stalwart development environment, mailbox-enabled agent sessions, and mailbox-focused docs/tutorials.
- External dependencies: Stalwart local server/runtime, Stalwart management API, and a programmatic mail access surface suitable for automated mailbox operations.
- Testing: new integration coverage for provisioning and live mail roundtrips against local Stalwart; existing filesystem transport coverage must remain intact unless explicitly superseded later.
