# Filesystem Mailbox Env Vars

## Common mailbox bindings

- `AGENTSYS_MAILBOX_TRANSPORT`
  Meaning: Selects the active mailbox transport.
  Expected value for this skill: `filesystem`

- `AGENTSYS_MAILBOX_PRINCIPAL_ID`
  Meaning: Stable mailbox principal id for the current agent or participant.
  Example: `AGENTSYS-research`

- `AGENTSYS_MAILBOX_ADDRESS`
  Meaning: Email-like address associated with the current mailbox principal.
  Example: `AGENTSYS-research@agents.localhost`

- `AGENTSYS_MAILBOX_BINDINGS_VERSION`
  Meaning: Monotonic binding version or timestamp used to detect runtime binding refresh.

## Filesystem-specific bindings

- `AGENTSYS_MAILBOX_FS_ROOT`
  Meaning: Root directory of the filesystem mailbox transport.
  Example: `<mailbox_root>`
  Default when no explicit override is configured: `<runtime_root>/mailbox`
  Shared mailbox rules directory: `<mailbox_root>/rules`
  Shared sensitive-operation scripts directory: `<mailbox_root>/rules/scripts`

- `AGENTSYS_MAILBOX_FS_SQLITE_PATH`
  Meaning: SQLite database path for mailbox metadata and mutable mailbox state.
  Example: `<mailbox_root>/index.sqlite`

- `AGENTSYS_MAILBOX_FS_INBOX_DIR`
  Meaning: Mailbox projection directory for the current session's active mailbox registration.
  Example: `<mailbox_root>/mailboxes/<address>/inbox`
  Note: this path follows the active registration path for `AGENTSYS_MAILBOX_ADDRESS`, which may traverse a symlinked `mailboxes/<address>` entry into a private mailbox directory outside `<mailbox_root>`.

## Usage rules

- Require all common bindings plus all filesystem-specific bindings before mailbox work.
- Treat `AGENTSYS_MAILBOX_FS_ROOT` as authoritative for mailbox content location; do not reconstruct it from the runtime root unless the runtime has already chosen that as the default.
- Re-read these bindings before each mailbox action.
- If `AGENTSYS_MAILBOX_BINDINGS_VERSION` changes, discard cached filesystem assumptions and reload the current bindings.
