# Stalwart Mailbox Env Vars

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
  Meaning: Login identity used for authenticated mailbox access.
- `AGENTSYS_MAILBOX_EMAIL_CREDENTIAL_REF`
  Meaning: Secret-free credential reference persisted in the session manifest.
- `AGENTSYS_MAILBOX_EMAIL_CREDENTIAL_FILE`
  Meaning: Session-local credential material used for authenticated mailbox access.

Gateway-related preference:

- When live gateway env bindings are present, prefer the gateway `/v1/mail/*` facade for shared mailbox operations before falling back to direct Stalwart access.
