# Filesystem Mailbox Env Vars

Resolve the current binding set through `pixi run houmao-mgr agents mail resolve-live --format json` before mailbox work. For current-session managed use, that manager-owned helper resolves the current agent from the owning tmux session when selectors are omitted, returns the current mailbox projection, and includes a `gateway` object with the exact `base_url`, `host`, `port`, `protocol_version`, and `state_path` for the shared `/v1/mail/*` facade when a valid attached gateway is live.

## Common mailbox bindings

- `AGENTSYS_MAILBOX_TRANSPORT`
  Meaning: selects the active mailbox transport.
  Expected value for this skill: `filesystem`

- `AGENTSYS_MAILBOX_PRINCIPAL_ID`
  Meaning: stable mailbox principal id for the current agent or participant.
  Example: `AGENTSYS-research`

- `AGENTSYS_MAILBOX_ADDRESS`
  Meaning: email-like address associated with the current mailbox principal.
  Example: `AGENTSYS-research@agents.localhost`

- `AGENTSYS_MAILBOX_BINDINGS_VERSION`
  Meaning: monotonic binding version or timestamp used to detect runtime binding refresh.

## Filesystem-specific bindings

- `AGENTSYS_MAILBOX_FS_ROOT`
  Meaning: root directory of the filesystem mailbox transport.
  Example: `<mailbox_root>`
  Default when no explicit override is configured: `<runtime_root>/mailbox`
  Shared mailbox rules directory: `<mailbox_root>/rules`
  Optional compatibility helper directory: `<mailbox_root>/rules/scripts`

- `AGENTSYS_MAILBOX_FS_SQLITE_PATH`
  Meaning: shared mailbox-root SQLite catalog path for registrations, canonical messages, projections, and structural indexes.
  Example: `<mailbox_root>/index.sqlite`

- `AGENTSYS_MAILBOX_FS_INBOX_DIR`
  Meaning: mailbox projection directory for the current session's active mailbox registration.
  Example: `<mailbox_root>/mailboxes/<address>/inbox`
  Note: this path follows the active registration path for `AGENTSYS_MAILBOX_ADDRESS`, which may traverse a symlinked `mailboxes/<address>` entry into a private mailbox directory outside `<mailbox_root>`.

- `AGENTSYS_MAILBOX_FS_MAILBOX_DIR`
  Meaning: resolved mailbox directory for the current session's active mailbox registration.
  Example: `<mailbox_root>/mailboxes/<address>`
  Note: for a symlinked registration this points at the resolved mailbox target directory, not merely the shared-root entry path.

- `AGENTSYS_MAILBOX_FS_LOCAL_SQLITE_PATH`
  Meaning: mailbox-local SQLite path that stores mailbox-view state for this one mailbox.
  Example: `<resolved_mailbox_dir>/mailbox.sqlite`

## Usage rules

- Require all common bindings plus all filesystem-specific bindings before mailbox work.
- When the resolver returns `gateway.base_url`, treat that value as the exact live shared-mailbox endpoint instead of guessing another loopback URL.
- Treat `AGENTSYS_MAILBOX_FS_ROOT` as authoritative for mailbox content location.
- Treat `AGENTSYS_MAILBOX_FS_SQLITE_PATH` as the shared structural catalog and `AGENTSYS_MAILBOX_FS_LOCAL_SQLITE_PATH` as the authoritative mailbox-view state store for the current mailbox.
- Treat shared `rules/` as mailbox-local policy guidance rather than as the ordinary execution protocol.
- Resolve and re-read these bindings before each mailbox action.
- If `AGENTSYS_MAILBOX_BINDINGS_VERSION` changes, discard cached filesystem assumptions and reload the current bindings.
