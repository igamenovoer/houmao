# Stalwart Mailbox Env Vars

Resolve the current binding set through `pixi run houmao-mgr agents mail resolve-live --format json` before mailbox work. For current-session managed use, that manager-owned helper resolves the current agent from the owning tmux session when selectors are omitted, returns the current mailbox projection, and includes a `gateway` object with the exact `base_url`, `host`, `port`, `protocol_version`, and `state_path` for the shared `/v1/mail/*` facade when a valid attached gateway is live.

Common mailbox bindings:

- `AGENTSYS_MAILBOX_TRANSPORT`
- `AGENTSYS_MAILBOX_PRINCIPAL_ID`
- `AGENTSYS_MAILBOX_ADDRESS`
- `AGENTSYS_MAILBOX_BINDINGS_VERSION`

Stalwart-specific bindings:

- `AGENTSYS_MAILBOX_EMAIL_JMAP_URL`
  Meaning: JMAP session endpoint for mailbox operations.
- `AGENTSYS_MAILBOX_EMAIL_MANAGEMENT_URL`
  Meaning: Stalwart management API base URL for provisioning or account inspection.
- `AGENTSYS_MAILBOX_EMAIL_LOGIN_IDENTITY`
  Meaning: login identity used for authenticated mailbox access.
- `AGENTSYS_MAILBOX_EMAIL_CREDENTIAL_REF`
  Meaning: secret-free credential reference persisted in the session manifest.
- `AGENTSYS_MAILBOX_EMAIL_CREDENTIAL_FILE`
  Meaning: session-local credential material used for authenticated mailbox access.

Gateway-related preference:

- When the resolver returns `gateway.base_url`, prefer that gateway `/v1/mail/*` facade for shared mailbox operations before falling back to direct Stalwart access.
- When direct Stalwart access is required, use the current `AGENTSYS_MAILBOX_EMAIL_*` values returned by the resolver rather than trusting stale inherited process env snapshots.
