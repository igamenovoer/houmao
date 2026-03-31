# Stalwart Mailbox Resolver Fields

Resolve the current binding set through `pixi run houmao-mgr agents mail resolve-live` before mailbox work. For current-session managed use, that manager-owned helper resolves the current agent from the owning tmux session when selectors are omitted, returns the current actionable mailbox payload, and includes a `gateway` object with the exact `base_url`, `host`, `port`, `protocol_version`, and `state_path` for the shared `/v1/mail/*` facade when a valid attached gateway is live.

Common fields:

- `transport`
- `principal_id`
- `address`
- `bindings_version`

Stalwart-specific fields:

- `mailbox.stalwart.jmap_url`
  Meaning: JMAP session endpoint for mailbox operations.
- `mailbox.stalwart.management_url`
  Meaning: Stalwart management API base URL for provisioning or account inspection.
- `mailbox.stalwart.login_identity`
  Meaning: login identity used for authenticated mailbox access.
- `mailbox.stalwart.credential_ref`
  Meaning: secret-free credential reference persisted in the session manifest.
- `mailbox.stalwart.credential_file`
  Meaning: session-local credential material used for authenticated mailbox access.

Gateway-related preference:

- When the resolver returns `gateway.base_url`, prefer that gateway `/v1/mail/*` facade for shared mailbox operations before falling back to direct Stalwart access.
- When direct Stalwart access is required, use the current `mailbox.stalwart.*` values returned by the resolver rather than trusting stale inherited process env snapshots.
