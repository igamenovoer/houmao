# Reserved Mail-System Compatibility Env Vars

## Common mailbox bindings

- `AGENTSYS_MAILBOX_TRANSPORT`
  Meaning: Selects the active mailbox transport.
  Expected value for this skill: `email`

- `AGENTSYS_MAILBOX_PRINCIPAL_ID`
  Meaning: Stable mailbox principal id for the current agent or participant.
  Example: `AGENTSYS-research`

- `AGENTSYS_MAILBOX_ADDRESS`
  Meaning: Email-like mailbox address associated with the current principal.
  Example: `AGENTSYS-research@agents.localhost`

- `AGENTSYS_MAILBOX_BINDINGS_VERSION`
  Meaning: Monotonic binding version or timestamp used to detect runtime binding refresh.

## Mail-system-specific bindings

- `AGENTSYS_MAILBOX_EMAIL_IMAP_URL`
  Meaning: Reserved IMAP endpoint name for a future true-email adapter.
  Example: `imap://localhost:1143`

- `AGENTSYS_MAILBOX_EMAIL_SMTP_URL`
  Meaning: Reserved SMTP endpoint name for a future true-email adapter.
  Example: `smtp://localhost:1025`

## Usage rules

- In this change, treat `AGENTSYS_MAILBOX_EMAIL_*` names as reserved compatibility names, not as required runtime-populated bindings.
- Use these names when documenting or designing a future true-email adapter so it stays consistent with the filesystem-first mailbox contract.
