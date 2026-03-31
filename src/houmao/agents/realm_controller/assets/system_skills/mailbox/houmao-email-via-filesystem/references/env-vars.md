# Filesystem Mailbox Resolver Fields

Resolve the current binding set through `pixi run houmao-mgr agents mail resolve-live` before mailbox work. For current-session managed use, that manager-owned helper resolves the current agent from the owning tmux session when selectors are omitted, returns the current actionable mailbox payload, and includes a `gateway` object with the exact `base_url`, `host`, `port`, `protocol_version`, and `state_path` for the shared `/v1/mail/*` facade when a valid attached gateway is live.

When `gateway.base_url` is present, use the installed Houmao gateway skill `houmao-email-via-agent-gateway` for shared `/v1/mail/*` operations.

## Common fields

- `transport`
  Meaning: selects the active mailbox transport.
  Expected value for this skill: `filesystem`

- `principal_id`
  Meaning: stable mailbox principal id for the current agent or participant.
  Example: `HOUMAO-research`

- `address`
  Meaning: email-like address associated with the current mailbox principal.
  Example: `HOUMAO-research@agents.localhost`

- `bindings_version`
  Meaning: monotonic binding version or timestamp used to detect mailbox-binding refresh.

## Filesystem-specific fields

- `mailbox.filesystem.root`
  Meaning: root directory of the filesystem mailbox transport.
  Example: `<mailbox_root>`
  Default when no explicit override is configured: `~/.houmao/mailbox`
  Shared mailbox rules directory: `<mailbox_root>/rules`
  Optional compatibility helper directory: `<mailbox_root>/rules/scripts`

- `mailbox.filesystem.sqlite_path`
  Meaning: shared mailbox-root SQLite catalog path for registrations, canonical messages, projections, and structural indexes.
  Example: `<mailbox_root>/index.sqlite`

- `mailbox.filesystem.inbox_path`
  Meaning: mailbox projection directory for the current session's active mailbox registration.
  Example: `<mailbox_root>/mailboxes/<address>/inbox`
  Note: this path follows the active registration path for `address`, which may traverse a symlinked `mailboxes/<address>` entry into a private mailbox directory outside `<mailbox_root>`.

- `mailbox.filesystem.mailbox_path`
  Meaning: resolved mailbox directory for the current session's active mailbox registration.
  Example: `<mailbox_root>/mailboxes/<address>`
  Note: for a symlinked registration this points at the resolved mailbox target directory, not merely the shared-root entry path.

- `mailbox.filesystem.local_sqlite_path`
  Meaning: mailbox-local SQLite path that stores mailbox-view state for this one mailbox.
  Example: `<resolved_mailbox_dir>/mailbox.sqlite`

- `mailbox.filesystem.mailbox_kind`
  Meaning: whether the active registration lives directly under the shared root or resolves through a symlinked private mailbox directory.

## Usage rules

- Require all common fields plus all filesystem-specific fields before mailbox work.
- When the resolver returns `gateway.base_url`, treat that value as the exact live shared-mailbox endpoint instead of guessing another loopback URL.
- Treat `mailbox.filesystem.root` as authoritative for mailbox content location.
- Treat `mailbox.filesystem.sqlite_path` as the shared structural catalog and `mailbox.filesystem.local_sqlite_path` as the authoritative mailbox-view state store for the current mailbox.
- Treat shared `rules/` as mailbox-local policy guidance rather than as the ordinary execution protocol.
- Resolve and re-read these bindings before each mailbox action.
- If `bindings_version` changes, discard cached filesystem assumptions and reload the current bindings.
