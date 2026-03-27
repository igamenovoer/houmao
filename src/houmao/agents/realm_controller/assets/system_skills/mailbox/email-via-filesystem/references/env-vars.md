# Filesystem Mailbox Env Vars

Resolve the current binding set through `pixi run python -m houmao.agents.mailbox_runtime_support resolve-live` before direct mailbox work. For tmux-backed managed sessions, that runtime-owned helper reads the targeted mailbox keys from the owning tmux session environment and returns the current mailbox projection. Do not scrape tmux state directly when this helper is available.

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
  Meaning: Shared mailbox-root SQLite catalog path for registrations, canonical messages, projections, and structural indexes.
  Example: `<mailbox_root>/index.sqlite`

- `AGENTSYS_MAILBOX_FS_INBOX_DIR`
  Meaning: Mailbox projection directory for the current session's active mailbox registration.
  Example: `<mailbox_root>/mailboxes/<address>/inbox`
  Note: this path follows the active registration path for `AGENTSYS_MAILBOX_ADDRESS`, which may traverse a symlinked `mailboxes/<address>` entry into a private mailbox directory outside `<mailbox_root>`.

- `AGENTSYS_MAILBOX_FS_MAILBOX_DIR`
  Meaning: Resolved mailbox directory for the current session's active mailbox registration.
  Example: `<mailbox_root>/mailboxes/<address>`
  Note: for a symlinked registration this points at the resolved mailbox target directory, not merely the shared-root entry path.

- `AGENTSYS_MAILBOX_FS_LOCAL_SQLITE_PATH`
  Meaning: Mailbox-local SQLite path that stores mailbox-view state for this one mailbox.
  Example: `<resolved_mailbox_dir>/mailbox.sqlite`

## Usage rules

- Require all common bindings plus all filesystem-specific bindings before mailbox work.
- Treat `AGENTSYS_MAILBOX_FS_ROOT` as authoritative for mailbox content location; do not reconstruct it from the runtime root unless the runtime has already chosen that as the default.
- Treat `AGENTSYS_MAILBOX_FS_SQLITE_PATH` as the shared structural catalog and `AGENTSYS_MAILBOX_FS_LOCAL_SQLITE_PATH` as the authoritative mailbox-view state store for the current mailbox.
- Resolve and re-read these bindings before each mailbox action.
- If `AGENTSYS_MAILBOX_BINDINGS_VERSION` changes, discard cached filesystem assumptions and reload the current bindings.
